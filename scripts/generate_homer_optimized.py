"""
Generador OPTIMIZADO de episodios con Homero + VoiceFixer.

Configuración de máxima calidad:
  - XTTS genera a 24kHz
  - VoiceFixer upscala a 44.1kHz
  - Se mantiene 44.1kHz en la mezcla final
  - Exporta WAV 44.1kHz (sin pérdida) + MP3 320k
  - Bitrate máximo para calidad profesional
"""

import sys
import os
import shutil
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydub import AudioSegment
from audio.audio_enhancer import VoiceFixerEnhancer
from cast.voice_cast_manager import VoiceCastManager
from core.tts_engine import TTSBase
from core.edge_tts_engine import EdgeTTSEngine
from core.xtts_engine import XTTSEngine


# ============================================================================
# GUIONES MEJORADOS
# ============================================================================

MOTIVATION_LINES = [
    "Hola. Soy Homero. Y hoy vengo a recordarte algo importante.",
    "Estás vivo. Ahora mismo. Respirando. Pensando. Capaz de cambiar todo.",
    "Sé que hay días en los que todo pesa más. Pero aquí estás. Y eso ya es una victoria.",
    "No necesitas ser perfecto. Necesitas ser constante. Un paso. Solo uno. Eso es suficiente por hoy.",
    "Mira todo lo que has sobrevivido hasta ahora. Eres más fuerte de lo que crees.",
    "El miedo no desaparece. Aprendes a caminar con él. Y cada vez que caminas con miedo... creces.",
    "No compares tu capítulo uno con el capítulo veinte de alguien más. Tu historia es única.",
    "Haz algo hoy que tu yo del futuro agradezca. Diez minutos. Una llamada. Un paso.",
    "La disciplina vence a la motivación. Todos los días. No cuando tienes ganas. Cuando no las tienes.",
    "Descansa si necesitas descansar. Pero no te rindas. Hay una diferencia enorme entre parar y abandonar.",
    "El éxito no es una montaña. Es una escalera. Y cada escalón cuenta.",
    "Tú no eres tus errores. Eres lo que haces después de ellos.",
    "Hoy es un buen día para empezar. No esperes al lunes. Empieza ahora.",
    "Confío en ti. En ti. Porque sé que puedes. Ahora demuéstratelo a ti mismo.",
    "Eso fue todo por hoy. Soy Homero. Te espero en el próximo episodio. Dale con todo.",
]

MEDITATION_LINES = [
    "Bienvenido. Soy Homero. Hoy voy a guiarte en una meditación de respiración.",
    "Siéntate cómodo. Relaja los hombros. Cierra los ojos si quieres.",
    "Vamos a respirar juntos. Inhala profundo por la nariz... cuatro segundos.",
    "Mantén el aire... dos segundos.",
    "Y exhala lentamente por la boca... seis segundos. Siente cómo el aire sale.",
    "De nuevo. Inhala profundo. Llena tu pecho de aire fresco.",
    "Manténlo suavemente.",
    "Y exhala. Deja ir cualquier tensión en los hombros.",
    "Con cada inhalación, imagina que traes paz a tu cuerpo.",
    "Con cada exhalación, imagina que sueltas todo lo que no necesitas.",
    "No juzgues tus pensamientos. Solo obsérvalos. Como nubes pasando por el cielo.",
    "Vuelve a tu respiración. Es tu ancla. Siempre está aquí.",
    "Inhala tranquilidad... y exhala preocupación.",
    "Siente cómo tu cuerpo se hace más pesado. Más relajado. Más presente.",
    "Quédate aquí un momento. Solo respirando. Solo siendo.",
    "Cuando estés listo, mueve suavemente los dedos. Los pies.",
    "Abre los ojos con calma. Lleva esta paz contigo el resto del día.",
    "Gracias por meditar conmigo. Soy Homero. Hasta la próxima.",
]


# ============================================================================
# GENERADOR OPTIMIZADO
# ============================================================================

