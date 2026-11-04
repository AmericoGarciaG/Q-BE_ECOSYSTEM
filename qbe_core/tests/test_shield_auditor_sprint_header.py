# -*- coding: utf-8 -*-
"""🏆 THE SHIELD — JUEZ INMUTABLE DEL SPRINT DINÁMICO DEL AUDITOR.

Nodo: `[LN-QBE-139]` Auditor de Paridad Estática AST.
Base de Gobierno: `docs/GOVERNANCE.md` §3.5.1 y `docs/LOGIC.md` `[LN-QBE-139]`.

El Juez certifica que la cabecera de `GL_update.md` no contiene un sprint
hardcodeado y que el Auditor resuelve el sprint desde `AKT.md` o, si el activo
está reiniciado, desde el acta más reciente de `history/`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from scripts.auditoria.auditar_paridad_bg import (  # noqa: E402
    AuditarParidadBG,
    _resolver_sprint_activo,
)


def _preparar_raiz(
    tmp_path: Path,
    *,
    akt: str | None = "**Sprint:** `SPRINT-77-CAUSAL`<br>\n",
    historicos: tuple[str, ...] = (),
) -> Path:
    (tmp_path / "docs" / "KTP" / "history").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs" / "ID_REGISTRY.md").write_text(
        "| `[LN-QBE-001]` | LOGIC | `docs/LOGIC.md` | Nodo de prueba | SELLADO |\n",
        encoding="utf-8",
    )
    if akt is not None:
        (tmp_path / "docs" / "KTP" / "AKT.md").write_text(akt, encoding="utf-8")
    for nombre in historicos:
        (tmp_path / "docs" / "KTP" / "history" / nombre).write_text(
            "# acta histórica de prueba\n", encoding="utf-8"
        )
    return tmp_path


def test_resuelve_sprint_desde_akt(tmp_path: Path) -> None:
    """[INV 1] El AKT manda: el sprint se toma de su cabecera."""
    raiz = _preparar_raiz(tmp_path)
    assert _resolver_sprint_activo(raiz) == "SPRINT-77-CAUSAL"


def test_fallback_al_acta_mas_reciente_de_history(tmp_path: Path) -> None:
    """[INV 2] AKT reiniciado: usa el acta más reciente por fecha del nombre."""
    raiz = _preparar_raiz(
        tmp_path,
        akt="**Sprint:** `PENDIENTE DE ASIGNACIÓN POR EL DIRECTOR`<br>\n",
        historicos=(
            "AKT_2026-10-31_SPRINT-41-TRANSICION-Y-CONSISTENCIA-BG.md",
            "AKT_2026-11-01_SPRINT-45-EXPANSION-CAUSAL-Y-RESCATE-EN-VIVO.md",
        ),
    )
    assert _resolver_sprint_activo(raiz) == "SPRINT-45"


def test_fail_loud_sin_akt_ni_history(tmp_path: Path) -> None:
    """[SAD 1] Sin fuente de sprint, RuntimeError; nunca un literal de rescate."""
    raiz = _preparar_raiz(tmp_path, akt=None)
    with pytest.raises(RuntimeError):
        _resolver_sprint_activo(raiz)


def test_bandeja_inyecta_el_sprint_resuelto_y_no_hardcode(tmp_path: Path) -> None:
    """[INV 3] La cabecera de GL_update.md usa el sprint resuelto."""
    raiz = _preparar_raiz(tmp_path)
    auditor = AuditarParidadBG(
        raiz=raiz, registro_path=raiz / "docs" / "ID_REGISTRY.md"
    )
    salida = raiz / "GL_update.md"

    auditor.generar_bandeja([], salida)

    texto = salida.read_text(encoding="utf-8")
    assert "- **Sprint:** `SPRINT-77-CAUSAL`" in texto
    assert "SPRINT-41" not in texto
