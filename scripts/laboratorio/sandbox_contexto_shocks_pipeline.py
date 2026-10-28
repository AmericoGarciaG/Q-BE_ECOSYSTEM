# -*- coding: utf-8 -*-
"""
[LN-QBE-109] / [ARCH-1.4.48] SANDBOX CONTEXTO & SHOCKS — PIPELINE AUTÓNOMO CLI-FIRST.

Misión
------
Aislar en consola la Dimensión 7 (𝒯_Shk · V29/V30 + `AUX_*`): el vector contextual (C_H, C_A) que
modula la ventaja territorial de la ecuación log-lineal canónica. Expone el desglose físico
—altitud (V29), descanso (V30), fortaleza de plaza y shocks de plantilla (`AUX_Q_MOD_H`/`AUX_Q_MOD_A`)— sin
FastAPI, sin DOM y sin Playwright.

Régimen: `[HÍBRIDO DUAL-TRACK]`
* `[DIRGEN-STRICT]`: las intensidades (λ_H, λ_A) NO se reimplementan: se invocan VERBATIM
  `estimar_intensidades_loglineal` y `calcular_alpha_ligadura` [VAULT-CORE-001]; el bono de
  plaza se delega en `obtener_bono_fortaleza_plaza` [LN-QBE-038]. Este sandbox NUNCA es
  fuente de λ: publica además `paridad_motor` como residuo auditable contra el plano sellado.
* `[DBBD-FUNGIBLE]`: catálogo de altitudes, resolución de calendario, celdas V29/V30 + `AUX_*`,
  tablero ASCII, semáforo CTX y CLI.

Axiomas operativos
------------------
1. **Sólo lectura:** `PersistenceGateway.read_session()`; prohibido escribir en la bóveda y
   prohibido abrir red.
2. **Futuro-ceguera (N−1):** el partido previo de cada club se toma de la cartelera con
   `jornada < N` y estado terminal. El fixture evaluado jamás alimenta su propio descanso.
3. **Fuente de fechas:** la tabla `matches` no publica `kickoff_utc` utilizable (100 % NULL en
   la 3NF viva); la fuente fáctica es `fixtures_snapshots.matches_json[].fecha_dt`.
4. **Cero invención [GOVERNANCE-01]:** altitud no catalogada ⇒ V29 `SIN EVIDENCIA` (jamás
   "nivel del mar"); sin reporte médico auditado ⇒ Q_mod = 1.0000 (`SIN SHOCK`).
5. **Altitud unidireccional (V29):** sólo bonifica jugar MÁS ALTO; el diferencial negativo se
   rectifica a 0 m y no penaliza al local.

Uso:
    python -m scripts.laboratorio.sandbox_contexto_shocks_pipeline --partido LIGAMX-J11-07
    python -m scripts.laboratorio.sandbox_contexto_shocks_pipeline --jornada 11
    python -m scripts.laboratorio.sandbox_contexto_shocks_pipeline --partido LIGAMX-J11-07 --json
    python -m scripts.laboratorio.sandbox_contexto_shocks_pipeline --partido LIGAMX-J11-07 --q-mod-h 0.95
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import os
import sys
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy import select

# ── Planos sellados (cero reimplementación de fórmulas) ─────────────────────────────────────
from src.core.intensity_canonical_loglink import (
    KAPPA_NET,
    calcular_alpha_ligadura,
    estimar_intensidades_loglineal,
    obtener_bono_fortaleza_plaza,
)
from src.storage.gateway import PersistenceGateway
from src.storage.models import FixtureSnapshot, Match

logger = logging.getLogger("SandboxContextoShocks")

# ── Nodos de gobierno y constantes legisladas ──────────────────────────────────────────────
NODOS_GOBIERNO: Tuple[str, str] = ("LN-QBE-109", "ARCH-1.4.48")
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

ESTADO_EVALUADO = "EVALUADO"
ESTADO_SIN_EVIDENCIA = "SIN EVIDENCIA"
ESTADOS_TERMINALES = ("FINALIZADO", "FINISHED")
NIVEL_VERDE = "VERDE"
NIVEL_AMARILLO = "AMARILLO"
NIVEL_ROJO = "ROJO"
NIVEL_NEUTRAL = "NEUTRAL"
GLIFO = {
    NIVEL_VERDE: "🟢", NIVEL_AMARILLO: "🟡", NIVEL_ROJO: "🔴", NIVEL_NEUTRAL: "⚪",
    ESTADO_EVALUADO: "🟢", ESTADO_SIN_EVIDENCIA: "⚪",
}
ANCHO_TABLERO = 94


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


def _slug_canonico_altitud(home_slug: Optional[str]) -> Optional[str]:
    """Resuelve el slug vivo al slug del catálogo de altitudes (alias declarado)."""
    if not home_slug:
        return None
    clave = str(home_slug).lower().strip()
    if clave in CATALOGO_ALTITUDES_LIGAMX:
        return clave
    return ALIAS_ALTITUDES.get(clave)


def altitud_estadio(home_slug: Optional[str]) -> Optional[float]:
    """Altitud oficial (msnm) del estadio del club; `None` si no está catalogado."""
    canonico = _slug_canonico_altitud(home_slug)
    if canonico is None:
        return None
    return float(CATALOGO_ALTITUDES_LIGAMX[canonico])


def _r(valor: Optional[float], decimales: int = 6) -> Optional[float]:
    """Redondeo seguro para serialización (None permanece None)."""
    return None if valor is None else round(float(valor), decimales)


def _clamp(valor: float, minimo: float, maximo: float) -> float:
    return max(float(minimo), min(float(maximo), float(valor)))


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
        "q_mod_h_clamped": bool(abs(q_h - float(q_mod_h or 0.0)) > 1e-12),
        "q_mod_a_clamped": bool(abs(q_a - float(q_mod_a or 0.0)) > 1e-12),
        "altitud_evaluada": altitud_evaluada,
        "descanso_evaluado": descanso_evaluado,
        "alpha_ligadura": _r(alpha, 6),
        "lambda_home": _r(lambda_home, 4),
        "lambda_away": _r(lambda_away, 4),
        "paridad_motor": _r(paridad, 8),
        "home_slug": str(home_slug or ""),
    }


# ═════════════════════════════════════════════════════════════════════════════════════════════
# LOCALIZACIÓN DEL FIXTURE Y CALENDARIO (cartelera 3NF, sólo lectura)
# ═════════════════════════════════════════════════════════════════════════════════════════════
def _entradas_snapshot(snapshot: Any) -> List[Dict[str, Any]]:
    """Normaliza `matches_json` (lista ORM o texto crudo SQLite) a lista de diccionarios."""
    partidos = snapshot.matches_json or []
    if isinstance(partidos, str):
        try:
            partidos = json.loads(partidos)
        except ValueError:
            return []
    if not isinstance(partidos, list):
        return []
    return [entrada for entrada in partidos if isinstance(entrada, dict)]


def _parse_fecha(valor: Any) -> Optional[datetime]:
    """Parsea `fecha_dt` (ISO-8601 con o sin zona) a datetime NAIVE comparable."""
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


def _fecha_iso(valor: Optional[datetime]) -> Optional[str]:
    return valor.isoformat() if valor is not None else None


def _leer_fixture(sesion: Any, match_id: str) -> Optional[Dict[str, Any]]:
    """Localiza el fixture por `id_partido` en el snapshot más reciente (fallback: `matches`).

    El snapshot es la fuente de exhibición (nombres, `fecha_dt`, marcador y JORNADA canónica).
    La tabla `matches` sólo aporta slugs y `kickoff_utc` cuando el fixture no está en cartelera.
    """
    consulta = select(FixtureSnapshot).order_by(
        FixtureSnapshot.updated_at.desc(), FixtureSnapshot.id.desc()
    )
    for snapshot in sesion.execute(consulta).scalars().all():
        for entrada in _entradas_snapshot(snapshot):
            if str(entrada.get("id_partido")) != str(match_id):
                continue
            actualizado = snapshot.updated_at
            return {
                "match_id": str(entrada.get("id_partido")),
                "jornada": int(snapshot.matchday) if snapshot.matchday is not None else None,
                "local": entrada.get("local") or "",
                "visitante": entrada.get("visitante") or "",
                "local_slug": entrada.get("home_team_slug") or "",
                "visitante_slug": entrada.get("away_team_slug") or "",
                "fecha_ref": entrada.get("fecha_dt") or entrada.get("kickoff_utc"),
                "estado": entrada.get("estado") or "",
                "marcador": entrada.get("marcador_actual"),
                "origen": f"fixtures_snapshots#{snapshot.id}",
                "snapshot_actualizado": (
                    actualizado.isoformat() if hasattr(actualizado, "isoformat")
                    else str(actualizado or "")
                ),
            }

    registro = sesion.execute(select(Match).where(Match.id == str(match_id))).scalars().first()
    if registro is None:
        return None
    marcador = None
    if registro.score_home is not None and registro.score_away is not None:
        marcador = f"{registro.score_home}-{registro.score_away}"
    return {
        "match_id": str(registro.id),
        "jornada": registro.matchday_num,
        "local": registro.home_team_slug or "",
        "visitante": registro.away_team_slug or "",
        "local_slug": registro.home_team_slug or "",
        "visitante_slug": registro.away_team_slug or "",
        "fecha_ref": registro.kickoff_utc.isoformat() if registro.kickoff_utc else None,
        "estado": registro.status or "",
        "marcador": marcador,
        "origen": "matches",
        "snapshot_actualizado": "",
    }


def _catalogo_calendario(sesion: Any) -> List[Dict[str, Any]]:
    """Cartelera completa (todas las jornadas) indexada por `id_partido`.

    Deduplica por fixture conservando la lectura del snapshot MÁS RECIENTE (la cartelera viva
    puede reprogramar un partido). `matches` sólo rellena fixtures ausentes de los snapshots.
    """
    indice: Dict[str, Dict[str, Any]] = {}
    consulta = select(FixtureSnapshot).order_by(
        FixtureSnapshot.updated_at.desc(), FixtureSnapshot.id.desc()
    )
    for snapshot in sesion.execute(consulta).scalars().all():
        jornada = int(snapshot.matchday) if snapshot.matchday is not None else None
        for entrada in _entradas_snapshot(snapshot):
            ident = str(entrada.get("id_partido") or "")
            if not ident or ident in indice:
                continue
            indice[ident] = {
                "match_id": ident,
                "jornada": jornada,
                "fecha": _parse_fecha(entrada.get("fecha_dt") or entrada.get("kickoff_utc")),
                "local_slug": str(entrada.get("home_team_slug") or "").lower().strip(),
                "visitante_slug": str(entrada.get("away_team_slug") or "").lower().strip(),
                "local": entrada.get("local") or "",
                "visitante": entrada.get("visitante") or "",
                "estado": str(entrada.get("estado") or "").upper().strip(),
                "marcador": entrada.get("marcador_actual"),
                "origen": f"fixtures_snapshots#{snapshot.id}",
            }

    for fila in sesion.execute(select(Match)).scalars().all():
        ident = str(fila.id)
        if ident in indice:
            continue
        marcador = None
        if fila.score_home is not None and fila.score_away is not None:
            marcador = f"{fila.score_home}-{fila.score_away}"
        indice[ident] = {
            "match_id": ident,
            "jornada": fila.matchday_num,
            "fecha": _parse_fecha(fila.kickoff_utc),
            "local_slug": str(fila.home_team_slug or "").lower().strip(),
            "visitante_slug": str(fila.away_team_slug or "").lower().strip(),
            "local": fila.home_team_slug or "",
            "visitante": fila.away_team_slug or "",
            "estado": str(fila.status or "").upper().strip(),
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
        "fecha": _fecha_iso(previo["fecha"]),
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
    fecha_previa = _parse_fecha(previo.get("fecha"))
    if fecha_previa is None:
        return None
    dias = (kickoff - fecha_previa).days
    if dias < 0:
        return None
    return float(min(DESCANSO_TOPE_DIAS, dias))


# ═════════════════════════════════════════════════════════════════════════════════════════════
# [LN-QBE-109] CELDAS DE 𝒯_Shk: V29/V30 + AUX_* (taxonomía Dimensión 7)
# ═════════════════════════════════════════════════════════════════════════════════════════════
def _texto_dias(dias: Optional[float]) -> str:
    return "—" if dias is None else f"{float(dias):.1f} d"


def _texto_metros(metros: Optional[float]) -> str:
    return "—" if metros is None else f"{float(metros):.0f} m"


def _texto_merma(q_mod: float) -> str:
    return f"{(1.0 - float(q_mod)) * 100.0:+.1f} %"


def _celda(
    identificador: str,
    variable: str,
    unidad: str,
    local: str,
    visita: str,
    estado: str,
    nota: str,
) -> Dict[str, Any]:
    return {
        "id": identificador,
        "variable": variable,
        "unidad": unidad,
        "local": local,
        "visita": visita,
        "estado": estado,
        "nota": nota,
    }


def _celdas_dimension_7(
    ctx: Dict[str, Any],
    prev_local: Dict[str, Any],
    prev_visita: Dict[str, Any],
    dias_local: Optional[float],
    dias_visita: Optional[float],
    altitud_local: Optional[float],
    altitud_visita: Optional[float],
    q_mod_h: float,
    q_mod_a: float,
) -> Dict[str, Dict[str, Any]]:
    """Construye las celdas de 𝒯_Shk (`V29`/`V30` + `AUX_*` de bajas, `[LN-QBE-122]`).
    La evidencia ausente se declara, jamás se imputa.
    """
    estado_descanso = ESTADO_EVALUADO if ctx["descanso_evaluado"] else ESTADO_SIN_EVIDENCIA
    estado_altitud = ESTADO_EVALUADO if ctx["altitud_evaluada"] else ESTADO_SIN_EVIDENCIA

    nota_descanso = (
        f"Previos: local {prev_local.get('match_id') or '—'} (J{prev_local.get('jornada') or '—'}), "
        f"visita {prev_visita.get('match_id') or '—'} (J{prev_visita.get('jornada') or '—'}). "
        f"Δcrudo {ctx['delta_descanso_dias'] if ctx['delta_descanso_dias'] is not None else '—'} d "
        f"→ clamp ±{DESCANSO_CLAMP_DIAS:.0f} d → Bono {ctx['bono_descanso']:+.4f}."
        if ctx["descanso_evaluado"] else
        "SIN EVIDENCIA: falta fecha de kickoff o partido previo terminal en el corte N−1."
    )
    nota_altitud = (
        f"Catálogo msnm: local {_texto_metros(altitud_local)}, visita {_texto_metros(altitud_visita)}. "
        f"ΔAlt⁺ {_texto_metros(ctx['delta_altitud_metros'])} → Bono {ctx['bono_altitud']:+.4f} "
        f"(unidireccional: altura menor no penaliza)."
        if ctx["altitud_evaluada"] else
        "SIN EVIDENCIA: al menos un club no está en el catálogo inmutable de altitudes."
    )

    return {
        "AUX_Q_MOD_H": _celda(
            "AUX_Q_MOD_H", "Bajas ofensivas del local (Q_mod,H)", "% merma",
            _texto_merma(q_mod_h), "—", ESTADO_EVALUADO,
            "SIN SHOCK · Q_mod,H = 1.0000 (no existe reporte médico auditado; se prohíbe inventar bajas)."
            if abs(float(q_mod_h) - 1.0) < 1e-12 else
            f"SHOCK INYECTADO POR CLI (no auditado): Q_mod,H = {float(q_mod_h):.4f}.",
        ),
        "AUX_Q_MOD_A": _celda(
            "AUX_Q_MOD_A", "Bajas defensivas del visitante (Q_mod,A)", "% merma",
            "—", _texto_merma(q_mod_a), ESTADO_EVALUADO,
            "SIN SHOCK · Q_mod,A = 1.0000 (no existe reporte médico auditado; se prohíbe inventar bajas)."
            if abs(float(q_mod_a) - 1.0) < 1e-12 else
            f"SHOCK INYECTADO POR CLI (no auditado): Q_mod,A = {float(q_mod_a):.4f}.",
        ),
        "V30": _celda(
            "V30", "Días de Descanso (ΔDías)", "días",
            _texto_dias(dias_local), _texto_dias(dias_visita), estado_descanso, nota_descanso,
        ),
        "V29": _celda(
            "V29", "Altitud ΔAlt+ (Factor Fisiológico)", "metros",
            _texto_metros(altitud_local), _texto_metros(altitud_visita), estado_altitud, nota_altitud,
        ),
    }


# ═════════════════════════════════════════════════════════════════════════════════════════════
# [LN-QBE-109] SEMÁFOROS Y ORQUESTACIÓN DEL SANDBOX (sólo lectura)
# ═════════════════════════════════════════════════════════════════════════════════════════════
def _semaforo(nivel: str, detalle: str) -> Dict[str, Any]:
    return {"nivel": nivel, "glifo": GLIFO.get(nivel, "·"), "detalle": detalle}


def _semaforos_contexto(
    ctx: Dict[str, Any], faltantes: Sequence[str], altitud_local: Optional[float],
    altitud_visita: Optional[float],
) -> Dict[str, Dict[str, Any]]:
    """Salud fiduciaria: techo normativo del vector C, paridad con el motor y cobertura."""
    magnitud = abs(float(ctx["C_H"]) - float(ctx["C_A"]))
    if faltantes:
        celda_ctx = _semaforo(
            NIVEL_NEUTRAL,
            f"CTX INCOMPLETO: sin evidencia para {', '.join(faltantes)}; "
            f"el techo ‖C‖max = {NORMA_CONTEXTO_MAX:.4f} no es evaluable.",
        )
    elif magnitud > NORMA_CONTEXTO_MAX:
        celda_ctx = _semaforo(
            NIVEL_AMARILLO,
            f"CTX EXTREMO: |C_H − C_A| = {magnitud:.4f} > techo {NORMA_CONTEXTO_MAX:.4f} "
            f"[LN-QBE-039]; revisar la cartelera antes de consumir λ.",
        )
    else:
        celda_ctx = _semaforo(
            NIVEL_VERDE,
            f"CTX NOMINAL: |C_H − C_A| = {magnitud:.4f} ≤ techo {NORMA_CONTEXTO_MAX:.4f}.",
        )

    paridad = float(ctx.get("paridad_motor") or 0.0)
    if paridad <= TOLERANCIA_PARIDAD:
        celda_paridad = _semaforo(
            NIVEL_VERDE,
            f"PARIDAD MATEMÁTICA: residuo {paridad:.2e} ≤ {TOLERANCIA_PARIDAD:.0e} frente a "
            f"[VAULT-CORE-001] (λ sólo las emite el motor sellado).",
        )
    else:
        celda_paridad = _semaforo(
            NIVEL_ROJO,
            f"DERIVA: residuo {paridad:.2e} > {TOLERANCIA_PARIDAD:.0e}; el desglose NO debe consumirse.",
        )

    if not faltantes:
        celda_cobertura = _semaforo(
            NIVEL_VERDE,
            f"V30 y V29 evaluadas · altitud local {_texto_metros(altitud_local)} · "
            f"visita {_texto_metros(altitud_visita)}.",
        )
    else:
        celda_cobertura = _semaforo(
            NIVEL_NEUTRAL,
            f"Cobertura parcial: {', '.join(faltantes)} sin evidencia; bono correspondiente = 0.0 "
            f"(jamás imputado).",
        )
    return {"CTX": celda_ctx, "PARIDAD_MOTOR": celda_paridad, "COBERTURA": celda_cobertura}


def _reporte_degradado(
    match_id: str, temporada: str, status: str, motivo: str,
    fixture: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Reporte íntegro y serializable cuando la evidencia no permite evaluar el contexto."""
    return {
        "nodos_gobernanza": list(NODOS_GOBIERNO),
        "sandbox": "CONTEXTO_SHOCKS_DIM7",
        "modo": "SOLO_LECTURA",
        "temporada": str(temporada),
        "match": fixture or {"match_id": str(match_id)},
        "status": status,
        "motivo": motivo,
        "dimension_7_contexto": {},
        "vector_contextual": {},
        "fortaleza_plaza": {},
        "altitud": {},
        "calendario": {},
        "intensidades_proyectadas": {},
        "semaforos": {},
        "escritura_bd": False,
        "llamadas_red": False,
    }


