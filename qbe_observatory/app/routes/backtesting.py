# -*- coding: utf-8 -*-
"""Rutas de backtesting y calibración del Observatorio (solo lectura).

Extraídas del monolito; la aritmética permanece en qbe_core / observatory.core.
"""

from typing import Any, Dict, List, Optional, Tuple
import logging
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
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


def _detalle_snapshot_ausente() -> str:
    """Mensaje accionable para el 503: dice qué falta y cómo resolverlo."""
    return (
        f"Snapshot de backtesting no disponible: {config.BACKTESTING_SNAPSHOT}. "
        "Materialícelo con `python -m scripts.refresh_snapshot --max-age-minutes 60` "
        "desde qbe_observatory/."
    )


def get_db_ro():
    try:
        motor = _motor_solo_lectura()
    except RuntimeError as exc:
        # La ausencia del snapshot es un estado de servicio, no un fallo interno:
        # 503 accionable, jamás un 500 opaco.
        raise HTTPException(status_code=503, detail=_detalle_snapshot_ausente()) from exc
    sesion = sessionmaker(bind=motor)()
    try:
        yield sesion
    finally:
        sesion.close()
        motor.dispose()


class _ReadOnlyGateway:
    """Puerto mínimo que satisface a `simulation_engine` sin abrir escritura."""

    def __init__(self) -> None:
        try:
            self.engine = _motor_solo_lectura()
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=_detalle_snapshot_ausente()) from exc
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


# ── [P0 #1 / P0 #5] FUENTES DE CUOTA Y VALIDEZ FIDUCIARIA ────────────────────────────────────
# Sellos de procedencia del trío 1X2. El reporte declara, partido por partido, de dónde sale la
# cuota: captura del fixture (J14), histórico FootyStats, o ausencia declarada. Cero imputación.
FUENTE_CUOTAS_FIXTURES = "FIXTURES"
FUENTE_CUOTAS_HISTORICO = "HISTORICAL_MATCHES"
FUENTE_CUOTAS_SIN_EVIDENCIA = "SIN EVIDENCIA"
FUENTE_CUOTAS_JOIN_AMBIGUO = "JOIN_AMBIGUO"

_CUOTA_MINIMA = 1.0          # una cuota ≤ 1.0 no es un precio de mercado válido
_SOBREPRECIO_MIN = 0.9       # Σ 1/o: por debajo no hay mercado (cuotas incoherentes)
_SOBREPRECIO_MAX = 1.2       # Σ 1/o: por encima el margen de la casa es implausible

_CLAVE_INDICE_HISTORICO = "qbe_indice_cuotas_historicas"
_IDENTIDAD_CANONICA: Dict[str, Optional[str]] = {}


def _trio_cuotas_valido(
    local: Any, empate: Any, visitante: Any
) -> Optional[Dict[str, float]]:
    """Valida un trío 1X2 factual: cuotas > 1.0 y Σ(1/o) ∈ [0.9, 1.2].

    Devuelve `None` cuando el trío está incompleto o es incoherente. No repara, no completa y no
    promedia: la ausencia se declara aguas arriba [GOVERNANCE-01].
    """
    try:
        o_local, o_empate, o_visitante = float(local), float(empate), float(visitante)
    except (TypeError, ValueError):
        return None
    if min(o_local, o_empate, o_visitante) <= _CUOTA_MINIMA:
        return None
    sobreprecio = 1.0 / o_local + 1.0 / o_empate + 1.0 / o_visitante
    if not (_SOBREPRECIO_MIN <= sobreprecio <= _SOBREPRECIO_MAX):
        return None
    return {"L": o_local, "E": o_empate, "V": o_visitante}


