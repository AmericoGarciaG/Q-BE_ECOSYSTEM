# -*- coding: utf-8 -*-
"""
🏆 THE SHIELD — HISTORICAL BULK LOAD INTEGRITY SUITE
Juez Inmutable: [LN-QBE-135] / [ARCH-1.4.72]
Base de Gobierno: Kybern Framework v13.5 [GOV-TEST-01]

Nota de aislamiento: el import del loader es diferido dentro de cada prueba
para no contaminar `sys.modules` durante la colecta (mismo defecto detectado
en el Sprint 37 con el Juez de Business).
"""

import os
import sqlite3
import pytest
from pathlib import Path


def _loader():
    from qbe_ingestion.src.ingestion.loaders import load_historical_footystats

    return load_historical_footystats


@pytest.fixture
def db_efimera(tmp_path):
    """Provee una base de datos SQLite efímera para pruebas de carga masiva."""
    db_path = tmp_path / "test_historico.db"
    return str(db_path)


def test_invarianza_carga_historica_crea_esquema_si_no_existe(db_efimera):
    """[INVARIANZA 1 - DDL DINÁMICO]: El loader debe crear las tablas necesarias si la BD es nueva."""
    m = _loader()
    # JSON Mock de 1 partido
    datos_mock = {
        "partidos": [{
            "match_id": "fs_2015_2016_tigres_toluca", "fecha_utc": 1437847200,
            "home_team": "tigres-uanl", "away_team": "deportivo-toluca",
            "home_goals": 0, "away_goals": 1,
            "odd_home": 1.76, "odd_draw": 3.42, "odd_away": 4.62
        }],
        "xg_macro": [], "forma": []
    }

    m.inyectar_temporada_en_db(db_efimera, "2015_2016", datos_mock)

    conn = sqlite3.connect(db_efimera)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tablas = [row[0] for row in cursor.fetchall()]
    conn.close()

    assert "historical_matches" in tablas or "matches" in tablas, "Falta tabla principal de partidos"


def test_invarianza_carga_historica_es_idempotente(db_efimera):
    """[INVARIANZA 2 - IDEMPOTENCIA]: Re-ejecutar la carga no debe duplicar los registros."""
    m = _loader()
    datos_mock = {
        "partidos": [{
            "match_id": "fs_2018_2019_cruz_azul_puebla", "fecha_utc": 1532217600,
            "home_team": "cruz-azul", "away_team": "club-puebla",
            "home_goals": 3, "away_goals": 0,
            "odd_home": 1.83, "odd_draw": 3.20, "odd_away": 4.10
        }],
        "xg_macro": [], "forma": []
    }

    # Carga 1
    m.inyectar_temporada_en_db(db_efimera, "2018_2019", datos_mock)
    # Carga 2 (repetida)
    m.inyectar_temporada_en_db(db_efimera, "2018_2019", datos_mock)

    conn = sqlite3.connect(db_efimera)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM historical_matches")
    conteo = cursor.fetchone()[0]
    conn.close()

    assert conteo == 1, f"Fallo de idempotencia: el registro fue duplicado (conteo={conteo})"


def test_invarianza_manejo_de_nulos_para_partidos_no_jugados(db_efimera):
    """[INVARIANZA 3 - CERO MOCKS]: Partidos sin goles (COVID/Futuro) deben insertarse como NULL, no 0."""
    m = _loader()
    datos_mock = {
        "partidos": [{
            "match_id": "fs_2019_2020_covid", "fecha_utc": None,
            "home_team": "pumas-unam", "away_team": "club-leon",
            "home_goals": None, "away_goals": None,
            "odd_home": None, "odd_draw": None, "odd_away": None
        }],
        "xg_macro": [], "forma": []
    }

    m.inyectar_temporada_en_db(db_efimera, "2019_2020", datos_mock)

    conn = sqlite3.connect(db_efimera)
    cursor = conn.cursor()
    cursor.execute("SELECT home_goals, odd_home FROM historical_matches WHERE match_id='fs_2019_2020_covid'")
    row = cursor.fetchone()
    conn.close()

    assert row[0] is None, "Goles nulos fueron forzados a un valor distinto de NULL"
    assert row[1] is None, "Cuotas nulas fueron forzadas a un valor distinto de NULL"
