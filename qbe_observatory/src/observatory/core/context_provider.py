# -*- coding: utf-8 -*-
"""
🧭 Q-BE SOVEREIGN · PROVEEDOR CANÓNICO DE CONTEXTO & SHOCKS (Fase 1 · Integración Maestra)
[LN-QBE-117] · [ARCH-1.4.55] · Migración VERBATIM de `[LN-QBE-109]` (sandbox de laboratorio).
Régimen: [DIRGEN-STRICT] para la aritmética del vector contextual C (cero margen creativo).

Contrato público:
  * `obtener_metricas_contexto(sesion, match_id, ...)` → bloque `contexto` del paquete
    `insumos_factivados` con V30 (ΔDías) y V29 (ΔAltitud⁺), `Q_mod` y `gamma_contextual`.
  * `calcular_vector_contextual_c(...)` → desglose puro (aritmética sellada, sin I/O).
  * `CATALOGO_ALTITUDES_LIGAMX` / `altitud_estadio(...)` → hecho declarado, jamás estimación.

Capa de lectura compartida de la fase (una sola implementación, cero duplicación):
`leer_fixture_cartelera`, `partidos_terminales_de_club`, `identidad_coincide`, `parse_fecha`.
Todos los proveedores de la fase consumen el MISMO corte futuro-ciego N−1 desde aquí.

Fuente única de datos: bóveda 3NF (`matches`, `match_telemetry`, `standings_snapshots`) leída por el
adaptador `src/core/sovereign_reads.py`, que entrega diccionarios planos: este paquete puro jamás
importa `sqlalchemy` ni `src.storage` ([ARCH-1.4.26]). Cero caché congelada, cero ficheros
laterales, cero defaults de esquema.
"""

from __future__ import annotations

import math
import unicodedata
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

from src.core.intensity_canonical_loglink import (
    calcular_alpha_ligadura,
    estimar_intensidades_loglineal,
    obtener_bono_fortaleza_plaza,
)
from src.observatory.core.factor_attribution import nombre_de_celda
from src.observatory.core.sovereign_reads import leer_calendario, leer_fixture, leer_partidos_corte

__all__ = [
    "CATALOGO_ALTITUDES_LIGAMX",
    "ALIAS_ALTITUDES",
    "ESTADOS_TERMINALES",
    "altitud_estadio",
    "slug_canonico_altitud",
    "calcular_vector_contextual_c",
    "identidad_coincide",
    "parse_fecha",
    "leer_fixture_cartelera",
    "partidos_terminales_de_club",
    "obtener_metricas_contexto",
]

# ── Nodos de gobierno y constantes legisladas [LN-QBE-109] / [LN-QBE-117] ──────────────────────
NODOS_GOBIERNO: Tuple[str, ...] = ("LN-QBE-117", "ARCH-1.4.55", "LN-QBE-109")
TEMPORADA_DEFAULT = "2026"
MU_LIGA_DEFAULT = 2.65                    # [CONSTANTS] media de goles de la competición
GAMMA_BASE = 0.1500                       # [LN-QBE-109] γ̄_base de localía
BETA_ALTITUD = 0.0300                     # [LN-QBE-109] bono por cada 1000 m de ΔAlt⁺
BETA_DESCANSO = 0.0200                    # [LN-QBE-109] bono por día de ΔDescanso
DESCANSO_TOPE_DIAS = 14.0                 # [LN-QBE-109] tope fisiológico de recuperación
DESCANSO_CLAMP_DIAS = 3.0                 # [LN-QBE-109] cota del bono de descanso
Q_MOD_MIN, Q_MOD_MAX = 0.90, 1.05         # [LN-QBE-109] contención de shocks de plantilla
LAMBDA_MIN, LAMBDA_MAX = 0.15, 4.50       # Invariante I6 (positividad estricta acotada)
NORMA_CONTEXTO_MAX = 0.2500               # [LN-QBE-039] techo normativo del vector C
TOLERANCIA_PARIDAD = 1e-3                 # residuo máximo admisible vs. motor sellado
VENTANA_TRAYECTORIA = 5                   # [LN-QBE-110] ventana móvil de la fase

ESTADOS_TERMINALES: Tuple[str, ...] = ("FINALIZADO", "FINISHED")
ESTADO_EXITO = "EXITO"
ESTADO_PARCIAL = "PARCIAL"
ESTADO_SIN_EVIDENCIA = "SIN EVIDENCIA"


