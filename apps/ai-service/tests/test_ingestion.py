"""Unit and integration tests for the document ingestion pipeline and API endpoint."""

import io
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.chunking.models import Chunk, ChunkingResult
from app.extractors.base import ExtractionResult, ExtractedPage
from app.main import app

# ─────────────────────────────────────────────────────────────────────────────
# Test Fixtures & Helpers
# ─────────────────────────────────────────────────────────────────────────────

VALID_DOCUMENT_ID = str(uuid.uuid4())
VALID_WORKSPACE_ID = str(uuid.uuid4())
VALID_STORAGE_PATH = "workspaces/test-workspace/document.pdf"

SAMPLE_EXTRACTION = ExtractionResult(
    pages=[
        ExtractedPage(page_number=1, text="Artificial intelligence is transforming knowledge management."),
        ExtractedPage(page_number=2, text="RAG pipelines enable accurate and cited answers from private documents."),
    ]
)

SAMPLE_CHUNKS = [
    Chunk(
        text="Artificial intelligence is transforming knowledge management.",
        chunk_index=0,
        page_number=1,
        char_count=61,
        metadata={"page_number": 1},
    ),
    Chunk(
        text="RAG pipelines enable accurate and cited answers from private documents.",
        chunk_index=1,
        page_number=2,
        char_count=70,
        metadata={"page_number": 2},
    ),
]

SAMPLE_CHUNKING_RESULT = ChunkingResult(
    chunks=SAMPLE_CHUNKS,
    document_id="",
    total_pages=2,
)

SAMPLE_EMBEDDINGS = [[0.1] * 1536, [0.2] * 1536]


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline Unit Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_pipeline_raises_on_empty_extraction():
    """If extractor returns zero pages, pipeline must raise ValueError."""
    import asyncio
    from app.pipeline.ingestion import process_document_ingestion

    empty_extraction = ExtractionResult(pages=[])

    with (
        patch("app.pipeline.ingestion.get_storage_client") as mock_storage,
        patch("app.pipeline.ingestion.get_extractor") as mock_extractor_factory,
    ):
        mock_storage.return_value.download_file.return_value = b"fake-pdf-bytes"
        mock_extractor = MagicMock()
        mock_extractor.extract.return_value = empty_extraction
        mock_extractor_factory.return_value = mock_extractor

        with pytest.raises(ValueError, match="no extractable text"):
            asyncio.run(
                process_document_ingestion(
                    document_id=VALID_DOCUMENT_ID,
                    workspace_id=VALID_WORKSPACE_ID,
                    storage_path=VALID_STORAGE_PATH,
                    file_type="PDF",
                )
            )


def test_pipeline_success_returns_ingest_result():
    """Happy-path: pipeline completes all 5 steps and returns IngestResult."""
    import asyncio
    from app.pipeline.ingestion import process_document_ingestion, IngestResult

    with (
        patch("app.pipeline.ingestion.get_storage_client") as mock_storage,
        patch("app.pipeline.ingestion.get_extractor") as mock_extractor_factory,
        patch("app.pipeline.ingestion.RecursiveCharacterChunker") as mock_chunker_cls,
        patch("app.pipeline.ingestion.get_embedding_service") as mock_embed_factory,
        patch("app.pipeline.ingestion.get_db_pool") as mock_pool,
        patch("app.pipeline.ingestion.save_document_chunks") as mock_save,
    ):
        # Mock Step 1: S3 download
        mock_storage.return_value.download_file.return_value = b"fake-bytes"

        # Mock Step 2: Text extraction
        mock_extractor = MagicMock()
        mock_extractor.extract.return_value = SAMPLE_EXTRACTION
        mock_extractor_factory.return_value = mock_extractor

        # Mock Step 3: Chunking
        mock_chunker = MagicMock()
        mock_chunker.chunk_document.return_value = SAMPLE_CHUNKING_RESULT
        mock_chunker_cls.return_value = mock_chunker

        # Mock Step 4: Embeddings (async)
        async def fake_embed_batch(texts):
            return SAMPLE_EMBEDDINGS

        mock_embed_service = MagicMock()
        mock_embed_service.embed_batch = fake_embed_batch
        mock_embed_factory.return_value = mock_embed_service

        # Mock Step 5: DB save (async)
        async def fake_get_pool():
            return MagicMock()

        async def fake_save(*args, **kwargs):
            return 2

        mock_pool.side_effect = fake_get_pool
        mock_save.side_effect = fake_save

        result = asyncio.run(
            process_document_ingestion(
                document_id=VALID_DOCUMENT_ID,
                workspace_id=VALID_WORKSPACE_ID,
                storage_path=VALID_STORAGE_PATH,
                file_type="PDF",
            )
        )

    assert isinstance(result, IngestResult)
    assert result.document_id == VALID_DOCUMENT_ID
    assert result.workspace_id == VALID_WORKSPACE_ID
    assert result.chunks_count == 2
    assert result.status == "completed"


