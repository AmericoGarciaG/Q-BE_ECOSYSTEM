# -*- coding: utf-8 -*-
"""🏆 THE SHIELD — FRESCURA DEL SNAPSHOT (UMBRAL 30 MIN).

Certifica el contrato de presentación del Observatorio: un snapshot con más de
30 minutos se declara `Obsoleto`; uno de 29 minutos permanece `Fresco`.
El cálculo es el mismo que consumen `backtesting_ui`, `calibration_view` y
`/api/observatory/snapshot/status`.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ / "qbe_observatory") not in sys.path:
    sys.path.insert(0, str(RAIZ / "qbe_observatory"))

from app.services.snapshot_refresh import edad_snapshot, snapshot_fresco  # noqa: E402

UMBRAL_MINUTOS = 30


def _envejecer(ruta: Path, minutos: float) -> None:
    instante = time.time() - (minutos * 60.0)
    os.utime(ruta, (instante, instante))


def test_snapshot_de_31_minutos_es_obsoleto(tmp_path: Path) -> None:
    """[DES-QBE-077] 31 min > 30 ⇒ `fresco=False` (badge `Obsoleto`)."""
    ruta = tmp_path / "observatory_snapshot.db"
    ruta.write_bytes(b"snapshot")
    _envejecer(ruta, 31)
    assert edad_snapshot(ruta) is not None
    assert snapshot_fresco(ruta, UMBRAL_MINUTOS) is False


def test_snapshot_de_29_minutos_sigue_fresco(tmp_path: Path) -> None:
    """[DES-QBE-077] 29 min ≤ 30 ⇒ `fresco=True` (badge `Fresco`)."""
    ruta = tmp_path / "observatory_snapshot.db"
    ruta.write_bytes(b"snapshot")
    _envejecer(ruta, 29)
    assert snapshot_fresco(ruta, UMBRAL_MINUTOS) is True
