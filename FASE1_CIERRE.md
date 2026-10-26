# FASE 1 — CIERRE DE MATERIALIZACIÓN DE `Q_BE_ECOSYSTEM` Y `qbe_core`

| Campo | Valor |
|---|---|
| **Proyecto** | `Q_BE_ECOSYSTEM` |
| **Fase** | Fase 1 — Núcleo puro (`qbe_core`) |
| **Régimen** | `[DIRGEN-STRICT]` para la extracción; `[DBBD-FUNGIBLE]` para la infraestructura |
| **Fecha** | 2026-10-25 · America/Mexico_City |
| **Ruta absoluta del ecosistema** | `D:\00 SW Projects\Q-BE Casino Deportes\Q_BE_ECOSYSTEM` |
| **Baseline** | `Q_BE_CD_WEB` @ tag `baseline-pre-ecosystem-v1.0` (`94f44e0`), sin mutaciones |
| **Estado** | **CERRADA** — smoke, paridad 8/8 y Bóveda 16/16 verificados |

---

## 1. Infraestructura materializada

```text
D:\00 SW Projects\Q-BE Casino Deportes\Q_BE_ECOSYSTEM\
├── .venv\                         Python 3.12.9
├── qbe_core\
│   ├── pyproject.toml             qbe_core 0.1.0
│   ├── MANIFEST_FASE1.sha256      copia del manifiesto sellado
│   ├── docs\DIRGEN_VAULT.md       Bóveda copiada con 16 rutas migradas
│   └── src\
│       ├── __init__.py
│       ├── core\                  (7 módulos + contracts)
│       └── models\analytics.py
└── FASE1_CIERRE.md                este documento
```

| Verificación | Resultado |
|---|---|
| `qbe_core` instalado en editable | `0.1.0`, `Editable project location: ...\Q_BE_ECOSYSTEM\qbe_core` |
| Python del venv | `3.12.9` |
| Dependencias | `numpy 2.5.4`, `scipy 1.18.1`, `pydantic 2.14.1` |
| `progol_math.py` | **No copiado** (`Test-Path` = `False`) |
| `tests/shield/` | **No copiado** (`Test-Path` = `False`) |
| Baseline `Q_BE_CD_WEB` | Sin cambios de código; `git status` solo muestra las BD históricas no versionadas |

---

## 2. Smoke de importación pura

Ejecutado desde `C:\...\Q_BE_ECOSYSTEM` (no desde el baseline, para evitar el *shadowing* de `src`):

```text
qbe_core OK
D:\00 SW Projects\Q-BE Casino Deportes\Q_BE_ECOSYSTEM\qbe_core\src\core\poisson.py
sqlalchemy_loaded False
storage_loaded False
```

El `__file__` demuestra que `src.core.poisson` se resuelve al paquete instalado, no al `src` del monolito. No se carga SQLAlchemy ni `src.storage`: el núcleo es I/O-free en la práctica.

---

## 3. Paridad de los 8 módulos — 8/8 OK

Verificación SHA-256 contra `qbe_core/MANIFEST_FASE1.sha256`:

```text
OK    src/core/contracts/portfolio_math.py
OK    src/core/poisson.py
OK    src/core/distribution_dixon_coles.py
OK    src/core/intensity_canonical_loglink.py
OK    src/core/simplex_morphology.py
OK    src/core/andre_early_payout.py
OK    src/core/constants.py
OK    src/models/analytics.py
8/8 OK
```

| Módulo | SHA-256 |
|---|---|
| `contracts/portfolio_math.py` | `37df6382339aa1b8ebdfb04620a1a585afa58d6b8d67dfd0b68e8c2595504f6a` |
| `poisson.py` | `d4678d06af9f70dbb84e6182e64a541a9edc90895f1de7e795469121cec15036` |
| `distribution_dixon_coles.py` | `ce0861dbc437e2478f4bffc2fdd52849fccad99a7790cec16020172391bfcefc` |
| `intensity_canonical_loglink.py` | `78d568a144c8db58504c5e1a1bd80a85d9677632d54a5151de5ff23f7fdcd1d4` |
| `simplex_morphology.py` | `3cd26b7c78148422aebf814a308df7bcbf6ab8bc896084341f64061b0748f3c6` |
| `andre_early_payout.py` | `9327cc299e01d078d9cb01c291623f8ecb67c24fb900dac6e1065345cf3d4852` |
| `constants.py` | `168e233702aba8c60b7f94cd8ce5938e820f770a13d145b2ce81b20115c5ba64` |
| `models/analytics.py` | `1ee6c983b664d1c92303ab4e23d7f7dd8d49e8ecbcc9375e5417f1f66e864d99` |

