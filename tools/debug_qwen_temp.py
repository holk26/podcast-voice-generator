"""Test de estabilidad: temperature alta vs baja con ref_text."""
import sys
import time

sys.path.insert(0, ".")

import numpy as np
import soundfile as sf

from core.qwen_tts_engine import Qwen3TTSEngine

TEXT = "Hola, esto es una prueba del sistema de voz. Estamos verificando que el audio se genere correctamente, sin cortes ni silencios extraños."

engine = Qwen3TTSEngine(model_name="Qwen/Qwen3-TTS-12Hz-1.7B-Base", device="cuda", language="es")
engine.load()

ref_audio = "voices/clones/homero_referencia.wav"
ref_text = engine._transcribe_ref(ref_audio, "es")
print(f"[temp] ref_text: '{ref_text}'", flush=True)

def analyze(path):
    audio, sr = sf.read(path)
    hop = 240
    n = len(audio)//hop
    env = np.array([np.sqrt(np.mean(audio[i*hop:(i+1)*hop]**2)) for i in range(n)])
    thresh = max(0.015, env.max()*0.1)
    voiced = env > thresh
    segments, start = [], None
    for i, v in enumerate(voiced):
        if v and start is None: start = i
        elif not v and start is not None:
            if (i-start)*hop/sr > 0.08: segments.append((start*hop/sr, i*hop/sr))
            start = None
    if start is not None: segments.append((start*hop/sr, n*hop/sr))
    gaps = [segments[i+1][0]-segments[i][1] for i in range(len(segments)-1)]
    pausa = np.mean(gaps)*1000 if gaps else 0
    print(f"[temp] {path}: dur={len(audio)/sr:.1f}s segs={len(segments)} pausa_media={pausa:.0f}ms", flush=True)

for tag, kw in [
    ("t0.9", dict(temperature=0.9, top_p=1.0)),
    ("t0.5", dict(temperature=0.5, top_p=0.9)),
    ("t0.3", dict(temperature=0.3, top_p=0.9)),
    ("t0.1", dict(temperature=0.1, top_p=0.9)),
]:
    t0 = time.time()
    wavs, sr = engine._model.generate_voice_clone(
        text=TEXT, language="Spanish", ref_audio=ref_audio, ref_text=ref_text,
        x_vector_only_mode=False, non_streaming_mode=False,
        max_new_tokens=max(256, min(16384, len(TEXT)*2 + 256)),
        **kw,
    )
    path = f"outputs/debug_temp_{tag}.wav"
    sf.write(path, np.asarray(wavs[0]), sr or 24000)
    print(f"[temp] {tag}: gen {time.time()-t0:.1f}s", flush=True)
    analyze(path)
