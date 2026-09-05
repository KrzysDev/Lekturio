from pydantic import BaseModel, Field


class QuestionAnswer(BaseModel):
    question: str = Field(description="Precyzyjne, kontekstowe pytanie egzaminacyjne z imionami bohaterów i tytułem lektury")
    answer: str = Field(description="Zwięzła, merytoryczna odpowiedź na pytanie na podstawie fragmentu tekstu")
    quote_from_book: str = Field(description="Dokładny cytat z podanego fragmentu potwierdzający odpowiedź")


class QuestionAnswerSet(BaseModel):
    qa_pairs: list[QuestionAnswer] = Field(
        description="Wymagana lista od 2 do 5 wygenerowanych pytań i odpowiedzi"
    )
    summary: str | None = Field(
        default=None,
        description="Opcjonalne krótkie podsumowanie"
    )


class AskRequest(BaseModel):
    query: str = Field(..., min_length=3, description="Pytanie użytkownika dotyczące lektury")


class SourceFragment(BaseModel):
    id: str
    title: str
    author: str | None = None
    chunk_index: int
    similarity: float
    fragment: str


class AskResponse(BaseModel):
    query: str
    answer: str
    sources: list[SourceFragment] = Field(default_factory=list)
