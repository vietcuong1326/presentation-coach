# MVP Task Board

Use this file as the single source of truth for implementation progress.
Mark tasks only after testing.

## Day 1 --- Foundation

-   [x] D1-01 Create Git repository and frontend/backend skeleton.
    -   Acceptance: both apps start locally; README contains commands.
-   [x] D1-02 Configure Supabase project, Auth and private Storage.
    -   Acceptance: test user can sign up/sign in.
-   [x] D1-03 Implement frontend auth flow.
    -   Acceptance: protected route redirects unauthenticated user.
-   [x] D1-04 Implement FastAPI health endpoint and token verification.
    -   Acceptance: valid token accepted; invalid token rejected.
-   [x] D1-05 Create dashboard shell and API client.
    -   Acceptance: frontend displays backend health response.

## Day 2 --- Project and files

-   [x] D2-01 Create database tables and RLS policies.
    -   Acceptance: two test users cannot read each other's projects.
-   [x] D2-02 Implement Project CRUD.
    -   Acceptance: create and retrieve owned Project.
-   [x] D2-03 Implement group member/time-range form.
    -   Acceptance: validate start \< end and flag overlaps.
-   [x] D2-04 Implement private file upload.
    -   Acceptance: supported file stored; unauthorized user cannot
        fetch it.
-   [x] D2-05 Implement PDF/PPTX text extraction.
    -   Acceptance: sample files produce text with page/slide
        references.
-   [x] D2-06 Implement MP4 audio extraction.
    -   Acceptance: valid MP4 yields playable/extractable audio; invalid
        file returns safe error.

## Day 3 --- AI pipeline

-   [x] D3-01 Integrate speech-to-text.
    -   Acceptance: sample audio returns transcript and timestamps where
        provider supports them.
-   [x] D3-02 Persist transcript and extraction metadata.
    -   Acceptance: transcript can be reopened by Evaluation owner.
-   [x] D3-03 Define Pydantic report/evidence schemas.
    -   Acceptance: valid sample passes; malformed output is rejected.
-   [x] D3-04 Implement evidence extraction.
    -   Acceptance: evidence points to source/timestamp/page or is
        explicitly ungrounded/omitted.
-   [x] D3-05 Implement criterion evaluator.
    -   Acceptance: missing evidence returns NOT_EVALUATED and null
        score.
-   [x] D3-06 Implement feedback synthesis.
    -   Acceptance: duplicate issues merged; each improvement includes
        impact and recommendation.
-   [x] D3-07 Persist report and Evaluation status.
    -   Acceptance: report saved; status becomes COMPLETED or PARTIAL.

## Day 4 --- Report UI

-   [x] D4-01 Build overall feedback section.
-   [x] D4-02 Build strengths and improvement cards.
-   [x] D4-03 Build evidence/timestamp viewer.
-   [x] D4-04 Build group and individual sections where evidence
    supports attribution.
-   [x] D4-05 Display evaluated/total criteria and partial points.
-   [x] D4-06 Implement loading, empty, partial and failed states.
    -   Acceptance for D4: report page renders real API data, not
        hardcoded mock data.

## Day 5 --- Chatbot

-   [x] D5-01 Create chat session/message persistence.
-   [x] D5-02 Implement ownership-protected chat API.
-   [x] D5-03 Build evaluation context assembler.
-   [x] D5-04 Implement grounded chat prompt and response validation.
-   [x] D5-05 Build chat UI and restore previous messages.
    -   Acceptance: ask "Why this feedback?" and receive answer grounded
        in report evidence.
-   [x] D5-06 Enforce academic integrity guardrail in Chatbot.
    -   Acceptance: Chatbot politely refuses requests to do homework, write full
        presentations, or rewrite entire scripts; offers pedagogical guidance,
        structural feedback, and short sentence-level examples instead.

## Day 6 --- Integration and security

-   [x] D6-01 Build dashboard project/evaluation lists.
-   [x] D6-02 Build history and reopen report.
-   [x] D6-03 Reopen prior chat session.
-   [x] D6-04 Verify API ownership checks for every resource.
-   [x] D6-05 Verify Storage private access and RLS.
-   [x] D6-06 Run complete user journey.
    -   Acceptance: user can create, evaluate, chat, sign out and return
        to old report.

## Day 7 --- Deployment

-   [ ] D7-01 Deploy FastAPI backend.
-   [ ] D7-02 Deploy frontend.
-   [ ] D7-03 Configure environment variables, CORS and auth redirects.
-   [ ] D7-04 Verify FFmpeg and provider credentials in deployed
    runtime.
-   [ ] D7-05 Run deployed end-to-end tests.
-   [ ] D7-06 Fix critical bugs and write demo instructions.
    -   Acceptance: external tester completes one Evaluation from upload
        to chat.

## Definition of done for every task

-   Code follows existing architecture.
-   Relevant tests pass.
-   No secrets committed.
-   Error paths are handled.
-   Documentation updated when behavior/API/schema changes.
-   No unrelated scope added.
