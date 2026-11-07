# -*- coding: utf-8 -*-
"""`[SPRINT-51]` Exportador del dataset maestro del Meta-Router para Manus.

Régimen ``[DIRGEN-STRICT]``. Este módulo es el ÚNICO punto de contacto con la bóveda
histórica y lo hace en **solo lectura estricta** (``mode=ro`` + ``PRAGMA query_only=ON``):
cero escrituras, cero DDL, cero imputación de cuotas ni de distribuciones.

Contrato IPO
------------
Entrada: ``qbe_observatorio/data/qbe_historico.db``.
Salida : Parquet tipado + diccionario de datos + folds Rolling-Origin.

La matemática NO se reimplementa: el de-vig se delega en ``desmarginar_shin``
(``[LN-QBE-151]``), el orden fiduciario en ``resolver_orden_fiduciario_con_indiferencia``
(``[LN-QBE-124]``) y el Brier 3N en ``brier_multiclase`` (``[LN-QBE-147]``, dividido entre 3
según ``[LN-QBE-100]``).

Advertencia de universo (ver ``DIRGEN_VARIANCE_REQUEST_SPRINT51_MANUS.md``)
--------------------------------------------------------------------------
La cifra ``2,726`` del expediente NO es reproducible con los cuatro filtros declarados
sobre la bóveda histórica: es el total de la vista ``/desempeno`` en modo ``Todas``, que
mezcla el corpus histórico (2,592) con la temporada viva (134) y deja 47 partidos sin
vector de mercado. El decreto ``VAR-2026-SPRINT51-MANUS`` ratificó el universo fáctico de
**2,667 filas** (histórico íntegro, cero NaN en variables críticas). ``--esperado-filas``
sigue siendo un candado explícito contra desviaciones silenciosas.

Uso
---
    python scripts/investigacion/exportar_dataset_manus.py --diagnostico
    python scripts/investigacion/exportar_dataset_manus.py \\
        --universo pre_holdout --esperado-filas 2569 --permitir-desviacion \\
        --salida .tmp_run/provisional_2569 --nombre-parquet dataset_meta_router_2569.parquet
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

RAIZ_PROYECTO = Path(__file__).resolve().parents[2]
for _ruta in (RAIZ_PROYECTO, RAIZ_PROYECTO / "qbe_core"):
    if str(_ruta) not in sys.path:
        sys.path.insert(0, str(_ruta))

#: Dependencia local declarada (``.vendor``) cuando el entorno no trae ``pyarrow``.
try:  # pragma: no cover - depende del entorno de ejecución
    import pyarrow as pa
    import pyarrow.parquet as pq
except ModuleNotFoundError:  # pragma: no cover
    _VENDOR = RAIZ_PROYECTO / ".vendor"
    if _VENDOR.is_dir() and str(_VENDOR) not in sys.path:
        sys.path.insert(0, str(_VENDOR))
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise ModuleNotFoundError(
            "pyarrow es imprescindible para materializar el Parquet: instálelo con "
            "`pip install pyarrow` o déjelo en `.vendor/`."
        ) from exc

from src.core.consensus import desmarginar_shin  # noqa: E402
from src.core.contracts.portfolio_math import (  # noqa: E402
    resolver_orden_fiduciario_con_indiferencia,
)
from src.core.sovereign.calibrar_perturbacion import brier_multiclase  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    try:  # consola Windows cp1252
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, OSError, ValueError):  # pragma: no cover
        pass

__all__ = [
    "BLOQUE_JORNADA",
    "DB_HISTORICO",
    "DIR_SALIDA",
    "FILAS_ESPERADAS",
    "ORDEN_COLUMNAS",
    "TEMPORADAS_CORPUS",
    "TEMPORADAS_EXCLUIDAS",
    "UniversoNoConforme",
    "construir_dataset",
    "construir_diccionario",
    "construir_folds",
    "verificar_dataset",
]


# ── Rutas y constantes legisladas ───────────────────────────────────────────────────────────
DB_HISTORICO = RAIZ_PROYECTO / "qbe_observatory" / "data" / "qbe_historico.db"
DIR_SALIDA = RAIZ_PROYECTO / "data" / "investigacion"
NOMBRE_PARQUET = "dataset_meta_router_2667.parquet"
NOMBRE_DICCIONARIO = "DATA_DICTIONARY_MANUS.json"
NOMBRE_FOLDS = "folds_rolling_origin.json"

#: Cifra mandatada por el expediente (candado, no verdad de la bóveda).
#: `VAR-2026-SPRINT51-MANUS` ratificó el universo fáctico de 2,667 filas.
FILAS_ESPERADAS = 2667

#: Overround comercial admisible: expulsa la terna corrupta ``(1.5, 3.0, 1.5)``.
SOBRE_MARGEN_MIN = 0.85
SOBRE_MARGEN_MAX = 1.30
#: Tolerancia de conservación del símplex.
TOLERANCIA_SIMPLEX = 1e-6
#: Bloque cronológico declarado (``historical_matches`` no porta número de jornada).
BLOQUE_JORNADA = 9

#: Temporadas del protocolo de folds (holdout final incluido).
TEMPORADAS_CORPUS: Tuple[str, ...] = (
    "2015_2016",
    "2018_2019",
    "2019_2020",
    "2020_2021",
    "2021_2022",
    "2022_2023",
    "2023_2024",
    "2024_2025",
    "2025_2026",
)
#: Sin vector causal FotMob (``KDB.md`` §5.5): se declaran, jamás se imputan.
TEMPORADAS_EXCLUIDAS: Tuple[str, ...] = ("2016_2017", "2017_2018")
TEMPORADA_ACTUAL = "2026_2027"

_MAPA_VERTICE: Dict[str, str] = {"LOCAL": "1", "EMPATE": "X", "VISITANTE": "2"}

_SQL_UNIVERSO = """
SELECT m.match_id, m.temporada, m.fecha_utc, m.home_team, m.away_team,
       m.home_goals, m.away_goals,
       m.odd_home, m.odd_draw, m.odd_away,
       d.p_local, d.p_empate, d.p_visitante,
       d.lambda_home, d.lambda_away, d.delta_epist,
       v.v29_local, v.v30_local
  FROM historical_matches m
  INNER JOIN historical_sovereign_distributions d ON d.match_id = m.match_id
  LEFT JOIN historical_match_causal_vars v ON v.match_id = m.match_id
 WHERE m.home_goals IS NOT NULL
   AND m.away_goals IS NOT NULL
 ORDER BY m.temporada ASC, m.fecha_utc ASC, m.match_id ASC
