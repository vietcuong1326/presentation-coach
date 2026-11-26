import time
from pathlib import Path
from uuid import uuid4
import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core.config import settings
from app.schemas.project import ProjectResponse, ProjectCreate, ProjectUpdate
from app.services.evaluation_service import EvaluationService
from app.services.file_service import FileService
from app.services.project_service import ProjectService
from app.services.chatbot.service import ChatbotService
from app.repositories.evaluation_repository import EvaluationRepository
from app.repositories.file_repository import FileRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.chat_repository import ChatRepository
from app.api.routes.evaluations import get_evaluation_service
from app.api.routes.chat import get_chatbot_service
from app.api.routes.projects import get_project_service
from app.api.routes.files import get_file_service

TEST_JWT_SECRET = "test-secret-key-12345678901234567890123456789012"
USER_A_ID = "00000000-0000-0000-0000-000000000001"
USER_B_ID = "00000000-0000-0000-0000-000000000002"
PROJECT_A_ID = "11111111-1111-1111-1111-111111111111"
PROJECT_B_ID = "22222222-2222-2222-2222-222222222222"
EVAL_A_ID = "33333333-3333-3333-3333-333333333333"
SESSION_A_ID = "44444444-4444-4444-4444-444444444444"
SESSION_B_ID = "55555555-5555-5555-5555-555555555555"

REPO_ROOT = Path(__file__).resolve().parents[2]


def make_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "email": f"{user_id}@test.com",
        "role": "authenticated",
        "exp": int(time.time()) + 3600,
    }
    return jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")


def make_auth_header(user_id: str):
    return {"Authorization": f"Bearer {make_token(user_id)}"}


class MockDay6EvaluationRepository(EvaluationRepository):
    def __init__(self):
        self.evals = {
            EVAL_A_ID: {
                "id": EVAL_A_ID,
                "project_id": PROJECT_A_ID,
                "user_id": USER_A_ID,
                "status": "COMPLETED",
                "rubric_version": "v1.0",
                "created_at": "2026-11-24T12:00:00Z",
                "completed_at": "2026-11-24T12:02:00Z",
                "error_code": None,
                "error_message": None,
            },
            "33333333-3333-3333-3333-333333333399": {
                "id": "33333333-3333-3333-3333-333333333399",
                "project_id": PROJECT_A_ID,
                "user_id": USER_A_ID,
                "status": "FAILED",
                "rubric_version": "v1.0",
                "created_at": "2026-11-24T11:50:00Z",
                "completed_at": "2026-11-24T11:51:00Z",
                "error_code": "PIPELINE_ERROR",
                "error_message": "Simulated failure",
            },
        }
        self.reports = {
            EVAL_A_ID: {
                "id": str(uuid4()),
                "evaluation_id": EVAL_A_ID,
                "version": 1,
                "report_json": {
                    "evaluation_summary": {
                        "headline": "Great presentation with solid evidence.",
                        "overall_feedback": "Delivery was clear and engaging.",
                    },
                    "strengths": [],
                    "improvements": [],
                    "criterion_results": [],
                },
                "created_at": "2026-11-24T12:02:00Z",
            }
        }
        self.transcripts = {
            EVAL_A_ID: {"language": "en", "full_text": "Hello world", "segments": []}
        }

    async def get_by_id(self, evaluation_id: str, user_id: str):
        row = self.evals.get(evaluation_id)
        if row and str(row["user_id"]) == str(user_id):
            return row
        return None

    async def list_by_user(self, user_id: str, limit: int = 30):
        return [e for e in self.evals.values() if str(e["user_id"]) == str(user_id)]

    async def list_by_project(self, project_id: str, user_id: str, limit: int = 30):
        return [
            e
            for e in self.evals.values()
            if str(e["project_id"]) == str(project_id) and str(e["user_id"]) == str(user_id)
        ]

    async def get_latest_report(self, evaluation_id: str, user_id: str):
        if not await self.get_by_id(evaluation_id, user_id):
            return None
        return self.reports.get(evaluation_id)

    async def get_transcript(self, evaluation_id: str, user_id: str):
        if not await self.get_by_id(evaluation_id, user_id):
            return None
        return self.transcripts.get(evaluation_id)

    async def update_status(self, evaluation_id: str, status: str, error_code=None, error_message=None):
        if evaluation_id in self.evals:
            self.evals[evaluation_id]["status"] = status
            self.evals[evaluation_id]["error_code"] = error_code
            self.evals[evaluation_id]["error_message"] = error_message
            return True
        return False

    async def delete(self, evaluation_id: str, user_id: str) -> bool:
        existing = await self.get_by_id(evaluation_id, user_id)
        if not existing:
            return False
        self.evals.pop(evaluation_id, None)
        self.reports.pop(evaluation_id, None)
        self.transcripts.pop(evaluation_id, None)
        return True


