"""FastAPI router for the RAG query endpoint (POST /api/v1/query)."""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator
import uuid as uuid_module

from app.pipeline.rag import RAGQueryResult, process_rag_query

logger = logging.getLogger(__name__)

router = APIRouter(tags=["RAG Query"])


# ─────────────────────────────────────────────
# Request & Response Schemas
# ─────────────────────────────────────────────


class QueryRequest(BaseModel):
    """Request schema for the RAG query endpoint."""

    workspace_id: str = Field(
        ...,
        description="UUID of the workspace to search within.",
        min_length=36,
        max_length=36,
    )
    query: str = Field(
        ...,
        description="Natural language question from the user.",
        min_length=1,
        max_length=2000,
    )
    document_ids: Optional[List[str]] = Field(
        default=None,
        description="Optional list of document UUIDs to restrict search scope.",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of chunks to retrieve (1–20).",
    )
    similarity_threshold: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum cosine similarity score (0.0 = no filter, 0.7 = strict).",
    )

    @field_validator("workspace_id")
    @classmethod
    def validate_workspace_uuid(cls, v: str) -> str:
        """Ensure workspace_id is a valid UUID."""
        try:
            uuid_module.UUID(v)
        except ValueError as exc:
            raise ValueError(f"'{v}' is not a valid UUID.") from exc
        return v

    @field_validator("document_ids")
    @classmethod
    def validate_document_uuids(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Ensure all document_ids are valid UUIDs if provided."""
        if v is None:
            return v
        for doc_id in v:
            try:
                uuid_module.UUID(doc_id)
            except ValueError as exc:
                raise ValueError(f"document_id '{doc_id}' is not a valid UUID.") from exc
        return v

    @field_validator("query")
    @classmethod
    def strip_query(cls, v: str) -> str:
        """Strip whitespace from query."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("query cannot be blank.")
        return stripped


class ChunkResult(BaseModel):
    """A single retrieved chunk in the query response."""

    chunk_id: str = Field(..., description="UUID of the document chunk.")
    document_id: str = Field(..., description="UUID of the parent document.")
    content: str = Field(..., description="Text content of the chunk.")
    page_number: Optional[int] = Field(None, description="Page number in the original document.")
    chunk_index: int = Field(..., description="Zero-based sequential index of this chunk.")
    similarity: float = Field(..., description="Cosine similarity score (0.0–1.0).")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional chunk metadata.")


class QueryResponse(BaseModel):
    """Response schema for the RAG query endpoint."""

    query: str = Field(..., description="The original user query.")
    workspace_id: str = Field(..., description="UUID of the workspace searched.")
    total: int = Field(..., description="Number of chunks retrieved.")
    results: List[ChunkResult] = Field(..., description="Ranked list of relevant chunks.")


# ─────────────────────────────────────────────
# Endpoint
# ─────────────────────────────────────────────


@router.post(
    "/query",
    response_model=QueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve semantically relevant document chunks (RAG)",
    description=(
        "Embeds the user's query into a 1536-dim vector, performs cosine similarity "
        "search on document_chunks strictly scoped to the provided workspace_id, and "
        "returns the top-K most relevant chunks with their similarity scores and citations. "
        "Called by the NestJS API when a user sends a chat message."
    ),
)
async def query_documents(request: QueryRequest) -> QueryResponse:
    """Execute RAG retrieval pipeline for a user question."""
    logger.info(
        "POST /api/v1/query — workspace_id=%s, top_k=%d, query_len=%d",
        request.workspace_id,
        request.top_k,
        len(request.query),
    )

    try:
        result: RAGQueryResult = await process_rag_query(
            workspace_id=request.workspace_id,
            query=request.query,
            document_ids=request.document_ids,
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold,
        )
    except ValueError as exc:
        logger.warning("RAG query validation error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("RAG query pipeline failed for workspace %s", request.workspace_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG query pipeline failed: {exc}",
        ) from exc

    return QueryResponse(
        query=result.query,
        workspace_id=result.workspace_id,
        total=result.total,
        results=[
            ChunkResult(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                content=chunk.content,
                page_number=chunk.page_number,
                chunk_index=chunk.chunk_index,
                similarity=chunk.similarity,
                metadata=chunk.metadata,
            )
            for chunk in result.results
        ],
    )

