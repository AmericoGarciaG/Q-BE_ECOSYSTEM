# -*- coding: utf-8 -*-
"""
🧪 Q-BE LABORATORIO — SANDBOX SHADOW COMPETITIVO (MODELO DE FUERZA DAVIDSON)

[LN-QBE-100] · [LN-QBE-120] · [LN-QBE-124] · [LN-QBE-126] · [LN-QBE-127]
Kybern Framework v13.5 · Base de Gobierno: [HÍBRIDO DUAL-TRACK]

Instrumento CLI-FIRST que pone a competir TRES predicciones sobre el MISMO universo de 124
partidos del Visor, sin tocar la P′ canónica:

    Motor A · DAVIDSON LEGISLADO [DBBD]
        6 pesos de dimensión (𝒯_Vol · 𝒯_Rem · 𝒯_Def · 𝒯_Por · 𝒯_Spc · 𝒯_Ctx)
        + sesgo de empate b_X + ventaja de localía b_H.
        s_i = Σ_k α_k · D_ik ;  u_i = (s_i + b_H, b_X, −s_i) ;  P_i = softmax(u_i)
        Ancla: prior uniforme PROYECTADO sobre β (el uniforme puro viola β_orden).
        Sin gauge: la escala de confianza se ajusta (un gauge aditivo la fija y el modelo
        pierde por construcción).  β_orden en RATIOS, invariante a escala.  SLSQP.

    Motor A0 · DIAGNÓSTICO DE SEÑAL
        Participación uniforme (α_k = 1/6) con UNA ganancia global τ calibrada + b_H + b_X.
        Separa «¿hay señal?» de «¿hay re-ponderación?». Sin β: referencia, no candidato.

    Motor B · TECHO DE INFORMACIÓN
        HistGradientBoostingClassifier (sklearn, dependencia ya declarada del Observatorio)
        sobre las celdas diferenciales crudas, NaN nativo (cero imputación).

    Juez · CV anidada por jornada + bootstrap de bloques + test de permutación + MDE.

Diseño antifuga: las features son DIFERENCIALES LOCAL − VISITANTE (no orientadas al favorito
del trío canónico). El modelo debe descubrir el signo; jamás hereda la respuesta de P′.

Read-only absoluto. La única escritura es el reporte JSON opcional.

Uso:
    python -m scripts.laboratorio.sandbox_shadow_competitivo
    python -m scripts.laboratorio.sandbox_shadow_competitivo --json
    python -m scripts.laboratorio.sandbox_shadow_competitivo --rapido
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy.optimize import Bounds, linprog, minimize
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

RAIZ_PROYECTO = Path(__file__).resolve().parents[2]
if str(RAIZ_PROYECTO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROYECTO))

from scripts.laboratorio.sandbox_arquetipos_vectores import (  # noqa: E402
    DIMENSIONES_ESTRUCTURALES,
    _distribuciones_vigentes,
    _indice_h2h_stats,
    _numero,
    _par_magnitudes,
)
from scripts.laboratorio.sandbox_optimizacion_gradiente import (  # noqa: E402
    N_ESPERADO,
    RUTA_SNAPSHOT_DEFECTO,
    _indice_fixtures,
    _motor_solo_lectura,
    _trio_captura,
    ruta_reporte,
    sha256_archivo,
)
from src.core.contracts.portfolio_math import calcular_brier_multicategorico  # noqa: E402

# ── Dimensiones canónicas (orden del catálogo [LN-QBE-120]) ─────────────────────────────────
DIMENSIONES: Tuple[str, ...] = (
    "𝒯_Vol",
    "𝒯_Rem",
    "𝒯_Def",
    "𝒯_Por",
    "𝒯_Spc",
    "𝒯_Ctx",
)
NOMBRE_DIMENSION: Dict[str, str] = {
    "𝒯_Vol": "Volumen territorial",
    "𝒯_Rem": "Calidad de remate",
    "𝒯_Def": "Resistencia defensiva",
    "𝒯_Por": "Rendimiento de portería",
    "𝒯_Spc": "Balón parado y disciplina",
    "𝒯_Ctx": "Memoria, forma y contexto",
}

# ── β · Polítopo futbolístico (ratios, invariante a escala) ─────────────────────────────────
ALFA_MIN = 0.05
ALFA_MAX = 2.00
ORDEN_REM_SOBRE_VOL = 1.10
ORDEN_REM_SOBRE_SPC = 1.20
ORDEN_DEF_SOBRE_SPC = 1.10
CELDA_ALTITUD = "V29"
UMBRAL_ALTITUD_METROS = 1000.0
COBERTURA_MINIMA = 0.80

# Índices del vector de parámetros: [0..5] = α (orden de DIMENSIONES), 6 = b_H, 7 = b_X
IDX_VOL, IDX_REM, IDX_DEF, IDX_POR, IDX_SPC, IDX_CTX = range(6)
IDX_B_HOME, IDX_B_DRAW = 6, 7

# Ancla de ridge y arranque FACTIBLES (el uniforme α = 1 viola β_orden: 1 ≥ 1.10·1 es falso).
ANCLA_FACTIBLE: Tuple[float, ...] = (1.00, 1.30, 1.20, 1.00, 1.00, 1.00, 0.00, 0.00)
ARRANQUE_FACTIBLE: Tuple[float, ...] = ANCLA_FACTIBLE

# ── Juez ────────────────────────────────────────────────────────────────────────────────────
N_FOLDS_EXTERNOS = 5
N_FOLDS_INTERNOS = 4
LAMBDAS_RIDGE: Tuple[float, ...] = (0.0, 0.02, 0.10)
N_BOOTSTRAP = 2000
N_PERMUTACIONES = 200
SEMILLA = 20261029
Z_POTENCIA_80 = 2.802

RUTA_SALIDA_JSON = RAIZ_PROYECTO / "data" / "output" / "shadow_competitivo_reporte.json"
ANCHO = 100


# ═════════════════════════════════════════════════════════════════════════════════════════════
# ERRORES FIDUCIARIOS
# ═════════════════════════════════════════════════════════════════════════════════════════════
class ErrorJuez(RuntimeError):
    """Fallo declarado del instrumento."""


class BetaInfactible(ErrorJuez):
    """El polítopo β no tiene punto factible: se dice QUÉ regla se contradice."""


class UniversoInsuficiente(ErrorJuez):
    """La bóveda no sostiene el experimento."""


class ConteoNoCoincide(UniversoInsuficiente):
    """El universo cargado no coincide con el `n_esperado` declarado (P0 #2)."""


class FalloOptimizacion(ErrorJuez):
    """SLSQP no convergió o devolvió un punto fuera de β."""


# ═════════════════════════════════════════════════════════════════════════════════════════════
# MUESTRA — diferenciales local − visitante (cero fuga del favorito canónico)
# ═════════════════════════════════════════════════════════════════════════════════════════════
@dataclass
class Muestra:
    ids: List[str]
    jornadas: np.ndarray
    p_base: np.ndarray
    y: np.ndarray
    resultados: List[str]
    celdas: Tuple[str, ...]
    dimension_de: Dict[str, str]
    crudo: np.ndarray
    delta_alt: np.ndarray
    cobertura: Dict[str, int]
    brier_base: float
    brier_mercado: float
    q_mercado: np.ndarray
    sha_snapshot: str
    ruta_snapshot: str
    # [P0 #2/#3] Trazabilidad del pre-vuelo: cobertura de TODO el catálogo candidato (no sólo las
    # celdas seleccionadas), exclusiones declaradas, conteo esperado y resumen de cuotas.
    cobertura_todas: Dict[str, int] = field(default_factory=dict)
    excluidas: List[Dict[str, Any]] = field(default_factory=list)
    n_esperado: int = 0
    universo_completo: bool = False
    resumen_cuotas: Dict[str, Any] = field(default_factory=dict)
    # [Rerun Doble] Procedencia xG certificada (ORC-08) y temporada de cada partido, para
    # estratificar σ y etiquetar outliers sin una segunda consulta a la bóveda.
    opta: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=bool))
    temporadas: List[str] = field(default_factory=list)

    @property
    def n(self) -> int:
        return len(self.ids)


