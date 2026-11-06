# -*- coding: utf-8 -*-
"""`[TAREA 50.4-bis]` Backtest definitivo de Fase 9 — tres estrategias y ejecución asimétrica.

Régimen ``[DIRGEN-STRICT]``. Sólo lectura sobre ``qbe_historico.db``
(``mode=ro`` + ``PRAGMA query_only=ON``). No reimplementa matemática de ``qbe_core``:
consume ``desmarginar_shin`` / ``consenso_shin_multicasa`` (`[LN-QBE-151]`), el proyector
`[LN-QBE-152]` y la cascada sellada `[LN-QBE-060-B]`.

Estrategias
-----------
* **A — El Rescate.** Cuando ``P_mid(Q-BE) > P_mid(mercado)`` y la cascada emite
  ``QBE-H1`` o ``QBE-R2``, se construye la cobertura sintética con liquidación ``V=0``:
  la pata de seguro (el empate) se dimensiona con ``1/O_empate`` de modo que, si cae,
  el retorno iguala el stake; la otra pata absorbe el resto y produce el beneficio.
* **B — Los Derivados.** Requiere cuota de mercado de Under 2.5 / BTTS. La bóveda no
  publica ninguna: se declara ``SIN EVIDENCIA`` (no se fabrica un benchmark).
* **C — La Híbrida.** A ∪ B. Al no existir la pata B, C se reporta como A con la
  componente B declarada ausente.

Motor de Ejecución Asimétrica
-----------------------------
``_mejor_momio(mercado_por_casino, seleccion)`` elige la cuota máxima por desenlace entre
los casinos disponibles y registra en cuál se ingresó. Con la bóveda actual (una sola
fuente) la selección es trivial; el motor soporta N fuentes sin cambios.

Uso::

    python scripts/investigacion/fase9_backtest_estrategias.py
"""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

RAIZ_PROYECTO = Path(__file__).resolve().parents[2]
for _ruta in (RAIZ_PROYECTO, RAIZ_PROYECTO / "qbe_core"):
    if str(_ruta) not in sys.path:
        sys.path.insert(0, str(_ruta))

if hasattr(sys.stdout, "reconfigure"):
    try:  # consola Windows cp1252
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, OSError, ValueError):  # pragma: no cover
        pass

from src.core.consensus import (  # noqa: E402
    InvalidOddsException,
    clasificar_origen_dato,
    consenso_shin_multicasa,
)
from src.core.contracts.portfolio_math import (  # noqa: E402
    triaje_determinista_9_estrategias,
)

DB_DEFECTO = RAIZ_PROYECTO / "qbe_observatory" / "data" / "qbe_historico.db"
SALIDA_DEFECTO = RAIZ_PROYECTO / "data" / "reportes" / "fase9_backtest_estrategias.json"

OVERROUND_MIN_ADMISIBLE = 0.8500
OVERROUND_MAX_ADMISIBLE = 1.3000
NOMBRES = ("LOCAL", "EMPATE", "VISITANTE")


# ═══════════════════════════════════════════════════════════════════════════════════════
# Utilidades
# ═══════════════════════════════════════════════════════════════════════════════════════


def _conectar(ruta: Path) -> sqlite3.Connection:
    conexion = sqlite3.connect(f"file:{ruta.as_posix()}?mode=ro", uri=True)
    conexion.execute("PRAGMA query_only = ON")
    if int(conexion.execute("PRAGMA query_only").fetchone()[0]) != 1:
        raise RuntimeError("La bóveda no quedó en query_only=ON: se aborta el backtest.")
    return conexion


def _orden(probabilidades: Sequence[float]) -> Tuple[int, int, int]:
    """Índices ordenados por probabilidad descendente: (P_max, P_mid, P_low)."""
    indice_max = max(range(3), key=lambda i: probabilidades[i])
    indice_min = min(range(3), key=lambda i: probabilidades[i])
    indice_mid = 3 - indice_max - indice_min
    return indice_max, indice_mid, indice_min


def _mejor_momio(
    mercado_por_casino: Dict[str, Dict[str, float]], seleccion: str
) -> Tuple[str, float]:
    """[Ejecución Asimétrica] Mejor cuota para un desenlace entre todos los casinos."""
    mejor_casino, mejor_cuota = "", 0.0
    for casino, momios in mercado_por_casino.items():
        cuota = float(momios[seleccion])
        if cuota > mejor_cuota:
            mejor_casino, mejor_cuota = casino, cuota
    return mejor_casino, mejor_cuota


