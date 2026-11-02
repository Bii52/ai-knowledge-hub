import pytest
from app.extractors.base import ExtractedPage, ExtractionResult
from app.chunking import RecursiveCharacterChunker, Chunk, ChunkingResult


class TestRecursiveCharacterChunker:
    """Unit tests for the RecursiveCharacterChunker algorithm."""

    def test_invalid_parameters_raise_value_error(self) -> None:
        # Overlap equal to or larger than chunk_size
        with pytest.raises(ValueError, match="chunk_overlap .* phải nhỏ hơn chunk_size"):
            RecursiveCharacterChunker(chunk_size=500, chunk_overlap=500)

        with pytest.raises(ValueError, match="chunk_overlap .* phải nhỏ hơn chunk_size"):
            RecursiveCharacterChunker(chunk_size=500, chunk_overlap=600)

        # Non-positive chunk_size
        with pytest.raises(ValueError, match="chunk_size phải lớn hơn 0"):
            RecursiveCharacterChunker(chunk_size=0, chunk_overlap=0)

    def test_short_text_returns_single_chunk(self) -> None:
        chunker = RecursiveCharacterChunker(chunk_size=800, chunk_overlap=100)
        short_text = "Đây là một đoạn văn ngắn không vượt quá kích thước chunk."

        chunks = chunker.split_text(short_text)

        assert len(chunks) == 1
        assert chunks[0] == short_text

    def test_empty_or_whitespace_returns_empty_list(self) -> None:
        chunker = RecursiveCharacterChunker(chunk_size=800, chunk_overlap=100)
        assert chunker.split_text("") == []
        assert chunker.split_text("   \n\n  \t ") == []

    def test_splits_paragraphs_respecting_chunk_size(self) -> None:
        chunker = RecursiveCharacterChunker(chunk_size=200, chunk_overlap=40)
        p1 = "Đoạn văn thứ nhất mô tả tổng quan về hệ sinh thái trí tuệ nhân tạo và các công nghệ học sâu đang phát triển mạnh mẽ trên toàn cầu."
        p2 = "Đoạn văn thứ hai tập trung vào kỹ thuật Retrieval-Augmented Generation (RAG) nhằm giải quyết hiện tượng ảo giác (hallucination) của LLM."
        p3 = "Đoạn văn thứ ba phân tích các giải pháp cơ sở dữ liệu vector như PostgreSQL kết hợp pgvector để tối ưu hiệu năng tìm kiếm độ tương đồng."
        text = f"{p1}\n\n{p2}\n\n{p3}"

        chunks = chunker.split_text(text)

        assert len(chunks) >= 3
        for chunk in chunks:
            assert len(chunk) <= 250  # Allows small boundary tolerance
            assert len(chunk) > 0

    def test_overlap_ensures_context_continuity(self) -> None:
        chunker = RecursiveCharacterChunker(chunk_size=150, chunk_overlap=50)
        text = (
            "Trí tuệ nhân tạo đang thay đổi thế giới một cách nhanh chóng. "
            "Các mô hình ngôn ngữ lớn như GPT-4 hay Claude có khả năng đọc hiểu phi thường. "
            "Tuy nhiên, chúng cần được kết nối với cơ sở tri thức riêng của doanh nghiệp để phát huy tối đa sức mạnh."
        )

        chunks = chunker.split_text(text)

        assert len(chunks) >= 2
        # Verify that trailing words from chunk 0 are present in chunk 1
        first_chunk = chunks[0]
        second_chunk = chunks[1]

        # Check there is common shared text between consecutive chunks
        first_chunk_words = set(first_chunk.split()[-5:])
        second_chunk_words = set(second_chunk.split()[:8])
        shared_words = first_chunk_words.intersection(second_chunk_words)
        assert len(shared_words) > 0

    def test_chunk_document_preserves_page_numbers_and_sequential_index(self) -> None:
        chunker = RecursiveCharacterChunker(chunk_size=120, chunk_overlap=30)

        # Simulate a 2-page document
        page1_text = (
            "Nội dung của trang 1 giải thích về cơ chế bóc tách văn bản. "
            "Mỗi trang cần được lưu giữ số trang chính xác."
        )
        page2_text = (
            "Nội dung của trang 2 mô tả về mô hình vector embeddings. "
            "Vector embeddings được chuyển hóa thành các mảng số thực."
        )

        extraction_result = ExtractionResult(
            pages=[
                ExtractedPage(page_number=1, text=page1_text),
                ExtractedPage(page_number=2, text=page2_text),
            ],
            total_pages=2,
            total_characters=len(page1_text) + len(page2_text),
        )

        result: ChunkingResult = chunker.chunk_document(extraction_result)

        assert result.total_chunks >= 2
        assert len(result.chunks) == result.total_chunks

        # Check global sequential chunk_index: 0, 1, 2, ...
        for idx, chunk in enumerate(result.chunks):
            assert chunk.chunk_index == idx
            assert chunk.char_count == len(chunk.text)
            assert chunk.page_number in (1, 2)

        # Check that page 1 chunks have page_number=1, and page 2 chunks have page_number=2
        p1_chunks = [c for c in result.chunks if c.page_number == 1]
        p2_chunks = [c for c in result.chunks if c.page_number == 2]

        assert len(p1_chunks) > 0
        assert len(p2_chunks) > 0

    def test_continuous_long_word_without_spaces_splits_gracefully(self) -> None:
        chunker = RecursiveCharacterChunker(chunk_size=100, chunk_overlap=20)
        long_string = "A" * 350

        chunks = chunker.split_text(long_string)

        assert len(chunks) >= 3
        for c in chunks:
            assert len(c) <= 120

