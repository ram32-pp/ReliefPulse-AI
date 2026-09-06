from app.ai.gemini_client import gemini_client
import httpx
from pathlib import Path
from typing import Dict, Any, Optional

async def extract_emergency_data(
    text: Optional[str] = None,
    audio_url: Optional[str] = None,
    audio_bytes: Optional[bytes] = None,
    audio_mime_type: str = "audio/webm",
    image_bytes: Optional[bytes] = None,
    image_mime_type: str = "image/jpeg",
    video_bytes: Optional[bytes] = None,
    video_mime_type: str = "video/mp4",
    location_context: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Multimodal Linguistic & Extraction Engine entry point.
    Processes unstructured voice, text, and visual inputs natively via GeminiClient.
    """
    if audio_bytes is None and audio_url:
        if audio_url.startswith("http://") or audio_url.startswith("https://"):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(audio_url)
                    if response.status_code == 200:
                        audio_bytes = response.content
            except Exception:
                pass
        elif audio_url.startswith("/uploads/"):
            # Local file path
            rel_path = audio_url.lstrip("/")
            if Path(rel_path).exists():
                try:
                    audio_bytes = Path(rel_path).read_bytes()
                except Exception:
                    pass

    return await gemini_client.process_report(
        text_input=text,
        audio_bytes=audio_bytes,
        audio_mime_type=audio_mime_type,
        image_bytes=image_bytes,
        image_mime_type=image_mime_type,
        video_bytes=video_bytes,
        video_mime_type=video_mime_type,
        location_context=location_context,
    )

