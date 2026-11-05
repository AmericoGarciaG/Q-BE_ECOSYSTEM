# -*- coding: utf-8 -*-
"""`[SPRINT-49]` Tarea 3 — Modelo B: regresión logística multiclase (El Clásico).

Régimen ``[DIRGEN-STRICT]``.

``y`` ∈ {0: Local, 1: Empate, 2: Visita} sobre las 23 variables causales (diferencial
local−visita, imputadas con la mediana del ``Train``). Se estandariza con media/desviación
del ``Train`` (cero fuga) y se ajusta ``LogisticRegression`` multinomial.

Traducción a multiplicadores
----------------------------
La magnitud legislada de cada variable es ``a_i = mean_k |coef_[k, i]|`` (promedio sobre los
tres desenlaces). Se proyecta monótonamente al intervalo ``[0.5, 2.0]``:

    w_i = 0.5 + 1.5 · (a_i − min a) / (max a − min a)

El signo no se usa como multiplicador (el canal `[LN-QBE-147]` modula magnitudes de evidencia,
no direcciones). Si todos los ``a_i`` coinciden, el vector queda neutro en ``1.0``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence

import numpy as np

DIR_SCRIPTS = Path(__file__).resolve().parent
if str(DIR_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(DIR_SCRIPTS))

import preparar_dataset_ml as base  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.pipeline import make_pipeline  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, OSError, ValueError):  # pragma: no cover
        pass

MODELO = "B"
MOTOR = "sklearn.linear_model.LogisticRegression(multinomial, lbfgs)"
PESO_MIN, PESO_MAX = 0.5, 2.0
C_REGULARIZACION = 1.0


class ModeloBError(RuntimeError):
    """`[SPRINT-49]` El modelo B no produce un vector válido."""


def proyectar(magnitudes: Sequence[float]) -> np.ndarray:
    """Proyección monótona de magnitudes positivas al intervalo ``[0.5, 2.0]``."""
    valores = np.asarray(magnitudes, dtype=np.float64)
    if not np.all(np.isfinite(valores)):
        raise ModeloBError("Magnitudes no finitas: el modelo no es calibrable.")
    minimo, maximo = float(valores.min()), float(valores.max())
    if maximo - minimo <= 0.0:
        return np.ones_like(valores)
    return PESO_MIN + (PESO_MAX - PESO_MIN) * (valores - minimo) / (maximo - minimo)


def entrenar(artefactos: Dict[str, Any]) -> Dict[str, Any]:
    x_train = np.asarray(artefactos["x_train"], dtype=np.float64)
    x_test = np.asarray(artefactos["x_test"], dtype=np.float64)
    y_train = np.asarray(artefactos["y_train"], dtype=np.int64)
    if (y_train < 0).any():
        raise ModeloBError("El Train contiene partidos sin marcador; no es calibrable.")

    modelo = make_pipeline(
        StandardScaler(),
        LogisticRegression(
            C=C_REGULARIZACION,
            max_iter=5000,
            solver="lbfgs",
            random_state=49,
        ),
    )
    modelo.fit(x_train, y_train)
    coeficientes = np.asarray(modelo[-1].coef_, dtype=np.float64)
    magnitudes = np.mean(np.abs(coeficientes), axis=0)
    pesos = proyectar(magnitudes)

    if not np.all((pesos >= PESO_MIN) & (pesos <= PESO_MAX)):
        raise ModeloBError("Vector fuera de la banda [0.5, 2.0].")

    acierto_train = float(modelo.score(x_train, y_train))
    mascara_test = np.asarray(artefactos["y_test"]) >= 0
    acierto_test = float(modelo.score(x_test[mascara_test], np.asarray(artefactos["y_test"])[mascara_test]))

    return {
        "modelo": MODELO,
        "motor": MOTOR,
        "variables": artefactos["variables"],
        "pesos": [float(valor) for valor in pesos],
        "brier_train": float(base.brier_de_vector(artefactos, "train", pesos)),
        "brier_test": float(base.brier_de_vector(artefactos, "test", pesos)),
        "diagnostico": {
            "C": C_REGULARIZACION,
            "clases": [int(valor) for valor in modelo[-1].classes_],
            "acierto_train": acierto_train,
            "acierto_test": acierto_test,
            "coeficientes": coeficientes.round(6).tolist(),
            "magnitudes": [float(valor) for valor in magnitudes],
        },
    }


def _reporte(acta: Dict[str, Any]) -> None:
    print("=" * 96)
    print("`[SPRINT-49]` TAREA 3 — MODELO B (REGRESIÓN LOGÍSTICA) · [DIRGEN-STRICT]")
    print("=" * 96)
    print(f"Motor: {acta['motor']}  ·  C={acta['diagnostico']['C']}")
    print(f"Acierto Train={acta['diagnostico']['acierto_train']:.4f}"
          f"  Test={acta['diagnostico']['acierto_test']:.4f}")
    print(f"Brier Test (puente V07/V13): {acta['brier_test']:.6f}")
    print("-" * 96)
    for variable, peso in zip(acta["variables"], acta["pesos"]):
        print(f"  {variable}  {peso:8.4f}")
    print("=" * 96)


def main() -> int:
    parser = argparse.ArgumentParser(description="Modelo B — regresión logística (SPRINT-49)")
    parser.add_argument("--salida", default=str(base.DIR_SALIDA / "pesos_modelo_b.json"))
    argumentos = parser.parse_args()

    artefactos = base.cargar_artefactos()
    acta = entrenar(artefactos)
    destino = Path(argumentos.salida)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(acta, ensure_ascii=False, indent=2), encoding="utf-8")
    _reporte(acta)
    print(f"Acta: {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
