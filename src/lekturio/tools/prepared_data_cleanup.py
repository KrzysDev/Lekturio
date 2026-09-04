import json
import re
from tkinter import filedialog
import os

TOKEN_RE = re.compile(r'<\|[^<>|]{1,40}\|>')
ROLE_LINE_RE = re.compile(
    r'(?im)^[ \t]*(assistant|human|user|system|participant)[ \t]*$'
)
NONE_GLUE_RE = re.compile(r'\bNone(?=[A-ZŁŚŻŹĆŃÓ])')
TABLE_WRAP_RE = re.compile(
    r'<table>\s*<td[^>]*>(.*?)</table>',
    re.DOTALL | re.IGNORECASE
)
SUP_RE = re.compile(r'<sup>\s*(\d+)\s*</sup>', re.IGNORECASE)
MULTI_BLANK_RE = re.compile(r'\n{3,}')

SUSPECT_KEYWORDS = [
    "university",
    "research group",
    "faculty of",
    "\nborn\n",
    " participant",
]


def strip_markup(text: str) -> str:
    text = TOKEN_RE.sub('', text)
    text = ROLE_LINE_RE.sub('', text)
    text = NONE_GLUE_RE.sub('', text)
    text = TABLE_WRAP_RE.sub(r'\1', text)
    text = SUP_RE.sub(r'[\1]', text)

    return text


def main():

    path = filedialog.askopenfilename(
        title="Book data JSON file",
        filetypes=[("JSON files", "*.json")]
    )

    if not path:
        return

    print(f"Loading: {path}")

    with open(path, "r", encoding="utf-8") as json_data:
        d = json.load(json_data)

    new_data = []

    for counter, chunk in enumerate(d):

        print(f"{counter + 1}/{len(d)}")

        text = chunk["text"]

        text = strip_markup(text)

        chunk["text"] = text

        new_data.append(chunk)

    save_directory = filedialog.askdirectory(
        title="Choose where to save cleaned JSON"
    )

    if not save_directory:
        return

    save_path = os.path.join(
        save_directory,
        "clean_data.json"
    )

    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(
            new_data,
            f,
            ensure_ascii=False,
            indent=2
        )

    print("Done!")
    print(f"Saved to: {save_path}")


if __name__ == "__main__":
    main()