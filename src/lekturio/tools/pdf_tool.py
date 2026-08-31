from pathlib import Path
import fitz
import easyocr

ocr_reader = easyocr.Reader(['pl', 'en'])


def extract_text(path: Path) -> str:
    whole_text = []
    doc = fitz.open(path)

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)

        zoom = 2.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)

        image_bytes = pix.tobytes("png")

        page_lines = ocr_reader.readtext(image_bytes, detail=0)

        page_text = "\n".join(page_lines)
        whole_text.append(page_text)
        print(f"Page {page_num + 1}/{len(doc)} done.")

    doc.close()

    return "\n\n".join(whole_text)

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


if __name__ == "__main__":
    print(chunk_text("Lorem ipsum, lorem ipsum, lorem ipsum, something something something something something something"), 3)

    



