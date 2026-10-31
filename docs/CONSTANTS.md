# Q-BE ECOSYSTEM — CONSTANTS BOOK

**Versión:** 2.0 — Ecosystem Edition  
**Estado:** `[ALGO-PROTECTED]` — Bóveda de Constantes Inmutables  
**Proyecto:** `Q_BE_ECOSYSTEM`  
**Autoridad Suprema:** Américo García Guerrero (Director Humano)  
**Marco:** Kybern Industrial Framework v13.5  
**Expediente:** `SPRINT-FASE4-MIGRACION-REFLEXIVA-BG-04`  
**Fecha:** 2026-10-28  
**Transformación:** consolidación de constantes y anexo de altitudes; rutas reancladas a los cuatro pilares.

---

## 1. DOMINIO TEMPORAL Y DECAIMIENTO HISTÓRICO (H2H)

| Símbolo | Nombre Canónico | Valor Exacto | Unidad | Nodo Dueño | Dominio de Validez | Prohibición de Reúso |
|:---:|---|---|:---:|:---:|---|---|
| $\tau_{\text{H2H}}$ | Vida Media Temporal H2H | `180.0` | Días | `[LN-QBE-020]` | Ventana de enfrentamientos directos | No usar como ventana de forma reciente |
| $\kappa_{\text{decay}}$ | Constante de Decaimiento H2H | $\frac{\ln(2)}{180.0} \approx 0.00385098$ | $\text{días}^{-1}$ | `[LN-QBE-020]` | Exponente del kernel $e^{-\kappa \Delta t}$ | **PROHIBIDO** usar como escala de damping |
| $N_{\text{H2H}}^{\max}$ | Muestra Máxima H2H | `5` | Partidos | `[LN-QBE-020]` | Enfrentamientos directos evaluados | No exceder sin calibración de varianza |
| $w_{\text{H2H}}^{\text{amp}}$ | Amplitud Máxima del Peso H2H en la Modulación Poisson | `0.5000` ($50.0\%$) | Adimensional | `[LN-QBE-040]` | Factor de mezcla $w_{\text{H2H}} = \max\!\left(w^{\text{piso}},\; w^{\text{amp}} \cdot e^{-\kappa_{\text{decay}} \Delta t}\right)$ en `qbe_core/src/core/poisson.py` | **PROHIBIDO** usar como peso de confianza en UI, como escala de damping ni como umbral de descarte |
| $w_{\text{H2H}}^{\text{piso}}$ | Piso de Influencia H2H con Antecedente Presente | `0.1500` ($15.0\%$) | Adimensional | `[LN-QBE-040]` | Cota inferior de la mezcla cuando existe antecedente H2H real (la ausencia total se rige por la Ley Zero-H2H `[LN-QBE-020-B]`) | **PROHIBIDO** usar como umbral de viabilidad, de descarte o de morfología Γ |
| $\tau_{\text{H2H, deep}}$ | Vida Media Multianual H2H | `540.0` | Días | `[LN-QBE-020]` | Ventana longitudinal interanual (~1.5 años) | Prohibido usar como ventana de forma reciente |
| $\kappa_{\text{H2H, deep}}$ | Constante de Decaimiento H2H Multianual | $\frac{\ln(2)}{540.0} \approx 0.00128338$ | $\text{días}^{-1}$ | `[LN-QBE-020]` | Exponente $e^{-\kappa \Delta t}$ para 5 partidos históricos | Prohibido confundir con $\kappa_{\text{decay}}$ corta |

---

## 2. DOMINIO DE FÍSICA ESTOCÁSTICA Y COMPRESIÓN DE GOLES

