# Q-BE ECOSYSTEM — ARCHITECTURE BOOK

**Versión:** 2.0 — Four-Pillar / CQRS Edition  
**Estado:** `[ALGO-PROTECTED]` — Arquitectura Certificada Fase 4  
**Proyecto:** `Q_BE_ECOSYSTEM`  
**Autoridad Suprema:** Américo García Guerrero (Director Humano)  
**Marco:** Kybern Industrial Framework v13.5  
**Expediente:** `SPRINT-FASE4-MIGRACION-REFLEXIVA-BG-04`  
**Fecha:** 2026-10-28  
**Sustituye a:** `Q_BE_CD_WEB/docs/ARCH.md` (topología monolítica `[DEROGADA]`)

> **Aviso de procedencia.** El `ARCH.md` legado describía un monolito full-stack con un único `src/` y un único puerto 8000. Este libro describe la topología real: cuatro pilares procesales, un sustrato de persistencia transversal y un contrato CQRS de solo lectura. Las secciones monolíticas del legado quedan derogadas; los nodos canónicos se preservan por ID en el índice final.

---

## 1. TOPOLOGÍA DEL ECOSISTEMA

```text
                         ┌──────────────────────────────────────────┐
                         │            Q_BE_ECOSYSTEM                │
                         │      Monorepo de cuatro pilares          │
                         └──────────────────────────────────────────┘

  ┌────────────────────┐        ┌────────────────────┐
  │  qbe_ingestion     │        │  qbe_business      │
  │  Data Nexus        │        │  Mesa de Apuestas  │
  │  FastAPI :8002     │        │  FastAPI :8000     │
  │  scrapers/daemons  │        │  OLTP + SPA        │
  └─────────┬──────────┘        └─────────┬──────────┘
            │                             │
            │      ┌──────────────┐       │
            └─────▶│ qbe_storage  │◀──────┘
                   │ gateway 3NF  │
                   │ WAL + backup │
                   └──────┬───────┘
                          │ snapshot atómico
                          ▼
                   ┌──────────────┐
                   │ data/        │
                   │ snapshots/   │
                   │ qbe_db_snap  │
                   └──────┬───────┘
                          │ solo lectura
                          ▼
                   ┌────────────────────┐
                   │ qbe_observatory    │
                   │ Observatorio OLAP  │
                   │ FastAPI/Jinja :8001│
                   └────────────────────┘

  ┌──────────────────────────────────────────┐
  │ qbe_core — ADN matemático puro, cero I/O │
  │ Poisson · Dixon-Coles · Log-lineal · Γ   │
  │ Morfología Δ² · Cartera · Triaje         │
  └──────────────────────────────────────────┘
```

### 1.1 Los cuatro pilares

| Pilar | Puerto | Régimen | Responsabilidad | Prohibición estructural |
|---|---:|---|---|---|
| `qbe_core` | — | `[DIRGEN-STRICT]` | Matemática pura, contratos, catálogos inmutables. | No importa FastAPI, SQLAlchemy, scrapers ni `qbe_business`/`qbe_ingestion`. |
| `qbe_business` | `8000` | OLTP | Mesa de Apuestas, cartera, routers transaccionales, SPA. | No lee el histórico OLAP ni ejecuta simulaciones de backtesting. |
| `qbe_observatory` | `8001` | OLAP | Visor de backtesting, calibración, cards semánticos, Jinja2. | No escribe sobre la base viva; solo lectura del snapshot. |
| `qbe_ingestion` | `8002` | Data Nexus | Scrapers, proveedores, daemons, normalización fáctica. | No publica UI ni decide precios o carteras. |

### 1.2 `qbe_storage` — sustrato transversal

`qbe_storage` no es un quinto pilar. Es la infraestructura compartida que provee:

- `PersistenceGateway` y unit of work;
- modelos 3NF y migraciones;
- PRAGMAs transaccionales, WAL y `busy_timeout`;
- copia online y publicación atómica del snapshot;
- lectura de solo lectura para el Observatorio.

Ningún pilar abre una sesión directa contra la base viva. La única puerta de escritura es el gateway; la única puerta de lectura analítica es el snapshot.

---

## 2. CQRS: COMANDO Y CONSULTA

### 2.1 Lado de comando — Mesa de Apuestas

`qbe_business` recibe la intención del usuario, valida el contrato, ejecuta la cartera y persiste la operación. Su base es OLTP: transacciones cortas, escritura gobernada, aislamiento por solicitud.

### 2.2 Lado de consulta — Observatorio

`qbe_observatory` no consulta la base viva. Consume `data/snapshots/qbe_database_snapshot.db` mediante una conexión `mode=ro` y `PRAGMA query_only=ON`. Su universo es OLAP: lecturas largas, agregaciones, backtesting y visualización.

### 2.3 Publicación atómica del snapshot

El publicador:

1. verifica que la base origen esté íntegra;
2. ejecuta `sqlite3.Connection.backup` hacia un archivo temporal en el mismo volumen;
3. valida `PRAGMA integrity_check`;
4. reemplaza el destino con `os.replace`, operación atómica en el mismo sistema de archivos;
5. publica la ruta y el sello de versión.

El Observatorio nunca ve una publicación a medias. Si el snapshot falta o está corrupto, falla de forma ruidosa; no cae a la base viva.

### 2.4 Invariantes CQRS

- `qbe_business` no lee snapshots para tomar decisiones de cartera.
- `qbe_observatory` no ejecuta `INSERT`, `UPDATE`, `DELETE` ni `CREATE`.
- `qbe_ingestion` no escribe fuera del gateway.
- `qbe_core` no conoce ninguna base de datos.
- El snapshot es el único contrato entre OLTP y OLAP.

---

## 3. FRONTERAS MODULARES

### 3.1 `qbe_core`

Contiene el ADN matemático y los modelos puros. Su contrato es entrada → salida, sin estado, sin reloj, sin red, sin disco. Los catálogos inmutables —estrategias, altitudes, constantes— viven aquí porque son ley, no configuración de entorno.

### 3.2 `qbe_business`

Contiene la fachada FastAPI, los routers de ligas, mercados, cartera, exportación, admin y soberano, y la SPA. Su dependencia permitida es `qbe_core` + `qbe_storage`. No importa `qbe_observatory` ni `qbe_ingestion`.

### 3.3 `qbe_observatory`

Contiene la app FastAPI/Jinja2, los adaptadores de solo lectura, los servicios de snapshot y el motor de simulación. Su dependencia permitida es `qbe_core` + `qbe_storage` (solo contratos) + snapshot. No importa routers de la Mesa de Apuestas.

### 3.4 `qbe_ingestion`

Contiene scrapers, proveedores, normalizadores, daemons y el Data Nexus. Su dependencia permitida es `qbe_storage` + `qbe_core` (normalización pura). No importa la UI ni el motor de cartera.

### 3.5 Matriz de dependencias

| Desde → Hacia | `qbe_core` | `qbe_storage` | `qbe_business` | `qbe_observatory` | `qbe_ingestion` |
|---|:---:|:---:|:---:|:---:|:---:|
| `qbe_core` | — | ✗ | ✗ | ✗ | ✗ |
| `qbe_storage` | ✓ contratos | — | ✗ | ✗ | ✗ |
| `qbe_business` | ✓ | ✓ | — | ✗ | ✗ |
| `qbe_observatory` | ✓ | ✓ contratos | ✗ | — | ✗ |
| `qbe_ingestion` | ✓ | ✓ | ✗ | ✗ | — |

---

## 4. CONTRATOS DE DATOS

### 4.1 Evidencia fáctica

La ingesta publica hechos estructurados con procedencia, sello temporal y estado de evidencia. Un campo ausente no se rellena: se marca `SIN EVIDENCIA` y se propaga la causa.

**Contrato de entrada del núcleo (`E-50.1`, `[VAULT-CORE-001]`).** La frontera `qbe_ingestion → qbe_core` distingue dos clases de insumo y no las mezcla:

| Clase | Insumos | Ausencia |
|:---:|---|---|
| **C-1 · Evidencia estadística** | `gf`, `gc`, `xg`, `xga`, `V01…V32` | `InsufficientDataException` o `S(I)=0`. Prohibido todo default literal. |
| **C-2 · Operador contextual** | `Δalt`, `Δrest`, `q_mod`, `Δγ_plaza` | Operador **no aplicado** y declarado en la traza. Nunca `0.0` fabricado. |

La contravención se clasifica como Clase I (Fabricación Sintética, `GOVERNANCE.md §1.1.3`). El motor GSL-3D v2 (`[LN-QBE-039]` §7.6) exige además la **matriz causal** $M\in\mathbb{R}^{n\times32}$ por club ($n\ge10$, pre-kickoff): la ingesta que sólo publique agregados escalares no habilita proyección ortogonal alguna y el partido se resuelve con `S(I)=0`.

### 4.2 Contrato de 32 variables

El catálogo vigente es `[LN-QBE-120]`: 6 dimensiones y 32 variables (`V01`…`V32`). El DTO conserva el nombre histórico `variables_44` por compatibilidad de red, pero su cardinalidad es 32. El contrato visible no se renombra sin Ficha de Varianza.

