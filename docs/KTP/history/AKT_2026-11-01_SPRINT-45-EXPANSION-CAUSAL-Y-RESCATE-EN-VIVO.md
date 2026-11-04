# AKT — REPORTE ACTIVO DE TRANSFERENCIA

**Sprint:** `SPRINT-45-EXPANSION-CAUSAL-Y-RESCATE-EN-VIVO`<br>
**Fecha:** 2026-11-01<br>
**Autoridad:** Américo García Guerrero (Director Humano)<br>
**Arquitecto saliente:** Constructor Kybern / Extracción causal y auditoría de bóveda<br>
**Estado:** `CERRADO`<br>
**Régimen:** `[DIRGEN-STRICT]` — documentación de transferencia; jurisdicción exclusiva `docs/KTP/AKT.md`<br>
**Nodos:** `[LN-QBE-138]` / `[ARCH-1.4.74]`

> **Nota de evidencia (Fail-Loud).** Este delta no certifica como concluido lo que no tiene evidencia. Al corte: `C01-C08` no existe en la Base de Gobierno ni en el código; el Daemon `Centinela` no está operando; no se emitió Ficha de Varianza; no existe split Train/Test. Todo lo anterior se declara abajo con su estado real.

## 1. SPRINT ACTUAL

- **Nombre:** `SPRINT-45-EXPANSION-CAUSAL-Y-RESCATE-EN-VIVO`.
- **Objetivo:** rescatar la ingesta en vivo, auditar la cobertura de la bóveda histórica y materializar el catálogo de 8 variables compuestas (`C01-C08`) para la calibración cruzada (Train/Test).
- **Alcance:** `docs/KTP/AKT.md` como vehículo de transferencia; lectura de solo lectura de `qbe_observatory/data/qbe_historico.db` y del estado Git. **No se modifica código en `src/`, no se altera `KDB.md` ni la Base de Gobierno fuera de KTP.**
- **Régimen:** `[DIRGEN-STRICT]` para documentación, datos y Jueces. Cero datos sintéticos; ausencia declarada como `SIN EVIDENCIA`.
- **Fecha de inicio / cierre:** 2026-11-01 / 2026-11-01.
- **Criterio de asunción:** el Arquitecto entrante debe leer `docs/KTP/KDB.md`, este `AKT.md` y `docs/KTP/KTP_Guide.md`, emitir su Eco de Comprensión y verificar la Sección 5 antes de tocar cualquier archivo.

## 2. HITOS CONCLUIDOS

> **Fail-Loud:** las dos filas ordenadas por la Directiva se registran con su estado real, no como avance simulado. `C01-C08` no tiene ID, Juez ni código; el Daemon no está operando.

| Hito | ID / Juez | Evidencia | Estado |
|---|---|---|---|
| Implementación del Catálogo Compuesto (`C01-C08`) | ID: **SIN ASIGNAR** (próximo libre `[LN-QBE-148]`, no sellado) · Juez: **NO MATERIALIZADO** | No existe `C01`–`C08` en `docs/LOGIC.md`, `docs/ID_REGISTRY.md` ni en `qbe_core/`; la búsqueda en `docs/` y `qbe_core/` no devuelve coincidencias y los únicos matches están en base64 del MHTML de muestra. No hay columnas, tabla ni contrato de las 8 variables. | **NO INICIADO — SIN EVIDENCIA** |
| Migración y Operación del Daemon en Vivo (`Centinela`) | `[VAULT-DAEMON-001]` / `[VAULT-DAEMON-001-B]` · Juez de operación en vivo: **NO EXISTE**; solo paridad de imports | Fuente en `qbe_ingestion/src/ingestion/daemons/centinela_deportivo.py`; no existe `scripts/daemons/`; sin proceso Python visible; sin tarea programada asociada (filtro `qbe`/`centinela`/`daemon`); sin log de operación localizado. | **DETENIDO — NO OPERANDO** |
| Extracción causal minuto a minuto (2015-2016) | `[LN-QBE-141]`–`[LN-QBE-145]` · Jueces: `test_shield_minuto_a_minuto_parser.py`, `test_shield_descubrimiento_ligamx.py`, `test_shield_orquestador_extraccion.py` | **301** partidos con **13,443** eventos en `historical_match_events`; muestra de 49 eventos: América 3-3 Monterrey (`fs_2015_2016_z85264`, J16 Clausura 2016). | **COMPLETADO — COMMIT `299e154`** |
| Derivación de 32 variables causales (9 derivadas / 23 `SIN EVIDENCIA`) | `[LN-QBE-146]` · Juez: `test_shield_derivacion_causal.py` | **301** filas en `historical_match_causal_vars`; `derivadas = 9` en 301/301; `sin_evidencia` con 23 variables. | **COMPLETADO — COMMIT `299e154`** |
| Calibración in-sample 2015-2016 | `[LN-QBE-147]` · Juez: `test_shield_calibracion.py` | 301 partidos; Brier base `0.65546144` → optimizado `0.59896449` (Δ `-0.05649695`; mejora `8.62%`); mercado `0.64031362`; acta `2026-11-01T06:54:38Z` en `data/reportes/calibracion_2015_2016.json`. | **COMPLETADO (IN-SAMPLE) — COMMIT `299e154`** |
| Formalización VÍA B de 8 ayudantes Clase IV | `[LN-QBE-146]`/`[LN-QBE-147]` · Juez de Paridad | 8 etiquetas canónicas en docstrings; `GL_update.md` 0 hallazgos (25 archivos de `qbe_core`); 20/20 Jueces de Paridad y Causalidad. | **COMPLETADO — SIN COMMIT (solo docstrings)** |

