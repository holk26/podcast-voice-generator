# Lindsay Clancy Podcast Episode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generar un episodio de podcast de 15–20 minutos sobre el caso Lindsay Clancy usando la voz clonada Alejandra (Higgs), emociones Higgs incrustadas y música de fondo.

**Architecture:** Se escribe un guion en español basado en el informe de investigación, con tags de emoción Higgs. Luego se crea un registro `Episode` en la API FastAPI con los parámetros correctos. El worker de generación se encarga de la síntesis TTS, mezcla de música, intro/outro y normalización.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy, Higgs TTS, pydub, ffmpeg.

---

## Files

- **Source:** `caso Lindsay Clancy/Lindsay Clancy_ Informe de investigación y análisis de evidencia.md`
- **Music:** `sfx_library/music/arctsound-mysterious-suspense-background-no-copyright-music-252023.mp3`
- **Voice reference:** `voices/clones/alejandra.wav`
- **API:** `http://localhost:8000/api/episodes`
- **Script auxiliar:** `scripts/create_lindsay_clancy_episode.py` (crear para ejecutar pasos de forma reproducible)

---

### Task 1: Verificar entorno y voz

**Files:**
- Read: `voices/clones/alejandra.wav`
- Read: `sfx_library/music/arctsound-mysterious-suspense-background-no-copyright-music-252023.mp3`
- Command: health checks

- [ ] **Step 1: Verificar que la voz de Alejandra existe**

```bash
ls -la voices/clones/alejandra.wav
```

Expected: file exists, 24000 Hz mono.

- [ ] **Step 2: Verificar que la música de fondo existe**

```bash
ls -la "sfx_library/music/arctsound-mysterious-suspense-background-no-copyright-music-252023.mp3"
```

Expected: file exists.

- [ ] **Step 3: Verificar que la API está activa**

```bash
curl -s http://localhost:8000/api/health | head -c 200
```

Expected: HTTP 200 / healthy response.

- [ ] **Step 4: Verificar que el worker está activo**

```bash
curl -s http://localhost:8001/health | head -c 200
```

Expected: HTTP 200 / healthy response.

---

### Task 2: Escribir el guion con emociones Higgs

**Files:**
- Create: `scripts/create_lindsay_clancy_episode.py`
- Reference: `docs/superpowers/specs/2026-08-08-lindsay-clancy-podcast-design.md`
- Reference: `caso Lindsay Clancy/Lindsay Clancy_ Informe de investigación y análisis de evidencia.md`

- [ ] **Step 1: Definir el string `SCRIPT` con las 7 secciones y tags Higgs**

Insertar en `scripts/create_lindsay_clancy_episode.py`:

```python
SCRIPT = """
<|emotion:contemplation|> Tres niños. Una madre. Una llamada al nueve once. Y una pregunta que un jurado de Massachusetts está tratando de responder: ¿qué estaba ocurriendo realmente en la mente de Lindsay Clancy el veinticuatro de enero de dos mil veintitrés?

<|emotion:sadness|> Este es el caso Commonwealth contra Lindsay Clancy. Un caso que no se reduce a saber qué pasó físicamente en aquella casa de Duxbury. Lo que está en juego es si Lindsay Clancy podía entender o controlar sus acciones.

<|emotion:fear|> Esa tarde de enero, Patrick Clancy, el esposo de Lindsay, salió de la vivienda. Cuando regresó, la escena que encontró lo llevó a llamar de inmediato a emergencias. Los tres hijos de la pareja, Cora de cinco años, Dawson de tres y Callan de apenas ocho meses, habían muerto.

<|emotion:helplessness|> Lindsay sobrevivió a un intento posterior de suicidio, pero quedó con graves consecuencias físicas. Desde entonces, el caso ha generado un debate mucho más amplio: el de la salud mental, la maternidad y la responsabilidad penal.

<|emotion:contemplation|> La investigación recopiló evidencia física en la vivienda: objetos, fotografías, muestras biológicas, documentación personal y comunicaciones. Los investigadores también buscaron huellas dactilares en objetos relevantes. Algunas de esas huellas no fueron utilizables. Eso no demuestra inocencia, pero tampoco establece identificación por ese medio.

<|emotion:confusion|> La evidencia toxicológica es una de las piezas más debatidas. Se encontraron medicamentos psiquiátricos prescritos: mirtazapina, lamotrigina, trazodona y quetiapina. El toxicólogo Justin Brower declaró que la quetiapina estaba algo elevada, pero que los niveles no correspondían a una sobredosis tóxica. Ni la intoxicación ni la ausencia de ella explican por sí solas el comportamiento.

<|emotion:contemplation|> Para la defensa, los medicamentos forman parte de un contexto más amplio: una mujer en crisis psiquiátrica, bajo tratamiento. Para la fiscalía, los resultados cuestionan la teoría de que una sobredosis o una intoxicación provocaron lo ocurrido.

<|emotion:sadness|> El historial psiquiátrico de Lindsay Clancy es el corazón del juicio. Antes de los hechos ya había sido documentada con depresión, ansiedad, insomnio, pensamientos suicidas y una sensación creciente de estar sobrepasada.

<|emotion:longing|> A comienzos de enero de dos mil veintitrés, Lindsay ingresó voluntariamente en el McLean Hospital. Allí recibió tratamiento por depresión, ansiedad, insomnio y pensamientos suicidas. Los profesionales que la atendieron declararon posteriormente que no observaron características psicóticas durante esa hospitalización.

<|emotion:contemplation|> Uno de los diagnósticos discutidos fue trastorno depresivo mayor grave, sin características psicóticas. Esa ausencia de diagnóstico de psicosis es una pieza clave para la fiscalía, porque la defensa necesita demostrar que una enfermedad psicótica pudo haberse desarrollado o no haber sido detectada.

<|emotion:sadness|> El diario personal de Lindsay es otra de las evidencias más importantes. En sus páginas se leen ansiedad, problemas de sueño, culpa, sentirse abrumada y pensamientos perturbadores. La defensa puede usarlo para mostrar un deterioro progresivo. La fiscalía puede argumentar que demuestra que Lindsay comprendía su situación y mantenía cierta organización cognitiva.

<|emotion:longing|> Patrick Clancy, el esposo de Lindsay, también declaró. Ha descrito a su mujer como una madre afectuosa y dedicada. También ha hablado de su deterioro psicológico. Incluso ha expresado públicamente que perdona a Lindsay y cree que la enfermedad mental tuvo un papel fundamental. Pero sus opiniones personales no determinan la responsabilidad criminal. Esa decisión corresponde al jurado.

<|emotion:contemplation|> La fiscalía ha presentado además evidencia de comunicaciones, mensajes, planes familiares y actividades previas. Todo ello puede interpretarse como organización, planificación y capacidad para tomar decisiones.

<|emotion:bitterness|> La defensa responde que una persona con una enfermedad mental grave puede mantener conversaciones normales y realizar actividades cotidianas incluso durante una crisis psiquiátrica. La superficie puede parecer controlada mientras algo mucho más profundo se descompone.

<|emotion:contemplation|> Así, el juicio enfrenta dos narrativas. La fiscalía sostiene que Clancy actuó deliberadamente, con conocimiento de sus circunstancias, y cuestiona que existiera una psicosis que eliminara su responsabilidad. La defensa sostiene que Lindsay experimentó un deterioro psicológico progresivo, que su condición pudo evolucionar hacia algo mucho más grave, y que la psicosis posparto pudo haber afectado su percepción de la realidad.

<|emotion:awe|> Aquí es importante aclarar algo: depresión posparto y psicosis posparto no son lo mismo. La psicosis posparto es una condición mucho más grave que puede incluir alteraciones importantes de la percepción de la realidad. Pero tener psicosis posparto no determina automáticamente la ausencia de responsabilidad criminal. Eso depende de la ley y de la evidencia médica concreta.

<|emotion:confusion|> El caso no es sencillo porque hay un conflicto entre dos tipos de evidencia. La médica habla de diagnósticos, síntomas, medicamentos y hospitalizaciones. La conductual habla de planificación, comunicaciones, acciones y decisiones. El jurado debe decidir cómo se relacionan ambas.

<|emotion:contemplation|> Durante el juicio surgió un desarrollo jurídico paralelo. La Corte Suprema Judicial de Massachusetts ordenó un nuevo juicio en el caso de Latarsha Sanders, por la exclusión de registros psiquiátricos que podían ser relevantes para la defensa. El juez William Sullivan está relacionado con ambos procedimientos. Esto no predetermina el resultado del caso Clancy, pero es un contexto que merece seguimiento.

<|emotion:sadness|> La pregunta decisiva del juicio puede resumirse así: ¿qué estaba ocurriendo psicológicamente con Lindsay Clancy en el momento exacto de los hechos? No basta con demostrar que estaba deprimida. No basta con demostrar que tomaba medicamentos. No basta con demostrar que había sido hospitalizada. Tampoco basta con demostrar que podía mantener una conversación normal.

<|emotion:contemplation|> El jurado debe valorar la totalidad de la evidencia: los registros médicos, el diario, la evidencia física, las comunicaciones, los testimonios y el comportamiento de Lindsay antes y después de aquel día.

<|emotion:helplessness|> Al siete de agosto de dos mil veintiséis, el juicio continúa. No hay veredicto. No hay conclusión judicial definitiva sobre la responsabilidad criminal de Lindsay Clancy.

<|emotion:contemplation|> Lo que sí queda es una historia que obliga a reflexionar sobre cómo identificamos las crisis de salud mental, cómo distinguimos la enfermedad de la responsabilidad, y hasta qué punto una sociedad está dispuesta a escuchar lo que ocurre bajo la superficie de una familia que parece funcionar.

<|emotion:sadness|> Este episodio no intenta dar una respuesta. Solo intenta contar, con el respeto que merecen las víctimas, las complejidades de un caso donde la tragedia y el derecho se encuentran en un mismo tribunal.
""".strip()
```

