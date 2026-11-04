# -*- coding: utf-8 -*-
"""Orquestador de mantenimiento y refresco del Sprint-46.

Secuencia:
  1. `centinela_multicasa` (momios multi-operador).
  2. `centinela_macro` (FotMob → `data/cache_macro_stats_liga_mx_2026.json`).
  3. Publicador atómico de `qbe_observatory/data/observatory_snapshot.db`.

No calcula probabilidades ni escribe fuera de los artefactos gobernados.
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

RAIZ = Path(__file__).resolve().parents[2]
PYTHON = RAIZ / ".venv" / ("Scripts" if os.name == "nt" else "bin") / (
    "python.exe" if os.name == "nt" else "python"
)
BOVEDA = RAIZ / "data" / "qbe_database.db"
SNAPSHOT = RAIZ / "qbe_observatory" / "data" / "observatory_snapshot.db"
ENTORNO = {
    **os.environ,
    "PYTHONIOENCODING": "utf-8",
    "DATABASE_URL": f"sqlite:///{BOVEDA.as_posix()}",
}


def _ejecutar(nombre: str, modulo: str, argumentos: List[str]) -> Dict[str, Any]:
    comando = [str(PYTHON), "-m", modulo, *argumentos]
    inicio = time.perf_counter()
    print(f"[orquestador] {nombre}: {' '.join(comando)}", flush=True)
    completado = subprocess.run(
        comando,
        cwd=str(RAIZ),
        env=ENTORNO,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=900,
        check=False,
    )
    duracion = time.perf_counter() - inicio
    salida = ((completado.stdout or "") + (completado.stderr or "")).strip()
    print(f"[orquestador] {nombre}: exit={completado.returncode} duracion={duracion:.1f}s", flush=True)
    if salida:
        print(salida[-4000:], flush=True)
    return {
        "nombre": nombre,
        "modulo": modulo,
        "exit_code": int(completado.returncode),
        "duracion_s": round(duracion, 2),
        "salida": salida[-4000:],
    }


def _hay_mercado_valido() -> bool:
    """True si el snapshot más reciente porta al menos una cuota 1X2 completa."""
    try:
        conexion = sqlite3.connect(
            f"file:{BOVEDA.as_posix()}?mode=ro", uri=True, timeout=5.0
        )
    except sqlite3.Error:
        return False
    try:
        filas = conexion.execute(
            "SELECT matches_json FROM fixtures_snapshots "
            "ORDER BY updated_at DESC"
        ).fetchall()
    except sqlite3.Error:
        return False
    finally:
        conexion.close()
    for fila in filas:
        if not fila or not fila[0]:
            continue
        try:
            partidos = json.loads(fila[0])
        except (TypeError, ValueError):
            continue
        for partido in partidos if isinstance(partidos, list) else []:
            operadores = partido.get("momios_operadores") or {}
            for payload in operadores.values():
                if isinstance(payload, dict) and all(
                    payload.get(clave) is not None for clave in ("L", "E", "V")
                ):
                    return True
    return False


def _publicar_snapshot() -> Dict[str, Any]:
    sys.path.insert(0, str(RAIZ / "qbe_observatory"))
    from app.services.snapshot_refresh import refrescar_snapshot

    inicio = time.perf_counter()
    resultado = refrescar_snapshot(
        BOVEDA,
        SNAPSHOT,
        max_age_minutes=30,
        minimo_partidos=1,
    )
    resultado["duracion_s"] = round(time.perf_counter() - inicio, 2)
    return resultado


def main() -> int:
    print("=" * 78)
    print("[orquestador_live] MANTENIMIENTO Y REFRESCO — SPRINT-46")
    print("=" * 78)
    print(f"Bóveda  : {BOVEDA}")
    print(f"Snapshot: {SNAPSHOT}")
    print()

    resultados: List[Dict[str, Any]] = []
    resultados.append(
        _ejecutar(
            "centinela_deportivo",
            "src.ingestion.daemons.centinela_deportivo",
            [],
        )
    )
    resultados.append(
        _ejecutar("centinela_multicasa", "src.ingestion.daemons.centinela_multicasa", [])
    )
    resultados.append(
        _ejecutar(
            "centinela_macro",
            "src.ingestion.daemons.centinela_macro",
            ["--liga-id", "230"],
        )
    )

    publicacion: Dict[str, Any] = {}
    error_publicacion = None
    mercado_ok = any(
        resultado["nombre"] == "centinela_multicasa"
        and resultado["exit_code"] == 0
        for resultado in resultados
    )
    if not mercado_ok:
        error_publicacion = "centinela_multicasa falló; snapshot válido preservado"
        print(f"[orquestador] snapshot: NO publicado ({error_publicacion})", flush=True)
    elif not _hay_mercado_valido():
        error_publicacion = "sin cuotas 1X2 válidas; snapshot válido preservado"
        print(f"[orquestador] snapshot: NO publicado ({error_publicacion})", flush=True)
    else:
        try:
            publicacion = _publicar_snapshot()
            print(
                f"[orquestador] snapshot: filas={publicacion.get('filas_matches')} "
                f"bytes={publicacion.get('bytes')} fresco={publicacion.get('fresco')}",
                flush=True,
            )
        except Exception as error:  # Fail-Loud: el orquestador reporta y falla.
            error_publicacion = f"{type(error).__name__}: {error}"
            print(f"[orquestador] snapshot: ERROR {error_publicacion}", flush=True)

    resumen = {
        "boveda": str(BOVEDA),
        "snapshot": str(SNAPSHOT),
        "daemons": [
            {clave: valor for clave, valor in resultado.items() if clave != "salida"}
            for resultado in resultados
        ],
        "snapshot_publicado": bool(publicacion) and error_publicacion is None,
        "snapshot_filas": publicacion.get("filas_matches"),
        "snapshot_fresco": publicacion.get("fresco"),
        "error_publicacion": error_publicacion,
    }
    print("\n[orquestador] RESUMEN")
    print(json.dumps(resumen, ensure_ascii=False, indent=2))

    fallos = [resultado for resultado in resultados if resultado["exit_code"] != 0]
    if fallos or error_publicacion is not None:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
