# -*- coding: utf-8 -*-
"""`[SPRINT-50][FASE 8]` Motor anti-sesgo: Índice de Prima Popular y Zonas de Convergencia.

Régimen ``[DIRGEN-STRICT]``. Sólo lectura sobre ``qbe_historico.db``. **Cero nombres de equipos
cableados**: el índice se deriva íntegramente de las diferencias ``q_MKT − P_QBE`` observadas.

* **Prima Popular** — para cada club, media histórica (expansiva, pre-kickoff) de
  ``q_MKT(gana) − P_QBE(gana)`` en sus partidos. Positivo alto ⇒ el mercado lo sobrevalora.
* **Zonas** (Test 2023_2024 → 2026_2027, vértice favorito del mercado):
  Z1 Consenso ``|P−q| < 0.03`` · Z2 Peligro ``P−q > 0.10`` · Z3 Fade ``q−P > 0.08``.
* **Triaje Z3** — cobertura sintética (QBE-H1 / QBE-R2) vía `[LN-QBE-060]` sobre la cuota inflada.

Uso::  python scripts/investigacion/fase8_sesgo_popular.py
"""

from __future__ import annotations

import sqlite3
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

RAIZ = Path(__file__).resolve().parents[2]
for _ruta in (RAIZ, RAIZ / "qbe_core"):
    if str(_ruta) not in sys.path:
        sys.path.insert(0, str(_ruta))

from scripts.auditoria.calcular_distribuciones_historicas import (  # noqa: E402
    DB_DEFECTO,
    TABLA_BOVEDA,
    TABLA_VECTOR,
    AcumuladorCausal,
    _filas,
    _vector_de,
)
from src.core.sovereign_pipeline import generar_distribucion_v6  # noqa: E402
from src.core.triage import evaluar_viabilidad_cuotas  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, OSError, ValueError):  # pragma: no cover
        pass

KAPPA_V6 = 0.35
SUPERSENAL = ("V06", "V07", "V12")
TEMPORADAS_TEST = {"2023_2024", "2024_2025", "2025_2026", "2026_2027"}

UMBRAL_Z1 = 0.03
UMBRAL_Z2 = 0.10
UMBRAL_Z3 = 0.08


def _devig(odd_h: Any, odd_d: Any, odd_a: Any) -> Optional[Tuple[float, float, float]]:
    if odd_h is None or odd_d is None or odd_a is None:
        return None
    cuotas = (float(odd_h), float(odd_d), float(odd_a))
    if min(cuotas) <= 1.0:
        return None
    inversas = [1.0 / c for c in cuotas]
    suma = sum(inversas)
    return tuple(i / suma for i in inversas)


