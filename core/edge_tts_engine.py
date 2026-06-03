import os
import asyncio
from typing import List
from core.tts_engine import TTSBase
from core.project import Voice


try:
    import edge_tts
except ImportError:
    edge_tts = None  # type: ignore


# Cache de voces en español (lista estática para no hacer requests cada vez)
_EDGE_VOICES = {
    "es-ES-AlvaroNeural": {"locale": "es-ES", "gender": "Male", "name": "Alvaro (España)"},
    "es-ES-ElviraNeural": {"locale": "es-ES", "gender": "Female", "name": "Elvira (España)"},
    "es-ES-XimenaNeural": {"locale": "es-ES", "gender": "Female", "name": "Ximena (España)"},
    "es-MX-DaliaNeural": {"locale": "es-MX", "gender": "Female", "name": "Dalia (México)"},
    "es-MX-JorgeNeural": {"locale": "es-MX", "gender": "Male", "name": "Jorge (México)"},
    "es-CO-GonzaloNeural": {"locale": "es-CO", "gender": "Male", "name": "Gonzalo (Colombia)"},
    "es-CO-SalomeNeural": {"locale": "es-CO", "gender": "Female", "name": "Salomé (Colombia)"},
    "es-AR-ElenaNeural": {"locale": "es-AR", "gender": "Female", "name": "Elena (Argentina)"},
    "es-AR-TomasNeural": {"locale": "es-AR", "gender": "Male", "name": "Tomás (Argentina)"},
    "es-CL-CatalinaNeural": {"locale": "es-CL", "gender": "Female", "name": "Catalina (Chile)"},
    "es-CL-LorenzoNeural": {"locale": "es-CL", "gender": "Male", "name": "Lorenzo (Chile)"},
    "es-PE-AlexNeural": {"locale": "es-PE", "gender": "Male", "name": "Alex (Perú)"},
    "es-PE-CamilaNeural": {"locale": "es-PE", "gender": "Female", "name": "Camila (Perú)"},
    "es-US-AlonsoNeural": {"locale": "es-US", "gender": "Male", "name": "Alonso (EE.UU.)"},
    "es-US-PalomaNeural": {"locale": "es-US", "gender": "Female", "name": "Paloma (EE.UU.)"},
}


class EdgeTTSEngine(TTSBase):
    """Microsoft Azure Edge-TTS engine.
    
    Usa la API online de Microsoft Edge para generar audio de alta calidad
    con voces neuronales. NO requiere GPU ni modelos locales.
    
    Voces más naturales recomendadas para español:
    - es-ES-AlvaroNeural (masculino, España, muy natural)
    - es-ES-ElviraNeural (femenino, España, muy natural)
    - es-MX-DaliaNeural (femenino, México, muy natural)
    - es-MX-JorgeNeural (masculino, México, muy natural)
    """
    
    def __init__(self, device: str = "auto"):
        self.device = "cpu"  # Edge-TTS usa API online, no GPU local
        self.name = "edge_tts"
        self._loaded = False
    
    def load(self) -> None:
        if edge_tts is None:
            raise ImportError("edge_tts no está instalado. Ejecuta: pip install edge-tts")
        self._loaded = True
    
    def unload(self) -> None:
        self._loaded = False
    
    def is_loaded(self) -> bool:
        return self._loaded
    
    def get_speakers(self) -> List[str]:
        return list(_EDGE_VOICES.keys())
    
    def synthesize(self, text: str, voice: Voice, output_path: str) -> str:
        if not self.is_loaded():
            self.load()
        
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        
        # Seleccionar voz: speaker_id de la voz, o default
        edge_voice = voice.speaker_id if voice.speaker_id else "es-ES-AlvaroNeural"
        
        # Edge-TTS genera MP3 por defecto; si necesitamos WAV convertimos después
        is_wav = output_path.lower().endswith(".wav")
        temp_mp3 = output_path.replace(".wav", ".mp3") if is_wav else output_path
        
        communicate = edge_tts.Communicate(text, edge_voice)
        
        # Ejecutar asyncio en contexto sincrónico
        try:
            loop = asyncio.get_running_loop()
            # Ya hay un loop corriendo (ej. dentro de Qt), usar run_coroutine_threadsafe
            future = asyncio.run_coroutine_threadsafe(communicate.save(temp_mp3), loop)
            future.result()
        except RuntimeError:
            # No hay loop corriendo
            asyncio.run(communicate.save(temp_mp3))
        
        # Convertir a WAV si es necesario (AudioPipeline espera WAV para procesar)
        if is_wav and temp_mp3 != output_path:
            self._convert_mp3_to_wav(temp_mp3, output_path)
            os.remove(temp_mp3)
        
        return output_path
    
    def _convert_mp3_to_wav(self, mp3_path: str, wav_path: str) -> None:
        """Convierte MP3 a WAV mono 24kHz para compatibilidad con AudioPipeline."""
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_mp3(mp3_path)
            audio = audio.set_channels(1).set_frame_rate(24000)
            audio.export(wav_path, format="wav")
        except ImportError:
            # Fallback: renombrar y que soundfile lo maneje (puede que no funcione con MP3)
            import shutil
            shutil.copy(mp3_path, wav_path)
    
    def clone_voice(self, reference_path: str, name: str) -> str:
        raise NotImplementedError(
            "Edge-TTS no soporta clonación de voz. "
            "Usa XTTS v2 o Bark para clonación."
        )
    
    @classmethod
    def get_voice_info(cls, voice_id: str) -> dict:
        """Retorna información de una voz Edge-TTS."""
        return _EDGE_VOICES.get(voice_id, {"locale": "es-ES", "gender": "Unknown", "name": voice_id})
