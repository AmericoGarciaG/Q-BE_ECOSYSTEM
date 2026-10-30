# -*- coding: utf-8 -*-
"""
🧊 Q-BE LABORATORIO — CONGELAR CORPUS (COPIA CONSISTENTE DE SQLITE, SOLO LECTURA)

[P0 #4] Congela una copia de `qbe_historico.db` usando la API de backup de SQLite
(compatible con WAL y con lectores concurrentes). NO modifica el origen: se abre con
`mode=ro` y `PRAGMA query_only=ON`, y el origen se re-verifica por SHA-256 antes y después.

Regla fiduciaria: si el SHA-256 del origen no coincide con el de la copia, el proceso aborta
(exit 2) y el dry-run no debe continuar. Cero reparación silenciosa.

Uso:
    python -m scripts.laboratorio.congelar_corpus \
        --origen qbe_observatory/data/qbe_historico.db \
        --destino data/snapshots/qbe_historico_congelado_20261030.db
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

RAIZ_PROYECTO = Path(__file__).resolve().parents[2]
DESTINO_DEFECTO_DIR = RAIZ_PROYECTO / "data" / "snapshots"


def sha256(ruta: Path) -> str:
    """Huella SHA-256 por bloques (no carga el archivo completo en memoria)."""
    digesto = hashlib.sha256()
    with open(ruta, "rb") as manejador:
        for bloque in iter(lambda: manejador.read(1 << 20), b""):
            digesto.update(bloque)
    return digesto.hexdigest()


# La API `backup` reescribe la CABECERA del destino (contador de cambio, cookie de esquema,
# versión-válida-para) aunque copie las mismas páginas. Son 3 bytes del encabezado de la página 1
# que no portan datos: el manifiesto los certifica y los iguala al origen SÓLO si el resto del
# archivo es byte-idéntico. Así la copia congelada queda byte-idéntica sin alterar contenido.
_CAMPOS_CABECERA = tuple(range(24, 28)) + tuple(range(40, 44)) + tuple(range(92, 96))


def _igualar_cabecera_sqlite(origen: Path, destino: Path) -> Dict[str, Any]:
    """
    Iguala la cabecera del destino a la del origen si —y sólo si— el resto es byte-idéntico.

    Devuelve `{igualada, bytes_diferentes, offsets, paginas_distintas}`. Aborta (RuntimeError) si
    la diferencia toca cualquier byte fuera de los campos de cabecera declarados: una copia que
    difiere en datos jamás se "repara".
    """
    a = origen.read_bytes()
    b = destino.read_bytes()
    if len(a) != len(b):
        raise RuntimeError(
            f"🚨 La copia difiere en tamaño ({len(a)} ≠ {len(b)} bytes): imposible certificarla."
        )
    tamano_pagina = int.from_bytes(a[16:18], "big") or 4096
    offsets = [i for i in range(len(a)) if a[i] != b[i]]
    fuera = [i for i in offsets if i not in _CAMPOS_CABECERA]
    if fuera:
        raise RuntimeError(
            "🚨 La copia difiere en datos, no sólo en la cabecera SQLite: "
            f"{len(fuera)} byte(s) fuera de los campos declarados (primeros: {fuera[:8]}). "
            "Dry-run abortado."
        )
    if offsets:
        mutable = bytearray(b)
        for i in offsets:
            mutable[i] = a[i]
        destino.write_bytes(bytes(mutable))
    return {
        "igualada": bool(offsets),
        "bytes_diferentes": len(offsets),
        "offsets": offsets,
        "tamano_pagina": tamano_pagina,
        "paginas": len(a) // tamano_pagina,
    }


def _integridad_sqlite(ruta: Path) -> str:
    con = sqlite3.connect(f"file:{ruta.as_posix()}?mode=ro", uri=True)
    try:
        return str(con.execute("PRAGMA integrity_check").fetchone()[0])
    finally:
        con.close()


def congelar(origen: Path, destino: Path, sobrescribir: bool = False) -> Dict[str, Any]:
    """
    Copia `origen` a `destino` con `sqlite3.Connection.backup` y certifica la identidad SHA-256.

    Devuelve el manifiesto de congelación. Lanza `FileExistsError` si el destino ya existe y no se
    autorizó sobrescribirlo; lanza `RuntimeError` si la copia no es byte-idéntica al origen.
    """
    origen = Path(origen).resolve()
    destino = Path(destino).resolve()
    if not origen.is_file():
        raise FileNotFoundError(f"No existe el origen declarado: {origen}")
    if origen == destino:
        raise ValueError("El destino no puede ser el mismo archivo que el origen.")
    if destino.exists() and not sobrescribir:
        if sha256(destino) == sha256(origen):
            # Congelación idempotente: la copia ya existe y es byte-idéntica.
            return {
                "origen": str(origen),
                "destino": str(destino),
                "sha256_origen_antes": sha256(origen),
                "sha256_origen_despues": sha256(origen),
                "sha256_destino": sha256(destino),
                "origen_inmutable": True,
                "identicos": True,
                "reutilizada": True,
                "bytes": destino.stat().st_size,
            }
        raise FileExistsError(
            f"El destino ya existe y NO es idéntico al origen: {destino}. "
            "Use --sobrescribir para reemplazarlo."
        )
    destino.parent.mkdir(parents=True, exist_ok=True)

    origen_sha_antes = sha256(origen)

    src = sqlite3.connect(f"file:{origen.as_posix()}?mode=ro", uri=True)
    try:
        src.execute("PRAGMA query_only=ON;")
        dst = sqlite3.connect(destino.as_posix())
        try:
            with dst:
                src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()

    origen_sha_despues = sha256(origen)
    cabecera = _igualar_cabecera_sqlite(origen, destino)
    destino_sha = sha256(destino)
    integridad = _integridad_sqlite(destino)
    identicos = origen_sha_antes == origen_sha_despues == destino_sha
    manifiesto = {
        "origen": str(origen),
        "destino": str(destino),
        "sha256_origen_antes": origen_sha_antes,
        "sha256_origen_despues": origen_sha_despues,
        "sha256_destino": destino_sha,
        "origen_inmutable": origen_sha_antes == origen_sha_despues,
        "identicos": identicos,
        "reutilizada": False,
        "cabecera_sqlite": cabecera,
        "integridad_destino": integridad,
        "bytes": destino.stat().st_size,
    }
    if not identicos:
        raise RuntimeError(
            "🚨 La copia congelada NO es byte-idéntica al origen: "
            f"origen {origen_sha_despues} ≠ destino {destino_sha}. Dry-run abortado."
        )
    if integridad != "ok":
        raise RuntimeError(
            f"🚨 La copia congelada no supera `PRAGMA integrity_check`: {integridad}. "
            "Dry-run abortado."
        )
    return manifiesto


def _parsear(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Congela una copia consistente de qbe_historico.db (origen solo lectura)."
    )
    parser.add_argument(
        "--origen",
        type=Path,
        default=RAIZ_PROYECTO / "qbe_observatory" / "data" / "qbe_historico.db",
        help="Ruta de la bóveda histórica (se abre en mode=ro).",
    )
    parser.add_argument(
        "--destino",
        type=Path,
        default=None,
        help="Ruta de la copia congelada (default: data/snapshots/qbe_historico_congelado_YYYYMMDD.db).",
    )
    parser.add_argument(
        "--sobrescribir",
        action="store_true",
        help="Reemplaza el destino si ya existe (por defecto se aborta).",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    argumentos = _parsear(argv)
    destino = argumentos.destino
    if destino is None:
        destino = DESTINO_DEFECTO_DIR / f"qbe_historico_congelado_{date.today():%Y%m%d}.db"
    try:
        manifiesto = congelar(Path(argumentos.origen), Path(destino), argumentos.sobrescribir)
    except (FileExistsError, FileNotFoundError, ValueError) as error:
        print(f"\n{error}\n", file=sys.stderr)
        return 3
    except RuntimeError as error:
        print(f"\n{error}\n", file=sys.stderr)
        return 2
    print(json.dumps(manifiesto, ensure_ascii=False, indent=2))
    print("\n🧊 Copia congelada certificada: origen y destino byte-idénticos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
