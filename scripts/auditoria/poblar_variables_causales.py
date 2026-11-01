# -*- coding: utf-8 -*-
"""[LN-QBE-146] Poblado de Variables Causales en la Bóveda OLAP.

Régimen: ``[DIRGEN-STRICT]``. Cero datos sintéticos, Null honesto, Fail-Loud.

Lee la línea de tiempo factual (``historical_match_events``), delega la
derivación en la función pura ``derivar_variables_causales`` (``src.core``) y
persiste una fila por partido en ``historical_match_causal_vars``.

Uso::

    python scripts/auditoria/poblar_variables_causales.py --migrar
    python scripts/auditoria/poblar_variables_causales.py
    python scripts/auditoria/poblar_variables_causales.py --match-id fs_2015_2016_z85264
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

RAIZ_PROYECTO = Path(__file__).resolve().parents[2]
for _ruta in (RAIZ_PROYECTO, RAIZ_PROYECTO / "qbe_core"):
    if str(_ruta) not in sys.path:
        sys.path.insert(0, str(_ruta))

from src.core.sovereign.derivar_variables_causales import (  # noqa: E402
    DerivacionError,
    VARIABLES,
    VARIABLES_DERIVADAS,
    VARIABLES_SIN_EVIDENCIA,
    derivar_variables_causales,
)

DB_DEFECTO = RAIZ_PROYECTO / "qbe_observatory" / "data" / "qbe_historico.db"

TABLA = "historical_match_causal_vars"
TABLA_EVENTOS = "historical_match_events"
TABLA_BOVEDA = "historical_matches"
FUENTE_DATOS = "LIGAMX_MXM"

#: Columnas del vector: ``vNN_local`` / ``vNN_visita`` para cada una de las 32.
COLUMNAS_VECTOR: Tuple[Tuple[str, str], ...] = tuple(
    (f"{variable.lower()}_{lado}", "REAL")
    for variable in VARIABLES
    for lado in ("local", "visita")
)

#: Columnas de gobierno de la fila.
COLUMNAS_META: Tuple[Tuple[str, str, str], ...] = (
    ("sin_evidencia", "TEXT", " NOT NULL DEFAULT '[]'"),
    ("derivadas", "INTEGER", " NOT NULL DEFAULT 0"),
    ("fuente_datos", "TEXT", f" NOT NULL DEFAULT '{FUENTE_DATOS}'"),
    ("cargado_utc", "TEXT", " NOT NULL DEFAULT ''"),
)

_SQL_EVENTOS = f"""
SELECT evento_id, orden_dom, minuto_texto, minuto_entero, minuto_agregado,
       periodo, tipo_evento, equipo, descripcion
  FROM {TABLA_EVENTOS}
 WHERE match_id = ?
 ORDER BY orden_dom
"""

_SQL_MATCHES = f"""
SELECT DISTINCT match_id
  FROM {TABLA_EVENTOS}
 ORDER BY match_id
