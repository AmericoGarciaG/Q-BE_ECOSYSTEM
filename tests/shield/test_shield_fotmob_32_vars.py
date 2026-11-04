# -*- coding: utf-8 -*-
"""🏆 THE SHIELD — `[ARCH-1.4.59]` CERTIFICACIÓN FOTMOB 32 VARIABLES.

Certifica que el Centinela de Macro-Estadísticas FotMob publica la evidencia
necesaria para el catálogo `[LN-QBE-120]` (V01–V32) antes del kickoff:

* cada variable está cubierta por un leaderboard del `tab=stats` o por una
  derivación declarada, o bien está declarada `FUERA DE FUENTE` con motivo;
* el artefacto congelado publica las claves de esos tableros para los 18 clubes;
* ninguna variable queda huérfana ni se imputa un cero sintético.

El Juez es determinista: consume el artefacto congelado, no la red.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set

import pytest

from src.ingestion.daemons.centinela_macro import (
    CATALOGO_VERSION,
    COBERTURA_FUERA_DE_FUENTE,
    DERIVACIONES,
    MAPA_LEADERBOARDS,
)

RAIZ = Path(__file__).resolve().parents[2]
RUTAS_ARTEFACTO = (
    RAIZ / "data" / "cache_macro_stats_liga_mx_2026.json",
    RAIZ / "qbe_ingestion" / "data" / "cache_macro_stats_liga_mx_2026.json",
)
VARIABLES: Set[str] = {f"V{indice:02d}" for indice in range(1, 33)}
PATRON_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _artefacto() -> Dict[str, Any]:
    for ruta in RUTAS_ARTEFACTO:
        if ruta.is_file():
            return json.loads(ruta.read_text(encoding="utf-8"))
    pytest.fail(
        "No existe el artefacto congelado de FotMob en "
        + " ni ".join(str(ruta) for ruta in RUTAS_ARTEFACTO)
    )


def _claves_por_variable() -> Dict[str, List[str]]:
    claves: Dict[str, List[str]] = {
        entrada["variable"]: [] for entrada in MAPA_LEADERBOARDS if entrada["variable"].startswith("V")
    }
    for entrada in MAPA_LEADERBOARDS:
        if entrada["variable"].startswith("V"):
            claves[entrada["variable"]].append(str(entrada["clave"]))
    for derivacion in DERIVACIONES:
        claves.setdefault(str(derivacion["variable"]), []).append(str(derivacion["clave"]))
    return claves


def test_cobertura_exhaustiva_de_las_32_variables() -> None:
    """[V01–V32] Toda variable está mapeada o declarada fuera de fuente."""
    claves = _claves_por_variable()
    cubiertas = set(claves) | set(COBERTURA_FUERA_DE_FUENTE)
    assert cubiertas == VARIABLES
    assert not (set(claves) & set(COBERTURA_FUERA_DE_FUENTE))
    assert set(COBERTURA_FUERA_DE_FUENTE) == {"V16", "V26", "V27", "V28", "V29", "V30", "V31", "V32"}


def test_cada_variable_fuera_de_fuente_declara_motivo() -> None:
    """[GOVERNANCE-01] Lo que FotMob no publica se declara, no se imputa."""
    for variable, motivo in COBERTURA_FUERA_DE_FUENTE.items():
        assert variable in VARIABLES
        assert isinstance(motivo, str) and motivo.strip()
        assert "sin evidencia" not in motivo.lower() or "no" in motivo.lower()


def test_artefacto_congelado_publica_cobertura_y_claves() -> None:
    """El artefacto materializa las 32 variables y las claves de sus tableros."""
    artefacto = _artefacto()
    assert artefacto.get("esquema") == "macro_stats_v1"
    assert artefacto.get("catalogo_version") == CATALOGO_VERSION
    assert artefacto.get("liga", {}).get("nombre") == "Liga MX"
    assert artefacto.get("liga", {}).get("fotmob_id") == 230
    assert len(artefacto.get("equipos") or {}) == 18
    assert artefacto.get("errores") == []

    cobertura = artefacto.get("cobertura") or {}
    claves = _claves_por_variable()
    for variable, lista_claves in claves.items():
        for clave in lista_claves:
            assert clave in cobertura, f"Falta '{clave}' ({variable}) en cobertura."
    assert set(COBERTURA_FUERA_DE_FUENTE) <= set(cobertura)
    assert set(artefacto.get("fuera_de_fuente") or {}) == set(COBERTURA_FUERA_DE_FUENTE)


def test_variables_mapeadas_tienen_al_menos_un_dato_factual() -> None:
    """Cada variable cubierta por FotMob tiene dato en al menos un club."""
    artefacto = _artefacto()
    equipos: Iterable[Dict[str, Any]] = (artefacto.get("equipos") or {}).values()
    for variable, claves in _claves_por_variable().items():
        con_dato = [
            clave
            for clave in claves
            if any(equipo.get(clave) is not None for equipo in equipos)
        ]
        assert con_dato, f"{variable} no tiene dato en ningún club: {claves}"


def test_fuera_de_fuente_sin_dato_sintetico() -> None:
    """Las variables fuera de fuente no publican dato (cero ceros sintéticos)."""
    artefacto = _artefacto()
    cobertura = artefacto.get("cobertura") or {}
    for variable in COBERTURA_FUERA_DE_FUENTE:
        entrada = cobertura.get(variable) or {}
        assert entrada.get("normalizacion") == "fuera_de_fuente"
        assert entrada.get("tablero") is None
        assert int(entrada.get("equipos_con_dato") or 0) == 0
        assert str(entrada.get("motivo") or "").strip()


def test_huella_y_generado_at_coherentes() -> None:
    """El artefacto conserva huella SHA-256 y sello temporal ISO-8601."""
    artefacto = _artefacto()
    huella = str(artefacto.get("hash_sha256") or "")
    assert PATRON_SHA256.match(huella)
    generado = str(artefacto.get("generado_at") or "")
    assert generado.endswith("Z")
    datetime.fromisoformat(generado.replace("Z", "+00:00"))
