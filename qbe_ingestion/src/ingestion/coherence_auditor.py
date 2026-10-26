# -*- coding: utf-8 -*-
"""
🔎 Q-BE — SONDA DIAGNÓSTICA DE COHERENCIA RELACIONAL Y PRE-VUELO DEL CONSTRUCTOR
[ARCH-1.4.34] — CLI Auditor (Read-Only, semáforo forense)

Utilidad de SOLO LECTURA. No muta la bóveda, no emite vetos (`QBE-00`) ni reescribe expedientes.
Su única misión es la observabilidad forense: confrontar la evidencia fáctica de la cartelera
(vectores P'/P̂, cuotas, λ xG, boletos) contra las aduanas canónicas ya selladas y publicar un
veredicto semafórico para el pre-vuelo del Agente Constructor (DoD 4).

Base de Gobierno (autoridad delegada, cero umbrales inventados):
  * `docs/LOGIC.md` `[LN-QBE-007-H]` → aduana de overround (vía `docs/CONSTANTS.md`).
  * `docs/LOGIC.md` `[LN-QBE-071]` `.3` / `[LN-QBE-071-B]` → piso de ventanilla y piso bivariado.
  * `docs/LOGIC.md` `[LN-QBE-040]` / `[LN-QBE-039]` / `[LN-QBE-040-B]` → techo de goles.
  * `docs/LOGIC.md` `[LN-QBE-059]` y `[LN-QBE-060-B]` → morfología Capa 0 y triaje determinista.
  * `docs/ARCH.md` `[ARCH-1.4.34]` → contrato de esta sonda (seis sondas, degradación honesta,
    semántica de salida).
  * Decreto `VAR-2026-PREFLIGHT-LEGITIMATE-ENVELOPE` (Dictamen A1, 2026-10-13) → banda decretada del
    techo de goles `(1.8600, 2.5000]` xG (🟡), 🔴 sólo por desborde físico o λ ≤ 0.0; sonda de
    divergencia de mercado: 🔴 reservado a rupturas axiomáticas (símplex fuera de Δ² / overround
    fuera de aduana), divergencia informativa ⇒ 🟡; y guarda de ignorancia declarada
    (`suficiencia_S_I == 0` ⇒ ⚪ SIN VEREDICTO).

Degradación honesta ([GOVERNANCE-01]): la ausencia de evidencia emite `SIN_VEREDICTO` (⚪) y
JAMÁS una discrepancia. Cero invención de cifras, umbrales o bloqueos.

Uso:
    python scripts/auditoria/auditar_coherencia_cartelera.py                 # diagnóstico (read-only)
    python scripts/auditoria/auditar_coherencia_cartelera.py --check         # EXIT 1 sólo ante 🔴
    python scripts/auditoria/auditar_coherencia_cartelera.py --jornada 11    # jornada explícita
    python scripts/auditoria/auditar_coherencia_cartelera.py --todo --json   # todas las jornadas
"""

import argparse
import json
import sys
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from pydantic import BaseModel, ConfigDict, Field

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ===========================================================================
# CONSTANTES CANÓNICAS — transcritas del Libro de Constantes sellado
# ===========================================================================
# [LN-QBE-007-H] Aduana de Sanidad Comercial de Overround (docs/CONSTANTS.md)
OVERROUND_MIN_ADMISIBLE = 0.8500
OVERROUND_MAX_ADMISIBLE = 1.3000
# Banda de VIGILANCIA diagnóstica (no veto): margen comercial elevado o no positivo.
OVERROUND_VIGILANCIA_MAX = 1.2500
OVERROUND_VIGILANCIA_MIN = 1.0000

# [LN-QBE-071] .3 / [LN-QBE-071-B] Piso Estructural Bivariado ($4.00 MXN) y piso de ventanilla
PISO_VENTANILLA_MXN = 2.00
PISO_BIVARIADO_MXN = 4.00
FAMILIAS_CON_COBERTURA: Tuple[str, ...] = ("QBE-H1", "QBE-H2", "QBE-R1", "QBE-R2", "QBE-C1")

# [LN-QBE-040] / [LN-QBE-040-B] Techo conjunto de intensidad ofensiva (anti-resonancia).
# Decreto `VAR-2026-PREFLIGHT-LEGITIMATE-ENVELOPE` (Dictamen A1 — umbrales decretados, transcripción
# literal; cero calibración autónoma):
#   🟢 λ_max ≤ 1.8600 xG · 🟡 1.8600 < λ_max ≤ 2.5000 xG (asimetría legítima de plaza) ·
#   🔴 λ_max > 2.5000 xG o λ ≤ 0.0 xG (desborde físico / captura corrupta).
# `TECHO_XG` es un límite de ESCALA FÍSICA de Liga MX para el semáforo del auditor: NO es la cota
# del motor sellado (`[LN-QBE-040-B]` garantiza λ ≤ 1.8600 xG en duelos equilibrados y el clamp
# canónico del plano de intensidades es más amplio).
TECHO_XG_ANTIRESONANCIA = 1.8600
TECHO_XG = 2.5000