"""


class UniversoNoConforme(RuntimeError):
    """El censo de la bóveda no satisface el contrato del expediente."""


# ── Lectura estricta de la bóveda ──────────────────────────────────────────────────────────
def _conectar() -> sqlite3.Connection:
    """Abre la bóveda en solo lectura estricta."""
    if not DB_HISTORICO.is_file():
        raise UniversoNoConforme(f"Bóveda inexistente: {DB_HISTORICO}")
    conexion = sqlite3.connect(f"file:{DB_HISTORICO.as_posix()}?mode=ro", uri=True)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA query_only = ON")
    return conexion


def _leer_filas() -> List[Dict[str, Any]]:
    conexion = _conectar()
    try:
        return [dict(fila) for fila in conexion.execute(_SQL_UNIVERSO)]
    finally:
        conexion.close()


def _sobre_margen(cuotas: Sequence[float]) -> float:
    return math.fsum(1.0 / float(cuota) for cuota in cuotas)


def censar_universo(
    filas: Sequence[Dict[str, Any]], universo: str
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Aplica los filtros del expediente y devuelve ``(universo, censo)``.

    ``universo``:
      * ``pre_holdout`` — temporadas del protocolo (excluye la temporada en curso);
      * ``historico``   — todas las temporadas con P′ de la bóveda (incluye 2026_2027).
    """
    permitidas: Optional[set[str]] = None
    if universo == "pre_holdout":
        permitidas = set(TEMPORADAS_CORPUS)
    elif universo != "historico":
        raise ValueError(f"Universo no reconocido: {universo!r}.")

    censo: Dict[str, Any] = {
        "universo": universo,
        "candidatos": len(filas),
        "fuera_temporada": 0,
        "sin_cuotas": 0,
        "overround_fuera": 0,
        "shin_fallido": 0,
        "aceptados": 0,
        "por_temporada": {},
        "overround_min": math.inf,
        "overround_max": -math.inf,
    }
    aceptados: List[Dict[str, Any]] = []
    for fila in filas:
        temporada = str(fila["temporada"])
        if permitidas is not None and temporada not in permitidas:
            censo["fuera_temporada"] += 1
            continue
        cuotas = (fila["odd_home"], fila["odd_draw"], fila["odd_away"])
        if any(cuota is None for cuota in cuotas):
            censo["sin_cuotas"] += 1
            continue
        sobre = _sobre_margen(cuotas)
        if not (SOBRE_MARGEN_MIN <= sobre <= SOBRE_MARGEN_MAX):
            censo["overround_fuera"] += 1
            continue
        try:
            shin = desmarginar_shin(tuple(float(cuota) for cuota in cuotas))
        except Exception:  # noqa: BLE001 - la aduana declara, no repara
            censo["shin_fallido"] += 1
            continue
        aceptados.append({**fila, "_shin": shin, "_sobre": sobre})
        censo["por_temporada"][temporada] = censo["por_temporada"].get(temporada, 0) + 1
        censo["overround_min"] = min(censo["overround_min"], sobre)
        censo["overround_max"] = max(censo["overround_max"], sobre)

    censo["aceptados"] = len(aceptados)
    if not aceptados:
        raise UniversoNoConforme("Universo vacío: revisar filtros y bóveda.")
    return aceptados, censo


# ── Derivación de columnas ─────────────────────────────────────────────────────────────────
def _resultado(goles_local: int, goles_visita: int) -> str:
    if goles_local > goles_visita:
        return "1"
    if goles_local < goles_visita:
        return "2"
    return "X"


def _entropia(probabilidades: Iterable[float]) -> float:
    terminos = (p * math.log(p) for p in probabilidades if p > 0.0)
    return -math.fsum(terminos)


def _orden_vertices(
    p1: float, pX: float, p2: float
) -> Tuple[float, float, float, str, str, str]:
    """Orden fiduciario canónico (``[LN-QBE-124]``) traducido a ``'1'/'X'/'2'``.

    ``delta_alt=0.0`` ⇒ orden aritmético estricto con desempate estable 1·X·2; la banda
    de indiferencia del despliegue no se aplica porque el Meta-Router no la legisla.
    """
    orden = resolver_orden_fiduciario_con_indiferencia(p1, pX, p2, delta_alt=0.0)
    return (
        float(orden["p_max_val"]),
        float(orden["p_mid_val"]),
        float(orden["p_low_val"]),
        _MAPA_VERTICE[orden["r_max"]],
        _MAPA_VERTICE[orden["r_mid"]],
        _MAPA_VERTICE[orden["r_low"]],
    )


