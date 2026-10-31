# AKT — REPORTE ACTIVO DE TRANSFERENCIA

**Sprint:** `SPRINT-41-TRANSICION-Y-CONSISTENCIA-BG`<br>
**Fecha:** 2026-10-31<br>
**Autoridad:** Américo García Guerrero (Director Humano)<br>
**Arquitecto saliente:** Agente Constructor Kybern / Arquitecto de Materialización<br>
**Estado:** `PENDIENTE DE ASUNCIÓN DE MANDO (PRUEBA DE FUEGO KTP)`<br>
**Régimen:** `[DIRGEN-STRICT]` — Documentación Institucional y Memoria de Transición<br>
**Nodos de referencia:** `[LN-QBE-138]` / `[ARCH-1.4.74]`

> **Naturaleza de este documento.** Este AKT es un delta de transferencia, no una memoria histórica ni un resumen narrativo. Su destinatario es un Arquitecto entrante con ventana de contexto limpia. Si para asumir el mando necesita reconstruir el chat, este delta falló.

---

## 1. SPRINT ACTUAL

- **Nombre:** `SPRINT-41-TRANSICION-Y-CONSISTENCIA-BG`.
- **Objetivo:** consagrar el **Principio de Identidad Fiduciaria** (Apego al Negocio $\equiv$ Apego a la Base de Gobierno), diseñar la detección determinista de **Reglas Huérfanas** vía AST hacia `docs/KTP/GL_update.md` y preparar la calibración del nuevo modelo sobre las 12 temporadas históricas.
- **Alcance:** `docs/KTP/AKT.md` como vehículo de transferencia; doctrina aplicable a `docs/GOVERNANCE.md`, `docs/LOGIC.md`, `docs/ID_REGISTRY.md` y `scripts/auditoria/`. **No se modifica código de producción en este sprint.**
- **Régimen:** `[DIRGEN-STRICT]` para gobierno, documentación normativa y Jueces. Cero margen creativo sobre constantes, algoritmos o fronteras CQRS.
- **Fecha de inicio / cierre:** 2026-10-31 / 2026-10-31 (delta emitido; la asunción de mando queda pendiente).
- **Criterio de asunción:** el Arquitecto entrante debe leer `docs/KTP/KDB.md`, este `AKT.md` y `docs/KTP/KTP_Guide.md`, emitir su Eco de Comprensión y verificar la Sección 5 con los comandos indicados antes de tocar cualquier archivo.

---

## 2. HITOS CONCLUIDOS

| Hito | Evidencia | Estado |
|---|---|---|
| Monorepo `Q_BE_ECOSYSTEM` materializado en cuatro pilares desacoplados | `qbe_core`, `qbe_business` (`:8000`), `qbe_observatory` (`:8001`), `qbe_ingestion` (`:8002`) + `qbe_storage` transversal; `docs/GOVERNANCE.md` §5 | COMPLETADO |
| Ingesta de 12 temporadas históricas en crudo | `data/raw_footystats/`; 12 filas `OK` en `historical_load_log` (2015_2016 a 2026_2027) | COMPLETADO |
| Corpus oficial de partidos y cuotas 1X2 | `historical_matches`: **3,870** partidos; **3,726** con `odd_home`, `odd_draw` y `odd_away` no nulos | COMPLETADO |
| Carga masiva e idempotente en SQLite 3NF | `qbe_observatory/data/qbe_historico.db`; 12 filas `OK` en `historical_load_log`; 217 filas en `historical_team_season_stats`; Sprint 38 | COMPLETADO |
| Paquete documental KTP con sus **6 artefactos rectores** | `docs/KTP/`: `KTP_Guide.md`, `KDB.md`, `AKT_Pmpt.md`, `AKT.md`, `KDB_Act_Pmpt.md`, `RT_Pmpt.md`; `RT_Pmpt.md` con 3,657 bytes y trackeado; `history/` existente | COMPLETADO |
| Juez de integridad del paquete KTP | `pytest qbe_core/tests/test_shield_ktp_package_integrity.py -v` → **5/5 PASSED** en **0.06s** | COMPLETADO |
| The Shield unificado en verde | `pytest qbe_core/tests qbe_business/tests qbe_ingestion/tests qbe_observatory/tests qbe_storage/tests -q --no-header` → **161 passed / 0 failed**, 1 warning, **47.20s**, **EXIT CODE 0** | COMPLETADO |
| Juez de gobernanza del ecosistema | `pytest qbe_core/tests/test_shield_ecosystem_governance.py -q --no-header` → **3/3 PASSED** en **0.02s** | COMPLETADO |
| Cierre del circuito canónico KTP | Commit `05ca4e4` — `docs(ktp): Materialización de RT_Pmpt.md y cierre de circuito canónico KTP` | COMPLETADO |