# [LN-QBE-059] / [LN-QBE-060-B] Parámetro de partición morfológica
GAMMA_BASE = 0.67
TOL_PARIDAD_SIMPLEX = 5e-4

# Divergencia de mercado (P' del modelo vs. distribución vig-free del operador)
TVD_MAX = 0.22
TVD_VIGILANCIA = 0.15

# Identificadores estables de las seis sondas (contrato público del reporte)
SONDA_PARIDAD = "paridad_simplex"
SONDA_OVERROUND = "overround_comercial"
SONDA_PISO_VENTANILLA = "piso_ventanilla"
SONDA_TECHO_GOLES = "techo_goles"
SONDA_COHERENCIA_CAPA0 = "coherencia_capa0"
SONDA_DIVERGENCIA_MERCADO = "divergencia_mercado"

ORDEN_SONDAS: Tuple[str, ...] = (
    SONDA_PARIDAD,
    SONDA_OVERROUND,
    SONDA_PISO_VENTANILLA,
    SONDA_TECHO_GOLES,
    SONDA_COHERENCIA_CAPA0,
    SONDA_DIVERGENCIA_MERCADO,
)


# ===========================================================================
# MODELOS (Pydantic V2 — contratos inmutables)
# ===========================================================================
class NivelSeveridad(str, Enum):
    """Veredicto semafórico de una sonda. La ausencia de evidencia NO es un defecto."""

    CONFORME = "CONFORME"            # 🟢
    ADVERTENCIA = "ADVERTENCIA"      # 🟡
    DISCREPANCIA = "DISCREPANCIA"    # 🔴
    SIN_VEREDICTO = "SIN_VEREDICTO"  # ⚪


# Glifos universales y neutros por nivel ([ARCH-1.4.12-B] · Decreto `VAR-2026-DRIFT-STREAM-MAP`):
# quedan PROHIBIDOS los emojis de bandera regional (p. ej. el par `U+1F1FE U+1F1EA`, que Windows
# descompone en los caracteres alfabéticos `Y` y `E`): el nivel sin veredicto emite `⚪`.
GLIFO_NIVEL: Dict[str, str] = {
    NivelSeveridad.CONFORME.value: "🟢",
    NivelSeveridad.ADVERTENCIA.value: "🟡",
    NivelSeveridad.DISCREPANCIA.value: "🔴",
    NivelSeveridad.SIN_VEREDICTO.value: "⚪",
}


class HallazgoSonda(BaseModel):
    """Resultado de una sonda sobre un partido: sonda, veredicto, detalle y métrica observable."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    sonda: str
    titulo: str
    nivel: NivelSeveridad
    detalle: str
    metrica: Optional[float] = None


class ReporteCoherenciaPartido(BaseModel):
    """Expediente diagnóstico de un partido: seis hallazgos y el veredicto agregado."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    id_partido: Optional[str] = None
    etiqueta: str
    hallazgos: List[HallazgoSonda] = Field(default_factory=list)
    nivel_global: NivelSeveridad = NivelSeveridad.SIN_VEREDICTO
    apto_pre_vuelo: bool = True


# ===========================================================================
# HELPERS DE LECTURA (puros, sin efectos)
# ===========================================================================
def _es_numero(valor: Any) -> bool:
    """Booleans NO son números de negocio (evita `True == 1` contaminando cuotas)."""
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def _vector_p(
    data: Dict[str, Any], claves: Sequence[str] = ("p_local", "p_empate", "p_visitante")
) -> Optional[Tuple[float, float, float]]:
    """Extrae un vector de Δ² declarado; `None` si la evidencia está incompleta."""
    valores = [data.get(clave) for clave in claves]
    if not all(_es_numero(v) for v in valores):
        return None
    return (float(valores[0]), float(valores[1]), float(valores[2]))


def _momios(data: Dict[str, Any]) -> Optional[Tuple[float, float, float]]:
    """Extrae las cuotas 1X2 si son comercialmente plausibles (> 1.00)."""
    crudo = data.get("momios")
    if not isinstance(crudo, dict):
        return None
    valores = [crudo.get(clave) for clave in ("L", "E", "V")]
    if not all(_es_numero(v) and float(v) > 1.0 for v in valores):
        return None
    return (float(valores[0]), float(valores[1]), float(valores[2]))


def _overround(momios: Sequence[float]) -> float:
    """S = Σ (1/o_i): la comisión implícita de la casa ([LN-QBE-007-H])."""
    return sum(1.0 / float(o) for o in momios)


def _probabilidades_vig_free(momios: Sequence[float]) -> Tuple[float, float, float]:
    """[LN-QBE-007-C] Descuento de margen: símplex implícito del operador."""
    s = _overround(momios)
    return (1.0 / float(momios[0]) / s, 1.0 / float(momios[1]) / s, 1.0 / float(momios[2]) / s)


