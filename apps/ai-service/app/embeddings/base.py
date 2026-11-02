"""Abstract base class and interface for embedding services."""

from abc import ABC, abstractmethod
from typing import List


class BaseEmbeddingService(ABC):
    """Interface for text embedding providers."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the vector dimensionality (e.g., 1536)."""
        pass

    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """Generate a vector embedding for a single text string.

        Args:
            text: Input text string to embed.

        Returns:
            List of floats representing the embedding vector.
        """
        pass

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate vector embeddings for a batch of text strings.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of vector embeddings corresponding to each input text.
        """
        pass

