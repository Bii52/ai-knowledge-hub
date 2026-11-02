# BÀI HỌC 4: VECTOR EMBEDDINGS VÀ SUPABASE PGVECTOR

> **Mục tiêu bài học:**
> 1. Hiểu bản chất Vector Embedding: Biến văn bản tự nhiên thành tọa độ toán học nhiều chiều (1536 chiều).
> 2. Nắm vững toán học Vector: Khoảng cách Cosine (`<=>`), Độ tương đồng Cosine (Cosine Similarity), và Chuẩn hóa L2-norm.
> 3. Nắm vững quy tắc bảo mật dữ liệu tuyệt đối: **Pre-retrieval Workspace Scoping** (cách ly dữ liệu cấp Workspace trước khi tìm kiếm vector).
> 4. Xây dựng dịch vụ Embeddings theo mẫu thiết kế Factory: Hỗ trợ cả **OpenAI API** (`text-embedding-3-small`) và **Mock Deterministic Generator** (để dev và test offline không tốn tiền API).
> 5. Làm chủ kết nối bất đồng bộ hiệu năng cao với **asyncpg** và tiện ích mở rộng **pgvector** trên Supabase PostgreSQL.

---

## 1. TẠI SAO PHẢI CẦN VECTOR EMBEDDING TRONG RAG?

### 1.1. Vấn đề của tìm kiếm từ khóa truyền thống (Keyword Search)
Trong các cơ sở dữ liệu truyền thống (SQL `LIKE %keyword%` hoặc Full-Text Search):
- Nếu tài liệu lưu: *"Công ty có chính sách làm việc từ xa vào thứ Sáu."*
- Người dùng hỏi: *"Tôi có được work from home cuối tuần không?"*
- **Kết quả:** Không tìm thấy! Vì từ khóa `"work from home"` không trùng chữ với `"làm việc từ xa"`.

### 1.2. Giải pháp: Vector Embedding (Biểu diễn ngữ nghĩa bằng số học)
Một mô hình Embedding (như `text-embedding-3-small` của OpenAI) biến một chuỗi văn bản thành một danh sách gồm **1536 số thực float**:
```python
"Công ty cho phép làm việc từ xa"  -> [0.0142, -0.0521, 0.0891, ..., 0.0031] (1536 số)
"Tôi có được work from home không" -> [0.0139, -0.0518, 0.0885, ..., 0.0029] (1536 số)
"Cách nấu bún bò Huế ngon chuẩn vị" -> [-0.0821, 0.1245, -0.0124, ..., -0.0912] (1536 số)
```
- Các câu có ngữ nghĩa tương đồng sẽ nằm **rất gần nhau** trong không gian hình học 1536 chiều.
- Câu về "nấu bún bò" sẽ nằm ở hướng hoàn toàn khác.

---

## 2. TOÁN HỌC VECTOR & BỘ TOÁN TỬ TRONG PGVECTOR

### 2.1. Độ tương đồng Cosine (Cosine Similarity) & Khoảng cách Cosine (Cosine Distance)
Hai vector $\vec{u}$ và $\vec{v}$ có góc $\theta$ giữa chúng.
Công thức tính Cosine Similarity:
$$\text{Cosine Similarity} = \cos(\theta) = \frac{\vec{u} \cdot \vec{v}}{\|\vec{u}\| \|\vec{v}\|}$$

- Khi hai vector cùng hướng (ngữ nghĩa giống hệt nhau): $\cos(\theta) = 1.0$.
- Khi hai vector vuông góc (hoàn toàn không liên quan): $\cos(\theta) = 0.0$.
- Khi hai vector ngược hướng (đối nghịch): $\cos(\theta) = -1.0$.

Trong tiện ích **pgvector** của PostgreSQL:
- Toán tử `<=>` đại diện cho **Cosine Distance** (khoảng cách góc).
- Công thức: $\text{Cosine Distance} = 1 - \text{Cosine Similarity}$.
- Do đó:
  - Vector giống hệt: Distance = $1 - 1 = 0.0$.
  - Vector càng gần nhau thì Distance càng nhỏ.
