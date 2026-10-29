# -*- coding: utf-8 -*-
"""
JUEZ INMUTABLE: [LN-QBE-060-C] Filtro de Veto Inteligente Anti-Ruptura QBE-00
Base de Gobierno: docs/LOGIC.md [LN-QBE-060-C] / docs/CONSTANTS.md
Autoridad: Américo García Guerrero (Director Humano)
Régimen: [DIRGEN-STRICT] — Inmutable, Cero Mocks.
"""

import pytest
from src.core.contracts.portfolio_math import triaje_determinista_9_estrategias


def test_invarianza_veto_falsa_paridad_alta_entropia():
    """
    [INVARIANZA 1 - VETO DE FALSA PARIDAD]:
    Partidos con dispersion estrecha (Delta P <= 12% y P_max <= 38%)
    DEBEN colapsar obligatoriamente a QBE-00 (Veto Fiduciario).
    """
    # Atlas vs Pumas J9: P' = (36.8%, 27.8%, 35.4%) => Delta P = 36.8 - 27.8 = 9.0% <= 12%
    payload_falsa_paridad = {
        "p_local": 0.3680,
        "p_empate": 0.2780,
        "p_visitante": 0.3540,
        "es_operable": True,
        "delta_epist": 0.03
    }
    cuotas = {"L": 2.15, "E": 3.30, "V": 3.22, "pa": True}
    
    # Peritaje VAR-ANTI-RUPTURA-ORDEN-01: la morfologia BIPOLARIDAD_TERRITORIAL ya abstenia
    # este partido en HEAD por la Invariante VIII-37; el nodo [LN-QBE-060-C] debe ademas
    # CALIFICAR el arquetipo de ruptura en la traza, sin alterar el veredicto sellado.
    res = triaje_determinista_9_estrategias(payload_falsa_paridad, cuotas, gamma=0.70)
    assert res["codigo"] == "QBE-00", f"🚨 ERROR: Debio vetar por Falsa Paridad, emitio {res['codigo']}"
    assert "Falsa Paridad" in res.get("motivo", "") or "Anti-Ruptura" in res.get("nombre", "")
    # [ALT-3] Trazabilidad sellada del arquetipo interceptado (dictamen 2026-10-15).
    assert res.get("arquetipo_veto") == "FALSA_PARIDAD", (
        f"🚨 FUGA DE TRAZA: Veto de Falsa Paridad sin arquetipo_veto (dio {res.get('arquetipo_veto')})"
    )


def test_invarianza_veto_bipolar_fuego_altas_anotaciones():
    """
    [INVARIANZA 2 - VETO DE BIPOLAR DE FUEGO EN 1X2]:
    Partidos con lambda total >= 3.0 xG y empate asfixiado (p_X <= 22%)
    DEBEN colapsar a QBE-00 en 1X2 para desvio a mercado de goles C2.
    """
    # Pachuca vs Necaxa J11: 3-3 real. P' = (47.3%, 21.6%, 31.2%), lambda_total = 1.89 + 1.55 = 3.44 xG
    payload_bipolar_fuego = {
        "p_local": 0.4730,
        "p_empate": 0.2160,
        "p_visitante": 0.3110,
        "lambda_home": 1.89,
        "lambda_away": 1.55,
        "es_operable": True,
        "delta_epist": 0.03
    }
    cuotas = {"L": 1.71, "E": 3.85, "V": 4.60, "pa": True}
    
    res = triaje_determinista_9_estrategias(payload_bipolar_fuego, cuotas, gamma=0.70)
    assert res["codigo"] == "QBE-00", f"🚨 ERROR: Debio vetar Bipolar de Fuego en 1X2, emitio {res['codigo']}"
    # [ALT-3] Trazabilidad sellada del arquetipo interceptado (dictamen 2026-10-15).
    assert res.get("arquetipo_veto") == "BIPOLAR_FUEGO", (
        f"🚨 FUGA DE TRAZA: Veto de Bipolar de Fuego sin arquetipo_veto (dio {res.get('arquetipo_veto')})"
    )


def test_invarianza_preservacion_partido_con_conviccion_sana():
    """
    [INVARIANZA 3 - NO-VETO EN PARTIDOS SANOS]:
    Partidos con conviccion solida (Delta P > 15% y P_max >= 45%) NO deben ser vetados.
    """
    payload_sano = {
        "p_local": 0.5200,
        "p_empate": 0.2600,
        "p_visitante": 0.2200,
        "lambda_home": 1.50,
        "lambda_away": 1.10,
        "es_operable": True,
        "delta_epist": 0.03
    }
    cuotas = {"L": 2.10, "E": 3.50, "V": 3.60, "pa": True}
    
    res = triaje_determinista_9_estrategias(payload_sano, cuotas, gamma=0.70)
    assert res["codigo"] != "QBE-00", f"🚨 ERROR: Veto indebido sobre partido sano, emitio {res['codigo']}"
    assert res["codigo"] == "QBE-H1"
    # [ALT-3] Trazabilidad inversa: un partido admitido NO porta arquetipo de veto alguno.
    assert res.get("arquetipo_veto") is None, (
        f"🚨 FUGA DE TRAZA: Partido con conviccion valida calificado como {res.get('arquetipo_veto')}"
    )
