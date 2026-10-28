# -*- coding: utf-8 -*-
"""
🛰️ Q-BE — MATRIZ CANÓNICA DE INVESTIGACIÓN (`research_feature_matrix.csv`)
[ARCH-1.4.67] — Instrumento CLI-FIRST de LECTURA PURA (cero DML, cero red, cero navegador).

Misión
------
Publicar el dataset tabular canónico para el Data Scientist aislado: una fila por partido
CONCLUIDO con marcador consumado, y CUATRO zonas disjuntas de columnas:

  · A — IDENTIDAD Y CONTEXTO (`match_id`, `jornada`, `competition_id`, `kickoff_utc`,
        `local`, `visitante`).
  · B — EVIDENCIA FÁCTICA PRE-KICKOFF: las 32 variables del catálogo forense `[LN-QBE-120]`
        × {local, visita} = 64 celdas (`v01_local` … `v32_visita`), transcritas del DTO
        `variables_44` del micro-caso del Visor `[ARCH-1.4.42]`.
  · C — DISTRIBUCIÓN SOBERANA PRE-KICKOFF: P′ servida, vértices de la tríada Δ², masa de
        cobertura, ΔAlt, bandera de rescate, sellos S(I) y procedencia del vector.
  · D — ETIQUETAS CONSUMADAS EN LA CANCHA: marcador, resultado real, clasificación de la
        tríada y Brier de ambas predicciones.

La frontera `A ∪ B ∪ C` (features) ∩ `D` (etiquetas) = ∅ es la GARANTÍA ANTI-FUGA del dataset:
ninguna columna de entrada puede delatar el desenlace (`score`, `goles`, `resultado_real`,
`brier`, `clasificacion`, `tipo_resultado`, `acierto`).

Régimen y autoridad delegada
----------------------------
[HÍBRIDO DUAL-TRACK] — la composición de la matriz, el cruce de identidades y la CLI son
[DBBD-FUNGIBLE]; TODA la matemática se DELEGA en sus planos sellados y esta utilidad no
reimplementa una sola fórmula:

    · `app.routes.backtesting._construir_reporte_calibracion`  [ARCH-1.4.38 / LN-QBE-125 / LN-QBE-127]
    · `src.observatory.core.factor_attribution`                [ARCH-1.4.42 / LN-QBE-120]

Una sola verdad: las filas de la matriz se derivan del MISMO informe que sirve el Visor de
Backtesting, de modo que la matriz JAMÁS puede auditar un universo distinto al publicado (la
resolución al vuelo de `[LN-QBE-127]` se hereda, no se reimplementa).

Uso
---
    python scripts/investigacion/generar_matriz_investigacion.py
    python scripts/investigacion/generar_matriz_investigacion.py --salida data/output/otra.csv
"""

import argparse
import csv
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.observatory.core.factor_attribution import estructurar_catalogo_44_variables  # noqa: E402
from src.storage.gateway import PersistenceGateway  # noqa: E402
from src.storage.models import Match  # noqa: E402
from app.routes.backtesting import (  # noqa: E402
    ORIGEN_P_PRIMA_AL_VUELO,
    _construir_reporte_calibracion,
)

logger = logging.getLogger(__name__)

# [ARCH-1.4.67] Las cuatro zonas disjuntas del dataset canónico. El orden es contractual: el
# encabezado del CSV se DERIVA de esta tupla (cero transcripción manual del header).
ZONAS: Tuple[str, ...] = ("A", "B", "C", "D")

# Lados del catálogo forense: cada variable PRE-KICKOFF se publica para local y visita.
LADOS_CATALOGO: Tuple[str, str] = ("local", "visita")

RUTA_SALIDA_DEFAULT = os.path.join("data", "output", "research_feature_matrix.csv")


def _identificadores_catalogo() -> Tuple[str, ...]:
    """Identificadores `V01..V32` del catálogo ÚNICO, leídos del productor puro (`[LN-QBE-120]`).

    Se invoca `estructurar_catalogo_44_variables()` sin datos: el productor devuelve las 32 celdas
    declaradas con `SIN EVIDENCIA`, y de ahí se toma la lista de identificadores. Cero transcripción
    a mano: si el catálogo cambia, el encabezado de la zona B cambia con él.
    """
    catalogo = estructurar_catalogo_44_variables()
    identificadores: List[str] = []
    for dimension in catalogo.get("dimensiones") or []:
        for variable in dimension.get("variables") or []:
            identificador = str(variable.get("id") or "").strip()
            if identificador:
                identificadores.append(identificador.lower())
    return tuple(identificadores)


