"""Centro de Control — puerta de Business hacia la ingesta (aún no extraída).

El ejecutor real (`IngestionCoordinator`) pertenece a `qbe_ingestion`; Business no
importa ingesta. Mientras el servicio no exista, responde 503 controlado.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/admin/tasks", tags=["Admin Tasks"])

# Whitelist nominal para el semáforo de deriva. La ejecución real vive en qbe_ingestion.
TAREAS_PERMITIDAS: Dict[str, Dict[str, Any]] = {
    nombre: {}
    for nombre in (
        "centinela_deportivo",
        "centinela_mercado",
        "centinela_progol",
        "sincronizar_activos",
        "cadena_ingesta_total",
        "ingestar_historico_betexplorer",
        "auditar_coherencia_cartelera",
        "auditar_pipeline_backtesting",
        "auditar_completitud_visor",
        "exportar_dataset_investigacion",
        "generar_matriz_investigacion",
        "mineria_factores_shannon",
        "cadena_pre_jornada",
        "cadena_post_jornada",
        "cadena_progol",
        "auditar_cartera_shield",
        "consultar_uso_llm",
        "purgar_base_datos",
        "homologar_temporada_opta",
    )
}


@router.post("/run")
def ejecutar_tarea_administrativa(payload: Optional[Dict[str, Any]] = None) -> None:
    raise HTTPException(
        status_code=503,
        detail="Centro de Control delegado a qbe_ingestion (no disponible en Business)",
    )
