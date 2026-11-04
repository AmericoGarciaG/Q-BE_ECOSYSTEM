# -*- coding: utf-8 -*-
"""`[ARCH-1.5.14]` Consolidador de Bóvedas Históricas → Bóveda Canónica.

Escanea las SQLite legacy, rescata momios históricos (`odds_ticks`), capas de
mercado de los snapshots, distribuciones soberanas y las 32 dimensiones
causales (`match_causal_vars`) y las UPSERTA en `data/qbe_database.db`.

Reglas
------
* ``[GOVERNANCE-01]``: sólo se copia evidencia factual; ``None`` se omite y
  jamás se imputa ``0.0``.
* Idempotente: ``INSERT OR IGNORE`` y llaves únicas; dos corridas no duplican.
* La bóveda canónica se respalda antes de la primera escritura.
* No borra ninguna base ni fila: sólo agrega o completa campos ausentes.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

RAIZ = Path(__file__).resolve().parents[2]
CANONICA = RAIZ / "data" / "qbe_database.db"
LEGACY = RAIZ.parent / "Q_BE_CD_WEB" / "data" / "qbe_database.db"
HISTORICO = RAIZ / "qbe_observatory" / "data" / "qbe_historico.db"
BACKUPS = RAIZ / "data" / "backups"
CAMPOS_MERCADO = (
    "momios",
    "momios_operadores",
    "probabilidades_sin_comision",
    "consenso_mercado",
    "arbitraje",
)

if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.storage.odds_ticks import (  # noqa: E402
    OddsTicksError,
    crear_tabla_odds_ticks,
    insertar_tick,
)

Stats = Dict[str, int]


def _stats() -> Stats:
    return {
        "snapshots": 0,
        "snapshots_nuevos": 0,
        "partidos": 0,
        "partidos_rescatados": 0,
        "capas_mercado": 0,
        "ticks": 0,
        "ticks_omitidos": 0,
        "distribuciones": 0,
        "causal_filas": 0,
        "variables_32d": 0,
    }


def _ro(ruta: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{ruta.as_posix()}?mode=ro", uri=True, timeout=5.0)


def _tabla_existe(conexion: sqlite3.Connection, tabla: str) -> bool:
    return conexion.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (tabla,)
    ).fetchone() is not None


def _columnas(conexion: sqlite3.Connection, tabla: str) -> List[str]:
    return [fila[1] for fila in conexion.execute(f'PRAGMA table_info("{tabla}")')]


def _backup(canonica: Path) -> Path:
    BACKUPS.mkdir(parents=True, exist_ok=True)
    marca = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destino = BACKUPS / f"qbe_database_pre_consolidacion_{marca}.db"
    origen = sqlite3.connect(canonica)
    respaldo = sqlite3.connect(destino)
    try:
        origen.backup(respaldo)
    finally:
        respaldo.close()
        origen.close()
    return destino


def _crear_tabla_causal(canonica: sqlite3.Connection, fuente: sqlite3.Connection) -> None:
    if _tabla_existe(canonica, "match_causal_vars"):
        return
    info = fuente.execute("PRAGMA table_info(historical_match_causal_vars)").fetchall()
    definiciones = []
    for _, nombre, tipo, _, _, pk in info:
        definiciones.append(f'"{nombre}" {tipo or "TEXT"}' + (" PRIMARY KEY" if pk else ""))
    canonica.execute(
        f'CREATE TABLE IF NOT EXISTS match_causal_vars ({", ".join(definiciones)})'
    )


def _rescue_ticks(
    canonica: sqlite3.Connection,
    partido: Dict[str, Any],
    updated_at: str,
    etiqueta: str,
    match_ids: set,
    stats: Stats,
) -> None:
    match_id = str(partido.get("id_partido") or "").strip()
    if not match_id:
        stats["ticks_omitidos"] += 1
        return
    if match_id not in match_ids:
        stats["ticks_omitidos"] += 1
        return

    candidatos: List[Tuple[str, str, float, float, float]] = []
    operadores = partido.get("momios_operadores") or {}
    if isinstance(operadores, dict):
        for casino, payload in operadores.items():
            if not isinstance(payload, dict):
                continue
            l, e, v = payload.get("L"), payload.get("E"), payload.get("V")
            if l is None or e is None or v is None:
                continue
            timestamp = str(payload.get("updated_at") or updated_at or "").strip()
            if not timestamp:
                continue
            candidatos.append((timestamp, str(casino), float(l), float(e), float(v)))
    if not candidatos and isinstance(partido.get("momios"), dict):
        payload = partido["momios"]
        l, e, v = payload.get("L"), payload.get("E"), payload.get("V")
        if l is not None and e is not None and v is not None:
            candidatos.append(
                (str(updated_at or "").strip(), "caliente", float(l), float(e), float(v))
            )

    for timestamp, casino, l, e, v in sorted(candidatos):
        try:
            if insertar_tick(
                canonica,
                match_id,
                casino,
                timestamp,
                l,
                e,
                v,
                origen=f"CONSOLIDACION::{etiqueta}",
            ):
                stats["ticks"] += 1
        except (OddsTicksError, ValueError):
            stats["ticks_omitidos"] += 1


def _merge_snapshots(
    canonica: sqlite3.Connection,
    fuente: sqlite3.Connection,
    etiqueta: str,
    match_ids: set,
    stats: Stats,
) -> None:
    if not _tabla_existe(fuente, "fixtures_snapshots"):
        return
    filas = fuente.execute(
        "SELECT league_id, matchday, updated_at, matches_json FROM fixtures_snapshots"
    ).fetchall()
    stats["snapshots"] += len(filas)

    for league_id, matchday, updated_at, crudo in filas:
        try:
            origen = json.loads(crudo) if crudo else []
        except (TypeError, ValueError):
            continue
        if not isinstance(origen, list):
            continue
        stats["partidos"] += len(origen)
        updated_at = str(updated_at or "").strip()

        objetivo = canonica.execute(
            "SELECT id, updated_at, matches_json FROM fixtures_snapshots "
            "WHERE league_id = ? AND matchday = ? ORDER BY updated_at DESC LIMIT 1",
            (league_id, matchday),
        ).fetchone()

        if objetivo is None:
            canonica.execute(
                "INSERT INTO fixtures_snapshots (league_id, matchday, updated_at, matches_json) "
                "VALUES (?, ?, ?, ?)",
                (
                    league_id,
                    matchday,
                    updated_at,
                    json.dumps(origen, ensure_ascii=False),
                ),
            )
            stats["snapshots_nuevos"] += 1
            destino = [dict(partido) for partido in origen]
        else:
            try:
                destino = json.loads(objetivo[2]) if objetivo[2] else []
            except (TypeError, ValueError):
                destino = []
            if not isinstance(destino, list):
                destino = []

        indice: Dict[Tuple[Any, Any], int] = {
            (p.get("local"), p.get("visitante")): posicion
            for posicion, p in enumerate(destino)
            if isinstance(p, dict)
        }
        for partido in origen:
            if not isinstance(partido, dict):
                continue
            clave = (partido.get("local"), partido.get("visitante"))
            posicion = indice.get(clave)
            if posicion is None:
                destino.append(dict(partido))
                indice[clave] = len(destino) - 1
                stats["partidos_rescatados"] += 1
            else:
                anterior = destino[posicion]
                # El origen legacy es la evidencia fresca del estado del partido;
                # la capa de mercado del destino se conserva si el origen no la trae.
                fusion = dict(partido)
                for campo in CAMPOS_MERCADO:
                    if not fusion.get(campo) and anterior.get(campo):
                        fusion[campo] = anterior[campo]
                        stats["capas_mercado"] += 1
                destino[posicion] = fusion
                indice[clave] = posicion

        if objetivo is None:
            nuevo_updated = updated_at
        else:
            nuevo_updated = max(str(objetivo[1] or ""), updated_at)
            canonica.execute(
                "UPDATE fixtures_snapshots SET matches_json = ?, updated_at = ? WHERE id = ?",
                (json.dumps(destino, ensure_ascii=False), nuevo_updated, objetivo[0]),
            )

        for partido in origen:
            if isinstance(partido, dict):
                _rescue_ticks(canonica, partido, updated_at, etiqueta, match_ids, stats)


def _rescue_distribuciones(
    canonica: sqlite3.Connection,
    fuente: sqlite3.Connection,
    etiqueta: str,
    match_ids: set,
    stats: Stats,
) -> None:
    if not _tabla_existe(fuente, "sovereign_distributions"):
        return
    columnas = _columnas(fuente, "sovereign_distributions")
    if "match_id" not in columnas:
        return
    filas = fuente.execute(
        f'SELECT {", ".join(columnas)} FROM sovereign_distributions'
    ).fetchall()
    marcadores = ", ".join("?" for _ in columnas)
    for fila in filas:
        if str(fila[columnas.index("match_id")]) not in match_ids:
            continue
        cursor = canonica.execute(
            f'INSERT OR IGNORE INTO sovereign_distributions ({", ".join(columnas)}) '
            f"VALUES ({marcadores})",
            fila,
        )
        if cursor.rowcount == 1:
            stats["distribuciones"] += 1


def _rescue_causal(
    canonica: sqlite3.Connection,
    fuente: sqlite3.Connection,
    etiqueta: str,
    stats: Stats,
) -> None:
    if not _tabla_existe(fuente, "historical_match_causal_vars"):
        return
    _crear_tabla_causal(canonica, fuente)
    columnas = _columnas(fuente, "historical_match_causal_vars")
    filas = fuente.execute(
        f'SELECT {", ".join(columnas)} FROM historical_match_causal_vars'
    ).fetchall()
    marcadores = ", ".join("?" for _ in columnas)
    for fila in filas:
        cursor = canonica.execute(
            f'INSERT OR IGNORE INTO match_causal_vars ({", ".join(columnas)}) '
            f"VALUES ({marcadores})",
            fila,
        )
        if cursor.rowcount != 1:
            continue
        stats["causal_filas"] += 1
        for columna, valor in zip(columnas, fila):
            if valor is not None and columna.startswith("v") and (
                columna.endswith("_local") or columna.endswith("_visita")
            ):
                stats["variables_32d"] += 1


def main() -> int:
    if not CANONICA.is_file():
        print(f"[ERROR] No existe la bóveda canónica: {CANONICA}")
        return 2

    respaldo = _backup(CANONICA)
    print("=" * 78)
    print("[ARCH-1.5.14] CONSOLIDACIÓN DE BÓVEDAS LEGACY → BÓVEDA CANÓNICA")
    print("=" * 78)
    print(f"Canónica : {CANONICA}")
    print(f"Respaldo : {respaldo}")
    print("[GOVERNANCE-01] Sólo evidencia factual; None omitido; cero ceros sintéticos.\n")

    canonica = sqlite3.connect(CANONICA, timeout=30.0)
    canonica.execute("PRAGMA foreign_keys = ON;")
    crear_tabla_odds_ticks(canonica)
    match_ids = {fila[0] for fila in canonica.execute("SELECT id FROM matches")}
    total = _stats()

    fuentes: Sequence[Tuple[str, Path]] = (
        ("legacy", LEGACY),
        ("historico", HISTORICO),
    )
    try:
        for etiqueta, ruta in fuentes:
            if not ruta.is_file():
                print(f"[{etiqueta}] AUSENTE: {ruta}")
                continue
            try:
                fuente = _ro(ruta)
            except sqlite3.Error as error:
                print(f"[{etiqueta}] No se pudo abrir: {error}")
                continue
            stats = _stats()
            try:
                if etiqueta == "historico":
                    # La bóveda histórica aporta las 32 dimensiones causales; sus
                    # snapshots FOTMOB pertenecen a otro corpus y no se mezclan
                    # con la cartelera viva.
                    _rescue_causal(canonica, fuente, etiqueta, stats)
                else:
                    _merge_snapshots(canonica, fuente, etiqueta, match_ids, stats)
                    _rescue_distribuciones(canonica, fuente, etiqueta, match_ids, stats)
                    _rescue_causal(canonica, fuente, etiqueta, stats)
            except sqlite3.Error as error:
                print(f"[{etiqueta}] ERROR SQL: {error}")
                canonica.rollback()
                raise
            finally:
                fuente.close()

            print(f"[{etiqueta}] {ruta}")
            print(
                f"  snapshots={stats['snapshots']} nuevos={stats['snapshots_nuevos']} "
                f"partidos={stats['partidos']} rescatados={stats['partidos_rescatados']}"
            )
            print(
                f"  capas_mercado={stats['capas_mercado']} ticks={stats['ticks']} "
                f"ticks_omitidos={stats['ticks_omitidos']} distribuciones={stats['distribuciones']}"
            )
            print(
                f"  causal_filas={stats['causal_filas']} "
                f"variables_32d={stats['variables_32d']}\n"
            )
            for clave in total:
                total[clave] += stats[clave]

        canonica.commit()
        print("-" * 78)
        print(
            f"TOTAL RESCATADO: ticks_momios={total['ticks']} "
            f"(omitidos={total['ticks_omitidos']}) | "
            f"variables_32d={total['variables_32d']} en {total['causal_filas']} partidos | "
            f"partidos_nuevos={total['partidos_rescatados']} | "
            f"capas_mercado={total['capas_mercado']} | "
            f"distribuciones={total['distribuciones']}"
        )
        print("-" * 78)
        return 0
    except Exception as error:
        canonica.rollback()
        print(f"[ERROR] Consolidación abortada: {type(error).__name__}: {error}")
        return 1
    finally:
        canonica.close()


if __name__ == "__main__":
    raise SystemExit(main())
