import time
from uuid import uuid4
import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core.config import settings
from app.schemas.chat import ChatMessageCreate
from app.services.chatbot.context_assembler import EvaluationContextAssembler
from app.services.chatbot.service import ChatbotService
from app.repositories.chat_repository import ChatRepository
from app.repositories.evaluation_repository import EvaluationRepository
from app.repositories.file_repository import FileRepository
from app.repositories.project_repository import ProjectRepository
from app.api.routes.chat import get_chatbot_service

TEST_JWT_SECRET = "test-secret-key-12345678901234567890123456789012"
USER_A_ID = "00000000-0000-0000-0000-000000000001"
USER_B_ID = "00000000-0000-0000-0000-000000000002"
PROJECT_ID = "11111111-1111-1111-1111-111111111111"
EVAL_ID = "22222222-2222-2222-2222-222222222222"
SESSION_ID = "33333333-3333-3333-3333-333333333333"


@pytest.fixture(autouse=True)
def setup_test_jwt(monkeypatch):
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", TEST_JWT_SECRET)


def create_token(user_id: str, email: str = "test@example.com") -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "role": "authenticated",
        "exp": int(time.time()) + 3600,
    }
    return jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")


class InMemoryChatRepository(ChatRepository):
    def __init__(self):
        self.sessions = {}
        self.messages = {}

    async def get_session_by_id(self, session_id: str, user_id: str):
        sess = self.sessions.get(session_id)
        if sess and sess.get("user_id") == user_id:
            return sess
        return None

    async def get_or_create_session(self, evaluation_id: str, user_id: str, session_id=None, title=None):
        if session_id and session_id in self.sessions:
            sess = self.sessions[session_id]
            if sess["user_id"] == user_id and sess["evaluation_id"] == evaluation_id:
                return sess
        new_id = session_id or str(uuid4())
        record = {
            "id": new_id,
            "evaluation_id": evaluation_id,
            "user_id": user_id,
            "title": title or "Presentation Coaching Session",
            "created_at": "2026-11-23T10:00:00Z",
        }
        self.sessions[new_id] = record
        self.messages[new_id] = []
        return record

    async def add_message(self, session_id: str, role: str, content: str):
        msg_id = str(uuid4())
        msg = {
            "id": msg_id,
            "session_id": session_id,
            "role": role,
            "content": content,
            "created_at": "2026-11-23T10:01:00Z",
        }
        if session_id not in self.messages:
            self.messages[session_id] = []
        self.messages[session_id].append(msg)
        return msg

    async def get_messages_by_session(self, session_id: str):
        return self.messages.get(session_id, [])

    async def get_sessions_by_evaluation(self, evaluation_id: str, user_id: str):
        res = []
        for s in self.sessions.values():
            if s["evaluation_id"] == evaluation_id and s["user_id"] == user_id:
                s_copy = dict(s)
                s_copy["messages"] = self.messages.get(s["id"], [])
                res.append(s_copy)
        return res


class MockEvaluationRepository(EvaluationRepository):
    async def get_by_id(self, evaluation_id: str, user_id: str):
        if evaluation_id == EVAL_ID and user_id == USER_A_ID:
            return {
                "id": EVAL_ID,
                "project_id": PROJECT_ID,
                "user_id": USER_A_ID,
                "status": "COMPLETED",
            }
        return None

    async def get_latest_report(self, evaluation_id: str, user_id: str):
        return {
            "id": str(uuid4()),
            "evaluation_id": evaluation_id,
            "report_json": {
                "evaluation_summary": {
                    "headline": "Solid presentation with clear delivery",
                    "overall_feedback": "Strong slide organization and clear vocal pace.",
                },
                "strengths": [
                    {
                        "title": "Clear introductory hook",
                        "description": "Engaging start on slide 1.",
                        "related_criteria": ["CONTENT"],
                    }
                ],
                "improvements": [
                    {
                        "id": "fb-1",
                        "title": "Smoother slide transitions",
                        "severity": "MEDIUM",
                        "scope": "GROUP",
                        "observation": "Abrupt jump between slide 2 and slide 3.",
                        "impact": "Audience might lose track of the argument.",
                        "recommendation": "Use bridge sentences between topics.",
                        "example": "Now that we covered X, let's explore Y.",
                        "related_criteria": ["LOGICALITY"],
                    }
                ],
                "criterion_results": [
                    {
                        "criterion_id": "LOGICALITY",
                        "status": "EVALUATED",
                        "score": 3,
                        "level": "SATISFACTORY",
                        "reason": "Transitions between slides 2 and 3 need connective phrasing.",
                    }
                ],
                "priority_actions": [
                    {"title": "Practice slide bridge transitions", "steps": ["Rehearse connecting phrase"]}
                ],
            },
        }

    async def get_transcript(self, evaluation_id: str, user_id: str):
        return {
            "language": "en",
            "full_text": "Good morning. Today we discuss AI in education. Moving to slide 2...",
            "segments": [
                {"start": 0.0, "end": 2.0, "text": "Good morning."},
                {"start": 2.0, "end": 5.0, "text": "Today we discuss AI in education."},
            ],
        }


