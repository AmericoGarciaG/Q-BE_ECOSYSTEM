# -*- coding: utf-8 -*-
"""
JUEZ INMUTABLE: [TRATADO VOL. I] Verificación del Pipeline Soberano y Trazabilidad
Doctrina: Kybern Framework v12.0 [DIRGEN-SEALED] [GOV-TEST-01 a 07]
Régimen: [DIRGEN-STRICT]
"""

import pytest

# En esta fase (previo a materialización en src/), esta importación DEBE FALLAR (RED STATE)
from src.core.sovereign_pipeline import (
    evaluar_suficiencia_informativa,
    generar_distribucion_soberana
)


def test_suficiencia_informativa_sad_path():
    """Valida que partidos sin datos mínimos (PJ < 3) colapsen a ignorancia S(I)=0."""
    datos_vacios = {
        "home_team_stats": {"pj": 1, "gf": 1, "gc": 2},
        "away_team_stats": {"pj": 2, "gf": 2, "gc": 3}
    }
    assert evaluar_suficiencia_informativa(datos_vacios) is False

    salida = generar_distribucion_soberana("MATCH_UNKNOWN", datos_vacios)
    assert salida.es_operable is False
    assert salida.p_local == 0.3333
    assert salida.p_empate == 0.3333
    assert salida.audit_trace.suficiencia_S_I == 0


def test_pipeline_soberano_caso_puebla_atlante():
    """
    Test Fáctico End-to-End: Puebla vs Atlante con datos reales de la Liga MX.
    Certifica que P(Puebla) se contenga a un realista 54%-60%, desterrando el 78.3%.
    """
    datos_puebla_atlante = {
        # [ARCH-1.4.41] Contrato de unidad canónico: "xg"/"xga" son ACUMULADOS TOTALES de temporada.
        # Tasa preservada: xg 11.68/8 = 1.46 · xga 10.32/8 = 1.29 · xg 8.56/8 = 1.07 · xga 12.16/8 = 1.52.
        "home_team_stats": {"pj": 8, "gf": 10, "gc": 10, "xg": 11.68, "xga": 10.32},
        "away_team_stats": {"pj": 8, "gf": 7, "gc": 12, "xg": 8.56, "xga": 12.16}
    }

    assert evaluar_suficiencia_informativa(datos_puebla_atlante) is True

    salida = generar_distribucion_soberana(
        match_id="LIGAMX-J9-01",
        raw_match_data=datos_puebla_atlante,
        mu_liga=2.65,
        gamma_home_base=0.15
    )

    # Invarianza del Símplex Δ²
    suma = salida.p_local + salida.p_empate + salida.p_visitante
    assert abs(suma - 1.0000) <= 0.0001

    # Validación contra sobre-amplificación:
    # Puebla debe estar en rango realista [0.52, 0.60] (NO el 0.783 de la patología)
    assert 0.52 <= salida.p_local <= 0.60, f"Puebla desbordado: {salida.p_local}"
    assert salida.p_empate >= 0.22, f"Empate subestimado: {salida.p_empate}"
    assert salida.lambda_home <= 2.00, f"Lambda Puebla inflada: {salida.lambda_home}"
    assert salida.lambda_away >= 0.75, f"Lambda Atlante colapsada: {salida.lambda_away}"

    # Verificación de Pago Anticipado (André)
    assert 0.25 <= salida.phi_lead2_home <= 0.45
    assert salida.phi_lead2_home > salida.phi_lead2_away

    # Verificación de Traza Forense
    assert salida.audit_trace.suficiencia_S_I == 1
    assert "lambda_home" in salida.audit_trace.intensidades
    assert salida.es_operable is True
