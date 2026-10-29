# -*- coding: utf-8 -*-
"""
🛡️ THE SHIELD — JUEZ INMUTABLE DE LA CALIBRACIÓN TÁCTICA DE ρ (DIXON-COLES DINÁMICO)
[LN-QBE-040-C] Parámetro de Correlación Táctica Bivariada (ρ) en Partidos de Baja Anotación
Régimen: [DIRGEN-STRICT] (ley de resolución, constantes y factor τ son INMUTABLES).
Axioma: concentrar masa fiduciaria en los vértices de empate de baja anotación (0,0) y (1,1)
        SOLO cuando Σλ ≤ 2.6500 xG, sin alterar una sola coma del plano sellado de τ(x, y),
        de las cotas de admisibilidad §5.16.1 ni de la renormalización [VAULT-CORE-004].
Cero mocks: los tres invariantes ejercen el código de producción y el pipeline soberano real.

Fixtures de control (Σλ verificada empíricamente con `generar_distribucion_soberana`):
* `_FIXTURE_CERRADO`: Σλ = 2.1222 xG (0.5278 por debajo de la frontera ⇒ rama táctica).
* `_FIXTURE_ABIERTO`: Σλ = 2.9182 xG (0.2682 por encima de la frontera ⇒ rama base sellada).
"""

import inspect

import pytest

RHO_BASE_CANONICO = -0.0500
RHO_TACTICA_CANONICA = -0.1200
CORTE_CANONICO = 2.6500

# Réplica hermética del registro fáctico mínimo del pipeline soberano (sin splits publicados).
_FIXTURE_CERRADO = {
    "home_team_stats": {"pj": 10, "gf": 9, "gc": 13, "xg": 0.95, "xga": 1.30},
    "away_team_stats": {"pj": 10, "gf": 7, "gc": 14, "xg": 0.85, "xga": 1.35},
}