def _construir(conexion: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Corpus cronológico con P_QBE(V6), q_MKT y metadatos de club (sin fuga temporal)."""
    filas = _filas(
        conexion,
        f"SELECT m.* FROM {TABLA_BOVEDA} m JOIN {TABLA_VECTOR} v ON v.match_id = m.match_id "
        f"ORDER BY m.fecha_utc, m.match_id",
    )
    acumulador = AcumuladorCausal()
    registros: List[Dict[str, Any]] = []
    for fila in filas:
        match_id = str(fila["match_id"])
        temporada = str(fila.get("temporada") or "")
        local = str(fila.get("home_team_slug") or "")
        visita = str(fila.get("away_team_slug") or "")
        vector = _vector_de(conexion, match_id)
        if vector is None or not str(vector.get("fuente_datos") or "").strip():
            acumulador.registrar(temporada, local, visita, vector, vector)
            continue
        matriz = acumulador.matriz_causal(temporada, local, visita)
        vec_local = matriz.get("vector_local") or {}
        vec_visita = matriz.get("vector_visita") or {}
        medias = matriz.get("medias_liga") or {}
        completo = (
            all(var in vec_local for var in SUPERSENAL)
            and all(var in vec_visita for var in SUPERSENAL)
            and all(var in medias for var in SUPERSENAL)
        )
        q_mkt = _devig(fila.get("odd_home"), fila.get("odd_draw"), fila.get("odd_away"))
        if completo and fila.get("home_goals") is not None and fila.get("away_goals") is not None and q_mkt:
            raw = {
                "home_team_stats": {
                    "pj": len(matriz.get("local") or []),
                    "xg": vec_local["V06"], "sot": vec_local["V07"], "xga": vec_local["V12"],
                },
                "away_team_stats": {
                    "pj": len(matriz.get("visita") or []),
                    "xg": vec_visita["V06"], "sot": vec_visita["V07"], "xga": vec_visita["V12"],
                },
                "medias_liga": {"xg": medias["V06"], "sot": medias["V07"], "xga": medias["V12"]},
            }
            out = generar_distribucion_v6(match_id, raw, kappa_net=KAPPA_V6)
            if out.es_operable:
                registros.append(
                    {
                        "match_id": match_id,
                        "temporada": temporada,
                        "local": local,
                        "visita": visita,
                        "p_qbe": (out.p_local, out.p_empate, out.p_visitante),
                        "q_mkt": q_mkt,
                        "odds": (
                            float(fila["odd_home"]), float(fila["odd_draw"]), float(fila["odd_away"]),
                        ),
                        "goles": (int(fila["home_goals"]), int(fila["away_goals"])),
                    }
                )
        acumulador.registrar(temporada, local, visita, vector, vector)
    return registros


def _resultado(goles: Tuple[int, int]) -> int:
    local, visita = goles
    return 0 if local > visita else (1 if local == visita else 2)


def _bets_roi(registros: Sequence[Dict[str, Any]], mascara: Sequence[bool]) -> Tuple[float, int]:
    """Apuesta 1 ud. al vértice de mayor EDGE (P_QBE − q_MKT) y liquida a momio real."""
    stake = 0.0
    retorno = 0.0
    n = 0
    for registro, dentro in zip(registros, mascara):
        if not dentro:
            continue
        p = registro["p_qbe"]
        q = registro["q_mkt"]
        edge = [p[i] - q[i] for i in range(3)]
        vertice = max(range(3), key=lambda i: edge[i])
        if edge[vertice] <= 0.0:
            continue
        momio = registro["odds"][vertice]
        if momio <= 1.0:
            continue
        stake += 1.0
        n += 1
        if _resultado(registro["goles"]) == vertice:
            retorno += momio
    return ((retorno - stake) / stake) if stake else 0.0, n


def _doble_oportunidad_roi(
    registros: Sequence[Dict[str, Any]], mascara: Sequence[bool]
) -> Tuple[float, int]:
    """Cobertura sintética: doble oportunidad que incluye al favorito (QBE-H1 / QBE-R2)."""
    stake = 0.0
    retorno = 0.0
    n = 0
    for registro, dentro in zip(registros, mascara):
        if not dentro:
            continue
        q = registro["q_mkt"]
        favorito = max(range(3), key=lambda i: q[i])
        if favorito == 1:  # el empate no es "equipo popular": sin cobertura de club
            continue
        cubiertos = (0, 1) if favorito == 0 else (1, 2)
        odds = registro["odds"]
        inversas = 1.0 / odds[cubiertos[0]] + 1.0 / odds[cubiertos[1]]
        if inversas <= 0.0:
            continue
        momio = 1.0 / inversas
        stake += 1.0
        n += 1
        if _resultado(registro["goles"]) in cubiertos:
            retorno += momio
    return ((retorno - stake) / stake) if stake else 0.0, n


def main() -> int:
    if not DB_DEFECTO.is_file():
        print(f"🔴 Bóveda inexistente: {DB_DEFECTO}", file=sys.stderr)
        return 1
    conexion = sqlite3.connect(f"file:{DB_DEFECTO.as_posix()}?mode=ro", uri=True)
    try:
        registros = _construir(conexion)
    finally:
        conexion.close()

    if not registros:
        print("🔴 Sin registros V6 con mercado.", file=sys.stderr)
        return 1

    # ── TAREA 2 — ÍNDICE DE PRIMA POPULAR (expansivo pre-kickoff + reporte full-sample) ──────
    residuales: Dict[str, List[float]] = defaultdict(list)
    for registro in registros:
        p, q = registro["p_qbe"], registro["q_mkt"]
        residuales[registro["local"]].append(q[0] - p[0])
        residuales[registro["visita"]].append(q[2] - p[2])
    indice_full = {club: sum(v) / len(v) for club, v in residuales.items() if v}

    print("=" * 96)
    print("FASE 8 — MOTOR ANTI-SESGO · ÍNDICE DE PRIMA POPULAR · ZONAS · [DIRGEN-STRICT]")
    print("=" * 96)
    print(f"Partidos con P_QBE(V6) + mercado: {len(registros)}")
    print()
    print("TAREA 2 · TOP 5 CLUBES MÁS POPULARES (media histórica q_MKT − P_QBE)")
    print("-" * 96)
    print(f"{'Pos':>4}{'Club':<26}{'Índice':>10}{'Partidos':>10}{'Lectura':>26}")
    for posicion, (club, valor) in enumerate(
        sorted(indice_full.items(), key=lambda par: -par[1])[:5], start=1
    ):
        lectura = "mercado lo sobrevalora" if valor > 0 else "mercado lo infravalora"
        print(f"{posicion:>4}{club:<26}{valor:>+10.4f}{len(residuales[club]):>10}{lectura:>26}")

    # ── TAREA 3 — ZONAS DE CONVERGENCIA (Test) ───────────────────────────────────────────────
    test = [r for r in registros if r["temporada"] in TEMPORADAS_TEST]
    m1: List[bool] = []
    m2: List[bool] = []
    m3: List[bool] = []
    for registro in test:
        q = registro["q_mkt"]
        p = registro["p_qbe"]
        favorito = max(range(3), key=lambda i: q[i])
        gap = p[favorito] - q[favorito]
        es1 = abs(gap) < UMBRAL_Z1
        es2 = gap > UMBRAL_Z2
        es3 = (-gap) > UMBRAL_Z3
        m1.append(es1)
        m2.append(es2)
        m3.append(es3)

    print()
    print(f"TAREA 3 · ZONAS DE CONVERGENCIA (Test, N={len(test)})")
    print("-" * 96)
    print(f"{'Zona':<26}{'Partidos':>10}{'Apuestas':>10}{'ROI':>12}")
    for etiqueta, mascara in (
        ("Z1 Consenso |P−q|<0.03", m1),
        ("Z2 Peligro  P−q>0.10", m2),
        ("Z3 Fade     q−P>0.08", m3),
    ):
        roi, n = _bets_roi(test, mascara)
        print(f"{etiqueta:<26}{sum(mascara):>10}{n:>10}{roi:>+12.2%}")

    # ── TAREA 4 — TRIAJE ZONA 3 (cobertura sintética QBE-H1 / QBE-R2) ────────────────────────
    print()
    print("TAREA 4 · TRIAJE ZONA 3 — COBERTURA SINTÉTICA [LN-QBE-060]")
    print("-" * 96)
    motivos: Dict[str, int] = defaultdict(int)
    habilitados = 0
    favorito_popular = 0
    for registro, dentro in zip(test, m3):
        if not dentro:
            continue
        odd_h, odd_d, odd_a = registro["odds"]
        viable, motivo = evaluar_viabilidad_cuotas(odd_h, odd_d, odd_a, True)
        motivos[motivo] += 1
        if viable and ("H1" in motivo or "R2" in motivo):
            habilitados += 1
        favorito = max(range(3), key=lambda i: registro["q_mkt"][i])
        club_favorito = registro["local"] if favorito == 0 else registro["visita"]
        if indice_full.get(club_favorito, 0.0) > 0.0:
            favorito_popular += 1
    total_z3 = sum(m3)
    print(f"Partidos en Zona 3: {total_z3}")
    print(f"Favorito inflado con índice positivo (club popular): {favorito_popular}")
    print(f"Coberturas habilitadas (QBE-H1 / QBE-R2): {habilitados}")
    print()
    print("Desglose por veredicto de triaje:")
    for motivo, cantidad in sorted(motivos.items(), key=lambda par: -par[1]):
        print(f"  {cantidad:>4}  {motivo}")
    roi_cob, n_cob = _doble_oportunidad_roi(test, m3)
    print()
    print(f"ROI de la cobertura (doble oportunidad sobre el favorito inflado): {roi_cob:+.2%}  (n={n_cob})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
