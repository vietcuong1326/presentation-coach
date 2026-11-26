from typing import List, Optional, Dict, Any
from uuid import uuid4
import httpx

from app.core.config import settings
from app.core.errors import AppException


class FileRepository:
    def __init__(self):
        self.base_url = settings.SUPABASE_URL.rstrip("/")
        self.service_key = settings.SUPABASE_SERVICE_ROLE_KEY
        self.bucket = "presentations"
        self.headers = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
        }

    async def get_or_create_pending_evaluation(self, project_id: str, user_id: str) -> str:
        """Finds or creates a PENDING evaluation for this project to attach files to."""
        url = f"{self.base_url}/rest/v1/evaluations"
        params = {
            "project_id": f"eq.{project_id}",
            "user_id": f"eq.{user_id}",
            "status": "eq.PENDING",
            "order": "created_at.desc",
            "limit": "1",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(url, params=params, headers=self.headers)
            if res.status_code == 200:
                rows = res.json()
                if rows:
                    return rows[0]["id"]

            # Create new PENDING evaluation
            post_payload = {
                "project_id": project_id,
                "user_id": user_id,
                "status": "PENDING",
                "rubric_version": "v1.0",
            }
            create_res = await client.post(
                url,
                json=post_payload,
                headers={**self.headers, "Content-Type": "application/json", "Prefer": "return=representation"},
            )
            if create_res.status_code in (200, 201):
                return create_res.json()[0]["id"]
            raise AppException(
                code="DATABASE_ERROR",
                message=f"Failed to initialize evaluation for file upload: {create_res.text}",
                status_code=500,
            )

    async def upload_to_storage(self, storage_path: str, file_bytes: bytes, mime_type: str) -> str:
        """Uploads private binary bytes to Supabase Storage bucket."""
        url = f"{self.base_url}/storage/v1/object/{self.bucket}/{storage_path}"
        headers = {
            **self.headers,
            "Content-Type": mime_type,
            "x-upsert": "true",
        }
        timeout = httpx.Timeout(120.0, connect=15.0)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(url, content=file_bytes, headers=headers)
        except httpx.TimeoutException:
            raise AppException(
                code="STORAGE_TIMEOUT",
                message="Uploading file to storage timed out. Please try a smaller file or retry.",
                status_code=504,
            )
        except httpx.RequestError as exc:
            raise AppException(
                code="STORAGE_ERROR",
                message=f"Network error while uploading file to storage: {exc}",
                status_code=502,
            )

        if resp.status_code not in (200, 201):
            raise AppException(
                code="STORAGE_ERROR",
                message=f"Failed to store private file in storage: {resp.text}",
                status_code=500,
            )
        return storage_path

    async def create_file_record(
        self,
        evaluation_id: str,
        user_id: str,
        file_role: str,
        storage_path: str,
        original_filename: str,
        mime_type: str,
        size_bytes: int,
    ) -> Dict[str, Any]:
        """Creates record in evaluation_files table."""
        url = f"{self.base_url}/rest/v1/evaluation_files"
        payload = {
            "evaluation_id": evaluation_id,
            "user_id": user_id,
            "file_role": file_role,
            "storage_bucket": self.bucket,
            "storage_path": storage_path,
            "original_filename": original_filename,
            "mime_type": mime_type,
            "size_bytes": size_bytes,
            "processing_status": "UPLOADED",
        }
        headers = {
            **self.headers,
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code not in (200, 201):
                raise AppException(
                    code="DATABASE_ERROR",
                    message=f"Failed to persist file metadata: {resp.text}",
                    status_code=500,
                )
            return resp.json()[0]

    async def list_files_by_evaluation(self, evaluation_id: str, user_id: str) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/rest/v1/evaluation_files"
        params = {
            "evaluation_id": f"eq.{evaluation_id}",
            "user_id": f"eq.{user_id}",
            "order": "created_at.desc",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params, headers=self.headers)
            if resp.status_code == 200:
                return resp.json()
            return []

    async def delete_from_storage(self, storage_paths: List[str]) -> bool:
        """Deletes private objects from Supabase Storage bucket to avoid orphans."""
        if not storage_paths:
            return True
        url = f"{self.base_url}/storage/v1/object/{self.bucket}"
        headers = {
            **self.headers,
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.request("DELETE", url, json={"prefixes": storage_paths}, headers=headers)
            return resp.status_code in (200, 204)


file_repository = FileRepository()