# ═════════════════════════════════════════════════════════════════════════════════════════════
# [LN-QBE-109] CATÁLOGO INMUTABLE DE ALTITUDES DE ESTADIO (msnm)
# Valores legislados en el Sprint de Contexto & Shocks. Cero calibración local: este catálogo
# es un HECHO declarado, no una estimación. Slug ausente ⇒ None (SIN EVIDENCIA), jamás 0 m.
# ═════════════════════════════════════════════════════════════════════════════════════════════
CATALOGO_ALTITUDES_LIGAMX: Dict[str, float] = {
    "deportivo-toluca": 2660.0,
    "pachuca": 2400.0,
    "club-puebla": 2135.0,
    "pumas-unam": 2240.0,
    "club-america": 2240.0,
    "cruz-azul": 2240.0,
    "atlante": 2240.0,
    "chivas-guadalajara": 1560.0,
    "atlas-fc": 1560.0,
    "club-leon": 1815.0,
    "queretaro-fc": 1820.0,
    "club-necaxa": 1880.0,
    "atletico-san-luis": 1860.0,
    "fc-juarez": 1120.0,
    "santos-laguna": 1120.0,
    "tigres-uanl": 540.0,
    "rayados-de-monterrey": 540.0,
    "club-tijuana": 30.0,
    "mazatlan-fc": 10.0,
}

# Deriva de nomenclatura viva (3NF / FotMob) → clave del catálogo legislado.
# Sólo resuelve nombres: NO altera un solo valor numérico del catálogo.
ALIAS_ALTITUDES: Dict[str, str] = {
    "club-pachuca": "pachuca",
    "necaxa": "club-necaxa",
    "pumas": "pumas-unam",
    "america": "club-america",
    "chivas": "chivas-guadalajara",
    "atlas": "atlas-fc",
    "leon": "club-leon",
    "queretaro": "queretaro-fc",
    "san-luis": "atletico-san-luis",
    "juarez": "fc-juarez",
    "santos": "santos-laguna",
    "tigres": "tigres-uanl",
    "monterrey": "rayados-de-monterrey",
    "tijuana": "club-tijuana",
    "mazatlan": "mazatlan-fc",
    "puebla": "club-puebla",
    "toluca": "deportivo-toluca",
    "club-atlante": "atlante",
}


def slug_canonico_altitud(home_slug: Optional[str]) -> Optional[str]:
    """Resuelve el slug vivo al slug del catálogo de altitudes (alias declarado)."""
    if not home_slug:
        return None
    clave = str(home_slug).lower().strip()
    if clave in CATALOGO_ALTITUDES_LIGAMX:
        return clave
    return ALIAS_ALTITUDES.get(clave)


def altitud_estadio(home_slug: Optional[str]) -> Optional[float]:
    """Altitud oficial (msnm) del estadio del club; `None` si no está catalogado."""
    canonico = slug_canonico_altitud(home_slug)
    if canonico is None:
        return None
    return float(CATALOGO_ALTITUDES_LIGAMX[canonico])


def _r(valor: Optional[float], decimales: int = 6) -> Optional[float]:
    """Redondeo seguro para serialización (None permanece None)."""
    return None if valor is None else round(float(valor), decimales)


def _clamp(valor: float, minimo: float, maximo: float) -> float:
    """Contención dura en [minimo, maximo] (invariante de rango, sin efectos laterales)."""
    return max(float(minimo), min(float(maximo), float(valor)))


def _num(valor: Any) -> Optional[float]:
    """Coerción defensiva: texto corrupto o booleano ⇒ `None`, nunca cero implícito."""
    if valor is None or isinstance(valor, bool):
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


