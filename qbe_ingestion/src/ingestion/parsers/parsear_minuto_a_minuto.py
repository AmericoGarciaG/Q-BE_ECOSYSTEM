# -*- coding: utf-8 -*-
"""[LN-QBE-141] Parser offline de la narrativa «Jugada a Jugada» de ligamx.net.

Régimen: ``[DIRGEN-STRICT]``. Cero red, cero navegador, cero datos sintéticos.

El parser consume un volcado MHTML (MIME HTML) del visor «Minuto a Minuto» de
ligamx.net y devuelve los eventos fácticos de la línea de tiempo. La estructura
de referencia es el archivo de muestra:

    data/raw_ligamx_min_x_min/MinXMin_2015-2016_Clau_Ame_vs_MTY.mhtml

Contrato principal
------------------
``parsear_minuto_a_minuto(ruta_mhtml) -> list[dict]``
    Devuelve la lista de eventos. Es el contrato legislado en ``docs/LOGIC.md``.

``parsear_partido(ruta_mhtml) -> dict``
    Devuelve el sobre completo: equipos, marcador y eventos.

Fail-Loud
---------
Toda ausencia de la estructura esperada (sin ``div.jugadasTool``, sin columnas,
sin ``.toolJugada``, sin minuto, sin identificador, IDs duplicados, minuto
corrupto o codificación no decodificable) lanza ``MinutoAJugadaError``. Nunca
se devuelve una lista vacía ni se fabrica un evento.
"""

from __future__ import annotations

import argparse
import email
import json
import re
import sys
from email import policy
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from bs4 import BeautifulSoup

__all__ = [
    "MinutoAJugadaError",
    "extraer_html_de_mhtml",
    "parsear_minuto_a_minuto",
    "parsear_minuto_a_minuto_desde_html",
    "parsear_partido",
    "parsear_partido_desde_html",
]

# ── Contrato estructural [LN-QBE-141] ─────────────────────────────────────────────────────────
CONTENEDOR_JUGADAS = "div.jugadasTool"
COLUMNA_LOCAL = "#timeline_local"
COLUMNA_VISITA = "#timeline_visita"

PATRON_EVENTO = re.compile(r"^evnt(?P<prefijo>Lcal|Vsta)_(?P<id>\d+)$")
PATRON_MINUTO_BASE = re.compile(r"^(?P<base>\d+)'$")
PATRON_MINUTO_AGREGADO = re.compile(r"^\+(?P<agregado>\d+)'$")
PATRON_MINUTO_COMPUESTO = re.compile(r"^(?P<base>\d+)\s*\+\s*(?P<agregado>\d+)'$")
PATRON_MARCADOR_PERIODO = re.compile(r"^(?P<marcador>MT|MF)$")
PATRON_MARCADOR = re.compile(r"^(?P<local>\d+)\s*-\s*(?P<visitante>\d+)$")

TIPOS_NEUTROS = frozenset(
    {
        "inicio_partido",
        "inicio_segundo_tiempo",
        "final_primer_tiempo",
        "final_partido",
    }
)

MARCADORES_OBLIGATORIOS = (
    "inicio_partido",
    "final_primer_tiempo",
    "inicio_segundo_tiempo",
    "final_partido",
)


class MinutoAJugadaError(RuntimeError):
    """[LN-QBE-141] El MHTML no contiene la estructura «Jugada a Jugada» esperada."""


# ── Utilidades de texto ──────────────────────────────────────────────────────────────────────
def _texto(nodo: Any) -> str:
    """Normaliza texto de un nodo o de un atributo (colapsa espacios)."""
    if nodo is None:
        return ""
    if isinstance(nodo, str):
        return re.sub(r"\s+", " ", nodo).strip()
    return re.sub(r"\s+", " ", nodo.get_text(" ", strip=True)).strip()


