# -*- coding: utf-8 -*-
"""
🏆 Q-BE SOVEREIGN FINANCIAL ENGINE — CONTRATOS MATEMÁTICOS DE PORTAFOLIO Y 9 ESTRATEGIAS
[ARCH-1.4.9] Biblioteca Funcional Pura de Asignación, Coberturas V=0, Kelly y Triaje Canónico.
[VAULT-CORE-070-TRIAJE], [VAULT-CORE-070-DUTCHING], [VAULT-CORE-070-RANKING],
[VAULT-CORE-070-KELLY], [VAULT-CORE-071-PISO], [VAULT-CORE-079-SHRINKAGE]
Régimen: [DIRGEN-STRICT]
Axioma: Cero dependencias de base de datos. Cero I/O. Cero números mágicos.
"""

import math
from typing import List, Dict, Tuple, Optional, Any


def calcular_alpha_edge(p: float, o: float) -> float:
    """[LN-QBE-007-C] Retorno neto esperado por unidad de capital (Edge)."""
    if p <= 0.0 or o <= 1.0:
        return -1.0
    return round(p * o - 1.0, 4)


def calcular_umbral_theta_estrella(o_fav: float) -> float:
    """[LN-QBE-050] Umbral de indiferencia theta* para cobertura viable en tablas."""
    if o_fav <= 1.0:
        return 999.0
    return round(o_fav / (o_fav - 1.0), 4)


def calcular_dutching_v0(b_total: float, o_fav: float, o_emp: float) -> Tuple[float, float, float, float]:
    """[LN-QBE-070] Resuelve importes y ROI garantizando V=0 en empate."""
    if o_emp <= 1.0 or o_fav <= 1.0 or b_total <= 0.0:
        return (0.0, 0.0, 0.0, 0.0)
    b_seg = round(b_total / o_emp, 2)
    b_prio = round(b_total - b_seg, 2)
    ganancia_neta = round((b_prio * o_fav) - b_total, 2)
    roi_pct = round((ganancia_neta / b_total) * 100.0, 2)
    return (b_prio, b_seg, ganancia_neta, roi_pct)


# ── [LN-QBE-077-B] / [LN-QBE-077-C] / [LN-QBE-077-D] COBERTURA DINÁMICA (V = δ > 0) ───────────
# Manifiesto canónico de `docs/CONSTANTS.md` («Parámetros de Cobertura Dinámica»). El Dutching
# clásico V=0 subsiste como la especialización δ = δ_def de la MISMA ley general de partición.
DELTA_DUTCHING_DEF: float = 0.0000          # δ_def — indemnidad pasiva V=0 exacta
RATIO_DELTA_BAL: float = 0.5000             # r_bal — fracción balanceada del δ de isorrendimiento
FACTOR_SEGURIDAD_DELTA_MAX: float = 0.9500  # Margen_δ — techo fiduciario de seguridad sobre δ_max
# Umbral operativo de reconocimiento de la Cosecha Activa: por debajo de este δ el desvío de
# capital hacia el seguro es ruido de redondeo y el veredicto permanece en la ley sellada V=0.
UMBRAL_DELTA_COSECHA_ACTIVA: float = 0.05


# ── [LN-QBE-060-C] FILTRO DE VETO FIDUCIARIO INTELIGENTE ANTI-RUPTURA (QBE-00) ─────────────────
# Manifiesto canónico de `docs/CONSTANTS.md` («Parámetros del Filtro de Veto Inteligente
# Anti-Ruptura»). Escalares identificables para ML. La aduana califica el veredicto VACÍO del
# triaje (paso 6) y jamás suprime una estrategia canónica ya resuelta por la cascada
# `[LN-QBE-060-B]` / `[VAULT-CORE-070-TRIAJE]`.
DELTA_P_PARIDAD_VETO: float = 0.1200    # ΔP_veto — dispersión mínima para admitir convicción
PMAX_MIN_OPERABLE: float = 0.3800       # P_max^min — piso de masa del favorito para apostar
LAMBDA_SUMA_FUEGO_VETO: float = 3.0000  # Σλ_fuego — techo de xG combinados que vetan el 1X2
P_EMPATE_FUEGO_TECHO: float = 0.2200    # p_X^max — cota de empate asfixiado en juegos de fuego


# ── [LN-QBE-115] SANEAMIENTO VOL. II — COTA UNDERDOG LEY 3 Y ESCUDO DE ALTITUD ────────────────
# Manifiesto canónico de `docs/CONSTANTS.md` (§5 «Dominio Financiero» y «Parámetros del Escudo de
# Altitud y de la Trinidad de Certeza»). La cota del 1.5% es un TECHO adicional EXCLUSIVO de la
# Familia R: jamás un piso, jamás rescata una orden sub-dimensionada ni infla la bolsa del 25%.
# El escudo de altitud veta la Híbrida Visitante cuando la visita viaja a >= 1000 m por encima de
# su plaza (trampa fisiológica certificada en `[LN-QBE-109]` V28, unidireccional).
CAP_UNDERDOG_LEY3_PCT: float = 0.0150          # Cap_underdog — techo duro de QBE-R1 / QBE-R2
FAMILIAS_UNDERDOG_LEY3: Tuple[str, ...] = ("QBE-R1", "QBE-R2")
UMBRAL_VETO_ALTITUD_METROS: float = 1000.0     # ΔAlt^veto — trampa de altitud visitante
# ── [LN-QBE-116] COTA DE DOMINANCIA P' >= 50% — BLINDAJE DE LA HÍBRIDA VISITANTE ────────────
# Manifiesto canónico de `docs/CONSTANTS.md` («Parámetros de la Cota de Dominancia P′»). La H2
# promete dominancia foránea con el empate asegurado en tablas: si el propio P' del modelo no
# concede mayoría al visitante, la promesa es fiduciariamente falsa. Piso de dominancia, jamás
# exclusión del 50%: la comparación es ESTRICTA (p2 == 0.5000 NO veta).
UMBRAL_DOMINANCIA_VISITANTE_PCT: float = 0.5000  # P'_min,visita — piso de mayoría del visitante


def calcular_delta_max_analitico(o_fav: float, o_emp: float) -> float:
    """[LN-QBE-077-C] Techo de viabilidad analítica δ_max = O_emp / θ* − 1.0000.

    θ* = O_fav / (O_fav − 1.0) es el umbral de breakeven sellado en [LN-QBE-050]. Por encima de
    δ_max la victoria del favorito dejaría de ser rentable (G_fav(δ) ≤ 0), violando la Invariante
    VIII-49: fuera del dominio viable se devuelve 0.0000 (degeneración al contrato defensivo).
    """
    if o_fav <= 1.0 or o_emp <= 1.0:
        return 0.0
    theta_estrella = calcular_umbral_theta_estrella(o_fav)
    if theta_estrella <= 0.0:
        return 0.0
    return round((o_emp / theta_estrella) - 1.0000, 4)


def calcular_delta_isorrendimiento(o_fav: float, o_emp: float) -> float:
    """[LN-QBE-077-D] δ* = (O_fav · O_emp) / (O_fav + O_emp) − 1.0000.

    Exige la condición de existencia del sub-símplex (Invariante VIII-51):
    (1.0/O_fav) + (1.0/O_emp) < 1.0000. Fuera de ese dominio no existe punto de doble cosecha
    simétrica y se devuelve δ = 0.0000 (degeneración al contrato defensivo sellado).
    """
    if o_fav <= 1.0 or o_emp <= 1.0:
        return 0.0
    if ((1.0 / o_fav) + (1.0 / o_emp)) >= 1.0000:
        return 0.0
    return round(((o_fav * o_emp) / (o_fav + o_emp)) - 1.0000, 4)