def construir_dataset(
    aceptados: Sequence[Dict[str, Any]], universo: str = "pre_holdout"
) -> List[Dict[str, Any]]:
    """Materializa las 53 columnas tipadas del contrato, en orden cronológico."""
    # Bloque de 9 partidos por temporada (reloj ascendente, match_id como desempate).
    bloques: Dict[str, int] = {}
    ordenados = sorted(
        aceptados,
        key=lambda f: (str(f["temporada"]), str(f["fecha_utc"]), str(f["match_id"])),
    )
    for indice, fila in enumerate(ordenados):
        temporada = str(fila["temporada"])
        posicion = bloques.get(temporada, 0)
        fila["_jornada_bloque"] = posicion // BLOQUE_JORNADA + 1
        bloques[temporada] = posicion + 1

    salida: List[Dict[str, Any]] = []
    for fila in ordenados:
        goles_local = int(fila["home_goals"])
        goles_visita = int(fila["away_goals"])
        resultado = _resultado(goles_local, goles_visita)

        p1, pX, p2 = float(fila["p_local"]), float(fila["p_empate"]), float(fila["p_visitante"])
        shin = fila["_shin"]
        q1, qX, q2 = float(shin.p_local), float(shin.p_empate), float(shin.p_visitante)
        sobre = float(fila["_sobre"])

        p_max, p_mid, p_low, vq_max, vq_mid, vq_low = _orden_vertices(p1, pX, p2)
        m_max, m_mid, m_low, vm_max, vm_mid, vm_low = _orden_vertices(q1, qX, q2)

        brier_qbe = brier_multiclase(p1, pX, p2, goles_local, goles_visita) / 3.0
        brier_mkt = brier_multiclase(q1, qX, q2, goles_local, goles_visita) / 3.0

        salida.append(
            {
                "match_id": str(fila["match_id"]),
                "temporada": str(fila["temporada"]),
                "fecha_utc": str(fila["fecha_utc"]),
                "home_team": str(fila["home_team"]),
                "away_team": str(fila["away_team"]),
                "jornada_bloque": int(fila["_jornada_bloque"]),
                "home_goals": goles_local,
                "away_goals": goles_visita,
                "resultado_real": resultado,
                "p_qbe_1": p1,
                "p_qbe_X": pX,
                "p_qbe_2": p2,
                "p_max_val": p_max,
                "p_mid_val": p_mid,
                "p_low_val": p_low,
                "vertice_qbe_max": vq_max,
                "vertice_qbe_mid": vq_mid,
                "vertice_qbe_low": vq_low,
                "lambda_home": float(fila["lambda_home"]),
                "lambda_away": float(fila["lambda_away"]),
                "delta_epist": float(fila["delta_epist"]),
                "odd_home": float(fila["odd_home"]),
                "odd_draw": float(fila["odd_draw"]),
                "odd_away": float(fila["odd_away"]),
                "overround_S": sobre,
                "q_shin_1": q1,
                "q_shin_X": qX,
                "q_shin_2": q2,
                "shin_z": float(shin.z_insider),
                "q_prop_1": (1.0 / float(fila["odd_home"])) / sobre,
                "q_prop_X": (1.0 / float(fila["odd_draw"])) / sobre,
                "q_prop_2": (1.0 / float(fila["odd_away"])) / sobre,
                "mkt_max_val": m_max,
                "mkt_mid_val": m_mid,
                "mkt_low_val": m_low,
                "vertice_mkt_max": vm_max,
                "vertice_mkt_mid": vm_mid,
                "vertice_mkt_low": vm_low,
                "tvd_qbe_vs_shin": 0.5
                * math.fsum(abs(a - b) for a, b in ((p1, q1), (pX, qX), (p2, q2))),
                "gap_max": p_max - m_max,
                "discrepancia_favorito": vq_max != vm_max,
                "entropia_shannon_qbe": _entropia((p1, pX, p2)),
                "entropia_shannon_mkt": _entropia((q1, qX, q2)),
                "delta_alt_metros": None if fila["v29_local"] is None else float(fila["v29_local"]),
                "delta_descanso_dias": None if fila["v30_local"] is None else float(fila["v30_local"]),
                "brier_qbe_3n": brier_qbe,
                "brier_mkt_3n": brier_mkt,
                "delta_brier": brier_mkt - brier_qbe,
                "acierto_pmax_qbe": int(vq_max == resultado),
                "acierto_pmid_qbe": int(vq_mid == resultado),
                "acierto_cobertura_qbe": int(resultado in (vq_max, vq_mid)),
                "acierto_pmax_mkt": int(vm_max == resultado),
                "acierto_cobertura_mkt": int(resultado in (vm_max, vm_mid)),
            }
        )
    return salida


ORDEN_COLUMNAS: Tuple[str, ...] = (
    "match_id", "temporada", "fecha_utc", "home_team", "away_team", "jornada_bloque",
    "home_goals", "away_goals", "resultado_real",
    "p_qbe_1", "p_qbe_X", "p_qbe_2",
    "p_max_val", "p_mid_val", "p_low_val",
    "vertice_qbe_max", "vertice_qbe_mid", "vertice_qbe_low",
    "lambda_home", "lambda_away", "delta_epist",
    "odd_home", "odd_draw", "odd_away", "overround_S",
    "q_shin_1", "q_shin_X", "q_shin_2", "shin_z",
    "q_prop_1", "q_prop_X", "q_prop_2",
    "mkt_max_val", "mkt_mid_val", "mkt_low_val",
    "vertice_mkt_max", "vertice_mkt_mid", "vertice_mkt_low",
    "tvd_qbe_vs_shin", "gap_max", "discrepancia_favorito",
    "entropia_shannon_qbe", "entropia_shannon_mkt",
    "delta_alt_metros", "delta_descanso_dias",
    "brier_qbe_3n", "brier_mkt_3n", "delta_brier",
    "acierto_pmax_qbe", "acierto_pmid_qbe", "acierto_cobertura_qbe",
    "acierto_pmax_mkt", "acierto_cobertura_mkt",
)

