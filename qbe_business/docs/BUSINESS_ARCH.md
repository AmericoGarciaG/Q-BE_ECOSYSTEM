# BUSINESS_ARCH — Legislación del módulo `qbe_business`

| Campo | Valor |
|---|---|
| **Proyecto** | `Q_BE_ECOSYSTEM` — Fase 3 |
| **Módulo** | `qbe_business` |
| **Régimen** | `[DBBD-FUNGIBLE]` para UI/rutas; `[DIRGEN-STRICT]` para gateway, modelos 3NF y consumo de `qbe_core` |
| **Ubicación** | `Q_BE_ECOSYSTEM/qbe_business/` |
| **Estado** | **PROPUESTA — PENDIENTE DE RATIFICACIÓN** |
| **Fecha** | 2026-10-25 · America/Mexico_City |
| **Alcance** | Legislación previa a código. Este documento no crea `.py`, `.html` ni copia archivos. |

---

## 0. Eco de comprensión

1. **Régimen:** `[HÍBRIDO DUAL-TRACK]`.
   - `[DIRGEN-STRICT]`: `PersistenceGateway` (`VAULT-DATA-001`), modelos 3NF, contratos y matemática importada de `qbe_core`.
   - `[DBBD-FUNGIBLE]`: FastAPI, rutas, SPA, plantillas, configuración y proxy.
2. **Ruta SDLC:** `SDLC-04 Feature Injection` — Fase 3.
3. **Contrato IPO:** entrada = SPA/JSON transaccional contra la BD viva; salida = carteras, boletos, tesis y PDFs servidos por `:8000`; invariantes = cero reimplementación matemática, cero import de Observatorio/Ingesta/ML, gateway único con WAL/FK.
4. **Pruebas del Bucle Reflexivo:**
   - `tests/shield/test_shield_persistence_gateway.py`
   - `tests/shield/test_shield_dirgen_integrity.py`
   - `tests/shield/test_shield_mesa_apuestas_reconnect.py`
   - `tests/shield/test_shield_portfolio_math.py`
   - `tests/shield/test_shield_phase6_dual_core_contracts.py`
   - `tests/shield/test_LN_QBE_003_live_board_integration.py`
   - `tests/shield/test_shield_volume2_consolidation.py`
   - Suite completa: **564 casos** en entorno no confinado.

> **Alto al Fuego respetado.** Ningún archivo de código fue creado ni copiado para producir esta ficha.

---

## 1. Topología

`qbe_business` es la aplicación FastAPI **dueña del tráfico transaccional**:

- Sirve la SPA actual (`index.html`, `app.js`, `theme.css` y estáticos) en `127.0.0.1:8000`.
- Expone los endpoints JSON que la SPA consume.
- Escribe la BD viva **solo** mediante `PersistenceGateway`.
- Consume `qbe_core` para toda la física y las estrategias.
- No sirve el Observatorio ni ejecuta ingesta.

```text
Navegador
   │  :8000  (misma origen)
   ▼
qbe_business (FastAPI + SPA + gateway) ──► data/qbe_database.db (WAL)
   │                         │
   │ proxy allowlist         └──► qbe_core (src.core.*, instalado)
   ├──► qbe_observatory :8001  (backtesting, solo lectura)
   └──► qbe_ingestion  (admin/refresh, a definir)
```

---

## 2. Fronteras y propiedad de escritura

### 2.1. Matriz de propiedad

| Grupo de datos | Escritor exclusivo | Lectores |
|---|---|---|
| `matches`, `sovereign_distributions`, `fixtures_snapshots`, `teams`, `leagues`, `seasons`, `competitions`, `standings_snapshots`, `match_telemetry`, `slates`, `slate_items`, `matchday_states` | `qbe_ingestion` | `qbe_business` (UI), `qbe_observatory` (snapshot) |
| `paper_trading_ledger` | **`qbe_business`** | `qbe_business` (ledger) |
| `portfolio_records` | Legado: sin escritor en las rutas web actuales | `qbe_business` (PDF) |
| `llm_token_ledger` | `qbe_ingestion` / admin | admin UI |
| BD del Observatorio | `qbe_observatory` | `qbe_observatory` |

