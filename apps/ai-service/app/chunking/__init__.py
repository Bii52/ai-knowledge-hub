"""Semantic text chunking module with recursive boundaries and sliding overlap."""

from app.chunking.models import Chunk, ChunkingResult
from app.chunking.splitter import RecursiveCharacterChunker, DEFAULT_SEPARATORS

__all__ = [
    "Chunk",
    "ChunkingResult",
    "RecursiveCharacterChunker",
    "DEFAULT_SEPARATORS",
]

