"""Centro de Control — puente de despacho de Business hacia Ingesta (:8002).

Business **no ejecuta tareas**: actúa como API Gateway / proxy reverso del
`IngestionCoordinator` que vive en `qbe_ingestion`. La frontera es el contrato JSON
HTTP (`POST /api/ingestion/tasks/run`), nunca un import.

Reglas de gobierno:
  * [ARCH-ECOSYSTEM-SUBFASE4.1] el despacho real se delega en `:8002`; Business no
    conoce ni reproduce la whitelist ejecutable de Ingesta.
  * D-1: la entrada es tolerante al contrato de la SPA (`task_id`) y al de la
    directiva (`tarea`); se canonicaliza a `{"tarea": ...}` antes de reenviar.
  * D-3: fail-closed. Sin identificador de tarea no hay despacho: 503 explícito que
    nombra a `qbe_ingestion` (preserva el juez certificado de paridad de Slice 3A).
  * 503 exclusivamente cuando Ingesta no está en línea; un error de contrato de
    Ingesta (4xx) se propaga con su status y su cuerpo originales.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/admin/tasks", tags=["Admin Tasks Bridge"])

# Whitelist nominal para el semáforo de deriva (registro de tareas que la SPA sabe
# pintar). La ejecución real y su whitelist ejecutable viven en qbe_ingestion.
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

INGESTA_POR_DEFECTO = "http://127.0.0.1:8002"
TIMEOUT_DESPACHO_S = 60.0


class SolicitudTarea(BaseModel):
    """Entrada tolerante [D-1]: la SPA manda `task_id`, la directiva manda `tarea`."""

    tarea: Optional[str] = None
    task_id: Optional[str] = None


def _base_ingesta() -> str:
    """URL de Ingesta resuelta por entorno, sin dependencia del CWD."""
    return os.getenv("QBE_INGESTION_URL", INGESTA_POR_DEFECTO).rstrip("/")


def _resolver_tarea(req: SolicitudTarea) -> str:
    """Canonicaliza el identificador; cadena vacía ⇒ no hay despacho posible."""
    return (req.tarea or req.task_id or "").strip()


@router.post("/run")
def ejecutar_tarea_administrativa(req: Optional[SolicitudTarea] = None) -> Any:
    """API Gateway / Proxy Reverso hacia `qbe_ingestion` (`:8002`)."""
    tarea = _resolver_tarea(req or SolicitudTarea())
    if not tarea:
        # [D-3] Fail-closed: el Centro de Control se delega a Ingesta y no admite
        # despachos anónimos. 503 (no 422) preserva el contrato certificado de Slice 3A.
        raise HTTPException(
            status_code=503,
            detail=(
                "Petición sin identificador de tarea: el Centro de Control se delega "
                "a qbe_ingestion (:8002) y no admite despachos anónimos."
            ),
        )

    base = _base_ingesta()
    try:
        with httpx.Client(timeout=TIMEOUT_DESPACHO_S) as cliente:
            respuesta = cliente.post(
                f"{base}/api/ingestion/tasks/run",
                json={"tarea": tarea},
            )
            respuesta.raise_for_status()
            try:
                return respuesta.json()
            except ValueError as exc:
                raise HTTPException(
                    status_code=502,
                    detail=(
                        f"qbe_ingestion (:8002) respondió un cuerpo no-JSON para la "
                        f"tarea '{tarea}': {exc}"
                    ),
                ) from exc
    except HTTPException:
        raise
    except httpx.HTTPStatusError as exc:
        # Ingesta SÍ respondió: se propaga su veredicto tal cual (p. ej. 400 por
        # tarea fuera de su whitelist ejecutable). Business no reinterpreta.
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=exc.response.text,
        ) from exc
    except Exception as exc:
        # Sólo aquí Ingesta no está en línea (conexión rechazada, timeout, DNS).
        raise HTTPException(
            status_code=503,
            detail=(
                f"Servicio de Ingesta (:8002) no disponible para ejecutar la tarea "
                f"'{tarea}': {exc}"
            ),
        ) from exc
