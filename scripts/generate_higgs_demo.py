#!/usr/bin/env python3
"""
Demo script: Genera audio con Higgs Audio v3 TTS.

Uso:
  venv311/bin/python scripts/generate_higgs_demo.py

Requisitos:
  - vllm-omni instalado
  - Modelo descargado: bosonai/higgs-audio-v3-tts-4b (~9.3 GB)
  - VRAM: ~18-20 GB en FP16, ~8-10 GB con cuantización

En 8 GB VRAM (RTX 5060) probablemente necesites cuantización o dará OOM.
Opciones para 8 GB:
  1. Usar cuantización: export HIGGS_QUANTIZATION=fp8
  2. Reducir gpu_memory_utilization: export HIGGS_GPU_UTIL=0.7
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.higgs_engine import HiggsAudioEngine
from core.project import Voice


def main():
    os.makedirs("output/higgs_demo", exist_ok=True)

    model_name = os.getenv("HIGGS_MODEL", "bosonai/higgs-audio-v3-tts-4b")
    quantization = os.getenv("HIGGS_QUANTIZATION", None)
    gpu_util = float(os.getenv("HIGGS_GPU_UTIL", "0.85"))

    print(f"[Demo] Modelo: {model_name}")
    print(f"[Demo] Cuantización: {quantization or 'ninguna (FP16)'}")
    print(f"[Demo] GPU memory utilization: {gpu_util}")
    print("[Demo] Cargando engine (puede tardar 2-5 min primero)...")

    engine = HiggsAudioEngine(
        model_name=model_name,
        gpu_memory_utilization=gpu_util,
        quantization=quantization,
    )
    engine.load()

    # Demo 1: Plain TTS (sin referencia)
    voice_plain = Voice(
        id="higgs_narrador",
        name="Narrador",
        type="pretrained",
        engine="higgs",
        language="es",
        speaker_id="higgs_default",
    )

    textos = [
        "¡Hola mundo! Esta es una prueba de Higgs Audio v3.",
        "<|emotion:elation|>¡Qué emocionante es probar esta tecnología!",
        "<|prosody:speed_slow|>Puedo hablar lentamente... <|prosody:pause|>y hacer pausas.",
    ]

    for i, texto in enumerate(textos):
        out_path = f"output/higgs_demo/plain_{i:02d}.wav"
        print(f"\n[Demo] Generando: {texto[:50]}...")
        try:
            engine.synthesize(texto, voice_plain, out_path)
            print(f"[Demo] Guardado: {out_path}")
        except Exception as e:
            print(f"[Demo] ERROR: {e}")

    # Demo 2: Voice cloning con referencia de Homero
    ref_path = "voices/clones/voz_homer_compat_mejorada.wav"
    if os.path.exists(ref_path):
        print(f"\n[Demo] Voice cloning con referencia: {ref_path}")
        voice_clone = Voice(
            id="higgs_homero",
            name="Homero (Higgs)",
            type="cloned",
            engine="higgs",
            language="es",
            speaker_id="higgs_default",
            reference_path=ref_path,
        )
        out_path = "output/higgs_demo/cloned_homero.wav"
        try:
            engine.synthesize(
                "¡Hola! Soy Homero, clonado con Higgs Audio v3. <laugh> ¡Qué divertido!",
                voice_clone,
                out_path,
            )
            print(f"[Demo] Guardado: {out_path}")
        except Exception as e:
            print(f"[Demo] ERROR en cloning: {e}")
    else:
        print(f"\n[Demo] Referencia no encontrada: {ref_path}")
        print("[Demo] Salta voice cloning.")

    engine.unload()
    print("\n✅ Demo completa. Archivos en output/higgs_demo/")
    print("   Si tuviste OOM (out of memory), prueba:")
    print("   HIGGS_QUANTIZATION=fp8 HIGGS_GPU_UTIL=0.7 venv311/bin/python scripts/generate_higgs_demo.py")


if __name__ == "__main__":
    main()
