import asyncio
import edge_tts
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

from shared.config import BASE_DIR, OUTPUT_DIR
from shared.schemas import WorkerJob
from worker.tts_local import synthesize_clone

logger = logging.getLogger(__name__)

VOICE_MAP = {
    "jorge": "es-ES-AlvaroNeural",
    "dalia": "es-ES-ElviraNeural",
    "elvira": "es-ES-ElviraNeural",
}
DEFAULT_VOICE = "es-ES-AlvaroNeural"

MUSIC_DIR = BASE_DIR / "sfx_library" / "music"
MUSIC_INTRO = MUSIC_DIR / "intro_jingle.wav"
MUSIC_OUTRO = MUSIC_DIR / "outro_theme.wav"


NO_BG_MUSIC_MARKER = "[NO_BG_MUSIC]"
BG_MUSIC_MARKER_PREFIX = "[BG_MUSIC:"

# Sintetiza la voz clonada en un subproceso independiente. Higgs/vLLM no
# suelta la VRAM del proceso en caliente (unload por GC no basta y la
# recarga falla), así que el hijo carga el motor, sintetiza y muere:
# al morir, libera toda su memoria GPU y el padre puede correr VoiceFixer
# con la VRAM completamente libre.
_TTS_CHILD_CODE = """
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s", datefmt="%H:%M:%S")

from worker.tts_local import synthesize_clone
text_path, voice_id, output_path = sys.argv[1], sys.argv[2], sys.argv[3]
text = open(text_path, encoding="utf-8").read()
synthesize_clone(text, voice_id, output_path)
"""

# Diálogo multi-voz: un único subproceso sintetiza N turnos (cada uno con su
# voz) a partir de un spec JSON {"segments": [{text, voice_id, output}, ...]}.
# Un solo cargado de motor para todo el episodio: _get_engine cachea por motor
# y synthesize_clone intercambia la referencia de voz por llamada.
_TTS_DIALOGUE_CHILD_CODE = """
import json
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s", datefmt="%H:%M:%S")

from worker.tts_local import synthesize_clone

with open(sys.argv[1], encoding="utf-8") as f:
    spec = json.load(f)
for seg in spec["segments"]:
    synthesize_clone(seg["text"], seg["voice_id"], seg["output"])
"""

# Higgs (voice clone v2) exige transformers>=5.3.0 y qwen-tts exige el pin
# 4.57.3: incompatibles en un mismo venv. Cada motor corre en su propio
# intérprete (venv-higgs / venv311); el padre solo elige cuál lanzar.
# Override opcional: HIGGS_PYTHON / QWEN3_PYTHON.
_VENV_HIGGS = Path(os.getenv("HIGGS_PYTHON", BASE_DIR / "venv-higgs" / "bin" / "python"))
_VENV_QWEN3 = Path(os.getenv("QWEN3_PYTHON", sys.executable))


def _tts_python_for(voice_id: str) -> str:
    engine = (voice_id.split(":")[2] if voice_id.count(":") >= 2 else "higgs").lower()
    if engine == "higgs" and _VENV_HIGGS.exists():
        return str(_VENV_HIGGS)
    if engine == "qwen3" and _VENV_QWEN3.exists():
        return str(_VENV_QWEN3)
    return sys.executable

# VoiceFixer también corre en un subproceso independiente. Si corre en el
# proceso padre del worker, su contexto CUDA queda retenido de forma
# permanente (~1.1 GiB medido) y el siguiente episodio no puede cargar
# Higgs (vLLM-Omni necesita ~6.8 GiB de los 7.57 totales):
# "StageEngineCoreProc died during READY". Al morir el hijo, toda su
# memoria GPU vuelve al SO.
_VOICEFIXER_CHILD_CODE = """
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s", datefmt="%H:%M:%S")

from audio.audio_enhancer import VoiceFixerEnhancer
input_path, output_path, mode = sys.argv[1], sys.argv[2], int(sys.argv[3])
enhancer = VoiceFixerEnhancer(cuda=True, mode=mode)
try:
    ok = enhancer.enhance(input_path, output_path)
finally:
    enhancer.close()
sys.exit(0 if ok else 1)
"""


