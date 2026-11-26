import sys
from pathlib import Path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

import asyncio
import unittest
from unittest.mock import AsyncMock

from app.core.config import settings
from app.services.ai_evaluator.pipeline import AIEvaluationPipeline
from app.services.transcription.service import TranscriptionService
from app.services.chatbot.service import ChatbotService


class TestProviderRouting(unittest.IsolatedAsyncioTestCase):
    async def test_evaluation_pipeline_routes_to_gemini(self):
        settings.AI_PROVIDER = "gemini"
        settings.GEMINI_API_KEY = "mock-key"
        pipeline = AIEvaluationPipeline()
        pipeline.evaluate_with_gemini = AsyncMock(return_value="gemini_eval_report")
        pipeline.evaluate_with_openai = AsyncMock(return_value="openai_eval_report")

        res = await pipeline.evaluate_presentation({"title": "Test"}, [], {"full_text": ""})
        self.assertEqual(res, "gemini_eval_report")
        pipeline.evaluate_with_gemini.assert_awaited_once()
        pipeline.evaluate_with_openai.assert_not_called()

    async def test_transcription_service_routes_to_gemini(self):
        settings.AI_PROVIDER = "gemini"
        settings.GEMINI_API_KEY = "mock-key"
        service = TranscriptionService()
        service.transcribe_with_gemini = AsyncMock(return_value={"provider": "gemini"})
        service.transcribe_with_whisper = AsyncMock(return_value={"provider": "whisper"})

        res = await service.transcribe_audio(b"audio-data")
        self.assertEqual(res["provider"], "gemini")
        service.transcribe_with_gemini.assert_awaited_once()
        service.transcribe_with_whisper.assert_not_called()

    async def test_chatbot_service_routes_to_gemini(self):
        settings.AI_PROVIDER = "gemini"
        settings.GEMINI_API_KEY = "mock-key"
        service = ChatbotService()
        service._call_gemini = AsyncMock(return_value="gemini_reply")
        service._call_openai = AsyncMock(return_value="openai_reply")

        res = await service._call_llm([{"role": "user", "content": "hi"}])
        self.assertEqual(res, "gemini_reply")
        service._call_gemini.assert_awaited_once()
        service._call_openai.assert_not_called()


if __name__ == "__main__":
    unittest.main()
