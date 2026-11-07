# -*- coding: utf-8 -*-
"""The Shield — Juez Inmutable de Semántica Visual de la Distribución Base.

[DES-QBE-078 · REV.4] [ARCH-1.4.78 · REV.2] · Régimen [DIRGEN-STRICT] · Paso 2
(Juez en RED).

Certifica la verdad semántica de la vista `/desempeno` mediante parseo de la
plantilla `app/templates/desempeno.html` con contexto sintético (no depende de
la base de datos), la fachada `desempeno_view.py` y el contrato HTTP:

1. **Cuadrícula de 7 macro KPIs.** La banda publica exactamente siete
   `.kpi-card`: Éxito Pmax, Éxito Pmid, Cobertura Resultado, Brier Q-BE,
   Brier Mercado, Alpha de Desempeño y Partidos Auditados (§7.4.11).
2. **Etiquetas mnemónicas de jornada.** Cada `<summary class="jornada-header-bar">`
   declara `Exto_Pmax:`, `Exto_Pmid:`, `Cobertura_Rltdo:` y `Alpha:` (§7.4.12).
3. **Invariante C-50.** `cobertura_resultado_rate ≡ pmax_success_rate +
   pmid_success_rate (± 1e-5)`, global y por jornada (§7.4.11 / §18.2).
4. **Chip de diagnóstico de vértice.** El pie de tarjeta publica
   `COB: PRIMARIO`, `COB: RESCATE`, `COB: RUPTURA` o `COB: COLD START`; el
   binario `RESCATE SÍ / NO` queda derogado (§7.4.13).
5. **Sensibilidad a mando.** `?mando=mercado` conmuta la terna inicial a
   Éxito Mkt_Max / Éxito Mkt_Mid / Cobertura Mercado y reordena el Brier
   Mercado a la cuarta posición (§7.4.11).
6. **Inversión de barras, coloreado del balón, Cold Start, Alpha bidireccional,
   acordeones y Fail-Loud** se conservan de REV.3.

Estado esperado en este turno: **RED CONTROLADO** — la producción se ajusta en
el Paso 3. El Juez no se adapta al código: el código se adapta al Juez.
"""

from __future__ import annotations

