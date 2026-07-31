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
from typing import List, Optional

import numpy as np
import soundfile as sf
import torch

from core.project import Voice
from core.tts_engine import TTSBase
from utils.gpu_utils import clear_gpu_cache

SAMPLE_RATE = 24_000
DEFAULT_MODEL = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"


def _patch_check_model_inputs() -> None:
    """Make qwen-tts 0.1.1 compatible with transformers>=5.

    qwen-tts decorates methods with ``@check_model_inputs()``, but
    transformers>=5 exposes ``check_model_inputs`` as a plain decorator
    (no parentheses). This patch makes the symbol callable both ways.
    """
    try:
        import transformers.utils.generic as _generic
    except Exception:
        return
    _orig = getattr(_generic, "check_model_inputs", None)
    if _orig is None:
        return
    if getattr(_orig, "_qwen_patched", False):
        return

    def _patched(*args, **kwargs):
        if args and callable(args[0]):
            return _orig(args[0])
        return _orig

    _patched._qwen_patched = True
    _generic.check_model_inputs = _patched


def _patch_qwen_configs() -> None:
    """qwen-tts configs do not expose ``pad_token_id`` but transformers>=5
    expects it on config objects. Add a fallback property that returns the
    codec-level / TTS-level pad id."""
    try:
        from qwen_tts.core.models.configuration_qwen3_tts import (
            Qwen3TTSConfig,
            Qwen3TTSTalkerConfig,
        )
    except Exception:
        return

    if not hasattr(Qwen3TTSTalkerConfig, "pad_token_id"):
        Qwen3TTSTalkerConfig.pad_token_id = property(
            lambda self: getattr(self, "codec_pad_id", None)
        )
    if not hasattr(Qwen3TTSConfig, "pad_token_id"):
        Qwen3TTSConfig.pad_token_id = property(
            lambda self: getattr(self, "tts_pad_token_id", None)
        )


def _compute_default_rope_parameters(config, device=None, seq_len=None, layer_type=None):
    """RoPE estándar sin escalado (factor = 1). Compatible con configs qwen-tts
    que usan ``rope_scaling.type == 'default'`` sin campo ``factor``."""
    config.standardize_rope_params()
    rope_parameters_dict = (
        config.rope_parameters[layer_type]
        if layer_type is not None
        else config.rope_parameters
    )
    base = rope_parameters_dict.get("rope_theta", getattr(config, "rope_theta", 10000.0))
    partial_rotary_factor = rope_parameters_dict.get("partial_rotary_factor", 1.0)
    head_dim = getattr(config, "head_dim", None) or config.hidden_size // config.num_attention_heads
    dim = int(head_dim * partial_rotary_factor)
    inv_freq = 1.0 / (
        base
        ** (
            torch.arange(0, dim, 2, dtype=torch.int64).to(device=device, dtype=torch.float)
            / dim
        )
    )
    return inv_freq, 1.0


def _patch_rope_functions() -> None:
    """qwen-tts usa ``rope_scaling.type == 'default'`` pero transformers>=5
    no registra esa clave."""
    try:
        from transformers.modeling_rope_utils import ROPE_INIT_FUNCTIONS

        if "default" not in ROPE_INIT_FUNCTIONS:
            ROPE_INIT_FUNCTIONS["default"] = _compute_default_rope_parameters
    except Exception:
        pass


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
        _patch_check_model_inputs()
        _patch_qwen_configs()
        _patch_rope_functions()

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
        ref_text = self._transcribe_ref(ref_audio) if ref_audio else ""

        language = voice.language or self.language
        # Qwen3-TTS espera nombres de idioma capitalizados: "Spanish", "English"…
        language_qwen = _normalize_language(language)

        wavs, sr = self._model.generate_voice_clone(
            text=text,
            language=language_qwen,
            ref_audio=ref_audio,
            ref_text=ref_text,
        )

        # wavs es una lista (generación individual) → tomar el primer elemento
        audio = wavs[0] if isinstance(wavs, list) else wavs
        _write_wav(audio, sr or SAMPLE_RATE, output_path)
        return output_path

    # ── Helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _transcribe_ref(ref_audio: Optional[str]) -> str:
        """Texto de referencia para mejorar la clonación.

        Si no se dispone de transcripción, devolvemos cadena vacía: el
        modelo cae a modo x_vector_only_mode con menor calidad pero
        funcional.
        """
        return ""

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
    lang = lang.lower().strip()
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