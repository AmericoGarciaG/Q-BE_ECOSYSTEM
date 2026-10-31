# AKT_Pmpt — PROMPT DE EXTRACCIÓN DE CONTEXTO SALIENTE

**Documento:** `AKT_Pmpt.md`  
**Versión:** 1.0.0  
**Uso:** copiar y ejecutar al cierre de un turno o sprint.  
**Salida:** `docs/KTP/AKT.md`  
**Nodos:** `[LN-QBE-138]` / `[ARCH-1.4.74]`

---

## INSTRUCCIÓN AL ARQUITECTO SALIENTE

Eres el Arquitecto saliente del ecosistema Q-BE. Tu tarea es producir el **delta de contexto** del turno que cierras, no una memoria histórica ni un resumen narrativo.

**Reglas absolutas:**

1. No inventes datos. Si no puedes verificar algo, escribe `SIN EVIDENCIA` y explica qué falta.
2. No pegues el historial del chat. Sintetiza.
3. No incluyas deudas ya cerradas. Solo deudas vivas.
4. No afirmes que una prueba pasa sin el comando y el resultado real.
5. No uses rutas `archivo:línea` para IDs canónicos; usa anclajes simbólicos (`docs/ARCH.md` + ID).
6. No propongas más de un “siguiente movimiento”. La transferencia debe ser accionable.
7. Si una cifra financiera es declarada y no auditada, dilo explícitamente.

**Evidencia mínima que debes recoger antes de redactar:**

```powershell
git rev-parse HEAD
git status --short
git log -5 --oneline
.\.venv\Scripts\python.exe -m pytest qbe_core/tests/test_shield_ecosystem_governance.py -q --no-header
.\.venv\Scripts\python.exe -m pytest qbe_core/tests/test_shield_ktp_package_integrity.py -q --no-header
```

Si el turno tocó datos o ingesta, añade la consulta de lectura correspondiente y el pre-vuelo de cartelera:

```powershell
$env:DATABASE_URL='sqlite:///data/snapshots/qbe_database_snapshot.db'
.\.venv\Scripts\python.exe -m qbe_ingestion.src.ingestion.coherence_auditor --check
```

---

## PLANTILLA OBLIGATORIA DE 7 PUNTOS

Copia esta estructura y complétala sin cambiar el orden:

```markdown
# AKT — REPORTE ACTIVO DE TRANSFERENCIA

**Sprint:** {SPRINT}
**Fecha:** {YYYY-MM-DD}
**Autoridad:** Américo García Guerrero (Director Humano)
**Arquitecto saliente:** {rol / instancia}
**Estado:** {ABIERTO | CERRADO | PENDIENTE DE CONSOLIDACIÓN}

## 1. SPRINT ACTUAL

- **Nombre:** {SPRINT}
- **Objetivo:** {una frase}
- **Alcance:** {archivos/pilares}
- **Régimen:** {DIRGEN-STRICT | DBBD-FUNGIBLE | HÍBRIDO}
- **Fecha de inicio / cierre:** {fechas}

## 2. HITOS CONCLUIDOS

| Hito | Evidencia | Estado |
|---|---|---|
| {hito} | {comando, archivo, ID o dato} | {COMPLETADO} |

## 3. DECISIONES TOMADAS

| Decisión | Razón | Impacto | Anclaje |
|---|---|---|---|
| {decisión} | {por qué} | {qué cambia} | {ID / documento} |

## 4. DEUDAS ABIERTAS

| Deuda | Severidad | Impacto | Siguiente acción | Responsable |
|---|---|---|---|---|
| {deuda} | {ALTA/MEDIA/BAJA} | {qué bloquea} | {acción concreta} | {rol} |

> Regla: si una deuda ya se cerró, no aparece aquí. Se conserva en `history/` o en el commit, no en el delta.

## 5. ESTADO FÁCTICO GIT / SHIELD

- **Branch:** {branch}
- **HEAD:** {hash corto} — {fecha}
- **Working tree:** {limpio / archivos no trackeados}
- **Juez de gobernanza:** {N passed / N failed}
- **Juez KTP:** {N/N PASSED | RED}
- **Suite unificada:** {comando} → {EXIT CODE}
- **Pre-vuelo de cartelera:** {0 🔴 | N 🔴 | no aplica}
- **Bóveda fáctica:** {partidos, cuotas, temporadas, DB}
- **Datos no verificados:** {lista o “ninguno”}

## 6. BACKLOG INMEDIATO

| Prioridad | Tarea | Criterio de aceptación |
|---:|---|---|
| 1 | {tarea} | {test/comando/resultado} |
| 2 | {tarea} | {test/comando/resultado} |

## 7. SIGUIENTE MOVIMIENTO

- **Acción única:** {la siguiente acción concreta}
- **Comando / punto de entrada:** {comando o archivo}
- **Resultado esperado:** {salida verificable}
- **Riesgo principal:** {riesgo}
- **Criterio de aborto:** {cuándo detenerse y emitir Ficha de Varianza}
```

---

## CRITERIOS DE CALIDAD DEL AKT

1. **Trazable:** cada afirmación tiene comando, archivo, ID o dato.
2. **Fechado:** el sprint y la fecha son explícitos.
3. **Accionable:** el siguiente movimiento se puede ejecutar sin preguntar.
4. **Honesto:** lo no verificado se declara `SIN EVIDENCIA`.
5. **Breve:** el delta no debe superar lo necesario para transferir el turno.
6. **Sin duplicación:** no repite secciones completas de `KDB.md`; las referencia.

---

## PROHIBICIONES ESPECÍFICAS

- No escribir “todo verde” sin el comando y el `EXIT CODE`.
- No escribir “The Shield blindado” si la suite unificada no se ejecutó.
- No presentar `+5.85%` como ROI auditado si solo es línea base declarada.
- No incluir credenciales, tokens, rutas personales ni datos sensibles.
- No modificar `KDB.md` desde este prompt; la consolidación es del Constructor.

---

## SALIDA

Guardar el resultado como `docs/KTP/AKT.md`. Si el paquete aún no existe, crear el directorio y el archivo, pero no inventar un histórico. El Juez KTP validará la presencia y el contenido crítico.
