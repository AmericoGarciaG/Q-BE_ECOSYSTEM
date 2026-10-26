"""Q-BE Observatory — aplicación FastAPI de solo lectura."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.core.contracts.portfolio_math import calcular_brier_multicategorico

from app import config
from app.routes.calibration import construir_reporte, router as calibration_router
from app.routes.backtesting import router as backtesting_router
from app.routes.backtesting_ui import router as backtesting_ui_router
from app.routes.manus import router as manus_router
from app.routes.snapshot import router as snapshot_router

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Q-BE Observatory")

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.include_router(calibration_router)
app.include_router(backtesting_router)
app.include_router(backtesting_ui_router)
app.include_router(manus_router)
app.include_router(snapshot_router)


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "index.html",
        {"titulo": "Q-BE Observatory"},
    )


@app.get("/visor", response_class=HTMLResponse)
def visor(request: Request, jornada: Optional[int] = None) -> HTMLResponse:
    reporte = construir_reporte(brier_fn=calcular_brier_multicategorico)
    jornadas = reporte.jornadas
    if jornada is not None:
        jornadas = [fila for fila in jornadas if fila.jornada == jornada]
    return templates.TemplateResponse(
        request,
        "visor.html",
        {
            "titulo": "Visor de Calibración",
            "reporte": reporte,
            "jornadas": jornadas,
            "jornada": jornada,
        },
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ONLINE", "db": "READ_ONLY"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=config.OBS_HOST, port=config.OBS_PORT)
