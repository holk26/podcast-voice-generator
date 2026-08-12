"""
Branding Engine — generates intro/outro audio for podcasts and audiobooks.

Combines:
  - Jinja2 templates for scripted voice-overs
  - Background music / jingles
  - Voice synthesis via DramaMixer components
  - Pydub mixing
"""

import os
from pathlib import Path
from typing import Optional

import jinja2
from pydub import AudioSegment

from core.media_package import MediaPackage, Manifest, ScriptLine
from cast.voice_cast_manager import VoiceCastManager
from audio.drama_mixer import DramaMixer


class BrandingEngine:
    """Generates branded intros and outros for MediaPackages."""

    DEFAULT_INTRO_TEMPLATE = """
{% if music_fade_in_ms is not defined %}{% set music_fade_in_ms = 1500 %}{% endif %}
{% if music_fade_out_ms is not defined %}{% set music_fade_out_ms = 1000 %}{% endif %}
[Música de intro]
{% if show_title %}
{{ show_title }}
{% endif %}
{% if episode_number %}Episodio {{ episode_number }}{% if episode_title %}: {{ episode_title }}{% endif %}{% endif %}
{% if host_name %}Con {{ host_name }}{% endif %}
""".strip()

    DEFAULT_OUTRO_TEMPLATE = """
{% if cta %}
{{ cta }}
{% endif %}
{% if host_name %}Esto fue {{ show_title }} con {{ host_name }}.{% endif %}
{% if outro_text %}{{ outro_text }}{% endif %}
Hasta la próxima.
[Música de cierre]
""".strip()

    def __init__(
        self,
        templates_dir: str = "templates/branding",
        sfx_library_dir: str = "sfx_library",
        voice_cast: Optional[VoiceCastManager] = None,
        sample_rate: int = 24000,
        branding_crossfade_ms: int = 300,
    ):
        self.templates_dir = Path(templates_dir)
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.sfx_library_dir = Path(sfx_library_dir)
        self.voice_cast = voice_cast or VoiceCastManager()
        self.sample_rate = sample_rate
        self.branding_crossfade_ms = max(0, min(int(branding_crossfade_ms), 1000))
        self._mixer = DramaMixer(voice_cast=self.voice_cast, sample_rate=sample_rate)

        # Jinja2 environment
        self._env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(self.templates_dir)),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True
        )

    def _get_template(self, template_name: str) -> jinja2.Template:
        """Load a Jinja2 template by name; fallback to default if missing."""
        template_path = self.templates_dir / template_name
        if template_path.exists():
            return self._env.get_template(template_name)

        # Fallback defaults
        if "intro" in template_name:
            return self._env.from_string(self.DEFAULT_INTRO_TEMPLATE)
        return self._env.from_string(self.DEFAULT_OUTRO_TEMPLATE)

    def _load_music(self, music_name: str) -> Optional[AudioSegment]:
        """Load a music/jingle file from sfx_library/music/."""
        music_dir = self.sfx_library_dir / "music"
        for ext in [".mp3", ".wav", ".flac", ".ogg"]:
            candidate = music_dir / f"{music_name}{ext}"
            if candidate.exists():
                seg = AudioSegment.from_file(candidate)
                return seg.set_frame_rate(self.sample_rate).set_channels(1)
        return None

    def _synthesize_text(self, text: str, voice_id: str) -> Optional[AudioSegment]:
        """Synthesize a piece of text and return as AudioSegment."""
        from tempfile import mkdtemp
        temp_dir = mkdtemp()
        output_path = os.path.join(temp_dir, "branding_line.wav")

        line = ScriptLine(character=voice_id, text=text.strip(), voice_id=voice_id)
        try:
            segment = self._mixer.render_line(line, output_path)
            return segment
        except Exception as e:
            print(f"[BrandingEngine] Failed to synthesize branding line: {e}")
            return None

    def generate_intro(
        self,
        manifest: Manifest,
        music_name: str = "intro_jingle",
        template_name: str = "intro_default.j2",
        host_voice_id: str = "homer",
        music_volume_db: float = -14.0,
        music_fade_in_ms: int = 1500,
        music_fade_out_ms: int = 1000
    ) -> Optional[AudioSegment]:
        """Generate an intro audio segment for a podcast/episode."""
        template = self._get_template(template_name)

        # Render template text
        rendered = template.render(
            show_title=manifest.title,
            episode_number=manifest.episode_number,
            episode_title=manifest.title,
            host_name="Homero" if host_voice_id == "homer" else host_voice_id.capitalize(),
            show_description=manifest.description,
            content_type=manifest.content_type,
            music_fade_in_ms=music_fade_in_ms,
            music_fade_out_ms=music_fade_out_ms
        ).strip()

        # Clean up placeholder lines like [Música de intro]
        voice_lines = [ln for ln in rendered.splitlines() if ln.strip() and not ln.strip().startswith("[")]
        voice_text = " ".join(voice_lines)

        if not voice_text:
            print("[BrandingEngine] Intro template produced no voice text.")
            return None

        # Synthesize voice
        voice_seg = self._synthesize_text(voice_text, host_voice_id)
        if voice_seg is None:
            return None

        # Load music
        music = self._load_music(music_name)
        if music is None:
            print(f"[BrandingEngine] Music '{music_name}' not found, returning voice-only intro.")
            return voice_seg

        # Ensure music covers voice + some tail
        target_ms = len(voice_seg) + 1500
        loops = []
        total_ms = 0
        while total_ms < target_ms:
            loops.append(music)
            total_ms += len(music)
        music_track = sum(loops[1:], loops[0])[:target_ms]

        # Apply fade and volume
        music_track = music_track.fade_in(music_fade_in_ms).fade_out(music_fade_out_ms)
        music_track = music_track + music_volume_db

        # Overlay voice onto music (voice starts after a short musical lead-in)
        voice_start_ms = 1500
        if len(music_track) < voice_start_ms + len(voice_seg):
            voice_start_ms = 0

        intro = music_track.overlay(voice_seg, position=voice_start_ms)
        return intro

    def generate_outro(
        self,
        manifest: Manifest,
        music_name: str = "outro_theme",
        template_name: str = "outro_default.j2",
        host_voice_id: str = "homer",
        cta: str = "Suscríbete en Spotify, Apple Podcasts y Google Podcasts.",
        music_volume_db: float = -14.0,
        music_fade_in_ms: int = 1000,
        music_fade_out_ms: int = 3000
    ) -> Optional[AudioSegment]:
        """Generate an outro audio segment."""
        template = self._get_template(template_name)

        rendered = template.render(
            show_title=manifest.title,
            host_name="Homero" if host_voice_id == "homer" else host_voice_id.capitalize(),
            cta=cta,
            outro_text="Gracias por escuchar.",
            content_type=manifest.content_type,
            music_fade_in_ms=music_fade_in_ms,
            music_fade_out_ms=music_fade_out_ms
        ).strip()

        voice_lines = [ln for ln in rendered.splitlines() if ln.strip() and not ln.strip().startswith("[")]
        voice_text = " ".join(voice_lines)

        if not voice_text:
            return None

        voice_seg = self._synthesize_text(voice_text, host_voice_id)
        if voice_seg is None:
            return None

        music = self._load_music(music_name)
        if music is None:
            return voice_seg

        target_ms = len(voice_seg) + 2000
        loops = []
        total_ms = 0
        while total_ms < target_ms:
            loops.append(music)
            total_ms += len(music)
        music_track = sum(loops[1:], loops[0])[:target_ms]

        music_track = music_track.fade_in(music_fade_in_ms).fade_out(music_fade_out_ms)
        music_track = music_track + music_volume_db

        # Voice starts at beginning of outro music
        outro = music_track.overlay(voice_seg, position=0)
        return outro

    def apply_to_package(
        self,
        package: MediaPackage,
        main_audio_path: str,
        output_path: str,
        intro_music: str = "intro_jingle",
        outro_music: str = "outro_theme",
        host_voice_id: str = "homer",
        target_lufs: Optional[float] = None,
    ) -> str:
        """
        Add intro and outro to an existing main audio file.
        Saves the final branded mix to output_path.

        When target_lufs is provided, each segment (intro, main, outro) is
        normalized to that target before concatenation, and crossfade is applied
        between segments.
        """
        main = AudioSegment.from_file(main_audio_path)
        main = main.set_frame_rate(self.sample_rate).set_channels(1)

        intro = self.generate_intro(
            manifest=package.manifest,
            music_name=intro_music,
            host_voice_id=host_voice_id
        )
        outro = self.generate_outro(
            manifest=package.manifest,
            music_name=outro_music,
            host_voice_id=host_voice_id
        )

        # Normalize intro/outro/main to target LUFS if provided
        if target_lufs is not None:
            import tempfile
            from audio.podcast_mastering import normalize_loudness

            with tempfile.TemporaryDirectory() as tmp:
                for seg_name, seg in [("intro", intro), ("main", main), ("outro", outro)]:
                    if seg is None:
                        continue
                    src = os.path.join(tmp, f"{seg_name}_src.wav")
                    dst = os.path.join(tmp, f"{seg_name}_norm.wav")
                    seg.export(src, format="wav")
                    try:
                        normalize_loudness(src, dst, target_lufs=target_lufs, true_peak_db=-1.0)
                        normalized = AudioSegment.from_wav(dst)
                        if seg_name == "intro":
                            intro = normalized
                        elif seg_name == "main":
                            main = normalized
                        else:
                            outro = normalized
                    except Exception as exc:
                        print(f"[BrandingEngine] Loudness normalization failed for {seg_name}: {exc}")

        cf = self.branding_crossfade_ms
        final = AudioSegment.silent(duration=0, frame_rate=self.sample_rate)
        if intro:
            final = final.append(intro, crossfade=0)
        final = final.append(main, crossfade=cf if intro else 0)
        if outro:
            final = final.append(outro, crossfade=cf)

        # Normalize
        final = final.normalize(headroom=1.0)

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        ext = Path(output_path).suffix.lower()
        if ext == ".mp3":
            final.export(output_path, format="mp3", bitrate="192k")
        elif ext == ".wav":
            final.export(output_path, format="wav")
        else:
            final.export(output_path, format="mp3", bitrate="192k")

        return output_path

    def close(self) -> None:
        self._mixer.close()
