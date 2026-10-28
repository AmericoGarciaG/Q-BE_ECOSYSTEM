# -*- coding: utf-8 -*-
"""
🏆 THE SHIELD — GATEWAY READONLY ISOLATION SUITE
Juez Inmutable: [ARCH-ECOSYSTEM-GATEWAY-ISOLATION]
Base de Gobierno: Kybern Framework v13.5

Certifica que `PersistenceGateway` no envenena el proceso:

* **I1 — No envenenamiento:** una conexión SQLite `mode=ro` abierta por un motor
  ajeno sigue siendo legible después de importar el gateway y de crear su engine.
* **I2 — Guarda fiduciaria:** el propio gateway puede abrir una URL `mode=ro`
  sin lanzar `attempt to write a readonly database` (los pragmas de escritura
  se omiten silenciosamente).
* **I3 — Aislamiento estructural:** el listener `connect` vive en la instancia
  `self.engine`, jamás en la clase global `Engine` ni como símbolo de módulo.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine

# tests/ -> qbe_storage/ (raíz del paquete editable, resolutivo de `src.*`)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import src.storage.gateway as gateway_module  # noqa: E402
from src.storage.gateway import PersistenceGateway  # noqa: E402


def _reiniciar_singleton() -> None:
    """Cierra el engine vivo y limpia el singleton para una prueba determinista."""
    instancia = getattr(PersistenceGateway, "_instance", None)
    if instancia is not None:
        try:
            instancia.engine.dispose()
        except Exception:  # pragma: no cover — limpieza best-effort del singleton
            pass
        PersistenceGateway._instance = None


@pytest.fixture(autouse=True)
def _singleton_limpio():
    """Aísla cada prueba del estado global del singleton (antes y después)."""
    _reiniciar_singleton()
    try:
        yield
    finally:
        _reiniciar_singleton()


def _boveda_efimera(tmp_path: Path) -> Path:
    """Crea una BD real en journal `delete` (el caso que delata la fuga global)."""
    db_file = tmp_path / "prueba_readonly.db"
    conn = sqlite3.connect(str(db_file))
    try:
        conn.execute("CREATE TABLE t (id INT)")
        conn.commit()
    finally:
        conn.close()
    return db_file


def _url_ro(db_file: Path) -> str:
    return f"sqlite:///file:{db_file.as_posix()}?mode=ro&uri=true"


# ── I1 — No envenenamiento de conexiones readonly ajenas ─────────────────────────────────────
def test_i1_gateway_no_envenena_conexiones_readonly(tmp_path: Path) -> None:
    """[INVARIANZA 1] Crear el gateway no debe romper motores `mode=ro` externos."""
    db_file = _boveda_efimera(tmp_path)

    # 1. El módulo ya fue importado en la cabecera: una conexión readonly externa
    #    debe seguir viva (con el listener global de clase, esto fallaría aquí).
    ro_engine = create_engine(_url_ro(db_file))
    try:
        with ro_engine.connect() as ro_conn:
            assert ro_conn.execute(text("SELECT COUNT(*) FROM t")).scalar() == 0
    finally:
        ro_engine.dispose()

    # 2. Instanciar el gateway contra su propia BD (sin tocar settings ni data/).
    gw = PersistenceGateway(db_url=f"sqlite:///{db_file.as_posix()}")
    try:
        # 3. Su motor sí debe quedar configurado (WAL/FK) por el listener de instancia.
        with gw.engine.connect() as conn_gw:
            modo = conn_gw.exec_driver_sql("PRAGMA journal_mode;").scalar()
            fk = conn_gw.exec_driver_sql("PRAGMA foreign_keys;").scalar()
        assert str(modo).strip().lower() == "wal", f"journal_mode={modo!r}"
        assert int(fk) == 1, f"foreign_keys={fk!r}"

        # 4. Un motor readonly posterior sigue siendo inmune al gateway.
        ro_engine = create_engine(_url_ro(db_file))
        try:
            with ro_engine.connect() as ro_conn:
                assert ro_conn.execute(text("SELECT COUNT(*) FROM t")).scalar() == 0
        finally:
            ro_engine.dispose()
    finally:
        gw.engine.dispose()
        _reiniciar_singleton()


# ── I2 — Guarda fiduciaria del propio gateway sobre mode=ro ───────────────────────────────────
def test_i2_guarda_fiduciaria_gateway_readonly(tmp_path: Path) -> None:
    """[INVARIANZA 2] El gateway debe tolerar una URL `mode=ro` sin lanzar excepción."""
    db_file = _boveda_efimera(tmp_path)

    gw = PersistenceGateway(db_url=_url_ro(db_file))
    try:
        with gw.read_session() as session:
            assert session.execute(text("SELECT COUNT(*) FROM t")).scalar() == 0
    finally:
        gw.engine.dispose()
        _reiniciar_singleton()


# ── I3 — Aislamiento estructural del listener ────────────────────────────────────────────────
def test_i3_listener_ligado_a_la_instancia(tmp_path: Path) -> None:
    """[INVARIANZA 3] El handler debe estar en `gw.engine`, nunca en la clase `Engine`."""
    manejador = getattr(gateway_module, "_configurar_conexion_sqlite", None)
    assert callable(manejador), (
        "Falta el handler de conexión `_configurar_conexion_sqlite`: la configuración "
        "de PRAGMAs debe ser una función registrable por instancia."
    )
    assert not hasattr(gateway_module, "_set_sqlite_pragmas"), (
        "El símbolo global `_set_sqlite_pragmas` sigue existiendo: el parche del "
        "Observatorio lo buscaría y `event.remove` lanzaría InvalidRequestError."
    )
    assert not event.contains(Engine, "connect", manejador), (
        "El handler está registrado en la CLASE Engine: envenenaría todo el proceso."
    )

    db_file = _boveda_efimera(tmp_path)
    gw = PersistenceGateway(db_url=f"sqlite:///{db_file.as_posix()}")
    try:
        assert event.contains(gw.engine, "connect", manejador), (
            "El handler no está registrado en la instancia self.engine."
        )
        assert not event.contains(Engine, "connect", manejador), (
            "Crear el gateway propagó el handler a la clase Engine."
        )
    finally:
        gw.engine.dispose()
        _reiniciar_singleton()
