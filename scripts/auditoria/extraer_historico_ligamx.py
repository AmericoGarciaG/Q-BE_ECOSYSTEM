# -*- coding: utf-8 -*-
"""[LN-QBE-143] Orquestador de Extracción Masiva de Eventos (ligamx.net → Bóveda OLAP).

Régimen: ``[DIRGEN-STRICT]``. Cero datos sintéticos, cero mocks en producción,
Fail-Loud por partido con resumen final de fallos.

Flujo por jornada:
    1. Sonda ``[LN-QBE-142]`` → partidos y URLs «Minuto a Minuto».
    2. Playwright (UA stealth, una sola sesión por lote) → HTML en memoria.
    3. Parser ``[LN-QBE-141]`` → sobre (equipos, marcador, eventos).
    4. Diccionario de alias ``[LN-QBE-145]`` → nombres canónicos de la bóveda.
    5. Join Determinista (``[ARCH-1.5.1]`` §15.3) → ``match_id`` de la bóveda.
    6. Almacén ``[LN-QBE-144]`` → ``INSERT OR IGNORE`` idempotente.

Uso::

    python scripts/auditoria/extraer_historico_ligamx.py \\
        --temporada 2015-2016 --torneo Clausura --jornada_inicio 16 --jornada_fin 16
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

RAIZ_PROYECTO = Path(__file__).resolve().parents[2]
if str(RAIZ_PROYECTO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROYECTO))

from scripts.auditoria.descubrir_partidos_ligamx import (  # noqa: E402
    ARGUMENTOS_NAVEGADOR,
    USER_AGENT,
    DescubrimientoError,
    descubrir,
)
from qbe_ingestion.src.ingestion.loaders.cargar_eventos_historicos import (  # noqa: E402
    DB_DEFECTO,
    AlmacenEventosError,
    cargar_eventos,
    resolver_match_id,
)
from qbe_ingestion.src.ingestion.parsers.parsear_minuto_a_minuto import (  # noqa: E402
    MinutoAJugadaError,
    parsear_partido_desde_html,
)
from qbe_core.src.core.normalization.ligamx_alias import (  # noqa: E402
    resolver_alias_ligamx,
)

__all__ = [
    "DescargaError",
    "DescargadorPlaywright",
    "ejecutar",
    "main",
]

# ── Política anti-bloqueo ───────────────────────────────────────────────────────────────────
# Un partido no puede consumir más de ~60 s (30 de navegación + 30 de render). Sin estos
# topes, un sitio que deja de responder cuelga el lote horas (Ficha de Varianza Sprint 42).
TIMEOUT_MS = 30_000
# Pausa entre partidos: el sitio aplica WAF y responde con la cartelera degradada bajo ráfaga.
PAUSA_DEFECTO_S = 2.0
# Estado reanudable del lote (vive bajo `qbe_ingestion/data/`, ignorado por git).
CHECKPOINT_DEFECTO = (
    RAIZ_PROYECTO / "qbe_ingestion" / "data" / "reportes" / "checkpoint.json"
)


class DescargaError(RuntimeError):
    """[LN-QBE-143] No se pudo obtener el HTML del visor «Minuto a Minuto»."""


# ── Descarga (Playwright, UA stealth) ───────────────────────────────────────────────────────
class DescargadorPlaywright:
    """Sesión única de Chromium para todo el lote; el HTML se procesa en memoria.

    Toda navegación y toda espera de render declaran ``TIMEOUT_MS``. Un tiempo
    agotado se traduce a ``DescargaError`` (fallo de ese partido), nunca a un
    proceso colgado.
    """

    def __init__(self, *, headless: bool = True, timeout_ms: int = TIMEOUT_MS) -> None:
        self._headless = headless
        self._timeout_ms = timeout_ms
        self._pw: Any = None
        self._navegador: Any = None
        self._contexto: Any = None
        self._timeout_error: Any = None

    def __enter__(self) -> "DescargadorPlaywright":
        try:
            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
            from playwright.sync_api import sync_playwright
        except ImportError as error:  # noqa: BLE001 — Fail-Loud deliberado
            raise DescargaError(
                "[LN-QBE-143] Playwright no está instalado: "
                "pip install playwright && playwright install chromium"
            ) from error

        self._timeout_error = PlaywrightTimeoutError
        self._pw = sync_playwright().start()
        self._navegador = self._pw.chromium.launch(
            headless=self._headless, args=ARGUMENTOS_NAVEGADOR
        )
        self._contexto = self._navegador.new_context(
            user_agent=USER_AGENT,
            locale="es-MX",
            viewport={"width": 1440, "height": 900},
            timezone_id="America/Mexico_City",
        )
        self._contexto.set_default_timeout(self._timeout_ms)
        return self

    def __exit__(self, *_excepcion: Any) -> None:
        if self._navegador is not None:
            self._navegador.close()
        if self._pw is not None:
            self._pw.stop()

    def descargar(self, url: str) -> str:
        """Captura el DOM renderizado del visor y lo devuelve como HTML en memoria.

        El HTML crudo del servidor no contiene la línea de tiempo: ``toolJugada`` y
        ``data-original-title`` los inyecta el JS del sitio (la captura canónica de
        ``[LN-QBE-136]`` es un volcado CDP del DOM ya renderizado). Por eso se navega
        y se espera la columna canónica antes de leer ``page.content()``.
        """
        pagina = self._contexto.new_page()
        try:
            pagina.set_default_timeout(self._timeout_ms)
            try:
                respuesta = pagina.goto(
                    url, wait_until="domcontentloaded", timeout=self._timeout_ms
                )
            except self._timeout_error as error:
                raise DescargaError(
                    f"[LN-QBE-143] Timeout de navegación ({self._timeout_ms} ms) en {url}"
                ) from error
            if respuesta is None or respuesta.status != 200:
                raise DescargaError(
                    f"[LN-QBE-143] {url} respondió "
                    f"HTTP {respuesta.status if respuesta else 'sin respuesta'}"
                )
            try:
                pagina.wait_for_selector(
                    "div.jugadasTool .toolJugada",
                    state="attached",
                    timeout=self._timeout_ms,
                )
            except self._timeout_error as error:
                raise DescargaError(
                    f"[LN-QBE-143] Timeout de render ({self._timeout_ms} ms): "
                    f"{url} no expuso la línea de tiempo (.toolJugada)"
                ) from error
            html = pagina.content()
        finally:
            try:
                pagina.close()
            except Exception:  # noqa: BLE001 — el cierre nunca debe enmascarar el fallo
                pass
        if not html or not html.strip():
            raise DescargaError(f"[LN-QBE-143] {url} devolvió un DOM vacío")
        return html


# ── Orquestación ────────────────────────────────────────────────────────────────────────────
@dataclass
class RegistroPartido:
    """Resultado por partido (un renglón del lote)."""

    jornada: int
    id_partido: str
    local: str
    visitante: str
    url: str
    estado: str = "OK"
    match_id: Optional[str] = None
    eventos: int = 0
    insertados: int = 0
    ignorados: int = 0
    error_tipo: Optional[str] = None
    error: Optional[str] = None

    def a_dict(self) -> Dict[str, Any]:
        return dict(vars(self))


@dataclass
class ResultadoLote:
    temporada: str
    torneo: str
    jornada_inicio: int
    jornada_fin: int
    registros: List[RegistroPartido] = field(default_factory=list)
    fallos_jornada: List[Dict[str, Any]] = field(default_factory=list)
    omitidos: int = 0

    def resumen(self) -> Dict[str, Any]:
        partidos = len(self.registros)
        ok = sum(1 for registro in self.registros if registro.estado == "OK")
        return {
            "temporada": self.temporada,
            "torneo": self.torneo,
            "jornada_inicio": self.jornada_inicio,
            "jornada_fin": self.jornada_fin,
            "jornadas": self.jornada_fin - self.jornada_inicio + 1,
            "partidos": partidos,
            "ok": ok,
            "fallidos": partidos - ok + len(self.fallos_jornada),
            "omitidos": self.omitidos,
            "eventos_recibidos": sum(r.eventos for r in self.registros),
            "eventos_insertados": sum(r.insertados for r in self.registros),
            "eventos_ignorados": sum(r.ignorados for r in self.registros),
        }


# ── Checkpoint (reanudación) ───────────────────────────────────────────────────────────────
def _clave_partido(temporada: str, torneo: str, id_partido: str) -> str:
    """Identidad estable de un partido dentro del lote reanudable."""
    return f"{temporada}|{torneo}|{id_partido}"


def _leer_checkpoint(ruta: Path) -> Dict[str, Any]:
    """Lee el estado previo; ausente o ilegible ⇒ lote nuevo (nunca aborta)."""
    if not ruta.is_file():
        return {}
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return datos if isinstance(datos, dict) else {}


def _guardar_checkpoint(ruta: Path, estado: Dict[str, Any]) -> None:
    """Escritura atómica: el estado nunca queda a medias si el proceso muere."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    estado["actualizado_utc"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    temporal = ruta.with_name(ruta.name + ".tmp")
    temporal.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")
    temporal.replace(ruta)


