"""
Demo Fase 6: Episode Queue + Review Tool

Shows the full lifecycle:
  1. Enqueue episodes
  2. Simulate pipeline run (rendering → review)
  3. Reviewer inspects, edits metadata, approves/rejects
  4. Dashboard stats
"""

import sys
import os
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.episode_queue import EpisodeQueue, QueuedEpisode
from core.review_tool import ReviewTool


def demo_queue_lifecycle():
    tmpdir = tempfile.mkdtemp()
    queue_file = os.path.join(tmpdir, "queue.json")

    print("=" * 70)
    print("DEMO FASE 6: Episode Queue + Review Tool")
    print("=" * 70)

    # ------------------------------------------------------------------
    # 1. Create queue and enqueue episodes
    # ------------------------------------------------------------------
    print("\n[1] Creating queue and enqueueing episodes...")
    queue = EpisodeQueue(queue_file=queue_file)

    ep1 = queue.enqueue(
        config={"episode_type": "news", "title": "TechPulse #100", "sources": []},
        priority=10
    )
    ep2 = queue.enqueue(
        config={"episode_type": "meditation", "title": "Meditación: Paz", "sources": []},
        priority=5
    )
    ep3 = queue.enqueue(
        config={"episode_type": "news", "title": "TechPulse #101", "sources": []},
        priority=10
    )

    print(f"    Enqueued: {ep1.episode_id} (priority {ep1.priority})")
    print(f"    Enqueued: {ep2.episode_id} (priority {ep2.priority})")
    print(f"    Enqueued: {ep3.episode_id} (priority {ep3.priority})")

    # ------------------------------------------------------------------
    # 2. Simulate pipeline processing
    # ------------------------------------------------------------------
    print("\n[2] Simulating pipeline processing...")

    # Pick next pending (highest priority, oldest first)
    next_ep = queue.get_next_pending()
    print(f"    Next pending: {next_ep.episode_id} — {next_ep.config['title']}")
    queue.update_status(next_ep.episode_id, "rendering")
    print(f"    → status: rendering")

    # Simulate finish render
    fake_pkg_dir = os.path.join(tmpdir, next_ep.episode_id)
    os.makedirs(fake_pkg_dir, exist_ok=True)
    fake_audio = os.path.join(fake_pkg_dir, "final.mp3")
    with open(fake_audio, "w") as f:
        f.write("fake audio data")

    queue.update_status(
        next_ep.episode_id,
        "review",
        media_package_path=fake_pkg_dir,
        final_audio_path=fake_audio
    )
    print(f"    → status: review (audio ready)")

    # ------------------------------------------------------------------
    # 3. Review workflow
    # ------------------------------------------------------------------
    print("\n[3] Review workflow...")
    review = ReviewTool(queue)

    # Stats before review
    stats = review.get_stats()
    print(f"    Dashboard: {stats['counts']}")
    print(f"    Pending review: {stats['pending_review_count']}")

    # Preview audio
    audio_path = review.preview_audio(next_ep.episode_id)
    print(f"    Preview audio: {audio_path}")

    # Edit metadata
    # Create a fake package so edit_metadata works
    from core.media_package import MediaPackage, Manifest
    pkg = MediaPackage(package_id=next_ep.episode_id, manifest=Manifest(title="Old Title"))
    pkg.save(fake_pkg_dir)

    updated_pkg = review.edit_metadata(
        next_ep.episode_id,
        title="TechPulse #100: La IA Revolution",
        description="Resumen tech semanal con noticias de IA."
    )
    print(f"    Metadata updated: title='{updated_pkg.manifest.title}'")
    print(f"    Description: {updated_pkg.manifest.description}")

    # Approve
    approved = review.approve(next_ep.episode_id, notes="Excelente episodio, listo para publicar.")
    print(f"    → Approved! Notes: {approved.review_notes}")

    # Reject another one
    queue.update_status(ep2.episode_id, "review")
    rejected = review.reject(ep2.episode_id, reason="Audio con ruido de fondo, regenerar.")
    print(f"    → Rejected: {rejected.episode_id}, reason: {rejected.review_notes}")

    # Request revision on the rejected one
    revised = review.request_revision(
        ep2.episode_id,
        instructions="Regenerar con parámetros de ruido reducido."
    )
    print(f"    → Back to pending: {revised.episode_id}")

    # ------------------------------------------------------------------
    # 4. Final stats
    # ------------------------------------------------------------------
    print("\n[4] Final queue status...")
    stats = review.get_stats()
    print(f"    Total episodes: {stats['total']}")
    print(f"    Counts: {stats['counts']}")
    print(f"    Next to publish: {stats['next_to_publish']}")
    print(f"    Next for review: {stats['next_for_review']}")

    for status in queue.VALID_STATUSES:
        eps = queue.list_by_status(status)
        if eps:
            print(f"\n    [{status.upper()}]")
            for ep in eps:
                print(f"      - {ep.episode_id}: {ep.config.get('title', 'Untitled')}")

    # Cleanup
    shutil.rmtree(tmpdir, ignore_errors=True)

    print("\n" + "=" * 70)
    print("DEMO FASE 6 COMPLETADO")
    print("=" * 70)


if __name__ == "__main__":
    demo_queue_lifecycle()
