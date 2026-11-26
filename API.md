# API Contract --- MVP

Base path: `/api`\
Format: JSON unless uploading multipart files.\
Authentication: `Authorization: Bearer <Supabase access token>`.

## 1. Common conventions

-   Use UUID identifiers.
-   Return consistent error shape:

``` json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "The requested resource was not found."
  }
}
```

-   Do not reveal whether another user's resource exists; return 404 for
    unauthorized resource lookup.
-   Validate request bodies with Pydantic.
-   Use pagination for list endpoints when practical.

## 2. Health

### `GET /health`

Response:

``` json
{"status":"ok"}
```

## 3. Projects

### `GET /api/projects`

List projects owned by the authenticated user.

### `POST /api/projects`

Request:

``` json
{
  "title": "AI in Education",
  "topic": "Artificial Intelligence",
  "objectives": "Explain applications of AI in education",
  "target_audience": "University students",
  "presentation_type": "GROUP",
  "expected_duration_seconds": 900,
  "members": [
    {"name":"Member A","start_time_seconds":0,"end_time_seconds":300},
    {"name":"Member B","start_time_seconds":300,"end_time_seconds":600}
  ]
}
```

### `GET /api/projects/{project_id}`

Return owned Project and members.

### `PATCH /api/projects/{project_id}`

Update allowed Project fields.

### `DELETE /api/projects/{project_id}`

Delete Project according to documented cascade policy.

## 4. Files

### `POST /api/projects/{project_id}/files`

Content-Type: `multipart/form-data`.

Fields: - `file`: binary upload. - `file_role`: `SLIDES`, `AUDIO`,
`VIDEO`, `REPORT`.

Backend validates ownership, size and type, then stores object privately
and returns metadata.

Response:

``` json
{
  "id": "uuid",
  "file_role": "SLIDES",
  "original_filename": "slides.pdf",
  "processing_status": "UPLOADED"
}
```

For large files, prefer direct-to-Supabase signed upload rather than
proxying bytes through the API. The MVP may use a bounded upload path if
deployment limits allow it.

## 5. Evaluations

### `POST /api/projects/{project_id}/evaluations`

Create an Evaluation and start processing.

Response:

``` json
{
  "id": "uuid",
  "status": "PENDING"
}
```

### `GET /api/evaluations/{evaluation_id}`

Return status, safe error information and timestamps.

### `GET /api/evaluations/{evaluation_id}/report`

Return latest report. If not ready, return status and no report payload.

### `POST /api/evaluations/{evaluation_id}/reanalyze`

Optional for MVP; if implemented, create a new report version rather
than overwriting the previous one.

### `DELETE /api/evaluations/{evaluation_id}`

Delete Evaluation and related user-owned data/files according to
retention policy.

## 6. Chat

### `POST /api/evaluations/{evaluation_id}/chat`

Request:

``` json
{
  "session_id": null,
  "message": "Why did the evaluator say my transition was unclear?"
}
```

Response:

``` json
{
  "session_id": "uuid",
  "message": {
    "id": "uuid",
    "role": "ASSISTANT",
    "content": "The feedback refers to the transition between ..."
  }
}
```

### `GET /api/evaluations/{evaluation_id}/chat`

Return chat sessions/messages for the authenticated owner. Consider
separate session-list and message-pagination endpoints if history grows.

## 7. Status values

Evaluation: - `PENDING` - `PROCESSING` - `COMPLETED` - `PARTIAL` -
`FAILED`

Criterion: - `EVALUATED` - `NOT_EVALUATED` - `PENDING`

## 8. Security requirements

-   Verify token server-side.
-   Check ownership on every endpoint.
-   Never accept `user_id` from the request as proof of identity.
-   Do not return service-role credentials or raw private storage paths
    unnecessarily.
-   Sanitize filenames and validate MIME/signature.
-   Apply request limits and rate limits where available.
