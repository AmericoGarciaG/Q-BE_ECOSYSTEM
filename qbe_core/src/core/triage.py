# Q-BE Casino Deportes — Triage Engine (src/core/triage.py)
"""
[LN-QBE-005] Triaje Determinista de Cuotas 1X2.
[BIZ-LOGIC] [ARCH-PILLAR]
Filtro previo que evalúa las 6 vías de viabilidad económica sobre momios decimales
antes de invocar la extracción fáctica o el análisis estocástico profundo.
"""

from typing import List, Dict, Any, Tuple, Optional
import math


# [LN-QBE-060-B] VÍA B — formalización de paridad canónica ([LN-QBE-139]/[LN-QBE-140]).
def evaluar_viabilidad_cuotas(
    momio_l: float,
    momio_e: float,
    momio_v: float,
    pago_anticipado: bool = True
) -> Tuple[bool, str]:
    """
    Evalúa si una terna de cuotas 1X2 ofrece margen matemático en alguna de las 6 vías Q-BE.
    """
    if momio_l <= 1.0 or momio_e <= 1.0 or momio_v <= 1.0:
        return False, "Momios inválidos (menores o iguales a 1.0)"

    momio_fav = min(momio_l, momio_v)
    momio_und = max(momio_l, momio_v)

    # 1. Cálculos de Rentabilidad Teórica de Coberturas
    roi_h1 = ((1.0 - (1.0 / momio_e)) * momio_fav) - 1.0
    roi_h2 = ((1.0 - (1.0 / momio_fav)) * momio_e) - 1.0
    roi_r1 = ((1.0 - (1.0 / momio_e)) * momio_und) - 1.0

    denom_x2 = (1.0 / momio_und) + (1.0 / momio_e)
    momio_x2 = 1.0 / denom_x2 if denom_x2 > 0 else 0.0

    # 2. Evaluación de las 6 Vías de Aprobación
    # Vía 1: Favorito con Seguro H1 / D1
    if roi_h1 >= 0.05 and (1.0 / momio_und) < 0.35:
        return True, "Candidato Favorito H1 / D1"

    # Vía 2: Empate de Valor H2 / H2+
    if roi_h2 >= 0.15 and (1.0 / momio_und) < 0.35:
        return True, "Candidato Empate H2 / H2+"

    # Vía 3: Super-Favorito Directo D1 / D1+
    if momio_fav <= 1.45 and (1.0 / momio_und) <= 0.20:
        return True, "Candidato Super-Favorito D1 / D1+"

    # Vía 4: Inverso Asimétrico R1
    if roi_r1 >= 1.00:
        return True, "Candidato Inverso R1"

    # Vía 5: Doble Oportunidad Sintética R2
    if momio_x2 >= 1.60:
        return True, "Candidato Inverso R2"

    # Vía 6: Satélite Moonshot Asimétrico
    if momio_und >= 4.50 and pago_anticipado:
        return True, "Candidato Satélite Moonshot"

    return False, "Volado sin margen de cobertura bilateral (+EV nulo en cuotas)"


