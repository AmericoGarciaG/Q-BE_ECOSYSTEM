# AKT — REPORTE ACTIVO DE TRANSFERENCIA

**Sprint:** `SPRINT-45-EXPANSION-CAUSAL-Y-RESCATE-EN-VIVO`<br>
**Fecha:** 2026-11-01<br>
**Autoridad:** Américo García Guerrero (Director Humano)<br>
**Arquitecto saliente:** Constructor Kybern / Extracción causal y auditoría de bóveda<br>
**Estado:** `PENDIENTE DE CONSOLIDACIÓN`<br>
**Régimen:** `[DIRGEN-STRICT]` — documentación de transferencia; jurisdicción exclusiva `docs/KTP/AKT.md`<br>
**Nodos:** `[LN-QBE-138]` / `[ARCH-1.4.74]`

> **Nota de evidencia (Fail-Loud).** Este delta no certifica como concluido lo que no tiene evidencia. Al corte: `C01-C08` no existe en la Base de Gobierno ni en el código; el Daemon `Centinela` no está operando; no se emitió Ficha de Varianza; no existe split Train/Test. Todo lo anterior se declara abajo con su estado real.

## 1. SPRINT ACTUAL

- **Nombre:** `SPRINT-45-EXPANSION-CAUSAL-Y-RESCATE-EN-VIVO`.
- **Objetivo:** rescatar la ingesta en vivo, auditar la cobertura de la bóveda histórica y materializar el catálogo de 8 variables compuestas (`C01-C08`) para la calibración cruzada (Train/Test).
- **Alcance:** `docs/KTP/AKT.md` como vehículo de transferencia; lectura de solo lectura de `qbe_observatory/data/qbe_historico.db` y del estado Git. **No se modifica código en `src/`, no se altera `KDB.md` ni la Base de Gobierno fuera de KTP.**
- **Régimen:** `[DIRGEN-STRICT]` para documentación, datos y Jueces. Cero datos sintéticos; ausencia declarada como `SIN EVIDENCIA`.
- **Fecha de inicio / cierre:** 2026-11-01 / PENDIENTE.
- **Criterio de asunción:** el Arquitecto entrante debe leer `docs/KTP/KDB.md`, este `AKT.md` y `docs/KTP/KTP_Guide.md`, emitir su Eco de Comprensión y verificar la Sección 5 antes de tocar cualquier archivo.

## 2. HITOS CONCLUIDOS

> **Fail-Loud:** las dos filas ordenadas por la Directiva se registran con su estado real, no como avance simulado. `C01-C08` no tiene ID, Juez ni código; el Daemon no está operando.

| Hito | ID / Juez | Evidencia | Estado |
|---|---|---|---|
| Implementación del Catálogo Compuesto (`C01-C08`) | ID: **SIN ASIGNAR** (próximo libre `[LN-QBE-148]`, no sellado) · Juez: **NO MATERIALIZADO** | No existe `C01`–`C08` en `docs/LOGIC.md`, `docs/ID_REGISTRY.md` ni en `qbe_core/`; la búsqueda en `docs/` y `qbe_core/` no devuelve coincidencias y los únicos matches están en base64 del MHTML de muestra. No hay columnas, tabla ni contrato de las 8 variables. | **NO INICIADO — SIN EVIDENCIA** |
| Migración y Operación del Daemon en Vivo (`Centinela`) | `[VAULT-DAEMON-001]` / `[VAULT-DAEMON-001-B]` · Juez de operación en vivo: **NO EXISTE**; solo paridad de imports | Fuente en `qbe_ingestion/src/ingestion/daemons/centinela_deportivo.py`; no existe `scripts/daemons/`; sin proceso Python visible; sin tarea programada asociada (filtro `qbe`/`centinela`/`daemon`); sin log de operación localizado. | **DETENIDO — NO OPERANDO** |
| Extracción causal minuto a minuto (2015-2016) | `[LN-QBE-141]`–`[LN-QBE-145]` · Jueces: `test_shield_minuto_a_minuto_parser.py`, `test_shield_descubrimiento_ligamx.py`, `test_shield_orquestador_extraccion.py` | **301** partidos con **13,443** eventos en `historical_match_events`; muestra de 49 eventos: América 3-3 Monterrey (`fs_2015_2016_z85264`, J16 Clausura 2016). | **COMPLETADO TÉCNICO — SIN COMMIT** |
| Derivación de 32 variables causales (9 derivadas / 23 `SIN EVIDENCIA`) | `[LN-QBE-146]` · Juez: `test_shield_derivacion_causal.py` | **301** filas en `historical_match_causal_vars`; `derivadas = 9` en 301/301; `sin_evidencia` con 23 variables. | **COMPLETADO TÉCNICO — SIN COMMIT** |
| Calibración in-sample 2015-2016 | `[LN-QBE-147]` · Juez: `test_shield_calibracion.py` | 301 partidos; Brier base `0.65546144` → optimizado `0.59896449` (Δ `-0.05649695`; mejora `8.62%`); mercado `0.64031362`; acta `2026-11-01T06:54:38Z` en `data/reportes/calibracion_2015_2016.json`. | **COMPLETADO (IN-SAMPLE) — SIN TRAIN/TEST** |