def _procesar_partido(
    partido: Dict[str, Any],
    jornada: int,
    *,
    temporada: str,
    db_path: str | Path,
    descargador: Any,
    parser: Callable[[str], Dict[str, Any]],
    resolver: Callable[..., str],
    persistidor: Callable[..., Dict[str, Any]],
) -> RegistroPartido:
    """Procesa un partido; toda excepción se propaga al bucle (que la registra)."""
    registro = RegistroPartido(
        jornada=jornada,
        id_partido=str(partido["id_partido"]),
        local=str(partido["local"]),
        visitante=str(partido["visitante"]),
        url=str(partido["url_minuto_a_minuto"]),
    )
    html = descargador.descargar(registro.url)
    sobre = parser(html)
    # [LN-QBE-145] El Join Determinista no se toca: se le alimentan los nombres
    # canónicos de la bóveda, no los nombres de pantalla del sitio.
    equipo_local = resolver_alias_ligamx(sobre["equipo_local"])
    equipo_visitante = resolver_alias_ligamx(sobre["equipo_visitante"])
    registro.match_id = resolver(
        db_path,
        temporada,
        equipo_local,
        equipo_visitante,
        sobre["marcador_local"],
        sobre["marcador_visitante"],
    )
    resultado = persistidor(db_path, registro.match_id, sobre["eventos"])
    registro.eventos = resultado["recibidos"]
    registro.insertados = resultado["insertados"]
    registro.ignorados = resultado["ignorados"]
    return registro


