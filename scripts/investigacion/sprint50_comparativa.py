# -*- coding: utf-8 -*-
"""`[SPRINT-50]` Comparativa P' V1 vs P' V2 — Brier multiclase y Alpha de calibración.

Régimen ``[DIRGEN-STRICT]``. Sólo lectura sobre ``qbe_historico.db``.

Compara las dos tablas de distribuciones históricas sobre:
  1. el universo propio de cada motor;
  2. la **intersección** de ``match_id`` (misma muestra, comparación válida).

Uso::

    python scripts/investigacion/sprint50_comparativa.py
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

RAIZ_PROYECTO = Path(__file__).resolve().parents[2]
for _ruta in (RAIZ_PROYECTO, RAIZ_PROYECTO / "qbe_core"):
    if str(_ruta) not in sys.path:
        sys.path.insert(0, str(_ruta))

from scripts.auditoria.calcular_distribuciones_historicas import (  # noqa: E402
    TABLA_DESTINO,
    TABLA_DESTINO_V2,
    TABLA_DESTINO_V3,
    _metricas_brier,
)

DB = RAIZ_PROYECTO / "qbe_observatory" / "data" / "qbe_historico.db"


def _leer(conexion: sqlite3.Connection, tabla: str) -> Dict[str, Tuple[Any, ...]]:
    sql = f"""
        SELECT d.match_id, d.p_local, d.p_empate, d.p_visitante,
               m.home_goals, m.away_goals, m.odd_home, m.odd_draw, m.odd_away, m.temporada
          FROM {tabla} d
          JOIN historical_matches m ON m.match_id = d.match_id
    """
    return {
        str(fila[0]): (
            float(fila[1]), float(fila[2]), float(fila[3]),
            fila[4], fila[5], fila[6], fila[7], fila[8], str(fila[9]),
        )
        for fila in conexion.execute(sql)
    }


def _tabla(titulo: str, filas: List[Tuple[str, Any, Any, Any, int]]) -> None:
    print()
    print(titulo)
    print("-" * 84)
    print(f"{'Motor':<10}{'N':>7}{'Brier QBE':>13}{'Brier mercado':>16}{'Alpha %':>11}{'Delta vs V1':>14}")
    referencia = next((f[2] for f in filas if f[0] == "V1"), None)
    for nombre, brier, mercado, alpha, n in filas:
        delta = "—"
        if referencia is not None and brier is not None and nombre != "V1":
            delta = f"{(brier - referencia):+.6f}"
        print(
            f"{nombre:<10}{n:>7}{_fmt(brier):>13}{_fmt(mercado):>16}{_fmt(alpha, 2):>11}{delta:>14}"
        )


def _fmt(valor: Any, decimales: int = 6) -> str:
    if valor is None:
        return "—"
    return f"{float(valor):.{decimales}f}"


def main() -> int:
    if not DB.is_file():
        print(f"🔴 Bóveda inexistente: {DB}", file=sys.stderr)
        return 1
    conexion = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    try:
        tablas = {}
        for etiqueta, tabla in (("V1", TABLA_DESTINO), ("V2", TABLA_DESTINO_V2), ("V3", TABLA_DESTINO_V3)):
            existe = conexion.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (tabla,)
            ).fetchone()
            if existe:
                tablas[etiqueta] = _leer(conexion, tabla)
    finally:
        conexion.close()

    if "V1" not in tablas:
        print("🔴 Falta la tabla V1 (baseline).", file=sys.stderr)
        return 1

    comunes = sorted(set.intersection(*(set(filas) for filas in tablas.values())))
    propias = {etiqueta: _metricas_brier([fila[:8] for fila in filas.values()]) for etiqueta, filas in tablas.items()}
    misma = {
        etiqueta: _metricas_brier([filas[k][:8] for k in comunes]) for etiqueta, filas in tablas.items()
    }

    print("=" * 84)
    print("COMPARATIVA P' V1 vs V2 vs V3 — [LN-QBE-150] · v13 · v14-GSL3D · v15-GSL3D-β")
    print("=" * 84)
    for etiqueta, filas in tablas.items():
        print(f"Partidos en {etiqueta}: {len(filas)}", end="   ")
    print(f"\nIntersección: {len(comunes)}")

    _tabla(
        "A) Universo propio de cada motor (N distinto: informa, no compara)",
        [
            (etiqueta, m["brier_qbe"], m["brier_mercado"], m["alpha_pct"], m["n_qbe"])
            for etiqueta, m in propias.items()
        ],
    )
    _tabla(
        "B) MISMA MUESTRA (intersección de match_id con marcador y cuota)",
        [
            (etiqueta, m["brier_qbe_misma_muestra"], m["brier_mercado"], m["alpha_pct"], m["n_mercado"])
            for etiqueta, m in misma.items()
        ],
    )

    referencia = misma["V1"]["brier_qbe_misma_muestra"]
    print()
    for etiqueta, m in misma.items():
        if etiqueta == "V1" or referencia is None or m["brier_qbe_misma_muestra"] is None:
            continue
        delta = m["brier_qbe_misma_muestra"] - referencia
        print(
            f"Δ Brier {etiqueta} − V1: {delta:+.6f} ({delta / referencia * 100:+.2f} %)   "
            f"Δ Alpha: {m['alpha_pct'] - misma['V1']['alpha_pct']:+.2f} pp"
        )
    print()
    print("Lectura: Δ < 0 ⇒ el motor calibra mejor que V1. Δ > 0 ⇒ calibra peor.")

    print()
    print("C) BRIER POR TEMPORADA (intersección)")
    print("-" * 84)
    cabecera = f"{'Temporada':<14}{'N':>6}" + "".join(f"{e:>12}" for e in tablas) + f"{'V3-V1':>12}"
    print(cabecera)
    for temporada in sorted({tablas["V1"][k][8] for k in comunes}):
        identificadores = [k for k in comunes if tablas["V1"][k][8] == temporada]
        valores = {}
        for etiqueta, filas in tablas.items():
            valores[etiqueta] = _metricas_brier([filas[k][:8] for k in identificadores])["brier_qbe"]
        if any(valor is None for valor in valores.values()):
            continue
        linea = f"{temporada:<14}{len(identificadores):>6}" + "".join(
            f"{valores[e]:>12.6f}" for e in tablas
        )
        linea += f"{(valores.get('V3', float('nan')) - valores['V1']):>+12.6f}"
        print(linea)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
