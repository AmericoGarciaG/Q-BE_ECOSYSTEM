# -*- coding: utf-8 -*-
"""
[LN-QBE-108] / [ARCH-1.4.47] SANDBOX ATAQUE & DEFENSA — PIPELINE AUTÓNOMO CLI-FIRST.

Misión
------
Aislar en consola el núcleo de mayor peso de la distribución soberana (>70 % de λ): la
Calidad de Remate (Dimensión 2, 𝒯_Rem, V06-V09) y la Contención Defensiva (Dimensión 3,
𝒯_Def, V12-V16). Ejecuta la cadena REAL —corte N−1 de la 3NF + caché Opta congelada →
factores estructurales → colisión cruzada → intensidades log-lineales → tablero ASCII—
sin FastAPI, sin DOM y sin Playwright.

Régimen: `[HÍBRIDO DUAL-TRACK]`
* `[DIRGEN-STRICT]`: los factores (A_H, D_A, A_A, D_H) y las intensidades (λ_H, λ_A) NO se
  reimplementan: se invocan VERBATIM `derivar_factores_estructurales` [VAULT-CORE-005] y
  `estimar_intensidades_loglineal` [VAULT-CORE-001].
* `[DBBD-FUNGIBLE]`: composición del corte, CLI (`--partido` / `--jornada` / `--temporada`
  / `--json`), tablero y semáforos.

Axiomas operativos
------------------
1. **Sólo lectura:** `PersistenceGateway.read_session()` y `json.load` del corpus congelado.
   Prohibido escribir en `data/qbe_database.db`; prohibido abrir red.
2. **Futuro-ceguera (N−1):** el corte de cada club son los partidos con `matchday_num < N`
   en estado terminal. El fixture evaluado jamás alimenta su propia acumulación.
3. **Cobertura íntegra [ARCH-1.4.39]:** si a UN partido del corte le falta la métrica Opta,
   ese club-corte NO publica `npxG/90` (se degrada completo). Jamás se mezclan fuentes ni se
   inventan cifras `[GOVERNANCE-01]`.
4. **Contrato homologado (Decreto `VAR-2026-J7-HOMOLOGACION` §E1):** el `raw_match_data` que
   alimenta el motor publica `xg` y NUNCA `xga`; el xGA sólo se exhibe como evidencia.
   Publicarlo invertía el diagnóstico defensivo medido (0.5102 → 0.4825).
5. **Bipartita simétrica:** las celdas de 𝒯_Rem/𝒯_Def son independientes por club (`local`, `visita`); el choque
   ocurre sólo en la ecuación log-lineal, jamás restando ataques.

Uso:
    python -m scripts.laboratorio.sandbox_ataque_defensa_pipeline --partido LIGAMX-J11-07
    python -m scripts.laboratorio.sandbox_ataque_defensa_pipeline --jornada 11
    python -m scripts.laboratorio.sandbox_ataque_defensa_pipeline --partido LIGAMX-J11-07 --json
    python -m scripts.laboratorio.sandbox_ataque_defensa_pipeline --jornada 11 --temporada 2026
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy import or_, select

# ── Planos sellados (cero reimplementación de fórmulas) ─────────────────────────────────────
from src.core.intensity_canonical_loglink import (
    KAPPA_NET,
    calcular_alpha_ligadura,
    estimar_intensidades_loglineal,
    obtener_bono_fortaleza_plaza,
)
from src.observatory.core.factor_attribution import derivar_taxonomia
from src.core.sovereign_pipeline import derivar_factores_estructurales
from src.storage.gateway import PersistenceGateway
from src.storage.models import FixtureSnapshot, Match, MatchTelemetry

logger = logging.getLogger("SandboxAtaqueDefensa")

# ── Constantes legisladas y de presentación ─────────────────────────────────────────────────
RUTA_CACHE_OPTA_PLANTILLA = os.path.join("data", "cache_optaxg_liga_mx_{temporada}.json")
TEMPORADA_DEFAULT = "2026"
MU_LIGA_DEFAULT = 2.65                       # [CONSTANTS] media de goles de la competición
GAMMA_HOME_DEFAULT = 0.15                    # [LN-QBE-038] ventaja base de localía
LAMBDA_MIN, LAMBDA_MAX = 0.15, 4.50          # Invariante I6 (positividad estricta acotada)
PJ_MINIMO_SPLITS_SEDE = 3                    # [LN-QBE-038] suficiencia mínima de splits

ESTADO_EVALUADO = "EVALUADO"
ESTADO_SIN_EVIDENCIA = "SIN EVIDENCIA"
ESTADOS_TERMINALES = ("FINALIZADO", "FINISHED")
NIVEL_VERDE = "VERDE"
NIVEL_AMARILLO = "AMARILLO"
NIVEL_NEUTRAL = "NEUTRAL"
GLIFO = {
    NIVEL_VERDE: "🟢", NIVEL_AMARILLO: "🟡", NIVEL_NEUTRAL: "⚪",
    ESTADO_EVALUADO: "🟢", ESTADO_SIN_EVIDENCIA: "⚪",
}
ANCHO_TABLERO = 94

# ── Taxonomía bipartita de las dimensiones nucleares ([LN-QBE-122] · 𝒯_Rem / 𝒯_Def) ──────────
# [LN-QBE-122] NOMBRE y ORDEN vienen del catálogo único `[LN-QBE-120]`; aquí sólo viven la unidad
# canónica y la nota de procedencia. `AUX_*` = magnitud sin celda (jamás usurpa un `VXX`).
_LOCALES_DIM_2: Dict[str, Tuple[str, str, str]] = {
    "V06": ("xG por Partido (ancla npxG)", "xG/PJ",
            "xG Opta de shotmap por partido del corte N−1 (acumulado del club / PJ)."),
    "V07": ("Tiros al Arco por Partido (SoT)", "SoT/PJ",
            "SoT por partido; fuente: match_telemetry 3NF (hoy vacía) / caché congelada."),
    "AUX_XGOT_90": ("xG a puerta (xGOT)", "xGOT/90",
                    "SIN EVIDENCIA (FASE 6): el sensor congelado no publica xGOT. No se simula."),
    "V08": ("Big Chances Creadas", "BC/PJ",
            "SIN EVIDENCIA (FASE 6): el sensor congelado no publica big chances creadas."),
    "V09": ("Big Chances Falladas", "BC/PJ",
            "SIN EVIDENCIA (FASE 6): el sensor congelado no publica big chances falladas."),
}
_LOCALES_DIM_3: Dict[str, Tuple[str, str, str]] = {
    "V12": ("xGA por Partido (ancla defensiva)", "xGA/PJ",
            "xGA Opta de shotmap por partido del corte N−1 (evidencia exhibida, no insumo del motor)."),
    "V13": ("Tiros al Arco Recibidos por Partido (SoTA)", "SoTA/PJ",
            "SoTA por partido; fuente: match_telemetry 3NF (hoy vacía) / caché congelada."),
    "AUX_PPDA": ("PPDA (presión defensiva)", "índice",
                 "SIN EVIDENCIA (FASE 6): el sensor congelado no publica PPDA."),
    "V15": ("Intercepciones por Partido", "rec/PJ",
            "SIN EVIDENCIA (FASE 6): el sensor congelado no publica recuperaciones."),
    "V16": ("Big Chances Concedidas", "BC/PJ",
            "SIN EVIDENCIA (FASE 6): el sensor congelado no publica big chances concedidas."),
}
_TAXONOMIA_DIM_2: Tuple[Tuple[str, str, str, str], ...] = derivar_taxonomia("𝒯_Rem", _LOCALES_DIM_2)
_TAXONOMIA_DIM_3: Tuple[Tuple[str, str, str, str], ...] = derivar_taxonomia("𝒯_Def", _LOCALES_DIM_3)
NOTA_FASE_6 = "SIN EVIDENCIA (FASE 6)"


def _celda(
    identificador: str,
    nombre: str,
    unidad: str,
    local: Optional[float],
    visita: Optional[float],
    nota: str,
) -> Dict[str, Any]:
    """Celda bipartita homogénea: `EVALUADO` sólo si AMBOS clubes publican magnitud real."""
    evaluada = local is not None and visita is not None
    return {
        "id": identificador,
        "variable": nombre,
        "unidad": unidad,
        "local": round(float(local), 4) if evaluada else None,
        "visita": round(float(visita), 4) if evaluada else None,
        "estado": ESTADO_EVALUADO if evaluada else ESTADO_SIN_EVIDENCIA,
        "nota": nota,
    }


def _tasa(total: Optional[float], pj: int) -> Optional[float]:
    """Tasa por partido (≈ por 90 min). `None` sin total o sin muestra: cero invención."""
    if total is None or pj <= 0:
        return None
    return float(total) / float(pj)


# ═════════════════════════════════════════════════════════════════════════════════════════════
# PROTOCOLO DE INGESTA FÁCTICA (caché congelada + telemetría 3NF, todo en SÓLO LECTURA)
# ═════════════════════════════════════════════════════════════════════════════════════════════
def ruta_cache_opta(temporada: str = TEMPORADA_DEFAULT) -> str:
    """Ruta absoluta del artefacto congelado `[ARCH-1.4.39]` para la temporada declarada."""
    return os.path.join(PROJECT_ROOT, RUTA_CACHE_OPTA_PLANTILLA.format(temporada=str(temporada)))


def cargar_cache_opta(temporada: str = TEMPORADA_DEFAULT) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Lee el corpus Opta congelado y publica su procedencia (`fuente`, `generado_at`, cobertura).

    Artefacto ausente o ilegible ⇒ mapa vacío + `disponible = False`: el reporte degrada de
    forma honesta a `SIN EVIDENCIA`. Jamás se fabrica una cifra para tapar la ausencia de feed.
    """
    ruta = ruta_cache_opta(temporada)
    meta: Dict[str, Any] = {
        "temporada": str(temporada),
        "ruta": os.path.relpath(ruta, PROJECT_ROOT).replace(os.sep, "/"),
        "disponible": False,
        "fuente": None,
        "generado_at": None,
        "partidos": 0,
        "error": None,
    }
    if not os.path.exists(ruta):
        meta["error"] = f"Artefacto congelado ausente: {meta['ruta']}"
        return {}, meta
    try:
        with open(ruta, "r", encoding="utf-8") as fh:
            artefacto = json.load(fh)
    except (OSError, ValueError) as exc:
        meta["error"] = f"{type(exc).__name__}: {exc}"
        return {}, meta
    partidos = artefacto.get("partidos") if isinstance(artefacto, dict) else None
    if not isinstance(partidos, dict):
        meta["error"] = "El artefacto no publica el mapa 'partidos'."
        return {}, meta
    meta.update({
        "disponible": True,
        "fuente": artefacto.get("fuente"),
        "generado_at": artefacto.get("generado_at"),
        "partidos": len(partidos),
    })
    return partidos, meta


