#!/usr/bin/env python3
"""Genera podcast con XTTS v2 clonando una voz expresiva de referencia."""
import os
import sys
import torch
from pydub import AudioSegment

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.xtts_engine import XTTSEngine, _apply_torch_compat_patches
from core.project import Voice

# Configurar GPU
_apply_torch_compat_patches()
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Usando device: {DEVICE}")

# Inicializar XTTS v2
print("Cargando XTTS v2...")
engine = XTTSEngine(device=DEVICE)
engine.load()
print("Modelo cargado.")

# Crear voz clonada desde referencia
REF_PATH = "output/ref_voz_expressiva.wav"
if not os.path.exists(REF_PATH):
    raise FileNotFoundError(f"No se encontró el audio de referencia: {REF_PATH}")

voice = Voice(
    id="cloned_expressiva",
    name="Voz Expressiva Clonada",
    type="cloned",
    engine="xtts",
    language="es",
    reference_path=REF_PATH,
    speed=1.0,
)

# Script de podcast dividido en segmentos (XTTS v2 limita ~400 tokens)
SEGMENTOS = [
    "¡Hola! ¿Qué tal? Bienvenidos a Tech Pulse, su resumen de noticias tecnológicas. Hoy es martes, dos de junio de dos mil veintiséis.",
    "Empezamos con Microsoft Build 2026, que está arrancando en San Francisco. El eje central es la inteligencia artificial agente.",
    "Microsoft presentó Scout, un asistente personal que integra Outlook, OneDrive y Teams. Puede organizar calendarios, redactar correos e incluso hacer llamadas telefónicas.",
    "En hardware, Microsoft lanzó la Surface RTX Spark Dev Box. Una mini PC con el nuevo chip de Nvidia y ciento veintiocho gigabytes de memoria unificada.",
    "También presentaron Majorana Dos, su nuevo procesador cuántico. Los cúbits son mil veces más fiables que los de la generación anterior.",
    "Microsoft también muestra Project Solara, un sistema operativo basado en Android para dispositivos con agentes de inteligencia artificial.",
    "Del lado de Nvidia, Jensen Huang confirmó que llevan tres años trabajando con Microsoft en el chip RTX Spark. Promete un petaflop de rendimiento de inteligencia artificial.",
    "Google lanza un armario digital generado por inteligencia artificial en Google Fotos. Analiza tus imágenes para crear combinaciones de ropa virtuales.",
    "OpenAI anunció que Codex, su agente de programación, ya cuenta con cinco millones de usuarios semanales.",
    "Apple se prepara para su WWDC 2026. Se esperan iOS veintisiete y una versión conversacional de Siri que competiría con ChatGPT.",
    "Eso es todo por hoy en Tech Pulse. Si te ha gustado este episodio, compártelo. ¡Hasta mañana!",
]

os.makedirs("output", exist_ok=True)

segment_files = []
for i, texto in enumerate(SEGMENTOS):
    print(f"\nGenerando segmento {i+1}/{len(SEGMENTOS)}...")
    output_path = f"output/podcast_seg_{i:03d}.wav"
    
    try:
        engine.synthesize(texto, voice, output_path)
        segment_files.append(output_path)
        print(f"  ✅ Segmento {i+1} generado ({len(texto)} chars)")
    except Exception as e:
        print(f"  ❌ Error en segmento {i+1}: {e}")
        # Crear un audio de silencio como placeholder para no romper la secuencia
        silent = AudioSegment.silent(duration=500)
        silent.export(output_path, format="wav")
        segment_files.append(output_path)

# Unir todos los segmentos
print("\n" + "="*60)
print("Uniendo segmentos...")
combined = AudioSegment.empty()
for seg_file in segment_files:
    segment = AudioSegment.from_wav(seg_file)
    combined += segment
    # Pequeña pausa entre segmentos
    combined += AudioSegment.silent(duration=300)
    os.remove(seg_file)

output_final = "output/podcast_noticias_xtts_clonado.wav"
combined.export(output_final, format="wav")
print(f"\n✅ Podcast final generado: {output_final}")
print(f"Duración total: {len(combined)/1000:.1f} segundos ({len(combined)/60000:.1f} minutos)")
print(f"Tamaño: {os.path.getsize(output_final)/1024**2:.1f} MB")
