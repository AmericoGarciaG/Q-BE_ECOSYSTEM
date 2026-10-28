# -*- coding: utf-8 -*-
"""
🏆 THE SHIELD — ECOSYSTEM E2E MULTI-PORT CONTRACTS SUITE
Juez Inmutable: [ARCH-ECOSYSTEM-SUBFASE4.1]
Base de Gobierno: Kybern Framework v13.5
"""

import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

def test_invarianza_proxy_tareas_despacha_a_ingestion_8002():
    """[INVARIANZA 1 - TASK PROXY]: admin_tasks/run debe reenviar la petición a :8002 y retornar su respuesta."""
    from qbe_business.src.web.app import app
    client = TestClient(app)
    
    # 1. Simular respuesta exitosa de qbe_ingestion (:8002)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"status": "EN_PROCESO", "tarea": "centinela_deportivo", "task_id": "mock-123"}
    
    with patch("httpx.Client.post", return_value=mock_resp):
        res = client.request("POST", "/api/admin/tasks/run", json={"tarea": "centinela_deportivo"})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "EN_PROCESO"
        assert data["tarea"] == "centinela_deportivo"

def test_invarianza_proxy_tareas_retorna_503_si_ingesta_no_responde():
    """[INVARIANZA 2 - FAIL-SAFE]: Si :8002 no está levantado, el proxy debe emitir 503 controlado."""
    from qbe_business.src.web.app import app
    client = TestClient(app)
    
    # Forzar excepción de conexión
    with patch("httpx.Client.post", side_effect=Exception("Connection refused")):
        res = client.request("POST", "/api/admin/tasks/run", json={"tarea": "centinela_mercado"})
        assert res.status_code == 503
        assert "no disponible" in res.json()["detail"].lower()

def test_invarianza_proxy_deriva_consume_ingestion_8002():
    """[INVARIANZA 3 - DRIFT PROXY]: admin_status/drift debe responder con el esquema completo de 5 luces."""
    from qbe_business.src.web.app import app
    client = TestClient(app)
    
    mock_drift_payload = {
        "status_mercado": {"nivel": "VERDE", "glifo": "🟢", "detalle": "Cuotas frescas", "metrica": 5.0},
        "status_deportivo": {"nivel": "VERDE", "glifo": "🟢", "detalle": "Al día", "metrica": 0.0},
        "status_progol": {"nivel": "CONFORME", "glifo": "🟢", "detalle": "Abierto", "metrica": None},
        "status_integridad": {"nivel": "CONFORME", "glifo": "🟢", "detalle": "Sin anomalías", "metrica": 0.0},
        "status_homologacion": {"nivel": "CONFORME", "glifo": "🟢", "detalle": "Al día", "metrica": 0.0},
        "accion_recomendada": {"task_id": None, "motivo": "Todo conforme"},
        "status": "OK", "fuente": "qbe_ingestion"
    }
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_drift_payload
    
    with patch("httpx.get", return_value=mock_resp):
        res = client.get("/api/admin/status/drift")
        assert res.status_code == 200
        data = res.json()
        assert data["status_mercado"]["nivel"] == "VERDE"
        assert data["fuente"] == "qbe_ingestion"
