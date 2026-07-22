"""
Higgs Audio v3 TTS Engine — Boson AI's state-of-the-art TTS via vLLM-Omni.

Supports:
  - 100+ languages (including Spanish)
  - Zero-shot voice cloning from reference audio
  - Inline emotion/style/prosody control tokens
  - 24 kHz output

Requirements:
  - vllm-omni installed
  - Model: bosonai/higgs-audio-v3-tts-4b (~9.3 GB safetensors)
  - VRAM: ~18-20 GB in FP16, ~8-10 GB with INT8/FP8 quantization
    On 8 GB VRAM you will likely need quantization or face OOM.

Inline control tokens (insert anywhere in text):
  Emotion:  <|emotion:elation|>, <|emotion:sadness|>, <|emotion:anger|>, ...
  Style:    <|style:whispering|>, <|style:shouting|>, <|style:singing|>
  Prosody:  <|prosody:speed_slow|>, <|prosody:pitch_high|>, <|prosody:pause|>
  SFX:      <|sfx:laughter|>Haha, <|sfx:sigh|>Uh, <|sfx:cough|>Ahem
"""

import os
import re
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
DEFAULT_MODEL = "bosonai/higgs-audio-v3-tts-4b"

# Supported inline control tags (documented; actual support depends on model)
HIGGS_EMOTIONS = [
    "elation", "amusement", "enthusiasm", "determination", "pride",
    "contentment", "affection", "relief", "contemplation", "confusion",
    "surprise", "awe", "longing", "arousal", "anger", "fear", "disgust",
    "bitterness", "sadness", "shame", "helplessness",
]
HIGGS_STYLES = ["singing", "shouting", "whispering"]
HIGGS_SFX = ["cough", "laughter", "crying", "screaming", "burping",
             "humming", "sigh", "sniff", "sneeze"]


