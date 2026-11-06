# -*- coding: utf-8 -*-
"""
🏆 Q-BE SOVEREIGN ENGINE — MOTOR DE ORTOGONALIZACIÓN RESIDUAL (GSL-3D)
[LN-QBE-039] & [ARCH-1.4.33] Contenedor de Factores Latentes Tridimensionales.
Base de Gobierno: Kybern Framework v13.5 [DIRGEN-STRICT] — Función Pura en O(m).

Resolución vinculante `VAR-2026-GSL3D-1D-DEGENERACY` (Dictamen Arquitectónico):
la proyección euclidiana escalar de Gram-Schmidt es degenerada en R^1
(Proj_u(X) == X  =>  v_perp == 0), por lo que se sustituye por el **Residuo
Ortogonal Log-Diferencial de Sede** en el espacio logarítmico natural del fútbol:

    v_sede_perp = ln(tasa_sede / tasa_gen) - gamma_base        (ataque)
    v_sede_perp = -[ ln(tasa_sede / tasa_gen) + gamma_base ]   (defensa)

y la síntesis acotada bajo presupuesto cerrado de norma:
    A* = tanh(A_gen + v_sede_perp),   |A*| <= 1.0,  |D*| <= 1.0
"""

import math
from typing import Dict, Any, Tuple, Optional
from pydantic import BaseModel, ConfigDict


EPSILON_ORTOGONAL = 1e-5
TECHO_NORMA_FACTOR = 1.0000


# [LN-QBE-039] VÍA B — formalización de paridad canónica ([LN-QBE-139]/[LN-QBE-140]).
class FactoresGSL3D(BaseModel):
    """Contrato inmutable de factores latentes emitidos por GSL-3D."""
    model_config = ConfigDict(frozen=True, extra="ignore")
    
    A_star: float
    D_star: float
    C_star: float
    residuo_ataque_sede: float
    residuo_defensa_sede: float


def calcular_residuo_sede_log(
    tasa_sede: float,
    tasa_gen: float,
    gamma_base: float = 0.15,
    es_defensa: bool = False
) -> float:
    """
    [LN-QBE-039] Extrae el residuo ortogonal de sede en espacio logarítmico:
    v_perp = ln(tasa_sede / tasa_gen) - gamma_base (para ataque)
    
    Si el desempeño en casa solo iguala a la calidad general más la localía macro,
    el residuo es ~0 (América: cero doble cobro).
    Si el desempeño en casa supera anómalamente a la calidad general (Tigres),
    el residuo captura la fuerza genuina de la plaza.
    """
    t_sede = max(0.2, float(tasa_sede))
    t_gen = max(0.2, float(tasa_gen))
    ratio_log = math.log(t_sede / t_gen)
    
    if not es_defensa:
        # Ataque: lo que excede a la localía macro de goles
        residuo = ratio_log - gamma_base
    else:
        # Defensa: menos goles concedidos en casa es mejor defensa (signo negativo en GC)
        residuo = -(ratio_log + gamma_base)
        
    return residuo


def sintetizar_factor_latente_acotado(
    factor_gen: float,
    residuo_sede: float,
    # ── RECONCILIACIÓN DE TRANSCRIPCIÓN (declarada, no silenciosa) ──────────────────────
    # La ecuación normativa del dictamen §2.C es A* = tanh(A_gen + v_sede_perp): el residuo
    # ortogonal entra con peso unitario (reconstrucción ortogonal íntegra). El bloque de
    # código remitido declaraba `0.50`, constante que CONTRADICE las verificaciones
    # numéricas del propio dictamen (América λ_H <= 1.90 y Tigres λ_H >= 1.35), al DoD
    # exigido (6 PASSED) y a §2.C. Se materializa la ecuación normativa (1.00).
    peso_residuo: float = 1.00,
    techo_norma: float = TECHO_NORMA_FACTOR
) -> float:
    """
    [LN-QBE-039] Sintetiza el factor latente combinando la calidad general
    con el residuo ortogonal de sede bajo compresión hiperbólica tanh.
    """
    combinacion = factor_gen + (peso_residuo * residuo_sede)
    factor_acotado = techo_norma * math.tanh(combinacion / techo_norma)
    return round(factor_acotado, 4)


