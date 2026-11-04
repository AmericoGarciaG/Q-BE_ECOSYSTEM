# -*- coding: utf-8 -*-
"""🏆 THE SHIELD — `[LN-QBE-148]` CONSENSO HISTÓRICO Q-BE × MERCADO.

Certifica el cruce histórico de la vista `/consenso` con la bóveda de
distribuciones soberanas (`historical_sovereign_distributions`, `[LN-QBE-150]`):

* el Brier de Q-BE histórico se calcula consumiendo la tabla de distribuciones P';
* la muestra de Alpha son los partidos donde **coexisten** momios FootyStats y P';
  un partido sin distribución queda fuera del promedio (no se imputa como cero);
* `Alpha = (1 − Brier_QBE / Brier_Mercado) × 100` con aritmética exacta;
* sin P' el Alpha se declara ausente (`SIN EVIDENCIA`), nunca fabricado;
* el filtro «Todas» agrega el universo completo y oculta el desglose por jornada.

El Juez es determinista: inyecta una bóveda sintética en `tmp_path`, no toca la
bóveda real ni la red.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Sequence, Tuple

import pytest

RAIZ = Path(__file__).resolve().parents[2]
for _ruta in (RAIZ, RAIZ / "qbe_observatory"):
    if str(_ruta) not in sys.path:
        sys.path.insert(0, str(_ruta))

from app.services import sabiduria_view as sv  # noqa: E402


# ── Bóveda sintética ──────────────────────────────────────────────────────────────────────
DDL_BOVEDA = """
CREATE TABLE historical_matches (
    match_id    TEXT PRIMARY KEY,
    temporada   TEXT NOT NULL,
    fecha_utc   TEXT NOT NULL,
    home_goals  INTEGER,
    away_goals  INTEGER,
    odd_home    REAL,
    odd_draw    REAL,
    odd_away    REAL
);
"""

DDL_P = """
CREATE TABLE historical_sovereign_distributions (
    match_id    TEXT PRIMARY KEY,
    p_local     REAL NOT NULL,
    p_empate    REAL NOT NULL,
    p_visitante REAL NOT NULL
);
"""

#: Cuota 2.00 / 4.00 / 4.00 ⇒ símplex exacto (0.50, 0.25, 0.25).
#: Resultado 1-0 ⇒ Brier de mercado = (0.25 + 0.0625 + 0.0625) / 3 = 0.125.
#: P' (0.60, 0.20, 0.20) ⇒ Brier Q-BE = (0.16 + 0.04 + 0.04) / 3 = 0.08.
#: Alpha esperado = (1 − 0.08 / 0.125) × 100 = 36.00 %.
ODDS = (2.0, 4.0, 4.0)
P_SINTETICA = (0.60, 0.20, 0.20)
BRIER_MERCADO_ESPERADO = 0.125
BRIER_QBE_ESPERADO = 0.08
ALPHA_ESPERADO = 36.0


def _crear_boveda(
    ruta: Path,
    partidos: Sequence[Tuple[str, str, Optional[Tuple[float, float, float]]]],
    *,
    con_tabla_p: bool = True,
) -> Path:
    """`partidos`: (match_id, temporada, (p_local, p_empate, p_visitante) | None)."""
    conexion = sqlite3.connect(str(ruta))
    try:
        conexion.execute(DDL_BOVEDA)
        if con_tabla_p:
            conexion.execute(DDL_P)
        for indice, (match_id, temporada, p_qbe) in enumerate(partidos):
            conexion.execute(
                "INSERT INTO historical_matches VALUES (?,?,?,?,?,?,?,?)",
                (match_id, temporada, f"2024-01-{indice + 1:02d}T00:00:00Z", 1, 0, *ODDS),
            )
            if con_tabla_p and p_qbe is not None:
                conexion.execute(
                    "INSERT INTO historical_sovereign_distributions VALUES (?,?,?,?)",
                    (match_id, *p_qbe),
                )
        conexion.commit()
    finally:
        conexion.close()
    return ruta


@pytest.fixture()
def boveda(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Inyecta una bóveda sintética con 2 partidos comparables + 1 sin P'."""
    ruta = _crear_boveda(
        tmp_path / "qbe_historico.db",
        [
            ("c1", "2023_2024", P_SINTETICA),
            ("c2", "2023_2024", P_SINTETICA),
            ("s1", "2023_2024", None),
            ("x1", "2024_2025", P_SINTETICA),
        ],
    )
    monkeypatch.setattr(sv, "RUTA_HISTORICO", ruta)
    monkeypatch.setattr(sv, "temporadas_historicas", lambda: ["2023_2024", "2024_2025"])
    monkeypatch.setattr(sv, "total_partidos_historicos", lambda: 4)
    return ruta


def _vista(temporada: str) -> Dict[str, Any]:
    return sv.construir_sabiduria_masas({}, Path("snapshot.db"), temporada=temporada)