def _free_vram_gib() -> float:
    """VRAM libre de la GPU principal en GiB (-1.0 si no se puede consultar)."""
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=15,
        )
        return max(int(x) for x in out.stdout.split()) / 1024.0
    except Exception:
        return -1.0


def _wait_for_free_vram(min_free_gib: float = 6.0, timeout_s: int = 180) -> None:
    """Espera a que la VRAM quede libre antes de lanzar el motor TTS.

    Los motores corren en subprocesos que mueren, pero los procesos nietos
    del engine (StageEngineCoreProc de vLLM-Omni) tardan segundos en soltar
    la GPU tras la muerte del padre; arrancar el siguiente motor antes de
    tiempo provoca 'StageEngineCoreProc died during READY'.
    """
    deadline = time.time() + timeout_s
    while True:
        free = _free_vram_gib()
        logger.info(f"[TTS] VRAM libre detectada: {free:.2f} GiB")
        if free < 0 or free >= min_free_gib:
            return
        if time.time() >= deadline:
            logger.warning(
                f"[TTS] VRAM libre insuficiente ({free:.2f} GiB < {min_free_gib} GiB) "
                f"tras {timeout_s}s de espera; se intenta la síntesis igual"
            )
            return
        time.sleep(5)


def _strip_music_markers(text: str) -> str:
    """Elimina los marcadores de control de música del inicio del texto."""
    while True:
        stripped = False
        if text.startswith(NO_BG_MUSIC_MARKER):
            text = text[len(NO_BG_MUSIC_MARKER):]
            stripped = True
        elif text.startswith(BG_MUSIC_MARKER_PREFIX):
            end = text.find("]", len(BG_MUSIC_MARKER_PREFIX))
            if end != -1:
                text = text[end + 1:]
                stripped = True
        if text.startswith("\n"):
            text = text[1:]
            stripped = True
        if not stripped:
            break
    return text


def _has_no_music_marker(job: WorkerJob | None) -> bool:
    """Verifica si el trabajo solicita explícitamente no usar música de fondo."""
    if not job:
        return False
    text = job.source_text or ""
    return text.startswith(NO_BG_MUSIC_MARKER)


def _extract_bg_music_marker(job: WorkerJob | None) -> str | None:
    """Extrae el nombre de archivo de música especificado vía marcador [BG_MUSIC:...]."""
    if not job:
        return None
    text = job.source_text or ""
    if text.startswith(BG_MUSIC_MARKER_PREFIX):
        end = text.find("]", len(BG_MUSIC_MARKER_PREFIX))
        if end != -1:
            return text[len(BG_MUSIC_MARKER_PREFIX):end].strip()
    return None


def _resolve_dialogue_plan(
    source_text: str, job: WorkerJob
) -> list[dict] | None:
    """Plan de síntesis multi-voz para guiones con turnos "NOMBRE: texto".

    Devuelve la lista de segmentos con la voz resuelta para cada uno, o None
    si el episodio no es un diálogo aplicable (sin mapa de voces del canal o
    sin turnos parseables). Los hablantes sin entrada en speaker_voices usan
    la voz por defecto del canal (job.voice_id).
    """
    from processors.dialogue_parser import parse_dialogue

    voice_map = {k.strip().title(): v for k, v in (job.speaker_voices or {}).items()}
    if not voice_map:
        return None
    segments = parse_dialogue(source_text)
    if len(segments) < 2:
        return None
    plan = []
    for seg in segments:
        voice_id = voice_map.get(seg.speaker) or job.voice_id
        plan.append({"speaker": seg.speaker, "text": seg.text, "voice_id": voice_id})
    speakers = {p["speaker"]: p["voice_id"] for p in plan}
    logger.info(
        f"[TTS] Diálogo multi-voz: {len(plan)} turnos, voces: "
        + ", ".join(f"{s}={v}" for s, v in speakers.items())
    )
    return plan


