# -*- coding: utf-8 -*-
"""
🏆 THE SHIELD — PUENTE DE DATOS V2 (MATRIZ CAUSAL HISTÓRICA)
Juez Inmutable: [LN-QBE-150] · [LN-QBE-039] §7.6
Base de Gobierno: docs/LOGIC.md §7.6 · docs/DIRGEN_VAULT.md §E-50.1
Régimen: [DIRGEN-STRICT] — Inmutable, Cero Mocks.
Expediente: SPRINT-50-REINGENIERIA-INDUSTRIAL-QBE-CORE (Fase 3)
"""

from __future__ import annotations

import sqlite3
import sys
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


def _fila(match_id, fecha, local, visita, gl, gv, temporada="2018_2019"):
    return (match_id, temporada, fecha, local, visita, local, visita, gl, gv)


def _serie(n: int, base_v01: float, base_v07: float, base_v13: float, base_v14: float):
    """Historial de un club: patrones NO proporcionales (evita colinealidad espuria)."""
    return [
        {
            "V01": base_v01 + float(i % 3),
            "V07": base_v07 + 0.15 * i,
            "V13": base_v13 - 0.05 * i,
            "V14": base_v14 + float((i * 2) % 4),
        }
        for i in range(n)
    ]


MEDIAS = {"V01": 1.0, "V07": 1.5, "V13": 1.2, "V14": 0.8}


def _matriz(local, visita):
    return {
        "local": local,
        "visita": visita,
        "vector_local": calc.AcumuladorCausal._media(local),
        "vector_visita": calc.AcumuladorCausal._media(visita),
        "medias_liga": dict(MEDIAS),
    }


def _registro(matriz):
    return {
        "home_team_stats": {"pj": 10, "gf": 18, "gc": 11},
        "away_team_stats": {"pj": 10, "gf": 14, "gc": 13},
        "home_team_slug": "america",
        "away_team_slug": "tigres",
        "matriz_causal": matriz,
    }


# ── 1. Acumulador: cero fuga temporal ────────────────────────────────────────────────────────
def test_acumulador_no_incluye_el_partido_evaluado() -> None:
    acumulador = calc.AcumuladorCausal()
    acumulador.registrar("2018_2019", "america", "tigres", {"v07_local": 3.0}, {"v13_visita": 2.0})

    matriz = acumulador.matriz_causal("2018_2019", "america", "tigres")
    assert len(matriz["local"]) == 1
    assert len(matriz["visita"]) == 1
    assert matriz["vector_local"]["V07"] == pytest.approx(3.0)
    assert "V13" not in matriz["vector_local"], "El vector local no debe mezclar el lado visita."

    # Una segunda evaluación sin registrar nada nuevo devuelve exactamente el mismo estado.
    assert acumulador.matriz_causal("2018_2019", "america", "tigres") == matriz


def test_acumulador_excluye_celdas_sin_dominio_logaritmico() -> None:
    """[§7.6.3] Una celda ≤ −ε no admite log-diferencial: se excluye, jamás se imputa."""
    plano = calc.AcumuladorCausal._plano({"v27_local": -5.0, "v30_local": 3.0, "v07_local": 4.0}, "local")
    assert "V27" not in plano
    assert plano["V30"] == pytest.approx(3.0)
    assert plano["V07"] == pytest.approx(4.0)


def test_acumulador_trunca_a_la_ventana_legislada() -> None:
    acumulador = calc.AcumuladorCausal(max_filas=3)
    for indice in range(6):
        acumulador.registrar(
            "2018_2019", "america", "tigres", {"v07_local": float(indice)}, {"v13_visita": 1.0}
        )
    matriz = acumulador.matriz_causal("2018_2019", "america", "tigres")
    assert len(matriz["local"]) == 3
    assert [fila["V07"] for fila in matriz["local"]] == [3.0, 4.0, 5.0]


# ── 2. La matriz gobierna el motor (V2) ─────────────────────────────────────────────────────
def test_matriz_causal_activa_gsl3d_v2() -> None:
    matriz = _matriz(_serie(10, 0.8, 1.2, 1.6, 0.5), _serie(10, 0.6, 1.0, 1.4, 0.7))
    salida = calc.generar_distribucion_soberana("TEST-PUENTE-V2", _registro(matriz))

    assert salida.es_operable is True
    assert salida.origen_factores == "gsl3d_v2", (
        f"La matriz causal debe gobernar la derivación; procedencia={salida.origen_factores!r}."
    )
    assert salida.audit_trace.gsl3d is not None
    assert salida.lambda_home > 0.0 and salida.lambda_away > 0.0
    assert abs(salida.p_local + salida.p_empate + salida.p_visitante - 1.0) <= 1e-12


