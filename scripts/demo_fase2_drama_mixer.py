"""
Demo Fase 2: Dialogue Parser + Drama Mixer

Este script demuestra el flujo completo de la Fase 2:
1. Parsea un guion en formato screenplay a turnos de personajes
2. Crea un MediaPackage con los turnos
3. Usa DramaMixer para generar un audio dramatizado multi-voz
4. Guarda el MP3 final y el MediaPackage completo

Requiere: edge-tts instalado
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.media_package import MediaPackage, Manifest
from processors.dialogue_parser import DialogueParser
from audio.drama_mixer import DramaMixer


def main():
    print("=" * 60)
    print("DEMO FASE 2: Dialogue Parser + Drama Mixer")
    print("=" * 60)

    # ── 1. Define screenplay script ──────────────────────────────────
    screenplay = """
PRESENTADOR: ¡Buenos días! Bienvenidos a TechPulse, su resumen diario de noticias tecnológicas.
PRESENTADORA: Y yo soy Dalia. Hoy hablaremos de los avances más recientes en inteligencia artificial.
PRESENTADOR: Empecemos. NVIDIA ha anunciado una nueva arquitectura de tarjetas gráficas con el doble de rendimiento.
PRESENTADORA: Eso es impresionante. ¿Crees que cambiará el mercado de los videojuegos?
PRESENTADOR: Definitivamente. Los desarrolladores podrán crear mundos mucho más detallados.
PRESENTADORA: Increíble. Hasta mañana, amigos.
PRESENTADOR: Hasta mañana.
"""

    # ── 2. Parse screenplay ──────────────────────────────────────────
    print("\n[1] Parsing screenplay...")
    parser = DialogueParser()
    lines = parser.parse_with_character_map(
        screenplay,
        character_voice_map={
            "Presentador": "homer",
            "Presentadora": "dalia"
        }
    )
    print(f"    Parsed {len(lines)} dialogue turns")
    for i, line in enumerate(lines):
        print(f"    [{i+1}] {line.character} ({line.voice_id}): {line.text[:50]}...")

    # ── 3. Create MediaPackage ───────────────────────────────────────
    print("\n[2] Creating MediaPackage...")
    pkg = MediaPackage(package_id="demo_fase2_techpulse_drama")
    pkg.set_manifest(Manifest(
        title="TechPulse — Demo Fase 2 (Drama Mix)",
        description="Podcast dramatizado generado automáticamente con DialogueParser y DramaMixer.",
        summary="Demo de audio multi-voz con Homero y Dalia.",
        category="Technology",
        content_type="podcast",
        episode_number=2
    ))
    pkg.add_lines(lines)

    output_dir = Path("media_packages")
    output_dir.mkdir(exist_ok=True)
    pkg.save(str(output_dir))
    print(f"    Package saved to: media_packages/{pkg.package_id}")

    # ── 4. Render with DramaMixer ────────────────────────────────────
    print("\n[3] Rendering audio with DramaMixer...")
    mixer = DramaMixer()
    output_path = f"media_packages/{pkg.package_id}/assets/mix_final.mp3"

    try:
        mixer.mix_package(pkg, output_path)
        print(f"    Final mix saved to: {output_path}")

        # Check file size
        size_kb = Path(output_path).stat().st_size / 1024
        print(f"    File size: {size_kb:.1f} KB")
    finally:
        mixer.close()

    print("\n" + "=" * 60)
    print("DEMO FASE 2 COMPLETADO")
    print("=" * 60)
    print("\nPróximos pasos:")
    print("  - Fase 3: BrandingEngine añadirá intro/outro musical")
    print("  - Fase 4: RSS/Gutenberg alimentarán guiones automáticamente")


if __name__ == "__main__":
    main()