class MockDay6FileRepository(FileRepository):
    def __init__(self, eval_repo: MockDay6EvaluationRepository):
        self.eval_repo = eval_repo
        self.bucket = "presentations"
        self.stored_objects = {
            f"{USER_A_ID}/{PROJECT_A_ID}/slides.pdf": b"%PDF-1.4 mock",
        }
        self.files = {
            EVAL_A_ID: [
                {
                    "id": str(uuid4()),
                    "evaluation_id": EVAL_A_ID,
                    "user_id": USER_A_ID,
                    "file_role": "SLIDES",
                    "storage_bucket": "presentations",
                    "storage_path": f"{USER_A_ID}/{PROJECT_A_ID}/slides.pdf",
                    "original_filename": "slides.pdf",
                    "mime_type": "application/pdf",
                    "size_bytes": 13,
                    "processing_status": "UPLOADED",
                    "created_at": "2026-11-24T12:00:00Z",
                }
            ]
        }
        self.deleted_paths = []

    async def get_or_create_pending_evaluation(self, project_id: str, user_id: str) -> str:
        for ev in self.eval_repo.evals.values():
            if ev["project_id"] == project_id and ev["user_id"] == user_id and ev["status"] == "PENDING":
                return ev["id"]
        new_id = str(uuid4())
        self.eval_repo.evals[new_id] = {
            "id": new_id,
            "project_id": project_id,
            "user_id": user_id,
            "status": "PENDING",
            "rubric_version": "v1.0",
            "created_at": "2026-11-25T10:00:00Z",
            "completed_at": None,
            "error_code": None,
            "error_message": None,
        }
        return new_id

    async def upload_to_storage(self, storage_path: str, file_bytes: bytes, mime_type: str) -> str:
        self.stored_objects[storage_path] = file_bytes
        return storage_path

    async def create_file_record(
        self,
        evaluation_id: str,
        user_id: str,
        file_role: str,
        storage_path: str,
        original_filename: str,
        mime_type: str,
        size_bytes: int,
    ):
        rec = {
            "id": str(uuid4()),
            "evaluation_id": evaluation_id,
            "user_id": user_id,
            "file_role": file_role,
            "storage_bucket": self.bucket,
            "storage_path": storage_path,
            "original_filename": original_filename,
            "mime_type": mime_type,
            "size_bytes": size_bytes,
            "processing_status": "UPLOADED",
            "created_at": "2026-11-25T10:00:00Z",
        }
        self.files.setdefault(evaluation_id, []).append(rec)
        return rec

    async def list_files_by_evaluation(self, evaluation_id: str, user_id: str):
        return [f for f in self.files.get(evaluation_id, []) if str(f["user_id"]) == str(user_id)]

    async def delete_from_storage(self, storage_paths):
        for p in storage_paths:
            self.stored_objects.pop(p, None)
            self.deleted_paths.append(p)
        return True


