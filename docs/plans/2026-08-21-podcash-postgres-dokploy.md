# Podcash: migración a PostgreSQL en Dokploy

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrar el backend de Podcash de SQLite a PostgreSQL gestionado por Dokploy, manteniendo la separación backend/frontend y desplegando los servicios en la nube.

**Architecture:** Se añade un servicio Postgres dentro del proyecto `podcash` de Dokploy. El backend (`podcash-api`) actualiza su cadena de conexión `DATABASE_URL` para apuntar a ese servicio. Se modifica `backend/app/database.py` para ser compatible con ambos dialectos (SQLite local y Postgres en producción). Opcionalmente se migra el volumen `/app/data/app.db` existente. El frontend (`podcash-web`) no requiere cambios funcionales, solo asegurar que apunta a la API pública.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, PostgreSQL 18 (Dokploy), Docker, Dokploy API, `psycopg2-binary`.

---

## Contexto actual

- Proyecto Dokploy: `podcash` (`projectId: aDs9rdf499Rg-C085tR8S`).
- Entorno: `production` (`environmentId: qCWpN69-hOSEaujii-sUE`).
- Aplicaciones existentes:
  - `podcash-api` (`applicationId: upqUVo_VoWUtINjk0VvNB`) → `https://api.podcash.app.moonsbow.com`.
  - `podcash-web` (`applicationId: EvKd8T4NRjaCtC7If0ryx`) → `https://podcash.app.moonsbow.com`.
- Volumen persistente montado en `/app/data` con SQLite (`app.db`).
- `backend/app/database.py` usa `connect_args={"check_same_thread": False}` y migraciones con `PRAGMA table_info` (específico de SQLite).
- `backend/requirements.txt` no incluye driver de PostgreSQL.

---

## File Structure

- Modify: `backend/requirements.txt` → añadir `psycopg2-binary>=2.9.0`.
- Modify: `backend/app/database.py` → hacer el engine y `_migrate()` compatibles con SQLite y PostgreSQL.
- Modify: `backend/.env.example` → documentar `DATABASE_URL` para Postgres.
- Modify: Variables de entorno de `podcash-api` en Dokploy vía MCP `application-saveEnvironment`.
- Create: Servicio Postgres en Dokploy vía MCP `postgres-create`.
- Optional: Script de migración de datos SQLite → PostgreSQL.

---

### Task 1: Añadir driver PostgreSQL

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Añadir `psycopg2-binary` a los requisitos**

```text
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
pydantic>=2.6.0
python-multipart>=0.0.9
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
pyyaml>=6.0
requests>=2.31
beautifulsoup4>=4.12
ollama>=0.1.0
crewai>=0.30.0
soundfile>=0.12.1
numpy>=1.26.0
edge-tts>=6.1.0
pytest>=7.4.0
```

- [ ] **Step 2: Commit**

```bash
git add backend/requirements.txt
git commit -m "chore(backend): add psycopg2-binary for PostgreSQL support"
```

---

### Task 2: Hacer `database.py` compatible con SQLite y PostgreSQL

**Files:**
- Modify: `backend/app/database.py`

- [ ] **Step 1: Actualizar imports y engine**

Cambiar la creación del engine para omitir `check_same_thread` cuando no sea SQLite y preparar `connect_args` condicionalmente:

```python
import os
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.app.config import DATABASE_URL

_connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    _connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args,
    echo=False,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
```

- [ ] **Step 2: Actualizar `_migrate()` para soportar ambos dialectos**

```python
def _migrate() -> None:
    """Añade columnas nuevas a tablas existentes (SQLite/Postgres)."""
    new_columns = {
        "channels": [
            ("brief", "TEXT"),
            ("autopilot", "BOOLEAN DEFAULT FALSE NOT NULL"),
            ("episodes_per_week", "INTEGER DEFAULT 2 NOT NULL"),
            ("target_minutes", "INTEGER DEFAULT 10 NOT NULL"),
            ("published_at", "TIMESTAMP"),
        ],
        "content_plan_entries": [
            ("season", "INTEGER DEFAULT 1 NOT NULL"),
        ],
        "episodes": [
            ("published_at", "TIMESTAMP"),
        ],
    }

    if DATABASE_URL.startswith("sqlite"):
        with engine.connect() as conn:
            for table, columns in new_columns.items():
                existing = {row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})")}
                for name, ddl in columns:
                    if name not in existing:
                        conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")
            conn.commit()
    else:
        # Postgres: usar information_schema
        with engine.connect() as conn:
            for table, columns in new_columns.items():
                result = conn.execute(
                    text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_name = :table AND table_schema = 'public'"
                    ),
                    {"table": table},
                )
                existing = {row[0] for row in result}
                for name, ddl in columns:
                    if name not in existing:
                        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
            conn.commit()
```

