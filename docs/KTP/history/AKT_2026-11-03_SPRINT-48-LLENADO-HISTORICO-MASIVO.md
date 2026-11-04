# AKT — REPORTE ACTIVO DE TRANSFERENCIA

**Sprint:** `SPRINT-46-WISDOM-OF-THE-CROWDS-Y-RESCATE-CENTINELA`<br>
**Fecha:** 2026-11-02<br>
**Autoridad:** Américo García Guerrero (Director Humano)<br>
**Arquitecto saliente:** Constructor Kybern / Cierre Sprint 46<br>
**Estado:** `CERRADO`<br>
**Régimen:** `[DIRGEN-STRICT]` — documentación de transferencia; jurisdicción exclusiva `docs/KTP/AKT.md`<br>
**Nodos:** `[LN-QBE-148]` / `[LN-QBE-149]` / `[ARCH-1.5.13]` / `[ARCH-1.5.14]` / `[ARCH-1.4.75]` / `[DES-QBE-077]`

> **Nota de cierre.** El Sprint 46 materializó el consenso ponderado vig-free, el radar de sindicatos, `odds_ticks` y el rescate de los centinelas de Momios y FotMob. La bóveda quedó consolidada en `data/qbe_database.db` sin fallback legacy. Deudas vivas en §4 y en `docs/KTP/KDB.md` §10.
>
> **Bóveda histórica:** 3,870 partidos y 12 temporadas en `qbe_historico.db`; sobre ese corpus se materializa la distribución soberana P' histórica en `historical_sovereign_distributions` (`[LN-QBE-150]` / `[ARCH-1.5.1]` §15.5).

## 1. SPRINT ACTUAL

- **Nombre:** `SPRINT-46-WISDOM-OF-THE-CROWDS-Y-RESCATE-CENTINELA`.
- **Objetivo:** activar el Motor de Consenso Ponderado (`[LN-QBE-148]`), el Radar de Sindicatos (`[LN-QBE-149]`) y la persistencia de `odds_ticks` (`[ARCH-1.5.13]`), rescatando los centinelas de Momios (`[ARCH-1.4.75]`) y FotMob (`[ARCH-1.4.59]`).
- **Alcance:** `qbe_core`, `qbe_ingestion`, `qbe_storage`, `qbe_observatory`, `tests/shield/`, `scripts/` y `docs/`.
- **Régimen:** `[DIRGEN-STRICT]` con migración autorizada.
- **Fecha de inicio / cierre:** 2026-11-01 / 2026-11-02.
- **Criterio de asunción:** leer `docs/KTP/KDB.md`, este `AKT.md` y `docs/KTP/KTP_Guide.md`; verificar §5 antes de tocar cualquier archivo.

## 2. HITOS CONCLUIDOS

| Hito | Evidencia | Estado |
|---|---|---|
| Consenso Ponderado `[LN-QBE-148]` | `qbe_core/src/core/consensus.py`; Juez `tests/shield/test_shield_odds_ticks_y_consenso.py` (3/3) | CERRADO |
| Radar de Sindicatos `[LN-QBE-149]` | `qbe_core/src/core/radar_sindicatos.py`; Juez `tests/shield/test_shield_radar_sindicatos.py` (3/3) | CERRADO |
| `odds_ticks` `[ARCH-1.5.13]` | `qbe_storage/src/storage/odds_ticks.py`; tabla canónica con 124 ticks históricos | CERRADO |
| Consolidador `[ARCH-1.5.14]` | `scripts/auditoria/consolidar_bovedas_legacy.py`: 124 momios + 5,418 variables de 32 dimensiones en 301 partidos | CERRADO |
| Bóveda única | `qbe_ingestion/src/ingestion/service.py`: fallback legacy eliminado; `DATABASE_URL` absoluto a `data/qbe_database.db` | CERRADO |
| Extracción Momios | Caliente `/es_MX/Futbol` 9/9; Novibet 9/9; Betway `INFO` sin eventos; fail-loud `OperadorExtraccionError` | CERRADO |
| FotMob 32V | `tests/shield/test_shield_fotmob_32_vars.py` (6/6); sonda `scripts/auditoria/auditar_fotmob_vivo.py` (24 con dato / 8 fuera de fuente) | CERRADO |
| Orquestador live | `scripts/daemons/orquestador_live.py`: multicasa + macro + `observatory_snapshot.db` (153 filas, fresco, EXIT 0) | CERRADO |
| Paridad canónica | `auditar_paridad_bg.py qbe_core/src/core`: 27 archivos, **0 hallazgos** | CERRADO |