def _sin_veredicto(sonda: str, titulo: str, detalle: str, metrica: Optional[float] = None) -> HallazgoSonda:
    """Degradación honesta ([GOVERNANCE-01]): ausencia de evidencia ⇒ ⚪, nunca 🔴."""
    return HallazgoSonda(
        sonda=sonda, titulo=titulo, nivel=NivelSeveridad.SIN_VEREDICTO, detalle=detalle, metrica=metrica
    )


# ===========================================================================
# SONDA 1 — PARIDAD DE VECTORES EN Δ²
# ===========================================================================
def _sonda_paridad(data: Dict[str, Any]) -> HallazgoSonda:
    titulo = "Paridad en Δ²"
    vectores: List[Tuple[str, Tuple[float, float, float]]] = []

    p_prima_crudo = data.get("p_prima")
    if isinstance(p_prima_crudo, dict):
        p_prima = _vector_p(p_prima_crudo, ("local", "empate", "visitante"))
        if p_prima is not None:
            vectores.append(("P'", p_prima))

    p_hat = _vector_p(data)
    if p_hat is not None:
        vectores.append(("P^", p_hat))

    if not vectores:
        return _sin_veredicto(
            SONDA_PARIDAD, titulo,
            "sin vectores P' / P^ en el expediente: evidencia ausente, no defecto",
        )

    for etiqueta, vector in vectores:
        desvio = abs(sum(vector) - 1.0)
        fuera_del_simplex = any(x < 0.0 or x > 1.0 for x in vector)
        if fuera_del_simplex or desvio > TOL_PARIDAD_SIMPLEX:
            return HallazgoSonda(
                sonda=SONDA_PARIDAD,
                titulo=titulo,
                nivel=NivelSeveridad.DISCREPANCIA,
                detalle=(
                    f"{etiqueta} fuera de Δ²: Σ={sum(vector):.4f} "
                    f"(desvío {desvio:.4f} > tol {TOL_PARIDAD_SIMPLEX:.4f})"
                ),
                metrica=round(desvio, 6),
            )

    auditados = " y ".join(etiqueta for etiqueta, _ in vectores)
    desvio_max = max(abs(sum(v) - 1.0) for _, v in vectores)
    return HallazgoSonda(
        sonda=SONDA_PARIDAD,
        titulo=titulo,
        nivel=NivelSeveridad.CONFORME,
        detalle=f"{auditados} viven en Δ² (Σ=1.0000, tol {TOL_PARIDAD_SIMPLEX:.4f})",
        metrica=round(desvio_max, 6),
    )


# ===========================================================================
# SONDA 2 — ADUANA DE OVERROUND ([LN-QBE-007-H] vía docs/CONSTANTS.md)
# ===========================================================================
def _sonda_overround(data: Dict[str, Any]) -> HallazgoSonda:
    titulo = "Aduana de Overround Comercial"
    momios = _momios(data)
    if momios is None:
        return _sin_veredicto(
            SONDA_OVERROUND, titulo,
            "sin cuotas 1X2 publicadas (momios ausentes): no hay margen comercial que auditar",
        )

    s = _overround(momios)
    if s < OVERROUND_MIN_ADMISIBLE or s > OVERROUND_MAX_ADMISIBLE:
        return HallazgoSonda(
            sonda=SONDA_OVERROUND, titulo=titulo, nivel=NivelSeveridad.DISCREPANCIA,
            detalle=(
                f"overround S={s:.4f} fuera de la aduana canónica "
                f"[{OVERROUND_MIN_ADMISIBLE:.4f}, {OVERROUND_MAX_ADMISIBLE:.4f}] ([LN-QBE-007-H])"
            ),
            metrica=round(s, 6),
        )

    if s > OVERROUND_VIGILANCIA_MAX:
        return HallazgoSonda(
            sonda=SONDA_OVERROUND, titulo=titulo, nivel=NivelSeveridad.ADVERTENCIA,
            detalle=(
                f"S={s:.4f} dentro de la aduana pero en banda de vigilancia "
                f"({OVERROUND_VIGILANCIA_MAX:.4f}, {OVERROUND_MAX_ADMISIBLE:.4f}]"
            ),
            metrica=round(s, 6),
        )

    if s < OVERROUND_VIGILANCIA_MIN:
        return HallazgoSonda(
            sonda=SONDA_OVERROUND, titulo=titulo, nivel=NivelSeveridad.ADVERTENCIA,
            detalle=f"S={s:.4f} con margen no positivo: posible arbitraje cross-market o captura corrupta",
            metrica=round(s, 6),
        )

    return HallazgoSonda(
        sonda=SONDA_OVERROUND, titulo=titulo, nivel=NivelSeveridad.CONFORME,
        detalle=(
            f"S={s:.4f} dentro de la aduana canónica "
            f"[{OVERROUND_MIN_ADMISIBLE:.4f}, {OVERROUND_MAX_ADMISIBLE:.4f}]"
        ),
        metrica=round(s, 6),
    )


