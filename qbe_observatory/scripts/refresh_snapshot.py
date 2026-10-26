"""Refresco programado del snapshot del Observatorio.

Uso (cron cada 30 min):
    python -m scripts.refresh_snapshot --max-age-minutes 60
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.config import BACKTESTING_SNAPSHOT, BASELINE_ROOT
from app.services.snapshot_refresh import refrescar_snapshot


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Refresca observatory_snapshot.db")
    parser.add_argument(
        "--source",
        type=Path,
        default=BASELINE_ROOT / "data" / "qbe_database.db",
        help="BD viva de origen (solo lectura)",
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=BACKTESTING_SNAPSHOT,
        help="Snapshot destino",
    )
    parser.add_argument("--max-age-minutes", type=int, default=60)
    args = parser.parse_args(argv)

    resultado = refrescar_snapshot(
        args.source,
        args.dest,
        max_age_minutes=args.max_age_minutes,
    )
    print(resultado)
    return 0


if __name__ == "__main__":
    sys.exit(main())
