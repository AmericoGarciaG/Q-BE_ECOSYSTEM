# Q-BE Casino Deportes — Portfolio & Router Engine (src/core/portfolio.py)
"""
Router de Portafolio, Dimensionamiento Fraccional de Kelly y Asignación de Capital.
[LN-QBE-070] [LN-QBE-079] [LN-QBE-081] [LN-QBE-082] [BIZ-LOGIC] [ALGO-PROTECTED]
Calcula la asignación de capital y el Dutching exacto eliminando pisos fijos y respetando
el techo aritmético de cartera.
[ARCH-1.4.17] / [ARCH-1.4.18]: la cartera se ordena por P_éxito' (distribución contraída) y el
capital se asigna de forma monótona no creciente. `calcular_kelly_atenuado` subsiste como cota
de auditoría NO vinculante (TD-COR-01).
"""

import itertools
from typing import List, Dict, Any, Optional, Tuple
from src.core.catalog import STRATEGY_CATALOG
from src.core.contracts.portfolio_math import (
    calcular_dutching_v0, calcular_kelly_atenuado, aplicar_hard_caps_constitucionales,
    contraer_distribucion_fiduciaria, calcular_probabilidad_exito_estrategia,
    ordenar_cartera_por_certeza_lexicografica, asignar_capital_monotono_cartera,
    # [LN-QBE-077-B/C/D] / [ARCH-1.4.37] Cobertura Dinámica (V = δ > 0) de la Familia H.
    calcular_particion_dutching_dinamico,
)
from src.models.decision import (
    MatchExecutionOrder, StrategySelection, KeyMetrics, TicketOrder,
    MatchTickets, Projections, CashoutTargets, SatelliteModule,
    PortfolioControl, PortfolioBalance, PortfolioExecutionPlan
)

# [LN-QBE-071] Piso canónico de ventanilla: ÚNICA fuente de verdad del piso mínimo por boleto.
# Erradica los literales históricos (4.00 en asignación y 2.00 redeclarado dentro del bucle).
PISO_MINIMO_BOLETO = 2.00


def _reimponer_monotonia_fiduciaria(orders_raw: List[Dict[str, Any]]) -> float:
    """[ARCH-1.4.19 / ALT-1] Pase de monotonía fiduciaria no creciente sobre el libro de órdenes.

    El piso de ventanilla ([LN-QBE-071]) re-deriva A_i = B_seg × O_seg y acopla el tamaño al momio
    del desenlace de cobertura, de modo que una posición de certeza INFERIOR puede quedar por
    encima de su predecesora. Este pase reimpone B_(1) >= B_(2) >= ... >= B_(K) truncando el techo
    al de la posición precedente y RE-DERIVA los boletos con Clamping Fiduciario
    (B_seg >= $2.00 MXN): el excedente se absorbe reduciendo el boleto de ataque B_prio, NUNCA
    degradando el seguro por debajo del piso legal ([LN-QBE-070-E]). La identidad
    B_seg + B_prio = A_i se preserva, por lo que el capital total jamás se infla: sólo decrece.

    Función pura sobre el libro recibido (cero I/O, cero estado externo). Devuelve el capital
    realmente comprometido tras el pase.
    """
    for i in range(1, len(orders_raw)):
        if orders_raw[i]["inv_partido"] > orders_raw[i - 1]["inv_partido"]:
            orders_raw[i]["inv_partido"] = orders_raw[i - 1]["inv_partido"]
            # Reajustar boletos split preservando V=0 (o V>=0 favorable si el piso clampa)
            code_i = orders_raw[i]["code"]
            inv_i = orders_raw[i]["inv_partido"]
            if any(f in code_i for f in ["H1", "H1+", "H2", "H2+", "R1"]):
                b1_mom_i = orders_raw[i]["b1_momio"]
                if b1_mom_i > 0:
                    b1_m_i = max(PISO_MINIMO_BOLETO, round(inv_i / b1_mom_i, 2))
                    orders_raw[i]["b1_monto"] = b1_m_i
                    orders_raw[i]["b2_monto"] = round(max(0.0, inv_i - b1_m_i), 2)
            elif code_i in ["QBE-D1", "QBE-D1+", "QBE-D2"]:
                orders_raw[i]["b2_monto"] = inv_i
    return round(sum(item["inv_partido"] for item in orders_raw), 2)


def _casa_de_la_pierna(m: Dict[str, Any], momio_pierna: float,
                       o_fav: float, o_emp: float, o_und: float) -> Optional[str]:
    """[DES-QBE-053 / ARCH-1.5.10] Casa patrocinadora que publica el momio de UNA pierna.

    Atribución fáctica por IDENTIDAD del momio: cada boleto viaja con la casa que realmente
    publica la cuota que ese boleto transporta (Familia H —`H1`, `H2`—: seguro en tablas ->
    boleto 1 -> o_emp, ataque al favorito -> boleto 2 -> o_fav; `R1`/`R2`: boleto 2 -> o_und).
    [INVARIANTE VIII-11] La Resolución Definitiva de VARIANZA-H2 derogó la inversión histórica
    de H2 (que enviaba o_fav al boleto 1): la simetría H1/H2 hace que el seguro V=0 sea el
    Empate en TODA la Familia H. Cero heurística
    de nombres y cero invención: si el payload no declara casas (modalidad mono-operador
    heredada) devuelve `None` y la ventanilla exhibe su rótulo genérico de degradación.
    Función de ROTULADO: no interviene en ninguna magnitud de capital, Kelly o Hard-Caps.
    """
    op_fav = m.get("operador_ataque")
    op_emp = m.get("operador_seguro")
    op_und = m.get("operador_und") or op_fav
    try:
        leg = round(float(momio_pierna), 4)
    except (TypeError, ValueError):
        return str(op_fav) if op_fav else (str(op_emp) if op_emp else None)
    if op_fav is not None and leg == round(float(o_fav), 4):
        return str(op_fav)
    if op_emp is not None and leg == round(float(o_emp), 4):
        return str(op_emp)
    if op_und is not None and leg == round(float(o_und), 4):
        return str(op_und)
    return None


def _p_c_pierna_pct(seleccion: str, fav_name: Optional[str], und_name: Optional[str],
                    p_c_fav: Optional[float], p_c_emp: Optional[float],
                    p_c_und: Optional[float]) -> Optional[float]:
    """[DES-QBE-060] P' contraído (%) del desenlace que transporta UNA pierna.

    Resolución por IDENTIDAD de la etiqueta (mismo principio doctrinal que
    `_casa_de_la_pierna`): el rótulo fiduciario se ancla al desenlace REALMENTE exhibido en la
    selección de la pierna, jamás al nombre del contenedor. Tras la Resolución Definitiva de
    VARIANZA-H2 [INVARIANTE VIII-11] la Familia H quedó SIMÉTRICA (`boleto_1_seguro` = Empate /
    recuperación V=0; `boleto_2_ganancia` = Gana Favorito), pero la resolución por identidad se
    conserva como blindaje estructural: si un contenedor volviera a cruzarse, el rótulo NO lo
    hereda. Función de ROTULADO: no interviene en
    ninguna magnitud de capital, Kelly o Hard-Caps. Devuelve `None` ante una etiqueta no
    reconocible, para que la ventanilla degrade a '—' antes que inventar una cifra
    ([GOVERNANCE-01] cero cifras inventadas).
    """
    sel = str(seleccion or "").upper().replace(" + PA", "").strip()
    if not sel:
        return None
    valor_c = None
    if "EMPATE" in sel:
        valor_c = p_c_emp
    elif und_name and sel == f"GANA {str(und_name).upper()}":
        valor_c = p_c_und
    elif fav_name and sel == f"GANA {str(fav_name).upper()}":
        valor_c = p_c_fav
    return round(float(valor_c) * 100.0, 1) if valor_c is not None else None