# ===========================================================================
# SONDA 3 — PISO DE VENTANILLA Y PISO BIVARIADO ([LN-QBE-071] .3 / [LN-QBE-071-B])
# ===========================================================================
def _sonda_piso_ventanilla(data: Dict[str, Any]) -> HallazgoSonda:
    titulo = "Piso de Ventanilla y Piso Bivariado"
    boletos_crudos = data.get("boletos")
    if not isinstance(boletos_crudos, (list, tuple)) or not boletos_crudos:
        return _sin_veredicto(
            SONDA_PISO_VENTANILLA, titulo,
            f"sin boletos declarados: no hay montos que contrastar contra el piso de ${PISO_VENTANILLA_MXN:.2f} MXN",
        )

    if not all(_es_numero(b) for b in boletos_crudos):
        return _sin_veredicto(
            SONDA_PISO_VENTANILLA, titulo,
            "boletos declarados con formato no numérico: evidencia ilegible, no defecto",
        )

    boletos = [float(b) for b in boletos_crudos]
    codigo = str(data.get("estrategia_codigo") or "").strip().upper()

    no_positivos = [b for b in boletos if b <= 0.0]
    if no_positivos:
        return HallazgoSonda(
            sonda=SONDA_PISO_VENTANILLA, titulo=titulo, nivel=NivelSeveridad.DISCREPANCIA,
            detalle=f"boleto(s) sin monto positivo: {no_positivos}",
            metrica=round(min(boletos), 4),
        )

    bajo_piso = [b for b in boletos if b < PISO_VENTANILLA_MXN]
    if bajo_piso:
        return HallazgoSonda(
            sonda=SONDA_PISO_VENTANILLA, titulo=titulo, nivel=NivelSeveridad.DISCREPANCIA,
            detalle=(
                f"boleto(s) bajo el piso legal de ${PISO_VENTANILLA_MXN:.2f} MXN: {bajo_piso} "
                f"([LN-QBE-071] .3)"
            ),
            metrica=round(min(boletos), 4),
        )

    total = round(sum(boletos), 4)
    if codigo in FAMILIAS_CON_COBERTURA and len(boletos) >= 2 and total < PISO_BIVARIADO_MXN:
        return HallazgoSonda(
            sonda=SONDA_PISO_VENTANILLA, titulo=titulo, nivel=NivelSeveridad.DISCREPANCIA,
            detalle=(
                f"familia con cobertura {codigo}: exposición bivariada ${total:.2f} MXN bajo el piso "
                f"estructural de ${PISO_BIVARIADO_MXN:.2f} MXN ([LN-QBE-071-B])"
            ),
            metrica=total,
        )

    if codigo in FAMILIAS_CON_COBERTURA:
        return HallazgoSonda(
            sonda=SONDA_PISO_VENTANILLA, titulo=titulo, nivel=NivelSeveridad.CONFORME,
            detalle=(
                f"{codigo}: exposición ${total:.2f} MXN ≥ ${PISO_BIVARIADO_MXN:.2f} MXN "
                f"y boletos ≥ ${PISO_VENTANILLA_MXN:.2f} MXN"
            ),
            metrica=total,
        )

    return HallazgoSonda(
        sonda=SONDA_PISO_VENTANILLA, titulo=titulo, nivel=NivelSeveridad.CONFORME,
        detalle=(
            f"boletos ≥ ${PISO_VENTANILLA_MXN:.2f} MXN; familia '{codigo or 'sin declarar'}' "
            f"sin piso bivariado aplicable"
        ),
        metrica=total,
    )


# ===========================================================================
# SONDA 4 — TECHO DE INTENSIDAD OFENSIVA ([LN-QBE-040] / [LN-QBE-040-B])
# ===========================================================================
def _sonda_techo_goles(data: Dict[str, Any]) -> HallazgoSonda:
    titulo = "Techo de Intensidad Ofensiva (Anti-Resonancia)"
    intensidades = [float(v) for v in (data.get("lambda_home"), data.get("lambda_away")) if _es_numero(v)]

    if not intensidades:
        return _sin_veredicto(
            SONDA_TECHO_GOLES, titulo,
            "sin intensidades λ (xG) declaradas: no hay techo ofensivo que auditar",
        )

    if any(lam <= 0.0 for lam in intensidades):
        return HallazgoSonda(
            sonda=SONDA_TECHO_GOLES, titulo=titulo, nivel=NivelSeveridad.DISCREPANCIA,
            detalle=(
                f"intensidad λ no positiva (λ ≤ 0.0000 xG: captura corrupta o dirección invertida): "
                f"{intensidades}"
            ),
            metrica=round(min(intensidades), 4),
        )

    lam_max = max(intensidades)
    if lam_max > TECHO_XG:
        return HallazgoSonda(
            sonda=SONDA_TECHO_GOLES, titulo=titulo, nivel=NivelSeveridad.DISCREPANCIA,
            detalle=(
                f"λ_max={lam_max:.4f} xG excede el límite de escala física {TECHO_XG:.4f} xG "
                f"(decreto `VAR-2026-PREFLIGHT-LEGITIMATE-ENVELOPE`): desborde o resonancia patológica"
            ),
            metrica=round(lam_max, 4),
        )

    if lam_max > TECHO_XG_ANTIRESONANCIA:
        return HallazgoSonda(
            sonda=SONDA_TECHO_GOLES, titulo=titulo, nivel=NivelSeveridad.ADVERTENCIA,
            detalle=(
                f"λ_max={lam_max:.4f} xG dentro del límite físico pero en banda de vigilancia "
                f"anti-resonancia ({TECHO_XG_ANTIRESONANCIA:.4f}, {TECHO_XG:.4f}] (asimetría de plaza)"
            ),
            metrica=round(lam_max, 4),
        )

    return HallazgoSonda(
        sonda=SONDA_TECHO_GOLES, titulo=titulo, nivel=NivelSeveridad.CONFORME,
        detalle=f"λ_max={lam_max:.4f} xG ≤ {TECHO_XG_ANTIRESONANCIA:.4f} xG (banda sana)",
        metrica=round(lam_max, 4),
    )