def _cuotas_1x2_factuales(fx: Dict[str, Any]) -> Dict[str, float]:
    """
    [ARCH-1.4.38 / P0 #1.1] Trío 1X2 factual de la captura congelada del snapshot.

    Decreto del Director (2026-10-14): la captura se lee con FALLBACK DUAL, `cuotas` (ingesta
    explícita) o `momios` (ingesta nativa), con respaldo determinista en `momios_operadores`.
    Un fixture sin trío válido devuelve `{}`: cero cuotas prestadas entre casas [GOVERNANCE-01].

    La referencia al fallback canónico inexistente quedó ELIMINADA (P0 #1.1): el flujo ya no
    puede romperse con un `NameError` ni caer a un `1/3` implícito. La ausencia se declara con
    `{}` y la fuente se resuelve en `_cuotas_1x2_con_fuente` / `cuotas_desde_historico`.
    """
    cuotas_dict = fx.get("cuotas") or fx.get("momios") or {}
    try:
        validas = _trio_cuotas_valido(
            cuotas_dict.get("L"), cuotas_dict.get("E"), cuotas_dict.get("V")
        )
    except AttributeError:
        validas = None
    if validas is not None:
        return validas

    capturas = fx.get("momios_operadores") or {}
    if isinstance(capturas, dict):
        for operador in sorted(capturas.keys()):
            m_data = capturas.get(operador) or {}
            if not isinstance(m_data, dict):
                continue
            validas = _trio_cuotas_valido(m_data.get("L"), m_data.get("E"), m_data.get("V"))
            if validas is not None:
                return validas
    return {}


def _cuotas_1x2_con_fuente(fx: Dict[str, Any]) -> Tuple[Dict[str, float], str]:
    """Trío del fixture + sello de fuente (`FIXTURES` o `SIN EVIDENCIA`)."""
    cuotas = _cuotas_1x2_factuales(fx)
    if cuotas:
        return cuotas, FUENTE_CUOTAS_FIXTURES
    return {}, FUENTE_CUOTAS_SIN_EVIDENCIA


def _fecha_dia(valor: Any) -> Optional[str]:
    """Día ISO (`YYYY-MM-DD`) de un `kickoff_utc`/`fecha_utc` textual o `datetime`."""
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor.date().isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    texto = str(valor).strip()
    if len(texto) < 10:
        return None
    return texto[:10]


def _identidad_canonica(slug: Any) -> Optional[str]:
    """
    Identidad de club para el JOIN histórico, SIN coincidencia difusa.

    Usa el catálogo canónico sellado [LN-QBE-012] en su rama de ALIAS EXPLÍCITO (`_CANONICAL_ALIASES`)
    —jamás SequenceMatcher ni Levenshtein— para reconciliar las dos convenciones de slug del
    corpus (`pachuca` ↔ `club-pachuca`, `guadalajara` ↔ `chivas-guadalajara`, …). Un slug que no
    figura en el catálogo conserva su forma literal normalizada: no se adivina su identidad.
    """
    if slug is None:
        return None
    clave = str(slug).strip()
    if not clave:
        return None
    if clave not in _IDENTIDAD_CANONICA:
        try:
            from src.core.normalization.normalizer import _CANONICAL_ALIASES, _normalize_text

            texto = _normalize_text(clave.replace("-", " "))
            _IDENTIDAD_CANONICA[clave] = _CANONICAL_ALIASES.get(texto) or f"slug:{clave.lower()}"
        except (ImportError, AttributeError):  # pragma: no cover - catálogo ausente ⇒ literal
            _IDENTIDAD_CANONICA[clave] = f"slug:{clave.lower()}"
    return _IDENTIDAD_CANONICA[clave]


