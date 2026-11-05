# -*- coding: utf-8 -*-
"""
🏆 THE SHIELD — RIGOR DEL NÚCLEO v2 (E-50.1 · GSL-3D §7.6)
Juez Inmutable: [VAULT-CORE-001] / [LN-QBE-039] / [E-50.1]
Base de Gobierno: docs/DIRGEN_VAULT.md §E-50.1 · docs/LOGIC.md §7.2 y §7.6 · docs/CONSTANTS.md §2
Régimen: [DIRGEN-STRICT] — Inmutable, Cero Mocks.
Expediente: SPRINT-50-REINGENIERIA-INDUSTRIAL-QBE-CORE
"""

import math

import pytest

from src.core.intensity_canonical_loglink import (
    InsufficientDataException,
    calcular_alpha_ligadura,
    estimar_intensidades_loglineal,
)
from src.core.sovereign_pipeline import generar_distribucion_soberana
from src.core.sovereign.orthogonal_factor_engine import resolver_factores_latentes_gsl3d_v2

MU_LIGA = 2.65
TOLERANCIA_MASA = 1e-12

# Tres escenarios de la clase C-2: neutro, altitud extrema + descanso corto, altitud máxima + descanso largo.
ESCENARIOS_CONTEXTO = (
    {"delta_alt_metros": 0.0, "delta_descanso_dias": 0.0},
    {"delta_alt_metros": 1000.0, "delta_descanso_dias": -3.0},
    {"delta_alt_metros": 2500.0, "delta_descanso_dias": 3.0},
)


# ═══════════════════════════════════════════════════════════════════════════════════════
# ASERCIÓN 1 — CONSERVACIÓN ESTRICTA DE MASA (Invariante L-1, E-50.1)
# ═══════════════════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("escenario", ESCENARIOS_CONTEXTO)
def test_asercion_1_conservacion_de_masa_exacta(escenario):
    """`λ_H + λ_A == μ_liga` con `A=D=0` y `q=1`, en todo el dominio de Δalt/Δrest (1e-12)."""
    lambda_h, lambda_a = estimar_intensidades_loglineal(
        A_home=0.0, D_away=0.0, A_away=0.0, D_home=0.0,
        mu_liga=MU_LIGA, gamma_home_base=0.15,
        **escenario,
    )
    suma = lambda_h + lambda_a
    assert abs(suma - MU_LIGA) <= TOLERANCIA_MASA, (
        f"🚨 [E-50.1 L-1] Fuga de masa con {escenario}: λ_H+λ_A={suma!r} ≠ {MU_LIGA}. "
        f"El intercepto contextual NO está cerrado en α."
    )
    assert lambda_h > 0.0 and lambda_a > 0.0, "Positividad estricta (Invariante I6)."


def test_asercion_1b_ligadura_sobre_intercepto_completo():
    """α(γ_efectivo) reproduce la identidad analítica en los cuatro puntos sellados (E-50.1.7)."""
    vectores = (
        (0.150, 0.203603),
        (0.180, 0.187368),
        (0.225, 0.162598),
        (0.090, 0.235400),
    )
    for gamma_efectivo, esperado in vectores:
        alpha = calcular_alpha_ligadura(MU_LIGA, gamma_efectivo)
        assert math.isclose(alpha, esperado, abs_tol=5e-7), (
            f"🚨 [E-50.1] α(μ={MU_LIGA}, γ={gamma_efectivo})={alpha!r} ≠ {esperado}."
        )


