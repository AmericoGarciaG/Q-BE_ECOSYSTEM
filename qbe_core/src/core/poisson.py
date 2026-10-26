from __future__ import annotations

# Q-BE Casino Deportes — Poisson Engine (src/core/poisson.py)
"""
Modulación de Desempeño, Goles Esperados y Matriz Poisson Bivariada (6x6).
[LN-QBE-040] [BIZ-LOGIC] [ALGO-PROTECTED]
Incorpora calibración cruzada de xG/xGA Opta (FotMob) para proyección estocástica pura.
"""

import math
import numpy as np
from scipy.stats import poisson
from src.models.analytics import (
    H2HDecayResult,
    SyntheticMetricsResult,
    PoissonModulationResult
)
from src.core.constants import (
    BASELINE_LIGA,
    SATURACION_MADUREZ_J,
    OMEGA_MIN,
    OMEGA_MAX,
    BLEND_XG,
    BLEND_GF,
    CLAMP_GOLES_MIN,
    CLAMP_GOLES_MAX,
    EDGE_MIN_SATELITE,
)


# ═══════════════════════════════════════════════════════════════════════════════════════
# CONSTANTES CANÓNICAS DE LA PONDERACIÓN H2H↔LIGA
# [LN-QBE-020] / [LN-QBE-020-B] (Ley Zero-H2H) / [LN-QBE-040]
# Promulgadas en docs/CONSTANTS.md §1 por Dictamen Arquitectónico V-01 (Opción B), 2026-10-08.
# ═══════════════════════════════════════════════════════════════════════════════════════
KAPPA_H2H = 0.00385098            # días⁻¹ — τ_H2H = 180.0 d ⇒ ln(2)/180 (CONSTANTS.md §1)
W_H2H_AMP = 0.50                  # Amplitud máxima del peso H2H en la mezcla Poisson
W_H2H_PISO = 0.15                 # Piso de influencia H2H cuando existe antecedente real
SENTINELA_ZERO_H2H_DIAS = 9000.0  # Centinela contractual de ausencia, emitido por temporal.py


# ═══════════════════════════════════════════════════════════════════════════════════════
# CONSTANTES CANÓNICAS DE LA CORRELACIÓN DIXON-COLES TÁCTICA
# [LN-QBE-040-C] Promulgadas en docs/CONSTANTS.md §2 (Parámetros Canónicos de Correlación
# Dixon-Coles Dinámica). Nodo dueño: `[LN-QBE-040-C]`.
# Juez: `tests/shield/test_shield_rho_tactico_calibration.py`.
# ═══════════════════════════════════════════════════════════════════════════════════════
RHO_BASE = -0.0500                  # Correlación base para partidos abiertos (Σλ > 2.6500 xG)
RHO_TACTICA_DEFICIT = -0.1200       # Correlación táctica para partidos cerrados (Σλ ≤ 2.6500 xG)
LAMBDA_SUMA_CORTE_TACTICO = 2.6500  # Frontera de conmutación (μ_liga canónico de Liga MX)


# ═══════════════════════════════════════════════════════════════════════════════════════
# [LN-QBE-040-C] CALIBRACIÓN TÁCTICA DE ρ EN LA MATRIZ BIVARIADA
# Régimen: `[DIRGEN-STRICT]` — ley de resolución, constantes y factor τ son INMUTABLES.
# ═══════════════════════════════════════════════════════════════════════════════════════
def resolver_rho_dixon_coles(lambda_h: float, lambda_a: float) -> float:
    """[LN-QBE-040-C §P.1] Ley de resolución del régimen de correlación bivariada.

    Conmuta la correlación de Dixon-Coles según el régimen de anotación proyectado:

        rho = -0.1200  si  lambda_h + lambda_a <= 2.6500 xG   (partido cerrado / táctico)
        rho = -0.0500  si  lambda_h + lambda_a >  2.6500 xG   (partido abierto / base sellada)

    Función pura y determinista: sin estado interno, sin aleatoriedad y sin I/O. La frontera
    Σ_corte = 2.6500 xG es el μ_liga canónico de Liga MX y pertenece a la rama táctica (≤).
    """
    suma_lambda = float(lambda_h) + float(lambda_a)
    if suma_lambda <= LAMBDA_SUMA_CORTE_TACTICO:
        return RHO_TACTICA_DEFICIT
    return RHO_BASE


