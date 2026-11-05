# -*- coding: utf-8 -*-
"""
🏆 THE SHIELD — SHIN DE-VIG ENGINE SUITE
Juez Inmutable: [LN-QBE-151]
Base de Gobierno: docs/LOGIC.md §25 / docs/CONSTANTS.md §11
Autoridad: Américo García Guerrero (Director Humano)
Régimen: [DIRGEN-STRICT] — Inmutable, Cero Mocks en Producción.

CONTRATO DE INTERFAZ (materialización futura de [LN-QBE-151] en
`qbe_core/src/core/consensus.py`):

    from src.core.consensus import desmarginar_shin, ShinDevigResult

    resultado = desmarginar_shin(cuotas: Sequence[float]) -> ShinDevigResult

    ShinDevigResult (@dataclass(frozen=True)):
        p_local:         float
        p_empate:        float
        p_visitante:     float
        z_insider:       float   # parámetro de apostadores informados
        overround_bruto: float   # S = Σ (1 / O_k)

    InvalidOddsException(ValueError): cuota no finita, ≤ 1.0, negativa, nula,
    no numérica o terna incompleta. Prohibido el retorno silencioso.

Invariantes del contrato:
  1. Raíz de F(z) = Σ_k √(z² + 4(1−z)·π_k²/S) − 2 − z en z ∈ [0, min(π_k)],
     con ε = 1e-9 y ≤ 100 iteraciones.
  2. Σ p_k = 1 ± 1e-9 y p_k ∈ (0, 1).
  3. S ≤ 1 ⇒ z = 0 y p_k = π_k / S (no se resuelve la ecuación).
  4. Purga favorito-longshot verificada en (1.90, 3.40, 4.00):
     z ∈ (0.01, 0.05) y p_fav > π_fav / S.

Este Juez se entrega en RED: `desmarginar_shin` aún no existe en `src/`. El rojo
no se corrige relajando el Juez; se corrige materializando el motor en el Paso 3.
"""

import math

import pytest

try:
    from src.core.consensus import desmarginar_shin
except ImportError as exc:  # RED controlado: el Motor de Shin todavía no existe.
    desmarginar_shin = None  # type: ignore[assignment]
    _ERROR_IMPORTACION = exc
else:
    _ERROR_IMPORTACION = None

TOL_SIMPLEX = 1e-9


def _motor():
    """Devuelve el motor de Shin o falla ruidosamente si aún no fue materializado."""
    if desmarginar_shin is None:
        pytest.fail(
            "RED [LN-QBE-151]: falta materializar `desmarginar_shin` "
            "(`ShinDevigResult` e `InvalidOddsException`) en "
            "`qbe_core/src/core/consensus.py`, conforme a docs/LOGIC.md §25. "
            f"Error de importación: {_ERROR_IMPORTACION}"
        )
    return desmarginar_shin


def _implicitas(cuotas):
    """π_k = 1/O_k y sobremargen bruto S, réplica analítica independiente del motor."""
    pi = [1.0 / float(cuota) for cuota in cuotas]
    return pi, math.fsum(pi)


def test_asercion_1_replica_analitica_caso_simetrico():
    """
    [TRIPLE ASERCIÓN 1a — RÉPLICA ANALÍTICA]:
    Con cuotas perfectamente simétricas (3.0, 3.0, 3.0) el mercado no tiene
    margen (S = 1) ni sesgo: el des-margen DEBE devolver el centro del símplex
    (1/3, 1/3, 1/3) con z = 0 y overround bruto 1.0.
    """
    resultado = _motor()((3.0, 3.0, 3.0))

    assert resultado.p_local == pytest.approx(1.0 / 3.0, abs=TOL_SIMPLEX)
    assert resultado.p_empate == pytest.approx(1.0 / 3.0, abs=TOL_SIMPLEX)
    assert resultado.p_visitante == pytest.approx(1.0 / 3.0, abs=TOL_SIMPLEX)
    assert resultado.z_insider == pytest.approx(0.0, abs=TOL_SIMPLEX), (
        "🚨 Mercado simétrico sin margen no puede exhibir apostadores informados: "
        f"z = {resultado.z_insider!r}."
    )
    assert resultado.overround_bruto == pytest.approx(1.0, abs=TOL_SIMPLEX)


