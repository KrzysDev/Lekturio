import json
from lekturio.services.ai_service import AiService
from lekturio.services.embeddings_service import EmbeddingsService
from lekturio.services.retrival_service import RetrivalService
from lekturio.models.prompts import (
    build_prompt_evaluation_prompt,
    build_adapt_hype_answer_prompt,
    build_generate_queries_prompt,
    build_final_answer_prompt,
)


class AgentService:
    """Uproszczony agent do wyszukiwania informacji w lekturach."""
    
    def __init__(self):
        self.ai = AiService()
        self.embeddings = EmbeddingsService()
        self.retrieval = RetrivalService(self.embeddings)
    
    def ask(self, question: str) -> str:
        """Główna funkcja - zadaj pytanie, otrzymaj odpowiedź."""
        print(f"\n[USER] {question}")
        
        # 1. Oceń czy pytanie wymaga wyszukiwania
        if not self._needs_search(question):
            print("[AGENT] Krótka odpowiedź - bez wyszukiwania")
            return self.ai.ask(question)
        
        print("[AGENT] Wymaga wyszukiwania")
        
        # 2. Sprawdź podobne pytania HyPE
        similar_questions = self._find_similar_hype_questions(question)
        if similar_questions:
            print(f"[AGENT] Znaleziono {len(similar_questions)} podobnych pytań HyPE")
            # Użyj odpowiedzi z HyPE jako części odpowiedzi
            hype_answer = self._use_hype_answers(question, similar_questions)
            if hype_answer:
                return hype_answer
        
        # 3. Wygeneruj zapytania
        queries = self._generate_queries(question)
        print(f"[AGENT] Wygenerowano {len(queries)} zapytań")
        
        # 4. Wykonaj zapytania i zbierz wyniki
        all_chunks = self._execute_queries(queries)
        print(f"[AGENT] Zebrano {len(all_chunks)} unikalnych fragmentów")
        
        # 5. Wygeneruj odpowiedź
        return self._generate_answer(question, all_chunks)
    
    def _needs_search(self, question: str) -> bool:
        """Sprawdź czy pytanie wymaga wyszukiwania w lekturze."""
        prompt = build_prompt_evaluation_prompt(question)
        response = self.ai.ask(prompt)
        try:
            data = json.loads(response)
            return data.get("needs_search", True)
        except:
            return True  # Jeśli błąd, lepiej wyszukać
    
    def _find_similar_hype_questions(self, question: str) -> list[dict]:
        """Znajdź podobne pytania HyPE w bazie."""
        results = self.retrieval.get_similar_hype_questions(question, limit=3)
        return results
    
    def _use_hype_answers(self, question: str, similar_questions: list[dict]) -> str | None:
        """Użyj odpowiedzi z HyPE jeśli są wystarczająco podobne."""
        # Sprawdź czy któraś odpowiedź HyPE jest wystarczająco dobra
        for result in similar_questions:
            if result["similarity"] > 0.85:  # Wysokie podobieństwo
                questions = result.get("questions", [])
                if questions:
                    # Znajdź najbardziej podobne pytanie HyPE
                    for q in questions:
                        hype_answer = q.get("answer", "")
                        if hype_answer:
                            print(f"[AGENT] Używam odpowiedzi HyPE (similarity: {result['similarity']:.2f})")
                            # Dopowiedz na podstawie pytania użytkownika
                            return self._adapt_hype_answer(question, hype_answer, result)
        
        return None
    
    def _adapt_hype_answer(self, user_question: str, hype_answer: str, source: dict) -> str:
        """Dopasuj odpowiedź HyPE do pytania użytkownika."""
        prompt = build_adapt_hype_answer_prompt(
            user_question, 
            hype_answer, 
            source['title'], 
            source.get('author', 'Nieznany')
        )
        return self.ai.ask(prompt)
    
    def _generate_queries(self, question: str) -> list[str]:
        """Wygeneruj zapytania do wyszukiwania."""
        prompt = build_generate_queries_prompt(question)
        response = self.ai.ask(prompt)
        try:
            data = json.loads(response)
            return data.get("queries", [question])
        except:
            return [question]
    
    def _execute_queries(self, queries: list[str]) -> list[dict]:
        """Wykonaj zapytania i zbierz unikalne wyniki."""
        all_chunks = []
        seen_ids = set()
        
        for query in queries:
            # Wyszukaj po pytaniach HyPE
            hype_results = self.retrieval.get_similar_by_questions(query, limit=3)
            for result in hype_results:
                if result["id"] not in seen_ids:
                    all_chunks.append(result)
                    seen_ids.add(result["id"])
            
            # Wyszukaj po treści chunków
            chunk_results = self.retrieval.get_similar_by_chunk_text(query, limit=3)
            for result in chunk_results:
                if result["id"] not in seen_ids:
                    all_chunks.append(result)
                    seen_ids.add(result["id"])
        
        return all_chunks
    
    def _generate_answer(self, question: str, chunks: list[dict]) -> str:
        """Wygeneruj odpowiedź na podstawie fragmentów."""
        if not chunks:
            return "Nie znalazłem żadnych fragmentów dotyczących tego pytania w dostępnych lekturach."
        
        context = self._format_chunks(chunks)
        prompt = build_final_answer_prompt(question, context)
        return self.ai.ask(prompt)
    
    def _format_chunks(self, chunks: list[dict]) -> str:
        """Formatuj fragmenty do czytelnego tekstu."""
        formatted = []
        for i, chunk in enumerate(chunks, 1):
            text = f"""
--- Fragment {i} ---
Tytuł: {chunk['title']}
Autor: {chunk.get('author', 'Nieznany')}
Lokalizacja: {chunk.get('location', 'Nieznana')}

Treść:
{chunk['fragment'][:500]}...
"""
            formatted.append(text)
        
        return "\n".join(formatted)


if __name__ == "__main__":
    agent = AgentService()
    
    while True:
        question = input("\nZadaj pytanie (lub 'exit'): ")
        if question.lower() == 'exit':
            break
        
        answer = agent.ask(question)
        print(f"\n[ANSWER]\n{answer}")
