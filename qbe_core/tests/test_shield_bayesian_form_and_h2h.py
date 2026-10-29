# -*- coding: utf-8 -*-
"""
🛡️ THE SHIELD: JUEZ INMUTABLE DE CAPA 4 (MEMORIA HISTÓRICA & H2H)
Validación de:
- [LN-QBE-036] Contracción Bayesiana de Forma Reciente (10 Partidos).
- [LN-QBE-020-C] Kernel H2H Empírico en Eje Localía (κ-Decay reutilizado de [LN-QBE-020]).
- [ARCH-1.4.26] Pureza Funcional sin I/O en src/core/sovereign/.

Nota de trazabilidad (Decreto Sprint 3 — enmiendas ratificadas del pre-vuelo):
* D-2: el kernel empírico en eje localía se sella bajo `[LN-QBE-020-C]` porque `[LN-QBE-020]` ya
  está materializado (`src/core/temporal.py`, Juez `abstract_test_LN_QBE_020_temporal.py`) y opera
  sobre el eje FAVORITO/UNDERDOG. Cero doble fuente de verdad sobre un nodo [ALGO-PROTECTED].
* D-3: el damping se delega en `[VAULT-CORE-001]` (κ_net = 0.2500 ABSOLUTO; la escalera
  κ = 2.5·σ_liga queda derogada por `VAR-2026-LIVE-AUDIT-J11`/V-2). El κ = ln(2)/180 del
  decaimiento H2H queda expresamente prohibido como escala de amortiguamiento.
"""

import math
import pytest
from pydantic import BaseModel


def test_ln_qbe_036_bayesian_form_contraction():
    """Audita que la contracción combine forma reciente y macro con respeto a shocks."""
    try:
        from src.core.sovereign.bayesian_form import contraer_factores_forma_bayesiana
    except ImportError as e:
        pytest.fail(f"❌ [LN-QBE-036] Falta el módulo bayesian_form.py: {e}")

    from src.core.intensity_canonical_loglink import KAPPA_NET

    # Escenario 1: Sin shock (Q_mod = 1.0) -> Ponderación equilibrada (rho = 0.55)
    res_neutro = contraer_factores_forma_bayesiana(
        xg_10p=2.10, gf_10p=2.00,  # Racha reciente muy goleadora
        xg_macro=1.20, gf_macro=1.10,  # Historial macro modesto
        mu_liga=2.60,
        q_mod=1.00
    )
    # Debe contraer hacia abajo por la pesadez del macro
    assert res_neutro.a_reciente > res_neutro.a_macro
    assert res_neutro.a_macro < res_neutro.a_contraido < res_neutro.a_reciente
    assert res_neutro.rho_aplicado == 0.55

    # Escenario 2: Con shock estructural positivo (Q_mod = 1.05) -> Prima lo reciente (rho = 0.30)
    res_shock = contraer_factores_forma_bayesiana(
        xg_10p=2.10, gf_10p=2.00,
        xg_macro=1.20, gf_macro=1.10,
        mu_liga=2.60,
        q_mod=1.05
    )
    # Al primar lo reciente, el factor contraído debe ser significativamente más alto
    assert res_shock.a_contraido > res_neutro.a_contraido
    assert res_shock.rho_aplicado == 0.30

    # [D-3] Amortiguamiento delegado en [VAULT-CORE-001]: κ_net = 0.2500 (NUNCA ln(2)/180).
    kappa_damp = KAPPA_NET
    assert res_neutro.a_amortiguado == pytest.approx(
        kappa_damp * math.tanh(res_neutro.a_contraido / kappa_damp), abs=1e-12
    )
    assert abs(res_neutro.a_amortiguado - 0.0038509775) > 1e-3, (
        "El factor amortiguado no puede colapsar a la constante κ del decaimiento H2H."
    )