COLUMNAS_ZONA_A: Tuple[str, ...] = (
    "match_id",
    "jornada",
    "competition_id",
    "kickoff_utc",
    "local",
    "visitante",
)

# 32 variables × 2 lados = 64 celdas fácticas PRE-KICKOFF.
COLUMNAS_ZONA_B: Tuple[str, ...] = tuple(
    f"{identificador}_{lado}"
    for identificador in _identificadores_catalogo()
    for lado in LADOS_CATALOGO
)

# Distribución soberana PRE-KICKOFF (P′ + tríada Δ² + sellos de procedencia y suficiencia).
COLUMNAS_ZONA_C: Tuple[str, ...] = (
    "p_local",
    "p_empate",
    "p_visitante",
    "r_max",
    "r_mid",
    "r_low",
    "masa_cobertura_pct",
    "p_low_ruptura_pct",
    "delta_alt_metros",
    "rescate_indiferencia",
    "suficiencia_s_i",
    "origen_p_prima",
    "origen_captura",
)

# Etiquetas consumadas en la cancha: la ÚNICA frontera que el modelo no puede ver.
COLUMNAS_ZONA_D: Tuple[str, ...] = (
    "resultado_real",
    "goles_local",
    "goles_visitante",
    "marcador",
    "clasificacion_triada",
    "tipo_resultado",
    "acierto",
    "brier_qbe",
    "brier_mercado",
)

COLUMNAS_MATRIZ: Tuple[str, ...] = (
    COLUMNAS_ZONA_A + COLUMNAS_ZONA_B + COLUMNAS_ZONA_C + COLUMNAS_ZONA_D
)

MAPEO_ZONAS: Dict[str, Tuple[str, ...]] = {
    "A": COLUMNAS_ZONA_A,
    "B": COLUMNAS_ZONA_B,
    "C": COLUMNAS_ZONA_C,
    "D": COLUMNAS_ZONA_D,
}


# ── CRUCE DE IDENTIDADES (sólo lectura) ────────────────────────────────────────
def _contexto_de_boveda(sesion) -> Dict[str, Dict[str, Any]]:
    """Contexto de identidad por partido: competición e instante de saque (`matches`, 3NF).

    Se consulta EXCLUSIVAMENTE la identidad del partido. Ningún agregado vivo (posiciones, forma)
    entra aquí: en un partido histórico serían FUTURO respecto del instante de cálculo y
    contaminarían el dataset con look-ahead.
    """
    contexto: Dict[str, Dict[str, Any]] = {}
    for fila in sesion.query(Match.id, Match.competition_id, Match.kickoff_utc).all():
        saque = fila.kickoff_utc
        contexto[str(fila.id)] = {
            "competition_id": fila.competition_id,
            "kickoff_utc": saque.isoformat() if hasattr(saque, "isoformat") else saque,
        }
    return contexto


