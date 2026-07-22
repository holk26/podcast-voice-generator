#!/usr/bin/env python3
"""Quick test for OrpheusEngine integration."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.orpheus_engine import OrpheusEngine
from core.project import Voice

os.makedirs("output/orpheus_test", exist_ok=True)

engine = OrpheusEngine(load_in_8bit=True)
print("Loading model (this may take 2-5 min first time)...")
engine.load()

voice = Voice(
    id="orpheus_leo",
    name="Leo",
    type="pretrained",
    engine="orpheus",
    language="es",
    speaker_id="leo"
)

texts = [
    "¡Hola mundo! Esta es una prueba de Orpheus TTS.",
    "<laugh> Qué divertido es probar nuevas tecnologías.",
]

for i, text in enumerate(texts):
    out_path = f"output/orpheus_test/test_{i:02d}_leo.wav"
    print(f"\nGenerating: {text[:50]}...")
    engine.synthesize(text, voice, out_path)
    print(f"Saved: {out_path}")

engine.unload()
print("\n✅ Orpheus test complete!")
