# -*- coding: utf-8 -*-
"""`[TAREA 50.4]` Auditoría empírica de Fase 9 — Shin, Derivados y Sistema Inmune.

Régimen ``[DIRGEN-STRICT]``. Sólo lectura sobre ``qbe_historico.db``
(``mode=ro`` + ``PRAGMA query_only=ON``). No escribe en la bóveda, no reimplementa
matemática de ``qbe_core`` y no imputa una sola cuota, probabilidad ni marcador.

Qué mide
---------
1. **Shin vs proporcional vs mercado (1X2).** Brier multiclase normalizado 3N
   (`[LN-QBE-100]`) sobre el universo con cuotas completas + marcador. El motor de
   Shin (`[LN-QBE-151]`) se compara contra el de-vig proporcional (`[LN-QBE-007-C]`)
   en comparación pareada partido a partido (Δ, t, tasa de victoria).
2. **Derivados (Under 2.5 / BTTS).** Se reconstruye la matriz ``M*_xy`` 7×7 desde
   las intensidades persistidas y se proyecta con `[LN-QBE-152]`. Brier binario
   normalizado por 2 (regla 3N generalizada a ``k`` clases) contra el marcador real,
   más *Brier Skill Score* frente a la frecuencia base de la muestra.
3. **Sistema Inmune (Paso 0).** Percentiles ``p25/p75/p90`` calculados **in-sample**
   sobre la propia cohorte evaluable (declarado), veto por lado y por partido, y
   contrafactual económico: apostar el vértice ``P_max`` a la cuota de cierre.

Declaraciones duras (cero invención)
------------------------------------
* **Alpha de derivados = SIN EVIDENCIA.** La bóveda no contiene cuotas históricas
  de Totales ni de BTTS (FootyStats sólo publica 1X2). Sin precio de mercado no hay
  Alpha; se reporta la habilidad disponible (BSS vs. frecuencia base) y se declara
  la deuda en lugar de fabricar un benchmark.
* **Brier "Mercado FootyStats" ≡ Brier proporcional.** Con una sola fuente de
  cuotas, el mercado de-vigado por ``[LN-QBE-007-C]`` *es* π/S. Se conservan ambas
  claves para trazabilidad del mandato y se declara la identidad.
* **Cero imputación.** Todo partido excluido se cuenta y se declara por motivo.
* **Reconstrucción verificada.** Cada matriz se contrasta contra el símplex
  paramétrico sellado en ``audit_trace_json.simplex_poisson``; si no coincide con
  la transición suave de ρ (`[E-50.5]`), se reintenta con el ρ escalonado heredado.
  Una matriz que no reproduce la traza se excluye y se declara.

Uso::

    python scripts/investigacion/fase9_derivados_shin.py
    python scripts/investigacion/fase9_derivados_shin.py --db otra.db --out otro.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sqlite3
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

RAIZ_PROYECTO = Path(__file__).resolve().parents[2]
for _ruta in (RAIZ_PROYECTO, RAIZ_PROYECTO / "qbe_core"):
    if str(_ruta) not in sys.path:
        sys.path.insert(0, str(_ruta))

if hasattr(sys.stdout, "reconfigure"):
    try:  # consola Windows cp1252
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, OSError, ValueError):  # pragma: no cover
        pass

from src.core.consensus import (  # noqa: E402
    InvalidOddsException,
    desmarginar_shin,
)
from src.core.distribution_dixon_coles import (  # noqa: E402
    calcular_matriz_dixon_coles,
    colapsar_matriz_a_simplex,
    proyectar_mercados_derivados,
)
from src.core.sovereign.calibrar_perturbacion import brier_multiclase  # noqa: E402
from src.core.triage import veto_inmunidad_fiduciaria  # noqa: E402

DB_DEFECTO = RAIZ_PROYECTO / "qbe_observatory" / "data" / "qbe_historico.db"
SALIDA_DEFECTO = RAIZ_PROYECTO / "data" / "reportes" / "fase9_evaluacion_derivados.json"

# `[LN-QBE-007-H]` — aduana de sanidad comercial (docs/CONSTANTS.md §2).
OVERROUND_MIN_ADMISIBLE = 0.8500
OVERROUND_MAX_ADMISIBLE = 1.3000

# Variables que consume el Sistema Inmune (`[LN-QBE-060-C]` / E-50.10).
VARIABLES_INMUNE: Tuple[str, ...] = ("V06", "V09", "V13", "V25", "V31")

SEMILLA_BOOTSTRAP = 20261105
REMUESTREOS_BOOTSTRAP = 10_000


# ═══════════════════════════════════════════════════════════════════════════════════════
# INFRAESTRUCTURA DE LECTURA
# ═══════════════════════════════════════════════════════════════════════════════════════


def _conectar(ruta: Path) -> sqlite3.Connection:
    """Abre la bóveda en modo SÓLO LECTURA y certifica el PRAGMA."""
    conexion = sqlite3.connect(f"file:{ruta.as_posix()}?mode=ro", uri=True)
    conexion.execute("PRAGMA query_only = ON")
    if int(conexion.execute("PRAGMA query_only").fetchone()[0]) != 1:
        raise RuntimeError("La bóveda no quedó en query_only=ON: se aborta la auditoría.")
    return conexion


def _sha256(ruta: Path) -> str:
    digesto = hashlib.sha256()
    with open(ruta, "rb") as manejador:
        for bloque in iter(lambda: manejador.read(1024 * 1024), b""):
            digesto.update(bloque)
    return digesto.hexdigest()


def _promedio(valores: Sequence[float]) -> float:
    return math.fsum(valores) / len(valores) if valores else 0.0


def _resumen(valores: Sequence[float]) -> Dict[str, Any]:
    """Media, desviación, error estándar e intervalo normal 95%."""
    n = len(valores)
    if n == 0:
        return {"n": 0, "media": None, "sd": None, "se": None, "ic95": None}
    media = _promedio(valores)
    sd = statistics.pstdev(valores) if n > 1 else 0.0
    se = sd / math.sqrt(n) if n > 1 else 0.0
    return {
        "n": n,
        "media": media,
        "sd": sd,
        "se": se,
        "ic95": [media - 1.96 * se, media + 1.96 * se] if n > 1 else [media, media],
    }


def _bootstrap_ic95(valores: Sequence[float], generador: np.random.Generator) -> List[float]:
    """IC 95% bootstrap (iid, semilla fija) para una media. Declarado iid."""
    if len(valores) < 2:
        return [float(valores[0]), float(valores[0])] if valores else [0.0, 0.0]
    arreglo = np.asarray(valores, dtype=float)
    indices = generador.integers(0, arreglo.size, size=(REMUESTREOS_BOOTSTRAP, arreglo.size))
    medias = arreglo[indices].mean(axis=1)
    return [float(np.percentile(medias, 2.5)), float(np.percentile(medias, 97.5))]


def _deciles(probabilidades: Sequence[float], observaciones: Sequence[int]) -> List[Dict[str, Any]]:
    """Curva de calibración por decil de probabilidad predicha."""
    if not probabilidades:
        return []
    arreglo = np.asarray(probabilidades, dtype=float)
    observado = np.asarray(observaciones, dtype=float)
    bordes = np.linspace(0.0, 1.0, 11)
    salida: List[Dict[str, Any]] = []
    for indice in range(10):
        bajo, alto = bordes[indice], bordes[indice + 1]
        if indice < 9:
            mascara = (arreglo >= bajo) & (arreglo < alto)
        else:
            mascara = (arreglo >= bajo) & (arreglo <= alto)
        n = int(mascara.sum())
        if n == 0:
            continue
        salida.append({
            "deciles": f"[{bajo:.1f},{alto:.1f}{']' if indice == 9 else ')'}",
            "n": n,
            "p_media": float(arreglo[mascara].mean()),
            "frecuencia_observada": float(observado[mascara].mean()),
        })
    return salida


# ═══════════════════════════════════════════════════════════════════════════════════════
# UNIVERSO
# ═══════════════════════════════════════════════════════════════════════════════════════


def _cargar_universo(conexion: sqlite3.Connection) -> Dict[str, Any]:
    """Carga partidos, distribuciones y vectores causales; contabiliza cada exclusión."""
    partidos: Dict[str, Dict[str, Any]] = {}
    for fila in conexion.execute(
        """
        SELECT match_id, temporada, home_goals, away_goals, odd_home, odd_draw, odd_away
          FROM historical_matches
        """
    ):
        partidos[str(fila[0])] = {
            "temporada": str(fila[1]),
            "goles_local": fila[2],
            "goles_visita": fila[3],
            "odds": (fila[4], fila[5], fila[6]),
        }

    distribuciones: Dict[str, Dict[str, Any]] = {}
    for fila in conexion.execute(
        """
        SELECT d.match_id, d.p_local, d.p_empate, d.p_visitante, d.lambda_home,
               d.lambda_away, d.duelos_h2h, d.es_operable, d.audit_trace_json,
               c.v06_local, c.v06_visita, c.v09_local, c.v09_visita,
               c.v13_local, c.v13_visita, c.v25_local, c.v25_visita,
               c.v31_local, c.v31_visita
          FROM historical_sovereign_distributions d
          LEFT JOIN historical_match_causal_vars c ON c.match_id = d.match_id
        """
    ):
        distribuciones[str(fila[0])] = {
            "p_local": fila[1],
            "p_empate": fila[2],
            "p_visitante": fila[3],
            "lambda_home": fila[4],
            "lambda_away": fila[5],
            "duelos_h2h": fila[6],
            "es_operable": fila[7],
            "traza": fila[8],
            "local": {
                "V06": fila[9], "V09": fila[11], "V13": fila[13],
                "V25": fila[15], "V31": fila[17],
            },
            "visita": {
                "V06": fila[10], "V09": fila[12], "V13": fila[14],
                "V25": fila[16], "V31": fila[18],
            },
        }
    return {"partidos": partidos, "distribuciones": distribuciones}


def _odds_validas(odds: Sequence[Any]) -> bool:
    return all(isinstance(o, (int, float)) and o > 1.0 for o in odds)


def _overround(odds: Sequence[float]) -> float:
    return math.fsum(1.0 / float(o) for o in odds)


def _marcador_valido(partido: Dict[str, Any]) -> bool:
    return partido["goles_local"] is not None and partido["goles_visita"] is not None


def _matriz_coherente(
    lambda_home: float, lambda_away: float, traza: Optional[str]
) -> Tuple[Optional[List[List[float]]], str]:
    """Reconstruye ``M*_xy`` y la valida contra el símplex paramétrico sellado.

    La transición suave de ρ (`[E-50.5]`) es el régimen vigente; 390 filas históricas
    se generaron con el escalón heredado. Se elige la que reproduce la traza; si
    ninguna lo hace, la matriz se declara no reconstruible (no se imputa).
    """
    simplex = None
    if traza:
        try:
            simplex = json.loads(traza).get("simplex_poisson")
        except (TypeError, ValueError):
            simplex = None

    for suave in (True, False):
        matriz = calcular_matriz_dixon_coles(
            lambda_h=lambda_home, lambda_a=lambda_away, rho=None, k_max=6, rho_suave=suave
        )
        if not simplex:
            return matriz, "sin_traza"
        colapso = colapsar_matriz_a_simplex(matriz)
        desvio = max(
            abs(colapso[0] - float(simplex.get("p_1", -9.0))),
            abs(colapso[1] - float(simplex.get("p_X", -9.0))),
            abs(colapso[2] - float(simplex.get("p_2", -9.0))),
        )
        if desvio <= 1e-9:
            return matriz, "suave" if suave else "escalon"
    return None, "no_reconstruible"


# ═══════════════════════════════════════════════════════════════════════════════════════
# BLOQUE 1 — SHIN vs PROPORCIONAL vs MERCADO
# ═══════════════════════════════════════════════════════════════════════════════════════


def _evaluar_shin(universo: Dict[str, Any]) -> Dict[str, Any]:
    """Brier 3N de Shin, proporcional, mercado FootyStats y uniforme (pareado)."""
    partidos = universo["partidos"]
    filas: List[Dict[str, Any]] = []
    conteo = {
        "sin_cuotas_completas": 0,
        "sin_marcador": 0,
        "overround_fuera_de_banda": 0,
        "excepcion_del_motor": 0,
    }
    for match_id, partido in partidos.items():
        odds = partido["odds"]
        if not _odds_validas(odds):
            conteo["sin_cuotas_completas"] += 1
            continue
        if not _marcador_valido(partido):
            conteo["sin_marcador"] += 1
            continue
        sobremargen = _overround(odds)
        if not (OVERROUND_MIN_ADMISIBLE <= sobremargen <= OVERROUND_MAX_ADMISIBLE):
            conteo["overround_fuera_de_banda"] += 1
            continue
        inversas = [1.0 / float(o) for o in odds]
        proporcional = [valor / sobremargen for valor in inversas]
        try:
            shin = desmarginar_shin((float(odds[0]), float(odds[1]), float(odds[2])))
        except InvalidOddsException:
            conteo["excepcion_del_motor"] += 1
            continue
        goles_local = int(partido["goles_local"])
        goles_visita = int(partido["goles_visita"])
        brier_shin = brier_multiclase(
            shin.p_local, shin.p_empate, shin.p_visitante, goles_local, goles_visita
        ) / 3.0
        brier_prop = brier_multiclase(
            proporcional[0], proporcional[1], proporcional[2], goles_local, goles_visita
        ) / 3.0
        brier_unif = brier_multiclase(
            1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0, goles_local, goles_visita
        ) / 3.0
        filas.append({
            "match_id": match_id,
            "temporada": partido["temporada"],
            "brier_shin": brier_shin,
            "brier_prop": brier_prop,
            "brier_unif": brier_unif,
            "z_insider": shin.z_insider,
            "p_max_prop": max(proporcional),
            "p_max_shin": max(shin.p_local, shin.p_empate, shin.p_visitante),
            "sin_margen": sobremargen <= 1.0,
        })

    deltas = [fila["brier_shin"] - fila["brier_prop"] for fila in filas]
    resumen_delta = _resumen(deltas)
    t_estadistico = (
        resumen_delta["media"] / resumen_delta["se"]
        if resumen_delta["se"] and resumen_delta["se"] > 0
        else 0.0
    )

    def por_temporada(clave: str) -> Dict[str, Any]:
        agrupado: Dict[str, List[float]] = {}
        for fila in filas:
            agrupado.setdefault(fila["temporada"], []).append(fila[clave])
        return {
            temporada: {"n": len(valores), "media": _promedio(valores)}
            for temporada, valores in sorted(agrupado.items())
        }

    por_deciles = []
    if filas:
        agrupado: Dict[int, List[Dict[str, Any]]] = {}
        for fila in filas:
            indice = min(9, int(fila["p_max_prop"] * 10))
            agrupado.setdefault(indice, []).append(fila)
        for indice in sorted(agrupado):
            bloque = agrupado[indice]
            por_deciles.append({
                "decil_favorito": f"[{indice/10:.1f},{(indice+1)/10:.1f})",
                "n": len(bloque),
                "brier_shin": _promedio([b["brier_shin"] for b in bloque]),
                "brier_prop": _promedio([b["brier_prop"] for b in bloque]),
                "delta": _promedio([b["brier_shin"] - b["brier_prop"] for b in bloque]),
            })

    return {
        "n": len(filas),
        "exclusiones": conteo,
        "brier_shin_3n": _resumen([f["brier_shin"] for f in filas]),
        "brier_proporcional_3n": _resumen([f["brier_prop"] for f in filas]),
        "brier_mercado_footystats_3n": {
            **_resumen([f["brier_prop"] for f in filas]),
            "nota": "Idéntico a brier_proporcional_3n por construcción: fuente única de "
                    "cuotas, de-vig proporcional [LN-QBE-007-C]. Se conserva la clave "
                    "para trazabilidad del mandato.",
        },
        "brier_uniforme_3n": _resumen([f["brier_unif"] for f in filas]),
        "delta_shin_menos_proporcional": {
            **resumen_delta,
            "t_pareado": t_estadistico,
            "tasa_victoria_shin": (
                sum(1 for delta in deltas if delta < 0.0) / len(deltas) if deltas else 0.0
            ),
            "veredicto": (
                "SHIN SUPERA (significativo)" if t_estadistico < -1.96 else
                "SHIN NO SUPERA (no significativo)" if t_estadistico <= 1.96 else
                "SHIN EMPEORA (significativo)"
            ),
        },
        "partidos_sin_margen": sum(1 for fila in filas if fila["sin_margen"]),
        "por_temporada": {
            "brier_shin": por_temporada("brier_shin"),
            "brier_proporcional": por_temporada("brier_prop"),
        },
        "por_decil_favorito": por_deciles,
    }


# ═══════════════════════════════════════════════════════════════════════════════════════
# BLOQUE 2 — DERIVADOS
# ═══════════════════════════════════════════════════════════════════════════════════════


def _evaluar_derivados(universo: Dict[str, Any]) -> Dict[str, Any]:
    """Brier binario 2N de Under 2.5 y BTTS desde ``M*_xy``, contra frecuencia base."""
    partidos = universo["partidos"]
    distribuciones = universo["distribuciones"]
    filas: List[Dict[str, Any]] = []
    regimen = {"suave": 0, "escalon": 0, "sin_traza": 0, "no_reconstruible": 0}
    goles_esperados: List[float] = []
    goles_observados: List[float] = []
    exclusiones = {
        "sin_marcador": 0,
        "no_operable": 0,
        "lambda_invalida": 0,
        "no_reconstruible": 0,
    }

    for match_id, distribucion in distribuciones.items():
        partido = partidos.get(match_id)
        if partido is None:
            continue
        if not bool(distribucion["es_operable"]):
            exclusiones["no_operable"] += 1
            continue
        if not _marcador_valido(partido):
            exclusiones["sin_marcador"] += 1
            continue
        lambda_home = distribucion["lambda_home"]
        lambda_away = distribucion["lambda_away"]
        if not lambda_home or not lambda_away or lambda_home <= 0.0 or lambda_away <= 0.0:
            exclusiones["lambda_invalida"] += 1
            continue
        matriz, etiqueta = _matriz_coherente(lambda_home, lambda_away, distribucion["traza"])
        regimen[etiqueta] = regimen.get(etiqueta, 0) + 1
        if matriz is None:
            exclusiones["no_reconstruible"] += 1
            continue
        proyeccion = proyectar_mercados_derivados(matriz)
        goles_local = int(partido["goles_local"])
        goles_visita = int(partido["goles_visita"])
        goles_esperados.append(float(lambda_home) + float(lambda_away))
        goles_observados.append(float(goles_local + goles_visita))
        under = 1 if (goles_local + goles_visita) <= 2 else 0
        btts = 1 if (goles_local >= 1 and goles_visita >= 1) else 0
        filas.append({
            "match_id": match_id,
            "temporada": partido["temporada"],
            "p_under": proyeccion.p_under_25,
            "y_under": under,
            "brier_under": (proyeccion.p_under_25 - under) ** 2 / 2.0,
            "p_btts": proyeccion.p_btts_si,
            "y_btts": btts,
            "brier_btts": (proyeccion.p_btts_si - btts) ** 2 / 2.0,
        })

    def bloque_mercado(etiqueta_p: str, etiqueta_y: str, etiqueta_brier: str) -> Dict[str, Any]:
        probabilidades = [fila[etiqueta_p] for fila in filas]
        observaciones = [fila[etiqueta_y] for fila in filas]
        brier = _promedio([fila[etiqueta_brier] for fila in filas])
        base = _promedio([float(valor) for valor in observaciones])
        brier_base = _promedio([(base - valor) ** 2 / 2.0 for valor in observaciones])
        return {
            "n": len(filas),
            "frecuencia_base": base,
            "p_media_modelo": _promedio(probabilidades),
            "sesgo_calibracion": _promedio(probabilidades) - base,
            "brier_2n": brier,
            "brier_base_2n": brier_base,
            "brier_skill_score": (1.0 - brier / brier_base) if brier_base > 0 else 0.0,
            "calibracion_por_decil": _deciles(probabilidades, observaciones),
        }

    def por_temporada(etiqueta_brier: str) -> Dict[str, Any]:
        agrupado: Dict[str, List[float]] = {}
        for fila in filas:
            agrupado.setdefault(fila["temporada"], []).append(fila[etiqueta_brier])
        return {
            temporada: {"n": len(valores), "brier_2n": _promedio(valores)}
            for temporada, valores in sorted(agrupado.items())
        }

    return {
        "n": len(filas),
        "regimen_rho": regimen,
        "exclusiones": exclusiones,
        "goles": {
            "esperados_modelo": _promedio(goles_esperados),
            "observados": _promedio(goles_observados),
            "sesgo": _promedio(goles_esperados) - _promedio(goles_observados),
        },
        "under_25": bloque_mercado("p_under", "y_under", "brier_under"),
        "btts_si": bloque_mercado("p_btts", "y_btts", "brier_btts"),
        "por_temporada": {
            "under_25": por_temporada("brier_under"),
            "btts_si": por_temporada("brier_btts"),
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════════════
# BLOQUE 3 — SISTEMA INMUNE (PASO 0)
# ═══════════════════════════════════════════════════════════════════════════════════════


def _vector_completo(distribucion: Dict[str, Any], lado: str) -> bool:
    return all(distribucion[lado].get(variable) is not None for variable in VARIABLES_INMUNE)


def _evaluar_inmune(universo: Dict[str, Any]) -> Dict[str, Any]:
    """Veto del Sistema Inmune y su contrafactual económico sobre el vértice P_max."""
    partidos = universo["partidos"]
    distribuciones = universo["distribuciones"]
    generador = np.random.default_rng(SEMILLA_BOOTSTRAP)

    candidatos: List[Tuple[str, Dict[str, Any], Dict[str, Any]]] = []
    exclusiones = {
        "sin_marcador": 0,
        "no_operable": 0,
        "sin_cuotas_completas": 0,
        "overround_fuera_de_banda": 0,
        "variables_inmune_incompletas": 0,
    }
    for match_id, distribucion in distribuciones.items():
        partido = partidos.get(match_id)
        if partido is None:
            continue
        if not bool(distribucion["es_operable"]):
            exclusiones["no_operable"] += 1
            continue
        if not _marcador_valido(partido):
            exclusiones["sin_marcador"] += 1
            continue
        if not _odds_validas(partido["odds"]):
            exclusiones["sin_cuotas_completas"] += 1
            continue
        if not (OVERROUND_MIN_ADMISIBLE <= _overround(partido["odds"]) <= OVERROUND_MAX_ADMISIBLE):
            exclusiones["overround_fuera_de_banda"] += 1
            continue
        if not (_vector_completo(distribucion, "local") and _vector_completo(distribucion, "visita")):
            exclusiones["variables_inmune_incompletas"] += 1
            continue
        candidatos.append((match_id, partido, distribucion))

    # Percentiles IN-SAMPLE sobre la cohorte evaluable (declarado).
    percentiles: Dict[str, Dict[str, float]] = {}
    for variable in VARIABLES_INMUNE:
        valores: List[float] = []
        for _, _, distribucion in candidatos:
            valores.append(float(distribucion["local"][variable]))
            valores.append(float(distribucion["visita"][variable]))
        arreglo = np.asarray(valores, dtype=float)
        percentiles[variable] = {
            "p25": float(np.percentile(arreglo, 25)),
            "p75": float(np.percentile(arreglo, 75)),
            "p90": float(np.percentile(arreglo, 90)),
        }
    p25 = {variable: percentiles[variable]["p25"] for variable in VARIABLES_INMUNE}
    p75 = {variable: percentiles[variable]["p75"] for variable in VARIABLES_INMUNE}
    p90 = {variable: percentiles[variable]["p90"] for variable in VARIABLES_INMUNE}

    conteo_arquetipos: Dict[str, int] = {}
    vetos_por_lado = 0
    vetos_por_partido = 0
    vetos_lado_dominante = 0
    roi_veto: List[float] = []
    roi_sin_veto: List[float] = []
    roi_dominante_veto: List[float] = []
    roi_dominante_sin_veto: List[float] = []
    perdidas_globales = 0
    evaluados_contrafactual = 0

    for _, partido, distribucion in candidatos:
        disparos_lado = []
        for lado in ("local", "visita"):
            vector = {variable: float(distribucion[lado][variable]) for variable in VARIABLES_INMUNE}
            veto = veto_inmunidad_fiduciaria(vector, p25, p75, p90)
            disparos_lado.append(veto)
            if veto is not None:
                vetos_por_lado += 1
                arquetipo = str(veto["arquetipo_veto"])
                conteo_arquetipos[arquetipo] = conteo_arquetipos.get(arquetipo, 0) + 1

        veto_partido = any(veto is not None for veto in disparos_lado)
        if veto_partido:
            vetos_por_partido += 1

        # Lado dominante = el de mayor probabilidad entre local y visita.
        indice_dominante = 0 if float(distribucion["p_local"]) >= float(distribucion["p_visitante"]) else 2
        lado_dominante = "local" if indice_dominante == 0 else "visita"
        veto_dominante = disparos_lado[0 if lado_dominante == "local" else 1] is not None
        if veto_dominante:
            vetos_lado_dominante += 1

        # Contrafactual: apostar el vértice P_max a la cuota de cierre, stake 1.
        probabilidades = (
            float(distribucion["p_local"]),
            float(distribucion["p_empate"]),
            float(distribucion["p_visitante"]),
        )
        indice = max(range(3), key=lambda i: probabilidades[i])
        cuota = float(partido["odds"][indice])
        goles_local = int(partido["goles_local"])
        goles_visita = int(partido["goles_visita"])
        if indice == 0:
            gano = goles_local > goles_visita
        elif indice == 1:
            gano = goles_local == goles_visita
        else:
            gano = goles_visita > goles_local
        beneficio = (cuota - 1.0) if gano else -1.0
        if veto_partido:
            roi_veto.append(beneficio)
        else:
            roi_sin_veto.append(beneficio)
        if veto_dominante:
            roi_dominante_veto.append(beneficio)
        else:
            roi_dominante_sin_veto.append(beneficio)
        evaluados_contrafactual += 1
        if beneficio < 0.0:
            perdidas_globales += 1

    roi_global = _promedio(roi_veto + roi_sin_veto)
    tasa_perdida_global = (
        perdidas_globales / evaluados_contrafactual if evaluados_contrafactual else 0.0
    )
    delta_roi = _promedio(roi_veto) - _promedio(roi_sin_veto)
    if len(roi_veto) >= 2 and len(roi_sin_veto) >= 2:
        arreglo_veto = np.asarray(roi_veto, dtype=float)
        arreglo_sin = np.asarray(roi_sin_veto, dtype=float)
        indices_veto = generador.integers(
            0, arreglo_veto.size, size=(REMUESTREOS_BOOTSTRAP, arreglo_veto.size)
        )
        indices_sin = generador.integers(
            0, arreglo_sin.size, size=(REMUESTREOS_BOOTSTRAP, arreglo_sin.size)
        )
        diferencias = arreglo_veto[indices_veto].mean(axis=1) - arreglo_sin[indices_sin].mean(axis=1)
        ic_delta = [
            float(np.percentile(diferencias, 2.5)),
            float(np.percentile(diferencias, 97.5)),
        ]
    else:
        ic_delta = [delta_roi, delta_roi]
    tasa_perdida_veto = (
        sum(1 for valor in roi_veto if valor < 0.0) / len(roi_veto) if roi_veto else 0.0
    )
    tasa_perdida_sin_veto = (
        sum(1 for valor in roi_sin_veto if valor < 0.0) / len(roi_sin_veto) if roi_sin_veto else 0.0
    )

    return {
        "n_evaluables": len(candidatos),
        "exclusiones": exclusiones,
        "percentiles_in_sample": percentiles,
        "tasa_veto": {
            "por_lado": vetos_por_lado / (len(candidatos) * 2) if candidatos else 0.0,
            "por_partido_cualquier_lado": vetos_por_partido / len(candidatos) if candidatos else 0.0,
            "por_lado_dominante": vetos_lado_dominante / len(candidatos) if candidatos else 0.0,
        },
        "conteo_arquetipos": dict(sorted(conteo_arquetipos.items(), key=lambda par: -par[1])),
        "contrafactual_1x2": {
            "descripcion": "Apostar el vértice P_max a la cuota de cierre, stake unitario.",
            "roi_global": roi_global,
            "cohorte_veto": {
                "n": len(roi_veto),
                "roi": _promedio(roi_veto),
                "ic95_bootstrap": _bootstrap_ic95(roi_veto, generador),
                "tasa_perdida": tasa_perdida_veto,
                "efectividad_del_veto": tasa_perdida_veto - tasa_perdida_global,
            },
            "cohorte_sin_veto": {
                "n": len(roi_sin_veto),
                "roi": _promedio(roi_sin_veto),
                "tasa_perdida": tasa_perdida_sin_veto,
            },
            "delta_roi_veto_menos_sin_veto": {
                "valor": delta_roi,
                "ic95_bootstrap": ic_delta,
                "significativo": bool(ic_delta[0] > 0.0 or ic_delta[1] < 0.0),
            },
            "cohorte_lado_dominante": {
                "n_veto": len(roi_dominante_veto),
                "roi_veto": _promedio(roi_dominante_veto),
                "n_sin_veto": len(roi_dominante_sin_veto),
                "roi_sin_veto": _promedio(roi_dominante_sin_veto),
                "delta_roi": (
                    _promedio(roi_dominante_veto) - _promedio(roi_dominante_sin_veto)
                ),
            },
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════════════
# BLOQUE 4 — ALPHA DE DERIVADOS: EVIDENCIA DISPONIBLE
# ═══════════════════════════════════════════════════════════════════════════════════════


def _evidencia_alpha_derivados(conexion: sqlite3.Connection) -> Dict[str, Any]:
    """Inspecciona el esquema y documenta por qué el Alpha de derivados no es calculable.

    Sólo considera **columnas de precio** (``odd*``, ``cuota*``, ``price*``); un
    estadístico agregado como ``btts_pct`` no es una cuota y no cuenta como evidencia.
    """
    patron_precio = re.compile(r"(odd|cuota|price)", re.IGNORECASE)
    patron_derivado = re.compile(
        r"(under|over|btts|ambos|handicap|total_goals|ou_?2|mas_?2|menos_?2)", re.IGNORECASE
    )
    tablas = [
        fila[0]
        for fila in conexion.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
    ]
    tablas_con_precio: List[Dict[str, Any]] = []
    derivadas: List[Dict[str, Any]] = []
    for tabla in tablas:
        columnas = [str(columna[1]) for columna in conexion.execute(f"PRAGMA table_info('{tabla}')")]
        precios = [columna for columna in columnas if patron_precio.search(columna)]
        if not precios:
            continue
        tablas_con_precio.append({"tabla": tabla, "columnas_precio": precios})
        mercados = [columna for columna in precios if patron_derivado.search(columna)]
        if mercados:
            derivadas.append({"tabla": tabla, "columnas_derivadas": mercados})
    return {
        "estado": "SIN EVIDENCIA" if not derivadas else "REVISAR",
        "motivo": (
            "La bóveda no contiene cuotas históricas de Totales (Over/Under 2.5) ni de "
            "BTTS: FootyStats sólo publica 1X2 y la captura Q-BE Live también es 1X2. "
            "Sin precio de mercado de derivados no existe Alpha de derivados; se reporta "
            "la habilidad disponible (Brier Skill Score vs. frecuencia base) y se declara "
            "la deuda de proveedor."
        ),
        "tablas_con_precio": tablas_con_precio,
        "columnas_derivadas_detectadas": derivadas,
        "tablas_inspeccionadas": len(tablas),
    }


# ═══════════════════════════════════════════════════════════════════════════════════════
# REPORTE
# ═══════════════════════════════════════════════════════════════════════════════════════


def _linea(caracter: str = "═", ancho: int = 86) -> None:
    print(caracter * ancho)


def _imprimir(reporte: Dict[str, Any]) -> None:
    universo = reporte["universo"]
    shin = reporte["shin"]
    derivados = reporte["derivados"]
    inmune = reporte["sistema_inmune"]

    _linea()
    print("TAREA 50.4 — AUDITORÍA DE DERIVADOS Y SHIN EN BÓVEDA HISTÓRICA")
    _linea()
    print(f"Bóveda  : {universo['db']}")
    print(f"sha256  : {universo['db_sha256'][:32]}…")
    print(f"Modo    : {universo['modo']}")
    print(f"Umbrales: overround admisible [{OVERROUND_MIN_ADMISIBLE:.2f}, {OVERROUND_MAX_ADMISIBLE:.2f}]")
    print()
    print("UNIVERSO")
    print(f"  partidos en bóveda                    {universo['partidos_total']:>7,}")
    print(f"  con cuotas 1X2 completas              {universo['con_cuotas']:>7,}")
    print(f"  con cuotas + marcador                 {universo['con_cuotas_y_marcador']:>7,}")
    print(f"  en banda de overround (Shin)          {shin['n']:>7,}")
    print(f"  con distribución P' (derivados)       {derivados['n']:>7,}")
    print(f"  evaluables por el Sistema Inmune      {inmune['n_evaluables']:>7,}")

    print()
    print("1 · SHIN vs PROPORCIONAL vs MERCADO — BRIER 3N")
    _linea("─")
    print(f"{'Estimador':<34}{'N':>7}{'Brier 3N':>12}{'SE':>11}{'IC95 inf':>11}{'IC95 sup':>11}")
    for etiqueta, clave in (
        ("Shin [LN-QBE-151]", "brier_shin_3n"),
        ("Proporcional [LN-QBE-007-C]", "brier_proporcional_3n"),
        ("Mercado FootyStats (≡ proporcional)", "brier_mercado_footystats_3n"),
        ("Uniforme (1/3,1/3,1/3)", "brier_uniforme_3n"),
    ):
        bloque = shin[clave]
        if bloque["n"] == 0:
            print(f"{etiqueta:<34}{0:>7,}{'—':>12}{'—':>11}{'—':>11}{'—':>11}")
            continue
        print(f"{etiqueta:<34}{bloque['n']:>7,}{bloque['media']:>12.6f}{bloque['se']:>11.6f}"
              f"{bloque['ic95'][0]:>11.6f}{bloque['ic95'][1]:>11.6f}")
    delta = shin["delta_shin_menos_proporcional"]
    print(f"\n  Δ (Shin − Proporcional) = {delta['media']:+.3e}  t pareado = {delta['t_pareado']:+.2f}  "
          f"victorias = {delta['tasa_victoria_shin']:.2%}")
    print(f"  Veredicto: {delta['veredicto']}")
    print(f"  Exclusiones: {shin['exclusiones']}")

    print()
    print("2 · DERIVADOS — UNDER 2.5 Y BTTS (Brier 2N)")
    _linea("─")
    for etiqueta, clave in (("Under 2.5", "under_25"), ("BTTS Sí", "btts_si")):
        bloque = derivados[clave]
        print(f"{etiqueta:<12} N={bloque['n']:>6,}  p_modelo={bloque['p_media_modelo']:.4f}  "
              f"base={bloque['frecuencia_base']:.4f}  sesgo={bloque['sesgo_calibracion']:+.4f}")
        print(f"{'':<12} Brier={bloque['brier_2n']:.6f}  base={bloque['brier_base_2n']:.6f}  "
              f"BSS={bloque['brier_skill_score']:+.2%}")
    print(f"\n  Régimen ρ: {derivados['regimen_rho']}")
    print(f"  Goles esperados λ = {derivados['goles']['esperados_modelo']:.4f} vs "
          f"observados = {derivados['goles']['observados']:.4f} "
          f"(sesgo {derivados['goles']['sesgo']:+.4f})")
    print(f"  Exclusiones: {derivados['exclusiones']}")
    print(f"  Alpha vs cuotas históricas: {reporte['alpha_derivados']['estado']} "
          f"(ver bloque 'alpha_derivados')")

    print()
    print("3 · SISTEMA INMUNE (PASO 0) — VETO Y CONTRAFACTUAL")
    _linea("─")
    tasas = inmune["tasa_veto"]
    print(f"  Cohortes evaluables ......... {inmune['n_evaluables']:>7,}")
    print(f"  Tasa de veto por lado ....... {tasas['por_lado']:>7.2%}")
    print(f"  Tasa de veto por partido .... {tasas['por_partido_cualquier_lado']:>7.2%}")
    print(f"  Tasa de veto lado dominante . {tasas['por_lado_dominante']:>7.2%}")
    print(f"  Arquetipos: {inmune['conteo_arquetipos']}")
    contrafactual = inmune["contrafactual_1x2"]
    print(f"  ROI global (P_max a cuota) .. {contrafactual['roi_global']:>+7.2%}")
    cohorte_veto = contrafactual["cohorte_veto"]
    cohorte_sin = contrafactual["cohorte_sin_veto"]
    print(f"  ROI cohorte veto ............ {cohorte_veto['roi']:>+7.2%} "
          f"(n={cohorte_veto['n']}, IC95 [{cohorte_veto['ic95_bootstrap'][0]:+.2%}, "
          f"{cohorte_veto['ic95_bootstrap'][1]:+.2%}])")
    print(f"  ROI cohorte sin veto ........ {cohorte_sin['roi']:>+7.2%} (n={cohorte_sin['n']})")
    delta_roi = contrafactual["delta_roi_veto_menos_sin_veto"]
    print(f"  Δ ROI (veto − sin veto) ..... {delta_roi['valor']:>+7.2%} "
          f"(IC95 [{delta_roi['ic95_bootstrap'][0]:+.2%}, {delta_roi['ic95_bootstrap'][1]:+.2%}], "
          f"{'significativo' if delta_roi['significativo'] else 'no significativo'})")
    print(f"  Efectividad (>0 evita pérdidas) {cohorte_veto['efectividad_del_veto']:>+6.2%}")

    print()
    print("RESUMEN EJECUTIVO")
    _linea("─")
    for linea in reporte["resumen_ejecutivo"]:
        print(f"  {linea}")

    print()
    print("DECLARACIONES")
    _linea("─")
    for declaracion in reporte["declaraciones"]:
        print(f"  • {declaracion}")


# ═══════════════════════════════════════════════════════════════════════════════════════
# ORQUESTACIÓN
# ═══════════════════════════════════════════════════════════════════════════════════════


def main(argv: Optional[Sequence[str]] = None) -> int:
    analizador = argparse.ArgumentParser(
        description="[TAREA 50.4] Auditoría empírica de Shin, derivados y Sistema Inmune."
    )
    analizador.add_argument("--db", type=Path, default=DB_DEFECTO, help="Ruta de qbe_historico.db")
    analizador.add_argument("--out", type=Path, default=SALIDA_DEFECTO, help="Ruta del reporte JSON")
    argumentos = analizador.parse_args(argv)

    ruta_db = argumentos.db.resolve()
    if not ruta_db.exists():
        print(f"ERROR: no existe la bóveda {ruta_db}", file=sys.stderr)
        return 2

    conexion = _conectar(ruta_db)
    try:
        universo = _cargar_universo(conexion)
        total_partidos = int(
            conexion.execute("SELECT COUNT(*) FROM historical_matches").fetchone()[0]
        )
        con_cuotas = int(
            conexion.execute(
                "SELECT COUNT(*) FROM historical_matches "
                "WHERE odd_home>1 AND odd_draw>1 AND odd_away>1"
            ).fetchone()[0]
        )
        con_cuotas_y_marcador = int(
            conexion.execute(
                "SELECT COUNT(*) FROM historical_matches "
                "WHERE odd_home>1 AND odd_draw>1 AND odd_away>1 "
                "AND home_goals IS NOT NULL AND away_goals IS NOT NULL"
            ).fetchone()[0]
        )
        alpha_derivados = _evidencia_alpha_derivados(conexion)
    finally:
        conexion.close()

    shin = _evaluar_shin(universo)
    derivados = _evaluar_derivados(universo)
    inmune = _evaluar_inmune(universo)

    delta_shin = shin["delta_shin_menos_proporcional"]
    under = derivados["under_25"]
    btts = derivados["btts_si"]
    contrafactual = inmune["contrafactual_1x2"]
    delta_roi = contrafactual["delta_roi_veto_menos_sin_veto"]
    signo_under = "sobreestima" if under["sesgo_calibracion"] > 0 else "subestima"
    signo_btts = "sobreestima" if btts["sesgo_calibracion"] > 0 else "subestima"
    signo_goles = "subestima" if derivados["goles"]["sesgo"] < 0 else "sobreestima"

    resumen_ejecutivo = [
        f"1X2 · Shin vs proporcional: Δ Brier = {delta_shin['media']:+.3e} "
        f"(t pareado {delta_shin['t_pareado']:+.2f}). {delta_shin['veredicto']}.",
        f"1X2 · ROI del vértice P_max a cuota de cierre: {contrafactual['roi_global']:+.2%} "
        f"sobre {inmune['n_evaluables']:,} partidos: el mercado absorbe el margen.",
        f"Derivados · Under 2.5: BSS = {under['brier_skill_score']:+.2%}; el modelo "
        f"{signo_under} el Under en {under['sesgo_calibracion']:+.2%}.",
        f"Derivados · BTTS Sí: BSS = {btts['brier_skill_score']:+.2%}; el modelo "
        f"{signo_btts} el BTTS en {btts['sesgo_calibracion']:+.2%}.",
        f"Derivados · Intensidades: λ esperados {derivados['goles']['esperados_modelo']:.3f} "
        f"vs goles observados {derivados['goles']['observados']:.3f} "
        f"(sesgo {derivados['goles']['sesgo']:+.3f}): el modelo {signo_goles} los goles; "
        "la brecha es de calibración de λ, no de la proyección analítica.",
        "Derivados · Alpha vs. mercado: SIN EVIDENCIA (la bóveda no publica cuotas de "
        "Totales ni de BTTS).",
        f"Sistema Inmune · veto en {inmune['tasa_veto']['por_partido_cualquier_lado']:.2%} "
        f"de los partidos; ROI cohorte veto {contrafactual['cohorte_veto']['roi']:+.2%} vs "
        f"{contrafactual['cohorte_sin_veto']['roi']:+.2%} sin veto "
        f"(Δ {delta_roi['valor']:+.2%}, IC95 [{delta_roi['ic95_bootstrap'][0]:+.2%}, "
        f"{delta_roi['ic95_bootstrap'][1]:+.2%}]): "
        + ("habilidad significativa." if delta_roi["significativo"] else "sin evidencia de habilidad."),
    ]

    reporte: Dict[str, Any] = {
        "meta": {
            "tarea": "50.4",
            "expediente": "SPRINT-50-REINGENIERIA-INDUSTRIAL-QBE-CORE",
            "fase": "9.4 — Auditoría empírica y backtesting",
            "generado_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "regimen": "[DIRGEN-STRICT]",
            "nodos": ["[LN-QBE-151]", "[LN-QBE-152]", "[LN-QBE-060-B]", "[LN-QBE-060-C]"],
            "nota_reproducibilidad": (
                "Los percentiles del Sistema Inmune son IN-SAMPLE sobre la cohorte "
                "evaluable; el bootstrap usa semilla fija 20261105. Las métricas son "
                "deterministas salvo 'generado_utc'."
            ),
        },
        "universo": {
            "db": str(ruta_db),
            "db_sha256": _sha256(ruta_db),
            "db_bytes": ruta_db.stat().st_size,
            "modo": "SÓLO LECTURA (mode=ro + PRAGMA query_only=ON)",
            "partidos_total": total_partidos,
            "con_cuotas": con_cuotas,
            "con_cuotas_y_marcador": con_cuotas_y_marcador,
        },
        "resumen_ejecutivo": resumen_ejecutivo,
        "shin": shin,
        "derivados": derivados,
        "sistema_inmune": inmune,
        "alpha_derivados": alpha_derivados,
        "declaraciones": [
            "Brier 3N = Brier multiclase / 3 ([LN-QBE-100]); en mercados binarios se "
            "normaliza por 2 (regla 3N generalizada a k clases).",
            "Brier 'Mercado FootyStats' es idéntico al proporcional por construcción: "
            "fuente única de cuotas 1X2 y de-vig proporcional [LN-QBE-007-C].",
            "Alpha de derivados = SIN EVIDENCIA: la bóveda no publica cuotas de Totales "
            "ni de BTTS; no se fabrica un benchmark.",
            "Percentiles del Sistema Inmune calculados in-sample sobre la cohorte "
            "evaluable (declarado, no calibración fuera de muestra).",
            f"Los {shin['exclusiones']['overround_fuera_de_banda']} partidos con overround "
            "fuera de [0.85, 1.30] se excluyen por la aduana [LN-QBE-007-H]; no se "
            "renormalizan ni se imputan.",
            "El contrafactual 1X2 apuesta el vértice P_max a la cuota de cierre con "
            "stake unitario; no modela Kelly ni hard-caps.",
            f"La reconstrucción de M*_xy se valida contra audit_trace.simplex_poisson; "
            f"{derivados['regimen_rho']['escalon']} filas históricas exigen el ρ "
            "escalonado heredado [E-50.5].",
            "Cada exclusión se cuenta y se declara por motivo: cero imputación.",
        ],
    }

    argumentos.out.parent.mkdir(parents=True, exist_ok=True)
    argumentos.out.write_text(
        json.dumps(reporte, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )

    _imprimir(reporte)
    print()
    print(f"Reporte JSON: {argumentos.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