import math
import re
import sys
import unicodedata
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
        # [REV.4] Lectura individual servida por la fachada (§18.2).
        "alpha_partido_pct": 5.47,
        "rescate_partido": True,
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
        # [REV.4] Contrato `DesempenoKPIsOut` (docs/ARCH.md §18.2).
        "kpis": {
            "pmax_success_rate": 50.0,
            "pmid_success_rate": 25.0,
            "cobertura_resultado_rate": 75.0,
            "brier_qbe": 0.2169,
            "brier_mercado": 0.2106,
            "alpha_desempeno": -2.99,
            "total_partidos": 134,
            "total_jornadas": 15,
            "metodo_devig": "shin",
            "mando_rector": mando,
            "temporadas_disponibles": list(TEMPORADAS_CANONICAS),
        },
        # [REV.4] Contrato `DesempenoJornadaOut` (docs/ARCH.md §18.2).
        "jornadas": [
            {
                "numero": 14,
                "etiqueta": None,
                "total_partidos": 1,
                "pmax_success_rate": 100.0,
                "pmid_success_rate": 0.0,
                "cobertura_resultado_rate": 100.0,
                "alpha": -5.47,
                "brier_qbe": 0.2886,
                "brier_mkt": 0.3053,
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
        alpha_partido_pct=None,
        rescate_partido=False,
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


# ── 6 · [REV.4] Banda de 7 macro KPIs unificados ────────────────────────────
def _normalizar_etiqueta(texto: str) -> str:
    """Mayúsculas, sin acentos, sin guiones bajos y con espacios colapsados."""
    limpio = unicodedata.normalize("NFKD", texto)
    limpio = "".join(c for c in limpio if not unicodedata.combining(c))
    return " ".join(limpio.upper().replace("_", " ").split())


def _etiquetas_kpi(sopa) -> List[str]:
    return [
        _normalizar_etiqueta(tarjeta.select_one(".kpi-label").get_text(" ", strip=True))
        for tarjeta in sopa.select(".kpi-card")
    ]


def _valor_kpi(sopa, clave: str) -> str:
    nodo = sopa.select_one(f'[data-kpi="{clave}"] .kpi-value')
    assert nodo is not None, f"la banda de 7 KPIs no publica la tarjeta {clave!r}"
    return nodo.get_text(" ", strip=True)


def _numero(texto: str) -> float:
    coincidencia = re.search(r"[+-]?\d+(?:\.\d+)?", texto)
    assert coincidencia, f"no hay cifra en {texto!r}"
    return float(coincidencia.group(0))


def test_banda_de_macro_kpis_transcribe_el_universo() -> None:
    sopa = BeautifulSoup(_render(_vista("qbe")), "html.parser")
    tarjetas = sopa.select(".kpi-card")

    assert len(tarjetas) == 7, (
        f"la banda debe publicar exactamente 7 tarjetas `.kpi-card`; hay {len(tarjetas)} "
        "— la cuadrícula de 5 quedó derogada [DES-QBE-078] §7.4.11"
    )

    etiquetas = _etiquetas_kpi(sopa)
    assert etiquetas[0] in {"EXITO PMAX", "EXITO P MAX"}, etiquetas
    assert etiquetas[1] in {"EXITO PMID", "EXITO P MID"}, etiquetas
    assert etiquetas[2] == "COBERTURA RESULTADO", etiquetas
    assert etiquetas[6] == "PARTIDOS AUDITADOS", etiquetas

    assert "50.0" in _valor_kpi(sopa, "pmax") and "%" in _valor_kpi(sopa, "pmax")
    assert "25.0" in _valor_kpi(sopa, "pmid") and "%" in _valor_kpi(sopa, "pmid")
    assert "75.0" in _valor_kpi(sopa, "cobertura") and "%" in _valor_kpi(sopa, "cobertura")
    assert "0.2169" in _valor_kpi(sopa, "brier-qbe")
    assert "0.2106" in _valor_kpi(sopa, "brier-mercado")
    assert "-2.99" in _valor_kpi(sopa, "alpha") and "%" in _valor_kpi(sopa, "alpha")
    assert "134" in _valor_kpi(sopa, "partidos")


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


# ── 9 · [REV.4] Encabezado de jornada: etiquetas mnemónicas + Brier bicolor ─
def _vista_jornadas_bicolor(mando: str = "qbe") -> Dict[str, Any]:
    vista = _vista(mando)
    partido = _partido()
    vista["jornadas"] = [
        {
            "numero": 1,
            "etiqueta": None,
            "total_partidos": 1,
            "pmax_success_rate": 80.0,
            "pmid_success_rate": 0.0,
            "cobertura_resultado_rate": 80.0,
            "alpha": -50.0,
            "brier_qbe": 0.2000,
            "brier_mkt": 0.3000,
            "partidos": [partido],
        },
        {
            "numero": 2,
            "etiqueta": None,
            "total_partidos": 1,
            "pmax_success_rate": 20.0,
            "pmid_success_rate": 0.0,
            "cobertura_resultado_rate": 20.0,
            "alpha": 300.0,
            "brier_qbe": 0.4000,
            "brier_mkt": 0.1000,
            "partidos": [partido],
        },
    ]
    return vista


def _clases_brier(barra, fuente: str) -> List[str]:
    nodo = barra.select_one(f'[data-brier="{fuente}"]')
    assert nodo is not None, f"falta el Brier {fuente!r} en la barra de jornada"
    return list(nodo.get("class") or [])


def test_encabezados_de_jornada_etiquetas_mnemonicas_y_bicolor() -> None:
    sopa = BeautifulSoup(_render(_vista_jornadas_bicolor("qbe")), "html.parser")
    barras = sopa.select("summary.jornada-header-bar")
    assert len(barras) == 2

    for barra in barras:
        texto = barra.get_text(" ", strip=True)
        assert "Exto_Pmax:" in texto, "cada jornada declara Exto_Pmax (§7.4.12)"
        assert "Exto_Pmid:" in texto, "cada jornada declara Exto_Pmid (§7.4.12)"
        assert "Cobertura_Rltdo:" in texto, (
            "cada jornada declara Cobertura_Rltdo (§7.4.12)"
        )
        assert "Alpha:" in texto, "cada jornada declara su Alpha"

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
    barra_mercado = mercado.select("summary.jornada-header-bar")[0]
    assert [nodo.get("data-brier") for nodo in barra_mercado.select("[data-brier]")] == ["mercado", "qbe"]


# ── 10 · [REV.4] Banda de 7 KPIs: orden por mando y bicolor ────────────────
def test_banda_kpis_bicolor_y_orden_por_mando() -> None:
    qbe = BeautifulSoup(_render(_vista("qbe")), "html.parser")
    orden = [nodo.get("data-kpi") for nodo in qbe.select(".kpi-card")]
    assert orden == [
        "pmax",
        "pmid",
        "cobertura",
        "brier-qbe",
        "brier-mercado",
        "alpha",
        "partidos",
    ], f"orden canónico de la banda Q-BE: {orden}"

    valor_qbe = qbe.select_one('[data-kpi="brier-qbe"] .kpi-value')
    valor_mkt = qbe.select_one('[data-kpi="brier-mercado"] .kpi-value')
    assert "text-muted" in (valor_qbe.get("class") or []), "0.2169 > 0.2106 ⇒ gris"
    assert "text-accent" in (valor_mkt.get("class") or []), "0.2106 < 0.2169 ⇒ acento"

    mercado = BeautifulSoup(_render(_vista("mercado")), "html.parser")
    orden_mercado = [nodo.get("data-kpi") for nodo in mercado.select(".kpi-card")]
    assert orden_mercado == [
        "pmax",
        "pmid",
        "cobertura",
        "brier-mercado",
        "brier-qbe",
        "alpha",
        "partidos",
    ], f"en Modo Mercado el Brier Mercado pasa a la 4.ª posición: {orden_mercado}"

    etiquetas = _etiquetas_kpi(mercado)
    assert etiquetas[0] == "EXITO MKT MAX", etiquetas
    assert etiquetas[1] == "EXITO MKT MID", etiquetas
    assert etiquetas[2] == "COBERTURA MERCADO", etiquetas
    assert etiquetas[3] == "BRIER MERCADO", etiquetas


# ── 11 · [REV.4] Acordeones: nacen cerrados y viven en la sesión (§7.4.10) ──
def test_acordeones_contraidos_y_persistidos_en_sesion() -> None:
    vista = _vista("qbe")
    html = _render(vista)
    sopa = BeautifulSoup(html, "html.parser")

    detalles = sopa.select("details.jornada-accordion[data-jornada]")
    assert len(detalles) == len(vista["jornadas"]), "cada jornada porta la llave de persistencia"
    assert all(not detalle.has_attr("open") for detalle in detalles), (
        "las jornadas nacen contraídas: el servidor no emite `open` "
        "[DES-QBE-078] §7.4.10"
    )
    assert "qbe_desempeno_acordeones_abiertos" in html
    assert "sessionStorage" in html, (
        "el estado del acordeón se persiste en `sessionStorage` [DES-QBE-078] §7.4.10"
    )
    assert "localStorage" not in html, (
        "`localStorage` queda prohibido: el foco de auditoría pertenece a la sesión"
    )
    assert 'data-acordeones-reset="1"' in html, (
        "«Restablecer» debe limpiar la clave de sesión y forzar el cierre"
    )
    assert "details.jornada-accordion" in html


# ── 12 · [REV.4] Cobertura reactiva a la Distribución Base (servicio) ───────
def _partido_rescate(
    resultado: str,
    p: tuple,
    q: tuple,
    r: tuple,
) -> Dict[str, Any]:
    clasificacion = (
        "P_MAX" if resultado == r[0] else ("P_MID" if resultado == r[1] else "P_LOW")
    )
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
        "clasificacion_triada": clasificacion,
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


def test_cobertura_reactiva_al_mando(monkeypatch) -> None:
    from app.services import desempeno_view

    monkeypatch.setattr(
        desempeno_view, "cargar_vista_calibracion", lambda: _calibracion_sintetica()
    )
    qbe = desempeno_view.cargar_vista_desempeno(mando="qbe", devig="proporcional")
    mercado = desempeno_view.cargar_vista_desempeno(mando="mercado", devig="proporcional")

    assert qbe["kpis"].get("pmax_success_rate") == 66.67, "Q-BE acierta P_max en 2 de 3"
    assert qbe["kpis"].get("pmid_success_rate") == 0.0
    assert qbe["kpis"].get("cobertura_resultado_rate") == 66.67
    assert mercado["kpis"].get("pmax_success_rate") == 33.33, "el consenso acierta 1 de 3"
    assert mercado["kpis"].get("pmid_success_rate") == 0.0
    assert mercado["kpis"].get("cobertura_resultado_rate") == 33.33
    assert qbe["kpis"].get("cobertura_resultado_rate") != mercado["kpis"].get(
        "cobertura_resultado_rate"
    )

    assert qbe["jornadas"][0].get("cobertura_resultado_rate") == 66.67
    assert mercado["jornadas"][0].get("cobertura_resultado_rate") == 33.33


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


# ── 13 · [REV.4] Alpha bidireccional de la Distribución Base (§7.4.9) ───────
def _calibracion_de(partido: Dict[str, Any]) -> Dict[str, Any]:
    """Universo sintético de una sola tarjeta para aislar la aritmética."""
    return {
        "fuente": {"temporada": "2026_2027 · Actual"},
        "error": None,
        "jornadas": [{"jornada": 1, "total_partidos": 1, "partidos": [partido]}],
    }


def _partido_alfa(p: tuple, q: tuple, resultado: str) -> Dict[str, Any]:
    """Partido con P′ y q_mkt controlados; el vértice Q-BE vive en `r_max`."""
    return _partido(
        id_partido=f"AL-{resultado}",
        resultado_real=resultado,
        p_local=p[0],
        p_empate=p[1],
        p_visitante=p[2],
        q_local=q[0],
        q_empate=q[1],
        q_visitante=q[2],
        r_max="LOCAL",
        r_mid="EMPATE",
        r_low="VISITANTE",
        clasificacion_triada="P_MAX",
    )


@pytest.mark.parametrize(
    "mando, p, q, signo, motivo",
    [
        # Caso canónico BS_QBE = 0.20 < BS_Mkt = 0.21 ⇒ Alpha positivo (+4.76).
        ("qbe", (0.70, 0.20, 0.10), (0.50, 0.30, 0.20), +1, "Q-BE mejor que el mercado"),
        # Caso canónico BS_QBE = 0.21 > BS_Mkt = 0.20 con base mercado ⇒ positivo.
        ("mercado", (0.50, 0.30, 0.20), (0.70, 0.20, 0.10), +1, "el mercado es mejor"),
        # Caso canónico BS_QBE = 0.20 < BS_Mkt = 0.21 con base mercado ⇒ negativo.
        ("mercado", (0.70, 0.20, 0.10), (0.50, 0.30, 0.20), -1, "el mercado es peor que Q-BE"),
    ],
)
def test_alpha_bidireccional(
    monkeypatch, mando: str, p: tuple, q: tuple, signo: int, motivo: str
) -> None:
    """`Alpha = (1 − BS_base / BS_oponente) × 100`, siempre a favor de la base."""
    from app.services import desempeno_view

    monkeypatch.setattr(
        desempeno_view,
        "cargar_vista_calibracion",
        lambda: _calibracion_de(_partido_alfa(p, q, "LOCAL")),
    )
    vista = desempeno_view.cargar_vista_desempeno(mando=mando, devig="proporcional")

    brier_qbe = vista["kpis"]["brier_qbe"]
    brier_mercado = vista["kpis"]["brier_mercado"]
    assert brier_qbe is not None and brier_mercado is not None and brier_mercado > 0
    base, oponente = (
        (brier_qbe, brier_mercado) if mando == "qbe" else (brier_mercado, brier_qbe)
    )
    esperado = round((1.0 - base / oponente) * 100.0, 2)

    alpha = vista["kpis"].get("alpha_desempeno")
    assert alpha is not None, f"con par de Briers medible el Alpha existe ({motivo})"
    assert math.copysign(1.0, alpha) == signo, (
        f"con base {mando!r} y {motivo}, el Alpha debe ser "
        f"{'positivo' if signo > 0 else 'negativo'} (recibido {alpha!r})"
    )
    assert alpha == pytest.approx(esperado, abs=0.1), (
        "Alpha = (1 − BS_base / BS_oponente) × 100 [DES-QBE-078] §7.4.9"
    )

    jornada = vista["jornadas"][0]
    assert jornada.get("alpha") == pytest.approx(esperado, abs=0.1), (
        "el encabezado de jornada aplica la MISMA ley bidireccional"
    )
    tarjeta = jornada["partidos"][0]
    assert "alpha_partido_pct" in tarjeta, (
        "DesempenoPartidoOut debe publicar `alpha_partido_pct` [ARCH-1.4.78] §18.2"
    )
    assert tarjeta["alpha_partido_pct"] == pytest.approx(esperado, abs=0.1), (
        "la tarjeta de partido aplica la MISMA ley bidireccional"
    )


# ── 14 · [REV.4] Rescate por partido: par de cobertura de la base activa ────
@pytest.mark.parametrize(
    "mando, resultado, esperado",
    [
        ("qbe", "LOCAL", True),          # r_max
        ("qbe", "EMPATE", True),         # r_mid
        ("qbe", "VISITANTE", False),     # r_low
        ("mercado", "VISITANTE", True),  # max q_mkt
        ("mercado", "EMPATE", True),     # second_max q_mkt
        ("mercado", "LOCAL", False),     # min q_mkt
    ],
)
def test_rescate_por_partido(monkeypatch, mando: str, resultado: str, esperado: bool) -> None:
    """`rescate_partido` = el resultado cayó en el par de cobertura de la base."""
    from app.services import desempeno_view

    # P′: LOCAL > EMPATE > VISITANTE · q_mkt: VISITANTE > EMPATE > LOCAL.
    partido = _partido_alfa((0.50, 0.30, 0.20), (0.20, 0.30, 0.50), resultado)
    monkeypatch.setattr(
        desempeno_view,
        "cargar_vista_calibracion",
        lambda: _calibracion_de(partido),
    )
    vista = desempeno_view.cargar_vista_desempeno(mando=mando, devig="proporcional")
    tarjeta = vista["jornadas"][0]["partidos"][0]

    assert "rescate_partido" in tarjeta, (
        "DesempenoPartidoOut debe publicar `rescate_partido` [ARCH-1.4.78] §18.2"
    )
    assert tarjeta["rescate_partido"] is esperado, (
        f"con base {mando!r} y resultado {resultado!r}, Rescate debe ser {esperado}: "
        "la base `qbe` cubre {r_max, r_mid} y la base `mercado` los dos máximos de q_mkt"
    )


# ── 15 · [REV.4] Chip de diagnóstico de vértice y Alpha del pie (§7.4.13) ──
def _chip_cobertura(tarjeta):
    chip = tarjeta.select_one(".mc-chip-cobertura")
    assert chip is not None, (
        "el pie de la tarjeta debe publicar `.mc-chip-cobertura` [DES-QBE-078] §7.4.13"
    )
    return chip


def test_pie_de_tarjeta_publica_diagnostico_de_cobertura_y_alpha() -> None:
    # Primario: el resultado consumado es r_max.
    primario = _partido(
        resultado_real="LOCAL",
        r_max="LOCAL",
        r_mid="VISITANTE",
        r_low="EMPATE",
        vertice_qbe="max",
    )
    chip = _chip_cobertura(_tarjeta(_render(_vista("qbe", primario))))
    assert "COB: PRIMARIO" in chip.get_text(" ", strip=True)
    assert "badge-success" in (chip.get("class") or []), (
        "el vértice primario se pinta en `badge-success` [DES-QBE-078] §7.4.13"
    )

    # Rescate: el resultado consumado es r_mid.
    rescate = _partido(
        resultado_real="VISITANTE",
        r_max="LOCAL",
        r_mid="VISITANTE",
        r_low="EMPATE",
        vertice_qbe="mid",
    )
    chip = _chip_cobertura(_tarjeta(_render(_vista("qbe", rescate))))
    assert "COB: RESCATE" in chip.get_text(" ", strip=True)
    assert "badge-accent" in (chip.get("class") or []), (
        "el vértice de rescate se pinta en `badge-accent` [DES-QBE-078] §7.4.13"
    )

    # Ruptura: el resultado consumado es r_low.
    ruptura = _partido(
        resultado_real="EMPATE",
        r_max="LOCAL",
        r_mid="VISITANTE",
        r_low="EMPATE",
        vertice_qbe="low",
    )
    chip = _chip_cobertura(_tarjeta(_render(_vista("qbe", ruptura))))
    assert "COB: RUPTURA" in chip.get_text(" ", strip=True)
    assert "badge-danger" in (chip.get("class") or []), (
        "el vértice de ruptura se pinta en `badge-danger` [DES-QBE-078] §7.4.13"
    )

    # Cold Start: chip neutral, sin diagnóstico fiduciario.
    frio = _partido(
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
        alpha_partido_pct=None,
        rescate_partido=False,
    )
    chip = _chip_cobertura(_tarjeta(_render(_vista("qbe", frio))))
    assert "COB: COLD START" in chip.get_text(" ", strip=True)
    assert "badge-neutral" in (chip.get("class") or []), (
        "Cold Start exhibe el chip neutral [DES-QBE-078] §7.4.13"
    )

    # El binario derogado no reaparece en ninguna tarjeta.
    for partido in (primario, rescate, ruptura, frio):
        tarjeta = _tarjeta(_render(_vista("qbe", partido)))
        texto = tarjeta.get_text(" ", strip=True).upper()
        assert "RESCATE SÍ" not in texto, "el binario RESCATE SÍ quedó derogado"
        assert "RESCATE NO" not in texto, "el binario RESCATE NO quedó derogado"
        assert not tarjeta.select("[data-rescate-partido]"), (
            "el atributo `data-rescate-partido` quedó derogado del DOM"
        )

    # Alpha positivo/negativo/ausente conserva su ley cromática.
    positivo = _partido(alpha_partido_pct=4.76, rescate_partido=True)
    alpha = _tarjeta(_render(_vista("qbe", positivo))).select_one("[data-alpha-partido]")
    assert alpha is not None, "el pie de la tarjeta debe publicar el indicador Alpha (§7.1)"
    assert "+4.76" in alpha.get_text(" ", strip=True), "el Alpha del partido se transcribe"
    assert "+4.76" in str(alpha.get("data-alpha-partido"))
    assert "text-success" in (alpha.get("class") or []), (
        "un Alpha positivo se tiñe con `--success` [DES-QBE-078] §7.4.9"
    )

    negativo = _partido(alpha_partido_pct=-3.2, rescate_partido=False)
    alpha_neg = _tarjeta(_render(_vista("mercado", negativo))).select_one(
        "[data-alpha-partido]"
    )
    assert "3.20" in alpha_neg.get_text(" ", strip=True)
    assert "text-danger" in (alpha_neg.get("class") or []), (
        "un Alpha negativo se tiñe con `--danger` [DES-QBE-078] §7.4.9"
    )

    sin_medicion = _partido(alpha_partido_pct=None, rescate_partido=False)
    alpha_sin = _tarjeta(_render(_vista("qbe", sin_medicion))).select_one(
        "[data-alpha-partido]"
    )
    assert alpha_sin.get("data-alpha-partido") == "SIN EVIDENCIA", (
        "sin medición no se fabrica un 0 %: se declara la ausencia [DES-QBE-078] §7.4.9"
    )
    assert "0.00" not in alpha_sin.get_text(" ", strip=True)


# ── 16 · [REV.4] Universo sintético del Invariante C-50 (servicio) ──────────
def _partido_c50(id_partido: str, resultado: str, q: tuple) -> Dict[str, Any]:
    """Partido coherente con el orden fiduciario fijo de `_calibracion_c50`."""
    clasificacion = {
        "LOCAL": "P_MAX",
        "EMPATE": "P_MID",
        "VISITANTE": "P_LOW",
    }[resultado]
    return _partido(
        id_partido=id_partido,
        resultado_real=resultado,
        p_local=0.50,
        p_empate=0.30,
        p_visitante=0.20,
        q_local=q[0],
        q_empate=q[1],
        q_visitante=q[2],
        r_max="LOCAL",
        r_mid="EMPATE",
        r_low="VISITANTE",
        clasificacion_triada=clasificacion,
    )


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


# ── 17 · [REV.4] Cuadrícula exacta de 7 KPIs sobre GET /desempeno ──────────
def test_cuadricula_exacta_de_siete_kpis(cliente) -> None:
    respuesta = cliente.get("/desempeno")

    assert respuesta.status_code == 200, respuesta.text[:400]
    sopa = BeautifulSoup(respuesta.text, "html.parser")
    tarjetas = sopa.select(".kpi-card")
    assert len(tarjetas) == 7, (
        f"`GET /desempeno` debe publicar exactamente 7 `.kpi-card`; hay "
        f"{len(tarjetas)} — la cuadrícula de 5 quedó derogada [DES-QBE-078] §7.4.11"
    )

    etiquetas = _etiquetas_kpi(sopa)
    assert etiquetas[0] in {"EXITO PMAX", "EXITO P MAX"}, etiquetas
    assert etiquetas[1] in {"EXITO PMID", "EXITO P MID"}, etiquetas
    assert etiquetas[2] == "COBERTURA RESULTADO", etiquetas
    assert etiquetas[6] == "PARTIDOS AUDITADOS", (
        f"la 7.ª tarjeta debe ser PARTIDOS AUDITADOS; es {etiquetas[6]!r}"
    )


# ── 18 · [REV.4] Etiquetas mnemónicas en la barra de jornada ───────────────
def test_etiquetas_mnemonicas_en_barra_de_jornada(cliente) -> None:
    respuesta = cliente.get("/desempeno")

    assert respuesta.status_code == 200, respuesta.text[:400]
    sopa = BeautifulSoup(respuesta.text, "html.parser")
    barras = sopa.select("summary.jornada-header-bar")
    assert barras, "la parrilla debe renderizar al menos una jornada"

    for barra in barras:
        texto = barra.get_text(" ", strip=True)
        for etiqueta in ("Exto_Pmax:", "Exto_Pmid:", "Cobertura_Rltdo:"):
            assert etiqueta in texto, (
                f"falta la etiqueta mnemónica {etiqueta!r} en la barra de jornada "
                "[DES-QBE-078] §7.4.12"
            )


# ── 19 · [REV.4] Invariante C-50: DOM y servicio ───────────────────────────
def _valor_etiqueta(texto: str, etiqueta: str) -> float:
    patron = rf"{re.escape(etiqueta)}\s*([+-]?\d+(?:\.\d+)?)"
    coincidencia = re.search(patron, texto)
    assert coincidencia, f"no se pudo leer {etiqueta!r} en {texto!r}"
    return float(coincidencia.group(1))


def test_invariante_c50_aditividad_en_dom_y_servicio(monkeypatch) -> None:
    # DOM: contexto sintético determinista (50.0 + 25.0 = 75.0).
    sopa = BeautifulSoup(_render(_vista("qbe")), "html.parser")
    pmax = _numero(_valor_kpi(sopa, "pmax"))
    pmid = _numero(_valor_kpi(sopa, "pmid"))
    cobertura = _numero(_valor_kpi(sopa, "cobertura"))
    assert abs(cobertura - (pmax + pmid)) <= 0.05, (
        f"Invariante C-50 violado en la banda global: {cobertura} != "
        f"{pmax} + {pmid} [DES-QBE-078] §7.4.11"
    )

    barra = sopa.select_one("summary.jornada-header-bar")
    assert barra is not None, "la parrilla debe publicar la barra de jornada"
    texto = barra.get_text(" ", strip=True)
    j_pmax = _valor_etiqueta(texto, "Exto_Pmax:")
    j_pmid = _valor_etiqueta(texto, "Exto_Pmid:")
    j_cob = _valor_etiqueta(texto, "Cobertura_Rltdo:")
    assert abs(j_cob - (j_pmax + j_pmid)) <= 0.05, (
        f"Invariante C-50 violado en la jornada: {j_cob} != {j_pmax} + {j_pmid}"
    )

    # Servicio: misma invariante sobre el DTO, sin redondeo de presentación.
    from app.services import desempeno_view

    monkeypatch.setattr(
        desempeno_view, "cargar_vista_calibracion", _calibracion_c50
    )
    for mando in ("qbe", "mercado"):
        vista = desempeno_view.cargar_vista_desempeno(
            mando=mando, devig="proporcional"
        )
        kpis = vista["kpis"]
        assert abs(
            kpis["cobertura_resultado_rate"]
            - (kpis["pmax_success_rate"] + kpis["pmid_success_rate"])
        ) <= 1e-5, f"Invariante C-50 violado en el global con base {mando!r}"

        jornada = vista["jornadas"][0]
        assert abs(
            jornada["cobertura_resultado_rate"]
            - (jornada["pmax_success_rate"] + jornada["pmid_success_rate"])
        ) <= 1e-5, f"Invariante C-50 violado en la jornada con base {mando!r}"


# ── 20 · [REV.4] Sensibilidad a mando: DOM y terna del servicio ────────────
def test_sensibilidad_a_mando_mercado(cliente, monkeypatch) -> None:
    respuesta = cliente.get("/desempeno", params={"mando": "mercado"})

    assert respuesta.status_code == 200, respuesta.text[:400]
    assert 'data-mando-rector="mercado"' in respuesta.text
    sopa = BeautifulSoup(respuesta.text, "html.parser")
    tarjetas = sopa.select(".kpi-card")
    assert len(tarjetas) == 7, (
        f"la cuadrícula de 7 KPIs debe sobrevivir la conmutación de mando; "
        f"hay {len(tarjetas)} tarjetas"
    )

    etiquetas = _etiquetas_kpi(sopa)
    assert etiquetas[0] == "EXITO MKT MAX", etiquetas
    assert etiquetas[1] == "EXITO MKT MID", etiquetas
    assert etiquetas[2] == "COBERTURA MERCADO", etiquetas
    assert etiquetas[3] == "BRIER MERCADO", (
        f"en Modo Mercado el Brier Mercado ocupa la 4.ª posición; {etiquetas}"
    )

    # La terna evalúa el consenso des-marginado, no las cuotas crudas.
    from app.services import desempeno_view

    monkeypatch.setattr(
        desempeno_view, "cargar_vista_calibracion", _calibracion_c50
    )
    qbe = desempeno_view.cargar_vista_desempeno(mando="qbe", devig="proporcional")
    mercado = desempeno_view.cargar_vista_desempeno(
        mando="mercado", devig="proporcional"
    )

    assert qbe["kpis"]["pmax_success_rate"] == pytest.approx(50.0, abs=1e-5)
    assert mercado["kpis"]["pmax_success_rate"] == pytest.approx(75.0, abs=1e-5)
    assert qbe["kpis"]["pmid_success_rate"] == pytest.approx(25.0, abs=1e-5)
    assert mercado["kpis"]["pmid_success_rate"] == pytest.approx(25.0, abs=1e-5)
    assert qbe["kpis"]["cobertura_resultado_rate"] == pytest.approx(75.0, abs=1e-5)
    assert mercado["kpis"]["cobertura_resultado_rate"] == pytest.approx(100.0, abs=1e-5)
