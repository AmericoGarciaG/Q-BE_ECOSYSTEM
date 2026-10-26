# Q-BE Casino Deportes — Caliente Market Scraper (src/ingestion/caliente_scraper.py)
"""
[ARCH-PILLAR] Sensor de Mercado e Ingesta: Caliente.mx Scraper & Normalizador.
[GOVERNANCE-01] Extracción resiliente de cuotas 1X2 y banderas de Pago Anticipado
con Playwright Stealth y BeautifulSoup. Cero generación de equipos sintéticos.
"""

import re
import json
import logging
from typing import List, Dict, Any, Optional, Tuple

from src.ingestion.normalizer import canonicalize_team_name

logger = logging.getLogger(__name__)

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None


class CalienteMarketScraper:
    """
    Sensor de Ingesta y Normalizador de Cuotas Caliente.mx.
    Soporta Playwright Stealth (headless / headed), BeautifulSoup y payloads JSON/texto.
    """

    @staticmethod
    def iniciar_navegador_stealth(pw, headed: bool = False):
        """
        Inicializa una sesión de Chromium con banderas stealth para evadir
        detección de bots y Cloudflare.
        """
        args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-infobars",
            "--window-position=0,0",
            "--ignore-certificate-errors",
        ]
        browser = pw.chromium.launch(headless=not headed, args=args)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1366, "height": 768},
            locale="es-MX",
            timezone_id="America/Mexico_City"
        )
        page = context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return browser, context, page

    @classmethod
    def scrape_url(cls, url: str, headed: bool = False) -> Tuple[List[Dict[str, Any]], str]:
        """
        Navega a la URL con Playwright Stealth y extrae partidos de forma resiliente con BeautifulSoup.
        Retorna (lista_de_partidos_normalizados, texto_crudo_extraido).
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            print("⚠️ Playwright no está instalado. Instala con: pip install playwright && playwright install chromium")
            return [], ""

        partidos = []
        raw_text = ""
        html_content = ""

        try:
            with sync_playwright() as pw:
                browser, context, page = cls.iniciar_navegador_stealth(pw, headed=headed)
                try:
                    page.goto(url, timeout=20_000, wait_until="domcontentloaded")
                    page.wait_for_load_state("domcontentloaded")
                    page.wait_for_timeout(3000)

                    try:
                        page.wait_for_selector(
                            ".coupon-row, .event-table, .coupon-event, table, tbody tr",
                            timeout=8000
                        )
                    except Exception:
                        pass

                    html_content = page.content()
                    raw_text = page.inner_text("body")

                finally:
                    browser.close()

        except Exception as e:
            print(f"⚠️ Error durante scraping Playwright Stealth: {e}")
            return [], ""

        if html_content:
            partidos = cls.parse_html_soup(html_content)

        if not partidos and raw_text:
            partidos = cls.parse_raw_text_or_json(raw_text)

        return partidos, raw_text

    @classmethod
    def parse_html_soup(cls, html: str) -> List[Dict[str, Any]]:
        """
        Extrae partidos estructurados desde el HTML de Caliente.mx usando BeautifulSoup.
        Descarta filas sin nombres de equipos legítimos (cero equipos sintéticos).
        """
        if BeautifulSoup is None:
            return []

        soup = BeautifulSoup(html, "html.parser")
        partidos = []
        pa_global = "pago anticipado" in html.lower()

        filas = soup.select(".coupon-row, .event-table tr, .coupon-event, tr.mkt, div.event-card, .event-row")
        if not filas:
            filas = soup.find_all("tr")

        seen_pairs = set()

        for idx, fila in enumerate(filas, 1):
            texto_fila = fila.get_text(separator=" ", strip=True)
            if not texto_fila or len(texto_fila) < 8:
                continue

            nums = re.findall(r"\b\d+\.\d{2}\b", texto_fila)
            if len(nums) >= 3:
                l, e, v = float(nums[0]), float(nums[1]), float(nums[2])
                pa = pa_global or bool(re.search(r"\b(pa|pago\s*anticipado)\b", texto_fila, re.IGNORECASE))

                partido_match = re.search(
                    r"([A-Za-zÁÉÍÓÚáéíóúÑñ\s\.\-]{3,35})\s+(?:vs\.?|contra|-|\n)\s+([A-Za-zÁÉÍÓÚáéíóúÑñ\s\.\-]{3,35})",
                    texto_fila
                )
                if partido_match:
                    local = partido_match.group(1).strip()
                    vis = partido_match.group(2).strip()
                else:
                    teams = fila.select(".participant, .team-name, .opp-name, .event-name")
                    if len(teams) >= 2:
                        local = teams[0].get_text(strip=True)
                        vis = teams[1].get_text(strip=True)
                    else:
                        # [GOVERNANCE-01] Prohibición de inventar Equipo L1 / Equipo V1
                        continue

                local = canonicalize_team_name(local)
                vis = canonicalize_team_name(vis)

                if not local or not vis or local.lower() == vis.lower():
                    continue

                par_key = f"{local.lower()}_vs_{vis.lower()}"
                if par_key in seen_pairs:
                    continue
                seen_pairs.add(par_key)

                partidos.append({
                    "id_partido": f"CALIENTE-{len(partidos)+1:02d}",
                    "local": local,
                    "visitante": vis,
                    "momios": {"L": l, "E": e, "V": v},
                    "pago_anticipado": pa
                })

        return partidos

    @staticmethod
    def parse_raw_text_or_json(raw_input: str) -> List[Dict[str, Any]]:
        """
        Interpreta un payload de entrada en formato JSON, OCR o texto de cuotas,
        extrayendo la lista de partidos con sus momios 1X2 y bandera de Pago Anticipado.
        """
        raw_input = raw_input.strip()
        if not raw_input:
            return []

        try:
            parsed = json.loads(raw_input)
            if isinstance(parsed, list):
                return CalienteMarketScraper.normalize_matches(parsed)
            elif isinstance(parsed, dict):
                partidos = parsed.get(
                    "partidos",
                    parsed.get("partidos_slate", parsed.get("partidos_raw", parsed.get("matches", [parsed])))
                )
                if isinstance(partidos, list):
                    return CalienteMarketScraper.normalize_matches(partidos)
        except json.JSONDecodeError:
            pass

        matches = []
        lines = raw_input.splitlines()
        for idx, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            nums = re.findall(r"\b\d+\.\d{2}\b", line)
            if len(nums) >= 3:
                l, e, v = float(nums[0]), float(nums[1]), float(nums[2])
                pa = bool(re.search(r"\b(pa|pago\s*anticipado|si|true)\b", line, re.IGNORECASE))

                partido_match = re.search(
                    r"([A-Za-zÁÉÍÓÚáéíóúÑñ\s\.\-]+)\s+(?:vs\.?|contra|-)\s+([A-Za-zÁÉÍÓÚáéíóúÑñ\s\.\-]+)",
                    line
                )
                if partido_match:
                    local = canonicalize_team_name(partido_match.group(1).strip())
                    visitante = canonicalize_team_name(partido_match.group(2).strip())
                else:
                    # [GOVERNANCE-01] Descartar si no hay nombres válidos
                    continue

                if not local or not visitante:
                    continue

                id_partido = f"INGEST-{len(matches)+1:02d}"
                matches.append({
                    "id_partido": id_partido,
                    "local": local,
                    "visitante": visitante,
                    "momios": {"L": l, "E": e, "V": v},
                    "pago_anticipado": pa
                })

        return matches

    @staticmethod
    def normalize_matches(matches_raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normaliza una lista de diccionarios de partidos al esquema canónico para triage.py.
        """
        normalized = []
        for idx, m in enumerate(matches_raw, 1):
            id_p = m.get("id_partido", f"MATCH-{idx:02d}")
            local = canonicalize_team_name(m.get("local", m.get("equipo_local", m.get("team_home", ""))))
            vis = canonicalize_team_name(m.get("visitante", m.get("equipo_visitante", m.get("team_away", ""))))

            if not local or not vis:
                continue

            momios = m.get("momios", {})
            if isinstance(momios, dict) and "pago_anticipado" in momios and isinstance(momios["pago_anticipado"], dict):
                pa_dict = momios["pago_anticipado"]
                l = float(pa_dict.get("L", 0.0))
                e = float(pa_dict.get("E", 0.0))
                v = float(pa_dict.get("V", 0.0))
                pa = bool(pa_dict.get("disponible", True))
            elif isinstance(momios, dict) and ("L" in momios or "E" in momios or "V" in momios):
                l = float(momios.get("L", m.get("odd_l", m.get("cuota_local", 0.0))))
                e = float(momios.get("E", m.get("odd_e", m.get("cuota_empate", 0.0))))
                v = float(momios.get("V", m.get("odd_v", m.get("cuota_visita", 0.0))))
                pa = bool(m.get("pago_anticipado", m.get("pa", True)))
            else:
                l = float(m.get("odd_l", m.get("cuota_local", m.get("L", 0.0))))
                e = float(m.get("odd_e", m.get("cuota_empate", m.get("E", 0.0))))
                v = float(m.get("odd_v", m.get("cuota_visita", m.get("V", 0.0))))
                pa = bool(m.get("pago_anticipado", m.get("pa", True)))

            normalized.append({
                "id_partido": id_p,
                "local": local,
                "visitante": vis,
                "momios": {"L": l, "E": e, "V": v},
                "pago_anticipado": pa
            })

        return normalized

    @classmethod
    def extraer_cuotas_focalizadas(cls, partidos_slate: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        [FASE 2 SOBERANA]
        Navega a Caliente.mx y extrae momios 1X2 y Pago Anticipado ÚNICAMENTE para los
        partidos que coincidan con los pares (local, visitante) del Slate oficial de la liga.
        [GOVERNANCE-01] Cero equipos sintéticos: solo se retorna lo encontrado en el sitio real.
        """
        if not partidos_slate:
            return []

        partidos_a_buscar = {(p["local"], p["visitante"]): p for p in partidos_slate}
        mercado_encontrado = []
        url_caliente = "https://sports.caliente.mx/es_MX/F%C3%BAtbol-Mexicano"

        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as pw:
                browser, context, page = cls.iniciar_navegador_stealth(pw, headed=False)
                try:
                    page.goto(url_caliente, timeout=25000, wait_until="domcontentloaded")
                    page.wait_for_timeout(4000)

                    if "attention" in page.title().lower() or "cloudflare" in page.title().lower():
                        print("[CALIENTE] ⚠️ Bloqueo perimetral detectado.")
                        return []

                    html = page.content()
                    if BeautifulSoup:
                        soup = BeautifulSoup(html, "html.parser")

                        # 1. Detección global de Pago Anticipado en el contenedor/cabecera de la liga
                        texto_pagina = soup.get_text().lower()
                        tiene_pa_global = any(kw in texto_pagina for kw in [
                            "pago anticipado", "2 goles de ventaja", "pago anticipado activo", "adelanto 2 goles"
                        ])

                        # [ANTI-CONTAMINACION] Localizar filas individuales de mercado (tr específicos de evento)
                        filas = soup.find_all("tr", class_=lambda c: c and any(k in str(c).lower() for k in ["event", "coupon", "mkt"]))
                        if not filas:
                            filas = soup.find_all(lambda tag: tag.name in ["tr", "div"] and len(tag.find_all("td")) >= 3)

                        for fila in filas:
                            texto_fila = fila.get_text(" | ", strip=True)

                            for (l_target, v_target) in partidos_a_buscar.keys():
                                palabras_l = [w for w in l_target.lower().replace("club", "").replace("deportivo", "").split() if len(w) >= 4]
                                palabras_v = [w for w in v_target.lower().replace("club", "").replace("deportivo", "").split() if len(w) >= 4]

                                match_l = any(re.search(r'\b' + re.escape(w) + r'\b', texto_fila.lower()) for w in palabras_l)
                                match_v = any(re.search(r'\b' + re.escape(w) + r'\b', texto_fila.lower()) for w in palabras_v)

                                if match_l and match_v:
                                    # Descartar coincidencias cruzadas si la fila menciona clubes ajenos al partido
                                    partido_completo_str = (l_target + " " + v_target).lower()
                                    if "chivas" in texto_fila.lower() and "chivas" not in partido_completo_str:
                                        continue
                                    if "pachuca" in texto_fila.lower() and "pachuca" not in partido_completo_str:
                                        continue
                                    if "monterrey" in texto_fila.lower() and "monterrey" not in partido_completo_str:
                                        continue
                                    if "cruz azul" in texto_fila.lower() and "cruz azul" not in partido_completo_str:
                                        continue

                                    momios_raw = re.findall(r'\b\d+\.\d{2}\b', texto_fila)
                                    if len(momios_raw) >= 3:
                                        l_odd = float(momios_raw[0])
                                        e_odd = float(momios_raw[1])
                                        v_odd = float(momios_raw[2])
                                        overround = (1.0 / l_odd) + (1.0 / e_odd) + (1.0 / v_odd)

                                        if 1.00 <= overround <= 1.35:
                                            item = {
                                                "local": l_target,
                                                "visitante": v_target,
                                                "L": l_odd,
                                                "E": e_odd,
                                                "V": v_odd,
                                                "pago_anticipado": tiene_pa_global,
                                                "encontrado_en_caliente": True
                                            }
                                            if not any(m["local"] == l_target and m["visitante"] == v_target for m in mercado_encontrado):
                                                mercado_encontrado.append(item)
                finally:
                    browser.close()
        except Exception as e:
            logger.warning(f"[CALIENTE] Error en extraccion focalizada: {e}")

        # Rellenar con None los partidos no cotizados [GOVERNANCE-01: sin datos sintéticos]
        for (l_target, v_target) in partidos_a_buscar.keys():
            if not any(m["local"] == l_target and m["visitante"] == v_target for m in mercado_encontrado):
                mercado_encontrado.append({
                    "local": l_target,
                    "visitante": v_target,
                    "L": None, "E": None, "V": None,
                    "pago_anticipado": False,
                    "encontrado_en_caliente": False
                })

        return mercado_encontrado