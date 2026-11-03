"""FastAPI router for the document ingestion endpoint (POST /api/v1/ingest)."""

import logging
from enum import Enum

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator
import uuid as uuid_module

from app.pipeline.ingestion import IngestResult, process_document_ingestion

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Ingestion"])


class SupportedFileType(str, Enum):
    """Supported document file types for ingestion."""

    PDF = "PDF"
    DOCX = "DOCX"
    TXT = "TXT"


class IngestRequest(BaseModel):
    """Request schema for the document ingestion endpoint."""

    document_id: str = Field(
        ...,
        description="UUID of the document record in PostgreSQL.",
        min_length=36,
        max_length=36,
    )
    workspace_id: str = Field(
        ...,
        description="UUID of the workspace that owns this document.",
        min_length=36,
        max_length=36,
    )
    storage_path: str = Field(
        ...,
        description="Storage path/key of the file in the S3 bucket.",
        min_length=1,
    )
    file_type: SupportedFileType = Field(
        ...,
        description="Type of document file: PDF, DOCX, or TXT.",
    )

    @field_validator("document_id", "workspace_id")
    @classmethod
    def validate_uuid(cls, v: str) -> str:
        """Ensure document_id and workspace_id are valid UUID strings."""
        try:
            uuid_module.UUID(v)
        except ValueError as exc:
            raise ValueError(f"'{v}' is not a valid UUID.") from exc
        return v

    @field_validator("storage_path")
    @classmethod
    def validate_storage_path(cls, v: str) -> str:
        """Remove leading/trailing whitespace from storage path."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("storage_path cannot be blank.")
        return stripped


class IngestResponse(BaseModel):
    """Response schema returned after successful ingestion."""

    document_id: str = Field(..., description="UUID of the ingested document.")
    workspace_id: str = Field(..., description="UUID of the workspace.")
    status: str = Field(..., description="Pipeline status: 'completed' or 'failed'.")
    chunks_count: int = Field(..., description="Number of chunks saved to pgvector.")
    message: str = Field(..., description="Human-readable result message.")


@router.post(
    "/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_200_OK,
    summary="Ingest a document into the RAG pipeline",
    description=(
        "Receives a document reference, downloads the file from S3, extracts text, "
        "chunks it semantically, generates vector embeddings, and saves to pgvector. "
        "Called by the NestJS BullMQ worker after a document is uploaded."
    ),
)
async def ingest_document(request: IngestRequest) -> IngestResponse:
    """Execute the full document ingestion pipeline."""
    logger.info(
        "POST /api/v1/ingest — document_id=%s, workspace_id=%s, file_type=%s",
        request.document_id,
        request.workspace_id,
        request.file_type.value,
    )

    try:
        result: IngestResult = await process_document_ingestion(
            document_id=request.document_id,
            workspace_id=request.workspace_id,
            storage_path=request.storage_path,
            file_type=request.file_type.value,
        )
    except ValueError as exc:
        logger.error("Ingestion validation error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Ingestion pipeline failed for document %s", request.document_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion pipeline failed: {exc}",
        ) from exc

    return IngestResponse(
        document_id=result.document_id,
        workspace_id=result.workspace_id,
        status=result.status,
        chunks_count=result.chunks_count,
        message=result.message,
    )

