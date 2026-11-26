import time
from uuid import uuid4
import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.main import app
from app.core.config import settings
from app.schemas.feedback import AnalysisReportPayload, CriterionResult, EvaluationSummary
from app.schemas.project import ProjectResponse
from app.services.ai_evaluator.pipeline import AIEvaluationPipeline
from app.services.transcription.service import TranscriptionService
from app.services.evaluation_service import EvaluationService
from app.repositories.evaluation_repository import EvaluationRepository
from app.repositories.file_repository import FileRepository
from app.repositories.project_repository import project_repository
from app.api.routes.evaluations import get_evaluation_service

TEST_JWT_SECRET = "test-secret-key-12345678901234567890123456789012"
USER_A_ID = "00000000-0000-0000-0000-000000000001"
USER_B_ID = "00000000-0000-0000-0000-000000000002"
PROJECT_ID = "11111111-1111-1111-1111-111111111111"
EVAL_ID = "22222222-2222-2222-2222-222222222222"


def make_valid_report_dict():
    return {
        "evaluation_summary": {
            "headline": "Well organized presentation with clear delivery.",
            "overall_feedback": "The presentation effectively introduces key concepts with strong slide alignment.",
            "evidence_coverage": {
                "evaluated_criteria": 16,
                "not_evaluated_criteria": 4,
            },
        },
        "strengths": [
            {
                "title": "Clear introductory hook",
                "description": "Presenter sets the context in slide 1 before presenting details.",
                "evidence_ids": ["ev-1"],
                "related_criteria": ["CONTENT"],
            }
        ],
        "improvements": [
            {
                "id": "fb-1",
                "title": "Bridge transitions between slides",
                "severity": "MEDIUM",
                "scope": "GROUP",
                "member_id": None,
                "observation": "Abrupt jump between slide 2 and slide 3.",
                "impact": "Audience might miss the logical connection.",
                "recommendation": "Add a connective phrase when advancing slides.",
                "example": "Having explored the challenge, let's now examine our proposed solution.",
                "evidence_ids": ["ev-2"],
                "related_criteria": ["LOGICALITY"],
            }
        ],
        "criterion_results": [
            {
                "criterion_id": "CONTENT",
                "scope": "GROUP",
                "member_id": None,
                "status": "EVALUATED",
                "score": 4,
                "level": "EXCELLENT",
                "reason": "Comprehensive coverage of topic objectives.",
                "evidence_ids": ["ev-1"],
                "confidence": 0.9,
            },
            {
                "criterion_id": "EYE_CONTACT_POSTURE",
                "scope": "INDIVIDUAL",
                "member_id": None,
                "status": "NOT_EVALUATED",
                "score": None,
                "level": None,
                "reason": "Visual video analysis is outside MVP scope.",
                "evidence_ids": [],
                "confidence": None,
            },
        ],
        "priority_actions": [
            {
                "title": "Rehearse transition sentences",
                "steps": ["Write 1 bridge sentence", "Practice aloud with slides"],
                "related_feedback_ids": ["fb-1"],
            }
        ],
    }


# --- D3-03: Pydantic Schema Validation Tests ---
def test_valid_report_payload_schema():
    data = make_valid_report_dict()
    payload = AnalysisReportPayload(**data)
    assert payload.evaluation_summary.headline == data["evaluation_summary"]["headline"]
    assert len(payload.strengths) == 1
    assert len(payload.improvements) == 1
    assert payload.criterion_results[1].status == "NOT_EVALUATED"
    assert payload.criterion_results[1].score is None


def test_malformed_report_payload_rejected():
    data = make_valid_report_dict()
    data["criterion_results"][0]["score"] = 10
    with pytest.raises(ValidationError):
        AnalysisReportPayload(**data)


# --- D3-01: Transcription Service Mock Test ---
class MockTranscriptionService(TranscriptionService):
    async def transcribe_audio(self, audio_bytes: bytes, filename: str = "audio.mp3"):
        return {
            "language": "en",
            "full_text": "Good morning everyone. Today we discuss artificial intelligence in healthcare.",
            "segments": [
                {"start": 0.0, "end": 2.5, "text": "Good morning everyone."},
                {"start": 2.5, "end": 6.0, "text": "Today we discuss artificial intelligence in healthcare."},
            ],
            "provider": "whisper",
        }


