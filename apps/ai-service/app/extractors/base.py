from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ExtractedPage(BaseModel):
    """Represents text extracted from a specific page or section of a document."""

    page_number: Optional[int] = Field(
        default=None,
        description="1-based page number where this text originated (None if format has no pages like TXT/DOCX)",
    )
    text: str = Field(
        description="Cleaned textual content extracted from the page",
    )
    char_count: int = Field(
        default=0,
        description="Number of characters in this extracted page",
    )

    def model_post_init(self, __context: Any) -> None:
        """Automatically compute char_count if not explicitly provided."""
        if not self.char_count and self.text:
            self.char_count = len(self.text)


class ExtractionResult(BaseModel):
    """Complete structured output from extracting a document."""

    pages: List[ExtractedPage] = Field(
        default_factory=list,
        description="List of extracted pages with page metadata",
    )
    total_pages: int = Field(
        default=0,
        description="Total number of pages extracted",
    )
    total_characters: int = Field(
        default=0,
        description="Total character count across all pages",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional file metadata (author, title, creation date, etc.)",
    )

    @property
    def full_text(self) -> str:
        """Join all page texts into a single string separated by newlines."""
        return "\n\n".join(p.text for p in self.pages if p.text.strip())


class BaseExtractor(ABC):
    """Abstract Base Class defining the contract for all document format extractors."""

    @abstractmethod
    def extract(self, content: bytes) -> ExtractionResult:
        """
        Extract text and structure from raw document bytes.

        :param content: Raw file bytes (downloaded from storage or uploaded)
        :return: Structured ExtractionResult with page numbers and text
        :raises ValueError: If file content is corrupt or cannot be parsed
        """
        pass

