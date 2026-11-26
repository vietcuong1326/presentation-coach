# 7-Day Development Plan

Capacity: one developer, 4--6 hours/day (28--42 hours total).\
Target: deployed MVP for real-user demo, not production-grade scale.

## Scope freeze

Must ship: - Auth. - Project creation. - PDF/PPTX + audio/video
upload. - Slide text extraction. - Audio extraction from MP4. -
Speech-to-text. - Evidence-based feedback report. - Evaluation-context
chatbot. - Evaluation history. - Basic ownership isolation. -
Deployment.

Defer: - Eye contact/posture. - Visual video analysis. - Advanced
teamwork scoring. - Revision Tracker. - PDF export. - Admin rubric
management portal. - Advanced analytics and notifications.

## Day 1 --- Foundation (5h)

-   1h: create repo, frontend and backend skeleton.
-   1h: create Supabase project, auth and private storage.
-   1.5h: implement login/register and token flow.
-   1.5h: dashboard shell and health/API connection.

Deliverable: authenticated user can open deployed/local app and call
backend.

## Day 2 --- Work Space and files (5h)

-   1h: create core database tables.
-   1.5h: Project creation and member form.
-   1h: private file upload.
-   1.5h: PDF/PPTX extraction and MP4 audio extraction.

Deliverable: user creates Project, uploads supported files and sees
extracted slide text.

## Day 3 --- AI pipeline (6h)

-   1.5h: speech-to-text integration and transcript persistence.
-   1h: normalized analysis input.
-   2.5h: evidence extraction, criterion evaluation and feedback
    synthesis.
-   1h: schema validation and report persistence.

Deliverable: sample presentation produces structured feedback with
evidence and partial statuses.

## Day 4 --- Report UI (5h)

-   2h: overall summary, strengths, improvements and priority actions.
-   1.5h: evidence viewer with timestamp/page.
-   1h: criterion details and partial score display.
-   0.5h: loading/error/empty states.

Deliverable: user can read a useful report.

## Day 5 --- Chatbot (5h)

-   0.75h: chat tables/session persistence.
-   2h: evaluation-context chat service and prompt.
-   1.5h: chat UI and history.
-   0.75h: tests for grounding and access control.

Deliverable: user asks about feedback and gets grounded answers; chat
persists.

## Day 6 --- Integration and security (4h)

-   1h: dashboard/history integration.
-   1h: reopen old report and chat.
-   1.5h: ownership/RLS/storage permission checks.
-   0.5h: end-to-end test.

Deliverable: main flow works across a returning session.

## Day 7 --- Deployment and verification (5h)

-   1h: deploy backend.
-   0.75h: deploy frontend and configure environment.
-   0.75h: Supabase redirect, CORS, storage and RLS verification.
-   1.5h: deployed end-to-end tests.
-   1h: fix critical bugs, README and demo setup.

Deliverable: public app URL and backend URL; one sample Evaluation
completes online.

## Schedule risk rule

Deploy a minimal vertical slice by Day 2 or Day 3. Do not wait until Day
7 to discover hosting, CORS, FFmpeg or environment problems.

## Cut line

If behind schedule: 1. Keep auth, project, upload, AI report and
chatbot. 2. Reduce supported formats rather than weakening validation.
3. Defer individual group breakdown if attribution is unreliable. 4.
Defer rich animations and nonessential dashboard widgets. 5. Never
remove ownership checks or secret management to save time.
