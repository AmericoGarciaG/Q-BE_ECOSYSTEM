# AKT — REPORTE ACTIVO DE TRANSFERENCIA

**Sprint:** SPRINT-50-REINGENIERIA-INDUSTRIAL-QBE-CORE
**Fecha:** 2026-11-04
**Autoridad:** Américo García Guerrero (Director Humano)
**Arquitecto saliente:** Agente Constructor (consolidación KTP)
**Estado:** ABIERTO (Fase 9 aprobada, pendiente de materialización)

## 1. SPRINT ACTUAL

- **Nombre:** SPRINT-50-REINGENIERIA-INDUSTRIAL-QBE-CORE
- **Objetivo:** Rediseñar el núcleo matemático (`qbe_core`) para alinearlo con el Volumen I, abandonar el ML predictivo y reorientar la estrategia económica hacia el consenso multicasa y los mercados derivados.
- **Alcance:** `qbe_core`, `qbe_observatory` (`legacy_ml`), `scripts/investigacion/` y `docs/`.
- **Régimen:** `[DIRGEN-STRICT]`
- **Fecha de inicio / cierre:** 2026-11-01 / `EN CURSO`

## 2. HITOS CONCLUIDOS

| Hito | Evidencia | Estado |
|---|---|---|
| **Decreto D1–D5 ratificado** | `DIRGEN_VARIANCE_REQUEST.md` → `RATIFICADO Y CERRADO` (VAR-2026-SPRINT50-CORE) | COMPLETADO |
| **Fase 2A — Clausura de masa** | Invariante L-1: `λ_H+λ_A = 2.6500` con desvío `4.4e-16` en 5 vectores (`intensity_canonical_loglink.py`) | COMPLETADO |
| **Fase 2B — GSL-3D v2** | `orthogonal_factor_engine.py`; matriz causal y proyección ortogonal | COMPLETADO |
| **Motor V6 (Súper-Señal)** | `generar_distribucion_v6`: sólo `V06`/`V07`/`V12`; Test Brier `0.617547` (N=1,084) | COMPLETADO |
| **Barrido κ (Fase 6)** | κ\* = 0.35 (Brier Train `0.642249`, N=990); **no adoptado en producción** (`KAPPA_NET=0.25`) | COMPLETADO (experimento) |
| **Sistema Inmune (Fase 6)** | `triage.veto_inmunidad_fiduciaria`: 296/1,084 = **27.31 %** (206 sobreasedio + 90 ineficacia) | COMPLETADO |
| **Fase 8 — Anti-sesgo (3 zonas)** | ROI: Z1 −8.29 % (249) · Z2 −20.11 % (18) · Z3 −14.94 % (426); cobertura −5.86 % | COMPLETADO |
| **Índice de Prima Popular** | Top: Morelia +0.0851 (16) · Monterrey +0.0691 (237) · Cruz Azul +0.0550 (250) · Tigres +0.0538 (256) · América +0.0465 (263) | COMPLETADO |
| **Cementerio del ML (Fase 7–8)** | `legacy_ml/` con meta-labeler, A/B/C y ensamble; PR-AUC `0.4823` | COMPLETADO |

## 3. DECISIONES TOMADAS

| Decisión | Razón | Impacto | Anclaje |
|---|---|---|---|
| **Ratificar el Decreto D1–D5** | La materialización de Fases 2A/2B/4/6/8 ya estaba en el árbol; el parte seguía abierto | El código actual es el estándar oficial; Alto al Fuego levantado | `DIRGEN_VARIANCE_REQUEST.md` |
| **Erradicar el ML predictivo** | PR-AUC 0.4823 < 0.50 y colapso de pesos | ML dormido en `legacy_ml/`; prohibido reimportar | `legacy_ml/README.md` |
| **No adoptar κ\* = 0.35 en producción** | El barrido es Train-only; el sello sigue en 0.25 | Sin re-sellado; requiere Ficha de Varianza | `docs/CONSTANTS.md`, Invariante 9 |
| **Adoptar el Consenso Multicasa** | Apostar contra un solo casino es ruido de inventario | De-vig Shin + Best Execution en Fase 9 | `[LN-QBE-148]` |
| **Migrar a Coberturas Sintéticas** | El 1X2 directo es una sangría de comisiones | Foco en \(P_{mid}\) con \(V=0\) | `[LN-QBE-115]` |
| **Explotar Mercados Derivados** | El 1X2 es hiper-eficiente; los derivados tienen menos liquidez | Extraer Under 2.5 y BTTS de la matriz \(M_{xy}\) | Fase 9 |