def _indice_dimensiones() -> Dict[str, str]:
    """id de celda → dimensión canónica, desde el catálogo ÚNICO [LN-QBE-120]."""
    from src.observatory.core.factor_attribution import _CATALOGO_32

    return {fila[0]: fila[2] for fila in _CATALOGO_32}


def _matriz_celdas(sesion: Session, micro: List[Dict[str, Any]], celdas: Sequence[str]):
    """Extrae el diferencial local − visitante de cada celda (contexto: magnitud propia).

    Devuelve también la máscara `xg_es_real_opta` de cada partido (ORC-08), leída de la traza
    soberana: es la fuente ÚNICA del sello de procedencia xG.
    """
    soberanas = _distribuciones_vigentes(sesion)
    h2h = _indice_h2h_stats(sesion)
    crudo = np.full((len(micro), len(celdas)), np.nan)
    delta_alt = np.zeros(len(micro))
    opta = np.zeros(len(micro), dtype=bool)
    for indice, partido in enumerate(micro):
        distribucion = soberanas.get(str(partido["id_partido"]))
        if distribucion is None:
            continue
        traza = distribucion.audit_trace_json if isinstance(distribucion.audit_trace_json, dict) else {}
        insumos = traza.get("insumos_factivados")
        if not isinstance(insumos, dict):
            continue
        opta[indice] = bool(insumos.get("xg_es_real_opta"))
        delta_alt[indice] = _numero(insumos.get("delta_alt_metros")) or 0.0
        for columna, celda in enumerate(celdas):
            local, visita, bilateral = _par_magnitudes(
                insumos, h2h.get(str(partido["id_partido"]), {}), celda
            )
            if bilateral:
                if local is not None and visita is not None:
                    crudo[indice, columna] = float(local) - float(visita)
            elif local is not None:
                crudo[indice, columna] = float(local)
    return crudo, delta_alt, opta