# ═══════════════════════════════════════════════════════════════════════════════════════
# ASERCIÓN 2 — ERRADICACIÓN DE MOCKS (E-50.1 P-01)
# ═══════════════════════════════════════════════════════════════════════════════════════
def test_asercion_2_sin_gf_lanza_insufficient_data():
    """Un registro sin `gf` NO se rellena con 10: levanta `InsufficientDataException`."""
    registro_sin_gf = {
        "home_team_stats": {"pj": 8, "gc": 10},
        "away_team_stats": {"pj": 8, "gf": 7, "gc": 12},
    }
    with pytest.raises(InsufficientDataException) as excinfo:
        generar_distribucion_soberana("TEST-MOCK-GF", registro_sin_gf)

    error = excinfo.value
    assert error.clave == "gf", f"La excepción debe señalar la clave ausente; señaló {error.clave!r}."
    assert error.lado == "local", f"La excepción debe señalar el lado; señaló {error.lado!r}."
    assert error.match_id == "TEST-MOCK-GF", "La excepción debe conservar el match_id."


def test_asercion_2b_sin_gc_visitante_tambien_falla():
    """Simetría de la aduana: la misma ley aplica al lado visitante (`gc`)."""
    registro_sin_gc = {
        "home_team_stats": {"pj": 8, "gf": 12, "gc": 9},
        "away_team_stats": {"pj": 8, "gf": 7},
    }
    with pytest.raises(InsufficientDataException) as excinfo:
        generar_distribucion_soberana("TEST-MOCK-GC", registro_sin_gc)
    assert excinfo.value.clave == "gc"
    assert excinfo.value.lado == "visita"


# ═══════════════════════════════════════════════════════════════════════════════════════
# ASERCIÓN 3 — GSL-3D v2: PROYECCIÓN ORTOGONAL Y COLINEALIDAD NEUTRALIZADA §7.6
# ═══════════════════════════════════════════════════════════════════════════════════════
def _matriz_con_colinealidad(n_filas: int = 12):
    """Matriz causal con V06 ≡ V07 (colineales exactos) y V08 independiente."""
    filas = []
    for i in range(n_filas):
        valor_base = 1.0 + 0.10 * i
        filas.append(
            {
                "V06": valor_base,
                "V07": valor_base,                      # colineal exacto con V06
                "V08": 0.40 + 0.05 * ((i * 3) % 5),
                "V12": 1.20 - 0.05 * i,
                "V13": 2.00 + 0.03 * ((i * 2) % 4),
            }
        )
    return filas


_MEDIAS_LIGA = {"V06": 1.55, "V07": 1.55, "V08": 0.55, "V12": 0.90, "V13": 2.05}
_VECTOR_FIXTURE = {"V06": 1.60, "V07": 1.60, "V08": 0.60, "V12": 0.95, "V13": 2.00}


def test_asercion_3_colinealidad_asigna_peso_cero():
    """Dos variables idénticas: la segunda es COLINEAL y aporta exactamente 0 (no infla λ)."""
    resultado = resolver_factores_latentes_gsl3d_v2(
        _matriz_con_colinealidad(), _VECTOR_FIXTURE, _MEDIAS_LIGA
    )

    assert resultado.estados["V07"] == "COLINEAL", (
        f"🚨 [§7.6.4] V07 es idéntica a V06 y debió declararse COLINEAL; "
        f"estado={resultado.estados.get('V07')!r}."
    )
    assert resultado.contribuciones["V07"] == 0.0, (
        "🚨 Una variable colineal no puede aportar peso distinto de 0."
    )
    assert resultado.estados["V06"] == "CONSUMIDA", "El pivote (V06) debe conservarse."
    assert resultado.n_att == 2, f"Se esperaban 2 atacantes no colineales (V06, V08); n_att={resultado.n_att}."
    assert resultado.n_def == 2, f"Se esperaban 2 defensivos no colineales; n_def={resultado.n_def}."
    assert resultado.suficiente is True