class MockProjectRepository(ProjectRepository):
    async def get_by_id(self, project_id: str, user_id: str):
        if project_id == PROJECT_ID and user_id == USER_A_ID:
            return {
                "id": PROJECT_ID,
                "user_id": USER_A_ID,
                "name": "AI Presentation Capstone",
                "presentation_type": "GROUP",
                "members": [
                    {"id": "m-1", "name": "Alice", "start_time_seconds": 0, "end_time_seconds": 60},
                    {"id": "m-2", "name": "Bob", "start_time_seconds": 60, "end_time_seconds": 120},
                ],
            }
        return None


class MockFileRepository(FileRepository):
    async def list_files_by_evaluation(self, evaluation_id: str, user_id: str):
        return [
            {
                "id": str(uuid4()),
                "file_role": "SLIDES",
                "extracted_slides": [
                    {"page_number": 1, "text": "AI in Education - Title Slide"},
                    {"page_number": 2, "text": "Current Challenges in Teaching"},
                    {"page_number": 3, "text": "Our Proposed AI Framework"},
                ],
            }
        ]


class MockChatbotService(ChatbotService):
    def __init__(self, in_memory_chat_repo):
        super().__init__(
            chat_repo=in_memory_chat_repo,
            eval_repo=MockEvaluationRepository(),
            file_repo=MockFileRepository(),
            project_repo=MockProjectRepository(),
        )

    async def _call_llm(self, messages):
        # Simulate grounded coaching response
        user_msg = messages[-1]["content"]
        if "transition" in user_msg.lower():
            return "The feedback noted an abrupt jump between Slide 2 and Slide 3. You can say: 'Now that we have examined the challenges, let's explore our proposed AI framework.'"
        return "I am your AI Coach. Based on your evaluation, your slide organization is solid."


# --- Tests ---

def test_context_assembler_structure():
    """Verify D5-03: EvaluationContextAssembler properly combines all context and fences untrusted data."""
    project = {
        "name": "Climate Change Capstone",
        "presentation_type": "INDIVIDUAL",
        "members": [{"name": "Carol", "start_time_seconds": 0, "end_time_seconds": 180}],
    }
    report = {
        "report_json": {
            "evaluation_summary": {
                "headline": "Good presentation",
                "overall_feedback": "Strong evidence and clear tone.",
            },
            "strengths": [{"title": "Hook", "description": "Good opening", "related_criteria": ["CONTENT"]}],
            "improvements": [
                {
                    "title": "Pacing",
                    "severity": "HIGH",
                    "scope": "INDIVIDUAL",
                    "observation": "Speaking at 210 words per minute.",
                    "impact": "Listener fatigue",
                    "recommendation": "Slow down to 140 wpm.",
                    "example": "Take pauses after key data points.",
                    "related_criteria": ["PACE"],
                }
            ],
            "criterion_results": [{"criterion_id": "PACE", "status": "EVALUATED", "score": 2, "level": "DEVELOPING", "reason": "Too fast"}],
            "priority_actions": [{"title": "Practice with metronome", "steps": ["Count 2s pause"]}],
        }
    }
    transcript = {"full_text": "Global temperatures have risen by 1.1 degrees Celsius..."}
    slide_text = "[Slide 1]: Climate Change Facts"

    system_prompt = EvaluationContextAssembler.assemble_system_prompt(
        project=project,
        report=report,
        transcript=transcript,
        slide_text=slide_text,
    )

    assert "Climate Change Capstone" in system_prompt
    assert "Speaking at 210 words per minute" in system_prompt
    assert "Take pauses after key data points" in system_prompt
    assert "<UNTRUSTED_PRESENTATION_CONTENT>" in system_prompt
    assert "NEVER invent or hallucinate timestamps" in system_prompt
    assert "ACADEMIC INTEGRITY & COACHING BOUNDARIES" in system_prompt
    assert "NOT a ghostwriter or homework solver" in system_prompt


