# -*- coding: utf-8 -*-
"""
[CONSTANTS.md §8] Dominio de Física Estocástica y Clamps (Saneamiento O-04 y O-14).

Fuente única de los literales de madurez, mezcla xG/GF, clamps de rendimiento y goles
esperados. Los valores son inmutables y están legislados en `docs/CONSTANTS.md` §8.
"""

# ── CONSTANTS.md §8 — valores legislados ─────────────────────────────────────
BASELINE_LIGA: float = 1.35
SATURACION_MADUREZ_J: float = 6.0
OMEGA_MIN: float = 0.40
OMEGA_MAX: float = 1.60
BLEND_XG: float = 0.65
BLEND_GF: float = 0.35
CLAMP_GOLES_MIN: float = 0.05
CLAMP_GOLES_MAX: float = 6.00
DELTA_EPIST_DEFAULT: float = 0.02

# ── Auxiliares de evaluación (mismos valores, semántica distinta) ────────────
# Se bautizan para erradicar los literales homónimos que no pertenecen al clamp
# físico: umbral de satélite, defaults de theta/psi y psi_downside de mercado.
EDGE_MIN_SATELITE: float = 0.05
THETA_FAV_H1_DEFAULT: float = 0.40
THETA_UND_R1_DEFAULT: float = 0.35
CANDADO_3_H2H_MIN: float = 0.4000
PSI_RUINA_DEFAULT: float = 0.05
PSI_DOWNSIDE_DEFAULT: float = 0.05

# ── [LN-QBE-075 / P1-5] Prior de Ignorancia Fiduciaria (Progol) ──────────────
# Fuente única legislada; vivía en `src.ingestion.progol_scraper` y se movió al
# núcleo para que `progol_math` no dependa de la ingesta.
PRIOR_IGNORANCIA_FIDUCIARIA: tuple[float, float, float] = (0.3333, 0.3333, 0.3334)
