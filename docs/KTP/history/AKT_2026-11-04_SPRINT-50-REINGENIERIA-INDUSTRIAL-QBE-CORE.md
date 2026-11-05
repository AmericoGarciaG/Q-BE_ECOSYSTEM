# AKT — REPORTE ACTIVO DE TRANSFERENCIA

**Sprint:** SPRINT-50-REINGENIERIA-INDUSTRIAL-QBE-CORE
**Fecha:** 2026-11-04
**Autoridad:** Américo García Guerrero (Director Humano)
**Arquitecto saliente:** Agente Arquitecto de Sistema
**Estado:** ABIERTO (Fase 9 aprobada, pendiente de materialización)

## 1. SPRINT ACTUAL
- **Nombre:** SPRINT-50-REINGENIERIA-INDUSTRIAL-QBE-CORE
- **Objetivo:** Rediseñar el núcleo matemático (`qbe_core`) para alinearlo con el Volumen I, abandonar el ML predictivo y reorientar la estrategia económica.
- **Alcance:** `qbe_core`, `qbe_observatory` (legacy_ml), `scripts/` y `docs/`.
- **Régimen:** `[DIRGEN-STRICT]`
- **Fecha de inicio / cierre:** 2026-11-01 / `EN CURSO`

## 2. HITOS CONCLUIDOS
| Hito | Evidencia | Estado |
|---|---|---|
| **Motor V6 (Súper-Señal)** | `qbe_core` aislado a V06 (xG), V07 (SoT), V12 (xGA). | COMPLETADO |
| **Sistema Inmune (Fase 6)** | `triage.py` vetando el 27.31% de partidos. | COMPLETADO |
| **ML Dormido (Fase 8)** | `meta_labeler.py` en `legacy_ml/` tras PR-AUC 0.4823. | COMPLETADO |
| **Fase 8 (Anti-Sesgo)** | Backtest de 3 Zonas. Resultado: ROI negativo. | COMPLETADO |
| **Índice de Prima Popular** | Detección paramétrica de equipos inflados (Monterrey, Cruz Azul). | COMPLETADO |

## 3. DECISIONES TOMADAS
| Decisión | Razón | Impacto | Anclaje |
|---|---|---|---|
| **Adoptar el Consenso Multicasa** | Apostar contra un solo casino es ruido. | Se implementará De-vig Shin y Best Execution en Fase 9. | Fase 9 (aprobada) |
| **Migrar a Coberturas Sintéticas** | Apostar directo al 1X2 es una sangría de comisiones. | El foco cambia a capturar \(P_{mid}\) con \(V=0\). | `[LN-QBE-115]` |
| **Explotar Mercados Derivados** | El 1X2 es hiper-eficiente; los derivados tienen menos liquidez. | Extraer Under 2.5 y BTTS de la matriz \(M_{xy}\). | Fase 9 (aprobada) |

## 4. DEUDAS ABIERTAS
| Deuda | Severidad | Impacto | Siguiente acción | Responsable |
|---|---|---|---|---|
| **Proveedor Histórico de Momios** | ALTA | FootyStats es la única fuente histórica. | Integrar OddsPortal o BetExplorer Pro. | Arquitecto / Director |
| **Integración de Kelly y Hard-Caps** | MEDIA | La Mesa de Apuestas no dimensiona el capital automáticamente. | Fase 10: Implementar Kelly Atenuado en `qbe_business`. | Constructor |
| **UI de Coberturas y Derivados** | MEDIA | La UI actual solo muestra el 1X2. | Rediseñar la vista de la Mesa de Apuestas. | Constructor |

## 5. ESTADO FÁCTICO GIT / SHIELD
- **Branch:** `feature/fase2-observatory`
- **HEAD:** `b01908e` — 2026-11-03
- **Working tree:** Limpio tras el commit de este turno.
- **Juez de gobernanza:** 114 passed / 0 failed.
- **Juez KTP:** 5/5 PASSED.
- **Suite unificada:** `pytest tests/shield` → 115 passed.
- **Bóveda fáctica:** `qbe_historico.db` — 3,870 partidos en 12 temporadas, 2,737 distribuciones P' (V1/V6).
- **Datos no verificados:** Los errores de setup en pytest son por ACL del sandbox, no por código.

## 6. BACKLOG INMEDIATO
| Prioridad | Tarea | Criterio de aceptación |
|---:|---|---|
| 1 | Ejecutar Fase 9: Implementar De-vig Shin, \(P_{mid}\) y Derivados. | Scripts creados y backtest corriendo sobre los 3,870 partidos. ROI > 0 en alguna estrategia. |

## 7. SIGUIENTE MOVIMIENTO
- **Acción única:** Implementar la Fase 9 (Consenso Multicasa, De-vig Shin, y cálculo de Mercados Derivados).
- **Comando / punto de entrada:** `python scripts/investigacion/fase9_backtest_estrategias.py` (a crear en el siguiente turno).
- **Resultado esperado:** Reporte de ROI para las 3 estrategias.
- **Riesgo principal:** Que el Consenso y los Derivados sigan siendo eficientes y el ROI siga negativo.
- **Criterio de aborto:** Si el ROI sigue siendo negativo, emitir Ficha de Varianza para redefinir la Fase 10.
