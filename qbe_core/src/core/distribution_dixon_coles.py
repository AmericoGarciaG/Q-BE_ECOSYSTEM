# -*- coding: utf-8 -*-
"""
🏆 Q-BE SOVEREIGN ENGINE — DIXON-COLES Y COLAPSO AL SÍMPLEX
[VAULT-CORE-004] Generador Dixon-Coles y Colapso Geométrico al Símplex Delta^2.
Base de Gobierno: Kybern Framework v12.0 [ARCH-1.3.4] / Tratado Volumen I (Sección 5.3.1 y 5.7)
"""

import math
from typing import List, Optional, Tuple

# [LN-QBE-040-C] Ley de resolución dinámica de la correlación táctica y constantes selladas
# (docs/CONSTANTS.md §2). El eje de resolución tiene un único dueño normativo: `src/core/poisson.py`.
from src.core.poisson import (
    LAMBDA_SUMA_CORTE_TACTICO,
    RHO_BASE,
    RHO_TACTICA_DEFICIT,
    resolver_rho_dixon_coles,
)

# ═══════════════════════════════════════════════════════════════════════════════════════
# [E-50.5][Tarea 3] TRANSICIÓN SUAVE DEL ESCALÓN DE ρ — ventana ±0.10 goles
#
# El escalón de `[LN-QBE-040-C]` (ρ = −0.12 → −0.05 al cruzar Σλ = 2.65) introduce una
# discontinuidad de primer orden en la superficie P(β): L-BFGS-B no encuentra gradiente
# utilizable en la frontera. Se interpola con una sigmoide reescalada dentro de la ventana
# [2.55, 2.75]; FUERA de ella los valores sellados se conservan EXACTOS (clamp), de modo que
# los Jueces de frontera y la paridad con `poisson.py` permanecen intactos.
# ═══════════════════════════════════════════════════════════════════════════════════════
VENTANA_RHO_SUAVE = 0.1000   # ±0.10 goles alrededor de la frontera táctica
_SIGMOIDE_K = 8.0            # pendiente de la sigmoide normalizada


def _sigmoide_normalizada(t: float) -> float:
    """Sigmoide reescalada a [0, 1] con s(0) = 0 y s(1) = 1 EXACTOS (C∞ en el interior)."""
    k = _SIGMOIDE_K
    inferior = 1.0 / (1.0 + math.exp(k * 0.5))     # σ(−k/2)
    superior = 1.0 / (1.0 + math.exp(-k * 0.5))    # σ(+k/2)
    centro = 1.0 / (1.0 + math.exp(-k * (t - 0.5)))
    return (centro - inferior) / (superior - inferior)


def resolver_rho_suave(lambda_h: float, lambda_a: float) -> float:
    """[E-50.5] ρ continuo: −0.12 exacto en Σλ ≤ 2.55, −0.05 exacto en Σλ ≥ 2.75, sigmoide entre.

    La función es continua en todo ℝ⁺ y monótona creciente en la ventana; en los extremos
    reproduce bit a bit las constantes selladas, por lo que la paridad con `[LN-QBE-040-C]`
    se conserva fuera de la banda de transición.
    """
    suma = float(lambda_h) + float(lambda_a)
    inferior = LAMBDA_SUMA_CORTE_TACTICO - VENTANA_RHO_SUAVE
    superior = LAMBDA_SUMA_CORTE_TACTICO + VENTANA_RHO_SUAVE
    if suma <= inferior:
        return float(RHO_TACTICA_DEFICIT)
    if suma >= superior:
        return float(RHO_BASE)
    t = (suma - inferior) / (superior - inferior)
    return float(RHO_TACTICA_DEFICIT) + (float(RHO_BASE) - float(RHO_TACTICA_DEFICIT)) * _sigmoide_normalizada(t)


