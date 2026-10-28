# -*- coding: utf-8 -*-
"""
🏆 THE SHIELD — QBE_INGESTION CONFINEMENT & PORT 8002 SERVICE SUITE
Juez Inmutable: [ARCH-ECOSYSTEM-FASE4]
Base de Gobierno: Kybern Framework v13.5
"""

import ast
import os
import pytest
from fastapi.testclient import TestClient

def test_invarianza_centinela_macro_materializado():
    """[INVARIANZA 1 - CENTINELA MACRO]: centinela_macro.py debe existir en daemons y exponer función runner."""
    ruta_macro = os.path.abspath(os.path.join(
        os.path.dirname(__file__), "..", "src", "ingestion", "daemons", "centinela_macro.py"
    ))
    assert os.path.exists(ruta_macro), f"Falta el archivo centinela_macro.py en {ruta_macro}"
    
    with open(ruta_macro, "r", encoding="utf-8") as f:
        contenido = f.read()
    assert "cache_macro_stats" in contenido
    assert "fotmob" in contenido.lower()

def test_invarianza_servicio_ingesta_endpoint_drift_8002():
    """[INVARIANZA 2 - SERVICE 8002]: El microservicio de ingesta debe responder /api/ingestion/status/drift."""
    from qbe_ingestion.src.ingestion.service import app
    client = TestClient(app)
    
    # 1. Health check
    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["service"] == "qbe_ingestion"
    
    # 2. Endpoint de deriva que consulta qbe_business
    res_drift = client.get("/api/ingestion/status/drift")
    assert res_drift.status_code == 200
    data = res_drift.json()
    assert "status_mercado" in data
    assert "status_deportivo" in data
    assert "status_progol" in data
    assert "status_integridad" in data
    assert "accion_recomendada" in data

def test_invarianza_confinamiento_estricto_cero_fuga_en_otros_modulos():
    """[INVARIANZA 3 - CONFINAMIENTO]: qbe_core, qbe_business y qbe_observatory no deben importar scrapers."""
    raiz_ecosystem = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    
    modulos_pasivos = ["qbe_core", "qbe_business", "qbe_observatory"]
    simbolos_scraping_prohibidos = {"CalienteScraper", "FotmobProvider", "BetwayScraper", "NovibetScraper", "ProgolScraper"}
    
    for mod in modulos_pasivos:
        ruta_src = os.path.join(raiz_ecosystem, mod, "src")
        if not os.path.exists(ruta_src):
            continue
            
        for raiz, _, archivos in os.walk(ruta_src):
            for archivo in archivos:
                if archivo.endswith(".py"):
                    ruta_completa = os.path.join(raiz, archivo)
                    with open(ruta_completa, "r", encoding="utf-8") as f:
                        arbol = ast.parse(f.read())
                        
                    for nodo in ast.walk(arbol):
                        if isinstance(nodo, ast.Import):
                            for alias in nodo.names:
                                for s in simbolos_scraping_prohibidos:
                                    assert s not in alias.name, f"Fuga de scraper en {mod}/{archivo}: {alias.name}"
                        elif isinstance(nodo, ast.ImportFrom):
                            if nodo.module and "scrapers" in nodo.module:
                                pytest.fail(f"Fuga: {mod}/{archivo} importa desde módulo scrapers: {nodo.module}")