# --- D3-05: AI Evaluation Pipeline Mock Test ---
class MockAIEvaluationPipeline(AIEvaluationPipeline):
    async def evaluate_presentation(self, project_meta, slide_pages, transcript):
        return AnalysisReportPayload(**make_valid_report_dict())


class MockFileRepository(FileRepository):
    async def get_or_create_pending_evaluation(self, project_id: str, user_id: str):
        return EVAL_ID

    async def list_files_by_evaluation(self, evaluation_id: str, user_id: str):
        return [
            {
                "file_role": "AUDIO",
                "storage_path": "test/path/audio.mp3",
                "original_filename": "speech.mp3",
            }
        ]


class MockEvaluationRepository(EvaluationRepository):
    def __init__(self):
        self.evaluations_db = {
            EVAL_ID: {
                "id": EVAL_ID,
                "project_id": PROJECT_ID,
                "user_id": USER_A_ID,
                "status": "PENDING",
                "rubric_version": "v1.0",
                "created_at": "2026-11-21T12:00:00Z",
            }
        }
        self.transcripts_db = {}
        self.reports_db = {}

    async def create(self, project_id: str, user_id: str):
        rec = {
            "id": EVAL_ID,
            "project_id": project_id,
            "user_id": user_id,
            "status": "PENDING",
            "rubric_version": "v1.0",
            "created_at": "2026-11-21T12:00:00Z",
        }
        self.evaluations_db[EVAL_ID] = rec
        return rec

    async def get_by_id(self, evaluation_id: str, user_id: str):
        row = self.evaluations_db.get(evaluation_id)
        if row and str(row["user_id"]) == str(user_id):
            return row
        return None

    async def update_status(self, evaluation_id: str, status: str, error_code=None, error_message=None):
        if evaluation_id in self.evaluations_db:
            self.evaluations_db[evaluation_id]["status"] = status
            return True
        return False

    async def save_transcript(self, evaluation_id, language, full_text, segments, provider="whisper"):
        rec = {
            "id": uuid4(),
            "evaluation_id": evaluation_id,
            "language": language,
            "full_text": full_text,
            "segments": segments,
            "provider": provider,
            "created_at": "2026-11-21T12:05:00Z",
        }
        self.transcripts_db[evaluation_id] = rec
        return rec

    async def get_transcript(self, evaluation_id: str, user_id: str):
        if not await self.get_by_id(evaluation_id, user_id):
            return None
        return self.transcripts_db.get(evaluation_id)

    async def save_analysis_report(self, evaluation_id, report_json, evaluated_count, not_evaluated_count, version=1):
        rec = {
            "id": uuid4(),
            "evaluation_id": evaluation_id,
            "version": version,
            "report_json": report_json,
            "evaluated_count": evaluated_count,
            "not_evaluated_count": not_evaluated_count,
            "created_at": "2026-11-21T12:10:00Z",
        }
        self.reports_db[evaluation_id] = rec
        return rec

    async def get_latest_report(self, evaluation_id: str, user_id: str):
        if not await self.get_by_id(evaluation_id, user_id):
            return None
        return self.reports_db.get(evaluation_id)


ACTIVE_MOCK_SERVICE = None


@pytest.fixture(autouse=True)
def setup_eval_test_env(monkeypatch):
    global ACTIVE_MOCK_SERVICE
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", TEST_JWT_SECRET)
    mock_repo = MockEvaluationRepository()
    mock_file_repo = MockFileRepository()
    mock_transcriber = MockTranscriptionService()
    mock_evaluator = MockAIEvaluationPipeline()
    ACTIVE_MOCK_SERVICE = EvaluationService(
        eval_repo=mock_repo,
        file_repo=mock_file_repo,
        transcriber=mock_transcriber,
        evaluator=mock_evaluator,
    )

    async def mock_bytes(storage_path: str):
        return b"fake-audio-file-content"

    monkeypatch.setattr(ACTIVE_MOCK_SERVICE, "get_file_bytes", mock_bytes)
    app.dependency_overrides[get_evaluation_service] = lambda: ACTIVE_MOCK_SERVICE

    async def mock_get_proj(p_id: str, u_id: str):
        if p_id == PROJECT_ID and u_id == USER_A_ID:
            return ProjectResponse(
                id=PROJECT_ID,
                user_id=USER_A_ID,
                title="AI Healthcare Presentation",
                presentation_type="INDIVIDUAL",
                created_at="2026-11-21T12:00:00Z",
                updated_at="2026-11-21T12:00:00Z",
            )
        return None

    monkeypatch.setattr(project_repository, "get_by_id", mock_get_proj)
    yield
    app.dependency_overrides.clear()