def _synthesize_dialogue(plan: list[dict], output_path: Path) -> None:
    """Sintetiza cada turno con su voz y concatena en orden.

    Los turnos se agrupan por intérprete (venv/motor): normalmente todos usan
    el mismo motor y hay un único subproceso (un solo cargado de motor para
    todo el episodio, aunque los turnos alternen hablantes). Cada spec lleva el
    índice global de su turno, así que sintetizar por grupos no altera el
    orden final. Al morir el/los hijo(s), la GPU queda libre para la
    postproducción, igual que en la voz única.
    """
    import tempfile

    from worker.tts_local import _concat_wavs

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        # 1) agrupar turnos por intérprete conservando el orden de aparición
        groups: dict[str, list[dict]] = {}
        order: list[str] = []
        for i, seg in enumerate(plan):
            py = _tts_python_for(seg["voice_id"])
            if py not in groups:
                groups[py] = []
                order.append(py)
            groups[py].append({
                "text": seg["text"],
                "voice_id": seg["voice_id"],
                "output": str(td_path / f"seg_{i:04d}.wav"),
            })

        # 2) un subproceso por intérprete (cada uno carga su motor una vez)
        env = {**os.environ, "PYTHONPATH": str(BASE_DIR) + os.pathsep + os.environ.get("PYTHONPATH", "")}
        for n, py in enumerate(order):
            spec_segments = groups[py]
            spec_path = td_path / f"spec_{n}.json"
            spec_path.write_text(
                json.dumps({"segments": spec_segments}, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.info(
                f"[TTS] Sintetizando {len(spec_segments)} turnos en subproceso ({Path(py).parent.parent.name})"
            )
            subprocess.run(
                [py, "-c", _TTS_DIALOGUE_CHILD_CODE, str(spec_path)],
                check=True,
                env=env,
                cwd=str(BASE_DIR),
            )

        # 3) concatenar los turnos en orden
        wavs = [td_path / f"seg_{i:04d}.wav" for i in range(len(plan))]
        missing = [w.name for w in wavs if not w.exists()]
        if missing:
            raise RuntimeError(f"Faltan audios de turnos: {missing}")
        full_wav = td_path / "full.wav"
        _concat_wavs(wavs, full_wav)
        fmt_args = ["-codec:a", "libmp3lame", "-b:a", "192k"] if output_path.suffix.lower() == ".mp3" else []
        subprocess.run(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
             "-i", str(full_wav), "-ar", "48000", *fmt_args, str(output_path)],
            check=True,
            capture_output=True,
            text=True,
            timeout=300,
        )


def _episode_slug(title: str) -> str:
    """Nombre de archivo a partir del título del episodio: sin acentos,
    espacios y caracteres especiales convertidos a '_' (p. ej.
    'MUNDO AHORA — Jueves 24' -> 'mundo_ahora_jueves_24')."""
    slug = unicodedata.normalize("NFKD", title or "")
    slug = "".join(c for c in slug if not unicodedata.combining(c))
    slug = re.sub(r"[^A-Za-z0-9]+", "_", slug).strip("_").lower()
    return slug[:80] or "episodio"


def _handle_cloned_episode(job: WorkerJob, output_dir: Path) -> Path:
    """Voces clonadas: genera audio localmente con Higgs/Qwen3 en el worker.

    El backend remoto NO ejecuta modelos pesados ni almacena muestras de voz.
    La síntesis corre en un subproceso que muere al terminar y libera la GPU
    (vLLM-Omni no suelta VRAM en caliente; ver _TTS_CHILD_CODE). Si el guion
    trae turnos "NOMBRE: texto" y el canal tiene speaker_voices, cada turno
    se sintetiza con su voz (ver _synthesize_dialogue).
    """
    import tempfile

    output_path = output_dir / f"{_episode_slug(job.title)}.mp3"
    source_text = _strip_music_markers(job.source_text or "")

    dialogue_plan = _resolve_dialogue_plan(source_text, job)

    _wait_for_free_vram()

    if dialogue_plan:
        _synthesize_dialogue(dialogue_plan, output_path)
        return output_path

    with tempfile.NamedTemporaryFile(
        "w", suffix=".txt", delete=False, encoding="utf-8"
    ) as tf:
        tf.write(source_text)
        text_path = tf.name
    try:
        env = {**os.environ, "PYTHONPATH": str(BASE_DIR) + os.pathsep + os.environ.get("PYTHONPATH", "")}
        subprocess.run(
            [_tts_python_for(job.voice_id or ""), "-c", _TTS_CHILD_CODE, text_path, job.voice_id, str(output_path)],
            check=True,
            env=env,
            cwd=str(BASE_DIR),
        )
    finally:
        os.unlink(text_path)
    return output_path


MUSIC_TRACK_MAP = {
    "crime": "arctsound-mysterious-suspense-background-no-copyright-music-252023.mp3",
    "crimen": "arctsound-mysterious-suspense-background-no-copyright-music-252023.mp3",
    "misterio": "arctsound-mysterious-suspense-background-no-copyright-music-252023.mp3",
    "suspenso": "arctsound-mysterious-suspense-background-no-copyright-music-252023.mp3",
    "garavito": "arctsound-mysterious-suspense-background-no-copyright-music-252023.mp3",
    "motivation": "rockot-powerful-emotional-epic-174136.mp3",
    "motivacion": "rockot-powerful-emotional-epic-174136.mp3",
    "mindfulness": "daynigthmorning-aura-273351.mp3",
    "aura": "daynigthmorning-aura-273351.mp3",
    "relax": "daynigthmorning-aura-273351.mp3",
}


def _resolve_background_music(job: WorkerJob | None) -> Path | None:
    if not MUSIC_DIR.is_dir():
        return None

    # 0. Config del canal (desde el backend): manda sobre marcadores y
    # heurísticas. "none" = episodio sin fondo; un nombre de archivo = esa
    # pista; si la pista no existe en el worker, se omite el fondo (mejor
    # silencio que la pista sorpresa del fallback automático).
    if job and job.bg_music is not None:
        requested = job.bg_music.strip()
        if requested.lower() in ("", "none", "off", "no", "silencio"):
            logger.info("[Audio] Canal configurado sin música de fondo")
            return None
        cand = MUSIC_DIR / requested
        if not cand.suffix:
            cand = cand.with_suffix(".mp3")
        if cand.exists():
            logger.info(f"[Audio] Usando música de fondo configurada en el canal: {cand.name}")
            return cand
        logger.warning(f"[Audio] Pista de fondo configurada en el canal no encontrada: {cand}; se omite")
        return None

    # Si el episodio solicita explícitamente no usar música, respetarlo
    if _has_no_music_marker(job):
        logger.info("[Audio] Episodio marcado con [NO_BG_MUSIC]; omitiendo música de fondo")
        return None

    # Si el episodio especifica una pista concreta vía marcador, usarla
    explicit_track = _extract_bg_music_marker(job)
    if explicit_track:
        cand = MUSIC_DIR / explicit_track
        if not cand.suffix:
            cand = cand.with_suffix(".mp3")
        if cand.exists():
            logger.info(f"[Audio] Usando música de fondo indicada por marcador: {cand.name}")
            return cand
        logger.warning(f"[Audio] Pista indicada por marcador no encontrada: {cand}; usando lógica por defecto")

    if job:
        title = (job.title or "").lower()
        job_type = (job.type or "").lower()
        for key, filename in MUSIC_TRACK_MAP.items():
            if key in job_type or key in title:
                cand = MUSIC_DIR / filename
                if cand.exists():
                    return cand

    # Default fallback a la primera pista mp3 disponible en sfx_library/music
    for candidate in sorted(MUSIC_DIR.glob("*.mp3")):
        if candidate.name not in ("intro_jingle.wav", "outro_theme.wav"):
            return candidate
    return None


# --- Postproducción mejorada (env overrides para desactivar por paso) ---
USE_DENOISE = os.getenv("POSTPROC_DENOISE", "1").lower() in ("1", "true", "yes")
USE_VOICE_MASTER = os.getenv("POSTPROC_MASTER", "1").lower() in ("1", "true", "yes")
USE_DUCKING = os.getenv("POSTPROC_DUCKING", "1").lower() in ("1", "true", "yes")
TARGET_LUFS = float(os.getenv("POSTPROC_TARGET_LUFS", "-14"))


def _apply_denoise(path: Path) -> None:
    """Reducción de ruido espectral (ffmpeg afftdn) para limpiar siseo/humedad
    residual del TTS antes del mastering. Moderada: el TTS ya es bastante limpio
    y un nr agresivo introduce artefactos metálicos."""
    tmp = path.with_suffix(".denoise" + path.suffix)
    tmp.unlink(missing_ok=True)
    result = subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-i", str(path), "-af", "afftdn=nr=12:nf=-50", str(tmp)],
        capture_output=True, text=True, timeout=600,
    )
    if result.returncode == 0 and tmp.exists():
        tmp.replace(path)
        logger.info("[Audio] Reducción de ruido (afftdn) completada.")
    else:
        tmp.unlink(missing_ok=True)
        logger.warning(f"[Audio] afftdn falló (rc={result.returncode}); se conserva el audio original")


