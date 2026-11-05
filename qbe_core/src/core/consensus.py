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

``desmarginar_shin(cuotas)``
    ``[LN-QBE-151]`` Invierte el modelo de microestructura de Shin (1991, 1993) y
    devuelve el símplex intrínseco del mercado (``ShinDevigResult``), purgando el
    sesgo favorito-longshot que la normalización proporcional no corrige.

Invariantes
-----------
* Cada cuota debe ser finita y estrictamente mayor que ``1.0``.
* Cada peso debe ser finito y no negativo; la suma de pesos debe ser positiva.
* El resultado vive en el 2-símplex: ``p_i >= 0`` y ``Σ p_i = 1``.
* Cualquier violación lanza ``ConsensoInvalidoError``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, Sequence, Tuple

__all__ = [
    "ConsensoInvalidoError",
    "calcular_consenso_ponderado",
    "promediar_simplex",
    "InvalidOddsException",
    "ShinDevigResult",
    "desmarginar_shin",
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


# ═══════════════════════════════════════════════════════════════════════════════════════
# [LN-QBE-151] MOTOR DE DES-MARGEN IMPLÍCITO DE SHIN (Shin De-vigging Engine)
#
# Inversión determinista del modelo de microestructura de Shin (1991, 1993). Resuelve el
# parámetro de apostadores informados `z` sobre la ecuación canónica
#     Σ_k √(z² + 4(1−z)π_k²/S) = 2 + z
# y devuelve el símplex intrínseco del mercado. Sin I/O, sin reloj, sin aleatoriedad.
# Constantes selladas: docs/CONSTANTS.md §11 (EPSILON_SHIN, MAX_ITER_SHIN, SHIN_ODDS_*).
# ═══════════════════════════════════════════════════════════════════════════════════════

EPSILON_SHIN: float = 1e-9          # ε_shin — convergencia y conservación del símplex
MAX_ITER_SHIN: int = 100            # N_max_iter,shin — techo de la bisección
SHIN_ODDS_MIN: float = 1.0500       # O_min,shin — cota inferior de admisibilidad
SHIN_ODDS_MAX: float = 50.0000      # O_max,shin — cota superior de admisibilidad


class InvalidOddsException(ValueError):
    """[LN-QBE-151] Cuota fuera de contrato: no numérica, no finita, ≤ 1.0 o fuera de cotas."""


@dataclass(frozen=True)
class ShinDevigResult:
    """[LN-QBE-151] Símplex intrínseco del mercado 1X2 tras el des-margen de Shin."""

    p_local: float
    p_empate: float
    p_visitante: float
    z_insider: float
    overround_bruto: float


def _validar_cuotas_shin(cuotas: Sequence[float]) -> Tuple[float, float, float]:
    """[LN-QBE-151] Aduana de la terna: tres cuotas decimales finitas dentro de ``[1.05, 50.0]``."""
    if cuotas is None:
        raise InvalidOddsException(
            "Cuotas ausentes: se esperaba la terna decimal (O_1, O_X, O_2)."
        )
    try:
        terna = tuple(cuotas)
    except TypeError:
        raise InvalidOddsException(
            f"Cuotas no iterables: {cuotas!r}. Se esperaba la terna (O_1, O_X, O_2)."
        ) from None
    if len(terna) != 3:
        raise InvalidOddsException(
            f"Se esperaban 3 cuotas 1X2, se recibieron {len(terna)}: {terna!r}."
        )
    valores = []
    for indice, cuota in enumerate(terna):
        if isinstance(cuota, bool) or not isinstance(cuota, (int, float)):
            raise InvalidOddsException(
                f"Cuota {indice + 1} no numérica: {cuota!r}. Prohibida la coerción de cadenas."
            )
        valor = float(cuota)
        if not math.isfinite(valor):
            raise InvalidOddsException(f"Cuota {indice + 1} no finita: {cuota!r}.")
        if valor <= 1.0:
            raise InvalidOddsException(
                f"Cuota {indice + 1} inválida: {valor!r}. Debe ser estrictamente mayor que 1.0."
            )
        if not (SHIN_ODDS_MIN <= valor <= SHIN_ODDS_MAX):
            raise InvalidOddsException(
                f"Cuota {indice + 1} fuera de admisibilidad [{SHIN_ODDS_MIN:.4f}, "
                f"{SHIN_ODDS_MAX:.4f}]: {valor!r}."
            )
        valores.append(valor)
    return valores[0], valores[1], valores[2]


def _resolver_z_shin(pi: Sequence[float], sobremargen: float) -> float:
    """[LN-QBE-151] Bisección sobre ``F(z) = Σ√(z² + 4(1−z)π_k²/S) − 2 − z`` en ``[0, min π_k]``."""
    def funcion(z: float) -> float:
        """[LN-QBE-151] ``F(z) = Σ_k √(z² + 4(1−z)π_k²/S) − 2 − z``: residual de la bisección."""
        return math.fsum(
            math.sqrt(z * z + 4.0 * (1.0 - z) * (cuota * cuota) / sobremargen)
            for cuota in pi
        ) - 2.0 - z

    inferior, superior = 0.0, min(pi)
    f_inferior = funcion(inferior)
    if f_inferior == 0.0:
        return 0.0
    f_superior = funcion(superior)
    if f_inferior * f_superior > 0.0:
        raise InvalidOddsException(
            "Sin raíz de Shin en [0, min(π_k)]: "
            f"F(0)={f_inferior:.12g}, F(min π_k)={f_superior:.12g}, S={sobremargen:.12g}."
        )
    for _ in range(MAX_ITER_SHIN):
        if (superior - inferior) <= EPSILON_SHIN:
            break
        medio = 0.5 * (inferior + superior)
        if f_inferior * funcion(medio) <= 0.0:
            superior = medio
        else:
            inferior = medio
            f_inferior = funcion(inferior)
    return 0.5 * (inferior + superior)


def desmarginar_shin(cuotas: Sequence[float]) -> ShinDevigResult:
    """[LN-QBE-151] Des-margen de Shin: probabilidad libre de margen y sesgo purgado.

    Resuelve ``z ∈ [0, min(π_k)]`` (bisección, ε = 1e-9, ≤ 100 iteraciones) sobre la
    ecuación canónica ``Σ_k √(z² + 4(1−z)π_k²/S) = 2 + z`` —forma equivalente exacta de
    ``Σ_k p_k = 1``— y devuelve el símplex intrínseco del mercado. Si ``S ≤ 1.0`` no hay
    des-margen identificable: ``z = 0`` y ``p_k = π_k / S``.
    """
    cuota_local, cuota_empate, cuota_visitante = _validar_cuotas_shin(cuotas)
    pi = (1.0 / cuota_local, 1.0 / cuota_empate, 1.0 / cuota_visitante)
    sobremargen = math.fsum(pi)

    if sobremargen <= 1.0:
        z_insider = 0.0
        probabilidades = (
            pi[0] / sobremargen,
            pi[1] / sobremargen,
            pi[2] / sobremargen,
        )
    else:
        z_insider = _resolver_z_shin(pi, sobremargen)
        denominador = 2.0 * (1.0 - z_insider)
        if denominador <= 0.0:
            raise InvalidOddsException(
                f"Denominador degenerado en el des-margen de Shin: z={z_insider!r}."
            )
        probabilidades = tuple(
            (
                math.sqrt(
                    z_insider * z_insider
                    + 4.0 * (1.0 - z_insider) * (cuota * cuota) / sobremargen
                )
                - z_insider
            )
            / denominador
            for cuota in pi
        )

    total = math.fsum(probabilidades)
    if abs(total - 1.0) > EPSILON_SHIN:
        raise InvalidOddsException(
            f"Símplex de Shin no conservativo: Σ p_k = {total!r} (tolerancia {EPSILON_SHIN:g})."
        )
    if not all(0.0 < valor < 1.0 for valor in probabilidades):
        raise InvalidOddsException(
            f"Probabilidad fuera del interior del símplex: {probabilidades!r}."
        )

    return ShinDevigResult(
        p_local=probabilidades[0],
        p_empate=probabilidades[1],
        p_visitante=probabilidades[2],
        z_insider=z_insider,
        overround_bruto=sobremargen,
    )
