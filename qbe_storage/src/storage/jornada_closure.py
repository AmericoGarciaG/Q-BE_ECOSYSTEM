# -*- coding: utf-8 -*-
"""`[SPRINT-47]` Cierre de Jornada — transferencia de `odds_ticks` a la Bóveda Histórica.

Régimen: ``[DIRGEN-STRICT]``. Persistencia pura, sin red y sin matemática nueva:
la aritmética estructural (símplex vig-free, consenso) se delega al plano
canónico de `qbe_core`.

Contrato
--------
* **Detector.** Una jornada está cerrada cuando porta al menos un partido y
  *todos* sus partidos declaran estado concluido (``FINISHED`` ≡ ``FINALIZADO``).
* **Transferencia.** Al cerrarse, la secuencia completa de ``odds_ticks`` de esa
  jornada se copia a la bóveda histórica en ``historical_odds_qbe_live`` con
  ``origen = Q_BE_CAPTURA_PROPIA``. La tabla es **paralela**: jamás se tocan los
  momios de FootyStats de ``historical_matches``.
* **Ausencia declarada.** Si la jornada no tiene ticks (daemon caído), se
  registra ``SIN EVIDENCIA_PROPIA`` en ``jornada_closure_log`` y **no** se
  escribe una sola fila de cuota: cero imputación.
* **Idempotencia.** La clave primaria ``(match_id, casino, timestamp)`` y
  ``INSERT OR REPLACE`` hacen que re-ejecutar el cierre no duplique evidencia.
* **Brier propio.** ``brier_propio`` es el Brier 3N/3 (misma ley que
  `calcular_brier_multicategorico`) del consenso de los últimos ticks por
  partido, medido contra el marcador consumado. Sin marcador, el partido no
  entra al denominador.

Columnas de ``historical_odds_qbe_live``
----------------------------------------
``match_id``, ``casino``, ``timestamp``, ``odd_home``, ``odd_draw``,
``odd_away``, ``delta`` (variación de la cuota local contra el tick anterior de
la misma secuencia; ``0.0`` en el primero), más la trazabilidad ``jornada``,
``temporada``, ``tick_id``, ``origen``, ``origen_tick``, ``estado`` y
``cargado_utc``.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

__all__ = [
    "ESTADO_CERRADA",
    "ESTADO_SIN_EVIDENCIA_PROPIA",
    "ORIGEN_CAPTURA_PROPIA",
    "cerrar_jornada",
    "cerrar_jornadas_pendientes",
    "detectar_jornadas_cerradas",
    "ruta_historico_por_defecto",
    "ruta_viva_por_defecto",
]

ORIGEN_CAPTURA_PROPIA = "Q_BE_CAPTURA_PROPIA"
ESTADO_CERRADA = "CERRADA"
ESTADO_SIN_EVIDENCIA_PROPIA = "SIN EVIDENCIA_PROPIA"
TEMPORADA_NO_DECLARADA = "SIN TEMPORADA"

_ESTADOS_CONCLUIDOS = frozenset({"FINISHED", "FINALIZADO"})
_ECOSISTEMA = Path(__file__).resolve().parents[3]

DDL_CIERRE = """
CREATE TABLE IF NOT EXISTS historical_odds_qbe_live (
    match_id    TEXT    NOT NULL,
    casino      TEXT    NOT NULL,
    timestamp   TEXT    NOT NULL,
    odd_home    REAL    NOT NULL CHECK (odd_home > 1.0),
    odd_draw    REAL    NOT NULL CHECK (odd_draw > 1.0),
    odd_away    REAL    NOT NULL CHECK (odd_away > 1.0),
    delta       REAL,
    jornada     INTEGER NOT NULL,
    temporada   TEXT    NOT NULL,
    tick_id     INTEGER,
    origen      TEXT    NOT NULL DEFAULT 'Q_BE_CAPTURA_PROPIA',
    origen_tick TEXT,
    estado      TEXT    NOT NULL DEFAULT 'CERRADA',
    cargado_utc TEXT    NOT NULL,
    PRIMARY KEY (match_id, casino, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_hist_odds_qbe_jornada
    ON historical_odds_qbe_live (temporada, jornada, match_id);

CREATE TABLE IF NOT EXISTS jornada_closure_log (
    temporada    TEXT    NOT NULL,
    jornada      INTEGER NOT NULL,
    estado       TEXT    NOT NULL,
    ticks        INTEGER NOT NULL DEFAULT 0,
    partidos     INTEGER NOT NULL DEFAULT 0,
    casinos      INTEGER NOT NULL DEFAULT 0,
    brier_propio REAL,
    detalle      TEXT,
    cerrada_utc  TEXT    NOT NULL,
    PRIMARY KEY (temporada, jornada)
);
"""


# ── Rutas ─────────────────────────────────────────────────────────────────────
def ruta_viva_por_defecto() -> Path:
    """Bóveda viva (3NF) del ecosistema: `QBE_LIVE_DB` o `data/qbe_database.db`."""
    return Path(
        os.getenv("QBE_LIVE_DB") or os.getenv("OBS_LIVE_DB") or (_ECOSISTEMA / "data" / "qbe_database.db")
    ).resolve()


def ruta_historico_por_defecto() -> Path:
    """Bóveda histórica: `QBE_HISTORICO_DB` o `qbe_observatory/data/qbe_historico.db`."""
    return Path(
        os.getenv("QBE_HISTORICO_DB")
        or os.getenv("OBS_HISTORICO_DB")
        or (_ECOSISTEMA / "qbe_observatory" / "data" / "qbe_historico.db")
    ).resolve()


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _conectar_viva(ruta: Path) -> sqlite3.Connection:
    conexion = sqlite3.connect(f"file:{ruta.as_posix()}?mode=ro", uri=True, timeout=10.0)
    conexion.row_factory = sqlite3.Row
    return conexion


def _conectar_historico(ruta: Path) -> sqlite3.Connection:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    conexion = sqlite3.connect(ruta.as_posix(), timeout=15.0)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA journal_mode=WAL;")
    conexion.execute("PRAGMA foreign_keys=ON;")
    conexion.executescript(DDL_CIERRE)
    return conexion


# ── Utilidades de mercado ─────────────────────────────────────────────────────
def _simplex(odd_home: Any, odd_draw: Any, odd_away: Any) -> Optional[Tuple[float, float, float]]:
    """Probabilidades vig-free (Σ(1/o) normalizada); `None` si no es representable."""
    try:
        cuotas = [float(odd_home), float(odd_draw), float(odd_away)]
    except (TypeError, ValueError):
        return None
    if any(not math.isfinite(cuota) or cuota <= 1.0 for cuota in cuotas):
        return None
    inversas = [1.0 / cuota for cuota in cuotas]
    total = sum(inversas)
    if not math.isfinite(total) or total <= 0.0:
        return None
    return (inversas[0] / total, inversas[1] / total, inversas[2] / total)


def _one_hot(goles_local: int, goles_visitante: int) -> Tuple[float, float, float]:
    if goles_local > goles_visitante:
        return (1.0, 0.0, 0.0)
    if goles_local == goles_visitante:
        return (0.0, 1.0, 0.0)
    return (0.0, 0.0, 1.0)


def _brier_3n(probabilidades: Sequence[float], resultado: Sequence[float]) -> float:
    """Brier 3N/3 — la misma normalización de `calcular_brier_multicategorico`."""
    return sum((float(p) - float(y)) ** 2 for p, y in zip(probabilidades, resultado)) / 3.0


def _consenso_de(por_casino: Mapping[str, Sequence[float]]) -> Optional[Tuple[float, float, float]]:
    """Consenso equiponderado de los operadores con cuota (delegado a `qbe_core`)."""
    if not por_casino:
        return None
    from src.core.consensus import ConsensoInvalidoError, promediar_simplex

    try:
        return promediar_simplex(
            {casino: tuple(fila) for casino, fila in por_casino.items()},
            {casino: 1.0 for casino in por_casino},
        )
    except ConsensoInvalidoError:
        return None


def _brier_propio(
    ticks: Sequence[Mapping[str, Any]],
) -> Tuple[Optional[float], int]:
    """Brier de nuestra captura: último tick por partido/casino, consenso, marcador.

    Devuelve ``(brier, partidos_evaluados)``. Sin marcador consumado el partido
    se excluye del denominador (cero imputación).
    """
    ultimo: Dict[Tuple[str, str], Mapping[str, Any]] = {}
    marcadores: Dict[str, Tuple[int, int]] = {}
    for tick in ticks:
        clave = (str(tick["match_id"]), str(tick["casino"]))
        actual = ultimo.get(clave)
        if actual is None or (str(tick["timestamp"]), int(tick["tick_id"] or 0)) >= (
            str(actual["timestamp"]),
            int(actual["tick_id"] or 0),
        ):
            ultimo[clave] = tick
        if tick["score_home"] is not None and tick["score_away"] is not None:
            marcadores[str(tick["match_id"])] = (int(tick["score_home"]), int(tick["score_away"]))

    por_partido: Dict[str, Dict[str, Sequence[float]]] = {}
    for (match_id, casino), tick in ultimo.items():
        if match_id not in marcadores:
            continue
        simplex = _simplex(tick["odd_home"], tick["odd_draw"], tick["odd_away"])
        if simplex is not None:
            por_partido.setdefault(match_id, {})[casino] = simplex

    briers: List[float] = []
    for match_id, por_casino in por_partido.items():
        consenso = _consenso_de(por_casino)
        if consenso is None:
            continue
        briers.append(_brier_3n(consenso, _one_hot(*marcadores[match_id])))
    if not briers:
        return None, 0
    return round(sum(briers) / len(briers), 4), len(briers)


# ── Detector y transferencia ──────────────────────────────────────────────────
def detectar_jornadas_cerradas(conexion: sqlite3.Connection) -> List[int]:
    """Jornadas con al menos un partido y TODOS concluidos (``FINISHED`` ≡ ``FINALIZADO``)."""
    filas = conexion.execute(
        "SELECT matchday_num, COUNT(*) AS total, "
        "SUM(CASE WHEN UPPER(TRIM(COALESCE(status, ''))) IN ('FINISHED', 'FINALIZADO') "
        "THEN 1 ELSE 0 END) AS concluidos "
        "FROM matches WHERE matchday_num IS NOT NULL GROUP BY matchday_num"
    ).fetchall()
    cerradas = [
        int(fila[0])
        for fila in filas
        if int(fila[1]) > 0 and int(fila[2]) == int(fila[1])
    ]
    return sorted(cerradas)


def _temporada(conexion_viva: Optional[sqlite3.Connection], conexion_historica: sqlite3.Connection) -> str:
    """Temporada del cierre: `matches.season_id` normalizado o la última del archivo."""
    if conexion_viva is not None:
        try:
            fila = conexion_viva.execute(
                "SELECT season_id FROM matches WHERE season_id IS NOT NULL "
                "AND TRIM(season_id) <> '' ORDER BY matchday_num DESC LIMIT 1"
            ).fetchone()
        except sqlite3.Error:
            fila = None
        if fila and fila["season_id"]:
            texto = str(fila["season_id"]).upper()
            if texto.startswith("MEX_"):
                texto = texto[4:]
            for sufijo in ("_APERTURA", "_CLAUSURA"):
                if texto.endswith(sufijo):
                    texto = texto[: -len(sufijo)]
            if texto:
                return texto
    try:
        fila = conexion_historica.execute(
            "SELECT MAX(temporada) AS temporada FROM historical_matches"
        ).fetchone()
    except sqlite3.Error:
        fila = None
    return str(fila["temporada"]) if fila and fila["temporada"] else TEMPORADA_NO_DECLARADA


def _ticks_de_jornada(conexion: sqlite3.Connection, jornada: int) -> List[Mapping[str, Any]]:
    return conexion.execute(
        "SELECT t.match_id, t.casino_id AS casino, t.timestamp, t.tick_id, "
        "t.odd_home, t.odd_draw, t.odd_away, t.delta_odd, t.origen, "
        "m.score_home, m.score_away, m.matchday_num "
        "FROM odds_ticks t JOIN matches m ON m.id = t.match_id "
        "WHERE m.matchday_num = ? "
        "ORDER BY t.match_id ASC, t.timestamp ASC, t.tick_id ASC",
        (jornada,),
    ).fetchall()


def _delta(tick: Mapping[str, Any], anterior: Optional[float]) -> float:
    """Variación de la cuota local contra el tick anterior de la misma secuencia."""
    if anterior is None:
        return 0.0
    return round(float(tick["odd_home"]) - float(anterior), 4)


def _registrar_cierre(
    conexion: sqlite3.Connection,
    *,
    temporada: str,
    jornada: int,
    estado: str,
    ticks: int,
    partidos: int,
    casinos: int,
    brier_propio: Optional[float],
    detalle: Mapping[str, Any],
) -> None:
    conexion.execute(
        "INSERT OR REPLACE INTO jornada_closure_log "
        "(temporada, jornada, estado, ticks, partidos, casinos, brier_propio, detalle, cerrada_utc) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            temporada,
            int(jornada),
            estado,
            int(ticks),
            int(partidos),
            int(casinos),
            brier_propio,
            json.dumps(detalle, ensure_ascii=False, sort_keys=True),
            _utc_iso(),
        ),
    )


def cerrar_jornada(
    jornada: int,
    ruta_viva: Optional[Path] = None,
    ruta_historico: Optional[Path] = None,
    temporada: Optional[str] = None,
) -> Dict[str, Any]:
    """Cierra UNA jornada: transfiere su secuencia de ticks y sella el estado.

    Returns:
        Resumen del cierre (dict) con ``estado``, ``ticks``, ``partidos``,
        ``casinos``, ``brier_propio``, ``temporada`` y ``jornada``.

    Raises:
        FileNotFoundError: si la bóveda viva no existe.
        sqlite3.Error: si la escritura del archivo histórico falla (fail-loud).
    """
    ruta_viva = Path(ruta_viva or ruta_viva_por_defecto()).resolve()
    ruta_historico = Path(ruta_historico or ruta_historico_por_defecto()).resolve()
    if not ruta_viva.is_file():
        raise FileNotFoundError(f"Bóveda viva no disponible: {ruta_viva}")

    viva = _conectar_viva(ruta_viva)
    historica = _conectar_historico(ruta_historico)
    try:
        temporada_uso = temporada or _temporada(viva, historica)
        ticks = _ticks_de_jornada(viva, int(jornada))
        if not ticks:
            # Daemon caído o jornada sin captura: estado DECLARADO, cero filas.
            _registrar_cierre(
                historica,
                temporada=temporada_uso,
                jornada=int(jornada),
                estado=ESTADO_SIN_EVIDENCIA_PROPIA,
                ticks=0,
                partidos=0,
                casinos=0,
                brier_propio=None,
                detalle={"motivo": "Sin ticks en odds_ticks para la jornada"},
            )
            historica.commit()
            return {
                "jornada": int(jornada),
                "temporada": temporada_uso,
                "estado": ESTADO_SIN_EVIDENCIA_PROPIA,
                "ticks": 0,
                "partidos": 0,
                "casinos": 0,
                "brier_propio": None,
            }

        anterior: Dict[Tuple[str, str], float] = {}
        cargados = 0
        for tick in ticks:
            clave = (str(tick["match_id"]), str(tick["casino"]))
            # `delta` se mide sobre la secuencia transferida (no se hereda un
            # `delta_odd` rezagado de la captura): mismo criterio que `insertar_tick`.
            delta = _delta(tick, anterior.get(clave))
            anterior[clave] = float(tick["odd_home"])
            cursor = historica.execute(
                "INSERT OR REPLACE INTO historical_odds_qbe_live "
                "(match_id, casino, timestamp, odd_home, odd_draw, odd_away, delta, jornada, "
                "temporada, tick_id, origen, origen_tick, estado, cargado_utc) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    clave[0],
                    clave[1],
                    str(tick["timestamp"]),
                    float(tick["odd_home"]),
                    float(tick["odd_draw"]),
                    float(tick["odd_away"]),
                    float(delta),
                    int(jornada),
                    temporada_uso,
                    int(tick["tick_id"]) if tick["tick_id"] is not None else None,
                    ORIGEN_CAPTURA_PROPIA,
                    str(tick["origen"] or ""),
                    ESTADO_CERRADA,
                    _utc_iso(),
                ),
            )
            cargados += cursor.rowcount

        brier_propio, partidos = _brier_propio(ticks)
        casinos = len({str(tick["casino"]) for tick in ticks})
        _registrar_cierre(
            historica,
            temporada=temporada_uso,
            jornada=int(jornada),
            estado=ESTADO_CERRADA,
            ticks=len(ticks),
            partidos=partidos,
            casinos=casinos,
            brier_propio=brier_propio,
            detalle={
                "origen": ORIGEN_CAPTURA_PROPIA,
                "origenes_tick": sorted({str(tick["origen"] or "") for tick in ticks}),
                "primero": str(ticks[0]["timestamp"]),
                "ultimo": str(ticks[-1]["timestamp"]),
            },
        )
        historica.commit()
        return {
            "jornada": int(jornada),
            "temporada": temporada_uso,
            "estado": ESTADO_CERRADA,
            "ticks": len(ticks),
            "partidos": partidos,
            "casinos": casinos,
            "brier_propio": brier_propio,
            "filas_escritas": cargados,
        }
    finally:
        viva.close()
        historica.close()


def cerrar_jornadas_pendientes(
    ruta_viva: Optional[Path] = None,
    ruta_historico: Optional[Path] = None,
    temporada: Optional[str] = None,
    forzar: bool = False,
) -> List[Dict[str, Any]]:
    """Detecta las jornadas cerradas y transfiere sólo las que aún no lo están.

    ``forzar=True`` re-ejecuta también las ya cerradas (re-sellado idempotente).
    Una jornada sellada como ``SIN EVIDENCIA_PROPIA`` se re-intenta siempre: si
    el daemon volvió a capturar ticks, el cierre se corrige.
    """
    ruta_viva = Path(ruta_viva or ruta_viva_por_defecto()).resolve()
    ruta_historico = Path(ruta_historico or ruta_historico_por_defecto()).resolve()
    if not ruta_viva.is_file():
        raise FileNotFoundError(f"Bóveda viva no disponible: {ruta_viva}")

    viva = _conectar_viva(ruta_viva)
    historica = _conectar_historico(ruta_historico)
    try:
        temporada_uso = temporada or _temporada(viva, historica)
        jornadas = detectar_jornadas_cerradas(viva)
        pendientes: List[int] = []
        for jornada in jornadas:
            fila = historica.execute(
                "SELECT estado FROM jornada_closure_log WHERE temporada = ? AND jornada = ?",
                (temporada_uso, int(jornada)),
            ).fetchone()
            if forzar or fila is None or str(fila["estado"]) != ESTADO_CERRADA:
                pendientes.append(int(jornada))
    finally:
        viva.close()
        historica.close()

    return [
        cerrar_jornada(jornada, ruta_viva, ruta_historico, temporada_uso)
        for jornada in pendientes
    ]


def resumen_historico(ruta_historico: Optional[Path] = None) -> Dict[str, Any]:
    """Estado del cierre en la bóveda histórica (solo lectura, para consola/auditoría)."""
    ruta_historico = Path(ruta_historico or ruta_historico_por_defecto()).resolve()
    conexion = sqlite3.connect(f"file:{ruta_historico.as_posix()}?mode=ro", uri=True, timeout=10.0)
    conexion.row_factory = sqlite3.Row
    try:
        tablas = {
            str(fila[0])
            for fila in conexion.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        resumen: Dict[str, Any] = {
            "filas_propias": 0,
            "origenes": {},
            "jornadas": [],
            "footystats_filas": 0,
        }
        if "historical_odds_qbe_live" in tablas:
            resumen["filas_propias"] = int(
                conexion.execute("SELECT COUNT(*) FROM historical_odds_qbe_live").fetchone()[0]
            )
            for fila in conexion.execute(
                "SELECT origen, COUNT(*) FROM historical_odds_qbe_live GROUP BY origen"
            ).fetchall():
                resumen["origenes"][str(fila[0])] = int(fila[1])
        if "historical_matches" in tablas:
            resumen["footystats_filas"] = int(
                conexion.execute("SELECT COUNT(*) FROM historical_matches").fetchone()[0]
            )
        if "jornada_closure_log" in tablas:
            for fila in conexion.execute(
                "SELECT temporada, jornada, estado, ticks, partidos, brier_propio "
                "FROM jornada_closure_log ORDER BY jornada ASC"
            ).fetchall():
                resumen["jornadas"].append(
                    {
                        "temporada": str(fila["temporada"]),
                        "jornada": int(fila["jornada"]),
                        "estado": str(fila["estado"]),
                        "ticks": int(fila["ticks"] or 0),
                        "partidos": int(fila["partidos"] or 0),
                        "brier_propio": fila["brier_propio"],
                    }
                )
        return resumen
    finally:
        conexion.close()


# ── CLI ───────────────────────────────────────────────────────────────────────
def main(argv: Optional[Sequence[str]] = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(
        description="[SPRINT-47] Cierre de jornada: odds_ticks → historical_odds_qbe_live"
    )
    parser.add_argument("--jornada", type=int, default=None, help="Jornada a cerrar (omitir = todas las pendientes)")
    parser.add_argument("--temporada", type=str, default=None)
    parser.add_argument("--forzar", action="store_true", help="Re-sellar jornadas ya cerradas")
    parser.add_argument("--resumen", action="store_true", help="Sólo imprime el estado del cierre")
    parser.add_argument("--viva", type=str, default=None)
    parser.add_argument("--historico", type=str, default=None)
    args = parser.parse_args(argv)

    viva = Path(args.viva) if args.viva else ruta_viva_por_defecto()
    historico = Path(args.historico) if args.historico else ruta_historico_por_defecto()
    print("=" * 78)
    print("🔒 [JORNADA CLOSURE] Bóveda viva:", viva)
    print("🔒 [JORNADA CLOSURE] Bóveda histórica:", historico)
    print("=" * 78)

    if args.resumen:
        estado = resumen_historico(historico)
        print(f"📊 historical_odds_qbe_live: {estado['filas_propias']} filas · orígenes {estado['origenes']}")
        print(f"📊 historical_matches (FootyStats): {estado['footystats_filas']} filas (intactas)")
        for fila in estado["jornadas"]:
            marca = "✅" if fila["estado"] == ESTADO_CERRADA else "⚠️"
            print(
                f"   {marca} J{fila['jornada']:02d} · {fila['temporada']} · {fila['estado']} · "
                f"ticks={fila['ticks']} partidos={fila['partidos']} brier_propio={fila['brier_propio']}"
            )
        return 0

    if args.jornada is not None:
        resultados = [cerrar_jornada(args.jornada, viva, historico, args.temporada)]
    else:
        resultados = cerrar_jornadas_pendientes(viva, historico, args.temporada, args.forzar)

    if not resultados:
        print("   (sin jornadas pendientes de cierre)")
        return 0
    for resumen in resultados:
        marca = "✅" if resumen["estado"] == ESTADO_CERRADA else "⚠️"
        print(
            f"{marca} J{resumen['jornada']:02d} · {resumen['temporada']} · {resumen['estado']} · "
            f"ticks={resumen['ticks']} partidos={resumen['partidos']} casinos={resumen['casinos']} "
            f"brier_propio={resumen['brier_propio']}"
        )
    cerradas = sum(1 for r in resultados if r["estado"] == ESTADO_CERRADA)
    print("-" * 78)
    print(f"Total: {len(resultados)} jornadas procesadas · {cerradas} con captura propia")
    return 0


if __name__ == "__main__":
    sys.exit(main())
