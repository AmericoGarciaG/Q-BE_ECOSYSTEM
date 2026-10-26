# FASE 2 — SLICE 2B: CIERRE DE UI, SNAPSHOT Y MANUS

| Campo | Valor |
|---|---|
| **Proyecto** | `Q_BE_ECOSYSTEM` — Fase 2 |
| **Slice** | 2B — UI, refresco de snapshot y modelos Manus |
| **Rama** | `feature/fase2-observatory` |
| **Estado** | **14/14 GREEN** (Observatorio) · **30/30** suite ecosistema |
| **Ruta** | `D:\00 SW Projects\Q-BE Casino Deportes\Q_BE_ECOSYSTEM\qbe_observatory` |

---

## 1. Jueces

```text
tests/test_parity_observatory_backtesting.py   3 passed
tests/test_shield_obs.py                       4 passed
tests/test_slice2b.py                          7 passed
--------------------------------------------------------
14 passed, 1 warning in 8.72s
```

Suite ecosistema:

```text
30 passed, 1 warning in 16.46s
Exit Code: 0
```

---

## 2. UI

- `GET /backtesting` → 200, sin `app.js` ni `features.js`.
- `POST /backtesting/simulate` → 200, renderiza métricas y curva CSS.
- `GET /api/observatory/snapshot/status` → edad/frescura.
- Navegación `/` ↔ `/visor` ↔ `/backtesting`.

No se bifurca `app.js`: la UI es Jinja2 server-side.

---

## 3. Snapshot

```bash
python -m scripts.refresh_snapshot --max-age-minutes 60
```

- `sqlite3.Connection.backup` desde la BD viva a un `.tmp`.
- `os.replace` atómico.
- Origen intacto (hash verificado en test).
- CLI certificado: copia 11,317,248 B en < 0.1 s.
- Límite de frescura: 60 min; el estado se publica en la UI y en la API.

---

## 4. Manus

```text
GET  /api/observatory/manus/models
POST /api/observatory/manus/{task}/predict
```

- 3 tareas: `task_a`, `task_b`, `task_c`.
- Sin artefacto → **503**.
- Tarea desconocida → **404**.
- Con `LinearRegression` real en joblib: predicción **200** verificada.
- `pandas`/`scikit-learn` instalados y usados solo en el Observatorio.

---

## 5. Reservas declaradas

1. **Modelos Manus reales:** no existen artefactos A/B/C; los endpoints devuelven 503. El test con `LinearRegression` certifica el camino técnico.
2. **Refresco:** es un CLI apto para cron; no hay daemon/systemd en este slice.
3. **UI:** server-rendered; sin gráficos JS; la curva es CSS.
4. **Snapshot:** el Observatorio sigue leyendo solo `data/observatory_snapshot.db`; la BD viva solo la toca el CLI de refresco.
5. **Simulación:** la UI usa el motor read-only; no escribe.

---

## 6. Git

- Rama: `feature/fase2-observatory`.
- Commit y tag `slice-2b-green` al cierre.
- `git status` limpio.

**Firma:** Agente Constructor Kybern v12.0.
