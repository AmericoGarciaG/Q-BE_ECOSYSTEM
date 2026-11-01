# -*- coding: utf-8 -*-
"""[LN-QBE-144] Almacén de Eventos Históricos (``historical_match_events``).

Régimen: ``[DIRGEN-STRICT]``. Cero datos sintéticos, Null honesto, Fail-Loud.

Contrato
--------
``cargar_eventos(db_path, match_id, eventos) -> dict``
    Inserta masiva e idempotentemente la lista de eventos que produce
    ``parsear_minuto_a_minuto`` ([LN-QBE-141]) bajo una llave de la bóveda
    (``historical_matches.match_id``).

``resolver_match_id(db_path, temporada, equipo_local, equipo_visitante,
goles_local, goles_visitante) -> str``
    Join Determinista de ``[ARCH-1.5.1]`` §15.3: exige exactamente una fila.

Garantías
---------
* ``INSERT OR IGNORE`` sobre la PK compuesta ``(match_id, evento_id)``: recargar
  un partido no duplica ni altera eventos.
* Una sola transacción ``BEGIN IMMEDIATE`` con ``ROLLBACK`` ante cualquier fallo.
* Reflection DDL: ``CREATE TABLE IF NOT EXISTS`` + ``PRAGMA table_info`` para
  agregar columnas faltantes sin recrear la tabla.
* Integridad referencial explícita (SQLite no fuerza FK por defecto).
* No toca ``matches``, ``sovereign_distributions`` ni ``match_telemetry``.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .load_historical_footystats import normalizar_temporada, slugify

__all__ = [
    "AlmacenEventosError",
    "EventoInvalidoError",
    "MatchResolutionError",
    "asegurar_esquema",
    "cargar_eventos",
    "resolver_match_id",
]

RAIZ_PROYECTO = Path(__file__).resolve().parents[4]
DB_DEFECTO = RAIZ_PROYECTO / "qbe_observatory" / "data" / "qbe_historico.db"

TABLA = "historical_match_events"
TABLA_BOVEDA = "historical_matches"
FUENTE_DATOS = "LIGAMX_MXM"

# Transcrito de ``docs/ARCH.md`` §15.2 ([ARCH-1.5.1]). Una sola fuente de DDL.
DDL_TABLA = f"""
CREATE TABLE IF NOT EXISTS {TABLA} (
    match_id        TEXT    NOT NULL,
    evento_id       TEXT    NOT NULL,
    minuto_texto    TEXT    NOT NULL,
    minuto_entero   INTEGER,
    minuto_agregado INTEGER,
    periodo         TEXT,
    tipo_evento     TEXT    NOT NULL,
    equipo          TEXT    NOT NULL CHECK (equipo IN ('local', 'visita')),
    descripcion     TEXT    NOT NULL,
    orden_dom       INTEGER NOT NULL,
    fuente_datos    TEXT    NOT NULL DEFAULT '{FUENTE_DATOS}',
    cargado_utc     TEXT    NOT NULL,
    PRIMARY KEY (match_id, evento_id),
    FOREIGN KEY (match_id) REFERENCES {TABLA_BOVEDA} (match_id)
)
"""

DDL_INDICE = f"""
CREATE INDEX IF NOT EXISTS idx_hist_events_match
    ON {TABLA} (match_id, orden_dom)
