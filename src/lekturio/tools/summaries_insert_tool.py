from tkinter import filedialog as fd

import os
import psycopg2
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "lekturio_db")
DB_USER = os.getenv("POSTGRES_USER", "lekturio")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "lekturio_pass")


def get_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )


def init_database(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS summaries (
                id VARCHAR(255) PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                summary TEXT NOT NULL
            );
            """
        )
    conn.commit()
    print("[Database] PostgreSQL 'summaries' table is ready.")


def upsert_summary(conn, book_id: str, title: str, summary: str):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO summaries (id, title, summary)
            VALUES (%s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                title = EXCLUDED.title,
                summary = EXCLUDED.summary;
            """,
            (book_id, title, summary),
        )
    conn.commit()


def main():
    path = fd.askdirectory(title="directory with book summaries")
    if not path:
        print("[Info] Nie wybrano folderu, kończę działanie.")
        return

    conn = get_connection()
    try:
        init_database(conn)

        print(len(os.listdir(path)))

        for filename in os.listdir(path):

            file_path = os.path.join(path, filename)

            if not os.path.isfile(file_path) or not filename.lower().endswith(".md"):
                continue

            book_id = os.path.splitext(filename)[0]  
            title = book_id.replace("_", " ").strip()  

            with open(file_path, "r", encoding="utf-8") as f:
                summary = f.read().strip()

            if not summary:
                print(f"[Warning] Plik '{filename}' jest pusty, pomijam.")
                continue

            upsert_summary(conn, book_id, title, summary)
            print(f"[OK] Zapisano/zaktualizowano: {title}")

        print("[Done] Import zakończony.")

    finally:
        conn.close()


if __name__ == "__main__":
    main()