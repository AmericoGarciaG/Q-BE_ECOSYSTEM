#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Lanzador del Ecosistema Q-BE — utilidad de desarrollo `[DBBD-FUNGIBLE]`.

Levanta y apaga los tres servidores procesales como un fixture E2E atómico:

  * Mesa de Apuestas  (`qbe_business`)    -> 127.0.0.1:8000
  * Observatorio      (`qbe_observatory`) -> 127.0.0.1:OBS_PORT (default 8001)
  * Data Nexus        (`qbe_ingestion`)   -> 127.0.0.1:PORT_INGESTION (default 8002)

Fronteras:
  * No importa `src.*` ni `qbe_core`; no abre SQLite ni publica snapshots.
  * No altera el estado de Git: los logs viven en `.bt_run/` (ignorado).
  * El puerto de la Mesa es la constante legislada de `docs/ARCH.md` §6.1.

Uso:
    .\\.venv\\Scripts\\python.exe scripts\\lanzador_ecosistema.py --plan
    .\\.venv\\Scripts\\python.exe scripts\\lanzador_ecosistema.py --preflight
    .\\.venv\\Scripts\\python.exe scripts\\lanzador_ecosistema.py
    .\\.venv\\Scripts\\python.exe scripts\\lanzador_ecosistema.py --duracion 15

Códigos de salida:
    0  APAGADO ORDENADO COMPLETADO
    1  APAGADO FORZADO (algún hijo requirió taskkill)
    2  uso o entorno inválido
    3  colisión de puerto detectada antes de arrancar
    4  fallo de arranque o muerte de un hijo en caliente
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

RAIZ = Path(__file__).resolve().parents[1]
HOST = "127.0.0.1"
PUERTO_MESA = 8000  # docs/ARCH.md §6.1: constante legislada, sin variable de entorno.
PYTHON = RAIZ / ".venv" / ("Scripts" if os.name == "nt" else "bin") / (
    "python.exe" if os.name == "nt" else "python"
)
TIMEOUT_ARRANQUE = 60.0
TIMEOUT_APAGADO = 8.0
LINEAS_DIAGNOSTICO = 10
_CTRL_BREAK_EVENT = 1
_JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
_JobObjectExtendedLimitInformation = 9
_PROCESS_SET_QUOTA = 0x0100
_PROCESS_TERMINATE = 0x0001
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


# ── API de Windows (Job Object, señales de consola, snapshot de procesos) ──────────────────────
if os.name == "nt":
    from ctypes import wintypes

    _KERNEL32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _INVALID_HANDLE = ctypes.c_void_p(-1).value
    _TH32CS_SNAPPROCESS = 0x00000002

    class _JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_longlong),
            ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", ctypes.c_uint32),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", ctypes.c_uint32),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", ctypes.c_uint32),
            ("SchedulingClass", ctypes.c_uint32),
        ]

    class _IO_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("ReadOperationCount", ctypes.c_ulonglong),
            ("WriteOperationCount", ctypes.c_ulonglong),
            ("OtherOperationCount", ctypes.c_ulonglong),
            ("ReadTransferCount", ctypes.c_ulonglong),
            ("WriteTransferCount", ctypes.c_ulonglong),
            ("OtherTransferCount", ctypes.c_ulonglong),
        ]

    class _JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", _JOBOBJECT_BASIC_LIMIT_INFORMATION),
            ("IoInfo", _IO_COUNTERS),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    class _PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.c_void_p),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", wintypes.WCHAR * 260),
        ]

    _KERNEL32.CreateJobObjectW.restype = wintypes.HANDLE
    _KERNEL32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    _KERNEL32.SetInformationJobObject.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    _KERNEL32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    _KERNEL32.OpenProcess.restype = wintypes.HANDLE
    _KERNEL32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    _KERNEL32.CloseHandle.argtypes = [wintypes.HANDLE]
    _KERNEL32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    _KERNEL32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    _KERNEL32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(_PROCESSENTRY32W)]
    _KERNEL32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(_PROCESSENTRY32W)]
    _KERNEL32.GenerateConsoleCtrlEvent.argtypes = [wintypes.DWORD, wintypes.DWORD]
    _KERNEL32.GenerateConsoleCtrlEvent.restype = wintypes.BOOL


