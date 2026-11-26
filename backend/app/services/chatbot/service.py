from typing import Optional, Dict, Any, List
import httpx
from app.core.config import settings
from app.core.errors import AppException
from app.repositories.chat_repository import ChatRepository
from app.repositories.evaluation_repository import EvaluationRepository
from app.repositories.file_repository import FileRepository
from app.repositories.project_repository import ProjectRepository
from app.services.chatbot.context_assembler import EvaluationContextAssembler


class ChatbotService:
    def __init__(
        self,
        chat_repo: Optional[ChatRepository] = None,
        eval_repo: Optional[EvaluationRepository] = None,
        file_repo: Optional[FileRepository] = None,
        project_repo: Optional[ProjectRepository] = None,
    ):
        self.chat_repo = chat_repo or ChatRepository()
        self.eval_repo = eval_repo or EvaluationRepository()
        self.file_repo = file_repo or FileRepository()
        self.project_repo = project_repo or ProjectRepository()
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.OPENAI_EVALUATION_MODEL or "gpt-4o-mini"

    async def chat(
        self,
        evaluation_id: str,
        user_id: str,
        message: str,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Process an interactive chat message grounded in the evaluation report."""
        # 1. Verify evaluation ownership
        eval_record = await self.eval_repo.get_by_id(evaluation_id, user_id)
        if not eval_record:
            raise AppException(
                code="EVALUATION_NOT_FOUND",
                message="Evaluation not found or access denied.",
                status_code=404,
            )

        # 2. Retrieve project metadata
        project = await self.project_repo.get_by_id(eval_record["project_id"], user_id)
        if not project:
            raise AppException(
                code="PROJECT_NOT_FOUND",
                message="Associated project not found.",
                status_code=404,
            )
        project_dict = project.model_dump() if hasattr(project, "model_dump") else project
        proj_title = project_dict.get("title") or project_dict.get("name") or "Presentation"

        # 3. Retrieve evaluation report, transcript, and slide texts
        report = await self.eval_repo.get_latest_report(evaluation_id, user_id)
        transcript = await self.eval_repo.get_transcript(evaluation_id, user_id)
        files = await self.file_repo.list_files_by_evaluation(evaluation_id, user_id)

        # Aggregate slide texts
        slide_text_parts: List[str] = []
        for f in files:
            slides = f.get("extracted_slides") or []
            for s in slides:
                p_num = s.get("page_number")
                txt = s.get("text", "").strip()
                if txt:
                    slide_text_parts.append(f"[Slide {p_num}]: {txt}")
        slide_text = "\n".join(slide_text_parts)

        # 4. Get or create chat session
        session = await self.chat_repo.get_or_create_session(
            evaluation_id=evaluation_id,
            user_id=user_id,
            session_id=session_id,
            title=f"Coaching for {proj_title}",
        )
        current_session_id = str(session["id"])

        # 5. Fetch prior messages before saving current one
        prior_messages = await self.chat_repo.get_messages_by_session(current_session_id)

        # 6. Save current user message
        await self.chat_repo.add_message(
            session_id=current_session_id,
            role="USER",
            content=message,
        )

        # 7. Assemble system prompt
        system_prompt = EvaluationContextAssembler.assemble_system_prompt(
            project=project_dict,
            report=report,
            transcript=transcript,
            slide_text=slide_text,
        )

        # 8. Build message history for LLM
        messages_payload = [{"role": "system", "content": system_prompt}]
        for pm in prior_messages[-10:]:  # Last 10 messages for conversation continuity
            role = "user" if pm["role"] == "USER" else "assistant"
            messages_payload.append({"role": role, "content": pm["content"]})
        messages_payload.append({"role": "user", "content": message})

        # 9. Call OpenAI Chat Completions API
        assistant_content = await self._call_llm(messages_payload)

        # 10. Save assistant response
        assistant_msg = await self.chat_repo.add_message(
            session_id=current_session_id,
            role="ASSISTANT",
            content=assistant_content,
        )

        return {
            "session_id": current_session_id,
            "message": assistant_msg,
        }

    async def get_history(self, evaluation_id: str, user_id: str) -> Dict[str, Any]:
        """Fetch chat sessions and history for an evaluation."""
        eval_record = await self.eval_repo.get_by_id(evaluation_id, user_id)
        if not eval_record:
            raise AppException(
                code="EVALUATION_NOT_FOUND",
                message="Evaluation not found or access denied.",
                status_code=404,
            )

        sessions = await self.chat_repo.get_sessions_by_evaluation(evaluation_id, user_id)
        return {
            "evaluation_id": evaluation_id,
            "sessions": sessions,
        }

    async def _call_llm(self, messages: List[Dict[str, str]]) -> str:
        is_gemini = (settings.AI_PROVIDER or "").lower().strip() == "gemini" or (bool(settings.GEMINI_API_KEY) and not self.api_key)
        if is_gemini:
            return await self._call_gemini(messages)
        return await self._call_openai(messages)

    async def _call_openai(self, messages: List[Dict[str, str]]) -> str:
        if not self.api_key:
            raise AppException(
                code="API_KEY_MISSING",
                message="OpenAI API key is required for presentation coaching chatbot.",
                status_code=500,
            )

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 1000,
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                raise AppException(
                    code="AI_CHATBOT_ERROR",
                    message=f"OpenAI chatbot call failed ({resp.status_code}): {resp.text[:200]}",
                    status_code=500,
                )
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def _call_gemini(self, messages: List[Dict[str, str]]) -> str:
        if not settings.GEMINI_API_KEY:
            raise AppException(
                code="API_KEY_MISSING",
                message="Google Gemini API key is required when AI_PROVIDER is set to 'gemini'.",
                status_code=500,
            )

        system_text = next((m["content"] for m in messages if m["role"] == "system"), "")
        chat_contents = []
        for m in messages:
            if m["role"] == "system":
                continue
            role = "user" if m["role"] == "user" else "model"
            chat_contents.append({
                "role": role,
                "parts": [{"text": m["content"]}]
            })

        model_name = settings.GEMINI_MODEL or "gemini-3.5-flash"
        candidates = [model_name]
        for fallback in ("gemini-3.5-flash", "gemini-3-flash-preview"):
            if fallback not in candidates:
                candidates.append(fallback)

        payload: Dict[str, Any] = {
            "contents": chat_contents,
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 1000,
            },
        }
        if system_text:
            payload["system_instruction"] = {
                "parts": [{"text": system_text}]
            }

        last_error = None
        for candidate in candidates:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{candidate}:generateContent?key={settings.GEMINI_API_KEY}"
            try:
                async with httpx.AsyncClient(timeout=45.0) as client:
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        return data["candidates"][0]["content"]["parts"][0]["text"]

                    last_error = f"Gemini chatbot call failed on {candidate} ({resp.status_code}): {resp.text[:200]}"
                    if resp.status_code in (404, 503) and candidate != candidates[-1]:
                        continue
                    raise AppException(
                        code="AI_CHATBOT_ERROR",
                        message=last_error,
                        status_code=500,
                    )
            except httpx.RequestError as e:
                last_error = f"Network error communicating with Gemini chatbot on {candidate}: {str(e)}"
                if candidate != candidates[-1]:
                    continue
                raise AppException(
                    code="AI_CHATBOT_ERROR",
                    message=last_error,
                    status_code=500,
                )

        raise AppException(
            code="AI_CHATBOT_ERROR",
            message=last_error or "All candidate Gemini models failed for chatbot.",
            status_code=500,
        )

