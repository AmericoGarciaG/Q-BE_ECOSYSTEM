# -*- coding: utf-8 -*-
"""
JUEZ INMUTABLE: [TRATADO VOL. I] Verificación del Motor Soberano de Distribuciones
Doctrina: Kybern Framework v12.0 [DIRGEN-SEALED] [GOV-TEST-01 a 07]
Régimen: [DIRGEN-STRICT]
"""

import pytest
import math

# En esta fase (previo a materialización en src/), estas importaciones DEBEN FALLAR (RED STATE)
from src.core.intensity_canonical_loglink import (
    calcular_alpha_ligadura,
    aplicar_damping_hiperbolico,
    estimar_intensidades_loglineal
)
from src.core.andre_early_payout import (
    operador_seccional_andre,
    calcular_probabilidad_pago_anticipado
)
from src.core.distribution_dixon_coles import (
    calcular_matriz_dixon_coles,
    colapsar_matriz_a_simplex
)


def test_ligadura_estructural_alpha_y_conservacion():
    """Valida que alpha ligue exactamente la masa de goles incondicional."""
    alpha = calcular_alpha_ligadura(mu_liga=2.65, gamma_home=0.15)
    assert abs(alpha - 0.2035) <= 0.001

    # Verificación en enfrentamiento neutral promedio
    lambda_base_h = math.exp(alpha + 0.15)
    lambda_base_a = math.exp(alpha)
    total_goles_esperados = lambda_base_h + lambda_base_a
    assert abs(total_goles_esperados - 2.65) <= 0.01, "Violación de conservación de masa de goles"


def test_damping_hiperbolico_erradica_patologia_puebla_atlante():
    """
    Verificación Dual:
    1. Caso Fáctico Puebla vs Atlante (Factores reales de Liga MX).
    2. Caso Límite de Estrés (+2.6 sigma) para certificar compresión tanh.
    """
    # ── 1. CASO FÁCTICO PUEBLA VS ATLANTE (Liga MX Real) ──
    # Puebla (#8) vs Atlante (#15): Factores moderados reales
    lh_real, la_real = estimar_intensidades_loglineal(
        A_home=0.12, D_away=-0.15,
        A_away=-0.20, D_home=0.05,
        mu_liga=2.65, gamma_home_base=0.15
    )
    ratio_real = lh_real / la_real
    # El modelo anterior producía un ratio de 4.96 (78.3% de victoria).
    # El nuevo motor calibrado debe contener el ratio a paridad deportiva (<= 2.20)
    assert ratio_real <= 2.20, f"Violación Fáctica: Ratio desbordado ({ratio_real:.2f})"
    assert 1.60 <= lh_real <= 1.95, f"Lambda local fuera de rango físico: {lh_real}"
    assert 0.80 <= la_real <= 1.05, f"Lambda visita fuera de rango físico: {la_real}"

    # ── 2. CASO LÍMITE DE ESTRÉS ASINTÓTICO (+2.6 sigma) ──
    # Simula disparidad extrema (Man City vs colista)
    lh_stress, la_stress = estimar_intensidades_loglineal(
        A_home=0.65, D_away=-0.40,
        A_away=-0.35, D_home=0.30,
        mu_liga=2.65, gamma_home_base=0.15
    )
    ratio_stress = lh_stress / la_stress
    # Sin damping el ratio era 6.35. Con compresión tanh se contiene a <= 4.90
    assert ratio_stress <= 4.90, f"Violación de cota de estrés: {ratio_stress:.2f}"
    assert lh_stress <= 3.30, f"Lambda de estrés desbordada: {lh_stress}"
    assert la_stress >= 0.65, f"Lambda de estrés colapsada: {la_stress}"



def test_formula_cerrada_andre_exactitud_combinatoria():
    """Valida que el Operador de André calcule exactamente los valores de frontera y colapso O(1)."""
    # 1. Frontera exacta x - y >= 2 -> 1.0000
    assert operador_seccional_andre(2, 0) == 1.0000
    assert operador_seccional_andre(3, 1) == 1.0000
    assert operador_seccional_andre(4, 2) == 1.0000

    # 2. Cota inferior x < 2 -> 0.0000
    assert operador_seccional_andre(1, 0) == 0.0000
    assert operador_seccional_andre(0, 0) == 0.0000
    assert operador_seccional_andre(1, 2) == 0.0000

    # 3. Marcador de erosión: 3 - 2
    # André: 3*(2) / (3*4) = 6/12 = 0.5000
    assert operador_seccional_andre(3, 2) == 0.5000

    # 4. Marcador de erosión: 2 - 1
    # André: 2*(1) / (2*3) = 2/6 = 0.3333
    assert abs(operador_seccional_andre(2, 1) - 0.3333) <= 0.001


def test_simplex_invarianza_y_dixon_coles():
    """Valida la suma exacta sobre el Símplex Δ² y no-negatividad."""
    matriz = calcular_matriz_dixon_coles(lambda_h=1.65, lambda_a=0.95, rho=-0.05, k_max=6)
    
    # Todas las celdas deben ser no-negativas (Invariante I13)
    for fila in matriz:
        for val in fila:
            assert val >= 0.0, "Violación Invariante I13: celda negativa en matriz"

    p1, pX, p2 = colapsar_matriz_a_simplex(matriz)
    
    # Invarianza I1 (Simplex)
    suma = p1 + pX + p2
    assert abs(suma - 1.0000) <= 0.0001, f"Violación Invarianza I1: Suma = {suma}"
    assert 0.0 <= p1 <= 1.0
    assert 0.0 <= pX <= 1.0
    assert 0.0 <= p2 <= 1.0
