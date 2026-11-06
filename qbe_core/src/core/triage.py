# Q-BE Casino Deportes — Triage Engine (src/core/triage.py)
"""
[LN-QBE-005] Triaje Determinista de Cuotas 1X2.
[BIZ-LOGIC] [ARCH-PILLAR]
Filtro previo que evalúa las 6 vías de viabilidad económica sobre momios decimales
antes de invocar la extracción fáctica o el análisis estocástico profundo.
"""

from typing import List, Dict, Any, Tuple, Optional
from collections.abc import Mapping
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
    """[LN-QBE-060-C] Veto QBE-00 por ineficiencia o sobreasedio, o `None` si el club está sano.

    * R1 · INEFICACIA_OFENSIVA: xG alto (V06) pero big chances falladas (V09) e indisciplina
      (V25) elevadas ⇒ favorito inflado por volumen sin conversión.
    * R2 · SOBREASEDIO_DEFENSIVO: SoTA muy alto (V13) con forma 5P en caída (V31) ⇒ defensa
      estructuralmente frágil.

    [E-50.10] El umbral viaja como parámetro: aquí no hay números mágicos locales.
    """
    def _alto(var: str) -> bool:
        """[LN-QBE-060-C] Variable en o por encima del percentil 75."""
        return float(vector.get(var, 0.0)) >= float(p75.get(var, math.inf))

    def _muy_alto(var: str) -> bool:
        """[LN-QBE-060-C] Variable en o por encima del percentil 90."""
        return float(vector.get(var, 0.0)) >= float(p90.get(var, math.inf))

    def _bajo(var: str) -> bool:
        """[LN-QBE-060-C] Variable en o por debajo del percentil 25."""
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


# ═══════════════════════════════════════════════════════════════════════════════════════
# [LN-QBE-060-B] / §27 — ORQUESTADOR DE MUNDO 2 (Paso 0 · Sistema Inmune Fiduciario)
#
# El Mundo 1 calcula P' y el consenso de mercado completos e independientes. Al transitar
# al Mundo 2, el Paso 0 evalúa el Sistema Inmune ANTES de leer una sola cuota: si dispara,
# el partido colapsa a QBE-00 con $0.00 MXN y traza de ambas distribuciones. Los Pasos 1
# (cuarentena fiduciaria) y 2 (selección de cobertura) se delegan a `[LN-QBE-060-B]`
# (`triaje_determinista_9_estrategias`): una sola fuente de verdad para la cascada.
# ═══════════════════════════════════════════════════════════════════════════════════════

TOLERANCIA_SIMPLEX_MUNDO2: float = 1e-9


def _validar_simplex_mundo2(nombre: str, distribucion: Any) -> Dict[str, float]:
    """[LN-QBE-060-B] Aduana: la distribución debe llegar completa y sumar 1.0 ± 1e-9."""
    if not isinstance(distribucion, Mapping):
        raise ValueError(
            f"{nombre} debe ser un mapping de probabilidades; se recibió {type(distribucion).__name__}."
        )
    faltantes = [
        clave for clave in ("p_local", "p_empate", "p_visitante") if clave not in distribucion
    ]
    if faltantes:
        raise ValueError(f"{nombre} incompleta: faltan {', '.join(faltantes)}.")
    valores: Dict[str, float] = {}
    for clave in ("p_local", "p_empate", "p_visitante"):
        crudo = distribucion[clave]
        if isinstance(crudo, bool) or not isinstance(crudo, (int, float)):
            raise ValueError(f"{nombre}.{clave} no numérica: {crudo!r}.")
        valor = float(crudo)
        if not math.isfinite(valor) or not (0.0 <= valor <= 1.0):
            raise ValueError(f"{nombre}.{clave} fuera de [0, 1]: {crudo!r}.")
        valores[clave] = valor
    total = math.fsum(valores.values())
    if abs(total - 1.0) > TOLERANCIA_SIMPLEX_MUNDO2:
        raise ValueError(
            f"{nombre} no es un símplex: Σ = {total!r} ≠ 1.0 "
            f"(tolerancia {TOLERANCIA_SIMPLEX_MUNDO2:g})."
        )
    return valores


def _validar_percentiles_mundo2(percentiles: Any) -> Dict[str, Mapping]:
    """[LN-QBE-060-B] Aduana: los tres bloques de percentiles del Sistema Inmune."""
    if not isinstance(percentiles, Mapping):
        raise ValueError(
            f"percentiles debe ser un mapping; se recibió {type(percentiles).__name__}."
        )
    salida: Dict[str, Mapping] = {}
    for clave in ("p25", "p75", "p90"):
        if clave not in percentiles:
            raise ValueError(f"percentiles incompletos: falta el bloque '{clave}'.")
        bloque = percentiles[clave]
        if not isinstance(bloque, Mapping):
            raise ValueError(f"percentiles['{clave}'] debe ser un mapping; se recibió {type(bloque).__name__}.")
        salida[clave] = bloque
    return salida