def ejecutar_sandbox_contexto_partido(
    match_id: str,
    temporada: str = TEMPORADA_DEFAULT,
    q_mod_h: float = 1.0,
    q_mod_a: float = 1.0,
) -> Dict[str, Any]:
    """Cadena completa de la Dimensión 7 para un fixture de la cartelera 3NF.

    Secuencia: cartelera 3NF (sólo lectura) → fixture + corte N−1 → altitudes del catálogo
    inmutable → V29/V30 + `AUX_*` → vector contextual (C_H, C_A) → λ selladas → semáforos.
    """
    gateway = PersistenceGateway()
    with gateway.read_session() as sesion:
        fixture = _leer_fixture(sesion, str(match_id))
        if fixture is None:
            return _reporte_degradado(
                str(match_id), temporada, "NO_ENCONTRADO",
                f"El fixture `{match_id}` no existe en `fixtures_snapshots` ni en `matches`.",
            )
        calendario = _catalogo_calendario(sesion)

    jornada = fixture.get("jornada")
    local_slug = str(fixture.get("local_slug") or "").lower().strip()
    visita_slug = str(fixture.get("visitante_slug") or "").lower().strip()
    if jornada is None or not local_slug or not visita_slug:
        return _reporte_degradado(
            str(match_id), temporada, "SIN_EVIDENCIA",
            "El fixture no publica jornada canónica o slugs de ambos clubes.", fixture,
        )

    kickoff = _parse_fecha(fixture.get("fecha_ref"))
    altitud_local = altitud_estadio(local_slug)
    altitud_visita = altitud_estadio(visita_slug)

    if kickoff is None:
        prev_local: Dict[str, Any] = {"encontrado": False, "motivo": "Sin fecha de kickoff."}
        prev_visita: Dict[str, Any] = {"encontrado": False, "motivo": "Sin fecha de kickoff."}
    else:
        prev_local = _partido_previo(calendario, local_slug, int(jornada), kickoff, str(match_id))
        prev_visita = _partido_previo(calendario, visita_slug, int(jornada), kickoff, str(match_id))

    dias_local = _dias_descanso(kickoff, prev_local)
    dias_visita = _dias_descanso(kickoff, prev_visita)

    ctx = calcular_vector_contextual_c(
        altitud_local, altitud_visita, dias_local, dias_visita,
        local_slug, q_mod_h=q_mod_h, q_mod_a=q_mod_a,
    )
    dimension_7 = _celdas_dimension_7(
        ctx, prev_local, prev_visita, dias_local, dias_visita,
        altitud_local, altitud_visita, q_mod_h, q_mod_a,
    )

    faltantes = [
        identificador for identificador in ("V30", "V29")
        if dimension_7[identificador]["estado"] != ESTADO_EVALUADO
    ]
    if not faltantes:
        status, motivo = "EXITO", "V29/V30 resueltas con evidencia fáctica del corte N−1."
    elif len(faltantes) == 1:
        status = "PARCIAL"
        motivo = f"Evidencia parcial: {faltantes[0]} sin sensor; su bono se publica como 0.0."
    else:
        status = "SIN_EVIDENCIA"
        motivo = "V30 y V29 sin evidencia: no se imputa ningún bono físico."

    semaforos = _semaforos_contexto(ctx, faltantes, altitud_local, altitud_visita)
    if status == "SIN_EVIDENCIA":
        semaforos["CTX"] = _semaforo(
            NIVEL_NEUTRAL, f"{semaforos['CTX']['detalle']} Semáforo CTX no concluyente."
        )

    ratio = (
        float(ctx["lambda_home"]) / float(ctx["lambda_away"])
        if float(ctx["lambda_away"]) > 0.0 else None
    )
    return {
        "nodos_gobernanza": list(NODOS_GOBIERNO),
        "sandbox": "CONTEXTO_SHOCKS_DIM7",
        "modo": "SOLO_LECTURA",
        "temporada": str(temporada),
        "match": {
            "match_id": fixture.get("match_id"),
            "jornada": int(jornada),
            "local": fixture.get("local"),
            "visitante": fixture.get("visitante"),
            "local_slug": local_slug,
            "visitante_slug": visita_slug,
            "fecha_ref": _fecha_iso(kickoff),
            "estado": fixture.get("estado"),
            "marcador": fixture.get("marcador"),
            "origen": fixture.get("origen"),
            "snapshot_actualizado": fixture.get("snapshot_actualizado"),
        },
        "corte_n_1": {
            "regla": "jornada < N ∧ estado terminal ∧ fecha < kickoff (futuro-ciego)",
            "jornada": int(jornada),
            "fuente_fechas": "fixtures_snapshots.matches_json[].fecha_dt",
            "partidos_en_calendario": len(calendario),
            "local": prev_local,
            "visita": prev_visita,
        },
        "altitud": {
            "local": {
                "slug": local_slug,
                "slug_canonico": _slug_canonico_altitud(local_slug),
                "msnm": altitud_local,
            },
            "visita": {
                "slug": visita_slug,
                "slug_canonico": _slug_canonico_altitud(visita_slug),
                "msnm": altitud_visita,
            },
            "catalogo": "CATALOGO_ALTITUDES_LIGAMX [LN-QBE-109]",
            "delta_altitud_metros": ctx["delta_altitud_metros"],
        },
        "calendario": {
            "local": {"dias_descanso": dias_local, **prev_local},
            "visita": {"dias_descanso": dias_visita, **prev_visita},
        },
        "fortaleza_plaza": {
            "slug": local_slug,
            "bono": ctx["bono_plaza"],
            "techo": 0.1000,
            "catalogo": "CONSTANTS §2 · [LN-QBE-038] (delegado: obtener_bono_fortaleza_plaza)",
        },
        "dimension_7_contexto": dimension_7,
        "vector_contextual": {
            **ctx,
            "q_mod_h_solicitado": _r(q_mod_h, 4),
            "q_mod_a_solicitado": _r(q_mod_a, 4),
            "ecuacion_gamma": (
                f"γ = {GAMMA_BASE:.4f} + plaza {ctx['bono_plaza']:+.4f} + alt "
                f"{ctx['bono_altitud']:+.4f} + rec {ctx['bono_descanso']:+.4f} = "
                f"{ctx['gamma_contextual']:.4f}"
            ),
            "ecuacion_contexto": (
                f"ΔContexto = {GAMMA_BASE:.4f} + C_H {ctx['C_H']:+.4f} − C_A "
                f"{ctx['C_A']:+.4f} = {ctx['delta_contexto']:.4f}"
            ),
        },
        "intensidades_proyectadas": {
            "canal": "CONTEXTUAL AISLADO (A_H = D_A = A_A = D_H = 0)",
            "lambda_home": ctx["lambda_home"],
            "lambda_away": ctx["lambda_away"],
            "ratio_ofensivo": _r(ratio, 4),
            "alpha_ligadura": ctx["alpha_ligadura"],
            "gamma_home_base": GAMMA_BASE,
            "gamma_contextual": ctx["gamma_contextual"],
            "C_H": ctx["C_H"],
            "C_A": ctx["C_A"],
            "delta_contexto": ctx["delta_contexto"],
            "mu_liga": MU_LIGA_DEFAULT,
            "kappa_net": KAPPA_NET,
            "cotas_fisicas": [LAMBDA_MIN, LAMBDA_MAX],
            "en_cota": LAMBDA_MIN <= min(float(ctx["lambda_home"]), float(ctx["lambda_away"]))
            and max(float(ctx["lambda_home"]), float(ctx["lambda_away"])) <= LAMBDA_MAX,
            "paridad_motor": ctx["paridad_motor"],
            "ecuacion_local": (
                f"ln λ_H = α {ctx['alpha_ligadura']:+.6f} + γ {ctx['gamma_contextual']:.4f} "
                f"+ ln Q_H {math.log(float(ctx['q_mod_h'])):+.4f}"
            ),
            "ecuacion_visita": (
                f"ln λ_A = α {ctx['alpha_ligadura']:+.6f} + ln Q_A "
                f"{math.log(float(ctx['q_mod_a'])):+.4f}"
            ),
            "nota": "λ emitidas VERBATIM por estimar_intensidades_loglineal [VAULT-CORE-001].",
        },
        "semaforos": semaforos,
        "status": status,
        "motivo": motivo,
        "escritura_bd": False,
        "llamadas_red": False,
    }


