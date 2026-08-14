"""
Genera un audiolibro real del Capítulo II de Don Quijote con voz de Homero + VoiceFixer.

Flujo completo:
  1. Descarga Don Quijote de Gutenberg
  2. Extrae Capítulo II
  3. Resume a ~400 palabras
  4. Convierte a guion con Homero como narrador
  5. Genera audio con XTTS (voz clonada Homero)
  6. Aplica VoiceFixer por línea + post-mix
  7. Aplica branding con intro/outro
  8. Guarda todo organizado en output/don_quijote_cap2/
"""

import sys
import os
import shutil
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from content.gutenberg_fetcher import GutenbergFetcher
from core.media_package import MediaPackage, ScriptLine, Manifest
from audio.drama_mixer import DramaMixer
from audio.branding_engine import BrandingEngine
from audio.audio_enhancer import VoiceFixerEnhancer
from cast.voice_cast_manager import VoiceCastManager


def download_chapter():
    print("[1] Descargando Don Quijote desde Gutenberg...")
    fetcher = GutenbergFetcher(timeout=120)
    book = fetcher.fetch_book('2000')
    text = book.get('cleaned_text', '')
    chapters = fetcher.split_into_chapters(text)

    # Capítulo II (índice 1, ya que índice 0 es el Prólogo)
    chapter = chapters[1]
    title = chapter['title']
    full_text = chapter['text']

    print(f"    Título: {title}")
    print(f"    Palabras totales: {len(full_text.split())}")

    # Limitar a primeras 400 palabras para que el renderizado sea rápido
    words = full_text.split()
    limited = ' '.join(words[:400])
    print(f"    Usando primeras 400 palabras")

    return title, limited, book


def text_to_script(title: str, text: str) -> str:
    """Convierte texto plano a guion con tags de voz."""
    print("\n[2] Convirtiendo texto a guion dramatizado...")

    # Dividir en frases para líneas de guion
    sentences = []
    for raw in text.replace('\n', ' ').split('. '):
        raw = raw.strip()
        if raw:
            if not raw.endswith('.'):
                raw += '.'
            if len(raw) > 150:
                # Dividir frases muy largas
                parts = raw.split(', ')
                for p in parts:
                    p = p.strip()
                    if p and len(p) > 10:
                        sentences.append(p)
            else:
                sentences.append(raw)

    # Crear guion con Homero como narrador
    lines = []
    lines.append(f"[homer]Capítulo. {title.replace('Capítulo II. ', '')}[/homer]")
    lines.append("[homer]Escrito por Miguel de Cervantes Saavedra.[/homer]")

    for sent in sentences[:25]:  # Limitar a 25 líneas
        # Escapar caracteres problemáticos para TTS
        clean = sent.replace('[', '').replace(']', '').replace('—', ', ')
        if len(clean) > 10:
            lines.append(f"[homer]{clean}[/homer]")

    lines.append("[homer]Fin del capítulo.[/homer]")

    script = '\n\n'.join(lines)
    print(f"    Líneas de guion: {len(lines)}")
    return script


def build_package(script_text: str, title: str) -> MediaPackage:
    from processors.dialogue_parser import DialogueParser
    parser = DialogueParser()
    parsed = parser.parse(script_text)

    manifest = Manifest(
        title=f"Don Quijote — {title}",
        description="Audiolibro generado con voz clonada de Homero + VoiceFixer",
        author="Miguel de Cervantes Saavedra",
        content_type="audiobook",
        language="es-ES"
    )
    pkg = MediaPackage(package_id="don_quijote_cap2_homero", manifest=manifest)

    for p in parsed:
        line = ScriptLine(
            character=p.character,
            text=p.text,
            voice_id=p.voice_id,
            pause_before_ms=300,
            pause_after_ms=500
        )
        pkg.add_line(line)

    return pkg


def render_with_enhancer(pkg: MediaPackage, output_dir: str):
    print("\n[3] Renderizando audio con Homero (XTTS)...")
    print("    Esto tomará varios minutos...")

    voice_cast = VoiceCastManager()

    # VoiceFixer enhancer
    enhancer = VoiceFixerEnhancer(cuda=True, mode=0)

    mixer = DramaMixer(
        voice_cast=voice_cast,
        sample_rate=24000,
        enhancer=enhancer,
        enhance_per_line=True,
        enhance_final=True
    )

    main_audio = os.path.join(output_dir, "cap2_main.mp3")
    os.makedirs(output_dir, exist_ok=True)

    try:
        mixer.mix_package(pkg, main_audio)
        print(f"    ✓ Audio principal: {main_audio}")
    finally:
        mixer.close()

    # Branding
    print("\n[4] Aplicando branding (intro/outro)...")
    branding = BrandingEngine(voice_cast=voice_cast, sample_rate=24000)
    final_audio = os.path.join(output_dir, "cap2_final.mp3")

    try:
        branding.apply_to_package(
            package=pkg,
            main_audio_path=main_audio,
            output_path=final_audio,
            host_voice_id="homer"
        )
        print(f"    ✓ Audio final: {final_audio}")
    finally:
        branding.close()

    # Guardar MediaPackage
    pkg_dir = os.path.join(output_dir, "media_package")
    if os.path.exists(pkg_dir):
        shutil.rmtree(pkg_dir)
    pkg.save(pkg_dir)
    print(f"    ✓ MediaPackage: {pkg_dir}")

    # Guardar guion
    script_path = os.path.join(output_dir, "script.txt")
    with open(script_path, 'w', encoding='utf-8') as f:
        for line in pkg.script:
            f.write(f"{line.character}: {line.text}\n")
    print(f"    ✓ Guion: {script_path}")

    # Stats
    size_kb = os.path.getsize(final_audio) / 1024
    print(f"\n    Tamaño final: {size_kb:.1f} KB")

    return final_audio


def main():
    print("=" * 60)
    print("GENERADOR DE AUDIOLIBRO: DON QUIJOTE + HOMERO + VOICEFIXER")
    print("=" * 60)

    output_dir = "output/don_quijote_cap2"
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    # 1. Descargar
    title, text, book = download_chapter()

    # 2. Guion
    script = text_to_script(title, text)

    # Guardar guion raw
    with open(os.path.join(output_dir, "guion_raw.txt"), 'w', encoding='utf-8') as f:
        f.write(script)

    # 3. Package
    pkg = build_package(script, title)

    # 4. Render + enhance
    final_audio = render_with_enhancer(pkg, output_dir)

    # Summary
    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    print(f"Título: {pkg.manifest.title}")
    print(f"Líneas: {len(pkg.script)}")
    print(f"Audio final: {final_audio}")
    print(f"Carpeta: {os.path.abspath(output_dir)}")
    print("\n✓ Audiolibro generado con:")
    print("  - Voz clonada de Homero (XTTS)")
    print("  - VoiceFixer (restauración + mejora por línea + post-mix)")
    print("  - Branding con intro/outro")
    print("\nArchivos en la carpeta:")
    for f in sorted(os.listdir(output_dir)):
        path = os.path.join(output_dir, f)
        if os.path.isfile(path):
            size = os.path.getsize(path) / 1024
            print(f"  {f} ({size:.1f} KB)")
        else:
            print(f"  {f}/")


if __name__ == "__main__":
    main()
