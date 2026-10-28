# Q-BE ECOSYSTEM — GOVERNANCE BOOK

**Versión:** 13.5 — Ecosystem Edition  
**Estado:** `[ALGO-PROTECTED]` — Base de Gobierno Fundacional  
**Proyecto:** `Q_BE_ECOSYSTEM`  
**Autoridad Suprema:** Américo García Guerrero (Director Humano)  
**Marco:** Kybern Industrial Framework v13.5 (DirGen Operational Edition)  
**Expediente de origen:** `SPRINT-FASE4-MIGRACION-REFLEXIVA-BG-04`  
**Fecha de sanción:** 2026-10-28  
**Sustituye a:** `Q_BE_CD_WEB/docs/GOVERNANCE.md` (monolito legado, no vigente)

> **Aviso de procedencia.** Este libro no es una copia del `GOVERNANCE.md` legado. Es una reescritura normativa para la topología real de `Q_BE_ECOSYSTEM`: cuatro pilares procesales, `qbe_storage` como sustrato transversal, CQRS entre la Mesa de Apuestas y el Observatorio, y un snapshot atómico como único contrato de lectura analítica. Las referencias al monolito se conservan únicamente como historia y quedan marcadas como `[DEROGADO]`.

---

## 1. AXIOMA CENTRAL

> **El código fuente es un subproducto fungible, transitorio y reemplazable; la Intención Legislada —lógica de negocio, restricciones matemáticas y fronteras de datos— es el único activo institucional permanente, inmutable y soberano.**

De este axioma se derivan seis reglas no negociables:

1. **La Base de Gobierno manda.** `docs/` es la fuente de verdad normativa; el código es su materialización verificable.
2. **El ID es inmutable.** Un identificador sellado no se reasigna, no se reutiliza y no se borra: se deroga con tombstone.
3. **La ruta es fungible.** Un nodo puede cambiar de archivo o de pilar; lo que no cambia es su ID, su contrato y su intención.
4. **Cero datos sintéticos en producción.** Ningún fallback puede fabricar marcadores, cuotas, probabilidades o estadísticas.
5. **Fallo ruidoso.** Un dato ausente produce `SIN EVIDENCIA`, cuarentena o veto; nunca un cero aparente.
6. **Documentación y código no pueden divergir.** Un cambio estructural sin actualización de la Base de Gobierno es un cambio incompleto, aunque los tests pasen.

---

## 2. PRINCIPIOS DE INGENIERÍA

### 2.1 Sándwich neuro-simbólico invertido

1. **Sensor fáctico estructurado:** APIs y scrapers deterministas, sin consumo generativo.
2. **Enforcer matemático determinista:** `qbe_core` ejecuta Poisson bivariado, Dixon-Coles, log-lineal, Kelly, morfología del símplex y contratos de cartera.
3. **Inferencia asistida:** los modelos de lenguaje auditan noticias o redactan tesis; jamás sustituyen un cálculo, un precio o una probabilidad.

### 2.2 Abstracción universal

Queda prohibido codificar reglas condicionales sobre partidos, equipos o fechas específicas. Los fixtures concretos son instancias de prueba de una ley general, nunca constantes de producción.

### 2.3 Aislamiento de fallos

`Q_BE_ECOSYSTEM` se compone de procesos independientes. La caída del Observatorio no detiene la Mesa de Apuestas; la caída de Ingesta no autoriza datos inventados; un fallo matemático en `qbe_core` es un `Alto al Fuego`, no una degradación silenciosa. Cada pilar falla en su propia frontera y publica su estado.

### 2.4 Segregación de responsabilidades CQRS

- **Lado de comando (OLTP):** `qbe_business` escribe la operación de la Mesa de Apuestas a través de `qbe_storage`.
- **Lado de consulta (OLAP):** `qbe_observatory` lee exclusivamente un snapshot atómico, en modo solo lectura.
- **Regla de oro:** el Observatorio no escribe sobre la base viva; la Mesa de Apuestas no ejecuta consultas analíticas de backtesting; Ingesta no publica UI.

### 2.5 Cero acoplamiento por estado compartido

Los pilares no comparten sesiones SQLAlchemy, objetos mutables en memoria ni archivos de trabajo. Comparten contratos versionados, el gateway de persistencia y el snapshot atómico. Cualquier atajo que cruce esa frontera es una violación de arquitectura.

