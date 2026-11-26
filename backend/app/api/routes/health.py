from fastapi import APIRouter
from app.core.config import settings
from app.services.file_processing.media_extractor import is_ffmpeg_available

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    return {"status": "ok"}


@router.get("/health/runtime")
async def runtime_health_check():
    """Verify non-secret runtime readiness (FFmpeg and provider configuration) for deployed environments."""
    provider = (settings.AI_PROVIDER or "openai").lower().strip()
    ai_configured = bool(settings.GEMINI_API_KEY) if provider == "gemini" else bool(settings.OPENAI_API_KEY)
    supabase_configured = bool(
        settings.SUPABASE_URL
        and settings.SUPABASE_ANON_KEY
        and settings.SUPABASE_SERVICE_ROLE_KEY
    )
    return {
        "status": "ok",
        "ffmpeg_available": is_ffmpeg_available(),
        "ai_provider": provider,
        "ai_configured": ai_configured,
        "supabase_configured": supabase_configured,
    }
