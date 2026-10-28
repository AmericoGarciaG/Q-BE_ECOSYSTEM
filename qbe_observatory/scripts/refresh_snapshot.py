"""Refresco programado del snapshot del Observatorio.

Uso (cron cada 30 min), desde `qbe_observatory/`:

    python -m scripts.refresh_snapshot --max-age-minutes 60

`--ensure-dir` (por omisión) crea `data/` de forma idempotente; `--no-ensure-dir`
exige que el directorio exista y falla con código 2 si no está.

Códigos de salida (contrato apto para cron, sin tracebacks):

    0  snapshot publicado y verificado
    2  BD de origen o directorio destino ausentes
    3  copia no verificada (quick_check o conteo mínimo); NO se publicó
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.config import BACKTESTING_SNAPSHOT, BASELINE_ROOT
from app.services.snapshot_refresh import refrescar_snapshot


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Refresca observatory_snapshot.db")
    parser.add_argument(
        "--source",
        type=Path,
        default=BASELINE_ROOT / "data" / "qbe_database.db",
        help="BD viva de origen (se abre en solo lectura)",
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=BACKTESTING_SNAPSHOT,
        help="Snapshot destino",
    )
    parser.add_argument("--max-age-minutes", type=int, default=60)
    parser.add_argument(
        "--ensure-dir",
        dest="ensure_dir",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Crea el directorio destino si falta (por omisión: sí)",
    )
    parser.add_argument(
        "--min-partidos",
        type=int,
        default=1,
        help="Mínimo de filas en `matches` para publicar la copia",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    if args.ensure_dir:
        args.dest.parent.mkdir(parents=True, exist_ok=True)

    try:
        resultado = refrescar_snapshot(
            args.source,
            args.dest,
            max_age_minutes=args.max_age_minutes,
            ensure_dir=args.ensure_dir,
            minimo_partidos=args.min_partidos,
        )
    except FileNotFoundError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 2
    except (RuntimeError, OSError) as exc:
        print(f"[FAIL] copia no publicada: {exc}", file=sys.stderr)
        return 3

    print(
        "[OK] snapshot={destino} bytes={bytes} sha256={sha256} "
        "matches={filas_matches} fresco={fresco} edad_s={edad_segundos:.1f}".format(
            **resultado
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
