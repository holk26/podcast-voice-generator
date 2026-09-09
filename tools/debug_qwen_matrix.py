"""Matriz de pruebas: modo streaming vs no-streaming, sampling vs greedy."""
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

def run(tag, **extra):
    kw = dict(
        text=TEXT, language="Spanish", ref_audio=ref_audio, ref_text=ref_text,
        x_vector_only_mode=False, non_streaming_mode=False,
        max_new_tokens=1024,
    )
    kw.update(extra)
    t0 = time.time()
    wavs, sr = engine._model.generate_voice_clone(**kw)
    dur = len(np.asarray(wavs[0])) / (sr or 24000)
    print(f"[m] {tag}: gen={time.time()-t0:.1f}s dur={dur:.1f}s {'OK' if dur < len(TEXT)*0.09 else 'DEGENERA'}", flush=True)
    sf.write(f"outputs/debug_m_{tag}.wav", np.asarray(wavs[0]), sr or 24000)

run("stream_t09", temperature=0.9, top_p=1.0)
run("nostream_t09", non_streaming_mode=True, temperature=0.9, top_p=1.0)
run("stream_greedy", do_sample=False, temperature=None, top_p=None, top_k=None)
