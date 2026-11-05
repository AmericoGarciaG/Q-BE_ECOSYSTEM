# DIRGEN_VARIANCE_REQUEST — VAR-2026-SPRINT50-CORE

**Título:** Reingeniería del núcleo matemático: clausura estricta de masa en la ligadura de α,
erradicación de defaults literales y sustitución del falso GSL-3D por una proyección ortogonal real
sobre las 32 variables. Autorización de reescritura de `sovereign_pipeline.py` e
`intensity_canonical_loglink.py`.

| Campo | Valor |
|---|---|
| **ID del parte** | `VAR-2026-SPRINT50-CORE` |
| **Expediente** | `SPRINT-50-REINGENIERIA-INDUSTRIAL-QBE-CORE` — Fase 1 (Legislación) |
| **Régimen** | `[DIRGEN-STRICT]` — matemática pura de `qbe_core` |
| **Autoridad** | Américo García Guerrero (Director Humano) |
| **Redactor** | Agente Constructor Kybern v13.5 |
| **Fecha del parte** | 2026-11-04 |
| **Estado** | 🟢 **RATIFICADO Y CERRADO — DECRETO D1-D5 APROBADO POR LA DIRECCIÓN** |
| **Enmiendas legisladas** | `E-50.1` (`[VAULT-CORE-001]`), `E-50.2` (`[LN-QBE-020-B]`), `E-50.3` (`[LN-QBE-039]`) |
| **Alcance de la Fase 1** | Sólo `docs/`. **Cero archivos de `src/` modificados.** |
| **Sustituye en portada** | Parte `SPRINT-47-UNIFICACION-FOTMOB-Y-LANZADOR`, conservado íntegro en el **Anexo A** |

---

> **Nota de ratificación (Decreto D1–D5).** La materialización de la Fase 2A, 2B, 4, 6 y 8
> fue autorizada vía directiva de arquitectura (Sprints 50) y se ratifica formalmente mediante
> este decreto. El código actual es el estándar oficial.

---

## 0. RESUMEN EJECUTIVO

La auditoría forense del núcleo (fase previa del mismo expediente) estableció que el motor v13.0
**no materializa el plano que invoca**. Cuatro defectos son estructurales y ninguno se corrige con un
parche:

1. **Masa rota.** La ligadura α se calcula sobre `γ_base` y el operador de altitud/descanso se suma
   después: `E[goles]` deja de ser `μ_liga` (2.6500 → **2.6934** con +1000 m; **2.7609** con +2500 m).
2. **Mocks ocultos.** `dict.get("gf", 10)`, `("gc", 12)`, `("gf", 7)`, `("gc", 10)`, `("pj", 8)`
   inyectan números cuando la fuente no publica el dato, y la telemetría declara «no publicado»
   mientras la aritmética usa `10`.
3. **GSL-3D falso.** No hay proyección ortogonal: hay un residuo log-diferencial **escalar** de sede,
   aplicado **sólo al club local**, condicionado a `PJ≥3` de ambos splits, y comprimido **dos veces**
   (`tanh` con techo 1.00 y después κ = 0.25).
4. **Catálogo decorativo.** De 32 variables, λ consume **4** (`V06`, `V12`, `V29`, `V30`) más `gf`/`gc`
   —no catalogados—, `q_mod` —no catalogado— y un bono de plaza por *slug*.

La Fase 1 legisla la corrección. La Fase 2 (reescritura) **no se ejecuta sin decreto** por el
Protocolo Anti-Bandazos: los dos módulos afectados son `[DIRGEN-STRICT]` y su materialización exige
esta ficha.

---

## 1. COORDENADAS EXACTAS

