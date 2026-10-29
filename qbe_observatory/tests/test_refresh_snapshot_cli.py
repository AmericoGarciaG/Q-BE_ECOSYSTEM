# -*- coding: utf-8 -*-
"""Juez de regresión del CLI de refresco del snapshot.

El commit de autonomía retiró `BASELINE_ROOT` de `app.config` y dejó el script
importando una constante inexistente. Este juez fija el contrato: la fuente por
omisión es la bóveda viva DENTRO del monorepo (`LIVE_DB`) y el CLI puede
construirse sin tocar el monolito.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def test_parser_construye_sin_baseline_root() -> None:
    import importlib.util

    from app import config

    ruta = PROJECT_ROOT / "scripts" / "refresh_snapshot.py"
    spec = importlib.util.spec_from_file_location("refresh_snapshot_cli_test", ruta)
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)

    args = modulo._parser().parse_args(["--max-age-minutes", "60"])

    assert args.source == config.LIVE_DB
    assert args.dest == config.BACKTESTING_SNAPSHOT


def test_live_db_por_omision_vive_dentro_del_monorepo() -> None:
    from app import config

    assert config.LIVE_DB.is_relative_to(config.ECOSYSTEM_ROOT)
