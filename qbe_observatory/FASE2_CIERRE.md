# FASE 2 — CIERRE DEL OBSERVATORIO (`qbe_observatory`)

| Campo | Valor |
|---|---|
| **Proyecto** | `Q_BE_ECOSYSTEM` — Fase 2 |
| **Módulo** | `qbe_observatory` |
| **Régimen** | `[DBBD-FUNGIBLE]` para UI/infraestructura; `[DIRGEN-STRICT]` para fronteras de datos y matemáticas |
| **Fecha** | 2026-10-25 · America/Mexico_City |
| **Ruta absoluta** | `D:\00 SW Projects\Q-BE Casino Deportes\Q_BE_ECOSYSTEM\qbe_observatory` |
| **Estado** | **CERRADA — 4/4 VERDE, Exit Code 0** |
| **Baseline** | `Q_BE_CD_WEB` sin cambios de código; BD intactas |

---

## 1. Resultado del Bucle Reflexivo

```text
$ .\.venv\Scripts\python.exe -m pytest qbe_observatory/tests/test_shield_obs.py -v
...
qbe_observatory\tests\test_shield_obs.py::test_a_aislamiento_de_escritura PASSED [ 25%]
qbe_observatory\tests\test_shield_obs.py::test_b_inmutabilidad_de_la_bd PASSED [ 50%]
qbe_observatory\tests\test_shield_obs.py::test_c_consumo_de_qbe_core PASSED [ 75%]
qbe_observatory\tests\test_shield_obs.py::test_d_contrato_del_endpoint PASSED [100%]

4 passed, 1 warning in 1.54s
Exit Code: 0
```

Log completo: `PYTEST_GREEN.log`.

---

## 2. Contrato del endpoint verificado

```text
GET /api/observatory/calibration-report → 200
liga: MEX_LIGAMX
temporada: MEX_2025_2026_CLAUSURA
n_partidos_qbe: 167
brier_qbe: 0.2014
brier_mercado: null
alpha_calibracion_pct: null
mercado_disponible: false
jornadas: 17
```

- `brier_mercado` y `alpha_calibracion_pct` son `None`, nunca `0.0` (D-1).
- El histórico no porta cuotas 1X2 (0/4,329); el contrato lo declara.
- `jornada 1`: 23 partidos, Brier 0.2222; `jornada 17`: 9 partidos, Brier 0.1719.

---

## 3. Aduana CQRS verificada

| Control | Evidencia |
|---|---|
| Solo `app/adapters/db_readonly.py` abre SQLite | Único `sqlite3.connect` del código de producción |
| URI `mode=ro` | `file:{ruta}?mode=ro`, `uri=True` |
| `PRAGMA query_only = ON` | Ejecutado antes de entregar la conexión |
| Sin SQLAlchemy | 0 imports de `sqlalchemy` en `app/` |
| Sin escrituras | Test A: `INSERT` → `sqlite3.OperationalError` |
| BD inmutable | Test B: hash SHA-256 idéntico antes/después de leer |
| BD viva intacta | `qbe_database.db` `b5fd…`; `qbe_historico.db` `d51c…` |

---

## 4. Estructura materializada

```text
qbe_observatory/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── main.py
│   ├── adapters/
│   │   ├── __init__.py
│   │   └── db_readonly.py
│   ├── routes/
│   │   ├── __init__.py
│   │   └── calibration.py
│   ├── templates/
│   │   ├── index.html
│   │   └── visor.html
│   └── static/
│       └── css/theme.css          (copia byte-idéntica del baseline)
├── tests/
│   └── test_shield_obs.py
├── docs/
│   └── OBSERVATORY_ARCH.md
├── requirements.txt
├── pyproject.toml
├── MANIFEST_FASE2.sha256
├── PYTEST_GREEN.log
└── FASE2_CIERRE.md
```

---

## 5. Desviaciones declaradas

### 5.1. Ruta real del histórico

La directiva indicaba `sqlite3.connect("file:../data/qbe_historico.db?mode=ro")`. Esa ruta no existe desde `qbe_observatory` (`../data` resolvería a `Q_BE_ECOSYSTEM/data`). La implementación resuelve la ruta real:

```text
Q_BE_CD_WEB/data/qbe_historico.db
```

mediante `OBS_HISTORICO_DB`, con default calculado desde `app/config.py`; nunca desde el CWD.

### 5.2. Temporada por omisión

El histórico contiene **32 temporadas**. Agrupar solo por `matchday_num` mezclaba 32 temporadas en una misma “jornada” (la jornada 1 arrojaba 642 partidos). La implementación reporta por omisión la **temporada más reciente de `seasons`** (`MEX_2025_2026_CLAUSURA`) y acepta `?temporada=...` para las demás. Así `resumen_temporada` significa una temporada real, no un agregado de 32.

### 5.3. Brier de mercado

No se implementó lectura de la BD viva ni snapshot en esta fase. `mercado_disponible=false`, `brier_mercado=null`, `alpha=null`. El snapshot vivo queda para una fase posterior, conforme a D-1/D-2.

### 5.4. Test C en verde desde el estado RED

`qbe_core` ya estaba instalado en Fase 1; el juez C verificó el símbolo canónico y pasó. Es la garantía de consumo del núcleo, no un fallo del Observatorio.

---

## 6. Manifiesto

`MANIFEST_FASE2.sha256` contiene los hashes SHA-256 de **todos** los archivos de `qbe_observatory/`, excluyendo:

- el propio manifiesto,
- `__pycache__/`,
- `.pytest_cache/`,
- `qbe_observatory.egg-info/`.

Formato:

```text
<hash_sha256>  <ruta_relativa>
```

La verificación se ejecuta recomputando cada hash; el reporte de cierre certifica **16/16**.

---

## 7. Cómo ejecutar

```powershell
cd "D:\00 SW Projects\Q-BE Casino Deportes\Q_BE_ECOSYSTEM"
.\.venv\Scripts\python.exe -m pytest qbe_observatory/tests/test_shield_obs.py -v
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir qbe_observatory --host 127.0.0.1 --port 8001
```

Rutas:

- `http://127.0.0.1:8001/` — índice.
- `http://127.0.0.1:8001/visor` — visor.
- `http://127.0.0.1:8001/api/observatory/calibration-report` — JSON.

---

## 8. Frontera respetada

- `Q_BE_CD_WEB` no fue modificado: `git status` solo muestra los `data/qbe_historico.db*` que nunca se versionaron.
- No se escribió en `qbe_database.db` ni en `qbe_historico.db`.
- No se copió `tests/shield/` ni `progol_math.py`.
- La UI no usa React/Vue/JS complejo; tablas y formulario GET con `theme.css`.

**Firma:** Agente Constructor Kybern v12.0 — `[DBBD-FUNGIBLE]` / `[DIRGEN-STRICT]`.
