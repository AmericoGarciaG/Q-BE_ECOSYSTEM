# -*- coding: utf-8 -*-
"""`[SPRINT-49]` Tarea 4 — Modelo C: gradient boosting (La Caja Negra).

Régimen ``[DIRGEN-STRICT]``.

``XGBClassifier`` multiclase sobre las 23 variables causales, con validación cronológica
interna (último 15 % del ``Train``) para detener el boosting y reajuste final sobre el
``Train`` completo. Determinista: ``random_state`` fijo y sin muestreo aleatorio de filas
fuera de ``subsample``/``colsample`` sembrados.

Traducción a multiplicadores
----------------------------
``a_i = feature_importances_[i]`` (ganancia normalizada del árbol) se proyecta monótonamente
a ``[0.5, 2.0]`` con la misma ley que el Modelo B:

    w_i = 0.5 + 1.5 · (a_i − min a) / (max a − min a)

Respaldo autorizado (D4): si ``xgboost`` no está disponible, se usa
``HistGradientBoostingClassifier`` con importancia por permutación.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np

DIR_SCRIPTS = Path(__file__).resolve().parent
RAIZ_PROYECTO = DIR_SCRIPTS.parents[1]
if str(DIR_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(DIR_SCRIPTS))
#: Instalación local autorizada (D4): rueda xgboost extraída fuera de `.venv`.
_VENDOR = RAIZ_PROYECTO / ".vendor"
if _VENDOR.is_dir() and str(_VENDOR) not in sys.path:
    sys.path.insert(0, str(_VENDOR))

import preparar_dataset_ml as base  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, OSError, ValueError):  # pragma: no cover
        pass

MODELO = "C"
PESO_MIN, PESO_MAX = 0.5, 2.0
SEMILLA = 49
FRACCION_VALIDACION = 0.15

try:  # pragma: no cover - depende del entorno
    from xgboost import XGBClassifier

    MOTOR = "xgboost.XGBClassifier"
    _HAY_XGBOOST = True
except Exception:  # noqa: BLE001
    from sklearn.ensemble import HistGradientBoostingClassifier

    MOTOR = "sklearn.HistGradientBoostingClassifier (respaldo autorizado D4)"
    _HAY_XGBOOST = False


class ModeloCError(RuntimeError):
    """`[SPRINT-49]` El modelo C no produce un vector válido."""


def proyectar(magnitudes: Sequence[float]) -> np.ndarray:
    valores = np.asarray(magnitudes, dtype=np.float64)
    if not np.all(np.isfinite(valores)):
        raise ModeloCError("Importancias no finitas: el modelo no es calibrable.")
    minimo, maximo = float(valores.min()), float(valores.max())
    if maximo - minimo <= 0.0:
        return np.ones_like(valores)
    return PESO_MIN + (PESO_MAX - PESO_MIN) * (valores - minimo) / (maximo - minimo)


def _particion_cronologica(filas: int) -> Tuple[np.ndarray, np.ndarray]:
    corte = int(round(filas * (1.0 - FRACCION_VALIDACION)))
    corte = max(1, min(filas - 1, corte))
    return np.arange(corte), np.arange(corte, filas)


def _importancias(x: np.ndarray, y: np.ndarray, indice_val: np.ndarray) -> np.ndarray:
    """Ajusta el boosting y devuelve la importancia normalizada de cada variable."""
    if _HAY_XGBOOST:
        modelo = XGBClassifier(
            objective="multi:softprob",
            num_class=3,
            n_estimators=600,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            reg_lambda=1.0,
            tree_method="hist",
            eval_metric="mlogloss",
            early_stopping_rounds=40,
            random_state=SEMILLA,
            n_jobs=4,
        )
        ajuste = np.arange(x.shape[0])
        entrenamiento = np.setdiff1d(ajuste, indice_val)
        modelo.fit(
            x[entrenamiento],
            y[entrenamiento],
            eval_set=[(x[indice_val], y[indice_val])],
            verbose=False,
        )
        mejores = int(getattr(modelo, "best_iteration", 0) or 0) + 1
        final = XGBClassifier(
            objective="multi:softprob",
            num_class=3,
            n_estimators=max(1, mejores),
            max_depth=4,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            reg_lambda=1.0,
            tree_method="hist",
            eval_metric="mlogloss",
            random_state=SEMILLA,
            n_jobs=4,
        )
        final.fit(x, y, verbose=False)
        return np.asarray(final.feature_importances_, dtype=np.float64)

    from sklearn.inspection import permutation_importance

    modelo = HistGradientBoostingClassifier(
        max_iter=400,
        max_depth=6,
        learning_rate=0.05,
        random_state=SEMILLA,
    )
    modelo.fit(x, y)
    importancias = permutation_importance(
        modelo, x[indice_val], y[indice_val], n_repeats=5, random_state=SEMILLA, scoring="neg_brier_score"
    )
    return np.clip(np.asarray(importancias.importances_mean, dtype=np.float64), 0.0, None)


def entrenar(artefactos: Dict[str, Any]) -> Dict[str, Any]:
    x_train = np.asarray(artefactos["x_train"], dtype=np.float64)
    y_train = np.asarray(artefactos["y_train"], dtype=np.int64)
    if (y_train < 0).any():
        raise ModeloCError("El Train contiene partidos sin marcador; no es calibrable.")

    _entrenamiento, indice_val = _particion_cronologica(x_train.shape[0])
    importancias = _importancias(x_train, y_train, indice_val)
    pesos = proyectar(importancias)
    if not np.all((pesos >= PESO_MIN) & (pesos <= PESO_MAX)):
        raise ModeloCError("Vector fuera de la banda [0.5, 2.0].")

    orden = np.argsort(-np.asarray(importancias))
    return {
        "modelo": MODELO,
        "motor": MOTOR,
        "variables": artefactos["variables"],
        "pesos": [float(valor) for valor in pesos],
        "brier_train": float(base.brier_de_vector(artefactos, "train", pesos)),
        "brier_test": float(base.brier_de_vector(artefactos, "test", pesos)),
        "diagnostico": {
            "importancias": [float(valor) for valor in importancias],
            "importancias_normalizadas": [float(valor) for valor in importancias / importancias.sum()]
            if importancias.sum() > 0
            else [0.0] * len(importancias),
            "top5": [artefactos["variables"][int(indice)] for indice in orden[:5]],
            "validacion_filas": int(indice_val.size),
        },
    }


def _reporte(acta: Dict[str, Any]) -> None:
    print("=" * 96)
    print("`[SPRINT-49]` TAREA 4 — MODELO C (GRADIENT BOOSTING) · [DIRGEN-STRICT]")
    print("=" * 96)
    print(f"Motor: {acta['motor']}")
    print(f"Top-5 por importancia: {', '.join(acta['diagnostico']['top5'])}")
    print(f"Brier Test (puente V07/V13): {acta['brier_test']:.6f}")
    print("-" * 96)
    for variable, peso in zip(acta["variables"], acta["pesos"]):
        print(f"  {variable}  {peso:8.4f}")
    print("=" * 96)


def main() -> int:
    parser = argparse.ArgumentParser(description="Modelo C — gradient boosting (SPRINT-49)")
    parser.add_argument("--salida", default=str(base.DIR_SALIDA / "pesos_modelo_c.json"))
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
