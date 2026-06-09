"""
Genera episodios REALES de motivación y meditación con la voz clonada de Homero.

Este script:
  1. Genera guiones completos y originales (actuando como LLM)
  2. Los estructura con tags de voz para el DramaMixer
  3. Usa XTTS con la voz real de Homero (voices/clones/voz_homer_compat.wav)
  4. Aplica branding con intro/outro
  5. Guarda los MP3 finales en output/
"""

import sys
import os
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.media_package import MediaPackage, ScriptLine, Manifest
from processors.dialogue_parser import DialogueParser
from audio.drama_mixer import DramaMixer
from audio.branding_engine import BrandingEngine
from cast.voice_cast_manager import VoiceCastManager


# ============================================================================
# GUIONES GENERADOS POR LLM (yo)
# ============================================================================

MOTIVATION_SCRIPT = """
[homer]Hola. Soy Homero. Y hoy vengo a recordarte algo que sueles olvidar.[/homer]

[homer]Estás vivo. Ahora mismo. Respirando. Pensando. Capaz de cambiar todo.[/homer]

[homer]Sé que la semana fue dura. Sé que hay días en los que todo pesa más. Pero aquí estás. Y eso ya es una victoria.[/homer]

[homer]No necesitas ser perfecto. Necesitas ser constante. Un paso. Solo uno. Eso es suficiente por hoy.[/homer]

[homer]Mira todo lo que has sobrevivido hasta ahora. ¿Te das cuenta? Eres más fuerte de lo que crees.[/homer]

[homer]El miedo no desaparece. Aprendes a caminar con él. Y cada vez que caminas con miedo... creces.[/homer]

[homer]No compares tu capítulo uno con el capítulo veinte de alguien más. Tu historia es única. Y vale la pena ser contada.[/homer]

[homer]Haz algo hoy que tu yo del futuro agradezca. Diez minutos. Una llamada. Un texto. Un paso.[/homer]

[homer]La disciplina vence a la motivación. Todos los días. No cuando tienes ganas. Cuando no las tienes.[/homer]

[homer]Descansa si necesitas descansar. Pero no te rindas. Hay una diferencia enorme entre parar y abandonar.[/homer]

[homer]El éxito no es una montaña. Es una escalera. Y cada escalón cuenta. Incluso los más pequeños.[/homer]

[homer]Tú no eres tus errores. Eres lo que haces después de ellos.[/homer]

[homer]Hoy es un buen día para empezar. No esperes al lunes. No esperes al primero de mes. Empieza ahora.[/homer]

[homer]Confío en ti. Sí, en ti. Porque sé que puedes. Ahora demuéstratelo a ti mismo.[/homer]

[homer]Eso fue todo por hoy. Soy Homero. Y te espero en el próximo episodio. Dale con todo.[/homer]
""".strip()

MEDITATION_SCRIPT = """
[homer]Bienvenido. Soy Homero. Y hoy voy a guiarte en una meditación de respiración.[/homer]

[homer]Siéntate cómodo. Relaja los hombros. Cierra los ojos si quieres. O simplemente mira hacia abajo, suavemente.[/homer]

[homer]Vamos a respirar juntos. Inhala profundo por la nariz... cuatro segundos.[/homer]

[homer]Manten el aire... dos segundos.[/homer]

[homer]Y exhala lentamente por la boca... seis segundos. Siente cómo el aire sale.[/homer]

[homer]De nuevo. Inhala profundo. Llena tu pecho de aire fresco.[/homer]

[homer]Mantenlo suavemente.[/homer]

[homer]Y exhala. Deja ir cualquier tensión que sientas en los hombros.[/homer]

[homer]Con cada inhalación, imagina que traes paz a tu cuerpo.[/homer]

[homer]Con cada exhalación, imagina que sueltas todo lo que no necesitas.[/homer]

[homer]No juzgues tus pensamientos. Solo obsérvalos. Como nubes pasando por el cielo.[/homer]

[homer]Vuelve a tu respiración. Es tu ancla. Siempre está aquí cuando la necesitas.[/homer]

[homer]Inhala tranquilidad... y exhala preocupación.[/homer]

[homer]Siente cómo tu cuerpo se hace más pesado. Más relajado. Más presente.[/homer]

[homer]Quédate aquí un momento. Solo respirando. Solo siendo.[/homer]

[homer]Cuando estés listo, mueve suavemente los dedos. Los pies.[/homer]

[homer]Abre los ojos con calma. Lleva esta paz contigo el resto del día.[/homer]

[homer]Gracias por meditar conmigo. Soy Homero. Hasta la próxima.[/homer]
""".strip()


