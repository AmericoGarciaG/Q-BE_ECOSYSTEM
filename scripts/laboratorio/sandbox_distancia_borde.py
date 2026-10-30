# -*- coding: utf-8 -*-
"""
🧪 Q-BE LABORATORIO — DISTANCIA AL BORDE DE DECISIÓN (COUNTERFACTUAL MÍNIMO)

[LN-QBE-100] · [LN-QBE-120] · [LN-QBE-126] · [LN-QBE-127]
Kybern Framework v13.5 · Base de Gobierno: [HÍBRIDO DUAL-TRACK]

Responde UNA pregunta: ¿cuánto tendría que moverse la evidencia (X) para que la P′ canónica
acierte el desenlace con probabilidad τ? No es una optimización de pesos: es la DISTANCIA AL
BORDE de cada partido, con deformación de norma mínima.

    Ancla      : ΔX = 0 ⇒ P̃ ≡ P′ ⇒ Brier = 0.2159 (paridad exacta).
    Mapa       : u = ln P′ + s·v_y ,  s = Σ_dim α_dim · media(Δ de sus celdas observadas)
                 v_y = (+1,0,−1) LOCAL · (−½,+1,−½) EMPATE · (−1,0,+1) VISITANTE.
    Mínima norma: Δ_j = clamp(λ·w_j, lo_j, hi_j) con w_j = α_dim / n_obs_dim.
                 λ se resuelve por bisección (el problema es convexo y monótono).
    Física     : la matriz es DIFERENCIAL (local − visitante). La no-negatividad se impone
                 sobre los NIVELES: local + δ/2 ≥ 0 y visita − δ/2 ≥ 0, celda por celda.
    τ          : curva {0.50, 0.80, 0.95, 0.99}.

Read-only absoluto. La única escritura es el reporte JSON opcional.
Determinista: cero RNG, cerrada bajo bisección.

Uso:
    python -m scripts.laboratorio.sandbox_distancia_borde
    python -m scripts.laboratorio.sandbox_distancia_borde --json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
from sqlalchemy.orm import Session, sessionmaker

RAIZ_PROYECTO = Path(__file__).resolve().parents[2]
if str(RAIZ_PROYECTO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROYECTO))

from scripts.laboratorio.sandbox_arquetipos_vectores import (  # noqa: E402
    _distribuciones_vigentes,
    _indice_h2h_stats,
    _numero,
    _par_magnitudes,
)
from scripts.laboratorio.sandbox_optimizacion_gradiente import (  # noqa: E402
    RUTA_SNAPSHOT_DEFECTO,
    _motor_solo_lectura,
    ruta_reporte,
    sha256_archivo,
)
from scripts.laboratorio.sandbox_shadow_competitivo import (  # noqa: E402
    ANCLA_FACTIBLE,
    DIMENSIONES,
    ConteoNoCoincide,
    FalloOptimizacion,
    NOMBRE_DIMENSION,
    UniversoInsuficiente,
    ajustar_davidson,
    brier,
    cargar_muestra,
    davidson,
    estandarizar,
    puntajes,
)

# ── Curva de fragilidad ─────────────────────────────────────────────────────────────────────
TAUS: Tuple[float, ...] = (0.50, 0.80, 0.95, 0.99)
TAU_PRINCIPAL = 0.99
N_FRAGILES = 10
CAP_SIGMA = 8.0          # techo numérico de deformación (σ)
TOLERANCIA = 1e-12
RUTA_SALIDA_JSON = RAIZ_PROYECTO / "data" / "output" / "distancia_borde_reporte.json"
ANCHO = 100


class BordeInfactible(RuntimeError):
    """La bisección no encontró multiplicador factible dentro de las cotas físicas."""


# ═════════════════════════════════════════════════════════════════════════════════════════════
# NIVELES (local, visitante) — la física vive aquí, no en el diferencial
# ═════════════════════════════════════════════════════════════════════════════════════════════
def cargar_niveles(ruta_snapshot: Path, ids: Sequence[str], celdas: Sequence[str]):
    """
    Devuelve (local, visitante, bilateral) en crudo para las celdas seleccionadas.

    `bilateral = False` ⇒ celda de contexto: sólo tiene nivel propio en `local`.
    El diferencial se reconstruye como local − visitante (idéntico al de `cargar_muestra`).
    """
    from app.routes.backtesting import _construir_reporte_calibracion

    motor = _motor_solo_lectura(Path(ruta_snapshot).resolve())
    sesion = sessionmaker(bind=motor)()
    try:
        reporte = _construir_reporte_calibracion(sesion, league_id=1)
        micro = [p for jornada in reporte.get("jornadas", []) for p in jornada["partidos"]]
        orden = {str(p["id_partido"]): p for p in micro}
        soberanas = _distribuciones_vigentes(sesion)
        h2h = _indice_h2h_stats(sesion)
    finally:
        sesion.close()
        motor.dispose()

    if [str(p["id_partido"]) for p in micro] != list(ids):
        raise RuntimeError("🚨 El orden de partidos del Visor cambió: no se puede alinear X.")

    local = np.full((len(ids), len(celdas)), np.nan)
    visita = np.full((len(ids), len(celdas)), np.nan)
    bilateral = np.zeros(len(celdas), dtype=bool)
    for indice, match_id in enumerate(ids):
        distribucion = soberanas.get(match_id)
        if distribucion is None:
            continue
        traza = distribucion.audit_trace_json if isinstance(distribucion.audit_trace_json, dict) else {}
        insumos = traza.get("insumos_factivados")
        if not isinstance(insumos, dict):
            continue
        for columna, celda in enumerate(celdas):
            valor_local, valor_visita, es_bilateral = _par_magnitudes(
                insumos, h2h.get(match_id, {}), celda
            )
            bilateral[columna] = bool(es_bilateral)
            if valor_local is not None:
                local[indice, columna] = float(valor_local)
            if es_bilateral and valor_visita is not None:
                visita[indice, columna] = float(valor_visita)
    return local, visita, bilateral


# ═════════════════════════════════════════════════════════════════════════════════════════════
# MAPA ANCLADO — Δ = 0 reproduce P′ exactamente
# ═════════════════════════════════════════════════════════════════════════════════════════════
def direccion_objetivo(indice_resultado: int) -> np.ndarray:
    """Vector v_y que empuja la probabilidad del desenlace observado."""
    if indice_resultado == 0:      # LOCAL
        return np.array([1.0, 0.0, -1.0])
    if indice_resultado == 1:      # EMPATE
        return np.array([-0.5, 1.0, -0.5])
    return np.array([-1.0, 0.0, 1.0])  # VISITANTE


def probabilidad_con_desplazamiento(p_base: np.ndarray, desplazamiento: float, v: np.ndarray) -> np.ndarray:
    """P̃ = softmax(ln P′ + s·v). Con s = 0 devuelve P′ (ancla identidad)."""
    logits = np.log(np.clip(p_base, 1e-15, 1.0)) + desplazamiento * v[None, :]
    logits -= logits.max(axis=1, keepdims=True)
    exp = np.exp(logits)
    return exp / exp.sum(axis=1, keepdims=True)


def biseccion_s(objetivo: float, p_fila: np.ndarray, v: np.ndarray, indice: int) -> float:
    """Desplazamiento s ≥ 0 mínimo que lleva P_y a τ (monótono)."""
    if float(p_fila[indice]) >= objetivo:
        return 0.0
    bajo, alto = 0.0, 1.0
    for _ in range(200):  # amplía el intervalo
        if float(probabilidad_con_desplazamiento(p_fila[None, :], alto, v)[0, indice]) >= objetivo:
            break
        alto *= 2.0
        if alto > 1e6:
            raise BordeInfactible("🚨 El objetivo τ no se alcanza ni con s = 1e6.")
    for _ in range(200):
        medio = 0.5 * (bajo + alto)
        if float(probabilidad_con_desplazamiento(p_fila[None, :], medio, v)[0, indice]) < objetivo:
            bajo = medio
        else:
            alto = medio
        if alto - bajo < TOLERANCIA:
            break
    return 0.5 * (bajo + alto)


def resolver_lambda(
    s_objetivo: float,
    w: np.ndarray,
    lo: np.ndarray,
    hi: np.ndarray,
    match_id: str,
) -> np.ndarray:
    """
    Water-filling monótono: Δ_j(λ) = clamp(λ·w_j, lo_j, hi_j), λ tal que Σ w_j Δ_j = s*.

    Es la solución EXACTA de min ‖Δ‖² s.a. Σ w Δ = s* y cotas de caja (multiplicador único).
    """
    def suma(lam: float) -> float:
        return float(np.sum(w * np.clip(lam * w, lo, hi)))

    if s_objetivo <= 0.0:
        return np.zeros_like(w)
    if suma(1e6) < s_objetivo - 1e-9:
        raise BordeInfactible(
            f"🚨 {match_id}: ni saturando todas las cotas se alcanza s* = {s_objetivo:.4f}."
        )
    bajo, alto = 0.0, 1.0
    while suma(alto) < s_objetivo:
        alto *= 2.0
        if alto > 1e6:
            raise BordeInfactible(f"🚨 {match_id}: bisección de λ no acota.")
    for _ in range(300):
        medio = 0.5 * (bajo + alto)
        if suma(medio) < s_objetivo:
            bajo = medio
        else:
            alto = medio
        if alto - bajo < 1e-15:
            break
    lam = 0.5 * (bajo + alto)
    return np.clip(lam * w, lo, hi)


# ═════════════════════════════════════════════════════════════════════════════════════════════
# EXPERIMENTO
# ═════════════════════════════════════════════════════════════════════════════════════════════
@dataclass
class ResultadoTau:
    tau: float
    deltas: np.ndarray          # (N, C) deformación en σ
    desplazamientos: np.ndarray  # (N,)
    brier_final: float
    brier_evidencia: float
    n_evidencia: int
    ya_correctos: int
    inalcanzables: List[str]
    sin_evidencia: List[str]


def ejecutar(
    ruta_snapshot: Path,
    n_esperado: Optional[int] = None,
    universo_completo: bool = False,
) -> Dict[str, Any]:
    muestra = cargar_muestra(
        ruta_snapshot, n_esperado=n_esperado, universo_completo=universo_completo
    )
    local, visita, bilateral = cargar_niveles(ruta_snapshot, muestra.ids, muestra.celdas)

    # Diferencial reconstruido: debe coincidir con la matriz certificada (cero imputación).
    # Bilateral sin ambos niveles ⇒ NaN (jamás se toma un lado como si fuera el diferencial).
    diferencial = np.where(bilateral[None, :], local - visita, local)
    if not np.allclose(np.nan_to_num(diferencial, nan=0.0), np.nan_to_num(muestra.crudo, nan=0.0), atol=1e-9):
        raise RuntimeError("🚨 Las celdas reconstruidas no coinciden con la matriz certificada.")

    # Estandarización GLOBAL (no hay predicción: se describe una geometría).
    indices = np.arange(muestra.n)
    z = estandarizar(muestra.crudo, indices)
    dims = puntajes(z, muestra.celdas, muestra.dimension_de, muestra.delta_alt)
    alfa = ajustar_davidson(dims, muestra.y, 0.02, np.asarray(ANCLA_FACTIBLE, dtype=float))[:6]
    escala = float(np.mean(alfa))
    alfa = alfa / escala  # convención: media 1 ⇒ 1σ de evidencia = 1 logit·participación

    with np.errstate(invalid="ignore"):
        media = np.nanmean(muestra.crudo, axis=0)
        sigma = np.nanstd(muestra.crudo, axis=0)
    sigma = np.where(sigma <= 1e-12, np.nan, sigma)

    # Pesos por celda: la dimensión reparte su α entre las celdas OBSERVADAS de cada partido.
    observado = ~np.isnan(muestra.crudo)
    w = np.zeros_like(muestra.crudo)
    for indice, celda in enumerate(muestra.celdas):
        dimension = muestra.dimension_de[celda]
        posicion = DIMENSIONES.index(dimension)
        for partido in range(muestra.n):
            if not observado[partido, indice]:
                continue
            n_obs = sum(
                1
                for otra in range(len(muestra.celdas))
                if observado[partido, otra] and muestra.dimension_de[muestra.celdas[otra]] == dimension
            )
            w[partido, indice] = alfa[posicion] / max(n_obs, 1)

    # Cotas físicas en σ: la no-negatividad se impone a los NIVELES (local ± δ/2, visita ∓ δ/2).
    lo = np.full_like(w, -CAP_SIGMA)
    hi = np.full_like(w, CAP_SIGMA)
    for indice in range(len(muestra.celdas)):
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

    indice_resultado = np.argmax(muestra.y, axis=1)
    con_evidencia = observado.sum(axis=1) > 0
    resultados: List[ResultadoTau] = []
    for tau in TAUS:
        deltas = np.zeros_like(w)
        desplazamientos = np.zeros(muestra.n)
        inalcanzables: List[str] = []
        sin_evidencia: List[str] = []
        for partido in range(muestra.n):
            if not con_evidencia[partido]:
                # Sin una sola celda observada no existe X que mover: el ancla es inamovible.
                sin_evidencia.append(muestra.ids[partido])
                continue
            v = direccion_objetivo(int(indice_resultado[partido]))
            try:
                s_objetivo = biseccion_s(
                    tau, muestra.p_base[partido], v, int(indice_resultado[partido])
                )
                delta = resolver_lambda(
                    s_objetivo, w[partido], lo[partido], hi[partido], muestra.ids[partido]
                )
            except BordeInfactible:
                inalcanzables.append(muestra.ids[partido])
                continue
            deltas[partido] = delta
            desplazamientos[partido] = float(np.sum(w[partido] * delta))
        probabilidades = np.vstack(
            [
                probabilidad_con_desplazamiento(
                    muestra.p_base[i], desplazamientos[i], direccion_objetivo(int(indice_resultado[i]))
                )
                for i in range(muestra.n)
            ]
        )
        resultados.append(
            ResultadoTau(
                tau=tau,
                deltas=deltas,
                desplazamientos=desplazamientos,
                brier_final=float(brier(probabilidades, muestra.y)),
                brier_evidencia=float(brier(probabilidades[con_evidencia], muestra.y[con_evidencia])),
                n_evidencia=int(con_evidencia.sum()),
                ya_correctos=int(
                    np.sum(
                        muestra.p_base[np.arange(muestra.n), indice_resultado][con_evidencia] >= tau
                    )
                ),
                inalcanzables=inalcanzables,
                sin_evidencia=sin_evidencia,
            )
        )

    return {
        "muestra": muestra,
        "alfa": alfa,
        "escala_alfa": escala,
        "w": w,
        "lo": lo,
        "hi": hi,
        "sigma": sigma,
        "local": local,
        "resultados": resultados,
    }


# ═════════════════════════════════════════════════════════════════════════════════════════════
# REPORTE
# ═════════════════════════════════════════════════════════════════════════════════════════════
def _linea() -> str:
    return "═" * ANCHO


def _normas(deltas: np.ndarray) -> np.ndarray:
    return np.sqrt(np.sum(deltas ** 2, axis=1))


def imprimir(datos: Dict[str, Any], sha_despues: str) -> None:
    muestra = datos["muestra"]
    resultados: List[ResultadoTau] = datos["resultados"]
    principal = next(r for r in resultados if math.isclose(r.tau, TAU_PRINCIPAL))
    normas = _normas(principal.deltas)

    lineas = [
        _linea(),
        "🎯 DISTANCIA AL BORDE DE DECISIÓN — counterfactual mínimo sobre la P′ canónica",
        "   [LN-QBE-100] Brier · ancla identidad · min ‖ΔX‖² s.a. P̃_y ≥ τ · [HÍBRIDO DUAL-TRACK]",
        _linea(),
        "",
        "0 · PARIDAD Y MAPA",
        f"   Snapshot     : {muestra.ruta_snapshot}",
        f"   SHA-256      : {muestra.sha_snapshot[:32]}…",
        f"   Matriz       : {muestra.n} × {len(muestra.celdas)} (celdas con β_suficiencia)",
        f"   Brier ancla  : {brier(muestra.p_base, muestra.y):.4f}  (ΔX = 0 ⇒ P̃ ≡ P′)",
        f"   α fijos      : " + " ".join(f"{v:.2f}" for v in datos["alfa"]),
        f"                  (media 1; escala bruta {datos['escala_alfa']:.3f})",
        "   Mapa         : u = ln P′ + s·v_y · v_y = (+1,0,−1) / (−½,+1,−½) / (−1,0,+1)",
        "   Física       : niveles local ± δ/2 ≥ 0 y visita ∓ δ/2 ≥ 0 (celda por partido)",
        "",
        "1 · CURVA DE FRAGILIDAD (σ necesarias para que el modelo acierte)",
        "   τ       σ mediana   σ P90    σ máx    ya ≥ τ    Brier 124   Brier 115",
    ]
    con_evidencia = ~np.all(np.isnan(muestra.crudo), axis=1)
    for resultado in resultados:
        fila_normas = _normas(resultado.deltas)[con_evidencia]
        lineas.append(
            f"   {resultado.tau:.2f}    {np.median(fila_normas):>9.2f}  {np.quantile(fila_normas, 0.90):>7.2f}"
            f"  {fila_normas.max():>7.2f}  {resultado.ya_correctos:>4}/{resultado.n_evidencia}"
            f"  {resultado.brier_final:>10.4f}  {resultado.brier_evidencia:>9.4f}"
        )

    lineas += [
        "",
        f"2 · TOP {N_FRAGILES} PARTIDOS MÁS FRÁGILES (τ = {TAU_PRINCIPAL:.2f})",
        "   partido            J   real       P′_y    ‖Δ‖σ   Top 3 celdas (Δσ)",
    ]
    orden = np.argsort(-normas)[:N_FRAGILES]
    for partido in orden:
        v = direccion_objetivo(int(np.argmax(muestra.y[partido])))
        p_y = float(probabilidad_con_desplazamiento(muestra.p_base[partido][None, :], 0.0, v)[0, np.argmax(muestra.y[partido])])
        fila = principal.deltas[partido]
        top = np.argsort(-np.abs(fila))[:3]
        detalle = " · ".join(
            f"{muestra.celdas[j]} {fila[j]:+.2f}" for j in top if abs(fila[j]) > 1e-9
        )
        if not detalle:
            detalle = "sin movimiento (ya ≥ τ)"
        lineas.append(
            f"   {muestra.ids[partido]:<18} {int(muestra.jornadas[partido]):>2}   "
            f"{muestra.resultados[partido]:<10} {p_y:>6.3f}  {normas[partido]:>6.2f}   {detalle}"
        )

    medias = np.nanmean(np.abs(principal.deltas), axis=0)
    orden_celdas = np.argsort(-medias)
    local = datos["local"]
    lineas += [
        "",
        "3 · DEFORMACIÓN MEDIA POR CELDA (τ = 0.99)",
        "   celda · dimensión                       |Δσ|    Δ crudo    × nivel local",
    ]
    for j in orden_celdas[:8]:
        dimension = muestra.dimension_de[muestra.celdas[j]]
        sigma_j = datos["sigma"][j]
        delta_crudo = float(np.mean(principal.deltas[:, j]) * sigma_j)
        multiplicadores = []
        for i in range(muestra.n):
            nivel = local[i, j]
            if np.isnan(nivel) or abs(nivel) <= 1e-6:
                continue
            multiplicadores.append((nivel + principal.deltas[i, j] * sigma_j / 2.0) / nivel)
        factor = float(np.mean(multiplicadores)) if multiplicadores else float("nan")
        lineas.append(
            f"   {muestra.celdas[j]} · {NOMBRE_DIMENSION.get(dimension, dimension):<28} "
            f"{medias[j]:>6.2f}  {delta_crudo:>+9.2f}   ×{factor:>6.3f}"
        )

    inertes = [muestra.celdas[j] for j in range(len(muestra.celdas)) if medias[j] <= 1e-9]
    resultado_95 = next(r for r in resultados if math.isclose(r.tau, 0.95))
    lineas += [
        "",
        "4 · CELDAS INERTES, SIN EVIDENCIA E INALCANZABLES",
        f"   Inertes (nunca se movieron): {', '.join(inertes) if inertes else 'ninguna'}",
        f"   Sin evidencia (0 celdas, X inamovible): {len(principal.sin_evidencia)}"
        f" · {', '.join(principal.sin_evidencia) if principal.sin_evidencia else 'ninguno'}",
        f"   Inalcanzables τ=0.99 (saturan cotas): "
        f"{', '.join(principal.inalcanzables) if principal.inalcanzables else 'ninguno'}",
        f"   Inalcanzables τ=0.95 (saturan cotas): "
        f"{', '.join(resultado_95.inalcanzables) if resultado_95.inalcanzables else 'ninguno'}",
        f"   Brier 115 (con evidencia) a τ=0.99: {principal.brier_evidencia:.6f}",
        "",
        "5 · PUREZA",
        f"   Snapshot inmutable: SHA-256 {'IDÉNTICO' if sha_despues == muestra.sha_snapshot else 'CAMBIÓ 🚨'}",
        "   Read-only: cero INSERT/UPDATE/DELETE/COMMIT · P′ canónica solo como ancla",
        "",
        _linea(),
    ]
    print("\n".join(lineas))


# ═════════════════════════════════════════════════════════════════════════════════════════════
# PRE-VUELO — [P0 #3] --dry-run: carga, verifica, imprime y sale (cero análisis)
# ═════════════════════════════════════════════════════════════════════════════════════════════
def _imprimir_dry_run(muestra, sha_despues: str) -> int:
    """[P0 #3.1] Verificación de carga: no se ejecuta bisección, λ, Davidson ni se reporta σ."""
    observado = ~np.isnan(muestra.crudo)
    n_con_evidencia = int((observado.sum(axis=1) > 0).sum())
    n_sin_evidencia = muestra.n - n_con_evidencia
    lineas = [
        _linea(),
        "🎯 DRY-RUN — DISTANCIA AL BORDE (solo carga y verificación)",
        _linea(),
        f"   Snapshot          : {muestra.ruta_snapshot}",
        f"   SHA-256 (carga)   : {muestra.sha_snapshot}",
        f"   n                 : {muestra.n}",
        f"   n_esperado        : {muestra.n_esperado}"
        f"{' (--universo-completo)' if muestra.universo_completo else ''}",
        f"   n_con_evidencia   : {n_con_evidencia}",
        f"   n_sin_evidencia   : {n_sin_evidencia}",
        f"   Celdas            : {len(muestra.celdas)} seleccionadas de "
        f"{len(muestra.cobertura_todas)} candidatas",
        "   Celdas seleccionadas (cobertura):",
    ]
    for celda in muestra.celdas:
        cobertura = muestra.cobertura.get(celda, 0)
        pct = (cobertura / muestra.n) * 100.0 if muestra.n else 0.0
        lineas.append(f"      · {celda}: {cobertura}/{muestra.n} ({pct:.2f}%)")
    lineas.append("   Variables excluidas:")
    if muestra.excluidas:
        for item in muestra.excluidas:
            lineas.append(
                f"      · {item['celda']}: {item['cobertura']}/{muestra.n} "
                f"({item['pct']:.2f}%) — {item['motivo']}"
            )
    else:
        lineas.append("      · ninguna")
    cuotas = muestra.resumen_cuotas or {}
    if cuotas:
        lineas += [
            "   Cuotas:",
            f"      · con cuota fixtures   : {cuotas.get('n_con_cuota_fixtures', 0)}",
            f"      · con cuota histórica  : {cuotas.get('n_con_cuota_historica', 0)}",
            f"      · sin cuota            : {cuotas.get('n_sin_cuota', 0)}",
            f"      · JOIN ambiguo         : {cuotas.get('n_join_ambiguo', 0)}",
            f"      · fuente               : {cuotas.get('fuente_cuotas', {})}",
            f"      · motivos sin cuota    : {cuotas.get('motivos_sin_cuota', {})}",
            f"      · inventario histórico : {cuotas.get('historico', {})}",
        ]
    lineas += [
        f"   SHA-256 (después) : {sha_despues}",
        f"   Snapshot inmutable: {'IDÉNTICO' if sha_despues == muestra.sha_snapshot else 'CAMBIÓ 🚨'}",
        f"   Conteo            : {'COINCIDE' if muestra.n == muestra.n_esperado else 'NO COINCIDE 🚨'}",
        "   Análisis ejecutado: NINGUNO (bisección, λ, Davidson y bootstrap no se invocan)",
        _linea(),
    ]
    print("\n".join(lineas))
    if sha_despues != muestra.sha_snapshot:
        return 2
    if muestra.n != muestra.n_esperado:
        return 3
    return 0


# ═════════════════════════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════════════════════════
def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Distancia al borde de decisión (counterfactual).")
    parser.add_argument("--snapshot", default=str(RUTA_SNAPSHOT_DEFECTO))
    parser.add_argument("--json", action="store_true")
    conteo = parser.add_mutually_exclusive_group()
    conteo.add_argument(
        "--n-esperado",
        type=int,
        default=None,
        help="Exige exactamente N partidos (default: 124).",
    )
    conteo.add_argument(
        "--universo-completo",
        action="store_true",
        help="Acepta el conteo real de la bóveda y lo declara (sustituye N_ESPERADO).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo carga y verifica. No ejecuta análisis.",
    )
    parser.add_argument(
        "--salida",
        default=None,
        type=Path,
        help="Directorio de salida para --json. Si None, usa data/output/ (compatibilidad).",
    )
    # ── [Rerun Doble B + D] Flags del análisis completo (opt-in, defaults intactos) ───────────
    parser.add_argument("--taus", default=None, help="Curva τ separada por comas.")
    parser.add_argument("--n-fragiles", type=int, default=None, help="Tamaño del top frágil.")
    parser.add_argument("--bootstrap", type=int, default=None, help="Remuestreos de bloques.")
    parser.add_argument("--fixed-free", action="store_true", help="Ablaciones V12/V26+V29+V30/V06.")
    parser.add_argument("--modelo-nulo", action="store_true", help="P_null uniforme (1/3).")
    parser.add_argument("--outliers", type=int, default=None, help="Top/bottom por norma.")
    parser.add_argument(
        "--estratificar",
        default=None,
        choices=["procedencia_xg"],
        help="Particiona σ por sello xg_es_real_opta.",
    )
    parser.add_argument("--kfold", type=int, default=None, help="K-fold de α (sólo D).")
    argumentos = parser.parse_args(argv)
    ruta_snapshot = Path(argumentos.snapshot)

    if argumentos.dry_run:
        try:
            muestra = cargar_muestra(
                ruta_snapshot,
                n_esperado=argumentos.n_esperado,
                universo_completo=argumentos.universo_completo,
            )
            cargar_niveles(ruta_snapshot, muestra.ids, muestra.celdas)
        except ConteoNoCoincide as error:
            print(f"\n{error}\n", file=sys.stderr)
            return 3
        except (UniversoInsuficiente, BordeInfactible, RuntimeError) as error:
            print(f"\n{error}\n", file=sys.stderr)
            return 4
        return _imprimir_dry_run(muestra, sha256_archivo(ruta_snapshot))

    # [Rerun Doble B + D] Los flags del análisis completo despachan al motor dedicado.
    flags_rerun = any(
        [
            argumentos.taus is not None,
            argumentos.n_fragiles is not None,
            argumentos.bootstrap is not None,
            argumentos.fixed_free,
            argumentos.modelo_nulo,
            argumentos.outliers is not None,
            argumentos.estratificar is not None,
            argumentos.kfold is not None,
        ]
    )
    if flags_rerun:
        from scripts.laboratorio.rerun_doble import ejecutar_rerun

        return ejecutar_rerun(argumentos, ruta_snapshot)

    try:
        datos = ejecutar(
            ruta_snapshot,
            n_esperado=argumentos.n_esperado,
            universo_completo=argumentos.universo_completo,
        )
    except ConteoNoCoincide as error:
        print(f"\n{error}\n", file=sys.stderr)
        return 3
    except BordeInfactible as error:
        print(f"\n{error}\n", file=sys.stderr)
        return 4
    except FalloOptimizacion as error:
        print(f"\n{error}\n", file=sys.stderr)
        return 4

    muestra = datos["muestra"]
    sha_despues = sha256_archivo(Path(muestra.ruta_snapshot))
    imprimir(datos, sha_despues)

    if argumentos.json:
        principal = next(r for r in datos["resultados"] if math.isclose(r.tau, TAU_PRINCIPAL))
        reporte = {
            "ley": "[LN-QBE-100] · [LN-QBE-120] · [LN-QBE-126]",
            "instrumento": "sandbox_distancia_borde",
            "snapshot": {"sha256": muestra.sha_snapshot, "inmutable": sha_despues == muestra.sha_snapshot},
            "paridad": {"brier_ancla": brier(muestra.p_base, muestra.y), "n": muestra.n},
            "alfa": [round(float(v), 6) for v in datos["alfa"]],
            "curva": [
                {
                    "tau": r.tau,
                    "sigma_mediana": round(float(np.median(_normas(r.deltas))), 4),
                    "sigma_p90": round(float(np.quantile(_normas(r.deltas), 0.90)), 4),
                    "sigma_max": round(float(_normas(r.deltas).max()), 4),
                    "ya_correctos": r.ya_correctos,
                    "n_evidencia": r.n_evidencia,
                    "brier": round(r.brier_final, 6),
                    "brier_evidencia": round(r.brier_evidencia, 6),
                    "inalcanzables": r.inalcanzables,
                    "sin_evidencia": r.sin_evidencia,
                }
                for r in datos["resultados"]
            ],
            "fragiles": [
                {
                    "id_partido": muestra.ids[i],
                    "jornada": int(muestra.jornadas[i]),
                    "resultado": muestra.resultados[i],
                    "norma_sigma": round(float(_normas(principal.deltas)[i]), 4),
                    "top3": [
                        {"celda": muestra.celdas[j], "delta_sigma": round(float(principal.deltas[i, j]), 4)}
                        for j in np.argsort(-np.abs(principal.deltas[i]))[:3]
                    ],
                }
                for i in np.argsort(-_normas(principal.deltas))[:N_FRAGILES]
            ],
            "deformacion_media": {
                muestra.celdas[j]: round(float(np.nanmean(np.abs(principal.deltas[:, j]))), 6)
                for j in range(len(muestra.celdas))
            },
        }
        ruta_salida = ruta_reporte(argumentos, "distancia_borde", RUTA_SALIDA_JSON)
        ruta_salida.parent.mkdir(parents=True, exist_ok=True)
        ruta_salida.write_text(json.dumps(reporte, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n📄 Reporte exportado: {ruta_salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
