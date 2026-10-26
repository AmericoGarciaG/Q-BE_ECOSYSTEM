# -*- coding: utf-8 -*-
"""
🏆 Q-BE REST CONTROLLER — ESTACIÓN DE MERCADOS FINANCIEROS Y ASIGNACIÓN
[ARCH-1.4.5 / DES-QBE-032] Rutas de Liquidación Financiera (Casino 1X2, Progol y Arbitraje).
[LN-QBE-073] Endpoint de despacho con Slider Dinámico de Certeza (Risk Dial).
[LN-QBE-074] Endpoint de optimización Progol por Presupuesto.
[LN-QBE-075 / VARIANCE-03 extirpada] El slate Progol se hidrata de la bóveda 3NF (`slates` / `slate_items`);
prohibida toda constante quemada de equipos, probabilidades o venta pública.
Base de Gobierno: Kybern Framework v12.0
"""

import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

from src.storage.gateway import PersistenceGateway
from src.storage.models import FixtureSnapshot, League, Match, SovereignDistribution, Slate, SlateItem
from src.core.constants import DELTA_EPIST_DEFAULT, PSI_DOWNSIDE_DEFAULT
from src.core.contracts.progol_math import (
    calcular_sesgo_quiniela,
    optimizar_quiniela_por_presupuesto,
    optimizar_quiniela_progol_soberana,
    seleccionar_cobertura_binaria_optima,
)

router = APIRouter(prefix="/api/markets", tags=["Financial Markets"])

# [LN-QBE-127] Registro de degradaciones DECLARADAS: una resolución al vuelo imposible se
# escribe aquí en vez de omitirse en silencio [GOVERNANCE-01].
logger = logging.getLogger(__name__)


# ── CARGA FÁCTICA DEL SLATE PROGOL DESDE LA BÓVEDA 3NF [ARCH-1.5.1-C] ────────
# [VARIANCE-03 extirpada] Eliminada la constante quemada SLATE_PROGOL_14_ITEMS: el tablero Progol
# se hidrata EXCLUSIVAMENTE de `slates` / `slate_items` a través de PersistenceGateway.
# [GOVERNANCE-01] Cero equipos, probabilidades, bolsas o marcadores sintéticos: si la bóveda no
# contiene un concurso OPEN, el endpoint declara la vaciedad y NO inventa casillas.

SLATE_PROGOL_14 = 14  # Casillas REGULAR publicadas por el concurso Progol (posiciones 1..14).


