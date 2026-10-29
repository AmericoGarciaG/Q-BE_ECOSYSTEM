# -*- coding: utf-8 -*-
"""
🛡️ THE SHIELD: JUEZ INMUTABLE DE INTEGRIDAD DE CARTERA Y PISO DE VENTANILLA UNIVERSAL

Expediente: `VAR-2026-LIVE-AUDIT-J11` — Edictos V-2 (compresión hiperbólica pura) y V-3
(guardia universal de familias con cobertura + piso bivariado de $4.00 MXN).

Audita:
- [V-2 / VAULT-CORE-001] κ_net = 0.2500 ABSOLUTO: la compresión deja de escalar con σ_liga
  (escalera κ = 2.5·σ derogada) y la cota del expediente se honra (λ_H(América) ≤ 1.86).
- [V-3 / LN-QBE-070-E] Guardia universal: las CUATRO familias con cobertura (H1, H2, R1, R2)
  reciben el clamping de piso de ventanilla ($2.00 MXN por boleto).
- [V-3 / LN-QBE-071].3 Piso bivariado universal: toda orden de cobertura exige dos piernas
  admisibles (2 · $2.00 = $4.00 MXN).
- [LN-QBE-070-B] El tope de cartera (25.0% del bankroll) permanece INVIOLABLE: el piso jamás
  infla Σ B_i (se financia con la holgura del boleto de ataque; agotada ésta, se declara).
- [GOV-TEST-01] Hermeticidad: cero red, cero DB, cero mocks en producción (funciones puras).

Régimen: [HÍBRIDO DUAL-TRACK] — matemática de cartera ([DIRGEN-STRICT]) verificada por jueces.
"""

import math
from pathlib import Path

from src.core.contracts.portfolio_math import (
    FAMILIAS_CON_COBERTURA,
    aplicar_hard_caps_con_respeto_a_piso,
)
from src.core.intensity_canonical_loglink import (
    KAPPA_NET,
    aplicar_damping_hiperbolico,
    estimar_intensidades_loglineal,
)
from src.core.sovereign_pipeline import generar_distribucion_soberana

# [OPERACIÓN ÉGIDA] Rutas ancladas a la topología de qbe_core (independientes del CWD).
_QBE_CORE_ROOT = Path(__file__).resolve().parents[1]
PORTFOLIO_MATH_PY = _QBE_CORE_ROOT / "src" / "core" / "contracts" / "portfolio_math.py"
LOG_LINK_PY = _QBE_CORE_ROOT / "src" / "core" / "intensity_canonical_loglink.py"

PISO_VENTANILLA = 2.00
PISO_BIVARIADO = 4.00
BANKROLL = 100.0
CAP_CARTERA_PCT = 0.25
CAP_CARTERA = round(BANKROLL * CAP_CARTERA_PCT, 2)
FAMILIAS_HIBRIDAS = ("QBE-H1", "QBE-H2", "QBE-R1", "QBE-R2")

# Fixture SELLADO por el juez GSL-3D ([VAULT-CORE-002]): América vs Rayados, J11.
FIXTURE_AMERICA_MONTERREY = {
    "home_team_stats": {"pj": 10, "gf": 21, "gc": 11, "xg": 19.5},
    "away_team_stats": {"pj": 10, "gf": 18, "gc": 12, "xg": 16.8},
    "home_split_stats": {"pj": 10, "gf": 22, "gc": 10},
    "away_split_stats": {"pj": 10, "gf": 14, "gc": 14},
    "home_team_slug": "club-america",
    "h2h_matches": [
        {"goles_local": 2, "goles_visita": 1, "dias_antiguedad": 120},
        {"goles_local": 1, "goles_visita": 1, "dias_antiguedad": 240},
        {"goles_local": 2, "goles_visita": 2, "dias_antiguedad": 380},
        {"goles_local": 0, "goles_visita": 1, "dias_antiguedad": 520},
        {"goles_local": 3, "goles_visita": 0, "dias_antiguedad": 680},
    ],
}


