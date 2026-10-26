# -*- coding: utf-8 -*-
"""
🏆 Q-BE REST CONTROLLER — CENTRO SOBERANO DE INTELIGENCIA DEPORTIVA
[ARCH-1.4.5 / DES-QBE-031] Rutas de Consulta Deportiva Pura (CERO cuotas de casino).
Base de Gobierno: Kybern Framework v12.0
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
from src.storage.gateway import PersistenceGateway
from src.storage.models import FixtureSnapshot, League, SovereignDistribution, CurrentTeamStanding
from src.core.sovereign_pipeline import generar_distribucion_soberana
from src.storage.crest_resolver import obtener_slug_club

router = APIRouter(prefix="/api/sovereign", tags=["Sovereign Intelligence"])


@router.get("/leagues/{league_id}/matches")
def get_sovereign_matches(
    league_id: int,
    jornada: Optional[int] = Query(None, description="Número de jornada opcional")
) -> Dict[str, Any]:
    """
    [ARCH-1.4.5] Retorna los partidos con su distribución estocástica pura + tabla general.
    RESTRICCIÓN ONTOLÓGICA: Cero campos de momios, cuotas o apuestas en el payload.
    """
    gateway = PersistenceGateway()

    with gateway.read_session() as session:
        league = session.query(League).filter(
            (League.fotmob_id == league_id) | (League.id == league_id)
        ).first()
        if not league:
            raise HTTPException(status_code=404, detail=f"Liga con ID {league_id} no encontrada.")

        # ── Estadísticas reales por equipo desde current_team_standings ──
        cts_rows = session.query(CurrentTeamStanding).filter(
            CurrentTeamStanding.league_id == league.id
        ).all()
        stats_map: Dict[str, Dict] = {}
        for row in cts_rows:
            stats_map[row.team_name] = {
                "pj": row.pj,
                "gf": row.gf,
                "gc": row.gc,
                "xg": row.xg,
                "xga": row.xga,
            }

        # ── Tabla general para hidratar el panel izquierdo ──
        standings_out = [
            {
                "pos": row.pos,
                "equipo": row.team_name,
                "escudo_url": f"/static/img/crests/{row.canonical_slug}.png",
                "puntos": row.puntos,
                "pj": row.pj,
                "pg": row.pg,
                "pe": row.pe,
                "pp": row.pp,
                "gf": row.gf,
                "gc": row.gc,
                "dif": row.dif,
                "xg": row.xg,
                "xga": row.xga,
                "xpts": row.xpts,
                "forma": row.forma_reciente.split("-") if row.forma_reciente else [],
                "proximo_rival": row.proximo_rival or "—",
                "proximo_escudo_url": row.proximo_escudo_url or "",
            }
            for row in sorted(cts_rows, key=lambda r: r.pos)
        ]

        # ── Detectar jornadas disponibles para el selector de píldoras ──
        all_snaps = session.query(FixtureSnapshot).filter(
            FixtureSnapshot.league_id == league.id
        ).all()
        jornadas_disponibles = sorted(set(s.matchday for s in all_snaps if s.matchday))

        # ── Snapshot de fixtures ──
        q = session.query(FixtureSnapshot).filter(FixtureSnapshot.league_id == league.id)
        if jornada is not None:
            q = q.filter(FixtureSnapshot.matchday == jornada)
        fix_snap = q.order_by(FixtureSnapshot.updated_at.desc()).first()

        if not fix_snap or not fix_snap.matches_json:
            return {
                "league_id": league_id,
                "league_name": league.name,
                "jornada": jornada or 10,
                "jornadas_disponibles": jornadas_disponibles,
                "standings": standings_out,
                "matches": []
            }

        matches_out = []
        for fx in fix_snap.matches_json:
            mid = fx.get("id_partido", "")

            # Consultar distribución soberana persistida en BD
            dist_db = session.query(SovereignDistribution).filter(
                SovereignDistribution.match_id == mid
            ).first()

            if dist_db:
                p_l = dist_db.p_local
                p_e = dist_db.p_empate
                p_v = dist_db.p_visitante
                lh = dist_db.lambda_home
                la = dist_db.lambda_away
                phi_h = dist_db.phi_lead2_home
            else:
                # [GOVERNANCE-01] Fallback con datos REALES de current_team_standings
                # Eliminado: datos_raw mock con valores clonados 55.7%
                h_stats = stats_map.get(fx.get("local", ""), {})
                a_stats = stats_map.get(fx.get("visitante", ""), {})

                datos_reales = {
                    "home_team_stats": {
                        "pj": h_stats.get("pj", 9),
                        "gf": h_stats.get("gf", 12),
                        "gc": h_stats.get("gc", 10),
                        "xg": h_stats.get("xg", 1.30),
                        "xga": h_stats.get("xga", 1.10),
                    },
                    "away_team_stats": {
                        "pj": a_stats.get("pj", 9),
                        "gf": a_stats.get("gf", 9),
                        "gc": a_stats.get("gc", 12),
                        "xg": a_stats.get("xg", 1.00),
                        "xga": a_stats.get("xga", 1.40),
                    },
                }
                out = generar_distribucion_soberana(mid, datos_reales)
                p_l, p_e, p_v = out.p_local, out.p_empate, out.p_visitante
                lh, la = out.lambda_home, out.lambda_away
                phi_h = out.phi_lead2_home

            # CONTRATO PURO: Cero cuotas, cero momios
            matches_out.append({
                "match_id": mid,
                "local": fx.get("local", ""),
                "visitante": fx.get("visitante", ""),
                "local_escudo_url": f"/static/img/crests/{obtener_slug_club(fx.get('local', ''))}.png",
                "visitante_escudo_url": f"/static/img/crests/{obtener_slug_club(fx.get('visitante', ''))}.png",
                "horario": fx.get("horario", ""),
                "fecha_bloque": fx.get("fecha_bloque", ""),
                "estado": fx.get("estado", "PROGRAMADO"),
                "marcador_actual": fx.get("marcador_actual"),
                "p_local": p_l,
                "p_empate": p_e,
                "p_visitante": p_v,
                "lambda_home": lh,
                "lambda_away": la,
                "phi_lead2_home": phi_h,
                "es_operable": fx.get("es_operable", True)
            })

        return {
            "league_id": league_id,
            "league_name": league.name,
            "jornada": fix_snap.matchday,
            "jornadas_disponibles": jornadas_disponibles,
            "standings": standings_out,
            "matches": matches_out
        }