## 3. DECISIONES TOMADAS

| Decisión | Razón | Impacto | Anclaje |
|---|---|---|---|
| **D1. No inventar `C01-C08`.** | No existe especificación, ID sellado, Juez ni columnas en la bóveda. Materializarlas por inferencia violaría `[GOVERNANCE-01]` y el régimen `[DIRGEN-STRICT]`. | El catálogo queda como deuda ALTA y Prioridad 2; no se usa en la calibración de este turno. | `docs/KTP/AKT_Pmpt.md` regla 1; `AGENTS.md`; `[LN-QBE-146]`. |
| **D2. No declarar operativo el Daemon.** | No hay proceso, tarea programada, log ni Juez de operación en vivo. La fuente existe, pero la migración/operación no está evidenciada. | El Daemon queda `DETENIDO`; la ingesta en vivo no se considera rescatada. | `[VAULT-DAEMON-001]`; `qbe_ingestion/tests/test_parity_ingestion_daemons.py`. |
| **D3. No presentar el Brier in-sample como Train/Test.** | `[LN-QBE-147]` no implementa partición temporal; el acta usa los 301 partidos completos de 2015-2016. | La mejora de 8.62% mide ajuste in-sample, no capacidad predictiva; el overfitting queda sin dictamen. | `docs/LOGIC.md` §20, limitación declarada de `[LN-QBE-147]`. |
| **D4. No emitir Ficha de Varianza sin fallo documentado.** | No consta intento de rescate del Daemon ni fallo de red/credenciales en este turno. Emitirla sin evidencia sería fabricar un incidente. | No hay `DIRGEN_VARIANCE_REQUEST.md`; solo la plantilla/parte histórico. Si el rescate falla por credenciales, se emite y se enlaza. | `docs/DIRGEN_VARIANCE_REQUEST_TEMPLATE.md`; `AGENTS.md`, Protocolo Anti-Bandazos. |
| **D5. VÍA B para los 8 hallazgos Clase IV.** | El Director autorizó formalizar los nodos sin etiqueta; las etiquetas son docstrings y no alteran la lógica ejecutable. | `GL_update.md` de `qbe_core` queda en 0 hallazgos; el Censo ampliado de `qbe_business` (72 Clase IV) queda como deuda separada. | `docs/GOVERNANCE.md` §3.5; `[LN-QBE-146]`/`[LN-QBE-147]`. |

## 4. DEUDAS ABIERTAS

