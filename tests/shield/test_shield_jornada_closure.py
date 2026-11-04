# -*- coding: utf-8 -*-
"""🏆 THE SHIELD — `[SPRINT-47]` CIERRE DE JORNADA (JORNADA CLOSURE).

Juez inmutable del expediente `SPRINT-47-UNIFICACION-FOTMOB-Y-LANZADOR`,
ampliación «Cierre de jornada y consolidación histórica».

Certifica:

  D11 · Detector: una jornada se cierra sólo cuando TODOS sus partidos concluyen
        (`FINISHED` ≡ `FINALIZADO`); una jornada con un partido vivo NO se cierra.
  D12 · Transferencia: la secuencia completa de `odds_ticks` de la jornada llega a
        `historical_odds_qbe_live` con `origen = Q_BE_CAPTURA_PROPIA`, `delta` y
        trazabilidad de jornada/temporada.
  D13 · No suplantación de FootyStats: `historical_matches` queda intacta (cero
        sobrescritura de momios).
  D14 · Ausencia declarada: sin ticks se sella `SIN EVIDENCIA_PROPIA` y no se
        escribe una sola fila de cuota.
  D15 · Idempotencia: re-ejecutar el cierre no duplica evidencia.
  D16 · Brier propio con la normalización 3N/3 canónica.
  D17 · El daemon (`centinela_deportivo`) invoca el cierre al final del ciclo.
  D18 · UI: la fila de mercado de una jornada cerrada con captura propia se rotula
        `Q-BE Live Capture`; sin evidencia propia, conserva su fuente nativa; el
        KPI sigue siendo la media ponderada de la tabla (D4 intacta).
"""

from __future__ import annotations

import inspect
import math
import sqlite3
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
for pilar in ("qbe_observatory", "qbe_storage"):
    if str(RAIZ / pilar) not in sys.path:
        sys.path.insert(0, str(RAIZ / pilar))

import pytest  # noqa: E402

from src.storage.jornada_closure import (  # noqa: E402
    ESTADO_CERRADA,
    ESTADO_SIN_EVIDENCIA_PROPIA,
    ORIGEN_CAPTURA_PROPIA,
    cerrar_jornada,
    cerrar_jornadas_pendientes,
    detectar_jornadas_cerradas,
)

CASINO = "caliente"
CUOTAS = (1.50, 4.00, 7.00)


# ── Bóvedas sintéticas ────────────────────────────────────────────────────────
def _crear_viva(ruta: Path, jornadas: dict[int, list[dict]]) -> Path:
    """`matches` + `odds_ticks` mínimos con el esquema real de la bóveda viva."""
    conexion = sqlite3.connect(ruta)
    try:
        conexion.execute(
            "CREATE TABLE matches (id TEXT PRIMARY KEY, matchday_num INTEGER, status TEXT, "
            "score_home INTEGER, score_away INTEGER, season_id TEXT)"
        )
        conexion.execute(
            "CREATE TABLE odds_ticks (tick_id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "match_id TEXT, casino_id TEXT, timestamp TEXT, odd_home REAL, odd_draw REAL, "
            "odd_away REAL, vig REAL, delta_odd REAL, origen TEXT, cargado_utc TEXT)"
        )
        for jornada, partidos in jornadas.items():
            for partido in partidos:
                conexion.execute(
                    "INSERT INTO matches VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        partido["id"],
                        jornada,
                        partido.get("status", "FINALIZADO"),
                        partido.get("goles_local"),
                        partido.get("goles_visitante"),
                        None,
                    ),
                )
                for indice, tick in enumerate(partido.get("ticks", [])):
                    conexion.execute(
                        "INSERT INTO odds_ticks (match_id, casino_id, timestamp, odd_home, "
                        "odd_draw, odd_away, vig, delta_odd, origen, cargado_utc) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            partido["id"],
                            tick.get("casino", CASINO),
                            tick["timestamp"],
                            tick["cuotas"][0],
                            tick["cuotas"][1],
                            tick["cuotas"][2],
                            0.0,
                            tick.get("delta", 0.0),
                            tick.get("origen", "CENTINELA_MULTICASA"),
                            "2026-11-03T00:00:00Z",
                        ),
                    )
        conexion.commit()
    finally:
        conexion.close()
    return ruta


def _crear_historica(ruta: Path, *, con_footystats: bool = True, con_log: bool = True) -> Path:
    conexion = sqlite3.connect(ruta)
    try:
        conexion.execute(
            "CREATE TABLE historical_matches (match_id TEXT PRIMARY KEY, temporada TEXT, "
            "home_goals INTEGER, away_goals INTEGER, odd_home REAL, odd_draw REAL, odd_away REAL)"
        )
        if con_footystats:
            conexion.execute(
                "INSERT INTO historical_matches VALUES ('fs_1', '2026_2027', 2, 1, 2.10, 3.40, 3.60)"
            )
        if con_log:
            conexion.execute(
                "CREATE TABLE jornada_closure_log (temporada TEXT, jornada INTEGER, estado TEXT, "
                "ticks INTEGER, partidos INTEGER, casinos INTEGER, brier_propio REAL, "
                "detalle TEXT, cerrada_utc TEXT, PRIMARY KEY (temporada, jornada))"
            )
        conexion.commit()
    finally:
        conexion.close()
    return ruta


