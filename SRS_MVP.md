# Software Requirements Specification --- MVP

Version: 1.0\
Status: Baseline for 7-day MVP\
Product: AI Presentation Coach

## 1. Product vision

AI Presentation Coach là trợ lý AI giúp sinh viên hiểu bài thuyết trình
của mình đang làm tốt ở đâu, cần cải thiện điều gì, vì sao và nên cải
thiện như thế nào.

**Feedback-first, Score-second.** Điểm số không phải mục tiêu chính và
không được hiển thị lấn át phần nhận xét.

## 2. Users and roles

### 2.1 Student/User

-   Đăng ký, đăng nhập, đăng xuất.
-   Tạo project presentation.
-   Upload slide và audio/video.
-   Khai báo mục tiêu, đối tượng nghe và thông tin thành viên.
-   Chạy Evaluation, xem report và chat với AI.
-   Xem/xóa Evaluation thuộc quyền sở hữu.

### 2.2 Admin

Không xây dựng Admin portal đầy đủ trong MVP. Rubric mặc định được quản
lý bằng cấu hình/tài liệu nội bộ do developer chuẩn bị. Không cho phép
user tự sửa rubric hệ thống trong MVP.

## 3. MVP scope

### In scope

1.  Authentication.
2.  Project creation and management.
3.  Upload PDF/PPTX and MP3/WAV/M4A/MP4.
4.  Extract slide text.
5.  Extract audio from video.
6.  Speech-to-text transcript.
7.  AI feedback based on available evidence and rubric.
8.  Feedback report with strengths, improvements, evidence and
    recommendations.
9.  Partial evaluation when some criteria lack data.
10. Evaluation-context chatbot with persistent chat history.
11. Evaluation history.
12. Deploy frontend, backend, database and storage.

### Out of scope

-   Eye contact and posture analysis.
-   Facial emotion/personality inference.
-   Speaker diarization / automatic identity recognition.
-   Advanced teamwork contribution scoring.
-   Revision Tracker and cross-version comparison.
-   PDF report export.
-   Class/course management.
-   Custom rubric upload/admin workflow.
-   Guaranteed expert-level phoneme/accent diagnosis.
-   Production-scale queue orchestration and autoscaling.

## 4. Core user journey

1.  User signs in.
2.  User creates a Project and enters title, topic, objectives, target
    audience and presentation type.
3.  For group presentations, user adds members and speaking time ranges.
4.  User uploads slide file and audio/video file.
5.  System validates and stores files.
6.  User starts Evaluation.
7.  System extracts slide text and audio, generates transcript, then
    runs AI analysis.
8.  User sees processing status.
9.  System stores report and feedback.
10. User reads report and asks follow-up questions in AI Coach Chat.
11. User can return to the Evaluation later.

## 5. Functional requirements

### Authentication and authorization

-   FR-01: User can sign up, sign in and sign out.
-   FR-02: Protected endpoints require a valid authenticated identity.
-   FR-03: A user can access only their own Projects, Evaluations, files
    and chats.
-   FR-04: Authorization must be checked on the backend and enforced by
    Supabase RLS where applicable.

### Project

-   FR-05: User can create, view, update and delete their own Project.
-   FR-06: Project fields: title, topic, objectives, target audience,
    presentation type, expected duration.
-   FR-07: Presentation type is `INDIVIDUAL` or `GROUP`.
-   FR-08: Group Project can contain members with name and optional
    start/end speaking timestamps.
-   FR-09: Validate `start_time < end_time`; flag ranges outside media
    duration and overlaps for user review. Do not silently infer speaker
    identity.

### Files

-   FR-10: Accept PDF/PPTX slides and MP3/WAV/M4A audio or MP4 video.
-   FR-11: Store files in private object storage; persist metadata and
    storage path.
-   FR-12: Validate file type and configured size limits.
-   FR-13: Extract text from PDF/PPTX.
-   FR-14: For MP4, extract audio using FFmpeg. Video frames are not
    analyzed in MVP.
-   FR-15: Display useful errors for unsupported, unreadable or failed
    files.

### Evaluation

-   FR-16: User can create an Evaluation for a Project.
-   FR-17: Evaluation has status `PENDING`, `PROCESSING`, `COMPLETED`,
    `PARTIAL` or `FAILED`.
-   FR-18: System creates a transcript from audio where possible.
-   FR-19: System evaluates criteria only when adequate evidence is
    available.
-   FR-20: System marks unsupported or insufficiently evidenced criteria
    as `NOT_EVALUATED`; never assign zero by default.
