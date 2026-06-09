"""
Demo Fase 4: RSS → News Processor → Agents → Audio

This script demonstrates the full agent-driven news pipeline:
1. Fetch tech news from RSS feeds
2. Process articles through NewsProcessor (which uses AgentOrchestrator)
3. Render multi-voice audio with DramaMixer
4. Add intro/outro with BrandingEngine

For this demo we use MockProvider so it works without API keys.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.llm_provider import MockProvider
from content.rss_fetcher import RSSFetcher
from processors.news_processor import NewsProcessor
from audio.drama_mixer import DramaMixer
from audio.branding_engine import BrandingEngine


def main():
    print("=" * 70)
    print("DEMO FASE 4: RSS → News Processor → Agents → Audio")
    print("=" * 70)

    # ── 1. Fetch RSS articles (or use demo articles if offline) ───────
    print("\n[1] Fetching RSS articles...")
    fetcher = RSSFetcher()

    demo_articles = [
        {
            "title": "NVIDIA presenta nueva arquitectura GPU en Computex 2026",
            "url": "https://example.com/nvidia-computex",
            "description": "La compañía promete el doble de rendimiento por vatio.",
            "content": (
                "NVIDIA presentó en Computex 2026 su nueva arquitectura de GPU. "
                "Según la compañía, los nuevos chips ofrecen el doble de rendimiento por vatio "
                "en comparación con la generación anterior. Esto beneficiará desde laptops gamer "
                "hasta centros de entrenamiento de inteligencia artificial."
            ),
            "source_url": "demo",
            "source": "rss"
        },
        {
            "title": "Apple Intelligence llega a macOS",
            "url": "https://example.com/apple-macos",
            "description": "Nuevas funciones de IA local para escritura, imágenes y Siri.",
            "content": (
                "Apple anunció una actualización importante de macOS que incluye inteligencia artificial local. "
                "Entre las funciones destacan un asistente de escritura, generación de imágenes "
                "y mejoras significativas en Siri. La actualización llegará este otoño."
            ),
            "source_url": "demo",
            "source": "rss"
        },
        {
            "title": "OpenAI lanza preview de GPT-5 para desarrolladores",
            "url": "https://example.com/openai-gpt5",
            "description": "Mejoras en razonamiento y programación según benchmarks iniciales.",
            "content": (
                "OpenAI ha abierto el acceso anticipado a GPT-5 para desarrolladores. "
                "Los primeros benchmarks muestran mejoras significativas en razonamiento "
                "y tareas de programación. La versión final se espera para finales de año."
            ),
            "source_url": "demo",
            "source": "rss"
        }
    ]

    # Try fetching from a real feed; fallback to demo articles
    articles = demo_articles
    try:
        fetched = fetcher.fetch("https://techcrunch.com/feed/", max_articles=3)
        if fetched:
            articles = fetched
            print(f"    ✓ Fetched {len(articles)} articles from TechCrunch")
        else:
            print("    ⚠ No articles fetched, using demo articles")
    except Exception as e:
        print(f"    ⚠ RSS fetch failed: {e}")
        print("    ⚠ Using demo articles")

    # ── 2. Process through NewsProcessor + Agents ────────────────────
    print("\n[2] Processing articles through agent pipeline...")

    mock_responses = {
        "limpiar": json.dumps({
            "title": "Resumen Tech: NVIDIA, Apple y OpenAI",
            "summary": "Tres grandes anuncios marcan la semana tech.",
            "key_points": ["NVIDIA GPU", "Apple IA macOS", "OpenAI GPT-5"],
            "cleaned_text": " ".join(a["content"] for a in articles),
            "language": "es"
        }),
        "escribe": json.dumps({
            "script_text": (
                "PRESENTADOR: Bienvenidos a TechPulse. Hoy repasamos las noticias tech más importantes.\n"
                "PRESENTADORA: Empecemos con NVIDIA. Presentaron una nueva arquitectura de GPU con el doble de rendimiento por vatio.\n"
                "PRESENTADOR: También Apple anunció inteligencia artificial local para macOS, con mejoras en Siri y asistente de escritura.\n"
                "PRESENTADORA: Y OpenAI abrió el preview de GPT-5 para desarrolladores, con mejoras en razonamiento.\n"
                "PRESENTADOR: Mucho movimiento en el mundo tech. Gracias por escucharnos.\n"
                "PRESENTADORA: Hasta la próxima."
            ),
            "scene_notes": [],
            "estimated_duration_minutes": 5.0,
            "content_warnings": []
        }),
        "revisa": json.dumps({
            "improved_script": (
                "PRESENTADOR: Bienvenidos a TechPulse, su resumen tech diario. Hoy repasamos las noticias más importantes de la semana.\n"
                "PRESENTADORA: Empecemos con NVIDIA. La compañía presentó una nueva arquitectura de GPU que promete el doble de rendimiento por vatio.\n"
                "PRESENTADOR: Apple también dio de qué hablar. macOS recibirá inteligencia artificial local, con mejoras en Siri, asistente de escritura y generación de imágenes.\n"
                "PRESENTADORA: Y cerramos con OpenAI, que abrió el preview de GPT-5 para desarrolladores. Los primeros benchmarks muestran mejoras claras en razonamiento y programación.\n"
                "PRESENTADOR: Mucho movimiento en el mundo tecnológico. Gracias por acompañarnos.\n"
                "PRESENTADORA: Hasta la próxima entrega."
            ),
            "changes_made": ["Mejoradas transiciones"],
            "quality_score": 8.5,
            "issues_found": [],
            "suggestions": []
        }),
        "asigna": json.dumps({
            "casting_map": {"PRESENTADOR": "homer", "PRESENTADORA": "dalia"},
            "reasoning": []
        }),
        "metadatos": json.dumps({
            "title": "TechPulse: NVIDIA, Apple y OpenAI",
            "description": "Resumen tech con noticias de NVIDIA, Apple y OpenAI. #tech #podcast",
            "summary": "Noticias tech de NVIDIA, Apple y OpenAI.",
            "tags": ["tech", "nvidia", "apple", "openai", "podcast"],
            "category": "Technology"
        })
    }

    provider = MockProvider(mock_responses)
    processor = NewsProcessor(provider=provider, target_duration_minutes=5.0)

    package = processor.process_articles(articles, episode_number=42, show_title="TechPulse")

    print(f"    ✓ Generated package: {package.package_id}")
    print(f"    ✓ Title: {package.manifest.title}")
    print(f"    ✓ Tags: {', '.join(package.manifest.tags)}")
    print(f"    ✓ Script lines: {len(package.script)}")

    # Save package
    output_dir = Path("media_packages")
    output_dir.mkdir(exist_ok=True)
    pkg_path = package.save(str(output_dir))

    # ── 3. Render audio ──────────────────────────────────────────────
    print("\n[3] Rendering audio with DramaMixer...")
    mixer = DramaMixer()
    main_audio = pkg_path / "assets" / "main_mix.mp3"
    try:
        mixer.mix_package(package, str(main_audio))
        print(f"    ✓ Main audio: {main_audio}")
    finally:
        mixer.close()

    # ── 4. Add branding ──────────────────────────────────────────────
    print("\n[4] Adding intro/outro with BrandingEngine...")
    branding = BrandingEngine()
    final_audio = pkg_path / "assets" / "final_with_branding.mp3"
    try:
        branding.apply_to_package(package, str(main_audio), str(final_audio))
        print(f"    ✓ Final audio: {final_audio}")
        print(f"    ✓ Size: {final_audio.stat().st_size / 1024:.1f} KB")
    finally:
        branding.close()

    print("\n" + "=" * 70)
    print("DEMO FASE 4 COMPLETADO")
    print("=" * 70)


if __name__ == "__main__":
    main()
