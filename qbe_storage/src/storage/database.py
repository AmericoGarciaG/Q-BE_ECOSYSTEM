"""Shim de compatibilidad: un solo engine, el del `PersistenceGateway` (WAL/FK).

El módulo original `src/storage/database.py` creaba un segundo engine sin PRAGMAs.
Aquí `get_db` delega en el gateway de forma perezosa, para que importar modelos no
abra una conexión ni cree una base de datos vacía.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.storage.base import Base


def get_db():
    from src.storage.gateway import PersistenceGateway

    db: Session = PersistenceGateway().SessionFactory()
    try:
        yield db
    finally:
        db.close()


def __getattr__(name: str):
    """Compatibilidad perezosa para imports históricos de `engine`/`SessionLocal`."""
    if name in {"engine", "SessionLocal"}:
        from src.storage.gateway import PersistenceGateway

        gateway = PersistenceGateway()
        return gateway.engine if name == "engine" else gateway.SessionFactory
    raise AttributeError(name)
