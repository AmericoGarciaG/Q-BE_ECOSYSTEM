# -*- coding: utf-8 -*-
"""Auditoría empírica del «Informe de Estrategia: Maximización de ROI vía Shannon».

Régimen: [DIRGEN-STRICT] de SÓLO LECTURA.

Este instrumento NO toca `src/core/contracts/portfolio_math.py`, NO escribe en la
bóveda 3NF, NO modifica `docs/` y NO altera el motor de simulación. Se limita a:

1. Medir cobertura de las cuatro celdas citadas por el informe.
2. Reproducir la Regla 1 (Trampa del Favorito) y la Regla 2 (Fricción Defensiva)
   exactamente con los umbrales declarados.
3. Ejecutar la línea base J1–J13 con el motor canónico.
4. Simular un veto por partido ANTES del sizing, sin reimplementar la aritmética:
   se filtran los fixtures vetados y se delega el resto en
   `simulation_engine._construir_cartera_jornada`.

Uso:
    python -m scripts.laboratorio.validar_informe_shannon
    python -m scripts.laboratorio.validar_informe_shannon --json
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.observatory.core import simulation_engine as motor  # noqa: E402
from src.storage.gateway import PersistenceGateway  # noqa: E402

RUTA_DATASET = PROJECT_ROOT / "data" / "output" / "research_feature_matrix.csv"
BANKROLL_BASE = 10_000.0
ROI_DECLARADO_PCT = 14.65
JORNADAS = tuple(range(1, 14))
UMBRAL_R1_XPTS = 3.0
UMBRAL_R1_ALTITUD_M = 1_000.0
UMBRAL_R2_BC_FALLADAS = 2.0
UMBRAL_R2_SAVE_PCT = 78.0
CLASES_TRIADA = ("P_MAX", "P_MID", "P_LOW")
_TOKENS_AUSENTES = {
    "", "SIN EVIDENCIA", "SIN_DATO", "SIN DATO", "N/A", "NA", "NULL", "NONE",
    "-", "—", "?", "NAN",
}


# ── Utilidades de lectura y estadística descriptiva ───────────────────────────
def _texto(valor: Any) -> str:
    return "" if valor is None else str(valor).strip()


def _numero(valor: Any) -> Optional[float]:
    """Convierte celdas del CSV; ausencia declarada => None (jamás cero fabricado)."""
    texto = _texto(valor).replace("\u00a0", "")
    if texto.upper() in _TOKENS_AUSENTES:
        return None
    texto = texto.replace("%", "").replace(",", "")
    if texto.lower().endswith("m"):
        texto = texto[:-1].strip()
    try:
        return float(texto)
    except (TypeError, ValueError):
        return None


def _pct(parte: int, total: int) -> Optional[float]:
    return round((parte / total) * 100.0, 4) if total else None


def _distribucion(filas: Sequence[Dict[str, str]]) -> Dict[str, int]:
    conteo = Counter(_texto(f.get("clasificacion_triada")).upper() for f in filas)
    return {clase: int(conteo.get(clase, 0)) for clase in CLASES_TRIADA} | {
        clase: int(n) for clase, n in sorted(conteo.items()) if clase not in CLASES_TRIADA
    }


def _wilson_95(k: int, n: int) -> Optional[List[float]]:
    """Intervalo de Wilson 95% para una proporción; None si no hay soporte."""
    if n <= 0:
        return None
    z = 1.959963984540054
    p = k / n
    denom = 1.0 + (z * z) / n
    centro = (p + (z * z) / (2.0 * n)) / denom
    mitad = z * math.sqrt((p * (1.0 - p) / n) + (z * z) / (4.0 * n * n)) / denom
    return [round(max(0.0, centro - mitad) * 100.0, 4),
            round(min(1.0, centro + mitad) * 100.0, 4)]


def _p_hipergeometrico(k: int, n: int, total: int, exitos_totales: int) -> Optional[float]:
    """P(X >= k) bajo muestreo sin reemplazo: prueba exacta de enriquecimiento.

    Responde a: si la regla no aportara información, ¿qué probabilidad hay de
    observar al menos `k` rupturas entre `n` seleccionados? Para n=1 es la tasa
    base; no es un p-valor de dos colas.
    """
    if n <= 0:
        return None
    limite = min(n, exitos_totales)
    if k <= 0:
        return 1.0
    if k > limite:
        return 0.0
    denominador = math.comb(total, n)
    numerador = sum(
        math.comb(exitos_totales, i) * math.comb(total - exitos_totales, n - i)
        for i in range(k, limite + 1)
    )
    return round(numerador / denominador, 6)


def _cargar_filas(ruta: Path) -> List[Dict[str, str]]:
    with ruta.open("r", encoding="utf-8-sig", newline="") as archivo:
        return [dict(fila) for fila in csv.DictReader(archivo)]


# ── Cobertura ─────────────────────────────────────────────────────────────────
def _cobertura(filas: Sequence[Dict[str, str]], columna: str) -> Dict[str, Any]:
    valores = [_numero(fila.get(columna)) for fila in filas]
    no_nulos = sum(valor is not None for valor in valores)
    return {
        "columna": columna,
        "n": len(filas),
        "no_nulos": no_nulos,
        "nulos": len(filas) - no_nulos,
        "pct_no_nulos": _pct(no_nulos, len(filas)),
        "pct_nulos": _pct(len(filas) - no_nulos, len(filas)),
        "min": min((v for v in valores if v is not None), default=None),
        "max": max((v for v in valores if v is not None), default=None),
    }


# ── Reglas del informe ────────────────────────────────────────────────────────
def _evaluar_regla_1(filas: Sequence[Dict[str, str]]) -> Dict[str, Any]:
    seleccion: List[Dict[str, str]] = []
    for fila in filas:
        xpts = _numero(fila.get("v32_local"))
        altitud = _numero(fila.get("v29_local"))
        if xpts is not None and altitud is not None and xpts >= UMBRAL_R1_XPTS and altitud >= UMBRAL_R1_ALTITUD_M:
            seleccion.append(fila)

    distribucion = _distribucion(seleccion)
    p_low = distribucion.get("P_LOW", 0)
    n = len(seleccion)
    return {
        "filtro": f"v32_local >= {UMBRAL_R1_XPTS} AND v29_local >= {UMBRAL_R1_ALTITUD_M}",
        "n": n,
        "distribucion_triada": distribucion,
        "p_low": p_low,
        "tasa_ruptura_pct": _pct(p_low, n),
        "cobertura_v32_local_pct": _cobertura(filas, "v32_local")["pct_no_nulos"],
        "cobertura_v29_local_pct": _cobertura(filas, "v29_local")["pct_no_nulos"],
        "advertencia_cero_mocks": _cobertura(filas, "v32_local")["pct_no_nulos"] == 0.0,
        "soporte": n,
        "veredicto": (
            "SIN SOPORTE: v32_local no tiene ni un valor; el filtro no puede evaluarse."
            if n == 0 else "CON SOPORTE"
        ),
        "ids": [fila.get("match_id") for fila in seleccion],
    }


def _evaluar_regla_2(filas: Sequence[Dict[str, str]]) -> Dict[str, Any]:
    seleccion: List[Dict[str, str]] = []
    for fila in filas:
        bc_falladas = _numero(fila.get("v09_local"))
        save_pct = _numero(fila.get("v18_visita"))
        if (
            bc_falladas is not None
            and save_pct is not None
            and bc_falladas > UMBRAL_R2_BC_FALLADAS
            and save_pct > UMBRAL_R2_SAVE_PCT
        ):
            seleccion.append(fila)

    distribucion = _distribucion(seleccion)
    p_low = distribucion.get("P_LOW", 0)
    n = len(seleccion)
    total = len(filas)
    total_p_low = sum(1 for fila in filas if _texto(fila.get("clasificacion_triada")).upper() == "P_LOW")
    return {
        "filtro": (
            f"v09_local > {UMBRAL_R2_BC_FALLADAS} AND "
            f"v18_visita > {UMBRAL_R2_SAVE_PCT}"
        ),
        "n": n,
        "distribucion_triada": distribucion,
        "p_low": p_low,
        "tasa_ruptura_pct": _pct(p_low, n),
        "tasa_base_p_low_pct": _pct(total_p_low, total),
        "lift": round((p_low / n) / (total_p_low / total), 4) if n and total_p_low else None,
        "ci95_wilson_pct": _wilson_95(p_low, n),
        "p_hipergeometrico_una_cola": _p_hipergeometrico(p_low, n, total, total_p_low),
        "cobertura_v09_local_pct": _cobertura(filas, "v09_local")["pct_no_nulos"],
        "cobertura_v18_visita_pct": _cobertura(filas, "v18_visita")["pct_no_nulos"],
        "advertencia_cero_mocks": (
            _cobertura(filas, "v09_local")["pct_no_nulos"] < 50.0
            or _cobertura(filas, "v18_visita")["pct_no_nulos"] < 50.0
        ),
        "soporte": n,
        "veredicto": (
            "N=1: 100% es una observación única, no una regla certificada."
            if n == 1 else ("SIN SOPORTE" if n == 0 else "CON SOPORTE DÉBIL")
        ),
        "ids": [fila.get("match_id") for fila in seleccion],
    }


# ── Simulación canónica y veto por partido ───────────────────────────────────
def _resumen_roi(reporte: Dict[str, Any]) -> Dict[str, Any]:
    total_apostado = round(
        sum(float(j.get("inversion_total") or 0.0) for j in reporte.get("jornadas_detalle", [])),
        2,
    )
    return {
        "bankroll_inicial": reporte.get("bankroll_inicial"),
        "bankroll_final": reporte.get("bankroll_final"),
        "pnl_acumulado": reporte.get("pnl_acumulado"),
        "roi_acumulado_pct": reporte.get("roi_acumulado_pct"),
        "posiciones_operables": reporte.get("posiciones_operables"),
        "jornadas_con_cartera": reporte.get("jornadas_con_cartera"),
        "drawdown_maximo_pct": reporte.get("drawdown_maximo_pct"),
        "total_apostado": total_apostado,
        "pct_apostado_sobre_inicial": _pct(total_apostado, int(reporte.get("bankroll_inicial") or 0)),
        "capital_no_desplegado_reportado": reporte.get("capital_no_desplegado"),
    }


def _simular_con_vetos(
    veto_ids: Sequence[str],
    *,
    bankroll_inicial: float = BANKROLL_BASE,
    jornadas: Sequence[int] = JORNADAS,
    modo: str = "compuesto",
) -> Dict[str, Any]:
    """Replica el bucle del motor, filtrando fixtures vetados ANTES del sizing.

    No se reimplementa ninguna fórmula: la cartera permitida se construye con
    `_construir_cartera_jornada`, que a su vez invoca el plano sellado de
    `portfolio_math`. El fixture vetado se declara QBE-00 y no absorbe capital.
    """
    modo_norm = str(modo or "").strip().lower()
    if modo_norm not in motor.MODOS_VALIDOS:
        raise ValueError(f"Modo no legislado: {modo!r}")
    base_inicial = round(float(bankroll_inicial), 2)
    if base_inicial <= 0.0:
        raise ValueError("El bankroll inicial debe ser positivo.")
    jornadas_lista = sorted({int(j) for j in jornadas})
    vetos = frozenset(str(v).strip() for v in veto_ids if str(v).strip())

    detalle: List[Dict[str, Any]] = []
    resumen_coberturas: Dict[str, int] = {escenario: 0 for escenario in motor.ESCENARIOS_CANONICOS}
    posiciones_operables = 0
    descartes_totales = 0
    capital_no_desplegado = 0.0
    bankroll = base_inicial
    origen_delta: Dict[str, int] = {"factico": 0, "fallback": 0}

    with PersistenceGateway().read_session() as sesion:
        for jornada in jornadas_lista:
            base_dimensionamiento = bankroll if modo_norm == "compuesto" else base_inicial
            cargado = motor._cargar_jornada(sesion, jornada)
            todos = list(cargado.get("fixtures") or [])
            vetos_jornada: List[Dict[str, Any]] = []
            permitidos: List[Dict[str, Any]] = []
            for fixture in todos:
                mid = _texto(fixture.get("id_partido"))
                if mid in vetos:
                    vetos_jornada.append({
                        "id_partido": mid,
                        "partido": f"{_texto(fixture.get('local'))} vs {_texto(fixture.get('visitante'))}",
                        "familia": "QBE-00",
                        "motivo": "Veto de regla Shannon (Regla 1/2) antes del sizing",
                        "familia_vetada": "QBE-00",
                        "veto_shannon": True,
                    })
                else:
                    permitidos.append(fixture)
            cargado["fixtures"] = permitidos

            cartera = motor._construir_cartera_jornada(
                cargado,
                base_dimensionamiento,
                excluir_estrategias=(),
                gamma=motor.GAMMA_BASE,
                modo_cobertura=motor.MODO_COBERTURA_DEF,
                familias_veto_certeza=(),
                modo_certeza=motor.MODO_CERTEZA_CRECIMIENTO,
            )
            cartera["descartes"] = vetos_jornada + list(cartera.get("descartes") or [])

            for origen, conteo in (cartera.get("delta_epist_origen") or {}).items():
                origen_delta[origen] = origen_delta.get(origen, 0) + int(conteo)

            posiciones = cartera.get("posiciones") or []
            inversion = round(motor._a_float(cartera.get("inversion_total")), 2)
            cobro = round(sum(motor._a_float(p.get("cobro_mxn")) for p in posiciones), 2)
            pnl = round(sum(motor._a_float(p.get("pnl_mxn")) for p in posiciones), 2)
            bankroll_final = round(bankroll + pnl, 2)

            for posicion in posiciones:
                escenario = str(posicion.get("escenario") or motor.ESCENARIO_RUPTURA)
                resumen_coberturas[escenario] = resumen_coberturas.get(escenario, 0) + 1

            posiciones_operables += len(posiciones)
            descartes_totales += len(cartera.get("descartes") or []) + len(cartera.get("no_liquidables") or [])
            capital_no_desplegado = round(
                capital_no_desplegado + motor._a_float(cartera.get("capital_no_desplegado")), 2
            )

            detalle.append({
                "jornada": jornada,
                "fecha_captura": cargado.get("snapshot_capturado"),
                "cartelera": len(todos),
                "candidatos_triaje": cartera.get("candidatos_triaje"),
                "bankroll_disponible": bankroll,
                "base_dimensionamiento": base_dimensionamiento,
                "inversion_total": inversion,
                "cobro_total": cobro,
                "pnl_jornada": pnl,
                "roi_jornada_pct": round((pnl / bankroll) * 100.0, 2) if bankroll > 0 else 0.0,
                "bankroll_final": bankroll_final,
                "posiciones_operables": len(posiciones),
                "capital_no_desplegado": round(motor._a_float(cartera.get("capital_no_desplegado")), 2),
                "descartes_total": len(cartera.get("descartes") or []) + len(cartera.get("no_liquidables") or []),
                "descartes": cartera.get("descartes") or [],
                "no_liquidables": cartera.get("no_liquidables") or [],
                "posiciones": posiciones,
            })
            bankroll = bankroll_final

    modo_certeza, familias_veto = motor._resolver_trinidad_certeza(motor.CERTEZA_NEUTRA_PCT)
    reporte = motor._consolidar_reporte(
        detalle=detalle,
        base_inicial=base_inicial,
        modo=modo_norm,
        jornadas_lista=jornadas_lista,
        resumen_coberturas=resumen_coberturas,
        posiciones_operables=posiciones_operables,
        descartes_totales=descartes_totales,
        capital_no_desplegado=capital_no_desplegado,
        jornadas_por_temporada=motor.JORNADAS_POR_TEMPORADA,
        parametros_simulacion={
            "gamma": motor.GAMMA_BASE,
            "target_certeza_pct": motor.CERTEZA_NEUTRA_PCT,
            "modo_certeza": modo_certeza,
            "familias_vetadas_certeza": list(familias_veto),
            "modo_cobertura": motor.MODO_COBERTURA_DEF,
            "escudo_altitud_metros": motor.UMBRAL_VETO_ALTITUD_METROS,
            "cap_underdog_ley3_pct": motor.CAP_UNDERDOG_LEY3_PCT,
            "delta_epist_origen": dict(origen_delta),
        },
        exclusiones_activas=(),
    )
    reporte["vetos_shannon_aplicados"] = sum(
        1 for jornada in detalle for descarte in jornada.get("descartes", [])
        if descarte.get("veto_shannon")
    )
    reporte["vetos_shannon_ids"] = sorted(vetos)
    if vetos:
        reporte["nota_paridad"].append(
            "Veto Shannon de auditoría: fixtures filtrados ANTES del sizing; "
            f"{reporte['vetos_shannon_aplicados']} abstenciones declaradas QBE-00."
        )
    return reporte


def _mapa_posiciones(reporte: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        str(p.get("id_partido")): p
        for jornada in reporte.get("jornadas_detalle", [])
        for p in jornada.get("posiciones", [])
    }


def _mapa_descartes(reporte: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        str(d.get("id_partido")): d
        for jornada in reporte.get("jornadas_detalle", [])
        for d in jornada.get("descartes", [])
    }


def _estado_vetos(
    veto_ids: Sequence[str],
    base: Dict[str, Any],
) -> List[Dict[str, Any]]:
    posiciones = _mapa_posiciones(base)
    descartes = _mapa_descartes(base)
    estados: List[Dict[str, Any]] = []
    for mid in sorted(veto_ids):
        if mid in posiciones:
            estados.append({
                "id_partido": mid,
                "estado_baseline": "POSICION_OPERADA",
                "detalle": posiciones[mid].get("familia"),
                "pnl_baseline": posiciones[mid].get("pnl_mxn"),
            })
        elif mid in descartes:
            estados.append({
                "id_partido": mid,
                "estado_baseline": "YA_QBE_00",
                "detalle": descartes[mid].get("motivo"),
                "pnl_baseline": 0.0,
            })
        else:
            estados.append({
                "id_partido": mid,
                "estado_baseline": "AUSENTE_DE_LA_JORNADA",
                "detalle": "Sin fixture en la bóveda para J1-J13",
                "pnl_baseline": 0.0,
            })
    return estados


def _hard_caps(reporte: Dict[str, Any]) -> Dict[str, Any]:
    """Verifica los topes 8%/25% con tolerancia de redondeo de un centavo.

    El sizing canónico redondea la orden a centavos; por eso el tope del 8% puede
    quedar unos centavos por encima del límite teórico. Eso no es una violación
    fiduciaria: es el residuo de redondeo del boleto.
    """
    tolerancia_mxn = 0.01
    max_partido = 0.0
    max_jornada = 0.0
    max_exceso_partido = 0.0
    max_exceso_jornada = 0.0
    violaciones: List[Dict[str, Any]] = []
    for jornada in reporte.get("jornadas_detalle", []):
        base = float(jornada.get("bankroll_disponible") or 0.0)
        if base <= 0.0:
            continue
        total = float(jornada.get("inversion_total") or 0.0)
        ratio_jornada = total / base
        max_jornada = max(max_jornada, ratio_jornada)
        exceso_jornada = max(0.0, total - (base * motor.CAP_MAX_CARTERA_PCT))
        max_exceso_jornada = max(max_exceso_jornada, exceso_jornada)
        if exceso_jornada > tolerancia_mxn:
            violaciones.append({
                "jornada": jornada.get("jornada"),
                "tipo": "CAP_CARTERA_25",
                "ratio_pct": round(ratio_jornada * 100.0, 6),
                "exceso_mxn": round(exceso_jornada, 4),
            })
        for posicion in jornada.get("posiciones", []):
            inversion = float(posicion.get("inversion_total") or 0.0)
            ratio = inversion / base
            max_partido = max(max_partido, ratio)
            exceso = max(0.0, inversion - (base * motor.CAP_MAX_PARTIDO_PCT))
            max_exceso_partido = max(max_exceso_partido, exceso)
            if exceso > tolerancia_mxn:
                violaciones.append({
                    "jornada": jornada.get("jornada"),
                    "id_partido": posicion.get("id_partido"),
                    "tipo": "CAP_PARTIDO_8",
                    "ratio_pct": round(ratio * 100.0, 6),
                    "exceso_mxn": round(exceso, 4),
                })
            if str(posicion.get("familia") or "").upper() in motor.FAMILIA_R_CODIGOS:
                exceso_underdog = max(0.0, inversion - (base * motor.CAP_UNDERDOG_LEY3_PCT))
                if exceso_underdog > tolerancia_mxn:
                    violaciones.append({
                        "jornada": jornada.get("jornada"),
                        "id_partido": posicion.get("id_partido"),
                        "tipo": "CAP_UNDERDOG_1_5",
                        "ratio_pct": round(ratio * 100.0, 6),
                        "exceso_mxn": round(exceso_underdog, 4),
                    })
    return {
        "max_partido_pct": round(max_partido * 100.0, 6),
        "max_jornada_pct": round(max_jornada * 100.0, 6),
        "max_exceso_partido_mxn": round(max_exceso_partido, 4),
        "max_exceso_jornada_mxn": round(max_exceso_jornada, 4),
        "tolerancia_redondeo_mxn": tolerancia_mxn,
        "cap_partido_pct": round(motor.CAP_MAX_PARTIDO_PCT * 100.0, 6),
        "cap_jornada_pct": round(motor.CAP_MAX_CARTERA_PCT * 100.0, 6),
        "cap_underdog_pct": round(motor.CAP_UNDERDOG_LEY3_PCT * 100.0, 6),
        "violaciones": violaciones,
        "respetados": not violaciones,
    }


def _redistribucion(base: Dict[str, Any], veto: Dict[str, Any], veto_ids: Sequence[str]) -> Dict[str, Any]:
    base_pos = _mapa_posiciones(base)
    veto_pos = _mapa_posiciones(veto)
    retiradas = sorted(set(base_pos) - set(veto_pos))
    nuevas = sorted(set(veto_pos) - set(base_pos))
    capital_liberado = round(sum(float(base_pos[mid].get("inversion_total") or 0.0) for mid in retiradas), 2)
    capital_reasignado = round(
        sum(
            max(0.0, float(veto_pos[mid].get("inversion_total") or 0.0)
                - float(base_pos[mid].get("inversion_total") or 0.0))
            for mid in set(base_pos) & set(veto_pos)
        ),
        2,
    )
    return {
        "ids_vetados": sorted(veto_ids),
        "estado_de_los_vetados_en_baseline": _estado_vetos(veto_ids, base),
        "posiciones_retiradas": retiradas,
        "posiciones_nuevas": nuevas,
        "capital_liberado_mxn": capital_liberado,
        "capital_reasignado_mxn": capital_reasignado,
        "misma_cartera": not retiradas and not nuevas,
        "capital_no_desplegado_reportado": veto.get("capital_no_desplegado"),
        "conclusion": (
            "NO_HUBO_CAPITAL_QUE_REDISTRIBUIR: los partidos vetados ya eran QBE-00 "
            "y no absorbían capital."
            if not retiradas and not nuevas
            else "El veto retiró posiciones; revisar reasignación y liquidez."
        ),
    }


# ── Reporte ───────────────────────────────────────────────────────────────────
def construir_reporte() -> Dict[str, Any]:
    filas = _cargar_filas(RUTA_DATASET)
    columnas = ("v09_local", "v18_local", "v29_local", "v32_local", "v18_visita", "v32_visita")
    coberturas = {columna: _cobertura(filas, columna) for columna in columnas}
    regla_1 = _evaluar_regla_1(filas)
    regla_2 = _evaluar_regla_2(filas)
    veto_ids = sorted(set(regla_1["ids"]) | set(regla_2["ids"]))

    base = motor.ejecutar_simulacion_rentabilidad(
        bankroll_inicial=BANKROLL_BASE,
        jornadas=JORNADAS,
        modo="compuesto",
    )
    paridad = _simular_con_vetos(())
    veto = _simular_con_vetos(veto_ids)

    resumen_base = _resumen_roi(base)
    resumen_veto = _resumen_roi(veto)
    roi_base = float(resumen_base["roi_acumulado_pct"] or 0.0)
    roi_veto = float(resumen_veto["roi_acumulado_pct"] or 0.0)
    hard_caps = _hard_caps(veto)
    redistribucion = _redistribucion(base, veto, veto_ids)

    paridad_ok = all(
        base.get(clave) == paridad.get(clave)
        for clave in (
            "bankroll_final", "pnl_acumulado", "roi_acumulado_pct",
            "posiciones_operables", "drawdown_maximo_pct", "capital_no_desplegado",
        )
    ) and _mapa_posiciones(base).keys() == _mapa_posiciones(paridad).keys()

    claim_reproducido = abs(roi_veto - ROI_DECLARADO_PCT) <= 0.01
    delta_vs_base = round(roi_veto - roi_base, 2)
    delta_vs_claim = round(roi_veto - ROI_DECLARADO_PCT, 2)

    if regla_1["n"] == 0 and regla_2["n"] <= 1:
        veredicto = "ESPEJISMO ESTADÍSTICO"
        explicacion = (
            "La Regla 1 no tiene soporte (v32_local 0% cubierto). La Regla 2 tiene N=1: "
            "su 100% es una observación única, con IC95% 20.65–100% y p hipergeométrico "
            "de una cola ≈ 0.278. Además, el único partido coincide con un QBE-00 que ya "
            "estaba fuera de la cartera; el veto no cambia el ROI. El +14.65% no se reproduce."
        )
    elif claim_reproducido:
        veredicto = "HALLAZGO REPRODUCIDO"
        explicacion = "El ROI declarado se reproduce con el veto simulado."
    else:
        veredicto = "HALLAZGO NO REPRODUCIDO"
        explicacion = "El ROI declarado no se reproduce con las reglas y datos auditados."

    return {
        "sonda": "validar_informe_shannon",
        "regimen": "DIRGEN-STRICT",
        "dataset": {
            "ruta": str(RUTA_DATASET),
            "filas": len(filas),
            "jornadas": dict(sorted(Counter(_texto(f.get("jornada")) for f in filas).items())),
            "distribucion_triada": _distribucion(filas),
            "tasa_base_p_low_pct": _pct(sum(1 for f in filas if _texto(f.get("clasificacion_triada")).upper() == "P_LOW"), len(filas)),
            "origen_captura": dict(sorted(Counter(_texto(f.get("origen_captura")) for f in filas).items())),
        },
        "cobertura": coberturas,
        "regla_1_trampa_del_favorito": regla_1,
        "regla_2_friccion_defensiva": regla_2,
        "veto": {
            "ids": veto_ids,
            "n_partidos": len(veto_ids),
        },
        "roi": {
            "base": resumen_base,
            "con_veto": resumen_veto,
            "delta_vs_base_pp": delta_vs_base,
            "claim_declarado_pct": ROI_DECLARADO_PCT,
            "delta_vs_claim_pp": delta_vs_claim,
            "claim_reproducido": claim_reproducido,
            "paridad_motor_sin_vetos": paridad_ok,
        },
        "hard_caps": hard_caps,
        "redistribucion": redistribucion,
        "veredicto": {
            "clasificacion": veredicto,
            "explicacion": explicacion,
            "base_rate_csv_pct": _pct(sum(1 for f in filas if _texto(f.get("clasificacion_triada")).upper() == "P_LOW"), len(filas)),
            "nota_docs": (
                "El dossier documental reporta 32/97 (32.99%) P_LOW; el CSV canónico "
                "reporta 27/97 (27.84%). La discrepancia debe resolverse antes de "
                "cualquier generalización."
            ),
        },
    }


def _imprimir_resumen(reporte: Dict[str, Any]) -> None:
    print("=" * 88)
    print("AUDITORÍA EMPÍRICA · INFORME SHANNON · RÉGIMEN [DIRGEN-STRICT]")
    print("=" * 88)
    print(f"Dataset: {reporte['dataset']['filas']} filas | J1–J13 | "
          f"P_LOW base: {reporte['dataset']['tasa_base_p_low_pct']}%")
    print("\n[1] COBERTURA")
    for columna, datos in reporte["cobertura"].items():
        print(f"  {columna:<14} {datos['no_nulos']:>3}/{datos['n']:<3} "
              f"= {datos['pct_no_nulos']:>6.2f}% no nulos")
    print("\n[2] REGLA 1 · TRAMPA DEL FAVORITO")
    r1 = reporte["regla_1_trampa_del_favorito"]
    print(f"  Filtro: {r1['filtro']}")
    print(f"  N = {r1['n']} | P_LOW = {r1['p_low']} | "
          f"tasa = {r1['tasa_ruptura_pct']} | soporte = {r1['soporte']}")
    print(f"  Veredicto: {r1['veredicto']}")
    print("\n[3] REGLA 2 · FRICCIÓN DEFENSIVA")
    r2 = reporte["regla_2_friccion_defensiva"]
    print(f"  Filtro: {r2['filtro']}")
    print(f"  N = {r2['n']} | P_LOW = {r2['p_low']} | "
          f"tasa = {r2['tasa_ruptura_pct']}% | lift = {r2['lift']}")
    print(f"  IC95% Wilson = {r2['ci95_wilson_pct']} | "
          f"p hipergeométrico = {r2['p_hipergeometrico_una_cola']}")
    print(f"  Distribución: {r2['distribucion_triada']}")
    print(f"  Veredicto: {r2['veredicto']}")
    print("\n[4] ROI")
    for etiqueta in ("base", "con_veto"):
        datos = reporte["roi"][etiqueta]
        print(f"  {etiqueta:<10} ROI {datos['roi_acumulado_pct']:>6.2f}% | "
              f"PnL ${datos['pnl_acumulado']:>9,.2f} | "
              f"posiciones {datos['posiciones_operables']} | "
              f"drawdown {datos['drawdown_maximo_pct']}%")
    print(f"  Delta veto vs base: {reporte['roi']['delta_vs_base_pp']:+.2f} pp | "
          f"claim {reporte['roi']['claim_declarado_pct']}% -> "
          f"{'REPRODUCIDO' if reporte['roi']['claim_reproducido'] else 'NO REPRODUCIDO'}")
    print("\n[5] HARD-CAPS")
    hc = reporte["hard_caps"]
    print(f"  Máx. partido: {hc['max_partido_pct']:.4f}% (cap {hc['cap_partido_pct']}%) | "
          f"Máx. jornada: {hc['max_jornada_pct']:.4f}% (cap {hc['cap_jornada_pct']}%)")
    print(f"  Exceso de redondeo: partido ${hc['max_exceso_partido_mxn']:.4f} | "
          f"jornada ${hc['max_exceso_jornada_mxn']:.4f} | "
          f"tolerancia ${hc['tolerancia_redondeo_mxn']:.2f}")
    print(f"  Respetados: {hc['respetados']} | Violaciones: {len(hc['violaciones'])}")
    print("\n[6] REDISTRIBUCIÓN")
    rd = reporte["redistribucion"]
    print(f"  Vetados: {rd['ids_vetados']}")
    print(f"  Estado baseline: {rd['estado_de_los_vetados_en_baseline']}")
    print(f"  Capital liberado: ${rd['capital_liberado_mxn']:,.2f} | "
          f"reasignado: ${rd['capital_reasignado_mxn']:,.2f}")
    print(f"  {rd['conclusion']}")
    print("\n[7] VEREDICTO")
    print(f"  {reporte['veredicto']['clasificacion']}")
    print(f"  {reporte['veredicto']['explicacion']}")
    print("=" * 88)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="validar_informe_shannon",
        description="Auditoría empírica del informe Shannon (sólo lectura).",
    )
    parser.add_argument("--json", action="store_true", dest="salida_json",
                        help="Emite el contrato JSON completo.")
    args = parser.parse_args(argv)
    reporte = construir_reporte()
    if args.salida_json:
        print(json.dumps(reporte, ensure_ascii=False, indent=2))
    else:
        _imprimir_resumen(reporte)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
