import uuid
import edge_tts
from pathlib import Path
from fastapi import APIRouter, HTTPException
from web_api.schemas import PreviewRequest, PreviewResponse
from web_api.config import PREVIEW_DIR
from web_api.routes.voices import list_voices, VoiceResponse

router = APIRouter()

VOICE_MAP = {
    "jorge": "es-ES-AlvaroNeural",
    "dalia": "es-ES-ElviraNeural",
    "elvira": "es-ES-ElviraNeural",
}

DEFAULT_VOICE = "es-ES-AlvaroNeural"

_xtts_engine = None


def _get_xtts_engine():
    global _xtts_engine
    if _xtts_engine is None:
        from core.xtts_engine import XTTSEngine
        from core.project import Voice
        _xtts_engine = XTTSEngine()
    return _xtts_engine


def _find_voice(voice_id: str) -> VoiceResponse | None:
    for v in list_voices():
        if v.id == voice_id:
            return v
    return None


@router.post("/preview", response_model=PreviewResponse)
async def preview(request: PreviewRequest):
    filename = f"{uuid.uuid4().hex}.mp3"
    output_path = PREVIEW_DIR / filename
    voice = _find_voice(request.voice_id)

    if voice is not None and voice.type == "cloned" and voice.reference_path:
        try:
            from core.project import Voice as CoreVoice
            core_voice = CoreVoice(
                id=voice.id,
                name=voice.name,
                type="cloned",
                engine="xtts",
                language=voice.language,
                reference_path=voice.reference_path,
            )
            engine = _get_xtts_engine()
            wav_path = output_path.with_suffix(".wav")
            engine.synthesize(request.text, core_voice, str(wav_path))
            return PreviewResponse(audio_url=f"/outputs/previews/{wav_path.name}")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            raise HTTPException(status_code=500, detail=f"XTTS preview failed: {e}\n{tb}")

    edge_voice = VOICE_MAP.get(request.voice_id, DEFAULT_VOICE)
    communicate = edge_tts.Communicate(request.text, voice=edge_voice)
    await communicate.save(str(output_path))
    return PreviewResponse(audio_url=f"/outputs/previews/{filename}")