def _resultado(indice: int, goles_local: int, goles_visita: int) -> bool:
    if indice == 0:
        return goles_local > goles_visita
    if indice == 1:
        return goles_local == goles_visita
    return goles_visita > goles_local


def _brier_3n(probabilidades: Sequence[float], indice: int) -> float:
    observado = [0.0, 0.0, 0.0]
    observado[indice] = 1.0
    return math.fsum((p - y) ** 2 for p, y in zip(probabilidades, observado)) / 3.0


def _resumen(valores: Sequence[float]) -> Dict[str, Any]:
    n = len(valores)
    if n == 0:
        return {"n": 0, "media": None, "sd": None, "se": None}
    media = math.fsum(valores) / n
    sd = statistics.pstdev(valores) if n > 1 else 0.0
    se = sd / math.sqrt(n) if n > 1 else 0.0
    return {"n": n, "media": media, "sd": sd, "se": se, "ic95": [media - 1.96 * se, media + 1.96 * se]}


# ═══════════════════════════════════════════════════════════════════════════════════════
# Carga
# ═══════════════════════════════════════════════════════════════════════════════════════


def _cargar(conexion: sqlite3.Connection) -> List[Dict[str, Any]]:
    filas = conexion.execute(
        """
        SELECT m.match_id, m.temporada, m.home_goals, m.away_goals,
               m.odd_home, m.odd_draw, m.odd_away,
               d.p_local, d.p_empate, d.p_visitante,
               d.lambda_home, d.lambda_away
          FROM historical_matches m
          JOIN historical_sovereign_distributions d ON d.match_id = m.match_id
         WHERE m.home_goals IS NOT NULL AND m.away_goals IS NOT NULL
           AND m.odd_home > 1.0 AND m.odd_draw > 1.0 AND m.odd_away > 1.0
        """
    ).fetchall()
    return [
        {
            "match_id": fila[0],
            "temporada": fila[1],
            "goles_local": int(fila[2]),
            "goles_visita": int(fila[3]),
            "momios": {"L": float(fila[4]), "E": float(fila[5]), "V": float(fila[6])},
            "qbe": (float(fila[7]), float(fila[8]), float(fila[9])),
            "lambda_home": float(fila[10]),
            "lambda_away": float(fila[11]),
        }
        for fila in filas
    ]


# ═══════════════════════════════════════════════════════════════════════════════════════
# Estrategias
# ═══════════════════════════════════════════════════════════════════════════════════════


