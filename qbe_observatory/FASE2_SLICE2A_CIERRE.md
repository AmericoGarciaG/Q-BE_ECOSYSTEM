# FASE 2 — SLICE 2A: CIERRE DEL MOTOR DE BACKTESTING

| Campo | Valor |
|---|---|
| **Proyecto** | `Q_BE_ECOSYSTEM` — Fase 2 |
| **Slice** | 2A — Backtesting y calibración |
| **Rama** | `feature/fase2-observatory` |
| **Estado** | **7/7 GREEN** (Observatorio) · **23/23** suite ecosistema |
| **Ruta** | `D:\00 SW Projects\Q-BE Casino Deportes\Q_BE_ECOSYSTEM\qbe_observatory` |

---

## 1. Jueces

```text
tests/test_parity_observatory_backtesting.py::test_paridad_calibracion_backtesting PASSED
tests/test_parity_observatory_backtesting.py::test_simulacion_backtesting_responde PASSED
tests/test_parity_observatory_backtesting.py::test_dependencias_analiticas_son_solo_del_observatorio PASSED
tests/test_shield_obs.py::test_a_aislamiento_de_escritura PASSED
tests/test_shield_obs.py::test_b_inmutabilidad_de_la_bd PASSED
tests/test_shield_obs.py::test_c_consumo_de_qbe_core PASSED
tests/test_shield_obs.py::test_d_contrato_del_endpoint PASSED

7 passed, 1 warning in 3.55s
```

Suite ecosistema:

```text
23 passed, 1 warning in 12.68s
Exit Code: 0
```

---

## 2. Paridad con el monolito

| Elemento | Valor |
|---|---|
| Golden Master | `tests/golden_master_backtesting.json` |
| Tamaño | **2,472,426 B** |
| Jornadas | 14 |
| Comparación | JSON completo, igualdad exacta |
| Snapshot | `qbe_database.baseline.db` (copia G0) |

La ruta `GET /api/observatory/backtesting/calibration-report?league_id=1`
devuelve **el mismo reporte** que `GET /api/markets/backtesting/calibration-report`
del monolito congelado.

---

## 3. Rutas y motor

```text
qbe_observatory/
├── app/routes/backtesting.py          calibración + simulación
├── app/main.py                        incluye el router
└── src/observatory/core/
    ├── simulation_engine.py
    ├── sovereign_reads.py
    ├── factor_attribution.py
    └── context_provider.py
```

- `GET /api/observatory/backtesting/calibration-report`
- `POST /api/observatory/backtesting/simulate` (smoke 200, `status=EXITO`)
- `_ReadOnlyGateway` + `get_db_ro` usan `file:...?mode=ro&uri=true`.
- Fuente: `OBS_BACKTESTING_SNAPSHOT` (default `data/observatory_snapshot.db`); nunca la BD viva.
- `context_provider`/`factor_attribution` importan desde `src.observatory.core`, no desde `src.core`.
- `simulation_engine` importa `altitud_estadio` desde `context_provider` (se eliminó el import de `scripts.laboratorio`).

---

## 4. Dependencias

`qbe_observatory/pyproject.toml` declara:

```text
sqlalchemy, pandas, scikit-learn
```

`qbe_core` y `qbe_business` **no** las declaran. El juez
`test_dependencias_analiticas_son_solo_del_observatorio` lo certifica.

---

## 5. Reservas declaradas

1. **UI de backtesting:** el Slice 2A expone API y motor; la SPA/curvas de capital son del 2B.
2. **pandas/sklearn:** declaradas como dependencias propias; aún no se usan en el código de 2A.
3. **Snapshot:** el backtesting lee una copia G0; el refresco del snapshot vivo queda fuera de la app.
4. **Simulación:** smoke con rango `1-2`; no se certificó una corrida completa de temporada.
5. **`qbe_business`:** no se tocó en 2A.

---

## 6. Git

- Rama: `feature/fase2-observatory`.
- Commit y tag `slice-2a-green` al cierre.
- `git status` limpio.

**Firma:** Agente Constructor Kybern v12.0.
