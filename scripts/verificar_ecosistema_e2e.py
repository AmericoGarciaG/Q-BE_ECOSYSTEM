#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Verificador E2E multi-puerto del ecosistema Q-BE (Sub-fase 4.1).

Certifica, en una sola pasada y sin importar el ecosistema:

  1. BUSINESS   (:8000) — la Mesa de Apuestas responde ``/health``.
  2. OBSERVATORY(:8001) — el CQRS de lectura responde ``/health`` en modo READ_ONLY.
  3. INGESTION  (:8002) — el Data Nexus responde ``/health``.
  4. LOOPBACK   (:8000 → :8002) — ``GET /api/admin/status/drift`` devuelve el contrato
     completo de CINCO LUCES emitido por ``qbe_ingestion`` (el puente inverso del proxy).
  5. CQRS       — el snapshot atómico ``data/snapshots/qbe_database_snapshot.db`` existe,
     es íntegro (``PRAGMA integrity_check``) y no tiene publicación a medias. [D-2] Si
     falta, se materializa con ``sqlite3.Connection.backup`` + ``os.replace`` (copia
     online, consciente de WAL); ``--solo-verificar`` desactiva toda escritura.

Sólo biblioteca estándar: se ejecuta con cualquier intérprete 3.12, sin instalar el
ecosistema.

Uso:
    python scripts/verificar_ecosistema_e2e.py
    python scripts/verificar_ecosistema_e2e.py --solo-verificar --verbose
    python scripts/verificar_ecosistema_e2e.py --json

Códigos de salida:
    0  los cinco pilares son conformes.
    1  al menos un pilar está en rojo.
    2  error de uso (argumentos inválidos).
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ECOSYSTEM_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_DESTINO = ECOSYSTEM_ROOT / "data" / "snapshots" / "qbe_database_snapshot.db"
BOVEDA_LEGADA = ECOSYSTEM_ROOT.parent / "Q_BE_CD_WEB" / "data" / "qbe_database.db"

LUCES_DRIFT = (
    "status_mercado",
    "status_deportivo",
    "status_progol",
    "status_integridad",
    "status_homologacion",
)

ESTADO_OK = "[ OK ]"
ESTADO_FALLO = "[FAIL]"
ESTADO_OMITIDO = "[SKIP]"


# ── Utilidades HTTP ───────────────────────────────────────────────────────────────────────────
def _get_json(url: str, timeout: float) -> Tuple[Optional[int], Optional[Any], str, float]:
    """GET JSON tolerante a fallos. Devuelve (status, cuerpo, error, latencia_ms)."""
    peticion = Request(url, headers={"Accept": "application/json", "User-Agent": "qbe-e2e-verifier/4.1"})
    inicio = time.perf_counter()
    try:
        with urlopen(peticion, timeout=timeout) as respuesta:  # noqa: S310 — loopback gobernado
            crudo = respuesta.read().decode("utf-8", "replace")
            latencia = (time.perf_counter() - inicio) * 1000.0
            try:
                return int(respuesta.status), json.loads(crudo), "", latencia
            except json.JSONDecodeError as exc:
                return int(respuesta.status), None, f"cuerpo no-JSON: {exc}", latencia
    except HTTPError as exc:
        crudo = exc.read().decode("utf-8", "replace")[:200]
        return int(exc.code), None, f"HTTP {exc.code}: {crudo}", (time.perf_counter() - inicio) * 1000.0
    except (URLError, TimeoutError, OSError) as exc:
        return None, None, f"sin conexión: {_motivo(exc)}", (time.perf_counter() - inicio) * 1000.0


def _motivo(exc: BaseException) -> str:
    razon = getattr(exc, "reason", None)
    return f"{type(exc).__name__}: {razon or exc}"


# ── Pilares 1-3: salud de los tres microservicios ─────────────────────────────────────────────
def _probar_salud(
    pilar: str,
    puerto: str,
    base: str,
    timeout: float,
    campo: str,
    esperado: str,
) -> Dict[str, Any]:
    status, cuerpo, error, latencia = _get_json(f"{base.rstrip('/')}/health", timeout)
    if status != 200 or not isinstance(cuerpo, dict):
        return _resultado(pilar, puerto, False, latencia, error or f"HTTP {status}")
    obtenido = str(cuerpo.get(campo, ""))
    conforme = obtenido == esperado
    evidencia = f"{campo}={obtenido or '∅'}"
    if not conforme:
        evidencia += f" (esperado {esperado})"
    return _resultado(pilar, puerto, conforme, latencia, evidencia)


