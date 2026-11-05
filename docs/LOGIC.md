# Q-BE ECOSYSTEM — LOGIC BOOK

**Versión:** 2.0 — 32V / Four-Pillar Edition  
**Estado:** `[ALGO-PROTECTED]` — Lógica Invariante Certificada  
**Proyecto:** `Q_BE_ECOSYSTEM`  
**Autoridad Suprema:** Américo García Guerrero (Director Humano)  
**Marco:** Kybern Industrial Framework v13.5  
**Expediente:** `SPRINT-FASE4-MIGRACION-REFLEXIVA-BG-04`  
**Fecha:** 2026-10-28  
**Sustituye a:** `Q_BE_CD_WEB/docs/LOGIC.md` (régimen 44V `[DEROGADO]`)

> **Aviso de procedencia.** El `LOGIC.md` legado conservaba la historia del régimen 44V y una topología de monolito. Este libro declara vigente el catálogo de **32 variables / 6 dimensiones** (`[LN-QBE-120]`), reancla los nodos a los cuatro pilares y conserva la memoria de las derogaciones como tombstone. La aritmética no cambia: cambia el anclaje institucional.

---

## 1. FORMALISMO DEL GRAFO IPO

El pipeline se modela como un dígrafo acíclico dirigido:

```text
G = (V, E)
V = { N_i }
N_i = <ID, Ω, I, P, O, Φ>
```

| Símbolo | Significado |
|---|---|
| `ID` | Identificador canónico inmutable (`[LN-QBE-XXX]`). |
| `Ω` | Resumen y propósito fiduciario del nodo. |
| `I` | Input: contrato de entrada y procedencia. |
| `P` | Process: transformación determinista. |
| `O` | Output: contrato de salida. |
| `Φ` | Transición: nodos sucesores y consumidores. |

**Invariante:** ningún nodo de `qbe_core` realiza I/O. La evidencia entra como dato; la salida es un valor, una distribución o un veredicto.

---

## 2. CATÁLOGO VIGENTE DE 32 VARIABLES — `[LN-QBE-120]`

El catálogo se organiza en **6 dimensiones** y **32 variables correlativas**. La reingeniería renumera, no reinterpreta: cada magnitud conserva su semántica y su espacio de Hilbert (`H_att`, `H_def`, `H_ctx`). El DTO conserva el nombre histórico `variables_44` por compatibilidad de red; su cardinalidad real es 32.

| Dimensión | Variables | N | Propósito |
|---|---|---:|---|
| `𝒯_Vol` — Volumen Territorial y Fricción | `V01`–`V05` | 5 | Posesión, toques en área, pases, faltas. |
| `𝒯_Rem` — Calidad de Remate | `V06`–`V11` | 6 | xG, SoT, big chances, xGOT, xA. |
| `𝒯_Def` — Resistencia Defensiva | `V12`–`V16` | 5 | xGA, SoTA, acciones defensivas, intercepciones, big chances concedidas. |
| `𝒯_Por` — Rendimiento de Portería | `V17`–`V20` | 4 | Goles evitados, save %, salidas, clean sheets. |
| `𝒯_Spc` — Balón Parado y Disciplina | `V21`–`V25` | 5 | Pelota parada, córners, penales, tarjetas. |
| `𝒯_Ctx` — Memoria, Forma y Contexto | `V26`–`V32` | 7 | H2H, sede, altitud, descanso, forma, ΔxPTS. |

### 2.1 Tabla canónica

| ID | Variable | Dimensión | Fuente | Espacio |
|---|---|---|---|---|
| `V01` | Posesión promedio (%) | `𝒯_Vol` | OPTA | `H_att` |
| `V02` | Toques en área rival | `𝒯_Vol` | OPTA | `H_att` |
| `V03` | Pases precisos | `𝒯_Vol` | OPTA | `H_att` |
| `V04` | Pases largos precisos | `𝒯_Vol` | OPTA | `H_att` |
| `V05` | Faltas cometidas | `𝒯_Vol` | OPTA | `H_att` |
| `V06` | xG por partido (ancla npxG) | `𝒯_Rem` | OPTA | `H_att` |
| `V07` | Tiros al arco por partido (SoT) | `𝒯_Rem` | OPTA | `H_att` |
| `V08` | Big chances creadas | `𝒯_Rem` | OPTA | `H_att` |
| `V09` | Big chances falladas | `𝒯_Rem` | OPTA | `H_att` |
| `V10` | xGOT de plantilla | `𝒯_Rem` | OPTA | `H_att` |
| `V11` | xA de plantilla | `𝒯_Rem` | OPTA | `H_att` |
| `V12` | xGA por partido (ancla defensiva) | `𝒯_Def` | OPTA | `H_def` |
| `V13` | Tiros al arco recibidos (SoTA) | `𝒯_Def` | OPTA | `H_def` |
| `V14` | Acciones defensivas por partido | `𝒯_Def` | OPTA | `H_def` |
| `V15` | Intercepciones por partido | `𝒯_Def` | OPTA | `H_def` |
| `V16` | Big chances concedidas | `𝒯_Def` | `FUERA DE FUENTE` | `H_def` |
| `V17` | Goles evitados | `𝒯_Por` | OPTA | `H_def` |
| `V18` | Save % (atajadas) | `𝒯_Por` | OPTA | `H_def` |
| `V19` | Salidas / líbero por partido | `𝒯_Por` | OPTA | `H_def` |
| `V20` | Clean sheets | `𝒯_Por` | OPTA | `H_def` |
| `V21` | Goles a favor de pelota parada | `𝒯_Spc` | OPTA | `H_att` |
| `V22` | Goles recibidos de pelota parada | `𝒯_Spc` | OPTA | `H_def` |
| `V23` | Córners por partido | `𝒯_Spc` | OPTA | `H_att` |
| `V24` | Penales favor/contra | `𝒯_Spc` | OPTA | `H_att` |
| `V25` | Tarjetas amarillas/rojas | `𝒯_Spc` | OPTA | `H_ctx` |
| `V26` | Récord H2H | `𝒯_Ctx` | Q-BE | `H_ctx` |
| `V27` | ΔG H2H (diferencial de goles) | `𝒯_Ctx` | Q-BE | `H_ctx` |
| `V28` | Récord visitante en sede | `𝒯_Ctx` | Q-BE | `H_ctx` |
| `V29` | Altitud ΔAlt+ (factor fisiológico) | `𝒯_Ctx` | FIXTURE | `H_ctx` |
| `V30` | Días de descanso (ΔDías) | `𝒯_Ctx` | FIXTURE | `H_ctx` |
| `V31` | Forma 5P (puntos recientes) | `𝒯_Ctx` | Q-BE | `H_ctx` |
| `V32` | Varianza ΔxPTS | `𝒯_Ctx` | Q-BE | `H_ctx` |

### 2.2 Reglas del catálogo

1. **Cero duplicados:** cada `V##` pertenece a exactamente una dimensión.
2. **Cero invención:** `V16` se conserva en su fila, pero se declara `FUERA DE FUENTE`; no se imputa ni se muestra como `0.00`.
3. **Cero rename de red:** `variables_44` y `Catalogo44Out` sobreviven como nombres de contrato; la UI lee `n/m` del DTO, no de una constante local.
4. **Cero re-derivación en el cliente:** el frontend transcribe; no calcula λ, probabilidades, Δ logarítmicas ni récords.

---

## 3. LAS NUEVE ESTRATEGIAS CANÓNICAS

| Código | Nombre | Familia | Rol |
|---|---|---|---|
| `QBE-D1` | Favorito Directo Puro | D | Victoria directa sin cobertura. |
| `QBE-D1+` | Favorito Directo Potenciado | D | Victoria con pago anticipado. |
| `QBE-H1` | Favorito con Seguro en Empate | H | Favorito + recuperación en tablas. |
| `QBE-H1+` | Favorito Potenciado con Seguro | H | Favorito + pago anticipado + seguro. |
| `QBE-H2` | Favorito Visitante con Cobertura en Tablas | H | Visitante + seguro V=0. |
| `QBE-H2+` | Freeroll Doble Impacto | H | Visitante + seguro + pago anticipado. |
| `QBE-R1` | Asalto al No-Favorito con Seguro | R | Underdog + seguro en tablas. |
| `QBE-R2` | Doble Oportunidad Sintética X2 | R | Dutching empate + underdog. |
| `QBE-00` | Veto Preventivo de Capital | VETO | Descarte total; capital en riesgo $0.00. |

`QBE-MOONSHOT` es satélite asimétrico, no una décima estrategia de la cascada principal.

---

## 4. LEY 3 — COTA UNDERDOG

**Nodo dueño:** `[LN-QBE-115]`  
**Constante:** `CAP_UNDERDOG_LEY3_PCT = 0.0150`  
**Alcance:** exclusivamente `QBE-R1` y `QBE-R2`.

$$ \text{Cap}_{\text{underdog}} = 0.0150 \cdot B_j $$

Reglas:

1. La cota se aplica **antes** del prorrateo global y después de la asignación monótona.
2. Es un **techo, jamás un piso**: no rescata una orden sub-dimensionada ni infla la bolsa del 25%.
3. No sustituye el hard-cap individual del 8% ni el cap de cartera del 25%.
4. No se aplica a `QBE-D*`, `QBE-H*` ni `QBE-MOONSHOT`.

---

## 5. ESCUDO DE ALTITUD

**Nodo dueño:** `[LN-QBE-115]`  
**Constante:** `UMBRAL_VETO_ALTITUD_METROS = 1000.0`  
**Alcance:** rama `ASIMETRIA_VISITANTE` / `QBE-H2`.

$$ \Delta\text{Alt}^{+} = \max\left(0,\; \text{Altitud}_{\text{local}} - \text{Altitud}_{\text{visita}}\right) $$

Si $\Delta\text{Alt}^{+} \ge 1000$ m y $O_X > \theta_2^*$, la orden `QBE-H2` se veta y colapsa a `QBE-00` con motivo de trampa de altitud visitante. El escudo tiene **precedencia estructural** sobre la cota de dominancia `[LN-QBE-116]`.

### 5.1 Catálogo canónico de altitudes

| Sede / club | Altitud (msnm) |
|---|---:|
| `deportivo-toluca` | 2,660 |
| `pachuca` | 2,400 |
| `club-america` | 2,240 |
| `cruz-azul` | 2,240 |
| `pumas-unam` | 2,240 |
| `atlante` / `club-atlante` | **2,240** |
| `club-puebla` | 2,135 |
| `club-necaxa` | 1,880 |
| `atletico-san-luis` | 1,860 |
| `queretaro-fc` | 1,820 |
| `club-leon` | 1,815 |
| `chivas-guadalajara` | 1,560 |
| `atlas-fc` | 1,560 |
| `fc-juarez` | 1,120 |
| `santos-laguna` | 1,120 |
| `tigres-uanl` | 540 |
| `rayados-de-monterrey` | 540 |
| `club-tijuana` | 30 |
| `mazatlan-fc` | 10 |

**Hecho certificado:** Atlante opera a 2,240 msnm; el diferencial con Rayados (540) es 1,700 m y activa el escudo. El valor es un hecho declarado, no una estimación.

---

## 6. BANDA DE INDIFERENCIA

**Nodo dueño:** `[LN-QBE-124]`  
**Constantes:** `BANDA_INDIFERENCIA_EPSILON = 0.0100` ($\varepsilon = 1.00\%$, es decir, 1.00%) y `UMBRAL_ALTITUD_RESCATE_METROS = 1000.0`.

La jerarquía $P_{\max} \ge P_{\text{mid}} \ge P_{\text{low}}$ no debe tratar como separación epistémica lo que es ruido de régimen. Si dos vértices están dentro de la banda, el desempate no se inventa: se aplica el orden canónico y, si concurren las tres condiciones, se promueve el LOCAL.

Condiciones conjuntivas de rescate:

1. $|P_{\text{mid}} - P_{\text{low}}| \le 0.0100$;
2. el par en disputa es exactamente `{LOCAL, EMPATE}`;
3. $\Delta\text{Alt}^{+} \ge 1000$ m.

Verificadas las tres, `LOCAL` asciende a `P_mid` y `EMPATE` desciende a `P_low`. El rescate no mueve una décima de $P_{\max}$ ni altera λ.

**Prohibición:** no confundir `UMBRAL_VETO_ALTITUD_METROS` (escudo que veta `QBE-H2`) con `UMBRAL_ALTITUD_RESCATE_METROS` (desempate ordinal). Son predicados distintos y no se mutan entre sí.

---

## 7. NÚCLEO MATEMÁTICO

### 7.1 Poisson bivariado y Dixon-Coles

`[LN-QBE-040]` construye la matriz 6×6 de marcadores con intensidades λ calibradas por Opta xG. `[LN-QBE-040-B]` impone el techo conjunto anti-resonancia en espacio logarítmico; `[LN-QBE-040-C]` gobierna la correlación táctica $\rho$ en partidos de baja anotación.

### 7.2 Ecuación log-lineal

`[VAULT-CORE-001]` estima intensidades con ligadura estructural de α. La ventaja territorial se descompone en:

$$ \gamma_{\text{efectivo}} = \bar{\gamma}_{\text{base}} + \Delta\gamma_{\text{plaza}} + \beta_{\text{alt}}\cdot\frac{\Delta\text{alt}}{1000} + \beta_{\text{rest}}\cdot\text{clip}(\Delta\text{días},-3,3) $$

con $\bar{\gamma}_{\text{base}} = 0.15$, $\kappa_{\text{net}} = 0.25$ como techo de compresión $\tanh$, $\beta_{\text{alt}} = 0.0300$ y $\beta_{\text{rest}} = 0.0200$ (`CONSTANTS.md` §2).

### 7.2-bis Súper-Señal V6 y Sistema Inmune Fiduciario (`E-50.9` / `E-50.10`, Fase 6)

**Capa 1 · Súper-Señal.** `derivar_factores_super_senal` (`qbe_core/src/core/sovereign_pipeline.py`) deriva los factores exclusivamente de `V06` (xG), `V07` (SoT) y `V12` (xGA), **sin GSL-3D** y con la ligadura α **fija** en el punto canónico $\alpha = \ln(2.65) - \ln(1+e^{0.15}) = 0.203603$ (prohibido inyectar plaza/altitud/descanso en α):

