# -*- coding: utf-8 -*-
"""
🏆 Q-BE SOVEREIGN ENGINE — OPERADOR DE ANDRÉ PARA PAGO ANTICIPADO
[VAULT-CORE-003] Fórmula Cerrada de Désiré André para activación de ventaja +2.
Base de Gobierno: Kybern Framework v12.0 [ARCH-1.3.4] / Tratado Volumen I (Sección 5.20.2)
"""

from typing import List


def operador_seccional_andre(x: int, y: int) -> float:
    """
    [Sección 5.20.2] Fórmula Cerrada de Désiré André para activación de ventaja +2:
    pi(x, y) = x*(x-1) / ((y+1)*(y+2)) para marcadores con x >= 2.
    Evaluación continua exacta en tiempo constante O(1).
    """
    if x - y >= 2:
        return 1.0000
    if x < 2:
        return 0.0000

    # Marcadores de erosión: x >= 2 pero x - y < 2 (ej. 2-1, 3-2, 4-3)
    num = float(x * (x - 1))
    den = float((y + 1) * (y + 2))
    prob = num / den
    return max(0.0, min(1.0, prob))


def calcular_probabilidad_pago_anticipado(matriz_2d: List[List[float]], es_local: bool = True) -> float:
    """
    [Sección 5.20.3] Integra el Operador de André sobre la matriz 2D consolidada:
    Phi_Lead2 = Sum_x Sum_y [ Pi_Lead2(x, y) * M_xy ]
    """
    phi_acumulado = 0.0
    k_dim = len(matriz_2d)

    for x in range(k_dim):
        for y in range(k_dim):
            p_marcador = matriz_2d[x][y]
            if p_marcador <= 0.0:
                continue

            # Si evaluamos al local: x son sus goles, y los del rival.
            # Si evaluamos al visitante: y son sus goles, x los del rival.
            goles_fav = x if es_local else y
            goles_und = y if es_local else x

            pi_hit = operador_seccional_andre(goles_fav, goles_und)
            phi_acumulado += pi_hit * p_marcador

    return round(max(0.0, min(1.0, phi_acumulado)), 4)
