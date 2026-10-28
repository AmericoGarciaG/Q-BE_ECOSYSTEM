# -*- coding: utf-8 -*-
"""
[LN-QBE-110] / [ARCH-1.4.49] SANDBOX TRAYECTORIA & MOMENTO — PIPELINE AUTÓNOMO CLI-FIRST.

Misión
------
Aislar en consola la Dimensión 8 (𝒯_Traj, V31/V32 + AUX_M_XG/AUX_M_XGA): el momento competitivo de cada club en
una ventana móvil de 5 partidos. Expone la forma reciente (V31), las pendientes de peligro
ofensivo (AUX_M_XG) y defensivo (AUX_M_XGA) y el diferencial de puntos esperados (V32), que separa el
sobre-rendimiento por suerte de la calidad estructural. Sin FastAPI, sin DOM y sin Playwright.

Régimen: `[HÍBRIDO DUAL-TRACK]`
* `[DIRGEN-STRICT]`: la pendiente de mínimos cuadrados y los umbrales de ΔxPTS se transcriben
  VERBATIM de [LN-QBE-110]. Cero margen creativo en la aritmética.
* `[DBBD-FUNGIBLE]`: resolución del fixture, normalización de identidad para el *lookup*,
  celdas V31/V32 + AUX_M_XG/AUX_M_XGA, semáforos, tablero ASCII y CLI.

Axiomas operativos
------------------
1. **Sólo lectura:** `PersistenceGateway.read_session()` y `json.load` del corpus congelado.
   Prohibido escribir en `data/qbe_database.db`; prohibido abrir red.
2. **Futuro-ceguera (N−1):** la ventana de cada club son los partidos terminales con
   `matchday_num < N`. El fixture evaluado jamás alimenta su propia trayectoria.
3. **Cobertura íntegra [GOVERNANCE-01]:** si a un partido de la ventana le falta la métrica
   Opta, la celda degrada a `SIN EVIDENCIA`; jamás se imputa una cifra.
4. **Identidad normalizada:** los slugs de `matches` viajan sin acento y los nombres de
   `standings_snapshots` con acento. El *lookup* usa NFKD + minúsculas + guiones; es una
   regla de identidad, no una regla de negocio.
5. **V31 desde marcadores reales:** la racha se computa con los goles de `matches`; el campo
   `forma` del snapshot se publica únicamente como testigo de contraste.

Uso:
    python -m scripts.laboratorio.sandbox_trayectoria_momento_pipeline --partido LIGAMX-J11-07
    python -m scripts.laboratorio.sandbox_trayectoria_momento_pipeline --jornada 11
    python -m scripts.laboratorio.sandbox_trayectoria_momento_pipeline --partido LIGAMX-J11-07 --json
    python -m scripts.laboratorio.sandbox_trayectoria_momento_pipeline --jornada 11 --temporada 2026
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import unicodedata
from typing import Any, Dict, List, Optional, Sequence, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy import select

from src.storage.gateway import PersistenceGateway
from src.storage.models import FixtureSnapshot, Match, StandingSnapshot

logger = logging.getLogger("SandboxTrayectoriaMomento")

# ── Nodos de gobierno y constantes legisladas ──────────────────────────────────────────────
NODOS_GOBIERNO: Tuple[str, str] = ("LN-QBE-110", "ARCH-1.4.49")
TEMPORADA_DEFAULT = "2026"
RUTA_CACHE_OPTA_PLANTILLA = os.path.join(
    "data", "cache_optaxg_liga_mx_{temporada}.json"
)
VENTANA_TRAYECTORIA = 5
DENOMINADOR_PENDIENTE_5P = 10.0  # [LN-QBE-110] Σ(t − 3)² con t = 1..5
UMBRAL_XPTS = 3.0  # [LN-QBE-110] cota de sobre/sub-rendimiento
TOLERANCIA_PENDIENTE = 1e-12  # frontera numérica de la tendencia estable
ANCHO_TABLERO = 94

ESTADOS_TERMINALES = ("FINALIZADO", "FINISHED")
ESTADO_EVALUADO = "EVALUADO"
ESTADO_SIN_EVIDENCIA = "SIN EVIDENCIA"

NIVEL_VERDE = "VERDE"
NIVEL_AMARILLO = "AMARILLO"
NIVEL_ROJO = "ROJO"
NIVEL_NEUTRAL = "NEUTRAL"
GLIFO = {
    NIVEL_VERDE: "🟢",
    NIVEL_AMARILLO: "🟡",
    NIVEL_ROJO: "🔴",
    NIVEL_NEUTRAL: "⚪",
    ESTADO_EVALUADO: "🟢",
    ESTADO_SIN_EVIDENCIA: "⚪",
    "EXITO": "🟢",
    "PARCIAL": "🟡",
    "NO_ENCONTRADO": "⚫",
}


# ═════════════════════════════════════════════════════════════════════════════════════════════
# [LN-QBE-110] ARITMÉTICA PURA (sin estado, sin I/O)
# ═════════════════════════════════════════════════════════════════════════════════════════════
def calcular_pendiente_lineal_5p(serie_valores: Sequence[float]) -> float:
    """Pendiente de mínimos cuadrados sobre la ventana móvil de 5 partidos.

    Definición sellada [LN-QBE-110]:
        m = Σ(t − t̄)(y_t − ȳ) / Σ(t − t̄)²

    Para n = 5 y t = 1..5 el denominador es exactamente 10. Si la serie publica menos de
    5 puntos se calcula sobre los disponibles (misma fórmula exacta, t = 1..n); con n < 2
    no existe pendiente y se retorna 0.0 (sin evidencia, jamás una cifra inventada).
    """
    valores: List[float] = []
    for valor in serie_valores:
        if isinstance(valor, (int, float)) and not isinstance(valor, bool):
            valores.append(float(valor))
    if len(valores) > VENTANA_TRAYECTORIA:
        valores = valores[-VENTANA_TRAYECTORIA:]
    n = len(valores)
    if n < 2:
        return 0.0
    t_barra = (n + 1) / 2.0
    y_barra = sum(valores) / n
    numerador = sum(
        (t - t_barra) * (y - y_barra) for t, y in enumerate(valores, start=1)
    )
    denominador = sum((t - t_barra) ** 2 for t in range(1, n + 1))
    if denominador <= 0:
        return 0.0
    return numerador / denominador


def evaluar_diagnostico_xpts(puntos_reales: float, xpts: float) -> Dict[str, Any]:
    """Diagnóstico de varianza ΔxPTS = PTS − xPTS conforme a [LN-QBE-110].

    Δ ≥ +3.0  ⇒ SOBRERRENDIMIENTO (alerta de regresión a la baja)
    Δ ≤ −3.0  ⇒ SUBRRENDIMIENTO   (alerta de rebote al alza)
    |Δ| < 3.0 ⇒ NEUTRAL / ALINEADO
    """
    delta = float(puntos_reales) - float(xpts)
    if delta >= UMBRAL_XPTS:
        diagnostico = "SOBRERRENDIMIENTO"
        alerta = (
            "Regresión a la baja inminente: los puntos superan el nivel de juego; "
            "la cosecha se sostiene en varianza favorable, no en calidad estructural."
        )
        nivel = NIVEL_AMARILLO
    elif delta <= -UMBRAL_XPTS:
        diagnostico = "SUBRRENDIMIENTO"
        alerta = (
            "Rebote al alza inminente: el equipo juega para más de lo que suma; "
            "los puntos perdidos son varianza adversa, no deterioro estructural."
        )
        nivel = NIVEL_AMARILLO
    else:
        diagnostico = "NEUTRAL / ALINEADO"
        alerta = (
            "Sin alerta: los puntos reales están alineados con los puntos esperados."
        )
        nivel = NIVEL_VERDE
    return {
        "puntos_reales": round(float(puntos_reales), 4),
        "xpts": round(float(xpts), 4),
        "delta_xpts": round(delta, 6),
        "diagnostico": diagnostico,
        "alerta": alerta,
        "umbral": UMBRAL_XPTS,
        "nivel": nivel,
        "glifo": GLIFO.get(nivel, "·"),
    }


def _direccion_xg(pendiente: Optional[float]) -> Dict[str, str]:
    """Lectura ofensiva de la pendiente xG [LN-QBE-110]."""
    if pendiente is None:
        return {"clave": "SIN_EVIDENCIA", "etiqueta": "Sin evidencia", "flecha": "·"}
    if pendiente > TOLERANCIA_PENDIENTE:
        return {
            "clave": "ACELERACION",
            "etiqueta": "Aceleración ofensiva",
            "flecha": "↗",
        }
    if pendiente < -TOLERANCIA_PENDIENTE:
        return {
            "clave": "DESACELERACION",
            "etiqueta": "Desaceleración ofensiva",
            "flecha": "↘",
        }
    return {"clave": "ESTABLE", "etiqueta": "Tendencia estable", "flecha": "➔"}


def _direccion_xga(pendiente: Optional[float]) -> Dict[str, str]:
    """Lectura defensiva de la pendiente xGA [LN-QBE-110]: bajar es mejorar."""
    if pendiente is None:
        return {"clave": "SIN_EVIDENCIA", "etiqueta": "Sin evidencia", "flecha": "·"}
    if pendiente < -TOLERANCIA_PENDIENTE:
        return {
            "clave": "CONSOLIDACION",
            "etiqueta": "Consolidación defensiva (mejora)",
            "flecha": "↘",
        }
    if pendiente > TOLERANCIA_PENDIENTE:
        return {
            "clave": "RESQUEBRAJAMIENTO",
            "etiqueta": "Resquebrajamiento defensivo",
            "flecha": "↗",
        }
    return {"clave": "ESTABLE", "etiqueta": "Defensa estable", "flecha": "➔"}


# ═════════════════════════════════════════════════════════════════════════════════════════════
# [ARCH-1.4.49] INGESTA DE SÓLO LECTURA (corpus Opta congelado + tablas 3NF)
# ═════════════════════════════════════════════════════════════════════════════════════════════
def _r(valor: Optional[float], decimales: int = 6) -> Optional[float]:
    """Redondeo de presentación; `None` viaja intacto (no se imputa evidencia)."""
    if valor is None:
        return None
    return round(float(valor), decimales)


def _a_float(valor: Any) -> Optional[float]:
    """Coerción defensiva de una métrica; texto corrupto ⇒ None, nunca cero implícito."""
    if valor is None or isinstance(valor, bool):
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _normalizar_identidad(texto: Any) -> str:
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


def _identidad_coincide(candidato: Any, referencia: Any) -> bool:
    """Casa `matches.home_team_slug` (sin acento) con `standings.equipo` (con acento).

    Regla de identidad, no de negocio: igualdad normalizada o contención de tokens
    distintivos (≥ 4 caracteres) tras descartar conectores y sufijos societarios.
    """
    izquierda = _normalizar_identidad(candidato)
    derecha = _normalizar_identidad(referencia)
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


def ruta_cache_opta(temporada: str) -> str:
    """Ruta absoluta del corpus Opta congelado para la temporada."""
    return os.path.join(
        PROJECT_ROOT, RUTA_CACHE_OPTA_PLANTILLA.format(temporada=str(temporada))
    )


def cargar_cache_opta(temporada: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Carga el corpus Opta (xG/xGA por partido) sin red y sin escritura."""
    ruta = ruta_cache_opta(temporada)
    meta: Dict[str, Any] = {
        "disponible": False,
        "ruta": os.path.relpath(ruta, PROJECT_ROOT).replace("\\", "/"),
        "generado_at": None,
        "fuente": None,
        "partidos_en_cache": 0,
    }
    if not os.path.exists(ruta):
        logger.warning("Corpus Opta ausente: %s", ruta)
        return {}, meta
    with open(ruta, "r", encoding="utf-8") as manejador:
        crudo = json.load(manejador)
    partidos = crudo.get("partidos") if isinstance(crudo, dict) else crudo
    if not isinstance(partidos, dict):
        logger.warning("Corpus Opta sin bloque `partidos` utilizable: %s", ruta)
        return {}, meta
    meta.update(
        {
            "disponible": True,
            "generado_at": (
                crudo.get("generado_at") if isinstance(crudo, dict) else None
            ),
            "fuente": crudo.get("fuente") if isinstance(crudo, dict) else None,
            "partidos_en_cache": len(partidos),
        }
    )
    return partidos, meta


