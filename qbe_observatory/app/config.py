"""Configuración del Observatorio — rutas resueltas, nunca dependientes del CWD."""

from __future__ import annotations

import os
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent                 # qbe_observatory/
ECOSYSTEM_ROOT = PROJECT_ROOT.parent          # Q_BE_ECOSYSTEM/
DATA_DIR = PROJECT_ROOT / "data"              # qbe_observatory/data/

# Autonomía absoluta: el histórico vive DENTRO del Observatorio, nunca en la
# carpeta del monolito. `QBE_HISTORICO_DB` permite fijar la ruta en despliegues
# (contenedor, volumen montado) sin tocar código; `OBS_HISTORICO_DB` sobrevive
# como alias legado de Fase 2 y queda subordinado al nombre canónico.
HISTORICO_DB = Path(
    os.getenv("QBE_HISTORICO_DB")
    or os.getenv("OBS_HISTORICO_DB")
    or str(DATA_DIR / "qbe_historico.db")
).resolve()

LIVE_SNAPSHOT = Path(
    os.getenv("OBS_LIVE_SNAPSHOT", str(PROJECT_ROOT / "data" / "live_snapshot.db"))
).resolve()

# Bóveda viva del monorepo: fuente del refresco atómico del snapshot. Vive dentro
# de Q_BE_ECOSYSTEM/ para preservar la autonomía del Observatorio; un despliegue
# puede sustituirla con `QBE_LIVE_DB` sin tocar código.
LIVE_DB = Path(
    os.getenv("QBE_LIVE_DB")
    or os.getenv("OBS_LIVE_DB")
    or str(ECOSYSTEM_ROOT / "data" / "qbe_database.db")
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