- Khi muốn lấy điểm phần trăm độ tương đồng (Similarity Score từ $0.0 \to 1.0$):
  $$\text{Similarity} = 1 - (\text{embedding} \Leftrightarrow \text{query\_vector})$$

### 2.2. Chuẩn hóa L2 (L2-norm Normalization)
Một vector $\vec{v} = [x_1, x_2, \dots, x_n]$ được gọi là vector đơn vị (unit vector) khi độ dài Euclide của nó bằng 1:
$$\|\vec{v}\| = \sqrt{\sum_{i=1}^{n} x_i^2} = 1.0$$
Khi vector đã được chuẩn hóa L2, tích vô hướng $\vec{u} \cdot \vec{v}$ chính là Cosine Similarity, giúp thuật toán tìm kiếm của cơ sở dữ liệu tính toán với tốc độ cực nhanh mà không cần phép chia căn bậc hai tốn kém tài nguyên CPU.

---

## 3. NGUYÊN TẮC BẢO MẬT BẮT BUỘC: PRE-RETRIEVAL WORKSPACE SCOPING

Trong kiến trúc SaaS đa người thuê (Multi-Tenant), dữ liệu giữa các Workspace tuyệt đối không được phép rò rỉ:

> [!CAUTION]
> **LỖI CHÍ MẠNG THƯỜNG GẶP:**
> Rất nhiều hệ thống AI lấy Top 5 chunks gần nhất trên toàn bộ cơ sở dữ liệu (`ORDER BY embedding <=> $1 LIMIT 5`), sau đó dùng code Python/NodeJS để kiểm tra xem chunk đó có thuộc Workspace của người dùng hay không.
> **Hậu quả:** Nếu người dùng khác có tài liệu nói về chủ đề tương tự, các chunk của họ sẽ chiếm hết Top 5, khiến người dùng hiện tại không nhận được dữ liệu của chính mình, thậm chí làm rò rỉ dữ liệu mật của khách hàng khác!

### Giải pháp bắt buộc trong AI Knowledge Hub:
Luôn luôn lọc `WHERE workspace_id = $1` **TRƯỚC** khi thực hiện sắp xếp khoảng cách vector:
```sql
SELECT 
    id, document_id, workspace_id, content, page_number, chunk_index, metadata,
    1 - (embedding <=> $2) AS similarity
FROM document_chunks
WHERE workspace_id = $1  -- BẮT BUỘC LỌC ĐẦU TIÊN
ORDER BY embedding <=> $2 ASC
LIMIT $3;
```

---

## 4. CHI TIẾT CÁC TẬP TIN MÃ NGUỒN VÀ GIẢI THÍCH TỪNG DÒNG

### 4.1. `app/embeddings/base.py` — Interface cho Embedding Service
Tập tin này định nghĩa hợp đồng lập trình (Interface) sử dụng Abstract Base Class (`ABC`):

```python
from abc import ABC, abstractmethod
from typing import List


class BaseEmbeddingService(ABC):
    """Interface cho các nhà cung cấp embedding vector."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Trả về số chiều không gian của vector (ví dụ: 1536)."""
        pass

    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """Tạo vector embedding cho một đoạn văn bản đơn lẻ."""
        pass

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Tạo danh sách vector embedding cho một danh sách các đoạn văn bản."""
        pass
```

- **Tại sao lại tạo class trừu tượng?** Để tách rời tầng nghiệp vụ khỏi nhà cung cấp cụ thể. Sau này nếu muốn chuyển từ OpenAI sang Google Vertex AI, Cohere, hay HuggingFace cục bộ, toàn bộ hệ thống lõi không cần sửa đổi dù chỉ 1 dòng.

---