## 3. DECISIONES TOMADAS

| Decisión | Razón | Impacto | Anclaje |
|---|---|---|---|
| **D1. No inventar `C01-C08`.** | No existe especificación, ID sellado, Juez ni columnas en la bóveda. Materializarlas por inferencia violaría `[GOVERNANCE-01]` y el régimen `[DIRGEN-STRICT]`. | El catálogo queda como deuda ALTA y Prioridad 2; no se usa en la calibración de este turno. | `docs/KTP/AKT_Pmpt.md` regla 1; `AGENTS.md`; `[LN-QBE-146]`. |
| **D2. No declarar operativo el Daemon.** | No hay proceso, tarea programada, log ni Juez de operación en vivo. La fuente existe, pero la migración/operación no está evidenciada. | El Daemon queda `DETENIDO`; la ingesta en vivo no se considera rescatada. | `[VAULT-DAEMON-001]`; `qbe_ingestion/tests/test_parity_ingestion_daemons.py`. |
| **D3. No presentar el Brier in-sample como Train/Test.** | `[LN-QBE-147]` no implementa partición temporal; el acta usa los 301 partidos completos de 2015-2016. | La mejora de 8.62% mide ajuste in-sample, no capacidad predictiva; el overfitting queda sin dictamen. | `docs/LOGIC.md` §20, limitación declarada de `[LN-QBE-147]`. |
| **D4. No emitir Ficha de Varianza sin fallo documentado.** | No consta intento de rescate del Daemon ni fallo de red/credenciales en este turno. Emitirla sin evidencia sería fabricar un incidente. | No hay `DIRGEN_VARIANCE_REQUEST.md`; solo la plantilla/parte histórico. Si el rescate falla por credenciales, se emite y se enlaza. | `docs/DIRGEN_VARIANCE_REQUEST_TEMPLATE.md`; `AGENTS.md`, Protocolo Anti-Bandazos. |

## 4. DEUDAS ABIERTAS

| Deuda | Severidad | Impacto | Siguiente acción | Responsable |
|---|---|---|---|---|
| **¿Se emitió `DIRGEN_VARIANCE_REQUEST.md` durante este sprint?** | ALTA | **NO — sin enlace.** El archivo no existe; solo están `docs/DIRGEN_VARIANCE_REQUEST_TEMPLATE.md` y el parte histórico resuelto `VAR-2026-J7-HOMOLOGACION` (2026-10-14), ajeno al Sprint 45. No consta fallo de red/credenciales del Daemon. | Si el rescate del Daemon falla por red/credenciales, emitir el parte y enlazarlo aquí antes de tocar código. | Arquitecto |
| Catálogo Compuesto `C01-C08` no materializado | ALTA | No hay 8 variables compuestas (ej. Reacción post-gol), ni ID, ni Juez, ni columnas en la BD; la calibración cruzada no puede ejecutarse sobre ese catálogo. | Definir especificación, asignar ID sellado, crear Juez Inmutable, migrar columnas y poblar 301 partidos. | Director / Arquitecto |
| Daemon en vivo `Centinela` detenido | ALTA | La ingesta en vivo no está rescatada; no hay proceso ni tarea programada. La causa raíz no está diagnosticada. | Diagnosticar red/credenciales/entorno, arrancar el Daemon y dejar log; o emitir Ficha de Varianza. | Arquitecto / Infraestructura |
| Sin split Train/Test | ALTA | El Brier `0.65546144 → 0.59896449` es in-sample; no hay evidencia fuera de muestra ni dictamen de overfitting. | Implementar partición temporal y ejecutar calibración cruzada; si no hay Test, declarar `SIN EVIDENCIA`. | Arquitecto |
| Cobertura histórica incompleta | ALTA | **0** temporadas con 32 variables; solo `2015_2016` con 9 variables y 301/334 partidos. Las otras 11 temporadas no tienen eventos. | Extraer eventos de las 11 temporadas restantes o declarar el alcance de la calibración. | Ingesta / Arquitecto |
| Sonda `auditar_boveda_historica.py` ausente | MEDIA | No existe el instrumento canónico de auditoría de cobertura; la auditoría de §4.1 se hizo con consulta SQL de solo lectura. | Materializar la sonda y su Juez; ejecutarla contra `qbe_historico.db`. | Constructor |
| Pipeline causal sin commit | MEDIA | 301 vectores, 13,443 eventos y los módulos nuevos del pipeline causal viven en el working tree; no son reproducibles desde Git. | Commit atómico con tests y actualización de BG; no mezclar con datos crudos. | Constructor |

