# -*- coding: utf-8 -*-
"""
JUEZ INMUTABLE: [LN-QBE-038] & [ARCH-1.6.13-C] Calibración de Localía, Plaza y H2H Profundo
Base de Gobierno: docs/LOGIC.md [LN-QBE-038] / docs/CONSTANTS.md / docs/ARCH.md [ARCH-1.6.13-C]
Autoridad: Américo García Guerrero (Director Humano)
Régimen: [DIRGEN-STRICT] — Inmutable, Cero Mocks.
"""

import pytest
import math
from src.core.intensity_canonical_loglink import estimar_intensidades_loglineal, calcular_alpha_ligadura
from src.core.sovereign_pipeline import generar_distribucion_soberana, derivar_factores_estructurales


def test_invarianza_plaza_fortaleza_bono():
    """
    [INVARIANZA 1 - FORTALEZA DE PLAZA EL VOLCÁN]:
    Verifica que Tigres reciba el bono gamma_plaza (+0.07) sobre la localía base (0.15),
    llegando a gamma_home = 0.2200, y que alpha se recalcule consistentemente.
    """
    gamma_base = 0.15
    bono_volcan = 0.07  # El Volcán en docs/CONSTANTS.md
    gamma_tigres = gamma_base + bono_volcan
    
    alpha_tigres = calcular_alpha_ligadura(mu_liga=2.65, gamma_home=gamma_tigres)
    
    # alpha = ln(2.65) - ln(1 + exp(0.22)) = 0.97456 - 0.80917 = 0.1654
    assert abs(gamma_tigres - 0.2200) < 1e-4
    assert abs(alpha_tigres - 0.1654) < 1e-3, f"Alpha mal calculado: {alpha_tigres}"


def test_invarianza_desglose_sede_tigres_recupera_fuerza():
    """
    [INVARIANZA 2 - FUSIÓN DE SPLITS LOCAL/VISITA]:
    Un local con récord general pobre (10 GF en 10 PJ) pero localía invicta
    (16 GF y 4 GC en 10 PJ) NO debe colapsar a lambda_H <= 1.15.
    Al inyectar los splits de sede, lambda_H debe ser >= 1.35 xG y mu_A <= 1.20 xG.
    """
    raw_data_con_splits = {
        "home_team_stats": {"pj": 10, "gf": 10, "gc": 13},  # General
        "away_team_stats": {"pj": 10, "gf": 23, "gc": 12},  # General
        "home_split_stats": {"pj": 10, "gf": 16, "gc": 4},  # Local Tigres (El Volcán)
        "away_split_stats": {"pj": 10, "gf": 13, "gc": 13},  # Visita Toluca
        "home_team_slug": "tigres-uanl"
    }
    
    # En el sistema actual sin el nodo LN-QBE-038, generar_distribucion_soberana
    # ignora los splits y arroja lambda_H = 1.10 y lambda_A = 1.95.
    # Con el nuevo nodo implementado, lambda_H debe subir a >= 1.35.
    dist_out = generar_distribucion_soberana(
        match_id="LIGAMX-J11-TEST",
        raw_match_data=raw_data_con_splits,
        mu_liga=2.65,
        gamma_home_base=0.15
    )
    
    assert dist_out.lambda_home >= 1.35, (
        f"🚨 FALLO DE LOCALÍA: Tigres invicto en casa no puede tener lambda={dist_out.lambda_home}. "
        f"Debe superar 1.35 xG con la integración de home_split_stats."
    )
    assert dist_out.lambda_away <= 1.20, (
        f"🚨 FALLO DE CONTENCIÓN: Toluca de visita frente a defensa de 4 GC no puede tener mu={dist_out.lambda_away}. "
        f"Debe ser <= 1.20 xG."
    )


def test_invarianza_h2h_profundo_multianual():
    """
    [INVARIANZA 3 - KERNEL H2H SIN CORTE ARTIFICIAL DE 180 DÍAS]:
    5 partidos históricos oficiales con antigüedad de hasta 750 días
    DEBEN ponderar con tau = 540d y NO colapsar a Zero-H2H (delta_epist debe ser > 0).
    """
    # 5 enfrentamientos Tigres vs Toluca de los últimos 2 años
    h2h_5_partidos = [
        {"goles_local": 1, "goles_visita": 2, "dias_antiguedad": 210},  # Toluca 2-1
        {"goles_local": 2, "goles_visita": 2, "dias_antiguedad": 380},  # 2-2
        {"goles_local": 1, "goles_visita": 3, "dias_antiguedad": 500},  # Toluca 3-1
        {"goles_local": 4, "goles_visita": 1, "dias_antiguedad": 504},  # Tigres 4-1
        {"goles_local": 3, "goles_visita": 1, "dias_antiguedad": 740},  # Tigres 3-1
    ]
    
    raw_data = {
        "home_team_stats": {"pj": 10, "gf": 10, "gc": 13},
        "away_team_stats": {"pj": 10, "gf": 23, "gc": 12},
        "h2h_matches": h2h_5_partidos,
        "home_team_slug": "tigres-uanl"
    }
    
    dist_out = generar_distribucion_soberana(
        match_id="LIGAMX-J11-TEST",
        raw_match_data=raw_data
    )
    
    # En el sistema actual, si delta_epist es 0.0 o no se leen los 5 partidos
    assert dist_out.delta_epist > 0.02, (
        f"🚨 H2H CIEGO: El historial de 5 partidos reales fue ignorado o colapsó a delta_epist={dist_out.delta_epist}."
    )