def _cargar_slate_progol(session: Session, slate_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    [LN-QBE-075 / LN-QBE-037] Hidrata el concurso Progol vigente desde la persistencia 3NF.
    Devuelve None si no existe concurso OPEN con casillas (prohibido fabricar un slate).
    La venta pública sólo se puebla si existe captura fáctica de momios de casino de esa jornada.
    """
    consulta = session.query(Slate).filter(Slate.status == "OPEN")
    slate = None
    if slate_id:
        slate = consulta.filter(Slate.id == slate_id).first()
    if slate is None:
        # [VARIANCE-03] `slate_id` ausente o inexistente => se degrada al concurso OPEN real.
        slate = consulta.order_by(Slate.created_at.desc()).first()
    if slate is None:
        return None

    items = (
        session.query(SlateItem)
        .filter(SlateItem.slate_id == slate.id)
        .order_by(SlateItem.position.asc())
        .all()
    )
    if not items:
        return None

    # ── Venta pública: SOLO si existe captura fáctica de momios de casino de esa jornada ──
    momios_publicos: Dict[str, Dict[str, float]] = {}
    if slate.matchday_num is not None:
        snapshot = (
            session.query(FixtureSnapshot)
            .filter(FixtureSnapshot.matchday == slate.matchday_num)
            .order_by(FixtureSnapshot.updated_at.desc())
            .first()
        )
        if snapshot and snapshot.matches_json:
            for fx in snapshot.matches_json:
                momios = fx.get("momios") or {}
                if momios.get("L") and momios.get("E") and momios.get("V"):
                    momios_publicos[fx.get("id_partido", "")] = {
                        "L": float(momios["L"]),
                        "E": float(momios["E"]),
                        "V": float(momios["V"]),
                    }

    items_out: List[Dict[str, Any]] = []
    for item in items:
        p_qbe = {"L": item.p_local, "E": item.p_empate, "V": item.p_visitante}
        momios = momios_publicos.get(item.match_id or "", {})
        if momios:
            # [ARCH-1.4.5] Misma convención del plano casino: probabilidad implícita = 1 / momio.
            v_pub = {clave: round(1.0 / valor, 4) for clave, valor in momios.items()}
            sesgo_disponible = True
            sesgo_motivo = "MOMIOS_DE_CASINO_DE_LA_JORNADA"
        else:
            v_pub = {}
            sesgo_disponible = False
            sesgo_motivo = "VENTA_PUBLICA_NO_INGESTADA_PARA_ESTE_PARTIDO"

        items_out.append({
            "order": item.position,
            "tipo_concurso": item.tipo_concurso,
            "local": item.local_canonico or item.local_raw,
            "visitante": item.visitante_canonico or item.visitante_raw,
            "local_raw": item.local_raw,
            "visitante_raw": item.visitante_raw,
            "match_id": item.match_id,
            "p_qbe": p_qbe,
            "v_pub": v_pub,
            "es_prior_ignorancia": bool(item.es_prior_ignorancia),
            "estado_qbe": "PRIOR-FIDUCIARIO-1/3" if item.es_prior_ignorancia else "SOBERANO-3NF",
            "sesgo_disponible": sesgo_disponible,
            "sesgo_motivo": sesgo_motivo,
            "analisis_sesgo": calcular_sesgo_quiniela(v_pub, p_qbe) if sesgo_disponible else None,
        })

    return {
        "slate_id": slate.id,
        "name": slate.name,
        "status": slate.status,
        "matchday_num": slate.matchday_num,
        "bolsa_estimada": slate.bolsa_estimada,
        "fecha_cierre": slate.fecha_cierre.isoformat() if getattr(slate, "fecha_cierre", None) else None,
        "sesgo_fuente": "MOMIOS_DE_CASINO" if momios_publicos else "NO_DISPONIBLE",
        "items": items_out,
    }


# ── [ARCH-1.4.15 / ARCH-1.5.10] VENTANILLA MULTI-OPERADOR ──────────────────────
# [GOVERNANCE-01] Cero hotlinking para emblemas de casino: las piezas viven en la
# bóveda local de activos (`/static/img/bookmakers/{slug}.png`, ancladas por
# `scripts/utilidades/sincronizar_boveda_activos.py`). El backend sólo declara
# disponibilidad fáctica de captura; jamás presta cuotas de una casa a otra.
_CASINOS_VENTANILLA: Tuple[str, ...] = ("caliente", "betway")


# ── ESQUEMAS PYDANTIC V2 ─────────────────────────────────────────────────────

class SportsbookPortfolioRequest(BaseModel):
    """[LN-QBE-073] Request del generador de cartera con Slider de Certeza."""
    league_id: int = Field(default=262)
    selected_match_ids: Optional[List[str]] = Field(default_factory=list)
    bankroll: float = Field(default=200.0, ge=10.0)
    target_certeza: float = Field(default=0.80, ge=0.0, le=1.0)
    operador: Optional[str] = Field(default="caliente")
    # [ARCH-1.4.30] Parámetro interactivo de concentración de masa Γ (Capa 0), tri-estado UI.
    gamma_slider: float = Field(default=0.67, ge=0.67, le=0.75)
    # [ARCH-1.4.37 / LN-QBE-077-B] Parámetro de Cobertura Dinámica δ (Dutching con Rendimiento):
    # `DEF` = indemnidad pura V=0 (contrato sellado) | `BAL` = 50% de δ* | `AGR` = δ*.
    # Cero aritmética en la capa web: el δ efectivo y su clamping los dicta la ley pura
    # `calcular_particion_dutching_dinamico()` invocada por `PortfolioEngine.build_plan()`.
    modo_cobertura: Optional[str] = Field(
        default="DEF", description="DEF (V=0), BAL (50% delta*), AGR (delta*)"
    )
    # [ARCH-1.4.35 / CONMUTADOR DE SLATES] Jornada explícita del Backtesting Fiduciario: cuando
    # viaja, la ventanilla se ANCLA al slate histórico de ESA jornada (se relaja la exigencia de
    # jornada activa/operable [ARCH-1.6.2]) y cada orden emitida se liquida contra el marcador
    # REAL de la bóveda 3NF (`matches`). Ausente ⇒ resolución dinámica intacta [ARCH-1.6.15].
    jornada: Optional[int] = Field(default=None, ge=1, le=38)


class ProgolOptimizeRequest(BaseModel):
    """
    [LN-QBE-074 / VARIANCE-03 extirpada] Request del optimizador Progol por presupuesto.
    `slate_id = None` => se resuelve el concurso OPEN vigente en la bóveda 3NF (cero ids sintéticos).
    """
    slate_id: Optional[str] = Field(default=None)
    presupuesto_mxn: float = Field(default=360.0, ge=15.0)


# ── [ARCH-1.6.15 / ARCH-1.6.2-B] RESOLUCIÓN DINÁMICA DE LA VENTANILLA DE CAPITAL ──
# [GOVERNANCE-01] Cero jornadas quemadas: la ventanilla emana del pool multiversal de
# snapshots capturados. Frontera de Despacho ([ARCH-1.6.2-B]): la selección MANUAL la
# gobierna el Live Board; el DESPACHO AUTOMÁTICO opera sobre las cuotas ya publicadas y
# no puede ser vetado por staleness sin declarar la jornada completa inoperable.


def _captura_de_cuotas(fx: Dict[str, Any]) -> bool:
    """
    [ARCH-1.4.15 / LN-QBE-076] ¿Porta el fixture alguna captura FÁCTICA 1X2 (L > 1.0)?
    Sólo se examinan capturas reales (canónica del snapshot + por operador): jamás se presta la
    cuota de una casa a otra [GOVERNANCE-01].
    """
    capturas: List[Dict[str, Any]] = [fx.get("momios") or {}]
    capturas.extend((fx.get("momios_operadores") or {}).values())
    for m_data in capturas:
        try:
            if float((m_data or {}).get("L", 0.0) or 0.0) > 1.0:
                return True
        except (TypeError, ValueError):
            continue
    return False


def _cuotas_del_operador(fx: Dict[str, Any], op_sel: str) -> Dict[str, Any]:
    """
    [ARCH-1.4.15 / LN-QBE-076] Resuelve las cuotas 1X2 del operador solicitado sobre la captura
    congelada del fixture:
      - `mejor_combinacion`: la casa que paga el mejor momio del local entre las capturas
        FÁCTICAS (L > 1.0); sin capturas se degrada a la captura canónica del snapshot.
      - Operador certificado: su PROPIA captura (`momios_operadores[op]`), con respaldo en la
        captura canónica. Una casa sin cuotas devuelve `{}`: cero cuotas inventadas.
    """
    m_ops = fx.get("momios_operadores") or {}
    if op_sel == "mejor_combinacion":
        candidatas = [
            (vals or {}) for vals in m_ops.values()
            if float((vals or {}).get("L", 0.0) or 0.0) > 1.0
        ]
        if candidatas:
            return max(candidatas, key=lambda v: float(v.get("L", 0.0)))
        return fx.get("momios") or {}
    return m_ops.get(op_sel) or fx.get("momios") or {}


def _captura_canonica_1x2(fx: Dict[str, Any]) -> Dict[str, Any]:
    """
    [ARCH-1.4.15 / LN-QBE-076 · Dictamen V-6] Captura CANÓNICA del snapshot: el trío 1X2 factual
    (`L`, `E`, `V` > 1.0) sellado en `momios`, más su bandera de Pago Anticipado declarada.

    Cero reparación de cuotas: un trío incompleto devuelve `{}`. La procedencia la declara el propio
    fixture (`operador`); esta función NUNCA la atribuye a una casa que no la publicó
    ([GOVERNANCE-01]).
    """
    momios = fx.get("momios") or {}
    try:
        if not all(float(momios.get(k, 0.0) or 0.0) > 1.0 for k in ("L", "E", "V")):
            return {}
        return {
            "L": float(momios.get("L", 0.0) or 0.0),
            "E": float(momios.get("E", 0.0) or 0.0),
            "V": float(momios.get("V", 0.0) or 0.0),
            "pa": bool(momios.get("pa", False) or momios.get("pago_anticipado", False)),
        }
    except (TypeError, ValueError):
        return {}


def _fixture_operable_en_ventanilla(fx: Dict[str, Any]) -> bool:
    """
    [ARCH-1.6.2] Un fixture es operable en la ventanilla de capital si NO está concluido y
    porta captura fáctica de cuotas 1X2 (L > 1.0). Cero cuotas inventadas [GOVERNANCE-01].
    """
    if str(fx.get("estado", "")) == "FINALIZADO":
        return False

    capturas: List[Dict[str, Any]] = [fx.get("momios") or {}]
    capturas.extend((fx.get("momios_operadores") or {}).values())

    for m_data in capturas:
        try:
            if float((m_data or {}).get("L", 0.0) or 0.0) > 1.0:
                return True
        except (TypeError, ValueError):
            continue

    return False


def _resolver_snapshot_ventanilla(
    session: Session,
    league_id: int,
    selected_ids: Optional[List[str]] = None,
    jornada: Optional[int] = None
) -> Optional[FixtureSnapshot]:
    """
    [ARCH-1.6.15 / ARCH-1.4.10] Resuelve el snapshot de la jornada activa de la ventanilla
    sin constantes quemadas:
      0. Carril BACKTESTING (`jornada` explícita, [ARCH-1.4.35]): anclaje EXACTO al slate de esa
         jornada, aunque esté concluida. Cero exigencia de `is_active`/operabilidad: el histórico
         congelado se re-expone tal cual fue capturado (cero cuotas inventadas [GOVERNANCE-01]).
      1. Carril MANUAL (`selected_ids` con contenido): el snapshot más reciente que contenga
         alguno de los partidos solicitados (la selección la gobierna el Live Board).
      2. Carril AUTOMÁTICO: el snapshot más reciente que porte al menos un partido operable
         (no concluido con cuotas publicadas); si la jornada vigente concluyó en su
         totalidad, conmuta a la última jornada operable registrada en la bóveda.
    """
    if jornada is not None:
        # [ARCH-1.4.35 / CONMUTADOR DE SLATES] El anclaje por jornada MANDA sobre cualquier
        # heurística de vigencia: es la ordenanza expresa del Director (doble seguro del candado).
        return (
            session.query(FixtureSnapshot)
            .filter(
                FixtureSnapshot.league_id == league_id,
                FixtureSnapshot.matchday == int(jornada)
            )
            .order_by(FixtureSnapshot.updated_at.desc())
            .first()
        )

    snapshots = session.query(FixtureSnapshot).filter(
        FixtureSnapshot.league_id == league_id
    ).order_by(FixtureSnapshot.updated_at.desc()).all()

    if not snapshots:
        return None

    if selected_ids:
        for snap in snapshots:
            for fx in (snap.matches_json or []):
                if fx.get("id_partido", "") in selected_ids:
                    return snap
        return snapshots[0]

    for snap in snapshots:
        if any(_fixture_operable_en_ventanilla(fx) for fx in (snap.matches_json or [])):
            return snap

    return snapshots[0]


# ── [ARCH-1.4.35 / LN-QBE-025-B] LIQUIDACIÓN REAL DEL BACKTESTING (Real vs. Predicho) ──
# [GOVERNANCE-01] Cero marcadores sintéticos: el oráculo es la bóveda 3NF (`matches`), única
# autoridad de resultados reales. La aritmética de liquidación NO vive aquí: se delega VERBATIM
# a la ley sellada `liquidar_orden_post_evento` de `src.core.contracts.portfolio_math`
# ([DIRGEN-STRICT] — este controlador sólo TRANSPORTA el contrato plano de piernas).


def _reales_3nf_por_jornada(session: Session) -> Dict[int, Dict[str, Tuple[int, int]]]:
    """
    [ARCH-1.4.35] Foto completa de resultados REALES de la bóveda 3NF (`matches`), agrupada por
    jornada: `{jornada: {id_partido: (goles_local, goles_visitante)}}`. Una sola consulta
    alimenta la cartelera congelada, el resumen de jornadas del conmutador y la liquidación.
    Sólo entran marcadores concluidos (ambos goles capturados): cero resultados inventados.
    """
    agrupado: Dict[int, Dict[str, Tuple[int, int]]] = {}
    for fila in session.query(Match).all():
        if fila.matchday_num is None or fila.score_home is None or fila.score_away is None:
            continue
        agrupado.setdefault(int(fila.matchday_num), {})[str(fila.id)] = (
            int(fila.score_home), int(fila.score_away)
        )
    return agrupado


def _marcadores_reales_3nf(session: Session, jornada: int) -> Dict[str, Tuple[int, int]]:
    """
    [ARCH-1.4.35] Marcadores REALES publicados en la 3NF para una jornada (`matches`).
    Devuelve `{id_partido: (goles_local, goles_visitante)}` con sólo resultados concluidos:
    un partido sin marcador capturado simplemente NO se liquida (cero invención).
    """
    return _reales_3nf_por_jornada(session).get(int(jornada), {})


def _piernas_liquidables(
    orden: Dict[str, Any],
    fixture: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    [VAULT-CORE-006 / INVARIANTE VIII-11] Traduce una orden emitida a su contrato PLANO de
    liquidación, sin re-calcular capital alguno (los montos y momios vienen certificados por el
    motor). Contrato de piernas: `boleto_2_ganancia` es SIEMPRE la pierna Ataque ("Gana {equipo}")
    y `boleto_1_seguro` la cobertura ("Empate", o "Empate (Sin Cobertura)" con monto 0.00 en las
    familias directas D1/D2). La identidad de la pierna Ataque se resuelve por el NOMBRE del
    equipo que la selección transporta (el mismo literal que el motor recibió del snapshot), con
    respaldo en el favorito soberano del fixture. Devuelve None si el contrato es ininteligible:
    en ese caso NO se liquida (cero liquidaciones inventadas [GOVERNANCE-01]).
    """
    boletos = orden.get("boletos") or {}
    b1 = boletos.get("boleto_1_seguro") or {}
    b2 = boletos.get("boleto_2_ganancia") or {}
    # Guarda de orden invertido: sólo se permuta si el `boleto_1_seguro` porta la pierna Ataque.
    ataque, cobertura = (b1, b2) if str(b1.get("seleccion", "")).strip().upper().startswith("GANA") else (b2, b1)
    if not ataque:
        return None

    seleccion = str(ataque.get("seleccion", "")).upper()
    local = str((fixture or {}).get("local", "")).upper()
    visitante = str((fixture or {}).get("visitante", "")).upper()
    if local and local in seleccion:
        lado_respaldado = "LOCAL"
    elif visitante and visitante in seleccion:
        lado_respaldado = "VISITA"
    else:
        p_local = float((fixture or {}).get("p_local", 0.0) or 0.0)
        p_visitante = float((fixture or {}).get("p_visitante", 0.0) or 0.0)
        lado_respaldado = "LOCAL" if p_local >= p_visitante else "VISITA"

    return {
        "inversion_total": float(boletos.get("inversion_partido_A_i", 0.0) or 0.0),
        "monto_ataque": float(ataque.get("monto_mxn", 0.0) or 0.0),
        "cuota_ataque": float(ataque.get("momio", 0.0) or 0.0),
        "monto_seguro": float((cobertura or {}).get("monto_mxn", 0.0) or 0.0),
        "cuota_seguro": float((cobertura or {}).get("momio", 0.0) or 0.0),
        "seleccion_favorito": lado_respaldado,
        # [ARCH-1.4.37 / LN-QBE-077-B] Cobertura Dinámica: el δ CERTIFICADO por el motor viaja
        # verbatim a la ley de liquidación (el bloque `cobertura_dinamica` sólo existe en las
        # familias con seguro de empate; su ausencia ⇒ δ = 0.0000 y veredicto sellado `TABLAS_V0`).
        # Cero re-derivación: la capa web no recalcula coberturas, sólo transporta el contrato.
        "delta_cobertura": float(
            ((orden.get("cobertura_dinamica") or {}) or {}).get("delta_cobertura", 0.0) or 0.0
        ),
    }


def _adjuntar_liquidacion_real(
    data: Dict[str, Any],
    session: Session,
    jornada: int,
    fixtures_por_id: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """
    [ARCH-1.4.35 / LN-QBE-025-B] Adjunta a cada orden emitida su `liquidacion_real` (marcador
    final real + PnL neto bancario) y publica el bloque agregado `backtesting` del payload.
    El contrato emitido NO se altera: la liquidación es evidencia AÑADIDA (montos, momios y
    estrategias quedan intactos). Las órdenes sin marcador real en la bóveda o con contrato
    ininteligible NO se liquidan: el agregado declara el denominador completo (`ordenes_sin_
    marcador_real`), cero marcadores o PnL inventados ([GOVERNANCE-01]).
    """
    from src.core.contracts.portfolio_math import liquidar_orden_post_evento

    marcadores = _marcadores_reales_3nf(session, jornada)
    ordenes: List[Dict[str, Any]] = data.get("ordenes_ejecucion_partidos") or []

    liquidados = 0
    cobrados = 0
    tablas = 0
    fallos = 0
    cosechas_delta = 0
    inversion_liquidada = 0.0
    pnl_total = 0.0

    for orden in ordenes:
        mid = str(orden.get("id_partido", ""))
        marcador = marcadores.get(mid)
        if marcador is None:
            continue
        piernas = _piernas_liquidables(orden, fixtures_por_id.get(mid, {}))
        if piernas is None:
            continue

        # [DIRGEN-STRICT] Aritmética sellada: la ley del backtesting dicta el veredicto.
        resultado = liquidar_orden_post_evento(piernas, marcador[0], marcador[1])
        resultado["marcador_final"] = f"{marcador[0]} - {marcador[1]}"
        resultado["lado_respaldado"] = piernas["seleccion_favorito"]
        resultado["jornada"] = int(jornada)
        # [GOVERNANCE-01] Trazabilidad: el desenlace exhibido es el marcador REAL de la bóveda.
        resultado["fuente_marcador"] = "3NF `matches` (resultado real)"
        orden["liquidacion_real"] = resultado

        liquidados += 1
        inversion_liquidada += float(resultado.get("inversion_mxn", 0.0) or 0.0)
        pnl_total += float(resultado.get("pnl_neto_mxn", 0.0) or 0.0)
        estado = resultado.get("estado")
        if estado == "COBRADO_ATAQUE":
            cobrados += 1
        elif estado == "COBRADO_SEGURO_DELTA":
            # [ARCH-1.4.37] COSECHA ACTIVA: el empate cubierto con δ > 0 devenga PnL positivo.
            # Se contabiliza como COBRO (jamás como fallo): cero tergiversación del agregado.
            cosechas_delta += 1
        elif estado == "TABLAS_V0":
            tablas += 1
        else:
            fallos += 1

    data["backtesting"] = {
        "activo": True,
        "jornada": int(jornada),
        "total_ordenes": len(ordenes),
        "ordenes_liquidadas": liquidados,
        "ordenes_sin_marcador_real": len(ordenes) - liquidados,
        "cobrados": cobrados,
        "tablas_v0": tablas,
        "cosechas_seguro_delta": cosechas_delta,
        "fallos": fallos,
        "inversion_liquidada_mxn": round(inversion_liquidada, 2),
        "pnl_neto_total_mxn": round(pnl_total, 2),
        "marcadores_reales": {mid: f"{h} - {a}" for mid, (h, a) in sorted(marcadores.items())},
    }
    return data


# ── ENDPOINTS ────────────────────────────────────────────────────────────────

@router.get("/sportsbook/matches")
def get_sportsbook_matches(
    bookmaker: str = Query("caliente", description="Operador de casino (ej. caliente)"),
    league_id: int = Query(262, description="ID de la liga")
) -> Dict[str, Any]:
    """
    [DES-QBE-032 / ARCH-1.4.5] Retorna los partidos abiertos con cuotas en ventanilla,
    contrastados contra la probabilidad soberana para exponer el GAP (+EV).
    """
    gateway = PersistenceGateway()

    with gateway.read_session() as session:
        league = session.query(League).filter((League.fotmob_id == league_id) | (League.id == league_id)).first()
        if not league:
            raise HTTPException(status_code=404, detail="Liga no encontrada.")

        # [ARCH-1.6.15 / ARCH-1.6.2-B] Ventanilla dinámica: partidos ABERTOS con cuotas
        # publicadas por el casino. Cero jornada quemada.
        fix_snap = _resolver_snapshot_ventanilla(session, league.id)

        if not fix_snap or not fix_snap.matches_json:
            return {"bookmaker": bookmaker, "league_id": league_id, "matches": []}

        matches_out = []
        for fx in fix_snap.matches_json:
            momios = fx.get("momios")
            if not momios or not momios.get("L"):
                continue

            mid = fx.get("id_partido", "")
            momio_l = float(momios.get("L", 0.0))
            momio_e = float(momios.get("E", 0.0))
            momio_v = float(momios.get("V", 0.0))
            pa = bool(momios.get("pago_anticipado", True))

            dist_db = session.query(SovereignDistribution).filter(SovereignDistribution.match_id == mid).first()
            # [LN-QBE-007-J] Prior fiduciario soberano sellado (Ω Resumen: 0.45 / 0.28 / 0.27).
            # Saneamiento O-11: erradicadas las semillas huérfanas 0.564 / 0.258 / 0.178.
            p_l = dist_db.p_local if dist_db else 0.4500
            p_e = dist_db.p_empate if dist_db else 0.2800
            p_v = dist_db.p_visitante if dist_db else 0.2700

            prob_impl_l = 1.0 / momio_l if momio_l > 0 else 0.0
            prob_impl_e = 1.0 / momio_e if momio_e > 0 else 0.0
            prob_impl_v = 1.0 / momio_v if momio_v > 0 else 0.0

            gap_l = round(p_l - prob_impl_l, 4)
            gap_e = round(p_e - prob_impl_e, 4)
            gap_v = round(p_v - prob_impl_v, 4)

            es_viable = (gap_l > 0.0 or gap_e > 0.0 or gap_v > 0.0)

            matches_out.append({
                "match_id": mid,
                "local": fx.get("local", ""),
                "visitante": fx.get("visitante", ""),
                "local_escudo_url": fx.get("local_escudo_url", ""),
                "visitante_escudo_url": fx.get("visitante_escudo_url", ""),
                "horario": fx.get("horario", ""),
                "p_local": p_l,
                "p_empate": p_e,
                "p_visitante": p_v,
                "momio_l": momio_l,
                "momio_e": momio_e,
                "momio_v": momio_v,
                "pago_anticipado": pa,
                "gap_local": gap_l,
                "gap_empate": gap_e,
                "gap_visitante": gap_v,
                "es_viable_ev": es_viable
            })

        return {
            "bookmaker": bookmaker,
            "league_id": league_id,
            "total_abiertos": len(matches_out),
            "matches": matches_out
        }


@router.get("/sportsbook/live-board")
def get_sportsbook_live_board(
    bookmaker: str = Query("caliente", description="Operador de casino (ej. caliente) o mejor_combinacion"),
    league_id: int = Query(262, description="ID de la liga (fotmob_id o id 3NF)"),
    jornada: Optional[int] = Query(default=None, description="Jornada del slate (histórica o activa)")
) -> Dict[str, Any]:
    """
    [ARCH-1.4.35 / CONMUTADOR DE SLATES] Cartelera 1X2 de UNA jornada con su captura fáctica de
    cuotas y su soberanía certificada. Es la cartelera que consume el conmutador del Director:

      - `jornada` AUSENTE ⇒ jornada ACTIVA dinámica [ARCH-1.6.15] (idéntica resolución que la
        ventanilla de capital).
      - `jornada` PRESENTE ⇒ slate ANCLADO de esa jornada, aunque esté CONCLUIDA: el histórico
        congelado se re-expone como cartelera del backtesting.

    [GOVERNANCE-01] Cero cuotas, marcadores o fechas inventadas: el partido sin captura viaja con
    `con_cuotas: false` y momios `null`; el marcador real emana EXCLUSIVAMENTE de la bóveda 3NF
    (`matches`). Jamás se presta la cuota de una casa a otra.
    """
    gateway = PersistenceGateway()
    op_sel = (bookmaker or "caliente").lower()

    with gateway.read_session() as session:
        league = session.query(League).filter((League.fotmob_id == league_id) | (League.id == league_id)).first()
        if not league:
            raise HTTPException(status_code=404, detail="Liga no encontrada.")

        jornada_solicitada = int(jornada) if isinstance(jornada, int) else None
        fix_snap = _resolver_snapshot_ventanilla(session, league.id, None, jornada_solicitada)

        reales_por_jornada = _reales_3nf_por_jornada(session)
        snap_activa = _resolver_snapshot_ventanilla(session, league.id)
        jornada_activa = int(snap_activa.matchday) if (snap_activa and snap_activa.matchday is not None) else None

        # [ARCH-1.4.15] Resumen fáctico de la bóveda: qué jornadas existen y qué porta cada una,
        # en UNA sola lectura (hidrata el conmutador sin multiplicar peticiones).
        resumen_jornadas: List[Dict[str, Any]] = []
        for snap in (
            session.query(FixtureSnapshot)
            .filter(FixtureSnapshot.league_id == league.id)
            .order_by(FixtureSnapshot.matchday.asc())
            .all()
        ):
            fixtures_snap = [fx for fx in (snap.matches_json or []) if isinstance(fx, dict)]
            num_jornada = int(snap.matchday) if snap.matchday is not None else None
            resumen_jornadas.append({
                "jornada": num_jornada,
                "total_partidos": len(fixtures_snap),
                "con_cuotas": sum(1 for fx in fixtures_snap if _captura_de_cuotas(fx)),
                "concluida": bool(fixtures_snap) and all(
                    str(fx.get("estado", "")) == "FINALIZADO" for fx in fixtures_snap),
                "con_marcador_real": len(reales_por_jornada.get(num_jornada, {})) if num_jornada else 0,
            })

        if not fix_snap or not fix_snap.matches_json:
            # Vaciedad declarada: cero carteleras sintéticas ([GOVERNANCE-01]).
            return {
                "bookmaker": op_sel,
                "league_id": league_id,
                "jornada": jornada_solicitada,
                "jornada_activa": jornada_activa,
                "es_backtesting": jornada_solicitada is not None,
                "motivo": "La bóveda no contiene captura de cartelera para la jornada solicitada.",
                "jornadas": resumen_jornadas,
                "operadores_disponibles": {},
                "total_partidos": 0,
                "partidos": []
            }

        num_jornada_snap = int(fix_snap.matchday) if fix_snap.matchday is not None else None
        marcadores_jornada = reales_por_jornada.get(num_jornada_snap, {}) if num_jornada_snap else {}

        partidos_out: List[Dict[str, Any]] = []
        operadores_disponibles: Dict[str, Dict[str, Any]] = {}

        for fx in fix_snap.matches_json:
            if not isinstance(fx, dict):
                continue
            mid = str(fx.get("id_partido", ""))

            # [ARCH-1.4.15] Disponibilidad fáctica por casa de ESTA jornada (las certificadas se
            # declaran siempre: `disponible: false` es un estado legítimo y explícito).
            for op_disp, vals_disp in (fx.get("momios_operadores") or {}).items():
                reg = operadores_disponibles.setdefault(op_disp, {"disponible": False, "capturas_validas": 0})
                try:
                    if float((vals_disp or {}).get("L", 0.0) or 0.0) > 1.0:
                        reg["capturas_validas"] += 1
                        reg["disponible"] = True
                except (TypeError, ValueError):
                    continue

            cuotas = _cuotas_del_operador(fx, op_sel)
            momio_l = float((cuotas or {}).get("L", 0.0) or 0.0)
            momio_e = float((cuotas or {}).get("E", 0.0) or 0.0)
            momio_v = float((cuotas or {}).get("V", 0.0) or 0.0)
            con_cuotas = momio_l > 1.0

            dist_db = session.query(SovereignDistribution).filter(SovereignDistribution.match_id == mid).first()
            p_local = fx.get("p_local") if fx.get("p_local") is not None else (dist_db.p_local if dist_db else None)
            p_empate = fx.get("p_empate") if fx.get("p_empate") is not None else (dist_db.p_empate if dist_db else None)
            p_visitante = fx.get("p_visitante") if fx.get("p_visitante") is not None else (dist_db.p_visitante if dist_db else None)
            sin_soberania = p_local is None or p_empate is None or p_visitante is None

            gap_l = gap_e = gap_v = None
            if con_cuotas and not sin_soberania:
                gap_l = round(float(p_local) - (1.0 / momio_l), 4)
                gap_e = round(float(p_empate) - (1.0 / momio_e), 4) if momio_e > 0 else None
                gap_v = round(float(p_visitante) - (1.0 / momio_v), 4) if momio_v > 0 else None

            marcador = marcadores_jornada.get(mid)
            partidos_out.append({
                "match_id": mid,
                "local": fx.get("local", ""),
                "visitante": fx.get("visitante", ""),
                "local_escudo_url": fx.get("local_escudo_url", ""),
                "visitante_escudo_url": fx.get("visitante_escudo_url", ""),
                "horario": fx.get("horario", ""),
                "fecha_dt": fx.get("fecha_dt"),
                "estado": fx.get("estado"),
                "concluido": str(fx.get("estado", "")) == "FINALIZADO",
                "seleccionable": (str(fx.get("estado", "")) != "FINALIZADO" and con_cuotas),
                "con_cuotas": con_cuotas,
                "sin_soberania": sin_soberania,
                "momio_l": momio_l if con_cuotas else None,
                "momio_e": momio_e if con_cuotas else None,
                "momio_v": momio_v if con_cuotas else None,
                "pago_anticipado": bool((cuotas or {}).get("pago_anticipado", False)) if con_cuotas else None,
                "p_local": float(p_local) if p_local is not None else None,
                "p_empate": float(p_empate) if p_empate is not None else None,
                "p_visitante": float(p_visitante) if p_visitante is not None else None,
                "gap_local": gap_l,
                "gap_empate": gap_e,
                "gap_visitante": gap_v,
                "es_viable_ev": bool(
                    gap_l is not None and (gap_l > 0.0 or (gap_e or 0.0) > 0.0 or (gap_v or 0.0) > 0.0)),
                "marcador_real": f"{marcador[0]} - {marcador[1]}" if marcador else None,
                "marcador_capturado": fx.get("marcador_actual"),
                "liquidable": marcador is not None,
            })

        for slug_certificado in _CASINOS_VENTANILLA:
            operadores_disponibles.setdefault(slug_certificado, {"disponible": False, "capturas_validas": 0})
        operadores_disponibles["mejor_combinacion"] = {
            "disponible": any(v["disponible"] for v in operadores_disponibles.values()),
            "capturas_validas": sum(v["capturas_validas"] for v in operadores_disponibles.values()),
        }

        return {
            "bookmaker": op_sel,
            "league_id": league_id,
            "jornada": num_jornada_snap,
            "jornada_activa": jornada_activa,
            "es_backtesting": jornada_solicitada is not None,
            "jornadas": resumen_jornadas,
            "operadores_disponibles": operadores_disponibles,
            "total_partidos": len(partidos_out),
            "partidos": partidos_out
        }


def _descartar_partido(
    descartes: List[Dict[str, Any]],
    partido_id: str,
    local: str,
    visitante: str,
    motivo: str,
    motivo_codigo: str,
    codigo_estrategia: str,
    explicacion_didactica: str,
    metricas_cifras: Optional[Dict[str, Any]] = None
) -> None:
    """
    [ARCH-1.4.8 §3 / LN-QBE-005 / LN-QBE-065 / LN-QBE-078] Registro canonico del Radar de Descartes.
    Todo activo vetado se clasifica QBE-00 con inversion de $0.00 MXN, motivo fiduciario y,
    cuando existen, el desglose cuantitativo transparente del veto (metricas_cifras).
    """
    item: Dict[str, Any] = {
        "id_partido": partido_id,
        "partido": f"{local} vs {visitante}",
        "motivo": motivo,
        "motivo_codigo": motivo_codigo,
        "codigo_estrategia": codigo_estrategia,
        "explicacion_didactica": explicacion_didactica,
        "inversion_mxn": 0.0,
        "metricas": metricas_cifras or {}
    }
    descartes.append(item)


def _orden_a_contrato_slider(
    orden: Dict[str, Any],
    candidato: Dict[str, Any]
) -> Dict[str, Any]:
    """
    [LN-QBE-073 / VAULT-CORE-006] Puente canonico Pydantic -> Contrato PLANO del Slider de Certeza.
    Reproduce EXACTAMENTE la regla que `PortfolioEngine.build_plan` aplica a su Trinidad 3^K
    [LN-QBE-072]: p_win <- prob_fav, p_draw <- prob_emp, p_loss <- prob_und (probabilidades
    soberanas ya certificadas por el triaje de 9 estrategias) y es_directo <- familia D.
    [GOVERNANCE-01] No se inventa ninguna magnitud: solo se TRANSPORTA capital y probabilidad
    ya calculados por el motor. Los defaults 70/20/10 son los MISMOS que usa `build_plan`
    (`portfolio.py` L556-558), por lo que el puente no introduce numeros nuevos.
    """
    boletos = orden.get("boletos") or {}
    proyecciones = orden.get("proyecciones") or {}
    codigo = str((orden.get("estrategia_seleccionada") or {}).get("codigo", "")).replace("+", "").strip()

    return {
        "id": orden.get("id_partido", ""),
        "ganancia": float(proyecciones.get("ganancia_neta_principal_mxn", 0.0) or 0.0),
        "inversion": float(boletos.get("inversion_partido_A_i", 0.0) or 0.0),
        "p_win": float(candidato.get("prob_fav", 70.0)) / 100.0,
        "p_draw": float(candidato.get("prob_emp", 20.0)) / 100.0,
        "p_loss": float(candidato.get("prob_und", 10.0)) / 100.0,
        "es_directo": codigo in ("QBE-D1", "QBE-D2"),
        "estrategia_codigo": codigo
    }


@router.post("/sportsbook/portfolio/generate")
def generate_sportsbook_portfolio_endpoint(
    req: SportsbookPortfolioRequest
) -> Dict[str, Any]:
    """
    [ARCH-1.4.10] Despacho Financiero 3NF Desacoplado.
    Consulta directamente FixtureSnapshot y SovereignDistribution, ejecuta el triaje
    y despacha la cartera en tiempo record sin dependencias del motor monolitico legacy.
    """
    from src.storage.gateway import PersistenceGateway
    from src.core.contracts.portfolio_math import (
        triaje_determinista_9_estrategias,
        calcular_ranking_friccion,
        aplicar_hard_caps_constitucionales,
        resolver_mejor_combinacion_cuotas,
        PortfolioParameters,
    )
    from src.core.portfolio import PortfolioEngine
    from src.core.risk_dial_modulator import modular_cartera_por_slider_certeza

    # NOTA CANONICA: `aplicar_hard_caps_constitucionales` es la utilidad de verificacion
    # constitucional (8.0% individual / 25.0% de jornada); la acotacion efectiva vive DENTRO de
    # `PortfolioEngine.build_plan` ([LN-QBE-070-B]). Esta ruta es 100% read-only y no reescala
    # capital post-despacho (cero mutacion de magnitudes certificadas).

    gateway = PersistenceGateway()

    # [ARCH-1.4.30] Contrato gobernante del dimensionamiento de cartera: el bankroll, el Slider
    # de Certeza y el parámetro interactivo de masa Γ (Capa 0) viajan por el DTO canónico
    # `PortfolioParameters`. Cero aritmética nueva: el DTO solo transporta magnitudes certificadas.
    parametros_cartera = PortfolioParameters(
        total_bankroll=req.bankroll,
        certainty_slider=req.target_certeza,
        gamma_threshold=req.gamma_slider,
    )

    with gateway.read_session() as session:
        league = session.query(League).filter((League.fotmob_id == req.league_id) | (League.id == req.league_id)).first()
        if not league:
            raise HTTPException(status_code=404, detail="Liga no encontrada en SQLite.")

        # [ARCH-1.4.35 / CONMUTADOR DE SLATES] Jornada ANCLADA del Backtesting Fiduciario: cuando
        # viaja (`req.jornada`), la ventanilla se congela en el slate histórico de esa jornada
        # —se relaja la exigencia de jornada activa/operable [ARCH-1.6.2] y el veto por partido
        # FINALIZADO, porque el backtesting EXISTE para cuantificar contra resultados ya
        # concluidos— y cada orden emitida se liquida contra el marcador REAL de la bóveda 3NF
        # (`matches`, [LN-QBE-025-B]). Ausente ⇒ resolución dinámica intacta [ARCH-1.6.15].
        jornada_anclada = int(req.jornada) if req.jornada is not None else None
        en_backtesting = jornada_anclada is not None

        # [ARCH-1.6.15 / ARCH-1.6.2-B] Frontera de Despacho: carril manual (Live Board) vs.
        # despacho automático de jornada (pool multiversal de snapshots capturados).
        fix_snap = _resolver_snapshot_ventanilla(session, league.id, req.selected_match_ids, jornada_anclada)

        if not fix_snap or not fix_snap.matches_json:
            if en_backtesting:
                # [ARCH-1.4.35] Vaciedad declarada del slate anclado: la bóveda no capturó esa
                # jornada. Cero carteleras sintéticas, cero marcadores inventados.
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"La bóveda 3NF no contiene captura de cartelera para la "
                        f"Jornada {jornada_anclada}."
                    ),
                )
            raise HTTPException(status_code=400, detail="No hay partidos registrados para la jornada activa.")

        partidos_candidatos = []
        descartes: List[Dict[str, Any]] = []
        op_sel = (req.operador or "caliente").lower()

        # [ARCH-1.4.14] Denominador fáctico de cartelera: TODOS los partidos que componen la
        # fecha en el snapshot de origen (no los que sobreviven el triaje). Cero heurística:
        # el conteo emana de la longitud del payload capturado (ej. 9 en Liga MX).
        total_jornada = len(fix_snap.matches_json or [])

        # [ARCH-1.4.35] Índice del slate por `id_partido`: hidrata la traducción de cada orden
        # emitida a su contrato PLANO de piernas ([VAULT-CORE-006]) durante la liquidación real.
        fixtures_por_id: Dict[str, Dict[str, Any]] = {
            str(fx.get("id_partido", "")): fx
            for fx in (fix_snap.matches_json or [])
            if isinstance(fx, dict)
        }

        # [ARCH-1.4.15] Contrato de Disponibilidad Dinámica de Operadores: se reporta la captura
        # FÁCTICA por casa en la jornada activa. Una casa sin cuotas válidas viaja `disponible: false`.
        operadores_capturados: Dict[str, Dict[str, Any]] = {}
        for fx_disp in (fix_snap.matches_json or []):
            for op_disp, vals_disp in (fx_disp.get("momios_operadores") or {}).items():
                reg = operadores_capturados.setdefault(op_disp, {"disponible": False, "capturas_validas": 0})
                try:
                    if float((vals_disp or {}).get("L", 0.0) or 0.0) > 1.0:
                        reg["capturas_validas"] += 1
                        reg["disponible"] = True
                except (TypeError, ValueError):
                    continue
        # [ARCH-1.4.15] Las casas certificadas de la ventanilla se declaran SIEMPRE, incluso si la
        # jornada no las capturó: `disponible: false` es un estado legítimo y explícito.
        for slug_certificado in _CASINOS_VENTANILLA:
            operadores_capturados.setdefault(
                slug_certificado, {"disponible": False, "capturas_validas": 0})
        # [ARCH-1.4.15 / LN-QBE-076 · Dictamen V-6] Captura MONO-FUENTE declarada: en un fixture sin
        # capturas multi-casa, la cuota canónica del snapshot se reporta con el NOMBRE DE SU FUENTE
        # (`fx["operador"]`) y jamás se presta a una casa local ([GOVERNANCE-01]). Es lo que habilita
        # el carril por defecto (Mejor Combinación) sobre jornadas de captura histórica.
        for fx_disp in (fix_snap.matches_json or []):
            if not _captura_canonica_1x2(fx_disp):
                continue
            capturas_casa = [
                vals for vals in (fx_disp.get("momios_operadores") or {}).values()
                if float((vals or {}).get("L", 0.0) or 0.0) > 1.0
            ]
            if capturas_casa:
                continue
            reg = operadores_capturados.setdefault(
                str(fx_disp.get("operador") or "snapshot"), {"disponible": False, "capturas_validas": 0})
            reg["capturas_validas"] += 1
            reg["disponible"] = True
        operadores_capturados["mejor_combinacion"] = {
            "disponible": any(v["disponible"] for v in operadores_capturados.values()),
            "capturas_validas": sum(v["capturas_validas"] for v in operadores_capturados.values()),
        }

        for fx in fix_snap.matches_json:
            mid = fx.get("id_partido", "")
            if req.selected_match_ids and mid not in req.selected_match_ids:
                continue
            if fx.get("estado") == "FINALIZADO" and not en_backtesting:
                # [ARCH-1.6.2] Partido concluido: vetado de la ventanilla de capital.
                _descartar_partido(
                    descartes, mid, fx.get("local", ""), fx.get("visitante", ""),
                    "Partido finalizado: fuera de ventanilla [ARCH-1.6.2]",
                    "QBE-00", "QBE-00", "Partido finalizado: fuera de ventanilla [ARCH-1.6.2]")
                continue

            # [ARCH-1.4.35 / CONMUTADOR DE SLATES] En BACKTESTING la jornada anclada es
            # necesariamente histórica: el veto [ARCH-1.6.2] se suspende porque la liquidación
            # real EXIGE el resultado concluido. Cero relajación más: el partido sin captura
            # fáctica de cuotas muere igual en la compuerta de abajo ([GOVERNANCE-01]).

            # Extraer cuotas del operador solicitado
            m_ops = fx.get("momios_operadores") or {}
            # [LN-QBE-076 / ARCH-1.4.15] Lane de Mejor Combinación Cross-Market: sólo entran a la
            # puja las capturas FÁCTICAS de cada operador que publican cuota de local (L > 1.0).
            # Una casa sin cuotas no participa ni presta sus datos a nombre de otra.
            lane_combinado = op_sel == "mejor_combinacion"
            cuotas_lane = {
                op: (vals or {}) for op, vals in m_ops.items()
                if float((vals or {}).get("L", 0.0) or 0.0) > 1.0
            }
            if lane_combinado:
                if not cuotas_lane:
                    # [ARCH-1.4.15 / LN-QBE-076 · Dictamen V-6] Degradación MONO-FUENTE legislada:
                    # sin capturas multi-casa la puja cae a la captura CANÓNICA del snapshot, con su
                    # procedencia declarada (`fx["operador"]`). Cero atribución a una casa local que
                    # no publicó esa cuota ([GOVERNANCE-01]); idéntica axiomática que el helper
                    # legislado `_cuotas_del_operador()` (carril del Live Board).
                    canonica = _captura_canonica_1x2(fx)
                    if not canonica:
                        _descartar_partido(
                            descartes, mid, fx.get("local", ""), fx.get("visitante", ""),
                            "Sin captura multi-operador suficiente para la Mejor Combinación",
                            "QBE-00", "QBE-00", "Sin captura multi-operador suficiente para la Mejor Combinación")
                        continue
                    cuotas_lane = {str(fx.get("operador") or "snapshot"): canonica}
                # Referencia mono-operador para el pre-chequeo de factibilidad: la casa que
                # paga el mejor momio del local (mejor ejecución de la pierna Ataque).
                m_data = max(cuotas_lane.values(), key=lambda v: float(v.get("L", 0.0)))
            else:
                m_data = m_ops.get(op_sel) or fx.get("momios") or {}
            if not m_data or not m_data.get("L"):
                # [GOVERNANCE-01] Sin cuotas capturadas no existe +EV calculable: cero cuotas inventadas.
                _descartar_partido(
                    descartes, mid, fx.get("local", ""), fx.get("visitante", ""),
                    "Sin cuotas publicadas por el operador solicitado",
                    "QBE-00", "QBE-00", "Sin cuotas publicadas por el operador solicitado")
                continue

            o_l = float(m_data.get("L", 0.0))
            o_e = float(m_data.get("E", 0.0))
            o_v = float(m_data.get("V", 0.0))
            pa = bool(m_data.get("pa", False) or m_data.get("pago_anticipado", False))

            # -- [ARCH-1.4.8 3] Compuerta de Descarte Temprano de Rentabilidad --
            # El veredicto del triaje de cuotas [LN-QBE-005] viaja CERTIFICADO en el snapshot
            # (`es_viable_triaje` / `motivo_triaje`). Un volado simetrico sin asimetria explotable
            # se deriva a QBE-00 con $0.00 MXN ANTES de asignar capital o ejecutar Dutching.
            if fx.get("es_viable_triaje", True) is False:
                motivo_veto = fx.get("motivo_triaje") or "Volado sin margen de cobertura bilateral (+EV nulo en cuotas)"
                _descartar_partido(
                    descartes, mid, fx.get("local", ""), fx.get("visitante", ""),
                    motivo_veto, "QBE-00", "QBE-00", motivo_veto)
                continue

            # [GOVERNANCE-01] Lectura fáctica: Priorizar distribución del Fixture; fallback a 3NF; prohibido inventar 0.55
            dist_db = session.query(SovereignDistribution).filter(SovereignDistribution.match_id == mid).first()
            p_l = fx.get("p_local") if fx.get("p_local") is not None else (dist_db.p_local if dist_db else None)
            p_e = fx.get("p_empate") if fx.get("p_empate") is not None else (dist_db.p_empate if dist_db else None)
            p_v = fx.get("p_visitante") if fx.get("p_visitante") is not None else (dist_db.p_visitante if dist_db else None)

            # Si ningún estrato contiene la distribución, descartar hacia cuarentena fiduciaria
            # (contrato canónico vigente `_descartar_partido(fx, motivo)`: QBE-00 / $0.00 MXN /
            #  explicación didáctica; cero cuotas ni probabilidades inventadas).
            if p_l is None or p_e is None or p_v is None:
                _descartar_partido(
                    descartes, mid, fx.get("local", ""), fx.get("visitante", ""),
                    "Sin distribución soberana fáctica en base de datos.",
                    "QBE-00", "QBE-00", "Sin distribución soberana fáctica en base de datos.")
                continue

            # -- Estratos epistémicos [LN-QBE-070-C] ------------------------------------------
            # NO existe estrato fáctico certificado para Δ_epist / Ψ_epist: el snapshot no los
            # porta y la columna 3NF `epistemic_delta` almacena magnitudes FUERA del rango
            # legislado Δ_epist ∈ [0,1) (su unidad no está certificada), por lo que NO se
            # transcribe. Se emiten los defaults LEGISLADOS del Contrato R-1 [LN-QBE-070-C] /
            # Directiva Fase 5 Paso 3: delta_epist = DELTA_EPIST_DEFAULT (portfolio.py L246-249).
            # Ψ se deriva con la fórmula canónica VERBATIM de `calcular_ranking_friccion`
            # (portfolio_math.py L139): Ψ = 1 − (Δ/0.12)², y Ψ = 0 ⟺ Cuarentena Fiduciaria.
            delta_epist = DELTA_EPIST_DEFAULT
            psi_epist = max(0.0, 1.0 - (delta_epist / 0.12) ** 2) if delta_epist <= 0.12 else 0.0
            # André: el diagnóstico del fixture primero, el estrato 3NF después y, si tampoco
            # existe, el valor neutro LEGISLADO para "no evaluado" (portfolio.py L298-303:
            # `phi_lead2_home = 0.0` en la rama de suficiencia informativa insuficiente).
            # Cero tasas André inventadas.
            phi_lead2 = fx.get("phi_lead2_home")
            if phi_lead2 is None and dist_db is not None:
                phi_lead2 = dist_db.phi_lead2_home
            if phi_lead2 is None:
                phi_lead2 = 0.0

            # -- [LN-QBE-076] Arbitraje Sintético Cross-Market: Mejor Ejecución por Pierna --
            # La casa que el usuario debe visitar para cada boleto se decide por máximo momio
            # observado en la captura fáctica del snapshot. El favorito soberano (p_l vs p_v)
            # fija el key de la pierna Ataque; la pierna Seguro es siempre el Empate.
            op_ataque: Optional[str] = None
            op_seguro: Optional[str] = None
            op_und: Optional[str] = None
            if lane_combinado:
                key_fav_soberano = "L" if p_l >= p_v else "V"
                arb_fav = resolver_mejor_combinacion_cuotas(cuotas_lane, fav=key_fav_soberano)
                # El leg restante (no favorito) se resuelve con LA MISMA función canónica
                # invocada sobre el key opuesto: cero lógica nueva, idéntica axiomática de máximo.
                arb_resto = resolver_mejor_combinacion_cuotas(
                    cuotas_lane, fav="V" if key_fav_soberano == "L" else "L")
                o_fav_arb = float(arb_fav["ataque"]["momio"])
                o_resto_arb = float(arb_resto["ataque"]["momio"])
                if key_fav_soberano == "L":
                    o_l, o_v = o_fav_arb, o_resto_arb
                else:
                    o_l, o_v = o_resto_arb, o_fav_arb
                o_e = float(arb_fav["seguro"]["momio"])
                op_ataque = str(arb_fav["ataque"]["operador"])
                op_seguro = str(arb_fav["seguro"]["operador"])
                # Casa del leg restante (no favorito), resuelta con la misma función canónica:
                # etiqueta los boletos de las estrategias R1/R2, cuyo boleto 2 viaja en el momio bajo.
                op_und = str(arb_resto["ataque"]["operador"])
                # El Pago Anticipado es un atributo de la casa que emite el boleto de Ataque
                # (pierna primaria); jamás se hereda la promoción de una casa distinta.
                pa = bool(arb_fav["ataque"]["pa"])

            payload_match = {
                "p_local": p_l, "p_empate": p_e, "p_visitante": p_v,
                "delta_epist": delta_epist, "es_operable": True,
                "phi_lead2_home": phi_lead2
            }
            cuotas_match = {"L": o_l, "E": o_e, "V": o_v, "pa": pa}

            # 1. Triaje determinista de las 9 estrategias
            triaje = triaje_determinista_9_estrategias(
                payload_match, cuotas_match, gamma=parametros_cartera.gamma_threshold
            )
            if triaje["codigo"] == "QBE-00":
                # [LN-QBE-078] Desglose cuantitativo transparente del veto fiduciario.
                p_fav_veto = p_l if p_l >= p_v else p_v
                odd_fav_veto = o_l if p_l >= p_v else o_v
                metricas_veto = {
                    "p_fav": round(p_fav_veto, 3),
                    "cuota_fav": odd_fav_veto,
                    "cuota_empate": o_e,
                    "alpha_max": round(triaje.get("alpha", 0.0), 3),
                    "theta_estrella": round(odd_fav_veto / (odd_fav_veto - 1.0), 2) if odd_fav_veto > 1.0 else 99.0
                }
                # [LN-QBE-040-C] El Radar de Descartes publica el motivo fiduciario REAL
                # emitido por el triaje ([LN-QBE-078]/[LN-QBE-065]); sólo cuando el contrato
                # no lo trae (p. ej. veto temprano por no-operabilidad) se rotula el
                # diagnóstico α. Prohibido inventar causa raíz en la cara al usuario.
                _descartar_partido(
                    descartes, mid, fx.get("local", ""), fx.get("visitante", ""),
                    triaje.get("motivo") or f"Cuarentena / Sin Valor: α = {metricas_veto['alpha_max']}",
                    "QBE-00", "QBE-00",
                    f"Q-BE: {round(p_l*100)}% · {round(p_e*100)}% · {round(p_v*100)}% | Momios: {o_l}/{o_e}/{o_v} | α_max: {metricas_veto['alpha_max']} (-EV)",
                    metricas_cifras=metricas_veto
                )
                continue

            # Determinar favorito vs underdog
            if p_l >= p_v:
                fav_name, und_name = fx.get("local", "Local"), fx.get("visitante", "Visita")
                odd_fav, odd_und = o_l, o_v
                p_fav, p_und = p_l, p_v
            else:
                fav_name, und_name = fx.get("visitante", "Visita"), fx.get("local", "Local")
                odd_fav, odd_und = o_v, o_l
                p_fav, p_und = p_v, p_l

            partidos_candidatos.append({
                "id_partido": mid,
                "partido_nombre": f"{fx.get('local')} vs {fx.get('visitante')}",
                "horario": fx.get("horario", "Fin de Semana"),
                "strategy_code": triaje["codigo"],
                "strategy_nombre": triaje["nombre"],
                "ev_neto_roi": triaje["alpha"],
                "psi_downside": PSI_DOWNSIDE_DEFAULT,
                "delta_epist": delta_epist,
                "psi_epist": psi_epist,
                "phi_lead2": phi_lead2,
                "odd_fav": odd_fav,
                "odd_emp": o_e,
                "odd_und": odd_und,
                "fav_name": fav_name,
                "und_name": und_name,
                "prob_fav": round(p_fav * 100.0, 1),
                "prob_emp": round(p_e * 100.0, 1),
                "prob_und": round(p_und * 100.0, 1),
                "pago_anticipado": pa,
                "operador_ataque": op_ataque,
                "operador_seguro": op_seguro,
                "operador_und": op_und,
                "alpha": triaje["alpha"]
            })

        if not partidos_candidatos:
            # [LN-QBE-025-B] & [ARCH-1.4.35] AXIOMA DE LA CARTERA VACÍA: la ausencia de activos con
            # +EV NO es un error de cliente (HTTP 400). Es una decisión fiduciaria explícita: se
            # preserva el 100% del capital en efectivo y se emite el contrato `PortfolioExecutionPlan`
            # con HTTP 200 y $0.00 MXN en riesgo. El rastro fáctico del veto ([LN-QBE-078] /
            # [ARCH-1.4.8 §3]) y el denominador de cartelera ([ARCH-1.4.14]) viajan SIEMPRE en el
            # payload emitido: cero pérdida de auditabilidad (mismo pos-procesamiento que la cartera
            # con posiciones, líneas 686-699 de este controlador).
            from src.pipeline.adapter import generar_cartera_vacia_fiduciaria

            plan_vacio = generar_cartera_vacia_fiduciaria(
                bankroll=req.bankroll,
                mensaje=(
                    "Ningún partido superó el triaje fiduciario (+EV). "
                    "Capital 100% preservado en efectivo."
                )
            )
            plan_vacio["descartes"] = descartes
            plan_vacio["control_portafolio"]["total_partidos_jornada"] = total_jornada
            plan_vacio["control_portafolio"]["total_partidos_escaneados"] = total_jornada
            plan_vacio["operadores_disponibles"] = operadores_capturados
            plan_vacio["parametros_cartera"] = parametros_cartera.model_dump()
            # [ARCH-1.4.35] Cartera vacía en BACKTESTING: el agregado declara la jornada anclada y
            # el denominador íntegro de órdenes sin liquidar (cero PnL inventado [GOVERNANCE-01]).
            if en_backtesting:
                plan_vacio = _adjuntar_liquidacion_real(
                    plan_vacio, session, jornada_anclada, fixtures_por_id)
            return plan_vacio

        # 2. Ranking de Friccion
        candidatos_ordenados = calcular_ranking_friccion(partidos_candidatos)

        # 3. Construccion del Plan via PortfolioEngine
        # [ARCH-1.4.37] La modalidad de Cobertura Dinámica δ viaja VERBATIM al motor: el orquestador
        # sólo transporta el parámetro; la resolución y el clamping son ley pura del motor.
        plan = PortfolioEngine.build_plan(
            candidatos_ordenados, bankroll=parametros_cartera.total_bankroll, mode="BANKROLL",
            total_jornada=total_jornada, modo_cobertura=req.modo_cobertura)
        data = plan.model_dump()

        # 4. Modulacion con Slider de Certeza [LN-QBE-073] — ALT-1 RATIFICADO (VAR FASE5_PASO3)
        #    (a) El modulador recibe la orden en su contrato PLANO [VAULT-CORE-006]; entregarle el
        #        dump Pydantic anidado dejaba el control INERTE (V-1/V-2).
        #    (b) La cartera superviviente (podada / transmutada D->H1) se RE-DESPACHA por el motor
        #        canonico: `3^K`, la cascada de reveses, `control_portafolio` y `trinidad_resiliencia`
        #        vuelven a describir la cartera EFECTIVAMENTE entregada (resuelve V-3).
        #    Cero matematica nueva: el puente solo transporta capital y probabilidad certificadas.
        if parametros_cartera.certainty_slider and parametros_cartera.certainty_slider != 0.80:
            por_id = {c["id_partido"]: c for c in candidatos_ordenados}
            ordenes_planas = [
                _orden_a_contrato_slider(o.model_dump(), por_id[o.id_partido])
                for o in plan.ordenes_ejecucion_partidos
                if o.id_partido in por_id
            ]
            supervivientes = modular_cartera_por_slider_certeza(
                ordenes_planas, target_certeza_pct=parametros_cartera.certainty_slider * 100.0
            )

            candidatos_finales: List[Dict[str, Any]] = []
            codigos_finales: Dict[str, str] = {}
            for s in supervivientes:
                cand = por_id.get(s.get("id"))
                if cand is None:
                    continue
                cand = dict(cand)
                transmutado = s.get("estrategia_codigo")
                if transmutado:
                    # [VAULT-CORE-006] Transmutacion D->H1 decretada por el modulador: el motor
                    # canonico recalcula la cobertura (Trinidad 3^K) desde la identidad de estrategia.
                    cand["strategy_code"] = transmutado
                codigos_finales[cand["id_partido"]] = str(cand.get("strategy_code", "")).replace("+", "").strip()
                candidatos_finales.append(cand)

            codigos_previos = {
                o.id_partido: o.estrategia_seleccionada.codigo.replace("+", "").strip()
                for o in plan.ordenes_ejecucion_partidos
            }
            if candidatos_finales and (
                len(candidatos_finales) != len(plan.ordenes_ejecucion_partidos)
                or codigos_finales != codigos_previos
            ):
                plan = PortfolioEngine.build_plan(
                    candidatos_finales, bankroll=parametros_cartera.total_bankroll, mode="BANKROLL",
                    total_jornada=total_jornada, modo_cobertura=req.modo_cobertura)
                data = plan.model_dump()

        # Alias de compatibilidad para The Shield
        data["balance_global_portafolio"] = data.get("balance_global_portafolio") or data.get("balance")
        data["control_portafolio"] = data.get("control_portafolio") or data.get("control")
        data["descartes"] = descartes

        # [ARCH-1.4.14] El denominador fáctico de cartelera viaja SIEMPRE en el payload emitido
        # (mismo patrón de pos-procesamiento que `src/pipeline/engine.py`): K / jornada, nunca K / K.
        data["control_portafolio"]["total_partidos_jornada"] = total_jornada
        data["control_portafolio"]["total_partidos_escaneados"] = total_jornada
        # [ARCH-1.4.15] Disponibilidad fáctica por operador para el selector de casinos.
        data["operadores_disponibles"] = operadores_capturados

        # [ARCH-1.4.30] Trazabilidad del parámetro interactivo de masa Γ (Capa 0) entregado por la UI.
        data["parametros_cartera"] = parametros_cartera.model_dump()

        # [ARCH-1.4.16] Atribución explícita de slug en mono-casino para renderizar logo
        operador_boleto = op_sel if op_sel in ("caliente", "novibet", "betway") else "caliente"
        for o_item in data.get("ordenes_ejecucion_partidos", []):
            if o_item.get("boletos"):
                if o_item["boletos"].get("boleto_1_seguro") and not o_item["boletos"]["boleto_1_seguro"].get("operador"):
                    o_item["boletos"]["boleto_1_seguro"]["operador"] = operador_boleto
                if o_item["boletos"].get("boleto_2_ganancia") and not o_item["boletos"]["boleto_2_ganancia"].get("operador"):
                    o_item["boletos"]["boleto_2_ganancia"]["operador"] = operador_boleto

        # [ARCH-1.4.35 / LN-QBE-025-B] BACKTESTING: con la jornada anclada, cada orden emitida se
        # liquida contra el marcador REAL de la bóveda 3NF y el payload publica el agregado
        # `backtesting`. La liquidación es evidencia AÑADIDA: montos, momios y estrategias del
        # contrato emitido quedan INTACTOS ([GOVERNANCE-01] paridad estricta backend↔pantalla).
        if en_backtesting:
            data = _adjuntar_liquidacion_real(data, session, jornada_anclada, fixtures_por_id)

        return data


