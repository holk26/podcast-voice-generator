"""
Pipeline Orchestrator — unifies the entire Media Automation Platform workflow.

A single EpisodeConfig drives the full pipeline:
  1. Content acquisition (RSS, Gutenberg, or template generation)
  2. Content processing (NewsProcessor, BookProcessor, or direct agent pipeline)
  3. Audio rendering (DramaMixer)
  4. Branding (BrandingEngine intro/outro + music)
  5. Package export (MediaPackage saved to disk)

Usage:
    config = EpisodeConfig(
        episode_type="news",
        sources=[{"type": "rss", "url": "https://techcrunch.com/feed/", "max_articles": 3}],
        target_duration_minutes=8.0,
        voice_cast_path="cast/voice_cast.yaml"
    )
    pipeline = PipelineOrchestrator(config)
    result = pipeline.run()
    if result.success:
        print(f"Final audio: {result.final_audio_path}")
"""

import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from audio.podcast_mastering import MasteringConfig
from core.media_package import MediaPackage, Manifest


@dataclass
class EpisodeConfig:
    """Configuration for a single episode production run."""

    episode_type: str  # "news", "book", "meditation", "motivation", "raw"
    title: Optional[str] = None
    sources: List[Dict[str, Any]] = field(default_factory=list)
    target_duration_minutes: float = 8.0
    voice_cast_path: Optional[str] = None
    host_voice_id: str = "homer"
    intro_music: str = "intro_jingle"
    outro_music: str = "outro_theme"
    branding_enabled: bool = True
    sfx_enabled: bool = True
    background_music: Optional[str] = None  # nombre del archivo en sfx_library/music/ sin extensión
    bg_music_volume: float = -18.0  # volumen en dB
    output_dir: str = "media_packages"
    episode_number: Optional[int] = None
    season_number: Optional[int] = None
    provider_config: Optional[Dict[str, Any]] = None
    # Audio enhancement
    audio_enhancer: str = "none"  # "none", "voicefixer", "voicefixer_line", "voicefixer_final", "voicefixer_both"
    audio_enhancer_mode: int = 0  # VoiceFixer mode: 0=original, 1=preprocess, 2=train
    # Podcast mastering
    podcast_mastering: MasteringConfig = field(default_factory=MasteringConfig)
    # Extra passthrough for processors
    processor_options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineResult:
    """Result of a pipeline run."""

    success: bool
    media_package: Optional[MediaPackage] = None
    final_audio_path: Optional[str] = None
    logs: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None


