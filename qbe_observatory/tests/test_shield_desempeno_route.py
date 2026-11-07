# -*- coding: utf-8 -*-
"""The Shield — Juez Inmutable de Ruta y Navegación de Desempeño.

[DES-QBE-078 · REV.4] [ARCH-1.4.78 · REV.2] · Régimen [DIRGEN-STRICT] · Paso 2
(Juez en RED).

Certifica lo que la vista `GET /desempeno` **debe** servir:

1. `GET /` redirige con `301`/`302` y `Location: /desempeno`; la portada pasiva
   deja de servirse.
2. `GET /desempeno` responde `200 OK` con HTML server-side.
3. El HTML declara las cuatro pestañas canónicas del Navbar del Observatorio.
4. El conmutador se rotula **«Distribución Base»** y el término «Mando Rector»
   desaparece de la UI (§7.4.2 / §7.4.3).
5. Las jornadas nacen **contraídas** y el estado vive en `sessionStorage`
   (§7.4.10).
6. **[REV.4] Banda de 7 macro KPIs.** La ruta publica exactamente siete
   `.kpi-card`: Éxito Pmax, Éxito Pmid, Cobertura Resultado, Brier Q-BE,
   Brier Mercado, Alpha de Desempeño y Partidos Auditados (7.ª, a la derecha).
7. **[REV.4] Contratos DTO C-50.** `DesempenoKPIsOut` / `DesempenoJornadaOut`
   exponen la terna de cobertura y respetan el **Invariante C-50**
   (`cobertura ≡ pmax + pmid`).
8. **[REV.4] Sensibilidad a mando.** `?mando=mercado` conmuta la terna y
   reordena el Brier Mercado a la cuarta posición.
9. **[REV.4] Chip de diagnóstico de vértice.** El binario `RESCATE SÍ / NO`
   (`data-rescate-partido`) queda derogado del DOM de la tarjeta.

Estado esperado en este turno: **RED CONTROLADO** — la producción se ajusta en
el Paso 3. El Juez no se adapta al código: el código se adapta al Juez.
"""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, Dict
from urllib.parse import urlparse

import pytest
from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

RUTA_DESEMPENO = "/desempeno"
PESTANAS = ("/desempeno", "/visor", "/consenso", "/backtesting")


# ── Utilidades de lectura del DOM ────────────────────────────────────────────
def _normalizar_etiqueta(texto: str) -> str:
    """Mayúsculas, sin acentos, sin guiones bajos y con espacios colapsados."""
    limpio = unicodedata.normalize("NFKD", texto)
    limpio = "".join(c for c in limpio if not unicodedata.combining(c))
    return " ".join(limpio.upper().replace("_", " ").split())


def _etiquetas_kpi(sopa) -> list[str]:
    return [
        _normalizar_etiqueta(tarjeta.select_one(".kpi-label").get_text(" ", strip=True))
        for tarjeta in sopa.select(".kpi-card")
    ]


def _total_partidos(html: str) -> int:
    """Lee el KPI de partidos auditados del HTML servido (7.ª tarjeta)."""
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
        "el conmutador de Distribución Base se declara una sola vez por página"
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


# ── 7 · [REV.4] Nomenclatura: la base activa se llama Distribución Base ──────
def test_nomenclatura_distribucion_base(cliente) -> None:
    """§7.4.2 / §7.4.3: el rótulo visible es «Distribución Base»; el viejo no vive."""
    html = cliente.get(RUTA_DESEMPENO).text
    plegado = html.lower()

    assert "distribución base" in plegado, (
        "la barra de comando debe rotular el conmutador como «Distribución Base» "
        "[DES-QBE-078] §7.4.3"
    )
    assert "mando rector" not in plegado, (
        "el término «Mando Rector» quedó derogado en la UI: la base activa se "
        "denomina «Distribución Base» [DES-QBE-078] §7.4.3"
    )