class OptimizedHomerGenerator:
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.voice_cast = VoiceCastManager()
        self.enhancer = VoiceFixerEnhancer(cuda=True, mode=0)
        self.xtts = None

    def _get_xtts(self):
        if self.xtts is None:
            profile = self.voice_cast.resolve_voice_for_line("Homero", "homer")
            voice = profile.to_voice()
            self.xtts = XTTSEngine(device="auto")
            self.xtts.load()
        return self.xtts

    def generate_line(self, text: str, output_path: str) -> bool:
        """Generate one line with XTTS + VoiceFixer."""
        try:
            # Generate with XTTS
            profile = self.voice_cast.resolve_voice_for_line("Homero", "homer")
            voice = profile.to_voice()
            tts = self._get_xtts()
            tts.synthesize(text, voice, output_path)

            # Enhance with VoiceFixer
            enhanced = str(Path(output_path).with_suffix(".enhanced.wav"))
            success = self.enhancer.enhance(output_path, enhanced)

            if success and os.path.exists(enhanced):
                shutil.move(enhanced, output_path)
                return True
            else:
                # Fallback: use original
                if os.path.exists(enhanced):
                    os.remove(enhanced)
                return os.path.exists(output_path)
        except Exception as exc:
            print(f"[ERROR] Line generation failed: {exc}")
            return False

    def render_episode(self, lines: list, title: str, filename: str):
        print(f"\n{'='*60}")
        print(f"GENERANDO: {title}")
        print(f"Líneas: {len(lines)}")
        print(f"{'='*60}")

        tmpdir = tempfile.mkdtemp()
        segments = []

        try:
            for i, text in enumerate(lines, 1):
                print(f"[{i}/{len(lines)}] {text[:50]}...")
                line_path = os.path.join(tmpdir, f"line_{i:03d}.wav")

                if not self.generate_line(text, line_path):
                    print(f"  ⚠ Failed, using silence")
                    seg = AudioSegment.silent(duration=1000, frame_rate=44100)
                else:
                    seg = AudioSegment.from_wav(line_path)
                    # VoiceFixer outputs 44.1kHz, keep it
                    seg = seg.set_channels(1)

                # Add pause
                pause = AudioSegment.silent(duration=600, frame_rate=44100)
                segments.append(seg)
                segments.append(pause)

            # Concatenate
            print("\nMezclando audio...")
            final = segments[0]
            for seg in segments[1:]:
                final = final + seg

            # Fade in/out
            final = final.fade_in(500).fade_out(1000)

            # Normalize
            final = final.normalize(headroom=1.0)

            # Export WAV 44.1kHz (máxima calidad)
            wav_path = self.output_dir / f"{filename}.wav"
            final.export(str(wav_path), format="wav")
            print(f"✓ WAV 44.1kHz: {wav_path} ({wav_path.stat().st_size/1024/1024:.1f} MB)")

            # Export MP3 320k
            mp3_path = self.output_dir / f"{filename}.mp3"
            final.export(str(mp3_path), format="mp3", bitrate="320k")
            print(f"✓ MP3 320k: {mp3_path} ({mp3_path.stat().st_size/1024/1024:.1f} MB)")

            # Save script
            script_path = self.output_dir / f"{filename}_script.txt"
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(f"{title}\n\n")
                for i, line in enumerate(lines, 1):
                    f.write(f"{i}. {line}\n")
            print(f"✓ Script: {script_path}")

            return str(mp3_path)

        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def close(self):
        if self.xtts:
            try:
                self.xtts.unload()
            except Exception:
                pass
        self.enhancer.close()


def main():
    print("=" * 60)
    print("GENERADOR HOMERO OPTIMIZADO")
    print("44.1kHz + VoiceFixer + MP3 320k")
    print("=" * 60)

    out_dir = "output/homero_optimizado"
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)

    gen = OptimizedHomerGenerator(out_dir)

    try:
        # Motivation
        gen.render_episode(
            MOTIVATION_LINES,
            "Homero Motiva: Empieza Ahora",
            "motivacion"
        )

        # Meditation
        gen.render_episode(
            MEDITATION_LINES,
            "Homero Medita: Respiración y Paz",
            "meditacion"
        )

        print("\n" + "=" * 60)
        print("RESUMEN")
        print("=" * 60)
        for f in sorted(os.listdir(out_dir)):
            path = Path(out_dir) / f
            if path.is_file():
                size_mb = path.stat().st_size / 1024 / 1024
                print(f"  {f} ({size_mb:.1f} MB)")

        print(f"\n✓ Todo guardado en: {os.path.abspath(out_dir)}")

    finally:
        gen.close()


if __name__ == "__main__":
    main()