$$ xg_n = \frac{V06+1}{\mu_{xG}+1},\quad sot_n = \frac{V07+1}{\mu_{SoT}+1},\quad xga_n = \frac{V12+1}{\mu_{xGA}+1} $$
$$ A = \ln(0.65\,xg_n + 0.35\,sot_n),\qquad D = -\ln(xga_n) $$

**Capa 2 · Barrido de κ.** `estimar_intensidades_loglineal` acepta `kappa_net` variable; el laboratorio busca $\kappa^* \in [0.35, 0.55]$.

**Capa 4 · Sistema Inmune Fiduciario.** `veto_inmunidad_fiduciaria` (`qbe_core/src/core/triage.py`) emite `QBE-00` sobre las variables residuales:

| Regla | Condición | Arquetipo |
|---|---|---|
| R1 · Ineficiencia Ofensiva | `V06 ≥ p75` ∧ `V09 ≥ p90` ∧ `V25 ≥ p75` | `INEFICACIA_OFENSIVA` |
| R2 · Sobreasedio Defensivo | `V13 ≥ p90` ∧ `V31 ≤ p25` | `SOBREASEDIO_DEFENSIVO` |

Los percentiles (p25/p75/p90) los calcula el laboratorio sobre la muestra histórica; `triage.py` no aloja números mágicos locales.


**Clausura de masa (Invariante L-1, enmienda `E-50.1`).** α se calcula sobre $\gamma_{\text{efectivo}}$ **completo**, no sobre la base:

$$ \alpha = \ln(\mu_{\text{liga}}) - \ln\!\left(1 + e^{\gamma_{\text{efectivo}}}\right) \;\Longrightarrow\; \lambda_H + \lambda_A = \mu_{\text{liga}} \text{ con } A=D=0,\ q=1 $$

Prohibido añadir un término a `eta_h` sin incorporarlo a la ligadura. El canon anterior dejaba fuera `Δalt` y `Δrest` y fugaba masa (2.6500 → 2.6934 con +1000 m; 2.7609 con +2500 m).

**Cero mocks (P-01/P-02).** Prohibido `dict.get(clave, <literal>)`, `clave or <literal>` y todo `except` que devuelva un número. La ausencia de evidencia estadística (`gf`, `gc`, `xg`, `xga`, `V01…V32`) se resuelve con `InsufficientDataException` o `S(I)=0`, nunca con `10`, `12`, `7` u `8`. Los operadores contextuales (`Δalt`, `Δrest`, `q_mod`) no se sustituyen por `0.0`: se declaran **no aplicados**.

### 7.3 Breakeven dinámico

$$ \theta^* = \frac{O_{\text{fav}}}{O_{\text{fav}} - 1} $$

es el umbral de indiferencia de cobertura. No es una constante universal: depende del momio del favorito y del régimen de pago anticipado.

### 7.4 Morfología del símplex

`[LN-QBE-059]` particiona $\Delta^2$ en ocho familias morfológicas con umbral maestro $\Gamma_{\text{base}} = 0.67$. Los umbrales `0.70` y `0.75` son modos de UI, no constantes del motor.

### 7.5 Kelly y hard-caps

`[LN-QBE-070]` aplica Kelly fraccional atenuado (`0.25`), hard-cap individual (`0.08`), cap de cartera (`0.25`) y piso de ventanilla (`$2.00`). La cota underdog del 1.5% es un techo adicional de la Familia R.

### 7.6 GSL-3D v2 — Proyección ortogonal real sobre las 32 variables (`[LN-QBE-039]`)

**Déficit derogado.** El motor v13.0 consume 4 celdas del catálogo (V06, V12, V29, V30) más `gf`/`gc`, suma el resto de forma plana en `eta` y denomina «ortogonalización» a un residuo escalar de sede aplicado únicamente al club local. Consecuencia: `xG` (V06), `SoT` (V07) y grandes ocasiones (V08) nunca coinciden en la ecuación, de modo que su colinealidad no se purga porque no llega a existir.

**7.6.1 · Contrato de entrada (IPO v2).** La ortogonalización es un operador sobre **variables**, no sobre escalares: exige la matriz causal del club $M \in \mathbb{R}^{n\times 32}$ ($n \ge 10$ partidos pre-kickoff, sin fuga temporal) más el vector del fixture $z \in \mathbb{R}^{32}$. Un agregado escalar por lado **no admite** proyección ortogonal; presentarlo como tal es simulación de ortogonalidad. Sin $M$ ⇒ `S(I)=0` con motivo `MATRIZ_CAUSAL_AUSENTE`.

**7.6.2 · Partición en los tres espacios de Hilbert.** Cada celda porta espacio y signo $\sigma_i \in \{+1,-1\}$ (más = mejor en su eje):

| Espacio | Variables ($\sigma$) | $n$ |
|---|---|:---:|
| $\mathbb{H}_{\text{att}}$ | V01(+), V02(+), V03(+), V04(+), V05(−), V06(+), V07(+), V08(+), V09(−), V10(+), V11(+), V21(+), V23(+), V24(+) | 14 |
| $\mathbb{H}_{\text{def}}$ | V12(−), V13(−), V14(+), V15(+), V16(−), V17(+), V18(+), V19(+), V20(+), V22(−) | 10 |
| $\mathbb{H}_{\text{ctx}}$ | V25(−), V26(+), V27(+), V28(+), V31(+), V32(−) | 6 |
| Clausura $\gamma$ | V29, V30 — **excluidas de $C^*$**: ya viven en $\gamma_{\text{efectivo}}$ | 2 |

Cobertura 32/32: 30 variables entran a la proyección y 2 a la ligadura. **Prohibido el doble conteo** de V29/V30.

**7.6.3 · Normalización obligatoria.** Sumar porcentajes con conteos y con xG produce una base arbitraria: sin normalizar no hay ortogonalización válida. Regla única, log-diferencial contra la referencia de liga por temporada $(\mu_i)$ sellada en el libro de medias:

$$ z_i = \ln\!\left(\frac{v_i + \varepsilon}{\mu_i + \varepsilon}\right),\qquad \varepsilon = 0.5 $$

Si $\mu_i$ no está sellada para la temporada, la variable se declara `SIN_EVIDENCIA`. **Prohibido** normalizar contra la media de la propia muestra (fuga de información).

**7.6.4 · Orquestación (Gram-Schmidt modificado).** Orden determinista `V##` ascendente sobre el subconjunto evidenciado; $q_1 = z_1/\lVert z_1\rVert$; residuo $r_i = z_i - \sum_{j<i}(z_i^{\top}q_j)\,q_j$. Si $\lVert r_i\rVert_2 < \varepsilon_{\text{ort}} = 10^{-5}$, la variable es **colineal**: aporta exactamente $0$, se declara junto a su pivote y no se descarta en silencio. La colinealidad deja de inflar $\lambda$ porque una dirección duplicada no aporta dirección nueva.

**7.6.5 · Síntesis acotada.** Con $Q$ la base ortonormal y $\beta = Q^{\top}z$:

$$ A^* = \tanh\!\left(\frac{1}{\sqrt{n_A}}\sum_j \sigma_j\beta_j\right),\ \lvert A^*\rvert \le 1.0;\quad D^* = \tanh\!\left(\frac{1}{\sqrt{n_D}}\sum_j \sigma_j\beta_j\right),\ \lvert D^*\rvert \le 1.0;\quad C^* = \tanh\!\left(\frac{1}{\sqrt{n_C}}\sum_j \sigma_j\beta_j\right),\ \lvert C^*\rvert \le 0.25 $$

El promedio por $\sqrt{n}$ (RMS) impide que añadir variables infle el factor: dos variables colineales producen el mismo $A^*$ que una sola.

**7.6.6 · Cobertura, suficiencia y declaración.** Toda variable publica estado ∈ {`CONSUMIDA`, `COLINEAL`, `SIN_EVIDENCIA`} y el motor publica `cobertura_variables = k/32`. Suficiencia: $n_A \ge 2 \wedge n_D \ge 2$ evidenciadas no colineales; en caso contrario `S(I)=0`. **La ley no autoriza a ignorar una variable: autoriza a declararla ausente.** Las 23 celdas `SIN EVIDENCIA` del corpus vigente quedan cableadas al contrato y excluidas del álgebra con declaración; su poblamiento es deuda de ingesta, no del motor.

### 7.7 Ley única del peso H2H (`[LN-QBE-020-B]`)

**Duplicidad derogada.** Coexistían $w=\max(0.15,\ 0.50\,e^{-\kappa_{180}\Delta t})$ (`CONSTANTS.md` §1, `[LN-QBE-040]`) y $w=\min(0.25,\ 0.05N)$ (`[LN-QBE-104]`). No son intercambiables porque **el decaimiento ya se aplica dentro del kernel, enfrentamiento por enfrentamiento** (`[LN-QBE-020-C]`, $\tau_{\text{deep}} = 540$ d): aplicarlo otra vez al peso descuenta dos veces la misma antigüedad.

**Regla de propiedad única:**

| Objeto | Ley | Dueño |
|---|---|---|
| Peso de la fusión convexa del símplex soberano | $w_{H2H}=0$ si $N=0$; $\min(0.25,\ 0.05N)$ si $N\ge 1$ — **sin decaimiento** | `[LN-QBE-104]` bajo `[LN-QBE-020-B]` |
| Modulación H2H de $\lambda$ en el motor legado (sin kernel) | $\max(0.15,\ 0.50\,e^{-\kappa_{180}\Delta t})$ | `[LN-QBE-040]` |
| Ponderación por enfrentamiento dentro del kernel | $e^{-\kappa_{540}\Delta t_k}$ | `[LN-QBE-020-C]` |

**Prohibiciones:** (i) aplicar decaimiento al peso de fusión; (ii) usar la amplitud `0.50` como techo de la fusión (su techo es `0.25`); (iii) invocar el kernel con $N=0$ (Ley Zero-H2H `[LN-QBE-020-B]`). $N$ cuenta sólo duelos verificables dentro de $\tau_{\text{deep}}$.

---

## 8. DEROGACIONES Y TOMBSTONES

| Elemento | Estado | Vigente |
|---|---|---|
| Catálogo 12 dimensiones × 44 variables (`[LN-QBE-101]`) | `[DEROGADO]` | 6 × 32 (`[LN-QBE-120]`). |
| `V39`, `V40`, `V41` | `[DEROGADO]` | `V26`, `V27`, `V28`. |
| `𝒯_Shk`, `𝒯_H2H`, `𝒯_Tra` como familias separadas | `[DEROGADO]` | Consolidadas en `𝒯_Ctx`. |
| Semáforo `EPIST` en el micro-HUD | `[DEROGADO]` visualmente | Backend lo conserva; UI muestra tetralogía fáctica. |
| Lectura del visor sobre la base viva | `[DEROGADO]` | Snapshot atómico de solo lectura. |
| Ligadura α calculada sobre $\bar\gamma_{\text{base}}$ (sin `Δalt`/`Δrest`) | `[DEROGADO]` — `E-50.1` | Clausura sobre $\gamma_{\text{efectivo}}$ (§7.2, Invariante L-1). |
| `dict.get("gf", 10)` y todo default literal de evidencia | `[DEROGADO]` — `P-01` | `InsufficientDataException` o `S(I)=0` (§7.2). |
| Residuo escalar de sede presentado como «GSL-3D» | `[DEROGADO]` | Proyección ortogonal real sobre 32 variables (§7.6). |
| Peso H2H con decaimiento aplicado a la fusión del símplex | `[DEROGADO]` | Decaimiento sólo dentro del kernel; fusión por $N$ (§7.7). |
| Amplitud `0.50` como techo de la fusión soberana | `[DEROGADO]` | Techo fiduciario `0.25` (`[LN-QBE-104]`, §7.7). |

---

## 9. PROCEDENCIA Y LÍMITES

- **Cero datos sintéticos:** un insumo ausente se marca `SIN EVIDENCIA`, se cuarentena o se veta.
- **Futuro-ceguera:** el corte N−1 no consume el fixture evaluado.
- **Trazabilidad:** cada celda publica origen, estado e impacto.
- **No re-derivación:** el cliente transcribe; el motor calcula.

---

## 10. ÍNDICE DE NODOS LÓGICOS

