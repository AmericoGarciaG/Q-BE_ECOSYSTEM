# -*- coding: utf-8 -*-
"""🏆 THE SHIELD — `[LN-QBE-146]` §19.1 EXTRACCIÓN HISTÓRICA FOTMOB.

Certifica el contrato de la fuente alterna declarada en `[LN-QBE-146]` §19.1:

* la cadencia anti-WAF es exactamente `1.0 s` por petición;
* las 32 variables del catálogo `[LN-QBE-120]` están repartidas 24 + 4 + 2 + 1 + 1
  y `V16` queda `FUERA DE FUENTE` (nunca imputada);
* el parser de `matchDetails` respeta las identidades declaradas y devuelve `None`
  —no `0.0`— cuando el proveedor no publica la métrica;
* el contexto `V26`–`V32` se calcula sin fuga temporal: el partido evaluado y los
  posteriores a él jamás entran en su propia evidencia;
* el join bóveda ↔ FotMob es determinista y declara los no emparejados.

El Juez es determinista: no toca la red ni la bóveda real.
"""

from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from scripts.auditoria import extraer_historico_fotmob as ex  # noqa: E402


# ── Payload de referencia: estructura real de `matchDetails` (Liga MX 2018/19) ─────────────
def _payload_referencia() -> dict:
    return {
        "header": {"status": {"scoreStr": "0 - 2"}},
        "content": {
            "stats": {
                "Periods": {
                    "All": {
                        "stats": [
                            {
                                "title": "Top stats",
                                "stats": [
                                    {"key": "BallPossesion", "stats": [57, 43]},
                                    {"key": "total_shots", "stats": [8, 13]},
                                    {"key": "ShotsOnTarget", "stats": [1, 3]},
                                    {"key": "big_chance", "stats": [1, 2]},
                                    {"key": "big_chance_missed_title", "stats": [1, 0]},
                                    {"key": "accurate_passes", "stats": ["282 (77%)", "189 (69%)"]},
                                    {"key": "corners", "stats": [2, 8]},
                                ],
                            },
                            {
                                "title": "Passes",
                                "stats": [
                                    {"key": "long_balls_accurate", "stats": ["24 (44%)", "30 (43%)"]},
                                ],
                            },
                            {
                                "title": "Defence",
                                "stats": [
                                    {"key": "matchstats.headers.tackles", "stats": [24, 15]},
                                    {"key": "interceptions", "stats": [11, 24]},
                                    {"key": "clearances", "stats": [21, 28]},
                                    {"key": "keeper_saves", "stats": [1, 1]},
                                ],
                            },
                            {
                                "title": "Discipline",
                                "stats": [
                                    {"key": "yellow_cards", "stats": [0, 1]},
                                    {"key": "red_cards", "stats": [0, 0]},
                                    {"key": "fouls", "stats": [15, 11]},
                                ],
                            },
                        ]
                    }
                }
            }
        },
    }


def _vector_referencia() -> dict:
    plano = ex._plano_stats(_payload_referencia())
    return ex._variables_de_stats(plano, ex._marcador(_payload_referencia()))


# ── Cadencia anti-WAF ──────────────────────────────────────────────────────────────────────
def test_cadencia_anti_waf_es_un_segundo() -> None:
    """[WAF] Una petición cada 1.0 s es la cadencia legislada del extractor."""
    assert ex.PAUSA_ENTRE_PETICIONES == 1.0


# ── Reparto canónico del dictamen V2 ───────────────────────────────────────────────────────
def test_reparto_canonico_24_4_2_1_1() -> None:
    """Las 32 variables se reparten sin huérfanas ni solapes."""
    directas = {variable for variable, claves in ex.CLAVES_DIRECTAS.items() if claves and variable != "V16"}
    assert len(directas) == 24
    assert len(ex.CLAVES_CONTEXTO) == 4
    assert len(ex.CLAVES_FIXTURE) == 2
    assert len(ex.CLAVES_DERIVADAS) == 1
    assert set(ex.VARIABLES) == directas | set(ex.CLAVES_CONTEXTO) | set(ex.CLAVES_FIXTURE) | set(ex.CLAVES_DERIVADAS) | {"V16"}
    for grupo in (ex.CLAVES_CONTEXTO, ex.CLAVES_FIXTURE, ex.CLAVES_DERIVADAS, directas, {"V16"}):
        assert len(grupo) == len(set(grupo))


def test_v16_fuera_de_fuente_sin_mapeo() -> None:
    """[GOVERNANCE-01] `V16` no tiene clave de origen: se declara, no se imputa."""
    assert ex.CLAVES_DIRECTAS["V16"] == ()
    assert _vector_referencia()["V16"] == {"local": None, "visita": None}


# ── Parser de `matchDetails` ───────────────────────────────────────────────────────────────
def test_parser_respeta_identidades_declaradas() -> None:
    vector = _vector_referencia()
    assert vector["V01"] == {"local": 57.0, "visita": 43.0}
    assert vector["V03"] == {"local": 282.0, "visita": 189.0}  # "282 (77%)"
    assert vector["V07"] == {"local": 1.0, "visita": 3.0}
    assert vector["V13"] == {"local": 3.0, "visita": 1.0}  # dual exacto de V07
    assert vector["V14"] == {"local": 56.0, "visita": 67.0}  # tackles+clearances+interceptions
    assert vector["V23"] == {"local": 2.0, "visita": 8.0}
    assert vector["V25"] == {"local": 0.0, "visita": 1.0}  # amarillas + rojas


def test_parser_declara_null_lo_que_el_proveedor_no_publica() -> None:
    """La era pre-xG no inventa xG: el slot queda `NULL`, jamás `0.0`."""
    vector = _vector_referencia()
    for variable in ("V06", "V10", "V11", "V12", "V17", "V19", "V21", "V22", "V24"):
        assert vector[variable] == {"local": None, "visita": None}, variable
    assert vector["V02"] == {"local": None, "visita": None}


