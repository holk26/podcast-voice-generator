"""
Demo: Multi-Agent Pipeline → Audio Production

This script demonstrates the full agent-driven pipeline:
1. Raw content → ContentCleanerAgent
2. Cleaned content → ScriptWriterAgent
3. Script → ScriptEditorAgent
4. Characters → CharacterCasterAgent
5. Episode → MetadataAgent
6. MediaPackage → DialogueParser
7. ScriptLines → DramaMixer (audio generation)
8. Audio + BrandingEngine (intro/outro)

For this demo we use MockProvider (deterministic, no API key needed).
To use a real LLM, set OPENAI_API_KEY or ANTHROPIC_API_KEY in your environment.
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.llm_provider import MockProvider
from agents.orchestrator import AgentOrchestrator
from audio.drama_mixer import DramaMixer
from audio.branding_engine import BrandingEngine


RAW_NEWS = """
NVIDIA Announces Next-Gen GPU Architecture at Computex 2026

At Computex 2026, NVIDIA unveiled its next-generation GPU architecture,
promising twice the performance-per-watt of the previous generation.
The new chips will power everything from gaming laptops to AI training clusters.

Apple Intelligence Comes to macOS

Apple announced a major update to macOS featuring on-device AI models
for writing assistance, image generation, and Siri improvements.
The update rolls out this fall to compatible Macs.

OpenAI Releases GPT-5 Developer Preview

