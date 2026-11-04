# -*- coding: utf-8 -*-
"""`[LN-QBE-146]` / `[LN-QBE-150]` Extractor Histórico Masivo FotMob → Bóveda OLAP.

Régimen ``[DIRGEN-STRICT]``.

Base arquitectónica (legacy aprobado por la Dirección)::

    Q_BE_CD_WEB/scripts/ingesta/ingestar_historico_fotmob.py   (transporte + parser )
    Q_BE_CD_WEB/scripts/ingesta/congelar_telemetria_fotmob.py  (matchDetails + 3NF)
    Q_BE_CD_WEB/src/ingestion/providers/fotmob_provider.py     (proveedor)

Axiomas operativos
------------------
1. **Cero datos inventados.** Una métrica que FotMob no publica se escribe ``NULL``; jamás
   ``0.0``. La fila declara su ``sin_evidencia`` completa.
2. **Cero fuga temporal.** El vector de contexto (``V26``–``V32``) se calcula EXCLUSIVAMENTE con
   partidos ANTERIORES al kickoff; el propio partido nunca entra en su contexto.
3. **Join determinista.** El emparejamiento bóveda ↔ FotMob se resuelve por sello temporal
   único y, para los empates, por el mapa ``team_id`` aprendido de los emparejamientos
   inequívocos. Un partido sin destino se declara ``UNMATCHED``; no se adivina.
4. **Una transacción por temporada** (``BEGIN IMMEDIATE``) + respaldo WORM previo +
   ``PRAGMA quick_check`` al cierre (excepción CQRS de ``[ARCH-1.5.1]`` §CQRS).
5. **WAF.** ``time.sleep(1.0)`` entre peticiones (constante ``PAUSA_ENTRE_PETICIONES``).

Uso::

    python scripts/auditoria/extraer_historico_fotmob.py --temporada 2018_2019 --piloto 5
    python scripts/auditoria/extraer_historico_fotmob.py --temporada 2018_2019
    python scripts/auditoria/extraer_historico_fotmob.py --temporada 2018_2019 --solo-reporte
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sqlite3
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

RAIZ_PROYECTO = Path(__file__).resolve().parents[2]
for _ruta in (RAIZ_PROYECTO, RAIZ_PROYECTO / "qbe_core"):
    if str(_ruta) not in sys.path:
        sys.path.insert(0, str(_ruta))

if hasattr(sys.stdout, "reconfigure"):
    try:  # consola Windows cp1252: el reporte es UTF-8
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, OSError, ValueError):  # pragma: no cover
        pass

from src.core.catalog import altitud_estadio  # noqa: E402

DB_DEFECTO = RAIZ_PROYECTO / "qbe_observatory" / "data" / "qbe_historico.db"
RUTA_REPORTES = RAIZ_PROYECTO / "data" / "reportes"
TABLA = "historical_match_causal_vars"
TABLA_BOVEDA = "historical_matches"
FUENTE_DATOS = "FOTMOB_MATCHDETAILS"

LIGA_FOTMOB_ID = 230
URL_OVERVIEW = "https://www.fotmob.com/leagues/230/overview/liga-mx?season={temporada}"
URL_TEMPORADA_API = "https://www.fotmob.com/api/data/leagues?id=230&ccode3=MEX"
URL_PARTIDO = "https://www.fotmob.com/api/data/matchDetails?matchId={match_id}"

CABECERAS_HTTP = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
    "Referer": "https://www.fotmob.com/",
}

#: [ARCH-1.5.1] §CQRS — cadencia obligatoria anti-WAF entre peticiones al proveedor.
PAUSA_ENTRE_PETICIONES: float = 1.0
TIMEOUT_SEGUNDOS: float = 30.0
REINTENTOS: int = 3

VARIABLES: Tuple[str, ...] = tuple(f"V{indice:02d}" for indice in range(1, 33))
LADOS: Tuple[str, str] = ("local", "visita")

#: `[LN-QBE-146]` §2.2 — variables sin fuente en `matchDetails` (se declaran, no se imputan).
V16_FUERA_DE_FUENTE = "V16"

#: Mapa `V##` → claves candidatas del bloque `content.stats.Periods.All.stats`.
CLAVES_DIRECTAS: Dict[str, Tuple[str, ...]] = {
    "V01": ("BallPossesion", "BallPossession", "ball_possession"),
    "V02": ("touches_in_opp_box", "touches_opp_box", "touches_in_box"),
    "V03": ("accurate_passes", "accurate_pass", "accurate_passes_team"),
    "V04": ("long_balls_accurate", "accurate_long_balls"),
    "V05": ("fouls", "fk_foul_lost", "fouls_committed"),
    "V06": ("expected_goals", "Expected goals (xG)", "xg", "xG"),
    "V07": ("ShotsOnTarget", "shots_on_target", "ontarget_scoring_att"),
    "V08": ("big_chance", "big_chances", "big_chance_created"),
    "V09": ("big_chance_missed_title", "big_chance_missed", "big_chances_missed"),
    "V10": ("expected_goals_on_target", "expected_goalsontarget", "xgot"),
    "V11": ("expected_assists", "xa"),
    "V12": ("expected_goals_conceded", "expected_goals_conceded_team", "xga"),
    "V13": ("__dual_sot",),  # identidad: SoTA_local ≡ SoT_visita
    "V14": ("__acciones_defensivas",),  # identidad: tackles + despejes + intercepciones
    "V15": ("interceptions", "interception"),
    "V16": (),  # FUERA DE FUENTE
    "V17": ("goals_prevented", "_goals_prevented", "goals_prevented_team"),
    "V18": ("__save_pct",),  # identidad: atajadas / SoT recibidos
    "V19": ("total_keeper_sweeper", "sweeper_actions", "keeper_sweeper"),
    "V20": ("__clean_sheet",),  # identidad: goles recibidos == 0
    "V21": ("_set_piece_goals_team", "set_piece_goals"),
    "V22": ("_set_piece_goals_conceded_team", "set_piece_goals_conceded"),
    "V23": ("corners", "corner_taken", "corners_team"),
    "V24": ("penalty_won", "penalties_won", "penalty_conceded"),
    "V25": ("__tarjetas",),  # identidad: amarillas + rojas
}

#: `[LN-QBE-146]` §2.2 — variables de contexto (`Q-BE`) y de calendario (`FIXTURE`).
CLAVES_CONTEXTO: Tuple[str, ...] = ("V26", "V27", "V28", "V31")
CLAVES_FIXTURE: Tuple[str, ...] = ("V29", "V30")
CLAVES_DERIVADAS: Tuple[str, ...] = ("V32",)

_TORNEO_POR_TEMPORADA: Dict[str, Tuple[str, str]] = {
    "2010_2011": ("2010/2011 - Apertura", "2010/2011 - Clausura"),
    "2011_2012": ("2011/2012 - Apertura", "2011/2012 - Clausura"),
    "2012_2013": ("2012/2013 - Apertura", "2012/2013 - Clausura"),
    "2013_2014": ("2013/2014 - Apertura", "2013/2014 - Clausura"),
    "2014_2015": ("2014/2015 - Apertura", "2014/2015 - Clausura"),
    "2015_2016": ("2015/2016 - Apertura", "2015/2016 - Clausura"),
    "2016_2017": ("2016/2017 - Apertura", "2016/2017 - Clausura"),
    "2017_2018": ("2017/2018 - Apertura", "2017/2018 - Clausura"),
    "2018_2019": ("2018/2019 - Apertura", "2018/2019 - Clausura"),
    "2019_2020": ("2019/2020 - Apertura", "2019/2020 - Clausura"),
    "2020_2021": ("2020/2021 - Apertura", "2020/2021 - Clausura"),
    "2021_2022": ("2021/2022 - Apertura", "2021/2022 - Clausura"),
    "2022_2023": ("2022/2023 - Apertura", "2022/2023 - Clausura"),
    "2023_2024": ("2023/2024 - Apertura", "2023/2024 - Clausura"),
    "2024_2025": ("2024/2025 - Apertura", "2024/2025 - Clausura"),
    "2025_2026": ("2025/2026 - Apertura", "2025/2026 - Clausura"),
    # 2026/2027: el Clausura 2027 aún no se publica; FotMob devuelve el Apertura por
    # fallback, por lo que se declara sólo el torneo existente (cero fixtures duplicados).
    "2026_2027": ("2026/2027 - Apertura",),
}

_RE_NUMERO_INICIAL = re.compile(r"^\s*(-?\d+(?:[.,]\d+)?)")
_RE_NEXT_DATA = re.compile(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.DOTALL)


class ExtraccionError(RuntimeError):
    """`[LN-QBE-146]` Fallo de dominio del extractor histórico."""


# ═════════════════════════════════════════════════════════════════════════════════════════════
# TRANSPORTE (WAF: una pausa por petición)
# ═════════════════════════════════════════════════════════════════════════════════════════════
def _descargar(url: str) -> str:
    """GET de texto con reintentos acotados y cadencia anti-WAF."""
    ultimo: Optional[Exception] = None
    for intento in range(1, REINTENTOS + 1):
        try:
            peticion = urllib.request.Request(url, headers=CABECERAS_HTTP)
            with urllib.request.urlopen(peticion, timeout=TIMEOUT_SEGUNDOS) as respuesta:
                return respuesta.read().decode("utf-8", "replace")
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as error:
            ultimo = error
            if intento < REINTENTOS:
                time.sleep(PAUSA_ENTRE_PETICIONES * 2 * intento)
        finally:
            # Bedrock anti-WAF: la cadencia se respeta incluso cuando el intento falla.
            time.sleep(PAUSA_ENTRE_PETICIONES)
    raise ExtraccionError(f"No se pudo descargar {url}: {ultimo}") from ultimo


def _descargar_json(url: str) -> Dict[str, Any]:
    texto = _descargar(url)
    try:
        return json.loads(texto)
    except ValueError as error:
        raise ExtraccionError(f"JSON inválido de {url}: {error}") from error


# ═════════════════════════════════════════════════════════════════════════════════════════════
# DESCUBRIMIENTO DE FIXTURES
# ═════════════════════════════════════════════════════════════════════════════════════════════
def _fixtures_de_torneo(torneo: str) -> List[Dict[str, Any]]:
    """Lee `props.pageProps.fixtures.allMatches` de la vista de liga del torneo."""
    url = URL_OVERVIEW.format(temporada=urllib.parse.quote(torneo))
    html = _descargar(url)
    coincidencia = _RE_NEXT_DATA.search(html)
    if not coincidencia:
        raise ExtraccionError(
            f"La página de {torneo} no publica `__NEXT_DATA__`; Alto al Fuego estructural."
        )
    datos = json.loads(coincidencia.group(1))
    page_props = ((datos.get("props") or {}).get("pageProps")) or {}
    fixtures = page_props.get("fixtures") or {}
    partidos = fixtures.get("allMatches")
    if not isinstance(partidos, list):
        raise ExtraccionError(f"`fixtures.allMatches` ausente en {torneo}; Alto al Fuego.")
    return [entrada for entrada in partidos if isinstance(entrada, dict)]


def _sellos_de_temporada(temporada: str) -> List[Dict[str, Any]]:
    torneos = _TORNEO_POR_TEMPORADA.get(temporada)
    if torneos is None:
        raise ExtraccionError(
            f"Temporada '{temporada}' sin mapa de torneos declarado en {__name__}."
        )
    fixtures: List[Dict[str, Any]] = []
    for torneo in torneos:
        fixtures.extend(_fixtures_de_torneo(torneo))
    return fixtures


# ═════════════════════════════════════════════════════════════════════════════════════════════
# JOIN DETERMINISTA BÓVEDA ↔ FOTMOB
# ═════════════════════════════════════════════════════════════════════════════════════════════
def _instante(texto: Any) -> Optional[datetime]:
    """Normaliza un sello ISO-8601 a `datetime` UTC (segundos)."""
    if not texto:
        return None
    crudo = str(texto).strip().replace("Z", "+00:00")
    try:
        instante = datetime.fromisoformat(crudo)
    except ValueError:
        return None
    if instante.tzinfo is None:
        instante = instante.replace(tzinfo=timezone.utc)
    return instante.astimezone(timezone.utc)


def _fecha_boveda(fila: Dict[str, Any]) -> Optional[datetime]:
    instante = _instante(fila.get("fecha_utc"))
    if instante is not None:
        return instante
    epoch = fila.get("fecha_epoch")
    if epoch:
        return datetime.fromtimestamp(int(epoch), tz=timezone.utc)
    return None


def _buckets(filas: Sequence[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Indexa la bóveda por sello UTC exacto."""
    indice: Dict[str, List[Dict[str, Any]]] = {}
    for fila in filas:
        instante = _fecha_boveda(fila)
        if instante is None:
            continue
        indice.setdefault(instante.isoformat(), []).append(fila)
    return indice


