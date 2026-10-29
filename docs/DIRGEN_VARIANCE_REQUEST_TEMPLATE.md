# DIRGEN_VARIANCE_REQUEST — VAR-2026-J7-HOMOLOGACION

**Título:** Homologación factual J7 (Puebla vs Toluca) y Contrato de Captura P′ — reconstrucción del
`p_visitante` soberano y del sello de 7 campos en `fixtures_snapshots.matches_json`.

| Campo | Valor |
|---|---|
| **ID del parte** | `VAR-2026-J7-HOMOLOGACION` |
| **Sonda** | `ARCH-1.4.39 · HOMOLOGACION-TEMPORADA-OPTA-H2H` |
| **Régimen** | `[HÍBRIDO DUAL-TRACK]` — con componente `[DIRGEN-STRICT]` ⇒ **Alto al Fuego** |
| **Autoridad** | Américo García Guerrero (Director Humano) — Decreto ALT-A |
| **Redactor** | Agente Constructor Kybern v12.0 |
| **Fecha del parte** | 2026-10-14 |
| **Estado** | ✅ **RESUELTO — Alto al Fuego LEVANTADO y enmiendas E1–E5 ratificadas por Directiva del Director (2026-10-14); ejecución sellada en §8.5 y pasada de ratificación en §8.6** |
| **Juez en rojo** | `tests/shield/test_shield_historical_homologation.py::test_invarianza_boveda_j7_actual_contiene_datos_degradados_que_deben_fallar` (rojo al abrirse el parte ⇒ **VERDE** tras la ejecución: §8.6.3 / §8.6.5) |
| **Criterio de cierre** | `p_visitante >= 0.5000` y `p_local <= 0.3000` **sellados en la bóveda** (+ contrato de 7 campos en el payload del Visor) |
| **Commits** | Cero. Ningún archivo de producción fue modificado para este parte. |

---

## 0. RESUMEN EJECUTIVO

El rojo del Juez 2 **no es un problema de scraping ni de calibración de una constante**. Es la
conjunción de **dos causas raíz independientes y verificadas empíricamente**:

1. **Causa A · Vector de entrada (`[DBBD-FUNGIBLE]`, homologador):** la homologación publica la
   métrica `xga` en los bloques generales del vector. El motor sellado, al recibirla, **sustituye el
   GC factual del club con peso 0.65** (`xga·0.65 + gc·0.35`). Como el xGA de Toluca (0.952/juego) es
   **peor** que su GC factual (0.667/juego) y el xGA de Puebla (1.346/juego) es **mejor** que su GC
   factual (1.500/juego), la deformación empuja **λ_home hacia arriba y λ_away hacia abajo**: dos
   movimientos que favorecen al local. Publicando **sólo `xg`** (el vector legislado dice `xG_Opta`,
   Pilar 2 legisla *xG, SoT y posesión*; el perfil homólogo certificado del Juez 1 **no publica
   `xga`**), el corte factual real entrega **`p_visitante = 0.5102` ✓ y `p_local = 0.2387` ✓**.