def build_package(script_text: str, title: str, package_id: str) -> MediaPackage:
    """Parse script text into a MediaPackage with Homer voice lines."""
    parser = DialogueParser()
    lines = parser.parse(script_text)

    manifest = Manifest(
        title=title,
        description=f"Episodio generado con voz clonada de Homero — {title}",
        author="Media Automation Platform + Homero",
        content_type="motivation" if "motiv" in title.lower() else "meditation",
        language="es-ES",
        tags=["homero", "español", "generado"]
    )

    package = MediaPackage(package_id=package_id, manifest=manifest)

    for parsed in lines:
        # Homer voice with longer pauses for meditation
        pause_after = 800 if "medit" in title.lower() else 500
        line = ScriptLine(
            character=parsed.character,
            text=parsed.text,
            voice_id=parsed.voice_id,
            emotion="calm" if "medit" in title.lower() else "confident",
            pause_before_ms=600 if "medit" in title.lower() else 400,
            pause_after_ms=pause_after
        )
        package.add_line(line)

    return package


def render_episode(package: MediaPackage, output_name: str):
    """Render a package through DramaMixer + BrandingEngine."""
    print(f"\n{'='*60}")
    print(f"RENDERIZANDO: {package.manifest.title}")
    print(f"Líneas: {len(package.script)}")
    print(f"{'='*60}")

    voice_cast = VoiceCastManager()

    # DramaMixer
    mixer = DramaMixer(voice_cast=voice_cast, sample_rate=24000)
    main_audio = f"output/{output_name}_main.mp3"
    os.makedirs("output", exist_ok=True)

    try:
        mixer.mix_package(package, main_audio)
        print(f"✓ Audio principal: {main_audio}")
    finally:
        mixer.close()

    # BrandingEngine
    branding = BrandingEngine(voice_cast=voice_cast, sample_rate=24000)
    final_audio = f"output/{output_name}_final.mp3"

    try:
        branding.apply_to_package(
            package=package,
            main_audio_path=main_audio,
            output_path=final_audio,
            host_voice_id="homer"
        )
        print(f"✓ Audio final con branding: {final_audio}")
    finally:
        branding.close()

    # Copy package
    pkg_dir = f"media_packages/{output_name}"
    if os.path.exists(pkg_dir):
        shutil.rmtree(pkg_dir)
    package.save(pkg_dir)
    print(f"✓ MediaPackage guardado: {pkg_dir}")

    # Size
    size_kb = os.path.getsize(final_audio) / 1024
    print(f"✓ Tamaño: {size_kb:.1f} KB")

    return final_audio


def main():
    print("="*60)
    print("GENERADOR DE EPISODIOS REALES CON VOZ DE HOMERO")
    print("="*60)
    print("\n⚠️  Esto usará XTTS con la voz clonada real.")
    print("   El renderizado puede tardar varios minutos.")
    print("   Cada línea de Homero toma ~3-5 segundos en GPU.")

    # --- Motivación ---
    print("\n" + "="*60)
    print("EPISODIO 1: MOTIVACIÓN")
    print("="*60)
    pkg_mot = build_package(
        MOTIVATION_SCRIPT,
        title="Homero Motiva: Empieza Ahora",
        package_id="homer_motivacion_real"
    )
    final_mot = render_episode(pkg_mot, "homer_motivacion_real")

    # --- Meditación ---
    print("\n" + "="*60)
    print("EPISODIO 2: MEDITACIÓN")
    print("="*60)
    pkg_med = build_package(
        MEDITATION_SCRIPT,
        title="Homero Medita: Respiración y Paz",
        package_id="homer_meditacion_real"
    )
    final_med = render_episode(pkg_med, "homer_meditacion_real")

    # --- Resumen ---
    print("\n" + "="*60)
    print("RESUMEN")
    print("="*60)
    print(f"Motivación: {final_mot}")
    print(f"Meditación: {final_med}")
    print("\n✓ Ambos episodios generados con voz REAL de Homero (XTTS)")


if __name__ == "__main__":
    main()
