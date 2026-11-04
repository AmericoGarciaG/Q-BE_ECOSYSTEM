# -*- coding: utf-8 -*-
"""`[DES-QBE-076]` Vista de Consenso de Mercado — revisión `[SPRINT-47]`.

Ruta `/consenso`: checkboxes de fuentes, KPIs del universo filtrado, mercado en
vivo y desglose por jornada.

Contrato `[SPRINT-47]`:

* Los filtros de Temporada y Jornada son GLOBALES: la misma temporada viaja al
  panel de mercado en vivo (que se declara vacío si es histórica) y al desglose.
* Un fallo de la bóveda histórica (`HistoricoDBError`) **detiene** la vista y se
  declara en la UI; jamás se sirve otra base de datos en silencio.
* `[LN-QBE-148]` Q-BE es Challenger independiente y nunca participa del
  Consenso Ponderado. Los pesos del panel vivo son `1 / casinos seleccionados`.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from app import config
from app.services.calibration_view import HistoricoDBError, cargar_vista_calibracion
from app.services.sabiduria_view import (
    FUENTES_CASINO,
    FUENTES_CONOCIDAS,
    construir_mercado_vivo,
    construir_sabiduria_masas,
)

logger = logging.getLogger(__name__)

SELECCION_DEFAULT: List[str] = [*FUENTES_CASINO, "qbe"]


def _normalizar_seleccion(fuentes: Sequence[str], filtros: bool) -> List[str]:
    if not filtros:
        return list(SELECCION_DEFAULT)
    seleccion: List[str] = []
    for fuente in fuentes:
        nombre = str(fuente or "").strip().lower()
        if nombre == "q-be":
            nombre = "qbe"
        if nombre in FUENTES_CONOCIDAS and nombre not in seleccion:
            seleccion.append(nombre)
    return seleccion


def _sabiduria_vacia(seleccion_vacia: bool = True) -> Dict[str, Any]:
    return {
        "resumen": {
            "brier_consenso": None,
            "brier_qbe": None,
            "alpha_pct": None,
            "etiqueta_mercado": "Consenso",
            "composicion_mercado": "",
            "fuentes_mercado": {},
            "n_partidos": 0,
            "n_jornadas": 0,
            "casinos_validos": 0,
            "casinos_totales": 0,
            "consenso_degenerado": False,
            "seleccion_vacia": seleccion_vacia,
        },
        "fuentes": [],
        "jornadas": [],
        "jornadas_disponibles": [],
        "temporadas": [],
        "temporada_actual": "",
        "total_partidos": 0,
        "total_universo": 0,
        "total_historico": 0,
        "casinos": 0,
        "seleccion": [],
        "seleccion_vacia": seleccion_vacia,
        "es_historica": False,
        "fuente_etiqueta": "Sin datos",
        "nota": "",
        "motivo_filtro": None,
    }


def _mercado_vacio(motivo: str) -> Dict[str, Any]:
    return {
        "jornada": None,
        "jornada_viva": None,
        "actualizado": None,
        "partidos": [],
        "vacio": True,
        "motivo": motivo,
        "motivo_historico": False,
        "fuente_etiqueta": "Sin datos de mercado",
    }


def _procedencia(sabiduria: Dict[str, Any], mercado: Dict[str, Any]) -> str:
    """Etiqueta de fuente que la UI muestra junto al título (`[SPRINT-47]` Tarea 4)."""
    if sabiduria.get("es_historica"):
        return f"Fuente: {sabiduria.get('fuente_etiqueta')}"
    jornada_viva = mercado.get("jornada_viva")
    if jornada_viva is not None:
        return f"Fuente: Snapshot Vivo (J{jornada_viva})"
    return f"Fuente: {sabiduria.get('fuente_etiqueta')}"


def _contexto(
    vista: Dict[str, Any],
    sabiduria: Dict[str, Any],
    mercado: Dict[str, Any],
    *,
    seleccion: Sequence[str],
    temporada: str,
    jornada: str,
    error: Optional[str],
) -> Dict[str, Any]:
    return {
        "titulo": "Consenso de Mercado — Q-BE Observatory",
        "vista": vista,
        "sabiduria": sabiduria,
        "jornadas_disponibles": list(sabiduria.get("jornadas_disponibles") or []),
        "mercado": mercado,
        "seleccion": list(seleccion),
        "seleccion_vacia": not seleccion or bool(sabiduria.get("seleccion_vacia")),
        "temporada_filtro": temporada,
        "jornada_filtro": jornada,
        "procedencia": _procedencia(sabiduria, mercado),
        "error": error,
    }


def cargar_vista_consenso(
    fuentes: Optional[Sequence[str]] = None,
    filtros: bool = False,
    temporada: str = "",
    jornada: str = "",
) -> Dict[str, Any]:
    """Construye el contexto de `/consenso` para la selección solicitada.

    Raises:
        No propaga `HistoricoDBError`: la transcribe a `error` para que la ruta
        responda con un mensaje explícito en la UI (Tarea 1).
    """
    seleccion = _normalizar_seleccion(fuentes or [], filtros)
    vista = cargar_vista_calibracion()
    reporte = vista.get("reporte")
    ruta = Path(config.BACKTESTING_SNAPSHOT)

    if vista.get("error") or not isinstance(reporte, dict):
        mensaje = str(vista.get("error") or "El reporte de calibración no está disponible.")
        return _contexto(
            vista,
            _sabiduria_vacia(),
            _mercado_vacio(mensaje),
            seleccion=seleccion,
            temporada=temporada,
            jornada=jornada,
            error=mensaje,
        )

    temporada_actual = temporada or str((vista.get("fuente") or {}).get("temporada") or "")
    try:
        sabiduria = construir_sabiduria_masas(
            reporte,
            ruta,
            temporada=temporada_actual,
            fuentes=seleccion,
            jornada=jornada,
        )
        # La temporada viaja también al panel vivo: si es histórica, el panel se
        # declara vacío con motivo (Tarea 2) en vez de servir J16 bajo otra etiqueta.
        mercado = construir_mercado_vivo(
            ruta,
            fuentes=seleccion,
            jornada=jornada,
            temporada=temporada_actual,
        )
    except HistoricoDBError as exc:
        # Fallo EXPLÍCITO: la vista se detiene; no se sustituye el universo.
        logger.error("Bóveda histórica no disponible: %s", exc)
        return _contexto(
            vista,
            _sabiduria_vacia(),
            _mercado_vacio(str(exc)),
            seleccion=seleccion,
            temporada=temporada,
            jornada=jornada,
            error=str(exc),
        )

    return _contexto(
        vista,
        sabiduria,
        mercado,
        seleccion=seleccion,
        temporada=temporada,
        jornada=jornada,
        error=None,
    )
