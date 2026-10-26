# -*- coding: utf-8 -*-
"""
🏆 Q-BE SOVEREIGN ENGINE — MOTOR DE ORTOGONALIZACIÓN RESIDUAL (GSL-3D)
[LN-QBE-039] & [ARCH-1.4.33] Contenedor de Factores Latentes Tridimensionales.
Base de Gobierno: Kybern Framework v13.5 [DIRGEN-STRICT] — Función Pura en O(m).

Resolución vinculante `VAR-2026-GSL3D-1D-DEGENERACY` (Dictamen Arquitectónico):
la proyección euclidiana escalar de Gram-Schmidt es degenerada en R^1
(Proj_u(X) == X  =>  v_perp == 0), por lo que se sustituye por el **Residuo
Ortogonal Log-Diferencial de Sede** en el espacio logarítmico natural del fútbol:

    v_sede_perp = ln(tasa_sede / tasa_gen) - gamma_base        (ataque)
    v_sede_perp = -[ ln(tasa_sede / tasa_gen) + gamma_base ]   (defensa)

y la síntesis acotada bajo presupuesto cerrado de norma:
    A* = tanh(A_gen + v_sede_perp),   |A*| <= 1.0,  |D*| <= 1.0
"""

import math
from typing import Dict, Any, Tuple, Optional
from pydantic import BaseModel, ConfigDict


EPSILON_ORTOGONAL = 1e-5
TECHO_NORMA_FACTOR = 1.0000


class FactoresGSL3D(BaseModel):
    """Contrato inmutable de factores latentes emitidos por GSL-3D."""
    model_config = ConfigDict(frozen=True, extra="ignore")
    
    A_star: float
    D_star: float
    C_star: float
    residuo_ataque_sede: float
    residuo_defensa_sede: float


def calcular_residuo_sede_log(
    tasa_sede: float,
    tasa_gen: float,
    gamma_base: float = 0.15,
    es_defensa: bool = False
) -> float:
    """
    [LN-QBE-039] Extrae el residuo ortogonal de sede en espacio logarítmico:
    v_perp = ln(tasa_sede / tasa_gen) - gamma_base (para ataque)
    
    Si el desempeño en casa solo iguala a la calidad general más la localía macro,
    el residuo es ~0 (América: cero doble cobro).
    Si el desempeño en casa supera anómalamente a la calidad general (Tigres),
    el residuo captura la fuerza genuina de la plaza.
    """
    t_sede = max(0.2, float(tasa_sede))
    t_gen = max(0.2, float(tasa_gen))
    ratio_log = math.log(t_sede / t_gen)
    
    if not es_defensa:
        # Ataque: lo que excede a la localía macro de goles
        residuo = ratio_log - gamma_base
    else:
        # Defensa: menos goles concedidos en casa es mejor defensa (signo negativo en GC)
        residuo = -(ratio_log + gamma_base)
        
    return residuo


def sintetizar_factor_latente_acotado(
    factor_gen: float,
    residuo_sede: float,
    # ── RECONCILIACIÓN DE TRANSCRIPCIÓN (declarada, no silenciosa) ──────────────────────
    # La ecuación normativa del dictamen §2.C es A* = tanh(A_gen + v_sede_perp): el residuo
    # ortogonal entra con peso unitario (reconstrucción ortogonal íntegra). El bloque de
    # código remitido declaraba `0.50`, constante que CONTRADICE las verificaciones
    # numéricas del propio dictamen (América λ_H <= 1.90 y Tigres λ_H >= 1.35), al DoD
    # exigido (6 PASSED) y a §2.C. Se materializa la ecuación normativa (1.00).
    peso_residuo: float = 1.00,
    techo_norma: float = TECHO_NORMA_FACTOR
) -> float:
    """
    [LN-QBE-039] Sintetiza el factor latente combinando la calidad general
    con el residuo ortogonal de sede bajo compresión hiperbólica tanh.
    """
    combinacion = factor_gen + (peso_residuo * residuo_sede)
    factor_acotado = techo_norma * math.tanh(combinacion / techo_norma)
    return round(factor_acotado, 4)


def resolver_factores_latentes_gsl3d(
    A_gen: float,
    D_gen: float,
    gf_gen: float,
    gc_gen: float,
    gf_sede: Optional[float],
    gc_sede: Optional[float],
    gamma_base: float = 0.15,
    es_local: bool = True,
    C_contexto: float = 0.0
) -> FactoresGSL3D:
    """
    Orquestador GSL-3D: extrae los residuos ortogonales y emite (A*, D*, C*)
    acotados estrictamente en norma <= 1.0.
    """
    if gf_sede is None or gc_sede is None:
        A_star = round(TECHO_NORMA_FACTOR * math.tanh(A_gen / TECHO_NORMA_FACTOR), 4)
        D_star = round(TECHO_NORMA_FACTOR * math.tanh(D_gen / TECHO_NORMA_FACTOR), 4)
        return FactoresGSL3D(
            A_star=A_star,
            D_star=D_star,
            C_star=round(C_contexto, 4),
            residuo_ataque_sede=0.0,
            residuo_defensa_sede=0.0
        )
    
    # 1. Extracción de Residuos Ortogonales
    res_A = calcular_residuo_sede_log(
        tasa_sede=gf_sede, tasa_gen=gf_gen,
        gamma_base=gamma_base if es_local else 0.0,
        es_defensa=False
    )
    res_D = calcular_residuo_sede_log(
        tasa_sede=gc_sede, tasa_gen=gc_gen,
        gamma_base=gamma_base if es_local else 0.0,
        es_defensa=True
    )
    
    # 2. Síntesis Acotada con tanh
    A_star = sintetizar_factor_latente_acotado(factor_gen=A_gen, residuo_sede=res_A)
    D_star = sintetizar_factor_latente_acotado(factor_gen=D_gen, residuo_sede=res_D)
    
    return FactoresGSL3D(
        A_star=A_star,
        D_star=D_star,
        C_star=round(C_contexto, 4),
        residuo_ataque_sede=round(res_A, 4),
        residuo_defensa_sede=round(res_D, 4)
    )