| Deuda | Severidad | Impacto | Siguiente acción | Responsable |
|---|---|---|---|---|
| **¿Se emitió `DIRGEN_VARIANCE_REQUEST.md` durante este sprint?** | ALTA | **NO — sin enlace.** El archivo no existe; solo están `docs/DIRGEN_VARIANCE_REQUEST_TEMPLATE.md` y el parte histórico resuelto `VAR-2026-J7-HOMOLOGACION` (2026-10-14), ajeno al Sprint 45. No consta fallo de red/credenciales del Daemon. | Si el rescate del Daemon falla por red/credenciales, emitir el parte y enlazarlo aquí antes de tocar código. | Arquitecto |
| Catálogo Compuesto `C01-C08` no materializado | ALTA | No hay 8 variables compuestas (ej. Reacción post-gol), ni ID, ni Juez, ni columnas en la BD; la calibración cruzada no puede ejecutarse sobre ese catálogo. | Definir especificación, asignar ID sellado, crear Juez Inmutable, migrar columnas y poblar 301 partidos. | Director / Arquitecto |
| Daemon en vivo `Centinela` detenido | ALTA | La ingesta en vivo no está rescatada; no hay proceso ni tarea programada. La causa raíz no está diagnosticada. | Diagnosticar red/credenciales/entorno, arrancar el Daemon y dejar log; o emitir Ficha de Varianza. | Arquitecto / Infraestructura |
| Sin split Train/Test | ALTA | El Brier `0.65546144 → 0.59896449` es in-sample; no hay evidencia fuera de muestra ni dictamen de overfitting. | Implementar partición temporal y ejecutar calibración cruzada; si no hay Test, declarar `SIN EVIDENCIA`. | Arquitecto |
| Cobertura histórica incompleta | ALTA | **0** temporadas con 32 variables; solo `2015_2016` con 9 variables y 301/334 partidos. Las otras 11 temporadas no tienen eventos. | Extraer eventos de las 11 temporadas restantes o declarar el alcance de la calibración. | Ingesta / Arquitecto |
| Sonda `auditar_boveda_historica.py` ausente | MEDIA | No existe el instrumento canónico de auditoría de cobertura; la auditoría de §4.1 se hizo con consulta SQL de solo lectura. | Materializar la sonda y su Juez; ejecutarla contra `qbe_historico.db`. | Constructor |
| Censo ampliado de `qbe_business`: 72 hallazgos Clase IV | ALTA | El Censo de Núcleo (`qbe_core`) está en 0; el barrido completo de §3.5 sobre `qbe_business` reporta 72 nodos sin etiqueta, fuera de la VÍA B autorizada. | Abrir VÍA B específica para `qbe_business` o excepción formal del Director. | Arquitecto |

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
- **HEAD:** `299e154` — 2026-11-01 16:52:28 -0600 — `Implementación de pipeline histórico Liga MX y calibración causal`.
- **Working tree:** **SUCIO**. `qbe_core/src/core/sovereign/calibrar_perturbacion.py` y `derivar_variables_causales.py` modificados solo en docstrings (VÍA B); `docs/KTP/GL_update.md` en 0; `docs/GOVERNANCE.md`, `docs/LOGIC.md`, `docs/KTP/KTP_Guide.md`, `docs/KTP/KDB.md` y `docs/KTP/AKT.md` en consolidación. Sin cambios de lógica ejecutable.
- **Juez de gobernanza:** **3/3 PASSED** (`pytest qbe_core/tests/test_shield_ecosystem_governance.py -q --no-header`).
- **Juez KTP:** **5/5 PASSED** (`pytest qbe_core/tests/test_shield_ktp_package_integrity.py -v`).
- **Jueces de Paridad y Causalidad:** **20/20 PASSED** (`pytest qbe_core/tests/test_shield_canonical_parity.py qbe_core/tests/test_shield_derivacion_causal.py -q --no-header`; ejecución sin confinamiento por bloqueo de `tmp_path`/`mode=ro` del sandbox).
- **Suite unificada:** `pytest qbe_core/tests qbe_business/tests qbe_ingestion/tests qbe_observatory/tests qbe_storage/tests -q --no-header` → **249 passed**, 1 warning, **128.39s**, **EXIT CODE 0**.
- **Pre-vuelo de cartelera:** **no aplica** en este turno: solo se modificó `docs/KTP/AKT.md`; no se tocaron motores estocásticos, ingesta ni datos.
- **Bóveda fáctica:** **3,870** partidos; **3,726** con cuotas 1X2 completas; **12 temporadas** (`2015_2016` a `2026_2027`); **301** partidos con eventos (**13,443** eventos); **301** filas en `historical_match_causal_vars`; **0** temporadas con 32 variables completas; **1** temporada con 9 variables (`2015_2016`, 301/334); **217** filas en `historical_team_season_stats`; **0** filas con xG por partido (`xg_home`/`xg_away` no poblados). DB: `qbe_observatory/data/qbe_historico.db`.
- **Censo de Paridad:** **0 hallazgos** en `qbe_core/src/core` (25 archivos); el barrido ampliado de `qbe_business/src` reporta **72 Clase IV** preexistentes, registrados como deuda separada. `GL_update.md` queda en 0 para el Censo de Núcleo ordenado.
- **Sonda de auditoría de la bóveda:** comando canónico previsto:
  ```powershell
  .\.venv\Scripts\python.exe scripts/auditoria/auditar_boveda_historica.py --db qbe_observatory/data/qbe_historico.db
  ```
  Estado: **NO MATERIALIZADO**. El archivo no existe y el comando no se ejecutó. La cobertura de §4.1 se obtuvo con consulta SQL de solo lectura (`PRAGMA query_only=ON`, URI `?immutable=1`) sobre `historical_matches`, `historical_match_events` y `historical_match_causal_vars`.
