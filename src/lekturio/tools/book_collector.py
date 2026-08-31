import requests
import time
import json
import unicodedata
from pathlib import Path

API_BASE = "https://wolnelektury.pl/api/books/"
OUTPUT_DIR = Path("lektury_pdf")
OUTPUT_DIR.mkdir(exist_ok=True)

def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.lower().strip()


_ALL_BOOKS_CACHE: list[dict] | None = None

def fetch_all_books() -> list[dict]:
    global _ALL_BOOKS_CACHE
    if _ALL_BOOKS_CACHE is not None:
        return _ALL_BOOKS_CACHE

    print("📚 Downloading...")
    books = []
    url = API_BASE
    while url:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict) and "results" in data:
            books.extend(data["results"])
            url = data.get("next")
        else:
            books.extend(data)
            url = None
    print(f"   -> pobrano {len(books)} pozycji\n")
    _ALL_BOOKS_CACHE = books
    return books
BOOKS = [
    {"title": "Mitologia (Grecja)", "search": "Mitologia", "known_slug": None,
     "note": "Parandowski zm. 1978 — prawdopodobnie NIE ma prawa domeny publicznej"},
    {"title": "Antygona", "search": "Antygona", "known_slug": None},
    {"title": "Makbet", "search": "Makbet", "known_slug": None},
    {"title": "Skąpiec", "search": "Skąpiec", "known_slug": None},
    {"title": "Dziady cz. III", "search": "Dziady", "known_slug": "dziady-dziady-poema-dziady-czesc-iii"},
    {"title": "Lalka", "search": "Lalka", "known_slug": None},
    {"title": "Zbrodnia i kara", "search": "Zbrodnia i kara", "known_slug": None},
    {"title": "Wesele", "search": "Wesele", "known_slug": None},
    {"title": "Przedwiośnie", "search": "Przedwiośnie", "known_slug": None},
    {"title": "Proszę państwa do gazu", "search": "Proszę państwa do gazu", "known_slug": None,
     "note": "Borowski zm. 1951 — prawa mogły niedawno wygasnąć, sprawdź ręcznie jeśli brak"},
    {"title": "Zdążyć przed Panem Bogiem", "search": "Zdążyć przed Panem Bogiem", "known_slug": None,
     "note": "Krall — autorka żyjąca, prawdopodobnie NIE na WL"},
    {"title": "Dżuma", "search": "Dżuma", "known_slug": None,
     "note": "Camus zm. 1960 — prawa wygasają ok. 2030, prawdopodobnie NIE na WL"},
    {"title": "Rok 1984", "search": "Rok 1984", "known_slug": None,
     "note": "Orwell zm. 1950 — prawa wygasły w UE w 2020, może być dostępne"},
    {"title": "Tango", "search": "Tango", "known_slug": None,
     "note": "Mrożek zm. 2013 — prawdopodobnie NIE na WL"},
    {"title": "Górą Edek", "search": "Górą Edek", "known_slug": None,
     "note": "Nowakowski zm. 2014 — prawdopodobnie NIE na WL"},
    {"title": "Miejsce", "search": "Miejsce Stasiuk", "known_slug": None,
     "note": "Stasiuk żyjący — prawdopodobnie NIE na WL"},
    {"title": "Profesor Andrews w Warszawie", "search": "Profesor Andrews w Warszawie", "known_slug": None,
     "note": "Tokarczuk żyjąca — prawdopodobnie NIE na WL"},

    {"title": "Biblia (fragmenty)", "search": "Biblia", "known_slug": None},
    {"title": "Iliada (fragmenty)", "search": "Iliada", "known_slug": None},
    {"title": "Lament świętokrzyski", "search": "Lament świętokrzyski", "known_slug": None},
    {"title": "Rozmowa Mistrza Polikarpa ze Śmiercią", "search": "Rozmowa mistrza Polikarpa ze śmiercią", "known_slug": None},
    {"title": "Pieśń o Rolandzie", "search": "Pieśń o Rolandzie", "known_slug": None},
    {"title": "Potop (fragmenty)", "search": "Potop", "known_slug": None},
    {"title": "Chłopi (fragmenty)", "search": "Chłopi", "known_slug": None},
    {"title": "Ferdydurke (fragmenty)", "search": "Ferdydurke", "known_slug": None,
     "note": "Gombrowicz zm. 1969 — prawdopodobnie NIE na WL"},
    {"title": "Inny świat (fragmenty)", "search": "Inny świat", "known_slug": None,
     "note": "Herling-Grudziński zm. 2000 — prawdopodobnie NIE na WL"},
    {"title": "Podróże z Herodotem (fragmenty)", "search": "Podróże z Herodotem", "known_slug": None,
     "note": "Kapuściński zm. 2007 — prawdopodobnie NIE na WL"},

    {"title": "Bajki (Krasicki)", "search": "Bajki Krasicki", "known_slug": None},
    {"title": "Dziady cz. II", "search": "Dziady", "known_slug": "dziady-dziady-poema-dziady-czesc-ii"},
    {"title": "Pan Tadeusz (fragmenty)", "search": "Pan Tadeusz", "known_slug": None},
    {"title": "Balladyna", "search": "Balladyna", "known_slug": None},
    {"title": "Zemsta", "search": "Zemsta", "known_slug": None},

    {"title": "Horacy — Zbudowałem pomnik", "search": "Zbudowałem pomnik", "known_slug": None},
    {"title": "Horacy — Do Deliusza", "search": "Do Deliusza", "known_slug": None},
    {"title": "Horacy — Do Leukonoe", "search": "Do Leukonoe", "known_slug": None},
    {"title": "Bogurodzica", "search": "Bogurodzica", "known_slug": None},
    {"title": "Kochanowski — Pieśń IX ks. I", "search": "Pieśń IX", "known_slug": None},
    {"title": "Kochanowski — Pieśń V ks. II", "search": "Pieśń V", "known_slug": None},
    {"title": "Kochanowski — Treny (IX, X, XI, XIX)", "search": "Treny", "known_slug": None,
     "note": "Pobiera cały zbiór Trenów — wybierz z niego IX, X, XI, XIX"},
    {"title": "Krasicki — Hymn do miłości ojczyzny", "search": "Hymn do miłości ojczyzny", "known_slug": None},
    {"title": "Mickiewicz — Oda do młodości", "search": "Oda do młodości", "known_slug": None},
    {"title": "Mickiewicz — Romantyczność", "search": "Romantyczność", "known_slug": None},
    {"title": "Słowacki — Testament mój", "search": "Testament mój", "known_slug": None},
]


