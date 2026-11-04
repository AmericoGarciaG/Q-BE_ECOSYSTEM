# -*- coding: utf-8 -*-
"""🏆 THE SHIELD — `[SPRINT-47]` CONSENSO DE MERCADO: D1–D10 ERRADICADOS.

Juez inmutable del expediente `SPRINT-47-UNIFICACION-FOTMOB-Y-LANZADOR`.
Certifica, hallazgo por hallazgo, que la refactorización de `sabiduria_view.py`,
`consenso_view.py` y `calibration_view.py` erradicó las inconsistencias
detectadas en la auditoría `SPRINT-47-AUDITORIA-CONSENSO`:

  D1  La temporada histórica vacía el panel de Mercado en vivo (motivo explícito).
  D2  La caída de la bóveda histórica lanza `HistoricoDBError` y la UI lo declara;
      jamás se degrada en silencio hacia el snapshot vivo.
  D3  La temporada vigente usa el reporte; una temporada desconocida NO hereda el
      snapshot vivo (queda sin evidencia, declarada).
  D4  El KPI es la media ponderada por partidos de los bloques de la tabla.
  D5  Una sola fila de mercado por bloque (sin duplicado Consenso/FootyStats) y
      los pesos suman 1.0.
  D6  Un casino sin evidencia histórica se rotula con su nombre y `SIN EVIDENCIA`;
      jamás se suplanta su identidad con la etiqueta de otra fuente.
  D7  El peso del panel vivo es real: 1 / casinos seleccionados (0.500 con dos).
  D8  Sin jornada declarada no se inventa `jornada=0`; con jornada declarada se
      emiten bloques J1…Jn.
  D9  El panel vivo declara la jornada SERVIDA, no la solicitada.
  D10 El código muerto y la regla de suplantación fueron eliminados.

Hermeticidad: bóvedas y snapshots son sintéticos (`tmp_path` + monkeypatch); el
Juez no depende de datos mutables ni escribe en producción.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ / "qbe_observatory") not in sys.path:
    sys.path.insert(0, str(RAIZ / "qbe_observatory"))

import pytest  # noqa: E402

import app.services.sabiduria_view as sabiduria_view  # noqa: E402
from app.services import calibration_view, consenso_view  # noqa: E402
from app.services.calibration_view import HistoricoDBError  # noqa: E402
from app.services.sabiduria_view import (  # noqa: E402
    MOTIVO_TEMPORADA_HISTORICA,
    _agrupar_por_jornada,
    _consenso_casinos,
    construir_mercado_vivo,
    construir_sabiduria_masas,
)

CASINO_A = "caliente"
CASINO_B = "novibet"
CASINOS = [CASINO_A, CASINO_B]
CUOTAS_A = (2.10, 3.40, 3.60)
CUOTAS_B = (1.95, 3.55, 3.90)
CUOTAS_QBE = (1.10, 8.00, 15.00)
TEMPORADA_HISTORICA = "2015_2016"
TEMPORADA_VIGENTE = "2026_2027"


# ── Utilidades ────────────────────────────────────────────────────────────────
def _simplex(cuotas: tuple[float, float, float]) -> tuple[float, float, float]:
    inversas = [1.0 / cuota for cuota in cuotas]
    total = sum(inversas)
    return (inversas[0] / total, inversas[1] / total, inversas[2] / total)


def _reporte() -> dict:
    """Universo de 30 partidos: J1 con Brier 0.10 (10 partidos) y J2 con 0.40 (20).

    El agregado ponderado por partidos es (10·0.10 + 20·0.40) / 30 = 0.30.
    La media aritmética de los Brier de jornada sería 0.25: el Juez exige 0.30.
    """
    return {
        "resumen_temporada": {
            "brier_score_mercado": 0.30,
            "brier_score_qbe": 0.2333,
            "alpha_calibracion_pct": 22.23,
            "total_partidos": 30,
        },
        "jornadas": [
            {
                "jornada": 1,
                "total_partidos": 10,
                "brier_score_mercado": 0.10,
                "brier_score_qbe": 0.10,
                "partidos": [
                    {"brier_mercado": 0.10, "brier_qbe": 0.10} for _ in range(10)
                ],
            },
            {
                "jornada": 2,
                "total_partidos": 20,
                "brier_score_mercado": 0.40,
                "brier_score_qbe": 0.30,
                "partidos": [
                    {"brier_mercado": 0.40, "brier_qbe": 0.30} for _ in range(20)
                ],
            },
        ],
    }


# Dos jornadas declaradas por la fuente (6 partidos a 0.20 y 4 a 0.40):
# ponderado = (6·0.20 + 4·0.40) / 10 = 0.28 ≠ media simple 0.30.
PARTIDOS_CON_JORNADA: list[dict] = (
    [{"jornada": 1, "brier": 0.20} for _ in range(6)]
    + [{"jornada": 2, "brier": 0.40} for _ in range(4)]
)
# Fuente que NO declara jornada (caso real del corpus FootyStats actual).
PARTIDOS_SIN_JORNADA: list[dict] = (
    [{"jornada": None, "brier": 0.21} for _ in range(3)] + [{"jornada": None, "brier": None}]
)


def _revienta() -> None:
    raise HistoricoDBError("bóveda histórica bloqueada por otro proceso")


@pytest.fixture
def visor(monkeypatch: pytest.MonkeyPatch):
    """Aísla la bóveda histórica con un corpus sintético de dos jornadas.

    `_cierres_propios` se neutraliza: el estado del Cierre de Jornada vive en la
    bóveda de producción y este Juez debe ser hermético (su propio Juez es
    `test_shield_jornada_closure.py`).
    """
    monkeypatch.setattr(
        sabiduria_view, "temporadas_historicas", lambda: [TEMPORADA_HISTORICA, TEMPORADA_VIGENTE]
    )
    monkeypatch.setattr(sabiduria_view, "total_partidos_historicos", lambda: 3870)
    monkeypatch.setattr(
        sabiduria_view, "_partidos_historicos", lambda temporada: list(PARTIDOS_CON_JORNADA)
    )
    monkeypatch.setattr(sabiduria_view, "_cierres_propios", lambda temporada: {})
    return sabiduria_view


@pytest.fixture
def snapshot(tmp_path: Path) -> Path:
    """Snapshot sintético: J7 con dos partidos PROGRAMADO y cuotas de dos casinos."""
    ruta = tmp_path / "snapshot.db"
    partidos = [
        {
            "id_partido": "P1",
            "local": "Local Uno",
            "visitante": "Visita Uno",
            "fecha_dt": "2026-11-08 19:00",
            "estado": "PROGRAMADO",
            "momios_operadores": {
                CASINO_A: {"L": CUOTAS_A[0], "E": CUOTAS_A[1], "V": CUOTAS_A[2]},
                CASINO_B: {"L": CUOTAS_B[0], "E": CUOTAS_B[1], "V": CUOTAS_B[2]},
            },
        },
        {
            "id_partido": "P2",
            "local": "Local Dos",
            "visitante": "Visita Dos",
            "fecha_dt": "2026-11-08 21:00",
            "estado": "PROGRAMADO",
            "momios_operadores": {
                CASINO_A: {"L": CUOTAS_B[0], "E": CUOTAS_B[1], "V": CUOTAS_B[2]},
            },
        },
        {"id_partido": "P3", "estado": "FINALIZADO"},
    ]
    conexion = sqlite3.connect(ruta)
    try:
        conexion.execute(
            "CREATE TABLE fixtures_snapshots ("
            "id INTEGER PRIMARY KEY, matchday INTEGER, updated_at TEXT, matches_json TEXT)"
        )
        conexion.execute(
            "CREATE TABLE sovereign_distributions ("
            "match_id TEXT PRIMARY KEY, p_local REAL, p_empate REAL, p_visitante REAL)"
        )
        conexion.execute(
            "INSERT INTO fixtures_snapshots (matchday, updated_at, matches_json) "
            "VALUES (7, '2026-11-03T18:00:00', ?)",
            (json.dumps(partidos),),
        )
        for indice, cuotas in ((1, CUOTAS_A), (2, CUOTAS_QBE)):
            simplex = _simplex(cuotas)
            conexion.execute(
                "INSERT INTO sovereign_distributions VALUES (?, ?, ?, ?)",
                (f"P{indice}", *simplex),
            )
        conexion.commit()
    finally:
        conexion.close()
    return ruta


# ── Leyes puras del Consenso `[LN-QBE-148]` ───────────────────────────────────
def test_consenso_es_el_promedio_ponderado_exacto_de_dos_casinos() -> None:
    pesos = {CASINO_A: 0.60, CASINO_B: 0.40}
    esperado = [
        0.60 * a + 0.40 * b for a, b in zip(_simplex(CUOTAS_A), _simplex(CUOTAS_B))
    ]
    consenso = _consenso_casinos(
        {CASINO_A: _simplex(CUOTAS_A), CASINO_B: _simplex(CUOTAS_B)}, pesos
    )
    assert consenso is not None
    assert consenso == pytest.approx(tuple(esperado), abs=1e-12)
    assert sum(consenso) == pytest.approx(1.0, abs=1e-12)


def test_qbe_inyectado_en_el_mismo_set_no_altera_el_consenso() -> None:
    pesos_casinos = {CASINO_A: 0.60, CASINO_B: 0.40}
    limpio = _consenso_casinos(
        {CASINO_A: _simplex(CUOTAS_A), CASINO_B: _simplex(CUOTAS_B)}, pesos_casinos
    )
    contaminado = _consenso_casinos(
        {
            CASINO_A: _simplex(CUOTAS_A),
            CASINO_B: _simplex(CUOTAS_B),
            "qbe": _simplex(CUOTAS_QBE),
            "Q-BE": _simplex(CUOTAS_QBE),
        },
        {**pesos_casinos, "qbe": 0.99, "Q-BE": 0.99},
    )
    assert limpio is not None
    assert contaminado == pytest.approx(limpio, abs=1e-12)


def test_sin_casinos_no_hay_consenso() -> None:
    assert _consenso_casinos({"qbe": _simplex(CUOTAS_QBE)}, {"qbe": 1.0}) is None
    assert _consenso_casinos({}, {}) is None


# ── D1: temporada histórica ⇒ mercado en vivo vacío con motivo ────────────────
def test_d1_temporada_historica_vacia_el_mercado_en_vivo(visor, tmp_path: Path) -> None:
    # Ruta inexistente: si el panel intentara leer el snapshot, fallaría. Debe
    # declarar el vacío ANTES de tocar disco.
    inexistente = tmp_path / "no-existe.db"
    mercado = construir_mercado_vivo(
        inexistente, fuentes=[*CASINOS, "qbe"], jornada="", temporada=TEMPORADA_HISTORICA
    )
    assert mercado["vacio"] is True
    assert mercado["partidos"] == []
    assert mercado["motivo"] == MOTIVO_TEMPORADA_HISTORICA
    assert mercado["motivo_historico"] is True
    assert mercado["jornada_viva"] is None


def test_d1_la_vista_historica_no_sirve_cartelera_viva(
    visor, snapshot: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(consenso_view, "cargar_vista_calibracion", _vista_falsa)
    monkeypatch.setattr("app.config.BACKTESTING_SNAPSHOT", snapshot)
    contexto = consenso_view.cargar_vista_consenso(
        fuentes=["novibet"], filtros=True, temporada=TEMPORADA_HISTORICA, jornada=""
    )
    assert contexto["error"] is None
    assert contexto["mercado"]["vacio"] is True
    assert contexto["mercado"]["motivo"] == MOTIVO_TEMPORADA_HISTORICA
    assert contexto["sabiduria"]["es_historica"] is True
    assert contexto["procedencia"].startswith("Fuente: Histórico FootyStats")


def _vista_falsa() -> dict:
    return {"reporte": _reporte(), "fuente": {"temporada": TEMPORADA_VIGENTE}, "error": None}


# ── D2: la bóveda caída NO se degrada en silencio ─────────────────────────────
def test_d2_la_boveda_caida_lanza_historico_db_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(calibration_view, "RUTA_HISTORICO", tmp_path / "ausente.db")
    with pytest.raises(HistoricoDBError):
        calibration_view.temporadas_historicas()
    with pytest.raises(HistoricoDBError):
        calibration_view.total_partidos_historicos()


def test_d2_la_vista_declara_el_fallo_y_no_cambia_de_universo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sabiduria_view, "temporadas_historicas", _revienta)
    monkeypatch.setattr(consenso_view, "cargar_vista_calibracion", _vista_falsa)
    contexto = consenso_view.cargar_vista_consenso(
        fuentes=[*CASINOS, "qbe"], filtros=True, temporada=TEMPORADA_HISTORICA, jornada=""
    )
    assert contexto["error"] is not None
    assert "bóveda histórica bloqueada" in contexto["error"]
    assert contexto["sabiduria"]["resumen"]["brier_consenso"] is None
    assert contexto["mercado"]["vacio"] is True


# ── D3: la temporada vigente usa el reporte; la desconocida no hereda nada ────
def test_d3_temporada_vigente_usa_el_reporte_y_jamas_la_boveda(
    visor, monkeypatch: pytest.MonkeyPatch
) -> None:
    def prohibido(temporada: str):
        raise AssertionError("la bóveda histórica no debe consultarse para la temporada vigente")

    monkeypatch.setattr(sabiduria_view, "_partidos_historicos", prohibido)
    sabiduria = visor.construir_sabiduria_masas(
        _reporte(), Path("."), temporada=TEMPORADA_VIGENTE, fuentes=[*CASINOS, "qbe"]
    )
    assert sabiduria["es_historica"] is False
    assert sabiduria["resumen"]["brier_consenso"] == pytest.approx(0.30)
    assert sabiduria["fuente_etiqueta"].startswith("Snapshot Vivo")


def test_d3_temporada_desconocida_no_hereda_el_snapshot_vivo(
    visor, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sabiduria_view, "_partidos_historicos", lambda temporada: [])
    sabiduria = visor.construir_sabiduria_masas(
        _reporte(), Path("."), temporada="1999_2000", fuentes=[*CASINOS, "qbe"]
    )
    assert sabiduria["es_historica"] is True
    assert sabiduria["resumen"]["brier_consenso"] is None
    assert sabiduria["jornadas"] == []
    assert sabiduria["total_partidos"] == 0


# ── D4: el KPI es la media ponderada de los bloques de la tabla ───────────────
def test_d4_kpi_es_la_media_ponderada_de_los_bloques_del_reporte(visor) -> None:
    sabiduria = visor.construir_sabiduria_masas(
        _reporte(), Path("."), temporada=TEMPORADA_VIGENTE, fuentes=[*CASINOS, "qbe"]
    )
    bloques = sabiduria["jornadas"]
    pares = [(bloque["brier_mercado"], bloque["n_mercado"]) for bloque in bloques]
    ponderada = sum(valor * n for valor, n in pares) / sum(n for _, n in pares)

    assert sabiduria["resumen"]["brier_consenso"] == pytest.approx(round(ponderada, 4))
    assert sabiduria["resumen"]["brier_consenso"] == pytest.approx(0.30)
    # La media aritmética de los Brier de jornada (0.25) queda PROHIBIDA.
    assert sabiduria["resumen"]["brier_consenso"] != pytest.approx(0.25)
    assert sabiduria["total_partidos"] == 30
    assert sabiduria["total_universo"] == 30


def test_d4_kpi_historico_es_la_media_ponderada_de_sus_bloques(visor) -> None:
    sabiduria = visor.construir_sabiduria_masas(
        _reporte(), Path("."), temporada=TEMPORADA_HISTORICA, fuentes=[CASINO_A]
    )
    pares = [
        (bloque["brier_mercado"], bloque["n_mercado"]) for bloque in sabiduria["jornadas"]
    ]
    ponderada = sum(valor * n for valor, n in pares) / sum(n for _, n in pares)
    assert sabiduria["resumen"]["brier_consenso"] == pytest.approx(round(ponderada, 4))
    assert sabiduria["resumen"]["brier_consenso"] == pytest.approx(0.28)
    assert sabiduria["resumen"]["brier_consenso"] != pytest.approx(0.30)
    assert sabiduria["total_partidos"] == 10


# ── D5: una sola fila de mercado y pesos que suman 1.0 ────────────────────────
def test_d5_sin_duplicado_consenso_footystats_y_pesos_unitarios(visor) -> None:
    sabiduria = visor.construir_sabiduria_masas(
        _reporte(), Path("."), temporada=TEMPORADA_HISTORICA, fuentes=[*CASINOS, "qbe"]
    )
    assert sabiduria["jornadas"], "la rama histórica debe servir bloques"
    for bloque in sabiduria["jornadas"]:
        etiquetas = [fila["fuente"] for fila in bloque["fuentes"]]
        assert etiquetas.count("FootyStats") == 1
        assert "Consenso" not in etiquetas
        assert sum(float(fila["peso"] or 0.0) for fila in bloque["fuentes"]) == pytest.approx(
            1.0
        )


def test_d5_el_reporte_emite_una_sola_fila_consenso(visor) -> None:
    sabiduria = visor.construir_sabiduria_masas(
        _reporte(), Path("."), temporada=TEMPORADA_VIGENTE, fuentes=[*CASINOS, "qbe"]
    )
    for bloque in sabiduria["jornadas"]:
        etiquetas = [fila["fuente"] for fila in bloque["fuentes"]]
        assert etiquetas.count("Consenso") == 1
        assert "FootyStats" not in etiquetas


# ── D6: el casino sin evidencia NO se suplanta con la etiqueta FootyStats ─────
def test_d6_novibet_sin_evidencia_y_footystats_con_su_cifra(visor) -> None:
    sabiduria = visor.construir_sabiduria_masas(
        _reporte(), Path("."), temporada=TEMPORADA_HISTORICA, fuentes=["novibet"]
    )
    bloque = sabiduria["jornadas"][0]
    por_fuente = {fila["fuente"]: fila for fila in bloque["fuentes"]}

    assert set(por_fuente) == {"FootyStats", "Novibet"}
    assert por_fuente["Novibet"]["estado"] == "SIN EVIDENCIA"
    assert por_fuente["Novibet"]["brier"] is None
    assert por_fuente["Novibet"]["peso"] is None
    assert por_fuente["FootyStats"]["brier"] == pytest.approx(0.20)
    # La cifra de mercado NUNCA se publica bajo la identidad del casino.
    assert por_fuente["Novibet"]["brier"] != por_fuente["FootyStats"]["brier"]
    # Los otros casinos no seleccionados no aparecen.
    assert "Caliente" not in por_fuente and "Betway" not in por_fuente


def test_d6_cada_casino_seleccionado_conserva_su_nombre(visor) -> None:
    sabiduria = visor.construir_sabiduria_masas(
        _reporte(), Path("."), temporada=TEMPORADA_HISTORICA, fuentes=[*CASINOS, "betway"]
    )
    bloque = sabiduria["jornadas"][0]
    etiquetas = {fila["fuente"] for fila in bloque["fuentes"]}
    assert {"Caliente", "Novibet", "Betway"} <= etiquetas
    for fila in bloque["fuentes"]:
        if fila["fuente"] in {"Caliente", "Novibet", "Betway"}:
            assert fila["estado"] == "SIN EVIDENCIA"


# ── D7: el peso del panel vivo es 1 / casinos seleccionados ───────────────────
def test_d7_peso_uniforme_y_consenso_promediado(snapshot: Path, visor) -> None:
    mercado = construir_mercado_vivo(
        snapshot, fuentes=[CASINO_A, CASINO_B], jornada="", temporada=""
    )
    assert mercado["vacio"] is False
    partido = mercado["partidos"][0]
    pesos = {
        fila["fuente"]: fila["peso"]
        for fila in partido["fuentes"]
        if fila["fuente"] in {"Caliente", "Novibet", "Betway"}
    }
    assert pesos["Caliente"] == pytest.approx(0.500)
    assert pesos["Novibet"] == pytest.approx(0.500)
    assert sum(pesos.values()) == pytest.approx(1.0)
    consenso = next(fila for fila in partido["fuentes"] if fila["fuente"] == "Consenso")
    esperado = [
        (a + b) / 2.0 for a, b in zip(_simplex(CUOTAS_A), _simplex(CUOTAS_B))
    ]
    assert consenso["p"] == pytest.approx(tuple(esperado), abs=1e-12)


def test_d7_un_solo_casino_pesa_uno_y_es_el_consenso(snapshot: Path, visor) -> None:
    mercado = construir_mercado_vivo(snapshot, fuentes=[CASINO_A], jornada="", temporada="")
    partido = mercado["partidos"][0]
    consenso = next(fila for fila in partido["fuentes"] if fila["fuente"] == "Consenso")
    caliente = next(fila for fila in partido["fuentes"] if fila["fuente"] == "Caliente")
    assert caliente["peso"] == pytest.approx(1.0)
    assert consenso["p"] == pytest.approx(caliente["p"], abs=1e-12)


# ── D8: sin jornada no se inventa el 0 sintético ──────────────────────────────
def test_d8_sin_jornada_declarada_no_se_inventa_jornada_cero(
    visor, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        sabiduria_view, "_partidos_historicos", lambda temporada: list(PARTIDOS_SIN_JORNADA)
    )
    sabiduria = visor.construir_sabiduria_masas(
        _reporte(), Path("."), temporada=TEMPORADA_HISTORICA, fuentes=[CASINO_A]
    )
    assert len(sabiduria["jornadas"]) == 1
    assert sabiduria["jornadas"][0]["jornada"] is None
    assert sabiduria["jornadas"][0]["etiqueta"].startswith("Temporada 2015_2016")
    assert sabiduria["jornadas_disponibles"] == []
    assert all(bloque["jornada"] != 0 for bloque in sabiduria["jornadas"])
    assert sabiduria["resumen"]["brier_consenso"] == pytest.approx(0.21)
    assert sabiduria["total_partidos"] == 3


def test_d8_agrupa_por_jornada_cuando_la_fuente_la_declara(visor) -> None:
    sabiduria = visor.construir_sabiduria_masas(
        _reporte(), Path("."), temporada=TEMPORADA_HISTORICA, fuentes=[CASINO_A]
    )
    assert [bloque["jornada"] for bloque in sabiduria["jornadas"]] == [1, 2]
    assert sabiduria["jornadas_disponibles"] == [1, 2]
    assert sabiduria["jornadas"][0]["n_partidos"] == 6
    assert sabiduria["jornadas"][1]["n_partidos"] == 4


def test_d8_el_filtro_de_jornada_recompone_el_kpi(visor) -> None:
    sabiduria = visor.construir_sabiduria_masas(
        _reporte(), Path("."), temporada=TEMPORADA_HISTORICA, fuentes=[CASINO_A], jornada="2"
    )
    assert [bloque["jornada"] for bloque in sabiduria["jornadas"]] == [2]
    assert sabiduria["resumen"]["brier_consenso"] == pytest.approx(0.40)
    assert sabiduria["total_partidos"] == 4
    assert sabiduria["jornadas_disponibles"] == [1, 2]


def test_d8_jornada_inexistente_declara_el_motivo(visor) -> None:
    sabiduria = visor.construir_sabiduria_masas(
        _reporte(), Path("."), temporada=TEMPORADA_HISTORICA, fuentes=[CASINO_A], jornada="9"
    )
    assert sabiduria["jornadas"] == []
    assert sabiduria["resumen"]["brier_consenso"] is None
    assert sabiduria["motivo_filtro"] is not None


def test_d8_agrupador_puro_respeta_la_jornada_real() -> None:
    bloques = _agrupar_por_jornada(PARTIDOS_CON_JORNADA)
    assert [bloque["jornada"] for bloque in bloques] == [1, 2]
    assert [bloque["n_partidos"] for bloque in bloques] == [6, 4]
    assert bloques[0]["brier"] == pytest.approx(0.20)


# ── D9: el panel vivo declara la jornada SERVIDA ──────────────────────────────
def test_d9_declara_la_jornada_servida_no_la_solicitada(snapshot: Path, visor) -> None:
    mercado = construir_mercado_vivo(snapshot, fuentes=[CASINO_A], jornada="", temporada="")
    assert mercado["jornada_viva"] == 7
    assert mercado["jornada"] == 7
    assert mercado["fuente_etiqueta"] == "Snapshot Vivo (J7)"


def test_d9_jornada_ajena_no_sirve_otra_cartelera(snapshot: Path, visor) -> None:
    mercado = construir_mercado_vivo(snapshot, fuentes=[CASINO_A], jornada="5", temporada="")
    assert mercado["vacio"] is True
    assert mercado["jornada_viva"] is None
    assert "J7" in mercado["motivo"]


# ── D10: código muerto y regla de suplantación erradicados ────────────────────
def test_d10_codigo_muerto_y_suplantacion_erradicados() -> None:
    eliminados = (
        "_filas",
        "_brier_por_casino",
        "_ticks_recientes",
        "_scores",
        "_pesos_validos",
        "_brier_consenso",
        "_etiqueta_proveedor",
        "ETIQUETA_PROVEEDOR",
        "ORIGENES_PROPIOS",
    )
    for nombre in eliminados:
        assert not hasattr(sabiduria_view, nombre), f"'{nombre}' sigue presente en el módulo"


def test_d10_la_rama_historica_solo_consulta_historical_matches(monkeypatch) -> None:
    """`odds_ticks` deja de alimentar la vista: la fuente es `historical_matches`."""
    consultas: list[str] = []

    def espia(self, query, params=()):
        consultas.append(str(query))
        return []

    monkeypatch.setattr(
        sabiduria_view.BaseDatosSoloLectura, "ejecutar_select", espia
    )
    sabiduria_view._partidos_historicos(TEMPORADA_HISTORICA)

    assert consultas, "la rama histórica debe ejecutar UNA consulta"
    assert all("historical_matches" in consulta for consulta in consultas)
    assert not any("odds_ticks" in consulta for consulta in consultas)