def _registro_opta(cache: Dict[str, Any], match_id: str, lado: str) -> Dict[str, Any]:
    """Bloque `home` | `away` del partido en el corpus congelado; `{}` si no está publicado."""
    registro = cache.get(match_id)
    if not isinstance(registro, dict):
        return {}
    bloque = registro.get(lado)
    return bloque if isinstance(bloque, dict) else {}


def _magnitud(bloque: Dict[str, Any], clave: str) -> Optional[float]:
    """Magnitud numérica publicada; `None` si la clave no existe (cero conversión inventada)."""
    valor = bloque.get(clave)
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        return float(valor)
    return None


def _partidos_de_club(sesion: Any, slug: str, jornada_corte: int) -> List[Dict[str, Any]]:
    """Corte futuro-ciego N−1: partidos TERMINALES del club con `matchday_num < N`."""
    consulta = (
        select(Match)
        .where(
            Match.matchday_num.isnot(None),
            Match.matchday_num < int(jornada_corte),
            Match.status.in_(ESTADOS_TERMINALES),
            or_(Match.home_team_slug == slug, Match.away_team_slug == slug),
        )
        .order_by(Match.matchday_num, Match.id)
    )
    partidos: List[Dict[str, Any]] = []
    for registro in sesion.execute(consulta).scalars().all():
        es_local = registro.home_team_slug == slug
        goles_favor = registro.score_home if es_local else registro.score_away
        goles_contra = registro.score_away if es_local else registro.score_home
        if goles_favor is None or goles_contra is None:
            logger.warning("[LN-QBE-108] Partido sin marcador terminal: %s", registro.id)
            continue
        partidos.append({
            "match_id": str(registro.id),
            "jornada": int(registro.matchday_num or 0),
            "es_local": bool(es_local),
            "goles_favor": int(goles_favor),
            "goles_contra": int(goles_contra),
        })
    return partidos


def _bloque_sede(partidos: Sequence[Dict[str, Any]], es_local: bool) -> Dict[str, Any]:
    """Split de sede (`pj`, `gf`, `gc`, `pts`) exigido por `[LN-QBE-038]`; `{}` si está vacío."""
    tramo = [p for p in partidos if p["es_local"] is es_local]
    if not tramo:
        return {}
    return {
        "pj": len(tramo),
        "gf": sum(p["goles_favor"] for p in tramo),
        "gc": sum(p["goles_contra"] for p in tramo),
        "pts": sum(
            3 if p["goles_favor"] > p["goles_contra"] else (1 if p["goles_favor"] == p["goles_contra"] else 0)
            for p in tramo
        ),
    }


def _telemetria_de_club(sesion: Any, partidos: Sequence[Dict[str, Any]], slug: str) -> Dict[str, Any]:
    """Agrega SoT/SoTA desde `match_telemetry` (3NF) con la misma regla de cobertura íntegra."""
    ids = [p["match_id"] for p in partidos]
    resultado: Dict[str, Any] = {
        "fuente": "match_telemetry",
        "cubiertos": 0,
        "total": len(ids),
        "sot_total": None,
        "sota_total": None,
        "faltantes": list(ids),
    }
    if not ids:
        return resultado
    filas = sesion.execute(
        select(MatchTelemetry).where(
            MatchTelemetry.match_id.in_(ids),
            MatchTelemetry.team_slug == slug,
        )
    ).scalars().all()
    indice = {str(fila.match_id): fila for fila in filas}
    faltantes = [identificador for identificador in ids if identificador not in indice]
    resultado["cubiertos"] = len(ids) - len(faltantes)
    resultado["faltantes"] = faltantes
    if faltantes:
        # Cobertura incompleta ⇒ NO se publica la tasa: mezclar submuestras sesga el corte.
        return resultado
    sot = [float(fila.sot) for fila in indice.values() if fila.sot is not None]
    sota = [float(fila.sota) for fila in indice.values() if fila.sota is not None]
    if len(sot) != len(ids) or len(sota) != len(ids):
        return resultado
    total_sot = round(sum(sot), 4)
    total_sota = round(sum(sota), 4)
    if total_sot <= 0.0 and total_sota <= 0.0:
        # Filas creadas con los defaults del esquema (0.0) NO son evidencia: se declara ausencia.
        return resultado
    resultado["sot_total"] = total_sot
    resultado["sota_total"] = total_sota
    return resultado