---

## 3. PROTOCOLO KTP v2.0 — ECOSYSTEM EDITION

**KTP** es el protocolo de tránsito de una intención legislada hacia una materialización verificable. La versión 2.0 incorpora la realidad de cuatro pilares y sustituye el flujo monolítico por un régimen de cambios atómicos por frontera.

### 3.1 Cláusulas

| Cláusula | Nombre | Obligación verificable |
|---|---|---|
| `KTP-01` | Jurisdicción y expediente | Todo cambio declara sprint, alcance, archivos y régimen. Sin expediente no hay intervención. |
| `KTP-02` | Eco de Comprensión | El Constructor reformula el propósito, las fronteras y los riesgos antes de tocar archivos. |
| `KTP-03` | Ley antes que código | La regla se redacta en `docs/` antes de materializarse. |
| `KTP-04` | Juez en RED | El contrato de prueba se escribe y falla antes de la materialización. |
| `KTP-05` | Cambio atómico por pilar | Cada intervención modifica el pilar dueño del contrato; prohibido el cambio lateral no declarado. |
| `KTP-06` | CQRS y no contaminación | Ningún cambio OLAP escribe sobre OLTP; ningún cambio OLTP introduce lógica de backtesting. |
| `KTP-07` | Evidencia reproducible | El cierre exige comando, salida, exit code, diff y manifiesto. |
| `KTP-08` | Custodia de IDs | Todo ID nuevo se asigna con `max + 1` sobre el registro completo; todo ID existente se preserva. |
| `KTP-09` | Cero invención | Dato ausente = `SIN EVIDENCIA`, cuarentena o veto. Nunca un valor fabricado. |
| `KTP-10` | Cierre y reversibilidad | Todo cambio declara cómo se revierte y qué evidencia lo autoriza. |

### 3.2 Regla de precedencia

Ante conflicto entre velocidad y gobernanza, prevalece la gobernanza. Ante conflicto entre un test y una ley, prevalece la ley; el test se corrige solo si la ley cambió por Ficha de Varianza aprobada. Ante conflicto entre un atajo de implementación y una frontera CQRS, prevalece la frontera.

---

## 4. ESTRUCTURA DE AUTORIDAD

| Rol | Función | Límite |
|---|---|---|
| **Director Humano** | Autoridad suprema; aprueba varianzas, presupuesto y cierre. | No opera el motor ni reemplaza al Juez. |
| **Arquitecto** | Custodia la Base de Gobierno, los IDs y las fronteras. | No autoriza datos sintéticos ni saltos de régimen. |
| **Constructor** | Materializa la ley y hace pasar al Juez. | No legisla por conveniencia ni modifica el Juez para obtener verde. |
| **The Shield** | Jueces inmutables de contrato, pureza y aislamiento. | No negocia el resultado: falla o pasa. |

La Tríada no es decorativa: separa intención, custodia y ejecución. Un cambio sin las tres miradas es un cambio incompleto.

---

## 5. TOPOLOGÍA NORMATIVA DE CUATRO PILARES

| Pilar | Responsabilidad | Prohibición |
|---|---|---|
| `qbe_core` | ADN matemático puro: Poisson, Dixon-Coles, log-lineal, morfología, cartera, triaje. | Cero I/O, cero DB, cero FastAPI, cero scrapers. |
| `qbe_business` | Mesa de Apuestas OLTP; FastAPI en `:8000`; SPA y routers transaccionales. | No lee el histórico analítico ni ejecuta backtesting. |
| `qbe_observatory` | Observatorio OLAP; Jinja2 en `:8001`; backtesting y visor de calibración sobre snapshot. | No escribe sobre la base viva ni modifica carteras. |
| `qbe_ingestion` | Data Nexus; scrapers y daemons en `:8002`; adquisición y normalización fáctica. | No publica UI ni decide precios. |

`qbe_storage` no es un quinto pilar: es la infraestructura transversal de persistencia —gateway, modelos 3NF, WAL y snapshot— que los cuatro pilares consumen bajo contrato.

### 5.1 Flujo canónico

1. `qbe_ingestion` obtiene y normaliza evidencia fáctica.
2. `qbe_storage` persiste a través del gateway, con PRAGMAs transaccionales y WAL.
3. `qbe_business` ejecuta la comanda de cartera y escribe la operación.
4. Un publicador materializa el snapshot con copia online y reemplazo atómico.
5. `qbe_observatory` abre el snapshot en solo lectura y sirve el visor.