# [LN-QBE-039] VÍA B — formalización de paridad canónica ([LN-QBE-139]/[LN-QBE-140]).
def resolver_factores_latentes_gsl3d(
    A_gen: float,
    D_gen: float,
    gf_gen: float,
    gc_gen: float,
    gf_sede: Optional[float],
    gc_sede: Optional[float],
    gamma_base: float = 0.15,
    es_local: bool = True,
    C_contexto: float = 0.0
) -> FactoresGSL3D:
    """
    Orquestador GSL-3D: extrae los residuos ortogonales y emite (A*, D*, C*)
    acotados estrictamente en norma <= 1.0.
    """
    if gf_sede is None or gc_sede is None:
        A_star = round(TECHO_NORMA_FACTOR * math.tanh(A_gen / TECHO_NORMA_FACTOR), 4)
        D_star = round(TECHO_NORMA_FACTOR * math.tanh(D_gen / TECHO_NORMA_FACTOR), 4)
        return FactoresGSL3D(
            A_star=A_star,
            D_star=D_star,
            C_star=round(C_contexto, 4),
            residuo_ataque_sede=0.0,
            residuo_defensa_sede=0.0
        )
    
    # 1. Extracción de Residuos Ortogonales
    res_A = calcular_residuo_sede_log(
        tasa_sede=gf_sede, tasa_gen=gf_gen,
        gamma_base=gamma_base if es_local else 0.0,
        es_defensa=False
    )
    res_D = calcular_residuo_sede_log(
        tasa_sede=gc_sede, tasa_gen=gc_gen,
        gamma_base=gamma_base if es_local else 0.0,
        es_defensa=True
    )
    
    # 2. Síntesis Acotada con tanh
    A_star = sintetizar_factor_latente_acotado(factor_gen=A_gen, residuo_sede=res_A)
    D_star = sintetizar_factor_latente_acotado(factor_gen=D_gen, residuo_sede=res_D)
    
    return FactoresGSL3D(
        A_star=A_star,
        D_star=D_star,
        C_star=round(C_contexto, 4),
        residuo_ataque_sede=round(res_A, 4),
        residuo_defensa_sede=round(res_D, 4)
    )


# ═══════════════════════════════════════════════════════════════════════════════════════
# [LN-QBE-039] GSL-3D v2 — PROYECCIÓN ORTOGONAL REAL SOBRE LAS 32 VARIABLES (§7.6)
# Enmienda E-50.3 · docs/LOGIC.md §7.6 · docs/CONSTANTS.md §2
#
# Sustituye la «ortogonalización» escalar de ℝ¹ (v1, arriba, conservada como ruta declarada)
# por un operador sobre VARIABLES: matriz causal M ∈ ℝ^{n×32}, normalización log-diferencial
# contra la media de liga sellada, Gram-Schmidt MODIFICADO con pivote determinista y síntesis
# RMS acotada por tanh. Una dirección duplicada no aporta dirección nueva: la colinealidad
# deja de inflar λ.
# ═══════════════════════════════════════════════════════════════════════════════════════
EPSILON_LOG_NORMALIZACION = 0.5000      # docs/CONSTANTS.md §2 (ε_log)
COBERTURA_MINIMA_POR_ESPACIO = 2        # docs/CONSTANTS.md §2 (n_min)

# Partición legislada 32/32 en los tres espacios de Hilbert + clausura γ.
# valor = (espacio, signo) con signo +1 = «más es mejor en su eje».
ESPECIFICACION_32: Dict[str, Tuple[str, int]] = {
    "V01": ("att", +1), "V02": ("att", +1), "V03": ("att", +1), "V04": ("att", +1),
    "V05": ("att", -1), "V06": ("att", +1), "V07": ("att", +1), "V08": ("att", +1),
    "V09": ("att", -1), "V10": ("att", +1), "V11": ("att", +1), "V21": ("att", +1),
    "V23": ("att", +1), "V24": ("att", +1),
    "V12": ("def", -1), "V13": ("def", -1), "V14": ("def", +1), "V15": ("def", +1),
    "V16": ("def", -1), "V17": ("def", +1), "V18": ("def", +1), "V19": ("def", +1),
    "V20": ("def", +1), "V22": ("def", -1),
    "V25": ("ctx", -1), "V26": ("ctx", +1), "V27": ("ctx", +1), "V28": ("ctx", +1),
    "V31": ("ctx", +1), "V32": ("ctx", -1),
    # Clausura γ: consumidas por la ligadura α (E-50.1), EXCLUIDAS de C* para no contar dos veces.
    "V29": ("gamma", +1), "V30": ("gamma", +1),
}