def ejecutar(
    temporada: str,
    torneo: str,
    jornada_inicio: int,
    jornada_fin: int,
    *,
    db_path: str | Path = DB_DEFECTO,
    descubridor: Optional[Callable[..., List[Dict[str, Any]]]] = None,
    descargador: Any = None,
    parser: Callable[[str], Dict[str, Any]] = parsear_partido_desde_html,
    resolver: Callable[..., str] = resolver_match_id,
    persistidor: Callable[..., Dict[str, Any]] = cargar_eventos,
    reporte_json: Optional[str | Path] = None,
    checkpoint: Optional[str | Path] = None,
    resume: bool = False,
    pausa: float = PAUSA_DEFECTO_S,
    headless: bool = True,
) -> ResultadoLote:
    """[LN-QBE-143] Ejecuta el lote completo y devuelve el resultado con sus fallos.

    ``resume`` reanuda desde ``checkpoint``: los partidos ya persistidos se omiten
    (se cuentan en ``omitidos``) y sólo se reintentan los pendientes y los fallidos.
    """
    if jornada_fin < jornada_inicio:
        raise ValueError(
            f"[LN-QBE-143] Rango de jornadas inválido: {jornada_inicio}..{jornada_fin}"
        )

    if descubridor is None:
        descubridor = lambda temporada_, torneo_, jornada_: descubrir(  # noqa: E731
            temporada_, torneo_, jornada_, headless=headless
        )

    lote = ResultadoLote(temporada, torneo, jornada_inicio, jornada_fin)

    ruta_checkpoint = Path(checkpoint) if checkpoint is not None else None
    completados: set = set()
    ultimo_previo: Optional[Dict[str, Any]] = None
    if resume and ruta_checkpoint is not None:
        previo = _leer_checkpoint(ruta_checkpoint)
        if previo.get("temporada") == temporada and previo.get("torneo") == torneo:
            completados = set(previo.get("completados", []))
            # Un lote que sólo omite no debe borrar la última posición conocida.
            ultimo_previo = previo.get("ultimo_partido")
    estado: Dict[str, Any] = {
        "version": 1,
        "temporada": temporada,
        "torneo": torneo,
        "jornada_inicio": jornada_inicio,
        "jornada_fin": jornada_fin,
        "completados": sorted(completados),
        "ultimo_partido": ultimo_previo,
    }

    # Fase 1 — Descubrimiento. La sonda abre y cierra su propia sesión de
    # Playwright; por eso se completa el rango antes de abrir la sesión de
    # descarga (dos `sync_playwright` anidados en el mismo hilo no son válidos).
    pendientes: List[tuple] = []
    for jornada in range(jornada_inicio, jornada_fin + 1):
        try:
            partidos = list(descubridor(temporada, torneo, str(jornada)))
        except Exception as error:  # noqa: BLE001 — Fail-Loud: se registra y se continúa
            lote.fallos_jornada.append(
                {
                    "jornada": jornada,
                    "error_tipo": type(error).__name__,
                    "error": str(error),
                }
            )
            continue
        pendientes.extend((jornada, partido) for partido in partidos)

    # Fase 2 — Descarga, parseo y persistencia con una sola sesión por lote.
    with (descargador if descargador is not None else DescargadorPlaywright(headless=headless)) as descarga:
        for jornada, partido in pendientes:
            clave = _clave_partido(temporada, torneo, str(partido.get("id_partido", "?")))
            if clave in completados:
                lote.omitidos += 1
                continue
            try:
                registro = _procesar_partido(
                    partido,
                    jornada,
                    temporada=temporada,
                    db_path=db_path,
                    descargador=descarga,
                    parser=parser,
                    resolver=resolver,
                    persistidor=persistidor,
                )
            except Exception as error:  # noqa: BLE001 — Fail-Loud: se registra y se continúa
                registro = RegistroPartido(
                    jornada=jornada,
                    id_partido=str(partido.get("id_partido", "?")),
                    local=str(partido.get("local", "?")),
                    visitante=str(partido.get("visitante", "?")),
                    url=str(partido.get("url_minuto_a_minuto", "?")),
                    estado="FALLO",
                    error_tipo=type(error).__name__,
                    error=str(error),
                )
            lote.registros.append(registro)

            estado["ultimo_partido"] = {
                "clave": clave,
                "jornada": jornada,
                "id_partido": registro.id_partido,
                "estado": registro.estado,
                "match_id": registro.match_id,
                "error": registro.error,
            }
            if registro.estado == "OK":
                completados.add(clave)
                estado["completados"] = sorted(completados)
            if ruta_checkpoint is not None:
                _guardar_checkpoint(ruta_checkpoint, estado)

            if pausa and pausa > 0:
                time.sleep(pausa)

    if ruta_checkpoint is not None:
        _guardar_checkpoint(ruta_checkpoint, estado)
    if reporte_json is not None:
        _escribir_reporte(Path(reporte_json), lote)
    return lote


