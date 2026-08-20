"""Migra los 3 canales locales al backend remoto de podcash."""
import json
import urllib.request
import urllib.error

API_BASE = "https://api.podcash.app.moonsbow.com"

CHANNELS = [
    {
        "name": "English Every Day",
        "description": "Aprende inglés práctico con una conversación bilingüe entre Alejandra (profesora) y Homero (alumno).",
        "niche": "educación / idiomas",
        "format": "podcast",
        "default_voice_id": "clone:homero_referencia:qwen3",
        "is_active": True,
        "brief": "Canal de enseñanza de inglés en formato diálogo bilingüe.\n- Personajes: Alejandra (profesora, voz femenina) y Homero (alumno, voz masculina).\n- Estructura: Alejandra presenta una frase o vocabulario en inglés, lo pronuncia con claridad, y Homero pregunta o repite. Luego Alejandra explica el significado y uso en español.\n- Idioma: mezcla 50% inglés / 50% español; el inglés debe ser natural y didáctico, el español de apoyo.\n- Tono: cercano, paciente, motivador.\n- Reglas: cada episodio introduce 5-8 expresiones útiles, incluye ejemplos de situaciones reales, y termina con un mini repaso.",
        "autopilot": False,
        "episodes_per_week": 2,
        "target_minutes": 10,
        "num_speakers": 2,
        "speaker_voices": {"Alejandra": "clone:alejandra", "Homero": "clone:homero_referencia:qwen3"},
    },
    {
        "name": "Motivacion diaria",
        "description": "Descubre consejos prácticos para mejorar tu jornada diaria y alcanzar tus objetivos. | Temporada 2: Desbloqueando el máximo potencial personal y profesional en 8 episodios",
        "niche": "motivación personal y profesional",
        "format": "motivation",
        "default_voice_id": "clone:homero_referencia",
        "is_active": True,
        "brief": "Brief de producción para el canal \"Empieza cada día mejor\"\n\nIDIOMA: Contenido hablado 100% en español, con algunas palabras o expresiones técnicas en inglés cuando sea necesario.\n\nAUDIENCIA OBJETIVO y NIVEL: Personas adultas entre 25 y 50 años, con nivel de educación secundaria completa o terciario superior, interesadas en mejorar su motivación personal y profesional para alcanzar objetivos específicos en la vida laboral y personal.\n\nTONO y ESTILO: Cercano, didáctico e inspirador, transmitiendo confianza y optimismo sin ser superficial. Nuestro tono debe ser amable pero también crítico y objetivo. Inspirar las personas a tomar acción no significa hacer la tarea por ellas.\n\nESTRUCTURA DE CADA EPISODIO: Cada episodio debe contar con las siguientes secciones:\n\n* Gancho (1-2 minutos): Introducir un tema que captue la atención del oyente y lo motive a seguir la conversación.\n* Desarrollo (10-12 minutos): Compartir consejos prácticos, experiencias reales y casos de estudio para ilustrar los conceptos básicos del tema elegido. Aportar ejemplos y técnicas concretas que cualquier persona pueda implementar en su vida diaria.\n* Cierre (2-3 minutos): Recomendar tareas prácticas o lecciones aprendidas, hacer preguntas para el oyente sobre cómo aplicar lo aprendido y brindar fuentes adicionales de información y recursos.\n\nREGLAS CONCRETAS A LAS QUE NO SE PUEDE DESCANAR: Siempre respetaremos la integridad, honestidad e interés genuino por ayudar al oyente. Evitaremos promesas exageradas, lenguaje manipulador o sensacionalista. El contenido debe ser verificable, útil y aplicable.",
        "autopilot": False,
        "episodes_per_week": 2,
        "target_minutes": 15,
        "num_speakers": 1,
        "speaker_voices": {"Narrador": "clone:homero_referencia"},
    },
    {
        "name": "Historias de Crímenes",
        "description": "Análisis de casos criminales reales con enfoque forense, psicológico y judicial. Tono dramático pero respetuoso.",
        "niche": "true crime / crímenes reales",
        "format": "podcast",
        "default_voice_id": "clone:alejandra",
        "is_active": True,
        "brief": "Brief de producción para el canal \"Historias de Crímenes\"\n\nIDIOMA: Contenido hablado 100% en español neutro.\n\nFORMATO: Podcast de true crime en monólogo narrativo. Un único locutor (Narrador/Alejandra) cuenta el caso.\n\nAUDIENCIA OBJETIVO: Adultos interesados en crímenes reales, psicología forense y análisis judicial.\n\nTONO Y ESTILO: Dramático pero respetuoso. Nunca sensacionalista. Se evitan descripciones gráficas, fotografías de autopsia o detalles innecesarios sobre la muerte de víctimas. El dramatismo proviene de la prosodia, la música y la estructura narrativa, no del morbo.\n\nÉTICA Y LÍMITES EDITORIALES:\n- Si el caso está en juicio o veredicto pendiente, se distingue claramente entre: hechos establecidos, evidencia presentada y alegaciones de cada parte.\n- No se anticipa veredicto.\n- No se presentan argumentos de fiscalía o defensa como si fueran hechos probados.\n- Se respeta la dignidad de las víctimas y sus familias.\n\nESTRUCTURA DE CADA EPISODIO (narrativa lineal con gancho):\n1. Gancho inicial (1-2 min): presentar la paradoja central o la pregunta judicial.\n2. El día de los hechos (2-3 min): qué ocurrió, dónde, cuándo, quiénes estaban involucrados.\n3. La evidencia (3-4 min): evidencia física, forense, toxicológica y sus interpretaciones.\n4. El contexto humano (3-4 min): historial psiquiátrico, personal, testimonios de personas cercanas.\n5. Las dos narrativas (3-4 min): argumentos de fiscalía y defensa, o las diferentes interpretaciones del caso.\n6. La pregunta decisiva (2-3 min): el conflicto central médico, legal o psicológico.\n7. Cierre reflexivo (1-2 min): reiterar el estado del caso si está pendiente, invitar a la reflexión, evitar conclusión forzada.\n\nVOZ Y MOTOR:\n- Voz principal: clone:alejandra (voz clonada de Alejandra).\n- Motor TTS: Higgs v3, que soporta tags de emoción inline.\n\nREGLAS DE EMOCIONES HIGGS:\n- Usar tags en formato <|emotion:NOMBRE|>.\n- Emociones permitidas: elation, amusement, enthusiasm, determination, pride, contentment, affection, relief, contemplation, confusion, surprise, awe, longing, anger, fear, disgust, bitterness, sadness, shame, helplessness.\n- Un tag de emoción por párrafo o frase clave. No saturar.\n- No usar tags de efecto sonoro como sfx:screaming.\n- Uso ocasional de <|prosody:pause|> para marcar peso narrativo.\n- Los tags deben mantenerse en el texto final porque Higgs los interpreta.\n\nDURACIÓN OBJETIVO: Entre 15 y 20 minutos. Aproximadamente 2500-2800 palabras por episodio.\n\nFUENTES: Usar solo información pública, informes de investigación del usuario o fuentes periodísticas citadas. No inventar detalles no presentes en la investigación.",
        "autopilot": True,
        "episodes_per_week": 2,
        "target_minutes": 17,
        "num_speakers": 1,
        "speaker_voices": {"Narrador": "clone:alejandra"},
    },
]


def get_token():
    with open("/tmp/login.json") as f:
        return json.load(f)["access_token"]


def create_channel(token, payload):
    req = urllib.request.Request(
        f"{API_BASE}/api/channels",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"ERROR {e.code}: {body}")
        raise


if __name__ == "__main__":
    token = get_token()
    for payload in CHANNELS:
        print(f"Creando canal: {payload['name']} ...")
        result = create_channel(token, payload)
        print(f"  → id={result['id']}")