# ── Desempaquetado MIME ──────────────────────────────────────────────────────────────────────
def extraer_html_de_mhtml(ruta_mhtml: Path) -> str:
    """Extrae la parte ``text/html`` de un ``.mhtml`` y la decodifica en estricto.

    Reglas:
      * Se respeta el ``charset`` declarado por la parte MIME; si no declara,
        se usa UTF-8 (la muestra declara UTF-8 en ``<meta>`` y no en la parte).
      * La decodificación es ``errors="strict"``. Un byte inválido aborta.
      * Se prohíbe ``errors="replace"``: corrompería los acentos del corpus.
    """
    ruta = Path(ruta_mhtml)
    with open(ruta, "rb") as manejador:
        mensaje = email.message_from_binary_file(manejador, policy=policy.default)

    for parte in mensaje.walk():
        if parte.get_content_type() != "text/html":
            continue
        carga = parte.get_payload(decode=True)
        if carga is None:
            raise MinutoAJugadaError(
                f"[LN-QBE-141] La parte text/html de {ruta} no tiene payload decodificable"
            )
        codificacion = parte.get_content_charset() or "utf-8"
        try:
            return carga.decode(codificacion, errors="strict")
        except (UnicodeDecodeError, LookupError) as error:
            raise MinutoAJugadaError(
                f"[LN-QBE-141] No se pudo decodificar {ruta} con charset {codificacion!r}: {error}"
            ) from error

    raise MinutoAJugadaError(
        f"[LN-QBE-141] No se encontró ninguna parte text/html en {ruta}"
    )


# ── Metadatos del partido ───────────────────────────────────────────────────────────────────
def _extraer_equipos(sopa: BeautifulSoup) -> Tuple[str, str]:
    """Devuelve ``(local, visitante)`` desde ``data-original-title``."""
    bloques = sopa.select(".cara-cara .equipoMin")
    if len(bloques) != 2:
        raise MinutoAJugadaError(
            f"[LN-QBE-141] Se esperaban 2 bloques .cara-cara .equipoMin; se encontraron {len(bloques)}"
        )

    nombres: List[str] = []
    for bloque in bloques:
        enlace = bloque.select_one('a[href*="/cancha/club/"]')
        if enlace is None:
            raise MinutoAJugadaError(
                "[LN-QBE-141] Un bloque .equipoMin no contiene enlace de club"
            )
        nombre = _texto(enlace.get("data-original-title"))
        if not nombre:
            raise MinutoAJugadaError(
                "[LN-QBE-141] El enlace de club no declara data-original-title"
            )
        nombres.append(nombre)
    return nombres[0], nombres[1]


def _extraer_marcador(sopa: BeautifulSoup) -> Tuple[int, int]:
    """Devuelve ``(goles_local, goles_visitante)`` desde ``.cara-cara .score``."""
    nodos = sopa.select(".cara-cara .score")
    if len(nodos) != 1:
        raise MinutoAJugadaError(
            f"[LN-QBE-141] Se esperaba 1 marcador .cara-cara .score; se encontraron {len(nodos)}"
        )
    texto = _texto(nodos[0])
    coincide = PATRON_MARCADOR.match(texto)
    if not coincide:
        raise MinutoAJugadaError(
            f"[LN-QBE-141] Marcador no reconocido: {texto!r}"
        )
    return int(coincide.group("local")), int(coincide.group("visitante"))


# ── Clasificación semántica desde .desc ─────────────────────────────────────────────────────
def _clasificar(descripcion: str) -> str:
    """Clasifica el evento por su narrativa oficial (no por ``div.paso``)."""
    texto = descripcion.lower()
    prefijo = texto.lstrip("¡ ")

    if "goool" in texto:
        return "gol_penal" if "penal" in texto else "gol"
    if "tarjeta amarilla" in texto:
        return "tarjeta_amarilla"
    if "tarjeta roja" in texto:
        return "tarjeta_roja"
    if "tiro de esquina" in texto or "corner" in texto:
        return "corner"
    if prefijo.startswith("falta cometida"):
        return "falta"
    if prefijo.startswith("tiro a gol"):
        return "tiro_a_gol"
    if prefijo.startswith("cambio de"):
        return "cambio"
    if prefijo.startswith("fuera de lugar"):
        return "fuera_de_lugar"
    if "señala penal" in texto:
        return "penal"
    if "gran atajada" in texto:
        return "atajada"
    if "final del partido" in texto:
        return "final_partido"
    if "final del primer tiempo" in texto:
        return "final_primer_tiempo"
    if prefijo.startswith("inicia el segundo tiempo"):
        return "inicio_segundo_tiempo"
    if prefijo.startswith("inicia el partido"):
        return "inicio_partido"
    return "otro"