"""

# Reflection DDL: columnas canónicas posteriores a la creación original. Una
# bóveda creada por una versión anterior recibe la columna, nunca una tabla nueva.
_COLUMNAS_CANONICAS: Tuple[Tuple[str, str, str], ...] = (
    ("minuto_texto", "TEXT", " NOT NULL DEFAULT ''"),
    ("minuto_entero", "INTEGER", ""),
    ("minuto_agregado", "INTEGER", ""),
    ("periodo", "TEXT", ""),
    ("tipo_evento", "TEXT", " NOT NULL DEFAULT 'otro'"),
    ("equipo", "TEXT", " NOT NULL DEFAULT 'local'"),
    ("descripcion", "TEXT", " NOT NULL DEFAULT ''"),
    ("orden_dom", "INTEGER", " NOT NULL DEFAULT 0"),
    ("fuente_datos", "TEXT", f" NOT NULL DEFAULT '{FUENTE_DATOS}'"),
    ("cargado_utc", "TEXT", " NOT NULL DEFAULT ''"),
)

_INSERT = f"""
INSERT OR IGNORE INTO {TABLA} (
    match_id, evento_id, minuto_texto, minuto_entero, minuto_agregado,
    periodo, tipo_evento, equipo, descripcion, orden_dom,
    fuente_datos, cargado_utc
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

_SQL_RESOLUCION = f"""
SELECT match_id
  FROM {TABLA_BOVEDA}
 WHERE temporada = ?
   AND home_team_slug = ?
   AND away_team_slug = ?
   AND home_goals = ?
   AND away_goals = ?
 ORDER BY match_id
"""


class AlmacenEventosError(RuntimeError):
    """[LN-QBE-144] Fallo de dominio del almacén de eventos."""


class EventoInvalidoError(AlmacenEventosError):
    """[LN-QBE-144] Un evento no cumple el contrato de [LN-QBE-141]."""


class MatchResolutionError(AlmacenEventosError):
    """[LN-QBE-144] El Join Determinista no resuelve una única fila de la bóveda."""


# ── Utilidades ────────────────────────────────────────────────────────────────────────────────
def _ahora_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _conectar(db_path: str | Path) -> sqlite3.Connection:
    """Abre la bóveda en modo autocommit para gobernar la transacción a mano."""
    ruta = Path(db_path)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    conexion = sqlite3.connect(str(ruta), isolation_level=None)
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion


def _columnas(conexion: sqlite3.Connection, tabla: str) -> set:
    return {fila[1] for fila in conexion.execute(f'PRAGMA table_info("{tabla}")')}


def asegurar_esquema(conexion: sqlite3.Connection) -> None:
    """[LN-QBE-144] Aplica el DDL canónico y refleja columnas faltantes."""
    conexion.execute(DDL_TABLA)
    existentes = _columnas(conexion, TABLA)
    for columna, tipo, extra in _COLUMNAS_CANONICAS:
        if columna not in existentes:
            conexion.execute(f'ALTER TABLE {TABLA} ADD COLUMN "{columna}" {tipo}{extra}')
    conexion.execute(DDL_INDICE)


def _entero(valor: Any, campo: str, indice: int) -> Optional[int]:
    if valor is None or valor == "":
        return None
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise EventoInvalidoError(
            f"[LN-QBE-144] Evento #{indice}: {campo} debe ser entero o nulo: {valor!r}"
        )
    return valor


def _texto(valor: Any, campo: str, indice: int) -> str:
    texto = "" if valor is None else str(valor).strip()
    if not texto:
        raise EventoInvalidoError(
            f"[LN-QBE-144] Evento #{indice}: {campo} es obligatorio y está vacío"
        )
    return texto


def _fila(
    match_id: str, evento: Any, indice: int, fuente_datos: str, cargado: str
) -> Tuple[Any, ...]:
    """Traduce un evento del parser a la tupla canónica de la tabla."""
    if not isinstance(evento, dict):
        raise EventoInvalidoError(
            f"[LN-QBE-144] Evento #{indice}: se esperaba dict, se recibió {type(evento).__name__}"
        )
    evento_id = _texto(evento.get("evento_id"), "evento_id", indice)
    lado = _texto(evento.get("lado"), "lado", indice)
    if lado not in ("local", "visita"):
        raise EventoInvalidoError(
            f"[LN-QBE-144] Evento {evento_id}: lado debe ser 'local' o 'visita', no {lado!r}"
        )
    orden = _entero(evento.get("orden_dom"), "orden_dom", indice)
    if orden is None:
        raise EventoInvalidoError(
            f"[LN-QBE-144] Evento {evento_id}: orden_dom es obligatorio"
        )
    periodo = evento.get("periodo")
    return (
        match_id,
        evento_id,
        _texto(evento.get("minuto_texto"), "minuto_texto", indice),
        _entero(evento.get("minuto"), "minuto", indice),
        _entero(evento.get("minuto_agregado"), "minuto_agregado", indice),
        None if periodo is None or str(periodo).strip() == "" else str(periodo).strip(),
        _texto(evento.get("tipo"), "tipo", indice),
        lado,
        _texto(evento.get("descripcion"), "descripcion", indice),
        orden,
        fuente_datos,
        cargado,
    )


# ── Resolución de llave (Join Determinista, [ARCH-1.5.1] §15.3) ──────────────────────────────
def resolver_match_id(
    db_path: str | Path,
    temporada: str,
    equipo_local: str,
    equipo_visitante: str,
    goles_local: Optional[int],
    goles_visitante: Optional[int],
) -> str:
    """Resuelve el ``match_id`` de la bóveda; exige exactamente una fila."""
    temporada_norm = normalizar_temporada(temporada)
    if not temporada_norm:
        raise MatchResolutionError(
            f"[LN-QBE-144] Temporada no normalizable a YYYY_YYYY: {temporada!r}"
        )
    local_slug = slugify(equipo_local)
    visita_slug = slugify(equipo_visitante)
    if not local_slug or not visita_slug:
        raise MatchResolutionError(
            "[LN-QBE-144] Los clubes no son canonizables a slug: "
            f"{equipo_local!r} / {equipo_visitante!r}"
        )
    if goles_local is None or goles_visitante is None:
        raise MatchResolutionError(
            "[LN-QBE-144] El marcador es obligatorio para resolver la llave: "
            f"{goles_local!r}-{goles_visitante!r}"
        )

    ruta = Path(db_path)
    if not ruta.is_file():
        raise MatchResolutionError(f"[LN-QBE-144] La bóveda no existe: {ruta}")

    conexion = _conectar(ruta)
    try:
        filas = [
            fila[0]
            for fila in conexion.execute(
                _SQL_RESOLUCION,
                (
                    temporada_norm,
                    local_slug,
                    visita_slug,
                    int(goles_local),
                    int(goles_visitante),
                ),
            )
        ]
    finally:
        conexion.close()

    if len(filas) != 1:
        raise MatchResolutionError(
            "[LN-QBE-144] Join Determinista sin resolución única para "
            f"{temporada_norm} {equipo_local} {goles_local}-{goles_visitante} "
            f"{equipo_visitante}: {len(filas)} candidatos {filas[:5]}"
        )
    return filas[0]


# ── Persistencia ─────────────────────────────────────────────────────────────────────────────
def cargar_eventos(
    db_path: str | Path,
    match_id: str,
    eventos: Sequence[Dict[str, Any]],
    *,
    fuente_datos: str = FUENTE_DATOS,
) -> Dict[str, Any]:
    """[LN-QBE-144] Inserta la lista de eventos de forma masiva e idempotente."""
    if not isinstance(match_id, str) or not match_id.strip():
        raise EventoInvalidoError(
            f"[LN-QBE-144] match_id debe ser un texto no vacío: {match_id!r}"
        )
    if not eventos:
        raise EventoInvalidoError(
            f"[LN-QBE-144] Lista de eventos vacía para {match_id}: se aborta sin escribir"
        )

    cargado = _ahora_utc()
    filas = [
        _fila(match_id.strip(), evento, indice, fuente_datos, cargado)
        for indice, evento in enumerate(eventos)
    ]

    conexion = _conectar(db_path)
    try:
        conexion.execute("BEGIN IMMEDIATE")
        try:
            asegurar_esquema(conexion)
            if conexion.execute(
                f"SELECT 1 FROM {TABLA_BOVEDA} WHERE match_id = ?", (match_id.strip(),)
            ).fetchone() is None:
                raise MatchResolutionError(
                    f"[LN-QBE-144] match_id inexistente en {TABLA_BOVEDA}: {match_id!r}"
                )
            antes = conexion.total_changes
            conexion.executemany(_INSERT, filas)
            insertados = conexion.total_changes - antes
            conexion.execute("COMMIT")
        except BaseException:
            conexion.execute("ROLLBACK")
            raise
        total = conexion.execute(
            f"SELECT COUNT(*) FROM {TABLA} WHERE match_id = ?", (match_id.strip(),)
        ).fetchone()[0]
    finally:
        conexion.close()

    return {
        "match_id": match_id.strip(),
        "recibidos": len(filas),
        "insertados": insertados,
        "ignorados": len(filas) - insertados,
        "total_en_tabla": total,
    }


def migrar(db_path: str | Path) -> Dict[str, int]:
    """Crea/refleja la tabla canónica en la bóveda indicada."""
    conexion = _conectar(db_path)
    try:
        asegurar_esquema(conexion)
        total = conexion.execute(f"SELECT COUNT(*) FROM {TABLA}").fetchone()[0]
    finally:
        conexion.close()
    return {"total_en_tabla": total}


# ── CLI ──────────────────────────────────────────────────────────────────────────────────────
def _cargar_json(ruta: Path) -> List[Dict[str, Any]]:
    datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    if isinstance(datos, dict):
        datos = datos.get("eventos")
    if not isinstance(datos, list):
        raise EventoInvalidoError(
            f"[LN-QBE-144] {ruta} no contiene una lista de eventos"
        )
    return datos


def _tablero(resultado: Dict[str, Any]) -> None:
    print(f"match_id        : {resultado['match_id']}")
    print(f"recibidos       : {resultado['recibidos']}")
    print(f"insertados      : {resultado['insertados']}")
    print(f"ignorados       : {resultado['ignorados']}")
    print(f"total_en_tabla  : {resultado['total_en_tabla']}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    analizador = argparse.ArgumentParser(
        prog="cargar_eventos_historicos",
        description="[LN-QBE-144] Almacén idempotente de eventos minuto a minuto.",
    )
    analizador.add_argument("--db", default=str(DB_DEFECTO), help="ruta de qbe_historico.db")
    analizador.add_argument("--migrar", action="store_true", help="aplica el DDL canónico")
    analizador.add_argument("--match-id", default=None, help="llave de la bóveda")
    analizador.add_argument("--eventos-json", default=None, help="lista de eventos (JSON)")
    analizador.add_argument("--temporada", default=None, help="resolución: temporada")
    analizador.add_argument("--local", default=None, help="resolución: club local")
    analizador.add_argument("--visitante", default=None, help="resolución: club visitante")
    analizador.add_argument("--marcador", default=None, help="resolución: '3-3'")
    argumentos = analizador.parse_args(argv)

    db = Path(argumentos.db)
    try:
        if argumentos.migrar:
            print(f"Esquema asegurado en {db}: {migrar(db)}")
            if not argumentos.eventos_json:
                return 0

        if not argumentos.eventos_json:
            analizador.error("Indique --migrar o --eventos-json")

        match_id = argumentos.match_id
        if not match_id:
            if not (argumentos.temporada and argumentos.local and argumentos.visitante and argumentos.marcador):
                analizador.error(
                    "Indique --match-id o el cuarteto --temporada/--local/--visitante/--marcador"
                )
            goles = argumentos.marcador.replace(" ", "").split("-")
            if len(goles) != 2:
                analizador.error(f"Marcador no reconocido: {argumentos.marcador!r}")
            match_id = resolver_match_id(
                db,
                argumentos.temporada,
                argumentos.local,
                argumentos.visitante,
                int(goles[0]),
                int(goles[1]),
            )
            print(f"match_id resuelto: {match_id}")

        resultado = cargar_eventos(db, match_id, _cargar_json(Path(argumentos.eventos_json)))
    except (AlmacenEventosError, OSError, ValueError, json.JSONDecodeError) as error:
        print(f"🔴 {error}", file=sys.stderr)
        return 1

    _tablero(resultado)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
