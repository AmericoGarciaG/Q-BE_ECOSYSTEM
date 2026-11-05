# `legacy_ml/` — CEMENTERIO DEL ML PREDICTIVO (Fases 7–8, DORMIDO)

> **Todos los modelos de ML predictivo, el meta-etiquetado y el ensamble de consenso están
> DORMIDOS porque no superaron el PR-AUC del 50 %. El estándar actual es la Física Pura (V6)
> + Análisis de Sesgo de Mercado.**

Régimen: `[DIRGEN-STRICT]` · Expediente `SPRINT-50-REINGENIERIA-INDUSTRIAL-QBE-CORE`.

## Dictamen

| Evidencia | Valor | Veredicto |
|---|---:|---|
| Meta-Labeler (XGBoost) — PR-AUC Test | **0.4823** | Por debajo de 0.50 ⇒ sin habilidad |
| Meta-Labeler — precisión máxima del veto | 0.6207 | ≈ tasa base del mercado |
| Alpha Gap — fracción donde Q-BE gana en discrepancias ≥ 0.10 | **0.3681** | Q-BE pierde el *alpha gap* |
| Fase 4 — Brier V2/V3 vs V1 | +3.79 % / +4.28 % | Peor que V1 |
| Fase 5.1 — elasticidad macro/micro | mejora INVIABLE | Sobreajuste de frontera |

El ML predictivo no aporta señal sobre el marcador: sus mejoras aparentes son varianza de muestra
pequeña o artefactos de frontera. Por dictamen del Auditor, la capa se **duerme** (no se borra:
se conserva como evidencia y se puede reactivar con Ficha de Varianza).

## Contenido archivado

| Archivo | Origen | Estado |
|---|---|---|
| `meta_labeler.py` | `qbe_observatory/src/observatory/ml/meta_labeler.py` | DORMIDO |
| `fase7_meta_labeling.py` | `scripts/investigacion/fase7_meta_labeling.py` | DORMIDO |
| `preparar_meta_dataset.py` | `scripts/investigacion/preparar_meta_dataset.py` | DORMIDO |
| `modelo_a_bayesiano.py` | `scripts/investigacion/modelo_a_bayesiano.py` | DORMIDO |
| `modelo_b_regresion.py` | `scripts/investigacion/modelo_b_regresion.py` | DORMIDO |
| `modelo_c_xgboost.py` | `scripts/investigacion/modelo_c_xgboost.py` | DORMIDO |
| `consenso_ensamble.py` | `scripts/investigacion/consenso_ensamble.py` | DORMIDO |

**Causa única de archivo:** fracaso en el PR-AUC. Ninguno de los modelos A/B/C, del meta-labeler
ni del ensamble de consenso superó el umbral 0.50 en Test (meta-labeler: 0.4823). El cementerio
conserva la evidencia; no es una biblioteca reutilizable.

Artefacto asociado (fuera del paquete): `.lab-sprint50/meta_dataset.npz`.

## Estándar vigente

1. **Física Pura — motor V6**: `generar_distribucion_v6` (`qbe_core/src/core/sovereign_pipeline.py`),
   súper-señal V06/V07/V12 con ligadura α fija y κ = 0.35.
2. **Análisis de Sesgo de Mercado**: `scripts/investigacion/fase8_sesgo_popular.py`
   (Índice de Prima Popular + Zonas de Convergencia + Triaje de cobertura).

## Prohibiciones

- **NO** reimportar estos módulos desde `qbe_core`, `qbe_business` ni desde el pipeline V6.
- **NO** reactivar el meta-labeler sin un PR-AUC de Test > 0.50 certificado por un Juez.
- **NO** cablear nombres de equipos: todo índice de sesgo es paramétrico.
