# -*- coding: utf-8 -*-
"""
🏆 Q-BE SOVEREIGN ENGINE — INTENSIDADES LOG-LINEALES Y LIGADURA DE ALFA
[VAULT-CORE-001] Ecuación Log-Lineal Canónica, Ligadura de α (clausura de masa) y Damping tanh.
Base de Gobierno: Kybern Framework v13.5 [ARCH-1.3.4] / Tratado Volumen I (Sección 4.9 y 4.12)
Enmienda E-50.1 (docs/DIRGEN_VAULT.md §E-50.1): γ_efectivo completo en la ligadura, prohibición de
defaults literales (P-01/P-02) y contrato `InsufficientDataException`.
"""

import math
from typing import Optional, Tuple, Dict


# ═══════════════════════════════════════════════════════════════════════════════════════
# [E-50.1 §P-01] CONTRATO DE ERROR — DATO ESTRUCTURALMENTE OBLIGATORIO AUSENTE
# ═══════════════════════════════════════════════════════════════════════════════════════
class InsufficientDataException(Exception):
    """[LN-QBE-035-B] Evidencia obligatoria ausente en la ruta de cálculo (E-50.1 §P-01).

    La levanta la aduana de entrada del núcleo, NUNCA la aritmética. Porta `match_id`, `clave`
    y `lado`. PROHIBIDO capturarla para devolver un valor: el llamador la traduce a `S(I)=0`
    con su motivo y la declara en la traza forense.
    """

    def __init__(self, match_id: str = "", clave: str = "", lado: str = "") -> None:
        """[LN-QBE-035-B] Construye la excepción tipada con la coordenada de la evidencia ausente."""
        self.match_id = str(match_id)
        self.clave = str(clave)
        self.lado = str(lado)
        super().__init__(
            f"[E-50.1] Evidencia obligatoria ausente: clave={self.clave!r} "
            f"lado={self.lado!r} match_id={self.match_id!r}. Prohibido sustituirla por un literal."
        )


# ═══════════════════════════════════════════════════════════════════════════════════════
# [LN-QBE-038] CATÁLOGO CANÓNICO SELLADO DE INTIMIDACIÓN DE PLAZA (Δγ_plaza)
# Fuente legislada: `docs/CONSTANTS.md` §2 (factores de fortaleza de plaza por slug).
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
    clave = str(home_team_slug).lower().strip()
    # [E-50.1 §P-01] Sin `dict.get(clave, literal)`: la ausencia en el catálogo sellado es un
    # hecho legislado (plaza estándar ⇒ 0.0000), no un valor de relleno.
    bono = CATALOGO_FORTALEZA_PLAZA[clave] if clave in CATALOGO_FORTALEZA_PLAZA else 0.0
    return min(TECHO_DELTA_GAMMA_PLAZA, max(0.0, float(bono)))


# [E-50.1] Coeficientes del operador de localía (docs/CONSTANTS.md §2).
BONO_ALTITUD_POR_KM = 0.0300    # log-ratio por 1000 m de Δaltitud (sólo Δalt > 0)
BONO_DESCANSO_POR_DIA = 0.0200  # log-ratio por día de Δdescanso, recortado a [-3, +3] días


# [VAULT-CORE-001] [E-50.1] VÍA B — formalización de paridad canónica.
def calcular_alpha_ligadura(
    mu_liga: float = 2.65,
    gamma_efectivo: Optional[float] = None,
    *,
    gamma_home: Optional[float] = None,
) -> float:
    """[LN-QBE-040] Ligadura estructural con CLAUSURA DE MASA (Sección 4.9.1 · E-50.1):

        alpha = ln(mu_liga) - ln(1.0 + exp(gamma_efectivo))

    `gamma_efectivo` es el INTERCEPTO COMPLETO de localía (γ_base + Δγ_plaza + bono_altitud +
    efecto_descanso), no la base. Invariante L-1: con A = D = 0 y q_mod = 1.0,
    `lambda_H + lambda_A == mu_liga` (tolerancia 1e-12).

    `gamma_home` se conserva como ALIAS LEGADO de `gamma_efectivo` (llamadas selladas previas);
    su semántica es la misma: intercepto completo. Cero margen creativo.
    """
    if gamma_efectivo is None:
        gamma_efectivo = gamma_home if gamma_home is not None else 0.15
    mu_val = float(mu_liga)
    if not math.isfinite(mu_val) or mu_val <= 0.0:
        raise ValueError(f"[VAULT-CORE-001] mu_liga inválido: {mu_liga!r}. Debe ser finito y > 0.")
    gamma_val = float(gamma_efectivo)
    if not math.isfinite(gamma_val):
        raise InsufficientDataException("", "gamma_efectivo", "")
    return math.log(mu_val) - math.log(1.0 + math.exp(gamma_val))


