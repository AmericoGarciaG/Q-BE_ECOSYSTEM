# -*- coding: utf-8 -*-
"""
Kybern Industrial — [LN-QBE-015] Curador Agéntico de Catálogos y Bóveda de Activos
[ARCH-1.5.2] Módulo Administrativo de Curación HITL
Base de Gobierno: Kybern Framework v8.0 / v12.0
"""
import os
import json
import shutil
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Set
import httpx
from sqlalchemy.orm import Session
from src.storage.models import League, Team
from src.core.normalization.normalizer import canonicalize_team_name

# ─── Directorios soberanos ────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
STAGING_DIR = PROJECT_ROOT / "data"
CRESTS_DIR = PROJECT_ROOT / "src" / "web" / "static" / "img" / "crests"
CRESTS_DIR.mkdir(parents=True, exist_ok=True)
STAGING_DIR.mkdir(parents=True, exist_ok=True)

# ─── Catálogo Canónico Oficial FMF / Liga MX (Fuente de la Verdad) ───────────
# [LN-QBE-130] Curación HITL: catálogo canónico oficial FMF / Liga MX.
# Cada entrada declara el SLUG CANÓNICO ratificado (ALT-8-C, catálogo `TEAMS_LIGA_MX`) y el
# identificador FÁCTICO de FotMob. Los slugs legados se conservan como `aliases` para el espejeo
# físico de escudos (Anti-Archivos Fantasma [ARCH-1.5.4]). Con los slugs legados,
# `sellar_catalogo_en_db` no hallaba par en la bóveda y fabricaba 10 clubes con
# `fotmob_team_id = 10000 + idx` ([GOVERNANCE-01]): defecto de idempotencia erradicado de raíz.
# `Mazatlán FC` no tiene par fáctico en el catálogo ratificado ⇒ `fotmob_id = None` y su
# inserción queda VETADA por [LN-QBE-130] (cero alta sintética).
PROSPECCION_LIGA_MX: List[Dict[str, Any]] = [
    {
        "name": "Club América", "short": "América", "slug": "club-america",
        "fotmob_id": 6576,
        "stadium": "Ciudad de los Deportes", "city": "Ciudad de México",
        "crest_url": "https://cldrsrcs.apilmx.com/v1/docs/archdgtl/AfldDrct/logos/1/1.png",
        "aliases": ["america", "aguilas"],
    },
    {
        "name": "Atlas FC", "short": "Atlas", "slug": "atlas-fc",
        "fotmob_id": 6577,
        "stadium": "Jalisco", "city": "Guadalajara",
        "crest_url": "https://cldrsrcs.apilmx.com/v1/docs/archdgtl/AfldDrct/logos/10445/10445.png",
        "aliases": ["atlas", "zorros", "rojinegros"],
    },
    {
        "name": "Club Tijuana", "short": "Tijuana", "slug": "club-tijuana",
        "fotmob_id": 162418,
        "stadium": "Caliente", "city": "Tijuana",
        "crest_url": "https://cldrsrcs.apilmx.com/v1/docs/archdgtl/AfldDrct/logos/5/5.png",
        "aliases": ["tijuana", "xolos"],
    },
    {
        "name": "Cruz Azul", "short": "Cruz Azul", "slug": "cruz-azul",
        "fotmob_id": 6578,
        "stadium": "Ciudad de los Deportes", "city": "Ciudad de México",
        "crest_url": "https://cldrsrcs.apilmx.com/v1/docs/archdgtl/AfldDrct/logos/6/6.png",
        "aliases": ["cruzazul", "la-maquina", "cementeros"],
    },
    {
        "name": "Chivas Guadalajara", "short": "Chivas", "slug": "chivas-guadalajara",
        "fotmob_id": 7807,
        "stadium": "Akron", "city": "Zapopan",
        "crest_url": "https://cldrsrcs.apilmx.com/v1/docs/archdgtl/AfldDrct/logos/7/7.png",
        "aliases": ["guadalajara", "chivas"],
    },
    {
        "name": "Club León", "short": "León", "slug": "club-leon",
        "fotmob_id": 1841,
        "stadium": "León", "city": "León",
        "crest_url": "https://cldrsrcs.apilmx.com/v1/docs/archdgtl/AfldDrct/logos/9/9.png",
        "aliases": ["leon", "la-fiera", "panzas-verdes"],
    },
    {
        "name": "Club Pachuca", "short": "Pachuca", "slug": "club-pachuca",
        "fotmob_id": 7848,
        "stadium": "Hidalgo", "city": "Pachuca",
        "crest_url": "https://cldrsrcs.apilmx.com/v1/docs/archdgtl/AfldDrct/logos/11/11.png",
        "aliases": ["pachuca", "tuzos"],
    },
    {
        "name": "Club Puebla", "short": "Puebla", "slug": "club-puebla",
        "fotmob_id": 7847,
        "stadium": "Cuauhtémoc", "city": "Puebla",
        "crest_url": "https://cldrsrcs.apilmx.com/v1/docs/archdgtl/AfldDrct/logos/12/12.png",
        "aliases": ["puebla", "la-franja", "camoteros"],
    },
    {
        "name": "Rayados de Monterrey", "short": "Monterrey", "slug": "rayados-de-monterrey",
        "fotmob_id": 7849,
        "stadium": "BBVA", "city": "Guadalupe",
        "crest_url": "https://cldrsrcs.apilmx.com/v1/docs/archdgtl/AfldDrct/logos/14/14.png",
        "aliases": ["monterrey", "rayados"],
    },
    {
        "name": "Santos Laguna", "short": "Santos", "slug": "santos-laguna",
        "fotmob_id": 7857,
        "stadium": "Corona", "city": "Torreón",
        "crest_url": "https://cldrsrcs.apilmx.com/v1/docs/archdgtl/AfldDrct/logos/15/15.png",
        "aliases": ["santos", "guerreros", "laguneros"],
    },
    {
        "name": "Tigres UANL", "short": "Tigres", "slug": "tigres-uanl",
        "fotmob_id": 8561,
        "stadium": "Universitario", "city": "San Nicolás de los Garza",
        "crest_url": "https://cldrsrcs.apilmx.com/v1/docs/archdgtl/AfldDrct/logos/16/16.png",
        "aliases": ["tigres", "felinos", "uanl"],
    },
    {
        "name": "Deportivo Toluca", "short": "Toluca", "slug": "deportivo-toluca",
        "fotmob_id": 6618,
        "stadium": "Nemesio Díez", "city": "Toluca",
        "crest_url": "https://cldrsrcs.apilmx.com/v1/docs/archdgtl/AfldDrct/logos/17/17.png",
        "aliases": ["toluca", "diablos-rojos"],
    },
    {
        "name": "Pumas UNAM", "short": "Pumas", "slug": "pumas-unam",
        "fotmob_id": 1946,
        "stadium": "Olímpico Universitario", "city": "Ciudad de México",
        "crest_url": "https://cldrsrcs.apilmx.com/v1/docs/archdgtl/AfldDrct/logos/18/18.png",
        "aliases": ["pumas", "unam", "univ-nacional", "universitarios"],
    },
    {
        "name": "Necaxa", "short": "Necaxa", "slug": "necaxa",
        "fotmob_id": 1842,
        "stadium": "Victoria", "city": "Aguascalientes",
        "crest_url": "https://cldrsrcs.apilmx.com/v1/docs/archdgtl/AfldDrct/logos/29/29.png",
        "aliases": ["rayos-necaxa", "rayos"],
    },
    {
        "name": "Querétaro FC", "short": "Querétaro", "slug": "queretaro-fc",
        "fotmob_id": 1943,
        "stadium": "Corregidora", "city": "Querétaro",
        "crest_url": "https://cldrsrcs.apilmx.com/v1/docs/archdgtl/AfldDrct/logos/13668/13668.png",
        "aliases": ["queretaro", "gallos-blancos", "qro-fc"],
    },
    {
        "name": "Atlético San Luis", "short": "San Luis", "slug": "atletico-san-luis",
        "fotmob_id": 6358,
        "stadium": "Alfonso Lastras", "city": "San Luis Potosí",
        "crest_url": "https://cldrsrcs.apilmx.com/v1/docs/archdgtl/AfldDrct/logos/11220/11220.png",
        "aliases": ["san-luis", "atleti-san-luis", "potosinos"],
    },
    {
        "name": "Mazatlán FC", "short": "Mazatlán", "slug": "mazatlan",
        "fotmob_id": None,
        "stadium": "El Encanto", "city": "Mazatlán",
        "crest_url": "https://cldrsrcs.apilmx.com/v1/docs/archdgtl/AfldDrct/logos/12043/12043.png",
        "aliases": ["mazatlan-fc", "canoneros"],
    },
    {
        "name": "FC Juárez", "short": "Juárez", "slug": "fc-juarez",
        "fotmob_id": 649424,
        "stadium": "Benito Juárez", "city": "Ciudad Juárez",
        "crest_url": "https://cldrsrcs.apilmx.com/v1/docs/archdgtl/AfldDrct/logos/11790/11790.png",
        "aliases": ["juarez", "bravos"],
    },
]