def _orden(codigo: str, inversion: float, odd_emp: float) -> dict:
    """Orden mínima del contrato de cartera (cero mocks: diccionario del contrato real)."""
    return {
        "strategy_code": codigo,
        "inversion_total": inversion,
        "odd_emp": odd_emp,
        "partido": f"Partido {codigo}",
    }


def _total(ordenes: list) -> float:
    return round(sum(float(o["inversion_total"]) for o in ordenes), 2)


# ---------------------------------------------------------------------------
# 1. [V-2] COMPRESIÓN HIPERBÓLICA PURA: κ_net ABSOLUTO
# ---------------------------------------------------------------------------
def test_v2_kappa_net_es_absoluto_y_no_escala_con_sigma_liga():
    """A = κ_net · tanh(A_crudo / κ_net) con κ_net = 0.2500, invariable ante σ_liga."""
    assert KAPPA_NET == 0.2500, "🚨 [V-2] κ_net debe ser la constante sellada 0.2500"
    assert f"KAPPA_NET = {KAPPA_NET:.4f}" in LOG_LINK_PY.read_text(encoding="utf-8"), (
        "🚨 [V-2] La constante sellada no está transcrita en el módulo canónico"
    )

    for factor in (-3.7, -1.0, -0.25, 0.0, 0.25, 1.0, 3.7, 12.0):
        esperado = KAPPA_NET * math.tanh(factor / KAPPA_NET)
        assert math.isclose(aplicar_damping_hiperbolico(factor), esperado, rel_tol=0, abs_tol=1e-12), (
            f"🚨 [V-2] A({factor}) no es la compresión hiperbólica PURA de κ_net = {KAPPA_NET}"
        )

    # Imparidad estricta: E[A] = 0 (la media cero se preserva por simetría).
    assert aplicar_damping_hiperbolico(0.0) == 0.0
    for factor in (0.4, 1.5, 4.0):
        assert math.isclose(
            aplicar_damping_hiperbolico(factor), -aplicar_damping_hiperbolico(-factor), abs_tol=1e-12
        ), "🚨 [V-2] La compresión perdió su imparidad (media cero)"

    # Cota asintótica: |A| ≤ κ_net (saturación estricta en el cuerpo útil, sin divergencias).
    assert abs(aplicar_damping_hiperbolico(1e6)) <= KAPPA_NET
    assert abs(aplicar_damping_hiperbolico(2.0)) < KAPPA_NET

    # La escalera derogada κ = 2.5·σ_liga NO puede gobernar el cálculo.
    derogado = 2.5 * math.tanh(1.0 / 2.5)
    assert not math.isclose(aplicar_damping_hiperbolico(1.0), derogado, abs_tol=1e-3), (
        "🚨 [V-2] La compresión sigue escalando con σ_liga (escalera κ = 2.5·σ derogada)"
    )
    for sigma in (0.10, 0.25, 0.50, 1.00, 2.50):
        assert math.isclose(
            aplicar_damping_hiperbolico(1.0, sigma_liga=sigma), aplicar_damping_hiperbolico(1.0),
            abs_tol=1e-12,
        ), "🚨 [V-2] σ_liga no debe alterar la compresión pura"
    # Compatibilidad de llamadas selladas (`sovereign/bayesian_form.py` invoca por palabra clave).
    assert math.isclose(
        aplicar_damping_hiperbolico(0.5, sigma_liga=0.25, kappa_mult=2.5),
        aplicar_damping_hiperbolico(0.5), abs_tol=1e-12,
    )


def test_v2_intensidad_de_america_respeta_la_cota_del_expediente():
    """λ_H(América) ≤ 1.86 (edicto V-2) sobre el fixture sellado, con positividad acotada."""
    dist = generar_distribucion_soberana(
        match_id="LIGAMX-J11-AME-MON",
        raw_match_data=FIXTURE_AMERICA_MONTERREY,
        mu_liga=2.65,
        gamma_home_base=0.15,
    )
    assert dist.lambda_home <= 1.86, (
        f"🚨 [V-2] λ_H(América) = {dist.lambda_home:.4f} excede la cota sellada 1.86"
    )
    assert math.isclose(dist.lambda_home, 1.6260, abs_tol=5e-4), (
        f"🚨 [V-2] λ_H(América) derivó del valor certificado 1.6260: {dist.lambda_home:.4f}"
    )
    assert dist.lambda_home <= 1.90, "🚨 [VAULT-CORE-002] Cota GSL-3D rebasada"

    # Invariante de positividad acotada (clamp de producción [0.15, 4.50]) con factores extremos.
    for intensidad in (
        estimar_intensidades_loglineal(A_home=50.0, D_away=-50.0, A_away=-50.0, D_home=50.0)
        + estimar_intensidades_loglineal(A_home=-50.0, D_away=50.0, A_away=50.0, D_home=-50.0)
    ):
        assert 0.15 <= intensidad <= 4.50, f"🚨 [V-2] Intensidad fuera del clamp sellado: {intensidad}"


