# Q-BE ECOSYSTEM — GUÍA DEL PROTOCOLO KTP

**Documento:** `KTP_Guide.md`  
**Versión:** 1.0.0  
**Estado:** `[ALGO-PROTECTED]` — Guía Operativa de Transferencia  
**Proyecto:** `Q_BE_ECOSYSTEM`  
**Autoridad Suprema:** Américo García Guerrero (Director Humano)  
**Marco:** Kybern Industrial Framework v13.5 (DirGen Operational Edition)  
**Expediente:** `SPRINT-MATERIALIZACION-PAQUETE-KTP-DOCS-39`  
**Nodos:** `[LN-QBE-138]` / `[ARCH-1.4.74]`  
**Juez:** `qbe_core/tests/test_shield_ktp_package_integrity.py`  
**Fecha:** 2026-10-30

---

## 1. PROPÓSITO

Esta guía define cómo se transfiere el conocimiento institucional del ecosistema Q-BE entre turnos, sin dependencia del historial de conversaciones y sin acumulación de deudas superadas.

El paquete `docs/KTP/` no es un archivo de prompts. Es un **contrato de continuidad**: separa lo que debe permanecer estable de lo que debe cambiar en cada sprint, y obliga a que todo relevo tenga evidencia verificable.

**Regla de oro:** un Arquitecto entrante debe poder asumir el proyecto leyendo `KDB.md` y el último `AKT.md`. Si necesita preguntar “¿qué pasó antes?”, la transferencia falló.

---

## 2. FILOSOFÍA: KDB ESTABLE vs. AKT DINÁMICO

| Capa | Archivo | Naturaleza | Vida útil | Se edita |
|---|---|---|---|---|
| Conocimiento estable | `KDB.md` | Base de Conocimiento del Proyecto. Single Pane of Glass. | Permanente, versionada por consolidación. | Solo mediante `KDB_Act_Pmpt.md`. |
| Delta de contexto | `AKT.md` | Reporte del sprint o turno activo. | Un ciclo de transferencia. | Solo por el Arquitecto saliente. |
| Procedimiento | `KTP_Guide.md` | Manual del ciclo y de roles. | Permanente, versionado por cambio de doctrina. | Solo por ley aprobada. |
| Extracción | `AKT_Pmpt.md` | Prompt estandarizado de salida. | Permanente, versionado. | Solo por cambio de plantilla. |
| Consolidación | `KDB_Act_Pmpt.md` | Prompt estandarizado de entrada. | Permanente, versionado. | Solo por cambio de plantilla. |
| Memoria histórica | `history/` | Archivo inmutable de actas cerradas. | Permanente. | Nunca se edita ni se elimina. |

**Prohibiciones de diseño:**

1. No se copia el historial de chat dentro de `KDB.md`.
2. No se acumulan deudas ya cerradas en `AKT.md`.
3. No se usa `KDB.md` como diario de cambios; para eso está `history/`.
4. No se usa `AKT.md` como fuente de verdad permanente; para eso está `KDB.md`.
5. No se inventa un dato para “completar” una sección.

---

## 3. ESTRUCTURA DEL PAQUETE

```text
docs/KTP/
├── KTP_Guide.md          # este manual
├── KDB.md                # conocimiento estable
├── AKT_Pmpt.md           # prompt de extracción saliente
├── AKT.md                # delta activo
├── KDB_Act_Pmpt.md       # prompt de consolidación entrante
└── history/
    └── AKT_{YYYY-MM-DD}_{SPRINT}.md
```

**Invariante de existencia:** los cinco archivos rectores y el directorio `history/` deben existir siempre. El Juez `test_shield_ktp_package_integrity.py` falla si falta uno solo.

**Invariante de archivo:** el acta cerrada se copia a `history/` y el activo `AKT.md` se reinicia. Nunca se mueve el activo sin recrearlo: el paquete quedaría incompleto.

---

## 4. FSM DE TRANSFERENCIA

La transferencia es una máquina de estados finita de tres fases. No hay atajos ni fases implícitas.

```text
┌─────────────┐      ┌──────────────────┐      ┌─────────────┐
│  DESPACHO   │ ───▶ │  CONSOLIDACIÓN   │ ───▶ │  ASUNCIÓN   │
│  (Fase A)   │      │     (Fase B)     │      │  (Fase C)   │
└─────────────┘      └──────────────────┘      └─────────────┘
      │                       │                       │
 Arquitecto              Constructor              Arquitecto
  saliente                 entrante                entrante
      │                       │                       │
  AKT.md                 KDB.md + copia           Eco de
  (delta)                a history/ + reset       Comprensión
```

### 4.1 Fase A — Despacho

