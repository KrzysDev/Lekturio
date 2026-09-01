import os
import re
import unicodedata
from pathlib import Path
import psycopg
from psycopg.types.json import Jsonb
from pgvector.psycopg import register_vector
import tkinter
from tkinter import filedialog
from dotenv import load_dotenv, find_dotenv
from lekturio.tools.pdf_tool import extract_pages, chunk_text
from lekturio.services.embeddings_service import EmbeddingsService


load_dotenv(find_dotenv())


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "_", text)


BOOK_AUTHORS = {
    "Antygona": ("Antygona", "Sofokles"),
    "Makbet": ("Makbet", "William Szekspir"),
    "Skąpiec": ("Skąpiec", "Molier"),
    "Lalka": ("Lalka", "Bolesław Prus"),
    "Wesele": ("Wesele", "Stanisław Wyspiański"),
    "Przedwiośnie": ("Przedwiośnie", "Stefan Żeromski"),
    "Proszę państwa do gazu": ("Proszę państwa do gazu", "Tadeusz Borowski"),
    "Rok 1984": ("Rok 1984", "George Orwell"),
    "Tango": ("Tango", "Sławomir Mrożek"),
    "Balladyna": ("Balladyna", "Juliusz Słowacki"),
    "Zemsta": ("Zemsta", "Aleksander Fredro"),
    "Bogurodzica": ("Bogurodzica", "Anonim"),
    "Lament świętokrzyski": ("Lament świętokrzyski", "Anonim"),
    "Rozmowa Mistrza Polikarpa ze Śmiercią": ("Rozmowa Mistrza Polikarpa ze Śmiercią", "Anonim"),
    "Pieśń o Rolandzie": ("Pieśń o Rolandzie", "Anonim"),
    "Mitologia (Grecja)": ("Mitologia (Grecja)", "Jan Parandowski"),
    "Biblia (fragmenty)": ("Biblia (fragmenty)", "Anonim"),
    "Iliada (fragmenty)": ("Iliada (fragmenty)", "Homer"),
    "Potop (fragmenty)": ("Potop (fragmenty)", "Henryk Sienkiewicz"),
    "Chłopi (fragmenty)": ("Chłopi (fragmenty)", "Władysław Reymont"),
    "Pan Tadeusz (fragmenty)": ("Pan Tadeusz (fragmenty)", "Adam Mickiewicz"),
    "dziady-dziady-poema-dziady-czesc-ii": ("Dziady cz. II", "Adam Mickiewicz"),
    "dziady-dziady-poema-dziady-czesc-iii": ("Dziady cz. III", "Adam Mickiewicz"),
    "Dziady cz. II": ("Dziady cz. II", "Adam Mickiewicz"),
    "Dziady cz. III": ("Dziady cz. III", "Adam Mickiewicz"),
    "Kochanowski — Pieśń IX ks. I": ("Pieśń IX ks. I", "Jan Kochanowski"),
    "Kochanowski — Pieśń V ks. II": ("Pieśń V ks. II", "Jan Kochanowski"),
    "Kochanowski — Treny (IX, X, XI, XIX)": ("Treny (IX, X, XI, XIX)", "Jan Kochanowski"),
    "Krasicki — Hymn do miłości ojczyzny": ("Hymn do miłości ojczyzny", "Ignacy Krasicki"),
    "Mickiewicz — Oda do młodości": ("Oda do młodości", "Adam Mickiewicz"),
    "Mickiewicz — Romantyczność": ("Romantyczność", "Adam Mickiewicz"),
    "Słowacki — Testament mój": ("Testament mój", "Juliusz Słowacki"),
    "Zbrodnia i kara": ("Zbrodnia i kara", "Fiodor Dostojewski"),
    "Zdążyć przed Panem Bogiem": ("Zdążyć przed Panem Bogiem", "Hanna Krall"),
    "Dżuma": ("Dżuma", "Albert Camus"),
    "Ferdydurke (fragmenty)": ("Ferdydurke (fragmenty)", "Witold Gombrowicz"),
    "Inny świat (fragmenty)": ("Inny świat (fragmenty)", "Gustaw Herling-Grudziński"),
    "Podróże z Herodotem (fragmenty)": ("Podróże z Herodotem (fragmenty)", "Ryszard Kapuściński"),
    "Bajki (Krasicki)": ("Bajki", "Ignacy Krasicki"),
}


