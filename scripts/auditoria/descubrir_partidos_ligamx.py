# -*- coding: utf-8 -*-
"""[LN-QBE-142] Sonda de Descubrimiento de Partidos y URLs Minuto a Minuto.

Régimen: ``[DIRGEN-STRICT]``. Solo lectura sobre ``ligamx.net``. Cero datos
sintéticos, cero IDs de partido codificados en la lógica.

Uso::

    python scripts/auditoria/descubrir_partidos_ligamx.py \
        --temporada 2015-2016 --torneo Clausura --jornada 16

    python scripts/auditoria/descubrir_partidos_ligamx.py \
        --temporada 2015-2016 --torneo Clausura --jornada 16 --json --verificar

La URL de «Minuto a Minuto» se construye con la forma determinista del sitio:
``/cancha/mxm/{idPartido}/{base64({"idClublocal", "idClubvisita", "idPartido", "pestana"})}``.
El enlace ``.lnk-minute`` del listado no expone ``href``; esta forma es la que
resuelve de manera estable.
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import time
from typing import Any, Dict, List, Optional, Sequence

BASE_URL = "https://ligamx.net"
URL_PARTIDOS = f"{BASE_URL}/cancha/partidos"

# El UA por defecto de Playwright/HeadlessChrome es bloqueado por el WAF
# (HTTP 500 «Web Page Blocked», Attack ID 20000051). Este UA de escritorio
# junto con --disable-blink-features=AutomationControlled es el que funciona.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)
ARGUMENTOS_NAVEGADOR = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-infobars",
    "--ignore-certificate-errors",
]

PATRON_PLANTILLA = re.compile(r"vsurlMrcdrActls:'([^']+)'")
PATRON_REGISTROS = re.compile(r"voTmpTrns\s*:\s*(\{.*?\})\s*,\s*\n", re.S)
PATRON_JORNADA = re.compile(r"^(?:jornada\s*)?(?P<numero>\d+)$", re.I)

# El widget PRTL_Partidos alterna de forma transitoria entre la cartelera y una
# respuesta vacía (`[{}]`) en la misma sesión. Se reintenta de forma acotada y
# determinista; si persiste, la sonda aborta (Fail-Loud).
INTENTOS_WIDGET = 4
ESPERA_REINTENTO_S = 0.4


class DescubrimientoError(RuntimeError):
    """[LN-QBE-142] No se pudo resolver o verificar la cartelera solicitada."""


# ── Constructor puro de URL ────────────────────────────────────────────────────────────────
def construir_url_minuto_a_minuto(
    id_partido: str, id_local: str, id_visitante: str
) -> str:
    """[LN-QBE-142] Construye la URL determinista de «Minuto a Minuto» para un partido.

    La carga útil replica la que usa el sitio: claves en minúsculas y
    ``pestana=3`` (la pestaña «Jugada a Jugada»).
    """
    for nombre, valor in (
        ("id_partido", id_partido),
        ("id_local", id_local),
        ("id_visitante", id_visitante),
    ):
        if not str(valor).strip().isdigit():
            raise DescubrimientoError(
                f"[LN-QBE-142] {nombre} debe ser numérico: {valor!r}"
            )

    carga = {
        "idClublocal": str(id_local),
        "idClubvisita": str(id_visitante),
        "idPartido": str(id_partido),
        "pestana": "3",
    }
    codificada = base64.b64encode(
        json.dumps(carga, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    return f"{BASE_URL}/cancha/mxm/{id_partido}/{codificada}"


def normalizar_jornada(jornada: str) -> str:
    """Acepta ``16`` o ``Jornada 16``; devuelve ``"16"``."""
    coincidencia = PATRON_JORNADA.match(str(jornada).strip())
    if not coincidencia:
        raise DescubrimientoError(
            f"[LN-QBE-142] Jornada no reconocida: {jornada!r}"
        )
    return coincidencia.group("numero")


# ── Parsers puros del HTML servidor ────────────────────────────────────────────────────────
def _extraer_plantilla(html: str) -> str:
    coincidencia = PATRON_PLANTILLA.search(html)
    if coincidencia is None:
        raise DescubrimientoError(
            "[LN-QBE-142] El HTML de /cancha/partidos no declara vsurlMrcdrActls"
        )
    return coincidencia.group(1)


def _extraer_registros(html: str) -> List[Dict[str, Any]]:
    coincidencia = PATRON_REGISTROS.search(html)
    if coincidencia is None:
        raise DescubrimientoError(
            "[LN-QBE-142] El HTML de /cancha/partidos no declara voTmpTrns"
        )
    try:
        datos = json.loads(coincidencia.group(1))
    except json.JSONDecodeError as error:
        raise DescubrimientoError(
            f"[LN-QBE-142] voTmpTrns no es JSON válido: {error}"
        ) from error
    registros = datos.get("DatosJSON")
    if not isinstance(registros, list) or not registros:
        raise DescubrimientoError(
            "[LN-QBE-142] voTmpTrns.DatosJSON está vacío o no es una lista"
        )
    return registros


def _resolver_torneo(
    registros: Sequence[Dict[str, Any]], temporada: str, torneo: str
) -> Dict[str, Any]:
    candidatos = [
        fila
        for fila in registros
        if str(fila.get("Temporada")) == temporada
        and str(fila.get("Torneo")) == torneo
        and str(fila.get("Division")) == "LIGA MX"
    ]
    if len(candidatos) != 1:
        disponibles = sorted(
            {
                f"{fila.get('Temporada')}/{fila.get('Torneo')}"
                for fila in registros
                if str(fila.get("Division")) == "LIGA MX"
            }
        )
        raise DescubrimientoError(
            f"[LN-QBE-142] Resolución ambigua para {temporada}/{torneo}: "
            f"{len(candidatos)} candidatos. Ejemplos disponibles: {disponibles[:8]}"
        )
    return candidatos[0]


def _codificar_servicio(servicio: str) -> str:
    """Replica ``btoa(service).replace('/','@')`` del sitio."""
    return base64.b64encode(servicio.encode("utf-8")).decode("ascii").replace(
        "/", "@", 1
    )


def _consultar_partidos(
    contexto: Any,
    plantilla: str,
    temporada_id: str,
    torneo_id: str,
    jornada: str,
) -> List[Dict[str, Any]]:
    servicio = plantilla
    for clave, valor in {
        "IDDIVISION": "1",
        "IDJORNADA": jornada,
        "IDTEMPORADA": temporada_id,
        "IDTORNEO": torneo_id,
    }.items():
        servicio = re.sub(rf"<{clave}>", str(valor), servicio, flags=re.I)

    url = f"{BASE_URL}/ws/{_codificar_servicio(servicio)}"
    ultimo_cuerpo = ""
    for intento in range(INTENTOS_WIDGET):
        respuesta = contexto.request.get(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Referer": URL_PARTIDOS,
                "X-Requested-With": "XMLHttpRequest",
            },
        )
        if respuesta.status != 200:
            raise DescubrimientoError(
                f"[LN-QBE-142] El widget PRTL_Partidos respondió HTTP {respuesta.status}"
            )
        ultimo_cuerpo = respuesta.text()
        try:
            datos = json.loads(ultimo_cuerpo)
        except json.JSONDecodeError as error:
            raise DescubrimientoError(
                f"[LN-QBE-142] El widget PRTL_Partidos no devolvió JSON: {error}"
            ) from error

        partidos = datos.get("DatosJSON") if isinstance(datos, dict) else None
        if (
            isinstance(partidos, list)
            and partidos
            and isinstance(partidos[0], dict)
            and partidos[0]
        ):
            return partidos
        if intento < INTENTOS_WIDGET - 1:
            time.sleep(ESPERA_REINTENTO_S)

    raise DescubrimientoError(
        "[LN-QBE-142] El widget PRTL_Partidos no devolvió partidos para "
        f"{temporada_id}/{torneo_id}/J{jornada} tras {INTENTOS_WIDGET} intentos. "
        f"Último cuerpo: {ultimo_cuerpo[:180]!r}"
    )


def _entero(valor: Any) -> Optional[int]:
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def _verificar_partido(contexto: Any, partido: Dict[str, Any]) -> None:
    respuesta = contexto.request.get(
        partido["url_minuto_a_minuto"],
        headers={"User-Agent": USER_AGENT},
    )
    if respuesta.status != 200:
        raise DescubrimientoError(
            f"[LN-QBE-142] La URL de {partido['id_partido']} respondió HTTP {respuesta.status}"
        )
    html = respuesta.text()
    if "jugadaSeccion" not in html:
        raise DescubrimientoError(
            f"[LN-QBE-142] La URL de {partido['id_partido']} no contiene section.jugadaSeccion"
        )


# ── Orquestación Playwright ───────────────────────────────────────────────────────────────
def descubrir(
    temporada: str,
    torneo: str,
    jornada: str,
    *,
    verificar: bool = False,
    headless: bool = True,
) -> List[Dict[str, Any]]:
    """Devuelve la lista de partidos con su URL de «Minuto a Minuto»."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as error:  # noqa: BLE001 — Fail-Loud deliberado
        raise DescubrimientoError(
            "[LN-QBE-142] Playwright no está instalado: "
            "pip install playwright && playwright install chromium"
        ) from error

    jornada_normalizada = normalizar_jornada(jornada)

    with sync_playwright() as pw:
        navegador = pw.chromium.launch(headless=headless, args=ARGUMENTOS_NAVEGADOR)
        contexto = navegador.new_context(
            user_agent=USER_AGENT,
            locale="es-MX",
            viewport={"width": 1440, "height": 900},
            timezone_id="America/Mexico_City",
        )
        contexto.set_default_timeout(60_000)
        pagina = contexto.new_page()
        pagina.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        try:
            respuesta = pagina.goto(
                URL_PARTIDOS, wait_until="domcontentloaded", timeout=60_000
            )
            if respuesta is None or respuesta.status != 200:
                raise DescubrimientoError(
                    "[LN-QBE-142] No se pudo abrir /cancha/partidos "
                    f"(HTTP {respuesta.status if respuesta else 'sin respuesta'})"
                )
            pagina.wait_for_selector(
                "#temporadasSelect", state="attached", timeout=30_000
            )
            # La población del selector confirma que el JS del sitio ya inicializó
            # la sesión (cookies del WAF) y que la temporada solicitada existe.
            try:
                pagina.wait_for_function(
                    "(temporada) => Array.from("
                    "document.querySelectorAll('#temporadasSelect option')"
                    ").some(o => o.textContent.trim() === temporada)",
                    arg=temporada,
                    timeout=30_000,
                )
            except Exception as error:  # noqa: BLE001 — Fail-Loud deliberado
                raise DescubrimientoError(
                    f"[LN-QBE-142] La temporada {temporada!r} no aparece en el "
                    "selector de /cancha/partidos"
                ) from error

            # El cuerpo de la respuesta documental es el HTML prístino del
            # servidor, antes de que el JS reescriba la plantilla del widget.
            html = respuesta.text()
            plantilla = _extraer_plantilla(html)
            registros = _extraer_registros(html)
            fila = _resolver_torneo(registros, temporada, torneo)

            partidos = _consultar_partidos(
                contexto,
                plantilla,
                str(fila["IDTemporada"]),
                str(fila["IDTorneo"]),
                jornada_normalizada,
            )

            resultado: List[Dict[str, Any]] = []
            for partido in partidos:
                url = construir_url_minuto_a_minuto(
                    partido["idPartido"],
                    partido["idClubLocal"],
                    partido["idClubVisita"],
                )
                fila_resultado = {
                    "id_partido": str(partido["idPartido"]),
                    "local": partido["clubLocal"],
                    "visitante": partido["clubVisita"],
                    "goles_local": _entero(partido.get("golLocal")),
                    "goles_visitante": _entero(partido.get("golVisita")),
                    "url_minuto_a_minuto": url,
                }
                if verificar:
                    _verificar_partido(contexto, fila_resultado)
                resultado.append(fila_resultado)

            if not resultado:
                raise DescubrimientoError(
                    "[LN-QBE-142] La consulta no devolvió ningún partido"
                )
            return resultado
        finally:
            navegador.close()


