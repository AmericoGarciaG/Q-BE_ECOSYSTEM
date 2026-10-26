# -*- coding: utf-8 -*-
"""
🏆 Q-BE CD WEB — CENTINELA DE PRONÓSTICOS DEPORTIVOS (scripts/daemons/centinela_progol.py)
[LN-QBE-075] Ingesta fáctica de Concursos Progol Regular + Revancha con resiliencia multi-torneo.
[ARCH-1.5.1-C] Persistencia 3NF en `slates` / `slate_items`.
SDLC-02: Standalone Background Engine (precedente: centinela_mercado.py).
Régimen: [DIRGEN-STRICT] para el vínculo soberano / Prior Fiduciario; [DBBD-FUNGIBLE] para el tablero.

Cascada de resiliencia [LN-QBE-075]:
  Caso A — Club en catálogo + partido en `matches` + distribución en `sovereign_distributions`
           => probabilidades soberanas reales, `es_prior_ignorancia = False`.
  Caso B — Club desconocido / partido ausente / bóveda inaccesible
           => Prior de Ignorancia Fiduciaria (0.3333, 0.3333, 0.3334), `match_id = None`.
Ninguna casilla congela el sistema: todo fallo degrada al Prior.

Matching elástico [VARIANCE-05 ratificada]: el vínculo Caso A coteja el slug canónico del club contra
`matches.home_team_slug` / `matches.away_team_slug` por contención mutua, tolerando prefijos societarios
('club-', 'deportivo-'). El cotejo es estrictamente de IDENTIDAD: la probabilidad sigue proviniendo
exclusivamente de `sovereign_distributions` (cero cálculo paralelo en el plano de ingesta).

Guardas de integridad fáctica [VARIANCE-04]: 0 casillas o par local/visitante incompleto => ALTO AL FUEGO
(exit 1), sin escribir nada en `slates`/`slate_items` (prohibida la persistencia silenciosa de datos corruptos).

[ARCH-1.4.22] Al cierre de CADA casilla degradada al Prior (Caso B) se dispara el descubrimiento JIT de la
competición del club (buscador estructurado de FotMob, caché de corrida por club). El descubrimiento se
inscribe en la MISMA transacción de la ingesta y degrada de forma explícita: JAMÁS bloquea el concurso.

[ARCH-1.6.20] El buscador estructurado de FotMob se fija al endpoint ACTIVO `/api/searchapi/suggest`,
erradicando el HTTP 404 (text/html) del endpoint deprecado `/api/search/searchapi` (SONDEO-03).

[ARCH-1.5.11] Estrato 0 de identidad: toda casilla (local y visitante) atraviesa el catálogo
determinista `PROGOL_GLOBAL_ALIASES` ANTES del cotejo elástico en SQLite y ANTES del normalizador
difuso. La traducción es puramente nominal: la probabilidad sigue proviniendo EXCLUSIVAMENTE de
`sovereign_distributions` (cero fabricación de identidades ni de distribuciones en el plano de ingesta).
"""

import re
import sys
import time
import urllib.parse
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.ingestion.normalizer import canonicalize_team_name
from src.ingestion.progol_scraper import (
    PROGOL_JARGON_MAP,
    CASILLAS_REGULAR,
    CASILLAS_REVANCHA,
    PRIOR_IGNORANCIA_FIDUCIARIA,
    ProgolMarketScraper,
)
from src.ingestion.progol_resolver import (
    parsear_respuesta_search_fotmob,
    traducir_jerga_global_progol,
    registrar_liga_descubierta_si_no_existe,
)
from src.storage.crest_resolver import obtener_slug_club, resolver_escudo_canonico
from src.storage.database import Base
from src.storage.gateway import PersistenceGateway
from src.storage.models import Match, Slate, SlateItem, SovereignDistribution

logger = logging.getLogger("CentinelaProgol")

ETIQUETA_PRIOR = "PRIOR DE IGNORANCIA FIDUCIARIA (1/3 - LN-QBE-075)"
ETIQUETA_SOBERANO = "SOBERANO (DISTRIBUCIÓN 3NF)"

# [ARCH-1.4.22] Descubrimiento JIT: buscador estructurado de FotMob (endpoint legislado).
# [ARCH-1.6.20] Endpoint ACTIVO de sugerencias (firma `?term=`): `/api/search/searchapi` queda deprecado (HTTP 404).
FOTMOB_SEARCH_API_URL = "https://www.fotmob.com/api/searchapi/suggest?term={term}"
FOTMOB_JIT_TIMEOUT_S = 15.0
FOTMOB_JIT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
    "Referer": "https://www.fotmob.com/",
}


