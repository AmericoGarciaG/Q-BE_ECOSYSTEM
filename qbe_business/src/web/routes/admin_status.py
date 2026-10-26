# -*- coding: utf-8 -*-
"""
Kybern Industrial — [ARCH-1.4.12-B] Detector de Deriva y Semáforo de Desactualización de Fuentes.
Controlador REST del Centro de Control Industrial: `GET /api/admin/status/drift`.

[SOLO LECTURA]: la sonda JAMÁS escribe ni muta la bóveda 3NF ([GOVERNANCE-01]); ninguna
constante de negocio se inventa aquí:

  * La jornada auditada NO se quema: emana del resolutor canónico
    `resolver_jornada_actual_dinamica` ([ARCH-1.6.15 / ARCH-1.4.10]), en paridad exacta con la
    ventanilla de capital que gobierna la Mesa de Apuestas.
  * `UMBRAL_CUOTAS_STALE_MIN` = 45 min ⇒ [ARCH-1.4.12-B] (deriva de mercado).
  * `UMBRAL_STALENESS_MIN` = 150 min ⇒ [ARCH-1.6.2-B] (`docs/ARCH.md` L606): ningún partido con
    inicio vencido hace más de 2.5 h puede seguir catalogado como PROGRAMADO. Transcripción del
    lazo canónico de `src/storage/sync_service.py` (L284).
  * El semáforo de integridad REUTILIZA el canon puro de [ARCH-1.4.34]
    (`scripts.auditoria.auditar_coherencia_cartelera`): cero reimplementación de las seis sondas
    y cero duplicación de su vocabulario (`NivelSeveridad` / `GLIFO_NIVEL`).
  * Iconografía Universal ([ARCH-1.4.12-B] · Decreto `VAR-2026-DRIFT-STREAM-MAP`): los glifos se
    heredan ÍNTEGROS de `GLIFO_NIVEL` del canon (🟢 / 🟡 / 🔴 / ⚪). Este adaptador JAMÁS escribe un
    glifo literal —ni el detalle de integridad, que también se compone del canon—, por lo que la
    erradicación del emoji de bandera regional (`U+1F1FE U+1F1EA`, que Windows descompone en `YE`)
    se propaga a la pantalla y al JSON sin una sola sustitución local.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.storage.gateway import PersistenceGateway
from src.storage.models import (
    FixtureSnapshot,
    League,
    Match,
    Slate,
    SovereignDistribution,
)
from src.storage.sync_service import (
    _fixture_operable_en_ventanilla,
    resolver_jornada_actual_dinamica,
)

router = APIRouter(prefix="/api/admin/status", tags=["Admin Control Center"])

# [ARCH-1.6.21] Frontera de competencia: la jornada auditada se resuelve contra la Liga MX.
FRONTERA_LIGA_MX_ID = 262

# [ARCH-1.4.12-B] Frescura exigida a las cuotas de la jornada activa mientras la ventanilla de
# capital permanezca abierta (Δt > 45 min ⇒ deriva de mercado).
UMBRAL_CUOTAS_STALE_MIN = 45

# [ARCH-1.6.2-B] Cuarentena por staleness: umbral de inicio vencido (150 min) antes de exigir el
# refresco de estado deportivo.
UMBRAL_STALENESS_MIN = 150

# [ARCH-1.4.12-C] Identificadores certificados de las cadenas temporales homologadas.
TAREA_CADENA_PRE_JORNADA = "cadena_pre_jornada"
TAREA_CADENA_PROGOL = "cadena_progol"

# [ARCH-1.4.12-C] Enmienda 2026-10-17: auditoría de homologación factual. La luz es ADITIVA: las
# cuatro dimensiones originales de [ARCH-1.4.12-B] conservan su contrato. Un partido concluido sin
# `insumos_factivados` en su traza soberana (traza legada o ausente) está pendiente de homologar; por
# encima del umbral la recomendación sugiere la tarea certificada de reconstrucción integral.
TAREA_HOMOLOGACION_OPTA = "homologar_temporada_optah2h"
UMBRAL_HOMOLOGACION_PENDIENTE = 5
MOTIVO_HOMOLOGACION_PENDIENTE = (
    "Existen partidos concluidos pendientes de homologación factual. "
    "Ejecutar Cadena Post-Jornada o Homologación Opta."
)
ESTADOS_PARTIDO_CONCLUIDO: Tuple[str, ...] = ("FINISHED", "FINALIZADO")

# Vocabulario del semáforo: los VALORES son los del canon [ARCH-1.4.34]; `_dimension` los valida
# contra `GLIFO_NIVEL` (cualquier literal ajeno revienta de inmediato: cero invención).
NIVEL_CONFORME = "CONFORME"
NIVEL_ADVERTENCIA = "ADVERTENCIA"
NIVEL_DISCREPANCIA = "DISCREPANCIA"
NIVEL_SIN_VEREDICTO = "SIN_VEREDICTO"

# [ARCH-1.4.12-B] Puente deriva ➔ ejecutor: cada dimensión declara su tarea certificada.
DIMENSION_A_TAREA: Dict[str, str] = {
    "deportivo": "centinela_deportivo",
    "mercado": "centinela_mercado",
    "integridad": "auditar_coherencia_cartelera",
    "progol": TAREA_CADENA_PROGOL,
}
# Orden de precedencia del capital: las tres dimensiones de la jornada activa.
DIMENSIONES_JORNADA: Tuple[str, ...] = ("deportivo", "mercado", "integridad")

_CANON_SONDA: Optional[Dict[str, Any]] = None


class EstadoDimension(BaseModel):
    """[ARCH-1.4.12-B] Veredicto de una dimensión del semáforo de deriva."""
    nivel: str = Field(..., description="CONFORME | ADVERTENCIA | DISCREPANCIA | SIN_VEREDICTO")
    glifo: str = Field(..., description="Glifo del canon semafórico [ARCH-1.4.34]")
    detalle: str = Field(..., description="Lectura factual que sustenta el veredicto")
    metrica: Optional[float] = Field(
        None, description="Métrica observable: minutos de rezago, partidos vencidos, etc."
    )


class AccionRecomendada(BaseModel):
    """[ARCH-1.4.12-B] Acción sugerida, unívoca y SIEMPRE perteneciente a la whitelist."""
    task_id: Optional[str] = Field(None, description="Identificador certificado (None ⇒ cero deriva)")
    motivo: str = Field(..., description="Evidencia textual de la deriva observada")
    deriva: List[str] = Field(default_factory=list, description="Dimensiones en DISCREPANCIA")


class ReporteDeriva(BaseModel):
    """[ARCH-1.4.12-B] Contrato REST del semáforo (cuatro luces + homologación [ARCH-1.4.12-C])."""
    regimen: str = "SOLO_LECTURA"
    evaluado_en_utc: str
    jornada_activa: Optional[int] = None
    liga_3nf: Optional[int] = None
    status_mercado: EstadoDimension
    status_deportivo: EstadoDimension
    status_progol: EstadoDimension
    status_integridad: EstadoDimension
    status_homologacion: EstadoDimension
    accion_recomendada: AccionRecomendada

def _canon_sonda() -> Dict[str, Any]:
    """
    [ARCH-1.4.34] Carga perezosa (una sola vez) del canon semafórico y de las seis sondas puras
    de coherencia de cartelera. El vocabulario y la aritmética se IMPORTAN de su plano
    legislativo: este controlador jamás los reimplementa.
    """
    global _CANON_SONDA
    if _CANON_SONDA is None:
        from src.core.coherence_auditor import (
            GLIFO_NIVEL,
            _agregar_nivel,
            _expediente_desde_fixture,
            auditar_coherencia_partido,
        )
        _CANON_SONDA = {
            "glifo": GLIFO_NIVEL,
            "agregar_nivel": _agregar_nivel,
            "expediente": _expediente_desde_fixture,
            "auditar": auditar_coherencia_partido,
        }
    return _CANON_SONDA


def _dimension(nivel: str, detalle: str, metrica: Optional[float] = None) -> EstadoDimension:
    """Materializa una luz del semáforo validando el nivel contra el canon [ARCH-1.4.34]."""
    glifos = _canon_sonda()["glifo"]
    if nivel not in glifos:
        raise ValueError(f"Nivel semafórico ajeno al canon [ARCH-1.4.34]: {nivel!r}")
    return EstadoDimension(nivel=nivel, glifo=glifos[nivel], detalle=detalle, metrica=metrica)


def _reloj_utc() -> datetime:
    """Sello UTC naive: autoridad temporal de las cuotas y de las fechas de cierre de concurso."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _reloj_local() -> datetime:
    """
    Reloj del soberano (naive local): paridad estricta con la ley de staleness [ARCH-1.6.2-B],
    que compara `fecha_dt` (hora local de la cartelera) contra `datetime.now()`.
    """
    return datetime.now()


