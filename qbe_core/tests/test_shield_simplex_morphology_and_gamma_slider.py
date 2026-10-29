# -*- coding: utf-8 -*-
"""
🛡️ THE SHIELD: JUEZ INMUTABLE DE CAPA 0 Y SU INTEGRACIÓN AL TRIAJE DE CARTERA
Validación de:
- [LN-QBE-059] Partición Canónica de Δ² con Γ=0.67 (Alcanzabilidad de Paridad Ciega).
- [LN-QBE-060-B] Subordinación Real del Triaje a la Morfología de Capa 0.
- [ARCH-1.4.30] Mutación Dinámica de Cartera: D1/D2 mutan a H1/H2 al mover Γ de 0.67 a 0.70.
"""

import pytest
from src.core.simplex_morphology import clasificar_morfologia_simplex
from src.core.contracts.portfolio_math import (
    triaje_determinista_9_estrategias,
    PortfolioParameters
)
from src.models.web_schemas import GeneratePortfolioRequest


# ---------------------------------------------------------------------------
# 1. AUDITORÍA DE PARTICIÓN CON Γ=0.67 (ALCANZABILIDAD DE PARIDAD CIEGA)
# ---------------------------------------------------------------------------
def test_ln_qbe_059_exact_simplex_partition_gamma_67():
    """Audita la partición exacta con el nuevo umbral canónico Γ=0.67 (> 2/3)."""
    # 1. Hegemonía Local
    assert clasificar_morfologia_simplex((0.70, 0.20, 0.10), gamma=0.67).familia == "HEGEMONIA_LOCAL"

    # 2. Hegemonía Visitante
    assert clasificar_morfologia_simplex((0.10, 0.20, 0.70), gamma=0.67).familia == "HEGEMONIA_VISITANTE"

    # 3. Asimetría Local (Local domina)
    assert clasificar_morfologia_simplex((0.55, 0.25, 0.20), gamma=0.67).familia == "ASIMETRIA_LOCAL"

    # 4. Asimetría Local (Empate domina por max-band)
    res_4 = clasificar_morfologia_simplex((0.30, 0.45, 0.25), gamma=0.67)
    assert res_4.familia == "ASIMETRIA_EMPATE_LOCAL"
    assert res_4.desenlace_seguro == "1"

    # 5. Asimetría Visitante (Visita domina)
    assert clasificar_morfologia_simplex((0.20, 0.25, 0.55), gamma=0.67).familia == "ASIMETRIA_VISITANTE"

    # 6. Asimetría Visitante (Empate domina por max-band)
    res_6 = clasificar_morfologia_simplex((0.25, 0.45, 0.30), gamma=0.67)
    assert res_6.familia == "ASIMETRIA_EMPATE_VISITANTE"
    assert res_6.desenlace_seguro == "2"

    # 7. Bipolaridad Territorial
    assert clasificar_morfologia_simplex((0.40, 0.20, 0.40), gamma=0.67).familia == "BIPOLARIDAD_TERRITORIAL"

    # 8. Paridad Ciega: con Γ=0.67 el centro (0.334, 0.333, 0.333) cae en Paridad
    # (max par = 0.334 + 0.333 = 0.667 < 0.6700)
    res_centro = clasificar_morfologia_simplex((0.334, 0.333, 0.333), gamma=0.67)
    assert res_centro.familia == "PARIDAD_CIEGA"
    assert res_centro.desenlace_ataque is None