def test_ln_qbe_020_c_h2h_temporal_decay_kernel():
    """Audita la ponderación de los últimos 5 partidos directos con vida media de 180 días."""
    try:
        from src.core.sovereign.h2h_kernel import calcular_matriz_h2h_empirica
    except ImportError as e:
        pytest.fail(f"❌ [LN-QBE-020-C] Falta el módulo h2h_kernel.py: {e}")

    # 5 enfrentamientos directos ordenados de más reciente a más antiguo
    h2h_matches = [
        {"goles_local": 2, "goles_visita": 1, "dias_antiguedad": 30},   # Muy reciente -> gran peso
        {"goles_local": 1, "goles_visita": 1, "dias_antiguedad": 120},  # < 180 días
        {"goles_local": 0, "goles_visita": 2, "dias_antiguedad": 210},  # > 180 días -> peso atenuado
        {"goles_local": 3, "goles_visita": 0, "dias_antiguedad": 380},  # > 1 año -> peso marginal
        {"goles_local": 1, "goles_visita": 0, "dias_antiguedad": 540},  # Antiguo
    ]

    res_h2h = calcular_matriz_h2h_empirica(h2h_matches)

    # Invariantes matemáticas
    assert abs(res_h2h.suma_probabilidades - 1.0) <= 1e-4, "La matriz H2H debe sumar 1.0000"
    assert res_h2h.p_local > res_h2h.p_visita, "El local domina por victorias recientes"
    assert res_h2h.peso_total_efectivo > 0.0

    # [LN-QBE-020-B] Fail-Loud: sin evidencia real no se fabrican partidos sintéticos.
    with pytest.raises(ValueError):
        calcular_matriz_h2h_empirica([])


def test_h2h_simplex_clausura_barrido():
    """[VAR-2026-10-17-H2H-SIMPLEX · ALT-A] Cierre exacto del símplex ante un barrido de desenlace.

    Cerrojo de regresión: el kernel acumulaba el denominador `W = sum(pesos)` con la suma
    COMPENSADA de CPython ≥ 3.12 y los numeradores con `+=` naíf. Cuando un solo desenlace absorbe
    la ventana (barrido), el numerador debe ser idénticamente igual a `W`; con algoritmos distintos
    difería en 1 ulp ⇒ `p_k = 1.0000000000000002` ⇒ `H2HKernelResult.Field(le=1.0)` rechazaba la
    matriz y el fixture quedaba sin distribución soberana (3 fixtures de LIGAMX-J6/J7).

    Las antigüedades de este Juez son exactamente las que reproducen el desborde:
    `sum(pesos) = 3.1971793144097447` vs acumulación naíf `3.197179314409745`.
    """
    from src.core.sovereign.h2h_kernel import calcular_matriz_h2h_empirica

    dias = [30, 120, 210, 380]

    def _ventana(goles_local: int, goles_visita: int):
        return [
            {"goles_local": goles_local, "goles_visita": goles_visita, "dias_antiguedad": d}
            for d in dias
        ]

    # Caso A — barrido de victoria local: P(local) == 1.0 EXACTO (no 0.9999999999999999).
    res_local = calcular_matriz_h2h_empirica(_ventana(2, 0))
    assert res_local.p_local == 1.0, f"Desborde/degradación del símplex: {res_local.p_local!r}"
    assert res_local.p_empate == 0.0
    assert res_local.p_visita == 0.0
    assert res_local.suma_probabilidades == 1.0, (
        f"La suma de masa del barrido debe ser 1.0 exacto: {res_local.suma_probabilidades!r}"
    )

    # Caso B — barrido de victoria visitante (LIGAMX-J6-05: 0-2 / 0-1 / 1-2 / 0-2).
    res_visita = calcular_matriz_h2h_empirica(_ventana(0, 2))
    assert res_visita.p_visita == 1.0, f"Desborde del símplex en visita: {res_visita.p_visita!r}"
    assert res_visita.suma_probabilidades == 1.0

    # Caso C — barrido de empates.
    res_empate = calcular_matriz_h2h_empirica(_ventana(1, 1))
    assert res_empate.p_empate == 1.0, f"Desborde del símplex en empate: {res_empate.p_empate!r}"
    assert res_empate.suma_probabilidades == 1.0

    # Caso D — ventana mixta: ninguna coordenada puede exceder el símplex y la suma cierra.
    mixta = [
        {"goles_local": 2, "goles_visita": 1, "dias_antiguedad": dias[0]},
        {"goles_local": 0, "goles_visita": 1, "dias_antiguedad": dias[1]},
        {"goles_local": 1, "goles_visita": 1, "dias_antiguedad": dias[2]},
        {"goles_local": 3, "goles_visita": 0, "dias_antiguedad": dias[3]},
    ]
    res_mixta = calcular_matriz_h2h_empirica(mixta)
    for etiqueta, valor in (
        ("p_local", res_mixta.p_local),
        ("p_empate", res_mixta.p_empate),
        ("p_visita", res_mixta.p_visita),
    ):
        assert 0.0 <= valor <= 1.0, f"[LN-QBE-020-C] {etiqueta} fuera del símplex: {valor!r}"
    assert abs(res_mixta.suma_probabilidades - 1.0) <= 1e-12


