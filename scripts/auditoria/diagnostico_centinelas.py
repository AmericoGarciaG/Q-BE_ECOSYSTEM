# -*- coding: utf-8 -*-
"""SONDA FORENSE FASE 0 — RESCATE DE CENTINELAS (`[ARCH-1.4.12]` / `[ARCH-1.4.59]`).

Solo lectura. No escribe en `src/`, no modifica bases de datos y no toca `.env`.
Los artefactos de evidencia (HTML/JSON crudos) se depositan en
`.bt_run/sonda_centinelas/` para auditoría del Director.

Estaciones:
  E1 — Entorno y red (Playwright/Chromium + httpx a FotMob y Caliente).
  E2 — Extracción (presencia de `script#__NEXT_DATA__` y selectores de cupón).
  E3 — Persistencia (SQLite read-only: integridad, tablas, frescura y WAL).
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SALIDA = RAIZ / ".bt_run" / "sonda_centinelas"
SALIDA.mkdir(parents=True, exist_ok=True)

URL_FOTMOB = "https://www.fotmob.com/api/data/leagues?id=230&tab=stats"
URL_FOTMOB_WEB = "https://www.fotmob.com/"
URL_CALIENTE = "https://sports.caliente.mx/es_MX/F%C3%BAtbol-Mexicano"
SEL_CALIENTE = ".coupon-row, .event-table tr, .coupon-event, tr.mkt, div.event-card, .event-row"

CABECERAS_FOTMOB = {
    "User-Agent": "Mozilla/5.0 (compatible; Q-BE-CentinelaMacro/1.0; +https://qbe.local)",
    "Accept": "application/json, text/plain, */*",
}
CABECERAS_NAVEGADOR = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
}


def seccion(titulo: str) -> None:
    print("\n" + "=" * 78)
    print(titulo)
    print("=" * 78)


def ahora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def edad_dias(marca: float) -> float:
    return (time.time() - marca) / 86400.0


def guardar(nombre: str, contenido: str) -> None:
    (SALIDA / nombre).write_text(contenido, encoding="utf-8", errors="replace")
    print(f"  [evidencia] {SALIDA / nombre} ({len(contenido)} bytes)")


# ─────────────────────────────────────────────────────────────────────────────
# E1 — Entorno y red
# ─────────────────────────────────────────────────────────────────────────────
def e1_entorno() -> None:
    seccion("E1.1 — ENTORNO PYTHON / PLAYWRIGHT")
    print(f"python: {sys.version}")
    print(f"executable: {sys.executable}")
    try:
        import playwright
        from playwright._impl._driver import compute_driver_executable

        print(f"playwright: {getattr(playwright, '__version__', 'desconocida')}")
        try:
            print(f"driver: {compute_driver_executable()}")
        except Exception:
            pass
    except Exception:
        print("playwright: NO IMPORTABLE")
        print(traceback.format_exc())

    from playwright.sync_api import sync_playwright

    try:
        with sync_playwright() as p:
            for nombre in ("chromium", "firefox", "webkit"):
                navegador = getattr(p, nombre)
                try:
                    print(f"{nombre}.executable_path: {navegador.executable_path}")
                    print(f"{nombre}.existe: {Path(navegador.executable_path).is_file()}")
                except Exception as error:
                    print(f"{nombre}.executable_path: ERROR {error}")
    except Exception:
        print("PLAYWRIGHT DRIVER: NO ARRANCÓ (ver traceback)")
        print(traceback.format_exc())


def e1_http() -> None:
    seccion("E1.2 — HTTP DIRECTO (httpx) — FOTMOB API Y CALIENTE")
    import httpx

    for etiqueta, url, cabeceras in (
        ("fotmob-api", URL_FOTMOB, CABECERAS_FOTMOB),
        ("caliente-html", URL_CALIENTE, CABECERAS_NAVEGADOR),
    ):
        print(f"\n[{etiqueta}] GET {url}")
        inicio = time.perf_counter()
        try:
            with httpx.Client(headers=cabeceras, timeout=40.0, follow_redirects=True) as cliente:
                respuesta = cliente.get(url)
            duracion = time.perf_counter() - inicio
            print(f"  status: {respuesta.status_code}")
            print(f"  elapsed: {duracion:.2f}s")
            print(f"  content-type: {respuesta.headers.get('content-type')}")
            print(f"  server: {respuesta.headers.get('server')}")
            print(f"  cf-ray: {respuesta.headers.get('cf-ray')}")
            print(f"  bytes: {len(respuesta.content)}")
            print(f"  url-final: {respuesta.url}")
            if etiqueta == "fotmob-api":
                try:
                    cuerpo = respuesta.json()
                    print(f"  json.type: {type(cuerpo).__name__}")
                    print(f"  json.keys: {list(cuerpo)[:15]}")
                    guardar("fotmob_api.json", json.dumps(cuerpo, ensure_ascii=False)[:200000])
                except Exception as error:
                    print(f"  json: NO DECODIFICABLE ({error})")
                    print(f"  body[:400]: {respuesta.text[:400]!r}")
                    guardar("fotmob_api.txt", respuesta.text[:200000])
            else:
                print(f"  title: {respuesta.text.split('<title>')[1].split('</title>')[0][:120] if '<title>' in respuesta.text else 'N/D'}")
                print(f"  selectores presentes: {resetear_selector(respuesta.text)}")
                guardar("caliente_http.html", respuesta.text[:500000])
        except Exception:
            print(f"  EXCEPCIÓN tras {time.perf_counter() - inicio:.2f}s")
            print(traceback.format_exc())


def resetear_selector(html: str) -> dict:
    import re

    patrones = {
        "coupon-row": r'class="[^"]*coupon-row',
        "event-table": r'class="[^"]*event-table',
        "coupon-event": r'class="[^"]*coupon-event',
        "event-card": r'class="[^"]*event-card',
        "event-row": r'class="[^"]*event-row',
        "captcha": r"captcha|challenge-platform|cf-chl",
    }
    return {clave: len(re.findall(patron, html, flags=re.IGNORECASE)) for clave, patron in patrones.items()}


def e1_navegador() -> None:
    seccion("E1.3 — NAVEGADOR HEADLESS (Playwright/Chromium)")
    from playwright.sync_api import sync_playwright

    try:
        contexto_manager = sync_playwright()
        p = contexto_manager.__enter__()
    except Exception:
        print("PLAYWRIGHT: NO SE PUDO INICIAR EL DRIVER:")
        print(traceback.format_exc())
        return

    try:
        try:
            navegador = p.chromium.launch(headless=True, timeout=30000)
            print(f"chromium lanzado: {navegador.version}")
        except Exception:
            print("FALLO AL LANZAR CHROMIUM:")
            print(traceback.format_exc())
            return

        try:
            for etiqueta, url in (("fotmob", URL_FOTMOB_WEB), ("caliente", URL_CALIENTE)):
                print(f"\n[{etiqueta}] goto {url}")
                contexto = navegador.new_context(
                    locale="es-MX",
                    user_agent=CABECERAS_NAVEGADOR["User-Agent"],
                    viewport={"width": 1440, "height": 900},
                )
                pagina = contexto.new_page()
                inicio = time.perf_counter()
                try:
                    respuesta = pagina.goto(url, timeout=30000, wait_until="domcontentloaded")
                    pagina.wait_for_timeout(3000)
                    html = pagina.content()
                    print(f"  status: {respuesta.status if respuesta else 'N/D'}")
                    print(f"  url-final: {pagina.url}")
                    print(f"  title: {pagina.title()!r}")
                    print(f"  elapsed: {time.perf_counter() - inicio:.2f}s")
                    print(f"  html.bytes: {len(html)}")
                    if etiqueta == "fotmob":
                        print(f"  __NEXT_DATA__: {pagina.locator('script#__NEXT_DATA__').count()}")
                        print(f"  react-root: {pagina.locator('#__next, [data-reactroot]').count()}")
                        guardar("fotmob_web.html", html[:500000])
                    else:
                        print(f"  selector-cupones: {pagina.locator(SEL_CALIENTE).count()}")
                        print(f"  body.text[:300]: {pagina.inner_text('body')[:300]!r}")
                        guardar("caliente_web.html", html[:500000])
                except Exception:
                    print(f"  EXCEPCIÓN tras {time.perf_counter() - inicio:.2f}s")
                    print(traceback.format_exc())
                    try:
                        guardar(f"{etiqueta}_error.html", pagina.content()[:500000])
                    except Exception:
                        pass
                finally:
                    contexto.close()
        finally:
            navegador.close()
    finally:
        try:
            contexto_manager.__exit__(None, None, None)
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# E3 — Persistencia
# ─────────────────────────────────────────────────────────────────────────────
def _columnas(con: sqlite3.Connection, tabla: str) -> list:
    return [fila[1] for fila in con.execute(f'PRAGMA table_info("{tabla}")')]


def _marca_temporal(con: sqlite3.Connection, tabla: str) -> str:
    columnas = _columnas(con, tabla)
    for candidata in ("updated_at", "timestamp", "created_at", "cargado_utc", "generado_at", "fecha"):
        if candidata in columnas:
            try:
                fila = con.execute(f'SELECT MAX("{candidata}") FROM "{tabla}"').fetchone()
                return f"{candidata}={fila[0] if fila else None}"
            except Exception as error:
                return f"{candidata}=ERROR({error})"
    return "sin columna temporal"


def e3_base(ruta: Path) -> None:
    print(f"\n[{ruta}]")
    if not ruta.exists():
        print("  NO EXISTE")
        return
    wal = Path(str(ruta) + "-wal")
    shm = Path(str(ruta) + "-shm")
    journal = Path(str(ruta) + "-journal")
    print(f"  db.bytes: {ruta.stat().st_size}")
    print(f"  wal.bytes: {wal.stat().st_size if wal.exists() else 'AUSENTE'}")
    print(f"  shm.bytes: {shm.stat().st_size if shm.exists() else 'AUSENTE'}")
    print(f"  journal: {journal.stat().st_size if journal.exists() else 'AUSENTE'}")
    print(f"  db.mtime: {datetime.fromtimestamp(ruta.stat().st_mtime).isoformat()}")

    con = sqlite3.connect(f"file:{ruta.as_posix()}?mode=ro", uri=True, timeout=1.0)
    try:
        print(f"  quick_check: {con.execute('PRAGMA quick_check').fetchall()}")
        print(f"  journal_mode: {con.execute('PRAGMA journal_mode').fetchall()}")
        print(f"  page_count: {con.execute('PRAGMA page_count').fetchone()[0]}")
        print(f"  freelist_count: {con.execute('PRAGMA freelist_count').fetchone()[0]}")
        tablas = [fila[0] for fila in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )]
        print(f"  tablas ({len(tablas)}): {tablas}")
        for tabla in tablas:
            try:
                total = con.execute(f'SELECT COUNT(*) FROM "{tabla}"').fetchone()[0]
                print(f"    {tabla}: {total} filas | {_marca_temporal(con, tabla)}")
            except Exception as error:
                print(f"    {tabla}: ERROR {error}")
        for tabla in ("fixture_snapshots", "matches", "odds_ticks", "slates"):
            if tabla not in tablas:
                print(f"  [ausente] tabla {tabla}")
        if "fixture_snapshots" in tablas:
            columnas = _columnas(con, "fixture_snapshots")
            print(f"  fixture_snapshots.columns: {columnas}")
            try:
                filas = con.execute(
                    'SELECT matchday, updated_at, length(matches_json) '
                    'FROM fixture_snapshots ORDER BY updated_at DESC LIMIT 3'
                ).fetchall()
                print(f"  fixture_snapshots.ultimas: {filas}")
                if filas:
                    crudo = con.execute(
                        'SELECT matches_json FROM fixture_snapshots ORDER BY updated_at DESC LIMIT 1'
                    ).fetchone()[0]
                    data = json.loads(crudo)
                    print(f"  ultimo snapshot: {len(data)} partidos")
                    con_momios = sum(1 for p in data if p.get("momios_operadores"))
                    print(f"  con momios_operadores: {con_momios}")
                    if data:
                        print(f"  ejemplo.momios_operadores: {json.dumps(data[0].get('momios_operadores'), ensure_ascii=False)[:500]}")
            except Exception as error:
                print(f"  fixture_snapshots.inspeccion: ERROR {error}")
    finally:
        con.close()


def e3_persistencia() -> None:
    seccion("E3 — PERSISTENCIA SQLITE (READ-ONLY)")
    for ruta in (RAIZ / "data" / "qbe_database.db", RAIZ / "qbe_observatory" / "data" / "qbe_historico.db"):
        try:
            e3_base(ruta)
        except Exception:
            print(f"ERROR auditando {ruta}:")
            print(traceback.format_exc())

    print("\n[artefacto macro FotMob]")
    cache = RAIZ / "data" / "cache_macro_stats_liga_mx_2026.json"
    if cache.exists():
        stat = cache.stat()
        print(f"  ruta: {cache}")
        print(f"  bytes: {stat.st_size}")
        print(f"  mtime: {datetime.fromtimestamp(stat.st_mtime).isoformat()}")
        print(f"  edad_dias: {edad_dias(stat.st_mtime):.2f}")
        try:
            cuerpo = json.loads(cache.read_text(encoding="utf-8"))
            print(f"  generado_at: {cuerpo.get('generado_at')}")
            print(f"  equipos: {len(cuerpo.get('equipos') or {})}")
            print(f"  errores: {cuerpo.get('errores')}")
            print(f"  huecos: {len(cuerpo.get('huecos') or [])}")
        except Exception:
            print(traceback.format_exc())
    else:
        print("  NO EXISTE")


def e4_logs() -> None:
    seccion("E4 — RASTRO EN LOGS")
    import re

    patron = re.compile(
        r"database is locked|timeout|timed out|403|401|429|cloudflare|ERR_|SSL|certificate|Traceback|ERROR|CRITICAL",
        re.IGNORECASE,
    )
    candidatos = []
    for carpeta in (RAIZ / ".bt_run" / "lanzador", RAIZ / "qbe_ingestion" / "data" / "reportes"):
        if carpeta.exists():
            candidatos.extend(sorted(carpeta.rglob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)[:8])
    for ruta in candidatos:
        try:
            lineas = ruta.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            continue
        hits = [(indice + 1, linea) for indice, linea in enumerate(lineas) if patron.search(linea)]
        if not hits:
            continue
        print(f"\n[{ruta.relative_to(RAIZ)}] mtime={datetime.fromtimestamp(ruta.stat().st_mtime).isoformat()} hits={len(hits)}")
        for numero, linea in hits[-5:]:
            print(f"  L{numero}: {linea[:220]}")


def main() -> int:
    print("SONDA FORENSE — CENTINELAS SPRINT-46")
    print(f"inicio: {ahora_iso()}")
    for estacion in (e1_entorno, e1_http, e1_navegador, e3_persistencia, e4_logs):
        try:
            estacion()
        except Exception:
            print(f"\n[ESTACIÓN {estacion.__name__}] ERROR NO CONTROLADO:")
            print(traceback.format_exc())
    print(f"\nfin: {ahora_iso()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
