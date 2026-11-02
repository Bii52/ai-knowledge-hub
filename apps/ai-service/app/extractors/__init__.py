"""Document text extraction module supporting PDF, DOCX, and TXT formats."""

from app.extractors.base import BaseExtractor, ExtractedPage, ExtractionResult
from app.extractors.pdf_extractor import PdfExtractor
from app.extractors.docx_extractor import DocxExtractor
from app.extractors.txt_extractor import TxtExtractor
from app.extractors.factory import get_extractor

__all__ = [
    "BaseExtractor",
    "ExtractedPage",
    "ExtractionResult",
    "PdfExtractor",
    "DocxExtractor",
    "TxtExtractor",
    "get_extractor",
]

