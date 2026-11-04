# -*- coding: utf-8 -*-
"""🏆 THE SHIELD — JUEZ INMUTABLE `[LN-QBE-149]` (RADAR DE SINDICATOS).

Base de Gobierno: `docs/LOGIC.md` §21, `docs/CONSTANTS.md` §10.
Fuente única de verdad: `odds_ticks` (`[ARCH-1.5.13]`).

Contrato congelado antes de la materialización (Paso 2). El radar **no** existe
todavía en `src/`; por eso el binding concreto falla en RED. El Paso 3 no está
autorizado.

Aserciones del contrato:
  1. [A1] Réplica analítica: un delta de cambio mayor a `0.10` y opuesto al
     Consenso Ponderado retorna `True` en la alerta.
  2. [A2] Invarianza estructural: un delta menor a `0.10` retorna `False`.
  3. [Sad Path] Una serie temporal vacía o con un solo tick no colapsa en
     silencio: `ValueError` (Fail-Loud).
"""

from __future__ import annotations

import abc
import importlib
from typing import Any, Dict, List, Sequence, Tuple

import pytest

MODULO_ESPERADO = "src.core.radar_sindicatos"
RAIZ_ESPERADA = "qbe_core/src/core/radar_sindicatos.py"
SIMBOLOS_REQUERIDOS = ("detectar_ruptura_sindicato",)

CONST_DELTA_SINDICATO_PCT = 0.10
Consenso = Tuple[float, float, float]
Tick = Dict[str, Any]


def _tick(timestamp: str, odd_home: float, odd_draw: float, odd_away: float) -> Tick:
    return {
        "casino_id": "Casino_A",
        "timestamp": timestamp,
        "odd_home": odd_home,
        "odd_draw": odd_draw,
        "odd_away": odd_away,
    }


def _probabilidad_implicita(odd: float) -> float:
    return 1.0 / odd


def _cargar_motor() -> Any:
    """Carga el radar materializado; si no existe, falla en RED (Paso 3 no autorizado)."""
    try:
        modulo = importlib.import_module(MODULO_ESPERADO)
    except ModuleNotFoundError as exc:
        raise pytest.fail.Exception(
            f"[RED] [LN-QBE-149] El radar de sindicatos no está materializado en "
            f"`{RAIZ_ESPERADA}`: {exc}. El Paso 3 no ha sido autorizado.",
            pytrace=False,
        ) from None
    ausentes = [nombre for nombre in SIMBOLOS_REQUERIDOS if not hasattr(modulo, nombre)]
    if ausentes:
        pytest.fail(
            f"[RED] [LN-QBE-149] `{MODULO_ESPERADO}` existe, pero faltan símbolos del "
            f"contrato: {', '.join(ausentes)}.",
            pytrace=False,
        )
    return modulo


class AbstractTestLN_QBE_149(abc.ABC):
    """Contrato inmutable del Motor de Detección de Rupturas de Consenso.

    Abstracta por diseño: el binding concreto (`TestLN_QBE_149`) declara la
    procedencia del motor. Las aserciones no se alteran al materializar el nodo.
    """

    @abc.abstractmethod
    def motor(self) -> Any:
        """Devuelve el módulo materializado que implementa `[LN-QBE-149]`."""

    def test_alerta_con_delta_mayor_al_umbral_y_opuesto_al_consenso(self) -> None:
        """[A1] Delta > 0.10 contra el consenso ⇒ alerta `True`."""
        motor = self.motor()
        serie: List[Tick] = [
            _tick("2026-11-01T17:00:00Z", 2.20, 3.30, 3.20),
            _tick("2026-11-01T17:10:00Z", 3.10, 3.30, 3.20),
        ]
        # Consenso con masa en el local (0.55); el casino se mueve en contra:
        # 1/2.20 = 0.4545 → 1/3.10 = 0.3226 (Δ ≈ -0.1319 > 0.10).
        consenso: Consenso = (0.55, 0.24, 0.21)
        assert _probabilidad_implicita(2.20) - _probabilidad_implicita(3.10) > CONST_DELTA_SINDICATO_PCT
        assert (
            motor.detectar_ruptura_sindicato(
                serie, consenso, umbral=CONST_DELTA_SINDICATO_PCT
            )
            is True
        )

    def test_invarianza_delta_menor_al_umbral_no_alerta(self) -> None:
        """[A2] Delta < 0.10 ⇒ sin alerta (`False`)."""
        motor = self.motor()
        serie: List[Tick] = [
            _tick("2026-11-01T17:00:00Z", 2.20, 3.30, 3.20),
            _tick("2026-11-01T17:10:00Z", 2.25, 3.30, 3.20),
        ]
        consenso: Consenso = (0.55, 0.24, 0.21)
        assert _probabilidad_implicita(2.20) - _probabilidad_implicita(2.25) < CONST_DELTA_SINDICATO_PCT
        assert (
            motor.detectar_ruptura_sindicato(
                serie, consenso, umbral=CONST_DELTA_SINDICATO_PCT
            )
            is False
        )

    def test_sad_path_serie_temporal_insuficiente(self) -> None:
        """[Sad Path] Serie vacía o de un solo tick ⇒ `ValueError` (Fail-Loud)."""
        motor = self.motor()
        consenso: Consenso = (0.55, 0.24, 0.21)
        with pytest.raises(ValueError):
            motor.detectar_ruptura_sindicato([], consenso, umbral=CONST_DELTA_SINDICATO_PCT)
        with pytest.raises(ValueError):
            motor.detectar_ruptura_sindicato(
                [_tick("2026-11-01T17:00:00Z", 2.20, 3.30, 3.20)],
                consenso,
                umbral=CONST_DELTA_SINDICATO_PCT,
            )


class TestLN_QBE_149(AbstractTestLN_QBE_149):
    """Binding RED: el radar `[LN-QBE-149]` aún no existe en `src/` (Paso 3 pendiente)."""

    def motor(self) -> Any:
        return _cargar_motor()
