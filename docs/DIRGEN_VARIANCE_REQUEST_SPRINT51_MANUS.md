# DIRGEN_VARIANCE_REQUEST — VAR-2026-SPRINT51-MANUS

**Título:** El universo de 2,726 partidos del expediente `SPRINT-51` no es reproducible
con los cuatro filtros declarados sobre `qbe_historico.db`: es el agregado dual-vault de
`/desempeno` (2,592 históricos + 134 vivos), y 47 de esas filas carecen de vector de
mercado. La DoD «2,726 filas con cero NaN en `q_shin_*`» es insatisfacible sin fabricar.

| Campo | Valor |
|---|---|
| **ID del parte** | `VAR-2026-SPRINT51-MANUS` |
| **Expediente** | `SPRINT-51-META-ROUTER-MACHINE-LEARNING` |
| **Régimen** | `[DIRGEN-STRICT]` — datos y artefactos del laboratorio |
| **Autoridad** | Américo García Guerrero (Director Humano) |
| **Redactor** | Agente Constructor Kybern v13.5 |
| **Fecha del parte** | 2026-11-06 |
| **Estado** | 🟢 **RATIFICADO Y EJECUTADO — DECRETO VAR-2026-SPRINT51-MANUS (OPCIÓN 1: 2,667)** |
| **Alcance** | Sólo `scripts/investigacion/` y `data/investigacion/`. **Cero archivos de `qbe_core/`, `qbe_business/`, `qbe_ingestion/`, `qbe_storage/` tocados.** |
| **Bóveda** | `qbe_observatory/data/qbe_historico.db` — sólo lectura (`mode=ro` + `PRAGMA query_only=ON`). |
| **Sustituye en portada** | El parte `VAR-2026-SPRINT50-CORE` (`DIRGEN_VARIANCE_REQUEST.md`) queda **íntegro y vigente**; éste es un parte nuevo, no lo reemplaza. |

> **Nota de ratificación (2026-11-06).** El Director ratificó la **Opción 1 — histórico
> íntegro (2,667 filas)**: pureza del dato sobre el conteo nominal, fuente exclusivamente
> histórica e inmutable, cero NaN en variables críticas. El artefacto oficial es
> `data/investigacion/dataset_meta_router_2667.parquet`; `2026_2027` (98 partidos) queda
> clasificado como **Conjunto de Estrés Post-Holdout (Out-of-Distribution Test)** en
> `folds_rolling_origin.json`.

---

## 0. RESUMEN EJECUTIVO

La directiva fija un universo de **2,726 partidos** que deben cumplir simultáneamente:
marcador confirmado, cuotas 1X2 completas, overround `S ∈ [0.85, 1.30]` y distribución
soberana pre-kickoff. La bóveda histórica **no produce 2,726 filas** bajo esos filtros:

| Etapa | Filas | Δ |
|---|---:|---:|
| P′ ∩ marcador confirmado | **2,728** | — |
| ∩ cuotas 1X2 completas | **2,690** | −38 |
| ∩ overround `S ∈ [0.85, 1.30]` | **2,667** | −23 |
| ∩ Shin resoluble | **2,667** | −0 |

Las **2,726** son otra cosa: el total de la vista `/desempeno` en modo **«Todas»**, que
suma el corpus histórico depurado (**2,592**) y la temporada viva del snapshot 3NF
(**134**). De esas 2,726, sólo **2,679** tienen vector de mercado; **47** no lo tienen
(23 históricos con la terna corrupta `1.5 / 3.0 / 1.5`, `S = 1.6667`, sin raíz de Shin;
24 vivos de `2026_2027`).

**Consecuencia:** la DoD exige a la vez «exactamente 2,726 filas» y «cero NaN en
`q_shin_*`». Ambas no pueden cumplirse sin imputar cuotas o inventar probabilidades, lo
que el propio régimen prohíbe. Se detuvo la emisión oficial y se sometieron tres
universos a decreto; la Dirección ratificó el **histórico íntegro de 2,667** (Opción 1).

---

## 1. COORDENADAS EXACTAS

