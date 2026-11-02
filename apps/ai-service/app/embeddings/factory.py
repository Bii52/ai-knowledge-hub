"""Factory for selecting and instantiating embedding services."""

import logging
from app.core.config import get_settings
from app.embeddings.base import BaseEmbeddingService
from app.embeddings.mock_service import MockEmbeddingService
from app.embeddings.openai_service import OpenAIEmbeddingService

logger = logging.getLogger(__name__)


def get_embedding_service(
    provider: str | None = None,
) -> BaseEmbeddingService:
    """Retrieve an embedding service instance based on provider or configuration.

    Args:
        provider: Provider identifier ('openai', 'mock', or None for auto-detection).

    Returns:
        Instance conforming to BaseEmbeddingService.
    """
    settings = get_settings()

    if provider == "mock":
        return MockEmbeddingService(dimension=settings.EMBEDDING_DIMENSION)

    if provider == "openai":
        return OpenAIEmbeddingService()

    # Auto-detection: Use OpenAI if API key is present, otherwise fallback to Mock
    if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.strip():
        logger.info("Using OpenAIEmbeddingService with model: %s", settings.EMBEDDING_MODEL)
        return OpenAIEmbeddingService()

    logger.warning("OPENAI_API_KEY not configured. Falling back to MockEmbeddingService.")
    return MockEmbeddingService(dimension=settings.EMBEDDING_DIMENSION)