def find_book(search_term: str) -> dict | None:
    """Finds a work by title by filtering the full list from the API LOCALLY.
    If there is more than one match, prints all candidates and picks the
    shortest title containing the phrase (usually the most accurate)."""
    try:
        all_books = fetch_all_books()
    except requests.RequestException as e:
        print(f"   ⚠️  Error fetching book list: {e}")
        return None

    norm_search = normalize(search_term)
    matches = [b for b in all_books if norm_search in normalize(b["title"])]

    if not matches:
        return None

    if len(matches) > 1:
        print(f"   ℹ️  Found {len(matches)} matches, picking the shortest:")
        for m in matches[:5]:
            print(f"      - {m['title']} ({m.get('author', '?')})")

    matches.sort(key=lambda b: len(b["title"]))
    return matches[0]


def get_details(book_href: str) -> dict | None:
    try:
        resp = requests.get(book_href, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        print(f"   ⚠️  Error fetching metadata: {e}")
        return None


def download_pdf(pdf_url: str, filename: str) -> bool:
    try:
        resp = requests.get(pdf_url, timeout=30)
        resp.raise_for_status()
        path = OUTPUT_DIR / filename
        path.write_bytes(resp.content)
        return True
    except requests.RequestException as e:
        print(f"   ⚠️  Error downloading PDF: {e}")
        return False


def main():
    found, not_found = [], []

    for entry in BOOKS:
        title = entry["title"]
        print(f"\n🔎 {title}")

        # 1) if we know the exact slug — go straight to it
        if entry.get("known_slug"):
            details = get_details(f"{API_BASE}{entry['known_slug']}/")
        else:
            summary = find_book(entry["search"])
            if not summary:
                print("   ❌ Not found in the API (likely missing from WL — see note)")
                not_found.append(entry)
                continue
            details = get_details(summary["href"])

        if not details:
            not_found.append(entry)
            continue

        pdf_url = details.get("pdf")
        if not pdf_url:
            print("   ❌ Work found, but no PDF file available")
            not_found.append(entry)
            continue

        slug = details.get("slug") or entry.get("known_slug") or title
        filename = f"{slug}.pdf"

        if download_pdf(pdf_url, filename):
            print(f"   ✅ Saved: {filename}")
            found.append({"title": title, "file": filename, "slug": slug})
        else:
            not_found.append(entry)

        time.sleep(0.5) 

    print("\n" + "=" * 60)
    print(f"✅ Downloaded: {len(found)} / {len(BOOKS)}")
    print(f"❌ Not found: {len(not_found)}")
    if not_found:
        print("\nMissing items (check notes — usually due to copyright):")
        for e in not_found:
            note = f" — {e['note']}" if e.get("note") else ""
            print(f"  • {e['title']}{note}")

    (OUTPUT_DIR / "_download_report.json").write_text(
        json.dumps({"found": found, "not_found": [e["title"] for e in not_found]},
                   ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"\n📄 Full report saved to {OUTPUT_DIR / '_download_report.json'}")


if __name__ == "__main__":
    main()