from fastapi import APIRouter, HTTPException
from lekturio.models.schemas import AskRequest, AskResponse, SourceFragment
from lekturio.services.embeddings_service import EmbeddingsService
from lekturio.services.retrival_service import RetrivalService
from lekturio.services.ai_service import AiService

router = APIRouter(prefix="/retrieval", tags=["Retrieval"])

embeddings_service = EmbeddingsService()
retrieval_service = RetrivalService(embeddings_service)
ai_service = AiService()

@router.post("/search", response_model=list[SourceFragment], summary="Wyszukaj relewantne fragmenty w bazie")
def search_chunks(request: AskRequest):
    user_query = request.query.strip()
    if not user_query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    results: dict[str, dict] = {}

    for r in retrieval_service.get_similar_by_questions(user_query, limit=5):
        results[r["id"]] = r

    for r in retrieval_service.get_similar_by_chunk_text(user_query, limit=5):
        if r["id"] not in results or r["similarity"] > results[r["id"]]["similarity"]:
            results[r["id"]] = r

    sorted_results = sorted(results.values(), key=lambda x: x["similarity"], reverse=True)

    return [
        SourceFragment(
            id=c["id"],
            title=c["title"],
            author=c.get("author"),
            chunk_index=c["chunk_index"],
            similarity=c["similarity"],
            fragment=c["fragment"],
        )
        for c in sorted_results[:5]
    ]

