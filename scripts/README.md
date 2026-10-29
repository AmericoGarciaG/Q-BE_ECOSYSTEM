# Scripts — Activos de Laboratorio e Investigación

**Origen:** migración reflexiva desde `Q_BE_CD_WEB/scripts/` (Fase 4).  
**Régimen:** solo lectura; cero escritura sobre la base viva.

## Entorno

Los scripts usan el namespace `src.*` de los paquetes editables del ecosistema:

- `qbe_core` → `src.core`, `src.models`
- `qbe_storage` → `src.storage`, `src.config`
- `qbe_business` → `src.web`
- `qbe_observatory` → `src.observatory`, `app`
- `qbe_ingestion` → `src.ingestion`

Para apuntar los sandboxes al snapshot atómico en lugar de una base viva:

```powershell
$env:DATABASE_URL = "sqlite:///data/snapshots/qbe_database_snapshot.db"
.\.venv\Scripts\python.exe -m scripts.laboratorio.sandbox_contexto_shocks_pipeline --help
```

## Lanzador del Ecosistema (utilidad de desarrollo)

`lanzador_ecosistema.py` levanta y apaga los tres servidores procesales como un
fixture E2E atómico. Es una utilidad `[DBBD-FUNGIBLE]`: vive en `scripts/`, no
importa `src.*` ni `qbe_core`, no abre SQLite y no publica snapshots. No crea
nodo en `docs/ARCH.md` ni ID en `docs/ID_REGISTRY.md` (dictamen del Arquitecto:
utilidad fungible sin contrato de negocio).

### Uso

```powershell
# Plan sin abrir sockets: imprime argv, cwd y entorno efectivo.
.\.venv\Scripts\python.exe scripts\lanzador_ecosistema.py --plan

# Plan + sondas de puerto, sin arrancar ningún proceso.
.\.venv\Scripts\python.exe scripts\lanzador_ecosistema.py --preflight

# Arranque real: bloquea hasta Ctrl+C y apaga los tres procesos.
.\.venv\Scripts\python.exe scripts\lanzador_ecosistema.py
```

Con el lanzador arriba, la certificación E2E se ejecuta en otra terminal:

```powershell
.\.venv\Scripts\python.exe scripts\verificar_ecosistema_e2e.py
```

### Contrato de arranque

| Pilar | Comando (cwd = raíz) | Puerto |
|---|---|---|
| Mesa de Apuestas | `.venv\Scripts\python.exe -m uvicorn src.web.app:app` | `8000` (constante legislada) |
| Observatorio | `.venv\Scripts\python.exe -m uvicorn app.main:app` | `OBS_PORT` (default `8001`) |
| Data Nexus | `.venv\Scripts\python.exe -m src.ingestion` | `PORT_INGESTION` (default `8002`) |

Host fijo `127.0.0.1`. El lanzador aborta con código 2 si `OBS_HOST` o
`HOST_INGESTION` apuntan fuera de loopback. `QBE_INGESTION_URL` solo se exporta
si falta y `PORT_INGESTION != 8002`; una URL explícita del operador nunca se
sobreescribe (solo se advierte si discrepa). No se tocan `DATABASE_URL`,
`QBE_FEATURE_*`, `OBS_*_SNAPSHOT` ni variables de scraping.

### Ciclo de vida

1. **Preflight:** raíz, intérprete del `.venv`, variables canónicas, puertos
   duplicados y los tres puertos (bind exclusivo en loopback).
2. **Arranque concurrente** con `CREATE_NEW_PROCESS_GROUP` y Job Object
   `KILL_ON_JOB_CLOSE`: si el lanzador muere abruptamente, Windows apaga el
   árbol completo.
3. **Readiness `/health`** por contrato: `module=business`, `db=READ_ONLY`,
   `service=qbe_ingestion` + `port` (timeout 60 s, configurable).
