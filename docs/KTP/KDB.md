# Q-BE ECOSYSTEM — BASE DE CONOCIMIENTO DEL PROYECTO (KDB)

**Documento:** `KDB.md` — Single Pane of Glass  
**Versión:** 1.7.0<br>
**Estado:** `[ALGO-PROTECTED]` — Conocimiento Estable Certificado  
**Proyecto:** `Q_BE_ECOSYSTEM`  
**Autoridad Suprema:** Américo García Guerrero (Director Humano)  
**Marco:** Kybern Industrial Framework v13.5 (DirGen Operational Edition)  
**Expediente:** `SPRINT-51-META-ROUTER-MACHINE-LEARNING`<br>
**Nodos:** `[LN-QBE-138]` / `[ARCH-1.4.74]`  
**Juez:** `qbe_core/tests/test_shield_ktp_package_integrity.py`  
**Última consolidación:** 2026-11-06<br>
**Actualización KTP:** 2026-11-06<br>
**Fuente de la consolidación:** `docs/KTP/AKT.md` (Sprint 51 — Meta-Router, veto por entropía y dataset maestro 2,667)

> **Nota de consolidación (2026-11-06) — v1.7.0, cierre `SPRINT-51`.** Se consolida el `SPRINT-51-META-ROUTER-MACHINE-LEARNING`. El dataset maestro queda materializado y verificado en solo lectura: **2,667 × 53**, SHA-256 `22633810…`, **cero NaN en columnas críticas** y **528 nulos declarados** (`delta_alt_metros` y `delta_descanso_dias` de `2015_2016`, sin imputar); Brier 3N reproducido **0.211572** (Q-BE) vs **0.203690** (Shin), Δ **−3.87 %**. Los resultados del **veto por entropía** (Brier `0.1882`, `p = 0.0012`) y del **Meta-Router** (`0.2005` vs `0.1998` en holdout `2025_2026`) provienen del Reporte Manus V2 y **no tienen artefacto reproducible en el repositorio**: se registran como **declarados**, no auditados. Decisiones: descarte del Meta-Router 1X2, adopción del veto selectivo por entropía y pausa del ML en 1X2. Deudas nuevas: **D-51.01** (exportación 32V), **D-51.02** (simulador financiero) y **D-51.03** (artefacto ML no reproducible). Bóveda sin cambios: **3,870** partidos, **3,726** con cuotas, **12** temporadas.

> **Nota de consolidación (2026-11-06) — v1.6.0, vista `/desempeno` y enrutador dual.** Se consolida `[DES-QBE-078]` (vista unificada de desempeño, Dark Fintech, mando rector, barras invertidas y persistencia de acordeón) y `[ARCH-1.4.78]` (enrutador dual de bóvedas: snapshot vivo para `2026_2027` y `qbe_historico.db` para las temporadas históricas y `Todas`), con `GET /` → `302 /desempeno`. Verificado en solo lectura: `2025_2026` sirve **305** partidos en **34** bloques de jornada; `Todas` agrega **2,726** partidos (**2,679** con vector de mercado) en **305** bloques. `2016_2017` y `2017_2018` siguen en **0** distribuciones P′ y se declaran vacías. Se homologó el navbar de las cuatro superficies y se retiró la portada pasiva `index.html`. Deudas nuevas: **D-50.11** (sincronía `ARCH.md` §18.2) y **D-50.12** (colisión de puerto `:8002`).

> **Nota de consolidación (2026-11-05) — cierre de Fase 9.** Se consolidan los nodos `[LN-QBE-151]` (des-margen de Shin) y `[LN-QBE-152]` (proyector de derivados), la doctrina de cobertura en dos niveles (§27) y la compuerta Paso 0 del Sistema Inmune. Se aplicó el parche **V-1** al denominador xG de la reconstrucción histórica y se re-materializó `P'` (2.737 filas): la brecha de λ cayó de **−8,20 % a −1,83 %** y el BSS de derivados de **−4,70 % a −0,73 %** (Under) y de **−2,70 % a −0,38 %** (BTTS). El **Censo de Paridad quedó en 0 hallazgos** (27 archivos, VÍA B sobre 23 ayudantes). El modelo sigue **sin resolución** sobre totales (`R² = 1,01 %`): `QBE-C2` permanece congelado. Bóveda: **3,870** partidos, 12 temporadas.

> **Nota de consolidación (2026-11-04):** se consolida el delta del `SPRINT-50-REINGENIERIA-INDUSTRIAL-QBE-CORE`: ratificación del Decreto D1–D5 (`VAR-2026-SPRINT50-CORE`), materialización de la Fase 2A (clausura de masa, Invariante L-1) y 2B (GSL-3D v2), súper-señal V6 con su barrido de κ, Sistema Inmune Fiduciario (27.31 % de veto), motor anti-sesgo de 3 zonas (ROI negativo en las tres) y el cementerio del ML predictivo (`legacy_ml/`). El sprint **no se cierra**: la Fase 9 (De-vig Shin, consenso multicasa, derivados) queda como deuda viva en §10. Bóveda verificada en solo lectura: 3,870 partidos, 3,726 con cuotas completas, 12 temporadas.