# ═════════════════════════════════════════════════════════════════════════════════════════════
# MODO JORNADA (barrido de la cartelera completa, mismo motor sellado)
# ═════════════════════════════════════════════════════════════════════════════════════════════
def _ids_de_jornada(sesion: Any, jornada: int) -> List[str]:
    """IDs de la jornada desde el snapshot más reciente; fallback a la tabla `matches`."""
    consulta = (
        select(FixtureSnapshot)
        .where(FixtureSnapshot.matchday == int(jornada))
        .order_by(FixtureSnapshot.updated_at.desc(), FixtureSnapshot.id.desc())
    )
    for snapshot in sesion.execute(consulta).scalars().all():
        identificadores: List[str] = []
        for entrada in _entradas_snapshot(snapshot):
            ident = str(entrada.get("id_partido") or "")
            if ident and ident not in identificadores:
                identificadores.append(ident)
        if identificadores:
            return identificadores
    filas = sesion.execute(
        select(Match).where(Match.matchday_num == int(jornada)).order_by(Match.id)
    ).scalars().all()
    return [str(fila.id) for fila in filas]


def ejecutar_sandbox_contexto_jornada(
    jornada: int,
    temporada: str = TEMPORADA_DEFAULT,
    q_mod_h: float = 1.0,
    q_mod_a: float = 1.0,
) -> Dict[str, Any]:
    """Barrido soberano de la jornada: un reporte por fixture + conteo de estados."""
    gateway = PersistenceGateway()
    with gateway.read_session() as sesion:
        identificadores = _ids_de_jornada(sesion, jornada)

    reportes = [
        ejecutar_sandbox_contexto_partido(ident, temporada, q_mod_h, q_mod_a)
        for ident in identificadores
    ]
    conteo = {"EXITO": 0, "PARCIAL": 0, "SIN_EVIDENCIA": 0, "NO_ENCONTRADO": 0}
    for reporte in reportes:
        estado = str(reporte.get("status") or "NO_ENCONTRADO")
        conteo[estado] = conteo.get(estado, 0) + 1
    return {
        "nodos_gobernanza": list(NODOS_GOBIERNO),
        "sandbox": "CONTEXTO_SHOCKS_DIM7_JORNADA",
        "modo": "SOLO_LECTURA",
        "temporada": str(temporada),
        "jornada": int(jornada),
        "total_partidos": len(reportes),
        "conteo_estados": conteo,
        "partidos": reportes,
        "escritura_bd": False,
        "llamadas_red": False,
    }