def calcular_trinidad_resiliencia_3k(ordenes_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    [LN-QBE-072] Resuelve de forma exacta los 3^K estados combinatorios de la cartera
    y computa la Trinidad de Certeza Cuantitativa. Latencia < 1 ms.
    """
    K = len(ordenes_data)
    if K == 0:
        return {
            "pleno_exito": {"pnl_mxn": 0.0, "probabilidad_pct": 0.0},
            "tablas_o_ganancia": {"umbral_pnl_mxn": 0.0, "probabilidad_pct": 0.0},
            "ruina_total": {"pnl_mxn": 0.0, "probabilidad_pct": 0.0}
        }

    # Construir para cada partido los 3 desenlaces discretos (Win, Draw, Loss)
    activos_micro = []
    for o in ordenes_data:
        ganancia = float(o.get("ganancia", 0.0))
        inversion = float(o.get("inversion", 0.0))
        p_win = float(o.get("p_win", 0.70))
        p_draw = float(o.get("p_draw", 0.20))
        p_loss = float(o.get("p_loss", max(0.001, 1.0 - p_win - p_draw)))
        es_directo = bool(o.get("es_directo", False))

        # En estrategias directas (D1/D1+), el empate pierde la inversión
        pnl_draw = -inversion if es_directo else 0.0

        activos_micro.append([
            {"pnl": ganancia, "prob": p_win},      # Estado 0: Gana boleto ataque
            {"pnl": pnl_draw, "prob": p_draw},     # Estado 1: Empate (V=0 o pérdida si directo)
            {"pnl": -inversion, "prob": p_loss}    # Estado 2: Derrota / Ruina
        ])

    prob_tablas_o_arriba = 0.0
    pnl_maximo = sum(float(o.get("ganancia", 0.0)) for o in ordenes_data)
    inv_total = sum(float(o.get("inversion", 0.0)) for o in ordenes_data)

    # Evaluar los 3^K micro-estados exhaustivamente
    for estado_combinado in itertools.product(*activos_micro):
        pnl_estado = sum(e["pnl"] for e in estado_combinado)
        prob_estado = 1.0
        for e in estado_combinado:
            prob_estado *= e["prob"]

        if pnl_estado >= -0.01:
            prob_tablas_o_arriba += prob_estado

    # Probabilidades analíticas de extremos
    prob_pleno = 1.0
    prob_ruina = 1.0
    for o in ordenes_data:
        prob_pleno *= float(o.get("p_win", 0.70))
        prob_ruina *= float(o.get("p_loss", 0.05))

    return {
        "pleno_exito": {
            "pnl_mxn": round(pnl_maximo, 2),
            "probabilidad_pct": round(prob_pleno * 100.0, 1)
        },
        "tablas_o_ganancia": {
            "umbral_pnl_mxn": 0.0,
            "probabilidad_pct": round(min(99.9, prob_tablas_o_arriba * 100.0), 1)
        },
        "ruina_total": {
            "pnl_mxn": round(-inv_total, 2),
            "probabilidad_pct": round(prob_ruina * 100.0, 4)
        }
    }


def _distribucion_factica(m: Dict[str, Any]) -> Optional[Tuple[float, float, float]]:
    """[LN-QBE-070-C · Enmienda Nudo 1] Distribución soberana FÁCTICA del candidato.

    Devuelve `(p_fav, p_emp, p_und)` como FRACCIONES en (0, 1] —la unidad que consume
    `contraer_distribucion_fiduciaria`— o `None` si falta cualquiera de las tres, si no es
    numérica o si está fuera del símplex. La ausencia se declara; jamás se sustituye por una
    distribución inventada (55/25/20).
    """
    valores: List[float] = []
    for clave in ("prob_fav", "prob_emp", "prob_und"):
        valor = m.get(clave)
        if isinstance(valor, bool) or valor is None:
            return None
        try:
            numero = float(valor)
        except (TypeError, ValueError):
            return None
        if numero != numero:
            return None
        if numero > 1.0:
            numero = numero / 100.0
        if not 0.0 < numero <= 1.0:
            return None
        valores.append(numero)
    return (valores[0], valores[1], valores[2])


class PortfolioEngine:
    DESCRIPCIONES_OFICIALES = {k: v.descripcion_ejecutiva for k, v in STRATEGY_CATALOG.items()}

    @classmethod
    def select_best_strategy(
        cls,
        evals: Dict[str, Dict[str, Any]],
        psi_ruina: float,
        pago_anticipado: bool,
        p_fav: float = 0.50
    ) -> tuple:
        """
        Escalera Canónica de Prioridad Absoluta V2.5 por Utilidad Ajustada:
        U_Directo = EV_Net * P_Fav
        U_Cobertura = EV_Net * (1.0 - Psi_Ruina)
        """
        def calc_utility(strat_key: str) -> float:
            ev = evals[strat_key]["ev_neto_roi"]
            downside = p_fav if strat_key in ("QBE_R1", "QBE_R2") else psi_ruina
            return float(ev * ((1.0 - downside) ** 2))

        def calc_direct_utility(strat_key: str) -> float:
            ev = evals[strat_key]["ev_neto_roi"]
            return float(ev * p_fav)

        def calc_coverage_utility(strat_key: str) -> float:
            ev = evals[strat_key]["ev_neto_roi"]
            return float(ev * (1.0 - psi_ruina))

        code = None

        # Nivel 1: Freeroll Doble Impacto (Joya)
        if evals.get("QBE_H2_plus", {}).get("viable"):
            code = "QBE-H2+"
        else:
            direct_viable = [s for s in ["QBE_D1_plus", "QBE_D1"] if evals.get(s, {}).get("viable")]
            coverage_viable = [s for s in ["QBE_H1_plus", "QBE_H1"] if evals.get(s, {}).get("viable")]

            if direct_viable and coverage_viable:
                direct_best = max(direct_viable, key=calc_direct_utility)
                coverage_best = max(coverage_viable, key=calc_coverage_utility)
                if psi_ruina <= 0.08 and calc_direct_utility(direct_best) >= calc_coverage_utility(coverage_best):
                    code = direct_best.replace("_plus", "+").replace("_", "-")
                else:
                    # Nivel 2: Favoritos de Alta Convicción Potenciados
                    if evals.get("QBE_D1_plus", {}).get("viable") and psi_ruina <= 0.08 and p_fav >= 0.60:
                        code = "QBE-D1+"
                    else:
                        nivel_2 = [s for s in ["QBE_H1_plus", "QBE_D1_plus"] if evals.get(s, {}).get("viable")]
                        if nivel_2:
                            best = max(nivel_2, key=calc_utility)
                            code = best.replace("_plus", "+").replace("_", "-")
                        else:
                            # Nivel 3: Favoritos y Cobertura Estándar (H1 / D1)
                            nivel_3 = [s for s in ["QBE_H1", "QBE_D1"] if evals.get(s, {}).get("viable")]
                            if nivel_3:
                                best = max(nivel_3, key=calc_utility)
                                code = best.replace("_", "-")
                            else:
                                # Nivel 4: Empate de Valor (H2)
                                if evals.get("QBE_H2", {}).get("viable"):
                                    code = "QBE-H2"
                                else:
                                    # Nivel 5: Asaltos Inversos Condicionados - Familia R (R1 / R2)
                                    nivel_5 = [s for s in ["QBE_R1", "QBE_R2"] if evals.get(s, {}).get("viable")]
                                    if nivel_5:
                                        best = max(nivel_5, key=calc_utility)
                                        code = best.replace("_", "-")
                                    else:
                                        # Nivel 6: Protección de Capital (QBE-00)
                                        return "QBE-00", evals.get("QBE_00", {}).get("nombre_oficial", "Veto Preventivo de Capital"), 0.0, "N/A"
            else:
                # Nivel 2: Favoritos de Alta Convicción Potenciados
                if evals.get("QBE_D1_plus", {}).get("viable") and psi_ruina <= 0.08 and p_fav >= 0.60:
                    code = "QBE-D1+"
                else:
                    nivel_2 = [s for s in ["QBE_H1_plus", "QBE_D1_plus"] if evals.get(s, {}).get("viable")]
                    if nivel_2:
                        best = max(nivel_2, key=calc_utility)
                        code = best.replace("_plus", "+").replace("_", "-")
                    else:
                        # Nivel 3: Favoritos y Cobertura Estándar (H1 / D1)
                        nivel_3 = [s for s in ["QBE_H1", "QBE_D1"] if evals.get(s, {}).get("viable")]
                        if nivel_3:
                            best = max(nivel_3, key=calc_utility)
                            code = best.replace("_", "-")
                        else:
                            # Nivel 4: Empate de Valor (H2)
                            if evals.get("QBE_H2", {}).get("viable"):
                                code = "QBE-H2"
                            else:
                                # Nivel 5: Asaltos Inversos Condicionados - Familia R (R1 / R2)
                                nivel_5 = [s for s in ["QBE_R1", "QBE_R2"] if evals.get(s, {}).get("viable")]
                                if nivel_5:
                                    best = max(nivel_5, key=calc_utility)
                                    code = best.replace("_", "-")
                                else:
                                    # Nivel 6: Protección de Capital (QBE-00)
                                    return "QBE-00", evals.get("QBE_00", {}).get("nombre_oficial", "Veto Preventivo de Capital"), 0.0, "N/A"

        # ── [LN-QBE-060-B] Convergencia canónica: el código devuelto es estrictamente uno
        # de los 9 canónicos puros (QBE-D1/D2, H1/H2, R1/R2, C1/C2, 00). El sufijo histórico
        # `+` (Pago Anticipado) se DESACOPLA como anomalía de identidad de estrategia y viaja
        # como el atributo ortogonal `promocion` / `pago_anticipado: bool` ([LN-QBE-070-C]).
        codigo_canonico = code.replace("+", "").replace("_plus", "").replace("_", "-").strip()
        if codigo_canonico.endswith("-"):
            codigo_canonico = codigo_canonico[:-1]

        clean_key = code.replace("+", "_plus").replace("-", "_")
        nombre = evals.get(clean_key, {}).get("nombre_oficial") or evals.get(codigo_canonico.replace("-", "_"), {}).get("nombre_oficial", "Estrategia Cuantitativa")
        ev = evals.get(clean_key, {}).get("ev_neto_roi") or evals.get(codigo_canonico.replace("-", "_"), {}).get("ev_neto_roi", 0.0)
        promocion = "Pago Anticipado (+2 goles)" if ("+" in code or code == "QBE-R1" or pago_anticipado) else "Estándar"

        return codigo_canonico, nombre, ev, promocion

    @classmethod
    def build_plan(
        cls,
        approved_matches: List[Dict[str, Any]],
        bankroll: float,
        mode: str = "BANKROLL",
        total_jornada: int = 9,
        modo_cobertura: str = "DEF"
    ) -> PortfolioExecutionPlan:
        # [ARCH-1.4.14] `total_jornada` es el denominador fáctico de la cartelera: la cantidad
        # total de partidos que componen la fecha oficial (ej. 9 en Liga MX). Se propaga VERBATIM
        # desde el snapshot de origen; el motor NO lo deriva de K (jamás K / K).
        # [LN-QBE-070-C] Contrato Extendido R-1 (Estratos Epistemicos).
        # Todo `CandidateMatchPayload` porta obligatoriamente delta_epist (discrepancia ponderada)
        # y psi_epist (factor cuadratico de atenuacion). Defaults legislados por la Directiva
        # Fase 5 Paso 3: delta_epist = 0.02 y psi_epist = 0.97.
        # [LN-QBE-060-B] / [LN-QBE-070-B] Frontera de incertidumbre tau_disp = 0.12:
        # delta_epist > 0.12 <=> psi_epist = 0 => f*_adj = 0 => Cuarentena Fiduciaria (QBE-00, $0.00).
        # El filtro se ejecuta ANTES del ordenamiento para que la ruina conjunta, los pesos
        # y la Trinidad 3^K se computen exclusivamente sobre activos con capital autorizado.
        # ── [LN-QBE-077-B/C/D] / [ARCH-1.4.37] MODALIDAD CANÓNICA DE COBERTURA DINÁMICA ──────
        # `DEF` (default) conserva la indemnidad pura V=0 (paridad bit a bit con el contrato
        # histórico sellado); `BAL` ⇒ δ = 0.50·δ*, `AGR` ⇒ δ = δ*, `CUSTOM` ⇒ δ explícito. La
        # resolución del valor efectivo y su clamping fiduciario viven EXCLUSIVAMENTE en la ley
        # pura `calcular_particion_dutching_dinamico` ([LN-QBE-077-C]): cero números nuevos aquí.
        modo_cobertura_norm = str(modo_cobertura or "DEF").strip().upper()

        # ── 0. [LN-QBE-070-C · Enmienda Nudo 1] PUREZA DE DISTRIBUCIÓN ────────────────────
        # Sin las tres probabilidades soberanas fácticas no hay activo: la ausencia de dato
        # JAMÁS se rellena con 55/25/20. El candidato se deriva a QBE-00 (queda fuera del
        # dimensionamiento) y, si no sobrevive ninguno, la cartera es vacía (ValueError de
        # dominio). Cero distribuciones inventadas.
        approved_matches = [
            m for m in approved_matches
            if float(m.get("delta_epist", 0.02)) <= 0.12
            and float(m.get("psi_epist", 0.97)) > 0.0
            and _distribucion_factica(m) is not None
        ]
        # ── 1. [LN-QBE-079] Distribución Fiduciaria Contraída P̂_i' (variable DERIVADA downstream).
        # La distribución soberana P̂_i (Poisson/Dixon-Coles 6x6, 3NF) se consume como entrada de
        # SÓLO LECTURA: nunca se muta ni se sobreescribe ([ARCH-1.4.17]). La contracción baricéntrica
        # hacia P⁽⁰⁾ = (1/3, 1/3, 1/3) se pondera por Ψ_epist,i = max(0, 1 - (Δ_epist,i/0.12)²) y el
        # resultado se inyecta como campo derivado `prob_exito_efectiva` en el payload de trabajo.
        for m in approved_matches:
            p_fav_f, p_emp_f, p_und_f = _distribucion_factica(m)
            p_l_c, p_e_c, p_v_c = contraer_distribucion_fiduciaria(
                p_fav_f, p_emp_f, p_und_f, float(m.get("delta_epist", 0.02))
            )
            m["prob_exito_efectiva"] = calcular_probabilidad_exito_estrategia(
                m.get("strategy_code", "QBE-H1"), p_l_c, p_e_c, p_v_c
            )
            # [DES-QBE-060] Los TRES componentes de la distribución contraída P̂_i' se preservan
            # como campos derivados del payload, para que el motor rotule el P' fiduciario de
            # CADA pierna y del desenlace descartado (paridad fáctica backend↔pantalla).
            # Convención de la llamada canónica de arriba: p_l_c := prob_fav, p_e_c := prob_emp,
            # p_v_c := prob_und. Cero matemática nueva: sólo se conserva el resultado ya
            # calculado por el plano sellado ([VAULT-CORE-079-SHRINKAGE]). La distribución
            # soberana P̂_i (Poisson 6x6 + 3NF) permanece INTACTA ([ARCH-1.4.17]).
            m["p_c_fav"], m["p_c_emp"], m["p_c_und"] = p_l_c, p_e_c, p_v_c

        # ── 2. [LN-QBE-081] Ordenamiento Lexicográfico por Certeza y Ganancia ──
        # Erradicada la clave muerta `(-(1.0 - x["psi_downside"]), -x["ev_neto_roi"])`, que degeneraba
        # a ROI bruto descendente porque `psi_downside` viajaba fijo para todos los partidos (colocaba
        # a los volados de cuota alta arriba y a los favoritos seguros abajo). Clave vigente:
        # 1° P_éxito' descendente, 2° ganancia neta descendente.
        approved_matches = ordenar_cartera_por_certeza_lexicografica(approved_matches)

        k_count = len(approved_matches)
        if k_count == 0:
            raise ValueError("No hay partidos aprobados para construir el portafolio.")

        # Ruina conjunta multi-activo
        prod_psi = 1.0
        for m in approved_matches:
            prod_psi *= m["psi_downside"]
        p_ruina_total = prod_psi * 100.0
        blindaje = 100.0 - p_ruina_total

        # 2. Scores de Calidad [METRICAS DESCRIPTIVAS DEL CONTRATO — sin efecto sobre el capital]
        # [LN-QBE-082] El capital NO se deriva de S_i ni de w_i: ambos alimentan exclusivamente
        # `KeyMetrics.score_calidad_S_i` / `peso_portafolio_w_i`. El dimensionamiento monótono se
        # resuelve abajo con `asignar_capital_monotono_cartera`.
        scores = []
        for m in approved_matches:
            s_i = max(0.01, m["ev_neto_roi"]) / max(0.01, m["psi_downside"])
            scores.append(s_i)

        sum_scores = sum(scores) if sum(scores) > 0 else 1.0
        weights = [s / sum_scores for s in scores]

        # ── 3. [LN-QBE-082] Asignación Monótona de Capital: B_(1) >= B_(2) >= ... >= B_(K) ──
        # Erradicados como generadores de tamaño: (a) la bolsa heurística no legislada
        # `bolsa_core = bankroll · min(0.25, 0.06·K)` y (b) el piso `max(0.02, f_kelly)`. El capital de
        # cada partido viaja en `inversion_total` (bolsa de jornada 25%, tope individual 8%, piso de
        # bolsa 5.00) y los hard-caps constitucionales siguen vigentes como segunda línea de defensa.
        approved_matches = asignar_capital_monotono_cartera(approved_matches, bankroll)

        orders: List[MatchExecutionOrder] = []
        # 2. Generar estructuras intermedias de órdenes y validar Hard-Cap Global
        orders_raw = []
        total_inv_core = 0.0
        # [LN-QBE-070-B] / TD-COR-01: bitácora de la cota analítica de Kelly atenuado (NO vinculante).
        auditoria_kelly: List[Dict[str, Any]] = []

        for idx, m in enumerate(approved_matches):
            code = m["strategy_code"]
            nombre = m["strategy_nombre"]
            ev_roi = m["ev_neto_roi"]
            psi = m["psi_downside"]
            phi = m.get("phi_lead2", 0.0)
            # [LN-QBE-070-C] `phi_lead2` es el diagnóstico André del partido. Un payload que
            # omite la llave (snapshot sin evaluación André) se declara NO EVALUADO con el valor
            # neutro ya legislado en el plano canónico (`docs/DIRGEN_VAULT.md`: `phi_lead2_home=0.0,
            # phi_lead2_away=0.0` en la rama de suficiencia informativa insuficiente). Cero número
            # nuevo y cero efecto sobre Kelly / Hard-Caps: el campo sólo alimenta el reporte
            # descriptivo `KeyMetrics.phi_lead2_prob_ventaja_2_goles`.
            # VARIANCE-03-F7.6 (sometida a ratificación de la Tríada).
            o_fav, o_emp, o_und = m["odd_fav"], m["odd_emp"], m["odd_und"]
            fav_name, und_name = m["fav_name"], m["und_name"]

            pa_activo = bool("+" in code or m.get("pago_anticipado", False))
            suffix_pa = " + PA" if pa_activo else ""

            if mode == "BANKROLL":
                # [LN-QBE-082] Dimensionamiento por Asignación Monótona de Capital: la inversión de
                # cada partido es la magnitud ya jerarquizada por certeza en el paso 3 (el partido más
                # seguro recibe el mayor capital). Erradicado el piso `max(0.02, f_kelly)`, que regalaba
                # capital a las apuestas voladas y castigaba a los favoritos de cuota baja. El piso de
                # ventanilla ([LN-QBE-071] PISO_MINIMO_BOLETO) y los techos (8.0% individual / 25.0% de
                # jornada) ya fueron aplicados por el asignador y se re-verifican en la segunda línea
                # de defensa `aplicar_hard_caps_constitucionales` (portfolio_math.py).
                inv_partido = float(m["inversion_total"])
                # [LN-QBE-070-B] / TD-COR-01 — COTA ANALÍTICA DE AUDITORÍA, **NO VINCULANTE**.
                # `calcular_kelly_atenuado` subsiste únicamente como trazabilidad del techo fiduciario
                # de sostenibilidad y se reporta en `desglose_bankroll.auditoria_kelly_atenuado`.
                # Ningún peso de cartera se deriva de Kelly ([ARCH-1.4.18]).
                p_fav_i = _distribucion_factica(m)[0]
                o_fav_i = float(m.get("odd_fav", 2.0))
                delta_epist_i = float(m.get("delta_epist", 0.02))

                f_kelly = calcular_kelly_atenuado(p=p_fav_i, o=o_fav_i, delta_epist=delta_epist_i, gamma_kelly=0.25)
                cota_kelly = round(bankroll * f_kelly, 2) if f_kelly > 0.0 else 0.0
                auditoria_kelly.append({
                    "id_partido": m.get("id_partido"),
                    "prob_exito_efectiva": m.get("prob_exito_efectiva"),
                    "f_kelly_atenuado": f_kelly,
                    "cota_kelly_mxn": cota_kelly,
                    "capital_asignado_mxn": round(inv_partido, 2),
                    "excede_cota_kelly": bool(round(inv_partido, 2) > cota_kelly)
                })
            else:
                inv_partido = 10.00

            # ── [LN-QBE-077-B/C/D] / [ARCH-1.4.37] Parámetro δ de COBERTURA DINÁMICA ──────────
            # Toda orden sin cobertura dinámica viaja con δ = 0.0000 y ROI de empate 0.00%,
            # preservando el contrato sellado y satisfaciendo la Invariante VIII-54 (trazabilidad).
            delta_cobertura_i = 0.0
            roi_empate_i = 0.0
            # [LN-QBE-077-B] Proyección de COSECHA certificada por la ley pura: con δ = 0.0000
            # (modalidad defensiva) ambas cifras permanecen en 0.0000 — la modalidad sellada no
            # proyecta ganancia alguna en empate (cero promesa inventada, [GOVERNANCE-01]).
            cobro_empate_i = 0.0
            pnl_empate_i = 0.0

            if "H2" in code:
                # ══════════════════════════════════════════════════════════════════════════════
                # [INVARIANTE VIII-11] / [LN-QBE-083] SIMETRÍA CANÓNICA H1/H2 — RESOLUCIÓN
                # DEFINITIVA DE VARIANZA-H2 (Director Humano, 2026-10). Queda DEROGADO el Diseño B
                # del commit génesis `0f4b340` ("Empate de Valor con Seguro Fav"), que invertía las
                # piernas: el seguro V=0 se anclaba al FAVORITO y el ataque al EMPATE.
                # Doctrina vigente (Diseño A): TODA la Familia H monetiza el +EV del FAVORITO
                # (α_V > 0: en H2 el favorito es el visitante) y recupera el 100% del capital en
                # TABLAS (V=0). Anclaje ENDÓGENO (no requiere doctrina externa):
                #   (a) [LN-QBE-083] legisla para `H1` y `H2` por igual: "1. Ganancia Principal:
                #       Victoria ordinaria del favorito" y "Retorno Bruto = B_prio·O_fav + B_i ⟹
                #       ROI_doble = (1 − 1/O_emp)·O_fav".
                #   (b) Contrato de presentación (`app.js` L969-970): el BOLETO 1 exhibido (GANANCIA
                #       / ataque) es `boleto_2_ganancia` y el BOLETO 2 (SEGURO) es `boleto_1_seguro`.
                #   (c) Invarianza 1 del Auditor Independiente (`1_auditar_cartera_shield.py`): para
                #       H1/H2/R1, `boleto_1_seguro.monto × momio ≈ A_i`.
                #   (d) Pase de monotonía fiduciaria (`_reimponer_monotonia_fiduciaria`): re-deriva
                #       `B_seg = A_i / O_seguro` sobre `boleto_1_seguro` para toda la Familia H.
                # La asignación de importes se delega VERBATIM a la ley sellada
                # `[VAULT-CORE-070-DUTCHING]` (`calcular_dutching_v0`): b_seg = B_i / O_emp.
                b_prio, b_seg, _, _ = calcular_dutching_v0(inv_partido, o_fav, o_emp)
                # [ARCH-1.4.37] CAPA DE COBERTURA DINÁMICA: cuando la ventanilla solicita δ > 0,
                # la partición la dicta la ley GENERAL [LN-QBE-077-B] (B_seg(δ) = (1+δ)·B_i/O_emp)
                # y el δ efectivo viaja con la orden. Con la modalidad `DEF` (δ = 0.0000) nada
                # cambia: el contrato sellado V=0 subsiste idéntico (paridad bit a bit).
                res_dutch = calcular_particion_dutching_dinamico(
                    inv_partido, o_fav, o_emp, modo=modo_cobertura_norm
                )
                if res_dutch["delta_efectivo"] > 0.0:
                    b_prio = res_dutch["monto_ataque"]
                    b_seg = res_dutch["monto_seguro"]
                    # Cosecha Activa: cobro bruto y PnL neto de EMPATE literalmente certificados
                    # por la ley pura ([LN-QBE-077-B]) — se declaran, jamás se recalculan.
                    cobro_empate_i = res_dutch["cobro_bruto_empate"]
                    pnl_empate_i = res_dutch["pnl_neto_empate"]
                delta_cobertura_i = res_dutch["delta_efectivo"]
                roi_empate_i = res_dutch["roi_empate_porcentaje"]
                b1_sel = "Empate"
                b1_momio = o_emp
                b1_monto = b_seg
                b2_sel = f"Gana {fav_name}{suffix_pa}"
                b2_momio = o_fav
                b2_monto = b_prio
                out_min85 = "Sin descuento. Dejar correr al 90' para cobrar 100% Tablas o cobro anticipado por ventaja de 2 goles."
                tablas_amt = inv_partido
            elif "H1" in code:
                b1_sel = "Empate"
                b1_momio = o_emp
                b1_monto = round(inv_partido / b1_momio, 2)
                b2_sel = f"Gana {fav_name}{suffix_pa}"
                b2_momio = o_fav
                b2_monto = round(inv_partido - b1_monto, 2)
                # [ARCH-1.4.37] Capa de Cobertura Dinámica: con δ > 0 la partición la dicta la ley
                # general [LN-QBE-077-B]; con δ = 0.0000 subsiste la fórmula sellada V=0 idéntica.
                res_dutch = calcular_particion_dutching_dinamico(
                    inv_partido, o_fav, o_emp, modo=modo_cobertura_norm
                )
                if res_dutch["delta_efectivo"] > 0.0:
                    b1_monto = res_dutch["monto_seguro"]
                    b2_monto = res_dutch["monto_ataque"]
                    # Cosecha Activa: cobro bruto y PnL neto de EMPATE certificados por la ley
                    # pura ([LN-QBE-077-B]); se declaran, jamás se recalculan downstream.
                    cobro_empate_i = res_dutch["cobro_bruto_empate"]
                    pnl_empate_i = res_dutch["pnl_neto_empate"]
                delta_cobertura_i = res_dutch["delta_efectivo"]
                roi_empate_i = res_dutch["roi_empate_porcentaje"]
                out_min85 = "Sin descuento. Dejar correr al 90' para cobrar 100% Tablas o cobro anticipado por ventaja de 2 goles."
                tablas_amt = inv_partido
            elif code == "QBE-R1":
                b1_sel = "Empate"
                b1_momio = o_emp
                b1_monto = round(inv_partido / b1_momio, 2)
                b2_sel = f"Gana {und_name}{suffix_pa if suffix_pa else ' + PA'}"
                b2_momio = o_und
                b2_monto = round(inv_partido - b1_monto, 2)
                out_min85 = "Sin descuento. Dejar correr al 90' para cobrar 100% Tablas en empate o victoria de Underdog."
                tablas_amt = inv_partido
            elif code == "QBE-R2":
                if o_emp > 0 and o_und > 0:
                    inv_emp_w = (1.0 / o_emp) / ((1.0 / o_emp) + (1.0 / o_und))
                else:
                    inv_emp_w = 0.5
                b1_sel = "Empate"
                b1_momio = o_emp
                b1_monto = round(inv_partido * inv_emp_w, 2)
                b2_sel = f"Gana {und_name}{suffix_pa}"
                b2_momio = o_und
                b2_monto = round(inv_partido - b1_monto, 2)
                out_min85 = "Dejar correr al 90'. Ambos boletos cubren el escenario X2."
                tablas_amt = inv_partido
            else:
                b1_sel = "Empate (Sin Cobertura)"
                b1_momio = round(float(m.get("odd_emp") or o_emp or 3.70), 2)
                b1_monto = 0.0
                b2_sel = f"Gana {fav_name}{suffix_pa}"
                b2_momio = o_fav
                b2_monto = inv_partido
                out_min85 = "N/A (Dejar correr al 90' o cobrado anticipadamente por ventaja de 2 goles)."
                tablas_amt = 0.0

            if any(f in code for f in ["H1", "H1+", "H2", "H2+", "R1"]):
                if 0.0 < b1_monto < PISO_MINIMO_BOLETO:
                    b1_monto = PISO_MINIMO_BOLETO
                    # [INVARIANTE VIII-11] Toda la Familia H (H1/H2) ancla el seguro de tablas al
                    # momio del EMPATE: la pierna 1 transporta SIEMPRE el desenlace de recuperación.
                    odd_seguro = m["odd_emp"] if any(f in code for f in ["H1", "H1+", "H2", "H2+", "R1"]) else m["odd_fav"]
                    inv_partido = round(b1_monto * odd_seguro, 2)
                    b2_monto = round(inv_partido - b1_monto, 2)
                elif 0.0 < b2_monto < PISO_MINIMO_BOLETO:
                    b2_monto = PISO_MINIMO_BOLETO
                    inv_partido = round(b1_monto + b2_monto, 2)
            elif code == "QBE-R2":
                if 0.0 < b1_monto < PISO_MINIMO_BOLETO or 0.0 < b2_monto < PISO_MINIMO_BOLETO:
                    factor_escala = max(PISO_MINIMO_BOLETO / max(0.01, b1_monto), PISO_MINIMO_BOLETO / max(0.01, b2_monto))
                    b1_monto = round(b1_monto * factor_escala, 2)
                    b2_monto = round(b2_monto * factor_escala, 2)
                    inv_partido = round(b1_monto + b2_monto, 2)
            elif code in ["QBE-D1", "QBE-D1+"]:
                if inv_partido < PISO_MINIMO_BOLETO:
                    inv_partido = PISO_MINIMO_BOLETO
                    b2_monto = inv_partido

            total_inv_core += inv_partido
            orders_raw.append({
                "m": m, "idx": idx, "code": code, "nombre": nombre, "ev_roi": ev_roi, "psi": psi, "phi": phi,
                "pa_activo": pa_activo, "inv_partido": inv_partido, "b1_sel": b1_sel, "b1_momio": b1_momio,
                "b1_monto": b1_monto, "b2_sel": b2_sel, "b2_momio": b2_momio, "b2_monto": b2_monto,
                "out_min85": out_min85, "tablas_amt": tablas_amt,
                # [LN-QBE-077-B] / Invariante VIII-54: el δ efectivo y las proyecciones de
                # cosecha en empate viajan con el libro de órdenes (se declaran VERBATIM desde la
                # ley pura, jamás se recalculan downstream). Con δ = 0.0000 (modo `DEF`) las
                # cifras de cosecha son 0.0000: la modalidad sellada no promete ganancia en empate.
                "delta_cobertura": delta_cobertura_i, "roi_empate_porcentaje": roi_empate_i,
                "cobro_bruto_empate_mxn": cobro_empate_i, "pnl_neto_empate_mxn": pnl_empate_i,
                "modo_cobertura": modo_cobertura_norm
            })

        # ── [ARCH-1.4.19 / ALT-1] SEGUNDO PASE DE MONOTONÍA FIDUCIARIA NO CRECIENTE ──────────
        # Ver `_reimponer_monotonia_fiduciaria`: la certeza gobierna el capital, nunca el momio.
        # [LN-QBE-070-B] El libro debe reflejar el capital REALMENTE comprometido (si el total
        # quedara obsoleto, el factor de prorrateo se calcularía contra un techo falso).
        total_inv_core = _reimponer_monotonia_fiduciaria(orders_raw)

        # ── [LN-QBE-070-B] HARD-CAPS CONSTITUCIONALES CANÓNICOS ───────────────
        # Los techos dejan de ser literales locales: la acotación individual (8.0%) y el
        # prorrateo global de jornada (25.0%) se delegan íntegramente a portfolio_math.py.
        inv_canonicas = aplicar_hard_caps_constitucionales(
            [item["inv_partido"] for item in orders_raw], bankroll
        )
        total_canonico = round(sum(inv_canonicas), 2)
        if orders_raw and total_inv_core > 0.0 and total_canonico < total_inv_core:
            scale_factor = round(total_canonico / total_inv_core, 8)
            total_inv_core = 0.0
            for item in orders_raw:
                code = item["code"]
                inv_orig = item["inv_partido"]
                new_inv = round(inv_orig * scale_factor, 2)
                b1_m = item["b1_monto"]
                b2_m = item["b2_monto"]
                b1_mom = item["b1_momio"]

                if b1_m > 0:
                    b1_m = round(b1_m * scale_factor, 2)
                if b2_m > 0:
                    b2_m = round(b2_m * scale_factor, 2)

                if any(f in code for f in ["H1", "H1+", "H2", "H2+", "R1"]):
                    # [ARCH-1.4.19 / LN-QBE-071] Clamping Fiduciario: el prorrateo jamás puede
                    # empujar el boleto seguro por debajo del piso legal de ventanilla ($2.00 MXN).
                    b1_m = max(PISO_MINIMO_BOLETO, b1_m) if b1_m > 0 else 0.0
                    new_inv = round(b1_m * b1_mom, 2) if b1_mom > 0 else new_inv
                    b2_m = round(max(0.0, new_inv - b1_m), 2)
                elif code in ["QBE-D1", "QBE-D1+"]:
                    new_inv = b2_m

                item["inv_partido"] = new_inv
                item["b1_monto"] = b1_m
                item["b2_monto"] = b2_m
                total_inv_core += new_inv

        # [ARCH-1.4.19 / ALT-1] El pase de monotonía es la ÚLTIMA autoridad sobre A_i: el prorrateo
        # del Hard-Cap global (25.0%) y su Clamping Fiduciario re-derivan A_i = B_seg × O_seg, lo
        # que puede re-inflar una pierna por encima de su predecesora y rebasar el techo de jornada.
        # Se reimpone la monotonía absorbiendo el excedente en B_prio (jamás en el seguro) y el
        # libro vuelve a reflejar el capital realmente comprometido.
        total_inv_core = _reimponer_monotonia_fiduciaria(orders_raw)

        # Materializar instancias Pydantic MatchExecutionOrder
        orders: List[MatchExecutionOrder] = []
        ganancia_esperada_core = 0.0

        for item in orders_raw:
            m = item["m"]
            idx = item["idx"]
            code = item["code"]
            nombre = item["nombre"]
            ev_roi = item["ev_roi"]
            psi = item["psi"]
            phi = item["phi"]
            pa_activo = item["pa_activo"]
            inv_partido = item["inv_partido"]
            b1_sel = item["b1_sel"]
            b1_momio = item["b1_momio"]
            b1_monto = item["b1_monto"]
            b2_sel = item["b2_sel"]
            b2_momio = item["b2_momio"]
            b2_monto = item["b2_monto"]
            out_min85 = item["out_min85"]
            tablas_amt = item["tablas_amt"]
            # [DES-QBE-053 / ARCH-1.5.10] Cuotas CANÓNICAS DE ESTE ÍTEM. La casa de cada pierna se
            # resuelve contra las cuotas del partido en curso; jamás contra variables heredadas de
            # otra iteración del bucle anterior (defecto de variable obsoleta detectado en la prueba
            # de fuego E2E: el boleto del partido N se comparaba contra el momio del partido último).
            o_fav_i, o_emp_i, o_und_i = m["odd_fav"], m["odd_emp"], m["odd_und"]

            # ── [DES-QBE-060] P' fiduciario por pierna y desenlace descartado ───────────────
            # Los componentes contraídos viajan como campos derivados en el payload (paso 1);
            # este bloque SÓLO los rotula. Cero números nuevos, cero recálculo y cero efecto
            # sobre capital, Kelly o Hard-Caps: es metadata de exhibición.
            # VARIANCE-04-F7.8 (sometida a ratificación de la Tríada): la Resolución nombra la
            # terna como `p_fav_c` / `pe_c` / `pv_c` y los contenedores `boleto_1_ganancia` /
            # `boleto_2_seguro`, nombres que NO existen en el código (la terna canónica es
            # `p_l_c, p_e_c, p_v_c` y los contenedores legislados son `boleto_1_seguro` y
            # `boleto_2_ganancia`, cuyo CONTENIDO se invierte entre las familias H1 y H2 — la
            # prueba de fuego E2E del 2026-09 demostró que rotular por nombre de campo
            # disparaba el P' del Empate sobre una pierna de Gana-Favorito). Se materializa la
            # INTENCIÓN fiduciaria resolviendo por IDENTIDAD de la etiqueta, igual que
            # `_casa_de_la_pierna`: el P' exhibido es siempre el del desenlace que la pierna
            # realmente transporta.
            p_c_fav = m.get("p_c_fav")
            p_c_emp = m.get("p_c_emp")
            p_c_und = m.get("p_c_und")
            fav_name = m.get("fav_name")
            und_name = m.get("und_name")
            prob_b1 = _p_c_pierna_pct(b1_sel, fav_name, und_name, p_c_fav, p_c_emp, p_c_und)
            prob_b2 = _p_c_pierna_pct(b2_sel, fav_name, und_name, p_c_fav, p_c_emp, p_c_und)
            # El desenlace NO JUGADO es el rival que la estrategia no cubre por diseño: en
            # H/D (cobertura Fav+Empate o sólo Fav) es el underdog; en R (cobertura Emp+Und)
            # el descartado es el favorito — exhibir ahí al underdog contradiría al boleto de
            # ataque que lo juega (paridad fáctica [DES-QBE-060]).
            cobertura_emp_und = code in ("QBE-R1", "QBE-R2")
            desc_p_c = p_c_fav if cobertura_emp_und else p_c_und
            opcion_no_jugada = {
                "nombre": (fav_name if cobertura_emp_und else und_name) or "Rival Descartado",
                "momio": o_fav_i if cobertura_emp_und else o_und_i,
                "prob_qbe": round(float(desc_p_c) * 100.0, 1) if desc_p_c is not None else None
            }

            if code == "QBE-R2":
                ganancia_neta = round(min(b1_monto * b1_momio, b2_monto * b2_momio) - inv_partido, 2)
            else:
                ganancia_neta = round((b2_monto * b2_momio) - inv_partido, 2)

            roi_pct = round((ganancia_neta / max(0.01, inv_partido)) * 100.0, 2)
            freeroll_neta = round((b1_monto * b1_momio) + (b2_monto * b2_momio) - inv_partido, 2) if "+" in code else 0.0
            freeroll_roi = round((freeroll_neta / max(0.01, inv_partido)) * 100.0, 2) if "+" in code else 0.0
            if any(f in code for f in ["H1", "H1+", "H2", "H2+", "R1", "R2"]):
                tablas_amt = inv_partido

            ganancia_esperada_core += (inv_partido * ev_roi) if ev_roi > 0 else 0.0

            fav_pos = m.get("fav_pos", 1)
            fav_pts = m.get("fav_pts", 0)
            q_fav = m.get("q_mod_fav", 1.0)
            und_pos = m.get("und_pos", 18)
            und_pts = m.get("und_pts", 0)
            q_und = m.get("q_mod_und", 1.0)

            # [LN-QBE-077-B] / Invariante VIII-54: bloque DERIVADO de trazabilidad de δ y de los
            # ROIs proyectados (favorito / empate). Cero aritmética nueva: se declara lo certificado
            # por el motor y sólo viaja en las familias con seguro de empate (H1/H2).
            es_familia_h = code.replace("+", "").strip() in ("QBE-H1", "QBE-H2")
            cobertura_dinamica = {
                "modo": item.get("modo_cobertura", "DEF"),
                "delta_cobertura": round(float(item.get("delta_cobertura", 0.0) or 0.0), 4),
                "roi_empate_porcentaje": float(item.get("roi_empate_porcentaje", 0.0) or 0.0),
                "roi_favorito_porcentaje": roi_pct,
                # Alias canónico del contrato de salida de la ley pura ([LN-QBE-077-B] declara
                # `delta_efectivo`): la ventanilla exhibe este nombre sin re-derivar nada.
                "delta_efectivo": round(float(item.get("delta_cobertura", 0.0) or 0.0), 4),
                "cobro_bruto_empate_mxn": round(float(item.get("cobro_bruto_empate_mxn", 0.0) or 0.0), 2),
                "pnl_neto_empate_mxn": round(float(item.get("pnl_neto_empate_mxn", 0.0) or 0.0), 2)
            } if es_familia_h else None

            order = MatchExecutionOrder(
                id_partido=m["id_partido"],
                partido=m["partido_nombre"],
                horario_evento=m.get("horario", "Fin de Semana"),
                estrategia_seleccionada=StrategySelection(
                    # [LN-QBE-070-C] La orden Pydantic expone EXCLUSIVAMENTE el código canónico puro;
                    # el Pago Anticipado se hereda como atributo ortogonal (`linea_promocional` / `+ PA`).
                    codigo=code.replace("+", "").strip(),
                    nombre_oficial=nombre,
                    descripcion_ejecutiva=cls.DESCRIPCIONES_OFICIALES.get(code, "Estrategia Cuantitativa"),
                    linea_promocional="Pago Anticipado (+2 goles)" if (pa_activo or code == "QBE-R1") else "Estándar"
                ),
                metricas_clave=KeyMetrics(
                    score_calidad_S_i=round(scores[idx], 4),
                    peso_portafolio_w_i=round(weights[idx], 4),
                    phi_lead2_prob_ventaja_2_goles=round(phi, 4),
                    psi_downside_riesgo=round(psi, 4),
                    ev_neto_roi_porcentaje=round(ev_roi * 100.0, 2)
                ),
                forma_reciente_auditada={
                    "fav_resumen": f"Posición #{fav_pos}, {fav_pts} pts | Q_mod: {q_fav}",
                    "und_resumen": f"Posición #{und_pos}, {und_pts} pts | Q_mod: {q_und}"
                },
                boletos=MatchTickets(
                    inversion_partido_A_i=inv_partido,
                    boleto_1_seguro=TicketOrder(seleccion=b1_sel, momio=b1_momio, monto_mxn=b1_monto,
                                                operador=_casa_de_la_pierna(m, b1_momio, o_fav_i, o_emp_i, o_und_i),
                                                prob_qbe=prob_b1),
                    boleto_2_ganancia=TicketOrder(seleccion=b2_sel, momio=b2_momio, monto_mxn=b2_monto,
                                                  operador=_casa_de_la_pierna(m, b2_momio, o_fav_i, o_emp_i, o_und_i),
                                                  prob_qbe=prob_b2)
                ),
                proyecciones=Projections(
                    ganancia_neta_principal_mxn=ganancia_neta,
                    roi_principal_porcentaje=roi_pct,
                    freeroll_doble_ganancia_mxn=freeroll_neta,
                    freeroll_roi_porcentaje=freeroll_roi,
                    resultado_tablas_mxn=tablas_amt,
                    perdida_maxima_posible_mxn=inv_partido
                ),
                cashout_targets=CashoutTargets(
                    monto_salida_emergencia_tablas_mxn=tablas_amt,
                    monto_salida_optima_min85=out_min85,
                    instruccion_emergencia_rompequinielas=f"CashOut en cuanto ofrezca Tablas (${inv_partido} MXN) al igualar en el 2T." if tablas_amt > 0 else "Monitorear en el 2T.",
                    instruccion_desarrollo_normal=out_min85
                ),
                # [LN-QBE-077-B] / Invariante VIII-54: bloque DERIVADO de trazabilidad de δ y de
                # los ROIs proyectados (favorito / empate), hidratado más arriba sin aritmética
                # nueva: se declara lo certificado por el motor (sólo familias con seguro).
                # [DES-QBE-060] Bloque de Transparencia 360°: desenlace rival descartado.
                opcion_no_jugada=opcion_no_jugada,
                cobertura_dinamica=cobertura_dinamica
            )
            orders.append(order)

        # 3. Satélite Asimétrico
        sat_module = SatelliteModule(
            autorizado=False,
            justificacion_financiamiento="No se autoriza boleto satélite al no existir underdogs con ventaja extrema en cuotas >= 4.50."
        )

        # 4. Consolidación de Balance con Techo Aritmético Estricto
        total_inv_core = round(sum(o.boletos.inversion_partido_A_i for o in orders), 2)

        ganancia_maxima_posible = sum(o.proyecciones.ganancia_neta_principal_mxn for o in orders)
        ganancia_esperada_core = round(min(ganancia_maxima_posible, max(0.0, ganancia_esperada_core)), 2)
        roi_global_esp = round((ganancia_esperada_core / total_inv_core) * 100.0, 2) if total_inv_core > 0 else 0.0

        # ── 5. Análisis de Resiliencia y Cascada de Reveses (Stress-Testing) ──
        # ── [LN-QBE-072] Cascada de Resiliencia Estocástica Ponderada ───────────
        import numpy as np

        ordenes_ordenadas = sorted(
            orders,
            key=lambda x: x.proyecciones.roi_principal_porcentaje,
            reverse=False
        )

        K = len(orders)
        probs_win = []
        for o in ordenes_ordenadas:
            inv_a = max(1.0, o.boletos.inversion_partido_A_i)
            p_est = 1.0 - (o.proyecciones.perdida_maxima_posible_mxn / inv_a * 0.2)
            probs_win.append(min(0.95, max(0.40, p_est)))

        cascada_reveses = []
        reveses_tolerados = 0

        for m in range(K + 1):
            if m == 0:
                pnl = sum(o.proyecciones.ganancia_neta_principal_mxn for o in orders)
                prob_nivel = round(float(np.prod(probs_win)) * 100.0, 1)
            elif m == K:
                pnl = -sum(o.boletos.inversion_partido_A_i for o in orders)
                prob_nivel = round(float(p_ruina_total), 4)
            else:
                ganancias_supervivientes = sum(o.proyecciones.ganancia_neta_principal_mxn for o in ordenes_ordenadas[:-m])
                perdidas_caidas = sum(o.boletos.inversion_partido_A_i for o in ordenes_ordenadas[-m:])
                pnl = ganancias_supervivientes - perdidas_caidas

                prob_fallo_m = float(np.prod([1.0 - p for p in probs_win[-m:]]))
                prob_exito_restantes = float(np.prod(probs_win[:-m]))
                prob_nivel = round(prob_fallo_m * prob_exito_restantes * 100.0, 1)

            if pnl >= 0.0 and m > 0:
                reveses_tolerados = m

            cascada_reveses.append({
                "nivel": m,
                "reveses": m,
                "escenario": "Pleno Éxito (0 Fallos)" if m == 0 else (f"{K} Reveses (Ruina Total)" if m == K else f"{m} Reves{'es' if m > 1 else ''}"),
                "pnl_mxn": round(pnl, 2),
                "roi_pct": round((pnl / total_inv_core) * 100.0, 1) if total_inv_core > 0 else 0.0,
                "probabilidad_pct": prob_nivel,
                "estado": "PLENO_POSITIVO" if (pnl > 0 and m == 0) else ("SUPERAVIT" if pnl > 0 else ("BREAKEVEN" if pnl == 0 else "DEFICIT"))
            })

        # ── [LN-QBE-072] Trinidad de Certeza Cuantitativa 3^K ──
        ordenes_trinidad = []
        for idx, o in enumerate(orders):
            m = approved_matches[idx]
            p_w, p_d, p_l = _distribucion_factica(m)
            code = o.estrategia_seleccionada.codigo
            es_directo = code in ["QBE-D1", "QBE-D1+"]

            ordenes_trinidad.append({
                "ganancia": o.proyecciones.ganancia_neta_principal_mxn,
                "inversion": o.boletos.inversion_partido_A_i,
                "p_win": p_w,
                "p_draw": p_d,
                "p_loss": p_l,
                "es_directo": es_directo
            })

        trinidad_resiliencia = calcular_trinidad_resiliencia_3k(ordenes_trinidad)

        plan_ejecucion = PortfolioExecutionPlan(
            control_portafolio=PortfolioControl(
                modalidad="BANKROLL" if mode == "BANKROLL" else "VAQUITA",
                total_partidos_core_aprobados=k_count,
                total_partidos_jornada=int(total_jornada),
                total_partidos_escaneados=int(total_jornada),
                capital_total_core_mxn=total_inv_core,
                probabilidad_ruina_total_porcentaje=round(p_ruina_total, 4),
                blindaje_global_preservacion_porcentaje=round(blindaje, 4),
                desglose_vaquita={"activa": mode == "VAQUITA", "cuota_fija_por_partido_mxn": 10.0, "numero_socios": 5},
                desglose_bankroll={
                    "activa": mode == "BANKROLL",
                    "bankroll_total": bankroll,
                    "porcentaje_total_arriesgado": round((total_inv_core / bankroll) * 100.0, 2),
                    "reveses_maximos_tolerados": reveses_tolerados,
                    "cascada_resiliencia": cascada_reveses,
                    "trinidad_resiliencia": trinidad_resiliencia,
                    # [LN-QBE-070-B] / TD-COR-01: cota analítica de Kelly atenuado (auditoría NO
                    # vinculante). Informa el techo fiduciario de sostenibilidad frente al capital
                    # realmente asignado por [LN-QBE-082]. No interviene en ninguna magnitud de cartera.
                    "auditoria_kelly_atenuado": auditoria_kelly
                }
            ),
            ordenes_ejecucion_partidos=orders,
            modulo_satelite_asimetrico=sat_module,
            balance_global_portafolio=PortfolioBalance(
                capital_total_comprometido_mxn=total_inv_core,
                ganancia_neta_esperada_jornada_mxn=ganancia_esperada_core,
                roi_global_esperado_porcentaje=roi_global_esp
            )
        )
        return plan_ejecucion
