# -*- coding: utf-8 -*-
"""
The Shield — Data Nexus (Fase 4, Slice 4A)

Certifica:
  1. Los tres daemons extraídos importan desde `qbe_ingestion`.
  2. El gateway apunta a una base efímera sin tocar la bóveda viva.
  3. `qbe_business` no importa ingesta.
"""

from __future__ import annotations

import ast
import os
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ECOSYSTEM_ROOT = PROJECT_ROOT.parent
BASELINE_ROOT = ECOSYSTEM_ROOT.parent / "Q_BE_CD_WEB"
SNAPSHOT = BASELINE_ROOT / "data" / "output" / "backups" / "qbe_database.baseline.db"
BUSINESS_SRC = ECOSYSTEM_ROOT / "qbe_business" / "src"


def _copiar_snapshot(destino: Path) -> None:
    origen = sqlite3.connect(f"file:{SNAPSHOT.resolve().as_posix()}?mode=ro", uri=True)
    copia = sqlite3.connect(destino.as_posix())
    try:
        origen.backup(copia)
    finally:
        copia.close()
        origen.close()


def test_daemons_importan_y_apuntan_a_bd_efimera(tmp_path: Path) -> None:
    assert SNAPSHOT.is_file(), f"No existe el snapshot G0: {SNAPSHOT}"
    base = tmp_path / "qbe_ingestion.db"
    _copiar_snapshot(base)

    url = f"sqlite:///{base.as_posix()}"
    os.environ["DATABASE_URL"] = url
    os.environ["KYBERN_NO_SCRAPE"] = "1"

    from src.config import settings

    settings.DATABASE_URL = url

    from src.storage.gateway import PersistenceGateway

    if PersistenceGateway._instance is not None:
        try:
            PersistenceGateway._instance.engine.dispose()
        except Exception:
            pass
        PersistenceGateway._instance = None

    gateway = PersistenceGateway()
    assert "qbe_ingestion.db" in str(gateway.engine.url)

    import src.ingestion.daemons.centinela_deportivo as deportivo
    import src.ingestion.daemons.centinela_mercado as mercado
    import src.ingestion.daemons.centinela_progol as progol

    assert "qbe_ingestion" in Path(deportivo.__file__).as_posix()
    assert callable(deportivo.main)
    assert callable(mercado.main)
    assert callable(progol.sincronizar_progol_en_sqlite)


def test_business_no_importa_ingesta() -> None:
    assert BUSINESS_SRC.is_dir()
    prohibidos = ("src.ingestion", "qbe_ingestion")
    violaciones = []
    for archivo in sorted(BUSINESS_SRC.rglob("*.py")):
        arbol = ast.parse(archivo.read_text(encoding="utf-8"), filename=str(archivo))
        for nodo in ast.walk(arbol):
            modulos = []
            if isinstance(nodo, ast.Import):
                modulos = [alias.name for alias in nodo.names]
            elif isinstance(nodo, ast.ImportFrom) and nodo.module:
                modulos = [nodo.module]
            for modulo in modulos:
                if modulo.startswith(prohibidos):
                    violaciones.append(f"{archivo}:{nodo.lineno}: {modulo}")
    assert not violaciones, "Business importa Ingesta:\n" + "\n".join(violaciones)
