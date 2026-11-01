# -*- coding: utf-8 -*-
"""[LN-QBE-147] Motor de Calibración y Perturbación de Variables Causales.

Régimen: ``[DIRGEN-STRICT]``. Función pura: sin I/O, sin red, sin BD, sin reloj.

Modelo puente (legislado en ``docs/LOGIC.md`` §20)
--------------------------------------------------
Las variables causales (``[LN-QBE-146]``) entran a la distribución soberana por
el único canal que la narrativa mide con censo completo: el volumen de remates
al arco. Con ``MU_LIGA`` = goles por equipo y partido de la temporada:

    ataque(lado)  = (V07_lado + 1) / (media_V07 + 1)
    defensa(lado) = (V13_lado + 1) / (media_V13 + 1)
    λ_local  = MU_LIGA · ataque(local)  / defensa(visita)
    λ_visita = MU_LIGA · ataque(visita) / defensa(local)

La distribución 1X2 se obtiene con el generador canónico Dixon-Coles
(``[VAULT-CORE-004]``, ``calcular_matriz_dixon_coles`` + ``colapsar_matriz_a_simplex``).

Perturbación controlada
-----------------------
Búsqueda voraz y determinista de factores multiplicativos **globales** por
(variable, lado). Cada candidato se acota a los límites físicos de la variable;
se acepta sólo si reduce estrictamente el Brier Score del lote. El acta registra
la secuencia completa y el impacto acumulado por variable.

Fail-Loud
---------
Lote vacío, marcador no entero, vector sin las llaves canónicas o medias no
positivas ⇒ ``CalibracionError``. Nunca se devuelve un acta vacía.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from src.core.distribution_dixon_coles import (
    calcular_matriz_dixon_coles,
    colapsar_matriz_a_simplex,
)

__all__ = [
    "CalibracionError",
    "LIMITES",
    "VARIABLES_PERTURBABLES",
    "aplicar_factores",
    "brier_multiclase",
    "calibrar",
    "distribucion_1x2",
    "lambdas_del_vector",
]

LADOS: Tuple[str, str] = ("local", "visita")

#: Límites físicos por variable (mínimo, máximo). Ningún movimiento los cruza.
LIMITES: Mapping[str, Tuple[float, float]] = {
    "V05": (0.0, 40.0),   # faltas
    "V07": (0.0, 25.0),   # remates al arco
    "V13": (0.0, 25.0),   # remates recibidos
    "V21": (0.0, 10.0),   # goles de pelota parada
    "V22": (0.0, 10.0),   # goles recibidos de pelota parada
    "V23": (0.0, 20.0),   # córners
    "V24": (0.0, 5.0),    # penales
    "V25": (0.0, 15.0),   # tarjetas
}

#: Variables que el optimizador puede mover. ``V20`` queda fuera: es binaria.
VARIABLES_PERTURBABLES: Tuple[str, ...] = tuple(LIMITES)

LAMBDA_MIN = 0.05
LAMBDA_MAX = 6.0
FACTORES_DEFECTO: Tuple[float, ...] = (0.85, 1.15)
PASOS_DEFECTO = 20
#: Banda del factor acumulado por (variable, lado). Impide que la búsqueda
#: comprima una variable hasta anularla (deriva degenerada del puente).
FACTOR_MIN = 0.5
FACTOR_MAX = 2.0


class CalibracionError(ValueError):
    """[LN-QBE-147] El lote no permite calibrar."""


# ── Distribución ───────────────────────────────────────────────────────────────────────────
def _acotar(valor: float, minimo: float, maximo: float) -> float:
    return max(minimo, min(maximo, valor))


def lambdas_del_vector(
    vector: Mapping[str, Mapping[str, Optional[float]]],
    medias: Mapping[str, float],
    mu_liga: float,
) -> Tuple[float, float]:
    """[LN-QBE-147] Traduce el vector causal a ``(λ_local, λ_visita)``."""
    if mu_liga <= 0.0:
        raise CalibracionError(f"[LN-QBE-147] MU_LIGA debe ser positivo: {mu_liga!r}")
    for clave in ("V07", "V13"):
        if clave not in vector:
            raise CalibracionError(f"[LN-QBE-147] El vector no declara {clave}")
        if medias.get(clave, 0.0) < 0.0:
            raise CalibracionError(
                f"[LN-QBE-147] La media de {clave} no puede ser negativa"
            )

    ataque_local = (float(vector["V07"]["local"] or 0.0) + 1.0) / (medias["V07"] + 1.0)
    ataque_visita = (float(vector["V07"]["visita"] or 0.0) + 1.0) / (medias["V07"] + 1.0)
    defensa_local = (float(vector["V13"]["local"] or 0.0) + 1.0) / (medias["V13"] + 1.0)
    defensa_visita = (float(vector["V13"]["visita"] or 0.0) + 1.0) / (medias["V13"] + 1.0)

    lam_local = _acotar(mu_liga * ataque_local / defensa_visita, LAMBDA_MIN, LAMBDA_MAX)
    lam_visita = _acotar(mu_liga * ataque_visita / defensa_local, LAMBDA_MIN, LAMBDA_MAX)
    return lam_local, lam_visita


def distribucion_1x2(lam_local: float, lam_visita: float) -> Tuple[float, float, float]:
    """[LN-QBE-147] Colapsa la matriz Dixon-Coles canónica al símplex 1X2."""
    matriz = calcular_matriz_dixon_coles(lam_local, lam_visita)
    return colapsar_matriz_a_simplex(matriz)


def brier_multiclase(
    p_local: float,
    p_empate: float,
    p_visitante: float,
    goles_local: int,
    goles_visita: int,
) -> float:
    """[LN-QBE-147] Brier de un partido: suma de cuadrados sobre los 3 desenlaces."""
    if goles_local > goles_visita:
        observado = (1.0, 0.0, 0.0)
    elif goles_local == goles_visita:
        observado = (0.0, 1.0, 0.0)
    else:
        observado = (0.0, 0.0, 1.0)
    return (
        (p_local - observado[0]) ** 2
        + (p_empate - observado[1]) ** 2
        + (p_visitante - observado[2]) ** 2
    )


# ── Perturbación ───────────────────────────────────────────────────────────────────────────
def _validar_lote(partidos: Sequence[Mapping[str, Any]]) -> None:
    if not partidos:
        raise CalibracionError("[LN-QBE-147] Lote vacío: no hay partidos que calibrar")
    for indice, partido in enumerate(partidos):
        for clave in ("vector", "goles_local", "goles_visita"):
            if clave not in partido:
                raise CalibracionError(
                    f"[LN-QBE-147] Partido #{indice} sin la llave {clave!r}"
                )
        for clave in ("goles_local", "goles_visita"):
            valor = partido[clave]
            if isinstance(valor, bool) or not isinstance(valor, int) or valor < 0:
                raise CalibracionError(
                    f"[LN-QBE-147] Partido #{indice}: {clave} debe ser entero ≥ 0, no {valor!r}"
                )


def aplicar_factores(
    vector: Mapping[str, Mapping[str, Optional[float]]],
    factores: Mapping[Tuple[str, str], float],
) -> Dict[str, Dict[str, Optional[float]]]:
    """Aplica los factores y acota cada variable a sus límites físicos."""
    nuevo = {variable: dict(valor) for variable, valor in vector.items()}
    for (variable, lado), factor in factores.items():
        if variable not in LIMITES or lado not in LADOS:
            continue
        actual = nuevo.get(variable, {}).get(lado)
        if actual is None:
            continue
        minimo, maximo = LIMITES[variable]
        nuevo[variable][lado] = _acotar(float(actual) * factor, minimo, maximo)
    return nuevo


def _brier_lote(
    partidos: Sequence[Mapping[str, Any]],
    factores: Mapping[Tuple[str, str], float],
    medias: Mapping[str, float],
    mu_liga: float,
) -> float:
    total = 0.0
    for partido in partidos:
        vector = aplicar_factores(partido["vector"], factores)
        lam_local, lam_visita = lambdas_del_vector(vector, medias, mu_liga)
        probabilidades = distribucion_1x2(lam_local, lam_visita)
        total += brier_multiclase(
            *probabilidades, partido["goles_local"], partido["goles_visita"]
        )
    return total / len(partidos)


def calibrar(
    partidos: Sequence[Mapping[str, Any]],
    medias: Mapping[str, float],
    mu_liga: float,
    *,
    pasos: int = PASOS_DEFECTO,
    factores: Iterable[float] = FACTORES_DEFECTO,
    variables: Sequence[str] = VARIABLES_PERTURBABLES,
) -> Dict[str, Any]:
    """[LN-QBE-147] Calibra el puente por perturbación voraz determinista.

    Returns:
        Acta con ``brier_base``, ``brier_optimizado``, ``delta``, la secuencia de
        ``movimientos`` y el ``impacto`` acumulado por variable.
    """
    _validar_lote(partidos)
    factores = tuple(float(factor) for factor in factores)
    if not factores or any(factor <= 0.0 for factor in factores):
        raise CalibracionError("[LN-QBE-147] Los factores deben ser positivos")

    brier_base = _brier_lote(partidos, {}, medias, mu_liga)
    aplicados: Dict[Tuple[str, str], float] = {}
    brier_actual = brier_base
    movimientos: List[Dict[str, Any]] = []

    for _paso in range(max(0, pasos)):
        mejor: Optional[Tuple[float, str, str, float, float]] = None
        for variable in variables:
            if variable not in LIMITES:
                continue
            for lado in LADOS:
                for factor in factores:
                    acumulado = aplicados.get((variable, lado), 1.0)
                    nuevo_factor = _acotar(acumulado * factor, FACTOR_MIN, FACTOR_MAX)
                    if abs(nuevo_factor - acumulado) < 1e-12:
                        continue
                    candidato = dict(aplicados)
                    candidato[(variable, lado)] = nuevo_factor
                    valor = _brier_lote(partidos, candidato, medias, mu_liga)
                    if valor < brier_actual - 1e-12:
                        if mejor is None or valor < mejor[0] - 1e-12:
                            mejor = (valor, variable, lado, factor, nuevo_factor)
        if mejor is None:
            break
        valor, variable, lado, factor, nuevo_factor = mejor
        aplicados[(variable, lado)] = nuevo_factor
        movimientos.append(
            {
                "paso": len(movimientos) + 1,
                "variable": variable,
                "lado": lado,
                "factor": factor,
                "brier_previo": round(brier_actual, 8),
                "brier_nuevo": round(valor, 8),
                "delta": round(valor - brier_actual, 8),
            }
        )
        brier_actual = valor

    impacto: Dict[str, Dict[str, Any]] = {}
    for movimiento in movimientos:
        clave = f"{movimiento['variable']}_{movimiento['lado']}"
        registro = impacto.setdefault(
            clave,
            {
                "variable": movimiento["variable"],
                "lado": movimiento["lado"],
                "movimientos": 0,
                "factor_final": 1.0,
                "delta_total": 0.0,
            },
        )
        registro["movimientos"] += 1
        # Factor ACUMULADO y acotado realmente aplicado (no el producto de crudos).
        registro["factor_final"] = round(
            aplicados[(movimiento["variable"], movimiento["lado"])], 8
        )
        registro["delta_total"] = round(
            registro["delta_total"] + movimiento["delta"], 8
        )

    ranking = sorted(impacto.values(), key=lambda fila: (fila["delta_total"], fila["variable"]))
    return {
        "partidos": len(partidos),
        "mu_liga": round(mu_liga, 8),
        "medias": {clave: round(valor, 8) for clave, valor in medias.items()},
        "brier_base": round(brier_base, 8),
        "brier_optimizado": round(brier_actual, 8),
        "delta": round(brier_actual - brier_base, 8),
        "mejora_relativa": (
            round((brier_base - brier_actual) / brier_base, 8) if brier_base else 0.0
        ),
        "pasos_ejecutados": len(movimientos),
        "movimientos": movimientos,
        "impacto_por_variable": ranking,
        "top3": ranking[:3],
        "factores_finales": {
            f"{variable}_{lado}": round(factor, 8)
            for (variable, lado), factor in sorted(aplicados.items())
        },
    }
