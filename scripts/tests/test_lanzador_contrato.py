# -*- coding: utf-8 -*-
"""Juez perimetral del Lanzador del Ecosistema (utilidad `[DBBD-FUNGIBLE]`).

No forma parte del comando canónico de The Shield; se ejecuta ad hoc:

    .\\.venv\\Scripts\\python.exe -m pytest scripts/tests -q

El Juez es de caja negra: no importa el módulo, lo invoca por CLI. Cubre

  * plan canónico y sensible al entorno;
  * fail-loud de entorno inválido y de puertos duplicados;
  * colisión real de puerto detectada antes de arrancar;
  * guardián AST: sin `src.*`/`qbe_core`/`sqlite3`, sin `shell=True`,
    sin `os.system` y sin `subprocess` invocando `git`;
  * integración opt-in de arranque y apagado ordenado (`QBE_LANZADOR_E2E=1`).
"""

from __future__ import annotations

import ast
import json
import os
import socket
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
LANZADOR = RAIZ / "scripts" / "lanzador_ecosistema.py"
PYTHON = RAIZ / ".venv" / "Scripts" / "python.exe"

VARIABLES_GOBERNADAS = (
    "PORT_INGESTION",
    "OBS_PORT",
    "QBE_INGESTION_URL",
    "QBE_BUSINESS_URL",
    "QBE_OBSERVATORY_URL",
    "HOST_INGESTION",
    "OBS_HOST",
)

PROHIBIDOS = {
    "src",
    "qbe_core",
    "qbe_storage",
    "qbe_business",
    "qbe_observatory",
    "qbe_ingestion",
    "sqlite3",
}

LLAMADAS_SHELL = {
    "subprocess.Popen",
    "subprocess.run",
    "subprocess.call",
    "subprocess.check_call",
    "subprocess.check_output",
}


# ── Utilidades ────────────────────────────────────────────────────────────────────────────────
def _entorno(extra: dict[str, str] | None = None) -> dict[str, str]:
    """Entorno hermético: borra las variables gobernadas y aplica las del caso."""
    entorno = {clave: valor for clave, valor in os.environ.items() if clave not in VARIABLES_GOBERNADAS}
    entorno["PYTHONIOENCODING"] = "utf-8"
    if extra:
        entorno.update(extra)
    return entorno


def _invocar(argumentos: list[str], extra: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(LANZADOR), *argumentos],
        cwd=str(RAIZ),
        env=_entorno(extra),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )


def _json(proceso: subprocess.CompletedProcess) -> dict:
    assert proceso.stdout.strip(), f"sin stdout; stderr={proceso.stderr!r}"
    return json.loads(proceso.stdout)


def _abrir(puerto: int) -> socket.socket:
    sonda = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
        sonda.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    sonda.bind(("127.0.0.1", puerto))
    sonda.listen(1)
    return sonda


def _puerto_libre(puerto: int) -> bool:
    try:
        sonda = _abrir(puerto)
    except OSError:
        return False
    sonda.close()
    return True


# ── Plan ─────────────────────────────────────────────────────────────────────────────────────
def test_plan_canonico_emite_los_tres_contratos() -> None:
    """Los tres argv, puertos y cwd son los legislados, sin abrir sockets."""
    proceso = _invocar(["--plan", "--json"])
    assert proceso.returncode == 0, proceso.stderr
    datos = _json(proceso)

    assert Path(datos["raiz"]).resolve() == RAIZ
    assert datos["interprete"] == str(PYTHON)

    pilares = {pilar["nombre"]: pilar for pilar in datos["pilares"]}
    assert list(pilares) == ["business", "observatory", "ingestion"]

    puertos = {nombre: pilar["puerto"] for nombre, pilar in pilares.items()}
    assert puertos == {"business": 8000, "observatory": 8001, "ingestion": 8002}

    assert pilares["business"]["argv"][1:] == [
        "-m", "uvicorn", "src.web.app:app",
        "--host", "127.0.0.1", "--port", "8000",
    ]
    assert pilares["observatory"]["argv"][1:] == [
        "-m", "uvicorn", "app.main:app",
        "--host", "127.0.0.1", "--port", "8001",
    ]
    assert pilares["ingestion"]["argv"][1:] == [
        "-m", "src.ingestion",
        "--host", "127.0.0.1", "--port", "8002",
    ]

    for pilar in pilares.values():
        assert Path(pilar["argv"][0]) == PYTHON
        assert Path(pilar["cwd"]).resolve() == RAIZ

    assert pilares["observatory"]["env"] == {"OBS_PORT": "8001"}
    assert pilares["ingestion"]["env"] == {"PORT_INGESTION": "8002"}
    assert "QBE_INGESTION_URL" not in pilares["business"]["env"]
    assert datos["advertencias"] == []


def test_plan_respeta_el_entorno_canonico() -> None:
    """`PORT_INGESTION` y `OBS_PORT` gobiernan argv y coherencia del puente."""
    proceso = _invocar(
        ["--plan", "--json"],
        {"PORT_INGESTION": "9102", "OBS_PORT": "9101"},
    )
    assert proceso.returncode == 0, proceso.stderr
    datos = _json(proceso)
    pilares = {pilar["nombre"]: pilar for pilar in datos["pilares"]}

    assert pilares["observatory"]["puerto"] == 9101
    assert pilares["ingestion"]["puerto"] == 9102
    assert pilares["observatory"]["argv"][-1] == "9101"
    assert pilares["ingestion"]["argv"][-1] == "9102"

    esperado = "http://127.0.0.1:9102"
    assert pilares["ingestion"]["env"]["QBE_INGESTION_URL"] == esperado
    assert pilares["business"]["env"]["QBE_INGESTION_URL"] == esperado


