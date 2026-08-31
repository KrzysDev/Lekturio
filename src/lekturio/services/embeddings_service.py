import ollama



class EmbeddingsService:
    def __init__(self):
        pass

    def embed_text(self, text: str):
        response = ollama.embed(
            model='qwen3-embedding:8b',
            input='The sky is blue because of Rayleigh scattering',
        )
        return response.embeddings


if __name__ == "__main__":
    service = EmbeddingsService()

    print(service.embed_text("Siala baba mak, something something, lorem ipsum"))