VARIABLES_POR_ESPACIO: Dict[str, Tuple[str, ...]] = {
    espacio: tuple(sorted(v for v, (e, _) in ESPECIFICACION_32.items() if e == espacio))
    for espacio in ("att", "def", "ctx", "gamma")
}

# ═══════════════════════════════════════════════════════════════════════════════════════
# [E-50.4][Tarea 1] JERARQUÍA FIJA DE ORTOGONALIZACIÓN — prohibido el orden alfabético
#
# Una variable de VOLUMEN nunca puede proyectarse antes que una de DEFINICIÓN: la primera
# consume grados de libertad del subespacio y «mutila» la varianza de la segunda (el pivote
# temprano absorbe la dirección compartida). El orden es LEY, no heurística: rank menor = se
# ortogonaliza antes. Empate imposible (rank único por variable).
# ═══════════════════════════════════════════════════════════════════════════════════════
PRIORIDAD_GS: Dict[str, int] = {
    # H_att — definición primero: xG → big chances → SoT → volumen → fricción → balón parado
    "V06": 10, "V08": 20, "V07": 30, "V01": 40, "V03": 50, "V02": 60, "V04": 70,
    "V05": 80, "V09": 90, "V10": 100, "V11": 110, "V21": 120, "V23": 130, "V24": 140,
    # H_def — ancla defensiva (xGA) → SoTA → acciones → portería → balón parado
    "V12": 10, "V13": 20, "V14": 30, "V15": 40, "V16": 50, "V17": 60, "V18": 70,
    "V19": 80, "V20": 90, "V22": 100,
    # H_ctx — memoria y forma antes que disciplina
    "V26": 10, "V27": 20, "V28": 30, "V31": 40, "V32": 50, "V25": 60,
    # Clausura γ (no se proyecta)
    "V29": 900, "V30": 910,
}


def orden_gs(nombres: Any) -> Tuple[str, ...]:
    """[LN-QBE-039] Orden legislado de Gram-Schmidt (rank ascendente; desempate por ID) — [E-50.4 §T1]."""
    return tuple(sorted(nombres, key=lambda nombre: (PRIORIDAD_GS.get(nombre, 999), nombre)))


class ResultadoGSL3Dv2(BaseModel):
    """[LN-QBE-039] Contrato de salida del motor de proyección ortogonal (§7.6)."""
    model_config = ConfigDict(frozen=True, extra="ignore")

    A_star: float
    D_star: float
    C_star: float
    estados: Dict[str, str]
    contribuciones: Dict[str, float]
    n_att: int
    n_def: int
    n_ctx: int
    cobertura: int
    suficiente: bool
    motivo: str = ""


def _normalizar_log(valor: float, media_liga: float) -> float:
    """[LN-QBE-039] z_i = ln((v_i + ε) / (μ_i + ε)) — log-diferencial contra la liga (§7.6.3).

    `μ_i` DEBE estar sellada por temporada: normalizar contra la media de la propia muestra
    sería fuga de información y queda prohibido por ley.
    """
    eps = EPSILON_LOG_NORMALIZACION
    return math.log((float(valor) + eps) / (float(media_liga) + eps))


def _columnas_utilizables(
    filas: Any, vector: Any, medias_liga: Any, espacio: str
) -> Tuple[Tuple[str, ...], Any]:
    """[LN-QBE-039] Columnas con evidencia COMPLETA (matriz + vector del fixture) y media de liga sellada."""
    nombres = []
    matriz = []
    for nombre in orden_gs(VARIABLES_POR_ESPACIO[espacio]):
        if not isinstance(medias_liga, dict) or nombre not in medias_liga:
            continue
        if not isinstance(vector, dict) or nombre not in vector:
            continue
        columna = []
        completa = True
        for fila in (filas or []):
            if not isinstance(fila, dict) or nombre not in fila:
                completa = False
                break
            valor = fila[nombre]
            if not isinstance(valor, (int, float)) or isinstance(valor, bool):
                completa = False
                break
            columna.append(float(valor))
        if not completa or not columna:
            continue
        valor_fixture = vector[nombre]
        if not isinstance(valor_fixture, (int, float)) or isinstance(valor_fixture, bool):
            continue
        nombres.append(nombre)
        matriz.append(columna)
    return tuple(nombres), matriz


