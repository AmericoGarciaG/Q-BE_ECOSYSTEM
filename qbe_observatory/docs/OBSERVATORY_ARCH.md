# OBSERVATORY_ARCH — Legislación del módulo `qbe_observatory`

| Campo | Valor |
|---|---|
| **Proyecto** | `Q_BE_ECOSYSTEM` — Fase 2 |
| **Módulo** | `qbe_observatory` |
| **Régimen** | `[DBBD-FUNGIBLE]` para infraestructura/UI; `[DIRGEN-STRICT]` para fronteras de datos y consumo de `qbe_core` |
| **Ubicación** | `Q_BE_ECOSYSTEM/qbe_observatory/` |
| **Estado** | **APROBADA — IMPLEMENTADA EN FASE 2** (D-1/D-6 ratificados) |
| **Fecha** | 2026-10-25 · America/Mexico_City |
| **Alcance** | Legislación previa a código. Este documento no crea `.py` ni `.html`. |

---

## 1. Topología

`qbe_observatory` es una **aplicación FastAPI independiente**, hermana de `qbe_business` y `qbe_ingestion`, que:

- Consume `qbe_core` como **librería instalada** (namespace preservado `src.core.*`).
- **No contiene lógica de apuestas**: no genera carteras, no calcula stakes, no despacha órdenes, no escribe la bóveda.
- **No importa** `src.web` ni `src.ingestion`.
- Se ejecuta en un proceso y puerto propios (`127.0.0.1:8001` por omisión).
- Su superficie es de **solo lectura**: reportes de calibración, backtesting y visualización.

### 1.1. Entrypoint canónico

El servidor web reside en el paquete **`app/`** y su objeto ASGI es **`app.main:app`**
(`app/main.py`, `app = FastAPI(title="Q-BE Observatory")`). No existe ni existió un
módulo `app.py`: la confusión histórica provino de buscar en `src/observatory/`, que
es la **capa de lógica pura**, no la aplicación.

```powershell
# Desde Q_BE_ECOSYSTEM/  (el flag --app-dir es OBLIGATORIO)
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir qbe_observatory --host 127.0.0.1 --port 8001
```

Ejecutar `python app/main.py` **no funciona**: el directorio del script —`qbe_observatory/app/`—
entra en `sys.path` y `from app import config` deja de resolverse.

```text
Q_BE_ECOSYSTEM/
├── qbe_core/                 (instalado, editable)
└── qbe_observatory/
    ├── app/                  Aplicación FastAPI (ASGI: app.main:app)
    ├── src/observatory/      Lógica pura (motores, atribución, lecturas soberanas)
    ├── scripts/              CLI de operación (refresco del snapshot)
    ├── data/                 Snapshot local — NO se versiona
    ├── tests/                The Shield del Observatorio
    ├── docs/                 esta legislación
    ├── pyproject.toml
    └── requirements.txt
```

---

## 2. Fronteras y dependencias

| Dependencia | Uso permitido | Prohibición |
|---|---|---|
| `qbe_core` (`src.core.*`, `src.models.web_schemas`) | `calcular_brier_multicategorico`, `desmarcar_cuotas_proporcional`, motores puros, DTO sellados | Reimplementar Poisson, Dixon-Coles, André, Kelly o cartera |
| `sqlite3` (stdlib) | Solo a través de `app/adapters/db_readonly.py` | Motores de escritura |
| `sqlalchemy` | **Solo** apertura del snapshot en `mode=ro` en `app/routes/backtesting.py` (y su gemelo de UI) | ORM de escritura, migraciones, `commit()` |
| `src.storage.models` | Modelos declarativos de la bóveda 3NF, para consultar el snapshot | Instanciar el gateway transaccional |
| `fastapi`, `jinja2`, `pydantic` | API y renderizado | Lógica financiera o de apuestas |
| `httpx`, `pytest` | Solo testing | Uso en producción |

### 2.1. Enmienda de transparencia (2026-10-28)

La redacción anterior declaraba «Cero SQLAlchemy» y «único punto de conexión
SQLite». Tras los Slices 2A/2B eso dejó de ser cierto y la legislación se alinea
con el código real:

- **SQLAlchemy está presente en runtime**, exclusivamente para abrir el snapshot
  con `sqlite:///file:...?mode=ro&uri=true`. No hay ORM de escritura, ni
  migraciones, ni `commit()`.
- **Hay dos aperturas read-only declaradas**, no una: `app/adapters/db_readonly.py`
  (histórico, sqlite3 puro) y el motor SQLAlchemy del snapshot.
