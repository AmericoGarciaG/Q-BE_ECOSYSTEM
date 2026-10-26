# FASE 4 — SLICE 4A: CIERRE DEL DATA NEXUS

| Campo | Valor |
|---|---|
| **Proyecto** | `Q_BE_ECOSYSTEM` — Fase 4 |
| **Slice** | 4A — Providers, scrapers, daemons y normalización |
| **Rama** | `feature/fase4-ingestion` |
| **Estado** | **2/2 GREEN** (juez de ingesta) · **12/12** con la suite de Business |
| **Ruta** | `D:\00 SW Projects\Q-BE Casino Deportes\Q_BE_ECOSYSTEM\qbe_ingestion` |

---

## 1. Juez de ingesta

```text
test_daemons_importan_y_apuntan_a_bd_efimera PASSED
test_business_no_importa_ingesta PASSED

2 passed in 2.27s
Exit Code: 0
```

Suite combinada Business + Ingestion:

```text
12 passed, 1 warning in 4.05s
```

---

## 2. Paquete `qbe_ingestion`

```text
qbe_ingestion/
├── pyproject.toml
├── src/ingestion/
│   ├── __init__.py
│   ├── betway_scraper.py
│   ├── caliente_scraper.py
│   ├── ligapremier_scraper.py
│   ├── novibet_scraper.py
│   ├── ocr_parser.py
│   ├── progol_scraper.py
│   ├── progol_resolver.py
│   ├── schemas.py
│   ├── normalizer.py            (shim → src.core.normalization.normalizer)
│   ├── coherence_auditor.py
│   ├── providers/
│   │   ├── base_provider.py
│   │   └── fotmob_provider.py
│   └── daemons/
│       ├── centinela_deportivo.py
│       ├── centinela_mercado.py
│       └── centinela_progol.py
└── tests/test_parity_ingestion_daemons.py
```

---

## 3. Daemons — hashes

| Daemon | SHA-256 | Byte-idéntico al baseline |
|---|---|---|
| `centinela_deportivo.py` | `023aecfe…` | Sí |
| `centinela_mercado.py` | `89a5a1f6…` | Sí |
| `centinela_progol.py` | `7e691a3b…` | Sí |
| `coherence_auditor.py` | `ecbb9445…` | No: se ajustó el import de `scripts.daemons` a `src.ingestion.daemons` |

---

## 4. Frontera de escritura

- `qbe_ingestion` importa `PersistenceGateway` y `write_transaction` (dueño de captura).
- `qbe_business` no importa `src.ingestion` ni `qbe_ingestion` (AST).
- El juez apunta el gateway a un SQLite efímero; no toca la bóveda viva.
- `src.ingestion.normalizer` es un **shim** al normalizador puro de `qbe_core`; no duplica lógica.

---

## 5. Deuda declarada

1. **`coherence_auditor`:** se copió a `qbe_ingestion` con el import de daemons corregido, pero **se conserva una copia en `qbe_core`** para no romper `admin/status` (Business no se tocó en 4A). Debe eliminarse de `qbe_core` cuando Ingestion exponga la API REST de deriva (4B) y Business la consuma.
2. **Daemons:** se importan y apuntan a la BD; no se ejecutó su bucle 24/7 ni una captura real.
3. **Scrapers:** se copiaron los módulos; no se ejecutó red/Playwright en este slice.
4. **`coherence_auditor`:** su hash no es byte-idéntico por el cambio de import; la lógica es la misma.

---

## 6. Git

- Rama: `feature/fase4-ingestion`.
- Commit de cierre 4A y tag `slice-4a-green`.
- `.gitignore` cubre `.venv/`, `__pycache__/`, `*.egg-info/`, bases SQLite y `qbe_storage/data/`.

**Firma:** Agente Constructor Kybern v12.0.
**Siguiente:** Slice 4B — Laboratorio de Scraping LLM.
