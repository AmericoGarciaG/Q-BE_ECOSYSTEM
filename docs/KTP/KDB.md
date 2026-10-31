# Q-BE ECOSYSTEM — BASE DE CONOCIMIENTO DEL PROYECTO (KDB)

**Documento:** `KDB.md` — Single Pane of Glass  
**Versión:** 1.0.0  
**Estado:** `[ALGO-PROTECTED]` — Conocimiento Estable Certificado  
**Proyecto:** `Q_BE_ECOSYSTEM`  
**Autoridad Suprema:** Américo García Guerrero (Director Humano)  
**Marco:** Kybern Industrial Framework v13.5 (DirGen Operational Edition)  
**Expediente:** `SPRINT-MATERIALIZACION-PAQUETE-KTP-DOCS-39`  
**Nodos:** `[LN-QBE-138]` / `[ARCH-1.4.74]`  
**Juez:** `qbe_core/tests/test_shield_ktp_package_integrity.py`  
**Última consolidación:** 2026-10-30  
**Fuente de la consolidación:** `docs/KTP/AKT.md` (Sprint 38)

---

## 0. CÓMO LEER ESTE DOCUMENTO

Este es el conocimiento estable del ecosistema. No es un diario de cambios ni un historial de conversaciones. Responde cinco preguntas:

1. **¿Quién manda?** Autoridad, mandato y axioma.
2. **¿Cómo está construido?** Topología de pilares, puertos y fronteras CQRS.
3. **¿Qué no se puede violar?** Los 11 invariantes constitucionales.
4. **¿Qué evidencia existe?** Catálogo de variables y bóveda fáctica.
5. **¿Dónde se toca cada cosa?** Mapa de intervención y Jueces asociados.

La capa dinámica —sprint, hitos, deudas y siguiente movimiento— vive en `AKT.md`. El histórico vive en `history/`. Si una cifra no tiene evidencia en este documento, se declara `SIN EVIDENCIA`; no se completa por inferencia.

---

## 1. IDENTIDAD, PROPÓSITO Y MANDATO

### 1.1 Autoridad Suprema

| Campo | Valor |
|---|---|
| **Autoridad Suprema** | **Américo García Guerrero** |
| **Rol** | **Director Humano** |
| **Marco de gobierno** | Kybern Industrial Framework v13.5 — DirGen Operational Edition |
| **Registro canónico** | `docs/ID_REGISTRY.md` |
| **Libros de gobierno** | `docs/GOVERNANCE.md`, `docs/LOGIC.md`, `docs/ARCH.md`, `docs/CONSTANTS.md`, `docs/DESIGN.md`, `docs/DIRGEN_VAULT.md` |
| **Juez de gobernanza** | `qbe_core/tests/test_shield_ecosystem_governance.py` |

El Director Humano es la autoridad suprema del ecosistema. Ratifica la doctrina, los IDs, las varianzas, la línea base financiera y el cierre. No opera el motor ni sustituye al Juez.

### 1.2 Mandato

`Q_BE_ECOSYSTEM` es un sistema de análisis y decisión deportiva con arquitectura de cuatro pilares procesales y un sustrato transversal de persistencia. Su propósito es transformar evidencia fáctica en distribuciones de probabilidad soberanas, decisiones de cartera gobernadas y trazabilidad auditable, sin datos sintéticos y sin acoplamiento CQRS.

### 1.3 Axioma de Soberanía Estocástica

> **El código es fungible; la intención legislada es permanente. La distribución soberana del modelo no se sustituye por el mercado observado. El mercado es una señal, no la ley.**

Este es el **Axioma de Dos Mundos**: el mundo del mercado —observado, imperfecto y con margen comercial— y el mundo del modelo —soberano, calibrado y expresado en el **Símplex Δ²**—. La convivencia se gobierna por contratos, no por imputación.

**Soberanía Estocástica** implica:

1. `qbe_core` calcula; no lee bases, no llama APIs y no depende de reloj, red o disco.
2. El mercado no reemplaza la probabilidad del modelo; se compara contra ella.
3. La ausencia de evidencia se declara, no se rellena.
4. Toda decisión financiera nace de una distribución y de un contrato, no de una corazonada.

---

## 2. TOPOLOGÍA DEL ECOSISTEMA

