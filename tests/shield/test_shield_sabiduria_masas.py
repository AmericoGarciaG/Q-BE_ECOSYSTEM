# -*- coding: utf-8 -*-
"""🏆 THE SHIELD — `[DES-QBE-076]` TABLA DE SABIDURÍA DE LAS MASAS.

Certifica el contrato de ordenamiento del Visor de Calibración:

* el **Consenso Ponderado** ocupa siempre la fila superior y queda destacado;
* las fuentes restantes se ordenan por `Brier Score` ascendente;
* una fuente sin Brier (`None`) cae al final, nunca se imputa;
* los pesos del consenso son Brier-inversos, suman 1.0 y respetan el piso 0.05;
* `Alpha (%)` compara el Brier de la fuente contra Q-BE.
"""

from __future__ import annotations

import pytest

from src.observatory.sabiduria_masas import (
    PESO_MIN,
    alpha_pct,
    construir_tabla_por_jornada,
    construir_tabla_sabiduria,
    pesos_desde_brier,
)


def _fuente(nombre: str, brier=None, alpha=None, peso=None) -> dict:
    return {"fuente": nombre, "brier": brier, "alpha_pct": alpha, "peso": peso}


def test_consenso_primero_y_resto_por_brier_ascendente() -> None:
    """[DES-QBE-076] Consenso fijo arriba; Q-BE y casinos por Brier ascendente."""
    tabla = construir_tabla_sabiduria(
        [
            _fuente("Casino B", 0.70, -6.06, 0.20),
            _fuente("Q-BE", 0.66, 0.0, None),
            _fuente("Consenso", 0.62, 6.06, 1.0),
            _fuente("Casino A", 0.64, 3.03, 0.30),
        ]
    )
    assert [fila["fuente"] for fila in tabla] == [
        "Consenso",
        "Casino A",
        "Q-BE",
        "Casino B",
    ]
    assert tabla[0]["es_consenso"] is True
    assert tabla[0]["orden"] == 1
    assert all(fila["es_consenso"] is False for fila in tabla[1:])
    assert [fila["orden"] for fila in tabla] == [1, 2, 3, 4]


def test_brier_ausente_cae_al_final_sin_imputacion() -> None:
    """[GOVERNANCE-01] `Brier=None` no se convierte en cero ni adelanta fila."""
    tabla = construir_tabla_sabiduria(
        [
            _fuente("Consenso", 0.60, 0.0, 1.0),
            _fuente("Q-BE", None, None, None),
            _fuente("Casino A", 0.70, -16.67, 1.0),
        ]
    )
    assert [fila["fuente"] for fila in tabla] == ["Consenso", "Casino A", "Q-BE"]
    assert tabla[-1]["brier"] is None


def test_pesos_brier_inversos_normalizados_y_piso() -> None:
    """[LN-QBE-148] Menor Brier ⇒ mayor peso; Σ pesos = 1 y piso 0.05."""
    pesos = pesos_desde_brier({"A": 0.60, "B": 0.80, "C": 0.95})
    assert set(pesos) == {"A", "B", "C"}
    assert sum(pesos.values()) == pytest.approx(1.0, abs=1e-6)
    assert all(peso >= PESO_MIN - 1e-9 for peso in pesos.values())
    assert pesos["A"] > pesos["B"] > pesos["C"]
    assert pesos_desde_brier({"Unico": 0.70}) == {"Unico": 1.0}


def test_alpha_relativo_a_qbe_canonico() -> None:
    """Alpha = ventaja de Q-BE sobre la fuente: (1 - QBE/fuente) × 100."""
    assert alpha_pct(0.75, 0.60) == pytest.approx(20.0)
    assert alpha_pct(0.6434, 0.2159) == pytest.approx(66.44, abs=0.01)
    assert alpha_pct(0.60, 0.60) == pytest.approx(0.0)
    assert alpha_pct(None, 0.75) is None
    assert alpha_pct(0.60, 0.0) == pytest.approx(100.0)


def test_jornadas_ordenadas_y_consenso_primero_en_cada_bloque() -> None:
    """La tabla por jornada conserva el Consenso como fila maestra de su bloque."""
    bloques = construir_tabla_por_jornada(
        [
            {
                "jornada": 16,
                "fuentes": [
                    _fuente("Casino A", 0.64, 66.0, 0.5),
                    _fuente("Consenso", 0.62, 66.4, 1.0),
                    _fuente("Q-BE", 0.66, 0.0, None),
                ],
            },
            {
                "jornada": 15,
                "fuentes": [
                    _fuente("Q-BE", 0.58, 0.0, None),
                    _fuente("Consenso", 0.60, 3.3, 1.0),
                    _fuente("Casino A", 0.61, 1.6, 1.0),
                ],
            },
        ]
    )
    assert [bloque["jornada"] for bloque in bloques] == [15, 16]
    for bloque in bloques:
        assert bloque["fuentes"][0]["fuente"] == "Consenso"
        assert bloque["fuentes"][0]["es_consenso"] is True
        assert all(fila["es_consenso"] is False for fila in bloque["fuentes"][1:])


def test_tabla_exige_un_unico_consenso() -> None:
    """El contrato falla en voz alta si falta o se duplica la fila maestra."""
    with pytest.raises(ValueError):
        construir_tabla_sabiduria([_fuente("Q-BE", 0.65, 0.0, None)])
    with pytest.raises(ValueError):
        construir_tabla_sabiduria(
            [_fuente("Consenso", 0.60, 0.0, 1.0), _fuente("Consenso", 0.61, 0.0, 1.0)]
        )
