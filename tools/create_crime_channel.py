"""Crea el canal 'Historias de Crímenes' con la configuración usada para el episodio 72.

Uso:
    PYTHONPATH=. venv311/bin/python scripts/create_crime_channel.py
"""

import json
import urllib.request

API_BASE = "http://localhost:8000"

BRIEF = """Brief de producción para el canal "Historias de Crímenes"

IDIOMA: Contenido hablado 100% en español neutro.

FORMATO: Podcast de true crime en monólogo narrativo. Un único locutor (Narrador/Alejandra) cuenta el caso.

AUDIENCIA OBJETIVO: Adultos interesados en crímenes reales, psicología forense y análisis judicial.

TONO Y ESTILO: Dramático pero respetuoso. Nunca sensacionalista. Se evitan descripciones gráficas, fotografías de autopsia o detalles innecesarios sobre la muerte de víctimas. El dramatismo proviene de la prosodia, la música y la estructura narrativa, no del morbo.

ÉTICA Y LÍMITES EDITORIALES:
- Si el caso está en juicio o veredicto pendiente, se distingue claramente entre: hechos establecidos, evidencia presentada y alegaciones de cada parte.
- No se anticipa veredicto.
- No se presentan argumentos de fiscalía o defensa como si fueran hechos probados.
- Se respeta la dignidad de las víctimas y sus familias.

ESTRUCTURA DE CADA EPISODIO (narrativa lineal con gancho):
1. Gancho inicial (1-2 min): presentar la paradoja central o la pregunta judicial.
2. El día de los hechos (2-3 min): qué ocurrió, dónde, cuándo, quiénes estaban involucrados.
3. La evidencia (3-4 min): evidencia física, forense, toxicológica y sus interpretaciones.
4. El contexto humano (3-4 min): historial psiquiátrico, personal, testimonios de personas cercanas.
5. Las dos narrativas (3-4 min): argumentos de fiscalía y defensa, o las diferentes interpretaciones del caso.
6. La pregunta decisiva (2-3 min): el conflicto central médico, legal o psicológico.
7. Cierre reflexivo (1-2 min): reiterar el estado del caso si está pendiente, invitar a la reflexión, evitar conclusión forzada.

VOZ Y MOTOR:
- Voz principal: clone:alejandra (voz clonada de Alejandra).
- Motor TTS: Higgs v3, que soporta tags de emoción inline.

MÚSICA Y SONIDO:
- Música de fondo: arctsound-mysterious-suspense-background-no-copyright-music-252023
- Volumen de fondo: -18 dB
- El worker aplica ducking dinámico, intro/outro de branding y normalización a -16 LUFS.

REGLAS DE EMOCONES HIGGS:
- Usar tags en formato <|emotion:NOMBRE|>.
- Emociones permitidas: elation, amusement, enthusiasm, determination, pride, contentment, affection, relief, contemplation, confusion, surprise, awe, longing, anger, fear, disgust, bitterness, sadness, shame, helplessness.
- Un tag de emoción por párrafo o frase clave. No saturar.
- No usar tags de efecto sonoro como sfx:screaming.
- Uso ocasional de <|prosody:pause|> para marcar peso narrativo.
- Los tags deben mantenerse en el texto final porque Higgs los interpreta.

DURACIÓN OBJETIVO: Entre 15 y 20 minutos. Aproximadamente 2500-2800 palabras por episodio.

FUENTES: Usar solo información pública, informes de investigación del usuario o fuentes periodísticas citadas. No inventar detalles no presentes en la investigación.
"""

CHANNEL_PAYLOAD = {
    "name": "Historias de Crímenes",
    "description": "Análisis de casos criminales reales con enfoque forense, psicológico y judicial. Tono dramático pero respetuoso.",
    "niche": "true crime / crímenes reales",
    "format": "podcast",
    "default_voice_id": "clone:alejandra",
    "is_active": True,
    "brief": BRIEF,
    "autopilot": True,
    "episodes_per_week": 2,
    "target_minutes": 17,
    "num_speakers": 1,
    "speaker_voices": {"Narrador": "clone:alejandra"},
    "background_music": "arctsound-mysterious-suspense-background-no-copyright-music-252023",
    "bg_music_volume": -18.0,
}


def create_channel():
    req = urllib.request.Request(
        f"{API_BASE}/api/channels",
        data=json.dumps(CHANNEL_PAYLOAD).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def create_plan_entry(channel_id: int):
    payload = {
        "title": "El caso Lindsay Clancy: ¿enfermedad mental o responsabilidad criminal?",
        "description": "Tres niños muertos en Duxbury, Massachusetts. El juicio de Lindsay Clancy explora el límite entre enfermedad mental y responsabilidad criminal.",
    }
    req = urllib.request.Request(
        f"{API_BASE}/api/channels/{channel_id}/plan",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


if __name__ == "__main__":
    channel = create_channel()
    print("Canal creado:")
    print(json.dumps(channel, indent=2, ensure_ascii=False))
    entry = create_plan_entry(channel["id"])
    print("\nEntrada de plan creada:")
    print(json.dumps(entry, indent=2, ensure_ascii=False))