| # | Artefacto | Línea / símbolo | Defecto verificado | Enmienda que lo cubre |
|---|---|---|---|---|
| **C1** | `qbe_core/src/core/intensity_canonical_loglink.py` | `calcular_alpha_ligadura` L48-56 | α sobre `γ_base`; `Δalt`/`Δrest` fuera de la ligadura ⇒ fuga de masa | `E-50.1` Invariante L-1 |
| **C2** | ídem | `estimar_intensidades_loglineal` L108, L117-119 | El intercepto se construye **después** de α | `E-50.1` §P-02 |
| **C3** | `qbe_core/src/core/sovereign_pipeline.py` | `derivar_factores_estructurales` L623-653 | `h.get("gf", 10)`, `a.get("gc", 12)`, `a.get("gf", 7)`, `h.get("gc", 10)`, `h.get("pj", 8)` | `P-01` |
| **C4** | ídem | L629-654 | `xg = 0 ⇒ gf` como sustituto silencioso del ancla xG | `P-01` / `E-50.3` §7.6.6 |
| **C5** | `qbe_core/src/core/sovereign/orthogonal_factor_engine.py` | L40-87 | Residuo escalar de sede presentado como GSL-3D; `tanh` con techo 1.00 | `E-50.3` §7.6 |
| **C6** | `qbe_core/src/core/sovereign_pipeline.py` | L661-684 | El residuo se aplica **sólo** al local; `D_away, A_away = D_away, A_away` es un no-op | `E-50.3` §7.6.2 |
| **C7** | ídem | L40 `W_SEDE = 0.50` | Constante legislada **muerta**: cero referencias; el peso real del residuo es `1.00` | `E-50.3` |
| **C8** | ídem | L903 | `k_max=6` (retículo 7×7) frente al `[0,5]` sellado en `CONSTANTS.md` L104 | Deuda declarada (Fase 2C) |
| **C9** | `qbe_core/src/core/poisson.py` | L37-38, L140 | Ley H2H con decaimiento coexistiendo con la ley `0.05N` del pipeline | `E-50.2` §7.7 |
| **C10** | `qbe_core/src/core/sovereign_pipeline.py` | L755-768 | `min(0.25, 0.05N)` sin decaimiento: segunda ley sobre el mismo objeto | `E-50.2` §7.7 |
| **C11** | ídem | L869-884 | Ruta `S(I)=0` devuelve `λ=1.325/1.325` y `P=(1/3,1/3,1/3)` como literales | Aceptado: ignorancia declarada R-1 |
| **C12** | `qbe_core/src/core/intensity_canonical_loglink.py` | L132-133 | Clamps `[0.15, 4.50]` inertes (κ satura λ_H ≈ 1.83) | Deuda declarada |
| **C13** | `qbe_core/docs/DIRGEN_VAULT.md` | espejo del canon | Copia **desincronizada** del plano (L1280+); dos fuentes de verdad documental | Deuda de sincronía (fuera de jurisdicción) |

**Nota de régimen.** C1-C6 y C10 viven en `qbe_core` `[DIRGEN-STRICT]`: **no se tocaron**. C13 no
pertenece a `docs/`: **no se tocó**.

---

## 2. EVIDENCIA FÁCTICA (CERO MOCKS)

### 2.1 Fuga de masa (ejecutado, sólo lectura)

```
α(2.65, 0.15)  = 0.203603
Δalt =    0 m  -> λ_H=1.4242  λ_A=1.2258  Σ=2.6500
Δalt = 1000 m  -> λ_H=1.4676  λ_A=1.2258  Σ=2.6934   (+1.64 %)
Δalt = 2500 m  -> λ_H=1.5351  λ_A=1.2258  Σ=2.7609   (+4.18 %)
```

Con la clausura `E-50.1` (α recomputada sobre `γ_efectivo`) la suma es **2.6500 exacta** en los tres
casos — verificado numéricamente antes de legislar:

```
γ_eff=0.180 -> α=0.187368 -> λ_H=1.443929  λ_A=1.206071  Σ=2.650000
γ_eff=0.225 -> α=0.162598 -> λ_H=1.473437  λ_A=1.176563  Σ=2.650000
γ_eff=0.090 -> α=0.235400 -> λ_H=1.384585  λ_A=1.265415  Σ=2.650000
```

> **Nota de refutación.** El ejemplo de la Directiva («α fijada como constante estática de 0.2035»)
> **no** corresponde al código: α se calcula dinámicamente y `0.203603` es simplemente su valor en el
> punto canónico (μ=2.65, γ=0.15), que se recalibra por plaza (Tigres 0.165375, Toluca 0.170910). El
> defecto real es la **clausura incompleta**, no una constante.

### 2.2 GSL-3D: compresión anidada

```
A_gen=0.6, split sede 2.0 vs 1.4  -> residuo=+0.2067 -> A*=0.6678 -> tras κ=0.25 -> 0.2476
                                    (sin GSL-3D:                              0.2459)
λ_H satura en 1.8287 para todo A_crudo ≥ 2.0
```

