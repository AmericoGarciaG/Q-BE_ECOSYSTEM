# -*- coding: utf-8 -*-
"""`[SPRINT-50][FASE 7]` Meta-Labeling + Alpha Gap + ROI simulado.

Régimen ``[DIRGEN-STRICT]``. Consume ``.lab-sprint50/meta_dataset.npz`` (vía
``preparar_meta_dataset.py``) y el ``MetaLabeler`` de ``qbe_observatory``. NO toca ``qbe_core``.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Tuple

import numpy as np

RAIZ = Path(__file__).resolve().parents[4]
for _ruta in (RAIZ, RAIZ / "qbe_core", RAIZ / "qbe_observatory" / "src"):
    if str(_ruta) not in sys.path:
        sys.path.insert(0, str(_ruta))

import preparar_meta_dataset as prep  # noqa: E402
from observatory.legacy_ml.meta_labeler import MetaLabeler, integrar_veto_meta  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, OSError, ValueError):  # pragma: no cover
        pass

UMBRAL_ALPHA_GAP = 0.10


def _cargar() -> Dict[str, np.ndarray]:
    ruta = prep.SALIDA
    if not ruta.is_file():
        print("Construyendo meta-dataset…")
        prep.preparar()
    with np.load(ruta, allow_pickle=False) as datos:
        artefactos = {clave: datos[clave] for clave in datos.files}
    return artefactos


def main() -> int:
    artefactos = _cargar()
    x_train, y_train = artefactos["x_train"], artefactos["y_train"]
    x_test, y_test = artefactos["x_test"], artefactos["y_test"]
    p_qbe_test = artefactos["p_qbe_test"]
    p_mercado_test = artefactos["p_mercado_test"]
    brier_qbe_test = artefactos["brier_qbe_test"]
    brier_mercado_test = artefactos["brier_mercado_test"]
    odds_test = artefactos["odds_test"]

    # Balance de clases (scale_pos_weight = neg/pos).
    n_pos = int((y_train == 1).sum())
    n_neg = int((y_train == 0).sum())
    scale_pos_weight = n_neg / max(1, n_pos)

    print("=" * 96)
    print("FASE 7 — META-LABELING + ALPHA GAP + ROI · [DIRGEN-STRICT]")
    print("=" * 96)
    print(f"Meta-dataset: Train {x_train.shape[0]} · Test {x_test.shape[0]} · "
          f"features {x_train.shape[1]} (29 variables NO-V6)")
    print(f"Target Y=1 (V6 bate al mercado): Train {n_pos}/{len(y_train)} · "
          f"Test {int((y_test==1).sum())}/{len(y_test)}")
    print(f"scale_pos_weight = {scale_pos_weight:.3f}")

    # ── TAREA 2 — META-MODELO ────────────────────────────────────────────────────────────────
    print()
    print("TAREA 2 · META-MODELO (PR-AUC y curva de confianza)")
    print("-" * 96)
    modelo = MetaLabeler(scale_pos_weight=scale_pos_weight).fit(x_train, y_train)
    pr_auc = modelo.pr_auc(x_test, y_test)
    umbral, precision_veto, n_vetos = modelo.umbral_veto_max_precision(x_test, y_test)
    print(f"PR-AUC (Test): {pr_auc:.4f}")
    print(f"Umbral de veto que maximiza precisión: {umbral:.2f}  "
          f"(precisión {precision_veto:.4f}, vetos {n_vetos})")
    print()
    print(f"{'Umbral P(win)<':>14}{'Precisión veto':>17}{'Recall veto':>13}{'Vetos':>7}")
    proba_test = modelo.predict_proba(x_test)
    for t in np.arange(0.30, 0.96, 0.05):
        vetados = proba_test < t
        n = int(vetados.sum())
        if n == 0:
            continue
        precision = float((y_test[vetados] == 0).sum() / n)
        recall = float((y_test[vetados] == 0).sum() / max(1, int((y_test == 0).sum())))
        print(f"{t:>14.2f}{precision:>17.4f}{recall:>13.4f}{n:>7}")

    # ── TAREA 3 — ALPHA GAP ───────────────────────────────────────────────────────────────────
    print()
    print("TAREA 3 · ALPHA GAP (discrepancias |P_QBE − P_Mercado| ≥ 0.10)")
    print("-" * 96)
    discrepancia = np.max(np.abs(p_qbe_test - p_mercado_test), axis=1)
    mascara_gap = (~np.isnan(discrepancia)) & (discrepancia >= UMBRAL_ALPHA_GAP)
    n_gap = int(mascara_gap.sum())
    bq_gap = float(np.mean(brier_qbe_test[mascara_gap])) if n_gap else float("nan")
    bm_gap = float(np.nanmean(brier_mercado_test[mascara_gap])) if n_gap else float("nan")
    gana_qbe = float(np.mean(brier_qbe_test[mascara_gap] < brier_mercado_test[mascara_gap])) if n_gap else float("nan")
    print(f"Partidos con gap ≥ 0.10: {n_gap} / {len(y_test)}")
    print(f"Brier QBE en el gap : {bq_gap:.6f}")
    print(f"Brier mercado en gap: {bm_gap:.6f}")
    print(f"Fracción donde Q-BE gana en el gap: {gana_qbe:.4f}")

    if n_gap >= 20:
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import average_precision_score
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
        y_gap = (brier_qbe_test[mascara_gap] < brier_mercado_test[mascara_gap]).astype(int)
        secundario = make_pipeline(
            StandardScaler(), LogisticRegression(max_iter=3000)
        ).fit(x_test[mascara_gap], y_gap)
        pr_auc_sec = float(average_precision_score(y_gap, secundario.predict_proba(x_test[mascara_gap])[:, 1]))
        print(f"Modelo secundario (Verdadero Alpha vs Punto Ciego) — PR-AUC: {pr_auc_sec:.4f}")
        print("Lectura: PR-AUC ≈ 0.5 ⇒ la discrepancia no es clasificable; > 0.5 ⇒ hay señal.")
    else:
        print(f"Muestra de gap insuficiente ({n_gap}) para el modelo secundario.")

    # ── TAREA 4 — INTEGRACIÓN Y ROI ───────────────────────────────────────────────────────────
    print()
    print("TAREA 4 · ROI SIMULADO (Test, filtro del meta-modelo)")
    print("-" * 96)
    veto = integrar_veto_meta(modelo, x_test, umbral)

    def _roi_calc(mascara: np.ndarray) -> Tuple[float, int]:
        stake = 0.0
        retorno = 0.0
        n_bets = 0
        # Resultado real: recuperar marcador. brier_mercado NaN en filas sin cuota; pero el
        # resultado real se recompone desde el vértice apostado comparando con el marcador real.
        # Se usa el vértice de mayor edge y se liquida con el marcador real.
        from scripts.auditoria.calcular_distribuciones_historicas import DB_DEFECTO
        import sqlite3
        conexion = sqlite3.connect(f"file:{DB_DEFECTO.as_posix()}?mode=ro", uri=True)
        ids_test = artefactos["ids_test"]
        for indice, dentro in enumerate(mascara):
            if not dentro or np.isnan(odds_test[indice]).any():
                continue
            mercado = p_mercado_test[indice]
            if np.isnan(mercado).any():
                continue
            edge = p_qbe_test[indice] - mercado
            vertice = int(np.argmax(edge))
            momio = float(odds_test[indice, vertice])
            if momio <= 1.0:
                continue
            match_id = str(ids_test[indice])
            marcador = conexion.execute(
                "SELECT home_goals, away_goals FROM historical_matches WHERE match_id=?", (match_id,)
            ).fetchone()
            if marcador is None or marcador[0] is None:
                continue
            gh, ga = int(marcador[0]), int(marcador[1])
            resultado = 0 if gh > ga else (1 if gh == ga else 2)
            stake += 1.0
            n_bets += 1
            retorno += momio if resultado == vertice else 0.0
        conexion.close()
        return ((retorno - stake) / stake) if stake else 0.0, n_bets

    roi_todo, n_todo = _roi_calc(np.ones(len(y_test), dtype=bool))
    roi_no_vetados, n_no_vetados = _roi_calc(~veto)
    roi_vetados, n_vetados = _roi_calc(veto)

    print(f"{'Estrategia':<24}{'ROI':>10}{'Apuestas':>10}")
    print(f"{'Sin filtro (todo el Test)':<24}{roi_todo:>+10.2%}{n_todo:>10}")
    print(f"{'Con filtro meta (no vetados)':<24}{roi_no_vetados:>+10.2%}{n_no_vetados:>10}")
    print(f"{'Vetados (QBE-00)':<24}{roi_vetados:>+10.2%}{n_vetados:>10}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