def _emparejar(
    fixtures: Sequence[Dict[str, Any]], filas: Sequence[Dict[str, Any]]
) -> Tuple[List[Tuple[Dict[str, Any], Dict[str, Any]]], List[Dict[str, Any]]]:
    """Resuelve el join por sello único y completa con el mapa `team_id` aprendido."""
    import collections

    indice = _buckets(filas)
    pendientes: List[Dict[str, Any]] = []
    parejas: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
    usados: set = set()

    for fixture in fixtures:
        sello = _instante(((fixture.get("status") or {}).get("utcTime")))
        candidatos = indice.get(sello.isoformat(), []) if sello else []
        libres = [fila for fila in candidatos if fila["match_id"] not in usados]
        if len(libres) == 1:
            parejas.append((fixture, libres[0]))
            usados.add(libres[0]["match_id"])
        else:
            pendientes.append(fixture)

    # Mapa `team_id` → slug aprendido de los emparejamientos inequívocos.
    votos: Dict[str, "collections.Counter[str]"] = {}

    def _votar(team_id: Any, slug: Any) -> None:
        if team_id and slug:
            votos.setdefault(str(team_id), collections.Counter())[str(slug)] += 1

    for fixture, fila in parejas:
        _votar((fixture.get("home") or {}).get("id"), fila.get("home_team_slug"))
        _votar((fixture.get("away") or {}).get("id"), fila.get("away_team_slug"))

    mapa: Dict[str, str] = {
        team_id: contador.most_common(1)[0][0] for team_id, contador in votos.items()
    }

    restantes: List[Dict[str, Any]] = []
    for fixture in pendientes:
        home_id = str((fixture.get("home") or {}).get("id") or "")
        away_id = str((fixture.get("away") or {}).get("id") or "")
        home_slug = mapa.get(home_id)
        away_slug = mapa.get(away_id)
        sello = _instante(((fixture.get("status") or {}).get("utcTime")))
        destino = None
        if home_slug and away_slug and sello is not None:
            for fila in filas:
                if fila["match_id"] in usados:
                    continue
                if fila.get("home_team_slug") != home_slug:
                    continue
                if fila.get("away_team_slug") != away_slug:
                    continue
                instante = _fecha_boveda(fila)
                if instante is None or abs((instante - sello).total_seconds()) > 36 * 3600:
                    continue
                if destino is not None:
                    destino = None
                    break
                destino = fila
        if destino is None:
            restantes.append(
                {
                    "fotmob_id": str(fixture.get("id") or ""),
                    "local": (fixture.get("home") or {}).get("name"),
                    "visita": (fixture.get("away") or {}).get("name"),
                    "utc": (fixture.get("status") or {}).get("utcTime"),
                    "motivo": "sin candidato único en la bóveda",
                }
            )
            continue
        parejas.append((fixture, destino))
        usados.add(destino["match_id"])

    return parejas, restantes


