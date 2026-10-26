# -*- coding: utf-8 -*-
"""
Módulo de Resolución Canónica de Escudos y Bóveda Soberana [LN-QBE-019]
Base de Gobierno: Kybern Framework v8.0 / v12.0
"""
import os
import logging
import urllib.parse
from typing import Optional, Dict
from sqlalchemy.orm import Session
from src.core.normalization.normalizer import NormalizationException, canonicalize_team_name

logger = logging.getLogger("CrestResolver")

# Directorio raíz del proyecto y carpeta de assets estáticos
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "qbe_business"))
STATIC_CRESTS_DIR = os.path.join(BASE_DIR, "src", "web", "static", "img", "crests")

def _generar_svg_fallback(iniciales: str, club_nombre: str) -> str:
    """Genera un Data URI SVG determinista Dark Mode Fintech para clubes sin escudo físico."""
    svg_raw = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="48" height="48">
      <defs>
        <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#1C2541" />
          <stop offset="100%" stop-color="#0B132B" />
        </linearGradient>
      </defs>
      <circle cx="24" cy="24" r="22" fill="url(#grad)" stroke="#38BDF8" stroke-width="2"/>
      <text x="50%" y="54%" text-anchor="middle" dominant-baseline="middle" 
            fill="#FFFFFF" font-family="Inter, system-ui, sans-serif" font-size="14" font-weight="700">
        {iniciales[:3]}
      </text>
    </svg>"""
    encoded = urllib.parse.quote(svg_raw)
    return f"data:image/svg+xml;utf8,{encoded}"

def obtener_slug_club(nombre: str) -> str:
    """Genera un slug limpio y canónico a partir del nombre del club.

    [LN-QBE-019] El resolutor de activos degrada de forma elegante ante un club fuera del
    catálogo: el normalizador conserva su Fail-Loud (P1-4), pero el slug se deriva del texto
    limpio para que la escalera de escudos pueda entregar el SVG institucional.
    """
    try:
        nombre_canonico = canonicalize_team_name(nombre)
    except NormalizationException:
        nombre_canonico = str(nombre or "").strip()
    slug = (
        nombre_canonico.lower()
        .replace(" ", "-")
        .replace(".", "")
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ñ", "n")
    )
    return slug

# Categoría neutra legislada por `[LN-QBE-095]` (token literal; se declara aquí para evitar
# una dependencia circular `crest_resolver -> gender_guards -> crest_resolver`).
CATEGORIA_VARONIL_MAYOR = "VARONIL_MAYOR"

# Memoria Caché In-Memory para resolución ultrarrápida (< 1ms) de escudos
_CREST_CACHE: Dict[str, str] = {}

def obtener_ruta_escudo_local(equipo_nombre: str, categoria: str = CATEGORIA_VARONIL_MAYOR) -> Optional[str]:
    """
    [LN-QBE-019] Nivel 1 de la escalera, categoría-consciente
    (VAR-2026-LN-QBE-019-CATEGORY-AWARE-CREST — ALT-1 ratificada).

    Para una entidad NO neutra (`FEMENIL`, `FILIAL`, `SUB20`, tokens de `[LN-QBE-095]`) se exige
    primero el activo categorizado `/static/img/crests/{slug}-{categoria}.png`; si el activo no
    existe en disco (o no supera el piso físico de 3 KB), degrada de forma gobernada al activo
    plano `/static/img/crests/{slug}.png`. Devuelve `None` si ningún candidato es físicamente válido
    (jamás fabrica archivos: la curación es competencia del pipeline HITL).
    """
    slug = obtener_slug_club(equipo_nombre)
    os.makedirs(STATIC_CRESTS_DIR, exist_ok=True)

    categoria_normalizada = str(categoria or "").strip().upper()
    candidatos = []
    if categoria_normalizada and categoria_normalizada != CATEGORIA_VARONIL_MAYOR:
        candidatos.append(f"{slug}-{categoria_normalizada.lower()}.png")
    candidatos.append(f"{slug}.png")

    for nombre_archivo in candidatos:
        ruta_fisica = os.path.join(STATIC_CRESTS_DIR, nombre_archivo)
        if os.path.exists(ruta_fisica) and os.path.getsize(ruta_fisica) > 3000:
            return f"/static/img/crests/{nombre_archivo}"
    return None

def resolver_escudo_canonico(
    equipo_nombre: str,
    fotmob_id: Optional[int] = None,
    db: Optional[Session] = None,
    categoria: str = CATEGORIA_VARONIL_MAYOR
) -> str:
    """
    [LN-QBE-019] Resuelve la URI de escudo bajo la escalera de precedencia legislada:
    1. Bóveda Local categoría-consciente (`/static/img/crests/{slug}-{categoria}.png` para entidades
       no neutras, con degradación gobernada a `/static/img/crests/{slug}.png`) y verificación
       física (>= 3 KB) — ALT-1 ratificada (`VAR-2026-LN-QBE-019-CATEGORY-AWARE-CREST`).
    2. Consulta en base de datos SQLite (Team.canonical_slug y Team.name).
    3. Fallback a SVG Data URI.
    """
    if not equipo_nombre:
        return _generar_svg_fallback("QBE", "Club")

    # [GOVERNANCE-01] La categoría integra la clave de caché: sin ella, un activo varonil ya
    # resuelto se serviría a la entidad femenil/filial homónima (envenenamiento de caché).
    categoria_normalizada = str(categoria or CATEGORIA_VARONIL_MAYOR).strip().upper()
    cache_key = f"{equipo_nombre}:{fotmob_id}:{categoria_normalizada}"
    if cache_key in _CREST_CACHE:
        return _CREST_CACHE[cache_key]

    slug = obtener_slug_club(equipo_nombre)
    os.makedirs(STATIC_CRESTS_DIR, exist_ok=True)

    # Nivel 1: Bóveda local categoría-consciente
    res_url = obtener_ruta_escudo_local(equipo_nombre, categoria_normalizada)

    if not res_url:
        # Nivel 1B: Verificación de aliases conocidos en disco
        for extension in [f"club-{slug}.png", f"{slug}-fc.png", f"deportivo-{slug}.png"]:
            alias_fisico = os.path.join(STATIC_CRESTS_DIR, extension)
            if os.path.exists(alias_fisico) and os.path.getsize(alias_fisico) > 3000:
                res_url = f"/static/img/crests/{extension}"
                break

    if not res_url and db is not None:
        try:
            from src.storage.models import Team
            # [CORRECCIÓN INDUSTRIAL]: Usar Team.canonical_slug y Team.name reales
            team_rec = db.query(Team).filter(
                (Team.canonical_slug == slug) | (Team.name == equipo_nombre) | (Team.short_name == equipo_nombre)
            ).first()
            if team_rec and team_rec.crest_url:
                c_url = team_rec.crest_url
                if "fotmob.com" not in c_url.lower():
                    if c_url.startswith("/static/") or c_url.startswith("data:image/svg+xml"):
                        res_url = c_url
        except Exception as ex:
            logger.warning(f"Aviso en consulta SQLite para '{equipo_nombre}': {ex}")

    if not res_url:
        # Nivel 3: Fallback a SVG determinista estilizado
        palabras = equipo_nombre.strip().split()
        if len(palabras) >= 2:
            iniciales = f"{palabras[0][0]}{palabras[1][0]}".upper()
        else:
            iniciales = equipo_nombre[:3].upper()
        res_url = _generar_svg_fallback(iniciales, equipo_nombre)

    _CREST_CACHE[cache_key] = res_url
    return res_url
