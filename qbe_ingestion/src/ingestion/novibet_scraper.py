# -*- coding: utf-8 -*-
"""
Q-BE Casino Deportes — Novibet Market Scraper (src/ingestion/novibet_scraper.py)
[ARCH-1.4.6-F] & [ARCH-1.4.6-C] & [LN-QBE-007-B, C, D, E]
Sensor de Ingesta Feed-First para Novibet.mx: intercepción del feed JSON
`/spt/feed/marketviews/location/v2/` (Angular + SignalR), no scraping de DOM.

[C-1] Axioma de transporte (cero matemática propia): la conversión de cuotas americanas a
decimales NO se re-escribe en este módulo. Se delega al artefacto canónico de bóveda
[VAULT-SCRAPER-001-A] (`BetwayMarketScraper.american_to_decimal`). El feed de Novibet publica
`price` ya en decimal nativo (evidencia fáctica del peritaje: 3.0 / 3.5 / 2.35 en
Puebla-León J11) y `oddsText` transporta el despliegue americano (+200 / +250 / +135), que sólo
se consume como respaldo declarado si `price` faltara. `src/core/` permanece intacto.

[C-2] Axioma de transporte tolerante (VARIANCE-01 §V-2): el Juez Inmutable
`tests/shield/test_shield_novibet_ingestion.py` modela las colecciones como
`betViews[].items[].marketViews[].itemViews[]` con selección por `caption`, mientras el feed
auditado en vivo publica `items[].markets[].betItems[]` con selección por `code` (raíz `list`,
`marketTags` a nivel evento con `marketId`). El parser resuelve por alias de clave para honrar
simultáneamente el contrato legislado y la evidencia fáctica; jamás se inventa una selección
ausente en los datos.
"""

import sys
import time
import logging
import unicodedata
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.ingestion.normalizer import canonicalize_team_name
from src.ingestion.betway_scraper import BetwayMarketScraper

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

logger = logging.getLogger("NovibetScraper")

NOVIBET_LIGA_MX_URL = "https://www.novibet.mx/apuestas-deportivas/futbol/mexico/liga-mx"
# [ARCH-1.4.6-F] Ruta de transporte auditada: es la única que monta el componente de mercados
# y emite el feed. Evidencia fáctica del turno 2026-09-28 (Playwright headless, misma sesión):
#   · Ruta legislada `/futbol/mexico/liga-mx` → HTTP 200, hidratación `sb-market-bet-item`
#     = False (timeout 20s), 1 request `/spt/`, **0** respuestas de marketviews.
#   · Ruta de carrusel `?t=6792246` → hidratación True en 13.4s, 79 requests `/spt/`,
#     **3** respuestas de `/spt/feed/marketviews/`. El parámetro `t=6792246` es exactamente el
#     `locationId` del feed capturado (`/v2/4324/6792246/`), con `4324` = clientId.
NOVIBET_CARTELERA_URL = (
    "https://www.novibet.mx/apuestas-deportivas/populares/4561745/competitions"
    "?ids=6791922,4596556,6589925&t=6792246"
)
# Señal fáctica de hidratación: el componente Angular de mercados ya montó.
NOVIBET_SELECTOR_HIDRATACION = "sb-market-bet-item, [class*='marketDisplay_row']"
NOVIBET_FEED_NAMESPACE = "/spt/feed/marketviews/location/v2/"
NOVIBET_LOGO_URL = "https://www.novibet.mx/assets/images/shared/header_logo.svg"

MERCADO_CANONICO_1X2 = "SOCCER_MATCH_RESULT"
TAG_PAGO_ANTICIPADO_2_GOLES = "SOCCER_2_GOALS_AHEAD_EARLY_PAYOUT"

# Selecciones canónicas del mercado 1X2 (evidencia fáctica: `code` y `caption` coinciden).
SELECCIONES_1X2 = ("1", "X", "2")

# [ARCH-1.4.6-F] Pre-siembra de consentimiento: Cookiebot se satisface antes del primer byte,
# sin modal y sin espera interactiva (bypass determinista verificado en 4 ejecuciones).
COOKIE_CONSENT_SEED = (
    "{stamp:'-1',necessary:true,preferences:true,statistics:true,"
    "marketing:true,method:'explicit',ver:1,utc:1727500000000}"
)

# Alias de colección: se prefiere la clave del feed auditado y se acepta la del contrato.
_CLAVES_MERCADOS = ("markets", "marketViews")
_CLAVES_SELECCIONES = ("betItems", "itemViews")

