# -*- coding: utf-8 -*-
"""`[SPRINT-50]` Tarea 3 — Re-entrenamiento A/B/C sobre la P' del motor V2 (GSL-3D v2).

Régimen ``[DIRGEN-STRICT]``. Sólo lectura sobre la bóveda; artefactos en ``.lab-sprint50/``.

Produce:
  * tabla de pesos de los tres modelos (23 variables del catálogo causal);
  * Brier en Test de cada modelo frente a la climatología, el mercado de-vig y la P' V2.

Uso::

    python scripts/investigacion/sprint50_ml.py [--reconstruir]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

DIR_SCRIPTS = Path(__file__).resolve().parent
RAIZ_PROYECTO = DIR_SCRIPTS.parents[1]
# [SANEAMIENTO-SPRINT-50] Modelos A/B/C archivados en legacy_ml (cementerio del ML).
DIR_LEGACY_ML = RAIZ_PROYECTO / "qbe_observatory" / "src" / "observatory" / "legacy_ml"
for _ruta in (DIR_SCRIPTS, RAIZ_PROYECTO, RAIZ_PROYECTO / "qbe_core", DIR_LEGACY_ML):
    if str(_ruta) not in sys.path:
        sys.path.insert(0, str(_ruta))

import preparar_dataset_ml as base  # noqa: E402
import modelo_a_bayesiano as modelo_a  # noqa: E402
import modelo_b_regresion as modelo_b  # noqa: E402
import modelo_c_xgboost as modelo_c  # noqa: E402

DIR_LAB = RAIZ_PROYECTO / ".lab-sprint50"
DATASET = DIR_LAB / "dataset_ml_v2.npz"


def _brier_matriz(probabilidades: np.ndarray, y: np.ndarray) -> tuple[float, int]:
    valido = y >= 0
    if not valido.any():
        return float("nan"), 0
    total = 0.0
    for p_local, p_empate, p_visitante, resultado in zip(
        probabilidades[valido, 0], probabilidades[valido, 1], probabilidades[valido, 2], y[valido]
    ):
        goles_local, goles_visita = (
            (1, 0) if int(resultado) == 0 else ((0, 0) if int(resultado) == 1 else (0, 1))
        )
        total += base.brier_canonico(p_local, p_empate, p_visitante, goles_local, goles_visita)
    return total / int(valido.sum()), int(valido.sum())


def _climatologia(y_train: np.ndarray, y_test: np.ndarray) -> tuple[float, int]:
    jugados = y_train[y_train >= 0]
    if jugados.size == 0:
        return float("nan"), 0
    frecuencias = np.array([(jugados == k).mean() for k in range(3)], dtype=np.float64)
    matriz = np.tile(frecuencias, (len(y_test), 1))
    return _brier_matriz(matriz, y_test)


def _fmt(valor: float) -> str:
    return "—" if valor is None or (isinstance(valor, float) and np.isnan(valor)) else f"{valor:.6f}"


def main(argv: List[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(prog="sprint50_ml")
    analizador.add_argument("--reconstruir", action="store_true", help="reconstruye el dataset V2")
    argumentos = analizador.parse_args(argv)

    DIR_LAB.mkdir(parents=True, exist_ok=True)
    if argumentos.reconstruir or not DATASET.is_file():
        meta = base.preparar_dataset(DATASET, base.TABLA_P_V2)
        print(f"Dataset V2 construido: {DATASET.name} · N_train={meta['n_train']} N_test={meta['n_test']}")
    artefactos = base.cargar_artefactos(DATASET)

    print("=" * 96)
    print("`[SPRINT-50]` TAREA 3 — ML A/B/C SOBRE P' V2 (GSL-3D v2) · [DIRGEN-STRICT]")
    print("=" * 96)
    print(f"Dataset: {DATASET.name} · fuente P': {artefactos['meta'].get('tabla_p')}")
    print(f"Train {len(artefactos['y_train'])} · Test {len(artefactos['y_test'])} · "
          f"variables {len(artefactos['variables'])}")

    actas: Dict[str, Dict[str, Any]] = {}
    for nombre, modulo in (("A", modelo_a), ("B", modelo_b), ("C", modelo_c)):
        acta = modulo.entrenar(artefactos)
        actas[nombre] = acta
        print(f"  modelo {nombre} ({acta['motor']}): Brier Test {acta['brier_test']:.6f}")

    y_test = artefactos["y_test"]
    brier_clima, n_clima = _climatologia(artefactos["y_train"], y_test)
    brier_p_base, n_base = _brier_matriz(np.asarray(artefactos["p_base_test"], dtype=float), y_test)
    brier_mercado, n_mercado = base.brier_mercado(artefactos, "test")

    print()
    print("TABLA DE PESOS (23 variables del catálogo causal)")
    print("-" * 96)
    variables = artefactos["variables"]
    print(f"{'Variable':<10}{'Modelo A':>12}{'Modelo B':>12}{'Modelo C':>12}")
    for indice, variable in enumerate(variables):
        print(
            f"{variable:<10}"
            f"{actas['A']['pesos'][indice]:>12.6f}"
            f"{actas['B']['pesos'][indice]:>12.6f}"
            f"{actas['C']['pesos'][indice]:>12.6f}"
        )

    print()
    print("BRIER EN TEST (misma vara: brier_multiclase de qbe_core)")
    print("-" * 96)
    filas = [
        ("Climatología", brier_clima, n_clima),
        ("P' V2 (motor)", brier_p_base, n_base),
        ("Mercado de-vig", brier_mercado, n_mercado),
        ("Modelo A", actas["A"]["brier_test"], len(y_test)),
        ("Modelo B", actas["B"]["brier_test"], len(y_test)),
        ("Modelo C", actas["C"]["brier_test"], len(y_test)),
    ]
    cabecera = (
        f"{'Fuente':<18}{'Brier Test':>12}{'N':>7}"
        f"{'vs climatologia':>17}{'vs P2':>12}"
    )
    print(cabecera)
    for nombre, brier, n in filas:
        delta_clima = "—" if brier_clima is None or np.isnan(brier_clima) else f"{brier - brier_clima:+.6f}"
        delta_base = "—" if np.isnan(brier_p_base) else f"{brier - brier_p_base:+.6f}"
        print(f"{nombre:<18}{_fmt(brier):>12}{n:>7}{delta_clima:>17}{delta_base:>12}")

    mejor = min(
        (("Climatología", brier_clima), ("P' V2", brier_p_base),
         ("A", actas["A"]["brier_test"]), ("B", actas["B"]["brier_test"]), ("C", actas["C"]["brier_test"])),
        key=lambda par: par[1],
    )
    print()
    print(f"Mejor fuente en Test: {mejor[0]} ({mejor[1]:.6f})")

    (DIR_LAB / "actas_ml_v2.json").write_text(
        json.dumps(actas, ensure_ascii=False, indent=2, default=float), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
