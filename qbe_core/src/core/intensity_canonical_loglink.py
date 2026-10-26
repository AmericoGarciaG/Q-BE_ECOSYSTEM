# -*- coding: utf-8 -*-
"""
🏆 Q-BE SOVEREIGN ENGINE — INTENSIDADES LOG-LINEALES Y LIGADURA DE ALFA
[VAULT-CORE-001] Ecuación Log-Lineal Canónica, Ligadura de alpha y Damping tanh.
Base de Gobierno: Kybern Framework v12.0 [ARCH-1.3.4] / Tratado Volumen I (Sección 4.9 y 4.12)
"""

import math
from typing import Tuple, Optional, Dict


# ═══════════════════════════════════════════════════════════════════════════════════════
# [LN-QBE-038] CATÁLOGO CANÓNICO SELLADO DE INTIMIDACIÓN DE PLAZA (Δγ_plaza)
# Fuente legislada: `docs/CONSTANTS.md` §2 (factores de fortaleza de plaza por slug).
# Los slugs son los canónicos de FotMob (`obtener_slug_club`); las variantes de alias
# (`guadalajara`, `monterrey`) se declaran para blindar la resolución ante la nomenclatura
# publicada por la fuente. Cero invención: sólo plazas selladas por el Libro de Constantes.
# ═══════════════════════════════════════════════════════════════════════════════════════
CATALOGO_FORTALEZA_PLAZA: Dict[str, float] = {
    "tigres-uanl": 0.0700,
    "deportivo-toluca": 0.0600,
    "pumas-unam": 0.0500,
    "atlas-fc": 0.0400,
    "atlas": 0.0400,
    "club-america": 0.0400,
    "guadalajara": 0.0400,
    "chivas-guadalajara": 0.0400,
    "monterrey": 0.0400,
    "rayados-de-monterrey": 0.0400,
}
TECHO_DELTA_GAMMA_PLAZA = 0.1000


def obtener_bono_fortaleza_plaza(home_team_slug: Optional[str]) -> float:
    """[LN-QBE-038] Δγ_plaza — bono aditivo de intimidación de la plaza del club local.

    Función pura y determinista sobre el catálogo sellado: club no catalogado (o slug
    ausente) ⇒ 0.0000 (jamás se inventa fortaleza). El resultado queda acotado al techo
    de la constante sellada Δγ_plaza_max = TECHO_DELTA_GAMMA_PLAZA.
    """
    if not home_team_slug:
        return 0.0
    bono = CATALOGO_FORTALEZA_PLAZA.get(str(home_team_slug).lower().strip(), 0.0)
    return min(TECHO_DELTA_GAMMA_PLAZA, max(0.0, float(bono)))


def calcular_alpha_ligadura(mu_liga: float = 2.65, gamma_home: float = 0.15) -> float:
    """
    [Sección 4.9.1] Ecuación de Ligadura Estructural de Q-BE:
    alpha = ln(mu_liga) - ln(1.0 + exp(gamma_home))
    Garantiza analíticamente la conservación de masa de goles de la competición.
    """
    gamma_val = float(gamma_home) if gamma_home is not None else 0.15
    mu_val = float(mu_liga) if mu_liga is not None else 2.65
    return math.log(mu_val) - math.log(1.0 + math.exp(gamma_val))


KAPPA_NET = 0.2500  # [VAULT-CORE-001] Compresión hiperbólica PURA (absoluta, adimensional)


def aplicar_damping_hiperbolico(factor_crudo: float, sigma_liga: float = 1.0,
                                kappa_mult: Optional[float] = None,
                                kappa_net: float = KAPPA_NET) -> float:
    """[Sección 4.12 / VAULT-CORE-001] Compresión Hiperbólica PURA de factores log-diferenciales:
    A = κ_net · tanh(A_crudo / κ_net), con κ_net = 0.2500 ABSOLUTO (Libro de Constantes §2).

    Preserva E[A] = 0 por imparidad estricta y acota asintóticamente |A| < κ_net.
    Los parámetros históricos `sigma_liga` / `kappa_mult` (κ = 2.5·σ_liga) quedan DEROGADOS
    por [VAULT-CORE-001]: se conservan en la firma —sin intervenir en el cómputo— para no
    romper llamadas selladas (`src/core/sovereign/bayesian_form.py` invoca por palabra clave
    `sigma_liga=`). Cero margen creativo: κ_net es constante legislada, no calibrada aquí.
    """
    kappa = float(kappa_net)
    if kappa <= 0.0:
        return 0.0
    return kappa * math.tanh(float(factor_crudo) / kappa)


def estimar_intensidades_loglineal(
    A_home: float,
    D_away: float,
    A_away: float,
    D_home: float,
    mu_liga: float = 2.65,
    gamma_home_base: float = 0.15,
    delta_alt_metros: float = 0.0,
    delta_descanso_dias: float = 0.0,
    q_mod_h: float = 1.0,
    q_mod_a: float = 1.0,
    sigma_A: float = 0.25,
    sigma_D: float = 0.25,
    home_team_slug: Optional[str] = None
) -> Tuple[float, float]:
    """
    [Sección 4.9] Arquitectura Canónica Log-Lineal:
    ln(lambda_H) = alpha + gamma_home + A_H - D_A + C_H
    ln(lambda_A) = alpha + A_A - D_H + C_A

    [LN-QBE-038] Si se suministra `home_team_slug`, la plaza agrega el bono sellado de
    intimidación Δγ_plaza al intercepto de localía y la ligadura estructural α se recalcula
    EN CALIENTE sobre la localía efectiva (γ̄_base + Δγ_plaza), garantizando la estricta
    conservación de masa global de goles. Slug ausente ⇒ comportamiento canónico intacto.
    """
    # 1. Ligadura estructural — [LN-QBE-038]: recalibrada sobre la localía efectiva.
    bono_plaza = obtener_bono_fortaleza_plaza(home_team_slug)
    alpha = calcular_alpha_ligadura(mu_liga, float(gamma_home_base) + bono_plaza)

    # 2. Damping hiperbólico aguas arriba en factores
    A_h_damped = aplicar_damping_hiperbolico(A_home, sigma_A)
    D_a_damped = aplicar_damping_hiperbolico(D_away, sigma_D)
    A_a_damped = aplicar_damping_hiperbolico(A_away, sigma_A)
    D_h_damped = aplicar_damping_hiperbolico(D_home, sigma_D)

    # 3. Operador vectorial de localía (Sección 4.7) + bono de plaza [LN-QBE-038]
    delta_alt_term = 0.03 * max(0.0, delta_alt_metros / 1000.0)
    delta_rest_term = 0.02 * max(-3.0, min(3.0, delta_descanso_dias))
    gamma_contextual = gamma_home_base + bono_plaza + delta_alt_term + delta_rest_term

    # 4. Factores contextuales en espacio logarítmico
    q_h_clamped = max(0.90, min(1.05, float(q_mod_h)))
    q_a_clamped = max(0.90, min(1.05, float(q_mod_a)))
    C_h = math.log(q_h_clamped)
    C_a = math.log(q_a_clamped)

    # 5. Formulación log-lineal canónica
    eta_h = alpha + gamma_contextual + A_h_damped - D_a_damped + C_h
    eta_a = alpha + A_a_damped - D_h_damped + C_a

    # 6. Transformación exponencial e Invariante I6 (Positividad estricta acotada)
    lambda_h = max(0.15, min(4.50, math.exp(eta_h)))
    lambda_a = max(0.15, min(4.50, math.exp(eta_a)))

    return round(lambda_h, 4), round(lambda_a, 4)
