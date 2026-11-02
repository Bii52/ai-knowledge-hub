# AI KNOWLEDGE HUB

## PROJECT OVERVIEW & PRODUCT BLUEPRINT

**Phiên bản:** 1.0\
**Loại dự án:** SaaS Web Application -- AI-powered Knowledge Management\
**Định hướng:** Portfolio Project -- Full-stack Development -- AI
Engineering\
**Kiến trúc AI:** Retrieval-Augmented Generation (RAG)

------------------------------------------------------------------------

# 1. GIỚI THIỆU DỰ ÁN

## 1.1. AI Knowledge Hub là gì?

AI Knowledge Hub là một nền tảng quản lý tài liệu và khai thác tri thức
bằng trí tuệ nhân tạo (AI).

Người dùng có thể tải tài liệu cá nhân hoặc tài liệu công việc lên hệ
thống. AI sẽ tự động đọc, phân tích, chia nhỏ nội dung, tạo embeddings
và lưu trữ dữ liệu dưới dạng vector.

Sau đó, người dùng có thể trò chuyện với AI để đặt câu hỏi dựa trên nội
dung tài liệu đã tải lên.

Thay vì phải mở từng file PDF, Word hoặc TXT để tìm kiếm thông tin,
người dùng chỉ cần hỏi bằng ngôn ngữ tự nhiên.

**Ví dụ:** Người dùng tải lên tài liệu học lập trình Java, hướng dẫn sử
dụng hệ thống, báo cáo kinh doanh hoặc tài liệu API. Sau đó có thể yêu
cầu AI tóm tắt, giải thích, so sánh nội dung hoặc tìm thông tin cụ thể
trong tài liệu.

AI sẽ tìm kiếm nội dung liên quan trong kho tài liệu và tạo câu trả lời
kèm nguồn tham chiếu.

## 1.2. Vấn đề mà dự án giải quyết

  Vấn đề                              Giải pháp của AI Knowledge Hub
  ----------------------------------- --------------------------------
  Có quá nhiều tài liệu               Quản lý tập trung
  Khó tìm kiếm thông tin              Tìm kiếm ngữ nghĩa bằng AI
  Phải đọc tài liệu dài               AI tóm tắt nội dung
  Khó tra cứu nhiều file              Chat với nhiều tài liệu
  Không biết AI lấy thông tin ở đâu   Trích dẫn nguồn tài liệu
  Khó quản lý tài liệu theo nhóm      Workspace và phân quyền

## 1.3. Đối tượng sử dụng

-   **Sinh viên:** Quản lý giáo trình, tài liệu học tập và nghiên cứu.
-   **Lập trình viên:** Tra cứu tài liệu kỹ thuật, API và source
    documentation.
-   **Nhân viên văn phòng:** Tìm kiếm thông tin trong báo cáo, quy trình
    và tài liệu nội bộ.
-   **Doanh nghiệp:** Xây dựng kho tri thức dùng chung cho các phòng
    ban.

------------------------------------------------------------------------

# 2. MỤC TIÊU SẢN PHẨM

AI Knowledge Hub hướng đến việc xây dựng một hệ thống có khả năng:

1.  Quản lý tài liệu tập trung.
2.  Tổ chức tài liệu theo Workspace.
3.  Tự động xử lý tài liệu bằng AI.
4.  Tìm kiếm nội dung theo ngữ nghĩa.
5.  Trò chuyện với một hoặc nhiều tài liệu.
6.  Trả lời câu hỏi kèm trích dẫn nguồn.
7.  Quản lý lịch sử hội thoại.
8.  Bảo vệ dữ liệu theo người dùng và Workspace.

## 2.1. Định hướng dài hạn

Sau khi hoàn thành MVP, hệ thống có thể phát triển thêm:

-   Hỗ trợ Excel, PowerPoint và nhiều định dạng tài liệu khác.
-   OCR để đọc tài liệu scan và hình ảnh.
-   So sánh nhiều tài liệu.
-   Tạo báo cáo tự động.
-   AI Agents thực hiện các tác vụ phức tạp.
-   Chia sẻ kho tri thức cho nhóm.
-   Tích hợp Slack, Google Drive, Notion hoặc Microsoft 365.
-   Thanh toán và quản lý gói SaaS.

------------------------------------------------------------------------

# 3. CÁC CHỨC NĂNG CỦA HỆ THỐNG

## 3.1. Authentication -- Xác thực người dùng

Người dùng có thể:

-   Đăng ký tài khoản.
-   Đăng nhập.
-   Đăng xuất.
-   Làm mới Access Token.
-   Xem và cập nhật thông tin cá nhân.
-   Quản lý phiên đăng nhập.