**Responsable:** Arquitecto saliente.  
**Entrada:** estado real del repositorio, resultados de The Shield, decisiones del turno.  
**Acción:** ejecutar `AKT_Pmpt.md` y producir `AKT.md`.  
**Salida:** delta de contexto completo, fechado y con evidencia.  
**Criterio de salida:** el `AKT.md` responde los 7 puntos de la plantilla y no contiene afirmaciones sin comando o dato que las respalde.

### 4.2 Fase B — Consolidación

**Responsable:** Constructor.  
**Entrada:** `AKT.md` cerrado, `KDB.md` vigente, Git HEAD y resultados de pruebas.  
**Acción:** ejecutar `KDB_Act_Pmpt.md`. Inspeccionar el repo real, actualizar `KDB.md`, copiar `AKT.md` a `history/AKT_{FECHA}_{SPRINT}.md`, reiniciar el activo y ejecutar el Juez.  
**Salida:** `KDB.md` actualizado, acta histórica inmutable, `AKT.md` listo para el siguiente ciclo.  
**Criterio de salida:** Juez KTP 4/4, suite unificada en verde, `history/` con el acta y `AKT.md` presente.

### 4.3 Fase C — Asunción

**Responsable:** Arquitecto entrante.  
**Entrada:** `KDB.md` actualizado y el último `AKT.md` (activo o archivado).  
**Acción:** leer ambos, contrastar con el estado real y emitir el **Eco de Comprensión** (KRM §9.2).  
**Salida:** confirmación de propósito, fronteras, régimen, topología y pruebas a ejecutar.  
**Criterio de salida:** el Arquitecto entrante puede explicar qué cambió, qué está protegido y cuál es el siguiente movimiento sin consultar chats anteriores.

---

## 5. ROLES Y RESPONSABILIDADES

| Rol | Responsabilidad | Límite |
|---|---|---|
| **Director Humano** | Autoridad suprema. Ratifica IDs, línea base financiera, varianzas y cierre. | No opera el motor ni sustituye al Juez. |
| **Arquitecto saliente** | Ejecuta `AKT_Pmpt.md`; declara hitos, decisiones, deudas y siguiente movimiento con evidencia. | No consolida `KDB.md` ni archiva su propio delta. |
| **Constructor** | Ejecuta `KDB_Act_Pmpt.md`; actualiza `KDB.md`; archiva por copia; reinicia `AKT.md`; hace pasar al Juez. | No legisla por conveniencia ni modifica el Juez para obtener verde. |
| **Arquitecto entrante** | Emite el Eco de Comprensión y valida la transferencia contra el estado real. | No asume el turno sin Eco ni sin evidencia. |
| **The Shield** | Certifica estructura, contenido crítico y gobernanza. | No negocia el resultado: falla o pasa. |

---

## 6. PROCEDIMIENTO OPERATIVO

### 6.1 Pre-vuelo obligatorio

Antes de tocar el paquete:

```powershell
git status --short
git rev-parse HEAD
.\.venv\Scripts\python.exe -m pytest qbe_core/tests/test_shield_ecosystem_governance.py -v
.\.venv\Scripts\python.exe -m pytest qbe_core/tests/test_shield_ktp_package_integrity.py -v
```

Si el Juez de gobernanza falla, **Alto al Fuego**. Si el Juez KTP falla por ausencia de paquete, es el estado RED esperado antes de materializar.

### 6.2 Despacho

1. Copiar la plantilla de `AKT_Pmpt.md`.
2. Ejecutar los comandos de evidencia.
3. Completar los 7 puntos.
4. Guardar como `docs/KTP/AKT.md`.
5. Verificar que no haya afirmaciones sin evidencia.

### 6.3 Consolidación

1. Leer `KDB.md` y `AKT.md`.
2. Contrastar cada dato con Git, The Shield y la bóveda fáctica.
3. Actualizar `KDB.md` sin borrar historia; cambiar versión y fecha.
4. Copiar `AKT.md` a `history/AKT_{YYYY-MM-DD}_{SPRINT}.md`.
5. Verificar que la copia sea byte a byte idéntica.
6. Reiniciar `AKT.md` desde la plantilla.
7. Ejecutar el Juez KTP y la suite unificada.
8. Commit de consolidación.

### 6.4 Asunción

1. Leer `KDB.md`.
2. Leer el `AKT.md` activo y, si aplica, el último archivo de `history/`.
3. Emitir el Eco de Comprensión.
4. Esperar la autorización del Director antes de ejecutar el Motor de 3 Pasos.

---

## 7. REGLAS DE VERSIONADO

### 7.1 `KDB.md`

