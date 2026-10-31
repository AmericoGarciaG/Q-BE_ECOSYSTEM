# AKT — REPORTE ACTIVO DE TRANSFERENCIA

**Sprint:** 38 — Cierre de carga histórica multianual  
**Fecha:** 2026-10-30  
**Autoridad:** Américo García Guerrero (Director Humano)  
**Arquitecto saliente:** Agente Constructor Kybern / Arquitecto de Materialización  
**Estado:** CERRADO — listo para consolidación  
**Nodos:** `[LN-QBE-138]` / `[ARCH-1.4.74]`

---

## 1. SPRINT ACTUAL

- **Nombre:** `SPRINT-MATERIALIZACION-PAQUETE-KTP-DOCS-39` — cierre operativo del Sprint 38.
- **Objetivo:** institucionalizar el paquete de transferencia `docs/KTP/` y dejar el estado fáctico del cierre histórico de 12 temporadas en la Base de Conocimiento.
- **Alcance:** `docs/LOGIC.md`, `docs/ARCH.md`, `docs/ID_REGISTRY.md`, `docs/KTP/` y `qbe_core/tests/test_shield_ktp_package_integrity.py`.
- **Régimen:** `[DIRGEN-STRICT]` para gobierno y Juez; sin cambios en código de producción.
- **Fecha de inicio / cierre:** 2026-10-30 / 2026-10-30.

---

## 2. HITOS CONCLUIDOS

| Hito | Evidencia | Estado |
|---|---|---|
| Carga histórica de 12 temporadas en SQLite 3NF | `historical_load_log`: 12 filas `OK`; `historical_matches`: 3,870 | COMPLETADO |
| Corpus con cuotas 1X2 completas | 3,726 partidos con `odd_home`, `odd_draw` y `odd_away` no nulos | COMPLETADO |
| Estadísticas club-temporada | 217 filas en `historical_team_season_stats` | COMPLETADO |
| Parser offline MHTML y cargador idempotente | `qbe_ingestion/src/ingestion/parsers/parsear_footystats_mhtml.py`; `qbe_ingestion/src/ingestion/loaders/load_historical_footystats.py` | COMPLETADO |
| Sonda CDP-MHTML y Juez de muestras | `[LN-QBE-136]` / `[LN-QBE-137]`; commit `56902a4` | COMPLETADO |
| Monorepo estabilizado en cuatro pilares | `qbe_core`, `qbe_business:8000`, `qbe_observatory:8001`, `qbe_ingestion:8002` + `qbe_storage` | COMPLETADO |
| Paquete KTP materializado | `docs/KTP/` con 5 archivos + `history/` | COMPLETADO |
| Juez KTP en verde | `qbe_core/tests/test_shield_ktp_package_integrity.py` — 4/4 PASSED | COMPLETADO |

---

## 3. DECISIONES TOMADAS

| Decisión | Razón | Impacto | Anclaje |
|---|---|---|---|
| Persistencia 3NF con carga idempotente por temporada | Evitar duplicados y permitir reruns seguros. | 12 temporadas cargadas con `historical_load_log` y hash por temporada. | `[LN-QBE-135]` |
| `NULL` honesto para datos ausentes | Cumplir `[GOVERNANCE-01]`; no inventar marcadores, cuotas ni xG. | Partidos futuros o cancelados conservan `NULL`. | `docs/GOVERNANCE.md` §2 |
| IDs nuevos `[LN-QBE-138]` / `[ARCH-1.4.74]` | `136`, `137` y `1.4.73` ya estaban sellados; no se reasignan. | Trazabilidad preservada; sin colisión. | `docs/ID_REGISTRY.md` |
| Archivo de `AKT.md` por copia + reinicio | La invariante exige que `AKT.md` exista siempre. | `history/` conserva el acta; el activo se reinicia. | `[LN-QBE-138]` |
| Línea base financiera declarada | `+5.85%`, `1.5%` y `$10,000` no tienen acta empírica en el repo. | Se presenta con provenance, no como resultado auditado. | `docs/KTP/KDB.md` §6 |

---

## 4. DEUDAS ABIERTAS

