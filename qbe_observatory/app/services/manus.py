"""Registro de modelos Manus (Tareas A/B/C) para el Observatorio."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODELOS_DIR = Path(os.getenv("OBS_MANUS_MODELS", str(PROJECT_ROOT / "data" / "models"))).resolve()

TAREAS: Dict[str, str] = {
    "task_a": "Modelo A — riesgo/calibración",
    "task_b": "Modelo B — señales de mercado",
    "task_c": "Modelo C — cartera/optimización",
}


class ModeloNoDisponible(RuntimeError):
    """El artefacto o las dependencias analíticas no están presentes."""


def _ruta_modelo(task: str) -> Path:
    return MODELOS_DIR / f"{task}.joblib"


def modelos_disponibles() -> List[Dict[str, Any]]:
    return [
        {
            "task": task,
            "descripcion": descripcion,
            "artefacto": str(_ruta_modelo(task)),
            "disponible": _ruta_modelo(task).is_file(),
        }
        for task, descripcion in TAREAS.items()
    ]


def predecir(task: str, features: Dict[str, Any]) -> Dict[str, Any]:
    """Carga el artefacto con joblib y predice con pandas/scikit-learn."""
    if task not in TAREAS:
        raise KeyError(task)
    ruta = _ruta_modelo(task)
    if not ruta.is_file():
        raise ModeloNoDisponible(f"Modelo no disponible: {ruta}")

    try:
        import joblib
        import pandas as pd
    except ImportError as exc:  # pragma: no cover - dependencia declarada
        raise ModeloNoDisponible("pandas/joblib no instalados") from exc

    modelo = joblib.load(ruta)
    marco = pd.DataFrame([features])
    prediccion = modelo.predict(marco)
    return {
        "task": task,
        "modelo": ruta.name,
        "predicciones": prediccion.tolist() if hasattr(prediccion, "tolist") else list(prediccion),
    }
