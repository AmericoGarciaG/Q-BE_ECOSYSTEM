# -*- coding: utf-8 -*-
"""
🏆 THE SHIELD — IMMUNE SYSTEM SEQUENCE SUITE (MUNDO 1 → MUNDO 2)
Juez Inmutable: [LN-QBE-060-B] / [LN-QBE-060-C] (enmienda doctrinal §27)
Base de Gobierno: docs/LOGIC.md §27
Autoridad: Américo García Guerrero (Director Humano)
Régimen: [DIRGEN-STRICT] — Inmutable, Cero Mocks en Producción.

CONTRATO DE INTERFAZ (materialización futura de §27 en `qbe_core/src/core/triage.py`):

    from src.core.triage import triaje_financiero_mundo2

    resultado = triaje_financiero_mundo2(
        match_id: str,
        distribucion_soberana: Mapping[str, float],      # P'
        consenso_mercado: Mapping[str, float],           # P_consenso / q^mkt
        cuotas: Mapping[str, float],                     # L / E / V
        vector: Mapping[str, float],                     # variables causales
        percentiles: Mapping[str, Mapping[str, float]],  # p25 / p75 / p90
    ) -> Dict[str, Any]

    Claves obligatorias en veto:
        codigo = "QBE-00" · paso_0 = True · arquetipo_veto ∈
        {"SOBREASEDIO_DEFENSIVO", "INEFICACIA_OFENSIVA"} · motivo_codigo ·
        capital_mxn = 0.0 · cuotas_evaluadas = False · boletos = [] ·
        traza = {"p_simplex": P', "p_consenso": P_consenso, ...}

Invariantes del contrato:
  1. Nivel 1 (Mundo 1) es ciego a cuotas y dinero: P' se emite completo —tres
     vértices, Σ = 1 ± 1e-9— aunque el Sistema Inmune vaya a disparar después.
  2. El Paso 0 del Mundo 2 evalúa el Sistema Inmune antes de leer una sola cuota.
  3. Un veto inmune colapsa a QBE-00 con $0.00 MXN y cero boletos, preservando
     AMBAS distribuciones en la traza forense (no se amputa ninguna).

Este Juez se entrega en RED: `triaje_financiero_mundo2` aún no existe en `src/`.
La Aserción 1 certifica el comportamiento vigente de Mundo 1 (no amputación);
la Aserción 2 es la deuda legislativa que el Paso 3 debe materializar.
"""

import math

import pytest

from src.core.sovereign_pipeline import generar_distribucion_soberana
from src.core.triage import veto_inmunidad_fiduciaria

try:
    from src.core.triage import triaje_financiero_mundo2
except ImportError as exc:  # RED controlado: el orquestador de Mundo 2 no existe.
    triaje_financiero_mundo2 = None  # type: ignore[assignment]
    _ERROR_IMPORTACION = exc
else:
    _ERROR_IMPORTACION = None

TOL_SIMPLEX = 1e-9

# Fixture fáctico sellado (8 PJ por club, xG/xGA acumulados de temporada).
DATOS_FACTICOS = {
    "home_team_stats": {"pj": 8, "gf": 10, "gc": 10, "xg": 11.68, "xga": 10.32},
    "away_team_stats": {"pj": 8, "gf": 7, "gc": 12, "xg": 8.56, "xga": 12.16},
}

# Los dos arquetipos del Sistema Inmune Fiduciario (docs/LOGIC.md §27.3).
CASOS_INMUNES = [
    pytest.param(
        "SOBREASEDIO_DEFENSIVO",
        {"V13": 7.8, "V31": 0.9},
        {"p25": {"V31": 1.2}, "p75": {}, "p90": {"V13": 7.0}},
        id="sobreasedio-defensivo",
    ),
    pytest.param(
        "INEFICACIA_OFENSIVA",
        {"V06": 1.8, "V09": 3.4, "V25": 2.2},
        {"p25": {}, "p75": {"V06": 1.5, "V25": 2.0}, "p90": {"V09": 3.0}},
        id="ineficacia-ofensiva",
    ),
]


def _orquestador():
    """Devuelve el orquestador de Mundo 2 o falla ruidosamente si no existe."""
    if triaje_financiero_mundo2 is None:
        pytest.fail(
            "RED [LN-QBE-060-B] §27: falta materializar `triaje_financiero_mundo2` "
            "en `qbe_core/src/core/triage.py` (Paso 0 del Sistema Inmune antes de "
            f"leer cuotas). Error de importación: {_ERROR_IMPORTACION}"
        )
    return triaje_financiero_mundo2


