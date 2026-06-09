"""
Demo Fase 8: MediaAutomationPlatform — Full End-to-End Integration

Demonstrates the complete lifecycle using the unified platform interface:
  1. Submit episodes
  2. Run pipeline (mock provider for speed)
  3. Review and approve
  4. Schedule future episodes
  5. Auto-publish
  6. Dashboard overview
"""

import sys
import os
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.platform import MediaAutomationPlatform, Dashboard
from core.pipeline_orchestrator import EpisodeConfig
from publishers.file_publisher import FilePublisher
from agents.llm_provider import MockProvider


def demo_platform():
    tmpdir = tempfile.mkdtemp()
    print("=" * 70)
    print("DEMO FASE 8: MediaAutomationPlatform — End-to-End")
    print("=" * 70)

    # ------------------------------------------------------------------
    # Initialize platform
    # ------------------------------------------------------------------
    platform = MediaAutomationPlatform(
        data_dir=os.path.join(tmpdir, "data"),
        publishers=[FilePublisher(output_dir=os.path.join(tmpdir, "published"))],
        provider=MockProvider()
    )
    print(f"\n[1] Platform initialized")
    print(f"    Data dir: {tmpdir}/data")

    # ------------------------------------------------------------------
    # Submit episodes
    # ------------------------------------------------------------------
    print("\n[2] Submitting episodes...")

    ep1 = platform.submit(EpisodeConfig(
        episode_type="raw",
        title="Episodio de Prueba 1",
        sources=[{"content": "Bienvenidos al podcast de prueba. Este es un episodio corto."}],
        target_duration_minutes=1.0,
        branding_enabled=False
    ), priority=10)

    ep2 = platform.submit(EpisodeConfig(
        episode_type="raw",
        title="Episodio de Prueba 2",
        sources=[{"content": "Segundo episodio para demostración del pipeline completo."}],
        target_duration_minutes=1.0,
        branding_enabled=False
    ), priority=5)

    print(f"    Submitted: {ep1.episode_id} (priority {ep1.priority})")
    print(f"    Submitted: {ep2.episode_id} (priority {ep2.priority})")

    # ------------------------------------------------------------------
    # Dashboard before processing
    # ------------------------------------------------------------------
    print("\n[3] Dashboard (before processing)...")
    dash = platform.get_dashboard()
    print(f"    Total: {dash.total_episodes}")
    print(f"    By status: {dash.by_status}")

    # ------------------------------------------------------------------
    # Run pipeline for pending episodes
    # ------------------------------------------------------------------
    print("\n[4] Running pipelines...")

    result1 = platform.run_pipeline(ep1.episode_id)
    print(f"    {ep1.episode_id}: {'OK' if result1.success else 'FAIL'}")
    if result1.success:
        print(f"      → Audio: {result1.final_audio_path}")

    result2 = platform.run_pipeline(ep2.episode_id)
    print(f"    {ep2.episode_id}: {'OK' if result2.success else 'FAIL'}")

    # ------------------------------------------------------------------
    # Review workflow
    # ------------------------------------------------------------------
    print("\n[5] Review workflow...")

    # Edit metadata on ep1
    platform.edit_metadata(ep1.episode_id, title="Episodio de Prueba 1 — Editado")
    print(f"    Edited metadata for {ep1.episode_id}")

    # Approve both
    platform.approve(ep1.episode_id, notes="Perfecto para publicar.")
    platform.approve(ep2.episode_id, notes="Listo.")
    print(f"    Approved both episodes")

    # Reject and revision demo
    ep3 = platform.submit_raw(
        title="Episodio Problemático",
        content="Contenido con errores.",
        branding_enabled=False
    )
    platform.run_pipeline(ep3.episode_id)
    platform.reject(ep3.episode_id, reason="Calidad de audio insuficiente.")
    print(f"    Rejected {ep3.episode_id}")

    # ------------------------------------------------------------------
    # Scheduling
    # ------------------------------------------------------------------
    print("\n[6] Scheduling...")

    from datetime import datetime, timedelta
    future = (datetime.now() + timedelta(days=1)).isoformat()
    job = platform.schedule(
        EpisodeConfig(
            episode_type="raw",
            title="Episodio Programado",
            sources=[{"content": "Contenido para mañana."}],
            branding_enabled=False
        ),
        when=future,
        recurrence="daily"
    )
    print(f"    Scheduled daily job: {job.schedule_id}")
    print(f"    Next run: {job.next_run}")

    # ------------------------------------------------------------------
    # Auto-publish approved
    # ------------------------------------------------------------------
    print("\n[7] Auto-publishing approved episodes...")
    pub_results = platform.auto_publish()
    for i, r in enumerate(pub_results):
        status = "✓" if r.success else "✗"
        print(f"    {status} Publish {i+1}: {r.published_path or r.error}")

    # ------------------------------------------------------------------
    # Final dashboard
    # ------------------------------------------------------------------
    print("\n[8] Final dashboard...")
    dash = platform.get_dashboard()
    print(f"    Total episodes: {dash.total_episodes}")
    print(f"    By status: {dash.by_status}")
    print(f"    Pending review: {dash.pending_review}")
    print(f"    Approved: {dash.approved}")
    print(f"    Published: {dash.published}")
    print(f"    Scheduled jobs: {dash.scheduled_jobs}")
    print(f"    Upcoming jobs: {dash.upcoming_jobs}")

    # ------------------------------------------------------------------
    # Tick demo (scheduler + pipeline + publish in one call)
    # ------------------------------------------------------------------
    print("\n[9] Running platform.tick()...")
    tick_result = platform.tick()
    print(f"    Scheduled enqueued: {tick_result['scheduled_enqueued']}")
    print(f"    Pipeline result: {tick_result['pipeline_result']}")
    print(f"    Published: {len(tick_result['published'])}")

    # Cleanup
    shutil.rmtree(tmpdir, ignore_errors=True)

    print("\n" + "=" * 70)
    print("DEMO FASE 8 COMPLETADO")
    print("=" * 70)


if __name__ == "__main__":
    demo_platform()
