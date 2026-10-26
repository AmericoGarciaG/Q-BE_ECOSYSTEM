"""UI server-rendered del backtesting (Jinja2, sin JS de la Mesa)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import sessionmaker

from app import config
from app.services.manus import modelos_disponibles
from app.services.snapshot_refresh import edad_snapshot, snapshot_fresco

BASE_DIR = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter(tags=["Observatory UI"])


def _reporte() -> Any:
    from app.routes.backtesting import _construir_reporte_calibracion, _motor_solo_lectura

    motor = _motor_solo_lectura()
    sesion = sessionmaker(bind=motor)()
    try:
        return _construir_reporte_calibracion(sesion, None)
    finally:
        sesion.close()
        motor.dispose()


def _contexto(request: Request) -> Dict[str, Any]:
    edad = edad_snapshot(config.BACKTESTING_SNAPSHOT)
    return {
        "titulo": "Backtesting — Q-BE Observatory",
        "snapshot": config.BACKTESTING_SNAPSHOT,
        "snapshot_edad_min": round(edad / 60, 1) if edad is not None else None,
        "snapshot_fresco": snapshot_fresco(config.BACKTESTING_SNAPSHOT, 60),
        "modelos_manus": modelos_disponibles(),
    }


@router.get("/backtesting", response_class=HTMLResponse)
def backtesting_ui(request: Request) -> HTMLResponse:
    contexto = _contexto(request)
    try:
        contexto["reporte"] = _reporte()
        contexto["error"] = None
    except Exception as exc:
        contexto["reporte"] = None
        contexto["error"] = str(exc)
    return templates.TemplateResponse(request, "backtesting.html", contexto)


@router.post("/backtesting/simulate", response_class=HTMLResponse)
def backtesting_simular(
    request: Request,
    bankroll_inicial: float = Form(default=10000.0),
    rango_jornadas: str = Form(default="1-2"),
    modo_interes: str = Form(default="plano"),
    gamma_slider: float = Form(default=0.67),
    target_certeza_pct: float = Form(default=0.0),
    modo_cobertura: str = Form(default="DEF"),
) -> HTMLResponse:
    from src.observatory.core.simulation_engine import (
        ejecutar_simulacion_rentabilidad,
        parsear_rango_jornadas,
    )
    from app.routes.backtesting import _ReadOnlyGateway

    contexto = _contexto(request)
    contexto["form"] = {
        "bankroll_inicial": bankroll_inicial,
        "rango_jornadas": rango_jornadas,
        "modo_interes": modo_interes,
        "gamma_slider": gamma_slider,
        "target_certeza_pct": target_certeza_pct,
        "modo_cobertura": modo_cobertura,
    }
    try:
        contexto["reporte"] = _reporte()
        contexto["error"] = None
    except Exception as exc:
        contexto["reporte"] = None
        contexto["error"] = str(exc)
        return templates.TemplateResponse(request, "backtesting.html", contexto)

    try:
        jornadas = parsear_rango_jornadas(rango_jornadas)
        if not jornadas:
            raise ValueError("rango sin jornadas positivas")
        resultado = ejecutar_simulacion_rentabilidad(
            bankroll_inicial=bankroll_inicial,
            jornadas=jornadas,
            modo=modo_interes,
            gateway=_ReadOnlyGateway(),
            gamma=gamma_slider,
            target_certeza_pct=target_certeza_pct,
            modo_cobertura=modo_cobertura,
        )
    except (TypeError, ValueError) as exc:
        contexto["sim_error"] = str(exc)
        return templates.TemplateResponse(request, "backtesting.html", contexto)

    curva = [float(v) for v in resultado.get("curva_bankroll", [])]
    minimo = min(curva) if curva else 0.0
    maximo = max(curva) if curva else 0.0
    rango = (maximo - minimo) or 1.0
    contexto["resultado"] = resultado
    contexto["curva"] = [
        {"valor": valor, "pct": max(0.0, min(100.0, (valor - minimo) / rango * 100.0))}
        for valor in curva
    ]
    contexto["sim_error"] = None
    return templates.TemplateResponse(request, "backtesting.html", contexto)