# ═════════════════════════════════════════════════════════════════════════════════════════════
# [ARCH-1.4.48] TABLERO ASCII DE CONSOLA (presentación pura, cero cálculo)
# ═════════════════════════════════════════════════════════════════════════════════════════════
def _ancho_visible(texto: str) -> int:
    """Ancho de desplazamiento en terminal (glifos anchos y emoji cuentan 2 columnas)."""
    ancho = 0
    for caracter in texto:
        codigo = ord(caracter)
        if codigo in (0xFE0F, 0x200D) or 0x0300 <= codigo <= 0x036F:
            continue
        if (
            0x1F000 <= codigo <= 0x1FAFF
            or 0x2600 <= codigo <= 0x27BF
            or 0x2B00 <= codigo <= 0x2BFF
            or 0x2E80 <= codigo <= 0xA4CF
        ):
            ancho += 2
        else:
            ancho += 1
    return ancho


def _pad(texto: str, ancho: int) -> str:
    """Relleno derecho por ancho VISIBLE (no por longitud de cadena)."""
    relleno = max(0, ancho - _ancho_visible(texto))
    return texto + (" " * relleno)


def _recortar(texto: str, ancho: int) -> str:
    """Recorta a ancho visible (red de seguridad para no romper el borde de la caja)."""
    if _ancho_visible(texto) <= ancho:
        return texto
    salida = ""
    for caracter in texto:
        if _ancho_visible(salida + caracter) > ancho - 1:
            break
        salida += caracter
    return salida + "…"


