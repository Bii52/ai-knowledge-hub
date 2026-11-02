from app.extractors.base import BaseExtractor
from app.extractors.pdf_extractor import PdfExtractor
from app.extractors.docx_extractor import DocxExtractor
from app.extractors.txt_extractor import TxtExtractor

# Registry of supported extractors
_EXTRACTOR_REGISTRY: dict[str, type[BaseExtractor]] = {
    "pdf": PdfExtractor,
    "docx": DocxExtractor,
    "txt": TxtExtractor,
}


def get_extractor(file_type: str) -> BaseExtractor:
    """
    Factory function to retrieve the appropriate extractor instance for a given file type.

    :param file_type: Extension or type string (e.g., 'pdf', '.PDF', 'docx', 'TXT')
    :return: An instantiated BaseExtractor subclass
    :raises ValueError: If the file type is not supported
    """
    normalized_type = file_type.lower().strip().lstrip(".")

    extractor_class = _EXTRACTOR_REGISTRY.get(normalized_type)
    if not extractor_class:
        supported = ", ".join(sorted(_EXTRACTOR_REGISTRY.keys()))
        raise ValueError(
            f"Định dạng tệp '{file_type}' không được hỗ trợ. Các định dạng được hỗ trợ: {supported}"
        )

    return extractor_class()

