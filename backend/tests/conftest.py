"""Aísla los tests de la BD y directorios reales.

Sin esto, los tests escriben canales/episodios en data/app.db (la BD de
producción). Debe cargarse antes que cualquier import de backend.app.
"""

import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="podcast_tests_")
_OUTPUT = os.path.join(_TMP, "output")

os.makedirs(os.path.join(_OUTPUT, "previews"), exist_ok=True)

os.environ.setdefault("DATABASE_URL", f"sqlite:///{_TMP}/test.db")
os.environ.setdefault("DATA_DIR", _TMP)
os.environ.setdefault("OUTPUT_DIR", _OUTPUT)
os.environ.setdefault("REQUIRE_AUTH", "false")
os.environ.setdefault("WORKER_TOKEN", "test-worker-token")
