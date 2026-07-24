"""Automatización de canales: ejecución de jobs CrewAI y piloto automático.

Centraliza la lógica que antes vivía en las rutas (plan, guion, temporada)
para reutilizarla tanto desde la API como desde el worker (autopilot).
"""

import json
import os
import threading
import urllib.request
from datetime import datetime, timedelta, timezone

from web_api.database import SessionLocal
from web_api.models import Channel, ContentPlanEntry, Episode
from web_api.services.crew_service import generate_plan, generate_script, generate_season
from web_api.services.job_service import registry

# Claves en curso para no lanzar dos jobs sobre el mismo recurso
_active: set[str] = set()
_active_lock = threading.Lock()


def _acquire(key: str) -> bool:
    with _active_lock:
        if key in _active:
            return False
        _active.add(key)
        return True


def _release(key: str) -> None:
    with _active_lock:
        _active.discard(key)


def is_active(key: str) -> bool:
    with _active_lock:
        return key in _active


def _start(kind: str, detail: str, key: str, target) -> str | None:
    """Crea un job y lo lanza en un hilo. None si ya hay uno en curso."""
    if not _acquire(key):
        return None
    job_id = registry.create(kind, detail=detail)

    def runner():
        try:
            target(job_id)
        finally:
            _release(key)

    threading.Thread(target=runner, daemon=True).start()
    return job_id


# ── Jobs concretos ──────────────────────────────────────────────────────


def _progress(job_id: str):
    return lambda step, msg, content=None: registry.emit(job_id, step, msg, content)


def run_plan_job(job_id: str, channel_id: int, count: int) -> None:
    session = SessionLocal()
    try:
        channel = session.query(Channel).filter(Channel.id == channel_id).first()
        proposed = generate_plan(channel, count=count, on_progress=_progress(job_id))
        for item in proposed:
            session.add(
                ContentPlanEntry(
                    channel_id=channel_id,
                    title=item.title,
                    description=item.description,
                )
            )
        session.commit()
        registry.emit(job_id, "done", f"Plan listo: {len(proposed)} ideas")
        registry.finish(job_id, {"channel_id": channel_id, "count": len(proposed)})
    except Exception as e:
        session.rollback()
        registry.fail(job_id, str(e))
    finally:
        session.close()


def start_plan_job(channel: Channel, count: int = 5) -> str | None:
    return _start(
        "plan",
        f"Plan editorial: {channel.name}",
        f"plan:channel:{channel.id}",
        lambda job_id: run_plan_job(job_id, channel.id, count),
    )


def run_script_job(job_id: str, entry_id: int, minutes: int) -> None:
    session = SessionLocal()
    try:
        entry = session.query(ContentPlanEntry).filter(
            ContentPlanEntry.id == entry_id
        ).first()
        channel = session.query(Channel).filter(Channel.id == entry.channel_id).first()
        script = generate_script(
            channel,
            entry,
            target_minutes=minutes,
            on_progress=_progress(job_id),
        )
        episode = Episode(
            title=entry.title,
            type=channel.format,
            source_text=script,
            voice_id=channel.default_voice_id,
            status="pending",
            target_duration_minutes=float(minutes),
        )
        session.add(episode)
        session.commit()
        session.refresh(episode)

        entry.status = "generated"
        entry.episode_id = episode.id
        session.commit()
        registry.emit(job_id, "done", f"Guion listo, episodio #{episode.id} en cola")
        registry.finish(
            job_id,
            {"entry_id": entry_id, "episode_id": episode.id, "channel_id": entry.channel_id},
        )
    except Exception as e:
        session.rollback()
        registry.fail(job_id, str(e))
    finally:
        session.close()


def start_script_job(entry: ContentPlanEntry, minutes: int = 10) -> str | None:
    return _start(
        "script",
        f"Guion: {entry.title}",
        f"script:entry:{entry.id}",
        lambda job_id: run_script_job(job_id, entry.id, minutes),
    )