- La garantía de inmutabilidad no depende del número de aperturas: la da SQLite
  con `mode=ro` + `PRAGMA query_only=ON`, verificada por The Shield.

**Invariante de frontera:** `qbe_observatory` no importa `src.web`, `src.ingestion`
ni `qbe_business`; consume modelos declarativos de `src.storage` y jamás instancia
`PersistenceGateway`. Un meta-test AST lo verifica.

---

## 3. Aduana de Datos — Candado CQRS

### 3.1. Aperturas read-only declaradas

**A. Histórico — `app/adapters/db_readonly.py`.**

Es el único punto de conexión del histórico. El adaptador:

1. Construye la URI `file:{ruta_absoluta_con_barras_forward}?mode=ro` y abre con `sqlite3.connect(uri, uri=True, timeout=5.0)`.
2. Configura `row_factory = sqlite3.Row`.
3. Ejecuta **inmediatamente** `PRAGMA query_only = ON;`.
4. Entrega la conexión en un `contextmanager` y la cierra en `finally`.
5. No expone `commit()`, `executemany()` ni helpers de escritura.

```python
# Contrato conceptual — se materializa en Paso 3
@contextmanager
def conexion_solo_lectura(ruta: Path) -> Iterator[sqlite3.Connection]:
    uri = f"file:{ruta.resolve().as_posix()}?mode=ro"
    con = sqlite3.connect(uri, uri=True, timeout=5.0)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA query_only = ON;")
    try:
        yield con
    finally:
        con.close()
```

**B. Snapshot 3NF — `app/routes/backtesting.py`.**

El reporte de backtesting abre `observatory_snapshot.db` con un motor SQLAlchemy
en modo estricto de lectura:

```python
create_engine(f"sqlite:///file:{ruta}?mode=ro&uri=true", connect_args={"check_same_thread": False})
```

Es la segunda y última apertura autorizada. El snapshot lo produce un CLI **fuera
de la app** (§4.5); la app nunca escribe ese archivo, y si no existe responde
**503** con instrucción de materialización — jamás 500.

### 3.2. Prohibiciones absolutas

- **SQLAlchemy prohibido salvo** la apertura read-only del snapshot descrita arriba.
- **Cero** `INSERT`, `UPDATE`, `DELETE`, `CREATE`, `DROP`, `ALTER`, `VACUUM`, `ATTACH` en código de producción.
- **Cero** `commit()` / `rollback()`.
- **Cero** lectura de `data/qbe_database.db` en vivo: si se necesita, se lee un **snapshot estático** (§4.3).
- El adaptador no acepta rutas arbitrarias desde la request; la ruta se resuelve solo desde configuración del servidor.

### 3.3. Defensa en profundidad

Además de `mode=ro` y `query_only=ON`, el adaptador puede validar que la sentencia empiece por `SELECT` o `WITH` antes de ejecutarla. Esa validación es **complementaria**, no sustituta: la garantía última la da SQLite, que responde `sqlite3.OperationalError: attempt to write a readonly database` ante cualquier escritura.

---

## 4. Fuentes de datos

### 4.1. Histórico — fuente primaria del backtesting

- **Archivo:** `qbe_observatory/data/qbe_historico.db` — copia byte-idéntica (21,991,424 B) del histórico congelado, **dentro** del ecosistema.
- **Modo:** `mode=ro`, `query_only=ON`.
- **Contenido verificado:** 4,329 partidos con marcador, 4,329 distribuciones soberanas, 32 snapshots de temporada.
- **Uso:** Brier Score QBE de temporada y desglose por jornada.
- **Aprovisionamiento:** el binario se copia con el despliegue y permanece ignorado por Git (`.gitignore: *.db`); `QBE_HISTORICO_DB` permite reubicarlo sin tocar código. Cero rutas por omisión fuera del monorepo.

### 4.2. Hecho verificado: el histórico NO tiene cuotas de mercado

Auditoría de `fixtures_snapshots.matches_json` en `qbe_historico.db`:

| BD | Fixtures | Con `momios`/`cuotas` |
|---|---:|---:|
| `qbe_historico.db` | 4,329 | **0** |
| `qbe_database.db` (viva) | 153 | **124** |

**Consecuencia:** el **Brier Score de Mercado** y el **Alpha de calibración** no son calculables desde `qbe_historico.db`. Cualquier valor numérico inventado en ese campo violaría `[GOVERNANCE-01]`. La arquitectura los declara **opcionales y nulos** cuando no hay snapshot de mercado.

### 4.3. Snapshot de la BD viva — fuente opcional de mercado