ESQUEMA = pa.schema(
    [
        ("match_id", pa.string()),
        ("temporada", pa.string()),
        ("fecha_utc", pa.string()),
        ("home_team", pa.string()),
        ("away_team", pa.string()),
        ("jornada_bloque", pa.int64()),
        ("home_goals", pa.int64()),
        ("away_goals", pa.int64()),
        ("resultado_real", pa.string()),
        ("p_qbe_1", pa.float64()),
        ("p_qbe_X", pa.float64()),
        ("p_qbe_2", pa.float64()),
        ("p_max_val", pa.float64()),
        ("p_mid_val", pa.float64()),
        ("p_low_val", pa.float64()),
        ("vertice_qbe_max", pa.string()),
        ("vertice_qbe_mid", pa.string()),
        ("vertice_qbe_low", pa.string()),
        ("lambda_home", pa.float64()),
        ("lambda_away", pa.float64()),
        ("delta_epist", pa.float64()),
        ("odd_home", pa.float64()),
        ("odd_draw", pa.float64()),
        ("odd_away", pa.float64()),
        ("overround_S", pa.float64()),
        ("q_shin_1", pa.float64()),
        ("q_shin_X", pa.float64()),
        ("q_shin_2", pa.float64()),
        ("shin_z", pa.float64()),
        ("q_prop_1", pa.float64()),
        ("q_prop_X", pa.float64()),
        ("q_prop_2", pa.float64()),
        ("mkt_max_val", pa.float64()),
        ("mkt_mid_val", pa.float64()),
        ("mkt_low_val", pa.float64()),
        ("vertice_mkt_max", pa.string()),
        ("vertice_mkt_mid", pa.string()),
        ("vertice_mkt_low", pa.string()),
        ("tvd_qbe_vs_shin", pa.float64()),
        ("gap_max", pa.float64()),
        ("discrepancia_favorito", pa.bool_()),
        ("entropia_shannon_qbe", pa.float64()),
        ("entropia_shannon_mkt", pa.float64()),
        ("delta_alt_metros", pa.float64()),
        ("delta_descanso_dias", pa.float64()),
        ("brier_qbe_3n", pa.float64()),
        ("brier_mkt_3n", pa.float64()),
        ("delta_brier", pa.float64()),
        ("acierto_pmax_qbe", pa.int64()),
        ("acierto_pmid_qbe", pa.int64()),
        ("acierto_cobertura_qbe", pa.int64()),
        ("acierto_pmax_mkt", pa.int64()),
        ("acierto_cobertura_mkt", pa.int64()),
    ]
)


