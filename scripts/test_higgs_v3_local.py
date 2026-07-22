#!/usr/bin/env python3
"""
Script de prueba para Higgs Audio v3 TTS 4B usando modelo local.
Adaptado para GPUs con VRAM limitada (~8 GB).
"""
import os
import sys
import time
from pathlib import Path

# Reducir logs de vLLM
os.environ["VLLM_LOGGING_LEVEL"] = "WARNING"
os.environ["VLLM_USE_DEEP_GEMM"] = "0"
os.environ["VLLM_MOE_USE_DEEP_GEMM"] = "0"

import numpy as np
import soundfile as sf
import torch

from vllm_omni import Omni

SAMPLE_RATE = 24_000
MODEL_PATH = "models/higgs-audio-v3-tts-4b"
OUTPUT_DIR = Path("output/higgs_v3_test")


def _extract_pcm(multimodal_output: dict) -> torch.Tensor:
    audio = multimodal_output.get("model_outputs")
    if audio is None:
        audio = multimodal_output.get("audio")
    if audio is None:
        raise ValueError(f"no audio key in multimodal_output: {list(multimodal_output.keys())}")
    if isinstance(audio, list):
        valid = [torch.as_tensor(a).float().cpu().reshape(-1) for a in audio if a is not None]
        if not valid:
            raise ValueError("audio list is empty")
        return torch.cat(valid, dim=0) if len(valid) > 1 else valid[0]
    return torch.as_tensor(audio).float().cpu().reshape(-1)


def _pcm_to_int16(pcm: torch.Tensor) -> np.ndarray:
    arr = pcm.numpy()
    if arr.dtype.kind == "f":
        arr = np.clip(arr, -1.0, 1.0)
        arr = (arr * 32767.0).astype(np.int16)
    else:
        arr = arr.astype(np.int16)
    return arr


def main():
    text = sys.argv[1] if len(sys.argv) > 1 else "Hola, esta es una prueba de voz en español."
    ref_audio = sys.argv[2] if len(sys.argv) > 2 else None
    ref_text = sys.argv[3] if len(sys.argv) > 3 else None

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Modelo  : {MODEL_PATH}")
    print(f"Texto   : {text}")
    print(f"Ref     : {ref_audio or 'ninguno'}")
    print("Iniciando motor vLLM-Omni (esto puede tomar unos minutos)...")

    # Configuración para bajo VRAM (~8 GB)
    # Higgs v3 4B en FP16 son ~8GB de pesos solos.
    # Usamos cpu_offload_gb para mover parte del modelo a RAM y FP8 para reducir.
    engine_kwargs = {
        "trust_remote_code": True,
        "gpu_memory_utilization": 0.85,
        "max_model_len": 512,
        "dtype": "half",  # fp16
        "quantization": "fp8",
        "enforce_eager": True,
        "disable_custom_all_reduce": True,
        "cpu_offload_gb": 4,  # Mover ~4GB de pesos a RAM
    }

    t0 = time.time()
    engine = Omni(model=MODEL_PATH, **engine_kwargs)
    print(f"Motor listo en {time.time() - t0:.1f}s")

    from transformers import AutoTokenizer
    from vllm_omni.model_executor.models.higgs_audio_v3.higgs_audio_v3_tokenizer import (
        HiggsAudioV3TokenizerAdapter,
        apply_delay_pattern,
        encode_reference_audio,
    )

    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
    adapter = HiggsAudioV3TokenizerAdapter(tokenizer)

    # Preparar referencia de voz (voice clone)
    ref_codes_delayed = None
    if ref_audio is not None:
        ref_path = Path(ref_audio)
        if not ref_path.exists():
            raise FileNotFoundError(f"Archivo de referencia no encontrado: {ref_audio}")
        ref_wav, ref_sr = sf.read(str(ref_path), always_2d=False)
        if ref_wav.ndim == 2:
            ref_wav = ref_wav.mean(axis=1)
        ref_codes_raw = encode_reference_audio(ref_wav, int(ref_sr))
        ref_codes_delayed = apply_delay_pattern(ref_codes_raw)
        print(f"Referencia cargada: {ref_codes_raw.shape[0]} frames")

    # Construir prompt
    if ref_codes_delayed is not None:
        prompt_ids = adapter.build_prompt(
            text,
            num_ref_tokens=int(ref_codes_delayed.shape[0]),
            reference_text=ref_text,
        )
        prompt = {
            "prompt_token_ids": prompt_ids,
            "additional_information": {
                "audio_input_ids": ref_codes_delayed.to(torch.long),
                "audio_input_ids_mask": torch.ones(ref_codes_delayed.shape[0], dtype=torch.bool),
            },
        }
    else:
        prompt_ids = adapter.build_prompt(text)
        prompt = {"prompt_token_ids": prompt_ids}

    print("Generando audio...")
    t0 = time.time()
    outputs = engine.generate([prompt])
    elapsed = time.time() - t0

    mm = outputs[0].outputs[0].multimodal_output
    pcm = _extract_pcm(mm)

    out_path = OUTPUT_DIR / "prueba_higgs_v3.wav"
    sf.write(str(out_path), _pcm_to_int16(pcm), SAMPLE_RATE, format="WAV", subtype="PCM_16")

    dur = pcm.numel() / SAMPLE_RATE
    rtf = elapsed / dur if dur > 0 else float("inf")
    print(f"\n✅ Audio guardado: {out_path}")
    print(f"   Duración : {dur:.2f}s")
    print(f"   Tiempo   : {elapsed:.2f}s")
    print(f"   RTF      : {rtf:.3f}")


if __name__ == "__main__":
    main()
