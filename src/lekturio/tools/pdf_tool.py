from pathlib import Path
import pypdfium2 as pdfium
import tkinter as tk
from tkinter import filedialog


def extract_pages(path: Path) -> list[tuple[int, str]]:
    doc = pdfium.PdfDocument(path)
    pages = []

    for page_num, page in enumerate(doc, start=1):
        text = page.get_textpage().get_text_range()
        if text.strip():
            pages.append((page_num, text))

    doc.close()
    return pages


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
        title="Select PDF file",
        filetypes=[("PDF files", "*.pdf")]
    )

    root.destroy()

    if not file_path:
        return None

    return Path(file_path)


if __name__ == "__main__":
    pdf_path = select_pdf_file()

    if pdf_path is None:
        print("No file selected.")
    else:
        print(f"Selected file: {pdf_path}")
        pages = extract_pages(pdf_path)
        print(f"Total non-empty pages: {len(pages)}")

        for page_num, text in pages[:2]:
            print(f"\n--- Page {page_num} ---")
            print(text[:200])