### 4.3 Snapshot

El snapshot publica una versión coherente de la base para lectura analítica. Incluye metadatos de versión, fecha de materialización y checksum. El Observatorio lo trata como inmutable durante la sesión.

### 4.4 Contratos de API

- `qbe_business:8000` — comandos y consultas transaccionales de la Mesa.
- `qbe_observatory:8001` — consultas analíticas, backtesting y visor.
- `qbe_ingestion:8002` — estado, drift, administración de daemons y datos de entrada.

Cada servicio expone `/health` y falla con un código distinto de 200 si su dependencia crítica no está disponible.

---

## 5. AISLAMIENTO DE FALLOS

| Falla | Efecto permitido | Efecto prohibido |
|---|---|---|
| Observatorio caído | La Mesa sigue operando; el visor no responde. | Bloquear la cartera o escribir en OLTP para “compensar”. |
| Ingesta caída | La Mesa entra en cuarentena de datos y no apuesta. | Fabricar cuotas, xG o marcadores. |
| Snapshot corrupto | El Observatorio falla ruidosamente. | Leer la base viva o servir un snapshot parcial. |
| Error matemático en `qbe_core` | Alto al Fuego y Ficha de Varianza. | Fallback silencioso o clamp arbitrario. |
| Base OLTP bloqueada | Reintento gobernado y error visible. | Escritura directa desde otro pilar. |

La separación de procesos y puertos es parte de la resiliencia. No se comparte memoria, sesión ni archivo de trabajo entre pilares.

---

## 6. DESPLIEGUE Y OPERACIÓN

### 6.1 Puertos canónicos

| Servicio | Host | Puerto | Modo |
|---|---|---:|---|
| Mesa de Apuestas | `127.0.0.1` | `8000` | OLTP |
| Observatorio | `127.0.0.1` | `8001` | OLAP, solo lectura |
| Data Nexus | `127.0.0.1` | `8002` | Ingesta |

### 6.2 Arranque

Cada pilar tiene su propio entrypoint y su propio proceso. No existe un `run_app.py` único que levante todo el ecosistema. El despliegue local se coordina con el verificador E2E y variables de entorno explícitas.

### 6.3 Observabilidad

- `/health` por pilar.
- Estado de daemons y drift en el Data Nexus.
- Sello de snapshot y estado de la última publicación.
- Logs estructurados, nunca secretos ni datos personales.
- `SIN EVIDENCIA` como estado de primera clase, no como error genérico.

---

## 7. SEGURIDAD Y SECRETOS

1. `.env` nunca se versiona; `.env.example` documenta las claves.
2. Las rutas de base y tokens se resuelven por entorno, no por hardcode.
3. El Observatorio abre la base en solo lectura; no recibe credenciales de escritura.
4. Los scrapers no escriben fuera del gateway.
5. Los logs no incluyen tokens, cookies ni payloads sensibles.

---

## 8. MAPA DE MIGRACIÓN LEGADO → ECOSISTEMA

| Ruta legada | Ruta canónica | Pilar |
|---|---|---|
| `src/core/` | `qbe_core/src/core/` | `qbe_core` |
| `src/models/` | `qbe_core/src/models/` | `qbe_core` |
| `src/storage/` | `qbe_storage/src/storage/` | `qbe_storage` |
| `src/web/` | `qbe_business/src/web/` | `qbe_business` |
| `src/ingestion/` | `qbe_ingestion/src/ingestion/` | `qbe_ingestion` |
| `scripts/daemons/` | `qbe_ingestion/src/ingestion/daemons/` | `qbe_ingestion` |
| `scripts/laboratorio/` | `scripts/laboratorio/` | Laboratorio |
| `scripts/investigacion/` | `scripts/investigacion/` | Investigación |
| `data/qbe_database.db` | `data/snapshots/qbe_database_snapshot.db` (solo lectura) | `qbe_storage` / `qbe_observatory` |

Las rutas legadas solo pueden aparecer en este mapa o en un bloque de procedencia. No son rutas operativas.

### 8.1 Activos de laboratorio e investigación

- `scripts/laboratorio/` conserva 10 pipelines CLI y su `__init__.py`; `scripts/investigacion/` conserva 3 instrumentos y su `__init__.py`.
- El paquete raíz `scripts/__init__.py` evita la colisión con el paquete `scripts` del Observatorio.
- Diez scripts tienen preflight de importación y `--help` en verde; tres deudas se declaran en `scripts/README.md` (`src.core.metrics`, `src.core.sovereign.h2h_provider` y `xgboost` opcional). No se inventaron shims.
- Los activos de `data/` se versionan como evidencia fáctica: cinco cachés, prior 2025, catálogo de staging, CSV de 97 partidos y matriz de investigación. Las bases `.db` y sus WAL/SHM se ignoran y no se copiaron.
- Los scripts abren el gateway en solo lectura; para apuntarlos al snapshot se usa `DATABASE_URL=sqlite:///data/snapshots/qbe_database_snapshot.db`.

---

## 9. DEUDAS Y TOMBSTONES

| Elemento legado | Estado | Nota |
|---|---|---|
| Monolito `Q_BE_CD_WEB` | `[DEROGADO]` | Sustituido por cuatro pilares. |
| `run_app.py` único | `[DEROGADO]` | Cada pilar tiene entrypoint propio. |
| Base viva como fuente del visor | `[DEROGADO]` | El visor consume snapshot atómico. |
| Catálogo 44V | `[DEROGADO]` | Vigente: 32V (`[LN-QBE-120]`). |
| `src/` plano | `[DEROGADO]` | Sustituido por `qbe_*/src/`. |
| `src.core.metrics` | `[DEUDA]` | `SyntheticMetricsEngine` no migrado; declarado en `scripts/README.md`. |
| `src.core.sovereign.h2h_provider` | `[DEUDA]` | Proveedor H2H no migrado; su destino exige decisión de pilar. |

---

## 10. ÍNDICE DE NODOS ARQUITECTÓNICOS