# ── Contrato ──────────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Pilar:
    nombre: str
    etiqueta: str
    puerto: int
    argv: tuple[str, ...]
    env: dict[str, str]


@dataclass
class Hijo:
    pilar: Pilar
    proceso: subprocess.Popen
    lineas: deque[str] = field(default_factory=lambda: deque(maxlen=200))
    hilo: Optional[threading.Thread] = None
    log: Optional[Path] = None


class ErrorLanzador(Exception):
    """Fallo tipificado: `codigo` es el exit code que verá el operador."""

    def __init__(self, codigo: int, mensaje: str) -> None:
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje


class _FalloCiclo(Exception):
    def __init__(self, hijo: Optional[Hijo], mensaje: str) -> None:
        super().__init__(mensaje)
        self.hijo = hijo
        self.mensaje = mensaje


# ── Salida ───────────────────────────────────────────────────────────────────────────────────
def _emitir(texto: str = "") -> None:
    try:
        print(texto, flush=True)
    except (OSError, ValueError):
        pass


def _avisar(texto: str) -> None:
    try:
        print(f"[LANZADOR] AVISO: {texto}", file=sys.stderr, flush=True)
    except (OSError, ValueError):
        pass


def _error(texto: str) -> None:
    try:
        print(f"[LANZADOR] {texto}", file=sys.stderr, flush=True)
    except (OSError, ValueError):
        pass