def _caja(titulo: str, filas: Sequence[str]) -> None:
    """Caja ASCII/Unicode de ancho fijo (94 columnas) con título embebido."""
    interior = ANCHO_TABLERO - 2
    encabezado = f"─ {titulo} "
    print("┌" + encabezado + ("─" * max(0, interior - _ancho_visible(encabezado))) + "┐")
    for fila in filas:
        print("│ " + _pad(_recortar(fila, interior - 2), interior - 2) + " │")
    print("└" + ("─" * interior) + "┘")


def _linea(etiqueta: str, texto: str) -> str:
    """Fila etiqueta/valor del bloque de contexto (etiqueta alineada en 10 columnas)."""
    return f"{_pad(etiqueta, 10)}{texto}"


def _num(valor: Optional[float], decimales: int = 4, ancho: int = 8) -> str:
    """Formato numérico con signo y ancho fijo; `—` cuando la evidencia no existe."""
    if valor is None:
        return "—".rjust(ancho)
    return f"{float(valor):+.{decimales}f}".rjust(ancho)


def _envolver(texto: str, ancho: int = ANCHO_TABLERO - 14) -> List[str]:
    """Envuelve texto largo respetando palabras (sin dependencias externas)."""
    palabras = str(texto).split()
    lineas: List[str] = []
    actual = ""
    for palabra in palabras:
        candidata = f"{actual} {palabra}".strip()
        if _ancho_visible(candidata) <= ancho:
            actual = candidata
            continue
        if actual:
            lineas.append(actual)
        actual = palabra
    if actual:
        lineas.append(actual)
    return lineas or [""]


def _glifo_celda(celda: Dict[str, Any]) -> str:
    return GLIFO.get(str(celda.get("estado")), "·")


def _encabezado_contexto() -> str:
    return (
        f"{_pad('ID', 5)}{_pad('VARIABLE', 34)}{_pad('UNIDAD', 9)}"
        f"{'LOCAL'.rjust(12)}{'VISITA'.rjust(12)}  ESTADO"
    )


def _fila_contexto(celda: Dict[str, Any]) -> str:
    return (
        f"{_pad(str(celda['id']), 5)}"
        f"{_pad(str(celda['variable'])[:33], 34)}"
        f"{_pad(str(celda['unidad']), 9)}"
        f"{str(celda.get('local') or '—').rjust(12)}"
        f"{str(celda.get('visita') or '—').rjust(12)}"
        f"  {_glifo_celda(celda)} {celda['estado']}"
    )