- **Estado del Daemon en Vivo: DETENIDO.** Sin proceso Python visible, sin tarea programada asociada (filtro `qbe`/`centinela`/`daemon`) y sin log de operación localizado. La causa raíz no está diagnosticada; no se observó fallo de red/credenciales en este turno. No se declara `BLOQUEADO` porque no hay evidencia de credenciales faltantes.
- **Brier Score Train vs. Test:** **NO EJECUTADO.** No existe split Train/Test en `[LN-QBE-147]`; el acta es in-sample. Evidencia in-sample (301 partidos, 2015-2016): Brier base `0.65546144`; optimizado `0.59896449`; Δ `-0.05649695` (mejora `8.62%`); mercado `0.64031362`. **Train:** sin partición formal (se usan los 301 partidos); **Test:** `SIN EVIDENCIA`.
- **Datos no verificados:** (1) `C01-C08`: sin ID, Juez, contrato ni columnas; (2) operación del Daemon y su causa raíz; (3) Brier Test y overfitting; (4) temporadas con 32 variables (0); (5) xG por partido (0 filas); (6) `auditar_boveda_historica.py` (ausente); (7) suite unificada: 249 passed, `EXIT CODE 0`; (8) línea base financiera `+5.85%` / `1.5%` / `$10,000`: declarada por Dirección, no auditada; (9) Censo ampliado de `qbe_business` (72 Clase IV).

## 6. BACKLOG INMEDIATO

| Prioridad | Tarea | Criterio de aceptación |
|---:|---|---|
| 1 | **Estado del Daemon en Vivo:** si no está operando automáticamente, documentar el bloqueo técnico exacto para que el Arquitecto entrante sepa si debe intervenir infraestructura. | Proceso vivo + tarea programada + log de operación, o `DIRGEN_VARIANCE_REQUEST.md` con causa raíz (red/credenciales/entorno) y enlace. |
| 2 | **Validar que las 8 variables `C01-C08` (ej. Reacción post-gol) están correctamente pobladas en la BD.** | Especificación en `LOGIC.md`, ID sellado en `ID_REGISTRY.md`, Juez Inmutable en verde, 8 columnas/tabla y 301 partidos poblados sin nulos no explicados. |
| 3 | **Ejecutar la Calibración Cruzada y reportar si el modelo sufre de Overfitting.** | Split temporal Train/Test (2015-2016 → 2016-2017), Brier Train y Test, Δ y veredicto de overfitting. Prerrequisito: 2016-2017 tiene **0** eventos; sin extracción, el Test no existe y se declara `SIN EVIDENCIA`. |
| 4 | **Abrir VÍA B específica para los 72 hallazgos Clase IV de `qbe_business`.** | Censo ampliado de §3.5 en 0 hallazgos o excepción formal del Director. |

## 7. SIGUIENTE MOVIMIENTO

- **Acción única:** cerrar el Sprint 45 y entregar el relevo al siguiente sprint; el Director asigna nombre y prioridad.
- **Comando / punto de entrada:** `docs/KTP/KDB.md` §10; `docs/KTP/AKT.md` reiniciado.
- **Resultado esperado:** acta archivada, `KDB.md` actualizado, `AKT.md` en `ABIERTO` y deudas vivas en `KDB.md` §10.
- **Riesgo principal:** Daemon detenido, `C01-C08` no materializado, sin Train/Test y 72 hallazgos Clase IV en `qbe_business`.
- **Criterio de aborto:** si el siguiente sprint no está legislado, no inventarlo; mantener el `AKT.md` en `ABIERTO` con sprint pendiente de asignación.

---

> **Firma de transferencia.** Delta emitido por el Constructor Kybern el 2026-11-01. La asunción de mando queda **PENDIENTE** hasta que el Arquitecto entrante emita su Eco de Comprensión, verifique la Sección 5 y confirme que puede operar sin reconstruir el historial. Este AKT no sustituye a `KDB.md`; es el delta del turno.