def _escribir_reporte(ruta: Path, lote: ResultadoLote) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    documento = {
        "nodo": "[LN-QBE-143]",
        "ejecutado_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "resumen": lote.resumen(),
        "fallos_jornada": lote.fallos_jornada,
        "registros": [registro.a_dict() for registro in lote.registros],
    }
    ruta.write_text(json.dumps(documento, ensure_ascii=False, indent=2), encoding="utf-8")


# ── Presentación ────────────────────────────────────────────────────────────────────────────
def _imprimir_tablero(registros: Sequence[RegistroPartido]) -> None:
    cabecera = ("JOR", "ID", "LOCAL", "VISITANTE", "ESTADO", "EVENTOS", "INS", "IGN", "ERROR")
    filas = [
        (
            str(registro.jornada),
            registro.id_partido,
            registro.local,
            registro.visitante,
            registro.estado,
            str(registro.eventos),
            str(registro.insertados),
            str(registro.ignorados),
            (registro.error or "")[:58],
        )
        for registro in registros
    ]
    anchos = [max(len(fila[i]) for fila in [cabecera, *filas]) for i in range(len(cabecera))]
    print(" | ".join(valor.ljust(anchos[i]) for i, valor in enumerate(cabecera)))
    print("-+-".join("-" * ancho for ancho in anchos))
    for fila in filas:
        print(" | ".join(valor.ljust(anchos[i]) for i, valor in enumerate(fila)))