### 2.1 Cuatro pilares procesales + sustrato transversal

| Pilar | Puerto | Régimen | Responsabilidad | Prohibición estructural |
|---|---:|---|---|---|
| `qbe_core` | — | `[DIRGEN-STRICT]` | Matemática pura, contratos, catálogos inmutables, morfología, cartera y triaje. | No importa FastAPI, SQLAlchemy, scrapers, red, disco ni bases de datos. |
| `qbe_business` | **8000** | OLTP | Mesa de Apuestas, cartera, routers transaccionales y SPA. | No lee el histórico OLAP ni ejecuta backtesting. |
| `qbe_observatory` | **8001** | OLAP | Visor de calibración, backtesting, cards semánticos y Jinja2. | No escribe sobre la base viva; solo lectura del snapshot. |
| `qbe_ingestion` | **8002** | Data Nexus | Scrapers, proveedores, daemons y normalización fáctica. | No publica UI ni decide precios o carteras. |
| `qbe_storage` | — | Sustrato | Gateway de persistencia, modelos 3NF, WAL, backup y snapshot atómico. | **No es un quinto pilar.** Ningún pilar abre sesión directa contra la base viva. |

### 2.2 Fronteras CQRS

- **Comando (OLTP):** `qbe_business` recibe la intención, valida el contrato, ejecuta la cartera y persiste a través de `qbe_storage`.
- **Consulta (OLAP):** `qbe_observatory` consume `data/snapshots/qbe_database_snapshot.db` en modo solo lectura (`mode=ro`, `PRAGMA query_only=ON`).
- **Único contrato entre OLTP y OLAP:** el snapshot atómico. El Observatorio nunca lee la base viva.
- **Ingesta:** escribe únicamente a través del gateway; no publica UI ni decide precios.
- **Núcleo:** `qbe_core` no conoce ninguna base de datos.

### 2.3 Rutas y artefactos críticos

| Artefacto | Ruta | Régimen |
|---|---|---|
| Base viva OLTP | `data/qbe_database.db` | Escritura gobernada por gateway. |
| Snapshot OLAP | `data/snapshots/qbe_database_snapshot.db` | Solo lectura. |
| Bóveda histórica | `qbe_observatory/data/qbe_historico.db` | OLAP histórico; lectura para calibración. |
| Gateway | `qbe_storage/src/storage/gateway.py` | Persistencia transversal. |
| Núcleo matemático | `qbe_core/src/core/` | `[DIRGEN-STRICT]`, cero I/O. |

---

## 3. LOS 11 INVARIANTES CONSTITUCIONALES

| # | Invariante | Regla canónica | Nodo rector |
|---:|---|---|---|
| 1 | **Soberanía Estocástica** | El modelo no se sustituye por el mercado. `qbe_core` es puro; el mercado es señal, no ley. | `[VAULT-CORE-004]` / `[LN-QBE-059]` |
| 2 | **Morfología Γ** | `Γ ∈ {0.67, 0.70, 0.75}`. `0.67` es el umbral del motor; `0.70` y `0.75` son modos de UI. | `[LN-QBE-059]` |
| 3 | **Dutching** | `V=0` en modo defensivo exacto; `V=δ` con cobertura activa; `δ ≥ 0`. Prohibido anular la ganancia del favorito. | `[LN-QBE-077-B]` |
| 4 | **Hard-caps** | `0.0800` (8%) por partido; `0.2500` (25%) por cartera. Inviolables. | `[LN-QBE-070-B]` |
| 5 | **Ley 3 del Underdog** | `0.0150` (1.5%) es techo exclusivo de `QBE-R1`/`QBE-R2`, no piso y no sustituto del hard-cap individual. | `[LN-QBE-115]` |
| 6 | **Escudo de Altitud** | Veto de la híbrida visitante cuando `ΔAlt ≥ 1000 m`. `UMBRAL_VETO_ALTITUD_METROS = 1000.0`. | `[LN-QBE-115]` |
| 7 | **Banda de Indiferencia** | `0.0100` (1.0%) de tolerancia ordinal; desempate por altitud del anfitrión. | `[LN-QBE-124]` |
| 8 | **Désiré André +PA** | Fórmula cerrada para ventaja `+2`; partición de capital con cobertura activa `V=δ`. | `[LN-QBE-077]` |
| 9 | **α y Damping** | `κ_net = 0.25` como techo de compresión `tanh`; `σ_liga` vestigial. Prohibido confundir con `κ_decay`. | `[VAULT-CORE-001]` |
| 10 | **Cero Mocks** | `[GOVERNANCE-01]`: dato ausente = `SIN EVIDENCIA`, cuarentena o veto. Nunca cero sintético. | `docs/GOVERNANCE.md` |
| 11 | **Abstracción** | `[GOVERNANCE-02]`: prohibido hardcodear clubes, fechas o partidos. Los fixtures son instancias de una ley general. | `docs/GOVERNANCE.md` |

