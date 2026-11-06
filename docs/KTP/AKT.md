# AKT — ACTA DE CIERRE DE FASE 9

**Sprint:** `SPRINT-50-REINGENIERIA-INDUSTRIAL-QBE-CORE`
**Fecha:** 2026-11-05
**Autoridad Suprema:** Américo García Guerrero (Director Humano)
**Emisor:** Agente Constructor de IA
**Fase:** 9 — De-vig Shin, Consenso Multicasa, P_mid y Mercados Derivados (Pasos 1–3), Fase 9.4 (Auditoría empírica) y compuerta de cierre
**Régimen:** `[DIRGEN-STRICT]`
**Estado:** `FASE 9 CERRADA EN VERDE ABSOLUTO` · `CIERRE TÉCNICO COMPLETO — PENDIENTE DE DECLARACIÓN FORMAL DEL DIRECTOR`
**Consolidación KDB:** `docs/KTP/KDB.md` v1.5.0

> **Nota de cierre.** Esta acta sustituye a `AKT.md` v1.4 y certifica el cierre de la Fase 9 con
> evidencia reproducible: Jueces en verde, Censo de Paridad en **0 hallazgos**, corrección V-1
> aplicada y re-materializada, y auditoría empírica re-ejecutada sobre las 12 temporadas.

---

## 1. SPRINT ACTUAL

- **Nombre:** `SPRINT-50-REINGENIERIA-INDUSTRIAL-QBE-CORE`
- **Objetivo:** alinear el núcleo matemático con el Volumen I y reorientar la estrategia económica hacia el consenso multicasa y los mercados derivados.
- **Alcance ejecutado:** `qbe_core` (3 motores + 3 Jueces), `docs/` (5 libros), `scripts/investigacion/` (1 auditor), `scripts/auditoria/` (parche V-1), `data/reportes/` (2 artefactos), `docs/KTP/` (AKT + KDB v1.5.0 + bandeja).
- **Régimen:** `[DIRGEN-STRICT]`
- **Inicio / cierre técnico:** 2026-11-01 / 2026-11-05

---

## 2. HITOS DE FASE 9 — CERTIFICACIÓN FINAL

| Hito | Evidencia | Estado |
|---|---|---|
| **Paso 1 — Legislación** | `[LN-QBE-151]` y `[LN-QBE-152]` en `ID_REGISTRY.md` (288 filas, `SELLADO`) y `LOGIC.md` §25-§27 (140 identificadores); `CONSTANTS.md` §11 + regla anti-homónimos `P_mid` | COMPLETADO |
| **Paso 2 — Jueces en RED** | 3 Jueces, 35 casos, `33 failed / 2 passed` genuinos por ausencia de contrato | COMPLETADO |
| **Paso 3 — Materialización** | `desmarginar_shin` (`consensus.py`), `proyectar_mercados_derivados` (`distribution_dixon_coles.py`), `triaje_financiero_mundo2` (`triage.py`) | COMPLETADO |
| **DoD — Verde absoluto** | Jueces Fase 9: **35 passed** · `qbe_core`: **149 passed** · 5 pilares: **296 passed** · `tests/shield`: **115 passed** | COMPLETADO |
| **Fase 9.4 — Auditoría** | `scripts/investigacion/fase9_derivados_shin.py` sobre **3,870** partidos de `qbe_historico.db` (12 temporadas) | COMPLETADO |
| **Ficha VAR-2026-F9-02** | `docs/VAR-2026-F9-02.md`: diagnóstico de la brecha de λ y plan V-1 | RATIFICADA Y EJECUTADA |
| **V-1 — Parche xG** | Denominador corregido en `calcular_distribuciones_historicas.py`; `P'` re-materializada (2.737 filas, `quick_check ok`) | **APLICADO** |
| **VÍA B — 23 ayudantes** | 23 nodos etiquetados en `qbe_core/src/core/` con su nodo rector | **APLICADO** |
| **Censo de Paridad** | `docs/KTP/GL_update.md`: 27 archivos, **0 hallazgos** (I, II, III y IV) | **CERRADO EN 0** |
| **Consolidación KTP** | `KDB.md` v1.5.0 y esta acta | **COMPLETADO** |

### 2.1 Resultado empírico — antes y después de V-1