# ═════════════════════════════════════════════════════════════════════════════════════════════
# [LN-QBE-109] VECTOR CONTEXTUAL C — aritmética pura, sin estado y sin I/O
# ═════════════════════════════════════════════════════════════════════════════════════════════
def calcular_vector_contextual_c(
    altitud_local: Optional[float],
    altitud_visita: Optional[float],
    dias_descanso_local: Optional[float],
    dias_descanso_visita: Optional[float],
    home_slug: str,
    q_mod_h: float = 1.0,
    q_mod_a: float = 1.0,
) -> Dict[str, Any]:
    """Desglose del vector contextual (C_H, C_A) de [LN-QBE-109].

    Definiciones selladas:
        ΔAlt⁺        = max(0, Alt_local − Alt_visita)                (unidireccional)
        Bono_alt     = 0.0300 · ΔAlt⁺ / 1000
        ΔDescanso    = Días_local − Días_visita ; Días_T = min(14, (t_match − t_prev).days)
        Bono_rec     = 0.0200 · clamp(ΔDescanso, [−3, +3])
        γ_contextual = γ̄_base + Δγ_plaza + Bono_alt + Bono_rec        (γ̄_base = 0.1500)
        C_H          = (γ_contextual − γ̄_base) + ln(clamp(Q_H, [0.90, 1.05]))
        C_A          = ln(clamp(Q_A, [0.90, 1.05]))
        ΔContexto    = γ̄_base + C_H − C_A

    La evidencia ausente NO se imputa: el bono correspondiente vale 0.0 y la celda se publica
    como `SIN EVIDENCIA` aguas arriba. Las λ provienen VERBATIM del motor sellado.
    """
    alt_local = None if altitud_local is None else float(altitud_local)
    alt_visita = None if altitud_visita is None else float(altitud_visita)
    altitud_evaluada = alt_local is not None and alt_visita is not None

    if altitud_evaluada:
        delta_altitud = max(0.0, alt_local - alt_visita)
        bono_altitud = BETA_ALTITUD * (delta_altitud / 1000.0)
    else:
        delta_altitud = None
        bono_altitud = 0.0

    descanso_evaluado = dias_descanso_local is not None and dias_descanso_visita is not None
    if descanso_evaluado:
        delta_descanso = float(dias_descanso_local) - float(dias_descanso_visita)
        delta_descanso_clamped = _clamp(delta_descanso, -DESCANSO_CLAMP_DIAS, DESCANSO_CLAMP_DIAS)
        bono_descanso = BETA_DESCANSO * delta_descanso_clamped
    else:
        delta_descanso = None
        delta_descanso_clamped = None
        bono_descanso = 0.0

    bono_plaza = float(obtener_bono_fortaleza_plaza(home_slug))
    gamma_contextual = GAMMA_BASE + bono_plaza + bono_altitud + bono_descanso

    q_h = _clamp(q_mod_h, Q_MOD_MIN, Q_MOD_MAX)
    q_a = _clamp(q_mod_a, Q_MOD_MIN, Q_MOD_MAX)
    C_H = (gamma_contextual - GAMMA_BASE) + math.log(q_h)
    C_A = math.log(q_a)
    delta_contexto = GAMMA_BASE + C_H - C_A

    # ── λ: delegación VERBATIM al motor sellado (canal contextual aislado: A = D = 0) ──────
    # [LN-QBE-123] El adaptador del motor exige `float` (firma sellada, [LN-QBE-109]): cuando el
    # descanso o la altitud NO son reconstruibles, el bono vale 0.0 y al motor se le entrega `0.0`
    # —ausencia de bono, no una medición—. Esa ignorancia NO se propaga a la telemetría: el vector
    # publica `delta_descanso_dias = None`/`delta_alt_metros = None` y las banderas
    # `descanso_evaluado` / `altitud_evaluada`, de modo que la celda forense V30/V29 se apaga en
    # lugar de exhibir un `+0.0 d` fabricado.
    lambda_home, lambda_away = estimar_intensidades_loglineal(
        0.0, 0.0, 0.0, 0.0,
        mu_liga=MU_LIGA_DEFAULT,
        gamma_home_base=GAMMA_BASE,
        delta_alt_metros=(delta_altitud or 0.0),
        delta_descanso_dias=(delta_descanso or 0.0),
        q_mod_h=q_h,
        q_mod_a=q_a,
        home_team_slug=home_slug,
    )

    # ── Guarda de paridad: residuo auditable contra la identidad canónica ────────────────
    alpha = calcular_alpha_ligadura(MU_LIGA_DEFAULT, GAMMA_BASE + bono_plaza)
    lambda_h_ref = _clamp(math.exp(alpha + gamma_contextual + math.log(q_h)),
                          LAMBDA_MIN, LAMBDA_MAX)
    lambda_a_ref = _clamp(math.exp(alpha + math.log(q_a)), LAMBDA_MIN, LAMBDA_MAX)
    paridad = max(abs(lambda_h_ref - float(lambda_home)),
                  abs(lambda_a_ref - float(lambda_away)))

    return {
        "delta_altitud_metros": _r(delta_altitud, 4),
        "bono_altitud": _r(bono_altitud, 6),
        "delta_descanso_dias": _r(delta_descanso, 4),
        "delta_descanso_clamped": _r(delta_descanso_clamped, 4),
        "bono_descanso": _r(bono_descanso, 6),
        "bono_plaza": _r(bono_plaza, 4),
        "gamma_contextual": _r(gamma_contextual, 6),
        "C_H": _r(C_H, 6),
        "C_A": _r(C_A, 6),
        "delta_contexto": _r(delta_contexto, 6),
        "q_mod_h": _r(q_h, 4),
        "q_mod_a": _r(q_a, 4),
        "q_mod_h_clamped": bool(abs(q_h - float(q_mod_h)) > 1e-12),
        "q_mod_a_clamped": bool(abs(q_a - float(q_mod_a)) > 1e-12),
        "altitud_evaluada": altitud_evaluada,
        "descanso_evaluado": descanso_evaluado,
        "alpha_ligadura": _r(alpha, 6),
        "lambda_home": _r(lambda_home, 4),
        "lambda_away": _r(lambda_away, 4),
        "paridad_motor": _r(paridad, 8),
        "home_slug": str(home_slug or ""),
    }


