# -*- coding: utf-8 -*-
"""
JUEZ INMUTABLE: [LN-QBE-073] Verificación del Modulador Adaptativo por Slider
Doctrina: Kybern Framework v12.0 [DIRGEN-SEALED] [GOV-TEST-01 a 07]
Régimen: [DIRGEN-STRICT]
"""

import pytest

# En esta fase (previo a materialización en src/), esta importación DEBE FALLAR (RED STATE)
from src.core.risk_dial_modulator import modular_cartera_por_slider_certeza
from src.core.portfolio import calcular_trinidad_resiliencia_3k


def test_modulador_transmuta_directo_a_cobertura_para_cumplir_slider():
    """
    Valida que ante una cartera con órdenes directas donde la certeza sea 68%,
    al exigir target_certeza = 80%, el modulador transmute D1 -> H1 elevando la certeza.
    """
    ordenes_iniciales = [
        {"id": "PARTIDO_01", "ganancia": 15.0, "inversion": 16.0, "p_win": 0.75, "p_draw": 0.18, "p_loss": 0.07, "es_directo": True},
        {"id": "PARTIDO_02", "ganancia": 8.0, "inversion": 16.0, "p_win": 0.65, "p_draw": 0.22, "p_loss": 0.13, "es_directo": True}
    ]

    # Certeza inicial sin seguro en empate (ambos directos pierden si empatan)
    trinidad_base = calcular_trinidad_resiliencia_3k(ordenes_iniciales)
    certeza_base = trinidad_base["tablas_o_ganancia"]["probabilidad_pct"]
    assert certeza_base < 75.0, f"La certeza base debió ser menor a 75%: {certeza_base}%"

    # Exigir slider al 80%
    ordenes_moduladas = modular_cartera_por_slider_certeza(ordenes_iniciales, target_certeza_pct=80.0)

    # Validar que al menos una orden directa fue transmutada a cobertura (es_directo = False)
    assert any(not o["es_directo"] for o in ordenes_moduladas), "Fallo de modulación: Ninguna orden fue protegida con seguro"

    # Evaluar certeza resultante
    trinidad_final = calcular_trinidad_resiliencia_3k(ordenes_moduladas)
    certeza_final = trinidad_final["tablas_o_ganancia"]["probabilidad_pct"]
    assert certeza_final >= 78.0, f"Fallo fiduciario: Certeza final {certeza_final}% no alcanzó el umbral del slider"


def test_modulador_poda_fiduciaria_ante_exigencia_extrema():
    """
    Valida que ante una exigencia extrema del 95% de certeza, el modulador
    pode activos riesgosos preservando únicamente las posiciones indestructibles.
    """
    ordenes_riesgosas = [
        {"id": "SEGURO", "ganancia": 4.0, "inversion": 16.0, "p_win": 0.92, "p_draw": 0.06, "p_loss": 0.02, "es_directo": False},
        {"id": "VOLATIL", "ganancia": 18.0, "inversion": 16.0, "p_win": 0.55, "p_draw": 0.25, "p_loss": 0.20, "es_directo": True}
    ]

    ordenes_filtradas = modular_cartera_por_slider_certeza(ordenes_riesgosas, target_certeza_pct=90.0)
    
    # Debe haber podado el partido volátil
    assert len(ordenes_filtradas) == 1
    assert ordenes_filtradas[0]["id"] == "SEGURO"