def _dixon_coles_tau(x: int, y: int, lambda_h: float, lambda_a: float, rho: float) -> float:
    """[LN-QBE-040-C §P.2] Factor de corrección τ(x, y) — transcripción verbatim del plano
    canónico `[VAULT-CORE-004]` §5.3.1, con las cotas analíticas de admisibilidad §5.16.1
    (Teorema de No-Negatividad Estricta, Invariante I13 ⇒ τ(x, y) ≥ 0.0 siempre).

    Fuera de los cuatro vértices corregidos τ ≡ 1.0000, por lo que la matriz de Poisson pura
    permanece intacta en el resto del retículo. Cero margen creativo: una sola coma alterada
    aquí rompe la paridad con la Bóveda.
    """
    cota_inf = -min(1.0 / max(0.01, lambda_h), 1.0 / max(0.01, lambda_a))
    cota_sup = min(1.0, 1.0 / max(0.01, lambda_h * lambda_a))
    rho_admisible = max(cota_inf, min(cota_sup, float(rho)))
    if x == 0 and y == 0:
        return 1.0 - (lambda_h * lambda_a * rho_admisible)
    if x == 0 and y == 1:
        return 1.0 + (lambda_h * rho_admisible)
    if x == 1 and y == 0:
        return 1.0 + (lambda_a * rho_admisible)
    if x == 1 and y == 1:
        return 1.0 - rho_admisible
    return 1.0