Công nghệ dự kiến:

-   NestJS Authentication.
-   JWT Access Token.
-   Refresh Token.
-   Password hashing bằng Argon2 hoặc bcrypt.

## 3.2. Workspace Management -- Quản lý không gian làm việc

Workspace là nơi tổ chức tài liệu và thành viên.

Ví dụ, người dùng có thể tạo:

-   Workspace: Java Learning.
-   Workspace: AI Research.
-   Workspace: Company Documents.

Mỗi Workspace có dữ liệu và quyền truy cập độc lập.

Các chức năng:

-   Tạo Workspace.
-   Cập nhật Workspace.
-   Xóa Workspace.
-   Mời thành viên.
-   Quản lý thành viên.
-   Phân quyền thành viên.

Vai trò dự kiến:

-   **Owner:** Chủ sở hữu.
-   **Admin:** Quản trị Workspace.
-   **Member:** Thành viên sử dụng.

## 3.3. Document Management -- Quản lý tài liệu

Đây là chức năng cốt lõi đầu tiên.

Người dùng có thể:

-   Upload PDF.
-   Upload DOCX.
-   Upload TXT.
-   Xem danh sách tài liệu.
-   Xem thông tin tài liệu.
-   Xóa tài liệu.
-   Theo dõi trạng thái xử lý.

Mỗi tài liệu có trạng thái:

  Trạng thái   Ý nghĩa
  ------------ ------------------
  Pending      Đang chờ xử lý
  Processing   Đang xử lý
  Completed    Xử lý thành công
  Failed       Xử lý thất bại

Thông tin tài liệu gồm:

-   Tên file.
-   Loại file.
-   Kích thước.
-   Người tải lên.
-   Workspace.
-   Thời gian tải lên.
-   Trạng thái xử lý.

## 3.4. AI Document Processing -- Xử lý tài liệu bằng AI

Sau khi upload, hệ thống tự động xử lý tài liệu.

Quy trình:

1.  Nhận file từ người dùng.
2.  Kiểm tra định dạng và kích thước.
3.  Lưu file vào Object Storage.
4.  Đưa công việc vào hàng đợi.
5.  AI Service đọc nội dung.
6.  Làm sạch nội dung.
7.  Chia nhỏ văn bản thành các đoạn (Chunks).
8.  Tạo Embeddings cho từng đoạn.
9.  Lưu nội dung và vector vào PostgreSQL.
10. Cập nhật trạng thái Completed.

Một tài liệu có 100 trang có thể được chia thành nhiều đoạn nhỏ để AI
tìm kiếm hiệu quả hơn.

Một đoạn (chunk) có thể chứa:

-   Nội dung văn bản.
-   Số trang.
-   Vị trí trong tài liệu.
-   Document ID.
-   Workspace ID.
-   Embedding vector.

## 3.5. AI Chat -- Trò chuyện với tài liệu

Đây là chức năng quan trọng nhất của sản phẩm.

Người dùng có thể:

-   Tạo cuộc hội thoại.
-   Chọn một hoặc nhiều tài liệu.
-   Đặt câu hỏi.
-   Nhận câu trả lời từ AI.
-   Xem nguồn tham chiếu.
-   Tiếp tục hội thoại.
-   Xem lịch sử trò chuyện.

**Ví dụ câu hỏi:** "JWT Refresh Token hoạt động như thế nào theo tài
liệu của tôi?"

AI trả lời dựa trên nội dung được truy xuất và hiển thị nguồn tham
chiếu, chẳng hạn tên file, số trang và đoạn nội dung liên quan.

AI phải ưu tiên trả lời dựa trên tài liệu được phép truy cập, không tự
bịa thông tin khi không tìm thấy bằng chứng.

## 3.6. Conversation Management -- Quản lý hội thoại

Các chức năng:

-   Tạo hội thoại mới.
-   Đổi tên hội thoại.
-   Xem danh sách hội thoại.
-   Xóa hội thoại.
-   Xem nội dung tin nhắn cũ.
-   Tiếp tục hội thoại trước đó.

------------------------------------------------------------------------

# 4. KIẾN TRÚC HỆ THỐNG

Dự án sử dụng kiến trúc tách biệt Frontend, Backend và AI Service.

