# Patrick Clancy Episodio 2 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generar un episodio de podcast de 15–20 minutos para el canal Historias de Crímenes, basado en `Episodio_2_Patrick_Clancy_FINAL_para_grabar.pdf`, usando la API REST y el worker local.

**Architecture:** Se adapta el guion del PDF a ~2500 palabras con tags de emoción Higgs, se envía mediante `curl` a `POST /api/episodes`, el worker reclama el trabajo, sintetiza la voz `clone:alejandra` con Higgs v3, mezcla música de fondo y normaliza a -16 LUFS.

**Tech Stack:** FastAPI backend, local worker, Higgs v3 TTS, curl, Python 3.11, ffprobe.

---

## Files

- **Source:** `Episodio_2_Patrick_Clancy_FINAL_para_grabar.pdf`
- **Script auxiliar:** `scripts/patrick_clancy_ep2_script.txt`
- **Payload:** `scripts/patrick_clancy_ep2_payload.json`
- **Music:** `sfx_library/music/arctsound-mysterious-suspense-background-no-copyright-music-252023.mp3`
- **Voice reference:** `voices/clones/alejandra.wav`
- **API:** `http://localhost:8000/api/episodes`
- **Output:** `output/<episode_id>/final.wav`

---

### Task 1: Verificar entorno y recursos

**Files:**
- Read: `voices/clones/alejandra.wav`
- Read: `sfx_library/music/arctsound-mysterious-suspense-background-no-copyright-music-252023.mp3`
- Command: health checks

- [ ] **Step 1: Verificar que la voz de Alejandra existe**

```bash
ls -la voices/clones/alejandra.wav
```

Expected: file exists.

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

- [ ] **Step 5: Si alguno no responde, levantar servicios**

```bash
python starter.py
```

Expected: api, worker y web arrancan; logs en `logs/`. `Ctrl+C` para detener al final.

---

### Task 2: Escribir el guion adaptado con emociones Higgs

**Files:**
- Create: `scripts/patrick_clancy_ep2_script.txt`
- Reference: `docs/superpowers/specs/2026-08-27-patrick-clancy-episodio2-design.md`
- Reference: `Episodio_2_Patrick_Clancy_FINAL_para_grabar.pdf`

- [ ] **Step 1: Crear el archivo con el guion adaptado**

Create `scripts/patrick_clancy_ep2_script.txt` with the following content (UTF-8, LF):