def _configurar_salida() -> None:
    for flujo in (sys.stdout, sys.stderr):
        reconfigurar = getattr(flujo, "reconfigure", None)
        if callable(reconfigurar):
            try:
                reconfigurar(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass


# ── Entorno y plan ───────────────────────────────────────────────────────────────────────────
def _entero_puerto(nombre: str, defecto: int) -> int:
    crudo = os.environ.get(nombre, "").strip()
    if not crudo:
        return defecto
    try:
        valor = int(crudo)
    except ValueError as exc:
        raise ErrorLanzador(2, f"{nombre}={crudo!r} no es un entero válido.") from exc
    if not 1 <= valor <= 65535:
        raise ErrorLanzador(2, f"{nombre}={valor} está fuera del rango 1..65535.")
    return valor


def _verificar_raiz() -> None:
    faltantes = [
        nombre
        for nombre in ("qbe_core", "qbe_business", "qbe_observatory", "qbe_ingestion", "qbe_storage")
        if not (RAIZ / nombre).is_dir()
    ]
    if faltantes:
        raise ErrorLanzador(
            2,
            "No se reconoce la raíz del monorepo en "
            f"{RAIZ}. Faltan: {', '.join(faltantes)}. "
            "Ejecuta el lanzador desde `scripts/` del ecosistema.",
        )
    if not PYTHON.is_file():
        raise ErrorLanzador(2, f"No existe el intérprete canónico del .venv: {PYTHON}")


def _verificar_hosts() -> None:
    for nombre in ("HOST_INGESTION", "OBS_HOST"):
        valor = os.environ.get(nombre, "").strip()
        if valor and valor not in {"127.0.0.1", "localhost", "::1"}:
            raise ErrorLanzador(
                2,
                f"{nombre}={valor!r} no es loopback. Este lanzador es de desarrollo local; "
                "para exponer en LAN usa el arranque manual de cada pilar.",
            )


def _puerto_de_url(crudo: str) -> Optional[int]:
    try:
        return urlparse(crudo).port
    except ValueError:
        return None


def _advertencias_urls(obs: int, ing: int) -> list[str]:
    avisos: list[str] = []
    esperados = {
        "QBE_BUSINESS_URL": PUERTO_MESA,
        "QBE_OBSERVATORY_URL": obs,
        "QBE_INGESTION_URL": ing,
    }
    for variable, esperado in esperados.items():
        crudo = os.environ.get(variable, "").strip()
        if not crudo:
            continue
        puerto = _puerto_de_url(crudo)
        if puerto is not None and puerto != esperado:
            avisos.append(
                f"{variable}={crudo} apunta a :{puerto}, pero este lanzador sirve :{esperado}."
            )
    return avisos


def construir_plan() -> tuple[list[Pilar], list[str]]:
    _verificar_raiz()
    obs = _entero_puerto("OBS_PORT", 8001)
    ing = _entero_puerto("PORT_INGESTION", 8002)
    if len({PUERTO_MESA, obs, ing}) != 3:
        raise ErrorLanzador(
            2,
            "Puertos duplicados: Mesa "
            f"({PUERTO_MESA}), Observatorio ({obs}) e Ingesta ({ing}) deben ser distintos.",
        )
    _verificar_hosts()

    avisos = _advertencias_urls(obs, ing)

    business_env: dict[str, str] = {}
    ingesta_env: dict[str, str] = {"PORT_INGESTION": str(ing)}
    explicita = os.environ.get("QBE_INGESTION_URL", "").strip()
    url_ingesta = explicita
    if not explicita and ing != 8002:
        url_ingesta = f"http://127.0.0.1:{ing}"
    if url_ingesta and not explicita:
        # Solo se inventa la URL del puente cuando el operador no legisló una.
        business_env["QBE_INGESTION_URL"] = url_ingesta
        ingesta_env["QBE_INGESTION_URL"] = url_ingesta

    pilares = [
        Pilar(
            "business",
            "Mesa de Apuestas",
            PUERTO_MESA,
            (
                str(PYTHON),
                "-m",
                "uvicorn",
                "src.web.app:app",
                "--host",
                HOST,
                "--port",
                str(PUERTO_MESA),
            ),
            business_env,
        ),
        Pilar(
            "observatory",
            "Observatorio",
            obs,
            (
                str(PYTHON),
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                HOST,
                "--port",
                str(obs),
            ),
            {"OBS_PORT": str(obs)},
        ),
        Pilar(
            "ingestion",
            "Data Nexus",
            ing,
            (
                str(PYTHON),
                "-m",
                "src.ingestion",
                "--host",
                HOST,
                "--port",
                str(ing),
            ),
            ingesta_env,
        ),
    ]
    return pilares, avisos


def plan_json(pilares: Sequence[Pilar], avisos: Sequence[str], preflight: Optional[bool]) -> str:
    datos: dict[str, object] = {
        "raiz": str(RAIZ),
        "interprete": str(PYTHON),
        "pilares": [
            {
                "nombre": pilar.nombre,
                "etiqueta": pilar.etiqueta,
                "puerto": pilar.puerto,
                "cwd": str(RAIZ),
                "argv": list(pilar.argv),
                "env": dict(pilar.env),
            }
            for pilar in pilares
        ],
        "advertencias": list(avisos),
    }
    if preflight is not None:
        datos["preflight"] = "ok" if preflight else "colision"
    return json.dumps(datos, ensure_ascii=False, indent=2)


def imprimir_plan(pilares: Sequence[Pilar], avisos: Sequence[str], preflight: bool = False) -> None:
    _emitir("")
    _emitir("=" * 78)
    _emitir("  Q-BE ECOSYSTEM — PLAN DE LANZAMIENTO")
    _emitir(
        "  modo       : "
        + ("preflight (sondas de puerto, sin arrancar)" if preflight else "plan (sin sockets)")
    )
    _emitir(f"  raíz       : {RAIZ}")
    _emitir(f"  intérprete : {PYTHON}")
    _emitir("-" * 78)
    for pilar in pilares:
        _emitir(f"  · {pilar.etiqueta} (:{pilar.puerto})")
        _emitir(f"      argv : {' '.join(pilar.argv)}")
        _emitir(f"      cwd  : {RAIZ}")
        if pilar.env:
            _emitir(f"      env  : {pilar.env}")
    if avisos:
        _emitir("-" * 78)
        for aviso in avisos:
            _emitir(f"  AVISO: {aviso}")
    _emitir("=" * 78)


# ── Puertos ──────────────────────────────────────────────────────────────────────────────────
def _probar_puerto(puerto: int, espera: float = 3.0) -> Optional[OSError]:
    """Bind exclusivo en loopback; reintenta para absorber TIME_WAIT de una sesión previa."""
    limite = time.monotonic() + espera
    while True:
        sonda = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                sonda.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            sonda.bind((HOST, puerto))
            sonda.listen(1)
            return None
        except OSError as exc:
            if getattr(exc, "winerror", None) == 10048 and time.monotonic() < limite:
                time.sleep(0.25)
                continue
            return exc
        finally:
            sonda.close()


def _describir_error(exc: OSError) -> str:
    if getattr(exc, "winerror", None) == 10048:
        return "ocupado por otro proceso"
    if getattr(exc, "winerror", None) == 10013:
        return "reservado o excluido por el sistema operativo (WSAEACCES)"
    return f"{type(exc).__name__}: {exc}"


def _titular_del_puerto(puerto: int) -> Optional[str]:
    try:
        salida = subprocess.run(
            ["netstat", "-ano", "-p", "tcp"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    pid: Optional[str] = None
    for linea in salida.splitlines():
        partes = linea.split()
        if len(partes) >= 5 and partes[0].upper() == "TCP" and partes[1].endswith(f":{puerto}"):
            if partes[-1].isdigit():
                pid = partes[-1]
                break
    if pid is None:
        return None
    nombre: Optional[str] = None
    try:
        listado = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        ).stdout.strip()
        if listado and "INFO:" not in listado:
            nombre = listado.split(",")[0].strip('"')
    except (OSError, subprocess.SubprocessError):
        pass
    return f"PID {pid}" + (f" ({nombre})" if nombre else "")


def verificar_puertos(pilares: Sequence[Pilar]) -> None:
    fallos: list[tuple[Pilar, OSError]] = []
    for pilar in pilares:
        error = _probar_puerto(pilar.puerto)
        if error is not None:
            fallos.append((pilar, error))
    if not fallos:
        return
    lineas = ["COLISIÓN DE PUERTOS: no se arrancará ningún proceso."]
    for pilar, error in fallos:
        lineas.append(f"  · {pilar.etiqueta} :{pilar.puerto} — {_describir_error(error)}")
        titular = _titular_del_puerto(pilar.puerto)
        if titular:
            lineas.append(f"      titular: {titular}")
    lineas.append("  Libera los puertos o detén el proceso que los ocupa; el lanzador no mata ajenos.")
    raise ErrorLanzador(3, "\n".join(lineas))


# ── Job Object ───────────────────────────────────────────────────────────────────────────────
def _hijos_directos() -> dict[int, list[int]]:
    """Mapa padre -> hijos usando Toolhelp (solo Windows)."""
    if os.name != "nt":
        return {}
    instantanea = _KERNEL32.CreateToolhelp32Snapshot(_TH32CS_SNAPPROCESS, 0)
    if not instantanea or instantanea == _INVALID_HANDLE:
        return {}
    entrada = _PROCESSENTRY32W()
    entrada.dwSize = ctypes.sizeof(entrada)
    mapa: dict[int, list[int]] = {}
    try:
        if _KERNEL32.Process32FirstW(instantanea, ctypes.byref(entrada)):
            while True:
                padre = int(entrada.th32ParentProcessID)
                hijo = int(entrada.th32ProcessID)
                mapa.setdefault(padre, []).append(hijo)
                if not _KERNEL32.Process32NextW(instantanea, ctypes.byref(entrada)):
                    break
    finally:
        _KERNEL32.CloseHandle(instantanea)
    return mapa


def _descendientes(pid: int, profundidad: int = 4) -> list[int]:
    mapa = _hijos_directos()
    vistos: list[int] = []
    frontera = [pid]
    for _ in range(profundidad):
        siguiente: list[int] = []
        for padre in frontera:
            for hijo in mapa.get(padre, []):
                if hijo not in vistos:
                    vistos.append(hijo)
                    siguiente.append(hijo)
        frontera = siguiente
        if not frontera:
            break
    return vistos


class _JobObject:
    """KILL_ON_JOB_CLOSE: si el lanzador muere, Windows apaga el árbol completo."""

    def __init__(self) -> None:
        self.handle: Optional[int] = None
        self.disponible = False
        self._asignados: set[int] = set()
        self._avisado = False
        if os.name != "nt":
            return
        try:
            handle = _KERNEL32.CreateJobObjectW(None, None)
            if not handle or handle == _INVALID_HANDLE:
                raise OSError(ctypes.get_last_error(), "CreateJobObjectW")
            informacion = _JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
            informacion.BasicLimitInformation.LimitFlags = _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            if not _KERNEL32.SetInformationJobObject(
                handle,
                _JobObjectExtendedLimitInformation,
                ctypes.byref(informacion),
                ctypes.sizeof(informacion),
            ):
                _KERNEL32.CloseHandle(handle)
                raise OSError(ctypes.get_last_error(), "SetInformationJobObject")
            self.handle = handle
            self.disponible = True
        except OSError as exc:
            _avisar(
                f"Job Object no disponible ({exc}); el apagado dependerá de taskkill /T."
            )

    def _asignar(self, pid: int) -> bool:
        if not self.disponible or self.handle is None:
            return False
        proceso = _KERNEL32.OpenProcess(
            _PROCESS_SET_QUOTA | _PROCESS_TERMINATE, False, pid
        )
        if not proceso:
            return False
        try:
            return bool(_KERNEL32.AssignProcessToJobObject(self.handle, proceso))
        finally:
            _KERNEL32.CloseHandle(proceso)

    def asignar_arbol(self, pid: int, espera: float = 1.0) -> bool:
        """Asigna el redirector del .venv y sus descendientes reales.

        El `python.exe` del .venv puede ser un lanzador que crea el intérprete
        real como hijo; la asignación del árbol cierra esa carrera.
        """
        if not self.disponible:
            return False
        limite = time.monotonic() + espera
        encontrado = False
        while True:
            candidatos = [pid, *_descendientes(pid)]
            for candidato in candidatos:
                if candidato in self._asignados:
                    encontrado = True
                    continue
                if self._asignar(candidato):
                    self._asignados.add(candidato)
                    encontrado = True
            if time.monotonic() >= limite:
                break
            time.sleep(0.1)
        if not encontrado and not self._avisado:
            self._avisado = True
            _avisar(
                "no se pudo asignar ningún proceso al Job Object; "
                "la garantía ante muerte abrupta queda degradada a taskkill /T."
            )
        return encontrado

    def cerrar(self) -> None:
        if self.handle is not None:
            _KERNEL32.CloseHandle(self.handle)
            self.handle = None
            self.disponible = False


# ── Señales ──────────────────────────────────────────────────────────────────────────────────
def _instalar_senales() -> None:
    def _corte(_signum: int, _frame: object) -> None:
        raise KeyboardInterrupt

    for nombre in ("SIGINT", "SIGTERM", "SIGBREAK"):
        senal = getattr(signal, nombre, None)
        if senal is None:
            continue
        try:
            signal.signal(senal, _corte)
        except (OSError, ValueError):
            pass


def _enviar_ctrl_break(pid: int) -> bool:
    if os.name != "nt":
        return False
    try:
        return bool(_KERNEL32.GenerateConsoleCtrlEvent(_CTRL_BREAK_EVENT, pid))
    except (AttributeError, OSError):
        return False


def _matar_arbol(proceso: subprocess.Popen) -> None:
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/T", "/F", "/PID", str(proceso.pid)],
                capture_output=True,
                timeout=15,
            )
            return
        except (OSError, subprocess.SubprocessError):
            pass
    try:
        proceso.kill()
    except OSError:
        pass


# ── Salud ────────────────────────────────────────────────────────────────────────────────────
def _leer_salud(puerto: int, timeout: float = 1.0) -> dict:
    peticion = Request(
        f"http://{HOST}:{puerto}/health",
        headers={"Accept": "application/json", "Connection": "close", "User-Agent": "qbe-lanzador/1.0"},
    )
    with urlopen(peticion, timeout=timeout) as respuesta:  # noqa: S310 — loopback gobernado
        return json.loads(respuesta.read().decode("utf-8", "replace"))


def _cumple_contrato(pilar: Pilar, datos: dict) -> bool:
    if pilar.nombre == "business":
        return str(datos.get("module", "")) == "business"
    if pilar.nombre == "observatory":
        return str(datos.get("db", "")) == "READ_ONLY"
    if pilar.nombre == "ingestion":
        try:
            return (
                str(datos.get("service", "")) == "qbe_ingestion"
                and int(datos.get("port", -1)) == pilar.puerto
            )
        except (TypeError, ValueError):
            return False
    return False


# ── Orquestador ──────────────────────────────────────────────────────────────────────────────
class _Orquestador:
    def __init__(self, pilares: Sequence[Pilar], args: argparse.Namespace) -> None:
        self.pilares = list(pilares)
        self.args = args
        self.job = _JobObject()
        self.hijos: list[Hijo] = []
        self.dir_logs: Optional[Path] = None

    # -- ciclo de vida ---------------------------------------------------------------------
    def arrancar(self) -> None:
        if not self.args.sin_logs:
            sello = time.strftime("%Y%m%dT%H%M%S")
            self.dir_logs = RAIZ / self.args.log_dir / sello
            self.dir_logs.mkdir(parents=True, exist_ok=True)
            _emitir(f"[LANZADOR] logs: {self.dir_logs}")

        for pilar in self.pilares:
            entorno = os.environ.copy()
            entorno.update(pilar.env)
            entorno["PYTHONUNBUFFERED"] = "1"
            entorno["PYTHONUTF8"] = "1"
            entorno["PYTHONIOENCODING"] = "utf-8"
            banderas = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
            try:
                proceso = subprocess.Popen(
                    list(pilar.argv),
                    cwd=str(RAIZ),
                    env=entorno,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    creationflags=banderas,
                )
            except OSError as exc:
                raise _FalloCiclo(None, f"no se pudo lanzar {pilar.etiqueta}: {exc}") from exc

            log = (self.dir_logs / f"{pilar.nombre}.log") if self.dir_logs else None
            hijo = Hijo(pilar=pilar, proceso=proceso, log=log)
            hilo = threading.Thread(
                target=self._bombear,
                args=(hijo,),
                name=f"log-{pilar.nombre}",
                daemon=True,
            )
            hijo.hilo = hilo
            hilo.start()
            self.hijos.append(hijo)
            _emitir(
                f"[LANZADOR] ARRANCANDO {pilar.etiqueta} :{pilar.puerto} "
                f"(pid {proceso.pid})"
            )

        # Los tres procesos ya están vivos; ahora se ancla el árbol completo al Job
        # Object. El `python.exe` del .venv puede ser un redirector, así que se
        # asignan también sus descendientes reales.
        for hijo in self.hijos:
            self.job.asignar_arbol(hijo.proceso.pid, espera=0.6)

    def _bombear(self, hijo: Hijo) -> None:
        archivo = None
        try:
            if hijo.log is not None:
                archivo = hijo.log.open("a", encoding="utf-8", errors="replace")
            if hijo.proceso.stdout is None:
                return
            for linea in hijo.proceso.stdout:
                texto = linea.rstrip("\r\n")
                hijo.lineas.append(texto)
                _emitir(f"[{hijo.pilar.nombre}] {texto}")
                if archivo is not None:
                    archivo.write(texto + "\n")
                    archivo.flush()
        except (OSError, ValueError):
            pass
        finally:
            if archivo is not None:
                try:
                    archivo.close()
                except OSError:
                    pass

    def esperar_salud(self) -> None:
        pendientes = list(self.hijos)
        limite = time.monotonic() + self.args.timeout_arranque
        while pendientes and time.monotonic() < limite:
            for hijo in list(pendientes):
                if hijo.proceso.poll() is not None:
                    raise _FalloCiclo(
                        hijo,
                        f"{hijo.pilar.etiqueta} terminó antes de READY "
                        f"(código {hijo.proceso.returncode})",
                    )
                try:
                    datos = _leer_salud(hijo.pilar.puerto)
                except (HTTPError, URLError, OSError, ValueError):
                    continue
                if _cumple_contrato(hijo.pilar, datos):
                    pendientes.remove(hijo)
                    _emitir(
                        f"[LANZADOR] READY {hijo.pilar.etiqueta} :{hijo.pilar.puerto} "
                        f"({datos})"
                    )
            if pendientes:
                time.sleep(0.25)
        if pendientes:
            raise _FalloCiclo(
                pendientes[0],
                f"{pendientes[0].pilar.etiqueta} no alcanzó READY en "
                f"{self.args.timeout_arranque:.0f}s",
            )
        for hijo in self.hijos:
            self.job.asignar_arbol(hijo.proceso.pid, espera=0.2)

    def resumen(self) -> None:
        _emitir("")
        _emitir("=" * 78)
        _emitir("  Q-BE ECOSYSTEM — TRES PILARES EN LÍNEA")
        for hijo in self.hijos:
            _emitir(
                f"  · {hijo.pilar.etiqueta:<20} http://{HOST}:{hijo.pilar.puerto:<5} "
                f"pid={hijo.proceso.pid}"
            )
        _emitir(
            r"  Verificación E2E: .\.venv\Scripts\python.exe scripts\verificar_ecosistema_e2e.py"
        )
        _emitir("  Ctrl+C para apagar de forma ordenada.")
        _emitir("=" * 78)

    def vigilar(self) -> None:
        limite = (time.monotonic() + self.args.duracion) if self.args.duracion > 0 else None
        while True:
            for hijo in self.hijos:
                codigo = hijo.proceso.poll()
                if codigo is not None:
                    raise _FalloCiclo(
                        hijo,
                        f"{hijo.pilar.etiqueta} murió en caliente con código {codigo}",
                    )
            if limite is not None and time.monotonic() >= limite:
                _emitir(
                    f"[LANZADOR] Duración de {self.args.duracion:.0f}s cumplida; apagando..."
                )
                return
            time.sleep(0.5)

    def apagar(self) -> list[str]:
        forzados: list[str] = []
        try:
            for hijo in reversed(self.hijos):
                proceso = hijo.proceso
                if proceso.poll() is not None:
                    continue
                _emitir(f"[LANZADOR] Cerrando {hijo.pilar.etiqueta} (pid {proceso.pid})...")
                if _enviar_ctrl_break(proceso.pid):
                    try:
                        proceso.wait(timeout=self.args.timeout_apagado)
                        continue
                    except subprocess.TimeoutExpired:
                        pass
                forzados.append(hijo.pilar.nombre)
                _emitir(f"[LANZADOR] Forzando {hijo.pilar.etiqueta} con taskkill /T...")
                _matar_arbol(proceso)
                try:
                    proceso.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    try:
                        proceso.kill()
                    except OSError:
                        pass
                    try:
                        proceso.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        pass
        finally:
            # Pase lo que pase, cerrar el Job Object: garantía dura de no-huérfanos.
            self.job.cerrar()
            time.sleep(0.2)
            for hijo in self.hijos:
                if hijo.proceso.poll() is None:
                    if hijo.pilar.nombre not in forzados:
                        forzados.append(hijo.pilar.nombre)
                    try:
                        hijo.proceso.kill()
                    except OSError:
                        pass
                    try:
                        hijo.proceso.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        pass
                if hijo.hilo is not None:
                    hijo.hilo.join(timeout=5)
        return forzados


# ── CLI ──────────────────────────────────────────────────────────────────────────────────────
def _parsear(argv: Optional[Sequence[str]]) -> argparse.Namespace:
    analizador = argparse.ArgumentParser(
        prog="python scripts/lanzador_ecosistema.py",
        description="Lanzador atómico de los tres pilares del ecosistema Q-BE.",
    )
    analizador.add_argument(
        "--plan",
        action="store_true",
        help="Imprime argv, cwd y entorno efectivo sin abrir sockets.",
    )
    analizador.add_argument(
        "--preflight",
        action="store_true",
        help="Ejecuta el plan y las sondas de puerto sin arrancar procesos.",
    )
    analizador.add_argument(
        "--json",
        action="store_true",
        help="Salida JSON para --plan/--preflight.",
    )
    analizador.add_argument(
        "--timeout-arranque",
        type=float,
        default=TIMEOUT_ARRANQUE,
        help=f"Segundos para alcanzar READY (default {TIMEOUT_ARRANQUE:.0f}).",
    )
    analizador.add_argument(
        "--timeout-apagado",
        type=float,
        default=TIMEOUT_APAGADO,
        help=f"Segundos de gracia por hijo antes de taskkill (default {TIMEOUT_APAGADO:.0f}).",
    )
    analizador.add_argument(
        "--duracion",
        type=float,
        default=0.0,
        help="Apaga ordenadamente tras N segundos de operación (smoke test).",
    )
    analizador.add_argument(
        "--log-dir",
        default=".bt_run/lanzador",
        help="Directorio de logs relativo a la raíz (default .bt_run/lanzador).",
    )
    analizador.add_argument(
        "--sin-logs",
        action="store_true",
        help="No escribe archivos de log; solo consola.",
    )
    args = analizador.parse_args(argv)
    if args.json and not (args.plan or args.preflight):
        analizador.error("--json solo es válido junto a --plan o --preflight")
    if args.timeout_arranque <= 0 or args.timeout_apagado <= 0:
        analizador.error("los timeouts deben ser positivos")
    if args.duracion < 0:
        analizador.error("--duracion no puede ser negativa")
    return args


def _diagnostico(hijo: Optional[Hijo]) -> None:
    if hijo is None:
        return
    _error(f"Últimas {LINEAS_DIAGNOSTICO} líneas de {hijo.pilar.etiqueta}:")
    lineas = list(hijo.lineas)[-LINEAS_DIAGNOSTICO:]
    if not lineas:
        _error("  (el hijo no emitió salida antes del fallo)")
    for linea in lineas:
        try:
            print(f"  | {linea}", file=sys.stderr, flush=True)
        except (OSError, ValueError):
            pass
    _error(f"Comando: {' '.join(hijo.pilar.argv)}")
    _error(f"cwd: {RAIZ}")
    if hijo.log is not None:
        _error(f"log completo: {hijo.log}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    _configurar_salida()
    args = _parsear(argv)

    try:
        pilares, avisos = construir_plan()
    except ErrorLanzador as exc:
        _error(exc.mensaje)
        return exc.codigo

    for aviso in avisos:
        _avisar(aviso)

    if args.plan or args.preflight:
        preflight_ok: Optional[bool] = None
        if args.preflight:
            try:
                verificar_puertos(pilares)
                preflight_ok = True
            except ErrorLanzador as exc:
                _error(exc.mensaje)
                return exc.codigo
        if args.json:
            _emitir(plan_json(pilares, avisos, preflight_ok))
        else:
            imprimir_plan(pilares, avisos, args.preflight)
            if preflight_ok:
                _emitir("[LANZADOR] PREFLIGHT OK: los tres puertos están libres.")
        return 0

    try:
        verificar_puertos(pilares)
    except ErrorLanzador as exc:
        _error(exc.mensaje)
        return exc.codigo

    _instalar_senales()
    _emitir(f"[LANZADOR] pid={os.getpid()} · raíz={RAIZ}")
    orquestador = _Orquestador(pilares, args)
    fallo: Optional[_FalloCiclo] = None
    forzados: list[str] = []
    try:
        orquestador.arrancar()
        orquestador.esperar_salud()
        orquestador.resumen()
        orquestador.vigilar()
    except KeyboardInterrupt:
        _emitir("")
        _emitir("[LANZADOR] Ctrl+C recibido; apagando el ecosistema...")
    except _FalloCiclo as exc:
        fallo = exc
    except Exception as exc:  # noqa: BLE001 — ninguna excepción puede dejar huérfanos
        fallo = _FalloCiclo(None, f"excepción inesperada: {type(exc).__name__}: {exc}")
    finally:
        try:
            forzados = orquestador.apagar()
        except Exception as exc:  # noqa: BLE001 — el cierre nunca puede quedar a medias
            _error(f"fallo durante el apagado: {type(exc).__name__}: {exc}")
            forzados = [hijo.pilar.nombre for hijo in orquestador.hijos]

    if fallo is not None:
        _diagnostico(fallo.hijo)
        _error(f"FALLO DE CICLO DE VIDA: {fallo.mensaje}")
        _error("Los procesos que seguían vivos fueron apagados.")
        return 4

    if forzados:
        _emitir(f"[LANZADOR] APAGADO FORZADO (Código 1): {', '.join(forzados)}")
        return 1

    _emitir("[LANZADOR] APAGADO ORDENADO COMPLETADO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
