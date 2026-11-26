import time
from uuid import uuid4
import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.core.config import settings
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse, MemberResponse
from app.repositories.project_repository import ProjectRepository
from app.services.project_service import ProjectService, project_service
from app.api.routes.projects import get_project_service

TEST_JWT_SECRET = "test-secret-key-12345678901234567890123456789012"


class InMemoryProjectRepository(ProjectRepository):
    """In-memory repository for deterministic, lightning-fast testing of project CRUD & ownership."""
    def __init__(self):
        self.projects_db = {}
        self.members_db = {}

    async def create(self, user_id: str, project_in: ProjectCreate) -> ProjectResponse:
        proj_id = uuid4()
        now = "2026-11-21T12:00:00Z"
        members = []
        for idx, m in enumerate(project_in.members):
            m_id = uuid4()
            mem_resp = MemberResponse(
                id=m_id,
                project_id=proj_id,
                name=m.name,
                start_time_seconds=m.start_time_seconds,
                end_time_seconds=m.end_time_seconds,
                display_order=m.display_order if m.display_order else idx,
            )
            members.append(mem_resp)
        self.members_db[str(proj_id)] = members

        proj = ProjectResponse(
            id=proj_id,
            user_id=user_id,
            title=project_in.title,
            topic=project_in.topic,
            objectives=project_in.objectives,
            target_audience=project_in.target_audience,
            presentation_type=project_in.presentation_type,
            expected_duration_seconds=project_in.expected_duration_seconds,
            members=members,
            created_at=now,
            updated_at=now,
        )
        self.projects_db[str(proj_id)] = proj
        return proj

    async def list_by_user(self, user_id: str):
        return [p for p in self.projects_db.values() if str(p.user_id) == str(user_id)]

    async def get_by_id(self, project_id: str, user_id: str):
        p = self.projects_db.get(str(project_id))
        if p and str(p.user_id) == str(user_id):
            return p
        return None

    async def update(self, project_id: str, user_id: str, update_in: ProjectUpdate):
        existing = await self.get_by_id(project_id, user_id)
        if not existing:
            return None
        data = existing.model_dump()
        for field in ("title", "topic", "objectives", "target_audience", "presentation_type", "expected_duration_seconds"):
            val = getattr(update_in, field)
            if val is not None:
                data[field] = val
        if update_in.members is not None:
            new_members = []
            for idx, m in enumerate(update_in.members):
                new_members.append(
                    MemberResponse(
                        id=uuid4(),
                        project_id=existing.id,
                        name=m.name,
                        start_time_seconds=m.start_time_seconds,
                        end_time_seconds=m.end_time_seconds,
                        display_order=m.display_order if m.display_order else idx,
                    )
                )
            data["members"] = new_members
            self.members_db[str(project_id)] = new_members
        data["updated_at"] = "2026-11-21T12:05:00Z"
        updated = ProjectResponse(**data)
        self.projects_db[str(project_id)] = updated
        return updated

    async def delete(self, project_id: str, user_id: str):
        existing = await self.get_by_id(project_id, user_id)
        if not existing:
            return False
        del self.projects_db[str(project_id)]
        self.members_db.pop(str(project_id), None)
        return True


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", TEST_JWT_SECRET)
    mock_repo = InMemoryProjectRepository()
    mock_service = ProjectService(repo=mock_repo)
    # Override app dependency
    app.dependency_overrides[get_project_service] = lambda: mock_service
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


USER_A_ID = "00000000-0000-0000-0000-000000000001"
USER_B_ID = "00000000-0000-0000-0000-000000000002"


@pytest.mark.asyncio
async def test_create_project_individual():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "title": "Solo Presentation on Renewable Energy",
            "topic": "Clean Energy",
            "objectives": "Explain solar panel efficiency",
            "target_audience": "Undergrads",
            "presentation_type": "INDIVIDUAL",
            "expected_duration_seconds": 600,
        }
        res = await client.post("/api/projects", json=payload, headers=make_auth_header(USER_A_ID))
        assert res.status_code == 201
        data = res.json()
        assert data["title"] == payload["title"]
        assert data["presentation_type"] == "INDIVIDUAL"
        assert data["user_id"] == USER_A_ID
        assert len(data["members"]) == 0
        assert len(data["warnings"]) == 0


