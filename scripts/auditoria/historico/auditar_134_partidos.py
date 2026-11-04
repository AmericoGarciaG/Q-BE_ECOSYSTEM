#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Auditoría forense de la muestra de control de 134 partidos.

Solo lectura: abre el reporte canónico de Auditoría (snapshot read-only) y
transcribe las probabilidades Q-BE/FootyStats y el Brier individual.
No escribe bases de datos ni modifica producción.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

RAIZ = Path(__file__).resolve().parents[3]
if str(RAIZ / "qbe_observatory") not in sys.path:
    sys.path.insert(0, str(RAIZ / "qbe_observatory"))

from app.services.calibration_view import cargar_vista_calibracion  # noqa: E402


def _one_hot(goles_local: int, goles_visitante: int) -> Tuple[float, float, float]:
    if goles_local > goles_visitante:
        return (1.0, 0.0, 0.0)
    if goles_local == goles_visitante:
        return (0.0, 1.0, 0.0)
    return (0.0, 0.0, 1.0)


def _brier_crudo(probabilidades: Iterable[Any], resultado: Tuple[float, float, float]) -> Optional[float]:
    try:
        p = [float(valor) for valor in probabilidades]
    except (TypeError, ValueError):
        return None
    if len(p) != 3:
        return None
    return sum((a - b) ** 2 for a, b in zip(p, resultado))


def _partidos(reporte: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    for jornada in reporte.get("jornadas") or []:
        for partido in jornada.get("partidos") or []:
            if isinstance(partido, dict):
                yield partido


def main() -> int:
    vista = cargar_vista_calibracion()
    reporte = vista.get("reporte") or {}
    resumen = reporte.get("resumen_temporada") or {}

    print("=" * 92)
    print("AUDITORÍA FORENSE — MUESTRA DE CONTROL 134 PARTIDOS")
    print("Fuente: reporte de calibración de Auditoría (snapshot read-only)")
    print("=" * 92)
    print(f"Total partidos : {resumen.get('total_partidos')}")
    print(f"Brier mercado  : {resumen.get('brier_score_mercado')}  (normalizado 3N)")
    print(f"Brier Q-BE     : {resumen.get('brier_score_qbe')}  (normalizado 3N)")
    print(f"Alpha          : {resumen.get('alpha_calibracion_pct')}%")
    print()

    encabezado = (
        f"{'Match_ID':<16} {'Local':<22} {'Visita':<22} "
        f"{'Resultado':<10} {'P Q-BE L':>9} {'P Footy L':>10} "
        f"{'Brier 3N':>9} {'Brier crudo':>11}"
    )
    print(encabezado)
    print("-" * len(encabezado))

    mostrados = 0
    for partido in _partidos(reporte):
        if mostrados >= 5:
            break
        p_local = partido.get("p_local")
        q_local = partido.get("q_local")
        brier_3n = partido.get("brier_mercado")
        if p_local is None or q_local is None or brier_3n is None:
            continue
        try:
            goles_local = int(partido.get("goles_local"))
            goles_visitante = int(partido.get("goles_visitante"))
        except (TypeError, ValueError):
            continue
        resultado = _one_hot(goles_local, goles_visitante)
        crudo = _brier_crudo(
            (partido.get("q_local"), partido.get("q_empate"), partido.get("q_visitante")),
            resultado,
        )
        print(
            f"{str(partido.get('id_partido')):<16} "
            f"{str(partido.get('local'))[:22]:<22} "
            f"{str(partido.get('visitante'))[:22]:<22} "
            f"{str(partido.get('resultado_real')):<10} "
            f"{float(p_local):9.4f} {float(q_local):10.4f} "
            f"{float(brier_3n):9.4f} "
            f"{(crudo if crudo is not None else float('nan')):11.6f}"
        )
        mostrados += 1

    if mostrados == 0:
        print("SIN EVIDENCIA: no hay partidos con P Q-BE, P FootyStats y Brier simultáneos.")
        return 1

    print()
    print("Lectura: el Brier individual del reporte = suma multiclase / 3.")
    print("Ejemplo: Brier individual 0.1287 = 0.385965 / 3 (según la fórmula 3N).")
    print("No es un Brier binario; es el Brier multiclase normalizado por 3 casillas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