La capa GSL-3D aporta **~0.7 %** al resultado final, pero impone una arquitectura completa. Su techo
declarado `|A*| ≤ 1.0` es **inalcanzable**: κ lo recorta a 0.25 antes de entrar a `eta`.

### 2.3 Cobertura del catálogo (bóveda, no opinión)

| Métrica | Valor | Fuente |
|---|---|---|
| Variables del catálogo `[LN-QBE-120]` | 32 | `docs/LOGIC.md` §2 |
| Variables con evidencia en el corpus | 9 | `docs/KTP/KDB.md` L189 |
| Variables `SIN EVIDENCIA` | 23 | `docs/KTP/KDB.md` L190 |
| Temporadas con 32/32 | **0 de 12** | `docs/KTP/KDB.md` L223 |
| Celdas que λ consume hoy | **4** (`V06`, `V12`, `V29`, `V30`) | `scripts/auditoria/calcular_distribuciones_historicas.py` L199-215 |

**Consecuencia normativa:** exigir el cumplimiento **inmediato** de 23/23 o 32/32 con este corpus
produce `S(I)=0` en **el 100 % de los partidos** y apaga la operación. La ley se redacta, por tanto,
en dos tiempos: contrato completo **ahora**, cobertura exigible **cuando la ingesta la publique**.

---

## 3. DIAGNÓSTICO CAUSAL

**A · La ligadura se escribió como normalización de un subconjunto del intercepto.** α nació para
fijar `E[λ_H+λ_A]=μ` en el punto neutro; al añadirse después el operador de altitud/descanso (y antes
el bono de plaza, ya incorporado a α en `[LN-QBE-038]`), la normalización quedó desalineada de su
propio intercepto. No es un error de constante: es un error de **orden de composición**.

**B · El default literal sustituyó a la aduana de evidencia.** El patrón `h.get("gf", 10)` se
introdujo para que el motor nunca fallara. El efecto es el contrario del exigido: el motor **nunca
declara ignorancia**, siempre publica un número, mientras `insumos_factivados` declara `None` sobre
el mismo dato — dos verdades contradictorias en el mismo objeto.

**C · «GSL-3D» designa hoy un corrector de localía, no una ortogonalización.** El módulo lo declara
honestamente en su docstring (degeneración de Gram-Schmidt en ℝ¹), pero el plano (`[LN-QBE-039]`,
`CONSTANTS.md` con `ε_ort` y tres techos de norma) describe una proyección de tres espacios que **no
existe**. La distancia entre el nombre y el operador es el defecto, no el operador.

**D · Dos leyes H2H sobre el mismo objeto.** `[LN-QBE-040]` pondera con decaimiento agregado;
`[LN-QBE-104]` pondera por `N`. Producen pesos distintos para la misma evidencia.

**E · El IPO no soporta la ley.** Aun legislando Gram-Schmidt, el motor recibe **agregados
escalares**. Una proyección ortogonal sobre variables requiere la matriz causal `n×32`. Sin cambio
de contrato de entrada, cualquier «ortogonalización» será cosmética.

---

## 4. ABANICO DE ALTERNATIVAS EVALUADAS

### 4.1 Clausura de masa

| Alt | Descripción | Efecto medido | Veredicto |
|---|---|---|---|
| **A-i** | `α = ln μ − ln(1+e^{γ_efectivo})` con el intercepto completo | Σ = 2.6500 exacta en todo el dominio | ✅ **RECOMENDADA** |
| A-ii | Restar el operador de contexto en el lado visitante | Σ = 2.6500, pero `λ_A` deja de ser neutro | ⚠️ Sólo si el término debe afectar a ambos |
| A-iii | Dejar α como está y declarar la fuga | Σ ∈ [2.65, 2.77] | ⛔ Viola `GOVERNANCE.md` regla 6 |
| A-iv | Clamp posterior de λ para forzar la suma | Σ = 2.65 artificial | ⛔ Fabricación de Clase I |

### 4.2 Insumos ausentes

| Alt | Descripción | Veredicto |
|---|---|---|
| **B-i** | Evidencia C-1 obligatoria ⇒ `InsufficientDataException` / `S(I)=0`; contexto C-2 «no aplicado» declarado | ✅ **RECOMENDADA** |
| B-ii | Mantener defaults pero publicarlos en la traza | ⛔ El número sigue siendo falso |
| B-iii | Default = media de liga | ⛔ Imputación no declarada |