def _entradas_snapshot(snapshot: Any, campo: str) -> List[Dict[str, Any]]:
    """Deserializa el JSON de un snapshot (listas directas o diccionarios envolventes)."""
    crudo = getattr(snapshot, campo, None)
    if crudo is None:
        return []
    if isinstance(crudo, str):
        try:
            crudo = json.loads(crudo)
        except (TypeError, ValueError):
            return []
    if isinstance(crudo, dict):
        for clave in ("partidos", "matches", "posiciones", "standings"):
            contenido = crudo.get(clave)
            if isinstance(contenido, list):
                return [entrada for entrada in contenido if isinstance(entrada, dict)]
        return []
    if isinstance(crudo, list):
        return [entrada for entrada in crudo if isinstance(entrada, dict)]
    return []


def _marcador_desde_texto(texto: Any) -> Tuple[Optional[int], Optional[int]]:
    """Convierte '1 - 2' en (1, 2); cualquier otro formato ⇒ (None, None)."""
    if texto is None:
        return None, None
    partes = str(texto).replace("–", "-").split("-")
    if len(partes) != 2:
        return None, None
    try:
        return int(partes[0].strip()), int(partes[1].strip())
    except ValueError:
        return None, None


def _leer_fixture(sesion: Any, match_id: str) -> Optional[Dict[str, Any]]:
    """Resuelve identidad y marcador del fixture: `matches` (canónico) + snapshot (nombres)."""
    ident = str(match_id or "").strip()
    if not ident:
        return None
    fila = sesion.get(Match, ident)
    entrada: Optional[Dict[str, Any]] = None
    jornada_snapshot: Optional[int] = None
    consulta = select(FixtureSnapshot).order_by(
        FixtureSnapshot.updated_at.desc(), FixtureSnapshot.id.desc()
    )
    for snapshot in sesion.execute(consulta).scalars().all():
        for candidata in _entradas_snapshot(snapshot, "matches_json"):
            if str(candidata.get("id_partido") or "") == ident:
                entrada = candidata
                jornada_snapshot = snapshot.matchday
                break
        if entrada is not None:
            break

    if fila is None and entrada is None:
        return None
    entrada = entrada or {}
    jornada = (
        int(fila.matchday_num)
        if fila is not None and fila.matchday_num is not None
        else int(jornada_snapshot or 0)
    )
    goles_local: Optional[int] = None
    goles_visita: Optional[int] = None
    if fila is not None:
        goles_local = int(fila.score_home) if fila.score_home is not None else None
        goles_visita = int(fila.score_away) if fila.score_away is not None else None
    if goles_local is None or goles_visita is None:
        desde_texto = _marcador_desde_texto(entrada.get("marcador_actual"))
        goles_local = goles_local if goles_local is not None else desde_texto[0]
        goles_visita = goles_visita if goles_visita is not None else desde_texto[1]

    slug_local = str(
        (fila.home_team_slug if fila is not None else None)
        or entrada.get("home_team_slug")
        or ""
    )
    slug_visita = str(
        (fila.away_team_slug if fila is not None else None)
        or entrada.get("away_team_slug")
        or ""
    )
    return {
        "id": ident,
        "jornada": jornada,
        "local": str(entrada.get("local") or slug_local),
        "visita": str(entrada.get("visitante") or slug_visita),
        "local_slug": slug_local,
        "visita_slug": slug_visita,
        "estado": str(
            (fila.status if fila is not None else None) or entrada.get("estado") or ""
        ).upper(),
        "goles_local": goles_local,
        "goles_visita": goles_visita,
        "marcador": (
            f"{goles_local}-{goles_visita}"
            if goles_local is not None and goles_visita is not None
            else str(entrada.get("marcador_actual") or "—")
        ),
        "procedencia": (
            "matches + fixtures_snapshots"
            if fila is not None and entrada is not None
            else ("matches" if fila is not None else "fixtures_snapshots")
        ),
    }