### 3.1 Notas de no-contaminación

1. `0.08` MXN es la tolerancia bancaria de indemnidad (`Tol_tablas`), no un hard-cap.
2. `0.0800` es el hard-cap individual; `0.2500` es el hard-cap de cartera.
3. `0.0150` es la cota de la Ley 3; no es un drawdown ni un hard-cap general.
4. `1000.0` m es el umbral de veto de altitud; `1000.0` m también se usa para el rescate ordinal, pero son predicados distintos.
5. `0.0100` es la banda de indiferencia ordinal; no es un umbral de descarte.
6. `V=0` y `V=δ` son regímenes de cobertura; no son intercambiables.

---

## 4. CATÁLOGO DE 32 VARIABLES DE PREDICCIÓN

### 4.1 Las seis dimensiones canónicas

| Dimensión | Variables | N | Propósito |
|---|---|---:|---|
| `𝒯_Vol` — Volumen Territorial y Fricción | `V01`–`V05` | 5 | Posesión, toques en área, pases y faltas. |
| `𝒯_Rem` — Calidad de Remate | `V06`–`V11` | 6 | xG, SoT, big chances, xGOT y xA. |
| `𝒯_Def` — Resistencia Defensiva | `V12`–`V16` | 5 | xGA, SoTA, acciones defensivas, intercepciones y big chances concedidas. |
| `𝒯_Por` — Rendimiento de Portería | `V17`–`V20` | 4 | Goles evitados, save %, salidas y clean sheets. |
| `𝒯_Spc` — Balón Parado y Disciplina | `V21`–`V25` | 5 | Pelota parada, córners, penales y tarjetas. |
| `𝒯_Ctx` — Memoria, Forma y Contexto | `V26`–`V32` | 7 | H2H, sede, altitud, descanso, forma y ΔxPTS. |

### 4.2 Tabla canónica