## 3. DECISIONES TOMADAS

| Decisión | Razón | Impacto | Anclaje |
|---|---|---|---|
| Bóveda canónica absoluta y sin fallback legacy | La doble SQLite congelaba la jornada y descartaba el slate vivo | El servicio y los daemons resuelven la misma `data/qbe_database.db` | `[ARCH-1.5.14]` / `service.py` |
| Fail-loud por operador | Un scraper vacío se persistía como cero silencioso | `OperadorExtraccionError` detiene la cadena y exige corrección | `[ARCH-1.4.75]` |
| Preservación de la capa de mercado | `centinela_deportivo` borraba `momios_operadores` y `consenso_mercado` | El refresh de deportivo conserva el último estado válido | `[ARCH-1.5.14]` |
| Umbral de obsolescencia 30 min | El badge existía con 60 min | `Fresco` ≤ 30 min; `Obsoleto` > 30 min en backtesting y visor | `[DES-QBE-077]` |
| Alias operativos en el normalizador | `ALIAS_LIGAMX` es corpus-puro 2015-2016 y su Juez lo exige | `club necaxa` y `atletico san luis` resuelven en el scraper sin romper el Juez histórico | `[LN-QBE-145]` / `[LN-QBE-012]` |

## 4. DEUDAS ABIERTAS

| Deuda | Severidad | Impacto | Siguiente acción | Responsable |
|---|---|---|---|---|
| Cableado del daemon de mercado a `odds_ticks` en vivo | MEDIA | Hoy persiste `fixtures_snapshots.matches_json`; la tabla tiene 124 ticks históricos consolidados | Insertar tick por operador en `actualizar_cuotas_en_sqlite` | Constructor |
| Tabla comparativa `[DES-QBE-076]` | BAJA | Sigue `EN FORJA`; no hay UI de Sabiduría de las Masas | Materializar en el Visor del Observatorio | Constructor |
| Betway sin eventos Liga MX | BAJA | 0/9 en la última pasada; la ruta responde 200 sin cartelera | Reintentar en ventana de publicación o fuente alternativa | Operación |
| 8 variables fuera de FotMob | DECLARADA | V16 y V26–V32 se resuelven con corpus propio/contexto | Mantener la declaración `fuera_de_fuente` | Arquitecto |
| 72 Clase IV en `qbe_business` | MEDIA | Deuda de paridad preexistente | Censo ampliado o excepción formal | Director / Constructor |
| Programación automática del orquestador | MEDIA | El script existe y corre manual; no hay cron/Task Scheduler registrado | Instalar disparo cada 30 min | Operación |

> Las deudas vivas se gobiernan en `docs/KTP/KDB.md` §10. No se duplican aquí.

## 4.1 CIERRE `SPRINT-48` — CORPUS HISTÓRICO MASIVO P'

**Expediente:** `SPRINT-48-LLENADO-HISTORICO-MASIVO`. **Estado:** `CERRADO`. **Fecha:** 2026-11-03.