def _validar_vector_mundo2(vector: Any) -> Dict[str, float]:
    """[LN-QBE-060-B] Aduana: variables causales numéricas y finitas."""
    if not isinstance(vector, Mapping):
        raise ValueError(f"vector debe ser un mapping; se recibió {type(vector).__name__}.")
    salida: Dict[str, float] = {}
    for clave, crudo in vector.items():
        if isinstance(crudo, bool) or not isinstance(crudo, (int, float)):
            raise ValueError(f"vector['{clave}'] no numérica: {crudo!r}.")
        valor = float(crudo)
        if not math.isfinite(valor):
            raise ValueError(f"vector['{clave}'] no finita: {crudo!r}.")
        salida[clave] = valor
    return salida


def triaje_financiero_mundo2(
    match_id: str,
    distribucion_soberana: Mapping,
    consenso_mercado: Mapping,
    cuotas: Mapping,
    vector: Mapping,
    percentiles: Mapping,
    gamma: float = 0.67,
) -> Dict[str, Any]:
    """[LN-QBE-060-B] Orquestador de Mundo 2 con compuerta de Paso 0 (Sistema Inmune).

    Secuencia obligatoria: (0) Sistema Inmune —sin leer cuotas—; (1) cuarentena
    fiduciaria (``not es_operable`` o Δ_epist > τ_disp = 0.12) y (2) selección de
    cobertura, ambas delegadas a `triaje_determinista_9_estrategias`. Un veto devuelve
    ``codigo="QBE-00"``, ``capital_mxn=0.0``, ``boletos=[]``, ``cuotas_evaluadas=False``
    y la traza con ambas distribuciones. En un veredicto operable ``capital_mxn`` es
    ``None``: el triaje no dimensiona capital (competencia de ``[LN-QBE-070]``).
    """
    if not isinstance(match_id, str) or not match_id.strip():
        raise ValueError(f"match_id inválido: {match_id!r}.")
    _validar_simplex_mundo2("distribucion_soberana", distribucion_soberana)
    _validar_simplex_mundo2("consenso_mercado", consenso_mercado)
    bloques = _validar_percentiles_mundo2(percentiles)
    vector_valido = _validar_vector_mundo2(vector)

    traza: Dict[str, Any] = {
        "p_simplex": dict(distribucion_soberana),
        "p_consenso": dict(consenso_mercado),
        "vector": dict(vector),
        "percentiles": {clave: dict(bloque) for clave, bloque in bloques.items()},
    }

    # ── PASO 0 · SISTEMA INMUNE FIDUCIARIO (antes de toda lectura de cuotas) ──
    veto = veto_inmunidad_fiduciaria(vector_valido, bloques["p25"], bloques["p75"], bloques["p90"])
    if veto is not None:
        return {
            "codigo": "QBE-00",
            "paso_0": True,
            "arquetipo_veto": veto["arquetipo_veto"],
            "motivo_codigo": veto["arquetipo_veto"],
            "motivo": veto["motivo"],
            "capital_mxn": 0.0,
            "cuotas_evaluadas": False,
            "boletos": [],
            "traza": traza,
        }

    # ── PASOS 1-2 · CUARENTENA Y COBERTURA (cascada sellada `[LN-QBE-060-B]`) ──
    from src.core.contracts.portfolio_math import triaje_determinista_9_estrategias

    payload = {
        "p_local": float(distribucion_soberana["p_local"]),
        "p_empate": float(distribucion_soberana["p_empate"]),
        "p_visitante": float(distribucion_soberana["p_visitante"]),
        # Defaults espejo de la cascada sellada: la ausencia de la bandera no es
        # evidencia de inoperancia; el llamador ya pasó por la aduana S(I).
        "es_operable": bool(distribucion_soberana.get("es_operable", True)),
        "delta_epist": float(distribucion_soberana.get("delta_epist", 0.0)),
    }
    veredicto = triaje_determinista_9_estrategias(payload, cuotas, gamma=float(gamma))
    return {
        **veredicto,
        "paso_0": False,
        "arquetipo_veto": None,
        "motivo_codigo": veredicto["codigo"],
        "motivo": veredicto.get("nombre", ""),
        "capital_mxn": 0.0 if veredicto["codigo"] == "QBE-00" else None,
        "cuotas_evaluadas": True,
        "boletos": [],
        "traza": traza,
    }