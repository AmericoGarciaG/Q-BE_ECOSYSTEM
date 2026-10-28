# -*- coding: utf-8 -*-
"""The Shield — Ciclo de vida del Observatorio.

Juez inmutable del sprint `SPRINT-OBSERVATORY-SNAPSHOT-AND-ARCH-ALIGNMENT`.
Certifica las tres invarianzas que la promesa de Fase 2 exige y que hasta este
sprint no tenían juez:

* **I1 — Snapshot físico:** existe, no está vacío, abre en `mode=ro`, supera
  `PRAGMA quick_check`, porta partidos y rechaza escrituras. Su hash no cambia
  por leerlo.
* **I2 — Arranque ASGI:** `app.main:app` se instancia y responde `/health` y `/`
  sin `RuntimeError` por snapshot ausente.
* **I3 — Resolución de calibración:** el endpoint canónico y su alias deprecado
  devuelven `200` con datos consistentes y coincidentes (una sola verdad).

Régimen `[DIRGEN-STRICT]`: nace RED cuando el snapshot no existe (I1 e I3 rojos)
y sólo pasa a verde cuando el ciclo de vida completo está materializado.
"""

from __future__ import annotations

import hashlib
import sqlite3
import sys
from pathlib import Path

import pytest

# tests/ -> qbe_observatory/ -> Q_BE_ECOSYSTEM/ -> Q-BE Casino Deportes/
PROJECT_ROOT = Path(__file__).resolve().parents[1]
ECOSYSTEM_ROOT = PROJECT_ROOT.parent

# Ruta canónica resuelta por `app/config.py` (nunca desde el CWD).
SNAPSHOT_CANONICO = PROJECT_ROOT / "data" / "observatory_snapshot.db"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(autouse=True)
def _aislar_configuracion_del_snapshot():
    """Fija y restaura `config.BACKTESTING_SNAPSHOT`.

    Otros jueces (`test_slice2b.py`, `test_parity_observatory_backtesting.py`)
    mutan estado global; sin este cinturón el resultado de este archivo dependería
    del orden de ejecución de pytest.

    El antiguo parche de pragmas globales fue extirpado: el Gateway
    (`qbe_storage.gateway`, [ARCH-1.5.1]) registra su listener de conexión en la
    instancia `self.engine`, nunca en la clase global `Engine`, por lo que ya no
    puede envenenar conexiones `mode=ro` ajenas. Manipular eventos globales desde
    un juez de integración era deuda técnica, no aislamiento.
    """
    from app import config

    original = config.BACKTESTING_SNAPSHOT
    config.BACKTESTING_SNAPSHOT = SNAPSHOT_CANONICO
    try:
        yield
    finally:
        config.BACKTESTING_SNAPSHOT = original


def _sha256(ruta: Path) -> str:
    digest = hashlib.sha256()
    with ruta.open("rb") as manejador:
        for bloque in iter(lambda: manejador.read(1024 * 1024), b""):
            digest.update(bloque)
    return digest.hexdigest()


def _conexion_ro(ruta: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{ruta.as_posix()}?mode=ro", uri=True, timeout=5.0)


# ── I1 — Presencia e inmutabilidad del snapshot ────────────────────────────────────────────────
def test_i1_snapshot_presente_verificado_e_inmutable() -> None:
    """El snapshot existe, es íntegro, porta partidos y no admite escritura."""
    assert SNAPSHOT_CANONICO.is_file(), (
        f"snapshot ausente: {SNAPSHOT_CANONICO}. "
        "Materialícelo con `python -m scripts.refresh_snapshot`."
    )
    assert SNAPSHOT_CANONICO.stat().st_size > 0, "snapshot vacío"

    huella_antes = _sha256(SNAPSHOT_CANONICO)

    conexion = _conexion_ro(SNAPSHOT_CANONICO)
    try:
        chequeo = conexion.execute("PRAGMA quick_check").fetchone()
        assert str(chequeo[0]).strip().lower() == "ok", f"quick_check={chequeo}"

        total = conexion.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
        assert int(total) > 0, "el snapshot no porta partidos"

        # Frontera CQRS: la conexión de solo lectura rechaza DDL/DML.
        with pytest.raises(sqlite3.OperationalError):
            conexion.execute("CREATE TABLE _shiel_probe (x INTEGER)")
        with pytest.raises(sqlite3.OperationalError):
            conexion.execute("DELETE FROM matches")
    finally:
        conexion.close()

    assert _sha256(SNAPSHOT_CANONICO) == huella_antes, (
        "el hash del snapshot cambió por efecto de la lectura"
    )


# ── I2 — Arranque ASGI ────────────────────────────────────────────────────────────────────────
def test_i2_arranque_asgi_salud_y_portada() -> None:
    """`app.main:app` se instancia y responde sin depender del snapshot."""
    from fastapi.testclient import TestClient

    from app.main import app

    assert app.title == "Q-BE Observatory"

    with TestClient(app) as cliente:
        salud = cliente.get("/health")
        assert salud.status_code == 200, salud.text
        assert salud.json() == {"status": "ONLINE", "db": "READ_ONLY"}

        portada = cliente.get("/")
        assert portada.status_code == 200, portada.text
        assert "Observatorio" in portada.text


# ── I3 — Resolución de calibración y convergencia del alias ───────────────────────────────────
def test_i3_calibracion_resuelve_y_el_alias_converge() -> None:
    """Canónico y alias deprecado devuelven 200 y la MISMA cifra (una sola verdad)."""
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as cliente:
        canonica = cliente.get("/api/observatory/backtesting/calibration-report")
        alias = cliente.get("/api/observatory/calibration-report")

    assert canonica.status_code == 200, canonica.text
    assert alias.status_code == 200, alias.text

    for respuesta in (canonica, alias):
        cuerpo = respuesta.json()
        assert "resumen_temporada" in cuerpo, cuerpo
        assert "jornadas" in cuerpo, cuerpo

        resumen = cuerpo["resumen_temporada"]
        assert 0.0 <= float(resumen["brier_score_qbe"]) <= 1.0

        jornadas = cuerpo["jornadas"]
        assert isinstance(jornadas, list) and jornadas, "sin jornadas calibradas"
        assert any(int(fila["total_partidos"]) > 0 for fila in jornadas)

    # Alias: deprecación declarada, no silenciosa.
    assert alias.headers.get("deprecation", "").lower() == "true"
    assert "successor-version" in alias.headers.get("link", "").lower()
    assert alias.headers.get("warning", "").startswith("299")

    # Misma fuente y mismo builder: cero divergencia de cifras.
    assert alias.json()["resumen_temporada"] == canonica.json()["resumen_temporada"]
