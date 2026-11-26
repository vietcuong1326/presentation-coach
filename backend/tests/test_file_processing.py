import io
import time
from uuid import uuid4
import jwt
import pytest
import fitz  # PyMuPDF
from pptx import Presentation
from pptx.util import Inches, Pt
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core.config import settings
from app.services.file_processing.pdf_extractor import extract_text_from_pdf
from app.services.file_processing.pptx_extractor import extract_text_from_pptx
from app.services.file_service import FileService, file_service
from app.repositories.file_repository import FileRepository
from app.repositories.project_repository import project_repository
from app.schemas.project import ProjectResponse
from app.api.routes.files import get_file_service

TEST_JWT_SECRET = "test-secret-key-12345678901234567890123456789012"
USER_A_ID = "00000000-0000-0000-0000-000000000001"
USER_B_ID = "00000000-0000-0000-0000-000000000002"
PROJECT_ID = "11111111-1111-1111-1111-111111111111"


def create_sample_pdf_bytes() -> bytes:
    """Generates an in-memory 2-page PDF document."""
    doc = fitz.open()
    # Page 1
    page1 = doc.new_page()
    page1.insert_text((50, 72), "AI in Healthcare: Overview", fontsize=18)
    page1.insert_text((50, 100), "Diagnosing diseases with deep learning models.", fontsize=12)

    # Page 2
    page2 = doc.new_page()
    page2.insert_text((50, 72), "Methodology & Results", fontsize=18)
    page2.insert_text((50, 100), "Achieved 95% accuracy on test dataset.", fontsize=12)

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_sample_pptx_bytes() -> bytes:
    """Generates an in-memory 2-slide PowerPoint presentation."""
    prs = Presentation()
    blank_layout = prs.slide_layouts[6]

    # Slide 1
    slide1 = prs.slides.add_slide(blank_layout)
    tx_box1 = slide1.shapes.add_textbox(Inches(1), Inches(1), Inches(5), Inches(2))
    tx_box1.text_frame.text = "Renewable Energy Transitions\nSolar and Wind Power"

    # Slide 2
    slide2 = prs.slides.add_slide(blank_layout)
    tx_box2 = slide2.shapes.add_textbox(Inches(1), Inches(1), Inches(5), Inches(2))
    tx_box2.text_frame.text = "Challenges & Grid Stability\nBattery storage solutions"

    output = io.BytesIO()
    prs.save(output)
    return output.getvalue()


class MockFileRepository(FileRepository):
    def __init__(self):
        self.storage = {}
        self.files_db = []

    async def get_or_create_pending_evaluation(self, project_id: str, user_id: str) -> str:
        return "eval-uuid-0000-0000-0000"

    async def upload_to_storage(self, storage_path: str, file_bytes: bytes, mime_type: str) -> str:
        self.storage[storage_path] = file_bytes
        return storage_path

    async def create_file_record(self, evaluation_id, user_id, file_role, storage_path, original_filename, mime_type, size_bytes):
        rec = {
            "id": uuid4(),
            "evaluation_id": evaluation_id,
            "user_id": user_id,
            "file_role": file_role,
            "storage_path": storage_path,
            "original_filename": original_filename,
            "mime_type": mime_type,
            "size_bytes": size_bytes,
            "processing_status": "UPLOADED",
            "created_at": "2026-11-21T14:00:00Z",
        }
        self.files_db.append(rec)
        return rec


@pytest.fixture(autouse=True)
def setup_mock_services(monkeypatch):
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", TEST_JWT_SECRET)
    mock_file_repo = MockFileRepository()
    mock_file_service = FileService(repo=mock_file_repo)
    app.dependency_overrides[get_file_service] = lambda: mock_file_service

    # Mock project repository get_by_id for ownership checks
    async def mock_get_project(p_id: str, u_id: str):
        if p_id == PROJECT_ID and u_id == USER_A_ID:
            return ProjectResponse(
                id=PROJECT_ID,
                user_id=USER_A_ID,
                title="Sample Project",
                presentation_type="INDIVIDUAL",
                created_at="2026-11-21T12:00:00Z",
                updated_at="2026-11-21T12:00:00Z",
            )
        return None

    monkeypatch.setattr(project_repository, "get_by_id", mock_get_project)
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