> **Nota de consolidación (2026-11-01):** cierre del `SPRINT-45-EXPANSION-CAUSAL-Y-RESCATE-EN-VIVO`. Se consolida la extracción causal minuto a minuto (301 partidos, 13,443 eventos), el vector de 32 variables con 9 derivadas y 23 `SIN EVIDENCIA`, la calibración in-sample 2015-2016 y la formalización VÍA B de 8 ayudantes (Censo de Núcleo en 0). Quedan abiertos `C01-C08`, el Daemon en vivo, el split Train/Test y el Censo ampliado de `qbe_business` (72 Clase IV).

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
| Bóveda histórica | `qbe_observatory/data/qbe_historico.db` | OLAP histórico; lectura para calibración y para `/desempeno` (enrutador dual `[ARCH-1.4.78]`). |
| Eventos y variables causales | `historical_match_events`, `historical_match_causal_vars` en `qbe_observatory/data/qbe_historico.db` | OLAP histórico; lectura para derivación y calibración. |
| Vista unificada de desempeño | `GET /desempeno` (`qbe_observatory`) | Jinja2 de solo lectura; enrutador dual de bóvedas. |
| Raíz del Observatorio | `GET /` → `HTTP 302 /desempeno` | Sin portada pasiva (`index.html` retirado). |
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

### 4.4 Derivación causal desde eventos

El vector de 32 variables puede derivarse parcialmente de la línea de tiempo `historical_match_events` mediante `[LN-QBE-146]` (`qbe_core/src/core/sovereign/derivar_variables_causales.py`). Al corte 2026-11-01:

- **9 variables derivadas:** `V05`, `V07`, `V13`, `V20`, `V21`, `V22`, `V23`, `V24`, `V25`.
- **23 variables `SIN EVIDENCIA`:** `V01`–`V04`, `V06`, `V08`–`V12`, `V14`–`V19`, `V26`–`V32`.

**Reglas de derivación:**

1. `None` ≠ `0.0`: la ausencia se declara, no se imputa.
2. `V07`/`V13` incluyen `gol_penal` como remate al arco.
3. `V21`/`V22` exigen córner o penal previo del mismo lado dentro de 5 minutos.
4. `V05`, `V23`, `V24` y `V25` son conteos directos de eventos.
5. `V20` es `1` si el rival no anotó; `0` si anotó.
6. No se imputan posesión, xG, pases, H2H, altitud, descanso ni forma.

La tabla `historical_match_causal_vars` guarda una fila por partido con `derivadas = 9` y la lista de las 23 variables `SIN EVIDENCIA`.

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
| Partidos con eventos minuto a minuto | **301** | `historical_match_events` |
| Eventos persistidos | **13,443** | `historical_match_events` |
| Filas de variables causales | **3,000** | `historical_match_causal_vars` (2,699 `FOTMOB_MATCHDETAILS` + 301 `LIGAMX_MXM`) |
| Distribuciones P' históricas | **2,737** | `historical_sovereign_distributions` (`[LN-QBE-150]`) |
| Distribuciones P' V2 (GSL-3D v2) | **2,727** | `historical_sovereign_distributions_v2` |
| Distribuciones P' V3 | **2,727** | `historical_sovereign_distributions_v3` |
| Temporadas con 32 variables completas | **0** | `historical_match_causal_vars.derivadas = 32` |
| Temporadas con 9 variables | **1** (`2015_2016`, 301/334) | `historical_match_causal_vars.derivadas = 9` |
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

### 5.4 Cobertura causal y calibración in-sample

| Métrica | Valor | Evidencia |
|---|---|---|
| Partidos con vector causal | **301** | `historical_match_causal_vars` |
| Variables derivadas por partido | **9** | `derivadas = 9` en 301/301 |
| Variables `SIN EVIDENCIA` por partido | **23** | columna `sin_evidencia` |
| Muestra de referencia | 49 eventos de América 3-3 Monterrey (`fs_2015_2016_z85264`) | `historical_match_events` |
| Brier base in-sample | **0.65546144** | `data/reportes/calibracion_2015_2016.json` |
| Brier optimizado in-sample | **0.59896449** | ídem; Δ `-0.05649695`, mejora `8.62%` |
| Brier de mercado | **0.64031362** | ídem |

> **Limitación declarada:** la calibración es **in-sample** (2015-2016); no existe split Train/Test. La mejora de 8.62% mide ajuste al puente, no capacidad predictiva fuera de muestra. El overfitting queda `SIN EVIDENCIA`.

### 5.5 Corpus histórico masivo P' — cierre `SPRINT-48`

Materialización completa del símplex soberano P' sobre el corpus histórico (`[LN-QBE-150]`, `[ARCH-1.5.1]` §15.5). La matemática no se reimplementó: cada fila es la salida de `generar_distribucion_soberana` sobre el registro fáctico **pre-kickoff** reconstruido desde la bóveda.

| Métrica | Valor |
|---|---:|
| Distribuciones P' persistidas | **2,737** |
| Cobertura sobre la bóveda | **70.7 %** (2,737 / 3,870 partidos) |
| Procedencia `FOTMOB_MATCHDETAILS` | **2,461** |
| Procedencia `LIGAMX_MXM` | **276** |
| Temporadas con P' | **10 de 12** |
| Fixtures FotMob emparejados | **3,181** (0 `UNMATCHED` de partidos jugados salvo Liguilla sin fila en bóveda) |
| Peticiones a FotMob | 1 por partido, cadencia fija `1.0 s` |
| Descartes `SI_insuficiente` | **263** (≈ 8 % estructural, J1–J3 de cada Apertura) |
| Imputaciones | **0** |

**Cobertura por temporada:**

