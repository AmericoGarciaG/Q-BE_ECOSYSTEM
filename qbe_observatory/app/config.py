"""Configuración del Observatorio — rutas resueltas, nunca dependientes del CWD."""

from __future__ import annotations

import os
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent                 # qbe_observatory/
ECOSYSTEM_ROOT = PROJECT_ROOT.parent          # Q_BE_ECOSYSTEM/
BASELINE_ROOT = ECOSYSTEM_ROOT.parent / "Q_BE_CD_WEB"

HISTORICO_DB = Path(
    os.getenv("OBS_HISTORICO_DB", str(BASELINE_ROOT / "data" / "qbe_historico.db"))
).resolve()

LIVE_SNAPSHOT = Path(
    os.getenv("OBS_LIVE_SNAPSHOT", str(PROJECT_ROOT / "data" / "live_snapshot.db"))
).resolve()

BACKTESTING_SNAPSHOT = Path(
    os.getenv(
        "OBS_BACKTESTING_SNAPSHOT",
        str(PROJECT_ROOT / "data" / "observatory_snapshot.db"),
    )
).resolve()

API_TOKEN = os.getenv("OBS_API_TOKEN", "").strip()

OBS_HOST = os.getenv("OBS_HOST", "127.0.0.1")
OBS_PORT = int(os.getenv("OBS_PORT", "8001"))
