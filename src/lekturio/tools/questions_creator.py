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


def init_database(conn):
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS questions (
                id VARCHAR(255) PRIMARY KEY,
                book VARCHAR(255) NOT NULL,
                page INT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                quote_from_book TEXT,
                embedding VECTOR
            );
            """
        )
    conn.commit()
    print("[Database] Extension 'vector' and table 'questions' are ready.")


def process_and_insert_questions():
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
        title="Select qa_data.json file",
        filetypes=[("JSON files", "*.json")]
    )

    if not input_path:
        print("[Abort] No input file selected.")
        conn.close()
        return

    print(f"[Info] Loading QA data from: {input_path}")
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    embedding_service = EmbeddingsService()
    total_inserted = 0

    with conn.cursor() as cur:
        for item_idx, item in enumerate(data, start=1):
            book = item.get("book", "Unknown Book")
            page = item.get("page", 0)
            qa_pairs = item.get("qa_pairs", [])

            if not qa_pairs:
                continue

            book_slug = slugify(book)
            print(f"[{item_idx}/{len(data)}] Processing '{book}' (page {page}) - {len(qa_pairs)} questions...")

            for q_idx, qa in enumerate(qa_pairs, start=1):
                question = qa.get("question", "").strip()
                answer = qa.get("answer", "").strip()
                quote = qa.get("quote_from_book", "").strip()

                if not question:
                    continue

                q_id = f"{book_slug}_p{page:04d}_q{q_idx:02d}"

                embeddings = embedding_service.embed_text(question)
                embedding_vector = embeddings[0] if embeddings else None

                cur.execute(
                    """
                    INSERT INTO questions (id, book, page, question, answer, quote_from_book, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        book = EXCLUDED.book,
                        page = EXCLUDED.page,
                        question = EXCLUDED.question,
                        answer = EXCLUDED.answer,
                        quote_from_book = EXCLUDED.quote_from_book,
                        embedding = EXCLUDED.embedding;
                    """,
                    (
                        q_id,
                        book,
                        page,
                        question,
                        answer,
                        quote,
                        embedding_vector,
                    ),
                )
                total_inserted += 1

            conn.commit()

    conn.close()
    print("\n" + "=" * 60)
    print(f"[Success] All questions inserted successfully! Total questions: {total_inserted}")
    print("=" * 60)


def main():
    process_and_insert_questions()


if __name__ == "__main__":
    main()