| ID | Nodo / Título | Capa | Estado |
|---|:---:|---|:---:|
| `[LN-QBE-002]` | Deprecación de Inferencia de Bajas y Anclaje Fáctico Estructurado | `motor` | SELLADO |
| `[LN-QBE-003]` | Ingesta Fáctica Estructurada FotMob (Opta Metrics Engine) | `ingesta` | SELLADO |
| `[LN-QBE-005]` | Triaje Determinista de Cuotas 1X2 | `motor` | SELLADO |
| `[LN-QBE-006]` | Asignación Relacional de Favorito por Momio 1X2 | `motor` | SELLADO |
| `[LN-QBE-007]` | Ingesta Fáctica y Normalización Multi-Operador (Caliente & Betway) | `ingesta` | SELLADO |
| `[LN-QBE-007-B]` | Normalización de Momios Americanos a Decimales | `motor` | SELLADO |
| `[LN-QBE-007-C]` | Descuento de Margen Comercial (Vig-Free De-biasing al Símplex Δ²) | `motor` | SELLADO |
| `[LN-QBE-007-D]` | Detector de Arbitraje Inter-Casas (Cross-Market Surebet) | `motor` | SELLADO |
| `[LN-QBE-007-E]` | Consenso de Mercado y Diferenciales vs. Distribución Soberana | `ingesta` | SELLADO |
| `[LN-QBE-007-F]` | Lista Negra de Tokens de Navegación e Interfaz en Scraping (UI_BLACKLIST) | `ingesta` | SELLADO |
| `[LN-QBE-007-G]` | Normalización y Limpieza de Nombres de Clubes de Betway | `ingesta` | SELLADO |
| `[LN-QBE-007-H]` | Cotas de Admisibilidad de Cuotas y Overround en Betway | `ingesta` | SELLADO |
| `[LN-QBE-007-I]` | Validación de Suma de Inversas en Caliente | `ingesta` | SELLADO |
| `[LN-QBE-007-J]` | Prior de Ignorancia Fiduciaria ante Ausencia de Distribución Soberana | `motor` | SELLADO |
| `[LN-QBE-010]` | Aduana de Sanidad, Integridad y Anclaje a Tabla Maestra | `observatorio` | SELLADO |
| `[LN-QBE-011]` | Cálculo del Momio Justo (Fair Odds Q-BE) | `motor` | SELLADO |
| `[LN-QBE-012]` | Normalizador Canónico de Clubes y Cuotas | `ingesta` | SELLADO |
| `[LN-QBE-013]` | Sintetizador de Metadatos, Cronometría Dinámica y Ventanas Reprogramadas | `motor` | SELLADO |
| `[LN-QBE-014]` | Narrativa Híbrida Asistida (Tesis Q-BE en 4 Bullets) | `motor` | SELLADO |
| `[LN-QBE-015]` | Curador Agéntico de Catálogos y Bóveda de Activos | `motor` | SELLADO |
| `[LN-QBE-017]` | Ingesta Fáctica Soberana de la Tabla General (Liga MX / FMF Engine) | `ingesta` | SELLADO |
| `[LN-QBE-018]` | Extractor Universal de Marcadores y Partidos Reprogramados | `motor` | SELLADO |
| `[LN-QBE-019]` | Resolutor Canónico de Escudos y Activos Visuales | `ingesta` | SELLADO |
| `[LN-QBE-020]` | Operador de Decaimiento Temporal en H2H ($\kappa$-Decay) | `motor` | SELLADO |
| `[LN-QBE-020-B]` | Ley de Ponderación Zero-H2H (Cero Mocks Sintéticos) | `motor` | SELLADO |
| `[LN-QBE-020-C]` | Kernel H2H Empírico en Eje Localía (Generador C) | `motor` | SELLADO |
| `[LN-QBE-021]` | Generador de Traza de Auditoría Cuantitativa Markdown | `ingesta` | SELLADO |
| `[LN-QBE-022]` | Auditor Paralelo Independiente CLI (The Shield Parallel Auditor) | `motor` | SELLADO |
| `[LN-QBE-025]` | Conmutador de Slates y Preservación de Estado Inter-Jornadas | `observatorio` | SELLADO |
| `[LN-QBE-025-B]` | Conmutador de Slates, Cartera Vacía y Liquidación Real (Backtesting Fiduciario) | `observatorio` | SELLADO |
| `[LN-QBE-030]` | Métricas Sintéticas de Control y Peligro ($FCF, E_{\text{att}}$) | `motor` | SELLADO |
| `[LN-QBE-035]` | Fórmulas de Derivación Opta y Tokens de Marcador | `observatorio` | SELLADO |
| `[LN-QBE-035-B]` | Registro Modular de Variables y Suficiencia Fáctica S(I) | `observatorio` | SELLADO |
| `[LN-QBE-036]` | Operador de Contracción Bayesiana de Forma Reciente (10 Partidos) | `motor` | SELLADO |
| `[LN-QBE-037]` | Algoritmo de Detección de Sesgo Popular en Quinielas Progol | `ingesta` | SELLADO |
| `[LN-QBE-038]` | Modelo de Desempeño Específico de Sede (Home/Away Splits) y Fortaleza de Plaza | `motor` | SELLADO |
| `[LN-QBE-039]` | Motor de Ortogonalización Residual y Factores Latentes Tridimensionales (GSL-3D) | `observatorio` | SELLADO |
| `[LN-QBE-040]` | Matriz Poisson Bivariada (6x6) con Calibración Opta xG | `observatorio` | SELLADO |
| `[LN-QBE-040-B]` | Techo Conjunto de Intensidad Ofensiva en Espacio Logarítmico (Anti-Resonancia) | `motor` | SELLADO |
| `[LN-QBE-040-C]` | Parámetro de Correlación Táctica Bivariada ($\rho$) en Partidos de Baja Anotación | `motor` | SELLADO |
| `[LN-QBE-050]` | Ecuaciones de Breakeven Dinámico Continuo ($\theta^*$) | `motor` | SELLADO |
| `[LN-QBE-059]` | Partición Canónica del 2-Símplex Δ² sobre P' y Concentración Dinámica Γ [ARCH-PILLAR] | `motor` | SELLADO |
| `[LN-QBE-060]` | Evaluador Determinista del Catálogo y Triple Candado Fáctico | `motor` | SELLADO |
| `[LN-QBE-060-B]` | Partición Exhaustiva de las 9 Estrategias Canónicas y Cascada de Triaje | `motor` | SELLADO |
| `[LN-QBE-060-C]` | Filtro de Veto Fiduciario Inteligente Anti-Ruptura (QBE-00) | `motor` | SELLADO |
| `[LN-QBE-060-R]` | NOTA FORMAL DE DEROGACIÓN — Sueño Profundo de la Familia R (R1 y R2) [GOVERNANCE] | `motor` | SELLADO |
| `[LN-QBE-060-R-AWAKEN]` | Las Cuatro Leyes de Hierro del Underdog (Familia R) | `motor` | SELLADO |
| `[LN-QBE-065]` | Filtro de Descarte Temprano de Ineficiencia (+EV Gate) | `motor` | SELLADO |
| `[LN-QBE-070]` | Router de Utilidad Pura, Kelly y Techo Aritmético | `motor` | SELLADO |
| `[LN-QBE-070-B]` | Asignación con Kelly Fraccional Atenuado y Hard-Caps Constitucionales | `motor` | SELLADO |
| `[LN-QBE-070-C]` | Contrato Extendido de Partidos Candidatos (CandidateMatchPayload) | `observatorio` | SELLADO |
| `[LN-QBE-070-D]` | Orquestación Analítica de Cartera en build_plan() | `motor` | SELLADO |
| `[LN-QBE-070-E]` | Prorrateo Resiliente de Hard-Caps con Respeto al Piso de Ventanilla | `motor` | SELLADO |
| `[LN-QBE-071]` | Algoritmo de Escalamiento a Piso de Ventanilla ($2.00 MXN) | `motor` | SELLADO |
| `[LN-QBE-071-B]` | Piso Estructural Bivariado ($4.00 MXN) y Cobertura Universal de la Familia R | `motor` | SELLADO |
| `[LN-QBE-072]` | Modelo Estocástico Combinatorio de Resiliencia 3^K y Trinidad de Certeza | `motor` | SELLADO |
| `[LN-QBE-073]` | Algoritmo del Slider Dinámico de Certeza (Risk Dial) | `motor` | SELLADO |
| `[LN-QBE-073-B]` | Algoritmo de Ranking de Fricción de Jornada | `motor` | SELLADO |
| `[LN-QBE-074]` | Optimizador de Quinielas Progol por Presupuesto | `ingesta` | SELLADO |
| `[LN-QBE-075]` | Ingesta Fáctica de Concursos Progol y Resiliencia Multi-Torneo | `ingesta` | SELLADO |
| `[LN-QBE-076]` | Arbitraje Sintético de Mejor Combinación Multi-Operador | `motor` | SELLADO |
| `[LN-QBE-077]` | Ecuación de Decisión: Pago Anticipado (+PA) vs. Cuota Nominal Pura | `motor` | SELLADO |
| `[LN-QBE-077-B]` | Teorema de Aceleración Asintótica y Partición de Capital con Cobertura Activa (V = δ > 0) | `motor` | SELLADO |
| `[LN-QBE-077-C]` | Techo de Viabilidad Analítica δ_max y Umbral de Breakeven θ* | `motor` | SELLADO |
| `[LN-QBE-077-D]` | Dutching Isorrendimiento de Doble Cosecha (δ*) | `motor` | SELLADO |
| `[LN-QBE-078]` | Cuantificación Transparente del Veto Fiduciario (Descartes QBE-00) | `motor` | SELLADO |
| `[LN-QBE-079]` | Operador de Contracción Fiduciaria Baricéntrica (Barycentric Dirichlet Shrinkage) | `motor` | SELLADO |
| `[LN-QBE-080]` | Compilador de Reportes Oficiales y PDF A4 | `motor` | SELLADO |
| `[LN-QBE-081]` | Probabilidad Efectiva de Éxito de la Posición (P_éxito') y Ordenamiento Lexicográfico | `motor` | SELLADO |
| `[LN-QBE-082]` | Principio de Asignación Monótona de Capital | `motor` | SELLADO |
| `[LN-QBE-083]` | Formalización de la Tetralogía de Escenarios de Liquidación | `motor` | SELLADO |
| `[LN-QBE-083-B]` | Unificación Honesta del Rótulo de Ausencia de Cobertura en Estrategias Directas | `motor` | SELLADO |
| `[LN-QBE-084]` | El Operador Canónico de Selección por Masa Acumulada P' en Progol | `ingesta` | SELLADO |
| `[LN-QBE-085]` | Cobertura Binaria Óptima (\|S_i\| ≤ 2) y Construcción del Espacio Restringido | `ingesta` | S_i\ |
| `[LN-QBE-086]` | Descenso por Distancia de Hamming hacia Premios Menores (L ∈ {13, 12, 11, 10}) | `ingesta` | SELLADO |
| `[LN-QBE-087]` | Algoritmo de Progol Revancha (K=7 Todo o Nada) | `ingesta` | SELLADO |
| `[LN-QBE-088]` | Resolver Semántico JIT de Competiciones y Clubes Internacionales | `ingesta` | SELLADO |
| `[LN-QBE-089]` | Parámetros Macro de Competiciones Descubiertas Dinámicamente | `motor` | SELLADO |
| `[LN-QBE-090]` | Escudo Forense de Invarianzas (The Shield Release Gate) | `motor` | SELLADO |
| `[LN-QBE-090-B]` | Heurística de Vinculación y Emparejamiento Multi-Torneo en Slates | `motor` | SELLADO |
| `[LN-QBE-091]` | Modelo de Intensidades para Divisiones Inferiores sin Opta xG | `observatorio` | SELLADO |
| `[LN-QBE-092]` | *(Reservado - Conciliación de Mercados Derivados)* | `motor` | LIBRE |
| `[LN-QBE-093]` | Axioma de Pureza de Sensores de Ingesta y Contratos DTO de Capa 1 (Data Nexus) | `observatorio` | SELLADO |
| `[LN-QBE-094]` | Algoritmo de Desambiguación Temporal en Ventana Crítica [t_cierre ± 72h] | `motor` | SELLADO |
| `[LN-QBE-095]` | Guardas Léxicas de Identidad de Género y Categoría (Femenil, Filiales, Sub-20) | `motor` | SELLADO |
| `[LN-QBE-096]` | Coordinador Orquestador Atómico del Ciclo de Vida de Datos (Data Nexus Bus) | `observatorio` | SELLADO |
| `[LN-QBE-097]` | Puente de Despacho Unificado entre Rutas Web y el Data Nexus Bus | `observatorio` | SELLADO |
| `[LN-QBE-098]` | Radiografía Forense Determinista y Comparador de Probabilidades sin LLM [ARCH-PILLAR] | `motor` | SELLADO |
| `[LN-QBE-099]` | Registro Fiduciario de Congelamiento de Boletos (Paper Trading & Audit Ledger) [ARCH-PILLAR] | `motor` | SELLADO |
| `[LN-QBE-100]` | Motor de Calibración Factual de Temporada y Evaluación Multicategórica de Brier | `observatorio` | SELLADO |
| `[LN-QBE-101]` | Motor de Atribución Factorial y Telemetría de Integridad de Insumos | `motor` | SELLADO |
| `[LN-QBE-102]` | Axioma de Protección de la Evidencia en Vivo, Sello de Procedencia y Telemetría de Insumos Fácticos | `motor` | SELLADO |
| `[LN-QBE-103]` | Proveedor Soberano de Memoria H2H con Corpus Congelado, Certificación Tri-Estado de la Procedencia Opta y Telemetría Dimensional | `ingesta` | SELLADO |
| `[LN-QBE-104]` | Fusión Convexa del Símplex Soberano (Poisson ∪ Kernel H2H) y Persistencia de la Δ_epist Real | `observatorio` | SELLADO |
| `[LN-QBE-105]` | Consolidación Fáctica de la Dimensión Memoria Longitudinal (H2H) | `ingesta` | SELLADO |
| `[LN-QBE-106]` | Pipeline Sandbox Autónomo y Modelado Relacional de Memoria H2H | `motor` | SELLADO |
| `[LN-QBE-107]` | Simulación Retrospectiva de Rentabilidad, Liquidación Factual y Métricas de Riesgo del Fondo | `motor` | SELLADO |
| `[LN-QBE-108]` | Colisión Cruzada de Fuerzas y Modelado Bipartito de Ataque (𝒯_Fin) y Defensa (𝒯_Def) | `motor` | SELLADO |
| `[LN-QBE-109]` | Modelado Físico de Shocks de Contexto, Altitud Fisiológica y Fatiga de Calendario | `motor` | SELLADO |
| `[LN-QBE-110]` | Modelado Fáctico de Trayectoria, Tendencias de Goles Esperados y Varianza xPTS | `motor` | SELLADO |
| `[LN-QBE-111]` | Modelado Fáctico de Volumen Territorial y Rendimiento de Guardametas (Volumen & Portería) | `motor` | SELLADO |
| `[LN-QBE-112]` | Modelado de Micro-Dinámicas, Balón Parado, Fricción Disciplinaria y Cierre Táctico | `motor` | SELLADO |
| `[LN-QBE-113]` | Veto Fiduciario Selectivo por Familia Estratégica en Simulador de Rentabilidad | `motor` | SELLADO |
| `[LN-QBE-114]` | Orquestación REST para Simulación Financiera Retrospectiva | `motor` | SELLADO |
| `[LN-QBE-115]` | Saneamiento Vol. II: Cota Underdog Ley 3, Escudo de Altitud y Trinidad de Certeza | `motor` | SELLADO |
| `[LN-QBE-116]` | Cota de Dominancia P′ ≥ 50% en la Híbrida Visitante (Blindaje H2) | `motor` | SELLADO |
| `[LN-QBE-117]` | Proveedores Canónicos de Insumos Factuales (Fase 1 · Integración Maestra) | `observatorio` | SELLADO |
| `[LN-QBE-118]` | Materialización Anidada de los Cinco Pilares y Resguardo WORM Previo a la DML (Fase 2 · Re-homologación) | `motor` | SELLADO |
| `[LN-QBE-119]` | Ley de Unidad de Volumen & Portería (Tasa Por Partido) y Sonda de Completitud Fáctica del Visor 44V (Fase 3 · Sincronía J13) | `observatorio` | SELLADO |
| `[LN-QBE-120]` | Catálogo Estructural de 32 Variables PRE-KICKOFF (Reingeniería Macro) y Derogación de la Partición 12×44 | `motor` | SELLADO |
| `[LN-QBE-121]` | Aduana de Exhibición Macro-Torneal: Iluminación Fáctica de las Celdas No Insumidas y Purga Nominal 44V | `motor` | SELLADO |
| `[LN-QBE-122]` | Purga Nominal ALT-B: Derivación Estructural de Taxonomías desde el Catálogo Único y Régimen de Auxiliares `AUX_*` | `motor` | SELLADO |
| `[LN-QBE-123]` | Saneamiento de Trayectoria Fáctica, Cuarentena Declarada de V16 y Guardián de Presencia del Descanso (Régimen Opción B) | `motor` | SELLADO |
| `[LN-QBE-124]` | Banda de Indiferencia Fiduciaria en la Cobertura Ordinal y Desempate por Altitud del Anfitrión | `motor` | SELLADO |
| `[LN-QBE-125]` | Cold Start Sincero: Derogación de la Sustitución por Prior de Mercado y Segmentación Declarada de la Muestra Calibrada | `observatorio` | SELLADO |
| `[LN-QBE-126]` | Sandbox de Arquetipos y Vectores: Extracción Inducida de Firmas por Clase en el Espacio Z-Score | `observatorio` | SELLADO |
| `[LN-QBE-127]` | Fuente Única de Verdad en la Calibración: Resolución al Vuelo de $P'$ y Derogación del Descarte Silencioso | `observatorio` | SELLADO |
| `[LN-QBE-128]` | Prior Congelado de Apertura 2025 y Ley de Mezcla Monótona del Corte (Erradicación del Cold Start Estructural) | `observatorio` | SELLADO |
| `[LN-QBE-129]` | Minería de Información Mutua de Shannon y Árbol Esparso de Veto (Descubrimiento de Rupturas P_LOW) | `motor` | SELLADO |
| `[LN-QBE-130]` | Reglas de Curación HITL y Seeding de Competiciones | `motor` | SELLADO |
| `[LN-QBE-133]` | Ingesta Fáctica Profunda | `ingesta` | SELLADO |
| `[LN-QBE-134]` | Protocolo de Ingesta Offline MHTML y Verificación de Integridad de Temporada | `ingesta` | SELLADO |
| `[LN-QBE-135]` | Protocolo de Carga Masiva Idempotente para Corpus Multianual (12 Temporadas) | `ingesta` | SELLADO |
| `[LN-QBE-136]` | Sonda de Captura CDP-MHTML y Perfil Persistente | `ingesta` | SELLADO |
| `[LN-QBE-137]` | Juez Inmutable de Integridad de Muestras MHTML | `ingesta` | SELLADO |
| `[LN-QBE-138]` | Protocolo de Memoria Institucional Modular y Transferencia de Arquitectura (KTP Package) | `gobierno` | SELLADO |
| `[LN-QBE-139]` | Auditor de Paridad Estática AST y Generador de Bandeja `GL_update.md` | `gobierno` | SELLADO |
| `[LN-QBE-140]` | Juez Inmutable de Paridad Canónica y Detección de Reglas Huérfanas | `gobierno` | SELLADO |
| `[LN-QBE-141]` | Parser Offline de Eventos Minuto a Minuto (Jugada a Jugada) | `ingesta` | SELLADO |
| `[LN-QBE-142]` | Sonda de Descubrimiento de Partidos y URLs Minuto a Minuto (ligamx.net) | `ingesta` | SELLADO |
| `[LN-QBE-143]` | Orquestador de Extracción Masiva de Eventos (ligamx.net → Bóveda OLAP) | `ingesta` | SELLADO |
| `[LN-QBE-144]` | Almacén de Eventos Históricos (`historical_match_events`) | `ingesta` | SELLADO |
| `[LN-QBE-145]` | Diccionario Canónico de Alias de Liga MX (`ligamx.net` → bóveda) | `ingesta` | SELLADO |
| `[LN-QBE-146]` | Motor de Derivación de Variables Causales | `motor` | SELLADO |
| `[LN-QBE-147]` | Motor de Calibración y Perturbación de Variables Causales | `motor` | SELLADO |
| `[LN-QBE-148]` | Motor de Consenso Ponderado (Wisdom of the Crowds) | `motor` | SELLADO |
| `[LN-QBE-149]` | Motor de Detección de Rupturas de Consenso (Radar de Sindicatos) | `motor` | SELLADO |
| `[LN-QBE-150]` | Motor de Cálculo de Distribuciones Históricas (P') | `motor` | SELLADO |

_Total: 138 identificadores._

---

## 10.1. AUDITOR DE PARIDAD ESTÁTICA AST Y JUEZ DE PARIDAD CANÓNICA

### ID: [LN-QBE-139] Auditor de Paridad Estática AST y Generador de Bandeja `GL_update.md`

* **Ω (Resumen):** Script determinista que escanea el AST de `qbe_core/src/core/` y `qbe_business/src/` para certificar la paridad biunívoca entre el código crítico y la Base de Gobierno. Extrae las etiquetas `[LN-QBE-XXX]`, cruza su existencia contra `docs/LOGIC.md` y `docs/ID_REGISTRY.md` y clasifica las infracciones en Clases I a IV. No usa LLM, no corrige código y no decide: detecta, clasifica y propone.
* **I (Input):** Directorios `qbe_core/src/core/`, `qbe_business/src/`; libros `docs/LOGIC.md` y `docs/ID_REGISTRY.md`. Para peritaje unitario, una ruta de archivo individual.
* **P (Process) [ALGO-PROTECTED] [DIRGEN-STRICT]:**
  1. **Parseo AST:** Lectura de cada archivo con `ast.parse`. Una sintaxis corrupta DEBE propagar `SyntaxError` (fail-loud), sin `try/except` que la silencie.
  2. **Extracción de etiquetas:** Identificación de `[LN-QBE-XXX]` en el docstring o comentario inmediato de cada función de cálculo crítico.
  3. **Cruce de conjuntos:** Comparación contra los IDs vigentes de la BG. Una función sin etiqueta, o con ID inexistente, es **Regla Huérfana**. Un nodo crítico sin materialización o sin Juez es **Brecha Legislativa**.
  4. **Clasificación:** Asignación de Clase I (Fabricación Sintética), Clase II (Contradicción Numérica), Clase III (Colisión de Literales) o Clase IV (Heurísticas Permisivas), conforme a `docs/GOVERNANCE.md` §1.1.3.
  5. **Generación de bandeja:** Serialización de hallazgos en `docs/KTP/GL_update.md` con archivo, línea, función, clase, evidencia y veredicto pendiente.
* **O (Output):** Archivo `docs/KTP/GL_update.md` con la tabla de hallazgos y el veredicto `PENDIENTE DEL DIRECTOR`. Es una bandeja de revisión, no una orden de cambio.
* **Invocación:** Ejecución mandatoria en el Cierre de Sprint y en el pre-commit de Núcleo (`qbe_core` / `qbe_business`); ejecución obligatoria bajo demanda a solicitud del Director Humano, del Arquitecto o del Juez. El Censo y el criterio de 0 hallazgos se rigen por `docs/GOVERNANCE.md` §3.5.
* **Φ (Transición):** Hacia la Tríada para aprobación de **VÍA A (Erradicación)** o **VÍA B (Formalización)**; luego a la materialización subordinada del Auditor.
* **Invariantes:** Solo lectura sobre el código; determinista; cero consumo generativo; no modifica `src/` ni `qbe_business/src/`; no reemplaza el dictamen humano.
* **[SHIELD]:** `qbe_core/tests/test_shield_canonical_parity.py`

### ID: [LN-QBE-140] Juez Inmutable de Paridad Canónica y Detección de Reglas Huérfanas

* **Ω (Resumen):** Juez Inmutable que certifica la Triple Aserción del Auditor: Réplica Analítica, Invarianza Estructural y Anti-Patrón Fail-Loud. Exige que el Auditor detecte exactamente una Regla Huérfana de Clase I en una función mock con `except: return 0.0` sin etiqueta, que no mute el archivo fuente y que una sintaxis corrupta produzca `SyntaxError`.
* **I (Input):** Clase `AuditarParidadBG` de `[LN-QBE-139]` y una fixture temporal con la función mock.
* **P (Process) [ALGO-PROTECTED] [DIRGEN-STRICT]:**
  1. **Réplica Analítica:** Evaluar una función mock con `except: return 0.0` y sin `[LN-QBE-XXX]`; exigir exactamente 1 Regla Huérfana de Clase I.
  2. **Invarianza Estructural:** Certificar que el Auditor no modifica el archivo original; el hash SHA-256 y el `mtime` deben permanecer idénticos.
  3. **Anti-Patrón (Sad Path):** Someter al Auditor a un archivo con sintaxis corrupta; exigir una excepción explícita `SyntaxError`, nunca un resultado vacío.
* **O (Output):** `GREEN` solo si las tres aserciones pasan; `RED` si el Auditor no existe, no detecta, muta el archivo o silencia la sintaxis corrupta.
* **Φ (Transición):** Hacia la materialización de `[LN-QBE-139]` y el primer `docs/KTP/GL_update.md`.
* **[SHIELD]:** `qbe_core/tests/test_shield_canonical_parity.py`

---

## 11. TRAZABILIDAD

- Fuente: `Q_BE_CD_WEB/docs/LOGIC.md`.
- Migración: 32V canónico, reanclaje a cuatro pilares, tombstone del 44V.
- Juez de referencia: `qbe_core/tests/test_shield_ecosystem_governance.py` + suite de dominio.
- Cierre: `53+ passed`, `0 failed`, `EXIT CODE 0`.

---

## 12. PROTOCOLO DE INGESTA OFFLINE MHTML

### ID: [LN-QBE-134] Protocolo de Ingesta Offline MHTML y Verificación de Integridad de Temporada

* **Ω (Resumen):** Establece el estándar de extracción fáctica determinista a partir de volcados offline en formato MIME HTML (`.mhtml`). Consagra el Candado de Integridad de Temporada: prohíbe procesar cualquier volcado cuyo metadato temporal interno en el DOM (`h1` o `data-hash`) no coincida estrictamente con el identificador de la carpeta contenedora. Extrae de forma estructurada calendarios, marcadores finales, cuotas de cierre 1X2, tablas de forma reciente (Last 5) y goles esperados macro ($xG/xGA$) por club-temporada para la serie histórica 2015-2027.
* **I (Input):** Directorio `data/raw_footystats/{temporada}/` conteniendo archivos `.mhtml`.
* **P (Process) [ALGO-PROTECTED] [DIRGEN-STRICT]:**
  1. **Desempaquetado MIME Puro:** Se decodifica el cuerpo `text/html` mediante `email.message_from_binary_file` sin llamadas de red ni dependencias de navegador.
  2. **Aserción de Integridad Temporal (Fail-Loud):**
     Se extrae la temporada del DOM analizando `h1.detailed-stats-h1` o `data-hash` y se normaliza a `YYYY_YYYY`.
     $$\text{Aserción Inviolable: } \text{Temporada}_{\text{DOM}} \equiv \text{NombreCarpeta}$$
     Si no coinciden, se lanza `SeasonIntegrityError` y se aborta el procesamiento de la carpeta.
  3. **Extracción de Fixtures y Momios:**
     - `fecha_utc`: Derivado estrictamente del atributo `data-time` (Unix epoch timestamp).
     - `home_team`, `away_team`: Extraídos con resolución de `data-team-id`.
     - `home_goals`, `away_goals`: Parseo de `.ft-score`.
     - Cuotas de cierre: Parseo de `.stat.odds` (`odd_home`, `odd_draw`, `odd_away`). Queda prohibida la lectura de `div.form-box` como cuota.
  4. **Extracción de Forma y xG Macro:**
     - Last 5: PPG, victorias, empates, derrotas desde `Form Table_*.mhtml`.
     - xG macro (2018+): Tasas agregadas de club desde `xG_*.mhtml`, selladas como `fuente_xg = "FOOTYSTATS_PROPIETARIO"`.
  5. **Persistencia Estructurada:** Generación de `data/extracted_footystats/temporada_{YYYY}_{YYYY}.json`.
* **O (Output):** Datasets JSON limpios por temporada y reporte consolidado en consola.
* **Φ (Transición):** Hacia `data/extracted_footystats/` y base histórica 3NF.
* **[SHIELD]:** `qbe_ingestion/tests/test_shield_mhtml_parser_and_season_integrity.py`

---

## 13. CARGA MASIVA HISTÓRICA 3NF

### ID: [LN-QBE-135] Protocolo de Carga Masiva Idempotente para Corpus Multianual (12 Temporadas)

* **Ω (Resumen):** Establece la doctrina de inserción relacional masiva para trasladar el corpus histórico (Datasets JSON) hacia la Bóveda Analítica (Base de Datos Histórica). Exige estricta idempotencia transaccional (cero duplicidad ante re-ejecuciones) y mapeo dinámico del esquema (Reflection). Preserva la honestidad de los datos ausentes (`[GOVERNANCE-01]`): si un partido fue cancelado o pertenece al futuro, sus marcadores y cuotas se insertan como `NULL`, prohibiendo la coerción a ceros sintéticos.
* **I (Input):** Directorio `data/extracted_footystats/*.json` (12 temporadas) y conexión a `qbe_observatory/data/qbe_historico.db`.
* **P (Process) [ALGO-PROTECTED] [DIRGEN-STRICT]:**
  1. **Generación de Llave Primaria Determinista:** 
     Se asigna a cada registro un `match_id` universal basado en hashes o concatenación normalizada: `fs_{temporada}_{match_ref}` para garantizar unicidad. Si el registro de entrada ya trae `match_id` explícito, se respeta.
  2. **Resolución de Esquema (DDL Dinámico):**
     Se audita el esquema de la base destino. Si faltan tablas para el almacenamiento de métricas macro (`historical_team_season_stats` para xG o Forma 5P) o cuotas, se ejecutan las sentencias `CREATE TABLE IF NOT EXISTS` garantizando soporte 3NF.
  3. **Transaccionalidad Atómica por Temporada:**
     La inserción se ejecuta en bloques (Bulk Insert) encapsulados en un único `COMMIT` por temporada. Si ocurre un error de tipado, se ejecuta `ROLLBACK` total de la temporada afectada.
* **O (Output):** Base de datos `qbe_historico.db` poblada con 3,870 partidos listos para inferencia estadística.
* **Φ (Transición):** Hacia modelos de entrenamiento y calibración de Dixon-Coles multianual.
* **[SHIELD]:** `qbe_ingestion/tests/test_shield_historical_load_integrity.py`

---

## 14. SONDA MULTIFUENTE MHTML Y JUEZ DE INTEGRIDAD

### ID: [LN-QBE-136] Sonda de Captura CDP-MHTML y Perfil Persistente

* **Ω (Resumen):** Capturar artefactos web dinámicos (SPA) evadiendo bloqueos antibot mediante navegación humana asistida (Playwright) y extracción binaria directa (Chrome DevTools Protocol) para consolidar el corpus histórico.
* **I (Input):** `ProbeTarget` (Pydantic V2) con `url`, `provider_name`, `output_dir`.
* **P (Process) [ALGO-PROTECTED]:**
  1. Lanzar contexto persistente (`launch_persistent_context`).
  2. Navegar a la URL y pausar para interacción humana (si el sitio exige captcha).
  3. Invocar `Page.captureSnapshot` vía CDP con formato 'mhtml'.
  4. Escribir los bytes directamente en disco. Si la red falla o hay timeout, lanzar `ProbeExtractionError` (Fail-Loud). Cero fallbacks.
* **O (Output):** `pathlib.Path` del archivo `.mhtml` generado.
* **Φ (Transición):** Hacia `[LN-QBE-137]` (Auditor Offline).

### ID: [LN-QBE-137] Juez Inmutable de Integridad de Muestras MHTML

* **Ω (Resumen):** Contrato de validación estricta (The Shield) que certifica que los archivos `.mhtml` capturados por la sonda son legibles, contienen payloads MIME válidos y no representan páginas vacías o bloqueos del WAF.
* **I (Input):** `pathlib.Path` al archivo `.mhtml`.
* **P (Process) [ALGO-PROTECTED]:** Parseo con la librería `email` de Python. Verificación de la cabecera `Content-Type: multipart/related`. Búsqueda de sub-bloques `text/html`.
* **O (Output):** Booleano `True` o excepción `MHTMLIntegrityError`.
* **Φ (Transición):** Hacia `[LN-QBE-134]` (Parser Offline).

---

## 15. PROTOCOLO DE MEMORIA INSTITUCIONAL MODULAR Y TRANSFERENCIA (KTP PACKAGE)

### ID: [LN-QBE-138] Protocolo de Memoria Institucional Modular y Transferencia de Arquitectura (KTP Package)

* **Ω (Resumen):** Establece la doctrina de transferencia de contexto y gobernanza asincrónica mediante el paquete estructurado `docs/KTP/`. Desacopla la base de conocimiento duradera del proyecto (`KDB.md`) del reporte de contexto dinámico del turno activo (`AKT.md`). Prohíbe la acumulación de deudas históricas superadas en los protocolos de relevo y estandariza los prompts de extracción de memoria (`AKT_Pmpt.md`), consolidación fáctica (`KDB_Act_Pmpt.md`) y asunción de mando (`RT_Pmpt.md`), garantizando continuidad inmediata sin pérdida de intención ni alucinaciones.
* **I (Input):** Estado de Git HEAD, resultados de The Shield, base de datos viva y registro de decisiones de la sesión.
* **P (Process) [ALGO-PROTECTED] [DIRGEN-STRICT]:**
  1. **Estructura Séxtuple Inviolable:** El paquete `docs/KTP/` debe contener exactamente los seis archivos rectores: `KTP_Guide.md`, `KDB.md`, `AKT_Pmpt.md`, `AKT.md`, `KDB_Act_Pmpt.md`, `RT_Pmpt.md` y el subdirectorio `history/`.
  2. **Ciclo de Relevo Fiduciario:**
     - **Fase A (Despacho):** El Arquitecto saliente ejecuta `AKT_Pmpt.md` generando el delta de su turno en `AKT.md`.
     - **Fase B (Consolidación):** El Constructor ejecuta `KDB_Act_Pmpt.md`, actualiza `KDB.md` con los datos empíricos de Git/Shield y archiva `AKT.md` en `history/AKT_{FECHA}_{SPRINT}.md`. El archivo se materializa por copia; el activo `AKT.md` se reinicia en el mismo acto para preservar la estructura séxtuple.
     - **Fase C (Asunción):** El Director Humano entrega `RT_Pmpt.md` en la conversación limpia del Arquitecto entrante, junto con `KDB.md`, `AKT.md`, la Base de Gobierno (`docs/`) y la Guía Kybern v13.5. El Arquitecto ejecuta el prompt, emite el Eco de Comprensión Integral de 7 puntos y queda en posición de espera sin requerir el historial de chats anteriores.
  3. **Custodia de IDs:** Los nodos de este subsistema se registran con `max + 1` sobre la familia correspondiente. Ningún ID sellado se reasigna ni se reutiliza.
  4. **Cero Invención:** Todo dato sin evidencia se declara `SIN EVIDENCIA`, se somete a cuarentena o se veta; nunca se sustituye por un valor sintético.
  5. **Archivo Inmutable:** Los archivos de `history/` no se editan ni se eliminan. El nombre canónico es `AKT_{YYYY-MM-DD}_{SPRINT}.md`.
* **O (Output):** Paquete `docs/KTP/` materializado y trazabilidad histórica blindada.
* **Φ (Transición):** Hacia la operación continua de relevos y onboarding de nuevas instancias.
* **[SHIELD]:** `qbe_core/tests/test_shield_ktp_package_integrity.py`

---

## 16. EXTRACCIÓN CAUSAL MINUTO A MINUTO (JUGADA A JUGADA)

### ID: `[LN-QBE-141]` Parser Offline de Eventos Minuto a Minuto (Jugada a Jugada)

* **Ω (Resumen):** Parser determinista y offline del visor «Minuto a Minuto» de `ligamx.net`. Desempaqueta un volcado MHTML, aísla la línea de tiempo canónica «Jugada a Jugada» y extrae los eventos fácticos (gol, tarjeta, córner, tiro, falta, cambio, fuera de lugar, penal, atajada y marcadores de período) con minuto, lado y equipo. Es la fuente causal para la calibración del modelo Q-BE. Cero red, cero navegador, cero datos sintéticos.
* **I (Input):** `pathlib.Path` a un archivo `.mhtml` con la página `https://ligamx.net/cancha/mxm/{idPartido}/.../minuto-a-minuto-...` capturada. La estructura de referencia es `data/raw_ligamx_min_x_min/MinXMin_2015-2016_Clau_Ame_vs_MTY.mhtml`.
* **P (Process) [ALGO-PROTECTED] [DIRGEN-STRICT]:**
  1. **Desempaquetado MIME:** `email.message_from_binary_file` con `policy.default`; se recorre el mensaje y se toma la parte `text/html`; `get_payload(decode=True)` resuelve el *quoted-printable*.
  2. **Decodificación estricta:** se respeta el `charset` declarado por la parte MIME; si no declara, se usa UTF-8. Se prohíbe `errors="replace"`: un byte inválido aborta con `MinutoAJugadaError`.
  3. **Aduana estructural:** el documento contiene **dos** `div.jugadasTool`: la línea canónica (con `#timeline_local` y `#timeline_visita`, 49 eventos) y la línea de videos (con `#timelineVideo_local` y `#timelineVideo_visita`, 13 duplicados). Solo se acepta el contenedor que contiene exactamente las dos columnas canónicas; si hay cero o más de uno, se aborta.
  4. **Extracción de eventos:** se iteran únicamente las filas hijas directas `div.row` con `div.toolJugada`; las filas espaciadoras (solo `div.paso`, sin `.toolJugada`) se ignoran. El `evento_id` se toma del sufijo de la clase `evntLcal_{id}` / `evntVsta_{id}` y se corrobora contra `span.enlace#evnt_{id}`.
  5. **Clasificación por narrativa:** el tipo se deriva de `span.desc` (no de `div.paso`, que solo existe en la columna local). El catálogo es `gol`, `gol_penal`, `tarjeta_amarilla`, `tarjeta_roja`, `corner`, `falta`, `tiro_a_gol`, `cambio`, `fuera_de_lugar`, `penal`, `atajada`, `inicio_partido`, `inicio_segundo_tiempo`, `final_primer_tiempo`, `final_partido` y `otro` (bucket declarado, nunca descartado).
  6. **Gramática del minuto:** `N'` → `minuto = N`; `+N'` → `minuto_agregado = N`; `N+M'` → `minuto = N`, `minuto_agregado = M`; `MT`/`MF` → marcador de período. Cualquier otro rótulo aborta.
  7. **Períodos:** la columna local usa una máquina de estados sobre los cuatro marcadores obligatorios (`inicio_partido`, `final_primer_tiempo`, `inicio_segundo_tiempo`, `final_partido`). La columna visitante no trae marcadores: se aplica la regla numérica `minuto ≤ 45 → 1T`, `minuto ≥ 46 → 2T`, `+N' → 2T`.
  8. **Metadatos:** `equipo_local` y `equipo_visitante` se leen de `.cara-cara .equipoMin a[href*='/cancha/club/']` vía `data-original-title` (primer bloque local, segundo visitante); el marcador se lee de `.cara-cara .score` con la forma `N - M`.
* **O (Output):** `parsear_minuto_a_minuto(ruta) -> list[dict]` devuelve 49 eventos para la muestra. Cada evento declara: `evento_id`, `lado` (`local`/`visita`), `equipo` (nulo en eventos neutrales), `minuto_texto`, `minuto`, `minuto_agregado`, `marcador_periodo`, `periodo`, `tipo`, `descripcion`, `video_url`, `paso`, `orden_dom` (orden de aparición en el DOM: columna local y luego visitante). El sobre extendido `parsear_partido(ruta)` añade `equipo_local`, `equipo_visitante`, `marcador_local` y `marcador_visitante`.
* **Φ (Transición):** Hacia la construcción de variables causales de calibración (goles, tarjetas, córners y ritmo por franja) y hacia el corpus histórico de `qbe_observatory`.
* **Invariantes:** offline puro; cero mocks; cero datos sintéticos; el número de eventos de la muestra es 49; los IDs son únicos; la línea de videos nunca se mezcla; `qbe_core` no se importa ni se modifica.
* **Fail-Loud:** aborta si falta el archivo, la parte `text/html`, la decodificación estricta, el contenedor canónico, alguna de las dos columnas, los cuatro marcadores, la descripción, el minuto, el `evento_id`, la corroboración `span.enlace` o si hay IDs duplicados o un minuto fuera de gramática.
* **[SHIELD]:** `qbe_ingestion/tests/test_shield_minuto_a_minuto_parser.py`

### ID: `[LN-QBE-142]` Sonda de Descubrimiento de Partidos y URLs Minuto a Minuto (ligamx.net)

* **Ω (Resumen):** Sonda determinista de descubrimiento que navega `ligamx.net/cancha/partidos`, resuelve los identificadores de temporada, torneo y jornada desde `voTmpTrns.DatosJSON`, consulta el widget `PRTL_Partidos` y construye las URLs canónicas de «Minuto a Minuto» para cada partido. Es la puerta de entrada al corpus causal; no descarga eventos ni interpreta el DOM de la línea de tiempo.
* **I (Input):** Argumentos CLI `--temporada` (ej. `2015-2016`), `--torneo` (ej. `Clausura`) y `--jornada` (ej. `16`); sesión HTTP de Playwright contra el sitio público.
* **P (Process) [ALGO-PROTECTED] [DIRGEN-STRICT]:**
  1. **Navegación stealth:** Chromium con `User-Agent` de escritorio y `--disable-blink-features=AutomationControlled`; el UA por defecto de Playwright es bloqueado por el WAF (HTTP 500 «Web Page Blocked»).
  2. **Captura del HTML servidor:** se captura el cuerpo de la respuesta documental de `page.goto(/cancha/partidos)` —el HTML prístino del servidor, antes de que el JS reescriba la plantilla— y se conservan las cookies de la sesión. Ese HTML contiene la plantilla `vsurlMrcdrActls` y el mapa `voTmpTrns.DatosJSON`.
  3. **Resolución de identificadores:** se filtra `Temporada == {temporada}`, `Torneo == {torneo}` y `Division == "LIGA MX"`; debe existir exactamente una fila. De ella salen `IDTemporada`, `IDTorneo` e `IDDivision`.
  4. **Consulta del widget:** se sustituyen `<IDDIVISION>`, `<IDJORNADA>`, `<IDTEMPORADA>` e `<IDTORNEO>` en la plantilla, se codifica el servicio en base64 (reemplazando el primer `/` por `@`) y se hace `GET /ws/{servicio}`. La respuesta debe contener `DatosJSON` con al menos un partido. El widget alterna de forma transitoria entre la cartelera y `[{}]`; se reintenta de forma acotada (4 intentos, 0.4 s) y, si persiste, se aborta.
  5. **Construcción determinista de URLs:** para cada partido se arma
     `https://ligamx.net/cancha/mxm/{idPartido}/{base64({"idClublocal": "{idLocal}", "idClubvisita": "{idVisita}", "idPartido": "{idPartido}", "pestana": "3"})}`.
     El enlace `.lnk-minute` del sitio no tiene `href`; esta forma es la que resuelve de forma estable.
  6. **Verificación opcional:** con `--verificar`, cada URL se descarga y se exige HTTP 200 y presencia de `section.jugadaSeccion`; los nombres de ambos clubes se contrastan en la salida del widget.
* **O (Output):** Tabla legible o JSON (`--json`) con `id_partido`, `local`, `visitante`, `goles_local`, `goles_visitante` y `url_minuto_a_minuto`. Para la muestra, la jornada 16 del Clausura 2016 devuelve 9 partidos, incluido `67047 América 3-3 Monterrey`.
* **Φ (Transición):** Hacia la captura MHTML (`[LN-QBE-136]`) y el parser offline (`[LN-QBE-141]`).
* **Invariantes:** solo lectura sobre el sitio; sin login; sin IDs de partido codificados en la lógica; sin datos sintéticos; determinista en la construcción de URLs; falla ruidosamente si no resuelve la temporada/torneo, si el widget no devuelve partidos o si la verificación no coincide.
* **[SHIELD]:** `qbe_ingestion/tests/test_shield_descubrimiento_ligamx.py` (constructor puro de URLs) y ejecución de `scripts/auditoria/descubrir_partidos_ligamx.py --verificar`.

---

## 17. ORQUESTACIÓN MASIVA Y ALMACENAMIENTO DE EVENTOS

### ID: `[LN-QBE-144]` Almacén de Eventos Históricos (`historical_match_events`)

* **Ω (Resumen):** Persistencia idempotente de la línea de tiempo factual de un partido en la bóveda OLAP. Recibe la llave canónica `match_id` y la lista de eventos del parser `[LN-QBE-141]`, asegura el esquema por Reflection DDL (`CREATE TABLE IF NOT EXISTS` + `PRAGMA table_info`), valida la integridad referencial y ejecuta una inserción masiva `INSERT OR IGNORE` dentro de una única transacción `BEGIN IMMEDIATE`. No transforma la evidencia ni inventa filas.
* **I (Input):** `db_path` (`qbe_observatory/data/qbe_historico.db`), `match_id` (`TEXT`, clave de `historical_matches`) y `eventos: list[dict]` con el contrato de `[LN-QBE-141]`. Para la CLI, la lista puede llegar como JSON (`--eventos-json`) o resolverse por Join Determinista (`--temporada/--local/--visitante/--marcador`).
* **P (Process) [ALGO-PROTECTED] [DIRGEN-STRICT]:**
  1. **Aduana de entrada:** la lista debe ser no vacía; cada evento debe declarar `evento_id`, `lado` ∈ {`local`, `visita`}, `tipo`, `minuto_texto`, `descripcion` y `orden_dom`. Cualquier faltante aborta con `EventoInvalidoError` antes de abrir transacción.
  2. **Reflection DDL:** se ejecuta el DDL canónico de `[ARCH-1.5.1]` §15.2; las columnas faltantes se agregan con `ALTER TABLE ... ADD COLUMN` tras leer `PRAGMA table_info`, sin recrear la tabla ni perder datos.
  3. **Integridad referencial explícita:** `SELECT 1 FROM historical_matches WHERE match_id = ?`; si no hay fila, se aborta con `MatchResolutionError` (SQLite no fuerza FK por defecto).
  4. **Inserción masiva:** `INSERT OR IGNORE` con `executemany` sobre `(match_id, evento_id)`; se cuentan insertados como delta de `total_changes` e ignorados como diferencia.
  5. **Atomicidad:** una sola transacción `BEGIN IMMEDIATE` / `COMMIT`; cualquier excepción ejecuta `ROLLBACK` y propaga.
* **O (Output):** `{"match_id": str, "recibidos": int, "insertados": int, "ignorados": int, "total_en_tabla": int}`. En la CLI, además, tablero de consola y código de salida `0`.
* **Φ (Transición):** Hacia el consumo causal del observatorio (goles, tarjetas, córners y ritmo por franja) y hacia el orquestador `[LN-QBE-143]`.
* **Invariantes:** idempotencia estricta por `(match_id, evento_id)`; cero duplicados; cero datos sintéticos; cero escrituras en `matches`, `sovereign_distributions` ni `match_telemetry`; `qbe_core` no se importa ni se modifica; el `match_id` proviene siempre de una fila existente de la bóveda.
* **Fail-Loud:** aborta si la lista está vacía, si un evento incumple el contrato, si el `match_id` no existe en `historical_matches`, si el DDL no se puede aplicar o si la transacción falla.
* **Resolución de `match_id` por Join Determinista (contrato de §15.3):** `resolver_match_id(db_path | connection, temporada, equipo_local, equipo_visitante, goles_local, goles_visitante)` normaliza la temporada a `YYYY_YYYY`, canoniza los clubes a slug y exige **exactamente una** fila de `historical_matches`. Cero o más de una coincidencias lanzan `MatchResolutionError`; nunca se aproxima ni se fabrica la llave.
* **[SHIELD]:** `qbe_ingestion/tests/test_shield_orquestador_extraccion.py`

### ID: `[LN-QBE-143]` Orquestador de Extracción Masiva de Eventos (ligamx.net → Bóveda OLAP)

* **Ω (Resumen):** Orquestador de lote que recorre un rango de jornadas, descubre los partidos con la sonda `[LN-QBE-142]`, descarga el HTML del visor «Minuto a Minuto» con Playwright (UA stealth reutilizando el contexto de la sonda), lo parsea con `parsear_partido_desde_html` (`[LN-QBE-141]`, extensión pura documentada en §17.3), canoniza los clubes con `[LN-QBE-145]`, resuelve el `match_id` por Join Determinista y persiste los eventos con `[LN-QBE-144]`. Es Fail-Loud por partido: registra el fallo, continúa con el siguiente y emite un resumen final con todos los fallos; nunca los oculta ni los convierte en éxitos.
* **I (Input):** `--temporada` (ej. `2015-2016`), `--torneo` (ej. `Clausura`), `--jornada_inicio`, `--jornada_fin`; opcionales `--db` (bóveda destino), `--reporte-json` (bitácora del lote) y `--headed` (diagnóstico visual).
* **P (Process) [ALGO-PROTECTED] [DIRGEN-STRICT]:**
  1. **Fase 1 — Descubrimiento:** `range(jornada_inicio, jornada_fin + 1)`; cada jornada se resuelve con `descubrir(temporada, torneo, jornada)` (`[LN-QBE-142]`). La sonda abre y cierra su propia sesión de Playwright, por lo que el rango completo se descubre antes de abrir la sesión de descarga (dos `sync_playwright` anidados en el mismo hilo no son válidos). Una jornada que aborta se registra como fallo de jornada y el lote continúa.
  2. **Fase 2 — Descarga:** para cada partido descubierto, navegación documental con Playwright y captura del **DOM renderizado** (`page.content()`), con el `User-Agent` de escritorio y las cookies de sesión del WAF. Se exige HTTP 200 y se espera `div.jugadasTool .toolJugada`: el HTML crudo del servidor no trae `toolJugada` ni `data-original-title` (los inyecta el JS), y la captura canónica de `[LN-QBE-136]` es justamente un volcado CDP del DOM ya renderizado. El HTML se procesa en memoria (nunca se materializa un MHTML de 14 MB).
  3. **Parseo:** `parsear_partido_desde_html(html)` devuelve el sobre (equipos, marcador, 49 eventos en la muestra). El parser es el único intérprete del DOM.
  4. **Canonización de nombres:** `resolver_alias_ligamx(...)` (`[LN-QBE-145]`) traduce `equipo_local` y `equipo_visitante` del sobre a los nombres canónicos de la bóveda. El Join Determinista no se modifica: solo recibe nombres limpios.
  5. **Resolución de llave:** `resolver_match_id(...)` con la temporada normalizada y el sobre ya canonizado (equipos y marcador); 0 o >1 candidatos abortan **ese** partido con `MatchResolutionError`.
  6. **Persistencia:** `cargar_eventos(db_path, match_id, eventos)`; el resultado (`insertados`/`ignorados`) se registra por partido.
  7. **Fail-Loud por partido:** toda excepción se captura **solo** para registrarla con tipo, mensaje, jornada, `id_partido` y URL; el lote continúa. Al cierre se emite tabla de resultados, resumen (`procesados`, `ok`, `fallidos`, `eventos_insertados`, `eventos_ignorados`) y, si se pidió, la bitácora JSON.
  8. **Código de salida:** `0` si y solo si no hubo fallos; `1` si hubo al menos uno (el resumen los enumera).
* **O (Output):** Tabla de lote (jornada, `id_partido`, local, visitante, estado, eventos, insertados, ignorados, error), resumen final y bitácora JSON opcional. Para la muestra: Jornada 16 del Clausura 2016 → 9 partidos, 49 eventos en `América 3-3 Monterrey` (`match_id` `fs_2015_2016_z85264`).
* **Φ (Transición):** Hacia el corpus causal de calibración del observatorio; el orquestador no calcula ni interpreta probabilidades.
* **Invariantes:** cero mocks en producción; cero datos sintéticos; una sola sesión de descarga por lote (la sonda abre y cierra la suya por jornada); el HTML se procesa en memoria; los fallos nunca se silencian; `qbe_core` no se importa ni se modifica; no se escribe fuera de `historical_match_events`.
* **Fail-Loud:** jornada irresoluble, HTTP distinto de 200, HTML sin estructura canónica, sobre sin equipos/marcador, resolución de `match_id` ambigua o vacía, o fallo de persistencia: se registran con evidencia y el resumen final los declara.
* **[SHIELD]:** `qbe_ingestion/tests/test_shield_orquestador_extraccion.py`

### 17.3 Extensión pura del Parser `[LN-QBE-141]`: `parsear_partido_desde_html`

* **Motivo:** el orquestador `[LN-QBE-143]` obtiene el HTML del visor en memoria; materializar un MIME de 14 MB por partido sería un desperdicio de I/O y una fuente de fragilidad.
* **Contrato:** `parsear_partido_desde_html(html: str) -> dict` devuelve exactamente el mismo sobre que `parsear_partido(ruta)`, reutilizando la misma función interna de extracción sobre el árbol `BeautifulSoup`. `parsear_partido(ruta)` pasa a ser «desempaquetar MIME y delegar»; su contrato, mensajes y Juez no cambian.
* **Invariantes:** la lógica de extracción no se duplica; las validaciones (contenedor canónico, columnas, marcadores, gramática del minuto, IDs únicos) son las mismas; un `html` vacío o no textual aborta con `MinutoAJugadaError`.
* **Fail-Loud:** idéntico al de `[LN-QBE-141]`.
* **[SHIELD]:** `qbe_ingestion/tests/test_shield_minuto_a_minuto_parser.py` (intacto) y `qbe_ingestion/tests/test_shield_orquestador_extraccion.py` (invariante de equivalencia MHTML ↔ HTML).

### 17.4 Contratos de Resiliencia del Orquestador `[LN-QBE-143]`

Consecuencia de la Ficha de Varianza del 2026-11-01 (cuelgue aparente del lote por esperas sin tope). Estos contratos son **obligatorios** para toda ejecución del orquestador:

| Contrato | Valor canónico | Semántica |
|---|---|---|
| `TIMEOUT_MS` | `30000` | Tope único de navegación (`goto`), de espera de render (`div.jugadasTool .toolJugada`) y `set_default_timeout` de contexto y página. Un tiempo agotado se traduce a `DescargaError` y **se registra como fallo del partido**; nunca cuelga el lote. |
| `PAUSA_DEFECTO_S` | `2.0` | Pausa entre partidos consecutivos (`time.sleep`), configurable con `--pausa`. Evita la ráfaga que degrada la cartelera (WAF). |
| `CHECKPOINT_DEFECTO` | `qbe_ingestion/data/reportes/checkpoint.json` | Estado reanudable del lote: `temporada`, `torneo`, rango de jornadas, `completados` (claves `temporada|torneo|id_partido`) y `ultimo_partido`. Se escribe de forma **atómica** (tmp + replace) después de cada partido. |
| `--resume` | bandera | Omite los partidos ya marcados como `completados`. Un partido en `FALLO` **no** se marca completado: se reintenta en la siguiente reanudación. Un lote que sólo omite no borra el `ultimo_partido` previo. |

* **Invariantes:** el checkpoint vive bajo un directorio ignorado por git; la ausencia de checkpoint con `--resume` equivale a lote nuevo (no aborta); la clave de reanudación incluye torneo, por lo que Apertura y Clausura no se pisan.
* **Fail-Loud:** un checkpoint ilegible se descarta (se reinicia el lote) pero se registra en el resumen; un timeout nunca se convierte en partido exitoso.
* **[SHIELD]:** `qbe_ingestion/tests/test_shield_orquestador_extraccion.py`

---

## 18. DICCIONARIO CANÓNICO DE ALIAS DE LIGA MX

### ID: `[LN-QBE-145]` Diccionario Canónico de Alias de Liga MX (`ligamx.net` → bóveda)

* **Ω (Resumen):** Traducción determinista entre el nombre de pantalla que publica `ligamx.net` y el nombre canónico que usa la bóveda OLAP (`historical_matches.home_team` / `away_team`). Es una tabla estática y cerrada: **cero fuzzy matching, cero normalización implícita, cero heurísticas**. Existe porque el Join Determinista de `[ARCH-1.5.1]` §15.3 exige coincidencia exacta de slug: `Jaguares` no es `Chiapas` y `M. Morelia` no es `Morelia`, aunque el partido sea el mismo.
* **I (Input):** `nombre_pantalla: str` — el nombre tal como lo entrega el parser `[LN-QBE-141]` (o la cartelera `[LN-QBE-142]`).
* **P (Process) [ALGO-PROTECTED] [DIRGEN-STRICT]:**
  1. **Validación de tipo:** un valor que no sea `str` aborta con `TypeError` (Fail-Loud); no se coacciona.
  2. **Búsqueda exacta:** `ALIAS_LIGAMX.get(nombre_pantalla)`. La clave es la cadena completa y literal; no hay plegado de mayúsculas, acentos, puntuación ni distancia de edición.
  3. **Fallback de identidad:** si la clave no está en el diccionario, se devuelve **el nombre original sin modificar**. El silencio no es una decisión: la ausencia de alias se manifestará como `MatchResolutionError` en el Join Determinista, nunca como una llave aproximada.
* **O (Output):** `nombre_canonico: str` — uno de los 18 nombres canónicos de la temporada 2015-2016 de la bóveda (`América`, `Atlas`, `Chiapas`, `Cruz Azul`, `Dorados`, `Guadalajara`, `León`, `Monterrey`, `Morelia`, `Pachuca`, `Puebla`, `Pumas UNAM`, `Querétaro`, `Santos Laguna`, `Tigres UANL`, `Tijuana`, `Toluca`, `Veracruz`) o el original si no hay alias.
* **Φ (Transición):** Hacia `resolver_match_id` (`[LN-QBE-144]`) dentro del orquestador `[LN-QBE-143]`; el Join no cambia su lógica, solo recibe nombres limpios.
* **Invariantes:** el diccionario es estático (se versiona con el código, no se calcula en ejecución); **todo valor** del diccionario debe existir literalmente como nombre canónico en `historical_matches`; el mapeo es función pura (misma entrada → misma salida, sin I/O, sin estado); el orden de las claves es irrelevante; ninguna clave se resuelve por aproximación.
* **Fail-Loud:** `TypeError` ante entrada no textual. Un nombre desconocido no se adivina: retorna el original y el Join Determinista aborta el partido con `MatchResolutionError`, que el orquestador registra en el resumen.
* **Deuda declarada:** el diccionario cubre las variantes **observadas** en la extracción de la temporada 2015-2016 (`Jaguares`, `M. Morelia`, `Tigres`, `Tigres de la U.A.N.L.`, `Club Tijuana`, `Pumas`, `Universidad Nacional`, `Puebla F.C.`, `Dorados de Sinaloa`). Una variante nueva que aparezca en otra temporada NO se resolverá por aproximación: se declarará como fallo de Join y exigirá una ampliación legislada del diccionario.
* **[SHIELD]:** `qbe_ingestion/tests/test_shield_orquestador_extraccion.py`

---

## 19. MOTOR DE VARIABLES CAUSALES

### ID: `[LN-QBE-146]` Motor de Derivación de Variables Causales

* **Ω (Resumen):** Función pura que convierte la línea de tiempo factual de un partido (`historical_match_events`) en el vector canónico de **32 variables** del catálogo `[LN-QBE-120]`. Deriva por conteo directo o por proximidad temporal lo que la narrativa «Jugada a Jugada» prueba, y **declara `SIN EVIDENCIA`** lo que no es inferible de eventos (posesión, xG, pases): no imputa, no modela y no interpola. Es el puente entre la evidencia causal y el script de calibración (Brier Score).
* **Delimitación de proveedores:** FootyStats es el Proveedor Primario Histórico de *momios* y *resultados*; FotMob es el Proveedor Primario de *evidencia fáctica* (32 variables). La derivación causal consume FotMob; no usa FootyStats para las 32 variables ni FotMob para momios de mercado.
* **I (Input):** `match_id: str` (llave de la bóveda) y `eventos: Sequence[Mapping]` con el contrato de `[LN-QBE-141]` (`evento_id`, `lado` ∈ {`local`,`visita`}, `tipo`, `minuto`, `minuto_agregado`, `periodo`, `orden_dom`).
* **P (Process) [ALGO-PROTECTED] [DIRGEN-STRICT]:**
  1. **Aduana:** `match_id` textual no vacío y lista no vacía; cada evento debe declarar `lado`, `tipo` y `orden_dom`. Un faltante aborta con `DerivacionError` (nunca se devuelve un vector vacío).
  2. **Conteo por lado:** se acumulan las magnitudes de conteo directo por `lado`.
  3. **Proximidad temporal (pelota parada):** un gol (`gol` o `gol_penal`) se marca como de pelota parada si el **evento inmediatamente anterior del mismo lado** es `corner` o `penal` y ocurre dentro de `5` minutos (`minuto_efectivo = minuto + minuto_agregado`; sin minuto base no hay ventana). `orden_dom` del visor es cronológico **inverso** (0 = final del partido), por lo que el «anterior» se resuelve recorriendo de mayor a menor. La regla es determinista y no usa distancia semántica. En la muestra justifica el gol de Monterrey al 10' (penal señalado al 7') y el de América al 36' (córner al 35').
  4. **Duales:** `V13` es el espejo exacto de `V07` (remates recibidos); `V22` es el espejo de `V21`.
  5. **Sin cocientes:** la narrativa no censa atajadas (el evento `atajada` es «gran atajada», no un recuento de paradas), por lo que `V18` no se imputa: se declara `SIN EVIDENCIA`.
  6. **Ensamblado:** se emite un diccionario con las 32 claves `V01`…`V32`; cada valor es `{"local": float|None, "visita": float|None}`.