Para comparar QBE contra mercado sin tocar la BD viva:

1. Un script **fuera de la app** crea `qbe_observatory/data/live_snapshot.db` con `sqlite3.Connection.backup` desde `qbe_database.db` (método ya usado por el gateway).
2. La app lee el snapshot con `mode=ro` y `query_only=ON`.
3. Si el snapshot no existe, `mercado_disponible = false`, `brier_mercado = null`, `alpha_calibracion_pct = null`.

**Prohibido:** que FastAPI abra `qbe_database.db` directamente, aunque sea en `mode=ro`. El snapshot es la única frontera autorizada.

> **Dos snapshots distintos, no confundirlos.** `live_snapshot.db` (mercado, opcional,
> §4.3) y `observatory_snapshot.db` (bóveda 3NF, obligatorio para backtesting, §4.5)
> son artefactos independientes con ciclos de vida separados.

### 4.4. Frescura y bloqueo

- El histórico es inmutable para la app; no hay writers.
- El snapshot se refresca fuera de la app; su fecha se publica en `fuente_mercado`.
- Ninguna consulta debe mantener una transacción abierta más de ~2 s. La consulta principal (4,329 filas) se resuelve en una sola lectura y se cierra.

### 4.5. Ciclo de vida de `observatory_snapshot.db` (operación)

El backtesting **no** lee la BD viva: consume un clon 3NF publicado por un CLI.
Sin ese clon, los endpoints de backtesting responden `503` accionable.

```powershell
# Desde qbe_observatory/
..\.venv\Scripts\python.exe -m scripts.refresh_snapshot --max-age-minutes 60
```

Garantías del publicador (`app/services/snapshot_refresh.py`):

| Etapa | Garantía |
|---|---|
| Directorio | `--ensure-dir` (por omisión) crea `data/` de forma idempotente; `--no-ensure-dir` exige que exista |
| Purga | el `.tmp` huérfano de una corrida fallida se elimina antes de copiar |
| Copia | `sqlite3.Connection.backup` desde la BD viva en `mode=ro` |
| Verificación **previa** | `PRAGMA quick_check = ok` **y** `SELECT count(*) FROM matches ≥ --min-partidos`; si falla, no se publica y el snapshot anterior queda intacto |
| Journal | la copia se normaliza a `journal_mode=DELETE`: un lector `mode=ro` no puede crear/borrar `-wal`/`-shm` y no debe dejar basura junto a la vitrina |
| Publicación | `os.replace` atómico en el mismo volumen; se purgan sidecars |
| Reporte | `bytes`, `sha256`, `filas_matches`, frescura |

Códigos de salida (contrato apto para cron, sin tracebacks):

```text
0  snapshot publicado y verificado
2  BD de origen o directorio destino ausentes
3  copia no verificada (quick_check o conteo mínimo); NO se publicó
```

Cron sugerido:

```cron
*/30 * * * * cd /ruta/Q_BE_ECOSYSTEM/qbe_observatory && ../.venv/bin/python -m scripts.refresh_snapshot >> data/refresh.log 2>&1
```

**Versionado:** `qbe_observatory/data/` está ignorado por Git (`.gitignore`: `*.db`,
`qbe_observatory/data/`). El snapshot es un artefacto de despliegue, nunca código.
Límite de frescura publicado: **60 min** (`/api/observatory/snapshot/status`).

---

## 5. Contratos expuestos

### 5.1. Catálogo consolidado de rutas

**HTML (Jinja2, server-rendered):**

| Ruta | Plantilla | Función |
|---|---|---|
| `GET /` | `index.html` | Portada y fronteras |
| `GET /visor` | `visor.html` | Calibración de temporada sobre `qbe_historico.db` (presentación) |
| `GET /backtesting` | `backtesting.html` | UI de backtesting sobre el snapshot 3NF |
| `POST /backtesting/simulate` | `backtesting.html` | Simulación server-side + curva CSS |

**API JSON (solo lectura):**

| Ruta | Estado | Fuente |
|---|---|---|
| `GET /health` | Vigente | Constante |
| `GET /api/observatory/backtesting/calibration-report` | **CANÓNICO** | Snapshot 3NF |
| `GET /api/observatory/calibration-report` | **OBSOLETO — alias** (cabeceras `Deprecation`, `Warning`, `Link`) | Snapshot 3NF (mismo builder) |
| `POST /api/observatory/backtesting/simulate` | Vigente | Snapshot 3NF |
| `GET /api/observatory/snapshot/status` | Vigente | Metadatos del snapshot |
| `GET /api/observatory/manus/models` | Vigente | Artefactos `data/models/*.joblib` |
| `POST /api/observatory/manus/{task}/predict` | Vigente | Ídem (503 sin artefacto) |

