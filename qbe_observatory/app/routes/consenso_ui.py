# -*- coding: utf-8 -*-
"""`[DES-QBE-076]` UI server-rendered del Consenso de Mercado."""

from __future__ import annotations

from pathlib import Path
from typing import List

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services.consenso_view import cargar_vista_consenso

BASE_DIR = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter(tags=["Consenso de Mercado"])


@router.get("/consenso", response_class=HTMLResponse)
def consenso_ui(
    request: Request,
    fuente: List[str] = Query(default=[]),
    filtros: int = 0,
    temporada: str = "",
    jornada: str = "",
) -> HTMLResponse:
    contexto = cargar_vista_consenso(
        fuentes=fuente,
        filtros=bool(filtros),
        temporada=temporada,
        jornada=jornada,
    )
    return templates.TemplateResponse(request, "consenso.html", contexto)
