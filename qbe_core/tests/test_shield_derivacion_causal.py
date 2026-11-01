# -*- coding: utf-8 -*-
"""🏆 THE SHIELD — JUEZ INMUTABLE DEL MOTOR DE VARIABLES CAUSALES.

Nodo: `[LN-QBE-146]` Motor de Derivación de Variables Causales.
Base de Gobierno: `docs/LOGIC.md` §19 y catálogo `[LN-QBE-120]` §2.1.

Evidencia fáctica: los 49 eventos de `América 3-3 Monterrey` (J16 Clausura 2016)
persistidos en `qbe_historico.db` (match_id `fs_2015_2016_z85264`).

Si la bóveda no está presente (clon limpio), los casos fácticos se declaran
omitidos; el resto del Juez corre igual.
"""

from __future__ import annotations

import ast
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from src.core.sovereign.derivar_variables_causales import (
    DerivacionError,
    LADOS,
    VARIABLES,
    VARIABLES_DERIVADAS,
    VARIABLES_SIN_EVIDENCIA,
    derivar_variables_causales,
)

RAIZ = Path(__file__).resolve().parents[2]
BOVEDA = RAIZ / "qbe_observatory" / "data" / "qbe_historico.db"
MATCH_AME_MTY = "fs_2015_2016_z85264"
MODULO = RAIZ / "qbe_core" / "src" / "core" / "sovereign" / "derivar_variables_causales.py"


# ── Utilidades ──────────────────────────────────────────────────────────────────────────────
def _evento(
    orden: int,
    lado: str,
    tipo: str,
    minuto: Optional[int] = None,
    agregado: Optional[int] = None,
) -> Dict[str, Any]:
    return {
        "evento_id": f"e{orden}",
        "lado": lado,
        "tipo": tipo,
        "minuto": minuto,
        "minuto_agregado": agregado,
        "orden_dom": orden,
    }


def _eventos_boveda(match_id: str) -> List[Dict[str, Any]]:
    if not BOVEDA.is_file():
        pytest.skip("bóveda no disponible en este entorno")
    conexion = sqlite3.connect(f"file:{BOVEDA.as_posix()}?mode=ro", uri=True)
    try:
        filas = conexion.execute(
            "SELECT evento_id, orden_dom, minuto_texto, minuto_entero, minuto_agregado, "
            "periodo, tipo_evento, equipo, descripcion "
            "FROM historical_match_events WHERE match_id = ? ORDER BY orden_dom",
            (match_id,),
        ).fetchall()
    finally:
        conexion.close()
    if not filas:
        pytest.skip(f"el partido {match_id} no está en la bóveda")
    return [
        {
            "evento_id": fila[0],
            "orden_dom": fila[1],
            "minuto_texto": fila[2],
            "minuto": fila[3],
            "minuto_agregado": fila[4],
            "periodo": fila[5],
            "tipo": fila[6],
            "lado": fila[7],
            "descripcion": fila[8],
        }
        for fila in filas
    ]


# ── Contrato del vector ────────────────────────────────────────────────────────────────────
def test_invarianza_el_vector_declara_las_32_variables() -> None:
    """[INV 1] Siempre 32 claves V01…V32, cada una con los dos lados."""
    eventos = _eventos_boveda(MATCH_AME_MTY)
    vector = derivar_variables_causales(MATCH_AME_MTY, eventos)

    assert list(vector) == list(VARIABLES)
    assert len(vector) == 32
    for variable in VARIABLES:
        assert set(vector[variable]) == set(LADOS), variable
        for lado in LADOS:
            valor = vector[variable][lado]
            assert valor is None or isinstance(valor, float), (variable, lado, valor)


