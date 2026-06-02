#!/usr/bin/env python3
"""Genera un podcast de prueba usando XTTS v2 en GPU RTX 5060."""
import os
import time
from core.xtts_engine import XTTSEngine
from core.project import Voice

def main():
    output_path = "output/Podcast_Prueba_GPU.mp3"
    os.makedirs("output", exist_ok=True)
    
    # Script de prueba: intro a un podcast de mindfulness
    script = (
        "Bienvenidos a Momentos de Calma. "
        "Soy tu guía en este viaje de cinco minutos hacia la serenidad interior. "
        "Hoy exploraremos la respiración consciente como ancla para el presente. "
        "Siéntate cómodamente, cierra los ojos suavemente, "
        "y deja que cada inhalación te conecte con tu cuerpo, "
        "y cada exhalación libere cualquier tensión acumulada. "
        "Comenzamos."
    )
    
    print("=" * 50)
    print("🎙️ GENERADOR DE PODCAST DE PRUEBA - GPU")
    print("=" * 50)
    
    # Crear motor XTTS en GPU
    print("\n[1/4] Inicializando XTTS v2 en GPU...")
    engine = XTTSEngine(device="cuda")
    print(f"   Dispositivo: {engine.device}")
    
    # Cargar modelo
    print("\n[2/4] Cargando modelo XTTS v2 (~1.9GB)...")
    t0 = time.time()
    engine.load()
    load_time = time.time() - t0
    print(f"   Modelo cargado en {load_time:.1f}s")
    print(f"   Speakers disponibles: {len(engine.get_speakers())}")
    
    # Generar audio
    print("\n[3/4] Generando audio con GPU RTX 5060...")
    voice = Voice(
        id="v1",
        name="Daisy",
        type="pretrained",
        engine="xtts",
        language="es",
        speaker_id="Daisy Studious",
        speed=1.0
    )
    
    t0 = time.time()
    wav_path = engine.synthesize(script, voice, output_path.replace(".mp3", ".wav"))
    gen_time = time.time() - t0
    
    # Convertir a MP3
    print("\n[4/4] Exportando a MP3...")
    from pydub import AudioSegment
    audio = AudioSegment.from_wav(wav_path)
    audio.export(output_path, format="mp3", bitrate="192k")
    os.remove(wav_path)
    
    # Estadísticas
    file_size = os.path.getsize(output_path)
    duration_sec = len(audio) / 1000
    rtf = gen_time / duration_sec
    
    print("\n" + "=" * 50)
    print("✅ PODCAST GENERADO EXITOSAMENTE")
    print("=" * 50)
    print(f"📁 Archivo: {output_path}")
    print(f"⏱️  Duración: {duration_sec:.1f}s")
    print(f"⚡ Tiempo de generación: {gen_time:.1f}s")
    print(f"📈 Real-Time Factor: {rtf:.2f}x")
    print(f"💾 Tamaño: {file_size / 1024:.1f} KB")
    print(f"🎛️  Calidad: MP3 192kbps, {audio.frame_rate}Hz")
    print(f"🎮 GPU: NVIDIA GeForce RTX 5060")
    print("=" * 50)

if __name__ == "__main__":
    main()
