# -*- coding: utf-8 -*-
"""The Shield — Juez de Contrato de la Auditoría de Calibración y Atribución.

[DBBD-FUNGIBLE] Régimen de presentación: certifica que `/visor` lee la bóveda 3NF
del snapshot canónico —no el histórico—, que las cifras de mercado/Alpha coinciden
con el endpoint canónico y que la ausencia del motor causal se declara como
`PENDIENTE MOTOR` / `SIN EVIDENCIA`, jamás como una cifra fabricada.

[DES-QBE-074] Añade el contrato de PRESENTACIÓN: encabezado sin texto pegado,
cifras alineadas por clase (no por estilo calculado), ausencia declarada con
guion + explicación accesible y píldora de atribución con bando explícito.
"""

from __future__ import annotations

import inspect
import re
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture()
def cliente():
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)


def _canonico(cliente) -> dict:
    respuesta = cliente.get("/api/observatory/backtesting/calibration-report")
    assert respuesta.status_code == 200, respuesta.text[:500]
    return respuesta.json()


def test_visor_200_y_titulo_auditoria(cliente) -> None:
    respuesta = cliente.get("/visor")

    assert respuesta.status_code == 200, respuesta.text[:500]
    assert "Auditoría de Calibración y Atribución" in respuesta.text
    assert "Brier Q-BE Variables" in respuesta.text
    assert "Brier Vars" in respuesta.text
    assert "PENDIENTE MOTOR" in respuesta.text


def test_visor_paridad_con_endpoint_canonico(cliente) -> None:
    """La vitrina y el contrato REST deben servir la MISMA aritmética y el MISMO universo."""
    reporte = _canonico(cliente)
    resumen = reporte["resumen_temporada"]
    html = cliente.get("/visor").text

    assert f"{resumen['brier_score_qbe']:.4f}" in html
    assert f"{resumen['brier_score_mercado']:.4f}" in html
    # El signo positivo se prefija con '+' en la vitrina; el valor absoluto debe aparecer.
    assert f"{abs(resumen['alpha_calibracion_pct']):.2f}%" in html
    # El histórico devolvía N/D; la fuente canónica no debe producir ese literal.
    assert "N/D" not in html


def test_visor_no_fabrica_brier_cuando_la_muestra_esta_vacia() -> None:
    from app.services.calibration_view import construir_vista_desde_reporte

    reporte = {
        "resumen_temporada": {
            "total_partidos": 0,
            "brier_score_qbe": 0.0,
            "brier_score_mercado": 0.0,
            "alpha_calibracion_pct": 0.0,
            "jornadas_auditadas": [],
        },
        "jornadas": [],
    }

    vista = construir_vista_desde_reporte(reporte, fuente={})

    assert vista["resumen"]["muestra_vacia"] is True
    assert vista["resumen"]["brier_qbe"] is None
    assert vista["resumen"]["brier_mercado"] is None
    assert vista["resumen"]["alpha_calibracion_pct"] is None
    assert vista["brier_vars"]["valor"] is None
    assert vista["brier_vars"]["estado"] == "PENDIENTE_MOTOR"


def test_visor_alpha_semantico_por_signo(cliente) -> None:
    resumen = _canonico(cliente)["resumen_temporada"]
    alpha = float(resumen["alpha_calibracion_pct"])
    signo = "positivo" if alpha > 0 else "negativo" if alpha < 0 else "neutro"
    html = cliente.get("/visor").text

    assert f'data-signo="{signo}"' in html


def test_visor_estructura_drilldown_y_columnas(cliente) -> None:
    reporte = _canonico(cliente)
    primera = reporte["jornadas"][0]["jornada"]
    html = cliente.get("/visor").text

    assert 'id="tabla-calibracion"' in html
    assert f'id="detalle-jornada-{primera}"' in html
    assert f'aria-controls="detalle-jornada-{primera}"' in html
    assert 'aria-expanded="false"' in html
    assert "Brier Vars" in html
    assert "Atribución" in html


def test_visor_slots_futuros_pendiente_motor(cliente) -> None:
    html = cliente.get("/visor").text

    assert 'id="slot-heatmap-sinergia"' in html
    assert 'id="lienzo-heatmap-sinergia"' in html
    assert 'id="slot-radar-distribucion"' in html
    assert 'id="lienzo-radar-distribucion"' in html
    assert 'data-estado="PENDIENTE_MOTOR"' in html


def test_visor_filtro_rango_estructura(cliente) -> None:
    html = cliente.get("/visor").text

    assert 'id="filtro-jornada-desde"' in html
    assert 'id="filtro-jornada-hasta"' in html
    assert 'id="visor-rango-reset"' in html
    assert 'id="visor-rango-estado"' in html


