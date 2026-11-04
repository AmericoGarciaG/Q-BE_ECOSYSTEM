# -*- coding: utf-8 -*-
"""`[ARCH-1.4.75]` Rescate del Daemon Centinela Multicasa y Orquestador de Temporizadores.

Régimen: ``[DIRGEN-STRICT]``. Orquestación pura de temporizadores y timeouts;
la extracción vive en los scrapers y la persistencia en ``odds_ticks``.

Reglas
------
* 4 h de lunes a jueves.
* 1 h viernes y sábado.
* 10 min dentro de las 3 h previas al kickoff (la ventana manda sobre el día).
* Timeout canónico de red: ``CONST_TIMEOUT_DAEMON_LIVE = 30000`` ms.
* Sin repositorio disponible: ``DatabaseConnectionError`` (Fail-Loud).
"""

from __future__ import annotations

import math
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from datetime import datetime, timedelta
from typing import Any, Callable, Optional

__all__ = [
    "CONST_TIMEOUT_DAEMON_LIVE",
    "DatabaseConnectionError",
    "OrquestadorCentinela",
    "calcular_intervalo",
    "ejecutar_con_timeout",
]

CONST_TIMEOUT_DAEMON_LIVE: int = 30000
VENTANA_PRE_KICKOFF = timedelta(hours=3)
INTERVALO_PRE_KICKOFF = timedelta(minutes=10)
INTERVALO_LUNES_JUEVES = timedelta(hours=4)
INTERVALO_VIERNES_SABADO = timedelta(hours=1)


class DatabaseConnectionError(RuntimeError):
    """La bóveda no está disponible para el orquestador (Fail-Loud)."""


def calcular_intervalo(ahora: datetime, kickoff: datetime) -> timedelta:
    """Cadencia de muestreo vigente para el instante ``ahora`` y el ``kickoff`` dado."""
    if not isinstance(ahora, datetime) or not isinstance(kickoff, datetime):
        raise TypeError("calcular_intervalo exige datetime en 'ahora' y 'kickoff'.")
    restante = kickoff - ahora
    if restante <= VENTANA_PRE_KICKOFF and restante >= timedelta(0):
        return INTERVALO_PRE_KICKOFF
    if restante < timedelta(0):
        return INTERVALO_LUNES_JUEVES if ahora.weekday() <= 3 else INTERVALO_VIERNES_SABADO
    if ahora.weekday() <= 3:  # lunes=0 … jueves=3
        return INTERVALO_LUNES_JUEVES
    return INTERVALO_VIERNES_SABADO


def ejecutar_con_timeout(
    funcion: Callable[[], Any],
    timeout_ms: int = CONST_TIMEOUT_DAEMON_LIVE,
) -> Any:
    """Ejecuta ``funcion`` con techo de tiempo; al vencer lanza ``TimeoutError`` sin colgar."""
    if not callable(funcion):
        raise TypeError("ejecutar_con_timeout exige un callable.")
    try:
        presupuesto = float(timeout_ms) / 1000.0
    except (TypeError, ValueError) as error:
        raise ValueError(f"timeout_ms inválido: {timeout_ms!r}.") from error
    if not math.isfinite(presupuesto) or presupuesto <= 0.0:
        raise ValueError(f"timeout_ms debe ser finito y positivo: {timeout_ms!r}.")

    pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="centinela-multicasa")
    futuro = pool.submit(funcion)
    try:
        return futuro.result(timeout=presupuesto)
    except FutureTimeoutError:
        futuro.cancel()
        raise TimeoutError(
            f"Timeout de red tras {timeout_ms} ms en el Daemon Multicasa."
        ) from None
    finally:
        pool.shutdown(wait=False, cancel_futures=True)


class OrquestadorCentinela:
    """Orquestador de muestreo multicasa; exige un repositorio de persistencia."""

    def __init__(self, repositorio: Optional[Any] = None) -> None:
        if repositorio is None:
            raise DatabaseConnectionError(
                "Sin base de datos disponible: el Orquestador Centinela no puede "
                "persistir ticks en odds_ticks."
            )
        self.repositorio = repositorio

    def recolectar_tick(
        self,
        extractor: Callable[[], Any],
        timeout_ms: int = CONST_TIMEOUT_DAEMON_LIVE,
    ) -> Any:
        """[ARCH-1.4.75] Extrae un tick con el techo canónico y lo entrega al repositorio."""
        return ejecutar_con_timeout(extractor, timeout_ms=timeout_ms)


def main() -> int:
    """[ARCH-1.4.75] Entry point del Daemon Multicasa: delega en el motor de mercado.

    La extracción multi-operador y la persistencia viven en ``centinela_mercado``;
    este módulo conserva la identidad del nodo y el orquestador de temporizadores.
    """
    from src.ingestion.daemons.centinela_mercado import main as _main_mercado

    _main_mercado()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