# [LN-QBE-060-B] VÍA B — formalización de paridad canónica ([LN-QBE-139]/[LN-QBE-140]).
def procesar_triaje_partidos(partidos_raw: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Procesa una lista de partidos crudos y separa los candidatos aprobados de los descartados,
    preservando fielmente la identidad del torneo y metadatos de origen.
    """
    aprobados = []
    descartados = []

    for p in partidos_raw:
        momios = p.get("momios", {})
        if isinstance(momios, dict) and "pago_anticipado" in momios and isinstance(momios["pago_anticipado"], dict):
            pa_dict = momios["pago_anticipado"]
            l = float(pa_dict.get("L", 0.0))
            e = float(pa_dict.get("E", 0.0))
            v = float(pa_dict.get("V", 0.0))
            pa_disponible = bool(pa_dict.get("disponible", True))
        elif isinstance(momios, dict):
            l = float(momios.get("L", 0.0))
            e = float(momios.get("E", 0.0))
            v = float(momios.get("V", 0.0))
            pa_disponible = bool(p.get("pago_anticipado", True))
        else:
            l, e, v, pa_disponible = 0.0, 0.0, 0.0, False

        viable, motivo = evaluar_viabilidad_cuotas(l, e, v, pa_disponible)

        id_p = p.get("id_partido", "")
        local_name = p.get("local", "")
        vis_name = p.get("visitante", "")
        nombre_partido = f"{local_name} vs {vis_name}".strip() if (local_name or vis_name) else id_p

        item = dict(p)
        item["momios"] = {"L": l, "E": e, "V": v}
        item["pago_anticipado"] = pa_disponible

        if viable:
            item["triaje_motivo"] = motivo
            aprobados.append(item)
        else:
            descartados.append({
                "id_partido": id_p,
                "partido": nombre_partido,
                "motivo": motivo,
                "motivo_titulo": "TRIAGE_COIN_FLIP",
                "motivo_codigo": "TRIAGE_COIN_FLIP",
                "momios": {"L": l, "E": e, "V": v},
                "liga_torneo": p.get("liga_torneo", "Liga MX"),
                "explicacion_didactica": (
                    f"El partido {nombre_partido} presenta cuotas ({l:.2f} / {e:.2f} / {v:.2f}) "
                    f"que configuran un volado plano sin ineficiencia explotable (+EV nulo). "
                    f"Descartado preventivamente en el triaje sin consumo de inferencia."
                )
            })

    return {"aprobados": aprobados, "descartados": descartados}


# ═══════════════════════════════════════════════════════════════════════════════════════
# [E-50.10][FASE 6] CAPA 4 — SISTEMA INMUNE FIDUCIARIO (reglas sobre variables residuales)
#
# Consume las variables que la súper-señal NO usa (V01-V05, V08-V11, V13-V28, V31-V32) y emite
# un veto QBE-00 cuando el diagnóstico de la Capa 1 es fiduciariamente frágil. Los percentiles
# (p25/p75/p90) los calcula el laboratorio sobre la muestra histórica; aquí NO hay números
# mágicos locales: el umbral viaja como parámetro.
# ═══════════════════════════════════════════════════════════════════════════════════════
def veto_inmunidad_fiduciaria(
    vector: Dict[str, Any],
    p25: Dict[str, float],
    p75: Dict[str, float],
    p90: Dict[str, float],
) -> Optional[Dict[str, Any]]:
    """[E-50.10] Veto QBE-00 por ineficiencia o sobreasedio, o `None` si el club está sano.

    * R1 · INEFICACIA_OFENSIVA: xG alto (V06) pero big chances falladas (V09) e indisciplina
      (V25) elevadas ⇒ favorito inflado por volumen sin conversión.
    * R2 · SOBREASEDIO_DEFENSIVO: SoTA muy alto (V13) con forma 5P en caída (V31) ⇒ defensa
      estructuralmente frágil.
    """
    def _alto(var: str) -> bool:
        return float(vector.get(var, 0.0)) >= float(p75.get(var, math.inf))

    def _muy_alto(var: str) -> bool:
        return float(vector.get(var, 0.0)) >= float(p90.get(var, math.inf))

    def _bajo(var: str) -> bool:
        return float(vector.get(var, 0.0)) <= float(p25.get(var, -math.inf))

    if _alto("V06") and _muy_alto("V09") and _alto("V25"):
        return {
            "codigo": "QBE-00",
            "nombre": "Veto Inmune: Ineficiencia Ofensiva",
            "arquetipo_veto": "INEFICACIA_OFENSIVA",
            "alpha": 0.0,
            "pa": False,
            "motivo": (
                "Favorito por xG (V06) con ineficiencia (V09 ≥ p90) e indisciplina (V25 ≥ p75) elevadas."
            ),
        }
    if _muy_alto("V13") and _bajo("V31"):
        return {
            "codigo": "QBE-00",
            "nombre": "Veto Inmune: Sobreasedio Defensivo",
            "arquetipo_veto": "SOBREASEDIO_DEFENSIVO",
            "alpha": 0.0,
            "pa": False,
            "motivo": "Defensa bajo asedio (SoTA ≥ p90) con forma 5P en caída (V31 ≤ p25).",
        }
    return None