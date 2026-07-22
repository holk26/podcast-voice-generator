"""
Orpheus TTS Engine — high-quality emotional speech synthesis via transformers.

Supports 8 preset voices with inline emotion tags:
  <laugh>, <chuckle>, <sigh>, <cough>, <sniffle>, <groan>, <yawn>, <gasp>

Runs in ~3-4 GB VRAM with 8-bit quantization (RTX 3060+ compatible).
Based on canopylabs/3b-es_it-ft-research_release for Spanish/Italian.
"""

import os
import re
import wave
from typing import List, Optional

import numpy as np
import torch

from core.project import Voice
from core.tts_engine import TTSBase
from utils.gpu_utils import select_best_device, clear_gpu_cache

# Orpheus special token constants
_START_TOKEN = 128259
_END_TOKENS = [128009, 128260, 128261, 128257]
_EOS_TOKEN_ID = 128258
_CUSTOM_TOKEN_RE = re.compile(r"<custom_token_(\d+)>")

# Available voices (finetuned model presets)
ORPHEUS_VOICES = ["tara", "leah", "jess", "leo", "dan", "mia", "zac", "zoe"]

# Default model IDs
# English finetuned (public):  unsloth/orpheus-3b-0.1-ft
# Spanish/Italian finetuned:   canopylabs/3b-es_it-ft-research_release (gated, requires HF token)
DEFAULT_MODEL = "unsloth/orpheus-3b-0.1-ft"
SNAC_MODEL = "hubertsiuzdak/snac_24khz"


