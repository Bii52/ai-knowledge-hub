"""Document ingestion pipeline: orchestrates S3 download -> Extract -> Chunk -> Embed -> Save."""

import logging
from dataclasses import dataclass
from typing import List, Optional

from app.chunking.splitter import RecursiveCharacterChunker
from app.core.database import get_db_pool, save_document_chunks
from app.core.storage import get_storage_client
from app.embeddings.factory import get_embedding_service
from app.extractors.factory import get_extractor

logger = logging.getLogger(__name__)

# Configuration constants for chunking
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200


@dataclass
class IngestResult:
    """Result returned after a successful ingestion pipeline run."""

    document_id: str
    workspace_id: str
    chunks_count: int
    status: str = "completed"
    message: str = "Document ingested and indexed successfully"


async def process_document_ingestion(
    document_id: str,
    workspace_id: str,
    storage_path: str,
    file_type: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    embedding_provider: Optional[str] = None,
) -> IngestResult:
    """Execute full document ingestion pipeline.

    Pipeline steps:
        1. Download binary content from Supabase S3 Object Storage.
        2. Extract text from binary using the appropriate extractor (PDF/DOCX/TXT).
        3. Split extracted text into overlapping semantic chunks.
        4. Generate 1536-dimensional vector embeddings for each chunk.
        5. Persist chunks + embeddings into Supabase PostgreSQL pgvector.

    Args:
        document_id: UUID of the Document record in PostgreSQL.
        workspace_id: UUID of the parent Workspace (used for data isolation).
        storage_path: Path/key of the file in the S3 bucket.
        file_type: Type string ('PDF', 'DOCX', 'TXT') for selecting the extractor.
        chunk_size: Maximum character length per chunk (default: 1000).
        chunk_overlap: Number of overlapping characters between adjacent chunks (default: 200).
        embedding_provider: Force embedding provider ('openai', 'mock', or None for auto-detect).

    Returns:
        IngestResult with chunks count and status.

    Raises:
        ValueError: If unsupported file_type is provided.
        StorageException: If file cannot be downloaded from S3.
        Exception: On any unhandled pipeline error.
    """
    logger.info(
        "[Pipeline] Starting ingestion: document_id=%s, workspace_id=%s, file_type=%s, storage_path=%s",
        document_id,
        workspace_id,
        file_type,
        storage_path,
    )

    # ──────────────────────────────────────────────
    # STEP 1: Download raw file bytes from S3 Storage
    # ──────────────────────────────────────────────
    logger.info("[Pipeline] Step 1/5 — Downloading file from storage...")
    storage_client = get_storage_client()
    file_bytes = storage_client.download_file(storage_path)
    logger.info("[Pipeline] Downloaded %d bytes from storage.", len(file_bytes))

    # ──────────────────────────────────────────────
    # STEP 2: Extract text from raw bytes
    # ──────────────────────────────────────────────
    logger.info("[Pipeline] Step 2/5 — Extracting text from %s file...", file_type)
    extractor = get_extractor(file_type.upper())
    extraction_result = extractor.extract(file_bytes)
    logger.info(
        "[Pipeline] Extracted %d pages, total text length: %d chars.",
        len(extraction_result.pages),
        sum(len(p.text) for p in extraction_result.pages),
    )

    if not extraction_result.pages:
        raise ValueError(
            f"Document '{document_id}' yielded no extractable text content."
        )

    # ──────────────────────────────────────────────
    # STEP 3: Split text into semantic chunks
    # ──────────────────────────────────────────────
    logger.info("[Pipeline] Step 3/5 — Chunking extracted text...")
    chunker = RecursiveCharacterChunker(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    chunking_result = chunker.chunk_document(extraction_result)
    chunks = chunking_result.chunks
    logger.info("[Pipeline] Created %d semantic chunks.", len(chunks))

    if not chunks:
        raise ValueError(
            f"Document '{document_id}' produced no chunks after splitting. "
            "The document may be blank or have non-extractable content."
        )

    # ──────────────────────────────────────────────
    # STEP 4: Generate vector embeddings for all chunks
    # ──────────────────────────────────────────────
    logger.info("[Pipeline] Step 4/5 — Generating vector embeddings for %d chunks...", len(chunks))
    embedding_service = get_embedding_service(provider=embedding_provider)
    chunk_texts: List[str] = [chunk.text for chunk in chunks]
    embeddings = await embedding_service.embed_batch(chunk_texts)
    logger.info(
        "[Pipeline] Generated %d embeddings, dimension: %d.",
        len(embeddings),
        len(embeddings[0]) if embeddings else 0,
    )

    # ──────────────────────────────────────────────
    # STEP 5: Persist chunks and embeddings into PostgreSQL pgvector
    # ──────────────────────────────────────────────
    logger.info("[Pipeline] Step 5/5 — Saving chunks to PostgreSQL pgvector...")
    pool = await get_db_pool()
    saved_count = await save_document_chunks(
        pool=pool,
        document_id=document_id,
        workspace_id=workspace_id,
        chunks=chunks,
        embeddings=embeddings,
    )
    logger.info("[Pipeline] Saved %d chunks for document %s.", saved_count, document_id)

    return IngestResult(
        document_id=document_id,
        workspace_id=workspace_id,
        chunks_count=saved_count,
        status="completed",
        message=f"Document ingested and indexed successfully ({saved_count} chunks).",
    )