| ID | Variable | Dimensión | Fuente | Espacio |
|---|---|---|---|---|
| `V01` | Posesión promedio (%) | `𝒯_Vol` | OPTA | `H_att` |
| `V02` | Toques en área rival | `𝒯_Vol` | OPTA | `H_att` |
| `V03` | Pases precisos | `𝒯_Vol` | OPTA | `H_att` |
| `V04` | Pases largos precisos | `𝒯_Vol` | OPTA | `H_att` |
| `V05` | Faltas cometidas | `𝒯_Vol` | OPTA | `H_att` |
| `V06` | xG por partido (ancla npxG) | `𝒯_Rem` | OPTA | `H_att` |
| `V07` | Tiros al arco por partido (SoT) | `𝒯_Rem` | OPTA | `H_att` |
| `V08` | Big chances creadas | `𝒯_Rem` | OPTA | `H_att` |
| `V09` | Big chances falladas | `𝒯_Rem` | OPTA | `H_att` |
| `V10` | xGOT de plantilla | `𝒯_Rem` | OPTA | `H_att` |
| `V11` | xA de plantilla | `𝒯_Rem` | OPTA | `H_att` |
| `V12` | xGA por partido (ancla defensiva) | `𝒯_Def` | OPTA | `H_def` |
| `V13` | Tiros al arco recibidos (SoTA) | `𝒯_Def` | OPTA | `H_def` |
| `V14` | Acciones defensivas por partido | `𝒯_Def` | OPTA | `H_def` |
| `V15` | Intercepciones por partido | `𝒯_Def` | OPTA | `H_def` |
| `V16` | Big chances concedidas | `𝒯_Def` | `FUERA DE FUENTE` | `H_def` |
| `V17` | Goles evitados | `𝒯_Por` | OPTA | `H_def` |
| `V18` | Save % (atajadas) | `𝒯_Por` | OPTA | `H_def` |
| `V19` | Salidas / líbero por partido | `𝒯_Por` | OPTA | `H_def` |
| `V20` | Clean sheets | `𝒯_Por` | OPTA | `H_def` |
| `V21` | Goles a favor de pelota parada | `𝒯_Spc` | OPTA | `H_att` |
| `V22` | Goles recibidos de pelota parada | `𝒯_Spc` | OPTA | `H_def` |
| `V23` | Córners por partido | `𝒯_Spc` | OPTA | `H_att` |
| `V24` | Penales favor/contra | `𝒯_Spc` | OPTA | `H_att` |
| `V25` | Tarjetas amarillas/rojas | `𝒯_Spc` | OPTA | `H_ctx` |
| `V26` | Récord H2H | `𝒯_Ctx` | Q-BE | `H_ctx` |
| `V27` | ΔG H2H (diferencial de goles) | `𝒯_Ctx` | Q-BE | `H_ctx` |
| `V28` | Récord visitante en sede | `𝒯_Ctx` | Q-BE | `H_ctx` |
| `V29` | Altitud ΔAlt+ (factor fisiológico) | `𝒯_Ctx` | FIXTURE | `H_ctx` |
| `V30` | Días de descanso (ΔDías) | `𝒯_Ctx` | FIXTURE | `H_ctx` |
| `V31` | Forma 5P (puntos recientes) | `𝒯_Ctx` | Q-BE | `H_ctx` |
| `V32` | Varianza ΔxPTS | `𝒯_Ctx` | Q-BE | `H_ctx` |

### 4.3 Reglas del catálogo

1. **Cero duplicados:** cada `V##` pertenece a exactamente una dimensión.
2. **Cero invención:** `V16` se conserva en su fila, pero se declara `FUERA DE FUENTE`; no se imputa ni se muestra como `0.00`.
3. **Cero rename de red:** `variables_44` y `Catalogo44Out` sobreviven como nombres de contrato; la UI lee `n/m` del DTO, no de una constante local.
4. **Cero re-derivación en el cliente:** el frontend transcribe; no calcula λ, probabilidades, Δ logarítmicas ni récords.

---

## 5. BÓVEDA FÁCTICA

### 5.1 Estado de `qbe_historico.db`

**Ruta:** `qbe_observatory/data/qbe_historico.db`  
**Motor:** SQLite 3NF  
**Estado:** cargado y verificado en lectura.

| Métrica | Valor | Evidencia |
|---|---:|---|
| Partidos históricos | **3,870** | `historical_matches` |
| Partidos con cuotas 1X2 completas | **3,726** | `odd_home`, `odd_draw`, `odd_away` no nulos |
| Temporadas | **12** | `2015_2016` a `2026_2027` |
| Filas de estadísticas club-temporada | **217** | `historical_team_season_stats` |
| Cobertura xG por partido | **0 filas** | `xg_home` y `xg_away` no poblados |

> **Regla de honestidad:** la bóveda tiene 12 temporadas y 3,870 partidos. No se afirmará cobertura xG por partido mientras `historical_matches` no tenga ambos xG poblados. La ausencia se declara, no se imputa.

### 5.2 Distribución por temporada

| Temporada | Partidos | Cuotas 1X2 |
|---|---:|---:|
| `2015_2016` | 334 | 319 |
| `2016_2017` | 334 | 315 |
| `2017_2018` | 334 | 324 |
| `2018_2019` | 334 | 333 |
| `2019_2020` | 338 | 284 |
| `2020_2021` | 342 | 332 |
| `2021_2022` | 342 | 336 |
| `2022_2023` | 342 | 331 |
| `2023_2024` | 340 | 340 |
| `2024_2025` | 340 | 340 |
| `2025_2026` | 337 | 337 |
| `2026_2027` | 153 | 135 |
| **Total** | **3,870** | **3,726** |

La temporada `2026_2027` está en curso: 153 partidos cargados al corte. No se extrapola ni se completa.

### 5.3 Integridad de carga