def test_particion_exacta_derivadas_y_sin_evidencia() -> None:
    """[INV 2] 9 derivadas + 23 SIN EVIDENCIA = 32, sin solapamiento."""
    assert len(VARIABLES_DERIVADAS) == 9
    assert len(VARIABLES_SIN_EVIDENCIA) == 23
    assert set(VARIABLES_DERIVADAS) & set(VARIABLES_SIN_EVIDENCIA) == set()
    assert set(VARIABLES_DERIVADAS) | set(VARIABLES_SIN_EVIDENCIA) == set(VARIABLES)


def test_sin_evidencia_no_es_cero() -> None:
    """[INV 3] Una variable no inferible es `None`, jamás `0.0` fabricado."""
    vector = derivar_variables_causales("m1", [_evento(0, "local", "gol", 10)])

    assert vector["V01"] == {"local": None, "visita": None}
    assert vector["V06"]["local"] is None and vector["V12"]["visita"] is None
    assert vector["V20"] == {"local": 1.0, "visita": 0.0}


# ── Casos fácticos: América 3-3 Monterrey (49 eventos) ────────────────────────────────────
def test_ame_mty_faltas_tiros_y_tarjetas_coinciden_con_los_49_eventos() -> None:
    """[INV 4] Los conteos derivados cuadran contra la línea de tiempo real."""
    eventos = _eventos_boveda(MATCH_AME_MTY)
    assert len(eventos) == 49

    tipos = [evento["tipo"] for evento in eventos]
    assert tipos.count("falta") == 8
    assert tipos.count("tiro_a_gol") == 12
    assert tipos.count("gol") == 5
    assert tipos.count("gol_penal") == 1
    assert tipos.count("corner") == 4
    assert tipos.count("tarjeta_amarilla") == 7
    assert tipos.count("tarjeta_roja") == 0
    assert tipos.count("penal") == 1

    vector = derivar_variables_causales(MATCH_AME_MTY, eventos)
    assert vector["V05"] == {"local": 4.0, "visita": 4.0}
    # Enmienda Sprint 44: el penal del 10' cuenta como remate al arco (18 totales).
    assert vector["V07"] == {"local": 10.0, "visita": 8.0}   # 7+3 y 5+2+1
    assert vector["V13"] == {"local": 8.0, "visita": 10.0}   # dual exacto
    assert vector["V07"]["local"] + vector["V07"]["visita"] == 18.0
    assert vector["V23"] == {"local": 3.0, "visita": 1.0}
    assert vector["V24"] == {"local": 0.0, "visita": 1.0}
    assert vector["V25"] == {"local": 4.0, "visita": 3.0}


def test_ame_mty_pelota_parada_y_porteria() -> None:
    """[INV 5] Pelota parada y valla invicta: 1-1 en goles a balón parado."""
    vector = derivar_variables_causales(MATCH_AME_MTY, _eventos_boveda(MATCH_AME_MTY))

    # América 36' tras córner 35'; Monterrey 10' tras penal 7'.
    assert vector["V21"] == {"local": 1.0, "visita": 1.0}
    assert vector["V22"] == {"local": 1.0, "visita": 1.0}
    assert vector["V20"] == {"local": 0.0, "visita": 0.0}

    sin_evidencia = [v for v in VARIABLES_SIN_EVIDENCIA if vector[v]["local"] is None]
    assert len(sin_evidencia) == 23


# ── Reglas puras ───────────────────────────────────────────────────────────────────────────
def test_pelota_parada_exige_proximidad_y_mismo_lado() -> None:
    """[INV 6] Córner previo dentro de 5 min y del mismo lado; si no, no cuenta."""
    cerca = [
        _evento(2, "local", "corner", 35),
        _evento(1, "local", "gol", 36),
        _evento(0, "local", "final_partido"),
    ]
    assert derivar_variables_causales("m", cerca)["V21"]["local"] == 1.0

    lejos = [
        _evento(2, "local", "corner", 20),
        _evento(1, "local", "gol", 36),
        _evento(0, "local", "final_partido"),
    ]
    assert derivar_variables_causales("m", lejos)["V21"]["local"] == 0.0

    ajeno = [
        _evento(2, "visita", "corner", 35),
        _evento(1, "local", "gol", 36),
        _evento(0, "local", "final_partido"),
    ]
    assert derivar_variables_causales("m", ajeno)["V21"]["local"] == 0.0