# ── Pilar 4: loopback del semáforo de deriva (:8000 → :8002) ─────────────────────────────────
def _validar_deriva(base_business: str, timeout: float) -> Dict[str, Any]:
    url = f"{base_business.rstrip('/')}/api/admin/status/drift"
    status, cuerpo, error, latencia = _get_json(url, timeout)
    if status != 200 or not isinstance(cuerpo, dict):
        return _resultado(
            "LOOPBACK DERIVA", ":8000→:8002", False, latencia,
            error or f"HTTP {status} · el puente :8000→:8002 no entregó JSON",
        )

    faltantes = [luz for luz in LUCES_DRIFT if not isinstance(cuerpo.get(luz), dict)]
    if faltantes:
        return _resultado(
            "LOOPBACK DERIVA", ":8000→:8002", False, latencia,
            f"contrato incompleto: faltan {', '.join(faltantes)}",
        )
    if not isinstance(cuerpo.get("accion_recomendada"), dict):
        return _resultado(
            "LOOPBACK DERIVA", ":8000→:8002", False, latencia,
            "contrato incompleto: falta accion_recomendada",
        )

    fuente = str(cuerpo.get("fuente", ""))
    if fuente != "qbe_ingestion":
        return _resultado(
            "LOOPBACK DERIVA", ":8000→:8002", False, latencia,
            f"fuente={fuente or '∅'} (esperado qbe_ingestion)",
        )

    verdes = sum(
        1
        for luz in LUCES_DRIFT
        if str(cuerpo[luz].get("nivel", "")).upper() in {"VERDE", "CONFORME"}
    )
    return _resultado(
        "LOOPBACK DERIVA", ":8000→:8002", True, latencia,
        f"5/5 luces · contrato completo · veredicto {verdes}/5",
    )


# ── Pilar 5: snapshot atómico CQRS ───────────────────────────────────────────────────────────
def _boveda_origen() -> Optional[Path]:
    """Bóveda viva gobernada: `DATABASE_URL` explícita o el fallback legado de Ingesta."""
    crudo = os.getenv("DATABASE_URL", "").strip()
    if crudo.startswith("sqlite:///"):
        ruta = Path(crudo[len("sqlite:///"):])
        if not ruta.is_absolute():
            ruta = Path.cwd() / ruta
        return ruta.resolve()
    return BOVEDA_LEGADA.resolve()