- **Nodos:** `[LN-QBE-146]` §19.1 (fuente alterna `matchDetails`) y `[LN-QBE-150]` (Motor de Cálculo de Distribuciones Históricas P'), esquema en `[ARCH-1.5.1]` §15.5.
- **Entregables:** `scripts/auditoria/extraer_historico_fotmob.py` (extracción masiva con cadencia anti-WAF de `1.0 s`, acta de faltantes y trazabilidad de procedencia), `scripts/auditoria/calcular_distribuciones_historicas.py` (transporte de evidencia pre-kickoff y delegación en `qbe_core`), y `tests/shield/test_shield_extraccion_historica_fotmob.py` + `test_shield_distribuciones_historicas.py` (19 jueces).
- **Resultado:** **2,737** distribuciones P' en `historical_sovereign_distributions` — **2,461** con vector `FOTMOB_MATCHDETAILS` y **276** con vector `LIGAMX_MXM`; **2,699** vectores FotMob materializados sobre **3,181** fixtures emparejados. Cobertura del corpus: **70.7 %** (2,737 / 3,870 partidos) en **10 de 12** temporadas.
- **Costo de red:** una petición por partido a cadencia fija de `1.0 s`; cero bloqueos del WAF; `PRAGMA quick_check = ok` y `foreign_key_check` sin violaciones al cierre de cada lote.
- **Hueco asumido (2016-2018):** `2016_2017` y `2017_2018` quedan en **0 filas** (668 partidos) porque FotMob no publica bloque estadístico antes de 2018/19 y ligamx.net fue descartado como fuente causal. Declarado, no imputado.
- **Cold start asumido:** 263 descartes `SI_insuficiente` (≈8 %), siempre en J1–J3 del Apertura; aprobado por Dirección.
- **Defecto corregido:** `fuente_causal` se escribía como constante; ahora se hereda de `historical_match_causal_vars.fuente_datos`. Las 276 filas de `2015_2016` se re-etiquetaron a `LIGAMX_MXM` (coincidencia destino↔vector: **2,737 / 2,737**).
- **Pendiente declarado:** el Alpha masivo (`[LN-QBE-148]` Φ) queda habilitado por datos pero no ejecutado en este sprint.

## 5. ESTADO FÁCTICO GIT / SHIELD

- **Branch:** `feature/fase2-observatory`.
- **HEAD:** `299e154` — 2026-11-01 16:52:28 -0600.
- **Working tree:** cambios del Sprint 46 pendientes de commit; sin secretos.
- **The Shield Sprint-46:** **20/20 PASSED**, **EXIT CODE 0**.
- **Suites de regresión:** `qbe_core` **104 passed**; `qbe_ingestion` **72 passed**; `qbe_storage` **3 passed**; `qbe_observatory` **58 passed**.
- **Censo de Paridad:** **0 hallazgos** en `qbe_core/src/core` (27 archivos); 72 Clase IV preexistentes en `qbe_business/src`.
- **Bóveda canónica:** 17 snapshots, 153 partidos, **124** filas en `odds_ticks`, **301** filas en `match_causal_vars`, **5,418** variables de 32 dimensiones con dato. J16: Caliente 9/9, Novibet 9/9, Betway 0/9; snapshot `observatory_snapshot.db` con 153 filas y fresco.
- **Sonda FotMob:** partido Atlético San Luis vs FC Juárez (J16); **24/32** variables con dato, **0** sin evidencia, **8** fuera de fuente declaradas; 18 equipos, 0 errores.
- **Datos no verificados:** split Train/Test; xG por partido; `auditar_boveda_historica.py`; línea base financiera declarada.

## 6. BACKLOG INMEDIATO

| Prioridad | Tarea | Criterio de aceptación |
|---:|---|---|
| 1 | Cablear `odds_ticks` al daemon de mercado | Cada tick de operador insertado con `vig` y `delta_odd`; Juez de persistencia |
| 2 | Materializar `[DES-QBE-076]` | Tabla comparativa con Brier, Alpha y peso en consenso |
| 3 | Programar `orquestador_live.py` cada 30 min | Snapshot siempre ≤ 30 min o badge `Obsoleto` visible |
| 4 | Resolver 72 Clase IV de `qbe_business` | 0 hallazgos o excepción formal |

## 7. SIGUIENTE MOVIMIENTO

- **Acción única:** archivar este `AKT.md` en `docs/KTP/history/` y asignar el siguiente sprint.
- **Comando / punto de entrada:** `docs/KTP/KDB.md` §10.
- **Resultado esperado:** sprint nombrado, objetivo legislado y `AKT.md` reiniciado.
- **Riesgo principal:** deuda de cableado de `odds_ticks` y programación del orquestador.
- **Criterio de aborto:** si no hay orden, mantener el activo `CERRADO`; no fabricar alcance.

---

> **Firma de transferencia.** Sprint 46 cerrado por el Constructor Kybern el 2026-11-02. La asunción de mando queda **PENDIENTE** hasta que el Director asigne el siguiente sprint.
