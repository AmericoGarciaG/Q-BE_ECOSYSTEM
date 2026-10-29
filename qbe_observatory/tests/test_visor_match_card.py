# -*- coding: utf-8 -*-
"""The Shield — Juez de Contrato de la Match Card Híbrida de Calibración.

[DES-QBE-075] [DBBD-FUNGIBLE] Régimen de presentación. Certifica que el detalle
de jornada del Visor se lee como tarjeta de tres zonas (cabecera / parrilla 1X2 /
pie), que la comparación P′ vs q_mkt se declara sin depender del color, que el
Brier Vars sin motor se degrada a guion con explicación —jamás a una cifra— y
que el modal de 32 variables conserva su contrato (`#modal-44-variables`,
`.btn-ver-44-vars`, `#vars44-cuerpo`) con el fragmento bajo demanda (B2).

El Juez mira CLASES, ATRIBUTOS y LITERALES del DOM: jamás estilos calculados.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

TITULO = "Auditoría de Calibración y Atribución"


@pytest.fixture()
def cliente():
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)


@pytest.fixture()
def reporte(cliente) -> Dict[str, Any]:
    respuesta = cliente.get("/api/observatory/backtesting/calibration-report")
    assert respuesta.status_code == 200, respuesta.text[:500]
    return respuesta.json()


@pytest.fixture()
def html(cliente) -> str:
    respuesta = cliente.get("/visor")
    assert respuesta.status_code == 200, respuesta.text[:500]
    return respuesta.text


# ── Utilidades de inspección ──────────────────────────────────────────────────
def _tarjetas(html: str) -> List[str]:
    return re.findall(r'<article class="mc-card".*?</article>', html, re.S)


def _celda(tarjeta: str, clave: str) -> str:
    """Devuelve el bloque completo de la celda: sus hijos son `span`, no `div`."""
    patron = r'<div class="mc-celda[^"]*"[^>]*data-clave="%s".*?</div>' % clave
    hallado = re.search(patron, tarjeta, re.S)
    assert hallado, f"la tarjeta no declara la celda {clave}"
    return hallado.group(0)


def _vista_sintetica(*, con_1x2: bool = True) -> Dict[str, Any]:
    """Vista mínima con los tres bandos de atribución y un partido concluido."""
    partido: Dict[str, Any] = {
        "id_partido": "P-001",
        "local": "Equipo Casa",
        "visitante": "Equipo Visita",
        "marcador": "2 - 1",
        "resultado_real": "LOCAL",
        "p_texto": "0.500 / 0.250 / 0.250",
        "brier_qbe": 0.31,
        "brier_mercado": 0.28,
        "brier_vars": None,
        "clasificacion_triada": "P_MAX",
        "r_max": "LOCAL",
        "r_mid": "EMPATE",
        "r_low": "VISITANTE",
        "suficiencia_s_i": 1,
        "origen_p_prima": "CAPTURA",
        "origen_captura": "EN_VIVO",
        "es_cold_start": False,
        "atribucion_disponible": True,
        "atribucion_driver": "🛡️ Defensiva Local (+0.23)",
        "atribucion_dimension": "def",
        "semaforos": {"opta": "VERDE", "sede": "AMARILLO", "h2h": "VERDE", "ctx": "ROJO"},
        "variables_44": {"dimensiones": [], "total_variables": 32},
        "descomposicion_log": {},
    }
    if con_1x2:
        partido.update(
            {
                "p_local": 0.512,
                "p_empate": 0.246,
                "p_visitante": 0.242,
                "q_local": 0.441,
                "q_empate": 0.271,
                "q_visitante": 0.288,
                "momios": {"L": 2.1, "E": 3.35, "V": 3.6},
                "local_escudo_url": None,
                "visitante_escudo_url": None,
            }
        )
    return {
        "fuente": {
            "nombre": "snapshot_test.db",
            "ruta": "/tmp/snapshot_test.db",
            "fresco": True,
            "edad_min": 1.0,
            "liga": "LIGA TEST (1)",
            "temporada": "2026",
        },
        "resumen": {
            "total_partidos": 1,
            "n_jornadas": 1,
            "jornada_min": 1,
            "jornada_max": 1,
            "brier_qbe": 0.31,
            "brier_mercado": 0.28,
            "alpha_calibracion_pct": 9.68,
            "alpha_signo": "positivo",
        },
        "jornadas": [
            {
                "jornada": 1,
                "total_partidos": 1,
                "brier_qbe": 0.31,
                "brier_mercado": 0.28,
                "alpha_calibracion_pct": 9.68,
                "alpha_signo": "positivo",
                "alpha_etiqueta": None,
                "partidos": [partido],
            }
        ],
        "error": None,
    }


def _render(vista: Dict[str, Any]) -> str:
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    entorno = Environment(
        loader=FileSystemLoader(str(PROJECT_ROOT / "app" / "templates")),
        autoescape=select_autoescape(["html"]),
    )
    return entorno.get_template("visor.html").render(
        titulo=TITULO, vista=vista, jornada_inicial=1
    )


# ── 1 · Una tarjeta por partido ──────────────────────────────────────────────
def test_match_card_una_por_partido(html: str, reporte: Dict[str, Any]) -> None:
    total = int(reporte["resumen_temporada"]["total_partidos"])
    assert total > 0, "el snapshot del Juez debe portar partidos auditables"
    tarjetas = _tarjetas(html)
    assert len(tarjetas) == total, f"se esperaban {total} tarjetas, hay {len(tarjetas)}"
    assert html.count('data-partido-id="') >= total


# ── 2 · Parrilla 1X2 con P′ · Mercado · Momio en cada celda ──────────────────
def test_match_card_parrilla_1x2_tres_celdas(html: str) -> None:
    tarjetas = _tarjetas(html)
    assert tarjetas, "sin tarjetas no hay parrilla que auditar"
    for tarjeta in tarjetas:
        assert tarjeta.count('data-clave="') == 3, "cada tarjeta declara 1 · X · 2"
        assert len(re.findall(r'<div class="mc-celda(?=[ "])', tarjeta)) == 3
        for clave in ("LOCAL", "EMPATE", "VISITANTE"):
            _celda(tarjeta, clave)
        assert 'mc-etiqueta">P′' in tarjeta
        assert 'mc-etiqueta">Mkt' in tarjeta
        assert 'mc-etiqueta">@' in tarjeta


# ── 3 · Acceso al modal 32V: un botón por tarjeta y un solo cascarón ─────────
def test_match_card_boton_32v_y_cascaron_unico(html: str) -> None:
    tarjetas = _tarjetas(html)
    assert html.count('class="btn-ver-44-vars"') == len(tarjetas)
    assert html.count('id="modal-44-variables"') == 1, "el ancla de red es única"
    assert html.count('id="vars44-cuerpo"') == 1
    assert html.count('id="vars44-titulo"') == 1
    assert re.search(r'data-vars44-url="/visor/partido/[^"]+/variables"', html)


# ── 4 · Contrato de apertura y cierre del modal ──────────────────────────────
def test_match_card_modal_contrato_apertura_cierre(html: str) -> None:
    assert 'role="dialog"' in html
    assert 'aria-modal="true"' in html
    assert 'data-cerrar-modal' in html
    assert re.search(r'id="modal-44-variables"[^>]*hidden', html), (
        "el cascarón nace oculto por atributo, no por estilo calculado"
    )


# ── 5 · Valor: P′ > q_mkt se declara con texto, no solo con color ────────────
def test_match_card_marca_valor_sin_depender_del_color() -> None:
    html = _render(_vista_sintetica())
    tarjeta = _tarjetas(html)[0]

    local = _celda(tarjeta, "LOCAL")
    assert 'data-valor="true"' in local
    assert "↑ VALOR" in local
    assert "COLD START" not in local

    visita = _celda(tarjeta, "VISITANTE")
    assert 'data-valor="false"' in visita
    assert "↑ VALOR" not in visita


# ── 6 · Acierto: la celda del resultado real se marca aparte del valor ───────
def test_match_card_marca_acierto_en_la_celda_correcta() -> None:
    html = _render(_vista_sintetica())
    tarjeta = _tarjetas(html)[0]

    assert 'data-acierto="true"' in _celda(tarjeta, "LOCAL")
    assert 'data-acierto="false"' in _celda(tarjeta, "EMPATE")
    assert 'data-acierto="false"' in _celda(tarjeta, "VISITANTE")


# ── 6-bis · Cold Start: el veredicto de valor se suprime ────────────────────
def test_match_card_cold_start_suprime_el_veredicto_de_valor() -> None:
    """Con S = 0 la P′ es el prior de ignorancia: P′ > q_mkt no es una oportunidad."""
    vista = _vista_sintetica()
    vista["jornadas"][0]["partidos"][0]["es_cold_start"] = True
    html = _render(vista)
    tarjeta = _tarjetas(html)[0]

    local = _celda(tarjeta, "LOCAL")  # P′ 51.2 > Mkt 44.1: "valor" sólo en apariencia
    assert "↑ VALOR" not in local, "un prior uniforme no puede declarar valor"
    assert 'data-valor="false"' in local
    assert 'data-valor-suprimido="cold_start"' in local
    assert "COLD START" in local
    assert "no se declara valor" in local

    # El acierto sobrevive: es un hecho consumado, no un veredicto de valor.
    assert 'data-acierto="true"' in local


# ── 6-ter · [REV.2] Vértice del resultado, balón y barras comparativas ──────

@pytest.mark.parametrize(
    ("triada", "vertice"),
    [("P_MAX", "max"), ("P_MID", "mid"), ("P_LOW", "low")],
)
def test_match_card_vertice_mapea_la_clasificacion_canonica(
    triada: str, vertice: str
) -> None:
    """El vértice es transcripción del núcleo: la plantilla no ordena ni compara."""
    vista = _vista_sintetica()
    vista["jornadas"][0]["partidos"][0]["clasificacion_triada"] = triada
    tarjeta = _tarjetas(_render(vista))[0]

    local = _celda(tarjeta, "LOCAL")
    assert f'data-vertice="{vertice}"' in local
    assert "data-vertice" not in _celda(tarjeta, "EMPATE")


def test_match_card_balon_sustituye_al_check(html: str) -> None:
    tarjetas = _tarjetas(html)
    assert tarjetas
    for tarjeta in tarjetas:
        assert tarjeta.count('class="mc-balon"') == 1, "un balón por tarjeta"
        assert 'href="#mc-balon"' in tarjeta
        assert "✓" not in tarjeta, "el checkmark quedó derogado"
    assert html.count('id="mc-balon"') == 1, "el sprite se declara una sola vez"


def test_match_card_barras_pmax_y_mktmax() -> None:
    vista = _vista_sintetica()
    tarjeta = _tarjetas(_render(vista))[0]

    # Caso A: la celda del resultado es P′max y además MKTmax ⇒ lleva ambas barras.
    local = _celda(tarjeta, "LOCAL")
    assert 'data-barra="p-max"' in local
    assert 'data-barra-mkt="true"' in local

    # Caso B: el máximo de mercado se desplaza a la visita.
    vista["jornadas"][0]["partidos"][0]["q_visitante"] = 0.55
    tarjeta = _tarjetas(_render(vista))[0]
    local = _celda(tarjeta, "LOCAL")
    visita = _celda(tarjeta, "VISITANTE")

    assert 'data-barra="p-max"' in local
    assert "data-barra-mkt" not in local.split(">", 1)[0]
    assert 'data-barra-mkt="true"' in visita


def test_match_card_cold_start_no_tiñe_el_vertice() -> None:
    vista = _vista_sintetica()
    partido = vista["jornadas"][0]["partidos"][0]
    partido["es_cold_start"] = True
    partido["q_visitante"] = 0.55
    tarjeta = _tarjetas(_render(vista))[0]

    local = _celda(tarjeta, "LOCAL")
    assert 'data-vertice="cold_start"' in local
    assert 'class="mc-balon"' in local
    assert 'data-barra="p-max"' not in tarjeta, "un prior de ignorancia no ordena vértices"
    assert 'data-barra-mkt="true"' in _celda(tarjeta, "VISITANTE"), (
        "el consenso de mercado es un hecho y conserva su barra"
    )


def test_match_card_sin_riel_de_valor() -> None:
    css = (PROJECT_ROOT / "app" / "static" / "css" / "theme.css").read_text(
        encoding="utf-8"
    )
    assert ".mc-celda-valor" not in css, "el riel verde de valor quedó derogado"


# ── 7 · Tetralogía fáctica: cuatro luces, cero EPIST ────────────────────────
def test_match_card_tetralogia_sin_epist(html: str) -> None:
    tarjetas = _tarjetas(html)
    assert tarjetas
    for tarjeta in tarjetas:
        assert tarjeta.count('class="hud-semaforo"') == 4
        for clave in ("OPTA", "SEDE", "H2H", "CTX"):
            assert f'data-semaforo="{clave}"' in tarjeta
    assert 'data-semaforo="EPIST"' not in html
    assert 'data-semaforo="epist"' not in html


# ── 8 · Brier Vars: guion con explicación, jamás un cero fabricado ──────────
def test_match_card_brier_vars_declara_el_vacio(html: str) -> None:
    tarjetas = _tarjetas(html)
    assert tarjetas
    for tarjeta in tarjetas:
        assert "Brier" in tarjeta
        assert 'class="visor-vacio"' in tarjeta
        assert "Pendiente de legislación del motor causal" in tarjeta
        assert "0.0000" not in tarjeta.split("mc-brier", 1)[-1].split("</p>", 1)[0]
    assert html.count('class="visor-vacio"') >= len(tarjetas)


# ── 9 · Cero hex inline en el marcado nuevo ─────────────────────────────────
def test_match_card_sin_hex_inline(html: str) -> None:
    for tarjeta in _tarjetas(html):
        assert not re.search(r"#[0-9A-Fa-f]{3,8}\b", tarjeta), "el color vive en theme.css"


# ── 10 · Paridad con el endpoint canónico ───────────────────────────────────
def test_match_card_paridad_brier_con_endpoint(
    html: str, reporte: Dict[str, Any]
) -> None:
    partido = reporte["jornadas"][0]["partidos"][0]
    assert f"{partido['brier_qbe']:.4f}" in html
    if partido.get("brier_mercado") is not None:
        assert f"{partido['brier_mercado']:.4f}" in html


# ── 11 · Degradación honesta con DTO incompleto ─────────────────────────────
def test_match_card_degrada_sin_explotar() -> None:
    """Sin P′/q_mkt el pintor no compara Undefined: declara el vacío."""
    html = _render(_vista_sintetica(con_1x2=False))
    tarjetas = _tarjetas(html)
    assert len(tarjetas) == 1
    assert 'data-valor="false"' in tarjetas[0]
    assert 'class="visor-vacio"' in tarjetas[0]


# ── Anexo · Fragmento B2 del panel de 32 variables ──────────────────────────
def test_fragmento_vars44_bajo_demanda(cliente, reporte: Dict[str, Any]) -> None:
    partido = reporte["jornadas"][0]["partidos"][0]
    respuesta = cliente.get(f"/visor/partido/{partido['id_partido']}/variables")
    assert respuesta.status_code == 200, respuesta.text[:500]
    html = respuesta.text
    assert "vars44-" in html
    assert 'id="modal-44-variables"' not in html, "el fragmento no duplica el cascarón"


def test_fragmento_vars44_partido_inexistente(cliente) -> None:
    respuesta = cliente.get("/visor/partido/NO-EXISTE/variables")
    assert respuesta.status_code == 404


def _render_panel(partido: Dict[str, Any]) -> str:
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    entorno = Environment(
        loader=FileSystemLoader(str(PROJECT_ROOT / "app" / "templates")),
        autoescape=select_autoescape(["html"]),
    )
    return entorno.get_template("_vars44_panel.html").render(partido=partido, jornada=1)


def test_fragmento_vars44_transcribe_cifras_textuales() -> None:
    """El DTO sirve tasas como cadena ya formateada: son evidencia, no se vacían."""
    partido = {
        "id_partido": "P-009",
        "local": "Equipo Casa",
        "visitante": "Equipo Visita",
        "origen_captura": "EN_VIVO",
        "origen_p_prima": "CAPTURA",
        "atribucion_disponible": True,
        "origen_factores": "analitico_base",
        "atribucion_driver": "🛡️ Defensiva Local (+0.23)",
        "semaforos": {"opta": "VERDE", "sede": "VERDE", "h2h": "VERDE", "ctx": "VERDE"},
        "descomposicion_log": {"delta_ofensiva": -0.0328},
        "variables_44": {
            "total_variables": 2,
            "dimensiones": [
                {
                    "dimension": "T_Vol",
                    "titulo": "Volumen Territorial y Fricción",
                    "conteo": 2,
                    "total_variables": 2,
                    "variables_evaluadas": 1,
                    "tiene_datos": True,
                    "variables": [
                        {
                            "id": "V01",
                            "variable": "Posesión Promedio (%)",
                            "local": None,
                            "visita": None,
                            "z_score": None,
                            "origen": "SIN EVIDENCIA",
                            "estado": "SIN EVIDENCIA",
                        },
                        {
                            "id": "V02",
                            "variable": "Toques en Área Rival",
                            "local": "20.09",
                            "visita": "25.54",
                            "z_score": "1.2345",
                            "origen": "OPTA",
                            "estado": "EVALUADO",
                        },
                    ],
                }
            ],
        },
    }

    html = _render_panel(partido)

    assert "20.09" in html, "la magnitud textual servida no puede degradarse a guion"
    assert "25.54" in html
    assert "1.2345" in html
    assert "−0.0328" in html or "-0.0328" in html
    assert "V01" in html and "V02" in html
    assert "SIN EVIDENCIA" in html
