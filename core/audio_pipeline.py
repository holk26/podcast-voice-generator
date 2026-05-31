import os
import numpy as np
import soundfile as sf
from typing import Dict, Optional
from core.project import Project, Section, Voice
from core.tts_engine import TTSBase
from audio.effects import fade_in, fade_out, add_silence
from audio.normalizer import normalize_peak
from audio.mixer import mix_with_background, apply_ducking
from audio.exporter import export_audio


class AudioPipeline:
    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir

    def _load_or_get_engine(self, engine_name: str, engines: Dict[str, TTSBase]) -> TTSBase:
        engine = engines.get(engine_name)
        if engine is None:
            raise ValueError(f"Engine '{engine_name}' not available")
        if not engine.is_loaded():
            engine.load()
        return engine

    def generate_section(self, project: Project, section: Section, engines: Dict[str, TTSBase]) -> str:
        voice = project.get_voice(section.voice_id)
        if voice is None:
            raise ValueError(f"Voice '{section.voice_id}' not found in project")
        
        engine = self._load_or_get_engine(voice.engine, engines)
        
        safe_title = "".join(c if c.isalnum() else "_" for c in section.title)[:30]
        output_name = f"{section.id}_{safe_title}.wav"
        output_path = os.path.join(self.output_dir, sanitize_filename(project.name), output_name)
        
        engine.synthesize(section.text, voice, output_path)
        
        audio, sample_rate = sf.read(output_path, dtype=np.float32)
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        
        if project.settings.normalize_audio:
            audio = normalize_peak(audio, target_db=-1.0)
        
        audio = fade_in(audio, sample_rate, project.settings.fade_in_ms)
        audio = fade_out(audio, sample_rate, project.settings.fade_out_ms)
        audio = add_silence(audio, sample_rate, section.pause_after_ms)
        
        if section.music and section.music.get("track"):
            if os.path.exists(section.music["track"]):
                bg_audio, bg_sr = sf.read(section.music["track"], dtype=np.float32)
                if bg_audio.ndim > 1:
                    bg_audio = bg_audio.mean(axis=1)
                if bg_sr != sample_rate:
                    try:
                        import resampy
                        bg_audio = resampy.resample(bg_audio, bg_sr, sample_rate)
                    except ImportError:
                        # Fallback: simple repeat/pad if resampy not available
                        ratio = sample_rate / bg_sr
                        new_len = int(len(bg_audio) * ratio)
                        indices = (np.arange(new_len) / ratio).astype(int)
                        indices = np.clip(indices, 0, len(bg_audio) - 1)
                        bg_audio = bg_audio[indices]
                if len(bg_audio) < len(audio):
                    repeats = int(np.ceil(len(audio) / len(bg_audio)))
                    bg_audio = np.tile(bg_audio, repeats)
                bg_audio = bg_audio[:len(audio)]
                bg_volume = section.music.get("volume_db", -18)
                if section.music.get("ducking"):
                    bg_audio = apply_ducking(bg_audio, duck_db=12)
                audio = mix_with_background(audio, bg_audio, bg_volume_db=bg_volume)
        
        final_ext = project.settings.output_format
        final_path = output_path.replace(".wav", f".{final_ext}")
        export_audio(audio, final_path, sample_rate)
        
        if final_path != output_path and os.path.exists(output_path):
            os.remove(output_path)
        
        return final_path


def sanitize_filename(name: str) -> str:
    import re
    return re.sub(r'[^\w\s-]', '_', name).strip()[:50]
