# -*- coding: utf-8 -*-
"""The Shield — Juez Inmutable de Semántica Visual del Mando Rector.

[DES-QBE-078] [ARCH-1.4.78] · Régimen [DIRGEN-STRICT] · Paso 2 (Juez en RED).

Certifica la verdad semántica de la vista `/desempeno` mediante parseo de la
plantilla `app/templates/desempeno.html` con contexto sintético (no depende de
la base de datos) y del contrato HTTP para el Fail-Loud de dominio:

1. **Inversión de barras.** Con `mando=qbe` la barra superior pertenece a P_max
   Q-BE y la inferior al máximo del consenso; con `mando=mercado` se invierte.
2. **Coloreado del balón.** El marco de la celda ganadora lo dicta la fuente
   rectora: si en Modo Mercado gana el favorito del casino, recibe el vértice
   `max` (`--success`) aunque Q-BE lo hubiera clasificado `low` (`--danger`).
3. **Fail-Loud.** Un casino fuera de dominio o un de-vig distinto de `shin` /
   `proporcional` lanzan `ValueError`; jamás se degrada en silencio.

Estado esperado en este turno: **RED CONTROLADO** — la plantilla y el router se
materializan en el Paso 3. El Juez no se adapta al código: el código se adapta
al Juez.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest
from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

TITULO = "Desempeño y Coberturas Probabilísticas — Q-BE Observatory"
PLANTILLA = PROJECT_ROOT / "app" / "templates" / "desempeno.html"
CELDAS = ("LOCAL", "EMPATE", "VISITANTE")

#: `[DES-QBE-078 · REV.3]` Catálogo canónico de temporadas (espejo del servicio).
TEMPORADAS_CANONICAS = [
    "Todas",
    "2026_2027 · Actual",
    "2025_2026",
    "2024_2025",
    "2023_2024",
    "2022_2023",
    "2021_2022",
    "2020_2021",
    "2019_2020",
    "2018_2019",
    "2017_2018",
    "2016_2017",
    "2015_2016",
]


# ── DTO sintético del contrato [ARCH-1.4.78] §18.2 ───────────────────────────
def _partido(**overrides: Any) -> Dict[str, Any]:
    """Tarjeta base: P_max Q-BE = LOCAL; max q_mkt = VISITANTE; gana LOCAL."""
    partido: Dict[str, Any] = {
        "id_partido": "P-014-01",
        "local": "Necaxa",
        "visitante": "FC Juárez",
        "marcador": "2 - 1",
        "resultado_real": "LOCAL",
        "brier_qbe": 0.2886,
        "brier_mercado": 0.3053,
        "es_cold_start": False,
        "suficiencia_s_i": 3,
        "p_local": 0.48,
        "p_empate": 0.25,
        "p_visitante": 0.27,
        "q_local": 0.30,
        "q_empate": 0.28,
        "q_visitante": 0.42,
        "momios": {"L": 1.71, "E": 3.85, "V": 4.60},
        "r_max": "LOCAL",
        "r_mid": "VISITANTE",
        "r_low": "EMPATE",
        "vertice_qbe": "max",
        "vertice_mercado": "mid",
        "shin_z": 0.0412,
        "spread_cuotas": 0.0625,
        "semaforos": {
            "opta": "VERDE",
            "sede": "AMARILLO",
            "h2h": "VERDE",
            "ctx": "VERDE",
        },
        "atribucion_disponible": True,
        "atribucion_driver": "🛡️ Defensiva Local (+0.23)",
        "variables_44": {"dimensiones": [], "total_variables": 32},
    }
    partido.update(overrides)
    return partido


def _vista(mando: str = "qbe", partido: Dict[str, Any] | None = None) -> Dict[str, Any]:
    partido = partido if partido is not None else _partido()
    return {
        "mando": mando,
        "temporadas_disponibles": list(TEMPORADAS_CANONICAS),
        "filtros": {
            "temporada": "2026_2027 · Actual",
            "jornada_min": 1,
            "jornada_max": 15,
            "jornadas": list(range(1, 16)),
            "fuentes": ["caliente", "novibet", "betway", "footystats"],
            "fuentes_disponibles": ["caliente", "novibet", "betway", "footystats"],
            "devig": "shin",
        },
        "kpis": {
            "total_partidos": 134,
            "n_jornadas": 15,
            "n_mercado": 134,
            "brier_qbe": 0.2169,
            "brier_mercado": 0.2106,
            "alpha_desempeno_pct": -2.99,
            "tasa_rescate_pct": 74.6,
        },
        "jornadas": [
            {
                "jornada": 14,
                "total_partidos": 1,
                "brier_qbe": 0.2886,
                "brier_mercado": 0.3053,
                "alpha_pct": -5.47,
                "tasa_rescate_pct": 100.0,
                "partidos": [partido],
            }
        ],
        "error": None,
    }


# ── Render y utilidades DOM ──────────────────────────────────────────────────
def _render(vista: Dict[str, Any]) -> str:
    if not PLANTILLA.exists():
        pytest.fail(
            "Falta la plantilla canónica app/templates/desempeno.html: "
            "el Paso 3 debe materializar [DES-QBE-078] antes de este Juez."
        )

    from jinja2 import Environment, FileSystemLoader, select_autoescape

    entorno = Environment(
        loader=FileSystemLoader(str(PROJECT_ROOT / "app" / "templates")),
        autoescape=select_autoescape(["html"]),
    )
    return entorno.get_template("desempeno.html").render(titulo=TITULO, vista=vista)


def _tarjeta(html: str):
    tarjetas = BeautifulSoup(html, "html.parser").select("article.mc-card")
    assert len(tarjetas) == 1, (
        f"se esperaba una única tarjeta de partido en la parrilla; hay {len(tarjetas)}"
    )
    return tarjetas[0]


def _celdas(tarjeta) -> Dict[str, Any]:
    celdas = {celda.get("data-clave"): celda for celda in tarjeta.select("div.mc-celda")}
    for clave in CELDAS:
        assert clave in celdas, f"la tarjeta no declara la celda {clave}"
    return celdas


def _fuente_barra(celda, atributo: str):
    return celda.get(atributo)


def _clases(celda) -> List[str]:
    return list(celda.get("class") or [])


# ── 1 · El Mando Rector es el estado que gobierna la tarjeta ─────────────────
def test_mando_rector_publicado_una_sola_vez() -> None:
    for mando in ("qbe", "mercado"):
        html = _render(_vista(mando))

        assert html.count("data-mando-rector=") == 1, (
            "el conmutador se declara una sola vez por página (cero estado espejo)"
        )
        assert f'data-mando-rector="{mando}"' in html, (
            f"vista.mando={mando!r} debe transcribirse al DOM"
        )


# ── 2 · Inversión de las barras comparativas de casilla ──────────────────────
def test_inversion_de_barras_segun_el_mando() -> None:
    qbe = _tarjeta(_render(_vista("qbe")))
    celdas = _celdas(qbe)

    assert _fuente_barra(celdas["LOCAL"], "data-barra-sup") == "qbe", (
        "en Modo Q-BE la barra superior (--text) es P_max Q-BE y vive en r_max"
    )
    assert _fuente_barra(celdas["VISITANTE"], "data-barra-inf") == "mercado", (
        "en Modo Q-BE la barra inferior (--muted) es el máximo del consenso"
    )
    assert _fuente_barra(celdas["EMPATE"], "data-barra-sup") is None, (
        "la celda sin máximo no porta barra superior"
    )
    assert _fuente_barra(celdas["EMPATE"], "data-barra-inf") is None, (
        "la celda sin máximo no porta barra inferior"
    )
    assert len(qbe.select("[data-barra-sup]")) == 1, "una sola barra superior por tarjeta"
    assert len(qbe.select("[data-barra-inf]")) == 1, "una sola barra inferior por tarjeta"

    mercado = _tarjeta(_render(_vista("mercado")))
    celdas = _celdas(mercado)

    assert _fuente_barra(celdas["VISITANTE"], "data-barra-sup") == "mercado", (
        "en Modo Mercado la barra superior (--text) es max q_mkt"
    )
    assert _fuente_barra(celdas["LOCAL"], "data-barra-inf") == "qbe", (
        "en Modo Mercado la barra inferior (--muted) es P_max Q-BE"
    )

    # Inversión estricta: la fuente rectora nunca ocupa la barra subordinada.
    assert 'data-barra-sup="qbe"' not in str(mercado), (
        "el mando invertido no puede conservar la jerarquía de Q-BE"
    )
    assert 'data-barra-sup="mercado"' not in str(qbe), (
        "el mando Q-BE no puede ceder la barra superior al consenso"
    )


def test_una_celda_puede_portar_ambas_barras() -> None:
    partido = _partido(q_local=0.55, q_empate=0.25, q_visitante=0.20)
    celdas = _celdas(_tarjeta(_render(_vista("qbe", partido))))

    assert _fuente_barra(celdas["LOCAL"], "data-barra-sup") == "qbe"
    assert _fuente_barra(celdas["LOCAL"], "data-barra-inf") == "mercado"
    assert _fuente_barra(celdas["EMPATE"], "data-barra-sup") is None
    assert _fuente_barra(celdas["EMPATE"], "data-barra-inf") is None


# ── 3 · El balón lo tiñe la fuente rectora, no Q-BE ──────────────────────────
def test_balon_se_tine_con_la_fuente_rect_activa() -> None:
    """Gana LOCAL: favorito del casino, pero P_LOW en la lectura soberana."""
    partido = _partido(
        p_local=0.15,
        p_empate=0.25,
        p_visitante=0.60,
        q_local=0.60,
        q_empate=0.22,
        q_visitante=0.18,
        r_max="VISITANTE",
        r_mid="EMPATE",
        r_low="LOCAL",
        vertice_qbe="low",
        vertice_mercado="max",
    )

    qbe = _celdas(_tarjeta(_render(_vista("qbe", partido))))
    assert qbe["LOCAL"].get("data-acierto") == "true", "el balón marca el hecho consumado"
    assert qbe["LOCAL"].get("data-vertice") == "low", (
        "en Modo Q-BE el ganador cae en P_LOW: Ruptura Residual"
    )
    assert "mc-celda-acierto" in _clases(qbe["LOCAL"])
    assert qbe["LOCAL"].select_one(".mc-balon") is not None
    assert qbe["EMPATE"].select_one(".mc-balon") is None, "un balón por tarjeta"

    mercado = _celdas(_tarjeta(_render(_vista("mercado", partido))))
    assert mercado["LOCAL"].get("data-vertice") == "max", (
        "en Modo Mercado el ganador es el favorito del casino: Acierto Mercado"
    )
    assert "mc-celda-acierto" in _clases(mercado["LOCAL"])
    assert mercado["LOCAL"].select_one(".mc-balon") is not None
    assert qbe["LOCAL"].get("data-vertice") != mercado["LOCAL"].get("data-vertice"), (
        "el vértice es función del mando, no del resultado"
    )

    # El literal `max` del acierto primario está atado a --success en la hoja.
    css = (PROJECT_ROOT / "app" / "static" / "css" / "theme.css").read_text(
        encoding="utf-8"
    )
    for vertice, token in (("max", "--success"), ("mid", "--accent"), ("low", "--danger")):
        bloque = re.search(
            r'\.mc-celda-acierto\[data-vertice="%s"\]\s*\{([^}]*)\}' % vertice, css
        )
        assert bloque, f"falta la regla cromática del vértice {vertice}"
        assert token in bloque.group(1), (
            f"el vértice {vertice} debe pintarse con {token}"
        )


# ── 4 · Cold Start: se suprime el veredicto, no el hecho ─────────────────────
def test_cold_start_suprime_el_veredicto_y_conserva_el_balon() -> None:
    partido = _partido(
        es_cold_start=True,
        suficiencia_s_i=0,
        p_local=1 / 3,
        p_empate=1 / 3,
        p_visitante=1 / 3,
        q_local=None,
        q_empate=None,
        q_visitante=None,
        brier_mercado=None,
        vertice_qbe="cold_start",
        vertice_mercado=None,
    )
    tarjeta = _tarjeta(_render(_vista("qbe", partido)))
    celdas = _celdas(tarjeta)
    texto = tarjeta.get_text(" ", strip=True)

    assert tarjeta.get("data-cold-start") == "true", "S = 0 se declara en la tarjeta"
    assert "Cold Start" in texto and "S = 0" in texto
    assert "SIN EVIDENCIA" in texto, "sin cuotas, el mercado se declara vacío"
    assert "0.0%" not in texto, "un cero fabricado es una mentira visual"
    assert tarjeta.select("[data-barra-sup]") == [], (
        "sin evidencia fáctica no hay barra Q-BE superior que ordenar"
    )
    assert tarjeta.select("[data-barra-inf]") == [], (
        "sin cuotas tampoco hay barra de consenso"
    )
    assert celdas["LOCAL"].get("data-vertice") == "cold_start", (
        "el hecho se marca; el vértice fiduciario no se tiñe"
    )
    assert celdas["LOCAL"].select_one(".mc-balon") is not None, (
        "el partido existió aunque S = 0"
    )


# ── 5 · Asimetría informativa del pie ────────────────────────────────────────
def test_asimetria_informativa_del_pie() -> None:
    qbe = _tarjeta(_render(_vista("qbe")))

    assert len(qbe.select("[data-semaforo]")) == 4, "tetralogía fáctica completa"
    assert qbe.select_one(".btn-ver-44-vars") is not None, "acceso al modal 32V"
    assert qbe.select("[data-shin-z]") == []
    assert qbe.select("[data-spread-cuotas]") == []

    mercado = _tarjeta(_render(_vista("mercado")))

    shin = mercado.select_one("[data-shin-z]")
    spread = mercado.select_one("[data-spread-cuotas]")
    assert shin is not None, "Modo Mercado publica el z de Shin del consenso"
    assert spread is not None, "Modo Mercado publica el spread inter-casinos"
    assert "0.0412" in str(shin.get("data-shin-z")), "el z se transcribe del DTO"
    assert "0.0625" in str(spread.get("data-spread-cuotas")), (
        "el spread se transcribe del DTO"
    )
    assert mercado.select("[data-semaforo]") == [], "el pie conmuta, no duplica"
    assert mercado.select_one(".btn-ver-44-vars") is None


# ── 6 · Banda de macro KPIs unificados ───────────────────────────────────────
def test_banda_de_macro_kpis_transcribe_el_universo() -> None:
    sopa = BeautifulSoup(_render(_vista("qbe")), "html.parser")
    kpis = {
        nodo.get("data-kpi"): nodo.get_text(" ", strip=True)
        for nodo in sopa.select("[data-kpi]")
    }

    assert set(kpis) >= {"partidos", "brier-qbe", "brier-mercado", "alpha", "rescate"}, (
        f"faltan macro KPIs canónicos: {sorted(kpis)}"
    )
    assert "134" in kpis["partidos"]
    assert "0.2169" in kpis["brier-qbe"]
    assert "0.2106" in kpis["brier-mercado"]
    assert "2.99" in kpis["alpha"] and "%" in kpis["alpha"]
    assert "74.6" in kpis["rescate"] and "%" in kpis["rescate"]


# ── 8 · [REV.3] Combo canónico de temporadas ────────────────────────────────
def test_selector_de_temporadas_canonico() -> None:
    sopa = BeautifulSoup(_render(_vista("qbe")), "html.parser")
    opciones = [opcion.get("value") for opcion in sopa.select("select[name='temporada'] option")]

    assert len(opciones) >= 12, f"el combo debe exponer ≥ 12 temporadas; hay {opciones}"
    for esperada in ("Todas", "2026_2027 · Actual", "2023_2024", "2015_2016"):
        assert esperada in opciones, f"falta la temporada canónica {esperada!r}"
    assert any(opcion.has_attr("selected") for opcion in sopa.select("select[name='temporada'] option")), (
        "el combo debe marcar la temporada solicitada"
    )


# ── 9 · [REV.3] Encabezado de jornada: Rescate + Alpha + Brier bicolor ──────
def _vista_jornadas_bicolor(mando: str = "qbe") -> Dict[str, Any]:
    vista = _vista(mando)
    partido = _partido()
    vista["jornadas"] = [
        {
            "jornada": 1,
            "total_partidos": 1,
            "brier_qbe": 0.2000,
            "brier_mercado": 0.3000,
            "alpha_pct": -50.0,
            "tasa_rescate_pct": 80.0,
            "partidos": [partido],
        },
        {
            "jornada": 2,
            "total_partidos": 1,
            "brier_qbe": 0.4000,
            "brier_mercado": 0.1000,
            "alpha_pct": 300.0,
            "tasa_rescate_pct": 20.0,
            "partidos": [partido],
        },
    ]
    return vista


def _clases_brier(barra, fuente: str) -> List[str]:
    nodo = barra.select_one(f'[data-brier="{fuente}"]')
    assert nodo is not None, f"falta el Brier {fuente!r} en la barra de jornada"
    return list(nodo.get("class") or [])


def test_encabezados_de_jornada_alpha_rescate_y_bicolor() -> None:
    sopa = BeautifulSoup(_render(_vista_jornadas_bicolor("qbe")), "html.parser")
    barras = sopa.select(".jornada-header-bar")
    assert len(barras) == 2

    for barra in barras:
        texto = barra.get_text(" ", strip=True)
        assert "Alpha:" in texto, "cada jornada declara su Alpha"
        assert "Rescate:" in texto, "cada jornada declara su Tasa de Rescate"

    # J1: Q-BE 0.2000 < Mkt 0.3000 ⇒ acento para Q-BE, gris para mercado.
    assert "text-accent" in _clases_brier(barras[0], "qbe")
    assert "text-muted" in _clases_brier(barras[0], "mercado")
    # J2: Mkt 0.1000 < Q-BE 0.4000 ⇒ acento para mercado, gris para Q-BE.
    assert "text-accent" in _clases_brier(barras[1], "mercado")
    assert "text-muted" in _clases_brier(barras[1], "qbe")

    for barra in barras:
        assert not (
            "text-accent" in _clases_brier(barra, "qbe")
            and "text-accent" in _clases_brier(barra, "mercado")
        ), "el acento es exclusivo del Brier de menor error (salvo empate exacto)"

    # El Mando Rector lidera la posición: Q-BE a la izquierda en Modo Q-BE.
    assert [nodo.get("data-brier") for nodo in barras[0].select("[data-brier]")] == ["qbe", "mercado"]

    mercado = BeautifulSoup(_render(_vista_jornadas_bicolor("mercado")), "html.parser")
    barra_mercado = mercado.select(".jornada-header-bar")[0]
    assert [nodo.get("data-brier") for nodo in barra_mercado.select("[data-brier]")] == ["mercado", "qbe"]


# ── 10 · [REV.3] Banda de KPIs: orden por mando y bicolor ───────────────────
def test_banda_kpis_bicolor_y_orden_por_mando() -> None:
    qbe = BeautifulSoup(_render(_vista("qbe")), "html.parser")
    orden = [nodo.get("data-kpi") for nodo in qbe.select("[data-kpi]")]
    assert orden[:3] == ["partidos", "brier-qbe", "brier-mercado"]

    valor_qbe = qbe.select_one('[data-kpi="brier-qbe"] .kpi-value')
    valor_mkt = qbe.select_one('[data-kpi="brier-mercado"] .kpi-value')
    assert "text-muted" in (valor_qbe.get("class") or []), "0.2169 > 0.2106 ⇒ gris"
    assert "text-accent" in (valor_mkt.get("class") or []), "0.2106 < 0.2169 ⇒ acento"
    assert "N=134" in qbe.select_one('[data-kpi="brier-mercado"] .kpi-sub').get_text()

    mercado = BeautifulSoup(_render(_vista("mercado")), "html.parser")
    orden_mercado = [nodo.get("data-kpi") for nodo in mercado.select("[data-kpi]")]
    assert orden_mercado[:3] == ["partidos", "brier-mercado", "brier-qbe"]


# ── 11 · [REV.3] Persistencia del acordeón (localStorage) ───────────────────
def test_persistencia_del_acordeon() -> None:
    vista = _vista("qbe")
    html = _render(vista)
    sopa = BeautifulSoup(html, "html.parser")

    detalles = sopa.select("details.jornada-accordion[data-jornada]")
    assert len(detalles) == len(vista["jornadas"]), "cada jornada porta la llave de persistencia"
    assert "qbe_desempeno_acordeones_abiertos" in html
    assert "localStorage" in html
    assert "details.jornada-accordion" in html


# ── 12 · [REV.3] Tasa de Rescate reactiva al Mando Rector (servicio) ────────
def _partido_rescate(
    resultado: str,
    p: tuple,
    q: tuple,
    r: tuple,
) -> Dict[str, Any]:
    return {
        "id_partido": f"T-{resultado}-{p[0]}",
        "local": "Local",
        "visitante": "Visita",
        "marcador": "1 - 0",
        "resultado_real": resultado,
        "es_cold_start": False,
        "suficiencia_s_i": 3,
        "p_local": p[0],
        "p_empate": p[1],
        "p_visitante": p[2],
        "q_local": q[0],
        "q_empate": q[1],
        "q_visitante": q[2],
        "momios": {"L": 2.0, "E": 3.5, "V": 4.0},
        "r_max": r[0],
        "r_mid": r[1],
        "r_low": r[2],
        "clasificacion_triada": "P_MAX",
        "semaforos": {},
        "atribucion_disponible": False,
        "atribucion_driver": None,
        "variables_44": {},
    }


def _calibracion_sintetica() -> Dict[str, Any]:
    """Tres partidos donde Q-BE y el consenso cubren desenlaces distintos."""
    partidos = [
        # Gana LOCAL: P′ lo cubre (r_max); el consenso no (top-2 = VISITANTE/EMPATE).
        _partido_rescate("LOCAL", (0.50, 0.30, 0.20), (0.20, 0.30, 0.50), ("LOCAL", "EMPATE", "VISITANTE")),
        # Gana VISITANTE: P′ no lo cubre (P_LOW); el consenso sí (top-2 = VISITANTE/LOCAL).
        _partido_rescate("VISITANTE", (0.50, 0.30, 0.20), (0.25, 0.15, 0.60), ("LOCAL", "EMPATE", "VISITANTE")),
        # Gana EMPATE: P′ lo cubre (r_max); el consenso no (top-2 = LOCAL/VISITANTE).
        _partido_rescate("EMPATE", (0.35, 0.45, 0.20), (0.45, 0.20, 0.35), ("EMPATE", "LOCAL", "VISITANTE")),
    ]
    return {
        "fuente": {"temporada": "2026_2027 · Actual"},
        "error": None,
        "jornadas": [{"jornada": 1, "total_partidos": len(partidos), "partidos": partidos}],
    }


def test_tasa_de_rescate_reactiva_al_mando(monkeypatch) -> None:
    from app.services import desempeno_view

    monkeypatch.setattr(
        desempeno_view, "cargar_vista_calibracion", lambda: _calibracion_sintetica()
    )
    qbe = desempeno_view.cargar_vista_desempeno(mando="qbe", devig="proporcional")
    mercado = desempeno_view.cargar_vista_desempeno(mando="mercado", devig="proporcional")

    assert qbe["kpis"]["tasa_rescate_pct"] == 66.67, "Q-BE cubre 2 de 3"
    assert mercado["kpis"]["tasa_rescate_pct"] == 33.33, "el consenso cubre 1 de 3"
    assert qbe["kpis"]["tasa_rescate_pct"] != mercado["kpis"]["tasa_rescate_pct"]
    assert qbe["jornadas"][0]["tasa_rescate_pct"] == 66.67
    assert mercado["jornadas"][0]["tasa_rescate_pct"] == 33.33


# ── 7 · Fail-Loud de dominio: sin degradación silenciosa ─────────────────────
@pytest.fixture()
def cliente():
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)


def test_fail_loud_casino_fuera_de_dominio(cliente) -> None:
    with pytest.raises(ValueError):
        cliente.get("/desempeno", params={"casino": "bet365"})


def test_fail_loud_devig_fuera_de_dominio(cliente) -> None:
    with pytest.raises(ValueError):
        cliente.get("/desempeno", params={"devig": "power"})


def test_dominios_validos_no_levantan(cliente) -> None:
    respuesta = cliente.get(
        "/desempeno",
        params=[
            ("casino", "caliente"),
            ("casino", "novibet"),
            ("devig", "proporcional"),
        ],
    )
    assert respuesta.status_code == 200, (
        "un dominio válido no puede romper la vista: "
        f"{respuesta.status_code}"
    )