### 5.2. Contrato canónico de calibración

`GET /api/observatory/backtesting/calibration-report` devuelve el DTO sellado
`CalibrationReportResponse` de `src.models.web_schemas`:

```text
resumen_temporada  CalibrationSummaryOut   # alias byte-idéntico de resumen_global
resumen_global     CalibrationSummaryOut   # temporada completa
resumen_calibrado  CalibrationSummaryOut   # universo informado S(I)=1
jornadas           list[CalibrationJornadaOut]
```

- **Una sola fuente de verdad:** el agregado se calcula una vez, en
  `_construir_reporte_calibracion`, expuesto públicamente como
  `reporte_calibracion_canonico`.
- **Alias obsoleto:** `/api/observatory/calibration-report` delega en ese mismo
  builder. No recalcula, no traduce, no reimplementa: por construcción devuelve
  `resumen_temporada` idéntico al canónico (lo verifica el Juez I3).
- **Snapshot ausente ⇒ `503`** con instrucción de materialización, en ambos
  endpoints. Un `500` por esta causa está derogado.
- **Contrato retirado (declarado):** `temporada` e `incluir_mercado` ya no existen
  en el alias. El reporte de temporada sobre el histórico sigue disponible como
  presentación HTML en `/visor`.

### 5.3. DTO de presentación del visor (histórico)

```python
class ResumenTemporada(BaseModel):
    brier_qbe: float
    brier_mercado: Optional[float] = None
    alpha_calibracion_pct: Optional[float] = None
    n_partidos_qbe: int
    n_partidos_mercado: int = 0
    brier_qbe_muestra_mercado: Optional[float] = None
    fuente_qbe: str                  # "qbe_historico"
    fuente_mercado: str              # "snapshot_vivo" | "no_disponible"
    mercado_disponible: bool
    nota_metodologica: Optional[str] = None


class JornadaResumen(BaseModel):
    jornada: int
    n_partidos: int
    brier_qbe: float
    brier_mercado: Optional[float] = None
    alpha_calibracion_pct: Optional[float] = None


class CalibrationReportResponse(BaseModel):
    generado_en: datetime
    liga: str
    temporada: Optional[str] = None
    resumen_temporada: ResumenTemporada
    jornadas: list[JornadaResumen]
```

### 5.4. Semántica de las métricas

- **Brier QBE:** `calcular_brier_multicategorico` de `src.core.contracts.portfolio_math` (qbe_core), con `BS = (1/3N) · Σ_i Σ_k (p_ik − y_ik)²`.
- **Brier Mercado:** `desmarcar_cuotas_proporcional` de qbe_core para convertir cuotas 1X2 en probabilidades sin vig; luego el mismo `calcular_brier_multicategorico`.
- **Alpha:** `(1 − BS_QBE / BS_MERCADO) × 100`, con guarda `BS_MERCADO <= 0 ⇒ null`.
- **Muestras:** el Brier QBE se calcula sobre la **temporada seleccionada** (por omisión la más reciente de `seasons`), nunca sobre las 32 temporadas mezcladas. El Brier de mercado usa el subconjunto del snapshot con cuotas y marcador. Para que el Alpha sea comparable, se publica `brier_qbe_muestra_mercado` calculado **sobre ese mismo subconjunto**; el Alpha se calcula con ese valor, no con el de toda la temporada. `nota_metodologica` declara las muestras.
- **Sin datos:** `n_partidos_qbe = 0` ⇒ `brier_qbe = 0.0` (definición canónica de qbe_core) y `nota_metodologica = "sin partidos evaluables"`. No se inventa un Brier perfecto.

### 5.5. Ejemplo de respuesta (histórico sin snapshot de mercado)

> Cifras **ilustrativas**, no certificadas: el ejemplo muestra la forma del contrato, no un resultado del dataset.

```json
{
  "generado_en": "2026-10-25T21:45:00Z",
  "liga": "MEX_LIGAMX",
  "temporada": "MEX_2025_2026_CLAUSURA",
  "resumen_temporada": {
    "brier_qbe": 0.2014,
    "brier_mercado": null,
    "alpha_calibracion_pct": null,
    "n_partidos_qbe": 167,
    "n_partidos_mercado": 0,
    "brier_qbe_muestra_mercado": null,
    "fuente_qbe": "qbe_historico",
    "fuente_mercado": "no_disponible",
    "mercado_disponible": false,
    "nota_metodologica": "Temporada MEX_2025_2026_CLAUSURA. El histórico no porta cuotas 1X2; el Brier de mercado y el Alpha requieren snapshot vivo (D-1)."
  },
  "jornadas": [
    {
      "jornada": 1,
      "n_partidos": 23,
      "brier_qbe": 0.2222,
      "brier_mercado": null,
      "alpha_calibracion_pct": null
    }
  ]
}
```

