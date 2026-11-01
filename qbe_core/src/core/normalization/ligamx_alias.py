# -*- coding: utf-8 -*-
"""[LN-QBE-145] Diccionario Canónico de Alias de Liga MX (``ligamx.net`` → bóveda).

Régimen: ``[DIRGEN-STRICT]``. Función pura: sin I/O, sin estado, sin red.

Motivo
------
El Join Determinista de ``[ARCH-1.5.1]`` §15.3 exige coincidencia exacta de slug
contra ``historical_matches``. El sitio publica nombres de pantalla que no son
los nombres canónicos de la bóveda (``Jaguares`` ≠ ``Chiapas``,
``M. Morelia`` ≠ ``Morelia``), y esa diferencia producía rechazos de partidos
que sí existen.

Contrato
--------
``resolver_alias_ligamx(nombre) -> str``
    Traduce un nombre de pantalla a su nombre canónico. La búsqueda es una
    igualdad literal de cadena: **cero fuzzy matching**, cero plegado de
    mayúsculas o acentos, cero distancia de edición. Si la clave no existe,
    devuelve el nombre original sin modificarlo.

Invariante
----------
Todo valor del diccionario existe literalmente como ``home_team``/``away_team``
en ``historical_matches`` (temporada 2015-2016, 18 clubes): los nombres de
pantalla se extrajeron de la corrida real de la Jornada 16 del Clausura 2016 y
de la cartelera del sitio; no se inventó ninguna variante.

Deuda declarada: una variante no listada no se resuelve por aproximación; se
manifiesta como ``MatchResolutionError`` y exige una ampliación legislada.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Final, Mapping

__all__ = ["ALIAS_LIGAMX", "resolver_alias_ligamx"]

#: Nombre de pantalla de ``ligamx.net`` → nombre canónico de la bóveda.
#: Evidencia: sobre parseado de la Jornada 16 (Clausura 2016) para las entradas
#: ``Jaguares``, ``M. Morelia``, ``Tigres``, ``Club Tijuana``, ``Pumas`` y
#: ``Puebla F.C.``; cartelera del sitio para ``Tigres de la U.A.N.L.``,
#: ``Universidad Nacional`` y ``Dorados de Sinaloa``.
ALIAS_LIGAMX: Final[Mapping[str, str]] = MappingProxyType(
    {
        # Chiapas
        "Jaguares": "Chiapas",
        # Morelia
        "M. Morelia": "Morelia",
        # Tigres UANL
        "Tigres": "Tigres UANL",
        "Tigres de la U.A.N.L.": "Tigres UANL",
        # Tijuana
        "Club Tijuana": "Tijuana",
        "Tijuana": "Tijuana",
        # Pumas UNAM
        "Pumas": "Pumas UNAM",
        "Universidad Nacional": "Pumas UNAM",
        # Puebla
        "Puebla F.C.": "Puebla",
        # Dorados
        "Dorados de Sinaloa": "Dorados",
    }
)


def resolver_alias_ligamx(nombre: str) -> str:
    """[LN-QBE-145] Traduce un nombre de pantalla al nombre canónico de la bóveda.

    Args:
        nombre: nombre tal como lo publica el sitio o lo entrega el parser.

    Returns:
        El nombre canónico si existe alias; en otro caso, ``nombre`` sin cambios.

    Raises:
        TypeError: si ``nombre`` no es ``str``.
    """
    if not isinstance(nombre, str):
        raise TypeError(
            f"[LN-QBE-145] resolver_alias_ligamx espera str, recibió {type(nombre).__name__}"
        )
    return ALIAS_LIGAMX.get(nombre, nombre)
