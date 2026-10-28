# -*- coding: utf-8 -*-
"""The Shield — UI, snapshot y Manus (Slice 2B)."""

from __future__ import annotations

import hashlib
import os
import sqlite3
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ECOSYSTEM_ROOT = PROJECT_ROOT.parent

# Snapshot interno canónico (idéntico lógicamente al baseline congelado).
SNAPSHOT = PROJECT_ROOT / "data" / "observatory_snapshot.db"


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _preparar_snapshot(tmp_path: Path) -> Path:
    base = tmp_path / "observatory_snapshot.db"
    origen = sqlite3.connect(f"file:{SNAPSHOT.resolve().as_posix()}?mode=ro", uri=True)
    copia = sqlite3.connect(base.as_posix())
    try:
        origen.backup(copia)
    finally:
        copia.close()
        origen.close()

    from app import config

    config.BACKTESTING_SNAPSHOT = base.resolve()
    return base


def test_ui_backtesting_200_sin_assets_de_la_mesa(tmp_path: Path) -> None:
    _preparar_snapshot(tmp_path)

    from fastapi.testclient import TestClient
    from app.main import app

    respuesta = TestClient(app).get("/backtesting")

    assert respuesta.status_code == 200
    assert "Backtesting" in respuesta.text
    assert "app.js" not in respuesta.text
    assert "features.js" not in respuesta.text


def test_ui_simulacion_renderiza_curva(tmp_path: Path) -> None:
    _preparar_snapshot(tmp_path)

    from fastapi.testclient import TestClient
    from app.main import app

    respuesta = TestClient(app).post(
        "/backtesting/simulate",
        data={
            "bankroll_inicial": "1000",
            "rango_jornadas": "1-2",
            "modo_interes": "plano",
            "gamma_slider": "0.67",
            "target_certeza_pct": "0",
            "modo_cobertura": "DEF",
        },
    )

    assert respuesta.status_code == 200, respuesta.text[:500]
    assert "Resultado" in respuesta.text
    assert "Curva de capital" in respuesta.text


def test_snapshot_status_y_frescura(tmp_path: Path) -> None:
    base = _preparar_snapshot(tmp_path)

    from fastapi.testclient import TestClient
    from app.main import app

    respuesta = TestClient(app).get("/api/observatory/snapshot/status")
    assert respuesta.status_code == 200
    assert respuesta.json()["fresco"] is True

    antiguo = time.time() - 7200
    os.utime(base, (antiguo, antiguo))
    respuesta = TestClient(app).get("/api/observatory/snapshot/status")
    assert respuesta.json()["fresco"] is False


def test_refresco_atomico_no_muta_origen(tmp_path: Path) -> None:
    from app.services.snapshot_refresh import refrescar_snapshot, snapshot_fresco

    origen = tmp_path / "live.db"
    con = sqlite3.connect(origen)
    con.execute("CREATE TABLE muestra (id INTEGER PRIMARY KEY, valor TEXT)")
    con.execute("INSERT INTO muestra (valor) VALUES ('capturado')")
    con.commit()
    con.close()

    hash_antes = _hash(origen)
    destino = tmp_path / "observatory_snapshot.db"
    resultado = refrescar_snapshot(
        origen, destino, max_age_minutes=60, exigir_contrato=False
    )

    assert destino.is_file()
    assert snapshot_fresco(destino, 60) is True
    assert resultado["fresco"] is True
    assert _hash(origen) == hash_antes

    con = sqlite3.connect(destino)
    try:
        assert con.execute("SELECT valor FROM muestra").fetchone()[0] == "capturado"
    finally:
        con.close()


def test_manus_lista_y_503_sin_artefacto(tmp_path: Path, monkeypatch) -> None:
    from app.services import manus

    monkeypatch.setattr(manus, "MODELOS_DIR", tmp_path / "modelos")
    _preparar_snapshot(tmp_path)

    from fastapi.testclient import TestClient
    from app.main import app

    cliente = TestClient(app)
    listado = cliente.get("/api/observatory/manus/models")
    assert listado.status_code == 200
    assert len(listado.json()["modelos"]) == 3

    prediccion = cliente.post(
        "/api/observatory/manus/task_a/predict",
        json={"features": {"x": 1.0}},
    )
    assert prediccion.status_code == 503

    desconocida = cliente.post(
        "/api/observatory/manus/task_z/predict",
        json={"features": {}},
    )
    assert desconocida.status_code == 404


def test_manus_predice_con_sklearn(tmp_path: Path, monkeypatch) -> None:
    import joblib
    import pandas as pd
    from sklearn.linear_model import LinearRegression

    from app.services import manus

    modelos = tmp_path / "modelos"
    modelos.mkdir()
    x = pd.DataFrame({"x": [1.0, 2.0, 3.0]})
    y = [2.0, 4.0, 6.0]
    modelo = LinearRegression().fit(x, y)
    joblib.dump(modelo, modelos / "task_a.joblib")
    monkeypatch.setattr(manus, "MODELOS_DIR", modelos)

    from fastapi.testclient import TestClient
    from app.main import app

    respuesta = TestClient(app).post(
        "/api/observatory/manus/task_a/predict",
        json={"features": {"x": 4.0}},
    )

    assert respuesta.status_code == 200, respuesta.text
    assert abs(respuesta.json()["predicciones"][0] - 8.0) < 1e-6

def test_puerto_propio_8001() -> None:
    from app import config

    assert config.OBS_PORT == 8001
    assert config.OBS_HOST == "127.0.0.1"