# ─── Claves de Identidad y Veto de Fabricación [LN-QBE-130] ──────────────────

def _slug_de_identidad(nombre: str) -> str:
    """Deriva el slug canónico de un nombre de club (paridad `seeder` / `sync_service`)."""
    return (
        canonicalize_team_name(nombre or "").lower()
        .replace(" ", "-").replace(".", "")
        .replace("á", "a").replace("é", "e").replace("í", "i")
        .replace("ó", "o").replace("ú", "u").replace("ñ", "n")
    )


def _claves_de_identidad(entrada: Dict[str, Any]) -> Set[str]:
    """
    [LN-QBE-130] Claves de reconciliación de una entrada de curación
    frente a la tabla `teams`: el slug declarado (canónico o legado), todos sus `aliases` y el
    slug derivado del nombre canónico. CERO fabricación: sólo habilita la búsqueda de un par
    fáctico ya existente en la bóveda.
    """
    claves: Set[str] = set()
    for valor in (entrada.get("canonical_slug"), entrada.get("slug")):
        if valor:
            claves.add(str(valor).strip().lower())
    for alias in (entrada.get("aliases") or []):
        if alias:
            claves.add(str(alias).strip().lower().replace(" ", "-"))
    if entrada.get("name"):
        slug_nombre = _slug_de_identidad(str(entrada["name"]))
        if slug_nombre:
            claves.add(slug_nombre)
    claves.discard("")
    return claves


