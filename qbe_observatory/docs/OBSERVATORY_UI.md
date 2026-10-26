# OBSERVATORY_UI — Slice 2B

| Campo | Valor |
|---|---|
| **Módulo** | `qbe_observatory` |
| **Slice** | 2B — UI, snapshot y Manus |
| **Régimen** | `[DBBD-FUNGIBLE]` UI; `[DIRGEN-STRICT]` motor |

---

## 1. UI de backtesting

| Ruta | Plantilla | Función |
|---|---|---|
| `GET /backtesting` | `backtesting.html` | resumen, tabla por jornada, formulario |
| `POST /backtesting/simulate` | `backtesting.html` | simulación server-side + curva CSS |

- Sin JavaScript: no se copia ni bifurca `app.js` de la Mesa.
- No carga `features.js`, `app.js` ni assets transaccionales.
- La curva de capital son barras CSS normalizadas en el servidor.
- Navegación: `/` ↔ `/visor` ↔ `/backtesting`.

### APIs consumidas por la UI

```text
GET  /api/observatory/backtesting/calibration-report
POST /api/observatory/backtesting/simulate
GET  /api/observatory/snapshot/status
GET  /api/observatory/manus/models
POST /api/observatory/manus/{task}/predict
```

---

## 2. Refresco del snapshot

`scripts/refresh_snapshot.py`:

```bash
python -m scripts.refresh_snapshot --max-age-minutes 60
```

- `sqlite3.Connection.backup` desde la BD viva (solo lectura) a un `.tmp`.
- `os.replace` publica el snapshot atómicamente.
- No bloquea escrituras de la BD viva.
- El Observatorio solo lee `data/observatory_snapshot.db`.
- `GET /api/observatory/snapshot/status` publica edad y frescura; el límite es 60 min.

Cron sugerido:

```cron
*/30 * * * * cd /ruta/Q_BE_ECOSYSTEM/qbe_observatory && .venv/bin/python -m scripts.refresh_snapshot >> data/refresh.log 2>&1
```

---

## 3. Manus (Tareas A/B/C)

`app/services/manus.py` + `app/routes/manus.py`:

```text
GET  /api/observatory/manus/models
POST /api/observatory/manus/{task}/predict
```

- Artefactos: `data/models/task_a.joblib`, `task_b.joblib`, `task_c.joblib`.
- Carga con `joblib`; predicción con `pandas` + `scikit-learn`.
- Sin artefacto: **503** controlado.
- Tarea desconocida: **404**.
- La UI lista los tres modelos y su disponibilidad.

---

## 4. Dependencias

`qbe_observatory` declara y usa:

```text
pandas, scikit-learn, joblib, python-multipart
```

`qbe_core` y `qbe_business` no las declaran.

---

**Firma:** Agente Constructor Kybern v12.0.
