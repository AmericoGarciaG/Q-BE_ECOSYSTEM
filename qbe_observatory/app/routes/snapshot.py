"""Estado de frescura del snapshot (solo lectura)."""

from __future__ import annotations

from fastapi import APIRouter

from app import config
from app.services.snapshot_refresh import edad_snapshot, snapshot_fresco

router = APIRouter(prefix="/api/observatory/snapshot", tags=["Snapshot"])


@router.get("/status")
def estado_snapshot() -> dict:
    edad = edad_snapshot(config.BACKTESTING_SNAPSHOT)
    return {
        "snapshot": str(config.BACKTESTING_SNAPSHOT),
        "edad_segundos": edad,
        "fresco": snapshot_fresco(config.BACKTESTING_SNAPSHOT, 60),
        "max_age_minutos": 60,
    }
