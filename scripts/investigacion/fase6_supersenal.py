# -*- coding: utf-8 -*-
"""`[SPRINT-50][FASE 6]` Súper-señal (V06/V07/V12), barrido de κ y Sistema Inmune Fiduciario.

Régimen ``[DIRGEN-STRICT]``. Sólo lectura sobre ``qbe_historico.db``.

* **Capa 1** — ``generar_distribucion_v6`` (α fija 0.203603, sin GSL-3D): xG/SoT para el ataque,
  xGA para la defensa, contra la media de liga por temporada.
* **Capa 2** — barrido κ ∈ [0.35, 0.55] (paso 0.05) sobre el Train; κ* = argmin Brier.
* **Capa 4** — ``veto_inmunidad_fiduciaria`` (ineficiencia / sobreasedio) sobre V01-V05, V08-V11,
  V13-V28, V31-V32; el experimento reporta el % de partidos vetados.

Uso::  python scripts/investigacion/fase6_supersenal.py
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
from src.core.sovereign_pipeline import generar_distribucion_v6  # noqa: E402
from src.core.triage import veto_inmunidad_fiduciaria  # noqa: E402
from src.core.sovereign.calibrar_perturbacion import brier_multiclase  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, OSError, ValueError):  # pragma: no cover
        pass

TEMPORADAS_TRAIN = ("2018_2019", "2019_2020", "2020_2021", "2021_2022", "2022_2023")
TEMPORADAS_TEST = ("2023_2024", "2024_2025", "2025_2026", "2026_2027")
KAPPA_BARRIDO = [0.35, 0.40, 0.45, 0.50, 0.55]

#: Variables de la SÚPER-SEÑAL (Capa 1) y variables del SISTEMA INMUNE (Capa 4).
SUPERSENAL = ("V06", "V07", "V12")
INMUNE_ALTO = ("V06", "V25")
INMUNE_MUY_ALTO = ("V09", "V13")
INMUNE_BAJO = ("V31",)


def _construir(conexion: sqlite3.Connection) -> Dict[str, Dict[str, Any]]:
    filas = _filas(
        conexion,
        f"SELECT m.* FROM {TABLA_BOVEDA} m JOIN {TABLA_VECTOR} v ON v.match_id = m.match_id "
        f"ORDER BY m.fecha_utc, m.match_id",
    )
    acumulador = AcumuladorCausal()
    salida: Dict[str, Dict[str, Any]] = {}
    for fila in filas:
        match_id = str(fila["match_id"])
        temporada = str(fila.get("temporada") or "")
        local = str(fila.get("home_team_slug") or "")
        visita = str(fila.get("away_team_slug") or "")
        vector = _vector_de(conexion, match_id)
        if vector is None or not str(vector.get("fuente_datos") or "").strip():
            acumulador.registrar(temporada, local, visita, vector, vector)
            continue
        matriz = acumulador.matriz_causal(temporada, local, visita)
        vec_local = matriz.get("vector_local") or {}
        vec_visita = matriz.get("vector_visita") or {}
        medias = matriz.get("medias_liga") or {}
        # Cobertura mínima de la súper-señal: las 3 tasas por club + las 3 medias de liga.
        completo = (
            all(var in vec_local for var in SUPERSENAL)
            and all(var in vec_visita for var in SUPERSENAL)
            and all(var in medias for var in SUPERSENAL)
        )
        registro = {
            "temporada": temporada,
            "home_goals": fila.get("home_goals"),
            "away_goals": fila.get("away_goals"),
            "odd_home": fila.get("odd_home"),
            "odd_draw": fila.get("odd_draw"),
            "odd_away": fila.get("odd_away"),
            "vector_local": vec_local,
            "vector_visita": vec_visita,
            "completo": completo,
        }
        if completo:
            registro["raw"] = {
                "home_team_stats": {
                    "pj": len(matriz.get("local") or []),
                    "xg": vec_local["V06"], "sot": vec_local["V07"], "xga": vec_local["V12"],
                },
                "away_team_stats": {
                    "pj": len(matriz.get("visita") or []),
                    "xg": vec_visita["V06"], "sot": vec_visita["V07"], "xga": vec_visita["V12"],
                },
                "medias_liga": {
                    "xg": medias["V06"], "sot": medias["V07"], "xga": medias["V12"],
                },
            }
        salida[match_id] = registro
        acumulador.registrar(temporada, local, visita, vector, vector)
    return salida


def _brier_medio(cache: Dict[str, Dict[str, Any]], identificadores: Sequence[str], kappa: float) -> Tuple[Optional[float], int]:
    total = 0.0
    n = 0
    for match_id in identificadores:
        registro = cache[match_id]
        if not registro["completo"]:
            continue
        out = generar_distribucion_v6(str(match_id), registro["raw"], kappa_net=kappa)
        if not out.es_operable:
            continue
        total += brier_multiclase(
            out.p_local, out.p_empate, out.p_visitante,
            int(registro["home_goals"]), int(registro["away_goals"]),
        )
        n += 1
    return (total / n) if n else None, n


def _mercado_brier(cache: Dict[str, Dict[str, Any]], identificadores: Sequence[str]) -> Tuple[Optional[float], int]:
    total = 0.0
    n = 0
    for match_id in identificadores:
        r = cache[match_id]
        if r["home_goals"] is None or r["away_goals"] is None or not r["completo"]:
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


def _percentiles(cache: Dict[str, Dict[str, Any]], variables: Sequence[str]) -> Dict[str, Dict[str, float]]:
    valores: Dict[str, List[float]] = defaultdict(list)
    for registro in cache.values():
        for lado in ("vector_local", "vector_visita"):
            for variable in variables:
                valor = registro[lado].get(variable)
                if valor is not None:
                    valores[variable].append(float(valor))
    salida: Dict[str, Dict[str, float]] = {}
    for variable, lista in valores.items():
        lista.sort()
        salida[variable] = {
            "p25": float(np.percentile(lista, 25)),
            "p75": float(np.percentile(lista, 75)),
            "p90": float(np.percentile(lista, 90)),
        }
    return salida


def _brier_tabla_p(tabla: str, identificadores: Sequence[str]) -> Tuple[Optional[float], int]:
    """Brier de una tabla P' (V1/V2/V3) sobre la MISMA intersección de match_ids."""
    conexion = sqlite3.connect(f"file:{DB_DEFECTO.as_posix()}?mode=ro", uri=True)
    try:
        total = 0.0
        n = 0
        for match_id in identificadores:
            fila = conexion.execute(
                f"SELECT p_local, p_empate, p_visitante FROM {tabla} WHERE match_id = ?", (match_id,)
            ).fetchone()
            if not fila:
                continue
            marcador = conexion.execute(
                "SELECT home_goals, away_goals FROM historical_matches WHERE match_id = ?", (match_id,)
            ).fetchone()
            if not marcador or marcador[0] is None or marcador[1] is None:
                continue
            total += brier_multiclase(fila[0], fila[1], fila[2], int(marcador[0]), int(marcador[1]))
            n += 1
        return (total / n) if n else None, n
    finally:
        conexion.close()


