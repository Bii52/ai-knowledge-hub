# BÀI HỌC 01: KHỞI TẠO KIẾN TRÚC LÕI FASTAPI CHO AI SERVICE

> **Dành cho**: Nhà phát triển muốn làm chủ kiến trúc Python FastAPI trong các dự án SaaS & AI RAG thực chiến.  
> **Dự án**: AI Knowledge Hub (`apps/ai-service`)  
> **Tác giả & Cố vấn**: Senior Software Architect

---

## 1. TỔNG QUAN BẢN CHẤT & TẠI SAO LẠI THIẾT KẾ NHƯ VẬY?

### 1.1. Tại sao chọn FastAPI thay vì Flask hay Django?
Trong các hệ thống AI & RAG hiện đại:
- **Xử lý bất đồng bộ (Asynchronous / `async`/`await`)**: Việc bóc tách văn bản, tính toán vector embeddings và gọi API của LLM (OpenAI/Anthropic) tốn nhiều thời gian I/O. FastAPI được xây dựng trên nền tảng **Starlette** và **ASGI (Asynchronous Server Gateway Interface)**, cho phép xử lý hàng nghìn request đồng thời mà không nghẽn luồng.
- **Tự động ép kiểu & validate dữ liệu với Pydantic v2**: Pydantic v2 được viết bằng ngôn ngữ Rust (`pydantic-core`), tốc độ validate dữ liệu nhanh gấp 5-10 lần Pydantic v1. Nó ngăn chặn triệt để dữ liệu sai kiểu trước khi đi vào pipeline AI.
- **Tự động sinh tài liệu OpenAPI / Swagger**: Khi bạn viết code bằng FastAPI, hệ thống tự động sinh ra trang web test API trực quan tại `/docs`, giúp bạn test trực tiếp mà không cần viết giao diện Frontend trước.

### 1.2. Cấu trúc thư mục được tổ chức như thế nào?
```text
apps/ai-service/
├── .venv/                  # Môi trường ảo Python (Virtual Environment) cô lập
├── app/
│   ├── __init__.py         # Biến thư mục app thành một Python Package
│   ├── core/
│   │   ├── __init__.py     # Package core
│   │   └── config.py       # Module quản lý cấu hình tập trung (Pydantic Settings)
│   └── main.py             # Điểm khởi chạy ứng dụng (Entrypoint), CORS, Lifespan
├── tests/
│   ├── __init__.py         # Package tests
│   └── test_health.py      # Unit test kiểm tra endpoint /health
├── .env                    # Lưu trữ bí mật (Secret keys, URL DB)
├── .env.example            # Bản mẫu cấu hình cho các lập trình viên khác
└── requirements.txt        # Danh sách thư viện cần thiết
```

---

## 2. GIẢI THÍCH CHI TIẾT CÁC CÂU LỆNH TERMINAL

### Lệnh 1: Khởi tạo môi trường ảo Python
```powershell
python -m venv apps/ai-service/.venv
```
- **`python -m venv`**: Gọi module có sẵn `venv` của Python để tạo một môi trường biệt lập.
- **`apps/ai-service/.venv`**: Đường dẫn thư mục chứa môi trường ảo.
- **Tại sao phải làm vậy?**: Tránh việc cài thư viện tràn lan vào Python gốc của hệ điều hành Windows, gây xung đột phiên bản giữa các dự án khác nhau.

### Lệnh 2: Kích hoạt môi trường ảo (Virtualenv)
```powershell
# Trên Windows PowerShell:
.\apps\ai-service\.venv\Scripts\Activate.ps1
```
- Khi kích hoạt thành công, đầu dòng terminal của bạn sẽ xuất hiện tiền tố `(.venv)`.
- Tất cả các lệnh `python`, `pip` sau đó sẽ chỉ tác động bên trong thư mục này.

### Lệnh 3: Cài đặt thư viện từ `requirements.txt`
```powershell
.\apps\ai-service\.venv\Scripts\python.exe -m pip install -r apps/ai-service/requirements.txt
```
- **`-r requirements.txt`**: Cờ `-r` (recursive/reference) yêu cầu `pip` đọc và cài đặt từng dòng thư viện được liệt kê trong tệp.