### 5.6. Consulta canónica (histórico)

```sql
SELECT m.id, m.matchday_num, m.score_home, m.score_away,
       d.p_local, d.p_empate, d.p_visitante
FROM matches AS m
JOIN sovereign_distributions AS d ON d.match_id = m.id
WHERE m.score_home IS NOT NULL
  AND m.score_away IS NOT NULL
  AND m.matchday_num IS NOT NULL
  AND m.season_id = ?          -- temporada seleccionada; por omisión la más reciente
ORDER BY m.matchday_num, m.id;
```

Solo se seleccionan las columnas necesarias; `audit_trace_json` (JSON grande) **no** se lee en el reporte inicial.

---

## 6. UI

### 6.1. Plantillas

- `app/templates/index.html` — portada y fronteras de la aplicación.
- `app/templates/visor.html` — detalle de una jornada (`?jornada=N`), tabla de partidos y barras CSS.
- `app/templates/backtesting.html` — resumen, tabla por jornada, formulario de simulación y curva CSS.
- **No existe `base.html`.** El layout se repite por plantilla; declararlo aquí habría sido legislar un archivo fantasma.

### 6.2. Reglas

- Jinja2 con autoescape; **cero** React, Vue, Svelte o bundler.
- **Cero** JavaScript complejo. Los “gráficos básicos” son barras CSS con `width` calculado en el servidor.
- `app/static/css/theme.css` es una **copia byte-idéntica** de `Q_BE_CD_WEB/src/web/static/css/theme.css`; no se edita el original ni se importa desde el monolito.
- Sin llamadas a APIs externas desde el navegador.
- Enlace de navegación: `index.html` → `visor.html?jornada=N` → `index.html`.

### 6.3. Rutas HTML

| Ruta | Plantilla | Contenido |
|---|---|---|
| `GET /` | `index.html` | Portada + fronteras |
| `GET /visor` | `visor.html` | Detalle de la jornada solicitada |
| `GET /backtesting` | `backtesting.html` | Resumen 3NF, formulario y curva CSS |
| `POST /backtesting/simulate` | `backtesting.html` | Simulación server-side |
| `GET /health` | JSON | `{"status": "ONLINE", "db": "READ_ONLY"}` |

---

## 7. Estructura de directorios

```text
qbe_observatory/
├── app/
│   ├── __init__.py
│   ├── main.py                    FastAPI + Jinja2 (ASGI: app.main:app)
│   ├── config.py                  env + rutas resueltas (nunca desde el CWD)
│   ├── adapters/
│   │   ├── __init__.py
│   │   └── db_readonly.py         Apertura read-only del histórico
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── calibration.py         Alias OBSOLETO + presentación del visor
│   │   ├── backtesting.py         Reporte canónico 3NF + simulación
│   │   ├── backtesting_ui.py      UI server-rendered
│   │   ├── manus.py               Modelos Manus
│   │   └── snapshot.py            Estado de frescura
│   ├── services/
│   │   ├── __init__.py
│   │   ├── manus.py               Carga de artefactos joblib
│   │   └── snapshot_refresh.py    Copia atómica + verificación
│   ├── templates/
│   │   ├── index.html
│   │   ├── visor.html
│   │   └── backtesting.html
│   └── static/
│       └── css/theme.css
├── src/observatory/core/          Lógica pura (simulación, atribución, lecturas)
├── scripts/
│   ├── __init__.py
│   └── refresh_snapshot.py        CLI de operación (--ensure-dir)
├── data/                          observatory_snapshot.db — IGNORADO por Git
├── tests/
│   ├── test_shield_obs.py         A–D: aislamiento, inmutabilidad, núcleo, contrato
│   ├── test_parity_observatory_backtesting.py
│   ├── test_shield_observatory_lifecycle.py  I1–I3: ciclo de vida
│   └── test_slice2b.py
├── docs/
│   └── OBSERVATORY_ARCH.md        este documento
├── pyproject.toml
└── requirements.txt
```