class MockDay6ProjectRepository(ProjectRepository):
    def __init__(self):
        self.projects = {
            PROJECT_A_ID: ProjectResponse(
                id=PROJECT_A_ID,
                user_id=USER_A_ID,
                title="User A Presentation",
                presentation_type="INDIVIDUAL",
                created_at="2026-11-24T10:00:00Z",
                updated_at="2026-11-24T10:00:00Z",
                members=[],
            ),
            PROJECT_B_ID: ProjectResponse(
                id=PROJECT_B_ID,
                user_id=USER_B_ID,
                title="User B Presentation",
                presentation_type="GROUP",
                created_at="2026-11-24T11:00:00Z",
                updated_at="2026-11-24T11:00:00Z",
                members=[],
            ),
        }

    async def create(self, user_id: str, project_in: ProjectCreate) -> ProjectResponse:
        new_id = str(uuid4())
        proj = ProjectResponse(
            id=new_id,
            user_id=user_id,
            title=project_in.title,
            topic=project_in.topic,
            objectives=project_in.objectives,
            target_audience=project_in.target_audience,
            presentation_type=project_in.presentation_type,
            expected_duration_seconds=project_in.expected_duration_seconds,
            created_at="2026-11-25T10:00:00Z",
            updated_at="2026-11-25T10:00:00Z",
            members=[],
        )
        self.projects[new_id] = proj
        return proj

    async def get_by_id(self, project_id: str, user_id: str):
        p = self.projects.get(project_id)
        if p and str(p.user_id) == str(user_id):
            return p
        return None

    async def list_by_user(self, user_id: str):
        return [p for p in self.projects.values() if str(p.user_id) == str(user_id)]

    async def update(self, project_id: str, user_id: str, update_in: ProjectUpdate):
        existing = await self.get_by_id(project_id, user_id)
        if not existing:
            return None
        updated = existing.model_copy(update={k: v for k, v in update_in.model_dump(exclude_none=True).items() if k != "members"})
        self.projects[project_id] = updated
        return updated

    async def delete(self, project_id: str, user_id: str) -> bool:
        existing = await self.get_by_id(project_id, user_id)
        if not existing:
            return False
        self.projects.pop(project_id, None)
        return True


class MockDay6ChatRepository(ChatRepository):
    def __init__(self):
        self.sessions = {
            SESSION_A_ID: {
                "id": SESSION_A_ID,
                "evaluation_id": EVAL_A_ID,
                "user_id": USER_A_ID,
                "title": "Coaching Session 1",
                "created_at": "2026-11-24T12:05:00Z",
            },
            SESSION_B_ID: {
                "id": SESSION_B_ID,
                "evaluation_id": str(uuid4()),
                "user_id": USER_B_ID,
                "title": "User B Private Session",
                "created_at": "2026-11-24T12:06:00Z",
            },
        }
        self.messages = {
            SESSION_A_ID: [
                {"id": str(uuid4()), "session_id": SESSION_A_ID, "role": "USER", "content": "How can I improve pace?", "created_at": "2026-11-24T12:05:00Z"},
                {"id": str(uuid4()), "session_id": SESSION_A_ID, "role": "ASSISTANT", "content": "Practice breathing at pauses.", "created_at": "2026-11-24T12:05:05Z"},
            ],
            SESSION_B_ID: [
                {"id": str(uuid4()), "session_id": SESSION_B_ID, "role": "USER", "content": "User B secret message", "created_at": "2026-11-24T12:06:00Z"},
            ],
        }

    async def get_sessions_by_evaluation(self, evaluation_id: str, user_id: str):
        res = []
        for s in self.sessions.values():
            if s["evaluation_id"] == evaluation_id and s["user_id"] == user_id:
                s_copy = dict(s)
                s_copy["messages"] = self.messages.get(s["id"], [])
                res.append(s_copy)
        return res

    async def get_or_create_session(self, evaluation_id: str, user_id: str, session_id=None, title=None):
        if session_id and session_id in self.sessions:
            existing = self.sessions[session_id]
            # Enforce ownership & evaluation match just like production ChatRepository
            if existing["user_id"] == user_id and existing["evaluation_id"] == evaluation_id:
                return existing
        new_id = str(uuid4())
        rec = {
            "id": new_id,
            "evaluation_id": evaluation_id,
            "user_id": user_id,
            "title": title or "New Session",
            "created_at": "2026-11-24T12:10:00Z",
        }
        self.sessions[new_id] = rec
        self.messages[new_id] = []
        return rec

    async def add_message(self, session_id: str, role: str, content: str):
        msg = {
            "id": str(uuid4()),
            "session_id": session_id,
            "role": role,
            "content": content,
            "created_at": "2026-11-24T12:11:00Z",
        }
        self.messages.setdefault(session_id, []).append(msg)
        return msg

    async def get_messages_by_session(self, session_id: str):
        return self.messages.get(session_id, [])


