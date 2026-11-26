import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_health_check_root():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_health_check_api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_health_runtime_check():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health/runtime")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert isinstance(data["ffmpeg_available"], bool)
        assert "ai_provider" in data
        assert isinstance(data["ai_configured"], bool)
        assert isinstance(data["supabase_configured"], bool)


def test_allowed_origins_strips_trailing_slash():
    from app.core.config import Settings

    parsed = Settings.parse_allowed_origins("https://demo.vercel.app/, http://localhost:5173/ ")
    assert parsed == ["https://demo.vercel.app", "http://localhost:5173"]


@pytest.mark.asyncio
async def test_cors_preflight_on_file_upload():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.options(
            "/api/projects/11111111-1111-1111-1111-111111111111/files",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


@pytest.mark.asyncio
async def test_cors_headers_preserved_on_unhandled_error(monkeypatch):
    from app.api.routes import files as files_route

    class BrokenFileService:
        async def upload_project_file(self, **kwargs):
            raise RuntimeError("Simulated unexpected failure")

    app.dependency_overrides[files_route.get_file_service] = lambda: BrokenFileService()
    try:
        import time, jwt
        from app.core.config import settings

        monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", "test-secret-key-12345678901234567890123456789012")
        token = jwt.encode(
            {"sub": "00000000-0000-0000-0000-000000000001", "role": "authenticated", "exp": int(time.time()) + 3600},
            "test-secret-key-12345678901234567890123456789012",
            algorithm="HS256",
        )
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/projects/11111111-1111-1111-1111-111111111111/files",
                headers={
                    "Origin": "http://localhost:5173",
                    "Authorization": f"Bearer {token}",
                },
                data={"file_role": "VIDEO"},
                files={"file": ("demo.mp4", b"fake-mp4", "video/mp4")},
            )
            assert response.status_code == 500
            assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
            assert response.json()["error"]["code"] == "INTERNAL_SERVER_ERROR"
    finally:
        app.dependency_overrides.clear()

