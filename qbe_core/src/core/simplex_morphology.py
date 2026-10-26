# -*- coding: utf-8 -*-
"""
Q-BE CORE — MORFOLOGÍA ESTOCÁSTICA PURA DEL SÍMPLEX Δ² (CAPA 0)
Base de Gobierno: [LN-QBE-059] / [ARCH-1.4.30] / Tratado Vol. II Sección 4.0
Régimen: [DIRGEN-STRICT] — Función Pura en O(1), Cero I/O, Cero DB.
"""

from typing import Tuple, Optional
from pydantic import BaseModel, ConfigDict


class MorphologyClassification(BaseModel):
    """Contrato inmutable de clasificación morfológica en Capa 0."""
    model_config = ConfigDict(frozen=True, extra="ignore")
    
    familia: str
    desenlace_ataque: Optional[str] = None  # "1", "X", "2" o None si es Paridad
    desenlace_seguro: Optional[str] = None  # "1", "X", "2" o None
    riesgo_residual: float                  # Masa del desenlace desprotegido (p_riesgo)
    gamma_utilizado: float


def clasificar_morfologia_simplex(
    p_prime: Tuple[float, float, float],
    gamma: float = 0.67
) -> MorphologyClassification:
    """
    [LN-QBE-059] Partición canónica y exhaustiva de Δ² en 8 familias morfológicas
    a partir de concentraciones de masa univariadas y bivariadas.
    p_prime = (p1, pX, p2) donde sum(p_prime) == 1.0
    """
    p1, pX, p2 = p_prime
    g = float(gamma)

    # -----------------------------------------------------------------------
    # 1. ADUANA DE DOMINANCIA UNIVARIADA (Hegemonías Puras)
    # -----------------------------------------------------------------------
    if p1 >= g:
        return MorphologyClassification(
            familia="HEGEMONIA_LOCAL",
            desenlace_ataque="1",
            desenlace_seguro=None,
            riesgo_residual=round(pX + p2, 4),
            gamma_utilizado=g
        )
    
    if p2 >= g:
        return MorphologyClassification(
            familia="HEGEMONIA_VISITANTE",
            desenlace_ataque="2",
            desenlace_seguro=None,
            riesgo_residual=round(p1 + pX, 4),
            gamma_utilizado=g
        )

    # -----------------------------------------------------------------------
    # 2. ADUANA DE VARIEDAD DE COBERTURA BIVARIADA (Asimetrías y Bipolaridad)
    # -----------------------------------------------------------------------
    s_1X = p1 + pX
    s_2X = p2 + pX
    s_12 = p1 + p2

    # A. Banda Local + Empate (Riesgo residual es p2 <= 1 - gamma)
    if s_1X >= g and s_1X > s_2X and s_1X >= s_12:
        if p1 >= pX:
            return MorphologyClassification(
                familia="ASIMETRIA_LOCAL",
                desenlace_ataque="1",
                desenlace_seguro="X",
                riesgo_residual=round(p2, 4),
                gamma_utilizado=g
            )
        else:
            return MorphologyClassification(
                familia="ASIMETRIA_EMPATE_LOCAL",
                desenlace_ataque="X",
                desenlace_seguro="1",
                riesgo_residual=round(p2, 4),
                gamma_utilizado=g
            )

    # B. Banda Visitante + Empate (Riesgo residual es p1 <= 1 - gamma)
    if s_2X >= g and s_2X >= s_1X and s_2X >= s_12:
        if p2 >= pX:
            return MorphologyClassification(
                familia="ASIMETRIA_VISITANTE",
                desenlace_ataque="2",
                desenlace_seguro="X",
                riesgo_residual=round(p1, 4),
                gamma_utilizado=g
            )
        else:
            return MorphologyClassification(
                familia="ASIMETRIA_EMPATE_VISITANTE",
                desenlace_ataque="X",
                desenlace_seguro="2",
                riesgo_residual=round(p1, 4),
                gamma_utilizado=g
            )

    # C. Banda Bipolar Territorial (Riesgo residual es pX <= 1 - gamma)
    if s_12 >= g and s_12 >= s_1X and s_12 >= s_2X:
        return MorphologyClassification(
            familia="BIPOLARIDAD_TERRITORIAL",
            desenlace_ataque="1" if p1 >= p2 else "2",
            desenlace_seguro="2" if p1 >= p2 else "1",
            riesgo_residual=round(pX, 4),
            gamma_utilizado=g
        )

    # -----------------------------------------------------------------------
    # 3. ADUANA DE ENTROPÍA (Ningún par bivariado alcanza gamma)
    # -----------------------------------------------------------------------
    return MorphologyClassification(
        familia="PARIDAD_CIEGA",
        desenlace_ataque=None,
        desenlace_seguro=None,
        riesgo_residual=1.0,
        gamma_utilizado=g
    )