```text
<|emotion:contemplation|> Hay algo extraño que pasó durante el juicio de Lindsay Clancy. Mientras doce jurados estaban sentados en una corte de Massachusetts intentando decidir qué ocurrió dentro de una casa en Duxbury, miles de personas en internet empezaron su propia investigación. Pero su sospechoso no era Lindsay. Era Patrick. Su esposo. El padre de Cora, Dawson y Callan. Y cuanto más avanzaba el juicio, más preguntas aparecían: un email enviado a las cinco veinticuatro. Un Apple Watch. Una conversación que nadie más escuchó. Un viaje a Costa Rica. Una nueva vida en New York. Y una investigación policial que el propio abogado de Lindsay describió con tres palabras: there was no investigation.

<|emotion:contemplation|> Hoy no quiero preguntarte si Patrick es culpable. La evidencia presentada no demuestra eso. Quiero hacer una pregunta mucho más interesante: ¿cómo pasó Patrick Clancy de ser el padre sobreviviente de una tragedia inimaginable a convertirse en el protagonista de una de las teorías de true crime más grandes de internet?

<|emotion:sadness|> Patrick y Lindsay se conocieron en South Boston en mayo de dos mil trece. Empezaron a salir ese verano, se mudaron juntos en dos mil quince, se casaron en diciembre de dos mil dieciséis. Cora nació en dos mil diecisiete, Dawson después, y en mayo de dos mil veintidós llegó Callan. Desde afuera, todo parecía normal: matrimonio, tres niños, una casa en los suburbios. Lindsay era enfermera. Patrick trabajaba en tecnología. Pero después del nacimiento de Callan, la salud mental de Lindsay empezó a deteriorarse. Y esa parte de la historia terminaría convirtiéndose en el centro del juicio.

<|emotion:fear|> El veinticuatro de enero de dos mil veintitrés, Lindsay le pide a Patrick que salga a comprar un medicamento infantil en CVS y recoger comida en tres V. La fiscalía sostiene que ella buscó las distancias para crear una ventana en la que estaría sola. Patrick sale alrededor de las cinco quince de la tarde. Nueve minutos después, a las cinco veinticuatro, envía un email de trabajo. Ese detalle años después internet lo convertiría en dinamita. La versión viral dice: si el email salió del Surface Pro que estaba en casa, Patrick todavía estaba allí. Pero no quedó probado que saliera físicamente de ese computador. Y además, cámaras lo muestran entrando a CVS aproximadamente a las cinco treinta y dos.

<|emotion:confusion|> La última lectura de frecuencia cardíaca del Apple Watch de Lindsay aparece alrededor de las cinco veintitrés cincuenta y dos. Aproximadamente un minuto después tenemos el email de Patrick. ¿Spicy? Sí. ¿Prueba? No. Una lectura que termina no es automáticamente una hora de muerte. Y un email enviado a las cinco veinticuatro no coloca automáticamente al remitente frente a un computador determinado. Pero cuando dos timestamps caen casi juntos dentro de una ventana ya extremadamente apretada, internet hace lo que internet hace: los conecta.

<|emotion:fear|> Patrick recoge la comida y vuelve a casa. Según su testimonio, llama a su familia y nadie responde. Encuentra la puerta del dormitorio principal cerrada, busca una llave, entra, ve la ventana abierta y sangre. Sale corriendo y encuentra a Lindsay debajo de la ventana gravemente herida. Y entonces Patrick dice que Lindsay le habló. Que ella le comunicó que había intentado suicidarse y que los niños estaban en el basement. Patrick entra y encuentra a los niños.

<|emotion:helplessness|> Años después, durante el juicio, el doctor Saathoff escuchó la llamada al nueve once y reconoció que no oye a Lindsay dar una respuesta verbal comprensible. Oye sonidos guturales. Pero Saathoff también sostuvo que médicamente ella pudo haber hablado antes y deteriorarse después. No podemos decir que Patrick inventó la conversación. Pero sí podemos decir algo inquietante: una de las piezas más importantes de la reconstrucción depende de una conversación que, según el material del juicio, solamente Patrick afirma haber escuchado.

<|emotion:contemplation|> Seis días después de las muertes, Patrick publicó una declaración pidiendo a la gente que perdone a Lindsay, como él dice haberla perdonado. Habla de ella como una madre amorosa. Si uno quisiera construir la historia de que Patrick estaba intentando convertir inmediatamente a Lindsay en una asesina fría, esta declaración no encaja cómodamente. ¿Demuestra inocencia? Tampoco. Pero es un dato que cualquier teoría seria tiene que incorporar.

<|emotion:surprise|> Semanas después de las muertes, Patrick viajó a Costa Rica. Y años más tarde internet descubrió que Rachel Danis, la mujer con la que Patrick terminaría casándose, también había viajado a Costa Rica en febrero de dos mil veintitrés. Imagínate el screenshot: esposo viudo, futura esposa, mismo país, mismo mes. Boom. Teoría instantánea. Algunas publicaciones incluso empezaron a decir que estuvieron veinte días juntos. Pero cuando revisamos los registros migratorios reportados, Rachel estuvo en Costa Rica aproximadamente del uno al cinco de febrero. Patrick estuvo del veintiuno al veintiséis. No coinciden. Y Patrick no estuvo veinte días. Fueron aproximadamente cinco. Este es el ejemplo perfecto de por qué este caso necesita fact-check.

<|emotion:longing|> Durante dos mil veintitrés Patrick vende o deja atrás la casa de Duxbury y se muda a New York City. En dos mil veinticuatro se sitúa públicamente en una relación con Rachel Danis, médica especializada en endocrinología reproductiva. Más tarde viven juntos y finalmente se casan en abril de dos mil veintiséis en Central Park. En dos mil veinticuatro Patrick corre el Boston Marathon en memoria de Cora, Dawson y Callan. Termina alrededor de cuatro horas y recauda más de setenta y cinco mil dólares para Boston Children's Hospital. Lleva a sus hijos literalmente sobre su camiseta. Para unos, es un padre intentando convertir un dolor imposible en algo bueno. Para otros, todo gesto público posterior es sospechoso.

<|emotion:awe|> En dos mil veinticuatro Patrick y sus hermanas crean Heard Foundation, una organización sin fines de lucro en memoria de los niños. Su misión es mejorar la salud mental perinatal: reducir estigma, ampliar acceso e impulsar un centro dedicado al tratamiento de madres y familias en Massachusetts. En dos mil veinticinco Heard Foundation participa en la construcción del Clancy Family Playground en Duxbury, con detalles dedicados a cada niño. La fundación no construye su misión alrededor de una madre malvada. La construye alrededor de la idea de que una crisis de salud mental perinatal terminó en una tragedia.

<|emotion:contemplation|> Vamos a poner las teorías sobre la mesa, no porque sean verdad, sino para ver cuáles sobreviven cuando las contrastamos con evidencia. ¿Patrick todavía estaba en casa a las cinco veinticuatro? No quedó probado que el email saliera del Surface Pro, y aparece en CVS minutos después. ¿El Apple Watch marca el momento real? Coincidencia cinematográfica, no prueba. ¿Lindsay no podía hablar, así que Patrick inventó todo? El nueve once no contiene respuestas verbales comprensibles, pero médicamente ella pudo hablar antes y deteriorarse. ¿Cómo supo ir al basement? Pregunta legítima, pero depende de demostrar primero que la conversación no ocurrió. ¿La sangre en la manija demuestra otra persona? Sin análisis completo de origen y DNA, no podemos hacer ese salto. ¿Rachel era la amante? No hay evidencia pública fiable de una relación romántica en enero de dos mil veintitrés. ¿Patrick y Rachel se encontraron en Costa Rica? Las fechas publicadas contradicen la versión viral.

<|emotion:bitterness|> Esta teoría se volvió enorme porque tiene todos los ingredientes que internet ama: un esposo que sobrevive, una cronología de minutos, tecnología, una nueva esposa, un viaje tropical, una investigación cuestionada. Parece escrito para Netflix. Pero la vida real tiene un problema que los thrillers no tienen: las coincidencias no están obligadas a resolver la historia.

<|emotion:contemplation|> Entonces, ¿quién es Patrick Clancy? Hay tres respuestas. El Patrick antes del veinticuatro de enero: esposo, padre, trabajador de tecnología. El Patrick de aquella noche: el único adulto que regresa a la escena, testigo de conversaciones que nadie más escuchó. Y el Patrick después: un hombre que pide perdón para Lindsay, viaja, se muda a New York, se vuelve a casar, corre un marathon por sus hijos, crea una fundación de salud mental perinatal, construye un playground en su memoria y demanda a los médicos que trataron a Lindsay. Puedes mirar esos mismos hechos y construir historias completamente diferentes. Y precisamente por eso existe un juicio.

<|emotion:contemplation|> No tenemos un nuevo culpable. Pero después de tres semanas de juicio, la defensa hace una pregunta incómoda: ¿cuántas cosas de esta historia sabemos porque fueron demostradas... y cuántas sabemos porque, desde el primer día, todos asumimos que eran verdad?
```

