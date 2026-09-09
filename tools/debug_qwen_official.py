"""Stack oficial: qwen-tts 0.1.1 + transformers 4.57.3, SIN parches."""
import sys
import time

sys.path.insert(0, "/tmp/tf457")  # transformers 4.57.3 override
sys.path.insert(0, ".")

import numpy as np
import soundfile as sf
import torch
import transformers

assert transformers.__version__.startswith("4.57"), transformers.__version__
print(f"[off] transformers {transformers.__version__}", flush=True)

from qwen_tts import Qwen3TTSModel

TEXT = "Hola, esto es una prueba del sistema de voz. Estamos verificando que el audio se genere correctamente, sin cortes ni silencios extraños."

t0 = time.time()
model = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
    device_map="cuda",
    dtype=torch.bfloat16,
    attn_implementation="sdpa",
)
print(f"[off] load {time.time()-t0:.1f}s", flush=True)

ref_audio = "voices/clones/homero_referencia.wav"

import whisper
wm = whisper.load_model("base")
ref_text = wm.transcribe(ref_audio, language="es")["text"].strip()
del wm
print(f"[off] ref_text: {ref_text!r}", flush=True)

for i in range(2):
    t0 = time.time()
    wavs, sr = model.generate_voice_clone(
        text=TEXT, language="Spanish", ref_audio=ref_audio, ref_text=ref_text,
        x_vector_only_mode=False, non_streaming_mode=False,
        max_new_tokens=2048,
    )
    dur = len(np.asarray(wavs[0])) / (sr or 24000)
    print(f"[off] run{i}: gen={time.time()-t0:.1f}s dur={dur:.1f}s {'OK' if dur < len(TEXT)*0.09 else 'DEGENERA'}", flush=True)
    sf.write(f"outputs/debug_off_{i}.wav", np.asarray(wavs[0]), sr or 24000)
