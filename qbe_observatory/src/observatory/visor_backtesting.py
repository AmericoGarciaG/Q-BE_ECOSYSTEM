# -*- coding: utf-8 -*-
"""`[DES-QBE-077]` Selector de Distribución en el Visor de Backtesting.

Régimen: ``[DIRGEN-STRICT]``. Construcción pura de DTO: sin I/O, sin red.

Fuentes admitidas
-----------------
* ``"Consenso"``: inyecta el Símplex ponderado ``Δ²`` (``[LN-QBE-148]``).
* ``"Q-BE"``: inyecta el mismo Símplex consensuado como referencia soberana.
* ``casino_id`` presente en la serie: filtra los ticks de ese casino.

Un casino no registrado lanza ``FuenteDesconocidaError`` (Fail-Loud).
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

__all__ = ["FuenteDesconocidaError", "construir_dto_simulacion"]

TOLERANCIA_SIMPLEX = 1e-6
FUENTES_AGREGADAS = frozenset({"consenso", "q-be", "qbe"})


class FuenteDesconocidaError(ValueError):
    """La fuente solicitada no está registrada en el catálogo del visor."""


def _validar_simplex(consenso: Sequence[float]) -> tuple[float, float, float]:
    if len(consenso) != 3:
        raise ValueError(f"El consenso debe tener 3 componentes, tiene {len(consenso)}.")
    valores = tuple(float(valor) for valor in consenso)
    if any(valor < 0.0 or valor > 1.0 for valor in valores):
        raise ValueError(f"Probabilidad fuera de [0, 1] en el consenso: {valores!r}.")
    if abs(sum(valores) - 1.0) > TOLERANCIA_SIMPLEX:
        raise ValueError(f"El consenso no suma 1.0: {sum(valores):.9f}.")
    return valores  # type: ignore[return-value]


def construir_dto_simulacion(
    fuente: str,
    ticks: Sequence[Mapping[str, Any]],
    consenso: Sequence[float],
) -> dict[str, Any]:
    """Construye el DTO de simulación para la fuente seleccionada en el visor."""
    if not isinstance(fuente, str) or not fuente.strip():
        raise FuenteDesconocidaError("La fuente del selector no puede estar vacía.")
    nombre = fuente.strip()

    if nombre.lower() in FUENTES_AGREGADAS:
        simplex = _validar_simplex(consenso)
        return {"fuente": nombre, "simplex": simplex, "ticks": []}

    filtrados = [dict(tick) for tick in ticks if str(tick.get("casino_id")) == nombre]
    if not filtrados:
        raise FuenteDesconocidaError(
            f"Casino no registrado en la serie de odds_ticks: '{nombre}'."
        )
    return {"fuente": nombre, "ticks": filtrados}