# ---------------------------------------------------------------------------
# 2. [V-3] GUARDIA UNIVERSAL DE FAMILIAS CON COBERTURA
# ---------------------------------------------------------------------------
def test_v3_guardia_cubre_las_cuatro_familias_con_cobertura():
    """H1, H2, R1 y R2 comparten la MISMA guardia de piso (cero familias huérfanas)."""
    assert tuple(FAMILIAS_CON_COBERTURA) == FAMILIAS_HIBRIDAS, (
        "🚨 [V-3] La guardia universal debe cubrir (QBE-H1, QBE-H2, QBE-R1, QBE-R2)"
    )
    fuente = PORTFOLIO_MATH_PY.read_text(encoding="utf-8")
    assert (
        'FAMILIAS_CON_COBERTURA: Tuple[str, ...] = ("QBE-H1", "QBE-H2", "QBE-R1", "QBE-R2")'
        in fuente
    ), (
        "🚨 [V-3] La guardia debe declarar EXACTAMENTE las cuatro familias bivariadas "
        "(H1, H2, R1, R2): cero familias huérfanas y cero familias ajenas a la cobertura"
    )


# ---------------------------------------------------------------------------
# 3. [V-3] FIXTURE DEL EXPEDIENTE: 4 × $8.00 SOBRE BANKROLL $100
# ---------------------------------------------------------------------------
def test_v3_fixture_4x8_sobre_bankroll_100_honra_los_dos_pisos():
    """El fixture del expediente: el seguro recupera el piso y la cartera no rebasa el 25%."""
    ordenes = [
        _orden("QBE-H1", 8.00, 3.30),
        _orden("QBE-H2", 8.00, 3.45),
        _orden("QBE-R1", 8.00, 3.10),
        _orden("QBE-R2", 8.00, 3.30),
    ]
    salida = aplicar_hard_caps_con_respeto_a_piso(ordenes, BANKROLL)

    assert _total(salida) <= CAP_CARTERA + 1e-9, (
        f"🚨 [LN-QBE-070-B] La cartera rebasó el tope del 25%: {_total(salida)} > {CAP_CARTERA}"
    )
    for orden in salida:
        # Invariante fiduciaria universal: el SEGURO efectivo de toda familia con cobertura queda
        # en o sobre el piso de ventanilla ($2.00 MXN), sea por clamping o por margen suficiente.
        inv = float(orden["inversion_total"])
        odd_emp = float(orden["odd_emp"])
        seguro_efectivo = float(orden.get("boleto_seguro", round(inv / odd_emp, 6)))
        assert seguro_efectivo >= PISO_VENTANILLA - 1e-9, (
            f"🚨 [V-3] {orden['strategy_code']}: seguro efectivo ${seguro_efectivo:.4f} < piso $2.00"
        )
        assert inv >= PISO_BIVARIADO - 1e-9, (
            f"🚨 [V-3 / LN-QBE-071].3 {orden['strategy_code']}: no costea dos piernas admisibles ($4.00)"
        )
        if "boleto_seguro" in orden:
            assert orden["boleto_seguro"] == PISO_VENTANILLA, (
                f"🚨 [V-3] {orden['strategy_code']}: el seguro no recuperó el piso de $2.00 MXN"
            )
            assert orden["boleto_ataque"] >= PISO_VENTANILLA, (
                f"🚨 [V-3 / LN-QBE-071].3 {orden['strategy_code']}: piso bivariado ($4.00) violado"
            )
            assert round(orden["boleto_seguro"] + orden["boleto_ataque"], 2) == inv, (
                f"🚨 La partición del capital no reproduce la inversión en {orden['strategy_code']}"
            )
            assert orden.get("piso_bivariado_insatisfecho") is not True, (
                f"🚨 {orden['strategy_code']}: el libro SÍ tenía holgura para el piso bivariado"
            )
            assert orden["piso_ventanilla_aplicado"] is True

    r2 = next(o for o in salida if o["strategy_code"] == "QBE-R2")
    assert r2["boleto_seguro"] >= PISO_VENTANILLA, (
        "🚨 [V-3] R2 quedó fuera de la guardia universal: su seguro cayó bajo el piso"
    )

    # Margen suficiente: sin compresión bajo el piso no hay cirugía (cero alteración inútil).
    holgada = aplicar_hard_caps_con_respeto_a_piso(
        [
            _orden("QBE-H1", 8.00, 2.90),
            _orden("QBE-H2", 8.00, 2.90),
            _orden("QBE-R1", 8.00, 2.90),
            _orden("QBE-R2", 8.00, 2.90),
        ],
        BANKROLL,
    )
    assert len(holgada) == 4
    assert _total(holgada) <= CAP_CARTERA + 1e-9
    for orden in holgada:
        assert "boleto_seguro" not in orden, (
            f"🚨 {orden['strategy_code']}: clamping aplicado sin necesidad (seguro teórico > piso)"
        )