def _jornada_1() -> dict[int, list[dict]]:
    return {
        1: [
            {
                "id": "M1",
                "goles_local": 1,
                "goles_visitante": 0,
                "ticks": [
                    {"timestamp": "2026-11-01T10:00:00Z", "cuotas": (1.60, 3.80, 6.00)},
                    {"timestamp": "2026-11-01T18:00:00Z", "cuotas": CUOTAS},
                ],
            },
            {
                "id": "M2",
                "goles_local": 0,
                "goles_visitante": 0,
                "ticks": [{"timestamp": "2026-11-01T12:00:00Z", "cuotas": (2.30, 3.10, 3.20)}],
            },
        ]
    }


# ── D11: detector ─────────────────────────────────────────────────────────────
def test_d11_detector_solo_cierra_jornadas_concluidas(tmp_path: Path) -> None:
    viva = _crear_viva(
        tmp_path / "viva.db",
        {
            1: [{"id": "A", "status": "FINALIZADO"}, {"id": "B", "status": "FINISHED"}],
            2: [{"id": "C", "status": "FINALIZADO"}, {"id": "D", "status": "PROGRAMADO"}],
            3: [{"id": "E", "status": "PROGRAMADO"}],
        },
    )
    conexion = sqlite3.connect(f"file:{viva.as_posix()}?mode=ro", uri=True)
    try:
        assert detectar_jornadas_cerradas(conexion) == [1]
    finally:
        conexion.close()


def test_d11_cierre_de_jornada_sin_partidos_concluidos_no_aplica(tmp_path: Path) -> None:
    viva = _crear_viva(
        tmp_path / "viva.db",
        {1: [{"id": "A", "status": "PROGRAMADO", "ticks": []}]},
    )
    historica = _crear_historica(tmp_path / "historica.db")
    assert cerrar_jornadas_pendientes(viva, historica) == []


# ── D12: transferencia de la secuencia ────────────────────────────────────────
def test_d12_transfiere_la_secuencia_completa_con_su_origen(tmp_path: Path) -> None:
    viva = _crear_viva(tmp_path / "viva.db", _jornada_1())
    historica = _crear_historica(tmp_path / "historica.db")

    resumen = cerrar_jornada(1, viva, historica, temporada="2026_2027")
    assert resumen["estado"] == ESTADO_CERRADA
    assert resumen["ticks"] == 3
    assert resumen["partidos"] == 2

    conexion = sqlite3.connect(historica)
    try:
        filas = conexion.execute(
            "SELECT match_id, casino, timestamp, odd_home, delta, jornada, temporada, origen "
            "FROM historical_odds_qbe_live ORDER BY match_id, timestamp"
        ).fetchall()
    finally:
        conexion.close()

    assert len(filas) == 3, "la secuencia completa (no sólo el último tick) debe transferirse"
    assert {fila[7] for fila in filas} == {ORIGEN_CAPTURA_PROPIA}
    assert {fila[5] for fila in filas} == {1}
    assert {fila[6] for fila in filas} == {"2026_2027"}
    # La secuencia de M1 conserva sus DOS ticks y su delta interno.
    m1 = [fila for fila in filas if fila[0] == "M1"]
    assert len(m1) == 2
    assert m1[0][4] == pytest.approx(0.0)
    assert m1[1][4] != pytest.approx(0.0)


# ── D13: FootyStats permanece intacto ─────────────────────────────────────────
def test_d13_no_sobrescribe_los_momios_de_footystats(tmp_path: Path) -> None:
    viva = _crear_viva(tmp_path / "viva.db", _jornada_1())
    historica = _crear_historica(tmp_path / "historica.db")

    conexion = sqlite3.connect(historica)
    try:
        antes = conexion.execute(
            "SELECT COUNT(*), SUM(odd_home) FROM historical_matches"
        ).fetchone()
    finally:
        conexion.close()

    cerrar_jornada(1, viva, historica, temporada="2026_2027")

    conexion = sqlite3.connect(historica)
    try:
        despues = conexion.execute(
            "SELECT COUNT(*), SUM(odd_home) FROM historical_matches"
        ).fetchone()
        propio = conexion.execute(
            "SELECT COUNT(*) FROM historical_odds_qbe_live"
        ).fetchone()[0]
        log = conexion.execute(
            "SELECT estado, ticks, brier_propio FROM jornada_closure_log WHERE jornada = 1"
        ).fetchone()
    finally:
        conexion.close()

    assert antes == despues, "historical_matches es inmutable para el cierre"
    assert propio == 3
    assert log[0] == ESTADO_CERRADA and log[1] == 3 and log[2] is not None