def _evaluar(
    partidos: Sequence[Dict[str, Any]],
    *,
    umbral_pmid: float,
    cuota_derivados: Optional[Dict[str, Dict[str, float]]] = None,
    umbral_derivados: float = 0.08,
) -> Dict[str, Any]:
    estrategia_a: List[Dict[str, Any]] = []
    estrategia_b: List[Dict[str, Any]] = []
    resumen = {
        "evaluados": 0,
        "sin_distribucion": 0,
        "overround_fuera_de_banda": 0,
        "shin_invalido": 0,
        "pmid_fuera_de_cobertura": 0,
    }
    casinos_usados: Dict[str, int] = {}

    for partido in partidos:
        resumen["evaluados"] += 1
        momios = partido["momios"]
        sobre = math.fsum(1.0 / momios[k] for k in ("L", "E", "V"))
        if not (OVERROUND_MIN_ADMISIBLE <= sobre <= OVERROUND_MAX_ADMISIBLE):
            resumen["overround_fuera_de_banda"] += 1
            continue
        try:
            consenso = consenso_shin_multicasa({"footystats": (momios["L"], momios["E"], momios["V"])})
        except InvalidOddsException:
            resumen["shin_invalido"] += 1
            continue
        q_mkt = consenso.q_mkt_consenso
        q_qbe = partido["qbe"]
        _, mid_mkt, _ = _orden(q_mkt)
        max_qbe, mid_qbe, low_qbe = _orden(q_qbe)

        # ── Estrategia A: rescate por cobertura sintética ─────────────────────────
        if q_qbe[mid_qbe] > q_mkt[mid_mkt] + umbral_pmid:
            payload = {
                "p_local": q_qbe[0],
                "p_empate": q_qbe[1],
                "p_visitante": q_qbe[2],
                "es_operable": True,
                "delta_epist": 0.0,
            }
            cuotas = {"L": momios["L"], "E": momios["E"], "V": momios["V"], "pa": True}
            veredicto = triaje_determinista_9_estrategias(payload, cuotas, gamma=0.67)
            codigo = veredicto.get("codigo")
            if codigo in ("QBE-H1", "QBE-R2"):
                # Patas de la cobertura: H1 = {P_max, empate}; R2 = {empate, P_low}.
                if codigo == "QBE-H1":
                    pata_a, pata_b = max_qbe, 1
                else:
                    pata_a, pata_b = low_qbe, 1
                cobertura = {pata_a, pata_b}
                if pata_a == pata_b:
                    continue
                # [V=0] El seguro DEBE ser el vértice P_mid de Q-BE. Si la cobertura
                # no lo contiene, la liquidación V=0 no es honrable: se descarta.
                if mid_qbe not in cobertura:
                    resumen["pmid_fuera_de_cobertura"] += 1
                    continue
                pata_seguro = mid_qbe
                pata_primaria = (cobertura - {pata_seguro}).pop()
                seleccion_primaria = ("L", "E", "V")[pata_primaria]
                seleccion_seguro = ("L", "E", "V")[pata_seguro]
                casino_primaria, odd_primaria = _mejor_momio(
                    {"footystats": momios}, seleccion_primaria
                )
                casino_seguro, odd_seguro = _mejor_momio(
                    {"footystats": momios}, seleccion_seguro
                )
                stake_seguro = 1.0 / odd_seguro           # V=0 si cae el seguro
                stake_primaria = 1.0 - stake_seguro
                if stake_primaria <= 0.0:
                    continue
                gano_primaria = _resultado(pata_primaria, partido["goles_local"], partido["goles_visita"])
                gano_seguro = _resultado(pata_seguro, partido["goles_local"], partido["goles_visita"])
                if gano_primaria:
                    beneficio = stake_primaria * odd_primaria - 1.0
                elif gano_seguro:
                    beneficio = 0.0
                else:
                    beneficio = -1.0
                probabilidad_cobertura = q_qbe[pata_primaria] + q_qbe[pata_seguro]
                exito = 1.0 if (gano_primaria or gano_seguro) else 0.0
                estrategia_a.append(
                    {
                        "match_id": partido["match_id"],
                        "temporada": partido["temporada"],
                        "codigo": codigo,
                        "seleccion_primaria": seleccion_primaria,
                        "seleccion_seguro": seleccion_seguro,
                        "casino_primaria": casino_primaria,
                        "casino_seguro": casino_seguro,
                        "odd_primaria": odd_primaria,
                        "odd_seguro": odd_seguro,
                        "beneficio": beneficio,
                        "exito": exito,
                        "p_cobertura": probabilidad_cobertura,
                        "brier_cobertura": (probabilidad_cobertura - exito) ** 2 / 2.0,
                    }
                )
                for casino in (casino_primaria, casino_seguro):
                    casinos_usados[casino] = casinos_usados.get(casino, 0) + 1

        # ── Estrategia B: derivados (requiere cuota de mercado) ───────────────────
        if cuota_derivados is not None:
            mercado = cuota_derivados.get(partido["match_id"])
            if not mercado:
                continue
            from src.core.distribution_dixon_coles import (
                calcular_matriz_dixon_coles,
                proyectar_mercados_derivados,
            )

            matriz = calcular_matriz_dixon_coles(
                lambda_h=partido["lambda_home"], lambda_a=partido["lambda_away"], rho=None, k_max=6
            )
            proyeccion = proyectar_mercados_derivados(matriz)
            goles = partido["goles_local"] + partido["goles_visita"]
            for mercado_nombre, p_modelo, gano_seleccion, cuota in (
                ("UNDER_25", proyeccion.p_under_25, goles <= 2, float(mercado.get("under_25", 0.0))),
                ("BTTS_NO", proyeccion.p_btts_no, not (partido["goles_local"] >= 1 and partido["goles_visita"] >= 1), float(mercado.get("btts_no", 0.0))),
            ):
                if cuota <= 1.0:
                    continue
                p_mercado = 1.0 / cuota
                if p_modelo - p_mercado <= umbral_derivados:
                    continue
                beneficio = (cuota - 1.0) if gano_seleccion else -1.0
                estrategia_b.append(
                    {
                        "match_id": partido["match_id"],
                        "temporada": partido["temporada"],
                        "mercado": mercado_nombre,
                        "p_modelo": p_modelo,
                        "p_mercado": p_mercado,
                        "cuota": cuota,
                        "beneficio": beneficio,
                        "exito": 1.0 if gano_seleccion else 0.0,
                        "brier": (p_modelo - (1.0 if gano_seleccion else 0.0)) ** 2 / 2.0,
                    }
                )

    def bloque(boletos: List[Dict[str, Any]], nombre: str) -> Dict[str, Any]:
        beneficios = [boleto["beneficio"] for boleto in boletos]
        brier = [boleto.get("brier_cobertura", boleto.get("brier")) for boleto in boletos]
        resumen_roi = _resumen(beneficios)
        resumen_brier = _resumen([valor for valor in brier if valor is not None])
        return {
            "estrategia": nombre,
            "n_boletos": len(boletos),
            "roi": resumen_roi["media"],
            "roi_ic95": resumen_roi.get("ic95"),
            "tasa_acierto": (
                sum(1 for boleto in boletos if boleto.get("exito")) / len(boletos)
                if boletos
                else None
            ),
            "brier_2n": resumen_brier["media"],
            "por_temporada": _por_temporada(boletos),
        }

    resultado = {
        "universo": dict(resumen),
        "estrategia_a": bloque(estrategia_a, "A_RESCATE"),
        "estrategia_b": bloque(estrategia_b, "B_DERIVADOS"),
        "casinos_usados": dict(sorted(casinos_usados.items(), key=lambda par: -par[1])),
        "boletos_a": estrategia_a,
        "boletos_b": estrategia_b,
    }
    return resultado