- [ ] **Step 2: Validar que todos los tags Higgs son reconocidos**

```bash
source .venv/bin/activate
python - <<'PY'
import re
from core.emotion_tags import HIGGS_TAGS

with open("scripts/patrick_clancy_ep2_script.txt", "r", encoding="utf-8") as f:
    text = f.read()

tags = re.findall(r"<\|([a-z]+:[a-z_]+)\|>", text)
invalid = [t for t in tags if t not in HIGGS_TAGS]
assert not invalid, f"Invalid Higgs tags: {invalid}"
words = len(text.split())
minutes = words / 150
print(f"OK: {len(tags)} Higgs tags, all valid")
print(f"Palabras: {words}, duración estimada: {minutes:.1f} min")
PY
```

Expected: `OK: N Higgs tags, all valid` and duration between 15 and 20 minutes.

---

### Task 3: Crear el payload JSON y enviarlo a la API

**Files:**
- Create: `scripts/patrick_clancy_ep2_payload.json`
- Command: curl

- [ ] **Step 1: Generar el payload JSON**

```bash
source .venv/bin/activate
python - <<'PY'
import json

with open("scripts/patrick_clancy_ep2_script.txt", "r", encoding="utf-8") as f:
    script = f.read()

payload = {
    "title": "Patrick Clancy: el hombre que internet puso bajo investigación",
    "type": "podcast",
    "source_text": script,
    "voice_id": "clone:alejandra",
    "target_duration_minutes": 17,
    "background_music": "arctsound-mysterious-suspense-background-no-copyright-music-252023",
    "bg_music_volume": -18.0,
}

with open("scripts/patrick_clancy_ep2_payload.json", "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False)

print("Payload written to scripts/patrick_clancy_ep2_payload.json")
PY
```