| Símbolo | Nombre Canónico | Valor Exacto | Unidad | Nodo Dueño | Dominio de Validez | Prohibición de Reúso |
|:---:|---|---|:---:|:---:|---|---|
| $\mu_{\text{liga}}$ | Media Goles Liga MX | `2.65` (Liga MX) / `2.60` (Gral) | Goles / 90' | `[LN-QBE-089]` | Parámetro macro de liga | No usar como expectativa individual |
| $\bar{\gamma}_{\text{home}}$ | Ventaja Media Incondicional | `0.15` | Log-Ratio | `[VAULT-CORE-001]` | Intercepto base en ecuación de ligadura | No alterar sin análisis de 3 temporadas |
| $\kappa_{\text{net}}$ | Techo de Compresión $\tanh$ (ABSOLUTO) | $0.2500$ | Adimensional | `[VAULT-CORE-001]` | Damping hiperbólico de factores $A, D$; $\sigma_{\text{liga}}$ **vestigial** en firma (escalera $2.5\cdot\sigma$ derogada, `VAR-2026-LIVE-AUDIT-J11`/V-2) | **PROHIBIDO** confundir con $\kappa_{\text{decay}}$ |
| $\sigma_{\text{liga}}$ | Dispersión Base de Factores | `1.00` | Desv. Estándar | `[VAULT-CORE-001]` | Escala de factores centrados en cero | Inmutable por diseño |
| $\text{peso}_{xG}$ | Ponderación Señal Calidad | `0.65` | Fracción | `[LN-QBE-035-B]` | Mezcla Opta $xG / GF$ | La suma con $\text{peso}_{GF}$ debe ser $1.0$ |
| $\text{peso}_{GF}$ | Ponderación Señal Volumen | `0.35` | Fracción | `[LN-QBE-035-B]` | Mezcla Opta $xG / GF$ | La suma con $\text{peso}_{xG}$ debe ser $1.0$ |
| $w_{\text{sede}}$ | Ponderación de Rendimiento en Sede | `0.5000` ($50.0\%$) | Fracción | `[LN-QBE-038]` | Mezcla entre promedio general y split local/visita | Inmutable por diseño |
| $\Delta\gamma_{\text{plaza}}^{\text{max}}$ | Techo de Intimidación de Plaza | `0.1000` | Log-Ratio | `[LN-QBE-038]` | Bono máximo admisible por localía extrema | No exceder sin prueba de 5 torneos |

### Catálogo Canónico de Fortaleza de Plaza ($\Delta\gamma_{\text{plaza}}$)
* `tigres-uanl` (Estadio Universitario / "El Volcán"): `+0.0700`
* `deportivo-toluca` (Estadio Nemesio Diez / "La Bombonera"): `+0.0600`
* `pumas-unam` (Estadio Olímpico Universitario / "CU"): `+0.0500`
* `atlas-fc` / `atlas` (Estadio Jalisco): `+0.0400`
* `club-america` / `chivas-guadalajara` / `rayados-de-monterrey`: `+0.0400`
* Plazas estándar / neutrales: `0.0000`

### Cotas de Admisibilidad de Margen Comercial (Overround)
| Símbolo | Nombre Canónico | Valor Exacto | Dominio de Validez |
|:---:|---|:---:|:---:|
| $S_{\min}$ | `OVERROUND_MIN_ADMISIBLE` | `0.8500` | Rechazo por arbitraje imposible o cuota duplicada |
| $S_{\max}$ | `OVERROUND_MAX_ADMISIBLE` | `1.3000` | Rechazo por cuota usuraria o mercado suspendido |