def test_save_pct_y_clean_sheet_con_denominador_real() -> None:
    vector = _vector_referencia()
    assert vector["V18"]["local"] == pytest.approx(100.0 * 1 / 3, abs=1e-4)
    assert vector["V18"]["visita"] == pytest.approx(100.0 * 1 / 1, abs=1e-4)
    assert vector["V20"] == {"local": 0.0, "visita": 1.0}


def test_sin_bloque_de_stats_no_hay_vector_parcial() -> None:
    assert ex._plano_stats({}) == {}
    assert ex._plano_stats({"content": {"stats": {"Periods": {}}}}) == {}


def test_numeros_con_porcentaje_y_nulos() -> None:
    assert ex._a_numero("282 (77%)") == 282.0
    assert ex._a_numero("44%") == 44.0
    assert ex._a_numero(8) == 8.0
    assert ex._a_numero(None) is None
    assert ex._a_numero(True) is None
    assert ex._a_numero("sin dato") is None


# ── Contexto sin fuga temporal ────────────────────────────────────────────────────────────
def _fila(match_id: str, fecha: str, local: str, visita: str, gl: int, gv: int) -> dict:
    return {
        "match_id": match_id,
        "temporada": "2018_2019",
        "fecha_utc": fecha,
        "home_team_slug": local,
        "away_team_slug": visita,
        "home_goals": gl,
        "away_goals": gv,
    }


def test_contexto_no_ve_el_futuro() -> None:
    """[INVARIANTE] Un H2H posterior al kickoff no contamina `V26`/`V27`."""
    objetivo = _fila("m3", "2018-09-01T00:00:00Z", "america", "tigres", 1, 0)
    corpus = ex.Historico(
        [
            _fila("m1", "2018-01-01T00:00:00Z", "america", "tigres", 3, 0),
            _fila("m2", "2018-05-01T00:00:00Z", "america", "tigres", 2, 2),
            objetivo,
            _fila("m4", "2019-01-01T00:00:00Z", "tigres", "america", 9, 0),
        ]
    )
    momento = datetime(2018, 9, 1, tzinfo=timezone.utc)
    vector = ex._contexto(corpus, objetivo, momento)
    assert vector["V26"]["local"] == pytest.approx(0.5, abs=1e-4)  # 1 victoria + 1 empate
    assert vector["V27"]["local"] == pytest.approx(1.5, abs=1e-4)  # (3 + 0) / 2
    assert vector["V31"]["local"] == pytest.approx(4.0, abs=1e-4)  # 3 + 1 puntos en 2 partidos


def test_altitud_es_diferencial_positivo_del_anfitrion() -> None:
    fila = _fila("m1", "2018-09-01T00:00:00Z", "pachuca", "tijuana", 0, 0)
    corpus = ex.Historico([fila])
    vector = ex._contexto(corpus, fila, datetime(2018, 9, 1, tzinfo=timezone.utc))
    assert vector["V29"]["local"] >= 0.0
    assert vector["V29"]["visita"] == -vector["V29"]["local"]


# ── Join determinista ────────────────────────────────────────────────────────────────────
def test_join_por_sello_unico_y_declaracion_de_huerfanos() -> None:
    boveda = [
        _fila("m1", "2018-07-21T00:00:00Z", "veracruz", "pumas-unam", 0, 2),
        _fila("m2", "2018-07-21T02:00:00Z", "atlas", "queretaro", 0, 0),
    ]
    fixtures = [
        {"id": "1", "home": {"name": "Veracruz", "id": "1"}, "away": {"name": "Pumas", "id": "2"},
         "status": {"utcTime": "2018-07-21T00:00:00Z"}},
        {"id": "2", "home": {"name": "Atlas", "id": "3"}, "away": {"name": "Queretaro", "id": "4"},
         "status": {"utcTime": "2018-07-21T02:00:00Z"}},
        {"id": "3", "home": {"name": "Nadie", "id": "5"}, "away": {"name": "Tampoco", "id": "6"},
         "status": {"utcTime": "2019-01-01T00:00:00Z"}},
    ]
    parejas, huerfanos = ex._emparejar(fixtures, boveda)
    assert {fila["match_id"] for _, fila in parejas} == {"m1", "m2"}
    assert len(huerfanos) == 1 and huerfanos[0]["fotmob_id"] == "3"


# ── DDL ───────────────────────────────────────────────────────────────────────────────────
def test_ddl_refleja_las_64_columnas_del_vector() -> None:
    conexion = sqlite3.connect(":memory:")
    try:
        ex.asegurar_esquema(conexion)
        ex.asegurar_esquema(conexion)  # idempotente
        columnas = {fila[1] for fila in conexion.execute('PRAGMA table_info("historical_match_causal_vars")')}
        for indice in range(1, 33):
            assert f"v{indice:02d}_local" in columnas
            assert f"v{indice:02d}_visita" in columnas
        assert {"match_id", "sin_evidencia", "derivadas", "fuente_datos", "cargado_utc"} <= columnas
    finally:
        conexion.close()


def test_fila_declara_sin_evidencia_sin_imputar() -> None:
    vector = _vector_referencia()
    for variable in ex.VARIABLES:
        vector[variable] = {"local": None, "visita": None}
    vector["V01"] = {"local": 50.0, "visita": 50.0}
    fila = ex._fila("m1", vector)
    declaradas = fila[-4]
    assert "V01" not in declaradas and "V16" in declaradas
    assert fila[-3] == 1  # derivadas = variables con evidencia
    assert fila[-2] == ex.FUENTE_DATOS
