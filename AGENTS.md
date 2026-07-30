# Scripts de arranque

El proyecto se levanta con `starter.py`, que arranca los tres servicios de la pila web y abre un monitor en vivo. Existen además lanzadores por plataforma que delegan en él.

## Pila de servicios

`starter.py` arranca en orden y con health-check entre cada uno:

| Servicio  | Origen                | Puerto default | Health check                         |
|-----------|-----------------------|----------------|--------------------------------------|
| API       | `python -m web_api.main`   | 8000           | `GET http://127.0.0.1:8000/api/health` |
| Worker    | `python -m worker.main`    | 8001           | `GET http://127.0.0.1:8001/health`     |
| Web (Vite)| `npm run dev` (en `web/`)  | 5173           | `http://127.0.0.1:5173`                |

Los tres procesos se lanzan en segundo plano, su salida se redirige a `logs/{api,worker,web}.log` **y** se reemite a la consola con el prefijo `[api]`/`[worker]`/`[web]`. Al finalizar, `starter.py`:

1. Abre una ventana de terminal nueva con el **monitor curses** (`starter_monitor.py`), si detecta un emulador (`gnome-terminal`, `konsole`, `xfce4-terminal`, `alacritty`, `wezterm`, `kitty`, `xterm`).
2. Abre el navegador en `http://127.0.0.1:5173`.

## Cómo ejecutar

### lanzadores por plataforma

Estos scripts simplemente delegan en `starter.py` (todos hacen `cd` al directorio del repo primero):

- **Linux/macOS**: `./starter.sh`
- **Windows**: `starter.bat` ( doble clic o `starter.bat` en cmd)

### Directamente

```bash
python starter.py
```

También desde el entorno virtual:

```bash
source venv311/bin/activate
python starter.py
```

### Variables de entorno

Todos los puertos son configurables. `starter.py` y `web/vite.config.ts` leen las mismas variables, así que el proxy del frontend siempre apunta a la API correcta:

```bash
API_PORT=9000 WORKER_PORT=9001 WEB_PORT=5174 python starter.py
```

| Variable      | Default | Descripción                              |
|---------------|---------|------------------------------------------|
| `API_PORT`    | 8000    | FastAPI (`web_api/main.py`)              |
| `WORKER_PORT` | 8001    | Worker de generación (`worker/main.py`)  |
| `WEB_PORT`     | 5173    | Vite dev server                          |

## Monitor curses (`starter_monitor.py`)

Dashboard en vivo (ventana de terminal independiente). Muestra:

- URL, puerto y estado de salud de cada servicio.
- Logs de `api`, `worker` y `web` en paneles separados, actualizados en tiempo real.
- Contador de errores resaltados en rojo.

Salir con `q` (modo curses) o `Ctrl+C` (modo consola simple si curses no está disponible). **Cerrar el monitor no detiene los servicios**: para pararlos usa `Ctrl+C` en la terminal donde corre `starter.py`.

Si no se encuentra ningún emulador de terminal, el monitor no se abre pero los logs siguen estando en `./logs/`.

## Detener todo

`starter.py` captura `SIGINT` y `SIGTERM` y apaga limpiamente los tres procesos (termina y, si no ceden en 2 s, los matar). **Nunca uses `kill -9`** salvo emergencia.

## Depencencias previas

Antes de ejecutar `starter.py` por primera vez:

```bash
# Python
python3.11 -m venv venv311
source venv311/bin/activate   # Windows: venv311\Scripts\activate
pip install -r requirements.txt

# Node (frontend)
cd web && npm install
```

Opcional pero recomendado para features de CrewAI: tener [Ollama](https://ollama.ai) corriendo con el modelo por defecto (`web_api/config.py`, `OLLAMA_DEFAULT_MODEL`). `starter.py` comprueba su disponibilidad al arrancar y avisa (sin abortar) si falta.

## Sólo la app de escritorio

`starter.py` es **solo para la versión web**. La app de escritorio PyQt6 se lanza aparte con:

```bash
python main.py
```

## Motor Qwen3-TTS (voz clonada)

El proyecto integra **Qwen/Qwen3-TTS-12Hz-1.7B-Base** como motor alternativo de clonación de voz, junto al Higgs v3 existente.

| Motor   | Paquete       | Modelo default                         | VRAM     |
|---------|---------------|----------------------------------------|----------|
| Higgs   | vLLM-Omni     | `bosonai/higgs-audio-v3-tts-4b`        | ~18 GB   |
| Qwen3   | `qwen-tts`    | `Qwen/Qwen3-TTS-12Hz-1.7B-Base`        | ~4 GB    |

### Instalación

```bash
pip install -r requirements.txt   # incluye qwen-tts
```

Opcional (recomendado): `pip install flash-attn --no-build-isolation`.

### Configuración

| Variable              | Default                                            |
|-----------------------|----------------------------------------------------|
| `QWEN3_TTS_MODEL`     | `Qwen/Qwen3-TTS-12Hz-1.7B-Base`                    |
| `QWEN3_TTS_DEVICE`    | `cuda`                                             |
| `QWEN3_TTS_DTYPE`     | *(vacío → bfloat16)*                               |

### Uso en la web

Las voces clonadas en `voices/clones/` se muestran **dos veces** en el dropdown de la interfaz: una con motor Higgs (retrocompatible) y otra con motor Qwen3 (`nombre (qwen3)`). El despacho se hace en `web_api/routes/tts.py` mediante `_get_clone_engine(voice)`.

### Documentación detallada

Ver `docs/QWEN3_TTS_SETUP.md`.

| Archivo              | Qué hace                                                                      |
|----------------------|-------------------------------------------------------------------------------|
| `starter.py`         | Orquestador principal: lanza api+worker+web, monitor y navegador, apagado limpio. |
| `starter_monitor.py` | Dashboard curses en vivo (ventana independiente).                            |
| `starter.sh`         | Wrapper bash: `cd` + `python starter.py`.                                     |
| `starter.bat`        | Wrapper cmd para Windows.                                                     |
| `logs/`              | Carpeta donde se guardan los logs de cada servicio al arrancar.              |