def _celdas_catalogo(atribucion: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Traduce el DTO `variables_44` del micro-caso a las 64 celdas de la zona B.

    El DTO publica `local`/`visita` por variable y declara `SIN EVIDENCIA` con `None`: la
    ausencia se transcribe como celda vacía, jamás se rellena [GOVERNANCE-01].
    """
    celdas: Dict[str, Any] = {}
    if not isinstance(atribucion, dict):
        return celdas
    catalogo = atribucion.get("variables_44")
    if not isinstance(catalogo, dict):
        return celdas
    for dimension in catalogo.get("dimensiones") or []:
        if not isinstance(dimension, dict):
            continue
        for variable in dimension.get("variables") or []:
            if not isinstance(variable, dict):
                continue
            identificador = str(variable.get("id") or "").strip().lower()
            if not identificador:
                continue
            for lado in LADOS_CATALOGO:
                celdas[f"{identificador}_{lado}"] = variable.get(lado)
    return celdas


def construir_fila(
    partido: Dict[str, Any],
    contexto: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Compone una fila de la matriz desde el micro-DTO del Visor (fuente única de verdad)."""
    referencia = contexto or {}
    fila: Dict[str, Any] = {columna: None for columna in COLUMNAS_MATRIZ}
    fila.update(
        {
            # Zona A — identidad y contexto.
            "match_id": partido.get("id_partido"),
            "jornada": partido.get("jornada"),
            "competition_id": referencia.get("competition_id"),
            "kickoff_utc": referencia.get("kickoff_utc"),
            "local": partido.get("local"),
            "visitante": partido.get("visitante"),
            # Zona C — distribución soberana PRE-KICKOFF y sus sellos.
            "p_local": partido.get("p_local"),
            "p_empate": partido.get("p_empate"),
            "p_visitante": partido.get("p_visitante"),
            "r_max": partido.get("r_max"),
            "r_mid": partido.get("r_mid"),
            "r_low": partido.get("r_low"),
            "masa_cobertura_pct": partido.get("masa_cobertura_pct"),
            "p_low_ruptura_pct": partido.get("p_low_ruptura_pct"),
            "delta_alt_metros": partido.get("delta_alt_metros"),
            "rescate_indiferencia": partido.get("rescate_indiferencia"),
            "suficiencia_s_i": partido.get("suficiencia_S_I"),
            "origen_p_prima": partido.get("origen_p_prima"),
            "origen_captura": partido.get("origen_captura"),
            # Zona D — etiquetas consumadas en la cancha.
            "resultado_real": partido.get("resultado_real"),
            "goles_local": partido.get("goles_local"),
            "goles_visitante": partido.get("goles_visitante"),
            "marcador": partido.get("marcador"),
            "clasificacion_triada": partido.get("clasificacion_triada"),
            "tipo_resultado": partido.get("tipo_resultado"),
            "acierto": partido.get("acierto"),
            "brier_qbe": partido.get("brier_qbe"),
            "brier_mercado": partido.get("brier_mercado"),
        }
    )
    # Zona B — 64 celdas fácticas PRE-KICKOFF del catálogo forense.
    fila.update(_celdas_catalogo(partido.get("atribucion_factorial")))
    # Contrato interno (no se publica en el CSV): permite a The Shield auditar la frontera.
    fila["_zonas"] = {zona: MAPEO_ZONAS[zona] for zona in ZONAS}
    return fila


def construir_matriz_investigacion(sesion) -> List[Dict[str, Any]]:
    """Matriz canónica: una fila por partido concluido del universo auditado por el Visor.

    [ARCH-1.4.67] Una sola verdad: el universo se toma del MISMO informe de calibración que sirve
    la vitrina, de modo que la matriz hereda la resolución al vuelo de `[LN-QBE-127]` y ninguna
    ceguera de captura queda fuera del dataset.
    """
    informe = _construir_reporte_calibracion(sesion)
    contexto = _contexto_de_boveda(sesion)
    filas: List[Dict[str, Any]] = []
    for jornada in informe.get("jornadas") or []:
        for partido in jornada.get("partidos") or []:
            identificador = str(partido.get("id_partido"))
            filas.append(construir_fila(partido, contexto.get(identificador)))
    logger.info("Matriz de investigación: %d partidos concluidos tabulados.", len(filas))
    return filas


# ── PUBLICACIÓN DEL ARTEFACTO ─────────────────────────────────────────────────
def exportar_matriz(filas: Sequence[Dict[str, Any]], ruta: str) -> str:
    """Escribe el CSV canónico (UTF-8 sin BOM, `newline=''`, encabezado = contrato declarado).

    El encabezado se deriva de `COLUMNAS_MATRIZ`; las claves internas (`_zonas`) no se publican.
    """
    directorio = os.path.dirname(os.path.abspath(ruta))
    if directorio and not os.path.isdir(directorio):
        os.makedirs(directorio, exist_ok=True)
    with open(ruta, "w", encoding="utf-8", newline="") as archivo:
        escritor = csv.DictWriter(
            archivo,
            fieldnames=list(COLUMNAS_MATRIZ),
            extrasaction="ignore",
            lineterminator="\n",
        )
        escritor.writeheader()
        for fila in filas:
            escritor.writerow(fila)
    return os.path.abspath(ruta)


def _imprimir_reporte(filas: Sequence[Dict[str, Any]], ruta_csv: str) -> int:
    """Epílogo ejecutivo: cardinalidad, cobertura fáctica y sellos de procedencia."""
    total = len(filas)
    print("=" * 90)
    print("🛰️ Q-BE — MATRIZ CANÓNICA DE INVESTIGACIÓN [ARCH-1.4.67]")
    print("   Régimen: [DBBD-FUNGIBLE] · Solo lectura · Matemática sellada delegada")
    print("=" * 90)
    print(f"  ARCHIVO  : {ruta_csv}")
    print(f"  FILAS    : {total} partidos concluidos | COLUMNAS: {len(COLUMNAS_MATRIZ)}")
    print(
        "  ZONAS    : "
        f"A={len(COLUMNAS_ZONA_A)} · B={len(COLUMNAS_ZONA_B)} · "
        f"C={len(COLUMNAS_ZONA_C)} · D={len(COLUMNAS_ZONA_D)}"
    )
    if total == 0:
        print("  ⚠️  Sin partidos concluidos: cero cifras fabricadas.")
        print("=" * 90)
        return 1

    celdas_zonas_b = sum(
        1 for fila in filas for columna in COLUMNAS_ZONA_B if fila.get(columna) not in (None, "")
    )
    print(f"  EVIDENCIA (zona B): {celdas_zonas_b} celdas fácticas materializadas")
    resueltos = sum(1 for fila in filas if fila.get("origen_p_prima") == ORIGEN_P_PRIMA_AL_VUELO)
    print(
        f"  PROCEDENCIA P′: AL_VUELO={resueltos} | "
        f"CAPTURA={sum(1 for fila in filas if fila.get('origen_p_prima') == 'CAPTURA')} | "
        f"SOBERANA={sum(1 for fila in filas if fila.get('origen_p_prima') == 'SOBERANA')}"
    )
    informados = sum(1 for fila in filas if fila.get("suficiencia_s_i") == 1)
    print(f"  S(I)=1 (segmento calibrado): {informados} de {total}")
    jornadas = sorted({fila.get("jornada") for fila in filas if fila.get("jornada") is not None})
    if jornadas:
        print(f"  JORNADAS : {min(jornadas)}-{max(jornadas)}")
    print("=" * 90)
    return 0


def _configurar_bd(ruta: str) -> None:
    """Reapunta el Gateway a una 3NF alterna (p. ej. `data/qbe_historico.db`)."""
    import src.config as cfg

    absoluta = os.path.abspath(ruta)
    cfg.settings.DATABASE_URL = f"sqlite:///{absoluta.replace(os.sep, '/')}"
    PersistenceGateway._instance = None


def ejecutar(argv: Optional[Sequence[str]] = None) -> int:
    """Punto de entrada: lectura pura de la bóveda, tabulación y publicación del CSV."""
    parser = argparse.ArgumentParser(
        description="Publica la matriz canónica de investigación (cuatro zonas, sin fuga de etiquetas).",
    )
    parser.add_argument(
        "--salida",
        default=RUTA_SALIDA_DEFAULT,
        help=f"ruta del CSV de salida (default: {RUTA_SALIDA_DEFAULT})",
    )
    parser.add_argument(
        "--db",
        default=None,
        help="SQLite alterna (p. ej. data/qbe_historico.db); omítala para la bóveda viva.",
    )
    args = parser.parse_args(argv)

    if args.db:
        _configurar_bd(str(args.db))
    gateway = PersistenceGateway()
    with gateway.read_session() as sesion:
        filas = construir_matriz_investigacion(sesion)

    ruta_csv = exportar_matriz(filas, args.salida)
    return _imprimir_reporte(filas, ruta_csv)


def main() -> int:
    """Punto de entrada CLI.

    La consola de Windows arranca en `cp1252` y el epílogo publica sellos con pictogramas: se
    asegura UTF-8 antes de imprimir (convención homóloga al resto de las CLIs del repositorio).
    El reajuste vive aquí y NO en el import: el módulo permanece hermético bajo The Shield.
    """
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (AttributeError, OSError, ValueError):
            pass
    return ejecutar()


if __name__ == "__main__":
    raise SystemExit(main())