OpenAI has opened a developer preview of GPT-5, its latest large language model.
Early benchmarks show significant improvements in reasoning and coding tasks.
"""


def main():
    print("=" * 70)
    print("DEMO: Multi-Agent Pipeline → Audio Production")
    print("=" * 70)

    # ── 1. Agent Pipeline ────────────────────────────────────────────
    print("\n[1] Running AgentOrchestrator on raw content...")

    # Canned mock responses so the demo works without API keys
    mock_responses = {
        "limpiar": json.dumps({
            "title": "Noticias Tech de la Semana",
            "summary": "NVIDIA, Apple y OpenAI anuncian avances importantes.",
            "key_points": [
                "NVIDIA anuncia nueva arquitectura GPU",
                "Apple integra IA en macOS",
                "OpenAI lanza GPT-5 preview"
            ],
            "cleaned_text": (
                "NVIDIA presentó su nueva arquitectura de GPU con el doble de rendimiento. "
                "Apple anunció funciones de inteligencia artificial para macOS. "
                "OpenAI lanzó una versión preview de GPT-5 con mejoras en razonamiento."
            ),
            "language": "es"
        }),
        "escribe": json.dumps({
            "script_text": (
                "PRESENTADOR: ¡Bienvenidos a TechPulse! Hoy tenemos tres noticias tecnológicas importantes.\n"
                "PRESENTADORA: Empecemos con NVIDIA. La compañía acaba de anunciar una nueva arquitectura de GPU con el doble de rendimiento por vatio.\n"
                "PRESENTADOR: Eso es impresionante. Significa laptops de gaming más potentes y clusters de IA más eficientes.\n"
                "PRESENTADORA: Apple también dio de qué hablar. macOS recibirá inteligencia artificial local para asistente de escritura, imágenes y Siri.\n"
                "PRESENTADOR: Y por último, OpenAI abrió el preview de GPT-5 para desarrolladores, con mejoras significativas en razonamiento y programación.\n"
                "PRESENTADORA: Mucho movimiento en el mundo tech. Hasta la próxima.\n"
                "PRESENTADOR: Hasta la próxima."
            ),
            "scene_notes": ["Ambiente de estudio de podcast"],
            "estimated_duration_minutes": 6.0,
            "content_warnings": []
        }),
        "revisa": json.dumps({
            "improved_script": (
                "PRESENTADOR: ¡Bienvenidos a TechPulse! Hoy tenemos tres noticias tecnológicas que no te puedes perder.\n"
                "PRESENTADORA: Empecemos con NVIDIA. La compañía acaba de anunciar una nueva arquitectura de GPU que promete el doble de rendimiento por vatio.\n"
                "PRESENTADOR: Eso es una locura. Significa laptops de gaming mucho más potentes y clusters de entrenamiento de IA mucho más eficientes.\n"
                "PRESENTADORA: Apple también está en la conversación. La próxima versión de macOS incluirá inteligencia artificial local: asistente de escritura, generación de imágenes y una Siri mucho más inteligente.\n"
                "PRESENTADOR: Y cerramos con OpenAI. Ya está disponible el preview de GPT-5 para desarrolladores, y los primeros benchmarks muestran mejoras claras en razonamiento y programación.\n"
                "PRESENTADORA: Mucho movimiento en el mundo tech. Hasta la próxima entrega.\n"
                "PRESENTADOR: Hasta la próxima, amigos."
            ),
            "changes_made": ["Añadí transiciones más naturales", "Mejoré las introducciones de cada noticia"],
            "quality_score": 8.5,
            "issues_found": [],
            "suggestions": []
        }),
        "asigna": json.dumps({
            "casting_map": {
                "PRESENTADOR": "homer",
                "PRESENTADORA": "dalia"
            },
            "reasoning": [
                "Presentador usa la voz principal clonada (homer).",
                "Presentadora usa la voz femenina natural de Dalia."
            ]
        }),
        "metadatos": json.dumps({
            "title": "TechPulse: NVIDIA, Apple y OpenAI",
            "description": (
                "Resumen tech semanal: NVIDIA revela nueva arquitectura GPU, "
                "Apple integra IA en macOS y OpenAI lanza GPT-5 preview. "
                "#tech #nvidia #apple #openai #gpt5 #podcast"
            ),
            "summary": "NVIDIA, Apple y OpenAI: las noticias tech de la semana.",
            "tags": ["tech", "nvidia", "apple", "openai", "gpt5", "inteligencia artificial", "podcast"],
            "category": "Technology"
        })
    }

    provider = MockProvider(mock_responses)
    orchestrator = AgentOrchestrator(provider=provider)

    result = orchestrator.run(
        raw_content=RAW_NEWS,
        source="demo",
        content_type="news",
        episode_number=10,
        target_duration_minutes=6.0
    )

    if not result.success:
        print(f"Agent pipeline failed: {result.error}")
        return

    package = result.data["media_package"]
    casting_map = result.data["casting_map"]
    manifest = result.data["manifest"]

    print(f"\n    ✓ Generated package: {package.package_id}")
    print(f"    ✓ Title: {manifest.title}")
    print(f"    ✓ Description: {manifest.description[:80]}...")
    print(f"    ✓ Tags: {', '.join(manifest.tags)}")
    print(f"    ✓ Casting: {casting_map}")
    print(f"    ✓ Script lines: {len(package.script)}")
    for i, line in enumerate(package.script):
        print(f"      [{i+1}] {line.character} ({line.voice_id}): {line.text[:60]}...")

    # Save package
    output_dir = Path("media_packages")
    output_dir.mkdir(exist_ok=True)
    pkg_path = package.save(str(output_dir))
    print(f"\n    ✓ Package saved to: {pkg_path}")

    # ── 2. Drama Mixer ───────────────────────────────────────────────
    print("\n[2] Rendering multi-voice audio with DramaMixer...")
    mixer = DramaMixer()
    main_audio_path = pkg_path / "assets" / "main_mix.mp3"

    try:
        mixer.mix_package(package, str(main_audio_path))
        print(f"    ✓ Main audio: {main_audio_path}")
        print(f"    ✓ Size: {main_audio_path.stat().st_size / 1024:.1f} KB")
    finally:
        mixer.close()

    # ── 3. Branding Engine ───────────────────────────────────────────
    print("\n[3] Adding intro/outro with BrandingEngine...")
    branding = BrandingEngine()
    final_output = pkg_path / "assets" / "final_with_branding.mp3"

    try:
        branding.apply_to_package(
            package=package,
            main_audio_path=str(main_audio_path),
            output_path=str(final_output)
        )
        print(f"    ✓ Final branded audio: {final_output}")
        print(f"    ✓ Size: {final_output.stat().st_size / 1024:.1f} KB")
    finally:
        branding.close()

    print("\n" + "=" * 70)
    print("AGENT PIPELINE DEMO COMPLETADO")
    print("=" * 70)
    print(f"\nArchivo final: {final_output}")
    print("\nPara usar un LLM real, configura:")
    print("  export OPENAI_API_KEY=sk-...")
    print("  # o")
    print("  export ANTHROPIC_API_KEY=sk-ant-...")


if __name__ == "__main__":
    main()