class OrpheusEngine(TTSBase):
    """Orpheus TTS engine using HuggingFace transformers + SNAC decoder."""

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        device: str = "auto",
        load_in_8bit: bool = True,
        max_new_tokens: int = 1200,
        temperature: float = 0.6,
        top_p: float = 0.8,
        repetition_penalty: float = 1.3,
    ):
        self.model_name = model_name
        self.device = select_best_device() if device == "auto" else device
        self.load_in_8bit = load_in_8bit and torch.cuda.is_available()
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.repetition_penalty = repetition_penalty

        self._tokenizer = None
        self._model = None
        self._snac = None
        self.name = "orpheus"
        self._loaded = False

    # ── Lifecycle ───────────────────────────────────────────────────────

    def load(self) -> None:
        if self._loaded:
            return

        print("[Orpheus] Loading tokenizer...")
        from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

        self._tokenizer = AutoTokenizer.from_pretrained(
            self.model_name, trust_remote_code=True
        )

        if self.load_in_8bit:
            print("[Orpheus] Loading model in 8-bit quantization...")
            bnb_config = BitsAndBytesConfig(
                load_in_8bit=True,
                llm_int8_threshold=6.0,
                llm_int8_has_fp16_weight=False,
            )
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                quantization_config=bnb_config,
                device_map="auto",
                trust_remote_code=True,
                torch_dtype=torch.float16,
            )
        else:
            print(f"[Orpheus] Loading model on {self.device} (fp16)...")
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16,
                device_map="auto",
                trust_remote_code=True,
            )

        print("[Orpheus] Loading SNAC decoder...")
        from snac import SNAC

        self._snac = SNAC.from_pretrained(SNAC_MODEL).eval().to(self.device)
        self._loaded = True
        print("[Orpheus] Engine ready.")

    def unload(self) -> None:
        self._model = None
        self._tokenizer = None
        self._snac = None
        self._loaded = False
        clear_gpu_cache()
        print("[Orpheus] Unloaded.")

    def is_loaded(self) -> bool:
        return self._loaded

    # ── Voice API ───────────────────────────────────────────────────────

    def get_speakers(self) -> List[str]:
        return list(ORPHEUS_VOICES)

    def clone_voice(self, reference_path: str, name: str) -> str:
        """Orpheus finetuned does NOT support zero-shot cloning.
        Use pretrained mode for conditioning, or fine-tune a LoRA.
        For now, return a prefixed voice ID to signal Orpheus native voice.
        """
        if not os.path.exists(reference_path):
            raise FileNotFoundError(f"Reference audio not found: {reference_path}")
        # Return a synthetic ID; actual voice will map to closest preset
        return f"orpheus_clone_{name}"

    # ── Synthesis ───────────────────────────────────────────────────────

    def synthesize(self, text: str, voice: Voice, output_path: str) -> str:
        if not self._loaded:
            self.load()

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        # Resolve Orpheus voice preset
        orpheus_voice = voice.speaker_id if voice.speaker_id in ORPHEUS_VOICES else "tara"
        if orpheus_voice not in ORPHEUS_VOICES:
            orpheus_voice = "tara"

        audio_bytes = self._generate_audio(text, voice=orpheus_voice)

        # Write WAV 24kHz mono 16-bit
        with wave.open(output_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            wf.writeframes(audio_bytes)

        return output_path

    # ── Internal generation ─────────────────────────────────────────────

    def _format_prompt(self, text: str, voice: str) -> torch.Tensor:
        adapted = f"{voice}: {text}"
        prompt_tokens = self._tokenizer(adapted, return_tensors="pt")
        start = torch.tensor([[_START_TOKEN]], dtype=torch.int64)
        end = torch.tensor([_END_TOKENS], dtype=torch.int64)
        input_ids = torch.cat([start, prompt_tokens.input_ids, end], dim=1)
        return input_ids.to(self._model.device)

    def _generate_audio(self, text: str, voice: str) -> bytes:
        input_ids = self._format_prompt(text, voice)

        with torch.inference_mode():
            outputs = self._model.generate(
                input_ids,
                max_new_tokens=self.max_new_tokens,
                temperature=self.temperature,
                top_p=self.top_p,
                do_sample=True,
                repetition_penalty=self.repetition_penalty,
                pad_token_id=(
                    self._tokenizer.pad_token_id
                    if self._tokenizer.pad_token_id
                    else self._tokenizer.eos_token_id
                ),
            )

        # Extract generated tokens after prompt
        gen_ids = outputs[0][input_ids.shape[1] :]
        tokens_text = self._tokenizer.decode(gen_ids, skip_special_tokens=False)

        # Parse custom tokens and decode with SNAC
        buffer = []
        count = 0
        all_audio = b""

        for match in _CUSTOM_TOKEN_RE.finditer(tokens_text):
            token_val = int(match.group(1)) - 10 - ((count % 7) * 4096)
            if token_val > 0:
                buffer.append(token_val)
                count += 1
                if count % 7 == 0 and count > 27:
                    chunk = self._decode_snac_buffer(buffer[-28:])
                    if chunk:
                        all_audio += chunk

        return all_audio

    def _decode_snac_buffer(self, multiframe: List[int]) -> Optional[bytes]:
        if len(multiframe) < 7:
            return None

        num_frames = len(multiframe) // 7
        frame = multiframe[: num_frames * 7]

        codes_0 = torch.tensor([], device=self.device, dtype=torch.int32)
        codes_1 = torch.tensor([], device=self.device, dtype=torch.int32)
        codes_2 = torch.tensor([], device=self.device, dtype=torch.int32)

        for j in range(num_frames):
            i = 7 * j
            codes_0 = torch.cat(
                [codes_0, torch.tensor([frame[i]], device=self.device, dtype=torch.int32)]
            )
            codes_1 = torch.cat(
                [codes_1, torch.tensor([frame[i + 1], frame[i + 4]], device=self.device, dtype=torch.int32)]
            )
            codes_2 = torch.cat(
                [
                    codes_2,
                    torch.tensor(
                        [frame[i + 2], frame[i + 3], frame[i + 5], frame[i + 6]],
                        device=self.device,
                        dtype=torch.int32,
                    ),
                ]
            )

        codes = [codes_0.unsqueeze(0), codes_1.unsqueeze(0), codes_2.unsqueeze(0)]

        # Validate codebook ranges
        if torch.any(codes[0] < 0) or torch.any(codes[0] > 4096):
            return None
        if torch.any(codes[1] < 0) or torch.any(codes[1] > 4096):
            return None
        if torch.any(codes[2] < 0) or torch.any(codes[2] > 4096):
            return None

        with torch.inference_mode():
            audio_hat = self._snac.decode(codes)

        # SNAC produces padded output; slice the valid center region
        audio_slice = audio_hat[:, :, 2048:4096]
        audio_np = audio_slice.detach().cpu().numpy()
        audio_int16 = (audio_np * 32767).astype(np.int16)
        return audio_int16.tobytes()