def _construir_indice_cuotas_historicas(sesion: Session) -> Dict[str, Any]:
    """
    Índice en memoria (una sola lectura) de `historical_matches` para resolver cuotas.

    `disponible = False` cuando la bóveda no porta la tabla (p. ej. el snapshot J14): el JOIN
    histórico no aplica y cada partido cae a `SIN EVIDENCIA`, sin excepción.
    """
    indice: Dict[str, Any] = {
        "disponible": False,
        "total": 0,
        "validas": 0,
        "invalidas": 0,
        "con_odd_mayor_1": 0,
        "por_fecha": {},
        "por_fecha_canonica": {},
        "filas": {},
        "usados": set(),
    }
    try:
        filas = sesion.execute(
            text(
                "SELECT match_id, fecha_utc, home_team_slug, away_team_slug, "
                "odd_home, odd_draw, odd_away FROM historical_matches"
            )
        ).mappings().all()
    except SQLAlchemyError:
        return indice

    indice["disponible"] = True
    for fila in filas:
        registro = dict(fila)
        dia = _fecha_dia(registro.get("fecha_utc"))
        if dia is None:
            continue
        match_hist = str(registro["match_id"])
        indice["filas"][match_hist] = registro
        indice["por_fecha"].setdefault(
            (str(registro.get("home_team_slug")), str(registro.get("away_team_slug")), dia), []
        ).append(match_hist)
        canonica = (
            _identidad_canonica(registro.get("home_team_slug")),
            _identidad_canonica(registro.get("away_team_slug")),
            dia,
        )
        indice["por_fecha_canonica"].setdefault(canonica, []).append(match_hist)
        if _trio_cuotas_valido(
            registro.get("odd_home"), registro.get("odd_draw"), registro.get("odd_away")
        ) is not None:
            indice["validas"] += 1
        else:
            indice["invalidas"] += 1
        try:
            if min(
                float(registro.get("odd_home")),
                float(registro.get("odd_draw")),
                float(registro.get("odd_away")),
            ) > _CUOTA_MINIMA:
                indice["con_odd_mayor_1"] += 1
        except (TypeError, ValueError):
            pass
        indice["total"] += 1
    return indice


def _resolver_cuota_historica(
    sesion: Session, match_id: str
) -> Tuple[Dict[str, float], str, Dict[str, Any]]:
    """
    Resuelve la cuota de mercado de un partido contra `historical_matches`.

    Reglas (P0 #1.2, tolerancia horaria declarada):
      1. JOIN por (home_team_slug, away_team_slug, date(kickoff_utc)) — identidad literal.
      2. Identidad canónica sellada + mismo día (dos convenciones de slug del corpus).
      3. Identidad canónica + día contiguo (−1/+1) por desfase de zona horaria.
      4. Cualquier empate entre candidatos ⇒ `JOIN_AMBIGUO` (no se adivina).
      5. Trío fuera de rango ⇒ `SIN EVIDENCIA` (cuota incompleta/incoherente).

    Devuelve `(cuotas, fuente, diagnostico)`. Nunca escribe.
    """
    indice = sesion.info.get(_CLAVE_INDICE_HISTORICO)
    if indice is None:
        indice = _construir_indice_cuotas_historicas(sesion)
        sesion.info[_CLAVE_INDICE_HISTORICO] = indice
    if not indice["disponible"]:
        return {}, FUENTE_CUOTAS_SIN_EVIDENCIA, {"motivo": "TABLA_AUSENTE"}

    fila = sesion.execute(
        text(
            "SELECT kickoff_utc, home_team_slug, away_team_slug FROM matches WHERE id = :id"
        ),
        {"id": str(match_id)},
    ).mappings().first()
    if fila is None:
        return {}, FUENTE_CUOTAS_SIN_EVIDENCIA, {"motivo": "PARTIDO_AUSENTE"}

    dia = _fecha_dia(fila["kickoff_utc"])
    if dia is None:
        return {}, FUENTE_CUOTAS_SIN_EVIDENCIA, {"motivo": "KICKOFF_ILEGIBLE"}
    try:
        dia_iso = date.fromisoformat(dia)
    except ValueError:
        return {}, FUENTE_CUOTAS_SIN_EVIDENCIA, {"motivo": "KICKOFF_ILEGIBLE"}
    local_literal = str(fila["home_team_slug"])
    visita_literal = str(fila["away_team_slug"])
    canonica = (_identidad_canonica(local_literal), _identidad_canonica(visita_literal))

    literal = indice["por_fecha"].get((local_literal, visita_literal, dia), [])
    canonico = indice["por_fecha_canonica"].get((canonica[0], canonica[1], dia), [])
    candidatos = list(dict.fromkeys(literal + canonico))
    if not candidatos:
        for desplazamiento in (-1, 1):
            vecino = (dia_iso + timedelta(days=desplazamiento)).isoformat()
            hallados = indice["por_fecha_canonica"].get((canonica[0], canonica[1], vecino), [])
            if hallados:
                candidatos = list(dict.fromkeys(hallados))
                break

    if len(candidatos) > 1:
        return {}, FUENTE_CUOTAS_JOIN_AMBIGUO, {
            "motivo": "MULTIPLES_CANDIDATOS",
            "candidatos": candidatos,
        }
    if not candidatos:
        return {}, FUENTE_CUOTAS_SIN_EVIDENCIA, {"motivo": "SIN_FILA_HISTORICA"}

    match_hist = candidatos[0]
    indice["usados"].add(match_hist)
    registro = indice["filas"][match_hist]
    cuotas = _trio_cuotas_valido(
        registro.get("odd_home"), registro.get("odd_draw"), registro.get("odd_away")
    )
    if cuotas is None:
        return {}, FUENTE_CUOTAS_SIN_EVIDENCIA, {
            "motivo": "CUOTA_INCOMPLETA",
            "match_historico": match_hist,
        }
    return cuotas, FUENTE_CUOTAS_HISTORICO, {
        "motivo": "OK",
        "match_historico": match_hist,
    }