@pytest.mark.asyncio
async def test_create_project_group_with_valid_members():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "title": "Group Presentation on AI",
            "presentation_type": "GROUP",
            "expected_duration_seconds": 900,
            "members": [
                {"name": "Alice", "start_time_seconds": 0, "end_time_seconds": 300},
                {"name": "Bob", "start_time_seconds": 300, "end_time_seconds": 600},
            ],
        }
        res = await client.post("/api/projects", json=payload, headers=make_auth_header(USER_A_ID))
        assert res.status_code == 201
        data = res.json()
        assert len(data["members"]) == 2
        assert data["members"][0]["name"] == "Alice"
        assert data["members"][1]["name"] == "Bob"
        assert len(data["warnings"]) == 0


@pytest.mark.asyncio
async def test_create_project_invalid_time_range():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "title": "Invalid Member Times",
            "members": [
                {"name": "Alice", "start_time_seconds": 400, "end_time_seconds": 200},  # start > end
            ],
        }
        res = await client.post("/api/projects", json=payload, headers=make_auth_header(USER_A_ID))
        assert res.status_code == 422
        data = res.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_create_project_overlap_and_exceeded_duration_flags_warnings():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "title": "Overlapping Members",
            "presentation_type": "GROUP",
            "expected_duration_seconds": 500,
            "members": [
                {"name": "Alice", "start_time_seconds": 0, "end_time_seconds": 350},
                {"name": "Bob", "start_time_seconds": 300, "end_time_seconds": 600},  # Overlaps & exceeds 500s
            ],
        }
        res = await client.post("/api/projects", json=payload, headers=make_auth_header(USER_A_ID))
        assert res.status_code == 201
        data = res.json()
        assert len(data["warnings"]) == 2
        assert "overlap" in data["warnings"][0].lower()
        assert "exceeds" in data["warnings"][1].lower()


@pytest.mark.asyncio
async def test_ownership_isolation_between_two_users():
    """AC: User A cannot read, update, or delete User B's project (returns 404)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. User A creates project
        create_res = await client.post(
            "/api/projects",
            json={"title": "User A Secret Presentation"},
            headers=make_auth_header(USER_A_ID),
        )
        assert create_res.status_code == 201
        project_a_id = create_res.json()["id"]

        # 2. User B lists projects -> should be empty
        list_b_res = await client.get("/api/projects", headers=make_auth_header(USER_B_ID))
        assert list_b_res.status_code == 200
        assert len(list_b_res.json()) == 0

        # 3. User B tries to GET User A's project -> must return 404 (not reveal existence)
        get_b_res = await client.get(f"/api/projects/{project_a_id}", headers=make_auth_header(USER_B_ID))
        assert get_b_res.status_code == 404
        assert get_b_res.json()["error"]["code"] == "RESOURCE_NOT_FOUND"

        # 4. User B tries to PATCH User A's project -> must return 404
        patch_b_res = await client.patch(
            f"/api/projects/{project_a_id}",
            json={"title": "Hacked Title"},
            headers=make_auth_header(USER_B_ID),
        )
        assert patch_b_res.status_code == 404

        # 5. User B tries to DELETE User A's project -> must return 404
        del_b_res = await client.delete(f"/api/projects/{project_a_id}", headers=make_auth_header(USER_B_ID))
        assert del_b_res.status_code == 404

        # 6. User A CAN read their own project
        get_a_res = await client.get(f"/api/projects/{project_a_id}", headers=make_auth_header(USER_A_ID))
        assert get_a_res.status_code == 200
        assert get_a_res.json()["title"] == "User A Secret Presentation"

        # 7. User A updates their project
        patch_a_res = await client.patch(
            f"/api/projects/{project_a_id}",
            json={"title": "Updated Title"},
            headers=make_auth_header(USER_A_ID),
        )
        assert patch_a_res.status_code == 200
        assert patch_a_res.json()["title"] == "Updated Title"

        # 8. User A deletes their project
        del_a_res = await client.delete(f"/api/projects/{project_a_id}", headers=make_auth_header(USER_A_ID))
        assert del_a_res.status_code == 200

        # 9. Project is now gone for User A as well
        get_a_after = await client.get(f"/api/projects/{project_a_id}", headers=make_auth_header(USER_A_ID))
        assert get_a_after.status_code == 404