### Lệnh 4: Khởi chạy máy chủ phát triển (Development Server)
```powershell
cd apps/ai-service
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- **`uvicorn`**: Web server ASGI chuẩn công nghiệp cho Python.
- **`app.main:app`**: 
  - `app.main`: Tệp `app/main.py`.
  - `:app`: Biến instance `app = FastAPI(...)` bên trong tệp đó.
- **`--port 8000`**: Cổng mở API (khớp với `AI_SERVICE_URL` của NestJS).
- **`--reload`**: Chế độ tự động phát hiện code thay đổi và khởi động lại server ngay lập tức (Hot-reload).

---

## 3. GIẢI THÍCH CHI TIẾT TỪNG DÒNG CODE

### 3.1. Tệp Quản lý Cấu hình: `app/core/config.py`

```python
from functools import lru_cache
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
```
- **`functools.lru_cache`**: Hàm decorator của Python dùng để lưu vào bộ nhớ đệm (cache) kết quả của một hàm. Tránh việc mỗi lần cần cấu hình lại phải đọc file đĩa `.env` nhiều lần.
- **`pydantic_settings.BaseSettings`**: Lớp cha quyền năng của Pydantic. Mọi thuộc tính khai báo trong class kế thừa `BaseSettings` sẽ tự động tìm kiếm biến môi trường tương ứng trong file `.env` hoặc biến hệ thống (OS Environment).

```python
class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Server Configuration
    ENVIRONMENT: str = Field(default="development", description="Environment mode")
    PORT: int = Field(default=8000, description="Port to run the service")
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:3001"],
        description="Allowed CORS origins",
    )
```
- **`Field(default=..., description=...)`**: Đặt giá trị mặc định phòng trường hợp lập trình viên quên không điền trong file `.env`. Nếu không có `.env`, server vẫn chạy an toàn với giá trị fallback.
- **`CORS_ORIGINS`**: Danh sách các tên miền được phép gửi request đến API AI:
  - `http://localhost:3000`: Frontend Next.js.
  - `http://localhost:3001`: Backend NestJS.

```python
    # Database Configuration (Supabase PostgreSQL + pgvector)
    DATABASE_URL: str = Field(default="", description="PostgreSQL connection string with pgvector support")

    # Supabase Object Storage (S3-compatible)
    STORAGE_ENDPOINT_URL: str = Field(default="", description="Supabase S3 storage endpoint URL")
    STORAGE_REGION: str = Field(default="eu-west-1", description="Storage region")
    STORAGE_ACCESS_KEY: str = Field(default="", description="S3 Access Key ID")
    STORAGE_SECRET_KEY: str = Field(default="", description="S3 Secret Access Key")
    STORAGE_BUCKET_NAME: str = Field(default="ai-knowledge-hub", description="Bucket name for documents")

    # Embeddings & AI Model
    EMBEDDING_MODEL: str = Field(default="text-embedding-3-small")
    EMBEDDING_DIMENSION: int = Field(default=1536)
    OPENAI_API_KEY: str = Field(default="")
```
- Các biến này khớp 100% với thông tin kết nối chúng ta đã kiểm thử thành công ở Backend NestJS (Supabase DB, Supabase Storage S3).
- `EMBEDDING_DIMENSION = 1536`: Đây là kích thước không gian vector của model OpenAI `text-embedding-3-small`, khớp đúng với định nghĩa `vector(1536)` trong database schema Prisma.

```python
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
```
- **`model_config`**: Chỉ định cho Pydantic biết phải tự động nạp file `.env`. Cờ `extra="ignore"` giúp bỏ qua các biến thừa mà không làm sập ứng dụng.

```python
@lru_cache()
def get_settings() -> Settings:
    """Singleton getter for application settings."""
    return Settings()
```
- Áp dụng **Singleton Pattern**: Hàm này chỉ khởi tạo đối tượng `Settings` một lần duy nhất trong toàn bộ vòng đời của server.

