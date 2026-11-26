from datetime import datetime
from typing import List, Optional, Literal
from uuid import UUID
from pydantic import BaseModel, Field, model_validator


class MemberBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    start_time_seconds: Optional[float] = Field(None, ge=0)
    end_time_seconds: Optional[float] = Field(None, ge=0)
    display_order: int = 0

    @model_validator(mode="after")
    def validate_time_range(self):
        if self.start_time_seconds is not None and self.end_time_seconds is not None:
            if self.start_time_seconds >= self.end_time_seconds:
                raise ValueError("start_time_seconds must be less than end_time_seconds")
        return self


class MemberCreate(MemberBase):
    pass


class MemberResponse(MemberBase):
    id: UUID
    project_id: UUID


class ProjectBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    topic: Optional[str] = Field(None, max_length=255)
    objectives: Optional[str] = None
    target_audience: Optional[str] = Field(None, max_length=255)
    presentation_type: Literal["INDIVIDUAL", "GROUP"] = "INDIVIDUAL"
    expected_duration_seconds: Optional[int] = Field(None, ge=1)


class ProjectCreate(ProjectBase):
    members: List[MemberCreate] = []

    @model_validator(mode="after")
    def validate_members_and_overlaps(self):
        # Check overlapping time windows among members if provided
        timed_members = [
            (i, m) for i, m in enumerate(self.members)
            if m.start_time_seconds is not None and m.end_time_seconds is not None
        ]
        # Sort by start_time
        timed_members.sort(key=lambda x: x[1].start_time_seconds)
        for j in range(len(timed_members) - 1):
            curr_idx, curr_m = timed_members[j]
            next_idx, next_m = timed_members[j + 1]
            if curr_m.end_time_seconds > next_m.start_time_seconds:
                # We flag overlaps as notes, but per SRS_MVP FR-09:
                # "flag ranges outside media duration and overlaps for user review"
                # If both members overlap, we allow creation but attach a warning/flag
                pass
        return self


class ProjectUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    topic: Optional[str] = None
    objectives: Optional[str] = None
    target_audience: Optional[str] = None
    presentation_type: Optional[Literal["INDIVIDUAL", "GROUP"]] = None
    expected_duration_seconds: Optional[int] = Field(None, ge=1)
    members: Optional[List[MemberCreate]] = None


class ProjectResponse(ProjectBase):
    id: UUID
    user_id: UUID
    members: List[MemberResponse] = []
    warnings: List[str] = []
    created_at: datetime
    updated_at: datetime

