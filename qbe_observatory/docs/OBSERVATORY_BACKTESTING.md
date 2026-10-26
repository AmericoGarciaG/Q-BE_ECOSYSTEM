# OBSERVATORY_BACKTESTING — Addendum Slice 2A

| Campo | Valor |
|---|---|
| **Módulo** | `qbe_observatory` |
| **Slice** | 2A — backtesting y calibración |
| **Régimen** | `[DBBD-FUNGIBLE]` para rutas; `[DIRGEN-STRICT]` para el motor |
| **Estado** | Implementado y en paridad con el monolito |

---

## 1. Topología C+D

El Observatorio conserva su superficie histórica de solo lectura
(`app/adapters/db_readonly.py`, `sqlite3` + `mode=ro`) y añade el backtesting
sobre los **mismos datos** con un motor SQLAlchemy **read-only**:

```text
snapshot (copia G0)
   ├── app/adapters/db_readonly.py     sqlite3 mode=ro  → calibración histórica
   └── app/routes/backtesting.py       SQLAlchemy URI   → calibración + simulación
                                       file:...?mode=ro&uri=true
```

Ninguna ruta de backtesting abre la bóveda viva. El snapshot se prepara fuera de la app
en `OBS_BACKTESTING_SNAPSHOT` (default `qbe_observatory/data/observatory_snapshot.db`).
Si el archivo no existe, la ruta responde con error controlado en vez de abrir la BD viva.

---

## 2. Rutas

| Método | Ruta | Origen |
|---|---|---|
| GET | `/api/observatory/backtesting/calibration-report` | monolito `markets.py` |
| POST | `/api/observatory/backtesting/simulate` | monolito `markets.py` |

La ruta histórica `/api/observatory/calibration-report` se conserva.

---

## 3. Núcleo analítico

```text
qbe_observatory/src/observatory/core/
├── simulation_engine.py     (copiado del monolito; import de altitud corregido)
├── sovereign_reads.py
├── factor_attribution.py
└── context_provider.py      (imports locales al Observatorio)
```

- `simulation_engine` recibe `_ReadOnlyGateway`, no el `PersistenceGateway` de escritura.
- `context_provider` importa `factor_attribution`/`sovereign_reads` desde
  `src.observatory.core`, no desde `src.core`, para no contaminar `qbe_core`.
- La aritmética sigue en `qbe_core` (`src.core.contracts.portfolio_math`,
  `src.core.sovereign_pipeline`).

---

## 4. Dependencias

`qbe_observatory` declara **pandas** y **scikit-learn** como dependencias propias.
`qbe_core` y `qbe_business` no las declaran ni las importan.

---

## 5. Paridad

- Golden Master: `tests/golden_master_backtesting.json` (2,472,426 B, 14 jornadas).
- `test_paridad_calibracion_backtesting` compara el JSON completo contra el monolito.
- `test_simulacion_backtesting_responde` certifica el contrato de simulación.
- `test_dependencias_analiticas_son_solo_del_observatorio` certifica el aislamiento.

---

**Firma:** Agente Constructor Kybern v12.0.