# ═════════════════════════════════════════════════════════════════════════════════════════════
# PARSER PURO DE `matchDetails`
# ═════════════════════════════════════════════════════════════════════════════════════════════
def _a_numero(valor: Any) -> Optional[float]:
    """Convierte `8`, `"8"`, `"282 (77%)"` o `"44%"` en número; `None` si no es numérico."""
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)):
        return None if math.isnan(float(valor)) else float(valor)
    coincidencia = _RE_NUMERO_INICIAL.match(str(valor).replace(",", "."))
    return float(coincidencia.group(1)) if coincidencia else None


def _plano_stats(detalle: Dict[str, Any]) -> Dict[str, Tuple[Optional[float], Optional[float]]]:
    """Aplana `content.stats.Periods.All.stats` a `{clave: (local, visita)}`."""
    stats = (detalle.get("content") or {}).get("stats")
    if not isinstance(stats, dict):
        stats = detalle.get("stats")
    if not isinstance(stats, dict):
        return {}
    all_period = ((stats.get("Periods") or {}).get("All")) or {}
    grupos = all_period.get("stats")
    if not isinstance(grupos, list):
        return {}
    plano: Dict[str, Tuple[Optional[float], Optional[float]]] = {}
    for grupo in grupos:
        if not isinstance(grupo, dict):
            continue
        for entrada in grupo.get("stats") or []:
            if not isinstance(entrada, dict):
                continue
            clave = str(entrada.get("key") or "").strip()
            if not clave:
                continue
            crudos = entrada.get("rawStats")
            vacios = entrada.get("stats")
            pares: List[Optional[float]] = []
            for indice in (0, 1):
                valor = None
                if isinstance(crudos, list) and len(crudos) > indice:
                    valor = _a_numero(crudos[indice])
                if valor is None and isinstance(vacios, list) and len(vacios) > indice:
                    valor = _a_numero(vacios[indice])
                pares.append(valor)
            par = (pares[0], pares[1])
            previo = plano.get(clave)
            if previo is None or all(valor is None for valor in previo):
                plano[clave] = par
    return plano


