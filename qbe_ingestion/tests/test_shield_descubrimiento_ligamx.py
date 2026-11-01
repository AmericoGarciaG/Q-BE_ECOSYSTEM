# -*- coding: utf-8 -*-
"""🏆 THE SHIELD — JUEZ DEL CONSTRUCTOR DETERMINISTA DE URLs DE DESCUBRIMIENTO.

Nodo: `[LN-QBE-142]` Sonda de Descubrimiento de Partidos y URLs Minuto a Minuto.
Prueba pura y offline: no navega, no descarga, no usa red.
"""

from __future__ import annotations

import base64
import json

import pytest

from scripts.auditoria.descubrir_partidos_ligamx import (
    DescubrimientoError,
    construir_url_minuto_a_minuto,
    normalizar_jornada,
)

URL_67047 = (
    "https://ligamx.net/cancha/mxm/67047/"
    "eyJpZENsdWJsb2NhbCI6IjEiLCJpZENsdWJ2aXNpdGEiOiIxNCIsImlkUGFydGlkbyI6IjY3MDQ3IiwicGVzdGFuYSI6IjMifQ=="
)


def test_url_exacta_del_partido_de_muestra() -> None:
    """[INV 1] La URL de América vs Monterrey es estable y byte a byte."""
    assert construir_url_minuto_a_minuto("67047", "1", "14") == URL_67047


def test_payload_base64_de_la_url() -> None:
    """[INV 2] La carga útil declara las claves y la pestaña que usa el sitio."""
    carga = construir_url_minuto_a_minuto("67047", "1", "14").rsplit("/", 1)[1]
    datos = json.loads(base64.b64decode(carga).decode("utf-8"))
    assert datos == {
        "idClublocal": "1",
        "idClubvisita": "14",
        "idPartido": "67047",
        "pestana": "3",
    }


def test_acepta_identificadores_enteros() -> None:
    """[INV 3] Los IDs del widget llegan como str o int; el contrato no cambia."""
    assert construir_url_minuto_a_minuto(67047, 1, 14) == URL_67047


def test_normalizacion_de_jornada() -> None:
    """[INV 4] Acepta ``16`` y ``Jornada 16``; rechaza cualquier otra forma."""
    assert normalizar_jornada("16") == "16"
    assert normalizar_jornada("Jornada 16") == "16"
    with pytest.raises(DescubrimientoError):
        normalizar_jornada("Octavos de final")


def test_rechaza_identificadores_no_numericos() -> None:
    """[SAD 1] Un ID vacío o no numérico aborta; no se inventa una URL."""
    with pytest.raises(DescubrimientoError):
        construir_url_minuto_a_minuto("67047", "1", "")
    with pytest.raises(DescubrimientoError):
        construir_url_minuto_a_minuto("abc", "1", "14")