# ── Artefactos auxiliares ─────────────────────────────────────────────────────────────────
def construir_folds(
    datos: Optional[Sequence[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Protocolo Rolling-Origin sellado (5 folds, holdout 2025_2026).

    ``2026_2027`` no entra en ningún train/val: el decreto
    ``VAR-2026-SPRINT51-MANUS`` lo clasifica como Conjunto de Estrés Post-Holdout
    (Out-of-Distribution Test).
    """
    acumuladas = ["2015_2016", "2018_2019", "2019_2020"]
    folds: List[Dict[str, Any]] = []
    for numero, validacion in enumerate(
        ("2020_2021", "2021_2022", "2022_2023", "2023_2024", "2024_2025"), start=1
    ):
        folds.append(
            {
                "fold_id": numero,
                "train_temporadas": list(acumuladas),
                "val_temporada": validacion,
            }
        )
        acumuladas.append(validacion)
    estres = sum(
        1 for fila in (datos or ()) if str(fila["temporada"]) == TEMPORADA_ACTUAL
    )
    return {
        "protocolo": "Rolling-Origin Temporal Cross-Validation",
        "holdout_final_sellado": "2025_2026",
        "folds": folds,
        "temporadas_excluidas": list(TEMPORADAS_EXCLUIDAS),
        "conjunto_estres_post_holdout": {
            "temporada": TEMPORADA_ACTUAL,
            "n_partidos": estres,
            "rol": "Out-of-Distribution Test",
            "nota": (
                "Partidos concluidos de 2026_2027. No entran en ningún train/val; "
                "se reservan como estrés post-holdout, sin contaminar el holdout sellado."
            ),
        },
        "nota": (
            "2016_2017 y 2017_2018 se excluyen por carecer de vector causal FotMob "
            "(KDB.md §5.5). El holdout 2025_2026 no entra en ningún train."
        ),
    }


def construir_diccionario(datos: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Diccionario de datos estructurado (una entrada por columna)."""
    filas = len(datos)
    temporadas = sorted({str(fila["temporada"]) for fila in datos})
    nulos = {
        columna: sum(1 for fila in datos if fila[columna] is None)
        for columna in ORDEN_COLUMNAS
    }
    columnas: Dict[str, Dict[str, Any]] = {
        "match_id": {
            "descripcion": "Clave primaria del partido en la bóveda histórica.",
            "tipo": "string",
            "dominio": "identificador estable (fs_<temporada>_z<id>)",
            "origen_tabla": "historical_matches.match_id",
            "disponible_prepartido": True,
        },
        "temporada": {
            "descripcion": "Temporada liguera en formato año_inicio_año_fin.",
            "tipo": "string",
            "dominio": temporadas,
            "origen_tabla": "historical_matches.temporada",
            "disponible_prepartido": True,
        },
        "fecha_utc": {
            "descripcion": "Instante de kickoff en ISO-8601 UTC.",
            "tipo": "string",
            "dominio": "ISO-8601 (YYYY-MM-DDTHH:MM:SSZ)",
            "origen_tabla": "historical_matches.fecha_utc",
            "disponible_prepartido": True,
        },
        "home_team": {
            "descripcion": "Nombre del club local.",
            "tipo": "string",
            "dominio": "nombre canónico de club",
            "origen_tabla": "historical_matches.home_team",
            "disponible_prepartido": True,
        },
        "away_team": {
            "descripcion": "Nombre del club visitante.",
            "tipo": "string",
            "dominio": "nombre canónico de club",
            "origen_tabla": "historical_matches.away_team",
            "disponible_prepartido": True,
        },
        "jornada_bloque": {
            "descripcion": "Bloque cronológico declarado de 9 partidos dentro de la temporada.",
            "tipo": "int",
            "dominio": [1, 40],
            "origen_tabla": "derivado: índice_orden(fecha_utc, match_id) // 9 + 1 por temporada",
            "disponible_prepartido": True,
        },
        "home_goals": {
            "descripcion": "Goles del local (ground truth).",
            "tipo": "int",
            "dominio": [0, 20],
            "origen_tabla": "historical_matches.home_goals",
            "disponible_prepartido": False,
        },
        "away_goals": {
            "descripcion": "Goles del visitante (ground truth).",
            "tipo": "int",
            "dominio": [0, 20],
            "origen_tabla": "historical_matches.away_goals",
            "disponible_prepartido": False,
        },
        "resultado_real": {
            "descripcion": "Desenlace 1X2 observado.",
            "tipo": "string",
            "dominio": ["1", "X", "2"],
            "origen_tabla": "derivado de home_goals vs away_goals",
            "disponible_prepartido": False,
        },
        "p_qbe_1": {
            "descripcion": "Probabilidad soberana Q-BE de victoria local (P′ del motor).",
            "tipo": "float",
            "dominio": [0.0, 1.0],
            "origen_tabla": "historical_sovereign_distributions.p_local",
            "disponible_prepartido": True,
        },
        "p_qbe_X": {
            "descripcion": "Probabilidad soberana Q-BE de empate.",
            "tipo": "float",
            "dominio": [0.0, 1.0],
            "origen_tabla": "historical_sovereign_distributions.p_empate",
            "disponible_prepartido": True,
        },
        "p_qbe_2": {
            "descripcion": "Probabilidad soberana Q-BE de victoria visitante.",
            "tipo": "float",
            "dominio": [0.0, 1.0],
            "origen_tabla": "historical_sovereign_distributions.p_visitante",
            "disponible_prepartido": True,
        },
        "p_max_val": {
            "descripcion": "Mayor probabilidad del vector Q-BE.",
            "tipo": "float",
            "dominio": [0.0, 1.0],
            "origen_tabla": "derivado: orden fiduciario LN-QBE-124 sobre p_qbe_*",
            "disponible_prepartido": True,
        },
        "p_mid_val": {
            "descripcion": "Segunda probabilidad del vector Q-BE.",
            "tipo": "float",
            "dominio": [0.0, 1.0],
            "origen_tabla": "derivado: orden fiduciario LN-QBE-124 sobre p_qbe_*",
            "disponible_prepartido": True,
        },
        "p_low_val": {
            "descripcion": "Menor probabilidad del vector Q-BE.",
            "tipo": "float",
            "dominio": [0.0, 1.0],
            "origen_tabla": "derivado: orden fiduciario LN-QBE-124 sobre p_qbe_*",
            "disponible_prepartido": True,
        },
        "vertice_qbe_max": {
            "descripcion": "Desenlace que ocupa P_max en el vector Q-BE.",
            "tipo": "string",
            "dominio": ["1", "X", "2"],
            "origen_tabla": "derivado: vértice de p_max_val",
            "disponible_prepartido": True,
        },
        "vertice_qbe_mid": {
            "descripcion": "Desenlace que ocupa P_mid en el vector Q-BE.",
            "tipo": "string",
            "dominio": ["1", "X", "2"],
            "origen_tabla": "derivado: vértice de p_mid_val",
            "disponible_prepartido": True,
        },
        "vertice_qbe_low": {
            "descripcion": "Desenlace que ocupa P_low en el vector Q-BE.",
            "tipo": "string",
            "dominio": ["1", "X", "2"],
            "origen_tabla": "derivado: vértice de p_low_val",
            "disponible_prepartido": True,
        },
        "lambda_home": {
            "descripcion": "Intensidad Dixon-Coles del local usada por el motor.",
            "tipo": "float",
            "dominio": [0.05, 6.0],
            "origen_tabla": "historical_sovereign_distributions.lambda_home",
            "disponible_prepartido": True,
        },
        "lambda_away": {
            "descripcion": "Intensidad Dixon-Coles del visitante usada por el motor.",
            "tipo": "float",
            "dominio": [0.05, 6.0],
            "origen_tabla": "historical_sovereign_distributions.lambda_away",
            "disponible_prepartido": True,
        },
        "delta_epist": {
            "descripcion": "Incertidumbre epistémica declarada de la distribución.",
            "tipo": "float",
            "dominio": [0.0, 1.0],
            "origen_tabla": "historical_sovereign_distributions.delta_epist",
            "disponible_prepartido": True,
        },
        "odd_home": {
            "descripcion": "Cuota decimal bruta de cierre para el local.",
            "tipo": "float",
            "dominio": [1.05, 50.0],
            "origen_tabla": "historical_matches.odd_home",
            "disponible_prepartido": True,
        },
        "odd_draw": {
            "descripcion": "Cuota decimal bruta de cierre para el empate.",
            "tipo": "float",
            "dominio": [1.05, 50.0],
            "origen_tabla": "historical_matches.odd_draw",
            "disponible_prepartido": True,
        },
        "odd_away": {
            "descripcion": "Cuota decimal bruta de cierre para el visitante.",
            "tipo": "float",
            "dominio": [1.05, 50.0],
            "origen_tabla": "historical_matches.odd_away",
            "disponible_prepartido": True,
        },
        "overround_S": {
            "descripcion": "Suma bruta de inversas de las tres cuotas (margen comercial).",
            "tipo": "float",
            "dominio": [0.85, 1.30],
            "origen_tabla": "derivado: Σ 1/O_k",
            "disponible_prepartido": True,
        },
        "q_shin_1": {
            "descripcion": "Probabilidad pura de victoria local tras de-vig de Shin.",
            "tipo": "float",
            "dominio": [0.0, 1.0],
            "origen_tabla": "desmarginar_shin([odd_home, odd_draw, odd_away]).p_local",
            "disponible_prepartido": True,
        },
        "q_shin_X": {
            "descripcion": "Probabilidad pura de empate tras de-vig de Shin.",
            "tipo": "float",
            "dominio": [0.0, 1.0],
            "origen_tabla": "desmarginar_shin(...).p_empate",
            "disponible_prepartido": True,
        },
        "q_shin_2": {
            "descripcion": "Probabilidad pura de victoria visitante tras de-vig de Shin.",
            "tipo": "float",
            "dominio": [0.0, 1.0],
            "origen_tabla": "desmarginar_shin(...).p_visitante",
            "disponible_prepartido": True,
        },
        "shin_z": {
            "descripcion": "Proporción de apostadores informados resuelta por Shin.",
            "tipo": "float",
            "dominio": [0.0, 1.0],
            "origen_tabla": "desmarginar_shin(...).z_insider",
            "disponible_prepartido": True,
        },
        "q_prop_1": {
            "descripcion": "Probabilidad local por de-vig proporcional clásico (1/O)/S.",
            "tipo": "float",
            "dominio": [0.0, 1.0],
            "origen_tabla": "derivado: (1/odd_home)/overround_S",
            "disponible_prepartido": True,
        },
        "q_prop_X": {
            "descripcion": "Probabilidad de empate por de-vig proporcional clásico.",
            "tipo": "float",
            "dominio": [0.0, 1.0],
            "origen_tabla": "derivado: (1/odd_draw)/overround_S",
            "disponible_prepartido": True,
        },
        "q_prop_2": {
            "descripcion": "Probabilidad visitante por de-vig proporcional clásico.",
            "tipo": "float",
            "dominio": [0.0, 1.0],
            "origen_tabla": "derivado: (1/odd_away)/overround_S",
            "disponible_prepartido": True,
        },
        "mkt_max_val": {
            "descripcion": "Mayor probabilidad del vector de mercado (Shin).",
            "tipo": "float",
            "dominio": [0.0, 1.0],
            "origen_tabla": "derivado: orden descendente de q_shin_*",
            "disponible_prepartido": True,
        },
        "mkt_mid_val": {
            "descripcion": "Segunda probabilidad del vector de mercado (Shin).",
            "tipo": "float",
            "dominio": [0.0, 1.0],
            "origen_tabla": "derivado: orden descendente de q_shin_*",
            "disponible_prepartido": True,
        },
        "mkt_low_val": {
            "descripcion": "Menor probabilidad del vector de mercado (Shin).",
            "tipo": "float",
            "dominio": [0.0, 1.0],
            "origen_tabla": "derivado: orden descendente de q_shin_*",
            "disponible_prepartido": True,
        },
        "vertice_mkt_max": {
            "descripcion": "Desenlace que ocupa Mkt_max.",
            "tipo": "string",
            "dominio": ["1", "X", "2"],
            "origen_tabla": "derivado: vértice de mkt_max_val",
            "disponible_prepartido": True,
        },
        "vertice_mkt_mid": {
            "descripcion": "Desenlace que ocupa Mkt_mid.",
            "tipo": "string",
            "dominio": ["1", "X", "2"],
            "origen_tabla": "derivado: vértice de mkt_mid_val",
            "disponible_prepartido": True,
        },
        "vertice_mkt_low": {
            "descripcion": "Desenlace que ocupa Mkt_low.",
            "tipo": "string",
            "dominio": ["1", "X", "2"],
            "origen_tabla": "derivado: vértice de mkt_low_val",
            "disponible_prepartido": True,
        },
        "tvd_qbe_vs_shin": {
            "descripcion": "Variación total entre el símplex Q-BE y el de Shin.",
            "tipo": "float",
            "dominio": [0.0, 1.0],
            "origen_tabla": "derivado: 0.5 * Σ |p_k − q_k|",
            "disponible_prepartido": True,
        },
        "gap_max": {
            "descripcion": "Diferencia P_max − Mkt_max; mide la ventaja de convicción Q-BE.",
            "tipo": "float",
            "dominio": [-1.0, 1.0],
            "origen_tabla": "derivado: p_max_val − mkt_max_val",
            "disponible_prepartido": True,
        },
        "discrepancia_favorito": {
            "descripcion": "Verdadero si Q-BE y el mercado señalan favoritos distintos.",
            "tipo": "boolean",
            "dominio": [False, True],
            "origen_tabla": "derivado: vertice_qbe_max ≠ vertice_mkt_max",
            "disponible_prepartido": True,
        },
        "entropia_shannon_qbe": {
            "descripcion": "Entropía de Shannon del vector Q-BE (nats).",
            "tipo": "float",
            "dominio": [0.0, 1.0986],
            "origen_tabla": "derivado: −Σ p_k ln p_k",
            "disponible_prepartido": True,
        },
        "entropia_shannon_mkt": {
            "descripcion": "Entropía de Shannon del vector de mercado (nats).",
            "tipo": "float",
            "dominio": [0.0, 1.0986],
            "origen_tabla": "derivado: −Σ q_k ln q_k",
            "disponible_prepartido": True,
        },
        "delta_alt_metros": {
            "descripcion": "Diferencial de altitud del anfitrión (V29 causal, metros).",
            "tipo": "float",
            "dominio": [-3000.0, 3000.0],
            "origen_tabla": "historical_match_causal_vars.v29_local",
            "disponible_prepartido": True,
        },
        "delta_descanso_dias": {
            "descripcion": "Diferencial de días de descanso del anfitrión (V30 causal).",
            "tipo": "float",
            "dominio": [-90.0, 90.0],
            "origen_tabla": "historical_match_causal_vars.v30_local",
            "disponible_prepartido": True,
        },
        "brier_qbe_3n": {
            "descripcion": "Brier multiclase normalizado 3N del vector Q-BE en el partido.",
            "tipo": "float",
            "dominio": [0.0, 1.0],
            "origen_tabla": "brier_multiclase(p_qbe_*) / 3 [LN-QBE-100]",
            "disponible_prepartido": False,
        },
        "brier_mkt_3n": {
            "descripcion": "Brier multiclase normalizado 3N del vector de Shin en el partido.",
            "tipo": "float",
            "dominio": [0.0, 1.0],
            "origen_tabla": "brier_multiclase(q_shin_*) / 3 [LN-QBE-100]",
            "disponible_prepartido": False,
        },
        "delta_brier": {
            "descripcion": "Ventaja de Brier: positivo si Q-BE superó al mercado.",
            "tipo": "float",
            "dominio": [-1.0, 1.0],
            "origen_tabla": "derivado: brier_mkt_3n − brier_qbe_3n",
            "disponible_prepartido": False,
        },
        "acierto_pmax_qbe": {
            "descripcion": "1 si el desenlace real coincidió con P_max de Q-BE.",
            "tipo": "int",
            "dominio": [0, 1],
            "origen_tabla": "derivado: resultado_real == vertice_qbe_max",
            "disponible_prepartido": False,
        },
        "acierto_pmid_qbe": {
            "descripcion": "1 si el desenlace real coincidió con P_mid de Q-BE.",
            "tipo": "int",
            "dominio": [0, 1],
            "origen_tabla": "derivado: resultado_real == vertice_qbe_mid",
            "disponible_prepartido": False,
        },
        "acierto_cobertura_qbe": {
            "descripcion": "1 si el desenlace real cayó en {P_max, P_mid} de Q-BE.",
            "tipo": "int",
            "dominio": [0, 1],
            "origen_tabla": "derivado: resultado_real ∈ {vertice_qbe_max, vertice_qbe_mid}",
            "disponible_prepartido": False,
        },
        "acierto_pmax_mkt": {
            "descripcion": "1 si el desenlace real coincidió con Mkt_max.",
            "tipo": "int",
            "dominio": [0, 1],
            "origen_tabla": "derivado: resultado_real == vertice_mkt_max",
            "disponible_prepartido": False,
        },
        "acierto_cobertura_mkt": {
            "descripcion": "1 si el desenlace real cayó en {Mkt_max, Mkt_mid}.",
            "tipo": "int",
            "dominio": [0, 1],
            "origen_tabla": "derivado: resultado_real ∈ {vertice_mkt_max, vertice_mkt_mid}",
            "disponible_prepartido": False,
        },
    }
    return {
        "dataset": f"dataset_meta_router_{filas}",
        "expediente": "SPRINT-51-META-ROUTER-MACHINE-LEARNING",
        "version": "1.0.0",
        "filas": filas,
        "columnas_total": len(columnas),
        "fuente": {
            "ruta": "qbe_observatory/data/qbe_historico.db",
            "tablas": [
                "historical_matches",
                "historical_sovereign_distributions",
                "historical_match_causal_vars",
            ],
            "modo": "solo_lectura_estricta",
        },
        "filtros": {
            "marcador_confirmado": True,
            "cuotas_1x2_completas": True,
            "overround_S": [SOBRE_MARGEN_MIN, SOBRE_MARGEN_MAX],
            "shin_resoluble": True,
        },
        "universo_ratificado": {
            "decreto": "VAR-2026-SPRINT51-MANUS",
            "opcion": "1 — histórico íntegro",
            "filas": filas,
            "temporadas": temporadas,
            "conjunto_estres_post_holdout": TEMPORADA_ACTUAL,
        },
        "calidad": {
            "temporadas": temporadas,
            "nulos_por_columna": {columna: cuenta for columna, cuenta in nulos.items() if cuenta},
            "nota": (
                "delta_alt_metros y delta_descanso_dias no existen en la temporada "
                "2015_2016 (historical_match_causal_vars sin V29/V30): se declaran nulos, "
                "no se imputan. El resto de columnas críticas no presenta nulos."
            ),
        },
        "columnas": columnas,
    }


# ── Persistencia y verificación ────────────────────────────────────────────────────────────
def _escribir_parquet(filas: Sequence[Dict[str, Any]], ruta: Path) -> pa.Table:
    import pandas as pd

    tabla = pa.Table.from_pandas(
        pd.DataFrame(list(filas), columns=list(ORDEN_COLUMNAS)),
        schema=ESQUEMA,
        preserve_index=False,
        safe=False,
    )
    pq.write_table(tabla, ruta, compression="snappy")
    return tabla


def verificar_dataset(
    filas: Sequence[Dict[str, Any]], esperado: Optional[int] = None
) -> Dict[str, Any]:
    """Puerta de calidad del artefacto: censo, símplex, dominios y Brier."""
    fallos: List[str] = []
    n = len(filas)
    if esperado is not None and n != esperado:
        fallos.append(f"filas={n} ≠ esperado={esperado}")

    criticas = (
        "p_qbe_1", "p_qbe_X", "p_qbe_2",
        "q_shin_1", "q_shin_X", "q_shin_2",
        "resultado_real", "brier_qbe_3n", "brier_mkt_3n", "delta_brier",
    )
    nulos = {columna: 0 for columna in criticas}
    for fila in filas:
        for columna in criticas:
            valor = fila[columna]
            if valor is None or (isinstance(valor, float) and math.isnan(valor)):
                nulos[columna] += 1
    for columna, cuenta in nulos.items():
        if cuenta:
            fallos.append(f"NaN en {columna}: {cuenta}")

    for fila in filas:
        suma_p = fila["p_qbe_1"] + fila["p_qbe_X"] + fila["p_qbe_2"]
        suma_q = fila["q_shin_1"] + fila["q_shin_X"] + fila["q_shin_2"]
        if abs(suma_p - 1.0) > TOLERANCIA_SIMPLEX:
            fallos.append(f"{fila['match_id']}: Σp_qbe={suma_p!r}")
            break
        if abs(suma_q - 1.0) > TOLERANCIA_SIMPLEX:
            fallos.append(f"{fila['match_id']}: Σq_shin={suma_q!r}")
            break
        if fila["resultado_real"] not in ("1", "X", "2"):
            fallos.append(f"{fila['match_id']}: resultado_real={fila['resultado_real']!r}")
            break
        if not (SOBRE_MARGEN_MIN <= fila["overround_S"] <= SOBRE_MARGEN_MAX):
            fallos.append(f"{fila['match_id']}: overround={fila['overround_S']!r}")
            break

    if fallos:
        raise UniversoNoConforme("; ".join(fallos[:10]))

    brier_qbe = math.fsum(fila["brier_qbe_3n"] for fila in filas) / n
    brier_mkt = math.fsum(fila["brier_mkt_3n"] for fila in filas) / n
    return {
        "filas": n,
        "columnas": len(ORDEN_COLUMNAS),
        "brier_qbe_3n": brier_qbe,
        "brier_mkt_3n": brier_mkt,
        "delta_brier": brier_mkt - brier_qbe,
        "alpha_pct": 100.0 * (brier_mkt - brier_qbe) / brier_mkt if brier_mkt else None,
        "sin_nulos_criticos": all(cuenta == 0 for cuenta in nulos.values()),
    }


def sha256(ruta: Path) -> str:
    digest = hashlib.sha256()
    with ruta.open("rb") as manejador:
        for bloque in iter(lambda: manejador.read(1 << 20), b""):
            digest.update(bloque)
    return digest.hexdigest()


# ── CLI ───────────────────────────────────────────────────────────────────────────────────
def _imprimir_censo(censo: Dict[str, Any]) -> None:
    print("-" * 96)
    print(f"Universo: {censo['universo']}")
    print(f"  Candidatos con marcador y P′ : {censo['candidatos']}")
    print(f"  Fuera de temporada           : {censo['fuera_temporada']}")
    print(f"  Sin cuotas 1X2 completas     : {censo['sin_cuotas']}")
    print(f"  Overround fuera de rango     : {censo['overround_fuera']}")
    print(f"  Shin no resoluble            : {censo['shin_fallido']}")
    print(f"  ACEPTADOS                    : {censo['aceptados']}")
    if censo["aceptados"]:
        print(f"  Overround observado          : [{censo['overround_min']:.6f}, {censo['overround_max']:.6f}]")
    print("  Por temporada:")
    for temporada, cuenta in sorted(censo["por_temporada"].items()):
        print(f"    {temporada}: {cuenta}")
    print("-" * 96)


def main(argv: Optional[Sequence[str]] = None) -> int:
    analizador = argparse.ArgumentParser(
        prog="exportar_dataset_manus",
        description="[SPRINT-51] Dataset maestro del Meta-Router (solo lectura estricta).",
    )
    analizador.add_argument(
        "--universo",
        choices=("pre_holdout", "historico"),
        default="historico",
        help="pre_holdout = temporadas del protocolo (2569); historico = todas (2667).",
    )
    analizador.add_argument(
        "--esperado-filas",
        type=int,
        default=FILAS_ESPERADAS,
        help=f"Candado de censo (por defecto {FILAS_ESPERADAS}, cifra del expediente).",
    )
    analizador.add_argument(
        "--permitir-desviacion",
        action="store_true",
        help="Autoriza escribir artefactos aunque el censo no coincida con el candado.",
    )
    analizador.add_argument(
        "--diagnostico",
        action="store_true",
        help="Sólo censa y reporta; no escribe artefactos.",
    )
    analizador.add_argument("--salida", default=None, help="Directorio de salida (omite: data/investigacion).")
    analizador.add_argument("--nombre-parquet", default=NOMBRE_PARQUET, help="Nombre del Parquet.")
    argumentos = analizador.parse_args(argv)

    print("=" * 96)
    print("[SPRINT-51] EXPORTADOR DEL DATASET MAESTRO — RÉGIMEN [DIRGEN-STRICT]")
    print("=" * 96)
    print(f"Bóveda (solo lectura): {DB_HISTORICO}")

    aceptados, censo = censar_universo(_leer_filas(), argumentos.universo)
    _imprimir_censo(censo)

    if argumentos.diagnostico:
        print("Modo diagnóstico: no se escriben artefactos.")
        return 0

    if censo["aceptados"] != argumentos.esperado_filas:
        mensaje = (
            f"UNIVERSO NO CONFORME: {censo['aceptados']} filas frente al candado "
            f"{argumentos.esperado_filas}. La bóveda histórica no reproduce la cifra "
            "del expediente (ver DIRGEN_VARIANCE_REQUEST_SPRINT51_MANUS.md)."
        )
        print(mensaje)
        if not argumentos.permitir_desviacion:
            return 2
        print("Desviación autorizada por CLI: se materializa el universo real.")

    datos = construir_dataset(aceptados, argumentos.universo)
    resumen = verificar_dataset(datos, esperado=None)

    salida = Path(argumentos.salida) if argumentos.salida else DIR_SALIDA
    salida.mkdir(parents=True, exist_ok=True)
    ruta_parquet = salida / argumentos.nombre_parquet
    ruta_diccionario = salida / NOMBRE_DICCIONARIO
    ruta_folds = salida / NOMBRE_FOLDS

    _escribir_parquet(datos, ruta_parquet)
    ruta_diccionario.write_text(
        json.dumps(construir_diccionario(datos), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    ruta_folds.write_text(
        json.dumps(construir_folds(datos), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Relectura del Parquet: certifica que el disco contiene el contrato.
    tabla = pq.read_table(ruta_parquet)
    verificacion_disco = verificar_dataset(
        [dict(fila) for fila in tabla.to_pylist()], esperado=None
    )

    print("=" * 96)
    print("ARTEFACTOS MATERIALIZADOS")
    print("=" * 96)
    print(f"  Parquet    : {ruta_parquet}  ({tabla.num_rows} filas × {tabla.num_columns} columnas)")
    print(f"  Diccionario: {ruta_diccionario}")
    print(f"  Folds      : {ruta_folds}")
    print("-" * 96)
    print(f"Brier 3N Q-BE   : {verificacion_disco['brier_qbe_3n']:.6f}")
    print(f"Brier 3N Shin   : {verificacion_disco['brier_mkt_3n']:.6f}")
    print(f"Delta (Mkt−QBE) : {verificacion_disco['delta_brier']:+.6f}"
          f"  ({verificacion_disco['alpha_pct']:+.2f} % sobre el mercado)")
    print("-" * 96)
    for ruta in (ruta_parquet, ruta_diccionario, ruta_folds):
        print(f"  SHA-256 {ruta.name}: {sha256(ruta)}")
    print("=" * 96)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