def test_asercion_1_replica_analitica_caso_asimetrico_purga_sesgo():
    """
    [TRIPLE ASERCIÓN 1b — RÉPLICA ANALÍTICA]:
    Con cuotas asimétricas reales (1.90, 3.40, 4.00) el motor DEBE resolver
    z ∈ (0.01, 0.05) y purgar el sesgo favorito-longshot: la probabilidad pura
    del favorito supera la probabilidad proporcional básica π_fav / S.
    """
    cuotas = (1.90, 3.40, 4.00)
    pi, sobremargen = _implicitas(cuotas)

    resultado = _motor()(cuotas)

    assert 0.01 < resultado.z_insider < 0.05, (
        "🚨 El parámetro de apostadores informados debe caer en (0.01, 0.05) "
        f"para (1.90, 3.40, 4.00); el motor devolvió z = {resultado.z_insider!r}."
    )
    p_fav = resultado.p_local
    proporcional_fav = pi[0] / sobremargen
    assert p_fav > proporcional_fav, (
        "🚨 SESGO NO PURGADO: el favorito conserva o pierde masa frente a la "
        f"normalización proporcional (p_fav={p_fav!r} ≤ π_fav/S={proporcional_fav!r})."
    )
    assert p_fav - proporcional_fav > 1e-4, (
        "🚨 La purga del sesgo debe ser material, no ruido numérico: "
        f"Δ = {p_fav - proporcional_fav!r}."
    )
    assert resultado.overround_bruto == pytest.approx(sobremargen, abs=1e-12)
    assert math.fsum(
        (resultado.p_local, resultado.p_empate, resultado.p_visitante)
    ) == pytest.approx(1.0, abs=TOL_SIMPLEX)


@pytest.mark.parametrize(
    "cuotas",
    [
        (1.90, 3.40, 4.00),
        (2.50, 3.10, 2.90),
        (1.50, 3.80, 6.00),
        (2.10, 3.30, 3.60),
        (1.75, 3.50, 5.25),
        (1.30, 5.50, 9.00),
    ],
)
def test_asercion_2_invarianza_estructural_del_simplex(cuotas):
    """
    [TRIPLE ASERCIÓN 2 — INVARIANZA ESTRUCTURAL]:
    Sobre combinaciones reales de cuotas, el resultado debe vivir estrictamente
    en el interior del 2-símplex (Σ p_k = 1 ± 1e-9, p_k ∈ (0, 1)) y el DTO debe
    ser inmutable (dataclass congelado): un valor de mercado no se reescribe.
    """
    resultado = _motor()(cuotas)
    p = (resultado.p_local, resultado.p_empate, resultado.p_visitante)

    assert all(math.isfinite(valor) for valor in p), (
        f"🚨 Probabilidad no finita en {cuotas}: {p!r}."
    )
    assert all(0.0 < valor < 1.0 for valor in p), (
        f"🚨 Probabilidad fuera del interior del símplex en {cuotas}: {p!r}."
    )
    assert math.fsum(p) == pytest.approx(1.0, abs=TOL_SIMPLEX), (
        f"🚨 Símplex no conservativo en {cuotas}: Σ p_k = {math.fsum(p)!r}."
    )

    pi, _ = _implicitas(cuotas)
    assert -TOL_SIMPLEX <= resultado.z_insider <= min(pi) + TOL_SIMPLEX, (
        "🚨 z fuera del intervalo legislado [0, min(π_k)]: "
        f"z = {resultado.z_insider!r}, min(π_k) = {min(pi)!r}."
    )

    with pytest.raises(AttributeError):
        resultado.p_local = 0.5  # type: ignore[misc]
    with pytest.raises(AttributeError):
        resultado.z_insider = 0.0  # type: ignore[misc]


@pytest.mark.parametrize(
    "cuotas",
    [
        pytest.param((1.00, 3.40, 4.00), id="cuota-igual-a-1"),
        pytest.param((0.95, 3.40, 4.00), id="cuota-menor-a-1"),
        pytest.param((-1.90, 3.40, 4.00), id="cuota-negativa"),
        pytest.param((1.90, 3.40), id="terna-incompleta"),
        pytest.param((1.90, 3.40, 4.00, 5.00), id="terna-sobredimensionada"),
        pytest.param((None, 3.40, 4.00), id="cuota-nula"),
        pytest.param(("1.90", 3.40, 4.00), id="cuota-cadena"),
        pytest.param((float("nan"), 3.40, 4.00), id="cuota-nan"),
        pytest.param((float("inf"), 3.40, 4.00), id="cuota-infinita"),
        pytest.param(None, id="entrada-nula"),
    ],
)
def test_asercion_3_anti_patron_fail_loud(cuotas):
    """
    [TRIPLE ASERCIÓN 3 — ANTI-PATRÓN / SAD PATH]:
    Toda entrada fuera de contrato DEBE lanzar una excepción tipada
    (`InvalidOddsException`, subclase de `ValueError`) con mensaje no vacío.
    Queda prohibido devolver ceros, un prior uniforme o un fallback silencioso.
    """
    motor = _motor()

    with pytest.raises(ValueError) as excinfo:
        motor(cuotas)

    assert str(excinfo.value).strip() != "", (
        f"🚨 Fail-Loud sin mensaje diagnóstico para cuotas {cuotas!r}."
    )