def _acumular_club(
    partidos: Sequence[Dict[str, Any]],
    cache: Dict[str, Any],
    telemetria: Dict[str, Any],
) -> Dict[str, Any]:
    """Corte N−1 de un club: goles reales + cobertura ÍNTEGRA de xG/xGA publicados.

    Regla dura: `xg_total`/`xga_total` sólo se publican si TODOS los partidos del corte traen la
    métrica Opta. Una sola ausencia ⇒ `None` (el motor cae a la ruta sellada con GF real).
    """
    pj = len(partidos)
    acumulado: Dict[str, Any] = {
        "pj": pj,
        "gf": sum(p["goles_favor"] for p in partidos),
        "gc": sum(p["goles_contra"] for p in partidos),
        "pts": sum(
            3 if p["goles_favor"] > p["goles_contra"] else (1 if p["goles_favor"] == p["goles_contra"] else 0)
            for p in partidos
        ),
        "xg_total": None,
        "xga_total": None,
        "cobertura_xg": {"cubiertos": 0, "total": pj, "faltantes": []},
        "sot_total": telemetria.get("sot_total"),
        "sota_total": telemetria.get("sota_total"),
        "cobertura_sot": {
            "cubiertos": int(telemetria.get("cubiertos") or 0),
            "total": int(telemetria.get("total") or pj),
            "faltantes": list(telemetria.get("faltantes") or []),
        },
        "partidos": [dict(p) for p in partidos],
    }
    cubiertos = 0
    faltantes: List[str] = []
    xg_suma = 0.0
    xga_suma = 0.0
    for partido in partidos:
        lado = "home" if partido["es_local"] else "away"
        bloque = _registro_opta(cache, partido["match_id"], lado)
        xg = _magnitud(bloque, "xg")
        xga = _magnitud(bloque, "xga")
        if xg is None or xga is None:
            faltantes.append(partido["match_id"])
            continue
        cubiertos += 1
        xg_suma += xg
        xga_suma += xga
    if pj > 0 and cubiertos == pj:
        acumulado["xg_total"] = round(xg_suma, 4)
        acumulado["xga_total"] = round(xga_suma, 4)
    acumulado["cobertura_xg"] = {"cubiertos": cubiertos, "total": pj, "faltantes": faltantes}
    return acumulado


def _bloque_factico(acumulado: Dict[str, Any]) -> Dict[str, Any]:
    """Bloque homologado §E1: publica `gf`, `gc`, `pj`, `pts` y `xg` — JAMÁS `xga`."""
    bloque: Dict[str, Any] = {
        "pj": int(acumulado["pj"]),
        "gf": int(acumulado["gf"]),
        "gc": int(acumulado["gc"]),
        "pts": int(acumulado["pts"]),
    }
    if acumulado.get("xg_total") is not None:
        bloque["xg"] = float(acumulado["xg_total"])
    return bloque


# ═════════════════════════════════════════════════════════════════════════════════════════════
# LOCALIZACIÓN DEL FIXTURE (cartelera 3NF, sólo lectura)
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


def _leer_fixture(sesion: Any, match_id: str) -> Optional[Dict[str, Any]]:
    """Localiza el fixture por `id_partido` en el snapshot más reciente (fallback: `matches`).

    El snapshot es la fuente de exhibición (nombres, `fecha_dt`, marcador y JORNADA canónica).
    La tabla `matches` sólo aporta slugs y `kickoff_utc` cuando el fixture no está en cartelera.
    """
    consulta = select(FixtureSnapshot).order_by(FixtureSnapshot.updated_at.desc(), FixtureSnapshot.id.desc())
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
                "snapshot_actualizado": actualizado.isoformat() if hasattr(actualizado, "isoformat") else str(actualizado or ""),
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


# ═════════════════════════════════════════════════════════════════════════════════════════════
# [LN-QBE-108] COLISIÓN CRUZADA DE FUERZAS (aritmética pura, sin estado ni I/O)
# ═════════════════════════════════════════════════════════════════════════════════════════════
def calcular_colision_fuerzas_cruzadas(
    A_h: float,
    D_a: float,
    A_a: float,
    D_h: float,
) -> Dict[str, Any]:
    """Choque cruzado de la ecuación log-lineal: ataque de un bando contra defensa del otro.

    Definición sellada [LN-QBE-108]:
        empuje_ofensivo_local  = A_H − D_A        (ataque local contra defensa visita)
        empuje_ofensivo_visita = A_A − D_H        (ataque visita contra defensa local)
        diferencial_neto       = empuje_local − empuje_visita = (A_H − D_A) − (A_A − D_H)

    El signo del diferencial identifica al bando dominante. NO se restan ataques entre sí
    (eso violaría la estructura bipartita de 𝒯_Rem/𝒯_Def): sólo se cruzan fuerzas complementarias.
    """
    empuje_local = float(A_h) - float(D_a)
    empuje_visita = float(A_a) - float(D_h)
    diferencial = empuje_local - empuje_visita
    if diferencial > 1e-12:
        bando = "LOCAL"
    elif diferencial < -1e-12:
        bando = "VISITANTE"
    else:
        bando = "EQUILIBRADO"
    return {
        "A_home": round(float(A_h), 6),
        "D_away": round(float(D_a), 6),
        "A_away": round(float(A_a), 6),
        "D_home": round(float(D_h), 6),
        "empuje_ofensivo_local": round(empuje_local, 6),
        "empuje_ofensivo_visita": round(empuje_visita, 6),
        "diferencial_neto_partido": round(diferencial, 6),
        "magnitud_colision": round(abs(empuje_local) + abs(empuje_visita), 6),
        "bando_dominante": bando,
        "ecuacion_local": f"A_H − D_A = {float(A_h):+.4f} − ({float(D_a):+.4f})",
        "ecuacion_visita": f"A_A − D_H = {float(A_a):+.4f} − ({float(D_h):+.4f})",
    }


# ═════════════════════════════════════════════════════════════════════════════════════════════
# [LN-QBE-108] COMPOSICIÓN DEL REPORTE (dimensiones, corte y semáforos)
# ═════════════════════════════════════════════════════════════════════════════════════════════
REGLA_CORTE = "matchday_num < N ∧ estado ∈ {FINALIZADO, FINISHED} (futuro-ceguera N−1)"
NODOS_GOBIERNO = ("LN-QBE-108", "ARCH-1.4.47")


def _r(valor: Optional[float], decimales: int = 4) -> Optional[float]:
    """Redondeo seguro de presentación (preserva `None` como ausencia declarada)."""
    return None if valor is None else round(float(valor), decimales)


def _resumen_corte(acumulado: Dict[str, Any]) -> Dict[str, Any]:
    """Corte N−1 auditable: muestra, goles reales, tasas y cobertura de cada métrica."""
    pj = int(acumulado["pj"])
    partidos = acumulado["partidos"]
    jornadas = [p["jornada"] for p in partidos if p.get("jornada")]
    return {
        "pj": pj,
        "rango_jornadas": [min(jornadas), max(jornadas)] if jornadas else None,
        "gf": int(acumulado["gf"]),
        "gc": int(acumulado["gc"]),
        "pts": int(acumulado["pts"]),
        "gf_90": _r(_tasa(acumulado["gf"], pj)),
        "gc_90": _r(_tasa(acumulado["gc"], pj)),
        "xg_total": _r(acumulado.get("xg_total")),
        "xga_total": _r(acumulado.get("xga_total")),
        "npxg_90": _r(_tasa(acumulado.get("xg_total"), pj)),
        "xga_90": _r(_tasa(acumulado.get("xga_total"), pj)),
        "sot_total": _r(acumulado.get("sot_total")),
        "sota_total": _r(acumulado.get("sota_total")),
        "sot_90": _r(_tasa(acumulado.get("sot_total"), pj)),
        "sota_90": _r(_tasa(acumulado.get("sota_total"), pj)),
        "cobertura_xg": dict(acumulado["cobertura_xg"]),
        "cobertura_sot": dict(acumulado["cobertura_sot"]),
        "splits_sede": {
            "como_local": _bloque_sede(partidos, True),
            "como_visitante": _bloque_sede(partidos, False),
        },
        "partidos": [dict(p) for p in partidos],
    }