- [ ] **Step 3: Actualizar `init_db()`**

Mantener la lógica de normalización de ruta solo para SQLite; para Postgres simplemente crear tablas:

```python
def init_db():
    print(f"[init_db] DATABASE_URL={DATABASE_URL}", flush=True)
    if DATABASE_URL.startswith("sqlite:///"):
        db_path = DATABASE_URL[len("sqlite:///") :]
        if not db_path.startswith("/"):
            db_path = str(Path(os.getcwd()) / db_path)
        parent = Path(db_path).parent
        if not parent.exists():
            parent.mkdir(parents=True, exist_ok=True)
        print(
            f"[init_db] db_path={db_path} parent={parent} exists={parent.exists()} "
            f"writable={os.access(parent, os.W_OK) if parent.exists() else 'N/A'} "
            f"user={os.getenv('USER') or os.getenv('USERNAME') or 'unknown'} "
            f"cwd={os.getcwd()}",
            flush=True,
        )
    Base.metadata.create_all(bind=engine)
    _migrate()
    print("[init_db] Database initialized successfully.", flush=True)
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/database.py
git commit -m "feat(backend): make database layer compatible with SQLite and PostgreSQL"
```

---

### Task 3: Actualizar ejemplo de entorno

**Files:**
- Modify: `backend/.env.example`

- [ ] **Step 1: Documentar `DATABASE_URL` para Postgres**

```text
# SQLite (desarrollo local)
# DATABASE_URL=sqlite:///data/app.db

# PostgreSQL (producción en Dokploy)
DATABASE_URL=postgresql://user:password@postgres:5432/podcash

SECRET_KEY=cambia_esto_por_una_clave_secreta_larga
ACCESS_TOKEN_EXPIRE_DAYS=7
ADMIN_USER=admin
ADMIN_PASSWORD=admin
# ADMIN_PASSWORD_HASH=$2b$12$...  # alternativa: hash bcrypt directo
WORKER_TOKEN=cambia_esto_por_un_token_largo_y_seguro
API_PORT=8000
# REQUIRE_AUTH=false  # solo para desarrollo/tests
```

- [ ] **Step 2: Commit**

```bash
git add backend/.env.example
git commit -m "docs(backend): document PostgreSQL DATABASE_URL example"
```

---

### Task 4: Crear servicio PostgreSQL en Dokploy

**Files:**
- (Sin cambios en repo; operación vía MCP `mcp__dokploy__postgres-create`)

- [ ] **Step 1: Crear base de datos PostgreSQL en el entorno `production` del proyecto `podcash`**

Usar MCP:
- `name`: `podcash-postgres`
- `appName`: `podcash-postgres`
- `environmentId`: `qCWpN69-hOSEaujii-sUE`
- `databaseName`: `podcash`
- `databaseUser`: `podcash`
- `databasePassword`: generar contraseña segura de 32 caracteres.
- `serverId`: `6_pG9WVomORS-V_xPZ_iV`
- `description`: `PostgreSQL para podcash-api`

Anotar el `postgresId` devuelto.

- [ ] **Step 2: Obtener datos de conexión interna**

Llamar a `mcp__dokploy__postgres-one` con el `postgresId` para confirmar el host interno (típicamente `podcash-postgres` o similar) y puerto.

---

### Task 5: Actualizar variables de entorno de `podcash-api`

**Files:**
- (Sin cambios en repo; operación vía MCP `mcp__dokploy__application-saveEnvironment`)

- [ ] **Step 1: Leer variables actuales**

Llamar a `mcp__dokploy__application-one` para `upqUVo_VoWUtINjk0VvNB` y anotar `env` actual.

- [ ] **Step 2: Actualizar `DATABASE_URL`**

Reemplazar `DATABASE_URL` por la cadena PostgreSQL interna, p. ej.:

```text
DATABASE_URL=postgresql://podcash:<PASSWORD>@podcash-postgres:5432/podcash
```

