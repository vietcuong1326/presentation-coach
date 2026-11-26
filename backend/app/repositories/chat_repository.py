from typing import List, Optional, Dict, Any
import httpx
from app.core.config import settings
from app.core.errors import AppException


class ChatRepository:
    def __init__(self):
        self.base_url = settings.SUPABASE_URL.rstrip("/")
        self.service_key = settings.SUPABASE_SERVICE_ROLE_KEY
        self.headers = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    async def get_session_by_id(self, session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/rest/v1/chat_sessions"
        params = {
            "id": f"eq.{session_id}",
            "user_id": f"eq.{user_id}",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params, headers=self.headers)
            if resp.status_code == 200:
                rows = resp.json()
                return rows[0] if rows else None
            return None

    async def get_or_create_session(
        self,
        evaluation_id: str,
        user_id: str,
        session_id: Optional[str] = None,
        title: Optional[str] = None,
    ) -> Dict[str, Any]:
        if session_id:
            existing = await self.get_session_by_id(session_id, user_id)
            if existing and existing.get("evaluation_id") == evaluation_id:
                return existing

        # Create new chat session
        url = f"{self.base_url}/rest/v1/chat_sessions"
        payload = {
            "evaluation_id": evaluation_id,
            "user_id": user_id,
            "title": title or "Presentation Coaching Session",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload, headers=self.headers)
            if resp.status_code not in (200, 201):
                raise AppException(
                    code="DATABASE_ERROR",
                    message=f"Failed to create chat session: {resp.text}",
                    status_code=500,
                )
            return resp.json()[0]

    async def add_message(self, session_id: str, role: str, content: str) -> Dict[str, Any]:
        url = f"{self.base_url}/rest/v1/chat_messages"
        payload = {
            "session_id": session_id,
            "role": role,
            "content": content,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload, headers=self.headers)
            if resp.status_code not in (200, 201):
                raise AppException(
                    code="DATABASE_ERROR",
                    message=f"Failed to save chat message: {resp.text}",
                    status_code=500,
                )
            return resp.json()[0]

    async def get_messages_by_session(self, session_id: str) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/rest/v1/chat_messages"
        params = {
            "session_id": f"eq.{session_id}",
            "order": "created_at.asc",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params, headers=self.headers)
            if resp.status_code == 200:
                return resp.json()
            return []

    async def get_sessions_by_evaluation(
        self, evaluation_id: str, user_id: str
    ) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/rest/v1/chat_sessions"
        params = {
            "evaluation_id": f"eq.{evaluation_id}",
            "user_id": f"eq.{user_id}",
            "order": "created_at.desc",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params, headers=self.headers)
            if resp.status_code == 200:
                sessions = resp.json()
                for sess in sessions:
                    sess["messages"] = await self.get_messages_by_session(sess["id"])
                return sessions
            return []

