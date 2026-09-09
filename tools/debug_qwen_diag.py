"""Instrumentación: ¿se genera el codec EOS? ¿dónde corta?"""
import sys
import time

sys.path.insert(0, ".")

import numpy as np
import soundfile as sf
import torch

from core.qwen_tts_engine import Qwen3TTSEngine

TEXT = "Hola, esto es una prueba del sistema de voz."

engine = Qwen3TTSEngine(model_name="Qwen/Qwen3-TTS-12Hz-1.7B-Base", device="cuda", language="es")
engine.load()

m = engine._model.model  # Qwen3TTSForConditionalGeneration
eos_id = m.config.talker_config.codec_eos_token_id
print(f"[diag] codec_eos_token_id = {eos_id}", flush=True)

ref_audio = "voices/clones/homero_referencia.wav"
ref_text = engine._transcribe_ref(ref_audio, "es")

orig_generate = m.generate

def wrapped_generate(*args, **kwargs):
    print(f"[diag] generate kwargs: max_new={kwargs.get('max_new_tokens')}, eos={kwargs.get('eos_token_id')}, temp={kwargs.get('temperature')}, suppress_n={len(kwargs.get('suppress_tokens') or [])}", flush=True)
    codes_list, hiddens = orig_generate(*args, **kwargs)
    for i, codes in enumerate(codes_list):
        first = codes[:, 0] if codes.dim() == 2 else codes
        eos_hits = (first == eos_id).nonzero().flatten().tolist()
        print(f"[diag] codes[{i}] shape={tuple(codes.shape)} eos_hits={eos_hits[:5]}", flush=True)
    return codes_list, hiddens

m.generate = wrapped_generate

t0 = time.time()
wavs, sr = engine._model.generate_voice_clone(
    text=TEXT, language="Spanish", ref_audio=ref_audio, ref_text=ref_text,
    x_vector_only_mode=False, non_streaming_mode=False,
    max_new_tokens=1024,
)
print(f"[diag] gen {time.time()-t0:.1f}s, out dur={len(np.asarray(wavs[0]))/(sr or 24000):.1f}s", flush=True)
sf.write("outputs/debug_diag.wav", np.asarray(wavs[0]), sr or 24000)