### 4.2. `app/embeddings/mock_service.py` — Bộ sinh Vector Deterministic Offline
Khi chạy Unit Test hoặc phát triển ở máy cá nhân không có kết nối mạng hoặc không muốn tốn tiền API OpenAI, `MockEmbeddingService` sinh ra vector 1536 chiều hoàn hảo:

```python
import hashlib
import math
import random
from typing import List
from app.embeddings.base import BaseEmbeddingService

class MockEmbeddingService(BaseEmbeddingService):
    def __init__(self, dimension: int = 1536) -> None:
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def _generate_vector(self, text: str) -> List[float]:
        if not text:
            return [0.0] * self._dimension

        # 1. Băm chuỗi text thành mã SHA-256 để làm seed cố định
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        seed = int.from_bytes(digest[:8], byteorder="big")

        # 2. Khởi tạo bộ sinh số ngẫu nhiên từ seed
        rng = random.Random(seed)
        raw_vector = [rng.gauss(0.0, 1.0) for _ in range(self._dimension)]

        # 3. Chuẩn hóa L2-norm để độ dài vector luôn = 1.0
        norm = math.sqrt(sum(x * x for x in raw_vector))
        if norm == 0.0:
            return raw_vector

        return [x / norm for x in raw_vector]

    async def embed_text(self, text: str) -> List[float]:
        return self._generate_vector(text)

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self._generate_vector(t) for t in texts]
```

- **Tính chất Deterministic (Xác định):** Cùng một đoạn văn bản đầu vào sẽ luôn luôn sinh ra chính xác cùng một mảng vector 1536 số thực. Khác đoạn văn sẽ sinh ra vector khác.
- **Chuẩn hóa `norm = math.sqrt(sum(x * x))`:** Đảm bảo khoảng cách Cosine và Cosine Similarity hoạt động chuẩn xác 100% trong bài toán kiểm thử.

---

### 4.3. `app/embeddings/openai_service.py` — Tích hợp OpenAI Embeddings
Sử dụng thư viện chính thức `openai` với client bất đồng bộ `AsyncOpenAI`:

```python
from typing import List
import openai
from app.core.config import get_settings
from app.embeddings.base import BaseEmbeddingService

class OpenAIEmbeddingService(BaseEmbeddingService):
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        dimension: int | None = None,
    ) -> None:
        settings = get_settings()
        self._api_key = api_key or settings.OPENAI_API_KEY
        self._model = model or settings.EMBEDDING_MODEL
        self._dimension = dimension or settings.EMBEDDING_DIMENSION

        if not self._api_key:
            raise ValueError(
                "OpenAI API key is missing. Set OPENAI_API_KEY in .env or pass api_key explicitly."
            )

        self._client = openai.AsyncOpenAI(api_key=self._api_key)

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed_text(self, text: str) -> List[float]:
        cleaned_text = text.replace("\n", " ").strip()
        if not cleaned_text:
            return [0.0] * self._dimension

        response = await self._client.embeddings.create(
            input=cleaned_text,
            model=self._model,
        )
        return response.data[0].embedding

    async def embed_batch(
        self, texts: List[str], batch_size: int = 100
    ) -> List[List[float]]:
        if not texts:
            return []

        all_embeddings: List[List[float]] = []

        # Chia nhỏ thành các batch 100 items để tránh quá giới hạn payload của OpenAI
        for i in range(0, len(texts), batch_size):
            chunk_texts = [
                t.replace("\n", " ").strip() or " " for t in texts[i : i + batch_size]
            ]
            response = await self._client.embeddings.create(
                input=chunk_texts,
                model=self._model,
            )
            # OpenAI trả về mảng có index, sắp xếp lại để bảo toàn thứ tự gốc
            sorted_data = sorted(response.data, key=lambda item: item.index)
            all_embeddings.extend([item.embedding for item in sorted_data])

        return all_embeddings
```

