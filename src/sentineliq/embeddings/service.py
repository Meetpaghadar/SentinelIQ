from openai import OpenAI

from sentineliq.config import get_settings

EMBEDDING_DIMENSIONS = 1536


class EmbeddingService:
    def __init__(self) -> None:
        settings = get_settings()

        if settings.openai_api_key is None:
            raise RuntimeError("SENTINELIQ_OPENAI_API_KEY is required for embeddings")

        self._client = OpenAI(api_key=settings.openai_api_key)
        self._model = settings.embedding_model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        response = self._client.embeddings.create(
            model=self._model,
            input=texts,
            dimensions=EMBEDDING_DIMENSIONS,
        )

        embeddings = [item.embedding for item in response.data]

        if len(embeddings) != len(texts):
            raise RuntimeError("Embedding response count does not match input count")

        return embeddings

    def embed_query(self, query: str) -> list[float]:
        query = query.strip()

        if not query:
            raise ValueError("Query cannot be empty")

        return self.embed_texts([query])[0]