def _par(plano: Dict[str, Tuple[Optional[float], Optional[float]]], claves: Iterable[str]):
    for clave in claves:
        if clave in plano:
            return plano[clave]
    return (None, None)


def _marcador(detalle: Dict[str, Any]) -> Tuple[Optional[int], Optional[int]]:
    """Extrae el marcador final de `header`/`matchFacts`; `None` si no está publicado."""
    candidatos: List[Any] = []
    header = (detalle.get("header") or {})
    candidatos.append(header.get("status"))
    content = (detalle.get("content") or {})
    facts = content.get("matchFacts") or {}
    candidatos.append(facts.get("infoBox"))
    for bloque in candidatos:
        if not isinstance(bloque, dict):
            continue
        for ruta in ("scoreStr", "score"):
            crudo = bloque.get(ruta)
            if isinstance(crudo, str):
                numeros = re.findall(r"\d+", crudo)
                if len(numeros) >= 2:
                    return int(numeros[0]), int(numeros[1])
            if isinstance(crudo, dict):
                local = crudo.get("home") if "home" in crudo else crudo.get("Home")
                visita = crudo.get("away") if "away" in crudo else crudo.get("Away")
                if local is not None and visita is not None:
                    return int(local), int(visita)
    return None, None


def _variables_de_stats(
    plano: Dict[str, Tuple[Optional[float], Optional[float]]],
    marcador: Tuple[Optional[int], Optional[int]],
) -> Dict[str, Dict[str, Optional[float]]]:
    """Traduce el bloque de stats a las 24 variables directas + V16 declarada."""
    vector: Dict[str, Dict[str, Optional[float]]] = {
        variable: {"local": None, "visita": None} for variable in VARIABLES
    }

    for variable, claves in CLAVES_DIRECTAS.items():
        if not claves or variable == V16_FUERA_DE_FUENTE:
            continue
        if claves[0].startswith("__"):
            continue
        local, visita = _par(plano, claves)
        vector[variable] = {"local": local, "visita": visita}

    sot_l, sot_v = _par(plano, CLAVES_DIRECTAS["V07"])
    # V13 — SoTA: dual exacto de V07 (identidad declarada en `[LN-QBE-120]` DERIVACIONES).
    vector["V13"] = {"local": sot_v, "visita": sot_l}

    tackles_l, tackles_v = _par(plano, ("matchstats.headers.tackles", "total_tackle", "tackles"))
    despejes_l, despejes_v = _par(plano, ("clearances", "effective_clearance"))
    inter_l, inter_v = _par(plano, ("interceptions", "interception"))
    vector["V14"] = {
        "local": _suma(tackles_l, despejes_l, inter_l),
        "visita": _suma(tackles_v, despejes_v, inter_v),
    }

    atajadas_l, atajadas_v = _par(plano, ("keeper_saves", "saves"))
    # V18 — Save %: atajadas / SoT recibidos (identidad de conjunto).
    vector["V18"] = {
        "local": _cociente(atajadas_l, sot_v),
        "visita": _cociente(atajadas_v, sot_l),
    }

    # V20 — Clean sheet: 1 si el rival no anotó, 0 si anotó, None sin marcador.
    goles_l, goles_v = marcador
    vector["V20"] = {
        "local": None if goles_v is None else (1.0 if goles_v == 0 else 0.0),
        "visita": None if goles_l is None else (1.0 if goles_l == 0 else 0.0),
    }

    amarillas_l, amarillas_v = _par(plano, ("yellow_cards", "total_yel_card"))
    rojas_l, rojas_v = _par(plano, ("red_cards", "total_red_card"))
    # V25 — Tarjetas: amarillas + rojas (convención `[LN-QBE-146]` §2.2).
    vector["V25"] = {
        "local": _suma(amarillas_l, rojas_l),
        "visita": _suma(amarillas_v, rojas_v),
    }

    # V12 — xGA por reciprocidad defensiva (xGA_local ≡ xG_visita) sólo si xG existe.
    if vector["V12"]["local"] is None and vector["V12"]["visita"] is None:
        xg_l, xg_v = vector["V06"]["local"], vector["V06"]["visita"]
        if xg_l is not None or xg_v is not None:
            vector["V12"] = {"local": xg_v, "visita": xg_l}

    return vector


def _suma(*valores: Optional[float]) -> Optional[float]:
    """Suma declarada de identidades publicadas; `None` si TODOS los sumandos faltan."""
    presentes = [valor for valor in valores if valor is not None]
    return float(sum(presentes)) if presentes else None


def _cociente(numerador: Optional[float], denominador: Optional[float]) -> Optional[float]:
    if numerador is None or denominador in (None, 0.0):
        return None
    return round(100.0 * float(numerador) / float(denominador), 4)


# ═════════════════════════════════════════════════════════════════════════════════════════════
# CONTEXTO FACTUAL (`[LN-QBE-146]` §2.2) — SIEMPRE ANTERIOR AL KICKOFF
# ═════════════════════════════════════════════════════════════════════════════════════════════
def _normalizar(texto: Any) -> str:
    crudo = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", crudo.lower()).strip()


