"""Refresco atómico del snapshot de backtesting (fuera de la app)."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional


def edad_snapshot(ruta: Path) -> Optional[float]:
    """Edad en segundos; `None` si el snapshot no existe."""
    if not ruta.is_file():
        return None
    return max(0.0, __import__("time").time() - ruta.stat().st_mtime)


def snapshot_fresco(ruta: Path, max_age_minutes: int = 60) -> bool:
    edad = edad_snapshot(ruta)
    return edad is not None and edad <= max_age_minutes * 60


def refrescar_snapshot(
    origen: Path,
    destino: Path,
    max_age_minutes: int = 60,
) -> Dict[str, Any]:
    """Copia online con `Connection.backup`, publica atómicamente y reporta frescura."""
    origen = Path(origen).resolve()
    destino = Path(destino).resolve()
    if not origen.is_file():
        raise FileNotFoundError(f"BD origen no disponible: {origen}")

    destino.parent.mkdir(parents=True, exist_ok=True)
    temporal = destino.with_name(destino.name + ".tmp")

    con_origen = sqlite3.connect(f"file:{origen.as_posix()}?mode=ro", uri=True)
    con_destino = sqlite3.connect(temporal.as_posix())
    try:
        con_origen.backup(con_destino)
    finally:
        con_destino.close()
        con_origen.close()

    os.replace(temporal, destino)
    return {
        "origen": str(origen),
        "destino": str(destino),
        "edad_segundos": edad_snapshot(destino),
        "fresco": snapshot_fresco(destino, max_age_minutes),
        "max_age_minutos": max_age_minutes,
    }