def cargar_muestra(
    ruta_snapshot: Path,
    n_esperado: Optional[int] = None,
    universo_completo: bool = False,
) -> Muestra:
    """Universo del Visor + diferenciales + cobertura; aborta si algo no cuadra.

    [P0 #2] `n_esperado` parametriza el conteo exigido (default `N_ESPERADO = 124`, backward-compat
    con J14). `universo_completo=True` sustituye la exigencia por el conteo real y lo declara.
    """
    from app.routes.backtesting import _construir_reporte_calibracion

    ruta = Path(ruta_snapshot).resolve()
    sha = sha256_archivo(ruta)
    esperado = int(n_esperado) if n_esperado is not None else N_ESPERADO
    motor = _motor_solo_lectura(ruta)
    sesion = sessionmaker(bind=motor)()
    try:
        reporte = _construir_reporte_calibracion(sesion, league_id=1)
        fixtures = _indice_fixtures(sesion)
        micro = [p for jornada in reporte.get("jornadas", []) for p in jornada["partidos"]]
        if not universo_completo and len(micro) != esperado:
            raise ConteoNoCoincide(
                f"🚨 Universo {len(micro)} ≠ {esperado}: la bóveda cambió de jornada. "
                "Use --universo-completo para aceptar el conteo real y declararlo."
            )
        n_declarado = len(micro) if universo_completo else esperado
        catalogo = _indice_dimensiones()
        candidatas = [c for c in DIMENSIONES_ESTRUCTURALES if c in catalogo]
        crudo_todo, delta_alt, opta = _matriz_celdas(sesion, micro, candidatas)
        resumen_cuotas = dict(reporte.get("cuotas") or {})
        temporadas_map = dict(
            sesion.execute(text("SELECT id, season_id FROM matches")).all()
        )
    finally:
        sesion.close()
        motor.dispose()

    cobertura_todas = {
        celda: int(np.sum(~np.isnan(crudo_todo[:, j])))
        for j, celda in enumerate(candidatas)
    }
    umbral = COBERTURA_MINIMA * len(micro)
    seleccionadas: List[str] = []
    excluidas: List[Dict[str, Any]] = []
    for j, celda in enumerate(candidatas):
        columna = crudo_todo[:, j]
        cobertura = cobertura_todas[celda]
        if cobertura < umbral:
            excluidas.append({
                "celda": celda,
                "cobertura": cobertura,
                "pct": round((cobertura / len(micro)) * 100.0, 2) if micro else 0.0,
                "motivo": f"COBERTURA<{COBERTURA_MINIMA:.0%}",
            })
            continue
        if cobertura and float(np.nanstd(columna)) <= 1e-9:
            excluidas.append({
                "celda": celda,
                "cobertura": cobertura,
                "pct": round((cobertura / len(micro)) * 100.0, 2) if micro else 0.0,
                "motivo": "VARIANZA_NULA",
            })
            continue
        seleccionadas.append(celda)
    if not seleccionadas:
        raise UniversoInsuficiente("🚨 Ninguna celda supera β_suficiencia.")

    columnas = [candidatas.index(c) for c in seleccionadas]
    crudo = crudo_todo[:, columnas]
    cobertura_sel = {c: cobertura_todas[c] for c in seleccionadas}

    ids, jornadas, p_base, y, resultados, q_mercado = [], [], [], [], [], []
    for partido in micro:
        match_id = str(partido["id_partido"])
        trio = _trio_captura(fixtures.get(match_id) or {})
        if trio is None:
            raise UniversoInsuficiente(f"🚨 {match_id} sin P′ íntegra en la captura.")
        resultado = str(partido["resultado_real"])
        ids.append(match_id)
        jornadas.append(int(partido["jornada"]))
        p_base.append(trio)
        resultados.append(resultado)
        y.append(
            (
                1.0 if resultado == "LOCAL" else 0.0,
                1.0 if resultado == "EMPATE" else 0.0,
                1.0 if resultado == "VISITANTE" else 0.0,
            )
        )
        # [P0 #1.3] Sin cuota válida NO hay vector de mercado: NaN, jamás 1/3 ni 0.0.
        if partido.get("q_local") is None or partido.get("q_empate") is None or partido.get("q_visitante") is None:
            q_mercado.append((np.nan, np.nan, np.nan))
        else:
            q_mercado.append(
                (float(partido["q_local"]), float(partido["q_empate"]), float(partido["q_visitante"]))
            )

    registros = [
        {"p_local": p[0], "p_empate": p[1], "p_visitante": p[2], "resultado": r}
        for p, r in zip(p_base, resultados)
    ]
    q_mercado_np = np.asarray(q_mercado, dtype=float)
    con_mercado = ~np.isnan(q_mercado_np).any(axis=1)
    registros_mercado = [
        {"p_local": q[0], "p_empate": q[1], "p_visitante": q[2], "resultado": r}
        for q, r, valido in zip(q_mercado, resultados, con_mercado)
        if valido
    ]
    return Muestra(
        ids=ids,
        jornadas=np.asarray(jornadas, dtype=int),
        p_base=np.asarray(p_base, dtype=float),
        y=np.asarray(y, dtype=float),
        resultados=resultados,
        celdas=tuple(seleccionadas),
        dimension_de=catalogo,
        crudo=crudo,
        delta_alt=delta_alt,
        cobertura=cobertura_sel,
        brier_base=float(calcular_brier_multicategorico(registros)),
        brier_mercado=(
            float(calcular_brier_multicategorico(registros_mercado))
            if registros_mercado
            else float("nan")
        ),
        q_mercado=q_mercado_np,
        sha_snapshot=sha,
        ruta_snapshot=str(ruta),
        cobertura_todas=cobertura_todas,
        excluidas=excluidas,
        n_esperado=n_declarado,
        universo_completo=bool(universo_completo),
        resumen_cuotas=resumen_cuotas,
        opta=opta,
        temporadas=[str(temporadas_map.get(i) or "") for i in ids],
    )


# ═════════════════════════════════════════════════════════════════════════════════════════════
# MOTOR A — DAVIDSON LEGISLADO
# ═════════════════════════════════════════════════════════════════════════════════════════════
def estandarizar(crudo: np.ndarray, indices: np.ndarray) -> np.ndarray:
    """Z-Score por celda con (μ, σ) del ajuste; NaN viaja como ausencia (cero imputación)."""
    sub = crudo[indices]
    with np.errstate(invalid="ignore"):
        medias = np.nanmean(sub, axis=0)
        sigmas = np.nanstd(sub, axis=0)
    sigmas = np.where(sigmas <= 1e-12, 0.0, sigmas)
    z = (crudo - medias) / np.where(sigmas == 0.0, 1.0, sigmas)
    return np.where(sigmas[None, :] == 0.0, np.where(np.isnan(crudo), np.nan, 0.0), z)


def puntajes(
    z: np.ndarray,
    celdas: Sequence[str],
    dimension_de: Dict[str, str],
    delta_alt: np.ndarray,
) -> np.ndarray:
    """Agrega las celdas en los 6 puntajes de dimensión (media observada, sin imputar)."""
    salida = np.full((z.shape[0], len(DIMENSIONES)), np.nan)
    for indice, dimension in enumerate(DIMENSIONES):
        columnas = [j for j, celda in enumerate(celdas) if dimension_de[celda] == dimension]
        if not columnas:
            continue
        bloques = []
        for columna in columnas:
            valores = z[:, columna].astype(float).copy()
            if celdas[columna] == CELDA_ALTITUD:
                # β_contexto: el regresor de altitud se APAGA si no hay desnivel real.
                valores = np.where(delta_alt >= UMBRAL_ALTITUD_METROS, valores, np.nan)
            bloques.append(valores)
        matriz = np.vstack(bloques)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            salida[:, indice] = np.nanmean(matriz, axis=0)
    return np.where(np.isnan(salida), 0.0, salida)


