# -*- coding: utf-8 -*-
"""
Q-BE ECOSYSTEM · DATA NEXUS — CENTINELA DE MACRO-ESTADÍSTICAS (FOTMOB `leagues?tab=stats`)
[ARCH-1.4.59] Materializa `data/cache_macro_stats_liga_mx_2026.json`: congela los leaderboards
torneales (equipo y plantilla) del proveedor en un artefacto idempotente de solo lectura.
Régimen: [HÍBRIDO DUAL-TRACK] — extractor y artefacto [DBBD-FUNGIBLE]; el mapa declarativo y la
cobertura de variables responden al contrato sellado de `[LN-QBE-120]`.

Base de Gobierno: Kybern Framework v13.5 / CERO ALAMBRADO

Axiomas operativos:
  1. Cero cifras inventadas: cada magnitud proviene del `StatList` publicado por el proveedor para
     el tablero declarado en `MAPA_LEADERBOARDS`. Si un tablero falla o no existe, la clave se
     OMITE y el hueco se declara en `huecos` (jamás se imputa `0.0` ni un promedio de fantasía).
  2. Unidad declarada, no adivinada: `normalizacion` fija la aritmética permitida por tablero
     (`publicado` = ya es tasa/porcentaje; `entre_pj` = acumulado ÷ partidos jugados del club;
     `acumulado` = se conserva el total; `suma`/`max` = agregado de plantilla declarado).
  3. Guarda de integridad de liga: el `id` solicitado DEBE publicar el nombre esperado
     (`LIGA_NOMBRE_ESPERADO`); de lo contrario el proceso aborta con SALIDA 2 (el `id` 262 publica
     Premier League, no Liga MX: `[LN-QBE-120]` VAR-1).
  4. Identidad canónica: el club se resuelve con `canonicalize_team_name` → `obtener_slug_club`;
     el `TeamId` del proveedor se conserva como llave dura de trazabilidad.
  5. Idempotencia: el cuerpo se ordena (`sort_keys`) y `hash_sha256` se calcula sobre el cuerpo
     canónico auto-excluyente (`generado_at` / `hash_sha256`). Dos corridas sobre la misma evidencia
     producen la misma huella y la segunda no reescribe el archivo (salvo `--forzar`).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import httpx

from src.ingestion.normalizer import canonicalize_team_name
from src.storage.crest_resolver import obtener_slug_club

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("CentinelaMacroEstadisticas")

SONDA_MACRO = "ARCH-1.4.59 · MACRO-STATS-LIGAMX"
ESQUEMA_MACRO = "macro_stats_v1"
CATALOGO_VERSION = "32V-2026"
FUENTE_MACRO = "fotmob.com · leagues(tab=stats) › stats.teams|players[].fetchAllUrl › TopLists[0].StatList"
DEFAULT_FOTMOB_LIGA_MX_ID = 230
LIGA_FOTMOB_ID_DEFAULT = DEFAULT_FOTMOB_LIGA_MX_ID
LIGA_NOMBRE_ESPERADO = "Liga MX"
URL_LIGA = "https://www.fotmob.com/api/data/leagues?id={liga_id}&tab=stats"
NOMBRE_CACHE_MACRO = "cache_macro_stats_liga_mx_2026.json"
RUTA_CACHE_PROPIA = os.path.join(PROJECT_ROOT, "data", NOMBRE_CACHE_MACRO)
# [Migración Fase 4] Puente de lectura/escritura mientras el homologador legado sigue leyendo
# `Q_BE_CD_WEB/data`. El dueño natural es `qbe_ingestion/data`; el fallback legado evita romper
# el consumidor de las 32 variables sin duplicar el artefacto.
RUTA_CACHE_LEGADO = os.path.abspath(
    os.path.join(PROJECT_ROOT, "..", "..", "Q_BE_CD_WEB", "data", NOMBRE_CACHE_MACRO)
)


def _resolver_ruta_cache() -> str:
    """Resuelve el artefacto: variable explícita → copia propia → fallback legado → ruta propia."""
    explicita = os.environ.get("QBE_MACRO_CACHE_PATH")
    if explicita:
        return os.path.abspath(explicita)
    if os.path.exists(RUTA_CACHE_PROPIA):
        return RUTA_CACHE_PROPIA
    if os.path.exists(RUTA_CACHE_LEGADO):
        return RUTA_CACHE_LEGADO
    return RUTA_CACHE_PROPIA


RUTA_CACHE_DEFAULT = _resolver_ruta_cache()
CABECERAS = {
    "User-Agent": "Mozilla/5.0 (compatible; Q-BE-CentinelaMacro/1.0; +https://qbe.local)",
    "Accept": "application/json, text/plain, */*",
}
MAX_REINTENTOS = 3
TIMEOUT_SEGUNDOS = 40.0
ESPERA_DEFAULT = 0.15


# ── [LN-QBE-120] Mapa declarativo leaderboard → clave canónica del catálogo de 32 variables ──────
# `fuente`: "equipo" (`stats.teams`) | "plantilla" (`stats.players`, agregado por `TeamId`).
# `normalizacion`: "publicado" | "entre_pj" | "acumulado" | "suma" | "max".
# La calibración de unidades fue empírica sobre la cartelera real (ver `[ARCH-1.4.59]`): p. ej.
# `expected_goals_team` es acumulado (÷ PJ) mientras `possession_percentage_team` ya es porcentaje.
MAPA_LEADERBOARDS: Tuple[Dict[str, Any], ...] = (
    # 𝒯_Vol — Volumen Territorial y Fricción
    {"variable": "V01", "clave": "possession_pct", "board": "possession_percentage_team",
     "fuente": "equipo", "normalizacion": "publicado", "unidad": "%"},
    {"variable": "V02", "clave": "touches_opp_box_per_match", "board": "touches_in_opp_box_team",
     "fuente": "equipo", "normalizacion": "entre_pj", "unidad": "toques/PJ"},
    {"variable": "V03", "clave": "accurate_passes_per_match", "board": "accurate_pass_team",
     "fuente": "equipo", "normalizacion": "publicado", "unidad": "pases/PJ"},
    {"variable": "V04", "clave": "accurate_long_balls_per_match", "board": "accurate_long_balls_team",
     "fuente": "equipo", "normalizacion": "publicado", "unidad": "pases largos/PJ"},
    {"variable": "V05", "clave": "fouls_per_match", "board": "fk_foul_lost_team",
     "fuente": "equipo", "normalizacion": "publicado", "unidad": "faltas/PJ"},
    # 𝒯_Rem — Calidad de Remate
    {"variable": "V06", "clave": "xg_per_match", "board": "expected_goals_team",
     "fuente": "equipo", "normalizacion": "entre_pj", "unidad": "xG/PJ"},
    {"variable": "V07", "clave": "sot_per_match", "board": "ontarget_scoring_att_team",
     "fuente": "equipo", "normalizacion": "publicado", "unidad": "tiros al arco/PJ"},
    {"variable": "V08", "clave": "big_chances_created_per_match", "board": "big_chance_team",
     "fuente": "equipo", "normalizacion": "entre_pj", "unidad": "big chances/PJ"},
    {"variable": "V09", "clave": "big_chances_missed_per_match", "board": "big_chance_missed_team",
     "fuente": "equipo", "normalizacion": "entre_pj", "unidad": "big chances falladas/PJ"},
    {"variable": "V10", "clave": "xgot_squad", "board": "expected_goalsontarget",
     "fuente": "plantilla", "normalizacion": "suma", "unidad": "xGOT acumulado TOP"},
    {"variable": "V11", "clave": "xa_squad", "board": "expected_assists",
     "fuente": "plantilla", "normalizacion": "suma", "unidad": "xA acumulada TOP"},
    # 𝒯_Def — Resistencia Defensiva
    {"variable": "V12", "clave": "xga_per_match", "board": "expected_goals_conceded_team",
     "fuente": "equipo", "normalizacion": "entre_pj", "unidad": "xGA/PJ"},
    {"variable": "V14", "clave": "tackles_per_match", "board": "total_tackle_team",
     "fuente": "equipo", "normalizacion": "publicado", "unidad": "entradas/PJ"},
    {"variable": "V14", "clave": "clearances_per_match", "board": "effective_clearance_team",
     "fuente": "equipo", "normalizacion": "publicado", "unidad": "despejes/PJ"},
    {"variable": "V15", "clave": "interceptions_per_match", "board": "interception_team",
     "fuente": "equipo", "normalizacion": "publicado", "unidad": "intercepciones/PJ"},
    # 𝒯_Por — Rendimiento de Portería
    {"variable": "V17", "clave": "goals_prevented_squad", "board": "_goals_prevented",
     "fuente": "plantilla", "normalizacion": "suma", "unidad": "goles evitados acumulados TOP"},
    {"variable": "V18", "clave": "save_percentage", "board": "_save_percentage",
     "fuente": "plantilla", "normalizacion": "max", "unidad": "%"},
    {"variable": "V19", "clave": "sweeper_actions", "board": "total_keeper_sweeper",
     "fuente": "plantilla", "normalizacion": "max", "unidad": "salidas/90'"},
    {"variable": "V20", "clave": "clean_sheets", "board": "clean_sheet_team",
     "fuente": "equipo", "normalizacion": "acumulado", "unidad": "porterías a cero (total)"},
    {"variable": "V20", "clave": "saves_per_match", "board": "saves_team",
     "fuente": "equipo", "normalizacion": "publicado", "unidad": "atajadas/PJ"},
    # 𝒯_Spc — Balón Parado y Disciplina
    {"variable": "V21", "clave": "set_piece_goals_per_match", "board": "_set_piece_goals_team",
     "fuente": "equipo", "normalizacion": "entre_pj", "unidad": "goles ABP/PJ"},
    {"variable": "V22", "clave": "set_piece_goals_conceded_per_match",
     "board": "_set_piece_goals_conceded_team", "fuente": "equipo", "normalizacion": "entre_pj",
     "unidad": "goles ABP recibidos/PJ"},
    {"variable": "V23", "clave": "corners_per_match", "board": "corner_taken_team",
     "fuente": "equipo", "normalizacion": "entre_pj", "unidad": "córners/PJ"},
    {"variable": "V24", "clave": "penalties_won_total", "board": "penalty_won_team",
     "fuente": "equipo", "normalizacion": "acumulado", "unidad": "penales a favor (total)"},
    {"variable": "V24", "clave": "penalties_conceded_total", "board": "penalty_conceded_team",
     "fuente": "equipo", "normalizacion": "acumulado", "unidad": "penales en contra (total)"},
    {"variable": "V25", "clave": "yellow_cards_per_match", "board": "total_yel_card_team",
     "fuente": "equipo", "normalizacion": "entre_pj", "unidad": "amarillas/PJ"},
    {"variable": "V25", "clave": "red_cards_per_match", "board": "total_red_card_team",
     "fuente": "equipo", "normalizacion": "entre_pj", "unidad": "rojas/PJ"},
    # Contexto factual complementario (identidad de conjunto, no señal directora del catálogo)
    {"variable": "-", "clave": "goals_per_match", "board": "goals_team_match",
     "fuente": "equipo", "normalizacion": "publicado", "unidad": "goles/PJ"},
    {"variable": "-", "clave": "goals_conceded_per_match", "board": "goals_conceded_team_match",
     "fuente": "equipo", "normalizacion": "publicado", "unidad": "goles recibidos/PJ"},
)

# ── Derivaciones declaradas (identidades aritméticas de magnitudes YA publicadas) ────────────────
# Prohibido inferir: sólo se suman tasas publicadas por el proveedor y se documenta la fórmula.
DERIVACIONES: Tuple[Dict[str, Any], ...] = (
    {"variable": "V13", "clave": "sota_per_match",
     "suma": ("saves_per_match", "goals_conceded_per_match"),
     "unidad": "tiros al arco recibidos/PJ",
     "nota": "Identidad de conjunto: SoTA ≈ atajadas + goles recibidos por partido (sin bloqueos ni palos)."},
    {"variable": "V14", "clave": "defensive_actions_per_match",
     "suma": ("tackles_per_match", "clearances_per_match", "interceptions_per_match"),
     "unidad": "acciones defensivas/PJ",
     "nota": "Agregado declarado de tres leaderboards de equipo ya normalizados por partido."},
)

# ── Cobertura de la fuente: variables del catálogo que FotMob NO publica en `tab=stats` ─────────
COBERTURA_FUERA_DE_FUENTE: Dict[str, str] = {
    "V16": "No existe leaderboard de equipo 'big chances concedidas' en `stats.teams` (28 tableros).",
    "V26": "H2H: se resuelve con el corpus propio de fixtures, no con leaderboards torneales.",
    "V27": "H2H: se resuelve con el corpus propio de fixtures, no con leaderboards torneales.",
    "V28": "Récord del visitante en sede: corpus propio de fixtures.",
    "V29": "Altitud: catálogo de sedes (`FIXTURE`), no leaderboard del proveedor.",
    "V30": "Δ descanso: calendario propio (`FIXTURE`), no leaderboard del proveedor.",
    "V31": "Forma 5P: derivada del historial propio de resultados (`Q-BE`).",
    "V32": "Varianza ΔxPTS: derivada del historial propio de resultados (`Q-BE`).",
}


# ── Cliente HTTP y utilidades de lectura (sin estado global, sin caché de proceso) ───────────────
def _cliente() -> httpx.Client:
    """Cliente HTTP con reintentos declarados (`MAX_REINTENTOS`) y timeout explícito."""
    return httpx.Client(
        headers=CABECERAS,
        timeout=TIMEOUT_SEGUNDOS,
        follow_redirects=True,
        transport=httpx.HTTPTransport(retries=MAX_REINTENTOS),
    )


def _leer_json(cliente: httpx.Client, url: str) -> Dict[str, Any]:
    """Descarga y decodifica un JSON de objeto; falla en voz alta tras agotar reintentos."""
    ultimo: Optional[Exception] = None
    for intento in range(1, MAX_REINTENTOS + 1):
        try:
            respuesta = cliente.get(url)
            respuesta.raise_for_status()
            cuerpo = respuesta.json()
            if not isinstance(cuerpo, dict):
                raise RuntimeError("la respuesta no es un objeto JSON")
            return cuerpo
        except (httpx.HTTPError, ValueError, RuntimeError) as error:
            ultimo = error
            logger.warning("⚠️ intento %d/%d fallido en %s: %s", intento, MAX_REINTENTOS, url, error)
            if intento < MAX_REINTENTOS:
                time.sleep(ESPERA_DEFAULT * intento * 4)
    raise RuntimeError(f"descarga irrecuperable: {url} ({ultimo})")


def _indice_boards(bloques: Any) -> Dict[str, str]:
    """Mapa `nombre_del_tablero → fetchAllUrl` publicado por `stats.teams` / `stats.players`."""
    indice: Dict[str, str] = {}
    for bloque in bloques or []:
        if not isinstance(bloque, dict):
            continue
        nombre = bloque.get("name")
        url = bloque.get("fetchAllUrl")
        if isinstance(nombre, str) and isinstance(url, str) and url.startswith("http"):
            indice[nombre] = url
    return indice


def _statlist(cliente: httpx.Client, url: str) -> List[Dict[str, Any]]:
    """`TopLists[0].StatList` del tablero: la lista completa rankeada (no sólo el podio)."""
    cuerpo = _leer_json(cliente, url)
    listas = cuerpo.get("TopLists")
    if not isinstance(listas, list) or not listas:
        return []
    filas = listas[0].get("StatList")
    if not isinstance(filas, list):
        return []
    return [fila for fila in filas if isinstance(fila, dict)]


def _temporada(fetch_url: str) -> Tuple[Optional[str], Optional[str]]:
    """(id de temporada, torneo) leídos del propio `fetchAllUrl`; `(None, None)` si no son legibles."""
    partes = [parte for parte in str(fetch_url or "").split("/") if parte]
    # https: / data.fotmob.com / stats / <liga> / season / <temporada> / <torneo> / <tablero>.json
    try:
        posicion = partes.index("season")
    except ValueError:
        return None, None
    temporada = partes[posicion + 1] if len(partes) > posicion + 1 else None
    torneo = partes[posicion + 2] if len(partes) > posicion + 2 else None
    return temporada, torneo


def _num(valor: Any) -> Optional[float]:
    """Número legible o `None` (jamás `0.0` por defecto)."""
    if isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    if isinstance(valor, str):
        limpio = valor.replace(",", "").replace("%", "").strip()
        try:
            return float(limpio)
        except ValueError:
            return None
    return None


def _normalizar(valor: Any, partidos_jugados: Any, modo: str) -> Optional[float]:
    """Aplica la aritmética declarada por el mapa (`entre_pj` ÷ PJ; el resto se conserva)."""
    numero = _num(valor)
    if numero is None:
        return None
    if modo == "entre_pj":
        pj = _num(partidos_jugados)
        if pj is None or pj <= 0.0:
            return None
        return round(numero / pj, 4)
    return round(numero, 4)


def _por_equipo(filas: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    """`TeamId → fila` (tableros de equipo: una fila por club)."""
    indice: Dict[int, Dict[str, Any]] = {}
    for fila in filas:
        team_id = fila.get("TeamId")
        if isinstance(team_id, int):
            indice[team_id] = fila
    return indice


def _por_equipo_lista(filas: List[Dict[str, Any]]) -> Dict[int, List[Dict[str, Any]]]:
    """`TeamId → [filas]` (tableros de plantilla: varias filas por club)."""
    agrupado: Dict[int, List[Dict[str, Any]]] = {}
    for fila in filas:
        team_id = fila.get("TeamId")
        if isinstance(team_id, int):
            agrupado.setdefault(team_id, []).append(fila)
    return agrupado


def _agregar_plantilla(filas: List[Dict[str, Any]], modo: str) -> Tuple[Optional[float], int]:
    """(valor agregado, n_jugadores) de las filas publicadas del club; `max` o `suma` declarados."""
    valores = [numero for numero in (_num(fila.get("StatValue")) for fila in filas) if numero is not None]
    if not valores:
        return None, 0
    if modo == "max":
        return round(max(valores), 4), len(valores)
    return round(sum(valores), 4), len(valores)


def _huella(cuerpo: Dict[str, Any]) -> str:
    """SHA-256 del cuerpo canónico auto-excluyente (`generado_at` / `hash_sha256`)."""
    limpio = {clave: valor for clave, valor in cuerpo.items() if clave not in ("generado_at", "hash_sha256")}
    serializado = json.dumps(limpio, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serializado.encode("utf-8")).hexdigest()


def _huella_previa(ruta: str) -> Optional[str]:
    """Huella del artefacto preexistente (`None` si no existe o no es legible)."""
    try:
        with open(ruta, "r", encoding="utf-8") as manejador:
            previo = json.load(manejador)
    except (OSError, ValueError):
        return None
    if not isinstance(previo, dict):
        return None
    huella = previo.get("hash_sha256")
    return huella if isinstance(huella, str) else None


def construir_artefacto(
    liga_id: int,
    espera: float = ESPERA_DEFAULT,
    limite: int = 0,
    cliente: Optional[httpx.Client] = None,
    verbose: bool = False,
) -> Dict[str, Any]:
    """Congela los leaderboards declarados; devuelve el cuerpo canónico (sin `generado_at`/huella)."""
    propio = cliente is None
    sesion = cliente if cliente is not None else _cliente()
    try:
        payload = _leer_json(sesion, URL_LIGA.format(liga_id=int(liga_id)))
        detalles = payload.get("details") if isinstance(payload.get("details"), dict) else {}
        nombre_liga = str(detalles.get("name") or "").strip()
        if LIGA_NOMBRE_ESPERADO.lower() not in nombre_liga.lower():
            raise RuntimeError(
                f"guarda de integridad de liga: id={int(liga_id)} publica "
                f"'{nombre_liga or 'sin nombre'}'; se exige '{LIGA_NOMBRE_ESPERADO}' (VAR-1 [LN-QBE-120])"
            )
        stats = payload.get("stats") if isinstance(payload.get("stats"), dict) else {}
        boards_equipo = _indice_boards(stats.get("teams"))
        boards_plantilla = _indice_boards(stats.get("players"))
        if not boards_equipo:
            raise RuntimeError("el payload no publica `stats.teams`: cero leaderboards de equipo")

        entradas = list(MAPA_LEADERBOARDS)
        if limite and limite > 0:
            entradas = entradas[:limite]

        fase: Dict[str, Dict[Any, Any]] = {}
        errores: List[str] = []
        temporada_id: Optional[str] = None
        torneo: Optional[str] = None
        for posicion, entrada in enumerate(entradas):
            board = str(entrada["board"])
            origen = boards_equipo if entrada["fuente"] == "equipo" else boards_plantilla
            url = origen.get(board)
            if url is None:
                errores.append(f"{board}: tablero ausente en la fuente ({entrada['fuente']})")
                continue
            if temporada_id is None:
                temporada_id, torneo = _temporada(url)
            try:
                filas = _statlist(sesion, url)
            except RuntimeError as error:
                errores.append(f"{board}: {error}")
                continue
            if not filas:
                errores.append(f"{board}: StatList vacío")
                continue
            fase[board] = _por_equipo(filas) if entrada["fuente"] == "equipo" else _por_equipo_lista(filas)
            if verbose:
                logger.debug("📊 %-34s %4d fila(s) · %s", board, len(filas), entrada["normalizacion"])
            if espera and espera > 0 and posicion + 1 < len(entradas):
                time.sleep(espera)

        nombres: Dict[int, str] = {}
        for tablero in fase.values():
            for team_id, contenido in tablero.items():
                if isinstance(contenido, dict):
                    nombre = contenido.get("ParticipantName")
                else:
                    nombre = contenido[0].get("ParticipantName") if contenido else None
                if isinstance(nombre, str) and nombre.strip():
                    nombres.setdefault(int(team_id), nombre.strip())
        if not nombres:
            raise RuntimeError("no se recuperó ningún club de los leaderboards: artefacto imposible")

        equipos: Dict[str, Dict[str, Any]] = {}
        huecos: List[str] = []
        cobertura: Dict[str, Dict[str, Any]] = {
            str(entrada["clave"]): {
                "variable": entrada["variable"],
                "tablero": entrada["board"],
                "normalizacion": entrada["normalizacion"],
                "unidad": entrada["unidad"],
                "equipos_con_dato": 0,
            }
            for entrada in entradas
        }
        for team_id in sorted(nombres):
            nombre_fuente = nombres[team_id]
            fila_equipo: Dict[str, Any] = {
                "team_id": int(team_id),
                "nombre_fuente": nombre_fuente,
                "slug": obtener_slug_club(canonicalize_team_name(nombre_fuente)),
                "partidos_jugados": None,
            }
            partidos: List[float] = []
            agregados: Dict[str, Dict[str, Any]] = {}
            for entrada in entradas:
                tablero = fase.get(str(entrada["board"]))
                if not tablero:
                    continue
                clave = str(entrada["clave"])
                modo = str(entrada["normalizacion"])
                if entrada["fuente"] == "equipo":
                    fila = tablero.get(team_id)
                    if not isinstance(fila, dict):
                        continue
                    pj = _num(fila.get("MatchesPlayed"))
                    if pj is not None:
                        partidos.append(pj)
                    valor = _normalizar(fila.get("StatValue"), pj, modo)
                    if valor is None:
                        continue
                    fila_equipo[clave] = valor
                else:
                    valor, n_jugadores = _agregar_plantilla(tablero.get(team_id) or [], modo)
                    if valor is None:
                        continue
                    fila_equipo[clave] = valor
                    agregados[clave] = {
                        "n_jugadores": n_jugadores,
                        "modo": modo,
                        "alcance": "top publicado por el proveedor",
                    }
                cobertura[clave]["equipos_con_dato"] += 1
            if partidos:
                fila_equipo["partidos_jugados"] = int(max(partidos))
            if agregados:
                fila_equipo["agregados_plantilla"] = agregados
            for derivacion in DERIVACIONES:
                componentes = [fila_equipo.get(str(clave)) for clave in derivacion["suma"]]
                if all(isinstance(componente, (int, float)) for componente in componentes):
                    fila_equipo[str(derivacion["clave"])] = round(
                        sum(float(componente) for componente in componentes), 4
                    )
            equipos[str(fila_equipo["slug"])] = fila_equipo

        for derivacion in DERIVACIONES:
            clave = str(derivacion["clave"])
            cobertura[clave] = {
                "variable": derivacion["variable"],
                "tablero": "+".join(str(componente) for componente in derivacion["suma"]),
                "normalizacion": "derivada",
                "unidad": derivacion["unidad"],
                "equipos_con_dato": sum(1 for fila in equipos.values() if clave in fila),
            }
        for clave, motivo in COBERTURA_FUERA_DE_FUENTE.items():
            cobertura.setdefault(
                clave,
                {
                    "variable": clave,
                    "tablero": None,
                    "normalizacion": "fuera_de_fuente",
                    "unidad": None,
                    "equipos_con_dato": 0,
                    "motivo": motivo,
                },
            )
        claves_esperadas = [str(entrada["clave"]) for entrada in entradas] + [
            str(derivacion["clave"]) for derivacion in DERIVACIONES
        ]
        for slug, fila_equipo in equipos.items():
            for clave in claves_esperadas:
                if clave not in fila_equipo:
                    huecos.append(f"{slug}:{clave}")

        return {
            "sonda": SONDA_MACRO,
            "esquema": ESQUEMA_MACRO,
            "catalogo_version": CATALOGO_VERSION,
            "legislacion": ["LN-QBE-120", "ARCH-1.4.59"],
            "fuente": FUENTE_MACRO,
            "endpoint": URL_LIGA.format(liga_id=int(liga_id)),
            "liga": {
                "fotmob_id": int(liga_id),
                "nombre": nombre_liga,
                "data_provider": detalles.get("dataProvider"),
                "temporada_seleccionada": detalles.get("selectedSeason"),
                "temporada_id": temporada_id,
                "torneo": torneo,
            },
            "mapa_leaderboards": [dict(entrada) for entrada in entradas],
            "derivaciones": [
                {
                    "variable": derivacion["variable"],
                    "clave": derivacion["clave"],
                    "suma": list(derivacion["suma"]),
                    "unidad": derivacion["unidad"],
                    "nota": derivacion["nota"],
                }
                for derivacion in DERIVACIONES
            ],
            "cobertura": cobertura,
            "fuera_de_fuente": COBERTURA_FUERA_DE_FUENTE,
            "totales": {
                "equipos": len(equipos),
                "tableros_leidos": len(fase),
                "tableros_solicitados": len(entradas),
                "claves_con_dato": sum(1 for fila in cobertura.values() if fila.get("equipos_con_dato")),
                "huecos": len(huecos),
                "errores": len(errores),
            },
            "equipos": equipos,
            "huecos": huecos,
            "errores": errores,
        }
    finally:
        if propio:
            sesion.close()


def _imprimir_resumen(artefacto: Dict[str, Any], ruta: str, idempotente: bool) -> None:
    """Resumen fiduciario en consola (una línea por hecho verificable)."""
    totales = artefacto.get("totales") or {}
    liga = artefacto.get("liga") or {}
    logger.info(
        "🏟️  %s · id=%s · proveedor=%s · %s",
        liga.get("nombre"), liga.get("fotmob_id"), liga.get("data_provider"),
        liga.get("temporada_seleccionada"),
    )
    logger.info(
        "📦 %s equipo(s) · %s/%s tablero(s) leído(s) · %s clave(s) con dato",
        totales.get("equipos"), totales.get("tableros_leidos"),
        totales.get("tableros_solicitados"), totales.get("claves_con_dato"),
    )
    logger.info(
        "🕳️  %s hueco(s) declarado(s) · %s error(es) · catálogo %s",
        totales.get("huecos"), totales.get("errores"), artefacto.get("catalogo_version"),
    )
    logger.info(
        "🧾 huella %s · %s · %s",
        str(artefacto.get("hash_sha256"))[:16],
        "IDEMPOTENTE" if idempotente else "NUEVA",
        ruta,
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Congela los leaderboards torneales de FotMob (equipo y plantilla) en un artefacto "
            "idempotente alineado al catálogo de 32 variables ([LN-QBE-120] / [ARCH-1.4.59])."
        )
    )
    parser.add_argument(
        "--liga-id", type=int, default=LIGA_FOTMOB_ID_DEFAULT,
        help=(
            "ID FotMob de la liga. DEFAULT_FOTMOB_LIGA_MX_ID = 230; el 262 publica "
            "Premier League y la guarda de nombre lo rechaza con SALIDA 2."
        ),
    )
    parser.add_argument(
        "--cache", default=RUTA_CACHE_DEFAULT,
        help=(
            "Ruta del artefacto JSON. Precedencia: --cache → QBE_MACRO_CACHE_PATH → "
            "qbe_ingestion/data → fallback Q_BE_CD_WEB/data."
        ),
    )
    parser.add_argument("--espera", type=float, default=ESPERA_DEFAULT, help="Pausa entre peticiones (segundos).")
    parser.add_argument("--limite", type=int, default=0, help="Procesa sólo los primeros N tableros (diagnóstico).")
    parser.add_argument("--dry-run", action="store_true", help="No escribe el artefacto.")
    parser.add_argument("--forzar", action="store_true", help="Reescribe aunque la huella sea idéntica.")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    ruta = str(args.cache)
    try:
        artefacto = construir_artefacto(
            liga_id=int(args.liga_id),
            espera=float(args.espera),
            limite=int(args.limite),
            verbose=bool(args.verbose),
        )
        huella = _huella(artefacto)
        artefacto["generado_at"] = (
            datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        )
        artefacto["hash_sha256"] = huella
        idempotente = (not args.forzar) and _huella_previa(ruta) == huella
        if idempotente:
            logger.info("✅ Artefacto bit-idéntico (huella %s): no se reescribe [idempotencia]", huella[:16])
        elif args.dry_run:
            logger.info("🔎 dry-run: artefacto NO escrito")
        else:
            os.makedirs(os.path.dirname(os.path.abspath(ruta)) or ".", exist_ok=True)
            temporal = f"{ruta}.tmp"
            with open(temporal, "w", encoding="utf-8") as manejador:
                json.dump(artefacto, manejador, ensure_ascii=False, indent=2, sort_keys=True)
                manejador.write("\n")
            os.replace(temporal, ruta)
            logger.info("💾 Artefacto materializado: %s", ruta)
    except RuntimeError as error:
        logger.error("❌ %s", error)
        return 2

    _imprimir_resumen(artefacto, ruta, idempotente)
    if artefacto.get("errores"):
        logger.error(
            "🔴 %d tablero(s) con error: SALIDA 1 (fail-loud, cero imputación)",
            len(artefacto.get("errores") or []),
        )
        return 1
    logger.info("✅ Macro-estadísticas congeladas · EXIT CODE 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


