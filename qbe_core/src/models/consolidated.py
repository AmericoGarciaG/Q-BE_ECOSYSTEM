# Q-BE Casino Deportes — Consolidated Payload Models (src/models/consolidated.py)
"""
[ARCH-PILLAR] Modelo consolidado de salida para orquestación de pipeline y generación de reportes.
Representa el payload maestro unificado consumido por Jinja2, Playwright y la SPA Web.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, ConfigDict


class ConsolidatedPayload(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")
    metadata: Dict[str, Any]
    control: Dict[str, Any]
    balance: Dict[str, Any]
    ordenes: List[Dict[str, Any]]
    satelite: Dict[str, Any]
    partidos_analisis: List[Dict[str, Any]]
    descartes: List[Dict[str, Any]]
    tabla_posiciones_completa: Optional[List[Dict[str, Any]]] = None
    cartelera_completa: Optional[List[Dict[str, Any]]] = None