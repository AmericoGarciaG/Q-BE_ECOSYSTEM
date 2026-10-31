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

$$ \gamma_{\text{home}} = \bar{\gamma}_{\text{base}} + \Delta\gamma_{\text{plaza}} + \text{bono}_{\text{alt}} + \text{efecto}_{\text{descanso}} $$

con $\bar{\gamma}_{\text{base}} = 0.15$ y $\kappa_{\text{net}} = 0.25$ como techo de compresión $\tanh$.

### 7.3 Breakeven dinámico

$$ \theta^* = \frac{O_{\text{fav}}}{O_{\text{fav}} - 1} $$

es el umbral de indiferencia de cobertura. No es una constante universal: depende del momio del favorito y del régimen de pago anticipado.

### 7.4 Morfología del símplex

`[LN-QBE-059]` particiona $\Delta^2$ en ocho familias morfológicas con umbral maestro $\Gamma_{\text{base}} = 0.67$. Los umbrales `0.70` y `0.75` son modos de UI, no constantes del motor.

### 7.5 Kelly y hard-caps

`[LN-QBE-070]` aplica Kelly fraccional atenuado (`0.25`), hard-cap individual (`0.08`), cap de cartera (`0.25`) y piso de ventanilla (`$2.00`). La cota underdog del 1.5% es un techo adicional de la Familia R.

---

## 8. DEROGACIONES Y TOMBSTONES

| Elemento | Estado | Vigente |
|---|---|---|
| Catálogo 12 dimensiones × 44 variables (`[LN-QBE-101]`) | `[DEROGADO]` | 6 × 32 (`[LN-QBE-120]`). |
| `V39`, `V40`, `V41` | `[DEROGADO]` | `V26`, `V27`, `V28`. |
| `𝒯_Shk`, `𝒯_H2H`, `𝒯_Tra` como familias separadas | `[DEROGADO]` | Consolidadas en `𝒯_Ctx`. |
| Semáforo `EPIST` en el micro-HUD | `[DEROGADO]` visualmente | Backend lo conserva; UI muestra tetralogía fáctica. |
| Lectura del visor sobre la base viva | `[DEROGADO]` | Snapshot atómico de solo lectura. |

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

_Total: 125 identificadores._


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