def make_auth_header(user_id: str):
    payload = {
        "sub": user_id,
        "email": f"{user_id}@test.com",
        "role": "authenticated",
        "exp": int(time.time()) + 3600,
    }
    token = jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_evaluation_starts_background_task():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            f"/api/projects/{PROJECT_ID}/evaluations",
            headers=make_auth_header(USER_A_ID),
        )
        assert res.status_code == 201
        data = res.json()
        assert data["status"] == "PENDING"
        assert "id" in data


@pytest.mark.asyncio
async def test_get_evaluation_status_and_ownership():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Owner User A can read status
        res = await client.get(
            f"/api/evaluations/{EVAL_ID}",
            headers=make_auth_header(USER_A_ID),
        )
        assert res.status_code == 200
        assert res.json()["id"] == EVAL_ID

        # Unauthorized User B receives 404
        res_b = await client.get(
            f"/api/evaluations/{EVAL_ID}",
            headers=make_auth_header(USER_B_ID),
        )
        assert res_b.status_code == 404
        assert res_b.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.asyncio
async def test_full_pipeline_execution_and_report_retrieval():
    global ACTIVE_MOCK_SERVICE
    # Execute full pipeline synchronously for test
    await ACTIVE_MOCK_SERVICE.run_evaluation_pipeline(EVAL_ID, PROJECT_ID, USER_A_ID)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Check report
        res = await client.get(
            f"/api/evaluations/{EVAL_ID}/report",
            headers=make_auth_header(USER_A_ID),
        )
        assert res.status_code == 200
        rep_data = res.json()
        assert "report_json" in rep_data
        report = rep_data["report_json"]
        assert len(report["strengths"]) == 1
        assert len(report["improvements"]) == 1
        assert report["improvements"][0]["recommendation"] is not None

        # 2. Check transcript
        trans_res = await client.get(
            f"/api/evaluations/{EVAL_ID}/transcript",
            headers=make_auth_header(USER_A_ID),
        )
        assert trans_res.status_code == 200
        trans = trans_res.json()
        assert "artificial intelligence" in trans["full_text"]
        assert len(trans["segments"]) == 2

        # 3. User B cannot access report (returns 404)
        rep_b = await client.get(
            f"/api/evaluations/{EVAL_ID}/report",
            headers=make_auth_header(USER_B_ID),
        )
        assert rep_b.status_code == 404


@pytest.mark.asyncio
async def test_gemini_transcription_and_evaluation_switch(monkeypatch):
    """Test AI_PROVIDER='gemini' branch execution and parsing."""
    import json
    import httpx
    monkeypatch.setattr(settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "dummy-gemini-key")

    trans_service = TranscriptionService()

    class MockRespTrans:
        status_code = 200
        def json(self):
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": json.dumps({
                                        "language": "en",
                                        "full_text": "Good morning and welcome to our presentation.",
                                        "segments": [
                                            {"start": 0.0, "end": 2.5, "text": "Good morning and welcome to our presentation."}
                                        ],
                                    })
                                }
                            ]
                        }
                    }
                ]
            }

    async def mock_post(*args, **kwargs):
        return MockRespTrans()

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    res = await trans_service.transcribe_audio(b"fake-audio-bytes", "test.mp3")
    assert res["provider"] == "gemini"
    assert res["full_text"] == "Good morning and welcome to our presentation."
    assert len(res["segments"]) == 1

    # Test Gemini Evaluator
    evaluator = AIEvaluationPipeline()
    valid_rep = make_valid_report_dict()

    class MockRespEval:
        status_code = 200
        def json(self):
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": json.dumps(valid_rep),
                                }
                            ]
                        }
                    }
                ]
            }

    async def mock_post_eval(*args, **kwargs):
        return MockRespEval()

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post_eval)

    rep = await evaluator.evaluate_presentation(
        project_meta={"title": "Gemini Demo", "members": []},
        slide_pages=[],
        transcript={"full_text": "Hello world", "segments": []},
    )
    assert rep.evaluation_summary.headline == valid_rep["evaluation_summary"]["headline"]
