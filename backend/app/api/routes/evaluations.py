from typing import List
from fastapi import APIRouter, Depends, BackgroundTasks, status
from app.core.security import AuthenticatedUser, get_current_user
from app.schemas.evaluation import EvaluationCreateResponse, EvaluationStatusResponse, EvaluationListItem
from app.services.evaluation_service import evaluation_service, EvaluationService

router = APIRouter(tags=["evaluations"])


def get_evaluation_service() -> EvaluationService:
    return evaluation_service


@router.post(
    "/projects/{project_id}/evaluations",
    response_model=EvaluationCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_evaluation(
    project_id: str,
    background_tasks: BackgroundTasks,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: EvaluationService = Depends(get_evaluation_service),
):
    """
    Start an evaluation for a project.
    Schedules AI pipeline asynchronously in the background to avoid blocking HTTP.
    """
    init_res = await service.start_evaluation(project_id, current_user.id)
    eval_id = init_res["id"]

    # Schedule background processing
    background_tasks.add_task(
        service.run_evaluation_pipeline,
        evaluation_id=eval_id,
        project_id=project_id,
        user_id=current_user.id,
    )

    return EvaluationCreateResponse(id=eval_id, status="PENDING")


@router.get(
    "/projects/{project_id}/evaluations",
    response_model=List[EvaluationListItem],
)
async def list_project_evaluations(
    project_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: EvaluationService = Depends(get_evaluation_service),
):
    """List all evaluations for a project owned by authenticated user."""
    return await service.list_project_evaluations(project_id, current_user.id)


@router.get(
    "/evaluations",
    response_model=List[EvaluationListItem],
)
async def list_evaluations(
    limit: int = 30,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: EvaluationService = Depends(get_evaluation_service),
):
    """List recent evaluations owned by the authenticated user across all projects."""
    return await service.list_user_evaluations(current_user.id, limit=limit)


@router.get("/evaluations/{evaluation_id}", response_model=EvaluationStatusResponse)
async def get_evaluation_status(
    evaluation_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: EvaluationService = Depends(get_evaluation_service),
):
    """Return status and safe error information for an evaluation."""
    return await service.get_evaluation_status(evaluation_id, current_user.id)


@router.get("/evaluations/{evaluation_id}/report")
async def get_evaluation_report(
    evaluation_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: EvaluationService = Depends(get_evaluation_service),
):
    """Return the latest generated coaching report for an evaluation."""
    return await service.get_latest_report(evaluation_id, current_user.id)


@router.get("/evaluations/{evaluation_id}/transcript")
async def get_evaluation_transcript(
    evaluation_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: EvaluationService = Depends(get_evaluation_service),
):
    """Return the transcript with timestamped segments."""
    return await service.get_transcript(evaluation_id, current_user.id)


@router.delete("/evaluations/{evaluation_id}")
async def delete_evaluation(
    evaluation_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: EvaluationService = Depends(get_evaluation_service),
):
    """Delete an evaluation and its associated private files if owned by authenticated user."""
    return await service.delete_evaluation(evaluation_id, current_user.id)

