"""Aduana CQRS: única puerta SQLite del Observatorio, estrictamente de solo lectura.

No importa SQLAlchemy. No expone `commit`, `executemany` ni helpers de escritura.
La garantía última es de SQLite (`mode=ro` + `PRAGMA query_only=ON`); la validación
de sentencia es defensa en profundidad para el código de producción.
"""

from __future__ import annotations

import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Sequence

_ESCRITURA = re.compile(
    r"\b(INSERT|UPDATE|DELETE|REPLACE|CREATE|DROP|ALTER|ATTACH|DETACH|VACUUM|PRAGMA)\b",
    re.IGNORECASE,
)
_SOLO_SELECT = re.compile(r"^\s*(SELECT|WITH)\b", re.IGNORECASE)


@contextmanager
def conexion_solo_lectura(ruta: str | Path) -> Iterator[sqlite3.Connection]:
    """Abre una conexión `mode=ro` y activa `query_only` antes de entregarla."""
    archivo = Path(ruta).resolve()
    if not archivo.is_file():
        raise FileNotFoundError(f"No existe la base de solo lectura: {archivo}")

    uri = f"file:{archivo.as_posix()}?mode=ro"
    conexion = sqlite3.connect(uri, uri=True, timeout=5.0)
    conexion.row_factory = sqlite3.Row
    try:
        conexion.execute("PRAGMA query_only = ON;")
        yield conexion
    finally:
        conexion.close()


def ejecutar_select(
    conexion: sqlite3.Connection,
    query: str,
    params: Sequence[Any] = (),
) -> list[sqlite3.Row]:
    """Ejecuta únicamente SELECT/WITH; cualquier intento de escritura es fail-loud."""
    if not _SOLO_SELECT.match(query):
        raise sqlite3.OperationalError("Solo se permiten consultas SELECT/WITH de solo lectura.")
    if _ESCRITURA.search(query):
        raise sqlite3.OperationalError("Sentencia de escritura rechazada por la aduana CQRS.")
    return conexion.execute(query, params).fetchall()


class BaseDatosSoloLectura:
    """Fachada mínima de lectura; una conexión por operación y cierre garantizado."""

    def __init__(self, ruta: str | Path) -> None:
        self.ruta = Path(ruta)

    @contextmanager
    def conexion(self) -> Iterator[sqlite3.Connection]:
        with conexion_solo_lectura(self.ruta) as conexion:
            yield conexion

    def ejecutar_select(self, query: str, params: Sequence[Any] = ()) -> list[sqlite3.Row]:
        with self.conexion() as conexion:
            return ejecutar_select(conexion, query, params)
