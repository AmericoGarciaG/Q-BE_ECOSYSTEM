# -*- coding: utf-8 -*-
"""
Q-BE Casino Deportes — Betway Market Scraper (src/ingestion/betway_scraper.py)
[LN-QBE-007-B, C, D, E] & [ARCH-1.4.6-C]
Sensor de Ingesta, Normalizador de Cuotas y Control de Errores Ruidoso para Betway.mx.
"""

import sys
import re
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from src.ingestion.normalizer import canonicalize_team_name

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

logger = logging.getLogger("BetwayScraper")

BETWAY_LIGA_MX_URL = "https://betway.mx/mx/es-mx/sports/grp/soccer/mexico/liga-mx?tab=matches"

# Tokens de UI que jamás deben confundirse con nombres de clubes
UI_BLACKLIST = {
    "inicio", "en vivo", "casino", "registrarse", "iniciar sesión", "liga mx",
    "fútbol, méxico", "partidos", "futuros", "próximos partidos", "1-x-2",
    "mañana", "hoy", "sábado", "domingo", "viernes", "jueves", "miércoles", "martes", "lunes",
    "local", "empate", "visitante", "mejorado", "más apuestas", "apuestas", "cuotas"
}


class BetwayMarketScraper:
    """Sensor de Ingesta Focalizado para Betway.mx con Control de Errores y Telemetría."""

    @staticmethod
    def american_to_decimal(val_str: str) -> float:
        """Convierte cuotas americanas (+230, -150) o decimales (3.30) a float decimal."""
        if not val_str:
            return 0.0
        txt = str(val_str).strip().replace(" ", "")
        
        # Si ya viene en formato decimal
        try:
            val_flt = float(txt)
            if "." in txt and val_flt > 1.0:
                return round(val_flt, 2)
        except ValueError:
            pass

        # Formato Americano con signo
        try:
            if txt.startswith("+"):
                num = float(txt[1:])
                return round(1.0 + (num / 100.0), 2)
            elif txt.startswith("-"):
                num = float(txt[1:])
                if num > 0:
                    return round(1.0 + (100.0 / num), 2)
            elif txt.isdigit():
                num = float(txt)
                if num >= 100:  # Ej. 150 sin signo suele ser +150
                    return round(1.0 + (num / 100.0), 2)
        except Exception:
            pass

        return 0.0

    @classmethod
    def _extraer_html_mercado(cls, url: Optional[str] = None) -> List[Dict[str, Any]]:
        """Extrae los eventos deportivos de Betway con telemetría de red y DOM."""
        target_url = url or BETWAY_LIGA_MX_URL
        resultados = []

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("[BETWAY] [ERROR] Playwright no está instalado.")
            print("❌ [BETWAY] Playwright no disponible en el entorno.")
            return resultados

        try:
            with sync_playwright() as pw:
                args = [
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-infobars",
                    "--ignore-certificate-errors",
                ]
                browser = pw.chromium.launch(headless=True, args=args)
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1366, "height": 768},
                    locale="es-MX",
                    timezone_id="America/Mexico_City",
                )
                page = context.new_page()
                page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

                try:
                    response = page.goto(target_url, timeout=35000, wait_until="domcontentloaded")
                    status_code = response.status if response else 0
                    print(f"📡 [BETWAY] Conexión HTTP: {status_code} | URL: {page.url[:65]}...")

                    if status_code != 200:
                        logger.warning(f"[BETWAY] [ALERTA] Respuesta HTTP no óptima: {status_code}")
                        return resultados

                    page.wait_for_timeout(4000)

                    # [ARCH-1.6.17] Despliegue elástico de acordeones de fecha (relativos y calendario)
                    page.evaluate("""() => {
                        const elementos = Array.from(document.querySelectorAll('div, button, span'));
                        const tokensFecha = ['domingo', 'sábado', 'sabado', 'lunes', 'viernes', 'oct', 'nov', 'próximos', 'jornada'];
                        for (let el of elementos) {
                            const t = el.textContent ? el.textContent.trim().toLowerCase() : '';
                            const esAriaClosed = el.getAttribute('aria-expanded') === 'false';
                            const esFechaToken = tokensFecha.some(tok => t.includes(tok)) && el.children.length <= 2;
                            if (esAriaClosed || esFechaToken) {
                                try { el.click(); } catch(e) {}
                            }
                        }
                    }""")
                    page.wait_for_timeout(2500)

                    # Scroll suave para forzar la renderización de los partidos recién desplegados
                    page.mouse.wheel(0, 1200)
                    page.wait_for_timeout(1500)
                    page.evaluate("window.scrollTo(0, 0)")
                    page.wait_for_timeout(1000)

                    body_text = page.inner_text("body")
                    lines = [line.strip() for line in body_text.splitlines() if line.strip()]
                    print(f"📄 [BETWAY] DOM cargado tras expandir acordeones: {len(lines)} líneas de texto.")

                    # Parseador secuencial inteligente por bloques de partido
                    i = 0
                    while i < len(lines) - 4:
                        token_1 = lines[i]
                        token_2 = lines[i+1]

                        # Validar si son nombres de equipo (no están en lista negra y tienen longitud adecuada)
                        if (token_1.lower() not in UI_BLACKLIST and 
                            token_2.lower() not in UI_BLACKLIST and 
                            len(token_1) >= 3 and len(token_2) >= 3 and
                            not re.match(r'^[\+\-\d\:\.]+$', token_1) and
                            not re.match(r'^[\+\-\d\:\.]+$', token_2)):

                            # Buscar las 3 cuotas subsecuentes en las siguientes 6 líneas
                            odds_candidatas = []
                            offset = 2
                            while offset <= 7 and (i + offset) < len(lines):
                                t_odd = lines[i + offset]
                                dec = cls.american_to_decimal(t_odd)
                                if dec > 1.05 and dec < 50.0:
                                    odds_candidatas.append(dec)
                                    if len(odds_candidatas) == 3:
                                        break
                                elif t_odd.lower() in UI_BLACKLIST:
                                    pass  # saltar etiquetas secundarias
                                offset += 1

                            if len(odds_candidatas) == 3:
                                resultados.append({
                                    "local_raw": token_1,
                                    "visitante_raw": token_2,
                                    "L": odds_candidatas[0],
                                    "E": odds_candidatas[1],
                                    "V": odds_candidatas[2],
                                    "pago_anticipado": False
                                })
                                i += offset  # Avanzar al siguiente bloque
                                continue

                        i += 1

                    print(f"🎯 [BETWAY] Eventos válidos identificados en DOM: {len(resultados)}")

                finally:
                    browser.close()

        except Exception as e:
            logger.error(f"[BETWAY] [ERROR CRÍTICO] Fallo durante navegación: {e}")
            print(f"❌ [BETWAY] Excepción de scraping: {e}")

        return resultados

    @classmethod
    def extraer_cuotas_focalizadas(cls, partidos_slate: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Mapea los eventos extraídos de Betway contra el Slate oficial con telemetría."""
        raw_items = cls._extraer_html_mercado()
        resultados: List[Dict[str, Any]] = []

        if not raw_items:
            print("⚠️ [BETWAY] No se obtuvieron eventos en crudo para cotejar.")
            return resultados

        def _clean_team_str(txt: str) -> str:
            if not txt:
                return ""
            import unicodedata
            nfkd = unicodedata.normalize('NFKD', txt)
            s = "".join([c for c in nfkd if not unicodedata.combining(c)]).lower()
            for token in ["de guadalajara", "guadalajara", "xolos", "fc", "club", "deportivo", "atletico", "unam"]:
                s = s.replace(token, " ")
            return " ".join(s.split()).strip()

        # Mapa de búsqueda con alias flexibles
        slate_list = []
        for match in partidos_slate:
            loc_orig = match.get("local", "")
            vis_orig = match.get("visitante", "")
            loc_can = canonicalize_team_name(loc_orig)
            vis_can = canonicalize_team_name(vis_orig)
            slate_list.append({
                "match": match,
                "loc_can": loc_can,
                "vis_can": vis_can,
                "loc_clean": _clean_team_str(loc_can or loc_orig),
                "vis_clean": _clean_team_str(vis_can or vis_orig),
            })

        for item in raw_items:
            loc_raw = item.get("local_raw", "")
            vis_raw = item.get("visitante_raw", "")

            loc_raw_clean = _clean_team_str(canonicalize_team_name(loc_raw) or loc_raw)
            vis_raw_clean = _clean_team_str(canonicalize_team_name(vis_raw) or vis_raw)

            # Búsqueda difusa o exacta en el slate
            match_encontrado = None
            for s_entry in slate_list:
                s_loc_clean = s_entry["loc_clean"]
                s_vis_clean = s_entry["vis_clean"]

                loc_match = (loc_raw_clean in s_loc_clean or s_loc_clean in loc_raw_clean)
                vis_match = (vis_raw_clean in s_vis_clean or s_vis_clean in vis_raw_clean)

                if loc_match and vis_match:
                    match_encontrado = s_entry["match"]
                    break

            if match_encontrado:
                l_val = float(item["L"])
                e_val = float(item["E"])
                v_val = float(item["V"])
                overround = ((1.0 / l_val) + (1.0 / e_val) + (1.0 / v_val) - 1.0) * 100.0

                res_obj = {
                    "local": match_encontrado["local"],
                    "visitante": match_encontrado["visitante"],
                    "L": l_val,
                    "E": e_val,
                    "V": v_val,
                    "pago_anticipado": False,
                    "overround": round(overround, 2),
                    "es_viable": 0.0 < overround <= 30.0,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                resultados.append(res_obj)
                print(f"  ✅ [BETWAY MATCH] {match_encontrado['local']} vs {match_encontrado['visitante']} -> {l_val:.2f}/{e_val:.2f}/{v_val:.2f}")
            else:
                logger.debug(f"[BETWAY] [IGNORADO] No coincide con slate: '{loc_raw}' vs '{vis_raw}'")

        print(f"📊 [BETWAY] Resumen de Cotejo: {len(resultados)}/{len(partidos_slate)} vinculados al Slate.")
        return resultados
