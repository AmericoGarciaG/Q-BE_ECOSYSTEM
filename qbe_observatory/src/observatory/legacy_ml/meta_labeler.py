# -*- coding: utf-8 -*-
"""`[SPRINT-50][FASE 7]` Meta-Labeler: clasifica si la P' de V6 bate al mercado.

Régimen ``[DIRGEN-STRICT]``. Módulo puro de ``qbe_observatory`` (NO toca ``qbe_core``):
consume el meta-dataset del laboratorio y emite ``P(Y=1)`` = «V6 calibra mejor que FootyStats».

Motor: ``XGBClassifier`` (con ``scale_pos_weight`` para el desbalance de clases); si el paquete
no está en el entorno se degrada a ``HistGradientBoostingClassifier`` (respaldo declarado).

El umbral de veto se elige para MAXIMIZAR la precisión del veto fiduciario (fracción de partidos
vetados que efectivamente el mercado ganó).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np

VENDOR = Path(__file__).resolve().parents[4] / ".vendor"
if VENDOR.is_dir() and str(VENDOR) not in sys.path:
    sys.path.insert(0, str(VENDOR))

try:  # pragma: no cover - depende del entorno
    from xgboost import XGBClassifier as _BaseClassifier
    MOTOR = "xgboost.XGBClassifier"
except Exception:  # noqa: BLE001
    from sklearn.ensemble import HistGradientBoostingClassifier as _BaseClassifier
    MOTOR = "sklearn.HistGradientBoostingClassifier (respaldo)"


class MetaLabeler:
    """Modelo binario meta: P(QBE V6 gana al mercado | features de 29 variables residuales)."""

    def __init__(self, scale_pos_weight: Optional[float] = None, **kwargs: Any) -> None:
        self.scale_pos_weight = scale_pos_weight
        self.kwargs = kwargs
        self.model: Optional[Any] = None
        self._clases: Optional[np.ndarray] = None

    def _instanciar(self) -> Any:
        if MOTOR.startswith("xgboost"):
            return _BaseClassifier(
                objective="binary:logistic",
                n_estimators=300,
                max_depth=3,
                learning_rate=0.05,
                subsample=0.9,
                colsample_bytree=0.9,
                reg_lambda=1.0,
                scale_pos_weight=self.scale_pos_weight,
                tree_method="hist",
                random_state=50,
                n_jobs=4,
                **self.kwargs,
            )
        return _BaseClassifier(max_iter=300, max_depth=3, learning_rate=0.05, random_state=50)

    def fit(self, x: np.ndarray, y: np.ndarray) -> "MetaLabeler":
        self._clases = np.unique(y)
        self.model = self._instanciar()
        self.model.fit(np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.int64))
        return self

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        """Devuelve P(Y=1), vector columna (N, 1)."""
        if self.model is None:
            raise RuntimeError("MetaLabeler sin entrenar: llamar .fit() primero.")
        proba = self.model.predict_proba(np.asarray(x, dtype=np.float64))
        if proba.shape[1] == 1:
            return proba[:, 0]
        # xgboost devuelve [P(0), P(1)]
        return proba[:, 1]

    def pr_auc(self, x: np.ndarray, y: np.ndarray) -> float:
        from sklearn.metrics import average_precision_score

        return float(average_precision_score(np.asarray(y), self.predict_proba(x)))

    def umbral_veto_max_precision(
        self, x: np.ndarray, y: np.ndarray, minimo_vetos: int = 5
    ) -> Tuple[float, float, int]:
        """Barre el umbral de confianza P(Y=1) y devuelve (umbral, precisión del veto, nº vetos).

        Veto = «P(V6 gana) < umbral»; la precisión del veto es la fracción de vetados cuyo
        mercado efectivamente ganó (y == 0).
        """
        proba = self.predict_proba(x)
        y = np.asarray(y, dtype=np.int64)
        mejor: Tuple[float, float, int] = (0.0, -1.0, 0)
        for umbral in np.arange(0.05, 1.0, 0.05):
            vetados = proba < umbral
            n_vetos = int(vetados.sum())
            if n_vetos < minimo_vetos:
                continue
            aciertos = int((y[vetados] == 0).sum())
            precision = aciertos / n_vetos
            if precision > mejor[1]:
                mejor = (float(umbral), precision, n_vetos)
        return mejor

    def es_veto(self, features: np.ndarray, umbral: float) -> np.ndarray:
        """Máscara booleana: True = el meta-modelo veta (P(V6 gana) < umbral)."""
        return self.predict_proba(features) < umbral


def integrar_veto_meta(labeler: MetaLabeler, features: np.ndarray, umbral: float) -> np.ndarray:
    """[FASE 7 §T4] Integración Capa 4 (observatorio, sin tocar core).

    Consume el meta-modelo y emite la máscara de veto QBE-00: ``True`` donde la confianza en
    que V6 supere al mercado cae por debajo del umbral.
    """
    return labeler.es_veto(features, umbral)
