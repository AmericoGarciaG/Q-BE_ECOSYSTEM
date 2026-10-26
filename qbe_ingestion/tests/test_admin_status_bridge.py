"""The Shield — puente REST Business → Ingesta (Slice 4B)."""

from __future__ import annotations

import os
import socket
import sqlite3
import threading
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ECOSYSTEM_ROOT = PROJECT_ROOT.parent
SNAPSHOT = (
    ECOSYSTEM_ROOT.parent
    / "Q_BE_CD_WEB"
    / "data"
    / "output"
    / "backups"
    / "qbe_database.baseline.db"
)


def _preparar_db(tmp_path: Path) -> None:
    base = tmp_path / "qbe_bridge.db"
    origen = sqlite3.connect(f"file:{SNAPSHOT.resolve().as_posix()}?mode=ro", uri=True)
    copia = sqlite3.connect(base.as_posix())
    try:
        origen.backup(copia)
    finally:
        copia.close()
        origen.close()

    url = f"sqlite:///{base.as_posix()}"
    os.environ["DATABASE_URL"] = url
    os.environ["QBE_FEATURE_ADMIN"] = "true"

    from src.config import settings

    settings.DATABASE_URL = url

    from src.storage.gateway import PersistenceGateway

    if PersistenceGateway._instance is not None:
        try:
            PersistenceGateway._instance.engine.dispose()
        except Exception:
            pass
        PersistenceGateway._instance = None


def test_admin_status_offline_503(tmp_path: Path) -> None:
    _preparar_db(tmp_path)
    os.environ["QBE_INGESTION_URL"] = "http://127.0.0.1:65530"

    from fastapi.testclient import TestClient
    from src.web.app import app

    respuesta = TestClient(app).get("/api/admin/status/drift")
    assert respuesta.status_code == 503
    assert "Ingesta" in respuesta.json()["detail"]


def test_admin_status_online_200(tmp_path: Path) -> None:
    _preparar_db(tmp_path)

    sonda = socket.socket()
    sonda.bind(("127.0.0.1", 0))
    puerto = sonda.getsockname()[1]
    sonda.close()

    os.environ["QBE_INGESTION_URL"] = f"http://127.0.0.1:{puerto}"

    import uvicorn
    from src.ingestion.service import app as ingestion_app

    servidor = uvicorn.Server(
        uvicorn.Config(
            ingestion_app,
            host="127.0.0.1",
            port=puerto,
            log_level="error",
            lifespan="off",
        )
    )
    hilo = threading.Thread(target=servidor.run, daemon=True)
    hilo.start()
    try:
        for _ in range(100):
            if servidor.started:
                break
            time.sleep(0.05)
        assert servidor.started, "El servicio de Ingesta no arrancó"

        from fastapi.testclient import TestClient
        from src.web.app import app

        respuesta = TestClient(app).get("/api/admin/status/drift")
        assert respuesta.status_code == 200, respuesta.text[:300]
        assert respuesta.json()["status"] == "OK"
        assert respuesta.json()["fuente"] == "qbe_ingestion"
    finally:
        servidor.should_exit = True
        hilo.join(timeout=5)
