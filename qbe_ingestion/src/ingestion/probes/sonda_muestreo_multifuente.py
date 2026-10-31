# -*- coding: utf-8 -*-
"""
[LN-QBE-136] Sonda de Captura CDP-MHTML y Perfil Persistente
Régimen: [DIRGEN-STRICT]

Captura artefactos web dinámicos (SPA) evadiendo bloqueos antibot mediante
navegación humana asistida (Playwright) y extracción binaria directa del
Chrome DevTools Protocol (`Page.captureSnapshot`, formato `mhtml`).

Fail-Loud: toda falla de navegación, timeout o snapshot vacío aborta el
proceso con `ProbeExtractionError`. Prohibido el fallback a `requests` o a
cualquier mock.

Uso:
    python qbe_ingestion/src/ingestion/probes/sonda_muestreo_multifuente.py \
        --url "https://www.sofascore.com/es/" --provider sofascore
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field
from playwright.async_api import async_playwright

# Constantes canónicas — [LN-QBE-136] (docs/CONSTANTS.md §9)
PROBE_TIMEOUT_MS = 60_000
PROBE_DATA_DIR = "data/sondas_exploracion"

# Raíz del monorepo: probes -> ingestion -> src -> qbe_ingestion -> Q_BE_ECOSYSTEM
MONOREPO_ROOT = Path(__file__).resolve().parents[4]
PROFILE_DIR = MONOREPO_ROOT / ".browser_profile"


class ProbeExtractionError(RuntimeError):
    """Fallo ruidoso de la sonda `[LN-QBE-136]` (sin fallbacks)."""


class ProbeTarget(BaseModel):
    """Contrato de entrada de la sonda multifuente."""

    model_config = ConfigDict(str_strip_whitespace=True)

    url: str = Field(min_length=1)
    provider_name: str = Field(min_length=1, pattern=r"^[A-Za-z0-9._-]+$")
    output_dir: str = Field(default=PROBE_DATA_DIR, min_length=1)


async def capturar_muestra_mhtml(target: ProbeTarget) -> Path:
    """
    Navega con perfil persistente, pausa para intervención humana y captura
    el snapshot MHTML vía CDP.

    Returns:
        `pathlib.Path` del archivo `.mhtml` escrito en disco.

    Raises:
        ProbeExtractionError: navegación fallida, timeout, CDP sin payload o
        intervención humana no disponible.
    """
    destino = Path(target.output_dir) / f"{target.provider_name}_sample.mhtml"
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as pw:
        try:
            contexto = await pw.chromium.launch_persistent_context(
                user_data_dir=str(PROFILE_DIR),
                headless=False,
                args=["--disable-blink-features=AutomationControlled"],
            )
        except Exception as exc:  # noqa: BLE001 — Fail-Loud deliberado
            raise ProbeExtractionError(
                f"[LN-QBE-136] No fue posible lanzar el contexto persistente "
                f"({PROFILE_DIR}): {exc}"
            ) from exc

        try:
            page = contexto.pages[0] if contexto.pages else await contexto.new_page()

            try:
                await page.goto(
                    target.url,
                    wait_until="domcontentloaded",
                    timeout=PROBE_TIMEOUT_MS,
                )
            except Exception as exc:  # noqa: BLE001 — Fail-Loud deliberado
                raise ProbeExtractionError(
                    f"[LN-QBE-136] Navegación fallida o timeout "
                    f"({PROBE_TIMEOUT_MS} ms) hacia {target.url!r}: {exc}"
                ) from exc

            print("⏸️  ESPERANDO INTERVENCIÓN HUMANA (Login/Captcha)...")
            try:
                await asyncio.to_thread(
                    input, "   Pulsa ENTER cuando la página esté lista... "
                )
            except EOFError as exc:
                raise ProbeExtractionError(
                    "[LN-QBE-136] Intervención humana no disponible: stdin cerrado."
                ) from exc

            try:
                client = await contexto.new_cdp_session(page)
                snapshot = await client.send(
                    "Page.captureSnapshot", {"format": "mhtml"}
                )
            except Exception as exc:  # noqa: BLE001 — Fail-Loud deliberado
                raise ProbeExtractionError(
                    f"[LN-QBE-136] Fallo en Page.captureSnapshot: {exc}"
                ) from exc

            if not isinstance(snapshot, dict) or not snapshot.get("data"):
                raise ProbeExtractionError(
                    "[LN-QBE-136] CDP devolvió un snapshot sin payload 'data'."
                )

            mhtml_bytes = str(snapshot["data"]).encode("utf-8")
            if not mhtml_bytes.strip():
                raise ProbeExtractionError(
                    "[LN-QBE-136] CDP devolvió un snapshot vacío (0 bytes útiles)."
                )

            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(mhtml_bytes)
            return destino
        finally:
            await contexto.close()


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sonda_muestreo_multifuente",
        description=(
            "[LN-QBE-136] Captura CDP-MHTML con perfil persistente y pausa "
            "para intervención humana (Login/Captcha)."
        ),
    )
    parser.add_argument("--url", required=True, help="URL objetivo (SPA).")
    parser.add_argument(
        "--provider",
        required=True,
        dest="provider_name",
        help="Nombre canónico del proveedor (ej. sofascore).",
    )
    parser.add_argument(
        "--output-dir",
        default=PROBE_DATA_DIR,
        help=f"Directorio de salida de muestras .mhtml (default: {PROBE_DATA_DIR}).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)
    objetivo = ProbeTarget(
        url=args.url,
        provider_name=args.provider_name,
        output_dir=args.output_dir,
    )

    print(f"🛰️  [LN-QBE-136] Sonda CDP-MHTML → {objetivo.url}")
    print(f"    Proveedor: {objetivo.provider_name} | Perfil: {PROFILE_DIR}")

    try:
        ruta = asyncio.run(capturar_muestra_mhtml(objetivo))
    except ProbeExtractionError as exc:
        print(f"\n❌ ALTO AL FUEGO — {exc}", file=sys.stderr)
        return 1

    print(f"\n✅ Muestra .mhtml consolidada: {ruta} ({ruta.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
