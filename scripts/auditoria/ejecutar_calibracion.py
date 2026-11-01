# -*- coding: utf-8 -*-
"""[LN-QBE-147] Ejecución de la calibración empírica de la Temporada 2015-2016.

Régimen: ``[DIRGEN-STRICT]``. Cero datos sintéticos, Fail-Loud.

Lee la bóveda (``historical_match_causal_vars`` + ``historical_matches``), arma
el lote factual, delega la optimización en la función pura
``calibrar`` (``src.core.sovereign``) y emite el acta en
``data/reportes/calibracion_2015_2016.json``.

Uso::

    python scripts/auditoria/ejecutar_calibracion.py --temporada 2015-2016
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

RAIZ_PROYECTO = Path(__file__).resolve().parents[2]
for _ruta in (RAIZ_PROYECTO, RAIZ_PROYECTO / "qbe_core"):
    if str(_ruta) not in sys.path:
        sys.path.insert(0, str(_ruta))

from src.core.sovereign.calibrar_perturbacion import (  # noqa: E402
    CalibracionError,
    calibrar,
    brier_multiclase,
)
from src.core.sovereign.derivar_variables_causales import VARIABLES  # noqa: E402

DB_DEFECTO = RAIZ_PROYECTO / "qbe_observatory" / "data" / "qbe_historico.db"
REPORTE_DEFECTO = RAIZ_PROYECTO / "data" / "reportes" / "calibracion_2015_2016.json"

TABLA_CAUSAL = "historical_match_causal_vars"
TABLA_BOVEDA = "historical_matches"

_SQL_LOTE = f"""
SELECT c.match_id,
       m.home_team, m.away_team, m.home_goals, m.away_goals,
       m.odd_home, m.odd_draw, m.odd_away,
       c.*
  FROM {TABLA_CAUSAL} c
  JOIN {TABLA_BOVEDA} m ON m.match_id = c.match_id
 WHERE m.temporada = ?
 ORDER BY c.match_id