def _bloque_contexto_experimento(reporte: Dict[str, Any]) -> None:
    """Caja 1: identidad del experimento, corte N−1 y procedencia de la fecha."""
    fixture = reporte.get("match") or {}
    corte = reporte.get("corte_n_1") or {}
    filas: List[str] = [
        _linea("FIXTURE", f"{fixture.get('match_id')} · Jornada {fixture.get('jornada')} · "
                          f"{fixture.get('estado') or '—'}"
                          f"{(' · ' + str(fixture.get('marcador'))) if fixture.get('marcador') else ''}"),
        _linea("DUELO", f"{fixture.get('local') or '—'} (L)  vs  {fixture.get('visitante') or '—'} (V)"),
        _linea("KICKOFF", f"{fixture.get('fecha_ref') or '—'} · origen {fixture.get('origen') or '—'}"),
        _linea("REGLA", str(corte.get("regla") or "Corte futuro-ciego N−1")),
        _linea("FECHAS", f"{corte.get('fuente_fechas') or '—'} · "
                         f"{corte.get('partidos_en_calendario', 0)} fixtures en cartelera"),
        _linea("MODELO", "DIM 7 (T_Shk V29/V30 + AUX) → (C_H, C_A) → λ [VAULT-CORE-001]"),
    ]
    filas.append("")
    trozos = _envolver(f"{reporte.get('status')} — {reporte.get('motivo')}")
    filas.append(_linea("ESTADO", trozos[0]))
    for trozo in trozos[1:]:
        filas.append(_linea("", trozo))
    _caja("CONTEXTO DEL EXPERIMENTO", filas)


def _bloque_dimension_7(reporte: Dict[str, Any]) -> None:
    """Caja 2: tabla V29/V30 + `AUX_*` (local · visita · estado) con pie de cobertura."""
    dimension = reporte.get("dimension_7_contexto") or {}
    if not dimension:
        _caja("DIM 7 · SHOCKS DE CONTEXTO (T_Shk · V29/V30 + AUX) [LN-QBE-109]", [
            "NO EVALUADA: el fixture no publica evidencia suficiente.",
            f"Motivo: {reporte.get('motivo')}",
        ])
        return
    filas: List[str] = [_encabezado_contexto(), "─" * (ANCHO_TABLERO - 4)]
    evaluadas = 0
    for identificador in sorted(dimension.keys()):
        celda = dimension[identificador]
        filas.append(_fila_contexto(celda))
        if celda.get("estado") == ESTADO_EVALUADO:
            evaluadas += 1
    filas.append("─" * (ANCHO_TABLERO - 4))
    filas.append(
        f"Evaluadas {evaluadas}/{len(dimension)} · ⚪ SIN EVIDENCIA = sensor ausente; "
        f"jamás se imputa una cifra."
    )
    _caja("DIM 7 · SHOCKS DE CONTEXTO (T_Shk · V29/V30 + AUX) [LN-QBE-109]", filas)


def _bloque_altitud(reporte: Dict[str, Any]) -> None:
    """Caja 3: V29 — ventaja hipóxica unidireccional."""
    altitud = reporte.get("altitud") or {}
    ctx = reporte.get("vector_contextual") or {}
    local = altitud.get("local") or {}
    visita = altitud.get("visita") or {}
    if not altitud:
        _caja("V29 · ALTITUD FISIOLÓGICA (unidireccional)", ["NO EVALUADA."])
        return
    filas: List[str] = [
        f"{_pad('BANDO', 22)}{_pad('SLUG VIVO', 24)}{_pad('CATÁLOGO', 24)}{'MSNM'.rjust(8)}",
        "─" * (ANCHO_TABLERO - 4),
        f"{_pad('LOCAL', 22)}{_pad(str(local.get('slug') or '—'), 24)}"
        f"{_pad(str(local.get('slug_canonico') or 'NO CATALOGADO'), 24)}"
        f"{_num(local.get('msnm'), 0, 8)}",
        f"{_pad('VISITA', 22)}{_pad(str(visita.get('slug') or '—'), 24)}"
        f"{_pad(str(visita.get('slug_canonico') or 'NO CATALOGADO'), 24)}"
        f"{_num(visita.get('msnm'), 0, 8)}",
        "─" * (ANCHO_TABLERO - 4),
    ]
    if local.get("msnm") is None or visita.get("msnm") is None:
        filas.append("⚪ SIN EVIDENCIA: club fuera del catálogo inmutable ⇒ bono de altitud = 0.0000.")
    else:
        filas.append(
            f"ΔAlt⁺ = max(0, {float(local['msnm']):.0f} − {float(visita['msnm']):.0f}) = "
            f"{float(ctx.get('delta_altitud_metros') or 0.0):.0f} m  →  "
            f"Bono = {BETA_ALTITUD:.4f} × Δ/1000 = {float(ctx.get('bono_altitud') or 0.0):+.4f}"
        )
        filas.append("Axioma: sólo bonifica jugar MÁS ALTO; la altura menor no penaliza al local.")
    _caja("V29 · ALTITUD FISIOLÓGICA (unidireccional)", filas)


def _bloque_calendario(reporte: Dict[str, Any]) -> None:
    """Caja 4: V30 — fatiga de calendario y descanso real del corte N−1."""
    calendario = reporte.get("calendario") or {}
    ctx = reporte.get("vector_contextual") or {}
    if not calendario:
        _caja("V30 · FATIGA DE CALENDARIO (corte N−1)", ["NO EVALUADA."])
        return
    filas: List[str] = [
        f"{_pad('BANDO', 12)}{_pad('PARTIDO PREVIO', 18)}{_pad('J', 4)}{_pad('FECHA', 22)}"
        f"{_pad('COND', 8)}{'DÍAS'.rjust(8)}{'TOPE'.rjust(8)}",
        "─" * (ANCHO_TABLERO - 4),
    ]
    for bando, clave in (("LOCAL", "local"), ("VISITA", "visita")):
        previo = calendario.get(clave) or {}
        filas.append(
            f"{_pad(bando, 12)}"
            f"{_pad(str(previo.get('match_id') or '—'), 18)}"
            f"{_pad(str(previo.get('jornada') or '—'), 4)}"
            f"{_pad(str(previo.get('fecha') or '—'), 22)}"
            f"{_pad(str(previo.get('condicion') or '—'), 8)}"
            f"{_num(previo.get('dias_descanso'), 0, 8)}"
            f"{_num(DESCANSO_TOPE_DIAS, 0, 8)}"
        )
    filas.append("─" * (ANCHO_TABLERO - 4))
    if ctx.get("descanso_evaluado"):
        filas.append(
            f"ΔDescanso = {float(ctx['delta_descanso_dias']):+.1f} d → "
            f"clamp ±{DESCANSO_CLAMP_DIAS:.0f} d → {float(ctx['delta_descanso_clamped']):+.1f} d "
            f"→ Bono = {BETA_DESCANSO:.4f} × Δ = {float(ctx['bono_descanso']):+.4f}"
        )
        filas.append("Días_T = min(14, (kickoff − previo).days) · corte futuro-ciego N−1.")
    else:
        previo_local = calendario.get("local") or {}
        filas.append(
            "⚪ SIN EVIDENCIA: "
            + str(previo_local.get("motivo") or "falta fecha de kickoff o previo terminal.")
            + " Bono de descanso = 0.0000 (no imputado)."
        )
    _caja("V30 · FATIGA DE CALENDARIO (corte N−1)", filas)


