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

Al arrancar, `starter.py` intenta abrir una **ventana de monitor** con un dashboard en vivo que muestra:

- URL y estado de cada servicio (health check).
- Logs de `api`, `worker` y `web` en paneles separados.
- Contador de errores resaltados en rojo.

Si no detecta un emulador de terminal compatible, los logs se guardan en `./logs/` (`api.log`, `worker.log`, `web.log`) y también se muestran en la consola.

Puedes cerrar el monitor con `q` (o `Ctrl+C` en modo consola) sin detener los servicios.

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

## Canales y CrewAI ("congreso de agentes")

1. Crea un canal en **Canales**.
2. Ve a **Studio**, selecciona el canal y pulsa **Generar plan**.
   El Studio muestra arriba el estado de Ollama (verde si está listo).
3. Revisa las entradas generadas en el plan editorial del canal.
4. Pulsa **Aprobar** en una entrada para generar el guion con CrewAI y crear el episodio.
5. Sigue la generación de audio en **Cola**.

Cómo trabaja el congreso (`web_api/services/crew_service.py`):

- **Plan editorial** (2 agentes): el *Content Strategist* propone 8 ideas en bruto
  y el *Chief Editor* las debate, descarta las flojas y devuelve las 5 mejores.
- **Guion** (3 agentes): el *Script Writer* escribe, el *Script Editor* pule ritmo
  y claridad, y el *Voice Director* deja el texto limpio para TTS (sin notas de
  producción ni markdown — además hay una limpieza regex de seguridad).

Tiempos orientativos con `llama3.1:8b` caliente en GPU: plan ≈ 50 s, guion ≈ 30 s.
Si el modelo está frío o en CPU (falta de VRAM), puede tardar varios minutos.

### Requisitos de Ollama

Asegúrate de que Ollama esté corriendo y tenga el modelo configurado:

```bash
ollama pull llama3.1:8b
ollama serve
```

La URL y el modelo se configuran en `config.yaml` bajo la sección `llm`
(también `OLLAMA_PLANNING_MODEL` y `OLLAMA_SCRIPT_MODEL` por separado).

**Nota VRAM (GPUs de ~8 GB)**: Ollama (≈5.6 GB) y el motor Higgs TTS (≈7 GB)
no caben a la vez. Al cargarse, Higgs descarga automáticamente los modelos de
Ollama de la GPU (`keep_alive=0`); Ollama los recarga en la siguiente llamada
del congreso (caída a CPU si la GPU está ocupada = mucho más lento).

## Troubleshooting

- **Puertos ocupados**: cambia `API_PORT`, `WORKER_PORT` y/o `WEB_PORT`.
- **`starter.py` dice que un servicio no inició**: revisa el log etiquetado (`[api]`, `[worker]` o `[web]`) o los archivos en `./logs/` para ver el error real.
- **El frontend no puede hablar con la API**: asegúrate de que `API_PORT` sea el mismo para `starter.py` y para la shell donde corres `npm run dev`.
- **No se abre la ventana del monitor**: instala un emulador de terminal (`gnome-terminal`, `konsole`, `xfce4-terminal`, `alacritty`, `kitty` o `xterm`). Sin uno, los logs siguen disponibles en `./logs/`.

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
