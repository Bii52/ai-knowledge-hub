"""Unit tests for the RAG query pipeline and API endpoint."""

import asyncio
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.pipeline.rag import RAGQueryResult, RetrievedChunk, process_rag_query

# ─────────────────────────────────────────────
# Test Fixtures
# ─────────────────────────────────────────────

VALID_WORKSPACE_ID = str(uuid.uuid4())
VALID_DOC_ID_1 = str(uuid.uuid4())
VALID_DOC_ID_2 = str(uuid.uuid4())
VALID_CHUNK_ID = str(uuid.uuid4())

SAMPLE_DB_RESULTS = [
    {
        "chunk_id": VALID_CHUNK_ID,
        "document_id": VALID_DOC_ID_1,
        "workspace_id": VALID_WORKSPACE_ID,
        "content": "Refunds are processed within 5-7 business days after receiving the returned item.",
        "page_number": 3,
        "chunk_index": 7,
        "similarity": 0.92,
        "metadata": {"source": "policy.pdf"},
    },
    {
        "chunk_id": str(uuid.uuid4()),
        "document_id": VALID_DOC_ID_2,
        "workspace_id": VALID_WORKSPACE_ID,
        "content": "Items must be returned in original condition to qualify for a full refund.",
        "page_number": 4,
        "chunk_index": 8,
        "similarity": 0.85,
        "metadata": {},
    },
]

client = TestClient(app, raise_server_exceptions=False)


# ─────────────────────────────────────────────
# Pipeline Unit Tests
# ─────────────────────────────────────────────


def test_rag_pipeline_raises_on_empty_workspace_id():
    """Pipeline must raise ValueError when workspace_id is empty."""
    with pytest.raises(ValueError, match="workspace_id is required"):
        asyncio.run(process_rag_query(workspace_id="", query="What is the refund policy?"))


def test_rag_pipeline_raises_on_empty_query():
    """Pipeline must raise ValueError when query is blank."""
    with pytest.raises(ValueError, match="Query text cannot be empty"):
        asyncio.run(process_rag_query(workspace_id=VALID_WORKSPACE_ID, query="   "))


def test_rag_pipeline_success_returns_ranked_chunks():
    """Happy-path: pipeline returns RAGQueryResult with ranked chunks."""

    async def fake_embed_text(text: str):
        return [0.1] * 1536

    async def fake_get_pool():
        return MagicMock()

    async def fake_search(*args, **kwargs):
        return SAMPLE_DB_RESULTS

    with (
        patch("app.pipeline.rag.get_embedding_service") as mock_embed_factory,
        patch("app.pipeline.rag.get_db_pool") as mock_pool,
        patch("app.pipeline.rag.search_similar_chunks") as mock_search,
    ):
        mock_embed_service = MagicMock()
        mock_embed_service.embed_text = fake_embed_text
        mock_embed_factory.return_value = mock_embed_service
        mock_pool.side_effect = fake_get_pool
        mock_search.side_effect = fake_search

        result = asyncio.run(
            process_rag_query(
                workspace_id=VALID_WORKSPACE_ID,
                query="What is the refund policy?",
                top_k=5,
            )
        )

    assert isinstance(result, RAGQueryResult)
    assert result.query == "What is the refund policy?"
    assert result.workspace_id == VALID_WORKSPACE_ID
    assert result.total == 2
    assert isinstance(result.results[0], RetrievedChunk)
    assert result.results[0].similarity == 0.92
    assert result.results[0].page_number == 3


def test_rag_pipeline_passes_document_ids_filter():
    """Pipeline must pass document_ids filter down to search_similar_chunks."""
    captured_kwargs = {}

    async def fake_embed_text(text: str):
        return [0.1] * 1536

    async def fake_get_pool():
        return MagicMock()

    async def fake_search(pool, workspace_id, query_embedding, limit, document_ids, similarity_threshold):
        captured_kwargs["document_ids"] = document_ids
        captured_kwargs["limit"] = limit
        captured_kwargs["similarity_threshold"] = similarity_threshold
        return []

    with (
        patch("app.pipeline.rag.get_embedding_service") as mock_embed_factory,
        patch("app.pipeline.rag.get_db_pool") as mock_pool,
        patch("app.pipeline.rag.search_similar_chunks") as mock_search,
    ):
        mock_embed_service = MagicMock()
        mock_embed_service.embed_text = fake_embed_text
        mock_embed_factory.return_value = mock_embed_service
        mock_pool.side_effect = fake_get_pool
        mock_search.side_effect = fake_search

        asyncio.run(
            process_rag_query(
                workspace_id=VALID_WORKSPACE_ID,
                query="test query",
                document_ids=[VALID_DOC_ID_1],
                top_k=3,
                similarity_threshold=0.5,
            )
        )

    assert captured_kwargs["document_ids"] == [VALID_DOC_ID_1]
    assert captured_kwargs["limit"] == 3
    assert captured_kwargs["similarity_threshold"] == 0.5