| Temporada | Filas P' | Fuente causal |
|---|---:|---|
| 2015_2016 | 276 | `LIGAMX_MXM` |
| 2016_2017 | 0 | `SIN EVIDENCIA` |
| 2017_2018 | 0 | `SIN EVIDENCIA` |
| 2018_2019 | 253 | `FOTMOB_MATCHDETAILS` |
| 2019_2020 | 243 | `FOTMOB_MATCHDETAILS` |
| 2020_2021 | 314 | `FOTMOB_MATCHDETAILS` |
| 2021_2022 | 315 | `FOTMOB_MATCHDETAILS` |
| 2022_2023 | 315 | `FOTMOB_MATCHDETAILS` |
| 2023_2024 | 304 | `FOTMOB_MATCHDETAILS` |
| 2024_2025 | 305 | `FOTMOB_MATCHDETAILS` |
| 2025_2026 | 305 | `FOTMOB_MATCHDETAILS` |
| 2026_2027 | 107 | `FOTMOB_MATCHDETAILS` (temporada en curso) |

> **Hueco asumido 2016-2018.** `2016_2017` y `2017_2018` quedan en **0 filas** (668 partidos): FotMob no publica `content.stats` antes de 2018/19 —verificado por sonda directa en `matchDetails` de 2015/16, 2016/17 y 2017/18— y ligamx.net fue descartado como fuente causal por dictamen. El hueco se declara, no se imputa ni se rellena con priors.
>
> **Cold start asumido.** Cada Apertura pierde sus jornadas 1–3 (27–30 partidos, ≈8 % de la temporada) porque `S(I_i)` exige 3 partidos previos por club dentro de la misma temporada. Aprobado por Dirección como pérdida estructural; el Clausura nunca descarta.

#### 5.5.1 Alpha histórico masivo — Q-BE vs Mercado

El Observatorio (`/consenso`, `[LN-QBE-148]` Φ) ya calcula el **Alpha histórico masivo** cruzando el símplex P' con los momios de FootyStats. La muestra de comparación son los partidos donde **coexisten** momios y distribución P'; un partido sin P' queda fuera del promedio de Q-BE (no se imputa como cero) y sin coexistencia el Alpha se declara `SIN EVIDENCIA`.

| Ámbito | Muestra (coexistencia) | Brier FootyStats | Brier Q-BE | Alpha |
|---|---:|---:|---:|---:|
| Temporada `2023_2024` | 304 de 340 auditados | 0.2021 | 0.2068 | **−2.33 %** |
| Universo histórico («Todas») | 2 690 de 3 870 auditados | 0.2040 | 0.2120 | **−3.92 %** |

* **Fórmula canónica:** `Alpha = (1 − Brier_QBE / Brier_FootyStats) × 100`, con Brier normalizado 3N (`[LN-QBE-100]`).
* **Lectura:** el mercado FootyStats sigue siendo marginalmente mejor calibrado que Q-BE en el histórico (−2.3 % a −3.9 %); el signo negativo es resultado, no defecto. Ningún porcentaje se fabrica: sin P' el Alpha es ausente.
* **Desglose por jornada:** no se publica en el modo global porque `historical_matches` no porta número de jornada; la UI lo declara en lugar de inventarlo.

### 5.6 Súper-Señal V6, Sistema Inmune y motor anti-sesgo — `SPRINT-50`

El motor V6 (`generar_distribucion_v6`, `qbe_core/src/core/sovereign_pipeline.py`) aísla exclusivamente `V06` (xG), `V07` (SoT) y `V12` (xGA) por temporada, sin GSL-3D y con α fija de `0.203603` en el punto canónico. Resultados reproducidos en solo lectura el 2026-11-04:

| Evidencia | Valor | Fuente |
|---|---:|---|
| Barrido κ en Train `[0.35, 0.55]` | **κ\* = 0.35** (Brier `0.642249`, N=990) | `scripts/investigacion/fase6_supersenal.py` |
| V6 Test con κ\* | Brier `0.617547` (N=1,084) | ídem |
| V1 en la misma muestra | Brier `0.616470` (N=1,012) | ídem |
| FootyStats (mercado) | Brier `0.598721` (N=1,084) | ídem |
| Alpha V6 Test vs mercado | **−3.14 %** | ídem |
| Sistema Inmune: veto `QBE-00` | **296 / 1,084 = 27.31 %** | `triage.veto_inmunidad_fiduciaria` |
| Desglose del veto | 206 `SOBREASEDIO_DEFENSIVO` + 90 `INEFICACIA_OFENSIVA` | ídem |
| Anti-sesgo Z1 Consenso `\|P−q\|<0.03` | ROI **−8.29 %** (N=249) | `scripts/investigacion/fase8_sesgo_popular.py` |
| Anti-sesgo Z2 Peligro `P−q>0.10` | ROI **−20.11 %** (N=18) | ídem |
| Anti-sesgo Z3 Fade `q−P>0.08` | ROI **−14.94 %** (N=426) | ídem |
| Cobertura sintética Z3 | ROI **−5.86 %** (N=426) | ídem |
| Prima Popular (top 5) | Morelia `+0.0851` (16) · Monterrey `+0.0691` (237) · Cruz Azul `+0.0550` (250) · Tigres `+0.0538` (256) · América `+0.0465` (263) | ídem |

> **Lectura honesta.** V6 **no** supera a V1 (`0.6175` vs `0.6165`) ni al mercado (`0.5987`); su Alpha es negativo y las tres zonas anti-sesgo pierden dinero. El motor puro no ha demostrado ventaja en 1X2. El Índice de Prima Popular es paramétrico (sin nombres cableados): los clubes listados son resultado, no configuración.

> **Sello de producción.** `κ* = 0.35` es el óptimo empírico del experimento V6; el damping sellado del motor sigue en `KAPPA_NET = 0.25` (Invariante 9, §3). Adoptar κ\* en producción exige Ficha de Varianza y re-sellado.