@router.get("/progol/slates/active")
def get_active_progol_slate() -> Dict[str, Any]:
    """
    [LN-QBE-037 / DES-QBE-032 / ARCH-1.5.1-C] Concurso Progol activo leído de la bóveda 3NF.
    Expone el contraste entre la probabilidad soberana Q-BE persistida y la venta pública fáctica
    (sólo si existe captura de momios de casino de esa jornada; en su ausencia se declara
    explícitamente la no disponibilidad — [GOVERNANCE-01], cero cifras inventadas).
    """
    gateway = PersistenceGateway()
    with gateway.read_session() as session:
        slate = _cargar_slate_progol(session)

    if slate is None:
        return {
            "slate_id": None,
            "name": None,
            "status": None,
            "matchday_num": None,
            "bolsa_garantizada_mxn": None,
            "fecha_cierre": None,
            "items_total": 0,
            "soberanos": 0,
            "priors": 0,
            "sesgo_fuente": "BOVEDA_SIN_CONCURSO_OPEN",
            "items": []
        }

    return {
        "slate_id": slate["slate_id"],
        "name": slate["name"],
        "status": slate["status"],
        "matchday_num": slate["matchday_num"],
        "bolsa_garantizada_mxn": slate["bolsa_estimada"],
        "fecha_cierre": slate["fecha_cierre"],
        "items_total": len(slate["items"]),
        "soberanos": sum(1 for i in slate["items"] if not i["es_prior_ignorancia"]),
        "priors": sum(1 for i in slate["items"] if i["es_prior_ignorancia"]),
        "sesgo_fuente": slate["sesgo_fuente"],
        "items": slate["items"]
    }


