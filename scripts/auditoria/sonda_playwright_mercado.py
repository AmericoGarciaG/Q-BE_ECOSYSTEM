# -*- coding: utf-8 -*-
"""Sonda E2 — DOM real de los tres operadores de mercado con Chromium headless.

Solo lectura: navega, cuenta selectores y guarda HTML en `.bt_run/sonda_centinelas/`.
No escribe en `src/`, no toca la base de datos ni `.env`.
"""

from __future__ import annotations

import time
import traceback
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SALIDA = RAIZ / ".bt_run" / "sonda_centinelas"
SALIDA.mkdir(parents=True, exist_ok=True)

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36"
)
SEL_CALIENTE = ".coupon-row, .event-table tr, .coupon-event, tr.mkt, div.event-card, .event-row"
SEL_NOVIBET = "sb-market-bet-item, [class*='marketDisplay_row']"

SITIOS = (
    ("caliente_vieja", "https://sports.caliente.mx/es_MX/F%C3%BAtbol-Mexicano", SEL_CALIENTE, 8000),
    ("caliente_nueva", "https://sports.caliente.mx/es_MX/Futbol", SEL_CALIENTE, 8000),
    ("betway", "https://betway.mx/mx/es-mx/sports/grp/soccer/mexico/liga-mx?tab=matches", None, 4000),
    ("novibet", "https://www.novibet.mx/apuestas-deportivas/futbol/mexico/liga-mx", SEL_NOVIBET, 20000),
)


def main() -> int:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        navegador = pw.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--ignore-certificate-errors",
            ],
        )
        print(f"chromium {navegador.version}")
        try:
            for nombre, url, selector, espera in SITIOS:
                print("\n" + "=" * 78)
                print(f"{nombre} · {url}")
                contexto = navegador.new_context(
                    user_agent=UA,
                    viewport={"width": 1440, "height": 900},
                    locale="es-MX",
                    timezone_id="America/Mexico_City",
                )
                pagina = contexto.new_page()
                inicio = time.perf_counter()
                try:
                    respuesta = pagina.goto(url, timeout=40000, wait_until="domcontentloaded")
                    pagina.wait_for_timeout(4000)
                    if selector:
                        try:
                            pagina.wait_for_selector(selector, timeout=espera)
                        except Exception as error:
                            print(f"  wait_for_selector({selector}): {type(error).__name__}")
                    print(f"  status: {respuesta.status if respuesta else 'N/D'}")
                    print(f"  url-final: {pagina.url}")
                    print(f"  title: {pagina.title()!r}")
                    print(f"  elapsed: {time.perf_counter() - inicio:.2f}s")
                    html = pagina.content()
                    print(f"  html.bytes: {len(html)}")
                    if selector:
                        print(f"  selector.count: {pagina.locator(selector).count()}")
                    texto = pagina.inner_text("body")
                    print(f"  body.text[:500]: {texto[:500]!r}")
                    for token in ("Liga MX", "América", "Tigres", "Monterrey", "Guadalajara", "ERROR 404", "Just a moment"):
                        print(f"    token {token!r}: {texto.lower().count(token.lower())}")
                    (SALIDA / f"{nombre}.html").write_text(html, encoding="utf-8", errors="replace")
                    print(f"  [evidencia] {SALIDA / (nombre + '.html')}")
                except Exception:
                    print(f"  EXCEPCIÓN tras {time.perf_counter() - inicio:.2f}s")
                    print(traceback.format_exc())
                    try:
                        (SALIDA / f"{nombre}_error.html").write_text(
                            pagina.content(), encoding="utf-8", errors="replace"
                        )
                    except Exception:
                        pass
                finally:
                    contexto.close()
        finally:
            navegador.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
