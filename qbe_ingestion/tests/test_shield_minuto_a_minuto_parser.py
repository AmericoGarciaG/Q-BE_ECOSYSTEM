# -*- coding: utf-8 -*-
"""🏆 THE SHIELD — JUEZ INMUTABLE DEL PARSER MINUTO A MINUTO.

Nodo: `[LN-QBE-141]` Parser Offline de Eventos Minuto a Minuto (Jugada a Jugada).
Base de Gobierno: `docs/LOGIC.md` §16.

Aislamiento: el import del parser es diferido para no contaminar `sys.modules`
durante la colecta (el Juez de fronteras de `qbe_business` verifica que
`qbe_ingestion` no se importe a nivel de módulo).
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

import pytest
from bs4 import BeautifulSoup

RAIZ = Path(__file__).resolve().parents[2]
MHTML_MUESTRA = (
    RAIZ
    / "data"
    / "raw_ligamx_min_x_min"
    / "MinXMin_2015-2016_Clau_Ame_vs_MTY.mhtml"
)


def _parser():
    """Import diferido del parser bajo juicio."""
    from qbe_ingestion.src.ingestion.parsers import parsear_minuto_a_minuto

    return parsear_minuto_a_minuto


def _escribir_mhtml(tmp_path: Path, html: str, tipo: str = "text/html") -> Path:
    """Envuelve un HTML en un MHTML mínimo para los Sad Paths estructurales."""
    cuerpo = (
        "MIME-Version: 1.0\r\n"
        'Content-Type: multipart/related; boundary="BOUND"\r\n'
        "\r\n"
        "--BOUND\r\n"
        f"Content-Type: {tipo}; charset=utf-8\r\n"
        "Content-Transfer-Encoding: 8bit\r\n"
        "\r\n"
        f"{html}\r\n"
        "--BOUND--\r\n"
    )
    ruta = tmp_path / "muestra_sad_path.mhtml"
    ruta.write_bytes(cuerpo.encode("utf-8"))
    return ruta


def _html_real() -> str:
    return _parser().extraer_html_de_mhtml(MHTML_MUESTRA)


# ── Invariantes fácticas ─────────────────────────────────────────────────────────────────────
def test_invarianza_49_eventos_y_metadatos_del_partido() -> None:
    """[INV 1] El MHTML de muestra contiene exactamente 49 eventos y el sobre 3-3."""
    modulo = _parser()
    assert MHTML_MUESTRA.is_file(), f"Falta el MHTML de muestra: {MHTML_MUESTRA}"

    partido = modulo.parsear_partido(MHTML_MUESTRA)
    eventos: List[Dict[str, Any]] = partido["eventos"]

    assert len(eventos) == 49
    assert partido["equipo_local"] == "América"
    assert partido["equipo_visitante"] == "Monterrey"
    assert partido["marcador_local"] == 3
    assert partido["marcador_visitante"] == 3
    assert sum(1 for e in eventos if e["lado"] == "local") == 27
    assert sum(1 for e in eventos if e["lado"] == "visita") == 22


def test_invarianza_goles_tarjetas_y_corners() -> None:
    """[INV 2] 6 goles (5 + 1 penal), 7 amarillas y 4 córners."""
    modulo = _parser()
    eventos = modulo.parsear_minuto_a_minuto(MHTML_MUESTRA)
    tipos = Counter(evento["tipo"] for evento in eventos)

    assert tipos["gol"] + tipos["gol_penal"] == 6
    assert tipos["tarjeta_amarilla"] == 7
    assert tipos["corner"] == 4

    goles = {
        (evento["minuto"], evento["lado"])
        for evento in eventos
        if evento["tipo"] in {"gol", "gol_penal"}
    }
    assert goles == {
        (19, "local"),
        (36, "local"),
        (78, "local"),
        (10, "visita"),
        (55, "visita"),
        (76, "visita"),
    }

    corners = {
        (evento["minuto_texto"], evento["lado"])
        for evento in eventos
        if evento["tipo"] == "corner"
    }
    assert corners == {("35'", "local"), ("39'", "local"), ("80'", "local"), ("+1'", "visita")}


def test_invarianza_ids_unicos_y_exclusion_de_la_linea_de_videos() -> None:
    """[INV 3] 49 IDs únicos; los 13 duplicados de `timelineVideo_*` quedan fuera."""
    modulo = _parser()
    eventos = modulo.parsear_minuto_a_minuto(MHTML_MUESTRA)
    identificadores = [evento["evento_id"] for evento in eventos]

    assert len(identificadores) == 49
    assert len(set(identificadores)) == 49
    assert "111584" in identificadores
    # La línea de videos repite 13 eventos; si se colara, el total sería 62.
    assert len(eventos) != 62


def test_invarianza_minutos_periodos_y_marcadores() -> None:
    """[INV 4] Gramática del minuto, tiempo agregado y períodos derivados."""
    modulo = _parser()
    eventos = modulo.parsear_minuto_a_minuto(MHTML_MUESTRA)
    por_id = {evento["evento_id"]: evento for evento in eventos}

    gol_78 = por_id["111584"]
    assert (gol_78["minuto"], gol_78["minuto_agregado"], gol_78["periodo"]) == (78, None, "2T")

    corner_agregado = por_id["111591"]
    assert corner_agregado["minuto"] is None
    assert corner_agregado["minuto_agregado"] == 1
    assert corner_agregado["minuto_texto"] == "+1'"
    assert corner_agregado["periodo"] == "2T"

    final = por_id["111593"]
    assert final["marcador_periodo"] == "MF"
    assert final["periodo"] == "MF"
    assert final["minuto"] is None

    medio_tiempo = por_id["111570"]
    assert medio_tiempo["marcador_periodo"] == "MT"
    assert medio_tiempo["periodo"] == "MT"

    inicio_segundo = por_id["111572"]
    assert inicio_segundo["tipo"] == "inicio_segundo_tiempo"
    assert inicio_segundo["periodo"] == "2T"


def test_invarianza_utf8_estricto_y_equipos() -> None:
    """[INV 5] La decodificación estricta preserva acentos y nombres canónicos."""
    modulo = _parser()
    partido = modulo.parsear_partido(MHTML_MUESTRA)

    assert partido["equipo_local"] == "América"
    assert partido["equipo_visitante"] == "Monterrey"
    descripciones = " ".join(evento["descripcion"] for evento in partido["eventos"])
    assert "José Daniel Octavio Guerrero" in descripciones
    assert "Darío Ismael Benedetto" in descripciones
    assert "Ã" not in descripciones


def test_invarianza_contrato_de_campos_y_orden_dom() -> None:
    """[INV 6] Todos los eventos declaran el contrato y preservan el orden DOM."""
    modulo = _parser()
    eventos = modulo.parsear_minuto_a_minuto(MHTML_MUESTRA)

    claves = {
        "evento_id",
        "lado",
        "equipo",
        "minuto_texto",
        "minuto",
        "minuto_agregado",
        "marcador_periodo",
        "periodo",
        "tipo",
        "descripcion",
        "video_url",
        "paso",
        "orden_dom",
    }
    for evento in eventos:
        assert claves <= set(evento)
        assert evento["tipo"] != "otro", evento
        assert evento["lado"] in {"local", "visita"}

    assert [evento["orden_dom"] for evento in eventos] == list(range(49))
    assert eventos[0]["evento_id"] == "111593"
    assert eventos[0]["tipo"] == "final_partido"
    assert eventos[-1]["evento_id"] == "111546"


def test_legislacion_141_y_142_ancladas_en_la_base_de_gobierno() -> None:
    """[INV 7] Los nodos nuevos existen en LOGIC.md y en ID_REGISTRY.md."""
    logica = (RAIZ / "docs" / "LOGIC.md").read_text(encoding="utf-8")
    registro = (RAIZ / "docs" / "ID_REGISTRY.md").read_text(encoding="utf-8")

    assert "[LN-QBE-141]" in logica
    assert "[LN-QBE-142]" in logica
    assert "[LN-QBE-141]" in registro
    assert "[LN-QBE-142]" in registro


# ── Sad Paths ───────────────────────────────────────────────────────────────────────────────
def test_sad_path_archivo_inexistente() -> None:
    """[SAD 1] Ruta inexistente: falla ruidosa, sin lista vacía."""
    modulo = _parser()
    with pytest.raises(FileNotFoundError):
        modulo.parsear_minuto_a_minuto(RAIZ / "data" / "no_existe.mhtml")


def test_sad_path_sin_parte_text_html(tmp_path: Path) -> None:
    """[SAD 2] MHTML sin parte text/html: excepción de dominio."""
    modulo = _parser()
    ruta = _escribir_mhtml(tmp_path, "sin html", tipo="text/plain")
    with pytest.raises(modulo.MinutoAJugadaError):
        modulo.parsear_minuto_a_minuto(ruta)


def test_sad_path_sin_contenedor_jugadas_tool(tmp_path: Path) -> None:
    """[SAD 3] Sin `div.jugadasTool`: excepción de dominio."""
    modulo = _parser()
    html = """
    <html><body>
      <div class="cara-cara">
        <div class="equipoMin"><a href="/cancha/club/1/america" data-original-title="América"></a></div>
        <div class="equipoMin"><a href="/cancha/club/14/monterrey" data-original-title="Monterrey"></a></div>
        <span class="score">3 - 3</span>
      </div>
    </body></html>
    """
    ruta = _escribir_mhtml(tmp_path, html)
    with pytest.raises(modulo.MinutoAJugadaError, match="jugadasTool"):
        modulo.parsear_minuto_a_minuto(ruta)


def test_sad_path_sin_columna_visita(tmp_path: Path) -> None:
    """[SAD 4] Sin `#timeline_visita`: excepción de dominio."""
    modulo = _parser()
    sopa = BeautifulSoup(_html_real(), "html.parser")
    columna = sopa.select_one("#timeline_visita")
    assert columna is not None
    columna.decompose()
    ruta = _escribir_mhtml(tmp_path, str(sopa))

    with pytest.raises(modulo.MinutoAJugadaError):
        modulo.parsear_minuto_a_minuto(ruta)


def test_sad_path_minuto_corrupto(tmp_path: Path) -> None:
    """[SAD 5] Minuto fuera de gramática: excepción de dominio, no evento inventado."""
    modulo = _parser()
    sopa = BeautifulSoup(_html_real(), "html.parser")
    nodo_minuto = sopa.select_one("div.jugadasTool .toolJugada > span.col-xs-2")
    assert nodo_minuto is not None
    nodo_minuto.string = "XX"
    ruta = _escribir_mhtml(tmp_path, str(sopa))

    with pytest.raises(modulo.MinutoAJugadaError, match="Minuto no reconocido"):
        modulo.parsear_minuto_a_minuto(ruta)


def test_sad_path_mhtml_invalido(tmp_path: Path) -> None:
    """[SAD 6] Archivo binario no MIME: excepción de dominio."""
    modulo = _parser()
    ruta = tmp_path / "invalido.mhtml"
    ruta.write_bytes(b"\x00\x01\x02 no es un mhtml \xff")
    with pytest.raises(modulo.MinutoAJugadaError):
        modulo.parsear_minuto_a_minuto(ruta)