def davidson(parametros: np.ndarray, dimensiones: np.ndarray) -> np.ndarray:
    """P = softmax(s + b_H, b_X, −s), con s = Σ α_k·D_k."""
    alfa = parametros[:6]
    b_home, b_draw = parametros[IDX_B_HOME], parametros[IDX_B_DRAW]
    fuerza = dimensiones @ alfa
    logits = np.column_stack((fuerza + b_home, np.full_like(fuerza, b_draw), -fuerza))
    logits -= logits.max(axis=1, keepdims=True)
    exp = np.exp(logits)
    return exp / exp.sum(axis=1, keepdims=True)


def davidson_uniforme(parametros: np.ndarray, dimensiones: np.ndarray) -> np.ndarray:
    """s = τ·media(D): participación uniforme 1/6 con UNA sola ganancia global τ."""
    fuerza = parametros[0] * dimensiones.mean(axis=1)
    logits = np.column_stack(
        (fuerza + parametros[1], np.full_like(fuerza, parametros[2]), -fuerza)
    )
    logits -= logits.max(axis=1, keepdims=True)
    exp = np.exp(logits)
    return exp / exp.sum(axis=1, keepdims=True)


def brier(probabilidades: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean(np.sum((probabilidades - y) ** 2, axis=1)) / 3.0)


def _restricciones_beta() -> List[Dict[str, Any]]:
    """β_orden en RATIOS (lineal y scale-invariant): el sentido futbolístico manda sobre la escala."""
    return [
        {
            "type": "ineq",
            "fun": lambda p: float(p[IDX_REM] - ORDEN_REM_SOBRE_VOL * p[IDX_VOL]),
        },
        {
            "type": "ineq",
            "fun": lambda p: float(p[IDX_REM] - ORDEN_REM_SOBRE_SPC * p[IDX_SPC]),
        },
        {
            "type": "ineq",
            "fun": lambda p: float(p[IDX_DEF] - ORDEN_DEF_SOBRE_SPC * p[IDX_SPC]),
        },
    ]


def verificar_factibilidad_beta() -> None:
    """
    Fase I del polítopo (linprog, independiente de SLSQP): si β es vacío, se aborta y se
    nombra la regla. SLSQP jamás se lanza sobre un conjunto infactible.
    """
    A_ub = np.array(
        [
            [ORDEN_REM_SOBRE_VOL, -1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, -1.0, 0.0, 0.0, ORDEN_REM_SOBRE_SPC, 0.0, 0.0, 0.0],
            [0.0, 0.0, -1.0, 0.0, ORDEN_DEF_SOBRE_SPC, 0.0, 0.0, 0.0],
        ]
    )
    b_ub = np.zeros(3)
    limites = [(ALFA_MIN, ALFA_MAX)] * 6 + [(-1.0, 1.0), (-1.0, 1.0)]
    resultado = linprog(c=np.zeros(8), A_ub=A_ub, b_ub=b_ub, bounds=limites, method="highs")
    if not resultado.success:
        raise BetaInfactible(
            "🚨 POLÍTOPO β INFACTIBLE: β_orden "
            f"(Rem ≥ {ORDEN_REM_SOBRE_VOL:.2f}·Vol · Rem ≥ {ORDEN_REM_SOBRE_SPC:.2f}·Spc · "
            f"Def ≥ {ORDEN_DEF_SOBRE_SPC:.2f}·Spc) no admite punto con "
            f"α ∈ [{ALFA_MIN:.2f}, {ALFA_MAX:.2f}]. linprog: {resultado.message}. "
            "No se relaja β en silencio."
        )


def verificar_beta(parametros: np.ndarray, tolerancia: float = 1e-7) -> None:
    """Auditoría post-SLSQP: caja + orden en ratios, con el nombre de la regla violada."""
    alfa = np.asarray(parametros[:6], dtype=float)
    if not np.all(np.isfinite(parametros)):
        raise FalloOptimizacion("🚨 SLSQP devolvió parámetros no finitos.")
    for indice, valor in enumerate(alfa):
        if valor < ALFA_MIN - tolerancia or valor > ALFA_MAX + tolerancia:
            raise FalloOptimizacion(
                f"🚨 β_cota violada en {DIMENSIONES[indice]}: α = {valor:.6f} ∉ [{ALFA_MIN}, {ALFA_MAX}]."
            )
    if alfa[IDX_REM] - ORDEN_REM_SOBRE_VOL * alfa[IDX_VOL] < -1e-5:
        raise FalloOptimizacion("🚨 β_orden violada: Rem < 1.10·Vol.")
    if alfa[IDX_REM] - ORDEN_REM_SOBRE_SPC * alfa[IDX_SPC] < -1e-5:
        raise FalloOptimizacion("🚨 β_orden violada: Rem < 1.20·Spc.")
    if alfa[IDX_DEF] - ORDEN_DEF_SOBRE_SPC * alfa[IDX_SPC] < -1e-5:
        raise FalloOptimizacion("🚨 β_orden violada: Def < 1.10·Spc.")


def ajustar_davidson(
    dimensiones: np.ndarray,
    y: np.ndarray,
    lam: float,
    ancla: np.ndarray,
) -> np.ndarray:
    """Brier + ridge hacia el ancla factible, sujeto al polítopo β (SLSQP determinista)."""

    def objetivo(parametros: np.ndarray) -> float:
        penalizacion = lam * float(np.sum((parametros[:6] - ancla[:6]) ** 2))
        return brier(davidson(parametros, dimensiones), y) + penalizacion

    resultado = minimize(
        objetivo,
        np.asarray(ARRANQUE_FACTIBLE, dtype=float),
        method="SLSQP",
        bounds=Bounds([ALFA_MIN] * 6 + [-1.0, -1.0], [ALFA_MAX] * 6 + [1.0, 1.0]),
        constraints=_restricciones_beta(),
        options={"maxiter": 500, "ftol": 1e-12},
    )
    if not resultado.success:
        raise FalloOptimizacion(f"🚨 SLSQP no convergió: {resultado.message}")
    verificar_beta(resultado.x)
    return resultado.x


def _folds(jornadas: np.ndarray, n_folds: int) -> List[np.ndarray]:
    """Reparto round-robin determinista de jornadas completas (jamás se parte una jornada)."""
    unicas = sorted({int(j) for j in jornadas})
    grupos: List[List[int]] = [[] for _ in range(n_folds)]
    for posicion, jornada in enumerate(unicas):
        grupos[posicion % n_folds].append(jornada)
    return [np.isin(jornadas, grupo) for grupo in grupos]