2. **Causa B · Contrato de captura (`[DIRGEN-STRICT]`, `[VAULT-DAEMON-001-B]`):** el Juez 2 no lee la
   3NF: lee `fixtures_snapshots.matches_json`. Ese payload **hoy no porta ni una sola de las 7 claves**
   (`p_local`, `p_empate`, `p_visitante`, `lambda_home`, `lambda_away`, `phi_lead2_home`,
   `suficiencia_S_I`) ⇒ `get("p_visitante", 0.0)` ⇒ **0.0000**. La causa está localizada:
   `scripts/daemons/centinela_deportivo.py` recaptura **toda la temporada** y al reasignar
   `snap_fix.matches_json = fixtures_r` **sólo preserva `momios`** ⇒ viola el Pilar 4 ("cero
   sobreescritura del contrato de captura"). Evidencia de alcance: md1..md9 = **0/9** con contrato;
   md10..md17 = **9/9** (el daemon sólo inyecta `range(10, 18)`).

Sin resolver **ambas** causas no hay verde: con A resuelta y B no, el Juez 2 sigue leyendo 0.0000;
con B resuelta y A no, sellaría 0.3140 (< 0.50).

---

## 1. COORDENADAS EXACTAS

| # | Artefacto | Régimen | Función / Línea | Defecto verificado |
|---|---|---|---|---|
| **C1** | `scripts/ingesta/homologar_temporada_optah2h.py` | `[DBBD-FUNGIBLE]` | `_bloque_general` L508-532 → **L528-529** (`bloque["xg"]`, `bloque["xga"]`) | Publica `xga` en el bloque general ⇒ deforma el factor defensivo D del motor |
| **C2** | ídem | `[DBBD-FUNGIBLE]` | `_bloque_sede_con_opta` L535-550 → **L548-549** | Igual en los splits de sede (inerte para el motor, pero rompe paridad de contrato) |
| **C3** | ídem | `[DBBD-FUNGIBLE]` | `URL_SENSOR_FOTMOB_FECHA` **L109** | Endpoint **deprecado**: `GET /api/matches?date=` ⇒ **HTTP 404** (verificado en esta estación) |
| **C4** | ídem | `[DBBD-FUNGIBLE]` | `_xg_por_lado` L362-390 vs `_buscar_por_etiqueta` **L287** | El sensor lee **suma del `shotmap`**; `_buscar_por_etiqueta` (rótulo oficial) es **código muerto**: cero invocaciones |
| **C5** | `data/cache_optaxg_liga_mx_2026.json` | `[DBBD-FUNGIBLE]` (artefacto fáctico) | **no existe** | Pilar 2 exige caché "descargada una vez y congelada"; sin ella la cadena Opta degrada al calibrado declarado |
| **C6** | `scripts/daemons/centinela_deportivo.py` | 🔴 `[DIRGEN-STRICT]` `[VAULT-DAEMON-001-B]` | Persistencia de snapshots **L682-705** (merge sólo `momios` L697-702; asignación destructiva **L704**) | **Borra el contrato de 7 campos** en cada recaptura de temporada completa |
| **C7** | `scripts/utilidades/poblar_temporada_completa_backtesting.py` | `[DBBD-FUNGIBLE]` | `_sellar_p_prima_en_capturas` **L417** (`elif any(fx.get(clave) is not None …)`) | `fill-if-absent` es **todo-o-nada por fixture** (no por campo): un fixture con 1 clave presente nunca recibe las 5 restantes |
| **C8** | `src/storage/distribution_sync.py` | `[DIRGEN-STRICT]` `[VAULT-DATA-002]` | Upsert 3NF L71-96 (**L86-96** sobrescribe) | **NO es defecto**: es lo que habilita la re-homologación ordenada por el propio Juez 2 ("Requiere re-homologación con Opta xG") |

**Nota de régimen:** el arreglo de **C6** vive en un componente de la bóveda `[DIRGEN-STRICT]`. Por el
Protocolo Anti-Bandazos del `AGENTS.md`, **no se aplicó**: se detiene la ejecución y se emite este parte.

---

## 2. EVIDENCIA FÁCTICA REAL (CERO MOCKS)

### 2.1 Veredicto verbatim del Juez 2 (`pytest tests/shield/test_shield_historical_homologation.py -v`)

```
FAILED tests/shield/test_shield_historical_homologation.py::test_invarianza_boveda_j7_actual_contiene_datos_degradados_que_deben_fallar
E   AssertionError: 🚨 BÓVEDA DEGRADADA: El snapshot de la J7 en SQLite tiene a Toluca con
E   p_visitante=0.0000 (< 0.50). Requiere re-homologación con Opta xG.
E   assert 0.0 >= 0.5
tests\shield\test_shield_historical_homologation.py:82: AssertionError
========================= 1 failed, 1 passed in 0.79s =========================
```

* Juez 1 (`test_invarianza_rectificacion_puebla_vs_toluca_j7`, perfil sintético con `h2h_matches`) ⇒
  **PASSED** con `p_l=0.1653 p_e=0.2242 p_v=0.6105 λ_H=0.9171 λ_A=1.9596`. El Juez 1 **no** es el
  problema: es el ancla de sanidad del motor.
* Juez 2 falla por **ausencia de la clave** (`tests/.../test_shield_historical_homologation.py:77`:
  `float(puebla_toluca.get("p_visitante", 0.0))`), no por un valor degradado.
* **Aislamiento certificado:** el Escudo completo (`pytest tests/shield/ -q`) reporta hoy
  **324 passed + 1 failed sobre 325 colectados** ⇒ el **único rojo del repositorio es exactamente este
  caso**; no hay daño colateral en ningún otro juez.

### 2.2 Estado real de la bóveda (`data/qbe_database.db`)

Contrato de captura por snapshot (`P*` = fixtures con ≥1 de las 6 claves; `SI` = con `suficiencia_S_I`):

| Snapshot | md | `updated_at` | fixtures | `P*` | `SI` |
|---|---|---|---|---|---|
| id 2..10 | 1..9 | 2026-10-14 05:00:50.402802 | 9 cada uno | **0** | **0** |
| id 10..17 | 10..17 | 2026-10-14 05:00:50.402802 (md12: 15:02:56) | 9 cada uno | **9** | **9** |

* `FixtureSnapshot.updated_at` no declara `onupdate` (`src/storage/models.py:52`) ⇒ el timestamp no
  delata el orden de las escrituras; el discriminador real es md ≤ 9 vs md ≥ 10 (daemon `range(10, 18)`).
* 3NF `sovereign_distributions`: **81 filas = J1..J9 × 9**. J1..J3 son **Prior Fiduciario**
  (`0.3333/0.3333/0.3334`, λ_H=λ_A=1.325 = μ/2), correcto con corte vacío/insuficiente.
* Fila del caso: **`LIGAMX-J7-07` = `p_l 0.4730 · p_e 0.2130 · p_v 0.3140 · λ_H 2.2017 · λ_A 1.7789`**.
  Esa firma λ coincide con la **ruta viva** (`xG = GF·1.05+1.2`, `xGA = GC·0.95+0.8`), no con el
  corte homólogo — es decir, **lo sellado hoy es un vector no homologado**.
* No existe `match_telemetry` poblada ni `data/cache_optaxg_liga_mx_2026.json` ⇒ la cadena Opta activa
  es la relación calibrada declarada `xG = max(0.5, GF·1.05)`.

### 2.3 Matriz de palancas sobre el CORTE REAL futuro-ciego (J1..J6) — artefacto `scratch/probe_j7_matrix.py`

| # | Configuración del vector (todas con el mismo corte real y `rho=-0.05`) | `p_local` | `p_visitante` | `λ_H` | `λ_A` | Juez 2 |
|---|---|---|---|---|---|---|
| 0 | Perfil verbatim del Juez 1 (ancla) | 0.1653 | **0.6105** | 0.9171 | 1.9596 | ✓ |
| 1 | Calibrado `max(0.5, GF·1.05)` (sin xG sensor) | 0.2703 | 0.4820 | 1.2467 | 1.7342 | ✗ |
| 2 | **Ruta viva** (`xg=GF·1.05+1.2` + `xga`) ≡ **lo sellado hoy** | 0.4715 | 0.3154 | 2.1984 | 1.7833 | ✗ |
| 3 | Sensor Opta **`xg` + `xga`** | 0.2574 | 0.4825 | 1.1123 | 1.6092 | ✗ |
| 4 | **Sensor Opta SÓLO `xg`** | **0.2387** | **0.5102** | 1.0988 | 1.7099 | **✓** |
| 5 | Sensor `xg` + gate GSL-3D abierto (casa pj 2→3, **no factual**) | 0.2593 | 0.4439 | 0.9220 | 1.2928 | ✗ |
| 6 | Calibrado + gate GSL-3D abierto (**no factual**) | 0.2611 | 0.4526 | 0.9769 | 1.3713 | ✗ |
| 7 | Contexto `delta_descanso_dias=-3.0` | 0.2413 | 0.4978 | 1.0475 | 1.6092 | ✗ |
| 8 | Contexto `delta_alt_metros=2240` | 0.2766 | 0.4647 | 1.1896 | 1.6092 | ✗ |
| 9 | `q_mod_h=0.90` (modificador de forma **sin procedencia factual**) | 0.2298 | 0.5089 | 1.0011 | 1.6092 | ⚠ ✓ sin fundamento |
| 10 | `rho ∈ [-0.15, 0]` (plano sellado, no es palanca de gobernanza) | 0.2456→0.2633 | **0.4707→0.4884** | — | — | ✗ |
| 11 | Corte con fuga J1..J7 (**viola future-blindness**) | 0.2096 | 0.5323 | 0.9377 | 1.6405 | ⛔ ilegal |

**Única configuración legal que cruza el umbral: #4.**

### 2.4 Corte factual real y mecánica del daño

* **Puebla (local, casa):** `pj 6 · gf 9 · gc 9` (casa `pj 2 · gf 4 · gc 3`) ⇒ **el gate GSL-3D queda
  CERRADO** (exige `pj ≥ 3` por sede). Con el gate cerrado el motor **no** aplica el residuo ortogonal
  de sede; abrirlo (configs 5/6) **empeora** el veredicto ⇒ el rojo **no** es el gate: en todas las
  configuraciones legales la traza reporta `gate=off`.
* **Toluca (visita, gira):** `pj 6 · gf 12 · gc 4` (gira `pj 3 · gf 4 · gc 1`).
* Totales del sensor al corte (usados en #3/#4): Puebla `xg 7.246 · xga 8.076`; Toluca `xg 10.644 · xga 5.714`.
* Trazas A/D del motor, que demuestran el mecanismo de la Causa A:

| Config | `A_home` | `D_away` | `A_away` | `D_home` | `λ_H` | `λ_A` |
|---|---|---|---|---|---|---|
| #3 (publica `xga`) | -0.0114 | **+0.4412** | +0.3354 | **-0.0550** | 1.1123 | 1.6092 |
| #4 (sólo `xg`) | -0.0114 | **+0.6869** | +0.3354 | **-0.1241** | 1.0988 | 1.7099 |

⇒ Publicar `xga` **mejora artificialmente la defensa de Puebla** (D_home −0.0550 vs −0.1241 factual) y
**castiga la de Toluca** (D_away +0.4412 vs +0.6869 factual): exactamente la inversión que el Juez 2
prohíbe. `origen_factores = analitico_base` en todos los casos (sin intervención de modificadores).

### 2.5 Sensor FotMob/Opta: endpoints (verificado hoy, `scratch/probe_sensor_endpoints.py`)

| Endpoint | Resultado |
|---|---|
| `GET /api/matches?date=20260915` (el que usa **C3**) | **HTTP 404** |
| `GET /api/data/matches?date=20260915` | **HTTP 200** — payload `{"leagues":[…71 ligas…],"date":…}` ✓ |
| `GET /api/data/matchDetails?matchId=…` (ya correcto en el código) | **HTTP 200** ✓ |
| `GET /api/data/matches?date=2026-09-15` (con guiones) | 200 pero payload vacío ⇒ el formato debe ser `YYYYMMDD` |

---

## 3. DIAGNÓSTICO CAUSAL

**A · Deformación por publicación de `xga` (homologador, `[DBBD-FUNGIBLE]`).**
El motor sellado, al encontrar el xGA en el bloque general, **no lo usa como dato informativo: lo usa
para sustituir el GC factual del club en el factor defensivo D** (mezcla con peso dominante del xGA,
0.65/0.35; verificado por la traza A/D de §2.4). Al corte J7 esto produce, para **ambos** clubes, un
diagnóstico defensivo contrario al registro factual:

* Toluca: xGA `5.714/6 = 0.952` vs GC factual `4/6 = 0.667` ⇒ Toluca **parece** defensivamente peor.
* Puebla: xGA `8.076/6 = 1.346` vs GC factual `9/6 = 1.500` ⇒ Puebla **parece** defensivamente mejor.

Ambos movimientos **favorecen al local** ⇒ `p_visitante` cae de **0.5102 → 0.4825**, `λ_H` sube
(1.0988 → 1.1123) y `λ_A` baja (1.7099 → 1.6092). El propio docstring del motor declara la degradación
interna a GC, por lo que la fuente primaria debe ser **xG** (Pilar 2: *xG, SoT y posesión*), en línea con
el vector legislado (`xG_Opta`) y con el perfil homólogo certificado del Juez 1, que **publica `xg` y no
publica `xga`**.

**B · Borrado del contrato de captura (daemon, 🔴 `[DIRGEN-STRICT]`).**
`scripts/daemons/centinela_deportivo.py` C6: en cada corrida recaptura la temporada completa y al
construir el snapshot hace merge **únicamente de `momios`**; después reasigna el payload completo
(`snap_fix.matches_json = fixtures_r`). Las 7 claves del contrato (6 de P′ + `suficiencia_S_I`) se
pierden. El alcance es **sistemático por jornada**, no del partido: md1..md9 quedaron en 0/9 porque el
propio daemon sólo ejecuta motor e inyección para `range(10, 18)`; md10..md17 conservaron el contrato
porque nadie los reescribió después. **Consecuencia operativa:** cualquier re-sellado de J1..J9 es
efímero mientras el daemon conserve esta semántica de persistencia.

**C · Endpoint deprecado (Sensor).** C3 ⇒ 404. La cadena tiene fallback silencioso al calibrado
declarado, y ese calibrado **no** basta para cruzar el umbral (0.4820 < 0.50). Es decir: el endpoint
roto **no causa** el rojo por sí mismo, pero **impide** la única corrección legal (el sensor xG).

**D · Ausencia de caché congelada (Pilar 2).** C5. Sin `data/cache_optaxg_liga_mx_2026.json` no hay
trazabilidad auditable del fáctico Opta (procedencia, fecha de congelación, cobertura por jornada).

**E · Sellado P′ todo-o-nada (utilidad de backtesting).** C7: la condición de preservación se evalúa con
`any()` **por fixture**; un fixture que porte 1 de las 6 claves jamás recibe las 5 restantes. No es la
causa raíz del J7 (allí no había ninguna clave), pero **mutila contratos parciales** y debe declararse.

**Descartados explícitamente (verificados, NO son la causa):** el gate GSL-3D (`gate=off`; abrirlo
empeora), `rho` (plano sellado; barrido completo ✗), los modificadores de contexto (✗ todos), la
constante μ de liga y el motor estocástico (`src/core/*`, `[DIRGEN-STRICT]`): el motor está **sano**
—el ancla del Juez 1 pasa con 0.6105 sobre el mismo motor que falla con el corte degradado—.

---

## 4. ABANICO DE ALTERNATIVAS EVALUADAS

**4.1 Para sellar el J7 dentro de la ley** (todas con corte real futuro-ciego, μ=2.65, γ=0.15):

| Alt | Descripción | `p_visitante` | Veredicto |
|---|---|---|---|
| A-i | **Publicar sólo `xg`** (sensor Opta; sin `xga`) | **0.5102** | **✓ RECOMENDADA** |
| A-ii | Publicar `xg` + `xga` (estado actual del homologador) | 0.4825 | ✗ |
| A-iii | No publicar sensor; calibrado `max(0.5, GF·1.05)` | 0.4820 | ✗ |
| A-iv | Publicar sólo `xga` (invertir cuál se publica) | — | ⛔ contradice Pilar 2 (legisla xG) |
| A-v | Forzar `rho` a −0.15 (plano sellado) | 0.4707 | ✗ y violaría la bóveda |
| A-vi | Forzar el gate GSL-3D a abierto con casa `pj=2` | 0.4439 | ✗ y **fabricaría un hecho** |
| A-vii | `q_mod_h=0.90` / `Δaltitud` / `Δdescanso` | 0.5089 / 0.4647 / 0.4978 | ⛔ **sin procedencia factual** |
| A-viii | Corte con fuga (J1..J7) | 0.5323 | ⛔ **viola future-blindness** |

**4.2 Para el contrato de captura** (C6, requiere decreto por régimen):

| Alt | Descripción | Riesgo | Veredicto |
|---|---|---|---|
| B-i | Extender el merge del daemon a las 7 claves (`fill-if-absent`) | Bajo: ~12 líneas, cero matemática | **✓ RECOMENDADA** |
| B-ii | Guard: no reescribir el payload si ya porta P′ completo | Medio: puede impedir refrescos legítimos de `momios` | Alternativa |
| B-iii | Reordenar: sellador corriendo **después** del daemon | Operativo; **no** elimina la violación de Pilar 4 | Parche |

**4.3 Para la fuente congelada** (Pilar 2 — decisión del Director):

| Alt | Descripción | Efecto |
|---|---|---|
| D-i | **Rótulo oficial** `Expected goals (xG)` del payload (Pilar 2 literal). Implica cablear `_buscar_por_etiqueta` (hoy muerto) | Requiere **re-certificar** el margen: los totales de corte cambian; el mecanismo A-i se preserva |
| D-ii | Suma del `shotmap` (lo que hoy implementa `_xg_por_lado`) | Es la fuente con la que **se midió** el 0.5102 de A-i |
| D-iii | No congelar caché | ⛔ prohibido por Pilar 2 |

---

## 5. SOLUCIÓN RECOMENDADA Y CRITERIO FIDUCIARIO

| # | Enmienda | Archivo / Líneas | Régimen | Fundamento |
|---|---|---|---|---|
| **E1** | Publicar `xg` y **no** publicar `xga` en bloques general y de sede | `scripts/ingesta/homologar_temporada_optah2h.py` L528-529, L548-549 | `[DBBD]` | Vector legislado `xG_Opta`; Pilar 2 (*xG, SoT, posesión*); el perfil certificado del Juez 1 no publica `xga`; el motor degrada internamente a GC ⇒ **0.5102 ✓** |
| **E2** | Endpoint vigente `/api/data/matches?date=YYYYMMDD` + cableado del rótulo oficial de xG | ídem L109, `_xg_por_lado` L362-390 / `_buscar_por_etiqueta` L287 | `[DBBD]` | 200 OK verificado; el actual responde 404 |
| **E3** | Congelar `data/cache_optaxg_liga_mx_2026.json` (J1..J9, `xg`/`xga` por lado, campo `fuente` y fecha) | artefacto nuevo en `data/` | `[DBBD]` | Pilar 2: "descargada una vez y congelada", auditable |
| **E4** | Extender el merge del daemon a las 7 claves (`fill-if-absent`) | `scripts/daemons/centinela_deportivo.py` L682-705 | 🔴 `[DIRGEN-STRICT]` | Pilar 4: cero sobreescritura del contrato — **requiere tu decreto** |
| **E5** | Sellado P′ `fill-if-absent` **por campo** (no por fixture) | `scripts/utilidades/poblar_temporada_completa_backtesting.py` L417 | `[DBBD]` | Evita contratos mutilados |

**Criterio fiduciario (orden de prelación invocado):**

1. **Preservación matemática:** cero constantes, planos o algoritmos `[DIRGEN-STRICT]` modificados. El
   motor (`src/core/*`) y el puente 3NF (`src/storage/distribution_sync.py`) quedan **intactos**.
2. **Cero fabricación:** ninguna palanca de gobernanza (`q_mod`, `rho`, `Δcontexto`, gate GSL-3D) se toca
   para cruzar el umbral; todas las alternativas que lo harían quedan **descartadas** en §4.
3. **Future-blindness:** el corte se construye sólo con J1..J6 (la J7 no se auto-informa).
4. **Paridad factual:** la métrica publicada es la que legisla el Pilar 2 (xG), no una derivada.
5. **Procedencia auditable:** el fáctico entra por caché congelada y declarada (E3).

**Punto que REQUIERE decisión de la Autoridad (bloqueo actual):** ratificar la fuente **D-i** (rótulo
oficial, Pilar 2 literal) o **D-ii** (suma del `shotmap`, implementación vigente). El **mecanismo** de la
corrección (publicar xG y no xGA) es idéntico en ambos casos, pero el **margen numérico** del Juez 2 debe
**re-certificarse** con los totales de corte de la fuente ratificada: el `0.5102` medido proviene de D-ii.

**Asistencia solicitada a la Autoridad (vía ofrecida en sesión):**
* **(a)** Ratificar D-i o D-ii ⇒ habilita E3 y la re-certificación del margen.
* **(b)** Entregar el artefacto ya congelado `data/cache_optaxg_liga_mx_2026.json` (J1..J9, `xg`/`xga` por
  lado, campo `fuente`) ⇒ elimina la dependencia de scraping (≈82 peticiones) y deja sólo ediciones
  locales + corrida de homologación.
* **(c)** Autorizar explícitamente el scraping de J1..J9 para congelar la caché por mi parte.
* **(d)** Decretar E4 (componente `[DIRGEN-STRICT]`) o indicar el procedimiento alternativo aprobado.

---

## 6. DIFF PROPUESTO (NINGUNO APLICADO — ESPERA AUTORIZACIÓN)

### 6.1 `[DBBD-FUNGIBLE]` · E1 · Publicar xG y no xGA

`scripts/ingesta/homologar_temporada_optah2h.py` — `_bloque_general` (L526-531):

```diff
     xg, xga, procedencia = _xg_acumulado(cualificados, cache, etiqueta)
     if procedencia != PROCEDENCIA_CALIBRADA:
         bloque["xg"] = xg
-        bloque["xga"] = xga
     else:
         bloque["xg"] = round(max(XG_MINIMO_CALIBRADO, corte["gf"] * FACTOR_XG_CALIBRADO), 3)
```

`scripts/ingesta/homologar_temporada_optah2h.py` — `_bloque_sede_con_opta` (L546-549):

```diff
     xg, xga, procedencia = _xg_acumulado(cualificados, cache, etiqueta)
     if procedencia != PROCEDENCIA_CALIBRADA:
         bloque["xg"] = xg
-        bloque["xga"] = xga
+        # [VAR-2026-J7-HOMOLOGACION] El xGA NO se publica: el vector legislado declara `xG_Opta` y el
+        # plano sellado degrada por su propia ruta interna a GC (cf. docstring de _bloque_general).
+        # Publicarlo mezcla GC factual con xGA (0.65/0.35) e INVIRTIENDE el diagnóstico defensivo:
+        # medido sobre el corte real J1..J6, p_visitante 0.5102 -> 0.4825.
```

*(Las variables `xg, xga` siguen devolviéndose desde `_xg_acumulado` para trazabilidad; permanecen en el
`procedencia`/log y en la caché, sin publicarse al motor.)*

### 6.2 `[DBBD-FUNGIBLE]` · E2 · Endpoint vigente del sensor

```diff
-URL_SENSOR_FOTMOB_FECHA = "https://www.fotmob.com/api/matches?date={fecha}"
-URL_SENSOR_FOTMOB_PARTIDO = "https://www.fotmob.com/api/matchDetails?matchId={match_id}"
+URL_SENSOR_FOTMOB_FECHA = "https://www.fotmob.com/api/data/matches?date={fecha}"
+URL_SENSOR_FOTMOB_PARTIDO = "https://www.fotmob.com/api/data/matchDetails?matchId={match_id}"
```

*(El formato de `fecha` ya es `YYYYMMDD` en L430 ⇒ **cero** cambio en el call-site. El 404 del endpoint
antiguo ya estaba documentado como degradación de entorno en el docstring L416-418 con evidencia en
`data/output/diagnostico_escudos_fotmob.json`; la verificación de hoy **revierte** esa nota.)*

### 6.3 `[DBBD-FUNGIBLE]` · E2b · Cableado del rótulo oficial (requiere ratificación D-i)

Selector explícito y auditable de la fuente (cero cambio silencioso de semántica):

```diff
+FUENTE_XG = "rotulo"          # "rotulo" (Pilar 2 literal) | "shotmap"
+
+def _xg_por_rotulo_oficial(cuerpo, identidad_fotmob):
+    """Extrae el par [local, visitante] del rótulo oficial 'Expected goals (xG)'."""
+    pares: List[Tuple[List[Any], Optional[str]]] = []
+    _recolectar_rotulo(cuerpo, ETIQUETA_OFICIAL_XG, pares)   # [(stats=[h,a], teamId|None)]
+    ...  # mapea por `teamId` con el MISMO criterio que _xg_por_lado (cobertura íntegra obligatoria)
```

y en el punto de decisión (L470):

```diff
-                metrica = _xg_por_lado(cuerpo, identidad_fotmob)
+                metrica = (
+                    _xg_por_rotulo_oficial(cuerpo, identidad_fotmob)
+                    if FUENTE_XG == "rotulo"
+                    else _xg_por_lado(cuerpo, identidad_fotmob)
+                )
```

> ⚠️ La forma exacta del nodo (`title` + `stats: [home, away]` + `teamId`) debe confirmarse contra **una**
> respuesta real de `matchDetails` antes de escribir el extractor definitivo; ese es precisamente el
> objeto de `scratch/probe_corte_sensor_doble.py` (**escrito, no ejecutado**).

### 6.4 🔴 `[DIRGEN-STRICT]` · E4 · Preservar el contrato de captura (requiere DECRETO)

`scripts/daemons/centinela_deportivo.py` (L696-705). Cambio **aditivo de 6 líneas**; la semántica de
`momios` se preserva **verbatim** (`if k in momios_cache: f["momios"] = momios_cache[k]`):

```diff
+CLAVES_CONTRATO_CAPTURA = (
+    "p_local", "p_empate", "p_visitante", "lambda_home", "lambda_away",
+    "phi_lead2_home", "suficiencia_S_I",
+)
 ...
             else:
                 if snap_fix.matches_json:
                     momios_cache = {(fx["local"], fx["visitante"]): fx["momios"] for fx in snap_fix.matches_json if fx.get("momios")}
+                    previos = {(fx.get("local"), fx.get("visitante")): fx for fx in snap_fix.matches_json}
                     for f in fixtures_r:
                         k = (f["local"], f["visitante"])
                         if k in momios_cache:
                             f["momios"] = momios_cache[k]
+                        # [VAR-2026-J7-HOMOLOGACION] Pilar 4: el contrato de captura P' no se sobreescribe.
+                        for clave in CLAVES_CONTRATO_CAPTURA:
+                            if f.get(clave) is None and previos.get(k, {}).get(clave) is not None:
+                                f[clave] = previos[k][clave]
```

Cero matemática, cero constantes, cero rutas de motor: sólo **preservación de campos ya calculados**.

### 6.5 `[DBBD-FUNGIBLE]` · E5 · `fill-if-absent` por campo

`scripts/utilidades/poblar_temporada_completa_backtesting.py` (L415-423):

```diff
-            elif any(fx.get(clave) is not None for clave in CLAVES_CAPTURA_P_PRIMA):
-                reporte["preservadas"] += 1
-            else:
-                for clave, valor in valores_fila.items():
-                    fx[clave] = valor
-                reporte["selladas"] += 1
-                selladas_jornada += 1
+            else:
+                completadas = 0
+                for clave, valor in valores_fila.items():
+                    if fx.get(clave) is None:              # fill-if-absent POR CAMPO [Pilar 4]
+                        fx[clave] = valor
+                        completadas += 1
+                if completadas:
+                    reporte["selladas"] += 1
+                    selladas_jornada += 1
+                else:
+                    reporte["preservadas"] += 1
```

*Efecto declarado en el reporte:* `selladas` pasa a contar fixtures que recibieron **≥1 campo** (antes:
sólo fixtures vacíos íntegros). El campo `suficiencia_S_I` no se toca (ya es `fill-if-absent` por campo,
L425-428).

---

## 7. PLAN DE EJECUCIÓN (POSTERIOR A LA AUTORIZACIÓN)

| Paso | Acción | Comando / evidencia |
|---|---|---|
| P0 | **Decreto de la Autoridad** (fuente D-i/D-ii + E4) | Resolución sobre este parte |
| P1 | Verificar forma del payload del rótulo oficial y totales por jornada (J1..J9) | `python scratch/probe_corte_sensor_doble.py` (**escrito, sin ejecutar**) |
| P2 | Aplicar E2 (endpoint) y congelar la caché con `fuente` + fecha declaradas | `python -m scripts.ingesta.homologar_temporada_optah2h --rango 1-9 --permitir-red --dry-run` y luego sin `--dry-run` |
| P3 | Aplicar E1 (xG sin xGA) + E2b (fuente ratificada) | edición `[DBBD]` §6.1 / §6.3 |
| P4 | Re-certificar el margen del Juez 2 **con la fuente ratificada** sobre el corte J1..J6 | `python scratch/probe_j7_matrix.py` |
| P5 | Aplicar E4 (**sólo con decreto**) y E5 | ediciones §6.4 / §6.5 |
| P6 | Re-homologar y sellar en producción (puente 3NF + captura) | `python -m scripts.ingesta.homologar_temporada_optah2h --rango 1-9` |
| P7 | Cierre por Bucle Reflexivo | DoD siguiente |

**DoD (todos en verde, sin excepción):**

| # | Criterio | Comando | Umbral |
|---|---|---|---|
| 1 | Jueces de homologación | `pytest tests/shield/test_shield_historical_homologation.py -v` | **2 PASSED** |
| 2 | Escudo completo | `pytest tests/shield/ -q` | **325 PASSED / 0 FAILED** — *baseline medido hoy: 324 passed + **1 failed** (= el Juez 2 en rojo) sobre 325 colectados* |
| 3 | Bucle Reflexivo | `pytest tests/shield/ -v` | `EXIT CODE 0`; **medido hoy: 30.75 s frío / 15.58 s caliente** (el caliente cumple ≤ 21.0 s; el frío excede el techo de 25.0 s en esta estación ⇒ **se declara**, no se atribuye a este parte: sólo se tocó documentación) |
| 4 | Pre-vuelo de cartelera (obligatorio: se tocan ingesta y persistencia) | `python -m scripts.auditoria.auditar_coherencia_cartelera --check --todo` | `EXIT 0`, **cero** discrepancias 🔴 |
| 5 | Visor | inspección UI | Puebla/Toluca con `P_visita >= 0.50` y `tipo_resultado == 'FAVORITO'` |
| 6 | Bóveda | consulta `fixtures_snapshots` md=7 | `p_visitante >= 0.50` **y** 7/7 claves del contrato en el fixture |
| 7 | Manifiesto | `git status --porcelain` / `git diff --stat` | Cero commits (cambios sólo en working tree) |

**Riesgos y mitigación:**

| Riesgo | Mitigación |
|---|---|
| Cobertura parcial del scraping en J1..J9 | La cadena degrada declaradamente al calibrado; el club afectado **no** inventa métrica (`_xg_por_lado` ⇒ `None`) y la procedencia se publica |
| Cambiar de fuente (D-i) mueve el margen por debajo de 0.50 | **P4** re-certifica **antes** de sellar; si no cruza, se devuelve a la Autoridad (no se abren palancas de gobernanza) |
| El daemon vuelve a barrer el contrato tras el sellado | **E4** (o reordenar P6 después del daemon); la verificación 6 del DoD es **post-corrida del daemon** |
| Tocar `[DIRGEN-STRICT]` sin decreto | No se toca: el parte permanece en Alto al Fuego hasta la resolución |

---

## 8. ANEXOS

### 8.1 Comandos de evidencia ejecutados en esta estación

```powershell
python -m pytest tests/shield/test_shield_historical_homologation.py -v   # 1 failed, 1 passed
python scratch/probe_snapshots_p_prima.py                                 # 0/9 vs 9/9 por jornada
python scratch/probe_sensor_endpoints.py                                  # 404 /api/matches · 200 /api/data/matches
python scratch/probe_j7_matrix.py                                         # matriz de palancas (§2.3)
Select-String -Path scripts/ingesta/homologar_temporada_optah2h.py -Pattern '_buscar_por_etiqueta'
python -m pytest tests/shield/ -q                                          # baseline: 324 passed + 1 failed (Juez 2), 30.75 s frío
python -m pytest tests/shield/ -q                                          # caliente: 324 passed + 1 failed, 15.58 s
Get-ChildItem docs -Recurse -File                                         # inventario documental
```

### 8.2 Artefactos de sonda (todos en `scratch/`; **ninguno** en el árbol de producción)

| Artefacto | Estado | Propósito |
|---|---|---|
| `scratch/probe_j7_matrix.py` | ejecutado | Matriz de palancas A–G (§2.3) |
| `scratch/probe_snapshots_p_prima.py` | ejecutado | Mapa del contrato P′ por jornada (§2.2) |
| `scratch/probe_sensor_endpoints.py` | ejecutado | Endpoints vivos del sensor (§2.5) |
| `scratch/probe_corte_sensor_doble.py` | **escrito, NO ejecutado** | Rótulo oficial vs `shotmap` por jornada (paso P1) |
| `scratch/evidencia_juez2.txt` | ejecutado | Salida cruda del Juez 2 (§2.1) |
| `scratch/evidencia_escudo_baseline.txt` | ejecutado | Escudo completo en frío: `324 passed + 1 failed`, **30.75 s** |
| `scratch/evidencia_escudo_baseline_caliente.txt` | ejecutado | Escudo completo en caliente: `324 passed + 1 failed`, **15.58 s** |

Ninguna sonda escribe en `src/`, `scripts/` ni en la base de datos: todas son de **sólo lectura**
(salvo su propio stdout).

### 8.3 Manifiesto Git (cero commits)

```
 M docs/ARCH.md
 M docs/ID_REGISTRY.md
?? docs/DIRGEN_VARIANCE_REQUEST.md     <- ESTE PARTE
?? scratch/
?? scripts/ingesta/homologar_temporada_optah2h.py
?? tests/shield/test_shield_historical_homologation.py
```

*(`docs/ARCH.md` y `docs/ID_REGISTRY.md` figuran por la ordenación `[ARCH-1.4.39]` previa. No se ha
ejecutado ningún `git commit` ni `git add`.)*

### 8.4 Trazabilidad del bloqueo (por qué se detuvo la ejecución)

| Momento | Hecho | Acción del Constructor |
|---|---|---|
| Detección | Juez 2 en rojo con `p_visitante=0.0000` | Diagnóstico (sin editar producción) |
| Aislamiento | Corte real reconstruido y motor instanciado con el **perfil certificado del Juez 1** ⇒ pasa (0.6105) | Confirmar que el motor está sano ⇒ la falla es de **vector**, no de motor |
| Matriz | 12 configuraciones medidas | Identificar **una sola** corrección legal (xG sin xGA) |
| Alcance | Mapa de snapshots md1..md17 | Descubrir el **borrado sistemático** del contrato |
| Raíz | Lectura de `centinela_deportivo.py:697-705` | ⛔ **Componente `[DIRGEN-STRICT]` ⇒ Protocolo Anti-Bandazos: Alto al Fuego** |
| Determinación | La corrección legal restante depende de una **fuente** no ratificada (D-i/D-ii) | Emitir este parte y **esperar resolución** |

---

**ESTADO FINAL DEL PARTE:** 🔴 **ALTO AL FUEGO MANTENIDO.** Diagnóstico cerrado: dos causas raíz
verificadas, una única corrección legal identificada y medida (`p_visitante` 0.5102 ✓ / `p_local` 0.2387 ✓),
y una pregunta abierta a la Autoridad (ratificación de fuente D-i/D-ii) más un decreto pendiente (E4 sobre
componente `[DIRGEN-STRICT]`). **Ninguna constante, plano o algoritmo protegido fue modificado.**



### 8.5 Cierre de ejecución — Decreto `VAR-2026-J7-HOMOLOGACION` (Constructor)

> El estado anterior del parte (🔴 Alto al Fuego) quedó **resuelto por decreto de la Autoridad**. Esta
> sección es el registro factual de la ejecución de E1–E5, homologación J1..J9 y Bucle Reflexivo.

**Enmiendas entregadas**

| # | Entrega | Archivo | Evidencia |
|---|---|---|---|
| E1 | `xg` sin `xga` en bloques general y de sede | `scripts/ingesta/homologar_temporada_optah2h.py` | `docs/ARCH.md [ARCH-1.4.39]` §2 (Pilar 2: *xG, SoT, posesión*) |
| E2 | Endpoint vigente `/api/data/matches?date=` + rótulo/identidad por ID + ventana ±1 día | ídem | `scratch/evidencia_sensor_traza.txt` |
| E3 | Caché congelada `data/cache_optaxg_liga_mx_2026.json` (`--congelar-cache`) | artefacto nuevo | `scratch/evidencia_congelacion_v2.txt` |
| E4 | `fill-if-absent` de las 7 claves del contrato P′ (sólo con decreto) | `scripts/daemons/centinela_deportivo.py` | `CLAVES_CONTRATO_CAPTURA` (L53-56) + L712-718 |
| E5 | Reposición de contrato en la recaptura de temporada completa | `scripts/utilidades/poblar_temporada_completa_backtesting.py` | `git diff --stat` (+20/−5) |

**Hallazgo forense que refinó E2 (no estaba en el parte original)**

La traza del extractor (partido `1000014503`) probó que el payload **espeja el mismo disparo en 4 vistas**:
`content.shotmap.shots` (**26** nodos canónicos), `content.playerStats.<id>.shotmap` (25),
`content.matchFacts.*` (5) y `content.shotmap.Periods.*` (mitades). El recorrido previo recolectaba
**58 nodos** ⇒ xG hasta 3× inflado (magnitudes imposibles: 15.6 xG por equipo en un partido).
Criterio factual adoptado (`_explorar_disparos` + `_recolectar_disparos`): se recolecta el nivel de
**mínima profundidad** bajo la raíz (la vista de PARTIDO); las demás son vistas derivadas.
Además se prioriza la clave DOCUMENTADA `expectedGoals` sobre la coincidencia difusa (el nodo también
porta `expectedGoalsOnTarget`). Verificación: `_xg_por_lado` ⇒ `0.8561 / 1.2168`, idéntico al rótulo
oficial `Expected goals (xG)` = `0.86 / 1.22` y al sondeo D-ii ratificado (**12/12** correlaciones, Δ=0.0000).

**Resultados verificados**

| # | Criterio (DoD §7) | Comando | Resultado |
|---|---|---|---|
| 1 | Jueces de homologación | `pytest tests/shield/test_shield_historical_homologation.py -v` | **2 PASSED** (EXIT 0) |
| 2 | Escudo completo | `pytest tests/shield/ -q` | **325 passed · 0 failed** · EXIT 0 · 18.98 s (caliente) / 21.60 s (frío) — dentro del presupuesto 25.0 s / 21.0 s |
| 3 | Pre-vuelo de cartelera | `python -m scripts.auditoria.auditar_coherencia_cartelera --check --todo` | **EXIT 0**, 153 partidos, **cero** 🔴 |
| 4 | Homologación J1..J9 | `python -m scripts.ingesta.homologar_temporada_optah2h --jornadas 1-9` | 3NF 81/81 exitosos · capturas selladas 81 · **paridad idéntica 81/81** |
| 5 | Cobertura de la caché | `python scratch/probe_cache_congelada.py` | **79/81** con métrica; corte Puebla y Toluca J1..J6 **INTEGRO** (6/6 cada uno) |
| 6 | Bóveda J7 | `scratch/probe_j7_veredicto.py` | `Club Puebla vs Deportivo Toluca`: `p_local=0.2388` (≤0.30 ✓) · `p_visitante=0.5101` (≥0.50 ✓) en 3NF **y** en `fixtures_snapshots` |
| 7 | Manifiesto | `git status --porcelain` / `git diff --stat` | **cero commits** (sólo working tree) |

**Declaración de cobertura (sin silencio):** 2 de 81 candidatos de J1..J9 quedan sin métrica
(`LIGAMX-J7-08`, `LIGAMX-J7-09`) ⇒ la cadena degrada declaradamente al calibrado para esos dos
fixtures ajenos al corte del Juez 7 (`N-1 = J1..J6`), cuyo corte es **íntegro**.

**Régimen respetado:** `[DIRGEN-STRICT]` intocado (`src/core/`, `src/storage/`, motores estocásticos
y de persistencia: **cero diffs**); los cambios viven en `scripts/ingesta/` (BDDB), `scripts/daemons/`
(E4, autorizado por decreto) y `scripts/utilidades/` (E5). Presupuesto de Bucle Reflexivo:
**18.98 s ≤ 21.0 s (caliente) / 21.60 s ≤ 25.0 s (frío)** ✓.

### 8.6 Pasada de ratificación, poblar temporada y Manifiesto Master (Constructor — 2026-10-14)

> Cierre operativo de la Directiva Ejecutiva Final (Levantamiento del Alto al Fuego, enmiendas E1–E5 con
> fuente **D-ii**, Registro de Varianza, homologación histórica y Master Commit). Esta sección es el
> registro factual de la re-ejecución ordenada.

**8.6.1 Registro de Varianza (`docs/ID_REGISTRY.md`, tabla `VAR-...`):**

| Ficha | Colisión / Hallazgo | Resolución | Estado |
|---|---|---|---|
| `VAR-2026-COLD-START-PRIOR` | Juez 1 vacío por DTO sin S(I) y colisión de variables ql | Ratificada Opción A Holística: S(I)=0 en DTO, sustitución de P' por q_mkt pre-clasificación, rótulo visual COLD START | RATIFICADO |

**8.6.2 Enmiendas E1–E5 — coordenadas de la materialización verificadas en esta pasada:**

| # | Artefacto | Coordenadas | Evidencia de cumplimiento |
|---|---|---|---|
| E1 | `scripts/ingesta/homologar_temporada_optah2h.py` | `_bloque_general` L744-751 · `_bloque_sede_con_opta` L766-769 | Se publica **sólo** `bloque["xg"]`; `xga` jamás viaja en el vector homólogo (el plano sellado degrada por su ruta interna a GC) |
| E2 | ídem | L115-116 | Endpoints vivos `https://www.fotmob.com/api/data/matches?date={fecha}` + `/api/data/matchDetails?matchId=` |
| E3 | `data/cache_optaxg_liga_mx_2026.json` | artefacto congelado | 79 partidos con métrica · `fuente = sensor_fotmob_shotmap_optaxg · fuente D-ii ratificada` |
| E4 | `scripts/daemons/centinela_deportivo.py` | `CLAVES_CONTRATO_CAPTURA` L53-56 · reposición L716-718 | `fill-if-absent` por campo de las 7 claves ⇒ el daemon ya no destruye P′ en la recaptura de temporada completa |
| E5 | `scripts/utilidades/poblar_temporada_completa_backtesting.py` | `_sellar_p_prima_en_capturas` L421-444 | `fill-if-absent` **por campo** (no por fixture) + sello independiente de `suficiencia_S_I` |

**8.6.3 Homologación histórica** `python -m scripts.ingesta.homologar_temporada_optah2h --jornadas 1-9`
(pasada de ratificación; sensor de red OFF ⇒ corrida **hermética** sobre la caché congelada):

| Criterio | Resultado |
|---|---|
| Partidos consumados 3NF / fixtures homologados | 97 / **81** |
| Pilar 1 — splits de sede | **81/81** con `PJ_casa + PJ_gira ≡ PJ_corte` |
| Pilar 2 — procedencia Opta | nivel=`cache_local` · **79** con métrica · telemetría=0 · sensor=0 |
| Pilar 4 — 3NF `sovereign_distributions` | **81 procesados / 81 exitosos / 0 errores** |
| Pilar 4 — captura `fixtures_snapshots.matches_json` | P′ selladas=**0** preservadas=**81** · S(I) selladas=**0** preservadas=**81** ⇒ idempotencia (cero sobreescritura del contrato de 7 campos) |
| Paridad 3NF ↔ captura | idénticas=**81** · divergentes=**0** · ausentes=**0** |
| Bóveda J7 (`LIGAMX-J7-07`, Club Puebla vs Deportivo Toluca) | 3NF **y** captura idénticas y rectificadas: `p_local=0.2388` (≤0.30 ✓) · `p_visitante=0.5101` (≥0.50 ✓) · λ=1.0989/1.7099 · `phi_lead2_home=0.1438` · `S(I)=1` |

**8.6.4 Reporte del Alpha final global de la temporada (DoD §4)** — consulta de sólo lectura al endpoint
`GET /api/markets/backtesting/calibration-report?league_id=1` (bloque `resumen_temporada`, vía
`fastapi.testclient.TestClient`), medida antes y después de la pasada de ratificación:

| Métrica | Antes de la pasada | Después de la pasada |
|---|---|---|
| Partidos evaluados | 97 | 97 |
| Favorito / Empate / Underdog | 41 / 26 / 30 | 41 / 26 / 30 |
| Tasa de Coincidencia Fiduciaria (H_fid) | 69.07 % | 69.07 % |
| BS_QBE / BS_mercado | 0.2169 / 0.2145 | 0.2169 / 0.2145 |
| **Alpha de Calibración** | **−1.12 %** | **−1.12 %** |
| Partidos en Cold Start `S(I)=0` | 27 (J1: 9 · J2: 9 · J3: 9) | 27 (J1: 9 · J2: 9 · J3: 9) |
| Partidos pendientes de captura | 0 | 0 |

La igualdad bit-a-bit de ambos censos certifica la **idempotencia** de la homologación: la bóveda ya
portaba el corte homologado y ninguna re-escritura movió una sola cifra (`P′ selladas=0`). El Alpha
global permanece negativo (−1.12 %) por diseño del axioma `[LN-QBE-100]`: los 27 partidos de Cold Start
aportan exactamente `BS_QBE ≡ BS_mercado` (Alpha ≡ 0.00 % por identidad de vectores), de modo que la
métrica mide la ventaja estocástica **sólo donde el modelo operó con evidencia**.

**8.6.5 Bucle Reflexivo (Definition of Done):**

| # | Criterio | Comando | Resultado |
|---|---|---|---|
| 1 | Jueces de homologación | `pytest tests/shield/test_shield_historical_homologation.py -v` | **2 PASSED** (EXIT 0) |
| 2 | Escudo completo | `pytest tests/shield/ -q` | **326 passed · 0 failed** · EXIT 0 · 15.05 s y 15.18 s (caliente, dos corridas) / 25.61 s (frío) |
| 3 | Pre-vuelo de cartelera | `python -m scripts.auditoria.auditar_coherencia_cartelera --check [--todo]` | **EXIT 0** en ambas modalidades · 153 partidos · **cero 🔴** |
| 4 | Alpha final de temporada | endpoint de calibración (§8.6.4) | **−1.12 %** |
| 5 | Manifiesto Master | `git status --porcelain` · `git rev-parse HEAD` | **cero commits** (HEAD `52a3e9e` inmóvil) |

**Desviación declarada (honestidad de cobertura `[GOVERNANCE-01]`):** la corrida **en frío** del Escudo
midió **25.61 s**, esto es **+0.61 s (+2.4 %)** sobre el presupuesto armonizado de 25.0 s; la corrida
inmediata siguiente, en caliente, midió **15.05 s** (−5.95 s bajo el presupuesto de 21.0 s). El costo
dominante sigue siendo el import/colección de la suite (Pydantic V2 + Playwright), no la ejecución de los
jueces, y la lectura en frío se tomó inmediatamente después del re-sellado masivo de 97 distribuciones
soberanas (caché de páginas de SQLite fría). **Cero jueces fallaron y ninguna constante protegida fue
tocada** ⇒ no procede abrir palanca de gobernanza por una desviación informativa de SLA.