"""


class EjecucionError(RuntimeError):
    """[LN-QBE-147] La bóveda no permite ejecutar la calibración."""


def _vector(fila: sqlite3.Row) -> Dict[str, Dict[str, Optional[float]]]:
    return {
        variable: {
            "local": fila[f"{variable.lower()}_local"],
            "visita": fila[f"{variable.lower()}_visita"],
        }
        for variable in VARIABLES
    }


def _brier_mercado(
    odd_home: Optional[float],
    odd_draw: Optional[float],
    odd_away: Optional[float],
    goles_local: int,
    goles_visita: int,
) -> Optional[float]:
    """Brier de referencia del mercado (1/cuota normalizada), si hay cuotas."""
    if not odd_home or not odd_draw or not odd_away:
        return None
    if min(odd_home, odd_draw, odd_away) <= 1.0:
        return None
    inversas = (1.0 / odd_home, 1.0 / odd_draw, 1.0 / odd_away)
    suma = sum(inversas)
    return brier_multiclase(
        inversas[0] / suma, inversas[1] / suma, inversas[2] / suma,
        goles_local, goles_visita,
    )


def _temporada_canonica(valor: str) -> str:
    """`2015-2016` / `2015_2016` → `2015_2016` (llave de la bóveda)."""
    texto = str(valor).strip().replace("-", "_").replace("/", "_")
    if not re.fullmatch(r"\d{4}_\d{4}", texto):
        raise EjecucionError(
            f"[LN-QBE-147] Temporada no normalizable a YYYY_YYYY: {valor!r}"
        )
    return texto


def cargar_lote(
    db_path: str | Path, temporada: str
) -> Tuple[List[Dict[str, Any]], Dict[str, float], float, Optional[float]]:
    """Devuelve ``(partidos, medias, mu_liga, brier_mercado)``."""
    temporada_canonica = _temporada_canonica(temporada)
    conexion = sqlite3.connect(f"file:{Path(db_path).as_posix()}?mode=ro", uri=True)
    conexion.row_factory = sqlite3.Row
    try:
        filas = list(conexion.execute(_SQL_LOTE, (temporada_canonica,)))
    finally:
        conexion.close()

    if not filas:
        raise EjecucionError(
            f"[LN-QBE-147] No hay partidos con variables causales para {temporada}"
        )

    partidos: List[Dict[str, Any]] = []
    brieres_mercado: List[float] = []
    for fila in filas:
        if fila["home_goals"] is None or fila["away_goals"] is None:
            continue
        goles_local = int(fila["home_goals"])
        goles_visita = int(fila["away_goals"])
        partidos.append(
            {
                "match_id": fila["match_id"],
                "vector": _vector(fila),
                "goles_local": goles_local,
                "goles_visita": goles_visita,
            }
        )
        referencia = _brier_mercado(
            fila["odd_home"], fila["odd_draw"], fila["odd_away"],
            goles_local, goles_visita,
        )
        if referencia is not None:
            brieres_mercado.append(referencia)

    if not partidos:
        raise EjecucionError(f"[LN-QBE-147] Lote sin marcadores jugados en {temporada}")

    total_goles = sum(p["goles_local"] + p["goles_visita"] for p in partidos)
    mu_liga = total_goles / (2.0 * len(partidos))
    medias = {
        "V07": sum(
            float(p["vector"]["V07"]["local"] or 0.0) + float(p["vector"]["V07"]["visita"] or 0.0)
            for p in partidos
        )
        / (2.0 * len(partidos)),
        "V13": sum(
            float(p["vector"]["V13"]["local"] or 0.0) + float(p["vector"]["V13"]["visita"] or 0.0)
            for p in partidos
        )
        / (2.0 * len(partidos)),
    }
    brier_mercado = (sum(brieres_mercado) / len(brieres_mercado)) if brieres_mercado else None
    return partidos, medias, mu_liga, brier_mercado


def ejecutar(
    db_path: str | Path,
    temporada: str,
    *,
    pasos: int = 8,
    reporte: Optional[str | Path] = REPORTE_DEFECTO,
) -> Dict[str, Any]:
    """[LN-QBE-147] Ejecuta la calibración y (opcionalmente) emite el acta JSON."""
    partidos, medias, mu_liga, brier_mercado = cargar_lote(db_path, temporada)
    acta = calibrar(partidos, medias, mu_liga, pasos=pasos)
    acta.update(
        {
            "nodo": "[LN-QBE-147]",
            "temporada": temporada,
            "boveda": str(db_path),
            "ejecutado_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "brier_mercado": round(brier_mercado, 8) if brier_mercado is not None else None,
        }
    )
    if reporte is not None:
        ruta = Path(reporte)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(json.dumps(acta, ensure_ascii=False, indent=2), encoding="utf-8")
        acta["reporte"] = str(ruta)
    return acta


def _imprimir(acta: Dict[str, Any]) -> None:
    print(f"partidos calibrados : {acta['partidos']}")
    print(f"MU_LIGA             : {acta['mu_liga']}")
    print(f"medias V07 / V13    : {acta['medias']['V07']} / {acta['medias']['V13']}")
    print(f"Brier base          : {acta['brier_base']}")
    print(f"Brier optimizado    : {acta['brier_optimizado']}")
    print(f"delta               : {acta['delta']}  (mejora relativa {acta['mejora_relativa']:.2%})")
    if acta.get("brier_mercado") is not None:
        print(f"Brier mercado       : {acta['brier_mercado']}")
    print(f"pasos ejecutados    : {acta['pasos_ejecutados']}")
    print("top3 variables      :")
    for fila in acta["top3"]:
        print(
            f"  {fila['variable']}_{fila['lado']:<6} factor {fila['factor_final']:.4f} "
            f"| movimientos {fila['movimientos']} | Δ{fila['delta_total']:+.6f}"
        )


def main(argv: Optional[Sequence[str]] = None) -> int:
    analizador = argparse.ArgumentParser(
        prog="ejecutar_calibracion",
        description="[LN-QBE-147] Calibración empírica y perturbación de variables causales.",
    )
    analizador.add_argument("--db", default=str(DB_DEFECTO), help="ruta de qbe_historico.db")
    analizador.add_argument("--temporada", default="2015-2016", help="ej. 2015-2016")
    analizador.add_argument("--pasos", type=int, default=20, help="pasos de la búsqueda voraz")
    analizador.add_argument("--reporte-json", default=str(REPORTE_DEFECTO), help="acta de salida")
    argumentos = analizador.parse_args(argv)

    try:
        acta = ejecutar(
            argumentos.db,
            argumentos.temporada,
            pasos=argumentos.pasos,
            reporte=argumentos.reporte_json,
        )
    except (EjecucionError, CalibracionError, sqlite3.Error) as error:
        print(f"🔴 {error}", file=sys.stderr)
        return 1

    _imprimir(acta)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
