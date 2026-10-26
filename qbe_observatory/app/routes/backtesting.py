# -*- coding: utf-8 -*-
"""Rutas de backtesting y calibración del Observatorio (solo lectura).

Extraídas del monolito; la aritmética permanece en qbe_core / observatory.core.
"""

from typing import Any, Dict, List, Optional, Tuple
import logging
from contextlib import contextmanager
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app import config
from src.storage.models import FixtureSnapshot, Match, SovereignDistribution
from src.models.web_schemas import CalibrationReportResponse, SimulatePortfolioRequest

router = APIRouter(prefix="/api/observatory", tags=["Backtesting & Calibration"])
logger = logging.getLogger(__name__)


def _motor_solo_lectura():
    """Motor SQLite en `mode=ro`: el Observatorio jamás escribe el snapshot."""
    if not config.BACKTESTING_SNAPSHOT.is_file():
        raise RuntimeError(
            f"Snapshot de backtesting no disponible: {config.BACKTESTING_SNAPSHOT}"
        )
    ruta = config.BACKTESTING_SNAPSHOT.as_posix()
    return create_engine(
        f"sqlite:///file:{ruta}?mode=ro&uri=true",
        connect_args={"check_same_thread": False},
    )


def get_db_ro():
    motor = _motor_solo_lectura()
    sesion = sessionmaker(bind=motor)()
    try:
        yield sesion
    finally:
        sesion.close()
        motor.dispose()


class _ReadOnlyGateway:
    """Puerto mínimo que satisface a `simulation_engine` sin abrir escritura."""

    def __init__(self) -> None:
        self.engine = _motor_solo_lectura()
        self.SessionFactory = sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )

    @contextmanager
    def read_session(self):
        sesion = self.SessionFactory()
        try:
            yield sesion
        finally:
            sesion.close()

# ── [ARCH-1.4.38 / LN-QBE-100] VISOR DE BACKTESTING (CALIBRACIÓN FACTUAL DE TEMPORADA) ──
# [GOVERNANCE-01] Cero cifras sintéticas: el oráculo de resultados reales es la bóveda 3NF
# (`matches`) y la fuente de P'/cuotas de cierre son las capturas congeladas de
# `fixtures_snapshots.matches_json`. La aritmética de calibración NO vive aquí: se delega
# VERBATIM a las leyes selladas `desmarcar_cuotas_proporcional` y
# `calcular_brier_multicategorico` de `src.core.contracts.portfolio_math`
# ([DIRGEN-STRICT] — este controlador sólo TRANSPORTA el contrato plano).
# Prohibido acoplar el centinela de mercado al router web [ARCH-1.6.4].

_ESTADOS_CONCLUIDOS_BACKTESTING = frozenset({"FINISHED", "FINALIZADO"})


def _estado_concluido(valor: Any) -> bool:
    """[ARCH-1.4.38 · Enmienda] Normaliza el estado del partido (`FINISHED` ≡ `FINALIZADO`).

    La aduana tolera espacios y minúsculas: un estado rezagado en la captura no puede cambiar la
    conclusión fáctica de un partido que la evidencia ya cerró.
    """
    return str(valor or "").strip().upper() in _ESTADOS_CONCLUIDOS_BACKTESTING


def _captura_declara_resultado(fixture: Optional[Dict[str, Any]]) -> bool:
    """La captura congelada declara el partido TERMINADO (`is_finished` o su `estado`)."""
    if not isinstance(fixture, dict):
        return False
    return fixture.get("is_finished") is True or _estado_concluido(fixture.get("estado"))


def _marcador_de_captura(fixture: Optional[Dict[str, Any]]) -> Optional[Tuple[int, int]]:
    """Marcador consumado publicado por la captura congelada (`marcador_actual` = "L - V").

    Sólo se acepta con el sello de partido terminado y AMBOS goles enteros: una captura en curso
    o un marcador ilegible no producen resultado (cero fabricación, `[GOVERNANCE-01]`).
    """
    if not _captura_declara_resultado(fixture):
        return None
    crudo = str((fixture or {}).get("marcador_actual") or "").strip()
    if not crudo:
        return None
    normalizado = crudo.replace("–", "-").replace("—", "-").replace("−", "-")
    partes = [parte.strip() for parte in normalizado.split("-")]
    if len(partes) != 2 or not all(parte.isdigit() for parte in partes):
        return None
    return int(partes[0]), int(partes[1])


def _resultado_consumado(
    fila: Match, fixture: Optional[Dict[str, Any]]
) -> Optional[Tuple[int, int]]:
    """[ARCH-1.4.38 · Enmienda] Marcador consumado con precedencia DECLARADA.

    1. `matches` porta el marcador y su estado (normalizado) es concluyente ⇒ hecho sellado.
    2. `matches` porta el marcador pero el estado 3NF quedó rezagado ⇒ se admite sólo si la
       captura congelada declara el partido terminado (transición no sincronizada).
    3. `matches` NO porta marcador (J12/J13 con captura final) ⇒ se recupera el marcador que la
       captura publicó, que es evidencia congelada y la recuperación se declara en el log.

    Sin marcador legible y sin sello de partido terminado el partido NO entra al universo
    auditable: cero invención de resultados (`[GOVERNANCE-01]`).
    """
    tiene_marcador = fila.score_home is not None and fila.score_away is not None
    if tiene_marcador and (_estado_concluido(fila.status) or _captura_declara_resultado(fixture)):
        return int(fila.score_home), int(fila.score_away)
    if tiene_marcador:
        return None
    return _marcador_de_captura(fixture)