# ===========================================================================
# SONDA 5 — COHERENCIA CAPA 0 VS. ESTRATEGIA DECLARADA ([LN-QBE-059] / [LN-QBE-060-B])
# ===========================================================================
def _sonda_coherencia_capa0(data: Dict[str, Any]) -> HallazgoSonda:
    titulo = "Coherencia Capa 0 vs. Estrategia Declarada"
    p_hat = _vector_p(data)
    if p_hat is None:
        return _sin_veredicto(
            SONDA_COHERENCIA_CAPA0, titulo,
            "sin vector P^ informativo: imposible cotejar contra el triaje canónico",
        )

    momios = _momios(data)
    if momios is None:
        return _sin_veredicto(
            SONDA_COHERENCIA_CAPA0, titulo,
            "sin cuotas 1X2 fácticas: el triaje canónico no puede emitir estrategia sin precio",
        )

    from src.core.contracts.portfolio_math import triaje_determinista_9_estrategias
    from src.core.simplex_morphology import clasificar_morfologia_simplex

    morfologia = clasificar_morfologia_simplex(p_hat, gamma=GAMMA_BASE).familia
    crudo = data.get("momios") if isinstance(data.get("momios"), dict) else {}
    cuotas: Dict[str, Any] = {
        "L": momios[0],
        "E": momios[1],
        "V": momios[2],
        "pa": bool(crudo.get("pago_anticipado")),
        "DNB": float(crudo.get("DNB")) if _es_numero(crudo.get("DNB")) else 0.0,
        "Under_25": float(crudo.get("Under_25")) if _es_numero(crudo.get("Under_25")) else 0.0,
    }
    payload_triaje: Dict[str, Any] = {
        "p_local": p_hat[0],
        "p_empate": p_hat[1],
        "p_visitante": p_hat[2],
        "es_operable": bool(data.get("es_operable", True)),
        "delta_epist": float(data.get("delta_epist")) if _es_numero(data.get("delta_epist")) else 0.0,
        "p_under_25": float(data.get("p_under_25")) if _es_numero(data.get("p_under_25")) else 0.0,
    }

    emitido = str(triaje_determinista_9_estrategias(payload_triaje, cuotas, gamma=GAMMA_BASE).get("codigo", "QBE-00"))
    declarado = str(data.get("estrategia_codigo") or "").strip().upper()

    if not declarado:
        return _sin_veredicto(
            SONDA_COHERENCIA_CAPA0, titulo,
            f"sin estrategia declarada en el expediente; el triaje canónico emite {emitido} (morfología {morfologia})",
        )

    if declarado == emitido:
        return HallazgoSonda(
            sonda=SONDA_COHERENCIA_CAPA0, titulo=titulo, nivel=NivelSeveridad.CONFORME,
            detalle=f"la estrategia declarada {declarado} coincide con el triaje canónico (morfología {morfologia})",
        )

    return HallazgoSonda(
        sonda=SONDA_COHERENCIA_CAPA0, titulo=titulo, nivel=NivelSeveridad.DISCREPANCIA,
        detalle=(
            f"discrepancia de Capa 0: el expediente declara {declarado} pero el triaje canónico "
            f"emite {emitido} (morfología {morfologia})"
        ),
    )


