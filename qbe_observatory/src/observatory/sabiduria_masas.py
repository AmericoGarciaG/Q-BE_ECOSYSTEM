# -*- coding: utf-8 -*-
"""`[DES-QBE-076]` Tabla Comparativa de Sabiduría de las Masas.

Funciones puras de presentación: reciben las métricas ya calculadas por el
Observatorio y las ordenan para el Visor de Calibración.

Contrato
--------
* El **Consenso Ponderado** ocupa siempre la fila superior (`es_consenso=True`).
* Las filas restantes se ordenan por `Brier Score` ascendente; `None` va al final.
* Los pesos del consenso se derivan del Brier inverso con piso
  `CONST_PESO_CONSENSO_MIN = 0.05`; la suma es 1.0.
* `Alpha (%)` de una fuente = ventaja de Q-BE sobre esa fuente:
  `(1 - Brier_QBE / Brier_fuente) × 100` (positivo ⇒ Q-BE calibra mejor).
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Mapping, Optional, Sequence

__all__ = [
    "PESO_MIN",
    "alpha_pct",
    "brier_jornada",
    "brier_promedio_partidos",
    "construir_tabla_por_jornada",
    "construir_tabla_sabiduria",
    "pesos_desde_brier",
]

PESO_MIN = 0.05
FUENTE_CONSENSO = "Consenso"
COLUMNAS = ("fuente", "brier", "alpha_pct", "peso")


def _numero(valor: Any) -> Optional[float]:
    if valor is None or isinstance(valor, bool):
        return None
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return numero if math.isfinite(numero) else None


def brier_promedio_partidos(briers: Sequence[Any]) -> Optional[float]:
    """Media aritmética de los Brier de partidos con evidencia.

    ``None``/no finitos/negativos se excluyen. Si no queda ningún partido
    válido, retorna ``None``; jamás imputa cero.
    """
    validos: List[float] = []
    for valor in briers:
        numero = _numero(valor)
        if numero is None or numero < 0.0:
            continue
        validos.append(numero)
    if not validos:
        return None
    return round(sum(validos) / len(validos), 12)


def brier_jornada(partidos: Sequence[Mapping[str, Any]]) -> Optional[float]:
    """Brier de jornada: promedio de los Brier individuales de los partidos válidos."""
    return brier_promedio_partidos([partido.get("brier") for partido in partidos])


def pesos_desde_brier(
    brier_por_fuente: Mapping[str, Any],
    peso_min: float = PESO_MIN,
) -> Dict[str, float]:
    """Peso normalizado por Brier inverso, con piso ``peso_min``."""
    validos: Dict[str, float] = {}
    for fuente, brier in brier_por_fuente.items():
        numero = _numero(brier)
        if numero is None or numero <= 0.0:
            continue
        validos[str(fuente)] = 1.0 / max(numero, 1e-9)
    if not validos:
        return {}

    total = sum(validos.values())
    pesos = {fuente: crudo / total for fuente, crudo in validos.items()}
    for _ in range(32):
        bajos = [fuente for fuente, peso in pesos.items() if peso < peso_min]
        if not bajos:
            break
        for fuente in bajos:
            pesos[fuente] = peso_min
        libres = [fuente for fuente in pesos if fuente not in bajos]
        if not libres:
            break
        resto = 1.0 - (peso_min * len(bajos))
        total_libres = sum(validos[fuente] for fuente in libres)
        for fuente in libres:
            pesos[fuente] = resto * validos[fuente] / total_libres
    return {fuente: round(peso, 6) for fuente, peso in pesos.items()}


def alpha_pct(brier_fuente: Any, brier_qbe: Any) -> Optional[float]:
    """Ventaja de Q-BE sobre la fuente: ``(1 - Brier_QBE / Brier_fuente) × 100``.

    Positivo ⇒ Q-BE calibra mejor que la fuente. Denominador = Brier de la
    fuente, idéntico a la fórmula canónica de `_alpha_calibracion_pct`.
    """
    fuente = _numero(brier_fuente)
    qbe = _numero(brier_qbe)
    if fuente is None or qbe is None or fuente <= 0.0:
        return None
    return round((1.0 - (qbe / fuente)) * 100.0, 2)


def construir_tabla_sabiduria(
    fuentes: Sequence[Mapping[str, Any]],
    exigir_consenso: bool = True,
    fuente_maestra: str = FUENTE_CONSENSO,
) -> List[Dict[str, Any]]:
    """Ordena las fuentes con la fila MAESTRA fija en la parte superior.

    La maestra es `Consenso` por omisión; `[SPRINT-47]` admite rotularla
    `FootyStats` o `Q-BE Live Capture` cuando la evidencia de mercado proviene de
    un único corpus (`fuente_maestra`). Con ``exigir_consenso=False`` se admite
    un bloque sin maestra (solo Q-BE).
    """
    filas: List[Dict[str, Any]] = []
    for fuente in fuentes:
        fila = dict(fuente)
        nombre = str(fila.get("fuente") or "").strip()
        if not nombre:
            raise ValueError("Cada fila de sabiduría requiere 'fuente'.")
        fila["fuente"] = nombre
        fila["brier"] = _numero(fila.get("brier"))
        fila["alpha_pct"] = _numero(fila.get("alpha_pct"))
        fila["peso"] = _numero(fila.get("peso"))
        filas.append(fila)

    objetivo = str(fuente_maestra or FUENTE_CONSENSO).strip()
    maestras = [fila for fila in filas if fila["fuente"].lower() == objetivo.lower()]
    if len(maestras) > 1:
        raise ValueError(f"La tabla de sabiduría admite una sola fila '{objetivo}'.")
    if not maestras and exigir_consenso:
        raise ValueError(f"La tabla de sabiduría exige una fila '{objetivo}'.")
    maestra = maestras[0] if maestras else None
    resto = [fila for fila in filas if fila is not maestra]
    resto.sort(
        key=lambda fila: (
            fila["brier"] is None,
            fila["brier"] if fila["brier"] is not None else 0.0,
            fila["fuente"].lower(),
        )
    )
    ordenadas = ([maestra] if maestra is not None else []) + resto
    for posicion, fila in enumerate(ordenadas, start=1):
        fila["es_consenso"] = maestra is not None and posicion == 1
        fila["orden"] = posicion
    return ordenadas


def construir_tabla_por_jornada(
    jornadas: Sequence[Mapping[str, Any]]
) -> List[Dict[str, Any]]:
    """Agrupa la tabla por jornada; cada bloque conserva al Consenso arriba."""
    bloques: List[Dict[str, Any]] = []
    for bloque in sorted(jornadas, key=lambda item: int(item.get("jornada") or 0)):
        fuentes_brutas = bloque.get("fuentes") or []
        exigir = any(
            str(fila.get("fuente") or "").strip().lower() == FUENTE_CONSENSO.lower()
            for fila in fuentes_brutas
        )
        fuentes = construir_tabla_sabiduria(fuentes_brutas, exigir_consenso=exigir)
        salida = {
            clave: valor for clave, valor in bloque.items() if clave != "fuentes"
        }
        salida["jornada"] = int(bloque.get("jornada") or 0)
        salida["fuentes"] = fuentes
        bloques.append(salida)
    return bloques