# ─── Funciones de Curación IPO ────────────────────────────────────────────────

def ejecutar_prospeccion_liga(league_id: int) -> Dict[str, Any]:
    """Descubre clubes candidatos y genera data/.staging_catalogs_{league_id}.json."""
    staged = []
    for idx, c in enumerate(PROSPECCION_LIGA_MX, 1):
        staged.append({
            "id_candidato": f"CAND-{idx:02d}",
            "name": c["name"],
            "short_name": c["short"],
            "canonical_slug": c["slug"],
            # [LN-QBE-130] Identidad fáctica propagada al staging HITL: el
            # contrato `TeamCatalogItemIn.fotmob_id` (ya declarado en el router) transporta la
            # evidencia oficial de FotMob hasta el sellado. Cero identificadores fabricados.
            "fotmob_id": c.get("fotmob_id"),
            "stadium": c["stadium"],
            "city": c["city"],
            "crest_candidate_url": c["crest_url"],
            "crest_url": f"/static/img/crests/{c['slug']}.png",
            "aliases": c["aliases"],
            "status": "APPROVED",
        })

    staging_path = STAGING_DIR / f".staging_catalogs_{league_id}.json"
    staging_path.write_text(
        json.dumps(staged, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return {"status": "STAGED", "league_id": league_id, "candidates_count": len(staged)}


def obtener_staging_liga(league_id: int) -> List[Dict[str, Any]]:
    """Lee candidatos en staging; auto-ejecuta prospección si no existe."""
    staging_path = STAGING_DIR / f".staging_catalogs_{league_id}.json"
    if not staging_path.exists():
        ejecutar_prospeccion_liga(league_id)
    
    raw = json.loads(staging_path.read_text(encoding="utf-8"))
    teams = raw.get("teams", raw) if isinstance(raw, dict) else raw
    return teams


def sellar_catalogo_en_db(
    league_id: int,
    approved_teams: List[Dict[str, Any]],
    db: Session,
) -> Dict[str, Any]:
    """
    [Commit Inmutable HITL + Multi-Slug Mirroring]
    Descarga los escudos oficiales a disco con verificación de integridad y realiza
    el espejeo físico obligatorio a todos sus aliases reconocidos [ARCH-1.5.4].

    [LN-QBE-130] Reconciliación
    IDEMPOTENTE por clave de identidad (slug canónico | aliases | slug del nombre canónico)
    y por el `fotmob_id` fáctico, con VETO de fabricación ([GOVERNANCE-01] / [ALT-5-A]): si la
    entrada no halla par fáctico comprobable en la bóveda se veta; JAMÁS se inserta identidad
    inventada (`fotmob_team_id = 10000 + idx`).
    """
    league = db.query(League).filter(
        (League.fotmob_id == league_id) | (League.id == league_id)
    ).first()
    if not league:
        raise ValueError(f"Liga con id={league_id} no encontrada en la base de datos.")

    committed = 0
    reconciliados = 0
    vetados: List[str] = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://ligamx.net/"
    }

    with httpx.Client(timeout=15.0, headers=headers, follow_redirects=True) as client:
        for t in approved_teams:
            slug = t.get("canonical_slug") or t.get("slug")
            if not slug:
                continue
            committed += 1
            crest_url = t.get("crest_candidate_url") or t.get("crest_url", "")
            local_filename = f"{slug}.png"
            local_path = CRESTS_DIR / local_filename

            # 1. Descarga soberana local (solo si no existe o es menor a 3 KB)
            if not local_path.exists() or local_path.stat().st_size < 3000:
                if crest_url and crest_url.startswith("http"):
                    try:
                        r = client.get(crest_url)
                        if r.status_code == 200 and len(r.content) > 3000 and r.content.startswith(b"\x89PNG"):
                            local_path.write_bytes(r.content)
                    except Exception as exc:
                        print(f"⚠️ [CURATION] Error descargando '{slug}': {exc}")

            # 2. [ARCH-1.5.4] Espejeo físico a todos los aliases (Anti-Archivos Fantasma)
            aliases = t.get("aliases", [])
            if local_path.exists() and local_path.stat().st_size >= 3000:
                for alias in aliases:
                    if alias and alias != slug:
                        alias_clean = alias.lower().replace(" ", "-")
                        alias_path = CRESTS_DIR / f"{alias_clean}.png"
                        shutil.copyfile(local_path, alias_path)

            # 3. [LN-QBE-130] Reconciliación idempotente con clave de
            #    identidad DUAL y VETO de fabricación. Defecto extirpado: la línea previa
            #    (`Team.canonical_slug == slug`) reconciliaba sólo por slug EXACTO, de modo que
            #    los slugs legados del catálogo de prospección no hallaban par en la bóveda y se
            #    insertaban clubes con `fotmob_team_id = 10000 + idx` (10 tuplas residuales por
            #    corrida ⇒ ruptura de la idempotencia de The Shield) [GOVERNANCE-01].
            final_crest_url = f"/static/img/crests/{local_filename}"
            claves_identidad = _claves_de_identidad(t)
            fotmob_id_factual = t.get("fotmob_id")

            # (a) Par fáctico dentro de la competición: slug canónico o cualquiera de sus aliases.
            team_db = db.query(Team).filter(
                Team.league_id == league.id,
                Team.canonical_slug.in_(sorted(claves_identidad)),
            ).first()

            # (b) Respaldo por identidad oficial de FotMob (única en la bóveda).
            if not team_db and fotmob_id_factual:
                team_db = db.query(Team).filter(
                    Team.fotmob_team_id == int(fotmob_id_factual)
                ).first()

            if not team_db:
                # VETO DE FABRICACIÓN: sin evidencia fáctica comprobable NO se inserta identidad
                # sintética. El único escritor autorizado de `teams` con identidad fáctica es la
                # Fase 4 de `centinela_deportivo.py` ([ALT-5-A RATIFICADA]).
                vetados.append(slug)
                continue

            # Actualización IN SITU (jamás INSERT): identidad fáctica y metadatos HITL.
            team_db.league_id = league.id
            team_db.name = t["name"]
            team_db.short_name = t.get("short_name", team_db.short_name)
            if fotmob_id_factual:
                team_db.fotmob_team_id = int(fotmob_id_factual)
            if team_db.canonical_slug == slug:
                # El espejo local sólo se declara sobre el slug canónico: nunca se reescribe el
                # `crest_url` canónico con un nombre legado (hallazgo 12.3.4 de [LN-QBE-130]).
                team_db.crest_url = final_crest_url
            reconciliados += 1

    db.commit()
    # [LN-QBE-130 / 12.3.3] Contador honesto: `teams_committed` reporta ENTRADAS PROCESADAS
    # (contrato del Juez 022 preservado) y el desglose real (reconciliadas / vetadas) se declara
    # aparte. El contador previo anunciaba «18 clubes» mientras insertaba 10 filas sintéticas.
    print(
        f"✅ [CURATION INDUSTRIAL] Catálogo sellado: {committed} entradas procesadas, "
        f"{reconciliados} clubes reconciliados in situ (cero altas sintéticas) "
        f"en league_id={league_id}."
    )
    if vetados:
        print(
            f"🛡️ [CURATION] {len(vetados)} entrada(s) VETADA(S) por ausencia de par fáctico: "
            f"{sorted(set(vetados))} ([GOVERNANCE-01])."
        )
    return {
        "status": "SEALED",
        "league_id": league_id,
        "teams_committed": committed,
        "teams_reconciled": reconciliados,
        "teams_vetoed": sorted(set(vetados)),
    }


# ─── Subsistema Incremental de Logos de Ligas ──────────────────────────────────
LEAGUES_DIR = PROJECT_ROOT / "src" / "web" / "static" / "img" / "leagues"
LEAGUES_DIR.mkdir(parents=True, exist_ok=True)

OFFICIAL_LEAGUE_LOGOS = {
    262: [
        "https://upload.wikimedia.org/wikipedia/commons/thumb/2/22/Liga_MX_logo.svg/500px-Liga_MX_logo.svg.png",
        "https://upload.wikimedia.org/wikipedia/commons/2/22/Liga_MX_logo.svg"
    ]
}

def asegurar_logo_liga_incremental(league_id: int, db: Session) -> str:
    """
    [ARCH-1.5.1] Inspección delta e ingesta nativa del emblema oficial de la competencia.
    """
    local_path = LEAGUES_DIR / f"league_{league_id}.png"
    relative_url = f"/static/img/leagues/league_{league_id}.png"

    if local_path.exists() and local_path.stat().st_size > 1000:
        return relative_url

    urls = OFFICIAL_LEAGUE_LOGOS.get(league_id, [])
    if isinstance(urls, str): urls = [urls]

    headers = {
        "User-Agent": "Q-BE-SportsEngine/3.0 (https://qbe.local; admin@qbe.local) Mozilla/5.0",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"
    }

    descargado = False
    with httpx.Client(timeout=15.0, headers=headers, follow_redirects=True) as client:
        for u in urls:
            try:
                r = client.get(u)
                if r.status_code == 200 and len(r.content) > 1000:
                    local_path.write_bytes(r.content)
                    print(f"✅ [ASSET] Logo oficial de liga {league_id} guardado en {local_path} ({len(r.content)/1024:.1f} KB)")
                    descargado = True
                    break
            except Exception as e:
                print(f"  ⚠️ Intento fallido para logo liga {league_id} desde {u}: {e}")

    if descargado and local_path.exists():
        league = db.query(League).filter((League.fotmob_id == league_id) | (League.id == league_id)).first()
        if league:
            league.flag = relative_url
            db.commit()

    return relative_url

