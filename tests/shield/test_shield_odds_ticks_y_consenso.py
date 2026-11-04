# -*- coding: utf-8 -*-
"""🏆 THE SHIELD — JUEZ INMUTABLE `[LN-QBE-148]` (WISDOM OF THE CROWDS).

Base de Gobierno: `docs/LOGIC.md` §21, `docs/ARCH.md` §15.4.
Fuente única de verdad: `odds_ticks` (`[ARCH-1.5.13]`).

Contrato congelado antes de la materialización (Paso 2). El motor de consenso
ponderado **no** existe todavía en `src/`; por eso el binding concreto de este
Juez falla en RED. El Paso 3 (materialización) no está autorizado.

Aserciones del contrato:
  1. [A1] Réplica analítica: el consenso es el promedio ponderado de los
     símplex de-vig de cada casino (Vig-Free De-biasing `[LN-QBE-007-C]`).
  2. [A2] Invarianza estructural: el Símplex Δ² consensuado suma `1.000000`
     con tolerancia `1e-6` y cada componente vive en `[0, 1]`.
  3. [Sad Path] Promediar cuotas brutas (probabilidades implícitas con
     overround, sin de-vig) es un anti-patrón: debe lanzar
     `ConsensoInvalidoError`.
"""

from __future__ import annotations

import abc
import importlib
from typing import Any, Dict, Tuple

import pytest

MODULO_ESPERADO = "src.core.consensus"
RAIZ_ESPERADA = "qbe_core/src/core/consensus.py"
SIMBOLOS_REQUERIDOS = (
    "ConsensoInvalidoError",
    "calcular_consenso_ponderado",
    "promediar_simplex",
)

Momios = Dict[str, Tuple[float, float, float]]
Pesos = Dict[str, float]


def _simplex_vig_free(momios: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """`[LN-QBE-007-C]`: normaliza las probabilidades implícitas al 2-símplex."""
    inversas = [1.0 / cuota for cuota in momios]
    total = sum(inversas)
    return tuple(inversa / total for inversa in inversas)  # type: ignore[return-value]


def _consenso_analitico(momios_por_casino: Momios, pesos: Pesos) -> Tuple[float, float, float]:
    """Réplica independiente: Δ² = Σ (P_casino · W_casino) sobre símplex de-vig."""
    resultado = [0.0, 0.0, 0.0]
    for casino, momios in momios_por_casino.items():
        for indice, probabilidad in enumerate(_simplex_vig_free(momios)):
            resultado[indice] += pesos[casino] * probabilidad
    return (resultado[0], resultado[1], resultado[2])


def _cargar_motor() -> Any:
    """Carga el motor materializado; si no existe, falla en RED (Paso 3 no autorizado)."""
    try:
        modulo = importlib.import_module(MODULO_ESPERADO)
    except ModuleNotFoundError as exc:
        raise pytest.fail.Exception(
            f"[RED] [LN-QBE-148] El motor de consenso no está materializado en "
            f"`{RAIZ_ESPERADA}`: {exc}. El Paso 3 no ha sido autorizado.",
            pytrace=False,
        ) from None
    ausentes = [nombre for nombre in SIMBOLOS_REQUERIDOS if not hasattr(modulo, nombre)]
    if ausentes:
        pytest.fail(
            f"[RED] [LN-QBE-148] `{MODULO_ESPERADO}` existe, pero faltan símbolos del "
            f"contrato: {', '.join(ausentes)}.",
            pytrace=False,
        )
    return modulo


class AbstractTestLN_QBE_148(abc.ABC):
    """Contrato inmutable del Motor de Consenso Ponderado (Wisdom of the Crowds).

    La clase es abstracta porque no fija la procedencia del motor: el binding
    concreto (`TestLN_QBE_148`) declara dónde vive la materialización. Cuando el
    Paso 3 exista, sólo cambia el binding; estas aserciones permanecen intactas.
    """

    @abc.abstractmethod
    def motor(self) -> Any:
        """Devuelve el módulo materializado que implementa `[LN-QBE-148]`."""

    def test_replica_analitica_promedio_ponderado_vig_free(self) -> None:
        """[A1] El consenso iguala el promedio ponderado de los símplex de-vig."""
        motor = self.motor()
        momios: Momios = {
            "Casino_A": (2.10, 3.40, 3.60),
            "Casino_B": (2.00, 3.50, 3.90),
            "Casino_C": (2.20, 3.30, 3.40),
        }
        pesos: Pesos = {"Casino_A": 0.50, "Casino_B": 0.30, "Casino_C": 0.20}
        esperado = _consenso_analitico(momios, pesos)
        obtenido = motor.calcular_consenso_ponderado(momios, pesos)
        assert tuple(float(valor) for valor in obtenido) == pytest.approx(esperado, abs=1e-9)

    def test_invarianza_estructural_simplex_suma_exacta(self) -> None:
        """[A2] El Símplex Δ² consensuado suma 1.000000 (tolerancia 1e-6)."""
        motor = self.motor()
        momios: Momios = {
            "Casino_A": (1.95, 3.55, 4.10),
            "Casino_B": (2.05, 3.45, 3.80),
            "Casino_C": (2.00, 3.60, 4.00),
        }
        pesos: Pesos = {"Casino_A": 0.40, "Casino_B": 0.35, "Casino_C": 0.25}
        consenso = tuple(float(valor) for valor in motor.calcular_consenso_ponderado(momios, pesos))
        assert sum(consenso) == pytest.approx(1.000000, abs=1e-6)
        assert all(0.0 <= probabilidad <= 1.0 for probabilidad in consenso)

    def test_sad_path_cuotas_brutas_sin_devig(self) -> None:
        """[Sad Path] Promediar cuotas brutas (overround) debe lanzar `ConsensoInvalidoError`."""
        motor = self.motor()
        # Probabilidades implícitas de cuotas brutas: suman 1.048 > 1. No son un símplex.
        brutas = {"Casino_A": (1.0 / 2.10, 1.0 / 3.40, 1.0 / 3.60)}
        with pytest.raises(motor.ConsensoInvalidoError):
            motor.promediar_simplex(brutas, {"Casino_A": 1.0})


class TestLN_QBE_148(AbstractTestLN_QBE_148):
    """Binding RED: el motor `[LN-QBE-148]` aún no existe en `src/` (Paso 3 pendiente)."""

    def motor(self) -> Any:
        return _cargar_motor()
