from fastapi import APIRouter, HTTPException
from lekturio.models.schemas import AskRequest, AskResponse, SourceFragment
from lekturio.services.agent_service import AgentService

router = APIRouter(prefix="/agent", tags=["Agent"])
agent = AgentService()


@router.post("/ask", response_model=AskResponse)
def ask_agent(request: AskRequest):
    """Zadaj pytanie agentowi."""
    question = request.query.strip()
    
    if not question:
        raise HTTPException(status_code=400, detail="Pytanie nie może być puste")
    
    try:
        answer = agent.ask(question)
        
        return AskResponse(
            query=question,
            answer=answer,
            sources=[]  # Agent nie zwraca źródeł w tym momencie
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Błąd agenta: {str(e)}")
