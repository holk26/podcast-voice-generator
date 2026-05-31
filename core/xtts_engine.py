import os
from typing import List
from core.tts_engine import TTSBase
from core.project import Voice
from utils.gpu_utils import select_best_device, clear_gpu_cache

try:
    import torch
except ImportError:
    torch = None  # type: ignore

try:
    from TTS.api import TTS
except ImportError:
    TTS = None  # type: ignore


class XTTSEngine(TTSBase):
    def __init__(self, model_name: str = "tts_models/multilingual/multi-dataset/xtts_v2", device: str = "auto"):
        self.model_name = model_name
        self.device = device if device != "auto" else select_best_device()
        self._model = None
        self.name = "xtts"
        self._speakers = []

    def load(self) -> None:
        if self._model is not None:
            return
        self._model = TTS(self.model_name).to(self.device)
        if hasattr(self._model, "speakers") and self._model.speakers:
            self._speakers = list(self._model.speakers)

    def unload(self) -> None:
        self._model = None
        clear_gpu_cache()

    def is_loaded(self) -> bool:
        return self._model is not None

    def get_speakers(self) -> List[str]:
        if not self.is_loaded():
            return []
        return self._speakers

    def synthesize(self, text: str, voice: Voice, output_path: str) -> str:
        if not self.is_loaded():
            self.load()
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        if voice.type == "cloned" and voice.reference_path:
            self._model.tts_to_file(
                text=text,
                speaker_wav=voice.reference_path,
                language=voice.language,
                file_path=output_path,
                speed=voice.speed
            )
        else:
            speaker = voice.speaker_id if voice.speaker_id else (self._speakers[0] if self._speakers else None)
            self._model.tts_to_file(
                text=text,
                speaker=speaker,
                language=voice.language,
                file_path=output_path,
                speed=voice.speed
            )
        return output_path

    def clone_voice(self, reference_path: str, name: str) -> str:
        """XTTS cloning is done on-the-fly via reference_path during synthesis.
        This method validates the reference and returns a voice identifier."""
        if not os.path.exists(reference_path):
            raise FileNotFoundError(f"Reference audio not found: {reference_path}")
        return f"xtts_clone_{name}"
