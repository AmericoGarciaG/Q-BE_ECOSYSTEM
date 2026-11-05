# -*- coding: utf-8 -*-
"""
🏆 THE SHIELD — DERIVATIVE MARKETS PROJECTION SUITE
Juez Inmutable: [LN-QBE-152]
Base de Gobierno: docs/LOGIC.md §26
Autoridad: Américo García Guerrero (Director Humano)
Régimen: [DIRGEN-STRICT] — Inmutable, Cero Mocks en Producción.

CONTRATO DE INTERFAZ (materialización futura de [LN-QBE-152] en
`qbe_core/src/core/distribution_dixon_coles.py`):

    from src.core.distribution_dixon_coles import (
        proyectar_mercados_derivados, DerivativeMarketsProjection,
    )

    resultado = proyectar_mercados_derivados(
        matriz: Sequence[Sequence[float]],   # M*_xy, 7×7, Σ = 1
    ) -> DerivativeMarketsProjection

    DerivativeMarketsProjection (@dataclass(frozen=True)):
        p_under_25, p_over_25, p_btts_si, p_btts_no: float
        cuota_under_25, cuota_over_25,
        cuota_btts_si, cuota_btts_no: float          # O* = 1 / P

    MatrixIntegrityError(ValueError): dimensión ≠ 7×7, celda negativa o no
    finita, o suma ≠ 1 ± 1e-9. Prohibida la renormalización automática.

Invariantes del contrato:
  1. Under 2.5 = Σ_{x+y ≤ 2} M*_xy; Over 2.5 = 1 − Under 2.5.
  2. BTTS No = fila 0 ∪ columna 0 (M*_00 descontada una sola vez);
     BTTS Sí = 1 − BTTS No = Σ_{x ≥ 1, y ≥ 1} M*_xy.
  3. |Under + Over − 1| ≤ 1e-12 y |BTTS Sí + BTTS No − 1| ≤ 1e-12.
  4. El proyector consume la matriz sellada: no re-estima λ, ρ ni la matriz.

Este Juez se entrega en RED: `proyectar_mercados_derivados` aún no existe en
`src/`. El rojo no se corrige relajando el Juez; se corrige materializando el
Proyector en el Paso 3.
"""

import math

import pytest

try:
    from src.core.distribution_dixon_coles import (
        MatrixIntegrityError,
        proyectar_mercados_derivados,
    )
except ImportError as exc:  # RED controlado: el Proyector todavía no existe.
    proyectar_mercados_derivados = None  # type: ignore[assignment]
    MatrixIntegrityError = None  # type: ignore[assignment]
    _ERROR_IMPORTACION = exc
else:
    _ERROR_IMPORTACION = None

TOL_PARTICION = 1e-12
DIM = 7


def _motor():
    """Devuelve el Proyector o falla ruidosamente si aún no fue materializado."""
    if proyectar_mercados_derivados is None:
        pytest.fail(
            "RED [LN-QBE-152]: falta materializar `proyectar_mercados_derivados` "
            "(`DerivativeMarketsProjection` y `MatrixIntegrityError`) en "
            "`qbe_core/src/core/distribution_dixon_coles.py`, conforme a "
            f"docs/LOGIC.md §26. Error de importación: {_ERROR_IMPORTACION}"
        )
    return proyectar_mercados_derivados


def _excepcion():
    """Devuelve la excepción tipada del contrato o falla ruidosamente."""
    if MatrixIntegrityError is None:
        pytest.fail(
            "RED [LN-QBE-152]: falta materializar `MatrixIntegrityError` "
            f"(subclase de ValueError). Error de importación: {_ERROR_IMPORTACION}"
        )
    return MatrixIntegrityError


# ── Réplicas analíticas independientes (no llaman al Proyector) ──────────────


def _matriz_concentrada(celdas):
    """Construye un fixture 7×7 válido: masa concentrada en las celdas declaradas."""
    matriz = [[0.0 for _ in range(DIM)] for _ in range(DIM)]
    for (x, y), valor in celdas.items():
        matriz[x][y] = float(valor)
    total = math.fsum(math.fsum(fila) for fila in matriz)
    return [[valor / total for valor in fila] for fila in matriz]


