# KDB_Act_Pmpt — PROMPT DE CONSOLIDACIÓN Y ARCHIVO DEL KTP

**Documento:** `KDB_Act_Pmpt.md`  
**Versión:** 1.0.0  
**Uso:** copiar y ejecutar por el Constructor al cerrar un ciclo de transferencia.  
**Entrada:** `docs/KTP/AKT.md` + `docs/KTP/KDB.md` + estado real del repositorio.  
**Salida:** `KDB.md` actualizado + `history/AKT_{FECHA}_{SPRINT}.md` + `AKT.md` reiniciado.  
**Nodos:** `[LN-QBE-138]` / `[ARCH-1.4.74]`

---

## INSTRUCCIÓN AL CONSTRUCTOR

Eres el Constructor de consolidación del ecosistema Q-BE. Tu tarea no es escribir una nueva ley ni embellecer el KDB: es **contrastar el delta del `AKT.md` contra la realidad**, actualizar el conocimiento estable y archivar el acta sin romper la estructura quíntuple.

**Reglas absolutas:**

1. **Cero invención.** Si un dato no se puede verificar, se marca `SIN EVIDENCIA`; no se completa por inferencia.
2. **Cero escritura en bases vivas.** La inspección de `qbe_historico.db` es de solo lectura.
3. **Cero cambios en código de producción.** Este prompt solo toca `docs/KTP/` y, si el acta lo exige, los libros de gobierno.
4. **Cero reasignación de IDs.** Los IDs sellados no se tocan.
5. **Cero pérdida del activo.** `AKT.md` se archiva por copia y se reinicia; nunca se mueve sin recrearlo.
6. **Cero verde forzado.** Si el Juez falla, se corrige el documento o se emite `DIRGEN_VARIANCE_REQUEST.md`; no se modifica el Juez para pasar.
7. **Cero secretos.** No se incluyen credenciales, tokens ni rutas personales.

---

## PASO 0 — PRE-VUELO DE ESTADO

Ejecutar y registrar:

```powershell
git rev-parse HEAD
git status --short
git log -3 --oneline
.\.venv\Scripts\python.exe -m pytest qbe_core/tests/test_shield_ecosystem_governance.py -q --no-header
.\.venv\Scripts\python.exe -m pytest qbe_core/tests/test_shield_ktp_package_integrity.py -q --no-header
```

**Criterio de aborto:** si el Juez de gobernanza falla, o si `docs/KTP/` no contiene los cinco archivos rectores y `history/`, detener y emitir Ficha de Varianza. No consolidar sobre un paquete incompleto.

---

## PASO 1 — LEER EL DELTA Y VERIFICAR HECHOS

1. Leer `docs/KTP/AKT.md` completo.
2. Leer `docs/KTP/KDB.md` completo.
3. Identificar cada afirmación factual del AKT:
   - commits, branch y estado del working tree;
   - resultados de The Shield;
   - cifras de la bóveda fáctica;
   - deudas y decisiones.
4. Contrastar con el repositorio real. Si hay conflicto entre AKT y realidad, **prevalece la realidad**; el AKT se corrige antes de consolidar.
5. Verificar la bóveda histórica en modo read-only:

```powershell
@'
import sqlite3
c = sqlite3.connect(r'qbe_observatory/data/qbe_historico.db')
print('matches', c.execute('select count(*) from historical_matches').fetchone()[0])
print('odds', c.execute('select count(*) from historical_matches where odd_home is not null and odd_draw is not null and odd_away is not null').fetchone()[0])
print('seasons', c.execute('select count(distinct temporada) from historical_matches').fetchone()[0])
c.close()
'@ | & .\.venv\Scripts\python.exe -
```

No ejecutar `INSERT`, `UPDATE`, `DELETE`, `CREATE`, `DROP` ni `VACUUM`. No tocar `data/qbe_database.db` ni el snapshot.

---

## PASO 2 — ACTUALIZAR `KDB.md`

Actualizar, como mínimo:

1. **Cabecera:** `Versión`, `Última consolidación`, `Fuente de la consolidación`.
2. **Topología:** puertos, rutas y fronteras CQRS si cambiaron.
3. **Invariantes:** solo si una ley aprobada cambió; en ese caso, citar la Ficha de Varianza.
4. **Variables:** altas, bajas o cambios de fuente.
5. **Bóveda fáctica:** partidos, cuotas, temporadas, filas de stats y cobertura xG.
6. **Estado financiero:** distinguir siempre `declarado` de `auditado`.
7. **Mapa de intervención:** rutas y Jueces si cambió la arquitectura.
8. **Deudas abiertas:** eliminar las cerradas del delta, conservar las vivas.
9. **Trazabilidad:** acta de origen y fecha.

**Regla de edición:** no borrar historia. Si una sección queda obsoleta, se reemplaza por la versión vigente y se deja el rastro en el acta histórica.

### 2.1 Versionado

- `MAJOR`: cambio de doctrina, topología o invariante.
- `MINOR`: nueva sección, nuevo ID o nueva deuda declarada.
- `PATCH`: corrección factual, cifra, enlace o errata.

Registrar el motivo del cambio en el encabezado o en una nota de consolidación.

---

## PASO 3 — ARCHIVAR `AKT.md` POR COPIA

**Nombre canónico:**

