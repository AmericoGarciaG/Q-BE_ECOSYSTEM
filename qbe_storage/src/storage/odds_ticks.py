# -*- coding: utf-8 -*-
"""`[ARCH-1.5.13]` Persistencia Append-Only de Odds Históricos (`odds_ticks`).

Régimen: ``[DIRGEN-STRICT]``. Esquema 3NF de la fuente única de verdad para
los momios en vivo. La tabla es **append-only**: no se actualiza ni se borra
un tick; la corrección se expresa con un tick nuevo.

Columnas canónicas
------------------
``tick_id`` (PK), ``match_id`` (FK lógica a ``matches.id``), ``casino_id``,
``timestamp``, ``odd_home``, ``odd_draw``, ``odd_away``, ``vig``,
``delta_odd``, ``origen``, ``cargado_utc``.

Invariantes
-----------
* Cuotas decimales finitas y estrictamente mayores que ``1.0``.
* ``UNIQUE(match_id, casino_id, timestamp)`` para idempotencia.
* ``vig = Σ(1/odd) - 1`` y ``delta_odd`` = variación de la cuota local contra
  el tick inmediatamente anterior del mismo partido/casino (``0.0`` si es el
  primero).
"""

from __future__ import annotations

import math
import sqlite3
from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Sequence

__all__ = [
    "DDL_ODDS_TICKS",
    "OddsTicksError",
    "calcular_vig",
    "crear_tabla_odds_ticks",
    "insertar_tick",
    "serie_historica",
    "ultimo_tick",
]

DDL_ODDS_TICKS = """
CREATE TABLE IF NOT EXISTS odds_ticks (
    tick_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id   TEXT    NOT NULL,
    casino_id  TEXT    NOT NULL,
    timestamp  TEXT    NOT NULL,
    odd_home   REAL    NOT NULL CHECK (odd_home > 1.0),
    odd_draw   REAL    NOT NULL CHECK (odd_draw > 1.0),
    odd_away   REAL    NOT NULL CHECK (odd_away > 1.0),
    vig        REAL,
    delta_odd  REAL,
    origen     TEXT    NOT NULL DEFAULT 'CENTINELA_MULTICASA',
    cargado_utc TEXT   NOT NULL,
    UNIQUE (match_id, casino_id, timestamp),
    FOREIGN KEY (match_id) REFERENCES matches (id)
);

CREATE INDEX IF NOT EXISTS idx_odds_ticks_match_ts
    ON odds_ticks (match_id, timestamp);

CREATE INDEX IF NOT EXISTS idx_odds_ticks_casino
    ON odds_ticks (casino_id, timestamp);
"""


class OddsTicksError(ValueError):
    """Tick fuera del contrato de ``odds_ticks``."""


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _validar_cuota(nombre: str, valor: Any) -> float:
    try:
        cuota = float(valor)
    except (TypeError, ValueError) as error:
        raise OddsTicksError(f"Cuota '{nombre}' no decimal: {valor!r}.") from error
    if not math.isfinite(cuota) or cuota <= 1.0:
        raise OddsTicksError(f"Cuota '{nombre}' inválida: {valor!r}. Debe ser > 1.0.")
    return cuota


def calcular_vig(odd_home: float, odd_draw: float, odd_away: float) -> float:
    """Margen comercial implícito: ``Σ(1/odd) - 1``."""
    l = _validar_cuota("odd_home", odd_home)
    e = _validar_cuota("odd_draw", odd_draw)
    v = _validar_cuota("odd_away", odd_away)
    return (1.0 / l) + (1.0 / e) + (1.0 / v) - 1.0


def crear_tabla_odds_ticks(conexion: sqlite3.Connection) -> None:
    """Crea la tabla y sus índices si no existen (idempotente)."""
    conexion.executescript(DDL_ODDS_TICKS)


def _ultima_cuota_local(
    conexion: sqlite3.Connection, match_id: str, casino_id: str
) -> Optional[float]:
    fila = conexion.execute(
        "SELECT odd_home FROM odds_ticks WHERE match_id = ? AND casino_id = ? "
        "ORDER BY timestamp DESC, tick_id DESC LIMIT 1",
        (match_id, casino_id),
    ).fetchone()
    return float(fila[0]) if fila else None


def insertar_tick(
    conexion: sqlite3.Connection,
    match_id: str,
    casino_id: str,
    timestamp: str,
    odd_home: float,
    odd_draw: float,
    odd_away: float,
    origen: str = "CENTINELA_MULTICASA",
) -> bool:
    """Inserta un tick nuevo; retorna ``True`` si la fila entró (idempotente)."""
    if not match_id or not casino_id:
        raise OddsTicksError("match_id y casino_id son obligatorios.")
    if not timestamp:
        raise OddsTicksError("timestamp es obligatorio.")
    l = _validar_cuota("odd_home", odd_home)
    e = _validar_cuota("odd_draw", odd_draw)
    v = _validar_cuota("odd_away", odd_away)
    anterior = _ultima_cuota_local(conexion, match_id, casino_id)
    delta = 0.0 if anterior is None else l - anterior
    cursor = conexion.execute(
        "INSERT OR IGNORE INTO odds_ticks "
        "(match_id, casino_id, timestamp, odd_home, odd_draw, odd_away, vig, delta_odd, origen, cargado_utc) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            match_id,
            casino_id,
            timestamp,
            l,
            e,
            v,
            calcular_vig(l, e, v),
            delta,
            origen,
            _utc_iso(),
        ),
    )
    return cursor.rowcount == 1


def ultimo_tick(
    conexion: sqlite3.Connection, match_id: str
) -> Optional[Mapping[str, Any]]:
    """Último tick del partido (``ORDER BY timestamp DESC LIMIT 1``)."""
    fila = conexion.execute(
        "SELECT * FROM odds_ticks WHERE match_id = ? "
        "ORDER BY timestamp DESC, tick_id DESC LIMIT 1",
        (match_id,),
    ).fetchone()
    if fila is None:
        return None
    columnas = [descripcion[0] for descripcion in conexion.execute(
        "SELECT * FROM odds_ticks LIMIT 0"
    ).description or []]
    return dict(zip(columnas, fila))


def serie_historica(
    conexion: sqlite3.Connection, match_id: str, casino_id: Optional[str] = None
) -> Sequence[Mapping[str, Any]]:
    """Serie histórica completa del partido, opcionalmente filtrada por casino."""
    if casino_id is None:
        filas = conexion.execute(
            "SELECT * FROM odds_ticks WHERE match_id = ? "
            "ORDER BY timestamp ASC, tick_id ASC",
            (match_id,),
        ).fetchall()
    else:
        filas = conexion.execute(
            "SELECT * FROM odds_ticks WHERE match_id = ? AND casino_id = ? "
            "ORDER BY timestamp ASC, tick_id ASC",
            (match_id, casino_id),
        ).fetchall()
    columnas = [descripcion[0] for descripcion in conexion.execute(
        "SELECT * FROM odds_ticks LIMIT 0"
    ).description or []]
    return [dict(zip(columnas, fila)) for fila in filas]
