from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
import httpx

from app.core.config import settings
from app.core.errors import AppException


class EvaluationRepository:
    def __init__(self):
        self.base_url = settings.SUPABASE_URL.rstrip("/")
        self.service_key = settings.SUPABASE_SERVICE_ROLE_KEY
        self.headers = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    async def create(self, project_id: str, user_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/rest/v1/evaluations"
        payload = {
            "project_id": project_id,
            "user_id": user_id,
            "status": "PENDING",
            "rubric_version": "v1.0",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload, headers=self.headers)
            if resp.status_code not in (200, 201):
                raise AppException(
                    code="DATABASE_ERROR",
                    message=f"Failed to create evaluation: {resp.text}",
                    status_code=500,
                )
            return resp.json()[0]

    async def get_by_id(self, evaluation_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/rest/v1/evaluations"
        params = {
            "id": f"eq.{evaluation_id}",
            "user_id": f"eq.{user_id}",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params, headers=self.headers)
            if resp.status_code == 200:
                rows = resp.json()
                return rows[0] if rows else None
            return None

    async def list_by_user(self, user_id: str, limit: int = 30) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/rest/v1/evaluations"
        params = {
            "user_id": f"eq.{user_id}",
            "order": "created_at.desc",
            "limit": str(limit),
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params, headers=self.headers)
            if resp.status_code == 200:
                return resp.json()
            return []

    async def list_by_project(self, project_id: str, user_id: str, limit: int = 30) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/rest/v1/evaluations"
        params = {
            "project_id": f"eq.{project_id}",
            "user_id": f"eq.{user_id}",
            "order": "created_at.desc",
            "limit": str(limit),
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params, headers=self.headers)
            if resp.status_code == 200:
                return resp.json()
            return []

    async def update_status(
        self,
        evaluation_id: str,
        status: str,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> bool:
        url = f"{self.base_url}/rest/v1/evaluations?id=eq.{evaluation_id}"
        payload = {
            "status": status,
            "error_code": error_code,
            "error_message": error_message,
        }
        if status in ("COMPLETED", "PARTIAL", "FAILED"):
            payload["completed_at"] = datetime.utcnow().isoformat()

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.patch(url, json=payload, headers=self.headers)
            return resp.status_code in (200, 204)

    async def save_transcript(
        self,
        evaluation_id: str,
        language: str,
        full_text: str,
        segments: List[Dict[str, Any]],
        provider: str = "whisper",
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/rest/v1/transcripts"
        payload = {
            "evaluation_id": evaluation_id,
            "language": language,
            "full_text": full_text,
            "segments": segments,
            "provider": provider,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload, headers=self.headers)
            if resp.status_code not in (200, 201):
                raise AppException(
                    code="DATABASE_ERROR",
                    message=f"Failed to persist transcript: {resp.text}",
                    status_code=500,
                )
            return resp.json()[0]

    async def get_transcript(self, evaluation_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        # Verify ownership through evaluation
        eval_row = await self.get_by_id(evaluation_id, user_id)
        if not eval_row:
            return None

        url = f"{self.base_url}/rest/v1/transcripts"
        params = {"evaluation_id": f"eq.{evaluation_id}"}
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params, headers=self.headers)
            if resp.status_code == 200:
                rows = resp.json()
                return rows[0] if rows else None
            return None

    async def save_analysis_report(
        self,
        evaluation_id: str,
        report_json: Dict[str, Any],
        evaluated_count: int,
        not_evaluated_count: int,
        version: int = 1,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/rest/v1/analysis_reports"
        payload = {
            "evaluation_id": evaluation_id,
            "version": version,
            "report_json": report_json,
            "evaluated_count": evaluated_count,
            "not_evaluated_count": not_evaluated_count,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload, headers=self.headers)
            if resp.status_code not in (200, 201):
                raise AppException(
                    code="DATABASE_ERROR",
                    message=f"Failed to persist analysis report: {resp.text}",
                    status_code=500,
                )
            return resp.json()[0]

    async def get_latest_report(self, evaluation_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        # Verify ownership through evaluation
        eval_row = await self.get_by_id(evaluation_id, user_id)
        if not eval_row:
            return None

        url = f"{self.base_url}/rest/v1/analysis_reports"
        params = {
            "evaluation_id": f"eq.{evaluation_id}",
            "order": "version.desc",
            "limit": "1",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params, headers=self.headers)
            if resp.status_code == 200:
                rows = resp.json()
                return rows[0] if rows else None
            return None

    async def delete(self, evaluation_id: str, user_id: str) -> bool:
        existing = await self.get_by_id(evaluation_id, user_id)
        if not existing:
            return False

        url = f"{self.base_url}/rest/v1/evaluations?id=eq.{evaluation_id}&user_id=eq.{user_id}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.delete(url, headers=self.headers)
            return resp.status_code in (200, 204)


evaluation_repository = EvaluationRepository()

