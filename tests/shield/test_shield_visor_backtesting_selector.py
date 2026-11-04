# -*- coding: utf-8 -*-
"""🏆 THE SHIELD — JUEZ INMUTABLE `[DES-QBE-077]` (SELECTOR DE DISTRIBUCIÓN).

Base de Gobierno: `docs/DESIGN.md` §7.3, `docs/LOGIC.md` §21.
Fuente única de verdad: `odds_ticks` (`[ARCH-1.5.13]`).

Contrato congelado antes de la materialización (Paso 2). El selector **no**
existe todavía en `src/`; por eso el binding concreto falla en RED. El Paso 3
no está autorizado.

Aserciones del contrato:
  1. [A1] Réplica analítica: inyectar `Casino_A` en el selector filtra el DTO
     de simulación a los ticks de ese casino.
  2. [A2] Invarianza estructural: seleccionar `Consenso` inyecta el Símplex
     ponderado, no una fuente individual.
  3. [Sad Path] Un casino no registrado ⇒ `FuenteDesconocidaError`.
"""

from __future__ import annotations

import abc
import importlib
from typing import Any, Dict, List, Tuple

import pytest

MODULO_ESPERADO = "src.observatory.visor_backtesting"
RAIZ_ESPERADA = "qbe_observatory/src/observatory/visor_backtesting.py"
SIMBOLOS_REQUERIDOS = ("FuenteDesconocidaError", "construir_dto_simulacion")

Consenso = Tuple[float, float, float]
Tick = Dict[str, Any]


def _tick(casino_id: str, timestamp: str, odd_home: float, odd_draw: float, odd_away: float) -> Tick:
    return {
        "casino_id": casino_id,
        "match_id": "m_2026_11_02_america_tigres",
        "timestamp": timestamp,
        "odd_home": odd_home,
        "odd_draw": odd_draw,
        "odd_away": odd_away,
    }


def _serie() -> List[Tick]:
    return [
        _tick("Casino_A", "2026-11-01T17:00:00Z", 2.10, 3.40, 3.60),
        _tick("Casino_A", "2026-11-01T17:10:00Z", 2.00, 3.50, 3.90),
        _tick("Casino_B", "2026-11-01T17:05:00Z", 2.20, 3.30, 3.40),
    ]


def _cargar_motor() -> Any:
    """Carga el selector materializado; si no existe, falla en RED (Paso 3 no autorizado)."""
    try:
        modulo = importlib.import_module(MODULO_ESPERADO)
    except ModuleNotFoundError as exc:
        raise pytest.fail.Exception(
            f"[RED] [DES-QBE-077] El selector de distribución no está materializado en "
            f"`{RAIZ_ESPERADA}`: {exc}. El Paso 3 no ha sido autorizado.",
            pytrace=False,
        ) from None
    ausentes = [nombre for nombre in SIMBOLOS_REQUERIDOS if not hasattr(modulo, nombre)]
    if ausentes:
        pytest.fail(
            f"[RED] [DES-QBE-077] `{MODULO_ESPERADO}` existe, pero faltan símbolos del "
            f"contrato: {', '.join(ausentes)}.",
            pytrace=False,
        )
    return modulo


class AbstractTestDES_QBE_077(abc.ABC):
    """Contrato inmutable del Selector de Distribución en el Visor de Backtesting.

    Abstracta por diseño: el binding concreto (`TestDES_QBE_077`) declara la
    procedencia del constructor de DTO. Las aserciones no se alteran al
    materializar el nodo.
    """

    @abc.abstractmethod
    def motor(self) -> Any:
        """Devuelve el módulo materializado que implementa `[DES-QBE-077]`."""

    def test_replica_analitica_filtra_ticks_del_casino_inyectado(self) -> None:
        """[A1] `Casino_A` ⇒ el DTO sólo transporta ticks de `Casino_A`."""
        motor = self.motor()
        dto = motor.construir_dto_simulacion(
            fuente="Casino_A",
            ticks=_serie(),
            consenso=(0.52, 0.25, 0.23),
        )
        assert dto["fuente"] == "Casino_A"
        assert [fila["casino_id"] for fila in dto["ticks"]] == ["Casino_A", "Casino_A"]

    def test_invarianza_consenso_inyecta_simplex_ponderado(self) -> None:
        """[A2] `Consenso` ⇒ el DTO inyecta el Símplex ponderado, no un casino."""
        motor = self.motor()
        consenso: Consenso = (0.52, 0.25, 0.23)
        dto = motor.construir_dto_simulacion(
            fuente="Consenso",
            ticks=_serie(),
            consenso=consenso,
        )
        assert dto["fuente"] == "Consenso"
        assert tuple(float(valor) for valor in dto["simplex"]) == pytest.approx(consenso, abs=1e-9)
        assert sum(dto["simplex"]) == pytest.approx(1.000000, abs=1e-6)

    def test_sad_path_casino_no_registrado(self) -> None:
        """[Sad Path] Casino fuera del catálogo ⇒ `FuenteDesconocidaError`."""
        motor = self.motor()
        with pytest.raises(motor.FuenteDesconocidaError):
            motor.construir_dto_simulacion(
                fuente="Casino_Z",
                ticks=_serie(),
                consenso=(0.52, 0.25, 0.23),
            )


class TestDES_QBE_077(AbstractTestDES_QBE_077):
    """Binding RED: el selector `[DES-QBE-077]` aún no existe en `src/` (Paso 3 pendiente)."""

    def motor(self) -> Any:
        return _cargar_motor()
