# DIRGEN_VARIANCE_REQUEST — `SPRINT-47-UNIFICACION-FOTMOB-Y-LANZADOR`

**Régimen:** `[DIRGEN-STRICT]`
**Pilar:** `qbe_observatory` (capa de presentación / lectura)
**Estado:** `ALTO AL FUEGO` sobre **un** requisito (Tarea 2, desglose histórico por jornada).
**Resto de la directiva:** en ejecución (Tareas 1, 2-live, 3, 4, 5).

---

## 1. Coordenadas exactas

| Elemento | Valor |
|---|---|
| Archivo | `qbe_observatory/app/services/sabiduria_view.py` |
| Función | `_partidos_historicos()` (nueva) / rama `es_historica` de `construir_sabiduria_masas()` |
| Requisito incumplido | *«En el desglose histórico, elimina el `jornada=0` sintético. Consulta `historical_matches` y agrupa por la columna real `jornada` para generar los bloques J1, J2, J3, etc.»* |
| Bóveda | `qbe_observatory/data/qbe_historico.db` (26 MB, 12 temporadas) |
| Tabla | `historical_matches` (3 870 filas, `fuente_datos='FOOTYSTATS_MHTML'` en 3 870/3 870) |

## 2. Evidencia fáctica real

```
PRAGMA table_info(historical_matches) →
['match_id','temporada','match_ref','fecha_utc','fecha_epoch','home_team','away_team',
 'home_team_slug','away_team_slug','home_team_id','away_team_id','home_goals','away_goals',
 'odd_home','odd_draw','odd_away','xg_home','xg_away','fuente_datos','cargado_utc']

¿Alguna columna de jornada?  NINGUNA
```

* `match_ref` es un identificador opaco de FootyStats (`z85293`), no una jornada.
* `historical_match_events`, `historical_match_events/…`, `historical_team_season_stats`,
  `historical_load_log`, `seasons`, `match_telemetry`: **ninguna** porta jornada.
* El parser que produjo el corpus (`qbe_ingestion/src/ingestion/parsers/parsear_footystats_mhtml.py`)
  **no contiene** la cadena `jornada` / `matchday` / `round`: el campo nunca se extrajo.
* La única jornada real del ecosistema vive en `matches.matchday_num` (corpus **FOTMOB**),
  pero los identificadores no se cruzan: `historical_matches.match_id = 'fs_2015_2016_z85293'`
  vs `matches.id = 'FOTMOB-1984244'` → **JOIN por id = 0 filas**.
* Emparejamiento por identidad factual (slug canónico `[LN-QBE-012]` + mismo día ±1):

| Temporada | Filas FootyStats | Con cuota | Emparejadas con `matches` | Cobertura |
|---|---|---|---|---|
| 2015_2016 | 334 | 319 | 204 (193 con cuota) | **61 %** |
| 2019_2020 | 338 | 284 | 226 | 67 % |
| 2025_2026 | 337 | 337 | 300 | 89 % |
| 2026_2027 | 153 | 135 | **0** | **0 %** |

## 3. Diagnóstico causal

La fuente cargada **no porta la jornada**: ni la columna, ni el parser, ni el log de carga. El
JOIN con el corpus FOTMOB es parcial (61 % en 2015_2016, 0 % en la temporada vigente) porque las
dos ingestas usan convenciones de slug y fechas distintas y la temporada actual no existe en FOTMOB.

Agrupar por esa vía dejaría la tabla con **193 de 319** partidos mientras el KPI se calcula sobre
**319**: exactamente la desincronización KPI↔tabla que la Tarea 3 ordena erradicar. Además, para
`2026_2027` no habría ningún bloque. La Directiva prohíbe modificar la BD y los daemons de ingesta,
y `[GOVERNANCE-01]` prohíbe fabricar una jornada (derivarla de fechas u ordinales sería una cifra
inventada).

## 4. Abanico de alternativas evaluadas

| # | Alternativa | Veredicto |
|---|---|---|
| **A** | **Bloque agregado de temporada con `jornada=None` declarado**; el código agrupa por `jornada` automáticamente en cuanto la fuente la propague. KPI y tabla comparten la **misma** consulta y el **mismo** universo (319/319). | **RECOMENDADA** — cero fabricación, cero desincronización, cumple Tareas 1/3/4. Es la implementada. |
| **B** | JOIN canónico contra `matches.matchday_num` y declarar cobertura parcial (61 % / 0 %). | Rechazada: viola Tarea 3 (KPI 319 ≠ tabla 193) y deja la temporada vigente sin desglose. |
| **C** | Ingesta: extraer la jornada del MHTML FootyStats y persistirla en `historical_matches.jornada`. | Correcta de fondo, **fuera de jurisdicción** (prohibido tocar BD y daemons). Requiere sprint de ingesta. |

## 5. Solución recomendada

1. **Ahora:** publicar el histórico como **un bloque de temporada** (`jornada = None`), sin el `0`
   sintético, con `jornadas_disponibles = []` y el selector de Jornada sin opciones falsas. El KPI
   es la media ponderada del único bloque ⇒ **0.2119 = 0.2119**, matemáticamente consistente.
2. **Sprint de ingesta (Tarea C):** poblar `historical_matches.jornada`; `_partidos_historicos()`
   la propaga y `_bloques_por_jornada()` emite J1…Jn **sin cambios de código** en la capa web.
3. **Criterio de cierre:** el Juez `test_shield_consenso_mercado.py` certifica hoy `jornada is None`
   (D8); cuando la fuente declare jornada, el Juez debe certificar los bloques reales.

## 6. Autorización solicitada

Confirmar la alternativa **A** como cumplimiento válido de la Tarea 2 para el corpus actual, y
registrar la alternativa **C** como deuda de ingesta del próximo sprint.
