import json
import os
import re
import sys
import unicodedata
from tkinter import filedialog as fd

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import Json
from pgvector.psycopg2 import register_vector

from lekturio.services.embeddings_service import EmbeddingsService

load_dotenv()

DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "lekturio_db")
DB_USER = os.getenv("POSTGRES_USER", "lekturio")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "lekturio_pass")


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "_", text)


def extract_title_and_author(book_name: str) -> tuple[str, str | None]:
    if " — " in book_name:
        parts = book_name.split(" — ", 1)
        return parts[1].strip(), parts[0].strip()
    if " - " in book_name:
        parts = book_name.split(" - ", 1)
        return parts[1].strip(), parts[0].strip()
    return book_name.strip(), None


def init_database(conn):
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                id VARCHAR(255) PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                author VARCHAR(255),
                fragment TEXT NOT NULL,
                chunk_index INT NOT NULL,
                location JSONB,
                embedding VECTOR
            );
            """
        )
    conn.commit()
    print("[Database] Extension 'vector' and table 'chunks' are ready.")


def process_and_insert_chunks():
    print(f"[Database] Connecting to PostgreSQL at {DB_HOST}:{DB_PORT}/{DB_NAME}...")
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )
    register_vector(conn)
    init_database(conn)

    input_path = fd.askopenfilename(
        title="Select clean_data.json file",
        filetypes=[("JSON files", "*.json")]
    )

    if not input_path:
        print("[Abort] No input file selected.")
        conn.close()
        return

    print(f"[Info] Loading clean book data from: {input_path}")
    with open(input_path, "r", encoding="utf-8") as f:
        pages = json.load(f)

    books_text: dict[str, list[str]] = {}
    for item in pages:
        book_title = item.get("book", "Unknown Book")
        text = item.get("text", "")
        if text:
            books_text.setdefault(book_title, []).append(text)

    embedding_service = EmbeddingsService()
    chunk_size_words = 500
    total_inserted = 0

    print(f"[Info] Found {len(books_text)} books to chunk (500 words per chunk).")

    with conn.cursor() as cur:
        for book_name, text_fragments in books_text.items():
            full_text = "\n\n".join(text_fragments)
            words = full_text.split()
            total_words = len(words)

            title, author = extract_title_and_author(book_name)
            book_slug = slugify(book_name)

            print(f"\n[Processing] '{book_name}' ({total_words} words)")

            for chunk_idx, i in enumerate(range(0, total_words, chunk_size_words), start=1):
                chunk_words = words[i : i + chunk_size_words]
                fragment = " ".join(chunk_words)
                chunk_id = f"{book_slug}_{chunk_idx:04d}"

                location = {
                    "word_range": [i, min(i + chunk_size_words, total_words)],
                    "word_count": len(chunk_words),
                }

                print(f"  -> Chunk #{chunk_idx} ({len(chunk_words)} words) [ID: {chunk_id}]... embedding...")
                embeddings = embedding_service.embed_text(fragment)
                embedding_vector = embeddings[0] if embeddings else None

                cur.execute(
                    """
                    INSERT INTO chunks (id, title, author, fragment, chunk_index, location, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        title = EXCLUDED.title,
                        author = EXCLUDED.author,
                        fragment = EXCLUDED.fragment,
                        chunk_index = EXCLUDED.chunk_index,
                        location = EXCLUDED.location,
                        embedding = EXCLUDED.embedding;
                    """,
                    (
                        chunk_id,
                        title,
                        author,
                        fragment,
                        chunk_idx,
                        Json(location),
                        embedding_vector,
                    ),
                )
                total_inserted += 1

            conn.commit()

    conn.close()
    print("\n" + "=" * 60)
    print(f"[Success] All chunks inserted successfully! Total chunks: {total_inserted}")
    print("=" * 60)


def main():
    process_and_insert_chunks()


if __name__ == "__main__":
    main()
