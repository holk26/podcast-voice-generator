"""Tests del flujo multi-voz por turnos y de la config de música por canal."""
import json
from pathlib import Path
from unittest.mock import patch

from shared.schemas import WorkerJob
from worker import handlers


def _job(**overrides) -> WorkerJob:
    base = dict(
        episode_id=1,
        title="MUNDO AHORA",
        type="podcast",
        source_text="EDUARDO: Buenos días.\n\nYOLIS: Buenas tardes.\n\nEDUARDO: Hasta luego.",
        voice_id="clone:eduardo_aponte",
    )
    base.update(overrides)
    return WorkerJob(**base)


class TestResolveDialoguePlan:
    def test_voices_resolve_per_speaker_with_default_fallback(self):
        job = _job(speaker_voices={"Yolis": "clone:yolis"})
        plan = handlers._resolve_dialogue_plan(job.source_text, job)
        assert plan is not None
        assert len(plan) == 3
        assert [p["voice_id"] for p in plan] == [
            "clone:eduardo_aponte",
            "clone:yolis",
            "clone:eduardo_aponte",
        ]
        assert plan[1]["speaker"] == "Yolis"
        assert "Buenas tardes" in plan[1]["text"]
        # el prefijo "YOLIS:" se elimina del texto a sintetizar
        assert not plan[1]["text"].startswith("YOLIS")

    def test_map_keys_are_case_insensitive(self):
        job = _job(speaker_voices={"YOLIS": "clone:yolis"})
        plan = handlers._resolve_dialogue_plan(job.source_text, job)
        assert plan[1]["voice_id"] == "clone:yolis"

    def test_no_speaker_voices_keeps_single_voice_path(self):
        job = _job()
        assert handlers._resolve_dialogue_plan(job.source_text, job) is None

    def test_script_without_turns_keeps_single_voice_path(self):
        job = _job(
            source_text="Esto es un monólogo largo, sin turnos de diálogo.",
            speaker_voices={"Yolis": "clone:yolis"},
        )
        assert handlers._resolve_dialogue_plan(job.source_text, job) is None


class _FakeResult:
    returncode = 0


def _fake_tts_and_ffmpeg(specs_sink):
    """Simula los subprocesos TTS (escriben los wavs del spec) y el ffmpeg final."""

    def fake_run(cmd, **kwargs):
        if cmd[0] == "ffmpeg":
            Path(cmd[-1]).write_bytes(b"mp3")
            return _FakeResult()
        spec = json.loads(Path(cmd[3]).read_text(encoding="utf-8"))
        for seg in spec["segments"]:
            Path(seg["output"]).write_bytes(b"wav")
        specs_sink.append(spec)
        return _FakeResult()

    return fake_run


class TestSynthesizeDialogue:
    def test_single_subprocess_when_all_same_engine(self, tmp_path):
        job = _job(speaker_voices={"Yolis": "clone:yolis"})
        plan = handlers._resolve_dialogue_plan(job.source_text, job)
        specs = []
        with patch.object(handlers.subprocess, "run", side_effect=_fake_tts_and_ffmpeg(specs)), \
             patch("worker.tts_local._concat_wavs", return_value=tmp_path / "full.wav"):
            handlers._synthesize_dialogue(plan, tmp_path / "final.mp3")

        assert len(specs) == 1  # un solo subproceso aunque los turnos alternen
        assert len(specs[0]["segments"]) == 3
        assert specs[0]["segments"][1]["voice_id"] == "clone:yolis"
        assert (tmp_path / "final.mp3").exists()

    def test_one_subprocess_per_engine_when_mixed(self, tmp_path):
        job = _job(speaker_voices={"Yolis": "clone:yolis:qwen3"})
        plan = handlers._resolve_dialogue_plan(job.source_text, job)
        specs = []
        with patch.object(handlers.subprocess, "run", side_effect=_fake_tts_and_ffmpeg(specs)), \
             patch("worker.tts_local._concat_wavs", return_value=tmp_path / "full.wav"):
            handlers._synthesize_dialogue(plan, tmp_path / "final.mp3")

        assert len(specs) == 2  # higgs (Eduardo) + qwen3 (Yolis)
        engines = {s["segments"][0]["voice_id"] for s in specs}
        assert engines == {"clone:eduardo_aponte", "clone:yolis:qwen3"}

    def test_missing_segment_audio_fails(self, tmp_path):
        job = _job(speaker_voices={"Yolis": "clone:yolis"})
        plan = handlers._resolve_dialogue_plan(job.source_text, job)
        # el subproceso no escribe nada: deben faltar todos los wavs
        with patch.object(handlers.subprocess, "run", return_value=_FakeResult()), \
             patch("worker.tts_local._concat_wavs", return_value=tmp_path / "full.wav"):
            try:
                handlers._synthesize_dialogue(plan, tmp_path / "final.mp3")
            except RuntimeError as e:
                assert "seg_0000.wav" in str(e)
            else:
                raise AssertionError("debió fallar por wavs faltantes")


class TestChannelMusicConfig:
    def test_bg_music_none_disables_background(self):
        job = _job(bg_music="none")
        assert handlers._resolve_background_music(job) is None

    def test_bg_music_custom_track(self):
        job = _job(bg_music="daynigthmorning-aura-273351.mp3")
        resolved = handlers._resolve_background_music(job)
        assert resolved is not None
        assert resolved.name == "daynigthmorning-aura-273351.mp3"

    def test_bg_music_missing_file_omits_background(self):
        job = _job(bg_music="no_existe_esta_pista.mp3")
        assert handlers._resolve_background_music(job) is None

    def test_bg_music_unset_keeps_legacy_logic(self):
        job = _job(source_text=f"{handlers.NO_BG_MUSIC_MARKER}\nHola")
        assert handlers._resolve_background_music(job) is None

    def test_intro_track_from_channel(self):
        job = _job(intro_track="intro noticias.mp3")
        assert handlers._resolve_intro_track(job).name == "intro noticias.mp3"

    def test_intro_track_missing_falls_back_to_default(self):
        job = _job(intro_track="no_existe.mp3")
        assert handlers._resolve_intro_track(job) == handlers.MUSIC_INTRO

    def test_intro_track_unset_uses_default(self):
        job = _job()
        assert handlers._resolve_intro_track(job) == handlers.MUSIC_INTRO