### Cotas Diagnósticas del Pre-Vuelo de Coherencia Relacional (Auditor `[ARCH-1.4.34]`)
| Símbolo | Nombre Canónico | Valor Exacto | Unidad | Nodo Dueño | Dominio de Validez | Prohibición de Reúso |
|:---:|---|---|:---:|:---:|---|---|
| $\text{Techo}_{xG}^{\text{plaza}}$ | `TECHO_XG` | `2.5000` | xG | `[LN-QBE-040-B]` + Decreto `VAR-2026-PREFLIGHT-LEGITIMATE-ENVELOPE` (A1) | Límite de escala física de Liga MX: $\lambda_{\max} > 2.5000$ ⇒ 🔴 (`DISCREPANCIA`) en el semáforo del auditor | **PROHIBIDO** usar como cota del motor, como clamp de intensidad o como umbral de morfología Γ |
| $\text{Techo}_{xG}^{\text{anti-res}}$ | `TECHO_XG_ANTIRESONANCIA` | `1.8600` | xG | `[LN-QBE-040-B]` | Frontera inferior de la banda de vigilancia del auditor: $\lambda_{\max} \in (1.8600, 2.5000]$ ⇒ 🟡 (`ADVERTENCIA`) | **PROHIBIDO** usar como umbral de descarte o de cuarentena |
| $\text{TVD}_{\max}$ | `TVD_MAX` | `0.2200` | Variación Total | `[ARCH-1.4.34]` + Decreto `VAR-2026-PREFLIGHT-LEGITIMATE-ENVELOPE` §2 | Divergencia informativa modelo↔mercado: $\text{TVD} > 0.2200$ ⇒ 🟡 (búsqueda de Alpha, **jamás** 🔴) | **PROHIBIDO** usar como umbral de exclusión de boletos o de cartera |
| $\text{TVD}_{\text{vig}}$ | `TVD_VIGILANCIA` | `0.1500` | Variación Total | `[ARCH-1.4.34]` | Banda de vigilancia diagnóstica $(0.1500, 0.2200]$ | No confundir con $\tau_{\text{disp}}$ (`0.12`, discrepancia inter-modelos) |

> **Addendum del Decreto `VAR-2026-PREFLIGHT-LEGITIMATE-ENVELOPE` (2026-10-13):** las cuatro cotas
> anteriores son **umbrales de OBSERVABILIDAD del auditor** (semáforo de presentación), no parámetros
> del motor estocástico. La garantía analítica de `[LN-QBE-040-B]` ($\lambda_H \le 1.8600$ xG en
> duelos equilibrados de liga) y el clamp canónico del plano de intensidades permanecen intactos: el
> semáforo no re-calibra la física, sólo amplía su banda de reporte para no castigar asimetrías
> legítimas de plaza ni divergencias de valor.

| Símbolo | Nombre Canónico | Valor Exacto | Unidad | Nodo Dueño | Dominio de Validez | Prohibición de Reúso |
|:---:|---|---|:---:|:---:|---|---|
| $\varepsilon_{\text{ort}}$ | Tolerancia de Singularidad Ortogonal | `1e-5` ($0.00001$) | Adimensional | `[LN-QBE-039]` | Umbral de norma para descartar variables colineales | Prohibido usar como cota bancaria |
| $\|\mathcal{A}^*\|_{\max}$ | Techo de Norma de Potencial Ofensivo | `1.0000` | Desv. Estándar | `[LN-QBE-039]` | Límite superior del espacio latente $\mathbb{H}_{\text{att}}$ | Inviolable (Anti-Resonancia) |
| $\|\mathcal{D}^*\|_{\max}$ | Techo de Norma de Resistencia Defensiva | `1.0000` | Desv. Estándar | `[LN-QBE-039]` | Límite superior del espacio latente $\mathbb{H}_{\text{def}}$ | Inviolable (Anti-Resonancia) |
| $\|\mathcal{C}^*\|_{\max}$ | Techo de Norma de Contexto y Plaza | `0.2500` | Log-Ratio | `[LN-QBE-039]` | Límite superior del espacio latente $\mathbb{H}_{\text{ctx}}$ | Inviolable (Anti-Resonancia) |

### Parámetros de Cobertura Dinámica (Dutching con Rendimiento)
| Símbolo | Nombre Canónico | Valor Exacto | Unidad | Nodo Dueño | Dominio de Validez |
|:---:|---|:---:|:---:|:---:|---|
| $\delta_{\text{def}}$ | `DELTA_DUTCHING_DEF` | `0.0000` | Ratio | `[LN-QBE-077-B]` | Modo Defensivo (V=0 exacto) |
| $r_{\text{bal}}$ | `RATIO_DELTA_BAL` | `0.5000` | Fracción | `[LN-QBE-077-D]` | 50% del delta de isorrendimiento |
| $\text{Margen}_{\delta}$ | `FACTOR_SEGURIDAD_DELTA_MAX` | `0.9500` | Fracción | `[LN-QBE-077-C]` | Techo de seguridad sobre δ_max |

