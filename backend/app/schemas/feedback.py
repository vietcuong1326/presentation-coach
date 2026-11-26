from typing import List, Optional, Literal
from uuid import UUID
from pydantic import BaseModel, Field


class EvidenceCoverage(BaseModel):
    evaluated_criteria: int = 0
    not_evaluated_criteria: int = 0


class EvaluationSummary(BaseModel):
    headline: str
    overall_feedback: str
    evidence_coverage: EvidenceCoverage


class StrengthItem(BaseModel):
    title: str
    description: str
    evidence_ids: List[str] = []
    related_criteria: List[str] = []


class ImprovementItem(BaseModel):
    id: str
    title: str
    severity: Literal["HIGH", "MEDIUM", "LOW"]
    scope: Literal["GROUP", "INDIVIDUAL"]
    member_id: Optional[str] = None
    observation: str
    impact: str
    recommendation: str
    example: Optional[str] = None
    evidence_ids: List[str] = []
    related_criteria: List[str] = []


class CriterionResult(BaseModel):
    criterion_id: str
    scope: Literal["GROUP", "INDIVIDUAL"]
    member_id: Optional[str] = None
    status: Literal["EVALUATED", "NOT_EVALUATED", "PENDING"]
    score: Optional[int] = Field(None, ge=1, le=5)
    level: Optional[Literal["SUPERIOR", "EXCELLENT", "VERY_GOOD", "SATISFACTORY", "UNACCEPTABLE"]] = None
    reason: str
    evidence_ids: List[str] = []
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)


class PriorityAction(BaseModel):
    title: str
    steps: List[str] = []
    related_feedback_ids: List[str] = []


class AnalysisReportPayload(BaseModel):
    evaluation_summary: EvaluationSummary
    strengths: List[StrengthItem] = []
    improvements: List[ImprovementItem] = []
    criterion_results: List[CriterionResult] = []
    priority_actions: List[PriorityAction] = []


class AnalysisReportResponse(BaseModel):
    id: UUID
    evaluation_id: UUID
    version: int = 1
    report_json: AnalysisReportPayload
    evaluated_count: int
    not_evaluated_count: int
    created_at: str