def test_asercion_3b_duplicar_una_columna_no_altera_el_factor():
    """No inflación: `A*` con V07 duplicada ≡ `A*` sin V07 (1e-12)."""
    filas = _matriz_con_colinealidad()
    con_duplicado = resolver_factores_latentes_gsl3d_v2(filas, _VECTOR_FIXTURE, _MEDIAS_LIGA)
    sin_duplicado = resolver_factores_latentes_gsl3d_v2(
        [{k: v for k, v in fila.items() if k != "V07"} for fila in filas],
        {k: v for k, v in _VECTOR_FIXTURE.items() if k != "V07"},
        _MEDIAS_LIGA,
    )
    assert abs(con_duplicado.A_star - sin_duplicado.A_star) <= 1e-12, (
        f"🚨 [§7.6.5] La colinealidad infló el factor: {con_duplicado.A_star} vs {sin_duplicado.A_star}."
    )
    assert abs(con_duplicado.D_star - sin_duplicado.D_star) <= 1e-12


def test_asercion_3c_matriz_suficiente_publica_traza_gsl3d():
    """Con matriz suficiente, el pipeline opera con procedencia `gsl3d_v2` y traza por lado."""
    filas_local = [
        {"V06": 1.0 + 0.1 * i, "V08": 0.40 + 0.05 * ((i * 3) % 5),
         "V12": 1.20 - 0.05 * i, "V13": 2.00 + 0.03 * ((i * 2) % 4)}
        for i in range(12)
    ]
    filas_visita = [
        {"V06": 0.9 + 0.08 * i, "V08": 0.35 + 0.04 * ((i * 2) % 5),
         "V12": 1.50 - 0.03 * i, "V13": 1.80 + 0.02 * ((i * 3) % 4)}
        for i in range(12)
    ]
    registro = {
        "home_team_stats": {"pj": 12},
        "away_team_stats": {"pj": 12},
        "matriz_causal": {
            "local": filas_local,
            "visita": filas_visita,
            "vector_local": {"V06": 1.55, "V08": 0.62, "V12": 1.05, "V13": 2.10},
            "vector_visita": {"V06": 1.30, "V08": 0.48, "V12": 1.35, "V13": 1.95},
            "medias_liga": {"V06": 1.55, "V08": 0.55, "V12": 1.05, "V13": 2.05},
        },
    }
    salida = generar_distribucion_soberana("TEST-GSL3D-V2", registro)

    assert salida.es_operable is True, "La matriz suficiente debe habilitar la operación."
    assert salida.origen_factores == "gsl3d_v2", (
        f"Procedencia declarada incorrecta: {salida.origen_factores!r}."
    )
    assert salida.audit_trace.gsl3d is not None, "La traza debe publicar la proyección §7.6."
    assert salida.audit_trace.gsl3d["local"]["cobertura"] >= 2
    assert abs(salida.p_local + salida.p_empate + salida.p_visitante - 1.0) <= 1e-12


def test_asercion_3d_matriz_insuficiente_declara_sin_evidencia():
    """`n_A < 2` ⇒ el partido se declara SIN EVIDENCIA (fail-loud, cero cálculo)."""
    matriz_pobre = {
        "local": [{"V06": 1.0 + 0.1 * i, "V12": 1.0} for i in range(10)],
        "visita": [{"V06": 1.0 + 0.1 * i, "V12": 1.0} for i in range(10)],
        "vector_local": {"V06": 1.5, "V12": 1.0},
        "vector_visita": {"V06": 1.4, "V12": 1.1},
        "medias_liga": {"V06": 1.55, "V12": 1.05},
    }
    registro = {
        "home_team_stats": {"pj": 8, "gf": 12, "gc": 9},
        "away_team_stats": {"pj": 8, "gf": 10, "gc": 11},
        "matriz_causal": matriz_pobre,
    }
    salida = generar_distribucion_soberana("TEST-MATRIZ-POBRE", registro)

    assert salida.es_operable is False
    assert salida.audit_trace.suficiencia_S_I == 0
    assert salida.audit_trace.motivo_insuficiencia is not None
    assert "MATRIZ_CAUSAL_INSUFICIENTE" in salida.audit_trace.motivo_insuficiencia