def _canonizar_seguro(nombre: str) -> str:
    """
    Normaliza a identidad canónica preservando el nombre limpio si el catálogo no lo conoce.
    [VARIANCE-05] Estrato 1 — traducción de jerga comercial (PROGOL_JARGON_MAP, fuente única en
    progol_scraper.py); Estrato 2 — normalizador difuso del catálogo canónico.
    """
    limpio = (nombre or "").strip()
    if not limpio:
        return ""
    traducido = PROGOL_JARGON_MAP.get(limpio.upper(), limpio)
    try:
        return canonicalize_team_name(traducido)
    except Exception as e:
        logger.warning("⚠️ Normalización fallida para '%s' (%s). Se preserva el nombre limpio.", limpio, type(e).__name__)
        return limpio


def _slug_seguro(nombre: str) -> str:
    """Slug canónico tolerante a fallos (vacío si no es resoluble)."""
    if not nombre:
        return ""
    try:
        return obtener_slug_club(nombre)
    except Exception as e:
        logger.warning("⚠️ Slug fallido para '%s' (%s).", nombre, type(e).__name__)
        return ""


def _bolsa_a_float(bolsa: str) -> Optional[float]:
    """
    Convierte el monto fáctico del sitio ('$8,800,000.00') a float preservando los centavos.
    Formato fáctico de miloteria.mx: coma = separador de miles, punto = separador decimal.
    '$8,800,000.00' => 8800000.0 (jamás 880000000.0). Sin dígitos ('Bolsa por Definir') => None.
    """
    limpio = re.sub(r"[^\d.,]", "", bolsa or "")
    if not limpio:
        return None
    if "," in limpio and "." in limpio:
        # El último separador en aparecer es el decimal.
        if limpio.rfind(".") > limpio.rfind(","):
            limpio = limpio.replace(",", "")
        else:
            limpio = limpio.replace(".", "").replace(",", ".")
    elif "," in limpio:
        limpio = limpio.replace(",", "")
    try:
        return float(limpio)
    except ValueError:
        logger.warning("⚠️ Monto de bolsa no interpretable ('%s'). Se persiste None.", bolsa)
        return None


def _escudo_seguro(nombre: str, db_session: Optional[Any]) -> str:
    """Resuelve escudo bajo [LN-QBE-019]; ante cualquier fallo entrega el SVG institucional."""
    try:
        return resolver_escudo_canonico(nombre, db=db_session)
    except Exception as e:
        logger.warning("⚠️ Escudo no resuelto para '%s' (%s). Se usa placeholder institucional.", nombre, type(e).__name__)
        return resolver_escudo_canonico("")


