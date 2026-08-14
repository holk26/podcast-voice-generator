"""
Demo Fase 1: MediaPackage + VoiceCast + Audio Generation

Este script demuestra el flujo completo de la Fase 1:
1. Crea un MediaPackage con un guion multi-voz
2. Usa VoiceCastManager para resolver voces
3. Genera audio con Edge-TTS para cada línea
4. Guarda el paquete completo en media_packages/

Requiere: edge-tts instalado (pip install edge-tts)
"""

import os
import sys
from pathlib import Path

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.media_package import MediaPackage, Manifest, ScriptLine
from cast.voice_cast_manager import VoiceCastManager
from core.edge_tts_engine import EdgeTTSEngine


def main():
    print("=" * 60)
    print("DEMO FASE 1: MediaPackage + VoiceCast + Audio Generation")
    print("=" * 60)

    # ── 1. Initialize Voice Cast ─────────────────────────────────────
    print("\n[1] Loading Voice Cast...")
    vcm = VoiceCastManager()
    print(f"    Available voices: {vcm.list_voice_ids()}")
    print(f"    Character map: {vcm.list_characters()}")

    # ── 2. Create MediaPackage ───────────────────────────────────────
    print("\n[2] Creating MediaPackage...")
    pkg = MediaPackage(package_id="demo_techpulse_pilot")
    pkg.set_manifest(Manifest(
        title="TechPulse Pilot — Demo Fase 1",
        description="Episodio de demostración de la Media Automation Platform.",
        summary="Demo de multi-voz con Homero y Dalia presentando noticias tech.",
        author="Media Automation Platform",
        category="Technology",
        content_type="podcast",
        episode_number=1
    ))

    # Script: a short news podcast scene
    script_lines = [
        ScriptLine(
            character="Presentador",
            text="¡Buenos días! Bienvenidos a TechPulse, su resumen diario de noticias tecnológicas. Soy Homero.",
            voice_id="homer",
            pause_after_ms=800
        ),
        ScriptLine(
            character="Presentadora",
            text="Y yo soy Dalia. Hoy tenemos noticias emocionantes sobre inteligencia artificial y lanzamientos de hardware.",
            voice_id="dalia",
            pause_after_ms=800
        ),
        ScriptLine(
            character="Presentador",
            text="Empecemos con el primer tema: NVIDIA acaba de anunciar su nueva arquitectura de tarjetas gráficas.",
            voice_id="homer",
            pause_after_ms=600
        ),
        ScriptLine(
            character="Presentadora",
            text="Es increíble cómo la computación gráfica sigue avanzando a pasos agigantados. ¿Qué opinas, Homero?",
            voice_id="dalia",
            pause_after_ms=600
        ),
        ScriptLine(
            character="Presentador",
            text="Creo que estamos viviendo una revolución tecnológica sin precedentes. Hasta mañana, amigos.",
            voice_id="homer",
            pause_after_ms=400
        ),
    ]
    pkg.add_lines(script_lines)
    print(f"    Script created with {len(pkg.script)} lines")

    # ── 3. Save package ──────────────────────────────────────────────
    print("\n[3] Saving MediaPackage...")
    output_dir = Path("media_packages")
    output_dir.mkdir(exist_ok=True)
    package_path = pkg.save(str(output_dir))
    print(f"    Package saved to: {package_path}")

    # ── 4. Generate audio per line ───────────────────────────────────
    print("\n[4] Generating audio for each line...")
    engine = EdgeTTSEngine()
    engine.load()

    assets_dir = package_path / "assets"
    assets_dir.mkdir(exist_ok=True)

    for i, line in enumerate(pkg.script):
        # Resolve voice
        profile = vcm.resolve_voice_for_line(line.character, fallback_voice_id=line.voice_id)
        voice = profile.to_voice()

        output_path = assets_dir / f"line_{i:03d}_{profile.voice_id}.wav"
        print(f"    [{i+1}/{len(pkg.script)}] {line.character} ({profile.voice_id}): {line.text[:50]}...")
        try:
            engine.synthesize(line.text, voice, str(output_path))
            print(f"         → {output_path}")
        except Exception as e:
            print(f"         → ERROR: {e}")

    print("\n" + "=" * 60)
    print("DEMO COMPLETADO")
    print("=" * 60)
    print(f"\nPackage location: {package_path}")
    print(f"Assets generated: {len(list(assets_dir.glob('*.wav')))}")
    print("\nNext steps:")
    print("  - Fase 2: DramaMixer will combine these lines into a single track")
    print("  - Fase 3: BrandingEngine will add intro/outro music")
    print("  - Fase 4: Content sources (RSS, Gutenberg) will feed scripts automatically")


if __name__ == "__main__":
    main()
