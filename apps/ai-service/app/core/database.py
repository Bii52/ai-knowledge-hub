"""Database management module for Supabase PostgreSQL and pgvector."""

import json
import logging
import uuid
from typing import Any, Dict, List, Optional

import asyncpg
from pgvector.asyncpg import register_vector

from app.chunking.models import Chunk
from app.core.config import get_settings

logger = logging.getLogger(__name__)

_pool: Optional[asyncpg.Pool] = None


async def _init_connection(conn: asyncpg.Connection) -> None:
    """Connection initialization hook to register pgvector codec."""
    try:
        # In Supabase, the vector extension is located in the 'extensions' schema
        await register_vector(conn, schema="extensions")
    except Exception as exc:
        logger.warning(
            "Could not register pgvector with schema 'extensions': %s. Retrying default...",
            exc,
        )
        try:
            await register_vector(conn)
        except Exception as fallback_exc:
            logger.error("Failed to register pgvector codec: %s", fallback_exc)
            raise


async def init_db_pool() -> asyncpg.Pool:
    """Initialize the asyncpg database connection pool.

    Returns:
        asyncpg.Pool instance.
    """
    global _pool
    if _pool is not None:
        return _pool

    settings = get_settings()
    if not settings.DATABASE_URL:
        raise ValueError("DATABASE_URL is not set in application configuration.")

    logger.info("Initializing asyncpg connection pool to PostgreSQL...")
    _pool = await asyncpg.create_pool(
        dsn=settings.DATABASE_URL,
        min_size=1,
        max_size=10,
        init=_init_connection,
    )
    logger.info("Database connection pool initialized successfully.")
    return _pool


async def get_db_pool() -> asyncpg.Pool:
    """Retrieve the active database connection pool.

    Returns:
        Active asyncpg.Pool instance.
    """
    global _pool
    if _pool is None:
        _pool = await init_db_pool()
    return _pool


async def close_db_pool() -> None:
    """Gracefully terminate all connections in the database connection pool."""
    global _pool
    if _pool is not None:
        logger.info("Closing database connection pool...")
        await _pool.close()
        _pool = None
        logger.info("Database connection pool closed.")


async def save_document_chunks(
    pool: asyncpg.Pool,
    document_id: str,
    workspace_id: str,
    chunks: List[Chunk],
    embeddings: List[List[float]],
) -> int:
    """Persist document chunks and their vector embeddings into PostgreSQL.

    Executes in an atomic transaction: deletes any prior chunks for this document_id
    and bulk-inserts the new chunks.

    Args:
        pool: Active asyncpg connection pool.
        document_id: UUID string of the parent document.
        workspace_id: UUID string of the workspace owning the document.
        chunks: List of Chunk objects from semantic chunking.
        embeddings: List of float vectors corresponding to each chunk.

    Returns:
        Number of chunks saved.
    """
    if len(chunks) != len(embeddings):
        raise ValueError(
            f"Chunk count ({len(chunks)}) does not match embedding count ({len(embeddings)})"
        )

    if not chunks:
        return 0

    records = []
    for chunk, embedding in zip(chunks, embeddings):
        chunk_uuid = str(uuid.uuid4())
        meta_json = json.dumps(chunk.metadata or {})
        records.append(
            (
                chunk_uuid,
                document_id,
                workspace_id,
                chunk.text,
                chunk.page_number,
                chunk.chunk_index,
                meta_json,
                embedding,
            )
        )

    insert_sql = """
        INSERT INTO document_chunks (
            id,
            document_id,
            workspace_id,
            content,
            page_number,
            chunk_index,
            metadata,
            embedding,
            created_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8, NOW())
    """

    delete_sql = "DELETE FROM document_chunks WHERE document_id = $1"

    async with pool.acquire() as conn:
        async with conn.transaction():
            # Delete any previous chunks to allow idempotent re-ingestion
            await conn.execute(delete_sql, document_id)
            # Bulk insert new chunks
            await conn.executemany(insert_sql, records)

    logger.info(
        "Persisted %d chunks for document %s in workspace %s",
        len(records),
        document_id,
        workspace_id,
    )
    return len(records)


async def search_similar_chunks(
    pool: asyncpg.Pool,
    workspace_id: str,
    query_embedding: List[float],
    limit: int = 5,
    document_ids: Optional[List[str]] = None,
    similarity_threshold: float = 0.0,
) -> List[Dict[str, Any]]:
    """Perform vector similarity search on document chunks with strict workspace scoping.

    Security Rule: Pre-retrieval Workspace Scoping is strictly enforced.
    Vector similarity is calculated using cosine distance (1 - <=>).

    Args:
        pool: Active asyncpg connection pool.
        workspace_id: Workspace UUID string. Required for isolation.
        query_embedding: Vector representation of the user query.
        limit: Maximum number of chunks to return (default: 5).
        document_ids: Optional list of document UUIDs to constrain retrieval.
        similarity_threshold: Minimum cosine similarity score (between 0.0 and 1.0).

    Returns:
        List of dictionaries with chunk information and similarity score.
    """
    if not workspace_id:
        raise ValueError("workspace_id is strictly required for vector similarity search.")

    # Cosine similarity in pgvector: 1 - (embedding <=> query_vector)
    # Cosine distance (<=>) ranges from 0 (identical) to 2 (opposite direction)
    base_query = """
        SELECT 
            id,
            document_id,
            workspace_id,
            content,
            page_number,
            chunk_index,
            metadata,
            1 - (embedding <=> $2) AS similarity
        FROM document_chunks
        WHERE workspace_id = $1
    """

    params: List[Any] = [workspace_id, query_embedding]
    param_idx = 3

    if document_ids:
        base_query += f" AND document_id = ANY(${param_idx})"
        params.append(document_ids)
        param_idx += 1

    if similarity_threshold > 0.0:
        base_query += f" AND (1 - (embedding <=> $2)) >= ${param_idx}"
        params.append(similarity_threshold)
        param_idx += 1

    base_query += f" ORDER BY embedding <=> $2 ASC LIMIT ${param_idx}"
    params.append(limit)

    async with pool.acquire() as conn:
        rows = await conn.fetch(base_query, *params)

    results: List[Dict[str, Any]] = []
    for r in rows:
        meta = r["metadata"]
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except json.JSONDecodeError:
                meta = {}

        results.append(
            {
                "chunk_id": r["id"],
                "document_id": r["document_id"],
                "workspace_id": r["workspace_id"],
                "content": r["content"],
                "page_number": r["page_number"],
                "chunk_index": r["chunk_index"],
                "metadata": meta or {},
                "similarity": float(r["similarity"]) if r["similarity"] is not None else 0.0,
            }
        )

    return results

