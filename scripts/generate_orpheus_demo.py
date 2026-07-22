#!/usr/bin/env python3
"""
Demo script: Genera audio con Orpheus TTS usando voces predefinidas.

Requisitos:
  - Para inglés: modelo descarga automáticamente (unsloth/orpheus-3b-0.1-ft)
  - Para español: solicitar acceso en https://huggingface.co/canopylabs/3b-es_it-ft-research_release
    y configurar HF token: huggingface-cli login

Uso:
  venv311/bin/python scripts/generate_orpheus_demo.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.orpheus_engine import OrpheusEngine, ORPHEUS_VOICES
from core.project import Voice


def main():
    os.makedirs("output/orpheus_demo", exist_ok=True)

    # Elige modelo: inglés (público) o español (gated, requiere token)
    model_name = os.getenv("ORPHEUS_MODEL", "unsloth/orpheus-3b-0.1-ft")
    # Para español descomenta:
    # model_name = "canopylabs/3b-es_it-ft-research_release"

    engine = OrpheusEngine(model_name=model_name, load_in_8bit=True)
    print(f"[Demo] Cargando modelo: {model_name}")
    print("[Demo] Primera vez descarga ~6GB, puede tardar 10-15 min...")
    engine.load()

    # Textos de prueba por idioma
    if "es_it" in model_name or "spanish" in model_name.lower():
        demos = [
            ("leo", "¡Hola! Soy Leo, una voz generada por inteligencia artificial. <laugh> ¡Qué emoción!"),
            ("tara", "Hola, me llamo Tara. Puedo expresar emociones como risas <chuckle> o suspiros <sigh>."),
            ("dan",  "Soy Dan. Mi voz es más grave, ideal para documentales o narración seria."),
        ]
    else:
        demos = [
            ("leo", "Hello! I'm Leo, an AI-generated voice. <laugh> This is amazing!"),
            ("tara", "Hi, I'm Tara. I can express emotions like laughter <chuckle> or sighs <sigh>."),
            ("dan",  "I'm Dan. My voice is deeper, great for documentaries or serious narration."),
        ]

    for voice_id, text in demos:
        voice = Voice(
            id=f"orpheus_{voice_id}",
            name=voice_id.capitalize(),
            type="pretrained",
            engine="orpheus",
            language="es" if "es" in model_name else "en",
            speaker_id=voice_id,
        )
        out_path = f"output/orpheus_demo/{voice_id}_demo.wav"
        print(f"\n[Demo] Generando {voice_id}: {text[:50]}...")
        engine.synthesize(text, voice, out_path)
        print(f"[Demo] Guardado: {out_path}")

    engine.unload()
    print("\n✅ Demo completa. Archivos en output/orpheus_demo/")
    print("   Para español, solicita acceso al modelo en HuggingFace:")
    print("   https://huggingface.co/canopylabs/3b-es_it-ft-research_release")


if __name__ == "__main__":
    main()