| ID | Nodo / Título | Pilar | Estado |
|---|:---:|---|:---:|
| `[ARCH-1.3.1]` | Rueda de Inferencia Gemini y Rotador de Llaves Multi-Proyecto [ARCH-PILLAR] | `qbe_core` | SELLADO |
| `[ARCH-1.3.2]` | Modelo Gemini Canónico Inmutable (`gemini-3.6-flash`) [ARCH-PILLAR] [ANTI-BUG] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.3.3]` | Gestor Contable Local de Cuotas y Circuit Breaker [ARCH-PILLAR] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.3.4]` | GeminiCognitiveGateway y Ledger Contable de Inferencia [ARCH-PILLAR] | `qbe_storage` | SELLADO |
| `[ARCH-1.3.5]` | Retiro y Deprecación Definitiva de Rutas Legacy en routes/portfolio.py [ARCH-PILLAR] | `qbe_business` | SELLADO |
| `[ARCH-1.4.0]` | Inversión de Carga Neuro-Simbólica (FotMob Primary Sensor) [ARCH-PILLAR] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.4.1]` | Resiliencia Defensiva del Scraper de Mercado [ARCH-PILLAR] [ANTI-BUG] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.4.1-B]` | Sensor de Estados Temporales Fácticos (Live vs. Finished en FotMob) [ARCH-PILLAR] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.4.2]` | Pipeline de Ingesta Soberana de Tabla de Posiciones (Liga MX FMF) [ARCH-PILLAR] [GOVERNANCE-01] | `qbe_observatory` | SELLADO |
| `[ARCH-1.4.3]` | Motor de Extracción Focalizada de Cuotas Caliente.mx [ARCH-PILLAR] [ANTI-BUG] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.4.4]` | Ingesta Estructurada de Forma (5P) vía FotMob Next.js (__NEXT_DATA__) [ARCH-PILLAR] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.4.5]` | Robustez de Parsers DOM y Expresiones Multilínea [ANTI-BUG] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.4.5-B]` | Endpoints Desacoplados de Soberanía y Mercados [ARCH-PILLAR] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.4.5-C]` | Unificación del Controlador Financiero REST en markets.py [ARCH-PILLAR] | `qbe_storage` | SELLADO |
| `[ARCH-1.4.6]` | Topología de Ingesta Multi-Operador y Persistencia Relacional [ARCH-PILLAR] | `qbe_observatory` | SELLADO |
| `[ARCH-1.4.6-C]` | Control de Errores y Telemetría de Extracción [ARCH-PILLAR] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.4.6-D]` | Expansión Universal de Acordeones de Fecha y Virtual Scroll en Betway [ARCH-PILLAR] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.4.6-E]` | Filtro de Descontaminación de Filas de Evento en Caliente [ARCH-PILLAR] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.4.6-F]` | Sensor de Ingesta Novibet.mx por Intercepción de Feed JSON [ARCH-PILLAR] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.4.7]` | Contrato de Telemetría Extendida en FixtureSnapshot.matches_json [ARCH-PILLAR] | `qbe_observatory` | SELLADO |
| `[ARCH-1.4.7-B]` | Jerarquía y Retrocompatibilidad de Cuotas por Defecto [ARCH-PILLAR] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.4.8]` | Despacho Global de Mesa de Apuestas y Descarte Temprano [ARCH-PILLAR] | `qbe_storage` | SELLADO |
| `[ARCH-1.4.8-B]` | Exposición del Objeto `consenso_mercado` en LiveBoardOut [ARCH-PILLAR] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.4.9]` | Módulo de Contratos Matemáticos Inmutables (portfolio_math.py) [ARCH-PILLAR] | `qbe_core` | SELLADO |
| `[ARCH-1.4.10]` | Despacho Financiero 3NF en markets.py [ARCH-PILLAR] | `qbe_observatory` | SELLADO |
| `[ARCH-1.4.11]` | Nodo canónico | `qbe_core` | VIGENTE |
| `[ARCH-1.4.12]` | Servicio del Centro de Control y Despacho de Tareas Administrativas [ARCH-PILLAR] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.4.12-B]` | Detector de Deriva y Semáforo de Desactualización de Fuentes [ARCH-PILLAR] | `qbe_observatory` | SELLADO |
| `[ARCH-1.4.12-C]` | Reestructuración de Cadenas de Ingesta Temporal y Whitelist Ampliada [ARCH-PILLAR] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.4.13]` | Guarda de Resiliencia ante Base de Datos Vacía en Live Board [ARCH-PILLAR] | `qbe_observatory` | SELLADO |
| `[ARCH-1.4.14]` | Denominador Fáctico de Cartelera en Macro KPIs [ARCH-PILLAR] | `qbe_observatory` | SELLADO |
| `[ARCH-1.4.15]` | Contrato de Disponibilidad Dinámica de Operadores en Ventanilla [ARCH-PILLAR] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.4.16]` | Contrato de Atribución Unívoca de Operador en Boletos [ARCH-PILLAR] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.4.16-B]` | Contrato de Horario Fáctico y Rótulo de Cobertura en el Resumen de Asignación [ARCH-PILLAR] | `qbe_business` | SELLADO |
| `[ARCH-1.4.17]` | Contrato de la Distribución Fiduciaria Contraída en el Pipeline de Cartera [ARCH-PILLAR] | `qbe_storage` | SELLADO |
| `[ARCH-1.4.18]` | Algoritmo de Sizing Monótono Proporcional a la Certeza [ARCH-PILLAR] | `qbe_core` | SELLADO |
| `[ARCH-1.4.19]` | Monotonía Estricta Post-Dutching en PortfolioEngine.build_plan() [ARCH-PILLAR] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.4.20]` | Contrato de Datos del Optimizador de Masa P' en progol_math.py [ARCH-PILLAR] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.4.21]` | Arquitectura de Ingesta Just-In-Time (JIT) Multi-Torneo [ARCH-PILLAR] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.4.22]` | Disparo JIT de Descubrimiento en centinela_progol.py [ARCH-PILLAR] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.4.23]` | Sensor de Ingesta Oficial de Liga Premier FMF (ligapremier.mx) [ARCH-PILLAR] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.4.24]` | Contrato Hexagonal de Proveedores de Ingesta Pura y DTOs (Capa 1) [ARCH-PILLAR] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.4.25]` | Módulo de Normalización, Jerga y Desambiguación (`src/normalization/`) [ARCH-PILLAR] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.4.26]` | Motor de Memoria Histórica y Kernel H2H (`qbe_core/src/core/sovereign/`) [ARCH-PILLAR] | `qbe_core` | SELLADO |
| `[ARCH-1.4.27]` | Módulo de Servicios de Composición y Orquestación (`src/services/`) [ARCH-PILLAR] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.4.28]` | Adaptador de Despacho Web y Telemetría del Centro de Control [ARCH-PILLAR] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.4.29]` | Purga Total In-Process de la Bóveda 3NF (Centro de Control) [ARCH-PILLAR] | `qbe_storage` | SELLADO |
| `[ARCH-1.4.30]` | Módulo Funcional SimplexMorphology y Controlador UI de Masa Γ [ARCH-PILLAR] | `qbe_business` | SELLADO |
| `[ARCH-1.4.31]` | Suspensión de Inferencia LLM en Inspección y Contrato de Radiografía Forense [ARCH-PILLAR] | `qbe_business` | SELLADO |
| `[ARCH-1.4.32]` | Contenedor de Acciones de Tarjeta y Congelamiento de Cuotas [ARCH-PILLAR] | `qbe_storage` | SELLADO |
| `[ARCH-1.4.33]` | Contenedor de Factores Latentes Tridimensionales y Motor GSL-3D [ARCH-PILLAR] | `qbe_observatory` | SELLADO |
| `[ARCH-1.4.34]` | Sonda Diagnóstica de Coherencia Relacional y Pre-Vuelo del Constructor (CLI Auditor) [ARCH-PILLAR] | `qbe_observatory` | SELLADO |
| `[ARCH-1.4.35]` | Contrato de Cartera Vacía y Conmutador de Slates en Mesa de Apuestas [ARCH-PILLAR] | `qbe_observatory` | SELLADO |
| `[ARCH-1.4.36]` | Sensor de Ingesta Histórica BetExplorer y Cortes Progresivos Anti-Leakage [ARCH-PILLAR] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.4.37]` | Parámetro de Cobertura Dinámica δ en el Pipeline de Cartera y DTOs [ARCH-PILLAR] | `qbe_core` | SELLADO |
| `[ARCH-1.4.38]` | Endpoint de Calibración Histórica y Visor de Backtesting [ARCH-PILLAR] | `qbe_observatory` | SELLADO |
| `[ARCH-1.4.39]` | Motor de Homologación Histórica Opta/H2H y Reconstrucción Progresiva [ARCH-PILLAR] [GOVERNANCE-01] | `qbe_observatory` | SELLADO |
| `[ARCH-1.4.41]` | Contrato Único de Escala xG y Extirpación de la Escala Artificial en la Ingesta [ARCH-PILLAR] [GOVERNANCE-01] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.4.42]` | Micro-HUD de Atribución Factorial y DTO de Inspección de 44 Variables [ARCH-PILLAR] | `qbe_observatory` | SELLADO |
| `[ARCH-1.4.42-B]` | Tolerancia de Tipos de Insumo con Unidades en DTO de Variables (44V) [ANTI-BUG] | `qbe_business` | SELLADO |
| `[ARCH-1.4.43]` | Persistencia Blindada de la Evidencia en Vivo, Propagación del Sello de Procedencia y DTOs de Inspección [ARCH-PILLAR] | `qbe_observatory` | SELLADO |
| `[ARCH-1.4.44]` | Proveedor H2H Unificado de Corpus Congelado, Sello Opta de Origen y Telemetría Dimensional del Acordeón Forense [ARCH-PILLAR] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.4.45]` | Arquitectura de Aislamiento Sandbox y Diagnóstico CLI-First [ARCH-PILLAR] | `qbe_business` | SELLADO |
| `[ARCH-1.4.46]` | Motor de Simulación Retrospectiva de Rentabilidad y Tablero Fiduciario CLI [ARCH-PILLAR] | `qbe_storage` | SELLADO |
| `[ARCH-1.4.47]` | Sandbox Ataque & Defensa: Colisión Cruzada y Tablero Bipartito CLI [ARCH-PILLAR] | `qbe_storage` | SELLADO |
| `[ARCH-1.4.48]` | Arquitectura del Laboratorio de Contexto y Shocks y Derivación del Vector Contextual C [ARCH-PILLAR] | `qbe_storage` | SELLADO |
| `[ARCH-1.4.49]` | Arquitectura del Laboratorio de Trayectoria y Dinámica Temporal [ARCH-PILLAR] | `qbe_storage` | SELLADO |
| `[ARCH-1.4.50]` | Arquitectura del Laboratorio de Volumen Territorial y Portería [ARCH-PILLAR] | `qbe_storage` | SELLADO |
| `[ARCH-1.4.51]` | Arquitectura del Laboratorio de Micro-Dinámicas y Fricciones Especiales [ARCH-PILLAR] | `qbe_storage` | SELLADO |
| `[ARCH-1.4.52]` | Extensión CLI del Sandbox de Rentabilidad para Políticas de Exclusión [ARCH-PILLAR] | `qbe_observatory` | SELLADO |
| `[ARCH-1.4.53]` | Saneamiento Vol. II: Cota Underdog, Escudo de Altitud y Parámetros Gobernantes del Simulador [ARCH-PILLAR] | `qbe_observatory` | SELLADO |
| `[ARCH-1.4.54]` | Blindaje de Dominancia P′ ≥ 50%, Altitud Atlante y Saneamiento Cromático de la Tabla Meso [ARCH-PILLAR] | `qbe_business` | SELLADO |
| `[ARCH-1.4.55]` | Proveedores Canónicos de Insumos y Orquestación Anidada de `insumos_factivados` [ARCH-PILLAR] | `qbe_core` | SELLADO |
| `[ARCH-1.4.55-B]` | Aduana de Lectura Soberana: Proyección ORM → Diccionarios Planos (`qbe_core/src/core/sovereign_reads.py`) [ARCH-PILLAR] | `qbe_observatory` | SELLADO |
| `[ARCH-1.4.56]` | Materialización Anidada de los Cinco Pilares en el Generador Sellado y Resguardo WORM del Lote [ARCH-PILLAR] | `qbe_core` | SELLADO |
| `[ARCH-1.4.57]` | Frontera de Presentación de los Cards Polimórficos: `variables_44` como Única Fuente y Deuda Declarada de `insumos_factivados` [ARCH-PILLAR] | `qbe_core` | SELLADO |
| `[ARCH-1.4.58]` | Telemetría Dimensional en el DTO, 19.ª Tarea del Centro de Control y Sonda de Completitud Fáctica 44V [ARCH-PILLAR] | `qbe_observatory` | SELLADO |
| `[ARCH-1.4.59]` | Centinela de Macro-Estadísticas FotMob y Congelación Idempotente del Artefacto `cache_macro_stats_liga_mx_2026.json` [ARCH-PILLAR] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.4.60]` | Inyección Macro-Torneal como Aduana de Exhibición y Derivación Dinámica de Taxonomías desde el Catálogo Único | `qbe_core` | SELLADO |
| `[ARCH-1.4.61]` | Taxonomías Derivadas en Import-Time y Régimen de Auxiliares `AUX_*` (Cierre de la Deriva Nominal 44V) | `qbe_core` | SELLADO |
| `[ARCH-1.4.62]` | Fase C de Vitrina: Retiro del Régimen 44V en la Capa Visible y Alineación de `sandbox_micro_dinamicas_pipeline` al Catálogo de 32 Variables | `qbe_observatory` | SELLADO |
| `[ARCH-1.4.63]` | Saneamiento de Vitrina: Derogación de la Tabla Duplicada por Dimensión, Soporte Forense Único y Normalización de la Barra de Posesión | `qbe_core` | SELLADO |
| `[ARCH-1.4.64]` | Delegación del Orden Fiduciario del Visor a la Función Pura Canónica y Resolución Declarada del Desnivel de Altitud | `qbe_observatory` | SELLADO |
| `[ARCH-1.4.65]` | Vitrina de Muestra Declarada: Selector Calibrada/Global en el Visor de Calibración | `qbe_observatory` | SELLADO |
| `[ARCH-1.4.66]` | Sandbox de Arquetipos y Vectores: Instrumento CLI-First de Lectura Pura para la Inducción de Firmas por Clase | `qbe_storage` | SELLADO |
| `[ARCH-1.4.67]` | Matriz Canónica de Investigación: Publicación No-Leakage de Cuatro Zonas Delegada al Reporte de Calibración | `qbe_observatory` | SELLADO |
| `[ARCH-1.4.68]` | Motor Cliente de Cuatro Capas del Visor de Calibración: Proyección Pura, Propagación Atómica y Transparencia de Denominador | `qbe_observatory` | SELLADO |
| `[ARCH-1.4.69]` | Artefacto Congelado del Prior de Apertura 2025 y Resolvedor de Insumos con Mezcla | `qbe_ingestion` | SELLADO |
| `[ARCH-1.4.70]` | Instrumento CLI-FIRST de Minería de Shannon y Árbol Esparso de Veto | `qbe_business` | SELLADO |
| `[ARCH-1.4.71]` | Arquitectura del Parser Offline MHTML y Pipeline de Extracción Multianual [ARCH-PILLAR] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.4.72]` | Pipeline de Inyección Histórica Multianual y Reflection DDL [ARCH-PILLAR] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.4.73]` | Extractor Histórico Masivo de FotMob | `qbe_ingestion` | SELLADO |
| `[ARCH-1.4.74]` | Topología y Subsistema Documental de Transferencia KTP [ARCH-PILLAR] | `docs` | SELLADO |
| `[ARCH-1.5.0]` | Central Persistence Gateway y Unidad de Trabajo (Unit of Work) [DIRGEN-SEALED] [ARCH-PILLAR] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.5.0-B]` | Aislamiento de Persistencia del Canal Gateway en The Shield [ARCH-PILLAR] [GOVERNANCE-01] | `qbe_storage` | SELLADO |
| `[ARCH-1.5.1]` | Esquema Relacional 3NF Multi-Torneo — Especificación Canónica de Columnas [ARCH-PILLAR] [DIRGEN-STRICT] | `qbe_storage` | SELLADO |
| `[ARCH-1.5.1-C]` | Tablas: `slates` y `slate_items` | `qbe_core` | SELLADO |
| `[ARCH-1.5.2]` | Persistencia Local en Base de Datos SQLite [ARCH-PILLAR] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.5.3]` | Catálogo de Equipos y Escudos en Base de Datos Local (`teams`) [ARCH-PILLAR] [ANTI-BUG] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.5.3-B]` | Política de Servido de Activos Visuales y Mitigación Anti-Hotlinking [ARCH-PILLAR] [ANTI-BUG] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.5.4]` | Espejeo Físico de Aliases y Axioma Anti-Archivos Fantasma [ARCH-PILLAR] [GOVERNANCE-01] | `qbe_business` | SELLADO |
| `[ARCH-1.5.5]` | Modelo de Datos Relacional para Aprendizaje Cuantitativo (Puente PM-FACE) [ARCH-PILLAR] [BIZ-LOGIC] | `qbe_observatory` | SELLADO |
| `[ARCH-1.5.6]` | Ledger Histórico de Momios y Circunstancias Pre-Partido (Backtesting Bridge) [BIZ-LOGIC] [PM-FACE] | `qbe_observatory` | SELLADO |
| `[ARCH-1.5.7]` | Bóveda Incremental de Emblemas de Ligas y Competiciones [ARCH-PILLAR] | `qbe_storage` | SELLADO |
| `[ARCH-1.5.8]` | Parámetros Canónicos de Normalización y Bóveda de Activos [ARCH-PILLAR] [ANTI-BUG] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.5.9]` | Módulo Centinela Pre-Kickoff: Sharp Money & Semantic Shock [BACKLOG] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.5.10]` | Bóveda de Activos de Operadores de Casino [ARCH-PILLAR] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.5.10-B]` | Bóveda de Emblemas de Operadores Oficiales y Anti-Hotlinking [ARCH-PILLAR] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.5.11]` | Catálogo de Jerga y Aliases Globales de Progol (PROGOL_GLOBAL_ALIASES) [ARCH-PILLAR] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.5.12]` | Aprovisionador JIT de Ligas y Bóveda Soberana de Activos de Clubes (`src/normalization/`) [ARCH-PILLAR] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.6.0]` | Arquitectura del Live Board Reactivo y Sincronización SQLite [ARCH-PILLAR] | `qbe_observatory` | SELLADO |
| `[ARCH-1.6.1]` | Política de Presentación Centrada en el Inversionista (Zero Technical Leakage) [ARCH-PILLAR] [UX-MANDATE] | `qbe_storage` | SELLADO |
| `[ARCH-1.6.2]` | Ventana Operativa de Cartelera y Ciclo de Vida de Cuotas [ARCH-PILLAR] [BIZ-LOGIC] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.6.2-B]` | Ancla Temporal Canónica, Cuarentena por Staleness y Orden Topológico Materializado [ARCH-PILLAR] [GOVERNANCE-01] | `qbe_observatory` | SELLADO |
| `[ARCH-1.6.3]` | Nodo canónico | `qbe_core` | VIGENTE |
| `[ARCH-1.6.4]` | Desacoplamiento Absoluto de Scraping en el Plano Web (Bus de Datos SQLite) [ARCH-PILLAR] [PERF-MANDATE] | `qbe_storage` | SELLADO |
| `[ARCH-1.6.5]` | Pipeline Adaptador de Portafolio (src/pipeline/adapter.py) [ARCH-PILLAR] | `qbe_observatory` | SELLADO |
| `[ARCH-1.6.6]` | Aislamiento de Hilos y Timeouts en Ingesta Playwright [ARCH-PILLAR] [ANTI-BUG] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.6.7]` | Endpoints Atómicos de Refresco Desacoplado [ARCH-PILLAR] [PERF-MANDATE] (H4) | `qbe_observatory` | SELLADO |
| `[ARCH-1.6.8]` | Topología Multi-Jornada y Caché Particionado por Slate [ARCH-PILLAR] [PERF-MANDATE] | `qbe_observatory` | SELLADO |
| `[ARCH-1.6.9]` | Herencia Dinámica de la Cláusula de Pago Anticipado en Boletos [BIZ-LOGIC] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.6.10]` | Herramienta de Saneamiento SQLite y Protocolo de Inferencia On-Demand [ARCH-PILLAR] | `qbe_observatory` | SELLADO |
| `[ARCH-1.6.10-B]` | Purga Atómica y Limpieza Relacional 3NF [ARCH-PILLAR] | `qbe_observatory` | SELLADO |
| `[ARCH-1.6.11]` | Servicio de Distribución Soberana y Sincronización en BD (`qbe_storage/src/storage/distribution_sync.py`) [DIRGEN-SEALED] | `qbe_observatory` | SELLADO |
| `[ARCH-1.6.12]` | Ingesta Dinámica de Calendario Completo sin Alambrado [DIRGEN-SEALED] [GOVERNANCE-01] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.6.13]` | Motor de Ingesta Total de Temporada y Reconstrucción Histórica [DIRGEN-SEALED] [GOVERNANCE-01] | `qbe_observatory` | SELLADO |
| `[ARCH-1.6.13-B]` | Unicidad Estricta de Encuentros Reprogramados [ARCH-PILLAR] | `qbe_observatory` | SELLADO |
| `[ARCH-1.6.13-C]` | Extracción de Tablas Desagregadas por Sede e Inyección H2H en Centinela Deportivo [ARCH-PILLAR] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.6.14]` | Nodo canónico | `qbe_core` | VIGENTE |
| `[ARCH-1.6.15]` | Resolución Dinámica de Jornada Activa en Sensores de Mercado [ARCH-PILLAR] | `qbe_observatory` | SELLADO |
| `[ARCH-1.6.15-B]` | Desacoplamiento Cronológico en Sensores de Mercado [ARCH-PILLAR] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.6.15-C]` | Apertura Dinámica de Jornada en Live Board (sync_service.py) [ARCH-PILLAR] | `qbe_storage` | SELLADO |
| `[ARCH-1.6.16]` | Política de Depuración y Archivado de Sondas Temporales [ARCH-PILLAR] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.6.17]` | Resiliencia de Sensores ante Acordeones de Fechas Calendario (Betway) [ARCH-PILLAR] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.6.18]` | Resiliencia de Navegación de Torneo en Sensores de Mercado [ARCH-PILLAR] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.6.19]` | Desacoplamiento Multi-Liga del Centinela Deportivo [ARCH-PILLAR] | `qbe_observatory` | SELLADO |
| `[ARCH-1.6.19-A]` | Nodo canónico | `qbe_core` | VIGENTE |
| `[ARCH-1.6.19-B]` | Ingesta y Parser Genérico de Temporadas FotMob [ARCH-PILLAR] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.6.20]` | Actualización de Endpoint de Búsqueda FotMob (/searchapi/suggest) [ARCH-PILLAR] | `qbe_ingestion` | SELLADO |
| `[ARCH-1.6.21]` | Frontera de Competición y Resolución Dinámica en Sensores de Mercado [ARCH-PILLAR] | `qbe_observatory` | SELLADO |
| `[ARCH-1.6.22]` | Materialización del Ensemble Convexo y del Puente de Δ_epist Real (`qbe_core/src/core/sovereign_pipeline.py`, `qbe_storage/src/storage/distribution_sync.py`) [ARCH-PILLAR] | `qbe_storage` | SELLADO |
| `[ARCH-1.7.0]` | Lanzador de Servidor con Sonda de Salud (run_app.py) [ARCH-PILLAR] (H10) | `qbe_ingestion` | SELLADO |
| `[ARCH-1.7.1]` | Piso Mínimo de Ventanilla ($2.00 MXN) y Escalamiento Proporcional [BIZ-LOGIC] [ALGO-PROTECTED] (H1) | `qbe_ingestion` | SELLADO |
| `[ARCH-1.4.78]` | Enrutador y Fachada de Desempeño Híbrido (`qbe_observatory`): `/desempeno`, Redirect 302 y DTOs de Desempeño [ARCH-PILLAR] | `qbe_observatory` | SELLADO |

