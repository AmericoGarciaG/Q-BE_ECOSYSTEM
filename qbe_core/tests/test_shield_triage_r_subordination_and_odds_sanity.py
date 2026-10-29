# -*- coding: utf-8 -*-
"""
JUEZ INMUTABLE: [LN-QBE-060-B], [LN-QBE-007-H] & [ARCH-1.4.1-B]
Subordinación de Familia R, Aduana de Overround y Plaza Jalisco.
Base de Gobierno: docs/LOGIC.md / docs/CONSTANTS.md / docs/ARCH.md
Autoridad: Américo García Guerrero (Director Humano)
Régimen: [DIRGEN-STRICT] — Inmutable, Cero Mocks.
"""

import pytest
from src.core.contracts.portfolio_math import triaje_determinista_9_estrategias
from src.core.intensity_canonical_loglink import obtener_bono_fortaleza_plaza


def test_invarianza_subordinacion_familia_r_en_asimetria_local():
    """
    [INVARIANZA 1 - SUBORDINACIÓN MORFOLÓGICA DE FAMILIA R]:
    En un partido con favoritismo local (Pachuca 45.3% vs Necaxa 31.5%, Empate 23.2%),
    queda PROHIBIDO que el sistema emita QBE-R2 a favor del visitante, ya que dejaría
    un riesgo desprotegido del 45.3% violando la Invariante VIII-37.
    """
    payload_pachuca = {
        "p_local": 0.4530,
        "p_empate": 0.2320,
        "p_visitante": 0.3150,
        "es_operable": True,
        "delta_epist": 0.03
    }
    cuotas = {
        "L": 1.71,
        "E": 4.00,
        "V": 4.95,
        "pa": True
    }

    resultado = triaje_determinista_9_estrategias(payload_pachuca, cuotas, gamma=0.67)

    assert resultado["codigo"] != "QBE-R2", (
        f"🚨 VIOLACIÓN INVARIANTE VIII-37: Partido con p_local=45.3% emitió {resultado['codigo']}. "
        f"Prohibido emitir QBE-R2 dejando más del 33% de riesgo al descubierto."
    )
    assert resultado["codigo"] in ("QBE-H1", "QBE-C1", "QBE-C2", "QBE-00")


def test_invarianza_aduana_overround_negativo_fuerza_cuarentena():
    """
    [INVARIANZA 2 - ADUANA DE SANIDAD COMERCIAL DE OVERROUND]:
    Si un casino entrega cuotas corruptas con suma de inversas S < 0.85
    (ej. Pachuca 4.95 y Necaxa 4.95, margen -34.6%),
    el triaje DEBE abortar inmediatamente a QBE-00 (Cuarentena).
    """
    payload = {
        "p_local": 0.45,
        "p_empate": 0.23,
        "p_visitante": 0.32,
        "es_operable": True,
        "delta_epist": 0.03
    }
    # Cuotas corruptas con margen negativo: S = 1/4.95 + 1/4.00 + 1/4.95 = 0.654 (< 0.85)
    cuotas_corruptas = {
        "L": 4.95,
        "E": 4.00,
        "V": 4.95,
        "pa": True
    }
    
    resultado = triaje_determinista_9_estrategias(payload, cuotas_corruptas, gamma=0.67)
    
    assert resultado["codigo"] == "QBE-00", (
        f"🚨 FUGA DE ADUANA: Cuotas corruptas con margen negativo no fueron vetadas. "
        f"Emitió: {resultado['codigo']} con alpha={resultado.get('alpha')}."
    )


def test_invarianza_estadio_jalisco_plaza_bono():
    """
    [INVARIANZA 3 - BONO DE PLAZA ESTADIO JALISCO]:
    Verifica que Atlas FC en el Estadio Jalisco reciba su bono de plaza de +0.0400.
    """
    bono_atlas_fc = obtener_bono_fortaleza_plaza("atlas-fc")
    bono_atlas = obtener_bono_fortaleza_plaza("atlas")
    
    assert bono_atlas_fc == 0.0400, f"🚨 PLAZA CIEGA: atlas-fc recibió {bono_atlas_fc} (esperado 0.0400)"
    assert bono_atlas == 0.0400, f"🚨 PLAZA CIEGA: atlas recibió {bono_atlas} (esperado 0.0400)"
