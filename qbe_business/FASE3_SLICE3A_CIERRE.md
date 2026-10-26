# SLICE 3A — CIERRE DE ROUTERS TRANSACCIONALES

| Campo | Valor |
|---|---|
| **Proyecto** | `Q_BE_ECOSYSTEM` — Fase 3, Slice 3A |
| **Régimen** | `[DBBD-FUNGIBLE]` / `[DIRGEN-STRICT]` |
| **Estado** | **6/6 GREEN** (5 estructurales + 1 paridad) |
| **Ruta** | `D:\00 SW Projects\Q-BE Casino Deportes\Q_BE_ECOSYSTEM\qbe_business` |
| **Fecha** | 2026-10-25 |

---

## 1. Jueces en verde

```text
test_namespace_pep420_core_y_storage_coexisten PASSED
test_frontera_business_no_importa_observatorio_ni_ingesta PASSED
test_qbe_storage_aislado_de_business_e_ingesta PASSED
test_spa_desactiva_backtesting_y_admin PASSED
test_progol_math_vive_en_qbe_core_sin_ingesta PASSED
test_paridad_generate_portfolio PASSED

6 passed, 1 warning in 4.95s
Exit Code: 0
```

Log: `PYTEST_SLICE3A_GREEN.log`.

---

## 2. Endpoints materializados

| Método | Endpoint | Smoke |
|---|---|---|
| GET | `/api/markets/sportsbook/matches` | 200 |
| GET | `/api/markets/sportsbook/live-board` | 200 |
| POST | `/api/markets/sportsbook/portfolio/generate` | 200 · **paridad exacta** |
| GET | `/api/markets/progol/slates/active` | 200 |
| POST | `/api/markets/progol/optimize` | router presente |
| POST | `/api/portfolio/register-ticket` | 200 · escribe ledger |
| GET | `/api/portfolio/ledger-status` | 200 |
| POST | `/api/portfolio/match-thesis` | router presente; LLM no ejercitado |
| GET | `/api/portfolio/{portfolio_id}/pdf` | router presente; PDF real pendiente |
| GET | `/api/leagues` | 200 |
| GET | `/api/leagues/` | 200 |
| GET | `/api/leagues/{league_id}/live-board` | 200 |

Gates (flag false): backtesting y admin → **503** (middleware de fachada).

---

## 3. Paridad Golden Master

- Payload: `LIGAMX-J14-09`, bankroll 1000, certeza 0.80, operador caliente, cobertura DEF.
- Snapshot: `Q_BE_CD_WEB/data/output/backups/qbe_database.baseline.db`.
- Resultado: `capital_total_core_mxn = 80.0`, `roi_global_esperado = 13.71%`, 1 orden.
- `qbe_business` devuelve el JSON **exacto** del Golden Master.

---

## 4. D-B3 resuelto

- `qbe_core/src/core/normalization/normalizer.py` copiado byte-idéntico (`efe0c1d1…`).
- `qbe_storage/src/storage/crest_resolver.py` importa desde `src.core.normalization.normalizer`.
- `qbe_business` no importa `src.ingestion` (AST).

Además se incorporaron a `qbe_core` las dependencias puras que `markets` necesita: `catalog`, `portfolio`, `risk_dial_modulator` y los contratos `decision`, `raw_input`, `consolidated`.

---

## 5. Sellos

- `qbe_core/MANIFEST_FASE1_REV2.sha256`: **8/8**.
- `qbe_storage` gateway: **byte-idéntico** al baseline (`7651763d…`).
- `qbe_business/MANIFEST_SLICE3A.sha256`: manifiesto de cierre (sin caches ni egg-info).

---

## 6. Reservas declaradas

1. **PDF real:** `export.py` fue corregido (`ReportCompiler.compile`, no el inexistente `compile_pdf`). Se validó que el router existe y responde 404 sin registro; no se certificó un PDF con payload real porque la tabla `portfolio_records` está vacía en el snapshot.
2. **Match-thesis:** el endpoint conserva el import diferido de `src.services.gemini_gateway`; el LLM no está portado a Business. No se ejercitó.
3. **`leagues/live-board`:** usa `sync_league_live_board`, que actualiza `matchday_states`; es un lector con escritura de estado, no un GET puro.
4. **Git:** `qbe_business` no es un repositorio Git. El baseline `Q_BE_CD_WEB` sigue limpio salvo `data/qbe_historico.db*`.

---

## 7. Pendiente 3B

- Admin (catálogos, LLM, tasks, drift) y `sovereign`.
- Certificación de PDF con un registro real.
- Decisión sobre LLM de tesis (mover a Ingesta o a un servicio aparte).

**Firma:** Agente Constructor Kybern v12.0.
