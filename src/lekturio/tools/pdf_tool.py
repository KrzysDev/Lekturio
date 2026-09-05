import os
import re
import sys
import traceback
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
import textract
from ollama import chat

from lekturio.services.embeddings_service import EmbeddingsService
from lekturio.models.schemas import QuestionAnswerSet

load_dotenv()

DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "lekturio_db")
DB_USER = os.getenv("POSTGRES_USER", "lekturio")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "lekturio_pass")

QUESTION_GEN_MODEL = os.getenv("LEKTURIO_QUESTION_MODEL", "SpeakLeash/bielik-minitron-7B-v3.0-instruct:Q4_K_M")

SPEAKER_LINE_RE = re.compile(
    r"^([A-ZŻŹĆĄŚĘŁÓŃ][A-ZŻŹĆĄŚĘŁÓŃa-zżźćąśęłóń]{1,30}(?:\s[A-ZŻŹĆĄŚĘŁÓŃ][a-zżźćąśęłóń]+)?)\s*[:\.]?\s*$"
)

SCENE_HEADER_RE = re.compile(
    r"^(AKT|SCENA|ODSŁONA)\s+[A-ZŻŹĆĄŚĘŁÓŃ0-9IVXLC]+", re.IGNORECASE
)


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
                questions JSONB,
                chunk_embedding VECTOR,
                question_embedding VECTOR
            );
            """
        )
    conn.commit()
    print("[Database] PostgreSQL 'chunks' table with dual embeddings is ready.")


def sanitize_qa_pair(qa: dict, title: str) -> dict | None:
    question = qa.get("question", "").strip()
    answer = qa.get("answer", "").strip()
    quote = qa.get("quote_from_book", "").strip()

    if len(question) < 20 and (
        answer.startswith(("Dlaczego", "W jaki sposób", "Jak", "Co ", "Kto ", "Gdzie "))
        and "?" in answer
    ):
        question, answer = answer, question

    question = re.sub(r",?\s*w kontekście\s*[:\?]?$", "?", question, flags=re.IGNORECASE).strip()
    if not question.endswith("?"):
        question += "?"

    if len(question) < 15 or len(answer) < 5:
        return None

    return {
        "question": question,
        "answer": answer,
        "quote_from_book": quote,
    }


def split_into_lines(raw_text: str) -> list[str]:
    """Dzieli surowy tekst na oczyszczone, niepuste linie, zachowując
    naturalne granice kwestii dialogowych i akapitów z PDF-a."""
    lines = [ln.strip() for ln in raw_text.splitlines()]
    return [ln for ln in lines if ln]


def build_word_index(lines: list[str]) -> list[dict]:
    """Buduje płaską listę słów, gdzie każde słowo pamięta:
    - z której linii pochodzi (do rekonstrukcji podziałów przy chunkowaniu)
    - aktualnego mówiącego (jeśli linia wygląda jak etykieta postaci)
    - aktualną scenę/akt (jeśli linia wygląda jak nagłówek sceny)
    """
    word_index = []
    current_speaker = None
    current_scene = None

    for line in lines:
        scene_match = SCENE_HEADER_RE.match(line)
        if scene_match:
            current_scene = line
            continue

        speaker_match = SPEAKER_LINE_RE.match(line)
        if speaker_match and len(line.split()) <= 4:
            current_speaker = speaker_match.group(1)
            for w in line.split():
                word_index.append(
                    {
                        "word": w,
                        "line": line,
                        "speaker": current_speaker,
                        "scene": current_scene,
                        "is_speaker_label": True,
                    }
                )
            continue

        for w in line.split():
            word_index.append(
                {
                    "word": w,
                    "line": line,
                    "speaker": current_speaker,
                    "scene": current_scene,
                    "is_speaker_label": False,
                }
            )

    return word_index


def reconstruct_fragment(window: list[dict]) -> str:
    fragment_lines = []
    current_line = None
    buf = []

    for item in window:
        if item["line"] != current_line:
            if buf:
                fragment_lines.append(" ".join(buf))
            buf = [item["word"]]
            current_line = item["line"]
        else:
            buf.append(item["word"])

    if buf:
        fragment_lines.append(" ".join(buf))

    return "\n".join(fragment_lines)


def chunk_text_preserving_structure(
    raw_text: str, chunk_size: int = 500, overlap: int = 100
):
    lines = split_into_lines(raw_text)
    word_index = build_word_index(lines)

    if not word_index:
        return []

    step = max(chunk_size - overlap, 1)
    chunks = []

    for i in range(0, len(word_index), step):
        window = word_index[i : i + chunk_size]
        if not window:
            continue

        fragment = reconstruct_fragment(window)

        speakers = sorted({w["speaker"] for w in window if w["speaker"]})
        scenes = sorted({w["scene"] for w in window if w["scene"]})

        chunks.append(
            {
                "fragment": fragment,
                "word_start": i,
                "word_end": min(i + chunk_size, len(word_index)),
                "speakers": speakers,
                "scenes": scenes,
            }
        )
        if i + chunk_size >= len(word_index):
            break

    return chunks


def generate_questions_for_chunk(
    title: str,
    author: str | None,
    chunk_idx: int,
    fragment: str,
    model: str = QUESTION_GEN_MODEL,
) -> list[dict]:
    author_info = f" (Autor: {author})" if author else ""
    prompt = (
        f"Lektura: \"{title}\"{author_info}\n"
        f"Fragment tekstu (część {chunk_idx}):\n{fragment}\n\n"
        "Zadanie:\n"
        "Wygeneruj od 2 do 4 konkretnych, pełnych pytań i odpowiedzi (z cytatami) na podstawie powyższego fragmentu.\n\n"
        "ZASADY:\n"
        "1. Pole 'question' MUSI zawierać kompletne, zamknięte pytanie zakończone znakiem zapytania (np. 'W jaki sposób Antygona w dramacie Sofoklesa uzasadnia swój czyn?').\n"
        "2. Pole 'answer' MUSI zawierać zwięzłą, rzeczową odpowiedź wyjaśniającą to pytanie.\n"
        "3. Pole 'quote_from_book' MUSI zawierać dosłowny cytat z podanego fragmentu — skopiowany dokładnie, "
        "bez łączenia ze sobą fragmentów pochodzących z różnych, nieciągłych miejsc tekstu.\n"
        "4. Używaj pełnych imion bohaterów i nazwy lektury, unikaj ogólników typu 'bohater', 'podmiot'."
    )

    try:
        response = chat(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Jesteś wybitnym nauczycielem języka polskiego i literatury. "
                        "Tworzysz precyzyjne pytania maturalne i egzaminacyjne do fragmentów lektur. "
                        "Każde pytanie w polu 'question' musi być pełnym, poprawnym gramatycznie pytaniem z pytajnikiem na końcu. "
                        "Zwracaj wyłącznie poprawny obiekt JSON zawierający tablicę 'qa_pairs'."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            format=QuestionAnswerSet.model_json_schema(),
            think=False,
        )
        parsed = QuestionAnswerSet.model_validate_json(response.message.content)
        sanitized_list = []
        for qa in parsed.qa_pairs:
            cleaned = sanitize_qa_pair(qa.model_dump(), title)
            if cleaned:
                sanitized_list.append(cleaned)
        return sanitized_list
    except Exception as e:
        print(f"  [Warning] Failed to generate questions for chunk {chunk_idx}: {e}")
        traceback.print_exc()
        return []


def delete_existing_book_chunks(conn, book_slug: str):
    with conn.cursor() as cur:
        cur.execute("DELETE FROM chunks WHERE id LIKE %s;", (f"{book_slug}_%",))
        deleted = cur.rowcount
    conn.commit()
    if deleted:
        print(f"[Cleanup] Usunięto {deleted} starych chunków dla '{book_slug}' przed re-ingestem.")


def process_pdf_folder(chunk_size: int = 500, overlap: int = 100, reingest: bool = True):
    pdf_dir = fd.askdirectory(title="Select folder with PDFs")
    if not pdf_dir:
        print("[Abort] No folder selected.")
        return

    pdf_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith(".pdf")]
    if not pdf_files:
        print(f"[Abort] No PDF files found in {pdf_dir}")
        return

    print(f"[Info] Found {len(pdf_files)} PDF files to process.")
    print(f"[Info] chunk_size={chunk_size}, overlap={overlap} ({overlap / chunk_size:.0%})")

    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )
    register_vector(conn)
    init_database(conn)

    embedding_service = EmbeddingsService()
    total_chunks_inserted = 0

    for file_idx, file_name in enumerate(pdf_files, start=1):
        full_pdf_path = os.path.join(pdf_dir, file_name)
        book_name = os.path.splitext(file_name)[0]
        title, author = extract_title_and_author(book_name)
        book_slug = slugify(book_name)

        print("\n" + "=" * 60)
        print(f"[{file_idx}/{len(pdf_files)}] Extracting text from '{file_name}' using textract...")
        print("=" * 60)

        try:
            raw_text = textract.process(full_pdf_path).decode("utf-8", errors="ignore")
        except Exception as e:
            print(f"[Error] Failed to extract text from {file_name}: {e}")
            continue

        if reingest:
            delete_existing_book_chunks(conn, book_slug)

        chunks = chunk_text_preserving_structure(raw_text, chunk_size=chunk_size, overlap=overlap)
        print(f"[Info] Zbudowano {len(chunks)} chunków (z zachowaniem struktury linii + overlap).")

        if not chunks:
            print(f"[Skip] '{file_name}' yielded 0 chunks.")
            continue

        with conn.cursor() as cur:
            for chunk_idx, chunk_data in enumerate(chunks, start=1):
                fragment = chunk_data["fragment"]
                chunk_id = f"{book_slug}_{chunk_idx:04d}"

                location = {
                    "word_range": [chunk_data["word_start"], chunk_data["word_end"]],
                    "word_count": chunk_data["word_end"] - chunk_data["word_start"],
                    "speakers": chunk_data["speakers"],
                    "scenes": chunk_data["scenes"],
                }

                qa_pairs = generate_questions_for_chunk(title, author, chunk_idx, fragment)
                speakers_str = ", ".join(chunk_data["speakers"]) or "brak"
                print(
                    f" -> Chunk #{chunk_idx} ({location['word_count']} words) "
                    f"[ID: {chunk_id}] [Postacie: {speakers_str}] - "
                    f"generated {len(qa_pairs)} questions. Embedding..."
                )

                chunk_embeddings = embedding_service.embed_text(fragment)
                chunk_vector = chunk_embeddings[0] if chunk_embeddings else None

                if qa_pairs:
                    questions_text = f"[{title}] " + " \n".join(qa["question"] for qa in qa_pairs)
                    q_embeddings = embedding_service.embed_text(questions_text)
                    question_vector = q_embeddings[0] if q_embeddings else None
                else:
                    question_vector = None

                cur.execute(
                    """
                    INSERT INTO chunks (
                        id, title, author, fragment, chunk_index, location,
                        questions, chunk_embedding, question_embedding
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        title = EXCLUDED.title,
                        author = EXCLUDED.author,
                        fragment = EXCLUDED.fragment,
                        chunk_index = EXCLUDED.chunk_index,
                        location = EXCLUDED.location,
                        questions = EXCLUDED.questions,
                        chunk_embedding = EXCLUDED.chunk_embedding,
                        question_embedding = EXCLUDED.question_embedding;
                    """,
                    (
                        chunk_id,
                        title,
                        author,
                        fragment,
                        chunk_idx,
                        Json(location),
                        Json(qa_pairs),
                        chunk_vector,
                        question_vector,
                    ),
                )
                total_chunks_inserted += 1

            conn.commit()

    conn.close()
    print("\n" + "=" * 60)
    print(f"[Success] All PDFs processed! Total chunks inserted: {total_chunks_inserted}")
    print("=" * 60)


def main():
    process_pdf_folder(chunk_size=500, overlap=100, reingest=True)


if __name__ == "__main__":
    main()