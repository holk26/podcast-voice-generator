"""Prueba SIN los parches del motor, directo con qwen-tts-hf."""
import sys
import time

sys.path.insert(0, "/tmp/qwenhf")
sys.path.insert(0, ".")

import numpy as np
import soundfile as sf

from qwen_tts import Qwen3TTSModel

TEXT = "Hola, esto es una prueba del sistema de voz. Estamos verificando que el audio se genere correctamente, sin cortes ni silencios extraños."

t0 = time.time()
model = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
    device_map="cuda",
    dtype=np.bfloat16 if hasattr(np, "bfloat16") else "bfloat16",
    attn_implementation="sdpa",
)
print(f"[raw] load {time.time()-t0:.1f}s", flush=True)

ref_audio = "voices/clones/homero_referencia.wav"

import whisper
wm = whisper.load_model("base")
ref_text = wm.transcribe(ref_audio, language="es")["text"].strip()
del wm
print(f"[raw] ref_text: {ref_text!r}", flush=True)

t0 = time.time()
wavs, sr = model.generate_voice_clone(
    text=TEXT, language="Spanish", ref_audio=ref_audio, ref_text=ref_text,
    x_vector_only_mode=False, non_streaming_mode=False,
    max_new_tokens=2048,
)
dur = len(np.asarray(wavs[0]))/(sr or 24000)
print(f"[raw] gen {time.time()-t0:.1f}s dur={dur:.1f}s", flush=True)
sf.write("outputs/debug_raw_hf.wav", np.asarray(wavs[0]), sr or 24000)
