import re
import threading
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from content.gutenberg_fetcher import GutenbergFetcher
from web_api.database import SessionLocal
from web_api.models import Episode
from web_api.services.crew_service import curate_audiobook
from web_api.services.job_service import registry

router = APIRouter()

_fetcher = GutenbergFetcher()
_book_cache: dict[str, dict] = {}
_cache_lock = threading.Lock()


class BookResult(BaseModel):
    title: str
    author: str
    book_id: str
    url: str


class BookChapter(BaseModel):
    index: int
    title: str
    words: int


class ConvertRequest(BaseModel):
    chapter_index: int
    voice_id: str


def _get_book(book_id: str) -> dict:
    with _cache_lock:
        if book_id not in _book_cache:
            _book_cache[book_id] = _fetcher.fetch_book(book_id)
        return _book_cache[book_id]


@router.get("/search", response_model=List[BookResult])
def search_books(q: str = "", limit: int = 8):
    """Busca libros de dominio público en Project Gutenberg."""
    try:
        return _fetcher.search(query=q, max_results=max(1, min(limit, 20)))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Gutenberg error: {e}")


@router.get("/{book_id}/chapters", response_model=List[BookChapter])
def list_chapters(book_id: str):
    """Devuelve los capítulos detectados de un libro (con nº de palabras)."""
    try:
        book = _get_book(book_id)
        chapters = _fetcher.split_into_chapters(book["cleaned_text"])
        return [
            BookChapter(index=i, title=c["title"][:80], words=len(c["text"].split()))
            for i, c in enumerate(chapters)
        ]
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Gutenberg error: {e}")


@router.post("/{book_id}/to-episode", status_code=202)
def convert_chapter(book_id: str, data: ConvertRequest):
    """Lanza la conversión del capítulo a audiolibro en segundo plano.

    El congreso cura el texto (ruido editorial de Gutenberg) antes de crear
    el episodio. Progreso en /api/jobs/{job_id}/events.
    """
    job_id = registry.create("audiobook", detail=f"Audiolibro: {book_id}")

    def work():
        session = SessionLocal()
        try:
            book = _get_book(book_id)
            registry.emit(job_id, "load", f"Libro cargado: {book['title']}")
            chapters = _fetcher.split_into_chapters(book["cleaned_text"])
            if not (0 <= data.chapter_index < len(chapters)):
                registry.fail(job_id, "Chapter not found")
                return
            chapter = chapters[data.chapter_index]
            text = re.sub(r"\n{3,}", "\n\n", chapter["text"]).strip()

            curated = curate_audiobook(
                text,
                f"{book['title']} — {chapter['title']}",
                on_progress=lambda step, msg, content=None: registry.emit(
                    job_id, step, msg, content
                ),
            )

            episode = Episode(
                title=f"{book['title']} — {chapter['title'][:60]}",
                type="audiobook",
                source_text=curated,
                voice_id=data.voice_id,
                status="pending",
            )
            session.add(episode)
            session.commit()
            session.refresh(episode)
            registry.emit(job_id, "done", f"Episodio #{episode.id} en cola de síntesis")
            registry.finish(job_id, {"episode_id": episode.id})
        except Exception as e:
            session.rollback()
            registry.fail(job_id, str(e))
        finally:
            session.close()

    threading.Thread(target=work, daemon=True).start()
    return {"job_id": job_id}