# ── D14: sin ticks ⇒ estado declarado, cero filas ─────────────────────────────
def test_d14_sin_ticks_sella_sin_evidencia_propia(tmp_path: Path) -> None:
    viva = _crear_viva(
        tmp_path / "viva.db",
        {5: [{"id": "X", "status": "FINALIZADO", "goles_local": 1, "goles_visitante": 1, "ticks": []}]},
    )
    historica = _crear_historica(tmp_path / "historica.db")

    resumen = cerrar_jornada(5, viva, historica, temporada="2026_2027")
    assert resumen["estado"] == ESTADO_SIN_EVIDENCIA_PROPIA
    assert resumen["ticks"] == 0
    assert resumen["brier_propio"] is None

    conexion = sqlite3.connect(historica)
    try:
        filas = conexion.execute("SELECT COUNT(*) FROM historical_odds_qbe_live").fetchone()[0]
        log = conexion.execute(
            "SELECT estado, ticks FROM jornada_closure_log WHERE jornada = 5"
        ).fetchone()
    finally:
        conexion.close()
    assert filas == 0, "sin ticks no se imputa una sola cuota"
    assert log == (ESTADO_SIN_EVIDENCIA_PROPIA, 0)


# ── D15: idempotencia ─────────────────────────────────────────────────────────
def test_d15_re_ejecutar_no_duplica_evidencia(tmp_path: Path) -> None:
    viva = _crear_viva(tmp_path / "viva.db", _jornada_1())
    historica = _crear_historica(tmp_path / "historica.db")

    cerrar_jornada(1, viva, historica, temporada="2026_2027")
    cerrar_jornada(1, viva, historica, temporada="2026_2027")

    conexion = sqlite3.connect(historica)
    try:
        filas = conexion.execute("SELECT COUNT(*) FROM historical_odds_qbe_live").fetchone()[0]
        logs = conexion.execute("SELECT COUNT(*) FROM jornada_closure_log").fetchone()[0]
    finally:
        conexion.close()
    assert filas == 3
    assert logs == 1


# ── D16: Brier propio 3N/3 ────────────────────────────────────────────────────
def test_d16_brier_propio_usa_la_normalizacion_3n(tmp_path: Path) -> None:
    viva = _crear_viva(
        tmp_path / "viva.db",
        {
            1: [
                {
                    "id": "U1",
                    "goles_local": 1,
                    "goles_visitante": 0,
                    "ticks": [{"timestamp": "2026-11-01T10:00:00Z", "cuotas": CUOTAS}],
                }
            ]
        },
    )
    historica = _crear_historica(tmp_path / "historica.db")
    resumen = cerrar_jornada(1, viva, historica, temporada="2026_2027")

    inversas = [1.0 / cuota for cuota in CUOTAS]
    total = sum(inversas)
    simplex = [inversa / total for inversa in inversas]
    esperado = round(((simplex[0] - 1.0) ** 2 + simplex[1] ** 2 + simplex[2] ** 2) / 3.0, 4)

    assert resumen["brier_propio"] == pytest.approx(esperado, abs=1e-9)
    assert 0.0 < resumen["brier_propio"] < 1.0


# ── D17: el daemon invoca el cierre al final del ciclo ────────────────────────
def test_d17_el_daemon_invoca_el_cierre_en_su_ciclo() -> None:
    from src.ingestion.daemons import centinela_deportivo

    fuente = inspect.getsource(centinela_deportivo.ejecutar_ingesta_soberana_ligamx)
    assert "detectar_y_cerrar_jornada()" in fuente
    assert callable(centinela_deportivo.detectar_y_cerrar_jornada)
    cierre = inspect.getsource(centinela_deportivo.detectar_y_cerrar_jornada)
    assert "cerrar_jornadas_pendientes" in cierre


# ── D18: UI — badge `Q-BE Live Capture` ───────────────────────────────────────
def _reporte_dos_jornadas() -> dict:
    """J1 con mercado 0.10 (10 partidos) y J2 con mercado 0.40 (20 partidos)."""
    return {
        "resumen_temporada": {"total_partidos": 30},
        "jornadas": [
            {
                "jornada": 1,
                "total_partidos": 10,
                "brier_score_mercado": 0.10,
                "brier_score_qbe": 0.10,
                "partidos": [{"brier_mercado": 0.10, "brier_qbe": 0.10}] * 10,
            },
            {
                "jornada": 2,
                "total_partidos": 20,
                "brier_score_mercado": 0.40,
                "brier_score_qbe": 0.30,
                "partidos": [{"brier_mercado": 0.40, "brier_qbe": 0.30}] * 20,
            },
        ],
    }