# ===========================================================================
# SONDA 6 — DIVERGENCIA DE MERCADO (TVD MODELO vs. OPERADOR)
# ===========================================================================
def _sonda_divergencia_mercado(data: Dict[str, Any]) -> HallazgoSonda:
    titulo = "Divergencia Mercado vs. Modelo (TVD)"
    p_hat = _vector_p(data)
    momios = _momios(data)

    if p_hat is None:
        return _sin_veredicto(
            SONDA_DIVERGENCIA_MERCADO, titulo,
            "sin vector P^ del modelo: no hay distribución que contrastar contra el operador",
        )
    if momios is None:
        return _sin_veredicto(
            SONDA_DIVERGENCIA_MERCADO, titulo,
            "sin cuotas 1X2 publicadas: no existe distribución vig-free contra la cual medir divergencia",
        )

    q_vig_free = _probabilidades_vig_free(momios)
    tvd = 0.5 * sum(abs(p - q) for p, q in zip(p_hat, q_vig_free))

    # -- Degradación Honesta: ignorancia declarada por el motor (S(I) = 0 ⇒ Prior Fiduciario) --
    # Decreto `VAR-2026-PREFLIGHT-LEGITIMATE-ENVELOPE` §2: un modelo que declara honestamente
    # «no tengo datos suficientes» jamás se penaliza como si hubiera emitido una mala predicción.
    suficiencia = data.get("suficiencia_S_I")
    if _es_numero(suficiencia) and int(suficiencia) == 0:
        return _sin_veredicto(
            SONDA_DIVERGENCIA_MERCADO, titulo,
            "S(I) = 0 declarado por el motor (Prior Fiduciario): no hay distribución informada que contrastar.",
            metrica=round(tvd, 4),
        )

    # -- 🔴 exclusivo de RUPTURAS AXIOMÁTICAS (vectores fuera de Δ² o cuotas fuera de aduana) --
    if abs(sum(p_hat) - 1.0) > TOL_PARIDAD_SIMPLEX:
        return HallazgoSonda(
            sonda=SONDA_DIVERGENCIA_MERCADO, titulo=titulo, nivel=NivelSeveridad.DISCREPANCIA,
            detalle=(
                f"ruptura axiomática: P^=({p_hat[0]:.4f}, {p_hat[1]:.4f}, {p_hat[2]:.4f}) "
                f"no pertenece a Δ² (Σ={sum(p_hat):.6f} ≠ 1.0000)"
            ),
            metrica=round(tvd, 6),
        )
    overround = _overround(momios)
    if not (OVERROUND_MIN_ADMISIBLE <= overround <= OVERROUND_MAX_ADMISIBLE):
        return HallazgoSonda(
            sonda=SONDA_DIVERGENCIA_MERCADO, titulo=titulo, nivel=NivelSeveridad.DISCREPANCIA,
            detalle=(
                f"ruptura axiomática: margen comercial S={overround:.4f} fuera de la aduana canónica "
                f"[{OVERROUND_MIN_ADMISIBLE:.4f}, {OVERROUND_MAX_ADMISIBLE:.4f}] ([LN-QBE-007-H])"
            ),
            metrica=round(tvd, 6),
        )

    # -- Divergencia informativa modelo ↔ mercado: jamas 🔴 (es la esencia de la búsqueda de Alpha) --
    if tvd > TVD_MAX:
        return HallazgoSonda(
            sonda=SONDA_DIVERGENCIA_MERCADO, titulo=titulo, nivel=NivelSeveridad.ADVERTENCIA,
            detalle=(
                f"TVD={tvd:.4f} excede el umbral informativo de {TVD_MAX:.2f}: divergencia declarada "
                f"modelo↔mercado (búsqueda de valor, NO ruptura axiomática); "
                f"P^=({p_hat[0]:.4f}, {p_hat[1]:.4f}, {p_hat[2]:.4f}) vs. "
                f"vig-free=({q_vig_free[0]:.4f}, {q_vig_free[1]:.4f}, {q_vig_free[2]:.4f})"
            ),
            metrica=round(tvd, 6),
        )

    if tvd > TVD_VIGILANCIA:
        return HallazgoSonda(
            sonda=SONDA_DIVERGENCIA_MERCADO, titulo=titulo, nivel=NivelSeveridad.ADVERTENCIA,
            detalle=f"TVD={tvd:.4f} en banda de vigilancia ({TVD_VIGILANCIA:.2f}, {TVD_MAX:.2f}]",
            metrica=round(tvd, 6),
        )

    return HallazgoSonda(
        sonda=SONDA_DIVERGENCIA_MERCADO, titulo=titulo, nivel=NivelSeveridad.CONFORME,
        detalle=f"TVD={tvd:.4f} ≤ {TVD_VIGILANCIA:.2f}: modelo y mercado comparten dirección de valor",
        metrica=round(tvd, 6),
    )