def _bloque_plaza_shocks(reporte: Dict[str, Any]) -> None:
    """Caja 5: fortaleza de plaza [LN-QBE-038] y shocks de plantilla `AUX_Q_MOD_H`/`AUX_Q_MOD_A`."""
    plaza = reporte.get("fortaleza_plaza") or {}
    dimension = reporte.get("dimension_7_contexto") or {}
    ctx = reporte.get("vector_contextual") or {}
    if not plaza:
        _caja("PLAZA & SHOCKS DE PLANTILLA (AUX_Q_MOD_H/AUX_Q_MOD_A)", ["NO EVALUADO."])
        return
    shocks = [dimension.get("AUX_Q_MOD_H") or {}, dimension.get("AUX_Q_MOD_A") or {}]
    filas: List[str] = [
        _linea("PLAZA", f"{plaza.get('slug') or '—'} · Δγ_plaza = "
                        f"{float(plaza.get('bono') or 0.0):+.4f} (techo {float(plaza.get('techo') or 0.1):.2f})"),
        _linea("CATÁLOGO", str(plaza.get("catalogo") or "—")),
        "─" * (ANCHO_TABLERO - 4),
        f"{_pad('VAR', 5)}{_pad('SHOCK', 34)}{_pad('MERMA', 10)}{'Q_MOD'.rjust(10)}  ESTADO",
    ]
    for celda, q_mod in ((shocks[0], ctx.get("q_mod_h")), (shocks[1], ctx.get("q_mod_a"))):
        filas.append(
            f"{_pad(str(celda.get('id') or '—'), 5)}"
            f"{_pad(str(celda.get('variable') or '—')[:33], 34)}"
            f"{_pad(str(celda.get('local') if celda.get('id') == 'AUX_Q_MOD_H' else celda.get('visita')), 10)}"
            f"{_num(q_mod, 4, 10)}  🟢 {celda.get('estado') or '—'}"
        )
    filas.append("─" * (ANCHO_TABLERO - 4))
    filas.append("Sin reporte médico auditado ⇒ Q_mod = 1.0000 (SIN SHOCK): se prohíbe inventar bajas.")
    filas.append("El shock inyectado por CLI es una HIPÓTESIS del operador, no evidencia.")
    _caja("PLAZA & SHOCKS DE PLANTILLA (AUX_Q_MOD_H/AUX_Q_MOD_A)", filas)


def _bloque_vector_contextual(reporte: Dict[str, Any]) -> None:
    """Caja 6: vector contextual neto y su proyección sobre λ (motor sellado)."""
    ctx = reporte.get("vector_contextual") or {}
    intensidades = reporte.get("intensidades_proyectadas") or {}
    if not ctx or not intensidades:
        _caja("VECTOR CONTEXTUAL NETO (C_H, C_A)", [
            "NO EVALUADO: sin evidencia de contexto para este fixture.",
        ])
        return
    filas: List[str] = [
        _linea("GAMMA", str(ctx.get("ecuacion_gamma") or "—")),
        _linea("NETO", str(ctx.get("ecuacion_contexto") or "—")),
        "─" * (ANCHO_TABLERO - 4),
        f"{_pad('COMPONENTE', 26)}{_pad('VALOR', 14)}{_pad('ORIGEN', 38)}LECTURA",
        "─" * (ANCHO_TABLERO - 4),
        f"{_pad('Δγ_plaza', 26)}{_num(ctx.get('bono_plaza'), 4, 14)}"
        f"{_pad('[LN-QBE-038]', 38)}{'catálogo sellado'}",
        f"{_pad('Bono altitud (V29)', 26)}{_num(ctx.get('bono_altitud'), 4, 14)}"
        f"{_pad('0.03 · ΔAlt⁺/1000', 38)}{'unidireccional'}",
        f"{_pad('Bono descanso (V30)', 26)}{_num(ctx.get('bono_descanso'), 4, 14)}"
        f"{_pad('0.02 · clamp(Δ, ±3)', 38)}{'futuro-ciego N−1'}",
        f"{_pad('ln Q_mod,H (AUX_Q_MOD_H)', 26)}{_num(math.log(float(ctx.get('q_mod_h') or 1.0)), 4, 14)}"
        f"{_pad('clamp [0.90, 1.05]', 38)}{'sin reporte = 1.0'}",
        f"{_pad('ln Q_mod,A (V26)', 26)}{_num(math.log(float(ctx.get('q_mod_a') or 1.0)), 4, 14)}"
        f"{_pad('clamp [0.90, 1.05]', 38)}{'sin reporte = 1.0'}",
        "─" * (ANCHO_TABLERO - 4),
        f"{_pad('C_H (ventaja local)', 26)}{_num(ctx.get('C_H'), 4, 14)}"
        f"{_pad('γ_ctx − γ̄ + ln Q_H', 38)}{'compuesta'}",
        f"{_pad('C_A (shock visita)', 26)}{_num(ctx.get('C_A'), 4, 14)}"
        f"{_pad('ln Q_A', 38)}{'visitante'}",
        f"{_pad('ΔContexto', 26)}{_num(ctx.get('delta_contexto'), 4, 14)}"
        f"{_pad('γ̄_base + C_H − C_A', 38)}{'ventaja territorial'}",
        "─" * (ANCHO_TABLERO - 4),
        f"{_pad('λ_H (motor)', 26)}{_num(intensidades.get('lambda_home'), 4, 14)}"
        f"{_pad('estimar_intensidades_loglineal', 38)}{'[VAULT-CORE-001]'}",
        f"{_pad('λ_A (motor)', 26)}{_num(intensidades.get('lambda_away'), 4, 14)}"
        f"{_pad('estimar_intensidades_loglineal', 38)}{'[VAULT-CORE-001]'}",
        f"{_pad('λ_H / λ_A', 26)}{_num(intensidades.get('ratio_ofensivo'), 4, 14)}"
        f"{_pad('canal contextual aislado', 38)}"
        f"{'en cota' if intensidades.get('en_cota') else 'FUERA DE COTA'}",
        "─" * (ANCHO_TABLERO - 4),
    ]
    filas.extend(_envolver(
        "El sandbox publica el desglose; las λ sólo las emite el plano sellado. "
        f"Residuo de paridad = {float(ctx.get('paridad_motor') or 0.0):.2e}."
    ))
    _caja("VECTOR CONTEXTUAL NETO (C_H, C_A) → λ", filas)


def _bloque_semaforos_contexto(reporte: Dict[str, Any]) -> None:
    """Caja 7: salud fiduciaria del experimento (CTX · paridad · cobertura)."""
    semaforos = reporte.get("semaforos") or {}
    filas: List[str] = []
    for nombre, celda in semaforos.items():
        detalle = _envolver(str(celda.get("detalle") or ""), ANCHO_TABLERO - 34)
        filas.append(f"{celda.get('glifo', '·')} {_pad(nombre, 22)}{detalle[0]}")
        for extra in detalle[1:]:
            filas.append(f"   {_pad('', 22)}{extra}")
    if not filas:
        filas.append("Sin semáforos publicados.")
    _caja("SEMÁFOROS DE SALUD", filas)


