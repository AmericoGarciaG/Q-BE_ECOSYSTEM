# -*- coding: utf-8 -*-
"""
JUEZ INMUTABLE: [LN-QBE-072] Verificación del Espacio Combinatorio 3^K y Trinidad de Certeza
Doctrina: Kybern Framework v8.0 / v12.0 [GOV-TEST-01 a 07]
"""

import pytest
from src.core.portfolio import calcular_trinidad_resiliencia_3k


def test_trinidad_resiliencia_invarianzas_estocasticas():
    """Valida leyes de conservación y congruencia en las 3 anclas de certeza."""
    # Mock de 4 órdenes típicas de Q-BE
    ordenes_mock = [
        {"ganancia": 4.00, "inversion": 16.00, "p_win": 0.909, "p_draw": 0.074, "p_loss": 0.017, "es_directo": True},
        {"ganancia": 17.92, "inversion": 16.00, "p_win": 0.783, "p_draw": 0.156, "p_loss": 0.061, "es_directo": True},
        {"ganancia": 2.51, "inversion": 7.50, "p_win": 0.687, "p_draw": 0.240, "p_loss": 0.073, "es_directo": False},
        {"ganancia": 2.87, "inversion": 4.32, "p_win": 0.301, "p_draw": 0.340, "p_loss": 0.359, "es_directo": False},
    ]

    trinidad = calcular_trinidad_resiliencia_3k(ordenes_mock)

    assert "pleno_exito" in trinidad
    assert "tablas_o_ganancia" in trinidad
    assert "ruina_total" in trinidad

    pleno = trinidad["pleno_exito"]
    tablas = trinidad["tablas_o_ganancia"]
    ruina = trinidad["ruina_total"]

    # 1. Invarianza: La probabilidad de tablas o ganar DEBE ser estrictamente mayor que el pleno
    assert tablas["probabilidad_pct"] > pleno["probabilidad_pct"], (
        f"Inconsistencia: Tablas ({tablas['probabilidad_pct']}%) debe ser > Pleno ({pleno['probabilidad_pct']}%)"
    )

    # 2. Invarianza: La probabilidad de ruina total debe ser extremadamente baja (<= 0.1%)
    assert ruina["probabilidad_pct"] <= 0.05, f"Ruina total anormalmente alta: {ruina['probabilidad_pct']}%"

    # 3. Invarianza: El PnL de tablas o ganancia garantiza umbral >= 0.0
    assert tablas["umbral_pnl_mxn"] == 0.0

    # 4. Invarianza: Pleno éxito suma exactamente las ganancias máximas
    ganancia_esperada = sum(o["ganancia"] for o in ordenes_mock)
    assert abs(pleno["pnl_mxn"] - ganancia_esperada) <= 0.05