### 4.3 Ortogonalización

| Alt | Descripción | Veredicto |
|---|---|---|
| C-i | Gram-Schmidt modificado sobre matriz `n×32` (n≥10) con `ε_ort=1e-5`, signos y RMS | ✅ **RECOMENDADA** |
| C-ii | Mantener el residuo escalar de sede y renombrarlo | ⛔ Cosmético |
| C-iii | Ortogonalizar los 4 escalares actuales | ⛔ Degenerado: 4 variables en ℝ¹ |
| C-iv | PCA en lugar de Gram-Schmidt | ⚠️ Equivalente, pero introduce componentes sin ID auditable |

### 4.4 Ley H2H

| Alt | Descripción | Veredicto |
|---|---|---|
| **D-i** | Propiedad única por capa: decaimiento **dentro** del kernel (`τ_deep=540`), peso de fusión por `N`, amplitud `0.50` sólo en el motor legado | ✅ **RECOMENDADA** |
| D-ii | Unificar en decaimiento agregado (`0.50·e^{−κΔt}`) para todo | ⛔ Doble descuento (el kernel ya decae) |
| D-iii | Unificar en `0.05N` para todo | ⛔ Deja el motor legado sin ley temporal |

---

## 5. SOLUCIÓN RECOMENDADA — PLAN DE MATERIALIZACIÓN (FASE 2)

| Fase | Acción | Archivos | Régimen | Reversible |
|---|---|---|---|---|
| **2A** | `γ_efectivo` → α; prohibición de defaults; `InsufficientDataException`; traza de masa | `intensity_canonical_loglink.py`, `sovereign_pipeline.py` | 🔴 `[DIRGEN-STRICT]` | Sí (revert atómico) |
| **2B** | GSL-3D v2: matriz causal en el IPO, normalización, MGS, síntesis RMS, `cobertura_variables` | `orthogonal_factor_engine.py`, `sovereign_pipeline.py`, contratos de ingesta | 🔴 `[DIRGEN-STRICT]` | Sí, con bandera `GSL3D_V2` |
| **2C** | Retiro de la ruta v1 y de `W_SEDE`; retículo a `[0,5]` | `sovereign_pipeline.py`, `distribution_dixon_coles.py` | 🔴 `[DIRGEN-STRICT]` | Sí |

**Orden obligatorio:** 2A entra sola (corrige un defecto de corrección, no de modelo). 2B cambia el
modelo y exige re-calibración y re-sellado. 2C sólo puede ejecutarse cuando 2B publique cobertura
suficiente en la temporada de referencia.

---

## 6. DIFF DE LA FASE 1 (APLICADO: SÓLO DOCUMENTACIÓN)

| Archivo | Cambio |
|---|---|
| `docs/DIRGEN_VAULT.md` | `[VAULT-CORE-001]` v2 + §E-50.1 (Invariante L-1, P-01/P-02, contrato de error, vectores de prueba) |
| `docs/LOGIC.md` | §7.2 clausura + §7.6 GSL-3D v2 + §7.7 ley H2H + 5 tombstones |
| `docs/CONSTANTS.md` | `β_alt`, `β_descanso`, `ε_log`, `n_min`; ámbito de `w_H2H` |
| `docs/ARCH.md` | Contrato de entrada del núcleo (C-1 / C-2) y matriz causal |
| `DIRGEN_VARIANCE_REQUEST.md` | Este parte |

**Cero cambios en `src/`.** `git status --short` no registra ninguna modificación en `qbe_core/src`,
`qbe_business`, `qbe_observatory`, `qbe_ingestion` ni `qbe_storage`.

> **Post-decreto (D1/D4).** Esta sección describe el estado de la Fase 1 en el momento de su
> redacción. Con posterioridad se materializaron las Fases 2A (`intensity_canonical_loglink.py`,
> `sovereign_pipeline.py`), 2B (`orthogonal_factor_engine.py` GSL-3D v2), 6 (`triage.py`)
> y 8; ese código es el que el Decreto D1–D5 ratifica como estándar oficial.

**Divergencia transitoria autorizada por este parte:** `docs/DIRGEN_VAULT.md` (ley) y
`qbe_core/src/core/intensity_canonical_loglink.py` (código) **no coinciden** hasta la Fase 2A. Es la
excepción explícita a `GOVERNANCE.md §1` regla 6 y queda limitada a este expediente.

