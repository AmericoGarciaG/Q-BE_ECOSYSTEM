"""
Kybern Industrial — [ARCH-1.5.2] Router Administrativo de Curación HITL
Controlador de endpoints /api/admin/catalogs/*

Endpoints:
  POST /api/admin/catalogs/discover   — Inicia prospección agéntica
  GET  /api/admin/catalogs/staging    — Retorna candidatos en staging
  POST /api/admin/catalogs/commit     — Sella el catálogo confirmado en SQLite

[AISLAMIENTO DE PRODUCCIÓN]: Ningún candidato en staging es visible en
/api/leagues/{id}/live-board hasta el commit administrativo. [LN-QBE-015]
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.storage.database import get_db
from src.storage.curation_service import (
    ejecutar_prospeccion_liga,
    obtener_staging_liga,
    sellar_catalogo_en_db,
)

router = APIRouter(prefix="/api/admin/catalogs", tags=["Admin Curation HITL"])


class TeamCatalogItemIn(BaseModel):
    name: str
    short_name: str
    canonical_slug: str
    crest_url: Optional[str] = None
    crest_candidate_url: Optional[str] = None
    stadium: Optional[str] = "Estadio Oficial"
    city: Optional[str] = "México"
    aliases: Optional[List[str]] = Field(default_factory=list)
    fotmob_id: Optional[int] = None


class CommitCatalogRequest(BaseModel):
    """Contrato de entrada para el sellado de catálogo [ARCH-1.5.2] (Protocolo Nexus)."""
    league_id: int = 262
    approved_teams: List[TeamCatalogItemIn]


@router.post("/discover")
def discover_catalogs(league_id: int = Query(default=262)) -> Dict[str, Any]:
    """
    [ARCH-1.5.2 — Endpoint 1]
    Inicia la prospección agéntica y prepara el staging temporal de clubes candidatos.
    """
    try:
        return ejecutar_prospeccion_liga(league_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/staging")
def get_staging_catalogs(league_id: int = Query(default=262)) -> List[Dict[str, Any]]:
    """
    [ARCH-1.5.2 — Endpoint 2]
    Retorna los clubes en prospección temporal para revisión e inspección visual HITL.
    """
    try:
        return obtener_staging_liga(league_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/commit")
def commit_catalogs(
    payload: CommitCatalogRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    [ARCH-1.5.2 — Endpoint 3]
    Sella los clubes confirmados por el Director Humano.
    """
    try:
        teams_data = [t.model_dump() for t in payload.approved_teams]
        return sellar_catalogo_en_db(payload.league_id, teams_data, db)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


llm_router = APIRouter(prefix="/api/admin/llm", tags=["LLM Telemetry"])


@llm_router.get("/telemetry")
def get_llm_telemetry(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    [ARCH-1.3.4] Entrega los últimos 50 registros de inferencia de LLMTokenLedger.
    """
    try:
        from src.storage.models import LLMTokenLedger
        records = db.query(LLMTokenLedger).order_by(LLMTokenLedger.id.desc()).limit(50).all()
        total_cost = sum(r.cost_usd for r in records)
        total_prompt_tokens = sum(r.prompt_tokens for r in records)
        total_candidates_tokens = sum(r.candidates_tokens for r in records)

        items = [
            {
                "id": r.id,
                "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                "key_alias": r.key_alias,
                "task_type": r.task_type,
                "model_name": r.model_name,
                "prompt_tokens": r.prompt_tokens,
                "candidates_tokens": r.candidates_tokens,
                "latency_ms": r.latency_ms,
                "cost_usd": r.cost_usd,
                "status": r.status,
            }
            for r in records
        ]

        return {
            "total_records": len(items),
            "summary": {
                "total_prompt_tokens": total_prompt_tokens,
                "total_candidates_tokens": total_candidates_tokens,
                "total_cost_usd": round(total_cost, 6),
            },
            "records": items,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

