import io
import pytest
import docx
from pypdf import PdfWriter
from app.extractors import (
    PdfExtractor,
    DocxExtractor,
    TxtExtractor,
    get_extractor,
)


class TestTxtExtractor:
    """Unit tests for Plain Text extraction."""

    def test_extract_utf8_vietnamese_text(self) -> None:
        extractor = TxtExtractor()
        sample_text = "Hệ thống AI Knowledge Hub xử lý tài liệu RAG tiếng Việt thông minh."
        content = sample_text.encode("utf-8")

        result = extractor.extract(content)

        assert result.total_pages == 1
        assert len(result.pages) == 1
        assert result.pages[0].page_number == 1
        assert result.pages[0].text == sample_text
        assert result.total_characters == len(sample_text)
        assert result.metadata.get("encoding") == "utf-8"

    def test_empty_content_raises_value_error(self) -> None:
        extractor = TxtExtractor()
        with pytest.raises(ValueError, match="Nội dung tệp TXT trống"):
            extractor.extract(b"")


class TestDocxExtractor:
    """Unit tests for Word (.docx) extraction."""

    def test_extract_docx_paragraphs_and_table(self) -> None:
        # Create an in-memory DOCX document
        doc = docx.Document()
        doc.core_properties.title = "Kế hoạch dự án RAG"
        doc.add_heading("Tiêu đề tài liệu", level=1)
        doc.add_paragraph("Đoạn văn thứ nhất mô tả kiến trúc.")
        
        # Add a table with 2 rows and 2 columns
        table = doc.add_table(rows=2, cols=2)
        table.cell(0, 0).text = "Module"
        table.cell(0, 1).text = "Trạng thái"
        table.cell(1, 0).text = "Extractor"
        table.cell(1, 1).text = "Hoàn thành"

        buffer = io.BytesIO()
        doc.save(buffer)
        docx_bytes = buffer.getvalue()

        extractor = DocxExtractor()
        result = extractor.extract(docx_bytes)

        assert result.total_pages == 1
        assert len(result.pages) == 1
        assert "Tiêu đề tài liệu" in result.pages[0].text
        assert "Đoạn văn thứ nhất mô tả kiến trúc." in result.pages[0].text
        assert "Module | Trạng thái" in result.pages[0].text
        assert "Extractor | Hoàn thành" in result.pages[0].text
        assert result.metadata.get("title") == "Kế hoạch dự án RAG"

    def test_empty_docx_raises_value_error(self) -> None:
        extractor = DocxExtractor()
        with pytest.raises(ValueError, match="Nội dung tệp DOCX trống"):
            extractor.extract(b"")

    def test_corrupt_docx_raises_value_error(self) -> None:
        extractor = DocxExtractor()
        with pytest.raises(ValueError, match="Không thể đọc tệp Word"):
            extractor.extract(b"PK corrupt docx content")


class TestPdfExtractor:
    """Unit tests for PDF extraction."""

    def test_extract_multi_page_pdf(self) -> None:
        # Create an in-memory PDF with 2 pages using pypdf
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        writer.add_blank_page(width=200, height=200)
        writer.add_metadata({"/Title": "Tài liệu mẫu PDF"})

        buffer = io.BytesIO()
        writer.write(buffer)
        pdf_bytes = buffer.getvalue()

        extractor = PdfExtractor()
        result = extractor.extract(pdf_bytes)

        assert result.total_pages == 2
        assert len(result.pages) == 2
        assert result.pages[0].page_number == 1
        assert result.pages[1].page_number == 2
        assert result.metadata.get("title") == "Tài liệu mẫu PDF"

    def test_empty_pdf_raises_value_error(self) -> None:
        extractor = PdfExtractor()
        with pytest.raises(ValueError, match="Nội dung tệp PDF trống"):
            extractor.extract(b"")

    def test_corrupt_pdf_raises_value_error(self) -> None:
        extractor = PdfExtractor()
        with pytest.raises(ValueError, match="Không thể đọc tệp PDF"):
            extractor.extract(b"%PDF-1.4 corrupt content not a real pdf")


class TestExtractorFactory:
    """Unit tests for get_extractor factory function."""

    def test_factory_returns_correct_extractor_types(self) -> None:
        assert isinstance(get_extractor("pdf"), PdfExtractor)
        assert isinstance(get_extractor("PDF"), PdfExtractor)
        assert isinstance(get_extractor(".pdf"), PdfExtractor)

        assert isinstance(get_extractor("docx"), DocxExtractor)
        assert isinstance(get_extractor("DOCX"), DocxExtractor)
        assert isinstance(get_extractor(".docx"), DocxExtractor)

        assert isinstance(get_extractor("txt"), TxtExtractor)
        assert isinstance(get_extractor("TXT"), TxtExtractor)
        assert isinstance(get_extractor(".txt"), TxtExtractor)

    def test_factory_raises_error_for_unsupported_format(self) -> None:
        with pytest.raises(ValueError, match="Định dạng tệp 'xlsx' không được hỗ trợ"):
            get_extractor("xlsx")

        with pytest.raises(ValueError, match="Định dạng tệp 'jpg' không được hỗ trợ"):
            get_extractor("jpg")