def _master_voice(path: Path) -> None:
    """Mastering de voz: EQ (highpass + cuerpo en graves + presencia),
    compresión, limitador y noise gate. Da a la voz TTS densidad y
    profundidad tipo estudio antes de mezclar la música."""
    from audio.podcast_mastering import MasteringConfig, process_voice_mix

    tmp_wav = path.with_suffix(".master.wav")
    tmp_wav.unlink(missing_ok=True)
    try:
        process_voice_mix(
            str(path),
            str(tmp_wav),
            MasteringConfig(
                target_lufs=TARGET_LUFS,
                eq_highpass_hz=85.0,
                eq_body_hz=150.0,
                eq_body_gain_db=3.0,
                eq_presence_hz=3500.0,
                eq_presence_gain_db=2.0,
                compressor_threshold_db=-20.0,
                compressor_ratio=3.0,
                compressor_attack_ms=10.0,
                compressor_release_ms=150.0,
                true_peak_db=-1.5,
                gate_threshold_db=-45.0,
            ),
        )
        # Volver al formato original (mp3 192k si aplica)
        fmt_args = ["-codec:a", "libmp3lame", "-b:a", "192k"] if path.suffix.lower() == ".mp3" else []
        result = subprocess.run(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
             "-i", str(tmp_wav), "-ar", "48000", *fmt_args, str(path)],
            capture_output=True, text=True, timeout=300,
        )
        if result.returncode != 0:
            logger.warning(f"[Audio] Mastering: no se pudo re-encodear (rc={result.returncode})")
    except Exception as e:
        logger.warning(f"[Audio] No se pudo aplicar mastering de voz: {e}")
    finally:
        tmp_wav.unlink(missing_ok=True)


