import io
import json
import base64
from typing import Dict, Any, List
import httpx

from app.core.config import settings
from app.core.errors import AppException
from app.schemas.transcript import TranscriptSegment


class TranscriptionService:
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.OPENAI_TRANSCRIPTION_MODEL or "whisper-1"

    async def transcribe_audio(
        self,
        audio_bytes: bytes,
        filename: str = "audio.mp3",
    ) -> Dict[str, Any]:
        """
        Transcribes presentation audio using configured AI provider (OpenAI Whisper or Google Gemini).
        Returns full text and timestamped segments.
        """
        is_gemini = (settings.AI_PROVIDER or "").lower().strip() == "gemini" or (bool(settings.GEMINI_API_KEY) and not self.api_key)
        if is_gemini:
            return await self.transcribe_with_gemini(audio_bytes, filename)
        return await self.transcribe_with_whisper(audio_bytes, filename)

    async def transcribe_with_whisper(
        self,
        audio_bytes: bytes,
        filename: str = "audio.mp3",
    ) -> Dict[str, Any]:
        """Transcribes audio using OpenAI Whisper API."""
        if not self.api_key:
            raise AppException(
                code="API_KEY_MISSING",
                message="OpenAI API key is required for speech-to-text transcription.",
                status_code=500,
            )

        url = "https://api.openai.com/v1/audio/transcriptions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }

        mime = "audio/mpeg"
        if filename.endswith(".wav"):
            mime = "audio/wav"
        elif filename.endswith(".m4a"):
            mime = "audio/m4a"
        elif filename.endswith(".mp4"):
            mime = "audio/mp4"

        # Whisper expects multipart/form-data
        files = {
            "file": (filename, audio_bytes, mime),
        }
        data = {
            "model": self.model,
            "response_format": "verbose_json",
            "timestamp_granularities[]": "segment",
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(url, headers=headers, data=data, files=files)
                if resp.status_code != 200:
                    err_text = resp.text
                    try:
                        err_json = resp.json()
                        err_detail = err_json.get("error", {}).get("message", err_text)
                    except Exception:
                        err_detail = err_text[:200]
                    raise AppException(
                        code="TRANSCRIPTION_ERROR",
                        message=f"Whisper transcription failed ({resp.status_code}): {err_detail}",
                        status_code=500,
                    )
                payload = resp.json()

                full_text = payload.get("text", "").strip()
                raw_segments = payload.get("segments", [])

                segments: List[TranscriptSegment] = []
                for s in raw_segments:
                    segments.append(
                        TranscriptSegment(
                            start=round(float(s.get("start", 0.0)), 2),
                            end=round(float(s.get("end", 0.0)), 2),
                            text=s.get("text", "").strip(),
                        )
                    )

                return {
                    "language": payload.get("language", "en"),
                    "full_text": full_text,
                    "segments": [seg.model_dump() for seg in segments],
                    "provider": "whisper",
                }
        except httpx.RequestError as e:
            raise AppException(
                code="TRANSCRIPTION_NETWORK_ERROR",
                message=f"Network error communicating with Whisper API: {str(e)}",
                status_code=500,
            )

    async def transcribe_with_gemini(
        self,
        audio_bytes: bytes,
        filename: str = "audio.mp3",
    ) -> Dict[str, Any]:
        """Transcribes presentation audio using Google Gemini multimodal audio."""
        if not settings.GEMINI_API_KEY:
            raise AppException(
                code="API_KEY_MISSING",
                message="Google Gemini API key is required when AI_PROVIDER is set to 'gemini'.",
                status_code=500,
            )

        b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
        ext = filename.split(".")[-1].lower()
        mime = "audio/mp3" if ext in ("mp3", "mp4") else f"audio/{ext}"

        model_name = settings.GEMINI_MODEL or "gemini-3.5-flash"
        candidates = [model_name]
        for fallback in ("gemini-3.5-flash", "gemini-3-flash-preview"):
            if fallback not in candidates:
                candidates.append(fallback)

        prompt = (
            "Transcribe this English presentation audio track accurately. "
            "Return ONLY a valid JSON object matching this schema:\n"
            "{\n"
            '  "language": "en",\n'
            '  "full_text": "complete speech transcript",\n'
            '  "segments": [\n'
            '    {"start": 0.0, "end": 3.5, "text": "transcribed segment"}\n'
            "  ]\n"
            "}"
        )

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": mime,
                                "data": b64_audio,
                            }
                        },
                        {
                            "text": prompt,
                        },
                    ]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.1,
            },
        }

        last_error = None
        for candidate in candidates:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{candidate}:generateContent?key={settings.GEMINI_API_KEY}"
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                        parsed = json.loads(raw_text)

                        raw_segments = parsed.get("segments", [])
                        segments: List[TranscriptSegment] = []
                        for s in raw_segments:
                            segments.append(
                                TranscriptSegment(
                                    start=round(float(s.get("start", 0.0)), 2),
                                    end=round(float(s.get("end", 0.0)), 2),
                                    text=s.get("text", "").strip(),
                                )
                            )

                        return {
                            "language": parsed.get("language", "en"),
                            "full_text": parsed.get("full_text", "").strip(),
                            "segments": [seg.model_dump() for seg in segments],
                            "provider": "gemini",
                        }

                    err_text = resp.text
                    try:
                        err_json = resp.json()
                        err_detail = err_json.get("error", {}).get("message", err_text)
                    except Exception:
                        err_detail = err_text[:200]
                    last_error = f"Gemini audio transcription failed on {candidate} ({resp.status_code}): {err_detail}"
                    if resp.status_code in (404, 503) and candidate != candidates[-1]:
                        continue
                    raise AppException(
                        code="TRANSCRIPTION_ERROR",
                        message=last_error,
                        status_code=500,
                    )
            except json.JSONDecodeError as e:
                raise AppException(
                    code="TRANSCRIPTION_FORMAT_ERROR",
                    message=f"Gemini output could not be parsed as JSON: {str(e)}",
                    status_code=500,
                )
            except httpx.RequestError as e:
                last_error = f"Network error communicating with Gemini API on {candidate}: {str(e)}"
                if candidate != candidates[-1]:
                    continue
                raise AppException(
                    code="TRANSCRIPTION_NETWORK_ERROR",
                    message=last_error,
                    status_code=500,
                )

        raise AppException(
            code="TRANSCRIPTION_ERROR",
            message=last_error or "All candidate Gemini models failed for transcription.",
            status_code=500,
        )


transcription_service = TranscriptionService()