@pytest.fixture
def ui_visor(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Aísla la UI con una bóveda histórica sintética que porta el cierre."""
    import app.services.sabiduria_view as visor

    historica = _crear_historica(tmp_path / "historica_ui.db")
    conexion = sqlite3.connect(historica)
    try:
        conexion.execute(
            "INSERT INTO jornada_closure_log VALUES "
            "('2026_2027', 2, 'CERRADA', 9, 20, 1, 0.25, NULL, '2026-11-03T00:00:00Z')"
        )
        conexion.execute(
            "INSERT INTO jornada_closure_log VALUES "
            "('2026_2027', 3, 'SIN EVIDENCIA_PROPIA', 0, 0, 0, NULL, NULL, '2026-11-03T00:00:00Z')"
        )
        conexion.commit()
    finally:
        conexion.close()

    monkeypatch.setattr(visor, "RUTA_HISTORICO", historica)
    monkeypatch.setattr(visor, "temporadas_historicas", lambda: ["2015_2016", "2026_2027"])
    monkeypatch.setattr(visor, "total_partidos_historicos", lambda: 1)
    return visor


def test_d18_la_jornada_cerrada_se_rotula_qbe_live_capture(ui_visor) -> None:
    sabiduria = ui_visor.construir_sabiduria_masas(
        _reporte_dos_jornadas(), Path("."), temporada="2026_2027", fuentes=["caliente", "qbe"]
    )
    bloques = {bloque["jornada"]: bloque for bloque in sabiduria["jornadas"]}

    fila_j2 = bloques[2]["fuentes"][0]
    assert fila_j2["fuente"] == "Q-BE Live Capture"
    assert fila_j2["brier"] == pytest.approx(0.25)
    assert fila_j2["n_partidos"] == 20
    assert bloques[2]["fuente_mercado"] == "Q-BE Live Capture"

    # J1 no fue cerrada con captura propia: conserva su fuente nativa.
    assert bloques[1]["fuentes"][0]["fuente"] == "Consenso"
    assert bloques[1]["fuentes"][0]["brier"] == pytest.approx(0.10)

    # D4 intacta: el KPI sigue siendo la media ponderada de la tabla.
    # (10·0.10 + 20·0.25) / 30 = 0.20
    assert sabiduria["resumen"]["brier_consenso"] == pytest.approx(0.20)
    assert sabiduria["resumen"]["n_partidos"] == 30
    assert sabiduria["resumen"]["etiqueta_mercado"] == "Mercado"
    assert "Q-BE Live Capture: 20 partidos" in sabiduria["resumen"]["composicion_mercado"]
    assert "Consenso: 10 partidos" in sabiduria["resumen"]["composicion_mercado"]
    assert sabiduria["total_partidos"] == 30


def test_d18_sin_evidencia_propia_no_se_rotula(ui_visor) -> None:
    """`SIN EVIDENCIA_PROPIA` no produce badge: la jornada conserva su fuente."""
    reporte = _reporte_dos_jornadas()
    reporte["jornadas"].append(
        {
            "jornada": 3,
            "total_partidos": 9,
            "brier_score_mercado": 0.30,
            "brier_score_qbe": 0.20,
            "partidos": [{"brier_mercado": 0.30, "brier_qbe": 0.20}] * 9,
        }
    )
    sabiduria = ui_visor.construir_sabiduria_masas(
        reporte, Path("."), temporada="2026_2027", fuentes=["caliente"]
    )
    bloques = {bloque["jornada"]: bloque for bloque in sabiduria["jornadas"]}
    assert bloques[3]["fuentes"][0]["fuente"] == "Consenso"
    assert bloques[3]["fuentes"][0]["brier"] == pytest.approx(0.30)
    assert bloques[2]["fuentes"][0]["fuente"] == "Q-BE Live Capture"


def test_d18_sin_tabla_de_cierre_la_ui_no_falla(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import app.services.sabiduria_view as visor

    historica = _crear_historica(tmp_path / "sin_log.db", con_log=False)
    monkeypatch.setattr(visor, "RUTA_HISTORICO", historica)
    monkeypatch.setattr(visor, "temporadas_historicas", lambda: ["2026_2027"])
    monkeypatch.setattr(visor, "total_partidos_historicos", lambda: 1)

    sabiduria = visor.construir_sabiduria_masas(
        _reporte_dos_jornadas(), Path("."), temporada="2026_2027", fuentes=["caliente"]
    )
    assert sabiduria["resumen"]["brier_consenso"] == pytest.approx(0.30)
    assert sabiduria["resumen"]["etiqueta_mercado"] == "Consenso"