> **Nota:** la estructura anterior listaba `app/services/calibration.py` y
> `app/schemas/calibration.py`, que nunca existieron: el DTO vive en
> `src.models.web_schemas` (sellado en `qbe_core`) y la lógica de presentación en
> `app/routes/calibration.py`. Legislar archivos fantasma fue el origen de la
> deriva que este sprint corrige.

---

## 8. Configuración

| Variable | Default | Uso |
|---|---|---|
| `QBE_HISTORICO_DB` | `qbe_observatory/data/qbe_historico.db` | Fuente del visor (histórico) |
| `OBS_HISTORICO_DB` | — | Alias legado de Fase 2 (subordinado a `QBE_HISTORICO_DB`) |
| `OBS_LIVE_SNAPSHOT` | `qbe_observatory/data/live_snapshot.db` | Fuente opcional de mercado |
| `OBS_BACKTESTING_SNAPSHOT` | `qbe_observatory/data/observatory_snapshot.db` | **Bóveda 3NF del backtesting** |
| `OBS_HOST` | `127.0.0.1` | Bind local |
| `OBS_PORT` | `8001` | Puerto propio |
| `OBS_API_TOKEN` | vacío | Si se define, exige `Authorization: Bearer` |

Las rutas se resuelven con `Path(__file__).resolve()`; **prohibido** depender del `cwd`.

---

## 9. Errores y códigos HTTP

| Caso | Código | Cuerpo |
|---|---|---|
| Reporte válido | `200` | DTO canónico |
| Alias obsoleto invocado | `200` | DTO canónico + `Deprecation: true`, `Warning: 299`, `Link: rel="successor-version"` |
| **Snapshot de backtesting ausente** | **`503`** | `{"detail": "Snapshot de backtesting no disponible: <ruta>. Materialícelo con \`python -m scripts.refresh_snapshot …\`"}` |
| BD histórica ausente | `200` | `/visor` con reporte vacío (`n_partidos_qbe=0`, `fuente_qbe=no_disponible`) y `nota_metodologica` accionable; nunca `500` |
| Snapshot de mercado configurado pero ilegible | `200` | DTO con `mercado_disponible=false` y `nota` |
| `jornada` inválida en `/visor` | `400` | `{"detail": "jornada inválida"}` |
| Error interno | `500` | `{"detail": "error interno"}`; sin traceback al cliente |

**Derogado:** un snapshot ausente ya **no** produce `500`. Era un fallo de
servicio presentado como fallo interno, y ocultaba la acción correctiva.

---

## 10. Pruebas del Paso 2 (The Shield)

El archivo `tests/test_shield_obs.py` debe nacer **RED** y cubrir exactamente:

| Test | Aserción | Cómo se satisface en Paso 3 |
|---|---|---|
| **A. Aislamiento de escritura** | `sqlite3.OperationalError` (o similar) al ejecutar `UPDATE/INSERT/DELETE` a través del adaptador | `mode=ro` + `query_only=ON` |
| **B. Inmutabilidad** | SHA-256 de `qbe_historico.db` idéntico antes/después de abrir y cerrar la conexión | Adaptador cierra sin escribir; solo SELECT |
| **C. Consumo de qbe_core** | `app/main.py` importa `qbe_core` y usa `calcular_brier_multicategorico` | `main.py` importa de `src.core.contracts.portfolio_math` y el servicio lo invoca |
| **D. Contrato** | `GET /api/observatory/calibration-report` → `200` con `resumen_temporada` y `jornadas`; convergencia byte-idéntica con el canónico y cabeceras de deprecación | Ruta alias + builder único + DTO de `src.models.web_schemas` |

**Test C — precisión:** la distribución se llama `qbe_core`, pero su **namespace de importación preservado** es `src.core.*`; no existe un módulo importable llamado `qbe_core`. El import canónico es:

```python
from src.core.contracts.portfolio_math import (
    calcular_brier_multicategorico,
    desmarcar_cuotas_proporcional,
)
```

El test puede hacer `monkeypatch` sobre `app.main.calcular_brier_multicategorico` para verificar la invocación. **No debe buscar el literal `import qbe_core`**: debe verificar el símbolo importado desde `src.core.contracts.portfolio_math` o su presencia en `sys.modules`.

**Test D — fixture:** `QBE_HISTORICO_DB` debe apuntar a `qbe_observatory/data/qbe_historico.db` antes de importar `app.main`; si el archivo no existe, el visor degrada con nota explícita (jamás una BD vacía silenciosa ni cifras fabricadas).