### Invariantes Constitucionales de Cobertura Dinámica (VIII-49 a VIII-54)
* **Invariante VIII-49 (Cota de Viabilidad Analítica):** $\delta < (O_{\text{emp}} / \theta^*) - 1.0000$ estricto; prohibido anular la ganancia del favorito.
* **Invariante VIII-50 (No Negatividad del Seguro):** $\delta \ge 0.0000$ obligatorio; prohibido diseñar coberturas con pérdida ante empate.
* **Invariante VIII-51 (Condición de Existencia de Isorrendimiento):** Exige $(1/O_{\text{fav}}) + (1/O_{\text{emp}}) < 1.0000$.
* **Invariante VIII-52 (Monotonía del Gasto de Seguro):** $\delta_1 < \delta_2 \implies B_{\text{seg}}(\delta_1) < B_{\text{seg}}(\delta_2)$.
* **Invariante VIII-53 (Piso Legal Inviolable en Ambas Piernas):** $B_{\text{seg}} \ge \$2.00\text{ MXN}$ y $B_{\text{prio}} \ge \$2.00\text{ MXN}$.
* **Invariante VIII-54 (Trazabilidad Contractual de δ):** Toda orden en cartera debe explicitar en JSON el parámetro $\delta$ y los ROIs proyectados de favorito y empate.



### Parámetros Canónicos de Correlación Dixon-Coles Dinámica ($\rho$ Táctica)
| Símbolo | Nombre Canónico | Valor Exacto | Unidad | Nodo Dueño | Dominio de Validez | Prohibición de Reúso |
|:---:|---|---|:---:|:---:|---|---|
| $\rho_{\text{base}}$ | `RHO_BASE` | `-0.0500` | Adimensional | `[LN-QBE-040-C]` | Partidos abiertos: $\lambda_H + \lambda_A > 2.6500$ xG | **PROHIBIDO** usar como cota de descarte, cuarentena o umbral de triaje |
| $\rho_{\text{táctica}}$ | `RHO_TACTICA_DEFICIT` | `-0.1200` | Adimensional | `[LN-QBE-040-C]` | Partidos cerrados: $\lambda_H + \lambda_A \le 2.6500$ xG | **PROHIBIDO** usarlo fuera de la frontera táctica o como constante universal |
| $\Sigma_{\text{corte}}$ | `LAMBDA_SUMA_CORTE_TACTICO` | `2.6500` | xG | `[LN-QBE-040-C]` | Frontera de conmutación de $\rho$ (coincide con $\mu_{\text{liga}}$ canónico de Liga MX) | **PROHIBIDO** reutilizarlo como umbral de morfología Γ o de rechazo de mercado |

> **Cláusula de admisibilidad heredada (`[VAULT-CORE-004]` §5.16.1, preservada verbatim):** ambos valores
> de $\rho$ circulan por las cotas analíticas $\rho_{\text{adm}} \in [-\min(1/\lambda_H, 1/\lambda_A),\ \min(1, 1/(\lambda_H\lambda_A))]$
> antes de entrar al factor $\tau(x, y)$, por lo que el Teorema de No-Negatividad Estricta (Invariante I13)
> y la renormalización sobre el retículo $[0, 5]$ permanecen inviolados. Un $\rho = 0.0000$ **explícito**
> desactiva la corrección Dixon-Coles (escape hatch de auditoría); cualquier otro $\rho$ explícito se
> transcribe verbatim sin conmutación de régimen.

## 3. DOMINIO DE CONTRACCIÓN BAYESIANA DE FORMA (10 PARTIDOS)

