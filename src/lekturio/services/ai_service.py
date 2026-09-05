import os
import sys
from ollama import chat

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from lekturio.services.prompt import SYSTEM_PROMPT, QUERY_REWRITE_PROMPT, ANSWER_PROMPT
from lekturio.services.embeddings_service import EmbeddingsService
from lekturio.services.retrival_service import RetrivalService


def dedupe_repeated_blocks(text: str) -> str:
    """Usuwa zduplikowane akapity/cytaty, które model czasem powtarza
    dwukrotnie w wygenerowanej odpowiedzi (np. ten sam cytat wklejony
    dwa razy pod różnymi punktami odpowiedzi)."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    seen = set()
    result = []
    for p in paragraphs:
        # Porównujemy po znormalizowanym prefiksie (nie całym akapicie),
        # żeby złapać też prawie-identyczne powtórzenia z drobnymi różnicami
        # na końcu (np. inny numer chunku w stopce cytatu).
        key = " ".join(p.lower().split())[:200]
        if key not in seen:
            seen.add(key)
            result.append(p)
    return "\n\n".join(result)


def trim_overlapping_context(sorted_chunks: list[dict]) -> list[dict]:
    """Jeśli sąsiednie chunki tej samej książki mają zachodzące na siebie
    zakresy słów (efekt overlapu przy chunkowaniu — patrz ingest_pdfs.py),
    to w kontekście RAG pojawia się dosłownie ten sam fragment tekstu
    dwukrotnie. To myli model i bywa jedną z przyczyn zapętlania się
    generowania (model "widzi" powtórzenie w promptcie i powtarza je dalej).

    Funkcja przycina początek fragmentu kolejnego chunku o tyle słów,
    ile pokrywa się z końcem poprzedniego, na podstawie metadanych
    word_start/word_end zapisanych w location przy ingestii.
    """
    if not sorted_chunks:
        return sorted_chunks

    result = [dict(sorted_chunks[0])]
    for chunk in sorted_chunks[1:]:
        prev = result[-1]
        prev_loc = prev.get("location") or {}
        cur_loc = chunk.get("location") or {}

        same_book = prev.get("title") == chunk.get("title")
        prev_end = prev_loc.get("word_range", [None, None])[1]
        cur_start = cur_loc.get("word_range", [None, None])[0]

        if same_book and prev_end is not None and cur_start is not None and cur_start < prev_end:
            overlap_words = prev_end - cur_start
            words = chunk["fragment"].split()
            # Ucinamy w przybliżeniu tyle słów z początku, ile wynosił
            # overlap — to szacunek (bo split() nie jest identyczny z tym
            # użytym przy ingestii), ale w praktyce eliminuje widoczne
            # dosłowne powtórzenia w kontekście.
            if overlap_words > 0 and overlap_words < len(words):
                chunk = dict(chunk)
                chunk["fragment"] = " ".join(words[overlap_words:])

        result.append(chunk)

    return result


def estimate_tokens(text: str) -> int:
    """Zgrubne oszacowanie liczby tokenów dla polskiego tekstu.
    Współczynnik 1.3 tokena/słowo to bezpieczny margines dla tokenizerów
    typu SentencePiece na tekstach z bogatą odmianą i przedrostkami
    (polski tokenizuje się gorzej niż angielski, więc lepiej przeszacować)."""
    return int(len(text.split()) * 1.3)


def select_chunks_within_budget(
    chunks: dict[str, dict],
    max_context_tokens: int = 5000,
) -> list[dict]:
    """Wybiera chunki o najwyższym similarity, mieszczące się w budżecie
    tokenów, zamiast bezkrytycznie wrzucać do kontekstu wszystko, co
    przekroczyło próg similarity >= 0.50.

    To zabezpiecza przed sytuacją, w której num_ctx w Ollamie zostaje
    po cichu przekroczony (bez błędu — model po prostu traci część
    kontekstu z początku promptu), przez co losowo "znika" akurat ten
    fragment, którego potrzeba do odpowiedzi.

    max_context_tokens=5000 przy num_ctx=8192 zostawia margines na:
    SYSTEM_PROMPT (~500-700 tokenów), pytanie użytkownika, nagłówki
    źródeł w context_blocks, oraz miejsce na samą odpowiedź modelu.
    """
    # Sortuj malejąco po similarity — najbardziej trafne chunki mają
    # pierwszeństwo do wejścia w budżet.
    by_relevance = sorted(chunks.values(), key=lambda c: c["similarity"], reverse=True)

    selected = []
    used_tokens = 0
    skipped = []
    for c in by_relevance:
        chunk_tokens = estimate_tokens(c["fragment"])
        if used_tokens + chunk_tokens > max_context_tokens:
            skipped.append(c["id"])
            continue  # pomiń ten, ale sprawdzaj kolejne — mogą być krótsze
        selected.append(c)
        used_tokens += chunk_tokens

    print(f"[Info] Wybrano {len(selected)}/{len(chunks)} chunków do kontekstu (~{used_tokens} tokenów).")
    if skipped:
        print(f"[Info] Pominięto z powodu budżetu tokenów: {skipped}")

    return selected


class AiService:
    def __init__(
        self,
        model: str = "SpeakLeash/bielik-minitron-7B-v3.0-instruct:Q4_K_M",
        use_reasoning: bool | None = None,
    ):
        self.model = model
        # Modele reasoningowe (np. rodzina gpt-oss) tracą swoją główną
        # przewagę — samo-weryfikację przed odpowiedzią — jeśli wymusimy
        # think=False. Dla takich modeli chcemy think=True, żeby model
        # faktycznie "przemyślał" i zweryfikował cytat/źródło przed
        # wypisaniem odpowiedzi, zamiast strzelać od razu.
        # Dla modeli bez trybu reasoning (np. Bielik) parametr jest
        # ignorowany przez Ollamę, więc bezpiecznie zostawiamy domyślnie
        # True, chyba że użytkownik jawnie wymusi inaczej.
        if use_reasoning is None:
            use_reasoning = "gpt-oss" in model.lower() or "oss" in model.lower()
        self.use_reasoning = use_reasoning

    def generate_search_queries(self, user_query: str) -> list[str]:
        prompt = QUERY_REWRITE_PROMPT.format(user_query=user_query)
        try:
            response = chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                think=False,
            )
            lines = [line.strip() for line in response.message.content.split("\n") if line.strip()]
            queries = [q.lstrip("0123456789.-*• ") for q in lines if len(q) > 5]
            # Prompt prosi o 2-5 zapytań — przycinamy do 5, nie do 3,
            # żeby nie obcinać dekompozycji przy pytaniach o 4+ wątki.
            return queries[:5]
        except Exception as e:
            print(f"[Warning] Query rewrite failed: {e}")
            return []

    def answer_query(self, user_query: str, context: str) -> str:
        """Niestreamingowa wersja — zwraca całą odpowiedź naraz (po dedupe)."""
        content = ANSWER_PROMPT.format(context=context, user_query=user_query)
        response = chat(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
            think=self.use_reasoning,
            options={
                "repeat_penalty": 1.3,
                "repeat_last_n": 256,
                "temperature": 0.4,
                "num_ctx": 8192,
                "num_predict": 4096,
            },
        )
        raw_answer = response.message.content
        if not raw_answer:
            print("[Warning] response.message.content jest puste. Pełny obiekt response:")
            print(response)
        return dedupe_repeated_blocks(raw_answer or "")

    def answer_query_stream(self, user_query: str, context: str):
        """Generator strumieniujący odpowiedź token po tokenie (tak jak
        przychodzi z Ollamy), do wypisywania na żywo w konsoli/UI.

        Uwaga: dedupe_repeated_blocks działa na całym tekście naraz, więc
        NIE jest stosowane tutaj — strumień pokazuje surowe wyjście modelu.
        Wywołujący powinien po zakończeniu streamu samodzielnie odpalić
        dedupe na złożonym tekście, jeśli chce oczyszczoną wersję (patrz main()).
        """
        content = ANSWER_PROMPT.format(context=context, user_query=user_query)
        stream = chat(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
            think=self.use_reasoning,
            stream=True,
        )
        for chunk in stream:
            piece = chunk.message.content
            if piece:
                yield piece


def main():
    print("=== Inicjalizacja usług Lekturio ===")
    embedding_service = EmbeddingsService()
    retrieval_service = RetrivalService(embedding_service)

    # Model brany ze zmiennej środowiskowej, żeby łatwo przełączać się
    # między Bielikiem a gpt-oss:120b bez edytowania kodu za każdym razem.
    # Przykład: $env:LEKTURIO_ANSWER_MODEL="gpt-oss:120b"
    model_name = os.getenv(
        "LEKTURIO_ANSWER_MODEL",
        "SpeakLeash/bielik-minitron-7B-v3.0-instruct:Q4_K_M",
    )
    ai_service = AiService(model=model_name)
    print(f"[Info] Model odpowiadający: {model_name} (reasoning: {ai_service.use_reasoning})")

    user_query = input("wpisz zapytanie>")

    print(f"\n[Pytanie użytkownika]: \"{user_query}\"")

    # 1. Rozszerzenie zapytania przez LLM (dekompozycja na proste sub-query)
    print("\n[1/3] Generowanie zapytań wyszukiwawczych przez model...")
    expanded_queries = ai_service.generate_search_queries(user_query)
    all_queries = [user_query] + expanded_queries
    print(f"Wygenerowane zapytania pomocnicze: {all_queries}")

    # 2. Retrieval z bazy danych
    print("\n[2/3] Wyszukiwanie fragmentów w bazie wektorowej...")
    retrieved_chunks: dict[str, dict] = {}

    for q in all_queries:
        # Wyszukiwanie po pytaniach hipotetycznych (HyPE)
        for r in retrieval_service.get_similar_by_questions(q, limit=5):
            if r["similarity"] >= 0.50:
                retrieved_chunks[r["id"]] = r

        # Wyszukiwanie bezpośrednio po tekście chunku
        for r in retrieval_service.get_similar_by_chunk_text(q, limit=5):
            if r["similarity"] >= 0.50:
                retrieved_chunks[r["id"]] = r

    if not retrieved_chunks:
        print("\n[Odpowiedź]: W bazie wiedzy nie odnaleziono wystarczających fragmentów, aby odpowiedzieć na to pytanie.")
        return

    print(f"Znaleziono {len(retrieved_chunks)} relewantnych fragmentów lektury (przed budżetowaniem).")

    # 3. Zbudowanie kontekstu dla modelu.
    # WAŻNA KOLEJNOŚĆ: najpierw ograniczamy do budżetu tokenów (na podstawie
    # similarity), DOPIERO POTEM sortujemy chronologicznie dla czytelności
    # modelu. Gdyby zrobić to odwrotnie, stracilibyśmy informację o tym,
    # które chunki są najbardziej trafne, zanim je przytniemy.
    budgeted_chunks = select_chunks_within_budget(retrieved_chunks, max_context_tokens=5000)

    sorted_chunks = sorted(budgeted_chunks, key=lambda c: (c["title"], c["chunk_index"]))
    sorted_chunks = trim_overlapping_context(sorted_chunks)

    context_blocks = []
    for c in sorted_chunks:
        author = f" ({c['author']})" if c.get("author") else ""
        location = c.get("location") or {}
        speakers = location.get("speakers") or []
        speakers_str = f" | Postacie w tym fragmencie: {', '.join(speakers)}" if speakers else ""
        context_blocks.append(
            f"--- ŹRÓDŁO: {c['title']}{author} | Część/Fragment #{c['chunk_index']} "
            f"(ID: {c['id']}){speakers_str} ---\n"
            f"{c['fragment']}\n"
        )
    context_str = "\n\n".join(context_blocks)

    print("\n--- SUROWY KONTEKST PRZEKAZANY DO MODELU ---")
    print(context_str)
    print("--- KONIEC KONTEKSTU ---\n")

    # 4. Generowanie odpowiedzi przez model — WERSJA BEZ STREAMINGU (tymczasowo),
    # żeby wykluczyć streaming jako źródło problemu "model nic nie zwrócił".
    print(f"\n[3/3] Generowanie odpowiedzi przez model ({ai_service.model})...")
    print("\n" + "=" * 70)
    print("ODPOWIEDŹ LEKTURIO:")
    print("=" * 70)

    answer = ai_service.answer_query(user_query=user_query, context=context_str)
    print(answer)
    print("=" * 70)


if __name__ == "__main__":
    main()