### 4.1 Auditoría de Cobertura Histórica

**Pregunta rectora:** ¿qué temporadas tienen el vector completo de 32 variables y cuáles solo la cobertura de 9 variables derivada de eventos?

- **Temporadas con 32 variables (Completas):** **NINGUNA** (0 de 12).
- **Temporadas con 9 variables (Minuto a Minuto):** **`2015_2016`** (301 de 334 partidos; 13,443 eventos; 9 derivadas / 23 `SIN EVIDENCIA`).

| Temporada | Partidos | Con eventos | Con vector causal | 32 vars | 9 vars |
|---|---:|---:|---:|---:|---:|
| `2015_2016` | 334 | 301 | 301 | 0 | 301 |
| `2016_2017`–`2026_2027` (11 temporadas) | 3,536 | 0 | 0 | 0 | 0 |
| **Total** | **3,870** | **301** | **301** | **0** | **301** |

- **Lectura fiduciaria:** no existe ninguna temporada con las 32 variables. La única cobertura causal es `2015_2016`, y cubre 9 de 32 variables en el 90.12% de sus partidos (301/334). Las 23 variables restantes están declaradas `SIN EVIDENCIA`; no se imputan.
- **Muestra de referencia:** 49 eventos de América 3-3 Monterrey (`fs_2015_2016_z85264`), J16 Clausura 2016; rango de fechas de los eventos: `2015-07-25T00:30:00Z` a `2016-05-08T22:00:00Z`.
- **Consecuencia:** la calibración de 301 partidos es una calibración de 9 variables, no de 32. No se puede afirmar que el modelo esté calibrado sobre el catálogo completo.

## 5. ESTADO FÁCTICO GIT / SHIELD

- **Branch:** `feature/fase2-observatory`.
- **HEAD:** `fac1bb0` — 2026-10-31 11:09:10 -0600 — `docs(ktp): Actualización de delta activo AKT.md para prueba de fuego KTP (Consistencia BG)`.
- **Working tree:** **SUCIO**. Modificados: `docs/ARCH.md`, `docs/GOVERNANCE.md`, `docs/ID_REGISTRY.md`, `docs/KTP/AKT.md`, `docs/KTP/KDB.md`, `docs/LOGIC.md`, 14 módulos de `qbe_core/src/core/` y `qbe_ingestion/src/ingestion/loaders/__init__.py`. No trackeados: `data/raw_ligamx_min_x_min/`, `data/reportes/`, `docs/KTP/GL_update.md`, `docs/KTP/history/AKT_2026-10-31_SPRINT-41-TRANSICION-Y-CONSISTENCIA-BG.md`, `qbe_core/src/core/normalization/ligamx_alias.py`, `qbe_core/src/core/sovereign/calibrar_perturbacion.py`, `qbe_core/src/core/sovereign/derivar_variables_causales.py`, tests nuevos de derivación/calibración/parser/orquestador, parser y loader de eventos, y `scripts/auditoria/`.
- **Juez de gobernanza:** **3/3 PASSED** (`pytest qbe_core/tests/test_shield_ecosystem_governance.py -q --no-header`).
- **Juez KTP:** **5/5 PASSED** (`pytest qbe_core/tests/test_shield_ktp_package_integrity.py -v`).
- **Suite unificada:** `pytest qbe_core/tests qbe_business/tests qbe_ingestion/tests qbe_observatory/tests qbe_storage/tests -q --no-header` → **NO EJECUTADA EN ESTE TURNO** (fuera del alcance de esta directiva; solo se ejecutaron los Jueces KTP y de gobernanza). No se afirma `EXIT CODE 0`.
- **Pre-vuelo de cartelera:** **no aplica** en este turno: solo se modificó `docs/KTP/AKT.md`; no se tocaron motores estocásticos, ingesta ni datos.
- **Bóveda fáctica:** **3,870** partidos; **3,726** con cuotas 1X2 completas; **12 temporadas** (`2015_2016` a `2026_2027`); **301** partidos con eventos (**13,443** eventos); **301** filas en `historical_match_causal_vars`; **217** filas en `historical_team_season_stats`; **0** filas con xG por partido (`xg_home`/`xg_away` no poblados). DB: `qbe_observatory/data/qbe_historico.db`.
- **Sonda de auditoría de la bóveda:** comando canónico previsto:
  ```powershell
  .\.venv\Scripts\python.exe scripts/auditoria/auditar_boveda_historica.py --db qbe_observatory/data/qbe_historico.db
  ```
  Estado: **NO MATERIALIZADO**. El archivo no existe y el comando no se ejecutó. La cobertura de §4.1 se obtuvo con consulta SQL de solo lectura (`PRAGMA query_only=ON`, URI `?immutable=1`) sobre `historical_matches`, `historical_match_events` y `historical_match_causal_vars`.