**Corrección al lenguaje de la directiva:** «business es dueño de la escritura» significa **dueño de la escritura transaccional del usuario** (boletos/carteras), no de la captura. La ingesta sigue siendo el único escritor de las tablas de datos deportivos. Si business escribiera `matches`/`sovereign_distributions`, se rompería CQRS y la trazabilidad.

### 2.2. Prohibiciones absolutas

`qbe_business` **no puede**:

- importar `qbe_observatory`, `qbe_ingestion` ni módulos de ML;
- importar `playwright`, `google-generativeai`, `sklearn`, `xgboost` ni `pandas`;
- reimplementar Poisson, Dixon-Coles, André, triaje, Kelly o dutching;
- abrir SQLite fuera de `PersistenceGateway`;
- ejecutar `VACUUM`, purgas o DDL en el proceso web;
- scrapear o lanzar Chromium.

---

## 3. Persistencia — El Gateway

### 3.1. Extracción mínima

| Archivo actual | Destino | Tratamiento |
|---|---|---|
| `src/storage/gateway.py` | `src/storage/gateway.py` | **Copia byte-idéntica** (`VAULT-DATA-001`) |
| `src/storage/models.py` | `src/storage/models.py` | Copia; 16 clases / 17 tablas 3NF |
| `src/storage/database.py` | `src/storage/database.py` | **Shim** de un solo motor (ver §3.3) |
| `src/storage/base.py` | `src/storage/base.py` | Nuevo: `Base = declarative_base()` |
| `src/config.py` | `src/config.py` | Copia/adaptación de settings; `.env` raíz |
| `src/storage/crest_resolver.py` | `src/storage/crest_resolver.py` | Copia **condicionada** a D-B3 |
| `src/storage/repository.py` | `src/storage/repository.py` | Copia; solo lectura si se usa |
| `src/reporting/compiler.py`, `narrative.py` | `src/reporting/` | Copia; PDF/tesis |
| `src/models/web_schemas.py` | `src/models/web_schemas.py` | Copia; DTO de la SPA |
| `src/storage/seeder.py`, `sync_service.py`, `curation_service.py`, `distribution_sync.py` | **No van a business** | Pertenecen a ingesta/bootstrap |

### 3.2. Gateway único

- `PersistenceGateway` conserva `PRAGMA journal_mode=WAL`, `foreign_keys=ON`, `synchronous=NORMAL`, `busy_timeout=15000`.
- Business usa `read_session()` para lecturas y `write_transaction()` solo para boletos/carteras.
- Prohibido crear un segundo engine funcional.

### 3.3. Shim de `database.py`

`models.py` importa `Base` de `src.storage.database`. Para no editar `models.py` ni `gateway.py`:

```python
# src/storage/database.py — shim de compatibilidad, un solo motor
from src.storage.base import Base
from src.storage.gateway import PersistenceGateway

_gateway = PersistenceGateway()
engine = _gateway.engine
SessionLocal = _gateway.SessionFactory

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

Así las rutas que aún usan `Depends(get_db)` escriben/leen por el **mismo** engine WAL del gateway. El `database.py` original (segundo engine sin PRAGMAs) queda retirado.

### 3.4. Ruta de la BD viva

`DATABASE_URL` debe resolverse a la ruta real del baseline, no al CWD:

```text
sqlite:///D:/00 SW Projects/Q-BE Casino Deportes/Q_BE_CD_WEB/data/qbe_database.db
```

o variable de entorno equivalente. Prohibido copiar la BD al ecosistema: business escribe la bóveda viva existente.

### 3.5. Migraciones y DDL

- Business **no** ejecuta `create_all` en el arranque; el esquema 3NF está congelado.
- Cambios de esquema: script de migración de ingesta + backup previo + `PRAGMA quick_check`.
- `seed_initial_leagues()` y `sync_active_leagues_data()` salen del `lifespan` de business; pasan a bootstrap de ingesta.

---

## 4. El problema del namespace `src` (D-B1, bloqueante)

### 4.1. Hecho

`qbe_core` instala un paquete **regular** `src` (`src/__init__.py`) con `src.core` y `src.models`. `qbe_business` necesita aportar `src.storage`, `src.web`, `src.config` y `src.models.web_schemas`. Python **no fusiona** paquetes regulares de dos distribuciones: el segundo `src/__init__.py` pisa al primero y `src.storage` deja de existir.

### 4.2. Opciones

| Opción | Mecánica | Ediciones en código sellado | Veredicto |
|---|---|---:|---|
| **A1. Namespace PEP 420** | Quitar `qbe_core/src/__init__.py` y `src/models/__init__.py`; `qbe_core` aporta `src.core`/`src.models`, `qbe_business` aporta `src.storage`/`src.web`/`src.config`; ambos se fusionan | **0** en gateway/models/web | **Recomendada, sujeta a spike** |
| **A2. `pkgutil.extend_path`** | Mantener `src/__init__.py` y `src/models/__init__.py` en ambas distribuciones, cada uno extendiendo `__path__` | 2 archivos de empaquetado | Alternativa si A1 no resuelve con editables |
| **B. Namespace propio `qbe_business.*`** | Copiar y reescribir imports de gateway/models/rutas a `qbe_business.*` | Decenas; gateway DirGen requiere varianza | Fallback costoso |
| **C. Overlay de `sys.path`/`sitecustomize`** | Extender `src.__path__` en runtime | 0, pero hack no auditable | Rechazada |

### 4.3. Spike obligatorio antes de copiar

La fusión de dos distribuciones editables bajo un mismo `src` **debe probarse** con un spike mínimo:

1. Instalar `qbe_core` editable (ya está).
2. Crear un `qbe_business/src/storage/__init__.py` vacío y un `src/config.py` temporal.
3. Verificar en un proceso limpio: `import src.core.poisson` **y** `import src.storage` resuelven a archivos de distribuciones distintas.
4. Si A1 falla, probar A2; si ambas fallan, decidir B con varianza.

Sin ese spike, la Fase 3 no debe copiar el gateway.

### 4.4. Consecuencia

**La Fase 3 no puede empezar a copiar código hasta que D-B1 se ratifique y el spike pase.** La opción A1/A2 exige una enmienda de empaquetado de `qbe_core` (sin tocar matemática) y re-certificar 8/8. La opción B exige una `DIRGEN_VARIANCE_REQUEST` para el gateway.

---

## 5. Consumo de `qbe_core`

Toda la física y las estrategias se importan de `src.core.*`:

| Necesidad | Símbolo canónico |
|---|---|
| Poisson / Dixon-Coles | `src.core.poisson`, `src.core.distribution_dixon_coles` |
| Intensidades log-lineal | `src.core.intensity_canonical_loglink` |
| André | `src.core.andre_early_payout` |
| Triaje / Kelly / Dutching / Brier / de-vig | `src.core.contracts.portfolio_math` |
| Símplex / Γ | `src.core.simplex_morphology`, `src.core.risk_dial_modulator` |
| Cartera | `src.core.portfolio` |
| Orquestador soberano | `src.core.sovereign_pipeline` |
| Progol | `src.core.contracts.progol_math` (**diferido**, ver D-B4) |

**Prohibido** copiar estas fórmulas a `qbe_business`. Un meta-test AST verifica que no existan constantes/fórmulas duplicadas.

### 5.1. `progol_math` (D-B4)

`progol_math.py` quedó fuera de `qbe_core` porque importa `PRIOR_IGNORANCIA_FIDUCIARIA` de `src.ingestion.progol_scraper`. Business necesita `/api/markets/progol/optimize`.

Opciones:

1. Mover la constante a `src.core.constants` y actualizar `progol_math` (varianza DirGen; recomendada).
2. Copiar `progol_math` a business y sustituir el import por una constante local (duplica fuente; requiere prueba de paridad).
3. Dejar Progol fuera de Fase 3 hasta resolverlo.

Sin esta decisión, `/progol/optimize` no puede migrar sin violar la frontera.

---

## 6. Rutas a migrar

Inventario actual: **23 endpoints** en 8 routers.

### 6.1. Núcleo transaccional → `qbe_business` (14)

| Método | Endpoint | Origen actual | Fase |
|---|---|---|---|
| GET | `/api/markets/sportsbook/matches` | `markets.py` | 3A |
| GET | `/api/markets/sportsbook/live-board` | `markets.py` | 3A |
| POST | `/api/markets/sportsbook/portfolio/generate` | `markets.py` | 3A |
| GET | `/api/markets/progol/slates/active` | `markets.py` | 3A (condicionado a D-B4) |
| POST | `/api/markets/progol/optimize` | `markets.py` | 3A (condicionado a D-B4) |
| GET | `/api/leagues` | `leagues.py` | 3A |
| GET | `/api/leagues/` | `leagues.py` | 3A |
| GET | `/api/leagues/{league_id}/live-board` | `leagues.py` | 3A |
| POST | `/api/portfolio/register-ticket` | `portfolio.py` | 3A |
| GET | `/api/portfolio/ledger-status` | `portfolio.py` | 3A |
| POST | `/api/portfolio/match-thesis` | `portfolio.py` | 3A |
| GET | `/api/portfolio/{portfolio_id}/pdf` | `export.py` | 3A |
| GET | `/api/sovereign/leagues/{league_id}/matches` | `sovereign.py` | 3A |
| GET | `/api/admin/status/drift` | `admin_status.py` | 3B (requiere separar `sync_service`) |

### 6.2. Observatorio — no van a business (2)

| Método | Endpoint | Destino |
|---|---|---|
| GET | `/api/markets/backtesting/calibration-report` | `qbe_observatory` |
| POST | `/api/markets/backtesting/simulate` | `qbe_observatory` |

**Advertencia D-B5:** el Observatorio MVP de Fase 2 solo implementa un reporte de calibración simple; **no** implementa el contrato rico del Visor ni `simulate`. La pestaña de Backtesting de la SPA no puede servirse desde business hasta que el Observatorio complete su contrato (Fase 2.5) o se proxe con un contrato compatible.

### 6.3. Ingesta / administración — no van a business (7)

| Método | Endpoint | Destino | Motivo |
|---|---|---|---|
| POST | `/api/leagues/{league_id}/refresh-tabla` | `qbe_ingestion` | Dispara captura |
| POST | `/api/leagues/{league_id}/refresh-momios` | `qbe_ingestion` | Dispara captura |
| POST | `/api/admin/catalogs/discover` | `qbe_ingestion` | Curación/LLM |
| GET | `/api/admin/catalogs/staging` | `qbe_ingestion` | Curación |
| POST | `/api/admin/catalogs/commit` | `qbe_ingestion` | Escritura de catálogo |
| GET | `/api/admin/llm/telemetry` | `qbe_ingestion` | Ledger LLM |
| POST | `/api/admin/tasks/run` | `qbe_ingestion` | `IngestionCoordinator` |

`admin_tasks.py` importa `src.services.ingestion_coordinator`; `leagues.py` importa `sync_service` (que importa `src.ingestion.normalizer`). Migrarlos a business **tal cual** violaría la frontera.

### 6.4. Corte obligatorio de módulos

La extracción no es “copiar `src/web` completo”:

| Módulo | Corte |
|---|---|
| `src/web/app.py` | Quitar `seed_initial_leagues`, `sync_active_leagues_data`, `admin_tasks`, `admin_status`, `admin` (3B); incluir solo routers 3A + proxy |
| `src/web/routes/markets.py` (2,206 líneas) | Retener sportsbook/progol (≈1,348 líneas); **cortar** `_construir_reporte_calibracion`, helpers de calibración y los dos endpoints de backtesting → Observatorio |
| `src/web/routes/leagues.py` | Separar lecturas (`GET /api/leagues*`) de los dos `refresh-*`; las lecturas no deben importar `sync_service` |
| `src/web/routes/admin.py`, `admin_tasks.py`, `admin_status.py` | 3B: proxy o traslado a ingesta; no copiar `IngestionCoordinator` ni `curation_service` |
| `src/web/routes/portfolio.py`, `export.py`, `sovereign.py` | Copiar con gateway y `web_schemas`; `sovereign` condicionado a D-B3 (`crest_resolver`) |

`markets.py` usa `simulation_engine` solo dentro del endpoint de backtesting; el corte debe eliminar ese import del árbol de business.

### 6.5. Rutas no-API

| Ruta | Destino |
|---|---|
| `GET /` | Business (Jinja2 `index.html`) |
| `GET /health` | Business |
| `/static/*` | Business (74 archivos, 4.3 MB) |

---

## 7. Frontend

### 7.1. Activos a migrar

| Activo | Tamaño | Tratamiento |
|---|---:|---|
| `src/web/templates/index.html` | 93,420 B | Copia byte-idéntica; sin etiquetas Jinja dinámicas hoy |
| `src/web/static/js/app.js` | 280,579 B | Copia byte-idéntica; **cero reescritura** |
| `src/web/static/css/theme.css` | 59,409 B | Copia byte-idéntica |
| `src/web/static/img/**` | ~4.3 MB / 74 archivos | Copia completa (escudos, bookmakers, ligas) |

La SPA usa **29 referencias** a `/api/...` relativas; al servirse desde `:8000`, siguen funcionando si las rutas existen o se proxean.

### 7.2. Fachada same-origin

Para no reescribir `app.js`, business actúa como **fachada** con una allowlist de proxy:

| Prefijo | Destino | Fase |
|---|---|---|
| `/api/markets/backtesting/*` | `http://127.0.0.1:8001/api/observatory/*` | 3C (cuando exista contrato) |
| `/api/admin/tasks/*` | `qbe_ingestion` (API administrativa) | 3B |
| `/api/admin/catalogs/*` | `qbe_ingestion` | 3B |
| `/api/admin/llm/telemetry` | `qbe_ingestion` | 3B |
| `/api/leagues/*/refresh-*` | `qbe_ingestion` | 3B |

El proxy **no importa** el código del destino: solo reenvía HTTP. Si el servicio no existe, la pestaña se desactiva con un feature flag visible (“Servicio no disponible”), sin inventar respuestas.

### 7.3. Reglas

- Sin React/Vue/bundler.
- Sin cálculo financiero en el cliente: la SPA solo pinta payloads.
- `N/D` para campos nulos.
- CORS no se necesita: misma origen.
- Auth: se preserva el bind local; token opcional por `.env` si se expone.

---

## 8. Estructura propuesta

```text
qbe_business/
├── src/                          # namespace compartido con qbe_core (D-B1)
│   ├── config.py
│   ├── models/
│   │   └── web_schemas.py
│   ├── storage/
│   │   ├── base.py
│   │   ├── database.py           # shim de un solo motor
│   │   ├── gateway.py            # copia byte-idéntica (DirGen)
│   │   ├── models.py             # copia byte-idéntica
│   │   ├── crest_resolver.py     # condicionado a D-B3
│   │   └── repository.py
│   ├── reporting/
│   │   ├── compiler.py
│   │   └── narrative.py
│   └── web/
│       ├── app.py
│       ├── routes/
│       │   ├── markets.py        # sin backtesting ni simulate
│       │   ├── leagues.py        # solo lecturas
│       │   ├── portfolio.py
│       │   ├── export.py
│       │   └── sovereign.py
│       ├── templates/index.html
│       └── static/{js,css,img}
├── tests/
├── docs/BUSINESS_ARCH.md
├── pyproject.toml
├── requirements.txt
└── MANIFEST_FASE3.sha256
```

Sin `src/__init__.py`; `src.core` lo aporta `qbe_core`.

---

## 9. Dependencias

```text
fastapi
uvicorn[standard]
jinja2
pydantic
pydantic-settings
sqlalchemy>=2.0
httpx            # solo proxy/fachada y tests
pytest
```

**No** incluye: `playwright`, `google-generativeai`, `pandas`, `scikit-learn`, `xgboost`, `beautifulsoup4`.

`qbe_core` se instala aparte (`pip install -e ../qbe_core`) y comparte el namespace `src`.

---

## 10. Decisiones pendientes (Custodio)

| ID | Decisión | Propuesta | Bloquea |
|---|---|---|---|
| **D-B1** | Fusión del namespace `src` | A1 (PEP 420) o A2 (`pkgutil`); spike de dos editables + re-certificar 8/8 | **Toda la Fase 3** |
| **D-B2** | ¿Quién posee el gateway? | Business lo aloja; ingesta lo consume como librería de infraestructura; a futuro `qbe_storage` compartido | Copia de storage |
| **D-B3** | `crest_resolver` importa `src.ingestion.normalizer` | **Resuelto en Slice 3A:** `normalizer.py` copiado byte-idéntico a `qbe_core/src/core/normalization/`; `crest_resolver` importa `src.core.normalization.normalizer` | Rutas de ligas/soberano |
| **D-B4** | `progol_math` y su constante | Mover constante a `qbe_core.constants` con varianza; luego `progol_math` a business | Progol |
| **D-B5** | Backtesting en la SPA | Extender Observatorio (Fase 2.5) o desactivar pestaña hasta entonces | Pestaña Visor |
| **D-B6** | Admin/refresh en la SPA | Proxy a ingesta (3B) o desactivar pestaña | Cockpit |
| **D-B7** | DDL/`create_all` en arranque | Eliminar; esquema congelado, migraciones externas | Arranque |
| **D-B8** | Varianza DirGen del gateway | Autorizar cambio de ruta del juez `test_shield_dirgen_integrity.py` sin tocar el gateway | G3 |
| **D-B9** | Ruta de la BD viva | `DATABASE_URL` absoluta al baseline; sin copia | Persistencia |

---

## 11. Pruebas y criterios de aceptación

### 11.1. Jueces mínimos

- `test_shield_persistence_gateway.py` — WAL/FK/timeout y `read_session`/`write_transaction`.
- `test_shield_dirgen_integrity.py` — gateway byte-idéntico y AST.
- `test_shield_mesa_apuestas_reconnect.py` — mesa y cartera.
- `test_shield_portfolio_math.py` — triaje/Kelly/dutching desde `qbe_core`.
- `test_shield_phase6_dual_core_contracts.py` — contratos de la SPA.
- `test_LN_QBE_003_live_board_integration.py` — live board.
- `test_shield_volume2_consolidation.py` — UI/estáticos.
- Suite completa 564.

### 11.2. Criterios

1. `GET /` y `/visor`/SPA cargan en `:8000`; `/static/*` sirve 74 activos.
2. Los 14 endpoints del núcleo responden 200 con datos reales.
3. `register-ticket` escribe en `paper_trading_ledger` vía gateway y es idempotente.
4. Un `INSERT`/`UPDATE`/`DELETE` fuera del gateway no existe en el código (AST).
5. Cero imports de `qbe_observatory`, `qbe_ingestion` y ML en `src/` de business.
6. Gateway SHA-256 idéntico al baseline; juez DirGen actualizado solo en ruta.
7. La BD viva conserva `b5fd…` antes/después de una sesión de lectura.
8. Latencia p95 de endpoints de lectura < 20 ms (medida en caliente, no estimada).

---

## 12. Lo que esta fase NO hace

- No copia el gateway ni los modelos todavía.
- No crea `qbe_business/src` ni `app.js`.
- No modifica `Q_BE_CD_WEB`.
- No resuelve D-B1…D-B9 por iniciativa propia.
- No implementa proxy, auth ni migraciones.

---

## 14. Slice 3A — Contrato ratificado

### 14.1. Endpoints (12)

| Método | Endpoint | Origen | Nota |
|---|---|---|---|
| GET | `/api/markets/sportsbook/matches` | `markets.py` | Solo sportsbook |
| GET | `/api/markets/sportsbook/live-board` | `markets.py` | Solo sportsbook |
| POST | `/api/markets/sportsbook/portfolio/generate` | `markets.py` | **Golden Master** |
| GET | `/api/markets/progol/slates/active` | `markets.py` | Progol |
| POST | `/api/markets/progol/optimize` | `markets.py` | Progol |
| POST | `/api/portfolio/register-ticket` | `portfolio.py` | Escritura transaccional |
| GET | `/api/portfolio/ledger-status` | `portfolio.py` | Lectura |
| POST | `/api/portfolio/match-thesis` | `portfolio.py` | Tesis |
| GET | `/api/portfolio/{portfolio_id}/pdf` | `export.py` | PDF |
| GET | `/api/leagues` | `leagues.py` | Lectura |
| GET | `/api/leagues/` | `leagues.py` | Lectura |
| GET | `/api/leagues/{league_id}/live-board` | `leagues.py` | Lectura |

**Fuera de 3A (gate 503):** backtesting (2), refresh-tabla/momios (2), admin catálogos/LLM/tasks (4) y `admin/status/drift`. `sovereign` queda para 3B.

### 14.2. Payload del Golden Master

```json
{
  "league_id": 262,
  "selected_match_ids": ["LIGAMX-J14-09"],
  "bankroll": 1000.0,
  "target_certeza": 0.80,
  "operador": "caliente",
  "gamma_slider": 0.67,
  "modo_cobertura": "DEF"
}
```

### 14.3. Golden Master

- **Archivo:** `tests/golden_master_portfolio.json` (5,639 B, 1 orden de ejecución).
- **Fuente:** `Q_BE_CD_WEB/data/output/backups/qbe_database.baseline.db` (snapshot G0), misma base que usará el test.
- **Comparación:** igualdad exacta del JSON completo, no solo de claves.

### 14.4. D-B3 — Resuelto

`src.core.normalization.normalizer` fue creado en `qbe_core` (copia byte-idéntica del normalizador puro, SHA-256 `efe0c1d1…`). `qbe_storage/src/storage/crest_resolver.py` importa ahora desde `src.core.normalization.normalizer`; `qbe_business` no importa `src.ingestion`.

Sin este paso, `leagues` y `sovereign` no podían portarse sin violar la frontera.

### 14.5. Juez de paridad

`tests/test_parity_business_routers.py` debe nacer **RED**:

1. Copia el snapshot G0 a un SQLite efímero.
2. Ajusta `DATABASE_URL` y resetea el singleton del gateway.
3. `POST /api/markets/sportsbook/portfolio/generate` con el payload §14.2.
4. Exige `200` e igualdad exacta con el Golden Master.

Comando:

```powershell
cd "D:\00 SW Projects\Q-BE Casino Deportes\Q_BE_ECOSYSTEM"
.\.venv\Scripts\python.exe -m pytest qbe_business/tests/test_parity_business_routers.py -v
```

### 14.6. Criterio de aceptación del Slice 3A

- Paridad exacta del Golden Master.
- Los 5 jueces estructurales siguen en verde.
- 12 endpoints 3A responden con datos reales.
- `refresh-*`, backtesting y admin devuelven 503/404.
- Cero imports de ingesta/observatorio en `qbe_business/src`.

---

**Firma:** Agente Constructor Kybern v12.0 — `[DBBD-FUNGIBLE]` / `[DIRGEN-STRICT]`.
**Estado:** Documento listo para revisión del Custodio. **No se creó ningún archivo de código.**
