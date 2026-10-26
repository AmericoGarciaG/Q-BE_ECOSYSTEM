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
- **No importa** `src.web`, `src.storage` ni `src.ingestion`.
- Se ejecuta en un proceso y puerto propios (`127.0.0.1:8001` por omisión).
- Su superficie es de **solo lectura**: reportes de calibración, backtesting y visualización.

```text
Q_BE_ECOSYSTEM/
├── qbe_core/                 (instalado, editable)
└── qbe_observatory/
    ├── app/                  FastAPI + adaptadores + servicios + UI
    ├── tests/                The Shield del Observatorio
    ├── docs/                 esta legislación
    ├── pyproject.toml
    └── requirements.txt
```

---

## 2. Fronteras y dependencias

| Dependencia | Uso permitido | Prohibición |
|---|---|---|
| `qbe_core` (`src.core.*`) | `calcular_brier_multicategorico`, `desmarcar_cuotas_proporcional`, motores puros | Reimplementar Poisson, Dixon-Coles, André, Kelly o cartera |
| `sqlite3` (stdlib) | Solo a través de `app/adapters/db_readonly.py` | SQLAlchemy, ORM, motores de escritura |
| `fastapi`, `jinja2`, `pydantic` | API y renderizado | Lógica financiera o de apuestas |
| `httpx`, `pytest` | Solo testing | Uso en producción |

**Invariante de frontera:** `qbe_observatory` no importa nada de `qbe_business` ni de `qbe_ingestion`; un meta-test AST lo verificará.

---

## 3. Aduana de Datos — Candado CQRS

### 3.1. Único punto de conexión

**Archivo:** `app/adapters/db_readonly.py`.

Ningún otro módulo de la aplicación abre SQLite. El adaptador:

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

### 3.2. Prohibiciones absolutas

- **Cero SQLAlchemy** (`import sqlalchemy` prohibido en todo `app/`).
- **Cero** `INSERT`, `UPDATE`, `DELETE`, `CREATE`, `DROP`, `ALTER`, `VACUUM`, `ATTACH` en código de producción.
- **Cero** `commit()` / `rollback()`.
- **Cero** lectura de `data/qbe_database.db` en vivo: si se necesita, se lee un **snapshot estático** (§4.3).
- El adaptador no acepta rutas arbitrarias desde la request; la ruta se resuelve solo desde configuración del servidor.

### 3.3. Defensa en profundidad

Además de `mode=ro` y `query_only=ON`, el adaptador puede validar que la sentencia empiece por `SELECT` o `WITH` antes de ejecutarla. Esa validación es **complementaria**, no sustituta: la garantía última la da SQLite, que responde `sqlite3.OperationalError: attempt to write a readonly database` ante cualquier escritura.

---

## 4. Fuentes de datos

### 4.1. Histórico — fuente primaria del backtesting

- **Archivo:** `Q_BE_CD_WEB/data/qbe_historico.db`.
- **Modo:** `mode=ro`, `query_only=ON`.
- **Contenido verificado:** 4,329 partidos con marcador, 4,329 distribuciones soberanas, 32 snapshots de temporada.
- **Uso:** Brier Score QBE de temporada y desglose por jornada.
- **No se copia** al ecosistema: se lee desde su ubicación original.

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

### 4.4. Frescura y bloqueo

- El histórico es inmutable para la app; no hay writers.
- El snapshot se refresca fuera de la app; su fecha se publica en `fuente_mercado`.
- Ninguna consulta debe mantener una transacción abierta más de ~2 s. La consulta principal (4,329 filas) se resuelve en una sola lectura y se cierra.

---

## 5. Contrato del endpoint

### 5.1. Ruta

```http
GET /api/observatory/calibration-report
```

Parámetros opcionales:

| Parámetro | Tipo | Default | Descripción |
|---|---|---|---|
| `league_id` | `str \| null` | `null` | Filtra por `competitions.id` (ej. `MEX_LIGAMX`). Sin valor: la liga de la temporada. |
| `temporada` | `str \| null` | `null` | `seasons.id` (ej. `MEX_2025_2026_CLAUSURA`). Sin valor: la temporada más reciente de `seasons`. |
| `incluir_mercado` | `bool` | `true` | Si es `false`, no intenta leer el snapshot de mercado. |

### 5.2. DTO `CalibrationReportResponse`

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

### 5.3. Semántica de las métricas