@pytest.fixture(autouse=True)
def setup_day6_env(monkeypatch):
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", TEST_JWT_SECRET)

    mock_eval_repo = MockDay6EvaluationRepository()
    mock_proj_repo = MockDay6ProjectRepository()
    mock_file_repo = MockDay6FileRepository(mock_eval_repo)
    mock_chat_repo = MockDay6ChatRepository()

    eval_service = EvaluationService(
        eval_repo=mock_eval_repo,
        file_repo=mock_file_repo,
        proj_repo=mock_proj_repo,
    )
    proj_service = ProjectService(repo=mock_proj_repo)
    file_service = FileService(repo=mock_file_repo, proj_repo=mock_proj_repo)
    chat_service = ChatbotService(
        chat_repo=mock_chat_repo,
        eval_repo=mock_eval_repo,
        file_repo=mock_file_repo,
        project_repo=mock_proj_repo,
    )

    async def mock_call_llm(messages):
        return "As your Presentation Coach, focus on your slide transitions."

    async def mock_run_pipeline(evaluation_id: str, project_id: str, user_id: str):
        mock_eval_repo.reports[evaluation_id] = {
            "id": str(uuid4()),
            "evaluation_id": evaluation_id,
            "version": 1,
            "report_json": {
                "evaluation_summary": {
                    "headline": "Clear structure with room for stronger transitions.",
                    "overall_feedback": "Your slides cover key points well.",
                },
                "strengths": [],
                "improvements": [],
                "criterion_results": [],
            },
            "created_at": "2026-11-25T10:01:00Z",
        }
        await mock_eval_repo.update_status(evaluation_id, "COMPLETED")

    monkeypatch.setattr(chat_service, "_call_llm", mock_call_llm)
    monkeypatch.setattr(eval_service, "run_evaluation_pipeline", mock_run_pipeline)

    app.dependency_overrides[get_evaluation_service] = lambda: eval_service
    app.dependency_overrides[get_project_service] = lambda: proj_service
    app.dependency_overrides[get_file_service] = lambda: file_service
    app.dependency_overrides[get_chatbot_service] = lambda: chat_service

    yield {
        "eval_repo": mock_eval_repo,
        "file_repo": mock_file_repo,
        "proj_repo": mock_proj_repo,
        "chat_repo": mock_chat_repo,
    }
    app.dependency_overrides.clear()


