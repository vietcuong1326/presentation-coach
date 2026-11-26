# Architecture --- MVP

Version: 1.0

## 1. Architecture goals

-   Deliver a working MVP within seven days.
-   Keep the implementation modular without premature microservices.
-   Use managed authentication, database and storage.
-   Keep long-running AI/media work outside request-response latency.
-   Make feedback generation testable independently of the UI.

## 2. High-level architecture

``` text
Browser
  |
  v
React + TypeScript (Vercel)
  |
  | HTTPS + Supabase access token
  v
FastAPI (Render)
  |---- Verify user identity / authorize resource ownership
  |---- Project & Evaluation APIs
  |---- File metadata and signed storage access
  |---- Processing coordinator
  |       |---- Slide extractor (PyMuPDF / python-pptx)
  |       |---- FFmpeg audio extraction for MP4
  |       |---- Speech-to-text provider
  |       |---- LLM Evidence & Feedback pipeline
  |
  +---- Supabase PostgreSQL
  +---- Supabase Storage (private buckets)
  +---- External AI APIs
```

## 3. Technology choices

### Frontend

-   React, TypeScript, Vite.
-   React Router.
-   Tailwind CSS and shadcn/ui.
-   TanStack Query or a small equivalent for API state.
-   Supabase JS client for authentication; do not expose service-role
    key.

### Backend

-   Python 3.11+ (pin the exact runtime supported by dependencies).
-   FastAPI, Uvicorn, Pydantic.
-   Supabase Python client or SQLAlchemy/async database access; choose
    one primary persistence approach and avoid duplicate data-access
    patterns.
-   FFmpeg available in the deployment image/environment.
-   PyMuPDF and python-pptx.

### Managed services

-   Supabase Auth, PostgreSQL and private Storage.
-   OpenAI-compatible speech-to-text and LLM APIs.
-   Vercel frontend.
-   Render backend.

## 4. Backend modules

``` text
app/
  api/
    routes/
      health.py
      projects.py
      evaluations.py
      chat.py
  core/
    config.py
    security.py
    errors.py
  schemas/
    project.py
    evaluation.py
    feedback.py
    chat.py
  services/
    file_processing/
      pdf_extractor.py
      pptx_extractor.py
      media_extractor.py
    transcription/
      service.py
    ai_evaluator/
      pipeline.py
      evidence_extractor.py
      criterion_evaluator.py
      feedback_synthesizer.py
      prompts/
    chatbot/
      service.py
      prompts/
  repositories/
  main.py
```

Keep route handlers thin. Business logic belongs in services;
persistence belongs in repositories or one clearly defined data-access
layer.

## 5. Processing flow

1.  Client requests Evaluation creation.
2.  Backend verifies Project ownership and required files.
3.  Backend creates Evaluation with `PENDING`.
4.  Backend schedules processing and returns Evaluation ID.
5.  Worker/background task changes status to `PROCESSING`.
6.  Extract slide text.
7.  Extract audio from uploaded audio/video.
8.  Generate transcript with timestamps where supported.
9.  Build normalized analysis input.
10. Run evidence extraction and criterion evaluation.
11. Synthesize non-redundant feedback.
12. Validate structured output.
13. Persist transcript, evidence, criterion results and report.
14. Set status to `COMPLETED` or `PARTIAL`.
15. On unrecoverable failure, persist safe error details and set
    `FAILED`.

For a one-week MVP, FastAPI BackgroundTasks may be used for low-volume
demos, but it is not a durable job queue. A process restart may
interrupt a task. Keep processing idempotent and document this
limitation. If the deployment environment cannot safely run long tasks,
use a managed job/worker service or reduce media limits.

## 6. File storage

-   Use private Supabase Storage buckets.
-   Store object path, original filename, MIME type, size and
    checksum/metadata.
-   Generate short-lived signed URLs only when needed.
-   Do not store public URLs for private presentation files.
-   Validate actual file type where feasible; do not trust filename
    extension alone.
-   Never execute or render uploaded files as trusted code.

## 7. Authentication and authorization

-   Frontend obtains Supabase access token.
-   Frontend sends `Authorization: Bearer <access_token>` to FastAPI.
-   Backend validates token using trusted Supabase verification.
-   Every Project/Evaluation/Chat operation checks ownership.
-   Supabase RLS policies protect direct client access to
    database/storage.
-   Service-role credentials remain backend-only and must not bypass
    application authorization checks.

## 8. AI orchestration

Use separate logical stages: - Extraction: parse files and create
transcript. - Evidence: collect observations tied to sources. -
Evaluation: map evidence to rubric criteria and status. - Synthesis:
merge duplicate issues and produce prioritized coaching feedback. -
Chat: answer follow-ups using the stored Evaluation context.

Validate every model response against Pydantic schemas. Retry only
bounded transient/format failures. Do not blindly retry expensive calls.

## 9. Deployment

### Vercel

-   Build command: frontend package build script.
-   Output directory: `dist`.
-   Environment: `VITE_API_BASE_URL`, Supabase public URL and anon key.

### Render

-   Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
    (adjust module path to actual project).
-   Environment: Supabase URL, service role key, AI API keys, allowed
    frontend origins, upload limits.
-   Include FFmpeg in the runtime if MP4 processing is enabled.

### Production caveats

-   Verify provider request limits and media duration/size limits.
-   Render filesystem may be ephemeral; do not rely on local files for
    durable storage.
-   Configure CORS narrowly.
-   Add request timeouts and safe error handling.
-   Do not claim production-grade reliability from a single web process
    and in-process background tasks.
