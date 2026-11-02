from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Chunk(BaseModel):
    """Represents an atomic semantic piece of text ready for vector embedding and storage."""

    text: str = Field(
        description="Text content of the chunk",
    )
    chunk_index: int = Field(
        description="Global 0-based sequential index of the chunk in the document",
    )
    page_number: Optional[int] = Field(
        default=None,
        description="1-based source page number where this chunk originated (None for unpaged files)",
    )
    char_count: int = Field(
        default=0,
        description="Total character count in this chunk",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional chunk metadata (e.g., page_chunk_index, section header)",
    )

    def model_post_init(self, __context: Any) -> None:
        """Compute char_count automatically if not provided."""
        if not self.char_count and self.text:
            self.char_count = len(self.text)


class ChunkingResult(BaseModel):
    """Encapsulates all chunks produced from a document extraction result."""

    chunks: List[Chunk] = Field(
        default_factory=list,
        description="List of ordered chunks",
    )
    total_chunks: int = Field(
        default=0,
        description="Total number of chunks created",
    )
    total_characters: int = Field(
        default=0,
        description="Total characters across all chunks",
    )