- **Brier QBE:** `calcular_brier_multicategorico` de `src.core.contracts.portfolio_math` (qbe_core), con `BS = (1/3N) · Σ_i Σ_k (p_ik − y_ik)²`.
- **Brier Mercado:** `desmarcar_cuotas_proporcional` de qbe_core para convertir cuotas 1X2 en probabilidades sin vig; luego el mismo `calcular_brier_multicategorico`.
- **Alpha:** `(1 − BS_QBE / BS_MERCADO) × 100`, con guarda `BS_MERCADO <= 0 ⇒ null`.
- **Muestras:** el Brier QBE se calcula sobre la **temporada seleccionada** (por omisión la más reciente de `seasons`), nunca sobre las 32 temporadas mezcladas. El Brier de mercado usa el subconjunto del snapshot con cuotas y marcador. Para que el Alpha sea comparable, se publica `brier_qbe_muestra_mercado` calculado **sobre ese mismo subconjunto**; el Alpha se calcula con ese valor, no con el de toda la temporada. `nota_metodologica` declara las muestras.
- **Sin datos:** `n_partidos_qbe = 0` ⇒ `brier_qbe = 0.0` (definición canónica de qbe_core) y `nota_metodologica = "sin partidos evaluables"`. No se inventa un Brier perfecto.

### 5.4. Ejemplo de respuesta (histórico sin snapshot de mercado)

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

### 5.5. Consulta canónica (histórico)

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

- `app/templates/base.html` — layout mínimo compartido (opcional; sin lógica).
- `app/templates/index.html` — resumen de temporada + tabla de jornadas.
- `app/templates/visor.html` — detalle de una jornada (`?jornada=N`), tabla de partidos y barras CSS.

### 6.2. Reglas

- Jinja2 con autoescape; **cero** React, Vue, Svelte o bundler.
- **Cero** JavaScript complejo. Los “gráficos básicos” son barras CSS con `width` calculado en el servidor.
- `app/static/css/theme.css` es una **copia byte-idéntica** de `Q_BE_CD_WEB/src/web/static/css/theme.css`; no se edita el original ni se importa desde el monolito.
- Sin llamadas a APIs externas desde el navegador.
- Enlace de navegación: `index.html` → `visor.html?jornada=N` → `index.html`.

### 6.3. Rutas HTML

| Ruta | Plantilla | Contenido |
|---|---|---|
| `GET /` | `index.html` | Tarjetas de resumen + tabla de jornadas |
| `GET /visor` | `visor.html` | Detalle de la jornada solicitada |
| `GET /health` | JSON | `{"status": "ONLINE", "db": "READ_ONLY"}` |

---

## 7. Estructura de directorios

```text
qbe_observatory/
├── app/
│   ├── __init__.py
│   ├── main.py                    FastAPI, rutas, Jinja2
│   ├── config.py                 env + rutas resueltas
│   ├── adapters/
│   │   ├── __init__.py
│   │   └── db_readonly.py        ÚNICO punto SQLite
│   ├── services/
│   │   ├── __init__.py
│   │   └── calibration.py        reporte + agregación
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── calibration.py        DTO Pydantic
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html
│   │   └── visor.html
│   └── static/
│       └── css/theme.css
├── tests/
│   └── test_shield_obs.py        (Paso 2)
├── docs/
│   └── OBSERVATORY_ARCH.md       este documento
├── pyproject.toml
├── requirements.txt
└── MANIFEST_FASE2.sha256         (Paso 3)
```

---

## 8. Configuración

| Variable | Default | Uso |
|---|---|---|
| `OBS_HISTORICO_DB` | `../Q_BE_CD_WEB/data/qbe_historico.db` resuelto desde `Q_BE_ECOSYSTEM` | Fuente QBE |
| `OBS_LIVE_SNAPSHOT` | `qbe_observatory/data/live_snapshot.db` | Fuente opcional de mercado |
| `OBS_HOST` | `127.0.0.1` | Bind local |
| `OBS_PORT` | `8001` | Puerto propio |
| `OBS_API_TOKEN` | vacío | Si se define, exige `Authorization: Bearer` |

Las rutas se resuelven con `Path(__file__).resolve()`; **prohibido** depender del `cwd`.

---

## 9. Errores y códigos HTTP

| Caso | Código | Cuerpo |
|---|---|---|
| Reporte válido | `200` | DTO |
| BD histórica ausente | `503` | `{"detail": "histórico no disponible"}` |
| Snapshot de mercado configurado pero ilegible | `200` | DTO con `mercado_disponible=false` y `nota` |
| `jornada` inválida en `/visor` | `400` | `{"detail": "jornada inválida"}` |
| Error interno | `500` | `{"detail": "error interno"}`; sin traceback al cliente |

---