def test_cold_start_declara_matriz_insuficiente() -> None:
    """Una sola fila por club es ℝ¹: toda columna es colineal ⇒ SIN EVIDENCIA declarada."""
    matriz = _matriz(_serie(1, 0.8, 1.2, 1.6, 0.5), _serie(1, 0.6, 1.0, 1.4, 0.7))
    salida = calc.generar_distribucion_soberana("TEST-PUENTE-COLD", _registro(matriz))

    assert salida.es_operable is False
    assert salida.audit_trace.suficiencia_S_I == 0
    assert "MATRIZ_CAUSAL_INSUFICIENTE" in (salida.audit_trace.motivo_insuficiencia or "")


# ── 3. End-to-end: V2 persiste en su propia tabla ───────────────────────────────────────────
def _base_temporal(tmp_path: Path):
    db = tmp_path / "qbe_historico.db"
    conexion = sqlite3.connect(str(db))
    try:
        conexion.execute(BOVEDA_MINIMA)
        asegurar_esquema(conexion)
        filas = []
        # 5 fechas previas: cada club acumula 5 filas antes del objetivo.
        for indice in range(5):
            filas.append(_fila(f"a{indice}", f"2018-07-{indice + 1:02d}T00:00:00Z", "america", f"r{indice}", 2, 1))
            filas.append(_fila(f"b{indice}", f"2018-07-{indice + 1:02d}T00:00:00Z", f"s{indice}", "tigres", 1, 1))
        filas.append(_fila("objetivo", "2018-09-01T00:00:00Z", "america", "tigres", 2, 0))
        conexion.executemany("INSERT INTO historical_matches VALUES (?,?,?,?,?,?,?,?,?)", filas)
        for indice in range(5):
            for match_id, lado in ((f"a{indice}", "local"), (f"b{indice}", "visita")):
                conexion.execute(
                    "INSERT INTO historical_match_causal_vars "
                    "(match_id, v01_local, v07_local, v13_local, v14_local, "
                    " v01_visita, v07_visita, v13_visita, v14_visita, fuente_datos) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (
                        match_id,
                        0.8 + indice, 1.2 + 0.3 * indice, 1.6 - 0.1 * indice, 0.5 + 0.2 * indice,
                        0.6 + indice, 1.0 + 0.25 * indice, 1.4 - 0.08 * indice, 0.7 + 0.15 * indice,
                        "TEST",
                    ),
                )
        conexion.execute(
            "INSERT INTO historical_match_causal_vars "
            "(match_id, v01_local, v07_local, v13_local, v14_local, "
            " v01_visita, v07_visita, v13_visita, v14_visita, fuente_datos) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            ("objetivo", 1.0, 2.0, 1.2, 0.9, 0.9, 1.8, 1.3, 0.8, "TEST"),
        )
        conexion.commit()
    finally:
        conexion.close()
    return db


def test_calculo_v2_persiste_en_tabla_v2(tmp_path: Path) -> None:
    db = _base_temporal(tmp_path)
    reporte = calc.calcular(db, "2018_2019", motor=calc.MOTOR_V2)

    assert reporte["motor"] == calc.MOTOR_V2
    assert reporte["tabla"] == calc.TABLA_DESTINO_V2
    assert reporte["generadas"] >= 1

    verificacion = sqlite3.connect(str(db))
    try:
        v2 = verificacion.execute(
            f"SELECT p_local, p_empate, p_visitante, model_version FROM {calc.TABLA_DESTINO_V2}"
        ).fetchall()
        existe_v1 = verificacion.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (calc.TABLA_DESTINO,)
        ).fetchone()
        v1 = (
            verificacion.execute(f"SELECT COUNT(*) FROM {calc.TABLA_DESTINO}").fetchone()[0]
            if existe_v1
            else 0
        )
    finally:
        verificacion.close()

    assert len(v2) == reporte["generadas"]
    assert v1 == 0, "El motor V2 no debe escribir en la tabla V1."
    for p_local, p_empate, p_visitante, version in v2:
        assert p_local + p_empate + p_visitante == pytest.approx(1.0, abs=1e-9)
        assert version == calc.MODEL_VERSION_V2