| # | Elemento | Coordenada |
|---|---|---|
| **C1** | Bóveda | `qbe_observatory/data/qbe_historico.db` (77.7 MB, 26 tablas) |
| **C2** | Tabla fáctica | `historical_matches` (3,870 filas; 12 temporadas) |
| **C3** | Tabla soberana | `historical_sovereign_distributions` (2,737 filas; 2,728 con marcador) |
| **C4** | Vector causal | `historical_match_causal_vars` (3,000 filas; `V29`/`V30` ausentes en 2015_2016) |
| **C5** | Ley de de-vig | `qbe_core/src/core/consensus.py::desmarginar_shin` `[LN-QBE-151]` |
| **C6** | Ley de orden | `qbe_core/src/core/contracts/portfolio_math.py::resolver_orden_fiduciario_con_indiferencia` `[LN-QBE-124]` |
| **C7** | Ley de Brier | `qbe_core/src/core/sovereign/calibrar_perturbacion.py::brier_multiclase` `[LN-QBE-147]` / 3 `[LN-QBE-100]` |
| **C8** | Vista de referencia | `qbe_observatory/app/services/desempeno_view.py::cargar_vista_desempeno` (modo «Todas») |
| **C9** | Script nuevo | `scripts/investigacion/exportar_dataset_manus.py` (53 columnas, candado de censo) |
| **C10** | Artefactos provisionales | `.tmp_run/provisional_2569/` y `.tmp_run/provisional_2667/` (**nada** en `data/investigacion/`) |

---

## 2. EVIDENCIA FÁCTICA REAL (CERO MOCKS)

### 2.1 Censo reproducible — `python scripts/investigacion/exportar_dataset_manus.py --diagnostico`

```
Candidatos con marcador y P′ : 2728
Fuera de temporada           : 0
Sin cuotas 1X2 completas     : 38
Overround fuera de rango     : 23
Shin no resoluble            : 0
ACEPTADOS                    : 2667
Overround observado          : [0.995726, 1.203995]
Por temporada:
  2015_2016: 264 · 2018_2019: 252 · 2019_2020: 243 · 2020_2021: 306
  2021_2022: 309 · 2022_2023: 304 · 2023_2024: 296 · 2024_2025: 290
  2025_2026: 305 · 2026_2027: 98
```

**Las 23 cuotas corruptas** son exactamente la terna repetida `(1.5, 3.0, 1.5)`
(`S = 1.6667`): 8 en `2023_2024` y 15 en `2024_2025`. Quedan fuera por el filtro de
overround **y** por la aduana de Shin — dos leyes independientes coinciden.

**Sin la temporada en curso** (`2026_2027`, 98 filas con P′ y cuotas), el mismo censo da
**2,630 → 2,592 → 2,569**.

### 2.2 La cifra 2,726 es el agregado dual-vault de `/desempeno`

Invocada la ley real de la vista (`cargar_vista_desempeno(temporada="Todas")`), el
resultado de hoy es **idéntico** al documentado en `KDB.md` §5.8:

```json
{"total_partidos": 2726, "total_jornadas": 305,
 "brier_qbe": 0.2115, "brier_mercado": 0.2036, "alpha": -3.88,
 "fuente": {"tipo": "dual_vault", "nombre": "qbe_historico.db + snapshot 3NF"}}
```

Descomposición por temporada de la vista:

| Temporada | Partidos | Origen |
|---|---:|---|
| 2015_2016 … 2025_2026 | 2,592 | bóveda histórica (excluye la temporada en curso) |
| 2026_2027 | 134 | snapshot 3NF (temporada viva) |
| **Total** | **2,726** | |

Es decir: **2,726 = 2,592 + 134**. La consulta histórica de la vista exige `odd_* > 1`
pero **no** exige `S ∈ [0.85, 1.30]`; por eso su corpus histórico es 2,592 y no 2,569.

### 2.3 Los 47 partidos sin vector de mercado

| Temporada | Sin mercado | Causa |
|---|---:|---|
| 2023_2024 | 8 | terna `(1.5, 3.0, 1.5)`, `S = 1.6667`, Shin sin raíz |
| 2024_2025 | 15 | ídem |
| 2026_2027 | 24 | partido vivo sin terna 1X2 completa/resoluble |
| **Total** | **47** | |

`2,726 − 47 = 2,679` = muestra coincidente P′ ∩ q_mkt ∩ resultado que la propia `KDB.md`
declara (N = 2,679). Todo cuadra: **el universo de 2,726 no es un universo con mercado
completo**.

### 2.4 Brier 3N por universo (ley canónica, no reimplementada)

| Universo | Filas | N mercado | Brier Q-BE | Brier Shin | Δ (Mkt−QBE) |
|---|---:|---:|---:|---:|---:|
| P′ ∩ marcador (todas) | 2,728 | 2,667 | 0.211457 | 0.203690 | −0.007767 |
| + cuotas completas | 2,690 | 2,667 | 0.211434 | 0.203690 | −0.007744 |
| **+ S ∈ [0.85, 1.30]** | **2,667** | **2,667** | **0.211572** | **0.203690** | **−0.007882** |
| Excl. 2026_2027 (P′ ∩ marcador) | 2,630 | 2,569 | 0.211214 | 0.203287 | −0.007927 |
| **Excl. 2026_2027 + S rango** | **2,569** | **2,569** | **0.211327** | **0.203287** | **−0.008040** |
| *Vista «Todas» (referencia KDB)* | *2,726* | *2,679* | *0.2115* | *0.2036* | *−3.88 %* |

