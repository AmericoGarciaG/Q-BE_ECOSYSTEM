# -*- coding: utf-8 -*-
"""
🏆 THE SHIELD — OBSERVATORY AUTONOMY & ISOLATION SUITE
Juez Inmutable: [ARCH-ECOSYSTEM-OBSERVATORY-AUTONOMY]
Base de Gobierno: Kybern Framework v13.5

Certifica que `qbe_observatory` es desplegable como unidad independiente:

* **INVARIANZA 1 — Autonomía de configuración:** `config.HISTORICO_DB` resuelve
  dentro del árbol de `Q_BE_ECOSYSTEM`; ninguna ruta por omisión escapa del
  monorepo.
* **INVARIANZA 2 — No contaminación:** ningún archivo `.py` del Observatorio
  cita al monolito legado (la documentación narrativa `.md` queda fuera del
  alcance, decisión D1 del expediente).
* **INVARIANZA 3 — Aprovisionamiento:** el histórico existe físicamente dentro
  de `qbe_observatory/data/`, no es un placeholder y abre íntegro en modo `ro`.

El token que delata el cordón umbilical se COMPONE en tiempo de ejecución: si se
escribiera literal en este archivo, la INVARIANZA 2 acusaría al propio juez.
"""

from __future__ import annotations

import contextlib
import os
import sqlite3
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ECOSYSTEM_ROOT = PROJECT_ROOT.parent

# `from qbe_observatory.app import config` exige la raíz del monorepo en sys.path
# tanto si pytest se invoca desde Q_BE_ECOSYSTEM como desde qbe_observatory/.
if str(ECOSYSTEM_ROOT) not in sys.path:
    sys.path.insert(0, str(ECOSYSTEM_ROOT))

TOKEN_MONOLITO = "Q_BE_CD" + "_WEB"  # nunca literal: el juez se escanea a sí mismo


def test_invarianza_historico_db_apunta_dentro_del_ecosistema():
    """[INVARIANZA 1 - AUTONOMÍA]: HISTORICO_DB no debe apuntar fuera del monorepo."""
    from qbe_observatory.app import config

    crudo = str(config.HISTORICO_DB)
    ruta_historico = Path(config.HISTORICO_DB).resolve()

    # 1. Comprobar que no contiene el token del monolito ni en crudo ni resuelto.
    assert TOKEN_MONOLITO not in crudo, (
        f"Cordón umbilical detectado en config.HISTORICO_DB: {crudo}"
    )
    assert TOKEN_MONOLITO not in str(ruta_historico)

    # 2. Comprobar que la ruta resuelta está dentro del árbol de Q_BE_ECOSYSTEM.
    try:
        ruta_historico.relative_to(ECOSYSTEM_ROOT)
    except ValueError:
        pytest.fail(f"HISTORICO_DB apunta fuera de Q_BE_ECOSYSTEM: {ruta_historico}")


def test_invarianza_cero_referencias_a_monolito_en_codigo_observatorio():
    """[INVARIANZA 2 - NO CONTAMINACIÓN]: ningún `.py` cita al monolito legado."""
    archivos_con_fuga: list[str] = []

    for raiz, carpetas, archivos in os.walk(PROJECT_ROOT):
        # Ignorar git, caches y artefactos temporales.
        carpetas[:] = [
            c for c in carpetas if c not in {".git", "__pycache__", ".pytest_cache"}
        ]
        for archivo in archivos:
            if not archivo.endswith(".py"):
                continue
            ruta_completa = Path(raiz) / archivo
            try:
                contenido = ruta_completa.read_text(encoding="utf-8", errors="ignore")
            except OSError:  # binarios ilegibles no son código ejecutable
                continue
            if TOKEN_MONOLITO in contenido:
                archivos_con_fuga.append(str(ruta_completa.relative_to(PROJECT_ROOT)))

    assert not archivos_con_fuga, (
        f"Archivos con referencias al monolito legado: {archivos_con_fuga}"
    )


def test_invarianza_archivo_historico_existe_en_data_observatorio():
    """[INVARIANZA 3 - APROVISIONAMIENTO]: el histórico vive dentro del Observatorio."""
    from qbe_observatory.app import config

    ruta_archivo = Path(config.HISTORICO_DB)
    assert ruta_archivo.exists(), (
        f"Falta el archivo de base de datos histórica en {ruta_archivo}"
    )
    assert ruta_archivo.stat().st_size > 1024 * 1024, (
        "El archivo histórico no puede ser un placeholder vacío"
    )

    # Integridad física: el binario abre en solo lectura y supera `quick_check`.
    with contextlib.closing(
        sqlite3.connect(f"file:{ruta_archivo.as_posix()}?mode=ro", uri=True)
    ) as conexion:
        chequeo = conexion.execute("PRAGMA quick_check").fetchone()
        assert str(chequeo[0]).strip().lower() == "ok", f"quick_check={chequeo}"
        total = conexion.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
    assert int(total) > 0, "El histórico aprovisionado no porta partidos"