> **Cierre de la discrepancia del delta anterior.** El AKT previo registraba `RT_Pmpt.md` vacío y un Juez de **4/4**. El commit `05ca4e4` materializó el sexto artefacto y el Juez amplió su colección a cinco invariantes. La evidencia vigente es **6/6 artefactos con contenido** y **5/5 PASSED**; no queda discrepancia estructural en el paquete.

---

## 3. DECISIONES TOMADAS

| Decisión | Razón | Impacto | Anclaje |
|---|---|---|---|
| **D1. Principio de Identidad Fiduciaria** | Se descarta la auditoría directa contra los PDFs de los Volúmenes I, II y III para evitar gasto de tokens y complejidad innecesaria. La Base de Gobierno es la única fuente operativa. | Se decreta que **Apego al Negocio $\equiv$ Apego Estricto a la Base de Gobierno (`docs/`)**. Todo requerimiento debe estar legislado en `LOGIC.md` y registrado en `ID_REGISTRY.md`. Si no está en la BG, no existe para el sistema. | `docs/GOVERNANCE.md` §1 (regla 1: “La Base de Gobierno manda”); `docs/LOGIC.md`; `docs/ID_REGISTRY.md`; `KTP-03`, `KTP-09`. Formalización expresa pendiente: Deuda 2. |
| **D2. Teorema de Paridad Canónica Biunívoca** | Evitar que código crítico que mueve dinero o probabilidades quede sin trazabilidad legislativa. | Toda función de cálculo de probabilidad, triaje de estrategias o asignación de capital en `src/` debe portar una etiqueta canónica `[LN-QBE-XXX]`, respaldada por un Juez Inmutable en The Shield. Sin etiqueta o con ID inexistente, la función es infractora. | `docs/GOVERNANCE.md` §3.1 (`KTP-04`, `KTP-07`) y §7 (custodia de IDs); Juez futuro `test_shield_canonical_parity.py` (aún no materializado). **No se asigna ID nuevo en este delta**: el sellado corresponde a la custodia. |
| **D3. Clasificación binaria de infracciones** | Distinguir el código que elude la ley de la ley que no tiene materialización; ambas rompen la paridad, pero exigen acciones distintas. | **Regla Huérfana (Código Furtivo):** código en `src/` que afecta dinero o probabilidades sin etiqueta o con ID inexistente en la BG; el auditor la volcará automáticamente a `docs/KTP/GL_update.md`. **Brecha Legislativa (Letra Muerta):** nodo en `LOGIC.md` sin código o sin test asociado. | `docs/LOGIC.md`; `docs/ID_REGISTRY.md`; `KTP-03` (ley antes que código) y `KTP-04` (Juez en RED). |
| **D4. Automatización 0-Tokens (`GL_update.md`)** | La auditoría manual de paridad consume tokens y es no determinista; el cierre de sprint exige evidencia reproducible en tiempo acotado. | Crear `scripts/auditoria/auditar_paridad_bg.py`: script Python determinista que escanea el código vía AST, corre en ~0.5s y genera la bandeja `docs/KTP/GL_update.md` para que el Director apruebe o elimine reglas huérfanas. No usa LLM, no modifica `src/`, no decide: solo detecta y propone. | Deuda 1; `KTP-07` (evidencia reproducible); `KTP-10` (cierre y reversibilidad). |
| **D5. Captura de reglas conversacionales** | Las decisiones tomadas en chat se pierden si no se capturan antes de cerrar el turno; el delta debe poder absorberlas sin depender del historial. | Enmendar `AKT_Pmpt.md` para incluir una sección obligatoria de captura de decisiones de chat antes de que se pierdan en el historial. La enmienda es de plantilla, no de este delta: **no se modificó `AKT_Pmpt.md` en este sprint** porque la jurisdicción solo autoriza `AKT.md`. Queda como deuda metodológica del siguiente ciclo. | `docs/KTP/AKT_Pmpt.md` (plantilla vigente de 7 puntos); `[LN-QBE-138]` / `[ARCH-1.4.74]`. |

### 3.1 Consecuencia operativa de la doctrina

La ecuación rectora del sprint es:

$$\text{Apego al Negocio} \equiv \text{Apego Estricto a la Base de Gobierno }(docs/)$$

De ella se derivan tres consecuencias que el Arquitecto entrante debe aplicar sin reinterpretar:

