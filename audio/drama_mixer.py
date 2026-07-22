"""
Drama Mixer — assembles multi-voice audio from a MediaPackage script.

For each ScriptLine:
  1. Resolves the voice via VoiceCastManager
  2. Generates speech with the appropriate TTS engine (cached)
  3. Adds pauses before/after the line
  4. Concatenates all lines into a continuous audio track
  5. Applies normalization, fade in/out, and exports
"""

import os
import shutil
from typing import List, Optional, Dict
from pathlib import Path

from pydub import AudioSegment

from core.media_package import MediaPackage, ScriptLine
from cast.voice_cast_manager import VoiceCastManager
from core.tts_engine import TTSBase
from core.edge_tts_engine import EdgeTTSEngine
from core.xtts_engine import XTTSEngine
from core.orpheus_engine import OrpheusEngine
from core.higgs_engine import HiggsAudioEngine


class DramaMixer:
    """Renders a multi-voice script into a single audio file."""

    def __init__(
        self,
        voice_cast: Optional[VoiceCastManager] = None,
        sample_rate: int = 24000,
        normalize: bool = True,
        fade_in_ms: int = 500,
        fade_out_ms: int = 1000,
        default_engine_device: str = "auto",
        enhancer=None,
        enhance_per_line: bool = True,
        enhance_final: bool = True
    ):
        self.voice_cast = voice_cast or VoiceCastManager()
        self.sample_rate = sample_rate
        self.normalize = normalize
        self.fade_in_ms = fade_in_ms
        self.fade_out_ms = fade_out_ms
        self.default_engine_device = default_engine_device
        self.enhancer = enhancer
        self.enhance_per_line = enhance_per_line
        self.enhance_final = enhance_final
        self._engine_cache: Dict[str, TTSBase] = {}

    def _get_engine(self, engine_name: str) -> TTSBase:
        """Get or instantiate a TTS engine by name."""
        if engine_name in self._engine_cache:
            return self._engine_cache[engine_name]

        if engine_name == "edge_tts":
            engine = EdgeTTSEngine(device="cpu")
        elif engine_name == "xtts":
            engine = XTTSEngine(device=self.default_engine_device)
        elif engine_name == "orpheus":
            engine = OrpheusEngine(device=self.default_engine_device)
        elif engine_name == "higgs":
            engine = HiggsAudioEngine(device=self.default_engine_device)
        elif engine_name == "bark":
            # Lazy import to avoid loading heavy deps unless needed
            from core.bark_engine import BarkEngine
            engine = BarkEngine(device=self.default_engine_device)
        else:
            raise ValueError(f"Unsupported TTS engine: {engine_name}")

        engine.load()
        self._engine_cache[engine_name] = engine
        return engine

    def render_line(self, line: ScriptLine, output_path: str) -> AudioSegment:
        """Generate audio for a single ScriptLine and return as AudioSegment."""
        # Resolve voice
        profile = self.voice_cast.resolve_voice_for_line(
            line.character,
            fallback_voice_id=line.voice_id
        )
        voice = profile.to_voice()

        # Get appropriate engine
        engine = self._get_engine(voice.engine)

        # Synthesize
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        engine.synthesize(line.text, voice, output_path)

        # Apply enhancer per-line if configured
        if self.enhancer and self.enhance_per_line:
            enhanced_path = str(Path(output_path).with_suffix(".enhanced.wav"))
            success = self.enhancer.enhance(output_path, enhanced_path)
            if success and os.path.exists(enhanced_path):
                # Replace original with enhanced
                shutil.move(enhanced_path, output_path)
            else:
                # Clean up failed enhancement temp file
                if os.path.exists(enhanced_path):
                    os.remove(enhanced_path)

        # Load as AudioSegment
        segment = AudioSegment.from_wav(output_path)

        # Ensure correct sample rate and mono
        segment = segment.set_frame_rate(self.sample_rate).set_channels(1)

        # Add silence before and after
        if line.pause_before_ms > 0:
            pre_silence = AudioSegment.silent(duration=line.pause_before_ms, frame_rate=self.sample_rate)
            segment = pre_silence + segment
        if line.pause_after_ms > 0:
            post_silence = AudioSegment.silent(duration=line.pause_after_ms, frame_rate=self.sample_rate)
            segment = segment + post_silence

        return segment

    def mix_package(
        self,
        package: MediaPackage,
        output_path: str,
        keep_line_files: bool = False
    ) -> str:
        """
        Render the entire MediaPackage script into a single audio file.
        Saves intermediate line files to package assets/ folder unless keep_line_files=False.
        """
        if not package.script:
            raise ValueError("MediaPackage has no script lines to render.")

        # Ensure package has a base path for intermediate assets
        if package._base_path is None:
            import tempfile
            temp_base = Path(tempfile.mkdtemp(prefix=f"dramamixer_{package.package_id}_"))
            package._base_path = temp_base
            (temp_base / "assets").mkdir(exist_ok=True)

        package.assets_path.mkdir(parents=True, exist_ok=True)

        segments: List[AudioSegment] = []
        for i, line in enumerate(package.script):
            line_path = package.assets_path / f"line_{i:03d}_{line.voice_id}.wav"
            print(f"[DramaMixer] [{i+1}/{len(package.script)}] {line.character}: {line.text[:50]}...")
            segment = self.render_line(line, str(line_path))
            segments.append(segment)
            if not keep_line_files:
                # Will delete after mixing
                pass

        # Concatenate all segments
        final = segments[0]
        for segment in segments[1:]:
            final = final + segment

        # Apply fade in/out
        final = final.fade_in(self.fade_in_ms).fade_out(self.fade_out_ms)

        # Normalize
        if self.normalize:
            # pydub normalize to -1.0 dBFS
            final = final.normalize(headroom=1.0)

        # Export
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        ext = Path(output_path).suffix.lower()
        if ext == ".mp3":
            final.export(output_path, format="mp3", bitrate="192k")
        elif ext == ".wav":
            final.export(output_path, format="wav")
        elif ext == ".flac":
            final.export(output_path, format="flac")
        else:
            final.export(output_path, format="wav")

        # Apply enhancer post-mix if configured
        if self.enhancer and self.enhance_final:
            # VoiceFixer works best with WAV input
            final_wav = str(Path(output_path).with_suffix(".pre_enhance.wav"))
            final.export(final_wav, format="wav")
            enhanced_path = str(Path(output_path).with_suffix(".enhanced.wav"))
            success = self.enhancer.enhance(final_wav, enhanced_path)
            if success and os.path.exists(enhanced_path):
                # Convert enhanced back to desired format
                enhanced_seg = AudioSegment.from_wav(enhanced_path)
                if ext == ".mp3":
                    enhanced_seg.export(output_path, format="mp3", bitrate="192k")
                elif ext == ".flac":
                    enhanced_seg.export(output_path, format="flac")
                else:
                    enhanced_seg.export(output_path, format="wav")
                os.remove(enhanced_path)
            os.remove(final_wav)

        # Clean up intermediate line files unless requested
        if not keep_line_files:
            for i, _ in enumerate(package.script):
                line_path = package.assets_path / f"line_{i:03d}_{package.script[i].voice_id}.wav"
                if line_path.exists():
                    line_path.unlink()

        # Copy final mix into package assets if it's not already there
        mix_asset_name = Path(output_path).name
        target_in_assets = package.assets_path / mix_asset_name
        if Path(output_path).resolve() != target_in_assets.resolve():
            package.copy_asset(output_path, asset_name=mix_asset_name)

        return output_path

    def close(self) -> None:
        """Unload all cached TTS engines and enhancer to free memory."""
        for engine in self._engine_cache.values():
            try:
                engine.unload()
            except Exception:
                pass
        self._engine_cache.clear()
        if self.enhancer and hasattr(self.enhancer, "close"):
            try:
                self.enhancer.close()
            except Exception:
                pass
