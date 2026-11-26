from datetime import datetime
from typing import List, Optional
from uuid import UUID
import httpx

from app.core.config import settings
from app.core.errors import AppException
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse, MemberResponse


class ProjectRepository:
    def __init__(self):
        self.base_url = settings.SUPABASE_URL.rstrip("/")
        self.service_key = settings.SUPABASE_SERVICE_ROLE_KEY
        self.headers = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    async def create(self, user_id: str, project_in: ProjectCreate) -> ProjectResponse:
        url = f"{self.base_url}/rest/v1/projects"
        payload = {
            "user_id": user_id,
            "title": project_in.title,
            "topic": project_in.topic,
            "objectives": project_in.objectives,
            "target_audience": project_in.target_audience,
            "presentation_type": project_in.presentation_type,
            "expected_duration_seconds": project_in.expected_duration_seconds,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload, headers=self.headers)
            if resp.status_code not in (200, 201):
                raise AppException(
                    code="DATABASE_ERROR",
                    message=f"Failed to create project: {resp.text}",
                    status_code=500,
                )
            created_proj = resp.json()[0]
            project_id = created_proj["id"]

            members_resp: List[MemberResponse] = []
            if project_in.members:
                members_url = f"{self.base_url}/rest/v1/project_members"
                members_payload = [
                    {
                        "project_id": project_id,
                        "name": m.name,
                        "start_time_seconds": m.start_time_seconds,
                        "end_time_seconds": m.end_time_seconds,
                        "display_order": m.display_order if m.display_order else idx,
                    }
                    for idx, m in enumerate(project_in.members)
                ]
                m_resp = await client.post(members_url, json=members_payload, headers=self.headers)
                if m_resp.status_code in (200, 201):
                    members_resp = [MemberResponse(**item) for item in m_resp.json()]

            return ProjectResponse(
                id=created_proj["id"],
                user_id=created_proj["user_id"],
                title=created_proj["title"],
                topic=created_proj.get("topic"),
                objectives=created_proj.get("objectives"),
                target_audience=created_proj.get("target_audience"),
                presentation_type=created_proj["presentation_type"],
                expected_duration_seconds=created_proj.get("expected_duration_seconds"),
                members=members_resp,
                created_at=created_proj["created_at"],
                updated_at=created_proj["updated_at"],
            )

    async def list_by_user(self, user_id: str) -> List[ProjectResponse]:
        url = f"{self.base_url}/rest/v1/projects"
        params = {
            "user_id": f"eq.{user_id}",
            "select": "*,members:project_members(*)",
            "order": "created_at.desc",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params, headers=self.headers)
            if resp.status_code != 200:
                raise AppException(
                    code="DATABASE_ERROR",
                    message=f"Failed to list projects: {resp.text}",
                    status_code=500,
                )
            results = []
            for item in resp.json():
                members = [MemberResponse(**m) for m in item.get("members", [])]
                results.append(
                    ProjectResponse(
                        id=item["id"],
                        user_id=item["user_id"],
                        title=item["title"],
                        topic=item.get("topic"),
                        objectives=item.get("objectives"),
                        target_audience=item.get("target_audience"),
                        presentation_type=item["presentation_type"],
                        expected_duration_seconds=item.get("expected_duration_seconds"),
                        members=members,
                        created_at=item["created_at"],
                        updated_at=item["updated_at"],
                    )
                )
            return results

    async def get_by_id(self, project_id: str, user_id: str) -> Optional[ProjectResponse]:
        url = f"{self.base_url}/rest/v1/projects"
        params = {
            "id": f"eq.{project_id}",
            "user_id": f"eq.{user_id}",
            "select": "*,members:project_members(*)",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params, headers=self.headers)
            if resp.status_code != 200:
                return None
            data = resp.json()
            if not data:
                return None
            item = data[0]
            members = [MemberResponse(**m) for m in item.get("members", [])]
            return ProjectResponse(
                id=item["id"],
                user_id=item["user_id"],
                title=item["title"],
                topic=item.get("topic"),
                objectives=item.get("objectives"),
                target_audience=item.get("target_audience"),
                presentation_type=item["presentation_type"],
                expected_duration_seconds=item.get("expected_duration_seconds"),
                members=members,
                created_at=item["created_at"],
                updated_at=item["updated_at"],
            )

    async def update(self, project_id: str, user_id: str, update_in: ProjectUpdate) -> Optional[ProjectResponse]:
        # 1. Check ownership
        existing = await self.get_by_id(project_id, user_id)
        if not existing:
            return None

        url = f"{self.base_url}/rest/v1/projects?id=eq.{project_id}&user_id=eq.{user_id}"
        patch_payload = {}
        for field in ("title", "topic", "objectives", "target_audience", "presentation_type", "expected_duration_seconds"):
            val = getattr(update_in, field)
            if val is not None:
                patch_payload[field] = val
        patch_payload["updated_at"] = datetime.utcnow().isoformat()

        async with httpx.AsyncClient(timeout=10.0) as client:
            if patch_payload:
                resp = await client.patch(url, json=patch_payload, headers=self.headers)
                if resp.status_code not in (200, 204):
                    raise AppException(
                        code="DATABASE_ERROR",
                        message=f"Failed to update project: {resp.text}",
                        status_code=500,
                    )

            # Update members if provided
            if update_in.members is not None:
                # Delete existing members
                del_url = f"{self.base_url}/rest/v1/project_members?project_id=eq.{project_id}"
                await client.delete(del_url, headers=self.headers)

                # Insert new members
                if update_in.members:
                    ins_url = f"{self.base_url}/rest/v1/project_members"
                    ins_payload = [
                        {
                            "project_id": project_id,
                            "name": m.name,
                            "start_time_seconds": m.start_time_seconds,
                            "end_time_seconds": m.end_time_seconds,
                            "display_order": m.display_order if m.display_order else idx,
                        }
                        for idx, m in enumerate(update_in.members)
                    ]
                    await client.post(ins_url, json=ins_payload, headers=self.headers)

        return await self.get_by_id(project_id, user_id)

    async def delete(self, project_id: str, user_id: str) -> bool:
        existing = await self.get_by_id(project_id, user_id)
        if not existing:
            return False

        url = f"{self.base_url}/rest/v1/projects?id=eq.{project_id}&user_id=eq.{user_id}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.delete(url, headers=self.headers)
            return resp.status_code in (200, 204)


project_repository = ProjectRepository()

