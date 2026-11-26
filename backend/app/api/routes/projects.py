from typing import List
from fastapi import APIRouter, Depends, status
from app.core.security import AuthenticatedUser, get_current_user
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from app.services.project_service import project_service, ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


def get_project_service() -> ProjectService:
    return project_service


@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service),
):
    """List all projects owned by the authenticated user."""
    return await service.list_projects(current_user.id)


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_in: ProjectCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service),
):
    """Create a new presentation project."""
    return await service.create_project(current_user.id, project_in)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service),
):
    """Get project details if owned by authenticated user."""
    return await service.get_project(project_id, current_user.id)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    update_in: ProjectUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service),
):
    """Update project fields if owned by authenticated user."""
    return await service.update_project(project_id, current_user.id, update_in)


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service),
):
    """Delete a project if owned by authenticated user."""
    return await service.delete_project(project_id, current_user.id)