# =====================================================================
# D6-01 & D6-02: Dashboard & Project Evaluation Lists, History, Reopen & Delete
# =====================================================================
@pytest.mark.asyncio
async def test_d6_01_and_d6_02_evaluation_lists_reopen_and_delete(setup_day6_env):
    file_repo = setup_day6_env["file_repo"]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. User A lists their evaluations across all projects (only successful COMPLETED/PARTIAL)
        res = await client.get("/api/evaluations", headers=make_auth_header(USER_A_ID))
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 1
        assert data[0]["id"] == EVAL_A_ID
        assert data[0]["status"] == "COMPLETED"
        assert data[0]["project_title"] == "User A Presentation"
        assert all(item["status"] in ("COMPLETED", "PARTIAL") for item in data)

        # 2. User A lists evaluations for a specific project (excludes FAILED)
        res_proj = await client.get(
            f"/api/projects/{PROJECT_A_ID}/evaluations",
            headers=make_auth_header(USER_A_ID),
        )
        assert res_proj.status_code == 200
        proj_data = res_proj.json()
        assert len(proj_data) == 1
        assert proj_data[0]["id"] == EVAL_A_ID

        # 3. User B cannot list evaluations for User A's project (returns 404)
        res_b = await client.get(
            f"/api/projects/{PROJECT_A_ID}/evaluations",
            headers=make_auth_header(USER_B_ID),
        )
        assert res_b.status_code == 404

        # 4. Reopen report: User A can fetch report
        res_rep = await client.get(
            f"/api/evaluations/{EVAL_A_ID}/report",
            headers=make_auth_header(USER_A_ID),
        )
        assert res_rep.status_code == 200
        assert "report_json" in res_rep.json()

        # 5. Delete evaluation: User A deletes evaluation and storage objects are cleaned up
        del_res = await client.delete(
            f"/api/evaluations/{EVAL_A_ID}",
            headers=make_auth_header(USER_A_ID),
        )
        assert del_res.status_code == 200
        assert del_res.json()["status"] == "deleted"
        assert f"{USER_A_ID}/{PROJECT_A_ID}/slides.pdf" in file_repo.deleted_paths

        # 6. Deleted evaluation is no longer retrievable
        res_after = await client.get(
            f"/api/evaluations/{EVAL_A_ID}",
            headers=make_auth_header(USER_A_ID),
        )
        assert res_after.status_code == 404


# =====================================================================
# D6-03: Prior Chat Session Reopening and Cross-User Session Isolation
# =====================================================================
@pytest.mark.asyncio
async def test_d6_03_reopen_prior_chat_session():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Get history and prior sessions
        res = await client.get(
            f"/api/evaluations/{EVAL_A_ID}/chat",
            headers=make_auth_header(USER_A_ID),
        )
        assert res.status_code == 200
        hist = res.json()
        assert len(hist["sessions"]) == 1
        assert hist["sessions"][0]["id"] == SESSION_A_ID
        assert len(hist["sessions"][0]["messages"]) == 2

        # 2. Send follow-up message in existing prior session
        post_res = await client.post(
            f"/api/evaluations/{EVAL_A_ID}/chat",
            headers=make_auth_header(USER_A_ID),
            json={"session_id": SESSION_A_ID, "message": "Can you elaborate?"},
        )
        assert post_res.status_code == 200
        post_data = post_res.json()
        assert post_data["session_id"] == SESSION_A_ID
        assert "Presentation Coach" in post_data["message"]["content"]

        # 3. User A passing User B's session_id must NOT attach to User B's session
        hijack_res = await client.post(
            f"/api/evaluations/{EVAL_A_ID}/chat",
            headers=make_auth_header(USER_A_ID),
            json={"session_id": SESSION_B_ID, "message": "Trying foreign session"},
        )
        assert hijack_res.status_code == 200
        assert hijack_res.json()["session_id"] != SESSION_B_ID