_Total: 144 identificadores._


---

## 11. TRAZABILIDAD

- Fuente: `Q_BE_CD_WEB/docs/ARCH.md`.
- Migración: reescritura de topología, reanclaje de rutas y preservación de IDs.
- Juez: `qbe_core/tests/test_shield_ecosystem_governance.py` (invariante de cuatro pilares).
- Cierre: suite completa y manifiesto de Fase 4.

---

## 12. PARSER OFFLINE MHTML

### [ARCH-1.4.71] Arquitectura del Parser Offline MHTML y Pipeline de Extracción Multianual [ARCH-PILLAR]
* **Módulo:** `qbe_ingestion/src/ingestion/parsers/parsear_footystats_mhtml.py`.
* **Especificación CLI:**
  - `python -m qbe_ingestion.src.ingestion.parsers.parsear_footystats_mhtml --verificar-solo` (valida integridad de las 12 carpetas sin escribir).
  - `python -m qbe_ingestion.src.ingestion.parsers.parsear_footystats_mhtml --temporada 2018_2019` (procesa una temporada).
  - `python -m qbe_ingestion.src.ingestion.parsers.parsear_footystats_mhtml --todas` (procesa las 12 temporadas completas).
* **Dependencias:** Librería estándar `email`, `re`, `json`, `pathlib` y `bs4` (`BeautifulSoup` con `html.parser`).
* **[SHIELD]:** `qbe_ingestion/tests/test_shield_mhtml_parser_and_season_integrity.py`