# ── Minuto ──────────────────────────────────────────────────────────────────────────────────
def _interpretar_minuto(texto: str, evento_id: str) -> Dict[str, Any]:
    """Traduce el rótulo del minuto a ``minuto``, ``minuto_agregado`` y ``marcador``.

    Gramática soportada:
      * ``N'``          → minuto = N
      * ``+N'``         → minuto_agregado = N (sin minuto base)
      * ``N+M'``        → minuto = N, minuto_agregado = M
      * ``MT`` / ``MF`` → marcador de período, sin minuto
    """
    limpio = texto.strip()

    coincide = PATRON_MINUTO_BASE.match(limpio)
    if coincide:
        return {
            "minuto": int(coincide.group("base")),
            "minuto_agregado": None,
            "marcador_periodo": None,
        }

    coincide = PATRON_MINUTO_AGREGADO.match(limpio)
    if coincide:
        return {
            "minuto": None,
            "minuto_agregado": int(coincide.group("agregado")),
            "marcador_periodo": None,
        }

    coincide = PATRON_MINUTO_COMPUESTO.match(limpio)
    if coincide:
        return {
            "minuto": int(coincide.group("base")),
            "minuto_agregado": int(coincide.group("agregado")),
            "marcador_periodo": None,
        }

    coincide = PATRON_MARCADOR_PERIODO.match(limpio)
    if coincide:
        return {
            "minuto": None,
            "minuto_agregado": None,
            "marcador_periodo": coincide.group("marcador"),
        }

    raise MinutoAJugadaError(
        f"[LN-QBE-141] Minuto no reconocido en evento {evento_id}: {texto!r}"
    )


# ── Extracción de una columna ───────────────────────────────────────────────────────────────
def _extraer_columna(
    columna: Any,
    lado: str,
    prefijo_esperado: str,
    equipo: str,
) -> List[Dict[str, Any]]:
    """Extrae los eventos de una columna; ignora filas espaciadoras."""
    filas = columna.find_all("div", class_="row", recursive=False)
    eventos: List[Dict[str, Any]] = []

    for fila in filas:
        jugada = fila.select_one(":scope > .toolJugada")
        if jugada is None:
            # Fila espaciadora: solo aporta alineación vertical, no es un evento.
            continue

        identificadores = []
        for clase in fila.get("class") or []:
            coincide = PATRON_EVENTO.match(str(clase))
            if coincide:
                identificadores.append(coincide)
        if len(identificadores) != 1:
            raise MinutoAJugadaError(
                f"[LN-QBE-141] Fila de evento sin identificador único: {fila.get('class')!r}"
            )
        coincide = identificadores[0]
        if coincide.group("prefijo") != prefijo_esperado:
            raise MinutoAJugadaError(
                f"[LN-QBE-141] Prefijo de evento {coincide.group('prefijo')!r} "
                f"no corresponde a la columna {lado!r}"
            )
        evento_id = coincide.group("id")

        descripcion = _texto(jugada.select_one(".desc"))
        if not descripcion:
            raise MinutoAJugadaError(
                f"[LN-QBE-141] Evento {evento_id} sin descripción (.desc)"
            )

        nodo_minuto = jugada.select_one(":scope > span.col-xs-2")
        if nodo_minuto is None:
            raise MinutoAJugadaError(
                f"[LN-QBE-141] Evento {evento_id} sin minuto (span.col-xs-2)"
            )
        minuto_texto = _texto(nodo_minuto)

        enlace = jugada.select_one("span.enlace[id^='evnt_']")
        if enlace is None:
            raise MinutoAJugadaError(
                f"[LN-QBE-141] Evento {evento_id} sin span.enlace[id^='evnt_']"
            )
        if enlace.get("id") != f"evnt_{evento_id}":
            raise MinutoAJugadaError(
                f"[LN-QBE-141] Identificador inconsistente en evento {evento_id}: "
                f"span declara {enlace.get('id')!r}"
            )

        interpretado = _interpretar_minuto(minuto_texto, evento_id)
        tipo = _clasificar(descripcion)

        nodo_paso = fila.select_one(":scope > .paso")
        clases_paso = [
            clase for clase in (nodo_paso.get("class") or []) if clase != "paso"
        ] if nodo_paso is not None else []

        video = jugada.select_one("a[data-urlvideo]")

        eventos.append(
            {
                "evento_id": evento_id,
                "lado": lado,
                "equipo": None if tipo in TIPOS_NEUTROS else equipo,
                "minuto_texto": minuto_texto,
                "minuto": interpretado["minuto"],
                "minuto_agregado": interpretado["minuto_agregado"],
                "marcador_periodo": interpretado["marcador_periodo"],
                "periodo": None,
                "tipo": tipo,
                "descripcion": descripcion,
                "video_url": video.get("data-urlvideo") if video is not None else None,
                "paso": " ".join(clases_paso) if clases_paso else None,
                "orden_dom": 0,
            }
        )

    return eventos