# Tokens de ruido societario que jamás distinguen a un club (cotejo por identidad desnuda).
_TOKENS_RUIDO = frozenset({"fc", "cf", "club", "deportivo", "atletico", "unam", "chivas"})


def _coleccion(nodo: Any, *claves: str) -> List[Dict[str, Any]]:
    """Resuelve una colección de nodos por alias de clave (feed auditado primero)."""
    if not isinstance(nodo, dict):
        return []
    for clave in claves:
        valor = nodo.get(clave)
        if isinstance(valor, list):
            return [v for v in valor if isinstance(v, dict)]
    return []


def _clave_cotejo(nombre: Optional[str]) -> str:
    """Identidad desnuda del club para el cotejo contra el Slate (sin ruido societario)."""
    if not nombre:
        return ""
    plano = "".join(
        c for c in unicodedata.normalize("NFKD", str(nombre)) if not unicodedata.combining(c)
    ).lower()
    plano = plano.replace(".", "").replace("-", " ")
    plano = "".join(c if (c.isalnum() or c.isspace()) else " " for c in plano)
    return " ".join(t for t in plano.split() if t not in _TOKENS_RUIDO).strip()


class NovibetMarketScraper:
    """Sensor de Ingesta Feed-First para Novibet.mx (Angular + JSON feed + SignalR).

    [ARCH-1.4.6-F] Novibet no es objetivo de scraping DOM: su cartelera se hidrata desde el
    feed `/spt/feed/marketviews/location/v2/{clientId}/{locationId}/`. El sensor intercepta esa
    respuesta (Transporte), extrae el mercado canónico 1X2 y delega el cotejo al normalizador
    canónico, sin tocar la matemática de `src/core/`.
    """

    # ── Nivel Parsing: contrato puro, determinista, sin red ──────────────────
    @staticmethod
    def _iterar_eventos(payload: Any) -> List[Dict[str, Any]]:
        """Recorre la raíz del feed (lista o nodo) hasta los eventos de partido."""
        nodos = payload if isinstance(payload, list) else [payload]
        eventos: List[Dict[str, Any]] = []
        for raiz in nodos:
            if not isinstance(raiz, dict):
                continue
            for vista in (_coleccion(raiz, "betViews") or [raiz]):
                eventos.extend(_coleccion(vista, "items"))
        return eventos

    @staticmethod
    def _resolver_mercado_1x2(evento: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Selecciona el mercado canónico `SOCCER_MATCH_RESULT` (1X2)."""
        for mercado in _coleccion(evento, *_CLAVES_MERCADOS):
            if str(mercado.get("betTypeSysname") or "") == MERCADO_CANONICO_1X2:
                return mercado
        return None

    @staticmethod
    def _precio_decimal(seleccion: Dict[str, Any]) -> float:
        """`price` decimal nativo; `oddsText` americano vía [VAULT-SCRAPER-001-A]."""
        precio = seleccion.get("price")
        try:
            if precio is not None:
                valor = float(precio)
                if valor > 1.0:
                    return round(valor, 2)
        except (TypeError, ValueError):
            pass
        return BetwayMarketScraper.american_to_decimal(seleccion.get("oddsText"))

    @staticmethod
    def _tags_de(nodo: Any) -> List[str]:
        """Normaliza `marketTags` (lista de dicts con `tag`, o lista de strings)."""
        crudo = nodo.get("marketTags") if isinstance(nodo, dict) else None
        etiquetas: List[str] = []
        if isinstance(crudo, list):
            for item in crudo:
                if isinstance(item, dict) and item.get("tag"):
                    etiquetas.append(str(item["tag"]))
                elif isinstance(item, str):
                    etiquetas.append(item)
        return etiquetas

    @classmethod
    def _selecciones_1x2(cls, mercado: Dict[str, Any]) -> Dict[str, float]:
        """Mapea `code`/`caption` de cada apuesta a las llaves canónicas L/E/V."""
        selecciones: Dict[str, float] = {}
        for apuesta in _coleccion(mercado, *_CLAVES_SELECCIONES):
            clave = str(apuesta.get("code") or apuesta.get("caption") or "").strip().upper()
            if clave not in SELECCIONES_1X2 or clave in selecciones:
                continue
            precio = cls._precio_decimal(apuesta)
            if precio > 1.0:
                selecciones[clave] = precio
        return selecciones

    @staticmethod
    def parse_feed_json(data: Any) -> List[Dict[str, Any]]:
        """[ARCH-1.4.6-F] Contrato IPO: payload del feed -> eventos 1X2 con L/E/V y +PA."""
        resultados: List[Dict[str, Any]] = []

        for evento in NovibetMarketScraper._iterar_eventos(data):
            captions = evento.get("additionalCaptions")
            local = captions.get("competitor1") if isinstance(captions, dict) else None
            visitante = captions.get("competitor2") if isinstance(captions, dict) else None
            if not local or not visitante:
                logger.debug("[NOVIBET] [IGNORADO] Evento sin competidores declarados.")
                continue

            mercado = NovibetMarketScraper._resolver_mercado_1x2(evento)
            if not mercado:
                logger.debug(f"[NOVIBET] [IGNORADO] Sin mercado {MERCADO_CANONICO_1X2}: {local} vs {visitante}")
                continue

            selecciones = NovibetMarketScraper._selecciones_1x2(mercado)
            if any(nombre not in selecciones for nombre in SELECCIONES_1X2):
                logger.debug(f"[NOVIBET] [IGNORADO] 1X2 incompleto: {local} vs {visitante}")
                continue

            etiquetas = NovibetMarketScraper._tags_de(evento) + NovibetMarketScraper._tags_de(mercado)
            metadata = evento.get("metadata") if isinstance(evento.get("metadata"), dict) else {}

            resultados.append({
                "local_raw": str(local).strip(),
                "visitante_raw": str(visitante).strip(),
                "L": selecciones["1"],
                "E": selecciones["X"],
                "V": selecciones["2"],
                "pago_anticipado": TAG_PAGO_ANTICIPADO_2_GOLES in etiquetas,
                "start_date": evento.get("startDate"),
                "jornada": metadata.get("tournamentRound"),
                "sportradar_match_id": evento.get("sportradarMatchId"),
                "num_mercados": evento.get("numMarkets"),
                "fuente": "novibet_feed",
            })

        return resultados

    # ── Nivel Red: intercepción del feed (única frontera con el exterior) ────
    @classmethod
    def _interceptar_feed(cls, url: Optional[str] = None) -> List[Any]:
        """[ARCH-1.4.6-C] Intercepta las respuestas JSON del namespace del feed de Novibet."""
        target_url = url or NOVIBET_CARTELERA_URL
        payloads: List[Any] = []

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("[NOVIBET] [ERROR] Playwright no está instalado.")
            print("❌ [NOVIBET] Playwright no disponible en el entorno.")
            return payloads

        capturadas: List[Dict[str, Any]] = []

        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True, args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-infobars",
                    "--ignore-certificate-errors",
                ])
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1600, "height": 900},
                    locale="es-MX",
                    timezone_id="America/Mexico_City",
                )
                # [ARCH-1.4.6-F] El consentimiento se siembra antes del primer byte.
                context.add_cookies([{
                    "name": "CookieConsent",
                    "value": COOKIE_CONSENT_SEED,
                    "domain": ".novibet.mx",
                    "path": "/",
                }])
                page = context.new_page()
                page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

                def _capturar(respuesta):
                    try:
                        if NOVIBET_FEED_NAMESPACE in respuesta.url and respuesta.status == 200:
                            capturadas.append({
                                "url": respuesta.url,
                                "status": respuesta.status,
                                "payload": respuesta.json(),
                            })
                    except Exception as ex:
                        logger.debug(f"[NOVIBET] Respuesta del feed no decodificable: {ex}")

                context.on("response", _capturar)

                t0 = time.perf_counter()
                respuesta = page.goto(target_url, timeout=45000, wait_until="domcontentloaded")
                t_nav = time.perf_counter() - t0

                codigo = respuesta.status if respuesta else 0
                estado = respuesta.status_text if respuesta else "sin respuesta"
                print(f"🌐 [NOVIBET] [RED] HTTP {codigo} {estado} | navegación {t_nav:.2f}s | {target_url}")
                if codigo != 200:
                    print(f"⚠️ [NOVIBET] [FAIL-LOUD] Navegación HTTP {codigo} != 200: el feed podría no hidratarse.")

                # [ARCH-1.4.6-C] Nivel DOM: la aparición del componente de mercados es la
                # señal fáctica de hidratación; sin ella el feed jamás se emite.
                hidratado = False
                try:
                    page.wait_for_selector(NOVIBET_SELECTOR_HIDRATACION, timeout=20000)
                    hidratado = True
                except Exception:
                    hidratado = False
                print(
                    f"🧩 [NOVIBET] [DOM] Hidratación del componente de mercados: {hidratado} "
                    f"({time.perf_counter() - t0:.1f}s) | selector '{NOVIBET_SELECTOR_HIDRATACION}'"
                )

                # Dwell acotado para completar la emisión del feed de la cartelera.
                page.wait_for_timeout(9000)
                browser.close()
        except Exception as ex:
            logger.error(f"[NOVIBET] [ERROR] Fallo de navegación: {ex}")
            print(f"❌ [NOVIBET] [FAIL-LOUD] Fallo de navegación Playwright: {ex}")
            return payloads

        print(f"📡 [NOVIBET] [DOM] Respuestas capturadas del namespace '{NOVIBET_FEED_NAMESPACE}': {len(capturadas)}")
        if not capturadas:
            print("⚠️ [NOVIBET] [FAIL-LOUD] Cero respuestas del feed interceptadas (consentimiento, hidratación o bloqueo de red).")

        for captura in capturadas:
            print(f"   ↳ HTTP {captura['status']} OK | {captura['url'][:150]}")
            payloads.append(captura["payload"])

        return payloads

    # ── Nivel Matching: cotejo contra el Slate oficial ──────────────────────
    @classmethod
    def extraer_cuotas_focalizadas(cls, partidos_slate: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """[LN-QBE-007-B] Mapea los eventos del feed contra el Slate oficial de la jornada."""
        resultados: List[Dict[str, Any]] = []
        payloads = cls._interceptar_feed()

        if not payloads:
            print("⚠️ [NOVIBET] No se obtuvieron payloads del feed para cotejar.")
            return resultados

        crudos: List[Dict[str, Any]] = []
        for payload in payloads:
            crudos.extend(cls.parse_feed_json(payload))

        print(f"🧮 [NOVIBET] [PARSING] Eventos crudos con 1X2 decimal completo: {len(crudos)}")
        for item in crudos:
            print(
                f"   • {item['local_raw']} vs {item['visitante_raw']} @ "
                f"{item['L']:.2f}/{item['E']:.2f}/{item['V']:.2f} | "
                f"+PA(+2 goles): {item['pago_anticipado']} | {item.get('jornada')} | "
                f"srId={item.get('sportradar_match_id')}"
            )

        for item in crudos:
            loc_raw = _clave_cotejo(canonicalize_team_name(item["local_raw"]) or item["local_raw"])
            vis_raw = _clave_cotejo(canonicalize_team_name(item["visitante_raw"]) or item["visitante_raw"])

            match_encontrado = None
            for entrada in partidos_slate:
                loc_slate = _clave_cotejo(canonicalize_team_name(entrada.get("local", "")) or entrada.get("local", ""))
                vis_slate = _clave_cotejo(canonicalize_team_name(entrada.get("visitante", "")) or entrada.get("visitante", ""))
                if not (loc_raw and vis_raw and loc_slate and vis_slate):
                    continue
                if (loc_raw in loc_slate or loc_slate in loc_raw) and (vis_raw in vis_slate or vis_slate in vis_raw):
                    match_encontrado = entrada
                    break

            if not match_encontrado:
                print(f"   ⚠️ [MATCH DESCARTADO] '{item['local_raw']}' vs '{item['visitante_raw']}' -> fuera del Slate oficial")
                continue

            l_val = float(item["L"])
            e_val = float(item["E"])
            v_val = float(item["V"])
            overround = ((1.0 / l_val) + (1.0 / e_val) + (1.0 / v_val) - 1.0) * 100.0

            resultados.append({
                "local": match_encontrado["local"],
                "visitante": match_encontrado["visitante"],
                "L": l_val,
                "E": e_val,
                "V": v_val,
                "pago_anticipado": bool(item["pago_anticipado"]),
                "overround": round(overround, 2),
                "es_viable": 0.0 < overround <= 30.0,
                "sportradar_match_id": item.get("sportradar_match_id"),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            print(f"  ✅ [NOVIBET MATCH OK] {match_encontrado['local']} vs {match_encontrado['visitante']} -> {l_val:.2f}/{e_val:.2f}/{v_val:.2f} (+PA: {item['pago_anticipado']})")

        print(f"📊 [NOVIBET] Resumen de Cotejo: {len(resultados)}/{len(partidos_slate)} vinculados al Slate.")
        return resultados

