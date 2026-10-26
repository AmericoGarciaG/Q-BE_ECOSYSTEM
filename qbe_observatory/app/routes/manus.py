"""Endpoints de los modelos Manus (Tareas A/B/C)."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.manus import (
    TAREAS,
    ModeloNoDisponible,
    modelos_disponibles,
    predecir,
)

router = APIRouter(prefix="/api/observatory/manus", tags=["Manus Models"])


class PredictionRequest(BaseModel):
    features: Dict[str, Any] = Field(default_factory=dict)


@router.get("/models")
def listar_modelos() -> Dict[str, Any]:
    return {"modelos": modelos_disponibles(), "tareas": TAREAS}


@router.post("/{task}/predict")
def predecir_modelo(task: str, payload: PredictionRequest) -> Dict[str, Any]:
    if task not in TAREAS:
        raise HTTPException(status_code=404, detail=f"Tarea desconocida: {task}")
    try:
        return predecir(task, payload.features)
    except ModeloNoDisponible as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
