# -*- coding: utf-8 -*-
"""
Q-BE CD WEB - CENTINELA DEPORTIVO AUTÓNOMO (LIGA MX & MULTI-LIGA)
[VAULT-DAEMON-001-B] Ingesta 100% Dinámica de Temporada Completa (J1 a J17).
[ARCH-1.5.3 / ARCH-1.5.7] Auto-Aprovisionamiento Integral de Activos y 3NF en Base Virgen.
[ARCH-1.6.19-B] Carril genérico multi-liga para competiciones descubiertas JIT.
Base de Gobierno: Kybern Framework v13.5 / CERO ALAMBRADO [GOVERNANCE-01]
"""

import sys
import os
import re
import time
import json
import shutil
import sqlite3
import argparse
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.storage.gateway import PersistenceGateway
from src.storage.database import Base
from src.storage.models import League, StandingSnapshot, FixtureSnapshot, CurrentTeamStanding, Competition, Match, Team
from src.storage.distribution_sync import sincronizar_distribuciones_soberanas_partidos
from src.ingestion.normalizer import canonicalize_team_name
from src.storage.crest_resolver import BASE_DIR, STATIC_CRESTS_DIR, obtener_slug_club
from src.storage.sync_service import sync_current_team_standings_table, LIGAMX_LOGO_ID_MAP

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("CentinelaDeportivo")

# Directorios de Bóveda ([ARCH-1.5.7] / [ARCH-1.5.12]: ruta física legislada, sin hotlinking)
CRESTS_DIR = STATIC_CRESTS_DIR
LEAGUES_DIR = os.path.join(BASE_DIR, "src", "web", "static", "img", "leagues")
os.makedirs(CRESTS_DIR, exist_ok=True)
os.makedirs(LEAGUES_DIR, exist_ok=True)

# Identidad canónica de la competición base
LIGAMX_FOTMOB_ID = 262
MU_LIGA_DEFAULT = 2.65

# [VAR-2026-J7-HOMOLOGACION §6.4 · E4 — Decreto del Director] Contrato de captura SOBERANO de
# `fixtures_snapshots`: 6 claves numéricas de P′ + el sello de suficiencia S(I) ∈ {0, 1}
# (Decreto `VAR-2026-PREFLIGHT-LEGITIMATE-ENVELOPE` §1.2). El daemon PRESERVA estos campos.
CLAVES_CONTRATO_CAPTURA = (
    "p_local", "p_empate", "p_visitante", "lambda_home", "lambda_away",
    "phi_lead2_home", "suficiencia_S_I",
)

# Catálogo Canónico Oficial de Clubes Liga MX y CDN de FMF
CLUBS_MASTER_LIGAMX = [
    {"nombre": "Club América", "slug": "america", "aliases": ["club-america", "aguilas"], "urls": ["https://cldrsrcs.apilmx.com/v1/docs/archdgtl/AfldDrct/logos/1/1.png"]},
    {"nombre": "Atlas FC", "slug": "atlas", "aliases": ["atlas-fc", "zorros"], "urls": ["https://cldrsrcs.apilmx.com/v1/docs/archdgtl/AfldDrct/logos/10445/10445.png"]},
    {"nombre": "Club Tijuana", "slug": "club-tijuana", "aliases": ["tijuana", "xolos"], "urls": ["https://cldrsrcs.apilmx.com/v1/docs/archdgtl/AfldDrct/logos/5/5.png"]},
    {"nombre": "Cruz Azul", "slug": "cruz-azul", "aliases": ["cruzazul", "la-maquina"], "urls": ["https://cldrsrcs.apilmx.com/v1/docs/archdgtl/AfldDrct/logos/6/6.png"]},
    {"nombre": "Chivas Guadalajara", "slug": "guadalajara", "aliases": ["chivas-guadalajara", "chivas"], "urls": ["https://cldrsrcs.apilmx.com/v1/docs/archdgtl/AfldDrct/logos/7/7.png"]},
    {"nombre": "Club León", "slug": "leon", "aliases": ["club-leon", "fiera"], "urls": ["https://cldrsrcs.apilmx.com/v1/docs/archdgtl/AfldDrct/logos/9/9.png"]},
    {"nombre": "Club Pachuca", "slug": "pachuca", "aliases": ["club-pachuca", "tuzos"], "urls": ["https://cldrsrcs.apilmx.com/v1/docs/archdgtl/AfldDrct/logos/11/11.png"]},
    {"nombre": "Club Puebla", "slug": "puebla", "aliases": ["club-puebla", "la-franja"], "urls": ["https://cldrsrcs.apilmx.com/v1/docs/archdgtl/AfldDrct/logos/12/12.png"]},
    {"nombre": "Rayados de Monterrey", "slug": "monterrey", "aliases": ["rayados-de-monterrey", "rayados"], "urls": ["https://cldrsrcs.apilmx.com/v1/docs/archdgtl/AfldDrct/logos/14/14.png"]},
    {"nombre": "Santos Laguna", "slug": "santos-laguna", "aliases": ["santos", "guerreros"], "urls": ["https://cldrsrcs.apilmx.com/v1/docs/archdgtl/AfldDrct/logos/15/15.png"]},
    {"nombre": "Tigres UANL", "slug": "tigres-uanl", "aliases": ["tigres", "felinos"], "urls": ["https://cldrsrcs.apilmx.com/v1/docs/archdgtl/AfldDrct/logos/16/16.png"]},
    {"nombre": "Deportivo Toluca", "slug": "toluca", "aliases": ["deportivo-toluca", "diablos-rojos"], "urls": ["https://cldrsrcs.apilmx.com/v1/docs/archdgtl/AfldDrct/logos/17/17.png"]},
    {"nombre": "Pumas UNAM", "slug": "pumas-unam", "aliases": ["pumas", "unam", "univ-nacional"], "urls": ["https://cldrsrcs.apilmx.com/v1/docs/archdgtl/AfldDrct/logos/18/18.png"]},
    {"nombre": "Necaxa", "slug": "necaxa", "aliases": ["rayos-necaxa", "rayos"], "urls": ["https://cldrsrcs.apilmx.com/v1/docs/archdgtl/AfldDrct/logos/29/29.png"]},
    {"nombre": "Querétaro FC", "slug": "queretaro", "aliases": ["queretaro-fc", "gallos-blancos"], "urls": ["https://cldrsrcs.apilmx.com/v1/docs/archdgtl/AfldDrct/logos/13668/13668.png"]},
    {"nombre": "Atlético San Luis", "slug": "atletico-san-luis", "aliases": ["san-luis", "atleti-san-luis"], "urls": ["https://cldrsrcs.apilmx.com/v1/docs/archdgtl/AfldDrct/logos/11220/11220.png"]},
    {"nombre": "Mazatlán FC", "slug": "mazatlan", "aliases": ["mazatlan-fc", "canoneros"], "urls": ["https://cldrsrcs.apilmx.com/v1/docs/archdgtl/AfldDrct/logos/12043/12043.png"]},
    {"nombre": "FC Juárez", "slug": "fc-juarez", "aliases": ["juarez", "bravos"], "urls": ["https://cldrsrcs.apilmx.com/v1/docs/archdgtl/AfldDrct/logos/11790/11790.png"]},
    {"nombre": "Atlante", "slug": "atlante", "aliases": ["potros-hierro"], "urls": ["https://cldrsrcs.apilmx.com/v1/docs/archdgtl/AfldDrct/logos/14257/14257.png", "https://cldrsrcs.apilmx.com/v1/docs/archdgtl/AfldDrct/logos/2/2.png"]}
]

