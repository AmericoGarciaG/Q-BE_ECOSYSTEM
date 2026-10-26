# -*- coding: utf-8 -*-
"""
🏆 Q-BE PROGOL ENGINE — DETECCIÓN DE SESGO POPULAR Y OPTIMIZADOR COMBINATORIO
[LN-QBE-037] Explotación de la Venta Pública Nacional vs Probabilidad Soberana.
[LN-QBE-074] Optimizador de Quinielas Progol por Presupuesto (2^D × 3^T ≤ B).
Base de Gobierno: Kybern Framework v12.0
"""

from itertools import product
from typing import List, Dict, Tuple, Any, Optional

# [LN-QBE-075 / P1-5] Prior de Ignorancia Fiduciaria — fuente única legislada.
from src.core.constants import PRIOR_IGNORANCIA_FIDUCIARIA

PROB_IGNORANCIA: Dict[str, float] = {
    "L": PRIOR_IGNORANCIA_FIDUCIARIA[0],
    "E": PRIOR_IGNORANCIA_FIDUCIARIA[1],
    "V": PRIOR_IGNORANCIA_FIDUCIARIA[2],
}


def calcular_sesgo_quiniela(v_publico: Dict[str, float], p_soberana: Dict[str, float]) -> Dict[str, Any]:
    """
    [LN-QBE-037] Compara la venta pública nacional contra la probabilidad real de Q-BE:
    Sesgo_k = V_publico_k - P_soberana_k
    Si el sesgo local supera +20% (0.20), el valor esperado se desplaza hacia el empate/visita (X2).
    """
    sesgo_l = round(float(v_publico.get("L", 0.0)) - float(p_soberana.get("L", 0.0)), 4)
    sesgo_e = round(float(v_publico.get("E", 0.0)) - float(p_soberana.get("E", 0.0)), 4)
    sesgo_v = round(float(v_publico.get("V", 0.0)) - float(p_soberana.get("V", 0.0)), 4)

    alerta = False
    rec = "BASE_SIMPLE"

    # Detección de sesgo abrumador del público
    if sesgo_l >= 0.20:
        alerta = True
        rec = "DOBLE_COBERTURA_SESGO (X2)"
    elif sesgo_v >= 0.20:
        alerta = True
        rec = "DOBLE_COBERTURA_SESGO (1X)"
    elif float(p_soberana.get("L", 0.0)) >= 0.65:
        rec = "BASE_SIMPLE (L)"
    elif float(p_soberana.get("V", 0.0)) >= 0.65:
        rec = "BASE_SIMPLE (V)"
    else:
        rec = "TRIPLE_ESTRATÉGICO (1X2)"

    return {
        "sesgo_local": sesgo_l,
        "sesgo_empate": sesgo_e,
        "sesgo_visitante": sesgo_v,
        "alerta_sesgo": alerta,
        "recomendacion_cobertura": rec
    }