---

## 6. MOTOR DE 3 PASOS

### Paso 0 — Pre-vuelo obligatorio

Se congelan baseline, IDs, hashes y estado del árbol. Se identifica el pilar dueño y se declara el alcance. Sin este paso, el Motor no arranca.

### Paso 1 — Legislación

Se redacta o modifica el nodo en `docs/`. Cero código de producción en este paso. La ley debe declarar: propósito, contrato de entrada, proceso, salida, transición, invarianzas y evidencia.

### Paso 2 — Juez inmutable

Se crea el contrato de prueba y se ejecuta en **RED**. El Juez no se adapta al código; el código se adapta al Juez. Si el Juez es incorrecto, se corrige la ley primero.

### Paso 3 — Materialización subordinada

Se modifica únicamente el pilar autorizado. Se ejecuta el Juez hasta **GREEN**, luego la suite completa y la auditoría perimetral. El cierre exige `EXIT CODE 0`.

### 6.1 Régimen dual-track

- `[DIRGEN-STRICT]`: matemática, persistencia, contratos financieros, hashes y fronteras CQRS. Cero ensayo y error; una falla detiene el proceso.
- `[DBBD-FUNGIBLE]`: UI, CSS, plantillas y utilidades. Se permite iteración táctica, pero con Juez y evidencia.

---

## 7. CUSTODIA DE IDENTIFICADORES

1. **Fuente única:** `docs/ID_REGISTRY.md`.
2. **Asignación:** `max(familia) + 1` sobre el registro completo, nunca sobre una vista parcial.
3. **Sellado:** un ID pasa a `SELLADO` solo con Juez en verde y anclaje simbólico en `docs/`.
4. **Prohibición:** no se reutiliza un ID `LIBRE` que haya estado sellado; no se borra un ID derogado.
5. **Trazabilidad:** todo ID debe aparecer en el cuerpo de su libro o en la tabla maestra. La migración no puede reducir el conjunto de IDs.

---

## 8. TAXONOMÍA DE INCIDENTES

| Clase | Ejemplo | Ruta |
|---|---|---|
| Implementación | `ImportError`, typo, ruta rota | Fast-track atómico, sin legislar. |
| Lógica | Probabilidades que no suman 1, Kelly mal aplicado, hardcode | Alto al Fuego + Ficha de Varianza. |
| Gobernanza | Cambio de docs sin Juez, ID reutilizado, ruta CQRS violada | Reversión y auditoría de Base de Gobierno. |
| Datos | Fallback sintético, cero aparente, cuarentena omitida | Violación crítica; reversión inmediata. |
| Seguridad | Secreto versionado, escritura OLAP, acceso no autorizado | Incidente crítico; rotación y bloqueo. |

---

## 9. PROHIBICIONES ABSOLUTAS

1. Copiar documentación legada sin reanclar topología, rutas y contratos.
2. Declarar verde sin ejecutar el Juez y la suite completa.
3. Modificar el Juez para ocultar un fallo.
4. Introducir datos sintéticos en producción o en la documentación normativa.
5. Escribir desde el Observatorio sobre la base viva.
6. Importar `qbe_business` o `qbe_ingestion` desde `qbe_core`.
7. Publicar un ID sin fila en `ID_REGISTRY.md`.
8. Cambiar constantes matemáticas sin Ficha de Varianza y sin actualizar `CONSTANTS.md`.
9. Versionar `.db`, `.log`, `.env` o cachés de pytest.
10. Presentar un `53+ passed` nominal si la suite tiene fallos o skips no declarados.

---

## 10. CIERRE DE INTERVENCIÓN

Un cierre válido de Fase 4 exige:

- Los 7 libros presentes y adaptados.
- `.gitignore` y `.gitattributes` globales.
- Juez de Gobernanza en `3/3 PASSED`.
- Suite completa con `53+ passed`, `0 failed`, `EXIT CODE 0`.
- Cobertura de IDs sin pérdida.
- Manifiesto `git diff` con archivos nuevos, modificados y excluidos.
- Declaración explícita de deudas y riesgos residuales.

> **Principio de cierre:** no se declara terminado lo que no se puede reproducir. La evidencia manda sobre la narrativa.
