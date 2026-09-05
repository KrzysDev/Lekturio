import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import psycopg2
from dotenv import find_dotenv, load_dotenv
from pgvector.psycopg2 import register_vector
from lekturio.services.embeddings_service import EmbeddingsService

load_dotenv(find_dotenv())

DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "lekturio_db")
DB_USER = os.getenv("POSTGRES_USER", "lekturio")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "lekturio_pass")


class RetrivalService:
    def __init__(self, embedding_service: EmbeddingsService):
        self.embedding_service = embedding_service
        self.conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
        )
        register_vector(self.conn)
        self.cursor = self.conn.cursor()

    def get_similar_chunks(self, text: str, limit: int = 5) -> list[dict]:
        embeddings = self.embedding_service.embed_text(text)
        embedding_vector = embeddings[0] if embeddings else None

        self.cursor.execute(
            """
            SELECT id, title, author, fragment, chunk_index, location,
                   1 - (embedding <=> %s::vector) AS similarity
            FROM chunks
            ORDER BY embedding <=> %s::vector
            LIMIT %s;
            """,
            (embedding_vector, embedding_vector, limit),
        )

        rows = self.cursor.fetchall()
        results = []
        for row in rows:
            results.append({
                "id": row[0],
                "title": row[1],
                "author": row[2],
                "fragment": row[3],
                "chunk_index": row[4],
                "location": row[5],
                "similarity": float(row[6]) if row[6] is not None else 0.0,
            })
        return results

    def get_similar_questions(self, text: str, limit: int = 5) -> list[dict]:
        embeddings = self.embedding_service.embed_text(text)
        embedding_vector = embeddings[0] if embeddings else None

        self.cursor.execute(
            """
            SELECT id, book, page, question, answer, quote_from_book,
                   1 - (embedding <=> %s::vector) AS similarity
            FROM questions
            ORDER BY embedding <=> %s::vector
            LIMIT %s;
            """,
            (embedding_vector, embedding_vector, limit),
        )

        rows = self.cursor.fetchall()
        results = []
        for row in rows:
            results.append({
                "id": row[0],
                "book": row[1],
                "page": row[2],
                "question": row[3],
                "answer": row[4],
                "quote_from_book": row[5],
                "similarity": float(row[6]) if row[6] is not None else 0.0,
            })
        return results


def main():
    embeddings = EmbeddingsService()
    service = RetrivalService(embeddings)

    query = "bunt przeciw bogu Konrad dziady cz. III"
    print(f"\n--- Top Chunks for query: '{query}' ---")
    chunks = service.get_similar_chunks(query, limit=3)
    for c in chunks:
        print(f"\n[{c['title']} | ID: {c['id']} | Similarity: {c['similarity']:.4f}]")
        print(f"Fragment: {c['fragment'][:250]}...")

    print(f"\n\n--- Top Questions for query: '{query}' ---")
    try:
        questions = service.get_similar_questions(query, limit=3)
        for q in questions:
            print(f"\n[{q['book']} (p. {q['page']}) | Similarity: {q['similarity']:.4f}]")
            print(f"Question: {q['question']}")
            print(f"Answer: {q['answer']}")
    except Exception as e:
        print(f"Questions search notice: {e}")


if __name__ == "__main__":
    main()
