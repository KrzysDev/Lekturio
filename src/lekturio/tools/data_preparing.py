import os
import json
from tkinter import filedialog as fd
from pdf2image import convert_from_path
from ollama import chat

def prepare_data_for_database_insert():
    path = fd.askdirectory(title="Select folder with PDFs")
    output_root = fd.askdirectory(title="Select output folder")

    data_output_root = fd.askdirectory(title="Select json data output folder")

    print(path)

    books_data = []

    for file in os.listdir(path):
        if not file.lower().endswith(".pdf"):
            continue

        full_pdf_path = os.path.join(path, file)
        book_name = os.path.splitext(file)[0]
        photo_book_output_dir = os.path.join(output_root, book_name)
        os.makedirs(photo_book_output_dir, exist_ok=True)

        print("preparing....", file)

        images = convert_from_path(full_pdf_path)
        print(f"converting {len(images)} images")

        images_to_convert = []
        for i, img in enumerate(images):
            print("converting", i, "image...")
            img_path = os.path.join(photo_book_output_dir, f"page{i}.jpg")
            img.save(img_path, "JPEG")
            images_to_convert.append(img_path)

        
        print("extracting....")

        for counter, image_path in enumerate(images_to_convert, start=1):
            print("extracting:", f"{counter}/{len(images_to_convert)}", "....")
            response = chat(
                model="deepseek-ocr:3b",
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "Extract the text from the page of this book. "
                            "Keep the formatting just as it is in the page. "
                            "Do not return anything else except this text."
                        ),
                        "images": [image_path],
                    }
                ],
                think=False,
            )
            
            books_data.append({
                "book" : book_name,
                "text": response.message.content,
                "page": counter,
            })

        json_save_path = os.path.join(data_output_root, f"book_data.json")
        with open(json_save_path, "w", encoding="utf-8") as f:
            json.dump(books_data, f, ensure_ascii=False, indent=2)

        print(f"saved {json_save_path}")


def main():
    prepare_data_for_database_insert()


if __name__ == "__main__":
    main()