# -*- coding: utf-8 -*-
"""🏆 THE SHIELD — JUEZ INMUTABLE DEL MOTOR DE CALIBRACIÓN Y PERTURBACIÓN.

Nodo: `[LN-QBE-147]` Motor de Calibración y Perturbación de Variables Causales.
Base de Gobierno: `docs/LOGIC.md` §20.

El Juez certifica: (1) la fórmula del Brier, (2) que la perturbación **mejora**
el Brier en un lote de prueba, (3) que respeta los límites físicos, (4) que es
determinista y (5) que nunca empeora el punto de partida.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

import pytest

from src.core.sovereign.calibrar_perturbacion import (
    CalibracionError,
    FACTOR_MAX,
    FACTOR_MIN,
    LIMITES,
    aplicar_factores,
    brier_multiclase,
    calibrar,
    distribucion_1x2,
    lambdas_del_vector,
)

RAIZ = __import__("pathlib").Path(__file__).resolve().parents[2]


def _vector(v07_local: float, v07_visita: float, v13_local: float, v13_visita: float) -> Dict[str, Dict[str, Optional[float]]]:
    vector: Dict[str, Dict[str, Optional[float]]] = {
        "V05": {"local": 5.0, "visita": 5.0},
        "V07": {"local": v07_local, "visita": v07_visita},
        "V13": {"local": v13_local, "visita": v13_visita},
        "V21": {"local": 0.0, "visita": 0.0},
        "V22": {"local": 0.0, "visita": 0.0},
        "V23": {"local": 4.0, "visita": 4.0},
        "V24": {"local": 0.0, "visita": 0.0},
        "V25": {"local": 2.0, "visita": 2.0},
    }
    return vector


def _lote_sin_goles(partidos: int = 12) -> List[Dict[str, Any]]:
    return [
        {
            "match_id": f"m{indice:02d}",
            "vector": _vector(5.0, 5.0, 5.0, 5.0),
            "goles_local": 0,
            "goles_visita": 0,
        }
        for indice in range(partidos)
    ]


# ── Aritmética del acta ───────────────────────────────────────────────────────────────────
def test_brier_multiclase_formula_exacta() -> None:
    """[INV 1] Brier = suma de cuadrados sobre los tres desenlaces."""
    # Victoria local observada, pronóstico (0.5, 0.3, 0.2).
    assert brier_multiclase(0.5, 0.3, 0.2, 2, 0) == pytest.approx(0.25 + 0.09 + 0.04)

    # Empate observado, pronóstico perfecto ⇒ 0.
    assert brier_multiclase(0.0, 1.0, 0.0, 1, 1) == pytest.approx(0.0)

    # Derrota local = victoria visitante.
    assert brier_multiclase(1.0, 0.0, 0.0, 0, 3) == pytest.approx(1.0 + 0.0 + 1.0)


def test_distribucion_colapsa_al_simplex() -> None:
    """[INV 2] La matriz Dixon-Coles canónica colapsa a probabilidades que suman 1."""
    p_local, p_empate, p_visitante = distribucion_1x2(1.6, 1.1)
    assert p_local + p_empate + p_visitante == pytest.approx(1.0, abs=1e-9)
    assert min(p_local, p_empate, p_visitante) >= 0.0


# ── Calibración ────────────────────────────────────────────────────────────────────────────
def test_calibracion_mejora_el_brier_en_un_lote_de_prueba() -> None:
    """[INV 3] En un lote donde el puente sobreestima goles, la perturbación mejora."""
    acta = calibrar(_lote_sin_goles(), {"V07": 5.0, "V13": 5.0}, 2.0, pasos=6)

    assert acta["brier_optimizado"] < acta["brier_base"]
    assert acta["delta"] < 0.0
    assert acta["mejora_relativa"] > 0.0
    assert acta["pasos_ejecutados"] > 0


def test_calibracion_nunca_empeora_el_punto_de_partida() -> None:
    """[INV 4] El optimizador sólo acepta movimientos que reducen el Brier."""
    acta = calibrar(_lote_sin_goles(8), {"V07": 5.0, "V13": 5.0}, 2.0, pasos=10)

    assert acta["brier_optimizado"] <= acta["brier_base"]
    previo = acta["brier_base"]
    for movimiento in acta["movimientos"]:
        assert movimiento["brier_nuevo"] < previo
        assert movimiento["delta"] < 0.0
        previo = movimiento["brier_nuevo"]


def test_perturbaciones_respetan_los_limites_fisicos() -> None:
    """[INV 5] Factores extremos jamás producen valores negativos ni imposibles."""
    acta = calibrar(
        _lote_sin_goles(6), {"V07": 5.0, "V13": 5.0}, 2.0,
        pasos=8, factores=(0.1, 10.0),
    )
    for clave, factor in acta["factores_finales"].items():
        assert FACTOR_MIN - 1e-12 <= factor <= FACTOR_MAX + 1e-12, clave

    vector = _vector(5.0, 5.0, 5.0, 5.0)
    perturbado = aplicar_factores(vector, {("V07", "local"): 0.1, ("V13", "visita"): 10.0})
    for variable, minimo_maximo in LIMITES.items():
        for lado in ("local", "visita"):
            valor = perturbado[variable][lado]
            if valor is None:
                continue
            assert 0.0 <= valor <= minimo_maximo[1], (variable, lado, valor)

    lam_local, lam_visita = lambdas_del_vector(perturbado, {"V07": 5.0, "V13": 5.0}, 2.0)
    assert lam_local > 0.0 and lam_visita > 0.0


def test_calibracion_es_determinista() -> None:
    """[INV 6] Mismas entradas ⇒ mismo acta, bit a bit."""
    primera = calibrar(_lote_sin_goles(10), {"V07": 5.0, "V13": 5.0}, 2.0, pasos=6)
    segunda = calibrar(_lote_sin_goles(10), {"V07": 5.0, "V13": 5.0}, 2.0, pasos=6)
    assert primera == segunda


def test_acta_declara_movimientos_e_impacto() -> None:
    """[INV 7] El acta trae la secuencia y el ranking de impacto (top3)."""
    acta = calibrar(_lote_sin_goles(10), {"V07": 5.0, "V13": 5.0}, 2.0, pasos=6)

    assert set(acta) >= {
        "brier_base", "brier_optimizado", "delta", "movimientos",
        "impacto_por_variable", "top3", "factores_finales",
    }
    assert len(acta["movimientos"]) == acta["pasos_ejecutados"]
    assert len(acta["top3"]) <= 3
    for movimiento in acta["movimientos"]:
        assert movimiento["variable"] in LIMITES
        assert movimiento["lado"] in ("local", "visita")
        assert movimiento["factor"] > 0.0
    ordenado = sorted(fila["delta_total"] for fila in acta["impacto_por_variable"])
    assert ordenado == [fila["delta_total"] for fila in acta["impacto_por_variable"]]


# ── Sad Paths ──────────────────────────────────────────────────────────────────────────────
def test_sad_path_lote_vacio() -> None:
    """[SAD 1] Sin partidos no hay acta: excepción de dominio."""
    with pytest.raises(CalibracionError):
        calibrar([], {"V07": 5.0, "V13": 5.0}, 2.0)


@pytest.mark.parametrize(
    "marcador",
    [(-1, 0), (0, -2), (1.5, 0), ("2", 0)],
)
def test_sad_path_marcador_invalido(marcador: tuple) -> None:
    """[SAD 2] Marcador no entero o negativo: excepción de dominio."""
    lote = [{"vector": _vector(5.0, 5.0, 5.0, 5.0), "goles_local": marcador[0], "goles_visita": marcador[1]}]
    with pytest.raises(CalibracionError):
        calibrar(lote, {"V07": 5.0, "V13": 5.0}, 2.0)


def test_sad_path_mu_liga_no_positivo() -> None:
    """[SAD 3] `MU_LIGA` no positivo: excepción de dominio."""
    with pytest.raises(CalibracionError):
        lambdas_del_vector(_vector(5.0, 5.0, 5.0, 5.0), {"V07": 5.0, "V13": 5.0}, 0.0)


def test_sad_path_vector_sin_v07() -> None:
    """[SAD 4] Vector sin `V07`: no se puede calibrar."""
    with pytest.raises(CalibracionError):
        lambdas_del_vector({"V13": {"local": 3.0, "visita": 3.0}}, {"V07": 5.0, "V13": 5.0}, 1.4)


# ── Gobierno ──────────────────────────────────────────────────────────────────────────────
def test_ley_147_anclada_en_la_base_de_gobierno() -> None:
    """[INV 8] El nodo existe en LOGIC.md y en ID_REGISTRY.md."""
    logica = (RAIZ / "docs" / "LOGIC.md").read_text(encoding="utf-8")
    registro = (RAIZ / "docs" / "ID_REGISTRY.md").read_text(encoding="utf-8")

    assert "[LN-QBE-147]" in logica
    assert "[LN-QBE-147]" in registro
