"""Refresco atómico del snapshot de backtesting (fuera de la app).

Ciclo de vida gobernado `[DBBD-FUNGIBLE]`:

1. purga del temporal huérfano de una corrida fallida;
2. copia online con `sqlite3.Connection.backup` desde la BD viva en `mode=ro`;
3. verificación de la copia (`PRAGMA quick_check` + conteo mínimo de partidos)
   **antes** de publicarla — un snapshot corrupto jamás sustituye al bueno;
4. publicación atómica con `os.replace` (mismo volumen);
5. reporte de bytes, SHA-256 y frescura.

La BD de origen se abre siempre en solo lectura: el Observatorio no escribe la
bóveda transaccional ni siquiera para clonarla.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Optional

_TABLA_CONTRATO = "matches"


def edad_snapshot(ruta: Path) -> Optional[float]:
    """Edad en segundos; `None` si el snapshot no existe."""
    if not ruta.is_file():
        return None
    return max(0.0, time.time() - ruta.stat().st_mtime)


def snapshot_fresco(ruta: Path, max_age_minutes: int = 60) -> bool:
    """Verdadero si el snapshot existe y no supera la edad máxima declarada."""
    edad = edad_snapshot(ruta)
    return edad is not None and edad <= max_age_minutes * 60


def huella_sha256(ruta: Path) -> str:
    """SHA-256 por streaming: no carga los ~11 MB completos en memoria."""
    digest = hashlib.sha256()
    with ruta.open("rb") as manejador:
        for bloque in iter(lambda: manejador.read(1024 * 1024), b""):
            digest.update(bloque)
    return digest.hexdigest()


def _uri_solo_lectura(ruta: Path) -> str:
    return f"file:{ruta.resolve().as_posix()}?mode=ro"


def _limpiar_sidecars(ruta: Path) -> None:
    """Borra los sidecars `-wal`/`-shm` de `ruta`.

    Un lector `mode=ro` no puede crear ni eliminar estos archivos: si el snapshot
    nace en modo WAL, cada lectura deja basura junto a la vitrina. El snapshot se
    normaliza a journal rollback y, como defensa, sus sidecars se purgan.
    """
    for sufijo in ("-wal", "-shm"):
        ruta.with_name(ruta.name + sufijo).unlink(missing_ok=True)


def _verificar_copia(ruta: Path, minimo_partidos: int, exigir_contrato: bool) -> int:
    """Verifica la copia EN SOLO LECTURA antes de publicarla.

    Devuelve el número de filas de `matches`. Levanta `RuntimeError` si la copia
    no supera `quick_check` o no alcanza el mínimo declarado: en ese caso el
    snapshot previo (si existe) permanece intacto.

    `exigir_contrato=True` (por omisión) exige la tabla `matches`, que es lo que
    el Observatorio consume. El CLI genérico puede desactivarlo para copiar
    cualquier SQLite (por ejemplo en pruebas de atomicidad).
    """
    conexion = sqlite3.connect(_uri_solo_lectura(ruta), uri=True, timeout=5.0)
    try:
        chequeo = conexion.execute("PRAGMA quick_check").fetchone()
        estado = str(chequeo[0]).strip().lower() if chequeo else "sin_respuesta"
        if estado != "ok":
            raise RuntimeError(f"copia corrupta: PRAGMA quick_check={estado!r}")

        existe = conexion.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
            (_TABLA_CONTRATO,),
        ).fetchone()
        if not existe or int(existe[0]) == 0:
            if exigir_contrato:
                raise RuntimeError(
                    f"copia sin contrato: falta la tabla {_TABLA_CONTRATO}"
                )
            return 0

        filas = conexion.execute(
            f"SELECT COUNT(*) FROM {_TABLA_CONTRATO}"
        ).fetchone()
        total = int(filas[0]) if filas else 0
    finally:
        conexion.close()

    if total < minimo_partidos:
        raise RuntimeError(
            f"copia incompleta: {_TABLA_CONTRATO}={total} < mínimo {minimo_partidos}"
        )
    return total


def refrescar_snapshot(
    origen: Path,
    destino: Path,
    max_age_minutes: int = 60,
    ensure_dir: bool = True,
    minimo_partidos: int = 1,
    exigir_contrato: bool = True,
) -> Dict[str, Any]:
    """Copia online con `Connection.backup`, verifica, publica atómicamente y reporta.

    `ensure_dir=True` (por omisión) crea el directorio destino de forma
    idempotente. Con `ensure_dir=False` el directorio debe existir: el CLI
    expone esa variante como `--no-ensure-dir` para modos estrictos de cron.
    """
    origen = Path(origen).resolve()
    destino = Path(destino).resolve()

    if not origen.is_file():
        raise FileNotFoundError(f"BD origen no disponible: {origen}")

    if ensure_dir:
        destino.parent.mkdir(parents=True, exist_ok=True)
    elif not destino.parent.is_dir():
        raise FileNotFoundError(f"directorio destino ausente: {destino.parent}")

    temporal = destino.with_name(destino.name + ".tmp")
    # Purga del residuo de una corrida anterior interrumpida.
    temporal.unlink(missing_ok=True)
    _limpiar_sidecars(temporal)

    try:
        con_origen = sqlite3.connect(_uri_solo_lectura(origen), uri=True, timeout=5.0)
        con_destino = sqlite3.connect(temporal.as_posix())
        try:
            con_origen.backup(con_destino)
            # Journal rollback en la copia: el snapshot se consume SIEMPRE en
            # `mode=ro`, y un lector read-only no puede crear/eliminar `-wal`/`-shm`.
            con_destino.execute("PRAGMA journal_mode=DELETE")
            con_destino.commit()
        finally:
            con_destino.close()
            con_origen.close()

        filas = _verificar_copia(temporal, minimo_partidos, exigir_contrato)
        os.replace(temporal, destino)
        _limpiar_sidecars(temporal)
    except BaseException:
        temporal.unlink(missing_ok=True)
        _limpiar_sidecars(temporal)
        raise

    return {
        "origen": str(origen),
        "destino": str(destino),
        "sha256": huella_sha256(destino),
        "bytes": destino.stat().st_size,
        "filas_matches": filas,
        "edad_segundos": edad_snapshot(destino),
        "fresco": snapshot_fresco(destino, max_age_minutes),
        "max_age_minutos": max_age_minutes,
    }
