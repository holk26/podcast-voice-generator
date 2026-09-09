"""
Qwen3-TTS 12Hz 1.7B Base — motor de clonación de voz (3 s de referencia).

Modelo: Qwen/Qwen3-TTS-12Hz-1.7B-Base (Apache 2.0)
Idiomas: zh, en, ja, ko, de, fr, ru, pt, es, it
VRAM: ~4 GB en bfloat16 (~1.7B params)
Salida: 24 kHz mono

Requiere el paquete `qwen-tts` (ver docs/QWEN3_TTS_SETUP.md).
"""

import os
import wave
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import soundfile as sf
import torch

from core.project import Voice
from core.tts_engine import TTSBase
from utils.gpu_utils import clear_gpu_cache

SAMPLE_RATE = 24_000
DEFAULT_MODEL = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"


def _free_ollama_vram() -> None:
    """Descarga los modelos de Ollama de la GPU antes de cargar Qwen3-TTS."""
    import json
    import urllib.request

    base = os.getenv("OLLAMA_URL", "http://localhost:11434")
    try:
        with urllib.request.urlopen(f"{base}/api/ps", timeout=3) as resp:
            models = [m["name"] for m in json.load(resp).get("models", [])]
        for name in models:
            req = urllib.request.Request(
                f"{base}/api/generate",
                data=json.dumps({"model": name, "keep_alive": 0}).encode(),
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req, timeout=15).read()
        if models:
            print(f"[Qwen3-TTS] Modelos de Ollama descargados de VRAM: {models}")
    except Exception:
        pass