def _marca_utc_naive(valor: Any) -> Optional[datetime]:
    """Normaliza un sello ISO-8601 de la bóveda a UTC naive; `None` si no es legible."""
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
    """Interpreta `fecha_dt` (hora local de la cartelera) sin inventar zona horaria."""
    if isinstance(valor, datetime):
        return valor.replace(tzinfo=None)
    if isinstance(valor, str) and valor.strip():
        try:
            return datetime.fromisoformat(valor.strip().replace("Z", "")).replace(tzinfo=None)
        except ValueError:
            return None
    return None


def _sello_cuotas_mas_reciente(fixtures: Sequence[Dict[str, Any]]) -> Optional[datetime]:
    """Sello de captura MÁS RECIENTE publicado por los operadores de la jornada auditada."""
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

def _status_mercado(fixtures: Sequence[Dict[str, Any]]) -> EstadoDimension:
    """[ARCH-1.4.12-B] Luz de mercado: frescura de las cuotas mientras la ventanilla esté abierta."""
    if not any(_fixture_operable_en_ventanilla(fx) for fx in fixtures):
        return _dimension(
            NIVEL_SIN_VEREDICTO,
            "Fuera de ventanilla de capital: no se exige frescura de cuotas sobre una jornada cerrada.",
        )
    sello = _sello_cuotas_mas_reciente(fixtures)
    if sello is None:
        return _dimension(
            NIVEL_SIN_VEREDICTO,
            "La bóveda no registra sello de captura de cuotas: frescura indeterminable (cero invención).",
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


def _status_deportivo(fixtures: Sequence[Dict[str, Any]]) -> EstadoDimension:
    """[ARCH-1.4.12-B / ARCH-1.6.2-B] Luz deportiva: partidos PROGRAMADO con inicio vencido."""
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


def _status_progol(session: Session) -> EstadoDimension:
    """[ARCH-1.4.12-B] Luz de quiniela: concursos abiertos cuya fecha de cierre ya expiró."""
    slates = session.query(Slate).order_by(Slate.created_at.desc()).all()
    abiertos = [s for s in slates if str(s.status or "").strip().upper() == "OPEN"]
    if not abiertos:
        return _dimension(
            NIVEL_SIN_VEREDICTO, "La bóveda no registra concurso de quiniela abierto."
        )
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
        return _dimension(
            NIVEL_SIN_VEREDICTO,
            f"Concurso(s) abierto(s) {etiquetas} sin fecha de cierre publicada por la fuente: "
            "cero fecha inventada.",
        )
    return _dimension(NIVEL_CONFORME, f"Cierre vigente: {min(vigentes).isoformat()} UTC.")

def _status_integridad(fixtures: Sequence[Dict[str, Any]]) -> EstadoDimension:
    """
    [ARCH-1.4.12-B / ARCH-1.4.34] Luz de integridad: veredicto agregado de las seis sondas puras
    sobre la cartelera persistida de la jornada activa (reutiliza el canon, no lo reimplementa).
    """
    if not fixtures:
        return _dimension(
            NIVEL_SIN_VEREDICTO,
            "Sin cartelera persistida en la jornada activa: nada que auditar (cero invención).",
        )
    canon = _canon_sonda()
    reportes = [canon["auditar"](canon["expediente"](fx)) for fx in fixtures]
    hallazgos = [h for reporte in reportes for h in reporte.hallazgos]
    nivel = canon["agregar_nivel"](hallazgos).value
    conteo = {
        nombre: sum(1 for r in reportes if r.nivel_global.value == nombre)
        for nombre in (NIVEL_DISCREPANCIA, NIVEL_ADVERTENCIA, NIVEL_CONFORME, NIVEL_SIN_VEREDICTO)
    }
    glifos = canon["glifo"]
    detalle = (
        f"{len(reportes)} partido(s) auditados"
        f" · {glifos[NIVEL_DISCREPANCIA]} {conteo[NIVEL_DISCREPANCIA]}"
        f" · {glifos[NIVEL_ADVERTENCIA]} {conteo[NIVEL_ADVERTENCIA]}"
        f" · {glifos[NIVEL_CONFORME]} {conteo[NIVEL_CONFORME]}"
        f" · {glifos[NIVEL_SIN_VEREDICTO]} {conteo[NIVEL_SIN_VEREDICTO]}"
    )
    return _dimension(nivel, detalle, float(conteo[NIVEL_DISCREPANCIA]))


def _status_homologacion(session: Session) -> Tuple[EstadoDimension, int]:
    """
    [ARCH-1.4.12-C] Luz de homologación factual: partidos CONCLUIDOS cuya traza soberana no publica
    `insumos_factivados` (traza legada de [ARCH-1.4.39] o distribución inexistente).

    Solo lectura: la sonda no repara nada; publica el rezago y su magnitud para que el Director
    despache `homologar_temporada_optah2h` desde el cockpit. Devuelve la luz y el conteo de pendientes
    (el conteo alimenta la recomendación sin re-consultar la bóveda).
    """
    filas = (
        session.query(Match.id, SovereignDistribution.audit_trace_json)
        .outerjoin(SovereignDistribution, SovereignDistribution.match_id == Match.id)
        .filter(Match.status.in_(ESTADOS_PARTIDO_CONCLUIDO))
        .all()
    )
    if not filas:
        return (
            _dimension(
                NIVEL_SIN_VEREDICTO,
                "La bóveda no registra partidos concluidos: homologación no exigible (cero invención).",
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
    dimensiones: Dict[str, EstadoDimension], homologacion_pendiente: int = 0
) -> AccionRecomendada:
    """
    [ARCH-1.4.12-B / ARCH-1.4.12-C] Traduce la deriva observada en UNA acción certificada:
      * Dos o más dimensiones de jornada en 🔴 ⇒ `cadena_pre_jornada` (reparación integral).
      * Una sola dimensión de jornada en 🔴 ⇒ su ejecutor individual.
      * Deriva exclusiva de quiniela ⇒ `cadena_progol`.
      * Rezago de homologación por encima del umbral (sin otra deriva) ⇒ `homologar_temporada_optah2h`.
      * Cero deriva ⇒ sin acción (`task_id = None`).
    """
    deriva = [
        dimension
        for dimension in ("deportivo", "mercado", "integridad", "progol")
        if dimensiones[dimension].nivel == NIVEL_DISCREPANCIA
    ]
    homologacion_exigible = homologacion_pendiente > UMBRAL_HOMOLOGACION_PENDIENTE
    if not deriva:
        if not homologacion_exigible:
            return AccionRecomendada(
                task_id=None,
                motivo="Cero deriva: las cuatro luces del semáforo están al día.",
                deriva=[],
            )
        from src.web.routes.admin_tasks import TAREAS_PERMITIDAS

        if TAREA_HOMOLOGACION_OPTA in TAREAS_PERMITIDAS:
            return AccionRecomendada(
                task_id=TAREA_HOMOLOGACION_OPTA,
                motivo=MOTIVO_HOMOLOGACION_PENDIENTE,
                deriva=["homologacion"],
            )
        return AccionRecomendada(
            task_id=None,
            motivo=f"Deriva sin ejecutor certificado en la whitelist: {MOTIVO_HOMOLOGACION_PENDIENTE}",
            deriva=["homologacion"],
        )
    deriva_jornada = [d for d in DIMENSIONES_JORNADA if d in deriva]
    if len(deriva_jornada) >= 2:
        tarea: Optional[str] = TAREA_CADENA_PRE_JORNADA
    elif deriva_jornada:
        tarea = DIMENSION_A_TAREA[deriva_jornada[0]]
    else:
        tarea = DIMENSION_A_TAREA["progol"]

    motivo = " · ".join(f"{d}: {dimensiones[d].detalle}" for d in deriva)
    if homologacion_exigible:
        motivo = f"{motivo} · {MOTIVO_HOMOLOGACION_PENDIENTE}"
    from src.web.routes.admin_tasks import TAREAS_PERMITIDAS
    if tarea not in TAREAS_PERMITIDAS:
        return AccionRecomendada(
            task_id=None,
            motivo=f"Deriva sin ejecutor certificado en la whitelist: {motivo}",
            deriva=deriva,
        )
    return AccionRecomendada(task_id=tarea, motivo=motivo, deriva=deriva)


def _liga_3nf(session: Session) -> Optional[League]:
    """Resuelve la fila 3NF de la Liga MX (paridad con la resolución de la Mesa de Apuestas)."""
    return (
        session.query(League)
        .filter((League.fotmob_id == FRONTERA_LIGA_MX_ID) | (League.id == FRONTERA_LIGA_MX_ID))
        .first()
    )


def _fixtures_jornada(
    session: Session, league_id: int, jornada: Optional[int]
) -> List[Dict[str, Any]]:
    """Cartelera persistida de la jornada activa (snapshot más reciente de ese `matchday`)."""
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


@router.get(
    "/drift",
    response_model=ReporteDeriva,
    summary="[ARCH-1.4.12-B] Semáforo de deriva y frescura de fuentes (solo lectura)",
)
def consultar_deriva_centro_control() -> ReporteDeriva:
    """Sonda read-only del Centro de Control: cuatro luces + homologación + acción recomendada."""
    gateway = PersistenceGateway()
    with gateway.read_session() as session:
        liga = _liga_3nf(session)
        jornada = resolver_jornada_actual_dinamica(session, liga.id) if liga else None
        fixtures = _fixtures_jornada(session, liga.id, jornada) if liga else []
        dimensiones = {
            "mercado": _status_mercado(fixtures),
            "deportivo": _status_deportivo(fixtures),
            "progol": _status_progol(session),
            "integridad": _status_integridad(fixtures),
        }
        status_homologacion, homologacion_pendiente = _status_homologacion(session)
        liga_id = liga.id if liga else None

    return ReporteDeriva(
        evaluado_en_utc=datetime.now(timezone.utc).isoformat(),
        jornada_activa=jornada,
        liga_3nf=liga_id,
        status_mercado=dimensiones["mercado"],
        status_deportivo=dimensiones["deportivo"],
        status_progol=dimensiones["progol"],
        status_integridad=dimensiones["integridad"],
        status_homologacion=status_homologacion,
        accion_recomendada=_accion_recomendada(dimensiones, homologacion_pendiente),
    )


def auditar_deriva_sistema() -> Dict[str, Any]:
    """
    [ARCH-1.4.12-C] Fachada programática del semáforo: publica el MISMO veredicto que el contrato
    REST `GET /api/admin/status/drift` como diccionario plano, sin abrir un segundo camino de
    lectura ni reimplementar sonda alguna ([GOVERNANCE-01]).
    """
    return consultar_deriva_centro_control().model_dump()
