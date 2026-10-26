"""Servicio REST del Data Nexus (Ingesta).

Expone el estado de deriva que Business consume por HTTP. No importa Business.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import FastAPI, Query

from src.ingestion.coherence_auditor import auditar_coherencia_partido
from src.ingestion.daemons.centinela_mercado import (
    FRONTERA_LIGA_MX_ID,
    cargar_fixtures_por_jornada,
)

app = FastAPI(title="Q-BE Ingestion — Data Nexus")


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "service": "qbe_ingestion"}


@app.get("/api/ingestion/status/drift")
def estado_deriva(league_id: Optional[int] = Query(default=None)) -> Dict[str, Any]:
    """Ejecuta las sondas de coherencia sobre la cartelera persistida."""
    liga = int(league_id) if league_id is not None else FRONTERA_LIGA_MX_ID
    cartelera = cargar_fixtures_por_jornada(liga)

    reportes = []
    for jornada, fixtures in cartelera.items():
        for fixture in fixtures:
            reporte = auditar_coherencia_partido(fixture)
            reportes.append(
                {
                    "jornada": jornada,
                    "reporte": reporte.model_dump(mode="json"),
                }
            )

    return {
        "status": "OK",
        "fuente": "qbe_ingestion",
        "liga": liga,
        "jornadas": len(cartelera),
        "partidos": len(reportes),
        "reportes": reportes,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8002)
