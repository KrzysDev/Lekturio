from pydantic import BaseModel, Field


class QuestionAnswer(BaseModel):
    question: str = Field(description="Pytanie dotyczące treści podanego fragmentu książki")
    answer: str = Field(description="Zwięzła, merytoryczna odpowiedź na pytanie na podstawie fragmentu")
    quote_from_book: str = Field(description="Dokładny cytat lub fragment tekstu z książki potwierdzający odpowiedź")


class QuestionAnswerSet(BaseModel):
    qa_pairs: list[QuestionAnswer] = Field(
        default_factory=list,
        description="Lista od 2 do 5 pytań i odpowiedzi na podstawie tekstu bieżącej strony, lub pusta lista jeśli strona jest pusta/tytułowa"
    )
    summary: str = Field(
        default="",
        description="Zwięzłe podsumowanie (2-3 zdania) wydarzeń z tej strony w kontekście dotychczasowej fabuły, służące jako kontekst dla kolejnych stron"
    )
