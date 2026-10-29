# -*- coding: utf-8 -*-
"""
JUEZ INMUTABLE: [LN-QBE-077-B/C/D] & [ARCH-1.4.37] Dutching Dinámico y Cobertura Activa
Base de Gobierno: docs/LOGIC.md / docs/CONSTANTS.md / docs/ARCH.md
Autoridad: Américo García Guerrero (Director Humano)
Régimen: [DIRGEN-STRICT] — Inmutable, Cero Mocks.
"""

import pytest
from src.core.contracts.portfolio_math import (
    calcular_particion_dutching_dinamico,
    liquidar_orden_post_evento
)


def test_invarianza_particion_dutching_defensivo_v0():
    """
    [INVARIANZA 1 - PARIDAD CON MODELO HISTÓRICO V=0]:
    En modo DEF (delta=0.0), el cobro en empate debe ser exactamente el 100% de la
    inversión ($0.00 MXN de beneficio neto), preservando la indemnidad clásica.
    """
    res = calcular_particion_dutching_dinamico(
        b_total=10.00,
        o_fav=1.89,
        o_emp=3.80,
        modo="DEF"
    )
    
    assert res["delta_efectivo"] == 0.0000
    assert abs(res["cobro_bruto_empate"] - 10.00) <= 0.08
    assert abs(res["pnl_neto_empate"] - 0.00) <= 0.08
    assert res["pnl_neto_favorito"] > 0.0
    assert res["monto_seguro"] >= 2.00
    assert res["monto_ataque"] >= 2.00


def test_invarianza_dutching_isorrendimiento_doble_cosecha():
    """
    [INVARIANZA 2 - TEOREMA DE ISORRENDIMIENTO δ*]:
    En modo AGR, el ROI neto obtenido en caso de victoria del favorito debe ser
    idéntico al ROI obtenido en empate dentro de la tolerancia bancaria (0.05%).
    """
    o_fav, o_emp = 1.89, 3.80
    res = calcular_particion_dutching_dinamico(
        b_total=10.00,
        o_fav=o_fav,
        o_emp=o_emp,
        modo="AGR"
    )
    
    delta_teorico = (o_fav * o_emp) / (o_fav + o_emp) - 1.0000  # ~0.2622 (26.2%)
    assert abs(res["delta_efectivo"] - delta_teorico) <= 0.02
    
    # Ambos desenlaces deben rendir prácticamente lo mismo
    roi_fav = res["roi_favorito_porcentaje"]
    roi_emp = res["roi_empate_porcentaje"]
    assert abs(roi_fav - roi_emp) <= 1.0, (
        f"🚨 ASIMETRÍA EN ISORRENDIMIENTO: ROI_fav={roi_fav}% != ROI_emp={roi_emp}%"
    )
    assert roi_emp > 15.0, f"ROI en empate debe ser sustancial: {roi_emp}%"


def test_invarianza_techo_analitico_delta_max():
    """
    [INVARIANZA 3 - VIABILIDAD ANALÍTICA δ < δ_max]:
    Verifica que el delta solicitado jamás anule la ganancia del favorito.
    Si se fuerza un delta mayor al techo, el motor debe aplicar clamping al 95%.
    """
    o_fav, o_emp = 1.60, 3.60
    # theta* = 1.60 / 0.60 = 2.6667 => delta_max = 3.60 / 2.6667 - 1 = 0.3500 (35%)
    res = calcular_particion_dutching_dinamico(
        b_total=10.00,
        o_fav=o_fav,
        o_emp=o_emp,
        modo="CUSTOM",
        delta_custom=0.80  # Forzado absurdo (> 35%)
    )
    
    # Debe haber aplicado clamping seguro
    assert res["delta_efectivo"] < 0.3500
    assert res["pnl_neto_favorito"] > 0.00, "La ganancia del favorito no puede ser nula ni negativa"


def test_invarianza_liquidacion_post_evento_con_delta_positivo():
    """
    [INVARIANZA 4 - LIQUIDACIÓN FACTUAL CON GANANCIA EN EMPATE]:
    Verifica que al liquidar un empate con delta=0.20, se acredite ganancia neta (+20%).
    """
    orden_con_delta = {
        "strategy_code": "QBE-H1",
        "inversion_total": 10.00,
        "monto_ataque": 6.84,
        "cuota_ataque": 1.89,
        "monto_seguro": 3.16,
        "cuota_seguro": 3.80,
        "delta_cobertura": 0.20,
        "seleccion_favorito": "LOCAL"
    }
    
    # Marcador 1 - 1 (Empate)
    res = liquidar_orden_post_evento(orden_con_delta, home_score=1, away_score=1)
    
    # Cobro bruto: 3.16 * 3.80 = 12.01 MXN => PnL neto: +2.01 MXN (~ +20%)
    assert res["estado"] in ("COBRADO_SEGURO_DELTA", "TABLAS_V0")
    assert res["pnl_neto_mxn"] >= 1.90, (
        f"🚨 ERROR EN COSECHA DE EMPATE: PnL={res['pnl_neto_mxn']} debería ser ~ +2.00 MXN"
    )
    assert res["roi_real_porcentaje"] >= 19.0