def calcular_particion_dutching_dinamico(
    b_total: float,
    o_fav: float,
    o_emp: float,
    modo: str = "DEF",
    delta_custom: float = 0.0,
    piso_min_boleto: float = 2.00
) -> Dict[str, Any]:
    """[LN-QBE-077-B / C / D] Partición de capital del Dutching con Cobertura Activa (V = δ > 0).

    Generaliza `calcular_dutching_v0` ([LN-QBE-070]) transformando el retorno de indemnidad pasiva
    ($0.00 MXN en tablas) en un retorno neto estrictamente positivo. Cero desviación del plano:

      1. Partición generalizada: B_seg(δ) = (1.0 + δ)·B_i / O_emp ; B_prio(δ) = B_i − B_seg(δ)
      2. Retornos proyectados: G_fav(δ) = B_prio·O_fav − B_i  [> 0 — Invariante VIII-49]
                              G_emp(δ) = δ·B_i                [δ ≥ 0 — Invariante VIII-50]
      3. Techo y clamping fiduciario ([LN-QBE-077-C]):
         δ_max = O_emp / θ* − 1.0000 ; δ_efectivo = max(0, min(δ, 0.95 · δ_max))
      4. Tríptico operativo ([LN-QBE-077-D]): `DEF` ⇒ δ = 0.0 (V=0) | `BAL` ⇒ δ = 0.50·δ*
         | `AGR` ⇒ δ = δ* | `CUSTOM` ⇒ δ = delta_custom (sujeto a clamping seguro).

    El piso legal de ventanilla (Invariante VIII-53) se DECLARA en `piso_ventanilla_insatisfecho`
    y jamás se clampa silenciosamente aquí: su reimposición es competencia del pase canónico de
    monotonía/piso de `PortfolioEngine.build_plan` ([LN-QBE-071] / [ARCH-1.4.19]), de modo que esta
    función permanece una ley PURA de partición (cero I/O, cero estado externo).
    """
    vacio: Dict[str, Any] = {
        "modo_resuelto": "DEF",
        "delta_solicitado": DELTA_DUTCHING_DEF,
        "delta_max": 0.0,
        "delta_isorrendimiento": 0.0,
        "delta_efectivo": DELTA_DUTCHING_DEF,
        "monto_seguro": 0.0,
        "monto_ataque": 0.0,
        "cobro_bruto_favorito": 0.0,
        "cobro_bruto_empate": 0.0,
        "pnl_neto_favorito": 0.0,
        "pnl_neto_empate": 0.0,
        "roi_favorito_porcentaje": 0.0,
        "roi_empate_porcentaje": 0.0,
        "piso_ventanilla_insatisfecho": False,
    }
    if b_total <= 0.0 or o_fav <= 1.0 or o_emp <= 1.0:
        return vacio

    modo_resuelto = str(modo or "DEF").strip().upper()
    delta_max = calcular_delta_max_analitico(o_fav, o_emp)
    delta_isorrendimiento = calcular_delta_isorrendimiento(o_fav, o_emp)

    if modo_resuelto == "BAL":
        delta_solicitado = round(RATIO_DELTA_BAL * delta_isorrendimiento, 4)
    elif modo_resuelto == "AGR":
        delta_solicitado = delta_isorrendimiento
    elif modo_resuelto == "CUSTOM":
        delta_solicitado = round(float(delta_custom or 0.0), 4)
    else:
        # `DEF` y cualquier modalidad no legislada degeneran al contrato defensivo sellado.
        modo_resuelto = "DEF"
        delta_solicitado = DELTA_DUTCHING_DEF

    # Invariante VIII-50 (δ ≥ 0.0) + [LN-QBE-077-C] δ_clamped = min(δ, 0.95 · δ_max).
    delta_efectivo = round(
        max(DELTA_DUTCHING_DEF, min(delta_solicitado, FACTOR_SEGURIDAD_DELTA_MAX * delta_max)), 4
    )

    # [LN-QBE-077-B].1 Partición generalizada de capital.
    b_seg = round(((1.0 + delta_efectivo) * b_total) / o_emp, 2)
    b_prio = round(b_total - b_seg, 2)

    cobro_fav = round(b_prio * o_fav, 2)
    cobro_emp = round(b_seg * o_emp, 2)
    pnl_fav = round(cobro_fav - b_total, 2)
    pnl_emp = round(cobro_emp - b_total, 2)

    return {
        "modo_resuelto": modo_resuelto,
        "delta_solicitado": delta_solicitado,
        "delta_max": delta_max,
        "delta_isorrendimiento": delta_isorrendimiento,
        "delta_efectivo": delta_efectivo,
        "monto_seguro": b_seg,
        "monto_ataque": b_prio,
        "cobro_bruto_favorito": cobro_fav,
        "cobro_bruto_empate": cobro_emp,
        "pnl_neto_favorito": pnl_fav,
        "pnl_neto_empate": pnl_emp,
        "roi_favorito_porcentaje": round((pnl_fav / b_total) * 100.0, 2),
        "roi_empate_porcentaje": round((pnl_emp / b_total) * 100.0, 2),
        # [GOVERNANCE-01] Cero silencios fiduciarios: la insuficiencia del piso se declara.
        "piso_ventanilla_insatisfecho": bool(b_seg < piso_min_boleto or b_prio < piso_min_boleto),
    }


def escalar_a_piso_ventanilla(b_total: float, o_emp: float, piso_min: float = 2.00) -> Tuple[float, float, float]:
    """[LN-QBE-071] Reescalado proporcional si el seguro cae por debajo de $2.00 MXN preservando V=0."""
    if o_emp <= 1.0 or b_total <= 0.0:
        return (0.0, 0.0, 0.0)
    b_seg_teorico = b_total / o_emp
    if b_seg_teorico < piso_min:
        b_seg = float(piso_min)
        b_total_reescalado = round(b_seg * o_emp, 2)
        b_prio = round(b_total_reescalado - b_seg, 2)
        return (b_prio, b_seg, b_total_reescalado)

    b_seg = round(b_seg_teorico, 2)
    b_prio = round(b_total - b_seg, 2)
    return (b_prio, b_seg, round(b_total, 2))


def calcular_ganancia_cobertura_v0(
    ganancia_directa: float,
    inversion: float,
    p_draw: float
) -> float:
    """
    [LN-QBE-073-B] Prima Canónica de la Transmutación D→H (erradicación del factor mágico 0.70).

    Derivación exacta a partir de la identidad del Dutching V=0 a cuotas soberanas justas:
      - La estructura directa revela la cuota implícita favorable: O_fav = 1 + g/B.
      - A cuotas justas, el seguro del empate absorbe su propia masa de probabilidad:
        b_seguro = B · p_draw  ⟹  b_primario = B · (1 − p_draw).
      - Ganancia neta de la estructura cubierta (V=0):
        g_cob = b_primario · O_fav − B = g · (1 − p_draw) − B · p_draw.

    Cero constantes empíricas: la prima emerge de la masa de probabilidad transferida al empate.
    """
    g = float(ganancia_directa or 0.0)
    b = float(inversion or 0.0)
    p_x = float(p_draw or 0.0)
    if b <= 0.0:
        return 0.0
    p_x = min(1.0, max(0.0, p_x))
    o_fav_implicita = 1.0 + (g / b)
    b_seguro = b * p_x
    b_primario = b - b_seguro
    return round((g * (1.0 - p_x)) - (b * p_x), 2)


def construir_veto_mercado_no_disponible() -> dict:
    """[LN-QBE-060-B / P1-3] Veto fiduciario único por ausencia o invalidez de cuotas."""
    return {
        "codigo": "QBE-00",
        "nombre": "Veto Fiduciario: Mercado no disponible",
        "alpha": 0.0,
        "pa": False,
        "motivo": "Cuotas comerciales ausentes o inválidas. Mercado suspendido o no capturado.",
    }


