import os
from typing import List
from core.tts_engine import TTSBase
from core.project import Voice
from utils.gpu_utils import select_best_device, clear_gpu_cache, is_gpu_architecture_compatible

try:
    import torch
except ImportError:
    torch = None  # type: ignore

try:
    from TTS.api import TTS
except ImportError:
    TTS = None  # type: ignore


def _apply_torch_compat_patches():
    """Apply PyTorch compatibility patches for TTS models.
    - Fixes torch.load weights_only issue in PyTorch 2.6+"""
    if torch is None:
        return
    # Patch torch.load to disable weights_only default (PyTorch 2.6+ breaks TTS checkpoints)
    _original_load = torch.load
    def _patched_load(*args, **kwargs):
        if "weights_only" not in kwargs:
            kwargs["weights_only"] = False
        return _original_load(*args, **kwargs)
    torch.load = _patched_load


class XTTSEngine(TTSBase):
    def __init__(self, model_name: str = "tts_models/multilingual/multi-dataset/xtts_v2", device: str = "auto"):
        self.model_name = model_name
        if device == "auto":
            # Check GPU compatibility - RTX 50-series needs PyTorch 2.7+
            compatible, reason = is_gpu_architecture_compatible()
            if not compatible:
                print(f"[XTTS] {reason}")
                print("[XTTS] Using CPU fallback for stability")
                self.device = "cpu"
            else:
                self.device = select_best_device()
        else:
            self.device = device
        self._model = None
        self.name = "xtts"
        self._speakers = []

    def load(self) -> None:
        if self._model is not None:
            return
        _apply_torch_compat_patches()
        self._model = TTS(self.model_name, gpu=self.device.startswith("cuda"))
        if self.device.startswith("cuda"):
            self._model = self._model.to(self.device)
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
