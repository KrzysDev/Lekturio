import ollama



class EmbeddingsService:
    def __init__(self):
        pass

    def embed_text(self, text: str):
        response = ollama.embed(
            model='qwen3-embedding:8b',
            input=text,
        )
        return response.embeddings


if __name__ == "__main__":
    service = EmbeddingsService()

    print(len(service.embed_text("Siala baba mak, something something, lorem ipsum")[0]))