- **`text.replace("\n", " ")`:** OpenAI khuyến nghị thay thế ký tự xuống dòng bằng khoảng trắng khi tạo embedding để mô hình tập trung vào ngữ nghĩa câu thay vì cấu trúc dòng.
- **`batch_size = 100`:** Nếu một cuốn sách có 2000 chunks, gửi cả 2000 chunks trong 1 request HTTP có thể bị timeout hoặc lỗi payload quá lớn. Việc chia batch 100 giúp ổn định và kiểm soát luồng dữ liệu tối ưu.

---

### 4.4. `app/embeddings/factory.py` — Cơ chế lựa chọn tự động thông minh
Áp dụng Factory Pattern để tự động nhận diện:

```python
def get_embedding_service(
    provider: str | None = None,
) -> BaseEmbeddingService:
    settings = get_settings()

    if provider == "mock":
        return MockEmbeddingService(dimension=settings.EMBEDDING_DIMENSION)

    if provider == "openai":
        return OpenAIEmbeddingService()

    # Tự động: Nếu có API Key thì dùng OpenAI, nếu không có thì tự động fallback về Mock
    if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.strip():
        return OpenAIEmbeddingService()

    return MockEmbeddingService(dimension=settings.EMBEDDING_DIMENSION)
```

---

### 4.5. `app/core/database.py` — Tích hợp Supabase PostgreSQL & pgvector với asyncpg

#### Bí quyết kỹ thuật với Supabase:
Trong Supabase, phần mở rộng `vector` được cài đặt trong schema đặc biệt tên là **`extensions`**, chứ không nằm trong schema `public` mặc định.
Vì vậy, hàm đăng ký codec của asyncpg phải chỉ định rõ `schema="extensions"`:

```python
import json
import logging
import uuid
from typing import Any, Dict, List, Optional
import asyncpg
from pgvector.asyncpg import register_vector
from app.chunking.models import Chunk
from app.core.config import get_settings

logger = logging.getLogger(__name__)
_pool: Optional[asyncpg.Pool] = None

async def _init_connection(conn: asyncpg.Connection) -> None:
    """Được gọi mỗi khi một kết nối mới được tạo trong Pool."""
    try:
        # Supabase đặt pgvector trong schema 'extensions'
        await register_vector(conn, schema="extensions")
    except Exception as exc:
        logger.warning("Falling back to default schema: %s", exc)
        await register_vector(conn)
```

#### Hàm lưu trữ Chunks và Vector vào Database:
```python
async def save_document_chunks(
    pool: asyncpg.Pool,
    document_id: str,
    workspace_id: str,
    chunks: List[Chunk],
    embeddings: List[List[float]],
) -> int:
    if len(chunks) != len(embeddings):
        raise ValueError("Số lượng chunk và số lượng vector không khớp nhau.")

    if not chunks:
        return 0

    records = []
    for chunk, embedding in zip(chunks, embeddings):
        records.append(
            (
                str(uuid.uuid4()),
                document_id,
                workspace_id,
                chunk.text,
                chunk.page_number,
                chunk.chunk_index,
                json.dumps(chunk.metadata or {}),
                embedding,
            )
        )

    insert_sql = """
        INSERT INTO document_chunks (
            id, document_id, workspace_id, content, page_number, chunk_index, metadata, embedding, created_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8, NOW())
    """

    async with pool.acquire() as conn:
        async with conn.transaction():
            # Xóa các chunk cũ nếu tài liệu này được ingest lại (Idempotency)
            await conn.execute("DELETE FROM document_chunks WHERE document_id = $1", document_id)
            # Thêm hàng loạt siêu tốc bằng executemany
            await conn.executemany(insert_sql, records)

    return len(records)
```

