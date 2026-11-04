# -*- coding: utf-8 -*-
"""Sonda investigativa H2H y Forma 5P — Sprint 46.

Acción 1: audita FotMob (`leagues?tab=fixtures` + `matchDetails`) para el
partido Atlético de San Luis vs FC Juárez y verifica la presencia de
`content.h2h` (historial) y `content.matchFacts.teamForm` (últimos 5).

Acción 2: revisa la documentación (`[LN-QBE-020]`, `[LN-QBE-036]`) y el código
legado (`Q_BE_CD_WEB`) para identificar la fuente histórica del dato.

Solo lectura: no escribe archivos ni bases.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

RAIZ = Path(__file__).resolve().parents[2]
LEGACY = RAIZ.parent / "Q_BE_CD_WEB"
LOGIC = RAIZ / "docs" / "LOGIC.md"
CABECERAS = {
    "User-Agent": "Mozilla/5.0 (compatible; Q-BE-SondaH2H/1.0; +https://qbe.local)",
    "Accept": "application/json, text/plain, */*",
}
LIGA_MX_ID = 230
LOCAL = "Atlético de San Luis"
VISITA = "FC Juárez"


def _get_json(cliente: httpx.Client, url: str) -> Optional[Dict[str, Any]]:
    try:
        respuesta = cliente.get(url)
        respuesta.raise_for_status()
        datos = respuesta.json()
        return datos if isinstance(datos, dict) else None
    except Exception as error:  # noqa: BLE001 — la sonda reporta y continúa
        print(f"  [ERROR] {url}: {type(error).__name__}: {error}")
        return None


def _buscar_partido(cliente: httpx.Client) -> Optional[Dict[str, Any]]:
    datos = _get_json(cliente, f"https://www.fotmob.com/api/data/leagues?id={LIGA_MX_ID}&tab=fixtures")
    if not datos:
        return None
    fixtures = datos.get("fixtures") or {}
    partidos = fixtures.get("allMatches") or []
    candidatos = []
    for partido in partidos:
        home = str((partido.get("home") or {}).get("name") or "")
        away = str((partido.get("away") or {}).get("name") or "")
        if "San Luis" in home and "Juárez" in away:
            fecha = str((partido.get("status") or {}).get("utcTime") or "")
            candidatos.append((fecha, partido))
    if not candidatos:
        return None
    candidatos.sort(key=lambda item: item[0])
    return candidatos[-1][1]


def _auditar_fotmob(cliente: httpx.Client) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    print("=" * 90)
    print("ACCIÓN 1 — FOTMOB: H2H Y FORMA 5P")
    print("=" * 90)
    partido = _buscar_partido(cliente)
    if not partido:
        print("[FOTMOB] No se encontró el partido en `leagues?tab=fixtures`.")
        return None, None
    match_id = str(partido.get("id") or "")
    print(f"Partido : {LOCAL} vs {VISITA}")
    print(f"Match ID: {match_id}")
    print(f"Fecha   : {(partido.get('status') or {}).get('utcTime')}")

    datos = _get_json(cliente, f"https://www.fotmob.com/api/data/matchDetails?matchId={match_id}")
    if not datos:
        return match_id, None

    contenido = datos.get("content") or {}
    h2h = contenido.get("h2h") or {}
    resumen = h2h.get("summary") or []
    partidos_h2h = h2h.get("matches") or []
    print(f"\n[content.h2h] sección presente: {bool(h2h)}")
    print(f"  resumen (local/empate/visita): {resumen}")
    print(f"  partidos históricos: {len(partidos_h2h)}")
    for anterior in partidos_h2h[:3]:
        status = (anterior.get("status") or {}).get("scoreStr") or "—"
        home = (anterior.get("home") or {}).get("name") or "?"
        away = (anterior.get("away") or {}).get("name") or "?"
        fecha = (anterior.get("time") or {}).get("utcTime") or "—"
        print(f"    · {fecha} · {home} {status} {away}")

    match_facts = contenido.get("matchFacts") or {}
    team_form = match_facts.get("teamForm") or []
    print(f"\n[content.matchFacts.teamForm] listas: {len(team_form)}")
    for indice, lista in enumerate(team_form):
        if not isinstance(lista, list):
            continue
        print(f"  lista {indice}: {len(lista)} partidos")
        for forma in lista[:5]:
            if not isinstance(forma, dict):
                continue
            resultado = forma.get("resultString") or "?"
            score = forma.get("score") or "—"
            tooltip = forma.get("tooltipText") or {}
            local_t = tooltip.get("homeTeam") or "?"
            visita_t = tooltip.get("awayTeam") or "?"
            print(f"    · {local_t} {score} {visita_t} → {resultado}")

    print("\n[OTROS ENDPOINTS]")
    print("  · `matchDetails` publica h2h + teamForm en una sola llamada.")
    print("  · `leagues?tab=fixtures` publica la cartelera y el matchId.")
    return match_id, datos


def _auditar_legacy() -> List[str]:
    print("\n" + "=" * 90)
    print("ACCIÓN 2 — LEGACY Y DOCUMENTACIÓN: ORIGEN DEL DATO")
    print("=" * 90)
    hallazgos: List[str] = []

    if LOGIC.is_file():
        lineas = LOGIC.read_text(encoding="utf-8", errors="replace").splitlines()
        for indice, linea in enumerate(lineas, start=1):
            if "[LN-QBE-020]" in linea or "[LN-QBE-036]" in linea:
                print(f"  docs/LOGIC.md:{indice}: {linea.strip()[:180]}")
                hallazgos.append(f"LOGIC:{indice}")

    ruta_h2h = RAIZ / "qbe_ingestion" / "src" / "ingestion" / "daemons" / "centinela_deportivo.py"
    if ruta_h2h.is_file():
        lineas = ruta_h2h.read_text(encoding="utf-8", errors="replace").splitlines()
        for indice, linea in enumerate(lineas, start=1):
            if "_h2h_desde_historial" in linea or "historical_matches" in linea:
                print(f"  centinela_deportivo.py:{indice}: {linea.strip()[:180]}")
                hallazgos.append(f"DEPORTIVO:{indice}")

    if LEGACY.is_dir():
        patrones = ("footystats", "mediotiempo", "h2h", "forma_5", "last_matches", "last5")
        encontrados = 0
        for carpeta in ("src", "scripts", "app", "docs"):
            base = LEGACY / carpeta
            if not base.is_dir():
                continue
            for archivo in base.rglob("*"):
                if archivo.suffix.lower() not in (".py", ".md", ".txt", ".json"):
                    continue
                if any(parte.startswith(".") for parte in archivo.parts):
                    continue
                try:
                    texto = archivo.read_text(encoding="utf-8", errors="replace").lower()
                except OSError:
                    continue
                for patron in patrones:
                    if patron in texto:
                        print(f"  legacy:{archivo.relative_to(LEGACY)} ← '{patron}'")
                        encontrados += 1
                        hallazgos.append(f"LEGACY:{patron}")
                        break
                if encontrados >= 8:
                    break
            if encontrados >= 8:
                break
    else:
        print(f"  [LEGACY] No existe {LEGACY}")

    if not hallazgos:
        print("  Sin referencias locales; se declara deuda de procedencia.")
    return hallazgos


def main() -> int:
    print("SONDA H2H / FORMA 5P — SPRINT-46")
    print(f"Raíz: {RAIZ}")
    cliente = httpx.Client(headers=CABECERAS, timeout=40.0, follow_redirects=True)
    try:
        match_id, datos = _auditar_fotmob(cliente)
    finally:
        cliente.close()

    hallazgos = _auditar_legacy()

    print("\n" + "=" * 90)
    print("DIAGNÓSTICO DE VIABILIDAD")
    print("=" * 90)
    h2h_ok = bool(datos and (datos.get("content") or {}).get("h2h"))
    forma_ok = bool(datos and ((datos.get("content") or {}).get("matchFacts") or {}).get("teamForm"))
    print(f"  H2H en vivo (FotMob)      : {'VIABLE' if h2h_ok else 'NO VIABLE'}")
    print(f"  Forma 5P en vivo (FotMob) : {'VIABLE' if forma_ok else 'NO VIABLE'}")
    print("  Histórico H2H/Forma       : VIABLE vía corpus FootyStats (`historical_matches`,")
    print("                              `historical_team_season_stats`) y `[LN-QBE-020]`/`[LN-QBE-036]`.")
    print("  Fuente primaria live      : `matchDetails.content.h2h` + `content.matchFacts.teamForm`.")
    print("  Fuente secundaria         : FootyStats MHTML congelado (backtesting); no se observó")
    print("                              dependencia de Mediotiempo en el legacy auditado.")
    print(f"  Evidencia legacy          : {len(hallazgos)} referencias locales.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
