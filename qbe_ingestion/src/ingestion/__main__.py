# -*- coding: utf-8 -*-
"""Entrypoint fail-loud del Data Nexus (Ingesta).

Uso canónico (desde ``Q_BE_ECOSYSTEM\\qbe_ingestion``):

    ..\\.venv\\Scripts\\python.exe -m src.ingestion --port 8002

Motivo [DIAGNOSTICO-MODULENOTFOUNDERROR-INGESTION]: el paquete ``src`` es un namespace
PEP 420 que sólo se completa con las cinco instalaciones editables del ecosistema
(``qbe_core``, ``qbe_storage``, ``qbe_business``, ``qbe_observatory``, ``qbe_ingestion``).
Un intérprete ajeno al ``.venv`` deja ``src`` incompleto y ``from src.config import settings``
colapsa con ``ModuleNotFoundError`` en ``service.py:30``. Este guard convierte ese fallo
opaco en un diagnóstico accionable **antes** de importar FastAPI/uvicorn.

Contrato:
  * Fuera de un entorno virtual  -> ``SystemExit`` con código 1 y guía de operador.
  * ``src.config`` irresoluble   -> ``SystemExit`` con código 1 (falta ``qbe_storage``).
  * ``src.config`` sombreado     -> ``SystemExit`` con código 1 (resuelve fuera de qbe_storage).
  * Entorno sano                 -> arranca uvicorn con el puerto canónico.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from pathlib import Path
from typing import NoReturn, Optional, Sequence

_COMANDO_CANONICO = r"..\.venv\Scripts\python.exe -m src.ingestion --port 8002"
_ALTERNATIVA_UVICORN = (
    r"..\.venv\Scripts\python.exe -m uvicorn src.ingestion.service:app --port 8002"
)


def _forzar_utf8() -> None:
    """Garantiza que el diagnóstico sea legible aunque el stream use la *locale* (cp1252)."""
    for flujo in (sys.stdout, sys.stderr):
        reconfigurar = getattr(flujo, "reconfigure", None)
        if callable(reconfigurar):
            try:
                reconfigurar(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass


def _abortar(motivo: str, detalle: str = "") -> NoReturn:
    """Aborta el arranque con un diagnóstico accionable (nunca un traceback opaco)."""
    _forzar_utf8()
    lineas = [
        "",
        "=" * 78,
        "[FALLO DE DESPLIEGUE] Data Nexus (qbe_ingestion) no puede arrancar.",
        f"  Motivo  : {motivo}",
    ]
    if detalle:
        lineas.append(f"  Detalle : {detalle}")
    lineas.extend(
        [
            f"  Intérprete actual : {sys.executable}",
            f"  sys.prefix        : {sys.prefix}",
            f"  sys.base_prefix   : {sys.base_prefix}",
            "",
            "  Comando canónico (desde Q_BE_ECOSYSTEM\\qbe_ingestion):",
            f"      {_COMANDO_CANONICO}",
            "",
            "  Alternativa uvicorn nativa:",
            f"      {_ALTERNATIVA_UVICORN}",
            "=" * 78,
            "",
        ]
    )
    raise SystemExit("\n".join(lineas))


def _resolver(origen: str) -> Optional[str]:
    """Devuelve la ruta de origen del módulo sin ejecutarlo; ``None`` si no existe."""
    try:
        especificacion = importlib.util.find_spec(origen)
    except (ImportError, ValueError):
        return None
    if especificacion is None:
        return None
    return especificacion.origin


def _verificar_entorno() -> None:
    """Puerta única de arranque: intérprete correcto + namespace ``src`` completo."""
    if sys.prefix == sys.base_prefix:
        _abortar(
            "el intérprete no pertenece a un entorno virtual.",
            "El namespace `src` sólo se completa con las cinco instalaciones editables del .venv.",
        )

    origen_config = _resolver("src.config")
    if origen_config is None:
        _abortar(
            "`src.config` no es resolvible en este intérprete.",
            "Falta la instalación editable de qbe_storage (o el .venv fue reconstruido).",
        )
    ruta_config = Path(origen_config)
    if "qbe_storage" not in ruta_config.parts:
        _abortar(
            "`src.config` resuelve fuera de qbe_storage (sombreado de namespace).",
            f"origen inesperado: {ruta_config}",
        )

    if _resolver("src.storage") is None:
        _abortar(
            "`src.storage` no es resolvible en este intérprete.",
            "Falta la instalación editable de qbe_storage.",
        )


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Valida el despliegue y arranca uvicorn con el puerto canónico."""
    _verificar_entorno()

    # Importación diferida: el guard debe disparar antes que FastAPI/SQLAlchemy.
    import uvicorn

    from src.ingestion.service import _puerto, app

    parser = argparse.ArgumentParser(
        prog="python -m src.ingestion",
        description="Data Nexus — servicio REST de Ingesta (Q-BE Ecosystem).",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("HOST_INGESTION", "127.0.0.1"),
        help="Interfaz de escucha (default: HOST_INGESTION o 127.0.0.1).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Puerto de escucha (default: PORT_INGESTION / QBE_INGESTION_URL o 8002).",
    )
    parser.add_argument(
        "--log-level",
        default="info",
        choices=("critical", "error", "warning", "info", "debug", "trace"),
        help="Nivel de log de uvicorn.",
    )
    argumentos = parser.parse_args(argv)

    if argumentos.port is not None:
        # Coherencia de contrato: `/health` reporta `_puerto()`, que lee PORT_INGESTION.
        # Sin esto, `--port 8791` ligaría 8791 pero el servicio declararía 8002.
        os.environ["PORT_INGESTION"] = str(argumentos.port)
        puerto = argumentos.port
    else:
        puerto = _puerto()

    uvicorn.run(app, host=argumentos.host, port=puerto, log_level=argumentos.log_level)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
