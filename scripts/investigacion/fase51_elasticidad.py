# -*- coding: utf-8 -*-
"""`[SPRINT-50][FASE 5.1]` Elasticidad macro y micro del motor GSL-3D v2.

Régimen ``[DIRGEN-STRICT]``. Sólo lectura sobre ``qbe_historico.db``; experimento de
sensibilidad sobre el motor que conecta las 32 variables (V2, `[LN-QBE-039]` §7.6).
PROHIBIDO el puente mutilado V1: cada símplex se recalcula con ``derivar_factores_estructurales_v2``.

Protocolo
---------
1. **Macro** — se aplica δ ∈ [0.80, 1.20] al bloque COMPLETO de una dimensión canónica y se
   mide el Brier en Train. Ordena las 6 dimensiones por sensibilidad.
2. **Micro** — sobre la dimensión más sensible se barre variable a variable con la **restricción
   de plausibilidad**: si δ·v sale de [p5, p95] de la muestra histórica, el ajuste es INVIABLE.
3. **Validación** — el Mapa de Sesgos ganador (selección greedy) se aplica al Test (2023_2024 →
   2026_2027) y se compara contra V1 (0.636) y FootyStats (0.612).

Uso::  python scripts/investigacion/fase51_elasticidad.py
"""

from __future__ import annotations

import sqlite3
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

RAIZ = Path(__file__).resolve().parents[2]
for _ruta in (RAIZ, RAIZ / "qbe_core"):
    if str(_ruta) not in sys.path:
        sys.path.insert(0, str(_ruta))

from scripts.auditoria.calcular_distribuciones_historicas import (  # noqa: E402
    DB_DEFECTO,
    TABLA_BOVEDA,
    TABLA_VECTOR,
    AcumuladorCausal,
    _filas,
    _vector_de,
)
from src.core.sovereign_pipeline import derivar_factores_estructurales_v2  # noqa: E402
from src.core.intensity_canonical_loglink import (  # noqa: E402
    InsufficientDataException,
    estimar_intensidades_loglineal,
)
from src.core.distribution_dixon_coles import (  # noqa: E402
    calcular_matriz_dixon_coles,
    colapsar_matriz_a_simplex,
)
from src.core.sovereign.calibrar_perturbacion import brier_multiclase  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, OSError, ValueError):  # pragma: no cover
        pass

# ── Dimensiones canónicas `[LN-QBE-120]` (§2) ────────────────────────────────────────────────
DIMENSIONES: Dict[str, Tuple[str, ...]] = {
    "Volumen": ("V01", "V02", "V03", "V04", "V05"),
    "Remate": ("V06", "V07", "V08", "V09", "V10", "V11"),
    "Defensa": ("V12", "V13", "V14", "V15", "V16"),
    "Porteria": ("V17", "V18", "V19", "V20"),
    "Balon_Parado": ("V21", "V22", "V23", "V24", "V25"),
    "Contexto": ("V26", "V27", "V28", "V29", "V30", "V31", "V32"),
}

NOMBRES_CORTOS: Dict[str, str] = {
    "V01": "posesión", "V02": "toques en área", "V03": "pases", "V04": "pases largos",
    "V05": "faltas", "V06": "xG", "V07": "SoT", "V08": "big chances", "V09": "chances falladas",
    "V10": "xGOT", "V11": "xA", "V12": "xGA", "V13": "SoTA", "V14": "acciones defensivas",
    "V15": "intercepciones", "V16": "big chances concedidas", "V17": "goles evitados",
    "V18": "save %", "V19": "salidas", "V20": "clean sheets", "V21": "goles balón parado",
    "V22": "goles recibidos BP", "V23": "córners", "V24": "penales", "V25": "tarjetas",
    "V26": "récord H2H", "V27": "ΔG H2H", "V28": "récord visitante sede", "V29": "Δaltitud",
    "V30": "Δdescanso", "V31": "forma 5P", "V32": "varianza ΔxPTS",
}