def _dimensiones(acum_local: Dict[str, Any], acum_visita: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Materializa las celdas de 𝒯_Rem y 𝒯_Def (taxonomía `[LN-QBE-122]`) en celdas bipartitas.

    `V06`/`V12` se evalúan con la caché Opta congelada (cobertura íntegra obligatoria).
    `V07`/`V13` se evalúan sólo si `match_telemetry` cubre TODOS los partidos del corte.
    El resto se declara `SIN EVIDENCIA (FASE 6)`: cero cifras inventadas `[GOVERNANCE-01]`.
    """
    pj_h, pj_v = int(acum_local["pj"]), int(acum_visita["pj"])
    xg_h = _tasa(acum_local.get("xg_total"), pj_h)
    xg_v = _tasa(acum_visita.get("xg_total"), pj_v)
    xga_h = _tasa(acum_local.get("xga_total"), pj_h)
    xga_v = _tasa(acum_visita.get("xga_total"), pj_v)
    sot_h = _tasa(acum_local.get("sot_total"), pj_h)
    sot_v = _tasa(acum_visita.get("sot_total"), pj_v)
    sota_h = _tasa(acum_local.get("sota_total"), pj_h)
    sota_v = _tasa(acum_visita.get("sota_total"), pj_v)

    def _nota_faltante(acum_local: Dict[str, Any], acum_visita: Dict[str, Any], metrica: str) -> str:
        """Nota honesta del faltante: publica la cobertura de AMBOS cortes, no sólo uno."""
        cobertura_h = acum_local.get(f"cobertura_{metrica}") or {}
        cobertura_v = acum_visita.get(f"cobertura_{metrica}") or {}
        return (
            f"{NOTA_FASE_6}: `match_telemetry` cubre "
            f"{int(cobertura_h.get('cubiertos') or 0)}/{int(cobertura_h.get('total') or acum_local['pj'])} "
            f"partidos del corte local y "
            f"{int(cobertura_v.get('cubiertos') or 0)}/{int(cobertura_v.get('total') or acum_visita['pj'])} "
            f"del corte visita."
        )

    dim_2: Dict[str, Any] = {}
    for identificador, nombre, unidad, nota in _TAXONOMIA_DIM_2:
        if identificador == "V06":
            dim_2["V06"] = _celda(identificador, nombre, unidad, xg_h, xg_v, nota)
        elif identificador == "V07":
            nota_v07 = nota if (sot_h is not None and sot_v is not None) else _nota_faltante(
                acum_local, acum_visita, "sot"
            )
            dim_2["V07"] = _celda(identificador, nombre, unidad, sot_h, sot_v, nota_v07)
        else:
            dim_2[identificador] = _celda(identificador, nombre, unidad, None, None, nota)

    dim_3: Dict[str, Any] = {}
    for identificador, nombre, unidad, nota in _TAXONOMIA_DIM_3:
        if identificador == "V12":
            dim_3["V12"] = _celda(identificador, nombre, unidad, xga_h, xga_v, nota)
        elif identificador == "V13":
            nota_v13 = nota if (sota_h is not None and sota_v is not None) else _nota_faltante(
                acum_local, acum_visita, "sot"
            )
            dim_3["V13"] = _celda(identificador, nombre, unidad, sota_h, sota_v, nota_v13)
        else:
            dim_3[identificador] = _celda(identificador, nombre, unidad, None, None, nota)
    return dim_2, dim_3


def _semaforo(nivel: str, detalle: str) -> Dict[str, str]:
    """Celda de salud fiduciaria homogénea (nivel + glifo + evidencia textual)."""
    return {"nivel": nivel, "glifo": GLIFO.get(nivel, "·"), "detalle": detalle}


def _semaforos(
    cache_meta: Dict[str, Any],
    acum_local: Dict[str, Any],
    acum_visita: Dict[str, Any],
    factores: Optional[Dict[str, Any]],
    colision: Optional[Dict[str, Any]],
    intensidades: Dict[str, Any],
) -> Dict[str, Dict[str, str]]:
    """Seis celdas de salud, todas derivadas de evidencia fáctica (cero opinión)."""
    salud: Dict[str, Dict[str, str]] = {}

    total = int(acum_local["cobertura_xg"]["total"]) + int(acum_visita["cobertura_xg"]["total"])
    cubiertos = int(acum_local["cobertura_xg"]["cubiertos"]) + int(acum_visita["cobertura_xg"]["cubiertos"])
    if total > 0 and cubiertos == total:
        salud["cobertura_opta"] = _semaforo(
            NIVEL_VERDE, f"{cubiertos}/{total} partidos del corte con xG/xGA publicados."
        )
    elif cubiertos > 0:
        salud["cobertura_opta"] = _semaforo(
            NIVEL_AMARILLO, f"{cubiertos}/{total} partidos cubiertos: el corte degrada a GF/GC sellado."
        )
    else:
        salud["cobertura_opta"] = _semaforo(
            NIVEL_NEUTRAL, "0 partidos con métrica Opta: no se publica npxG/90 (cero invención)."
        )

    muestra = min(int(acum_local["pj"]), int(acum_visita["pj"]))
    if muestra >= 5:
        salud["muestra_corte"] = _semaforo(NIVEL_VERDE, f"Muestra mínima N−1 = {muestra} partidos por club.")
    elif muestra >= 1:
        salud["muestra_corte"] = _semaforo(NIVEL_AMARILLO, f"Muestra mínima N−1 = {muestra} partidos: corte corto.")
    else:
        salud["muestra_corte"] = _semaforo(NIVEL_NEUTRAL, "Muestra N−1 vacía: motor estructural no invocado.")

    if factores is not None:
        salud["motor_estructural"] = _semaforo(
            NIVEL_VERDE, "Factores derivados por el plano sellado [VAULT-CORE-005] (cero reimplementación)."
        )
    else:
        salud["motor_estructural"] = _semaforo(
            NIVEL_NEUTRAL, "No invocado: muestra insuficiente (prohibido caer en los defaults del motor)."
        )

    lambda_home = intensidades.get("lambda_home")
    lambda_away = intensidades.get("lambda_away")
    if lambda_home is not None and lambda_away is not None:
        acotadas = min(lambda_home, lambda_away) > LAMBDA_MIN and max(lambda_home, lambda_away) < LAMBDA_MAX
        if acotadas:
            salud["acotamiento_lambda"] = _semaforo(
                NIVEL_VERDE,
                f"λ_H={lambda_home:.4f} · λ_A={lambda_away:.4f} dentro de I6 "
                f"[{LAMBDA_MIN:.2f}, {LAMBDA_MAX:.2f}].",
            )
        else:
            salud["acotamiento_lambda"] = _semaforo(
                NIVEL_AMARILLO, f"λ_H={lambda_home:.4f} · λ_A={lambda_away:.4f} saturan la cota I6."
            )
    else:
        salud["acotamiento_lambda"] = _semaforo(NIVEL_NEUTRAL, "Sin λ proyectada: no hay intensidad que acotar.")

    if colision is not None:
        salud["colision_cruzada"] = _semaforo(
            NIVEL_VERDE,
            f"(A_H − D_A)={colision['empuje_ofensivo_local']:+.4f} · "
            f"(A_A − D_H)={colision['empuje_ofensivo_visita']:+.4f} ⇒ dominio {colision['bando_dominante']}.",
        )
    else:
        salud["colision_cruzada"] = _semaforo(NIVEL_NEUTRAL, "Colisión no evaluada: depende del motor estructural.")

    if cache_meta.get("disponible"):
        salud["corpus_congelado"] = _semaforo(
            NIVEL_VERDE, f"{int(cache_meta.get('partidos') or 0)} partidos en `{cache_meta.get('ruta')}`."
        )
    else:
        salud["corpus_congelado"] = _semaforo(
            NIVEL_NEUTRAL, str(cache_meta.get("error") or "Artefacto congelado no disponible.")
        )
    return salud


def _marco_reporte(match_id: str, fixture: Optional[Dict[str, Any]], temporada: str) -> Dict[str, Any]:
    """Esqueleto común del reporte (contrato estable para la consola y `--json`)."""
    return {
        "nodos_gobernanza": list(NODOS_GOBIERNO),
        "sandbox": "ATAQUE_DEFENSA_DIM2_DIM3",
        "modo": "SOLO_LECTURA",
        "temporada": str(temporada),
        "match": fixture if fixture is not None else {"match_id": str(match_id)},
        "escritura_bd": False,
        "llamadas_red": False,
    }


def _intensidades_nulas(mu_liga: float = MU_LIGA_DEFAULT) -> Dict[str, Any]:
    """Contrato de intensidades cuando el motor NO se invoca (ausencia declarada)."""
    return {
        "lambda_home": None,
        "lambda_away": None,
        "ratio_ofensivo": None,
        "cotas_fisicas": [LAMBDA_MIN, LAMBDA_MAX],
        "en_cota": False,
        "mu_liga": mu_liga,
        "kappa_net": KAPPA_NET,
        "modelo": None,
    }


def _reporte_degradado(
    match_id: str,
    fixture: Optional[Dict[str, Any]],
    temporada: str,
    cache_meta: Dict[str, Any],
    status: str,
    motivo: str,
    acum_local: Dict[str, Any],
    acum_visita: Dict[str, Any],
    mu_liga: float = MU_LIGA_DEFAULT,
) -> Dict[str, Any]:
    """Reporte honesto sin proyección: publica el corte y las dimensiones que SÍ existan."""
    dim_2, dim_3 = _dimensiones(acum_local, acum_visita)
    intensidades = _intensidades_nulas(mu_liga)
    reporte = _marco_reporte(match_id, fixture, temporada)
    reporte.update({
        "status": status,
        "motivo": motivo,
        "cache_opta": cache_meta,
        "corte_n_1": {
            "jornada_objetivo": (fixture or {}).get("jornada"),
            "regla": REGLA_CORTE,
            "local": _resumen_corte(acum_local),
            "visita": _resumen_corte(acum_visita),
        },
        "dimension_2_ataque": dim_2,
        "dimension_3_defensa": dim_3,
        "factores_estructurales": None,
        "colision": None,
        "intensidades_proyectadas": intensidades,
        "semaforos": _semaforos(cache_meta, acum_local, acum_visita, None, None, intensidades),
    })
    return reporte


def ejecutar_sandbox_ataque_defensa_partido(
    match_id: str,
    temporada: str = TEMPORADA_DEFAULT,
    mu_liga: float = MU_LIGA_DEFAULT,
) -> Dict[str, Any]:
    """Cadena completa Dimensión 2 × Dimensión 3 para un fixture de la cartelera 3NF.

    Secuencia: caché congelada + corte N−1 (sólo lectura) → celdas V06-V16 → factores
    estructurales sellados → colisión cruzada `[LN-QBE-108]` → λ_H/λ_A canónicas → semáforos.
    """
    cache, cache_meta = cargar_cache_opta(temporada)

    gateway = PersistenceGateway()
    with gateway.read_session() as sesion:
        fixture = _leer_fixture(sesion, str(match_id))
        if fixture is None:
            vacio = _acumular_club([], cache, {})
            return _reporte_degradado(
                str(match_id), None, temporada, cache_meta, "NO_ENCONTRADO",
                f"El fixture `{match_id}` no existe en `fixtures_snapshots` ni en `matches`.",
                vacio, vacio, mu_liga,
            )

        jornada = fixture.get("jornada")
        local_slug = str(fixture.get("local_slug") or "")
        visita_slug = str(fixture.get("visitante_slug") or "")
        if jornada is None or not local_slug or not visita_slug:
            vacio = _acumular_club([], cache, {})
            return _reporte_degradado(
                str(match_id), fixture, temporada, cache_meta, "SIN_EVIDENCIA",
                "El fixture no publica jornada canónica o slugs de ambos clubes.",
                vacio, vacio, mu_liga,
            )

        partidos_local = _partidos_de_club(sesion, local_slug, int(jornada))
        partidos_visita = _partidos_de_club(sesion, visita_slug, int(jornada))
        telemetria_local = _telemetria_de_club(sesion, partidos_local, local_slug)
        telemetria_visita = _telemetria_de_club(sesion, partidos_visita, visita_slug)

    acum_local = _acumular_club(partidos_local, cache, telemetria_local)
    acum_visita = _acumular_club(partidos_visita, cache, telemetria_visita)

    if acum_local["pj"] == 0 or acum_visita["pj"] == 0:
        return _reporte_degradado(
            str(match_id), fixture, temporada, cache_meta, "SIN_EVIDENCIA",
            "El corte N−1 no publica partidos terminales para ambos clubes: el motor no se invoca "
            "(sus defaults fabricarían fuerza inexistente).",
            acum_local, acum_visita, mu_liga,
        )

    # ── Insumos homologados (§E1: `xg` sí, `xga` JAMÁS) ────────────────────────────────────
    crudo: Dict[str, Any] = {
        "home_team_stats": _bloque_factico(acum_local),
        "away_team_stats": _bloque_factico(acum_visita),
        "home_split_stats": _bloque_sede(partidos_local, True),
        "away_split_stats": _bloque_sede(partidos_visita, False),
        "xg_es_real_opta": acum_local.get("xg_total") is not None and acum_visita.get("xg_total") is not None,
    }

    # ── Motor sellado [VAULT-CORE-005]: invocación VERBATIM, cero reimplementación ─────────
    A_home, D_away, A_away, D_home = derivar_factores_estructurales(crudo, mu_liga=mu_liga)
    colision = calcular_colision_fuerzas_cruzadas(A_home, D_away, A_away, D_home)

    # ── Motor sellado [VAULT-CORE-001]: identidad canónica log-lineal + bono de plaza ─────
    lambda_home, lambda_away = estimar_intensidades_loglineal(
        A_home, D_away, A_away, D_home,
        mu_liga=mu_liga,
        gamma_home_base=GAMMA_HOME_DEFAULT,
        home_team_slug=local_slug,
    )
    bono_plaza = obtener_bono_fortaleza_plaza(local_slug)
    gamma_efectivo = GAMMA_HOME_DEFAULT + bono_plaza
    alpha = calcular_alpha_ligadura(mu_liga, gamma_efectivo)
    ratio = (float(lambda_home) / float(lambda_away)) if float(lambda_away) > 0.0 else None

    intensidades: Dict[str, Any] = {
        "lambda_home": round(float(lambda_home), 4),
        "lambda_away": round(float(lambda_away), 4),
        "ratio_ofensivo": _r(ratio),
        "cotas_fisicas": [LAMBDA_MIN, LAMBDA_MAX],
        "en_cota": LAMBDA_MIN <= min(float(lambda_home), float(lambda_away))
        and max(float(lambda_home), float(lambda_away)) <= LAMBDA_MAX,
        "mu_liga": float(mu_liga),
        "alpha_ligadura": round(float(alpha), 6),
        "gamma_home_base": GAMMA_HOME_DEFAULT,
        "bono_plaza": round(float(bono_plaza), 4),
        "gamma_home_efectivo": round(float(gamma_efectivo), 4),
        "delta_alt_metros": 0.0,
        "delta_descanso_dias": 0.0,
        "kappa_net": KAPPA_NET,
        "modelo": (
            "ln(λ_H) = α + (γ̄ + Δγ_plaza) + A_H − D_A ; "
            "ln(λ_A) = α + A_A − D_H   [VAULT-CORE-001]"
        ),
    }
    dim_2, dim_3 = _dimensiones(acum_local, acum_visita)

    cobertura_completa = (
        int(acum_local["cobertura_xg"]["cubiertos"]) == int(acum_local["pj"])
        and int(acum_visita["cobertura_xg"]["cubiertos"]) == int(acum_visita["pj"])
    )
    if cobertura_completa:
        status = "EXITO"
        motivo = (
            "Cobertura Opta íntegra en ambos cortes: V06 y V12 evaluados con evidencia real; "
            "λ proyectada por los planos sellados."
        )
    else:
        status = "PARCIAL"
        motivo = (
            "Cobertura Opta incompleta: V06/V12 se declaran SIN EVIDENCIA y el motor cae a la ruta "
            "sellada con GF/GC reales [VAULT-CORE-005]. Cero cifras fabricadas."
        )

    return _reporte_final(
        str(match_id), fixture, temporada, cache_meta, status, motivo,
        acum_local, acum_visita, dim_2, dim_3, crudo, colision, intensidades, mu_liga,
    )


def _insumos_motor(acum_local: Dict[str, Any], acum_visita: Dict[str, Any]) -> Dict[str, Any]:
    """Transparencia de los insumos REALES que consumió el motor sellado (tasas por partido)."""
    pj_h, pj_v = int(acum_local["pj"]), int(acum_visita["pj"])
    return {
        "A_H (ataque local)": {
            "xg_90": _r(_tasa(acum_local.get("xg_total"), pj_h)),
            "gf_90": _r(_tasa(acum_local["gf"], pj_h)),
            "mezcla_sellada": "0.65·xG/90 + 0.35·GF/90 → log(tasa / (μ_liga/2))",
        },
        "D_A (defensa visita)": {
            "xga_90_evidencia": _r(_tasa(acum_visita.get("xga_total"), pj_v)),
            "gc_90_insumo": _r(_tasa(acum_visita["gc"], pj_v)),
            "mezcla_sellada": "−log(0.65·xGA/90 + 0.35·GC/90) — xGA NO inyectado (§E1)",
        },
        "A_A (ataque visita)": {
            "xg_90": _r(_tasa(acum_visita.get("xg_total"), pj_v)),
            "gf_90": _r(_tasa(acum_visita["gf"], pj_v)),
            "mezcla_sellada": "0.65·xG/90 + 0.35·GF/90 → log(tasa / (μ_liga/2))",
        },
        "D_H (defensa local)": {
            "xga_90_evidencia": _r(_tasa(acum_local.get("xga_total"), pj_h)),
            "gc_90_insumo": _r(_tasa(acum_local["gc"], pj_h)),
            "mezcla_sellada": "−log(0.65·xGA/90 + 0.35·GC/90) — xGA NO inyectado (§E1)",
        },
        "nota_homologacion": (
            "Decreto VAR-2026-J7-HOMOLOGACION §E1: `xga` permanece fuera del `raw_match_data` para "
            "preservar el diagnóstico defensivo certificado; el xGA se publica sólo como V12."
        ),
    }


def _reporte_final(
    match_id: str,
    fixture: Dict[str, Any],
    temporada: str,
    cache_meta: Dict[str, Any],
    status: str,
    motivo: str,
    acum_local: Dict[str, Any],
    acum_visita: Dict[str, Any],
    dim_2: Dict[str, Any],
    dim_3: Dict[str, Any],
    crudo: Dict[str, Any],
    colision: Dict[str, Any],
    intensidades: Dict[str, Any],
    mu_liga: float,
) -> Dict[str, Any]:
    """Ensambla el reporte soberano del experimento (contrato único para consola y `--json`)."""
    jornada = fixture.get("jornada")
    splits_inyectados = (
        int((crudo.get("home_split_stats") or {}).get("pj") or 0) >= PJ_MINIMO_SPLITS_SEDE
        and int((crudo.get("away_split_stats") or {}).get("pj") or 0) >= PJ_MINIMO_SPLITS_SEDE
    )
    factores: Dict[str, Any] = {
        "A_home": colision["A_home"],
        "D_away": colision["D_away"],
        "A_away": colision["A_away"],
        "D_home": colision["D_home"],
        "mu_liga": float(mu_liga),
        "origen_factores": "analitico_base",
        "nota_origen": "El corte N−1 no publica `form_10p` ⇒ ruta sellada [LN-QBE-035-B]; cero invención.",
        "splits_sede_inyectados": splits_inyectados,
        "regla_splits": f"PJ ≥ {PJ_MINIMO_SPLITS_SEDE} por bloque de sede [LN-QBE-038] (w_sede = 0.50).",
        "xga_inyectado": False,
        "xg_es_real_opta": bool(crudo.get("xg_es_real_opta")),
        "insumos": _insumos_motor(acum_local, acum_visita),
        "contrato_consumido": {
            "home_team_stats": dict(crudo["home_team_stats"]),
            "away_team_stats": dict(crudo["away_team_stats"]),
            "home_split_stats": dict(crudo["home_split_stats"]),
            "away_split_stats": dict(crudo["away_split_stats"]),
        },
    }
    reporte = _marco_reporte(match_id, fixture, temporada)
    reporte.update({
        "status": status,
        "motivo": motivo,
        "cache_opta": cache_meta,
        "corte_n_1": {
            "jornada_objetivo": jornada,
            "corte_hasta_jornada": (int(jornada) - 1) if jornada is not None else None,
            "regla": REGLA_CORTE,
            "local": _resumen_corte(acum_local),
            "visita": _resumen_corte(acum_visita),
        },
        "dimension_2_ataque": dim_2,
        "dimension_3_defensa": dim_3,
        "factores_estructurales": factores,
        "colision": colision,
        "intensidades_proyectadas": intensidades,
        "semaforos": _semaforos(cache_meta, acum_local, acum_visita, factores, colision, intensidades),
    })
    return reporte


# ═════════════════════════════════════════════════════════════════════════════════════════════
# [ARCH-1.4.47] TABLERO ASCII DE CONSOLA (presentación pura, cero cálculo)
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


def _glifo_celda(celda: Dict[str, Any]) -> str:
    """Glifo de estado de una celda V0x (🟢 evaluada / ⚪ sin evidencia)."""
    return GLIFO.get(str(celda.get("estado")), "·")


def _fila_dimension(celda: Dict[str, Any]) -> str:
    """Fila de tabla: ID · variable · unidad · LOCAL · VISITA · estado."""
    return (
        f"{_pad(str(celda['id']), 5)}"
        f"{_pad(str(celda['variable'])[:39], 40)}"
        f"{_pad(str(celda['unidad']), 10)}"
        f"{_num(celda.get('local'), 4, 7)}"
        f"{_num(celda.get('visita'), 4, 9)}"
        f"  {_glifo_celda(celda)} {celda['estado']}"
    )


def _encabezado_dimension(etiqueta: str) -> str:
    """Cabecera de tabla de dimensión, alineada con `_fila_dimension`."""
    return (
        f"{_pad(etiqueta, 5)}{_pad('VARIABLE', 40)}{_pad('UNIDAD', 10)}"
        f"{'LOCAL'.rjust(7)}{'VISITA'.rjust(9)}  ESTADO"
    )


def _bloque_dimension(reporte: Dict[str, Any], clave: str, titulo: str) -> None:
    """Caja de una dimensión completa (5 variables V0x) con pie de cobertura."""
    dimension = reporte.get(clave) or {}
    filas: List[str] = [_encabezado_dimension("ID"), "─" * (ANCHO_TABLERO - 4)]
    evaluadas = 0
    for identificador in sorted(dimension.keys()):
        celda = dimension[identificador]
        filas.append(_fila_dimension(celda))
        if celda.get("estado") == ESTADO_EVALUADO:
            evaluadas += 1
    filas.append("─" * (ANCHO_TABLERO - 4))
    filas.append(
        f"Evaluadas {evaluadas}/{len(dimension)} · ⚪ SIN EVIDENCIA = sensor ausente; "
        f"jamás se imputa una cifra."
    )
    _caja(titulo, filas)


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


def _bloque_contexto(reporte: Dict[str, Any]) -> None:
    """Caja 1: identidad del experimento, corte N−1 declarado y procedencia de la evidencia."""
    fixture = reporte.get("match") or {}
    corte = reporte.get("corte_n_1") or {}
    cache = reporte.get("cache_opta") or {}
    local = corte.get("local") or {}
    visita = corte.get("visita") or {}
    jornada = fixture.get("jornada")
    marcador = fixture.get("marcador")
    rango = local.get("rango_jornadas")
    tramo = f"J{rango[0]}..J{rango[1]}" if rango else "—"
    filas: List[str] = [
        _linea("FIXTURE", f"{fixture.get('match_id')} · Jornada {jornada} · {fixture.get('estado') or '—'}"
                          f"{(' · ' + str(marcador)) if marcador else ''}"),
        _linea("DUELO", f"{fixture.get('local') or '—'} (L)  vs  {fixture.get('visitante') or '—'} (V)"),
        _linea("REGLA", "Corte futuro-ciego N−1 · `matchday_num < N` ∧ estado terminal"),
        _linea("CORTE", f"{tramo} · {local.get('pj', 0)} PJ local · {visita.get('pj', 0)} PJ visita"),
        _linea("CORPUS", f"{cache.get('ruta') or '—'} · {cache.get('partidos', 0)} partidos"),
        *[
            _linea("FUENTE" if indice == 0 else "", trozo)
            for indice, trozo in enumerate(_envolver(str(cache.get("fuente") or "sin fuente")))
        ],
        _linea("MODELO", "DIM 2 (T_Fin) × DIM 3 (T_Def) → factores → λ [VAULT-CORE-001/005]"),
    ]
    filas.append("")
    texto_estado = f"{reporte.get('status')} — {reporte.get('motivo')}"
    trozos = _envolver(texto_estado)
    filas.append(_linea("ESTADO", trozos[0]))
    for trozo in trozos[1:]:
        filas.append(_linea("", trozo))
    _caja("CONTEXTO DEL EXPERIMENTO", filas)


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


def _bloque_colision(reporte: Dict[str, Any]) -> None:
    """Caja 2: colisión cruzada A_H − D_A vs A_A − D_H (núcleo de [LN-QBE-108])."""
    colision = reporte.get("colision")
    factor = reporte.get("factores_estructurales") or {}
    if not colision:
        _caja("COLISIÓN CRUZADA · A_H − D_A  /  A_A − D_H  [LN-QBE-108]", [
            "NO EVALUADA: el motor estructural no fue invocado en este reporte.",
            f"Motivo: {reporte.get('motivo')}",
        ])
        return
    separador = "─" * (ANCHO_TABLERO - 4)
    filas: List[str] = [
        f"{_pad('FACTOR', 14)}{_pad('SIGNIFICADO', 40)}{'VALOR'.rjust(10)}",
        separador,
        f"{_pad('A_H', 14)}{_pad('Ataque del club LOCAL', 40)}{_num(colision['A_home'], 4, 10)}",
        f"{_pad('D_A', 14)}{_pad('Permisividad de la VISITA', 40)}{_num(colision['D_away'], 4, 10)}",
        f"{_pad('A_A', 14)}{_pad('Ataque del club VISITA', 40)}{_num(colision['A_away'], 4, 10)}",
        f"{_pad('D_H', 14)}{_pad('Permisividad del LOCAL', 40)}{_num(colision['D_home'], 4, 10)}",
        separador,
        f"{_pad('A_H − D_A', 14)}{_pad('Empuje ofensivo LOCAL', 40)}"
        f"{_num(colision['empuje_ofensivo_local'], 4, 10)}",
        f"{_pad('A_A − D_H', 14)}{_pad('Empuje ofensivo VISITA', 40)}"
        f"{_num(colision['empuje_ofensivo_visita'], 4, 10)}",
        f"{_pad('Δ NETO', 14)}{_pad('Empuje local − empuje visita', 40)}"
        f"{_num(colision['diferencial_neto_partido'], 4, 10)}   ⇒ dominio {colision['bando_dominante']}",
        separador,
    ]
    filas.extend(_envolver(
        "Identidad: A = log[(0.65·xG/90 + 0.35·GF/90) / (μ_liga/2)] · "
        "D = −log[(0.65·xGA/90 + 0.35·GC/90) / (μ_liga/2)]  [VAULT-CORE-005]"
    ))
    filas.extend(_envolver(
        f"GSL-3D: splits de sede inyectados = "
        f"{'SÍ' if factor.get('splits_sede_inyectados') else 'NO'} · "
        f"xGA inyectado al motor = NO (§E1) · origen = {factor.get('origen_factores')}"
    ))
    filas.append("")
    filas.extend(_envolver(
        f"Lectura mecánica: el empuje local ({colision['empuje_ofensivo_local']:+.4f}) frente al de la visita "
        f"({colision['empuje_ofensivo_visita']:+.4f}) deja un diferencial de "
        f"{colision['diferencial_neto_partido']:+.4f}; magnitud conjunta "
        f"{colision['magnitud_colision']:.4f}. Sólo se cruzan fuerzas complementarias: jamás se restan "
        f"ataques entre sí."
    ))
    _caja("COLISIÓN CRUZADA · A_H − D_A  /  A_A − D_H  [LN-QBE-108]", filas)


def _texto_ratio(valor: Optional[float]) -> str:
    """Formato del ratio ofensivo λ_H/λ_A (guion largo si no existe proyección)."""
    return "—" if valor is None else f"{float(valor):.4f}"


def _bloque_intensidades(reporte: Dict[str, Any]) -> None:
    """Caja 5: proyección λ_H/λ_A por la identidad canónica [VAULT-CORE-001]."""
    intensidades = reporte.get("intensidades_proyectadas") or {}
    lambda_home = intensidades.get("lambda_home")
    lambda_away = intensidades.get("lambda_away")
    titulo = "PROYECCIÓN DE INTENSIDADES · ln(λ) CANÓNICO [VAULT-CORE-001]"
    if lambda_home is None or lambda_away is None:
        _caja(titulo, [
            "NO PROYECTADA: sin corte N−1 suficiente o sin motor estructural invocado.",
            f"Motivo: {reporte.get('motivo')}",
        ])
        return
    separador = "─" * (ANCHO_TABLERO - 4)

    def _fila(simbolo: str, concepto: str, valor: str, detalle: str = "") -> str:
        return f"{_pad(simbolo, 12)}{_pad(concepto, 44)}{_pad(valor.rjust(12), 12)}  {detalle}"

    cotas = intensidades.get("cotas_fisicas") or [LAMBDA_MIN, LAMBDA_MAX]
    texto_cotas = f"[{float(cotas[0]):.2f}, {float(cotas[1]):.2f}]"
    filas: List[str] = [
        f"{_pad('SÍMBOLO', 12)}{_pad('CONCEPTO', 44)}{_pad('VALOR'.rjust(12), 12)}  DETALLE",
        separador,
        _fila("λ_H", "Goles esperados del club LOCAL", f"{lambda_home:.4f}", "Invariante I6"),
        _fila("λ_A", "Goles esperados del club VISITA", f"{lambda_away:.4f}", "Invariante I6"),
        _fila("ρ = λ_H/λ_A", "Ratio ofensivo del partido",
              _texto_ratio(intensidades.get("ratio_ofensivo")), ">1 ⇒ domina el local"),
        separador,
        _fila("α", "Ligadura estructural",
              f"{float(intensidades.get('alpha_ligadura') or 0.0):.6f}",
              f"μ_liga = {intensidades.get('mu_liga')}"),
        _fila("γ̄", "Ventaja base de localía",
              f"{float(intensidades.get('gamma_home_base') or 0.0):.4f}", "[LN-QBE-038]"),
        _fila("Δγ_plaza", "Bono de intimidación de la plaza",
              f"{float(intensidades.get('bono_plaza') or 0.0):+.4f}", "[LN-QBE-038]"),
        _fila("γ_efectivo", "Localía efectiva (γ̄ + Δγ_plaza)",
              f"{float(intensidades.get('gamma_home_efectivo') or 0.0):.4f}", "ligadura recalculada"),
        _fila("κ_net", "Compresión hiperbólica pura",
              f"{float(intensidades.get('kappa_net') or 0.0):.4f}", "[VAULT-CORE-001]"),
        _fila("I6", "Cotas físicas de positividad", texto_cotas,
              f"en_cota = {'SÍ' if intensidades.get('en_cota') else 'NO'}"),
        separador,
    ]
    filas.extend(_envolver(
        "Identidad canónica: ln(λ_H) = α + (γ̄ + Δγ_plaza) + A_H − D_A ; ln(λ_A) = α + A_A − D_H. "
        "El techo conjunto anti-resonancia [LN-QBE-040-B] se custodia DENTRO del plano sellado "
        "(no se reimplementa aquí)."
    ))
    _caja(titulo, filas)


def _bloque_semaforos(reporte: Dict[str, Any]) -> None:
    """Caja 6: salud fiduciaria del experimento (seis celdas verificables)."""
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


def imprimir_tablero_ataque_defensa_consola(reporte: Dict[str, Any]) -> None:
    """Renderiza el tablero completo de un partido ([ARCH-1.4.47]). Presentación pura."""
    print()
    _caja("Q-BE · LABORATORIO ATAQUE & DEFENSA · DIM 2 (T_Fin) × DIM 3 (T_Def)", [
        f"[{NODOS_GOBIERNO[0]}] / [{NODOS_GOBIERNO[1]}] · SÓLO LECTURA · corte N−1 (futuro-ciego)",
        f"λ ∈ [{LAMBDA_MIN:.2f}, {LAMBDA_MAX:.2f}] · κ_net = {KAPPA_NET:.4f} · planos [VAULT-CORE-001/005]",
        "Suites hermanas: sandbox_h2h_pipeline [ARCH-1.4.46] · sandbox_pipeline [ARCH-1.4.45]",
    ])
    _bloque_contexto(reporte)
    _bloque_colision(reporte)
    _bloque_dimension(reporte, "dimension_2_ataque", "DIM 2 · CALIDAD DE REMATE (T_Rem · V06-V09)")
    _bloque_dimension(reporte, "dimension_3_defensa", "DIM 3 · CONTENCIÓN DEFENSIVA (T_Def · V12-V16)")
    _bloque_intensidades(reporte)
    _bloque_semaforos(reporte)
    print("─" * ANCHO_TABLERO)
    print(
        " Sólo lectura · 0 escrituras en la bóveda · 0 llamadas de red · "
        f"nodos {' + '.join(NODOS_GOBIERNO)}"
    )
    print()


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


def ejecutar_sandbox_ataque_defensa_jornada(
    jornada: int,
    temporada: str = TEMPORADA_DEFAULT,
    mu_liga: float = MU_LIGA_DEFAULT,
) -> Dict[str, Any]:
    """Barrido soberano de la jornada: un reporte por fixture + conteo de estados."""
    gateway = PersistenceGateway()
    with gateway.read_session() as sesion:
        identificadores = _ids_de_jornada(sesion, jornada)

    reportes = [
        ejecutar_sandbox_ataque_defensa_partido(ident, temporada, mu_liga)
        for ident in identificadores
    ]
    conteo = {"EXITO": 0, "PARCIAL": 0, "SIN_EVIDENCIA": 0, "NO_ENCONTRADO": 0}
    for reporte in reportes:
        estado = str(reporte.get("status") or "NO_ENCONTRADO")
        conteo[estado] = conteo.get(estado, 0) + 1
    return {
        "nodos_gobernanza": list(NODOS_GOBIERNO),
        "sandbox": "ATAQUE_DEFENSA_DIM2_DIM3_JORNADA",
        "modo": "SOLO_LECTURA",
        "temporada": str(temporada),
        "jornada": int(jornada),
        "total_partidos": len(reportes),
        "conteo_estados": conteo,
        "partidos": reportes,
        "escritura_bd": False,
        "llamadas_red": False,
    }


def imprimir_tablero_jornada_ataque_defensa_consola(resumen: Dict[str, Any]) -> None:
    """Tablero compacto de la jornada: empujes cruzados y λ por fixture."""
    jornada = resumen.get("jornada")
    conteo = resumen.get("conteo_estados") or {}
    glifos = {"EXITO": "🟢", "PARCIAL": "🟡", "SIN_EVIDENCIA": "⚪", "NO_ENCONTRADO": "⚫"}
    print()
    _caja(f"JORNADA {jornada} · ATAQUE & DEFENSA [LN-QBE-108]", [
        f"[{NODOS_GOBIERNO[0]}] / [{NODOS_GOBIERNO[1]}] · SÓLO LECTURA · temporada {resumen.get('temporada')} · "
        f"{resumen.get('total_partidos')} fixtures",
        " · ".join(
            f"{glifos.get(estado, '·')} {estado}: {cantidad}"
            for estado, cantidad in conteo.items()
        ),
    ])

    filas: List[str] = [
        f"{_pad('FIXTURE', 15)}{_pad('LOCAL', 19)}{_pad('VISITA', 19)}"
        f"{'A_H−D_A'.rjust(8)}{'A_A−D_H'.rjust(8)}{'λ_H'.rjust(7)}{'λ_A'.rjust(7)}  ST",
        "─" * (ANCHO_TABLERO - 4),
    ]
    for reporte in resumen.get("partidos") or []:
        fixture = reporte.get("match") or {}
        colision = reporte.get("colision") or {}
        intensidades = reporte.get("intensidades_proyectadas") or {}
        estado = str(reporte.get("status") or "NO_ENCONTRADO")
        inicial = {"EXITO": "E", "PARCIAL": "P", "SIN_EVIDENCIA": "S", "NO_ENCONTRADO": "N"}.get(estado, "?")
        filas.append(
            f"{_pad(str(fixture.get('match_id'))[:14], 15)}"
            f"{_pad(str(fixture.get('local') or '—')[:18], 19)}"
            f"{_pad(str(fixture.get('visitante') or '—')[:18], 19)}"
            f"{_num(colision.get('empuje_ofensivo_local'), 3, 8)}"
            f"{_num(colision.get('empuje_ofensivo_visita'), 3, 8)}"
            f"{_num(intensidades.get('lambda_home'), 3, 7)}"
            f"{_num(intensidades.get('lambda_away'), 3, 7)}"
            f"  {inicial}"
        )
    if not filas:
        filas.append("Sin fixtures publicados para la jornada solicitada.")
    filas.append("")
    filas.append("ST: E=EXITO · P=PARCIAL · S=SIN EVIDENCIA · N=NO ENCONTRADO")
    _caja(f"BARRIDO DE LA JORNADA {jornada} · EMPUJES Y λ", filas)
    print("─" * ANCHO_TABLERO)
    print(f" Sólo lectura · nodos {' + '.join(NODOS_GOBIERNO)} · detalle por fixture: --partido <ID>")
    print()


# ═════════════════════════════════════════════════════════════════════════════════════════════
# CLI (argparse puro, sin dependencias externas)
# ═════════════════════════════════════════════════════════════════════════════════════════════
def _construir_parser() -> argparse.ArgumentParser:
    """Contrato de línea de comandos del sandbox [ARCH-1.4.47]."""
    parser = argparse.ArgumentParser(
        prog="sandbox_ataque_defensa_pipeline",
        description=(
            "Sandbox CLI-first de Ataque (DIM 2 · V06-V09) y Defensa (DIM 3 · V12-V16): "
            "corte N−1 real → factores sellados → colisión cruzada → λ_H/λ_A. Sólo lectura."
        ),
    )
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--partido", metavar="MATCH_ID", help="Fixture a evaluar, ej. LIGAMX-J11-07")
    grupo.add_argument("--jornada", type=int, metavar="N", help="Barrido de toda la jornada, ej. 11")
    parser.add_argument(
        "--temporada", default=TEMPORADA_DEFAULT, metavar="AAAA",
        help=f"Temporada del corpus congelado (default {TEMPORADA_DEFAULT}).",
    )
    parser.add_argument(
        "--mu-liga", dest="mu_liga", type=float, default=MU_LIGA_DEFAULT, metavar="MU",
        help=f"Media de goles de la competición (default {MU_LIGA_DEFAULT}).",
    )
    parser.add_argument("--json", action="store_true", help="Emite el reporte estructurado en JSON.")
    parser.add_argument("--verbose", action="store_true", help="Registro de diagnóstico detallado.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Punto de entrada CLI. Devuelve 0 salvo fixture inexistente o jornada vacía."""
    argumentos = _construir_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if argumentos.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    if argumentos.partido:
        reporte = ejecutar_sandbox_ataque_defensa_partido(
            argumentos.partido, argumentos.temporada, argumentos.mu_liga
        )
        if argumentos.json:
            print(json.dumps(reporte, ensure_ascii=False, indent=2))
        else:
            imprimir_tablero_ataque_defensa_consola(reporte)
        return 0 if reporte.get("status") in ("EXITO", "PARCIAL", "SIN_EVIDENCIA") else 1

    resumen = ejecutar_sandbox_ataque_defensa_jornada(
        argumentos.jornada, argumentos.temporada, argumentos.mu_liga
    )
    if argumentos.json:
        print(json.dumps(resumen, ensure_ascii=False, indent=2))
    else:
        imprimir_tablero_jornada_ataque_defensa_consola(resumen)
    return 0 if resumen.get("total_partidos") else 1


if __name__ == "__main__":
    sys.exit(main())
