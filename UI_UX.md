# UI/UX Specification --- MVP

## 1. UX principles

-   Feedback-first, score-second.
-   Calm, modern AI product aesthetic; gradient may be used sparingly.
-   Prioritize readability of long feedback.
-   Make evidence easy to inspect.
-   Clearly show missing data and processing states.
-   Desktop-first but responsive.

## 2. Sitemap

``` text
/auth
  /login
  /register

/app
  /dashboard
  /projects/new
  /projects/:projectId
  /evaluations/:evaluationId
    /report
    /chat
  /history
  /settings (basic)
```

## 3. Main screens

### Login/Register

-   Email/password or supported Supabase auth flow.
-   Clear validation and error messages.
-   No secret values in browser logs.

### Dashboard

-   Recent Projects.
-   Recent Evaluations and status.
-   Primary CTA: New Presentation Evaluation.

### New Project / Work Space

-   Project title, topic, objectives, target audience.
-   Individual/Group selection.
-   Member names and optional time ranges.
-   Slide upload and audio/video upload.
-   Supported formats and configured size limits visible.

### Processing

-   Status: Pending, Processing, Completed, Partial, Failed.
-   Explain what stage is running where possible.
-   Failure state includes safe retry guidance.

### Evaluation Report

Recommended order: 1. Overall feedback. 2. Priority improvements. 3.
Strengths. 4. Detailed feedback with evidence. 5. Individual feedback
for group presentation. 6. Rubric details and partial score at the
bottom.

Each feedback card: - Title and severity. - Scope/member. -
Observation. - Evidence and timestamp/page. - Impact. -
Recommendation. - Example rewrite/action where useful. - Related rubric
criteria.

### AI Coach Chat

-   Chat is scoped to the current Evaluation.
-   Suggested prompts: "Explain this feedback", "Help me rewrite this
    part", "How can I improve this transition?"
-   Show conversation history.
-   Indicate when answer is based on stored report vs general guidance.

### History

-   List Evaluations with title, created date and status.
-   Open report and chat.
-   Delete with confirmation.

## 4. States

Every data-driven screen should support: - Loading. - Empty. - Error. -
Partial data. - Success.

Do not show a score badge as the primary visual element. Emphasize
feedback and next actions.
