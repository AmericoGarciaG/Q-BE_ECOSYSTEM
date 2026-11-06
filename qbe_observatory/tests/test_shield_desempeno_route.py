# -*- coding: utf-8 -*-
"""The Shield — Juez Inmutable de Ruta y Navegación de Desempeño.

[DES-QBE-078] [ARCH-1.4.78] · Régimen [DIRGEN-STRICT] · Paso 2 (Juez en RED).

Certifica tres cosas que hoy **no** existen:

1. `GET /` redirige con `301`/`302` y `Location: /desempeno`; la portada pasiva
   deja de servirse.
2. `GET /desempeno` responde `200 OK` con HTML (hoy responde `404 Not Found`).
3. El HTML declara las cuatro pestañas canónicas del Navbar del Observatorio.

Además fija el estado del conmutador: `data-mando-rector` se publica **una sola
vez** por página y su valor por defecto es `qbe`.

Estado esperado en este turno: **RED CONTROLADO** — el router y la plantilla se
materializan en el Paso 3. El Juez no se adapta al código: el código se adapta
al Juez.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import pytest
from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

RUTA_DESEMPENO = "/desempeno"
PESTANAS = ("/desempeno", "/visor", "/consenso", "/backtesting")


def _total_partidos(html: str) -> int:
    """Lee el KPI de partidos auditados del HTML servido."""
    sopa = BeautifulSoup(html, "html.parser")
    nodo = sopa.select_one('[data-kpi="partidos"] .kpi-value')
    assert nodo is not None, "la banda de KPIs no publica el contador de partidos"
    return int(nodo.get_text(" ", strip=True))


@pytest.fixture()
def cliente():
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)


# ── 1 · La raíz es una redirección, no una portada ───────────────────────────
def test_raiz_redirige_a_la_ruta_semantica(cliente) -> None:
    respuesta = cliente.get("/", follow_redirects=False)

    assert respuesta.status_code in (301, 302), (
        "GET / debe redirigir a /desempeno con 301/302; "
        f"respondió {respuesta.status_code} y la portada pasiva sigue viva"
    )

    destino = respuesta.headers.get("location", "")
    assert destino, "la redirección no declara cabecera Location"
    assert urlparse(destino).path == RUTA_DESEMPENO, (
        f"Location debe apuntar a /desempeno; apunta a {destino!r}"
    )


# ── 2 · La ruta semántica existe y sirve HTML ────────────────────────────────
def test_desempeno_responde_200_html(cliente) -> None:
    respuesta = cliente.get(RUTA_DESEMPENO, follow_redirects=False)

    assert respuesta.status_code == 200, (
        f"GET {RUTA_DESEMPENO} debe servir la vista; respondió "
        f"{respuesta.status_code} (la ruta aún no está materializada)"
    )
    assert "text/html" in respuesta.headers.get("content-type", ""), (
        "la vista de desempeño es HTML server-side (Jinja2), no un JSON"
    )
    assert respuesta.text.strip(), "la vista respondió un cuerpo vacío"


# ── 3 · Navbar de cuatro pestañas, ninguna retirada ──────────────────────────
def test_navbar_declara_las_cuatro_pestanas(cliente) -> None:
    respuesta = cliente.get(RUTA_DESEMPENO)
    assert respuesta.status_code == 200, (
        f"sin la vista materializada no hay Navbar que auditar ({respuesta.status_code})"
    )
    html = respuesta.text

    for ruta in PESTANAS:
        patron = r'href="%s(?:\?[^"]*)?"' % re.escape(ruta)
        assert re.search(patron, html), (
            f"el Navbar no declara la pestaña {ruta}: {PESTANAS}"
        )


# ── 4 · El Mando Rector es un estado publicado, no un cálculo del cliente ────
def test_mando_rector_se_publica_una_sola_vez(cliente) -> None:
    html = cliente.get(RUTA_DESEMPENO).text

    assert html.count("data-mando-rector=") == 1, (
        "el conmutador de Mando Rector se declara una sola vez por página"
    )
    assert 'data-mando-rector="qbe"' in html, (
        "el defecto canónico es Q-BE Soberano (P′)"
    )


def test_mando_mercado_es_estado_servido(cliente) -> None:
    respuesta = cliente.get(RUTA_DESEMPENO, params={"mando": "mercado"})

    assert respuesta.status_code == 200, (
        f"la conmutación de mando no puede romper la vista ({respuesta.status_code})"
    )
    assert 'data-mando-rector="mercado"' in respuesta.text, (
        "?mando=mercado debe declararse en el DOM como fuente rectora"
    )


# ── 5 · [REV.3] El combo expone el catálogo canónico de temporadas ───────────
def test_selector_de_temporadas_canonico(cliente) -> None:
    html = cliente.get(RUTA_DESEMPENO).text

    for temporada in ("Todas", "2026_2027 · Actual", "2015_2016", "2023_2024"):
        assert f'value="{temporada}"' in html, f"falta la temporada {temporada!r} en el combo"
    assert html.count('<option value="20') >= 12, (
        "el combo debe exponer las 12 temporadas canónicas de la bóveda"
    )
    assert 'name="temporada"' in html, "el select de temporada debe conservar su contrato"


# ── 6 · [ARCH-1.4.78 · FIX] Enrutador dual: bóveda histórica real ───────────
def test_consulta_historica_2025_2026(cliente) -> None:
    respuesta = cliente.get(RUTA_DESEMPENO, params={"temporada": "2025_2026"})

    assert respuesta.status_code == 200, respuesta.text[:400]
    html = respuesta.text
    assert "no está servida por el snapshot" not in html, (
        "el letrero derogado del enrutamiento mono-bóveda no puede reaparecer"
    )
    assert _total_partidos(html) > 0, (
        "2025_2026 existe en la bóveda histórica: debe portar partidos auditados"
    )
    assert BeautifulSoup(html, "html.parser").select("details.jornada-accordion"), (
        "la parrilla histórica debe renderizar sus jornadas"
    )


def test_modo_todas_agrega_universo_masivo(cliente) -> None:
    respuesta = cliente.get(RUTA_DESEMPENO, params={"temporada": "Todas"})

    assert respuesta.status_code == 200, respuesta.text[:400]
    total = _total_partidos(respuesta.text)
    assert total > 2000, f"«Todas» debe agregar el corpus histórico; hay {total}"
    assert BeautifulSoup(respuesta.text, "html.parser").select("details.jornada-accordion")


def test_temporada_sin_vector_causal_se_declara_vacia(cliente) -> None:
    """2016_2017/2017_2018 no tienen distribuciones P′: se declara, no se rellena."""
    respuesta = cliente.get(RUTA_DESEMPENO, params={"temporada": "2016_2017"})

    assert respuesta.status_code == 200, respuesta.text[:400]
    assert _total_partidos(respuesta.text) == 0
    assert "no está servida por el snapshot" not in respuesta.text
    assert "distribuciones P′" in respuesta.text, (
        "la ausencia de vector causal debe declararse con su motivo"
    )