def _imprimir_resumen(resumen: Dict[str, Any], fallos_jornada: Sequence[Dict[str, Any]]) -> None:
    print()
    print(
        f"RESUMEN | jornadas {resumen['jornadas']} | partidos {resumen['partidos']} | "
        f"ok {resumen['ok']} | fallidos {resumen['fallidos']} | "
        f"omitidos {resumen['omitidos']} | "
        f"eventos {resumen['eventos_recibidos']} | "
        f"insertados {resumen['eventos_insertados']} | "
        f"ignorados {resumen['eventos_ignorados']}"
    )
    for fallo in fallos_jornada:
        print(
            f"🔴 Jornada {fallo['jornada']}: {fallo['error_tipo']}: {fallo['error']}"
        )


def main(argv: Optional[Sequence[str]] = None) -> int:
    analizador = argparse.ArgumentParser(
        prog="extraer_historico_ligamx",
        description="[LN-QBE-143] Orquestador de extracción masiva de eventos (ligamx.net).",
    )
    analizador.add_argument("--temporada", required=True, help="ej. 2015-2016")
    analizador.add_argument("--torneo", required=True, help="ej. Clausura")
    analizador.add_argument("--jornada_inicio", required=True, type=int, help="ej. 16")
    analizador.add_argument("--jornada_fin", required=True, type=int, help="ej. 16")
    analizador.add_argument("--db", default=str(DB_DEFECTO), help="bóveda destino")
    analizador.add_argument("--reporte-json", default=None, help="bitácora del lote (JSON)")
    analizador.add_argument(
        "--checkpoint", default=str(CHECKPOINT_DEFECTO), help="estado reanudable del lote"
    )
    analizador.add_argument(
        "--resume",
        action="store_true",
        help="omite los partidos ya persistidos según --checkpoint",
    )
    analizador.add_argument(
        "--pausa",
        type=float,
        default=PAUSA_DEFECTO_S,
        help=f"segundos de espera entre partidos (defecto {PAUSA_DEFECTO_S})",
    )
    analizador.add_argument("--headed", action="store_true", help="Chromium con ventana (debug)")
    argumentos = analizador.parse_args(argv)

    try:
        lote = ejecutar(
            argumentos.temporada,
            argumentos.torneo,
            argumentos.jornada_inicio,
            argumentos.jornada_fin,
            db_path=argumentos.db,
            reporte_json=argumentos.reporte_json,
            checkpoint=argumentos.checkpoint,
            resume=argumentos.resume,
            pausa=argumentos.pausa,
            headless=not argumentos.headed,
        )
    except (DescubrimientoError, DescargaError, AlmacenEventosError, MinutoAJugadaError) as error:
        print(f"🔴 {error}", file=sys.stderr)
        return 2
    except Exception as error:  # noqa: BLE001 — el fallo de lote nunca se silencia
        print(f"🔴 [LN-QBE-143] Fallo de lote: {type(error).__name__}: {error}", file=sys.stderr)
        return 2

    _imprimir_tablero(lote.registros)
    _imprimir_resumen(lote.resumen(), lote.fallos_jornada)
    if lote.registros:
        return 0 if lote.resumen()["fallidos"] == 0 else 1
    if lote.omitidos:
        print(f"ℹ️ Sin pendientes: {lote.omitidos} partidos ya persistidos")
        return 0
    print("🔴 [LN-QBE-143] El lote no procesó ningún partido", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