* **Reglas por variable (catálogo `[LN-QBE-120]`, §2.1):**

| Variable | Regla | Estado |
|---|---|---|
| `V01` Posesión | no inferible de eventos | `SIN EVIDENCIA` |
| `V02` Toques en área | no inferible | `SIN EVIDENCIA` |
| `V03` Pases precisos | no inferible | `SIN EVIDENCIA` |
| `V04` Pases largos | no inferible | `SIN EVIDENCIA` |
| `V05` Faltas cometidas | conteo `falta` | derivada |
| `V06` xG | no inferible | `SIN EVIDENCIA` |
| `V07` Tiros al arco (SoT) | conteo `tiro_a_gol` + `gol` + `gol_penal` | derivada |
| `V08` Big chances creadas | no inferible | `SIN EVIDENCIA` |
| `V09` Big chances falladas | no inferible | `SIN EVIDENCIA` |
| `V10` xGOT | no inferible | `SIN EVIDENCIA` |
| `V11` xA | no inferible | `SIN EVIDENCIA` |
| `V12` xGA | no inferible (orden explícita) | `SIN EVIDENCIA` |
| `V13` SoTA | dual exacto de `V07` | derivada |
| `V14` Acciones defensivas | no inferible | `SIN EVIDENCIA` |
| `V15` Intercepciones | no inferible | `SIN EVIDENCIA` |
| `V16` Big chances concedidas | `FUERA DE FUENTE` en el catálogo | `SIN EVIDENCIA` |
| `V17` Goles evitados | no inferible (modelado) | `SIN EVIDENCIA` |
| `V18` Save % | no inferible: `atajada` narra «gran atajada», no un censo de paradas | `SIN EVIDENCIA` |
| `V19` Salidas / líbero | no inferible | `SIN EVIDENCIA` |
| `V20` Clean sheets | `1` si el rival anotó `0` | derivada |
| `V21` Goles a favor de pelota parada | gol precedido por `corner`/`penal` del mismo lado (≤ 5 min) | derivada |
| `V22` Goles recibidos de pelota parada | dual de `V21` | derivada |
| `V23` Córners | conteo `corner` | derivada |
| `V24` Penales | conteo `penal` (señalados a favor) | derivada |
| `V25` Tarjetas | conteo `tarjeta_amarilla` + `tarjeta_roja` | derivada |
| `V26` Récord H2H | requiere historia | `SIN EVIDENCIA` |
| `V27` ΔG H2H | requiere historia | `SIN EVIDENCIA` |
| `V28` Récord visitante en sede | requiere historia | `SIN EVIDENCIA` |
| `V29` Altitud | dato de fixture | `SIN EVIDENCIA` |
| `V30` Días de descanso | dato de calendario | `SIN EVIDENCIA` |
| `V31` Forma 5P | requiere historia | `SIN EVIDENCIA` |
| `V32` Varianza ΔxPTS | requiere modelo | `SIN EVIDENCIA` |

