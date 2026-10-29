# -*- coding: utf-8 -*-
"""
🛡️ THE SHIELD — TWIN-TEST: CONTRATOS MATEMÁTICOS DE PORTAFOLIO Y 9 ESTRATEGIAS
[LN-QBE-060-B, LN-QBE-060-R-AWAKEN, LN-QBE-070-B, LN-QBE-071, LN-QBE-073-B] & [ARCH-1.4.9]
Régimen: [DIRGEN-STRICT]
Axioma: Cero tolerancia a números mágicos. Paridad fiduciaria al centavo.
"""

import pytest
import os
import ast
from abc import ABC, abstractmethod


class AbstractTestPortfolioMath(ABC):
    """Juez Abstracto que impone las leyes matemáticas del Tratado Volumen II."""

    def test_alpha_edge_positive_negative(self):
        """Verifica la condición de valor esperado positivo (+EV)."""
        from src.core.contracts.portfolio_math import calcular_alpha_edge
        # Caso con valor (+EV): p = 0.55, O = 2.10 -> 0.55 * 2.10 - 1 = +0.1550 (+15.5%)
        assert calcular_alpha_edge(0.55, 2.10) == 0.1550
        # Caso sin valor (-EV): p = 0.40, O = 2.10 -> 0.40 * 2.10 - 1 = -0.1600 (-16.0%)
        assert calcular_alpha_edge(0.40, 2.10) == -0.1600
        # Frontera nula: cuota rota
        assert calcular_alpha_edge(0.50, 1.00) == -1.0

    def test_dutching_v0_exact_zero_loss(self):
        """Verifica la Invarianza #2: Pérdida neta de $0.00 MXN en caso de empate."""
        from src.core.contracts.portfolio_math import calcular_dutching_v0
        b_total = 100.0
        o_fav = 1.90
        o_emp = 3.60
        b_prio, b_seg, ganancia, roi = calcular_dutching_v0(b_total, o_fav, o_emp)

        # Retorno del seguro en empate debe devolver exactamente b_total
        retorno_seguro = round(b_seg * o_emp, 2)
        assert abs(retorno_seguro - b_total) <= 0.08, f"Violación V=0: Retorno {retorno_seguro} != {b_total}"
        assert b_prio + b_seg == b_total
        assert ganancia > 0.0
        assert roi > 0.0

    def test_umbral_theta_estrella(self):
        """Verifica el cálculo analítico de breakeven theta* para cobertura viable."""
        from src.core.contracts.portfolio_math import calcular_umbral_theta_estrella
        # Favorito @ 1.90 -> theta* = 1.90 / (1.90 - 1) = 2.1111
        assert abs(calcular_umbral_theta_estrella(1.90) - 2.1111) <= 1e-3
        # Favorito @ 1.50 -> theta* = 1.50 / 0.50 = 3.0000
        assert abs(calcular_umbral_theta_estrella(1.50) - 3.0000) <= 1e-3

    def test_escalamiento_piso_ventanilla(self):
        """Verifica que si el seguro cae por debajo de $2.00, se reescale preservando V=0."""
        from src.core.contracts.portfolio_math import escalar_a_piso_ventanilla
        # Inversión de $5.00 con empate @ 4.00 -> Seguro teórico sería $1.25 (< $2.00)
        b_prio, b_seg, b_total = escalar_a_piso_ventanilla(5.00, 4.00, piso_min=2.00)
        assert b_seg == 2.00
        assert b_total == 8.00  # 2.00 * 4.00 = 8.00
        assert b_prio == 6.00
        # Si ocurre el empate: 2.00 * 4.00 = 8.00 -> Retorno cubre 100% de b_total (V=0)
        assert round(b_seg * 4.00, 2) == b_total

    def test_triaje_9_estrategias_cascada(self):
        """Verifica la convergencia determinista hacia las estrategias canónicas."""
        from src.core.contracts.portfolio_math import triaje_determinista_9_estrategias

        # 1. Caso Cuarentena (Régimen IV: alta discrepancia)
        p_cuarentena = {"p_local": 0.60, "p_empate": 0.25, "p_visitante": 0.15, "delta_epist": 0.14, "es_operable": True}
        assert triaje_determinista_9_estrategias(p_cuarentena, {"L": 2.0, "E": 3.4, "V": 4.0})["codigo"] == "QBE-00"

        # 2. Caso Directa Local QBE-D1 (Régimen I con +EV)
        p_d1 = {"p_local": 0.72, "p_empate": 0.18, "p_visitante": 0.10, "delta_epist": 0.02, "es_operable": True}
        assert triaje_determinista_9_estrategias(p_d1, {"L": 1.60, "E": 3.8, "V": 6.0})["codigo"] == "QBE-D1"

        # 3. Caso Híbrida Local QBE-H1 (Régimen II con seguro viable)
        p_h1 = {"p_local": 0.52, "p_empate": 0.26, "p_visitante": 0.22, "delta_epist": 0.03, "es_operable": True}
        res_h1 = triaje_determinista_9_estrategias(p_h1, {"L": 2.10, "E": 3.50, "V": 3.60, "pa": True})
        assert res_h1["codigo"] == "QBE-H1"
        assert res_h1["pa"] is True

        # 4. Caso Underdog Familia R (QBE-R1) — Admisible exclusivamente en PARIDAD_CIEGA ([LN-QBE-060-B])
        #    tras la derogación de Bipolaridad por la Invariante VIII-37 (Decreto VAR-2026-TRIAJE-R-BIPOLAR).
        p_r1 = {"p_local": 0.334, "p_empate": 0.333, "p_visitante": 0.333, "delta_epist": 0.03, "es_operable": True}
        # Dog local a 4.50 con p=0.334 -> alpha = 0.334*4.50 - 1 = +0.503 (+50.3% EV)
        assert triaje_determinista_9_estrategias(p_r1, {"L": 4.50, "E": 3.40, "V": 1.80})["codigo"] == "QBE-R1"

        # 4-bis. Blindaje Invariante VIII-37: el mismo perro en BIPOLARIDAD_TERRITORIAL (s_12 = 0.76 >= Gamma)
        #        queda terminantemente enmudecido (QBE-00) por dejar >33% de riesgo descubierto.
        p_bipolar = {"p_local": 0.28, "p_empate": 0.24, "p_visitante": 0.48, "delta_epist": 0.03, "es_operable": True}
        assert triaje_determinista_9_estrategias(p_bipolar, {"L": 4.50, "E": 3.40, "V": 1.80})["codigo"] == "QBE-00"

    def test_ranking_friccion(self):
        """Verifica que el ordenamiento priorice activos de alto +EV y bajo desacuerdo."""
        from src.core.contracts.portfolio_math import calcular_ranking_friccion
        partidos = [
            {"id": "P1", "codigo": "QBE-H1", "alpha": 0.08, "delta_epist": 0.02},  # Score alto
            {"id": "P2", "codigo": "QBE-00", "alpha": 0.15, "delta_epist": 0.13},  # Cuarentena -> Score 0
            {"id": "P3", "codigo": "QBE-D1", "alpha": 0.12, "delta_epist": 0.01},  # Score altísimo
        ]
        ranking = calcular_ranking_friccion(partidos)
        assert ranking[0]["id"] == "P3"
        assert ranking[1]["id"] == "P1"
        assert ranking[2]["id"] == "P2"
        assert ranking[2]["score_friccion"] == 0.0

    def test_kelly_atenuado_y_hardcaps(self):
        """Verifica la Invarianza #3 y #4: Topes de 8.0% individual y 25.0% global."""
        from src.core.contracts.portfolio_math import calcular_kelly_atenuado, aplicar_hard_caps_constitucionales
        bankroll = 1000.0

        # Kelly para p=0.60, O=2.00 -> f_puro = 0.20 / 1.0 = 0.20
        # Con gamma=0.25 y psi=1.0 (delta_epist=0.0) -> f_adj = 0.20 * 0.25 * 1.0 = 0.05 (5.0%)
        f_adj = calcular_kelly_atenuado(0.60, 2.00, delta_epist=0.00)
        assert f_adj == 0.05

        # Verificación de cota de incertidumbre en frontera tau_disp=0.12 (psi=0.0 -> f_adj=0.0)
        assert calcular_kelly_atenuado(0.60, 2.00, delta_epist=0.12) == 0.00

        # Probar Hard-Caps con excesos de stake
        inversiones_excesivas = [120.0, 100.0, 90.0, 80.0]  # Suma = 390 (excede 250 de bankroll)
        acotadas = aplicar_hard_caps_constitucionales(inversiones_excesivas, bankroll)

        # 1. Ningún partido supera 80.0 (8% de 1000)
        for inv in acotadas:
            assert inv <= 80.01
        # 2. La suma no supera 250.0 (25% de 1000)
        assert sum(acotadas) <= 250.08

    def test_ganancia_cobertura_v0_derivada(self):
        """Verifica [LN-QBE-073-B]: la prima de cobertura es DERIVADA, no un factor mágico.

        g_cob = g·(1 − p_draw) − B·p_draw  (dutching V=0 a cuotas soberanas justas)
        """
        from src.core.contracts.portfolio_math import calcular_ganancia_cobertura_v0

        # PARTIDO_01: g=15.00, B=16.00, p_draw=0.18 -> 15*0.82 - 16*0.18 = 12.30 - 2.88 = 9.42
        assert calcular_ganancia_cobertura_v0(15.0, 16.0, 0.18) == 9.42
        # PARTIDO_02: g=8.00, B=16.00, p_draw=0.22 -> 8*0.78 - 16*0.22 = 6.24 - 3.52 = 2.72
        assert calcular_ganancia_cobertura_v0(8.0, 16.0, 0.22) == 2.72

        # Frontera degenerada: sin masa de probabilidad en el empate la cobertura es inocua
        assert calcular_ganancia_cobertura_v0(15.0, 16.0, 0.0) == 15.0
        # Certeza absoluta de empate: la estructura colapsa a la pérdida del capital (V=0)
        assert calcular_ganancia_cobertura_v0(15.0, 16.0, 1.0) == -16.0
        # Cuota rota / sin capital no genera ganancia alguna
        assert calcular_ganancia_cobertura_v0(15.0, 0.0, 0.18) == 0.0

        # Monotonía: a mayor masa de probabilidad en el empate, mayor prima (menor ganancia)
        previas = [calcular_ganancia_cobertura_v0(15.0, 16.0, p) for p in (0.05, 0.10, 0.18, 0.25)]
        assert previas == sorted(previas, reverse=True)

        # Erradicación del factor mágico 0.70: ninguna constante única replica ambos casos reales
        assert calcular_ganancia_cobertura_v0(15.0, 16.0, 0.18) != round(15.0 * 0.70, 2)
        assert calcular_ganancia_cobertura_v0(8.0, 16.0, 0.22) != round(8.0 * 0.70, 2)


class TestPortfolioMath(AbstractTestPortfolioMath):
    """Implementación concreta del Juez en The Shield."""
    pass