def test_academic_integrity_guardrail_prompt():
    """Verify D5-06: Assembled system prompt explicitly instructs refusing full script rewrite or ghostwriting."""
    project = {"name": "Senior Project", "presentation_type": "INDIVIDUAL"}
    prompt = EvaluationContextAssembler.assemble_system_prompt(project=project, report=None, transcript=None)

    # Must contain clear boundary directives
    assert "ACADEMIC INTEGRITY & COACHING BOUNDARIES (STRICT)" in prompt
    assert "You MUST REFUSE any request to do homework for the student" in prompt
    assert "rewrite their entire speech/presentation script from start to finish" in prompt
    assert "AT MOST 1 or 2 specific sentences or transitional hooks" in prompt


@pytest.mark.asyncio
async def test_chat_unauthorized():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            f"/api/evaluations/{EVAL_ID}/chat",
            json={"message": "Why was my score 3?"},
        )
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_chat_ownership_protection():
    """User B cannot chat about User A's evaluation."""
    chat_repo = InMemoryChatRepository()
    mock_service = MockChatbotService(chat_repo)
    app.dependency_overrides[get_chatbot_service] = lambda: mock_service

    token_b = create_token(USER_B_ID)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            f"/api/evaluations/{EVAL_ID}/chat",
            json={"message": "How can I improve?"},
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert resp.status_code == 404

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_chat_empty_message_validation():
    """Empty message should return 422."""
    chat_repo = InMemoryChatRepository()
    mock_service = MockChatbotService(chat_repo)
    app.dependency_overrides[get_chatbot_service] = lambda: mock_service

    token_a = create_token(USER_A_ID)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            f"/api/evaluations/{EVAL_ID}/chat",
            json={"message": ""},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert resp.status_code == 422

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_chat_success_and_continuation():
    """Verify D5-01, D5-02, D5-04: Chat message sent, grounded response returned, and session persisted."""
    chat_repo = InMemoryChatRepository()
    mock_service = MockChatbotService(chat_repo)
    app.dependency_overrides[get_chatbot_service] = lambda: mock_service

    token_a = create_token(USER_A_ID)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Message 1: Ask about transition
        resp1 = await ac.post(
            f"/api/evaluations/{EVAL_ID}/chat",
            json={"message": "Why was my slide transition flagged?"},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert resp1.status_code == 200
        data1 = resp1.json()
        assert "session_id" in data1
        session_id = data1["session_id"]
        assert data1["message"]["role"] == "ASSISTANT"
        assert "Slide 2 and Slide 3" in data1["message"]["content"]

        # Message 2: Continuation in the same session
        resp2 = await ac.post(
            f"/api/evaluations/{EVAL_ID}/chat",
            json={"session_id": session_id, "message": "Can you give me another example?"},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["session_id"] == session_id
        assert data2["message"]["role"] == "ASSISTANT"

        # Check History Endpoint: GET /api/evaluations/{id}/chat
        history_resp = await ac.get(
            f"/api/evaluations/{EVAL_ID}/chat",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert history_resp.status_code == 200
        history_data = history_resp.json()
        assert history_data["evaluation_id"] == EVAL_ID
        assert len(history_data["sessions"]) == 1
        # Session has 2 user messages + 2 assistant messages = 4 messages
        assert len(history_data["sessions"][0]["messages"]) == 4
        roles = [m["role"] for m in history_data["sessions"][0]["messages"]]
        assert roles == ["USER", "ASSISTANT", "USER", "ASSISTANT"]

    app.dependency_overrides.clear()