class PoissonBivariateEngine:
    @classmethod
    def compute_modulations(
        cls,
        h2h: H2HDecayResult,
        metrics: SyntheticMetricsResult,
        gf_local_10p: float,
        gf_vis_10p: float,
        pts_pj_local: float,
        pts_pj_vis: float,
        jornada_tabla: int,
        q_mod_local: float,
        q_mod_vis: float,
        is_fav_local: bool,
        odd_fav: float,
        odd_emp: float,
        odd_und: float,
        pago_anticipado_activo: bool,
        local_xg: float | None = None,
        vis_xga: float | None = None,
        vis_xg: float | None = None,
        local_xga: float | None = None,
        local_gc_10p: float | None = None,
        vis_gc_10p: float | None = None,
        xg_local_prom: float | None = None,
        xga_vis_prom: float | None = None,
        rho: float | None = None
    ) -> PoissonModulationResult:
        # Resolver alias de nombres Opta
        loc_xg = xg_local_prom if xg_local_prom is not None else local_xg
        v_xga = xga_vis_prom if xga_vis_prom is not None else vis_xga

        # 1. Ponderación adaptativa H2H vs Liga — [LN-QBE-020-B] Ley Zero-H2H
        if h2h.antiguedad_promedio_dias >= SENTINELA_ZERO_H2H_DIAS:
            # Sin antecedentes H2H reales: 100% métricas de liga
            w_h2h = 0.0
            w_liga = 1.0
        else:
            # [LN-QBE-020] Decaimiento con la vida media sellada (180 d), preservando la
            # amplitud y el piso promulgados en CONSTANTS.md §1 (Dictamen V-01, Opción B).
            w_h2h = max(W_H2H_PISO, W_H2H_AMP * math.exp(-KAPPA_H2H * h2h.antiguedad_promedio_dias))
            w_liga = 1.0 - w_h2h

        # 2. Modulador de tabla
        madurez = min(1.0, float(jornada_tabla) / SATURACION_MADUREZ_J)
        mod_tabla_l = 1.0 + madurez * ((pts_pj_local / BASELINE_LIGA) - 1.0)
        mod_tabla_v = 1.0 + madurez * ((pts_pj_vis / BASELINE_LIGA) - 1.0)

        # 3. Multiplicador compuesto (Omega)
        omega_l = float(np.clip(metrics.fcf_local * metrics.e_att_local * mod_tabla_l * q_mod_local, OMEGA_MIN, OMEGA_MAX))
        omega_v = float(np.clip(metrics.fcf_vis * metrics.e_att_vis * mod_tabla_v * q_mod_vis, OMEGA_MIN, OMEGA_MAX))

        # 4. Goles esperados (lambda, mu) con calibración cruzada Opta xG [LN-QBE-040]
        if loc_xg is not None and v_xga is not None:
            gc_v = vis_gc_10p if vis_gc_10p is not None else 1.0
            base_att_l = BLEND_XG * loc_xg + BLEND_GF * gf_local_10p
            base_def_v = BLEND_XG * v_xga + BLEND_GF * gc_v
            lambda_base = math.sqrt(max(0.01, base_att_l * base_def_v))
        else:
            lambda_base = gf_local_10p

        if vis_xg is not None and local_xga is not None:
            gc_l = local_gc_10p if local_gc_10p is not None else 1.0
            base_att_v = BLEND_XG * vis_xg + BLEND_GF * gf_vis_10p
            base_def_l = BLEND_XG * local_xga + BLEND_GF * gc_l
            mu_base = math.sqrt(max(0.01, base_att_v * base_def_l))
        else:
            mu_base = gf_vis_10p

        raw_lambda = ((w_h2h * h2h.gf_h2h_local) + (w_liga * lambda_base)) * omega_l
        raw_mu = ((w_h2h * h2h.gf_h2h_visita) + (w_liga * mu_base)) * omega_v

        lambda_loc = float(np.clip(raw_lambda, CLAMP_GOLES_MIN, CLAMP_GOLES_MAX))
        mu_vis = float(np.clip(raw_mu, CLAMP_GOLES_MIN, CLAMP_GOLES_MAX))

        # 5. Matriz Poisson Bivariada 6x6 con corrección Dixon-Coles táctica [LN-QBE-040-C]
        #    ρ = None ⇒ ley de resolución dinámica por régimen de anotación (Σλ vs 2.6500 xG).
        #    ρ explícito = escape hatch sellado de auditoría (ρ = 0.0 ⇒ Poisson pura, τ ≡ 1.0).
        rho_efectivo = resolver_rho_dixon_coles(lambda_loc, mu_vis) if rho is None else float(rho)
        p_mat = np.zeros((6, 6))
        for x in range(6):
            for y in range(6):
                tau = _dixon_coles_tau(
                    x, y, lambda_h=lambda_loc, lambda_a=mu_vis, rho=rho_efectivo
                )
                p_mat[x, y] = poisson.pmf(x, lambda_loc) * poisson.pmf(y, mu_vis) * tau

        # Normalizar matriz truncada
        p_mat /= np.sum(p_mat)

        p_poi_loc = float(np.sum(np.tril(p_mat, -1)))
        p_poi_emp = float(np.sum(np.diag(p_mat)))
        p_poi_vis = float(np.sum(np.triu(p_mat, 1)))

        if is_fav_local:
            p_poi_fav, p_poi_und = p_poi_loc, p_poi_vis
        else:
            p_poi_fav, p_poi_und = p_poi_vis, p_poi_loc

        # 6. Probabilidades Híbridas
        p_hib_fav = (w_h2h * h2h.p_fav) + (w_liga * p_poi_fav)
        p_hib_emp = (w_h2h * h2h.p_emp) + (w_liga * p_poi_emp)
        p_hib_und = (w_h2h * h2h.p_und) + (w_liga * p_poi_und)

        # Invarianza de masa de probabilidad
        p_sum = p_hib_fav + p_hib_emp + p_hib_und
        p_hib_fav /= p_sum
        p_hib_emp /= p_sum
        p_hib_und /= p_sum

        # 7. Variables Avanzadas
        gamma_inplay = min(0.28, (lambda_loc + mu_vis) / 14.0)

        # Suma de marcadores con ventaja >= 2 goles para el favorito
        lead2_sum = 0.0
        for x in range(6):
            for y in range(6):
                diff = (x - y) if is_fav_local else (y - x)
                if diff >= 2:
                    lead2_sum += p_mat[x, y]

        # Tránsito dinámico in-play
        p_1_0_fav = p_mat[1, 0] if is_fav_local else p_mat[0, 1]
        p_emp_transit = p_mat[1, 1] + p_mat[2, 2] + p_mat[3, 3]
        phi_lead2 = float(np.clip(lead2_sum + gamma_inplay * (p_1_0_fav + p_emp_transit), 0.0, 1.0))

        psi_ruina = p_hib_und * 0.98
        d_mkt = (1.0 / odd_fav) / p_hib_fav if p_hib_fav > 0 else 99.0

        edge_fav = p_hib_fav - (1.0 / odd_fav)
        edge_emp = p_hib_emp - (1.0 / odd_emp)
        edge_und = p_hib_und - (1.0 / odd_und)

        candidato_satelite = bool(odd_und >= 4.50 and pago_anticipado_activo and edge_und >= EDGE_MIN_SATELITE and q_mod_vis >= 0.95)

        return PoissonModulationResult(
            lambda_local=lambda_loc,
            mu_visitante=mu_vis,
            goles_esperados_totales=lambda_loc + mu_vis,
            peso_h2h=w_h2h,
            peso_liga=w_liga,
            omega_perf_local=omega_l,
            omega_perf_vis=omega_v,
            p_poisson_fav=p_poi_fav,
            p_poisson_emp=p_poi_emp,
            p_poisson_und=p_poi_und,
            prob_hibrida_fav=p_hib_fav,
            prob_hibrida_empate=p_hib_emp,
            prob_hibrida_und=p_hib_und,
            phi_lead2=phi_lead2,
            psi_ruina=psi_ruina,
            d_mkt=d_mkt,
            edge_fav=edge_fav,
            edge_empate=edge_emp,
            edge_und=edge_und,
            candidato_satelite=candidato_satelite
        )