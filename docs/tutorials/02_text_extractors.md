# BÀI HỌC 02: XÂY DỰNG MODULE BÓC TÁCH VĂN BẢN (TEXT EXTRACTORS) CHO RAG PIPELINE

> **Dành cho**: Kỹ sư AI / Backend muốn làm chủ kỹ thuật xử lý dữ liệu phi cấu trúc (Unstructured Data Processing) cho hệ thống Retrieval-Augmented Generation (RAG).  
> **Dự án**: AI Knowledge Hub (`apps/ai-service/app/extractors`)  
> **Tác giả & Cố vấn**: Senior Software Architect

---

## 1. TỔNG QUAN BẢN CHẤT & TẠI SAO LẠI THIẾT KẾ NHƯ VẬY?

### 1.1. Thách thức lớn nhất trong RAG đối với tài liệu doanh nghiệp
Khi người dùng tải lên tài liệu (PDF, Word, TXT), hệ thống RAG không thể đưa trực tiếp file nhị phân (binary bytes) vào mô hình ngôn ngữ lớn (LLM). Ta phải chuyển đổi tệp nhị phân thành **văn bản thuần (clean text)**.

Tuy nhiên, bóc tách văn bản trong RAG có 2 yêu cầu khắt khe:
1. **Bảo tồn vị trí nguồn gốc (Page Number Tracking)**: Khi AI trả lời: *"Doanh thu quý 3 tăng 25%"*, nó **bắt buộc phải trích dẫn chính xác: "Theo trang 14 của Báo cáo tài chính"**. Nếu không lưu số trang lúc bóc tách, tính năng trích dẫn nguồn (Citations) sẽ hoàn toàn vô dụng!
2. **Cấu trúc bảng biểu (Tables in Word/PDF)**: Bảng biểu thường bị bẹp dúm thành các dòng chữ rời rạc nếu bóc tách thô sơ. Ta cần chuyển đổi cấu trúc hàng/cột của bảng thành định dạng bảng có dấu gạch đứng `Col1 | Col2` để LLM hiểu được quan hệ dòng - cột.

---

### 1.2. Mẫu thiết kế Strategy Pattern & Factory Pattern

Thay vì viết một khối lệnh `if/else` khổng lồ:
```python
# ❌ Phản mẫu (Anti-pattern): Khó bảo trì, vi phạm nguyên lý Open/Closed (SOLID)
if file_type == "pdf":
    ...
elif file_type == "docx":
    ...
```

Chúng ta áp dụng bộ đôi mẫu thiết kế kinh điển:
1. **Strategy Pattern (`BaseExtractor`)**: Định nghĩa một bản giao kèo (Interface) chung. Mọi định dạng file (PDF, DOCX, TXT) đều phải tuân thủ đúng phương thức `extract(content: bytes) -> ExtractionResult`.
2. **Factory Pattern (`get_extractor`)**: Một hàm xưởng tập trung chịu trách nhiệm trả về đúng Extractor tương ứng với định dạng file. Sau này nếu muốn hỗ trợ thêm `.pptx`, `.epub`, ta chỉ việc thêm một class mới mà **không cần sửa đổi logic cũ**.

```text
                    ┌─────────────────────────┐
                    │      BaseExtractor      │ (Abstract Contract)
                    │  extract(bytes) -> Result│
                    └────────────▲────────────┘
                                 │ kế thừa
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
┌───────┴────────┐       ┌───────┴────────┐       ┌───────┴────────┐
│  PdfExtractor  │       │ DocxExtractor  │       │  TxtExtractor  │
│  (trang 1..N)  │       │ (đoạn + bảng)  │       │ (UTF-8, CP1252)│
└────────────────┘       └────────────────┘       └────────────────┘
```

---

## 2. GIẢI THÍCH CHI TIẾT TỪNG TỆP MÃ NGUỒN

### 2.1. Bản hợp đồng cơ sở: `app/extractors/base.py`

```python
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
```
- **`abc.ABC` & `@abstractmethod`**: Đánh dấu lớp `BaseExtractor` là lớp trừu tượng. Bất kỳ lớp nào kế thừa nó mà quên viết hàm `extract()` thì Python sẽ báo lỗi ngay từ lúc khởi động.
- **`pydantic.BaseModel`**: Đảm bảo dữ liệu trích xuất ra được ép kiểu chặt chẽ, tự động kiểm tra lỗi kiểu dữ liệu.

