# -*- coding: utf-8 -*-
"""
🏆 Q-BE CD WEB — RESOLVER SEMÁNTICO JIT DE COMPETICIONES Y CLUBES
[LN-QBE-088, LN-QBE-089] & [ARCH-1.4.21] & [ARCH-1.6.20] & [ARCH-1.5.11]
Identificación bajo demanda de ligas y auto-registro transaccional en SQLite 3NF.
Régimen: [DIRGEN-STRICT] — Bloque sellado [VAULT-CORE-088-JIT-RESOLVER]
Firma: SHA256-VAULT-CORE-PROGOL-JIT-RESOLVER-001
"""

import logging
import urllib.parse
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from sqlalchemy.orm import Session

from src.storage.models import League

logger = logging.getLogger("ProgolResolver")

# [ARCH-1.6.20] Endpoint ACTIVO del buscador estructurado de FotMob (erradica el HTTP 404 de SONDEO-03
# del endpoint deprecado `/api/search/searchapi`). Fuente única del plano de ingesta Progol.
URL_FOTMOB_SUGGEST_BASE = "https://www.fotmob.com/api/searchapi/suggest"

# [ARCH-1.5.11] Catálogo Maestro de Jerga y Aliases Globales de Progol
PROGOL_GLOBAL_ALIASES = {
    "VERACRUZ": "Racing de Veracruz",
    "OAXACA": "Chapulineros de Oaxaca",
    "DURANGO": "Alacranes de Durango",
    "ZACATECAS": "Zacatepec",
    "CANCUN": "Cancún FC",
    "TAPATIO": "Tapatío",
    "AGUILAS F": "Club América Femenil",
    "RAYADOS DE MONTERREY": "CF Monterrey Femenil",
    "MILAN F": "AC Milan Femenil",
    "JUVENTUS F": "Juventus Femenil",
    "R SOCIED. B": "Real Sociedad B",
    "E.U.A.": "USA",
    "BOSNIA Y H": "Bosnia and Herzegovina",
    "TRIN Y TOB": "Trinidad and Tobago"
}


def traducir_jerga_global_progol(nombre_crudo: str) -> str:
    """[ARCH-1.5.11] Traduce abreviaturas y motes de Pronósticos a identidades oficiales."""
    limpio = str(nombre_crudo or "").strip()
    if not limpio:
        return ""
    return PROGOL_GLOBAL_ALIASES.get(limpio.upper(), limpio)


def parsear_respuesta_search_fotmob(payload_json: Dict[str, Any], query_str: str) -> Optional[Dict[str, Any]]:
    """[LN-QBE-088] Extrae la liga y el club de mayor relevancia desde la API de búsqueda de FotMob."""
    if not payload_json:
        return None

    # Inspeccionar la sección 'teams' del buscador estructurado
    teams_hits = []
    # La API de FotMob agrupa por 'teams', 'squad', o resultados en lista
    if isinstance(payload_json, dict):
        if "teams" in payload_json and isinstance(payload_json["teams"], list):
            teams_hits = payload_json["teams"]
        elif "squad" in payload_json and isinstance(payload_json["squad"], list):
            teams_hits = payload_json["squad"]
        elif "data" in payload_json and isinstance(payload_json["data"], list):
            teams_hits = payload_json["data"]

    if not teams_hits:
        return None

    top_hit = teams_hits[0]

    # Extraer metadatos de liga y equipo de forma segura
    team_id = top_hit.get("id") or top_hit.get("teamId")
    team_name = top_hit.get("name") or top_hit.get("teamName") or query_str

    # Resolver la competición asociada al club
    league_id = None
    league_name = None

    if "leagueId" in top_hit:
        league_id = top_hit.get("leagueId")
        league_name = top_hit.get("leagueName", "Competición Internacional")
    elif "primaryLeague" in top_hit and isinstance(top_hit["primaryLeague"], dict):
        league_id = top_hit["primaryLeague"].get("id")
        league_name = top_hit["primaryLeague"].get("name")

    if not league_id:
        return None

    # [RULING-5 / VARIANZA V-6 RATIFICADA] Origen del club exigido por [LN-QBE-088].I
    country_val = str(top_hit.get("country") or top_hit.get("ccode") or "Internacional").strip()

    return {
        "fotmob_team_id": int(team_id) if team_id else None,
        "team_name": str(team_name).strip(),
        "fotmob_league_id": int(league_id),
        "league_name": str(league_name or "Torneo Internacional").strip(),
        "country": country_val,
        "query_original": query_str
    }


def registrar_liga_descubierta_si_no_existe(session: Session, datos_liga: Dict[str, Any]) -> League:
    """[ARCH-1.4.21] Auto-registro atómico de competición en SQLite 3NF con salvaguardas NOT NULL.

    [VARIANCE-JIT-01] El PK físico `leagues.id` es INTEGER (rowid alias, PRAGMA table_info
    verificado): asignar un literal textual ("LEAGUE_47") levanta
    `sqlite3.IntegrityError: datatype mismatch`. Por tanto la identidad de la competición
    se delega al autoincremento y la llave canónica de lookup es `fotmob_id` (UNIQUE),
    idéntico al patrón ya gobernado en `seeder.py::seed_initial_data`.
    """
    f_id = int(datos_liga["fotmob_league_id"])
    liga_existente = session.query(League).filter(League.fotmob_id == f_id).first()
    if liga_existente:
        return liga_existente

    ahora = datetime.now(timezone.utc).replace(tzinfo=None)
    l_name = str(datos_liga.get("league_name") or f"Liga {f_id}").strip()
    l_country = str(datos_liga.get("country") or "Internacional").strip()
    l_flag = str(datos_liga.get("flag") or f"flag_{f_id}.png").strip()

    nueva_liga = League(
        name=l_name,
        country=l_country,
        flag=l_flag,
        fotmob_id=f_id,
        caliente_url=None,
        is_active=True,
        created_at=ahora
    )
    # [ARCH-1.4.23 / LN-QBE-091] mu_liga declarada por el llamador; 2.60 como default historico.
    setattr(nueva_liga, "_mu_liga", float(datos_liga.get("mu_liga", 2.60)))
    session.add(nueva_liga)
    session.flush()
    logger.info("🏛️ [JIT DISCOVERY] Nueva competición registrada en 3NF: %s (FotMob ID: %d)", l_name, f_id)
    return nueva_liga