---

### 5.7 Fase 9 — Shin, derivados y secuencia inmune (cierre `SPRINT-50`)

La Fase 9 materializó tres contratos en `qbe_core` y los certificó con 35 aserciones:

| Nodo | Materialización | Contrato |
|---|---|---|
| `[LN-QBE-151]` | `consensus.desmarginar_shin` | Inversión del modelo de Shin (1991, 1993): `Σ√(z²+4(1−z)π_k²/S) = 2+z`, `z ∈ [0, min π_k]`, DTO `ShinDevigResult`, `InvalidOddsException` |
| `[LN-QBE-152]` | `distribution_dixon_coles.proyectar_mercados_derivados` | Proyección exacta de `M*_xy` 7×7 a Under/Over 2.5 y BTTS; `MatrixIntegrityError`; sin renormalización |
| `[LN-QBE-060-B]` §27 | `triage.triaje_financiero_mundo2` | Paso 0 inmune **antes de leer cuotas**; veto ⇒ `QBE-00` con \$0.00 MXN y traza de ambas distribuciones; Pasos 1-2 delegados a la cascada sellada |

**Hallazgo estructural (VAR-2026-F9-02).** El proyector y Shin cumplen sus Jueces; el fallo estaba en el insumo. La reconstrucción histórica sumaba xG sólo sobre los partidos con vector causal (cobertura 62,7 %) y lo dividía entre `pj` (todos), contrayendo el factor de ataque. El parche V-1 normaliza el acumulado al denominador completo.

| Métrica | Antes | Después V-1 |
|---|---:|---:|
| λ_sum medio | 2,5221 | **2,6971** |
| Brecha vs goles observados (2,7474) | −8,20 % | **−1,83 %** |
| Under 2.5 — BSS | −4,70 % | **−0,73 %** |
| BTTS Sí — BSS | −2,70 % | **−0,38 %** |
| `corr(λ_sum, goles)` | +0,0884 | **+0,1006** (R² 1,01 %) |
| 1X2 — ROI P_max | −6,73 % | **−5,21 %** |
| Shin vs proporcional | Δ = −6,955×10⁻⁵ (t = −0,94) | sin cambio |

> **Lectura honesta.** Corregir la calibración mejora el Brier pero **no cruza cero**: la `resolution` de λ sobre el total de goles es ~1 %. Un modelo de 1X2 no es un modelo de totales. `QBE-C2` queda congelado hasta demostrar `R² > 0,05` y BSS > 0 out-of-sample.

**Convenciones de métrica.** Brier 3N = multiclase / 3 (`[LN-QBE-100]`); mercados binarios normalizados por 2. El Alpha de derivados se declara `SIN EVIDENCIA` porque la bóveda no publica cuotas de Totales ni de BTTS (sólo 1X2 de FootyStats y captura Q-BE Live).

### 5.8 Vista unificada `/desempeno` y enrutador dual de bóvedas — `[ARCH-1.4.78]` · FIX

`GET /desempeno` (`[DES-QBE-078]`) conmuta la fuente según la temporada solicitada: `2026_2027 · Actual` se sirve del snapshot vivo por el builder canónico; `Todas` y las temporadas históricas se sirven de la bóveda OLAP en solo lectura (`mode=ro` + `PRAGMA query_only=ON`), cruzando `historical_matches` con `historical_sovereign_distributions`. El orden fiduciario se delega en `resolver_orden_fiduciario_con_indiferencia` `[LN-QBE-124]`; el des-margen en `[LN-QBE-151]`/`[VAULT-CORE-007-C]`; el Brier 3N en `[LN-QBE-100]`. Sin parámetro la vista aterriza en la temporada en curso.

| Consulta | Partidos | Jornadas | Brier Q-BE | Brier Mkt (Shin) | Alpha | Rescate Q-BE | Rescate Mercado | N (coincidencia) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `2026_2027 · Actual` | 134 | 15 | 0.2149 | 0.2111 | −1.80 % | 71.6 % | 73.6 % | 110 |
| `2025_2026` | 305 | 34 | 0.2043 | 0.1999 | −2.20 % | 78.4 % | 76.4 % | 305 |
| `Todas` | 2,726 | 305 | 0.2115 | 0.2036 | −3.88 % | 74.6 % | 77.6 % | 2,679 |
| `2016_2017` | 0 | 0 | `SIN EVIDENCIA` | `SIN EVIDENCIA` | `SIN EVIDENCIA` | `SIN EVIDENCIA` | `SIN EVIDENCIA` | 0 |

* **Agrupación:** `historical_matches` no porta número de jornada; el corpus se agrupa en bloques cronológicos de 9 partidos por temporada (declarado, no inventado).
* **Denominadores:** Briers y Alpha se agregan sobre la muestra coincidente P′ ∩ q_mkt ∩ resultado; la Tasa de Rescate usa el par `{r_max, r_mid}` en Modo Q-BE y `{max q, second_max q}` en Modo Mercado.
* **Exclusiones declaradas:** 47 partidos de `Todas` sin vector de mercado quedan fuera del Brier de mercado y se marcan `SIN EVIDENCIA`; `2016_2017`/`2017_2018` no tienen P′ (0 filas) y se declaran vacías. La temporada en curso se excluye del corpus histórico para no duplicar fixtures.
* **Jueces:** `qbe_observatory/tests/test_shield_desempeno_route.py` y `test_shield_desempeno_visual_semantics.py` (24 casos entre ambos).

### 5.9 Meta-Router, veto por entropía y dataset maestro — `SPRINT-51`