def triaje_determinista_9_estrategias(payload: dict, cuotas: dict, gamma: float = 0.67) -> dict:
    """[LN-QBE-060-B] Triaje determinista subordinado a la morfología Capa 0."""
    from src.core.simplex_morphology import clasificar_morfologia_simplex
    if not payload.get("es_operable", True) or payload.get("delta_epist", 0.0) > 0.12:
        return {"codigo": "QBE-00", "nombre": "Cuarentena Fiduciaria", "alpha": 0.0, "pa": False}

    # ── [P1-3 / Saneamiento O-05] Pureza de mercado: sin las tres cuotas fácticas no hay triaje.
    # Prohibidos los fallbacks, interpolaciones y proxies sintéticos de O_L, O_E u O_V.
    try:
        oL = float(cuotas["L"])
        oX = float(cuotas["E"])
        oV = float(cuotas["V"])
    except (KeyError, TypeError, ValueError):
        return construir_veto_mercado_no_disponible()
    if not all(math.isfinite(precio) and precio >= 1.0 for precio in (oL, oX, oV)):
        return construir_veto_mercado_no_disponible()

    p1, pX, p2 = payload["p_local"], payload["p_empate"], payload["p_visitante"]
    delta_epist = payload.get("delta_epist", 0.0)
    pa = bool(cuotas.get("pa", False) or cuotas.get("pago_anticipado", False))

    aL = p1 * oL - 1.0 if oL > 1.0 else -1.0
    aV = p2 * oV - 1.0 if oV > 1.0 else -1.0

    # [LN-QBE-007-H] Aduana de Sanidad Comercial de Overround
    if oL > 1.0 and oX > 1.0 and oV > 1.0:
        s_overround = (1.0 / oL) + (1.0 / oX) + (1.0 / oV)
        if s_overround < 0.8500 or s_overround > 1.3000:
            return {"codigo": "QBE-00", "nombre": "Cuarentena: Overround Anómalo", "alpha": 0.0, "pa": False}

    # -- CAPA 0: CLASIFICACION MORFOLOGICA CON EL PARAMETRO GAMMA DINAMICO --
    morf = clasificar_morfologia_simplex((p1, pX, p2), gamma=gamma)
    familia = morf.familia

    # 1. Directas Régimen I (Subordinadas a Hegemonía en Capa 0)
    if familia == "HEGEMONIA_LOCAL" and delta_epist <= 0.04 and aL > 0.05:
        return {"codigo": "QBE-D1", "nombre": "Directa Local", "alpha": aL, "pa": pa}
    if familia == "HEGEMONIA_VISITANTE" and delta_epist <= 0.04 and aV > 0.05:
        return {"codigo": "QBE-D2", "nombre": "Directa Visita", "alpha": aV, "pa": pa}

    # 2. Híbridas Dutching V=0 (Subordinadas a Asimetría en Capa 0)
    theta_1 = oL / (oL - 1.0) if oL > 1.0 else 99.0
    theta_2 = oV / (oV - 1.0) if oV > 1.0 else 99.0

    if familia == "ASIMETRIA_LOCAL" and oX > theta_1 and aL > 0:
        return {"codigo": "QBE-H1", "nombre": "Híbrida Local + Empate V=0", "alpha": aL, "pa": pa}

    # ── [LN-QBE-115] ESCUDO DE ALTITUD — precedencia estructural ANTES de exigir α_V > 0 ───────
    # Trampa fisiológica certificada ([LN-QBE-109] V28 unidireccional): la visita sube >= 1000 m
    # respecto de su plaza y el empate sigue vivo en tablas (O_X > θ2*). El diferencial ausente
    # vale 0.0: sin evidencia de altitud NO se evalúa el escudo ni se fabrica un veto
    # (`[GOVERNANCE-01]`). La aduana de altitud es morfológica + de existencia de Dutching.
    if familia == "ASIMETRIA_VISITANTE":
        delta_alt_metros = float(payload.get("delta_alt_metros", 0.0) or 0.0)
        if delta_alt_metros >= UMBRAL_VETO_ALTITUD_METROS and oX > theta_2:
            return {
                "codigo": "QBE-00",
                "nombre": "Veto Fiduciario: Trampa de Altitud Visitante",
                "alpha": 0.0,
                "pa": False,
                "motivo": "Veto Fiduciario: Trampa de Altitud Visitante (Delta Alt >= 1000m)",
                "arquetipo_veto": "TRAMPA_ALTITUD",
            }

    if familia == "ASIMETRIA_VISITANTE" and oX > theta_2 and aV > 0:
        # ── [LN-QBE-116] COTA DE DOMINANCIA P' >= 50% ────────────────────────────────────────
        # Blindaje quirúrgico de la ruta H2: el ataque descansa sobre un favorito foráneo que
        # el propio modelo NO considera mayoritario. Opera después del Escudo de Altitud
        # (precedencia estructural del hecho fisiológico certificado) y ANTES de emitir la
        # Híbrida Visitante. Borde exacto: 0.5000 no veta.
        if p2 < UMBRAL_DOMINANCIA_VISITANTE_PCT:
            return {
                "codigo": "QBE-00",
                "nombre": "Veto Fiduciario: Ruptura de Dominancia Visitante",
                "alpha": 0.0,
                "pa": False,
                "motivo": "Veto Fiduciario: Dominancia Visitante (P_visitante < 50%)",
                "arquetipo_veto": "RUPTURA_DOMINANCIA",
            }
        return {"codigo": "QBE-H2", "nombre": "Híbrida Visita + Empate V=0", "alpha": aV, "pa": pa}

    # 3. Underdogs Familia R (Subordinados estrictamente a Capa 0: prohibido en Asimetrías opuestas y Bipolaridad)
    if familia not in ("ASIMETRIA_VISITANTE", "HEGEMONIA_VISITANTE", "BIPOLARIDAD_TERRITORIAL") and p1 >= 0.20 and oL >= 3.50 and aL >= 0.20 and delta_epist <= 0.05:
        return {"codigo": "QBE-R1", "nombre": "Reversa Local Underdog", "alpha": aL, "pa": pa}
    if familia not in ("ASIMETRIA_LOCAL", "HEGEMONIA_LOCAL", "BIPOLARIDAD_TERRITORIAL") and p2 >= 0.20 and oV >= 3.50 and aV >= 0.20 and delta_epist <= 0.05:
        return {"codigo": "QBE-R2", "nombre": "Reversa Visita Underdog", "alpha": aV, "pa": pa}

    # 4. Mutación DNB si el empate fue caníbal en Asimetrías
    if familia in ("ASIMETRIA_LOCAL", "ASIMETRIA_VISITANTE"):
        p_fav = p1 if familia == "ASIMETRIA_LOCAL" else p2
        p_und = p2 if familia == "ASIMETRIA_LOCAL" else p1
        o_fav = oL if familia == "ASIMETRIA_LOCAL" else oV
        p_dnb = p_fav / (p_fav + p_und) if (p_fav + p_und) > 0 else 0.0
        # [GOVERNANCE-01] Cero cuotas sintéticas: sin precio DNB fáctico no hay mutación QBE-C1.
        # Saneamiento O-01 (Censo de Huérfanos): erradicada la fabricación `o_fav * 0.75`.
        o_dnb = float(cuotas.get("DNB", 0.0) or 0.0)
        if o_dnb > 1.0 and (p_dnb * o_dnb - 1.0) > 0.05:
            return {"codigo": "QBE-C1", "nombre": "Cobertura DNB", "alpha": (p_dnb * o_dnb - 1.0), "pa": False}

    # 5. Totales / Bajas
    p_under = payload.get("p_under_25", 0.0)
    o_under = cuotas.get("Under_25", 0.0)
    if o_under > 1.0 and (p_under * o_under - 1.0) > 0.06:
        return {"codigo": "QBE-C2", "nombre": "Cobertura Derivada Totales", "alpha": (p_under * o_under - 1.0), "pa": False}

    # 6. Paridad Ciega o Sin Valor
    # ── [LN-QBE-060-C] ADUANA DE VETO FIDUCIARIO INTELIGENTE ANTI-RUPTURA (QBE-00) ─────────────
    # Última frontera del triaje: el veredicto vacío se CALIFICA con el arquetipo de ruptura
    # demostrado (Falsa Paridad / Bipolar de Fuego) y la calificación viaja en la traza como
    # `arquetipo_veto` ('FALSA_PARIDAD' / 'BIPOLAR_FUEGO'), preservando el capital en escenarios
    # de alta entropía o de fuego ingobernable. Invariante de alcance: la aduana opera
    # EXCLUSIVAMENTE sobre el veredicto vacío; las estrategias canónicas selladas por
    # `[LN-QBE-060-B]` (D1/D2/H1/H2/R1/R2/C1/C2) son resueltas aguas arriba y no pueden ser
    # suprimidas aquí.
    p_max_veto = max(p1, pX, p2)
    delta_p_veto = p_max_veto - min(p1, pX, p2)

    # 6.1 Veto de Falsa Paridad / Alta Entropía (Arquetipo 4): ΔP estrecho y masa sin convicción.
    if delta_p_veto <= DELTA_P_PARIDAD_VETO and p_max_veto <= PMAX_MIN_OPERABLE:
        return {
            "codigo": "QBE-00",
            "nombre": "Veto Anti-Ruptura: Falsa Paridad (Alta Entropía)",
            "alpha": 0.0,
            "pa": False,
            "motivo": "Veto Fiduciario: Falsa Paridad / Alta Entropía (Delta P <= 12%)",
            "arquetipo_veto": "FALSA_PARIDAD",
        }

    # 6.2 Veto de Bipolar de Fuego (Arquetipo 3): Σλ ≥ 3.00 xG con empate asfixiado en el 1X2.
    #     El desvío táctico corresponde al mercado derivado de totales (C2), no a esta ventanilla.
    lambda_fuego_veto = float(payload.get("lambda_home", 0.0) or 0.0) \
        + float(payload.get("lambda_away", 0.0) or 0.0)
    if lambda_fuego_veto >= LAMBDA_SUMA_FUEGO_VETO \
            and pX <= P_EMPATE_FUEGO_TECHO and p_max_veto < 0.5000:
        return {
            "codigo": "QBE-00",
            "nombre": "Veto Anti-Ruptura: Bipolar de Fuego",
            "alpha": 0.0,
            "pa": False,
            "motivo": "Veto Fiduciario: Bipolar de Fuego (Desvío a Mercado Derivado de Altas C2)",
            "arquetipo_veto": "BIPOLAR_FUEGO",
        }
    return {"codigo": "QBE-00", "nombre": "Cuarentena / Sin Valor", "alpha": 0.0, "pa": False}


