"""Reproducción de problema en Qwen3-TTS: genera audio corto y lo analiza."""
import sys
import time

sys.path.insert(0, ".")

import numpy as np
import soundfile as sf

from core.qwen_tts_engine import Qwen3TTSEngine
from core.project import Voice

TEXT = "Hola, esto es una prueba del sistema de voz. Estamos verificando que el audio se genere correctamente, sin cortes ni silencios extraños."

voice = Voice(
    id="clone:homero_referencia:qwen3",
    name="homero_referencia",
    type="cloned",
    engine="qwen3",
    reference_path="voices/clones/homero_referencia.wav",
    language="es",
)

engine = Qwen3TTSEngine(model_name="Qwen/Qwen3-TTS-12Hz-1.7B-Base", device="cuda", language="es")
t0 = time.time()
engine.load()
print(f"[repro] load: {time.time()-t0:.1f}s", flush=True)

t0 = time.time()
out = engine.synthesize(TEXT, voice, "outputs/debug_qwen_repro.wav")
print(f"[repro] synth: {time.time()-t0:.1f}s", flush=True)

audio, sr = sf.read(out)
dur = len(audio) / sr
expected = len(TEXT) * 0.06  # ~16 chars/s de habla
rms = np.sqrt(np.mean(audio ** 2))
thresh = 0.01
silent = float(np.mean(np.abs(audio) < thresh))
print(f"[repro] sr={sr} dur={dur:.2f}s expected~{expected:.2f}s rms={rms:.4f} silent_frac={silent:.2%}", flush=True)

# silencios consecutivos largos
below = np.abs(audio) < thresh
runs, cur = [], 0
for b in below:
    cur = cur + 1 if b else 0
    runs.append(cur)
longest_sil = max(runs) / sr
print(f"[repro] silencio más largo: {longest_sil:.2f}s", flush=True)