Expected: file created, no errors.

- [ ] **Step 2: Enviar el episodio a la API con curl**

```bash
curl -s -X POST http://localhost:8000/api/episodes \
  -H "Content-Type: application/json" \
  -d @scripts/patrick_clancy_ep2_payload.json \
  | python -m json.tool
```

Expected: JSON con `id`, `status: pending`, `voice_id: clone:alejandra`. Guardar el `id` como `EPISODE_ID`.

---

### Task 4: Monitorear la generación del audio

**Files:**
- Command line polling

- [ ] **Step 1: Consultar estado del episodio hasta completar o fallar**

```bash
EPISODE_ID=<id-devuelto>
while true; do
  STATUS=$(curl -s "http://localhost:8000/api/episodes/$EPISODE_ID" | python -c 'import sys,json;print(json.load(sys.stdin)["status"])')
  echo "$(date -Iseconds) status=$STATUS"
  if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then break; fi
  sleep 10
done
```

Expected: `status` pasa de `pending` → `running` → `completed`.

- [ ] **Step 2: En caso de fallo, leer logs**

```bash
tail -n 200 logs/worker.log
```

Expected: identificar el error.

---

### Task 5: Verificar y reproducir el episodio final

**Files:**
- Output: `output/<episode_id>/final.wav`

- [ ] **Step 1: Confirmar que el archivo de audio existe**

```bash
EPISODE_ID=<id-devuelto>
ls -lh "output/$EPISODE_ID/final.wav"
```

Expected: archivo WAV generado.

- [ ] **Step 2: Revisar duración con ffprobe**

```bash
EPISODE_ID=<id-devuelto>
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "output/$EPISODE_ID/final.wav"
```

Expected: duración entre 900 y 1200 segundos.

- [ ] **Step 3: Confirmar que el audio contiene música de fondo**

Reproducir el archivo o inspeccionar visualmente la forma de onda. El espectro debe mostrar componentes musicales continuos bajo la voz.

---

## Self-Review

- **Spec coverage:** cada sección del spec está representada en el guion adaptado.
- **Placeholder scan:** no hay TBD ni TODO; el guion y los comandos son completos.
- **Type consistency:** `voice_id` coincide con `clone:alejandra`, `background_music` sin extensión, `bg_music_volume` float.