def calcular_ranking_friccion(partidos: List[dict]) -> List[dict]:
    """[LN-QBE-073-B] Ordenamiento por Calidad Distributiva descendente."""
    for p in partidos:
        alpha = max(0.0, float(p.get("alpha", 0.0)))
        delta_epist = max(0.0, float(p.get("delta_epist", 0.0)))
        psi = max(0.0, 1.0 - (delta_epist / 0.12) ** 2) if delta_epist <= 0.12 else 0.0
        score = (alpha / (delta_epist + 0.01)) * psi if p.get("codigo") != "QBE-00" else 0.0
        p["score_friccion"] = round(score, 4)
        p["psi_epist"] = round(psi, 4)
    return sorted(partidos, key=lambda x: x["score_friccion"], reverse=True)


def calcular_kelly_atenuado(p: float, o: float, delta_epist: float, gamma_kelly: float = 0.25) -> float:
    """[LN-QBE-070-B] Kelly Fraccional modulado por atenuación cuadrática de incertidumbre."""
    alpha = calcular_alpha_edge(p, o)
    if alpha <= 0.0 or o <= 1.0:
        return 0.0
    f_puro = alpha / (o - 1.0)
    psi = max(0.0, 1.0 - (delta_epist / 0.12) ** 2) if delta_epist <= 0.12 else 0.0
    f_adj = gamma_kelly * f_puro * psi
    return round(max(0.0, min(0.08, f_adj)), 4)


def aplicar_hard_caps_constitucionales(inversiones: List[float], bankroll: float) -> List[float]:
    """[LN-QBE-070-B] Aplica techo individual (8.0%) y prorrateo global de jornada (25.0%)."""
    if bankroll <= 0.0 or not inversiones:
        return [0.0] * len(inversiones)
    cap_indiv = bankroll * 0.0800
    cap_global = bankroll * 0.2500

    # 1. Cap individual
    acotadas = [min(max(0.0, float(inv)), cap_indiv) for inv in inversiones]
    total_inv = sum(acotadas)

    # 2. Cap global prorrateado
    if total_inv > cap_global and total_inv > 0.0:
        escala = cap_global / total_inv
        return [round(inv * escala, 2) for inv in acotadas]
    return [round(inv, 2) for inv in acotadas]


def evaluar_tradeoff_pago_anticipado(
    o_pa: float,
    o_vanilla: float,
    p_fav: float,
    delta_freeroll: float
) -> Dict[str, Any]:
    """
    [LN-QBE-077] Cuantifica analíticamente si conviene tomar la cuota con Pago Anticipado (+PA)
    o la cuota nominal más alta sin la promoción.
    """
    if o_pa <= 1.0 or o_vanilla <= 1.0 or p_fav <= 0.0:
        return {"recomendar_pa": False, "ev_pa": -1.0, "ev_vanilla": -1.0, "cuota_indiferencia": 99.0}

    p_pa = p_fav + delta_freeroll
    ev_pa = round(p_pa * o_pa - 1.0, 4)
    ev_vanilla = round(p_fav * o_vanilla - 1.0, 4)
    o_indif = round(o_vanilla * (p_fav / p_pa), 4)

    return {
        "recomendar_pa": ev_pa > ev_vanilla,
        "ev_pa": ev_pa,
        "ev_vanilla": ev_vanilla,
        "cuota_indiferencia": o_indif,
        "delta_ev": round(ev_pa - ev_vanilla, 4)
    }


def resolver_mejor_combinacion_cuotas(
    cuotas_operadores: Dict[str, Dict[str, Any]],
    fav: str = "L"
) -> Dict[str, Any]:
    """
    [LN-QBE-076] Resuelve la Mejor Combinación Cross-Market: selecciona el operador
    que maximiza la cuota del Favorito (Ataque) y el operador que maximiza el Empate (Seguro).
    """
    best_ataque = {"operador": "caliente", "momio": 0.0, "pa": False}
    best_seguro = {"operador": "caliente", "momio": 0.0, "pa": False}

    key_fav = "L" if fav.upper() in ("L", "LOCAL", "1") else "V"

    for op_name, m in cuotas_operadores.items():
        if not m:
            continue
        m_fav = float(m.get(key_fav, 0.0))
        m_emp = float(m.get("E", 0.0))
        pa_val = bool(m.get("pa", False) or m.get("pago_anticipado", False))

        if m_fav > best_ataque["momio"]:
            best_ataque = {"operador": op_name, "momio": m_fav, "pa": pa_val}

        if m_emp > best_seguro["momio"]:
            best_seguro = {"operador": op_name, "momio": m_emp, "pa": pa_val}

    return {
        "ataque": best_ataque,
        "seguro": best_seguro,
        "fav_key": key_fav
    }