def _materializar_snapshot(origen: Path, destino: Path) -> None:
    """Copia online y publicación atómica — jamás un `copy` de archivo en caliente."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporal = destino.with_name(destino.name + ".tmp")
    con_origen = sqlite3.connect(f"file:{origen.as_posix()}?mode=ro", uri=True)
    con_destino = sqlite3.connect(temporal.as_posix())
    try:
        con_origen.backup(con_destino)
    finally:
        con_destino.close()
        con_origen.close()
    os.replace(temporal, destino)


def _inspeccionar_snapshot(ruta: Path) -> Tuple[bool, str]:
    """Existencia, tamaño, integridad SQLite y contenido mínimo."""
    if not ruta.is_file():
        return False, f"no existe: {ruta}"
    tamano = ruta.stat().st_size
    if tamano <= 0:
        return False, "archivo de 0 bytes"
    try:
        conexion = sqlite3.connect(f"file:{ruta.as_posix()}?mode=ro", uri=True)
        try:
            integridad = conexion.execute("PRAGMA integrity_check").fetchone()
            tablas = conexion.execute(
                "SELECT count(*) FROM sqlite_master WHERE type='table'"
            ).fetchone()[0]
        finally:
            conexion.close()
    except sqlite3.Error as exc:
        return False, f"SQLite ilegible: {exc}"
    if not integridad or str(integridad[0]).lower() != "ok":
        return False, f"integrity_check={integridad[0] if integridad else '∅'}"
    if not tablas:
        return False, "snapshot sin tablas (bóveda vacía)"
    edad_min = max(0.0, (time.time() - ruta.stat().st_mtime) / 60.0)
    return True, f"integro · {tablas} tablas · {tamano / 1024:.0f} KiB · {edad_min:.1f} min"


def _validar_snapshot(solo_verificar: bool, verbose: bool) -> Dict[str, Any]:
    inicio = time.perf_counter()
    destino = SNAPSHOT_DESTINO
    temporal = destino.with_name(destino.name + ".tmp")
    origen = _boveda_origen()
    notas: List[str] = []

    if temporal.is_file():
        notas.append("publicación a medias (.tmp presente)")

    if not destino.is_file() and not solo_verificar:
        if origen is None or not origen.is_file():
            return _resultado(
                "SNAPSHOT CQRS", "data/", False,
                (time.perf_counter() - inicio) * 1000.0,
                f"sin bóveda origen para materializar: {origen}",
            )
        try:
            _materializar_snapshot(origen, destino)
            notas.append(f"materializado desde {origen.name}")
        except (sqlite3.Error, OSError) as exc:
            return _resultado(
                "SNAPSHOT CQRS", "data/", False,
                (time.perf_counter() - inicio) * 1000.0,
                f"falló la publicación atómica: {exc}",
            )
    elif not destino.is_file():
        return _resultado(
            "SNAPSHOT CQRS", "data/", False,
            (time.perf_counter() - inicio) * 1000.0,
            "ausente y --solo-verificar impide materializarlo",
        )

    conforme, detalle = _inspeccionar_snapshot(destino)
    if not conforme:
        return _resultado(
            "SNAPSHOT CQRS", "data/", False,
            (time.perf_counter() - inicio) * 1000.0, detalle,
        )

    # Un `.tmp` superviviente tras la inspección delata una publicación interrumpida:
    # el snapshot se lee, pero el contrato de atomicidad no está sano.
    publicacion_a_medias = temporal.is_file()
    if publicacion_a_medias:
        notas.append("publicación a medias (.tmp presente)")
    evidencia = detalle
    if notas:
        evidencia += " · " + " · ".join(notas)
    resultado = _resultado(
        "SNAPSHOT CQRS", "data/", not publicacion_a_medias,
        (time.perf_counter() - inicio) * 1000.0, evidencia,
    )
    resultado["detalle_snapshot"] = {
        "destino": str(destino),
        "origen": str(origen) if origen else None,
        "tamano_bytes": destino.stat().st_size,
    }
    if verbose:
        resultado["detalle_snapshot"]["inspeccion"] = detalle
    return resultado


# ── Presentación ─────────────────────────────────────────────────────────────────────────────
def _resultado(
    pilar: str, puerto: str, conforme: bool, latencia_ms: float, evidencia: str
) -> Dict[str, Any]:
    return {
        "pilar": pilar,
        "puerto": puerto,
        "conforme": bool(conforme),
        "estado": ESTADO_OK if conforme else ESTADO_FALLO,
        "latencia_ms": round(latencia_ms, 1),
        "evidencia": evidencia,
    }


ANCHO_PILAR = 22
ANCHO_PUERTO = 13
ANCHO_ESTADO = 6
ANCHO_LAT = 7
ANCHO_EVIDENCIA = 46


def _recortar(texto: str, ancho: int) -> str:
    return texto if len(texto) <= ancho else texto[: ancho - 1] + "…"


def _linea(datos: List[str]) -> str:
    return "| " + " | ".join(datos) + " |"


def _separador(relleno: str = "-") -> str:
    return (
        "+"
        + relleno * (ANCHO_PILAR + 2)
        + "+"
        + relleno * (ANCHO_PUERTO + 2)
        + "+"
        + relleno * (ANCHO_ESTADO + 2)
        + "+"
        + relleno * (ANCHO_LAT + 2)
        + "+"
        + relleno * (ANCHO_EVIDENCIA + 2)
        + "+"
    )


def _tablero(resultados: List[Dict[str, Any]]) -> str:
    def _celda(texto: str, ancho: int) -> str:
        return _recortar(texto, ancho).ljust(ancho)

    lineas = [
        _separador("="),
        _linea(
            [
                _celda("Q-BE ECOSYSTEM", ANCHO_PILAR),
                _celda("PUERTO", ANCHO_PUERTO),
                _celda("ESTADO", ANCHO_ESTADO),
                _celda("LAT ms", ANCHO_LAT),
                _celda("CERTIFICACIÓN E2E MULTI-PUERTO · SUBFASE 4.1", ANCHO_EVIDENCIA),
            ]
        ),
        _separador("="),
        _linea(
            [
                _celda("PILAR", ANCHO_PILAR),
                _celda("", ANCHO_PUERTO),
                _celda("", ANCHO_ESTADO),
                _celda("", ANCHO_LAT),
                _celda("SPRINT-36 · 3 SERVICIOS + LOOPBACK + CQRS", ANCHO_EVIDENCIA),
            ]
        ),
        _separador("-"),
    ]
    for r in resultados:
        lineas.append(
            _linea(
                [
                    _celda(r["pilar"], ANCHO_PILAR),
                    _celda(r["puerto"], ANCHO_PUERTO),
                    _celda(r["estado"], ANCHO_ESTADO),
                    _celda(f"{r['latencia_ms']:.1f}", ANCHO_LAT),
                    _celda(r["evidencia"], ANCHO_EVIDENCIA),
                ]
            )
        )
    lineas.append(_separador("="))
    return "\n".join(lineas)


# ── Orquestación ─────────────────────────────────────────────────────────────────────────────
def _bases() -> Dict[str, str]:
    return {
        "business": os.getenv("QBE_BUSINESS_URL", "http://127.0.0.1:8000"),
        "observatory": os.getenv("QBE_OBSERVATORY_URL", "http://127.0.0.1:8001"),
        "ingestion": os.getenv("QBE_INGESTION_URL", "http://127.0.0.1:8002"),
    }


def main(argv: Optional[List[str]] = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            pass

    parser = argparse.ArgumentParser(
        description="Verificador E2E multi-puerto del ecosistema Q-BE (Sub-fase 4.1).",
    )
    parser.add_argument("--timeout", type=float, default=3.0, help="Timeout HTTP por sonda (s).")
    parser.add_argument(
        "--solo-verificar",
        action="store_true",
        help="No materializa el snapshot si falta (auditoría sin escrituras).",
    )
    parser.add_argument("--verbose", action="store_true", help="Detalle adicional en la evidencia.")
    parser.add_argument("--json", action="store_true", help="Emite el reporte como JSON.")
    args = parser.parse_args(argv)

    bases = _bases()
    resultados = [
        _probar_salud("BUSINESS (Mesa OLTP)", ":8000", bases["business"], args.timeout, "module", "business"),
        _probar_salud("OBSERVATORY (CQRS)", ":8001", bases["observatory"], args.timeout, "db", "READ_ONLY"),
        _probar_salud("INGESTION (Data Nexus)", ":8002", bases["ingestion"], args.timeout, "service", "qbe_ingestion"),
        _validar_deriva(bases["business"], args.timeout),
        _validar_snapshot(args.solo_verificar, args.verbose),
    ]

    conformes = sum(1 for r in resultados if r["conforme"])
    total = len(resultados)
    fallos = [r["pilar"] for r in resultados if not r["conforme"]]
    codigo = 0 if conformes == total else 1

    if args.json:
        print(
            json.dumps(
                {
                    "conformes": conformes,
                    "total": total,
                    "exit_code": codigo,
                    "pilares": resultados,
                    "snapshot": SNAPSHOT_DESTINO.as_posix(),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return codigo

    print(_tablero(resultados))
    print(f"  snapshot ............ {SNAPSHOT_DESTINO}")
    print(f"  bóveda origen ....... {_boveda_origen()}")
    print(_separador("-"))
    if codigo == 0:
        print(f"  VEREDICTO: {conformes}/{total} PILARES CONFORMES · exit 0")
    else:
        print(f"  VEREDICTO: {conformes}/{total} PILARES CONFORMES · exit 1")
        print(f"  FALLOS: {', '.join(fallos)}")
        for r in resultados:
            if not r["conforme"]:
                print(f"    · {r['pilar']}: {r['evidencia']}")
    return codigo


if __name__ == "__main__":
    raise SystemExit(main())