def cuotas_desde_historico(sesion: Session, match_id: str) -> Tuple[Dict[str, float], str]:
    """
    [P0 #1.2] Cuota de mercado desde `historical_matches` para un partido de la bóveda.

    Devuelve `({'L': odd_home, 'E': odd_draw, 'V': odd_away}, "HISTORICAL_MATCHES")` o
    `({}, "SIN EVIDENCIA")` si el partido no está en `historical_matches`, si sus cuotas están
    incompletas/incoherentes o si la bóveda no porta la tabla. Devuelve `({}, "JOIN_AMBIGUO")`
    cuando el JOIN no es unívoco: jamás se adivina la fila.

    Función de PURA LECTURA: no escribe, no imputa y no promedia cuotas.
    """
    cuotas, fuente, _ = _resolver_cuota_historica(sesion, match_id)
    return cuotas, fuente


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
    registros_por_partido: Dict[str, Tuple[Dict[str, Any], Optional[Dict[str, Any]]]] = {}
    # [P0 #1.3 / P0 #5] Procedencia de la cuota de mercado: un contador entero por fuente y la
    # lista declarada de JOINs ambiguos. Cero partido con cuota imputada.
    conteo_fuente_cuotas: Dict[str, int] = {}
    motivos_sin_cuota: Dict[str, int] = {}
    join_ambiguos: List[str] = []

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

        # [P0 #1.3] PRIORIDAD DECLARADA DE LA CUOTA DE MERCADO:
        #   1. `fixtures_snapshots.matches_json.cuotas|momios` válida (J14 / captura).
        #   2. `historical_matches.odd_*` válida (corpus histórico).
        #   3. `{}` + `SIN EVIDENCIA` (jamás 1/3, jamás 0.0, jamás promedio).
        cuotas, fuente_cuotas = ({}, FUENTE_CUOTAS_SIN_EVIDENCIA)
        motivo_sin_cuota = "SIN_FIXTURE"
        if fixture:
            cuotas, fuente_cuotas = _cuotas_1x2_con_fuente(fixture)
        if not cuotas:
            cuotas, fuente_cuotas, diagnostico = _resolver_cuota_historica(session, id_partido)
            motivo_sin_cuota = str(diagnostico.get("motivo") or "SIN_EVIDENCIA")
            if fuente_cuotas == FUENTE_CUOTAS_JOIN_AMBIGUO:
                join_ambiguos.append(id_partido)
        conteo_fuente_cuotas[fuente_cuotas] = conteo_fuente_cuotas.get(fuente_cuotas, 0) + 1
        if fuente_cuotas != FUENTE_CUOTAS_FIXTURES and fuente_cuotas != FUENTE_CUOTAS_HISTORICO:
            motivos_sin_cuota[motivo_sin_cuota] = motivos_sin_cuota.get(motivo_sin_cuota, 0) + 1

        if cuotas:
            q_local, q_empate, q_visitante = desmarcar_cuotas_proporcional(
                float(cuotas["L"]), float(cuotas["E"]), float(cuotas["V"])
            )
        else:
            # Ausencia DECLARADA: el vector de mercado no existe. No se invoca el desmarque (su
            # guarda fiduciaria degradaría a 1/3) y el partido queda fuera del Brier de mercado.
            q_local, q_empate, q_visitante = None, None, None

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
        # El registro de mercado SÓLO existe si hay cuota válida: los partidos sin cuota quedan
        # excluidos del Brier de mercado (P0 #1.3), no puntuados contra un prior imputado.
        registro_mkt: Optional[Dict[str, Any]] = None
        if cuotas:
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
            "fuente_cuotas": fuente_cuotas,
            "brier_qbe": calcular_brier_multicategorico([registro_qbe]),
            "brier_mercado": (
                calcular_brier_multicategorico([registro_mkt])
                if registro_mkt is not None
                else None
            ),
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
        if registro_mkt is not None:
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
        # Brier de mercado sobre las jornadas con al menos una cuota válida; una jornada sin
        # cuota no inventa un vector de mercado (su Brier queda en 0.0 por guarda de vacío).
        bs_mkt = calcular_brier_multicategorico(registros_mkt.get(jornada, []))

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
        [
            registro
            for p in partidos_calibrados
            if (registro := registros_por_partido[p["id_partido"]][1]) is not None
        ],
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

    # [P0 #1.3 / P0 #5] Resumen DECLARADO de la procedencia de cuotas. `n_sin_cuota` es aritmética
    # pura del universo (no un contador aparte): todo partido sin cuota válida queda fuera del
    # Brier de mercado y dentro del Brier del modelo.
    n_con_cuota_fixtures = int(conteo_fuente_cuotas.get(FUENTE_CUOTAS_FIXTURES, 0))
    n_con_cuota_historica = int(conteo_fuente_cuotas.get(FUENTE_CUOTAS_HISTORICO, 0))
    n_sin_cuota = len(partidos_planos) - n_con_cuota_fixtures - n_con_cuota_historica
    indice_historico = session.info.get(_CLAVE_INDICE_HISTORICO) or {}
    resumen_cuotas = {
        "n_con_cuota_fixtures": n_con_cuota_fixtures,
        "n_con_cuota_historica": n_con_cuota_historica,
        "n_sin_cuota": n_sin_cuota,
        "n_join_ambiguo": len(join_ambiguos),
        "join_ambiguos": sorted(join_ambiguos),
        "fuente_cuotas": dict(sorted(conteo_fuente_cuotas.items())),
        "motivos_sin_cuota": dict(sorted(motivos_sin_cuota.items())),
        "n_brier_mercado": len(todos_mkt),
        "historico": {
            "disponible": bool(indice_historico.get("disponible", False)),
            "total_filas": int(indice_historico.get("total", 0)),
            "cuotas_odd_mayor_1": int(indice_historico.get("con_odd_mayor_1", 0)),
            "cuotas_validas": int(indice_historico.get("validas", 0)),
            "cuotas_invalidas": int(indice_historico.get("invalidas", 0)),
            "filas_consumidas": len(indice_historico.get("usados", ())),
            "filas_huerfanas": int(indice_historico.get("total", 0))
            - len(indice_historico.get("usados", ())),
        },
    }

    return {
        # [ARCH-1.4.38] Alias SELLADO de la temporada (tres consumidores lo leen): byte-idéntico al
        # agregado global, que es lo que siempre significó.
        "resumen_temporada": dict(resumen_global),
        # [LN-QBE-125 · ARCH-1.4.65] Doble agregado declarado: informado (S=1) vs completo.
        "resumen_global": resumen_global,
        "resumen_calibrado": resumen_calibrado,
        "cuotas": resumen_cuotas,
        "jornadas": jornadas,
    }


def reporte_calibracion_canonico(
    session: Session, league_id: Optional[int] = None
) -> Dict[str, Any]:
    """Punto público ÚNICO del reporte de calibración sobre la bóveda 3NF.

    Existe para que ningún consumidor —incluido el alias deprecado de
    `app.routes.calibration`— dependa de un símbolo privado ni reimplemente el
    agregado. Una sola fuente de verdad, dos puertas: la canónica y la obsoleta.
    """
    return _construir_reporte_calibracion(session, league_id)


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


