"""Q-BE Observatory — aplicación FastAPI de solo lectura."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import config
from app.routes.calibration import router as calibration_router
from app.routes.backtesting import router as backtesting_router
from app.routes.backtesting_ui import router as backtesting_ui_router
from app.routes.manus import router as manus_router
from app.routes.snapshot import router as snapshot_router
from app.services.calibration_view import cargar_panel_vars44, cargar_vista_calibracion

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
    """Auditoría de Calibración y Atribución sobre la bóveda 3NF (solo lectura).

    La fuente es el MISMO builder canónico que alimenta `/backtesting` y el
    endpoint REST. `jornada` se conserva como atajo de deep-link: el filtro de
    rango se resuelve en el cliente, por lo que la tabla se sirve completa y el
    usuario puede ampliar el rango sin recargar. Sin JavaScript se muestra todo
    el universo y el detalle expandido (nunca se oculta evidencia).
    """
    vista = cargar_vista_calibracion()
    return templates.TemplateResponse(
        request,
        "visor.html",
        {
            "titulo": "Auditoría de Calibración y Atribución — Q-BE Observatory",
            "vista": vista,
            "jornada_inicial": jornada if jornada and jornada > 0 else None,
        },
    )


@app.get("/visor/partido/{id_partido}/variables", response_class=HTMLResponse)
def visor_panel_vars44(request: Request, id_partido: str) -> HTMLResponse:
    """[DES-QBE-075] Fragmento HTML (B2) del panel forense de 32 variables.

    Solo lectura: reutiliza el builder canónico del Visor y transcribe
    `atribucion_factorial`. No calcula ni recalcula nada; si el partido no está
    en el universo auditado responde 404 y el cliente declara el fallo.
    """
    panel = cargar_panel_vars44(id_partido)
    if panel is None:
        raise HTTPException(status_code=404, detail="Partido no auditado en el snapshot")
    return templates.TemplateResponse(request, "_vars44_panel.html", panel)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ONLINE", "db": "READ_ONLY"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=config.OBS_HOST, port=config.OBS_PORT)