# =====================================================================
# D6-04: Strict API Ownership Checks on EVERY Resource
# =====================================================================
@pytest.mark.asyncio
async def test_d6_04_api_ownership_checks_return_404_for_unauthorized():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        b_headers = make_auth_header(USER_B_ID)

        # Projects: GET, PATCH, DELETE
        res_get = await client.get(f"/api/projects/{PROJECT_A_ID}", headers=b_headers)
        assert res_get.status_code == 404
        assert res_get.json()["error"]["code"] == "RESOURCE_NOT_FOUND"

        res_patch = await client.patch(
            f"/api/projects/{PROJECT_A_ID}",
            headers=b_headers,
            json={"title": "Hijacked Title"},
        )
        assert res_patch.status_code == 404

        res_del_proj = await client.delete(f"/api/projects/{PROJECT_A_ID}", headers=b_headers)
        assert res_del_proj.status_code == 404

        # Files: POST upload to User A's project
        res_upload = await client.post(
            f"/api/projects/{PROJECT_A_ID}/files",
            headers=b_headers,
            data={"file_role": "SLIDES"},
            files={"file": ("hack.pdf", b"%PDF-1.4", "application/pdf")},
        )
        assert res_upload.status_code == 404

        # Evaluations: POST create, GET list, GET status, GET report, GET transcript, DELETE
        res_create_eval = await client.post(
            f"/api/projects/{PROJECT_A_ID}/evaluations", headers=b_headers
        )
        assert res_create_eval.status_code == 404

        res_eval = await client.get(f"/api/evaluations/{EVAL_A_ID}", headers=b_headers)
        assert res_eval.status_code == 404

        res_rep = await client.get(f"/api/evaluations/{EVAL_A_ID}/report", headers=b_headers)
        assert res_rep.status_code == 404

        res_transcript = await client.get(
            f"/api/evaluations/{EVAL_A_ID}/transcript", headers=b_headers
        )
        assert res_transcript.status_code == 404

        res_del_eval = await client.delete(f"/api/evaluations/{EVAL_A_ID}", headers=b_headers)
        assert res_del_eval.status_code == 404

        # Chat: GET history, POST message
        res_chat_get = await client.get(f"/api/evaluations/{EVAL_A_ID}/chat", headers=b_headers)
        assert res_chat_get.status_code == 404

        res_chat_post = await client.post(
            f"/api/evaluations/{EVAL_A_ID}/chat",
            headers=b_headers,
            json={"message": "Sneaky question"},
        )
        assert res_chat_post.status_code == 404


# =====================================================================
# D6-05: Unauthenticated Access, Private Storage Paths, and RLS Verification
# =====================================================================
@pytest.mark.asyncio
async def test_d6_05_unauthenticated_requests_are_rejected():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # No token
        res1 = await client.get("/api/projects")
        assert res1.status_code == 401

        # Invalid bearer token
        res2 = await client.get("/api/evaluations", headers={"Authorization": "Bearer invalid.token.value"})
        assert res2.status_code == 401

        # Health endpoint remains public
        res_health = await client.get("/health")
        assert res_health.status_code == 200


def test_d6_05_storage_rls_schema_and_no_frontend_service_role_leak():
    schema_sql = (REPO_ROOT / "supabase_schema.sql").read_text(encoding="utf-8")

    # Verify RLS is enabled on all 10 user-owned tables
    required_rls_tables = [
        "public.profiles",
        "public.projects",
        "public.project_members",
        "public.evaluations",
        "public.evaluation_files",
        "public.transcripts",
        "public.analysis_reports",
        "public.evaluation_evidence",
        "public.chat_sessions",
        "public.chat_messages",
    ]
    for table in required_rls_tables:
        assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;" in schema_sql

    # Verify private storage bucket configuration and folder-based RLS policies
    assert "VALUES ('presentations', 'presentations', false)" in schema_sql
    assert "ON storage.objects FOR SELECT TO authenticated" in schema_sql
    assert "ON storage.objects FOR INSERT TO authenticated" in schema_sql
    assert "ON storage.objects FOR DELETE TO authenticated" in schema_sql
    assert "(storage.foldername(name))[1] = auth.uid()::text" in schema_sql

    # Verify frontend never references SUPABASE_SERVICE_ROLE_KEY
    frontend_src = REPO_ROOT / "frontend" / "src"
    for ts_file in frontend_src.rglob("*"):
        if ts_file.is_file():
            content = ts_file.read_text(encoding="utf-8", errors="ignore")
            assert "SERVICE_ROLE" not in content, f"Service role reference found in {ts_file}"


