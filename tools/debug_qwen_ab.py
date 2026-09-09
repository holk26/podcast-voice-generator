"""Test A/B: x_vector_only vs ref_text real (transcripción whisper)."""
import sys
import time

sys.path.insert(0, ".")

import numpy as np
import soundfile as sf

from core.qwen_tts_engine import Qwen3TTSEngine

TEXT = "Hola, esto es una prueba del sistema de voz. Estamos verificando que el audio se genere correctamente, sin cortes ni silencios extraños."

engine = Qwen3TTSEngine(model_name="Qwen/Qwen3-TTS-12Hz-1.7B-Base", device="cuda", language="es")
engine.load()

# 1) Transcribir referencia con whisper
t0 = time.time()
import whisper
wmodel = whisper.load_model("base")
ref_audio = "voices/clones/homero_referencia.wav"
res = wmodel.transcribe(ref_audio, language="es")
ref_text = res["text"].strip()
print(f"[ab] whisper '{ref_text}' ({time.time()-t0:.1f}s)", flush=True)
del wmodel

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
    print(f"[ab] {path}: dur={len(audio)/sr:.1f}s segs={len(segments)} pausa_media={np.mean(gaps)*1000:.0f}ms", flush=True)

# 2) A: x_vector_only (actual)
t0 = time.time()
wavs, sr = engine._model.generate_voice_clone(
    text=TEXT, language="Spanish", ref_audio=ref_audio, ref_text="",
    x_vector_only_mode=True, non_streaming_mode=False,
    max_new_tokens=max(256, min(16384, len(TEXT)*2 + 256)),
)
sf.write("outputs/debug_ab_xvector.wav", np.asarray(wavs[0]), sr or 24000)
print(f"[ab] A x_vector_only: {time.time()-t0:.1f}s", flush=True)
analyze("outputs/debug_ab_xvector.wav")

# 3) B: con ref_text
t0 = time.time()
wavs, sr = engine._model.generate_voice_clone(
    text=TEXT, language="Spanish", ref_audio=ref_audio, ref_text=ref_text,
    x_vector_only_mode=False, non_streaming_mode=False,
    max_new_tokens=max(256, min(16384, len(TEXT)*2 + 256)),
)
sf.write("outputs/debug_ab_reftext.wav", np.asarray(wavs[0]), sr or 24000)
print(f"[ab] B ref_text: {time.time()-t0:.1f}s", flush=True)
analyze("outputs/debug_ab_reftext.wav")
