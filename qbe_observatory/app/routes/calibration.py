"""Contrato y cálculo del reporte de calibración del Observatorio."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.core.contracts.portfolio_math import calcular_brier_multicategorico
from src.models.web_schemas import CalibrationReportResponse as CanonicalReportResponse

from app.adapters.db_readonly import BaseDatosSoloLectura
from app.config import HISTORICO_DB
from app.routes.backtesting import get_db_ro, reporte_calibracion_canonico

router = APIRouter(prefix="/api/observatory", tags=["Observatory"])


class ResumenTemporada(BaseModel):
    brier_qbe: float
    brier_mercado: Optional[float] = None
    alpha_calibracion_pct: Optional[float] = None
    n_partidos_qbe: int
    n_partidos_mercado: int = 0
    brier_qbe_muestra_mercado: Optional[float] = None
    fuente_qbe: str = "qbe_historico"
    fuente_mercado: str = "no_disponible"
    mercado_disponible: bool = False
    nota_metodologica: Optional[str] = None


class JornadaResumen(BaseModel):
    jornada: int
    n_partidos: int
    brier_qbe: float
    brier_mercado: Optional[float] = None
    alpha_calibracion_pct: Optional[float] = None


class CalibrationReportResponse(BaseModel):
    generado_en: datetime
    liga: str
    temporada: Optional[str] = None
    resumen_temporada: ResumenTemporada
    jornadas: List[JornadaResumen] = Field(default_factory=list)


def _temporada_mas_reciente(base: BaseDatosSoloLectura) -> Optional[str]:
    """Temporada por omisión: la más reciente declarada en `seasons` (nunca inventada)."""
    filas = base.ejecutar_select(
        "SELECT id FROM seasons ORDER BY year DESC, created_at DESC, id DESC LIMIT 1"
    )
    return str(filas[0]["id"]) if filas else None


def _desenlace(score_home: int, score_away: int) -> str:
    """Traducción factual 1X2; no interpreta ni imputa marcadores."""
    if score_home > score_away:
        return "LOCAL"
    if score_home < score_away:
        return "VISITANTE"
    return "EMPATE"


def _reporte_sin_historico(
    ruta: Path, temporada: Optional[str]
) -> CalibrationReportResponse:
    """Degradación controlada cuando el histórico no está aprovisionado.

    El arranque de la app no toca el archivo; sólo una consulta histórica lo
    necesita. Si falta, se devuelve el contrato completo con cero partidos y una
    nota accionable —jamás 500, jamás cifras inventadas— y `/visor` sigue
    renderizando su estado vacío explícito.
    """
    nota = (
        f"Histórico no aprovisionado en {ruta}. La app arranca y el visor sigue "
        "disponible; aprovisione el archivo para evaluar la calibración."
    )
    return CalibrationReportResponse(
        generado_en=datetime.now(timezone.utc),
        liga="N/D",
        temporada=temporada,
        resumen_temporada=ResumenTemporada(
            brier_qbe=0.0,
            brier_mercado=None,
            alpha_calibracion_pct=None,
            n_partidos_qbe=0,
            n_partidos_mercado=0,
            brier_qbe_muestra_mercado=None,
            fuente_qbe="no_disponible",
            fuente_mercado="no_disponible",
            mercado_disponible=False,
            nota_metodologica=nota,
        ),
        jornadas=[],
    )


def construir_reporte(
    *,
    league_id: Optional[str] = None,
    temporada: Optional[str] = None,
    incluir_mercado: bool = True,
    brier_fn: Callable[[List[Dict[str, Any]]], float] = calcular_brier_multicategorico,
) -> CalibrationReportResponse:
    """Lee el histórico en modo `ro` y agrega Brier QBE por temporada y jornada.

    Por omisión se reporta la temporada más reciente de `seasons`; el histórico
    contiene 32 temporadas y mezclarlas en un mismo `jornada` produciría un
    agregado sin significado. D-1: el histórico no porta cuotas 1X2; el Brier de
    mercado y el Alpha se devuelven como `None` (nunca `0.0`).

    Si el archivo histórico no existe (despliegue sin aprovisionar), se degrada
    de forma controlada a un reporte vacío con nota explícita: sin excepción, sin
    cifras fabricadas.
    """
    ruta = Path(HISTORICO_DB)
    if not ruta.is_file():
        return _reporte_sin_historico(ruta, temporada)

    base = BaseDatosSoloLectura(ruta)
    temporada_efectiva = temporada or _temporada_mas_reciente(base)
    sql = """
        SELECT m.id,
               m.competition_id,
               m.season_id,
               m.matchday_num,
               m.score_home,
               m.score_away,
               d.p_local,
               d.p_empate,
               d.p_visitante
        FROM matches AS m
        JOIN sovereign_distributions AS d ON d.match_id = m.id
        WHERE m.score_home IS NOT NULL
          AND m.score_away IS NOT NULL
          AND m.matchday_num IS NOT NULL
          AND d.p_local IS NOT NULL
          AND d.p_empate IS NOT NULL
          AND d.p_visitante IS NOT NULL
    """
    params: List[Any] = []
    if league_id:
        sql += " AND m.competition_id = ?"
        params.append(league_id)
    if temporada_efectiva:
        sql += " AND m.season_id = ?"
        params.append(temporada_efectiva)
    sql += " ORDER BY m.matchday_num ASC, m.id ASC"

    filas = base.ejecutar_select(sql, tuple(params))

    todos: List[Dict[str, Any]] = []
    por_jornada: Dict[int, List[Dict[str, Any]]] = {}
    competiciones: set[str] = set()

    for fila in filas:
        try:
            p_local = float(fila["p_local"])
            p_empate = float(fila["p_empate"])
            p_visitante = float(fila["p_visitante"])
            score_home = int(fila["score_home"])
            score_away = int(fila["score_away"])
            jornada = int(fila["matchday_num"])
        except (TypeError, ValueError):
            continue

        if not all(0.0 <= p <= 1.0 for p in (p_local, p_empate, p_visitante)):
            continue

        registro = {
            "p_local": p_local,
            "p_empate": p_empate,
            "p_visitante": p_visitante,
            "resultado": _desenlace(score_home, score_away),
        }
        todos.append(registro)
        por_jornada.setdefault(jornada, []).append(registro)
        if fila["competition_id"]:
            competiciones.add(str(fila["competition_id"]))

    brier_qbe = float(brier_fn(todos)) if todos else 0.0
    if len(competiciones) == 1:
        liga = next(iter(competiciones))
    elif competiciones:
        liga = "MULTI"
    else:
        liga = "N/D"

    etiqueta_temporada = temporada_efectiva or "sin temporada declarada"
    if not todos:
        nota = f"Sin partidos evaluables para {etiqueta_temporada}."
    elif incluir_mercado:
        nota = (
            f"Temporada {etiqueta_temporada}. El histórico no porta cuotas 1X2; "
            "el Brier de mercado y el Alpha requieren snapshot vivo (D-1)."
        )
    else:
        nota = f"Temporada {etiqueta_temporada}. Mercado no solicitado en esta invocación."

    jornadas = [
        JornadaResumen(
            jornada=jornada,
            n_partidos=len(registros),
            brier_qbe=round(float(brier_fn(registros)), 6),
            brier_mercado=None,
            alpha_calibracion_pct=None,
        )
        for jornada, registros in sorted(por_jornada.items())
    ]

    return CalibrationReportResponse(
        generado_en=datetime.now(timezone.utc),
        liga=liga,
        temporada=temporada_efectiva,
        resumen_temporada=ResumenTemporada(
            brier_qbe=round(brier_qbe, 6),
            brier_mercado=None,
            alpha_calibracion_pct=None,
            n_partidos_qbe=len(todos),
            n_partidos_mercado=0,
            brier_qbe_muestra_mercado=None,
            fuente_qbe="qbe_historico",
            fuente_mercado="no_disponible",
            mercado_disponible=False,
            nota_metodologica=nota,
        ),
        jornadas=jornadas,
    )


@router.get(
    "/calibration-report",
    response_model=CanonicalReportResponse,
    deprecated=True,
    summary="[OBSOLETO] Alias de /api/observatory/backtesting/calibration-report",
)
def reporte_calibracion(
    response: Response,
    league_id: Optional[int] = Query(
        None,
        description="ID de liga de la bóveda 3NF (ej. 1 = Liga MX). Sin valor: universo global.",
    ),
    db: Session = Depends(get_db_ro),
) -> Dict[str, Any]:
    """[OBSOLETO desde 2026-10-28] Alias delgado del reporte canónico de calibración.

    Resolución D-1 (`SPRINT-OBSERVATORY-SNAPSHOT-AND-ARCH-ALIGNMENT`): se unifica
    la calibración en UN solo builder —`reporte_calibracion_canonico`, bóveda 3NF
    del snapshot— para impedir que dos endpoints con el mismo nombre sirvan
    universos distintos. Esta puerta permanece abierta sólo por compatibilidad y
    se declara obsoleta en cabeceras y en OpenAPI.

    Contrato anterior retirado (declarado, no silencioso): `temporada` e
    `incluir_mercado` ya no existen aquí; el universo es la bóveda 3NF y el
    reporte de temporada sobre `qbe_historico.db` sigue disponible en `/visor`
    como ruta de presentación. Sin snapshot, ambos endpoints responden **503**
    con instrucción de materialización, jamás 500.
    """
    response.headers["Deprecation"] = "true"
    response.headers["Warning"] = (
        '299 - "Endpoint obsoleto: use /api/observatory/backtesting/calibration-report"'
    )
    response.headers["Link"] = (
        '</api/observatory/backtesting/calibration-report>; rel="successor-version"'
    )
    return reporte_calibracion_canonico(db, league_id)