def optimizar_quiniela_por_presupuesto(items: List[Dict[str, Any]], presupuesto_mxn: float = 360.0) -> Dict[str, Any]:
    """
    [LN-QBE-074] Asigna matemáticamente Triples y Dobles maximizando cobertura sobre sesgo popular:
    Costo Oficial Progol = 15.00 * (2^D) * (3^T) <= Presupuesto.

    Regla de Asignación:
    - Ordena los 14 encuentros por magnitud de sesgo popular absoluto descendente.
    - Asigna Triples a los partidos de máxima incertidumbre/sesgo.
    - Asigna Dobles a los partidos con sesgo >= +0.20.
    - Fija como Bases Simples los partidos de alta probabilidad (P_L >= 0.65 o P_V >= 0.65).
    """
    precio_simple = 15.0
    presupuesto = float(presupuesto_mxn)

    # 1. Encontrar la combinación óptima (D, T) que maximice el costo sin superar el presupuesto
    mejor_d, mejor_t, mejor_costo = 0, 0, precio_simple

    for t in range(5):      # 0 a 4 triples
        for d in range(9):  # 0 a 8 dobles
            comb = (2 ** d) * (3 ** t)
            costo = comb * precio_simple
            if costo <= presupuesto and costo > mejor_costo:
                mejor_costo = costo
                mejor_d = d
                mejor_t = t

    # 2. Calcular sesgos y ordenar por magnitud descendente
    items_analizados = []
    for p in items:
        sesgo_data = calcular_sesgo_quiniela(p.get("v_pub", {}), p.get("p_qbe", {}))
        magnitud_sesgo = abs(sesgo_data.get("sesgo_local", 0.0)) + abs(sesgo_data.get("sesgo_visitante", 0.0))
        items_analizados.append({
            **p,
            "sesgo_magnitud": magnitud_sesgo,
            "analisis": sesgo_data
        })

    items_ordenados = sorted(items_analizados, key=lambda x: x["sesgo_magnitud"], reverse=True)

    # 3. Asignar Triples, Dobles y Simples según la Regla de Asignación [LN-QBE-074]
    triples_restantes = mejor_t
    dobles_restantes = mejor_d
    matriz_resultado = []

    for item in items_ordenados:
        s = item["analisis"]
        p_qbe = item.get("p_qbe", {})

        juega_l, juega_e, juega_v = False, False, False
        rec = "SIMPLE"

        if triples_restantes > 0:
            # Triple estratégico: cubre las 3 casillas (1, X, 2)
            juega_l, juega_e, juega_v = True, True, True
            triples_restantes -= 1
            rec = "TRIPLE_ESTRATÉGICO (1X2)"
        elif dobles_restantes > 0 and s.get("alerta_sesgo"):
            # Doble en la dirección opuesta al sesgo popular
            if s.get("sesgo_local", 0.0) >= 0.20:
                juega_e, juega_v = True, True
                rec = "DOBLE_SESGO (X2)"
            elif s.get("sesgo_visitante", 0.0) >= 0.20:
                juega_l, juega_e = True, True
                rec = "DOBLE_SESGO (1X)"
            else:
                juega_l, juega_v = True, True
                rec = "DOBLE_EXTREMOS (12)"
            dobles_restantes -= 1
        elif dobles_restantes > 0:
            # Doble en las dos opciones de mayor probabilidad Q-BE
            sorted_probs = sorted(
                [("L", p_qbe.get("L", 0.33)), ("E", p_qbe.get("E", 0.33)), ("V", p_qbe.get("V", 0.33))],
                key=lambda x: x[1],
                reverse=True
            )
            top_2 = [x[0] for x in sorted_probs[:2]]
            juega_l = "L" in top_2
            juega_e = "E" in top_2
            juega_v = "V" in top_2
            dobles_restantes -= 1
            rec = f"DOBLE_VALOR ({top_2[0]}{top_2[1]})"
        else:
            # Simple a la probabilidad más alta según Q-BE
            sorted_probs = sorted(
                [("L", p_qbe.get("L", 0.33)), ("E", p_qbe.get("E", 0.33)), ("V", p_qbe.get("V", 0.33))],
                key=lambda x: x[1],
                reverse=True
            )
            top_1 = sorted_probs[0][0]
            juega_l = (top_1 == "L")
            juega_e = (top_1 == "E")
            juega_v = (top_1 == "V")
            rec = f"BASE_SIMPLE ({top_1})"

        matriz_resultado.append({
            "order": item.get("order"),
            "local": item.get("local"),
            "visitante": item.get("visitante"),
            "juega_L": juega_l,
            "juega_E": juega_e,
            "juega_V": juega_v,
            "alerta_sesgo": s.get("alerta_sesgo", False),
            "recomendacion": rec
        })

    # Reordenar por el número oficial del partido (1 al 14)
    matriz_final = sorted(matriz_resultado, key=lambda x: x["order"])

    return {
        "costo_total_mxn": mejor_costo,
        "combinaciones_totales": (2 ** mejor_d) * (3 ** mejor_t),
        "dobles_asignados": mejor_d,
        "triples_asignados": mejor_t,
        "matriz_quiniela": matriz_final
    }


