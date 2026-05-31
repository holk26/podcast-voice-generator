import os
from typing import List
from core.tts_engine import TTSBase
from core.project import Voice
from utils.gpu_utils import select_best_device, clear_gpu_cache


class BarkEngine(TTSBase):
    HISTORY_PROMPTS = [
        "v2/en_speaker_0", "v2/en_speaker_1", "v2/en_speaker_2", "v2/en_speaker_3",
        "v2/en_speaker_4", "v2/en_speaker_5", "v2/en_speaker_6", "v2/en_speaker_7",
        "v2/en_speaker_8", "v2/en_speaker_9",
        "v2/es_speaker_0", "v2/es_speaker_1", "v2/es_speaker_2", "v2/es_speaker_3",
        "v2/es_speaker_4", "v2/es_speaker_5", "v2/es_speaker_6", "v2/es_speaker_7",
        "v2/es_speaker_8", "v2/es_speaker_9",
    ]

    def __init__(self, device: str = "auto", model_size: str = "small"):
        self.device = device if device != "auto" else select_best_device()
        self.model_size = model_size
        self.name = "bark"
        self._model = None
        self._processor = None

    def load(self) -> None:
        if self.is_loaded():
            return
        try:
            from transformers import AutoProcessor, BarkModel
            model_name = f"suno/bark-{self.model_size}"
            self._processor = AutoProcessor.from_pretrained(model_name)
            self._model = BarkModel.from_pretrained(model_name)
            self._model = self._model.to(self.device)
        except ImportError:
            raise ImportError("Bark requires 'transformers' and 'accelerate'. Install: pip install transformers accelerate")

    def unload(self) -> None:
        self._model = None
        self._processor = None
        clear_gpu_cache()

    def is_loaded(self) -> bool:
        return self._model is not None

    def get_speakers(self) -> List[str]:
        return self.HISTORY_PROMPTS

    def synthesize(self, text: str, voice: Voice, output_path: str) -> str:
        if not self.is_loaded():
            self.load()
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        speaker = voice.speaker_id if voice.speaker_id else self.HISTORY_PROMPTS[0]
        inputs = self._processor(text, voice_preset=speaker)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        import torch
        with torch.no_grad():
            audio_array = self._model.generate(**inputs)
            audio_array = audio_array.cpu().numpy().squeeze()
        import scipy.io.wavfile as wavfile
        wavfile.write(output_path, rate=self._model.generation_config.sample_rate, data=audio_array)
        return output_path

    def clone_voice(self, reference_path: str, name: str) -> str:
        raise NotImplementedError("Bark voice cloning is limited. Use XTTS for voice cloning.")