---

### 3.2. Tệp Khởi Chạy Chính: `app/main.py`

```python
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
```
- **`asynccontextmanager`**: Tiện ích tạo hàm quản lý ngữ cảnh bất đồng bộ (dùng cú pháp `async with`).
- **`CORSMiddleware`**: Bộ lọc bảo mật trình duyệt, chỉ cho phép các trang web được cấp phép gửi request.

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan event handler for startup and shutdown procedures."""
    logger.info("Starting AI Knowledge Hub - AI Core Service...")
    logger.info(f"Environment: {settings.ENVIRONMENT} | Port: {settings.PORT}")
    logger.info(f"Embedding Model: {settings.EMBEDDING_MODEL} (dim: {settings.EMBEDDING_DIMENSION})")

    yield

    logger.info("Shutting down AI Core Service cleanly...")
```
- **Cơ chế Lifespan (Chuẩn mới nhất của FastAPI thay thế `@app.on_event("startup")`)**:
  - Đoạn code **trước chữ `yield`**: Sẽ chạy khi server **BẮT ĐẦU KHỞI ĐỘNG** (nơi ta kết nối database pool, load trước AI model).
  - Đoạn code **sau chữ `yield`**: Sẽ chạy khi server **TẮT HOẶC NHẬN TÍN HIỆU DỪNG** (nơi ta đóng kết nối database, giải phóng RAM an toàn).

```python
app = FastAPI(
    title="AI Knowledge Hub - AI Core Service",
    description="Python FastAPI service handling Text Extraction, Semantic Chunking, Embeddings, and RAG Pipeline.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)
```
- Khởi tạo thực thể `app`. Đường dẫn tài liệu tự động Swagger UI được gán tại `/docs`.

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```
- Đăng ký bộ lọc CORS: Cho phép đầy đủ các phương thức HTTP (`GET`, `POST`, `PUT`, `DELETE`) từ các nguồn uy tín.

```python
@app.get(
    "/health",
    status_code=status.HTTP_200_OK,
    tags=["Health"],
    summary="Health check endpoint",
)
async def health_check() -> dict[str, str]:
    """Health check endpoint to verify service availability."""
    return {
        "status": "ok",
        "app": "AI Knowledge Hub - AI Core Service",
        "environment": settings.ENVIRONMENT,
    }
```
- **Endpoint `/health`**: Đây là tiêu chuẩn vàng của hệ thống microservices. Kubernetes, Docker, hoặc NestJS API có thể ping vào đây định kỳ để biết AI Service còn sống hay đã chết.

---

### 3.3. Tệp Kiểm Thử: `tests/test_health.py`

```python
import asyncio
from app.main import root, health_check

def test_root_endpoint() -> None:
    data = asyncio.run(root())
    assert data["status"] == "online"
    assert "service" in data

def test_health_check_endpoint() -> None:
    data = asyncio.run(health_check())
    assert data["status"] == "ok"
```
- **Tại sao gọi trực tiếp `root()` và `health_check()`?**: Trong FastAPI, các hàm xử lý route thực chất là các hàm Python tiêu chuẩn. Việc gọi trực tiếp qua `asyncio.run()` giúp kiểm thử nhanh như chớp (0.5 giây), không cần mở port mạng thực tế.

---

## 4. BÀI TẬP THỰC HÀNH TỰ KIỂM TRA

Bạn hãy mở Terminal của mình và gõ các lệnh sau để tự trải nghiệm thành quả:

1. **Chạy test tự động**:
   ```powershell
   cd "d:\Dự án\AI Knowledge Hub\apps\ai-service"
   .\.venv\Scripts\python.exe -m pytest tests -p no:asyncio -v
   ```
   *(Kết quả sẽ báo `2 passed in 0.50s` màu xanh lá).*

2. **Khởi động server AI**:
   ```powershell
   .\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000 --reload
   ```
   *(Mở trình duyệt truy cập `http://localhost:8000/docs` bạn sẽ thấy giao diện Swagger UI tuyệt đẹp).*

