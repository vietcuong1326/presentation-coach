import time
import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.core.config import settings

TEST_JWT_SECRET = "test-secret-key-12345678901234567890123456789012"


@pytest.fixture(autouse=True)
def override_jwt_secret(monkeypatch):
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", TEST_JWT_SECRET)


def create_token(user_id: str, email: str = "test@example.com", expires_in: int = 3600):
    payload = {
        "sub": user_id,
        "email": email,
        "role": "authenticated",
        "exp": int(time.time()) + expires_in,
    }
    return jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")


@pytest.mark.asyncio
async def test_auth_me_missing_token():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/auth/me")
        assert resp.status_code == 401
        data = resp.json()
        assert data["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_auth_me_invalid_token():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": "Bearer invalid-token-string"}
        resp = await client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 401
        data = resp.json()
        assert data["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_auth_me_expired_token():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_token("user-expired", expires_in=-10)
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 401
        data = resp.json()
        assert data["error"]["code"] == "TOKEN_EXPIRED"


@pytest.mark.asyncio
async def test_auth_me_valid_token():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_token("test-user-uuid-1234", email="student@university.edu")
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["user"]["id"] == "test-user-uuid-1234"
        assert data["user"]["email"] == "student@university.edu"
        assert data["user"]["role"] == "authenticated"

