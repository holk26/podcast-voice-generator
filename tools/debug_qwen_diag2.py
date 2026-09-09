"""Instrumentación nivel talker: ¿llegan eos/suppress? ¿para la generación?"""
import sys
import time

sys.path.insert(0, ".")

import numpy as np
import soundfile as sf

from core.qwen_tts_engine import Qwen3TTSEngine

TEXT = "Hola, esto es una prueba del sistema de voz."

engine = Qwen3TTSEngine(model_name="Qwen/Qwen3-TTS-12Hz-1.7B-Base", device="cuda", language="es")
engine.load()

import torch
import qwen_tts.core.models.modeling_qwen3_tts as qm

m = engine._model.model
eos_id = m.config.talker_config.codec_eos_token_id
vocab = m.config.talker_config.vocab_size
print(f"[diag2] codec_eos={eos_id} vocab={vocab} suppress range=[{vocab-1024},{vocab})", flush=True)

ref_audio = "voices/clones/homero_referencia.wav"
ref_text = engine._transcribe_ref(ref_audio, "es")

talker_cls = qm.Qwen3TTSTalkerForConditionalGeneration
orig_talker_generate = talker_cls.generate

def wrapped_talker_generate(self, *args, **kwargs):
    print(f"[diag2] talker.generate: max_new={kwargs.get('max_new_tokens')} min_new={kwargs.get('min_new_tokens')} eos={kwargs.get('eos_token_id')} suppress_n={len(kwargs.get('suppress_tokens') or [])} do_sample={kwargs.get('do_sample')}", flush=True)
    out = orig_talker_generate(self, *args, **kwargs)
    seqs = out.sequences if hasattr(out, 'sequences') else out
    if isinstance(seqs, torch.Tensor):
        for i in range(seqs.shape[0]):
            row = seqs[i]
            hits = (row == kwargs.get('eos_token_id')).nonzero().flatten().tolist()
            print(f"[diag2] seq[{i}] len={row.shape[0]} new_tokens={row.shape[0]-1} eos_hits={hits[:5]}", flush=True)
            print(f"[diag2] últimos 15 tokens: {row[-15:].tolist()}", flush=True)
    return out

talker_cls.generate = wrapped_talker_generate

t0 = time.time()
wavs, sr = engine._model.generate_voice_clone(
    text=TEXT, language="Spanish", ref_audio=ref_audio, ref_text=ref_text,
    x_vector_only_mode=False, non_streaming_mode=False,
    max_new_tokens=300,
)
print(f"[diag2] gen {time.time()-t0:.1f}s, out dur={len(np.asarray(wavs[0]))/(sr or 24000):.1f}s", flush=True)