Conservar el resto de variables (`SECRET_KEY`, `ADMIN_USER`, `ADMIN_PASSWORD`, `WORKER_TOKEN`, `API_PORT=8000`, `REQUIRE_AUTH=true`, `CORS_ORIGINS=https://podcash.app.moonsbow.com`).

Llamar a `mcp__dokploy__application-saveEnvironment` con:
- `applicationId`: `upqUVo_VoWUtINjk0VvNB`
- `env`: el contenido actualizado.
- `createEnvFile`: `true`.

---

### Task 6: Redesplegar backend

**Files:**
- (Sin cambios en repo; operación vía MCP `mcp__dokploy__application-deploy`)

- [ ] **Step 1: Redeploy de `podcash-api`**

Llamar a `mcp__dokploy__application-deploy` con `applicationId: upqUVo_VoWUtINjk0VvNB`.

- [ ] **Step 2: Verificar logs**

Llamar a `mcp__dokploy__application-readLogs` con `applicationId: upqUVo_VoWUtINjk0VvNB` y buscar `[init_db]` para confirmar conexión a PostgreSQL.

---

### Task 7: (Opcional) Migrar datos SQLite existentes a PostgreSQL

**Files:**
- Create: `tools/migrate_sqlite_to_postgres.py` (script auxiliar)

- [ ] **Step 1: Crear script de migración**

```python
#!/usr/bin/env python3
"""Migración simple SQLite -> PostgreSQL vía SQLAlchemy."""
import os
import sys

# Permitir importar módulos del proyecto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import Session

SQLITE_URL = os.getenv("SOURCE_SQLITE_URL", "sqlite:///data/app.db")
POSTGRES_URL = os.getenv("TARGET_POSTGRES_URL")

if not POSTGRES_URL:
    print("Define TARGET_POSTGRES_URL", file=sys.stderr)
    sys.exit(1)

source = create_engine(SQLITE_URL)
target = create_engine(POSTGRES_URL)

metadata = MetaData()
metadata.reflect(bind=source)
metadata.create_all(bind=target)

with Session(target) as tgt_session:
    with Session(source) as src_session:
        for table in metadata.sorted_tables:
            rows = src_session.execute(table.select()).all()
            if rows:
                tgt_session.execute(table.insert(), [row._asdict() for row in rows])
                print(f"Migradas {len(rows)} filas a {table.name}")
    tgt_session.commit()

print("Migración completada.")
```

- [ ] **Step 2: Ejecutar migración desde local con acceso al volumen**

Para migrar el `app.db` actual del contenedor:

```bash
# Descargar el SQLite del contenedor a local
docker cp podcash-api-rjvyto:/app/data/app.db /tmp/podcash_app.db
SOURCE_SQLITE_URL="sqlite:////tmp/podcash_app.db" \
TARGET_POSTGRES_URL="postgresql://podcash:<PASSWORD>@api.podcash.app.moonsbow.com:5432/podcash" \
python tools/migrate_sqlite_to_postgres.py
```

> Nota: si el puerto de Postgres no está expuesto externamente, ejecutar el script dentro de la red de Dokploy o a través de `docker exec` en el nodo.

- [ ] **Step 3: Commit del script (opcional)**

```bash
git add tools/migrate_sqlite_to_postgres.py
git commit -m "chore(tools): add SQLite to PostgreSQL migration script"
```

---

### Task 8: Verificar salud y dominios

**Files:**
- (Sin cambios en repo)

- [ ] **Step 1: Comprobar health check del backend**

```bash
curl -s https://api.podcash.app.moonsbow.com/api/health | python3 -m json.tool
```

- [ ] **Step 2: Comprobar login y un endpoint protegido**

```bash
TOKEN=$(curl -s -X POST https://api.podcash.app.moonsbow.com/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
curl -s -H "Authorization: Bearer $TOKEN" https://api.podcash.app.moonsbow.com/api/auth/me
```

- [ ] **Step 3: Comprobar frontend**

```bash
curl -s -I https://podcash.app.moonsbow.com
```

---

## Self-Review

- [x] **Spec coverage:** Se crea PostgreSQL, se actualiza el backend para usarlo, se redeploya y se verifica. La migración de datos es opcional.
- [x] **Placeholder scan:** No hay TBDs; todos los pasos incluyen comandos concretos.
- [x] **Type consistency:** `DATABASE_URL` siempre es string; `init_db()` mantiene firma; `_migrate()` no recibe argumentos.

---

## Execution Handoff

**Plan complete and saved to `docs/plans/2026-08-21-podcash-postgres-dokploy.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
