"""
Demo Fase 5: Pipeline Orchestrator — end-to-end episode generation.

This demo shows how a single EpisodeConfig drives the entire pipeline:
  config → fetch → agents → mix → brand → package

Uses MockProvider for deterministic agent responses (no LLM API needed).
"""

import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.pipeline_orchestrator import PipelineOrchestrator, EpisodeConfig
from agents.llm_provider import MockProvider


def demo_news_pipeline():
    print("=" * 70)
    print("DEMO FASE 5: Pipeline Orchestrator — News Episode")
    print("=" * 70)

    config = EpisodeConfig(
        episode_type="news",
        title="TechPulse",
        sources=[
            {
                "type": "rss",
                "url": "https://techcrunch.com/feed/",
                "max_articles": 2
            }
        ],
        target_duration_minutes=5.0,
        host_voice_id="homer",
        intro_music="intro_jingle",
        outro_music="outro_theme",
        branding_enabled=True,
        episode_number=99,
        output_dir="media_packages"
    )

    provider = MockProvider()
    pipeline = PipelineOrchestrator(config, provider=provider)

    print("\n[1] Running full pipeline...")
    result = pipeline.run()

    if result.success:
        print(f"\n[2] Pipeline completed successfully!")
        print(f"    Package ID: {result.media_package.package_id}")
        print(f"    Title: {result.media_package.manifest.title}")
        print(f"    Duration: {result.media_package.manifest.duration_seconds}s")
        print(f"    Final audio: {result.final_audio_path}")
        print(f"    Logs:")
        for log in result.logs:
            status = "✓" if log["success"] else "✗"
            print(f"      {status} {log['step']}: {log.get('path', log.get('package_id', ''))}")
    else:
        print(f"\n[2] Pipeline failed: {result.error}")
        for log in result.logs:
            print(f"    {log['step']}: success={log['success']}")

    print("\n" + "=" * 70)
    print("DEMO FASE 5 COMPLETADO")
    print("=" * 70)
    return result


def demo_meditation_pipeline():
    print("\n" + "=" * 70)
    print("DEMO FASE 5: Pipeline Orchestrator — Meditation Episode")
    print("=" * 70)

    config = EpisodeConfig(
        episode_type="meditation",
        title="Meditación Diaria",
        target_duration_minutes=3.0,
        host_voice_id="elvira",
        branding_enabled=True,
        output_dir="media_packages",
        processor_options={
            "topic": "respiración",
            "seed": 42
        }
    )

    provider = MockProvider()
    pipeline = PipelineOrchestrator(config, provider=provider)

    print("\n[1] Running meditation pipeline...")
    result = pipeline.run()

    if result.success:
        print(f"\n[2] Meditation pipeline completed!")
        print(f"    Package: {result.media_package.package_id}")
        print(f"    Title: {result.media_package.manifest.title}")
        print(f"    Audio: {result.final_audio_path}")
    else:
        print(f"\n[2] Failed: {result.error}")

    print("\n" + "=" * 70)
    print("MEDITATION DEMO COMPLETADO")
    print("=" * 70)
    return result


if __name__ == "__main__":
    # Run news demo (uses real RSS + Mock agents)
    news_result = demo_news_pipeline()

    # Run meditation demo (template-based, no network)
    meditation_result = demo_meditation_pipeline()

    print("\n\nRESUMEN:")
    print(f"  News:      {'OK' if news_result.success else 'FAIL'}")
    print(f"  Meditation: {'OK' if meditation_result.success else 'FAIL'}")
