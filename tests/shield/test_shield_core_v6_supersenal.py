# -*- coding: utf-8 -*-
"""
🏆 THE SHIELD — FASE 6: SÚPER-SEÑAL, κ VARIABLE Y SISTEMA INMUNE
Juez Inmutable: [E-50.9] / [E-50.10]
Régimen: [DIRGEN-STRICT] — Inmutable, Cero Mocks.
Expediente: SPRINT-50-REINGENIERIA-INDUSTRIAL-QBE-CORE (Fase 6)
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
for _ruta in (RAIZ, RAIZ / "qbe_core"):
    if str(_ruta) not in sys.path:
        sys.path.insert(0, str(_ruta))

from src.core.intensity_canonical_loglink import (  # noqa: E402
    KAPPA_NET,
    estimar_intensidades_loglineal,
)
from src.core.sovereign_pipeline import generar_distribucion_v6  # noqa: E402
from src.core.triage import veto_inmunidad_fiduciaria  # noqa: E402


def _raw(xg_h=1.4, sot_h=4.3, xga_h=1.3, xg_a=1.2, sot_a=3.9, xga_a=1.5):
    return {
        "home_team_stats": {"pj": 10, "xg": xg_h, "sot": sot_h, "xga": xga_h},
        "away_team_stats": {"pj": 10, "xg": xg_a, "sot": sot_a, "xga": xga_a},
        "medias_liga": {"xg": 1.35, "sot": 4.2, "xga": 1.4},
    }


# ── 1. α fija + conservación de masa ────────────────────────────────────────────────────────
def test_v6_conserva_masa_con_factores_neutros():
    """Con tasas iguales a la media de liga ⇒ A=D≈0 ⇒ λ_H+λ_A = μ = 2.65 (α fija)."""
    raw = _raw(xg_h=1.35, sot_h=4.2, xga_h=1.4, xg_a=1.35, sot_a=4.2, xga_a=1.4)
    out = generar_distribucion_v6("TEST-V6-NEUTRO", raw)
    assert out.es_operable is True
    assert out.origen_factores == "super_senal"
    assert abs((out.lambda_home + out.lambda_away) - 2.65) <= 1e-9, (
        f"Fuga de masa: {out.lambda_home + out.lambda_away}"
    )


def test_v6_super_senal_responde_a_la_direccion_correcta():
    """Favorito con xG/SoT altos y xGA bajo proyecta más λ que el rival."""
    raw = _raw(xg_h=1.8, sot_h=5.0, xga_h=1.0, xg_a=0.9, sot_a=3.0, xga_a=1.8)
    out = generar_distribucion_v6("TEST-V6-FAV", raw)
    assert out.lambda_home > out.lambda_away


# ── 2. κ variable ───────────────────────────────────────────────────────────────────────────
def test_kappa_variable_cambia_la_compresion():
    """κ_net distinto del sellado altera la intensidad (y por tanto el damping)."""
    base = estimar_intensidades_loglineal(0.6, 0.0, 0.0, 0.0)
    comprimido = estimar_intensidades_loglineal(0.6, 0.0, 0.0, 0.0, kappa_net=0.45)
    assert base[0] != comprimido[0]
    # κ mayor ⇒ más techo ⇒ el factor comprimido se acerca a κ·tanh(x/κ) con mayor cota.
    assert KAPPA_NET == 0.25  # sello intacto por defecto


# ── 3. Sistema Inmune ───────────────────────────────────────────────────────────────────────
def test_veto_ineficacia_ofensiva():
    p25 = {"V06": 1.0, "V09": 1.0, "V13": 3.0, "V25": 2.0, "V31": 1.0}
    p75 = {"V06": 1.8, "V09": 2.0, "V13": 5.0, "V25": 3.0, "V31": 3.0}
    p90 = {"V06": 2.2, "V09": 3.0, "V13": 7.0, "V25": 4.0, "V31": 4.0}
    # xG alto + chances falladas muy altas + tarjetas altas ⇒ INEFICACIA_OFENSIVA
    vector = {"V06": 2.0, "V09": 3.5, "V25": 3.2}
    veto = veto_inmunidad_fiduciaria(vector, p25, p75, p90)
    assert veto is not None and veto["codigo"] == "QBE-00"
    assert veto["arquetipo_veto"] == "INEFICACIA_OFENSIVA"


def test_veto_sobreasedio_defensivo():
    p25 = {"V06": 1.0, "V09": 1.0, "V13": 3.0, "V25": 2.0, "V31": 1.0}
    p75 = {"V06": 1.8, "V09": 2.0, "V13": 5.0, "V25": 3.0, "V31": 3.0}
    p90 = {"V06": 2.2, "V09": 3.0, "V13": 7.0, "V25": 4.0, "V31": 4.0}
    veto = veto_inmunidad_fiduciaria({"V13": 8.0, "V31": 0.5}, p25, p75, p90)
    assert veto is not None and veto["arquetipo_veto"] == "SOBREASEDIO_DEFENSIVO"


def test_veto_no_dispara_sobre_club_sano():
    p25 = {"V06": 1.0, "V09": 1.0, "V13": 3.0, "V25": 2.0, "V31": 1.0}
    p75 = {"V06": 1.8, "V09": 2.0, "V13": 5.0, "V25": 3.0, "V31": 3.0}
    p90 = {"V06": 2.2, "V09": 3.0, "V13": 7.0, "V25": 4.0, "V31": 4.0}
    assert veto_inmunidad_fiduciaria({"V06": 1.5, "V09": 1.5, "V25": 2.5}, p25, p75, p90) is None
