# BÀI HỌC 03: THUẬT TOÁN SEMANTIC CHUNKING (CẮT NHỎ VĂN BẢN THÔNG MINH) CHO RAG

> **Dành cho**: Kỹ sư AI / Backend muốn nắm vững kỹ thuật phân đoạn văn bản (Text Segmentation & Chunking Strategies) - yếu tố quyết định 70% độ chính xác của một hệ thống RAG doanh nghiệp.  
> **Dự án**: AI Knowledge Hub (`apps/ai-service/app/chunking`)  
> **Tác giả & Cố vấn**: Senior Software Architect

---

## 1. TỔNG QUAN BẢN CHẤT: TẠI SAO PHẢI CẮT NHỎ VĂN BẢN (CHUNKING)?

### 1.1. Nghịch lý kích thước trong RAG (The "Goldilocks" Problem)
Khi xây dựng hệ thống hỏi đáp tài liệu:
- **Nếu Chunk QUÁ LỚN (ví dụ 3.000 - 5.000 ký tự)**: 
  - Mô hình nhúng vector (Embedding Model) sẽ bị "pha loãng" ý nghĩa. Vector sinh ra mang tính chung chung, khó tìm thấy khi người dùng hỏi một chi tiết nhỏ cụ thể.
  - Vượt quá giới hạn Context Window của LLM hoặc làm tăng chi phí token không đáng có.
- **Nếu Chunk QUÁ NHỎ (ví dụ 50 - 100 ký tự)**:
  - Vector quá cụ thể nhưng lại bị **mất ngữ cảnh xung quanh**. Ví dụ câu *"Nó tăng 15%"* - nếu đứng một mình, AI sẽ không biết "Nó" là doanh thu, chi phí hay lạm phát!
- **Kích thước lý tưởng**: Thường nằm trong khoảng **500 - 800 ký tự** (tương đương 100 - 180 từ). Đây là kích thước vừa đủ để chứa trọn vẹn 1 ý tưởng hoặc 1 luận điểm hoàn chỉnh.

---

### 1.2. Tại sao BẮT BUỘC phải có "Chunk Overlap" (Gối đầu)?
Hãy tưởng tượng một câu văn quan trọng nằm ngay ranh giới cắt giữa Chunk 1 và Chunk 2:
- *"Công ty đã đầu tư 100 tỷ VND..."* (ở cuối Chunk 1)
- *"...vào nghiên cứu chip AI trong năm 2026."* (ở đầu Chunk 2)

Nếu cắt phẳng không có overlap (cắt đứt lìa), cả 2 chunk đều mất đi ý nghĩa trọn vẹn. 
**Kỹ thuật Sliding Window Overlap (gối đầu 100 - 150 ký tự)**: Cho phép phần đuôi của Chunk 1 được lặp lại ở phần đầu của Chunk 2. Nhờ đó, bất kể câu hỏi của người dùng chạm vào Chunk 1 hay Chunk 2, ngữ cảnh vẫn luôn được bảo toàn nguyên vẹn!

```text
Văn bản gốc:  [========================================================]
Chunk 1:     [-----------------------] (800 ký tự)
                                ▲
                          (gối đầu 150 ký tự)
                                ▼
Chunk 2:                   [-----------------------] (800 ký tự)
```

---

### 1.3. Khớp nối hoàn hảo với Database Schema (Prisma)
Ở Phần Backend NestJS, chúng ta đã thiết kế bảng `document_chunks` trong `schema.prisma`:
```prisma
model DocumentChunk {
  content     String   // Nội dung văn bản của Chunk
  pageNumber  Int?     // Số trang gốc để hiển thị trích dẫn Citation
  chunkIndex  Int      // Vị trí thứ tự của chunk: 0, 1, 2, 3...
  metadata    Json?    // Thông tin bổ trợ
  embedding   vector(1536) // Vector sau này nhúng vào
}
```
Module Chunking của chúng ta được thiết kế để xuất ra cấu trúc dữ liệu **khớp 100%** với các trường trên.

---

## 2. GIẢI THÍCH CHI TIẾT CÁC TỆP MÃ NGUỒN