class PipelineOrchestrator:
    """
    End-to-end pipeline: config → content → agents → audio → branding → package.
    """

    def __init__(
        self,
        config: EpisodeConfig,
        provider=None,
        voice_cast=None
    ):
        self.config = config
        self.provider = provider
        self.voice_cast = voice_cast
        self._logs: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> PipelineResult:
        """Execute the full pipeline."""
        try:
            # 1. Content acquisition
            raw_content, content_meta = self._acquire_content()
            self._log("acquire", True, meta=content_meta)

            # 2. Process content through agents → MediaPackage
            package = self._process_content(raw_content, content_meta)
            self._log("process", True, package_id=package.package_id)

            # 3. Save package skeleton so assets have a home
            package.save(self.config.output_dir)
            self._log("save", True, path=str(package._base_path))

            # 4. Render main audio with DramaMixer
            main_audio_path = self._render_audio(package)
            self._log("render", True, path=main_audio_path)

            # 4b. Apply background music (continuous bed under voice)
            if self.config.background_music:
                self._apply_background_music(main_audio_path)
                self._log("bg_music", True, track=self.config.background_music)

            # 5. Apply branding (intro/outro)
            final_audio_path = self._apply_branding(package, main_audio_path)
            self._log("brand", True, path=final_audio_path)

            # 6. Update manifest with duration
            self._update_manifest(package, final_audio_path)
            package.save(self.config.output_dir)

            return PipelineResult(
                success=True,
                media_package=package,
                final_audio_path=final_audio_path,
                logs=self._logs
            )

        except Exception as exc:
            self._log("pipeline", False, error=str(exc))
            return PipelineResult(
                success=False,
                logs=self._logs,
                error=str(exc)
            )

    # ------------------------------------------------------------------
    # Step 1: Content acquisition
    # ------------------------------------------------------------------

    def _acquire_content(self) -> tuple:
        """
        Fetch or generate raw content based on episode_type and sources.
        Returns (raw_content, metadata_dict).
        """
        etype = self.config.episode_type.lower()

        if etype == "news":
            return self._fetch_rss()

        if etype == "book":
            return self._fetch_gutenberg()

        if etype in ("meditation", "motivation"):
            return self._generate_template(etype)

        if etype == "raw":
            # Expect a single source with "content" key
            if not self.config.sources:
                raise ValueError("Raw episodes require a source with 'content' key.")
            src = self.config.sources[0]
            return src.get("content", ""), {
                "title": src.get("title", "Raw Content"),
                "source": "raw",
                "source_url": ""
            }

        raise ValueError(f"Unsupported episode_type: {etype}")

    def _fetch_rss(self) -> tuple:
        from content.rss_fetcher import RSSFetcher

        if not self.config.sources:
            raise ValueError("News episodes require at least one RSS source.")

        fetcher = RSSFetcher()
        all_articles = []
        for src in self.config.sources:
            if src.get("type") != "rss":
                continue
            articles = fetcher.fetch(
                feed_url=src["url"],
                max_articles=src.get("max_articles", 5)
            )
            all_articles.extend(articles)

        if not all_articles:
            raise RuntimeError("No articles fetched from RSS sources.")

        # Merge articles into a single raw content block
        parts = [f"# {self.config.title or 'News Podcast'}\n"]
        for i, article in enumerate(all_articles, 1):
            parts.append(f"\n## Noticia {i}: {article.get('title', '')}\n")
            parts.append(article.get("content", article.get("description", "")))
            parts.append(f"\nFuente: {article.get('url', article.get('source_url', ''))}")

        raw = "\n".join(parts)
        meta = {
            "title": self.config.title or "News Podcast",
            "source": "rss",
            "source_url": all_articles[0].get("source_url", "")
        }
        return raw, meta

    def _fetch_gutenberg(self) -> tuple:
        from content.gutenberg_fetcher import GutenbergFetcher

        if not self.config.sources:
            raise ValueError("Book episodes require a source with 'book_id' or 'query'.")

        src = self.config.sources[0]
        fetcher = GutenbergFetcher()

        if "book_id" in src:
            book = fetcher.download_book(src["book_id"])
        elif "query" in src:
            results = fetcher.search(query=src["query"], language=src.get("language", "es"))
            if not results:
                raise RuntimeError(f"No Gutenberg books found for query: {src['query']}")
            book = fetcher.download_book(results[0]["id"])
        else:
            raise ValueError("Book source requires 'book_id' or 'query'.")

        text = book.get("cleaned_text", book.get("content", ""))
        if not text:
            raise ValueError("Downloaded book has no text content.")

        meta = {
            "title": book.get("title", "Audiolibro"),
            "author": book.get("author", ""),
            "source": "gutenberg",
            "source_url": book.get("source_url", ""),
            "book": book
        }
        return text, meta

    def _generate_template(self, etype: str) -> tuple:
        from content.template_engine import TemplateEngine

        engine = TemplateEngine()
        duration = int(self.config.target_duration_minutes)

        if etype == "meditation":
            result = engine.generate_meditation(
                duration_minutes=duration,
                topic=self.config.processor_options.get("topic"),
                seed=self.config.processor_options.get("seed")
            )
        else:  # motivation
            result = engine.generate_motivation(
                duration_minutes=duration,
                topic=self.config.processor_options.get("topic"),
                seed=self.config.processor_options.get("seed")
            )

        raw = result["content"]
        meta = {
            "title": result["title"],
            "source": "template",
            "source_url": "",
            "topic": result.get("topic", ""),
            "duration_minutes": result.get("duration_minutes", duration)
        }
        return raw, meta

    # ------------------------------------------------------------------
    # Step 2: Content processing
    # ------------------------------------------------------------------

    def _process_content(self, raw_content: str, content_meta: Dict[str, Any]) -> MediaPackage:
        """
        Route raw content to the appropriate processor and run the agent pipeline.
        """
        etype = self.config.episode_type.lower()

        if etype == "news":
            return self._process_news(raw_content, content_meta)

        if etype == "book":
            return self._process_book(content_meta)

        if etype in ("meditation", "motivation", "raw"):
            return self._process_direct(raw_content, content_meta)

        raise ValueError(f"No processor available for episode_type: {etype}")

    def _process_news(self, raw_content: str, content_meta: Dict[str, Any]) -> MediaPackage:
        from processors.news_processor import NewsProcessor

        proc = NewsProcessor(
            provider=self.provider,
            target_duration_minutes=self.config.target_duration_minutes,
            voice_cast=self.voice_cast
        )
        # NewsProcessor expects articles list, but we already merged them.
        # We'll bypass and use the orchestrator directly.
        result = proc.orchestrator.run(
            raw_content=raw_content,
            source="rss",
            content_type="news",
            content_title=content_meta.get("title", "News"),
            source_url=content_meta.get("source_url", ""),
            episode_number=self.config.episode_number,
            target_duration_minutes=self.config.target_duration_minutes
        )
        if not result.success:
            raise RuntimeError(f"News processing failed: {result.error}")

        package = result.data["media_package"]
        if self.config.title and self.config.episode_number:
            package.manifest.title = f"{self.config.title} #{self.config.episode_number}: {package.manifest.title}"
        elif self.config.title:
            package.manifest.title = f"{self.config.title}: {package.manifest.title}"

        return package

    def _process_book(self, content_meta: Dict[str, Any]) -> MediaPackage:
        from processors.book_processor import BookProcessor
        from content.gutenberg_fetcher import GutenbergFetcher

        book = content_meta["book"]
        proc = BookProcessor(
            provider=self.provider,
            target_duration_minutes=self.config.target_duration_minutes,
            voice_cast=self.voice_cast,
            max_words_per_chapter=self.config.processor_options.get("max_words_per_chapter", 2500)
        )
        packages = proc.process_book(book)
        if not packages:
            raise RuntimeError("Book processing produced no chapters.")

        # Return first chapter for now (future: queue all chapters)
        first = packages[0]
        first.manifest.title = f"{book.get('title', 'Audiolibro')} — {first.manifest.title}"
        first.manifest.author = book.get("author", "")
        first.manifest.content_type = "audiobook"
        return first

    def _process_direct(self, raw_content: str, content_meta: Dict[str, Any]) -> MediaPackage:
        """For meditation, motivation, and raw content — run agents directly."""
        from agents.orchestrator import AgentOrchestrator

        orch = AgentOrchestrator(
            provider=self.provider,
            voice_cast=self.voice_cast
        )
        result = orch.run(
            raw_content=raw_content,
            source=content_meta.get("source", "raw"),
            content_type=self.config.episode_type,
            content_title=content_meta.get("title", self.config.title or "Untitled"),
            source_url=content_meta.get("source_url", ""),
            episode_number=self.config.episode_number,
            target_duration_minutes=self.config.target_duration_minutes
        )
        if not result.success:
            raise RuntimeError(f"Direct processing failed: {result.error}")

        package = result.data["media_package"]
        package.manifest.content_type = self.config.episode_type
        return package

    # ------------------------------------------------------------------
    # Step 3: Audio rendering
    # ------------------------------------------------------------------

    def _render_audio(self, package: MediaPackage) -> str:
        from audio.drama_mixer import DramaMixer
        from audio.audio_enhancer import VoiceFixerEnhancer, NoOpEnhancer

        # Build enhancer from config
        enh_cfg = self.config.audio_enhancer.lower()
        if enh_cfg in ("voicefixer", "voicefixer_both"):
            enhancer = VoiceFixerEnhancer(cuda=True, mode=self.config.audio_enhancer_mode)
            enhance_per_line = True
            enhance_final = True
        elif enh_cfg == "voicefixer_line":
            enhancer = VoiceFixerEnhancer(cuda=True, mode=self.config.audio_enhancer_mode)
            enhance_per_line = True
            enhance_final = False
        elif enh_cfg == "voicefixer_final":
            enhancer = VoiceFixerEnhancer(cuda=True, mode=self.config.audio_enhancer_mode)
            enhance_per_line = False
            enhance_final = True
        else:
            enhancer = None
            enhance_per_line = False
            enhance_final = False

        mixer = DramaMixer(
            voice_cast=self.voice_cast,
            sample_rate=24000,
            enhancer=enhancer,
            enhance_per_line=enhance_per_line,
            enhance_final=enhance_final
        )
        output_path = str(package.assets_path / "main_mix.mp3")
        mixer.mix_package(package, output_path)
        mixer.close()
        return output_path

    # ------------------------------------------------------------------
    # Step 4: Branding
    # ------------------------------------------------------------------

    def _apply_branding(self, package: MediaPackage, main_audio_path: str) -> str:
        if not self.config.branding_enabled:
            # Just copy main audio as final
            final_path = str(package.assets_path / "final.mp3")
            shutil.copy2(main_audio_path, final_path)
            return final_path

        from audio.branding_engine import BrandingEngine

        branding = BrandingEngine(
            voice_cast=self.voice_cast,
            sample_rate=24000
        )
        final_path = str(package.assets_path / "final_with_branding.mp3")
        branding.apply_to_package(
            package=package,
            main_audio_path=main_audio_path,
            output_path=final_path,
            intro_music=self.config.intro_music,
            outro_music=self.config.outro_music,
            host_voice_id=self.config.host_voice_id
        )
        branding.close()
        return final_path

    # ------------------------------------------------------------------
    # Step 4b: Background music
    # ------------------------------------------------------------------

    def _apply_background_music(self, audio_path: str) -> None:
        """Mix continuous background music under the voice track with ducking."""
        import numpy as np
        from pydub import AudioSegment

        music_base = Path("sfx_library") / "music"
        music_file = None
        for ext in (".mp3", ".wav", ".flac", ".ogg"):
            candidate = music_base / f"{self.config.background_music}{ext}"
            if candidate.exists():
                music_file = candidate
                break
        if music_file is None:
            print(f"[PipelineOrchestrator] Background music '{self.config.background_music}' not found")
            return

        main = AudioSegment.from_file(audio_path)
        music_seg = AudioSegment.from_file(str(music_file))

        sr = main.frame_rate
        sw = main.sample_width
        ch = main.channels

        music_seg = music_seg.set_frame_rate(sr).set_channels(ch)

        # Loop music to cover voice
        while len(music_seg) < len(main):
            music_seg = music_seg + music_seg
        music_seg = music_seg[:len(main)]

        # Fade in/out
        fade_in_ms = min(3000, int(len(main) * 0.1))
        fade_out_ms = min(4000, int(len(main) * 0.1))
        if fade_in_ms > 0:
            music_seg = music_seg.fade_in(fade_in_ms)
        if fade_out_ms > 0:
            music_seg = music_seg.fade_out(fade_out_ms)

        vol_db = self.config.bg_music_volume

        # numpy conversion
        dtype_map = {1: np.int8, 2: np.int16, 4: np.int32}
        np_dtype = dtype_map.get(sw, np.int16)
        max_val = float(2 ** (8 * sw - 1))

        main_arr = np.array(main.get_array_of_samples(), dtype=np_dtype).astype(np.float32) / max_val
        music_arr = np.array(music_seg.get_array_of_samples(), dtype=np_dtype).astype(np.float32) / max_val

        if ch == 2:
            main_arr = main_arr.reshape(-1, 2)
            music_arr = music_arr.reshape(-1, 2)
            main_mono = main_arr.mean(axis=1)
        else:
            main_mono = main_arr

        n = len(main_mono)

        win = max(1, int(0.2 * sr))
        hop = max(1, int(0.05 * sr))
        n_win = max(1, (n - win) // hop + 1)

        if n_win < 3:
            gain = 10 ** (vol_db / 20)
            music_arr *= gain
        else:
            rms = np.empty(n_win, dtype=np.float32)
            for w in range(n_win):
                s = w * hop
                e = min(s + win, n)
                rms[w] = np.sqrt(np.mean(main_mono[s:e] ** 2))

            kernel = max(1, n_win // 15)
            rms = np.convolve(rms, np.ones(kernel) / kernel, mode="same")

            max_rms = float(np.max(rms)) if np.max(rms) > 0 else 1.0
            level = np.clip(rms / max_rms, 0.0, 1.0)

            silence_gain = 10 ** ((vol_db + 3) / 20)
            ducked_gain = 10 ** ((vol_db - 4) / 20)
            gain_curve = silence_gain + (ducked_gain - silence_gain) * level

            positions = np.arange(n_win) * hop + win // 2
            positions = np.clip(positions, 0, n - 1)
            full_gain = np.interp(np.arange(n), positions, gain_curve)

            if ch == 2:
                music_arr[:, 0] *= full_gain
                music_arr[:, 1] *= full_gain
            else:
                music_arr *= full_gain

        mixed = main_arr + music_arr
        mixed = np.clip(mixed, -1.0, 1.0)

        mixed_int = (mixed * max_val).clip(-max_val, max_val - 1).astype(np_dtype)
        mixed_seg = AudioSegment(
            mixed_int.tobytes(),
            frame_rate=sr,
            sample_width=sw,
            channels=ch,
        )

        ext = Path(audio_path).suffix.lower().lstrip(".")
        fmt = "mp3" if ext == "mp3" else ("flac" if ext == "flac" else "wav")
        mixed_seg.export(audio_path, format=fmt)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _update_manifest(self, package: MediaPackage, final_audio_path: str) -> None:
        """Update manifest with file metadata."""
        from pydub import AudioSegment

        try:
            audio = AudioSegment.from_file(final_audio_path)
            package.manifest.duration_seconds = int(len(audio) / 1000)
        except Exception:
            pass

        package.manifest.episode_number = self.config.episode_number
        package.manifest.season_number = self.config.season_number
        package.manifest.publish_date = datetime.now().isoformat()

    def _log(self, step: str, success: bool, **kwargs) -> None:
        self._logs.append({
            "step": step,
            "success": success,
            "timestamp": datetime.now().isoformat(),
            **kwargs
        })
