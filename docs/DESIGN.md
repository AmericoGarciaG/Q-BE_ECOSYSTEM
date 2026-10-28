# Q-BE ECOSYSTEM — DESIGN BOOK

**Versión:** 2.0 — Dual-Surface / Semantic Cards Edition  
**Estado:** `[ALGO-PROTECTED]` — Sistema de Diseño Certificado  
**Proyecto:** `Q_BE_ECOSYSTEM`  
**Autoridad Suprema:** Américo García Guerrero (Director Humano)  
**Marco:** Kybern Industrial Framework v13.5  
**Expediente:** `SPRINT-FASE4-MIGRACION-REFLEXIVA-BG-04`  
**Fecha:** 2026-10-28  
**Sustituye a:** `Q_BE_CD_WEB/docs/DESIGN.md` (SPA monolítica `[DEROGADA]`)

> **Aviso de procedencia.** El diseño legado asumía una sola SPA servida por el monolito. El ecosistema tiene dos superficies: la SPA de la Mesa de Apuestas (`qbe_business`, OLTP) y el visor Jinja2 del Observatorio (`qbe_observatory`, OLAP). Comparten tokens y gramática visual, pero no estado, no sesión y no fuente de datos. Las cards semánticas y la tetralogía fáctica son el contrato de lectura de la evidencia.

---

## 1. PRINCIPIOS VISUALES

1. **Dark fintech, no casino.** Fondo slate profundo, cian institucional, verde esmeralda para valor positivo, rojo para riesgo, ámbar para advertencia, gris para ausencia de evidencia.
2. **La evidencia manda.** Un color sin dato es una mentira visual. `SIN EVIDENCIA` tiene representación propia; nunca se pinta como cero.
3. **Cero aritmética en el pintor.** El cliente transcribe el DTO; no deriva probabilidades, λ, Δ logarítmicas ni récords.
4. **Jerarquía antes que densidad.** La card semántica es el vehículo de lectura; la tabla forense es el soporte de auditoría.
5. **Estabilidad de contrato.** Los `id`, clases y nombres de red sellados no se renombran por estética.

### 1.1 Tokens canónicos

| Token | Valor | Uso |
|---|---|---|
| `--bg-base` | `#0F172A` | Fondo principal. |
| `--bg-surface` | `#1E293B` | Cards y superficies. |
| `--border` | `#334155` | Bordes y divisores. |
| `--accent` | `#38BDF8` / `#0284C7` | Acento institucional; el ámbar saturado está derogado. |
| `--success` | `#10B981` | Valor positivo, evidencia suficiente. |
| `--warning` | `#F59E0B` | Advertencia, evidencia parcial. |
| `--danger` | `#EF4444` | Riesgo, veto, evidencia contradictoria. |
| `--muted` | `#94A3B8` | Texto secundario y `SIN EVIDENCIA`. |
| `--text` | `#F8FAFC` | Texto principal. |

Tipografía: `Inter`/`Outfit`/system sans para lectura; `JetBrains Mono`/`Fira Code` para cifras, momios y probabilidades.

---

## 2. DOS SUPERFICIES, UN LENGUAJE

### 2.1 Mesa de Apuestas — `qbe_business:8000`

- SPA reactiva.
- Vistas: Hub de Ligas, Jornada y Tabla, Cartera Cuantitativa, Centro de Control.
- Foco: decisión y comando.
- No muestra backtesting histórico ni simulación OLAP.

### 2.2 Observatorio — `qbe_observatory:8001`

- Jinja2 server-side.
- Vistas: visor de calibración, backtesting, snapshot, Manus.
- Foco: auditoría y lectura.
- No escribe carteras ni modifica la base viva.

### 2.3 Regla de frontera visual

Un componente de la Mesa no importa templates del Observatorio; un template del Observatorio no llama routers de la Mesa. Si un dato necesita viajar, viaja por contrato o snapshot, no por estado compartido.

---

## 3. CARDS SEMÁNTICOS POLIMÓRFICOS

Cada dimensión del catálogo de 32 variables (`[LN-QBE-120]`) se abre con una **Card Semántica Polimórfica**. La anatomía depende de la familia `𝒯_*`; no se repite una tabla plana como único vehículo.

