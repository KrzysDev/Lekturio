import json
import os
import sys
from tkinter import filedialog as fd

# Add src to sys.path if run directly as a script
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from ollama import chat
from pydantic import ValidationError
from lekturio.models.schemas import QuestionAnswerSet


def generate_qa_for_chunk(
    book: str,
    page: int,
    text: str,
    previous_summary: str = "",
    model: str = "gemma4:latest",
    max_retries: int = 3,
) -> tuple[list[dict], str]:
    stripped_text = text.strip() if text else ""
    if not stripped_text or len(stripped_text) < 30:
        print(f"[Skip] Page {page} of '{book}' is empty or too short. Skipping LLM generation.")
        return [], ""

    context_section = ""
    if previous_summary:
        context_section = (
            "Dotychczasowe streszczenie wydarzeń z poprzednich stron tej książki:\n"
            f"{previous_summary}\n\n"
        )

    prompt = (
        f"Książka: \"{book}\"\n"
        f"Numer strony: {page}\n\n"
        f"{context_section}"
        f"Treść bieżącej strony:\n{text}\n\n"
        "Zadania:\n"
        "1. Na podstawie bieżącej strony (uwzględniając dotychczasowy kontekst fabularny) wygeneruj od 2 do 5 konkretnych pytań i odpowiedzi. "
        "Dla każdego pytania podaj zwięzłą odpowiedź oraz dokładny cytat z tekstu bieżącej strony potwierdzający tę odpowiedź.\n"
        "2. W polu 'summary' napisz zwięzłe (2-3 zdania) podsumowanie najważniejszych wydarzeń z tej strony, "
        "które posłuży jako kontekst fabularny przy analizie kolejnych stron książki.\n"
        "Jeśli strona jest wyłącznie stroną tytułową, spisem treści, zawiera tylko nagłówki/numery lub brak w niej merytorycznej treści, "
        "zwróć pustą listę (qa_pairs: []) oraz puste podsumowanie (summary: '')."
    )

    for attempt in range(1, max_retries + 1):
        print("\n" + "=" * 60)
        print(f"--- [PROMPT DEBUG] Book: '{book}', Page: {page} (Attempt {attempt}/{max_retries}) ---")
        print(prompt)
        print("=" * 60 + "\n")

        try:
            response = chat(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Jesteś pomocnym ekspertem do spraw literatury. "
                            "Twoim zadaniem jest analiza tekstu lektur strona po stronie, śledzenie rozwoju fabuły "
                            "oraz generowanie pytań, odpowiedzi i cytatów na podstawie bieżącego fragmentu i dotychczasowego kontekstu. "
                            "Zwracaj dane ściśle według podanego schematu JSON."
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

            content = response.message.content
            parsed = QuestionAnswerSet.model_validate_json(content)
            qa_list = [qa.model_dump() for qa in parsed.qa_pairs]
            page_summary = parsed.summary.strip()
            return qa_list, page_summary

        except (ValidationError, json.JSONDecodeError) as val_err:
            print(f"[Validation Error] Attempt {attempt}/{max_retries} failed JSON validation for '{book}', page {page}: {val_err}")
            if attempt < max_retries:
                print(f"[Retry] Retrying generation for page {page}...")
            else:
                print(f"[Failed] Exceeded max retries ({max_retries}) due to validation errors. Returning empty QA set.")
                return [], ""
        except Exception as e:
            print(f"[Error] Attempt {attempt}/{max_retries} encountered unexpected error for '{book}', page {page}: {e}")
            if attempt < max_retries:
                print(f"[Retry] Retrying generation for page {page}...")
            else:
                print(f"[Failed] Exceeded max retries ({max_retries}). Returning empty QA set.")
                return [], ""

    return [], ""


def process_clean_data():
    input_path = fd.askopenfilename(
        title="Select clean_data.json file",
        filetypes=[("JSON files", "*.json")]
    )

    if not input_path:
        print("[Abort] No input file selected.")
        return

    print(f"[Info] Loading data from: {input_path}")
    with open(input_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    if not isinstance(chunks, list):
        print("[Error] Input file must contain a JSON list of objects.")
        return

    output_dir = fd.askdirectory(
        title="Select output folder for QA data"
    )

    if not output_dir:
        print("[Abort] No output directory selected.")
        return

    output_path = os.path.join(output_dir, "qa_data.json")
    print(f"[Info] Output file will be saved to: {output_path}")

    results = []
    total_chunks = len(chunks)

    current_book = None
    rolling_summary = ""

    for idx, chunk in enumerate(chunks, start=1):
        book = chunk.get("book", "Unknown Book")
        page = chunk.get("page", idx)
        text = chunk.get("text", "")

        # Reset rolling summary when moving to a different book
        if book != current_book:
            current_book = book
            rolling_summary = ""
            print("\n" + "#" * 60)
            print(f"--- [NEW BOOK] Started processing: {book} ---")
            print("#" * 60)

        print(f"\n[{idx}/{total_chunks}] Processing: \"{book}\" (page {page})...")

        qa_pairs, page_summary = generate_qa_for_chunk(
            book=book,
            page=page,
            text=text,
            previous_summary=rolling_summary,
        )

        # Update cumulative summary for subsequent pages of the same book
        if page_summary:
            if rolling_summary:
                rolling_summary = f"{rolling_summary}\n[Strona {page}]: {page_summary}"
            else:
                rolling_summary = f"[Strona {page}]: {page_summary}"

        result_item = {
            "book": book,
            "page": page,
            "text": text,
            "summary": page_summary,
            "qa_pairs": qa_pairs,
        }
        results.append(result_item)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print("[Success] Processing completed successfully!")
    print(f"[Success] Saved {len(results)} pages with QA pairs to: {output_path}")
    print("=" * 60)


def main():
    process_clean_data()


if __name__ == "__main__":
    main()
