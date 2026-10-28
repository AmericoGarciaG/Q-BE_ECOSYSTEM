#!/usr/bin/env python3
"""Q-BE temporal benchmark. Usage: python manus_qbe_model.py [csv_path]"""
from __future__ import annotations
import sys
import warnings
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import log_loss
from xgboost import XGBClassifier

CSV = sys.argv[1] if len(sys.argv) > 1 else "/home/ubuntu/upload/pasted_file_G6ijFG_Q-BE_Manus_Dataset.csv"
LABELS = ["L", "E", "V"]
QBE = ["p_local_qbe", "p_empate_qbe", "p_visita_qbe"]
MKT = ["p_local_mkt", "p_empate_mkt", "p_visita_mkt"]
LAM = ["lambda_home", "lambda_away"]

def brier(y, probs):
    yy = np.eye(3)[pd.Categorical(y, categories=LABELS).codes]
    return float(np.mean(np.sum((probs - yy) ** 2, axis=1)))

def engineer(df):
    """Use only pregame model outputs: all postgame/semantically ambiguous v* facts excluded."""
    x = df[QBE + MKT + LAM].astype(float).copy()
    # At least 10 derived features, all available from the prediction snapshot.
    x["qbe_mkt_home_gap"] = x.p_local_qbe - x.p_local_mkt
    x["qbe_mkt_draw_gap"] = x.p_empate_qbe - x.p_empate_mkt
    x["qbe_mkt_away_gap"] = x.p_visita_qbe - x.p_visita_mkt
    x["home_away_lambda_diff"] = x.lambda_home - x.lambda_away
    x["total_lambda"] = x.lambda_home + x.lambda_away
    x["lambda_ratio"] = x.lambda_home / (x.lambda_away + 1e-6)
    x["qbe_home_away_diff"] = x.p_local_qbe - x.p_visita_qbe
    x["mkt_home_away_diff"] = x.p_local_mkt - x.p_visita_mkt
    x["qbe_entropy"] = -(x[QBE].clip(1e-6, 1).apply(np.log) * x[QBE]).sum(axis=1)
    x["mkt_entropy"] = -(x[MKT].clip(1e-6, 1).apply(np.log) * x[MKT]).sum(axis=1)
    x["qbe_top_probability"] = x[QBE].max(axis=1)
    x["mkt_top_probability"] = x[MKT].max(axis=1)
    return x

