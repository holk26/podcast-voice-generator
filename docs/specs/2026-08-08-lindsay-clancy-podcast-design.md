# Diseño: Episodio podcast — Caso Lindsay Clancy

**Fecha:** 8 de agosto de 2026  
**Estado:** Aprobado por el usuario  
**Tipo de entrega:** Contenido (guion + episodio generado)

---

## 1. Objetivo

Crear un episodio de podcast de 15–20 minutos sobre el caso *Commonwealth v. Lindsay Clancy*, a partir del informe de investigación del usuario. El episodio debe:

- Contar la historia con un tono dramático pero respetuoso.
- Usar la voz clonada **Alejandra** con el motor **Higgs**.
- Incrustar emociones en formato Higgs (`<|emotion:...|>`).
- Incluir música de fondo: `arctsound-mysterious-suspense-background-no-copyright-music-252023.mp3`.
- No anticipar veredicto ni reproducir argumentos como hechos establecidos.

---

## 2. Restricciones y criterios editoriales

- **Caso sensible:** muerte de tres menores. No se incluyen descripciones gráficas, fotografías de autopsia ni sensacionalismo.
- **Juicio en curso** (al 7 de agosto de 2026). Se distingue entre: hechos establecidos, evidencia presentada y alegaciones de cada parte.
- **Fuentes:** solo el informe de investigación del usuario y las fuentes citadas en él.
- **Idioma:** español neutro.

---

## 3. Parámetros técnicos

| Campo | Valor |
|---|---|
| `title` | El caso Lindsay Clancy: ¿enfermedad mental o responsabilidad criminal? |
| `type` | podcast |
| `voice_id` | `clone:alejandra` |
| `engine` | higgs (soporta tags de emoción) |
| `background_music` | `arctsound-mysterious-suspense-background-no-copyright-music-252023` |
| `bg_music_volume` | -18 dB (default del worker) |
| `target_duration_minutes` | 17 (estimado centro del rango 15–20) |

La ruta física de la música coincide con `sfx_library/music/arctsound-mysterious-suspense-background-no-copyright-music-252023.mp3`.

---

## 4. Estructura narrativa

### 4.1. Gancho inicial (0:00–1:30)

- Abrir con la paradoja central: madre afectuosa, tres niños muertos, un juicio que pregunta qué pasaba en su mente.
- Emociones: `contemplation`, `sadness`.

### 4.2. El día de los hechos (1:30–4:00)

- 24 de enero de 2023, Duxbury, Massachusetts.
- Patrick Clancy sale, regresa, llamada al 911.
- Lindsay sobrevive a intento de suicidio con consecuencias físicas graves.
- Emociones: `fear`, `helplessness`.

### 4.3. La evidencia (4:00–7:30)

- Evidencia física recogida en la vivienda.
- Huellas dactilares no utilizables en algunos objetos.
- Toxicología: mirtazapina, lamotrigina, trazodona, quetiapina. Niveles no tóxicos.
- Interpretación de ambas partes.
- Emociones: `contemplation`, `confusion`.

### 4.4. El historial psiquiátrico (7:30–11:00)

- Antecedentes: depresión, ansiedad, insomnio, pensamientos suicidas.
- Hospitalización voluntaria en McLean Hospital a comienzos de enero de 2023.
- Diagnóstico: trastorno depresivo mayor grave sin características psicóticas.
- Diario personal: ansiedad, culpa, sentirse sobrepasada.
- Testimonio de Patrick Clancy: madre afectuosa, deterioro psicológico, perdón.
- Emociones: `sadness`, `longing`.

### 4.5. Las dos narrativas (11:00–15:00)

- **Fiscalía:** conducta organizada, planificación, comunicaciones, ausencia de sobredosis, sin psicosis documentada.
- **Defensa:** deterioro progresivo, posible psicosis posparto no detectada, efectos de medicamentos.
- Emociones: `bitterness`, `contemplation`.

### 4.6. La pregunta decisiva (15:00–18:00)

- Diferencia entre depresión posparto y psicosis posparto.
- Conflicto entre evidencia médica y evidencia conductual.
- Caso paralelo de Latarsha Sanders y su posible relevancia.
- Emociones: `awe`, `confusion`.

### 4.7. Cierre reflexivo (18:00–19:30)

- El juicio continúa; veredicto pendiente.
- Reflexión sobre salud mental, maternidad y responsabilidad legal.
- Emociones: `sadness`, `contemplation`.

---

## 5. Reglas de emociones Higgs

- Emociones permitidas del motor Higgs v3: `elation`, `amusement`, `enthusiasm`, `determination`, `pride`, `contentment`, `affection`, `relief`, `contemplation`, `confusion`, `surprise`, `awe`, `longing`, `arousal`, `anger`, `fear`, `disgust`, `bitterness`, `sadness`, `shame`, `helplessness`.
- Un tag de emoción por párrafo o frase clave. No se saturan.
- No se usan tags de efecto sonoro (`sfx:screaming`, etc.).
- Uso ocasional de `<|prosody:pause|>` para marcar peso narrativo.
- Los tags se mantienen en el texto final porque el motor Higgs los interpreta; el worker los pasa a la API de TTS que sanitiza solo para motores que no los soportan.

---

## 6. Flujo de generación

1. Redactar el guion completo con tags Higgs en una variable/string.
2. Crear el episodio mediante `POST /api/episodes` con los parámetros del §3.
3. El worker detecta el episodio en estado `pending` y:
   - Delega la síntesis en `/api/tts/synthesize` (motor Higgs con voz clonada Alejandra).
   - Aplica música de fondo con ducking dinámico.
   - Añade intro/outro de branding.
   - Normaliza a -16 LUFS.
4. El episodio queda en estado `completed` con `audio_url` disponible.

---

## 7. Criterios de aceptación

- [ ] El guion tiene entre 15 y 20 minutos de lectura estimada.
- [ ] Todos los tags de emoción están en formato Higgs válido.
- [ ] Se distingue claramente entre hechos, evidencia y alegaciones.
- [ ] No hay descripciones gráficas ni anticipación de veredicto.
- [ ] El episodio se crea en la base de datos con `voice_id="clone:alejandra"`.
- [ ] El audio final incluye la música de fondo solicitada.
- [ ] El episodio alcanza estado `completed`.

---

## 8. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Error de VRAM al cargar Higgs | Usar la API (`/api/tts/synthesize`) para que el motor ya esté cargado; no crear una segunda instancia en el worker. |
| Tags Higgs mal formateados | Validar con la expresión regular del proyecto antes de enviar. |
| Música no encontrada | Verificar que el archivo existe en `sfx_library/music/` con nombre exacto. |
| Duración excesiva | Trocear el texto en chunks de ~400 caracteres para Higgs, como ya hace la API. |
| Tono inadecuado | Revisar el guion antes de enviar a síntesis; evitar lenguaje sensacionalista. |
