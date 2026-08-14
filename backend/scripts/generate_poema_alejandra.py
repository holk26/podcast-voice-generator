"""
Genera un poema de amor para Alejandra, leído por Homero con voz mejorada.
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
from core.xtts_engine import XTTSEngine


POEMA = [
    "Alejandra.",
    "Mi amor.",
    "Mi compañera.",
    "Mi mejor amiga.",
    "",
    "Desde que llegaste a mi vida,",
    "todo cambió.",
    "Las mañanas son más brillantes.",
    "Las noches, más cálidas.",
    "Y cada respiración mía,",
    "lleva tu nombre escondido.",
    "",
    "No hay palabra que sea suficiente,",
    "para describir lo que siento.",
    "Pero si hay algo que quiero que sepas,",
    "es esto.",
    "",
    "Te elijo todos los días.",
    "En los buenos momentos.",
    "Y en los difíciles.",
    "En la salud.",
    "Y en la enfermedad.",
    "Con risas.",
    "Y con lágrimas.",
    "",
    "Eres mi hogar.",
    "Mi paz.",
    "Mi razón para ser mejor.",
    "",
    "Alejandra.",
    "Eres el amor de mi vida.",
    "Hoy.",
    "Mañana.",
    "Y siempre.",
    "",
    "Con todo mi corazón.",
    "Tu Homero.",
]


def main():
    print("=" * 60)
    print("POEMA DE AMOR PARA ALEJANDRA")
    print("Voz: Homero mejorada (VoiceFixer + 44.1kHz)")
    print("=" * 60)

    out_dir = "output/poema_para_alejandra"
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir, exist_ok=True)

    voice_cast = VoiceCastManager()
    enhancer = VoiceFixerEnhancer(cuda=True, mode=0)
    xtts = XTTSEngine(device="auto")
    xtts.load()

    profile = voice_cast.resolve_voice_for_line("Homero", "homer")
    voice = profile.to_voice()

    tmpdir = tempfile.mkdtemp()
    segments = []

    try:
        for i, text in enumerate(POEMA, 1):
            if not text.strip():
                # Silence for empty lines (pause)
                seg = AudioSegment.silent(duration=1200, frame_rate=44100)
                segments.append(seg)
                continue

            print(f"[{i}/{len(POEMA)}] {text}")
            line_path = os.path.join(tmpdir, f"line_{i:03d}.wav")

            # Generate with XTTS
            xtts.synthesize(text, voice, line_path)

            # Enhance with VoiceFixer
            enhanced = str(Path(line_path).with_suffix(".enhanced.wav"))
            success = enhancer.enhance(line_path, enhanced)

            if success and os.path.exists(enhanced):
                shutil.move(enhanced, line_path)

            seg = AudioSegment.from_wav(line_path)
            seg = seg.set_channels(1)

            # Pause after each line
            pause = AudioSegment.silent(duration=700, frame_rate=44100)
            segments.append(seg)
            segments.append(pause)

        print("\nMezclando audio...")
        final = segments[0]
        for seg in segments[1:]:
            final = final + seg

        final = final.fade_in(800).fade_out(1500)
        final = final.normalize(headroom=1.0)

        # Export
        wav_path = os.path.join(out_dir, "poema_alejandra.wav")
        mp3_path = os.path.join(out_dir, "poema_alejandra.mp3")

        final.export(wav_path, format="wav")
        final.export(mp3_path, format="mp3", bitrate="320k")

        # Save text
        text_path = os.path.join(out_dir, "poema.txt")
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write("Poema de amor para Alejandra\n")
            f.write("Leído por Homero\n\n")
            for line in POEMA:
                f.write(line + "\n")

        print(f"\n✓ WAV: {wav_path} ({os.path.getsize(wav_path)/1024/1024:.1f} MB)")
        print(f"✓ MP3: {mp3_path} ({os.path.getsize(mp3_path)/1024/1024:.1f} MB)")
        print(f"✓ Texto: {text_path}")

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
        xtts.unload()
        enhancer.close()

    print(f"\n💝 Todo guardado en: {os.path.abspath(out_dir)}")


if __name__ == "__main__":
    main()