def test_invarianza_soberania_tigres_toluca_resuelve_asimetria():
    """
    [INVARIANZA 4 - TRANSMUTACIÓN DE P' Y CORRECCIÓN DEL SESGO]:
    Con el modelo calibrado, Tigres en El Volcán NO puede ser un underdog de 20%.

    [VAR-2026-10-17-H2H-FUSION · ALT-C] El piso/techo cuantitativo (p_local ≥ 0.40, p_visitante ≤ 0.32)
    se certifica sobre el GENERADOR A (`audit_trace.simplex_poisson`), que es el objeto que la
    calibración de sede y plaza gobierna (λ y dominancia estructural). El símplex PUBLICADO es ahora la
    mezcla convexa [LN-QBE-104] P_hib = w_Liga·P_A + w_H2H·P_C con w_H2H = min(0.25, N·0.05); sobre él
    rigen los invariantes ESTRUCTURALES: dominancia local, orden del podio y acotamiento por componente.
    Este fixture publica H2H adverso (Toluca ganó 2 de los 5 duelos recientes), por lo que el kernel
    empírico empuja legítimamente la mezcla hacia abajo: el techo/piso sigue siendo del Generador A.
    """
    raw_data_completo = {
        "home_team_stats": {"pj": 10, "gf": 10, "gc": 13},
        "away_team_stats": {"pj": 10, "gf": 23, "gc": 12},
        "home_split_stats": {"pj": 10, "gf": 16, "gc": 4},
        "away_split_stats": {"pj": 10, "gf": 13, "gc": 13},
        "h2h_matches": [
            {"goles_local": 1, "goles_visita": 2, "dias_antiguedad": 210},
            {"goles_local": 2, "goles_visita": 2, "dias_antiguedad": 380},
            {"goles_local": 1, "goles_visita": 3, "dias_antiguedad": 500},
            {"goles_local": 4, "goles_visita": 1, "dias_antiguedad": 504},
            {"goles_local": 3, "goles_visita": 1, "dias_antiguedad": 740},
        ],
        "home_team_slug": "tigres-uanl",
        "q_mod_h": 1.03,
        "q_mod_a": 0.97
    }
    
    dist_out = generar_distribucion_soberana(
        match_id="LIGAMX-J11-TIG-TOL",
        raw_match_data=raw_data_completo,
        mu_liga=2.65,
        gamma_home_base=0.15
    )
    
    # ── Generador A (Poisson paramétrico): el piso/techo que la calibración de plaza gobierna ──
    simplex_poisson = dict(dist_out.audit_trace.simplex_poisson)
    assert simplex_poisson, "La traza debe publicar el símplex Poisson pre-fusión [LN-QBE-104]."
    p_local_poisson = float(simplex_poisson["p_1"])
    p_visita_poisson = float(simplex_poisson["p_2"])

    assert p_local_poisson >= 0.40, (
        f"🚨 SESGO PERSISTENTE: Tigres en casa tiene p_local(Poisson)={p_local_poisson:.3f}. "
        f"Debe ser >= 0.400 tras la calibración de sede y plaza."
    )
    assert p_visita_poisson <= 0.32, (
        f"🚨 SOBREESTIMACIÓN FORÁNEA: Toluca de visita tiene p_visita(Poisson)={p_visita_poisson:.3f}. "
        f"Debe ser <= 0.320."
    )

    # ── Símplex publicado: invariantes estructurales de la mezcla convexa [LN-QBE-104] ──
    assert dist_out.p_local > dist_out.p_visitante, (
        f"🚨 ASIMETRÍA PERDIDA: el símplex híbrido publica p_local={dist_out.p_local:.3f} "
        f"≤ p_visitante={dist_out.p_visitante:.3f}."
    )
    assert dist_out.p_local > dist_out.p_empate, (
        f"🚨 PODIO INVERTIDO: p_local={dist_out.p_local:.3f} ≤ p_empate={dist_out.p_empate:.3f}."
    )
    assert abs(dist_out.p_local + dist_out.p_empate + dist_out.p_visitante - 1.0) <= 1e-12, (
        "La mezcla convexa debe habitar el símplex Δ²."
    )
    kernel = dist_out.audit_trace.kernel_h2h_empirico
    assert 0.0 < kernel["peso_h2h"] <= 0.25, "w_H2H debe respetar el tope fiduciario 0.25."
    for hibrida, poisson_pura, empirica in (
        (dist_out.p_local, p_local_poisson, kernel["p_local"]),
        (dist_out.p_empate, float(simplex_poisson["p_X"]), kernel["p_empate"]),
        (dist_out.p_visitante, p_visita_poisson, kernel["p_visita"]),
    ):
        assert min(poisson_pura, empirica) - 1e-12 <= hibrida <= max(poisson_pura, empirica) + 1e-12, (
            "Cada componente del símplex publicado debe quedar acotada entre generadores."
        )
    assert 0.0 < dist_out.epistemic_delta <= 1.0, (
        f"Δ_epist(∞) fuera de rango: {dist_out.epistemic_delta!r}."
    )