def _fixtures_snapshot_indexados(
    session: Session, league_id: Optional[int] = None
) -> Dict[str, Dict[str, Any]]:
    """
    [ARCH-1.4.38] Índice `{id_partido: fixture}` sobre las capturas congeladas de la bóveda.
    Ante varios snapshots de la MISMA jornada rige el más reciente (`updated_at DESC`).
    """
    consulta = session.query(FixtureSnapshot)
    if league_id is not None:
        consulta = consulta.filter(FixtureSnapshot.league_id == int(league_id))
    snapshots = consulta.order_by(
        FixtureSnapshot.matchday.asc(), FixtureSnapshot.updated_at.desc()
    ).all()

    indice: Dict[str, Dict[str, Any]] = {}
    for snap in snapshots:
        for fx in (snap.matches_json or []):
            id_partido = str(fx.get("id_partido") or "")
            if id_partido:
                indice.setdefault(id_partido, fx)
    return indice


def _soberanas_por_id(session: Session) -> Dict[str, Tuple[float, float, float]]:
    """
    [ARCH-1.4.38] Respaldo SECUNDARIO de P': la tabla soberana 3NF
    (`sovereign_distributions`). La autoridad primaria es la captura del snapshot.
    """
    return {
        str(fila.match_id): (
            float(fila.p_local), float(fila.p_empate), float(fila.p_visitante)
        )
        for fila in session.query(SovereignDistribution).all()
    }


def _trazas_soberanas_por_id(session: Session) -> Dict[str, Dict[str, Any]]:
    """
    [ARCH-1.4.42] Traza forense por partido desde `sovereign_distributions`.

    Devuelve `{id_partido: {audit_trace, lambda_home, lambda_away, delta_epist}}` para que el
    motor de atribución factorial transcriba `factores_entrada` / `intensidades` / `Δ_epist`
    sin tocar la red ni recalcular la matemática soberana. Una fila sin traza aporta sólo sus
    intensidades publicadas: cero fabricación de factores [GOVERNANCE-01].
    """
    indice: Dict[str, Dict[str, Any]] = {}
    for fila in session.query(SovereignDistribution).all():
        traza = fila.audit_trace_json if isinstance(fila.audit_trace_json, dict) else {}
        indice[str(fila.match_id)] = {
            "audit_trace": traza,
            "lambda_home": fila.lambda_home,
            "lambda_away": fila.lambda_away,
            "delta_epist": fila.epistemic_delta,
        }
    return indice


def _origen_captura_de_traza(fila: Optional[Dict[str, Any]]) -> Optional[str]:
    """[LN-QBE-102] Sello de procedencia publicado por la traza soberana (`None` si no lo porta).

    La ausencia NO se interpreta como captura histórica: una traza legada (`origen_captura`
    inexistente) se declara `None` y la UI omite el badge en vez de acusar una procedencia falsa.
    """
    if not isinstance(fila, dict):
        return None
    traza = fila.get("audit_trace")
    if not isinstance(traza, dict):
        return None
    origen = traza.get("origen_captura")
    return str(origen) if origen else None


def _datos_partido_para_atribucion(
    traza: Optional[Dict[str, Any]],
    fixture: Optional[Dict[str, Any]],
    suficiencia_s_i: Optional[int],
) -> Dict[str, Any]:
    """
    [ARCH-1.4.42] Ensambla el payload fáctico del motor de atribución factorial.

    La traza soberana aporta factores/intensidades/Δ_epist; el fixture aporta únicamente los
    bloques que realmente porta (splits de sede, ventana H2H, localía efectiva). No se consulta
    la tabla de posiciones vivas: en un partido histórico sus agregados serían FUTURO respecto
    del instante de cálculo (look-ahead) y corromperían la auditoría.
    """
    datos: Dict[str, Any] = dict(traza or {})
    if isinstance(fixture, dict):
        for clave in (
            "home_team_stats",
            "away_team_stats",
            "home_split_stats",
            "away_split_stats",
            "h2h_matches",
            "h2h_partidos",
            "gamma_home",
            "xg_disponible",
            "xg_calibrado",
            "q_mod_home",
            "q_mod_away",
            # [LN-QBE-102] Telemetría de insumos y sello de procedencia (candado en vivo).
            "insumos_factivados",
            "origen_captura",
        ):
            if fixture.get(clave) is not None:
                datos[clave] = fixture[clave]
    if suficiencia_s_i is not None:
        datos.setdefault("S_I", suficiencia_s_i)
    return datos


def _atribucion_factorial_del_partido(
    traza: Optional[Dict[str, Any]],
    fixture: Optional[Dict[str, Any]],
    suficiencia_s_i: Optional[int],
) -> Dict[str, Any]:
    """[ARCH-1.4.42] Bloque `atribucion_factorial` de la casilla micro (motor puro)."""
    from src.observatory.core.factor_attribution import construir_atribucion_factorial

    return construir_atribucion_factorial(
        _datos_partido_para_atribucion(traza, fixture, suficiencia_s_i)
    )


def _p_prima_del_fixture(fx: Dict[str, Any]) -> Optional[Tuple[float, float, float]]:
    """[ARCH-1.4.38] P' sellada en la captura congelada; `None` si la bóveda no la porta."""
    try:
        return (
            float(fx.get("p_local")),
            float(fx.get("p_empate")),
            float(fx.get("p_visitante")),
        )
    except (TypeError, ValueError):
        return None


# ── [LN-QBE-127] RESOLUCIÓN DINÁMICA DE P′ PARA EL UNIVERSO AUDITABLE ─────────
# Sellos de procedencia publicados por la casilla micro (`origen_p_prima`). Se declaran como
# constantes para que ningún literal suelto pueda divergir entre el productor y los consumidores.
ORIGEN_P_PRIMA_CAPTURA = "CAPTURA"
ORIGEN_P_PRIMA_SOBERANA = "SOBERANA"
ORIGEN_P_PRIMA_AL_VUELO = "AL_VUELO"

# Lista CERRADA de insumos PRE-KICKOFF que la resolución al vuelo puede tomar de la bóveda. Se
# ciñe a las claves que el plano canónico realmente consume (`_datos_partido_para_atribucion`,
# `_extraer_bloque_forma_10p`, V29 de altitud): no se inventa un campo que la captura no publica.
_CLAVES_RESOLUCION_AL_VUELO = (
    "home_team_stats",
    "away_team_stats",
    "home_split_stats",
    "away_split_stats",
    "form_10p",
    "h2h_matches",
    "h2h_partidos",
    "gamma_home",
    "xg_disponible",
    "xg_calibrado",
    "q_mod_home",
    "q_mod_away",
    "delta_alt_metros",
)


