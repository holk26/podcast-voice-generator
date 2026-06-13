# Interfaz Web

La interfaz web permite usar el Podcast Voice Generator desde el navegador para generar podcasts, audiolibros y probar voces.

## Levantar los servicios

```bash
python starter.py
```

Esto inicia tres servicios:

- **Frontend** en http://localhost:5173
- **API** en http://localhost:8000
- **Worker** en http://localhost:8001

Para usar puertos diferentes:

```bash
API_PORT=9000 WORKER_PORT=9001 WEB_PORT=5174 python starter.py
```

`starter.py` y `web/vite.config.ts` leen las mismas variables, así que el proxy del frontend apunta automáticamente a la API correcta.

## Requisitos

- Node.js 18+
- Python 3.11+
- Dependencias de Python instaladas (`pip install -r requirements.txt`)
- Dependencias de Node instaladas (`cd web && npm install`)

## Uso básico

1. Abre http://localhost:5173 en el navegador (`starter.py` lo abre automáticamente).
2. Desde el **Dashboard** revisa el estado de la cola.
3. Ve a **Voces** para escuchar una vista previa de las voces disponibles.
4. Ve a **Crear** para generar un nuevo episodio o audiolibro.
5. Ve a **Cola** para ver el progreso en tiempo real (SSE).

## Canales y CrewAI

1. Crea un canal en **Canales**.
2. Ve a **Studio**, selecciona el canal y pulsa **Generar plan**.
3. Revisa las entradas generadas en el plan editorial del canal.
4. Pulsa **Aprobar** en una entrada para generar el guion con CrewAI y crear el episodio.
5. Sigue la generación de audio en **Cola**.

### Requisitos de Ollama

Asegúrate de que Ollama esté corriendo y tenga el modelo configurado:

```bash
ollama pull llama3.1:8b
ollama serve
```

La URL y el modelo se configuran en `config.yaml` bajo la sección `llm`.

## Troubleshooting

- **Puertos ocupados**: cambia `API_PORT`, `WORKER_PORT` y/o `WEB_PORT`.
- **`starter.py` dice que un servicio no inició**: revisa el log etiquetado (`[api]`, `[worker]` o `[web]`) para ver el error real.
- **El frontend no puede hablar con la API**: asegúrate de que `API_PORT` sea el mismo para `starter.py` y para la shell donde corres `npm run dev`.

## Tests frontend

```bash
cd web
npm test -- --run
npm run build
```

## Arquitectura

```
web/          # React + Vite + Tailwind + TanStack Router + Zustand
web_api/      # FastAPI + SQLAlchemy + SQLite
worker/       # Proceso Python con Edge-TTS
starter.py    # Lanza los tres servicios
```