def _gram_schmidt_modificado(
    nombres: Tuple[str, ...], matriz: Any, eps_ort: float, pesos: Any = None
) -> Tuple[list, Dict[str, str], Dict[str, list]]:
    """[LN-QBE-039] MGS con jerarquía legislada ([E-50.4 §T1]) y peso β PRE-proyección (§7.6.4).

    Cada variable es una COLUMNA de longitud n (la muestra histórica del club). Antes de
    ortogonalizar se aplica el peso β_i ([E-50.4 §T2]): el producto interno opera sobre el
    vector PONDERADO, de modo que un β_i = 0 apaga la variable (Lasso) y el residuo de las
    siguientes se calcula sin su dirección. El residuo se proyecta contra las direcciones ya
    aceptadas y se registran los coeficientes `c_ij`, que evalúan el partido nuevo en la MISMA
    descomposición.

    Devuelve (base [(nombre, q, ‖r‖)], estados por variable, coeficientes por variable). Una
    variable con residuo < `eps_ort` es COLINEAL: aporta exactamente 0 y se declara con su pivote.
    """
    base: list = []
    estados: Dict[str, str] = {}
    coeficientes: Dict[str, list] = {}

    for indice, nombre in enumerate(nombres):
        beta_variable = 1.0
        if isinstance(pesos, dict):
            beta_variable = float(pesos.get(nombre, 1.0))
            if not math.isfinite(beta_variable) or beta_variable < 0.0:
                raise ValueError(
                    f"[E-50.4 §T2] Peso β inválido para {nombre}: {beta_variable!r} (finito y ≥ 0)."
                )
        if beta_variable == 0.0:
            # [E-50.4 §T2] Lasso: la variable se APAGA y no participa de la base ni del factor.
            estados[nombre] = "APAGADA_L1"
            coeficientes[nombre] = []
            continue
        vector = [beta_variable * float(matriz[indice][fila]) for fila in range(len(matriz[indice]))]
        acumulado: list = []
        for previo, q, _norma in base:
            producto = sum(a * b for a, b in zip(vector, q))
            vector = [a - producto * b for a, b in zip(vector, q)]
            acumulado.append((previo, producto))
        norma = math.sqrt(sum(componente * componente for componente in vector))
        if norma < float(eps_ort):
            estados[nombre] = "COLINEAL"
            coeficientes[nombre] = []
            continue
        q = [componente / norma for componente in vector]
        # Orientación determinista: la carga dominante se fuerza positiva (signo auditable).
        dominante = max(range(len(q)), key=lambda i: abs(q[i]))
        if q[dominante] < 0.0:
            q = [-componente for componente in q]
        base.append((nombre, q, norma))
        coeficientes[nombre] = acumulado
        estados[nombre] = "CONSUMIDA"
    return base, estados, coeficientes


def _sintetizar_espacio(
    nombres: Tuple[str, ...],
    matriz: Any,
    vector: Dict[str, Any],
    medias_liga: Dict[str, Any],
    espacio: str,
    eps_ort: float,
    techo_norma: float,
    pesos: Any = None,
) -> Tuple[float, Dict[str, str], Dict[str, float], int]:
    """[LN-QBE-039] Factor del espacio: RMS de la proyección sobre la base ortonormal (§7.6.5).

    El partido nuevo se evalúa con LOS MISMOS coeficientes `c_ij` de la descomposición histórica
    y con el MISMO peso β_i:
        r_i^fix = β_i·z_i^fix − Σ_{j<i} c_ij·(β_j·z_j^fix),   β̂_i = r_i^fix / ‖r_i‖
    de modo que una dirección duplicada (colineal) no recibe carga y una apagada por L1 no infla.
    """
    base, estados, coeficientes = _gram_schmidt_modificado(nombres, matriz, eps_ort, pesos)
    contribuciones: Dict[str, float] = {nombre: 0.0 for nombre in nombres}

    if not base:
        return 0.0, estados, contribuciones, 0

    z = {nombre: _normalizar_log(vector[nombre], medias_liga[nombre]) for nombre in nombres}
    if isinstance(pesos, dict):
        z = {nombre: float(pesos.get(nombre, 1.0)) * valor for nombre, valor in z.items()}
    suma = 0.0
    for origen, _q, norma in base:
        residuo = z[origen]
        for previo, coeficiente in coeficientes[origen]:
            residuo -= coeficiente * z[previo]
        beta = residuo / norma
        sigma = ESPECIFICACION_32[origen][1]
        suma += sigma * beta
        contribuciones[origen] = sigma * beta / math.sqrt(len(base))

    factor = techo_norma * math.tanh(suma / math.sqrt(len(base)))
    return factor, estados, contribuciones, len(base)


