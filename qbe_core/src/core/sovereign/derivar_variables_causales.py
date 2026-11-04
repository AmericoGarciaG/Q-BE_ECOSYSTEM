# -*- coding: utf-8 -*-
"""[LN-QBE-146] Motor de Derivación de Variables Causales.

Régimen: ``[DIRGEN-STRICT]``. Función pura: sin I/O, sin red, sin BD, sin reloj.

Convierte la línea de tiempo factual de un partido (``historical_match_events``,
``[LN-QBE-144]``) en el vector canónico de 32 variables del catálogo
``[LN-QBE-120]``. Deriva por conteo directo o por proximidad temporal lo que la
narrativa «Jugada a Jugada» prueba, y **declara ``SIN EVIDENCIA``** lo que no es
inferible de eventos (posesión, pases, xG, contexto). No imputa, no modela y no
interpola: ``None`` nunca significa ``0.0``.

Contrato
--------
``derivar_variables_causales(match_id, eventos) -> dict[str, dict[str, float | None]]``
    Devuelve las 32 claves ``V01``…``V32``; cada valor es
    ``{"local": float | None, "visita": float | None}``.

Fail-Loud
---------
Lista vacía, ``match_id`` inválido, evento sin ``lado``/``tipo``/``orden_dom`` o
``lado`` fuera de dominio ⇒ ``DerivacionError``. Nunca se devuelve un vector
vacío ni un valor fabricado.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

__all__ = [
    "DerivacionError",
    "LADOS",
    "VARIABLES",
    "VARIABLES_DERIVADAS",
    "VARIABLES_SIN_EVIDENCIA",
    "derivar_variables_causales",
]

LADOS: Tuple[str, str] = ("local", "visita")

#: Catálogo canónico `[LN-QBE-120]` §2.1: 32 variables correlativas.
VARIABLES: Tuple[str, ...] = tuple(f"V{indice:02d}" for indice in range(1, 33))

#: Variables que la línea de tiempo prueba por conteo o por proximidad temporal.
VARIABLES_DERIVADAS: Tuple[str, ...] = (
    "V05",  # Faltas cometidas
    "V07",  # Tiros al arco (SoT)
    "V13",  # Tiros al arco recibidos (SoTA), dual exacto de V07
    "V20",  # Clean sheets
    "V21",  # Goles a favor de pelota parada
    "V22",  # Goles recibidos de pelota parada, dual de V21
    "V23",  # Córners
    "V24",  # Penales señalados
    "V25",  # Tarjetas amarillas + rojas
)

#: Variables declaradas `SIN EVIDENCIA`: no inferibles de la narrativa.
VARIABLES_SIN_EVIDENCIA: Tuple[str, ...] = tuple(
    variable for variable in VARIABLES if variable not in VARIABLES_DERIVADAS
)

#: Ventana máxima (minutos) entre la pelota parada y el gol que la aprovecha.
#: Cinco minutos cubre la conversión de un penal señalado (en la muestra: 7' → 10').
VENTANA_PELOTA_PARADA_MIN = 5

TIPOS_REMATE = frozenset({"tiro_a_gol", "gol", "gol_penal"})
TIPOS_GOL = frozenset({"gol", "gol_penal"})
TIPOS_PELOTA_PARADA = frozenset({"corner", "penal"})
TIPOS_FALTA = frozenset({"falta"})
TIPOS_CORNER = frozenset({"corner"})
TIPOS_PENAL = frozenset({"penal"})
TIPOS_TARJETA = frozenset({"tarjeta_amarilla", "tarjeta_roja"})


class DerivacionError(ValueError):
    """[LN-QBE-146] La lista de eventos no permite derivar el vector canónico."""


# ── Aduana ──────────────────────────────────────────────────────────────────────────────────
def _validar_evento(evento: Any, indice: int) -> Tuple[str, str, int]:
    """[LN-QBE-146] Devuelve ``(lado, tipo, orden_dom)`` o aborta (Fail-Loud)."""
    if not isinstance(evento, Mapping):
        raise DerivacionError(
            f"[LN-QBE-146] Evento #{indice}: se esperaba Mapping, "
            f"se recibió {type(evento).__name__}"
        )
    lado = evento.get("lado")
    if lado not in LADOS:
        raise DerivacionError(
            f"[LN-QBE-146] Evento #{indice}: lado debe ser 'local' o 'visita', no {lado!r}"
        )
    tipo = evento.get("tipo")
    if not isinstance(tipo, str) or not tipo.strip():
        raise DerivacionError(
            f"[LN-QBE-146] Evento #{indice}: tipo es obligatorio y debe ser texto"
        )
    orden = evento.get("orden_dom")
    if isinstance(orden, bool) or not isinstance(orden, int):
        raise DerivacionError(
            f"[LN-QBE-146] Evento #{indice}: orden_dom debe ser entero, no {orden!r}"
        )
    return lado, tipo.strip(), orden


def _minuto_efectivo(evento: Mapping[str, Any]) -> Optional[int]:
    """[LN-QBE-146] ``minuto + minuto_agregado``; ``None`` si el rótulo no declara minuto base."""
    minuto = evento.get("minuto")
    agregado = evento.get("minuto_agregado")
    if isinstance(minuto, bool) or not isinstance(minuto, int):
        return None
    extra = agregado if isinstance(agregado, int) and not isinstance(agregado, bool) else 0
    return minuto + extra


def _opuesto(lado: str) -> str:
    """[LN-QBE-146] Devuelve el lado contrario (local ↔ visita)."""
    return "visita" if lado == "local" else "local"


def _vector_vacio() -> Dict[str, Dict[str, Optional[float]]]:
    """[LN-QBE-146] Construye el vector de 32 variables con ambos lados en ``None``."""
    return {variable: {"local": None, "visita": None} for variable in VARIABLES}


# ── Contrato público ───────────────────────────────────────────────────────────────────────
def derivar_variables_causales(
    match_id: str, eventos: Sequence[Mapping[str, Any]]
) -> Dict[str, Dict[str, Optional[float]]]:
    """[LN-QBE-146] Deriva el vector canónico de 32 variables de un partido.

    Args:
        match_id: llave de la bóveda (``historical_matches.match_id``).
        eventos: línea de tiempo con el contrato de ``[LN-QBE-141]``.

    Returns:
        ``{"V01": {"local": ..., "visita": ...}, ..., "V32": {...}}``.

    Raises:
        DerivacionError: si ``match_id`` es inválido, la lista está vacía o un
            evento no cumple el contrato.
    """
    if not isinstance(match_id, str) or not match_id.strip():
        raise DerivacionError(
            f"[LN-QBE-146] match_id debe ser texto no vacío: {match_id!r}"
        )
    if not isinstance(eventos, Sequence) or isinstance(eventos, (str, bytes)):
        raise DerivacionError(
            f"[LN-QBE-146] eventos debe ser una secuencia, no {type(eventos).__name__}"
        )
    if not eventos:
        raise DerivacionError(
            f"[LN-QBE-146] Lista de eventos vacía para {match_id}: no hay vector que derivar"
        )

    conteo: Dict[str, Dict[str, int]] = {
        lado: {"falta": 0, "remate": 0, "corner": 0, "penal": 0, "tarjeta": 0, "gol": 0}
        for lado in LADOS
    }
    ordenados: List[Tuple[int, str, str, Optional[int]]] = []

    for indice, evento in enumerate(eventos):
        lado, tipo, orden = _validar_evento(evento, indice)
        ordenados.append((orden, lado, tipo, _minuto_efectivo(evento)))
        if tipo in TIPOS_FALTA:
            conteo[lado]["falta"] += 1
        if tipo in TIPOS_REMATE:
            conteo[lado]["remate"] += 1
        if tipo in TIPOS_CORNER:
            conteo[lado]["corner"] += 1
        if tipo in TIPOS_PENAL:
            conteo[lado]["penal"] += 1
        if tipo in TIPOS_TARJETA:
            conteo[lado]["tarjeta"] += 1
        if tipo in TIPOS_GOL:
            conteo[lado]["gol"] += 1

    # Pelota parada: el evento inmediatamente anterior del mismo lado, dentro de
    # la ventana, debe ser córner o penal. Determinista sobre `orden_dom`, que en
    # el visor es cronológico INVERSO (0 = final del partido): se recorre de mayor
    # a menor para que el «anterior» sea el que ocurrió antes en el tiempo real.
    pelota_parada: Dict[str, int] = {lado: 0 for lado in LADOS}
    ultimo: Dict[str, Tuple[str, Optional[int]]] = {}
    for _orden, lado, tipo, minuto in sorted(ordenados, key=lambda fila: fila[0], reverse=True):
        if tipo in TIPOS_GOL:
            previo = ultimo.get(lado)
            if previo is not None:
                tipo_previo, minuto_previo = previo
                if (
                    tipo_previo in TIPOS_PELOTA_PARADA
                    and minuto is not None
                    and minuto_previo is not None
                    and 0 <= minuto - minuto_previo <= VENTANA_PELOTA_PARADA_MIN
                ):
                    pelota_parada[lado] += 1
        ultimo[lado] = (tipo, minuto)

    vector = _vector_vacio()
    for lado in LADOS:
        rival = _opuesto(lado)
        vector["V05"][lado] = float(conteo[lado]["falta"])
        vector["V07"][lado] = float(conteo[lado]["remate"])
        vector["V13"][lado] = float(conteo[rival]["remate"])
        vector["V20"][lado] = 1.0 if conteo[rival]["gol"] == 0 else 0.0
        vector["V21"][lado] = float(pelota_parada[lado])
        vector["V22"][lado] = float(pelota_parada[rival])
        vector["V23"][lado] = float(conteo[lado]["corner"])
        vector["V24"][lado] = float(conteo[lado]["penal"])
        vector["V25"][lado] = float(conteo[lado]["tarjeta"])

    return vector