# --- D2-05: PDF Extraction Tests ---
def test_pdf_extraction_sample():
    pdf_bytes = create_sample_pdf_bytes()
    slides = extract_text_from_pdf(pdf_bytes)
    assert len(slides) == 2
    assert slides[0]["page_number"] == 1
    assert "AI in Healthcare" in slides[0]["text"]
    assert slides[1]["page_number"] == 2
    assert "95% accuracy" in slides[1]["text"]


# --- D2-05: PPTX Extraction Tests ---
def test_pptx_extraction_sample():
    pptx_bytes = create_sample_pptx_bytes()
    slides = extract_text_from_pptx(pptx_bytes)
    assert len(slides) == 2
    assert slides[0]["page_number"] == 1
    assert "Renewable Energy Transitions" in slides[0]["text"]
    assert slides[1]["page_number"] == 2
    assert "Battery storage solutions" in slides[1]["text"]


# --- D2-04: File Upload & Authorization Tests ---
@pytest.mark.asyncio
async def test_upload_pdf_slides_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        pdf_bytes = create_sample_pdf_bytes()
        files = {
            "file": ("slides.pdf", pdf_bytes, "application/pdf"),
        }
        data = {
            "file_role": "SLIDES",
        }
        res = await client.post(
            f"/api/projects/{PROJECT_ID}/files",
            data=data,
            files=files,
            headers=make_auth_header(USER_A_ID),
        )
        assert res.status_code == 201
        res_data = res.json()
        assert res_data["file_role"] == "SLIDES"
        assert res_data["original_filename"] == "slides.pdf"
        assert res_data["processing_status"] == "UPLOADED"
        assert len(res_data["extracted_slides"]) == 2
        assert "AI in Healthcare" in res_data["extracted_slides"][0]["text"]


@pytest.mark.asyncio
async def test_upload_file_unauthorized_project_ownership():
    """User B cannot upload file to User A's project (returns 404)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        pdf_bytes = create_sample_pdf_bytes()
        files = {
            "file": ("hacked.pdf", pdf_bytes, "application/pdf"),
        }
        data = {
            "file_role": "SLIDES",
        }
        res = await client.post(
            f"/api/projects/{PROJECT_ID}/files",
            data=data,
            files=files,
            headers=make_auth_header(USER_B_ID),
        )
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.asyncio
async def test_upload_file_unsupported_format():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {
            "file": ("script.exe", b"binary content", "application/octet-stream"),
        }
        data = {
            "file_role": "SLIDES",
        }
        res = await client.post(
            f"/api/projects/{PROJECT_ID}/files",
            data=data,
            files=files,
            headers=make_auth_header(USER_A_ID),
        )
        assert res.status_code == 400
        assert res.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


@pytest.mark.asyncio
async def test_upload_file_size_exceeded(monkeypatch):
    monkeypatch.setattr(settings, "MAX_SLIDE_SIZE_MB", 1)  # 1MB limit
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        large_bytes = b"0" * (2 * 1024 * 1024)  # 2MB
        files = {
            "file": ("huge.pdf", large_bytes, "application/pdf"),
        }
        data = {
            "file_role": "SLIDES",
        }
        res = await client.post(
            f"/api/projects/{PROJECT_ID}/files",
            data=data,
            files=files,
            headers=make_auth_header(USER_A_ID),
        )
        assert res.status_code == 400
        assert res.json()["error"]["code"] == "FILE_TOO_LARGE"


# --- D2-06: Media Audio Extraction Tests ---
from app.services.file_processing.media_extractor import extract_audio_from_video
from app.core.errors import AppException
from pathlib import Path


def test_media_extractor_corrupt_file_handling(tmp_path):
    fake_video = tmp_path / "corrupt.mp4"
    fake_video.write_bytes(b"not an actual mp4 video content")
    out_audio = tmp_path / "output.mp3"

    with pytest.raises(AppException) as exc_info:
        extract_audio_from_video(fake_video, out_audio)

    assert exc_info.value.code in ("FFMPEG_NOT_FOUND", "MEDIA_EXTRACTION_ERROR")