El `SPRINT-51` evaluó el Meta-Router Q-BE vs Shin y la taxonomía de Vetos Fiduciarios con validación temporal Rolling-Origin. El único artefacto reproducible en el repositorio es el dataset maestro y sus folds; los resultados numéricos del experimento ML provienen del Reporte Manus V2 y se consignan como **declarados**.

**Dataset maestro (`data/investigacion/dataset_meta_router_2667.parquet`) — verificado 2026-11-06:**

| Métrica | Valor | Evidencia |
|---|---:|---|
| Filas × columnas | **2,667 × 53** | lectura del Parquet |
| SHA-256 | `22633810ff22220a1767e89a1622c9b7bbf6ca3a76828b0b71697b718657b613` | `Get-FileHash` |
| Nulos en columnas críticas (`p_qbe_*`, `q_shin_*`, `brier_*`, `resultado_real`) | **0** | `isna().sum()` |
| Nulos declarados (no imputados) | **528** = 264 `delta_alt_metros` + 264 `delta_descanso_dias` | `2015_2016` sin `V29`/`V30` |
| Temporadas | **10** (`2016_2017` y `2017_2018` excluidas por falta de P′) | columna `temporada` |
| Brier 3N Q-BE | **0.211572** | media de `brier_qbe_3n` |
| Brier 3N Shin | **0.203690** | media de `brier_mkt_3n` |
| Delta (Shin − Q-BE) | **−0.007882 (−3.87 %)** | cálculo |

**Folds (`folds_rolling_origin.json`):** 5 folds Rolling-Origin (`2020_2021` … `2024_2025`), holdout final sellado `2025_2026` y `2026_2027` (98 partidos) como conjunto de estrés post-holdout. Las temporadas `2016_2017` y `2017_2018` quedan excluidas (0 filas P′).

**Resultados declarados (Reporte Manus V2, sin artefacto en el repositorio):**

| Resultado | Valor | Estatus |
|---|---|---|
| Veto fiduciario por entropía — Brier retenido | **0.1882** | Declarado; `p = 0.0012` declarado |
| Meta-Router 1X2 — Brier árbol | **0.2005** | Declarado |
| Meta-Router 1X2 — Brier Shin (holdout `2025_2026`) | **0.1998** | Declarado |

> **Lectura honesta.** El ensamble ML no superó a Shin fuera de muestra; el 1X2 se declara hiper-eficiente y el valor residual inoperable por el vig. El veto por entropía se adopta como mitigación de varianza, no como fuente de Alpha. Ninguna de las tres cifras tiene script, log ni JSON en el repositorio: **no son auditables** (`D-51.03`).

---

## 6. ESTADO FINANCIERO VIGENTE

### 6.1 Línea base declarada por la Dirección

| Parámetro | Valor | Estatus |
|---|---:|---|
| ROI de referencia | **+5.85%** | **Declarado por la Dirección**; pendiente de acta reproducible. |
| ROI de vetos fiduciarios (Flat Stake) | **−8.38%** | **Declarado en Reporte Manus V2**; no auditado; ignora Dutching `V=0`. |
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
| Súper-Señal V6 (V06/V07/V12) | `qbe_core/src/core/sovereign_pipeline.py` (`generar_distribucion_v6`) | `tests/shield/test_shield_core_v6_supersenal.py` |
| Sistema Inmune Fiduciario (veto `QBE-00`) | `qbe_core/src/core/triage.py` (`veto_inmunidad_fiduciaria`) | `tests/shield/test_shield_core_v6_supersenal.py` |
| Clausura de masa (Invariante L-1) | `qbe_core/src/core/intensity_canonical_loglink.py` | `qbe_core/tests/test_shield_core_v2_rigor.py` |
| GSL-3D v2 y puente de matriz | `qbe_core/src/core/sovereign/orthogonal_factor_engine.py` | `tests/shield/test_shield_core_v2_puente_matriz.py`, `test_shield_core_v3_enmiendas.py` |
| Motor anti-sesgo y Prima Popular | `scripts/investigacion/fase8_sesgo_popular.py` | Sin Juez dedicado (`SIN EVIDENCIA`); solo lectura de bóveda |
| Cementerio del ML predictivo | `qbe_observatory/src/observatory/legacy_ml/` | Prohibido reimportar desde `qbe_core` o el pipeline V6 |
| Désiré André y +PA | `qbe_core/src/core/andre_early_payout.py` | `qbe_core/tests/test_shield_sovereign_pipeline.py` |
| Persistencia y gateway | `qbe_storage/src/storage/gateway.py` | `qbe_storage/tests/test_shield_gateway_readonly_isolation.py` |
| Ingesta histórica y parser | `qbe_ingestion/src/ingestion/` | `qbe_ingestion/tests/test_shield_historical_load_integrity.py`, `test_shield_mhtml_parser_and_season_integrity.py` |
| Extracción de eventos minuto a minuto | `qbe_ingestion/src/ingestion/parsers/parsear_minuto_a_minuto.py`, `loaders/cargar_eventos_historicos.py`, `scripts/auditoria/` | `qbe_ingestion/tests/test_shield_minuto_a_minuto_parser.py`, `test_shield_orquestador_extraccion.py`, `test_shield_descubrimiento_ligamx.py` |
| Variables causales y calibración | `qbe_core/src/core/sovereign/derivar_variables_causales.py`, `calibrar_perturbacion.py` | `qbe_core/tests/test_shield_derivacion_causal.py`, `test_shield_calibracion.py` |
| Paridad canónica y Censo | `scripts/auditoria/auditar_paridad_bg.py` | `qbe_core/tests/test_shield_canonical_parity.py` |
| Observatorio y calibración | `qbe_observatory/src/observatory/` | `qbe_observatory/tests/test_shield_obs.py`, `test_visor_auditoria_calibracion.py` |
| Vista unificada de desempeño | `qbe_observatory/app/routes/desempeno_ui.py`, `app/services/desempeno_view.py`, `app/templates/desempeno.html` | `qbe_observatory/tests/test_shield_desempeno_route.py`, `test_shield_desempeno_visual_semantics.py` |
| Enrutador dual de bóvedas | `qbe_observatory/app/services/desempeno_view.py` | Ídem (`test_shield_desempeno_route.py`) |
| Navbar único del Observatorio | `qbe_observatory/app/templates/_navbar.html` + `base.html` | `qbe_observatory/tests/test_shield_desempeno_route.py` |
| Transferencia KTP | `docs/KTP/` | `qbe_core/tests/test_shield_ktp_package_integrity.py` |

