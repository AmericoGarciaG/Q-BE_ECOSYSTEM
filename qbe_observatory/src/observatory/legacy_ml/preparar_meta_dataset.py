# -*- coding: utf-8 -*-
"""`[SPRINT-50][FASE 7]` Preparación del Meta-Dataset (Matriz de Entrenamiento del Auditor).

Régimen ``[DIRGEN-STRICT]``. Sólo lectura sobre ``qbe_historico.db``.

* **Features X (29):** variables del catálogo que V6 NO usa — ``V01-V05, V08-V11, V13-V32``.
  Cada feature es la DIFERENCIA local − visita (media expansiva pre-kickoff); nulos imputados
  con la mediana del Train (columna íntegramente nula ⇒ 0.0 declarado).
* **Target Y:** ``1`` si ``Brier_QBE(V6) < Brier_Mercado(FootyStats de-vig)``, si no ``0``.
* **Split:** Train = temporadas ≤ 2024_2025 · Test = {2025_2026, 2026_2027}. Sin fuga temporal.

Artefactos: ``.lab-sprint50/meta_dataset.npz`` (+ ``_meta.json``).
"""

from __future__ import annotations

import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np

RAIZ = Path(__file__).resolve().parents[4]
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
from src.core.sovereign.calibrar_perturbacion import brier_multiclase  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, OSError, ValueError):  # pragma: no cover
        pass

KAPPA_V6 = 0.35
SUPERSENAL = ("V06", "V07", "V12")
# 29 variables NO consumidas por V6: V01-V05 (5) + V08-V11 (4) + V13-V32 (20).
FEATURES: Tuple[str, ...] = tuple(
    f"V{i:02d}" for i in list(range(1, 6)) + list(range(8, 12)) + list(range(13, 33))
)
TEMPORADAS_TEST = {"2025_2026", "2026_2027"}
SALIDA = RAIZ / ".lab-sprint50" / "meta_dataset.npz"


def _mercado_de_vig(odd_h: Any, odd_d: Any, odd_a: Any) -> Tuple[float, float, float] | None:
    if odd_h is None or odd_d is None or odd_a is None:
        return None
    cuotas = (float(odd_h), float(odd_d), float(odd_a))
    if min(cuotas) <= 1.0:
        return None
    inversas = [1.0 / c for c in cuotas]
    suma = sum(inversas)
    return tuple(i / suma for i in inversas)


def construir() -> Dict[str, Any]:
    if not DB_DEFECTO.is_file():
        raise RuntimeError(f"Bóveda inexistente: {DB_DEFECTO}")
    conexion = sqlite3.connect(f"file:{DB_DEFECTO.as_posix()}?mode=ro", uri=True)
    try:
        filas = _filas(
            conexion,
            f"SELECT m.* FROM {TABLA_BOVEDA} m JOIN {TABLA_VECTOR} v ON v.match_id = m.match_id "
            f"ORDER BY m.fecha_utc, m.match_id",
        )
        acumulador = AcumuladorCausal()
        registros: List[Dict[str, Any]] = []
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
            completo = (
                all(var in vec_local for var in SUPERSENAL)
                and all(var in vec_visita for var in SUPERSENAL)
                and all(var in medias for var in SUPERSENAL)
            )
            if not completo or fila.get("home_goals") is None or fila.get("away_goals") is None:
                acumulador.registrar(temporada, local, visita, vector, vector)
                continue

            raw = {
                "home_team_stats": {
                    "pj": len(matriz.get("local") or []),
                    "xg": vec_local["V06"], "sot": vec_local["V07"], "xga": vec_local["V12"],
                },
                "away_team_stats": {
                    "pj": len(matriz.get("visita") or []),
                    "xg": vec_visita["V06"], "sot": vec_visita["V07"], "xga": vec_visita["V12"],
                },
                "medias_liga": {"xg": medias["V06"], "sot": medias["V07"], "xga": medias["V12"]},
            }
            out = generar_distribucion_v6(match_id, raw, kappa_net=KAPPA_V6)
            if not out.es_operable:
                acumulador.registrar(temporada, local, visita, vector, vector)
                continue
            p_qbe = (out.p_local, out.p_empate, out.p_visitante)
            brier_qbe = brier_multiclase(
                p_qbe[0], p_qbe[1], p_qbe[2], int(fila["home_goals"]), int(fila["away_goals"])
            )
            p_mercado = _mercado_de_vig(fila.get("odd_home"), fila.get("odd_draw"), fila.get("odd_away"))
            brier_mercado = None
            if p_mercado is not None:
                brier_mercado = brier_multiclase(
                    p_mercado[0], p_mercado[1], p_mercado[2], int(fila["home_goals"]), int(fila["away_goals"])
                )
            registros.append(
                {
                    "match_id": match_id,
                    "temporada": temporada,
                    "vec_local": vec_local,
                    "vec_visita": vec_visita,
                    "p_qbe": p_qbe,
                    "p_mercado": p_mercado,
                    "brier_qbe": brier_qbe,
                    "brier_mercado": brier_mercado,
                    "odds": (fila.get("odd_home"), fila.get("odd_draw"), fila.get("odd_away")),
                }
            )
            acumulador.registrar(temporada, local, visita, vector, vector)
        return {"registros": registros, "features": FEATURES}
    finally:
        conexion.close()