# ─────────────────────────────────────────────────────────────────────────────
# API Endpoint Tests (via FastAPI TestClient)
# ─────────────────────────────────────────────────────────────────────────────

client = TestClient(app, raise_server_exceptions=False)


def test_ingest_endpoint_invalid_uuid_returns_422():
    """Endpoint must reject non-UUID document_id with 422 Unprocessable Entity."""
    response = client.post(
        "/api/v1/ingest",
        json={
            "document_id": "not-a-uuid",
            "workspace_id": VALID_WORKSPACE_ID,
            "storage_path": VALID_STORAGE_PATH,
            "file_type": "PDF",
        },
    )
    assert response.status_code == 422


def test_ingest_endpoint_unsupported_file_type_returns_422():
    """Endpoint must reject unsupported file types (e.g., XLSX) with 422."""
    response = client.post(
        "/api/v1/ingest",
        json={
            "document_id": VALID_DOCUMENT_ID,
            "workspace_id": VALID_WORKSPACE_ID,
            "storage_path": VALID_STORAGE_PATH,
            "file_type": "XLSX",
        },
    )
    assert response.status_code == 422


def test_ingest_endpoint_empty_storage_path_returns_422():
    """Endpoint must reject blank storage_path with 422."""
    response = client.post(
        "/api/v1/ingest",
        json={
            "document_id": VALID_DOCUMENT_ID,
            "workspace_id": VALID_WORKSPACE_ID,
            "storage_path": "   ",
            "file_type": "PDF",
        },
    )
    assert response.status_code == 422


def test_ingest_endpoint_success():
    """Happy-path: endpoint returns 200 with IngestResponse when pipeline succeeds."""
    from app.pipeline.ingestion import IngestResult

    mock_result = IngestResult(
        document_id=VALID_DOCUMENT_ID,
        workspace_id=VALID_WORKSPACE_ID,
        chunks_count=5,
        status="completed",
        message="Document ingested and indexed successfully (5 chunks).",
    )

    with patch("app.api.v1.ingest.process_document_ingestion") as mock_pipeline:
        async def fake_pipeline(*args, **kwargs):
            return mock_result

        mock_pipeline.side_effect = fake_pipeline

        response = client.post(
            "/api/v1/ingest",
            json={
                "document_id": VALID_DOCUMENT_ID,
                "workspace_id": VALID_WORKSPACE_ID,
                "storage_path": VALID_STORAGE_PATH,
                "file_type": "PDF",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["document_id"] == VALID_DOCUMENT_ID
    assert body["workspace_id"] == VALID_WORKSPACE_ID
    assert body["chunks_count"] == 5
    assert body["status"] == "completed"


def test_ingest_endpoint_pipeline_error_returns_500():
    """If pipeline raises an Exception, endpoint must return 500."""
    with patch("app.api.v1.ingest.process_document_ingestion") as mock_pipeline:
        async def fail_pipeline(*args, **kwargs):
            raise RuntimeError("S3 connection refused")

        mock_pipeline.side_effect = fail_pipeline

        response = client.post(
            "/api/v1/ingest",
            json={
                "document_id": VALID_DOCUMENT_ID,
                "workspace_id": VALID_WORKSPACE_ID,
                "storage_path": VALID_STORAGE_PATH,
                "file_type": "PDF",
            },
        )

    assert response.status_code == 500
    assert "S3 connection refused" in response.json()["detail"]

