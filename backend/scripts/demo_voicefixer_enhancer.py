"""
Demo: Audio Enhancement con VoiceFixer

Compara audio generado SIN enhancer vs CON enhancer (por línea + post-mix).
Genera un fragmento corto de Homero en ambas modalidades para comparar calidad.
"""

import sys
import os
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.media_package import MediaPackage, ScriptLine, Manifest
from audio.drama_mixer import DramaMixer
from audio.audio_enhancer import VoiceFixerEnhancer, NoOpEnhancer
from cast.voice_cast_manager import VoiceCastManager


def build_test_package() -> MediaPackage:
    """Create a small 3-line test package with Homer."""
    manifest = Manifest(
        title="Test Enhancement",
        description="Demo comparativo de VoiceFixer",
        author="Media Automation Platform",
        content_type="demo"
    )
    pkg = MediaPackage(package_id="demo_enhancer", manifest=manifest)

    lines = [
        ScriptLine(character="Homero", text="Hola. Soy Homero. Este es un test de calidad de audio.", voice_id="homer"),
        ScriptLine(character="Homero", text="La voz que escuchas ahora pasará por un modelo de inteligencia artificial.", voice_id="homer"),
        ScriptLine(character="Homero", text="El resultado será un audio más limpio, claro y profesional.", voice_id="homer"),
    ]
    for line in lines:
        pkg.add_line(line)
    return pkg


def render_with_enhancer(pkg: MediaPackage, enhancer, label: str, output_dir: str) -> str:
    """Render package with given enhancer."""
    print(f"\n{'='*60}")
    print(f"RENDERIZANDO: {label}")
    print(f"{'='*60}")

    voice_cast = VoiceCastManager()
    mixer = DramaMixer(
        voice_cast=voice_cast,
        sample_rate=24000,
        enhancer=enhancer,
        enhance_per_line=(enhancer is not None),
        enhance_final=(enhancer is not None)
    )

    output_path = os.path.join(output_dir, f"demo_{label.lower().replace(' ', '_')}.mp3")
    try:
        mixer.mix_package(pkg, output_path, keep_line_files=True)
        size_kb = os.path.getsize(output_path) / 1024
        print(f"✓ {label}: {output_path} ({size_kb:.1f} KB)")
        return output_path
    finally:
        mixer.close()


def main():
    tmpdir = tempfile.mkdtemp()
    print("=" * 60)
    print("DEMO: Audio Enhancement con VoiceFixer")
    print("=" * 60)
    print(f"\nDirectorio temporal: {tmpdir}")
    print("Generando 3 líneas de Homero con XTTS...")
    print("Luego aplicando VoiceFixer en cada línea + audio final...")
    print("\n⚠️  Esto tomará varios minutos (descarga de modelos + procesamiento)")

    pkg = build_test_package()

    # 1. Sin enhancer
    path_no_enh = render_with_enhancer(pkg, None, "SIN enhancer", tmpdir)

    # 2. Con enhancer (VoiceFixer)
    enhancer = VoiceFixerEnhancer(cuda=True, mode=0)
    path_with_enh = render_with_enhancer(pkg, enhancer, "CON VoiceFixer", tmpdir)
    enhancer.close()

    # Summary
    print("\n" + "=" * 60)
    print("RESUMEN COMPARATIVO")
    print("=" * 60)
    for label, path in [("SIN enhancer", path_no_enh), ("CON VoiceFixer", path_with_enh)]:
        size = os.path.getsize(path) / 1024
        print(f"  {label}:")
        print(f"    {path}")
        print(f"    Tamaño: {size:.1f} KB")

    print("\n✓ Ambos archivos están listos para comparación.")
    print(f"  Escucha primero '{path_no_enh}' y luego '{path_with_enh}'")

    # Don't cleanup so user can listen
    print(f"\nArchivos preservados en: {tmpdir}")


if __name__ == "__main__":
    main()