# ═════════════════════════════════════════════════════════════════════════════════════════════
# [ARCH-1.4.55] CAPA DE LECTURA COMPARTIDA DE LA FASE (cartelera 3NF, sólo lectura)
# ═════════════════════════════════════════════════════════════════════════════════════════════
def parse_fecha(valor: Any) -> Optional[datetime]:
    """Parsea `kickoff_utc` (ISO-8601 con o sin zona) a datetime NAIVE comparable."""
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor.replace(tzinfo=None)
    if isinstance(valor, date):
        return datetime(valor.year, valor.month, valor.day)
    texto = str(valor).strip()
    if not texto:
        return None
    try:
        return datetime.fromisoformat(texto.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        pass
    for formato in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(texto[:19], formato)
        except ValueError:
            continue
    try:
        return datetime.strptime(texto[:10], "%Y-%m-%d")
    except ValueError:
        return None


def normalizar_identidad(texto: Any) -> str:
    """NFKD → ASCII → minúsculas → guiones. Sólo para casar identidades, jamás para publicar."""
    if texto is None:
        return ""
    crudo = unicodedata.normalize("NFKD", str(texto))
    crudo = "".join(
        caracter for caracter in crudo if not unicodedata.combining(caracter)
    )
    crudo = crudo.encode("ascii", "ignore").decode("ascii").lower()
    slug = "".join(caracter if caracter.isalnum() else "-" for caracter in crudo)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")


_PALABRAS_GENERICAS = frozenset(
    {
        "club",
        "cf",
        "fc",
        "cd",
        "ca",
        "deportivo",
        "atletico",
        "at",
        "de",
        "del",
        "la",
        "el",
        "los",
    }
)


def identidad_coincide(candidato: Any, referencia: Any) -> bool:
    """Casa `matches.home_team_slug` (sin acento) con `standings.equipo` (con acento).

    Regla de identidad, no de negocio: igualdad normalizada o contención de tokens
    distintivos (≥ 4 caracteres) tras descartar conectores y sufijos societarios.
    """
    izquierda = normalizar_identidad(candidato)
    derecha = normalizar_identidad(referencia)
    if not izquierda or not derecha:
        return False
    if izquierda == derecha:
        return True
    tokens_izquierda = {
        token
        for token in izquierda.split("-")
        if token and token not in _PALABRAS_GENERICAS
    }
    tokens_derecha = {
        token
        for token in derecha.split("-")
        if token and token not in _PALABRAS_GENERICAS
    }
    if not tokens_izquierda or not tokens_derecha:
        return False
    if tokens_izquierda <= tokens_derecha or tokens_derecha <= tokens_izquierda:
        return max(len(token) for token in (tokens_izquierda | tokens_derecha)) >= 4
    return False


def leer_fixture_cartelera(sesion: Any, match_id: str) -> Optional[Dict[str, Any]]:
    """Localiza el fixture evaluado en la cartelera 3NF (`matches`), sólo lectura.

    La jornada canónica proviene de `matchday_num` y la fecha de `kickoff_utc`: la columna
    heredada `kickoff` no se consulta (la cartelera viva la publica vacía por decreto).
    """
    registro = leer_fixture(sesion, match_id)
    if registro is None:
        return None
    marcador = None
    if registro["score_home"] is not None and registro["score_away"] is not None:
        marcador = f"{registro['score_home']}-{registro['score_away']}"
    return {
        "match_id": str(registro["id"]),
        "jornada": (
            int(registro["matchday_num"]) if registro["matchday_num"] is not None else None
        ),
        "fecha": parse_fecha(registro["kickoff_utc"]),
        "local_slug": str(registro["home_team_slug"] or "").lower().strip(),
        "visitante_slug": str(registro["away_team_slug"] or "").lower().strip(),
        "local": registro["home_team_slug"] or "",
        "visitante": registro["away_team_slug"] or "",
        "estado": str(registro["status"] or "").upper().strip(),
        "marcador": marcador,
        "competicion": str(registro["competition_id"] or ""),
        "temporada": str(registro["season_id"] or ""),
        "origen": "matches",
    }


def partidos_terminales_de_club(
    sesion: Any,
    club_slug: str,
    jornada_corte: Optional[int],
    limite: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Corte futuro-ciego N−1 de un club: partidos terminales con `matchday_num < N`.

    Sólo se publican partidos con marcador real y estado terminal; el fixture evaluado (y toda
    jornada ≥ N) queda fuera del corte por construcción. `limite` recorta la COLA de la ventana
    (los `limite` partidos más recientes), preservando el orden cronológico ascendente.
    """
    corte = int(jornada_corte or 0)
    club = str(club_slug or "").lower().strip()
    if not club or corte <= 1:
        return []
    filas = leer_partidos_corte(sesion, corte)
    partidos: List[Dict[str, Any]] = []
    for fila in filas:
        estado = str(fila["status"] or "").upper().strip()
        if estado not in ESTADOS_TERMINALES:
            continue
        if fila["score_home"] is None or fila["score_away"] is None:
            continue
        home = str(fila["home_team_slug"] or "").lower().strip()
        away = str(fila["away_team_slug"] or "").lower().strip()
        if club not in (home, away):
            continue
        es_local = home == club
        goles_favor = int(fila["score_home"] if es_local else fila["score_away"])
        goles_contra = int(fila["score_away"] if es_local else fila["score_home"])
        partidos.append(
            {
                "match_id": str(fila["id"]),
                "jornada": int(fila["matchday_num"]),
                "fecha": parse_fecha(fila["kickoff_utc"]),
                "es_local": es_local,
                "rival_slug": away if es_local else home,
                "goles_favor": goles_favor,
                "goles_contra": goles_contra,
                "resultado": (
                    "G" if goles_favor > goles_contra
                    else ("E" if goles_favor == goles_contra else "P")
                ),
            }
        )
    if limite is not None and len(partidos) > int(limite):
        return partidos[-int(limite):]
    return partidos


def _catalogo_calendario(sesion: Any) -> List[Dict[str, Any]]:
    """Cartelera completa (todas las jornadas) indexada por `match_id` desde la bóveda 3NF."""
    indice: Dict[str, Dict[str, Any]] = {}
    for fila in leer_calendario(sesion):
        ident = str(fila["id"])
        if ident in indice:
            continue
        marcador = None
        if fila["score_home"] is not None and fila["score_away"] is not None:
            marcador = f"{fila['score_home']}-{fila['score_away']}"
        indice[ident] = {
            "match_id": ident,
            "jornada": fila["matchday_num"],
            "fecha": parse_fecha(fila["kickoff_utc"]),
            "local_slug": str(fila["home_team_slug"] or "").lower().strip(),
            "visitante_slug": str(fila["away_team_slug"] or "").lower().strip(),
            "local": fila["home_team_slug"] or "",
            "visitante": fila["away_team_slug"] or "",
            "estado": str(fila["status"] or "").upper().strip(),
            "marcador": marcador,
            "origen": "matches",
        }
    return list(indice.values())


def _partido_previo(
    calendario: Sequence[Dict[str, Any]],
    club_slug: str,
    jornada: int,
    kickoff: Optional[datetime],
    excluir: str,
) -> Dict[str, Any]:
    """Último partido TERMINAL del club con `jornada < N` y fecha estrictamente anterior.

    Regla futuro-ciega: el fixture evaluado (y toda jornada ≥ N) queda fuera del corte, de
    modo que el descanso jamás se construye con información posterior al partido.
    """
    club = str(club_slug or "").lower().strip()
    candidatos: List[Dict[str, Any]] = []
    for partido in calendario:
        if partido["match_id"] == str(excluir):
            continue
        if partido["jornada"] is None or int(partido["jornada"]) >= int(jornada):
            continue
        if partido["estado"] not in ESTADOS_TERMINALES:
            continue
        if club not in (partido["local_slug"], partido["visitante_slug"]):
            continue
        if partido["fecha"] is None:
            continue
        if kickoff is not None and partido["fecha"] >= kickoff:
            continue
        candidatos.append(partido)

    if not candidatos:
        return {"encontrado": False, "motivo": f"Sin partidos terminales previos para `{club}`."}
    previo = max(candidatos, key=lambda partido: partido["fecha"])
    condicion = "LOCAL" if previo["local_slug"] == club else "VISITA"
    return {
        "encontrado": True,
        "match_id": previo["match_id"],
        "jornada": int(previo["jornada"]),
        "fecha": previo["fecha"].isoformat(),
        "rival": previo["visitante"] if condicion == "LOCAL" else previo["local"],
        "condicion": condicion,
        "marcador": previo["marcador"],
        "origen": previo["origen"],
        "partidos_considerados": len(candidatos),
    }


def _dias_descanso(kickoff: Optional[datetime], previo: Dict[str, Any]) -> Optional[float]:
    """Días reales de recuperación acotados al tope fisiológico [LN-QBE-109]."""
    if kickoff is None or not previo.get("encontrado"):
        return None
    fecha_previa = parse_fecha(previo.get("fecha"))
    if fecha_previa is None:
        return None
    dias = (kickoff - fecha_previa).days
    if dias < 0:
        return None
    return float(min(DESCANSO_TOPE_DIAS, dias))


# ═════════════════════════════════════════════════════════════════════════════════════════════
# [LN-QBE-117] BLOQUE `contexto` DEL PAQUETE `insumos_factivados`
# ═════════════════════════════════════════════════════════════════════════════════════════════
def _celda(
    identificador: str,
    variable: str,
    local: Any,
    visita: Any,
    estado: str,
    origen: str,
    impacto: str,
    nota: str,
) -> Dict[str, Any]:
    """Celda forense V-coded del bloque (unidades declaradas, cero fabricación)."""
    return {
        "id": identificador,
        "variable": variable,
        "local": local,
        "visita": visita,
        "estado": estado,
        "origen": origen,
        "impacto": impacto,
        "nota": nota,
        "glifo": "🟢" if estado == "EVALUADO" else "⚪",
    }


def _texto_dias(dias: Optional[float]) -> str:
    return "—" if dias is None else f"{float(dias):.1f} d"


def _texto_metros(metros: Optional[float]) -> str:
    return "—" if metros is None else f"{float(metros):.0f} m"


def _bloque_vacio_contexto(match_id: str, motivo: str, temporada: str) -> Dict[str, Any]:
    """Bloque degradado honesto: cero cifras, cero defaults, semáforo apagado."""
    return {
        "bloque": "contexto",
        "match_id": str(match_id),
        "temporada": str(temporada),
        "status": ESTADO_SIN_EVIDENCIA,
        "motivo": motivo,
        "fixture": None,
        "altitud_local": None,
        "altitud_visita": None,
        "descanso_local": None,
        "descanso_visita": None,
        "previo_local": {"encontrado": False, "motivo": motivo},
        "previo_visita": {"encontrado": False, "motivo": motivo},
        "vector": None,
        "insumos": {
            "delta_alt_metros": None,
            "delta_descanso_dias": None,
            "altitud_local": None,
            "altitud_visita": None,
            "q_mod_h": None,
            "q_mod_a": None,
            "gamma_contextual": None,
            "delta_contexto": None,
            "descanso_local": None,
            "descanso_visita": None,
            # [LN-QBE-123] Presencia DECLARADA: sin fixture no hay altitud ni descanso evaluados.
            "altitud_evaluada": False,
            "descanso_evaluado": False,
        },
        "variables": {
            "AUX_XG_BAJAS": _celda("AUX_XG_BAJAS", "Impacto xG de bajas ofensivas", None, None,
                                   ESTADO_SIN_EVIDENCIA, "Q-BE", "H_ctx", motivo),
            "AUX_XGA_BAJAS": _celda("AUX_XGA_BAJAS", "Impacto xGA de bajas defensivas", None, None,
                                    ESTADO_SIN_EVIDENCIA, "Q-BE", "H_ctx", motivo),
            "V30": _celda("V30", nombre_de_celda("V30", "Días de Descanso (ΔDías)"), None, None,
                          ESTADO_SIN_EVIDENCIA, "FIXTURE", "H_ctx", motivo),
            "V29": _celda("V29", nombre_de_celda("V29", "Altitud ΔAlt+ (Factor Fisiológico)"), None, None,
                          ESTADO_SIN_EVIDENCIA, "FIXTURE", "H_ctx", motivo),
        },
    }



def obtener_metricas_contexto(
    sesion: Any,
    match_id: str,
    temporada: str = TEMPORADA_DEFAULT,
    q_mod_h: float = 1.0,
    q_mod_a: float = 1.0,
) -> Dict[str, Any]:
    """[LN-QBE-117] · Bloque `contexto` (`V29`/`V30` + `AUX_*` de bajas) del fixture evaluado.

    Secuencia: fixture en cartelera 3NF → altitud catalogada de ambas plazas → descanso real
    (último partido terminal con `jornada < N`, futuro-ciego) → vector contextual C sellado
    [LN-QBE-109] → celdas `V30`/`V29` con su estado de evidencia.

    Una plaza sin altitud catalogada o un calendario sin fechas reales degradan la celda a
    `SIN EVIDENCIA` (bono 0.0), jamás a "nivel del mar" ni a un descanso inventado.
    """
    fixture = leer_fixture_cartelera(sesion, match_id)
    if fixture is None:
        return _bloque_vacio_contexto(
            match_id,
            f"El fixture `{match_id}` no existe en la cartelera 3NF (`matches`).",
            temporada,
        )

    jornada = fixture.get("jornada")
    local_slug = str(fixture.get("local_slug") or "")
    visita_slug = str(fixture.get("visitante_slug") or "")
    if jornada is None or not local_slug or not visita_slug:
        return _bloque_vacio_contexto(
            match_id,
            "El fixture no publica jornada canónica (`matchday_num`) o slugs de ambos clubes.",
            temporada,
        )

    altitud_local = altitud_estadio(local_slug)
    altitud_visita = altitud_estadio(visita_slug)
    calendario = _catalogo_calendario(sesion)
    previo_local = _partido_previo(
        calendario, local_slug, int(jornada), fixture.get("fecha"), fixture["match_id"]
    )
    previo_visita = _partido_previo(
        calendario, visita_slug, int(jornada), fixture.get("fecha"), fixture["match_id"]
    )
    descanso_local = _dias_descanso(fixture.get("fecha"), previo_local)
    descanso_visita = _dias_descanso(fixture.get("fecha"), previo_visita)

    vector = calcular_vector_contextual_c(
        altitud_local,
        altitud_visita,
        descanso_local,
        descanso_visita,
        local_slug,
        q_mod_h=q_mod_h,
        q_mod_a=q_mod_a,
    )

    altitud_evaluada = bool(vector["altitud_evaluada"])
    descanso_evaluado = bool(vector["descanso_evaluado"])
    if altitud_evaluada and descanso_evaluado:
        status = ESTADO_EXITO
        motivo = (
            "Altitud de ambas plazas catalogada y descanso real reconstruido del calendario "
            "terminal: el vector contextual se publica completo [LN-QBE-109]."
        )
    elif altitud_evaluada or descanso_evaluado:
        status = ESTADO_PARCIAL
        motivo = (
            "Evidencia contextual parcial: el bono ausente vale 0.0 y su celda se declara "
            "SIN EVIDENCIA (cero imputación de altitud o descanso)."
        )
    else:
        status = ESTADO_SIN_EVIDENCIA
        motivo = (
            "Ni la altitud de las plazas ni el descanso previo son reconstruibles: el vector "
            "contextual se publica neutro (bonos 0.0) y V30/V29 quedan SIN EVIDENCIA."
        )

    delta_alt = vector["delta_altitud_metros"]
    delta_dias = vector["delta_descanso_dias"]
    variables = {
        "AUX_XG_BAJAS": _celda(
            "AUX_XG_BAJAS", "Impacto xG de bajas ofensivas", None, None, ESTADO_SIN_EVIDENCIA,
            "Q-BE", "H_ctx",
            "SIN EVIDENCIA: el sensor congelado no publica reporte de bajas por club.",
        ),
        "AUX_XGA_BAJAS": _celda(
            "AUX_XGA_BAJAS", "Impacto xGA de bajas defensivas", None, None, ESTADO_SIN_EVIDENCIA,
            "Q-BE", "H_ctx",
            "SIN EVIDENCIA: el sensor congelado no publica reporte de bajas por club.",
        ),
        "V30": _celda(
            "V30",
            nombre_de_celda("V30", "Días de Descanso (ΔDías)"),
            _texto_dias(descanso_local),
            _texto_dias(descanso_visita),
            "EVALUADO" if descanso_evaluado else ESTADO_SIN_EVIDENCIA,
            "FIXTURE",
            "H_ctx",
            (
                f"ΔDías = {delta_dias:+.1f} d (clamp ±{DESCANSO_CLAMP_DIAS:.0f} d; tope "
                f"{DESCANSO_TOPE_DIAS:.0f} d) · Bono = {vector['bono_descanso']:+.6f}"
                if descanso_evaluado
                else "SIN EVIDENCIA: el calendario no publica fechas previas terminales."
            ),
        ),
        "V29": _celda(
            "V29",
            nombre_de_celda("V29", "Altitud ΔAlt+ (Factor Fisiológico)"),
            _texto_metros(altitud_local),
            _texto_metros(altitud_visita),
            "EVALUADO" if altitud_evaluada else ESTADO_SIN_EVIDENCIA,
            "FIXTURE",
            "H_ctx",
            (
                f"ΔAlt⁺ = {delta_alt:.0f} m (max(0, Alt_local − Alt_visita)) · "
                f"Bono = {vector['bono_altitud']:+.6f}"
                if altitud_evaluada
                else "SIN EVIDENCIA: alguna plaza no está en el catálogo de altitudes."
            ),
        ),
    }


    return {
        "bloque": "contexto",
        "match_id": str(match_id),
        "temporada": str(temporada),
        "status": status,
        "motivo": motivo,
        "fixture": fixture,
        "altitud_local": altitud_local,
        "altitud_visita": altitud_visita,
        "descanso_local": descanso_local,
        "descanso_visita": descanso_visita,
        "previo_local": previo_local,
        "previo_visita": previo_visita,
        "vector": vector,
        "insumos": {
            "delta_alt_metros": delta_alt,
            "delta_descanso_dias": delta_dias,
            "altitud_local": altitud_local,
            "altitud_visita": altitud_visita,
            "q_mod_h": vector["q_mod_h"],
            "q_mod_a": vector["q_mod_a"],
            "gamma_contextual": vector["gamma_contextual"],
            "delta_contexto": vector["delta_contexto"],
            "bono_altitud": vector["bono_altitud"],
            "bono_descanso": vector["bono_descanso"],
            "bono_plaza": vector["bono_plaza"],
            "descanso_local": descanso_local,
            "descanso_visita": descanso_visita,
            # [LN-QBE-123] Presencia DECLARADA de las magnitudes de `contexto`: la bandera manda
            # sobre cualquier centinela plano del homologador (`0.0`) al encender V30/V29.
            "altitud_evaluada": bool(altitud_evaluada),
            "descanso_evaluado": bool(descanso_evaluado),
            "alpha_ligadura": vector["alpha_ligadura"],
            "lambda_contextual_home": vector["lambda_home"],
            "lambda_contextual_away": vector["lambda_away"],
            "paridad_motor": vector["paridad_motor"],
            "paridad_ok": bool(
                float(vector["paridad_motor"]) <= float(TOLERANCIA_PARIDAD)
            ),
            "dentro_norma_contexto": bool(
                abs(float(vector["delta_contexto"])) <= float(NORMA_CONTEXTO_MAX)
            ),
        },
        "variables": variables,
    }

