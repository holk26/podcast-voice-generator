# 🎙️ Podcast Voice Generator

Aplicación web para generar podcasts con voz sintética de alta calidad usando GPU NVIDIA. Soporta múltiples motores TTS, clonación de voz y procesamiento de audio profesional.

La arquitectura está dividida en tres partes:

- **Backend** (`backend/`): API REST + SSE en FastAPI.
- **Frontend** (`frontend/`): Interfaz web en Vite.
- **Worker** (`worker/`): Proceso local que renderiza audio y reporta resultados al backend.

> La versión de escritorio PyQt6 fue eliminada. Todo se controla desde el navegador.

## ✨ Características

- **🌐 Interfaz Web**: Trabaja desde cualquier lugar; el backend puede ir a un servidor y el worker a tu PC.
- **🔊 Múltiples Motores TTS**:
  - **XTTS v2** (Coqui) - Clonación de voz con audio de referencia
  - **Bark** (Suno) - Voz expresiva y natural
  - **Edge-TTS** - Síntesis rápida en la nube
  - **Qwen3-TTS** - Clonación de voz ligera (~4 GB VRAM)
- **🎭 Clonación de Voz**: Clona voces a partir de archivos de referencia
- **⚡ Aceleración GPU**: Soporte NVIDIA CUDA con gestión de VRAM
- **🎚️ Procesamiento de Audio**: Mezcla, normalización, efectos y exportación profesional
- **🤖 Autopiloto de Canales**: Generación automática de temporadas, planes y guiones
- **🌍 Multi-idioma**: Soporte para varios idiomas

## 🚀 Instalación

### Requisitos

- Python 3.11+
- NVIDIA GPU con CUDA (opcional pero recomendado)
- 8GB+ RAM (16GB recomendado)
- ~5GB espacio libre para modelos
- Node.js 18+ (para el frontend)

### Paso 1: Clonar el repositorio

```bash
git clone <repo-url>
cd podcast-voice-generator
```

### Paso 2: Crear entorno virtual de Python

```bash
python3.11 -m venv venv311
source venv311/bin/activate  # Linux/Mac
# venv311\Scripts\activate  # Windows
```

### Paso 3: Instalar dependencias de Python

```bash
pip install -r requirements.txt
```

> **Nota para RTX 50-series**: PyTorch < 2.11 no es compatible con sm_120 (Blackwell). La app usa CPU fallback si detecta una GPU no soportada. Para GPU instala PyTorch 2.11+ con CUDA 13.0.

### Paso 4: Instalar dependencias del frontend

```bash
cd frontend && npm install && cd ..
```

### Paso 5: Configurar variables de entorno

```bash
cp backend/.env.example backend/.env
cp worker/.env.example worker/.env
cp frontend/.env.example frontend/.env
```

Edita al menos:

- `backend/.env`: `SECRET_KEY`, `ADMIN_PASSWORD`, `WORKER_TOKEN`
- `worker/.env`: `BACKEND_URL`, `WORKER_TOKEN` (mismo valor)
- `frontend/.env`: `VITE_API_URL` (URL pública del backend)

### Paso 6: Ejecutar en desarrollo

```bash
python starter.py
```

Esto levanta backend (`:8000`), worker (`:8001`) y frontend (`:5173`), y abre el navegador.

## 🏗️ Arquitectura

```
podcast-voice-generator/
├── backend/                 # API FastAPI
│   ├── app/
│   │   ├── main.py          # Punto de entrada FastAPI
│   │   ├── auth.py          # JWT y hashing
│   │   ├── dependencies.py  # Auth dependencies
│   │   ├── routes/          # Routers (auth, worker, episodes, channels...)
│   │   └── services/        # Lógica de negocio
│   ├── tests/               # Tests del backend
│   └── .env.example
├── frontend/                # Aplicación web Vite
│   ├── src/
│   ├── package.json
│   └── .env.example
├── worker/                  # Proceso local de renderizado
│   ├── main.py              # Health check HTTP + bucle
│   ├── runner.py            # Bucle SSE/polling
│   ├── client.py            # Cliente HTTP hacia backend
│   ├── handlers.py          # Renderizado de audio
│   ├── tests/
│   └── .env.example
├── shared/                  # Contratos y config compartidos
│   ├── schemas/__init__.py  # Schemas Pydantic
│   └── config.py
├── core/                    # Motores TTS y pipelines
├── audio/                   # Procesamiento de audio
├── models/                  # Modelos descargados
├── voices/                  # Voces y clones
└── output/                  # Audio generado
```

## 🌍 Deploy en producción

### Servidor (backend + frontend)

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r ../requirements.txt
cp .env.example .env
# Edita SECRET_KEY, ADMIN_PASSWORD, WORKER_TOKEN, DATABASE_URL...
python -m app.main
```

Frontend:

```bash
cd frontend
npm install
npm run build
# Sirve dist/ con nginx/caddy
```

Configura `CORS_ORIGINS` en el backend con el dominio del frontend.

### PC local (worker)

```bash
export BACKEND_URL=https://tu-dominio.com
export WORKER_TOKEN=<mismo_token_que_backend>
cd worker
python -m main
```

El worker se conecta por SSE y, si falla, hace polling cada 30 segundos.

## 🔐 Seguridad

- Las rutas de la API web requieren JWT (`Authorization: Bearer <token>`).
- Las rutas del worker requieren el token estático `WORKER_TOKEN`.
- `REQUIRE_AUTH=false` deshabilita JWT solo para desarrollo/tests.
- Nunca subas `.env` con secretos reales.

## 🧪 Tests

```bash
python -m pytest backend/tests worker/tests -v --tb=short
```

## 🖥️ Compatibilidad de GPU

| GPU | Arquitectura | CUDA | PyTorch Recomendado | Estado |
|-----|-------------|------|-------------------|--------|
| RTX 3060-4090 | Ampere/Ada | sm_86/sm_89 | 2.6.0+cu124 | ✅ GPU |
| RTX 5060-5090 | Blackwell | sm_120 | 2.11.0+cu130 | ✅ GPU |
| GTX 1060-1080 | Pascal | sm_61 | 2.6.0+cu124 | ✅ GPU |
| Sin GPU | - | - | Cualquiera | ✅ CPU |

## 📝 Licencia

MIT License - ver archivo LICENSE para detalles.

Los modelos XTTS v2, Bark y Qwen3-TTS tienen sus propias licencias.