def _vector_x(registro: Dict[str, Any]) -> np.ndarray:
    out = np.full(len(FEATURES), np.nan, dtype=np.float64)
    for indice, feature in enumerate(FEATURES):
        local = registro["vec_local"].get(feature)
        visita = registro["vec_visita"].get(feature)
        if local is not None and visita is not None:
            out[indice] = float(local) - float(visita)
    return out


def _imputar_mediana(matrices: Sequence[np.ndarray]) -> List[np.ndarray]:
    entrenamiento = matrices[0]
    medianas = np.full(entrenamiento.shape[1], 0.0, dtype=np.float64)
    for columna in range(entrenamiento.shape[1]):
        valida = entrenamiento[:, columna][~np.isnan(entrenamiento[:, columna])]
        if valida.size:
            medianas[columna] = float(np.median(valida))
    salidas = []
    for matriz in matrices:
        copia = matriz.copy()
        for columna in range(copia.shape[1]):
            copia[np.isnan(copia[:, columna]), columna] = medianas[columna]
        salidas.append(copia)
    return salidas


def preparar() -> Dict[str, Any]:
    datos = construir()
    registros = datos["registros"]
    es_test = np.array([r["temporada"] in TEMPORADAS_TEST for r in registros], dtype=bool)

    n = len(registros)
    x = np.vstack([_vector_x(r) for r in registros])
    y = np.array(
        [
            1 if (r["brier_mercado"] is not None and r["brier_qbe"] < r["brier_mercado"]) else 0
            for r in registros
        ],
        dtype=np.int64,
    )
    p_qbe = np.array([r["p_qbe"] for r in registros], dtype=np.float64)
    p_mercado = np.full((n, 3), np.nan, dtype=np.float64)
    for indice, r in enumerate(registros):
        if r["p_mercado"] is not None:
            p_mercado[indice] = r["p_mercado"]
    brier_qbe = np.array([r["brier_qbe"] for r in registros], dtype=np.float64)
    brier_mercado = np.array(
        [r["brier_mercado"] if r["brier_mercado"] is not None else np.nan for r in registros],
        dtype=np.float64,
    )
    odds = np.array(
        [[(float(r["odds"][i]) if r["odds"][i] is not None else np.nan) for i in range(3)] for r in registros],
        dtype=np.float64,
    )
    temporadas = np.array([r["temporada"] for r in registros])
    ids = np.array([r["match_id"] for r in registros])

    x_train_raw, x_test_raw = x[~es_test], x[es_test]
    x_train, x_test = _imputar_mediana([x_train_raw, x_test_raw])

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        SALIDA,
        x_train=x_train, x_test=x_test,
        y_train=y[~es_test], y_test=y[es_test],
        ids_train=ids[~es_test], ids_test=ids[es_test],
        p_qbe_train=p_qbe[~es_test], p_qbe_test=p_qbe[es_test],
        p_mercado_train=p_mercado[~es_test], p_mercado_test=p_mercado[es_test],
        brier_qbe_train=brier_qbe[~es_test], brier_qbe_test=brier_qbe[es_test],
        brier_mercado_train=brier_mercado[~es_test], brier_mercado_test=brier_mercado[es_test],
        odds_train=odds[~es_test], odds_test=odds[es_test],
        temporada_train=temporadas[~es_test], temporada_test=temporadas[es_test],
    )
    meta = {
        "features": list(FEATURES),
        "kappa_v6": KAPPA_V6,
        "temporadas_test": sorted(TEMPORADAS_TEST),
        "n_total": n,
        "n_train": int((~es_test).sum()),
        "n_test": int(es_test.sum()),
        "tasa_positivos_train": float(np.mean(y[~es_test])),
        "tasa_positivos_test": float(np.mean(y[es_test])),
    }
    (SALIDA.with_name("meta_dataset_meta.json")).write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return meta


if __name__ == "__main__":
    _meta = preparar()
    print("META-DATASET construido:", SALIDA.name)
    print(json.dumps(_meta, ensure_ascii=False, indent=2))