* **O (Output):** `dict[str, dict[str, float | None]]` con las 32 claves. **9 derivadas** (`V05`, `V07`, `V13`, `V20`, `V21`, `V22`, `V23`, `V24`, `V25`), **23 `SIN EVIDENCIA`**. Persistencia: una fila por partido en `historical_match_causal_vars` (columnas `vNN_local` / `vNN_visita`, más `sin_evidencia`, `derivadas`, `fuente_datos`, `cargado_utc`).

* **Φ (Transición):** Hacia el script de calibración (Brier Score) y la ingeniería de variables del observatorio.
* **Invariantes:** función pura (sin I/O, sin red, sin BD, sin reloj); `qbe_core` no importa `sqlalchemy`, `requests`, `playwright`, `src.storage` ni `src.ingestion`; las 32 claves siempre están presentes; `None` ≠ `0.0` (ausencia declarada vs. cero factual); el conteo es del **lado**, nunca del partido agregado.
* **Fail-Loud:** lista vacía, `match_id` inválido, evento sin `lado`/`tipo`/`orden_dom`, o `lado` fuera del dominio ⇒ `DerivacionError`.
* **Limitación declarada:** superada por enmienda del Director (Sprint 44): `V07`/`V13` **incluyen `gol_penal`** como remate al arco. En la muestra, América 3-3 Monterrey pasa de 17 a **18 remates** (10 local / 8 visita).
* **[SHIELD]:** `qbe_core/tests/test_shield_derivacion_causal.py`

