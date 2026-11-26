from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class EvaluationCreateResponse(BaseModel):
    id: UUID
    status: str = "PENDING"


class EvaluationStatusResponse(BaseModel):
    id: UUID
    project_id: UUID
    user_id: UUID
    status: str
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    rubric_version: str = "v1.0"
    created_at: datetime
    completed_at: Optional[datetime] = None


class EvaluationListItem(BaseModel):
    id: UUID
    project_id: UUID
    user_id: UUID
    status: str
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    rubric_version: str = "v1.0"
    created_at: datetime
    completed_at: Optional[datetime] = None
    project_title: Optional[str] = None
    presentation_type: Optional[str] = None

