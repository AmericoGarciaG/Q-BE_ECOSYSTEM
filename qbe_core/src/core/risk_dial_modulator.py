# -*- coding: utf-8 -*-
"""
🏆 Q-BE SOVEREIGN ENGINE — MODULADOR ADAPTATIVO DEL SLIDER DE CERTEZA EN ESPACIO 3^K
[VAULT-CORE-006] Algoritmo Fiduciario de Transmutación D1 -> H1 y Poda de Varianza.
Base de Gobierno: Kybern Framework v12.0 [LN-QBE-073]
"""

from typing import List, Dict, Any
from src.core.portfolio import calcular_trinidad_resiliencia_3k
from src.core.contracts.portfolio_math import calcular_ganancia_cobertura_v0


def modular_cartera_por_slider_certeza(
    ordenes_candidatas: List[Dict[str, Any]],
    target_certeza_pct: float = 80.0,
    piso_ventanilla: float = 2.0
) -> List[Dict[str, Any]]:
    """
    [LN-QBE-073] Modula dinámicamente la cartera de casino para garantizar que
    la probabilidad combinada de no perder (tablas o arriba) satisfaga target_certeza_pct.
    Transmuta D1 -> H1 y contrae exposición si es necesario.
    """
    if not ordenes_candidatas:
        return []

    target = float(max(70.0, min(95.0, target_certeza_pct)))
    ordenes = [dict(o) for o in ordenes_candidatas]

    # Bucle de convergencia fiduciaria (máximo 5 iteraciones)
    for _ in range(5):
        # 1. Evaluar el espacio 3^K actual
        trinidad = calcular_trinidad_resiliencia_3k(ordenes)
        certeza_actual = float(trinidad.get("tablas_o_ganancia", {}).get("probabilidad_pct", 0.0))

        # Si ya se cumple la meta de certeza, retornar órdenes optimizadas
        if certeza_actual >= target:
            break

        # 2. Localizar órdenes directas (D1/D1+) que expongan capital al empate sin seguro
        orden_directa_idx = None
        menor_prob_directa = 1.0

        for idx, o in enumerate(ordenes):
            if o.get("es_directo", False):
                p_win = float(o.get("p_win", 1.0))
                if p_win < menor_prob_directa:
                    menor_prob_directa = p_win
                    orden_directa_idx = idx

        # Si hay una orden directa, transmutarla a cobertura H1 (comprar seguro V=0)
        if orden_directa_idx is not None:
            od = ordenes[orden_directa_idx]
            od["es_directo"] = False
            od["estrategia_codigo"] = "QBE-H1"
            od["linea_promocional"] = "Cobertura por Certeza Slider"

            # [LN-QBE-073-B] Prima de Cobertura Canónica (dutching V=0 a cuotas soberanas justas).
            # Al volverse cobertura, el empate ya no pierde dinero: pnl_draw pasa de -inversión a $0.00.
            # El sacrificio de premio se DERIVA de la masa de probabilidad transferida al seguro;
            # se erradica el factor mágico `0.70` (ver portfolio_math.calcular_ganancia_cobertura_v0).
            od["ganancia"] = calcular_ganancia_cobertura_v0(
                ganancia_directa=float(od.get("ganancia", 0.0)),
                inversion=float(od.get("inversion", 0.0)),
                p_draw=float(od.get("p_draw", 0.0))
            )
            continue

        # 3. Si ya no hay órdenes directas y aún no alcanza el target:
        # Podar la orden más frágil de la cartera para salvar la certeza global
        if len(ordenes) > 1:
            # Ordenar por probabilidad de éxito y remover la peor
            ordenes.sort(key=lambda x: float(x.get("p_win", 0.0)), reverse=True)
            ordenes.pop()  # Poda fiduciaria del activo más riesgoso
        else:
            break

    return ordenes