def cv_anidada_davidson(
    muestra: Muestra,
    lambdas: Sequence[float] = LAMBDAS_RIDGE,
    seleccionar_lambda: bool = True,
) -> Dict[str, Any]:
    """CV anidada (externa 5, interna 4) agrupada por jornada; devuelve OOS y λ por fold."""
    ancla = np.asarray(ANCLA_FACTIBLE, dtype=float)
    pronosticos = np.zeros((muestra.n, 3))
    detalle: List[Dict[str, Any]] = []
    for indice, prueba in enumerate(_folds(muestra.jornadas, N_FOLDS_EXTERNOS)):
        ajuste = ~prueba
        z = estandarizar(muestra.crudo, np.where(ajuste)[0])
        dims = puntajes(z, muestra.celdas, muestra.dimension_de, muestra.delta_alt)
        lam_elegida = 0.0
        if seleccionar_lambda and len(lambdas) > 1:
            inner = _folds(muestra.jornadas[ajuste], N_FOLDS_INTERNOS)
            errores = {lam: 0.0 for lam in lambdas}
            conteo = 0
            idx_ajuste = np.where(ajuste)[0]
            for mascara_interna in inner:
                idx_prueba_int = idx_ajuste[mascara_interna]
                idx_entrena_int = idx_ajuste[~mascara_interna]
                if idx_entrena_int.size < 20 or idx_prueba_int.size == 0:
                    continue
                z_int = estandarizar(muestra.crudo, idx_entrena_int)
                dims_int = puntajes(z_int, muestra.celdas, muestra.dimension_de, muestra.delta_alt)
                for lam in lambdas:
                    parametros = ajustar_davidson(
                        dims_int[idx_entrena_int], muestra.y[idx_entrena_int], lam, ancla
                    )
                    q = davidson(parametros, dims_int[idx_prueba_int])
                    errores[lam] += brier(q, muestra.y[idx_prueba_int]) * idx_prueba_int.size
                conteo += int(idx_prueba_int.size)
            if conteo:
                lam_elegida = min(lambdas, key=lambda lam: errores[lam] / conteo)
        parametros = ajustar_davidson(dims[ajuste], muestra.y[ajuste], lam_elegida, ancla)
        pronosticos[prueba] = davidson(parametros, dims[prueba])
        detalle.append(
            {
                "fold": indice + 1,
                "jornadas": sorted({int(j) for j in muestra.jornadas[prueba]}),
                "n_prueba": int(prueba.sum()),
                "lambda": lam_elegida,
                "alfa": [round(float(v), 4) for v in parametros[:6]],
                "b_home": round(float(parametros[IDX_B_HOME]), 4),
                "b_draw": round(float(parametros[IDX_B_DRAW]), 4),
                "brier": round(float(brier(pronosticos[prueba], muestra.y[prueba])), 6),
            }
        )
    return {
        "pronosticos": pronosticos,
        "brier": float(brier(pronosticos, muestra.y)),
        "folds": detalle,
    }


def diagnostico_uniforme(muestra: Muestra) -> Dict[str, Any]:
    """
    Competidor de 3 parámetros: participación UNIFORME (α_k = 1/6) y una sola ganancia global τ.

    Aísla «¿hay señal?» de «¿hay re-ponderación?». No lleva β: es referencia de señal, NO un
    modelo legislado ni candidato a promoción.
    """
    pronosticos = np.zeros_like(muestra.p_base)
    for prueba in _folds(muestra.jornadas, N_FOLDS_EXTERNOS):
        ajuste = ~prueba
        z = estandarizar(muestra.crudo, np.where(ajuste)[0])
        dims = puntajes(z, muestra.celdas, muestra.dimension_de, muestra.delta_alt)
        resultado = minimize(
            lambda p: brier(davidson_uniforme(p, dims[ajuste]), muestra.y[ajuste]),
            np.array([1.0, 0.0, 0.0]),
            method="SLSQP",
            bounds=Bounds([0.05, -1.0, -1.0], [5.0, 1.0, 1.0]),
            options={"maxiter": 300, "ftol": 1e-12},
        )
        pronosticos[prueba] = davidson_uniforme(resultado.x, dims[prueba])
    return {"pronosticos": pronosticos, "brier": float(brier(pronosticos, muestra.y))}


# ═════════════════════════════════════════════════════════════════════════════════════════════
# MOTOR B — TECHO DE INFORMACIÓN (HGB, NaN nativo)
# ═════════════════════════════════════════════════════════════════════════════════════════════
def cv_hgb(muestra: Muestra) -> Dict[str, Any]:
    """Mismo esquema de folds; el árbol ve las 23 celdas crudas con NaN nativo."""
    from sklearn.ensemble import HistGradientBoostingClassifier

    pronosticos = np.zeros((muestra.n, 3))
    detalle: List[Dict[str, Any]] = []
    for indice, prueba in enumerate(_folds(muestra.jornadas, N_FOLDS_EXTERNOS)):
        ajuste = ~prueba
        modelo = HistGradientBoostingClassifier(
            max_iter=30,
            learning_rate=0.05,
            max_depth=2,
            min_samples_leaf=35,
            l2_regularization=5.0,
            early_stopping=False,
            random_state=SEMILLA,
        )
        modelo.fit(muestra.crudo[ajuste], np.argmax(muestra.y[ajuste], axis=1))
        pronosticos[prueba] = modelo.predict_proba(muestra.crudo[prueba])
        detalle.append(
            {
                "fold": indice + 1,
                "n_prueba": int(prueba.sum()),
                "brier": round(float(brier(pronosticos[prueba], muestra.y[prueba])), 6),
            }
        )
    return {"pronosticos": pronosticos, "brier": float(brier(pronosticos, muestra.y)), "folds": detalle}


