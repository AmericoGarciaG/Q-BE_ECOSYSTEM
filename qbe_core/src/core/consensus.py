# -*- coding: utf-8 -*-
"""`[LN-QBE-148]` Motor de Consenso Ponderado (Wisdom of the Crowds).

Régimen: ``[DIRGEN-STRICT]``. Función pura: sin I/O, sin red, sin reloj.

Contrato
--------
``calcular_consenso_ponderado(momios_por_casino, pesos)``
    Aplica ``[LN-QBE-007-C]`` (Vig-Free De-biasing) a cada casino y devuelve
    ``Δ² = Σ (P_casino_i · W_i)`` como tupla de tres probabilidades que suman 1.

``promediar_simplex(probabilidades_por_casino, pesos)``
    Agrega filas YA de-vigadas. Rechaza cualquier fila cuya suma no sea 1
    (tolerancia ``1e-6``): prohibido promediar cuotas brutas.

Invariantes
-----------
* Cada cuota debe ser finita y estrictamente mayor que ``1.0``.
* Cada peso debe ser finito y no negativo; la suma de pesos debe ser positiva.
* El resultado vive en el 2-símplex: ``p_i >= 0`` y ``Σ p_i = 1``.
* Cualquier violación lanza ``ConsensoInvalidoError``.
"""

from __future__ import annotations

import math
from typing import Dict, Iterable, Mapping, Sequence, Tuple

__all__ = [
    "ConsensoInvalidoError",
    "calcular_consenso_ponderado",
    "promediar_simplex",
]

TOLERANCIA_SIMPLEX = 1e-6
Simplex = Tuple[float, float, float]


class ConsensoInvalidoError(ValueError):
    """[LN-QBE-148] Entrada fuera del contrato del consenso (cuotas brutas, pesos o símplex inválidos)."""


def _validar_cuotas(momios: Sequence[float]) -> None:
    """[LN-QBE-148] Valida que las tres cuotas 1X2 sean decimales finitas > 1.0."""
    if len(momios) != 3:
        raise ConsensoInvalidoError(f"Se esperaban 3 cuotas 1X2, se recibieron {len(momios)}.")
    for cuota in momios:
        valor = float(cuota)
        if not math.isfinite(valor) or valor <= 1.0:
            raise ConsensoInvalidoError(
                f"Cuota decimal inválida: {cuota!r}. Debe ser finita y mayor que 1.0."
            )


def _validar_pesos(pesos: Mapping[str, float], casinos: Iterable[str]) -> Dict[str, float]:
    """[LN-QBE-148] Valida y normaliza los pesos de las fuentes del consenso."""
    faltantes = [casino for casino in casinos if casino not in pesos]
    if faltantes:
        raise ConsensoInvalidoError(f"Faltan pesos para los casinos: {', '.join(faltantes)}.")
    normalizados: Dict[str, float] = {}
    for casino, peso in pesos.items():
        valor = float(peso)
        if not math.isfinite(valor) or valor < 0.0:
            raise ConsensoInvalidoError(f"Peso inválido para '{casino}': {peso!r}.")
        normalizados[casino] = valor
    total = sum(normalizados.get(casino, 0.0) for casino in casinos)
    if not math.isfinite(total) or total <= 0.0:
        raise ConsensoInvalidoError("La suma de pesos debe ser finita y positiva.")
    return {casino: normalizados[casino] / total for casino in casinos}


def _simplex_vig_free(momios: Sequence[float]) -> Simplex:
    """[LN-QBE-148] ``[LN-QBE-007-C]``: normaliza las probabilidades implícitas al 2-símplex."""
    _validar_cuotas(momios)
    inversas = [1.0 / float(cuota) for cuota in momios]
    total = sum(inversas)
    if not math.isfinite(total) or total <= 0.0:
        raise ConsensoInvalidoError("La suma de probabilidades implícitas no es positiva.")
    return (inversas[0] / total, inversas[1] / total, inversas[2] / total)


def calcular_consenso_ponderado(
    momios_por_casino: Mapping[str, Sequence[float]],
    pesos: Mapping[str, float],
) -> Simplex:
    """[LN-QBE-148] Consenso vig-free: ``Δ² = Σ (P_casino_i · W_i)``."""
    if not momios_por_casino:
        raise ConsensoInvalidoError("No hay casinos en la muestra de consenso.")
    pesos_norm = _validar_pesos(pesos, momios_por_casino.keys())
    consenso = [0.0, 0.0, 0.0]
    for casino, momios in momios_por_casino.items():
        simplex = _simplex_vig_free(momios)
        peso = pesos_norm[casino]
        for indice in range(3):
            consenso[indice] += peso * simplex[indice]
    total = sum(consenso)
    if not math.isfinite(total) or total <= 0.0:
        raise ConsensoInvalidoError("El consenso calculado no es un símplex válido.")
    return (consenso[0] / total, consenso[1] / total, consenso[2] / total)


def promediar_simplex(
    probabilidades_por_casino: Mapping[str, Sequence[float]],
    pesos: Mapping[str, float],
) -> Simplex:
    """[LN-QBE-148] Promedia filas YA de-vigadas; rechaza cuotas brutas (suma ≠ 1)."""
    if not probabilidades_por_casino:
        raise ConsensoInvalidoError("No hay fuentes en la muestra de consenso.")
    for casino, fila in probabilidades_por_casino.items():
        if len(fila) != 3:
            raise ConsensoInvalidoError(
                f"La fila de '{casino}' debe tener 3 componentes, tiene {len(fila)}."
            )
        valores = [float(valor) for valor in fila]
        for valor in valores:
            if not math.isfinite(valor) or valor < 0.0 or valor > 1.0:
                raise ConsensoInvalidoError(
                    f"Probabilidad inválida en '{casino}': {valor!r}."
                )
        suma = sum(valores)
        if abs(suma - 1.0) > TOLERANCIA_SIMPLEX:
            raise ConsensoInvalidoError(
                f"'{casino}' no es un símplex vig-free: suma {suma:.9f} ≠ 1.0 "
                f"(tolerancia {TOLERANCIA_SIMPLEX:g}). Prohibido promediar cuotas brutas."
            )
    pesos_norm = _validar_pesos(pesos, probabilidades_por_casino.keys())
    consenso = [0.0, 0.0, 0.0]
    for casino, fila in probabilidades_por_casino.items():
        peso = pesos_norm[casino]
        for indice in range(3):
            consenso[indice] += peso * float(fila[indice])
    total = sum(consenso)
    return (consenso[0] / total, consenso[1] / total, consenso[2] / total)
