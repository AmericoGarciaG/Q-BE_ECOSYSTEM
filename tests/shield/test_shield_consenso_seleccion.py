# -*- coding: utf-8 -*-
"""🏆 THE SHIELD — `[DES-QBE-076]` SELECCIÓN DE FUENTES DEL CONSENSO.

Certifica:
* el default activa los tres casinos + Q-BE;
* una selección explícita conserva solo fuentes conocidas;
* sin fuentes seleccionadas la vista queda vacía;
* un bloque Q-BE-only se ordena sin exigir la fila maestra Consenso.

`[SPRINT-47]` D10: la regla de suplantación `_etiqueta_proveedor` (que rotulaba
un casino como «FootyStats») fue erradicada junto con su código muerto; este
Juez verifica su ausencia en lugar de su comportamiento.
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ / "qbe_observatory") not in sys.path:
    sys.path.insert(0, str(RAIZ / "qbe_observatory"))

import app.services.sabiduria_view as sabiduria_view  # noqa: E402
from app.services.consenso_view import _normalizar_seleccion  # noqa: E402
from src.observatory.sabiduria_masas import construir_tabla_sabiduria  # noqa: E402


def test_default_activa_casinos_y_qbe() -> None:
    seleccion = _normalizar_seleccion([], filtros=False)
    assert seleccion == ["caliente", "novibet", "betway", "qbe"]


def test_seleccion_explicita_y_vacia() -> None:
    assert _normalizar_seleccion(["caliente", "novibet", "qbe"], filtros=True) == [
        "caliente",
        "novibet",
        "qbe",
    ]
    assert _normalizar_seleccion([], filtros=True) == []
    assert _normalizar_seleccion(["inventado", "q-be"], filtros=True) == ["qbe"]


def test_la_regla_de_suplantacion_fue_erradicada() -> None:
    """`[SPRINT-47]` D10: ningún casino puede heredar la etiqueta de otra fuente."""
    assert not hasattr(sabiduria_view, "_etiqueta_proveedor")
    assert not hasattr(sabiduria_view, "ETIQUETA_PROVEEDOR")
    assert not hasattr(sabiduria_view, "ORIGENES_PROPIOS")


def test_bloque_sin_casinos_solo_qbe_no_exige_consenso() -> None:
    filas = construir_tabla_sabiduria(
        [{"fuente": "Q-BE", "brier": 0.2159, "alpha_pct": 0.0, "peso": None}],
        exigir_consenso=False,
    )
    assert len(filas) == 1
    assert filas[0]["fuente"] == "Q-BE"
    assert filas[0]["es_consenso"] is False