def resolver_factores_latentes_gsl3d_v2(
    matriz_causal: Any,
    vector_fixture: Any,
    medias_liga: Any,
    eps_ort: float = EPSILON_ORTOGONAL,
    pesos: Any = None,
) -> ResultadoGSL3Dv2:
    """[LN-QBE-039] GSL-3D v2 — factores (A*, D*, C*) desde la matriz causal del club (§7.6).

    `matriz_causal` es una secuencia de registros `{V##: valor}` (n ≥ 1 filas pre-kickoff);
    `vector_fixture` es el registro del partido evaluado (mismo esquema); `medias_liga` es el
    libro de medias selladas por temporada. La ausencia de una celda no se imputa: la variable
    se declara `SIN_EVIDENCIA` y queda fuera del álgebra.

    [E-50.4 §T2] `pesos` es el vector β (V## → β ≥ 0) aplicado **antes** del residuo de
    Gram-Schmidt. `β = 0` apaga la variable (`APAGADA_L1`); `None` ⇒ β ≡ 1 (peso neutro).
    """
    if isinstance(pesos, dict):
        for clave, valor in pesos.items():
            if not isinstance(valor, (int, float)) or isinstance(valor, bool):
                raise ValueError(f"[E-50.4 §T2] Peso β no numérico para {clave!r}: {valor!r}.")
            if not math.isfinite(float(valor)) or float(valor) < 0.0:
                raise ValueError(f"[E-50.4 §T2] Peso β inválido para {clave!r}: {valor!r}.")
    filas = list(matriz_causal or [])
    estados: Dict[str, str] = {}
    contribuciones: Dict[str, float] = {}
    factores: Dict[str, float] = {}
    conteo: Dict[str, int] = {}

    for espacio, techo in (("att", TECHO_NORMA_FACTOR), ("def", TECHO_NORMA_FACTOR), ("ctx", 0.25)):
        nombres, matriz = _columnas_utilizables(filas, vector_fixture, medias_liga, espacio)
        factor, estados_espacio, contrib_espacio, n_consumidas = _sintetizar_espacio(
            nombres, matriz, vector_fixture or {}, medias_liga or {}, espacio, eps_ort, techo, pesos
        )
        factores[espacio] = round(factor, 6)
        conteo[espacio] = n_consumidas
        estados.update(estados_espacio)
        contribuciones.update(contrib_espacio)
        for nombre in VARIABLES_POR_ESPACIO[espacio]:
            if nombre not in estados:
                estados[nombre] = "SIN_EVIDENCIA"
                contribuciones[nombre] = 0.0

    # Clausura γ: V29/V30 no entran a C* (ya viven en la ligadura α) — cero doble conteo.
    for nombre in VARIABLES_POR_ESPACIO["gamma"]:
        estados[nombre] = "CLAUSURA_GAMMA"
        contribuciones[nombre] = 0.0

    suficiente = (
        conteo["att"] >= COBERTURA_MINIMA_POR_ESPACIO
        and conteo["def"] >= COBERTURA_MINIMA_POR_ESPACIO
    )
    motivo = "" if suficiente else (
        f"COBERTURA_INSUFICIENTE(n_att={conteo['att']},n_def={conteo['def']},"
        f"min={COBERTURA_MINIMA_POR_ESPACIO})"
    )
    return ResultadoGSL3Dv2(
        A_star=factores["att"],
        D_star=factores["def"],
        C_star=factores["ctx"],
        estados=estados,
        contribuciones=contribuciones,
        n_att=conteo["att"],
        n_def=conteo["def"],
        n_ctx=conteo["ctx"],
        cobertura=sum(1 for e in estados.values() if e == "CONSUMIDA"),
        suficiente=suficiente,
        motivo=motivo,
    )