# ── Períodos ──────────────────────────────────────────────────────────────────────────────
def _asignar_periodos(
    eventos_local: List[Dict[str, Any]],
    eventos_visita: List[Dict[str, Any]],
) -> None:
    """Asigna ``periodo`` de forma determinista.

    Columna local: máquina de estados sobre los marcadores explícitos
    (inicio, MT, inicio 2T, final). Columna visitante: regla numérica
    (<=45 → 1T; >=46 → 2T; +N' → 2T), porque el DOM visitante no trae marcadores.
    """
    periodo = "1T"
    for evento in reversed(eventos_local):
        tipo = evento["tipo"]
        if tipo == "inicio_partido":
            periodo = "1T"
            evento["periodo"] = periodo
        elif tipo == "final_primer_tiempo":
            evento["periodo"] = "MT"
            periodo = "2T"
        elif tipo == "inicio_segundo_tiempo":
            periodo = "2T"
            evento["periodo"] = periodo
        elif tipo == "final_partido":
            evento["periodo"] = "MF"
        else:
            evento["periodo"] = periodo

    for evento in reversed(eventos_visita):
        if evento["minuto"] is not None:
            evento["periodo"] = "1T" if evento["minuto"] <= 45 else "2T"
        elif evento["minuto_agregado"] is not None:
            evento["periodo"] = "2T"
        else:
            evento["periodo"] = None


def _validar_marcadores(eventos_local: List[Dict[str, Any]]) -> None:
    """Exige los cuatro marcadores de período en la columna local."""
    if not eventos_local:
        raise MinutoAJugadaError(
            "[LN-QBE-141] La columna local no contiene eventos"
        )
    if eventos_local[0]["tipo"] != "final_partido":
        raise MinutoAJugadaError(
            "[LN-QBE-141] El primer evento de la columna local no es el final del partido"
        )
    if eventos_local[-1]["tipo"] != "inicio_partido":
        raise MinutoAJugadaError(
            "[LN-QBE-141] El último evento de la columna local no es el inicio del partido"
        )
    for marcador in MARCADORES_OBLIGATORIOS:
        if sum(1 for evento in eventos_local if evento["tipo"] == marcador) != 1:
            raise MinutoAJugadaError(
                f"[LN-QBE-141] La columna local no contiene exactamente un marcador {marcador!r}"
            )


# ── Contrato público ───────────────────────────────────────────────────────────────────────
def _parsear_arbol(sopa: BeautifulSoup) -> Dict[str, Any]:
    """[LN-QBE-141] Núcleo puro de extracción sobre un árbol ``BeautifulSoup``.

    Es la única implementación del contrato: la comparten la ruta MHTML
    (``parsear_partido``) y la ruta HTML en memoria (``parsear_partido_desde_html``),
    de modo que no exista una segunda copia de las validaciones estructurales.
    """
    equipo_local, equipo_visitante = _extraer_equipos(sopa)
    marcador_local, marcador_visitante = _extraer_marcador(sopa)

    contenedores = sopa.select(CONTENEDOR_JUGADAS)
    if not contenedores:
        raise MinutoAJugadaError(
            f"[LN-QBE-141] No existe {CONTENEDOR_JUGADAS} en el documento"
        )

    # El documento contiene DOS `div.jugadasTool`: la línea de tiempo canónica
    # (`#timeline_local` + `#timeline_visita`, 49 eventos) y la línea de videos
    # (`#timelineVideo_local` + `#timelineVideo_visita`, 13 duplicados). Solo la
    # primera contiene las columnas canónicas; la segunda se descarta por completo.
    candidatos: List[Tuple[Any, Any, Any]] = []
    for contenedor in contenedores:
        locales = contenedor.select(COLUMNA_LOCAL)
        visitas = contenedor.select(COLUMNA_VISITA)
        if len(locales) == 1 and len(visitas) == 1:
            candidatos.append((contenedor, locales[0], visitas[0]))

    if len(candidatos) != 1:
        raise MinutoAJugadaError(
            f"[LN-QBE-141] Se esperaba 1 contenedor canónico con "
            f"{COLUMNA_LOCAL} y {COLUMNA_VISITA}; se encontraron {len(candidatos)}"
        )

    _, columna_local, columna_visita = candidatos[0]

    eventos_local = _extraer_columna(columna_local, "local", "Lcal", equipo_local)
    eventos_visita = _extraer_columna(columna_visita, "visita", "Vsta", equipo_visitante)

    if not eventos_local or not eventos_visita:
        raise MinutoAJugadaError(
            "[LN-QBE-141] Una de las dos columnas quedó sin eventos"
        )

    _validar_marcadores(eventos_local)
    _asignar_periodos(eventos_local, eventos_visita)

    eventos = eventos_local + eventos_visita
    vistos = set()
    for indice, evento in enumerate(eventos):
        if evento["evento_id"] in vistos:
            raise MinutoAJugadaError(
                f"[LN-QBE-141] Evento duplicado: {evento['evento_id']}"
            )
        vistos.add(evento["evento_id"])
        evento["orden_dom"] = indice

    return {
        "equipo_local": equipo_local,
        "equipo_visitante": equipo_visitante,
        "marcador_local": marcador_local,
        "marcador_visitante": marcador_visitante,
        "eventos": eventos,
    }