def test_entorno_invalido_aborta_sin_arrancar() -> None:
    """Un puerto no numérico es error de operador, no un fallback silencioso."""
    proceso = _invocar(["--plan", "--json"], {"PORT_INGESTION": "abc"})
    assert proceso.returncode == 2
    assert "PORT_INGESTION" in (proceso.stdout + proceso.stderr)


def test_puertos_duplicados_abortan() -> None:
    """La Mesa no puede compartir puerto con el Observatorio."""
    proceso = _invocar(["--plan", "--json"], {"PORT_INGESTION": "8001"})
    assert proceso.returncode == 2
    assert "8001" in (proceso.stdout + proceso.stderr)


def test_preflight_colision_falla_antes_de_arrancar() -> None:
    """Un puerto ocupado aborta con 3 y no deja procesos ni listeners propios."""
    for canonico in (8000, 8001, 8002):
        if not _puerto_libre(canonico):
            pytest.skip(f"el puerto canónico {canonico} ya está ocupado en esta máquina")

    sonda = _abrir(0)
    ocupado = int(sonda.getsockname()[1])
    try:
        proceso = _invocar(["--preflight", "--json"], {"PORT_INGESTION": str(ocupado)})
    finally:
        sonda.close()

    assert proceso.returncode == 3, (proceso.stdout, proceso.stderr)
    assert str(ocupado) in (proceso.stdout + proceso.stderr)
    assert _puerto_libre(8000) and _puerto_libre(8001)


# ── Guardián AST ─────────────────────────────────────────────────────────────────────────────
def _cadena(nodo: ast.AST) -> str:
    if isinstance(nodo, ast.Name):
        return nodo.id
    if isinstance(nodo, ast.Attribute):
        base = _cadena(nodo.value)
        return f"{base}.{nodo.attr}" if base else nodo.attr
    return ""


def test_ast_sin_contaminacion_ni_shell() -> None:
    """Solo stdlib, sin DB, sin `src.*` y sin puertas de shell."""
    arbol = ast.parse(LANZADOR.read_text(encoding="utf-8"), filename=str(LANZADOR))
    permitidos = set(sys.stdlib_module_names)

    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            for alias in nodo.names:
                raiz_mod = alias.name.split(".")[0]
                assert raiz_mod in permitidos, f"import no estándar: {alias.name}"
                assert raiz_mod not in PROHIBIDOS, f"import prohibido: {alias.name}"
        elif isinstance(nodo, ast.ImportFrom):
            assert nodo.level == 0, "el lanzador no usa imports relativos"
            raiz_mod = (nodo.module or "").split(".")[0]
            assert raiz_mod in permitidos, f"from no estándar: {nodo.module}"
            assert raiz_mod not in PROHIBIDOS, f"from prohibido: {nodo.module}"
            nombres = {alias.name for alias in nodo.names}
            if raiz_mod == "os":
                assert not nombres & {"system", "popen"}, "os.system/os.popen prohibidos"
            if raiz_mod == "subprocess":
                assert not nombres & {"getoutput", "getstatusoutput"}

    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Call):
            continue
        nombre = _cadena(nodo.func)
        assert nombre not in {
            "os.system",
            "os.popen",
            "subprocess.getoutput",
            "subprocess.getstatusoutput",
        }, f"llamada prohibida: {nombre}"

        if nombre in LLAMADAS_SHELL:
            for clave in nodo.keywords:
                if clave.arg == "shell":
                    assert (
                        isinstance(clave.value, ast.Constant) and clave.value.value is False
                    ), f"{nombre} no puede usar shell=True"
            if nodo.args:
                primero = nodo.args[0]
                elementos: list[object] = []
                if isinstance(primero, (ast.List, ast.Tuple)):
                    elementos = [elemento.value for elemento in primero.elts if isinstance(elemento, ast.Constant)]
                elif isinstance(primero, ast.Constant):
                    elementos = [primero.value]
                for elemento in elementos:
                    if isinstance(elemento, str):
                        assert not elemento.strip().lower().startswith("git"), (
                            f"{nombre} no puede invocar git"
                        )


# ── Integración opt-in ───────────────────────────────────────────────────────────────────────
@pytest.mark.skipif(
    os.getenv("QBE_LANZADOR_E2E") != "1",
    reason="integración real: exportar QBE_LANZADOR_E2E=1 y liberar :8000/:8001/:8002",
)
def test_integracion_arranque_y_apagado_ordenado(tmp_path: Path) -> None:
    """Los tres pilares llegan a READY y el apagado ordenado libera los puertos."""
    for canonico in (8000, 8001, 8002):
        if not _puerto_libre(canonico):
            pytest.skip(f"el puerto canónico {canonico} ya está ocupado en esta máquina")

    registro = tmp_path / "lanzador.log"
    with registro.open("w", encoding="utf-8") as flujo:
        proceso = subprocess.Popen(
            [sys.executable, str(LANZADOR), "--duracion", "8", "--sin-logs"],
            cwd=str(RAIZ),
            env=_entorno(),
            stdout=flujo,
            stderr=subprocess.STDOUT,
            text=True,
        )
        codigo = proceso.wait(timeout=120)

    salida = registro.read_text(encoding="utf-8", errors="replace")
    assert codigo == 0, salida
    assert "APAGADO ORDENADO COMPLETADO" in salida, salida
    for canonico in (8000, 8001, 8002):
        assert _puerto_libre(canonico), f"el puerto {canonico} quedó ocupado tras el apagado"
