from fastapi import APIRouter, HTTPException
from lekturio.models.schemas import AskRequest, AskResponse, SourceFragment
from lekturio.services.embeddings_service import EmbeddingsService
from lekturio.services.retrival_service import RetrivalService
from lekturio.services.ai_service import AiService

router = APIRouter(prefix="/retrieval", tags=["Retrieval"])

embeddings_service = EmbeddingsService()
retrieval_service = RetrivalService(embeddings_service)
ai_service = AiService()


@router.post("/ask", response_model=AskResponse, summary="Zapytaj asystenta Lekturio o lekturę")
def ask_question(request: AskRequest):
    user_query = request.query.strip()
    if not user_query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    # 1. Expand query via LLM (HyPE / multi-query)
    expanded_queries = ai_service.generate_search_queries(user_query)
    all_queries = [user_query] + expanded_queries

    # 2. Retrieve chunks from PostgreSQL pgvector
    retrieved_chunks: dict[str, dict] = {}
    for q in all_queries:
        for r in retrieval_service.get_similar_by_questions(q, limit=2):
            if r["similarity"] >= 0.45:
                retrieved_chunks[r["id"]] = r

        for r in retrieval_service.get_similar_by_chunk_text(q, limit=2):
            if r["similarity"] >= 0.45:
                retrieved_chunks[r["id"]] = r

    if not retrieved_chunks:
        return AskResponse(
            query=user_query,
            answer="W bazie wiedzy nie odnaleziono wystarczających fragmentów, aby odpowiedzieć na to pytanie.",
            sources=[],
        )

    # 3. Build context for Bielik LLM
    context_blocks = []
    source_items = []

    for c in retrieved_chunks.values():
        author = f" ({c['author']})" if c.get("author") else ""
        context_blocks.append(
            f"--- ŹRÓDŁO: {c['title']}{author} | Część/Fragment #{c['chunk_index']} (ID: {c['id']}) ---\n"
            f"{c['fragment']}\n"
        )
        source_items.append(
            SourceFragment(
                id=c["id"],
                title=c["title"],
                author=c.get("author"),
                chunk_index=c["chunk_index"],
                similarity=c["similarity"],
                fragment=c["fragment"],
            )
        )

    context_str = "\n\n".join(context_blocks)

    # 4. Generate Answer
    answer = ai_service.answer_query(user_query=user_query, context=context_str)

    return AskResponse(
        query=user_query,
        answer=answer,
        sources=source_items,
    )


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