DELTAS = [0.80, 0.85, 0.90, 0.95, 1.00, 1.05, 1.10, 1.15, 1.20]
TEMPORADAS_TRAIN = ("2018_2019", "2019_2020", "2020_2021", "2021_2022", "2022_2023")
TEMPORADAS_TEST = ("2023_2024", "2024_2025", "2025_2026", "2026_2027")


class ElasticidadError(RuntimeError):
    """`[FASE 5.1]` La bóveda no permite ejecutar el experimento."""


# ── Construcción del cache de matrices causales ──────────────────────────────────────────────
def construir_cache(conexion: sqlite3.Connection) -> Dict[str, Dict[str, Any]]:
    """Para cada partido con vector: su `matriz_causal` + evidencia (marcador, cuota, contexto)."""
    filas = _filas(
        conexion,
        f"""
        SELECT m.* FROM {TABLA_BOVEDA} m
        JOIN {TABLA_VECTOR} v ON v.match_id = m.match_id
        ORDER BY m.fecha_utc, m.match_id
        """,
    )
    acumulador = AcumuladorCausal()
    cache: Dict[str, Dict[str, Any]] = {}
    for fila in filas:
        match_id = str(fila["match_id"])
        temporada = str(fila.get("temporada") or "")
        vector = _vector_de(conexion, match_id)
        if vector is None or not str(vector.get("fuente_datos") or "").strip():
            acumulador.registrar(
                temporada, str(fila.get("home_team_slug") or ""), str(fila.get("away_team_slug") or ""),
                vector, vector,
            )
            continue
        local = str(fila.get("home_team_slug") or "")
        visita = str(fila.get("away_team_slug") or "")
        matriz = acumulador.matriz_causal(temporada, local, visita)
        delta_alt = vector.get("v29_local")
        delta_rest = vector.get("v30_local")
        cache[match_id] = {
            "matriz": matriz,
            "local": local,
            "visita": visita,
            "delta_alt": float(delta_alt) if delta_alt is not None else None,
            "delta_rest": float(delta_rest) if delta_rest is not None else None,
            "home_goals": fila.get("home_goals"),
            "away_goals": fila.get("away_goals"),
            "odd_home": fila.get("odd_home"),
            "odd_draw": fila.get("odd_draw"),
            "odd_away": fila.get("odd_away"),
            "temporada": temporada,
        }
        acumulador.registrar(temporada, local, visita, vector, vector)
    return cache


def _perturbar(matriz: Dict[str, Any], deltas: Optional[Dict[str, float]]) -> Dict[str, Any]:
    """Escala por δ las variables del club (matriz + vector); la referencia de liga NO se toca."""
    if not deltas:
        return matriz
    salida: Dict[str, Any] = {"medias_liga": matriz["medias_liga"]}
    for lado in ("local", "visita"):
        salida[lado] = [
            {clave: (valor * deltas[clave] if clave in deltas else valor) for clave, valor in fila.items()}
            for fila in matriz[lado]
        ]
    for clave in ("vector_local", "vector_visita"):
        salida[clave] = {
            k: (v * deltas[k] if k in deltas else v) for k, v in matriz[clave].items()
        }
    if "pesos" in matriz:
        salida["pesos"] = matriz["pesos"]
    return salida


