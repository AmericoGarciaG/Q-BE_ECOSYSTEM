"""Servicio REST del Data Nexus (Ingesta).

Expone el estado de deriva que Business consume por HTTP. No importa Business ni conoce
sus routers: la única frontera es el contrato JSON de `ReporteDeriva`.

Reglas de gobierno:
  * [ARCH-1.4.12-B] cuatro luces originales + [ARCH-1.4.12-C] quinta luz de homologación.
  * [ARCH-1.5.0] toda lectura pasa por `PersistenceGateway.read_session()`.
  * [GOVERNANCE-01] ausencia de evidencia ⇒ `SIN_VEREDICTO`; nunca una cifra inventada.
  * El endpoint JAMÁS responde 500 por bóveda vacía: degrada a ⚪ con motivo explícito.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from src.config import settings
from src.ingestion.coherence_auditor import (
    GLIFO_NIVEL,
    _agregar_nivel,
    _expediente_desde_fixture,
    auditar_coherencia_partido,
)
from src.ingestion.daemons.centinela_mercado import FRONTERA_LIGA_MX_ID
from src.storage.gateway import PersistenceGateway
from src.storage.models import FixtureSnapshot, League, Match, Slate, SovereignDistribution
from src.storage.sync_service import (
    _fixture_operable_en_ventanilla,
    resolver_jornada_actual_dinamica,
)

logger = logging.getLogger("qbe_ingestion_service")

app = FastAPI(title="Q-BE Ingestion — Data Nexus")

# ── Contrato legislado [ARCH-1.4.12-B] / [ARCH-1.6.2-B] / [ARCH-1.4.12-C] ─────────────────────
UMBRAL_CUOTAS_STALE_MIN = 45
UMBRAL_STALENESS_MIN = 150
UMBRAL_HOMOLOGACION_PENDIENTE = 5

NIVEL_CONFORME = "CONFORME"
NIVEL_ADVERTENCIA = "ADVERTENCIA"
NIVEL_DISCREPANCIA = "DISCREPANCIA"
NIVEL_SIN_VEREDICTO = "SIN_VEREDICTO"

ESTADOS_PARTIDO_CONCLUIDO: Tuple[str, ...] = ("FINISHED", "FINALIZADO")
DIMENSIONES_JORNADA: Tuple[str, ...] = ("deportivo", "mercado", "integridad")
TAREA_HOMOLOGACION = "homologar_temporada_optah2h"
TAREA_CADENA_PRE_JORNADA = "cadena_pre_jornada"
TAREA_CADENA_PROGOL = "cadena_progol"
DIMENSION_A_TAREA: Dict[str, str] = {
    "deportivo": "centinela_deportivo",
    "mercado": "centinela_mercado",
    "integridad": "auditar_coherencia_cartelera",
    "progol": TAREA_CADENA_PROGOL,
}

# ── Whitelist de despacho: sólo identificadores certificados, cero texto libre ─────────────────
# Cada entrada es una secuencia de comandos `python -m modulo [args]`; el despachador nunca usa
# `shell=True` ni interpola el payload del cliente.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
TAREAS_EJECUTABLES: Dict[str, Tuple[Tuple[str, Tuple[str, ...]], ...]] = {
    "centinela_deportivo": (("src.ingestion.daemons.centinela_deportivo", ()),),
    "centinela_mercado": (("src.ingestion.daemons.centinela_mercado", ()),),
    "centinela_progol": (("src.ingestion.daemons.centinela_progol", ()),),
    "centinela_macro": (("src.ingestion.daemons.centinela_macro", ("--liga-id", "230")),),
    "auditar_coherencia_cartelera": (("src.ingestion.coherence_auditor", ("--check",)),),
    "cadena_pre_jornada": (
        ("src.ingestion.daemons.centinela_deportivo", ()),
        ("src.ingestion.daemons.centinela_mercado", ()),
        ("src.ingestion.coherence_auditor", ("--check",)),
    ),
    "cadena_progol": (("src.ingestion.daemons.centinela_progol", ()),),
}

_BOVEDA_RESUELTA = False


class TareaRequest(BaseModel):
    """Entrada tolerante al contrato de la SPA (`task_id`) y al de la directiva (`tarea`)."""

    tarea: Optional[str] = None
    task_id: Optional[str] = None


# ── Utilidades temporales (misma semántica que el adaptador de Business) ──────────────────────
def _sello_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _reloj_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _reloj_local() -> datetime:
    return datetime.now()


def _marca_utc_naive(valor: Any) -> Optional[datetime]:
    if isinstance(valor, datetime):
        marca = valor
    elif isinstance(valor, str) and valor.strip():
        try:
            marca = datetime.fromisoformat(valor.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if marca.tzinfo is not None:
        marca = marca.astimezone(timezone.utc).replace(tzinfo=None)
    return marca


def _marca_local_naive(valor: Any) -> Optional[datetime]:
    if isinstance(valor, datetime):
        return valor.replace(tzinfo=None)
    if isinstance(valor, str) and valor.strip():
        try:
            return datetime.fromisoformat(valor.strip().replace("Z", "")).replace(tzinfo=None)
        except ValueError:
            return None
    return None


# ── Resolución de la bóveda ───────────────────────────────────────────────────────────────────
def _ruta_fisica_sqlite() -> Optional[Path]:
    """Ruta física de la SQLite gobernada; `None` para memoria o motores no SQLite."""
    try:
        url = make_url(settings.DATABASE_URL)
    except Exception:
        return None
    if url.get_backend_name() != "sqlite":
        return None
    database = url.database
    if not database or database == ":memory:":
        return None
    ruta = Path(database)
    if not ruta.is_absolute():
        ruta = Path.cwd() / ruta
    return ruta


def _boveda_legada() -> Path:
    """Bóveda viva del monorepo legado, usada sólo como fallback de lectura/operación."""
    return Path(__file__).resolve().parents[3].parent / "Q_BE_CD_WEB" / "data" / "qbe_database.db"


def _configurar_boveda() -> None:
    """Si no hay URL explícita y la SQLite local está ausente/vacía, apunta a la bóveda viva.

    El fallback evita que el servicio arranque contra un archivo vacío recién creado por una
    prueba y devuelva un veredicto falso. `DATABASE_URL` explícita siempre tiene precedencia.
    """
    global _BOVEDA_RESUELTA
    if _BOVEDA_RESUELTA:
        return
    _BOVEDA_RESUELTA = True
    if os.environ.get("DATABASE_URL", "").strip():
        return

    ruta = _ruta_fisica_sqlite()
    if ruta is not None and ruta.is_file() and ruta.stat().st_size > 0:
        return
    legada = _boveda_legada()
    if not (legada.is_file() and legada.stat().st_size > 0):
        return

    settings.DATABASE_URL = f"sqlite:///{legada.as_posix()}"
    if PersistenceGateway._instance is not None:
        try:
            PersistenceGateway._instance.engine.dispose()
        except Exception:
            pass
        PersistenceGateway._instance = None
    logger.info("Bóveda resuelta al fallback legado: %s", legada)


def _boveda_disponible() -> bool:
    _configurar_boveda()
    ruta = _ruta_fisica_sqlite()
    if ruta is None:
        return True
    try:
        return ruta.is_file() and ruta.stat().st_size > 0
    except OSError:
        return False


# ── Dimensiones del semáforo ─────────────────────────────────────────────────────────────────
def _dimension(nivel: str, detalle: str, metrica: Optional[float] = None) -> Dict[str, Any]:
    if nivel not in GLIFO_NIVEL:
        raise ValueError(f"Nivel semafórico ajeno al canon [ARCH-1.4.34]: {nivel!r}")
    return {
        "nivel": nivel,
        "glifo": GLIFO_NIVEL[nivel],
        "detalle": detalle,
        "metrica": metrica,
    }


def _sin_veredicto(detalle: str) -> Dict[str, Any]:
    return _dimension(NIVEL_SIN_VEREDICTO, detalle)


def _sello_cuotas_mas_reciente(fixtures: Sequence[Dict[str, Any]]) -> Optional[datetime]:
    sellos: List[datetime] = []
    for fixture in fixtures:
        operadores = fixture.get("momios_operadores")
        if not isinstance(operadores, dict):
            continue
        for captura in operadores.values():
            if not isinstance(captura, dict):
                continue
            sello = _marca_utc_naive(captura.get("updated_at"))
            if sello is not None:
                sellos.append(sello)
    return max(sellos) if sellos else None


def _status_mercado(fixtures: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    if not any(_fixture_operable_en_ventanilla(fx) for fx in fixtures):
        return _sin_veredicto(
            "Fuera de ventanilla de capital: no se exige frescura de cuotas sobre una jornada cerrada."
        )
    sello = _sello_cuotas_mas_reciente(fixtures)
    if sello is None:
        return _sin_veredicto(
            "La bóveda no registra sello de captura de cuotas: frescura indeterminable (cero invención)."
        )
    delta_min = (_reloj_utc() - sello).total_seconds() / 60.0
    if delta_min > UMBRAL_CUOTAS_STALE_MIN:
        return _dimension(
            NIVEL_DISCREPANCIA,
            f"Cuotas rezagadas {delta_min:.0f} min (umbral {UMBRAL_CUOTAS_STALE_MIN} min): "
            "el mercado debe re-escanearse antes de exponer la cartelera.",
            round(delta_min, 2),
        )
    return _dimension(
        NIVEL_CONFORME,
        f"Cuotas frescas: {delta_min:.1f} min desde la última captura "
        f"(umbral {UMBRAL_CUOTAS_STALE_MIN} min).",
        round(delta_min, 2),
    )


def _status_deportivo(fixtures: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    rezagados: List[str] = []
    for fixture in fixtures:
        if str(fixture.get("estado") or "").strip().upper() != "PROGRAMADO":
            continue
        inicio = _marca_local_naive(fixture.get("fecha_dt"))
        if inicio is None:
            continue
        if (_reloj_local() - inicio) > timedelta(minutes=UMBRAL_STALENESS_MIN):
            rezagados.append(str(fixture.get("id_partido") or fixture.get("local") or "sin-id"))
    if not rezagados:
        return _dimension(
            NIVEL_CONFORME,
            f"Cero partidos PROGRAMADO con inicio vencido hace más de {UMBRAL_STALENESS_MIN} min.",
            0.0,
        )
    muestra = ", ".join(rezagados[:5]) + ("…" if len(rezagados) > 5 else "")
    return _dimension(
        NIVEL_DISCREPANCIA,
        f"{len(rezagados)} partido(s) PROGRAMADO con inicio vencido hace más de "
        f"{UMBRAL_STALENESS_MIN} min ({muestra}): el estado deportivo exige refresco.",
        float(len(rezagados)),
    )


def _status_progol(session: Session) -> Dict[str, Any]:
    slates = session.query(Slate).order_by(Slate.created_at.desc()).all()
    abiertos = [s for s in slates if str(s.status or "").strip().upper() == "OPEN"]
    if not abiertos:
        return _sin_veredicto("La bóveda no registra concurso de quiniela abierto.")
    cierres = [(s, _marca_utc_naive(s.fecha_cierre)) for s in abiertos]
    vencidos = [s.id for s, cierre in cierres if cierre is not None and cierre < _reloj_utc()]
    if vencidos:
        return _dimension(
            NIVEL_DISCREPANCIA,
            f"{len(vencidos)} concurso(s) abierto(s) con fecha de cierre superada "
            f"({', '.join(vencidos)}): sincronizar el concurso vigente.",
            float(len(vencidos)),
        )
    vigentes = [cierre for _, cierre in cierres if cierre is not None]
    if not vigentes:
        etiquetas = ", ".join(s.id for s in abiertos)
        return _sin_veredicto(
            f"Concurso(s) abierto(s) {etiquetas} sin fecha de cierre publicada por la fuente: "
            "cero fecha inventada."
        )
    return _dimension(NIVEL_CONFORME, f"Cierre vigente: {min(vigentes).isoformat()} UTC.")


def _status_integridad(fixtures: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    if not fixtures:
        return _sin_veredicto("Sin cartelera persistida en la jornada activa: nada que auditar.")
    reportes = [auditar_coherencia_partido(_expediente_desde_fixture(fx)) for fx in fixtures]
    hallazgos = [h for reporte in reportes for h in reporte.hallazgos]
    nivel = _agregar_nivel(hallazgos).value
    conteo = {
        nombre: sum(1 for r in reportes if r.nivel_global.value == nombre)
        for nombre in (NIVEL_DISCREPANCIA, NIVEL_ADVERTENCIA, NIVEL_CONFORME, NIVEL_SIN_VEREDICTO)
    }
    detalle = (
        f"{len(reportes)} partido(s) auditados"
        f" · {GLIFO_NIVEL[NIVEL_DISCREPANCIA]} {conteo[NIVEL_DISCREPANCIA]}"
        f" · {GLIFO_NIVEL[NIVEL_ADVERTENCIA]} {conteo[NIVEL_ADVERTENCIA]}"
        f" · {GLIFO_NIVEL[NIVEL_CONFORME]} {conteo[NIVEL_CONFORME]}"
        f" · {GLIFO_NIVEL[NIVEL_SIN_VEREDICTO]} {conteo[NIVEL_SIN_VEREDICTO]}"
    )
    return _dimension(nivel, detalle, float(conteo[NIVEL_DISCREPANCIA]))


def _status_homologacion(session: Session) -> Tuple[Dict[str, Any], int]:
    filas = (
        session.query(Match.id, SovereignDistribution.audit_trace_json)
        .outerjoin(SovereignDistribution, SovereignDistribution.match_id == Match.id)
        .filter(Match.status.in_(ESTADOS_PARTIDO_CONCLUIDO))
        .all()
    )
    if not filas:
        return (
            _sin_veredicto(
                "La bóveda no registra partidos concluidos: homologación no exigible (cero invención)."
            ),
            0,
        )

    pendientes: List[str] = []
    for identificador, traza in filas:
        insumos = traza.get("insumos_factivados") if isinstance(traza, dict) else None
        if not isinstance(insumos, dict) or not insumos:
            pendientes.append(str(identificador))

    total = len(filas)
    if len(pendientes) > UMBRAL_HOMOLOGACION_PENDIENTE:
        muestra = ", ".join(sorted(pendientes)[:3]) + ("…" if len(pendientes) > 3 else "")
        return (
            _dimension(
                NIVEL_DISCREPANCIA,
                f"{len(pendientes)} de {total} partido(s) concluido(s) sin insumos fácticos "
                f"homologados, por encima del umbral {UMBRAL_HOMOLOGACION_PENDIENTE} ({muestra}): "
                "la temporada debe re-homologarse.",
                float(len(pendientes)),
            ),
            len(pendientes),
        )
    if pendientes:
        return (
            _dimension(
                NIVEL_ADVERTENCIA,
                f"{len(pendientes)} de {total} partido(s) concluido(s) sin insumos fácticos "
                f"homologados (umbral {UMBRAL_HOMOLOGACION_PENDIENTE}): rezago tolerable, "
                "subsanable con la Cadena Post-Jornada.",
                float(len(pendientes)),
            ),
            len(pendientes),
        )
    return (
        _dimension(
            NIVEL_CONFORME,
            f"{total} partido(s) concluido(s) con insumos fácticos homologados en su traza soberana.",
            0.0,
        ),
        0,
    )


def _accion_recomendada(
    dimensiones: Dict[str, Dict[str, Any]], homologacion_pendiente: int = 0
) -> Dict[str, Any]:
    """Traduce la deriva observada en UNA acción certificada y ejecutable."""
    deriva = [
        dimension
        for dimension in ("deportivo", "mercado", "integridad", "progol")
        if dimensiones[dimension]["nivel"] == NIVEL_DISCREPANCIA
    ]
    homologacion_exigible = homologacion_pendiente > UMBRAL_HOMOLOGACION_PENDIENTE

    if not deriva:
        if not homologacion_exigible:
            return {
                "task_id": None,
                "motivo": "Cero deriva: las cuatro luces del semáforo están al día.",
                "deriva": [],
            }
        if TAREA_HOMOLOGACION in TAREAS_EJECUTABLES:
            return {
                "task_id": TAREA_HOMOLOGACION,
                "motivo": (
                    "Existen partidos concluidos pendientes de homologación factual. "
                    "Ejecutar Cadena Post-Jornada o Homologación Opta."
                ),
                "deriva": ["homologacion"],
            }
        return {
            "task_id": None,
            "motivo": (
                "Homologación pendiente sin ejecutor certificado en el Data Nexus; "
                "se requiere un adaptador autorizado para homologar_temporada_optah2h."
            ),
            "deriva": ["homologacion"],
        }

    deriva_jornada = [d for d in DIMENSIONES_JORNADA if d in deriva]
    if len(deriva_jornada) >= 2:
        tarea: Optional[str] = TAREA_CADENA_PRE_JORNADA
    elif deriva_jornada:
        tarea = DIMENSION_A_TAREA[deriva_jornada[0]]
    else:
        tarea = DIMENSION_A_TAREA["progol"]

    motivo = " · ".join(f"{d}: {dimensiones[d]['detalle']}" for d in deriva)
    if homologacion_exigible:
        motivo = (
            f"{motivo} · Existen partidos concluidos pendientes de homologación factual. "
            "Ejecutar Cadena Post-Jornada o Homologación Opta."
        )
    if tarea not in TAREAS_EJECUTABLES:
        return {
            "task_id": None,
            "motivo": f"Deriva sin ejecutor certificado en la whitelist de Ingesta: {motivo}",
            "deriva": deriva,
        }
    return {"task_id": tarea, "motivo": motivo, "deriva": deriva}


# ── Ensamblado del reporte ────────────────────────────────────────────────────────────────────
def _liga_3nf(session: Session) -> Optional[League]:
    return (
        session.query(League)
        .filter((League.fotmob_id == FRONTERA_LIGA_MX_ID) | (League.id == FRONTERA_LIGA_MX_ID))
        .first()
    )


def _fixtures_jornada(
    session: Session, league_id: int, jornada: Optional[int]
) -> List[Dict[str, Any]]:
    if jornada is None:
        return []
    snapshot = (
        session.query(FixtureSnapshot)
        .filter(
            FixtureSnapshot.league_id == league_id,
            FixtureSnapshot.matchday == int(jornada),
        )
        .order_by(FixtureSnapshot.updated_at.desc())
        .first()
    )
    if snapshot is None or not snapshot.matches_json:
        return []
    return [fx for fx in snapshot.matches_json if isinstance(fx, dict)]


def _reporte_sin_boveda(motivo: str) -> Dict[str, Any]:
    return {
        "regimen": "SOLO_LECTURA",
        "evaluado_en_utc": _sello_utc(),
        "jornada_activa": None,
        "liga_3nf": None,
        "status_mercado": _sin_veredicto(motivo),
        "status_deportivo": _sin_veredicto(motivo),
        "status_progol": _sin_veredicto(motivo),
        "status_integridad": _sin_veredicto(motivo),
        "status_homologacion": _sin_veredicto(motivo),
        "accion_recomendada": {"task_id": None, "motivo": motivo, "deriva": []},
        "status": "OK",
        "fuente": "qbe_ingestion",
    }


def _construir_reporte(session: Session) -> Dict[str, Any]:
    liga = _liga_3nf(session)
    jornada = resolver_jornada_actual_dinamica(session, int(liga.id)) if liga else None
    fixtures = _fixtures_jornada(session, int(liga.id), jornada) if liga else []

    status_mercado = _status_mercado(fixtures)
    status_deportivo = _status_deportivo(fixtures)
    status_progol = _status_progol(session)
    status_integridad = _status_integridad(fixtures)
    status_homologacion, pendientes = _status_homologacion(session)
    dimensiones = {
        "mercado": status_mercado,
        "deportivo": status_deportivo,
        "progol": status_progol,
        "integridad": status_integridad,
        "homologacion": status_homologacion,
    }
    return {
        "regimen": "SOLO_LECTURA",
        "evaluado_en_utc": _sello_utc(),
        "jornada_activa": jornada,
        "liga_3nf": int(liga.id) if liga else None,
        "status_mercado": status_mercado,
        "status_deportivo": status_deportivo,
        "status_progol": status_progol,
        "status_integridad": status_integridad,
        "status_homologacion": status_homologacion,
        "accion_recomendada": _accion_recomendada(dimensiones, pendientes),
        # Compatibilidad con el juez puente de Slice 4B; el contrato nuevo es aditivo.
        "status": "OK",
        "fuente": "qbe_ingestion",
    }


def _leer_reporte() -> Dict[str, Any]:
    if not _boveda_disponible():
        return _reporte_sin_boveda(
            "Bóveda 3NF no disponible: la sonda de deriva degrada a ⚪ sin inventar veredicto."
        )
    try:
        gateway = PersistenceGateway()
        with gateway.read_session() as session:
            return _construir_reporte(session)
    except Exception as exc:  # bóveda vacía, esquema ausente o corrupción: degradación honesta
        logger.warning("Sonda de deriva sin bóveda legible: %s: %s", type(exc).__name__, exc)
        return _reporte_sin_boveda(
            f"Bóveda 3NF no legible ({type(exc).__name__}): la sonda degrada a ⚪."
        )


# ── Superficie HTTP ──────────────────────────────────────────────────────────────────────────
def _puerto() -> int:
    crudo = os.environ.get("PORT_INGESTION", "").strip()
    if crudo:
        try:
            return int(crudo)
        except ValueError:
            pass
    url = os.environ.get("QBE_INGESTION_URL", "").strip()
    if url:
        try:
            puerto = urlparse(url).port
            if puerto:
                return int(puerto)
        except ValueError:
            pass
    return 8002


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok", "service": "qbe_ingestion", "port": _puerto()}


@app.get("/api/ingestion/status/drift")
def estado_deriva(league_id: Optional[int] = None) -> Dict[str, Any]:
    """Ejecuta las sondas de coherencia sobre la bóveda 3NF y publica el semáforo completo."""
    # `league_id` se conserva por compatibilidad de query string; la frontera institucional es 262.
    _ = league_id
    return _leer_reporte()


def _resolver_tarea(payload: TareaRequest) -> str:
    tarea = (payload.tarea or payload.task_id or "").strip()
    if not tarea:
        raise HTTPException(status_code=400, detail="Falta 'tarea' o 'task_id' en el payload.")
    if tarea not in TAREAS_EJECUTABLES:
        raise HTTPException(
            status_code=400,
            detail=f"Tarea no certificada en la whitelist de Ingesta: {tarea}",
        )
    return tarea


def _ejecutar_comando(modulo: str, argumentos: Sequence[str], timeout_s: float) -> Dict[str, Any]:
    entorno = os.environ.copy()
    entorno["DATABASE_URL"] = settings.DATABASE_URL
    entorno["PYTHONIOENCODING"] = "utf-8"
    comando = [sys.executable, "-m", modulo, *argumentos]
    inicio = time.perf_counter()
    try:
        completado = subprocess.run(
            comando,
            cwd=str(PROJECT_ROOT),
            env=entorno,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_s,
            check=False,
        )
        salida = (completado.stdout or "") + (completado.stderr or "")
        codigo = int(completado.returncode)
    except subprocess.TimeoutExpired as exc:
        salida = (exc.stdout or "") + (exc.stderr or "")
        salida += f"\n[TIMEOUT] La tarea excedió {timeout_s:.0f}s."
        codigo = 124
    except Exception as exc:
        salida = f"[ERROR] No se pudo despachar {modulo}: {type(exc).__name__}: {exc}"
        codigo = 1
    return {
        "modulo": modulo,
        "exit_code": codigo,
        "output": salida,
        "duration_s": round(time.perf_counter() - inicio, 2),
    }


@app.post("/api/ingestion/tasks/run")
def ejecutar_tarea_administrativa(payload: TareaRequest) -> Dict[str, Any]:
    """Despacha una tarea certificada en subproceso controlado y devuelve su salida."""
    tarea = _resolver_tarea(payload)
    _configurar_boveda()
    inicio = time.perf_counter()
    resultados: List[Dict[str, Any]] = []
    for modulo, argumentos in TAREAS_EJECUTABLES[tarea]:
        resultados.append(_ejecutar_comando(modulo, argumentos, timeout_s=900.0))
        if resultados[-1]["exit_code"] != 0:
            break

    salida = "\n".join(
        f"=== {resultado['modulo']} (exit {resultado['exit_code']}) ===\n{resultado['output']}"
        for resultado in resultados
    )
    codigo = next(
        (resultado["exit_code"] for resultado in resultados if resultado["exit_code"] != 0),
        0,
    )
    return {
        "task_id": tarea,
        "exit_code": codigo,
        "output": salida,
        "duration_s": round(time.perf_counter() - inicio, 2),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=_puerto())