_FIXTURE_ABIERTO = {
    "home_team_stats": {"pj": 10, "gf": 21, "gc": 11, "xg": 19.5},
    "away_team_stats": {"pj": 10, "gf": 18, "gc": 12, "xg": 16.8},
    "home_split_stats": {"pj": 10, "gf": 22, "gc": 10},
    "away_split_stats": {"pj": 10, "gf": 14, "gc": 14},
    "h2h_matches": [
        {"goles_local": 2, "goles_visita": 1, "dias_antiguedad": 120},
        {"goles_local": 1, "goles_visita": 1, "dias_antiguedad": 240},
        {"goles_local": 2, "goles_visita": 2, "dias_antiguedad": 380},
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════════════
# INVARIANTE 1 — LEY DE RESOLUCIÓN DINÁMICA DE ρ (FRONTERA Σλ = 2.6500)
# ═══════════════════════════════════════════════════════════════════════════════════════
def test_invariante_1_ley_de_resolucion_dinamica_de_rho():
    """[LN-QBE-040-C §P.1] ρ deja de ser constante: es función del régimen de anotación."""
    from src.core.poisson import (
        LAMBDA_SUMA_CORTE_TACTICO,
        RHO_BASE,
        RHO_TACTICA_DEFICIT,
        resolver_rho_dixon_coles,
    )

    # (a) Constantes selladas en docs/CONSTANTS.md §2 — cero margen creativo.
    assert RHO_BASE == RHO_BASE_CANONICO, "RHO_BASE alterado respecto al sello legislativo."
    assert RHO_TACTICA_DEFICIT == RHO_TACTICA_CANONICA, (
        "RHO_TACTICA_DEFICIT alterado respecto al sello legislativo."
    )
    assert LAMBDA_SUMA_CORTE_TACTICO == CORTE_CANONICO, (
        "LAMBDA_SUMA_CORTE_TACTICO alterado respecto al sello legislativo."
    )

    # (b) Régimen cerrado ⇒ ρ táctica (Σλ = 2.6000 ≤ 2.6500).
    assert resolver_rho_dixon_coles(1.65, 0.95) == RHO_TACTICA_DEFICIT
    # (c) Régimen abierto ⇒ ρ base sellada (Σλ = 2.9000 > 2.6500).
    assert resolver_rho_dixon_coles(1.80, 1.10) == RHO_BASE
    # (d) Frontera EXACTA ⊆ rama táctica (≤). El duplicado binario es exacto: 1.325 × 2 = 2.65.
    assert resolver_rho_dixon_coles(1.325, 1.325) == RHO_TACTICA_DEFICIT, (
        "La frontera Σλ = 2.6500 debe pertenecer a la rama táctica (desigualdad ≤)."
    )
    # (e) Un solo corte: 2.6502 xG ya pertenece a la rama base sellada.
    assert resolver_rho_dixon_coles(1.3251, 1.3251) == RHO_BASE

    # (f) Anti-invención: sobre la rejilla del dominio la ley SÓLO puede devolver esas dos ramas.
    for lambda_h in (0.05, 0.90, 1.325, 1.65, 2.65, 4.00):
        for lambda_a in (0.05, 0.90, 1.325, 1.65, 2.65, 4.00):
            valor = resolver_rho_dixon_coles(lambda_h, lambda_a)
            assert valor in (RHO_BASE, RHO_TACTICA_DEFICIT), (
                f"ρ fuera del catálogo sellado: resolver({lambda_h}, {lambda_a}) = {valor}"
            )
            esperado = (
                RHO_TACTICA_DEFICIT
                if lambda_h + lambda_a <= LAMBDA_SUMA_CORTE_TACTICO
                else RHO_BASE
            )
            assert valor == esperado, "Discrepancia entre la ley publicada y la resolutor."

    # (g) Determinismo estricto (cero estado interno, cero aleatoriedad).
    assert resolver_rho_dixon_coles(1.65, 0.95) == resolver_rho_dixon_coles(1.65, 0.95)


# ═══════════════════════════════════════════════════════════════════════════════════════
# INVARIANTE 2 — FACTOR τ(x, y) VERBATIM Y ADMISIBILIDAD §5.16.1 (INVARIANTE I13)
# ═══════════════════════════════════════════════════════════════════════════════════════
def test_invariante_2_factor_tau_verbatim_y_admisibilidad():
    """[LN-QBE-040-C §P.2] El factor τ y las cotas analíticas permanecen intactos."""
    from src.core.poisson import RHO_TACTICA_DEFICIT, _dixon_coles_tau

    lambda_h, lambda_a, rho = 1.30, 0.90, RHO_TACTICA_DEFICIT

    # (a) Los cuatro vértices corregidos, transcripción exacta de la Sección 5.3.1.
    assert _dixon_coles_tau(0, 0, lambda_h=lambda_h, lambda_a=lambda_a, rho=rho) == pytest.approx(
        1.0 - (lambda_h * lambda_a * rho), abs=1e-12
    )
    assert _dixon_coles_tau(0, 1, lambda_h=lambda_h, lambda_a=lambda_a, rho=rho) == pytest.approx(
        1.0 + (lambda_h * rho), abs=1e-12
    )
    assert _dixon_coles_tau(1, 0, lambda_h=lambda_h, lambda_a=lambda_a, rho=rho) == pytest.approx(
        1.0 + (lambda_a * rho), abs=1e-12
    )
    assert _dixon_coles_tau(1, 1, lambda_h=lambda_h, lambda_a=lambda_a, rho=rho) == pytest.approx(
        1.0 - rho, abs=1e-12
    )

    # (b) Fuera de los cuatro vértices τ ≡ 1.0000 (matriz de Poisson pura, cero sobrecorrección).
    for x, y in ((2, 0), (0, 2), (2, 2), (3, 1), (5, 5)):
        assert _dixon_coles_tau(x, y, lambda_h=lambda_h, lambda_a=lambda_a, rho=rho) == 1.0

    # (c) Escape hatch sellado: ρ = 0.0000 ⇒ τ ≡ 1.0000 en los cuatro vértices.
    for x, y in ((0, 0), (0, 1), (1, 0), (1, 1)):
        assert _dixon_coles_tau(x, y, lambda_h=lambda_h, lambda_a=lambda_a, rho=0.0) == 1.0

    # (d) Sentido físico del signo con λ_H = λ_A = 1.00 (aritmética binaria exacta):
    #     ρ negativo eleva los vértices de empate y deprime los de definición.
    tau_00 = _dixon_coles_tau(0, 0, lambda_h=1.0, lambda_a=1.0, rho=-0.12)
    tau_11 = _dixon_coles_tau(1, 1, lambda_h=1.0, lambda_a=1.0, rho=-0.12)
    tau_01 = _dixon_coles_tau(0, 1, lambda_h=1.0, lambda_a=1.0, rho=-0.12)
    assert tau_00 == pytest.approx(1.12, abs=1e-12) and tau_11 == pytest.approx(1.12, abs=1e-12)
    assert tau_01 == pytest.approx(0.88, abs=1e-12)
    assert tau_00 > 1.0 > tau_01 and tau_11 > 1.0

    # (e) Cotas analíticas §5.16.1 (Invariante I13, Teorema de No-Negatividad Estricta):
    #     ρ se acota en [-min(1/λ_H, 1/λ_A), min(1, 1/(λ_H·λ_A))] ⇒ τ(x, y) ≥ 0 SIEMPRE.
    assert _dixon_coles_tau(0, 0, lambda_h=1.0, lambda_a=1.0, rho=-5.0) == pytest.approx(2.0, abs=1e-12)
    assert _dixon_coles_tau(1, 1, lambda_h=1.0, lambda_a=1.0, rho=-5.0) == pytest.approx(2.0, abs=1e-12)
    assert _dixon_coles_tau(0, 1, lambda_h=1.0, lambda_a=1.0, rho=-5.0) == 0.0
    assert _dixon_coles_tau(0, 0, lambda_h=1.0, lambda_a=1.0, rho=+5.0) == 0.0
    assert _dixon_coles_tau(1, 1, lambda_h=1.0, lambda_a=1.0, rho=+5.0) == 0.0
    for rho_adverso in (-9.0, -1.0, -0.12, 0.0, 0.5, 9.0):
        for x, y in ((0, 0), (0, 1), (1, 0), (1, 1), (4, 4)):
            tau = _dixon_coles_tau(x, y, lambda_h=1.0, lambda_a=1.0, rho=rho_adverso)
            assert tau >= 0.0, f"τ({x},{y}) negativo con ρ={rho_adverso}: {tau}"


# ═══════════════════════════════════════════════════════════════════════════════════════
# INVARIANTE 3 — CABLEADO REAL (CERO CÓDIGO MUERTO) EN GENERADOR Y PIPELINE SOBERANO
# ═══════════════════════════════════════════════════════════════════════════════════════
def _masa_empate(matriz):
    """Masa total del vértice de empate (diagonal principal) de la matriz bivariada."""
    return sum(matriz[x][x] for x in range(len(matriz)))


def test_invariante_3_cableado_en_generador_y_pipeline():
    """[LN-QBE-040-C §P.1] La ley debe regir la física real, no ser capacidad dormida."""
    from src.core.distribution_dixon_coles import calcular_matriz_dixon_coles
    from src.core.poisson import (
        RHO_BASE,
        RHO_TACTICA_DEFICIT,
        PoissonBivariateEngine,
    )

    # (a) Guardián sintáctico: las funciones que computan la matriz bivariada invocan la ley.
    fuente_dc = inspect.getsource(calcular_matriz_dixon_coles)
    assert "resolver_rho_dixon_coles" in fuente_dc and "RHO_BASE" in fuente_dc, (
        "[LN-QBE-040-C] El generador Dixon-Coles no invoca la cláusula de resolución dinámica."
    )
    fuente_poisson = inspect.getsource(PoissonBivariateEngine.compute_modulations)
    assert "resolver_rho_dixon_coles" in fuente_poisson and "_dixon_coles_tau" in fuente_poisson, (
        "[LN-QBE-040-C] La matriz bivariada 6x6 de [LN-QBE-040] no aplica el factor τ dinámico."
    )

    # (b) Propagación al símplex Δ² desde el generador (régimen táctico: Σλ = 2.6000 xG).
    lambda_h, lambda_a = 1.65, 0.95
    assert lambda_h + lambda_a <= 2.6500, "Fixture fuera del régimen táctico: recalibrar el Juez."
    matriz_default = calcular_matriz_dixon_coles(lambda_h, lambda_a, k_max=6)
    matriz_tactica = calcular_matriz_dixon_coles(lambda_h, lambda_a, rho=RHO_TACTICA_DEFICIT, k_max=6)
    matriz_pura = calcular_matriz_dixon_coles(lambda_h, lambda_a, rho=0.0, k_max=6)
    matriz_base_sep = calcular_matriz_dixon_coles(lambda_h, lambda_a, rho=RHO_BASE, k_max=6)

    # Sin `rho` provisto ⇒ ley dinámica (idéntica al ρ táctica explícito).
    assert _masa_empate(matriz_default) == pytest.approx(_masa_empate(matriz_tactica), abs=1e-15)
    # El default sellado (-0.0500) NO se considera un ρ explícito distinto ⇒ misma física.
    assert _masa_empate(matriz_base_sep) == pytest.approx(_masa_empate(matriz_default), abs=1e-15)
    # Escape hatch: ρ = 0.0 verbatim ⇒ menos empate que la corrección táctica.
    assert _masa_empate(matriz_default) - _masa_empate(matriz_pura) >= 1e-3
    # Un ρ explícito distinto del default se transcribe verbatim (monotonía de |ρ|).
    masa_verbatim = _masa_empate(calcular_matriz_dixon_coles(lambda_h, lambda_a, rho=-0.0501))
    assert _masa_empate(matriz_pura) < masa_verbatim < _masa_empate(matriz_default)

    # (c) Pipeline soberano de producción: el default sellado `rho=-0.05` conmuta de régimen.
    from src.core.sovereign_pipeline import generar_distribucion_soberana

    auto_cerrado = generar_distribucion_soberana("TEST-RHO-CERRADO", _FIXTURE_CERRADO)
    tact_cerrado = generar_distribucion_soberana("TEST-RHO-CERRADO", _FIXTURE_CERRADO, rho=-0.12)
    puro_cerrado = generar_distribucion_soberana("TEST-RHO-CERRADO", _FIXTURE_CERRADO, rho=0.0)
    suma_cerrado = auto_cerrado.lambda_home + auto_cerrado.lambda_away
    assert suma_cerrado <= 2.6500, (
        f"Fixture de control fuera del régimen cerrado (Σλ={suma_cerrado:.4f}): recalibrar el Juez."
    )
    assert auto_cerrado.p_empate == pytest.approx(tact_cerrado.p_empate, abs=1e-12), (
        "[LN-QBE-040-C] El pipeline soberano no resolvió ρ táctica en partido cerrado."
    )
    assert auto_cerrado.p_empate - puro_cerrado.p_empate >= 1e-3, (
        "El pipeline no aplicó corrección Dixon-Coles alguna (matriz de Poisson pura)."
    )
    assert abs(auto_cerrado.p_local + auto_cerrado.p_empate + auto_cerrado.p_visitante - 1.0) <= 1e-4

    # (d) Conmutación real de régimen: en partido abierto NO se inyecta ρ táctica.
    auto_abierto = generar_distribucion_soberana("TEST-RHO-ABIERTO", _FIXTURE_ABIERTO)
    tact_abierto = generar_distribucion_soberana("TEST-RHO-ABIERTO", _FIXTURE_ABIERTO, rho=-0.12)
    suma_abierto = auto_abierto.lambda_home + auto_abierto.lambda_away
    assert suma_abierto > 2.6500, (
        f"Fixture de control fuera del régimen abierto (Σλ={suma_abierto:.4f}): recalibrar el Juez."
    )
    assert tact_abierto.p_empate - auto_abierto.p_empate >= 1e-3, (
        "[LN-QBE-040-C] El régimen abierto conmutó a ρ táctica: la frontera Σλ no está operando."
    )
    assert abs(auto_abierto.p_local + auto_abierto.p_empate + auto_abierto.p_visitante - 1.0) <= 1e-4