def test_arch_1_4_26_core_pure_function_isolation():
    """Audita que los módulos en src/core/sovereign/ no importen librerías de DB ni red."""
    import ast
    from pathlib import Path

    # [OPERACIÓN ÉGIDA] Ruta anclada a la topología de qbe_core (independiente del CWD).
    core_dir = Path(__file__).resolve().parents[1] / "src" / "core" / "sovereign"
    if not core_dir.exists():
        pytest.fail("Directorio src/core/sovereign no existe aún.")

    for py_file in core_dir.glob("*.py"):
        with open(py_file, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "sqlalchemy" not in alias.name
                    assert "requests" not in alias.name
                    assert "playwright" not in alias.name
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    assert "sqlalchemy" not in node.module
                    assert "src.storage" not in node.module
                    assert "src.ingestion" not in node.module


# =============================================================================
# H-16 — ERRADICACIÓN DEL CÓDIGO MUERTO: CONEXIÓN REAL DE LA CAPA 4 AL MOTOR
# Los Jueces anteriores certifican la pureza de los módulos; estos certifican que el MOTOR EN
# PRODUCCIÓN (`src/core/sovereign_pipeline.py`, nodo [VAULT-CORE-005]) los consume de verdad.
# =============================================================================

_REGISTRO_BASE_SUFICIENTE = {
    "home_team_stats": {"pj": 8, "gf": 14, "gc": 8, "xg": 1.65},
    "away_team_stats": {"pj": 8, "gf": 9, "gc": 12, "xg": 1.10},
}

_FORM_10P_SUFICIENTE = {
    "home": {
        "xg_10p": 2.30, "gf_10p": 2.40, "xga_10p": 0.70, "gc_10p": 0.80,
        "xg_macro": 1.40, "gf_macro": 1.35, "xga_macro": 1.30, "gc_macro": 1.25,
        "q_mod": 1.00,
    },
    "away": {
        "xg_10p": 0.80, "gf_10p": 0.70, "xga_10p": 1.90, "gc_10p": 2.00,
        "xg_macro": 1.15, "gf_macro": 1.05, "xga_macro": 1.45, "gc_macro": 1.50,
        "q_mod": 1.00,
    },
}

_H2H_DOMINIO_LOCAL = [
    {"goles_local": 3, "goles_visita": 0, "dias_antiguedad": 25},
    {"goles_local": 2, "goles_visita": 0, "dias_antiguedad": 95},
    {"goles_local": 4, "goles_visita": 1, "dias_antiguedad": 190},
    {"goles_local": 2, "goles_visita": 1, "dias_antiguedad": 300},
    {"goles_local": 1, "goles_visita": 1, "dias_antiguedad": 420},
]


def test_ln_qbe_036_wired_into_sovereign_pipeline():
    """[LN-QBE-036] conectado: si el registro publica `form_10p`, el motor usa el operador bayesiano.

    Guarda de gobierno: cuando el registro NO publica la forma reciente, el motor debe seguir por la
    ruta analítica sellada `[LN-QBE-035-B]` sin una sola variación (cero regresión silenciosa).
    """
    from src.core.sovereign_pipeline import (
        derivar_factores_con_procedencia,
        derivar_factores_estructurales,
        generar_distribucion_soberana,
    )

    factores_base, origen_base = derivar_factores_con_procedencia(_REGISTRO_BASE_SUFICIENTE)
    assert origen_base == "analitico_base", "Sin `form_10p` la Capa 4 no debe intervenir."
    assert factores_base == derivar_factores_estructurales(_REGISTRO_BASE_SUFICIENTE), (
        "El envoltorio trazable no puede alterar los factores de la ruta sellada [LN-QBE-035-B]."
    )

    registro_capa4 = dict(_REGISTRO_BASE_SUFICIENTE)
    registro_capa4["form_10p"] = _FORM_10P_SUFICIENTE

    factores_capa4, origen_capa4 = derivar_factores_con_procedencia(registro_capa4)
    assert origen_capa4 == "bayesiano_10p"
    assert factores_capa4 != factores_base, "El operador bayesiano debe sustituir la mezcla analítica."

    # Coherencia física del signo defensivo legislado por [LN-QBE-035-B]: D = -ln(tasa / μ_base).
    A_home, D_away, A_away, D_home = factores_capa4
    assert A_home > A_away, "Local con xG_10p=2.30 debe superar a la visita con xG_10p=0.80."
    assert D_home > 0.0, "Defensa local sólida (xGA_10p=0.70) ⇒ D_home positivo (frena a la visita)."
    assert D_away < 0.0, "Defensa visita frágil (xGA_10p=1.90) ⇒ D_away negativo (suelta al local)."

    salida = generar_distribucion_soberana("TEST-CAPA4-FORMA", registro_capa4)
    assert salida.es_operable is True
    assert salida.origen_factores == "bayesiano_10p"
    assert salida.audit_trace.origen_factores == "bayesiano_10p"
    assert salida.p_local > salida.p_visitante, "Incoherencia física: el local debe dominar el 1X2."
    assert abs(salida.p_local + salida.p_empate + salida.p_visitante - 1.0) <= 1e-4


def test_ln_qbe_020_c_wired_delta_epist_and_zero_h2h_law():
    """[LN-QBE-020-C] conectado: el kernel H2H alimenta Δ_epist; sin evidencia rige la Ley Zero-H2H.

    Se certifica además el alcance legislado por el **Decreto de Fusión Convexa `[LN-QBE-104]`**:
    Δ_epist se **deriva y publica** (insumo de calibración futura `[LN-QBE-040]`) y el símplex Poisson
    paramétrico SÍ se mezcla con el kernel empírico bajo la ley w_H2H = min(0.25, N·0.05). Este Juez
    certifica la ESTRUCTURA de la mezcla (cierre del símplex, acotamiento por componente, tope del peso
    y coherencia Δ(∞) ≥ TVD), jamás la igualdad pre-fusión que el Sprint 3 congeló — enmienda E-2.
    """
    from src.core.sovereign_pipeline import (
        derivar_discrepancia_epistemica,
        generar_distribucion_soberana,
    )

    # Caso A — Ley Zero-H2H ([LN-QBE-020-B]): sin enfrentamientos, w_H2H = 0.0 y Δ_epist = 0.0.
    salida_sin_h2h = generar_distribucion_soberana("TEST-CAPA4-ZERO-H2H", _REGISTRO_BASE_SUFICIENTE)
    assert salida_sin_h2h.delta_epist == 0.0
    assert salida_sin_h2h.audit_trace.discrepancia_epist == 0.0
    assert salida_sin_h2h.audit_trace.kernel_h2h_empirico == {"peso_h2h": 0.0, "peso_liga": 1.0}

    delta_explicito, evidencia = derivar_discrepancia_epistemica(
        {"p_local": 0.50, "p_empate": 0.20, "p_visitante": 0.30}, None
    )
    assert (delta_explicito, evidencia) == (0.0, {"peso_h2h": 0.0, "peso_liga": 1.0})
    # Ley Zero-H2H también para evidencia explícitamente vacía: el MOTOR gobierna con w_H2H = 0.0
    # (el fail-loud vive en el kernel crudo `[LN-QBE-020-C]`, ya certificado por el Juez anterior).
    assert derivar_discrepancia_epistemica(
        {"p_local": 0.50, "p_empate": 0.20, "p_visitante": 0.30}, []
    ) == (0.0, {"peso_h2h": 0.0, "peso_liga": 1.0})

    # Caso B — Con evidencia H2H real: el kernel se invoca y Δ_epist ∈ (0, 1).
    registro_h2h = dict(_REGISTRO_BASE_SUFICIENTE)
    registro_h2h["h2h_matches"] = _H2H_DOMINIO_LOCAL

    salida_con_h2h = generar_distribucion_soberana("TEST-CAPA4-H2H", registro_h2h)
    delta_epist = salida_con_h2h.delta_epist
    assert 0.0 < delta_epist < 1.0, "Δ_epist es una distancia de variación total en [0, 1)."
    assert salida_con_h2h.audit_trace.discrepancia_epist == delta_epist
    kernel = salida_con_h2h.audit_trace.kernel_h2h_empirico
    assert kernel["p_local"] > kernel["p_visita"], "El kernel H2H debe reflejar el dominio local."
    assert abs(kernel["p_local"] + kernel["p_empate"] + kernel["p_visita"] - 1.0) <= 1e-4

    # [LN-QBE-104] Decreto de Fusión Convexa (Generador A ∪ Generador C): la evidencia H2H SÍ mezcla el
    # símplex publicado con w_H2H = min(0.25, N·0.05). Enmienda E-2: se certifica la ESTRUCTURA de la
    # mezcla, no la igualdad pre-fusión congelada por el Sprint 3.
    peso_h2h = kernel["peso_h2h"]
    assert 0.0 < peso_h2h <= 0.25, "w_H2H debe saturar en el tope fiduciario 0.25."
    assert peso_h2h == pytest.approx(min(0.25, len(_H2H_DOMINIO_LOCAL) * 0.05), abs=1e-12)
    assert kernel["peso_liga"] == pytest.approx(1.0 - peso_h2h, abs=1e-12)

    # 1) Cierre del símplex: una combinación convexa habita Δ².
    suma_hibrida = salida_con_h2h.p_local + salida_con_h2h.p_empate + salida_con_h2h.p_visitante
    assert abs(suma_hibrida - 1.0) <= 1e-12, f"El símplex híbrido no cierra: Σ = {suma_hibrida!r}"

    # 2) Acotamiento por componente: min(P_A, P_C) ≤ P_hib ≤ max(P_A, P_C).
    pares = (
        ("p_local", salida_con_h2h.p_local, salida_sin_h2h.p_local, kernel["p_local"]),
        ("p_empate", salida_con_h2h.p_empate, salida_sin_h2h.p_empate, kernel["p_empate"]),
        ("p_visitante", salida_con_h2h.p_visitante, salida_sin_h2h.p_visitante, kernel["p_visita"]),
    )
    for etiqueta, hibrida, poisson_pura, empirica in pares:
        assert min(poisson_pura, empirica) - 1e-12 <= hibrida <= max(poisson_pura, empirica) + 1e-12, (
            f"P_hib({etiqueta}) = {hibrida!r} se sale del intervalo convexo "
            f"[{min(poisson_pura, empirica)!r}, {max(poisson_pura, empirica)!r}]."
        )
    # 3) La mezcla NO es la identidad: con evidencia y N ≥ 1 el kernel desplaza el símplex publicado.
    assert salida_con_h2h.p_local != pytest.approx(salida_sin_h2h.p_local, abs=1e-12)

    # 4) [LN-QBE-104] Δ_epist(∞) = max_k |P_A − P_C| y ACOTA por arriba a la TVD [LN-QBE-020-C].
    delta_infinito = salida_con_h2h.epistemic_delta
    esperado_infinito = max(
        abs(salida_sin_h2h.p_local - kernel["p_local"]),
        abs(salida_sin_h2h.p_empate - kernel["p_empate"]),
        abs(salida_sin_h2h.p_visitante - kernel["p_visita"]),
    )
    assert delta_infinito == pytest.approx(esperado_infinito, abs=1e-6)
    assert 0.0 < delta_infinito <= 1.0
    assert delta_epist <= delta_infinito + 1e-6, "La TVD jamás puede exceder la norma infinito."
    assert salida_con_h2h.audit_trace.epistemic_delta == pytest.approx(delta_infinito, abs=1e-12)