# ═════════════════════════════════════════════════════════════════════════════════════════════
# JUEZ — bootstrap de bloques, permutación y potencia mínima detectable
# ═════════════════════════════════════════════════════════════════════════════════════════════
def _errores_por_partido(probabilidades: np.ndarray, y: np.ndarray) -> np.ndarray:
    return np.sum((probabilidades - y) ** 2, axis=1) / 3.0


def mde(errores_modelo: np.ndarray, errores_base: np.ndarray) -> Dict[str, float]:
    """Diferencia pareada + error estándar + efecto mínimo detectable (80 % potencia)."""
    diferencia = errores_modelo - errores_base
    n = diferencia.size
    sd = float(np.std(diferencia, ddof=1))
    se = sd / math.sqrt(n)
    return {
        "delta": float(diferencia.mean()),
        "sd": sd,
        "se": se,
        "mde": Z_POTENCIA_80 * se,
        "n": n,
    }


def bootstrap_bloques(
    errores_modelo: np.ndarray,
    errores_base: np.ndarray,
    jornadas: np.ndarray,
    n_remuestreos: int = N_BOOTSTRAP,
    semilla: int = SEMILLA,
) -> Dict[str, float]:
    """Bootstrap por BLOQUES DE JORNADA: preserva la dependencia intra-jornada."""
    rng = np.random.default_rng(semilla)
    bloques = [np.where(jornadas == j)[0] for j in sorted({int(x) for x in jornadas})]
    deltas = np.empty(n_remuestreos)
    for indice in range(n_remuestreos):
        elegidos = rng.integers(0, len(bloques), size=len(bloques))
        idx = np.concatenate([bloques[k] for k in elegidos])
        deltas[indice] = float((errores_modelo[idx] - errores_base[idx]).mean())
    return {
        "media": float(deltas.mean()),
        "ic_bajo": float(np.quantile(deltas, 0.025)),
        "ic_alto": float(np.quantile(deltas, 0.975)),
    }


def test_permutacion(
    muestra: Muestra,
    delta_real: float,
    n_permutaciones: int = N_PERMUTACIONES,
    semilla: int = SEMILLA,
) -> Dict[str, float]:
    """
    Baraja el desenlace DENTRO de cada jornada y re-corre la CV externa completa (λ fija).

    El nulo responde a la pregunta correcta: ¿cuánto ΔBrier produce el mismo pipeline sobre
    etiquetas sin señal? Si el Δ real cae dentro del nulo, es sobreajuste.
    """
    ancla = np.asarray(ANCLA_FACTIBLE, dtype=float)
    rng = np.random.default_rng(semilla)
    folds = _folds(muestra.jornadas, N_FOLDS_EXTERNOS)
    deltas = np.empty(n_permutaciones)
    for permutacion in range(n_permutaciones):
        y_perm = muestra.y.copy()
        for jornada in sorted({int(j) for j in muestra.jornadas}):
            idx = np.where(muestra.jornadas == jornada)[0]
            valores = muestra.y[idx].copy()
            rng.shuffle(valores)
            y_perm[idx] = valores
        pronosticos = np.zeros_like(muestra.p_base)
        for prueba in folds:
            ajuste = ~prueba
            z = estandarizar(muestra.crudo, np.where(ajuste)[0])
            dims = puntajes(z, muestra.celdas, muestra.dimension_de, muestra.delta_alt)
            parametros = ajustar_davidson(dims[ajuste], y_perm[ajuste], 0.0, ancla)
            pronosticos[prueba] = davidson(parametros, dims[prueba])
        deltas[permutacion] = float(
            (
                _errores_por_partido(pronosticos, y_perm)
                - _errores_por_partido(muestra.p_base, y_perm)
            ).mean()
        )
    p_valor = float((np.sum(deltas <= delta_real) + 1) / (n_permutaciones + 1))
    return {
        "n": n_permutaciones,
        "media": float(deltas.mean()),
        "sd": float(deltas.std(ddof=1)),
        "p_valor": p_valor,
        "umbral_5pct": float(np.quantile(deltas, 0.05)),
        "delta_real": float(delta_real),
    }


def veredicto(delta: float, ic_bajo: float, ic_alto: float, mde_valor: float) -> str:
    """
    Regla de decisión ratificada: sin MDE no hay promoción.

    GANA           → mejora, IC 95 % excluye 0 y |Δ| ≥ MDE.
    PIERDE         → empeora de forma significativa (IC 95 % excluye 0 por arriba).
    NO CONCLUYENTE → el IC cruza 0 (o la mejora no alcanza el MDE): con 124 partidos el
                     instrumento no puede distinguir el modelo de la P′.
    """
    if delta < 0.0 and ic_alto < 0.0 and abs(delta) >= mde_valor:
        return "GANA"
    if delta < 0.0:
        return "NO CONCLUYENTE"
    if ic_bajo > 0.0:
        return "PIERDE"
    return "NO CONCLUYENTE"


# ═════════════════════════════════════════════════════════════════════════════════════════════
# TABLERO
# ═════════════════════════════════════════════════════════════════════════════════════════════
def _linea() -> str:
    return "═" * ANCHO


