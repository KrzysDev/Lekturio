from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from lekturio.api.routers.retrival_router import router as retrival_router
from lekturio.api.routers.agent_router import router as agent_router

app = FastAPI(
    title="Lekturio API",
    description="System RAG (HyPE + Dual Embeddings) wspomagający naukę i analizę lektur szkolnych.",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(retrival_router)
app.include_router(agent_router)


@app.get("/", summary="Status API")
def root():
    return {
        "status": "online",
        "service": "Lekturio API",
        "version": "0.1.0",
        "docs_url": "/docs",
    }


@app.get("/health", summary="Healthcheck")
def healthcheck():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("lekturio.main:app", host="0.0.0.0", port=8000, reload=True)

