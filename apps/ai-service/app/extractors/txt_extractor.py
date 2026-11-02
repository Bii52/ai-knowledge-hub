import logging
from app.extractors.base import BaseExtractor, ExtractedPage, ExtractionResult

logger = logging.getLogger("txt_extractor")


class TxtExtractor(BaseExtractor):
    """Extractor for Plain Text (.txt) files supporting multi-encoding fallback."""

    # Encodings to try in order of likelihood
    CANDIDATE_ENCODINGS = ("utf-8", "utf-8-sig", "cp1252", "latin-1")

    def extract(self, content: bytes) -> ExtractionResult:
        """
        Extract text from raw text file bytes with automatic encoding detection.

        :param content: Raw text bytes
        :return: ExtractionResult containing decoded and normalized text
        :raises ValueError: If the content is empty or cannot be decoded with any candidate encoding
        """
        if not content:
            raise ValueError("Nội dung tệp TXT trống (0 bytes)")

        decoded_text: str | None = None
        used_encoding: str = "unknown"

        for encoding in self.CANDIDATE_ENCODINGS:
            try:
                decoded_text = content.decode(encoding)
                used_encoding = encoding
                break
            except (UnicodeDecodeError, LookupError):
                continue

        if decoded_text is None:
            # Last-resort fallback: replace un-decodable bytes rather than failing
            try:
                decoded_text = content.decode("utf-8", errors="replace")
                used_encoding = "utf-8-replaced"
            except Exception as exc:
                raise ValueError(f"Không thể giải mã nội dung văn bản: {exc}") from exc

        # Normalize line endings
        normalized_text = decoded_text.replace("\r\n", "\n").replace("\r", "\n").strip()

        page = ExtractedPage(
            page_number=1,
            text=normalized_text,
            char_count=len(normalized_text),
        )

        return ExtractionResult(
            pages=[page],
            total_pages=1,
            total_characters=len(normalized_text),
            metadata={"encoding": used_encoding},
        )

