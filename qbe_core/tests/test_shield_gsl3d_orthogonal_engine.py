# -*- coding: utf-8 -*-
"""
JUEZ INMUTABLE: [LN-QBE-039] & [ARCH-1.4.33] Motor GSL-3D y Anti-Resonancia
Base de Gobierno: docs/LOGIC.md [LN-QBE-039] / docs/CONSTANTS.md / docs/ARCH.md [ARCH-1.4.33]
Autoridad: Américo García Guerrero (Director Humano)
Régimen: [DIRGEN-STRICT] — Inmutable, Cero Mocks.
"""

import pytest
import math
from src.core.intensity_canonical_loglink import estimar_intensidades_loglineal, calcular_alpha_ligadura
from src.core.sovereign_pipeline import generar_distribucion_soberana


def test_invarianza_desamplificacion_america_vs_monterrey():
    """
    [INVARIANZA 1 - CONTROL DE RESONANCIA AMÉRICA VS RAYADOS]:
    Verifica que Club América NO sea inflado artificialmente a p_local = 78.8%
    frente a Rayados de Monterrey. El modelo GSL-3D debe purgar la redundancia
    de localía en un club con calidad general ya dominante.
    
    Límites Constitucionales Exigidos:
    - p_local (América) <= 0.6000 (60.0% máx, en línea con el mercado ~50%)
    - p_visita (Monterrey) >= 0.1800 (18.0% mín, erradicando el colapso al 8.0%)
    - lambda_local (América) <= 1.90 xG (erradicando la hiper-intensidad de 2.45 xG)
    """
    # Datos de la Jornada 11 activa
    raw_data_america_monterrey = {
        "home_team_stats": {"pj": 10, "gf": 21, "gc": 11, "xg": 19.5},  # América General
        "away_team_stats": {"pj": 10, "gf": 18, "gc": 12, "xg": 16.8},  # Monterrey General
        "home_split_stats": {"pj": 10, "gf": 22, "gc": 10},             # América Sede
        "away_split_stats": {"pj": 10, "gf": 14, "gc": 14},             # Monterrey Sede
        "home_team_slug": "club-america",
        "h2h_matches": [
            {"goles_local": 2, "goles_visita": 1, "dias_antiguedad": 120},
            {"goles_local": 1, "goles_visita": 1, "dias_antiguedad": 240},
            {"goles_local": 2, "goles_visita": 2, "dias_antiguedad": 380},
            {"goles_local": 0, "goles_visita": 1, "dias_antiguedad": 520},
            {"goles_local": 3, "goles_visita": 0, "dias_antiguedad": 680},
        ]
    }
    
    dist_out = generar_distribucion_soberana(
        match_id="LIGAMX-J11-AME-MON",
        raw_match_data=raw_data_america_monterrey,
        mu_liga=2.65,
        gamma_home_base=0.15
    )
    
    # En el código actual no-ortogonalizado, América arroja p_local = 0.788 y lambda = 2.40.
    # Este assert DEBE FALLAR EN ROJO antes de la materialización de GSL-3D.
    assert dist_out.p_local <= 0.6000, (
        f"🚨 RESONANCIA EXCESIVA: América tiene p_local={dist_out.p_local:.4f}. "
        f"Debe ser <= 0.6000 para evitar sobre-amplificación contra Rayados."
    )
    assert dist_out.p_visitante >= 0.1800, (
        f"🚨 COLAPSO DE RIVAL: Rayados fue comprimido a p_visita={dist_out.p_visitante:.4f}. "
        f"Debe ser >= 0.1800."
    )
    assert dist_out.lambda_home <= 1.90, (
        f"🚨 INTENSIDAD DESBORDADA: América proyecta lambda={dist_out.lambda_home} xG. "
        f"Debe estar acotada a <= 1.90 xG bajo GSL-3D."
    )


def test_invarianza_preservacion_fuerza_tigres_el_volcan():
    """
    [INVARIANZA 2 - PRESERVACIÓN DEL RESIDUO LEGÍTIMO DE TIGRES]:
    GSL-3D no debe desinflar ciegamente a todos los locales. Tigres en El Volcán
    posee un residuo genuino no explicado por su récord general (invicto 16 GF, 4 GC).
    Debe mantener p_local >= 0.4000 y lambda_H >= 1.35 xG frente a Toluca.

    [VAR-2026-10-17-H2H-FUSION · ALT-C] El piso p_local ≥ 0.4000 se certifica sobre el GENERADOR A
    (`audit_trace.simplex_poisson`), que es el objeto que la ortogonalización GSL-3D gobierna. El símplex
    PUBLICADO es la mezcla convexa [LN-QBE-104] con w_H2H = min(0.25, N·0.05); este fixture publica H2H
    adverso (Toluca ganó 2 de los 5 duelos recientes), por lo que sobre él rige la dominancia local.
    """
    raw_data_tigres_toluca = {
        "home_team_stats": {"pj": 10, "gf": 10, "gc": 13},  # Tigres General
        "away_team_stats": {"pj": 10, "gf": 23, "gc": 12},  # Toluca General
        "home_split_stats": {"pj": 10, "gf": 16, "gc": 4},  # Tigres Sede
        "away_split_stats": {"pj": 10, "gf": 13, "gc": 13},  # Toluca Sede
        "home_team_slug": "tigres-uanl",
        "h2h_matches": [
            {"goles_local": 1, "goles_visita": 2, "dias_antiguedad": 210},
            {"goles_local": 2, "goles_visita": 2, "dias_antiguedad": 380},
            {"goles_local": 1, "goles_visita": 3, "dias_antiguedad": 500},
            {"goles_local": 4, "goles_visita": 1, "dias_antiguedad": 504},
            {"goles_local": 3, "goles_visita": 1, "dias_antiguedad": 740},
        ],
        "q_mod_h": 1.03,
        "q_mod_a": 0.97
    }
    
    dist_out = generar_distribucion_soberana(
        match_id="LIGAMX-J11-TIG-TOL",
        raw_match_data=raw_data_tigres_toluca,
        mu_liga=2.65,
        gamma_home_base=0.15
    )
    
    # [VAR-2026-10-17-H2H-FUSION · ALT-C] Piso sobre el Generador A + dominancia sobre el publicado.
    simplex_poisson = dict(dist_out.audit_trace.simplex_poisson)
    assert simplex_poisson, "La traza debe publicar el símplex Poisson pre-fusión [LN-QBE-104]."
    p_local_poisson = float(simplex_poisson["p_1"])
    assert p_local_poisson >= 0.4000, (
        f"🚨 INJUSTICIA CON EL VOLCÁN: Tigres en casa cayó a p_local(Poisson)={p_local_poisson:.4f}. "
        f"Debe conservar p_local >= 0.4000."
    )
    assert dist_out.p_local > dist_out.p_visitante, (
        f"🚨 DOMINANCIA PERDIDA: el símplex híbrido publica p_local={dist_out.p_local:.4f} "
        f"≤ p_visitante={dist_out.p_visitante:.4f}."
    )
    assert abs(dist_out.p_local + dist_out.p_empate + dist_out.p_visitante - 1.0) <= 1e-12, (
        "La mezcla convexa debe habitar el símplex Δ²."
    )
    assert dist_out.lambda_home >= 1.35, (
        f"🚨 PERDIDA DE FUERZA EN EL VOLCÁN: Tigres proyecta lambda={dist_out.lambda_home} xG. "
        f"Debe ser >= 1.35 xG."
    )
