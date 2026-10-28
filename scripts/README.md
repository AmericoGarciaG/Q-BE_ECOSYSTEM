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

## Estado de importación

| Script | Estado | Nota |
|---|---|---|
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
- No se inventan datos cuando falta una celda.
- Los scripts de deuda no se presentan como verdes.
- Cualquier promoción de deuda exige Juez, Ficha de Varianza y actualización de `docs/ARCH.md`.
