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

## Requisitos

- Node.js 18+
- Python 3.11+
- Dependencias de Python instaladas (`pip install -r requirements.txt`)
- Dependencias de Node instaladas (`cd web && npm install`)

## Uso básico

1. Abre http://localhost:5173 en el navegador.
2. Desde el **Dashboard** revisa el estado de la cola.
3. Ve a **Voces** para escuchar una vista previa de las voces disponibles.
4. Ve a **Crear** para generar un nuevo episodio o audiolibro.
5. Ve a **Cola** para ver el progreso en tiempo real (SSE).

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