@router.post("/progol/optimize")
def optimize_progol_endpoint(req: ProgolOptimizeRequest) -> Dict[str, Any]:
    """
    [ARCH-1.4.20 / VAULT-CORE-084-PROGOL-P-PRIME] Optimizador soberano por maximización de la masa
    acumulada P'. Se fija M = floor(presupuesto / costo_simple) y se prioriza la secuencia canónica
    P' del universo restringido 2^K (K = casillas con doble cobertura), maximizando C(M).
    El retículo de la matriz expone la ventana de cobertura binaria canónica [LN-QBE-085] y el
    bloque `boletas` expone cada quiniela priorizada por el motor, con su masa conjunta.
    El tablero se hidrata de `slate_items` (bloque REGULAR: las 14 casillas del concurso Progol).
    La frontera de inmutabilidad [LN-QBE-074] (`optimizar_quiniela_por_presupuesto`) permanece
    disponible para los consumidores históricos.
    """
    gateway = PersistenceGateway()
    with gateway.read_session() as session:
        slate = _cargar_slate_progol(session, slate_id=req.slate_id)

    if slate is None:
        raise HTTPException(status_code=404, detail="No existe concurso Progol activo en la bóveda 3NF.")

    items_regular = [i for i in slate["items"] if i["tipo_concurso"] == "REGULAR"][:SLATE_PROGOL_14]

    resultado_soberano = optimizar_quiniela_progol_soberana(
        partidos_14=items_regular,
        presupuesto_mxn=req.presupuesto_mxn,
        l_objetivo=14
    )

    cobertura_por_casilla = {
        c["order"]: c["opciones"] for c in seleccionar_cobertura_binaria_optima(items_regular)
    }

    matriz_quiniela = []
    for item in sorted(items_regular, key=lambda x: x.get("order", 0)):
        opciones = cobertura_por_casilla.get(item.get("order"), [])
        analisis = calcular_sesgo_quiniela(item.get("v_pub", {}), item.get("p_qbe", {}))
        matriz_quiniela.append({
            "order": item.get("order"),
            "local": item.get("local"),
            "visitante": item.get("visitante"),
            "juega_L": "L" in opciones,
            "juega_E": "E" in opciones,
            "juega_V": "V" in opciones,
            "alerta_sesgo": analisis.get("alerta_sesgo", False),
            "recomendacion": analisis.get("recomendacion_cobertura", "SIN_ANALISIS")
        })

    return {
        "motor": "PROGOL_P_PRIME_MASS",
        "combinaciones_totales": resultado_soberano["combinaciones_totales"],
        "costo_total_mxn": resultado_soberano["costo_total_mxn"],
        "dobles_asignados": sum(
            1 for fila in matriz_quiniela
            if sum((fila["juega_L"], fila["juega_E"], fila["juega_V"])) == 2
        ),
        "triples_asignados": sum(
            1 for fila in matriz_quiniela
            if sum((fila["juega_L"], fila["juega_E"], fila["juega_V"])) == 3
        ),
        "masa_acumulada_capturada": resultado_soberano["masa_acumulada_capturada"],
        "garantia_fiduciaria": resultado_soberano["garantia_fiduciaria"],
        "boletas": resultado_soberano["boletas"],
        "matriz_quiniela": matriz_quiniela
    }