| Deuda | Severidad | Impacto | Siguiente acción | Responsable |
|---|---|---|---|---|
| xG por partido no poblado en `historical_matches` | MEDIA | Modelos que requieren xG a nivel partido no pueden calibrarse con esa columna. | Cargar xG o declarar `SIN EVIDENCIA` por temporada. | Ingesta / Arquitecto |
| Wrapper CLI de pre-vuelo ausente | BAJA | El pre-vuelo se ejecuta por módulo, no por wrapper. | Crear `scripts/auditoria/auditar_coherencia_cartelera.py` o corregir la referencia. | Arquitecto |
| Cuerpo de `[ARCH-1.4.73]` ausente | BAJA | Deuda documental; no afecta el ID ni el contrato KTP. | Reconciliar en sprint documental posterior. | Arquitecto |
| Línea base financiera sin acta reproducible | MEDIA | Riesgo de presentar una declaración como resultado. | Producir acta con comando, fecha y evidencia. | Director / Arquitecto |
| `data/sondas_exploracion/` sin trackear | BAJA | Ruido en `git status`. | Mantener fuera del commit KTP. | Constructor |

---

## 5. ESTADO FÁCTICO GIT / SHIELD

- **Branch:** `feature/fase2-observatory`
- **HEAD:** `56902a4` — 2026-10-30 20:09:34 -0600
- **Working tree:** `data/sondas_exploracion/` no trackeado; sin cambios en código de producción.
- **Juez de gobernanza:** 3 passed / 0 failed.
- **Juez KTP:** 4/4 PASSED (`pytest qbe_core/tests/test_shield_ktp_package_integrity.py -v`).
- **Suite unificada:** 160 passed, 1 warning, EXIT CODE 0. Se ejecutó con `TMP`/`TEMP`/`TMPDIR` redirigidos a `.bt_run/pytest_tmp` por una restricción de permisos del directorio temporal de Windows; no se modificó código de producción.
- **Pre-vuelo de cartelera:** 0 🔴, 9 🟡, EXIT 0 sobre `data/snapshots/qbe_database_snapshot.db`.
- **Bóveda fáctica:** 3,870 partidos; 3,726 cuotas; 12 temporadas; `qbe_observatorio/data/qbe_historico.db`; 217 filas de stats club-temporada.
- **Datos no verificados:** ROI `+5.85%`, drawdown `1.5%` y `B0=$10,000` son línea base declarada, no auditada; xG por partido = 0 filas.

---

## 6. BACKLOG INMEDIATO

| Prioridad | Tarea | Criterio de aceptación |
|---:|---|---|
| 1 | Entrenar/calibrar el nuevo modelo multianual Q-BE. | Acta de calibración con Brier, baseline y corte temporal. |
| 2 | Resolver la deuda de xG por partido. | Carga verificada o declaración `SIN EVIDENCIA` por temporada. |
| 3 | Crear el wrapper CLI de pre-vuelo. | `scripts/auditoria/auditar_coherencia_cartelera.py` ejecuta el módulo canónico. |
| 4 | Reconciliar el cuerpo de `[ARCH-1.4.73]`. | Sección documental sin reasignar el ID. |
| 5 | Repetir el pre-vuelo en la próxima cartelera. | `coherence_auditor --check` → 0 🔴, EXIT 0. |

---

## 7. SIGUIENTE MOVIMIENTO

- **Acción única:** iniciar el entrenamiento y calibración del nuevo modelo multianual Q-BE sobre las 12 temporadas cargadas.
- **Comando / punto de entrada:** pipeline de calibración del Observatorio sobre `qbe_observatory/data/qbe_historico.db`, en modo solo lectura.
- **Resultado esperado:** acta de calibración con Brier Score, baseline de mercado y curvas por temporada.
- **Riesgo principal:** usar xG por partido sin cobertura; debe declararse `SIN EVIDENCIA` y no imputarse.
- **Criterio de aborto:** si el modelo requiere una variable sin evidencia y no hay sustituto soberano, detener y emitir Ficha de Varianza.

---

## 8. FIRMA DE TRANSFERENCIA

| Campo | Valor |
|---|---|
| Arquitecto saliente | Agente Constructor Kybern |
| Fecha de despacho | 2026-10-30 |
| Estado del delta | CERRADO |
| Consolidación | Pendiente de ejecución por el Constructor con `KDB_Act_Pmpt.md` |
| Archivo destino | `docs/KTP/history/AKT_2026-10-30_SPRINT-38.md` |

> Este AKT no sustituye a `KDB.md`. Es el delta del turno. La consolidación actualizará la Base de Conocimiento y archivará este reporte por copia.