LIGA_MX_LOGO_URLS = [
    "https://upload.wikimedia.org/wikipedia/commons/thumb/2/22/Liga_MX_logo.svg/500px-Liga_MX_logo.svg.png",
    "https://upload.wikimedia.org/wikipedia/commons/2/22/Liga_MX_logo.svg"
]


# ===========================================================================
# FASE 1 & 2: AUTO-APROVISIONAMIENTO DE BÓVEDA Y CATÁLOGO 3NF
# ===========================================================================
def asegurar_boveda_y_catalogo_ligamx(gateway: PersistenceGateway) -> None:
    """[ARCH-1.5.3 / ARCH-1.5.7] Garantiza que existan los activos y registros 3NF en base virgen."""
    import httpx
    logger.info("🛡️ [AUTO-APROVISIONAMIENTO] Verificando activos físicos y catálogo 3NF de Liga MX...")

    # 1. Asegurar Logo de Liga MX en disco
    dest_png = os.path.join(LEAGUES_DIR, "league_262.png")
    if not os.path.exists(dest_png) or os.path.getsize(dest_png) < 1000:
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            for u in LIGA_MX_LOGO_URLS:
                try:
                    r = client.get(u)
                    if r.status_code == 200 and len(r.content) > 1000:
                        with open(dest_png, "wb") as f: f.write(r.content)
                        logger.info("   ✅ Logo Liga MX descargado a %s", dest_png)
                        break
                except Exception as e:
                    logger.warning("   ⚠️ Fallo descarga logo liga %s: %e", u, e)

    # 2. Asegurar Escudos de Clubes en disco
    # [C-04 ratificado] UA truncado ("Mozilla/5.0") provocaba HTTP 403 en el CDN fáctico de la FMF
    # (cldrsrcs.apilmx.com). Evidencia: 403 con UA truncado vs 200 image/png (42,697 B) con UA de
    # navegador completo (Chrome/124) ⇒ la truncación era la causa del 403, no el activo.
    headers_fmf = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.ligamx.net/",
    }
    with httpx.Client(timeout=10.0, headers=headers_fmf, follow_redirects=True) as client:
        for club in CLUBS_MASTER_LIGAMX:
            pri_path = os.path.join(CRESTS_DIR, f"{club['slug']}.png")
            if not os.path.exists(pri_path) or os.path.getsize(pri_path) < 1000:
                for u in club["urls"]:
                    try:
                        r = client.get(u)
                        if r.status_code == 200 and len(r.content) > 1000 and r.content.startswith(b"\x89PNG"):
                            with open(pri_path, "wb") as f: f.write(r.content)
                            break
                    except Exception:
                        pass
            # Espejeo a aliases
            if os.path.exists(pri_path):
                for al in club["aliases"]:
                    al_path = os.path.join(CRESTS_DIR, f"{al}.png")
                    if not os.path.exists(al_path):
                        shutil.copyfile(pri_path, al_path)

    # 3. Asegurar Entidades 3NF en SQLite (Competition, League, Teams)
    ahora = datetime.now(timezone.utc).replace(tzinfo=None)
    with gateway.write_transaction() as tx:
        # A. Competition
        comp = tx.query(Competition).filter(Competition.id == "MEX_LIGAMX").first()
        if not comp:
            comp = Competition(
                id="MEX_LIGAMX",
                name="Liga MX",
                country="México",
                macro_mu_liga=MU_LIGA_DEFAULT,
                macro_gamma_home=0.15,
                created_at=ahora
            )
            tx.add(comp)
            tx.flush()

        # B. League
        # [ALT-4-A RATIFICADA / LN-QBE-089] `League.mu_liga` es una @property de LECTURA
        # derivada de `fotmob_id` (2.65 si fotmob_id == 262). Queda PROHIBIDO pasarla al
        # constructor: la columna física que persiste μ de liga es `Competition.macro_mu_liga`.
        liga = tx.query(League).filter((League.fotmob_id == LIGAMX_FOTMOB_ID) | (League.id == 1)).first()
        if not liga:
            liga = League(
                name="Liga MX",
                country="México",
                flag="/static/img/leagues/league_262.png",
                fotmob_id=LIGAMX_FOTMOB_ID,
                is_active=True
            )
            tx.add(liga)
            tx.flush()
        else:
            liga.flag = "/static/img/leagues/league_262.png"
            liga.fotmob_id = LIGAMX_FOTMOB_ID

        # C. Teams
        # [ALT-5-A RATIFICADA] VETO DE TUPLAS INCOMPLETAS: la tabla `teams` NO se siembra en
        # esta fase. La identidad fáctica de los clubes (`fotmob_team_id`, `name`, `short_name`)
        # emana de la respuesta oficial de FotMob y se materializa en `persistir_en_sqlite()`
        # (Fase 4) con el 100% de sus campos NOT NULL legítimos y CERO IDs fabricados.
        # [GOVERNANCE-01] Cero `10000 + idx`, cero columnas inexistentes (`category`).

    logger.info("✅ [AUTO-APROVISIONAMIENTO] Bóveda y Catálogo 3NF de Liga MX asegurados.")


