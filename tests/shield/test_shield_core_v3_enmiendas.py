# -*- coding: utf-8 -*-
"""
🏆 THE SHIELD — ENMIENDAS E-50.4 / E-50.5 / E-50.6 (FASE 4)
Juez Inmutable: [LN-QBE-039] §7.6 · [LN-QBE-040-C] · [E-50.4/5/6]
Régimen: [DIRGEN-STRICT] — Inmutable, Cero Mocks.
Expediente: SPRINT-50-REINGENIERIA-INDUSTRIAL-QBE-CORE (Fase 4)
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
for _ruta in (RAIZ, RAIZ / "qbe_core"):
    if str(_ruta) not in sys.path:
        sys.path.insert(0, str(_ruta))

from src.core.distribution_dixon_coles import (  # noqa: E402
    VENTANA_RHO_SUAVE,
    resolver_rho_suave,
)
from src.core.sovereign.orthogonal_factor_engine import (  # noqa: E402
    PRIORIDAD_GS,
    orden_gs,
    resolver_factores_latentes_gsl3d_v2,
)

MEDIAS = {"V01": 1.0, "V07": 1.5, "V13": 1.2, "V14": 0.8, "V08": 0.6}


def _serie(n: int, base: float, paso: float, modulo: int = 3):
    return [
        {
            "V01": base + float(i % modulo),
            "V07": base + paso * i,
            "V08": base + 0.11 * i,
            "V13": 1.6 - 0.05 * i,
            "V14": 0.5 + float((i * 2) % 4),
        }
        for i in range(n)
    ]


# ── 1. Jerarquía fija [E-50.4 §T1] ──────────────────────────────────────────────────────────
def test_jerarquia_definicion_antes_que_volumen() -> None:
    """xG → big chances → SoT → volumen: una de volumen NUNCA se proyecta antes."""
    orden = orden_gs(["V01", "V03", "V07", "V08", "V06"])
    assert orden == ("V06", "V08", "V07", "V01", "V03"), f"Orden no legislado: {orden}."
    assert PRIORIDAD_GS["V06"] < PRIORIDAD_GS["V08"] < PRIORIDAD_GS["V07"] < PRIORIDAD_GS["V01"]


def test_jerarquia_es_determinista_e_independiente_del_orden_de_entrada() -> None:
    entrada = ["V24", "V06", "V21", "V08", "V01"]
    assert orden_gs(entrada) == orden_gs(list(reversed(entrada)))


# ── 2. Peso β PRE-Gram-Schmidt [E-50.4 §T2] ────────────────────────────────────────────────
def test_peso_cero_apaga_la_variable_y_no_altera_el_factor() -> None:
    filas = _serie(12, 1.0, 0.2)
    vector = {clave: sum(fila[clave] for fila in filas) / len(filas) for clave in filas[0]}

    con_beta = resolver_factores_latentes_gsl3d_v2(filas, vector, MEDIAS, pesos={"V01": 0.0})
    sin_columna = resolver_factores_latentes_gsl3d_v2(
        [{k: v for k, v in fila.items() if k != "V01"} for fila in filas],
        {k: v for k, v in vector.items() if k != "V01"},
        MEDIAS,
    )

    assert con_beta.estados["V01"] == "APAGADA_L1", (
        f"β = 0 debe declarar APAGADA_L1; estado={con_beta.estados.get('V01')!r}."
    )
    assert con_beta.contribuciones["V01"] == 0.0
    assert con_beta.A_star == pytest.approx(sin_columna.A_star, abs=1e-12), (
        "Apagar por β debe ser idéntico a no proyectar la variable."
    )


def test_peso_negativo_es_rechazado() -> None:
    filas = _serie(5, 1.0, 0.2)
    vector = {clave: 1.0 for clave in filas[0]}
    with pytest.raises(ValueError):
        resolver_factores_latentes_gsl3d_v2(filas, vector, MEDIAS, pesos={"V01": -0.5})


# ── 3. Transición suave de ρ [E-50.5 §T3] ──────────────────────────────────────────────────
def test_rho_conserva_los_extremos_sellados() -> None:
    assert VENTANA_RHO_SUAVE == pytest.approx(0.10)
    assert resolver_rho_suave(2.00, 0.00) == -0.12
    assert resolver_rho_suave(2.55, 0.00) == -0.12
    assert resolver_rho_suave(2.75, 0.00) == -0.05
    assert resolver_rho_suave(3.20, 0.00) == -0.05


def test_rho_es_continuo_en_la_frontera() -> None:
    """El escalón (salto 0.07) queda erradicado: el salto residual es < 1e-3."""
    salto = abs(resolver_rho_suave(2.6500001, 0.0) - resolver_rho_suave(2.6499999, 0.0))
    assert salto < 1e-3, f"Discontinuidad residual {salto:.6f} en Σλ = 2.65."
    anterior = resolver_rho_suave(2.40, 0.0)
    for paso in range(1, 40):
        actual = resolver_rho_suave(2.40 + 0.02 * paso, 0.0)
        assert actual >= anterior - 1e-12, "ρ debe ser monótono creciente en Σλ."
        anterior = actual
