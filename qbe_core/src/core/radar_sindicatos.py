# -*- coding: utf-8 -*-
"""`[LN-QBE-149]` Motor de Detección de Rupturas de Consenso (Radar de Sindicatos).

Régimen: ``[DIRGEN-STRICT]``. Función pura: sin I/O, sin red, sin reloj.

Contrato
--------
``detectar_ruptura_sindicato(serie_ticks, consenso, umbral=0.10) -> bool``
    Mide la tasa de cambio de la probabilidad implícita del local entre el
    primer y el último tick. Si ``|Δ| > umbral`` y el movimiento va en contra
    del sesgo del Consenso Ponderado, emite alerta.

Invariantes
-----------
* Una serie vacía o con un solo tick es evidencia insuficiente: ``ValueError``.
* Cada tick debe portar ``odd_home`` decimal finito y mayor que ``1.0``.
* El umbral canónico es ``CONST_DELTA_SINDICATO_PCT = 0.10``.
"""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

__all__ = ["detectar_ruptura_sindicato"]

CONST_DELTA_SINDICATO_PCT = 0.10


def _probabilidad_implicita_local(tick: Mapping[str, Any]) -> float:
    """[LN-QBE-149] Probabilidad implícita local (1/odd_home) de un tick."""
    cuota = tick.get("odd_home")
    try:
        valor = float(cuota)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Tick sin 'odd_home' decimal válido: {cuota!r}.") from error
    if not math.isfinite(valor) or valor <= 1.0:
        raise ValueError(f"Cuota local inválida: {cuota!r}. Debe ser mayor que 1.0.")
    return 1.0 / valor


def detectar_ruptura_sindicato(
    serie_ticks: Sequence[Mapping[str, Any]],
    consenso: Sequence[float],
    umbral: float = CONST_DELTA_SINDICATO_PCT,
) -> bool:
    """[LN-QBE-149] ``True`` si hay movimiento anómalo contra el consenso; ``False`` si no."""
    if serie_ticks is None or len(serie_ticks) < 2:
        raise ValueError(
            "Serie temporal insuficiente: se requieren al menos 2 ticks para medir "
            "una tasa de cambio (Fail-Loud, sin imputación)."
        )
    if len(consenso) != 3:
        raise ValueError(f"El consenso debe tener 3 componentes, tiene {len(consenso)}.")

    umbral_valido = float(umbral)
    if not math.isfinite(umbral_valido) or umbral_valido < 0.0:
        raise ValueError(f"Umbral inválido: {umbral!r}.")

    primero = serie_ticks[0]
    ultimo = serie_ticks[-1]
    delta = _probabilidad_implicita_local(ultimo) - _probabilidad_implicita_local(primero)

    if abs(delta) <= umbral_valido:
        return False

    sesgo_consenso = float(consenso[0]) - (1.0 / 3.0)
    if abs(sesgo_consenso) < 1e-12:
        return True
    return (delta < 0.0) if sesgo_consenso > 0.0 else (delta > 0.0)