4. **Vigilancia:** cualquier muerte inesperada apaga el resto y sale con 4.
5. **Apagado:** `CTRL_BREAK_EVENT` al grupo de cada hijo, espera de 8 s,
   `taskkill /T /F` solo si es necesario, y cierre final del Job Object.

### Códigos de salida

| Código | Significado |
|---:|---|
| 0 | APAGADO ORDENADO COMPLETADO |
| 1 | APAGADO FORZADO (algún hijo requirió `taskkill`) |
| 2 | uso o entorno inválido |
| 3 | colisión de puerto detectada antes de arrancar |
| 4 | fallo de arranque o muerte de un hijo en caliente |

### Pruebas

```powershell
.\.venv\Scripts\python.exe -m pytest scripts/tests -q
```

El Juez es perimetral: no forma parte del comando canónico de The Shield en
`AGENTS.md`. La prueba de integración real es opt-in (`QBE_LANZADOR_E2E=1`) y
requiere `:8000`, `:8001` y `:8002` libres. Los logs viven en
`.bt_run/lanzador/<sello>/` (ignorado por Git).

## Estado de importación

| Script | Estado | Nota |
|---|---|---|
| `lanzador_ecosistema.py` | RUNNABLE | Utilidad E2E de tres procesos; no importa `src.*`; ver sección propia. |
| `laboratorio/generar_dataset_manus.py` | RUNNABLE | Requiere snapshot y matriz de investigación. |
| `laboratorio/sandbox_arquetipos_vectores.py` | RUNNABLE | Factor attribution reanclado al Observatorio. |
| `laboratorio/sandbox_ataque_defensa_pipeline.py` | RUNNABLE | Factor attribution reanclado al Observatorio. |
| `laboratorio/sandbox_contexto_shocks_pipeline.py` | RUNNABLE | Solo lectura. |
| `laboratorio/sandbox_micro_dinamicas_pipeline.py` | RUNNABLE | Solo lectura. |
| `laboratorio/sandbox_rentabilidad_pipeline.py` | RUNNABLE | Reexporta el motor del Observatorio. |
| `laboratorio/sandbox_trayectoria_momento_pipeline.py` | RUNNABLE | Solo lectura. |
| `laboratorio/sandbox_volumen_porteria_pipeline.py` | DEUDA DECLARADA | Falta `src.core.metrics` (`SyntheticMetricsEngine`). |
| `laboratorio/sandbox_h2h_pipeline.py` | DEUDA DECLARADA | Falta `src.core.sovereign.h2h_provider`. |
| `laboratorio/validar_informe_shannon.py` | RUNNABLE | Motor de simulación reanclado al Observatorio. |
| `investigacion/generar_matriz_investigacion.py` | RUNNABLE | Reporte de calibración reanclado al Observatorio. |
| `investigacion/mineria_factores_shannon.py` | RUNNABLE | Solo biblioteca estándar. |
| `investigacion/manus_qbe_model.py` | DEUDA OPCIONAL | Requiere `xgboost` (dependencia no instalada). |

## Deudas declaradas

1. **`src.core.metrics`**: el módulo legado `metrics.py` es puro y pequeño, pero su migración a `qbe_core` exige Juez de pureza y Ficha de Varianza. No se inventó un shim.
2. **`src.core.sovereign.h2h_provider`**: el módulo legado mezcla lectura 3NF y corpus congelado; su destino correcto es un pilar con I/O (probablemente `qbe_ingestion`), no `qbe_core`. No se copió a ciegas.
3. **`xgboost`**: dependencia opcional del modelo Manus; se declara, no se instala silenciosamente.

## Reglas

- No se escribe en `data/qbe_database.db` ni en el snapshot.
- El lanzador no escribe en la base: solo orquesta procesos; los servidores que
  levanta conservan su propio régimen (OLTP/OLAP/ingesta).
- No se inventan datos cuando falta una celda.
- Los scripts de deuda no se presentan como verdes.
- Cualquier promoción de deuda exige Juez, Ficha de Varianza y actualización de `docs/ARCH.md`.