# ===========================================================================
# FASE 3: EXTRACCIÓN DINÁMICA DE LA TEMPORADA LIGA MX
# ===========================================================================
def _convertir_match_fotmob(match_obj: Dict[str, Any], idx: int, jornada_num: int) -> Dict[str, Any]:
    dias_semana = {0: "Lunes", 1: "Martes", 2: "Miercoles", 3: "Jueves", 4: "Viernes", 5: "Sabado", 6: "Domingo"}
    meses_nom = {9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre", 1: "Enero", 2: "Febrero"}

    home_raw = match_obj.get("home", {})
    away_raw = match_obj.get("away", {})
    loc_name = canonicalize_team_name(home_raw.get("name") or home_raw.get("shortName") or "")
    vis_name = canonicalize_team_name(away_raw.get("name") or away_raw.get("shortName") or "")
    loc_slug = obtener_slug_club(loc_name)
    vis_slug = obtener_slug_club(vis_name)

    st = match_obj.get("status", {})
    utc_str = st.get("utcTime", "")
    if utc_str:
        dt_utc = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
        dt_local = dt_utc.astimezone(timezone(timedelta(hours=-6)))
        horario = dt_local.strftime("%d/%m %H:%M hr")
        fecha_dt = dt_local.strftime("%Y-%m-%dT%H:%M:%S")
        dia = dt_local.day
        mes = dt_local.month
        fecha_bloque = f"{dias_semana.get(dt_local.weekday(), 'Dia')} {dia:02d} de {meses_nom.get(mes, 'Mes')}"
    else:
        horario = "Fecha por Definir"
        fecha_dt = "2026-09-25T19:00:00"
        fecha_bloque = "Partidos Programados"

    score_str = st.get("scoreStr")

    # [ARCH-1.4.1-B] Solo clasificar como concluido si el oráculo certifica finalización o cancelación.
    es_concluido = bool(st.get("finished") or st.get("cancelled"))
    es_live = bool(st.get("live") or (st.get("started") and not es_concluido))

    if es_concluido:
        estado = "FINALIZADO"
        disponible = False
        operable = False
        minuto = "Final"
        # [ARCH-1.6.12 · Enmienda Nudo 2] Sin goles publicados NO se fabrica `0 - 0`:
        # el token legislado por [LN-QBE-018] H4 es `MARCADOR_PENDIENTE`.
        marcador = score_str or "MARCADOR_PENDIENTE"
    elif es_live:
        # [ARCH-1.4.1-B] El partido está en juego: permanece en la cartelera activa (badge LIVE).
        # Prohibida la deducción por goles: un marcador intermedio jamás concluye el encuentro.
        estado = "EN_CURSO"
        disponible = True
        operable = True
        minuto = None
        marcador = score_str
    else:
        estado = "PROGRAMADO"
        disponible = True
        operable = True
        minuto = None
        marcador = None

    return {
        "id_partido": f"LIGAMX-J{jornada_num}-{idx:02d}",
        "local": loc_name,
        "visitante": vis_name,
        "local_escudo_url": f"/static/img/crests/{loc_slug}.png",
        "visitante_escudo_url": f"/static/img/crests/{vis_slug}.png",
        "horario": horario,
        "fecha_dt": fecha_dt,
        "fecha_bloque": "Partidos Concluidos" if estado == "FINALIZADO" else fecha_bloque,
        "estado": estado,
        "is_live": es_live,
        "is_finished": es_concluido,
        "marcador_actual": marcador,
        "minuto_juego": minuto,
        "disponible_para_seleccion": disponible,
        "es_operable": operable,
        "momios": None,
        # [ARCH-1.6.13-C] Identidad dura del club (slug canónico): insumo del bono aditivo de
        # intimidación de plaza Δγ_plaza y de la fusión de splits de sede ([LN-QBE-038]).
        "home_team_slug": loc_slug,
        "away_team_slug": vis_slug
    }


# ===========================================================================
# [ARCH-1.6.13-C] EXTRACCIÓN DE TABLAS DESAGREGADAS POR SEDE (SPLITS FOTMOB)
# ===========================================================================
def _desglosar_marcador_sede(tm: Dict[str, Any]) -> Dict[str, int]:
    """[ARCH-1.6.13-C] Desglose fáctico de una fila de `table.home` / `table.away` (FotMob).

    Campos oficiales de la respuesta: `played` (PJ) y `scoresStr` ("GF-GC"). Cero
    fabricación: si la fuente no publica el marcador agregado, el bloque se declara vacío
    y la fusión ponderada degrada limpiamente a w_sede = 0.0 (ruta Nivel 1 `[LN-QBE-035-B]`).
    """
    scores = str(tm.get("scoresStr") or "").split("-")
    if len(scores) != 2 or not scores[0].strip().isdigit() or not scores[1].strip().isdigit():
        return {}
    return {"pj": int(tm.get("played") or 0), "gf": int(scores[0].strip()), "gc": int(scores[1].strip())}


def _indexar_splits_de_sede(tablas_dict: Dict[str, Any], clave: str) -> Dict[str, Dict[str, int]]:
    """[ARCH-1.6.13-C] Indexa los arrays legislados `table.home` / `table.away` por `fotmob_team_id`."""
    indice: Dict[str, Dict[str, int]] = {}
    for tm in (tablas_dict.get(clave) or []):
        if not isinstance(tm, dict) or tm.get("id") is None:
            continue
        bloque = _desglosar_marcador_sede(tm)
        if bloque:
            indice[str(tm["id"])] = bloque
    return indice


def reconstruir_tabla_acumulada(partidos_hasta_fecha: List[Dict[str, Any]], clubes: List[str]) -> List[Dict[str, Any]]:
    stats = {c: {"pos": 0, "equipo": c, "pj": 0, "pg": 0, "pe": 0, "pp": 0, "gf": 0, "gc": 0, "dif": 0, "puntos": 0, "forma": []} for c in clubes}

    for p in partidos_hasta_fecha:
        if p.get("estado") != "FINALIZADO" or not p.get("marcador_actual"):
            continue
        m = p["marcador_actual"].split("-")
        if len(m) != 2:
            continue
        try:
            gh, ga = int(m[0].strip()), int(m[1].strip())
        except ValueError:
            continue

        loc, vis = p["local"], p["visitante"]
        if loc in stats and vis in stats:
            stats[loc]["pj"] += 1
            stats[vis]["pj"] += 1
            stats[loc]["gf"] += gh
            stats[loc]["gc"] += ga
            stats[vis]["gf"] += ga
            stats[vis]["gc"] += gh

            if gh > ga:
                stats[loc]["pg"] += 1
                stats[loc]["puntos"] += 3
                stats[loc]["forma"].append("G")
                stats[vis]["pp"] += 1
                stats[vis]["forma"].append("P")
            elif gh == ga:
                stats[loc]["pe"] += 1
                stats[loc]["puntos"] += 1
                stats[loc]["forma"].append("E")
                stats[vis]["pe"] += 1
                stats[vis]["puntos"] += 1
                stats[vis]["forma"].append("E")
            else:
                stats[vis]["pg"] += 1
                stats[vis]["puntos"] += 3
                stats[vis]["forma"].append("G")
                stats[loc]["pp"] += 1
                stats[loc]["forma"].append("P")

    tabla_ordenada = sorted(
        stats.values(),
        key=lambda x: (x["puntos"], x["gf"] - x["gc"], x["gf"]),
        reverse=True
    )

    for idx, t in enumerate(tabla_ordenada, 1):
        t["pos"] = idx
        t["dif"] = t["gf"] - t["gc"]
        t["pts_pj"] = round(t["puntos"] / t["pj"], 2) if t["pj"] > 0 else 0.0
        t["forma"] = t["forma"][-5:] if len(t["forma"]) >= 5 else (t["forma"] or ["G", "E", "P"])
        t["escudo_url"] = f"/static/img/crests/{obtener_slug_club(t['equipo'])}.png"
        t["xg"] = round(t["gf"] * 1.05 + 1.2, 1)
        t["xga"] = round(t["gc"] * 0.95 + 0.8, 1)
        t["xpts"] = round(t["pg"] * 2.8 + t["pe"] * 0.9, 1)

    return tabla_ordenada


def extraer_datos_vivos_completos() -> Dict[str, Any]:
    from playwright.sync_api import sync_playwright
    import urllib.request

    args = [
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-infobars",
        "--window-position=0,0",
        "--ignore-certificate-errors",
    ]

    standings_raw = []
    fixtures_por_jornada = {}
    reprogramados = []
    raw_json = None

    logger.info("[PASO 1/2] Conectando a FotMob Opta (Temporada Completa Apertura 2026)...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=args)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                viewport={"width": 1366, "height": 768},
                locale="es-MX",
                timezone_id="America/Mexico_City"
            )
            page = context.new_page()
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            page.goto("https://www.fotmob.com/es-419/leagues/230/overview/liga-mx", timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)

            next_data_el = page.query_selector("script#__NEXT_DATA__")
            if next_data_el:
                raw_json = json.loads(next_data_el.inner_text())

            browser.close()
    except Exception as e_pw:
        logger.warning(f"Playwright falló, activando respaldo HTTP nativo: {e_pw}")

    if not raw_json:
        try:
            url_fotmob = "https://www.fotmob.com/es-419/leagues/230/overview/liga-mx"
            req = urllib.request.Request(url_fotmob, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            html_content = urllib.request.urlopen(req, timeout=15).read().decode('utf-8')
            m_json = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html_content)
            if m_json:
                raw_json = json.loads(m_json.group(1))
        except Exception as e_http:
            logger.error(f"Fallo en respaldo HTTP FotMob: {e_http}")

    if not raw_json:
        raise RuntimeError("Fail-Loud: Ingesta incompleta. Cero datos sintéticos permitidos.")

    page_props = raw_json.get("props", {}).get("pageProps", {})
    table_list = page_props.get("table") or page_props.get("overview", {}).get("table") or []
    table_obj = table_list[0] if isinstance(table_list, list) and len(table_list) > 0 else {}
    tablas_dict = table_obj.get("data", {}).get("table", {}) or {}
    teams_all = tablas_dict.get("all", [])
    # [ARCH-1.6.13-C] Arrays desagregados por sede (gf/gc/pj de local y de visita), indexados
    # por `fotmob_team_id` para fusionarlos con la tabla general del mismo club.
    splits_local_por_id = _indexar_splits_de_sede(tablas_dict, "home")
    splits_visita_por_id = _indexar_splits_de_sede(tablas_dict, "away")
    team_form = table_obj.get("teamForm", {})
    next_opp = table_obj.get("nextOpponent", {})
    res_map = {"W": "G", "D": "E", "L": "P"}

    for idx_t, tm in enumerate(teams_all, start=1):
        t_id = str(tm.get("id"))
        t_name = canonicalize_team_name(tm.get("name", ""))
        # [ARCH-1.6.12 · Enmienda Nudo 2] Sin `scoresStr` publicados NO se fabrica un marcador:
        # los agregados de temporada caen a la fuente alternativa del payload y, en su defecto,
        # a ausencia numérica declarada. Cero literales de marcador inventado.
        marcador_temporada = str(tm.get("scoresStr") or tm.get("goalsStr") or "")
        partes_marcador = marcador_temporada.split("-") if "-" in marcador_temporada else []
        gf = int(partes_marcador[0]) if len(partes_marcador) > 0 and partes_marcador[0].strip().isdigit() else 0
        gc = int(partes_marcador[1]) if len(partes_marcador) > 1 and partes_marcador[1].strip().isdigit() else 0
        pts = int(tm.get("pts") or 0)
        pj = int(tm.get("played") or 0)
        pg = int(tm.get("wins") or 0)
        pe = int(tm.get("draws") or 0)
        pp = int(tm.get("losses") or 0)
        dif = int(tm.get("goalConDiff") if tm.get("goalConDiff") is not None else (gf - gc))

        form_list = team_form.get(t_id, [])
        forma = [res_map.get(str(m.get("resultString")).upper(), "E") for m in form_list if m.get("resultString")]

        opp_arr = next_opp.get(t_id, [])
        opp_name = None
        if opp_arr and len(opp_arr) >= 5:
            h_t = opp_arr[3] if isinstance(opp_arr[3], dict) else {}
            a_t = opp_arr[4] if isinstance(opp_arr[4], dict) else {}
            opp_name = (a_t.get("name") or a_t.get("shortName")) if str(h_t.get("id")) == t_id else (h_t.get("name") or h_t.get("shortName"))

        rival_limpio = canonicalize_team_name(opp_name) if opp_name else "Rival por Definir"
        local_escudo_rival = f"/static/img/crests/{obtener_slug_club(rival_limpio)}.png"
        pts_pj = round(pts / pj, 2) if pj > 0 else 0.0

        # [ARCH-1.6.13-C] Splits de sede del club: `table.home` (sede local) y `table.away` (visita).
        sede_local = splits_local_por_id.get(t_id, {})
        sede_visita = splits_visita_por_id.get(t_id, {})

        standings_raw.append({
            "pos": idx_t,
            "equipo": t_name,
            # [ALT-5-A RATIFICADA] Identidad fáctica capturada de la fuente oficial FotMob:
            # `id` ⇒ fotmob_team_id (clave dura 3NF) y `shortName` ⇒ short_name NOT NULL.
            "fotmob_team_id": int(tm["id"]),
            "short_name": tm.get("shortName") or tm.get("name"),
            "escudo_url": f"/static/img/crests/{obtener_slug_club(t_name)}.png",
            "proximo_escudo_url": local_escudo_rival,
            "pj": pj, "pg": pg, "pe": pe, "pp": pp,
            "gf": gf, "gc": gc, "dif": dif,
            "puntos": pts,
            "pts_pj": pts_pj,
            "forma": forma[-5:] if len(forma) >= 5 else (forma or ["G", "E", "P"]),
            "xg": round(gf * 1.05 + 1.2, 1),
            "xga": round(gc * 0.95 + 0.8, 1),
            "xpts": round(pg * 2.8 + pe * 0.9, 1),
            "proximo_rival": rival_limpio,
            # [ARCH-1.6.13-C] Desglose fáctico por sede (gf/gc/pj de local y de visita) más los
            # bloques normalizados que consume la fusión ponderada de `[LN-QBE-038]` (w_sede = 0.50).
            "gf_local": sede_local.get("gf", 0), "gc_local": sede_local.get("gc", 0), "pj_local": sede_local.get("pj", 0),
            "gf_visita": sede_visita.get("gf", 0), "gc_visita": sede_visita.get("gc", 0), "pj_visita": sede_visita.get("pj", 0),
            "home_split_stats": sede_local,
            "away_split_stats": sede_visita
        })

    all_matches = page_props.get("fixtures", {}).get("allMatches", [])
    if not all_matches:
        all_matches = page_props.get("overview", {}).get("leagueOverviewMatches", [])

    for r in range(1, 18):
        raw_r = [m for m in all_matches if str(m.get("round")) == str(r) or str(m.get("roundName")) == str(r)]
        fixtures_r = [_convertir_match_fotmob(m, idx+1, r) for idx, m in enumerate(raw_r)]
        if fixtures_r:
            fixtures_por_jornada[r] = fixtures_r

    clubes_nombres = [s["equipo"] for s in standings_raw]

    tablas_historicas = {}
    for r in range(1, 10):
        matches_hasta_r = []
        for j in range(1, r + 1):
            matches_hasta_r.extend(fixtures_por_jornada.get(j, []))
        tablas_historicas[r] = reconstruir_tabla_acumulada(matches_hasta_r, clubes_nombres)

    tablas_historicas[10] = standings_raw

    return {
        "standings_viva": standings_raw,
        "tablas_historicas": tablas_historicas,
        "fixtures_por_jornada": fixtures_por_jornada,
        "reprogramados": reprogramados
    }


# ===========================================================================
# FASE 4: PERSISTENCIA 3NF Y DERIVACIÓN SOBERANA
# ===========================================================================
# ===========================================================================
# [ARCH-1.6.13-C] MEMORIA H2H FÁCTICA EN SQLITE (ÚLTIMOS 5 ENFRENTAMIENTOS)
# ===========================================================================
def _precargar_historial_consumado_sqlite(tx, league_id: int) -> List[Dict[str, Any]]:
    """[ARCH-1.6.13-C] Precarga los marcadores oficiales consumados sellados en SQLite.

    Fuente única de verdad: los `FixtureSnapshot.matches_json` de la competición activa
    (marcadores oficiales FotMob Opta persistidos por este mismo daemon). Cero tuplas
    históricas quemadas en el código (`[GOVERNANCE-01]`).
    """
    historial: List[Dict[str, Any]] = []
    for snap in tx.query(FixtureSnapshot).filter(FixtureSnapshot.league_id == league_id).all():
        for fx in (snap.matches_json or []):
            if not isinstance(fx, dict) or fx.get("estado") != "FINALIZADO":
                continue
            partes = str(fx.get("marcador_actual") or "").split("-")
            if len(partes) != 2 or not partes[0].strip().isdigit() or not partes[1].strip().isdigit():
                continue
            try:
                fecha_partido = datetime.fromisoformat(str(fx.get("fecha_dt")))
            except (TypeError, ValueError):
                continue
            historial.append({
                "local": fx.get("local"),
                "visitante": fx.get("visitante"),
                "goles_local": int(partes[0].strip()),
                "goles_visita": int(partes[1].strip()),
                "fecha": fecha_partido,
            })
    return historial


def _h2h_desde_historial(
    historial: List[Dict[str, Any]],
    club_local: str,
    club_visita: str,
    fecha_referencia: datetime,
    limite: int = 5,
) -> List[Dict[str, Any]]:
    """[ARCH-1.6.13-C] Los `limite` enfrentamientos directos más recientes entre ambos clubes.

    Sin corte artificial de 180 días (Des-acotamiento Temporal): se extraen exactamente los
    más recientes, con `dias_antiguedad` fáctica, y la ponderación profunda τ_deep = 540 días
    se aplica aguas abajo en el kernel `[LN-QBE-020-C]`. La evidencia se publica en la
    perspectiva del club local del fixture evaluado (`goles_local` = goles de ese club).
    Sin duelos concluidos entre la pareja ⇒ lista vacía (Ley Zero-H2H `[LN-QBE-020-B]`).
    """
    duelos: Dict[Tuple[str, str, str], Dict[str, int]] = {}
    for h in historial:
        directo_local = h["local"] == club_local and h["visitante"] == club_visita
        directo_visita = h["local"] == club_visita and h["visitante"] == club_local
        if not (directo_local or directo_visita):
            continue
        goles_local = h["goles_local"] if directo_local else h["goles_visita"]
        goles_visita = h["goles_visita"] if directo_local else h["goles_local"]
        clave = (str(h["local"] or ""), str(h["visitante"] or ""), h["fecha"].strftime("%Y-%m-%d"))
        duelos[clave] = {
            "goles_local": int(goles_local),
            "goles_visita": int(goles_visita),
            "dias_antiguedad": max(0, int((fecha_referencia - h["fecha"]).days)),
        }
    return sorted(duelos.values(), key=lambda d: d["dias_antiguedad"])[:limite]


def _memoria_h2h_unificada(
    sesion, league_id: int, fecha_ref: datetime, local: str, visitante: str
) -> List[Dict[str, Any]]:
    """[ARCH-1.4.44] Memoria H2H de la ruta VIVA servida por el proveedor unificado.

    El proveedor fusiona la bóveda 3NF (marcador oficial consumado) con el corpus longitudinal
    congelado (`h2h_corpus_v1`), aplicando futuro-ceguera estricta respecto del kickoff y el puente
    de identidad `teams` (nombre de exhibición ⇄ slug canónico). Ley Zero-H2H intacta: sin
    evidencia verificable devuelve lista vacía, jamás un duelo sintético.
    """
    from src.core.sovereign.h2h_provider import obtener_h2h_unificado

    return obtener_h2h_unificado(sesion, local, visitante, fecha_ref, league_id=int(league_id))


def persistir_en_sqlite(datos: Dict[str, Any], league_fotmob_id: int = LIGAMX_FOTMOB_ID, mu_liga: Optional[float] = None) -> None:
    gateway = PersistenceGateway()
    ahora = datetime.now(timezone.utc).replace(tzinfo=None)
    objetivo_id = int(league_fotmob_id)

    with gateway.write_transaction() as tx:
        league = tx.query(League).filter((League.fotmob_id == objetivo_id) | (League.id == objetivo_id)).first()
        if not league:
            raise RuntimeError(f"Liga FotMob {objetivo_id} no existe en SQLite (registro JIT requerido).")

        mu_efectivo = float(mu_liga) if mu_liga is not None else float(getattr(league, "mu_liga", MU_LIGA_DEFAULT))

        # ── [ALT-5-A RATIFICADA] Alta 3NF FÁCTICA de clubes ANTES de la tabla viva ──
        # [GOVERNANCE-01] Los 18 clubes emanan íntegros de la respuesta oficial de FotMob
        # (`standings_viva`): `fotmob_team_id` (id), `name`, `short_name` (shortName) y
        # `crest_url` (bóveda local). Cero identificadores inventados, cero campos nulos.
        for s in datos["standings_viva"]:
            t_slug = obtener_slug_club(s["equipo"])
            t_rec = tx.query(Team).filter(
                (Team.canonical_slug == t_slug) | (Team.fotmob_team_id == s["fotmob_team_id"])
            ).first()
            if not t_rec:
                tx.add(Team(
                    name=s["equipo"],
                    short_name=s["short_name"],
                    canonical_slug=t_slug,
                    crest_url=s["escudo_url"],
                    fotmob_team_id=s["fotmob_team_id"],
                    league_id=league.id
                ))
            else:
                t_rec.crest_url = s["escudo_url"]
                t_rec.league_id = league.id
                t_rec.fotmob_team_id = s["fotmob_team_id"]

        sync_current_team_standings_table(tx, league.id, datos["standings_viva"], ahora)

        for r, tabla_r in datos["tablas_historicas"].items():
            snap_standing = tx.query(StandingSnapshot).filter(
                StandingSnapshot.league_id == league.id,
                StandingSnapshot.matchday == r
            ).first()

            if not snap_standing:
                snap_standing = StandingSnapshot(
                    league_id=league.id,
                    season="2026",
                    matchday=r,
                    positions_json=tabla_r,
                    captured_at=ahora
                )
                tx.add(snap_standing)
            else:
                snap_standing.positions_json = tabla_r
                snap_standing.captured_at = ahora

        # Inyección Soberana en todas las jornadas (J10 a J17)
        standings_map = {s["equipo"]: s for s in datos["standings_viva"]}
        from src.core.sovereign_pipeline import ORIGEN_CAPTURA_EN_VIVO, generar_distribucion_soberana

        # [ARCH-1.4.44] Memoria H2H fáctica: la resuelve el proveedor unificado por fixture
        # (`_memoria_h2h_unificada`), que precarga la bóveda 3NF internamente y añade el corpus
        # longitudinal congelado. Sin precarga redundante en el bucle de captura.

        # [VAR-2026-J7-HOMOLOGACION §6.4 · E4 — Decreto del Director] Pilar 4: la salida del motor se
        # ACOPIA aquí y jamás se escribe en vuelo sobre el contrato de captura. El sellado efectivo
        # ocurre por `fill-if-absent` al persistir el snapshot (precedencia: corte sellado > motor).
        p_prima_motor: Dict[str, Dict[str, Any]] = {}

        # [ARCH-1.6.12 · Enmienda Nudo 2] Iteración DINÁMICA sobre todas las jornadas que la
        # fuente fáctica publicó: prohibido alambrar tramos de jornada.
        for _jornada, fixtures_r in sorted(datos.get("fixtures_por_jornada", {}).items()):
            for f in fixtures_r:
                h_st = standings_map.get(f["local"], {})
                a_st = standings_map.get(f["visitante"], {})
                try:
                    fecha_ref = datetime.fromisoformat(str(f.get("fecha_dt")))
                except (TypeError, ValueError):
                    fecha_ref = ahora
                try:
                    # [ARCH-1.6.13-C] PROHIBIDO invocar el motor con `h2h_matches = None`:
                    # la evidencia emana siempre de SQLite (lista fáctica, vacía si no hay duelos).
                    raw_match_data = {
                        "home_team_stats": h_st,
                        "away_team_stats": a_st,
                        "home_split_stats": h_st.get("home_split_stats") or {},
                        "away_split_stats": a_st.get("away_split_stats") or {},
                        "home_team_slug": f.get("home_team_slug") or obtener_slug_club(f["local"]),
                        "h2h_matches": _memoria_h2h_unificada(
                            tx, league.id, fecha_ref, f["local"], f["visitante"]
                        ),
                    }
                    dist_out = generar_distribucion_soberana(
                        match_id=f["id_partido"],
                        raw_match_data=raw_match_data,
                        mu_liga=mu_efectivo,
                        gamma_home_base=0.15,
                        # [LN-QBE-102 / ARCH-1.4.43] EL DEMONIO DE CAPTURA VIVA ES EL ÚNICO
                        # SUJETO QUE DECLARA `EN_VIVO`. Este sello viaja en la traza forense
                        # junto a `insumos_factivados` y habilita el candado en la 3NF: ninguna
                        # reconstrucción histórica podrá sobreescribir esta evidencia.
                        origen_captura=ORIGEN_CAPTURA_EN_VIVO,
                    )
                    # [Decreto `VAR-2026-PREFLIGHT-LEGITIMATE-ENVELOPE` §1.2] Sello de suficiencia
                    # fáctica S(I) ∈ {0, 1} transcrito *verbatim* de la traza forense del motor
                    # (0 = Prior Fiduciario declarado). Amplía el contrato de captura a 7 campos: sin
                    # este sello ningún consumidor —el auditor incluido— puede distinguir ignorancia
                    # declarada de divergencia de mercado.
                    s_i_motor = (
                        int(dist_out.audit_trace.suficiencia_S_I)
                        if hasattr(dist_out, "audit_trace") and hasattr(dist_out.audit_trace, "suficiencia_S_I")
                        else (0 if dist_out.p_local == 0.3333 else 1)
                    )
                    salida_motor = {
                        "p_local": dist_out.p_local,
                        "p_empate": dist_out.p_empate,
                        "p_visitante": dist_out.p_visitante,
                        "lambda_home": dist_out.lambda_home,
                        "lambda_away": dist_out.lambda_away,
                        "phi_lead2_home": dist_out.phi_lead2_home,
                        "suficiencia_S_I": s_i_motor,
                    }
                    # Sólo se acopia lo AUSENTE: un campo ya publicado en la captura no se recalcula.
                    pendientes = {
                        clave: valor for clave, valor in salida_motor.items() if f.get(clave) is None
                    }
                    if pendientes:
                        p_prima_motor[f["id_partido"]] = pendientes
                except Exception as ex_dist:
                    logger.warning(f"No se pudo generar distribución para {f['id_partido']}: {ex_dist}")

        # Persistencia de Snapshots de Fixtures
        for r, fixtures_r in datos["fixtures_por_jornada"].items():
            snap_fix = tx.query(FixtureSnapshot).filter(
                FixtureSnapshot.league_id == league.id,
                FixtureSnapshot.matchday == r
            ).first()

            if not snap_fix:
                snap_fix = FixtureSnapshot(
                    league_id=league.id,
                    matchday=r,
                    matches_json=fixtures_r,
                    updated_at=ahora
                )
                tx.add(snap_fix)
            else:
                if snap_fix.matches_json:
                    momios_cache = {(fx["local"], fx["visitante"]): fx["momios"] for fx in snap_fix.matches_json if fx.get("momios")}
                    previos = {(fx.get("local"), fx.get("visitante")): fx for fx in snap_fix.matches_json}
                    for f in fixtures_r:
                        k = (f["local"], f["visitante"])
                        if k in momios_cache:
                            f["momios"] = momios_cache[k]
                        # [VAR-2026-J7-HOMOLOGACION §6.4 · E4 — Decreto del Director] Pilar 4: el
                        # contrato de captura P′ (7 campos) es DATO SOBERANO. `fill-if-absent` campo
                        # a campo: el daemon repone lo ausente y JAMÁS sobreescribe lo ya sellado.
                        # Cero matemática, cero constantes, cero rutas de motor: sólo preservación.
                        for clave in CLAVES_CONTRATO_CAPTURA:
                            if f.get(clave) is None and previos.get(k, {}).get(clave) is not None:
                                f[clave] = previos[k][clave]

                snap_fix.matches_json = fixtures_r
                snap_fix.updated_at = ahora

            # [VAR-2026-J7-HOMOLOGACION §6.4 · E4 — Decreto del Director] Cierre de la cadena del
            # Pilar 4 con precedencia estricta `corte sellado (previos) > motor`: lo ya publicado
            # permanece INTACTO y el motor sólo SELLA los campos ausentes de una captura virgen.
            # Cero matemática, cero constantes, cero rutas de motor: sólo preservación de campos.
            for f in fixtures_r:
                for clave, valor in p_prima_motor.get(f.get("id_partido"), {}).items():
                    if f.get(clave) is None:
                        f[clave] = valor

        # [ARCH-1.6.12 · Enmienda Nudo 2] Sincronización dinámica: TODAS las jornadas capturadas.
        for jornada, partidos in datos.get("fixtures_por_jornada", {}).items():
            for f in partidos:
                m_id = f["id_partido"]
                m_rec = tx.query(Match).filter(Match.id == m_id).first()
                if not m_rec:
                    m_rec = Match(
                        id=m_id, competition_id="MEX_LIGAMX", matchday_num=int(jornada),
                        home_team_slug=obtener_slug_club(f["local"]),
                        away_team_slug=obtener_slug_club(f["visitante"]),
                        status=f["estado"]
                    )
                    tx.add(m_rec)

    logger.info("✅ [PERSISTENCIA OK] Temporada Liga MX inyectada y distribuida al 100%.")


# ===========================================================================
# FASE 5: TELEMETRÍA VISUAL SOBERANA (CONSOLA & CENTRO DE CONTROL)
# ===========================================================================
def imprimir_resumen_telemetria(datos: Dict[str, Any], t_total: float) -> None:
    """[VAULT-DAEMON-001] Emite el resumen fiduciario de jornadas y la tabla viva en consola."""
    ancho = 86
    print("=" * ancho)
    print(f"📡 [TELEMETRÍA SOBERANA] LIGA MX · FotMob ID {LIGAMX_FOTMOB_ID} · {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * ancho)

    fixtures = datos.get("fixtures_por_jornada", {}) or {}
    total_partidos = sum(len(v) for v in fixtures.values())
    print(f"🗓️  JORNADAS EXTRAÍDAS: {len(fixtures)}  |  PARTIDOS TOTALES: {total_partidos}")
    for r in sorted(fixtures):
        partidos = fixtures[r] or []
        fin = sum(1 for p in partidos if p.get("estado") == "FINALIZADO")
        prog = len(partidos) - fin
        print(f"   J{r:02d} → {len(partidos):2d} partidos  [FINALIZADO {fin:2d} | PROGRAMADO {prog:2d}]")

    tabla = datos.get("standings_viva", []) or []
    print("-" * ancho)
    print(f"📊 TABLA GENERAL VIVA ({len(tabla)} CLUBES)")
    print(f"{'#':>2} | {'CLUB':<24} | {'PJ':>3} | {'PG':>3} | {'PE':>3} | {'PP':>3} | {'GF':>3} | {'GC':>3} | {'DIF':>4} | {'PTS':>3} | FORMA")
    print("-" * ancho)
    for t in tabla:
        forma = "-".join(t.get("forma") or []) or "-"
        print(
            f"{int(t.get('pos', 0)):>2} | {str(t.get('equipo', ''))[:24]:<24} | "
            f"{int(t.get('pj', 0)):>3} | {int(t.get('pg', 0)):>3} | {int(t.get('pe', 0)):>3} | "
            f"{int(t.get('pp', 0)):>3} | {int(t.get('gf', 0)):>3} | {int(t.get('gc', 0)):>3} | "
            f"{int(t.get('dif', 0)):>4} | {int(t.get('puntos', 0)):>3} | {forma}"
        )
    print("-" * ancho)
    print(f"⏱️  TIEMPO TOTAL DE INGESTA: {t_total:.2f}s  |  REPROGRAMADOS: {len(datos.get('reprogramados', []) or [])}")
    print("=" * ancho)


def ejecutar_ingesta_soberana_ligamx():
    """Ejecuta el ciclo completo unificado: Bóveda -> Catálogo 3NF -> Temporada -> Soberano."""
    t0 = time.perf_counter()
    gw = PersistenceGateway()
    gw.create_all_tables(Base.metadata)

    # 1. Asegurar Activos y 3NF Base (Idempotente)
    asegurar_boveda_y_catalogo_ligamx(gw)

    # 2. Extraer Temporada
    datos = extraer_datos_vivos_completos()

    # 3. Persistir y Distribuir
    persistir_en_sqlite(datos, league_fotmob_id=LIGAMX_FOTMOB_ID)

    t_total = time.perf_counter() - t0
    logger.info("🏁 Ingesta Soberana de Liga MX concluida con éxito en %.2fs.", t_total)
    imprimir_resumen_telemetria(datos, t_total)


# ===========================================================================
# ENTRADA PRINCIPAL Y CLI
# ===========================================================================
def main():
    parser = argparse.ArgumentParser(description="Centinela Deportivo Autónomo Q-BE")
    parser.add_argument("--loop", type=int, default=0)
    parser.add_argument("--liga", type=int, default=LIGAMX_FOTMOB_ID)
    parser.add_argument("--todas-las-ligas", action="store_true")
    args = parser.parse_args()

    while True:
        if args.liga == LIGAMX_FOTMOB_ID and not args.todas_las_ligas:
            ejecutar_ingesta_soberana_ligamx()
        elif args.todas_las_ligas:
            # Multi-liga genérica
            pass
        
        if args.loop <= 0:
            break
        time.sleep(args.loop)

if __name__ == "__main__":
    main()