```python
class ExtractedPage(BaseModel):
    page_number: Optional[int] = Field(
        default=None,
        description="1-based page number where this text originated",
    )
    text: str = Field(description="Cleaned textual content")
    char_count: int = Field(default=0)

    def model_post_init(self, __context: Any) -> None:
        if not self.char_count and self.text:
            self.char_count = len(self.text)
```
- **`ExtractedPage`**: Đại diện cho 1 trang văn bản.
- **`page_number`**: Đánh số trang bắt đầu từ `1` (1-indexed). Đây chính là dữ liệu sau này lưu vào cột `page_number` trong bảng `document_chunks` và `message_sources`.
- **`model_post_init`**: Phương thức hook tự động của Pydantic v2. Nếu người gọi không truyền `char_count`, nó sẽ tự động lấy `len(self.text)`.

```python
class ExtractionResult(BaseModel):
    pages: List[ExtractedPage] = Field(default_factory=list)
    total_pages: int = Field(default=0)
    total_characters: int = Field(default=0)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def full_text(self) -> str:
        return "\n\n".join(p.text for p in self.pages if p.text.strip())
```
- **`ExtractionResult`**: Đóng gói toàn bộ kết quả sau khi bóc tách 1 tệp.
- **`@property full_text`**: Hàm tiện ích giúp ghép toàn bộ nội dung của các trang lại với nhau khi cần đọc toàn bộ văn bản.

---

### 2.2. Bóc tách tệp PDF: `app/extractors/pdf_extractor.py`

PDF là định dạng phức tạp nhất vì nó được thiết kế cho việc in ấn (Graphic layout) chứ không phải để đọc văn bản thuần.

```python
import io
import re
from pypdf import PdfReader
from pypdf.errors import PdfReadError
```
- **`io.BytesIO(content)`**: Chuyển đổi mảng byte trong bộ nhớ RAM thành một luồng tệp giả lập (Stream). Nhờ vậy, thư viện `pypdf` có thể đọc trực tiếp mà không cần ghi file tạm ra ổ đĩa (tiết kiệm I/O đĩa và tăng tốc độ xử lý).

```python
stream = io.BytesIO(content)
reader = PdfReader(stream)

if reader.is_encrypted:
    decrypted = reader.decrypt("")
    if decrypted == 0:
        raise ValueError("Tệp PDF có mật khẩu bảo vệ...")
```
- **Xử lý mật khẩu (`is_encrypted`)**: Một số file PDF cho phép đọc không cần pass nhưng vẫn bật cờ mã hóa quyền (permission restrictions). Thử giải mã với chuỗi rỗng `""`. Nếu thất bại, ném ra ngoại lệ tiếng Việt thân thiện để báo người dùng.

```python
for idx, page in enumerate(reader.pages):
    page_num = idx + 1
    raw_text = page.extract_text() or ""
    cleaned_text = self._clean_text(raw_text)
```
- Lặp qua từng trang trong danh sách `reader.pages`.
- Luôn giữ lại bản ghi trang dù trang đó là ảnh scan hoặc trang trắng (`cleaned_text == ""`), nhằm giữ đúng thứ tự chỉ mục trang cho các trang phía sau.

```python
@staticmethod
def _clean_text(text: str) -> str:
    text = text.replace("\x00", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x0c", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [line.strip() for line in text.split("\n")]
    return "\n".join(lines).strip()
```
- **Làm sạch văn bản PDF (`_clean_text`)**:
  - `\x00` (Null byte): Rất hay xuất hiện trong font chữ lỗi của PDF, nếu để nguyên sẽ làm gãy chuỗi khi insert vào PostgreSQL.
  - `\x0c` (Form feed): Ký hiệu ngắt trang đặc thù của PDF.
  - `re.sub(r"\n{3,}", "\n\n", text)`: Gom các khoảng xuống dòng thừa mứa lại thành tối đa 2 dấu xuống dòng (phân cách đoạn).

---

### 2.3. Bóc tách tệp Word DOCX: `app/extractors/docx_extractor.py`

Tệp `.docx` thực chất là một gói tệp nén ZIP chứa các file XML (`word/document.xml`).

