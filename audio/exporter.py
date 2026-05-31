import os
import numpy as np
import soundfile as sf
from pydub import AudioSegment


def export_audio(audio: np.ndarray, output_path: str, sample_rate: int = 24000) -> str:
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    ext = os.path.splitext(output_path)[1].lower()
    if ext == ".wav":
        sf.write(output_path, audio, sample_rate, subtype="PCM_16")
    elif ext == ".mp3":
        temp_wav = output_path.replace(".mp3", "_temp.wav")
        sf.write(temp_wav, audio, sample_rate, subtype="PCM_16")
        segment = AudioSegment.from_wav(temp_wav)
        segment.export(output_path, format="mp3", bitrate="192k")
        os.remove(temp_wav)
    elif ext == ".flac":
        sf.write(output_path, audio, sample_rate)
    else:
        sf.write(output_path, audio, sample_rate, subtype="PCM_16")
    return output_path