def procesar_casilla_con_resiliencia(local: str, visitante: str, db_session: Optional[Any] = None) -> Dict[str, Any]:
    """
    [LN-QBE-075] Resuelve una casilla Progol: Vínculo Soberano (Caso A) o Prior de Ignorancia (Caso B).
    Contrato de salida: local_raw, visitante_raw, local_canonico, visitante_canonico, match_id,
    p_local, p_empate, p_visitante, es_prior_ignorancia, estado_qbe, model_version y escudos.
    """
    resultado: Dict[str, Any] = {
        "local_raw": (local or "").strip(),
        "visitante_raw": (visitante or "").strip(),
        "local_canonico": (local or "").strip(),
        "visitante_canonico": (visitante or "").strip(),
        "slug_local": "",
        "slug_visitante": "",
        "match_id": None,
        "p_local": PRIOR_IGNORANCIA_FIDUCIARIA[0],
        "p_empate": PRIOR_IGNORANCIA_FIDUCIARIA[1],
        "p_visitante": PRIOR_IGNORANCIA_FIDUCIARIA[2],
        "es_prior_ignorancia": True,
        "estado_qbe": ETIQUETA_PRIOR,
        "model_version": "PRIOR-FIDUCIARIO-1/3",
    }

    try:
        # [ARCH-1.5.11] Estrato 0: traducción determinista de jerga/aliases globales de las 21 casillas,
        # aplicada ANTES del cotejo elástico en SQLite y ANTES del normalizador difuso. `local_raw` /
        # `visitante_raw` conservan la literalidad fáctica del operador (procedencia intacta).
        identidad_local = traducir_jerga_global_progol(local)
        identidad_visitante = traducir_jerga_global_progol(visitante)

        resultado["local_canonico"] = _canonizar_seguro(identidad_local)
        resultado["visitante_canonico"] = _canonizar_seguro(identidad_visitante)
        resultado["slug_local"] = _slug_seguro(resultado["local_canonico"])
        resultado["slug_visitante"] = _slug_seguro(resultado["visitante_canonico"])

        if db_session is not None and resultado["slug_local"] and resultado["slug_visitante"]:
            # [VARIANCE-05 ratificada] Cotejo elástico por contención mutua de slugs, tolerante a
            # prefijos societarios ('club-', 'deportivo-'). El escrutinio preserva la jornada más
            # reciente y el vínculo JAMÁS fabrica probabilidad: sólo localiza el partido en `matches`.
            slug_local_norm = resultado["slug_local"].replace("club-", "").replace("deportivo-", "")
            slug_visitante_norm = resultado["slug_visitante"].replace("club-", "").replace("deportivo-", "")
            partido = None
            for candidato in db_session.query(Match).order_by(Match.matchday_num.desc()).all():
                cand_local = str(
                    getattr(candidato, "home_team_slug", None)
                    or getattr(candidato, "home_team_id", None)
                    or ""
                ).replace("club-", "").replace("deportivo-", "")
                cand_visitante = str(
                    getattr(candidato, "away_team_slug", None)
                    or getattr(candidato, "away_team_id", None)
                    or ""
                ).replace("club-", "").replace("deportivo-", "")
                if not cand_local or not cand_visitante:
                    continue
                if (slug_local_norm in cand_local or cand_local in slug_local_norm) and (
                    slug_visitante_norm in cand_visitante or cand_visitante in slug_visitante_norm
                ):
                    partido = candidato
                    break
            if partido is not None:
                dist = (
                    db_session.query(SovereignDistribution)
                    .filter(SovereignDistribution.match_id == partido.id)
                    .first()
                )
                if dist is not None:
                    resultado.update({
                        "match_id": partido.id,
                        "p_local": dist.p_local,
                        "p_empate": dist.p_empate,
                        "p_visitante": dist.p_visitante,
                        "es_prior_ignorancia": False,
                        "estado_qbe": ETIQUETA_SOBERANO,
                        "model_version": dist.model_version,
                    })
    except Exception as e:
        logger.warning(
            "⚠️ Resiliencia [LN-QBE-075] en '%s vs %s' (%s: %s). Se aplica el Prior de Ignorancia.",
            local, visitante, type(e).__name__, e,
        )

    resultado["escudo_local_url"] = _escudo_seguro(resultado["local_canonico"], db_session)
    resultado["escudo_visitante_url"] = _escudo_seguro(resultado["visitante_canonico"], db_session)
    return resultado


def _consultar_busqueda_fotmob(club: str) -> Optional[Dict[str, Any]]:
    """[LN-QBE-088] GET del buscador estructurado de FotMob para un club.

    Degradación explícita (SONDEO-03): cualquier fallo de red, HTTP no-200 o content-type no JSON
    devuelve `None`; JAMÁS se propaga una excepción al bucle de ingesta.
    """
    import httpx

    termino = urllib.parse.quote(str(club or "").strip())
    if not termino:
        return None
    try:
        resp = httpx.get(
            FOTMOB_SEARCH_API_URL.format(term=termino),
            headers=FOTMOB_JIT_HEADERS,
            timeout=FOTMOB_JIT_TIMEOUT_S,
            follow_redirects=True,
        )
        tipo = str(resp.headers.get("content-type") or "").lower()
        if resp.status_code == 200 and "json" in tipo:
            return resp.json()
        logger.info(
            "ℹ️ [ARCH-1.4.22] Buscador FotMob para '%s' HTTP %s (content-type=%s): descubrimiento diferido.",
            club, resp.status_code, tipo or "desconocido"
        )
    except Exception as e:
        logger.warning(
            "⚠️ [ARCH-1.4.22] Buscador FotMob inaccesible para '%s' (%s: %s): descubrimiento diferido.",
            club, type(e).__name__, e
        )
    return None


