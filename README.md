# AI Presentation Coach --- MVP Documentation

Bộ tài liệu này định nghĩa phạm vi, kiến trúc, dữ liệu, API, AI
evaluation và kế hoạch triển khai MVP trong 7 ngày.

## Mục tiêu

Xây dựng một web application giúp sinh viên cải thiện kỹ năng thuyết
trình thông qua **feedback có bằng chứng và có thể hành động**. Điểm số
chỉ là thông tin tham khảo; giá trị cốt lõi là nhận xét, giải thích và
hướng dẫn cải thiện.

## Tài liệu

  -----------------------------------------------------------------------
  File                                Nội dung
  ----------------------------------- -----------------------------------
  `SRS_MVP.md`                        Yêu cầu sản phẩm và phạm vi MVP

  `ARCHITECTURE_MVP.md`               Kiến trúc hệ thống và luồng xử lý

  `DATABASE.md`                       Mô hình dữ liệu MVP

  `API.md`                            Quy ước và API endpoints

  `AI_EVALUATION.md`                  AI pipeline, feedback schema và
                                      nguyên tắc đánh giá

  `RUBRIC_SPECIFICATION.md`           Cách chuẩn hóa rubric và trạng thái
                                      đánh giá

  `UI_UX.md`                          Sitemap và yêu cầu giao diện

  `DEVELOPMENT_PLAN.md`               Kế hoạch triển khai 7 ngày

  `TASKS.md`                          Task và acceptance criteria

  `AGENTS.md`                         Quy tắc làm việc cho AI coding
                                      agent
  -----------------------------------------------------------------------

## Quyết định đã chốt

-   Đối tượng chính: sinh viên tự đánh giá bài presentation.
-   Input MVP: slide PDF/PPTX và audio MP3/WAV/M4A hoặc video MP4 (video
    chỉ trích xuất audio trong MVP).
-   Ngôn ngữ bài presentation: tiếng Anh.
-   Thời lượng thường gặp: 10--20 phút; không hard-code giới hạn này.
-   Có bài cá nhân và bài nhóm; nhóm nhập tên và khoảng thời gian trình
    bày của từng thành viên.
-   Feedback-first, score-second.
-   Báo cáo phải có strengths, areas for improvement, evidence, impact
    và actionable recommendations.
-   Chatbot phải sử dụng ngữ cảnh của Evaluation.
-   Lưu lịch sử Evaluation và chat.
-   Thiếu dữ liệu: đánh dấu `NOT_EVALUATED`, không tự cho 0 hoặc đoán.
-   Bài nhóm: có nhận xét cấp nhóm và cá nhân theo tiêu chí phù hợp.
-   MVP chưa phân tích eye contact/posture; video chỉ dùng làm nguồn
    audio.
-   MVP chưa có Revision Tracker hoàn chỉnh, export PDF hoặc phân tích
    teamwork nâng cao.
-   Mục tiêu 7 ngày: deploy MVP để demo và cho người khác dùng thử; chưa
    phải production-grade.

## Công nghệ định hướng

-   Frontend: React + TypeScript + Vite, Tailwind CSS, shadcn/ui.
-   Backend: Python + FastAPI.
-   Database/Auth/Storage: Supabase (PostgreSQL, Supabase Auth, Supabase
    Storage).
-   AI: API speech-to-text và LLM; model cụ thể cấu hình qua environment
    variables.
-   File processing: PyMuPDF, python-pptx, FFmpeg.
-   Hosting: Vercel (frontend), Render (backend).

## Cách dùng

1.  Đọc `SRS_MVP.md` và `AGENTS.md` trước khi code.
2.  Dùng `ARCHITECTURE_MVP.md`, `DATABASE.md`, `API.md` làm chuẩn triển
    khai.
3.  Dùng `AI_EVALUATION.md` và `RUBRIC_SPECIFICATION.md` để xây dựng AI
    evaluator.
4.  Hoàn thành từng task trong `TASKS.md`; không làm tính năng ngoài MVP
    nếu chưa được xác nhận.
5.  Khi có quyết định mới, cập nhật tài liệu liên quan trước khi sửa
    code.


## Quick Start (Local Development)

