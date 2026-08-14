import json
import os
import urllib.request
from pathlib import Path
from typing import List

import numpy as np
import soundfile as sf

from processors.dialogue_parser import DialogueSegment
from backend.app.routes.tts import _find_voice
from backend.app.routes.voices import VoiceResponse

API_BASE = f"http://localhost:{os.getenv('API_PORT', '8000')}"


def _synth_segment(text: str, voice: VoiceResponse, output: Path) -> Path:
    req = urllib.request.Request(
        f"{API_BASE}/api/tts/synthesize",
        data=json.dumps({
            "voice_id": voice.id,
            "text": text,
            "label": f"{voice.name}: {text[:60]}...",
        }).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=3600) as resp:
        audio_url = json.load(resp)["audio_url"]
    with urllib.request.urlopen(f"{API_BASE}{audio_url}", timeout=300) as resp:
        output.write_bytes(resp.read())
    return output


def _read_mono_24k(path: Path) -> tuple[np.ndarray, int]:
    data, sr = sf.read(str(path), always_2d=False)
    if data.ndim == 2:
        data = data.mean(axis=1)
    return data.astype(np.float32), sr


def mix_dialogue(segments: List[DialogueSegment], output: Path, voice_map: dict[str, str]) -> Path:
    """Synthesize each segment with its mapped voice and concatenate."""
    parts: List[np.ndarray] = []
    rate = 24000
    for i, seg in enumerate(segments):
        voice_id = voice_map.get(seg.speaker)
        if not voice_id:
            raise ValueError(f"No voice mapped for speaker {seg.speaker}")
        voice = _find_voice(voice_id)
        if not voice:
            raise ValueError(f"Voice not found: {voice_id}")
        part_path = output.with_suffix(f".{i}.wav")
        _synth_segment(seg.text, voice, part_path)
        data, sr = _read_mono_24k(part_path)
        rate = sr
        parts.append(data)
        part_path.unlink(missing_ok=True)

    output.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(output), np.concatenate(parts), rate, format="WAV", subtype="PCM_16")
    return output