---

## 7. DEFINITION OF DONE

### Fase 1 (esta entrega)

| # | Criterio | Comando | Umbral |
|---|---|---|---|
| 1 | Ley publicada en los cuatro libros | inspección `docs/` | ✅ |
| 2 | Sin cambios en `src/` | `git status --short` | ✅ |
| 3 | Jueces del núcleo intactos | `pytest qbe_core/tests -q` | `104 passed` |
| 4 | Sin IDs nuevos (ninguno sin registro) | `grep -o "LN-QBE-[0-9]*" docs/` | ✅ |
| 5 | Manifiesto | `git diff --stat` | ✅ |

### Fase 2 (bloqueada hasta decreto)

| # | Criterio | Umbral |
|---|---|---|
| 1 | Invariante L-1 | `|λ_H+λ_A−μ| ≤ 1e-12` en los 4 vectores de §2.1 |
| 2 | Cero defaults | `get("<clave>", <literal>)` en la ruta de λ = **0** |
| 3 | Ortogonalidad | `‖QᵀQ − I‖_F ≤ 1e-9`; colineales declaradas con pivote |
| 4 | No inflación | dos variables colineales ⇒ `A*` idéntico (`≤1e-9`) a una sola |
| 5 | Cobertura | `cobertura_variables` publicado en el 100 % de las trazas |
| 6 | Escudo | suite completa de los cinco pilares ⇒ **EXIT 0** |
| 7 | Re-sellado | paridad 3NF ↔ captura 100 % en la temporada de referencia |

---

## 8. RIESGOS Y DEPENDENCIAS

| Riesgo | Impacto | Mitigación |
|---|---|---|
| **Cobertura 9/32 del corpus** | Un corte estricto a 32/32 pone `S(I)=0` en todo el universo | Contrato completo + umbral `n_A,n_D ≥ 2` + deuda de ingesta declarada |
| **Cambio de IPO (matriz causal)** | Toca `qbe_ingestion` (fuera de esta jurisdicción) | 2B se activa sólo cuando la ingesta publique `M`; hasta entonces `GSL3D_V2=off` |
| **Re-calibración** | El motor v2 mueve λ y por tanto el Alpha de temporada | Re-sellado y medición antes/después (Fase 2C) |
| **Reescritura total** | Riesgo de regresión silenciosa | Jueces en RED antes de materializar (`KTP-04`), por fase |
| **Espejo `qbe_core/docs/DIRGEN_VAULT.md`** | Dos leyes en circulación | Sincronizar en 2A (fuera de la jurisdicción actual) |

---

## 9. DECISIONES DECRETADAS (D1–D5)

**Decreto:** D1–D5 **APROBADOS** por la Dirección el 2026-11-04.

| # | Decisión | Veredicto |
|---|---|---|
| **D1** | Autorizar la reescritura de `sovereign_pipeline.py` e `intensity_canonical_loglink.py` (Fase 2A) | **Sí** — corrige un defecto de corrección, no un cambio de modelo |
| **D2** | Ratificar la doctrina de cobertura: contrato 32/32 + umbral operativo `n_A,n_D ≥ 2` + deuda declarada | **Sí** — la alternativa apaga la operación |
| **D3** | Ratificar la propiedad única de la ley H2H (`E-50.2`) | **Sí** — elimina el doble descuento |
| **D4** | Autorizar el cambio de IPO (matriz causal) y su impacto en `qbe_ingestion` | **Sí, diferido a 2B** |
| **D5** | Ordenar la sincronización de `qbe_core/docs/DIRGEN_VAULT.md` | **Sí** — deuda de paridad documental |

---

**ESTADO FINAL DEL PARTE:** 🟢 **RATIFICADO Y CERRADO.** Decreto D1–D5 aprobado por la Dirección:
la Fase 2A/2B y las Fases 4, 6 y 8 quedan ratificadas y el código materializado es el estándar
oficial del expediente. El Alto al Fuego queda levantado.

---
---

# ANEXO A — PARTE ANTERIOR CONSERVADO ÍNTEGRO

> Conservado por trazabilidad (`KTP-10`). Corresponde al parte `SPRINT-47-UNIFICACION-FOTMOB-Y-LANZADOR`
> presente en este mismo archivo antes de la apertura de `VAR-2026-SPRINT50-CORE`. No se altera su
> contenido; su vigencia se resuelve por separado.

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