def parsear_partido_desde_html(html: str) -> Dict[str, Any]:
    """[LN-QBE-141] Extrae el sobre completo desde un HTML ya en memoria.

    Extensión pura para el orquestador `[LN-QBE-143]`: no toca red ni disco y
    devuelve el mismo sobre que ``parsear_partido(ruta)`` reutilizando
    ``_parsear_arbol``. Un ``html`` vacío o no textual aborta (Fail-Loud).
    """
    if not isinstance(html, str) or not html.strip():
        raise MinutoAJugadaError(
            "[LN-QBE-141] El HTML en memoria debe ser una cadena no vacía"
        )
    return _parsear_arbol(BeautifulSoup(html, "html.parser"))


def parsear_partido(ruta_mhtml: Path) -> Dict[str, Any]:
    """[LN-QBE-141] Extrae el sobre completo del partido: equipos, marcador y eventos.

    Returns:
        ``{"equipo_local": str, "equipo_visitante": str,
           "marcador_local": int, "marcador_visitante": int, "eventos": list[dict]}``
    """
    return parsear_partido_desde_html(extraer_html_de_mhtml(ruta_mhtml))


def parsear_minuto_a_minuto_desde_html(html: str) -> List[Dict[str, Any]]:
    """[LN-QBE-141] Contrato principal sobre HTML en memoria: lista de eventos."""
    return parsear_partido_desde_html(html)["eventos"]


def parsear_minuto_a_minuto(ruta_mhtml: Path) -> List[Dict[str, Any]]:
    """[LN-QBE-141] Contrato principal: devuelve la lista de eventos del MHTML."""
    return parsear_partido(ruta_mhtml)["eventos"]


# ── CLI de evidencia ────────────────────────────────────────────────────────────────────────
def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI determinista para inspeccionar un MHTML (sin red)."""
    analizador = argparse.ArgumentParser(
        prog="parsear_minuto_a_minuto",
        description="[LN-QBE-141] Parser offline de la narrativa Jugada a Jugada (ligamx.net).",
    )
    analizador.add_argument("--mhtml", required=True, help="ruta del archivo .mhtml")
    analizador.add_argument("--json", action="store_true", help="emite el sobre completo en JSON")
    argumentos = analizador.parse_args(argv)

    try:
        partido = parsear_partido(Path(argumentos.mhtml))
    except (MinutoAJugadaError, OSError) as error:
        print(f"🔴 {error}", file=sys.stderr)
        return 1

    if argumentos.json:
        print(json.dumps(partido, ensure_ascii=False, indent=2))
        return 0

    print(
        f"{partido['equipo_local']} {partido['marcador_local']} - "
        f"{partido['marcador_visitante']} {partido['equipo_visitante']} "
        f"({len(partido['eventos'])} eventos)"
    )
    for evento in partido["eventos"]:
        print(
            f"  {evento['minuto_texto']:>4s} {evento['lado']:6s} "
            f"{evento['tipo']:20s} {evento['descripcion']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