---

## 13. PIPELINE DE INYECCIÓN HISTÓRICA

### [ARCH-1.4.72] Pipeline de Inyección Histórica Multianual y Reflection DDL [ARCH-PILLAR]
* **Módulo de Carga:** `qbe_ingestion/src/ingestion/loaders/load_historical_footystats.py`.
* **Especificación CLI:** `--run` (ejecuta la carga completa), `--temporada YYYY_YYYY` (carga selectiva).
* **Dependencias:** SQLAlchemy Core (para ejecución DML/DDL de alta velocidad, evadiendo el overhead del ORM de sesión en inserciones masivas).
* **Destino:** `qbe_observatory/data/qbe_historico.db` (Bóveda OLAP).
* **Excepción CQRS autorizada:** carga bulk directa sobre tablas `historical_*`, transacción `BEGIN IMMEDIATE`, backup WORM previo y `PRAGMA quick_check` al cierre. No toca `matches`, `sovereign_distributions` ni `match_telemetry`.
* **[SHIELD]:** `qbe_ingestion/tests/test_shield_historical_load_integrity.py`

---

## 14. SUBSISTEMA DOCUMENTAL DE TRANSFERENCIA KTP

### [ARCH-1.4.74] Topología y Subsistema Documental de Transferencia KTP [ARCH-PILLAR]
* **Ubicación Canónica:** `docs/KTP/`.
* **Naturaleza:** subsistema documental de gobierno; no ejecuta lógica de negocio, no abre conexiones de base de datos y no cruza fronteras CQRS. Su única función es preservar y transferir la intención legislada entre turnos.
* **Especificación de Artefactos:**
  - `KTP_Guide.md`: Guía de procedimiento y FSM de transferencia.
  - `KDB.md`: Base de datos de conocimiento y mapa de arquitectura del ecosistema.
  - `AKT_Pmpt.md`: Prompt de extracción de contexto saliente.
  - `AKT.md`: Estado dinámico del sprint vigente.
  - `KDB_Act_Pmpt.md`: Prompt de consolidación y versionado en disco.
  - `RT_Pmpt.md`: Prompt de asunción de mando y continuidad para el Arquitecto entrante.
  - `history/`: Registro inmutable de transiciones históricas archivadas.
* **Contrato de Integridad:** los seis archivos rectores deben existir físicamente y superar el umbral mínimo de contenido; `history/` debe existir incluso cuando aún no contiene actas. El archivo de `AKT.md` se realiza por copia y reinicio, nunca por sustracción del activo.
* **Frontera:** `qbe_core` no consume estos documentos en tiempo de ejecución; el Juez documental vive en `qbe_core/tests/` como guardián de la Base de Gobierno, sin introducir I/O en el núcleo matemático.
* **[SHIELD]:** `qbe_core/tests/test_shield_ktp_package_integrity.py`
* **Deuda documental declarada:** `[ARCH-1.4.73]` figura sellado en la tabla maestra y en `docs/ID_REGISTRY.md`, pero carece de sección de cuerpo en este libro. Se preserva su ID y su denominación; la deuda se declara para una reconciliación posterior y no se reasigna.

---

## 15. ESQUEMA RELACIONAL 3NF MULTI-TORNEO

### [ARCH-1.5.1] Esquema Relacional 3NF Multi-Torneo — Especificación Canónica de Columnas [ARCH-PILLAR] [DIRGEN-STRICT]

* **Bóveda:** `qbe_observatory/data/qbe_historico.db` (SQLite). Régimen `[DIRGEN-STRICT]`: el DDL de esta sección es la transcripción canónica; ningún módulo puede divergir de él.
* **Naturaleza:** esquema de consulta (lado Q del CQRS). La escritura bulk se ejerce únicamente por la excepción CQRS autorizada de `[ARCH-1.4.72]`; este libro no autoriza escrituras desde `qbe_core` ni desde el lado de comando.

#### 15.1 Familia `historical_*` (corpus fáctico)