# [LN-QBE-071].1 + [LN-QBE-076] Posiciones BIVARIADAS con pierna de cobertura en tablas.
# Familias R incluidas por mandato de la Enmienda Universal: R1 lleva seguro de Empate
# ([LN-QBE-071].1) y R2 escala AMBOS boletos al piso ([LN-QBE-071].3).
FAMILIAS_CON_COBERTURA: Tuple[str, ...] = ("QBE-H1", "QBE-H2", "QBE-R1", "QBE-R2")


def aplicar_hard_caps_con_respeto_a_piso(
    ordenes: List[Dict[str, Any]],
    bankroll: float,
    cap_partido_pct: float = 0.08,
    cap_cartera_pct: float = 0.25,
    piso_min_boleto: float = 2.00
) -> List[Dict[str, Any]]:
    """[LN-QBE-070-E] Prorratea el capital respetando el piso de ventanilla ($2.00 MXN).

    Doctrina sellada (docs/LOGIC.md [LN-QBE-070-E].2 y .3):
      1. escala = (0.25·Bankroll) / ΣB_i.
      2. PISO NATURAL: la inversión de toda orden de cobertura no puede quedar por debajo de
         piso · odd_emp (el seguro B_i/odd_emp debe alcanzar la ventanilla) ni de 2 · piso
         (dos piernas admisibles de $2.00, [LN-QBE-071].3 lo deriva para R2 con k = piso/min(B1,B2)).
      3. PRORRATEO CON HOLGURA: el déficit de la escala se rescata con el SUPERÁVIT del libro; las
         órdenes por encima de su propio piso ceden excedente y jamás cruzan su piso. Σ B_i es un
         invariante de la transferencia: el tope del 25.0% no se infla jamás.
      4. Si el superávit no alcanza (libro sin holgura), el tope —ley monetaria— prevalece y se
         aplica el clamping fiduciario (B_seg = piso, residual al boleto de ataque) declarando la
         insuficiencia de forma transparente (`piso_ventanilla_natural_insatisfecho` /
         `piso_bivariado_insatisfecho`): cero silencios fiduciarios ([GOVERNANCE-01]).
    """
    if bankroll <= 0.0 or not ordenes:
        return ordenes

    cap_max_partido = round(bankroll * cap_partido_pct, 2)
    cap_max_cartera = round(bankroll * cap_cartera_pct, 2)
    piso_bivariado = round(2.0 * piso_min_boleto, 2)

    # 1. Aplicar tope individual
    for ord_item in ordenes:
        inv = float(ord_item.get("inversion_total", 0.0))
        if inv > cap_max_partido:
            ord_item["inversion_total"] = cap_max_partido

    total_inv = sum(float(o.get("inversion_total", 0.0)) for o in ordenes)

    # 2. Prorrateo global si excede el 25% del bankroll
    if total_inv > cap_max_cartera and total_inv > 0.0:
        factor_escala = cap_max_cartera / total_inv
        piso_natural: Dict[int, float] = {}
        for indice, ord_item in enumerate(ordenes):
            inv_inicial = float(ord_item.get("inversion_total", 0.0))
            nueva_inv = round(inv_inicial * factor_escala, 2)
            ord_item["inversion_total"] = nueva_inv

            codigo = str(ord_item.get("strategy_code", "")).upper().strip()
            if codigo in FAMILIAS_CON_COBERTURA and nueva_inv > 0.0:
                if (
                    "odd_emp" not in ord_item
                    or ord_item["odd_emp"] is None
                    or float(ord_item["odd_emp"]) <= 1.0
                ):
                    raise ValueError(
                        "[O-06] La orden requiere un 'odd_emp' válido para el reescalado al piso de ventanilla."
                    )
                o_emp = float(ord_item["odd_emp"])
                # Piso NATURAL ([LN-QBE-070-E].2): inversión mínima para que el seguro
                # (B_i / odd_emp) alcance la ventanilla, con dos piernas admisibles como suelo.
                piso_natural[indice] = max(round(piso_min_boleto * o_emp, 2), piso_bivariado)

        # 3. RESCATE DEL PISO NATURAL (prorrateo con holgura): el déficit de las órdenes
        #    comprimidas se financia con el SUPERÁVIT de las que quedaron por encima de su
        #    propio piso, jamás cruzando éste. Σ B_i es invariante de la transferencia: el
        #    tope de cartera no se infla y el seguro de ventanilla no colapsa.
        for indice, piso in sorted(piso_natural.items(), key=lambda par: -par[1]):
            falta = round(piso - float(ordenes[indice]["inversion_total"]), 2)
            if falta <= 0.0:
                continue
            donantes = sorted(
                [j for j, piso_j in piso_natural.items()
                 if j != indice and float(ordenes[j]["inversion_total"]) - piso_j > 0.0],
                key=lambda j: float(ordenes[j]["inversion_total"]) - piso_natural[j],
                reverse=True,
            )
            for j in donantes:
                if falta <= 0.0:
                    break
                holgura = round(float(ordenes[j]["inversion_total"]) - piso_natural[j], 2)
                cesion = min(holgura, falta)
                if cesion <= 0.0:
                    continue
                ordenes[j]["inversion_total"] = round(
                    float(ordenes[j]["inversion_total"]) - cesion, 2
                )
                ordenes[indice]["inversion_total"] = round(
                    float(ordenes[indice]["inversion_total"]) + cesion, 2
                )
                falta = round(falta - cesion, 2)

        # 4. CLAMPING FIDUCIARIO: si tras el rescate el seguro comprimido sigue bajo el piso (libro
        #    sin superávit: el tope —ley monetaria— prevalece), se fija B_seg = piso y el residual
        #    queda en el boleto de ataque, declarándose con transparencia total ([GOVERNANCE-01]).
        #    La suma de ambas piernas reproduce la inversión prorrateada: cero inflación.
        for indice, ord_item in enumerate(ordenes):
            if indice not in piso_natural:
                continue
            inv = float(ord_item["inversion_total"])
            if (
                "odd_emp" not in ord_item
                or ord_item["odd_emp"] is None
                or float(ord_item["odd_emp"]) <= 1.0
            ):
                raise ValueError(
                    "[O-06] La orden requiere un 'odd_emp' válido para el reescalado al piso de ventanilla."
                )
            o_emp = float(ord_item["odd_emp"])
            seguro_teorico = round(inv / o_emp, 2) if o_emp > 1.0 else 0.0
            if seguro_teorico < piso_min_boleto or inv < piso_bivariado:
                b_seg = float(piso_min_boleto)
                b_prio = round(max(0.0, inv - b_seg), 2)
                ord_item["boleto_seguro"] = b_seg
                ord_item["boleto_ataque"] = b_prio
                ord_item["piso_ventanilla_aplicado"] = True
                if seguro_teorico < piso_min_boleto:
                    # El seguro natural no alcanzó la ventanilla: rescate parcial declarado.
                    ord_item["piso_ventanilla_natural_insatisfecho"] = True
                if round(inv, 2) < piso_bivariado or b_prio < piso_min_boleto:
                    # Ni dos piernas admisibles caben en el tope: la promesa bivariada se declara.
                    ord_item["piso_bivariado_insatisfecho"] = True

        # 5. Garantía analítica del tope: el centavo de exceso por redondeo se recorta primero de
        #    la holgura de las órdenes por encima de su piso natural, luego de las órdenes sin
        #    cobertura y sólo en último término del boleto de ataque (declarándolo). El 25.0% es
        #    inviolable; el recorte nunca cruza el piso natural si hay alternativa.
        exceso = round(sum(float(o.get("inversion_total", 0.0)) for o in ordenes) - cap_max_cartera, 2)
        if exceso > 0.0:
            candidatos = sorted(
                [i for i in piso_natural
                 if float(ordenes[i]["inversion_total"]) - piso_natural[i] > 0.0],
                key=lambda i: float(ordenes[i]["inversion_total"]) - piso_natural[i],
                reverse=True,
            )
            for i in candidatos:
                if exceso <= 0.0:
                    break
                holgura = round(float(ordenes[i]["inversion_total"]) - piso_natural[i], 2)
                recorte = min(holgura, exceso)
                if recorte <= 0.0:
                    continue
                ordenes[i]["inversion_total"] = round(
                    float(ordenes[i]["inversion_total"]) - recorte, 2
                )
                exceso = round(exceso - recorte, 2)
            for i, ord_item in enumerate(ordenes):
                if exceso <= 0.0:
                    break
                if i in piso_natural:
                    continue
                recorte = min(float(ord_item.get("inversion_total", 0.0)), exceso)
                if recorte <= 0.0:
                    continue
                ord_item["inversion_total"] = round(
                    float(ord_item.get("inversion_total", 0.0)) - recorte, 2
                )
                exceso = round(exceso - recorte, 2)
            for ord_item in ordenes:
                if exceso <= 0.0:
                    break
                if "boleto_ataque" not in ord_item:
                    continue
                recorte = min(
                    round(float(ord_item["boleto_ataque"]) - piso_min_boleto, 2),
                    exceso,
                )
                if recorte <= 0.0:
                    continue
                ord_item["boleto_ataque"] = round(float(ord_item["boleto_ataque"]) - recorte, 2)
                ord_item["inversion_total"] = round(
                    float(ord_item["boleto_seguro"]) + float(ord_item["boleto_ataque"]), 2
                )
                exceso = round(exceso - recorte, 2)
                if float(ord_item["boleto_ataque"]) < piso_min_boleto:
                    ord_item["piso_bivariado_insatisfecho"] = True

    return ordenes