def _p_prima_al_vuelo(
    fila: Match,
    fixture: Optional[Dict[str, Any]],
    traza: Optional[Dict[str, Any]],
) -> Optional[Tuple[float, float, float]]:
    """
    [LN-QBE-127] Resolución DINÁMICA de P′ para un partido concluido sin distribución sellada.

    `matches` es la fuente única de verdad de la calibración: descartar en silencio un partido
    concluido porque su jornada no capturó cuotas es una ceguera de universo, no una salvaguarda.
    El vector se pide AL MOTOR SOBERANO SELLADO (`generar_distribucion_soberana`,
    [DIRGEN-STRICT]) —cero reimplementación del prior, cero matemática local— con los insumos
    fácticos PRE-KICKOFF que la bóveda realmente porta: precedencia declarada
    **traza soberana → snapshot de captura** (lo que el motor consumió manda sobre lo exhibido).

    Sin un solo insumo el motor publica el prior de ignorancia fiduciario R-1
    (0.3333, 0.3333, 0.3334); el llamador lo declara `AL_VUELO` con `suficiencia_S_I = 0`.

    La resolución es EFÍMERA: no se persiste (una segunda fila en `sovereign_distributions` sería
    una segunda verdad). Devuelve `None` sólo si el motor falla; el llamador lo contabiliza como
    pendiente y lo registra en el log (cero descarte mudo).
    """
    from src.core.sovereign_pipeline import generar_distribucion_soberana

    datos: Dict[str, Any] = {
        "home_team_slug": getattr(fila, "home_team_slug", None),
        "away_team_slug": getattr(fila, "away_team_slug", None),
    }
    for origen in (traza, fixture):
        if not isinstance(origen, dict):
            continue
        for clave in _CLAVES_RESOLUCION_AL_VUELO:
            if datos.get(clave) is None and origen.get(clave) is not None:
                datos[clave] = origen[clave]

    try:
        salida = generar_distribucion_soberana(match_id=str(fila.id), raw_match_data=datos)
    except Exception as exc:
        logger.warning(
            f"⚠️ [LN-QBE-127] Resolución al vuelo imposible para el partido {fila.id}: {exc}"
        )
        return None

    return (float(salida.p_local), float(salida.p_empate), float(salida.p_visitante))


def _cuotas_1x2_factuales(fx: Dict[str, Any]) -> Dict[str, float]:
    """
    [ARCH-1.4.38] Trío 1X2 factual para el desmarque: captura CANÓNICA del snapshot
    ([ARCH-1.4.15]) con respaldo determinista en la mejor captura por operador. Un fixture
    sin trío completo devuelve `{}`: cero cuotas prestadas entre casas [GOVERNANCE-01].

    Decreto del Director (2026-10-14): la captura congelada se lee con FALLBACK DUAL,
    `cuotas` (ingesta explícita) o `momios` (ingesta nativa). El mismo trío factual no puede
    quedar invisible al Visor por el nombre del campo que lo porta: el Brier del mercado se
    deriva de las cuotas de cierre realmente capturadas, jamás de un relleno uniforme.
    """
    cuotas_dict = fx.get("cuotas") or fx.get("momios") or {}
    try:
        if all(float(cuotas_dict.get(k, 0.0) or 0.0) > 1.0 for k in ("L", "E", "V")):
            return {
                "L": float(cuotas_dict["L"]),
                "E": float(cuotas_dict["E"]),
                "V": float(cuotas_dict["V"]),
            }
    except (TypeError, ValueError):
        pass

    canonica = _captura_canonica_1x2(fx)
    if canonica:
        return {"L": canonica["L"], "E": canonica["E"], "V": canonica["V"]}

    capturas = fx.get("momios_operadores") or {}
    for operador in sorted(capturas.keys()):
        m_data = capturas.get(operador) or {}
        try:
            if all(float(m_data.get(k, 0.0) or 0.0) > 1.0 for k in ("L", "E", "V")):
                return {
                    "L": float(m_data["L"]),
                    "E": float(m_data["E"]),
                    "V": float(m_data["V"]),
                }
        except (TypeError, ValueError):
            continue
    return {}


def _desenlace_real_1x2(score_home: int, score_away: int) -> str:
    """[LN-QBE-100] Traducción factual del marcador consumado al desenlace 1X2."""
    if score_home > score_away:
        return "LOCAL"
    if score_home < score_away:
        return "VISITANTE"
    return "EMPATE"


def _clasificacion_factual(
    desenlace_real: str, p_local: float, p_visitante: float
) -> Tuple[str, str]:
    """
    [LN-QBE-100] Clasificación factual: `FAVORITO` (el desenlace coincide con el favorito de
    P'), `EMPATE` (marcador nivelado) o `UNDERDOG` (ganó el rival no cubierto).
    Devuelve `(favorito_designado, tipo_resultado)`.
    """
    favorito = "LOCAL" if p_local >= p_visitante else "VISITANTE"
    if desenlace_real == "EMPATE":
        return favorito, "EMPATE"
    return favorito, ("FAVORITO" if desenlace_real == favorito else "UNDERDOG")


def _alpha_calibracion_pct(brier_qbe: float, brier_mercado: float) -> float:
    """[LN-QBE-100] Alpha de Calibración = (1 - BS_QBE / BS_MKT) × 100. Guarda de cero."""
    if brier_mercado <= 0.0:
        return 0.0
    return round((1.0 - (brier_qbe / brier_mercado)) * 100.0, 2)