| Tabla | Clave primaria | Grano | Origen |
|---|---|---|---|
| `historical_matches` | `match_id` | un partido | `[ARCH-1.4.72]` · FootyStats |
| `historical_team_season_stats` | `(temporada, team_slug)` | club-temporada | `[ARCH-1.4.72]` · FootyStats |
| `historical_load_log` | `temporada` | temporada cargada | `[ARCH-1.4.72]` |
| `historical_match_events` | `(match_id, evento_id)` | evento de la línea de tiempo | `[LN-QBE-144]` · ligamx.net |

#### 15.2 `historical_match_events` — Almacén de eventos minuto a minuto

* **Origen fáctico:** visor «Minuto a Minuto» de `ligamx.net`, parseado offline por `[LN-QBE-141]` y persistido por `[LN-QBE-144]`.
* **DDL canónico:**

```sql
CREATE TABLE IF NOT EXISTS historical_match_events (
    match_id        TEXT    NOT NULL,
    evento_id       TEXT    NOT NULL,
    minuto_texto    TEXT    NOT NULL,
    minuto_entero   INTEGER,
    minuto_agregado INTEGER,
    periodo         TEXT,
    tipo_evento     TEXT    NOT NULL,
    equipo          TEXT    NOT NULL CHECK (equipo IN ('local', 'visita')),
    descripcion     TEXT    NOT NULL,
    orden_dom       INTEGER NOT NULL,
    fuente_datos    TEXT    NOT NULL DEFAULT 'LIGAMX_MXM',
    cargado_utc     TEXT    NOT NULL,
    PRIMARY KEY (match_id, evento_id),
    FOREIGN KEY (match_id) REFERENCES historical_matches (match_id)
);

CREATE INDEX IF NOT EXISTS idx_hist_events_match
    ON historical_match_events (match_id, orden_dom);
```

* **Columnas (especificación canónica):**

| Columna | Tipo | Nulo | Semántica |
|---|---|---|---|
| `match_id` | TEXT | NO | FK → `historical_matches.match_id`. Clave de la bóveda, resuelta por Join Determinista (§15.3). |
| `evento_id` | TEXT | NO | Identificador del sitio (`evntLcal_N` / `evntVsta_N`); único por partido. |
| `minuto_texto` | TEXT | NO | Rótulo literal del minuto (`12'`, `+3'`, `45+2'`, `MT`, `MF`). Se preserva sin normalizar: es la evidencia. |
| `minuto_entero` | INTEGER | SÍ | Minuto base interpretado; `NULL` en `+N'`, `MT` y `MF`. Nunca se imputa. |
| `minuto_agregado` | INTEGER | SÍ | Tiempo añadido interpretado; `NULL` si el rótulo no lo declara. |
| `periodo` | TEXT | SÍ | `1T`, `2T`, `MT`, `MF`; `NULL` solo si el parser no pudo derivarlo (no ocurre en la columna canónica). |
| `tipo_evento` | TEXT | NO | Catálogo de `[LN-QBE-141]` (`gol`, `gol_penal`, `tarjeta_amarilla`, `tarjeta_roja`, `corner`, `falta`, `tiro_a_gol`, `cambio`, `fuera_de_lugar`, `penal`, `atajada`, `inicio_partido`, `inicio_segundo_tiempo`, `final_primer_tiempo`, `final_partido`, `otro`). |
| `equipo` | TEXT | NO | Dominio cerrado `local`/`visita` (el `lado` del parser). El nombre del club no se duplica: se resuelve por `match_id` → `historical_matches`. |
| `descripcion` | TEXT | NO | Narrativa oficial del sitio, en UTF-8 estricto. |
| `orden_dom` | INTEGER | NO | Orden de aparición en el DOM canónico (columna local y luego visitante). |
| `fuente_datos` | TEXT | NO | Procedencia declarada (`LIGAMX_MXM`). |
| `cargado_utc` | TEXT | NO | Marca ISO-8601 Z de la transacción que insertó la fila. |

* **Justificación 3NF:** la clave primaria compuesta identifica el evento sin ambigüedad; todos los atributos dependen de la clave completa (`descripcion` y `minuto_texto` del par, no de `match_id` aislado); no existen dependencias transitivas, porque el nombre de club, la temporada y el marcador viven en `historical_matches` y se alcanzan por FK.
* **Idempotencia:** `INSERT OR IGNORE` sobre `(match_id, evento_id)`. Recargar un partido no duplica eventos ni altera los ya persistidos.
* **Integridad referencial:** la FK es física; el cargador la verifica además de forma explícita antes de la transacción (Fail-Loud si el `match_id` no existe), porque SQLite no fuerza FK por defecto.
* **Prohibición:** esta tabla no se escribe desde el lado de comando ni desde `qbe_core`; no se toca `matches`, `sovereign_distributions` ni `match_telemetry`.

#### 15.3 Contrato de Resolución de `match_id` por Join Determinista

La llave del sitio (`idPartido`, p. ej. `67047`) no es la llave de la bóveda (`match_id`, p. ej. `fs_2015_2016_z85264`). La resolución es determinista y se ejecuta contra `historical_matches`:

1. `temporada` se normaliza a la forma `YYYY_YYYY` (`2015-2016` → `2015_2016`).
2. `equipo_local` y `equipo_visitante` se canonizan a slug (`América` → `america`, con plegado NFKD y ASCII).
3. Se exige coincidencia exacta de `home_team_slug`, `away_team_slug`, `home_goals` y `away_goals` sobre la temporada normalizada.
4. Debe existir **exactamente una** fila. Cero coincidencias o más de una abortan el partido con `MatchResolutionError`; no se elige por aproximación, no se crea la fila y no se imputa la llave.

* **[SHIELD]:** `qbe_ingestion/tests/test_shield_historical_load_integrity.py` (familia existente) y `qbe_ingestion/tests/test_shield_orquestador_extraccion.py` (Resolución, Persistencia y Orquestación de §15.2 y §15.3).

#### 15.4 `odds_ticks` — Serie Histórica de Momios en Vivo y Tracking de Movimientos

### [ARCH-1.5.13] Esquema 3NF de Odds Históricos y Tracking de Movimientos (`odds_ticks`)
*   **Ω (Resumen):** Fuente única de verdad para los momios en vivo. Almacena la serie histórica de ticks para análisis de mercado.
*   **I (Input):** Ingesta desde el Daemon Multicasa.
*   **Deuda técnica (FootyStats):** Las cuotas históricas actuales (FootyStats) demuestran un Brier Score ineficiente (Alpha Q-BE +66%). Queda prohibido usar estas cuotas para simular ROI histórico. Se requiere la integración de un nuevo proveedor de cuotas históricas de calidad o la acumulación de ticks propios vía Daemon.
*   **P (Process):** Inserción Append-Only. Columnas: `tick_id` (PK), `match_id` (FK), `casino_id` (FK), `timestamp`, `odd_home`, `odd_draw`, `odd_away`, `vig`, `delta_odd`.
*   **O (Output):** `qbe_business` lee el último tick (`ORDER BY timestamp DESC LIMIT 1`). `qbe_observatory` lee la serie histórica.
*   **Φ (Transición):** Consumidor activo: `qbe_storage` / `qbe_business`.

#### 15.5 `historical_sovereign_distributions` — Símplex Soberano P' del Corpus Histórico

* **Origen fáctico:** motor sellado `generar_distribucion_soberana` de `qbe_core` (Dixon-Coles 2D + colapso al Símplex Δ² + Cláusula de André), alimentado por el vector causal de `[LN-QBE-146]` y transportado por `[LN-QBE-150]`.
* **Separación CQRS:** es una tabla **histórica** (`historical_*`). No es, ni sustituye a, `sovereign_distributions` (tabla del lado vivo, 4 329 filas, `match_id` `FOTMOB-*`). Ambas coexisten y jamás se escriben entre sí.
* **DDL canónico:**

```sql
CREATE TABLE IF NOT EXISTS historical_sovereign_distributions (
    match_id                  TEXT    PRIMARY KEY,
    temporada                 TEXT    NOT NULL,
    model_version             TEXT    NOT NULL,
    p_local                   REAL    NOT NULL,
    p_empate                  REAL    NOT NULL,
    p_visitante               REAL    NOT NULL,
    lambda_home               REAL    NOT NULL,
    lambda_away               REAL    NOT NULL,
    phi_lead2_home            REAL    NOT NULL,
    phi_lead2_away            REAL    NOT NULL,
    epistemic_delta           REAL    NOT NULL DEFAULT 0.0,
    delta_epist               REAL    NOT NULL DEFAULT 0.0,
    origen_factores           TEXT    NOT NULL DEFAULT 'analitico_base',
    es_operable               INTEGER NOT NULL DEFAULT 1,
    pj_home                   INTEGER NOT NULL DEFAULT 0,
    pj_away                   INTEGER NOT NULL DEFAULT 0,
    duelos_h2h                INTEGER NOT NULL DEFAULT 0,
    variables_con_evidencia   INTEGER NOT NULL DEFAULT 0,
    origen                    TEXT    NOT NULL DEFAULT 'HISTORICO_SPRINT48',
    fuente_causal             TEXT    NOT NULL DEFAULT 'FOTMOB_MATCHDETAILS',
    audit_trace_json          TEXT    NOT NULL DEFAULT '{}',
    created_at                TEXT    NOT NULL DEFAULT '',
    FOREIGN KEY (match_id) REFERENCES historical_matches (match_id)
);
```

