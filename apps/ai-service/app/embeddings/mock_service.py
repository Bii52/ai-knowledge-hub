"""Mock embedding service for offline development and deterministic unit testing."""

import hashlib
import math
import random
from typing import List

from app.embeddings.base import BaseEmbeddingService


class MockEmbeddingService(BaseEmbeddingService):
    """Deterministic mock embedding service producing normalized vectors."""

    def __init__(self, dimension: int = 1536) -> None:
        """Initialize mock embedding service.

        Args:
            dimension: Dimensionality of embedding vector (default: 1536).
        """
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        """Return the vector dimensionality."""
        return self._dimension

    def _generate_vector(self, text: str) -> List[float]:
        """Generate a deterministic unit-length vector from text using SHA256 seed.

        Args:
            text: Input string.

        Returns:
            L2-normalized float vector of length `self._dimension`.
        """
        if not text:
            # Return zero vector if text is empty
            return [0.0] * self._dimension

        # Derive 64-bit integer seed from SHA-256 hash of text
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        seed = int.from_bytes(digest[:8], byteorder="big")

        rng = random.Random(seed)
        # Sample numbers from standard normal distribution
        raw_vector = [rng.gauss(0.0, 1.0) for _ in range(self._dimension)]

        # L2-normalize to ensure unit length (norm = 1.0) for cosine similarity
        norm = math.sqrt(sum(x * x for x in raw_vector))
        if norm == 0.0:
            return raw_vector

        return [x / norm for x in raw_vector]

    async def embed_text(self, text: str) -> List[float]:
        """Generate mock embedding for a single text string."""
        return self._generate_vector(text)

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate mock embeddings for a batch of text strings."""
        return [self._generate_vector(t) for t in texts]

