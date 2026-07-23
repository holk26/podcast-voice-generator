import re
import threading
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from content.gutenberg_fetcher import GutenbergFetcher
from web_api.database import get_db
from web_api.models import Episode
from web_api.schemas import EpisodeResponse

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


@router.post("/{book_id}/to-episode", response_model=EpisodeResponse, status_code=201)
def convert_chapter(book_id: str, data: ConvertRequest, db: Session = Depends(get_db)):
    """Crea un episodio (audiolibro) con el texto de un capítulo del libro.

    El worker lo sintetiza con la voz indicada (edge o clonada vía Higgs).
    """
    try:
        book = _get_book(book_id)
        chapters = _fetcher.split_into_chapters(book["cleaned_text"])
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Gutenberg error: {e}")

    if not (0 <= data.chapter_index < len(chapters)):
        raise HTTPException(status_code=404, detail="Chapter not found")

    chapter = chapters[data.chapter_index]
    # Limpieza ligera: títulos de capítulo en mayúsculas seguidas molestan al TTS
    text = re.sub(r"\n{3,}", "\n\n", chapter["text"]).strip()

    episode = Episode(
        title=f"{book['title']} — {chapter['title'][:60]}",
        type="audiobook",
        source_text=text,
        voice_id=data.voice_id,
        status="pending",
    )
    db.add(episode)
    db.commit()
    db.refresh(episode)
    return episode
