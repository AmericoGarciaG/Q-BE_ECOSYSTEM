# -*- coding: utf-8 -*-
"""
🏆 Q-BE PERSISTENCE GATEWAY — CENTRAL DATA ACCESS & UNIT OF WORK
[VAULT-DATA-001] Motor Transaccional SQLite WAL con Foreign Keys y Aislamiento de Contextos.
Base de Gobierno: Kybern Framework v13.5 [ARCH-1.5.1]
"""

import os
import sqlite3
import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Generator, Optional
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from src.config import settings

logger = logging.getLogger("PersistenceGateway")


def _configurar_conexion_sqlite(dbapi_connection, connection_record):
    """[ARCH-1.5.1] PRAGMAs de sesión para UNA instancia de motor, nunca para la clase.

    Regla de aislamiento: esta función se registra con `event.listen(self.engine, ...)`
    dentro de `_init_engine`. Jamás debe decorarse con `@event.listens_for(Engine, ...)`:
    ese registro de clase contamina todos los engines del proceso y rompe las conexiones
    ajenas abiertas con `mode=ro` (`attempt to write a readonly database`).

    Guarda fiduciaria: `PRAGMA query_only` es un cinturón semántico (en una conexión
    `mode=ro` recién abierta devuelve 0). La garantía real es capturar
    `sqlite3.OperationalError` al intentar escribir WAL/synchronous: una conexión de
    solo lectura o `immutable=1` debe seguir siendo usable para leer.
    """
    if not isinstance(dbapi_connection, sqlite3.Connection):
        return

    cursor = dbapi_connection.cursor()
    try:
        # Seguros también en solo lectura: no escriben el archivo.
        cursor.execute("PRAGMA busy_timeout = 15000;")
        cursor.execute("PRAGMA foreign_keys = ON;")

        # Cinturón: si la sesión ya se declaró de solo lectura, no intentar WAL.
        try:
            cursor.execute("PRAGMA query_only;")
            fila = cursor.fetchone()
            es_readonly = bool(fila and fila[0] == 1)
        except sqlite3.OperationalError:
            es_readonly = True
        if es_readonly:
            return

        # Guarda real: WAL exige escribir la cabecera; en `mode=ro` falla y se ignora.
        try:
            cursor.execute("PRAGMA journal_mode = WAL;")
            cursor.execute("PRAGMA synchronous = NORMAL;")
        except sqlite3.OperationalError as exc:
            logger.debug(
                "🔒 [GATEWAY PRAGMA] WAL/synchronous omitidos en conexión no escribible: %s",
                exc,
            )
    finally:
        cursor.close()


