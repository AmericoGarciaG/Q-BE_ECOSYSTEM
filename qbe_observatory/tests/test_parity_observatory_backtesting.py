# -*- coding: utf-8 -*-
"""The Shield — paridad de backtesting del Observatorio (Slice 2A)."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ECOSYSTEM_ROOT = PROJECT_ROOT.parent

# Baseline CONGELADO de paridad: el Golden Master se ancla a esta copia, no al
# snapshot operativo. El snapshot de `qbe_observatory/data/` se refresca desde la
# bóveda viva y por diseño cambia con cada jornada; usarlo aquí acoplaría un juez
# de regresión del builder al calendario de la ingesta.
SNAPSHOT = ECOSYSTEM_ROOT / "data" / "snapshots" / "qbe_database_snapshot.db"
GOLDEN = Path(__file__).with_name("golden_master_backtesting.json")


def _preparar(tmp_path: Path) -> None:
    base = tmp_path / "qbe_backtesting.db"
    origen = sqlite3.connect(f"file:{SNAPSHOT.resolve().as_posix()}?mode=ro", uri=True)
    copia = sqlite3.connect(base.as_posix())
    try:
        origen.backup(copia)
    finally:
        copia.close()
        origen.close()

    url = f"sqlite:///{base.as_posix()}"
    os.environ["DATABASE_URL"] = url
    os.environ["QBE_HISTORICO_DB"] = str(
        PROJECT_ROOT / "data" / "qbe_historico.db"
    )
    os.environ["OBS_BACKTESTING_SNAPSHOT"] = str(base.resolve())

    from app import config as obs_config

    obs_config.BACKTESTING_SNAPSHOT = base.resolve()

    from src.config import settings

    settings.DATABASE_URL = url

    from src.storage.gateway import PersistenceGateway

    if PersistenceGateway._instance is not None:
        try:
            PersistenceGateway._instance.engine.dispose()
        except Exception:
            pass
        PersistenceGateway._instance = None


def test_paridad_calibracion_backtesting(tmp_path: Path) -> None:
    assert GOLDEN.is_file(), f"No existe el Golden Master: {GOLDEN}"
    _preparar(tmp_path)

    from fastapi.testclient import TestClient
    from app.main import app

    respuesta = TestClient(app).get(
        "/api/observatory/backtesting/calibration-report",
        params={"league_id": 1},
    )

    assert respuesta.status_code == 200, respuesta.text[:500]
    esperado = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert respuesta.json() == esperado, "La calibración difiere del monolito congelado"


def test_simulacion_backtesting_responde(tmp_path: Path) -> None:
    _preparar(tmp_path)

    from fastapi.testclient import TestClient
    from app.main import app

    respuesta = TestClient(app).post(
        "/api/observatory/backtesting/simulate",
        json={
            "bankroll_inicial": 1000.0,
            "rango_jornadas": "1-2",
            "modo_interes": "plano",
        },
    )

    assert respuesta.status_code == 200, respuesta.text[:500]
    cuerpo = respuesta.json()
    assert cuerpo["status"] == "EXITO"
    assert cuerpo["bankroll_inicial"] == 1000.0
    assert "jornadas_solicitadas" in cuerpo

def test_dependencias_analiticas_son_solo_del_observatorio() -> None:
    """pandas/sklearn viven en el Observatorio, no en core ni business."""
    import tomllib

    def deps(ruta: Path) -> str:
        datos = tomllib.loads(ruta.read_text(encoding="utf-8"))
        return " ".join(datos["project"].get("dependencies", [])).lower()

    observatorio = deps(PROJECT_ROOT / "pyproject.toml")
    core = deps(ECOSYSTEM_ROOT / "qbe_core" / "pyproject.toml")
    business = deps(ECOSYSTEM_ROOT / "qbe_business" / "pyproject.toml")

    assert "pandas" in observatorio
    assert "scikit-learn" in observatorio
    assert "pandas" not in core and "scikit-learn" not in core
    assert "pandas" not in business and "scikit-learn" not in business