def test_rag_pipeline_empty_results():
    """Pipeline returns empty results without error when no chunks match."""

    async def fake_embed_text(text: str):
        return [0.0] * 1536

    async def fake_get_pool():
        return MagicMock()

    async def fake_search(*args, **kwargs):
        return []

    with (
        patch("app.pipeline.rag.get_embedding_service") as mock_embed_factory,
        patch("app.pipeline.rag.get_db_pool") as mock_pool,
        patch("app.pipeline.rag.search_similar_chunks") as mock_search,
    ):
        mock_embed_service = MagicMock()
        mock_embed_service.embed_text = fake_embed_text
        mock_embed_factory.return_value = mock_embed_service
        mock_pool.side_effect = fake_get_pool
        mock_search.side_effect = fake_search

        result = asyncio.run(
            process_rag_query(workspace_id=VALID_WORKSPACE_ID, query="Something obscure")
        )

    assert result.total == 0
    assert result.results == []


# ─────────────────────────────────────────────
# API Endpoint Tests
# ─────────────────────────────────────────────


def test_query_endpoint_invalid_workspace_uuid_returns_422():
    """Endpoint must reject non-UUID workspace_id with 422."""
    response = client.post(
        "/api/v1/query",
        json={
            "workspace_id": "not-a-uuid",
            "query": "What is the refund policy?",
        },
    )
    assert response.status_code == 422


def test_query_endpoint_blank_query_returns_422():
    """Endpoint must reject blank query string with 422."""
    response = client.post(
        "/api/v1/query",
        json={
            "workspace_id": VALID_WORKSPACE_ID,
            "query": "   ",
        },
    )
    assert response.status_code == 422


def test_query_endpoint_top_k_out_of_range_returns_422():
    """Endpoint must reject top_k > 20 with 422."""
    response = client.post(
        "/api/v1/query",
        json={
            "workspace_id": VALID_WORKSPACE_ID,
            "query": "test query",
            "top_k": 999,
        },
    )
    assert response.status_code == 422


def test_query_endpoint_invalid_document_id_in_list_returns_422():
    """Endpoint must reject invalid UUIDs in document_ids list with 422."""
    response = client.post(
        "/api/v1/query",
        json={
            "workspace_id": VALID_WORKSPACE_ID,
            "query": "test query",
            "document_ids": ["not-a-valid-uuid"],
        },
    )
    assert response.status_code == 422


def test_query_endpoint_success_returns_200():
    """Happy-path: endpoint returns 200 with QueryResponse."""
    mock_result = RAGQueryResult(
        query="What is the refund policy?",
        workspace_id=VALID_WORKSPACE_ID,
        results=[
            RetrievedChunk(
                chunk_id=VALID_CHUNK_ID,
                document_id=VALID_DOC_ID_1,
                content="Refunds are processed within 5-7 business days.",
                page_number=3,
                chunk_index=7,
                similarity=0.92,
                metadata={"source": "policy.pdf"},
            )
        ],
    )

    with patch("app.api.v1.query.process_rag_query") as mock_pipeline:
        async def fake_pipeline(*args, **kwargs):
            return mock_result

        mock_pipeline.side_effect = fake_pipeline

        response = client.post(
            "/api/v1/query",
            json={
                "workspace_id": VALID_WORKSPACE_ID,
                "query": "What is the refund policy?",
                "top_k": 5,
                "similarity_threshold": 0.0,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "What is the refund policy?"
    assert body["workspace_id"] == VALID_WORKSPACE_ID
    assert body["total"] == 1
    assert len(body["results"]) == 1
    assert body["results"][0]["similarity"] == 0.92
    assert body["results"][0]["page_number"] == 3
    assert body["results"][0]["content"] == "Refunds are processed within 5-7 business days."


def test_query_endpoint_pipeline_failure_returns_500():
    """If pipeline raises an exception, endpoint must return 500."""
    with patch("app.api.v1.query.process_rag_query") as mock_pipeline:
        async def fail(*args, **kwargs):
            raise RuntimeError("Database connection lost")

        mock_pipeline.side_effect = fail

        response = client.post(
            "/api/v1/query",
            json={
                "workspace_id": VALID_WORKSPACE_ID,
                "query": "What happened?",
            },
        )

    assert response.status_code == 500
    assert "Database connection lost" in response.json()["detail"]