# ===========================================================================
# NÚCLEO PURO: EXPEDIENTE DIAGNÓSTICO DE UN PARTIDO
# ===========================================================================
def _agregar_nivel(hallazgos: Sequence[HallazgoSonda]) -> NivelSeveridad:
    """
    Agregación semafórica conservadora y honesta:
      🔴 si existe DISCREPANCIA; 🟡 si existe ADVERTENCIA o si la cobertura de evidencia es
      parcial (hay 🟢 pero alguna sonda quedó ⚪); 🟢 sólo con evidencia completa y conforme;
      ⚪ si ninguna sonda pudo pronunciarse (jornada sin mercado ni vectores).
    """
    niveles = [h.nivel for h in hallazgos]
    if NivelSeveridad.DISCREPANCIA in niveles:
        return NivelSeveridad.DISCREPANCIA
    if NivelSeveridad.ADVERTENCIA in niveles:
        return NivelSeveridad.ADVERTENCIA
    if niveles and all(n == NivelSeveridad.CONFORME for n in niveles):
        return NivelSeveridad.CONFORME
    if NivelSeveridad.CONFORME in niveles:
        return NivelSeveridad.ADVERTENCIA  # cobertura de evidencia parcial
    return NivelSeveridad.SIN_VEREDICTO


def auditar_coherencia_partido(data: Dict[str, Any]) -> ReporteCoherenciaPartido:
    """
    [ARCH-1.4.34] Función PURA (sin E/S, sin mutación): ejecuta las seis sondas sobre el
    expediente fáctico de un partido y devuelve el reporte semafórico agregado.

    `apto_pre_vuelo` sólo es `False` ante DISCREPANCIA: el diagnóstico informa, no veta.
    """
    expediente: Dict[str, Any] = dict(data or {})
    hallazgos: List[HallazgoSonda] = [
        _sonda_paridad(expediente),
        _sonda_overround(expediente),
        _sonda_piso_ventanilla(expediente),
        _sonda_techo_goles(expediente),
        _sonda_coherencia_capa0(expediente),
        _sonda_divergencia_mercado(expediente),
    ]
    nivel_global = _agregar_nivel(hallazgos)

    id_partido = expediente.get("id_partido")
    etiqueta = str(expediente.get("etiqueta") or "").strip()
    if not etiqueta:
        local = str(expediente.get("local") or "").strip()
        visitante = str(expediente.get("visitante") or "").strip()
        etiqueta = f"{local} vs {visitante}".strip() if (local or visitante) else str(id_partido or "partido sin identidad")

    return ReporteCoherenciaPartido(
        id_partido=str(id_partido) if id_partido else None,
        etiqueta=etiqueta,
        hallazgos=hallazgos,
        nivel_global=nivel_global,
        apto_pre_vuelo=nivel_global != NivelSeveridad.DISCREPANCIA,
    )


def calcular_codigo_salida(reportes: Iterable[ReporteCoherenciaPartido]) -> int:
    """
    [ARCH-1.4.34] Contrato de salida del CLI: `1` exclusivamente ante 🔴 DISCREPANCIA.
    🟡 ADVERTENCIA y ⚪ SIN VEREDICTO no bloquean el pre-vuelo (`[GOVERNANCE-01]`).
    """
    for reporte in reportes:
        if reporte.nivel_global == NivelSeveridad.DISCREPANCIA:
            return 1
    return 0


# ===========================================================================
# CLI (SOLO LECTURA) — PRE-VUELO DIAGNÓSTICO
# ===========================================================================
def _expediente_desde_fixture(partido: Dict[str, Any]) -> Dict[str, Any]:
    """Traduce un partido de `FixtureSnapshot.matches_json` al expediente de la sonda.

    Contrato de captura: 6 claves numéricas de P′ + el sello de suficiencia `suficiencia_S_I`
    (0 ó 1) transcrito *verbatim* de `SovereignDistributionOutput.audit_trace.suficiencia_S_I`
    (Decreto `VAR-2026-PREFLIGHT-LEGITIMATE-ENVELOPE` §1.2). Un fixture legado sin el sello se
    transcribe como `None` ⇒ la sonda de divergencia NO degrada por ausencia de señal.
    """
    momios = partido.get("momios") if isinstance(partido.get("momios"), dict) else {}
    local = str(partido.get("local") or "").strip()
    visitante = str(partido.get("visitante") or "").strip()
    return {
        "id_partido": partido.get("id_partido"),
        "etiqueta": f"{local} vs {visitante}".strip() if (local or visitante) else None,
        "p_local": partido.get("p_local"),
        "p_empate": partido.get("p_empate"),
        "p_visitante": partido.get("p_visitante"),
        "lambda_home": partido.get("lambda_home"),
        "lambda_away": partido.get("lambda_away"),
        "momios": momios,
        "es_operable": partido.get("es_operable", True),
        # Sello de suficiencia fáctica S(I) del motor (0 = Prior Fiduciario declarado).
        "suficiencia_S_I": partido.get("suficiencia_S_I"),
        # Sólo se transcribe lo que la bóveda declare: cero estrategias ni boletos inventados.
        "estrategia_codigo": partido.get("estrategia_codigo") or partido.get("codigo_triaje"),
        "boletos": partido.get("boletos"),
    }