# ---------------------------------------------------------------------------
# 4. [LN-QBE-070-B] EL TOPE ES INVIOLABLE AUNQUE LA HOLGURA SE AGOTE
# ---------------------------------------------------------------------------
def test_v3_tope_inviolable_con_holgura_agotada_y_declaracion_transparente():
    """8 órdenes de $8.00: el piso compite con el tope; el tope prevalece y la falta se declara."""
    ordenes = [_orden("QBE-R1", 8.00, 3.30) for _ in range(8)]
    salida = aplicar_hard_caps_con_respeto_a_piso(ordenes, BANKROLL)

    assert _total(salida) <= CAP_CARTERA + 1e-9, (
        f"🚨 [LN-QBE-070-B] El piso infló la exposición: {_total(salida)} > {CAP_CARTERA}"
    )
    for orden in salida:
        assert orden["boleto_seguro"] == PISO_VENTANILLA, (
            "🚨 [V-3] El seguro debe recuperar el piso incluso bajo compresión severa"
        )
        assert orden["piso_bivariado_insatisfecho"] is True, (
            "🚨 [GOVERNANCE-01] La insuficiencia del piso bivariado debe declararse, no silenciarse"
        )


def test_v3_familias_sin_cobertura_no_reciben_cirugia_de_piso():
    """D1/D2/C1/00 no portan seguro en tablas: la guardia jamás les inventa piernas."""
    ordenes = [
        _orden("QBE-D1", 8.00, 3.30),
        _orden("QBE-D2", 8.00, 3.30),
        _orden("QBE-C1", 8.00, 3.30),
        _orden("QBE-00", 8.00, 3.30),
    ]
    salida = aplicar_hard_caps_con_respeto_a_piso(ordenes, BANKROLL)

    assert _total(salida) <= CAP_CARTERA + 1e-9
    for orden in salida:
        assert "boleto_seguro" not in orden and "boleto_ataque" not in orden, (
            f"🚨 {orden['strategy_code']}: se inventó una pierna de cobertura inexistente"
        )
        assert "piso_bivariado_insatisfecho" not in orden


def test_v3_orden_terminal_no_es_alterada_sin_cartera():
    """Sin bankroll o sin órdenes el motor devuelve el libro intacto (fail-soft declarado)."""
    vacio = aplicar_hard_caps_con_respeto_a_piso([], BANKROLL)
    assert vacio == []

    ordenes = [_orden("QBE-R2", 8.00, 3.30)]
    intacto = aplicar_hard_caps_con_respeto_a_piso(ordenes, 0.0)
    assert intacto[0]["inversion_total"] == 8.00
    assert "boleto_seguro" not in intacto[0]