def _evaluar(
    cache: Dict[str, Dict[str, Any]],
    identificadores: Sequence[str],
    deltas: Optional[Dict[str, float]] = None,
) -> Tuple[Optional[float], int]:
    """Brier medio del subconjunto bajo un mapa de δ (recalcula el motor V2)."""
    total = 0.0
    n = 0
    for match_id in identificadores:
        registro = cache[match_id]
        matriz = _perturbar(registro["matriz"], deltas)
        if not matriz.get("medias_liga"):
            continue  # cold start: sin referencia de liga ⇒ S(I)=0 (paridad con el puente)
        try:
            factores = derivar_factores_estructurales_v2(matriz)
        except (InsufficientDataException, ValueError):
            continue
        if factores is None:
            continue
        a_h, d_a, a_a, d_h, _traza = factores
        lambda_h, lambda_a = estimar_intensidades_loglineal(
            a_h, d_a, a_a, d_h,
            mu_liga=2.65, gamma_home_base=0.15,
            delta_alt_metros=registro["delta_alt"], delta_descanso_dias=registro["delta_rest"],
            home_team_slug=registro["local"],
        )
        matriz_dc = calcular_matriz_dixon_coles(lambda_h, lambda_a)
        p1, px, p2 = colapsar_matriz_a_simplex(matriz_dc)
        total += brier_multiclase(p1, px, p2, int(registro["home_goals"]), int(registro["away_goals"]))
        n += 1
    return (total / n) if n else None, n


def _percentiles(cache: Dict[str, Dict[str, Any]]) -> Dict[str, Tuple[float, float]]:
    """[p5, p95] por variable sobre la muestra histórica completa (ambos lados)."""
    valores: Dict[str, List[float]] = defaultdict(list)
    for registro in cache.values():
        for lado in ("local", "visita"):
            for fila in registro["matriz"][lado]:
                for clave, valor in fila.items():
                    valores[clave].append(float(valor))
    return {
        clave: (float(np.percentile(lista, 5)), float(np.percentile(lista, 95)))
        for clave, lista in valores.items()
    }


def _viable(deltas: Dict[str, float], cache: Dict[str, Dict[str, Any]], percs: Dict[str, Tuple[float, float]]) -> Tuple[bool, int]:
    """¿El mapa δ mantiene TODOS los valores dentro de [p5, p95]? Devuelve (viable, violaciones)."""
    violaciones = 0
    for registro in cache.values():
        for lado in ("local", "visita"):
            for fila in registro["matriz"][lado]:
                for clave, valor in fila.items():
                    if clave not in deltas:
                        continue
                    p5, p95 = percs.get(clave, (-np.inf, np.inf))
                    ajustado = float(valor) * deltas[clave]
                    if ajustado < p5 or ajustado > p95:
                        violaciones += 1
    return violaciones == 0, violaciones


def _greedy(
    variables: Sequence[str],
    cache: Dict[str, Dict[str, Any]],
    identificadores: Sequence[str],
    percs: Dict[str, Tuple[float, float]],
    baseline: float,
) -> Tuple[Dict[str, float], float]:
    """Selección forward greedy: aplica el (variable, δ) que más baja el Brier de Train."""
    activo: Dict[str, float] = {}
    mejor_brier = baseline
    while True:
        candidato: Optional[Tuple[float, str, float]] = None
        for variable in variables:
            for delta in DELTAS:
                if delta == 1.0:
                    continue
                mapa = dict(activo)
                mapa[variable] = delta
                viable, _ = _viable(mapa, cache, percs)
                if not viable:
                    continue
                brier, _n = _evaluar(cache, identificadores, mapa)
                if brier is None:
                    continue
                if brier < mejor_brier - 1e-4 and (candidato is None or brier < candidato[0]):
                    candidato = (brier, variable, delta)
        if candidato is None:
            break
        brier, variable, delta = candidato
        activo[variable] = delta
        mejor_brier = brier
    return activo, mejor_brier


def _mercado_brier(cache: Dict[str, Dict[str, Any]], identificadores: Sequence[str]) -> Tuple[Optional[float], int]:
    """Brier de referencia FootyStats de-vig (misma intersección con marcador)."""
    total = 0.0
    n = 0
    for match_id in identificadores:
        r = cache[match_id]
        if r["home_goals"] is None or r["away_goals"] is None:
            continue
        if r["odd_home"] is None or r["odd_draw"] is None or r["odd_away"] is None:
            continue
        cuotas = (float(r["odd_home"]), float(r["odd_draw"]), float(r["odd_away"]))
        if min(cuotas) <= 1.0:
            continue
        inversas = [1.0 / c for c in cuotas]
        suma = sum(inversas)
        p = [i / suma for i in inversas]
        total += brier_multiclase(p[0], p[1], p[2], int(r["home_goals"]), int(r["away_goals"]))
        n += 1
    return (total / n) if n else None, n


