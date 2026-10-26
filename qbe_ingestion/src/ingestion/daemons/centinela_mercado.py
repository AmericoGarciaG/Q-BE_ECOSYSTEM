# -*- coding: utf-8 -*-
"""
🏆 Q-BE CD WEB — CENTINELA AUTÓNOMO DE MERCADO Y CUOTAS MULTI-OPERADOR (CALIENTE, BETWAY & NOVIBET)
[SDLC-02: Standalone Background Engine — Market & Ledger Edition]
[LN-QBE-007-B, C, D, E] & [ARCH-1.4.7] & [ARCH-1.4.6-F]
Ingesta Fáctica, Normalización, Descuento de Margen, Arbitraje Cross-Market y Consenso Multi-Operador.
Base de Gobierno: Kybern Framework v12.0 / v13.5
"""

import sys
import os
import re
import time
import argparse
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy.orm.attributes import flag_modified
from src.storage.gateway import PersistenceGateway
from src.storage.models import League, FixtureSnapshot, SovereignDistribution
from src.ingestion.caliente_scraper import CalienteMarketScraper
from src.ingestion.betway_scraper import BetwayMarketScraper
from src.ingestion.novibet_scraper import NovibetMarketScraper
from src.ingestion.normalizer import canonicalize_team_name
from src.core.triage import evaluar_viabilidad_cuotas

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("CentinelaMercado")


def calcular_probabilidades_sin_comision(L: float, E: float, V: float) -> Tuple[float, float, float]:
    """
    [LN-QBE-007-C] Descuento de Margen Comercial (Vig-Free De-biasing al Símplex Δ²)
    Calcula probabilidades implícitas normalizadas desprovistas de la comisión de la casa.
    """
    if L <= 1.0 or E <= 1.0 or V <= 1.0:
        return (0.0, 0.0, 0.0)

    pi_l = 1.0 / L
    pi_e = 1.0 / E
    pi_v = 1.0 / V
    S = pi_l + pi_e + pi_v

    if S <= 0.0:
        return (0.0, 0.0, 0.0)

    return (pi_l / S, pi_e / S, pi_v / S)