1. **La BG es el contrato, no la documentación de apoyo.** Un PDF, una nota de chat o una memoria verbal no legislan. Si un requerimiento no está en `LOGIC.md` con su ID en `ID_REGISTRY.md`, el sistema no lo reconoce y el código que lo implemente es sospechoso de fuga.
2. **La paridad es biunívoca.** No basta con que el código tenga etiqueta: la etiqueta debe existir en la BG. No basta con que la ley exista: debe tener materialización y Juez. Cualquier lado sin el otro es una infracción binaria, no una “deuda cosmética”.
3. **La detección debe ser determinista y barata.** El script de paridad es un instrumento de cierre, no un motor generativo. Su salida es una bandeja de revisión humana; la aprobación o eliminación de una regla huérfana es potestad del Director.

### 3.2 Frontera de la decisión

Estas decisiones **no autorizan** a etiquetar código existente de forma masiva, ni a inventar IDs para “cerrar” la paridad, ni a modificar `GOVERNANCE.md`, `LOGIC.md` o `ID_REGISTRY.md` en este sprint. La única materialización autorizada es este `AKT.md`. Cualquier etiquetado o enmienda normativa pertenece al Sprint de Consistencia de la Base de Gobierno y exige su propio Juez.

---

## 4. DEUDAS ABIERTAS

| Deuda | Severidad | Impacto | Siguiente acción | Responsable |
|---|---|---|---|---|
| **Deuda 1 — Script de paridad y bandeja `GL_update.md` ausentes** | ALTA | Sin `auditar_paridad_bg.py` no hay detección reproducible de Reglas Huérfanas ni evidencia de paridad al cierre. El Teorema de Paridad Canónica queda como doctrina sin instrumento. El directorio `scripts/auditoria/` aún no existe. | Materializar `scripts/auditoria/auditar_paridad_bg.py` y el generador de `docs/KTP/GL_update.md`; crear `test_shield_canonical_parity.py`; ejecutar el primer escaneo. | Constructor / Arquitecto |
| **Deuda 2 — Principio de Identidad Fiduciaria no formalizado en `GOVERNANCE.md`** | MEDIA | La doctrina existe en este delta, pero no está legislada en el libro de gobierno; un Arquitecto entrante podría no encontrarla si solo lee `GOVERNANCE.md`. | Añadir el artículo del Principio de Identidad Fiduciaria y el Teorema de Paridad Canónica a `docs/GOVERNANCE.md`, con su Juez de gobernanza actualizado. | Arquitecto |
| **Deuda 3 — Tres scripts de laboratorio con imports legados** | BAJA | Los scripts no arrancan bajo la topología actual: importan `src.core...` / `src.storage...`, rutas del monolito derogado. No afectan producción ni The Shield, pero rompen la reproducibilidad del laboratorio. | Reconectar `scripts/laboratorio/sandbox_h2h_pipeline.py`, `scripts/laboratorio/sandbox_volumen_porteria_pipeline.py` y `scripts/investigacion/manus_qbe_model.py` a `qbe_core` / `qbe_storage`; smoke test de importación y `--help`. | Constructor |

> **Nota de ubicación (corrección fáctica):** el expediente ubica estos tres scripts en `qbe_observatory/scripts/`. La inspección real los encuentra en `scripts/laboratorio/` y `scripts/investigacion/`; `qbe_observatory/scripts/` solo contiene `refresh_snapshot.py` e `__init__.py`. Se conserva la deuda, se corrige la ruta.

> **Regla de este delta:** no se listan deudas cerradas. Lo que ya se cerró vive en `history/` o en el commit, no aquí.

---

## 5. ESTADO FÁCTICO GIT / SHIELD

- **Branch:** `feature/fase2-observatory`.
- **HEAD de inspección:** `05ca4e4` — 2026-10-31 10:58:25 -0600 — `docs(ktp): Materialización de RT_Pmpt.md y cierre de circuito canónico KTP`. Es el padre del commit de este delta.
- **Working tree (pre-commit):** limpio; `git status --short` no devuelve entradas. El único cambio de este delta será `docs/KTP/AKT.md`.
- **Juez de gobernanza:** **3/3 PASSED** en 0.02s (`pytest qbe_core/tests/test_shield_ecosystem_governance.py -q --no-header`).
- **Juez KTP:** **5/5 PASSED** en 0.06s (`pytest qbe_core/tests/test_shield_ktp_package_integrity.py -v`). Los cinco invariantes cubren estructura séxtuple, KDB, topología, estado fáctico del AKT y `RT_Pmpt.md`.
- **Suite unificada:** `pytest qbe_core/tests qbe_business/tests qbe_ingestion/tests qbe_observatory/tests qbe_storage/tests -q --no-header` → **161 passed / 0 failed**, 1 warning, **47.20s**, **EXIT CODE 0**. Warning: `StarletteDeprecationWarning` por `httpx` en `fastapi/testclient.py`; no afecta el resultado.
- **Pre-vuelo de cartelera:** **no aplica** en este delta: no se modificaron motores estocásticos, ingesta ni datos. No se ejecutó `coherence_auditor --check`.
- **Bóveda fáctica:** **3,870** partidos en `qbe_observatory/data/qbe_historico.db`; **3,726** con cuotas 1X2 completas; **12** temporadas con estado `OK` en `historical_load_log` (2015_2016 a 2026_2027); **217** filas en `historical_team_season_stats`.
- **Línea base financiera (declarada por Dirección, no auditada):** ROI **+5.85%**; Drawdown **1.5%**; Bankroll inicial **$10,000**. Se consigna con provenance, no como resultado empírico. Cualquier presentación pública debe citar esta condición.
- **Datos no verificados / discrepancias de evidencia:**
  1. **Línea base financiera:** declarada por Dirección, sin acta reproducible; no auditada por el Constructor.
  2. **Cobertura xG:** no verificada en este delta. La calibración multianual deberá declararla `SIN EVIDENCIA` si no existe cobertura suficiente.
  3. **`GL_update.md`:** no existe todavía porque el auditor de paridad aún no ha sido materializado (Deuda 1). No se presenta como artefacto entregado.
  4. **Auditoría de PDFs:** no realizada por decisión D1; la BG es la única fuente operativa.