def _delta_altitud_del_partido(
    traza: Optional[Dict[str, Any]],
    fixture: Optional[Dict[str, Any]],
    fila: Match,
) -> float:
    """
    [LN-QBE-124 / ARCH-1.4.64 · BR-3] Desnivel positivo del anfitrión que decide la Banda de
    Indiferencia: ΔAlt⁺ = max(0, altitud_local − altitud_visita).

    Precedencia DECLARADA (prohibida toda imputación silenciosa [GOVERNANCE-01]):
      1. `delta_alt_metros` del propio fixture, si la captura lo publicara.
      2. Traza V29 de `sovereign_distributions.audit_trace_json` → la magnitud que λ REALMENTE
         consumió (`insumos_factivados.contexto.insumos.delta_alt_metros` o su clave plana).
      3. Catálogo inmutable de plazas `altitud_estadio(local) − altitud_estadio(visita)`.
      4. Ausencia de evidencia ⇒ `0.0` **declarado** (sin desnivel ⇒ sin rescate).
    """
    insumos = ((traza or {}).get("audit_trace") or {}).get("insumos_factivados") or {}
    contexto = insumos.get("contexto") or {}
    candidatos = [
        (fixture or {}).get("delta_alt_metros"),
        (contexto.get("insumos") or {}).get("delta_alt_metros"),
        insumos.get("delta_alt_metros"),
    ]
    for valor in candidatos:
        if valor is None:
            continue
        try:
            return round(max(0.0, float(valor)), 1)
        except (TypeError, ValueError):
            continue

    from src.observatory.core.context_provider import altitud_estadio

    altitud_local = altitud_estadio(getattr(fila, "home_team_slug", None))
    altitud_visita = altitud_estadio(getattr(fila, "away_team_slug", None))
    if altitud_local is None or altitud_visita is None:
        return 0.0
    return round(max(0.0, float(altitud_local) - float(altitud_visita)), 1)


def _agregar_resumen_calibracion(
    partidos: List[Dict[str, Any]],
    registros_qbe: List[Dict[str, Any]],
    registros_mkt: List[Dict[str, Any]],
    jornadas_auditadas: List[int],
    partidos_pendientes: int,
) -> Dict[str, Any]:
    """
    [LN-QBE-125] Agregado macro ÚNICO del Visor (una sola aritmética para las dos muestras).

    Recibe los micro-DTO planos del universo elegido y sus registros de Brier, y emite el bloque
    `CalibrationSummaryOut` completo: tasas puras por vértice del símplex Δ² (P_max · P_mid ·
    P_low ≡ 100 %), desglose factual del rescate secundario (empate vs rival), Brier dual y Alpha
    de calibración. Cero ponderación, cero cifra fabricada: con `partidos` vacío toda tasa es 0.0.
    """
    from src.core.contracts.portfolio_math import calcular_brier_multicategorico

    total = len(partidos)
    favorito_t = sum(1 for p in partidos if p["tipo_resultado"] == "FAVORITO")
    empate_t = sum(1 for p in partidos if p["tipo_resultado"] == "EMPATE")
    underdog_t = sum(1 for p in partidos if p["tipo_resultado"] == "UNDERDOG")

    total_p_max = sum(1 for p in partidos if p["clasificacion_triada"] == "P_MAX")
    total_p_mid = sum(1 for p in partidos if p["clasificacion_triada"] == "P_MID")
    total_p_low = sum(1 for p in partidos if p["clasificacion_triada"] == "P_LOW")
    total_p_mid_empate = sum(
        1
        for p in partidos
        if p["clasificacion_triada"] == "P_MID"
        and p["resultado_real"] == "EMPATE"
        and p["r_mid"] == "EMPATE"
    )
    total_p_mid_rival = total_p_mid - total_p_mid_empate

    def _pct(cantidad: int) -> float:
        return round((cantidad / total) * 100.0, 2) if total else 0.0

    p_max_aciertos_pct = _pct(total_p_max)
    p_mid_rescate_pct = _pct(total_p_mid)
    p_low_ruptura_pct = _pct(total_p_low)
    bs_qbe = calcular_brier_multicategorico(registros_qbe)
    bs_mkt = calcular_brier_multicategorico(registros_mkt)
    # [LN-QBE-127] Resoluciones dinámicas del universo recibido: se DERIVAN del propio micro-DTO
    # (cero parámetro extra, cero segunda contabilidad). En el segmento informado (S=1) vale 0 por
    # construcción: una resolución al vuelo jamás declara suficiencia.
    total_resueltos_al_vuelo = sum(
        1 for p in partidos if p.get("origen_p_prima") == ORIGEN_P_PRIMA_AL_VUELO
    )

    return {
        "total_partidos": total,
        "partidos_favorito": favorito_t,
        "partidos_empate": empate_t,
        "partidos_underdog": underdog_t,
        "tasa_coincidencia_fiduciaria_pct": (
            round(((favorito_t + empate_t) / total) * 100.0, 2) if total else 0.0
        ),
        # [LN-QBE-100 · REFACTOR-TRIADA-PMAX-PMID-PLOW] Taxonomía macro de vértices (payload
        # sellado por [ARCH-1.4.38]): masa de cobertura y desglose factual del rescate P_mid.
        "masa_cobertura_pct": round(p_max_aciertos_pct + p_mid_rescate_pct, 2),
        "p_max_aciertos_pct": p_max_aciertos_pct,
        "p_mid_rescate_pct": p_mid_rescate_pct,
        "p_mid_empate_pct": _pct(total_p_mid_empate),
        "p_mid_rival_pct": _pct(total_p_mid_rival),
        "p_low_ruptura_pct": p_low_ruptura_pct,
        "total_p_max": total_p_max,
        "total_p_mid": total_p_mid,
        "total_p_low": total_p_low,
        "total_p_mid_empate": total_p_mid_empate,
        "total_p_mid_rival": total_p_mid_rival,
        "brier_score_qbe": bs_qbe,
        "brier_score_mercado": bs_mkt,
        "alpha_calibracion_pct": _alpha_calibracion_pct(bs_qbe, bs_mkt),
        "partidos_pendientes_captura": partidos_pendientes,
        # [LN-QBE-127] Partidos concluidos cuyo P′ se resolvió dinámicamente (sin distribución
        # sellada). Declarados y contados: la ceguera de captura se mide, jamás se esconde.
        "partidos_resueltos_al_vuelo": total_resueltos_al_vuelo,
        "jornadas_auditadas": sorted(jornadas_auditadas),
    }


