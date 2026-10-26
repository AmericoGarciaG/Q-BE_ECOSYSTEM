"""Adaptador local de LLM — el gateway real vive en `qbe_ingestion`.

Business no importa `google-generativeai` ni `src.services.gemini_gateway`.
Si no hay llaves configuradas, o el gateway no está portado, responde 503 limpio.
"""

from __future__ import annotations

import os
from typing import Any, Dict

from fastapi import HTTPException

_KEYS = (
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "Gemini_API_4_QBE_001",
    "Gemini_API_4_QBE_002",
    "Gemini_API_4_QBE_003",
    "Gemini_API_4_QBE_004",
)


def llm_disponible() -> bool:
    return any(os.getenv(nombre, "").strip() for nombre in _KEYS)


def generar_tesis_partido(partido_data: Dict[str, Any]) -> str:
    """Fachada de tesis; no reimplementa el gateway de ingesta."""
    if not llm_disponible():
        raise HTTPException(
            status_code=503,
            detail="LLM no configurado en Business (QBE-FEATURE-LLM=false)",
        )
    raise HTTPException(
        status_code=503,
        detail="Gateway LLM delegado a qbe_ingestion (no portado a Business)",
    )
