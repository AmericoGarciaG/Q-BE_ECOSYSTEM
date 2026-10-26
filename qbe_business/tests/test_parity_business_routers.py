# -*- coding: utf-8 -*-
"""
The Shield — Paridad funcional de routers de Business (Slice 3A).

Juez Golden Master: el `POST /api/markets/sportsbook/portfolio/generate` de
`qbe_business` debe devolver EXACTAMENTE el mismo JSON que el monolito congelado
para el mismo snapshot y payload.

Nace RED: los routers aún no están portados a `qbe_business`.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ECOSYSTEM_ROOT = PROJECT_ROOT.parent
BASELINE_ROOT = ECOSYSTEM_ROOT.parent / "Q_BE_CD_WEB"

SNAPSHOT = BASELINE_ROOT / "data" / "output" / "backups" / "qbe_database.baseline.db"
GOLDEN = Path(__file__).with_name("golden_master_portfolio.json")

PAYLOAD = {
    "league_id": 262,
    "selected_match_ids": ["LIGAMX-J14-09"],
    "bankroll": 1000.0,
    "target_certeza": 0.80,
    "operador": "caliente",
    "gamma_slider": 0.67,
    "modo_cobertura": "DEF",
}


def _copiar_snapshot(destino: Path) -> None:
    """Copia consistente del snapshot G0 (incluye WAL consolidado)."""
    assert SNAPSHOT.is_file(), f"No existe el snapshot G0: {SNAPSHOT}"
    origen = sqlite3.connect(f"file:{SNAPSHOT.resolve().as_posix()}?mode=ro", uri=True)
    copia = sqlite3.connect(destino.as_posix())
    try:
        origen.backup(copia)
    finally:
        copia.close()
        origen.close()


def test_paridad_generate_portfolio(tmp_path: Path) -> None:
    """Golden Master exacto del generador de cartera sportsbook."""
    assert GOLDEN.is_file(), f"No existe el Golden Master: {GOLDEN}"
    base_efimera = tmp_path / "qbe_parity.db"
    _copiar_snapshot(base_efimera)

    url = f"sqlite:///{base_efimera.as_posix()}"
    os.environ["DATABASE_URL"] = url
    os.environ["KYBERN_NO_SCRAPE"] = "1"

    # La configuración y el singleton deben apuntar a la copia, no a la bóveda viva.
    from src.config import settings

    settings.DATABASE_URL = url

    from src.storage.gateway import PersistenceGateway

    if PersistenceGateway._instance is not None:
        try:
            PersistenceGateway._instance.engine.dispose()
        except Exception:
            pass
        PersistenceGateway._instance = None

    from src.web.app import app

    with TestClient(app) as cliente:
        respuesta = cliente.post(
            "/api/markets/sportsbook/portfolio/generate",
            json=PAYLOAD,
        )

    assert respuesta.status_code == 200, (
        f"El router no existe o falló: status={respuesta.status_code} "
        f"body={respuesta.text[:500]}"
    )

    esperado = json.loads(GOLDEN.read_text(encoding="utf-8"))
    obtenido = respuesta.json()
    assert obtenido == esperado, "El JSON de qbe_business difiere del Golden Master"