def _pct(delta: float) -> str:
    return f"{(delta - 1.0) * 100:+.1f}%"


def main() -> int:
    if not DB_DEFECTO.is_file():
        raise ElasticidadError(f"Bóveda inexistente: {DB_DEFECTO}")
    conexion = sqlite3.connect(f"file:{DB_DEFECTO.as_posix()}?mode=ro", uri=True)
    try:
        cache = construir_cache(conexion)
    finally:
        conexion.close()

    train_ids = [m for m, r in cache.items() if r["temporada"] in TEMPORADAS_TRAIN and r["home_goals"] is not None]
    test_ids = [m for m, r in cache.items() if r["temporada"] in TEMPORADAS_TEST and r["home_goals"] is not None]
    if not train_ids or not test_ids:
        raise ElasticidadError("Split vacío: revisar temporadas legisladas.")

    percs = _percentiles(cache)
    base_train, n_train = _evaluar(cache, train_ids)
    base_test, n_test = _evaluar(cache, test_ids)

    print("=" * 96)
    print("FASE 5.1 — ELASTICIDAD MACRO Y MICRO DEL MOTOR GSL-3D v2 · [DIRGEN-STRICT]")
    print("=" * 96)
    print(f"Partidos con matriz causal : {len(cache)}")
    print(f"Train {TEMPORADAS_TRAIN[0]}..{TEMPORADAS_TRAIN[-1]} : {len(train_ids)}  (Brier base {base_train:.6f})")
    print(f"Test  {TEMPORADAS_TEST[0]}..{TEMPORADAS_TEST[-1]} : {len(test_ids)}  (Brier base {base_test:.6f})")
    print(f"Rejilla δ : {DELTAS}")

    # ── TAREA 1 — MACRO ──────────────────────────────────────────────────────────────────────
    print()
    print("TAREA 1 · MACRO-ELASTICIDAD (bloque completo de la dimensión)")
    print("-" * 96)
    print(f"{'Dimensión':<14}{'Variables':>28}{'Mejor δ':>10}{'ΔBrier':>10}{'Viable':>9}")
    macro = {}
    for nombre, variables in DIMENSIONES.items():
        mejor = (1.0, 0.0, True)
        for delta in DELTAS:
            mapa = {v: delta for v in variables}
            brier, _ = _evaluar(cache, train_ids, mapa)
            if brier is None:
                continue
            viable, _ = _viable(mapa, cache, percs)
            delta_brier = brier - base_train
            if delta_brier < mejor[1] - 1e-6:
                mejor = (delta, delta_brier, viable)
        macro[nombre] = mejor
        print(
            f"{nombre:<14}{','.join(variables):>28}{_pct(mejor[0]):>10}"
            f"{mejor[1]:>+10.6f}{('SÍ' if mejor[2] else 'NO'):>9}"
        )

    mejor_dim = min(macro, key=lambda d: macro[d][1])
    print(f"\nDimensión más sensible: {mejor_dim} (ΔBrier {macro[mejor_dim][1]:+.6f})")

    # ── TAREA 2 — MICRO ──────────────────────────────────────────────────────────────────────
    variables_dim = DIMENSIONES[mejor_dim]
    print()
    print(f"TAREA 2 · MICRO-ELASTICIDAD (variables de {mejor_dim})")
    print("-" * 96)
    print(f"{'Variable':<28}{'Rango':>18}{'Mejor δ':>10}{'ΔBrier':>10}{'Plausible':>11}")
    micro = {}
    for variable in variables_dim:
        mejor = (1.0, 0.0, True)
        for delta in DELTAS:
            mapa = {variable: delta}
            brier, _ = _evaluar(cache, train_ids, mapa)
            if brier is None:
                continue
            viable, _ = _viable(mapa, cache, percs)
            delta_brier = brier - base_train
            if delta_brier < mejor[1] - 1e-6:
                mejor = (delta, delta_brier, viable)
        micro[variable] = mejor
        print(
            f"{variable} ({NOMBRES_CORTOS.get(variable,'')})".ljust(28)
            + f"[{DELTAS[0]:.2f}, {DELTAS[-1]:.2f}]".rjust(18)
            + f"{_pct(mejor[0]):>10}{mejor[1]:>+10.6f}"
            + f"{('SÍ' if mejor[2] else 'INVIABLE'):>11}"
        )

    # ── MAPA DE SESGOS GANADOR (greedy) ──────────────────────────────────────────────────────
    print()
    print("TAREA 2-bis · MAPA DE SESGOS GANADOR (selección greedy sobre Train)")
    print("-" * 96)
    ganador, brier_train_ganador = _greedy(variables_dim, cache, train_ids, percs, base_train)
    if not ganador:
        print("  Ninguna combinación viable mejoró el Brier de Train.")
    else:
        for variable, delta in sorted(ganador.items()):
            print(f"  {variable:<6} → {_pct(delta):>8}   (Δ acumulado: {brier_train_ganador - base_train:+.6f})")

    # ── TAREA 3 — VALIDACIÓN EN TEST ─────────────────────────────────────────────────────────
    print()
    print("TAREA 3 · VALIDACIÓN EN TEST")
    print("-" * 96)
    brier_test_ganador, n_test_ganador = _evaluar(cache, test_ids, ganador) if ganador else (base_test, n_test)
    brier_mercado, n_mercado = _mercado_brier(cache, test_ids)

    print(f"{'Motor':<22}{'Brier Test':>12}{'N':>7}{'Δ vs V1(0.636)':>17}{'Δ vs FootyStats':>18}")
    referencias = [("V1 (0.636)", 0.636), ("V2 base", base_test), ("V2 + Mapa de Sesgos", brier_test_ganador)]
    for etiqueta, valor in referencias:
        dv1 = valor - 0.636
        dfs = (valor - brier_mercado) if brier_mercado else float("nan")
        print(f"{etiqueta:<22}{valor:>12.6f}{'':>7}{dv1:>+17.6f}{dfs:>+18.6f}")
    print(f"{'FootyStats (mercado)':<22}{brier_mercado:>12.6f}{n_mercado:>7}")

    supera_v1 = brier_test_ganador < 0.636
    supera_mercado = brier_mercado is not None and brier_test_ganador < brier_mercado
    print()
    print(f"¿Supera a V1 (0.636)?      {'SÍ' if supera_v1 else 'NO'}")
    print(f"¿Supera a FootyStats?      {'SÍ' if supera_mercado else 'NO'}")

    # ── TAREA 4 — MAPA DE SESGOS (formato del Auditor) ───────────────────────────────────────
    print()
    print("TAREA 4 · MAPA DE SESGOS (formato del Auditor)")
    print("-" * 96)
    print(f"{'Variable':<10}{'Rango Probado':>16}{'Mejor δ':>10}{'Impacto Brier':>16}{'Interpretación':>34}")
    for variable, (delta, impacto, viable) in micro.items():
        interpretacion = (
            f"{NOMBRES_CORTOS.get(variable, '')} {'(ajuste plausible)' if viable else '(INVIABLE)'}"
        )
        print(
            f"{variable:<10}{f'[{DELTAS[0]:.2f}, {DELTAS[-1]:.2f}]':>16}{_pct(delta):>10}"
            f"{impacto:>+16.6f}{interpretacion:>34}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