def run_season_job(job_id: str, channel_id: int, weeks: int) -> None:
    session = SessionLocal()
    try:
        channel = session.query(Channel).filter(Channel.id == channel_id).first()
        last_season = (
            session.query(ContentPlanEntry)
            .filter(ContentPlanEntry.channel_id == channel_id)
            .order_by(ContentPlanEntry.season.desc())
            .first()
        )
        season_number = (last_season.season if last_season else 0) + 1

        season = generate_season(
            channel,
            season_number=season_number,
            weeks=weeks,
            on_progress=_progress(job_id),
        )

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        per_week = max(1, channel.episodes_per_week or 2)
        counts_by_week: dict[int, int] = {}
        for ep in season["episodes"]:
            week = ep["week"]
            slot = counts_by_week.get(week, 0)
            counts_by_week[week] = slot + 1
            # Reparte los episodios de cada semana a lo largo de ella
            day_offset = (week - 1) * 7 + slot * max(1, 7 // per_week)
            scheduled = now + timedelta(days=day_offset)
            session.add(
                ContentPlanEntry(
                    channel_id=channel_id,
                    title=ep["title"],
                    description=ep["description"],
                    season=season_number,
                    scheduled_date=scheduled,
                )
            )
        if season.get("theme"):
            channel.description = (
                f"{(channel.description or '').split(' | Temporada')[0]}"
                f" | Temporada {season_number}: {season['theme']}"
            )
        session.commit()
        registry.emit(
            job_id, "done",
            f"Temporada {season_number} lista: {len(season['episodes'])} episodios en {weeks} semanas",
        )
        registry.finish(
            job_id,
            {"channel_id": channel_id, "season": season_number,
             "count": len(season["episodes"]), "theme": season.get("theme")},
        )
    except Exception as e:
        session.rollback()
        registry.fail(job_id, str(e))
    finally:
        session.close()


def start_season_job(channel: Channel, weeks: int = 4) -> str | None:
    return _start(
        "season",
        f"Temporada: {channel.name}",
        f"season:channel:{channel.id}",
        lambda job_id: run_season_job(job_id, channel.id, weeks),
    )


# ── Piloto automático ───────────────────────────────────────────────────

API_BASE = f"http://localhost:{os.getenv('API_PORT', '8000')}"


def _post_job(path: str) -> str | None:
    """Lanza un job vía la API (jobs visibles en el registro de la API/UI).
    Devuelve el job_id o None si está ocupado/falló."""
    req = urllib.request.Request(
        f"{API_BASE}{path}",
        data=b"{}",
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp).get("job_id")
    except Exception:
        # 409/400 = ya hay un job en curso o entrada procesada; otros errores
        # (API caída) se reintentan en la siguiente pasada
        return None


def autopilot_tick() -> list[str]:
    """Una acción por canal en piloto automático por pasada.

    - Sin borradores: lanza la planificación de una temporada nueva.
    - Con borradores: lanza el guion del más antiguo.
    Devuelve los job_ids lanzados (para logs).
    """
    launched: list[str] = []
    session = SessionLocal()
    try:
        channels = (
            session.query(Channel)
            .filter(Channel.is_active.is_(True), Channel.autopilot.is_(True))
            .all()
        )
        for channel in channels:
            draft = (
                session.query(ContentPlanEntry)
                .filter(
                    ContentPlanEntry.channel_id == channel.id,
                    ContentPlanEntry.status == "draft",
                )
                .order_by(ContentPlanEntry.scheduled_date.asc().nullsfirst(),
                          ContentPlanEntry.created_at.asc())
                .first()
            )
            if draft is None:
                job_id = _post_job(f"/api/channels/{channel.id}/season?weeks=4")
            else:
                job_id = _post_job(
                    f"/api/channels/plan/{draft.id}/approve"
                    f"?minutes={channel.target_minutes or 10}"
                )
            if job_id:
                launched.append(job_id)
    finally:
        session.close()
    return launched
