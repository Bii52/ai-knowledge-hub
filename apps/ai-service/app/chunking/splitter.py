import logging
from typing import List, Optional
from app.extractors.base import ExtractionResult
from app.chunking.models import Chunk, ChunkingResult

logger = logging.getLogger("chunker")

# Default hierarchical separators in descending order of semantic granularity
DEFAULT_SEPARATORS: List[str] = [
    "\n\n",  # Paragraphs
    "\n",    # Lines
    ". ",    # Sentences (period)
    "? ",    # Sentences (question)
    "! ",    # Sentences (exclamation)
    "; ",    # Clauses
    ", ",    # Phrases
    " ",     # Words
    "",      # Characters (last resort)
]


class RecursiveCharacterChunker:
    """
    Splits text recursively using semantic boundaries (paragraphs -> sentences -> words)
    combined with a sliding window overlap to preserve contextual continuity for RAG.
    """

    def __init__(
        self,
        chunk_size: int = 800,
        chunk_overlap: int = 150,
        separators: Optional[List[str]] = None,
    ) -> None:
        """
        :param chunk_size: Maximum target character length for each chunk
        :param chunk_overlap: Character overlap between consecutive chunks to avoid semantic cutoff
        :param separators: Custom list of separators ordered from largest to smallest boundary
        """
        if chunk_size <= 0:
            raise ValueError("chunk_size phải lớn hơn 0")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap không được âm")
        if chunk_overlap >= chunk_size:
            raise ValueError(
                f"chunk_overlap ({chunk_overlap}) phải nhỏ hơn chunk_size ({chunk_size})"
            )

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or DEFAULT_SEPARATORS

    def split_text(self, text: str) -> List[str]:
        """
        Split a raw text string into a list of chunk strings respecting boundaries and overlap.

        :param text: Input text string
        :return: List of chunk text strings
        """
        cleaned = text.strip()
        if not cleaned:
            return []

        # If text is already within chunk size limit, return as single chunk
        if len(cleaned) <= self.chunk_size:
            return [cleaned]

        splits = self._recursive_split(cleaned, self.separators)
        return self._merge_splits(splits)

    def chunk_document(self, extraction_result: ExtractionResult) -> ChunkingResult:
        """
        Chunk a multi-page document while preserving page metadata and sequential indexing.

        :param extraction_result: Output from a document extractor (PDF, DOCX, TXT)
        :return: ChunkingResult with sequential global chunk_index and page_number
        """
        chunks: List[Chunk] = []
        global_chunk_idx = 0
        total_chars = 0

        for page in extraction_result.pages:
            page_text = page.text.strip()
            if not page_text:
                continue

            page_splits = self.split_text(page_text)

            for page_chunk_idx, split_text in enumerate(page_splits):
                chunk = Chunk(
                    text=split_text,
                    chunk_index=global_chunk_idx,
                    page_number=page.page_number,
                    char_count=len(split_text),
                    metadata={
                        "page_chunk_index": page_chunk_idx,
                        "source_total_pages": extraction_result.total_pages,
                    },
                )
                chunks.append(chunk)
                total_chars += len(split_text)
                global_chunk_idx += 1

        return ChunkingResult(
            chunks=chunks,
            total_chunks=len(chunks),
            total_characters=total_chars,
        )

    def _recursive_split(self, text: str, separators: List[str]) -> List[str]:
        """Recursively break text down using hierarchical separators."""
        final_pieces: List[str] = []

        # Find the first separator present in the text
        active_sep: Optional[str] = None
        remaining_seps: List[str] = []

        for idx, sep in enumerate(separators):
            if sep == "":
                active_sep = ""
                remaining_seps = []
                break
            if sep in text:
                active_sep = sep
                remaining_seps = separators[idx + 1 :]
                break

        if active_sep is None:
            return [text]

        # Split text by chosen separator
        if active_sep == "":
            splits = list(text)
        else:
            splits = text.split(active_sep)

        # Recursively process splits that exceed chunk_size
        for split in splits:
            if not split:
                continue
            if len(split) > self.chunk_size and remaining_seps:
                final_pieces.extend(self._recursive_split(split, remaining_seps))
            else:
                final_pieces.append(split)

        return final_pieces

    def _merge_splits(self, splits: List[str]) -> List[str]:
        """Merge smaller splits into chunks of up to chunk_size with chunk_overlap."""
        merged_chunks: List[str] = []
        current_pieces: List[str] = []
        current_len = 0

        for piece in splits:
            piece_len = len(piece)
            separator_len = 1 if current_pieces else 0

            # If adding this piece exceeds chunk_size, save current chunk and apply overlap
            if current_len + separator_len + piece_len > self.chunk_size and current_pieces:
                chunk_str = " ".join(current_pieces).strip()
                if chunk_str:
                    merged_chunks.append(chunk_str)

                # Compute overlap pieces from previous chunk to maintain context continuity
                overlap_pieces: List[str] = []
                overlap_len = 0

                # 1. First try matching intact previous pieces
                for prev in reversed(current_pieces):
                    add_len = len(prev) + (1 if overlap_pieces else 0)
                    if overlap_len + add_len <= self.chunk_overlap:
                        overlap_pieces.insert(0, prev)
                        overlap_len += add_len
                    else:
                        break

                # 2. If no full piece fits (pieces were large sentences), take trailing words from chunk_str
                if not overlap_pieces and self.chunk_overlap > 0:
                    words = chunk_str.split()
                    for w in reversed(words):
                        add_len = len(w) + (1 if overlap_pieces else 0)
                        if overlap_len + add_len <= self.chunk_overlap:
                            overlap_pieces.insert(0, w)
                            overlap_len += add_len
                        else:
                            break

                current_pieces = overlap_pieces
                current_len = sum(len(p) for p in current_pieces) + max(0, len(current_pieces) - 1)

            current_pieces.append(piece)
            current_len += piece_len + (1 if len(current_pieces) > 1 else 0)

        # Append final remaining chunk
        if current_pieces:
            chunk_str = " ".join(current_pieces).strip()
            if chunk_str:
                merged_chunks.append(chunk_str)

        return merged_chunks
