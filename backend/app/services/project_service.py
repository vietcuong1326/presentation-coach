from typing import List, Optional
from app.core.errors import AppException
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from app.repositories.project_repository import project_repository, ProjectRepository


class ProjectService:
    def __init__(self, repo: ProjectRepository = project_repository):
        self.repo = repo

    def check_warnings(self, project: ProjectResponse) -> List[str]:
        warnings: List[str] = []
        members = project.members
        # Check overlaps
        timed_members = [
            m for m in members
            if m.start_time_seconds is not None and m.end_time_seconds is not None
        ]
        sorted_members = sorted(timed_members, key=lambda x: x.start_time_seconds)
        for i in range(len(sorted_members) - 1):
            curr_m = sorted_members[i]
            next_m = sorted_members[i + 1]
            if curr_m.end_time_seconds > next_m.start_time_seconds:
                warnings.append(
                    f"Speaking time overlap detected between '{curr_m.name}' ({curr_m.start_time_seconds}s-{curr_m.end_time_seconds}s) "
                    f"and '{next_m.name}' ({next_m.start_time_seconds}s-{next_m.end_time_seconds}s). Please review."
                )

        # Check duration limit
        if project.expected_duration_seconds:
            for m in timed_members:
                if m.end_time_seconds > project.expected_duration_seconds:
                    warnings.append(
                        f"Member '{m.name}' end time ({m.end_time_seconds}s) exceeds project expected duration ({project.expected_duration_seconds}s)."
                    )
        return warnings

    async def create_project(self, user_id: str, project_in: ProjectCreate) -> ProjectResponse:
        created = await self.repo.create(user_id, project_in)
        created.warnings = self.check_warnings(created)
        return created

    async def list_projects(self, user_id: str) -> List[ProjectResponse]:
        projects = await self.repo.list_by_user(user_id)
        for p in projects:
            p.warnings = self.check_warnings(p)
        return projects

    async def get_project(self, project_id: str, user_id: str) -> ProjectResponse:
        project = await self.repo.get_by_id(project_id, user_id)
        if not project:
            raise AppException(
                code="RESOURCE_NOT_FOUND",
                message="The requested project was not found.",
                status_code=404,
            )
        project.warnings = self.check_warnings(project)
        return project

    async def update_project(self, project_id: str, user_id: str, update_in: ProjectUpdate) -> ProjectResponse:
        updated = await self.repo.update(project_id, user_id, update_in)
        if not updated:
            raise AppException(
                code="RESOURCE_NOT_FOUND",
                message="The requested project was not found.",
                status_code=404,
            )
        updated.warnings = self.check_warnings(updated)
        return updated

    async def delete_project(self, project_id: str, user_id: str) -> dict:
        deleted = await self.repo.delete(project_id, user_id)
        if not deleted:
            raise AppException(
                code="RESOURCE_NOT_FOUND",
                message="The requested project was not found.",
                status_code=404,
            )
        return {"status": "ok", "message": "Project deleted successfully."}


project_service = ProjectService()

