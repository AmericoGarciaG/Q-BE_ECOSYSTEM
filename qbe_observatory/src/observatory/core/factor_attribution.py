# -*- coding: utf-8 -*-
"""
🏆 Q-BE SOVEREIGN ENGINE — ATRIBUCIÓN FACTORIAL Y TELEMETRÍA DE INTEGRIDAD DE INSUMOS
[LN-QBE-101] / [ARCH-1.4.42] · Base de Gobierno: Kybern Framework v12.0 · [DIRGEN-STRICT]

Descomposición aditiva EXACTA del diferencial log-lineal de intensidades:

    Δη = ln(λ_H / λ_A) = (A_H − D_A) + (D_H − A_A) + (γ̄_home + C_H − C_A)
                         └ Ofensiva ┘  └ Defensiva ┘  └   Contexto/Sede   ┘

Cláusula de Amortiguamiento Canónico [VAULT-CORE-001]: los factores llegan CRUDOS
(pre-damping) desde `derivar_factores_estructurales`; la descomposición opera sobre su imagen
canónica κ_net · tanh(A / κ_net) con κ_net = 0.2500, exactamente como los consume
`estimar_intensidades_loglineal`. Sin esa cláusula la suma factorial no reproduciría ln(λ_H/λ_A)
y se violaría la conservación de energía legislada. Cero margen creativo: se delega en la función
sellada del Libro de Constantes (`aplicar_damping_hiperbolico`), jamás se reimplementa.

El vector CRUDO se conserva en las claves `*_cruda` como evidencia forense (cero maquillaje).

Pureza funcional [GOVERNANCE-01]: sin I/O, sin red, sin SQLAlchemy, sin imports de src.storage.
"""

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

from src.core.intensity_canonical_loglink import aplicar_damping_hiperbolico

# ── Gobernanza de los cinco semáforos [LN-QBE-101].P.3 ─────────────────────────────────────────
VERDE = "VERDE"
AMARILLO = "AMARILLO"
ROJO = "ROJO"
NEUTRO = "NEUTRO"

UMBRAL_EPIST_CONSENSO = 0.0300   # 🟢 Consenso (banda baja de fricción)
UMBRAL_EPIST_RUPTURA = 0.1200   # 🔴 frontera de cuarentena fiduciaria [LN-QBE-070-B]
UMBRAL_Q_MOD_SEVERO = 0.9300    # 🔴 shock severo
PJ_SEDE_GATE_GSL3D = 3          # gate de suficiencia de sede ([LN-QBE-038])
H2H_VENTANA_NORMATIVA = 5       # ventana longitudinal normativa (τ = 540 d)

# Precedencia canónica del desempate del driver (reproducibilidad estricta del Juez).
ORDEN_DIMENSIONES_DRIVER: Tuple[str, ...] = ("OFENSIVA", "DEFENSIVA", "CONTEXTO")


def _num(valor: Any, defecto: Optional[float] = None) -> Optional[float]:
    """Lectura numérica honesta: `None`/texto no convertible ⇒ `defecto` (jamás se inventa)."""
    if valor is None or isinstance(valor, bool):
        return defecto
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return defecto
    if math.isnan(numero) or math.isinf(numero):
        return defecto
    return numero


def _es_certificado(valor: Any) -> bool:
    """[ARCH-1.4.44] Lectura estricta del sello `xg_es_real_opta` (True/1/"true" ⇒ certificado).

    Cualquier otra forma —`False`, `0`, `None`, texto vacío o ausente— NO certifica métrica Opta
    real: la procedencia se declara honestamente como no certificada (`[GOVERNANCE-01]`).
    """
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, (int, float)):
        return float(valor) == 1.0
    if isinstance(valor, str):
        return valor.strip().lower() in ("true", "1", "si", "sí", "yes")
    return False


def _amortiguar(factor: Any) -> float:
    """[VAULT-CORE-001] Imagen canónica κ_net · tanh(A / κ_net), κ_net = 0.2500 absoluto."""
    numero = _num(factor, 0.0)
    return aplicar_damping_hiperbolico(numero if numero is not None else 0.0)


def calcular_atribucion_loglineal(
    A_h: Any,
    D_a: Any,
    A_a: Any,
    D_h: Any,
    gamma_home: Any = 0.0,
    C_h: Any = 0.0,
    C_a: Any = 0.0,
    lambda_h: Any = None,
    lambda_a: Any = None,
) -> Dict[str, Optional[float]]:
    """[LN-QBE-101].P.1 — Descomposición aditiva exacta del diferencial log-lineal.

    `C_h` / `C_a` se reciben EN ESPACIO LOGARÍTMICO (espejo de `C = ln(q_mod_clamped)` de la
    Sección 4.9); `gamma_home` es la localía efectiva (γ̄_base + Δγ_plaza + altitud + descanso).
    Las intensidades `λ_H`, `λ_A` son opcionales: si se publican habilitan la cláusula de
    auditoría `delta_ln_lambda` y el `residuo_no_atribuido`.

    Conservación garantizada por construcción: `delta_neto_total` ES la suma de las tres
    componentes canónicas; el residuo sólo puede ser ruido de redondeo de las λ persistidas.
    """
    a_h = _amortiguar(A_h)
    d_a = _amortiguar(D_a)
    a_a = _amortiguar(A_a)
    d_h = _amortiguar(D_h)

    delta_ofensiva = a_h - d_a
    delta_defensiva = d_h - a_a
    delta_contexto = (
        (_num(gamma_home, 0.0) or 0.0)
        + (_num(C_h, 0.0) or 0.0)
        - (_num(C_a, 0.0) or 0.0)
    )
    delta_neto_total = delta_ofensiva + delta_defensiva + delta_contexto

    lh = _num(lambda_h)
    la = _num(lambda_a)
    delta_ln_lambda: Optional[float] = None
    residuo: Optional[float] = None
    if lh is not None and la is not None and lh > 0.0 and la > 0.0:
        delta_ln_lambda = math.log(lh / la)
        residuo = delta_ln_lambda - delta_neto_total

    redondear = lambda x: None if x is None else round(float(x), 6)
    return {
        "delta_ofensiva": redondear(delta_ofensiva),
        "delta_defensiva": redondear(delta_defensiva),
        "delta_contexto": redondear(delta_contexto),
        "delta_neto_total": redondear(delta_neto_total),
        "delta_ofensiva_cruda": redondear((_num(A_h, 0.0) or 0.0) - (_num(D_a, 0.0) or 0.0)),
        "delta_defensiva_cruda": redondear((_num(D_h, 0.0) or 0.0) - (_num(A_a, 0.0) or 0.0)),
        "delta_ln_lambda": redondear(delta_ln_lambda),
        "residuo_no_atribuido": redondear(residuo),
    }

# ── [LN-QBE-101].P.2 — Resolución determinista del Driver Principal ───────────────────────────
_CLAVES_DRIVER: Dict[str, str] = {
    "OFENSIVA": "delta_ofensiva",
    "DEFENSIVA": "delta_defensiva",
    "CONTEXTO": "delta_contexto",
}
_GLIFOS_DRIVER: Dict[str, str] = {
    "OFENSIVA": "⚡",
    "DEFENSIVA": "🛡️",
    "CONTEXTO": "🏟️",
}
_NOMBRES_DRIVER: Dict[str, str] = {
    "OFENSIVA": "Ofensiva",
    "DEFENSIVA": "Defensiva",
    "CONTEXTO": "Sede/Contexto",
}


