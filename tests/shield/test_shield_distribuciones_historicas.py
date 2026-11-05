# -*- coding: utf-8 -*-
"""🏆 THE SHIELD — `[LN-QBE-150]` DISTRIBUCIONES HISTÓRICAS (P').

Certifica el contrato del motor de cálculo histórico:

* el DDL de `historical_sovereign_distributions` existe y es idempotente
  (`[ARCH-1.5.1]` §15.5);
* la aduana de suficiencia `S(I_i) = 3` descarta sin imputar;
* el registro fáctico de entrada se construye **sin fuga temporal**: el marcador
  del partido evaluado no entra en su propio agregado;
* la matemática se delega en `qbe_core` y el símplex publicado suma 1;
* el cálculo end-to-end persiste sólo los partidos operables y declara el resto.

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

from scripts.auditoria import calcular_distribuciones_historicas as calc  # noqa: E402
from scripts.auditoria.extraer_historico_fotmob import asegurar_esquema  # noqa: E402


BOVEDA_MINIMA = """
CREATE TABLE IF NOT EXISTS historical_matches (
    match_id        TEXT PRIMARY KEY,
    temporada       TEXT NOT NULL,
    fecha_utc       TEXT NOT NULL,
    home_team       TEXT,
    away_team       TEXT,
    home_team_slug  TEXT,
    away_team_slug  TEXT,
    home_goals      INTEGER,
    away_goals      INTEGER
)
"""


def _fila(match_id: str, fecha: str, local: str, visita: str, gl, gv, temporada: str = "2018_2019") -> tuple:
    return (match_id, temporada, fecha, local, visita, local, visita, gl, gv)


def _conexion(filas) -> sqlite3.Connection:
    conexion = sqlite3.connect(":memory:")
    conexion.execute(BOVEDA_MINIMA)
    asegurar_esquema(conexion)
    conexion.executemany(
        "INSERT INTO historical_matches VALUES (?,?,?,?,?,?,?,?,?)", list(filas)
    )
    return conexion


# ── DDL ───────────────────────────────────────────────────────────────────────────────────
def test_ddl_de_distribuciones_historicas_es_idempotente(tmp_path: Path) -> None:
    conexion = sqlite3.connect(":memory:")
    try:
        conexion.execute(calc.DDL)
        conexion.execute(calc.DDL)
        columnas = {fila[1] for fila in conexion.execute(f'PRAGMA table_info("{calc.TABLA_DESTINO}")')}
    finally:
        conexion.close()
    requeridas = {
        "match_id", "temporada", "model_version", "p_local", "p_empate", "p_visitante",
        "lambda_home", "lambda_away", "phi_lead2_home", "phi_lead2_away", "epistemic_delta",
        "delta_epist", "origen_factores", "es_operable", "pj_home", "pj_away", "duelos_h2h",
        "variables_con_evidencia", "origen", "fuente_causal", "audit_trace_json", "created_at",
    }
    assert requeridas <= columnas


# ── Aduana de suficiencia ────────────────────────────────────────────────────────────────
def test_umbral_de_suficiencia_es_tres() -> None:
    assert calc.PARTIDOS_MINIMOS_SI == 3


def test_sin_tres_partidos_previos_se_descarta_sin_imputar() -> None:
    """[GOVERNANCE-01] Dos partidos previos no bastan: se salta y se declara el motivo."""
    conexion = _conexion(
        [
            _fila("m1", "2018-07-01T00:00:00Z", "america", "x", 1, 0),
            _fila("m2", "2018-07-08T00:00:00Z", "america", "y", 2, 0),
            _fila("objetivo", "2018-09-01T00:00:00Z", "america", "tigres", 0, 0),
        ]
    )
    try:
        conexion.execute("INSERT INTO historical_match_causal_vars (match_id) VALUES ('objetivo')")
        fila = {
            "match_id": "objetivo",
            "temporada": "2018_2019",
            "fecha_utc": "2018-09-01T00:00:00Z",
            "home_team_slug": "america",
            "away_team_slug": "tigres",
        }
        entrada, motivo = calc.construir_entrada(conexion, calc.Corpus(calc._filas(conexion, "SELECT * FROM historical_matches")), fila, {"v29_local": None, "v30_local": None})
        assert entrada is None
        assert motivo is not None and motivo.startswith("SI_insuficiente")
    finally:
        conexion.close()


# ── Cero fuga temporal ───────────────────────────────────────────────────────────────────
def test_agregado_de_entrada_excluye_el_partido_evaluado() -> None:
    """El marcador 9-0 del propio partido NO contamina su registro de entrada."""
    conexion = _conexion(
        [
            _fila("p1", "2018-07-01T00:00:00Z", "america", "x", 1, 0),
            _fila("p2", "2018-07-08T00:00:00Z", "america", "y", 2, 1),
            _fila("p3", "2018-07-15T00:00:00Z", "america", "z", 3, 0),
            _fila("p4", "2018-07-22T00:00:00Z", "w", "tigres", 0, 1),
            _fila("p5", "2018-07-29T00:00:00Z", "v", "tigres", 1, 1),
            _fila("p6", "2018-08-05T00:00:00Z", "u", "tigres", 0, 2),
            _fila("objetivo", "2018-09-01T00:00:00Z", "america", "tigres", 9, 0),
        ]
    )
    try:
        conexion.execute("INSERT INTO historical_match_causal_vars (match_id) VALUES ('objetivo')")
        fila = {
            "match_id": "objetivo",
            "temporada": "2018_2019",
            "fecha_utc": "2018-09-01T00:00:00Z",
            "home_team_slug": "america",
            "away_team_slug": "tigres",
        }
        corpus = calc.Corpus(calc._filas(conexion, "SELECT * FROM historical_matches"))
        entrada, motivo = calc.construir_entrada(
            conexion, corpus, fila, {"v29_local": 1200.0, "v30_local": -1.0}
        )
        assert motivo is None and entrada is not None
        assert entrada["home_team_stats"]["pj"] == 3
        assert entrada["home_team_stats"]["gf"] == 6.0
        assert entrada["home_team_stats"]["gc"] == 1.0
        assert entrada["away_team_stats"]["pj"] == 3
        assert entrada["away_team_stats"]["gf"] == 4.0
        assert entrada["away_team_stats"]["gc"] == 1.0
        assert entrada["delta_alt_metros"] == pytest.approx(1200.0)
        assert entrada["delta_descanso_dias"] == pytest.approx(-1.0)
    finally:
        conexion.close()


# ── Delegación en `qbe_core` ────────────────────────────────────────────────────────────
def test_motor_soberano_produce_un_simplex_valido() -> None:
    """El símplex P' se publica normalizado y con intensidades positivas."""
    raw = {
        "home_team_stats": {"pj": 8, "gf": 14, "gc": 9, "xg": 0.0, "xga": 0.0},
        "away_team_stats": {"pj": 8, "gf": 10, "gc": 12, "xg": 0.0, "xga": 0.0},
        "home_team_slug": "pachuca",
        "delta_alt_metros": 2400.0,
        "delta_descanso_dias": 2.0,
        "h2h_matches": [{"dias_antiguedad": 300.0, "goles_local": 2.0, "goles_visita": 1.0}],
    }
    salida = calc.generar_distribucion_soberana(
        "prueba", raw, delta_alt_metros=2400.0, delta_descanso_dias=2.0
    )
    assert salida.es_operable is True
    assert salida.p_local + salida.p_empate + salida.p_visitante == pytest.approx(1.0, abs=1e-9)
    assert salida.lambda_home > 0.0 and salida.lambda_away > 0.0
    assert 0.0 <= salida.phi_lead2_home <= 1.0
    assert salida.origen_factores in {"analitico_base", "bayesiano_10p"}