## 4.1. Tổng quan công nghệ

  Thành phần      Công nghệ                    Nhiệm vụ
  --------------- ---------------------------- -----------------------
  Frontend        Next.js + TypeScript         Giao diện người dùng
  UI              Tailwind CSS + shadcn/ui     Thiết kế giao diện
  Backend         NestJS                       API và nghiệp vụ
  AI Service      Python + FastAPI             Xử lý tài liệu và RAG
  Database        PostgreSQL                   Lưu dữ liệu hệ thống
  Vector Search   pgvector                     Tìm kiếm embeddings
  ORM             Prisma                       Truy vấn Database
  Queue           Redis + BullMQ               Xử lý tác vụ nền
  Storage         Cloudflare R2 / S3           Lưu file
  Container       Docker                       Đóng gói môi trường
  Testing         Vitest / Jest / Playwright   Kiểm thử

## 4.2. Sơ đồ kiến trúc

``` text
                   USER
                    |
                    v
             NEXT.JS FRONTEND
                    |
                    v
              NESTJS BACKEND
                    |
          +---------+----------+
          |         |          |
          v         v          v
      PostgreSQL   Redis    Object Storage
      + pgvector    Queue    (PDF/DOCX/TXT)
          |         |
          |         v
          |      AI SERVICE
          |      FASTAPI
          |         |
          |    +----+-----+
          |    |          |
          |    v          v
          |  Extract    Embedding
          |  Text       Model
          |    |          |
          |    +----+-----+
          |         |
          +---------+
                    |
                    v
               LLM MODEL
                    |
                    v
              AI RESPONSE
                    |
                    v
                FRONTEND
```

## 4.3. Vai trò từng thành phần

### Frontend -- Next.js

-   Hiển thị giao diện.
-   Quản lý trạng thái người dùng.
-   Upload tài liệu.
-   Gửi câu hỏi đến Backend.
-   Hiển thị câu trả lời và nguồn tham chiếu.

### Backend -- NestJS

-   Authentication.
-   Authorization.
-   Quản lý Workspace.
-   Quản lý Document.
-   Quản lý Conversation.
-   Điều phối công việc xử lý AI.
-   Giao tiếp với Database và AI Service.

### AI Service -- FastAPI

-   Đọc PDF, DOCX, TXT.
-   Trích xuất nội dung.
-   Chunking.
-   Embedding.
-   Vector Retrieval.
-   Xây dựng RAG Pipeline.
-   Gọi mô hình LLM.

### PostgreSQL + pgvector

Lưu Users, Workspaces, Memberships, Documents, Document Chunks,
Embeddings, Conversations và Messages.

### Redis + BullMQ

Xử lý các tác vụ mất nhiều thời gian như đọc tài liệu, chia nhỏ nội
dung, tạo Embeddings và xử lý lại tài liệu lỗi.

### Object Storage

Lưu file gốc, không lưu toàn bộ file trực tiếp vào Database.

------------------------------------------------------------------------

# 5. CÔNG NGHỆ AI -- RAG

## 5.1. RAG là gì?

RAG là viết tắt của Retrieval-Augmented Generation.

Đây là phương pháp kết hợp:

-   **Retrieval:** Tìm kiếm thông tin liên quan.
-   **Augmented:** Bổ sung thông tin tìm được vào ngữ cảnh.
-   **Generation:** Dùng AI tạo câu trả lời.

Mục đích là giúp AI trả lời dựa trên nguồn dữ liệu riêng của người dùng.

## 5.2. Quy trình xử lý tài liệu (Ingestion Pipeline)

``` text
Upload Document
       |
       v
Extract Text
       |
       v
Clean Text
       |
       v
Split into Chunks
       |
       v
Generate Embeddings
       |
       v
Store in PostgreSQL
       |
       v
Ready for AI Chat
```

Ví dụ, một đoạn văn:

> NestJS là một framework Node.js được xây dựng bằng TypeScript.

Sau khi tạo Embedding, nội dung được chuyển thành một vector số học đại
diện cho ngữ nghĩa của đoạn văn.

Vector được lưu vào pgvector để phục vụ tìm kiếm tương đồng.

## 5.3. Quy trình hỏi đáp (RAG Pipeline)

``` text
User Question
      |
      v
Generate Query Embedding
      |
      v
Vector Similarity Search
      |
      v
Retrieve Relevant Chunks
      |
      v
Build Prompt + Context
      |
      v
Call LLM
      |
      v
Generate Answer
      |
      v
Return Answer + Citations
```

Ví dụ, khi người dùng hỏi "NestJS có ưu điểm gì?", hệ thống sẽ:

1.  Chuyển câu hỏi thành Embedding.
2.  Tìm các đoạn tài liệu liên quan.
3.  Lấy những đoạn phù hợp nhất.
4.  Gửi câu hỏi và các đoạn tài liệu đến LLM.
5.  Nhận câu trả lời.
6.  Trả kết quả và nguồn tài liệu về Frontend.