- [ ] **Step 2: Validar que todos los tags Higgs son reconocidos**

```python
import re
from core.emotion_tags import HIGGS_TAGS

tags = re.findall(r"<\|([a-z]+:[a-z_]+)\|>", SCRIPT)
invalid = [t for t in tags if t not in HIGGS_TAGS]
assert not invalid, f"Invalid Higgs tags: {invalid}"
print(f"OK: {len(tags)} Higgs tags, all valid")
```

Expected: `OK: N Higgs tags, all valid` with no invalid tags.

- [ ] **Step 3: Estimar duración de lectura**

```python
words = len(SCRIPT.split())
minutes = words / 150  # ritmo pausado para narración dramática
print(f"Palabras: {words}, duración estimada: {minutes:.1f} min")
```

Expected: entre 15 y 20 minutos.

---

### Task 3: Crear el episodio en la API

**Files:**
- Modify: `scripts/create_lindsay_clancy_episode.py`

- [ ] **Step 1: Añadir la función `create_episode`**

```python
import json
import urllib.request

API_BASE = "http://localhost:8000"


def create_episode():
    payload = {
        "title": "El caso Lindsay Clancy: ¿enfermedad mental o responsabilidad criminal?",
        "type": "podcast",
        "source_text": SCRIPT,
        "voice_id": "clone:alejandra",
        "target_duration_minutes": 17,
        "background_music": "arctsound-mysterious-suspense-background-no-copyright-music-252023",
        "bg_music_volume": -18.0,
    }
    req = urllib.request.Request(
        f"{API_BASE}/api/episodes",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


if __name__ == "__main__":
    episode = create_episode()
    print(json.dumps(episode, indent=2, ensure_ascii=False))
```

- [ ] **Step 2: Ejecutar el script y obtener el `episode_id`**

```bash
source venv311/bin/activate
python scripts/create_lindsay_clancy_episode.py
```

Expected: JSON con `id`, `status: pending`, `voice_id: clone:alejandra`.

---

### Task 4: Monitorear la generación del audio

**Files:**
- Command line polling

- [ ] **Step 1: Consultar estado del episodio cada pocos segundos**

```bash
EPISODE_ID=1  # reemplazar por el id devuelto
curl -s "http://localhost:8000/api/episodes/$EPISODE_ID" | python -m json.tool
```

Expected: `status` pasa de `pending` → `completed` o `failed`.

- [ ] **Step 2: En caso de fallo, leer logs**

```bash
tail -n 100 logs/worker.log
```

Expected: identificar el error.

---

### Task 5: Verificar y reproducir el episodio final

**Files:**
- Output: `output/<episode_id>/final.wav`

- [ ] **Step 1: Confirmar que el archivo de audio existe**

```bash
EPISODE_ID=1
ls -lh "output/$EPISODE_ID/final.wav"
```

Expected: archivo WAV generado, duración cercana a 15–20 min.

- [ ] **Step 2: Revisar duración con ffprobe**

```bash
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "output/$EPISODE_ID/final.wav"
```

Expected: duración entre 900 y 1200 segundos.

- [ ] **Step 3: Confirmar que el audio contiene música de fondo**

Reproducir el archivo o inspeccionar visualmente la forma de onda. El espectro debe mostrar componentes musicales continuos bajo la voz.

---

## Self-Review

- **Spec coverage:** cada sección del spec §4 está representada en el `SCRIPT`.
- **Placeholder scan:** no hay TBD ni TODO; el guion está completo.
- **Type consistency:** `voice_id` coincide con `clone:alejandra`, `background_music` sin extensión, `bg_music_volume` float.