```text
docs/KTP/history/AKT_{YYYY-MM-DD}_{SPRINT}.md
```

Ejemplo:

```text
docs/KTP/history/AKT_2026-10-30_SPRINT-38.md
```

Procedimiento:

1. Verificar que el nombre destino no exista. Si existe, **abortar**; no sobrescribir.
2. Copiar el contenido exacto de `AKT.md` al destino.
3. Verificar que la copia sea byte a byte idéntica (hash o comparación de contenido).
4. **No borrar** `AKT.md`.
5. Reiniciar `AKT.md` desde la plantilla de `AKT_Pmpt.md`, con el siguiente sprint y estado `ABIERTO`.

Comandos de referencia (PowerShell):

```powershell
$fecha = '2026-10-30'
$sprint = 'SPRINT-38'
$destino = "docs/KTP/history/AKT_${fecha}_${sprint}.md"
if (Test-Path $destino) { throw "El acta destino ya existe: $destino" }
Copy-Item -LiteralPath 'docs/KTP/AKT.md' -Destination $destino
$hashOrigen = (Get-FileHash 'docs/KTP/AKT.md' -Algorithm SHA256).Hash
$hashDestino = (Get-FileHash $destino -Algorithm SHA256).Hash
if ($hashOrigen -ne $hashDestino) { throw 'La copia del acta no es idéntica' }
```

Después de la copia, reiniciar el activo sin alterar el archivo histórico.

**Prohibido:** `Move-Item` o `git mv` sin recrear `AKT.md` en el mismo acto. El Juez falla si el activo desaparece.

---

## PASO 4 — VALIDAR EL PAQUETE

```powershell
.\.venv\Scripts\python.exe -m pytest qbe_core/tests/test_shield_ktp_package_integrity.py -v
.\.venv\Scripts\python.exe -m pytest qbe_core/tests qbe_business/tests qbe_ingestion/tests qbe_observatory/tests qbe_storage/tests -q --no-header
```

**Criterios:**

- Juez KTP: `4/4 PASSED`.
- Suite unificada: `EXIT CODE 0`.
- `docs/KTP/` conserva los 5 archivos y `history/`.
- `AKT.md` existe y está reiniciado.
- El acta histórica existe y es idéntica a la cerrada.
- `git status --short` no incluye bases de datos, snapshots ni `data/sondas_exploracion/`.

Si el Juez falla por contenido, corregir `KDB.md` o `AKT.md`. Si falla por estructura, completar el paquete. **No modificar el Juez.**

---

## PASO 5 — PRE-VUELO DE CARTELERA (SI APLICA)

Si el acta tocó ingesta, motores estocásticos o cartelera:

```powershell
$env:DATABASE_URL='sqlite:///data/snapshots/qbe_database_snapshot.db'
.\.venv\Scripts\python.exe -m qbe_ingestion.src.ingestion.coherence_auditor --check
```

**Criterio:** `0 🔴` y `EXIT 0`. Las 🟡 son advertencias informativas; no bloquean, pero deben registrarse.

---

## PASO 6 — COMMIT DE CONSOLIDACIÓN

1. Revisar el diff:

```powershell
git diff -- docs/KTP docs/LOGIC.md docs/ARCH.md docs/ID_REGISTRY.md
git status --short
```

2. Confirmar que no hay cambios fuera del expediente.
3. Commit atómico:

```powershell
git add docs/KTP docs/LOGIC.md docs/ARCH.md docs/ID_REGISTRY.md qbe_core/tests/test_shield_ktp_package_integrity.py
git commit -m "docs(KTP): consolidar KDB y archivar AKT {SPRINT}"
```

No agregar `data/`, `*.db`, `.pytest_cache/`, `data/sondas_exploracion/` ni artefactos temporales.

4. Emitir el manifiesto:

```powershell
git status --short
git log -1 --stat
```

---

## PASO 7 — REPORTE DE CONSOLIDACIÓN

Completar y entregar:

```markdown
# REPORTE DE CONSOLIDACIÓN KTP

- **Sprint consolidado:** {SPRINT}
- **Fecha:** {YYYY-MM-DD}
- **KDB:** {versión anterior} → {versión nueva}
- **Acta archivada:** docs/KTP/history/AKT_{FECHA}_{SPRINT}.md
- **Hash del acta:** {SHA-256}
- **AKT reiniciado:** {SÍ/NO}
- **Juez KTP:** {N/N PASSED}
- **Suite unificada:** {EXIT CODE}
- **Pre-vuelo:** {0 🔴 / no aplica}
- **Archivos modificados:** {lista}
- **Deudas cerradas:** {lista}
- **Deudas abiertas:** {lista}
- **Observaciones:** {texto}
```

---

## CRITERIOS DE ABORTO

Detener y emitir `DIRGEN_VARIANCE_REQUEST.md` si:

1. El Juez KTP falla y la causa es una contradicción de ley, no un archivo faltante.
2. El acta destino ya existe y no se puede archivar sin sobrescribir.
3. `AKT.md` no se puede reiniciar sin perder contenido.
4. La bóveda fáctica no coincide con el AKT y no hay explicación verificable.
5. Aparece un cambio de código de producción no declarado en el expediente.
6. Se pretende reasignar un ID sellado.

**Nunca** se resuelve un aborto modificando el Juez, inventando datos o borrando historia.