def disparar_descubrimiento_jit(tx: Any, analisis: Dict[str, Any], cache: Dict[str, Any]) -> None:
    """[ARCH-1.4.22] Inscribe atómicamente en `leagues` la competición de una casilla degradada al Prior.

    Se dispara SÓLO en Caso B (`es_prior_ignorancia = True`), en la MISMA transacción de la ingesta
    (atomicidad: si la ingesta aborta, el descubrimiento no queda huérfano). Guarda de corrida por
    club (`cache`): a lo sumo UNA consulta por club y por corrida. La ingesta del concurso JAMÁS se
    interrumpe: todo fallo se registra y la casilla conserva su Prior Fiduciario [LN-QBE-075].
    """
    clubes = (
        analisis.get("local_canonico") or analisis.get("local_raw"),
        analisis.get("visitante_canonico") or analisis.get("visitante_raw"),
    )
    for club in clubes:
        nombre = str(club or "").strip()
        if not nombre or nombre in cache:
            continue
        cache[nombre] = None
        try:
            payload = _consultar_busqueda_fotmob(nombre)
            if not payload:
                continue
            hallazgo = parsear_respuesta_search_fotmob(payload, nombre)
            if not hallazgo:
                logger.info("ℹ️ [ARCH-1.4.22] Club '%s' sin competición resoluble: Prior Fiduciario preservado.", nombre)
                continue
            liga = registrar_liga_descubierta_si_no_existe(tx, {
                "fotmob_league_id": hallazgo["fotmob_league_id"],
                "league_name": hallazgo["league_name"],
                "country": hallazgo.get("country") or "Internacional",
            })
            cache[nombre] = getattr(liga, "fotmob_id", hallazgo["fotmob_league_id"])
            logger.info(
                "🏛️ [ARCH-1.4.22] Competición '%s' (FotMob %s) disponible para '%s'.",
                hallazgo["league_name"], hallazgo["fotmob_league_id"], nombre
            )
        except Exception as e:
            logger.warning(
                "⚠️ [ARCH-1.4.22] Descubrimiento JIT fallido para '%s' (%s: %s). La ingesta continúa.",
                nombre, type(e).__name__, e
            )