* **Columnas (especificación canónica):**

| Columna | Tipo | Nulo | Semántica |
|---|---|---|---|
| `match_id` | TEXT | NO | PK y FK → `historical_matches.match_id`. Una fila por partido; el `INSERT OR REPLACE` es idempotente. |
| `temporada` | TEXT | NO | Temporada canónica (`YYYY_YYYY`) desnormalizada para consulta directa del lado Q. |
| `model_version` | TEXT | NO | Versión del motor que produjo el símplex (`v13.0-DIRGEN`). |
| `p_local` / `p_empate` / `p_visitante` | REAL | NO | Símplex Δ² publicado por el motor (suma = 1 ± 1e-9). |
| `lambda_home` / `lambda_away` | REAL | NO | Intensidades Poisson acotadas que sostienen la matriz Dixon-Coles. |
| `phi_lead2_home` / `phi_lead2_away` | REAL | NO | Operador de André: probabilidad de pago anticipado por lado. |
| `epistemic_delta` | REAL | NO | Δ_epist(∞) de la fusión convexa `[LN-QBE-104]`. |
| `delta_epist` | REAL | NO | Δ_epist de variación total contra el kernel H2H `[LN-QBE-020-C]`. |
| `origen_factores` | TEXT | NO | Procedencia legislada: `analitico_base` `[LN-QBE-035-B]` o `bayesiano_10p` `[LN-QBE-036]`. |
| `es_operable` | INTEGER | NO | `1` siempre: el motor sólo persiste distribuciones con `S(I_i) = 1`. |
| `pj_home` / `pj_away` | INTEGER | NO | Partidos previos del club en la temporada que sostienen el agregado de entrada. |
| `duelos_h2h` | INTEGER | NO | Enfrentamientos directos previos dentro de la ventana de memoria. |
| `variables_con_evidencia` | INTEGER | NO | Variables del catálogo `[LN-QBE-120]` con dato factual en el vector causal de origen. |
| `origen` / `fuente_causal` | TEXT | NO | Trazabilidad del productor (`HISTORICO_SPRINT48`) y del vector (`FOTMOB_MATCHDETAILS`). |
| `audit_trace_json` | TEXT | NO | `StochasticAuditTrace` completo serializado (factores, intensidades, símplex, insumos). |
| `created_at` | TEXT | NO | Marca ISO-8601 Z de la transacción que insertó la fila. |

* **Regla de suficiencia:** un partido sin `S(I_i) = 1` (menos de 3 partidos previos por club con marcador legible) **no genera fila**: se salta y se declara en el reporte. Cero imputaciones, cero distribuciones uniformes almacenadas como si fueran cálculo.
* **Justificación 3NF:** `match_id` determina todas las columnas; `temporada` es la única dependencia funcional parcial y se conserva desnormalizada por costo de consulta del lado Q (declarado, no implícito). El detalle forense vive en `audit_trace_json` y no participa de los predicados analíticos.
* **Prohibición:** esta tabla no se escribe desde el lado de comando ni desde `qbe_core`; no se toca `matches`, `sovereign_distributions` ni `match_telemetry`.

---

## 16. DAEMON CENTINELA MULTICASA Y ORQUESTADOR DE TEMPORIZADORES

### [ARCH-1.4.75] Rescate del Daemon Centinela Multicasa y Orquestador de Temporizadores
*   **Ω (Resumen):** Rescatar y refactorizar el Centinela de Momios (`[ARCH-1.4.12]`) para extraer momios de múltiples casinos.
*   **I (Input):** Catálogo de scrapers (Caliente, Novibet, Betway, etc.) y temporizadores.
*   **P (Process):** Muestreo dinámico: 4h de lunes a jueves, 1h viernes/sábado, 10min en las 3 horas previas al kickoff. Límite de timeout de 30000 ms.
*   **O (Output):** Inserción de ticks en `odds_ticks`.

### [ARCH-1.4.77] Delimitación de Proveedores Primarios
*   **FootyStats:** Proveedor Primario Histórico para *momios* y *resultados de partidos*. Es la fuente para calcular Brier Score y Alpha históricos. **Limitación:** No cuenta con la información suficiente para obtener las 32 variables de la distribución.
*   **FotMob:** Proveedor Primario para la *evidencia fáctica* (32 variables). Es la fuente para calibrar el modelo Q-BE. **Limitación:** No maneja momios de mercado.
*   **Flujo de convergencia:** FootyStats provee los momios y resultados históricos. Q-BE provee la distribución. La comparación Alpha (Q-BE vs Mercado) solo es posible en los partidos donde ambas fuentes convergen (muestra de control).

---

## 17. CONSOLIDADOR DE BÓVEDAS HISTÓRICAS

### [ARCH-1.5.14] Consolidador de Bóvedas Históricas y UPSERT Canónico
*   **Ω (Resumen):** Rescatar la evidencia de las SQLite legacy y consolidarla en la bóveda canónica `data/qbe_database.db` sin duplicar ni imputar ceros.
*   **I (Input):** `Q_BE_CD_WEB/data/qbe_database.db`, `data/qbe_database.db` y `qbe_observatory/data/qbe_historico.db` (solo lectura).
*   **P (Process):** Backup previo, DDL idempotente de `odds_ticks` y `match_causal_vars`, UPSERT de snapshots, ticks, distribuciones y las 32 dimensiones causales. `[GOVERNANCE-01]`: `None` se omite.
*   **O (Output):** Reporte de consola con ticks de momios rescatados y variables de 32 dimensiones rescatadas.
*   **Φ (Transición):** Consumidor activo: `orquestador_live.py` y el Juez de Paridad `[LN-QBE-140]`.

---

## 18. ENRUTADOR Y FACHADA DE DESEMPEÑO HÍBRIDO

### [ARCH-1.4.78] Enrutador y Fachada de Desempeño Híbrido (`qbe_observatory`)

*   **Ω (Resumen):** una sola ruta `GET /desempeno` sirve la lectura unificada de desempeño (Brier Q-BE vs. consenso de mercado) sobre el snapshot 3NF, con la **Distribución Base** de `[DES-QBE-078]`: un conmutador `qbe` / `mercado` que decide la fuente rectora del coloreado, de la jerarquía de barras y del signo del Alpha bidireccional, más la banda de **siete macro KPIs** de cobertura (`pmax`, `pmid`, `cobertura`), el **chip de diagnóstico de vértice** y el Invariante C-50. `GET /` deja de renderizar la portada pasiva y redirige a la ruta semántica.
*   **I (Input):** snapshot 3NF `data/snapshots/qbe_database_snapshot.db` en solo lectura, a través del builder canónico de calibración (`reporte_calibracion_canonico` / `cargar_vista_calibracion`), más los parámetros de consulta. No se abre la base viva y no se ejecuta lógica de `qbe_business`.
*   **P (Process):**
    1. `GET /` → `HTTP 302` con `Location: /desempeno` (se admite `301`). La portada pasiva `qbe_observatory/app/templates/index.html` queda derogada; el redirect se declara en `qbe_observatory/app/main.py`.
    2. `GET /desempeno` → router `qbe_observatory/app/routes/desempeno_ui.py` + fachada `qbe_observatory/app/services/desempeno_view.py`. La fachada proyecta el reporte canónico a los DTO y emite **ambas** clasificaciones del resultado consumado (`vertice_qbe`, `vertice_mercado`); el pintor solo transcribe la del mando activo.
    3. **Fail-Loud:** el dominio de `casino` es `{caliente, novibet, betway, footystats}` y el de `devig` es `{shin, proporcional}`. Cualquier otro valor lanza `ValueError` y la petición falla ruidosamente: no hay sustitución silenciosa por la fuente por defecto ni degradación a `shin`.
    4. Lectura estrictamente de solo lectura (`mode=ro` + `PRAGMA query_only=ON`): cero escrituras, cero caché de estado y cero acoplamiento CQRS.
*   **O (Output):** HTML server-side (`qbe_observatory/app/templates/desempeno.html`) y el DTO que lo sostiene. Shin, cuotas individuales y vectores causales coexisten en un mismo DTO de lectura sin invocar el lado de comando.
*   **Φ (Transición):** consumidor activo: `qbe_observatory/app/templates/desempeno.html`.

#### 18.1 Parámetros de consulta de `GET /desempeno`