class CuotasEspia(dict):
    """Mapping centinela: cuenta cada acceso por clave que el motor intente.

    Copiar el mapping (`dict(cuotas)`) no dispara el contador; leer una cuota
    concreta (`cuotas["L"]`, `cuotas.get("E")`) sí. Es la prueba de que el
    Paso 0 no evaluó cuotas.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.accesos = 0

    def __getitem__(self, clave):
        self.accesos += 1
        return super().__getitem__(clave)

    def get(self, clave, default=None):
        self.accesos += 1
        return super().get(clave, default)


@pytest.mark.parametrize("arquetipo, vector, percentiles", CASOS_INMUNES)
def test_asercion_1_mundo_1_no_amputa_el_simplex(arquetipo, vector, percentiles):
    """
    [TRIPLE ASERCIÓN 1 — NO-AMPUTACIÓN EN MUNDO 1]:
    Aunque el vector de variables cumpla las condiciones de SOBREASEDIO_DEFENSIVO
    o INEFICACIA_OFENSIVA, `sovereign_pipeline.py` DEBE emitir el símplex P'
    completo (tres vértices positivos, Σ = 1 ± 1e-9) con S(I) = 1. El veto es una
    decisión del Mundo 2: no puede mutilar la física del Mundo 1.
    """
    veto = veto_inmunidad_fiduciaria(
        vector, percentiles["p25"], percentiles["p75"], percentiles["p90"]
    )
    assert veto is not None, (
        f"🚨 El fixture debe disparar el Sistema Inmune ({arquetipo}); no disparó."
    )
    assert veto["arquetipo_veto"] == arquetipo
    assert veto["codigo"] == "QBE-00"

    salida = generar_distribucion_soberana("LIGAMX-FASE9-M1", DATOS_FACTICOS)
    p = (salida.p_local, salida.p_empate, salida.p_visitante)

    assert salida.es_operable is True, (
        "🚨 Mundo 1 amputó el partido por un veto que sólo compete al Mundo 2."
    )
    assert salida.audit_trace.suficiencia_S_I == 1, (
        "🚨 El símplex se emitió con S(I) = 0: la evidencia fáctica fue amputada."
    )
    assert all(math.isfinite(valor) and valor > 0.0 for valor in p), (
        f"🚨 Vértice de P' no positivo o no finito: {p!r}."
    )
    assert math.fsum(p) == pytest.approx(1.0, abs=TOL_SIMPLEX), (
        f"🚨 Símplex P' no conservativo: Σ = {math.fsum(p)!r}."
    )

    traza = salida.audit_trace.distribucion_simplex
    assert traza["p_1"] == salida.p_local
    assert traza["p_X"] == salida.p_empate
    assert traza["p_2"] == salida.p_visitante, (
        "🚨 La traza forense no preserva los tres vértices de P'."
    )


@pytest.mark.parametrize("arquetipo, vector, percentiles", CASOS_INMUNES)
def test_asercion_2_paso_0_veto_inmune_antes_de_cuotas(arquetipo, vector, percentiles):
    """
    [TRIPLE ASERCIÓN 2 — VETO EN PASO 0 DE MUNDO 2]:
    Al invocar el triaje financiero, el partido debe ser interceptado en el
    Paso 0: código QBE-00, motivo tipado, capital $0.00 MXN y cero boletos,
    SIN leer una sola cuota (el centinela no registra accesos) y preservando
    ambas distribuciones en la traza.
    """
    orquestador = _orquestador()

    p_simplex = {"p_local": 0.5123, "p_empate": 0.2411, "p_visitante": 0.2466}
    p_consenso = {"p_local": 0.4800, "p_empate": 0.2600, "p_visitante": 0.2600}
    cuotas = CuotasEspia({"L": 0.0, "E": -1.0, "V": "corrupta"})

    resultado = orquestador(
        match_id="LIGAMX-FASE9-VETO",
        distribucion_soberana=p_simplex,
        consenso_mercado=p_consenso,
        cuotas=cuotas,
        vector=vector,
        percentiles=percentiles,
    )

    assert resultado["codigo"] == "QBE-00", (
        f"🚨 El Sistema Inmune no colapsó a QBE-00; emitió {resultado.get('codigo')!r}."
    )
    assert resultado["paso_0"] is True, (
        "🚨 El veredicto no se declara como Paso 0 del Mundo 2."
    )
    assert resultado["arquetipo_veto"] == arquetipo
    assert resultado["motivo_codigo"] == arquetipo
    assert resultado["capital_mxn"] == 0.0, (
        f"🚨 Un veto no puede comprometer capital: {resultado.get('capital_mxn')!r}."
    )
    assert resultado["boletos"] == [], (
        f"🚨 Un veto no puede asignar boletos: {resultado.get('boletos')!r}."
    )
    assert resultado["cuotas_evaluadas"] is False, (
        "🚨 La aduana de cuotas se ejecutó antes del Paso 0."
    )
    assert cuotas.accesos == 0, (
        "🚨 El triaje leyó cuotas antes de resolver el Sistema Inmune: "
        f"{cuotas.accesos} accesos."
    )
    assert resultado["traza"]["p_simplex"] == p_simplex, (
        "🚨 La traza no preserva P' (Mundo 1) tras el veto."
    )
    assert resultado["traza"]["p_consenso"] == p_consenso, (
        "🚨 La traza no preserva P_consenso (Mundo 1) tras el veto."
    )
