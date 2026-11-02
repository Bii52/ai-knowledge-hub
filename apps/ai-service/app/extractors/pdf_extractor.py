import io
import re
import logging
from typing import Any, Dict
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from app.extractors.base import BaseExtractor, ExtractedPage, ExtractionResult

logger = logging.getLogger("pdf_extractor")


class PdfExtractor(BaseExtractor):
    """Extractor for Portable Document Format (.pdf) files using pypdf."""

    def extract(self, content: bytes) -> ExtractionResult:
        """
        Extract text page-by-page from PDF binary data.

        :param content: Raw PDF bytes
        :return: ExtractionResult containing text split by exact page number
        :raises ValueError: If the PDF is corrupted or unreadable
        """
        if not content:
            raise ValueError("Nội dung tệp PDF trống (0 bytes)")

        try:
            stream = io.BytesIO(content)
            reader = PdfReader(stream)
        except (PdfReadError, Exception) as exc:
            logger.error(f"Failed to parse PDF binary: {exc}")
            raise ValueError(f"Không thể đọc tệp PDF. Tệp có thể bị lỗi hoặc hỏng: {exc}") from exc

        if reader.is_encrypted:
            # Attempt empty password decryption (some PDFs have empty password restrictions)
            try:
                decrypted = reader.decrypt("")
                if decrypted == 0:
                    raise ValueError("Tệp PDF có mật khẩu bảo vệ. Vui lòng gỡ mật khẩu trước khi tải lên.")
            except Exception as exc:
                raise ValueError("Tệp PDF có mật khẩu bảo vệ và không thể giải mã.") from exc

        pages: list[ExtractedPage] = []
        total_chars = 0

        for idx, page in enumerate(reader.pages):
            page_num = idx + 1
            try:
                raw_text = page.extract_text() or ""
            except Exception as page_exc:
                logger.warning(f"Failed extracting text from page {page_num}: {page_exc}")
                raw_text = ""

            cleaned_text = self._clean_text(raw_text)

            # Preserve page entry even if blank so page numbering remains accurate for citations
            extracted_page = ExtractedPage(
                page_number=page_num,
                text=cleaned_text,
                char_count=len(cleaned_text),
            )
            pages.append(extracted_page)
            total_chars += len(cleaned_text)

        metadata: Dict[str, Any] = {}
        if reader.metadata:
            for key, val in reader.metadata.items():
                if val:
                    clean_key = key.lstrip("/").lower()
                    metadata[clean_key] = str(val)

        return ExtractionResult(
            pages=pages,
            total_pages=len(pages),
            total_characters=total_chars,
            metadata=metadata,
        )

    @staticmethod
    def _clean_text(text: str) -> str:
        """Clean extracted PDF text while preserving paragraph structure."""
        if not text:
            return ""

        # Replace null bytes
        text = text.replace("\x00", "")

        # Normalize carriage returns and form feeds
        text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x0c", "\n")

        # Collapse more than two consecutive newlines into double newlines (paragraphs)
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Strip leading/trailing whitespaces per line
        lines = [line.strip() for line in text.split("\n")]
        return "\n".join(lines).strip()