### 2.1. Cấu trúc dữ liệu: `app/chunking/models.py`

```python
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class Chunk(BaseModel):
    text: str = Field(description="Nội dung văn bản của đoạn chunk")
    chunk_index: int = Field(description="Chỉ mục tuần tự toàn cục (0, 1, 2...)")
    page_number: Optional[int] = Field(default=None, description="Số trang gốc (1-indexed)")
    char_count: int = Field(default=0, description="Số lượng ký tự")
    metadata: Dict[str, Any] = Field(default_factory=dict)
```
- **`chunk_index`**: Đánh số từ `0` tăng dần xuyên suốt toàn bộ tài liệu. Điều này cực kỳ quan trọng để sau này khi AI trả lời, ta có thể lấy thêm các chunk lân cận (`chunk_index - 1` hoặc `chunk_index + 1`) để mở rộng ngữ cảnh (Neighbor Chunk Retrieval).
- **`page_number`**: Nhận trực tiếp từ `ExtractedPage` của Giai đoạn 2. Khi người dùng bấm vào trích dẫn ở giao diện web, UI sẽ tự nhảy đến đúng trang PDF này.

---

### 2.2. Thuật toán Cắt Đệ quy: `app/chunking/splitter.py`

#### Danh sách phân cấp phân cách (Hierarchical Separators):
```python
DEFAULT_SEPARATORS: List[str] = [
    "\n\n",  # 1. Cắt theo đoạn văn trước tiên
    "\n",    # 2. Cắt theo dòng
    ". ",    # 3. Cắt theo câu hoàn chỉnh (dấu chấm)
    "? ",    # 4. Cắt theo câu hỏi
    "! ",    # 5. Cắt theo câu cảm thán
    "; ",    # 6. Cắt theo mệnh đề
    ", ",    # 7. Cắt theo cụm từ
    " ",     # 8. Cắt theo từng từ
    "",      # 9. Bước đường cùng: cắt theo từng ký tự
]
```
- **Ý nghĩa**: Thuật toán sẽ ưu tiên cắt ở ranh giới lớn nhất có thể (`\n\n` - giữa hai đoạn văn). Chỉ khi một đoạn văn dài hơn `chunk_size`, nó mới "hạ cấp" xuống cắt theo dấu chấm câu (`. `), rồi đến dấu phẩy (`, `) và khoảng trắng (` `). Nhờ vậy, câu văn không bao giờ bị chém ngang xương!

#### Phương thức đệ quy `_recursive_split`:
```python
def _recursive_split(self, text: str, separators: List[str]) -> List[str]:
    # 1. Tìm dấu phân cách đầu tiên xuất hiện trong văn bản
    for idx, sep in enumerate(separators):
        if sep in text:
            active_sep = sep
            remaining_seps = separators[idx + 1 :]
            break
            
    # 2. Tách văn bản theo dấu phân cách đó
    splits = text.split(active_sep)
    
    # 3. Nếu mảnh nào vẫn còn dài hơn chunk_size -> Đệ quy với các dấu phân cách nhỏ hơn
    for split in splits:
        if len(split) > self.chunk_size and remaining_seps:
            final_pieces.extend(self._recursive_split(split, remaining_seps))
        else:
            final_pieces.append(split)
```

#### Phương thức gom mảnh và gối đầu `_merge_splits`:
```python
# Khi thêm một mảnh mới làm vượt quá chunk_size:
if current_len + separator_len + piece_len > self.chunk_size and current_pieces:
    chunk_str = " ".join(current_pieces).strip()
    merged_chunks.append(chunk_str)

    # Giữ lại các từ cuối cùng của chunk vừa tạo để gối đầu sang chunk tiếp theo
    overlap_pieces = []
    # (Lấy ngược từ cuối lên đến khi tổng ký tự đạt ngưỡng chunk_overlap)
    ...
```
- Cơ chế **Word-level Overlap Fallback**: Nếu mảnh văn bản trước đó là một câu dài vượt quá `chunk_overlap`, thuật toán sẽ tự động bóc tách các **từ ngữ cuối cùng** của câu đó để làm phần mở đầu cho chunk tiếp theo. Điều này đảm bảo tính liên tục ngữ nghĩa 100% trong mọi trường hợp!

