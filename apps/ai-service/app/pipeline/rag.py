"""RAG (Retrieval-Augmented Generation) query pipeline."""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.core.database import get_db_pool, search_similar_chunks
from app.embeddings.factory import get_embedding_service

logger = logging.getLogger(__name__)

DEFAULT_TOP_K = 5
DEFAULT_SIMILARITY_THRESHOLD = 0.0


@dataclass
class RetrievedChunk:
    """A single chunk returned from vector similarity search."""

    chunk_id: str
    document_id: str
    content: str
    page_number: Optional[int]
    chunk_index: int
    similarity: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RAGQueryResult:
    """Result of a RAG retrieval query."""

    query: str
    workspace_id: str
    results: List[RetrievedChunk]

    @property
    def total(self) -> int:
        """Number of retrieved chunks."""
        return len(self.results)


async def process_rag_query(
    workspace_id: str,
    query: str,
    document_ids: Optional[List[str]] = None,
    top_k: int = DEFAULT_TOP_K,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    embedding_provider: Optional[str] = None,
) -> RAGQueryResult:
    """Execute the RAG retrieval pipeline for a user query.

    Steps:
        1. Generate vector embedding for the user's query text.
        2. Perform cosine similarity search on document_chunks scoped to workspace_id.
        3. Return ranked, relevant chunks as structured result.

    Security: workspace_id filtering is applied BEFORE vector search inside
    `search_similar_chunks()`, ensuring strict data isolation between workspaces.

    Args:
        workspace_id: UUID of the workspace — required for strict data isolation.
        query: Natural language question from the user.
        document_ids: Optional list of document UUIDs to restrict retrieval to.
        top_k: Maximum number of chunks to retrieve (default: 5).
        similarity_threshold: Minimum cosine similarity score to include (0.0 = all, 0.7 = strict).
        embedding_provider: Force 'openai', 'mock', or None for auto-detect.

    Returns:
        RAGQueryResult with ranked list of RetrievedChunk objects.

    Raises:
        ValueError: If workspace_id or query is empty.
    """
    if not workspace_id or not workspace_id.strip():
        raise ValueError("workspace_id is required for RAG query.")

    query = query.strip()
    if not query:
        raise ValueError("Query text cannot be empty.")

    logger.info(
        "[RAG] Query received: workspace_id=%s, top_k=%d, doc_filter=%s",
        workspace_id,
        top_k,
        f"{len(document_ids)} docs" if document_ids else "none",
    )

    # ──────────────────────────────────────────────
    # STEP 1: Embed the user query into a 1536-dim vector
    # ──────────────────────────────────────────────
    embedding_service = get_embedding_service(provider=embedding_provider)
    query_embedding = await embedding_service.embed_text(query)

    logger.info("[RAG] Query embedding generated, dim=%d", len(query_embedding))

    # ──────────────────────────────────────────────
    # STEP 2: Vector similarity search (workspace-scoped)
    # ──────────────────────────────────────────────
    pool = await get_db_pool()
    raw_results = await search_similar_chunks(
        pool=pool,
        workspace_id=workspace_id,
        query_embedding=query_embedding,
        limit=top_k,
        document_ids=document_ids if document_ids else None,
        similarity_threshold=similarity_threshold,
    )

    logger.info("[RAG] Retrieved %d chunks from pgvector.", len(raw_results))

    # ──────────────────────────────────────────────
    # STEP 3: Map raw DB rows to typed RetrievedChunk objects
    # ──────────────────────────────────────────────
    chunks = [
        RetrievedChunk(
            chunk_id=row["chunk_id"],
            document_id=row["document_id"],
            content=row["content"],
            page_number=row["page_number"],
            chunk_index=row["chunk_index"],
            similarity=row["similarity"],
            metadata=row.get("metadata") or {},
        )
        for row in raw_results
    ]

    return RAGQueryResult(
        query=query,
        workspace_id=workspace_id,
        results=chunks,
    )

