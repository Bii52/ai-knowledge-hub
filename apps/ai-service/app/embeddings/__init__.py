"""Embeddings package exposing service interfaces and factory."""

from app.embeddings.base import BaseEmbeddingService
from app.embeddings.factory import get_embedding_service
from app.embeddings.mock_service import MockEmbeddingService
from app.embeddings.openai_service import OpenAIEmbeddingService

__all__ = [
    "BaseEmbeddingService",
    "OpenAIEmbeddingService",
    "MockEmbeddingService",
    "get_embedding_service",
]