El universo de **2,667** reproduce la auditoría previa hasta la cuarta decimal
(0.2116 vs 0.2115; −3.87 % vs −3.88 %). La diferencia residual es exactamente la
temporada viva (134 filas) que la bóveda histórica no contiene.

### 2.5 Calidad declarada: `V29`/`V30` ausentes en 2015_2016

`historical_match_causal_vars` no publica `v29_local`/`v30_local` para **2015_2016**
(301 filas, 100 % nulas). En el corpus de 2,569/2,667 eso deja **264 filas** con
`delta_alt_metros` y `delta_descanso_dias` nulos. No son columnas críticas para la DoD,
pero **sí** son features de entrada del Meta-Router: se declaran en
`DATA_DICTIONARY_MANUS.json → calidad.nulos_por_columna` y **no se imputan**.

---

## 3. DIAGNÓSTICO CAUSAL

1. **Confusión de universos.** La directiva toma el total de presentación de
   `/desempeno · Todas` (2,726) y lo presenta como el resultado de una consulta histórica
   con overround. Son objetos distintos: el primero es **dual-vault** e incluye la
   temporada viva; el segundo es **histórico puro** y da 2,667.
2. **El 2,726 no es estable.** El snapshot vivo cambia con cada jornada (hoy la tabla
   `matches` tiene 153 filas y 126 distribuciones; la auditoría se hizo con 134). Cualquier
   dataset anclado a 2,726 deja de ser reproducible al día siguiente.
3. **47 filas sin mercado.** Aun aceptando el universo dual-vault, 47 filas no tienen
   `q_shin`: la DoD de «cero NaN» obligaría a imputar cuotas —prohibido por
   `[GOVERNANCE-01]` y por el propio contrato de `desmarginar_shin`—.
4. **La cifra 2,726 tampoco cuadra con los folds.** El protocolo sellado usa 9 temporadas
   (2015_2016 + 2018_2019 … 2025_2026 = 2,569 con mercado). Las 98 filas históricas de
   `2026_2027` y las 134 vivas quedan **fuera de todo fold**.

---

## 4. ABANICO DE ALTERNATIVAS EVALUADAS

### A. Universo histórico íntegro — **2,667 filas** (recomendada)

Aplica **literalmente** los cuatro filtros de la directiva sobre la bóveda declarada,
incluida `2026_2027`. Cero NaN en columnas críticas; símplex conservado; Brier
0.211572 / 0.203690 (Δ −3.87 %), el más próximo a la auditoría (0.2115 / 0.2036).
*Coste:* el nombre `…_2726` es falso; se propone `dataset_meta_router_2667.parquet`.

### B. Universo pre-holdout — **2,569 filas**

Idéntico a A pero excluyendo la temporada en curso (`2026_2027`), que queda después del
holdout sellado. Coincide **exactamente** con las 9 temporadas de los folds. Brier
0.211327 / 0.203287 (Δ −3.96 %).
*Coste:* se aleja una diezmilésima más de la auditoría y descarta 98 partidos ya jugados.

### C. Universo «Todas» — **2,726 filas** (rechazada de oficio)

Requiere leer el snapshot vivo (fuera de la fuente declarada) y deja **47 NaN** en
`q_shin_*`/`brier_mkt_3n`. Viola la DoD y la regla de cero cifras fabricadas. No se
materializa.

### D. Universo «Todas» recortado a la muestra coincidente — **2,679 filas** (rechazada)

Cero NaN y reproduce el Brier de mercado de la auditoría, pero (i) no son 2,726,
(ii) depende de una bóveda viva mutable y (iii) mezcla temporada en curso con corpus
histórico. No es un dataset de laboratorio reproducible.

---

## 5. SOLUCIÓN RATIFICADA Y EJECUTADA

El decreto ratificó **A (2,667 filas)**: `data/investigacion/dataset_meta_router_2667.parquet`,
con el diccionario y los folds regenerados. El alias del expediente (`…_2726`) queda
documentado como cifra de presentación de `/desempeno`, no como censo del dataset.

Resultado materializado y verificado:

| Comprobación | Resultado |
|---|---|
| Filas × columnas | **2,667 × 53** |
| Nulos en `p_qbe_*`, `q_shin_*`, `resultado_real`, `brier_*` | **0** |
| `\|Σp−1\|` máximo | **2.22 × 10⁻¹⁶** (tolerancia 10⁻⁶) |
| `\|Σq−1\|` máximo | **4.72 × 10⁻¹⁰** (tolerancia 10⁻⁶) |
| Brier 3N Q-BE | **0.211572** |
| Brier 3N Shin | **0.203690** |
| Delta (Mkt − QBE) | **−0.007882 (−3.87 %)** — paridad con la auditoría (0.2115 / 0.2036 / −3.88 %) |
| Re-ejecución | **idempotente** (mismos SHA-256) |