---

## 4. Bóveda copiada — 16 sustituciones exactas

**Archivo:** `qbe_core/docs/DIRGEN_VAULT.md` (3,144 líneas).

| Control | Resultado |
|---|---|
| Líneas totales | `3,144` (idénticas al original) |
| Líneas modificadas | **16** |
| Naturaleza del cambio | solo prefijo `src/core/` → `qbe_core/src/core/` |
| Otras diferencias | **0** |
| Referencias migradas | **16** |
| Referencias diferidas (sin tocar) | **10** |
| Original `docs/DIRGEN_VAULT.md` | intacto; SHA-256 `36ea920b…` |

**Líneas migradas:** `10, 12, 30, 31, 32, 33, 34, 37, 159, 165, 256, 262, 313, 325, 1548, 2951`.

Corresponden exactamente a los 5 módulos de Fase 1 con presencia en la Bóveda:

- `intensity_canonical_loglink.py`: 10, 159, 165.
- `andre_early_payout.py`: 12, 256, 262.
- `contracts/portfolio_math.py`: 30, 31, 32, 33, 34, 1548.
- `simplex_morphology.py`: 37, 2951.
- `distribution_dixon_coles.py`: 313, 325.

Las 10 referencias restantes conservan `src/...` por corresponder a módulos aún no extraídos (`sovereign_pipeline`, `risk_dial_modulator`, `progol_math`, `bayesian_form`) o a rutas inexistentes preexistentes (`metrics_damping_orthogonalizer`, `generators_ensemble_bma`).

---

## 5. Prohibiciones respetadas

| Prohibición | Estado |
|---|---|
| No modificar `Q_BE_CD_WEB` | Cumplida: `git status` del baseline solo muestra `data/qbe_historico.db*` (nunca versionados) |
| No copiar `progol_math.py` | Cumplida: no existe en `qbe_core` |
| No copiar `tests/shield/` | Cumplida: no existe `Q_BE_ECOSYSTEM/tests` |
| No editar la matemática | Cumplida: 8/8 hashes idénticos |
| No tocar las BD | Cumplida: solo lectura y snapshots en `data/output/backups/` |

---

## 6. Eco de comprensión — Fase 2: Observatorio

1. **Régimen:** `[HÍBRIDO DUAL-TRACK]`.
   - `[DIRGEN-STRICT]`: consumo de `qbe_core` (Poisson, Dixon-Coles, André, cartera) sin reimplementar una sola fórmula; `src.core.*` es la única fuente.
   - `[DBBD-FUNGIBLE]`: FastAPI, Jinja2/UI, snapshot, orquestación y pruebas de integración del Observatorio.
2. **Ruta SDLC:** `SDLC-04 Feature Injection` — Fase 2, con el alcance de solo lectura.
3. **Contrato IPO:** entrada = BD viva en `mode=ro` o snapshot consistente + `league_id`/`jornada`; salida = `CalibrationReportResponse` y simulación retrospectiva; invariantes = **cero DDL** y **cero escrituras** sobre la BD de negocio, cero red en el Visor y matemática importada de `qbe_core`.
4. **Pruebas del Bucle Reflexivo:**
   - `tests/shield/test_shield_visor_backtesting.py`
   - `tests/shield/test_shield_visor_backtesting_cold_start.py`
   - `tests/shield/test_shield_backtesting_and_empty_portfolio.py`
   - `tests/shield/test_shield_backtesting_simulation_rest.py`
   - `tests/shield/test_shield_cold_start_and_indifference_band.py`
   - Suite completa `pytest tests/shield -q` → **564 casos** (entorno no confinado).
5. **Compuertas de la Fase 2:** `mode=ro` + `PRAGMA query_only=ON`; snapshot para escaneos > 2 s; tablas propias en `observatory.db`, nunca `create_all` sobre la viva; UI nueva sin bifurcar `app.js`; auth local/token si se expone.

---

**Firma:** Agente Constructor Kybern v12.0 — `[DIRGEN-STRICT]` / `[DBBD-FUNGIBLE]`.
**Estado:** Fase 1 cerrada. **No se modificó una sola línea de lógica matemática.**