class Historico:
    """Corpus de la bóveda indexado para resolver el contexto pre-kickoff."""

    def __init__(self, filas: Sequence[Dict[str, Any]]) -> None:
        self.filas: List[Dict[str, Any]] = []
        for fila in filas:
            instante = _fecha_boveda(fila)
            if instante is None:
                continue
            registro = dict(fila)
            registro["_instante"] = instante
            self.filas.append(registro)
        self.filas.sort(key=lambda fila: fila["_instante"])
        self.por_equipo: Dict[str, List[Dict[str, Any]]] = {}
        for fila in self.filas:
            self.por_equipo.setdefault(str(fila.get("home_team_slug")), []).append(fila)
            self.por_equipo.setdefault(str(fila.get("away_team_slug")), []).append(fila)

    def anteriores(self, slug: str, momento: datetime) -> List[Dict[str, Any]]:
        return [f for f in self.por_equipo.get(slug, []) if f["_instante"] < momento]

    def h2h(self, local: str, visita: str, momento: datetime) -> List[Dict[str, Any]]:
        previos = []
        for fila in self.filas:
            if fila["_instante"] >= momento:
                continue
            pareja = {str(fila.get("home_team_slug")), str(fila.get("away_team_slug"))}
            if pareja == {local, visita} and local != visita:
                previos.append(fila)
        return previos

    def visitas(self, local: str, visita: str, momento: datetime) -> List[Dict[str, Any]]:
        return [
            fila
            for fila in self.por_equipo.get(visita, [])
            if fila["_instante"] < momento and str(fila.get("home_team_slug")) == local
        ]


def _puntos(fila: Dict[str, Any], slug: str) -> Optional[float]:
    goles_local = fila.get("home_goals")
    goles_visita = fila.get("away_goals")
    if goles_local is None or goles_visita is None:
        return None
    es_local = str(fila.get("home_team_slug")) == slug
    propios = goles_local if es_local else goles_visita
    rivales = goles_visita if es_local else goles_local
    return 3.0 if propios > rivales else (1.0 if propios == rivales else 0.0)


def _contexto(
    historico: Historico,
    fila: Dict[str, Any],
    momento: datetime,
) -> Dict[str, Dict[str, Optional[float]]]:
    """Calcula `V26`–`V32` con evidencia estrictamente anterior al kickoff."""
    local = str(fila.get("home_team_slug") or "")
    visita = str(fila.get("away_team_slug") or "")
    vector: Dict[str, Dict[str, Optional[float]]] = {
        variable: {"local": None, "visita": None} for variable in VARIABLES
    }

    duelos = historico.h2h(local, visita, momento)
    if duelos:
        registros = {"local": [], "visita": []}
        diferencias = {"local": [], "visita": []}
        for duelo in duelos:
            goles_local = duelo.get("home_goals")
            goles_visita = duelo.get("away_goals")
            if goles_local is None or goles_visita is None:
                continue
            anfitrion = str(duelo.get("home_team_slug"))
            # Perspectiva del fixture evaluado: goles del club `local` vs goles del club `visita`.
            if anfitrion == local:
                pro_local, pro_visita = goles_local, goles_visita
            elif anfitrion == visita:
                pro_local, pro_visita = goles_visita, goles_local
            else:  # pragma: no cover - el filtro `h2h` ya garantiza la pareja
                continue
            registros["local"].append(3.0 if pro_local > pro_visita else (1.0 if pro_local == pro_visita else 0.0))
            registros["visita"].append(3.0 if pro_visita > pro_local else (1.0 if pro_local == pro_visita else 0.0))
            diferencias["local"].append(float(pro_local - pro_visita))
            diferencias["visita"].append(float(pro_visita - pro_local))
        for lado in LADOS:
            if registros[lado]:
                # V26 — Récord H2H: tasa de victorias del club en la serie histórica.
                victorias = sum(1 for puntos in registros[lado] if puntos == 3.0)
                vector["V26"][lado] = round(victorias / len(registros[lado]), 4)
                # V27 — ΔG H2H: diferencial medio de goles en la serie.
                vector["V27"][lado] = round(sum(diferencias[lado]) / len(diferencias[lado]), 4)

    # V28 — Récord del visitante en la sede del anfitrión (sólo tiene sentido en `visita`).
    visitas = historico.visitas(local, visita, momento)
    if visitas:
        puntos = [p for p in (_puntos(fila, visita) for fila in visitas) if p is not None]
        if puntos:
            vector["V28"]["visita"] = round(sum(1 for p in puntos if p == 3.0) / len(puntos), 4)
    # Espejo simétrico: el anfitrión defiende su sede (misma serie, perspectiva local).
    if visitas:
        puntos_local = [p for p in (_puntos(fila, local) for fila in visitas) if p is not None]
        if puntos_local:
            vector["V28"]["local"] = round(sum(1 for p in puntos_local if p == 3.0) / len(puntos_local), 4)

    # V31 (forma 5P) y V32 (varianza ΔxPTS) sobre los últimos 5 partidos de cada club.
    for lado, slug in (("local", local), ("visita", visita)):
        previos = historico.anteriores(slug, momento)
        if not previos:
            continue
        ultimos = previos[-5:]
        puntos = [p for p in (_puntos(fila, slug) for fila in ultimos) if p is not None]
        if puntos:
            vector["V31"][lado] = round(sum(puntos), 4)
            if len(puntos) >= 2:
                media = sum(puntos) / len(puntos)
                vector["V32"][lado] = round(
                    sum((p - media) ** 2 for p in puntos) / len(puntos), 4
                )

    # V30 — ΔDías de descanso (local − visita) y V29 — ΔAlt⁺ (altitud del anfitrión − visita).
    descansos = {}
    for lado, slug in (("local", local), ("visita", visita)):
        previos = historico.anteriores(slug, momento)
        if previos:
            descansos[lado] = (momento - previos[-1]["_instante"]).total_seconds() / 86400.0
    if len(descansos) == 2:
        vector["V30"] = {
            "local": round(descansos["local"] - descansos["visita"], 4),
            "visita": round(descansos["visita"] - descansos["local"], 4),
        }

    altitud = max(0.0, float(altitud_estadio(local)) - float(altitud_estadio(visita)))
    vector["V29"] = {"local": round(altitud, 4), "visita": round(-altitud, 4)}
    return vector


