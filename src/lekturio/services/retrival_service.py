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

    def get_similar_by_questions(self, text: str, limit: int = 5) -> list[dict]:
        """Search chunks using the question_embedding (HyPE / Hypothetical Prompts)."""
        embeddings = self.embedding_service.embed_text(text)
        embedding_vector = embeddings[0] if embeddings else None

        self.cursor.execute(
            """
            SELECT id, title, author, fragment, chunk_index, location, questions,
                   1 - (question_embedding <=> %s::vector) AS similarity
            FROM chunks
            WHERE question_embedding IS NOT NULL
            ORDER BY question_embedding <=> %s::vector
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
                "questions": row[6],
                "similarity": float(row[7]) if row[7] is not None else 0.0,
            })
        return results

    def get_similar_by_chunk_text(self, text: str, limit: int = 5) -> list[dict]:
        """Search chunks using direct chunk_embedding."""
        embeddings = self.embedding_service.embed_text(text)
        embedding_vector = embeddings[0] if embeddings else None

        self.cursor.execute(
            """
            SELECT id, title, author, fragment, chunk_index, location, questions,
                   1 - (chunk_embedding <=> %s::vector) AS similarity
            FROM chunks
            WHERE chunk_embedding IS NOT NULL
            ORDER BY chunk_embedding <=> %s::vector
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
                "questions": row[6],
                "similarity": float(row[7]) if row[7] is not None else 0.0,
            })
        return results

    def get_similar_hype_questions(self, text: str, limit: int = 5) -> list[dict]:
        """Search HyPE questions and return matching answers."""
        embeddings = self.embedding_service.embed_text(text)
        embedding_vector = embeddings[0] if embeddings else None

        self.cursor.execute(
            """
            SELECT id, title, author, fragment, chunk_index, location, questions,
                   1 - (question_embedding <=> %s::vector) AS similarity
            FROM chunks
            WHERE question_embedding IS NOT NULL
            ORDER BY question_embedding <=> %s::vector
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
                "questions": row[6],
                "similarity": float(row[7]) if row[7] is not None else 0.0,
            })
        return results


def print_search_results(title_header: str, results: list[dict]):
    print("\n" + "=" * 70)
    print(f"=== {title_header} ===")
    print("=" * 70)

    if not results:
        print("Brak pasujących wyników.")
        return

    for idx, r in enumerate(results, start=1):
        author_str = f" ({r['author']})" if r.get("author") else ""
        print(f"\n[{idx}] {r['title']}{author_str} | ID: {r['id']} | Chunk #{r['chunk_index']} | Similarity: {r['similarity']:.4f}")
        print(f"Fragment: {r['fragment'][:280]}...")
        
        questions = r.get("questions") or []
        if questions:
            print("\n  Dopasowane pytania i odpowiedzi (HyPE):")
            for q_idx, q in enumerate(questions, start=1):
                print(f"    [{q_idx}] Pytanie:    {q.get('question')}")
                print(f"        Odpowiedź:  {q.get('answer')}")
                if q.get("quote_from_book"):
                    print(f"        Cytat:      \"{q.get('quote_from_book')}\"")
        print("-" * 70)


def main():
    embeddings = EmbeddingsService()
    service = RetrivalService(embeddings)

    query = "antygona argumentacja swojej zbrodni"

    # 1. HyPE Search (Hypothetical Questions Embedding)
    hype_results = service.get_similar_by_questions(query, limit=3)
    print_search_results(f"HyPE Search (Wyszukiwanie po pytaniach) dla: '{query}'", hype_results)

    # 2. Direct Chunk Text Search
    chunk_results = service.get_similar_by_chunk_text(query, limit=3)
    print_search_results(f"Direct Chunk Search (Wyszukiwanie po tekście fragmentu) dla: '{query}'", chunk_results)


if __name__ == "__main__":
    main()