def calcular_matriz_dixon_coles(
    lambda_h: float,
    lambda_a: float,
    rho: Optional[float] = None,
    k_max: int = 6,
    rho_suave: bool = True
) -> List[List[float]]:
    """
    [Sección 5.3.1, 5.14 y 5.16] Generador paramétrico con corrección de dependencia
    en baja puntuación bajo Teorema de No-Negatividad Estricta (Invariante I13).

    [LN-QBE-040-C] Calibración táctica dinámica: si el invocante NO aporta un `rho`
    explícito distinto del default sellado (`RHO_BASE = -0.0500`), la correlación se
    resuelve por régimen de anotación. `rho = 0.0` explícito es el escape hatch de auditoría.
    [E-50.5] Con `rho_suave=True` (default legislado) la frontera Σλ = 2.65 se interpola en
    una ventana de ±0.10 goles; `rho_suave=False` reproduce el escalón sellado de `poisson.py`.
    """
    # 0. [LN-QBE-040-C] Resolución dinámica del régimen de correlación
    if rho is None or float(rho) == RHO_BASE:
        rho = (
            resolver_rho_suave(lambda_h, lambda_a)
            if rho_suave
            else resolver_rho_dixon_coles(lambda_h, lambda_a)
        )

    # 1. Cotas analíticas de admisibilidad de rho (Sección 5.16.1)
    cota_inf = -min(1.0 / max(0.01, lambda_h), 1.0 / max(0.01, lambda_a))
    cota_sup = min(1.0, 1.0 / max(0.01, lambda_h * lambda_a))
    rho_admisible = max(cota_inf, min(cota_sup, rho))

    # 2. Distribución de Poisson base
    # [LN-QBE-040] VÍA B — formalización de paridad canónica ([LN-QBE-139]/[LN-QBE-140]).
    def pois_prob(lmb: float, k: int) -> float:
        return (math.exp(-lmb) * (lmb ** k)) / math.factorial(k)

    # 3. Factor de corrección tau(x, y)
    # [LN-QBE-040] VÍA B — formalización de paridad canónica ([LN-QBE-139]/[LN-QBE-140]).
    def tau_factor(x: int, y: int) -> float:
        if x == 0 and y == 0:
            return 1.0 - (lambda_h * lambda_a * rho_admisible)
        if x == 0 and y == 1:
            return 1.0 + (lambda_h * rho_admisible)
        if x == 1 and y == 0:
            return 1.0 + (lambda_a * rho_admisible)
        if x == 1 and y == 1:
            return 1.0 - rho_admisible
        return 1.0

    matriz = []
    suma_total = 0.0

    for x in range(k_max + 1):
        fila = []
        p_x = pois_prob(lambda_h, x)
        for y in range(k_max + 1):
            p_y = pois_prob(lambda_a, y)
            p_conjunta = max(0.0, p_x * p_y * tau_factor(x, y))
            fila.append(p_conjunta)
            suma_total += p_conjunta
        matriz.append(fila)

    # 4. Renormalización estricta sobre el retículo truncado (Sección 5.14)
    if suma_total > 0.0:
        for x in range(k_max + 1):
            for y in range(k_max + 1):
                matriz[x][y] /= suma_total

    return matriz


# [LN-QBE-040] VÍA B — formalización de paridad canónica ([LN-QBE-139]/[LN-QBE-140]).
def colapsar_matriz_a_simplex(matriz_2d: List[List[float]]) -> Tuple[float, float, float]:
    """
    [Sección 5.7 a 5.10] Colapso geométrico exacto de regiones disjuntas sobre el Símplex Delta^2:
    p_1 = Sum_{x > y} M_xy
    p_X = Sum_{x = y} M_xy
    p_2 = Sum_{x < y} M_xy
    Garantiza formalmente Invariante I1 (Exhaustividad) e Invariante I14 (Partición).
    """
    p_local = 0.0
    p_empate = 0.0
    p_visitante = 0.0
    k_dim = len(matriz_2d)

    for x in range(k_dim):
        for y in range(k_dim):
            val = matriz_2d[x][y]
            if x > y:
                p_local += val
            elif x == y:
                p_empate += val
            else:
                p_visitante += val

    # Normalización final de seguridad para redondear a 4 decimales
    p_1 = round(p_local, 4)
    p_X = round(p_empate, 4)
    p_2 = round(1.0 - p_1 - p_X, 4)

    return p_1, p_X, p_2
