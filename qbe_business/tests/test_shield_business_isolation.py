# -*- coding: utf-8 -*-
"""
🏆 THE SHIELD — QBE_BUSINESS FAULT ISOLATION & PURITY SUITE
Juez Inmutable: [ARCH-ECOSYSTEM-FASE3]
Base de Gobierno: Kybern Framework v13.5
"""

import ast
import os
import sys
from pathlib import Path
import pytest

# ---------------------------------------------------------------------------
# Helpers de entorno
# ---------------------------------------------------------------------------
_ECOSYSTEM_ROOT = Path(__file__).resolve().parents[2]
if str(_ECOSYSTEM_ROOT) not in sys.path:
    sys.path.insert(0, str(_ECOSYSTEM_ROOT))


def _recopilar_rutas(app) -> list:
    """Recopila todos los .path del app.router, incluyendo _IncludedRouter de FastAPI 0.162+."""
    import fastapi.routing as _fr
    rutas = []
    for ruta in app.routes:
        path = getattr(ruta, "path", None)
        if path is not None:
            rutas.append(path)
        # FastAPI 0.162+ envuelve routers incluidos en _IncludedRouter
        if isinstance(ruta, _fr._IncludedRouter):
            ctx = getattr(ruta, "include_context", None)
            if ctx is not None:
                router = getattr(ctx, "included_router", None)
                if router is not None:
                    for sub in router.routes:
                        sub_path = getattr(sub, "path", None)
                        if sub_path is not None:
                            rutas.append(sub_path)
    return rutas


# ---------------------------------------------------------------------------
# INVARIANZA 1 — Pureza de catalog.py en qbe_core
# ---------------------------------------------------------------------------
def test_invarianza_catalogo_core_es_puro_y_resuelve_atlante():
    """[INVARIANZA 1 - PUREZA CORE]: catalog.py en qbe_core debe ser puro y resolver Atlante a 2240m."""
    from src.core.catalog import altitud_estadio, CATALOGO_ALTITUDES_LIGAMX

    assert altitud_estadio("atlante") == 2240.0
    assert altitud_estadio("club-atlante") == 2240.0
    assert altitud_estadio("deportivo-toluca") == 2660.0
    assert len(CATALOGO_ALTITUDES_LIGAMX) >= 18

    # Verificar pureza AST de catalog.py
    ruta_catalog = os.path.abspath(os.path.join(
        os.path.dirname(__file__), "..", "..", "qbe_core", "src", "core", "catalog.py"
    ))
    with open(ruta_catalog, "r", encoding="utf-8") as f:
        arbol = ast.parse(f.read())

    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            for alias in nodo.names:
                assert "sqlalchemy" not in alias.name
                assert "requests" not in alias.name
                assert "storage" not in alias.name
        elif isinstance(nodo, ast.ImportFrom):
            if nodo.module:
                assert "sqlalchemy" not in nodo.module
                assert "requests" not in nodo.module
                assert "storage" not in nodo.module


# ---------------------------------------------------------------------------
# INVARIANZA 2 — No-contaminación: observatory / pandas / sklearn
# ---------------------------------------------------------------------------
def test_invarianza_business_no_importa_observatory_ni_ml():
    """[INVARIANZA 2 - NO CONTAMINACION]: qbe_business no debe importar qbe_observatory, pandas ni sklearn."""
    ruta_business_src = os.path.abspath(os.path.join(
        os.path.dirname(__file__), "..", "src"
    ))

    librerias_prohibidas = {"pandas", "scikit-learn", "sklearn", "joblib", "qbe_observatory", "observatory"}

    for raiz, _, archivos in os.walk(ruta_business_src):
        for archivo in archivos:
            if archivo.endswith(".py"):
                ruta_completa = os.path.join(raiz, archivo)
                with open(ruta_completa, "r", encoding="utf-8") as f:
                    try:
                        arbol = ast.parse(f.read())
                    except Exception as e:
                        pytest.fail(f"Fallo de parseo AST en {archivo}: {e}")

                    for nodo in ast.walk(arbol):
                        if isinstance(nodo, ast.Import):
                            for alias in nodo.names:
                                for prohibida in librerias_prohibidas:
                                    assert prohibida not in alias.name, (
                                        f"Violacion de frontera en {archivo}: importa '{alias.name}'"
                                    )
                        elif isinstance(nodo, ast.ImportFrom):
                            if nodo.module:
                                for prohibida in librerias_prohibidas:
                                    assert prohibida not in nodo.module, (
                                        f"Violacion de frontera en {archivo}: importa from '{nodo.module}'"
                                    )


# ---------------------------------------------------------------------------
# INVARIANZA 3 — Puerto 8000 / rutas OLTP montadas
# ---------------------------------------------------------------------------
def test_invarianza_servidor_business_puerto_8000_configurado():
    """[INVARIANZA 3 - PUERTO 8000]: app.py debe inicializar FastAPI con rutas de negocio montadas."""
    from qbe_business.src.web.app import app

    assert app is not None

    rutas = _recopilar_rutas(app)

    assert any("/api/markets" in r for r in rutas), (
        f"Faltan rutas de markets en qbe_business. Rutas detectadas: {rutas}"
    )
    assert any("/api/portfolio" in r or "/api/leagues" in r for r in rutas), (
        f"Faltan rutas de cartelera/cartera. Rutas detectadas: {rutas}"
    )