def _under_directo(matriz):
    """Σ_{x+y ≤ 2} M*_xy, suma de región independiente del Proyector."""
    return math.fsum(
        matriz[x][y]
        for x in range(DIM)
        for y in range(DIM)
        if x + y <= 2
    )


def _btts_si_directo(matriz):
    """Σ_{x ≥ 1, y ≥ 1} M*_xy, suma de región independiente del Proyector."""
    return math.fsum(
        matriz[x][y]
        for x in range(1, DIM)
        for y in range(1, DIM)
    )


# ── Aserción 1: réplica analítica de regiones ────────────────────────────────


def test_asercion_1_replica_analitica_marcadores_sin_goles_visitante():
    """
    [TRIPLE ASERCIÓN 1a — RÉPLICA ANALÍTICA]:
    Con la matriz concentrada en {0-0, 1-0, 0-1} (ningún partido con 3+ goles y
    ningún bando anotando en ambos lados), Under 2.5 ≡ 1.0 y BTTS Sí ≡ 0.0.
    """
    matriz = _matriz_concentrada({(0, 0): 0.50, (1, 0): 0.30, (0, 1): 0.20})

    resultado = _motor()(matriz)

    assert resultado.p_under_25 == pytest.approx(1.0, abs=TOL_PARTICION), (
        f"🚨 Under 2.5 debe ser 1.0; el Proyector emitió {resultado.p_under_25!r}."
    )
    assert resultado.p_over_25 == pytest.approx(0.0, abs=TOL_PARTICION)
    assert resultado.p_btts_si == pytest.approx(0.0, abs=TOL_PARTICION), (
        f"🚨 BTTS Sí debe ser 0.0; el Proyector emitió {resultado.p_btts_si!r}."
    )
    assert resultado.p_btts_no == pytest.approx(1.0, abs=TOL_PARTICION)


def test_asercion_1_replica_analitica_marcadores_con_goles_en_ambos_bandos():
    """
    [TRIPLE ASERCIÓN 1b — RÉPLICA ANALÍTICA]:
    Con la matriz concentrada en {1-1, 2-1, 1-2} (todos los marcadores anotan en
    ambos bandos), BTTS Sí ≡ 1.0 y Under 2.5 ≡ 0.0.
    """
    matriz = _matriz_concentrada({(1, 1): 0.40, (2, 1): 0.30, (1, 2): 0.30})

    resultado = _motor()(matriz)

    assert resultado.p_btts_si == pytest.approx(1.0, abs=TOL_PARTICION), (
        f"🚨 BTTS Sí debe ser 1.0; el Proyector emitió {resultado.p_btts_si!r}."
    )
    assert resultado.p_btts_no == pytest.approx(0.0, abs=TOL_PARTICION)
    # Réplica analítica de Totales: 1-1 suma 2 goles ⇒ Under 2.5; 2-1 y 1-2 suman 3 ⇒ Over.
    assert resultado.p_under_25 == pytest.approx(0.40, abs=TOL_PARTICION), (
        f"🚨 Under 2.5 debe ser 0.40 (el 1-1 tiene 2 goles); emitió {resultado.p_under_25!r}."
    )
    assert resultado.p_over_25 == pytest.approx(0.60, abs=TOL_PARTICION)


# ── Aserción 2: invarianza de partición exacta sobre matrices reales ─────────