## 10. Pruebas del Paso 2 (The Shield)

El archivo `tests/test_shield_obs.py` debe nacer **RED** y cubrir exactamente:

| Test | Aserción | Cómo se satisface en Paso 3 |
|---|---|---|
| **A. Aislamiento de escritura** | `sqlite3.OperationalError` (o similar) al ejecutar `UPDATE/INSERT/DELETE` a través del adaptador | `mode=ro` + `query_only=ON` |
| **B. Inmutabilidad** | SHA-256 de `qbe_historico.db` idéntico antes/después de abrir y cerrar la conexión | Adaptador cierra sin escribir; solo SELECT |
| **C. Consumo de qbe_core** | `app/main.py` importa `qbe_core` y usa `calcular_brier_multicategorico` | `main.py` importa de `src.core.contracts.portfolio_math` y el servicio lo invoca |
| **D. Contrato** | `GET /api/observatory/calibration-report` → `200` con `resumen_temporada` y `jornadas` | Ruta + DTO + datos históricos |

**Test C — precisión:** la distribución se llama `qbe_core`, pero su **namespace de importación preservado** es `src.core.*`; no existe un módulo importable llamado `qbe_core`. El import canónico es:

```python
from src.core.contracts.portfolio_math import (
    calcular_brier_multicategorico,
    desmarcar_cuotas_proporcional,
)
```

El test puede hacer `monkeypatch` sobre `app.main.calcular_brier_multicategorico` para verificar la invocación. **No debe buscar el literal `import qbe_core`**: debe verificar el símbolo importado desde `src.core.contracts.portfolio_math` o su presencia en `sys.modules`.

**Test D — fixture:** `OBS_HISTORICO_DB` debe apuntar a `Q_BE_CD_WEB/data/qbe_historico.db` antes de importar `app.main`; si el archivo no existe, el test debe fallar de forma explícita (no usar una BD vacía silenciosa).

---

## 11. Decisiones pendientes de ratificación

| ID | Decisión | Propuesta | Impacto |
|---|---|---|---|
| **D-1** | ¿Cómo se reporta el Brier de Mercado si el histórico no tiene cuotas? | `brier_mercado`/`alpha` **nullable** + `mercado_disponible=false`; snapshot vivo opcional | Evita fabricar un 0.0 que parezca calibración perfecta |
| **D-2** | ¿Se permite leer un snapshot de la BD viva en Fase 2? | Sí, solo `live_snapshot.db` creado fuera de la app; nunca la BD viva | Habilita Alpha real sin romper CQRS |
| **D-3** | ¿La UI usa gráficos? | Barras CSS; cero JS | Cumple “sin JavaScript complejo” |
| **D-4** | ¿El endpoint filtra por liga/temporada? | `league_id` y `temporada` opcionales; sin valor, la temporada más reciente de `seasons` | Evita mezclar 32 temporadas en un mismo `jornada` |
| **D-5** | ¿Autenticación? | Bind local; token opcional por env | No bloquea el MVP |
| **D-6** | El literal `qbe_core` no es importable (la distribución usa `src.core.*`) | El Test C verifica el símbolo de `src.core.contracts.portfolio_math`, no la cadena `import qbe_core` | Evita un test imposible de satisfacer sin romper el namespace |

---

## 12. Criterios de aceptación de Fase 2

1. `pytest qbe_observatory/tests/test_shield_obs.py` → **4/4 verde**.
2. El hash de `qbe_historico.db` no cambia antes/después de la suite.
3. `GET /api/observatory/calibration-report` → `200`, claves `resumen_temporada` y `jornadas`.
4. `app/` no contiene `sqlalchemy` ni sentencias de escritura.
5. `qbe_core` se importa desde `src.core.*` y el Brier se calcula con `calcular_brier_multicategorico`.
6. `index.html` y `visor.html` renderizan sin JavaScript complejo.
7. `MANIFEST_FASE2.sha256` generado con hashes de todos los archivos creados.

---

## 13. Lo que este módulo NO hace

- No escribe la BD, no crea tablas, no ejecuta migraciones.
- No genera carteras, stakes, triajes ni órdenes.
- No reimplementa Poisson, Dixon-Coles, André, Kelly ni cartera.
- No lee la BD viva directamente.
- No reemplaza al Visor del monolito: lo replica en un proceso aislado y de solo lectura.

---

**Firma:** Agente Constructor Kybern v12.0 — `[DBBD-FUNGIBLE]` / `[DIRGEN-STRICT]`.
**Estado:** Documento listo para revisión del Custodio. **No se creó ningún archivo `.py` ni `.html`.**