#### Hàm tìm kiếm tương đồng vector với Cosine Distance:
```python
async def search_similar_chunks(
    pool: asyncpg.Pool,
    workspace_id: str,
    query_embedding: List[float],
    limit: int = 5,
    document_ids: Optional[List[str]] = None,
    similarity_threshold: float = 0.0,
) -> List[Dict[str, Any]]:
    if not workspace_id:
        raise ValueError("workspace_id là bắt buộc để cách ly dữ liệu!")

    base_query = """
        SELECT 
            id, document_id, workspace_id, content, page_number, chunk_index, metadata,
            1 - (embedding <=> $2) AS similarity
        FROM document_chunks
        WHERE workspace_id = $1
    """

    params = [workspace_id, query_embedding]
    param_idx = 3

    if document_ids:
        base_query += f" AND document_id = ANY(${param_idx})"
        params.append(document_ids)
        param_idx += 1

    if similarity_threshold > 0.0:
        base_query += f" AND (1 - (embedding <=> $2)) >= ${param_idx}"
        params.append(similarity_threshold)
        param_idx += 1

    base_query += f" ORDER BY embedding <=> $2 ASC LIMIT ${param_idx}"
    params.append(limit)

    async with pool.acquire() as conn:
        rows = await conn.fetch(base_query, *params)

    # Chuyển đổi kết quả thành danh sách dict chuẩn
    results = []
    for r in rows:
        meta = r["metadata"]
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except json.JSONDecodeError:
                meta = {}
        results.append({
            "chunk_id": r["id"],
            "document_id": r["document_id"],
            "workspace_id": r["workspace_id"],
            "content": r["content"],
            "page_number": r["page_number"],
            "chunk_index": r["chunk_index"],
            "metadata": meta,
            "similarity": float(r["similarity"]) if r["similarity"] is not None else 0.0,
        })

    return results
```

---

## 5. GIẢI THÍCH CÁC LỆNH TERMINAL ĐÃ SỬ DỤNG

### 5.1. Kiểm tra và chạy bộ kiểm thử Unit Tests:
```powershell
$env:PYTHONPATH="apps/ai-service"; & "apps/ai-service/.venv/Scripts/python.exe" -m pytest apps/ai-service/tests -p no:asyncio -v
```
- `$env:PYTHONPATH="apps/ai-service"`: Đưa thư mục `apps/ai-service` vào danh sách đường dẫn tìm kiếm module của Python, giúp câu lệnh `import app.core...` hoạt động chính xác từ bất kỳ thư mục làm việc nào.
- `& "apps/ai-service/.venv/Scripts/python.exe"`: Sử dụng toán tử gọi `&` trong PowerShell để thực thi file nhị phân của Python bên trong môi trường ảo (.venv).
- `-m pytest apps/ai-service/tests`: Chạy công cụ kiểm thử Pytest trên thư mục chứa các bài test.
- `-p no:asyncio`: Vô hiệu hóa plugin tự động của pytest-asyncio nhằm tránh việc tạo vòng lặp socketpair loopback có thể gây nghẽn tiến trình trên Windows Sandbox.
- `-v` (`--verbose`): Hiển thị chi tiết từng test case, bao gồm tên test và trạng thái `PASSED` / `FAILED`.

---

## 6. KẾT QUẢ KIỂM THỬ GIAI ĐOẠN 4

Toàn bộ **29 bài kiểm thử** trong dự án đã chạy thành công 100%:
- **`test_extractors.py`**: 10 tests (PDF, DOCX, TXT, Factory, Error cases) — **PASSED**.
- **`test_chunking.py`**: 7 tests (Recursive Character Chunker, Overlap, Metadata preservation) — **PASSED**.
- **`test_embeddings.py`**: 10 tests (Dimension 1536, L2-norm, Determinism, Fallback, Validation) — **PASSED**.
- **`test_health.py`**: 2 tests (Root & Health endpoints) — **PASSED**.
- **Live Supabase Vector Roundtrip**: Đã xác nhận chèn vector và truy vấn khoảng cách Cosine `1 - (embedding <=> query)` trực tiếp trên cơ sở dữ liệu Supabase đám mây với độ tương đồng đạt **1.0000** hoàn hảo!

