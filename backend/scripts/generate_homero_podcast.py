#!/usr/bin/env python3
"""Genera un podcast con la voz de Homero usando XTTS v2."""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.project import Project, Voice, Section
from core.xtts_engine import XTTSEngine
from core.audio_pipeline import AudioPipeline
from core.batch_generator import BatchGenerator
from utils.config_manager import ConfigManager
from datetime import datetime


def main():
    print("=" * 60)
    print("Generando podcast con la voz de Homero")
    print("=" * 60)

    # Load project
    project_path = "projects/homero.json"
    if os.path.exists(project_path):
        project = Project.load(project_path)
        print(f"Proyecto cargado: {project.name}")
    else:
        project = Project(name="homero")
        print("Nuevo proyecto creado: homero")

    # Add Homero voice
    ref_path = os.path.abspath("voices/clones/mi_voz-homero.wav")
    if not os.path.exists(ref_path):
        print(f"ERROR: No se encuentra el audio de referencia: {ref_path}")
        print("Graba tu voz primero usando la app (pestaña Voces > Grabar mi voz)")
        return

    # Remove existing voices
    project.voices = []

    voice = Voice(
        id="homero",
        name="Homero",
        type="cloned",
        engine="xtts",
        language="es",
        reference_path=ref_path,
        speed=1.0
    )
    project.add_voice(voice)
    print(f"Voz añadida: {voice.name} (referencia: {ref_path})")

    # Clear sections and add new content
    project.sections = []

    secciones = [
        ("Introducción",
         "¡Hola, hola! Bienvenidos a Tech Pulse, su resumen de noticias tecnológicas. "
         "Hoy es martes, dos de junio de dos mil veintiséis. Soy Homero y estoy muy emocionado de estar aquí con ustedes. "
         "¡Así que pongan atención porque tenemos mucho que contar!"),

        ("Microsoft Build 2026",
         "Empezamos con Microsoft Build 2026, que está arrancando en San Francisco. "
         "El eje central es la inteligencia artificial agente. "
         "Microsoft presentó Scout, un asistente personal que integra Outlook, OneDrive y Teams. "
         "Puede organizar calendarios, redactar correos e incluso hacer llamadas telefónicas. "
         "¡Imagínense, un asistente que hace todo por nosotros!"),

        ("Hardware de Microsoft",
         "En hardware, Microsoft lanzó la Surface RTX Spark Dev Box. "
         "Una mini PC con el nuevo chip de Nvidia y ciento veintiocho gigabytes de memoria unificada. "
         "También presentaron Majorana Dos, su nuevo procesador cuántico. "
         "Los cúbits son mil veces más fiables que los de la generación anterior. "
         "¡La tecnología avanza a pasos agigantados!"),

        ("Nvidia RTX Spark",
         "Del lado de Nvidia, Jensen Huang confirmó que llevan tres años trabajando con Microsoft en el chip RTX Spark. "
         "Promete un petaflop de rendimiento de inteligencia artificial. "
         "Esto es una locura, amigos. Un petaflop en una sola máquina. "
         "Los desarrolladores van a poder hacer cosas increíbles con esto."),

        ("Google Fotos IA",
         "Google lanza un armario digital generado por inteligencia artificial en Google Fotos. "
         "Analiza tus imágenes para crear combinaciones de ropa virtuales. "
         "Ahora tu teléfono será tu propio estilista personal. "
         "Yo la verdad soy más de camiseta y jeans, pero bueno, ¡para los fashionistas está genial!"),

        ("OpenAI Codex",
         "OpenAI anunció que Codex, su agente de programación, ya cuenta con cinco millones de usuarios semanales. "
         "Cinco millones de personas programando con ayuda de inteligencia artificial. "
         "El futuro del código está cambiando frente a nuestros ojos."),

        ("Apple WWDC 2026",
         "Apple se prepara para su WWDC 2026. "
         "Se esperan iOS veintisiete y una versión conversacional de Siri que competiría con ChatGPT. "
         "Finalmente Siri va a poder tener una conversación decente con nosotros. "
         "¡Ya era hora, Apple!"),

        ("Despedida",
         "Eso es todo por hoy en Tech Pulse. "
         "Si te ha gustado este episodio, compártelo con tus amigos. "
         "Yo soy Homero y nos escuchamos en el próximo episodio. "
         "¡Hasta la próxima, y que la tecnología los acompañe!"),
    ]

    for titulo, texto in secciones:
        project.add_section(
            title=titulo,
            text=texto,
            voice_id="homero",
            speed=1.0,
            pause_after_ms=500
        )

    print(f"Secciones añadidas: {len(project.sections)}")

    # Save project
    project.save(project_path)
    print(f"Proyecto guardado: {project_path}")

    # Setup engines
    cm = ConfigManager()
    device = cm.get("gpu.device", "auto")
    print(f"\nConfigurando XTTS v2 en dispositivo: {device}")

    xtts = XTTSEngine(device=device)
    pipeline = AudioPipeline(output_dir="output")
    generator = BatchGenerator(pipeline=pipeline)
    generator.register_engine("xtts", xtts)

    # Generate
    generator.add_project(project)
    print(f"\nGenerando {len(project.sections)} secciones...\n")

    def progress(current, total, msg):
        pct = int(100 * current / total)
        bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
        print(f"\r[{bar}] {current}/{total} — {msg}", end="", flush=True)

    generator.set_progress_callback(progress)
    results = generator.run(project)
    print()

    # Report
    completed = sum(1 for r in results if r.status == "completed")
    failed = sum(1 for r in results if r.status == "failed")
    print(f"\n{'=' * 60}")
    print(f"Resultado: {completed} completadas, {failed} fallidas")

    if completed > 0:
        # Mix all sections into one podcast file
        print("\nMezclando secciones en podcast final...")
        import numpy as np
        import soundfile as sf

        all_audio = []
        sample_rate = 24000

        for section in project.sections:
            output_file = project.generation_state["output_files"].get(section.id)
            if output_file and os.path.exists(output_file):
                audio, sr = sf.read(output_file, dtype=np.float32)
                if audio.ndim > 1:
                    audio = audio.mean(axis=1)
                if sr != sample_rate:
                    import resampy
                    audio = resampy.resample(audio, sr, sample_rate)
                all_audio.append(audio)
                # Add 0.8s silence between sections
                all_audio.append(np.zeros(int(sample_rate * 0.8), dtype=np.float32))

        if all_audio:
            final_audio = np.concatenate(all_audio)
            wav_path = "output/podcast_homero_techpulse.wav"
            mp3_path = "output/podcast_homero_techpulse.mp3"
            sf.write(wav_path, final_audio, sample_rate)
            try:
                from pydub import AudioSegment
                audio = AudioSegment.from_wav(wav_path)
                audio.export(mp3_path, format="mp3", bitrate="192k")
                os.remove(wav_path)
                final_path = mp3_path
            except Exception:
                final_path = wav_path
            duration = len(final_audio) / sample_rate
            size_mb = os.path.getsize(final_path) / (1024 * 1024)
            print(f">> Podcast final generado: {final_path}")
            print(f"   Duración: {duration:.1f} segundos ({duration / 60:.1f} minutos)")
            print(f"   Tamaño: {size_mb:.1f} MB")
    project.save(project_path)
    print(f"\nProyecto actualizado: {project_path}")


if __name__ == "__main__":
    main()