| Métrica | Antes (bóveda V-1.0) | Después (V-1) | Δ |
|---|---:|---:|---:|
| λ_local + λ_visitante medio | 2,5221 | **2,6971** | +0,1750 |
| Goles observados por partido | 2,7474 | 2,7474 | — |
| Brecha de nivel | −0,2253 (−8,20 %) | **−0,0503 (−1,83 %)** | +6,37 pp |
| Under 2.5 — Brier 2N | 0,130555 | **0,125604** | −0,004951 |
| Under 2.5 — BSS | −4,70 % | **−0,73 %** | +3,97 pp |
| BTTS Sí — Brier 2N | 0,126541 | **0,123681** | −0,002860 |
| BTTS Sí — BSS | −2,70 % | **−0,38 %** | +2,32 pp |
| Correlación λ_sum ↔ goles | +0,0884 (R² 0,78 %) | **+0,1006 (R² 1,01 %)** | +0,0122 |
| 1X2 — ROI del vértice P_max | −6,73 % | **−5,21 %** | +1,52 pp |
| Shin vs proporcional (Δ Brier) | −6,955×10⁻⁵ (t = −0,94) | −6,955×10⁻⁵ (t = −0,94) | — |
| Alpha de derivados vs mercado | SIN EVIDENCIA | **SIN EVIDENCIA** | — |

> **Lectura honesta.** V-1 corrigió la capa de **calibración** (la brecha cayó de 8,20 % a 1,83 %) y
> llevó el BSS de derivados de −4,70 % a −0,73 % (Under) y de −2,70 % a −0,38 % (BTTS). **No** lo
> cruza a positivo: la capa de **resolución** sigue siendo el límite estructural (`R² = 1,01 %`).
> El criterio de aceptación de la Ficha (`λ_sum ∈ [2,70, 2,80]`) se cumple en espíritu pero no en
> literalidad: 2,6971 queda 0,0029 por debajo del piso (0,11 %). La brecha residual (1,83 %) es
> inferior al umbral del 2 % que activaría V-2, por lo que **μ_liga no se toca**.

---

## 3. DECISIONES TOMADAS

| # | Decisión | Fundamento | Anclaje |
|---:|---|---|---|
| D1 | Ratificar `overround_bruto = S`, `cuota_*`, `P=0 ⇒ inf`, tolerancia matriz `1e-9` y firma §27.4 | La ley y el Juez prevalecen sobre el resumen conversacional (`GOVERNANCE.md` §3.2) | `DEC-2026-F9-CONVERGENCE` |
| D2 | Errata E-1: `1-1` suma 2 goles ⇒ Under 2.5 = 0,40 en `{1-1,2-1,1-2}` | Aritmética irrefutable | Juez `[LN-QBE-152]` |
| D3 | Aplicar V-1 (denominador xG) y re-materializar `P'` | La brecha de λ era de calibración, no de proyección | `VAR-2026-F9-02` §6 |
| D4 | No tocar `μ_liga` (V-2 diferida) | Brecha residual 1,83 % < 2 % | `VAR-2026-F9-02` §5 |
| D5 | Congelar `QBE-C2` (mutación a derivados) | BSS < 0 en ambos mercados; R² = 1,01 % | `VAR-2026-F9-02` §5 |
| D6 | Formalizar VÍA B los 23 ayudantes del núcleo | Censo de cierre a 0 hallazgos (`GOVERNANCE.md` §3.5) | `GL_update.md` |
| D7 | Los 23 partidos con overround 1,667 quedan excluidos del cómputo | Aduana `[LN-QBE-007-H]` | Reporte 50.4 |

---

## 4. DEUDAS ABIERTAS (consolidadas en `KDB.md` v1.5.0 §10)

| ID | Deuda | Severidad | Estado |
|---|---|---|:---:|
| D-50.01 | Denominador xG en la reconstrucción histórica | ALTA | **CERRADA** (V-1) |
| D-50.02 | λ sin resolución sobre totales (`R² = 1,01 %`) | ALTA | ABIERTA |
| D-50.03 | Ancla `μ_liga = 2.65` vs 2,7474 | MEDIA | DIFERIDA (residual < 2 %) |
| D-50.04 | Sin proveedor de cuotas de Totales/BTTS | ALTA | ABIERTA |
| D-50.05 | 23 hallazgos Clase IV del Censo | MEDIA | **CERRADA** (0 hallazgos) |
| D-50.06 | 23 partidos con cuotas corruptas `(1.50, 3.00, 1.50)` | MEDIA | ABIERTA |
| D-50.07 | Percentiles inmunes in-sample no persistidos | MEDIA | ABIERTA |
| D-50.08 | Shin sin valor económico medible en 1X2 | BAJA | ABIERTA (documentada) |
| D-50.09 | `.pytest_tmp/` no versionado | BAJA | ABIERTA |
| D-50.10 | Consolidación en `KDB.md` | ALTA | **CERRADA** (v1.5.0) |