| Familia | Card | Contenido |
|---|---|---|
| `𝒯_Vol` | Barra dual de posesión | `V01` local/visita + rejilla `V02`–`V05`. |
| `𝒯_Rem` | Balanza de goles + badge | `V06` (xG, ancla npxG) + rejilla `V07`–`V11`. |
| `𝒯_Def` | Balanza de goles + badge | `V12` (xGA) + rejilla `V13`–`V16`; `V16` en cuarentena. |
| `𝒯_Por` | Balanza de goles + badge | `V18` (atajadas) + rejilla `V17`, `V19`, `V20`. |
| `𝒯_Spc` | Card atenuada de Fase 6 | Rótulo `0 de 5 (Fase 6)`; prohibido fabricar cifras. |
| `𝒯_Ctx` | Card consolidada | H2H, sede, altitud, descanso, forma y ΔxPTS. |

### 3.1 Reglas de composición

1. **Un solo soporte forense.** La tabla numérica de 7 columnas se publica una vez, consolidada y replegable al pie del acordeón; no se replica por dimensión.
2. **Cero tabla plana como única lectura.** La card es el vehículo principal.
3. **Cero `<table>` dentro de `_tablaDimension32`.**
4. **Cero estado espejo.** El DOM lee el DTO; no recalcula.
5. **Cero `0.00` aparente.** Una celda sin fuente se muestra vacía o `SIN EVIDENCIA`.

### 3.2 `𝒯_Ctx` — la card consolidada

- `V26`: récord H2H (`3V - 1E - 0D`).
- `V27`: Δgoles H2H.
- `V28`: récord de la visita en la sede.
- `V29`: ΔAlt+ servido por el motor (no altitud absoluta inventada en el cliente).
- `V30`: ΔDías de descanso.
- `V31`: forma 5P.
- `V32`: varianza ΔxPTS.

---

## 4. TETRALOGÍA FÁCTICA DE SEMÁFOROS

El micro-HUD publica exactamente cuatro luces:

```text
● OPTA    ● SEDE    ● H2H    ● CTX
```

| Luz | Qué mide | Estados |
|---|---|---|
| `OPTA` | Suficiencia y calidad de la evidencia Opta. | Verde, ámbar, rojo, gris. |
| `SEDE` | Evidencia de sede/altitud; gate mínimo de 3 partidos. | Verde, ámbar, rojo, gris. |
| `H2H` | Ventana H2H; 5 enfrentamientos es el estado pleno; 1–4 parcial; 0 es Zero-H2H. | Verde, ámbar, gris. |
| `CTX` | Contexto: descanso, shocks, forma y factores auxiliares. | Verde, ámbar, rojo, gris. |

### 4.1 Reglas

1. **`EPIST` no se muestra en el micro-HUD.** El backend conserva `semaforos.epist` para el filtro anti-cuarentena; la UI muestra solo la tetralogía fáctica.
2. **Sin texto redundante.** Se usa glifo + nombre; la clase CSS dicta el color. No se escribe “verde” al lado de un punto verde.
3. **Sin cero fabricado.** `SIN EVIDENCIA` es gris y tiene explicación; no es un cero.
4. **Contraste y accesibilidad.** El color no es el único portador de significado: el estado se anuncia con glifo y texto accesible.

### 4.2 Colores de estado

| Estado | Color | Lectura |
|---|---|---|
| Suficiente | `#10B981` | Evidencia plena. |
| Parcial | `#F59E0B` | Evidencia incompleta o ventana reducida. |
| Contradictorio / veto | `#EF4444` | Evidencia que bloquea o descalifica. |
| Sin evidencia | `#94A3B8` | No hay dato; no se imputa. |

---

## 5. ESTADOS VACÍOS Y DEGRADACIÓN

1. **`SIN EVIDENCIA`** es un estado de primera clase, no un error genérico.
2. **`FUERA DE FUENTE`** aplica a celdas del catálogo que el proveedor no publica (por ejemplo, `V16`).
3. **`FASE 6`** aplica a dimensiones sin feed certificado (`𝒯_Spc`); se atenúan, no se rellenan.
4. **Base vacía** se explica con una guía didáctica; no se muestran tablas falsas.
5. **Snapshot ausente** produce un error ruidoso del Observatorio; no se cae a la base viva.

---