```python
# 1. Trích xuất các đoạn văn (Paragraphs)
for paragraph in doc.paragraphs:
    text = paragraph.text.strip()
    if text:
        text_blocks.append(text)

# 2. Trích xuất các bảng biểu (Tables)
for table in doc.tables:
    table_rows: List[str] = []
    for row in table.rows:
        row_cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
        if any(row_cells):
            table_rows.append(" | ".join(row_cells))
    if table_rows:
        text_blocks.append("\n".join(table_rows))
```
- **Xử lý bảng thông minh**:
  - Mỗi ô trong bảng được nối với nhau bằng ký tự gạch đứng ` | ` (chuẩn Markdown Table).
  - Điều này giúp các mô hình ngôn ngữ lớn (LLM) hiểu chính xác bảng dữ liệu theo cấu trúc cột.

---

### 2.4. Bóc tách tệp văn bản thô TXT: `app/extractors/txt_extractor.py`

Tệp `.txt` trông đơn giản nhưng lại chứa một cạm bẫy lớn: **Bảng mã ký tự (Character Encoding)**.

```python
CANDIDATE_ENCODINGS = ("utf-8", "utf-8-sig", "cp1252", "latin-1")
```
- Nếu dùng mỗi `utf-8`, các tệp văn bản tiếng Việt lưu từ Notepad cũ hoặc Windows Excel thường dùng `utf-8-sig` (chứa ký tự Byte Order Mark `\ufeff`) hoặc `cp1252`, sẽ làm chương trình bị văng lỗi `UnicodeDecodeError`.
- Thuật toán của chúng ta thử giải mã lần lượt qua danh sách ưu tiên. Nếu tệp sử dụng bảng mã nào thì lưu lại metadata `encoding` của tệp đó.

---

### 2.5. Xưởng điều phối Extractor: `app/extractors/factory.py`

```python
_EXTRACTOR_REGISTRY: dict[str, type[BaseExtractor]] = {
    "pdf": PdfExtractor,
    "docx": DocxExtractor,
    "txt": TxtExtractor,
}

def get_extractor(file_type: str) -> BaseExtractor:
    normalized_type = file_type.lower().strip().lstrip(".")
    ...
```
- **`normalized_type`**: Chuẩn hóa mọi biến thể của người dùng: `"PDF"`, `".pdf"`, `"  Pdf "` đều được chuyển về `"pdf"`.
- Đảm bảo an toàn kiểu dữ liệu: Nếu ai đó truyền vào `"exe"` hay `"mp4"`, hàm sẽ lập tức từ chối và thông báo rõ các định dạng được hỗ trợ.

---

## 3. KIỂM THỬ TỰ ĐỘNG VỚI PYTEST

Toàn bộ logic bóc tách được kiểm thử tự động trong `tests/test_extractors.py`:
- Kiểm tra tạo tệp PDF trong RAM với 2 trang → xác nhận bóc tách đủ 2 trang và đúng metadata.
- Kiểm tra tạo tệp Word trong RAM với đoạn văn và bảng biểu → xác nhận cấu trúc bảng được giữ nguyên.
- Kiểm tra tệp rỗng hoặc hỏng → xác nhận ném lỗi chính xác để hệ thống không bị treo.

Chạy lệnh kiểm thử:
```powershell
cd "d:\Dự án\AI Knowledge Hub\apps\ai-service"
.\.venv\Scripts\python.exe -m pytest tests -p no:asyncio -v
```

Kết quả: **12/12 bài kiểm thử vượt qua 100% trong 1.11 giây!**

---

## 4. TỔNG KẾT & BƯỚC TIẾP THEO

Bây giờ chúng ta đã có module bóc tách hoàn hảo, sẵn sàng nhận file từ Supabase Storage và chuyển hóa thành văn bản kèm số trang chính xác.

Trong **Phần 3**, chúng ta sẽ xây dựng **Module Semantic Chunking**:
- Sau khi bóc tách được văn bản dài, làm thế nào để cắt nhỏ văn bản thành các đoạn (chunks) có kích thước tối ưu (ví dụ 500 - 800 tokens)?
- Thuật toán **Sliding Window với Overlap** (gối đầu giữa các chunk) để không làm đứt gãy ngữ cảnh của câu.