class Qwen3TTSEngine(TTSBase):
    """Motor de clonación de voz basado en Qwen3-TTS-12Hz-1.7B-Base."""

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        device: str = "cuda",
        dtype: Optional[str] = None,
        attn_implementation: str = "sdpa",
        language: str = "es",
    ):
        self.model_name = model_name
        self.device = device
        # Si dtype es None, dejamos que el paquete elija (bfloat16 por defecto)
        self.dtype = dtype
        self.attn_implementation = attn_implementation
        self.language = language

        self._model = None
        self.name = "qwen3"
        self._loaded = False

    # ── Lifecycle ───────────────────────────────────────────────────────

    def load(self) -> None:
        if self._loaded:
            return

        _free_ollama_vram()

        try:
            from qwen_tts import Qwen3TTSModel
        except ImportError as e:
            raise ImportError(
                "qwen-tts no está instalado. Instala con: pip install qwen-tts "
                "(ver docs/QWEN3_TTS_SETUP.md)"
            ) from e

        print(f"[Qwen3-TTS] Loading {self.model_name}...")
        print("[Qwen3-TTS] Esto puede tardar 1-3 minutos la primera vez (descarga)…")

        kwargs = {
            "device_map": self.device,
        }
        if self.dtype:
            dtype_map = {
                "bfloat16": torch.bfloat16,
                "float16": torch.float16,
                "float32": torch.float32,
            }
            kwargs["dtype"] = dtype_map.get(self.dtype, torch.bfloat16)
        else:
            kwargs["dtype"] = torch.bfloat16

        kwargs["attn_implementation"] = self.attn_implementation

        self._model = Qwen3TTSModel.from_pretrained(self.model_name, **kwargs)
        self._loaded = True
        print("[Qwen3-TTS] Engine listo.")

    def unload(self) -> None:
        if self._model is not None:
            del self._model
            self._model = None
        self._loaded = False
        clear_gpu_cache()
        print("[Qwen3-TTS] Descargado.")

    def is_loaded(self) -> bool:
        return self._loaded

    # ── Voice API ───────────────────────────────────────────────────────

    def get_speakers(self) -> List[str]:
        # El modelo Base usa clonación de voz; no tiene speakers predefinidos.
        return ["qwen3_clone"]

    def clone_voice(self, reference_path: str, name: str) -> str:
        if not os.path.exists(reference_path):
            raise FileNotFoundError(f"Reference audio not found: {reference_path}")
        return f"qwen3_clone_{name}"

    # ── Synthesis ───────────────────────────────────────────────────────

    def synthesize(self, text: str, voice: Voice, output_path: str) -> str:
        if not self._loaded:
            self.load()

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        ref_audio = voice.reference_path
        language = voice.language or self.language
        ref_text = self._transcribe_ref(ref_audio, language)

        # Qwen3-TTS espera nombres de idioma capitalizados: "Spanish", "English"…
        language_qwen = _normalize_language(language)

        # Estimación de tokens de audio necesarios: ~2 tokens por carácter de
        # texto da margen para ritmos de habla variados. Cap en 16384 para
        # evitar OOM en episodios largos (≈21 min de audio a 12.5 token/s).
        estimated_tokens = max(256, min(16384, len(text) * 2 + 256))

        wavs, sr = self._model.generate_voice_clone(
            text=text,
            language=language_qwen,
            ref_audio=ref_audio,
            ref_text=ref_text,
            x_vector_only_mode=not ref_text,
            # El modo no-streaming produce audio muy largo (no alcanza el token
            # de fin de habla); el modo streaming (simulado) sí detiene la
            # generación en el EOS de codec.
            non_streaming_mode=False,
            max_new_tokens=estimated_tokens,
        )

        # wavs es una lista (generación individual) → tomar el primer elemento
        audio = wavs[0] if isinstance(wavs, list) else wavs
        _write_wav(audio, sr or SAMPLE_RATE, output_path)
        return output_path

    # ── Helpers ─────────────────────────────────────────────────────────

    _whisper_model = None
    _ref_text_cache: Dict[str, str] = {}

    @classmethod
    def _transcribe_ref(cls, ref_audio: Optional[str], language: str = "es") -> str:
        """Texto de referencia para mejorar la clonación.

        El modo ``x_vector_only_mode`` (sin ref_text) degrada la prosodia:
        habla estacada con pausas entre sílabas y audio 2-4x más largo. La
        transcripción con whisper mejora notablemente el ritmo. Si whisper
        no está disponible o falla, devolvemos cadena vacía y el modelo cae
        al modo x_vector (menor calidad pero funcional).
        """
        if not ref_audio or not os.path.exists(ref_audio):
            return ""

        cached = cls._ref_text_cache.get(ref_audio)
        if cached is not None:
            return cached

        try:
            import whisper
        except ImportError:
            print("[Qwen3-TTS] whisper no instalado; clonación en modo x_vector_only.")
            return ""

        try:
            if cls._whisper_model is None:
                model_name = os.getenv("QWEN3_TTS_WHISPER_MODEL", "base")
                cls._whisper_model = whisper.load_model(model_name)
            lang = (language or "es").split("-")[0]
            result = cls._whisper_model.transcribe(ref_audio, language=lang)
            text = (result.get("text") or "").strip()
        except Exception as e:
            print(f"[Qwen3-TTS] Transcripción de referencia falló ({e}); modo x_vector_only.")
            return ""

        cls._ref_text_cache[ref_audio] = text
        return text

    def create_clone_prompt(self, ref_audio, ref_text: str = ""):
        """Construye un prompt reutilizable para múltiples síntesis con la
        misma voz de referencia (evita recalcular features)."""
        if not self._loaded:
            self.load()
        return self._model.create_voice_clone_prompt(
            ref_audio=ref_audio,
            ref_text=ref_text,
            x_vector_only_mode=not ref_text,
        )


# ── Utilidades de formato ───────────────────────────────────────────────

_LANGUAGE_MAP = {
    "es": "Spanish",
    "en": "English",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "de": "German",
    "fr": "French",
    "ru": "Russian",
    "pt": "Portuguese",
    "it": "Italian",
}


def _normalize_language(lang: str) -> str:
    if not lang:
        return "Spanish"
    # Acepta subtags regionales: "es-ES" → "es", "pt-BR" → "pt"
    lang = lang.lower().strip().split("-")[0]
    return _LANGUAGE_MAP.get(lang, lang.capitalize())


def _write_wav(audio: np.ndarray, sr: int, path: str) -> None:
    """Escribe un array numpy a WAV mono 16-bit."""
    arr = np.asarray(audio, dtype=np.float32).reshape(-1)
    # Normalizar si excede [-1, 1] (defensivo)
    peak = float(np.max(np.abs(arr))) or 1.0
    if peak > 1.0:
        arr = arr / peak
    int16 = np.clip(arr, -1.0, 1.0)
    int16 = (int16 * 32767.0).astype(np.int16)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(int(sr))
        wf.writeframes(int16.tobytes())