`historical_load_log` registra 12 ejecuciones con estado `OK` y hash SHA-256 por temporada. La carga es idempotente y transaccional por temporada; un error de tipado produce `ROLLBACK` total de la temporada afectada. No se tocan `matches`, `sovereign_distributions` ni `match_telemetry`.

---

## 6. ESTADO FINANCIERO VIGENTE

### 6.1 Línea base declarada por la Dirección

| Parámetro | Valor | Estatus |
|---|---:|---|
| ROI de referencia | **+5.85%** | **Declarado por la Dirección**; pendiente de acta reproducible. |
| Drawdown de referencia | **1.5%** | **Declarado por la Dirección**; pendiente de acta reproducible. |
| Bankroll inicial | **$10,000** | **Declarado por la Dirección**. |
| Hard-cap individual | **8%** | Invariante constitucional. |
| Hard-cap de cartera | **25%** | Invariante constitucional. |
| Cota Underdog Ley 3 | **1.5%** | Invariante constitucional, exclusivo R1/R2. |

> **Provenance fiduciaria:** los valores `+5.85%`, `1.5%` y `$10,000` provienen de la directiva del expediente `SPRINT-MATERIALIZACION-PAQUETE-KTP-DOCS-39` y se consignan como **línea base declarada por la Dirección**, no como resultado auditado. Cualquier presentación pública debe citar esta condición. Si se obtiene un acta empírica, se actualizará este apartado con comando, fecha y evidencia.

### 6.2 Reglas de presentación

1. No se presenta un ROI declarado como ROI verificado.
2. No se confunde drawdown con la cota Underdog `0.0150`.
3. No se presenta un hard-cap como rendimiento.
4. Toda cifra financiera debe poder rastrearse a una fuente, una fecha y un comando.

---

## 7. MAPA DE INTERVENCIÓN RÁPIDA

**Formato:** “Qué cambiar → Dónde tocar → Juez asociado”.

| Qué cambiar | Dónde tocar | Juez asociado |
|---|---|---|
| Estrategia, triaje o cascada | `qbe_core/src/core/triage.py`, `docs/LOGIC.md` | `qbe_core/tests/test_shield_triage_r_subordination_and_odds_sanity.py` |
| Morfología Γ y símplex | `qbe_core/src/core/simplex_morphology.py`, `docs/CONSTANTS.md` | `qbe_core/tests/test_shield_simplex_morphology_and_gamma_slider.py` |
| Dutching y parámetro δ | `qbe_core/src/core/portfolio.py`, `docs/LOGIC.md` | `qbe_core/tests/test_shield_dynamic_dutching_delta.py` |
| Cartera, Kelly y hard-caps | `qbe_core/src/core/portfolio.py`, `docs/CONSTANTS.md` | `qbe_core/tests/test_shield_portfolio_math.py`, `test_shield_portfolio_integrity_and_floor.py` |
| Damping y `κ_net` | `qbe_core/src/core/intensity_canonical_loglink.py` | `qbe_core/tests/test_shield_sovereign_engine.py` |
| Désiré André y +PA | `qbe_core/src/core/andre_early_payout.py` | `qbe_core/tests/test_shield_sovereign_pipeline.py` |
| Persistencia y gateway | `qbe_storage/src/storage/gateway.py` | `qbe_storage/tests/test_shield_gateway_readonly_isolation.py` |
| Ingesta histórica y parser | `qbe_ingestion/src/ingestion/` | `qbe_ingestion/tests/test_shield_historical_load_integrity.py`, `test_shield_mhtml_parser_and_season_integrity.py` |
| Observatorio y calibración | `qbe_observatory/src/observatory/` | `qbe_observatory/tests/test_shield_obs.py`, `test_visor_auditoria_calibracion.py` |
| Transferencia KTP | `docs/KTP/` | `qbe_core/tests/test_shield_ktp_package_integrity.py` |

**Regla de intervención:** primero se lee la ley en `docs/`; después se crea o ajusta el Juez; solo entonces se modifica el código. Bajo `[DIRGEN-STRICT]`, una prueba que falla detiene el proceso y exige `DIRGEN_VARIANCE_REQUEST.md`; no se corrige por ensayo y error.

---

