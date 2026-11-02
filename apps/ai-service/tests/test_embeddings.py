"""Unit tests for embedding services and vector operations."""

import asyncio
import math
import pytest
from unittest.mock import patch

from app.chunking.models import Chunk
from app.core.database import save_document_chunks, search_similar_chunks
from app.embeddings.factory import get_embedding_service
from app.embeddings.mock_service import MockEmbeddingService
from app.embeddings.openai_service import OpenAIEmbeddingService


def test_mock_embedding_dimension():
    """Verify that MockEmbeddingService reports and produces 1536-dim vectors."""
    service = MockEmbeddingService(dimension=1536)
    assert service.dimension == 1536

    vec = asyncio.run(service.embed_text("Hello AI Knowledge Hub"))
    assert len(vec) == 1536
    assert isinstance(vec[0], float)


def test_mock_embedding_unit_norm():
    """Verify that generated vectors are L2-normalized (unit length)."""
    service = MockEmbeddingService(dimension=1536)
    vec = asyncio.run(service.embed_text("Testing vector normalization for cosine similarity"))

    norm = math.sqrt(sum(x * x for x in vec))
    assert pytest.approx(norm, abs=1e-5) == 1.0


def test_mock_embedding_determinism():
    """Verify that the same input yields identical vectors and different inputs differ."""
    service = MockEmbeddingService(dimension=1536)

    vec1 = asyncio.run(service.embed_text("Consistent query"))
    vec2 = asyncio.run(service.embed_text("Consistent query"))
    vec3 = asyncio.run(service.embed_text("Completely different query"))

    assert vec1 == vec2
    assert vec1 != vec3


def test_mock_embedding_empty_text():
    """Verify that empty text generates a zero vector."""
    service = MockEmbeddingService(dimension=1536)
    vec = asyncio.run(service.embed_text(""))

    assert len(vec) == 1536
    assert all(x == 0.0 for x in vec)


def test_mock_embedding_batch():
    """Verify batch embedding generation preserves count and dimensions."""
    service = MockEmbeddingService(dimension=1536)
    texts = ["Paragraph one", "Paragraph two", "Paragraph three"]

    vectors = asyncio.run(service.embed_batch(texts))
    assert len(vectors) == 3
    for v in vectors:
        assert len(v) == 1536
        norm = math.sqrt(sum(x * x for x in v))
        assert pytest.approx(norm, abs=1e-5) == 1.0


def test_factory_mock_provider():
    """Verify factory returns MockEmbeddingService when provider='mock'."""
    service = get_embedding_service(provider="mock")
    assert isinstance(service, MockEmbeddingService)
    assert service.dimension == 1536


def test_factory_auto_fallback_to_mock():
    """Verify factory falls back to MockEmbeddingService when OPENAI_API_KEY is empty."""
    with patch("app.embeddings.factory.get_settings") as mock_settings:
        mock_settings.return_value.OPENAI_API_KEY = ""
        mock_settings.return_value.EMBEDDING_DIMENSION = 1536
        service = get_embedding_service()
        assert isinstance(service, MockEmbeddingService)


def test_openai_service_missing_key_raises_error():
    """Verify OpenAIEmbeddingService raises ValueError when API key is missing."""
    with patch("app.embeddings.openai_service.get_settings") as mock_settings:
        mock_settings.return_value.OPENAI_API_KEY = ""
        mock_settings.return_value.EMBEDDING_MODEL = "text-embedding-3-small"
        mock_settings.return_value.EMBEDDING_DIMENSION = 1536

        with pytest.raises(ValueError, match="OpenAI API key is missing"):
            OpenAIEmbeddingService(api_key="")


def test_save_chunks_validation_count_mismatch():
    """Verify save_document_chunks raises ValueError if chunks and embeddings length differ."""
    chunks = [
        Chunk(
            text="Test chunk",
            chunk_index=0,
            page_number=1,
            char_count=10,
            metadata={},
        )
    ]
    embeddings = []  # Empty embeddings

    with pytest.raises(ValueError, match="does not match embedding count"):
        asyncio.run(save_document_chunks(None, "doc-1", "ws-1", chunks, embeddings))


def test_search_similar_chunks_requires_workspace_id():
    """Verify search_similar_chunks enforces workspace_id requirement for data isolation."""
    query_vec = [0.1] * 1536
    with pytest.raises(ValueError, match="workspace_id is strictly required"):
        asyncio.run(search_similar_chunks(None, "", query_vec))