## 4. DEUDAS ABIERTAS

| Deuda | Severidad | Impacto | Siguiente acción | Responsable |
|---|---|---|---|---|
| **Fase 9 no materializada** (De-vig Shin, consenso multicasa, \(P_{mid}\), derivados) | ALTA | Bloquea la estrategia económica; el 1X2 no ha dado Alpha | Implementar en `qbe_core` con Jueces y backtest | Constructor / Arquitecto |
| **Proveedor histórico de momios** | ALTA | FootyStats es la única fuente histórica y no tiene derivados | Integrar OddsPortal o BetExplorer Pro | Arquitecto / Director |
| **Kelly y hard-caps no automatizados** | MEDIA | La Mesa de Apuestas no dimensiona capital | Kelly atenuado en `qbe_business` | Constructor |
| **UI de coberturas y derivados** | MEDIA | La UI sólo muestra 1X2 | Rediseñar la Mesa de Apuestas | Constructor |
| **κ\* = 0.35 no re-sellado** | MEDIA | Divergencia entre experimento y motor (`0.25`) | Ficha de Varianza o declarar 0.25 definitivo | Director / Arquitecto |

## 5. ESTADO FÁCTICO GIT / SHIELD

- **Branch:** `feature/fase2-observatory`
- **HEAD:** `827e6ca` — 2026-11-04
- **Working tree:** limpio
- **Juez de gobernanza:** 114 passed / 0 failed (`pytest qbe_core/tests`)
- **Juez KTP:** 5/5 PASSED
- **Suite unificada:** `pytest qbe_core/tests qbe_business/tests qbe_ingestion/tests qbe_observatory/tests qbe_storage/tests -q --no-header` → **263 passed, EXIT CODE 0**
- **Escudo de mercado:** `pytest tests/shield` → 115 passed
- **Pre-vuelo de cartelera:** no aplica (sin cambios de ingesta)
- **Bóveda fáctica:** `qbe_historico.db` — 3,870 partidos en 12 temporadas, **3,726** con cuotas 1X2 completas, 2,737 distribuciones P' V1 (2,727 V2 · 2,727 V3)
- **Datos no verificados:** ninguno

## 6. BACKLOG INMEDIATO

| Prioridad | Tarea | Criterio de aceptación |
|---:|---|---|
| 1 | Ejecutar Fase 9: De-vig Shin, consenso multicasa y derivados (Under 2.5 / BTTS). | Script de backtest sobre los 3,726 partidos con cuotas; ROI > 0 en alguna estrategia o Ficha de Varianza |

## 7. SIGUIENTE MOVIMIENTO

- **Acción única:** materializar la Fase 9 — De-vig Shin en `consensus.py`, derivados en `distribution_dixon_coles.py` y el backtest de las tres estrategias.
- **Comando / punto de entrada:** `python scripts/investigacion/fase9_backtest_estrategias.py` (a crear en el siguiente turno).
- **Resultado esperado:** reporte de ROI por estrategia sobre 3,726 partidos; confirmación de si los derivados rompen la barrera del ROI > 0.
- **Riesgo principal:** que el consenso y los derivados sigan siendo eficientes y el ROI permanezca negativo (Alpha agotado).
- **Criterio de aborto:** si las tres estrategias siguen con ROI negativo y el Brier no mejora, emitir Ficha de Varianza para redefinir la Fase 10 o pausar la búsqueda de Alpha.