def test_visor_snapshot_ausente_degrada_sin_fallback(cliente, tmp_path, monkeypatch) -> None:
    """Sin snapshot: 200 con SIN EVIDENCIA y aviso accionable; nunca fallback al histórico."""
    from app import config

    monkeypatch.setattr(config, "BACKTESTING_SNAPSHOT", tmp_path / "no_existe.db")

    respuesta = cliente.get("/visor")

    assert respuesta.status_code == 200, respuesta.text[:500]
    assert "SIN EVIDENCIA" in respuesta.text
    assert "Snapshot no disponible" in respuesta.text
    assert "N/D" not in respuesta.text


def test_main_no_consume_el_builder_legacy_del_historico() -> None:
    """Guardián de fuente: `/visor` no debe volver a `construir_reporte` ni a su Brier."""
    from app import main

    fuente = inspect.getsource(main)

    assert "construir_reporte" not in fuente
    assert "calcular_brier_multicategorico" not in fuente


# ── [DES-QBE-074] Contrato de presentación del saneamiento visual ──────────────────────────────
# El Juez mira CLASES y ATRIBUTOS del DOM, jamás estilos calculados: una hoja de estilos
# reescrita no puede ponerlo en rojo, y una regresión de marcado no puede esconderse.

def test_visor_presentacion_saneada(cliente) -> None:
    """Encabezado sin texto pegado, cifras alineadas por clase y ausencia declarada con guion."""
    html = cliente.get("/visor").text

    # 1. El estado del motor jamás vuelve a pegarse al nombre de la métrica.
    assert "Brier VarsPENDIENTE" not in html

    # 2. La alineación numérica viaja como contrato de clase, no como estilo inline.
    assert 'class="visor-num visor-th-num"' in html

    # 3. La ausencia de evidencia es guion visual + literal canónico accesible.
    assert 'class="visor-vacio"' in html
    assert "SIN EVIDENCIA" in html

    # 4. La atribución se pinta como píldora con bando declarado y coherente con su clase.
    pares = re.findall(
        r'class="visor-pildora visor-pildora-(local|visita|neutro)" data-favorece="(local|visita|neutro)"',
        html,
    )
    assert pares, "la atribución disponible debe renderizarse como píldora con data-favorece"
    assert all(clase == bando for clase, bando in pares)


def _vista_sintetica() -> dict:
    """Vista mínima con los tres bandos de atribución: local, visita y sin driver."""
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
            "total_partidos": 3,
            "n_jornadas": 1,
            "jornada_min": 1,
            "jornada_max": 1,
            "brier_qbe": 0.4,
            "brier_mercado": 0.5,
            "alpha_calibracion_pct": 20.0,
            "alpha_signo": "positivo",
        },
        "jornadas": [
            {
                "jornada": 1,
                "total_partidos": 3,
                "brier_qbe": 0.4,
                "brier_mercado": 0.5,
                "alpha_calibracion_pct": 20.0,
                "alpha_signo": "positivo",
                "alpha_etiqueta": None,
                "partidos": [
                    {
                        "local": "Equipo Casa",
                        "visitante": "Equipo Visita",
                        "marcador": "2-1",
                        "resultado_real": "LOCAL",
                        "p_texto": "0.500 / 0.250 / 0.250",
                        "brier_qbe": 0.31,
                        "brier_mercado": 0.28,
                        "atribucion_disponible": True,
                        "atribucion_driver": "🛡️ Defensiva Local (+0.23)",
                    },
                    {
                        "local": "Equipo Casa",
                        "visitante": "Equipo Visita",
                        "marcador": "0-1",
                        "resultado_real": "VISITANTE",
                        "p_texto": "0.500 / 0.250 / 0.250",
                        "brier_qbe": 0.44,
                        "brier_mercado": 0.52,
                        "atribucion_disponible": True,
                        "atribucion_driver": "⚡ Ofensiva Visita (+0.31)",
                    },
                    {
                        "local": "Equipo Casa",
                        "visitante": "Equipo Visita",
                        "marcador": None,
                        "resultado_real": None,
                        "p_texto": None,
                        "brier_qbe": None,
                        "brier_mercado": None,
                        "atribucion_disponible": False,
                        "atribucion_driver": None,
                    },
                ],
            }
        ],
        "error": None,
    }


def _render_visor(vista: dict) -> str:
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    entorno = Environment(
        loader=FileSystemLoader(str(PROJECT_ROOT / "app" / "templates")),
        autoescape=select_autoescape(["html"]),
    )
    return entorno.get_template("visor.html").render(
        titulo="Auditoría de Calibración y Atribución",
        vista=vista,
        jornada_inicial=1,
    )


def test_visor_pildora_declara_bando_y_oculta_el_token_crudo() -> None:
    """Transcripción determinista: el bando sale de la etiqueta y el token LOCAL queda en sr-only."""
    html = _render_visor(_vista_sintetica())

    assert 'class="visor-pildora visor-pildora-local" data-favorece="local"' in html
    assert 'class="visor-pildora visor-pildora-visita" data-favorece="visita"' in html
    assert "Resultado real: LOCAL" in html
    assert ">LOCAL</span>" not in html
    assert html.count('class="visor-vacio"') >= 3