def _mix_with_ducking(main, bg):
    """Mezcla voz + música con ducking sidechain (ffmpeg): la música baja
    automáticamente cuando suena la voz y sube en las pausas."""
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        main_wav = Path(td) / "main.wav"
        bg_wav = Path(td) / "bg.wav"
        out_wav = Path(td) / "out.wav"
        main.export(str(main_wav), format="wav")
        bg_match = bg.set_frame_rate(main.frame_rate).set_channels(main.channels)
        bg_match.export(str(bg_wav), format="wav")
        fc = (
            "[1:a]volume=-12dB[bg];"
            "[bg][0:a]sidechaincompress=threshold=0.08:ratio=6:attack=30:release=700:makeup=1[duck];"
            "[0:a][duck]amix=inputs=2:duration=first:normalize=0[a]"
        )
        result = subprocess.run(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
             "-i", str(main_wav), "-i", str(bg_wav),
             "-filter_complex", fc, "-map", "[a]", str(out_wav)],
            capture_output=True, text=True, timeout=600,
        )
        if result.returncode != 0 or not out_wav.exists():
            logger.warning(
                f"[Audio] Ducking sidechain falló (rc={result.returncode}); "
                f"usando mezcla plana: {result.stderr[-300:]}"
            )
            return main.overlay(bg)
        from pydub import AudioSegment

        return AudioSegment.from_file(str(out_wav))