- **Estado del Daemon en Vivo: DETENIDO.** Sin proceso Python visible, sin tarea programada asociada (filtro `qbe`/`centinela`/`daemon`) y sin log de operación localizado. La causa raíz no está diagnosticada; no se observó fallo de red/credenciales en este turno. No se declara `BLOQUEADO` porque no hay evidencia de credenciales faltantes.
- **Brier Score Train vs. Test:** **NO EJECUTADO.** No existe split Train/Test en `[LN-QBE-147]`; el acta es in-sample. Evidencia in-sample (301 partidos, 2015-2016): Brier base `0.65546144`; optimizado `0.59896449`; Δ `-0.05649695` (mejora `8.62%`); mercado `0.64031362`. **Train:** sin partición formal (se usan los 301 partidos); **Test:** `SIN EVIDENCIA`.
- **Datos no verificados:** (1) `C01-C08`: sin ID, Juez, contrato ni columnas; (2) operación del Daemon y su causa raíz; (3) Brier Test y overfitting; (4) temporadas con 32 variables (0); (5) xG por partido (0 filas); (6) `auditar_boveda_historica.py` (ausente); (7) suite unificada (no ejecutada); (8) línea base financiera `+5.85%` / `1.5%` / `$10,000`: declarada por Dirección, no auditada.

## 6. BACKLOG INMEDIATO

| Prioridad | Tarea | Criterio de aceptación |
|---:|---|---|
| 1 | **Estado del Daemon en Vivo:** si no está operando automáticamente, documentar el bloqueo técnico exacto para que el Arquitecto entrante sepa si debe intervenir infraestructura. | Proceso vivo + tarea programada + log de operación, o `DIRGEN_VARIANCE_REQUEST.md` con causa raíz (red/credenciales/entorno) y enlace. |
| 2 | **Validar que las 8 variables `C01-C08` (ej. Reacción post-gol) están correctamente pobladas en la BD.** | Especificación en `LOGIC.md`, ID sellado en `ID_REGISTRY.md`, Juez Inmutable en verde, 8 columnas/tabla y 301 partidos poblados sin nulos no explicados. |
| 3 | **Ejecutar la Calibración Cruzada y reportar si el modelo sufre de Overfitting.** | Split temporal Train/Test (2015-2016 → 2016-2017), Brier Train y Test, Δ y veredicto de overfitting. Prerrequisito: 2016-2017 tiene **0** eventos; sin extracción, el Test no existe y se declara `SIN EVIDENCIA`. |

## 7. SIGUIENTE MOVIMIENTO

- **Acción única:** revisar la **Auditoría de Cobertura Histórica** de §4.1 y aprobar o rechazar la muestra Train/Test `2015-2016 → 2016-2017`.
- **Comando / punto de entrada:** `docs/KTP/AKT.md` §4.1; `scripts/auditoria/ejecutar_calibracion.py` solo ejecuta in-sample (`--temporada 2015-2016`). No existe CLI Train/Test.
- **Resultado esperado:** decisión firmada: (a) aprobar `2015-2016` como Train y ordenar la extracción de `2016-2017` para Test; o (b) declarar `SIN EVIDENCIA` y no calibrar. En ambos casos, el Daemon queda operando o con Ficha de Varianza.
- **Riesgo principal:** overfitting. La única evidencia es in-sample (301 partidos, 9/32 variables) y la mejora de 8.62% no tiene contraparte fuera de muestra.
- **Criterio de aborto:** si el Daemon no se puede rescatar por falta de credenciales, emitir `DIRGEN_VARIANCE_REQUEST.md` y proceder a calibrar solo con el histórico. Si no hay Test, no se afirma capacidad predictiva ni se declara superación del mercado.
- **Definición de terminado:** cobertura firmada + decisión Train/Test + Daemon `OPERANDO` o Ficha de Varianza + Juez KTP en verde + suite unificada con `EXIT CODE 0`.

---

> **Firma de transferencia.** Delta emitido por el Constructor Kybern el 2026-11-01. La asunción de mando queda **PENDIENTE** hasta que el Arquitecto entrante emita su Eco de Comprensión, verifique la Sección 5 y confirme que puede operar sin reconstruir el historial. Este AKT no sustituye a `KDB.md`; es el delta del turno.