@pytest.mark.parametrize(
    "lambda_h, lambda_a",
    [(1.80, 1.20), (0.90, 0.80), (2.60, 2.10), (1.10, 1.40)],
)
def test_asercion_2_invarianza_de_particion_exacta(lambda_h, lambda_a):
    """
    [TRIPLE ASERCIÓN 2 — INVARIANZA ESTRUCTURAL]:
    Sobre matrices reales de Dixon-Coles, cada mercado debe ser una partición
    exacta (|Under + Over − 1| ≤ 1e-12, |BTTS Sí + BTTS No − 1| ≤ 1e-12), cada
    probabilidad debe coincidir con la réplica analítica de su región y la cuota
    justa debe ser exactamente O* = 1/P.
    """
    from src.core.distribution_dixon_coles import calcular_matriz_dixon_coles

    matriz = calcular_matriz_dixon_coles(lambda_h=lambda_h, lambda_a=lambda_a, k_max=6)

    resultado = _motor()(matriz)

    assert abs(resultado.p_under_25 + resultado.p_over_25 - 1.0) <= TOL_PARTICION, (
        "🚨 PARTICIPACIÓN ROTA: Under + Over ≠ 1 "
        f"({resultado.p_under_25!r} + {resultado.p_over_25!r})."
    )
    assert abs(resultado.p_btts_si + resultado.p_btts_no - 1.0) <= TOL_PARTICION, (
        "🚨 PARTICIPACIÓN ROTA: BTTS Sí + BTTS No ≠ 1 "
        f"({resultado.p_btts_si!r} + {resultado.p_btts_no!r})."
    )
    assert resultado.p_under_25 == pytest.approx(_under_directo(matriz), abs=TOL_PARTICION)
    assert resultado.p_btts_si == pytest.approx(_btts_si_directo(matriz), abs=TOL_PARTICION)
    assert all(
        0.0 <= valor <= 1.0
        for valor in (
            resultado.p_under_25,
            resultado.p_over_25,
            resultado.p_btts_si,
            resultado.p_btts_no,
        )
    ), "🚨 Probabilidad fuera de [0, 1] en la proyección de mercados derivados."
    assert resultado.p_under_25 * resultado.cuota_under_25 == pytest.approx(
        1.0, abs=TOL_PARTICION
    ), "🚨 La cuota justa de Under 2.5 no es el inverso exacto de su probabilidad."
    assert resultado.p_btts_si * resultado.cuota_btts_si == pytest.approx(
        1.0, abs=TOL_PARTICION
    ), "🚨 La cuota justa de BTTS Sí no es el inverso exacto de su probabilidad."

    with pytest.raises(AttributeError):
        resultado.p_under_25 = 0.5  # type: ignore[misc]


# ── Aserción 3: anti-patrón fail-loud ───────────────────────────────────────


def _matriz_uniforme(factor=1.0):
    return [[factor / (DIM * DIM) for _ in range(DIM)] for _ in range(DIM)]


def _matriz_negativa():
    matriz = _matriz_uniforme()
    matriz[0][0] = -0.02
    matriz[0][1] += 0.02 + (1.0 / (DIM * DIM))
    return matriz


def _matriz_no_finita():
    matriz = _matriz_uniforme()
    matriz[3][3] = float("nan")
    return matriz


@pytest.mark.parametrize(
    "matriz",
    [
        pytest.param([[0.0] * DIM for _ in range(DIM - 1)], id="6x7-filas"),
        pytest.param([[0.0] * (DIM - 1) for _ in range(DIM)], id="7x6-columnas"),
        pytest.param([[0.0] * (DIM + 1) for _ in range(DIM + 1)], id="8x8"),
        pytest.param(_matriz_negativa(), id="celda-negativa"),
        pytest.param(_matriz_no_finita(), id="celda-nan"),
        pytest.param(_matriz_uniforme(factor=0.98), id="suma-0.98"),
        pytest.param(_matriz_uniforme(factor=1.02), id="suma-1.02"),
    ],
)
def test_asercion_3_anti_patron_fail_loud(matriz):
    """
    [TRIPLE ASERCIÓN 3 — ANTI-PATRÓN / SAD PATH]:
    Dimensión distinta de 7×7, probabilidades negativas, celdas no finitas o
    sumas distintas de 1.0 DEBEN lanzar `MatrixIntegrityError` (subclase de
    `ValueError`). Queda prohibida la renormalización automática de matrices
    corruptas y cualquier retorno silencioso.
    """
    proyector = _motor()
    excepcion = _excepcion()

    with pytest.raises(excepcion) as excinfo:
        proyector(matriz)

    assert isinstance(excinfo.value, ValueError), (
        "🚨 `MatrixIntegrityError` debe heredar de ValueError para que la aduana "
        f"sea tipada; se capturó {type(excinfo.value)!r}."
    )
    assert str(excinfo.value).strip() != "", (
        "🚨 Fail-Loud sin mensaje diagnóstico para una matriz corrupta."
    )
