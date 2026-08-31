import os
import re
import unicodedata
from pathlib import Path
import psycopg
from psycopg.types.json import Jsonb
import tkinter
from tkinter import filedialog
from dotenv import load_dotenv, find_dotenv
from lekturio.tools.pdf_tool import extract_text, chunk_text


load_dotenv(find_dotenv())


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "_", text)


def parse_title_and_author(filename_stem: str) -> tuple[str, str | None]:
    if " — " in filename_stem:
        parts = filename_stem.split(" — ", 1)
        return parts[1].strip(), parts[0].strip()
    if " - " in filename_stem:
        parts = filename_stem.split(" - ", 1)
        return parts[1].strip(), parts[0].strip()
    return filename_stem.strip(), None


def get_db_connection():
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )


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
                chapter TEXT,
                location JSONB,
                embedding vector(1024)
            );
        """)
        conn.commit()


def main():
    conn = get_db_connection()
    init_db(conn)
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
            text = extract_text(pdf_path)
            if not text.strip():
                print(f"Empty text for {pdf_path.name}, skipping.")
                continue

            print(f"Extracted {len(text)} characters from {pdf_path.name}.")

            chunks = chunk_text(text, chunk_size=300, overlap=50)
            print(f"Created {len(chunks)} chunks.")

            title, author = parse_title_and_author(pdf_path.stem)
            book_slug = slugify(title)

            with conn.cursor() as cur:
                last_char_pos = 0
                for idx, chunk in enumerate(chunks, start=1):
                    chunk_id = f"{book_slug}_{idx:04d}"

                    char_start = text.find(chunk[:50], last_char_pos)
                    if char_start == -1:
                        char_start = last_char_pos
                    char_end = char_start + len(chunk)
                    last_char_pos = char_start

                    location = {
                        "chapter": None,
                        "char_range": [char_start, char_end]
                    }

                    cur.execute(
                        """
                        INSERT INTO chunks (id, title, author, fragment, chunk_index, chapter, location, embedding)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            title = EXCLUDED.title,
                            author = EXCLUDED.author,
                            fragment = EXCLUDED.fragment,
                            chunk_index = EXCLUDED.chunk_index,
                            chapter = EXCLUDED.chapter,
                            location = EXCLUDED.location;
                        """,
                        (
                            chunk_id,
                            title,
                            author,
                            chunk,
                            idx,
                            location["chapter"],
                            Jsonb(location),
                            None
                        )
                    )

                conn.commit()
                print(f"Saved {len(chunks)} chunks for '{title}' in the database.")

        except Exception as e:
            conn.rollback()
            print(f"Error processing {pdf_path.name}: {e}")

    conn.close()
    print("\nFinished processing all files and saving to database.")


if __name__ == "__main__":
    main()