# ═══════════════════════════════════════════════════════════════════════════════════════
# [VAULT-CORE-079-SHRINKAGE] Contracción Baricéntrica y Ordenamiento Monótono
# Firma: SHA256-VAULT-CORE-BARYCENTRIC-SHRINKAGE-001
# [LN-QBE-079] / [LN-QBE-081] / [LN-QBE-082] — Transcripción canónica VERBATIM.
# Nota de trazabilidad: el bloque fue inyectado como [LN-QBE-080]/[LN-QBE-081] y remapeado
# a [LN-QBE-081]/[LN-QBE-082] por colisión con el nodo sellado [LN-QBE-080] (Compilador PDF A4).
# Ver VAR-HIST-080-COLLISION
# ═══════════════════════════════════════════════════════════════════════════════════════


def contraer_distribucion_fiduciaria(
    p_l: float, p_e: float, p_v: float, delta_epist: float
) -> Tuple[float, float, float]:
    """[LN-QBE-079] Contracción convexa hacia el baricentro (1/3, 1/3, 1/3) modulada por incertidumbre."""
    delta = max(0.0, float(delta_epist))
    psi = max(0.0, 1.0 - (delta / 0.12) ** 2) if delta <= 0.12 else 0.0
    p0 = 1.0 / 3.0
    p_l_c = round(psi * p_l + (1.0 - psi) * p0, 4)
    p_e_c = round(psi * p_e + (1.0 - psi) * p0, 4)
    p_v_c = round(1.0 - p_l_c - p_e_c, 4)
    return (p_l_c, p_e_c, p_v_c)


def calcular_probabilidad_exito_estrategia(
    codigo_estrategia: str, p_fav_p: float, p_emp_p: float, p_und_p: float = 0.0
) -> float:
    """[LN-QBE-081] Calcula la probabilidad efectiva de éxito según la estructura de cobertura."""
    cod = str(codigo_estrategia).upper().replace("+", "").strip()
    if cod in ("QBE-H1", "QBE-H2"):
        return round(p_fav_p + p_emp_p, 4)
    elif cod in ("QBE-D1", "QBE-D2"):
        return round(p_fav_p, 4)
    elif cod in ("QBE-R1", "QBE-R2"):
        return round(p_und_p, 4)
    elif cod == "QBE-C1":
        denom = p_fav_p + p_und_p
        if denom <= 0:
            return 0.0
        return round(p_fav_p / denom, 4)
    return 0.3333


