# -*- coding: utf-8 -*-
"""
Kybern Industrial — Portfolio REST Router [ARCH-PILLAR]
[ARCH-1.3.5 · Enmienda Nudo 3] La ruta legacy `/generate` fue físicamente eliminada.
Este router conserva exclusivamente el registro de boletos (`/register-ticket`), su
estado (`/ledger-status`) y la tesis narrativa (`/match-thesis`). Toda generación de
cartera es gobernada por `src/web/routes/markets.py`.
"""
from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import IntegrityError
from src.storage.gateway import PersistenceGateway
from src.storage.models import PaperTradingLedger
from src.models.web_schemas import (
    TicketLedgerStatusResponse,
    TicketRegistrationRequest,
    TicketRegistrationResponse,
)


router = APIRouter(prefix="/api/portfolio", tags=["Portfolio"])


def _resumen_ledger(filas) -> TicketLedgerStatusResponse:
    return TicketLedgerStatusResponse(
        boletos_comprados=len(filas),
        monto_comprometido_mxn=round(sum(float(f.monto) for f in filas), 2),
        match_ids=[f.match_id for f in filas],
    )


@router.post("/register-ticket", response_model=TicketRegistrationResponse)
def register_ticket(req: TicketRegistrationRequest):
    """[ARCH-1.4.32 / P3-9] Sella el boleto en `paper_trading_ledger` con idempotencia."""
    gateway = PersistenceGateway()
    with gateway.read_session() as db:
        existente = db.query(PaperTradingLedger).filter(
            PaperTradingLedger.match_id == req.match_id,
            PaperTradingLedger.desenlace == req.desenlace,
            PaperTradingLedger.monto == req.monto,
        ).first()
        if existente is not None:
            raise HTTPException(
                status_code=409,
                detail="[P3-9] Boleto duplicado: ya existe un registro idéntico.",
            )

    try:
        with gateway.write_transaction() as db:
            registro = PaperTradingLedger(
                match_id=req.match_id,
                desenlace=req.desenlace,
                cuota_congelada=req.cuota_congelada,
                monto=req.monto,
            )
            db.add(registro)
            db.flush()
            ticket_id = int(registro.id)
            filas = db.query(PaperTradingLedger).all()
            resumen = _resumen_ledger(filas)
    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="[P3-9] Boleto duplicado: la restricción única rechazó el registro.",
        )

    return TicketRegistrationResponse(
        status="OK",
        ticket_id=ticket_id,
        boletos_comprados=resumen.boletos_comprados,
        monto_comprometido_mxn=resumen.monto_comprometido_mxn,
    )


@router.get("/ledger-status", response_model=TicketLedgerStatusResponse)
def get_ledger_status():
    """[ARCH-1.4.32 / P3-9] Estado agregado del ledger para hidratar el badge de la SPA."""
    with PersistenceGateway().read_session() as db:
        return _resumen_ledger(db.query(PaperTradingLedger).all())


import logging
from typing import Dict, Any
from pydantic import BaseModel

logger = logging.getLogger("PortfolioRouter")

class MatchThesisRequest(BaseModel):
    partido_id: str
    partido_data: Dict[str, Any]


@router.post("/match-thesis")
def generate_match_thesis_endpoint(req: MatchThesisRequest):
    """
    [ARCH-1.3.4 / ARCH-1.6.10] Invocación real de Gemini 3.6 Flash bajo demanda.
    """
    logger.info(f"🧠 [ON-DEMAND] Redactando Tesis con Gemini para partido {req.partido_id}...")
    print(f"🧠 [ON-DEMAND] Redactando Tesis con Gemini para partido {req.partido_id}...")
    from src.services.gemini_gateway import GeminiCognitiveGateway
    gateway = GeminiCognitiveGateway()
    tesis_html = gateway.generate_thesis(req.partido_data)
    return {"partido_id": req.partido_id, "tesis_html": tesis_html}