## 5.4. Các khái niệm cần nắm

  Khái niệm           Giải thích
  ------------------- ---------------------------------------
  LLM                 Mô hình ngôn ngữ lớn
  Embedding           Chuyển văn bản thành vector
  Chunking            Chia tài liệu thành đoạn nhỏ
  Vector Database     Lưu trữ và tìm kiếm vector
  Similarity Search   Tìm kiếm nội dung tương đồng
  Retrieval           Truy xuất dữ liệu liên quan
  Prompt              Chỉ dẫn gửi đến AI
  Context             Ngữ cảnh cung cấp cho AI
  RAG                 Kết hợp truy xuất và sinh câu trả lời

------------------------------------------------------------------------

# 6. THIẾT KẾ DỮ LIỆU TỔNG QUAN

Các bảng Database dự kiến:

  Bảng                Chức năng
  ------------------- ---------------------------
  users               Người dùng
  workspaces          Không gian làm việc
  workspace_members   Thành viên Workspace
  documents           Thông tin tài liệu
  document_chunks     Nội dung đã chia nhỏ
  conversations       Cuộc hội thoại
  messages            Tin nhắn
  message_sources     Nguồn tài liệu tham chiếu
  refresh_tokens      Phiên làm mới xác thực

Quan hệ dữ liệu cơ bản:

``` text
Users
  |
  +---- Workspace Members
              |
              v
          Workspaces
              |
              +---- Documents
              |        |
              |        v
              |   Document Chunks
              |
              +---- Conversations
                       |
                       v
                    Messages
                       |
                       v
                 Message Sources
```

Thiết kế chi tiết sẽ được hoàn thiện trong tài liệu Database Design
riêng, bao gồm khóa chính, khóa ngoại, indexes và quy tắc xóa dữ liệu.

------------------------------------------------------------------------

# 7. BẢO MẬT HỆ THỐNG

Vì hệ thống lưu tài liệu riêng tư nên bảo mật là yêu cầu bắt buộc.

Các nguyên tắc:

1.  Người dùng chỉ truy cập dữ liệu được cấp quyền.
2.  Mỗi Workspace có phạm vi dữ liệu độc lập.
3.  Backend kiểm tra quyền trước khi truy xuất tài liệu.
4.  AI Service chỉ nhận những dữ liệu đã được Backend xác thực quyền
    truy cập.
5.  Không để API Key của AI trong Frontend.
6.  Không lưu mật khẩu dạng văn bản thuần.
7.  Kiểm tra định dạng và kích thước file upload.
8.  Không cho phép truy cập file bằng URL công khai không kiểm soát.
9.  Xóa tài liệu phải xử lý cả file gốc, chunks và embeddings.
10. Không đưa dữ liệu của Workspace khác vào prompt của AI.

**Nguyên tắc quan trọng nhất:** Phải kiểm tra quyền truy cập trước khi
lấy dữ liệu đưa vào RAG. Không được chỉ dựa vào việc lọc kết quả sau khi
AI đã xử lý dữ liệu.

------------------------------------------------------------------------

# 8. PHẠM VI MVP

MVP là phiên bản đầu tiên có thể sử dụng được.

## 8.1. Chức năng bắt buộc

-   Đăng ký và đăng nhập.
-   Quản lý Workspace.
-   Upload PDF, DOCX, TXT.
-   Theo dõi trạng thái xử lý tài liệu.
-   Trích xuất nội dung.
-   Chunking và Embedding.
-   Lưu Embeddings bằng pgvector.
-   Chat với tài liệu.
-   Trả lời kèm nguồn trích dẫn.
-   Lưu lịch sử hội thoại.
-   Kiểm soát quyền truy cập.

## 8.2. Chưa triển khai trong MVP

-   OCR nâng cao.
-   AI Agents tự động thực hiện tác vụ.
-   Thanh toán SaaS.
-   Tích hợp Google Drive.
-   Tích hợp Microsoft 365.
-   Real-time collaboration.
-   Phân tích dữ liệu nâng cao.
-   Mobile Application.

Những chức năng này sẽ được xem xét sau khi MVP hoạt động ổn định.

------------------------------------------------------------------------