### 19.1 Fuente alterna declarada: `matchDetails` de FotMob (extracción histórica masiva)

Enmienda del Director (Sprint 48). El motor anterior deriva lo que la narrativa «Jugada a Jugada» prueba; esta fuente paralela toma el bloque estadístico oficial del partido publicado por FotMob (`content.stats.Periods.All.stats`) y reconstruye el mismo vector de 32 claves. **Misma tabla, mismos slots, misma regla de `NULL` honesto**; cambia la procedencia (`fuente_datos = 'FOTMOB_MATCHDETAILS'`).

**Reparto canónico de las 32 variables:**

| Bloque | Variables | N |
|---|---|---:|
| FotMob directas (tablero publicado) | `V01`–`V15`, `V17`–`V25` | 24 |
| FotMob contexto (historia de la bóveda) | `V26`, `V27`, `V28`, `V31` | 4 |
| Fixture / estáticas | `V29`, `V30` | 2 |
| Derivada | `V32` | 1 |
| Fuera de fuente | `V16` | 1 |

**Mapeo exacto por variable:**

| Variable | Fuente | Clave / regla determinista |
|---|---|---|
| `V01` | FotMob | `BallPossesion` (%). |
| `V02` | FotMob | `touches_in_opp_box` (sólo si el partido lo publica; si no, `NULL`). |
| `V03` | FotMob | `accurate_passes`, entero inicial de `"N (P%)"`. |
| `V04` | FotMob | `long_balls_accurate`, entero inicial de `"N (P%)"`. |
| `V05` | FotMob | `fouls`. |
| `V06` | FotMob | `expected_goals` (ausente antes de la era xG ⇒ `NULL`). |
| `V07` | FotMob | `ShotsOnTarget`. |
| `V08` | FotMob | `big_chance`. |
| `V09` | FotMob | `big_chance_missed_title`. |
| `V10` | FotMob | `expected_goals_on_target` (ausente ⇒ `NULL`). |
| `V11` | FotMob | `expected_assists` (ausente ⇒ `NULL`). |
| `V12` | FotMob | `expected_goals_conceded`; si no se publica, dual de `V06` (`xGA_local ≡ xG_visita`). Sin xG ⇒ `NULL`. |
| `V13` | Identidad | Dual exacto de `V07`: `SoTA_local ≡ SoT_visita`. |
| `V14` | Identidad | `tackles + clearances + interceptions` (suma declarada de la misma familia). |
| `V15` | FotMob | `interceptions`. |
| `V16` | — | `FUERA DE FUENTE` permanente (`[LN-QBE-120]` §2.2 regla 2). |
| `V17` | FotMob | `goals_prevented` (ausente ⇒ `NULL`). |
| `V18` | Identidad | `keeper_saves / SoTA × 100`; denominador `0` ⇒ `NULL` (nunca `0 %` fabricado). |
| `V19` | FotMob | `total_keeper_sweeper` (ausente ⇒ `NULL`). |
| `V20` | Identidad | `1` si el rival no anotó, `0` si anotó; sin marcador ⇒ `NULL`. |
| `V21` | FotMob | `_set_piece_goals_team` (ausente ⇒ `NULL`). |
| `V22` | FotMob | `_set_piece_goals_conceded_team` (ausente ⇒ `NULL`). |
| `V23` | FotMob | `corners`. |
| `V24` | FotMob | `penalty_won` (ausente ⇒ `NULL`). |
| `V25` | Identidad | `yellow_cards + red_cards` (convención sellada del catálogo). |
| `V26` | Bóveda | Tasa de victorias del club en la serie H2H **anterior al kickoff**. |
| `V27` | Bóveda | Diferencial medio de goles en la serie H2H **anterior al kickoff**. |
| `V28` | Bóveda | Tasa de victorias del club en la sede del anfitrión (serie previa). |
| `V29` | Catálogo | `ΔAlt⁺ = max(0, altitud_anfitrión − altitud_visita)` desde `CATALOGO_ALTITUDES_LIGAMX` (misma magnitud en ambos lados con signo opuesto). |
| `V30` | Bóveda | `ΔDías = descanso_local − descanso_visita`, medido contra el último partido previo de cada club. |
| `V31` | Bóveda | Puntos obtenidos en los 5 partidos previos del club. |
| `V32` | Derivada | Varianza poblacional de los puntos de esos mismos 5 partidos; `NULL` con menos de 2 observaciones. |

