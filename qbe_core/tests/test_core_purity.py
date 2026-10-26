"""The Shield — pureza de `qbe_core`.

El auditor de coherencia pertenece a Ingesta (`qbe_ingestion`). El núcleo no debe
contener módulos con I/O, CLI ni imports de daemons.
"""

from __future__ import annotations

from pathlib import Path

CORE = Path(__file__).resolve().parents[1] / "src" / "core"


def test_coherence_auditor_no_vive_en_qbe_core() -> None:
    assert not (CORE / "coherence_auditor.py").exists(), (
        "coherence_auditor.py volvió a qbe_core; debe vivir en qbe_ingestion"
    )