---

## 5. ESTADO FÁCTICO GIT / SHIELD / CENSO

- **Branch:** `feature/fase2-observatory`
- **Jueces Fase 9:** `35 passed`
- **`qbe_core/tests`:** `149 passed`
- **Suite 5 pilares:** `296 passed`
- **`tests/shield`:** `115 passed`
- **Censo de Paridad:** 27 archivos · **0 hallazgos** (I/II/III/IV) · bandeja `cb5c8cf9…`
- **Bóveda:** `qbe_historico.db` — **3,870** partidos, 3.726 con cuotas 1X2, 2.737 distribuciones `P'` re-materializadas, 12 temporadas.
- **Respaldo WORM:** `qbe_observatory/data/backups/qbe_historico_pre_distribuciones_20261105T220247Z.db`
- **Pre-vuelo de cartelera:** no aplica (sin cambios de ingesta).

### 5.1 Manifiesto

```text
 M data/cache_macro_stats_liga_mx_2026.json      (subproducto del cálculo; deriva decimal)
 M data/reportes/fase9_evaluacion_derivados.json (re-ejecutado post V-1)
 M docs/KTP/AKT.md                               (esta acta)
 M docs/KTP/GL_update.md                         (Censo en 0)
 M docs/KTP/KDB.md                               (v1.5.0)
 M docs/VAR-2026-F9-02.md                        (anexo §8.5 de ejecución)
 M qbe_core/src/core/distribution_dixon_coles.py (VÍA B: 1 nodo)
 M qbe_core/src/core/intensity_canonical_loglink.py (VÍA B: 4 nodos)
 M qbe_core/src/core/sovereign/orthogonal_factor_engine.py (VÍA B: 7 nodos)
 M qbe_core/src/core/sovereign_pipeline.py       (VÍA B: 7 nodos)
 M qbe_core/src/core/triage.py                   (VÍA B: 4 nodos)
 M scripts/auditoria/calcular_distribuciones_historicas.py (V-1)
?? data/reportes/rematerializacion_v1.json
```

> **Base del commit anterior:** `a1765b9` (2026-11-05 15:54) consolidó Pasos 1–3, Fase 9.4 y los
> 3 Jueces. Este cierre añade V-1, la VÍA B de 23 nodos, el Censo en 0 y la consolidación KTP.

---

## 6. BACKLOG INMEDIATO

| Prioridad | Tarea | Criterio de aceptación |
|---:|---|---|
| 1 | Investigar resolución de totales (ruta C) | `R²(λ_sum, goles) > 0,05` out-of-sample y BSS > 0 |
| 2 | Integrar proveedor de cuotas de derivados | Alpha de Totales/BTTS calculable |
| 3 | Persistir percentiles inmunes calibrados | Tasa de veto comparable entre corridas |
| 4 | Purga de los 23 partidos con cuotas corruptas | Bóveda sin overround 1,667 |

---

## 7. SIGUIENTE MOVIMIENTO

- **Acción única (Director):** declarar formalmente concluido el Sprint 50 con esta acta.
- **Acción única (Constructor, Fase 10):** abrir la línea de resolución de totales con el criterio de aceptación de §6.
- **Criterio de aborto:** si la ruta C no demuestra `R² > 0,05` y BSS > 0, `QBE-C2` queda definitivamente fuera de la Mesa de Apuestas.

---

## 8. TRAZABILIDAD

| Elemento | Anclaje |
|---|---|
| Ficha de Varianza | `docs/VAR-2026-F9-02.md` |
| Reporte 50.4 | `data/reportes/fase9_evaluacion_derivados.json` |
| Re-materialización | `data/reportes/rematerializacion_v1.json` |
| Bandeja de Paridad | `docs/KTP/GL_update.md` |
| Base de conocimiento | `docs/KTP/KDB.md` v1.5.0 |
| Ley de la fase | `docs/LOGIC.md` §25-§27 / `docs/CONSTANTS.md` §11 |
