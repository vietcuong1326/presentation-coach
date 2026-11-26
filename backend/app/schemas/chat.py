from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class ChatMessageCreate(BaseModel):
    session_id: Optional[UUID] = None
    message: str = Field(..., min_length=1, max_length=4000)


class ChatMessageItem(BaseModel):
    id: UUID
    session_id: UUID
    role: str  # 'USER' | 'ASSISTANT'
    content: str
    created_at: datetime


class ChatResponse(BaseModel):
    session_id: UUID
    message: ChatMessageItem


class ChatSessionItem(BaseModel):
    id: UUID
    evaluation_id: UUID
    user_id: UUID
    title: Optional[str] = None
    created_at: datetime
    messages: List[ChatMessageItem] = []


class ChatHistoryResponse(BaseModel):
    evaluation_id: UUID
    sessions: List[ChatSessionItem]