def ordenar_cartera_por_certeza_lexicografica(partidos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """[LN-QBE-081] Ordena: 1° Probabilidad Efectiva de Éxito (desc), 2° Ganancia Neta (desc)."""
    return sorted(
        partidos,
        key=lambda x: (
            round(float(x.get("prob_exito_efectiva", 0.0)), 4),
            round(float(x.get("ganancia_neta", 0.0)), 2)
        ),
        reverse=True
    )


def asignar_capital_monotono_cartera(
    partidos_ordenados: List[Dict[str, Any]],
    bankroll: float,
    cap_max_partido_pct: float = 0.08,
    cap_max_cartera_pct: float = 0.25
) -> List[Dict[str, Any]]:
    """[LN-QBE-082] Asigna capital en degradé monótono no creciente según la certeza."""
    if bankroll <= 0.0 or not partidos_ordenados:
        return partidos_ordenados

    K = len(partidos_ordenados)
    cap_max_partido = round(bankroll * cap_max_partido_pct, 2)
    bolsa_disponible = round(bankroll * cap_max_cartera_pct, 2)
    cap_underdog = round(bankroll * CAP_UNDERDOG_LEY3_PCT, 2)

    probabilidades = [max(0.01, float(p.get("prob_exito_efectiva", 0.33))) for p in partidos_ordenados]
    suma_prob = sum(probabilidades)
    pesos = [pr / suma_prob for pr in probabilidades]

    for idx, p in enumerate(partidos_ordenados):
        inv_teorica = round(bolsa_disponible * pesos[idx], 2)
        asignado = min(cap_max_partido, max(5.00, inv_teorica))
        # [LN-QBE-115] Cota Underdog Ley 3: techo EXCLUSIVO de la Familia R. La cota de la
        # jornada la dicta `CAP_UNDERDOG_LEY3_PCT` sobre el bankroll vigente B_j; la monotonía y
        # el prorrateo posteriores sólo pueden reducir, jamás violar el techo.
        familia_orden = str(p.get("familia") or p.get("estrategia_codigo") or "").upper()
        if familia_orden in FAMILIAS_UNDERDOG_LEY3:
            asignado = min(asignado, cap_underdog)
        p["inversion_total"] = round(asignado, 2)

    # Forzar monotonía no creciente: B_(1) >= B_(2) >= ... >= B_(K)
    for i in range(1, K):
        if partidos_ordenados[i]["inversion_total"] > partidos_ordenados[i-1]["inversion_total"]:
            partidos_ordenados[i]["inversion_total"] = partidos_ordenados[i-1]["inversion_total"]

    # Prorrateo si excede el tope de cartera
    total_inv = sum(float(p["inversion_total"]) for p in partidos_ordenados)
    if total_inv > bolsa_disponible and total_inv > 0:
        escala = bolsa_disponible / total_inv
        for p in partidos_ordenados:
            p["inversion_total"] = round(float(p["inversion_total"]) * escala, 2)

    return partidos_ordenados


# ─────────────────────────────────────────────────────────────────────────────
# [ARCH-1.4.30] EXTENSIÓN AUTORIZADA POR EL DIRECTOR (PASO 3, Directiva Táctica de
# Materialización). Contrato Pydantic del dimensionamiento de cartera: bankroll, Slider
# de Certeza y el parámetro interactivo de concentración de masa Γ (Capa 0).
#
# RÉGIMEN: [DBBD-FUNGIBLE] — DTO de transferencia de estado (no es aritmética sellada).
# NOTA DE GOBERNANZA: se anexa al FINAL del módulo (import diferido) para preservar
# íntegros los anclajes de línea del plano canónico [ARCH-1.4.9] (p. ej. la fórmula
# Ψ = 1 − (Δ/0.12)² citada como "portfolio_math.py L139" desde markets.py).
# ─────────────────────────────────────────────────────────────────────────────
from pydantic import BaseModel, ConfigDict


class PortfolioParameters(BaseModel):
    """[ARCH-1.4.30] Parámetros gobernantes del dimensionamiento de cartera."""
    model_config = ConfigDict(extra="ignore")
    total_bankroll: float
    certainty_slider: float = 0.80
    gamma_threshold: float = 0.67


# ─────────────────────────────────────────────────────────────────────────────
# [LN-QBE-025-B] & [ARCH-1.4.35] EXTENSIÓN AUTORIZADA POR EL DIRECTOR (PASO 3).
# Liquidador Post-Evento del Backtesting Fiduciario: contrasta una orden histórica del
# plan contra el marcador final REAL emitido por el oráculo y devuelve el PnL neto
# bancario. Es aritmética sellada: cero E/S, cero números mágicos, cero heurística.
#
# RÉGIMEN: [DIRGEN-STRICT] — Transcripción de las ecuaciones legisladas en el Libro
# Primero [LN-QBE-025-B §3]. Un cambio de coma exige nueva Directiva.
# NOTA DE GOBERNANZA: se anexa al FINAL del módulo (mismo precedente que [ARCH-1.4.30])
# para preservar ÍNTEGROS los anclajes de línea del plano canónico [ARCH-1.4.9]
# (p. ej. la fórmula Ψ = 1 − (Δ/0.12)² citada como "portfolio_math.py L139").
# ─────────────────────────────────────────────────────────────────────────────


def _resolver_familia_cobertura(orden: Dict[str, Any]) -> Optional[str]:
    """[LN-QBE-077-B] Resuelve el código canónico de estrategia del contrato plano de liquidación.

    Acepta `strategy_code` (contrato plano interno consumido por `aplicar_hard_caps_*`) o
    `estrategia_seleccionada.codigo` (contrato EMITIDO por el motor de cartera). Devuelve `None`
    cuando el transporte es LEGADO —ninguna de las dos claves viaja—: en ese caso el liquidador
    preserva la ley sellada V=0 (`TABLAS_V0`) en lugar de inventar una pérdida total, honrando el
    principio de cero liquidaciones fabricadas ([GOVERNANCE-01]).
    """
    crudo = orden.get("strategy_code")
    if crudo is None:
        seleccion = orden.get("estrategia_seleccionada")
        if isinstance(seleccion, dict):
            crudo = seleccion.get("codigo")
    if crudo is None:
        return None
    codigo = str(crudo).upper().replace("+", "").strip()
    return codigo or None


def _roi_real_porcentaje(pnl_neto: float, inversion: float) -> float:
    """[LN-QBE-025-B] ROI real bancario (%), sin división por cero."""
    if inversion <= 0.0:
        return 0.0
    return round((pnl_neto / inversion) * 100.0, 2)


def liquidar_orden_post_evento(
    orden: Dict[str, Any],
    home_score: int,
    away_score: int,
) -> Dict[str, Any]:
    """[LN-QBE-025-B §3] Liquidación real (Real vs. Predicho) de una orden histórica.

    Ecuaciones legisladas — cero desviación:
      - Gana el Favorito respaldado: PnL = B_prio * O_fav - B_total
      - Empate con cobertura V=0:    PnL = B_seg  * O_emp - B_total  (≡ $0.00 MXN)
      - Empate con COSECHA ACTIVA:   PnL = (1.0 + δ)·B_i - B_total = δ·B_i > 0  [ARCH-1.4.37]
      - Gana el Underdog:            PnL = -B_total

    `seleccion_favorito` es la identidad de la pierna Ataque ("LOCAL" | "VISITA");
    el marcador final decide el desenlace sin transformar ninguna probabilidad.

    [ARCH-1.4.37] Cuando el empate acaece sobre una orden que portaba δ > 0
    (`delta_cobertura`) en una familia con cobertura ([LN-QBE-077-B]), el cobro bruto devengado
    (1.0 + δ)·B_i se acredita con el estado `COBRADO_SEGURO_DELTA`. Las familias SIN cobertura
    (D1/D2/C1/QBE-00) consumen el stake íntegro en tablas (estado `FALLO`, cobro $0.00 MXN).
    """
    inversion_total = round(float(orden.get("inversion_total", 0.0) or 0.0), 2)
    monto_ataque = float(orden.get("monto_ataque", 0.0) or 0.0)
    cuota_ataque = float(orden.get("cuota_ataque", 0.0) or 0.0)
    monto_seguro = float(orden.get("monto_seguro", 0.0) or 0.0)
    cuota_seguro = float(orden.get("cuota_seguro", 0.0) or 0.0)
    favorito_local = str(orden.get("seleccion_favorito", "LOCAL")).strip().upper() == "LOCAL"

    if home_score == away_score:
        # Escenario TABLAS: se cobra la pierna de cobertura.
        # [LN-QBE-077-B] / [ARCH-1.4.37] Cosecha Activa: si la orden viajó con δ > 0 la cobertura
        # devenga (1.0 + δ)·B_i y el veredicto se eleva a `COBRADO_SEGURO_DELTA`; con δ = δ_def
        # subsiste la ley sellada V=0 (indemnidad pasiva ⇒ `TABLAS_V0`).
        retorno_bruto = round(monto_seguro * cuota_seguro, 2)
        familia = _resolver_familia_cobertura(orden)
        delta_cobertura = float(orden.get("delta_cobertura", DELTA_DUTCHING_DEF) or 0.0)

        if familia is not None and familia not in FAMILIAS_CON_COBERTURA:
            # Familia SIN cobertura en empate (D1/D2/C1/QBE-00): el stake se consume íntegro.
            retorno_bruto = 0.0
            estado = "FALLO"
        elif delta_cobertura > UMBRAL_DELTA_COSECHA_ACTIVA and retorno_bruto > inversion_total:
            estado = "COBRADO_SEGURO_DELTA"
        else:
            estado = "TABLAS_V0"

        pnl_neto = round(retorno_bruto - inversion_total, 2)
        return {
            "estado": estado,
            "pnl_neto_mxn": pnl_neto,
            "retorno_bruto_mxn": retorno_bruto,
            "inversion_mxn": inversion_total,
            "roi_real_porcentaje": _roi_real_porcentaje(pnl_neto, inversion_total),
        }

    if (home_score > away_score) == favorito_local:
        # Escenario PLENO ÉXITO: se cobra la pierna Ataque respaldada.
        retorno_bruto = round(monto_ataque * cuota_ataque, 2)
        pnl_neto = round(retorno_bruto - inversion_total, 2)
        return {
            "estado": "COBRADO_ATAQUE",
            "pnl_neto_mxn": pnl_neto,
            "retorno_bruto_mxn": retorno_bruto,
            "inversion_mxn": inversion_total,
            "roi_real_porcentaje": _roi_real_porcentaje(pnl_neto, inversion_total),
        }

    # Escenario FALLO: el desenlace no cubierto consume el stake íntegro.
    return {
        "estado": "FALLO",
        "pnl_neto_mxn": round(-inversion_total, 2),
        "retorno_bruto_mxn": 0.0,
        "inversion_mxn": inversion_total,
        "roi_real_porcentaje": _roi_real_porcentaje(round(-inversion_total, 2), inversion_total),
    }


# ── [VAULT-CORE-007-C / LN-QBE-100] CALIBRACIÓN FACTUAL DE TEMPORADA ─────────
# [DIRGEN-STRICT] Transparencia verbatim de bóveda: cero margen creativo.


def desmarcar_cuotas_proporcional(oL: float, oX: float, oV: float) -> Tuple[float, float, float]:
    """
    [VAULT-CORE-007-C] [DIRGEN-STRICT] Desmarque proporcional de vig (consenso Vig-Free).

    Extrae el consenso de probabilidad sin comisión de la casa desde el trío de cuotas 1X2
    de ventanilla, repartiendo el sobreprecio (overround) en proporción exacta a la
    probabilidad implícita bruta:

        S  = 1/oL + 1/oX + 1/oV      (sobreprecio; S > 1.0 cuando hay comisión)
        q_k = (1/o_k) / S            (k ∈ {L, X, V})

    Guarda fiduciaria [GOVERNANCE-01]: un trío incompleto o degenerado (cualquier cuota
    <= 1.0) NO se repara ni se inventa; se degrada a la ignorancia máxima uniforme
    (1/3, 1/3, 1/3).

    Returns:
        Tupla `(q_LOCAL, q_EMPATE, q_VISITANTE)` que clausura en 1.0 (redondeo a 4 decimales).
    """
    try:
        o_l, o_x, o_v = float(oL), float(oX), float(oV)
    except (TypeError, ValueError):
        return (round(1.0 / 3.0, 4), round(1.0 / 3.0, 4), round(1.0 / 3.0, 4))

    if o_l <= 1.0 or o_x <= 1.0 or o_v <= 1.0:
        return (round(1.0 / 3.0, 4), round(1.0 / 3.0, 4), round(1.0 / 3.0, 4))

    inversas = (1.0 / o_l, 1.0 / o_x, 1.0 / o_v)
    sobreprecio = inversas[0] + inversas[1] + inversas[2]
    q_local = round(inversas[0] / sobreprecio, 4)
    q_empate = round(inversas[1] / sobreprecio, 4)
    q_visitante = round(1.0 - q_local - q_empate, 4)
    return (q_local, q_empate, q_visitante)


def calcular_brier_multicategorico(partidos: List[Dict[str, Any]]) -> float:
    """
    [LN-QBE-100] [DIRGEN-STRICT] Brier Score Multicategórico 1X2.

    Penaliza por igual la sobreconfianza y la subconfianza sobre las 3 casillas del
    mercado (1, X, 2) con normalización 3N:

        BS = (1 / 3N) · Σ_i Σ_{k ∈ {1, X, 2}} (p_{i,k} - y_{i,k})²

    Args:
        partidos: lista de dicts `{"p_local": float, "p_empate": float, "p_visitante": float,
                  "resultado": "LOCAL" | "EMPATE" | "VISITANTE"}` (P', P̂ o q_mkt indistintamente).

    Un partido con desenlace desconocido o probabilidades ilegibles se EXCLUYE del cómputo
    y del denominador (N = partidos evaluados): cero cifras fabricadas [GOVERNANCE-01].
    Sin partidos evaluables el score es 0.0.
    """
    suma_error = 0.0
    evaluados = 0

    for partido in (partidos or []):
        try:
            p_local = float(partido.get("p_local"))
            p_empate = float(partido.get("p_empate"))
            p_visitante = float(partido.get("p_visitante"))
            desenlace = str(partido.get("resultado", "")).upper()
        except (TypeError, ValueError, AttributeError):
            continue

        y_local = 1.0 if desenlace == "LOCAL" else 0.0
        y_empate = 1.0 if desenlace == "EMPATE" else 0.0
        y_visitante = 1.0 if desenlace == "VISITANTE" else 0.0

        if (y_local + y_empate + y_visitante) == 0.0:
            continue

        suma_error += (
            (p_local - y_local) ** 2
            + (p_empate - y_empate) ** 2
            + (p_visitante - y_visitante) ** 2
        )
        evaluados += 1

    if evaluados == 0:
        return 0.0
    return round(suma_error / (3.0 * evaluados), 4)


# ── [LN-QBE-124] BANDA DE INDIFERENCIA FIDUCIARIA EN LA COBERTURA ORDINAL ───────────────────
# Manifiesto canónico de la ley: la banda reconoce la cuasi-paridad estocástica de la frontera
# {P_siguiente, P_ultimo}. Cuando la separación es indistinguible del ruido de régimen y el
# anfitrión ostenta una ventaja territorial extrema (ΔAlt⁺ ≥ 1000 msnm), el desempate fiduciario
# promueve al LOCAL a P_mid. La banda JAMÁS altera P_max y JAMÁS inventa una magnitud: sólo
# PERMUTA los dos vértices inferiores (la masa de cobertura P_max + P_mid queda invariante).
BANDA_INDIFERENCIA_EPSILON: float = 0.0100     # ε_indif — banda de indiferencia ordinal (1.00 %)
UMBRAL_ALTITUD_RESCATE_METROS: float = 1000.0  # ΔAlt⁺_rescate — desnivel que decide la banda


def resolver_orden_fiduciario_con_indiferencia(
    p1: float, pX: float, p2: float, delta_alt: float = 0.0
) -> Dict[str, Any]:
    """
    [LN-QBE-124] [DIRGEN-STRICT] Jerarquía ordinal fiduciaria con Banda de Indiferencia y
    desempate por altitud geográfica del anfitrión.

    Contrato IPO: recibe el trío soberano P′ = (p1, pX, p2) y el desnivel del anfitrión
    ΔAlt⁺ = max(0, altitud_local − altitud_visita) en metros; devuelve la tupla ordenada
    (P_max, P_mid, P_low) con la bandera `rescate_indiferencia`.

      1. Orden aritmético descendente (`sorted` estable ⇒ el orden canónico 1 · X · 2 resuelve la
         igualdad exacta; cero desempate inventado).
      2. Rescate territorial: si |P_mid − P_low| ≤ ε_indif, el par en disputa es exactamente
         {LOCAL, EMPATE} y ΔAlt⁺ ≥ 1000.0 msnm, el LOCAL se promueve a P_mid y el EMPATE
         desciende a P_low.
      3. En cualquier otro caso rige el orden aritmético estricto.

    Invarianzas: P_max NUNCA cambia (la banda no reescribe al favorito); la masa de cobertura
    P_max + P_mid es invariante bajo la permutación; un par {LOCAL, VISITANTE} o
    {EMPATE, VISITANTE} en banda NO se toca. Cero I/O, cero números mágicos, cero estado.
    """
    candidatos = [
        ("LOCAL", float(p1)),
        ("EMPATE", float(pX)),
        ("VISITANTE", float(p2)),
    ]
    ordenados = sorted(candidatos, key=lambda x: x[1], reverse=True)
    r_max, p_max_val = ordenados[0]
    r_mid, p_mid_val = ordenados[1]
    r_low, p_low_val = ordenados[2]

    separacion = abs(p_mid_val - p_low_val)
    desnivel = max(0.0, float(delta_alt))
    rescate = False
    if (
        separacion <= BANDA_INDIFERENCIA_EPSILON
        and {r_mid, r_low} == {"LOCAL", "EMPATE"}
        and desnivel >= UMBRAL_ALTITUD_RESCATE_METROS
    ):
        # Permutación pura: los dos vértices inferiores intercambian posición, jamás magnitud.
        rescate = True
        r_mid, p_mid_val = "LOCAL", float(p1)
        r_low, p_low_val = "EMPATE", float(pX)

    return {
        "r_max": r_max,
        "r_mid": r_mid,
        "r_low": r_low,
        "p_max_val": float(p_max_val),
        "p_mid_val": float(p_mid_val),
        "p_low_val": float(p_low_val),
        "masa_cobertura_pct": round((float(p_max_val) + float(p_mid_val)) * 100.0, 2),
        "separacion_mid_low": round(separacion, 4),
        "rescate_indiferencia": rescate,
        "delta_alt_metros": round(desnivel, 1),
    }

