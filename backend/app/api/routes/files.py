from fastapi import APIRouter, Depends, UploadFile, File, Form, status
from app.core.security import AuthenticatedUser, get_current_user
from app.schemas.file import FileMetadataResponse
from app.services.file_service import file_service, FileService

router = APIRouter(prefix="/projects", tags=["files"])


def get_file_service() -> FileService:
    return file_service


@router.post("/{project_id}/files", response_model=FileMetadataResponse, status_code=status.HTTP_201_CREATED)
async def upload_project_file(
    project_id: str,
    file_role: str = Form(...),
    file: UploadFile = File(...),
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: FileService = Depends(get_file_service),
):
    """
    Upload slide (PDF/PPTX) or media (MP3/WAV/M4A/MP4) file for a presentation project.
    Validates ownership, file role, size limits, and stores file privately.
    """
    content = await file.read()
    return await service.upload_project_file(
        project_id=project_id,
        user_id=current_user.id,
        file_role=file_role.upper(),
        original_filename=file.filename or "uploaded_file",
        file_bytes=content,
        content_type=file.content_type,
    )