## 6. GEOMETRÍA Y RESPONSIVE

- Contenedores con `minmax(0, 1fr)` para evitar desbordes.
- Rejillas de cards con `gap` consistente y jerarquía de 4 niveles en cartelera.
- Modo enfoque centrado a 880 px para lectura de tablas y cards.
- Header fino de un solo piso; sin barras duplicadas.
- En móvil, la card semántica se apila; la tabla forense se repliega; nunca se oculta evidencia sin indicador.

---

## 7. CONTRATOS DE COMPONENTE

| Contrato | Regla |
|---|---|
| `id="modal-44-variables"` | No se renombra; es ancla de red y de pruebas. |
| `variables_44` | Nombre de DTO conservado; cardinalidad real 32. |
| `Catalogo44Out` | Contrato Pydantic conservado. |
| `.btn-ver-44-vars` | No se renombra por estética. |
| `semaforos` | Tetralogía `OPTA/SEDE/H2H/CTX`; `epist` queda fuera del micro-HUD. |
| `SIN EVIDENCIA` | Literal canónico; no se sustituye por `0` ni por `—` sin explicación. |

---

## 8. ÍNDICE DE NODOS DE DISEÑO

| ID | Nodo / Título | Superficie | Estado |
|---|:---:|---|:---:|
| `[DES-QBE-005]` | Paleta Cromática Disciplinada (Erradicación de Amarillo Saturado) [UX-MANDATE] | `compartida` | VIGENTE |
| `[DES-QBE-010]` | Barra Superior de Identidad Discreta (Silent Branding) [UX-MANDATE] | `compartida` | VIGENTE |
| `[DES-QBE-012]` | Isotipo Institucional y Favicon Dark Fintech [UX-MANDATE] | `compartida` | VIGENTE |
| `[DES-QBE-015]` | Hub de Ligas (Vista 1) — Voz Institucional [UX-MANDATE] | `compartida` | VIGENTE |
| `[DES-QBE-016]` | Jornada y Tabla de Posiciones (Vista 2) [UX-MANDATE] | `business` | VIGENTE |
| `[DES-QBE-016-B]` | Geometría y Renderizado de Próximo Rival [UX-MANDATE] | `business` | VIGENTE |
| `[DES-QBE-016-C]` | Jerarquía de Cartelera en 4 Niveles y Clicabilidad Total de Tarjeta [UX-MANDATE] | `business` | VIGENTE |
| `[DES-QBE-016-D]` | Erradicación de Prefijos Redundantes en Columna Próximo Rival [UX-MANDATE] | `compartida` | VIGENTE |
| `[DES-QBE-017-B]` | Jerarquía de Resolución de Emblemas por Variantes de Disco y SVG Fallback [UX-MANDATE] | `business` | VIGENTE |
| `[DES-QBE-018]` | Panel Administrativo de Curación HITL (Catálogos y Bóveda) [UX-MANDATE] | `compartida` | VIGENTE |
| `[DES-QBE-019]` | Vista 5: Radiografía Forense Interactiva en UI (Backlog / PM-FACE) [UX-MANDATE] | `business` | VIGENTE |
| `[DES-QBE-020]` | Dashboard Ejecutivo de Cartera y Métricas Duales [UX-MANDATE] | `compartida` | VIGENTE |
| `[DES-QBE-021]` | Bloqueo Semántico en DOM y Cronometría Dinámica [UX-MANDATE] | `business` | VIGENTE |
| `[DES-QBE-023]` | Modal HUD de Procesamiento Cuantitativo en Vivo [UX-MANDATE] (H7) | `compartida` | VIGENTE |
| `[DES-QBE-024]` | Ergonomía de Boletos Split con Prioridad Financiera [UX-MANDATE] (H9) | `compartida` | VIGENTE |
| `[DES-QBE-026]` | Selector de Jornadas en Píldoras Continuas (Pill-Tabs) [UX-MANDATE] | `business` | VIGENTE |
| `[DES-QBE-027]` | Banner de Resiliencia Tripartito (Las Tres Píldoras de Certeza) [UX-MANDATE] | `compartida` | VIGENTE |
| `[DES-QBE-028]` | Badge de Inconsistencia Auditada en Tesis [UX-MANDATE] | `compartida` | VIGENTE |
| `[DES-QBE-030]` | Barra de Navegación Cockpit y Dual-Core Layout [UX-MANDATE] | `business` | VIGENTE |
| `[DES-QBE-031]` | Pantalla Core 1: El Centro Soberano de Inteligencia Deportiva | `business` | VIGENTE |
| `[DES-QBE-032]` | Pantalla Core 2: Estación de Mercados Financieros y Asignación | `business` | VIGENTE |
| `[DES-QBE-033]` | Geometría DOM Obligatoria para la Interfaz Dual-Core [UX-MANDATE] | `business` | VIGENTE |
| `[DES-QBE-035]` | Vista Equipos y Partidos Soberana (Limpieza de Controles Comerciales) [UX-MANDATE] | `business` | VIGENTE |
| `[DES-QBE-036]` | Inviolabilidad Geométrica de la Columna Forma [UX-MANDATE] [ARCH-PILLAR] | `business` | VIGENTE |
| `[DES-QBE-037]` | El Carrusel Horizontal Continuo y la Tarjeta Clicable Limpia [UX-MANDATE] | `business` | VIGENTE |
| `[DES-QBE-037-A]` | Ventanizado de 3 Píldoras en Carrusel de Jornadas [UX-MANDATE] | `business` | VIGENTE |
| `[DES-QBE-039]` | Configuración de Cartera con Selector de Operador y Despacho Único [UX-MANDATE] | `business` | VIGENTE |
| `[DES-QBE-039-B]` | Cluster Central de Tarjeta: Triple Nivel Probabilístico (Soberano vs. Consenso) & Micro-Malla [UX-MANDATE] | `business` | VIGENTE |
| `[DES-QBE-040]` | Modo Enfoque: Alternador de Tabla General y Cartelera Centrada [UX-MANDATE] | `compartida` | VIGENTE |
| `[DES-QBE-040-A]` | Modo Enfoque de Cartelera y Persistencia Local [UX-MANDATE] | `business` | VIGENTE |
| `[DES-QBE-041]` | Header Fino de Un Solo Piso (45px Fijo) [UX-MANDATE] | `business` | VIGENTE |
| `[DES-QBE-042]` | Contención Maestra Split-View con Columna minmax(0, 1fr) [UX-MANDATE] | `business` | VIGENTE |
| `[DES-QBE-043]` | Respaldo Narrativo Local de 4 Puntos Focales [UX-MANDATE] | `business` | VIGENTE |
| `[DES-QBE-044]` | Nodo canónico | `compartida` | VIGENTE |
| `[DES-QBE-045]` | Contrato de Claves Frontend y Soporte de las 9 Estrategias Canónicas [UX-MANDATE] | `compartida` | VIGENTE |
| `[DES-QBE-046]` | Sub-Pestaña de Quinielas Progol #2352 en la Mesa de Apuestas [UX-MANDATE] | `compartida` | VIGENTE |
| `[DES-QBE-047]` | Selector Multi-Operador en Mesa de Apuestas [UX-MANDATE] | `business` | VIGENTE |
| `[DES-QBE-048]` | Cockpit: Cuarta Pestaña [ ⚙️ Centro de Control ] y Terminal de Streaming [UX-MANDATE] | `business` | VIGENTE |
| `[DES-QBE-049]` | Saneamiento Tipográfico de Celdas de Equipo (Anti-Truncamiento Real) [UX-MANDATE] | `compartida` | VIGENTE |
| `[DES-QBE-050]` | Tooltips Didácticos Fiduciarios en el Centro de Control [UX-MANDATE] | `compartida` | VIGENTE |
| `[DES-QBE-051]` | Banner Didáctico de Base de Datos Vacía en Live Board [UX-MANDATE] | `compartida` | VIGENTE |
| `[DES-QBE-052]` | Selector Multi-Operador con Opción "Mejor Combinación" por Defecto [UX-MANDATE] | `compartida` | VIGENTE |
| `[DES-QBE-053]` | Boletos Split con Logo de Casa Patrocinadora por Boleto [UX-MANDATE] | `compartida` | VIGENTE |
| `[DES-QBE-054]` | Corrección de Macro KPI "Posiciones del Total" [UX-MANDATE] | `compartida` | VIGENTE |
| `[DES-QBE-055]` | Micro-Insignia de Operador en Boletos Split (Cero Texto Duplicado) [UX-MANDATE] | `business` | VIGENTE |
| `[DES-QBE-056]` | Apertura Dinámica del Live Board en Jornada Vigente [UX-MANDATE] | `compartida` | VIGENTE |
| `[DES-QBE-057]` | Selector de Mercados con Tríada de Operadores y "Mejor Combinación" [UX-MANDATE] | `compartida` | VIGENTE |
| `[DES-QBE-058]` | Desglose Cuantitativo en Tarjetas de Partidos Vetados [UX-MANDATE] | `business` | VIGENTE |
| `[DES-QBE-059]` | Renderizado Universal de Emblema de Casino en Boletos Mono-Operador [UX-MANDATE] | `compartida` | VIGENTE |
| `[DES-QBE-060]` | Anatomía Enriquecida de Boletos Split con Momio Casino, P' y Opción No Jugada [UX-MANDATE] | `business` | VIGENTE |
| `[DES-QBE-061]` | Formato Dual de Cuotas de Casino: Probabilidad Implícita + Decimal [UX-MANDATE] | `compartida` | VIGENTE |
| `[DES-QBE-062]` | Despliegue de la Tetralogía de Escenarios en Boletos Split [UX-MANDATE] | `compartida` | VIGENTE |
| `[DES-QBE-063]` | Diseño de la Radiografía Forense: Barras Duales Apiladas, Radiografía Estructural y Cero Estrellas [ARCH-PILLAR] | `compartida` | VIGENTE |
| `[DES-QBE-064]` | Geometría del Micro-HUD de Tarjeta y Modal Forense de 44 Variables [UX-MANDATE] | `compartida` | VIGENTE |
| `[DES-QBE-064-B]` | Geometría Refinada del HUD de Tarjeta Micro [UX-MANDATE] | `business` | VIGENTE |
| `[DES-QBE-065]` | Badge de Procedencia de la Evidencia e Iluminación de las Ocho Variables Vivas [UX-MANDATE] | `compartida` | VIGENTE |
| `[DES-QBE-066]` | Acordeón Bicolor del Catálogo Forense: Dimensiones con Datos vs. Dimensiones en Fase 6 [UX-MANDATE] | `compartida` | VIGENTE |
| `[DES-QBE-067]` | Badge `SIN EVALUAR` y Filtro Anti-Cuarentena de la Cartelera de Calibración [UX-MANDATE] | `observatorio` | VIGENTE |
| `[DES-QBE-068]` | Diseño Dual del Visor de Backtesting (Auditoría Fáctica vs. Rentabilidad) [UX-MANDATE] | `observatorio` | VIGENTE |
| `[DES-QBE-069]` | Conmutador de Laboratorio (Candado) y Filtros de Estrategia [UX-MANDATE] | `observatorio` | VIGENTE |
| `[DES-QBE-070]` | Nodo canónico | `compartida` | VIGENTE |
| `[DES-QBE-070-B]` | Cards Semánticos Polimórficos del Catálogo de 32 Variables y Lectura Consolidada de `𝒯_Ctx` [UX-MANDATE] | `compartida` | VIGENTE |
| `[DES-QBE-071]` | Tetralogía Fáctica en el Micro-HUD y Retiro Visual del Semáforo EPIST [UX-MANDATE] | `compartida` | VIGENTE |
| `[DES-QBE-072]` | Glosario Autodescriptivo de la Vitrina y Arquitectura de Cuatro Capas del Visor de Calibración [UX-MANDATE] | `observatorio` | VIGENTE |
| `[DES-QBE-073]` | Apilamiento de Desglose en Tabla Meso [UX-MANDATE] | `observatorio` | VIGENTE |
| `[UX-CFG-01]` | Orden Configurable de Boletos en Tarjeta [UX-MANDATE] [BACKLOG] | `compartida` | VIGENTE |

_Total: 66 identificadores._


---

## 9. TRAZABILIDAD

- Fuente: `Q_BE_CD_WEB/docs/DESIGN.md`.
- Migración: de SPA monolítica a dos superficies; cards polimórficas y tetralogía fáctica.
- Juez de referencia: suite de Observatorio y contratos de UI.
- Cierre: `53+ passed`, `0 failed`, `EXIT CODE 0`.