| Símbolo | Nombre Canónico | Valor Exacto | Unidad | Nodo Dueño | Dominio de Validez | Prohibición de Reúso |
|:---:|---|---|:---:|:---:|---|---|
| $\rho_{\text{estable}}$ | Peso Ancla Macro (Sin Shock) | `0.55` | Fracción | `[LN-QBE-036]` | Contracción Normal-Normal ($Q_{\text{mod}} = 1.0$) | No alterar sin prueba de calibración |
| $\rho_{\text{shock}}$ | Peso Ancla Macro (Con Shock) | `0.30` | Fracción | `[LN-QBE-036]` | Contracción con shock ($Q_{\text{mod}} \ne 1.0$) | No usar si no hay reporte médico verificado |
| $N_{\text{forma}}$ | Ventana de Forma Reciente | `10` | Partidos | `[LN-QBE-036]` | Partidos de alta frecuencia recientes | No truncar a menos de 5 fechas |

---

## 4. DOMINIO DE INCERTIDUMBRE EPISTÉMICA Y GOBERNANZA

| Símbolo | Nombre Canónico | Valor Exacto | Unidad | Nodo Dueño | Dominio de Validez | Prohibición de Reúso |
|:---:|---|---|:---:|:---:|---|---|
| $\tau_{\text{disp}}$ | Tolerancia Crítica Discrepancia | `0.12` | Probabilidad | `[LN-QBE-070-B]` | Límite de desacuerdo inter-modelos | Discrepancia $> 0.12 \implies$ Cuarentena |
| $\varepsilon_{\text{friccion}}$ | Amortiguador de Singularidad | `0.01` | Adimensional | `[LN-QBE-073-B]` | Denominador en Score de Fricción | Evita división por cero |
| $\gamma_{\text{Kelly}}$ | Fracción Atenuada de Kelly | `0.25` (Cuarto de Kelly) | Escalar | `[LN-QBE-070-B]` | Supresión de colas de varianza | Prohibido usar Kelly Completo ($1.0$) |
| $\Gamma_{\text{base}}$ | Umbral Maestro de Masa Base | `0.6700` ($67.0\%$) | Probabilidad | `[LN-QBE-059]` | Corte canónico que supera $2/3 \approx 0.6667$ | No descender por debajo de 2/3 |
| $\Gamma_{\text{mid}}$ | Umbral Maestro Exigente | `0.7000` ($70.0\%$) | Probabilidad | `[LN-QBE-059]` | Modo estricto de concentración | Exclusivo del selector UI |
| $\Gamma_{\text{high}}$| Umbral Maestro Conservador | `0.7500` ($75.0\%$) | Probabilidad | `[LN-QBE-059]` | Modo ultra-prudente (baja varianza) | Exclusivo del selector UI |


---

## 5. DOMINIO FINANCIERO Y LÍMITES PATRIMONIALES (HARD-CAPS)