## 8. GOBIERNO DE IDENTIFICADORES

| ID | Familia | Título | Estado |
|---|---|---|---|
| `[LN-QBE-136]` | LOGIC | Sonda de Captura CDP-MHTML y Perfil Persistente | SELLADO |
| `[LN-QBE-137]` | LOGIC | Juez Inmutable de Integridad de Muestras MHTML | SELLADO |
| `[LN-QBE-138]` | LOGIC | Protocolo de Memoria Institucional Modular y Transferencia de Arquitectura (KTP Package) | SELLADO |
| `[ARCH-1.4.72]` | ARCH | Pipeline de Inyección Histórica Multianual y Reflection DDL | SELLADO |
| `[ARCH-1.4.73]` | ARCH | Extractor Histórico Masivo de FotMob | SELLADO — deuda de cuerpo declarada |
| `[ARCH-1.4.74]` | ARCH | Topología y Subsistema Documental de Transferencia KTP | SELLADO |

**Reglas:**

1. El ID es inmutable; no se reasigna ni se reutiliza.
2. El nuevo ID es `max(familia) + 1` sobre el registro completo.
3. Un ID sellado se deroga con tombstone, no se borra.
4. La deuda de cuerpo de `[ARCH-1.4.73]` está declarada y no autoriza reasignación.

---

## 9. PROTOCOLO DE TRANSFERENCIA KTP

| Fase | Responsable | Acción | Salida |
|---|---|---|---|
| **A. Despacho** | Arquitecto saliente | Ejecuta `AKT_Pmpt.md`. | `AKT.md` con el delta del turno. |
| **B. Consolidación** | Constructor | Ejecuta `KDB_Act_Pmpt.md`; actualiza `KDB.md`; copia `AKT.md` a `history/`; reinicia el activo. | `KDB.md` versionado, acta histórica y `AKT.md` vigente. |
| **C. Asunción** | Arquitecto entrante | Lee `KDB.md` y el último `AKT.md`; emite Eco de Comprensión. | Continuidad sin historial de chats. |

**Invariante de archivo:** se copia, no se mueve. `history/` es inmutable. `AKT.md` siempre existe.

---

## 10. DEUDAS ABIERTAS DECLARADAS

| Deuda | Impacto | Acción siguiente | Responsable |
|---|---|---|---|
| xG por partido no poblado en `historical_matches` | Limitación de modelos que requieren xG a nivel partido. | Cargar o declarar `SIN EVIDENCIA` por temporada. | Ingesta / Arquitecto |
| Wrapper CLI `scripts/auditoria/auditar_coherencia_cartelera.py` ausente | El pre-vuelo se ejecuta por módulo, no por wrapper. | Crear wrapper o actualizar la referencia documental. | Arquitecto |
| Cuerpo de `[ARCH-1.4.73]` ausente | Deuda documental; no afecta el ID. | Reconciliar en un sprint documental posterior. | Arquitecto |
| Línea base financiera sin acta reproducible | Riesgo de presentar una declaración como resultado. | Producir acta con comando, fecha y evidencia. | Director / Arquitecto |
| `data/sondas_exploracion/` sin trackear | Higiene de Git. | Mantener fuera del commit del paquete KTP. | Constructor |

---

## 11. TRAZABILIDAD

| Elemento | Anclaje |
|---|---|
| Ley KTP | `docs/LOGIC.md` §15, `[LN-QBE-138]` |
| Arquitectura KTP | `docs/ARCH.md` §14, `[ARCH-1.4.74]` |
| Registro maestro | `docs/ID_REGISTRY.md` |
| Guía operativa | `docs/KTP/KTP_Guide.md` |
| Prompt de despacho | `docs/KTP/AKT_Pmpt.md` |
| Prompt de consolidación | `docs/KTP/KDB_Act_Pmpt.md` |
| Juez | `qbe_core/tests/test_shield_ktp_package_integrity.py` |
| Acta activa | `docs/KTP/AKT.md` |
| Archivo histórico | `docs/KTP/history/` |

> **Mantenimiento:** este documento se actualiza solo por consolidación formal. La versión, la fecha y el acta de origen se registran en cada cambio. No se edita para “hacer pasar” un test; si la ley cambia, se emite la Ficha de Varianza correspondiente.
