from pathlib import Path
import pypdfium2 as pdfium
import tkinter as tk
from tkinter import filedialog


def extract_text(path: Path) -> str:
    doc = pdfium.PdfDocument(path)

    whole_text = "\n".join(
        page.get_textpage().get_text_range()
        for page in doc
    )

    doc.close()

    return whole_text


def chunk_text(
    whole_text: str,
    chunk_size: int = 300,
    overlap: int = 50
) -> list[str]:
    if overlap >= chunk_size:
        raise ValueError("Overlap has to be smaller than chunk size")

    words = whole_text.split()
    if not words:
        return []

    chunks = []
    step = chunk_size - overlap

    for i in range(0, len(words), step):
        chunk = " ".join(words[i : i + chunk_size])
        chunks.append(chunk)

        if i + chunk_size >= len(words):
            break

    return chunks


def select_pdf_file() -> Path | None:
    root = tk.Tk()
    root.withdraw()

    file_path = filedialog.askopenfilename(
        title="Wybierz plik PDF",
        filetypes=[("Pliki PDF", "*.pdf")]
    )

    root.destroy()

    if not file_path:
        return None

    return Path(file_path)


if __name__ == "__main__":
    pdf_path = select_pdf_file()

    if pdf_path is None:
        print("Nie wybrano żadnego pliku.")
    else:
        print(f"Wybrany plik: {pdf_path}")

        text = extract_text(pdf_path)
        print("\n--- Wyekstrahowany tekst ---")
        print(text)

        chunks = chunk_text(text)
        print(f"\nLiczba chunków: {len(chunks)}")
        for i, chunk in enumerate(chunks, start=1):
            print(f"\n--- Chunk {i} ---")
            print(chunk)