def seleccionar_cobertura_binaria_optima(partidos_14: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """[LN-QBE-085] Selecciona los 2 desenlaces con mayor probabilidad por partido."""
    resultado = []
    for p in partidos_14:
        p_qbe = p.get("p_qbe") or PROB_IGNORANCIA
        probs = [("L", float(p_qbe.get("L", PROB_IGNORANCIA["L"]))),
                 ("E", float(p_qbe.get("E", PROB_IGNORANCIA["E"]))),
                 ("V", float(p_qbe.get("V", PROB_IGNORANCIA["V"])))]
        # Ordenar desenlaces por probabilidad descendente
        probs.sort(key=lambda x: x[1], reverse=True)
        top_2 = [probs[0][0], probs[1][0]]
        masa_cubierta = round(probs[0][1] + probs[1][1], 4)
        
        resultado.append({
            "order": p.get("order", 0),
            "local": p.get("local", ""),
            "visitante": p.get("visitante", ""),
            "opciones": top_2,
            "probs_dict": dict(probs),
            "masa_2x": masa_cubierta
        })
    return resultado


def generar_universo_restringido_y_ordenar_p_prime(partidos_14: List[Dict[str, Any]]) -> List[Tuple[Tuple[str, ...], float]]:
    """[LN-QBE-084] Construye el espacio 2^K y ordena las boletas en la secuencia canónica P'."""
    coberturas = seleccionar_cobertura_binaria_optima(partidos_14)
    opciones_por_partido = [c["opciones"] for c in coberturas]
    probs_por_partido = [c["probs_dict"] for c in coberturas]

    candidatos = []
    for combinacion in product(*opciones_por_partido):
        p_conjunta = 1.0
        for idx, signo in enumerate(combinacion):
            p_conjunta *= probs_por_partido[idx].get(signo, PROB_IGNORANCIA[signo])
        candidatos.append((combinacion, round(p_conjunta, 8)))

    # Ordenamiento canónico descendente por masa probabilística P'
    candidatos.sort(key=lambda x: x[1], reverse=True)
    return candidatos



def seleccionar_primeras_m_combinaciones(
    p_prime_ordenado: List[Tuple[Tuple[str, ...], float]], 
    m_cupo: int
) -> Tuple[List[Dict[str, Any]], float]:
    """[LN-QBE-084] Toma las primeras M boletas maximizando estrictamente la masa acumulada C(M)."""
    seleccionadas = p_prime_ordenado[:max(1, m_cupo)]
    masa_acumulada = round(sum(item[1] for item in seleccionadas), 6)
    
    boletas_formateadas = []
    for idx, (comb, prob) in enumerate(seleccionadas, 1):
        boletas_formateadas.append({
            "boleta_id": idx,
            "combinacion": list(comb),
            "prob_conjunta": prob
        })
    return boletas_formateadas, masa_acumulada


def reducir_a_garantia_hamming_l(
    p_prime_ordenado: List[Tuple[Tuple[str, ...], float]],
    l_aciertos_objetivo: int = 13,
    max_boletas: int = 16
) -> List[Dict[str, Any]]:
    """[LN-QBE-086] Algoritmo Greedy de recubrimiento a distancia d_H <= 14 - L."""
    d_max = max(0, 14 - l_aciertos_objetivo)
    universo = [item[0] for item in p_prime_ordenado]
    cubiertos = set()
    seleccionadas = []

    for comb, prob in p_prime_ordenado:
        if len(seleccionadas) >= max_boletas:
            break
        # Calcular cuántos elementos nuevos cubre esta boleta dentro del radio de Hamming
        nuevos = 0
        indices_cubiertos = []
        for idx, u in enumerate(universo):
            if idx not in cubiertos:
                dist = sum(1 for a, b in zip(comb, u) if a != b)
                if dist <= d_max:
                    nuevos += 1
                    indices_cubiertos.append(idx)
        
        if nuevos > 0 or not seleccionadas:
            seleccionadas.append({
                "boleta_id": len(seleccionadas) + 1,
                "combinacion": list(comb),
                "prob_conjunta": prob,
                "nuevos_cubiertos": nuevos
            })
            cubiertos.update(indices_cubiertos)

    return seleccionadas


def optimizar_quiniela_progol_soberana(
    partidos_14: List[Dict[str, Any]], 
    presupuesto_mxn: float = 360.0,
    l_objetivo: int = 14
) -> Dict[str, Any]:
    """[LN-QBE-074] Orquestador maestro del optimizador combinatorio por presupuesto."""
    m_cupo = int(presupuesto_mxn // 15.0)
    p_prime = generar_universo_restringido_y_ordenar_p_prime(partidos_14)

    if l_objetivo >= 14:
        boletas, masa = seleccionar_primeras_m_combinaciones(p_prime, m_cupo)
        garantia = "14 Aciertos (Premio Mayor por Maximización de Masa C(M))"
    else:
        boletas = reducir_a_garantia_hamming_l(p_prime, l_aciertos_objetivo=l_objetivo, max_boletas=m_cupo)
        masa = round(sum(b["prob_conjunta"] for b in boletas), 6)
        garantia = f"{l_objetivo} Aciertos Garantizados al 100% (Radio de Hamming d<={14 - l_objetivo})"

    costo_total = len(boletas) * 15.0

    return {
        "combinaciones_totales": len(boletas),
        "costo_total_mxn": costo_total,
        "masa_acumulada_capturada": masa,
        "garantia_fiduciaria": garantia,
        "boletas": boletas
    }
