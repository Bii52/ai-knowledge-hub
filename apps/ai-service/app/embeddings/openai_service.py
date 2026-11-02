"""OpenAI embedding service implementation using AsyncOpenAI."""

from typing import List
import openai

from app.core.config import get_settings
from app.embeddings.base import BaseEmbeddingService


class OpenAIEmbeddingService(BaseEmbeddingService):
    """Embedding service integrating with OpenAI Embeddings API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        dimension: int | None = None,
    ) -> None:
        """Initialize OpenAI embedding client.

        Args:
            api_key: OpenAI API key. If omitted, loaded from settings.
            model: Embedding model name (default: text-embedding-3-small).
            dimension: Dimensionality of vector (default: 1536).
        """
        settings = get_settings()
        self._api_key = api_key or settings.OPENAI_API_KEY
        self._model = model or settings.EMBEDDING_MODEL
        self._dimension = dimension or settings.EMBEDDING_DIMENSION

        if not self._api_key:
            raise ValueError(
                "OpenAI API key is missing. Set OPENAI_API_KEY in .env or pass api_key explicitly."
            )

        self._client = openai.AsyncOpenAI(api_key=self._api_key)

    @property
    def dimension(self) -> int:
        """Return the vector dimensionality."""
        return self._dimension

    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding vector for a single text using OpenAI API."""
        cleaned_text = text.replace("\n", " ").strip()
        if not cleaned_text:
            return [0.0] * self._dimension

        response = await self._client.embeddings.create(
            input=cleaned_text,
            model=self._model,
        )
        return response.data[0].embedding

    async def embed_batch(
        self, texts: List[str], batch_size: int = 100
    ) -> List[List[float]]:
        """Generate embeddings for a list of texts in safe sub-batches.

        Args:
            texts: List of text strings to embed.
            batch_size: Maximum texts per API request (default: 100).

        Returns:
            List of embedding vectors.
        """
        if not texts:
            return []

        all_embeddings: List[List[float]] = []

        for i in range(0, len(texts), batch_size):
            chunk_texts = [
                t.replace("\n", " ").strip() or " " for t in texts[i : i + batch_size]
            ]
            response = await self._client.embeddings.create(
                input=chunk_texts,
                model=self._model,
            )
            # OpenAI preserves the ordering in response.data
            sorted_data = sorted(response.data, key=lambda item: item.index)
            all_embeddings.extend([item.embedding for item in sorted_data])

        return all_embeddings