# ── End-to-end sin red ──────────────────────────────────────────────────────────────────
def test_calculo_persiste_solo_partidos_operables(tmp_path: Path) -> None:
    db = tmp_path / "qbe_historico.db"
    conexion = sqlite3.connect(str(db))
    try:
        conexion.execute(BOVEDA_MINIMA)
        asegurar_esquema(conexion)
        filas = []
        for indice in range(1, 5):
            filas.append(_fila(f"p{indice}", f"2018-07-0{indice}T00:00:00Z", "america", f"r{indice}", 2, 1))
            filas.append(_fila(f"q{indice}", f"2018-07-0{indice}T00:00:00Z", f"s{indice}", "tigres", 0, 1))
        filas.append(_fila("objetivo", "2018-09-01T00:00:00Z", "america", "tigres", 1, 1))
        filas.append(_fila("temprano", "2018-07-02T00:00:00Z", "nuevo", "otro", 0, 0))
        conexion.executemany("INSERT INTO historical_matches VALUES (?,?,?,?,?,?,?,?,?)", filas)
        for match_id in ("objetivo", "temprano"):
            conexion.execute("INSERT INTO historical_match_causal_vars (match_id) VALUES (?)", (match_id,))
        conexion.commit()
    finally:
        conexion.close()

    # [SPRINT-50] El motor V2 es el estándar: este Juez certifica la RUTA V1 (baseline sellado)
    # de forma explícita, porque su fixture no publica matriz causal (V2 declararía SIN EVIDENCIA).
    reporte = calc.calcular(db, "2018_2019", motor=calc.MOTOR_V1)
    assert reporte["candidatos"] == 2
    assert reporte["generadas"] == 1
    assert reporte["saltadas"] == 1
    assert reporte["integridad"] == "ok"
    assert any(registro["match_id"] == "temprano" for registro in reporte["detalle_saltadas"])

    verificacion = sqlite3.connect(str(db))
    try:
        fila = verificacion.execute(
            "SELECT p_local, p_empate, p_visitante, es_operable, model_version "
            "FROM historical_sovereign_distributions"
        ).fetchall()
    finally:
        verificacion.close()
    assert len(fila) == 1
    p1, px, p2, operable, version = fila[0]
    assert p1 + px + p2 == pytest.approx(1.0, abs=1e-9)
    assert operable == 1 and version == calc.MODEL_VERSION