class PersistenceGateway:
    _instance = None

    def __new__(cls, db_url: Optional[str] = None):
        if cls._instance is None:
            instancia = super(PersistenceGateway, cls).__new__(cls)
            instancia._init_engine(db_url=db_url)
            cls._instance = instancia
        return cls._instance

    def _init_engine(self, db_url: Optional[str] = None):
        """Construye el motor y liga el listener de PRAGMAs a ESTA instancia.

        `db_url` permite inyectar una bóveda efímera (jueces, herramientas) sin
        depender de `settings.DATABASE_URL`; el singleton lo honra sólo en la
        primera construcción.
        """
        url = db_url or settings.DATABASE_URL
        connect_args = {"check_same_thread": False} if "sqlite" in url else {}

        self.engine = create_engine(
            url,
            connect_args=connect_args,
            pool_pre_ping=True
        )
        # [ARCH-1.5.1] Registro por instancia: la clase global `Engine` queda intacta.
        event.listen(self.engine, "connect", _configurar_conexion_sqlite)
        self.SessionFactory = sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False
        )
        self._verify_database_health()

    def _verify_database_health(self):
        """Ejecuta PRAGMA quick_check al arranque para detectar corrupción."""
        with self.engine.connect() as conn:
            result = conn.exec_driver_sql("PRAGMA quick_check;").scalar()
            if result != "ok":
                raise RuntimeError(f"🚨 FATAL: Base de datos corrupta: {result}")
            logger.info("🛡️ [GATEWAY HEALTH] SQLite integrity verified: OK (FK activas)")

    @contextmanager
    def read_session(self) -> Generator[Session, None, None]:
        """
        Contexto de Solo Lectura (FastAPI UI / Endpoints).
        No-lock, ultraligero (< 2ms), auto-close garantizado.
        """
        session: Session = self.SessionFactory()
        try:
            yield session
        finally:
            session.close()

    @contextmanager
    def write_transaction(self) -> Generator[Session, None, None]:
        """
        Contexto de Escritura Atómica (Unit of Work para Daemons).
        Commit automático si todo es exitoso; ROLLBACK total ante cualquier excepción.
        """
        session: Session = self.SessionFactory()
        try:
            yield session
            session.commit()
        except Exception as ex:
            session.rollback()
            logger.error(f"❌ [GATEWAY ROLLBACK] Transacción abortada por excepción: {ex}")
            raise ex
        finally:
            session.close()

    def create_all_tables(self, base_metadata):
        """Crea todas las tablas declaradas en el esquema ORM."""
        base_metadata.create_all(bind=self.engine)
        logger.info("✅ [GATEWAY TABLES] Esquema relacional 3NF sincronizado.")

    # ── [ARCH-1.4.55] Respaldo atómico de la bóveda (continuidad de operación) ────────────────
    def _ruta_sqlite_local(self) -> str:
        """Ruta física del archivo SQLite gobernado por el motor (`RuntimeError` si no aplica)."""
        url = self.engine.url
        backend = url.get_backend_name()
        if backend != "sqlite":
            raise RuntimeError(
                f"🚨 [GATEWAY BACKUP] El respaldo atómico exige SQLite; motor declarado: {backend}."
            )
        archivo = url.database
        if not archivo or archivo == ":memory:":
            raise RuntimeError(
                "🚨 [GATEWAY BACKUP] La bóveda no tiene archivo físico (URL en memoria): "
                "no existe nada que respaldar."
            )
        return os.path.abspath(archivo)

    def crear_backup_boveda_sqlite(self, directorio_destino: Optional[str] = None) -> str:
        """[ARCH-1.4.55] Copia CONSISTENTE de la bóveda vía la API online de SQLite.

        `sqlite3.Connection.backup` es la única lectura segura bajo WAL con escritores activos:
        no bloquea al daemon de captura ni congela el journal. El respaldo se verifica con
        `PRAGMA quick_check` antes de declararse válido; una copia corrupta JAMÁS se publica
        (se elimina y se lanza `RuntimeError`).

        Se invoca EXPLÍCITAMENTE al inicio del lote (jamás por escritura). Devuelve la ruta
        absoluta del respaldo materializado en
        `data/backups/qbe_database_backup_{YYYYMMDD_HHMMSS}.db` por omisión.
        """
        origen = self._ruta_sqlite_local()
        if not os.path.isfile(origen):
            raise RuntimeError(
                f"🚨 [GATEWAY BACKUP] La bóveda declarada no existe en disco: {origen}"
            )
        destino_dir = os.path.abspath(directorio_destino or os.path.join("data", "backups"))
        os.makedirs(destino_dir, exist_ok=True)
        marca = datetime.now().strftime("%Y%m%d_%H%M%S")
        destino = os.path.join(destino_dir, f"qbe_database_backup_{marca}.db")

        con_origen = sqlite3.connect(origen)
        con_destino = sqlite3.connect(destino)
        try:
            con_origen.backup(con_destino)
            fila = con_destino.execute("PRAGMA quick_check;").fetchone()
        finally:
            con_destino.close()
            con_origen.close()

        veredicto = str(fila[0]) if fila else "sin respuesta"
        if veredicto != "ok":
            try:
                os.remove(destino)
            except OSError:  # pragma: no cover — limpieza best-effort del artefacto inválido
                pass
            raise RuntimeError(
                f"🚨 [GATEWAY BACKUP] Respaldo corrupto ({veredicto}); copia descartada: {destino}"
            )
        logger.info(f"🛡️ [GATEWAY BACKUP] Bóveda respaldada y verificada: {destino}")
        return destino

