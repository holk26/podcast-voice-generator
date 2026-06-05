#!/usr/bin/env python3
"""Genera audio con Bark usando emociones y risas en español."""
import os
import sys
import torch
import numpy as np
from scipy.io import wavfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.gpu_utils import select_best_device

DEVICE = select_best_device()
print(f"Usando device: {DEVICE}")

# Importar Bark
from bark import SAMPLE_RATE, generate_audio, preload_models
from bark.api import semantic_to_waveform

print("Pre-cargando modelos Bark (si no están cargados)...")
preload_models(
    text_use_gpu=(DEVICE != "cpu"),
    coarse_use_gpu=(DEVICE != "cpu"),
    fine_use_gpu=(DEVICE != "cpu"),
    codec_use_gpu=(DEVICE != "cpu"),
)
print("Modelos listos.")

# Texto con emociones usando tags de Bark
# Bark entiende ciertos "non-verbal sounds" en el texto:
# [laughter], [laughs], [sighs], [gasps], [clears throat], [music]
# Y también entona basado en puntuación y contexto

textos = [
    "¡Hola! ¿Qué tal? [laughs] Hoy vamos a hablar de las noticias tecnológicas más importantes del día.",
    "¡Es increíble todo lo que está pasando! [laughter] Microsoft acaba de anunciar su nuevo asistente de inteligencia artificial.",
    "Nvidia presentó su nuevo chip RTX Spark. [sighs] Esto va a cambiar todo en el mundo de la computación personal.",
]

os.makedirs("output", exist_ok=True)

for i, texto in enumerate(textos):
    print(f"\nGenerando audio {i+1}/{len(textos)}...")
    print(f"Texto: {texto}")
    
    # Generar con history_prompt en español
    audio = generate_audio(
        texto,
        history_prompt="v2/es_speaker_6",  # Voz española
        text_temp=0.7,
        waveform_temp=0.7,
    )
    
    output_path = f"output/bark_spanish_emocion_{i+1}.wav"
    wavfile.write(output_path, SAMPLE_RATE, (audio * 32767).astype(np.int16))
    duracion = len(audio) / SAMPLE_RATE
    print(f"  ✅ Guardado: {output_path} ({duracion:.1f}s)")

print("\n✅ Todos los audios generados.")