* **Cero fuga temporal [INVARIANTE]:** `V26`–`V32` se calculan exclusivamente con partidos estrictamente anteriores al kickoff. El partido evaluado jamás participa de su propio contexto, aunque el proveedor publique la serie completa.
* **Fail-Loud:** un `matchDetails` sin `content.stats.Periods.All` no produce fila parcial: el partido se declara fallido y se reporta.
* **Φ (Transición):** hacia `[LN-QBE-150]` (cálculo de P') y hacia el Alpha masivo del Observatorio.
* **[SHIELD]:** `tests/shield/test_shield_fotmob_32_vars.py` (cobertura del catálogo) y `tests/shield/test_shield_extraccion_historica_fotmob.py`.

---

## 20. CALIBRACIÓN EMPÍRICA Y PERTURBACIÓN DE VARIABLES

### ID: `[LN-QBE-147]` Motor de Calibración y Perturbación de Variables Causales

* **Ω (Resumen):** Motor puro que mide la calidad predictiva del vector causal de `[LN-QBE-146]` contra los resultados reales de la bóveda (Brier Score multiclase) y busca, por **perturbación controlada** de las variables dentro de sus límites físicos, la combinación de ajustes que más reduce el error. Emite un acta auditable con el Brier base, el optimizado y el impacto de cada variable. No entrena un modelo nuevo: calibra el **puente** entre la evidencia causal y la distribución soberana.
* **I (Input):** lote de partidos con `vector` causal (32 variables por lado), marcador real (`home_goals`, `away_goals`), temporada, `medias` de `V07`/`V13` del lote y `MU_LIGA` (goles por equipo y partido). Las cuotas se aceptan como **referencia de mercado**, nunca como insumo de la optimización.
* **P (Process) [ALGO-PROTECTED] [DIRGEN-STRICT]:**
  1. **Puente de calibración (único canal legislado):** con `ataque(lado) = (V07+1)/(media_V07+1)` y `defensa(lado) = (V13+1)/(media_V13+1)`,
     `λ_local = MU_LIGA · ataque(local)/defensa(visita)` y `λ_visita = MU_LIGA · ataque(visita)/defensa(local)`, acotadas a `[0.05, 6.0]`.
  2. **Distribución soberana base:** `calcular_matriz_dixon_coles` + `colapsar_matriz_a_simplex` (`[VAULT-CORE-004]`). No se reimplementa la matemática del núcleo.
  3. **Brier Score base:** media del lote de `Σ₃ (pᵢ − yᵢ)²` por partido (0 a 2).
  4. **Perturbación controlada:** búsqueda voraz y determinista de factores multiplicativos **globales** por pareja (variable, lado), con `factores ∈ {0.85, 1.15}` y hasta 20 pasos. El factor **acumulado** por pareja se acota a la banda física `[0.5, 2.0]` (impide anular una variable y degenerar el puente). Cada candidato se acota además a los límites físicos de la variable y sólo se acepta si reduce **estrictamente** el Brier del lote.
  5. **Acta:** secuencia completa de movimientos (`brier_previo`, `brier_nuevo`, `delta`), impacto acumulado por variable ordenado por reducción, `top3` y factores finales.
* **Límites físicos (invariante):** `V05 ≤ 40`, `V07/V13 ≤ 25`, `V21/V22 ≤ 10`, `V23 ≤ 20`, `V24 ≤ 5`, `V25 ≤ 15`; todos `≥ 0`; factor acumulado por pareja en `[0.5, 2.0]`. `V20` es binaria y queda fuera de la perturbación. Ninguna perturbación puede producir valores negativos, posesión > 100 % ni remates imposibles.
* **O (Output):** acta `{brier_base, brier_optimizado, delta, mejora_relativa, movimientos, impacto_por_variable, top3, factores_finales}`; en la CLI se materializa en `data/reportes/calibracion_2015_2016.json`.
* **Φ (Transición):** Hacia la verificación fuera de muestra (temporada siguiente) y hacia el ajuste del puente en `[LN-QBE-146]`.
* **Invariantes:** función pura y determinista (mismas entradas ⇒ mismo acta); el optimizador **nunca** empeora el Brier base (los movimientos se aceptan sólo si mejoran); `qbe_core` no importa `sqlalchemy`, `requests`, `playwright`, `src.storage` ni `src.ingestion`; las cuotas no participan en la optimización.
* **Fail-Loud:** lote vacío, marcador no entero o negativo, vector sin `V07`/`V13`, `MU_LIGA ≤ 0`, medias negativas o factores no positivos ⇒ `CalibracionError`.
* **Limitación declarada:** la calibración es **in-sample** (misma temporada 2015-2016); la mejora del Brier mide ajuste al puente, no capacidad predictiva fuera de muestra. El puente sólo canaliza `V07`/`V13`; las demás variables perturbables se exploran y, si no tienen canal, su delta es `0.0` y así se declaran.
* **[SHIELD]:** `qbe_core/tests/test_shield_calibracion.py`

---

## 21. CONSENSO PONDERADO Y RADAR DE SINDICATOS

### ID: `[LN-QBE-148]` Motor de Consenso Ponderado (Wisdom of the Crowds)
*   **Ω (Resumen):** Calcular el Símplex consensuado del mercado aplicando de-vig y pesos dinámicos basados en la precisión histórica.
*   **Delimitación de proveedores:** El Brier Score y el Alpha históricos se calculan sobre FootyStats (momios + resultados de partidos). La distribución Q-BE se calibra con FotMob (32 variables). Los dominios no se mezclan: FootyStats no alimenta las 32 variables y FotMob no alimenta momios de mercado.
*   **I (Input):** Momios de los casinos desde `odds_ticks`.
*   **P (Process):**
    1. Aplicar `[LN-QBE-007-C]` (Vig-Free De-biasing) a cada casino.
    2. Asignar pesos ($W_i$) basados en el Brier Score histórico (Opción B).
    3. Calcular $\Delta^2 = \sum (P_{casino\_i} \cdot W_i)$.
*   **Challenger aislado (Sprint 47) [INVARIANTE]:** Q-BE opera como Challenger independiente y queda estrictamente prohibida su participación en el cálculo del Consenso de Mercado. El Consenso agrupa únicamente a los casinos. La distribución Q-BE se publica como fila de solo lectura (peso `—`) y se mide contra el Consenso vía Alpha; jamás entra en $\Delta^2$, ni siquiera cuando comparte el mismo set de datos, la misma jornada o el mismo payload de cuotas.
*   **O (Output):** Distribución de probabilidad consensuada en el Símplex $\Delta^2$.
*   **Agregación Brier:** La agregación de Brier por jornada se realizará mediante el promedio aritmético de los Brier individuales de los partidos. Los partidos sin evidencia para una fuente seleccionada son excluidos del promedio, no imputados como cero.
*   **Agregación global (Sprint 47) [INVARIANTE]:** El Brier Score Global se calcula sobre la totalidad de los partidos válidos, no mediante el promedio aritmético de los Brier de cada jornada. Los KPIs superiores transcriben el agregado del universo completo de partidos finalizados (normalizado 3N); el promedio por jornada describe exclusivamente el bloque de esa jornada y nunca se re-promedia para fabricar el global.
*   **Fuente de verdad histórica:** El Brier Score histórico del mercado se calculará exclusivamente sobre el universo de partidos finalizados (histórico masivo). Queda prohibido utilizar muestras parciales de ticks en vivo para calcular métricas de rendimiento histórico (Brier/Alpha).
*   **Brier histórico Q-BE (Sprint 48):** El Brier Score histórico de Q-BE se calcula consumiendo `historical_sovereign_distributions`. La muestra de comparación son los partidos donde coexisten momios de FootyStats y distribución P'. Un partido sin distribución P' queda fuera del promedio de Q-BE —no se imputa como cero ni se extrapola— y sin coexistencia el Alpha se declara `SIN EVIDENCIA`. El filtro «Todas» agrega el universo histórico completo; el desglose por jornada no se publica en ese modo porque el histórico masivo no porta número de jornada.
*   **Deuda técnica (FootyStats):** Las cuotas históricas actuales (FootyStats) demuestran un Brier Score ineficiente (Alpha Q-BE +66%). Queda prohibido usar estas cuotas para simular ROI histórico. Se requiere la integración de un nuevo proveedor de cuotas históricas de calidad o la acumulación de ticks propios vía Daemon.
*   **Φ (Transición):** Consumidor activo: `qbe_core` / `qbe_observatory`.

### ID: `[LN-QBE-149]` Motor de Detección de Rupturas de Consenso (Radar de Sindicatos)
*   **Ω (Resumen):** Detectar movimientos anómalos en los momios que sugieran intervención de capital informado.
*   **I (Input):** Serie histórica de `odds_ticks` y la distribución de consenso.
*   **P (Process):** Si la tasa de cambio (velocidad/magnitud) de un casino excede `CONST_DELTA_SINDICATO_PCT` y rompe la tendencia del Consenso Ponderado, emite alerta.
*   **O (Output):** Flag de alerta en el DTO de la Mesa de Apuestas.

---

## 22. VISOR DE CONSENSO — MOMIO JUSTO

**Nodos:** `[LN-QBE-011]` / `[DES-QBE-076]`

> El Visor de Consenso de Mercado debe mostrar el Momio Justo calculado como el inverso de la probabilidad (1/P) para la distribución Q-BE y el Consenso Ponderado, manteniendo los momios brutos para los casinos.

*   **Fail-Loud:** si `P` es `None`, `0.0` o no representable, el Momio Justo es `None` y la UI muestra `—`; nunca `Infinity` ni un valor inventado.

---

## 23. ESTÁNDAR DE BRIER MULTICLASE 3N

### ID: `[LN-QBE-100]` Motor de Calibración Factual de Temporada y Evaluación Multicategórica de Brier

> **Estándar de Brier Multiclase:** El Brier Score reportado en todas las vistas del ecosistema DEBE ser normalizado por el número de clases (fórmula `3N`: dividir entre 3). Queda prohibido reportar el Brier crudo o suma de cuadrados sin normalizar.

*   **Fuente única:** `/visor` y `/consenso` consumen el mismo reporte de Auditoría para el Brier de mercado.
*   **Histórico FootyStats:** el Brier de `historical_matches` se normaliza igualmente por 3 antes de mostrarse; el crudo solo se conserva en las sondas forenses de `scripts/auditoria/historico/`.

---

## 24. DISTRIBUCIONES HISTÓRICAS Y ALPHA MASIVO

### ID: `[LN-QBE-150]` Motor de Cálculo de Distribuciones Históricas (P')

* **Ω (Resumen):** Materializar el símplex soberano P' de todo el corpus histórico, partido por partido, leyendo el vector causal de 32 variables (`historical_match_causal_vars`, `[LN-QBE-146]` §19.1), reconstruyendo el registro fáctico **pre-kickoff** de cada encuentro y delegando la matemática en la función sellada `generar_distribucion_soberana` de `qbe_core` (Dixon-Coles 2D → colapso al Símplex Δ² → Cláusula de André). Sin P' histórica no existe Alpha masivo: el Observatorio sólo podía comparar Q-BE contra mercado en la muestra de control viva.
* **Delimitación de proveedores (`[ARCH-1.4.77]`):** los momios y resultados provienen de FootyStats (`historical_matches`); la evidencia fáctica proviene de FotMob (`historical_match_causal_vars`). Este nodo **no mezcla dominios**: sólo cruza ambos linajes por `match_id` al publicar el Alpha.
* **I (Input):** `qbe_observatorio/data/qbe_historico.db` — `historical_match_causal_vars` (vector de 32 variables) y `historical_matches` (marcadores y calendario). No consume red.
* **P (Process) [DIRGEN-STRICT]:**
  1. **Reconstrucción pre-kickoff:** para cada club se agregan `pj`, `gf` y `gc` con **exclusivamente** los partidos de la misma temporada anteriores al kickoff; `xg`/`xga` se suman de `V06`/`V12` de esos mismos partidos cuando el proveedor los publica, y `0.0` en caso contrario (el motor sellado cae a la ancla de goles, nunca a un valor fabricado).
  2. **Contexto:** `V29` (ΔAlt⁺) y `V30` (ΔDías) viajan al motor como `delta_alt_metros` y `delta_descanso_dias`; la serie H2H previa viaja como `h2h_matches` con `dias_antiguedad`, `goles_local` y `goles_visita` en la perspectiva del fixture.
  3. **Aduana de suficiencia `S(I_i)`:** con menos de 3 partidos previos legibles por club, el partido **se salta** y se declara en el reporte. No se persiste una distribución uniforme disfrazada de cálculo.
  4. **Delegación:** `generar_distribucion_soberana(match_id, raw_match_data, delta_alt_metros, delta_descanso_dias)`. Ninguna fórmula se reimplementa fuera de `qbe_core`.
  5. **Persistencia:** `INSERT OR REPLACE` idempotente en `historical_sovereign_distributions` (`[ARCH-1.5.1]` §15.5) dentro de `BEGIN IMMEDIATE`, con respaldo WORM previo y `PRAGMA quick_check` al cierre.
* **O (Output):** una fila por partido operable en `historical_sovereign_distributions` con `p_local`/`p_empate`/`p_visitante`, `lambda_home`/`lambda_away`, `phi_lead2_*`, `epistemic_delta`, `delta_epist`, `origen_factores`, `pj_home`/`pj_away` y `audit_trace_json` completo. Reporte de consola con generadas, saltadas y motivo de cada descarte.
* **Φ (Transición):** hacia el **Alpha masivo** del Observatorio (`[LN-QBE-148]`): el símplex P' histórico se cruza con los momios de FootyStats (o con la captura Q-BE Live) para calcular el Alpha por partido y su Brier 3N (`[LN-QBE-100]`) sobre el universo completo, no sobre una muestra de control.
* **Invariantes:** cero fuga temporal (el resultado del partido evaluado jamás entra en su propio registro de entrada); cero imputaciones; `qbe_core` se importa y no se modifica; `sovereign_distributions` (tabla viva) no se lee ni se escribe; el símplex persistido suma 1 con tolerancia 1e-9.
* **Fail-Loud:** bóveda inexistente, tabla de destino sin DDL aplicable, o `PRAGMA quick_check` distinto de `ok` ⇒ código de salida 1 y traza. Un partido sin `S(I_i)` no es un fallo del motor: es un descarte declarado.
* **[SHIELD]:** `tests/shield/test_shield_distribuciones_historicas.py`.