def main():
    warnings.filterwarnings("ignore")
    df = pd.read_csv(CSV)
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df = df.dropna(subset=["fecha", "resultado_real"]).sort_values(["fecha", "match_id"]).reset_index(drop=True)
    if set(df.resultado_real) - set(LABELS):
        raise ValueError("resultado_real debe contener únicamente L/E/V")
    # Strict holdout: chronological final 3 jornadas (regardless of non-monotonic CSV order).
    test_mask = df.jornada >= 9
    train = df.loc[~test_mask].copy(); test = df.loc[test_mask].copy()
    if train.empty or test.empty:
        raise ValueError("Se requieren jornadas anteriores y jornadas 9–11 para evaluación")
    X, Xt = engineer(train), engineer(test)
    y = pd.Categorical(train.resultado_real, categories=LABELS).codes
    yt = test.resultado_real.to_numpy()
    if set(y) != {0, 1, 2}:
        raise ValueError("Entrenamiento temporal sin las tres clases")

    lr = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                       LogisticRegression(C=0.1, penalty="l2", max_iter=2000, solver="lbfgs"))
    lr.fit(X, y)
    plr = lr.predict_proba(Xt)

    tree = XGBClassifier(objective="multi:softprob", num_class=3, n_estimators=80,
                         max_depth=2, learning_rate=0.035, min_child_weight=5,
                         subsample=0.8, colsample_bytree=0.8, reg_lambda=5,
                         eval_metric="mlogloss", random_state=42, n_jobs=2)
    tree.fit(X, y)
    ptrees = tree.predict_proba(Xt)
    pq = test[QBE].to_numpy(float); pm = test[MKT].to_numpy(float)
    # Renormalize to protect against source rounding.
    pq = pq / pq.sum(axis=1, keepdims=True); pm = pm / pm.sum(axis=1, keepdims=True)
    scores = {"Mercado": brier(yt, pm), "Q-BE": brier(yt, pq),
              "Logística L2": brier(yt, plr), "XGBoost": brier(yt, ptrees)}

    # Fit temporal sigmoid calibration on LR, using expanding-window validation folds.
    # CalibratedClassifierCV requires each training fold to contain all classes; gracefully
    # report unavailable if the small sample cannot support such strictly temporal folds.
    calibrated = None
    rounds = train.jornada.to_numpy()
    unique_rounds = sorted(np.unique(rounds))
    cv = []
    for r in unique_rounds[3:]:
        tr_idx = np.flatnonzero(rounds < r); va_idx = np.flatnonzero(rounds == r)
        if len(va_idx) and len(set(y[tr_idx])) == 3:
            cv.append((tr_idx, va_idx))
    try:
        if len(cv) >= 2:
            try:
                cal = CalibratedClassifierCV(estimator=lr, method="sigmoid", cv=cv, ensemble=True)
            except TypeError:
                cal = CalibratedClassifierCV(base_estimator=lr, method="sigmoid", cv=cv, ensemble=True)
            cal.fit(X, y)
            calibrated = cal.predict_proba(Xt)
            # Align sklearn's encoded classes to fixed L,E,V order.
            calibrated = calibrated[:, [list(cal.classes_).index(i) for i in range(3)]]
            scores["Logística L2 calibrada"] = brier(yt, calibrated)
    except Exception as e:
        calibration_note = f"No estimable con CV temporal: {type(e).__name__}: {e}"
    else:
        calibration_note = "Calibración sigmoide temporal" if calibrated is not None else "No hubo suficientes folds temporales válidos"

    print("=" * 72)
    print("INFORME TÉCNICO Q-BE — VALIDACIÓN WALK-FORWARD")
    print(f"Archivo: {CSV} | n={len(df)} | train={len(train)} (J1–J8) | test={len(test)} (J9–J{int(test.jornada.max())})")
    print("Clases train:", train.resultado_real.value_counts().reindex(LABELS, fill_value=0).to_dict())
    print("Clases test:", test.resultado_real.value_counts().reindex(LABELS, fill_value=0).to_dict())
    print("Brier multicategórico (mean sum_k (p-y)^2; menor es mejor):")
    for name, val in scores.items(): print(f"  {name:25s} {val:.6f}")
    print("\nMejor modelo ML no calibrado:", min(["Logística L2", "XGBoost"], key=lambda k: scores[k]))
    print("Calibración:", calibration_note)
    print("\nTop 5 importancia predictiva (XGBoost gain, datos de entrenamiento):")
    imp = pd.Series(tree.feature_importances_, index=X.columns).sort_values(ascending=False)
    for name, val in imp.head(5).items(): print(f"  {name:28s} {val:.5f}")
    print("\nParámetros producción — Logística L2:")
    print(f"  C=0.1, penalty=l2, solver=lbfgs, max_iter=2000; clases={LABELS}")
    print("  intercept:", np.round(lr[-1].intercept_, 6).tolist())
    print("  coefficients (features × classes L,E,V; standardized inputs):")
    for name, vals in zip(X.columns, lr[-1].coef_.T): print(f"    {name:28s} {np.round(vals, 6).tolist()}")
    print("Parámetros XGBoost: objective=multi:softprob, n_estimators=80, max_depth=2, learning_rate=0.035, min_child_weight=5, subsample=0.8, colsample_bytree=0.8, reg_lambda=5, random_state=42")
    print("\nAdvertencias: v01–v32 se excluyeron porque el diccionario no permite verificar disponibilidad prepartido;" 
          " varias parecen estadísticas del propio partido. 27 casos de test no bastan para afirmar ventaja robusta.")
    print("Sin ajuste de hiperparámetros sobre test; no se mezclaron scores de test en entrenamiento.")

if __name__ == "__main__": main()
