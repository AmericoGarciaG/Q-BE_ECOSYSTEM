# FASE 3 — CIERRE DEL SLICE ESTRUCTURAL DE `qbe_business`

| Campo | Valor |
|---|---|
| **Proyecto** | `Q_BE_ECOSYSTEM` — Fase 3 |
| **Estado** | **5/5 GREEN** (jueces inmutables) |
| **Ruta** | `D:\00 SW Projects\Q-BE Casino Deportes\Q_BE_ECOSYSTEM\qbe_business` |
| **Fecha** | 2026-10-25 |
| **Régimen** | `[DBBD-FUNGIBLE]` / `[DIRGEN-STRICT]` |

---

## 1. Resultado de los jueces

```text
collected 5 items

test_namespace_pep420_core_y_storage_coexisten PASSED [ 20%]
test_frontera_business_no_importa_observatorio_ni_ingesta PASSED [ 40%]
test_qbe_storage_aislado_de_business_e_ingesta PASSED [ 60%]
test_spa_desactiva_backtesting_y_admin PASSED [ 80%]
test_progol_math_vive_en_qbe_core_sin_ingesta PASSED [100%]

5 passed, 1 warning in 5.17s
Exit Code: 0
```

Log: `PYTEST_GREEN.log`.

---

## 2. Materializado

### 2.1. Namespace compartido

```text
src.__path__ =
  ...\qbe_business\src
  ...\qbe_core\src
  ...\qbe_storage\src
```

- `src/core/*` → `qbe_core`.
- `src/storage/*` y `src/config` → `qbe_storage`.
- `src/web/*` → `qbe_business`.
- Sin `src/__init__.py` en la raíz de ninguna distribución.

### 2.2. `qbe_storage`

- `gateway.py` **byte-idéntico** al baseline (`7651763d…`).
- `models.py` byte-idéntico (`898b3ee6…`).
- `base.py` y `database.py` (shim) nuevos.
- `qbe_storage` es paquete importable y su metadata solo exige `sqlalchemy` y `pydantic-settings`; no depende de business ni ingesta.

### 2.3. `qbe_core`

- `progol_math.py` copiado a `src/core/contracts/` con import desde `src.core.constants`.
- `PRIOR_IGNORANCIA_FIDUCIARIA = (0.3333, 0.3333, 0.3334)` en `constants.py`.
- `web_schemas.py` alojado en `src/models` para mantener un único proveedor del namespace `src.models`.
- **Enmienda de sello:** `MANIFEST_FASE1_REV2.sha256` 8/8; el sello original queda 7/8 por el cambio autorizado en `constants.py` (`VAR-2026-PROGOL-CONSTANT`).

### 2.4. `qbe_business`

- `src/web/app.py` con FastAPI, estáticos y plantilla.
- `GET /api/business/features` → `{"backtesting": false, "admin": false}`.
- `GET /api/markets/backtesting/calibration-report` y `GET /api/admin/status/drift` → **503** mientras los flags estén en false.
- SPA copiada byte-idéntica (`index.html`, `app.js`, `theme.css`, 74 estáticos / 4.3 MB).
- `features.js` bloquea los tabs de Backtesting y Admin al arrancar.

---

## 3. Pendiente declarado — routers transaccionales

Los **14 endpoints 3A/3B** no fueron portados en este slice. La app expone hoy solo:

```text
GET  /api/business/features
GET  /api/markets/backtesting/calibration-report  (503 gate)
GET  /api/admin/status/drift                      (503 gate)
GET  /health
GET  /
```

Motivo: los 5 jueces ratificados certifican los contratos estructurales, no la paridad funcional de los routers. Portar `markets.py` (2,206 líneas) y el resto exige cortar backtesting, resolver `crest_resolver` (D-B3) y separar `sync_service` (D-B6); hacerlo a ciegas violaría la Regla de Un Solo Intento y la frontera.

**Siguiente slice:** portar 3A (markets sportsbook + portfolio + export + leagues read) y luego 3B (admin/refresh) con los contratos ya verdes.

---

## 4. Frontera respetada

- `Q_BE_CD_WEB` no fue modificado: `git status` solo muestra `data/qbe_historico.db*`.
- No se importa `qbe_ingestion`/`qbe_observatory` en `qbe_business/src` (AST).
- No se escribe en la BD desde los tests.
- No se copió `tests/shield` ni `progol_math` del baseline (se copió el módulo al ecosistema; el baseline conserva el original).

---

## 5. Próximo paso

Ratificar este cierre estructural y autorizar el **slice 3A de routers transaccionales**, con:

1. `qbe_storage` y `qbe_core` ya disponibles.
2. Middleware de feature flags ya operativo.
3. SPA copiada y bloqueada para los módulos no disponibles.

**Firma:** Agente Constructor Kybern v12.0.