### 1. Backend (FastAPI)
```powershell
# Chạy từ thư mục gốc
$env:PYTHONPATH="backend"
.\backend\venv\Scripts\uvicorn app.main:app --reload --port 8000
```
Backend chạy tại: `http://localhost:8000` (Swagger docs: `http://localhost:8000/api/docs`)

Chạy unit tests:
```powershell
$env:PYTHONPATH="backend"
.\backend\venv\Scripts\pytest -v
```

### 2. Frontend (React + Vite + Tailwind)
```powershell
cd frontend
npm run dev
```
Frontend chạy tại: `http://localhost:5173`

## Deployment (Day 7 Guide)

### 1. Backend (Render)
1. Push repository lên GitHub/GitLab (không commit `.env`).
2. Trên Render, chọn **New + → Blueprint** và trỏ tới `render.yaml` (hoặc tạo **Web Service** dùng **Docker** với Dockerfile `backend/Dockerfile` và Docker Context `backend`).
3. Cấu hình các biến môi trường bắt buộc trên Render:
   - `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`
   - `AI_PROVIDER` (`gemini` hoặc `openai`), `GEMINI_API_KEY` (hoặc `OPENAI_API_KEY`)
   - `ALLOWED_ORIGINS` (URL frontend đã deploy, ví dụ `https://your-app.vercel.app`)
4. Kiểm tra sau khi deploy:
   - `GET https://<render-service>.onrender.com/health` trả về `{"status":"ok"}`.
   - `GET https://<render-service>.onrender.com/api/health/runtime` xác nhận `ffmpeg_available: true`, `ai_configured: true`, `supabase_configured: true`.

### 2. Frontend (Vercel)
1. Trên Vercel, chọn **Add New → Project** và import repository.
2. Đặt **Root Directory** là `frontend` (Build Command: `npm run build`, Output Directory: `dist`; file `frontend/vercel.json` đã cấu hình sẵn SPA rewrite).
3. Cấu hình biến môi trường trên Vercel:
   - `VITE_API_BASE_URL` = `https://<render-service>.onrender.com`
   - `VITE_SUPABASE_URL`
   - `VITE_SUPABASE_ANON_KEY`
4. Deploy và lấy URL `https://<your-app>.vercel.app`.

### 3. CORS & Supabase Auth Redirects
1. Trên Render, cập nhật `ALLOWED_ORIGINS` thành `https://<your-app>.vercel.app` (có thể thêm `,http://localhost:5173` nếu test local).
2. Trên **Supabase Dashboard → Authentication → URL Configuration**:
   - **Site URL**: `https://<your-app>.vercel.app`
   - **Redirect URLs**: `https://<your-app>.vercel.app/**`
3. Đảm bảo đã chạy toàn bộ `supabase_schema.sql` trong Supabase SQL Editor (bao gồm bucket `presentations` private và RLS policies).

## Demo Instructions (Dành cho người dùng thử)

1. Truy cập URL frontend trên Vercel, chọn **Sign up** để tạo tài khoản (hoặc đăng nhập bằng tài khoản demo).
2. Nhấn **New Evaluation**, nhập tiêu đề, chủ đề, mục tiêu, đối tượng nghe và chọn **Individual** hoặc **Group** (nếu Group, thêm tên thành viên và khoảng thời gian dự kiến).
3. Trong trang Project, upload:
   - **Slides**: `.pdf` hoặc `.pptx` (tối đa 20MB).
   - **Audio / Video**: `.mp3`, `.wav`, `.m4a` hoặc `.mp4` (tối đa 50MB; video được trích xuất audio bằng FFmpeg).
4. Nhấn **Start Evaluation** và chờ trạng thái chuyển sang `COMPLETED` hoặc `PARTIAL`.
5. Đọc báo cáo theo thứ tự **Feedback-first**: tóm tắt tổng quan → hành động ưu tiên → điểm mạnh → điểm cần cải thiện (kèm bằng chứng/khuyến nghị) → bảng tiêu chí rubric ở cuối trang.
6. Nhấn **Ask AI Coach** để hỏi đáp dựa trên bằng chứng của bài thuyết trình, sau đó thử đăng xuất, đăng nhập lại và mở lại báo cáo + lịch sử chat từ tab **History** trên Dashboard.