def _resolve_intro_track(job: WorkerJob | None) -> Path:
    """Jingle de apertura: el configurado en el canal si existe; si no, el global."""
    if job and job.intro_track:
        cand = MUSIC_DIR / job.intro_track
        if not cand.suffix:
            for ext in (".mp3", ".wav"):
                if cand.with_suffix(ext).exists():
                    return cand.with_suffix(ext)
        elif cand.exists():
            return cand
        logger.warning(f"[Audio] Intro configurada en el canal no encontrada: {cand}; usando intro por defecto")
    return MUSIC_INTRO


def _add_branding_music(path: Path, job: WorkerJob | None = None) -> None:
    """Mezcla la música de fondo del canal y jingles de intro/outro."""
    bg_path = _resolve_background_music(job)
    intro_track = _resolve_intro_track(job)
    has_intro_outro = intro_track.exists() or MUSIC_OUTRO.exists()

    if not bg_path and not has_intro_outro:
        return

    from pydub import AudioSegment

    main = AudioSegment.from_file(path)

    # 1. Mezclar música de fondo del canal (con ducking sidechain si está activo)
    if bg_path and bg_path.exists():
        logger.info(f"[Audio] Aplicando música de fondo del canal: {bg_path.name}")
        bg = AudioSegment.from_file(bg_path)
        if len(bg) < len(main):
            loops = (len(main) // len(bg)) + 1
            bg = bg * loops
        bg = bg[:len(main)].fade_in(2000).fade_out(3000)
        if USE_DUCKING:
            main = _mix_with_ducking(main, bg)
        else:
            main = main.overlay(bg.apply_gain(-18))

    # 2. Añadir intro y outro jingles si existen
    parts: list[AudioSegment] = []
    if intro_track.exists():
        intro = AudioSegment.from_file(intro_track).apply_gain(-5)
        parts.append(intro.fade_out(1500))
    parts.append(main)
    if MUSIC_OUTRO.exists():
        outro = AudioSegment.from_file(MUSIC_OUTRO).apply_gain(-5)
        parts.append(outro.fade_in(2000))

    mixed = parts[0]
    for part in parts[1:]:
        mixed = mixed.append(part, crossfade=300)

    fmt = "mp3" if path.suffix.lower() == ".mp3" else "wav"
    mixed.export(path, format=fmt)


def _normalize_loudness(path: Path, target_i: float = TARGET_LUFS) -> None:
    """Volumen uniforme de principio a fin: loudnorm a dos pasadas
    (mide y aplica una ganancia constante; -14 LUFS = estándar Spotify/podcast moderno)."""
    measure = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(path),
         "-af", f"loudnorm=I={target_i}:TP=-1.5:LRA=11:print_format=json",
         "-f", "null", "-"],
        capture_output=True, text=True, timeout=300,
    )
    try:
        tail = measure.stderr[measure.stderr.rfind("{"):]
        stats = json.loads(tail)
        loudness = (
            f"loudnorm=I={target_i}:TP=-1.5:LRA=11:"
            f"measured_I={stats['input_i']}:measured_TP={stats['input_tp']}:"
            f"measured_LRA={stats['input_lra']}:measured_thresh={stats['input_thresh']}:"
            "linear=true"
        )
    except (json.JSONDecodeError, KeyError):
        loudness = f"loudnorm=I={target_i}:TP=-1.5:LRA=11"

    tmp = path.with_suffix(".norm" + path.suffix)
    fmt_args = ["-codec:a", "libmp3lame", "-b:a", "192k"] if path.suffix.lower() == ".mp3" else []
    result = subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-i", str(path), "-af", loudness, "-ar", "48000", *fmt_args, str(tmp)],
        capture_output=True, text=True, timeout=600,
    )
    if result.returncode == 0 and tmp.exists():
        tmp.replace(path)


