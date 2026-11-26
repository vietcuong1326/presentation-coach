from datetime import datetime
from typing import List, Optional, Literal
from uuid import UUID
from pydantic import BaseModel


class SlideContent(BaseModel):
    page_number: int
    text: str


class FileMetadataResponse(BaseModel):
    id: UUID
    project_id: UUID
    user_id: UUID
    file_role: Literal["SLIDES", "AUDIO", "VIDEO", "REPORT", "OTHER"]
    original_filename: str
    mime_type: Optional[str] = None
    size_bytes: int
    processing_status: Literal["UPLOADED", "PROCESSED", "FAILED"] = "UPLOADED"
    storage_path: str
    created_at: datetime
    extracted_slides: Optional[List[SlideContent]] = None