# 9. LỘ TRÌNH PHÁT TRIỂN 12 TUẦN

  Giai đoạn   Nội dung                            Kết quả
  ----------- ----------------------------------- ------------------------------
  Tuần 1      Khởi tạo dự án, kiến trúc, Docker   Môi trường chạy được
  Tuần 2      Database, Prisma, Authentication    Đăng nhập được
  Tuần 3      Workspace và phân quyền             Quản lý Workspace
  Tuần 4      Document Management                 Upload và quản lý file
  Tuần 5      AI Service và Text Extraction       Đọc được tài liệu
  Tuần 6      Chunking và Embeddings              Tạo vector
  Tuần 7      PostgreSQL + pgvector               Vector Search
  Tuần 8      RAG Pipeline                        AI trả lời dựa trên tài liệu
  Tuần 9      Chat và Conversation                Hoàn thiện hội thoại
  Tuần 10     Citation và bảo mật                 Trích dẫn và kiểm soát quyền
  Tuần 11     Testing và tối ưu                   Hệ thống ổn định
  Tuần 12     Deploy và tài liệu                  Hoàn thiện Portfolio

Thời gian trên là kế hoạch tham khảo, có thể điều chỉnh theo tiến độ
thực tế.

------------------------------------------------------------------------

# 10. CẤU TRÚC SOURCE CODE DỰ KIẾN

``` text
AI-KNOWLEDGE-HUB/
│
├── apps/
│   ├── web/
│   │   └── Next.js Frontend
│   │
│   ├── api/
│   │   └── NestJS Backend
│   │
│   └── ai-service/
│       └── Python FastAPI
│
├── infrastructure/
│   ├── docker/
│   ├── postgres/
│   └── redis/
│
├── docs/
│   ├── 01-project-overview.md
│   ├── 02-product-requirements.md
│   ├── 03-system-architecture.md
│   ├── 04-database-design.md
│   ├── 05-api-specification.md
│   ├── 06-ai-rag-pipeline.md
│   ├── 07-security-design.md
│   └── 08-development-roadmap.md
│
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

------------------------------------------------------------------------

# 11. TIÊU CHÍ HOÀN THÀNH DỰ ÁN

Dự án được xem là hoàn thành MVP khi:

-   Người dùng đăng ký và đăng nhập được.
-   Người dùng tạo Workspace được.
-   Upload PDF, DOCX và TXT được.
-   Hệ thống tự động xử lý tài liệu.
-   Có thể tìm kiếm nội dung bằng Vector Search.
-   AI trả lời câu hỏi dựa trên tài liệu.
-   Câu trả lời có nguồn trích dẫn.
-   Người dùng xem lại hội thoại cũ.
-   Không thể truy cập tài liệu trái quyền.
-   Có Unit Test và Integration Test cho các chức năng quan trọng.
-   Có thể chạy hệ thống bằng Docker.
-   Có tài liệu hướng dẫn cài đặt và sử dụng.

------------------------------------------------------------------------

# 12. ĐỊNH HƯỚNG TRIỂN KHAI

AI Knowledge Hub không đơn thuần là một ứng dụng chat với AI.

Đây là một hệ thống Full-stack có tích hợp AI, trong đó mỗi thành phần
có nhiệm vụ rõ ràng:

-   Next.js chịu trách nhiệm giao diện.
-   NestJS chịu trách nhiệm nghiệp vụ và bảo mật.
-   FastAPI chịu trách nhiệm xử lý AI.
-   PostgreSQL chịu trách nhiệm lưu trữ dữ liệu.
-   pgvector chịu trách nhiệm tìm kiếm ngữ nghĩa.
-   Redis và BullMQ chịu trách nhiệm xử lý công việc nền.
-   Object Storage chịu trách nhiệm lưu file.

**Mục tiêu cuối cùng:** Xây dựng một nền tảng có thể biến kho tài liệu
thông thường thành một kho tri thức có thể tìm kiếm, phân tích và trò
chuyện bằng AI.

Đây là nền tảng để phát triển thành một sản phẩm SaaS thực tế và đồng
thời là một dự án Portfolio thể hiện năng lực Full-stack Development kết
hợp AI Engineering.

------------------------------------------------------------------------

## TÀI LIỆU TIẾP THEO

Sau tài liệu tổng quan này, dự án sẽ có các tài liệu kỹ thuật riêng:

1.  **Product Requirements Document (PRD):** Mô tả chi tiết từng chức
    năng và luồng người dùng.
2.  **System Architecture:** Thiết kế cách các thành phần giao tiếp.
3.  **Database Design:** Thiết kế bảng, khóa và quan hệ dữ liệu.
4.  **API Specification:** Định nghĩa các API.
5.  **AI/RAG Pipeline:** Thiết kế quy trình xử lý AI.
6.  **Security Design:** Quy tắc bảo mật và phân quyền.
7.  **Development Roadmap:** Theo dõi tiến độ triển khai.