def parse_title_and_author(filename_stem: str) -> tuple[str, str | None]:
    if filename_stem in BOOK_AUTHORS:
        return BOOK_AUTHORS[filename_stem]

    norm_stem = filename_stem.lower().strip()
    for key, (title, author) in BOOK_AUTHORS.items():
        if key.lower().strip() == norm_stem:
            return title, author

    if " — " in filename_stem:
        parts = filename_stem.split(" — ", 1)
        return parts[1].strip(), parts[0].strip()
    if " - " in filename_stem:
        parts = filename_stem.split(" - ", 1)
        return parts[1].strip(), parts[0].strip()

    return filename_stem.strip(), None


def get_db_connection():
    conn = psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )
    register_vector(conn)
    return conn


def init_db(conn):
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                author TEXT,
                fragment TEXT NOT NULL,
                chunk_index INT NOT NULL,
                page INT,
                location JSONB,
                embedding vector
            );
        """)
        cur.execute("ALTER TABLE chunks DROP COLUMN IF EXISTS chapter;")
        cur.execute("ALTER TABLE chunks ADD COLUMN IF NOT EXISTS page INT;")
        cur.execute("ALTER TABLE chunks ADD COLUMN IF NOT EXISTS location JSONB;")
        cur.execute("ALTER TABLE chunks ALTER COLUMN embedding TYPE vector;")
        conn.commit()


def main():
    conn = get_db_connection()
    init_db(conn)
    embeddings_service = EmbeddingsService()
    print("Connected to PostgreSQL database and initialized 'chunks' table.")

    root = tkinter.Tk()
    root.withdraw()
    folder_path = filedialog.askdirectory(title="Select folder containing PDF files")
    root.destroy()

    if not folder_path:
        default_books_dir = Path("books")
        if default_books_dir.exists():
            folder_path = str(default_books_dir.resolve())
            print(f"No folder selected. Using default folder: {folder_path}")
        else:
            print("No folder selected.")
            conn.close()
            return

    folder = Path(folder_path)
    pdf_files = [p for p in folder.iterdir() if p.suffix.lower() == ".pdf"]

    if not pdf_files:
        print(f"No PDF files found in folder {folder}.")
        conn.close()
        return

    print(f"Found {len(pdf_files)} PDF files to process.\n")

    for pdf_path in pdf_files:
        print("==========================================")
        print(f"Processing: {pdf_path.name}")
        print("==========================================")

        try:
            pages = extract_pages(pdf_path)
            if not pages:
                print(f"No text extracted for {pdf_path.name}, skipping.")
                continue

            book_chunks = []
            for page_num, page_text in pages:
                page_chunk_texts = chunk_text(page_text, chunk_size=300, overlap=50)
                last_pos = 0
                for chunk in page_chunk_texts:
                    start_char = page_text.find(chunk[:50], last_pos)
                    if start_char == -1:
                        start_char = last_pos
                    end_char = start_char + len(chunk)
                    last_pos = start_char

                    book_chunks.append({
                        "page": page_num,
                        "text": chunk,
                        "char_range": [start_char, end_char]
                    })

            print(f"Extracted {len(pages)} pages and created {len(book_chunks)} chunks.")

            print("Generating embeddings...")
            chunk_texts = [c["text"] for c in book_chunks]
            embeddings = embeddings_service.embed_text(chunk_texts)
            print(f"Generated {len(embeddings)} embeddings.")

            title, author = parse_title_and_author(pdf_path.stem)
            book_slug = slugify(title)

            with conn.cursor() as cur:
                for idx, (item, emb) in enumerate(zip(book_chunks, embeddings), start=1):
                    chunk_id = f"{book_slug}_{idx:04d}"

                    location = {
                        "page": item["page"],
                        "char_range": item["char_range"]
                    }

                    cur.execute(
                        """
                        INSERT INTO chunks (id, title, author, fragment, chunk_index, page, location, embedding)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            title = EXCLUDED.title,
                            author = EXCLUDED.author,
                            fragment = EXCLUDED.fragment,
                            chunk_index = EXCLUDED.chunk_index,
                            page = EXCLUDED.page,
                            location = EXCLUDED.location,
                            embedding = EXCLUDED.embedding;
                        """,
                        (
                            chunk_id,
                            title,
                            author,
                            item["text"],
                            idx,
                            item["page"],
                            Jsonb(location),
                            emb
                        )
                    )

                conn.commit()
                print(f"Saved {len(book_chunks)} chunks with embeddings for '{title}' in the database.")

        except Exception as e:
            conn.rollback()
            print(f"Error processing {pdf_path.name}: {e}")

    conn.close()
    print("\nFinished processing all files and saving to database.")


if __name__ == "__main__":
    main()