# ── 8 · [REV.4] Las jornadas nacen contraídas (§7.4.10) ─────────────────────
def test_jornadas_nacen_contraidas(cliente) -> None:
    """Ningún `<details class="jornada-accordion">` se sirve con `open`."""
    for parametros in ({}, {"mando": "mercado"}):
        html = cliente.get(RUTA_DESEMPENO, params=parametros).text
        detalles = BeautifulSoup(html, "html.parser").select(
            "details.jornada-accordion"
        )
        assert detalles, "la parrilla debe renderizar al menos una jornada"

        abiertas = [detalle for detalle in detalles if detalle.has_attr("open")]
        assert not abiertas, (
            f"con {parametros or 'los filtros por defecto'} el HTML inicial abre "
            f"{len(abiertas)} de {len(detalles)} jornadas: todas deben nacer "
            "contraídas, sin el atributo `open` [DES-QBE-078] §7.4.10"
        )


# ── 9 · [REV.4] El estado del acordeón vive en la sesión, no en el navegador ─
def test_acordeon_en_session_storage_y_reset_explicito(cliente) -> None:
    html = cliente.get(RUTA_DESEMPENO).text

    assert "sessionStorage" in html, (
        "el estado del acordeón se persiste en `sessionStorage` [DES-QBE-078] §7.4.10"
    )
    assert "localStorage" not in html, (
        "`localStorage` queda prohibido: el foco de auditoría es de la sesión, "
        "no del navegador [DES-QBE-078] §7.4.10"
    )
    assert "qbe_desempeno_acordeones_abiertos" in html, (
        "la clave canónica de persistencia debe publicarse en el HTML"
    )
    assert 'data-acordeones-reset="1"' in html, (
        "«Restablecer» debe declarar `data-acordeones-reset=\"1\"` para limpiar el "
        "estado y forzar el cierre de todas las jornadas [DES-QBE-078] §7.4.10"
    )


# ── 10 · [REV.4] Cuadrícula exacta de 7 macro KPIs en la ruta ────────────────
def test_banda_de_siete_kpis_en_la_ruta(cliente) -> None:
    respuesta = cliente.get(RUTA_DESEMPENO)

    assert respuesta.status_code == 200, respuesta.text[:400]
    sopa = BeautifulSoup(respuesta.text, "html.parser")
    tarjetas = sopa.select(".kpi-card")

    assert len(tarjetas) == 7, (
        f"la banda debe publicar exactamente 7 `.kpi-card`; hay {len(tarjetas)} "
        "— la cuadrícula de 5 quedó derogada [DES-QBE-078] §7.4.11"
    )
    etiquetas = _etiquetas_kpi(sopa)
    assert etiquetas[0] in {"EXITO PMAX", "EXITO P MAX"}, etiquetas
    assert etiquetas[1] in {"EXITO PMID", "EXITO P MID"}, etiquetas
    assert etiquetas[2] == "COBERTURA RESULTADO", etiquetas
    assert etiquetas[6] == "PARTIDOS AUDITADOS", (
        f"la 7.ª tarjeta debe ser PARTIDOS AUDITADOS; es {etiquetas[6]!r}"
    )


# ── 11 · [REV.4] El chip de cobertura sustituye al binario ───────────────────
def test_chip_de_cobertura_sustituye_al_binario(cliente) -> None:
    html = cliente.get(RUTA_DESEMPENO).text
    sopa = BeautifulSoup(html, "html.parser")

    assert sopa.select("article.mc-card"), "la parrilla debe renderizar tarjetas"
    assert not sopa.select("[data-rescate-partido]"), (
        "el chip binario `data-rescate-partido` quedó derogado [DES-QBE-078] §7.4.13"
    )

    chips = sopa.select(".mc-chip-cobertura")
    assert chips, (
        "el pie de tarjeta debe publicar `.mc-chip-cobertura` con el diagnóstico "
        "de vértice [DES-QBE-078] §7.4.13"
    )
    for chip in chips:
        texto = chip.get_text(" ", strip=True)
        assert any(
            literal in texto
            for literal in (
                "COB: PRIMARIO",
                "COB: RESCATE",
                "COB: RUPTURA",
                "COB: COLD START",
            )
        ), f"chip de cobertura fuera de la legislación: {texto!r}"