| Parámetro | Tipo | Dominio / defecto | Semántica |
|---|---|---|---|
| `mando` | texto | `qbe` \| `mercado` — defecto `qbe` | **Distribución Base**: fuente rectora del coloreado, de la jerarquía de barras y del signo del Alpha. |
| `temporada` | texto | `YYYY_YYYY` — defecto: la última disponible | Universo histórico servido por la fachada. |
| `jornada_desde` | entero | `>= 1` — defecto: mínimo del universo | Extremo inferior del rango declarado. |
| `jornada_hasta` | entero | `>= jornada_desde` — defecto: máximo del universo | Extremo superior del rango declarado. |
| `casino` | texto repetible | ⊆ `{caliente, novibet, betway, footystats}` — defecto: las cuatro | Fuentes de mercado que componen el consenso des-marginado. Un valor fuera del dominio ⇒ `ValueError`. |
| `devig` | texto | `shin` \| `proporcional` — defecto `shin` | Método de des-marginado del consenso. Un valor fuera del dominio ⇒ `ValueError`. |

#### 18.2 Contratos DTO

`DesempenoKPIsOut` — banda de siete macro KPIs del universo filtrado. Esquema canónico `[ARCH-1.4.78 · REV.2]`:

```python
class DesempenoKPIsOut(BaseModel):
    pmax_success_rate: float            # Tasa de éxito de P_max (%)
    pmid_success_rate: float            # Tasa de rescate de P_mid (%)
    cobertura_resultado_rate: float     # Invariante: pmax + pmid (%)
    brier_qbe: float
    brier_mercado: float
    alpha_desempeno: float
    total_partidos: int
    total_jornadas: int
    metodo_devig: str
    mando_rector: str
    temporadas_disponibles: List[str]
```

| Campo | Tipo efectivo | Semántica |
|---|---|---|
| `pmax_success_rate` | `float \| None` | Porcentaje de partidos evaluables donde el resultado consumado coincide con el primer vértice de la base activa (`r_max` en `qbe`; `max q_mkt` en `mercado`). |
| `pmid_success_rate` | `float \| None` | Porcentaje donde coincide con el segundo vértice (`r_mid` en `qbe`; `second_max q_mkt` en `mercado`). Mide la eficacia del rescate. |
| `cobertura_resultado_rate` | `float \| None` | **Invariante C-50**: suma exacta `pmax_success_rate + pmid_success_rate` (± 1e-5). Prohibido calcularla con una fórmula independiente. |
| `brier_qbe` | `float \| None` | Brier multicategórico 1X2 (3N) del símplex Q-BE. |
| `brier_mercado` | `float \| None` | Brier del consenso des-marginado con el método declarado. |
| `alpha_desempeno` | `float \| None` | **Alpha bidireccional de la Distribución Base activa**: `(1 − BS_base / BS_oponente) × 100`. Positivo ⇒ la base activa supera al oponente. `None` sin muestra coincidente o con denominador `≤ 0`. |
| `total_partidos` | `int` | Universo total de partidos auditados. |
| `total_jornadas` | `int` | Jornadas con al menos un partido auditable. |
| `metodo_devig` | `str` | `shin` \| `proporcional` efectivamente aplicado. |
| `mando_rector` | `str` | `qbe` \| `mercado` de la petición. |
| `temporadas_disponibles` | `List[str]` | Catálogo canónico de temporadas. |

> **Ausencias declaradas.** Sin muestra evaluable, las tasas y los Briers son `None` y la UI publica `—` + `SIN EVIDENCIA`; nunca un `0.0` fabricado. La anotación `float` del esquema denota el dominio medido, no una autorización para imputar ceros.

`DesempenoJornadaOut` — contenedor desplegable de la parrilla. Esquema canónico `[ARCH-1.4.78 · REV.2]`:

```python
class DesempenoJornadaOut(BaseModel):
    numero: int
    etiqueta: str
    total_partidos: int
    pmax_success_rate: float
    pmid_success_rate: float
    cobertura_resultado_rate: float
    alpha: float
    brier_qbe: float
    brier_mkt: float
    partidos: List[DesempenoPartidoOut]
```

| Campo | Tipo efectivo | Semántica |
|---|---|---|
| `numero` | `int` | N.º de jornada (`data-jornada`). |
| `etiqueta` | `str \| None` | Rótulo de presentación (`2025_2026 · J12` en el modo «Todas»); `None` ⇒ `JORNADA n`. |
| `total_partidos` | `int` | Partidos listados en la jornada. |
| `pmax_success_rate` / `pmid_success_rate` | `float \| None` | Tasa de éxito del primer / segundo vértice de la base activa en la jornada. |
| `cobertura_resultado_rate` | `float \| None` | Invariante C-50 a nivel jornada: suma exacta de las dos tasas anteriores. |
| `alpha` | `float \| None` | Alpha bidireccional de la jornada. |
| `brier_qbe` / `brier_mkt` | `float \| None` | Media de la jornada; `None` sin evidencia. |
| `partidos` | `List[DesempenoPartidoOut]` | Tarjetas de la jornada, en orden de cartelera. |

#### 18.2.1 Invariante Constitucional C-50

$$\text{cobertura\_resultado\_rate} \equiv \text{pmax\_success\_rate} + \text{pmid\_success\_rate} \quad (\pm 10^{-5})$$

Tanto a nivel global (`DesempenoKPIsOut`) como en cada jornada individual (`DesempenoJornadaOut`), la cobertura es la suma estricta de sus dos componentes ortogonales. La fachada calcula `cobertura_resultado_rate` **sumando** las dos tasas ya derivadas; no existe una fórmula independiente que pueda discrepar. Las tasas se publican redondeadas a dos decimales (`round(..., 2)`) y la cobertura se obtiene sumando esas tasas ya redondeadas, de modo que la identidad se conserva en la representación decimal. El Juez `test_shield_desempeno_visual_semantics.py` certifica la igualdad con tolerancia `1e-5` en el DTO y `0.05` en el DOM formateado a un decimal.

`DesempenoPartidoOut` — tarjeta de partido (coexistencia de fuentes sin CQRS).

| Campo | Tipo | Semántica |
|---|---|---|
| `id_partido`, `local`, `visitante`, `marcador`, `resultado_real` | `str` | Identidad y desenlace consumado (`LOCAL` / `EMPATE` / `VISITANTE`). |
| `brier_qbe` / `brier_mercado` | `float \| None` | Brier del partido por fuente. |
| `es_cold_start`, `suficiencia_s_i` | `bool`, `int` | `S = 0` declara el prior de ignorancia. |
| `p_local`, `p_empate`, `p_visitante` | `float \| None` | Símplex soberano P′. |
| `q_local`, `q_empate`, `q_visitante` | `float \| None` | Consenso des-marginado `q_mkt`. |
| `momios` | `Dict[str, float]` | Cuotas decimales individuales (`L` / `E` / `V`). |
| `r_max`, `r_mid`, `r_low` | `str` | Orden fiduciario Q-BE emitido por el núcleo (rol por vértice). |
| `vertice_qbe` | `str \| None` | `max` / `mid` / `low` / `cold_start` del resultado consumado en la lectura Q-BE. |
| `vertice_mercado` | `str \| None` | `max` / `mid` / `low` del resultado consumado en el orden del consenso. |
| `alpha_partido_pct` | `float \| None` | Alpha bidireccional del partido bajo la Distribución Base activa: la misma ley de `alpha_desempeno` aplicada a los Briers individuales (`brier_qbe` / `brier_mercado` de la tarjeta). Positivo ⇒ la base supera al oponente. `None` si falta cualquiera de los dos Briers o el denominador es `≤ 0`. |
| `rescate_partido` | `bool` | Booleano de compatibilidad derivado del par de cobertura de la base activa (`{r_max, r_mid}` en `qbe`; `{max q_mkt, second_max q_mkt}` en `mercado`). **No se pinta como chip binario**: el pie usa el Chip de Diagnóstico de Vértice (§7.4.13) transcrito de `vertice_qbe` / `vertice_mercado`. |
| `shin_z` | `float \| None` | Parámetro `z` de Shin del consenso. |
| `spread_cuotas` | `float \| None` | Spread de cuotas inter-casinos. |
| `semaforos` | `Dict[str, str]` | Tetralogía `OPTA/SEDE/H2H/CTX`. |
| `atribucion_disponible`, `atribucion_driver` | `bool`, `str \| None` | Driver factorial dominante. |
| `variables_44` | `Dict[str, Any]` | Catálogo causal de 32 variables (card polimórfica del modal). |

#### 18.3 Autoridad de la ruta

El redirect de `/` y la ruta `/desempeno` no introducen un quinto pilar ni una base nueva: son la fachada de lectura del Observatorio sobre el mismo snapshot y el mismo builder canónico que alimentan `/visor` y `/consenso`. La fachada no reimplementa Brier, Alpha, Poisson ni Shin: los transcribe.

*   **[SHIELD]:** `qbe_observatory/tests/test_shield_desempeno_route.py` (ruta, redirect 302, navbar de cuatro pestañas, banda de 7 KPIs y contrato DTO del Invariante C-50) y `qbe_observatory/tests/test_shield_desempeno_visual_semantics.py` (cuadrícula de 7 KPIs, etiquetas mnemónicas de jornada, aditividad C-50, chip de diagnóstico de vértice, sensibilidad a mando, inversión de barras, coloreado por mando y Fail-Loud de dominio).
