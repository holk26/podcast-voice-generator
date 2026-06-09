"""
Demo Fase 7: Publishing + Scheduling

Shows:
  1. FilePublisher and RSSPublisher publish approved episodes
  2. EpisodeScheduler schedules future generation
  3. AutoPublisher publishes approved episodes automatically
  4. Tick executes overdue scheduled jobs
"""

import sys
import os
import tempfile
import shutil
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.episode_queue import EpisodeQueue
from core.scheduler import EpisodeScheduler, AutoPublisher
from publishers.file_publisher import FilePublisher
from publishers.rss_publisher import RSSPublisher, RSSFeedConfig


def demo_publishing():
    tmpdir = tempfile.mkdtemp()
    queue_file = os.path.join(tmpdir, "queue.json")

    print("=" * 70)
    print("DEMO FASE 7: Publishing + Scheduling")
    print("=" * 70)

    # ------------------------------------------------------------------
    # Setup queue with approved episodes
    # ------------------------------------------------------------------
    queue = EpisodeQueue(queue_file=queue_file)

    # Create fake audio files
    ep1_dir = os.path.join(tmpdir, "ep1")
    ep2_dir = os.path.join(tmpdir, "ep2")
    os.makedirs(ep1_dir, exist_ok=True)
    os.makedirs(ep2_dir, exist_ok=True)

    audio1 = os.path.join(ep1_dir, "final.mp3")
    audio2 = os.path.join(ep2_dir, "final.mp3")
    with open(audio1, "w") as f:
        f.write("fake audio 1")
    with open(audio2, "w") as f:
        f.write("fake audio 2")

    ep1 = queue.enqueue(config={"title": "TechPulse #200", "episode_type": "news"})
    queue.update_status(ep1.episode_id, "approved", final_audio_path=audio1)

    ep2 = queue.enqueue(config={"title": "Meditación: Mañana", "episode_type": "meditation"})
    queue.update_status(ep2.episode_id, "approved", final_audio_path=audio2)

    print(f"\n[1] Created 2 approved episodes")

    # ------------------------------------------------------------------
    # FilePublisher
    # ------------------------------------------------------------------
    print("\n[2] FilePublisher...")
    file_pub = FilePublisher(output_dir=os.path.join(tmpdir, "published_files"))
    result1 = file_pub.publish(ep1)
    result2 = file_pub.publish(ep2)

    print(f"    Episode 1: {'OK' if result1.success else 'FAIL'}")
    if result1.success:
        print(f"      → {result1.published_path}")
    print(f"    Episode 2: {'OK' if result2.success else 'FAIL'}")
    if result2.success:
        print(f"      → {result2.published_path}")

    # ------------------------------------------------------------------
    # RSSPublisher
    # ------------------------------------------------------------------
    print("\n[3] RSSPublisher...")
    rss_pub = RSSPublisher(
        output_dir=os.path.join(tmpdir, "published_rss"),
        feed_config=RSSFeedConfig(
            title="Mi Podcast Automático",
            description="Generado con Media Automation Platform",
            link="https://mipodcast.example.com",
            author="Media Bot"
        ),
        base_url="https://mipodcast.example.com"
    )
    result3 = rss_pub.publish(ep1)
    result4 = rss_pub.publish(ep2)

    print(f"    Episode 1 RSS: {'OK' if result3.success else 'FAIL'}")
    if result3.success:
        print(f"      → Feed: {result3.published_path}")
    print(f"    Episode 2 RSS: {'OK' if result4.success else 'FAIL'}")

    # Show feed content
    feed_path = os.path.join(tmpdir, "published_rss", "feed.xml")
    if os.path.exists(feed_path):
        with open(feed_path, "r") as f:
            content = f.read()
        print(f"    Feed size: {len(content)} bytes")
        if "TechPulse #200" in content:
            print("    ✓ Feed contains episode titles")

    # ------------------------------------------------------------------
    # EpisodeScheduler
    # ------------------------------------------------------------------
    print("\n[4] EpisodeScheduler...")
    scheduler = EpisodeScheduler(queue, schedule_file=os.path.join(tmpdir, "schedule.json"))

    # Schedule a one-shot job in the past (so tick will pick it up)
    past = (datetime.now() - timedelta(minutes=5)).isoformat()
    job1 = scheduler.schedule(
        config={"episode_type": "news", "title": "Scheduled News"},
        when=past
    )
    print(f"    Scheduled one-shot (past): {job1.schedule_id}")

    # Schedule a daily recurring job
    future = (datetime.now() + timedelta(hours=2)).isoformat()
    job2 = scheduler.schedule(
        config={"episode_type": "meditation", "title": "Daily Meditation"},
        when=future,
        recurrence="daily"
    )
    print(f"    Scheduled daily (future): {job2.schedule_id}")

    # List upcoming
    upcoming = scheduler.list_upcoming()
    print(f"    Upcoming jobs: {len(upcoming)}")

    # Tick — should enqueue the past job
    print("\n[5] Scheduler tick (executing overdue jobs)...")
    before_count = len(queue.list_by_status("pending"))
    enqueued = scheduler.tick()
    after_count = len(queue.list_by_status("pending"))

    print(f"    Enqueued {len(enqueued)} episode(s)")
    print(f"    Pending count: {before_count} → {after_count}")

    # Verify the daily job got a new next_run
    updated_job2 = scheduler.get(job2.schedule_id)
    if updated_job2:
        print(f"    Daily job next run still future: {updated_job2.next_run > datetime.now().isoformat()}")

    # ------------------------------------------------------------------
    # AutoPublisher
    # ------------------------------------------------------------------
    print("\n[6] AutoPublisher...")
    # Reset queue to have approved episodes
    for ep in queue.list_by_status("published"):
        queue.update_status(ep.episode_id, "approved")

    auto_pub = AutoPublisher(queue, publishers=[file_pub, rss_pub])
    results = auto_pub.run()

    print(f"    Published {len(results)} episode(s)")
    for i, r in enumerate(results):
        status = "✓" if r.success else "✗"
        print(f"      {status} Result {i+1}: {r.published_path or r.error}")

    published_count = len(queue.list_by_status("published"))
    print(f"    Queue published count: {published_count}")

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------
    shutil.rmtree(tmpdir, ignore_errors=True)

    print("\n" + "=" * 70)
    print("DEMO FASE 7 COMPLETADO")
    print("=" * 70)


if __name__ == "__main__":
    demo_publishing()