def test_orden_dom_es_cronologico_inverso() -> None:
    """[INV 7] Un córner posterior en el tiempo (orden_dom mayor) no precede al gol."""
    eventos = [
        _evento(0, "local", "final_partido"),
        _evento(1, "local", "gol", 78),
        _evento(2, "local", "corner", 80),
    ]
    assert derivar_variables_causales("m", eventos)["V21"]["local"] == 0.0


def test_penal_convertido_cuenta_como_pelota_parada() -> None:
    """[INV 8] Penal señalado 3 minutos antes del gol: pelota parada."""
    eventos = [
        _evento(0, "visita", "final_partido"),
        _evento(1, "visita", "gol_penal", 10),
        _evento(2, "visita", "penal", 7),
    ]
    vector = derivar_variables_causales("m", eventos)
    assert vector["V21"]["visita"] == 1.0
    assert vector["V22"]["local"] == 1.0


# ── Sad Paths ──────────────────────────────────────────────────────────────────────────────
def test_sad_path_lista_vacia() -> None:
    """[SAD 1] Sin eventos no hay vector: excepción de dominio."""
    with pytest.raises(DerivacionError):
        derivar_variables_causales(MATCH_AME_MTY, [])


@pytest.mark.parametrize(
    "evento",
    [
        {"orden_dom": 0, "tipo": "gol"},                       # sin lado
        {"orden_dom": 0, "lado": "local"},                     # sin tipo
        {"orden_dom": 0, "lado": "arbitro", "tipo": "gol"},    # lado fuera de dominio
        {"lado": "local", "tipo": "gol"},                      # sin orden_dom
        {"orden_dom": 0, "lado": "local", "tipo": ""},         # tipo vacío
    ],
)
def test_sad_path_evento_fuera_de_contrato(evento: Dict[str, Any]) -> None:
    """[SAD 2] Evento sin contrato: `DerivacionError`, nunca vector parcial."""
    with pytest.raises(DerivacionError):
        derivar_variables_causales("m", [evento])


def test_sad_path_match_id_invalido() -> None:
    """[SAD 3] `match_id` vacío o no textual: excepción de dominio."""
    for identificador in ("", "   ", None, 7):
        with pytest.raises(DerivacionError):
            derivar_variables_causales(identificador, [_evento(0, "local", "gol", 1)])  # type: ignore[arg-type]


# ── Pureza y gobierno ─────────────────────────────────────────────────────────────────────
def test_pureza_ast_sin_io_ni_persistencia() -> None:
    """[INV 9] El motor no importa I/O, red ni persistencia (AST)."""
    assert MODULO.is_file(), f"Falta el motor: {MODULO}"
    arbol = ast.parse(MODULO.read_text(encoding="utf-8"))
    prohibidos = {"sqlite3", "sqlalchemy", "requests", "playwright", "pathlib", "os", "io"}
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            for alias in nodo.names:
                assert alias.name.split(".")[0] not in prohibidos, alias.name
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            assert nodo.module.split(".")[0] not in prohibidos, nodo.module
        elif isinstance(nodo, ast.Call) and getattr(nodo.func, "id", None) == "open":
            pytest.fail("[LN-QBE-146] El motor puro no puede abrir archivos")


def test_legislacion_146_anclada_en_la_base_de_gobierno() -> None:
    """[INV 10] El nodo existe en LOGIC.md y en ID_REGISTRY.md."""
    logica = (RAIZ / "docs" / "LOGIC.md").read_text(encoding="utf-8")
    registro = (RAIZ / "docs" / "ID_REGISTRY.md").read_text(encoding="utf-8")

    assert "[LN-QBE-146]" in logica
    assert "[LN-QBE-146]" in registro
    assert "historical_match_causal_vars" in logica
