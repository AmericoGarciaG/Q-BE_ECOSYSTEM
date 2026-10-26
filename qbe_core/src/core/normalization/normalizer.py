# Q-BE Casino Deportes — Team Normalizer Engine (src/ingestion/normalizer.py)
"""
[LN-QBE-012] Normalizador Canónico de Clubes y Cuotas.
[ARCH-PILLAR] Módulo de resolución canónica de identidades de clubes y matching difuso
para Liga MX y competencias internacionales.
"""

import re
from difflib import SequenceMatcher
from typing import Dict, Iterable, List, Optional, Tuple


class NormalizationException(Exception):
    """[LN-QBE-012 / Saneamiento O-09] Identidad no resoluble con certeza."""


_CANONICAL_ALIASES: Dict[str, str] = {
    # Liga MX
    "club tijuana": "Club Tijuana",
    "tijuana xolos de caliente": "Club Tijuana",
    "xolos": "Club Tijuana",
    "club tijuana xolos": "Club Tijuana",
    "tijuana": "Club Tijuana",
    "fc juarez": "FC Juárez",
    "fc juárez": "FC Juárez",
    "fe juarez": "FC Juárez",
    "fe juárez": "FC Juárez",
    "bravos": "FC Juárez",
    "juarez": "FC Juárez",
    "juarezz": "FC Juárez",
    "jurez": "FC Juárez",
    "queretaro fc": "Querétaro FC",
    "querétaro fc": "Querétaro FC",
    "queretaro": "Querétaro FC",
    "querétaro": "Querétaro FC",
    "gallos blancos": "Querétaro FC",
    "gallos": "Querétaro FC",
    "qro fc": "Querétaro FC",
    "qro": "Querétaro FC",
    "club america": "Club América",
    "america": "Club América",
    "américa": "Club América",
    "cf america": "Club América",
    "club leon": "Club León",
    "leon": "Club León",
    "león": "Club León",
    "club pachuca": "Club Pachuca",
    "pachuca": "Club Pachuca",
    "guadalajara": "Chivas Guadalajara",
    "chivas": "Chivas Guadalajara",
    "chivas guadalajara": "Chivas Guadalajara",
    "guadalajara chivas": "Guadalajara",
    "atlas": "Atlas FC",
    "atlas fc": "Atlas FC",
    "tigres": "Tigres UANL",
    "tigres uanl": "Tigres UANL",
    "monterrey": "Rayados de Monterrey",
    "cf monterrey": "Monterrey",
    "rayados": "Rayados de Monterrey",
    "rayados de monterrey": "Rayados de Monterrey",
    "puebla": "Club Puebla",
    "club puebla": "Club Puebla",
    "santos laguna": "Santos Laguna",
    "santos": "Santos Laguna",
    "cruz azul": "Cruz Azul",
    "necaxa": "Necaxa",
    "toluca": "Deportivo Toluca",
    "deportivo toluca": "Deportivo Toluca",
    "mazatlan": "Mazatlán FC",
    "mazatlán": "Mazatlán FC",
    "mazatlan fc": "Mazatlán",
    "mazatlán fc": "Mazatlán",
    "pumas": "Pumas UNAM",
    "pumas unam": "Pumas UNAM",
    "unam pumas": "Pumas UNAM",
    "unam": "Pumas UNAM",
    "univ. nacional": "Pumas UNAM",
    "univ nacional": "Pumas UNAM",
    "universidad nacional": "Pumas UNAM",
    "club universidad nacional": "Pumas UNAM",
    "u.n.a.m.": "Pumas UNAM",

    "san luis": "Atlético San Luis",
    "atletico san luis": "Atlético San Luis",
    "atlético san luis": "Atlético San Luis",
    "atletico de san luis": "Atlético San Luis",
    "atleti san luis": "Atlético San Luis",
    "atlante": "Atlante",
}

_CANONICAL_TEAM_NAMES: List[str] = sorted({name for name in _CANONICAL_ALIASES.values()}, key=len, reverse=True)


def _normalize_text(value: str) -> str:
    text = value.strip().lower()
    text = text.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ñ", "n")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"[\s_\-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _levenshtein_distance(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)

    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i]
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            curr.append(min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost))
        prev = curr
    return prev[-1]


def canonicalize_team_name(team_name: Optional[str]) -> str:
    """Normaliza nombres de clubes del mercado o scraper a un nombre canónico oficial."""
    if team_name is None:
        return ""

    texto = _normalize_text(str(team_name))
    if not texto:
        return ""

    direct = _CANONICAL_ALIASES.get(texto)
    if direct:
        return direct

    # Fuzzy matching robusto para errores OCR / tipográficos. [Saneamiento O-09]
    # Prohibida la contención de subcadenas: sólo igualdad exacta, ratio >= 0.78 o
    # distancia de Levenshtein <= 2 para cadenas de longitud >= 4.
    for canonical in _CANONICAL_TEAM_NAMES:
        normalized_canonical = _normalize_text(canonical)
        if texto == normalized_canonical:
            return canonical

        ratio = SequenceMatcher(None, texto, normalized_canonical).ratio()
        if ratio >= 0.78:
            return canonical

        if len(texto) >= 4 and len(normalized_canonical) >= 4:
            if _levenshtein_distance(texto, normalized_canonical) <= 2:
                return canonical

    raise NormalizationException(f"No se pudo normalizar el equipo: '{team_name}'")


normalizar_nombre_club = canonicalize_team_name



def canonicalize_match_teams(local: Optional[str], visitante: Optional[str]) -> Tuple[str, str]:
    return canonicalize_team_name(local), canonicalize_team_name(visitante)


def canonicalize_records(records: Iterable[Dict[str, object]]) -> List[Dict[str, object]]:
    normalized: List[Dict[str, object]] = []
    for record in records:
        item = dict(record)
        for field in ("local", "equipo_local", "team_home", "visitante", "equipo_visitante", "team_away"):
            if field in item and item[field] is not None:
                item[field] = canonicalize_team_name(str(item[field]))
        normalized.append(item)
    return normalized