class HiggsAudioEngine(TTSBase):
    """Higgs Audio v3 TTS engine using vLLM-Omni."""

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        device: str = "cuda",
        max_new_tokens: int = 2048,
        temperature: float = 0.8,
        top_p: float = 0.95,
        top_k: int = 50,
        gpu_memory_utilization: float = 0.85,
        quantization: Optional[str] = None,  # "fp8", "awq", "gptq", etc.
    ):
        self.model_name = model_name
        self.device = device
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.top_k = top_k
        self.gpu_memory_utilization = gpu_memory_utilization
        self.quantization = quantization

        self._engine = None
        self._tokenizer = None
        self._adapter = None
        self.name = "higgs"
        self._loaded = False

    # ── Lifecycle ───────────────────────────────────────────────────────

    def load(self) -> None:
        if self._loaded:
            return

        print(f"[Higgs] Loading vLLM-Omni engine with {self.model_name}...")
        print("[Higgs] This may take 1-3 minutes on first load...")

        try:
            from vllm_omni import Omni
        except ImportError as e:
            raise ImportError(
                "vllm-omni is required. Install with: pip install vllm-omni"
            ) from e

        # Build engine args; quantization is passed if provided
        engine_kwargs = {
            "model": self.model_name,
            "trust_remote_code": True,
            "gpu_memory_utilization": self.gpu_memory_utilization,
        }
        if self.quantization:
            engine_kwargs["quantization"] = self.quantization

        self._engine = Omni(**engine_kwargs)

        from transformers import AutoTokenizer
        from vllm_omni.model_executor.models.higgs_audio_v3.higgs_audio_v3_tokenizer import (
            HiggsAudioV3TokenizerAdapter,
        )

        self._tokenizer = AutoTokenizer.from_pretrained(
            self.model_name, trust_remote_code=True
        )
        self._adapter = HiggsAudioV3TokenizerAdapter(self._tokenizer)

        self._loaded = True
        print("[Higgs] Engine ready.")

    def unload(self) -> None:
        if self._engine is not None:
            # Omni may not have explicit shutdown; rely on GC
            self._engine = None
        self._tokenizer = None
        self._adapter = None
        self._loaded = False
        clear_gpu_cache()
        print("[Higgs] Unloaded.")

    def is_loaded(self) -> bool:
        return self._loaded

    # ── Voice API ───────────────────────────────────────────────────────

    def get_speakers(self) -> List[str]:
        # Higgs v3 does not use named speakers; it uses reference-audio cloning
        # Return a single synthetic ID for default voice
        return ["higgs_default"]

    def clone_voice(self, reference_path: str, name: str) -> str:
        if not os.path.exists(reference_path):
            raise FileNotFoundError(f"Reference audio not found: {reference_path}")
        return f"higgs_clone_{name}"

    # ── Synthesis ───────────────────────────────────────────────────────

    def synthesize(self, text: str, voice: Voice, output_path: str) -> str:
        if not self._loaded:
            self.load()

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        # Determine if voice cloning is requested
        ref_audio_path = voice.reference_path
        ref_text = ""  # Optional; improves cloning fidelity if provided

        pcm = self._generate_pcm(text, ref_audio_path, ref_text)

        # Write WAV 24kHz mono 16-bit
        with wave.open(output_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(pcm)

        return output_path

    # ── Internal generation ─────────────────────────────────────────────

    def _generate_pcm(
        self, text: str, ref_audio_path: Optional[str], ref_text: str
    ) -> bytes:
        from vllm_omni.model_executor.models.higgs_audio_v3.higgs_audio_v3_tokenizer import (
            encode_reference_audio,
            apply_delay_pattern,
        )

        # Encode reference audio if provided
        ref_codes_delayed = None
        if ref_audio_path and os.path.exists(ref_audio_path):
            ref_wav, ref_sr = sf.read(ref_audio_path, always_2d=False)
            if ref_wav.ndim == 2:
                ref_wav = ref_wav.mean(axis=1)
            ref_codes_raw = encode_reference_audio(ref_wav, int(ref_sr))
            ref_codes_delayed = apply_delay_pattern(ref_codes_raw)

        # Build prompt
        if ref_codes_delayed is not None:
            prompt_ids = self._adapter.build_prompt(
                text,
                num_ref_tokens=int(ref_codes_delayed.shape[0]),
                reference_text=ref_text,
            )
            prompt = {
                "prompt_token_ids": prompt_ids,
                "additional_information": {
                    "audio_input_ids": ref_codes_delayed.to(torch.long),
                    "audio_input_ids_mask": torch.ones(
                        ref_codes_delayed.shape[0], dtype=torch.bool
                    ),
                },
            }
        else:
            prompt_ids = self._adapter.build_prompt(text)
            prompt = {"prompt_token_ids": prompt_ids}

        # Generate
        outputs = self._engine.generate([prompt])

        mm = outputs[0].outputs[0].multimodal_output
        pcm_tensor = self._extract_pcm(mm)
        return self._pcm_to_int16_bytes(pcm_tensor)

    @staticmethod
    def _extract_pcm(multimodal_output: dict) -> torch.Tensor:
        audio = multimodal_output.get("model_outputs")
        if audio is None:
            audio = multimodal_output.get("audio")
        if audio is None:
            raise ValueError(
                f"No audio key in multimodal_output: {list(multimodal_output.keys())}"
            )
        if isinstance(audio, list):
            valid = [
                torch.as_tensor(a).float().cpu().reshape(-1)
                for a in audio
                if a is not None
            ]
            if not valid:
                raise ValueError("Audio list is empty")
            return torch.cat(valid, dim=0) if len(valid) > 1 else valid[0]
        return torch.as_tensor(audio).float().cpu().reshape(-1)

    @staticmethod
    def _pcm_to_int16_bytes(pcm: torch.Tensor) -> bytes:
        arr = pcm.numpy()
        if arr.dtype.kind == "f":
            arr = np.clip(arr, -1.0, 1.0)
            arr = (arr * 32767.0).astype(np.int16)
        else:
            arr = arr.astype(np.int16)
        return arr.tobytes()
