# -*- coding: utf-8 -*-
"""[ARCH-1.4.78] Enrutador server-rendered de la Vista Unificada de Desempeño.

`GET /desempeno` (`[DES-QBE-078]`) sirve `desempeno.html` con el contexto
`{"titulo", "vista", "seccion"}`. El enrutador no calcula nada: delega en la
fachada `app.services.desempeno_view` y en el builder canónico del Observatorio.

La aduana de dominio vive en la fachada y es Fail-Loud (`ValueError`): un casino
no reconocido o un de-vig fuera de `shin` / `proporcional` NO se captura aquí.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services.desempeno_view import cargar_vista_desempeno

BASE_DIR = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter(tags=["Desempeño y Coberturas"])

TITULO = "Desempeño y Coberturas Probabilísticas — Q-BE Observatory"


@router.get("/desempeno", response_class=HTMLResponse)
def desempeno_ui(
    request: Request,
    mando: str = "qbe",
    temporada: str = "",
    jornada_desde: Optional[int] = None,
    jornada_hasta: Optional[int] = None,
    casino: List[str] = Query(default=[]),
    devig: str = "shin",
) -> HTMLResponse:
    """Vista rectora de desempeño: Brier Q-BE vs. consenso bajo Distribución Base."""
    vista = cargar_vista_desempeno(
        mando=mando,
        temporada=temporada,
        jornada_desde=jornada_desde,
        jornada_hasta=jornada_hasta,
        casinos=casino,
        devig=devig,
    )
    return templates.TemplateResponse(
        request,
        "desempeno.html",
        {"titulo": TITULO, "vista": vista, "seccion": "desempeno"},
    )