def _construir_reporte_calibracion(
    session: Session, league_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    [ARCH-1.4.38 / LN-QBE-100 / LN-QBE-127] Reporte macro/meso/micro de calibración factual.

    Universo auditable: partidos de la bóveda 3NF con estado concluido y marcador consumado.
    `matches` es la fuente ÚNICA de verdad: un partido que no porta P′ sellada (ni en la captura
    del snapshot ni en la tabla soberana) se resuelve AL VUELO por el motor soberano sellado y se
    declara `origen_p_prima = "AL_VUELO"` con `suficiencia_S_I = 0` [LN-QBE-127]. El descarte
    silencioso queda derogado: sólo se contabiliza como "Pendiente de captura" el partido en el
    que el motor no pudo emitir vector alguno (fallo declarado en el log) [GOVERNANCE-01].

    [ARCH-1.4.38 · Enmienda de Saneamiento] CERO TRUNCAMIENTO NO DECLARADO: el universo abarca
    TODAS las jornadas concluidas. Cuando el marcador consumado vive en la captura congelada
    (`estado`/`is_finished` ⇒ FINALIZADO y `marcador_actual` legible) pero la fila 3NF quedó
    rezagada, el resultado se recupera de la evidencia congelada con precedencia declarada
    (`matches` → captura) y la recuperación se cuenta en el log. Jamás se inventa un marcador.
    """
    from src.core.contracts.portfolio_math import (
        desmarcar_cuotas_proporcional,
        calcular_brier_multicategorico,
        resolver_orden_fiduciario_con_indiferencia,
    )

    fixtures = _fixtures_snapshot_indexados(session, league_id)
    soberanas = _soberanas_por_id(session)
    # [ARCH-1.4.42] Trazas forenses para la atribución factorial (una sola consulta, cero N+1).
    trazas_soberanas = _trazas_soberanas_por_id(session)

    micro_por_jornada: Dict[int, List[Dict[str, Any]]] = {}
    registros_qbe: Dict[int, List[Dict[str, Any]]] = {}
    registros_mkt: Dict[int, List[Dict[str, Any]]] = {}
    partidos_pendientes = 0
    # [LN-QBE-127] Contador entero de las resoluciones dinámicas: la ceguera de captura se MIDE.
    resoluciones_al_vuelo = 0
    # [LN-QBE-100 · REFACTOR-TRIADA-PMAX-PMID-PLOW] Conteos enteros de la taxonomía de vértices
    # por jornada: acierto primario (P_MAX), rescate secundario (P_MID, desglosado en empate vs
    # rival) y ruptura residual (P_LOW). Conteos puros: cero ponderación, cero cifra fabricada.
    triada_por_jornada: Dict[int, Dict[str, int]] = {}
    # [LN-QBE-125] Registros de Brier indexados por partido: la muestra calibrada se agrega con la
    # MISMA aritmética que la global, sin segunda verdad ni recálculo.
    registros_por_partido: Dict[str, Tuple[Dict[str, Any], Dict[str, Any]]] = {}

    filas = session.query(Match).order_by(Match.matchday_num.asc(), Match.id.asc()).all()
    marcadores_recuperados = 0

    for fila in filas:
        if fila.matchday_num is None:
            continue

        id_partido = str(fila.id)
        fixture = fixtures.get(id_partido)
        # [ARCH-1.4.38 · Enmienda] Universo COMPLETO: el marcador consumado manda y la captura
        # congelada rescata la transición 3NF rezagada (J12/J13). Prohibido el truncamiento no
        # declarado: la recuperación se cuenta y se publica, jamás se silencia.
        resultado_consumado = _resultado_consumado(fila, fixture)
        if resultado_consumado is None:
            continue
        goles_local, goles_visitante = resultado_consumado
        if fila.score_home is None or fila.score_away is None:
            marcadores_recuperados += 1
        # [ARCH-1.4.38] P' sellada: captura del snapshot o, EN SU DEFECTO, tabla soberana 3NF.
        # El respaldo rige también cuando el fixture EXISTE pero NO porta P' (jornadas históricas
        # con momios de cierre y distribución sellada sólo en la tabla soberana): sin él, una
        # jornada con cuotas reales quedaría invisible al Visor (Decreto del Director, 2026-10-14).
        p_prima = _p_prima_del_fixture(fixture) if fixture else None
        # [LN-QBE-127] Sello de procedencia del vector P′ servido (`CAPTURA` · `SOBERANA` ·
        # `AL_VUELO`): la vitrina y la matriz de investigación declaran de dónde sale cada P′.
        origen_p_prima = ORIGEN_P_PRIMA_CAPTURA if p_prima is not None else None
        if p_prima is None:
            p_prima = soberanas.get(id_partido)
            if p_prima is not None:
                origen_p_prima = ORIGEN_P_PRIMA_SOBERANA
        if p_prima is None:
            # [LN-QBE-127] UNIVERSO SIN DESCARTE SILENCIOSO: un partido CONCLUIDO con marcador
            # consumado JAMÁS se omite en silencio. Se resuelve AL VUELO por el motor soberano
            # sellado y la resolución se DECLARA (`AL_VUELO` · S(I)=0), de modo que la ceguera de
            # captura se mide en vez de esconderse [GOVERNANCE-01].
            p_prima = _p_prima_al_vuelo(fila, fixture, trazas_soberanas.get(id_partido))
            if p_prima is None:
                # Único descarte admitido: el motor no pudo emitir vector (fallo ya registrado).
                partidos_pendientes += 1
                continue
            resoluciones_al_vuelo += 1
            origen_p_prima = ORIGEN_P_PRIMA_AL_VUELO

        p_local, p_empate, p_visitante = p_prima
        desenlace = _desenlace_real_1x2(goles_local, goles_visitante)

        cuotas = _cuotas_1x2_factuales(fixture) if fixture else {}
        q_local, q_empate, q_visitante = desmarcar_cuotas_proporcional(
            float(cuotas.get("L", 0.0) or 0.0),
            float(cuotas.get("E", 0.0) or 0.0),
            float(cuotas.get("V", 0.0) or 0.0),
        )

        # [LN-QBE-125] Cold Start SINCERO — derogación expresa de la sustitución del *Axioma del
        # Prior de Mercado* ([LN-QBE-100]): un partido que declara ignorancia fáctica S(I)=0 se
        # puntúa con su P′ SOBERANA REAL (el prior puro del modelo). Sustituirla por el consenso
        # desmarcado q_mkt forzaba `BS_QBE ≡ BS_MKT` por identidad de vectores y fabricaba un
        # Alpha ≡ 0.00% que NO era una medición. La ceguera se DECLARA en la vitrina
        # (`es_cold_start` · `❄️ Cold Start (S=0)`), jamás se maquilla [GOVERNANCE-01].
        _s_i = (fixture or {}).get("suficiencia_S_I")
        suficiencia_s_i = 1 if _s_i is None else int(_s_i)
        if origen_p_prima == ORIGEN_P_PRIMA_AL_VUELO:
            # [LN-QBE-127] El vector emitido sin distribución sellada ES el prior de ignorancia:
            # declararlo informado fabricaría una calibración inexistente [GOVERNANCE-01].
            suficiencia_s_i = 0

        favorito, tipo_resultado = _clasificacion_factual(desenlace, p_local, p_visitante)

        # [LN-QBE-124 / ARCH-1.4.64] Jerarquía estocástica de vértices en Δ² DELEGADA al plano
        # canónico: la MISMA función pura que gobierna el triaje fiduciario resuelve aquí el orden
        # (cero segunda verdad). El desnivel ΔAlt⁺ se resuelve por precedencia declarada
        # (fixture → traza V29 → catálogo de plazas → 0.0), jamás por imputación silenciosa.
        delta_alt_metros = _delta_altitud_del_partido(
            trazas_soberanas.get(id_partido), fixture, fila
        )
        orden_fiduciario = resolver_orden_fiduciario_con_indiferencia(
            p_local, p_empate, p_visitante, delta_alt=delta_alt_metros
        )
        r_max, p_max_val = orden_fiduciario["r_max"], orden_fiduciario["p_max_val"]
        r_mid, p_mid_val = orden_fiduciario["r_mid"], orden_fiduciario["p_mid_val"]
        r_low, p_low_val = orden_fiduciario["r_low"], orden_fiduciario["p_low_val"]
        rescate_indiferencia = bool(orden_fiduciario["rescate_indiferencia"])

        if desenlace == r_max:
            clasificacion = "P_MAX"
        elif desenlace == r_mid:
            clasificacion = "P_MID"
        else:
            clasificacion = "P_LOW"

        es_pmid_empate = (r_mid == "EMPATE")

        registro_qbe = {
            "p_local": p_local, "p_empate": p_empate,
            "p_visitante": p_visitante, "resultado": desenlace,
        }
        registro_mkt = {
            "p_local": q_local, "p_empate": q_empate,
            "p_visitante": q_visitante, "resultado": desenlace,
        }

        jornada = int(fila.matchday_num)
        # [LN-QBE-100 · REFACTOR-TRIADA] Conteo entero del vértice consumado y de la procedencia
        # del rescate secundario (empate vs rival) en la jornada en curso.
        conteo_jornada = triada_por_jornada.setdefault(jornada, {
            "n_p_max": 0, "n_p_mid": 0, "n_p_low": 0,
            "n_p_mid_empate": 0, "n_p_mid_rival": 0,
        })
        if clasificacion == "P_MAX":
            conteo_jornada["n_p_max"] += 1
        elif clasificacion == "P_MID":
            conteo_jornada["n_p_mid"] += 1
            if desenlace == "EMPATE" and es_pmid_empate:
                conteo_jornada["n_p_mid_empate"] += 1
            else:
                conteo_jornada["n_p_mid_rival"] += 1
        else:
            conteo_jornada["n_p_low"] += 1

        micro_por_jornada.setdefault(jornada, []).append({
            "id_partido": id_partido,
            "jornada": jornada,
            "local": (fixture or {}).get("local") or str(fila.home_team_slug),
            "visitante": (fixture or {}).get("visitante") or str(fila.away_team_slug),
            "local_escudo_url": (fixture or {}).get("local_escudo_url"),
            "visitante_escudo_url": (fixture or {}).get("visitante_escudo_url"),
            "marcador": f"{goles_local} - {goles_visitante}",
            "goles_local": goles_local,
            "goles_visitante": goles_visitante,
            "resultado_real": desenlace,
            "favorito_designado": favorito,
            "tipo_resultado": tipo_resultado,
            "p_local": round(p_local, 4),
            "p_empate": round(p_empate, 4),
            "p_visitante": round(p_visitante, 4),
            "q_local": q_local,
            "q_empate": q_empate,
            "q_visitante": q_visitante,
            "momios": cuotas,
            "brier_qbe": calcular_brier_multicategorico([registro_qbe]),
            "brier_mercado": calcular_brier_multicategorico([registro_mkt]),
            "acierto": tipo_resultado in ("FAVORITO", "EMPATE"),
            # [LN-QBE-100] Sello de suficiencia S(I) del contrato de captura (fixture legado sin
            # el campo ⇒ `None` ⇒ 1: la ausencia de señal no degrada el partido).
            "suficiencia_S_I": suficiencia_s_i,
            # [LN-QBE-102] Sello de procedencia de la evidencia (badge de la casilla micro).
            "origen_captura": _origen_captura_de_traza(trazas_soberanas.get(id_partido))
            or (fixture or {}).get("origen_captura"),
            # [LN-QBE-127] Sello de procedencia del VECTOR: `CAPTURA` (snapshot) · `SOBERANA`
            # (tabla 3NF) · `AL_VUELO` (resuelto dinámicamente por el motor soberano).
            "origen_p_prima": origen_p_prima,
            # [LN-QBE-100 · REFACTOR-TRIADA-PMAX-PMID-PLOW] Vértices del símplex Δ² sellados por
            # partido (R_(1) ≥ R_(2) ≥ R_(3)) y vértice que consumó el resultado de la cancha.
            "r_max": r_max,
            "r_mid": r_mid,
            "r_low": r_low,
            "clasificacion_triada": clasificacion,
            # Masa individual de cobertura = (P_max + P_mid) · 100 ≡ (1 − P_low) · 100.
            "masa_cobertura_pct": round((p_max_val + p_mid_val) * 100.0, 2),
            "p_low_ruptura_pct": round(p_low_val * 100.0, 2),
            # [LN-QBE-124 / ARCH-1.4.64] Sellos del desempate territorial: desnivel REALMENTE
            # consumido por λ y bandera del rescate que promovió al LOCAL a P_mid.
            "delta_alt_metros": delta_alt_metros,
            "rescate_indiferencia": rescate_indiferencia,
            # [ARCH-1.4.42] Micro-HUD de atribución factorial + DTO forense de 44 variables.
            "atribucion_factorial": _atribucion_factorial_del_partido(
                trazas_soberanas.get(id_partido), fixture, suficiencia_s_i
            ),
        })
        registros_qbe.setdefault(jornada, []).append(registro_qbe)
        registros_mkt.setdefault(jornada, []).append(registro_mkt)
        # [LN-QBE-125] Índice por partido para segmentar la muestra calibrada sin recalcular.
        registros_por_partido[id_partido] = (registro_qbe, registro_mkt)

    jornadas: List[Dict[str, Any]] = []
    for jornada in sorted(micro_por_jornada.keys()):
        partidos = sorted(micro_por_jornada[jornada], key=lambda x: x["id_partido"])
        total = len(partidos)
        favorito_n = sum(1 for p in partidos if p["tipo_resultado"] == "FAVORITO")
        empate_n = sum(1 for p in partidos if p["tipo_resultado"] == "EMPATE")
        underdog_n = sum(1 for p in partidos if p["tipo_resultado"] == "UNDERDOG")

        bs_qbe = calcular_brier_multicategorico(registros_qbe[jornada])
        bs_mkt = calcular_brier_multicategorico(registros_mkt[jornada])

        # [LN-QBE-100 · REFACTOR-TRIADA] Desglose cuantitativo puro de la jornada: porcentaje por
        # vértice (P_max · P_mid · P_low ≡ 100%) y conteos enteros del rescate secundario.
        conteos_triada = triada_por_jornada.get(jornada, {})
        n_p_max = int(conteos_triada.get("n_p_max", 0))
        n_p_mid = int(conteos_triada.get("n_p_mid", 0))
        n_p_low = int(conteos_triada.get("n_p_low", 0))
        n_p_mid_empate = int(conteos_triada.get("n_p_mid_empate", 0))
        n_p_mid_rival = int(conteos_triada.get("n_p_mid_rival", 0))
        pct_p_max = round((n_p_max / total) * 100.0, 2) if total else 0.0
        pct_p_mid = round((n_p_mid / total) * 100.0, 2) if total else 0.0
        pct_p_low = round((n_p_low / total) * 100.0, 2) if total else 0.0

        # [LN-QBE-125] Ceguera DECLARADA de la jornada, derivada del DATO (todos sus partidos con
        # S(I)=0) y no del número de jornada: mañana una J14 ciega se declarará igual.
        es_cold_start = all(p["suficiencia_S_I"] == 0 for p in partidos)

        jornadas.append({
            "jornada": jornada,
            "total_partidos": total,
            # [LN-QBE-100 · REFACTOR-TRIADA] Masa de cobertura = % P_max + % P_mid (= 100% − % P_low).
            "masa_cobertura_pct": round(pct_p_max + pct_p_mid, 2),
            "pct_p_max": pct_p_max,
            "pct_p_mid": pct_p_mid,
            "pct_p_low": pct_p_low,
            "n_p_max": n_p_max,
            "n_p_mid": n_p_mid,
            "n_p_low": n_p_low,
            "n_p_mid_empate": n_p_mid_empate,
            "n_p_mid_rival": n_p_mid_rival,
            "aciertos_cobertura": favorito_n + empate_n,
            "tasa_cobertura_pct": (
                round(((favorito_n + empate_n) / total) * 100.0, 2) if total else 0.0
            ),
            "desglose": {
                "favorito": favorito_n, "empate": empate_n, "underdog": underdog_n,
            },
            "brier_score_qbe": bs_qbe,
            "brier_score_mercado": bs_mkt,
            "alpha_calibracion_pct": _alpha_calibracion_pct(bs_qbe, bs_mkt),
            # [LN-QBE-125 / ARCH-1.4.65] Ceguera declarada de la jornada y etiqueta del Alpha
            # servido: "COLD_START" no es una medición de ventaja, es un prior sin evidencia.
            "es_cold_start": es_cold_start,
            "alpha_etiqueta": "COLD_START" if es_cold_start else "MEDIDO",
            "partidos": partidos,
        })

    todos_qbe = [r for j in sorted(registros_qbe.keys()) for r in registros_qbe[j]]
    todos_mkt = [r for j in sorted(registros_mkt.keys()) for r in registros_mkt[j]]
    partidos_planos = [p for j in jornadas for p in j["partidos"]]

    # [LN-QBE-125 · ARCH-1.4.65] DOBLE AGREGADO DECLARADO con una sola aritmética (cero segunda
    # verdad, `_agregar_resumen_calibracion`):
    #   · `resumen_global`    — universo completo auditado (partidos con P′ sellada).
    #   · `resumen_calibrado` — universo INFORMADO (S(I)=1). El criterio es el DATO, no el número
    #     de jornada: una jornada futura parcialmente ciega no puede contaminar la medición.
    #   · `resumen_temporada` — alias byte-idéntico del global (tres consumidores sellados).
    resumen_global = _agregar_resumen_calibracion(
        partidos_planos,
        todos_qbe,
        todos_mkt,
        [j["jornada"] for j in jornadas],
        partidos_pendientes,
    )
    partidos_calibrados = [p for p in partidos_planos if p["suficiencia_S_I"] == 1]
    resumen_calibrado = _agregar_resumen_calibracion(
        partidos_calibrados,
        [registros_por_partido[p["id_partido"]][0] for p in partidos_calibrados],
        [registros_por_partido[p["id_partido"]][1] for p in partidos_calibrados],
        [j["jornada"] for j in jornadas
         if any(p["suficiencia_S_I"] == 1 for p in j["partidos"])],
        partidos_pendientes,
    )

    if resoluciones_al_vuelo or partidos_pendientes:
        # [LN-QBE-127] Declaración operativa: la ceguera de captura se MIDE (partidos resueltos al
        # vuelo) y el único descarte admitido —el motor no pudo emitir vector— se publica. Ninguno
        # de los dos es mudo, y ninguno viaja como cifra que la vitrina no pueda auditar.
        logger.info(
            "🏳️ [LN-QBE-127] Calibración: %d resueltos AL VUELO · %d pendientes de captura (motor sin vector)",
            resoluciones_al_vuelo,
            partidos_pendientes,
        )

    if marcadores_recuperados:
        # [ARCH-1.4.38 · Enmienda] Recuperación DECLARADA: el marcador consumado de la captura
        # congelada rescata a la jornada cuya fila 3NF quedó rezagada. Cero truncamiento mudo.
        logger.info(
            "🧭 [ARCH-1.4.38 · Enmienda] Calibración: %d marcador(es) recuperados de la captura "
            "congelada (fila 3NF rezagada); cero truncamiento no declarado.",
            marcadores_recuperados,
        )

    return {
        # [ARCH-1.4.38] Alias SELLADO de la temporada (tres consumidores lo leen): byte-idéntico al
        # agregado global, que es lo que siempre significó.
        "resumen_temporada": dict(resumen_global),
        # [LN-QBE-125 · ARCH-1.4.65] Doble agregado declarado: informado (S=1) vs completo.
        "resumen_global": resumen_global,
        "resumen_calibrado": resumen_calibrado,
        "jornadas": jornadas,
    }


@router.get("/backtesting/calibration-report", response_model=CalibrationReportResponse)
def get_backtesting_calibration_report(
    league_id: Optional[int] = Query(
        None, description="ID de liga de la bóveda 3NF (ej. 1 = Liga MX). Sin valor: universo global."
    ),
    db: Session = Depends(get_db_ro)
) -> Dict[str, Any]:
    """
    [ARCH-1.4.38 / LN-QBE-100] Visor de Backtesting — Calibración Factual de Temporada.

    Operación 100% READ-ONLY sobre la bóveda 3NF: cruza los resultados reales consumados
    (`matches`) con las capturas congeladas de P' y cuotas de cierre
    (`fixtures_snapshots.matches_json`) y emite el reporte macro/meso/micro.
    Jamás muta la bóveda ni dispara ingesta: cero red, cero escritura.
    """
    return _construir_reporte_calibracion(db, league_id)


@router.post("/backtesting/simulate")
def post_backtesting_simulate(payload: SimulatePortfolioRequest) -> Dict[str, Any]:
    """
    [LN-QBE-114 / DES-QBE-068] Pasarela REST de Simulación Financiera Retrospectiva.

    Contrato IPO: recibe `SimulatePortfolioRequest` y devuelve **verbatim** el reporte de
    `ejecutar_simulacion_rentabilidad` (`[LN-QBE-107]`), incluido el veto fiduciario
    selectivo de `[LN-QBE-113]` y los parámetros gobernantes de `[LN-QBE-115]` (Γ, Slider de
    Certeza §5.10 y modo de cobertura δ).

    Régimen `[DIRGEN-STRICT]`: esta función es un PASS-THROUGH. Prohibido reimplementar
    PnL, ROI, drawdown o sumatorias de capital: cualquier aritmética nueva aquí sería una
    segunda fuente de verdad. La única transformación permitida es el parseo declarativo
    del rango (`parsear_rango_jornadas`) y la traducción de errores de dominio a HTTP 400.

    El import es diferido para preservar el presupuesto de arranque de The Shield: el
    sandbox arrastra el plano estocástico completo y sólo se materializa en la primera
    invocación real del endpoint.
    """
    from src.observatory.core.simulation_engine import (
        ejecutar_simulacion_rentabilidad,
        parsear_rango_jornadas,
    )

    try:
        jornadas = parsear_rango_jornadas(payload.rango_jornadas or "")
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=400, detail=f"rango_jornadas inválido ('{payload.rango_jornadas}'): {exc}"
        ) from exc

    if not jornadas:
        raise HTTPException(
            status_code=400,
            detail="rango_jornadas no declara ninguna jornada positiva (formato: '1-11', '1,3,5').",
        )

    try:
        return ejecutar_simulacion_rentabilidad(
            bankroll_inicial=payload.bankroll_inicial,
            gateway=_ReadOnlyGateway(),
            jornadas=jornadas,
            modo=payload.modo_interes,
            excluir_estrategias=payload.excluir_estrategias or [],
            # [ARCH-1.4.53 / LN-QBE-115] Pass-through puro de los parámetros gobernantes.
            gamma=payload.gamma_slider,
            target_certeza_pct=payload.target_certeza_pct,
            modo_cobertura=payload.modo_cobertura,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Simulación rechazada: {exc}") from exc