-   FR-21: Report must prioritize qualitative feedback over score.
-   FR-22: Important feedback should include evidence references
    (timestamp, slide/page or source excerpt) when available.
-   FR-23: System stores the rubric version/snapshot used for each
    Evaluation.
-   FR-24: Re-running analysis creates a new report version; do not
    silently overwrite historical results.

### Feedback

-   FR-25: Report includes overall summary, strengths, areas for
    improvement and prioritized recommendations.
-   FR-26: Each improvement item includes observation, evidence, impact
    and recommendation.
-   FR-27: Feedback should be specific, constructive, non-redundant and
    actionable.
-   FR-28: System distinguishes observed facts from interpretation and
    uncertainty.
-   FR-29: System does not infer personality, effort, intelligence or
    motivation from limited media evidence.

### Group evaluation

-   FR-30: Group report includes group-level findings.
-   FR-31: Individual findings are generated only for criteria with
    evidence attributable to a member.
-   FR-32: User-provided time ranges may be used to associate transcript
    segments with members, but are treated as approximate metadata, not
    verified speaker identity.
-   FR-33: Do not equate speaking duration with contribution quality.
-   FR-34: If overlap, cross-talk or uncertain attribution occurs, mark
    affected evidence as uncertain or not attributable.

### Chatbot

-   FR-35: User can chat within an Evaluation.
-   FR-36: Chat context includes Project metadata, rubric snapshot,
    report, feedback and relevant transcript/evidence.
-   FR-37: Chatbot can explain feedback, suggest improved wording and
    offer practice advice.
-   FR-38: Chatbot must not invent timestamps, evidence, scores or facts
    absent from the Evaluation.
-   FR-39: Chat messages are persisted and isolated by user ownership.

### History

-   FR-40: User can list and reopen previous Evaluations.
-   FR-41: User can delete an Evaluation and its associated data
    according to deletion policy.
-   FR-42: Historical reports remain tied to the rubric snapshot and
    report version originally used.

## 6. Non-functional requirements

-   NFR-01 Security: secrets only on server; private storage;
    authorization on every resource access.
-   NFR-02 Privacy: do not expose uploaded media publicly; explain
    external AI processing in the product privacy notice.
-   NFR-03 Reliability: failures produce a clear `FAILED` state and safe
    error message.
-   NFR-04 Data integrity: store source files, transcript, rubric
    snapshot and report version references.
-   NFR-05 Performance: long-running media/AI tasks must not block the
    HTTP request until completion.
-   NFR-06 Usability: show processing status and actionable error
    messages.
-   NFR-07 Maintainability: separate API, processing, AI evaluation and
    persistence logic.
-   NFR-08 Cost control: enforce file-size/duration limits and avoid
    unnecessary repeated AI calls.

## 7. Evaluation principles

1.  Feedback-first, score-second.
2.  Evidence-based: no material criticism without supporting evidence or
    an explicit uncertainty label.
3.  Actionable: explain how to improve.
4.  Non-redundant: merge overlapping observations into one primary
    feedback item and reference affected criteria.
5.  Fair: do not infer unobservable behaviors.
6.  Partial: missing evidence means `NOT_EVALUATED`, not zero.
7.  Transparent: distinguish rubric score, confidence and evidence
    coverage.
8.  Group fairness: separate shared project quality from attributable
    individual performance.

## 8. Acceptance criteria

-   AC-01: User can sign up/sign in and access their own dashboard.
-   AC-02: User A cannot read User B's Project, Evaluation, files or
    chat by guessing IDs.
-   AC-03: User can create a Project and upload supported files.
-   AC-04: System extracts text from a sample PDF and PPTX.
-   AC-05: System extracts audio from a sample MP4.
-   AC-06: System generates transcript from a supported audio sample.
-   AC-07: System produces a report with strengths, improvements,
    evidence and recommendations.
-   AC-08: Missing evidence is represented as `NOT_EVALUATED`.
-   AC-09: Report prioritizes feedback and displays scores as secondary
    information.
-   AC-10: Chatbot answers questions using the selected Evaluation
    context.
-   AC-11: User can reopen a previous report and chat.
-   AC-12: Processing failure is visible and does not silently lose the
    Project.
-   AC-13: Deployed application completes the main user journey with
    real API credentials configured.

## 9. Open decisions / configuration

These must be configured before public use: - Maximum upload size and
maximum media duration. - AI provider/model and API budget. - Data
retention and deletion policy. - Whether registration is open or
invite-only. - Exact official descriptors for each rubric level. -
Privacy notice and consent language for external AI processing.

Until confirmed, use conservative limits and clearly label the rubric
descriptors as provisional.
