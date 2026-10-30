# -*- coding: utf-8 -*-
"""
🏆 THE SHIELD — MHTML PARSER & SEASON INTEGRITY SUITE
Juez Inmutable: [LN-QBE-134] / [ARCH-1.4.71]
Base de Gobierno: Kybern Framework v13.5 [GOV-TEST-01] (Pure Offline Test)

Nota de aislamiento: el import del parser es diferido dentro de cada prueba.
El motivo es que `qbe_business/tests/test_shield_business.py` certifica que
`qbe_ingestion` no esté en `sys.modules`; un import a nivel de módulo durante
la colecta contaminaría ese juez ajeno.
"""

import os
import pytest
from pathlib import Path


def _parser():
    """Import diferido: evita contaminar `sys.modules` en la fase de colecta."""
    from qbe_ingestion.src.ingestion.parsers import parsear_footystats_mhtml

    return parsear_footystats_mhtml


def test_invarianza_desempaquetado_mhtml_extrae_html():
    """[INVARIANZA 1 - MIME UNPACK]: Debe extraer un string HTML válido desde un archivo .mhtml real."""
    m = _parser()
    raiz_raw = Path("data/raw_footystats")
    carpeta_1516 = raiz_raw / "2015_2016"
    assert carpeta_1516.exists(), "Falta carpeta data/raw_footystats/2015_2016"

    archivo_mhtml = next(carpeta_1516.glob("Fixtures*.mhtml"), None)
    assert archivo_mhtml is not None

    html = m.extraer_html_de_mhtml(archivo_mhtml)
    assert html is not None
    assert "<html" in html.lower() or "<body" in html.lower()
    assert len(html) > 1000


def test_invarianza_verificacion_integridad_temporada_en_archivos_reales():
    """[INVARIANZA 2 - INTEGRIDAD FACTICA]: Debe validar el H1 de 2015/16 y lanzar SeasonIntegrityError ante discordancia."""
    m = _parser()
    raiz_raw = Path("data/raw_footystats")
    carpeta_1516 = raiz_raw / "2015_2016"
    archivo_fixtures = next(carpeta_1516.glob("Fixtures*.mhtml"))
    html_1516 = m.extraer_html_de_mhtml(archivo_fixtures)

    # 1. Coincidencia fáctica real
    temp_detectada = m.verificar_integridad_temporada_html(html_1516, carpeta_esperada="2015_2016")
    assert temp_detectada == "2015_2016"

    # 2. Discordancia forzada -> DEBE LANZAR EXCEPCIÓN
    with pytest.raises(m.SeasonIntegrityError):
        m.verificar_integridad_temporada_html(html_1516, carpeta_esperada="2020_2021")


def test_invarianza_parseo_fixtures_extrae_momios_goles_y_timestamp():
    """[INVARIANZA 3 - FIXTURES]: Debe parsear partidos con goles, equipos, momios 1X2 y epoch UTC."""
    m = _parser()
    raiz_raw = Path("data/raw_footystats")
    carpeta_1516 = raiz_raw / "2015_2016"
    archivo_fixtures = next(carpeta_1516.glob("Fixtures*.mhtml"))
    html = m.extraer_html_de_mhtml(archivo_fixtures)

    partidos = m.parsear_archivo_fixtures_html(html, temporada="2015_2016")
    assert len(partidos) >= 300, f"Esperados >=300 partidos, extraídos: {len(partidos)}"

    p0 = partidos[0]
    assert "home_team" in p0 and "away_team" in p0
    assert "home_goals" in p0 and "away_goals" in p0
    assert "odd_home" in p0 and "odd_draw" in p0 and "odd_away" in p0
    assert "fecha_utc" in p0 and p0["fecha_utc"] is not None
    assert isinstance(p0["home_goals"], int)
    assert p0["odd_home"] > 1.0


def test_invarianza_parseo_xg_macro_desde_2018():
    """[INVARIANZA 4 - XG MACRO >= 2018]: xG_*.mhtml debe parsear tabla macro de xG/xGA por club."""
    m = _parser()
    raiz_raw = Path("data/raw_footystats")
    carpeta_1819 = raiz_raw / "2018_2019"
    archivo_xg = next(carpeta_1819.glob("xG*.mhtml"), None)
    assert archivo_xg is not None, "Falta xG_18-19.mhtml en 2018_2019"

    html = m.extraer_html_de_mhtml(archivo_xg)
    tabla_xg = m.parsear_archivo_xg_macro_html(html, temporada="2018_2019")

    assert len(tabla_xg) >= 18, f"Se esperaban 18 clubes en tabla xG, obtenidos: {len(tabla_xg)}"
    c0 = tabla_xg[0]
    assert "team" in c0 and "xg" in c0 and "xga" in c0
    assert c0["fuente_xg"] == "FOOTYSTATS_PROPIETARIO"
    assert c0["xg"] > 0.0
