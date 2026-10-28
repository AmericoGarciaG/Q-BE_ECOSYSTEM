# -*- coding: utf-8 -*-
"""
🏆 THE SHIELD — FRONTERA DE DESPLIEGUE (SUBPROCESS + UVICORN NATIVO)
Juez Inmutable: [ARCH-ECOSYSTEM-DEPLOYMENT-BOUNDARY]
Base de Gobierno: Kybern Framework v13.5

Origen: expediente `DIAGNOSTICO-MODULENOTFOUNDERROR-INGESTION`.
El Escudo anterior importaba `service.app` **en el mismo proceso** de pytest, con el
mismo intérprete y el mismo `sys.path`; por eso no podía ver que el arranque real
(`uvicorn` en terminal) moría con `ModuleNotFoundError: No module named 'src.config'`.

Estos jueces cierran ese punto ciego de forma permanente:

  1. `test_invarianza_despliegue_arranque_nativo_subprocess`
     Lanza `python -m uvicorn src.ingestion.service:app` en un **proceso hijo** con
     `sys.executable`, `cwd=qbe_ingestion` y puerto efímero, y exige un HTTP 200 real
     en `/health`. Si el namespace `src` está incompleto, el juez falla ruidosamente
     con la salida cruda de uvicorn.

  2. `test_invarianza_despliegue_entrypoint_aborta_fuera_del_venv`
     Ejecuta `python -m src.ingestion` con el intérprete **base** (fuera del `.venv`)
     y exige `SystemExit` (código != 0) con el diagnóstico accionable, nunca un
     traceback opaco.

Convención: estos jueces asumen que la suite se ejecuta con el intérprete del
ecosistema (`Q_BE_ECOSYSTEM\\.venv\\Scripts\\python.exe`). Si se ejecutan con otro
intérprete, el juez 1 debe fallar — esa es exactamente su función.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

QBE_INGESTION = Path(__file__).resolve().parents[1]
ECOSYSTEM_ROOT = QBE_INGESTION.parent
TIMEOUT_ARRANQUE_S = 60.0
TIMEOUT_APAGADO_S = 15.0


# ── Utilidades de proceso ──────────────────────────────────────────────────────────────────────


def _puerto_efimero() -> int:
    """Reserva un puerto libre en loopback y lo libera para uvicorn."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sonda:
        sonda.bind(("127.0.0.1", 0))
        return int(sonda.getsockname()[1])


def _entorno_aislado(tmp_path: Path, puerto: int) -> dict:
    """Entorno hermético: sin red de scraping, sin bóveda viva y con puerto explícito."""
    entorno = os.environ.copy()
    entorno["KYBERN_NO_SCRAPE"] = "1"
    entorno["PYTHONIOENCODING"] = "utf-8"
    entorno["PORT_INGESTION"] = str(puerto)
    entorno["DATABASE_URL"] = f"sqlite:///{(tmp_path / 'deployment_boundary.db').as_posix()}"
    entorno.pop("QBE_INGESTION_URL", None)
    return entorno


def _detener(proceso: subprocess.Popen) -> str:
    """Termina el hijo y devuelve su salida completa (stdout + stderr fusionados)."""
    if proceso.poll() is None:
        proceso.terminate()
    try:
        salida, _ = proceso.communicate(timeout=TIMEOUT_APAGADO_S)
    except subprocess.TimeoutExpired:
        proceso.kill()
        salida, _ = proceso.communicate(timeout=TIMEOUT_APAGADO_S)
    return salida or ""


def _interprete_base() -> Path | None:
    """Localiza el intérprete fuera del entorno virtual (para el juez del guard)."""
    base = Path(sys.base_prefix)
    candidatos = [
        base / "python.exe",
        base / "Scripts" / "python.exe",
        base / "bin" / "python3",
        base / "bin" / "python",
    ]
    for candidato in candidatos:
        if candidato.is_file():
            return candidato
    return None


# ── Juez 1: arranque nativo en subproceso ─────────────────────────────────────────────────────


def test_invarianza_despliegue_arranque_nativo_subprocess(tmp_path: Path) -> None:
    """[FRONTERA DE DESPLIEGUE]: uvicorn debe levantar en un proceso hijo y servir /health."""
    puerto = _puerto_efimero()
    comando = [
        sys.executable,
        "-m",
        "uvicorn",
        "src.ingestion.service:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(puerto),
        "--log-level",
        "warning",
    ]
    proceso = subprocess.Popen(
        comando,
        cwd=str(QBE_INGESTION),
        env=_entorno_aislado(tmp_path, puerto),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    respuesta = None
    ultimo_error: Exception | None = None
    limite = time.monotonic() + TIMEOUT_ARRANQUE_S
    try:
        while time.monotonic() < limite:
            if proceso.poll() is not None:
                break
            try:
                candidata = httpx.get(f"http://127.0.0.1:{puerto}/health", timeout=1.0)
                if candidata.status_code == 200:
                    respuesta = candidata
                    break
            except Exception as exc:  # conexión rechazada mientras uvicorn importa
                ultimo_error = exc
            time.sleep(0.2)
    finally:
        salida = _detener(proceso)

    if respuesta is None:
        pytest.fail(
            "La frontera de despliegue NO arrancó: el servicio no respondió /health.\n"
            f"  comando            : {' '.join(comando)}\n"
            f"  cwd                : {QBE_INGESTION}\n"
            f"  intérprete         : {sys.executable}\n"
            f"  puerto efímero     : {puerto}\n"
            f"  último error HTTP  : {ultimo_error!r}\n"
            "  --- salida cruda de uvicorn ---\n"
            f"{salida}"
        )

    datos = respuesta.json()
    assert datos.get("status") == "ok", f"contrato /health roto: {datos!r}"
    assert datos.get("service") == "qbe_ingestion", f"servicio inesperado: {datos!r}"
    assert datos.get("port") == puerto, (
        f"/health reporta {datos.get('port')!r} pero uvicorn escuchó en {puerto}: "
        "PORT_INGESTION no está gobernando el puerto."
    )


# ── Juez 2: el entrypoint fail-loud aborta fuera del venv ─────────────────────────────────────


def test_invarianza_despliegue_entrypoint_aborta_fuera_del_venv() -> None:
    """[FAIL-LOUD]: `python -m src.ingestion` sin venv debe abortar con diagnóstico claro."""
    if sys.prefix == sys.base_prefix:
        pytest.skip("la suite no corre dentro de un entorno virtual: no hay intérprete base ajeno")

    interprete = _interprete_base()
    if interprete is None:
        pytest.skip(f"no se localizó el intérprete base en {sys.base_prefix!r}")

    entorno = os.environ.copy()
    entorno["PYTHONIOENCODING"] = "utf-8"
    proceso = subprocess.run(
        [str(interprete), "-m", "src.ingestion"],
        cwd=str(QBE_INGESTION),
        env=entorno,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=TIMEOUT_ARRANQUE_S,
    )
    salida = (proceso.stdout or "") + (proceso.stderr or "")

    assert proceso.returncode != 0, (
        "el entrypoint arrancó con un intérprete ajeno al .venv: el guard no disparó.\n"
        f"  intérprete : {interprete}\n  salida:\n{salida}"
    )
    for fragmento in ("[FALLO DE DESPLIEGUE]", "entorno virtual", ".venv", "src.ingestion --port"):
        assert fragmento in salida, (
            f"el diagnóstico no contiene {fragmento!r}.\n  salida:\n{salida}"
        )