- Versionado semántico: `MAJOR.MINOR.PATCH`.
- `MAJOR`: cambio de doctrina, topología o invariante.
- `MINOR`: nueva sección, nuevo ID, nueva deuda declarada.
- `PATCH`: corrección factual, cifra, enlace o errata.
- Toda consolidación actualiza `**Versión:**`, `**Última consolidación:**` y el `AKT` de origen.

### 7.2 `AKT.md`

- Un `AKT.md` por sprint o turno de transferencia.
- No se reutiliza el nombre de un sprint anterior.
- Se archiva como `AKT_{YYYY-MM-DD}_{SPRINT}.md`.
- El activo se reinicia, no se borra.

### 7.3 `history/`

- Archivo inmutable: no se edita, no se renombra y no se elimina.
- Si el nombre destino ya existe, el proceso falla en vez de sobrescribir.
- El archivo histórico conserva el contenido exacto del `AKT.md` cerrado.

### 7.4 Git

- Un commit atómico por consolidación.
- Mensaje sugerido: `docs(KTP): consolidar KDB y archivar AKT {SPRINT}`.
- No se incluyen bases de datos, snapshots, `.pytest_cache`, `data/sondas_exploracion/` ni artefactos temporales.
- El manifiesto `git status --short` se adjunta al cierre.

---

## 8. CRITERIOS DE ACEPTACIÓN FIDUCIARIA

Una transferencia se considera cerrada solo si se cumplen todos:

1. Los cinco archivos rectores existen y superan el umbral mínimo de contenido.
2. `history/` existe y el acta cerrada está archivada por copia.
3. `AKT.md` sigue existiendo después del archivo.
4. `KDB.md` contiene la Autoridad Suprema, los 11 invariantes, los 4 pilares, los puertos y el estado fáctico vigente.
5. El Juez KTP devuelve `4/4 PASSED`.
6. La suite unificada devuelve `EXIT CODE 0`.
7. El pre-vuelo de cartelera devuelve `0 🔴` cuando aplique.
8. No hay cambios en código de producción ni escrituras en bases vivas.
9. El manifiesto Git Diff solo contiene los archivos del expediente.
10. Toda cifra financiera declarada tiene provenance; toda cifra no verificada se marca `SIN EVIDENCIA`.

---

## 9. ANTI-PATRONES

| Anti-patrón | Consecuencia | Corrección |
|---|---|---|
| Pegar el historial completo del chat en `KDB.md`. | Deriva, ruido y pérdida de foco. | Sintetizar en conocimiento estable; el detalle va a `history/`. |
| Acumular deudas cerradas en `AKT.md`. | El siguiente Arquitecto cree que siguen abiertas. | Cerrar y eliminar del delta; conservar solo deudas vivas. |
| Mover `AKT.md` a `history/` sin recrearlo. | El Juez falla por ausencia del activo. | Copiar, verificar y reiniciar. |
| Reutilizar un ID sellado. | Viola la inmutabilidad y rompe la trazabilidad. | `max + 1` y Ficha de Varianza si hay conflicto. |
| Inventar ROI, drawdown o cobertura. | Viola `[GOVERNANCE-01]`. | `SIN EVIDENCIA` o provenance declarada. |
| Modificar el Juez para obtener verde. | Destruye la función de The Shield. | Corregir el documento o detener el proceso. |
| Editar un acta de `history/`. | Borra la memoria institucional. | Crear una nueva acta; el histórico es inmutable. |

---

## 10. CHECKLIST DE BOLSILLO

- [ ] `git status --short` revisado.
- [ ] `git rev-parse HEAD` registrado.
- [ ] Juez de gobernanza en verde.
- [ ] `AKT.md` completo con los 7 puntos.
- [ ] `KDB.md` actualizado y versionado.
- [ ] Acta copiada a `history/AKT_{FECHA}_{SPRINT}.md`.
- [ ] `AKT.md` reiniciado y presente.
- [ ] Juez KTP 4/4.
- [ ] Suite unificada `EXIT CODE 0`.
- [ ] Pre-vuelo `0 🔴`.
- [ ] Manifiesto Git Diff emitido.

---

## 11. TRAZABILIDAD

- **Ley:** `docs/LOGIC.md` §15, `[LN-QBE-138]`.
- **Arquitectura:** `docs/ARCH.md` §14, `[ARCH-1.4.74]`.
- **Registro:** `docs/ID_REGISTRY.md`.
- **Juez:** `qbe_core/tests/test_shield_ktp_package_integrity.py`.
- **Cierre:** Juez 4/4 + suite unificada + pre-vuelo sin 🔴.

> Esta guía no sustituye a `KDB.md` ni a `AKT.md`. Es el contrato de cómo se producen, se consolidan y se relevan.
