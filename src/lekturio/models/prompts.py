"""Proste funkcje do budowania promptów dla agenta."""


def build_prompt_evaluation_prompt(question: str) -> str:
    """Prompt do oceny czy pytanie wymaga wyszukiwania."""
    return f"""Oceń czy to pytanie wymaga wyszukiwania informacji w treści lektury szkolnej.

Pytanie: {question}

Odpowiedz JSON: {{"needs_search": true}} lub {{"needs_search": false}}

Zasady:
- needs_search = true: pytanie o konkretny fragment, cytat, wydarzenie, postać z lektury
- needs_search = false: ogólne pytanie, pozdrowienie, pytanie o samego agenta

JSON:"""


def build_adapt_hype_answer_prompt(user_question: str, hype_answer: str, title: str, author: str) -> str:
    """Prompt do dopasowania odpowiedzi HyPE do pytania użytkownika."""
    return f"""Użytkownik zadał pytanie: {user_question}

W bazie znalazłem bardzo podobne pytanie z odpowiedzią: {hype_answer}

Źródło: {title} ({author})

Zadanie: Użyj tej odpowiedzi i dopasuj ją do pytania użytkownika. Jeśli odpowiedź HyPE nie odpowiada w pełni na pytanie, dopowiedz brakujące informacje na podstawie kontekstu. Jeśli odpowiedź HyPE jest wystarczająca, po prostu ją zwróć.

Odpowiedź:"""


def build_generate_queries_prompt(question: str) -> str:
    """Prompt do generowania zapytań wyszukiwawczych."""
    return f"""Wygeneruj zapytania do wyszukiwania informacji w lekturze.

Pytanie: {question}

Zadanie: Stwórz 2-4 zapytania:
1. Pytania w formie pytań (jak w HyPE) - pełne zdania pytające
2. Krótkie zapytania (jak do Google) - 2-4 słowa kluczowe

Odpowiedz JSON: {{"queries": ["pytanie 1", "zapytanie 2", ...]}}

JSON:"""


def build_final_answer_prompt(question: str, context: str) -> str:
    """Prompt do generowania końcowej odpowiedzi."""
    return f"""Odpowiedz na pytanie na podstawie dostarczonych fragmentów lektury.

Pytanie: {question}

Fragmenty:
{context}

Zasady:
1. Odpowiadaj TYLKO na podstawie dostarczonych fragmentów
2. Jeśli fragmenty nie zawierają pełnej odpowiedzi, napisz co znalazłeś i wyraźnie powiedz czego brakuje
3. Używaj cytatów z fragmentów aby poprzeć swoje twierdzenia
4. Nie wymyślaj informacji których nie ma w fragmentach

Odpowiedź:"""