def main() -> int:
    if not DB_DEFECTO.is_file():
        print(f"🔴 Bóveda inexistente: {DB_DEFECTO}", file=sys.stderr)
        return 1
    conexion = sqlite3.connect(f"file:{DB_DEFECTO.as_posix()}?mode=ro", uri=True)
    try:
        cache = _construir(conexion)
    finally:
        conexion.close()

    train_ids = [m for m, r in cache.items() if r["temporada"] in TEMPORADAS_TRAIN]
    test_ids = [m for m, r in cache.items() if r["temporada"] in TEMPORADAS_TEST]
    completos_train = [m for m in train_ids if cache[m]["completo"] and cache[m]["home_goals"] is not None]
    completos_test = [m for m in test_ids if cache[m]["completo"] and cache[m]["home_goals"] is not None]

    print("=" * 96)
    print("FASE 6 — SÚPER-SEÑAL (V06/V07/V12) · BARrido de κ · SISTEMA INMUNE · [DIRGEN-STRICT]")
    print("=" * 96)
    print(f"Partidos con vector causal : {len(cache)}")
    print(f"Train (completos súper-señal): {len(completos_train)} · Test: {len(completos_test)}")

    # ── CAPA 2 — BARRIDO DE κ ────────────────────────────────────────────────────────────────
    print()
    print("CAPA 2 · BARRIDO DE κ (Train)")
    print("-" * 96)
    print(f"{'κ':>8}{'Brier Train':>14}{'N':>7}")
    resultados = {}
    for kappa in KAPPA_BARRIDO:
        brier, n = _brier_medio(cache, completos_train, kappa)
        resultados[kappa] = brier
        print(f"{kappa:>8.2f}{brier:>14.6f}{n:>7}" if brier is not None else f"{kappa:>8.2f}{'—':>14}{n:>7}")
    kappa_optimo = min(resultados, key=lambda k: resultados[k])
    print(f"\nκ óptimo: {kappa_optimo:.2f} (Brier Train {resultados[kappa_optimo]:.6f})")

    # ── CAPA 1 — P' V6 con κ óptimo ───────────────────────────────────────────────────────────
    print()
    print("CAPA 1 · P' V6 (κ óptimo) — comparativa")
    print("-" * 96)
    brier_train, n_train = _brier_medio(cache, completos_train, kappa_optimo)
    brier_test, n_test = _brier_medio(cache, completos_test, kappa_optimo)
    brier_mercado, n_mercado = _mercado_brier(cache, completos_test)
    alpha = (1.0 - brier_test / brier_mercado) * 100.0 if brier_mercado else None

    # Comparación JUSTA: V1/V2 sobre la MISMA intersección de match_ids (V6 completos en Test).
    v1_misma, n_v1 = _brier_tabla_p("historical_sovereign_distributions", completos_test)
    v2_misma, n_v2 = _brier_tabla_p("historical_sovereign_distributions_v2", completos_test)

    print(f"{'Motor':<22}{'Brier':>12}{'N':>7}{'Δ vs V1':>16}{'Δ vs FootyStats':>18}")
    filas = [
        ("V1 (misma muestra)", v1_misma, n_v1),
        ("V2 (misma muestra)", v2_misma, n_v2),
        ("V6 Train (κ*)", brier_train, n_train),
        ("V6 Test (κ*)", brier_test, n_test),
        ("FootyStats (mercado)", brier_mercado, n_mercado),
    ]
    for etiqueta, valor, n in filas:
        dv1 = (valor - v1_misma) if (valor is not None and v1_misma) else float("nan")
        dfs = (valor - brier_mercado) if (valor is not None and brier_mercado) else float("nan")
        print(f"{etiqueta:<22}{valor if valor is not None else 0:>12.6f}{n:>7}{dv1:>+16.6f}{dfs:>+18.6f}")
    print(f"Alpha (V6 Test vs mercado): {alpha:+.2f} %" if alpha is not None else "Alpha: —")
    supera_v1 = brier_test is not None and v1_misma is not None and brier_test < v1_misma
    supera_mercado = brier_mercado is not None and brier_test is not None and brier_test < brier_mercado
    print(f"¿Supera a V1 (misma muestra)?  {'SÍ' if supera_v1 else 'NO'}")
    print(f"¿Supera a FootyStats?          {'SÍ' if supera_mercado else 'NO'}")

    # ── CAPA 4 — SISTEMA INMUNE ───────────────────────────────────────────────────────────────
    print()
    print("CAPA 4 · SISTEMA INMUNE FIDUCIARIO (QBE-00)")
    print("-" * 96)
    variables_inmune = tuple(set(INMUNE_ALTO + INMUNE_MUY_ALTO + INMUNE_BAJO))
    percs = _percentiles(cache, variables_inmune)
    p25 = {v: percs[v]["p25"] for v in percs}
    p75 = {v: percs[v]["p75"] for v in percs}
    p90 = {v: percs[v]["p90"] for v in percs}
    contador: Dict[str, int] = defaultdict(int)
    evaluados = 0
    for match_id in completos_test:
        registro = cache[match_id]
        for lado in ("vector_local", "vector_visita"):
            vector = registro[lado]
            veto = veto_inmunidad_fiduciaria(vector, p25, p75, p90)
            if veto is not None:
                contador[veto["arquetipo_veto"]] += 1
        evaluados += 1
    total_vetos = sum(contador.values())
    print(f"Partidos evaluados (Test): {evaluados}")
    print(f"Vetos emitidos: {total_vetos}  ({total_vetos / max(1, evaluados) * 100:.2f} % de los partidos)")
    for arquetipo, cantidad in sorted(contador.items(), key=lambda par: -par[1]):
        print(f"  {cantidad:>4}  {arquetipo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