def evaluar_arbitraje_partido(momios_operadores: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    [LN-QBE-007-D] Detector de Arbitraje Inter-Casas (Cross-Market Surebet)
    Evalúa la combinación de mejores cuotas entre operadores para detectar ineficiencias (+EV).
    """
    best_l = {"momio": 0.0, "operador": None}
    best_e = {"momio": 0.0, "operador": None}
    best_v = {"momio": 0.0, "operador": None}

    for op_name, m in momios_operadores.items():
        if not m:
            continue
        l_val = float(m.get("L", 0.0))
        e_val = float(m.get("E", 0.0))
        v_val = float(m.get("V", 0.0))

        if l_val > best_l["momio"]:
            best_l = {"momio": l_val, "operador": op_name}
        if e_val > best_e["momio"]:
            best_e = {"momio": e_val, "operador": op_name}
        if v_val > best_v["momio"]:
            best_v = {"momio": v_val, "operador": op_name}

    if best_l["momio"] > 1.0 and best_e["momio"] > 1.0 and best_v["momio"] > 1.0:
        indice = (1.0 / best_l["momio"]) + (1.0 / best_e["momio"]) + (1.0 / best_v["momio"])
        existe = indice < 1.0000
        roi_pct = ((1.0 / indice) - 1.0) * 100.0 if existe else 0.0
    else:
        indice = 1.0
        existe = False
        roi_pct = 0.0

    return {
        "existe": existe,
        "indice": round(indice, 4),
        "roi_pct": round(roi_pct, 2),
        "mejor_L": best_l,
        "mejor_E": best_e,
        "mejor_V": best_v
    }


def calcular_consenso_y_deltas(prob_ops: Dict[str, Dict[str, float]], p_qbe: Tuple[float, float, float]) -> Dict[str, Any]:
    """
    [LN-QBE-007-E] Consenso de Mercado y Diferenciales vs. Distribución Soberana
    Promedia las probabilidades justas (sin comisión) y calcula la discrepancia (delta) vs Q-BE.
    """
    valid_ops = [p for p in prob_ops.values() if p and p.get("p_L", 0) > 0]
    if not valid_ops:
        return {
            "p_L_mercado": 0.0,
            "p_E_mercado": 0.0,
            "p_V_mercado": 0.0,
            "delta_L": 0.0,
            "delta_E": 0.0,
            "delta_V": 0.0
        }

    n = len(valid_ops)
    bar_q_l = sum(p["p_L"] for p in valid_ops) / n
    bar_q_e = sum(p["p_E"] for p in valid_ops) / n
    bar_q_v = sum(p["p_V"] for p in valid_ops) / n

    p_qbe_l, p_qbe_e, p_qbe_v = p_qbe

    return {
        "p_L_mercado": round(bar_q_l, 3),
        "p_E_mercado": round(bar_q_e, 3),
        "p_V_mercado": round(bar_q_v, 3),
        "delta_L": round(p_qbe_l - bar_q_l, 3),
        "delta_E": round(p_qbe_e - bar_q_e, 3),
        "delta_V": round(p_qbe_v - bar_q_v, 3)
    }


def extraer_mercado_viva(partidos_slate: List[Dict[str, Any]], operador: str = "todos") -> Dict[str, List[Dict[str, Any]]]:
    """
    Sincroniza la ingesta de cuotas 1X2 desde los operadores especificados
    (caliente, betway, novibet, todos).
    """
    resultados = {}

    if operador in ("caliente", "todos"):
        logger.info(f"Escaneando Caliente.mx para {len(partidos_slate)} partidos del slate...")
        try:
            resultados["caliente"] = CalienteMarketScraper.extraer_cuotas_focalizadas(partidos_slate)
        except Exception as e:
            logger.error(f"Error escaneando Caliente.mx: {e}")
            resultados["caliente"] = []

    if operador in ("betway", "todos"):
        logger.info(f"Escaneando Betway.mx para {len(partidos_slate)} partidos del slate...")
        try:
            resultados["betway"] = BetwayMarketScraper.extraer_cuotas_focalizadas(partidos_slate)
        except Exception as e:
            logger.error(f"Error escaneando Betway.mx: {e}")
            resultados["betway"] = []

    # [ARCH-1.4.6-F] Frente Novibet.mx: sensor Feed-First (intercepción de /spt/feed/). Es el
    # tercer operador del terceto Caliente–Betway–Novibet; su captura entra al mismo mapa
    # `momios_operadores` y por tanto al comparador de arbitraje cross-market.
    if operador in ("novibet", "todos"):
        logger.info(f"Escaneando Novibet.mx para {len(partidos_slate)} partidos...")
        try:
            resultados["novibet"] = NovibetMarketScraper.extraer_cuotas_focalizadas(partidos_slate)
        except Exception as e:
            logger.error(f"Error escaneando Novibet.mx: {e}")
            resultados["novibet"] = []

    return resultados


# ── [ARCH-1.6.15] RESOLUCIÓN DINÁMICA DE LA JORNADA ACTIVA ───────────────────
# [GOVERNANCE-01] Cero jornadas quemadas en el intérprete de comandos: la jornada
# del sensor de mercado emana de la bóveda 3NF, nunca de un valor por defecto.

# [ARCH-1.6.21] VOCABULARIO CANÓNICO DE ESTADO DE PARTIDO (única fuente: la bóveda 3NF).
# `PROGRAMADO` = ventanilla futura abierta; `EN_CURSO` = ventanilla viva. Las variantes
# anglosajonas de sensores externos entran como ALIAS de normalización defensiva: jamás como
# estados nuevos inventados por este daemon ([GOVERNANCE-01]).
ESTADOS_VENTANILLA_ABIERTA: frozenset = frozenset({"PROGRAMADO", "EN_CURSO"})
ALIAS_ESTADO_VENTANILLA_ABIERTA: frozenset = frozenset({"SCHEDULED", "IN_PLAY"})

# [ARCH-1.6.15-B] Etiqueta canónica de la cartelera reprogramada fuera del horizonte de
# ventanilla ($\Delta t > 14$ días, `docs/LOGIC.md:551`): una Fecha Lejana NO abre ventanilla.
ETIQUETA_FECHA_LEJANA = "Fecha Lejana"

# [ARCH-1.6.21] FRONTERA DE COMPETENCIA: la jornada activa del sensor de mercado se resuelve
# EXCLUSIVAMENTE contra la Liga MX (`fotmob_id` = 262). Sin esta frontera, la primera jornada con
# cartelera abierta podía emanar de OTRA liga de la bóveda (contaminación multi-liga), y la
# cartelera leída para esa jornada no sería la de la competición objetivo.
FRONTERA_LIGA_MX_ID = 262


def _estado_abre_ventanilla(partido: Optional[Dict[str, Any]]) -> bool:
    """[ARCH-1.6.21] ¿El estado del partido pertenece al vocabulario canónico de ventanilla?"""
    estado = str((partido or {}).get("estado", "") or "").strip().upper()
    return estado in ESTADOS_VENTANILLA_ABIERTA or estado in ALIAS_ESTADO_VENTANILLA_ABIERTA


def es_cartelera_inmediata(partido: Optional[Dict[str, Any]]) -> bool:
    """[ARCH-1.6.15-B] Partido vivo de ventanilla: estado de apertura y fecha NO lejana."""
    if not _estado_abre_ventanilla(partido):
        return False
    sub_badge = str((partido or {}).get("sub_badge") or "").strip()
    return sub_badge != ETIQUETA_FECHA_LEJANA


def resolver_jornada_activa_dinamica(fixtures_por_jornada: Dict[int, List[Dict[str, Any]]]) -> Optional[int]:
    r"""
    [ARCH-1.6.15-B / ARCH-1.6.21] Resuelve la jornada con cartelera regular abierta inmediata
    (ignora fechas lejanas).

    Precedencia determinista: (1) la primera jornada con $\ge 3$ partidos de ventanilla abierta
    inmediata; (2) la primera jornada con cualquier partido de ventanilla abierta; (3) la última
    jornada registrada. `None` sólo si la bóveda no registra jornada alguna ([GOVERNANCE-01]:
    cero invención de jornadas).
    """
    if not fixtures_por_jornada:
        return None

    jornadas = sorted(int(j) for j in fixtures_por_jornada.keys())

    # 1. Buscar la jornada que tenga una cartelera regular activa inmediata (no lejana)
    for jornada in jornadas:
        partidos = fixtures_por_jornada.get(jornada) or []
        partidos_inmediatos = [p for p in partidos if es_cartelera_inmediata(p)]
        # Si tiene partidos programados en la ventana corriente, es la jornada viva de ventanilla
        if len(partidos_inmediatos) >= 3:
            return jornada

    # 2. Fallback: primera jornada con cartelera de ventanilla abierta
    for jornada in jornadas:
        partidos = fixtures_por_jornada.get(jornada) or []
        if any(_estado_abre_ventanilla(p) for p in partidos):
            return jornada

    return jornadas[-1]


def _pk_liga_de_frontera(session: Any, frontera_id: int) -> int:
    """[ARCH-1.6.21] Traduce la FRONTERA de competencia (FotMob 262) a la PK interna de `leagues`.

    `FixtureSnapshot.league_id` es la FK hacia `leagues.id`, mientras la frontera de competencia se
    declara con el identificador de FotMob. Sin esta traducción la lectura devuelve vacío aunque la
    bóveda registre la temporada entera, y el sensor de mercado aborta creyendo que no hay jornadas.
    El criterio es el MISMO dual ya usado por `actualizar_cuotas_en_sqlite`, el tablero de mercado y
    `src/web/routes/sovereign.py`: `(fotmob_id == frontera) | (id == frontera)`, que tolera ambas
    convenciones canónicas de registro (seeder `src/storage/seeder.py`, JIT `src/ingestion/progol_resolver.py`).
    """
    fila = (
        session.query(League.id)
        .filter((League.fotmob_id == frontera_id) | (League.id == frontera_id))
        .first()
    )
    return int(fila[0]) if fila and fila[0] is not None else int(frontera_id)


def cargar_fixtures_por_jornada(league_id: Optional[int] = FRONTERA_LIGA_MX_ID) -> Dict[int, List[Dict[str, Any]]]:
    """
    [ARCH-1.6.4] Lector puro de la bóveda 3NF: agrupa los fixtures persistidos por
    jornada para alimentar la resolución dinámica [ARCH-1.6.15]. Cero red, cero scrape.

    [ARCH-1.6.21] Por defecto acota a la FRONTERA DE COMPETENCIA (Liga MX 262); `league_id=None`
    es la única vía para una vista multi-liga explícita. La frontera se traduce a la PK interna de
    `leagues` antes de filtrar porque la FK persistida es `leagues.id`, no el `fotmob_id`.
    """
    gateway = PersistenceGateway()
    por_jornada: Dict[int, List[Dict[str, Any]]] = {}

    with gateway.read_session() as session:
        filtro_liga = None if league_id is None else _pk_liga_de_frontera(session, int(league_id))

        query = session.query(FixtureSnapshot.matchday).distinct()
        if filtro_liga is not None:
            query = query.filter(FixtureSnapshot.league_id == filtro_liga)

        jornadas = sorted({int(j[0]) for j in query.all() if j[0] is not None})

        for jornada in jornadas:
            snap_query = session.query(FixtureSnapshot).filter(FixtureSnapshot.matchday == jornada)
            if filtro_liga is not None:
                snap_query = snap_query.filter(FixtureSnapshot.league_id == filtro_liga)
            snap = snap_query.order_by(FixtureSnapshot.updated_at.desc()).first()
            por_jornada[jornada] = list(snap.matches_json) if (snap and snap.matches_json) else []

    return por_jornada


def actualizar_cuotas_en_sqlite(jornada: int, dict_cuotas: Dict[str, List[Dict[str, Any]]], operador_sel: str = "todos") -> List[Dict[str, Any]]:
    gateway = PersistenceGateway()
    ahora = datetime.now(timezone.utc).replace(tzinfo=None)
    ahora_iso = datetime.now(timezone.utc).isoformat()
    partidos_procesados = []

    with gateway.write_transaction() as tx:
        league = tx.query(League).filter((League.fotmob_id == FRONTERA_LIGA_MX_ID) | (League.id == FRONTERA_LIGA_MX_ID)).first()
        if not league:
            raise RuntimeError("Liga MX no encontrada en SQLite.")

        fix_snap = tx.query(FixtureSnapshot).filter(
            FixtureSnapshot.league_id == league.id,
            FixtureSnapshot.matchday == jornada
        ).order_by(FixtureSnapshot.updated_at.desc()).first()

        if not fix_snap or not fix_snap.matches_json:
            raise RuntimeError(f"No existe FixtureSnapshot para la Jornada {jornada}. Ejecuta primero centinela_deportivo.py.")

        matches_actualizados = []

        for fx_orig in fix_snap.matches_json:
            fx = dict(fx_orig)
            loc_can = canonicalize_team_name(fx["local"])
            vis_can = canonicalize_team_name(fx["visitante"])
            mid = fx.get("id_partido", "")

            # Mapa de operadores preservando estado previo si existe
            momios_operadores = dict(fx.get("momios_operadores") or {})

            # [ARCH-1.4.6-F] El bucle es genérico sobre `dict_cuotas`: la captura de Novibet se
            # persiste en `momios_operadores["novibet"]` sin ramas especiales, alimentando de
            # forma automática las probabilidades sin comisión y el detector de arbitraje.
            for op_name, cuotas_list in dict_cuotas.items():
                cuota_match = None
                for c in cuotas_list:
                    c_loc = canonicalize_team_name(c.get("local"))
                    c_vis = canonicalize_team_name(c.get("visitante"))
                    if (c_loc, c_vis) == (loc_can, vis_can):
                        cuota_match = c
                        break

                if cuota_match and cuota_match.get("L") is not None:
                    momios_operadores[op_name] = {
                        "L": float(cuota_match["L"]),
                        "E": float(cuota_match["E"]),
                        "V": float(cuota_match["V"]),
                        "pa": bool(cuota_match.get("pago_anticipado", False if op_name == "betway" else True)),
                        "updated_at": ahora_iso
                    }

            fx["momios_operadores"] = momios_operadores

            # Mantener fx["momios"] con Caliente (o Betway como fallback) para retrocompatibilidad
            momio_def = momios_operadores.get("caliente") or momios_operadores.get("betway") or fx.get("momios")
            if momio_def:
                fx["momios"] = {
                    "L": float(momio_def["L"]),
                    "E": float(momio_def["E"]),
                    "V": float(momio_def["V"]),
                    "pago_anticipado": bool(momio_def.get("pa", True))
                }

            # Probabilidades desprovistas de comisión por operador
            probabilidades_sin_comision = {}
            for op_name, m in momios_operadores.items():
                if m and m.get("L") and m["L"] > 1.0:
                    ql, qe, qv = calcular_probabilidades_sin_comision(m["L"], m["E"], m["V"])
                    probabilidades_sin_comision[op_name] = {
                        "p_L": round(ql, 3),
                        "p_E": round(qe, 3),
                        "p_V": round(qv, 3)
                    }
            fx["probabilidades_sin_comision"] = probabilidades_sin_comision

            # Arbitraje Inter-Casas
            arb_res = evaluar_arbitraje_partido(momios_operadores)
            fx["arbitraje"] = arb_res

            # Consultar probabilidad soberana real
            dist_db = tx.query(SovereignDistribution).filter(SovereignDistribution.match_id == mid).first()
            p_soberana_l = dist_db.p_local if dist_db else 0.45
            p_soberana_e = dist_db.p_empate if dist_db else 0.28
            p_soberana_v = dist_db.p_visitante if dist_db else 0.27

            # Consenso de mercado y deltas vs Q-BE
            consenso_res = calcular_consenso_y_deltas(probabilidades_sin_comision, (p_soberana_l, p_soberana_e, p_soberana_v))
            fx["consenso_mercado"] = consenso_res

            caliente_m = momios_operadores.get("caliente")
            betway_m = momios_operadores.get("betway")
            novibet_m = momios_operadores.get("novibet")

            l_cal = caliente_m["L"] if caliente_m else 0.0
            e_cal = caliente_m["E"] if caliente_m else 0.0
            v_cal = caliente_m["V"] if caliente_m else 0.0

            l_btw = betway_m["L"] if betway_m else 0.0
            e_btw = betway_m["E"] if betway_m else 0.0
            v_btw = betway_m["V"] if betway_m else 0.0

            l_nov = novibet_m["L"] if novibet_m else 0.0
            e_nov = novibet_m["E"] if novibet_m else 0.0
            v_nov = novibet_m["V"] if novibet_m else 0.0

            best_l = arb_res["mejor_L"]["momio"]
            best_e = arb_res["mejor_E"]["momio"]
            best_v = arb_res["mejor_V"]["momio"]

            viable = False
            motivo = "Cuotas no publicadas"
            if best_l > 1.0 and best_e > 1.0 and best_v > 1.0:
                pa_val = caliente_m.get("pa", True) if caliente_m else False
                viable, motivo = evaluar_viabilidad_cuotas(best_l, best_e, best_v, pago_anticipado=pa_val)

            fx["disponible_para_seleccion"] = True
            fx["es_operable"] = True
            fx["es_viable_triaje"] = viable
            fx["motivo_triaje"] = motivo

            partidos_procesados.append({
                "partido": f"{fx['local']} vs {fx['visitante']}",
                "horario": fx.get("horario", ""),
                "caliente": {"L": l_cal, "E": e_cal, "V": v_cal, "pa": caliente_m.get("pa") if caliente_m else False},
                "betway": {"L": l_btw, "E": e_btw, "V": v_btw, "pa": betway_m.get("pa") if betway_m else False},
                "novibet": {"L": l_nov, "E": e_nov, "V": v_nov, "pa": novibet_m.get("pa") if novibet_m else False},
                "best": {"L": best_l, "E": best_e, "V": best_v},
                "consenso": consenso_res,
                "deltas": (consenso_res["delta_L"], consenso_res["delta_E"], consenso_res["delta_V"]),
                "triaje": "APROBADO" if viable else ("DESCARTADO" if best_l > 1.0 else "PENDIENTE"),
                "arbitraje": arb_res
            })

            matches_actualizados.append(fx)

        fix_snap.matches_json = matches_actualizados
        flag_modified(fix_snap, "matches_json")
        fix_snap.updated_at = ahora

    return partidos_procesados


def imprimir_tablero_mercado(partidos: List[Dict[str, Any]], duracion: float, jornada: int, operador_sel: str) -> None:
    # [ARCH-1.4.6-F] El tablero expone el terceto completo (Caliente | Betway | Novibet).
    # El comparador `MEJOR 1X2` incorpora a Novibet de forma automática porque
    # `evaluar_arbitraje_partido` itera sobre todo `momios_operadores`.
    banner = "=" * 184
    subbanner = "-" * 184

    print("\n" + banner)
    print(f"🏆 Q-BE CD WEB — TABLERO DE MERCADO Y TELEMETRÍA MULTI-CASINO (JORNADA {jornada})")
    print(banner)
    print(f"TIEMPO DE ESCANEO: {duracion:.2f}s | OPERADOR: {operador_sel.upper()} | PERSISTENCIA: data/qbe_database.db [WAL Mode]")
    print(subbanner)
    print(
        f" #  {'HORARIO':<11} {'PARTIDO':<28} {'CALIENTE 1X2':<18} {'BETWAY 1X2':<18} "
        f"{'NOVIBET 1X2':<18} {'MEJOR 1X2':<18} {'CONSENSO SIN COMISIÓN':<23} "
        f"{'Q-BE VS MERCADO (DIFF)':<24} {'ARBITRAJE'}"
    )
    print(subbanner)

    for idx, p in enumerate(partidos, 1):
        cal = p["caliente"]
        btw = p["betway"]
        nov = p.get("novibet") or {"L": 0.0, "E": 0.0, "V": 0.0, "pa": False}
        bst = p["best"]
        con = p["consenso"]
        dL, dE, dV = p["deltas"]
        arb = p["arbitraje"]

        c_txt = f"{cal['L']:.2f}/{cal['E']:.2f}/{cal['V']:.2f}" if cal['L'] > 0 else "—"
        b_txt = f"{btw['L']:.2f}/{btw['E']:.2f}/{btw['V']:.2f}" if btw['L'] > 0 else "—"
        n_txt = f"{nov['L']:.2f}/{nov['E']:.2f}/{nov['V']:.2f}" if nov['L'] > 0 else "—"
        m_txt = f"{bst['L']:.2f}/{bst['E']:.2f}/{bst['V']:.2f}" if bst['L'] > 0 else "—"
        con_txt = f"{con['p_L_mercado']:.3f}/{con['p_E_mercado']:.3f}/{con['p_V_mercado']:.3f}" if con['p_L_mercado'] > 0 else "—"
        diff_txt = f"{dL:+.3f}/{dE:+.3f}/{dV:+.3f}" if con['p_L_mercado'] > 0 else "—"

        if arb["existe"]:
            arb_txt = f"⚡ ¡SÍ! (+{arb['roi_pct']:.1f}% ROI)"
        else:
            arb_txt = f"NO ({arb['indice']:.4f})"

        print(
            f" {idx:<2} {p['horario']:<11} {p['partido']:<28} {c_txt:<18} {b_txt:<18} "
            f"{n_txt:<18} {m_txt:<18} {con_txt:<23} {diff_txt:<24} {arb_txt}"
        )

    print(subbanner)
    con_caliente = sum(1 for p in partidos if p["caliente"]["L"] > 1.0)
    con_betway = sum(1 for p in partidos if p["betway"]["L"] > 1.0)
    con_novibet = sum(1 for p in partidos if (p.get("novibet") or {}).get("L", 0.0) > 1.0)
    aprobados = sum(1 for p in partidos if p["triaje"] == "APROBADO")
    arbitrajes = sum(1 for p in partidos if p["arbitraje"]["existe"])

    print(f"INTEGRIDAD: Caliente ({con_caliente}/{len(partidos)}) | Betway ({con_betway}/{len(partidos)}) | Novibet ({con_novibet}/{len(partidos)}) | Triaje Aprobados: {aprobados} | Arbitrajes (+EV): {arbitrajes}")
    print(banner + "\n")


def main():
    parser = argparse.ArgumentParser(description="Centinela de Mercado Autónomo Q-BE Multi-Operador")
    parser.add_argument("--jornada", type=int, default=None, help="Override manual de jornada (default: resolución dinámica [ARCH-1.6.15])")
    parser.add_argument("--operador", choices=["caliente", "betway", "novibet", "todos"], default="todos", help="Operador objetivo (caliente|betway|novibet|todos)")
    parser.add_argument("--loop", type=int, default=0)
    args = parser.parse_args()

    while True:
        t0 = time.perf_counter()

        # [ARCH-1.6.15] Cero jornadas quemadas: el override manual (`--jornada`) tiene
        # precedencia; en su ausencia la jornada activa emana de la bóveda 3NF (la primera
        # jornada que registre partidos en estado PROGRAMADO).
        # [ARCH-1.6.21] La lectura va acotada a la FRONTERA DE COMPETENCIA (Liga MX 262):
        # una jornada homónima de otra liga (p. ej. Argentina J8) NUNCA puede abrir la ventanilla.
        if args.jornada is not None:
            jornada_activa = args.jornada
        else:
            jornada_activa = resolver_jornada_activa_dinamica(
                cargar_fixtures_por_jornada(league_id=FRONTERA_LIGA_MX_ID)
            )

        if jornada_activa is None:
            logger.error("La bóveda 3NF no registra jornadas. Corre primero centinela_deportivo.py.")
            return

        logger.info(f"Iniciando escaneo multi-operador [{args.operador}] para Jornada {jornada_activa}...")

        gateway = PersistenceGateway()
        with gateway.read_session() as session:
            # [ARCH-1.6.21] Slate acotado a la frontera de competencia: el snapshot más reciente
            # DE LA LIGA MX para esa jornada (jamás el de otra liga con el mismo matchday).
            liga_objetivo = session.query(League).filter(
                (League.fotmob_id == FRONTERA_LIGA_MX_ID) | (League.id == FRONTERA_LIGA_MX_ID)
            ).first()

            if not liga_objetivo:
                logger.error(f"Liga MX ({FRONTERA_LIGA_MX_ID}) no encontrada en la bóveda 3NF. Corre primero centinela_deportivo.py.")
                return

            fix_snap = session.query(FixtureSnapshot).filter(
                FixtureSnapshot.league_id == liga_objetivo.id,
                FixtureSnapshot.matchday == jornada_activa
            ).order_by(FixtureSnapshot.updated_at.desc()).first()

        if not fix_snap or not fix_snap.matches_json:
            logger.error(f"No hay partidos en SQLite para Jornada {jornada_activa}. Corre primero centinela_deportivo.py.")
            return

        slate = [{"local": f["local"], "visitante": f["visitante"]} for f in fix_snap.matches_json]
        dict_cuotas = extraer_mercado_viva(slate, operador=args.operador)
        partidos_proc = actualizar_cuotas_en_sqlite(jornada_activa, dict_cuotas, operador_sel=args.operador)

        t_total = time.perf_counter() - t0
        imprimir_tablero_mercado(partidos_proc, t_total, jornada_activa, args.operador)

        if args.loop <= 0:
            break
        time.sleep(args.loop)


if __name__ == "__main__":
    main()
