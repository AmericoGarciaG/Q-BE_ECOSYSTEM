"""Q-BE Business — fachada FastAPI de la Mesa de Apuestas (Fase 3).

Esta primera materialización habilita:
  * el namespace compartido `src.*`,
  * la fachada de feature flags,
  * el bloqueo 503 de backtesting/admin mientras sus servicios no estén migrados.

Los routers transaccionales (markets/portfolio/leagues) se incorporan en la
siguiente iteración de la misma fase, sobre `qbe_storage` y `qbe_core`.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.web.routes.markets import router as markets_router
from src.web.routes.portfolio import router as portfolio_router
from src.web.routes.leagues import router as leagues_router
from src.web.routes.export import router as export_router
from src.web.routes.sovereign import router as sovereign_router
from src.web.routes.admin import router as admin_router, llm_router
from src.web.routes.admin_status import router as admin_status_router
from src.web.routes.admin_tasks import router as admin_tasks_router

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Q-BE Business")

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.include_router(markets_router)
app.include_router(portfolio_router)
app.include_router(leagues_router)
app.include_router(export_router)
app.include_router(sovereign_router)
app.include_router(admin_router)
app.include_router(llm_router)
app.include_router(admin_status_router)
app.include_router(admin_tasks_router)


def _flag(nombre: str, default: bool = False) -> bool:
    valor = os.getenv(nombre)
    if valor is None:
        return default
    return valor.strip().lower() in {"1", "true", "yes", "on"}


def _flags() -> dict[str, bool]:
    return {
        "backtesting": _flag("QBE_FEATURE_BACKTESTING", False),
        "admin": _flag("QBE_FEATURE_ADMIN", False),
    }


# [D-4 / ARCH-ECOSYSTEM-SUBFASE4.1] Rutas-puente del Centro de Control: ya están
# materializadas como proxy reverso hacia Ingesta (:8002), por lo que no son
# superficie de UI bloqueable por flag. El resto de `/api/admin` sigue gobernado por
# `QBE_FEATURE_ADMIN`; `/api/business/features` continúa declarando `admin: false`
# hasta que la SPA reciba el flag de forma explícita.
RUTAS_PUENTE_ADMIN = (
    "/api/admin/status/drift",
    "/api/admin/tasks/run",
)


@app.middleware("http")
async def _fachada_gate(request: Request, call_next):
    """Los módulos no migrados no deben alcanzar routers ni servicios externos."""
    ruta = request.url.path
    flags = _flags()
    if ruta.startswith("/api/markets/backtesting") and not flags["backtesting"]:
        return JSONResponse(
            status_code=503,
            content={"detail": "Módulo no disponible en Business"},
        )
    if ruta.startswith("/api/admin") and not flags["admin"]:
        if ruta.rstrip("/") not in RUTAS_PUENTE_ADMIN:
            return JSONResponse(
                status_code=503,
                content={"detail": "Módulo no disponible en Business"},
            )
    return await call_next(request)


@app.get("/api/business/features")
def feature_flags() -> dict[str, bool]:
    """Contrato de fachada ratificado: ambos módulos nacen desactivados."""
    return _flags()


@app.get("/api/markets/backtesting/calibration-report")
def backtesting_no_disponible() -> None:
    if not _flags()["backtesting"]:
        raise HTTPException(status_code=503, detail="Módulo no disponible en Business")
    raise HTTPException(status_code=503, detail="Backtesting se sirve desde qbe_observatory")


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html", {"titulo": "Q-BE Casino Deportes"})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ONLINE", "module": "business"}
