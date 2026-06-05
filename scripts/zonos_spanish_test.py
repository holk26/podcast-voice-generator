#!/usr/bin/env python3
"""Prueba Zonos TTS en español con emociones."""
import os
import sys
import torch
import torchaudio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zonos.model import Zonos
from zonos.conditioning import make_cond_dict
from zonos.utils import DEFAULT_DEVICE

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Usando device: {DEVICE}")

if DEVICE == "cuda":
    vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
    print(f"VRAM total: {vram:.1f} GB")

MODEL_NAME = "Zyphra/Zonos-v0.1-transformer"

print("Cargando modelo Zonos (esto puede tardar varios minutos la primera vez)...")
model = Zonos.from_pretrained(MODEL_NAME, device=DEVICE)
print("Modelo cargado.")

# Generar un speaker embedding desde un audio de referencia
# Usamos un audio generado previamente con edge-tts como referencia
ref_audio_path = "output/muestra_edge_tts_alvaro.mp3"
if os.path.exists(ref_audio_path):
    print(f"Usando audio de referencia: {ref_audio_path}")
    wav, sr = torchaudio.load(ref_audio_path)
    speaker = model.make_speaker_embedding(wav, sr)
else:
    print("No hay audio de referencia. Usando speaker aleatorio (None).")
    speaker = None

# Texto de prueba en español con emociones
texto = "¡Hola! ¿Qué tal? Hoy vamos a hablar de las noticias tecnológicas más importantes del día. ¡Es increíble todo lo que está pasando!"

print("\nGenerando audio con emoción de felicidad...")
cond_dict = make_cond_dict(
    text=texto,
    speaker=speaker,
    language="es",
    emotion=[0.6, 0.02, 0.02, 0.02, 0.15, 0.02, 0.07, 0.1],  # Feliz/sorprendido
    pitch_std=50.0,
    speaking_rate=15.0,
    fmax=22050.0,
    device=DEVICE,
)

conditioning = model.prepare_conditioning(cond_dict)
codes = model.generate(conditioning)
wavs = model.autoencoder.decode(codes).cpu()

os.makedirs("output", exist_ok=True)
output_path = "output/zonos_spanish_feliz.wav"
torchaudio.save(output_path, wavs[0], model.autoencoder.sampling_rate)
print(f"\n✅ Audio generado: {output_path}")
print(f"Duración: {wavs.shape[-1] / model.autoencoder.sampling_rate:.1f}s")