- **Estado del repositorio para transferencia:** el paquete `docs/KTP/` está completo (6/6 artefactos con contenido), el Juez KTP está en **5/5** y el árbol queda limpio antes de este delta. El residuo `RT_Pmpt.md` del turno anterior quedó cerrado y trackeado en `05ca4e4`.

---

## 6. BACKLOG INMEDIATO

| Prioridad | Tarea | Criterio de aceptación |
| ---: | --- | --- |
| 1 | Enmendar `docs/GOVERNANCE.md` con el Principio de Identidad Fiduciaria y el Teorema de Paridad Canónica. | Artículo normativo publicado; Juez de gobernanza actualizado y en verde; sin IDs inventados. |
| 2 | Construir `scripts/auditoria/auditar_paridad_bg.py` y crear el Juez `test_shield_canonical_parity.py`. | El script escanea AST, detecta etiquetas `[LN-QBE-XXX]` y IDs inexistentes, y el Juez falla en RED antes de la materialización y pasa en GREEN después. |
| 3 | Ejecutar el primer escaneo de paridad para generar `docs/KTP/GL_update.md`. | Bandeja generada en ~0.5s, con reglas huérfanas y brechas legislativas clasificadas; consumo de tokens = 0. |
| 4 | Iniciar la calibración multianual del modelo Q-BE sobre los 3,870 partidos de `qbe_historico.db`. | Acta de calibración con corte temporal, Brier Score, baseline de mercado y curvas por temporada; xG declarado `SIN EVIDENCIA` si no hay cobertura. |

---

## 7. SIGUIENTE MOVIMIENTO

- **Acción única:** ejecutar el **Sprint de Consistencia de la Base de Gobierno**: crear `scripts/auditoria/auditar_paridad_bg.py`, materializar el Juez de Paridad Canónica en The Shield, enmendar `GOVERNANCE.md` y emitir el primer `docs/KTP/GL_update.md`.
- **Comando / punto de entrada:** `scripts/auditoria/auditar_paridad_bg.py` (a crear; aún no existe).
- **Resultado esperado:** detección de Reglas Huérfanas y Brechas Legislativas en ~0.5s, con **cero gasto de tokens**, bandeja `GL_update.md` generada y paridad certificada por un Juez Inmutable.
- **Riesgo principal:** que el análisis AST confunda llamadas dinámicas, alias, decoradores o etiquetas embebidas en strings con funciones reales, produciendo falsos positivos o falsos negativos. El script debe declarar su alcance, usar allowlist explícita y no “corregir” código.
- **Criterio de aborto:** si el AST no puede resolver una llamada crítica sin ambigüedad, o si el Juez de paridad y la BG discrepan sobre qué es una función crítica, **detener** y emitir `DIRGEN_VARIANCE_REQUEST.md` con coordenadas, evidencia, diagnóstico causal, alternativas y recomendación. No se parchea a ciegas bajo `[DIRGEN-STRICT]`.
- **Definición de terminado:** script + Juez + artículo en `GOVERNANCE.md` + primer `GL_update.md` + The Shield completo en **EXIT CODE 0**.

---

> **Firma de transferencia.** Delta emitido por el Agente Constructor Kybern el 2026-10-31. La asunción de mando queda **PENDIENTE** hasta que el Arquitecto entrante emita su Eco de Comprensión, verifique la Sección 5 y confirme que puede operar sin reconstruir el historial. Este AKT no sustituye a `KDB.md`; es el delta del turno.