Nulos declarados (no críticos, no imputados): `delta_alt_metros` y
`delta_descanso_dias`, 264 filas de `2015_2016` sin `V29`/`V30` en la bóveda.

---

## 6. DIFF PROPUESTO (NINGUNO APLICADO — ESPERA AUTORIZACIÓN)

### 6.1 `[DIRGEN-STRICT]` · Cero cambios en pilares

No se ha tocado `qbe_core/`, `qbe_business/`, `qbe_ingestion/`, `qbe_storage/` ni las
tablas de la base viva. `git status --short` no muestra ningún archivo nuevo fuera de
`scripts/investigacion/exportar_dataset_manus.py` (los cambios listados son preexistentes
de la sesión del Director).

### 6.2 Script nuevo (perímetro autorizado)

`scripts/investigacion/exportar_dataset_manus.py` — 53 columnas tipadas, candado
`--esperado-filas` (por defecto 2,726), `--universo {pre_holdout, historico}`,
`--diagnostico`, `--permitir-desviacion`. Importa las leyes canónicas; no reimplementa
ninguna.

### 6.3 Artefactos

- **Publicados** en `data/investigacion/`:
  `dataset_meta_router_2667.parquet`, `DATA_DICTIONARY_MANUS.json` y
  `folds_rolling_origin.json`.
- Provisionales de contraste conservados en `.tmp_run/provisional_2569/` y
  `.tmp_run/provisional_2667/` (directorio ignorado por git).

---

## 7. EJECUCIÓN (POST-RATIFICACIÓN)

```powershell
# Opción A ratificada (2,667) — ejecutada:
python scripts/investigacion/exportar_dataset_manus.py
#   -> data/investigacion/dataset_meta_router_2667.parquet  (2,667 × 53)
```

El script toma por defecto `--universo historico --esperado-filas 2667`. La variante
`--universo pre_holdout` (2,569) queda disponible como contraste, sin publicar.

---

## 8. ANEXOS

### 8.1 Comandos de evidencia ejecutados

```powershell
python scripts/investigacion/exportar_dataset_manus.py --diagnostico
python scripts/investigacion/exportar_dataset_manus.py            # EXIT=2 (candado)
python .tmp_run/probe_vista_todas.py                              # 2,726 / 0.2115 / 0.2036
```

### 8.2 Artefactos oficiales (verificados)

| Archivo | Filas × Cols | SHA-256 |
|---|---|---|
| `dataset_meta_router_2667.parquet` | 2,667 × 53 | `22633810ff22220a1767e89a1622c9b7bbf6ca3a76828b0b71697b718657b613` |
| `DATA_DICTIONARY_MANUS.json` | 53 columnas | `0bd3457b67704f6d41147ae6915c7e9a6348c31b61036c6891698a3e766abfed` |
| `folds_rolling_origin.json` | 5 folds + estrés | `daeb964ddb451866179dcfc9f38e73908ac673f3506e3b364c75845127882d3d` |

Provisionales de contraste (`.tmp_run/`):

| Universo | Filas × Cols | SHA-256 Parquet |
|---|---|---|
| 2,569 | 2,569 × 53 | `1f55574a183fe2e3af5dda86a10f8ad8f87d58af22555de1ccba7a4187f396a0` |
| 2,667 | 2,667 × 53 | `22633810ff22220a1767e89a1622c9b7bbf6ca3a76828b0b71697b718657b613` |

### 8.3 Manifiesto Git

`git status --short` no añade nada fuera de `scripts/investigacion/exportar_dataset_manus.py`.
`.vendor/` (pyarrow de soporte) y `.tmp_run/` están en `.gitignore`.

### 8.4 Trazabilidad del bloqueo

1. El censo de la bóveda (2,667) no coincide con el candado (2,726) → `EXIT=2`, sin artefactos.
2. La vista «Todas» explica el 2,726 (2,592 + 134) y los 47 sin mercado.
3. Se detuvo la emisión oficial y se elevó este parte, conforme al Protocolo Anti-Bandazos.
4. **Resolución:** decreto `VAR-2026-SPRINT51-MANUS` (Opción 1, 2,667). Se materializó el
   paquete, se verificó (cero NaN críticos, símplex conservado, idempotencia) y se
   clasificó `2026_2027` como conjunto de estrés post-holdout.
