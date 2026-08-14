#!/usr/bin/env python3
"""
Demo 100% funcional: Genera un mini-podcast con Edge TTS + DramaMixer.
No requiere descargar modelos grandes. Funciona inmediatamente.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.media_package import MediaPackage, ScriptLine, Manifest
from cast.voice_cast_manager import VoiceCastManager, VoiceProfile
from audio.drama_mixer import DramaMixer


def main():
    os.makedirs("output/demo_funcional", exist_ok=True)

    # Configurar voces
    voice_cast = VoiceCastManager()
    voice_cast.register_profile(VoiceProfile(
        voice_id="homero",
        name="Homero",
        engine="edge_tts",
        language="es",
        speaker_id="es-MX-JorgeNeural",
        speed=1.0,
    ))
    voice_cast.register_profile(VoiceProfile(
        voice_id="narrador",
        name="Narrador",
        engine="edge_tts",
        language="es",
        speaker_id="es-ES-AlvaroNeural",
        speed=0.95,
    ))

    # Crear el script como líneas de diálogo
    lines = [
        ScriptLine(
            character="homero",
            text="¡Hola a todos! Bienvenidos a TechPulse, el podcast donde la tecnología se encuentra con el humor.",
            voice_id="homero",
            pause_before_ms=0,
            pause_after_ms=500,
        ),
        ScriptLine(
            character="narrador",
            text="Hoy hablaremos sobre los últimos avances en inteligencia artificial.",
            voice_id="narrador",
            pause_before_ms=0,
            pause_after_ms=500,
        ),
        ScriptLine(
            character="homero",
            text="¿Sabían que ahora hay modelos de voz tan avanzados que parecen humanos reales? ¡Aunque algunos todavía suenan peor que yo después de tres cervezas!",
            voice_id="homero",
            pause_before_ms=0,
            pause_after_ms=500,
        ),
        ScriptLine(
            character="narrador",
            text="Homero tiene razón. Los modelos de texto a voz han evolucionado enormemente en 2026.",
            voice_id="narrador",
            pause_before_ms=0,
            pause_after_ms=500,
        ),
        ScriptLine(
            character="homero",
            text="Yo personalmente prefiero los que funcionan en mi laptop. Nada de modelos de 20 gigabytes que ni siquiera caben en mi GPU.",
            voice_id="homero",
            pause_before_ms=0,
            pause_after_ms=500,
        ),
        ScriptLine(
            character="narrador",
            text="Y hablando de eso... este demo fue generado completamente con Edge TTS y el pipeline de producción de podcast.",
            voice_id="narrador",
            pause_before_ms=0,
            pause_after_ms=500,
        ),
        ScriptLine(
            character="homero",
            text="¡Nos escuchamos en el próximo episodio! Y recuerden: si algo no funciona, reinícielenlo tres veces antes de llorar.",
            voice_id="homero",
            pause_before_ms=0,
            pause_after_ms=0,
        ),
    ]

    # Crear MediaPackage
    manifest = Manifest(
        title="TechPulse Demo",
        description="Demo funcional del pipeline de podcast",
        language="es-ES",
    )
    
    package = MediaPackage(
        package_id="demo_funcional",
        script=lines,
        manifest=manifest,
    )

    print("=" * 60)
    print("🎙️  DEMO FUNCIONAL - Mini Podcast con Edge TTS")
    print("=" * 60)
    print("\nEste demo funciona SIN descargar modelos grandes.")
    print("Usa Edge TTS (Microsoft) via internet + el pipeline local.\n")

    mixer = DramaMixer(voice_cast=voice_cast)
    
    print("🎬 Renderizando mini podcast...")
    output_path = "output/demo_funcional/mini_podcast_demo.mp3"
    mixer.mix_package(package, output_path, keep_line_files=False)
    
    print(f"\n✅ ¡Listo! Archivo generado: {output_path}")
    print(f"📁 Tamaño: {os.path.getsize(output_path) / 1024 / 1024:.1f} MB")
    
    mixer.close()
    
    print("\n" + "=" * 60)
    print("🚀 PIPELINE COMPLETO FUNCIONANDO")
    print("=" * 60)
    print("""
El pipeline completo está operativo:
  ✅ Edge TTS (voz online)
  ✅ DramaMixer (mezcla dramatizada)
  ✅ Efectos de audio (silencios, transiciones)
  ✅ Exportación MP3

Para usar modelos locales más avanzados:
  • Orpheus TTS 3B → ~6GB, funciona en tu 8GB VRAM
  • Higgs Audio v3 → ~9GB, REQUIERE 12GB+ VRAM (no cabe en tu GPU)
  • XTTS v2 → ~2GB, clonación de voz

Ejecuta el demo de Orpheus cuando termine de descargar:
  venv311/bin/python scripts/generate_orpheus_demo.py
    """)


if __name__ == "__main__":
    main()
