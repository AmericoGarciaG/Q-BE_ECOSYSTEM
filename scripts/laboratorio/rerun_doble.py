# -*- coding: utf-8 -*-
"""
🔬 Q-BE LABORATORIO — RERUN DOBLE B + D (FRAGILIDAD DE LA EVIDENCIA)

[DIRGEN-STRICT] en frontera de datos/contratos · [DBBD-FUNGIBLE] en CLI y reportes.

Implementa los flags del Rerun Doble sobre `sandbox_distancia_borde`:

    --taus 0.50,...,0.99     curva de fragilidad paramétrica
    --n-fragiles 30          tamaño del top de partidos frágiles
    --bootstrap 1000         IC 95% de la mediana por bloques (temporada, jornada)
    --fixed-free             ablaciones: V12 · V26+V29+V30 · V06 · todos
    --modelo-nulo            P_null uniforme (1/3,1/3,1/3) y ratio σ_QBE/σ_null
    --outliers 30            top/bottom por norma con metadata
    --estratificar procedencia_xg   Opta · non-Opta · total
    --kfold 5                α en train 80%, σ en held-out 20% (sólo D)

Lectura absoluta: no escribe snapshots, no imputa cuotas, no usa red ni navegador.
La única escritura son los JSON/MD/console bajo `--salida`.
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from scripts.laboratorio.sandbox_distancia_borde import (
    BordeInfactible,
    CAP_SIGMA,
    TAUS as TAUS_PILOTO,
    biseccion_s,
    cargar_niveles,
    cargar_muestra,
    direccion_objetivo,
    resolver_lambda,
)
from scripts.laboratorio.sandbox_optimizacion_gradiente import RAIZ_PROYECTO, sha256_archivo
from scripts.laboratorio.sandbox_shadow_competitivo import (
    ANCLA_FACTIBLE,
    DIMENSIONES,
    FalloOptimizacion,
    Muestra,
    _folds,
    ajustar_davidson,
    brier,
    estandarizar,
    puntajes,
)

ANCHO = 100
SEMILLA_BOOTSTRAP = 20261030
SUBCONJUNTOS_ABLACION: Dict[str, Optional[List[str]]] = {
    "solo_V06": ["V06"],
    "solo_V12": ["V12"],
    "solo_V26_V29_V30": ["V26", "V29", "V30"],
    "todos": None,
}


@dataclass
class Geometria:
    """Pesos y cotas de la deformación para un subconjunto de celdas activas."""

    w: np.ndarray
    lo: np.ndarray
    hi: np.ndarray
    observado: np.ndarray
    activas: List[int]


@dataclass
class ResultadoTau:
    tau: float
    deltas: np.ndarray
    normas: np.ndarray
    validos: np.ndarray
    inalcanzables: List[str]
    sin_evidencia: List[str]
    saturados: int = 0


# ═════════════════════════════════════════════════════════════════════════════════════════════
# GEOMETRÍA — idéntica al piloto, parametrizada por celdas activas y σ de ajuste
# ═════════════════════════════════════════════════════════════════════════════════════════════
def sigma_celdas(muestra: Muestra) -> np.ndarray:
    with np.errstate(invalid="ignore"):
        sigma = np.nanstd(muestra.crudo, axis=0)
    return np.where(sigma <= 1e-12, np.nan, sigma)


def alfa_global(muestra: Muestra) -> Tuple[np.ndarray, float]:
    """α de Davidson estimado sobre TODO el universo, normalizado a media 1 (ancla del piloto)."""
    indices = np.arange(muestra.n)
    z = estandarizar(muestra.crudo, indices)
    dims = puntajes(z, muestra.celdas, muestra.dimension_de, muestra.delta_alt)
    alfa = ajustar_davidson(dims, muestra.y, 0.02, np.asarray(ANCLA_FACTIBLE, dtype=float))[:6]
    escala = float(np.mean(alfa))
    return alfa / escala, escala


def geometria(
    muestra: Muestra,
    alfa: np.ndarray,
    sigma: np.ndarray,
    local: np.ndarray,
    visita: np.ndarray,
    bilateral: np.ndarray,
    celdas_activas: Optional[Sequence[str]] = None,
) -> Geometria:
    """Construye w, lo, hi con las MISMAS reglas del piloto, restringidas a las celdas activas."""
    celdas = list(muestra.celdas)
    if celdas_activas is None:
        activas = list(range(len(celdas)))
    else:
        activas = [celdas.index(c) for c in celdas_activas if c in celdas]
    observado = ~np.isnan(muestra.crudo)
    n, c = muestra.crudo.shape
    w = np.zeros((n, c), dtype=float)
    for indice in activas:
        dimension = muestra.dimension_de[celdas[indice]]
        posicion = DIMENSIONES.index(dimension)
        if alfa[posicion] <= 0.0:
            continue
        for partido in range(n):
            if not observado[partido, indice]:
                continue
            n_obs = sum(
                1
                for otra in activas
                if observado[partido, otra]
                and muestra.dimension_de[celdas[otra]] == dimension
            )
            w[partido, indice] = alfa[posicion] / max(n_obs, 1)

    lo = np.full((n, c), -CAP_SIGMA, dtype=float)
    hi = np.full((n, c), CAP_SIGMA, dtype=float)
    for indice in activas:
        if bilateral[indice]:
            lo[:, indice] = np.maximum(-2.0 * local[:, indice] / sigma[indice], -CAP_SIGMA)
            hi[:, indice] = np.minimum(2.0 * visita[:, indice] / sigma[indice], CAP_SIGMA)
        else:
            lo[:, indice] = np.maximum(-local[:, indice] / sigma[indice], -CAP_SIGMA)
    lo = np.where(np.isnan(lo), 0.0, lo)
    hi = np.where(np.isnan(hi), 0.0, hi)
    lo = np.minimum(lo, 0.0)
    hi = np.maximum(hi, 0.0)
    lo = np.where(observado, lo, 0.0)
    hi = np.where(observado, hi, 0.0)
    inactivas = [j for j in range(c) if j not in activas]
    if inactivas:
        lo[:, inactivas] = 0.0
        hi[:, inactivas] = 0.0
        w[:, inactivas] = 0.0
    return Geometria(w=w, lo=lo, hi=hi, observado=observado, activas=activas)


def normas_por_tau(
    muestra: Muestra,
    geo: Geometria,
    taus: Sequence[float],
    mascara: Optional[np.ndarray] = None,
) -> List[ResultadoTau]:
    """Resuelve la deformación mínima de cada partido para cada τ."""
    base = np.ones(muestra.n, dtype=bool) if mascara is None else np.asarray(mascara, bool)
    # La evidencia de una ablación es la de sus celdas ACTIVAS: un partido sin V06 no es
    # "inalcanzable" en la ablación V06, es ausencia declarada.
    if geo.activas:
        con_evidencia = np.any(geo.observado[:, geo.activas], axis=1)
    else:
        con_evidencia = np.zeros(muestra.n, dtype=bool)
    indice_resultado = np.argmax(muestra.y, axis=1)
    resultados: List[ResultadoTau] = []
    for tau in taus:
        deltas = np.zeros_like(geo.w)
        normas = np.zeros(muestra.n, dtype=float)
        validos = base & con_evidencia
        inalcanzables: List[str] = []
        sin_evidencia: List[str] = []
        saturados = 0
        for partido in np.where(base)[0]:
            if not con_evidencia[partido]:
                sin_evidencia.append(muestra.ids[partido])
                continue
            v = direccion_objetivo(int(indice_resultado[partido]))
            try:
                s_objetivo = biseccion_s(
                    tau, muestra.p_base[partido], v, int(indice_resultado[partido])
                )
                delta = resolver_lambda(
                    s_objetivo,
                    geo.w[partido],
                    geo.lo[partido],
                    geo.hi[partido],
                    muestra.ids[partido],
                )
            except BordeInfactible:
                inalcanzables.append(muestra.ids[partido])
                validos[partido] = False
                continue
            deltas[partido] = delta
            normas[partido] = float(np.sqrt(np.sum(delta ** 2)))
            if np.any(np.abs(delta) >= CAP_SIGMA - 1e-9):
                saturados += 1
        resultados.append(
            ResultadoTau(
                tau=float(tau),
                deltas=deltas,
                normas=normas,
                validos=validos,
                inalcanzables=inalcanzables,
                sin_evidencia=sin_evidencia,
                saturados=saturados,
            )
        )
    return resultados


def _stats(valores: np.ndarray) -> Dict[str, Any]:
    if valores.size == 0:
        return {
            "n": 0,
            "sigma_mediana": None,
            "sigma_p90": None,
            "sigma_max": None,
            "sigma_media": None,
        }
    return {
        "n": int(valores.size),
        "sigma_mediana": round(float(np.median(valores)), 6),
        "sigma_p90": round(float(np.quantile(valores, 0.90)), 6),
        "sigma_max": round(float(valores.max()), 6),
        "sigma_media": round(float(valores.mean()), 6),
    }


# ═════════════════════════════════════════════════════════════════════════════════════════════
# BOOTSTRAP DE BLOQUES — IC 95% de la mediana (no reajusta α)
# ═════════════════════════════════════════════════════════════════════════════════════════════
def bloques_de_jornada(muestra: Muestra) -> np.ndarray:
    """Bloque = (temporada, jornada). En J14 (una sola temporada) equivale a jornada."""
    temporadas = list(muestra.temporadas) if muestra.temporadas else [""] * muestra.n
    if len(set(temporadas)) > 1:
        return np.asarray([f"{t}|{int(j)}" for t, j in zip(temporadas, muestra.jornadas)])
    return np.asarray([str(int(j)) for j in muestra.jornadas])


def bootstrap_mediana(
    valores: np.ndarray,
    bloques: np.ndarray,
    n_boot: int,
    semilla: int,
) -> Optional[List[float]]:
    """IC 95% percentil de la mediana por remuestreo de bloques completos."""
    if n_boot <= 0 or valores.size == 0:
        return None
    unicos = sorted(set(bloques.tolist()))
    indices = [np.where(bloques == bloque)[0] for bloque in unicos]
    generador = np.random.default_rng(semilla)
    medianas = np.empty(n_boot, dtype=float)
    for remuestreo in range(n_boot):
        elegidos = generador.integers(0, len(unicos), len(unicos))
        reunion = np.concatenate([valores[indices[j]] for j in elegidos])
        medianas[remuestreo] = np.median(reunion)
    return [
        round(float(np.quantile(medianas, 0.025)), 6),
        round(float(np.quantile(medianas, 0.975)), 6),
    ]


# ═════════════════════════════════════════════════════════════════════════════════════════════
# PARTICIONES Y DECOMPOSICIÓN
# ═════════════════════════════════════════════════════════════════════════════════════════════
def particiones(muestra: Muestra, estratificar: Optional[str]) -> Dict[str, np.ndarray]:
    total = np.ones(muestra.n, dtype=bool)
    if estratificar == "procedencia_xg":
        opta = np.asarray(muestra.opta, dtype=bool)
        return {"total": total, "opta": opta, "non_opta": ~opta}
    return {"total": total}


def deformacion_por_celda(
    muestra: Muestra, resultado: ResultadoTau, mascara: np.ndarray
) -> Dict[str, Dict[str, float]]:
    validos = resultado.validos & mascara
    deltas = resultado.deltas[validos]
    if deltas.size == 0:
        return {
            celda: {"media_abs_delta": 0.0, "share_norma2": 0.0} for celda in muestra.celdas
        }
    media = np.mean(np.abs(deltas), axis=0)
    cuadrados = np.sum(deltas ** 2, axis=0)
    total = float(cuadrados.sum())
    return {
        celda: {
            "media_abs_delta": round(float(media[j]), 6),
            "share_norma2": round(float(cuadrados[j] / total) if total > 0 else 0.0, 6),
        }
        for j, celda in enumerate(muestra.celdas)
    }


def descomposicion(
    muestra: Muestra, resultado: ResultadoTau, mascara: np.ndarray
) -> Dict[str, float]:
    validos = resultado.validos & mascara
    deltas = resultado.deltas[validos]
    if deltas.size == 0:
        return {clave: 0.0 for clave in ("V06", "V12", "V26_V29_V30", "resto")}
    cuadrados = np.sum(deltas ** 2, axis=0)
    total = float(cuadrados.sum())
    indice = {celda: j for j, celda in enumerate(muestra.celdas)}

    def _share(celdas: Sequence[str]) -> float:
        if total <= 0:
            return 0.0
        return round(float(sum(cuadrados[indice[c]] for c in celdas if c in indice) / total), 6)

    v26 = _share([c for c in ("V26", "V29", "V30") if c in indice])
    v12 = _share(["V12"])
    v06 = _share(["V06"])
    return {
        "V06": v06,
        "V12": v12,
        "V26_V29_V30": v26,
        "resto": round(max(0.0, 1.0 - v06 - v12 - v26), 6),
    }


# ═════════════════════════════════════════════════════════════════════════════════════════════
# OUTLIERS
# ═════════════════════════════════════════════════════════════════════════════════════════════
def outliers(
    muestra: Muestra, resultado: ResultadoTau, n: int
) -> Dict[str, Any]:
    indices = np.where(resultado.validos)[0]
    orden = indices[np.argsort(-resultado.normas[indices])]
    temporadas = list(muestra.temporadas) if muestra.temporadas else [""] * muestra.n
    normas_validas = resultado.normas[resultado.validos]
    total_cuadrados = float(np.sum(normas_validas ** 2))
    top_cuadrados = float(np.sum(resultado.normas[orden[:n]] ** 2))
    bottom_cuadrados = float(np.sum(resultado.normas[orden[-n:]] ** 2))

    def _fila(indice: int) -> Dict[str, Any]:
        fila = resultado.deltas[indice]
        top = np.argsort(-np.abs(fila))[:3]
        return {
            "id_partido": muestra.ids[indice],
            "temporada": temporadas[indice],
            "jornada": int(muestra.jornadas[indice]),
            "resultado": muestra.resultados[indice],
            "norma_sigma": round(float(resultado.normas[indice]), 6),
            "n_celdas_observadas": int(np.sum(~np.isnan(muestra.crudo[indice]))),
            "celdas_dominantes": [
                {"celda": muestra.celdas[j], "delta_sigma": round(float(fila[j]), 6)}
                for j in top
                if abs(float(fila[j])) > 1e-12
            ],
        }

    return {
        "tau": resultado.tau,
        "n_evaluados": int(indices.size),
        "n_sin_evidencia_excluidos": int(
            np.sum((~resultado.validos) & (np.sum(~np.isnan(muestra.crudo), axis=1) == 0))
        ),
        "concentracion_top": round(top_cuadrados / total_cuadrados, 6)
        if total_cuadrados > 0
        else None,
        "concentracion_bottom": round(bottom_cuadrados / total_cuadrados, 6)
        if total_cuadrados > 0
        else None,
        "top": [_fila(int(i)) for i in orden[:n]],
        "bottom": [_fila(int(i)) for i in orden[-n:][::-1]],
    }


# ═════════════════════════════════════════════════════════════════════════════════════════════
# MODELO NULO — P_null uniforme, misma geometría de pesos y cotas simétricas
# ═════════════════════════════════════════════════════════════════════════════════════════════
def modelo_nulo(
    muestra: Muestra, geo: Geometria, taus: Sequence[float]
) -> List[Dict[str, Any]]:
    uniforme = np.full(3, 1.0 / 3.0)
    indice_resultado = np.argmax(muestra.y, axis=1)
    con_evidencia = geo.observado.sum(axis=1) > 0
    lo = np.where(geo.observado, -CAP_SIGMA, 0.0)
    hi = np.where(geo.observado, CAP_SIGMA, 0.0)
    filas: List[Dict[str, Any]] = []
    for tau in taus:
        normas = np.zeros(muestra.n, dtype=float)
        inalcanzables = 0
        for partido in np.where(con_evidencia)[0]:
            v = direccion_objetivo(int(indice_resultado[partido]))
            try:
                s_objetivo = biseccion_s(tau, uniforme, v, int(indice_resultado[partido]))
                delta = resolver_lambda(
                    s_objetivo, geo.w[partido], lo[partido], hi[partido], muestra.ids[partido]
                )
            except BordeInfactible:
                inalcanzables += 1
                continue
            normas[partido] = float(np.sqrt(np.sum(delta ** 2)))
        validos = con_evidencia & (normas > 0)
        mediana = float(np.median(normas[validos])) if validos.any() else float("nan")
        filas.append(
            {"tau": float(tau), "sigma_null_mediana": round(mediana, 6),
             "n": int(validos.sum()), "n_inalcanzables": int(inalcanzables),
             "normas": normas, "validos": validos}
        )
    return filas


# ═════════════════════════════════════════════════════════════════════════════════════════════
# K-FOLD (sólo D)
# ═════════════════════════════════════════════════════════════════════════════════════════════
def kfold_alfa_sigma(
    muestra: Muestra,
    taus: Sequence[float],
    local: np.ndarray,
    visita: np.ndarray,
    bilateral: np.ndarray,
    n_folds: int,
    tau_principal: float,
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    celdas_objetivo = ["V12", "V14", "V15", "V17", "V18", "V19", "V20", "V29"]
    folds = _folds(muestra.jornadas, n_folds)
    alfa_folds: List[np.ndarray] = []
    celda_folds: List[Dict[str, float]] = []
    curva_folds: List[List[Dict[str, Any]]] = []
    detalle: List[Dict[str, Any]] = []
    for numero, prueba in enumerate(folds):
        ajuste = ~prueba
        z = estandarizar(muestra.crudo, np.where(ajuste)[0])
        dims = puntajes(z, muestra.celdas, muestra.dimension_de, muestra.delta_alt)
        alfa_crudo = ajustar_davidson(
            dims[ajuste], muestra.y[ajuste], 0.02, np.asarray(ANCLA_FACTIBLE, dtype=float)
        )[:6]
        alfa = alfa_crudo / float(np.mean(alfa_crudo))
        with np.errstate(invalid="ignore"):
            sigma_train = np.nanstd(muestra.crudo[ajuste], axis=0)
        sigma_train = np.where(sigma_train <= 1e-12, np.nan, sigma_train)
        geo = geometria(muestra, alfa, sigma_train, local, visita, bilateral)
        resultados = normas_por_tau(muestra, geo, taus, mascara=prueba)
        principal = next(r for r in resultados if math.isclose(r.tau, tau_principal))
        por_celda = deformacion_por_celda(muestra, principal, prueba)
        alfa_folds.append(alfa)
        celda_folds.append(
            {celda: float(por_celda[celda]["media_abs_delta"]) for celda in celdas_objetivo}
        )
        curva_folds.append(
            [
                {"tau": r.tau, "n": int(r.validos.sum()), **_stats(r.normas[r.validos])}
                for r in resultados
            ]
        )
        detalle.append(
            {
                "fold": numero + 1,
                "jornadas_test": sorted({int(j) for j in muestra.jornadas[prueba]}),
                "n_train": int(ajuste.sum()),
                "n_test": int(prueba.sum()),
                "alfa": [round(float(v), 6) for v in alfa],
                "alfa_Por": round(float(alfa[DIMENSIONES.index("𝒯_Por")]), 6),
                "sigma_por_celda": {
                    celda: round(float(valor), 6) for celda, valor in celda_folds[-1].items()
                },
            }
        )

    alfa_matriz = np.asarray(alfa_folds, dtype=float)
    resumen_alfa = {
        dimension: {
            "mean": round(float(np.mean(alfa_matriz[:, j])), 6),
            "std": round(float(np.std(alfa_matriz[:, j], ddof=1)), 6),
        }
        for j, dimension in enumerate(DIMENSIONES)
    }
    alfa_por = alfa_matriz[:, DIMENSIONES.index("𝒯_Por")]
    resumen_alfa["alfa_Por"] = {
        "mean": round(float(np.mean(alfa_por)), 6),
        "std": round(float(np.std(alfa_por, ddof=1)), 6),
        "cv": round(float(np.std(alfa_por, ddof=1) / np.mean(alfa_por)), 6)
        if np.mean(alfa_por) != 0
        else None,
    }

    resumen_sigma: Dict[str, Dict[str, Any]] = {}
    for celda in celdas_objetivo:
        valores = np.asarray([fila[celda] for fila in celda_folds], dtype=float)
        resumen_sigma[celda] = {
            "mean": round(float(np.mean(valores)), 6),
            "std": round(float(np.std(valores, ddof=1)), 6),
        }

    kfold_alpha = {
        "kfold": n_folds,
        "dimensiones": list(DIMENSIONES),
        "por_fold": detalle,
        "resumen": resumen_alfa,
        "convencion": "α normalizado a media 1 sobre el train de cada fold",
    }
    kfold_sigma = {
        "kfold": n_folds,
        "tau_principal": tau_principal,
        "celdas": celdas_objetivo,
        "por_fold": [
            {"fold": i + 1, "sigma_media_por_celda": celda_folds[i], "curva": curva_folds[i]}
            for i in range(len(folds))
        ],
        "resumen": resumen_sigma,
        "convencion": "media de |Δ| por celda en el held-out de cada fold; mean/std entre folds",
    }
    return kfold_alpha, kfold_sigma, resumen_sigma


# ═════════════════════════════════════════════════════════════════════════════════════════════
# REPORTE
# ═════════════════════════════════════════════════════════════════════════════════════════════
def _linea() -> str:
    return "═" * ANCHO


def _tabla_curva(nombre: str, filas: List[Dict[str, Any]]) -> List[str]:
    lineas = [
        f"   {nombre}",
        "   τ       n       σ_mediana   σ_p90     σ_máx     sat    IC95%(mediana)",
    ]
    for fila in filas:
        ic = fila.get("ic95_mediana")
        ic_txt = f"[{ic[0]:.4f}, {ic[1]:.4f}]" if ic else "—"
        lineas.append(
            f"   {fila['tau']:.2f}   {fila['n']:>6}   {fila['sigma_mediana']:>9.4f}  "
            f"{fila['sigma_p90']:>7.4f}  {fila['sigma_max']:>7.4f}   "
            f"{fila.get('n_saturados', 0):>4}   {ic_txt}"
        )
    return lineas


def texto_console(
    corpus: str,
    muestra: Muestra,
    alfa: np.ndarray,
    escala: float,
    curvas: Dict[str, List[Dict[str, Any]]],
    celdas: Dict[str, Dict[str, Dict[str, float]]],
    ablaciones: Dict[str, List[Dict[str, Any]]],
    descomposicion_total: Dict[str, float],
    nulo: List[Dict[str, Any]],
    outliers_data: Optional[Dict[str, Any]],
    kfold_alpha: Optional[Dict[str, Any]],
    kfold_sigma: Optional[Dict[str, Any]],
    sha_despues: str,
) -> str:
    lineas = [
        _linea(),
        f"🔬 RERUN DOBLE — OPCIÓN {corpus} — FRAGILIDAD DE LA EVIDENCIA",
        f"   [LN-QBE-100] · [LN-QBE-120] · [LN-QBE-126] · [LN-QBE-127] · corpus {corpus}",
        _linea(),
        "",
        "0 · PARIDAD Y UNIVERSO",
        f"   Snapshot     : {muestra.ruta_snapshot}",
        f"   SHA-256      : {muestra.sha_snapshot}",
        f"   n            : {muestra.n}  (n_esperado {muestra.n_esperado})",
        f"   Evidencia    : {int(np.sum(np.sum(~np.isnan(muestra.crudo), axis=1) > 0))} con ≥1 celda"
        f" · {int(np.sum(np.sum(~np.isnan(muestra.crudo), axis=1) == 0))} sin evidencia",
        f"   Celdas       : {len(muestra.celdas)} · α = " + " ".join(f"{v:.3f}" for v in alfa)
        + f"  (escala bruta {escala:.3f})",
        f"   Brier ancla  : {brier(muestra.p_base, muestra.y):.6f}",
        "",
        "1 · CURVA DE FRAGILIDAD (σ para que el modelo acierte τ)",
    ]
    for particion, filas in curvas.items():
        lineas += _tabla_curva(f"[{particion}]", filas)
        lineas.append("")
    lineas += ["2 · DEFORMACIÓN MEDIA POR CELDA (τ principal)"]
    for particion, celdas_particion in celdas.items():
        orden = sorted(
            celdas_particion.items(), key=lambda par: -par[1]["media_abs_delta"]
        )
        lineas.append(f"   [{particion}]")
        for celda, valores in orden:
            if valores["media_abs_delta"] <= 1e-12:
                continue
            lineas.append(
                f"      {celda}: media|Δ| {valores['media_abs_delta']:.6f}  "
                f"share {valores['share_norma2'] * 100:.2f}%"
            )
    lineas += ["", "3 · FIXED/FREE — σ por ablación", "   ablación              τ       n      sat    σ_mediana   σ_p90"]
    for nombre, filas in ablaciones.items():
        for fila in filas:
            lineas.append(
                f"   {nombre:<21} {fila['tau']:.2f}   {fila['n']:>6}  "
                f"{fila.get('n_saturados', 0):>4}   "
                f"{fila['sigma_mediana']:>9.4f}  {fila['sigma_p90']:>7.4f}"
            )
    lineas.append(
        "   descomposición (share de ‖Δ‖²): "
        + " · ".join(f"{k} {v * 100:.2f}%" for k, v in descomposicion_total.items())
    )
    lineas += ["", "4 · MODELO NULO — P_null uniforme", "   τ       σ_QBE     σ_null    ratio"]
    for fila in nulo:
        lineas.append(
            f"   {fila['tau']:.2f}   {fila['sigma_qbe_mediana']:>8.4f}  "
            f"{fila['sigma_null_mediana']:>8.4f}  {fila['ratio']:>6.3f}"
        )
    if outliers_data:
        lineas += [
            "",
            f"5 · OUTLIERS (τ = {outliers_data['tau']:.2f}) — "
            f"top {min(10, len(outliers_data['top']))} de {len(outliers_data['top'])}",
        ]
        for fila in outliers_data["top"][:10]:
            celdas_txt = " · ".join(
                f"{c['celda']} {c['delta_sigma']:+.2f}" for c in fila["celdas_dominantes"]
            )
            lineas.append(
                f"   {fila['id_partido']:<18} {fila['temporada']:<22} J{fila['jornada']:<3} "
                f"‖Δ‖ {fila['norma_sigma']:>6.2f}   {celdas_txt}"
            )
    if kfold_alpha and kfold_sigma:
        lineas += ["", "6 · K-FOLD 5 — α y σ held-out"]
        lineas.append("   fold  α[Vol Rem Def Por Spc Ctx]                         α_Por   n_train n_test")
        for fila in kfold_alpha["por_fold"]:
            lineas.append(
                f"   {fila['fold']:>4}  " + " ".join(f"{v:.3f}" for v in fila["alfa"])
                + f"   {fila['alfa_Por']:.4f}   {fila['n_train']:>5}  {fila['n_test']:>5}"
            )
        lineas.append("   α resumen (mean ± std):")
        for dimension in DIMENSIONES:
            datos = kfold_alpha["resumen"][dimension]
            lineas.append(f"      {dimension:<8} {datos['mean']:.4f} ± {datos['std']:.4f}")
        lineas.append("   σ held-out por celda (mean ± std entre folds):")
        for celda, datos in kfold_sigma["resumen"].items():
            lineas.append(f"      {celda:<5} {datos['mean']:.4f} ± {datos['std']:.4f}")
    lineas += [
        "",
        "7 · PUREZA",
        f"   SHA-256 después: {sha_despues}",
        f"   Snapshot inmutable: {'IDÉNTICO' if sha_despues == muestra.sha_snapshot else 'CAMBIÓ 🚨'}",
        "   Read-only: cero INSERT/UPDATE/DELETE/COMMIT · cero red · cero cuota imputada",
        _linea(),
    ]
    return "\n".join(lineas)


# ═════════════════════════════════════════════════════════════════════════════════════════════
# EJECUCIÓN
# ═════════════════════════════════════════════════════════════════════════════════════════════
def _parsear_taus(valor: Optional[str]) -> Tuple[float, ...]:
    if not valor:
        return TAUS_PILOTO
    taus = sorted({float(parte) for parte in str(valor).split(",") if parte.strip()})
    if not taus:
        raise ValueError("--taus no declara ningún valor")
    return tuple(taus)


def ejecutar_rerun(argumentos: Any, ruta_snapshot: Path) -> int:
    corpus = "D" if argumentos.kfold else "B"
    taus = _parsear_taus(argumentos.taus)
    tau_principal = float(max(taus))
    n_fragiles = int(argumentos.n_fragiles or 10)
    n_boot = int(argumentos.bootstrap or 0)
    n_outliers = int(argumentos.outliers or 0)
    if n_outliers == 0 and argumentos.n_fragiles:
        n_outliers = n_fragiles
    salida = Path(argumentos.salida) if argumentos.salida else (
        RAIZ_PROYECTO / "data" / "output" / "rerun_20261030" / ("opcion_d" if corpus == "D" else "opcion_b")
    )
    salida.mkdir(parents=True, exist_ok=True)

    try:
        muestra = cargar_muestra(
            ruta_snapshot,
            n_esperado=argumentos.n_esperado,
            universo_completo=argumentos.universo_completo,
        )
        local, visita, bilateral = cargar_niveles(ruta_snapshot, muestra.ids, muestra.celdas)
        sigma = sigma_celdas(muestra)
        alfa, escala = alfa_global(muestra)
    except BordeInfactible as error:
        print(f"\n{error}\n", file=sys.stderr)
        return 4
    except FalloOptimizacion as error:
        print(f"\n{error}\n", file=sys.stderr)
        return 4
    if corpus == "D" and not any(muestra.temporadas):
        # J14 no porta `season_id` en la bóveda: la temporada declarada es el propio corte.
        muestra.temporadas = ["J14"] * muestra.n

    geo = geometria(muestra, alfa, sigma, local, visita, bilateral)
    resultados = normas_por_tau(muestra, geo, taus)
    principal = next(r for r in resultados if math.isclose(r.tau, tau_principal))
    mascaras = particiones(muestra, argumentos.estratificar)
    bloques = bloques_de_jornada(muestra)

    curvas: Dict[str, List[Dict[str, Any]]] = {}
    celdas: Dict[str, Dict[str, Dict[str, float]]] = {}
    for nombre, mascara in mascaras.items():
        filas = []
        for resultado in resultados:
            validos = resultado.validos & mascara
            fila = {"tau": resultado.tau, "n": int(validos.sum()), **_stats(resultado.normas[validos])}
            fila["n_inalcanzables"] = len(resultado.inalcanzables)
            fila["n_sin_evidencia"] = len(resultado.sin_evidencia)
            fila["n_saturados"] = resultado.saturados
            fila["ic95_mediana"] = bootstrap_mediana(
                resultado.normas[validos],
                bloques[validos],
                n_boot,
                SEMILLA_BOOTSTRAP + int(round(resultado.tau * 1000)) + len(nombre),
            )
            filas.append(fila)
        curvas[nombre] = filas
        celdas[nombre] = deformacion_por_celda(muestra, principal, mascara)

    ablaciones: Dict[str, List[Dict[str, Any]]] = {}
    if argumentos.fixed_free:
        for nombre, subconjunto in SUBCONJUNTOS_ABLACION.items():
            geo_ablacion = geometria(
                muestra, alfa, sigma, local, visita, bilateral, celdas_activas=subconjunto
            )
            filas = []
            for resultado in normas_por_tau(muestra, geo_ablacion, taus):
                validos = resultado.validos
                filas.append(
                    {
                        "tau": resultado.tau,
                        "n": int(validos.sum()),
                        "n_inalcanzables": len(resultado.inalcanzables),
                        "n_sin_evidencia": len(resultado.sin_evidencia),
                        "n_saturados": resultado.saturados,
                        **_stats(resultado.normas[validos]),
                    }
                )
            ablaciones[nombre] = filas

    descomposicion_total = descomposicion(muestra, principal, mascaras["total"])

    nulo: List[Dict[str, Any]] = []
    if argumentos.modelo_nulo:
        for fila in modelo_nulo(muestra, geo, taus):
            qbe = next(r for r in resultados if math.isclose(r.tau, fila["tau"]))
            validos_qbe = qbe.validos & fila["validos"]
            mediana_qbe = (
                float(np.median(qbe.normas[validos_qbe])) if validos_qbe.any() else float("nan")
            )
            ratio = (
                float(mediana_qbe / fila["sigma_null_mediana"])
                if fila["sigma_null_mediana"] and math.isfinite(fila["sigma_null_mediana"])
                else None
            )
            nulo.append(
                {
                    "tau": fila["tau"],
                    "n": fila["n"],
                    "sigma_qbe_mediana": round(mediana_qbe, 6),
                    "sigma_null_mediana": fila["sigma_null_mediana"],
                    "ratio": round(ratio, 6) if ratio is not None else None,
                }
            )

    outliers_data = outliers(muestra, principal, n_outliers) if n_outliers > 0 else None

    kfold_alpha = None
    kfold_sigma = None
    if argumentos.kfold:
        kfold_alpha, kfold_sigma, _ = kfold_alfa_sigma(
            muestra, taus, local, visita, bilateral, int(argumentos.kfold), tau_principal
        )

    sha_despues = sha256_archivo(Path(muestra.ruta_snapshot))
    texto = texto_console(
        corpus, muestra, alfa, escala, curvas, celdas, ablaciones,
        descomposicion_total, nulo, outliers_data, kfold_alpha, kfold_sigma, sha_despues,
    )
    print(texto)
    (salida / "reporte_consola.txt").write_text(texto + "\n", encoding="utf-8")

    comun = {
        "instrumento": "sandbox_distancia_borde",
        "corpus": corpus,
        "snapshot": {
            "ruta": muestra.ruta_snapshot,
            "sha256": muestra.sha_snapshot,
            "inmutable": sha_despues == muestra.sha_snapshot,
        },
        "n": muestra.n,
        "n_esperado": muestra.n_esperado,
        "taus": list(taus),
        "tau_principal": tau_principal,
        "alfa": [round(float(v), 6) for v in alfa],
        "escala_alfa": round(float(escala), 6),
        "estratificacion": argumentos.estratificar or "total",
        "metodo_bootstrap": (
            f"bloques (temporada, jornada); mediana; {n_boot} remuestreos"
            if n_boot > 0
            else "sin bootstrap"
        ),
    }
    (salida / "curva_fragilidad.json").write_text(
        json.dumps({**comun, "curvas": curvas}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (salida / "deformacion_por_celda.json").write_text(
        json.dumps(
            {**comun, "celdas": celdas, "descomposicion_total": descomposicion_total},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    if argumentos.fixed_free:
        (salida / "fixed_free.json").write_text(
            json.dumps({**comun, "ablaciones": ablaciones}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    if argumentos.modelo_nulo:
        (salida / "modelo_nulo.json").write_text(
            json.dumps({**comun, "por_tau": nulo}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    if outliers_data:
        (salida / "outliers.json").write_text(
            json.dumps(outliers_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    if corpus == "B":
        cuotas = muestra.resumen_cuotas or {}
        (salida / "brier_mercado.json").write_text(
            json.dumps(
                {
                    "n_total": muestra.n,
                    "brier_modelo_total": round(float(muestra.brier_base), 6),
                    "n_con_cuota": int(cuotas.get("n_con_cuota_historica", 0))
                    + int(cuotas.get("n_con_cuota_fixtures", 0)),
                    "brier_mercado": round(float(muestra.brier_mercado), 6)
                    if math.isfinite(float(muestra.brier_mercado))
                    else None,
                    "n_sin_cuota": int(cuotas.get("n_sin_cuota", 0)),
                    "fuente_cuotas": cuotas.get("fuente_cuotas", {}),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    if kfold_alpha and kfold_sigma:
        (salida / "kfold_alpha.json").write_text(
            json.dumps({**comun, **kfold_alpha}, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (salida / "kfold_sigma.json").write_text(
            json.dumps({**comun, **kfold_sigma}, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    print(f"\n📄 Artefactos exportados: {salida}")
    if sha_despues != muestra.sha_snapshot:
        print("\n🚨 El snapshot cambió durante la corrida. Abortado.", file=sys.stderr)
        return 2
    return 0