# =====================================================================
# D6-06: Complete End-to-End User Journey (Create -> Evaluate -> Chat -> Sign Out -> Return)
# =====================================================================
@pytest.mark.asyncio
async def test_d6_06_complete_user_journey(monkeypatch):
    # Mock PDF text extractor so minimal PDF bytes succeed in upload test
    monkeypatch.setattr(
        "app.services.file_service.extract_text_from_pdf",
        lambda _: [{"page_number": 1, "text": "AI in Education Overview"}],
    )

    transport = ASGITransport(app=app)

    # --- Session 1: Create Project, Upload, Evaluate, Read Report, Chat ---
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = make_auth_header(USER_A_ID)

        # 1. Verify authentication
        me_res = await client.get("/api/auth/me", headers=headers)
        assert me_res.status_code == 200
        assert me_res.json()["user"]["id"] == USER_A_ID

        # 2. Create project
        create_proj = await client.post(
            "/api/projects",
            headers=headers,
            json={
                "title": "Final Capstone Pitch",
                "topic": "AI Presentation Coaching",
                "objectives": "Demonstrate MVP",
                "target_audience": "Faculty",
                "presentation_type": "INDIVIDUAL",
                "expected_duration_seconds": 300,
                "members": [],
            },
        )
        assert create_proj.status_code == 201
        new_project_id = create_proj.json()["id"]

        # 3. Upload slide file (verify private storage path starts with user_id/project_id/)
        upload_res = await client.post(
            f"/api/projects/{new_project_id}/files",
            headers=headers,
            data={"file_role": "SLIDES"},
            files={"file": ("pitch.pdf", b"%PDF-1.4 sample slides", "application/pdf")},
        )
        assert upload_res.status_code == 201
        assert upload_res.json()["storage_path"].startswith(f"{USER_A_ID}/{new_project_id}/")

        # 4. Start evaluation
        start_eval = await client.post(
            f"/api/projects/{new_project_id}/evaluations",
            headers=headers,
        )
        assert start_eval.status_code == 201
        new_eval_id = start_eval.json()["id"]

        # 5. Check completed status & report
        status_res = await client.get(f"/api/evaluations/{new_eval_id}", headers=headers)
        assert status_res.status_code == 200
        assert status_res.json()["status"] == "COMPLETED"

        report_res = await client.get(f"/api/evaluations/{new_eval_id}/report", headers=headers)
        assert report_res.status_code == 200
        assert "report_json" in report_res.json()

        # 6. Ask first coaching question in chat
        chat_res = await client.post(
            f"/api/evaluations/{new_eval_id}/chat",
            headers=headers,
            json={"message": "How do I improve my transitions?"},
        )
        assert chat_res.status_code == 200
        created_session_id = chat_res.json()["session_id"]

    # --- Session 2: Simulate Sign Out & Return (Fresh client + fresh token) ---
    async with AsyncClient(transport=transport, base_url="http://test") as returning_client:
        fresh_headers = make_auth_header(USER_A_ID)

        # 7. Dashboard: list projects and evaluation history
        projects_res = await returning_client.get("/api/projects", headers=fresh_headers)
        assert projects_res.status_code == 200
        assert any(p["id"] == new_project_id for p in projects_res.json())

        evals_res = await returning_client.get("/api/evaluations", headers=fresh_headers)
        assert evals_res.status_code == 200
        assert any(e["id"] == new_eval_id for e in evals_res.json())

        # 8. Reopen old report
        reopen_rep = await returning_client.get(
            f"/api/evaluations/{new_eval_id}/report", headers=fresh_headers
        )
        assert reopen_rep.status_code == 200
        assert reopen_rep.json()["report_json"]["evaluation_summary"]["headline"]

        # 9. Reopen prior chat session and send follow-up
        hist_res = await returning_client.get(
            f"/api/evaluations/{new_eval_id}/chat", headers=fresh_headers
        )
        assert hist_res.status_code == 200
        sessions = hist_res.json()["sessions"]
        assert any(s["id"] == created_session_id for s in sessions)

        followup_res = await returning_client.post(
            f"/api/evaluations/{new_eval_id}/chat",
            headers=fresh_headers,
            json={"session_id": created_session_id, "message": "Give me one practice tip."},
        )
        assert followup_res.status_code == 200
        assert followup_res.json()["session_id"] == created_session_id