def _por_temporada(boletos: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    agrupado: Dict[str, List[float]] = {}
    for boleto in boletos:
        agrupado.setdefault(str(boleto["temporada"]), []).append(float(boleto["beneficio"]))
    return {
        temporada: {"n": len(valores), "roi": math.fsum(valores) / len(valores)}
        for temporada, valores in sorted(agrupado.items())
    }


# ═══════════════════════════════════════════════════════════════════════════════════════
# Reporte
# ═══════════════════════════════════════════════════════════════════════════════════════


def _imprimir(reporte: Dict[str, Any]) -> None:
    print("=" * 86)
    print("TAREA 50.4-bis — BACKTEST DE 3 ESTRATEGIAS · EJECUCIÓN ASIMÉTRICA")
    print("=" * 86)
    universo = reporte["universo"]
    print(f"Partidos con P' + cuotas + marcador : {universo['evaluados']:,}")
    print(f"Excluidos por overround             : {universo['overround_fuera_de_banda']:,}")
    print(f"Excluidos por Shin inválido         : {universo['shin_invalido']:,}")
    print()
    for clave, titulo in (
        ("estrategia_a", "A · EL RESCATE (cobertura sintética V=0)"),
        ("estrategia_b", "B · LOS DERIVADOS (Under 2.5 / BTTS No)"),
        ("estrategia_c", "C · LA HÍBRIDA (A ∪ B)"),
    ):
        bloque = reporte[clave]
        print(titulo)
        print("-" * 86)
        if bloque.get("estado") == "SIN EVIDENCIA":
            print(f"  SIN EVIDENCIA — {bloque.get('motivo', '')}")
            print()
            continue
        roi = bloque["roi"]
        print(f"  Boletos           : {bloque['n_boletos']:,}")
        print(f"  ROI               : {'—' if roi is None else f'{roi:+.2%}'}"
              + (f"  IC95 [{bloque['roi_ic95'][0]:+.2%}, {bloque['roi_ic95'][1]:+.2%}]" if bloque.get("roi_ic95") else ""))
        acierto = bloque.get("tasa_acierto")
        print(f"  Tasa de acierto   : {'—' if acierto is None else f'{acierto:.2%}'}")
        brier = bloque.get("brier_2n")
        print(f"  Brier 2N          : {'—' if brier is None else f'{brier:.6f}'}")
        print()
    print("EJECUCIÓN ASIMÉTRICA — casinos usados")
    print("-" * 86)
    for casino, n in reporte["casinos_usados"].items():
        print(f"  {casino:<24}{n:>8,} patas")
    print()
    print("RESUMEN EJECUTIVO")
    print("-" * 86)
    for linea in reporte["resumen_ejecutivo"]:
        print(f"  {linea}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    analizador = argparse.ArgumentParser(
        description="[TAREA 50.4-bis] Backtest de estrategias A/B/C con ejecución asimétrica."
    )
    analizador.add_argument("--db", type=Path, default=DB_DEFECTO)
    analizador.add_argument("--out", type=Path, default=SALIDA_DEFECTO)
    analizador.add_argument("--umbral-pmid", type=float, default=0.0)
    analizador.add_argument("--cuotas-derivados", type=Path, default=None,
                            help="JSON {match_id: {under_25, btts_no}} con cuotas de derivados (opcional).")
    argumentos = analizador.parse_args(argv)

    ruta_db = argumentos.db.resolve()
    if not ruta_db.exists():
        print(f"ERROR: no existe la bóveda {ruta_db}", file=sys.stderr)
        return 2

    cuotas_derivados = None
    if argumentos.cuotas_derivados:
        cuotas_derivados = json.loads(argumentos.cuotas_derivados.read_text(encoding="utf-8"))

    conexion = _conectar(ruta_db)
    try:
        partidos = _cargar(conexion)
    finally:
        conexion.close()

    resultado = _evaluar(
        partidos,
        umbral_pmid=argumentos.umbral_pmid,
        cuota_derivados=cuotas_derivados,
    )

    estrategia_a = resultado["estrategia_a"]
    estrategia_b = resultado["estrategia_b"]
    if cuotas_derivados is None:
        estrategia_b = {
            "estrategia": "B_DERIVADOS",
            "estado": "SIN EVIDENCIA",
            "motivo": (
                "La bóveda no contiene cuotas históricas de Totales ni de BTTS; sin precio "
                "de mercado no existe la condición 'Q-BE > mercado + 8%'. No se fabrica."
            ),
            "n_boletos": 0,
            "roi": None,
            "tasa_acierto": None,
            "brier_2n": None,
        }
    estrategia_c = {
        "estrategia": "C_HIBRIDA",
        "n_boletos": estrategia_a["n_boletos"] + (estrategia_b.get("n_boletos") or 0),
        "roi": estrategia_a["roi"],
        "roi_ic95": estrategia_a.get("roi_ic95"),
        "tasa_acierto": estrategia_a.get("tasa_acierto"),
        "brier_2n": estrategia_a.get("brier_2n"),
        "componente_b": estrategia_b.get("estado", "OPERATIVA"),
        "nota": (
            "C = A ∪ B. La componente B está ausente por falta de cuotas de derivados; "
            "C hereda el resultado de A y no lo mejora."
        ),
    }

    roi_a = estrategia_a["roi"]
    resumen_ejecutivo = [
        f"Estrategia A: {estrategia_a['n_boletos']:,} boletos, ROI "
        + ("—" if roi_a is None else f"{roi_a:+.2%}")
        + ".",
        "Estrategia B: SIN EVIDENCIA (sin cuotas históricas de derivados).",
        "Estrategia C: hereda A; sin componente B no puede cruzar a positivo por sí sola.",
        "Ejecución asimétrica: "
        + ", ".join(f"{casino} ({n:,} patas)" for casino, n in resultado["casinos_usados"].items()),
    ]

    reporte = {
        "meta": {
            "tarea": "50.4-bis",
            "expediente": "SPRINT-50-REINGENIERIA-INDUSTRIAL-QBE-CORE",
            "generado_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "regimen": "[DIRGEN-STRICT]",
            "db": str(ruta_db),
        },
        "universo": resultado["universo"],
        "estrategia_a": estrategia_a,
        "estrategia_b": estrategia_b,
        "estrategia_c": estrategia_c,
        "casinos_usados": resultado["casinos_usados"],
        "resumen_ejecutivo": resumen_ejecutivo,
        "boletos_a": resultado["boletos_a"],
        "boletos_b": resultado["boletos_b"],
    }

    argumentos.out.parent.mkdir(parents=True, exist_ok=True)
    argumentos.out.write_text(
        json.dumps(reporte, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    _imprimir(reporte)
    print(f"Reporte JSON: {argumentos.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