# ── 12 · [REV.4] Contratos DTO del Invariante C-50 ──────────────────────────
def _partido_dto(**overrides: Any) -> Dict[str, Any]:
    """Partido sintético con P′ mejor que el consenso y resultado en `r_max`."""
    partido: Dict[str, Any] = {
        "id_partido": "SP50-01",
        "local": "Necaxa",
        "visitante": "FC Juárez",
        "marcador": "2 - 1",
        "resultado_real": "LOCAL",
        "es_cold_start": False,
        "suficiencia_s_i": 3,
        "p_local": 0.70,
        "p_empate": 0.20,
        "p_visitante": 0.10,
        "q_local": 0.50,
        "q_empate": 0.30,
        "q_visitante": 0.20,
        "momios": {"L": 1.71, "E": 3.85, "V": 4.60},
        "r_max": "LOCAL",
        "r_mid": "EMPATE",
        "r_low": "VISITANTE",
        "clasificacion_triada": "P_MAX",
        "semaforos": {},
        "atribucion_disponible": False,
        "atribucion_driver": None,
        "variables_44": {},
    }
    partido.update(overrides)
    return partido


def _partido_c50(id_partido: str, resultado: str, q: tuple) -> Dict[str, Any]:
    """Partido coherente con el orden fiduciario fijo de `_calibracion_c50`."""
    clasificacion = {
        "LOCAL": "P_MAX",
        "EMPATE": "P_MID",
        "VISITANTE": "P_LOW",
    }[resultado]
    return _partido_dto(
        id_partido=id_partido,
        resultado_real=resultado,
        p_local=0.50,
        p_empate=0.30,
        p_visitante=0.20,
        q_local=q[0],
        q_empate=q[1],
        q_visitante=q[2],
        clasificacion_triada=clasificacion,
    )


def _calibracion_sintetica() -> Dict[str, Any]:
    return {
        "fuente": {"temporada": "2026_2027 · Actual"},
        "error": None,
        "jornadas": [
            {"jornada": 1, "total_partidos": 1, "partidos": [_partido_dto()]}
        ],
    }


def _calibracion_c50() -> Dict[str, Any]:
    """Universo de 4 partidos con cobertura Q-BE 50+25 y mercado 75+25."""
    partidos = [
        _partido_c50("C50-1", "LOCAL", (0.50, 0.30, 0.20)),      # qbe Pmax · mkt Pmax
        _partido_c50("C50-2", "EMPATE", (0.20, 0.30, 0.50)),     # qbe Pmid · mkt Pmid
        _partido_c50("C50-3", "VISITANTE", (0.40, 0.10, 0.50)),  # qbe Plow · mkt Pmax
        _partido_c50("C50-4", "LOCAL", (0.50, 0.30, 0.20)),      # qbe Pmax · mkt Pmax
    ]
    return {
        "fuente": {"temporada": "2026_2027 · Actual"},
        "error": None,
        "jornadas": [{"jornada": 1, "total_partidos": 4, "partidos": partidos}],
    }


def test_dto_kpis_publica_contrato_c50(monkeypatch) -> None:
    """`DesempenoKPIsOut` y `DesempenoJornadaOut` deben portar la terna C-50."""
    from app.services import desempeno_view

    monkeypatch.setattr(
        desempeno_view, "cargar_vista_calibracion", _calibracion_c50
    )
    vista = desempeno_view.cargar_vista_desempeno(mando="qbe", devig="proporcional")

    kpis = vista.get("kpis") or {}
    for campo in (
        "pmax_success_rate",
        "pmid_success_rate",
        "cobertura_resultado_rate",
        "brier_qbe",
        "brier_mercado",
        "alpha_desempeno",
        "total_partidos",
        "total_jornadas",
        "metodo_devig",
        "mando_rector",
        "temporadas_disponibles",
    ):
        assert campo in kpis, (
            f"DesempenoKPIsOut debe publicar `{campo}` [ARCH-1.4.78] §18.2"
        )

    assert kpis["total_partidos"] == 4
    assert kpis["total_jornadas"] == 1
    assert kpis["metodo_devig"] == "proporcional"
    assert kpis["mando_rector"] == "qbe"
    assert "2026_2027 · Actual" in kpis["temporadas_disponibles"]

    jornada = vista["jornadas"][0]
    for campo in (
        "numero",
        "etiqueta",
        "total_partidos",
        "pmax_success_rate",
        "pmid_success_rate",
        "cobertura_resultado_rate",
        "alpha",
        "brier_qbe",
        "brier_mkt",
        "partidos",
    ):
        assert campo in jornada, (
            f"DesempenoJornadaOut debe publicar `{campo}` [ARCH-1.4.78] §18.2"
        )
    assert jornada["numero"] == 1
    assert jornada["total_partidos"] == 4