# ---------------------------------------------------------------------------
# 2. PRUEBA DE INTEGRACIÓN: MUTACIÓN REAL D1/D2 -> H1/H2 AL MOVER Γ (67% -> 70%)
# ---------------------------------------------------------------------------
def test_ln_qbe_060_b_triaje_integrates_simplex_morphology_and_gamma():
    """
    Audita que triaje_determinista_9_estrategias consuma activamente a Capa 0:
    Pachuca (67.2%) y Tijuana (67.3%) deben ser DIRECTAS con Γ=0.67 y MUTAR a HÍBRIDAS con Γ=0.70.
    """
    # Caso Pachuca vs Necaxa: P'=(0.672, 0.186, 0.141), Cuotas L=1.71, E=3.95, V=4.80
    payload_pachuca = {
        "p_local": 0.672, "p_empate": 0.186, "p_visitante": 0.141,
        "delta_epist": 0.02, "es_operable": True
    }
    cuotas_pachuca = {"L": 1.71, "E": 3.95, "V": 4.80, "pa": True}

    # Con Γ = 0.67: p1 = 0.672 >= 0.67 -> Debe ser DIRECTA LOCAL (QBE-D1)
    triaje_pachuca_67 = triaje_determinista_9_estrategias(payload_pachuca, cuotas_pachuca, gamma=0.67)
    assert triaje_pachuca_67["codigo"] == "QBE-D1", (
        f"Con Γ=0.67 Pachuca debía ser QBE-D1, dio: {triaje_pachuca_67['codigo']}"
    )

    # Con Γ = 0.70: p1 = 0.672 < 0.70, pero p1 + pX = 0.858 >= 0.70 -> DEBE MUTAR A HÍBRIDA (QBE-H1)
    triaje_pachuca_70 = triaje_determinista_9_estrategias(payload_pachuca, cuotas_pachuca, gamma=0.70)
    assert triaje_pachuca_70["codigo"] == "QBE-H1", (
        f"🚨 ERROR DE INTEGRACIÓN: Con Γ=0.70 Pachuca debía mutar a QBE-H1, pero dio: {triaje_pachuca_70['codigo']}"
    )

    # Caso Juárez vs Tijuana: P'=(0.141, 0.185, 0.673), Cuotas L=3.00, E=3.55, V=2.35
    payload_tijuana = {
        "p_local": 0.141, "p_empate": 0.185, "p_visitante": 0.673,
        "delta_epist": 0.02, "es_operable": True
    }
    cuotas_tijuana = {"L": 3.00, "E": 3.55, "V": 2.35, "pa": True}

    # Con Γ = 0.67: p2 = 0.673 >= 0.67 -> Debe ser DIRECTA VISITA (QBE-D2)
    triaje_tijuana_67 = triaje_determinista_9_estrategias(payload_tijuana, cuotas_tijuana, gamma=0.67)
    assert triaje_tijuana_67["codigo"] == "QBE-D2", (
        f"Con Γ=0.67 Tijuana debía ser QBE-D2, dio: {triaje_tijuana_67['codigo']}"
    )

    # Con Γ = 0.70: p2 = 0.673 < 0.70, pero p2 + pX = 0.858 >= 0.70 -> DEBE MUTAR A HÍBRIDA (QBE-H2)
    triaje_tijuana_70 = triaje_determinista_9_estrategias(payload_tijuana, cuotas_tijuana, gamma=0.70)
    assert triaje_tijuana_70["codigo"] == "QBE-H2", (
        f"🚨 ERROR DE INTEGRACIÓN: Con Γ=0.70 Tijuana debía mutar a QBE-H2, pero dio: {triaje_tijuana_70['codigo']}"
    )


# ---------------------------------------------------------------------------
# 3. AUDITORÍA DE CONTRATOS DTO DE CARTERA ([ARCH-1.4.30])
# ---------------------------------------------------------------------------
def test_arch_1_4_30_portfolio_dto_accepts_gamma_threshold():
    """Audita que los DTOs acepten gamma_threshold y default 0.67."""
    params = PortfolioParameters(total_bankroll=200.0, certainty_slider=0.80, gamma_threshold=0.67)
    assert params.gamma_threshold == 0.67

    req = GeneratePortfolioRequest(bankroll=200.0, gamma_slider=0.70)
    assert req.gamma_slider == 0.70