| Símbolo | Nombre Canónico | Valor Exacto | Unidad | Nodo Dueño | Dominio de Validez | Prohibición de Reúso |
|:---:|---|---|:---:|:---:|---|---|
| $\text{Cap}_{\text{partido}}$ | Hard-Cap Individual Máximo | `0.0800` ($8.0\%$) | % Bankroll | `[LN-QBE-070-B]` | Exposición máxima por evento | Inviolable (The Shield Invariante #3) |
| $\text{Cap}_{\text{cartera}}$ | Hard-Cap Global de Jornada | `0.2500` ($25.0\%$) | % Bankroll | `[LN-QBE-070-B]` | Exposición total simultánea de jornada | Inviolable (The Shield Invariante #4) |
| $\text{Cap}_{\text{underdog}}$ | Cota Underdog Ley 3 (Familia R) | `0.0150` ($1.5\%$) | % Bankroll | `[LN-QBE-115]` | Techo exclusivo de `QBE-R1`/`QBE-R2` | **Techo, jamás piso**: no rescata órdenes sub-dimensionadas |
| $\text{Piso}_{\text{ventanilla}}$ | Apuesta Mínima Legal | `$2.00` | MXN | `[LN-QBE-071]` | Terminal físico de casino | Ningún boleto split puede ser $< 2.00$ |
| $\text{Tol}_{\text{tablas}}$ | Tolerancia Bancaria $V=0$ | `$0.08` | MXN | `[LN-QBE-070]` | Desviación máxima de indemnidad | $\|B_{\text{seg}} \cdot O_{\text{emp}} - B_i\| \le 0.08$ |

### Parámetros del Filtro de Veto Inteligente Anti-Ruptura (Identificables para ML)
| Símbolo | Nombre Canónico | Valor Exacto | Unidad | Nodo Dueño | Propósito Fiduciario |
|:---:|---|---|:---:|:---:|---|
| $\Delta P_{\text{paridad}}$ | `DELTA_P_PARIDAD_VETO` | `0.1200` (12.0%) | Fracción | `[LN-QBE-060-C]` | Cota de dispersión mínima para admitir convicción |
| $P_{\max}^{\min}$ | `PMAX_MIN_OPERABLE` | `0.3800` (38.0%) | Fracción | `[LN-QBE-060-C]` | Piso de masa del favorito para apostar |
| $\sum \lambda_{\text{fuego}}$ | `LAMBDA_SUMA_FUEGO_VETO` | `3.0000` | Goles xG | `[LN-QBE-060-C]` | Techo de goles combinados para veto en 1X2 |
| $p_{X,\text{fuego}}^{\max}$ | `P_EMPATE_FUEGO_TECHO` | `0.2200` (22.0%) | Fracción | `[LN-QBE-060-C]` | Cota de asfixia de empate en partidos de fuego |

### Parámetros del Escudo de Altitud y de la Trinidad de Certeza (Saneamiento Vol. II)
| Símbolo | Nombre Canónico | Valor Exacto | Unidad | Nodo Dueño | Propósito Fiduciario |
|:---:|---|---|:---:|:---:|---|
| $\Delta\text{Alt}^{\text{veto}}$ | `UMBRAL_VETO_ALTITUD_METROS` | `1000.0` | Metros | `[LN-QBE-115]` | Veta la Híbrida Visitante (`QBE-H2`) por trampa de altitud |
| $\text{Certeza}_{\text{conservador}}$ | Banda Conservadora §5.10 | `90.0` | % | `[LN-QBE-115]` | Admite sólo Híbridas con cobertura (veta D1/D2/R1/R2) |
| $\text{Certeza}_{\text{balanceado}}$ | Banda Balanceada §5.10 | `80.0` | % | `[LN-QBE-115]` | Veta Familia R y directas foráneas (`QBE-D2`) |

### Parámetros de la Cota de Dominancia P′ (Blindaje H2)
| Símbolo | Nombre Canónico | Valor Exacto | Unidad | Nodo Dueño | Propósito Fiduciario |
|:---:|---|---|:---:|:---:|---|
| $P'_{\min,\text{visita}}$ | `UMBRAL_DOMINANCIA_VISITANTE_PCT` | `0.5000` (50.0%) | Fracción | `[LN-QBE-116]` | Veta la Híbrida Visitante (`QBE-H2`) si el propio P′ del modelo no concede mayoría al visitante |

---

## 6. DOMINIO COMBINATORIO QUINIELAS (PROGOL / REVANCHA)

| Símbolo | Nombre Canónico | Valor Exacto | Unidad | Nodo Dueño | Dominio de Validez | Prohibición de Reúso |
|:---:|---|---|:---:|:---:|---|---|
| $K_{\text{regular}}$ | Dimensión Progol Regular | `14` | Partidos | `[LN-QBE-084]` | Casillas de concurso principal | Espacio de búsqueda $2^{14} = 16,384$ |
| $K_{\text{revancha}}$ | Dimensión Progol Revancha | `7` | Partidos | `[LN-QBE-087]` | Casillas de concurso anexo | Espacio total $3^7 = 2,187$ (Todo o Nada) |
| $\text{Precio}_{\text{progol}}$ | Costo Quiniela Sencilla | `$15.00` | MXN | `[LN-QBE-074]` | Precio oficial Pronósticos | $M = \lfloor B / 15.0 \rfloor$ |
| $\text{Precio}_{\text{revancha}}$ | Costo Revancha Sencilla | `$5.00` | MXN | `[LN-QBE-087]` | Precio oficial Pronósticos | Prohibido descenso por Hamming |
| $\mathcal{W}_{\text{desamb}}$ | Ventana Crítica de Torneo | $[-24\text{h}, +72\text{h}]$ | Horas | `[LN-QBE-094]` | Disputa respecto a $t_{\text{cierre}}$ | Desambiguación temporal de ligas |

---

## 7. TABLA DE PROHIBICIONES DE REÚSO (CO-LOCACIÓN DE SÍMBOLOS)

| Símbolo A | Símbolo B | Relación Legislada | Nodo Rector |
|---|---|---|:---:|
| $\kappa_{\text{decay}}$ (`ln2/180`, días⁻¹) | $\kappa_{\text{net}}$ (`0.2500`, adimensional) | **Jamás son intercambiables**: uno decae evidencia histórica H2H, el otro comprime factores log-diferenciales | `[LN-QBE-020]` / `[VAULT-CORE-001]` |
| $\rho_{\text{estable}}$ (`0.55`) | $\rho_{\text{shock}}$ (`0.30`) | El ancla macro sólo se relaja con **shock verificado** ($Q_{\text{mod}} \ne 1.0$) | `[LN-QBE-036]` |
| $\text{Cap}_{\text{partido}}$ (`0.08`) | $\text{Cap}_{\text{cartera}}$ (`0.25`) | El cap individual no puede superar el 32% del cap de cartera (relación $0.08/0.25$) | `[LN-QBE-070-B]` |
| $\tau_{\text{disp}}$ (`0.12`) | $\text{Tol}_{\text{tablas}}$ (`0.08` MXN) | Uno mide desacuerdo epistémico en probabilidad; el otro indemnidad bancaria en pesos | `[LN-QBE-070-B]` / `[LN-QBE-070]` |
| $\text{Cap}_{\text{partido}}$ (`0.08`) | $\text{Cap}_{\text{underdog}}$ (`0.015`) | **Jamás son intercambiables**: la cota del 1.5% es un techo adicional EXCLUSIVO de la Familia R y no sustituye el hard-cap individual | `[LN-QBE-070-B]` / `[LN-QBE-115]` |

---

## 8. DOMINIO DE FÍSICA ESTOCÁSTICA Y CLAMPS (SANEAMIENTO O-04 Y O-14)
| Símbolo | Nombre Canónico | Valor Exacto | Unidad | Nodo Dueño | Dominio de Validez |
|:---:|---|---|:---:|:---:|---|
| $B_{\text{liga}}$ | `BASELINE_LIGA` | `1.35` | Goles / Partido | `[LN-QBE-040]` | Baseline para cálculo de madurez |
| $J_{\text{sat}}$ | `SATURACION_MADUREZ_J` | `6.0` | Jornadas | `[LN-QBE-040]` | Punto de saturación de madurez |
| $\Omega_{\min}$ | `OMEGA_MIN` | `0.40` | Adimensional | `[LN-QBE-040]` | Clamp inferior de rendimiento |
| $\Omega_{\max}$ | `OMEGA_MAX` | `1.60` | Adimensional | `[LN-QBE-040]` | Clamp superior de rendimiento |
| $w_{xG}$ | `BLEND_XG` | `0.65` | Fracción | `[LN-QBE-040]` | Peso de xG en mezcla de ataque |
| $w_{GF}$ | `BLEND_GF` | `0.35` | Fracción | `[LN-QBE-040]` | Peso de GF en mezcla de ataque |
| $G_{\min}$ | `CLAMP_GOLES_MIN` | `0.05` | Goles | `[LN-QBE-040]` | Cota inferior de goles esperados |
| $G_{\max}$ | `CLAMP_GOLES_MAX` | `6.00` | Goles | `[LN-QBE-040]` | Cota superior de goles esperados |
| $\Delta_{\text{epist}}^{\text{def}}$ | `DELTA_EPIST_DEFAULT` | `0.02` | Probabilidad | `[LN-QBE-070-C]` | Delta epistémico por defecto |

---

## 9. DOMINIO DE INGESTA Y SONDAS
| Símbolo | Nombre Canónico | Valor Exacto | Unidad | Nodo Dueño | Propósito |
|:---:|---|---|:---:|:---:|---|
| $\text{Timeout}_{\text{probe}}$ | `PROBE_TIMEOUT_MS` | `60000` | ms | `[LN-QBE-136]` | Tiempo máximo de espera de renderizado DOM antes de abortar. |
| $\text{Dir}_{\text{probe}}$ | `PROBE_DATA_DIR` | `"data/sondas_exploracion/"` | Ruta | `[LN-QBE-136]` | Directorio de salida para muestras .mhtml. |

---

## 📎 NOTA DE TRANSCRIPCIÓN (Provenance)

Transcrito **verbatim** desde el Decreto de Consolidación (Sprint 3 — Capa 4), según la Directiva
Maestra de Consolidación y Materialización. Los valores numéricos, unidades y nodos dueños son
**inmutables**; el catálogo no crea, delega ni re-calibra nada por sí mismo.

* **Errata tipográfica declarada (sólo presentación markdown):** en la fila de
  $\text{Tol}_{\text{tablas}}$ las barras de valor absoluto se escriben `\|` al renderizar (las
  barras crudas `|` cierran la celda de la tabla). El contenido matemático legislado
  ($\text{Tol} = \$0.08$ MXN con $|B_{\text{seg}} \cdot O_{\text{emp}} - B_i| \le 0.08$) queda intacto.
* **Fuentes de verificación en código (anclaje simbólico, cero archivo:línea):**
  $\tau_{\text{H2H}}$ / $\kappa_{\text{decay}}$ → `qbe_core/src/core/temporal.py` (`TemporalDecayEngine`);
  $\kappa_{\text{net}}$ ($\sigma_{\text{liga}}$ vestigial) → `qbe_core/src/core/intensity_canonical_loglink.py`
  (`KAPPA_NET`, `aplicar_damping_hiperbolico`); $\rho_{\text{estable}}$ / $\rho_{\text{shock}}$ /
  $\text{peso}_{xG}$ / $\text{peso}_{GF}$ → `qbe_core/src/core/sovereign/bayesian_form.py`.
* **Cierre de la Capa 4:** los símbolos $\kappa_{\text{decay}}$, $\rho_{\text{estable}}$,
  $\rho_{\text{shock}}$ y $N_{\text{forma}}$ quedan **consumidos** por el motor en producción
  (`qbe_core/src/core/sovereign_pipeline.py`, nodos `[LN-QBE-036]` y `[LN-QBE-020-C]`); ninguna constante
  canónica permanece huérfana ni duplicada.

## ANEXO A — CATÁLOGO CANÓNICO DE ALTITUDES (`CATALOGO_ALTITUDES_LIGAMX`)

**Nodo dueño:** `[LN-QBE-109]` / `[LN-QBE-115]`  
**Fuente:** `qbe_core/src/core/catalog.py`  
**Uso:** escudo de altitud y desempate ordinal. Los valores son hechos declarados, no estimaciones.

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

**Umbral de veto:** `UMBRAL_VETO_ALTITUD_METROS = 1000.0` (`[LN-QBE-115]`).  
**Umbral de rescate ordinal:** `UMBRAL_ALTITUD_RESCATE_METROS = 1000.0` (`[LN-QBE-124]`).  
**Prohibición:** no son la misma constante; rigen predicados distintos y no se mutan entre sí.

---