def test_invariante_c50_global_y_por_jornada(monkeypatch) -> None:
    """`cobertura ≡ pmax + pmid` en el global y en cada jornada."""
    from app.services import desempeno_view

    monkeypatch.setattr(
        desempeno_view, "cargar_vista_calibracion", _calibracion_c50
    )

    for mando, pmax_esperado in (("qbe", 50.0), ("mercado", 75.0)):
        vista = desempeno_view.cargar_vista_desempeno(
            mando=mando, devig="proporcional"
        )
        kpis = vista["kpis"]
        pmax = kpis.get("pmax_success_rate")
        pmid = kpis.get("pmid_success_rate")
        cobertura = kpis.get("cobertura_resultado_rate")
        assert pmax is not None and pmid is not None and cobertura is not None, (
            "DesempenoKPIsOut debe publicar la terna de cobertura [ARCH-1.4.78] §18.2"
        )
        assert pmax == pytest.approx(pmax_esperado, abs=1e-5)
        assert pmid == pytest.approx(25.0, abs=1e-5)
        assert cobertura == pytest.approx(pmax + pmid, abs=1e-5), (
            f"Invariante C-50 violado en el global con base {mando!r}"
        )

        jornada = vista["jornadas"][0]
        j_pmax = jornada.get("pmax_success_rate")
        j_pmid = jornada.get("pmid_success_rate")
        j_cob = jornada.get("cobertura_resultado_rate")
        assert j_pmax is not None and j_pmid is not None and j_cob is not None, (
            "DesempenoJornadaOut debe publicar la terna de cobertura §18.2"
        )
        assert j_cob == pytest.approx(j_pmax + j_pmid, abs=1e-5), (
            f"Invariante C-50 violado en la jornada con base {mando!r}"
        )


def test_mando_mercado_reactiva_la_terna(monkeypatch) -> None:
    """La terna evalúa el consenso des-marginado cuando la base es `mercado`."""
    from app.services import desempeno_view

    monkeypatch.setattr(
        desempeno_view, "cargar_vista_calibracion", _calibracion_c50
    )
    qbe = desempeno_view.cargar_vista_desempeno(mando="qbe", devig="proporcional")
    mercado = desempeno_view.cargar_vista_desempeno(
        mando="mercado", devig="proporcional"
    )

    assert qbe["kpis"].get("mando_rector") == "qbe"
    assert mercado["kpis"].get("mando_rector") == "mercado"

    assert qbe["kpis"].get("pmax_success_rate") == pytest.approx(50.0, abs=1e-5)
    assert mercado["kpis"].get("pmax_success_rate") == pytest.approx(75.0, abs=1e-5)
    assert qbe["kpis"].get("cobertura_resultado_rate") == pytest.approx(75.0, abs=1e-5)
    assert mercado["kpis"].get("cobertura_resultado_rate") == pytest.approx(100.0, abs=1e-5)


# ── 13 · El DTO de partido publica Alpha y Rescate interno (§18.2) ──────────
def test_dto_de_partido_publica_alpha_y_rescate(monkeypatch) -> None:
    """`DesempenoPartidoOut` conserva `alpha_partido_pct` y `rescate_partido`."""
    from app.services import desempeno_view

    monkeypatch.setattr(
        desempeno_view, "cargar_vista_calibracion", _calibracion_sintetica
    )
    vista = desempeno_view.cargar_vista_desempeno(mando="qbe", devig="proporcional")

    partidos = [partido for jornada in vista["jornadas"] for partido in jornada["partidos"]]
    assert partidos, "el DTO sintético debe producir al menos una tarjeta"

    for partido in partidos:
        assert "alpha_partido_pct" in partido, (
            "DesempenoPartidoOut debe publicar `alpha_partido_pct` "
            "[ARCH-1.4.78] §18.2"
        )
        assert "rescate_partido" in partido, (
            "DesempenoPartidoOut debe publicar `rescate_partido` "
            "[ARCH-1.4.78] §18.2"
        )
        assert isinstance(partido["rescate_partido"], bool), (
            "`rescate_partido` es un booleano, no un texto ni un `None`"
        )

    assert isinstance(partidos[0]["alpha_partido_pct"], float), (
        "con par de Briers medible el Alpha del partido es numérico: "
        f"{partidos[0]['alpha_partido_pct']!r}"
    )