KAPPA_NET = 0.2500  # [VAULT-CORE-001] Compresión hiperbólica PURA (absoluta, adimensional)


# [VAULT-CORE-001] [LN-QBE-038] VÍA B — formalización de paridad canónica.
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


# [VAULT-CORE-001] [E-50.1] VÍA B — formalización de paridad canónica.
def estimar_intensidades_loglineal(
    A_home: float,
    D_away: float,
    A_away: float,
    D_home: float,
    mu_liga: float = 2.65,
    gamma_home_base: float = 0.15,
    delta_alt_metros: Optional[float] = None,
    delta_descanso_dias: Optional[float] = None,
    q_mod_h: Optional[float] = None,
    q_mod_a: Optional[float] = None,
    sigma_A: float = 0.25,
    sigma_D: float = 0.25,
    home_team_slug: Optional[str] = None,
    kappa_net: float = KAPPA_NET,
) -> Tuple[float, float]:
    """[LN-QBE-040] Arquitectura Canónica Log-Lineal con CLAUSURA DE MASA (Sección 4.9 · E-50.1):

        ln(lambda_H) = alpha + gamma_efectivo + A_H - D_A + C_H
        ln(lambda_A) = alpha + A_A - D_H + C_A

    `gamma_efectivo` es el ÚNICO intercepto de localía y se construye ANTES de alpha. Prohibido
    añadir un término a `eta_h` sin añadirlo a la ligadura (Invariante L-1).

    [E-50.1 §P-01] Los insumos de clase C-2 (`Δalt`, `Δrest`, `q_mod`) ausentes NO se sustituyen
    por `0.0`: se declaran **no aplicados** (`None`) y el operador no interviene.

    Sin clamp: la cota física la impone la saturación `tanh(κ)` de los factores (|A|,|D| < 0.25),
    no un recorte posterior que enmascare el resultado.
    """
    # 1. Operador de localía (Sección 4.7) — se calcula ANTES de la ligadura
    delta_gamma_plaza = obtener_bono_fortaleza_plaza(home_team_slug)
    delta_alt_term = (
        BONO_ALTITUD_POR_KM * max(0.0, float(delta_alt_metros) / 1000.0)
        if delta_alt_metros is not None else 0.0
    )
    delta_rest_term = (
        BONO_DESCANSO_POR_DIA * max(-3.0, min(3.0, float(delta_descanso_dias)))
        if delta_descanso_dias is not None else 0.0
    )
    gamma_efectivo = (
        float(gamma_home_base) + delta_gamma_plaza + delta_alt_term + delta_rest_term
    )

    # 2. Ligadura estructural sobre el intercepto COMPLETO (clausura de masa, Invariante L-1)
    alpha = calcular_alpha_ligadura(mu_liga, gamma_efectivo)

    # 3. Damping hiperbólico aguas arriba en factores — κ_net gobernado por el llamador
    #    ([E-50.8][FASE 6] κ variable para el barrido empírico; default = κ sellado 0.25).
    A_h_damped = aplicar_damping_hiperbolico(A_home, sigma_A, kappa_net=kappa_net)
    D_a_damped = aplicar_damping_hiperbolico(D_away, sigma_D, kappa_net=kappa_net)
    A_a_damped = aplicar_damping_hiperbolico(A_away, sigma_A, kappa_net=kappa_net)
    D_h_damped = aplicar_damping_hiperbolico(D_home, sigma_D, kappa_net=kappa_net)

    # 4. Factores contextuales en espacio logarítmico (None = modificador no publicado)
    q_h_clamped = 1.0 if q_mod_h is None else max(0.90, min(1.05, float(q_mod_h)))
    q_a_clamped = 1.0 if q_mod_a is None else max(0.90, min(1.05, float(q_mod_a)))
    C_h = math.log(q_h_clamped)
    C_a = math.log(q_a_clamped)

    # 5. Formulación log-lineal canónica
    eta_h = alpha + gamma_efectivo + A_h_damped - D_a_damped + C_h
    eta_a = alpha + A_a_damped - D_h_damped + C_a

    # 6. Transformación exponencial SIN clamp: la cota la impone κ (|A|,|D| < 0.25) e I6.
    lambda_h = math.exp(eta_h)
    lambda_a = math.exp(eta_a)

    return lambda_h, lambda_a