USE_VOICEFIXER = os.getenv("USE_VOICEFIXER", "1").lower() in ("1", "true", "yes")


def _apply_voicefixer_enhancer(path: Path) -> None:
    """Restaura y mejora la calidad de la voz sintética con VoiceFixer AI.

    Corre en un subproceso que muere al terminar: es la única forma fiable
    de devolver al SO toda la memoria GPU que VoiceFixer reserva (contexto
    CUDA + modelos). En el proceso padre esa memoria quedaba retenida de
    forma permanente y asfixiaba la carga de Higgs en el episodio siguiente.
    """
    if not USE_VOICEFIXER:
        return
    import sys

    tmp_out = path.with_suffix(".enhanced" + path.suffix)
    tmp_out.unlink(missing_ok=True)
    try:
        logger.info("[Audio] Aplicando mejorador de voz neural VoiceFixer...")
        env = {
            **os.environ,
            "PYTHONPATH": str(BASE_DIR) + os.pathsep + os.environ.get("PYTHONPATH", ""),
        }
        result = subprocess.run(
            [sys.executable, "-c", _VOICEFIXER_CHILD_CODE, str(path), str(tmp_out), "0"],
            env=env,
            cwd=str(BASE_DIR),
        )
        if result.returncode == 0 and tmp_out.exists():
            tmp_out.replace(path)
            logger.info("[Audio] Restauración VoiceFixer completada con éxito.")
        else:
            logger.warning(
                f"[Audio] VoiceFixer no mejoró el audio (rc={result.returncode}); "
                "se conserva la voz original"
            )
    except Exception as e:
        logger.warning(f"[Audio] No se pudo aplicar VoiceFixer: {e}")
    finally:
        tmp_out.unlink(missing_ok=True)


def postprocess_episode_audio(path: Path, job: WorkerJob | None = None) -> None:
    """Cadena de postproducción: VoiceFixer → denoise → mastering de voz
    (EQ/compresión/limitador/gate) → música con ducking → loudness uniforme."""
    logger.info("[Audio] Iniciando postproducción (VoiceFixer → denoise → mastering → música/ducking → LUFS)...")
    _apply_voicefixer_enhancer(path)
    if USE_DENOISE:
        try:
            _apply_denoise(path)
        except Exception as e:
            logger.warning(f"[Audio] No se pudo aplicar reducción de ruido: {e}")
    if USE_VOICE_MASTER:
        _master_voice(path)
    try:
        _add_branding_music(path, job)
    except Exception as e:
        logger.warning(f"[Audio] No se pudo aplicar música de fondo: {e}")
    try:
        logger.info(f"[Audio] Normalizando volumen con ffmpeg loudnorm ({TARGET_LUFS} LUFS)...")
        _normalize_loudness(path)
        logger.info("[Audio] Normalización de volumen completada con éxito.")
    except Exception as e:
        logger.warning(f"[Audio] No se pudo normalizar volumen: {e}")


def handle_podcast_episode(job: WorkerJob) -> Path:
    output_dir = OUTPUT_DIR / str(job.episode_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    if (job.voice_id or "").startswith("clone:"):
        output_path = _handle_cloned_episode(job, output_dir)
        # Conservar la voz seca (antes de fixer/música) permite re-mezclar
        # sin repetir la síntesis. El motor TTS corrió en un subproceso que
        # ya murió: la GPU está libre para VoiceFixer, y el fixer siempre
        # corre antes de mezclar la música de fondo.
        shutil.copy2(output_path, output_dir / "voice_dry.mp3")
    else:
        output_path = output_dir / f"{_episode_slug(job.title)}.mp3"
        voice = VOICE_MAP.get(job.voice_id, DEFAULT_VOICE)

        async def _run():
            from core.emotion_tags import sanitize_emotion_tags
            source_text = _strip_music_markers(job.source_text or "")
            communicate = edge_tts.Communicate(
                sanitize_emotion_tags(source_text, "edge"),
                voice=voice
            )
            await communicate.save(str(output_path))

        asyncio.run(_run())

    postprocess_episode_audio(output_path, job)
    return output_path

