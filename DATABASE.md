# Database Design --- MVP

Version: 1.0\
Database: Supabase PostgreSQL

## 1. Conventions

-   Primary keys: UUID.
-   Timestamps: `timestamptz`, UTC.
-   Ownership: every user-owned root entity includes `user_id` or is
    reachable through a parent with verified ownership.
-   Store file bytes in Supabase Storage, not PostgreSQL.
-   JSONB is suitable for versioned AI report payloads, but important
    queryable entities should have relational columns.
-   Enable RLS on all user-owned tables.

## 2. Tables

### `profiles`

  Column         Type          Notes
  -------------- ------------- ----------------------------
  id             uuid PK       References `auth.users.id`
  display_name   text          Optional
  created_at     timestamptz   Default now

### `projects`

  Column                      Type          Notes
  --------------------------- ------------- ------------------------
  id                          uuid PK       
  user_id                     uuid FK       Owner
  title                       text          Required
  topic                       text          
  objectives                  text          
  target_audience             text          
  presentation_type           text          `INDIVIDUAL` / `GROUP`
  expected_duration_seconds   integer       Nullable
  created_at                  timestamptz   
  updated_at                  timestamptz   

### `project_members`

  Column               Type      Notes
  -------------------- --------- ----------
  id                   uuid PK   
  project_id           uuid FK   
  name                 text      
  start_time_seconds   numeric   Nullable
  end_time_seconds     numeric   Nullable
  display_order        integer   

Time ranges are user-provided approximations. Validate start \< end.
Overlaps should be flagged for review, not silently resolved.

### `evaluations`

  -----------------------------------------------------------------------
  Column                  Type                    Notes
  ----------------------- ----------------------- -----------------------
  id                      uuid PK                 

  project_id              uuid FK                 

  user_id                 uuid FK                 Denormalized owner for
                                                  RLS

  status                  text                    `PENDING`,
                                                  `PROCESSING`,
                                                  `COMPLETED`, `PARTIAL`,
                                                  `FAILED`

  error_code              text                    Safe machine-readable
                                                  error

  error_message           text                    Safe user-facing
                                                  message

  rubric_version          text                    Snapshot/version
                                                  identifier

  created_at              timestamptz             

  completed_at            timestamptz             Nullable
  -----------------------------------------------------------------------

### `evaluation_files`

  Column              Type          Notes
  ------------------- ------------- -----------------------------------------------
  id                  uuid PK       
  evaluation_id       uuid FK       
  user_id             uuid FK       Owner
  file_role           text          `SLIDES`, `AUDIO`, `VIDEO`, `REPORT`, `OTHER`
  storage_bucket      text          
  storage_path        text          Private object path
  original_filename   text          
  mime_type           text          
  size_bytes          bigint        
  processing_status   text          `UPLOADED`, `PROCESSED`, `FAILED`
  created_at          timestamptz   

### `transcripts`

  Column          Type          Notes
  --------------- ------------- ----------------------------------
  id              uuid PK       
  evaluation_id   uuid FK       
  language        text          Usually `en`
  full_text       text          
  segments        jsonb         Array of text/start/end segments
  provider        text          
  created_at      timestamptz   

### `analysis_reports`

  Column                Type          Notes
  --------------------- ------------- -----------------------------
  id                    uuid PK       
  evaluation_id         uuid FK       
  version               integer       Increment per re-analysis
  report_json           jsonb         Validated structured report
  evaluated_count       integer       
  not_evaluated_count   integer       
  created_at            timestamptz   

Unique constraint: `(evaluation_id, version)`.

### `evaluation_evidence`

  -----------------------------------------------------------------------
  Column                  Type                    Notes
  ----------------------- ----------------------- -----------------------
  id                      uuid PK                 

  report_id               uuid FK                 

  criterion_id            text                    Rubric criterion key

  member_id               uuid FK nullable        Null for group-level or
                                                  unattributed

  source_type             text                    `AUDIO`, `TRANSCRIPT`,
                                                  `SLIDE`, `DOCUMENT`,
                                                  `USER_INPUT`

  start_seconds           numeric nullable        

  end_seconds             numeric nullable        

  page_number             integer nullable        

  excerpt                 text                    Short supporting
                                                  excerpt/observation

  confidence              numeric nullable        Model confidence
                                                  estimate, not score

  created_at              timestamptz             
  -----------------------------------------------------------------------

### `chat_sessions`

  Column          Type          Notes
  --------------- ------------- ----------
  id              uuid PK       
  evaluation_id   uuid FK       
  user_id         uuid FK       Owner
  title           text          Optional
  created_at      timestamptz   

### `chat_messages`

  Column       Type          Notes
  ------------ ------------- ---------------------
  id           uuid PK       
  session_id   uuid FK       
  role         text          `USER`, `ASSISTANT`
  content      text          
  created_at   timestamptz   

## 3. Relationships

``` text
auth.users
  └── profiles
  └── projects
       ├── project_members
       └── evaluations
            ├── evaluation_files
            ├── transcripts
            ├── analysis_reports
            │    └── evaluation_evidence
            └── chat_sessions
                 └── chat_messages
```

## 4. RLS requirements

-   `profiles`: user can read/update own profile.
-   `projects`: owner can CRUD own projects.
-   `project_members`: access only through owned project.
-   `evaluations`: owner can read/create/delete own evaluations.
-   `evaluation_files`: owner can access metadata; storage policy must
    restrict object paths to owner.
-   `transcripts`, `analysis_reports`, `evaluation_evidence`: access
    only through an owned evaluation.
-   `chat_sessions`, `chat_messages`: access only through an owned
    evaluation/session.

Do not rely only on frontend route guards. Test direct API/database
access using a second account.

## 5. Deletion

Deleting an Evaluation should delete related rows and storage objects,
or enqueue a cleanup operation. Define whether deleting a Project
cascades to its Evaluations. Avoid orphaned storage objects.

## 6. Important implementation notes

-   Save a rubric snapshot or immutable rubric version with each
    Evaluation.
-   Never overwrite a prior report version.
-   `score` must be nullable for `NOT_EVALUATED`.
-   Confidence is not the rubric score.
-   Keep raw provider payloads only if necessary; minimize retained
    personal data.
