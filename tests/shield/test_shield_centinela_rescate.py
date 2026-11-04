# -*- coding: utf-8 -*-
"""🏆 THE SHIELD — JUEZ INMUTABLE `[ARCH-1.4.75]` (RESCATE DEL CENTINELA MULTICASA).

Base de Gobierno: `docs/ARCH.md` §16, `docs/CONSTANTS.md` §10.
Fuente única de verdad: `odds_ticks` (`[ARCH-1.5.13]`).

Contrato congelado antes de la materialización (Paso 2). El orquestador **no**
existe todavía en `src/`; por eso el binding concreto falla en RED. El Paso 3
no está autorizado.

Aserciones del contrato:
  1. [A1] Réplica analítica: los intervalos de muestreo respetan la
     temporalidad canónica — 4h de lunes a jueves, 1h viernes/sábado y 10min
     en las 3 horas previas al kickoff.
  2. [A2] Invarianza estructural: un timeout de red de `30000` ms lanza
     `TimeoutError` y no cuelga el hilo.
  3. [Sad Path] Sin base de datos disponible ⇒ `DatabaseConnectionError`.
"""

from __future__ import annotations

import abc
import importlib
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

MODULO_ESPERADO = "src.ingestion.daemons.centinela_multicasa"
RAIZ_ESPERADA = "qbe_ingestion/src/ingestion/daemons/centinela_multicasa.py"
SIMBOLOS_REQUERIDOS = (
    "CONST_TIMEOUT_DAEMON_LIVE",
    "DatabaseConnectionError",
    "OrquestadorCentinela",
    "calcular_intervalo",
    "ejecutar_con_timeout",
)

KICKOFF = datetime(2026, 11, 2, 20, 0, tzinfo=timezone.utc)  # lunes 20:00 UTC


def _utc(anio: int, mes: int, dia: int, hora: int, minuto: int) -> datetime:
    return datetime(anio, mes, dia, hora, minuto, tzinfo=timezone.utc)


def _cargar_motor() -> Any:
    """Carga el orquestador materializado; si no existe, falla en RED (Paso 3 no autorizado)."""
    try:
        modulo = importlib.import_module(MODULO_ESPERADO)
    except ModuleNotFoundError as exc:
        raise pytest.fail.Exception(
            f"[RED] [ARCH-1.4.75] El Daemon Centinela Multicasa no está materializado en "
            f"`{RAIZ_ESPERADA}`: {exc}. El Paso 3 no ha sido autorizado.",
            pytrace=False,
        ) from None
    ausentes = [nombre for nombre in SIMBOLOS_REQUERIDOS if not hasattr(modulo, nombre)]
    if ausentes:
        pytest.fail(
            f"[RED] [ARCH-1.4.75] `{MODULO_ESPERADO}` existe, pero faltan símbolos del "
            f"contrato: {', '.join(ausentes)}.",
            pytrace=False,
        )
    return modulo


class AbstractTestARCH_1_4_75(abc.ABC):
    """Contrato inmutable del Rescate del Daemon Centinela Multicasa.

    Abstracta por diseño: el binding concreto (`TestARCH_1_4_75`) declara la
    procedencia del orquestador. Las aserciones no se alteran al materializarlo.
    """

    @abc.abstractmethod
    def motor(self) -> Any:
        """Devuelve el módulo materializado que implementa `[ARCH-1.4.75]`."""

    def test_replica_analitica_temporizadores_de_muestreo(self) -> None:
        """[A1] 4h lun–jue, 1h vie/sáb y 10min en las 3h previas al kickoff."""
        motor = self.motor()

        # Lunes 10:00 a 10 horas del kickoff ⇒ cadencia base de 4h.
        assert motor.calcular_intervalo(
            ahora=_utc(2026, 11, 2, 10, 0), kickoff=KICKOFF
        ) == timedelta(hours=4)

        # Viernes 10:00 (jornada de viernes) ⇒ cadencia de 1h.
        assert motor.calcular_intervalo(
            ahora=_utc(2026, 11, 6, 10, 0), kickoff=_utc(2026, 11, 6, 20, 0)
        ) == timedelta(hours=1)

        # Sábado 18:30, dentro de las 3h previas ⇒ 10min (la ventana manda).
        assert motor.calcular_intervalo(
            ahora=_utc(2026, 11, 7, 18, 30), kickoff=_utc(2026, 11, 7, 20, 0)
        ) == timedelta(minutes=10)

        # Lunes 18:00, también dentro de las 3h previas ⇒ 10min.
        assert motor.calcular_intervalo(
            ahora=_utc(2026, 11, 2, 18, 0), kickoff=KICKOFF
        ) == timedelta(minutes=10)

    def test_invarianza_timeout_30000_no_cuelga_el_hilo(self) -> None:
        """[A2] El timeout canónico es 30000 ms; al vencer lanza `TimeoutError`."""
        motor = self.motor()
        assert motor.CONST_TIMEOUT_DAEMON_LIVE == 30000

        inicio = time.monotonic()
        # Se ejerce la misma guarda con un presupuesto corto para no bloquear el
        # Juez 30 s; el techo canónico se certifica en la línea anterior.
        with pytest.raises(TimeoutError):
            motor.ejecutar_con_timeout(lambda: time.sleep(0.5), timeout_ms=50)
        assert time.monotonic() - inicio < 2.0

    def test_sad_path_sin_base_de_datos(self) -> None:
        """[Sad Path] Sin repositorio disponible ⇒ `DatabaseConnectionError`."""
        motor = self.motor()
        with pytest.raises(motor.DatabaseConnectionError):
            motor.OrquestadorCentinela(repositorio=None)


class TestARCH_1_4_75(AbstractTestARCH_1_4_75):
    """Binding RED: el Centinela Multicasa aún no existe en `src/` (Paso 3 pendiente)."""

    def motor(self) -> Any:
        return _cargar_motor()