**Regla de intervención:** primero se lee la ley en `docs/`; después se crea o ajusta el Juez; solo entonces se modifica el código. Bajo `[DIRGEN-STRICT]`, una prueba que falla detiene el proceso y exige `DIRGEN_VARIANCE_REQUEST.md`; no se corrige por ensayo y error.

---

## 8. GOBIERNO DE IDENTIFICADORES

| ID | Familia | Título | Estado |
|---|---|---|---|
| `[LN-QBE-136]` | LOGIC | Sonda de Captura CDP-MHTML y Perfil Persistente | SELLADO |
| `[LN-QBE-137]` | LOGIC | Juez Inmutable de Integridad de Muestras MHTML | SELLADO |
| `[LN-QBE-138]` | LOGIC | Protocolo de Memoria Institucional Modular y Transferencia de Arquitectura (KTP Package) | SELLADO |
| `[LN-QBE-139]` | LOGIC | Auditor de Paridad Estática AST y Generador de Bandeja `GL_update.md` | SELLADO |
| `[LN-QBE-140]` | LOGIC | Juez Inmutable de Paridad Canónica y Detección de Reglas Huérfanas | SELLADO |
| `[LN-QBE-141]` | LOGIC | Parser Offline de Eventos Minuto a Minuto (Jugada a Jugada) | SELLADO |
| `[LN-QBE-142]` | LOGIC | Sonda de Descubrimiento de Partidos y URLs Minuto a Minuto (ligamx.net) | SELLADO |
| `[LN-QBE-143]` | LOGIC | Orquestador de Extracción Masiva de Eventos (ligamx.net → Bóveda OLAP) | SELLADO |
| `[LN-QBE-144]` | LOGIC | Almacén de Eventos Históricos (`historical_match_events`) | SELLADO |
| `[LN-QBE-145]` | LOGIC | Diccionario Canónico de Alias de Liga MX (`ligamx.net` → bóveda) | SELLADO |
| `[LN-QBE-146]` | LOGIC | Motor de Derivación de Variables Causales | SELLADO |
| `[LN-QBE-147]` | LOGIC | Motor de Calibración y Perturbación de Variables Causales | SELLADO |
| `[LN-QBE-148]` | LOGIC | Motor de Consenso Ponderado (Wisdom of the Crowds) | SELLADO |
| `[LN-QBE-149]` | LOGIC | Motor de Detección de Rupturas de Consenso (Radar de Sindicatos) | SELLADO |
| `[LN-QBE-150]` | LOGIC | Motor de Cálculo de Distribuciones Históricas (P') | SELLADO |
| `[LN-QBE-151]` | LOGIC | Motor de Des-margen Implícito de Shin (Shin De-vigging Engine) — IPO Node | SELLADO |
| `[LN-QBE-152]` | LOGIC | Proyector Analítico de Mercados Derivados (Totales & BTTS) — IPO Node | SELLADO |
| `[DES-QBE-078]` | DISEÑO | Vista Unificada de Desempeño y Coberturas Probabilísticas (`/desempeno`) | SELLADO |
| `[ARCH-1.4.78]` | ARCH | Enrutador y Fachada de Desempeño Híbrido (`qbe_observatory`) | SELLADO |
| `[ARCH-1.4.72]` | ARCH | Pipeline de Inyección Histórica Multianual y Reflection DDL | SELLADO |
| `[ARCH-1.4.73]` | ARCH | Extractor Histórico Masivo de FotMob | SELLADO — deuda de cuerpo declarada |
| `[ARCH-1.4.74]` | ARCH | Topología y Subsistema Documental de Transferencia KTP | SELLADO |
| `[ARCH-1.5.1]` | ARCH | Esquema Relacional 3NF Multi-Torneo — Especificación Canónica de Columnas | SELLADO |

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
| **C. Asunción** | Arquitecto entrante | Ejecuta `RT_Pmpt.md` con `KDB.md` y `AKT.md`; aplica Alto al Fuego Inicial; emite Eco de Comprensión Integral de 7 puntos y espera orden. | Continuidad sin historial de chats. |

### 9.1 Inventario de artefactos rectores (estructura séxtuple)

| Artefacto | Función | Fase |
|---|---|---|
| `KTP_Guide.md` | Manual operativo y FSM de transferencia. | Todas |
| `KDB.md` | Base de conocimiento estable. | B / C |
| `AKT_Pmpt.md` | Prompt de extracción saliente. | A |
| `AKT.md` | Delta activo del turno. | A / B |
| `KDB_Act_Pmpt.md` | Prompt de consolidación en disco. | B |
| `RT_Pmpt.md` | Prompt de asunción de mando entrante. | C |
| `history/` | Registro inmutable de actas archivadas. | B |

**Invariante de existencia:** los seis archivos rectores y el directorio `history/` deben existir siempre.  
**Invariante de archivo:** se copia, no se mueve. `history/` es inmutable. `AKT.md` y `RT_Pmpt.md` siempre existen.

### 9.2 Compuerta de Censo de Paridad Canónica

La Fase B exige el Censo de Paridad Canónica de `docs/GOVERNANCE.md` §3.5. **Cierre `SPRINT-50` (2026-11-05):** el Censo se ejecutó sobre `qbe_core/src/core` (27 archivos) y quedó en **0 hallazgos** (Clases I, II, III y IV), tras la VÍA B de 23 ayudantes heredados. Bandeja `docs/KTP/GL_update.md` con SHA-256 `cb5c8cf9…`. El barrido ampliado de §3.5 sobre `qbe_business/src` reporta **72 hallazgos Clase IV** preexistentes; se registran como deuda separada y no se declaran en 0. **Re-verificado (2026-11-06):** 27 archivos, 0 hallazgos.

---

## 10. DEUDAS ABIERTAS DECLARADAS

**Cerradas en la consolidación v1.5.0 (2026-11-05):** `D-50.01` (denominador xG — parche V-1 aplicado y `P'` re-materializada), `D-50.05` (23 Clase IV — Censo en 0) y `D-50.10` (consolidación KDB). El detalle vive en `docs/VAR-2026-F9-02.md` y en el AKT.

**Cerradas en la consolidación v1.6.0 (2026-11-06):** `D-50.09` (`.pytest_tmp/` y `.tmp_run/` ignorados por `.gitignore`).

| ID | Deuda | Impacto | Acción siguiente | Responsable |
|---|---|---|---|---|
| **D-51.01** | Exportación 32V incompleta: el pipeline Parquet omitió las variables crudas `V01`–`V32` | Bloquea los Arquetipos 1, 3, 7 y 8 | Corregir `exportar_dataset_manus.py` para aplanar el JSON de causales | Constructor |
| **D-51.02** | Simulador financiero: el ROI reportado (`−8.38 %`) es Naive Flat Stake e ignora el Dutching `V=0` | El ROI de los vetos no refleja la cartera Q-BE | Incorporar `portfolio_math.py` al script de evaluación de ROI | Quant / Arquitecto |
| **D-51.03** | Resultados ML del Sprint 51 sin artefacto reproducible: Brier `0.1882` / `0.2005` / `0.1998` provienen del Reporte Manus V2 | Las decisiones de descarte y de veto no son auditables end-to-end | Publicar cuaderno, semilla y folds del experimento, o re-ejecutarlo con `folds_rolling_origin.json` | Arquitecto |
| **D-50.02** | λ no discrimina el total de goles (`corr = +0,1006`, `R² = 1,01 %`, pendiente OLS 0,41 vs 1,00) | `QBE-C2` congelado: ningún reanclaje convierte el BSS en positivo | Abrir la ruta C (modelo de totales dedicado) con criterio `R² > 0,05` out-of-sample y BSS > 0 | Arquitecto / Constructor |
| **D-50.03** | Ancla `μ_liga = 2.65` bajo la media observada 2,7474 | Brecha residual de nivel 1,83 % (bajo el umbral del 2 %) | Diferida; sólo decreto si la brecha supera el 2 % | Director |
| **D-50.04** | Proveedor histórico de momios único (FootyStats), sin Totales ni BTTS | El Alpha de derivados es `SIN EVIDENCIA`; el consenso multicasa no se reconstruye hacia atrás | Integrar OddsPortal o BetExplorer Pro; declarar cobertura | Arquitecto / Director |
| **D-50.06** | 23 partidos con cuotas corruptas `(1.50, 3.00, 1.50)` (overround 1,667) | Contaminan cualquier métrica que no aplique la aduana `[LN-QBE-007-H]` | Purga o cuarentena declarada en `historical_matches` | Ingesta |
| **D-50.07** | Percentiles del Sistema Inmune in-sample y no persistidos | La tasa de veto (12,10 %) no es comparable entre corridas | Persistir percentiles calibrados con split Train/Test | Arquitecto |
| **D-50.08** | Shin no aporta valor económico medible en 1X2 (Δ = −6,955×10⁻⁵, t = −0,94) | Coste de complejidad sin retorno demostrado | Mantener (es correcto) y documentar que no es fuente de Alpha | Arquitecto |
| **D-50.11** | `docs/ARCH.md` §18.2 no lista los campos vivos del DTO de desempeño (`etiqueta`, `n_mercado`, `alpha_pct`, `tasa_rescate_pct`) ni los orígenes `historico_olap`/`dual_vault` | Deriva documental: el contrato legislado va por detrás del código sellado | Sincronizar la tabla de DTOs y el enrutador dual en el libro de arquitectura | Arquitecto |
| **D-50.12** | Proceso vivo en `:8002` (Data Nexus) desbloquea `/api/admin/status/drift`, ruta-puente exenta por diseño | Falso positivo en `test_spa_desactiva_backtesting_y_admin` de `qbe_business` cuando el daemon está en línea | Aislar `QBE_INGESTION_URL` en el Juez o eximir la ruta-puente en la aserción | Infraestructura |
| xG por partido no poblado en `historical_matches` | Limitación de modelos que requieren xG a nivel partido. | Cargar o declarar `SIN EVIDENCIA` por temporada. | Ingesta / Arquitecto |
| Wrapper CLI `scripts/auditoria/auditar_coherencia_cartelera.py` ausente | El pre-vuelo se ejecuta por módulo, no por wrapper. | Crear wrapper o actualizar la referencia documental. | Arquitecto |
| Cuerpo de `[ARCH-1.4.73]` ausente | Deuda documental; no afecta el ID. | Reconciliar en un sprint documental posterior. | Arquitecto |
| Línea base financiera sin acta reproducible | Riesgo de presentar una declaración como resultado. | Producir acta con comando, fecha y evidencia. | Director / Arquitecto |
| `data/sondas_exploracion/` sin trackear | Higiene de Git. | Mantener fuera del commit del paquete KTP. | Constructor |
| Deuda 3 — Tres scripts de laboratorio con imports legados (`sandbox_h2h_pipeline.py`, `sandbox_volumen_porteria_pipeline.py`, `manus_qbe_model.py`) | No afectan producción ni The Shield; rompen la reproducibilidad del laboratorio. | Reconectar a `qbe_core` / `qbe_storage`; smoke test de importación y `--help`. | Constructor |
| Catálogo Compuesto `C01-C08` no materializado | No hay 8 variables compuestas (ej. Reacción post-gol), ni ID sellado, ni Juez, ni columnas en la BD. | Definir especificación, asignar ID, crear Juez Inmutable, migrar columnas y poblar los 301 partidos. | Director / Arquitecto |
| Daemon en vivo `Centinela` detenido | La ingesta en vivo no está rescatada; sin proceso, tarea programada ni log. La causa raíz no está diagnosticada. | Diagnosticar red/credenciales/entorno, arrancar el Daemon y dejar log; o emitir Ficha de Varianza. | Arquitecto / Infraestructura |
| Sin split Train/Test | El Brier `0.65546144 → 0.59896449` es in-sample; no hay evidencia fuera de muestra ni dictamen de overfitting. | Implementar partición temporal y ejecutar calibración cruzada; si no hay Test, declarar `SIN EVIDENCIA`. | Arquitecto |
| Cobertura causal limitada a `2015_2016` | 0 temporadas con 32 variables; solo `2015_2016` con 9 variables y 301/334 partidos. Las otras 11 temporadas no tienen eventos. | Extraer eventos de las 11 temporadas restantes o declarar el alcance de la calibración. | Ingesta / Arquitecto |
| Sonda `auditar_boveda_historica.py` ausente | No existe el instrumento canónico de auditoría de cobertura; la cobertura se midió con consulta SQL de solo lectura. | Materializar la sonda y su Juez; ejecutarla contra `qbe_historico.db`. | Constructor |
| Censo ampliado de `qbe_business`: 72 hallazgos Clase IV | El Censo de Núcleo (`qbe_core`) está en 0; el barrido de §3.5 sobre `qbe_business/src` reporta 72 nodos sin etiqueta, fuera de la VÍA B del Sprint 50. | Abrir VÍA B específica para `qbe_business` o excepción formal del Director. | Arquitecto |
| Kelly y hard-caps no automatizados en `qbe_business` | El motor calcula probabilidades; la Mesa de Apuestas no dimensiona capital automáticamente. | Implementar Kelly atenuado con los hard-caps de §6. | Constructor |
| UI de coberturas y derivados ausente | La UI solo muestra 1X2; no refleja \(P_{mid}\) ni derivados. | Rediseñar la vista de la Mesa de Apuestas. | Constructor |
| `κ* = 0.35` no adoptado en producción | El óptimo empírico del barrido V6 no entró al motor (`KAPPA_NET = 0.25`); hay divergencia entre experimento y sello. | Ficha de Varianza para re-sellar; o declarar 0.25 como definitivo. | Director / Arquitecto |

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
| Prompt de asunción | `docs/KTP/RT_Pmpt.md` |
| Juez | `qbe_core/tests/test_shield_ktp_package_integrity.py` |
| Juez de Paridad Canónica | `qbe_core/tests/test_shield_canonical_parity.py` |
| Censo de Paridad Canónica | `docs/GOVERNANCE.md` §3.5; `[LN-QBE-139]`/`[LN-QBE-140]` |
| Bandeja de paridad | `docs/KTP/GL_update.md` |
| Acta activa | `docs/KTP/AKT.md` |
| Acta histórica Sprint 41 | `docs/KTP/history/AKT_2026-10-31_SPRINT-41-TRANSICION-Y-CONSISTENCIA-BG.md` |
| Acta histórica Sprint 45 | `docs/KTP/history/AKT_2026-11-01_SPRINT-45-EXPANSION-CAUSAL-Y-RESCATE-EN-VIVO.md` |
| Acta histórica Sprint 48 | `docs/KTP/history/AKT_2026-11-03_SPRINT-48-LLENADO-HISTORICO-MASIVO.md` |
| Acta histórica Sprint 50 | `docs/KTP/history/AKT_2026-11-04_SPRINT-50-REINGENIERIA-INDUSTRIAL-QBE-CORE.md` |
| Acta histórica Sprint 50 (cierre Fase 9 + enrutador dual) | `docs/KTP/history/AKT_2026-11-06_SPRINT-50-REINGENIERIA-INDUSTRIAL-QBE-CORE.md` |
| Acta histórica Sprint 51 | `docs/KTP/history/AKT_2026-11-06_SPRINT-51-META-ROUTER-MACHINE-LEARNING.md` |
| Archivo histórico | `docs/KTP/history/` |

> **Mantenimiento:** este documento se actualiza solo por consolidación formal. La versión, la fecha y el acta de origen se registran en cada cambio. No se edita para “hacer pasar” un test; si la ley cambia, se emite la Ficha de Varianza correspondiente.