# ═════════════════════════════════════════════════════════════════════════════════════════════
# ESQUEMA Y PERSISTENCIA
# ═════════════════════════════════════════════════════════════════════════════════════════════
def _columnas(conexion: sqlite3.Connection, tabla: str) -> set:
    return {fila[1] for fila in conexion.execute(f'PRAGMA table_info("{tabla}")')}


def _columnas_vector() -> List[Tuple[str, str]]:
    return [(f"{variable.lower()}_{lado}", "REAL") for variable in VARIABLES for lado in LADOS]


def asegurar_esquema(conexion: sqlite3.Connection) -> None:
    """Reflection DDL `[ARCH-1.5.1]` §15.2 sobre la tabla del vector causal."""
    columnas = ",\n    ".join(f"{nombre} {tipo}" for nombre, tipo in _columnas_vector())
    conexion.execute(
        f"CREATE TABLE IF NOT EXISTS {TABLA} (\n"
        f"    match_id TEXT PRIMARY KEY,\n"
        f"    {columnas},\n"
        f"    sin_evidencia TEXT NOT NULL DEFAULT '[]',\n"
        f"    derivadas INTEGER NOT NULL DEFAULT 0,\n"
        f"    fuente_datos TEXT NOT NULL DEFAULT '{FUENTE_DATOS}',\n"
        f"    cargado_utc TEXT NOT NULL DEFAULT ''\n"
        ")"
    )
    existentes = _columnas(conexion, TABLA)
    for nombre, tipo in _columnas_vector():
        if nombre not in existentes:
            conexion.execute(f'ALTER TABLE {TABLA} ADD COLUMN "{nombre}" {tipo}')