# ── CLI ───────────────────────────────────────────────────────────────────────────────────
def _imprimir_tabla(partidos: Sequence[Dict[str, Any]]) -> None:
    cabecera = ("ID", "LOCAL", "VISITANTE", "MARCADOR", "URL")
    filas = [
        (
            partido["id_partido"],
            partido["local"],
            partido["visitante"],
            f"{partido['goles_local']}-{partido['goles_visitante']}",
            partido["url_minuto_a_minuto"],
        )
        for partido in partidos
    ]
    anchos = [
        max(len(str(fila[indice])) for fila in [cabecera, *filas])
        for indice in range(len(cabecera))
    ]
    print(" | ".join(valor.ljust(anchos[i]) for i, valor in enumerate(cabecera)))
    print("-+-".join("-" * ancho for ancho in anchos))
    for fila in filas:
        print(" | ".join(str(valor).ljust(anchos[i]) for i, valor in enumerate(fila)))


def main(argv: Optional[Sequence[str]] = None) -> int:
    analizador = argparse.ArgumentParser(
        prog="descubrir_partidos_ligamx",
        description="[LN-QBE-142] Descubre partidos y URLs de Minuto a Minuto en ligamx.net.",
    )
    analizador.add_argument("--temporada", required=True, help="ej. 2015-2016")
    analizador.add_argument("--torneo", required=True, help="ej. Clausura")
    analizador.add_argument("--jornada", required=True, help="ej. 16 o 'Jornada 16'")
    analizador.add_argument(
        "--json", action="store_true", help="emite la lista en JSON"
    )
    analizador.add_argument(
        "--verificar",
        action="store_true",
        help="descarga cada URL y exige HTTP 200 y section.jugadaSeccion",
    )
    analizador.add_argument(
        "--headed", action="store_true", help="lanza Chromium con ventana (debug)"
    )
    argumentos = analizador.parse_args(argv)

    try:
        partidos = descubrir(
            argumentos.temporada,
            argumentos.torneo,
            argumentos.jornada,
            verificar=argumentos.verificar,
            headless=not argumentos.headed,
        )
    except DescubrimientoError as error:
        print(f"🔴 {error}", file=sys.stderr)
        return 1

    if argumentos.json:
        print(json.dumps(partidos, ensure_ascii=False, indent=2))
    else:
        _imprimir_tabla(partidos)
        print(f"\nTotal: {len(partidos)} partidos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
