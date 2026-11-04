# -*- coding: utf-8 -*-
"""🏆 THE SHIELD — `[LN-QBE-148]` AGREGACIÓN DE BRIER POR JORNADA.

Invariante inmutable:
* Un partido sin evidencia (``brier=None``) se excluye del promedio.
* El Brier de la jornada es la media aritmética exacta de los partidos válidos.
* Si no queda ningún partido válido, el Brier y el Alpha son ``None``.
* Cero imputaciones: el set de 3 partidos no promedia 1/6.
"""

from __future__ import annotations

import pytest

from src.observatory.sabiduria_masas import (
    alpha_pct,
    brier_jornada,
    brier_promedio_partidos,
)


def test_tres_partidos_perfecto_parcial_sin_datos() -> None:
    """Perfecto 0.0 + parcial 0.5 + sin datos None ⇒ media exacta 0.25."""
    partidos = [
        {"id": "perfecto", "brier": 0.0},
        {"id": "parcial", "brier": 0.5},
        {"id": "sin_datos", "brier": None},
    ]
    assert brier_jornada(partidos) == pytest.approx(0.25)
    assert brier_promedio_partidos([0.0, 0.5, None]) == pytest.approx(0.25)
    # La imputación de cero habría producido 0.1666...; el Juez la prohíbe.
    assert brier_jornada(partidos) != pytest.approx(1.0 / 6.0)


def test_muestra_vacia_no_imputa_cero_y_alpha_es_none() -> None:
    assert brier_jornada([{"brier": None}, {"brier": None}]) is None
    assert alpha_pct(None, 0.2159) is None
    assert alpha_pct(0.6434, None) is None