def _partidos_de_club(
    sesion: Any,
    slug: str,
    jornada_corte: Optional[int],
    limite: int = VENTANA_TRAYECTORIA,
) -> List[Dict[str, Any]]:
    """Partidos terminales del club con `matchday_num < N`, en orden cronológico."""
    corte = int(jornada_corte or 0)
    if not slug or corte <= 1:
        return []
    filas = (
        sesion.execute(
            select(Match)
            .where(Match.matchday_num < corte)
            .order_by(Match.matchday_num, Match.id)
        )
        .scalars()
        .all()
    )
    partidos: List[Dict[str, Any]] = []
    for fila in filas:
        if str(fila.status or "").upper() not in ESTADOS_TERMINALES:
            continue
        if fila.score_home is None or fila.score_away is None:
            continue
        es_local = _identidad_coincide(fila.home_team_slug, slug)
        es_visita = _identidad_coincide(fila.away_team_slug, slug)
        if not (es_local or es_visita):
            continue
        goles_favor = int(fila.score_home if es_local else fila.score_away)
        goles_contra = int(fila.score_away if es_local else fila.score_home)
        resultado = (
            "G"
            if goles_favor > goles_contra
            else ("E" if goles_favor == goles_contra else "P")
        )
        partidos.append(
            {
                "match_id": str(fila.id),
                "jornada": int(fila.matchday_num),
                "es_local": es_local,
                "rival_slug": str(
                    fila.away_team_slug if es_local else fila.home_team_slug
                ),
                "goles_favor": goles_favor,
                "goles_contra": goles_contra,
                "resultado": resultado,
            }
        )
    return partidos[-limite:]


def _ventana_5p(
    sesion: Any,
    slug: str,
    jornada_corte: Optional[int],
    partidos_cache: Dict[str, Any],
) -> Dict[str, Any]:
    """Ventana móvil de 5 partidos con sus series de xG/xGA (lookup en corpus congelado)."""
    partidos = _partidos_de_club(sesion, slug, jornada_corte)
    detalle: List[Dict[str, Any]] = []
    for partido in partidos:
        bloque = partidos_cache.get(partido["match_id"]) or {}
        lado = "home" if partido["es_local"] else "away"
        datos = bloque.get(lado) if isinstance(bloque, dict) else None
        xg = _a_float(datos.get("xg")) if isinstance(datos, dict) else None
        xga = _a_float(datos.get("xga")) if isinstance(datos, dict) else None
        detalle.append(
            {**partido, "lado_cache": lado, "xg": _r(xg, 4), "xga": _r(xga, 4)}
        )

    integro = bool(detalle) and all(
        partido["xg"] is not None and partido["xga"] is not None for partido in detalle
    )
    serie_xg = [partido["xg"] for partido in detalle]
    serie_xga = [partido["xga"] for partido in detalle]
    pendiente_xg = calcular_pendiente_lineal_5p(serie_xg) if integro else None
    pendiente_xga = calcular_pendiente_lineal_5p(serie_xga) if integro else None
    return {
        "slug": slug,
        "partidos": detalle,
        "serie_xg": serie_xg,
        "serie_xga": serie_xga,
        "muestra": len(detalle),
        "ventana_completa": len(detalle) == VENTANA_TRAYECTORIA,
        "integro": integro,
        "pendiente_xg": _r(pendiente_xg, 6),
        "pendiente_xga": _r(pendiente_xga, 6),
        "promedio_xg": (
            _r(sum(serie_xg) / len(serie_xg), 4) if integro and serie_xg else None
        ),
        "promedio_xga": (
            _r(sum(serie_xga) / len(serie_xga), 4) if integro and serie_xga else None
        ),
    }


def _snapshot_corte(
    sesion: Any, jornada_corte: Optional[int], temporada: str
) -> Tuple[Any, List[Dict[str, Any]]]:
    """Snapshot de posiciones más reciente con `matchday ≤ N−1` (corte futuro-ciego)."""
    corte = int(jornada_corte or 0)
    if corte < 1:
        return None, []
    consulta = (
        select(StandingSnapshot)
        .where(StandingSnapshot.matchday <= corte)
        .order_by(
            StandingSnapshot.matchday.desc(),
            StandingSnapshot.captured_at.desc(),
            StandingSnapshot.id.desc(),
        )
    )
    respaldo: Tuple[Any, List[Dict[str, Any]]] = (None, [])
    for snapshot in sesion.execute(consulta).scalars().all():
        entradas = _entradas_snapshot(snapshot, "positions_json")
        if not entradas:
            continue
        if str(snapshot.season or "") == str(temporada):
            return snapshot, entradas
        if respaldo[0] is None:
            respaldo = (snapshot, entradas)
    return respaldo


def _entrada_posiciones(
    entradas: Sequence[Dict[str, Any]], slug: str
) -> Optional[Dict[str, Any]]:
    """Localiza la fila del club en el snapshot casando identidades normalizadas."""
    for fila in entradas:
        for clave in ("equipo", "short_name", "slug", "canonical_slug", "team_slug"):
            if clave in fila and _identidad_coincide(fila.get(clave), slug):
                return fila
    return None