**Test D — re-apuntado (2026-10-28):** tras ratificarse la unificación de rutas, el
Juez D dejó de fijar el contrato del histórico y pasó a fijar el contrato canónico
3NF: claves de `CalibrationSummaryOut`, rango válido del Brier, convergencia
byte-idéntica alias↔canónico y cabeceras de deprecación. Sus aserciones no se
debilitaron: se trasladaron al contrato vigente y se añadió la convergencia.

### 10.1. The Shield — ciclo de vida (`test_shield_observatory_lifecycle.py`)

Juez incorporado en `SPRINT-OBSERVATORY-SNAPSHOT-AND-ARCH-ALIGNMENT`, nacido RED:

| Invariante | Aserción |
|---|---|
| **I1 — Snapshot físico** | `data/observatory_snapshot.db` existe, no está vacío, `PRAGMA quick_check=ok`, porta partidos, rechaza DDL/DML y su SHA-256 no cambia por leerlo |
| **I2 — Arranque ASGI** | `app.main:app` se instancia; `/health` → `{"status":"ONLINE","db":"READ_ONLY"}`; `/` → 200 sin `RuntimeError` |
| **I3 — Resolución de calibración** | canónico y alias → 200; `resumen_temporada` con Brier en `[0,1]`; jornadas no vacías; `Deprecation`/`Link` presentes; `resumen_temporada` idéntico en ambos |

El juez se aísla de dos fugas de estado global conocidas: la mutación de
`config.BACKTESTING_SNAPSHOT` que hacen otros jueces y el listener `connect` de
`qbe_storage.gateway` —que ejecuta `PRAGMA journal_mode=WAL` sobre **toda**
conexión del proceso y rompe cualquier lectura `mode=ro` posterior—. Esa
suspensión es local al juez y se restaura al terminar cada prueba.

### 10.2. The Shield — autonomía (`test_shield_observatory_autonomy.py`)

Juez incorporado en `SPRINT-SANEAMIENTO-OBSERVATORIO-AUTONOMIA-02` para impedir
la regresión del cordón umbilical:

| Invariante | Aserción |
|---|---|
| **A1 — Autonomía de configuración** | `config.HISTORICO_DB` resuelto queda dentro de `Q_BE_ECOSYSTEM` y no cita al monolito |
| **A2 — No contaminación** | ningún `.py` bajo `qbe_observatory/` contiene el token del monolito; la documentación narrativa `.md` queda fuera del alcance (D1) |
| **A3 — Aprovisionamiento** | el histórico existe en `data/`, supera 1 MiB, abre en `mode=ro` y pasa `PRAGMA quick_check` con partidos |

El juez compone el token prohibido en tiempo de ejecución para poder escanearse a
sí mismo sin autoculparse; su fixture de importación añade la raíz del monorepo a
`sys.path`, de modo que es válido tanto desde `Q_BE_ECOSYSTEM/` como desde
`qbe_observatory/`.

---

## 11. Decisiones pendientes de ratificación

| ID | Decisión | Propuesta | Impacto |
|---|---|---|---|
| **D-1** | ¿Cómo se reporta el Brier de Mercado si el histórico no tiene cuotas? | `brier_mercado`/`alpha` **nullable** + `mercado_disponible=false`; snapshot vivo opcional | Evita fabricar un 0.0 que parezca calibración perfecta. **Sigue vigente para el visor (histórico).** El contrato canónico 3NF usa `brier_score_mercado` de `CalibrationSummaryOut`, donde 0.0 es la definición canónica de `qbe_core` para muestra vacía |
| **D-2** | ¿Se permite leer un snapshot de la BD viva en Fase 2? | Sí, solo `live_snapshot.db` creado fuera de la app; nunca la BD viva | Habilita Alpha real sin romper CQRS. **Extendido 2026-10-28** a `observatory_snapshot.db` (§4.5) |
| **D-3** | ¿La UI usa gráficos? | Barras CSS; cero JS | Cumple “sin JavaScript complejo” |
| **D-4** | ¿El endpoint filtra por liga/temporada? | `league_id` y `temporada` opcionales; sin valor, la temporada más reciente de `seasons` | Evita mezclar 32 temporadas. **Enmienda 2026-10-28:** el canónico filtra solo por `league_id`; `temporada` queda en el visor histórico |
| **D-5** | ¿Autenticación? | Bind local; token opcional por env | No bloquea el MVP |
| **D-6** | El literal `qbe_core` no es importable (la distribución usa `src.core.*`) | El Test C verifica el símbolo de `src.core.contracts.portfolio_math`, no la cadena `import qbe_core` | Evita un test imposible de satisfacer sin romper el namespace |

---

