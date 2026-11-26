import os
import shutil
import subprocess
from pathlib import Path
from app.core.errors import AppException


def is_ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def extract_audio_from_video(video_path: Path, output_audio_path: Path) -> Path:
    """
    Extracts audio track from an MP4 video file using FFmpeg.
    Video is an audio source only in MVP (no computer vision / pose tracking).
    """
    if not is_ffmpeg_available():
        raise AppException(
            code="FFMPEG_NOT_FOUND",
            message=(
                "FFmpeg is not installed or not in system PATH. "
                "For MVP, please upload audio files directly (MP3, WAV, M4A) or install FFmpeg."
            ),
            status_code=400,
        )

    output_audio_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",               # Overwrite output
        "-i", str(video_path),
        "-vn",              # Disable video recording
        "-acodec", "libmp3lame",
        "-q:a", "2",        # High quality VBR audio
        str(output_audio_path),
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        return output_audio_path
    except subprocess.CalledProcessError as e:
        err_msg = e.stderr.decode("utf-8", errors="ignore")
        raise AppException(
            code="MEDIA_EXTRACTION_ERROR",
            message=f"Failed to extract audio track from video: {err_msg[:300]}",
            status_code=400,
        )


def extract_audio_bytes_from_video(video_bytes: bytes) -> bytes:
    """Extract audio track from in-memory MP4 video bytes into MP3 bytes."""
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as in_f:
        in_f.write(video_bytes)
        in_path = Path(in_f.name)
    out_path = in_path.with_suffix(".mp3")
    try:
        extract_audio_from_video(in_path, out_path)
        return out_path.read_bytes()
    finally:
        if in_path.exists():
            in_path.unlink()
        if out_path.exists():
            out_path.unlink()

