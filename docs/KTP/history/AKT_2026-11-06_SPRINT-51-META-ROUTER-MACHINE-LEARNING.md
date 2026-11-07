# AKT — REPORTE ACTIVO DE TRANSFERENCIA

**Sprint:** SPRINT-51-META-ROUTER-MACHINE-LEARNING
**Fecha:** 2026-11-06
**Autoridad:** Américo García Guerrero (Director Humano)
**Arquitecto saliente:** Agente Arquitecto de Sistema (Kybern Framework v13.5)
**Estado:** PENDIENTE DE CONSOLIDACIÓN

## 1. SPRINT ACTUAL

- **Nombre:** SPRINT-51-META-ROUTER-MACHINE-LEARNING
- **Objetivo:** Evaluar empíricamente el Meta-Router (Q-BE vs Shin) y la taxonomía de Vetos Fiduciarios mediante modelado ML y validación temporal Rolling-Origin.
- **Alcance:** `scripts/investigacion/`, `data/investigacion/`, `qbe_observatory/data/`.
- **Régimen:** `[DIRGEN-STRICT]` (Extracción point-in-time y evaluación fuera de muestra estricta).
- **Fecha de inicio / cierre:** 2026-11-06 / 2026-11-06.

## 2. HITOS CONCLUIDOS

| Hito | Evidencia | Estado |
|---|---|---|
| Extracción Dataset Maestro 2,667 filas | `data/investigacion/dataset_meta_router_2667.parquet` (2,667 × 53; cero NaN en columnas críticas) | COMPLETADO |
| Auditoría Veto Fiduciario (Meseta de Entropía) | Brier retenido `0.1882` (reducción estadísticamente significativa $p=0.0012$) | COMPLETADO |
| Refutación Meta-Router 1X2 | Brier Árbol `0.2005` vs Shin `0.1998` en Holdout `2025_2026` | COMPLETADO |

## 3. DECISIONES TOMADAS

| Decisión | Razón | Impacto | Anclaje |
|---|---|---|---|
| **Descarte del Meta-Router 1X2** | El ensamble de ML no superó al mercado Shin fuera de muestra. | Shin se consagra como ancla de mercado definitiva para 1X2. | `docs/LOGIC.md` §25 |
| **Aprobación de Veto por Entropía** | Vetar partidos con Alta Entropía y poco spread reduce el error a 0.1882. | Veto selectivo se adopta como herramienta de mitigación de varianza. | Reporte Manus V2 |
| **Pausa de ML en 1X2 Directo** | El 1X2 es hiper-eficiente. El valor residual es inoperable por el Vig. | Reorientación estratégica hacia Progol (Volumen III) y Derivados (Volumen II). | `Q_BE-MANUS-RESEARCH-EVALUATION-V2` |

## 4. DEUDAS ABIERTAS

| Deuda | Severidad | Impacto | Siguiente acción | Responsable |
|---|---|---|---|---|
| **D-51.01 (Falla Exportación 32V)** | ALTA | El pipeline Parquet omitió variables crudas V01-V32. Bloquea Arquetipos 1, 3, 7 y 8. | Corregir `exportar_dataset_manus.py` para aplanar JSON de causales. | Constructor |
| **D-51.02 (Simulador Financiero)** | MEDIA | ROI reportado (-8.38%) es Naive Flat Stake. Ignora Dutching V=0 de Q-BE. | Incorporar `portfolio_math.py` al script de evaluación de ROI. | Quant / Arquitecto |
| **D-50.02 (Resolución de Totales)** | ALTA | $\lambda$ sigue sin resolución rítmica ($R^2 < 1\%$). Bloquea `QBE-C2`. | Diseñar modelo de ritmo/tempo con $R^2 > 5\%$. | Arquitecto |
| **D-50.04 (Cuotas de Derivados)** | ALTA | Histórico carece de cuotas Over/Under y BTTS. | Ingestar datos históricos de Totales/BTTS. | Data Nexus |

> Regla: si una deuda ya se cerró, no aparece aquí. Se conserva en `history/` o en el commit, no en el delta.

## 5. ESTADO FÁCTICO GIT / SHIELD

- **Branch:** `feature/fase2-observatory`
- **HEAD:** `3be4030` — 2026-11-06 (commit del dataset Manus; `a1765b9` era el HEAD previo)
- **Working tree:** limpio salvo `docs/KTP/AKT.md`; dataset, diccionario, folds y scripts de investigación trackeados en `3be4030`.
- **Juez de gobernanza:** `3 passed / 0 failed`
- **Juez KTP:** `5/5 PASSED`
- **Suite unificada:** `pytest qbe_core/tests qbe_business/tests qbe_ingestion/tests qbe_observatory/tests qbe_storage/tests -q` → `EXIT CODE 0` (345/345 passed).
- **Pre-vuelo de cartelera:** no aplica (no se tocó base viva).
- **Bóveda fáctica:** qbe_historico.db (3,870 partidos totales, 2,667 con P' y q^mkt limpios sin nulos, 12 temporadas).
- **Datos no verificados:** ROI real de los vetos fiduciarios aplicando reglas de Dutching V=0 y Kelly (solo evaluado bajo Flat Stake); Brier `0.1882`, `p=0.0012`, `0.2005` vs `0.1998` declarados en el Reporte Manus V2, sin artefacto reproducible en el repositorio.

## 6. BACKLOG INMEDIATO

| Prioridad | Tarea | Criterio de aceptación |
|---:|---|---|
| 1 | Consolidación en disco de KDB.md y AKT.md | `docs/KTP/KDB.md` actualizado con hashes de S51 y deudas D-51.x. |
| 2 | Corrección D-51.01 (Dataset 32V) | El Parquet regenerado incluye las columnas V01 a V32. |
| 3 | Apertura Progol (Resolvedor ILP) | `scripts/investigacion/08_progol_solver.py` operando con OR-Tools. |

## 7. SIGUIENTE MOVIMIENTO

- **Acción única:** Ejecutar el protocolo de consolidación fáctica de la Base de Conocimiento (Pase de AKT a Histórico y Actualización KDB).
- **Comando / punto de entrada:** `docs/KTP/KDB_Act_Pmpt.md`
- **Resultado esperado:** Archivo de este AKT en `docs/KTP/history/`, actualización de `docs/KTP/KDB.md` a su versión vigente (`[ALGO-PROTECTED]`), y reinicio de la plantilla `AKT.md`.
- **Riesgo principal:** Pérdida de los hallazgos críticos del reporte de Manus si no se incorporan correctamente a KDB.md.
- **Criterio de aborto:** Si el Juez KTP (`test_shield_ktp_package_integrity.py`) falla tras la consolidación.