"""


class PobladoError(RuntimeError):
    """[LN-QBE-146] Fallo de dominio del poblador de variables causales."""


# ── Esquema (Reflection DDL) ────────────────────────────────────────────────────────────────
def _ddl() -> str:
    columnas = ",\n    ".join(f"{nombre} {tipo}" for nombre, tipo in COLUMNAS_VECTOR)
    meta = ",\n    ".join(f"{nombre} {tipo}{extra}" for nombre, tipo, extra in COLUMNAS_META)
    return (
        f"CREATE TABLE IF NOT EXISTS {TABLA} (\n"
        f"    match_id TEXT PRIMARY KEY,\n"
        f"    {columnas},\n"
        f"    {meta},\n"
        f"    FOREIGN KEY (match_id) REFERENCES {TABLA_BOVEDA} (match_id)\n"
        ")"
    )


def _columnas(conexion: sqlite3.Connection, tabla: str) -> set:
    return {fila[1] for fila in conexion.execute(f'PRAGMA table_info("{tabla}")')}


def asegurar_esquema(conexion: sqlite3.Connection) -> None:
    """[LN-QBE-146] Aplica el DDL canónico y refleja columnas faltantes."""
    conexion.execute(_ddl())
    existentes = _columnas(conexion, TABLA)
    for nombre, tipo in COLUMNAS_VECTOR:
        if nombre not in existentes:
            conexion.execute(f'ALTER TABLE {TABLA} ADD COLUMN "{nombre}" {tipo}')
    for nombre, tipo, extra in COLUMNAS_META:
        if nombre not in existentes:
            conexion.execute(f'ALTER TABLE {TABLA} ADD COLUMN "{nombre}" {tipo}{extra}')


def _conectar(db_path: str | Path) -> sqlite3.Connection:
    ruta = Path(db_path)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    conexion = sqlite3.connect(str(ruta), isolation_level=None)
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion


# ── Poblado ────────────────────────────────────────────────────────────────────────────────
def _eventos_de(conexion: sqlite3.Connection, match_id: str) -> List[Dict[str, Any]]:
    filas = conexion.execute(_SQL_EVENTOS, (match_id,)).fetchall()
    return [
        {
            "evento_id": fila[0],
            "orden_dom": fila[1],
            "minuto_texto": fila[2],
            "minuto": fila[3],
            "minuto_agregado": fila[4],
            "periodo": fila[5],
            "tipo": fila[6],
            "lado": fila[7],
            "descripcion": fila[8],
        }
        for fila in filas
    ]


def _fila(match_id: str, vector: Dict[str, Dict[str, Optional[float]]]) -> Tuple[Any, ...]:
    valores: List[Any] = [match_id]
    for variable in VARIABLES:
        for lado in ("local", "visita"):
            valores.append(vector[variable][lado])
    valores.append(json.dumps(list(VARIABLES_SIN_EVIDENCIA), ensure_ascii=False))
    valores.append(len(VARIABLES_DERIVADAS))
    valores.append(FUENTE_DATOS)
    valores.append(datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
    return tuple(valores)


def _insert() -> str:
    columnas = ["match_id", *[nombre for nombre, _ in COLUMNAS_VECTOR]]
    columnas += [nombre for nombre, _, _ in COLUMNAS_META]
    marcadores = ", ".join("?" for _ in columnas)
    return (
        f"INSERT OR REPLACE INTO {TABLA} ({', '.join(columnas)})\n"
        f"VALUES ({marcadores})"
    )


def poblar(
    db_path: str | Path,
    *,
    match_id: Optional[str] = None,
    limite: Optional[int] = None,
    salida: Any = None,
) -> Dict[str, Any]:
    """Deriva y persiste el vector causal de cada partido con eventos."""
    salida = salida or sys.stdout
    conexion = _conectar(db_path)
    try:
        asegurar_esquema(conexion)
        if match_id:
            pendientes = [match_id]
        else:
            pendientes = [fila[0] for fila in conexion.execute(_SQL_MATCHES)]
        if limite is not None:
            pendientes = pendientes[:limite]
        if not pendientes:
            raise PobladoError(
                f"[LN-QBE-146] No hay partidos con eventos en {db_path}"
            )

        poblados: List[Tuple[str, int, float]] = []
        fallos: List[Dict[str, str]] = []
        for identificador in pendientes:
            try:
                eventos = _eventos_de(conexion, identificador)
                vector = derivar_variables_causales(identificador, eventos)
            except (DerivacionError, sqlite3.Error) as error:
                fallos.append(
                    {
                        "match_id": identificador,
                        "error_tipo": type(error).__name__,
                        "error": str(error),
                    }
                )
                continue
            conexion.execute("BEGIN IMMEDIATE")
            try:
                conexion.execute(_insert(), _fila(identificador, vector))
                conexion.execute("COMMIT")
            except BaseException:
                conexion.execute("ROLLBACK")
                raise
            derivadas = sum(
                1
                for variable in VARIABLES_DERIVADAS
                if vector[variable]["local"] is not None
                or vector[variable]["visita"] is not None
            )
            poblados.append((identificador, len(eventos), derivadas))

        total = conexion.execute(f"SELECT COUNT(*) FROM {TABLA}").fetchone()[0]
    finally:
        conexion.close()

    return {
        "partidos_objetivo": len(pendientes),
        "poblados": len(poblados),
        "fallidos": len(fallos),
        "fallos": fallos,
        "filas_en_tabla": total,
        "derivadas_promedio": (
            round(sum(fila[2] for fila in poblados) / len(poblados), 2) if poblados else 0.0
        ),
        "detalle": poblados,
    }


def _tablero(resultado: Dict[str, Any]) -> None:
    print(
        f"RESUMEN | objetivo {resultado['partidos_objetivo']} | "
        f"poblados {resultado['poblados']} | fallidos {resultado['fallidos']} | "
        f"filas_en_tabla {resultado['filas_en_tabla']} | "
        f"derivadas_promedio {resultado['derivadas_promedio']}"
    )
    for fallo in resultado["fallos"]:
        print(f"🔴 {fallo['match_id']}: {fallo['error_tipo']}: {fallo['error']}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    analizador = argparse.ArgumentParser(
        prog="poblar_variables_causales",
        description="[LN-QBE-146] Puebla el vector causal de 32 variables por partido.",
    )
    analizador.add_argument("--db", default=str(DB_DEFECTO), help="ruta de qbe_historico.db")
    analizador.add_argument("--match-id", default=None, help="puebla un solo partido")
    analizador.add_argument("--limite", type=int, default=None, help="tope de partidos")
    analizador.add_argument("--migrar", action="store_true", help="sólo aplica el DDL")
    analizador.add_argument("--reporte-json", default=None, help="bitácora del poblado (JSON)")
    argumentos = analizador.parse_args(argv)

    if argumentos.migrar and not (argumentos.match_id or argumentos.limite):
        conexion = _conectar(argumentos.db)
        try:
            asegurar_esquema(conexion)
            total = conexion.execute(f"SELECT COUNT(*) FROM {TABLA}").fetchone()[0]
        finally:
            conexion.close()
        print(f"Esquema asegurado en {argumentos.db}: filas={total}")
        return 0

    try:
        resultado = poblar(
            argumentos.db,
            match_id=argumentos.match_id,
            limite=argumentos.limite,
        )
    except (PobladoError, sqlite3.Error) as error:
        print(f"🔴 {error}", file=sys.stderr)
        return 1

    if argumentos.reporte_json:
        ruta = Path(argumentos.reporte_json)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")

    _tablero(resultado)
    return 0 if resultado["fallidos"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
