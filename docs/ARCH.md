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

_Total: 140 identificadores._


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
