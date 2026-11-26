from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel


class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str


class TranscriptResponse(BaseModel):
    id: UUID
    evaluation_id: UUID
    language: str = "en"
    full_text: str
    segments: List[TranscriptSegment] = []
    provider: str = "whisper"
    created_at: datetime