def _fila(match_id: str, vector: Dict[str, Dict[str, Optional[float]]]) -> Tuple[Any, ...]:
    sin_evidencia = [
        variable
        for variable in VARIABLES
        if vector[variable]["local"] is None and vector[variable]["visita"] is None
    ]
    con_evidencia = [variable for variable in VARIABLES if variable not in sin_evidencia]
    valores: List[Any] = [match_id]
    for variable in VARIABLES:
        for lado in LADOS:
            valores.append(vector[variable][lado])
    valores.append(json.dumps(sin_evidencia, ensure_ascii=False))
    valores.append(len(con_evidencia))
    valores.append(FUENTE_DATOS)
    valores.append(datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
    return tuple(valores)


def _insert() -> str:
    columnas = ["match_id", *[nombre for nombre, _ in _columnas_vector()]]
    columnas += ["sin_evidencia", "derivadas", "fuente_datos", "cargado_utc"]
    marcadores = ", ".join("?" for _ in columnas)
    return f"INSERT OR REPLACE INTO {TABLA} ({', '.join(columnas)}) VALUES ({marcadores})"


def _respaldo_worm(db_path: Path) -> Optional[Path]:
    """[ARCH-1.5.1] §CQRS — respaldo WORM previo a la carga bulk sobre `historical_*`."""
    if not db_path.is_file():
        return None
    destino = db_path.parent / "backups" / (
        f"{db_path.stem}_pre_sprint48_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.db"
    )
    destino.parent.mkdir(parents=True, exist_ok=True)
    origen = sqlite3.connect(str(db_path))
    copia = sqlite3.connect(str(destino))
    try:
        origen.backup(copia)
    finally:
        copia.close()
        origen.close()
    return destino


# ═════════════════════════════════════════════════════════════════════════════════════════════
# ACTA DE FALTANTES (fallos de red / proveedor)
# ═════════════════════════════════════════════════════════════════════════════════════════════
COLUMNAS_FALTANTES: Tuple[str, ...] = (
    "Temporada",
    "Jornada",
    "Fecha",
    "Local",
    "Visitante",
    "Match_ID",
    "Motivo_del_Fallo",
)


def _jornada(fixture: Dict[str, Any]) -> str:
    """Jornada declarada por el fixture (`round`/`roundName`); cadena vacía si no la publica."""
    crudo = fixture.get("round")
    if crudo in (None, ""):
        crudo = fixture.get("roundName")
    return str(crudo or "")


def _registro_fallo(
    fixture: Dict[str, Any],
    fila: Optional[Dict[str, Any]],
    temporada: str,
    motivo: str,
) -> Dict[str, str]:
    """Una fila del acta de faltantes con las siete columnas legisladas."""
    return {
        "Temporada": temporada,
        "Jornada": _jornada(fixture),
        "Fecha": str((fixture.get("status") or {}).get("utcTime") or fixture.get("utc") or ""),
        "Local": str((fixture.get("home") or {}).get("name") or fixture.get("local") or ""),
        "Visitante": str((fixture.get("away") or {}).get("name") or fixture.get("visita") or ""),
        "Match_ID": str((fila or {}).get("match_id") or ""),
        "Motivo_del_Fallo": motivo,
    }


def _escribir_faltantes(
    temporada: str, registros: Sequence[Dict[str, str]], destino: Optional[Path] = None
) -> Optional[Path]:
    """Materializa `data/reportes/faltantes_fotmob_{temporada}.csv` (UTF-8 con BOM)."""
    if not registros:
        return None
    ruta = Path(destino) if destino else (RUTA_REPORTES / f"faltantes_fotmob_{temporada}.csv")
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8-sig", newline="") as flujo:
        escritor = csv.DictWriter(flujo, fieldnames=list(COLUMNAS_FALTANTES), extrasaction="ignore")
        escritor.writeheader()
        for registro in registros:
            escritor.writerow(registro)
    return ruta


# ═════════════════════════════════════════════════════════════════════════════════════════════
# ORQUESTACIÓN
# ═════════════════════════════════════════════════════════════════════════════════════════════
def _boveda(conexion: sqlite3.Connection, temporada: str) -> List[Dict[str, Any]]:
    conexion.row_factory = sqlite3.Row
    filas = [
        dict(fila)
        for fila in conexion.execute(
            f"SELECT * FROM {TABLA_BOVEDA} WHERE temporada = ? ORDER BY fecha_utc", (temporada,)
        )
    ]
    conexion.row_factory = None
    return filas


def extraer(
    db_path: Path,
    temporada: str,
    *,
    piloto: Optional[int] = None,
    reanudar: bool = False,
    salida: Any = None,
) -> Dict[str, Any]:
    salida = salida or sys.stdout
    conexion = sqlite3.connect(str(db_path), isolation_level=None)
    conexion.execute("PRAGMA foreign_keys = ON")
    reporte: Dict[str, Any] = {
        "temporada": temporada,
        "fuente": FUENTE_DATOS,
        "pausa_waf_segundos": PAUSA_ENTRE_PETICIONES,
    }
    try:
        asegurar_esquema(conexion)
        boveda = _boveda(conexion, temporada)
        if not boveda:
            raise ExtraccionError(f"La bóveda no tiene partidos para '{temporada}'.")
        cursor = conexion.execute(f"SELECT * FROM {TABLA_BOVEDA}")
        nombres = [columna[0] for columna in cursor.description]
        historico = Historico(dict(zip(nombres, fila)) for fila in cursor.fetchall())
        ya_poblados = {
            fila[0] for fila in conexion.execute(f"SELECT match_id FROM {TABLA}")
        }

        print(f"[DISCOVERY] {temporada}: {len(boveda)} partidos en la bóveda.", file=salida)
        fixtures = _sellos_de_temporada(temporada)
        print(f"[DISCOVERY] FotMob publica {len(fixtures)} fixtures.", file=salida)

        parejas, sin_pareja = _emparejar(fixtures, boveda)
        if reanudar:
            parejas = [
                (fixture, fila) for fixture, fila in parejas if fila["match_id"] not in ya_poblados
            ]
        if piloto is not None:
            parejas = parejas[:piloto]
        print(
            f"[JOIN] emparejados {len(parejas)} · sin destino {len(sin_pareja)}", file=salida
        )

        procesados: List[str] = []
        fallidos: List[Dict[str, str]] = []
        acta: List[Dict[str, str]] = [
            _registro_fallo(
                suelto,
                None,
                temporada,
                f"UNMATCHED · {suelto['motivo']}",
            )
            for suelto in sin_pareja
        ]
        vectores: List[Tuple[str, Dict[str, Dict[str, Optional[float]]]]] = []
        for indice, (fixture, fila) in enumerate(parejas, start=1):
            fotmob_id = str(fixture.get("id") or "")
            try:
                detalle = _descargar_json(URL_PARTIDO.format(match_id=fotmob_id))
            except ExtraccionError as error:
                motivo = f"{type(error).__name__}: error de red en matchDetails"
                fallidos.append({"match_id": fila["match_id"], "error": str(error)})
                acta.append(_registro_fallo(fixture, fila, temporada, motivo))
                continue
            if detalle.get("error"):
                motivo = f"matchDetails error={detalle.get('error')}"
                fallidos.append({"match_id": fila["match_id"], "error": motivo})
                acta.append(_registro_fallo(fixture, fila, temporada, motivo))
                continue
            plano = _plano_stats(detalle)
            if not plano:
                motivo = "proveedor no publica content.stats.Periods.All"
                fallidos.append({"match_id": fila["match_id"], "error": motivo})
                acta.append(_registro_fallo(fixture, fila, temporada, motivo))
                continue

            momento = _fecha_boveda(fila)
            if momento is None:
                motivo = "fecha_utc ilegible en la bóveda"
                fallidos.append({"match_id": fila["match_id"], "error": motivo})
                acta.append(_registro_fallo(fixture, fila, temporada, motivo))
                continue

            vector = _variables_de_stats(plano, _marcador(detalle))
            contexto = _contexto(historico, fila, momento)
            for variable in CLAVES_CONTEXTO + CLAVES_FIXTURE + CLAVES_DERIVADAS:
                vector[variable] = contexto[variable]
            vector[V16_FUERA_DE_FUENTE] = {"local": None, "visita": None}

            vectores.append((fila["match_id"], vector))
            procesados.append(fila["match_id"])
            if indice % 25 == 0:
                print(f"  … {indice}/{len(parejas)} procesados", file=salida)

        # Procedencias que el lote reemplaza (`INSERT OR REPLACE`): se declaran, y el
        # respaldo WORM previo las conserva íntegras.
        previas = {
            fila[0]: fila[1]
            for fila in conexion.execute(f"SELECT match_id, fuente_datos FROM {TABLA}")
        }
        reemplazadas: Dict[str, int] = {}
        for match_id, _ in vectores:
            fuente_previa = previas.get(match_id)
            if fuente_previa and fuente_previa != FUENTE_DATOS:
                reemplazadas[fuente_previa] = reemplazadas.get(fuente_previa, 0) + 1

        respaldo = _respaldo_worm(db_path) if vectores else None
        if vectores:
            conexion.execute("BEGIN IMMEDIATE")
            try:
                for match_id, vector in vectores:
                    conexion.execute(_insert(), _fila(match_id, vector))
                conexion.execute("COMMIT")
            except BaseException:
                conexion.execute("ROLLBACK")
                raise

        integridad = conexion.execute("PRAGMA quick_check").fetchone()[0]
        total_tabla = conexion.execute(f"SELECT COUNT(*) FROM {TABLA}").fetchone()[0]
        filas_temporada = conexion.execute(
            f"SELECT COUNT(*) FROM {TABLA} v JOIN {TABLA_BOVEDA} m ON m.match_id = v.match_id "
            "WHERE m.temporada = ? AND v.fuente_datos = ?",
            (temporada, FUENTE_DATOS),
        ).fetchone()[0]
    finally:
        conexion.close()

    ruta_faltantes = _escribir_faltantes(temporada, acta)

    cobertura = {variable: 0 for variable in VARIABLES}
    for _, vector in vectores:
        for variable in VARIABLES:
            if vector[variable]["local"] is not None or vector[variable]["visita"] is not None:
                cobertura[variable] += 1

    reporte.update(
        {
            "partidos_boveda": len(boveda),
            "fixtures_fotmob": len(fixtures),
            "emparejados": len(parejas),
            "procesados": len(procesados),
            "fallidos": len(fallidos),
            "detalle_fallos": fallidos,
            "sin_destino": sin_pareja,
            "filas_temporada": filas_temporada,
            "filas_tabla": total_tabla,
            "integridad": integridad,
            "respaldo_worm": str(respaldo) if respaldo else None,
            "reporte_faltantes": str(ruta_faltantes) if ruta_faltantes else None,
            "faltantes_registrados": len(acta),
            "acta_faltantes": acta,
            "procedencias_reemplazadas": reemplazadas,
            "cobertura": cobertura,
            "variables_con_evidencia": sum(1 for n in cobertura.values() if n > 0),
            "variables_sin_evidencia": sum(1 for n in cobertura.values() if n == 0),
        }
    )
    return reporte


def _tablero(reporte: Dict[str, Any]) -> None:
    print("=" * 78)
    print(f"PILOTO HISTÓRICO FOTMOB — temporada {reporte['temporada']}")
    print("=" * 78)
    print(f"Partidos en bóveda        : {reporte['partidos_boveda']}")
    print(f"Fixtures publicados       : {reporte['fixtures_fotmob']}")
    print(f"Emparejados boveda<->FotMob: {reporte['emparejados']}")
    print(f"Procesados (con stats)    : {reporte['procesados']}")
    print(f"Fallidos                  : {reporte['fallidos']}")
    print(f"Sin destino (UNMATCHED)   : {len(reporte['sin_destino'])}")
    print(f"Filas de la temporada     : {reporte['filas_temporada']}")
    print(f"Filas en tabla            : {reporte['filas_tabla']}")
    print(f"PRAGMA quick_check        : {reporte['integridad']}")
    print(f"Respaldo WORM             : {reporte['respaldo_worm'] or '—'}")
    print(f"Acta de faltantes         : {reporte['reporte_faltantes'] or '—'} ({reporte['faltantes_registrados']} filas)")
    reemplazos = reporte.get("procedencias_reemplazadas") or {}
    if reemplazos:
        print("Procedencias reemplazadas : " + ", ".join(f"{k}={v}" for k, v in reemplazos.items()))
    print(f"Variables con evidencia   : {reporte['variables_con_evidencia']}/32")
    print(f"Variables SIN EVIDENCIA   : {reporte['variables_sin_evidencia']}/32")
    print("-" * 78)
    print(f"{'VAR':<5}{'PARTIDOS CON DATO':>20}  {'ESTADO':<18}")
    for variable, cantidad in reporte["cobertura"].items():
        estado = "CON EVIDENCIA" if cantidad else "SIN EVIDENCIA (NULL)"
        print(f"{variable:<5}{cantidad:>20}  {estado:<18}")
    print("-" * 78)
    if reporte["detalle_fallos"]:
        for fallo in reporte["detalle_fallos"][:20]:
            print(f"🔴 {fallo['match_id']}: {fallo['error']}")
    for suelto in reporte["sin_destino"][:20]:
        print(
            f"⚠️  UNMATCHED {suelto['fotmob_id']}: "
            f"{suelto['local']} vs {suelto['visita']} ({suelto['utc']})"
        )


def main(argv: Optional[Sequence[str]] = None) -> int:
    analizador = argparse.ArgumentParser(
        prog="extraer_historico_fotmob",
        description="[LN-QBE-146] Extrae el vector causal de 32 variables por partido desde FotMob.",
    )
    analizador.add_argument("--temporada", required=True, help="p. ej. 2018_2019")
    analizador.add_argument("--db", default=str(DB_DEFECTO), help="ruta de qbe_historico.db")
    analizador.add_argument("--piloto", type=int, default=None, help="tope de partidos a procesar")
    analizador.add_argument("--reanudar", action="store_true", help="omite partidos ya poblados")
    analizador.add_argument("--solo-reporte", action="store_true", help="no descarga; sólo reporta")
    analizador.add_argument("--reporte-json", default=None, help="bitácora del piloto (JSON)")
    argumentos = analizador.parse_args(argv)

    db_path = Path(argumentos.db)
    if not db_path.is_file():
        print(f"🔴 Bóveda inexistente: {db_path}", file=sys.stderr)
        return 1

    if argumentos.solo_reporte:
        conexion = sqlite3.connect(str(db_path))
        try:
            filas = conexion.execute(
                f"SELECT COUNT(*) FROM {TABLA} v JOIN {TABLA_BOVEDA} m ON m.match_id = v.match_id "
                "WHERE m.temporada = ? AND v.fuente_datos = ?",
                (argumentos.temporada, FUENTE_DATOS),
            ).fetchone()[0]
        finally:
            conexion.close()
        print(f"{TABLA} · temporada {argumentos.temporada} · fuente {FUENTE_DATOS}: {filas} filas")
        return 0

    try:
        reporte = extraer(
            db_path,
            argumentos.temporada,
            piloto=argumentos.piloto,
            reanudar=argumentos.reanudar,
        )
    except (ExtraccionError, sqlite3.Error) as error:
        print(f"🔴 {error}", file=sys.stderr)
        return 1

    if argumentos.reporte_json:
        ruta = Path(argumentos.reporte_json)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(json.dumps(reporte, ensure_ascii=False, indent=2), encoding="utf-8")

    _tablero(reporte)
    return 0 if reporte["integridad"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
