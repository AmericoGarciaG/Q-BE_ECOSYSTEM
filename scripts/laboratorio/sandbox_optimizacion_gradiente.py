# -*- coding: utf-8 -*-
"""
🧪 Q-BE LABORATORIO — SANDBOX DE OPTIMIZACIÓN (SHADOW MODEL)

[LN-QBE-100] · [LN-QBE-124] · [LN-QBE-126] · [LN-QBE-127] · Kybern Framework v13.5
Base de Gobierno: [HÍBRIDO DUAL-TRACK]

Instrumento CLI-FIRST (cero HTTP, cero plantillas, cero estado persistente) que mide si una
RE-PONDERACIÓN de las 32 celdas del catálogo forense puede reducir el Brier Score global de la
P′ soberana. NO es un motor: es un experimento de sensibilidad sobre la bóveda real.

    Universo : el MISMO que consume el Visor del Observatorio — `_construir_reporte_calibracion`
               ([LN-QBE-127]) sobre `qbe_observatory/data/observatory_snapshot.db`.
    Ancla    : α₀ = 1.0 ⇒ la deformación es exactamente 0 ⇒ P̃ ≡ P′ (Brier inicial = Brier UI).
    Sombra   : u_i = ln P′_i + g·(s_i(α) − s_i(1))·δ_i·(1, 0, −1) ; P̃_i = softmax(u_i)
               s_i(α) = media ponderada de los Z-Score observados (máscara; cero imputación).
    β        : α_j ∈ [0.05, 2.00] — toda variable queda VIVA. Violación ⇒ aborto (exit 2).
    Optimizador: `scipy.optimize.minimize(method="L-BFGS-B")`, x₀ = 1.0, determinista.

Régimen declarado:
* `[DIRGEN-STRICT]` (solo lectura) — Brier canónico y orden fiduciario: se IMPORTAN, jamás se
  reimplementan ni se editan.
* `[DBBD-FUNGIBLE]` — ingesta, álgebra de sombra, optimizador y tablero.

Read-only absoluto: el motor abre el snapshot con `PRAGMA query_only=ON` y jamás ejecuta
INSERT/UPDATE/DELETE/COMMIT. La única escritura posible es el reporte JSON de laboratorio.

Uso:
    python -m scripts.laboratorio.sandbox_optimizacion_gradiente
    python -m scripts.laboratorio.sandbox_optimizacion_gradiente --json
    python -m scripts.laboratorio.sandbox_optimizacion_gradiente --probar-guardia
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy.optimize import minimize
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

RAIZ_PROYECTO = Path(__file__).resolve().parents[2]
if str(RAIZ_PROYECTO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROYECTO))

from scripts.laboratorio.sandbox_arquetipos_vectores import (  # noqa: E402
    DIMENSIONES_ESTRUCTURALES,
    NOMBRES_DIMENSION,
    _distribuciones_vigentes,
    _fila_arquetipo,
    _indice_h2h_stats,
    _numero,
)
from src.core.contracts.portfolio_math import (  # noqa: E402
    calcular_brier_multicategorico,
    resolver_orden_fiduciario_con_indiferencia,
)
from src.storage.models import FixtureSnapshot  # noqa: E402

# ── Rutas y muestreo ────────────────────────────────────────────────────────────────────────
RUTA_SNAPSHOT_DEFECTO = (
    RAIZ_PROYECTO / "qbe_observatory" / "data" / "observatory_snapshot.db"
)
RUTA_SALIDA_JSON = RAIZ_PROYECTO / "data" / "output" / "sandbox_optimizacion_reporte.json"

# Universo que publica el Visor sobre este snapshot ([LN-QBE-127]). Si la bóveda cambia de
# jornada, el script NO adivina: declara la diferencia y aborta.
N_ESPERADO = 124

# ── Reglas β ratificadas por Dirección (2026-10-29) ─────────────────────────────────────────
BETA_MIN = 0.05
BETA_MAX = 2.00
TOLERANCIA_BETA = 1e-9
PESO_IDENTIDAD = 1.0

# ── Hipótesis de sombra (ancla identidad) ───────────────────────────────────────────────────
GANANCIA_SOMBRA = 0.10
BARRIDO_GANANCIA: Tuple[float, ...] = (0.05, 0.10, 0.20)
DIRECCION_VERTICES = np.array([1.0, 0.0, -1.0])  # (LOCAL, EMPATE, VISITANTE)

# ── Celdas fuera de matriz: fijadas en α = 1.0 y declaradas (cero imputación) ───────────────
CELDAS_FIJAS: Dict[str, str] = {
    "V16": "Cuarentena [LN-QBE-123]: FotMob no publica big chances concedidas.",
    "V27": "Sin `h2h_stats` en el snapshot vigente (0 celdas) [LN-QBE-105].",
    "V28": "Récord de sede sin magnitud firmada (celda nominal, no métrica).",
    "V31": "Forma 5P sin evidencia en la traza soberana (0 insumos encendidos).",
    "V32": "Varianza ΔxPTS sin evidencia en la traza soberana (0 insumos encendidos).",
}
DIMENSIONES_OPTIMIZABLES: Tuple[str, ...] = tuple(
    dimension for dimension in DIMENSIONES_ESTRUCTURALES if dimension not in CELDAS_FIJAS
)

# ── Determinismo ────────────────────────────────────────────────────────────────────────────
SEMILLA = 20261029  # declarada por disciplina; el instrumento no consume RNG
ANCHO = 96
N_FOLDS = 5


# ═════════════════════════════════════════════════════════════════════════════════════════════
# ERRORES FIDUCIARIOS — el instrumento falla en voz alta, nunca repara en silencio
# ═════════════════════════════════════════════════════════════════════════════════════════════
class ErrorLaboratorio(RuntimeError):
    """Fallo declarado del sandbox."""


class ViolacionBetaFiduciaria(ErrorLaboratorio):
    """Un peso intentó salir de [BETA_MIN, BETA_MAX]: la regla β manda sobre el optimizador."""


class UniversoInsuficiente(ErrorLaboratorio):
    """La bóveda no publica el universo o la evidencia mínima para optimizar."""


class ConteoNoCoincide(UniversoInsuficiente):
    """El universo cargado no coincide con el `n_esperado` declarado (P0 #2)."""


class FalloOptimizacion(ErrorLaboratorio):
    """El optimizador no convergió o devolvió un vector no finito."""


# ═════════════════════════════════════════════════════════════════════════════════════════════
# NÚCLEO PURO — [DIRGEN-STRICT] (cero I/O, cero estado, cero aleatoriedad)
# ═════════════════════════════════════════════════════════════════════════════════════════════
def validar_beta(
    pesos: Sequence[float],
    etiquetas: Optional[Sequence[str]] = None,
    minimo: float = BETA_MIN,
    maximo: float = BETA_MAX,
    tolerancia: float = TOLERANCIA_BETA,
) -> np.ndarray:
    """
    Guardia β: certifica que TODO peso es finito y vive en `[minimo, maximo]`.

    Se ejecuta ANTES (x₀) y DESPUÉS (resultado) del optimizador. Cualquier violación aborta con
    las coordenadas exactas del peso culpable: el vector jamás se recorta ni se «repara».
    """
    vector = np.asarray(pesos, dtype=float)
    if vector.ndim != 1:
        raise ViolacionBetaFiduciaria(f"🚨 β: el vector de pesos debe ser 1-D; recibido {vector.shape}.")
    nombres = list(etiquetas) if etiquetas is not None else [f"α[{i}]" for i in range(vector.size)]
    for indice, valor in enumerate(vector):
        nombre = nombres[indice] if indice < len(nombres) else f"α[{indice}]"
        if not math.isfinite(float(valor)):
            raise ViolacionBetaFiduciaria(f"🚨 β: `{nombre}` no es finito ({valor!r}).")
        if float(valor) < minimo - tolerancia or float(valor) > maximo + tolerancia:
            raise ViolacionBetaFiduciaria(
                f"🚨 β: `{nombre}` = {float(valor):.9f} fuera de [{minimo}, {maximo}]. "
                "El optimizador intentó anular o desbordar una variable: se aborta el experimento."
            )
    return vector


def estandarizar_sobre(
    crudo: np.ndarray, indices_ajuste: np.ndarray
) -> np.ndarray:
    """
    Z-Score por columna con (μ, σ) poblacional de la muestra de AJUSTE.

    Las celdas ausentes viajan como `NaN` y NUNCA se imputan; σ ≤ 1e-12 declara z = 0.0
    (guarda de varianza nula). El cálculo vive dentro del fold para no filtrar información.
    """
    submuestra = crudo[indices_ajuste]
    with np.errstate(invalid="ignore"):
        medias = np.nanmean(submuestra, axis=0)
        sigmas = np.nanstd(submuestra, axis=0)
    sigmas = np.where(sigmas <= 1e-12, 0.0, sigmas)
    z = (crudo - medias) / np.where(sigmas == 0.0, 1.0, sigmas)
    z = np.where(sigmas[None, :] == 0.0, np.where(np.isnan(crudo), np.nan, 0.0), z)
    return z


def evidencia_ponderada(z: np.ndarray, mascara: np.ndarray, pesos: np.ndarray) -> np.ndarray:
    """
    s_i(α) = Σ_{j∈O_i} α_j·z_ij / Σ_{j∈O_i} α_j — media ponderada de la evidencia OBSERVADA.

    `O_i` es la máscara de celdas presentes: una celda ausente no suma al numerador ni al
    denominador (cero imputación). Un partido sin una sola celda observada declara s_i = 0.0.
    """
    observado = np.where(mascara, z, 0.0)
    numerador = np.sum(observado * pesos[None, :], axis=1)
    denominador = np.sum(mascara.astype(float) * pesos[None, :], axis=1)
    return np.divide(
        numerador, denominador, out=np.zeros_like(numerador), where=denominador > 0.0
    )


def probabilidades_sombra(
    p_base: np.ndarray,
    z: np.ndarray,
    mascara: np.ndarray,
    pesos: np.ndarray,
    favorito_local: np.ndarray,
    ganancia: float,
) -> np.ndarray:
    """
    P̃ = softmax( ln P′ + g·(s(α) − s(α₀))·δ·(1, 0, −1) ).

    Con α = α₀ el paréntesis es exactamente 0 ⇒ P̃ ≡ P′ (ancla identidad, sin segundo modelo).
    δ = +1 si el favorito es LOCAL y −1 si es VISITANTE: la evidencia positiva empuja al favorito.
    """
    s_actual = evidencia_ponderada(z, mascara, pesos)
    s_ancla = evidencia_ponderada(z, mascara, np.full_like(pesos, PESO_IDENTIDAD))
    signo = np.where(favorito_local, 1.0, -1.0)
    desplazamiento = (ganancia * (s_actual - s_ancla) * signo)[:, None] * DIRECCION_VERTICES[None, :]
    logits = np.log(np.clip(p_base, 1e-15, 1.0)) + desplazamiento
    logits = logits - logits.max(axis=1, keepdims=True)
    exponencial = np.exp(logits)
    return exponencial / exponencial.sum(axis=1, keepdims=True)


def brier_global(probabilidades: np.ndarray, y: np.ndarray) -> float:
    """BS = (1/3N)·Σ_i Σ_k (p_ik − y_ik)² — misma aritmética que [LN-QBE-100], sin redondeo."""
    return float(np.mean(np.sum((probabilidades - y) ** 2, axis=1)) / 3.0)


def perdida(
    pesos: np.ndarray,
    p_base: np.ndarray,
    y: np.ndarray,
    z: np.ndarray,
    mascara: np.ndarray,
    favorito_local: np.ndarray,
    ganancia: float,
) -> float:
    """Objetivo del descenso: Brier global de la P′ sombreada."""
    sombra = probabilidades_sombra(p_base, z, mascara, pesos, favorito_local, ganancia)
    return brier_global(sombra, y)


def optimizar_pesos(
    p_base: np.ndarray,
    y: np.ndarray,
    z: np.ndarray,
    mascara: np.ndarray,
    favorito_local: np.ndarray,
    ganancia: float,
    etiquetas: Sequence[str],
    arranques: Sequence[float] = (0.30, 1.00, 1.70),
) -> Tuple[np.ndarray, Any, int, bool]:
    """
    L-BFGS-B determinista sobre el símplex rectangular β, con guardia antes y después.

    Multi-arranque FIJO (sin RNG): el vértice sólo se declara hallado si todos los arranques
    convergen al mismo mínimo. Si dos arranques discrepan, se conserva el mejor y se declara
    `vertice_unico = False` — jamás se presenta un óptimo local como global.
    """
    mejor = None
    soluciones: List[np.ndarray] = []
    for inicio in arranques:
        x0 = validar_beta(np.full(len(etiquetas), float(inicio)), etiquetas)
        resultado = minimize(
            perdida,
            x0,
            args=(p_base, y, z, mascara, favorito_local, ganancia),
            method="L-BFGS-B",
            bounds=[(BETA_MIN, BETA_MAX)] * len(etiquetas),
            options={"maxiter": 2000, "maxfun": 50000, "ftol": 1e-14, "gtol": 1e-10},
        )
        if not resultado.success or not np.all(np.isfinite(resultado.x)):
            raise FalloOptimizacion(
                f"🚨 El optimizador no convergió (x₀={inicio}): "
                f"status={resultado.status} · {resultado.message}"
            )
        validar_beta(resultado.x, etiquetas)
        soluciones.append(resultado.x)
        if mejor is None or resultado.fun < mejor.fun:
            mejor = resultado
    assert mejor is not None
    distinto = any(float(np.max(np.abs(solucion - mejor.x))) > 1e-6 for solucion in soluciones)
    return validar_beta(mejor.x, etiquetas), mejor, len(arranques), not distinto


def vector_catalogo_32(pesos_optimizables: np.ndarray) -> List[Dict[str, Any]]:
    """Reconstruye el vector de 32 pesos: 27 optimizados + 5 fijados en la identidad."""
    mapa = dict(zip(DIMENSIONES_OPTIMIZABLES, (float(v) for v in pesos_optimizables)))
    filas: List[Dict[str, Any]] = []
    for identificador, nombre in ((f[0], f[1]) for f in _catalogo_32()):
        fijo = identificador in CELDAS_FIJAS
        valor = PESO_IDENTIDAD if fijo else float(mapa.get(identificador, PESO_IDENTIDAD))
        filas.append(
            {
                "id_variable": identificador,
                "nombre": nombre,
                "peso": round(valor, 9),
                "delta": round(valor - PESO_IDENTIDAD, 9),
                "estado": "FIJA" if fijo else "OPTIMIZADA",
                "motivo_fijado": CELDAS_FIJAS.get(identificador),
            }
        )
    return filas


def _catalogo_32() -> Tuple[Tuple[str, ...], ...]:
    """Catálogo canónico [LN-QBE-120] importado del productor puro (cero segunda verdad)."""
    from src.observatory.core.factor_attribution import _CATALOGO_32

    return _CATALOGO_32


def sha256_archivo(ruta: Path) -> str:
    """Huella del snapshot para certificar que el experimento no lo mutó."""
    digesto = hashlib.sha256()
    with open(ruta, "rb") as manejador:
        for bloque in iter(lambda: manejador.read(1024 * 1024), b""):
            digesto.update(bloque)
    return digesto.hexdigest()


# ═════════════════════════════════════════════════════════════════════════════════════════════
# INGESTA READ-ONLY — el universo del Visor, sin segunda contabilidad
# ═════════════════════════════════════════════════════════════════════════════════════════════
@dataclass
class Universo:
    """Muestra auditada + evidencia fáctica PRE-KICKOFF de cada partido."""

    ids: List[str]
    jornadas: np.ndarray
    favorito_local: np.ndarray
    p_base: np.ndarray
    y: np.ndarray
    resultados: List[str]
    crudo: np.ndarray
    tiene_evidencia: np.ndarray
    origenes: Dict[str, int]
    brier_ui: float
    brier_canonico: float
    sha_snapshot: str
    ruta_snapshot: str
    brier_inicial: float = 0.0
    # [P0 #2] Conteo exigido efectivo (--n-esperado / --universo-completo) y su procedencia.
    n_esperado_declarado: int = 0
    universo_completo: bool = False

    @property
    def n(self) -> int:
        return len(self.ids)

    @property
    def d(self) -> int:
        return int(self.crudo.shape[1])


def _motor_solo_lectura(ruta: Path):
    """Motor SQLAlchemy con `PRAGMA query_only=ON` en cada conexión (cero escritura)."""
    if not ruta.is_file():
        raise UniversoInsuficiente(f"🚨 No existe el snapshot declarado: {ruta}")
    motor = create_engine(
        f"sqlite:///{ruta.as_posix()}",
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )

    @event.listens_for(motor, "connect")
    def _blindar_conexion(conexion_dbapi, _registro):  # pragma: no cover - lado driver
        cursor = conexion_dbapi.cursor()
        try:
            cursor.execute("PRAGMA query_only=ON;")
        finally:
            cursor.close()

    return motor


def _indice_fixtures(sesion: Session) -> Dict[str, Dict[str, Any]]:
    """Última captura por partido: la MISMA fuente de P′ que consume el Visor ([LN-QBE-127])."""
    indice: Dict[str, Dict[str, Any]] = {}
    for snapshot in sesion.query(FixtureSnapshot).order_by(
        FixtureSnapshot.updated_at.desc(), FixtureSnapshot.id.desc()
    ).all():
        partidos = snapshot.matches_json or []
        if isinstance(partidos, str):
            try:
                partidos = json.loads(partidos)
            except ValueError:
                continue
        for fixture in partidos:
            if isinstance(fixture, dict) and fixture.get("id_partido"):
                indice.setdefault(str(fixture["id_partido"]), fixture)
    return indice


def _trio_captura(fixture: Dict[str, Any]) -> Optional[Tuple[float, float, float]]:
    """P′ sellada en la captura congelada, a precisión completa (sin el redondeo del DTO)."""
    try:
        local = float(fixture["p_local"])
        empate = float(fixture["p_empate"])
        visita = float(fixture["p_visitante"])
    except (KeyError, TypeError, ValueError):
        return None
    if min(local, empate, visita) < 0.0 or abs(local + empate + visita - 1.0) > 1e-6:
        return None
    return local, empate, visita


def cargar_universo(
    ruta_snapshot: Path,
    n_esperado: Optional[int] = None,
    universo_completo: bool = False,
) -> Universo:
    """
    Reconstruye EXACTAMENTE el universo del Visor: `_construir_reporte_calibracion` del
    Observatorio ([LN-QBE-127]) sobre `observatory_snapshot.db`, más la matriz de 27 celdas
    del sandbox [LN-QBE-126] (trazas soberanas + macro + H2H, cero imputación).

    [P0 #2] `n_esperado` parametriza el conteo exigido (default `N_ESPERADO = 124`, backward-compat
    con J14). `universo_completo=True` acepta el conteo real de la bóveda y lo declara.

    Guardas ruidosas: universo ≠ conteo declarado, P′ incompleta o Brier desalineado ⇒ aborto.
    """
    from app.routes.backtesting import _construir_reporte_calibracion  # import perezoso

    ruta = Path(ruta_snapshot).resolve()
    sha_antes = sha256_archivo(ruta)
    esperado = int(n_esperado) if n_esperado is not None else N_ESPERADO
    motor = _motor_solo_lectura(ruta)
    sesion = sessionmaker(bind=motor)()
    try:
        reporte = _construir_reporte_calibracion(sesion, league_id=1)
        fixtures = _indice_fixtures(sesion)
        soberanas = _distribuciones_vigentes(sesion)
        h2h = _indice_h2h_stats(sesion)
    finally:
        sesion.close()
        motor.dispose()

    micro = [partido for jornada in reporte.get("jornadas", []) for partido in jornada["partidos"]]
    total = len(micro)
    if not universo_completo and total != esperado:
        raise ConteoNoCoincide(
            f"🚨 Universo {total} ≠ {esperado} declarado por el Visor: la bóveda cambió de "
            "jornada. Use --n-esperado N o --universo-completo; no un parche silencioso."
        )

    ids: List[str] = []
    jornadas: List[int] = []
    favoritos: List[bool] = []
    p_base: List[Tuple[float, float, float]] = []
    y: List[Tuple[float, float, float]] = []
    resultados: List[str] = []
    crudo: List[List[float]] = []
    tiene_evidencia: List[bool] = []
    origenes: Dict[str, int] = {}

    for partido in micro:
        match_id = str(partido["id_partido"])
        fixture = fixtures.get(match_id) or {}
        trio = _trio_captura(fixture)
        if trio is None:
            raise UniversoInsuficiente(
                f"🚨 El partido {match_id} no porta P′ íntegra en la captura congelada."
            )
        origenes[str(partido.get("origen_p_prima"))] = (
            origenes.get(str(partido.get("origen_p_prima")), 0) + 1
        )

        orden = resolver_orden_fiduciario_con_indiferencia(
            trio[0], trio[1], trio[2], delta_alt=0.0
        )
        favorito_local = orden["r_max"] == "LOCAL"

        fila: List[float] = [float("nan")] * len(DIMENSIONES_OPTIMIZABLES)
        distribucion = soberanas.get(match_id)
        if distribucion is not None:
            from types import SimpleNamespace

            registro = SimpleNamespace(
                id=match_id,
                score_home=int(partido["goles_local"]),
                score_away=int(partido["goles_visitante"]),
                matchday_num=int(partido["jornada"]),
            )
            arquetipo = _fila_arquetipo(match_id, registro, distribucion, h2h.get(match_id, {}))
            if arquetipo is not None:
                vector = arquetipo["vector"]
                fila = [_numero(vector.get(d)) for d in DIMENSIONES_OPTIMIZABLES]
                favorito_local = arquetipo["favorito"] == "LOCAL"

        # Guarda de conteo: `NaN` es AUSENCIA, jamás una observación (cero imputación).
        fila_numerica = [
            float(valor) if valor is not None else float("nan") for valor in fila
        ]
        observadas = sum(1 for valor in fila_numerica if not math.isnan(valor))
        ids.append(match_id)
        jornadas.append(int(partido["jornada"]))
        favoritos.append(bool(favorito_local))
        p_base.append(trio)
        resultados.append(str(partido["resultado_real"]))
        y.append(
            (
                1.0 if partido["resultado_real"] == "LOCAL" else 0.0,
                1.0 if partido["resultado_real"] == "EMPATE" else 0.0,
                1.0 if partido["resultado_real"] == "VISITANTE" else 0.0,
            )
        )
        crudo.append(fila_numerica)
        tiene_evidencia.append(observadas > 0)

    registros = [
        {"p_local": p[0], "p_empate": p[1], "p_visitante": p[2], "resultado": r}
        for p, r in zip(p_base, resultados)
    ]
    brier_ui = float(reporte["resumen_temporada"]["brier_score_qbe"])
    brier_canonico = float(calcular_brier_multicategorico(registros))

    universo = Universo(
        ids=ids,
        jornadas=np.asarray(jornadas, dtype=int),
        favorito_local=np.asarray(favoritos, dtype=bool),
        p_base=np.asarray(p_base, dtype=float),
        y=np.asarray(y, dtype=float),
        resultados=resultados,
        crudo=np.asarray(crudo, dtype=float),
        tiene_evidencia=np.asarray(tiene_evidencia, dtype=bool),
        origenes=origenes,
        brier_ui=brier_ui,
        brier_canonico=brier_canonico,
        sha_snapshot=sha_antes,
        ruta_snapshot=str(ruta),
        n_esperado_declarado=(total if universo_completo else esperado),
        universo_completo=bool(universo_completo),
    )
    universo.brier_inicial = brier_global(
        probabilidades_sombra(
            universo.p_base,
            np.zeros_like(universo.crudo),
            np.zeros_like(universo.crudo, dtype=bool),
            np.full(universo.d, PESO_IDENTIDAD),
            universo.favorito_local,
            GANANCIA_SOMBRA,
        ),
        universo.y,
    )
    _certificar_paridad(universo)
    return universo


def _certificar_paridad(universo: Universo) -> None:
    """El Brier inicial DEBE coincidir con el Visor y con el plano canónico (4 decimales)."""
    vector = round(float(universo.brier_inicial), 4)
    if vector != round(universo.brier_canonico, 4) or vector != round(universo.brier_ui, 4):
        raise UniversoInsuficiente(
            "🚨 Paridad rota: vectorizado="
            f"{vector} · canónico={universo.brier_canonico} · Visor={universo.brier_ui}. "
            "El ancla identidad no reproduce la P′ auditada."
        )


# ═════════════════════════════════════════════════════════════════════════════════════════════
# EXPERIMENTO — ajuste global + validación cruzada agrupada por jornada
# ═════════════════════════════════════════════════════════════════════════════════════════════
@dataclass
class Ajuste:
    pesos: np.ndarray
    brier_optimo: float
    iteraciones: int
    evaluaciones: int
    arranques: int = 3
    vertice_unico: bool = True


def ajustar(
    universo: Universo, ganancia: float, indices: Optional[np.ndarray] = None
) -> Ajuste:
    """Estandariza SOBRE EL AJUSTE, corre L-BFGS-B multi-arranque y devuelve pesos + Brier."""
    indices = (
        np.arange(universo.n) if indices is None else np.asarray(indices, dtype=int)
    )
    z = estandarizar_sobre(universo.crudo, indices)
    mascara = ~np.isnan(z)
    pesos, resultado, arranques, unico = optimizar_pesos(
        universo.p_base[indices],
        universo.y[indices],
        z[indices],
        mascara[indices],
        universo.favorito_local[indices],
        ganancia,
        DIMENSIONES_OPTIMIZABLES,
    )
    brier = perdida(
        pesos,
        universo.p_base[indices],
        universo.y[indices],
        z[indices],
        mascara[indices],
        universo.favorito_local[indices],
        ganancia,
    )
    return Ajuste(
        pesos=pesos,
        brier_optimo=float(brier),
        iteraciones=int(getattr(resultado, "nit", 0) or 0),
        evaluaciones=int(getattr(resultado, "nfev", 0) or 0),
        arranques=int(arranques),
        vertice_unico=bool(unico),
    )


def validacion_cruzada(universo: Universo, ganancia: float) -> Dict[str, Any]:
    """
    K-fold AGRUPADO POR JORNADA (una jornada jamás se parte entre ajuste y prueba).

    Determinista: las jornadas ordenadas se reparten round-robin entre los folds. La
    estandarización se re-calcula dentro de cada fold para no filtrar μ/σ del futuro.
    """
    jornadas = sorted({int(j) for j in universo.jornadas})
    folds: List[List[int]] = [[] for _ in range(N_FOLDS)]
    for posicion, jornada in enumerate(jornadas):
        folds[posicion % N_FOLDS].append(jornada)

    filas: List[Dict[str, Any]] = []
    suma_error_base = 0.0
    suma_error_optimo = 0.0
    n_pool = 0
    for indice_fold, jornadas_fold in enumerate(folds):
        prueba = np.isin(universo.jornadas, jornadas_fold)
        ajuste_idx = np.where(~prueba & universo.tiene_evidencia)[0]
        prueba_idx = np.where(prueba)[0]
        if ajuste_idx.size < universo.d + 2 or prueba_idx.size == 0:
            raise UniversoInsuficiente(
                f"🚨 Fold {indice_fold + 1}: ajuste={ajuste_idx.size} prueba={prueba_idx.size} "
                "no sostienen el experimento."
            )
        resultado = ajustar(universo, ganancia, ajuste_idx)
        z = estandarizar_sobre(universo.crudo, ajuste_idx)
        mascara = ~np.isnan(z)
        base = perdida(
            np.full(universo.d, PESO_IDENTIDAD),
            universo.p_base[prueba_idx],
            universo.y[prueba_idx],
            z[prueba_idx],
            mascara[prueba_idx],
            universo.favorito_local[prueba_idx],
            ganancia,
        )
        optimo = perdida(
            resultado.pesos,
            universo.p_base[prueba_idx],
            universo.y[prueba_idx],
            z[prueba_idx],
            mascara[prueba_idx],
            universo.favorito_local[prueba_idx],
            ganancia,
        )
        # Agregado POOLED: cada partido lo predice el fold que no lo vio. Sumar los errores
        # cuadráticos (en vez de promediar medias de folds de distinto N) hace que el Brier
        # out-of-sample sea directamente comparable con el global de 0.2159.
        suma_error_base += float(
            np.sum(
                (
                    probabilidades_sombra(
                        universo.p_base[prueba_idx],
                        z[prueba_idx],
                        mascara[prueba_idx],
                        np.full(universo.d, PESO_IDENTIDAD),
                        universo.favorito_local[prueba_idx],
                        ganancia,
                    )
                    - universo.y[prueba_idx]
                )
                ** 2
            )
        )
        suma_error_optimo += float(
            np.sum(
                (
                    probabilidades_sombra(
                        universo.p_base[prueba_idx],
                        z[prueba_idx],
                        mascara[prueba_idx],
                        resultado.pesos,
                        universo.favorito_local[prueba_idx],
                        ganancia,
                    )
                    - universo.y[prueba_idx]
                )
                ** 2
            )
        )
        n_pool += int(prueba_idx.size)
        filas.append(
            {
                "fold": indice_fold + 1,
                "jornadas": jornadas_fold,
                "n_ajuste": int(ajuste_idx.size),
                "n_prueba": int(prueba_idx.size),
                "brier_base": round(float(base), 6),
                "brier_optimo": round(float(optimo), 6),
                "delta": round(float(optimo - base), 6),
                "victorias_beta": sorted(
                    DIMENSIONES_OPTIMIZABLES[i]
                    for i in np.argsort(-np.abs(resultado.pesos - PESO_IDENTIDAD))[:3]
                ),
            }
        )

    pesos_folds = np.array([f["brier_optimo"] for f in filas])
    base_folds = np.array([f["brier_base"] for f in filas])
    return {
        "n_folds": N_FOLDS,
        "regla": "Agrupado por jornada (round-robin determinista); μ/σ re-calculadas por fold.",
        "folds": filas,
        "pooled_base": round(float(suma_error_base / (3.0 * n_pool)), 6),
        "pooled_optimo": round(float(suma_error_optimo / (3.0 * n_pool)), 6),
        "delta_pooled": round(
            float((suma_error_optimo - suma_error_base) / (3.0 * n_pool)), 6
        ),
        "media_delta_folds": round(float((pesos_folds - base_folds).mean()), 6),
        "folds_mejoran": int((pesos_folds < base_folds).sum()),
    }


# ═════════════════════════════════════════════════════════════════════════════════════════════
# TABLERO — consola
# ═════════════════════════════════════════════════════════════════════════════════════════════
def _linea(caracter: str = "═") -> str:
    return caracter * ANCHO


def _pct(valor: float) -> str:
    return f"{valor * 100.0:+.2f}%"


def _bloque_fuente(universo: Universo, lineas: List[str]) -> None:
    evidencia = int(universo.tiene_evidencia.sum())
    sin_evidencia = universo.n - evidencia
    origenes = " · ".join(f"{clave} {valor}" for clave, valor in sorted(universo.origenes.items()))
    lineas += [
        "",
        "0 · FUENTE DE DATOS Y PARIDAD CON EL VISOR",
        f"   Snapshot   : {universo.ruta_snapshot}",
        f"   SHA-256    : {universo.sha_snapshot[:32]}…",
        f"   Universo   : {universo.n} partidos concluidos (Visor: {N_ESPERADO})",
        f"   P′         : {origenes}",
        f"   Evidencia  : {evidencia}/{universo.n} con vector de {universo.d} celdas · "
        f"{sin_evidencia} sin traza (α no informado por ellos, P′ intacta)",
        "   Celdas     : 27 optimizables + 5 fijas en 1.0 "
        f"({', '.join(sorted(CELDAS_FIJAS))})",
        f"   Ancla      : α₀ = 1.0 · g = {GANANCIA_SOMBRA:.2f} · semilla {SEMILLA}",
        f"   Paridad    : Inicial {universo.brier_inicial:.4f} == Canónico "
        f"{universo.brier_canonico:.4f} == Visor {universo.brier_ui:.4f}  [OK]",
    ]


def _bloque_optimo(
    universo: Universo,
    ajuste: Ajuste,
    barrido: Sequence[Dict[str, Any]],
    top: int,
    impactos: Dict[str, float],
) -> List[str]:
    base = universo.brier_inicial
    delta = ajuste.brier_optimo - base
    vector = vector_catalogo_32(ajuste.pesos)
    for fila in vector:
        fila["impacto"] = round(float(impactos.get(fila["id_variable"], 0.0)), 9)
    ranking = sorted(
        vector, key=lambda f: (-abs(f["delta"]), -f["impacto"], f["id_variable"])
    )
    saturados = [f for f in vector if math.isclose(f["peso"], BETA_MAX, abs_tol=1e-6)]
    anulados = [f for f in vector if math.isclose(f["peso"], BETA_MIN, abs_tol=1e-6)]
    interior = len(vector) - len(saturados) - len(anulados) - len(CELDAS_FIJAS)
    lineas = [
        "",
        "1 · BRIER GLOBAL (universo completo del Visor)",
        f"   Inicial  (α₀ = 1.0) : {base:.4f}",
        f"   Optimizado          : {ajuste.brier_optimo:.4f}   (Δ {delta:+.4f} · {_pct(delta / base)})",
        f"   Optimizador         : L-BFGS-B · {ajuste.iteraciones} iteraciones · "
        f"{ajuste.evaluaciones} evaluaciones · convergencia verificada",
        f"   Multi-arranque      : {ajuste.arranques} x₀ fijos (0.30 · 1.00 · 1.70) → "
        + ("MISMO vértice" if ajuste.vertice_unico else "VÉRTICES DISTINTOS (óptimo local)"),
        f"   Frontera β          : {len(saturados)} en 2.00 · {len(anulados)} en {BETA_MIN:.2f} · "
        f"{interior} interiores",
    ]
    if barrido:
        lineas += [
            "",
            "   Sensibilidad a la ganancia g (in-sample vs out-of-sample):",
            "     g      Brier INS   Δ INS     Brier OOS   Δ OOS    α_min  α_max",
        ]
        for fila in barrido:
            lineas.append(
                f"     {fila['g']:.2f}   {fila['brier']:.4f}    {fila['delta']:+.4f}   "
                f"{fila['cv_optimo']:.4f}     {fila['cv_delta']:+.4f}   "
                f"{fila['alpha_min']:.3f}  {fila['alpha_max']:.3f}"
            )

    lineas += ["", f"2 · TOP {top} DE PESOS QUE MÁS SE MOVIERON (|Δα|; empate: impacto en Brier)"]
    for posicion, fila in enumerate(ranking[:top], start=1):
        nombre = NOMBRES_DIMENSION.get(fila["id_variable"], fila["id_variable"])
        lineas.append(
            f"   {posicion}. {nombre[:56]:<56} α {fila['peso']:.4f}  "
            f"Δ {fila['delta']:+.4f}  impacto {fila['impacto']:+.4f}"
        )
    lineas.append(
        "   (impacto = ΔBrier si esa variable se devuelve a α = 1.0; >0 ⇒ el óptimo depende de ella)"
    )
    conductores = sorted(vector, key=lambda f: (-f["impacto"], f["id_variable"]))[:5]
    lineas.append("   Conductores REALES del ΔBrier (ordenados por impacto, no por |Δα|):")
    for fila in conductores:
        lineas.append(
            f"     {fila['id_variable']} · α {fila['peso']:.2f} · impacto {fila['impacto']:+.6f}"
        )
    return lineas


def _bloque_cv(cv: Dict[str, Any]) -> List[str]:
    lineas = [
        "",
        "3 · VALIDACIÓN CRUZADA 5-FOLD (agrupada por jornada)",
        "   Fold  Jornadas            N_aj  N_pr     Brier base   Brier opt      Δ",
        "   ────  ──────────────────  ────  ────  ────────────  ──────────  ─────────",
    ]
    for fila in cv["folds"]:
        jornadas = ",".join(f"J{j}" for j in fila["jornadas"])
        lineas.append(
            f"   {fila['fold']:>4}  {jornadas:<18}  {fila['n_ajuste']:>4}  {fila['n_prueba']:>4}"
            f"  {fila['brier_base']:>12.4f}  {fila['brier_optimo']:>10.4f}  {fila['delta']:>+9.4f}"
        )
    lineas += [
        "   ────  ──────────────────  ────  ────  ────────────  ──────────  ─────────",
        f"   POOLED OUT-OF-SAMPLE (N = {sum(f['n_prueba'] for f in cv['folds'])})   "
        f"{cv['pooled_base']:>12.4f}  {cv['pooled_optimo']:>10.4f}  {cv['delta_pooled']:>+9.4f}",
        f"   Folds que mejoran: {cv['folds_mejoran']}/{cv['n_folds']} · "
        f"media de Δ por fold: {cv['media_delta_folds']:+.4f}",
        f"   Regla: {cv['regla']}",
    ]
    return lineas


def _bloque_pureza(universo: Universo, sha_despues: str) -> List[str]:
    integra = sha_despues == universo.sha_snapshot
    return [
        "",
        "4 · DECLARACIÓN DE PUREZA",
        "   Read-only: `PRAGMA query_only=ON` · cero INSERT/UPDATE/DELETE/COMMIT",
        f"   Snapshot inmutable: SHA-256 {'IDÉNTICO' if integra else 'CAMBIÓ 🚨'}",
        "   Fuente de universo: `_construir_reporte_calibracion` del Observatorio ([LN-QBE-127])",
        "   Núcleo: Brier [LN-QBE-100] y orden fiduciario [LN-QBE-124] IMPORTADOS, no reescritos",
    ]


def calcular_impactos(universo: Universo, ajuste: Ajuste, ganancia: float) -> Dict[str, float]:
    """
    Sensibilidad de frontera: ΔBrier si cada variable se devuelve a α = 1.0 con las demás fijas.

    Desambigua el Top 5 cuando varios pesos saturan el mismo límite β: mide qué variable
    SOSTIENE de verdad la mejora in-sample, en vez de ordenar por identificador.
    """
    z = estandarizar_sobre(universo.crudo, np.arange(universo.n))
    mascara = ~np.isnan(z)
    impactos: Dict[str, float] = {}
    for indice, dimension in enumerate(DIMENSIONES_OPTIMIZABLES):
        pesos = np.array(ajuste.pesos, copy=True)
        pesos[indice] = PESO_IDENTIDAD
        impactos[dimension] = float(
            perdida(
                pesos,
                universo.p_base,
                universo.y,
                z,
                mascara,
                universo.favorito_local,
                ganancia,
            )
            - ajuste.brier_optimo
        )
    return impactos


def imprimir_tablero(
    universo: Universo,
    ajuste: Ajuste,
    cv: Dict[str, Any],
    barrido: Sequence[Dict[str, Any]],
    impactos: Dict[str, float],
    sha_despues: str,
    top: int = 5,
) -> None:
    lineas = [_linea(), "🧪 SANDBOX DE OPTIMIZACIÓN — SHADOW MODEL (Gradiente Descendente)",
              "   [LN-QBE-100] Brier · L-BFGS-B · β ∈ [0.05, 2.00] · [HÍBRIDO DUAL-TRACK]", _linea()]
    _bloque_fuente(universo, lineas)
    lineas += _bloque_optimo(universo, ajuste, barrido, top, impactos)
    lineas += _bloque_cv(cv)
    lineas += _bloque_pureza(universo, sha_despues)
    lineas += ["", _linea()]
    print("\n".join(lineas))


# ═════════════════════════════════════════════════════════════════════════════════════════════
# GUARDIA β — prueba negativa determinista
# ═════════════════════════════════════════════════════════════════════════════════════════════
def ejecutar_prueba_guardia() -> int:
    """Inyecta violaciones de β y certifica que el instrumento ABORTA (exit 2 intencional)."""
    print(_linea())
    print("🛑 PRUEBA NEGATIVA DE LA GUARDIA β — el instrumento debe abortar")
    print(_linea())
    casos: Tuple[Tuple[str, float], ...] = (
        ("desborde superior", BETA_MAX + 0.0001),
        ("negativo", -0.01),
        ("anulación (0.0)", 0.0),
        ("piso incumplido", BETA_MIN - 0.001),
        ("no finito", float("nan")),
    )
    abortados = 0
    for etiqueta, valor in casos:
        try:
            validar_beta([1.0, valor], ["α_ok", "α_prueba"])
        except ViolacionBetaFiduciaria as error:
            abortados += 1
            print(f"   🛑 {etiqueta:<20} → ABORTO CORRECTO: {error}")
        else:
            print(f"   🚨 {etiqueta:<20} → NO ABORTÓ (fallo de la guardia)")
    print(_linea())
    if abortados != len(casos):
        print(f"🚨 Guardia β incompleta: {abortados}/{len(casos)} violaciones detectadas.")
        return 4
    print(f"✅ Guardia β certificada: {abortados}/{len(casos)} violaciones abortadas.")
    print("   Exit code 2 = la regla β manda sobre el optimizador (aborto intencional).")
    return 2


# ═════════════════════════════════════════════════════════════════════════════════════════════
# PRE-VUELO — [P0 #3] --dry-run: carga, verifica, imprime y sale (cero análisis)
# ═════════════════════════════════════════════════════════════════════════════════════════════
def ruta_reporte(argumentos: argparse.Namespace, nombre: str, defecto: Path) -> Path:
    """[P0 #3.2] `--salida` redirige el JSON; sin flag se conserva `data/output/`."""
    if getattr(argumentos, "salida", None) is None:
        return defecto
    salida = Path(argumentos.salida).resolve()
    # [P0 #3.2] Prohibido pisar el reporte del piloto: `--salida` debe apuntar a otro directorio.
    if salida == (RAIZ_PROYECTO / "data" / "output").resolve():
        raise SystemExit(
            "🚨 --salida no puede ser data/output/: sobrescribiría el reporte del piloto. "
            "Use otro directorio."
        )
    salida.mkdir(parents=True, exist_ok=True)
    return salida / f"{nombre}_reporte.json"


def _imprimir_dry_run(universo: Universo, sha_despues: str) -> int:
    """[P0 #3.1] Verificación de carga del universo: nada de optimización ni de σ."""
    observado = ~np.isnan(universo.crudo)
    n_con_evidencia = int(universo.tiene_evidencia.sum())
    n_sin_evidencia = universo.n - n_con_evidencia
    coberturas = {
        dimension: int(observado[:, j].sum())
        for j, dimension in enumerate(DIMENSIONES_OPTIMIZABLES)
    }
    excluidas = [
        (dimension, cobertura)
        for dimension, cobertura in coberturas.items()
        if universo.n and cobertura / universo.n < 0.80
    ]
    lineas = [
        _linea(),
        "🧪 DRY-RUN — SANDBOX DE OPTIMIZACIÓN (solo carga y verificación)",
        _linea(),
        f"   Snapshot          : {universo.ruta_snapshot}",
        f"   SHA-256 (carga)   : {universo.sha_snapshot}",
        f"   n                 : {universo.n}",
        f"   n_esperado        : {universo.n_esperado_declarado}"
        f"{' (--universo-completo)' if universo.universo_completo else ''}",
        f"   n_con_evidencia   : {n_con_evidencia}",
        f"   n_sin_evidencia   : {n_sin_evidencia}",
        f"   Dimensiones       : {universo.d} ({', '.join(DIMENSIONES_OPTIMIZABLES)})",
        f"   Orígenes P′       : {dict(sorted(universo.origenes.items()))}",
        "   Cobertura por dimensión:",
    ]
    for dimension, cobertura in coberturas.items():
        pct = (cobertura / universo.n) * 100.0 if universo.n else 0.0
        lineas.append(f"      · {dimension:<8} {cobertura}/{universo.n} ({pct:.2f}%)")
    lineas.append("   Variables con cobertura <80% (declaradas, no imputadas):")
    if excluidas:
        for dimension, cobertura in excluidas:
            pct = (cobertura / universo.n) * 100.0 if universo.n else 0.0
            lineas.append(f"      · {dimension:<8} {cobertura}/{universo.n} ({pct:.2f}%)")
    else:
        lineas.append("      · ninguna")
    lineas += [
        f"   SHA-256 (después) : {sha_despues}",
        f"   Snapshot inmutable: {'IDÉNTICO' if sha_despues == universo.sha_snapshot else 'CAMBIÓ 🚨'}",
        f"   Conteo            : "
        f"{'COINCIDE' if universo.n == universo.n_esperado_declarado else 'NO COINCIDE 🚨'}",
        "   Análisis ejecutado: NINGUNO (SLSQP, barrido y CV no se invocan)",
        _linea(),
    ]
    print("\n".join(lineas))
    if sha_despues != universo.sha_snapshot:
        return 2
    if universo.n != universo.n_esperado_declarado:
        return 3
    return 0


# ═════════════════════════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════════════════════════
def _parsear_argumentos(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sandbox de optimización (shadow model) sobre el snapshot del Observatorio."
    )
    parser.add_argument("--snapshot", default=str(RUTA_SNAPSHOT_DEFECTO))
    parser.add_argument("--top", type=int, default=5)
    parser.add_argument("--json", action="store_true", help="Exporta el reporte de laboratorio.")
    parser.add_argument(
        "--probar-guardia",
        action="store_true",
        help="Prueba negativa de β: inyecta violaciones y certifica el aborto (exit 2).",
    )
    parser.add_argument(
        "--sin-barrido", action="store_true", help="Omite la sensibilidad a la ganancia g."
    )
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


def main(argv: Optional[Sequence[str]] = None) -> int:
    argumentos = _parsear_argumentos(argv)
    if argumentos.probar_guardia and not argumentos.dry_run:
        return ejecutar_prueba_guardia()

    try:
        universo = cargar_universo(
            Path(argumentos.snapshot),
            n_esperado=argumentos.n_esperado,
            universo_completo=argumentos.universo_completo,
        )
    except ViolacionBetaFiduciaria as error:
        print(f"\n{error}\n", file=sys.stderr)
        return 2
    except ConteoNoCoincide as error:
        print(f"\n{error}\n", file=sys.stderr)
        return 3
    except (UniversoInsuficiente, ErrorLaboratorio) as error:
        print(f"\n{error}\n", file=sys.stderr)
        return 4 if argumentos.dry_run else 3

    if argumentos.dry_run:
        sha_dry = sha256_archivo(Path(universo.ruta_snapshot))
        return _imprimir_dry_run(universo, sha_dry)

    try:
        ganancias = (GANANCIA_SOMBRA,) if argumentos.sin_barrido else BARRIDO_GANANCIA
        barrido: List[Dict[str, Any]] = []
        ajuste: Optional[Ajuste] = None
        cv: Optional[Dict[str, Any]] = None
        for ganancia in ganancias:
            resultado = ajustar(universo, ganancia)
            cv_ganancia = validacion_cruzada(universo, ganancia)
            barrido.append(
                {
                    "g": ganancia,
                    "brier": round(resultado.brier_optimo, 4),
                    "delta": round(resultado.brier_optimo - universo.brier_inicial, 4),
                    "cv_optimo": round(cv_ganancia["pooled_optimo"], 4),
                    "cv_delta": round(cv_ganancia["delta_pooled"], 4),
                    "alpha_min": float(resultado.pesos.min()),
                    "alpha_max": float(resultado.pesos.max()),
                }
            )
            if math.isclose(ganancia, GANANCIA_SOMBRA):
                ajuste, cv = resultado, cv_ganancia
        if ajuste is None or cv is None:
            ajuste, cv = ajustar(universo, GANANCIA_SOMBRA), validacion_cruzada(
                universo, GANANCIA_SOMBRA
            )
        impactos = calcular_impactos(universo, ajuste, GANANCIA_SOMBRA)
    except ViolacionBetaFiduciaria as error:
        print(f"\n{error}\n", file=sys.stderr)
        return 2
    except (FalloOptimizacion, UniversoInsuficiente) as error:
        print(f"\n{error}\n", file=sys.stderr)
        return 4

    sha_despues = sha256_archivo(Path(universo.ruta_snapshot))
    imprimir_tablero(universo, ajuste, cv, barrido, impactos, sha_despues, top=argumentos.top)

    if argumentos.json:
        reporte = {
            "ley": "[LN-QBE-100] · [LN-QBE-126] · [LN-QBE-127]",
            "instrumento": "sandbox_optimizacion_gradiente",
            "regimen": "[HÍBRIDO DUAL-TRACK]",
            "semilla": SEMILLA,
            "snapshot": {
                "ruta": universo.ruta_snapshot,
                "sha256": universo.sha_snapshot,
                "inmutable": sha_despues == universo.sha_snapshot,
            },
            "universo": {
                "n": universo.n,
                "n_esperado": universo.n_esperado_declarado,
                "universo_completo": universo.universo_completo,
                "con_evidencia": int(universo.tiene_evidencia.sum()),
                "origenes_p_prima": universo.origenes,
                "brier_inicial": round(universo.brier_inicial, 6),
                "brier_canonico": round(universo.brier_canonico, 6),
                "brier_visor": round(universo.brier_ui, 6),
            },
            "beta": {"min": BETA_MIN, "max": BETA_MAX, "fijas": sorted(CELDAS_FIJAS)},
            "sombra": {"ancla": PESO_IDENTIDAD, "ganancia": GANANCIA_SOMBRA,
                       "barrido": list(BARRIDO_GANANCIA)},
            "optimizacion": {
                "brier_inicial": round(universo.brier_inicial, 6),
                "brier_optimo": round(ajuste.brier_optimo, 6),
                "delta": round(ajuste.brier_optimo - universo.brier_inicial, 6),
                "iteraciones": ajuste.iteraciones,
                "evaluaciones": ajuste.evaluaciones,
            },
            "pesos_32": [
                {**fila, "impacto": round(float(impactos.get(fila["id_variable"], 0.0)), 9)}
                for fila in vector_catalogo_32(ajuste.pesos)
            ],
            "barrido_ganancia": barrido,
            "validacion_cruzada": cv,
        }
        ruta_salida = ruta_reporte(argumentos, "sandbox_optimizacion", RUTA_SALIDA_JSON)
        ruta_salida.parent.mkdir(parents=True, exist_ok=True)
        ruta_salida.write_text(
            json.dumps(reporte, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\n📄 Reporte exportado: {ruta_salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