## 12. Criterios de aceptación

Vigentes tras `SPRINT-OBSERVATORY-SNAPSHOT-AND-ARCH-ALIGNMENT` (2026-10-28):

1. `pytest qbe_core/tests qbe_business/tests qbe_ingestion/tests qbe_observatory/tests qbe_storage/tests -q` → **EXIT CODE 0** (50/50 al cierre de `SPRINT-SANEAMIENTO-OBSERVATORIO-AUTONOMIA-02`).
2. Los hashes de `qbe_historico.db` (interno y original) y `qbe_database.db` no cambian antes/después de la suite.
3. Canónico y alias → `200`, con `resumen_temporada`/`jornadas` y cifras idénticas.
4. `sqlalchemy` aparece **solo** en la apertura read-only del snapshot; cero ORM de escritura, cero `commit()`.
5. `qbe_core` se importa desde `src.core.*` y el Brier se calcula con `calcular_brier_multicategorico`.
6. `index.html`, `visor.html` y `backtesting.html` renderizan sin JavaScript complejo.
7. **Snapshot materializado y verificado** (I1 del §10.1); sin él, los endpoints de backtesting responden **503** accionable.
8. `MANIFEST_FASE2.sha256` y su linaje (2A, 2B) permanecen válidos.
9. **Autonomía:** `config.HISTORICO_DB` resuelve dentro de `Q_BE_ECOSYSTEM` y ningún `.py` del Observatorio cita al monolito (§10.2).

> **Criterio derogado:** «`app/` no contiene `sqlalchemy`». Era falso desde el
> Slice 2A; mantenerlo habría convertido la legislación en una mentira verificable.

---

## 13. Lo que este módulo NO hace

- No escribe la BD, no crea tablas, no ejecuta migraciones.
- No genera carteras, stakes, triajes ni órdenes.
- No reimplementa Poisson, Dixon-Coles, André, Kelly ni cartera.
- No lee la BD viva directamente.
- No reemplaza al Visor del monolito: lo replica en un proceso aislado y de solo lectura.

---

## 14. Bitácora de revisiones

| Fecha | Revisión | Motivo | Evidencia |
|---|---|---|---|
| 2026-10-25 | v12.0 — original | Legislación previa a código (Fase 2) | `FASE2_CIERRE.md` |
| 2026-10-25 | Slices 2A/2B | Backtesting, UI y Manus introducen la segunda apertura read-only | `FASE2_SLICE2A_CIERRE.md`, `FASE2_SLICE2B_CIERRE.md` |
| **2026-10-28** | **v13.5 — alineación con la realidad** | **Deriva documental detectada en el reporte pericial `RECON-MISSING-OBSERVATORY-APP`: §1 declaraba la app en `src/observatory`, §2/§3 afirmaban «cero SQLAlchemy», §7 listaba archivos inexistentes y no existía catálogo único de rutas.** | `SPRINT-OBSERVATORY-SNAPSHOT-AND-ARCH-ALIGNMENT`; suite 17/17; Juez I1–I3; snapshot `sha256=0016e1ef…` |
| **2026-10-28** | **v13.5 — autonomía del Observatorio** | **Corte del cordón umbilical: `HISTORICO_DB` resolvía por omisión a la carpeta del monolito, impidiendo desplegar el Observatorio en un contenedor independiente. Se aprovisiona el histórico dentro de `data/` y se añade juez de autonomía.** | `SPRINT-SANEAMIENTO-OBSERVATORIO-AUTONOMIA-02`; suite 50/50; Juez A1–A3; histórico `sha256=d51ccbf3…` |

**Enmiendas de esta revisión:** §1.1 entrypoint canónico · §2.1 transparencia de
SQLAlchemy · §3.1 dos aperturas read-only · §4.1 histórico interno · §4.5 ciclo
de vida del snapshot · §5 catálogo consolidado y distinción canónico/obsoleto ·
§6.1–6.3 plantillas y rutas reales · §7 estructura materializada · §8
`QBE_HISTORICO_DB`/`OBS_BACKTESTING_SNAPSHOT` · §9 degradación del visor ·
§10.1–10.2 jueces de ciclo de vida y autonomía · §12 criterios vigentes.

---

**Firma:** Agente Constructor Kybern v13.5 — `[DBBD-FUNGIBLE]` / `[DIRGEN-STRICT]`.
**Estado:** **VIGENTE Y VERIFICADA.** Refleja la topología materializada; toda
afirmación fue comprobada contra el código y la suite en este sprint. Sin archivos
fantasma y sin capacidades declaradas que no existan.
