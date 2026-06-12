import uuid
import edge_tts
from pathlib import Path
from fastapi import APIRouter
from web_api.schemas import PreviewRequest, PreviewResponse
from web_api.config import PREVIEW_DIR

router = APIRouter()

VOICE_MAP = {
    "jorge": "es-ES-AlvaroNeural",
    "dalia": "es-ES-ElviraNeural",
    "elvira": "es-ES-ElviraNeural",
}

DEFAULT_VOICE = "es-ES-AlvaroNeural"


@router.post("/preview", response_model=PreviewResponse)
async def preview(request: PreviewRequest):
    filename = f"{uuid.uuid4().hex}.mp3"
    output_path = PREVIEW_DIR / filename
    voice = VOICE_MAP.get(request.voice_id, DEFAULT_VOICE)
    communicate = edge_tts.Communicate(request.text, voice=voice)
    await communicate.save(str(output_path))
    return PreviewResponse(audio_url=f"/outputs/previews/{filename}")
