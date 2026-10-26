# -*- coding: utf-8 -*-
"""
The Shield — Observatorio (Fase 2, Paso 2)

Juez inmutable de aislamiento y contrato. Nace RED: la app `app.main` y el
adaptador `app.adapters.db_readonly` se materializan en el Paso 3.

Régimen: [DIRGEN-STRICT] para las fronteras de datos (solo lectura, qbe_core).
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import sys
from pathlib import Path

import pytest

# ── Rutas del ecosistema ────────────────────────────────────────────────────────────────────────
# tests/ -> qbe_observatory/ -> Q_BE_ECOSYSTEM/ -> Q-BE Casino Deportes/
PROJECT_ROOT = Path(__file__).resolve().parents[1]
BASELINE_ROOT = PROJECT_ROOT.parent.parent / "Q_BE_CD_WEB"
HISTORICO = Path(
    os.environ.get("OBS_HISTORICO_DB", str(BASELINE_ROOT / "data" / "qbe_historico.db"))
).resolve()

# La app resuelve su fuente por entorno antes de importarse.
os.environ.setdefault("OBS_HISTORICO_DB", str(HISTORICO))

# Permite `import app.*` cuando pytest se ejecuta desde Q_BE_ECOSYSTEM.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _sha256(path: Path) -> str:
    """Hash de streaming para no cargar 22 MB en memoria de golpe."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_a_aislamiento_de_escritura() -> None:
    """Test A — el adaptador debe impedir INSERT aunque la SQL sea válida."""
    from app.adapters.db_readonly import conexion_solo_lectura

    with conexion_solo_lectura(HISTORICO) as conexion:
        with pytest.raises(sqlite3.OperationalError):
            conexion.execute("INSERT INTO matches (id) VALUES ('test-shield')")


def test_b_inmutabilidad_de_la_bd() -> None:
    """Test B — leer no puede cambiar el SHA-256 del histórico."""
    assert HISTORICO.is_file(), f"No existe el histórico: {HISTORICO}"
    hash_antes = _sha256(HISTORICO)

    from app.adapters.db_readonly import conexion_solo_lectura

    with conexion_solo_lectura(HISTORICO) as conexion:
        total = conexion.execute("SELECT COUNT(*) FROM matches").fetchone()[0]

    hash_despues = _sha256(HISTORICO)
    assert total > 0, "El histórico no devolvió partidos"
    assert hash_despues == hash_antes, "La conexión de solo lectura mutó el histórico"


def test_c_consumo_de_qbe_core() -> None:
    """Test C — el Brier canónico se importa del namespace preservado de qbe_core.

    Este juez ya está VERDE en el estado RED del Observatorio: `qbe_core` se instaló
    en Fase 1 y expone la función. No es un fallo del Paso 2; es la garantía de que
    el núcleo es consumible antes de materializar la app.
    """
    from src.core.contracts.portfolio_math import calcular_brier_multicategorico

    assert callable(calcular_brier_multicategorico)

    partidos = [
        {
            "p_local": 0.50,
            "p_empate": 0.30,
            "p_visitante": 0.20,
            "resultado": "LOCAL",
        },
        {
            "p_local": 0.20,
            "p_empate": 0.30,
            "p_visitante": 0.50,
            "resultado": "VISITANTE",
        },
    ]
    brier = calcular_brier_multicategorico(partidos)
    assert isinstance(brier, float)
    assert 0.0 <= brier <= 1.0


def test_d_contrato_del_endpoint() -> None:
    """Test D — contrato JSON y no-fabricación del Brier de mercado."""
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as cliente:
        respuesta = cliente.get("/api/observatory/calibration-report")

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert "resumen_temporada" in cuerpo
    assert "jornadas" in cuerpo
    assert isinstance(cuerpo["jornadas"], list)

    resumen = cuerpo["resumen_temporada"]
    assert "brier_mercado" in resumen
    assert "alpha_calibracion_pct" in resumen
    assert "mercado_disponible" in resumen

    if resumen["mercado_disponible"] is False:
        # D-1: la ausencia de cuotas se declara con null, jamás con 0.0.
        assert resumen["brier_mercado"] is None
        assert resumen["alpha_calibracion_pct"] is None
    else:
        assert isinstance(resumen["brier_mercado"], (int, float))
        assert isinstance(resumen["alpha_calibracion_pct"], (int, float))