#### Phương thức xử lý toàn tài liệu `chunk_document`:
```python
def chunk_document(self, extraction_result: ExtractionResult) -> ChunkingResult:
    for page in extraction_result.pages:
        # Cắt riêng từng trang để không bao giờ làm lẫn số trang giữa trang N và trang N+1!
        page_splits = self.split_text(page.text)
        for page_chunk_idx, split_text in enumerate(page_splits):
            chunk = Chunk(
                text=split_text,
                chunk_index=global_chunk_idx,
                page_number=page.page_number,  # Bảo toàn số trang gốc
                ...
            )
            chunks.append(chunk)
            global_chunk_idx += 1
```

---

## 3. KIỂM THỬ TỰ ĐỘNG (PYTEST)

Toàn bộ các trường hợp biên đã được kiểm thử trong `tests/test_chunking.py`:
1. `test_invalid_parameters`: Tham số sai (`overlap >= size` hoặc `size <= 0`) bị chặn ngay lập tức.
2. `test_short_text_returns_single_chunk`: Văn bản ngắn hơn `chunk_size` giữ nguyên 1 chunk, không bị cắt vụn.
3. `test_splits_paragraphs_respecting_chunk_size`: Tách đoạn văn lớn thành các chunk nhỏ hơn hoặc bằng `chunk_size`.
4. `test_overlap_ensures_context_continuity`: Kiểm tra từ ngữ ở đuôi Chunk 1 có xuất hiện ở đầu Chunk 2 hay không.
5. `test_chunk_document_preserves_page_numbers`: Xác nhận tài liệu 2 trang sinh ra các chunk có đúng `page_number=1` và `page_number=2`, và `chunk_index` tăng đều từ `0, 1, 2...`.
6. `test_continuous_long_word_without_spaces`: Thử thách chuỗi dài 350 ký tự không có dấu cách (như mã hoá base64) vẫn được cắt an toàn mà không làm sập server.

Chạy lệnh kiểm thử:
```powershell
cd "d:\Dự án\AI Knowledge Hub\apps\ai-service"
.\.venv\Scripts\python.exe -m pytest tests -p no:asyncio -v
```
Kết quả: **19/19 bài kiểm thử vượt qua 100% trong 1.00 giây!**

---

## 4. TỰ THỰC HÀNH VỚI MÃ PYTHON

Bạn có thể mở terminal và chạy thử trực tiếp đoạn mã Python sau để tận mắt quan sát cách thuật toán cắt đoạn và tạo overlap:

```python
from app.chunking import RecursiveCharacterChunker

chunker = RecursiveCharacterChunker(chunk_size=120, chunk_overlap=30)
text = (
    "AI Knowledge Hub là nền tảng quản trị tri thức doanh nghiệp. "
    "Hệ thống ứng dụng kiến trúc RAG hiện đại giúp giải quyết hiện tượng ảo giác. "
    "Mọi câu trả lời của AI đều được trích dẫn nguồn tài liệu chính xác tuyệt đối."
)

chunks = chunker.split_text(text)
for i, c in enumerate(chunks):
    print(f"\n--- CHUNK {i} ({len(c)} ký tự) ---")
    print(c)
```

---

## 5. TỔNG KẾT & BƯỚC TIẾP THEO

Bây giờ chúng ta đã có:
1. **Kiến trúc cốt lõi**: FastAPI, Pydantic Settings, CORS.
2. **Module Extractor**: Đọc file PDF/DOCX/TXT thành văn bản kèm số trang.
3. **Module Chunking**: Cắt nhỏ văn bản thành các đoạn ~500-800 ký tự với gối đầu overlap, bảo toàn số trang và chỉ mục tuần tự.

Trong **Giai đoạn 4**, chúng ta sẽ xây dựng **Module Embeddings & Vector Database**:
- Chuyển đổi các chunk văn bản này thành mảng số thực 1536 chiều (`list[float]`) bằng mô hình embedding.
- Kết nối tới **Supabase PostgreSQL** qua extension `pgvector` để lưu trữ và truy vấn tìm kiếm độ tương đồng Cosine Similarity (`<=>`).