def imprimir_tablero_contexto_consola(reporte: Dict[str, Any]) -> None:
    """Renderiza el tablero completo de un partido ([ARCH-1.4.48]). Presentación pura."""
    print()
    _caja("Q-BE · LABORATORIO CONTEXTO & SHOCKS · DIM 7 (T_Shk · V29/V30 + AUX)", [
        f"[{NODOS_GOBIERNO[0]}] / [{NODOS_GOBIERNO[1]}] · SÓLO LECTURA · corte N−1 (futuro-ciego)",
        f"γ̄_base = {GAMMA_BASE:.4f} · β_alt = {BETA_ALTITUD:.4f} · β_rec = {BETA_DESCANSO:.4f} · "
        f"clamp Q ∈ [{Q_MOD_MIN:.2f}, {Q_MOD_MAX:.2f}]",
        f"Techo contextual ‖C‖max = {NORMA_CONTEXTO_MAX:.4f} · motor [VAULT-CORE-001] inmutable",
    ])
    _bloque_contexto_experimento(reporte)
    _bloque_dimension_7(reporte)
    _bloque_altitud(reporte)
    _bloque_calendario(reporte)
    _bloque_plaza_shocks(reporte)
    _bloque_vector_contextual(reporte)
    _bloque_semaforos_contexto(reporte)
    print("─" * ANCHO_TABLERO)
    print(
        " Sólo lectura · 0 escrituras en la bóveda · 0 llamadas de red · "
        f"nodos {' + '.join(NODOS_GOBIERNO)}"
    )
    print()


def imprimir_tablero_jornada_contexto_consola(resumen: Dict[str, Any]) -> None:
    """Tablero compacto de la jornada: ΔAlt⁺, ΔDescanso, C_H y C_A por fixture."""
    jornada = resumen.get("jornada")
    conteo = resumen.get("conteo_estados") or {}
    glifos = {"EXITO": "🟢", "PARCIAL": "🟡", "SIN_EVIDENCIA": "⚪", "NO_ENCONTRADO": "⚫"}
    print()
    _caja(f"JORNADA {jornada} · CONTEXTO & SHOCKS [LN-QBE-109]", [
        f"[{NODOS_GOBIERNO[0]}] / [{NODOS_GOBIERNO[1]}] · SÓLO LECTURA · "
        f"temporada {resumen.get('temporada')} · {resumen.get('total_partidos')} fixtures",
        " · ".join(
            f"{glifos.get(estado, '·')} {estado}: {cantidad}"
            for estado, cantidad in conteo.items()
        ),
    ])

    filas: List[str] = [
        f"{_pad('FIXTURE', 14)}{_pad('LOCAL', 16)}{_pad('VISITA', 16)}"
        f"{'ΔALT⁺'.rjust(8)}{'B_ALT'.rjust(8)}{'ΔDESC'.rjust(7)}{'C_H'.rjust(8)}{'C_A'.rjust(8)}  ST",
        "─" * (ANCHO_TABLERO - 4),
    ]
    for reporte in resumen.get("partidos") or []:
        fixture = reporte.get("match") or {}
        ctx = reporte.get("vector_contextual") or {}
        glifo = glifos.get(str(reporte.get("status") or "NO_ENCONTRADO"), "·")
        filas.append(
            f"{_pad(str(fixture.get('match_id') or '—')[:13], 14)}"
            f"{_pad(str(fixture.get('local') or '—')[:15], 16)}"
            f"{_pad(str(fixture.get('visitante') or '—')[:15], 16)}"
            f"{_num(ctx.get('delta_altitud_metros'), 0, 8)}"
            f"{_num(ctx.get('bono_altitud'), 4, 8)}"
            f"{_num(ctx.get('delta_descanso_dias'), 1, 7)}"
            f"{_num(ctx.get('C_H'), 4, 8)}"
            f"{_num(ctx.get('C_A'), 4, 8)}  {glifo}"
        )
    filas.append("─" * (ANCHO_TABLERO - 4))
    filas.append("ΔALT⁺ en metros · B_ALT bono de altitud · ΔDESC en días · Δ = — ⇒ SIN EVIDENCIA")
    _caja("MATRIZ CONTEXTUAL DE LA CARTELERA", filas)
    print("─" * ANCHO_TABLERO)
    print(
        " Sólo lectura · 0 escrituras en la bóveda · 0 llamadas de red · "
        f"nodos {' + '.join(NODOS_GOBIERNO)}"
    )
    print()


# ═════════════════════════════════════════════════════════════════════════════════════════════
# CLI
# ═════════════════════════════════════════════════════════════════════════════════════════════
def _construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sandbox_contexto_shocks_pipeline",
        description=(
            "[LN-QBE-109] / [ARCH-1.4.48] Laboratorio CLI de la Dimensión 7: "
            "altitud, descanso y shocks de plantilla → vector contextual (C_H, C_A)."
        ),
    )
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--partido", metavar="ID", help="ID canónico del fixture (ej. LIGAMX-J11-07).")
    grupo.add_argument("--jornada", type=int, metavar="N", help="Barrido completo de la jornada N.")
    parser.add_argument("--temporada", default=TEMPORADA_DEFAULT, help="Etiqueta de temporada (default 2026).")
    parser.add_argument("--json", action="store_true", dest="salida_json", help="Emite JSON serializable.")
    parser.add_argument("--verbose", action="store_true", help="Activa logging DEBUG.")
    parser.add_argument(
        "--q-mod-h", type=float, default=1.0, dest="q_mod_h", metavar="Q",
        help="Shock ofensivo del local AUX_Q_MOD_H (default 1.00 = SIN SHOCK; clamp [0.90, 1.05]).",
    )
    parser.add_argument(
        "--q-mod-a", type=float, default=1.0, dest="q_mod_a", metavar="Q",
        help="Shock defensivo de la visita V26 (default 1.00 = SIN SHOCK; clamp [0.90, 1.05]).",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Punto de entrada CLI. Sólo lectura; jamás escribe en la bóveda ni abre red."""
    argumentos = _construir_parser().parse_args(list(argv) if argv is not None else None)
    logging.basicConfig(
        level=logging.DEBUG if argumentos.verbose else logging.WARNING,
        format="%(asctime)s · %(levelname)s · %(name)s · %(message)s",
    )
    try:
        if argumentos.partido:
            reporte = ejecutar_sandbox_contexto_partido(
                argumentos.partido, argumentos.temporada,
                q_mod_h=argumentos.q_mod_h, q_mod_a=argumentos.q_mod_a,
            )
            if argumentos.salida_json:
                print(json.dumps(reporte, ensure_ascii=False, indent=2, default=str))
            else:
                imprimir_tablero_contexto_consola(reporte)
            return 0 if reporte.get("status") != "NO_ENCONTRADO" else 2

        resumen = ejecutar_sandbox_contexto_jornada(
            int(argumentos.jornada), argumentos.temporada,
            q_mod_h=argumentos.q_mod_h, q_mod_a=argumentos.q_mod_a,
        )
        if argumentos.salida_json:
            print(json.dumps(resumen, ensure_ascii=False, indent=2, default=str))
        else:
            imprimir_tablero_jornada_contexto_consola(resumen)
        return 0

    except Exception as exc:  # pragma: no cover - red de seguridad CLI
        logger.exception("Fallo del laboratorio de contexto: %s", exc)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