def sincronizar_progol_en_sqlite(url: Optional[str] = None) -> int:
    """Ejecuta la ingesta fáctica y persiste el concurso completo (21 casillas) en SQLite."""
    t0 = time.perf_counter()

    gateway = PersistenceGateway()
    gateway.create_all_tables(Base.metadata)

    payload = ProgolMarketScraper.extraer_concurso_activo(url)
    concurso_id = payload["concurso_id"]

    if not payload["partidos_regular"] and not payload["partidos_revancha"]:
        print("🚨 [ALTO AL FUEGO] Ingesta vacía (0 casillas fácticas): no se persiste nada. Revisar conectividad o selectores.")
        return 1

    # [VARIANCE-04] Guarda de integridad fáctica: una casilla Progol SIEMPRE tiene local y visitante.
    # Un par incompleto delata un corte estructural fallido, no una casilla legítima.
    incompletas = [
        f"{p['tipo'][:3]}-{p['posicion']}"
        for p in (payload["partidos_regular"] + payload["partidos_revancha"])
        if not p["local_raw"] or not p["visitante_raw"]
    ]
    if incompletas:
        print(f"🚨 [ALTO AL FUEGO] {len(incompletas)} casillas con par local/visitante incompleto ({', '.join(incompletas)}): no se persiste nada.")
        return 1

    ahora = datetime.now(timezone.utc)
    casillas_procesadas = []
    cache_descubrimiento_jit: Dict[str, Any] = {}  # [ARCH-1.4.22] Una consulta por club y por corrida.

    with gateway.write_transaction() as tx:
        bolsa_num = _bolsa_a_float(payload["bolsa"])
        slate = tx.query(Slate).filter(Slate.id == concurso_id).first()
        if not slate:
            slate = Slate(
                id=concurso_id,
                name=f"Progol Concurso {payload['concurso_num']}",
                competition_id="MEX_LIGAMX",
                matchday_num=10,
                bolsa_estimada=bolsa_num,
                fecha_cierre=None,  # El sitio publica día/mes sin año: no se inventa fecha.
                status="OPEN",
                created_at=ahora.replace(tzinfo=None)
            )
            tx.add(slate)
            tx.flush()
        else:
            slate.bolsa_estimada = bolsa_num
            slate.status = "OPEN"

        # Purgar items previos del mismo slate si existían
        tx.query(SlateItem).filter(SlateItem.slate_id == concurso_id).delete(synchronize_session=False)
        tx.flush()

        # 1. Procesar 14 partidos Progol Regular
        for p in payload["partidos_regular"]:
            analisis = procesar_casilla_con_resiliencia(p["local_raw"], p["visitante_raw"], db_session=tx)
            if analisis["es_prior_ignorancia"]:
                disparar_descubrimiento_jit(tx, analisis, cache_descubrimiento_jit)
            item = SlateItem(
                slate_id=concurso_id,
                tipo_concurso="REGULAR",
                position=p["posicion"],
                local_raw=analisis["local_raw"],
                visitante_raw=analisis["visitante_raw"],
                local_canonico=analisis["local_canonico"],
                visitante_canonico=analisis["visitante_canonico"],
                match_id=analisis["match_id"],
                p_local=analisis["p_local"],
                p_empate=analisis["p_empate"],
                p_visitante=analisis["p_visitante"],
                es_prior_ignorancia=analisis["es_prior_ignorancia"],
            )
            tx.add(item)
            casillas_procesadas.append({
                "pos": p["posicion"], "tipo": "REGULAR",
                "partido": f"{analisis['local_canonico']} vs {analisis['visitante_canonico']}",
                "estado_qbe": analisis["estado_qbe"],
                "dist": f"{analisis['p_local']*100:.0f}% · {analisis['p_empate']*100:.0f}% · {analisis['p_visitante']*100:.0f}%",
                "vinculo": analisis["match_id"] or "—"
            })

        # 2. Procesar 7 partidos Revancha
        for p in payload["partidos_revancha"]:
            analisis = procesar_casilla_con_resiliencia(p["local_raw"], p["visitante_raw"], db_session=tx)
            if analisis["es_prior_ignorancia"]:
                disparar_descubrimiento_jit(tx, analisis, cache_descubrimiento_jit)
            item = SlateItem(
                slate_id=concurso_id,
                tipo_concurso="REVANCHA",
                position=p["posicion"] + CASILLAS_REGULAR,  # 15 a 21
                local_raw=analisis["local_raw"],
                visitante_raw=analisis["visitante_raw"],
                local_canonico=analisis["local_canonico"],
                visitante_canonico=analisis["visitante_canonico"],
                match_id=analisis["match_id"],
                p_local=analisis["p_local"],
                p_empate=analisis["p_empate"],
                p_visitante=analisis["p_visitante"],
                es_prior_ignorancia=analisis["es_prior_ignorancia"],
            )
            tx.add(item)
            casillas_procesadas.append({
                "pos": p["posicion"], "tipo": "REVANCHA",
                "partido": f"{analisis['local_canonico']} vs {analisis['visitante_canonico']}",
                "estado_qbe": analisis["estado_qbe"],
                "dist": f"{analisis['p_local']*100:.0f}% · {analisis['p_empate']*100:.0f}% · {analisis['p_visitante']*100:.0f}%",
                "vinculo": analisis["match_id"] or "—"
            })

    # Imprimir Tablero
    t_tot = time.perf_counter() - t0
    banner = "=" * 125
    subbanner = "-" * 125
    print("\n" + banner)
    print(f"🏆 Q-BE CD WEB — CENTINELA DE PRONÓSTICOS DEPORTIVOS (CONCURSO {payload['concurso_num']})")
    print(banner)
    print(f"BOLSA ESTIMADA: {payload['bolsa']} | CIERRE: {payload['fecha_cierre']} | PERSISTENCIA: data/qbe_database.db [WAL Mode] | TIEMPO: {t_tot:.2f}s")
    print(subbanner)
    print(f" #  {'TIPO':<10} {'ENCUENTRO':<36} {'ESTADO MODELO':<24} {'DISTRIBUCIÓN (1-X-2)':<25} {'VÍNCULO BD'}")
    print(subbanner)

    for c in casillas_procesadas:
        print(f" {c['pos']:<2} {c['tipo']:<10} {c['partido']:<36} {c['estado_qbe']:<24} {c['dist']:<25} {c['vinculo']}")

    print(subbanner)
    soberanos = sum(1 for c in casillas_procesadas if "SOBERANO" in c["estado_qbe"])
    priors = sum(1 for c in casillas_procesadas if "PRIOR" in c["estado_qbe"])
    print(f"TOTAL CASILLAS: {CASILLAS_REGULAR + CASILLAS_REVANCHA} ({CASILLAS_REGULAR} Progol + {CASILLAS_REVANCHA} Revancha) | Modelados Q-BE: {soberanos} | Priors de Resiliencia: {priors}")
    print(banner + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(sincronizar_progol_en_sqlite())
