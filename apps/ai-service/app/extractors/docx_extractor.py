import io
import logging
from typing import Any, Dict, List
import docx
from app.extractors.base import BaseExtractor, ExtractedPage, ExtractionResult

logger = logging.getLogger("docx_extractor")


class DocxExtractor(BaseExtractor):
    """Extractor for Microsoft Word (.docx) documents using python-docx."""

    def extract(self, content: bytes) -> ExtractionResult:
        """
        Extract text from paragraphs and tables in a .docx binary file.

        :param content: Raw .docx bytes
        :return: ExtractionResult containing structured text and metadata
        :raises ValueError: If the document is corrupted or invalid .docx format
        """
        if not content:
            raise ValueError("Nội dung tệp DOCX trống (0 bytes)")

        try:
            stream = io.BytesIO(content)
            doc = docx.Document(stream)
        except Exception as exc:
            logger.error(f"Failed to parse DOCX binary: {exc}")
            raise ValueError(f"Không thể đọc tệp Word (.docx). Tệp có thể bị hỏng: {exc}") from exc

        text_blocks: List[str] = []

        # 1. Extract paragraphs
        for paragraph in doc.paragraphs:
            text = paragraph.text.strip()
            if text:
                text_blocks.append(text)

        # 2. Extract tables (format rows as pipe-separated values for LLM clarity)
        for table in doc.tables:
            table_rows: List[str] = []
            for row in table.rows:
                row_cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                if any(row_cells):
                    table_rows.append(" | ".join(row_cells))
            if table_rows:
                text_blocks.append("\n".join(table_rows))

        combined_text = "\n\n".join(text_blocks)

        metadata: Dict[str, Any] = {}
        try:
            props = doc.core_properties
            if props.title:
                metadata["title"] = props.title
            if props.author:
                metadata["author"] = props.author
            if props.comments:
                metadata["comments"] = props.comments
        except Exception as prop_err:
            logger.debug(f"Could not read DOCX core properties: {prop_err}")

        # In Word documents without explicit physical page markers, we represent the content as page 1
        page = ExtractedPage(
            page_number=1,
            text=combined_text,
            char_count=len(combined_text),
        )

        return ExtractionResult(
            pages=[page],
            total_pages=1,
            total_characters=len(combined_text),
            metadata=metadata,
        )

