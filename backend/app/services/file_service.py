import re
from pathlib import Path
from uuid import uuid4
from typing import List, Dict, Any, Optional

from app.core.config import settings
from app.core.errors import AppException
from app.repositories.project_repository import project_repository, ProjectRepository
from app.repositories.file_repository import file_repository, FileRepository
from app.services.file_processing.pdf_extractor import extract_text_from_pdf
from app.services.file_processing.pptx_extractor import extract_text_from_pptx
from app.schemas.file import FileMetadataResponse, SlideContent


class FileService:
    def __init__(
        self,
        repo: FileRepository = file_repository,
        proj_repo: ProjectRepository = project_repository,
    ):
        self.repo = repo
        self.proj_repo = proj_repo

    def sanitize_filename(self, filename: str) -> str:
        # Keep alphanumeric, dot, dash, underscore
        clean = re.sub(r"[^a-zA-Z0-9._-]", "_", filename)
        return clean[:100]

    async def upload_project_file(
        self,
        project_id: str,
        user_id: str,
        file_role: str,
        original_filename: str,
        file_bytes: bytes,
        content_type: Optional[str] = None,
    ) -> FileMetadataResponse:
        # 1. Verify project ownership
        project = await self.proj_repo.get_by_id(project_id, user_id)
        if not project:
            raise AppException(
                code="RESOURCE_NOT_FOUND",
                message="Project not found or not owned by user.",
                status_code=404,
            )

        # 2. Validate file size
        size_bytes = len(file_bytes)
        ext = Path(original_filename).suffix.lower()

        if file_role == "SLIDES":
            max_bytes = settings.MAX_SLIDE_SIZE_MB * 1024 * 1024
            if size_bytes > max_bytes:
                raise AppException(
                    code="FILE_TOO_LARGE",
                    message=f"Slide file exceeds maximum limit of {settings.MAX_SLIDE_SIZE_MB}MB.",
                    status_code=400,
                )
            if ext not in (".pdf", ".pptx"):
                raise AppException(
                    code="UNSUPPORTED_FILE_TYPE",
                    message="Unsupported slide format. Allowed: .pdf, .pptx",
                    status_code=400,
                )
        elif file_role in ("AUDIO", "VIDEO"):
            max_bytes = settings.MAX_MEDIA_SIZE_MB * 1024 * 1024
            if size_bytes > max_bytes:
                raise AppException(
                    code="FILE_TOO_LARGE",
                    message=f"Media file exceeds maximum limit of {settings.MAX_MEDIA_SIZE_MB}MB.",
                    status_code=400,
                )
            if ext not in (".mp3", ".wav", ".m4a", ".mp4"):
                raise AppException(
                    code="UNSUPPORTED_FILE_TYPE",
                    message="Unsupported media format. Allowed: .mp3, .wav, .m4a, .mp4",
                    status_code=400,
                )

        # 3. Get or create pending evaluation
        eval_id = await self.repo.get_or_create_pending_evaluation(project_id, user_id)

        # 4. Storage path: {user_id}/{project_id}/{file_uuid}_{clean_name}
        file_uuid = uuid4()
        clean_name = self.sanitize_filename(original_filename)
        storage_path = f"{user_id}/{project_id}/{file_uuid}_{clean_name}"

        # 5. Upload to Supabase Storage
        actual_mime = content_type or "application/octet-stream"
        await self.repo.upload_to_storage(storage_path, file_bytes, actual_mime)

        # 6. Extract text if SLIDES
        extracted_slides: Optional[List[SlideContent]] = None
        if file_role == "SLIDES":
            if ext == ".pdf":
                raw_slides = extract_text_from_pdf(file_bytes)
            elif ext == ".pptx":
                raw_slides = extract_text_from_pptx(file_bytes)
            else:
                raw_slides = []
            extracted_slides = [SlideContent(**s) for s in raw_slides]

        # 7. Persist metadata record
        record = await self.repo.create_file_record(
            evaluation_id=eval_id,
            user_id=user_id,
            file_role=file_role,
            storage_path=storage_path,
            original_filename=original_filename,
            mime_type=actual_mime,
            size_bytes=size_bytes,
        )

        return FileMetadataResponse(
            id=record["id"],
            project_id=project.id,
            user_id=project.user_id,
            file_role=record["file_role"],
            original_filename=record["original_filename"],
            mime_type=record["mime_type"],
            size_bytes=record["size_bytes"],
            processing_status=record["processing_status"],
            storage_path=record["storage_path"],
            created_at=record["created_at"],
            extracted_slides=extracted_slides,
        )


file_service = FileService()