def imprimir(
    muestra: Muestra,
    motor_a: Dict[str, Any],
    motor_b: Dict[str, Any],
    juicio: Dict[str, Any],
    sha_despues: str,
) -> None:
    lineas = [
        _linea(),
        "🧪 SANDBOX SHADOW COMPETITIVO — DAVIDSON vs HGB vs P′ canónica",
        "   [LN-QBE-100] Brier · CV anidada por jornada · β polítopo (SLSQP) · [HÍBRIDO DUAL-TRACK]",
        _linea(),
        "",
        "0 · MUESTRA Y DISEÑO",
        f"   Snapshot     : {muestra.ruta_snapshot}",
        f"   SHA-256      : {muestra.sha_snapshot[:32]}…",
        f"   Partidos     : {muestra.n} · jornadas {int(muestra.jornadas.min())}–{int(muestra.jornadas.max())}",
        f"   Celdas       : {len(muestra.celdas)} útiles de {len(DIMENSIONES_ESTRUCTURALES)} estructurales "
        f"(β_suficiencia ≥80 % y no constantes)",
        f"   Dimensiones  : {len(DIMENSIONES)} · ancla factible · escala libre (sin gauge)",
        f"   β_orden      : Rem ≥ {ORDEN_REM_SOBRE_VOL:.2f}·Vol · Rem ≥ {ORDEN_REM_SOBRE_SPC:.2f}·Spc · "
        f"Def ≥ {ORDEN_DEF_SOBRE_SPC:.2f}·Spc (ratios)",
        f"   Gate altitud : V29 activo en {int(np.sum(muestra.delta_alt >= UMBRAL_ALTITUD_METROS))} partidos "
        f"(ΔAlt ≥ {UMBRAL_ALTITUD_METROS:.0f} m)",
        "   Features     : diferencial LOCAL − VISITANTE (cero fuga del favorito canónico)",
        "",
        "1 · MOTOR A · DAVIDSON LEGISLADO (6 α + b_H + b_X)",
        f"   Brier OOS    : {motor_a['brier']:.4f}   (CV anidada 5×4, λ ∈ {list(LAMBDAS_RIDGE)})",
        "   Fold   Jornadas                    λ      Brier   α[Vol Rem Def Por Spc Ctx]",
    ]
    for fila in motor_a["folds"]:
        jornadas = ",".join(f"J{j}" for j in fila["jornadas"])
        alfa = " ".join(f"{v:.2f}" for v in fila["alfa"])
        lineas.append(
            f"   {fila['fold']:>4}   {jornadas:<24} {fila['lambda']:>4.2f}   {fila['brier']:.4f}   {alfa}"
        )
    lineas += [
        "",
        "2 · MOTOR B · TECHO (HGB 30 iter · depth 2 · leaf 35) y A0 · SEÑAL UNIFORME",
        f"   HGB          : {motor_b['brier']:.4f}   (mismos folds; NaN nativo)",
        f"   Uniforme τ   : {juicio['p_brier']:.4f}   (α_k = 1/6 + τ calibrada; sin β, referencia)",
        "",
        "3 · JUEZ · BASELINES Y DECISIÓN",
        f"   P′ canónica  : {muestra.brier_base:.4f}",
        f"   Mercado      : {muestra.brier_mercado:.4f}",
        f"   Uniforme     : {juicio['brier_uniforme']:.4f}",
        "",
        f"   Davidson     : {juicio['a_brier']:.4f}   Δ vs P′ {juicio['a_delta']:+.4f}   "
        f"IC95 % [{juicio['a_ic'][0]:+.4f}, {juicio['a_ic'][1]:+.4f}]",
        f"   HGB          : {juicio['b_brier']:.4f}   Δ vs P′ {juicio['b_delta']:+.4f}   "
        f"IC95 % [{juicio['b_ic'][0]:+.4f}, {juicio['b_ic'][1]:+.4f}]",
        f"   Uniforme τ   : {juicio['p_brier']:.4f}   Δ vs P′ {juicio['p_delta']:+.4f}   "
        f"IC95 % [{juicio['p_ic'][0]:+.4f}, {juicio['p_ic'][1]:+.4f}]",
        "",
        f"   MDE (σ_dif pareada) : {juicio['mde_a']:.4f}   (SE {juicio['se_a']:.4f}, sd {juicio['sd_a']:.4f})",
        f"   Permutación         : p = {juicio['permutacion']['p_valor']:.3f} · "
        f"nulo 5 % = {juicio['permutacion']['umbral_5pct']:+.4f} · "
        f"Δ real = {juicio['permutacion']['delta_real']:+.4f}",
        "",
        f"   ⚖️  VEREDICTO DAVIDSON ... {juicio['veredicto_a']}",
        f"   ⚖️  TECHO (HGB) ......... {juicio['veredicto_b']}",
        f"   ⚖️  SEÑAL UNIFORME ...... {juicio['veredicto_p']}",
        "",
        "4 · AUDITORÍA β Y PUREZA",
        "   β_orden (ratios), β_cota, β_suficiencia: satisfechas (linprog + SLSQP + post-check)",
        f"   β_contexto: V29 apagado en {muestra.n - int(np.sum(muestra.delta_alt >= UMBRAL_ALTITUD_METROS))} partidos",
        f"   Snapshot inmutable: SHA-256 {'IDÉNTICO' if sha_despues == muestra.sha_snapshot else 'CAMBIÓ 🚨'}",
        "   Read-only: cero INSERT/UPDATE/DELETE/COMMIT · P′ canónica solo como baseline",
        "",
        _linea(),
    ]
    print("\n".join(lineas))