def _forma_5p(partidos: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """V31 desde marcadores reales: puntos y racha de la ventana (máximo 15)."""
    puntos = 0
    for partido in partidos:
        if partido["resultado"] == "G":
            puntos += 3
        elif partido["resultado"] == "E":
            puntos += 1
    return {
        "puntos": puntos,
        "racha": "".join(partido["resultado"] for partido in partidos) or "—",
        "partidos": list(partidos),
        "muestra": len(partidos),
    }


# ═════════════════════════════════════════════════════════════════════════════════════════════
# [LN-QBE-110] CELDAS V31/V32 + AUX_M_XG/AUX_M_XGA Y SÍNTESIS DE MOMENTO
# ═════════════════════════════════════════════════════════════════════════════════════════════
def _bando(
    valor_local: Optional[float],
    valor_visita: Optional[float],
    mayor_es_mejor: bool = True,
) -> str:
    """Lectura comparada de dos métricas simétricas (empate técnico ⇒ EQUILIBRADO)."""
    if valor_local is None or valor_visita is None:
        return "SIN EVIDENCIA"
    if abs(float(valor_local) - float(valor_visita)) <= 1e-9:
        return "EQUILIBRADO"
    if mayor_es_mejor:
        return "LOCAL" if float(valor_local) > float(valor_visita) else "VISITANTE"
    return "LOCAL" if float(valor_local) < float(valor_visita) else "VISITANTE"


def _sintesis_momento(
    v29: Dict[str, Any], v30: Dict[str, Any], v31: Dict[str, Any], v32: Dict[str, Any]
) -> Dict[str, Any]:
    """Cruce de las 4 variables: momento, pulso ofensivo, solidez y respaldo estructural."""
    delta_puntos = v29.get("delta_puntos")
    if delta_puntos is None:
        momento = "SIN EVIDENCIA"
    elif delta_puntos > 0:
        momento = "LOCAL"
    elif delta_puntos < 0:
        momento = "VISITANTE"
    else:
        momento = "EQUILIBRADO"

    pulso = _bando(v30.get("pendiente_local"), v30.get("pendiente_visita"), True)
    solidez = _bando(v31.get("pendiente_local"), v31.get("pendiente_visita"), False)
    respaldo = _bando(v32.get("delta_xpts_local"), v32.get("delta_xpts_visita"), False)

    if "SIN EVIDENCIA" in (momento, respaldo):
        divergencia = "SIN EVIDENCIA"
    elif respaldo == "EQUILIBRADO":
        divergencia = "SIN SESGO ESTRUCTURAL"
    elif momento == respaldo:
        divergencia = "ALINEADO"
    else:
        divergencia = "DIVERGENTE"

    return {
        "momento_5p": momento,
        "pulso_ofensivo": pulso,
        "solidez_defensiva": solidez,
        "respaldo_estructural": respaldo,
        "divergencia": divergencia,
        "lectura": (
            f"Forma {momento}; pulso ofensivo {pulso}; solidez {solidez}; "
            f"respaldo estructural {respaldo}; veredicto {divergencia}."
        ),
        "nota": (
            "Un ΔxPTS bajo indica menos sobre-rendimiento (cosecha respaldada); "
            "un ΔxPTS alto delata puntos inflados por varianza favorable."
        ),
    }


def _semaforo(nivel: str, detalle: str) -> Dict[str, str]:
    return {"nivel": nivel, "glifo": GLIFO.get(nivel, "·"), "detalle": detalle}


def _reporte_no_encontrado(match_id: str, temporada: str) -> Dict[str, Any]:
    return {
        "nodos_gobernanza": list(NODOS_GOBIERNO),
        "sandbox": "TRAYECTORIA_MOMENTO_DIM8",
        "modo": "SOLO_LECTURA",
        "temporada": str(temporada),
        "match": {"id": str(match_id)},
        "corte_n_1": None,
        "dimension_8_trayectoria": {},
        "sintesis_momento": {},
        "semaforos": {},
        "status": "NO_ENCONTRADO",
        "motivo": f"El fixture `{match_id}` no existe en `matches` ni en `fixtures_snapshots`.",
        "escritura_bd": False,
        "llamadas_red": False,
    }


def ejecutar_sandbox_trayectoria_partido(
    match_id: str, temporada: str = TEMPORADA_DEFAULT
) -> Dict[str, Any]:
    """Orquesta un fixture: corte N−1, ventanas 5P, celdas V31/V32 + AUX_M_XG/AUX_M_XGA y síntesis. Sólo lectura."""
    temporada = str(temporada)
    partidos_cache, cache_meta = cargar_cache_opta(temporada)
    gateway = PersistenceGateway()

    with gateway.read_session() as sesion:
        fixture = _leer_fixture(sesion, match_id)
        if fixture is None:
            return _reporte_no_encontrado(match_id, temporada)

        jornada = int(fixture.get("jornada") or 0)
        corte = jornada - 1 if jornada >= 2 else None

        ventana_local = _ventana_5p(
            sesion, fixture["local_slug"], corte, partidos_cache
        )
        ventana_visita = _ventana_5p(
            sesion, fixture["visita_slug"], corte, partidos_cache
        )

        snapshot, entradas = _snapshot_corte(sesion, corte, temporada)
        pj_max = max((int(fila.get("pj") or 0) for fila in entradas), default=0)
        matchday_snapshot = int(snapshot.matchday) if snapshot is not None else None
        estricto = bool(matchday_snapshot is not None and pj_max <= matchday_snapshot)
        fidelidad = {
            "snapshot_id": getattr(snapshot, "id", None),
            "matchday_snapshot": matchday_snapshot,
            "captured_at": str(getattr(snapshot, "captured_at", "") or ""),
            "pj_max": pj_max,
            "corte_solicitado": corte,
            "estricto": estricto,
            "advertencia": (
                ""
                if estricto or snapshot is None
                else (
                    f"El snapshot J{matchday_snapshot} publica clubes con pj_max={pj_max} "
                    f"(> corte {matchday_snapshot}): la foto incluye resultados posteriores. "
                    "Se conserva la etiqueta del snapshot como testigo y se advierte la "
                    "contaminación; la ventana de trayectoria sí respeta J < N."
                )
            ),
        }
        entrada_local = _entrada_posiciones(entradas, fixture["local_slug"])
        entrada_visita = _entrada_posiciones(entradas, fixture["visita_slug"])

        # ── V31 · Forma 5P (puntos reales de la ventana) ────────────────────────────────
        forma_local = _forma_5p(ventana_local["partidos"])
        forma_visita = _forma_5p(ventana_visita["partidos"])
        evidencia_forma = (
            forma_local["muestra"] == VENTANA_TRAYECTORIA
            and forma_visita["muestra"] == VENTANA_TRAYECTORIA
        )
        v29 = {
            "id": "V31",
            "variable": "Forma 5P (ΔPts últimos 5)",
            "unidad": "puntos",
            "estado": ESTADO_EVALUADO if evidencia_forma else ESTADO_SIN_EVIDENCIA,
            "puntos_local": forma_local["puntos"] if forma_local["muestra"] else None,
            "puntos_visita": (
                forma_visita["puntos"] if forma_visita["muestra"] else None
            ),
            "delta_puntos": (
                forma_local["puntos"] - forma_visita["puntos"]
                if evidencia_forma
                else None
            ),
            "racha_local": forma_local["racha"],
            "racha_visita": forma_visita["racha"],
            "muestra_local": forma_local["muestra"],
            "muestra_visita": forma_visita["muestra"],
            "ventana_completa": (
                forma_local["muestra"] == VENTANA_TRAYECTORIA
                and forma_visita["muestra"] == VENTANA_TRAYECTORIA
            ),
            "partidos_local": forma_local["partidos"],
            "partidos_visita": forma_visita["partidos"],
            "nota": (
                "Pts5P = 3G + 1E por club; ventana = últimos 5 partidos terminales con J < N. "
                "El campo `forma` del snapshot sólo se usa como testigo de contraste."
            ),
        }

        # ── AUX_M_XG · Pendiente de peligro ofensivo (xG) ────────────────────────────────────
        m_xg_local = ventana_local["pendiente_xg"]
        m_xg_visita = ventana_visita["pendiente_xg"]
        direccion_xg_local = _direccion_xg(m_xg_local)
        direccion_xg_visita = _direccion_xg(m_xg_visita)
        evidencia_xg = (
            ventana_local["ventana_completa"]
            and ventana_local["integro"]
            and ventana_visita["ventana_completa"]
            and ventana_visita["integro"]
        )
        v30 = {
            "id": "AUX_M_XG",
            "variable": "Pendiente xG 5P (m_xG)",
            "unidad": "xG/partido",
            "estado": ESTADO_EVALUADO if evidencia_xg else ESTADO_SIN_EVIDENCIA,
            "pendiente_local": m_xg_local,
            "pendiente_visita": m_xg_visita,
            "direccion_local": direccion_xg_local["etiqueta"],
            "direccion_visita": direccion_xg_visita["etiqueta"],
            "clave_local": direccion_xg_local["clave"],
            "clave_visita": direccion_xg_visita["clave"],
            "flecha_local": direccion_xg_local["flecha"],
            "flecha_visita": direccion_xg_visita["flecha"],
            "serie_local": ventana_local["serie_xg"],
            "serie_visita": ventana_visita["serie_xg"],
            "promedio_local": ventana_local["promedio_xg"],
            "promedio_visita": ventana_visita["promedio_xg"],
            "muestra_local": ventana_local["muestra"],
            "muestra_visita": ventana_visita["muestra"],
            "nota": (
                "OLS exacta sobre t=1..5 (denominador 10); m>0 ⇒ aceleración ofensiva, "
                "m<0 ⇒ desaceleración. xG del corpus Opta congelado, jamás imputado."
            ),
        }

        # ── AUX_M_XGA · Pendiente de vulnerabilidad defensiva (xGA) ───────────────────────────
        m_xga_local = ventana_local["pendiente_xga"]
        m_xga_visita = ventana_visita["pendiente_xga"]
        direccion_xga_local = _direccion_xga(m_xga_local)
        direccion_xga_visita = _direccion_xga(m_xga_visita)
        evidencia_xga = (
            ventana_local["ventana_completa"]
            and ventana_local["integro"]
            and ventana_visita["ventana_completa"]
            and ventana_visita["integro"]
        )
        v31 = {
            "id": "AUX_M_XGA",
            "variable": "Pendiente xGA 5P (m_xGA)",
            "unidad": "xGA/partido",
            "estado": ESTADO_EVALUADO if evidencia_xga else ESTADO_SIN_EVIDENCIA,
            "pendiente_local": m_xga_local,
            "pendiente_visita": m_xga_visita,
            "direccion_local": direccion_xga_local["etiqueta"],
            "direccion_visita": direccion_xga_visita["etiqueta"],
            "clave_local": direccion_xga_local["clave"],
            "clave_visita": direccion_xga_visita["clave"],
            "flecha_local": direccion_xga_local["flecha"],
            "flecha_visita": direccion_xga_visita["flecha"],
            "serie_local": ventana_local["serie_xga"],
            "serie_visita": ventana_visita["serie_xga"],
            "promedio_local": ventana_local["promedio_xga"],
            "promedio_visita": ventana_visita["promedio_xga"],
            "muestra_local": ventana_local["muestra"],
            "muestra_visita": ventana_visita["muestra"],
            "nota": (
                "OLS exacta sobre t=1..5 (denominador 10); m<0 ⇒ consolidación defensiva, "
                "m>0 ⇒ resquebrajamiento. xGA del corpus Opta congelado."
            ),
        }

        # ── V32 · ΔxPTS (PTS − xPTS) con auditoría de fidelidad del corte ───────────────
        def _puntos_y_xpts(
            entrada: Optional[Dict[str, Any]],
        ) -> Tuple[Optional[float], Optional[float]]:
            if entrada is None:
                return None, None
            return _a_float(entrada.get("puntos")), _a_float(entrada.get("xpts"))

        pts_local, xpts_local = _puntos_y_xpts(entrada_local)
        pts_visita, xpts_visita = _puntos_y_xpts(entrada_visita)
        diagnostico_local = (
            evaluar_diagnostico_xpts(pts_local, xpts_local)
            if pts_local is not None and xpts_local is not None
            else None
        )
        diagnostico_visita = (
            evaluar_diagnostico_xpts(pts_visita, xpts_visita)
            if pts_visita is not None and xpts_visita is not None
            else None
        )
        evidencia_xpts = (
            diagnostico_local is not None and diagnostico_visita is not None
        )
        v32 = {
            "id": "V32",
            "variable": "ΔxPTS (PTS − xPTS)",
            "unidad": "puntos",
            "estado": ESTADO_EVALUADO if evidencia_xpts else ESTADO_SIN_EVIDENCIA,
            "puntos_local": _r(pts_local, 4),
            "xpts_local": _r(xpts_local, 4),
            "delta_xpts_local": (
                diagnostico_local["delta_xpts"] if diagnostico_local else None
            ),
            "diagnostico_local": (
                diagnostico_local["diagnostico"]
                if diagnostico_local
                else ESTADO_SIN_EVIDENCIA
            ),
            "alerta_local": (
                diagnostico_local["alerta"]
                if diagnostico_local
                else "Sin fila del club en el snapshot de posiciones del corte."
            ),
            "nivel_local": (
                diagnostico_local["nivel"] if diagnostico_local else NIVEL_NEUTRAL
            ),
            "glifo_local": (
                diagnostico_local["glifo"]
                if diagnostico_local
                else GLIFO[NIVEL_NEUTRAL]
            ),
            "puntos_visita": _r(pts_visita, 4),
            "xpts_visita": _r(xpts_visita, 4),
            "delta_xpts_visita": (
                diagnostico_visita["delta_xpts"] if diagnostico_visita else None
            ),
            "diagnostico_visita": (
                diagnostico_visita["diagnostico"]
                if diagnostico_visita
                else ESTADO_SIN_EVIDENCIA
            ),
            "alerta_visita": (
                diagnostico_visita["alerta"]
                if diagnostico_visita
                else "Sin fila del club en el snapshot de posiciones del corte."
            ),
            "nivel_visita": (
                diagnostico_visita["nivel"] if diagnostico_visita else NIVEL_NEUTRAL
            ),
            "glifo_visita": (
                diagnostico_visita["glifo"]
                if diagnostico_visita
                else GLIFO[NIVEL_NEUTRAL]
            ),
            "delta_xpts_neto": (
                round(
                    float(diagnostico_local["delta_xpts"])
                    - float(diagnostico_visita["delta_xpts"]),
                    6,
                )
                if evidencia_xpts
                else None
            ),
            "umbral": UMBRAL_XPTS,
            "fuente": (
                f"standings_snapshots#{getattr(snapshot, 'id', None)} (J{matchday_snapshot})"
                if snapshot is not None
                else "standings_snapshots (sin snapshot ≤ corte)"
            ),
            "fidelidad_corte": fidelidad,
            "nota": (
                "PTS y xPTS se leen del snapshot histórico ≤ N−1; no se sustituyen por la "
                "tabla viva. Δ ≥ +3 ⇒ sobre-rendimiento; Δ ≤ −3 ⇒ sub-rendimiento."
            ),
        }

        dimension_8 = {"V31": v29, "AUX_M_XG": v30, "AUX_M_XGA": v31, "V32": v32}
        sintesis = _sintesis_momento(v29, v30, v31, v32)
        evaluadas = sum(
            1 for celda in dimension_8.values() if celda["estado"] == ESTADO_EVALUADO
        )
        if evaluadas == len(dimension_8):
            status = "EXITO"
            motivo = "Las 4 variables V31/V32 + AUX_M_XG/AUX_M_XGA quedaron evaluadas con evidencia íntegra."
        elif evaluadas:
            status = "PARCIAL"
            motivo = (
                f"{evaluadas}/4 variables evaluadas; el resto degradó a SIN EVIDENCIA."
            )
        else:
            status = "SIN_EVIDENCIA"
            motivo = (
                "No hay ventana previa ni snapshot ≤ N−1 para evaluar la trayectoria."
            )

        cobertura_integra = bool(ventana_local["integro"] and ventana_visita["integro"])
        cobertura_completa = bool(
            ventana_local["ventana_completa"] and ventana_visita["ventana_completa"]
        )
        nivel_trayectoria = (
            NIVEL_VERDE
            if evaluadas == len(dimension_8)
            else (NIVEL_AMARILLO if evaluadas else NIVEL_NEUTRAL)
        )
        nivel_corte = (
            NIVEL_VERDE
            if estricto
            else (NIVEL_AMARILLO if snapshot is not None else NIVEL_NEUTRAL)
        )
        nivel_cobertura = (
            NIVEL_VERDE
            if cobertura_integra and cobertura_completa
            else (
                NIVEL_AMARILLO
                if (ventana_local["muestra"] or ventana_visita["muestra"])
                else NIVEL_NEUTRAL
            )
        )
        semaforos = {
            "TRAYECTORIA": _semaforo(
                nivel_trayectoria, f"{evaluadas}/4 celdas V31/V32 + AUX_M_XG/AUX_M_XGA evaluadas."
            ),
            "CORTE": _semaforo(
                nivel_corte,
                (
                    f"Snapshot J{matchday_snapshot} estricto (pj_max={pj_max})."
                    if estricto
                    else (fidelidad["advertencia"] or "Sin snapshot ≤ corte.")
                ),
            ),
            "COBERTURA_OPTA": _semaforo(
                nivel_cobertura,
                (
                    f"Local {ventana_local['muestra']}/5 · Visita {ventana_visita['muestra']}/5 · "
                    f"series íntegras: {cobertura_integra}."
                ),
            ),
        }

        return {
            "nodos_gobernanza": list(NODOS_GOBIERNO),
            "sandbox": "TRAYECTORIA_MOMENTO_DIM8",
            "modo": "SOLO_LECTURA",
            "temporada": temporada,
            "match": fixture,
            "corte_n_1": {
                "jornada_corte": corte,
                "regla": "matchday_num < N (futuro-ciego)",
                "partidos_local": ventana_local["partidos"],
                "partidos_visita": ventana_visita["partidos"],
                "muestra_local": ventana_local["muestra"],
                "muestra_visita": ventana_visita["muestra"],
                "ventana_completa": cobertura_completa,
            },
            "cache_opta": cache_meta,
            "dimension_8_trayectoria": dimension_8,
            "sintesis_momento": sintesis,
            "semaforos": semaforos,
            "status": status,
            "motivo": motivo,
            "escritura_bd": False,
            "llamadas_red": False,
        }


# ═════════════════════════════════════════════════════════════════════════════════════════════
# [ARCH-1.4.49] MODO JORNADA (barrido de la cartelera completa)
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
        for entrada in _entradas_snapshot(snapshot, "matches_json"):
            ident = str(entrada.get("id_partido") or "")
            if ident and ident not in identificadores:
                identificadores.append(ident)
        if identificadores:
            return identificadores
    filas = (
        sesion.execute(
            select(Match).where(Match.matchday_num == int(jornada)).order_by(Match.id)
        )
        .scalars()
        .all()
    )
    return [str(fila.id) for fila in filas]


def ejecutar_sandbox_trayectoria_jornada(
    jornada: int, temporada: str = TEMPORADA_DEFAULT
) -> Dict[str, Any]:
    """Barrido soberano de la jornada: un reporte por fixture + conteo de estados."""
    gateway = PersistenceGateway()
    with gateway.read_session() as sesion:
        identificadores = _ids_de_jornada(sesion, jornada)

    reportes = [
        ejecutar_sandbox_trayectoria_partido(ident, temporada)
        for ident in identificadores
    ]
    conteo = {"EXITO": 0, "PARCIAL": 0, "SIN_EVIDENCIA": 0, "NO_ENCONTRADO": 0}
    for reporte in reportes:
        estado = str(reporte.get("status") or "NO_ENCONTRADO")
        conteo[estado] = conteo.get(estado, 0) + 1
    return {
        "nodos_gobernanza": list(NODOS_GOBIERNO),
        "sandbox": "TRAYECTORIA_MOMENTO_DIM8_JORNADA",
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
# [ARCH-1.4.49] TABLERO ASCII DE CONSOLA (presentación pura, cero cálculo)
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
    print(
        "┌" + encabezado + ("─" * max(0, interior - _ancho_visible(encabezado))) + "┐"
    )
    for fila in filas:
        print("│ " + _pad(_recortar(fila, interior - 2), interior - 2) + " │")
    print("└" + ("─" * interior) + "┘")


def _linea(etiqueta: str, texto: str) -> str:
    """Fila etiqueta/valor del bloque de contexto (etiqueta alineada en 12 columnas)."""
    return f"{_pad(etiqueta, 12)}{texto}"


def _num(valor: Optional[float], decimales: int = 4, ancho: int = 8) -> str:
    """Formato numérico con signo y ancho fijo; `—` cuando la evidencia no existe."""
    if valor is None:
        return "—".rjust(ancho)
    return f"{float(valor):+.{decimales}f}".rjust(ancho)


def _num_abs(valor: Optional[float], decimales: int = 2, ancho: int = 8) -> str:
    """Formato numérico SIN signo (magnitudes acumuladas: PTS, xPTS, goles)."""
    if valor is None:
        return "—".rjust(ancho)
    return f"{float(valor):.{decimales}f}".rjust(ancho)


def _entero_o_guion(valor: Any) -> str:
    """Puntos acumulados legibles (`13`, no `13.0`); `—` si no hay evidencia."""
    if valor is None:
        return "—"
    try:
        return f"{float(valor):g}"
    except (TypeError, ValueError):
        return "—"


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


def _bloque_experimento_trayectoria(reporte: Dict[str, Any]) -> None:
    """Caja 1: identidad del fixture, corte N−1, corpus y fidelidad del snapshot."""
    fixture = reporte.get("match") or {}
    corte = reporte.get("corte_n_1") or {}
    cache = reporte.get("cache_opta") or {}
    v32 = (reporte.get("dimension_8_trayectoria") or {}).get("V32") or {}
    fidelidad = v32.get("fidelidad_corte") or {}
    nombre_cache = os.path.basename(str(cache.get("ruta") or "—").replace("\\", "/"))
    filas: List[str] = [
        _linea("Fixture", f"{fixture.get('id')} · J{fixture.get('jornada')}"),
        _linea("Partido", f"{fixture.get('local')} vs {fixture.get('visita')}"),
        _linea(
            "Marcador", f"{fixture.get('marcador')} · estado {fixture.get('estado')}"
        ),
        _linea(
            "Corte N−1",
            f"J{corte.get('jornada_corte')} · regla: {corte.get('regla')}",
        ),
        _linea(
            "Ventana 5P",
            f"Local {corte.get('muestra_local')}/5 · Visita {corte.get('muestra_visita')}/5 · "
            f"completa: {corte.get('ventana_completa')}",
        ),
        _linea(
            "Corpus Opta",
            f"{nombre_cache} · "
            f"{cache.get('partidos_en_cache')} partidos · "
            f"{str(cache.get('generado_at') or '—')[:10]}",
        ),
        _linea(
            "Snapshot",
            f"#{fidelidad.get('snapshot_id')} J{fidelidad.get('matchday_snapshot')} · "
            f"pj_max={fidelidad.get('pj_max')} · estricto={fidelidad.get('estricto')}",
        ),
        _linea(
            "Régimen", "SOLO LECTURA · 0 escrituras en la bóveda · 0 llamadas de red"
        ),
    ]
    if fidelidad.get("advertencia"):
        filas.append("─" * (ANCHO_TABLERO - 4))
        filas.extend(_envolver(f"⚠ CORTE: {fidelidad['advertencia']}"))
    _caja("TRAYECTORIA & MOMENTO · DIM 8 (V31/V32 + AUX_M_XG/AUX_M_XGA) · [LN-QBE-110]", filas)


def _bloque_forma_5p(reporte: Dict[str, Any]) -> None:
    """Caja 2: V31 · puntos y racha de los últimos 5 partidos por club."""
    fixture = reporte.get("match") or {}
    celda = (reporte.get("dimension_8_trayectoria") or {}).get("V31") or {}
    filas: List[str] = [
        f"{_pad('EQUIPO', 18)}{_pad('RACHA', 10)}{'PTS/15'.rjust(8)}{'MUESTRA'.rjust(9)}  ESTADO",
        "─" * (ANCHO_TABLERO - 4),
    ]
    for etiqueta, nombre in (
        ("LOCAL", fixture.get("local")),
        ("VISITA", fixture.get("visita")),
    ):
        sufijo = "local" if etiqueta == "LOCAL" else "visita"
        filas.append(
            f"{_pad(str(nombre or '—')[:17], 18)}"
            f"{_pad(str(celda.get(f'racha_{sufijo}') or '—'), 10)}"
            f"{str(celda.get(f'puntos_{sufijo}') if celda.get(f'puntos_{sufijo}') is not None else '—').rjust(8)}"
            f"{str(celda.get(f'muestra_{sufijo}') or 0).rjust(9)}"
            f"  {_glifo_celda(celda)} {celda.get('estado')}"
        )
    delta = celda.get("delta_puntos")
    filas.append("─" * (ANCHO_TABLERO - 4))
    filas.append(
        f"{_pad('ΔPts 5P', 18)}"
        f"{('%+d' % delta) if delta is not None else '—'} "
        f"(local − visita; cota [−15, +15])"
    )
    filas.extend(_envolver(str(celda.get("nota") or "")))
    _caja("V31 · FORMA 5P (MOMENTO DE PUNTOS)", filas)


def _bloque_pendientes(reporte: Dict[str, Any]) -> None:
    """Caja 3: AUX_M_XG/AUX_M_XGA · pendientes OLS de xG y xGA con su lectura direccional."""
    fixture = reporte.get("match") or {}
    dimension = reporte.get("dimension_8_trayectoria") or {}
    v30 = dimension.get("AUX_M_XG") or {}
    v31 = dimension.get("AUX_M_XGA") or {}
    filas: List[str] = [
        f"{_pad('EQUIPO', 16)}{'m_xG'.rjust(8)}  {_pad('DIRECCIÓN xG', 18)}"
        f"{'m_xGA'.rjust(8)}  DIRECCIÓN xGA",
        "─" * (ANCHO_TABLERO - 4),
    ]
    for etiqueta, nombre in (
        ("local", fixture.get("local")),
        ("visita", fixture.get("visita")),
    ):
        direccion_xg = (
            f"{v30.get(f'flecha_{etiqueta}') or '·'} "
            f"{v30.get(f'clave_{etiqueta}') or 'SIN_EVIDENCIA'}"
        )
        direccion_xga = (
            f"{v31.get(f'flecha_{etiqueta}') or '·'} "
            f"{v31.get(f'clave_{etiqueta}') or 'SIN_EVIDENCIA'}"
        )
        filas.append(
            f"{_pad(str(nombre or '—')[:15], 16)}"
            f"{_num(v30.get(f'pendiente_{etiqueta}'), 4, 8)}  "
            f"{_pad(direccion_xg, 18)}"
            f"{_num(v31.get(f'pendiente_{etiqueta}'), 4, 8)}  "
            f"{direccion_xga}"
        )
    filas.append("─" * (ANCHO_TABLERO - 4))
    filas.append(
        f"{_pad('Serie xG L', 12)}{' → '.join(f'{v:.4f}' for v in (v30.get('serie_local') or []) if v is not None) or '—'}"
    )
    filas.append(
        f"{_pad('Serie xG V', 12)}{' → '.join(f'{v:.4f}' for v in (v30.get('serie_visita') or []) if v is not None) or '—'}"
    )
    filas.append(
        f"{_pad('Serie xGA L', 12)}{' → '.join(f'{v:.4f}' for v in (v31.get('serie_local') or []) if v is not None) or '—'}"
    )
    filas.append(
        f"{_pad('Serie xGA V', 12)}{' → '.join(f'{v:.4f}' for v in (v31.get('serie_visita') or []) if v is not None) or '—'}"
    )
    filas.append("─" * (ANCHO_TABLERO - 4))
    filas.extend(
        _envolver(
            "↗/↘ = signo de la pendiente · xG: ACELERACION / DESACELERACION · "
            "xGA: RESQUEBRAJAMIENTO / CONSOLIDACION · ESTABLE dentro de la tolerancia"
        )
    )
    filas.extend(
        _envolver("Pendiente OLS exacta [LN-QBE-110]: m = Σ(t−3)(y_t−ȳ)/10 con t=1..5.")
    )
    _caja("AUX_M_XG/AUX_M_XGA · PENDIENTES DE PELIGRO (5P)", filas)


def _bloque_varianza_xpts(reporte: Dict[str, Any]) -> None:
    """Caja 4: V32 · PTS vs xPTS, diagnóstico de varianza y fidelidad del corte."""
    fixture = reporte.get("match") or {}
    celda = (reporte.get("dimension_8_trayectoria") or {}).get("V32") or {}
    fidelidad = celda.get("fidelidad_corte") or {}
    filas: List[str] = [
        f"{_pad('EQUIPO', 18)}{'PTS'.rjust(6)}{'xPTS'.rjust(8)}{'ΔxPTS'.rjust(9)}  DIAGNÓSTICO",
        "─" * (ANCHO_TABLERO - 4),
    ]
    for etiqueta, nombre in (
        ("local", fixture.get("local")),
        ("visita", fixture.get("visita")),
    ):
        filas.append(
            f"{_pad(str(nombre or '—')[:17], 18)}"
            f"{_entero_o_guion(celda.get(f'puntos_{etiqueta}')).rjust(6)}"
            f"{_num_abs(celda.get(f'xpts_{etiqueta}'), 2, 8)}"
            f"{_num(celda.get(f'delta_xpts_{etiqueta}'), 4, 9)}"
            f"  {celda.get(f'glifo_{etiqueta}') or '·'} {celda.get(f'diagnostico_{etiqueta}') or '—'}"
        )
    filas.append("─" * (ANCHO_TABLERO - 4))
    filas.append(
        f"{_pad('ΔxPTS neto', 18)}{_num(celda.get('delta_xpts_neto'), 4, 9)}"
        f"  (local − visita; umbral ±{UMBRAL_XPTS:.1f})"
    )
    filas.append(f"{_pad('Fuente', 18)}{celda.get('fuente') or '—'}")
    filas.append("─" * (ANCHO_TABLERO - 4))
    filas.extend(_envolver(f"LOCAL: {celda.get('alerta_local') or '—'}"))
    filas.extend(_envolver(f"VISITA: {celda.get('alerta_visita') or '—'}"))
    if fidelidad.get("advertencia"):
        filas.append("─" * (ANCHO_TABLERO - 4))
        filas.extend(_envolver(f"FIDELIDAD DEL CORTE: {fidelidad['advertencia']}"))
    _caja("V32 · VARIANZA xPTS (SUERTE vs ESTRUCTURA)", filas)


def _bloque_sintesis(reporte: Dict[str, Any]) -> None:
    """Caja 5: lectura cruzada de las 4 variables (sin cálculo, sólo presentación)."""
    sintesis = reporte.get("sintesis_momento") or {}
    filas: List[str] = []
    for clave, etiqueta in (
        ("momento_5p", "Momento 5P"),
        ("pulso_ofensivo", "Pulso ofensivo"),
        ("solidez_defensiva", "Solidez defensiva"),
        ("respaldo_estructural", "Respaldo estructural"),
        ("divergencia", "Divergencia"),
    ):
        filas.append(f"{_pad(etiqueta, 24)}{sintesis.get(clave) or 'SIN EVIDENCIA'}")
    filas.append("─" * (ANCHO_TABLERO - 4))
    filas.extend(_envolver(sintesis.get("lectura") or ""))
    filas.extend(_envolver(sintesis.get("nota") or ""))
    _caja("SÍNTESIS DE MOMENTO (V31/V32 + AUX_M_XG/AUX_M_XGA)", filas)


def _bloque_semaforos_trayectoria(reporte: Dict[str, Any]) -> None:
    """Caja 6: salud fiduciaria del experimento (trayectoria · corte · cobertura)."""
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


def imprimir_tablero_trayectoria_consola(reporte: Dict[str, Any]) -> None:
    """Renderiza el tablero completo de un partido ([ARCH-1.4.49]). Presentación pura."""
    print()
    _caja(
        "Q-BE · LABORATORIO TRAYECTORIA & MOMENTO · DIM 8 (V31/V32 + AUX_M_XG/AUX_M_XGA)",
        [
            f"[{NODOS_GOBIERNO[0]}] / [{NODOS_GOBIERNO[1]}] · SÓLO LECTURA · corte N−1 (futuro-ciego)",
            f"Ventana móvil 5P · pendiente OLS exacta (denominador 10) · umbral ΔxPTS ±{UMBRAL_XPTS:.1f}",
            "Corpus Opta congelado · 0 escrituras en la bóveda · 0 llamadas de red",
        ],
    )
    _bloque_experimento_trayectoria(reporte)
    _bloque_forma_5p(reporte)
    _bloque_pendientes(reporte)
    _bloque_varianza_xpts(reporte)
    _bloque_sintesis(reporte)
    _bloque_semaforos_trayectoria(reporte)
    print("─" * ANCHO_TABLERO)
    print(f" STATUS: {reporte.get('status')} · {reporte.get('motivo')}")
    print(
        " Sólo lectura · 0 escrituras en la bóveda · 0 llamadas de red · "
        f"nodos {' + '.join(NODOS_GOBIERNO)}"
    )
    print()


def imprimir_tablero_jornada_trayectoria_consola(resumen: Dict[str, Any]) -> None:
    """Tablero compacto de la jornada: forma, pendientes y ΔxPTS por fixture."""
    jornada = resumen.get("jornada")
    conteo = resumen.get("conteo_estados") or {}
    glifos = {
        "EXITO": "🟢",
        "PARCIAL": "🟡",
        "SIN_EVIDENCIA": "⚪",
        "NO_ENCONTRADO": "⚫",
    }
    print()
    _caja(
        f"JORNADA {jornada} · TRAYECTORIA & MOMENTO [LN-QBE-110]",
        [
            f"[{NODOS_GOBIERNO[0]}] / [{NODOS_GOBIERNO[1]}] · SÓLO LECTURA · "
            f"temporada {resumen.get('temporada')} · {resumen.get('total_partidos')} fixtures",
            " · ".join(
                f"{glifos.get(estado, '·')} {estado}: {cantidad}"
                for estado, cantidad in conteo.items()
            ),
        ],
    )

    filas: List[str] = [
        f"{_pad('FIXTURE', 14)}{_pad('LOCAL', 10)}{_pad('VISITA', 10)}"
        f"{'PTSL'.rjust(5)}{'PTSV'.rjust(5)}{'ΔPTS'.rjust(5)}"
        f"{'mxG_L'.rjust(7)}{'mxG_V'.rjust(7)}{'mGA_L'.rjust(7)}{'mGA_V'.rjust(7)}"
        f"{'ΔxPTS'.rjust(7)}  ST",
        "─" * (ANCHO_TABLERO - 4),
    ]
    for reporte in resumen.get("partidos") or []:
        fixture = reporte.get("match") or {}
        dimension = reporte.get("dimension_8_trayectoria") or {}
        v29 = dimension.get("V31") or {}
        v30 = dimension.get("AUX_M_XG") or {}
        v31 = dimension.get("AUX_M_XGA") or {}
        v32 = dimension.get("V32") or {}
        filas.append(
            f"{_pad(str(fixture.get('id') or '—')[:13], 14)}"
            f"{_pad(str(fixture.get('local') or '—')[:9], 10)}"
            f"{_pad(str(fixture.get('visita') or '—')[:9], 10)}"
            f"{str(v29.get('puntos_local') if v29.get('puntos_local') is not None else '—').rjust(5)}"
            f"{str(v29.get('puntos_visita') if v29.get('puntos_visita') is not None else '—').rjust(5)}"
            f"{_num(v29.get('delta_puntos'), 0, 5)}"
            f"{_num(v30.get('pendiente_local'), 3, 7)}"
            f"{_num(v30.get('pendiente_visita'), 3, 7)}"
            f"{_num(v31.get('pendiente_local'), 3, 7)}"
            f"{_num(v31.get('pendiente_visita'), 3, 7)}"
            f"{_num(v32.get('delta_xpts_neto'), 3, 7)}"
            f"  {glifos.get(str(reporte.get('status')), '·')}"
        )
    filas.append("─" * (ANCHO_TABLERO - 4))
    filas.extend(
        _envolver(
            "PTSL/PTSV = puntos 5P · mxG/mGA = unidades por partido · "
            "ΔxPTS neto = local − visita · — ⇒ SIN EVIDENCIA"
        )
    )
    _caja("MATRIZ DE TRAYECTORIA DE LA CARTELERA", filas)
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
        prog="sandbox_trayectoria_momento_pipeline",
        description=(
            "[LN-QBE-110] / [ARCH-1.4.49] Laboratorio CLI de la Dimensión 8: forma 5P, "
            "pendientes xG/xGA y varianza xPTS por fixture."
        ),
    )
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument(
        "--partido", metavar="ID", help="ID canónico del fixture (ej. LIGAMX-J11-07)."
    )
    grupo.add_argument(
        "--jornada", type=int, metavar="N", help="Barrido completo de la jornada N."
    )
    parser.add_argument(
        "--temporada",
        default=TEMPORADA_DEFAULT,
        help="Etiqueta de temporada (default 2026).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="salida_json",
        help="Emite JSON serializable.",
    )
    parser.add_argument("--verbose", action="store_true", help="Activa logging DEBUG.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Punto de entrada CLI. Sólo lectura; jamás escribe en la bóveda ni abre red."""
    argumentos = _construir_parser().parse_args(
        list(argv) if argv is not None else None
    )
    logging.basicConfig(
        level=logging.DEBUG if argumentos.verbose else logging.WARNING,
        format="%(asctime)s · %(levelname)s · %(name)s · %(message)s",
    )
    try:
        if argumentos.partido:
            reporte = ejecutar_sandbox_trayectoria_partido(
                argumentos.partido, argumentos.temporada
            )
            if argumentos.salida_json:
                print(json.dumps(reporte, ensure_ascii=False, indent=2, default=str))
            else:
                imprimir_tablero_trayectoria_consola(reporte)
            return 0 if reporte.get("status") != "NO_ENCONTRADO" else 2

        resumen = ejecutar_sandbox_trayectoria_jornada(
            int(argumentos.jornada), argumentos.temporada
        )
        if argumentos.salida_json:
            print(json.dumps(resumen, ensure_ascii=False, indent=2, default=str))
        else:
            imprimir_tablero_jornada_trayectoria_consola(resumen)
        return 0 if resumen.get("total_partidos") else 2
    except Exception as error:  # pragma: no cover - red de seguridad de consola
        logger.error("Fallo del sandbox de trayectoria: %s", error, exc_info=True)
        print(f"[ERROR] {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
