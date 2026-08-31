# Diseño: Episodio 2 — Patrick Clancy (Historias de Crímenes)

## Objetivo

Generar un episodio de podcast de 15–20 minutos para el canal **Historias de Crímenes**, basado en el guion entregado en `Episodio_2_Patrick_Clancy_FINAL_para_grabar.pdf`.

## Alcance

- Adaptar y condensar el guion del PDF a ~2500–2800 palabras.
- Añadir tags de emoción Higgs inline compatibles con la voz `clone:alejandra`.
- Crear un registro `Episode` en la API FastAPI mediante `curl`.
- Dejar que el worker local genere el audio final (TTS + música + masterización).
- Verificar que el archivo `output/<episode_id>/final.wav` se genere correctamente.

## Fuente

- `Episodio_2_Patrick_Clancy_FINAL_para_grabar.pdf` — guion completo del episodio 2.

## Canal destino

- **Nombre:** Historias de Crímenes
- **Voz principal:** `clone:alejandra`
- **Motor TTS:** Higgs v3
- **Música de fondo:** `arctsound-mysterious-suspense-background-no-copyright-music-252023`
- **Volumen de fondo:** -18 dB
- **Duración objetivo:** 15–20 minutos

## Arquitectura

```
PDF (guion original)
    |
    v
Guion adaptado (~2500-2800 palabras) + tags Higgs
    |
    v
curl POST /api/episodes  -->  FastAPI backend  -->  SQLAlchemy/Episode
    |
    v
Worker (SSE/polling) reclama el job
    |
    v
Higgs TTS  +  música de fondo  +  intro/outro  +  normalización
    |
    v
output/<episode_id>/final.wav
```

## Estructura narrativa del guion adaptado

1. **Hook (1–2 min):** Patrick Clancy como protagonista accidental de las teorías de internet.
2. **Antes de la tragedia:** cómo se conocieron, familia, trabajo, deterioro de Lindsay.
3. **La noche del 24 de enero:** los recados, el email de las 5:24, el Apple Watch, CVS.
4. **Patrick regresa:** la conversación atribuida a Lindsay, la sangre, el basement.
5. **Después de las muertes:** declaración pidiendo perdón para Lindsay.
6. **Costa Rica y Rachel Danis:** fact-check de las fechas y la teoría viral.
7. **Nueva vida, Boston Marathon y Heard Foundation:** gestos públicos y sus lecturas opuestas.
8. **Las teorías más spicy:** veredicto de cada una según evidencia.
9. **Cierre:** la pregunta real del juicio — ¿cuánto fue demostrado y cuánto asumido?

## Tags Higgs permitidos

Usar tags en formato `<|emotion:NOMBRE|>` con las emociones permitidas por el canal:
`contemplation`, `sadness`, `fear`, `helplessness`, `confusion`, `surprise`, `awe`, `longing`, `bitterness`.

Reglas:
- Un tag por párrafo o frase clave.
- No saturar.
- No usar tags de efecto sonoro.
- Mantener los tags en el texto final porque Higgs los interpreta.

## Pasos de implementación

1. **Verificar entorno**
   - API: `GET http://localhost:8000/api/health`
   - Worker: `GET http://localhost:8001/health`
   - Si no responden, lanzar con `python starter.py`.

2. **Preparar el guion adaptado**
   - Extraer texto del PDF.
   - Condensar a ~2500–2800 palabras.
   - Insertar tags Higgs.
   - Validar tags contra `core.emotion_tags.HIGGS_TAGS`.

3. **Crear el episodio vía API**
   - Endpoint: `POST http://localhost:8000/api/episodes`
   - Payload:
     ```json
     {
       "title": "Patrick Clancy: el hombre que internet puso bajo investigación",
       "type": "podcast",
       "source_text": "<guion con tags Higgs>",
       "voice_id": "clone:alejandra",
       "target_duration_minutes": 17,
       "background_music": "arctsound-mysterious-suspense-background-no-copyright-music-252023",
       "bg_music_volume": -18.0
     }
     ```

4. **Monitorear generación**
   - Polling: `GET http://localhost:8000/api/episodes/{episode_id}`
   - Esperar `status: completed` o `failed`.
   - En caso de fallo, revisar `logs/worker.log`.

5. **Verificar audio final**
   - Confirmar existencia: `output/{episode_id}/final.wav`
   - Confirmar duración: `ffprobe -v error -show_entries format=duration ...`
   - Rango esperado: 900–1200 segundos.

## Criterios de éxito

- Episodio creado en la API con `voice_id: clone:alejandra`.
- Estado final `completed`.
- Audio generado con duración entre 15 y 20 minutos.
- Ausencia de tags Higgs inválidos en el guion.

## Notas

- El guion del PDF ya distingue entre hechos, coincidencias y especulación; se conserva esa distinción ética.
- Se evita presentar teorías no probadas como verdades.
- El episodio se genera en español neutro.