def _imprimir_reporte(reporte: ReporteCoherenciaPartido) -> None:
    glifo = GLIFO_NIVEL[reporte.nivel_global.value]
    encabezado = f"{reporte.id_partido or 'SIN-ID'}  {reporte.etiqueta}"
    print(f"\n{glifo} [{reporte.nivel_global.value}] {encabezado}")
    for hallazgo in reporte.hallazgos:
        glifo_sonda = GLIFO_NIVEL[hallazgo.nivel.value]
        print(f"    {glifo_sonda} {hallazgo.titulo}: {hallazgo.detalle}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Punto de entrada. Read-Only: no muta la bóveda ni escribe archivos."""
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # pragma: no cover - consolas exóticas
        pass

    parser = argparse.ArgumentParser(
        prog="auditar_coherencia_cartelera",
        description="[ARCH-1.4.34] Sonda diagnóstica de coherencia relacional (solo lectura).",
    )
    parser.add_argument("--check", action="store_true", help="EXIT CODE 1 exclusivamente ante 🔴 DISCREPANCIA")
    parser.add_argument("--json", action="store_true", help="emite el reporte completo en JSON")
    parser.add_argument("--jornada", type=int, default=None, help="jornada explícita a auditar")
    parser.add_argument("--liga", type=int, default=None, help="frontera de competencia (default: Liga MX)")
    parser.add_argument("--todo", action="store_true", help="audita todas las jornadas con cartelera persistida")
    argumentos = parser.parse_args(argv)

    from src.ingestion.daemons.centinela_mercado import (
        FRONTERA_LIGA_MX_ID,
        cargar_fixtures_por_jornada,
        resolver_jornada_activa_dinamica,
    )

    liga = argumentos.liga if argumentos.liga is not None else FRONTERA_LIGA_MX_ID
    cartelera = cargar_fixtures_por_jornada(liga)

    if argumentos.jornada is not None:
        jornadas: List[int] = [argumentos.jornada]
    elif argumentos.todo:
        jornadas = sorted(int(j) for j in cartelera)
    else:
        activa = resolver_jornada_activa_dinamica(cartelera)
        jornadas = [] if activa is None else [int(activa)]

    salida_humana = not argumentos.json
    if salida_humana:
        print("=" * 78)
        print("🔎 Q-BE — SONDA DE COHERENCIA RELACIONAL Y PRE-VUELO DIAGNÓSTICO [ARCH-1.4.34]")
        print("   Régimen: SOLO LECTURA · sin mutaciones · sin vetos (`QBE-00` intacto)")
        print("=" * 78)

        if not jornadas:
            print("⚪ SIN VEREDICTO: la bóveda no registra jornada alguna (cero invención de cartelera).")
            return 0

    reportes: List[ReporteCoherenciaPartido] = []
    for jornada in jornadas:
        partidos = [p for p in (cartelera.get(jornada) or []) if isinstance(p, dict)]
        if salida_humana:
            print(f"\n── JORNADA {jornada} · {len(partidos)} partido(s) en cartelera ──")
            if not partidos:
                print("⚪ SIN VEREDICTO: jornada sin partidos persistidos.")
        for partido in partidos:
            reporte = auditar_coherencia_partido(_expediente_desde_fixture(partido))
            reportes.append(reporte)
            if salida_humana:
                _imprimir_reporte(reporte)

    conteo = {nivel: sum(1 for r in reportes if r.nivel_global == nivel) for nivel in NivelSeveridad}
    sondas = {nivel: sum(1 for r in reportes for h in r.hallazgos if h.nivel == nivel) for nivel in NivelSeveridad}
    codigo_salida = calcular_codigo_salida(reportes)

    if argumentos.json:
        # Modo máquina: un ÚNICO objeto JSON puro por stdout, sin decoración ni resumen humano.
        print(json.dumps(
            {
                "sonda": "ARCH-1.4.34",
                "regimen": "SOLO_LECTURA",
                "jornadas": jornadas,
                "total_partidos": len(reportes),
                "codigo_salida": codigo_salida,
                "resumen": {
                    "partidos": {nivel.value: conteo[nivel] for nivel in NivelSeveridad},
                    "sondas": {nivel.value: sondas[nivel] for nivel in NivelSeveridad},
                },
                "reportes": [r.model_dump(mode="json") for r in reportes],
            },
            ensure_ascii=False,
            indent=2,
        ))
        return codigo_salida

    print("\n" + "=" * 78)
    print("RESUMEN DE PRE-VUELO")
    for nivel in NivelSeveridad:
        print(f"  {GLIFO_NIVEL[nivel.value]} {nivel.value:<14} partidos={conteo[nivel]:<3} sondas={sondas[nivel]}")
    print(f"  Partidos auditados: {len(reportes)} · jornadas: {jornadas}")
    if codigo_salida == 0:
        print("✅ PRE-VUELO APTO: ninguna DISCREPANCIA (🔴) detectada.")
    else:
        print("🔴 PRE-VUELO BLOQUEADO: una o más DISCREPANCIAS requieren dictamen antes de continuar.")
    print("=" * 78)
    return codigo_salida


if __name__ == "__main__":
    sys.exit(main())