def resolver_driver_principal(descomposicion: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """[LN-QBE-101].P.2 — `Driver* = argmax |Δ_k|` con desempate por precedencia canónica.

    Signo positivo ⇒ la fuerza impulsa al LOCAL; negativo ⇒ impulsa al VISITANTE.
    Fuerzas nulas ⇒ `NEUTRO` declarado (jamás se disfraza un driver inexistente).
    """
    valores: Dict[str, float] = {}
    for dimension in ORDEN_DIMENSIONES_DRIVER:
        clave = _CLAVES_DRIVER[dimension]
        valores[dimension] = _num((descomposicion or {}).get(clave), 0.0) or 0.0

    elegida = ORDEN_DIMENSIONES_DRIVER[0]
    magnitud = abs(valores[elegida])
    for dimension in ORDEN_DIMENSIONES_DRIVER[1:]:
        candidata = abs(valores[dimension])
        if candidata > magnitud:  # comparación estricta ⇒ el empate conserva la precedencia
            elegida, magnitud = dimension, candidata

    valor = valores[elegida]
    if magnitud <= 0.0:
        return {
            "dimension": NEUTRO,
            "magnitud": 0.0,
            "favorece": NEUTRO,
            "etiqueta": "⚪ Sin driver (fuerzas nulas)",
            "valor_firmado": 0.0,
        }

    favorece = "LOCAL" if valor > 0.0 else "VISITANTE"
    bando = "Local" if valor > 0.0 else "Visita"
    return {
        "dimension": elegida,
        "magnitud": round(magnitud, 6),
        "favorece": favorece,
        "etiqueta": f"{_GLIFOS_DRIVER[elegida]} {_NOMBRES_DRIVER[elegida]} {bando} (+{magnitud:.2f})",
        "valor_firmado": round(valor, 6),
    }


# ── [LN-QBE-101].P.3 — Los cinco semáforos de salud fáctica ───────────────────────────────────
def evaluar_semaforos_salud_datos(
    xg_disponible: bool = False,
    xg_calibrado: bool = False,
    pj_sede_local: Any = 0,
    pj_sede_visita: Any = 0,
    h2h_partidos_conteo: Any = 0,
    delta_epist: Any = 0.0,
    q_mod: Any = 1.0,
    suficiencia_S_I: Any = 1,
    xg_es_real_opta: Any = None,
    xg_metricas_publicadas: Any = None,
) -> Dict[str, str]:
    """[LN-QBE-101].P.3 — Auditoría de completitud de insumos (degradación honesta).

    * `opta`   : 🟢 sello `xg_es_real_opta` certificado · 🟡 métrica xG publicada sin certificación
                 Opta (o respaldo calibrado 1.05·GF) · 🔴 sin métrica que juzgar.
    * `sede`   : evalúa el MÍNIMO bilateral de PJ (el gate GSL-3D exige solidez de ambas plazas).
    * `h2h`    : 🟢 5 enfrentamientos (τ = 540 d) · 🟡 1–4 · ⚪ Zero-H2H [LN-QBE-020-B].
    * `epist`  : 🟢 Δ ≤ 0.03 · 🟡 0.03 < Δ ≤ 0.12 · 🔴 Δ > 0.12 (cuarentena fiduciaria).
    * `ctx`    : 🟢 Q_mod = 1.00 · 🟡 shock leve · 🔴 Q_mod ≤ 0.93 (shock severo).

    [ARCH-1.4.44] Tri-estado de la procedencia Opta: el ROJO deja de acusar evidencia existente.
    Un llamador que no declara el sello (`xg_es_real_opta is None`) conserva el contrato heredado
    (`xg_disponible ⇒ VERDE`); todo productor que SÍ declara el sello —el homologador siempre lo
    estampa— sólo obtiene verde con certificación positiva. La ignorancia canónica S(I) = 0 sigue
    degradando a ROJO mientras no exista certificación Opta real.
    """
    sello_declarado = xg_es_real_opta is not None
    certificado = _es_certificado(xg_es_real_opta) or (not sello_declarado and bool(xg_disponible))
    metrica_publicada = (
        bool(xg_disponible) or bool(xg_calibrado) or _es_certificado(xg_metricas_publicadas)
    )
    if certificado and metrica_publicada:
        opta = VERDE
    elif metrica_publicada:
        opta = AMARILLO
    else:
        opta = ROJO
    if not certificado and (_num(suficiencia_S_I, 1) or 0) == 0:
        opta = ROJO

    pj_local = int(_num(pj_sede_local, 0.0) or 0.0)
    pj_visita = int(_num(pj_sede_visita, 0.0) or 0.0)
    pj_bilateral = min(pj_local, pj_visita)
    if pj_bilateral >= PJ_SEDE_GATE_GSL3D:
        sede = VERDE
    elif pj_bilateral >= 1:
        sede = AMARILLO
    else:
        sede = ROJO

    duelos = int(_num(h2h_partidos_conteo, 0.0) or 0.0)
    if duelos >= H2H_VENTANA_NORMATIVA:
        h2h = VERDE
    elif duelos >= 1:
        h2h = AMARILLO
    else:
        h2h = NEUTRO

    discrepancia = abs(_num(delta_epist, 0.0) or 0.0)
    if discrepancia <= UMBRAL_EPIST_CONSENSO:
        epist = VERDE
    elif discrepancia <= UMBRAL_EPIST_RUPTURA:
        epist = AMARILLO
    else:
        epist = ROJO

    modulador = _num(q_mod, 1.0)
    if modulador is None:
        modulador = 1.0
    if 0.9950 <= modulador <= 1.0050:
        ctx = VERDE
    elif modulador <= UMBRAL_Q_MOD_SEVERO:
        ctx = ROJO
    else:
        ctx = AMARILLO

    return {"opta": opta, "sede": sede, "h2h": h2h, "epist": epist, "ctx": ctx}


# ── [LN-QBE-120].P.4 — Catálogo Estructural de 32 Variables de Predicción (Reingeniería Macro) ──
# Partición canónica INMUTABLE: 6 dimensiones, 32 variables PRE-KICKOFF, cero duplicados.
# Deroga la taxonomía histórica de 44 variables de [LN-QBE-101] (superseditada, no reutilizada).
# Cada renglón declara su espacio de Hilbert (H_att / H_def / H_ctx) de forma explícita:
# la señal directora es xG/PJ (ataque) y xGA/PJ (defensa); contexto, forma, sede y memoria
# longitudinal viven en H_ctx ([LN-QBE-039], [ARCH-1.4.33]).
# Las métricas de minuto a minuto (1T/2T, 0-15', 80-90'), suplentes y rotación del XI quedan
# EXCLUIDAS del catálogo base y se delegan a un proyecto periférico de inferencia causal.
CATALOGO_VERSION: str = "32V-2026"

DIMENSIONES_CANONICAS: Tuple[Tuple[str, str], ...] = (
    ("𝒯_Vol", "Volumen Territorial y Fricción"),
    ("𝒯_Rem", "Calidad de Remate"),
    ("𝒯_Def", "Resistencia Defensiva"),
    ("𝒯_Por", "Rendimiento de Portería"),
    ("𝒯_Spc", "Balón Parado y Disciplina"),
    ("𝒯_Ctx", "Memoria, Forma y Contexto"),
)

# (id, nombre, dimensión, claves fácticas, modo, origen, espacio)
# [LN-QBE-120] El nombre de la tupla se CONSERVA por contrato del Juez Inmutable y de las
# dependencias locales (`estructurar_catalogo_44_variables`, DTO `variables_44`); su contenido
# es de 32 renglones. El alias `_CATALOGO_32` documenta la verdad semántica.
_CATALOGO_44: Tuple[Tuple[str, str, str, Tuple[str, ...], str, str, str], ...] = (
    # 𝒯_Vol — Volumen Territorial y Fricción (5)
    ("V01", "Posesión Promedio (%)", "𝒯_Vol", ("possession_pct", "possession", "posesion"), "directo", "OPTA", "H_att"),
    ("V02", "Toques en Área Rival", "𝒯_Vol", ("opp_box_touches", "touches_opp_box", "toques_area_rival"), "directo", "OPTA", "H_att"),
    ("V03", "Pases Precisos", "𝒯_Vol", ("accurate_pass_team", "accurate_passes_per_match", "pases_precisos"), "directo", "OPTA", "H_att"),
    ("V04", "Pases Largos Precisos", "𝒯_Vol", ("accurate_long_balls_team", "accurate_long_balls_per_match", "pases_largos_precisos"), "directo", "OPTA", "H_att"),
    ("V05", "Faltas Cometidas", "𝒯_Vol", ("fk_foul_lost_team", "fouls_per_match", "faltas_cometidas"), "directo", "OPTA", "H_att"),
    # 𝒯_Rem — Calidad de Remate (6)
    ("V06", "xG por Partido (ancla npxG)", "𝒯_Rem", ("npxg", "xg"), "tasa", "OPTA", "H_att"),
    ("V07", "Tiros al Arco por Partido (SoT)", "𝒯_Rem", ("sot", "shots_on_target", "ontarget_scoring_att_team"), "directo", "OPTA", "H_att"),
    ("V08", "Big Chances Creadas", "𝒯_Rem", ("big_chances_created", "big_chance_team", "bc_created"), "directo", "OPTA", "H_att"),
    ("V09", "Big Chances Falladas", "𝒯_Rem", ("big_chances_missed", "big_chance_missed_team", "bc_missed"), "directo", "OPTA", "H_att"),
    ("V10", "xGOT de Plantilla", "𝒯_Rem", ("xgot", "expected_goalsontarget"), "directo", "OPTA", "H_att"),
    ("V11", "xA de Plantilla", "𝒯_Rem", ("xa", "expected_assists"), "directo", "OPTA", "H_att"),
    # 𝒯_Def — Resistencia Defensiva (5)
    ("V12", "xGA por Partido (ancla defensiva)", "𝒯_Def", ("xga",), "tasa", "OPTA", "H_def"),
    ("V13", "Tiros al Arco Recibidos por Partido (SoTA)", "𝒯_Def", ("sota", "shots_on_target_against"), "directo", "OPTA", "H_def"),
    ("V14", "Acciones Defensivas por Partido", "𝒯_Def", ("defensive_contributions", "defensive_actions_per_match"), "directo", "OPTA", "H_def"),
    ("V15", "Intercepciones por Partido", "𝒯_Def", ("interceptions_mid", "mid_third_recoveries", "interception_team"), "directo", "OPTA", "H_def"),
    # [LN-QBE-123] V16 en CUARENTENA: FotMob no publica leaderboard de big chances concedidas. La
    # fila se conserva (integridad del 32V y de `derivar_taxonomia`) pero queda FUERA DE FUENTE: sin
    # claves de extracción y con modo `cuarentena`, de modo que ninguna ruta heredada puede encenderla.
    ("V16", "Big Chances Concedidas", "𝒯_Def", (), "cuarentena", "FotMob", "H_def"),
    # 𝒯_Por — Rendimiento de Portería (4)
    ("V17", "Goles Evitados", "𝒯_Por", ("goals_prevented", "goles_prevenidos"), "directo", "OPTA", "H_def"),
    ("V18", "Save % (Porcentaje de Atajadas)", "𝒯_Por", ("save_pct", "save_percentage", "atajadas_pct"), "directo", "OPTA", "H_def"),
    ("V19", "Salidas/Líbero por Partido", "𝒯_Por", ("sweeper_actions", "total_keeper_sweeper", "high_claims", "salidas_altas"), "directo", "OPTA", "H_def"),
    ("V20", "Clean Sheets", "𝒯_Por", ("clean_sheets", "clean_sheet_team"), "directo", "OPTA", "H_def"),
    # 𝒯_Spc — Balón Parado y Disciplina (5)
    ("V21", "Goles a Favor de Pelota Parada", "𝒯_Spc", ("set_piece_goals", "xg_setpiece"), "directo", "OPTA", "H_att"),
    ("V22", "Goles Recibidos de Pelota Parada", "𝒯_Spc", ("set_piece_goals_conceded", "xga_setpiece"), "directo", "OPTA", "H_def"),
    ("V23", "Córners por Partido", "𝒯_Spc", ("corners", "corner_taken_team", "tiros_esquina"), "directo", "OPTA", "H_att"),
    ("V24", "Penales Favor/Contra", "𝒯_Spc", ("penalty_rate", "penalty_won_team", "penalty_conceded_team", "penales_tasa"), "directo", "OPTA", "H_att"),
    ("V25", "Tarjetas Amarillas/Rojas", "𝒯_Spc", ("yellow_cards", "total_yel_card_team", "red_card_risk", "amarillas"), "directo", "OPTA", "H_ctx"),
    # 𝒯_Ctx — Memoria, Forma y Contexto (7)
    ("V26", "Récord H2H", "𝒯_Ctx", ("h2h_wins",), "h2h_victorias", "Q-BE", "H_ctx"),
    ("V27", "ΔG H2H (Diferencial de Goles)", "𝒯_Ctx", ("h2h_gd",), "h2h_diferencia", "Q-BE", "H_ctx"),
    ("V28", "Récord Visitante Sede", "𝒯_Ctx", ("resistencia_sede_visita",), "contexto_local_inverso", "Q-BE", "H_ctx"),
    ("V29", "Altitud ΔAlt+ (Factor Fisiológico)", "𝒯_Ctx", ("delta_alt_metros",), "contexto_local", "FIXTURE", "H_ctx"),
    ("V30", "Días de Descanso (ΔDías)", "𝒯_Ctx", ("delta_descanso_dias",), "contexto", "FIXTURE", "H_ctx"),
    ("V31", "Forma 5P (Puntos Recientes)", "𝒯_Ctx", ("pts_last5", "pts_5p", "puntos_recientes"), "directo", "Q-BE", "H_ctx"),
    ("V32", "Varianza ΔxPTS", "𝒯_Ctx", ("xpts_variance", "varianza_xpts", "xpts_diff"), "directo", "Q-BE", "H_ctx"),
)

# Alias semántico de lectura: el catálogo vigente es de 32 variables ([LN-QBE-120]).
_CATALOGO_32 = _CATALOGO_44

# ── [LN-QBE-122] Derivación de taxonomías locales desde el catálogo ÚNICO ─────────────────────
# Materializa `[ARCH-1.4.60]` §4-§5: el catálogo manda en NOMBRE y ORDEN (fidelidad FotMob
# `[LN-QBE-120]`); el proveedor sólo aporta la unidad canónica y la nota de procedencia. Las
# magnitudes sin celda viajan con prefijo `AUX_` y jamás usurpan un identificador `V\\d\\d`.
PREFIJO_AUXILIAR = "AUX_"

_NOMBRES_CATALOGO: Dict[str, str] = {fila[0]: fila[1] for fila in _CATALOGO_44}


def es_identificador_auxiliar(identificador: Any) -> bool:
    """`True` si el identificador es una magnitud auxiliar sin celda (`AUX_*`, `[LN-QBE-122]`)."""
    return str(identificador or "").startswith(PREFIJO_AUXILIAR)


def nombre_de_celda(identificador: str, respaldo: str = "") -> str:
    """[LN-QBE-122] Nombre forense canónico de la celda; `respaldo` para los `AUX_*` huérfanos."""
    return _NOMBRES_CATALOGO.get(str(identificador), respaldo)


def derivar_taxonomia(
    dimension: str,
    locales: Dict[str, Tuple[str, str, str]],
) -> Tuple[Tuple[str, str, str, str], ...]:
    """[LN-QBE-122] Taxonomía de una familia `𝒯_*` derivada del catálogo único.

    `locales[identificador] = (nombre_respaldo, unidad, nota)`. Las celdas del catálogo toman
    NOMBRE y POSICIÓN de `_CATALOGO_32`; del proveedor se conservan la unidad canónica y la nota
    de procedencia. Los `AUX_*` no habitan el catálogo: se anexan al final en el orden declarado.
    Un identificador `V\\d\\d` ausente de la familia es un error de contrato y se rechaza en voz
    alta: la taxonomía local no puede inventar celdas ni robarle una a otra dimensión.
    """
    canonicos: List[Tuple[str, str]] = [
        (identificador, nombre)
        for identificador, nombre, familia, _claves, _modo, _origen, _espacio in _CATALOGO_44
        if familia == dimension
    ]
    orden: Dict[str, int] = {identificador: posicion for posicion, (identificador, _) in enumerate(canonicos)}
    nombres: Dict[str, str] = {identificador: nombre for identificador, nombre in canonicos}
    derivadas: List[Tuple[str, str, str, str]] = []
    auxiliares: List[Tuple[str, str, str, str]] = []
    for identificador, (nombre_local, unidad, nota) in locales.items():
        if es_identificador_auxiliar(identificador):
            auxiliares.append((identificador, nombre_local, unidad, nota))
            continue
        if identificador not in nombres:
            raise ValueError(
                f"[LN-QBE-122] `{identificador}` no pertenece a `{dimension}` en el catálogo "
                f"`{CATALOGO_VERSION}`: la taxonomía local no puede inventar celdas."
            )
        derivadas.append((identificador, nombres[identificador], unidad, nota))
    derivadas.sort(key=lambda fila: orden[fila[0]])
    return tuple(derivadas + auxiliares)

_ESTADO_VALIDADO = "VALIDADO"
_ESTADO_DERIVADO = "DERIVADO"
_ESTADO_SIN_EVIDENCIA = "SIN EVIDENCIA"
_ESTADO_EVALUADO = "EVALUADO"   # [LN-QBE-102] El insumo publicado SÍ fue consumido por el motor.

# ── [LN-QBE-123] Cuarentena de fuentes no extraíbles ───────────────────────────────────────────
# Una celda puede pertenecer al catálogo forense y NO tener fuente publicable. Se exhibe con su
# fila (integridad del 32V y de `derivar_taxonomia`) y se declara `FUERA DE FUENTE`: la cuarentena
# se evalúa ANTES de la telemetría y de la ruta heredada, de modo que ninguna clave —ni la macros
# torneal— puede encenderla por la espalda. Cero imputación, cero cero fabricado.
ESTADO_FUERA_DE_FUENTE = "FUERA DE FUENTE"
_CUARENTENA: Dict[str, str] = {
    "V16": (
        "FUERA DE FUENTE: FotMob no publica el leaderboard de big chances concedidas "
        "(ni el corpus Opta homologado); la celda se exhibe vacía y jamás se imputa [LN-QBE-123]."
    ),
}

# ── [LN-QBE-102] Tabla de transcripción tipada de los insumos telemetrizados ────────────────────
# (clave_local, clave_visita, formato): traduce el número REALMENTE consumido por el pipeline a la
# celda forense del catálogo de 32 variables ([LN-QBE-120]). `clave_visita = None` ⇒ magnitud de
# contexto (no bilateral): se declara en la columna `local` y la visita permanece `None` (cero
# fabricación). REMAPEO [LN-QBE-120]: la renumeración V01..V32 conserva la MISMA magnitud en la
# celda que la hospeda (xG V05→V06, SoT V06→V07, xGA V10→V12, SoTA V11→V13, ΔDescanso V27→V30,
# ΔAltitud V28→V29, H2H V39→V26). Ningún insumo cambia de semántica.
_FORMATO_INSUMO: Dict[str, Tuple[str, Optional[str], str]] = {
    "V01": ("poss_local", "poss_visita", "pct"),        # Posesión media
    "V06": ("xg_local_rate", "xg_visita_rate", "num2"),  # xG por partido (ancla acumulado / PJ)
    "V07": ("sot_local", "sot_visita", "num0"),          # Tiros a puerta por partido
    "V12": ("xga_local_rate", "xga_visita_rate", "num2"),  # xGA por partido
    "V13": ("sota_local", "sota_visita", "num0"),        # Tiros a puerta recibidos por partido
    "V26": ("h2h_conteo", None, "partidos"),             # Duelos leídos dentro de la ventana τ
    "V29": ("delta_alt_metros", None, "metros"),         # Δ altitud REALMENTE aplicado al modelo
    "V30": ("delta_descanso_dias", None, "dias"),        # Δ descanso REALMENTE aplicado al modelo
}

# ── [ARCH-1.4.44] Respaldo declarado del Axioma 4 (cero fabricación de xGA) ────────────────────
# Si el generador publicó `gc_*_rate` (goles recibidos por partido) sin `xga_*_rate`, la celda V12
# (ancla defensiva, antes V10) transcribe el respaldo REALMENTE consumido y lo declara en su nota
# forense. Nunca se sustituye una métrica ausente por un valor inventado: sólo se exhibe el
# insumo que el motor sí consumió.
_RESPALDO_INSUMO: Dict[str, Tuple[Tuple[str, str], str, str]] = {
    "V12": (
        ("gc_local_rate", "gc_visita_rate"),
        "num2",
        "Respaldo GC/PJ (xGA no publicado) · Axioma 4 [ARCH-1.4.44]",
    ),
}


# ── [LN-QBE-105] Transcripción del bloque `h2h_stats` del pipeline a V26/V27/V28 ───────────────
# El orquestador ya agregó la ventana desde la perspectiva del local evaluado; aquí sólo se
# TRANSCRIBE la magnitud consumida, sin recalcular récords ni fabricar sede alguna. [LN-QBE-120]
# remapea la memoria longitudinal a 𝒯_Ctx: V39→V26 (récord), V40→V27 (ΔG), V41→V28 (sede).
_CLAVES_H2H_STATS: Dict[str, Tuple[str, str]] = {
    "V26": ("record_general", "Récord H2H del local evaluado (V-E-D) [LN-QBE-105]"),
    "V27": ("dif_goles", "Diferencial acumulado de goles H2H Σ(GF−GC) [LN-QBE-105]"),
    "V28": ("record_sede", "Récord del visitante en la sede evaluada [LN-QBE-105]"),
}


def _celda_h2h_stats(
    identificador: str,
    nombre: str,
    origen: str,
    espacio: str,
    z_scores: Dict[str, Any],
    estadisticas: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Celda `EVALUADO` de V26/V27/V28 a partir del agregado `h2h_stats` (`None` si no aplica)."""
    receta = _CLAVES_H2H_STATS.get(identificador)
    if receta is None:
        return None
    clave, nota = receta
    valor = estadisticas.get(clave)
    if not isinstance(valor, str) or not valor.strip():
        return None
    return {
        "id": identificador,
        "variable": nombre,
        "local": valor.strip(),
        "visita": None,
        "z_score": _num(z_scores.get(identificador)),
        "origen": origen,
        "estado": _ESTADO_EVALUADO,
        "impacto": espacio,
        "nota": nota,
    }


# ── [LN-QBE-123] Transcripción del bloque `trayectoria` a V31/V32 ─────────────────────────────
# `trajectory_provider` publica las claves planas de su bloque en `trayectoria.insumos`
# (`pts_last5_*`, `xpts_diff_*`). Aquí SÓLO se transcribe la magnitud REALMENTE publicada: una clave
# ausente o `None` apaga la celda. La trayectoria es DIAGNÓSTICO forense: jamás entra en λ ni en P′
# (`[DIRGEN-STRICT]` intacto).
_CLAVES_TRAYECTORIA: Dict[str, Tuple[str, str, str, str]] = {
    "V31": (
        "pts_last5_local", "pts_last5_visita", "num0",
        "Forma 5P transcrita de `trajectory_provider` (puntos de la ventana de 5) [LN-QBE-123]",
    ),
    "V32": (
        "xpts_diff_local", "xpts_diff_visita", "delta2",
        "ΔxPTS transcrita de `trajectory_provider` (+ sobre-rendimiento esperado) [LN-QBE-123]",
    ),
}


def _celda_trayectoria(
    identificador: str,
    nombre: str,
    origen: str,
    espacio: str,
    z_scores: Dict[str, Any],
    insumos: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Celda `EVALUADO` de V31/V32 desde el bloque `trayectoria` (`None` si no se publicó)."""
    receta = _CLAVES_TRAYECTORIA.get(identificador)
    if receta is None:
        return None
    clave_local, clave_visita, formato, nota = receta
    bloque = _insumos_del_bloque(insumos.get("trayectoria"))
    if not bloque:
        return None
    local_insumo = _formatear_insumo(bloque.get(clave_local), formato)
    visita_insumo = _formatear_insumo(bloque.get(clave_visita), formato)
    if local_insumo is None and visita_insumo is None:
        return None
    return {
        "id": identificador,
        "variable": nombre,
        "local": local_insumo,
        "visita": visita_insumo,
        "z_score": _num(z_scores.get(identificador)),
        "origen": origen,
        "estado": _ESTADO_EVALUADO,
        "impacto": espacio,
        "nota": nota,
    }


# ── [LN-QBE-121] Aduana de Exhibición Macro-Torneal ───────────────────────────────────────────
# La verdad torneal (`data/cache_macro_stats_liga_mx_2026.json`, `[ARCH-1.4.59]`) llega YA
# RESUELTA por slug desde el orquestador de ingesta. Jurisdicción: EXHIBICIÓN. Enciende celdas
# del catálogo que el corte N−1 dejó apagadas y JAMÁS sustituye una magnitud que alimente λ:
# las cinco celdas insumidas (V01, V06, V07, V12, V13) conservan el corte certificado y su
# cotejo torneal se publica aparte. Cero imputación: una clave ausente apaga la celda.
CLAVE_MACRO_STATS = "macro_stats"
PROCEDENCIA_MACRO_TORNEAL = "MACRO_TORNEAL"

# (claves del bloque del club, formato de transcripción, nota de procedencia)
_CLAVES_MACRO_STATS: Dict[str, Tuple[Tuple[str, ...], str, str]] = {
    "V02": (("touches_opp_box_per_match",), "num2",
            "Agregado torneal: toques en área rival por partido [LN-QBE-121]."),
    "V03": (("accurate_passes_per_match",), "num1",
            "Agregado torneal: pases precisos por partido [LN-QBE-121]."),
    "V04": (("accurate_long_balls_per_match",), "num1",
            "Agregado torneal: pases largos precisos por partido [LN-QBE-121]."),
    "V05": (("fouls_per_match",), "num1",
            "Agregado torneal: faltas cometidas por partido [LN-QBE-121]."),
    "V08": (("big_chances_created_per_match",), "num2",
            "Agregado torneal: big chances creadas por partido [LN-QBE-121]."),
    "V09": (("big_chances_missed_per_match",), "num2",
            "Agregado torneal: big chances falladas por partido [LN-QBE-121]."),
    "V10": (("xgot_squad",), "num1",
            "Agregado torneal: xGOT acumulado de plantilla [LN-QBE-121]."),
    "V11": (("xa_squad",), "num1",
            "Agregado torneal: xA acumulada de plantilla [LN-QBE-121]."),
    "V14": (("defensive_actions_per_match",), "num1",
            "Agregado torneal: acciones defensivas por partido [LN-QBE-121]."),
    "V15": (("interceptions_per_match",), "num1",
            "Agregado torneal: intercepciones por partido [LN-QBE-121]."),
    "V17": (("goals_prevented_squad",), "num1",
            "Agregado torneal: goles evitados de plantilla [LN-QBE-121]."),
    "V18": (("save_percentage",), "pct",
            "Agregado torneal: Save % del club [LN-QBE-121]."),
    "V19": (("sweeper_actions",), "num1",
            "Agregado torneal: salidas del portero por partido [LN-QBE-121]."),
    "V20": (("clean_sheets",), "num0",
            "Agregado torneal: porterías a cero acumuladas [LN-QBE-121]."),
    "V21": (("set_piece_goals_per_match",), "num2",
            "Agregado torneal: goles a favor de pelota parada por partido [LN-QBE-121]."),
    "V22": (("set_piece_goals_conceded_per_match",), "num2",
            "Agregado torneal: goles recibidos de pelota parada por partido [LN-QBE-121]."),
    "V23": (("corners_per_match",), "num2",
            "Agregado torneal: córners por partido [LN-QBE-121]."),
    "V24": (("penalties_won_total", "penalties_conceded_total"), "penales",
            "Agregado torneal: penales a favor/en contra acumulados [LN-QBE-121]."),
    "V25": (("yellow_cards_per_match", "red_cards_per_match"), "tarjetas",
            "Agregado torneal: amarillas y rojas por partido [LN-QBE-121]."),
}

# Celdas que el MOTOR ya consume: la macro sólo las exhibe como control cruzado, jamás las pisa.
CELDAS_INSUMIDAS: Tuple[str, ...] = ("V01", "V06", "V07", "V12", "V13")
# Claves del artefacto que se publican en `macro_stats.cotejo` (control cruzado de exhibición).
_CLAVES_COTEJO_MACRO: Dict[str, str] = {
    "V01": "possession_pct",
    "V06": "xg_per_match",
    "V07": "sot_per_match",
    "V12": "xga_per_match",
    "V13": "sota_per_match",
}


def _formatear_macro(
    bloque: Any, claves: Sequence[str], formato: str
) -> Optional[str]:
    """Transcribe el agregado torneal de UN club (`None` si falta cualquier clave: cero imputación)."""
    if not isinstance(bloque, dict):
        return None
    valores: Dict[str, float] = {}
    for clave in claves:
        numero = _num(bloque.get(clave))
        if numero is None:
            return None
        valores[clave] = numero
    if formato == "penales":
        return f"{valores[claves[0]]:.0f} a favor · {valores[claves[1]]:.0f} en contra"
    if formato == "tarjetas":
        return f"{valores[claves[0]]:.2f} amarillas/PJ · {valores[claves[1]]:.2f} rojas/PJ"
    return _formatear_insumo(valores[claves[0]], formato)


def _celda_macro_stats(
    identificador: str,
    nombre: str,
    origen: str,
    espacio: str,
    z_scores: Dict[str, Any],
    macro_stats: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Celda `EVALUADO` de exhibición torneal (`None` si la celda no tiene receta o no hay dato)."""
    receta = _CLAVES_MACRO_STATS.get(identificador)
    if receta is None:
        return None
    claves, formato, nota = receta
    local = _formatear_macro(macro_stats.get("local"), claves, formato)
    visita = _formatear_macro(macro_stats.get("visita"), claves, formato)
    if local is None and visita is None:
        return None
    return {
        "id": identificador,
        "variable": nombre,
        "local": local,
        "visita": visita,
        "z_score": _num(z_scores.get(identificador)),
        "origen": origen,
        "estado": _ESTADO_EVALUADO,
        "impacto": espacio,
        "nota": nota,
    }


def _cotejo_macro(macro_stats: Dict[str, Any]) -> Dict[str, Any]:
    """[LN-QBE-121] Control cruzado: agregado torneal de las celdas que SÍ manda el corte.

    Sólo transcribe valores publicados por el artefacto; no calcula, no compara y no altera la
    celda. Es evidencia de exhibición para el Visor (`macro_stats.cotejo`).
    """
    cotejo: Dict[str, Any] = {}
    for identificador, clave in _CLAVES_COTEJO_MACRO.items():
        entrada: Dict[str, Any] = {"clave": clave}
        for lado in ("local", "visita"):
            bloque = macro_stats.get(lado)
            valor = _num(bloque.get(clave)) if isinstance(bloque, dict) else None
            if valor is not None:
                entrada[lado] = valor
        if "local" in entrada or "visita" in entrada:
            cotejo[identificador] = entrada
    return cotejo


def _celda_telemetria(
    identificador: str,
    nombre: str,
    origen: str,
    espacio: str,
    z_scores: Dict[str, Any],
    insumos: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """[LN-QBE-102] Celda `EVALUADO` de un insumo consumido (o `None` si no se publicó).

    Precedencia: `[LN-QBE-105]` el bloque `h2h_stats` manda cuando está presente (V26/V27/V28);
    `[LN-QBE-123]` el bloque `trayectoria` manda para V31/V32; si no llegó, rige la receta primaria de
    `_FORMATO_INSUMO` (ruta heredada byte-idéntica) y, en su ausencia, el respaldo legislado de
    `_RESPALDO_INSUMO` (Axioma 4). Como ÚLTIMO recurso de exhibición —nunca de motor— rige
    `_CLAVES_MACRO_STATS` (`[LN-QBE-121]`): la verdad torneal sólo enciende celdas que el corte
    certificado dejó apagadas.
    """
    estadisticas_h2h = insumos.get("h2h_stats")
    if isinstance(estadisticas_h2h, dict):
        celda_h2h = _celda_h2h_stats(
            identificador, nombre, origen, espacio, z_scores, estadisticas_h2h
        )
        if celda_h2h is not None:
            return celda_h2h

    # [LN-QBE-123] V31/V32: transcripción del bloque `trayectoria` ANTES de la ruta heredada.
    celda_trayectoria = _celda_trayectoria(identificador, nombre, origen, espacio, z_scores, insumos)
    if celda_trayectoria is not None:
        return celda_trayectoria

    receta = _FORMATO_INSUMO.get(identificador)
    if receta is not None:
        clave_local, clave_visita, formato = receta
        local_insumo = _formatear_insumo(insumos.get(clave_local), formato)
        visita_insumo = (
            _formatear_insumo(insumos.get(clave_visita), formato) if clave_visita else None
        )
        if local_insumo is not None or visita_insumo is not None:
            return {
                "id": identificador,
                "variable": nombre,
                "local": local_insumo,
                "visita": visita_insumo,
                "z_score": _num(z_scores.get(identificador)),
                "origen": origen,
                "estado": _ESTADO_EVALUADO,
                "impacto": espacio,
                "nota": "Insumo consumido por el pipeline [LN-QBE-102]",
            }

    respaldo = _RESPALDO_INSUMO.get(identificador)
    if respaldo is not None:
        (clave_local, clave_visita), formato, nota = respaldo
        local_insumo = _formatear_insumo(insumos.get(clave_local), formato)
        visita_insumo = _formatear_insumo(insumos.get(clave_visita), formato)
        if local_insumo is not None or visita_insumo is not None:
            return {
                "id": identificador,
                "variable": nombre,
                "local": local_insumo,
                "visita": visita_insumo,
                "z_score": _num(z_scores.get(identificador)),
                "origen": origen,
                "estado": _ESTADO_EVALUADO,
                "impacto": espacio,
                "nota": nota,
            }

    macro_stats = insumos.get(CLAVE_MACRO_STATS)
    if isinstance(macro_stats, dict):
        celda_macro = _celda_macro_stats(
            identificador, nombre, origen, espacio, z_scores, macro_stats
        )
        if celda_macro is not None:
            return celda_macro
    return None


# ── [ARCH-1.4.55] Orquestación ANIDADA del paquete `insumos_factivados` ───────────────────────
# Fase 1 de la Integración Maestra: los proveedores canónicos de `src/core/sovereign/` publican
# bloques con `status` + `insumos`; aquí se anidan bajo sus cinco nombres legislados y se derivan
# las claves PLANAS heredadas para que el catálogo de 44 variables ([LN-QBE-101]) ilumine
# exactamente las mismas celdas. Cero I/O: el empaquetado es una función pura de sus argumentos.
SUB_BLOQUES_INSUMOS_FACTIVADOS: Tuple[str, ...] = (
    "h2h",
    "contexto",
    "trayectoria",
    "volumen_porteria",
    "ataque_defensa",
)

# (sub_bloque, clave en `insumos` del bloque, clave plana heredada). El ORDEN declara la
# precedencia: la primera aparición gana (jamás se sobreescribe una clave ya derivada). El bloque
# `ataque_defensa` manda porque hospeda la ruta sellada `[VAULT-CORE-005]` realmente consumida;
# `trayectoria` no hereda claves planas (su contrato son las celdas V29–V32, no un insumo previo).
_MAPA_NIDOS_A_PLANO: Tuple[Tuple[str, str, str], ...] = (
    ("ataque_defensa", "xg_local_rate", "xg_local_rate"),
    ("ataque_defensa", "xg_visita_rate", "xg_visita_rate"),
    ("ataque_defensa", "xga_local_rate", "xga_local_rate"),
    ("ataque_defensa", "xga_visita_rate", "xga_visita_rate"),
    ("ataque_defensa", "gc_local_rate", "gc_local_rate"),
    ("ataque_defensa", "gc_visita_rate", "gc_visita_rate"),
    ("ataque_defensa", "sot_local", "sot_local"),
    ("ataque_defensa", "sot_visita", "sot_visita"),
    ("ataque_defensa", "sota_local", "sota_local"),
    ("ataque_defensa", "sota_visita", "sota_visita"),
    ("ataque_defensa", "pj_sede_local", "pj_sede_local"),
    ("ataque_defensa", "pj_sede_visita", "pj_sede_visita"),
    ("ataque_defensa", "xg_es_real_opta", "xg_es_real_opta"),
    ("contexto", "delta_alt_metros", "delta_alt_metros"),
    ("contexto", "delta_descanso_dias", "delta_descanso_dias"),
    ("contexto", "q_mod_h", "q_mod_h"),
    ("contexto", "q_mod_a", "q_mod_a"),
    ("volumen_porteria", "poss_local", "poss_local"),
    ("volumen_porteria", "poss_visita", "poss_visita"),
    ("h2h", "h2h_conteo", "h2h_conteo"),
    ("h2h", "h2h_stats", "h2h_stats"),
)


# ── [LN-QBE-123] Guardián de presencia de las magnitudes de `contexto` ────────────────────────
# (identificador, clave_bandera, claves_fecha…): si la bandera declara `False` —o TODAS las fechas
# publicadas son `None`— la celda se apaga. El centinela plano del homologador (`0.0`) no es prueba.
_PRESENCIA_CONTEXTO: Dict[str, Tuple[str, ...]] = {
    "V30": ("descanso_evaluado", "descanso_local", "descanso_visita"),
}


def _presencia_refutada(identificador: str, insumos: Dict[str, Any]) -> bool:
    """[LN-QBE-123] La ausencia DECLARADA por el proveedor manda sobre cualquier clave plana.

    `homologar_temporada_optah2h` publica `delta_descanso_dias = 0.0` cuando el fixture no
    reconstruye fechas (`or 0.0`): ese cero heredado es un CENTINELA de ausencia, no una magnitud.
    Si el bloque `contexto` declara el descanso como no evaluado (`descanso_evaluado = False`, o
    ambas fechas publicadas en `None`), la celda V30 se apaga aunque la clave plana traiga `0.0`.
    """
    claves = _PRESENCIA_CONTEXTO.get(identificador)
    if not claves:
        return False
    bloque = _insumos_del_bloque(insumos.get("contexto"))
    if not bloque:
        return False
    if bloque.get("descanso_evaluado") is False:
        return True
    presentes = [clave for clave in claves[1:] if clave in bloque]
    return bool(presentes) and all(bloque[clave] is None for clave in presentes)


def _insumos_del_bloque(bloque: Any) -> Dict[str, Any]:
    """Insumos planos de un sub-bloque de proveedor (`insumos` si lo publica; si no, el bloque)."""
    if not isinstance(bloque, dict):
        return {}
    anidado = bloque.get("insumos")
    return anidado if isinstance(anidado, dict) else bloque


def _aplanar_insumos(paquete: Dict[str, Any]) -> Dict[str, Any]:
    """[ARCH-1.4.55] Deriva las claves planas heredadas de un paquete SÓLO anidado.

    Sólo se transcriben magnitudes publicadas por los proveedores (jamás `None`, jamás un valor
    inventado). La tabla `_MAPA_NIDOS_A_PLANO` es la ÚNICA fuente de verdad del aplanado.
    """
    planas: Dict[str, Any] = {}
    if not isinstance(paquete, dict):
        return planas
    for sub_bloque, clave_nido, clave_plana in _MAPA_NIDOS_A_PLANO:
        if clave_plana in planas:
            continue
        bloque = _insumos_del_bloque(paquete.get(sub_bloque))
        valor = bloque.get(clave_nido) if clave_nido in bloque else None
        if valor is not None:
            planas[clave_plana] = valor
    return planas


def _fusionar_planas(paquete: Dict[str, Any]) -> Dict[str, Any]:
    """Vista plana del paquete: una clave raíz publicada manda, salvo que declare `None`.

    La ignorancia declarada en la raíz (`None`) no borra la evidencia REAL publicada por el
    sub-bloque anidado: es la misma magnitud, sólo cambió su ubicación `[ARCH-1.4.55]`.
    """
    fusionado = _aplanar_insumos(paquete)
    for clave, valor in paquete.items():
        if valor is None and clave in fusionado:
            continue
        fusionado[clave] = valor
    return fusionado


def empaquetar_insumos_factivados(
    h2h: Optional[Dict[str, Any]] = None,
    contexto: Optional[Dict[str, Any]] = None,
    trayectoria: Optional[Dict[str, Any]] = None,
    volumen_porteria: Optional[Dict[str, Any]] = None,
    ataque_defensa: Optional[Dict[str, Any]] = None,
    claves_heredadas: Optional[Dict[str, Any]] = None,
    macro_stats: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """[ARCH-1.4.55] Paquete `insumos_factivados` ANIDADO + claves planas heredadas.

    * Los cinco sub-bloques se publican con el shape ÍNTEGRO de los proveedores (`status`,
      `motivo`, `variables`, `insumos`, `semaforos`, …) para consumo de la consola forense.
    * `_aplanar_insumos` completa las claves planas ausentes: un paquete SÓLO anidado ilumina
      exactamente las mismas celdas del catálogo de 44 variables de `[LN-QBE-101]`.
    * `claves_heredadas` son las magnitudes que el generador sellado `[LN-QBE-102]` ya publica:
      mandan sobre cualquier derivación (ruta byte-idéntica, cero ruptura de contrato). Un `None`
      heredado NO borra la evidencia real del sub-bloque: misma regla que `_fusionar_planas`.
    """
    paquete: Dict[str, Any] = {
        "h2h": h2h if isinstance(h2h, dict) else None,
        "contexto": contexto if isinstance(contexto, dict) else None,
        "trayectoria": trayectoria if isinstance(trayectoria, dict) else None,
        "volumen_porteria": volumen_porteria if isinstance(volumen_porteria, dict) else None,
        "ataque_defensa": ataque_defensa if isinstance(ataque_defensa, dict) else None,
    }
    paquete.update(_aplanar_insumos(paquete))
    if claves_heredadas:
        for clave, valor in claves_heredadas.items():
            if not isinstance(clave, str):
                continue
            if valor is None and paquete.get(clave) is not None:
                # La ignorancia declarada en la raíz no destruye la magnitud REAL ya derivada.
                continue
            paquete[clave] = valor
    # [LN-QBE-121] Bloque de EXHIBICIÓN torneal: se anida tal cual llega (ya resuelto por slug).
    # No entra en `_MAPA_NIDOS_A_PLANO` ni en `_FORMATO_INSUMO`: la ruta plana queda intacta.
    if isinstance(macro_stats, dict) and macro_stats:
        paquete[CLAVE_MACRO_STATS] = dict(macro_stats)
    return paquete



def _insumos_factivados(datos: Dict[str, Any]) -> Dict[str, Any]:
    """[LN-QBE-102] Paquete de telemetría fáctica publicado por el generador (`{}` si ausente).

    Se admiten las dos ubicaciones canónicas: la raíz del payload y la traza persistida
    (`audit_trace_json`). La ausencia NO es evidencia de nada: simplemente desactiva la iluminación.
    `[ARCH-1.4.55]` Un paquete SÓLO anidado se aplana aquí por `_MAPA_NIDOS_A_PLANO`, de modo que
    la ruta heredada de lectura permanece intacta.
    """
    candidato = datos.get("insumos_factivados")
    if isinstance(candidato, dict) and candidato:
        return _fusionar_planas(candidato)
    trace = datos.get("audit_trace") or datos.get("trace")
    if isinstance(trace, dict):
        candidato = trace.get("insumos_factivados")
        if isinstance(candidato, dict) and candidato:
            return _fusionar_planas(candidato)
    return {}



def _formatear_insumo(valor: Any, formato: str) -> Optional[str]:
    """Transcribe la magnitud consumida a la celda forense tipada (unidades declaradas, sin redondeo ciego)."""
    numero = _num(valor)
    if numero is None:
        return None
    if formato == "pct":
        return f"{numero:.1f}%"
    if formato == "num2":
        return f"{numero:.2f}"
    if formato == "num0":
        return f"{numero:.0f}"
    if formato == "delta2":                     # [LN-QBE-123] Magnitud CON signo (ΔxPTS)
        return f"{numero:+.2f}"
    if formato == "metros":
        return f"{numero:.0f}m"
    if formato == "dias":
        return f"{numero:+.1f} d"
    if formato == "partidos":
        return f"{int(round(numero))} partidos"
    if formato == "num1":                       # [LN-QBE-121] Aggregados torneales de un decimal
        return f"{numero:.1f}"
    return f"{numero:.2f}"


def _bloque_equipo(datos: Dict[str, Any], lado: str) -> Dict[str, Any]:
    """Bloque fáctico del club (`home_team_stats` / `home_split_stats`, sin fabricar claves)."""
    for clave in (f"{lado}_team_stats", f"{lado}_split_stats", f"{lado}_stats"):
        bloque = datos.get(clave)
        if isinstance(bloque, dict):
            return bloque
    return {}


def _leer_clave(bloque: Any, claves: Sequence[str]) -> Optional[float]:
    """Primera clave publicada con valor numérico legible; `None` si no hay evidencia."""
    if not isinstance(bloque, dict):
        return None
    for clave in claves:
        if clave in bloque:
            valor = _num(bloque.get(clave))
            if valor is not None:
                return valor
    return None


def _valor_tasa(bloque: Dict[str, Any], claves: Sequence[str]) -> Optional[float]:
    """[ARCH-1.4.41] Tasa canónica = acumulado / PJ (o tasa precomputada ya publicada).

    Sin PJ publicado y sin tasa explícita el valor es `None`: jamás se adivina la escala.
    """
    precomputada = _leer_clave(bloque, tuple(f"{clave}_rate" for clave in claves))
    if precomputada is not None:
        return precomputada
    acumulado = _leer_clave(bloque, claves)
    pj = _num(bloque.get("pj"))
    if acumulado is None or not pj or pj <= 0.0:
        return None
    return acumulado / pj


def _h2h_secuencia(datos: Dict[str, Any]) -> List[Any]:
    secuencia = datos.get("h2h_matches")
    if isinstance(secuencia, (list, tuple)):
        return list(secuencia)
    return []


def _campo_partido(partido: Any, nombre: str) -> Any:
    if isinstance(partido, dict):
        return partido.get(nombre)
    return getattr(partido, nombre, None)


def _resumen_h2h(secuencia: Sequence[Any]) -> Dict[str, Optional[float]]:
    """Resumen empírico H2H en la perspectiva del club local del fixture evaluado.

    Se transcriben únicamente los campos publicados (`goles_local` / `goles_visita`); los
    enfrentamientos sin marcador legible no aportan cifra (cero fabricación).
    """
    victorias_local = 0
    victorias_visita = 0
    gf_local = 0.0
    gf_visita = 0.0
    xg_local: List[float] = []
    xg_visita: List[float] = []
    leidos = 0

    for partido in secuencia:
        gl = _num(_campo_partido(partido, "goles_local"))
        gv = _num(_campo_partido(partido, "goles_visita"))
        if gl is not None and gv is not None:
            leidos += 1
            gf_local += gl
            gf_visita += gv
            if gl > gv:
                victorias_local += 1
            elif gv > gl:
                victorias_visita += 1
        xl = _num(_campo_partido(partido, "xg_local"))
        xv = _num(_campo_partido(partido, "xg_visita"))
        if xl is not None and xv is not None:
            xg_local.append(xl)
            xg_visita.append(xv)

    return {
        "partidos": float(len(secuencia)),
        "leidos": float(leidos),
        "victorias_local": float(victorias_local),
        "victorias_visita": float(victorias_visita),
        "diferencia_goles": (gf_local - gf_visita) if leidos else None,
        "xg_local": (sum(xg_local) / len(xg_local)) if xg_local else None,
        "xg_visita": (sum(xg_visita) / len(xg_visita)) if xg_visita else None,
    }


def _valor_variable(
    modo: str,
    claves: Sequence[str],
    datos: Dict[str, Any],
    bloque_local: Dict[str, Any],
    bloque_visita: Dict[str, Any],
    h2h: Dict[str, Optional[float]],
) -> Tuple[Optional[float], Optional[float]]:
    """Resuelve el par (local, visita) de una variable del catálogo sin inventar cifras."""
    if modo == "directo":
        return _leer_clave(bloque_local, claves), _leer_clave(bloque_visita, claves)
    if modo == "tasa":
        return _valor_tasa(bloque_local, claves), _valor_tasa(bloque_visita, claves)
    if modo == "contexto":
        valor = _leer_clave(datos, claves)
        return valor, (None if valor is None else -valor)
    if modo == "contexto_local":
        return _leer_clave(datos, claves), None
    if modo == "contexto_local_inverso":
        return None, _leer_clave(datos, claves)

    victorias_local = h2h["victorias_local"] if h2h["leidos"] else None
    victorias_visita = h2h["victorias_visita"] if h2h["leidos"] else None
    if modo == "h2h_victorias":
        explicito_local = _leer_clave(datos, ("h2h_wins_local",))
        explicito_visita = _leer_clave(datos, ("h2h_wins_visita",))
        return (
            explicito_local if explicito_local is not None else victorias_local,
            explicito_visita if explicito_visita is not None else victorias_visita,
        )
    if modo == "h2h_diferencia":
        diferencia = h2h["diferencia_goles"]
        explicito_local = _leer_clave(datos, ("h2h_gd_local",))
        explicito_visita = _leer_clave(datos, ("h2h_gd_visita",))
        return (
            explicito_local if explicito_local is not None else diferencia,
            explicito_visita if explicito_visita is not None else (None if diferencia is None else -diferencia),
        )
    if modo == "h2h_xg":
        return h2h["xg_local"], h2h["xg_visita"]
    return None, None


def estructurar_catalogo_44_variables(datos_partido: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """[LN-QBE-101].P.4 — Taxonomía forense de 32 variables en 6 dimensiones canónicas.

    Contrato [LN-QBE-120]: el nombre de la función se CONSERVA (contrato REST `variables_44` y
    dependencias locales) aunque el catálogo vigente sea de 32 variables PRE-KICKOFF.
    Cada renglón exhibe `local` / `visita` / `z_score` / `origen` / `estado` / `impacto`.
    La ausencia de evidencia se declara `SIN EVIDENCIA` con valor `None`; jamás se rellena.
    """
    datos: Dict[str, Any] = datos_partido if isinstance(datos_partido, dict) else {}
    bloque_local = _bloque_equipo(datos, "home")
    bloque_visita = _bloque_equipo(datos, "away")
    h2h = _resumen_h2h(_h2h_secuencia(datos))
    z_scores = datos.get("z_scores") if isinstance(datos.get("z_scores"), dict) else {}

    acumuladas: Dict[str, List[Dict[str, Any]]] = {dimension: [] for dimension, _ in DIMENSIONES_CANONICAS}
    insumos = _insumos_factivados(datos)
    for identificador, nombre, dimension, claves, modo, origen, espacio in _CATALOGO_44:
        # [LN-QBE-123] Cuarentena ANTES de cualquier ruta: la fuente no existe y la celda no se enciende.
        nota_cuarentena = _CUARENTENA.get(identificador)
        if nota_cuarentena is not None:
            acumuladas[dimension].append({
                "id": identificador,
                "variable": nombre,
                "local": None,
                "visita": None,
                "z_score": _num(z_scores.get(identificador)),
                "origen": ESTADO_FUERA_DE_FUENTE,
                "estado": _ESTADO_SIN_EVIDENCIA,
                "impacto": espacio,
                "nota": nota_cuarentena,
            })
            continue
        # [LN-QBE-123] El centinela `0.0` del homologador no es magnitud: la ausencia declarada manda.
        if _presencia_refutada(identificador, insumos):
            acumuladas[dimension].append({
                "id": identificador,
                "variable": nombre,
                "local": None,
                "visita": None,
                "z_score": _num(z_scores.get(identificador)),
                "origen": _ESTADO_SIN_EVIDENCIA,
                "estado": _ESTADO_SIN_EVIDENCIA,
                "impacto": espacio,
                "nota": (
                    "SIN EVIDENCIA: el fixture no reconstruye las fechas previas y el centinela "
                    "`0.0` del homologador no es magnitud [LN-QBE-123]."
                ),
            })
            continue
        # [LN-QBE-102] Precedencia de la telemetría: si el motor consumió el insumo, la celda se
        # enciende en `EVALUADO` con la magnitud tipada. Si no lo publicó, la ruta heredada decide.
        celda = _celda_telemetria(identificador, nombre, origen, espacio, z_scores, insumos)
        if celda is not None:
            acumuladas[dimension].append(celda)
            continue

        local, visita = _valor_variable(modo, claves, datos, bloque_local, bloque_visita, h2h)
        sin_evidencia = local is None and visita is None
        if sin_evidencia:
            estado = _ESTADO_SIN_EVIDENCIA
        elif origen == "Q-BE":
            estado = _ESTADO_DERIVADO
        else:
            estado = _ESTADO_VALIDADO
        acumuladas[dimension].append({
            "id": identificador,
            "variable": nombre,
            "local": None if local is None else round(float(local), 4),
            "visita": None if visita is None else round(float(visita), 4),
            "z_score": _num(z_scores.get(identificador)),
            "origen": origen if not sin_evidencia else _ESTADO_SIN_EVIDENCIA,
            "estado": estado,
            "impacto": espacio,
            "nota": "Ancla canónica acumulado / PJ [ARCH-1.4.41]" if modo == "tasa" else "",
        })


    dimensiones = []
    for dimension, titulo in DIMENSIONES_CANONICAS:
        filas = acumuladas[dimension]
        # [DES-QBE-066] Telemetría dimensional servida: el acordeón bicolor jamás cuenta filas.
        evaluadas = sum(1 for fila in filas if fila.get("estado") == _ESTADO_EVALUADO)
        dimensiones.append({
            "dimension": dimension,
            "titulo": titulo,
            # [LN-QBE-105] Alias aditivo (`nombre` = `titulo`): los consumidores forenses pueden
            # rotular la dimensión sin depender de la clave de exhibición. `dimension` y `titulo`
            # permanecen intactos (cero ruptura del DTO [LN-QBE-101]).
            "nombre": titulo,
            "conteo": len(filas),
            "total_variables": len(filas),
            "variables_evaluadas": evaluadas,
            "tiene_datos": evaluadas > 0,
            "variables": filas,
        })
    return {
        "catalogo_version": CATALOGO_VERSION,
        "total_variables": len(_CATALOGO_44),
        "total_evaluadas": sum(dimension["variables_evaluadas"] for dimension in dimensiones),
        "dimensiones": dimensiones,
    }


# ── [LN-QBE-101].P.5 — Orquestador del bloque `atribucion_factorial` (contrato del endpoint) ──
def _primero(*valores: Any) -> Any:
    for valor in valores:
        if valor is not None:
            return valor
    return None


def _gamma_efectivo(
    A_h: Any, D_a: Any, A_a: Any, D_h: Any, lambda_h: Any, lambda_a: Any, C_h: float, C_a: float
) -> float:
    """Localía efectiva implícita en las λ publicadas (γ̄_base + Δγ_plaza + altitud + descanso).

    Si las intensidades no se publican, se declara 0.0 (sin evidencia ⇒ sin efecto atribuido).
    """
    lh = _num(lambda_h)
    la = _num(lambda_a)
    if lh is None or la is None or lh <= 0.0 or la <= 0.0:
        return 0.0
    equipos = (_amortiguar(A_h) - _amortiguar(D_a)) + (_amortiguar(D_h) - _amortiguar(A_a))
    return math.log(lh / la) - equipos - C_h + C_a


def construir_atribucion_factorial(datos_partido: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """[LN-QBE-101].P.5 — Ensambla el bloque de auditoría que consume la consola forense.

    Fuentes únicas admitidas: el payload fáctico del partido y su `audit_trace_json` persistido.
    Cualquier insumo ausente degrada a `None` / `NEUTRO` / `SIN EVIDENCIA`; cero fabricación.
    """
    datos: Dict[str, Any] = datos_partido if isinstance(datos_partido, dict) else {}
    trace = datos.get("audit_trace") or datos.get("trace") or {}
    if not isinstance(trace, dict):
        trace = {}
    factores = datos.get("factores") or trace.get("factores_entrada") or {}
    if not isinstance(factores, dict):
        factores = {}
    intensidades = datos.get("intensidades") or trace.get("intensidades") or {}
    if not isinstance(intensidades, dict):
        intensidades = {}

    A_h = _primero(factores.get("A_H"), factores.get("A_home"), factores.get("a_h"))
    D_a = _primero(factores.get("D_A"), factores.get("D_away"), factores.get("d_a"))
    A_a = _primero(factores.get("A_A"), factores.get("A_away"), factores.get("a_a"))
    D_h = _primero(factores.get("D_H"), factores.get("D_home"), factores.get("d_h"))
    lambda_h = _primero(
        intensidades.get("lambda_H"), intensidades.get("lambda_home"),
        intensidades.get("lambda_h"), intensidades.get("home"), datos.get("lambda_home"),
    )
    lambda_a = _primero(
        intensidades.get("lambda_A"), intensidades.get("lambda_away"),
        intensidades.get("lambda_a"), intensidades.get("away"), datos.get("lambda_away"),
    )

    q_mod = trace.get("q_mod") if isinstance(trace.get("q_mod"), dict) else {}
    q_home = _primero(q_mod.get("home"), trace.get("q_mod_home"), datos.get("q_mod_home"))
    q_away = _primero(q_mod.get("away"), trace.get("q_mod_away"), datos.get("q_mod_away"))
    C_h = math.log(q_home) if _num(q_home, 0.0) and float(q_home) > 0.0 else 0.0
    C_a = math.log(q_away) if _num(q_away, 0.0) and float(q_away) > 0.0 else 0.0

    gamma_home = _primero(datos.get("gamma_home"), trace.get("gamma_home"))
    if gamma_home is None:
        gamma_home = _gamma_efectivo(A_h, D_a, A_a, D_h, lambda_h, lambda_a, C_h, C_a)

    disponible = all(_num(valor) is not None for valor in (A_h, D_a, A_a, D_h))
    if disponible:
        descomposicion = calcular_atribucion_loglineal(
            A_h, D_a, A_a, D_h, gamma_home, C_h, C_a, lambda_h, lambda_a
        )
    else:
        descomposicion = {
            "delta_ofensiva": None,
            "delta_defensiva": None,
            "delta_contexto": None,
            "delta_neto_total": None,
            "delta_ofensiva_cruda": None,
            "delta_defensiva_cruda": None,
            "delta_ln_lambda": None,
            "residuo_no_atribuido": None,
        }

    split_local = _bloque_equipo(datos, "home")
    split_visita = _bloque_equipo(datos, "away")
    h2h_leidos = _num(_primero(trace.get("h2h_partidos"), datos.get("h2h_partidos")))
    if h2h_leidos is None:
        h2h_leidos = _resumen_h2h(_h2h_secuencia(datos))["leidos"]

    flag_xg = _primero(trace.get("xg_disponible"), datos.get("xg_disponible"))
    flag_xg_calibrado = _primero(trace.get("xg_calibrado"), datos.get("xg_calibrado"))

    # ── [LN-QBE-102] La telemetría fáctica manda sobre la degradación por omisión ──────────────
    # Si el pipeline publicó el insumo, el semáforo se pronuncia sobre el número REALMENTE
    # consumido. `_primero` garantiza que sin paquete telemetrizado (dict vacío) nada cambia.
    insumos = _insumos_factivados(datos)
    # [ARCH-1.4.44] Sello de procedencia Opta: se admite en el paquete de insumos, en la traza o en
    # la raíz del `raw_match_data` sellado por el homologador. `None` con paquete publicado ⇒ se
    # declara `False` (exige certificación); sin paquete ni sello ⇒ contrato heredado intacto.
    sello_opta = _primero(
        insumos.get("xg_es_real_opta"),
        trace.get("xg_es_real_opta"),
        datos.get("xg_es_real_opta"),
    )
    sello_declarado = bool(insumos) or sello_opta is not None
    metricas_xg_publicadas = any(
        _num(insumos.get(clave)) is not None
        for clave in ("xg_local_rate", "xg_visita_rate")
    )
    if _es_certificado(sello_opta):
        flag_xg = True
        flag_xg_calibrado = False
    elif metricas_xg_publicadas and flag_xg is None:
        flag_xg = True
    if _num(insumos.get("h2h_conteo")) is not None:
        h2h_leidos = _num(insumos.get("h2h_conteo"))

    semaforos = evaluar_semaforos_salud_datos(
        xg_disponible=bool(flag_xg),
        xg_calibrado=bool(flag_xg_calibrado),
        pj_sede_local=_primero(insumos.get("pj_sede_local"), split_local.get("pj"), split_local.get("pj_sede"), 0),
        pj_sede_visita=_primero(insumos.get("pj_sede_visita"), split_visita.get("pj"), split_visita.get("pj_sede"), 0),
        h2h_partidos_conteo=h2h_leidos or 0,
        delta_epist=_primero(trace.get("discrepancia_epist"), trace.get("delta_epist"), datos.get("delta_epist"), 0.0),
        q_mod=min(
            _num(_primero(insumos.get("q_mod_h"), q_home), 1.0) or 1.0,
            _num(_primero(insumos.get("q_mod_a"), q_away), 1.0) or 1.0,
        ),
        suficiencia_S_I=_primero(trace.get("suficiencia_S_I"), trace.get("S_I"), datos.get("S_I"), 1),
        xg_es_real_opta=(sello_opta if sello_opta is not None else (False if sello_declarado else None)),
        xg_metricas_publicadas=metricas_xg_publicadas,
    )
    # Degradación honesta de la procedencia: la AUSENCIA de un metadato no es evidencia de
    # insuficiencia. Sin sello de procedencia xG, sin splits y sin Q_mod persistidos, la luz
    # correspondiente se declara NEUTRO (sin veredicto) en vez de acusar un rojo inexistente.
    # [LN-QBE-102] Con telemetría publicada NUNCA se neutraliza: el insumo ya es evidencia.
    if not insumos:
        if flag_xg is None and flag_xg_calibrado is None:
            semaforos["opta"] = NEUTRO
        if not split_local and not split_visita:
            semaforos["sede"] = NEUTRO
        if q_home is None and q_away is None:
            semaforos["ctx"] = NEUTRO
        if not disponible and not trace:
            semaforos = {"opta": NEUTRO, "sede": NEUTRO, "h2h": NEUTRO, "epist": NEUTRO, "ctx": NEUTRO}

    return {
        "disponible": disponible,
        "origen_factores": trace.get("origen_factores") or ("analitico_base" if disponible else "sin_traza"),
        "origen_captura": _primero(datos.get("origen_captura"), trace.get("origen_captura")),
        "descomposicion_log": descomposicion,
        "driver_principal": resolver_driver_principal(descomposicion),
        "semaforos": semaforos,
        "variables_44": estructurar_catalogo_44_variables(datos),
    }