# ═════════════════════════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════════════════════════
def _parsear(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Shadow competitivo Davidson + HGB + Juez.")
    parser.add_argument("--snapshot", default=str(RUTA_SNAPSHOT_DEFECTO))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--rapido", action="store_true", help="Menos permutaciones y bootstrap.")
    conteo = parser.add_mutually_exclusive_group()
    conteo.add_argument(
        "--n-esperado",
        type=int,
        default=None,
        help=f"Exige exactamente N partidos (default: {N_ESPERADO}).",
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
    return parser.parse_args(argv)


def _imprimir_dry_run(muestra: Muestra, sha_despues: str) -> int:
    """[P0 #3.1] Pre-vuelo: carga, verifica, imprime y sale. Cero análisis."""
    observado = ~np.isnan(muestra.crudo)
    n_con_evidencia = int((observado.sum(axis=1) > 0).sum())
    n_sin_evidencia = muestra.n - n_con_evidencia
    lineas = [
        _linea(),
        "🧪 DRY-RUN — SANDBOX SHADOW COMPETITIVO (solo carga y verificación)",
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
        "   Análisis ejecutado: NINGUNO (bisección, Davidson y bootstrap no se invocan)",
        _linea(),
    ]
    print("\n".join(lineas))
    if sha_despues != muestra.sha_snapshot:
        return 2
    if muestra.n != muestra.n_esperado:
        return 3
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    argumentos = _parsear(argv)
    n_perm = 40 if argumentos.rapido else N_PERMUTACIONES
    n_boot = 300 if argumentos.rapido else N_BOOTSTRAP
    try:
        muestra = cargar_muestra(
            Path(argumentos.snapshot),
            n_esperado=argumentos.n_esperado,
            universo_completo=argumentos.universo_completo,
        )
    except BetaInfactible as error:
        print(f"\n{error}\n", file=sys.stderr)
        return 2
    except ConteoNoCoincide as error:
        print(f"\n{error}\n", file=sys.stderr)
        return 3
    except UniversoInsuficiente as error:
        print(f"\n{error}\n", file=sys.stderr)
        return 4

    if argumentos.dry_run:
        sha_dry = sha256_archivo(Path(muestra.ruta_snapshot))
        return _imprimir_dry_run(muestra, sha_dry)

    try:
        verificar_factibilidad_beta()
    except BetaInfactible as error:
        print(f"\n{error}\n", file=sys.stderr)
        return 2

    try:
        motor_a = cv_anidada_davidson(muestra)
        motor_b = cv_hgb(muestra)
        uniforme = diagnostico_uniforme(muestra)
    except FalloOptimizacion as error:
        print(f"\n{error}\n", file=sys.stderr)
        return 4

    errores_a = _errores_por_partido(motor_a["pronosticos"], muestra.y)
    errores_b = _errores_por_partido(motor_b["pronosticos"], muestra.y)
    errores_u = _errores_por_partido(uniforme["pronosticos"], muestra.y)
    errores_base = _errores_por_partido(muestra.p_base, muestra.y)

    stats_a = mde(errores_a, errores_base)
    stats_b = mde(errores_b, errores_base)
    stats_u = mde(errores_u, errores_base)
    boot_a = bootstrap_bloques(errores_a, errores_base, muestra.jornadas, n_boot)
    boot_b = bootstrap_bloques(errores_b, errores_base, muestra.jornadas, n_boot)
    boot_u = bootstrap_bloques(errores_u, errores_base, muestra.jornadas, n_boot)

    permutacion = test_permutacion(muestra, stats_a["delta"], n_perm)

    uniforme_prior = np.full((muestra.n, 3), 1.0 / 3.0)
    juicio = {
        "brier_uniforme": brier(uniforme_prior, muestra.y),
        "a_brier": motor_a["brier"],
        "a_delta": stats_a["delta"],
        "a_ic": (boot_a["ic_bajo"], boot_a["ic_alto"]),
        "b_brier": motor_b["brier"],
        "b_delta": stats_b["delta"],
        "b_ic": (boot_b["ic_bajo"], boot_b["ic_alto"]),
        "p_brier": uniforme["brier"],
        "p_delta": stats_u["delta"],
        "p_ic": (boot_u["ic_bajo"], boot_u["ic_alto"]),
        "mde_a": stats_a["mde"],
        "se_a": stats_a["se"],
        "sd_a": stats_a["sd"],
        "permutacion": permutacion,
        "veredicto_a": veredicto(stats_a["delta"], boot_a["ic_bajo"], boot_a["ic_alto"], stats_a["mde"]),
        "veredicto_b": veredicto(stats_b["delta"], boot_b["ic_bajo"], boot_b["ic_alto"], stats_b["mde"]),
        "veredicto_p": veredicto(stats_u["delta"], boot_u["ic_bajo"], boot_u["ic_alto"], stats_u["mde"]),
    }

    sha_despues = sha256_archivo(Path(muestra.ruta_snapshot))
    imprimir(muestra, motor_a, motor_b, juicio, sha_despues)

    if argumentos.json:
        reporte = {
            "ley": "[LN-QBE-100] · [LN-QBE-120] · [LN-QBE-126] · [LN-QBE-127]",
            "instrumento": "sandbox_shadow_competitivo",
            "regimen": "[HÍBRIDO DUAL-TRACK]",
            "semilla": SEMILLA,
            "snapshot": {
                "ruta": muestra.ruta_snapshot,
                "sha256": muestra.sha_snapshot,
                "inmutable": sha_despues == muestra.sha_snapshot,
            },
            "muestra": {
                "n": muestra.n,
                "n_esperado": muestra.n_esperado,
                "celdas": list(muestra.celdas),
                "cobertura": muestra.cobertura,
                "excluidas": muestra.excluidas,
                "cuotas": muestra.resumen_cuotas,
                "partidos_con_altitud": int(np.sum(muestra.delta_alt >= UMBRAL_ALTITUD_METROS)),
            },
            "beta": {
                "orden_ratios": [ORDEN_REM_SOBRE_VOL, ORDEN_REM_SOBRE_SPC, ORDEN_DEF_SOBRE_SPC],
                "cota": [ALFA_MIN, ALFA_MAX],
                "cobertura_minima": COBERTURA_MINIMA,
                "factible": True,
            },
            "motor_a": {
                "brier": motor_a["brier"],
                "folds": motor_a["folds"],
            },
            "motor_b": {"brier": motor_b["brier"], "folds": motor_b["folds"]},
            "senal_uniforme": {
                "brier": uniforme["brier"],
                "delta": stats_u["delta"],
                "bootstrap": boot_u,
                "veredicto": juicio["veredicto_p"],
            },
            "juez": {
                "baselines": {
                    "p_prima": muestra.brier_base,
                    "mercado": muestra.brier_mercado,
                    "uniforme": juicio["brier_uniforme"],
                },
                "davidson": {
                    "delta": stats_a["delta"],
                    "se": stats_a["se"],
                    "mde": stats_a["mde"],
                    "bootstrap": boot_a,
                    "veredicto": juicio["veredicto_a"],
                },
                "hgb": {
                    "delta": stats_b["delta"],
                    "se": stats_b["se"],
                    "mde": stats_b["mde"],
                    "bootstrap": boot_b,
                    "veredicto": juicio["veredicto_b"],
                },
                "permutacion": permutacion,
            },
        }
        ruta_salida = ruta_reporte(argumentos, "shadow_competitivo", RUTA_SALIDA_JSON)
        ruta_salida.parent.mkdir(parents=True, exist_ok=True)
        ruta_salida.write_text(json.dumps(reporte, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n📄 Reporte exportado: {ruta_salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