# ── Cruce histórico ─────────────────────────────────────────────────────────────────────
def test_brier_qbe_y_alpha_numericos_con_distribuciones(boveda: Path) -> None:
    """[DoD] Con P' inyectada, Q-BE y Alpha dejan de ser `SIN EVIDENCIA`."""
    vista = _vista("2023_2024")
    resumen = vista["resumen"]
    assert resumen["brier_qbe"] is not None
    assert resumen["alpha_pct"] is not None
    assert resumen["brier_qbe"] == pytest.approx(BRIER_QBE_ESPERADO, abs=1e-9)
    assert resumen["brier_consenso"] == pytest.approx(BRIER_MERCADO_ESPERADO, abs=1e-9)
    assert resumen["alpha_pct"] == pytest.approx(ALPHA_ESPERADO, abs=1e-9)


def test_alpha_es_la_formula_canonica(boveda: Path) -> None:
    """Alpha = (1 − Brier_QBE / Brier_Mercado) × 100."""
    resumen = _vista("2023_2024")["resumen"]
    esperado = (1.0 - resumen["brier_qbe"] / resumen["brier_consenso"]) * 100.0
    assert resumen["alpha_pct"] == pytest.approx(esperado, abs=1e-9)


def test_muestra_es_la_interseccion_y_excluye_sin_p(boveda: Path) -> None:
    """El partido sin distribución P' no entra en la muestra de comparación."""
    vista = _vista("2023_2024")
    assert vista["n_comparables"] == 2
    assert vista["resumen"]["n_partidos"] == 2
    assert vista["total_universo"] == 3


def test_fila_qbe_en_la_tabla_lleva_dato(boveda: Path) -> None:
    """La fila Q-BE del bloque publica Brier numérico y estado DATO."""
    bloques = _vista("2023_2024")["jornadas"]
    assert bloques, "El bloque histórico debe existir con evidencia"
    filas_qbe = [fila for fila in bloques[0]["fuentes"] if fila["fuente"] == "Q-BE"]
    assert filas_qbe, "La selección por defecto incluye Q-BE"
    fila = filas_qbe[0]
    assert fila["brier"] == pytest.approx(BRIER_QBE_ESPERADO, abs=1e-9)
    assert fila["estado"] == sv.ESTADO_DATO


# ── Fail-Loud: sin evidencia no se fabrica ───────────────────────────────────────────────
def test_sin_distribuciones_el_alpha_es_ausente(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Sin P' el Alpha se declara ausente, no se inventa un porcentaje."""
    ruta = _crear_boveda(
        tmp_path / "sin_p.db",
        [("c1", "2023_2024", None), ("c2", "2023_2024", None)],
    )
    monkeypatch.setattr(sv, "RUTA_HISTORICO", ruta)
    monkeypatch.setattr(sv, "temporadas_historicas", lambda: ["2023_2024", "2024_2025"])
    monkeypatch.setattr(sv, "total_partidos_historicos", lambda: 2)

    resumen = _vista("2023_2024")["resumen"]
    assert resumen["brier_consenso"] is not None
    assert resumen["brier_qbe"] is None
    assert resumen["alpha_pct"] is None
    assert _vista("2023_2024")["n_comparables"] == 0


def test_boveda_sin_tabla_p_no_falla(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Una bóveda previa a `[LN-QBE-150]` sigue sirviendo el Brier de mercado."""
    ruta = _crear_boveda(
        tmp_path / "legacy.db",
        [("c1", "2023_2024", None)],
        con_tabla_p=False,
    )
    monkeypatch.setattr(sv, "RUTA_HISTORICO", ruta)
    monkeypatch.setattr(sv, "temporadas_historicas", lambda: ["2023_2024", "2024_2025"])
    monkeypatch.setattr(sv, "total_partidos_historicos", lambda: 1)

    resumen = _vista("2023_2024")["resumen"]
    assert resumen["brier_consenso"] == pytest.approx(BRIER_MERCADO_ESPERADO, abs=1e-9)
    assert resumen["brier_qbe"] is None
    assert resumen["alpha_pct"] is None


# ── Filtro «Todas» ──────────────────────────────────────────────────────────────────────
def test_filtro_todas_agrega_todas_las_temporadas(boveda: Path) -> None:
    """El modo global consolida el universo histórico completo."""
    vista = _vista("Todas")
    assert vista["es_global"] is True
    assert vista["resumen"]["n_partidos"] == 3  # c1, c2, x1 (s1 no tiene P')
    assert vista["total_universo"] == 4
    assert vista["resumen"]["brier_qbe"] == pytest.approx(BRIER_QBE_ESPERADO, abs=1e-9)
    assert vista["resumen"]["alpha_pct"] == pytest.approx(ALPHA_ESPERADO, abs=1e-9)


def test_filtro_todas_declara_desglose_no_disponible(boveda: Path) -> None:
    """Sin número de jornada en el histórico masivo, el desglose se declara fuera."""
    vista = _vista("Todas")
    assert vista["desglose_no_disponible"] is True
    assert vista["aviso_desglose"] == sv.AVISO_DESGLOSE_GLOBAL
    assert "Seleccione una temporada específica" in str(vista["aviso_desglose"])
    assert vista["jornadas_disponibles"] == []


def test_temporada_especifica_conserva_su_desglose(boveda: Path) -> None:
    """El filtro por temporada NO activa el aviso global."""
    vista = _vista("2023_2024")
    assert vista["desglose_no_disponible"] is False
    assert vista["aviso_desglose"] is None
