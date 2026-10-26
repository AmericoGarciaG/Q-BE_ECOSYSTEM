# -*- coding: utf-8 -*-
"""
[LN-QBE-036] Operador de Contracción Bayesiana de Forma Reciente (10 Partidos).
[ARCH-1.4.26] Módulo puro del paquete `src/core/sovereign/` (Capa 4 — Sovereign Memory).
Régimen: [DIRGEN-STRICT] — [ALGO-PROTECTED]; legislado en `docs/LOGIC.md` ([LN-QBE-036]).

Composición sellada (cero duplicación de constantes ni de fórmulas):
* Amortiguamiento hiperbólico: delegado en `[VAULT-CORE-001]`
  (`src/core/intensity_canonical_loglink.py: aplicar_damping_hiperbolico`), con
  κ_net = 0.2500 ABSOLUTO (`VAR-2026-LIVE-AUDIT-J11`/V-2; escalera κ = 2.5·σ_liga derogada).
  El símbolo κ de este módulo NUNCA se usa como escala de damping.
* Pesos Opta 0.65/0.35 y denominador μ_liga/2: transcripción de `[LN-QBE-035-B]` / `[LN-QBE-036]`.

Pureza funcional: sin I/O, sin red, sin SQLAlchemy, sin imports de `src.storage` / `src.ingestion`.
"""

import math

from src.core.intensity_canonical_loglink import aplicar_damping_hiperbolico
from src.models.analytics import BayesianFormResult

# Ponderación adaptativa por ruptura estructural (LOGIC [LN-QBE-036].P.2).
RHO_SHOCK = 0.30      # Q_mod != 1.00 → shock verificado: prima la evidencia reciente.
RHO_ESTABLE = 0.55    # Q_mod == 1.00 → estabilidad: prima el ancla macro de temporada.

# Pesos de la mezcla Opta (LOGIC [LN-QBE-036].P.1 / [LN-QBE-035-B]).
PESO_XG = 0.65
PESO_GF = 0.35

MU_LIGA_DEFAULT = 2.60
SIGMA_LIGA_DEFAULT = 1.0


def _factor_log_diferencial(xg: float, gf: float, mu_liga: float) -> float:
    """A = ln((0.65·xG + 0.35·GF) / (μ_liga/2)) — LOGIC [LN-QBE-036].P.1.

    Guarda fail-loud: evidencia nula o inconsistente no se maquilla con constantes arbitrarias;
    la suficiencia fáctica S(I) es competencia de `[LN-QBE-035-B]`.
    """
    denominador = float(mu_liga) / 2.0
    if denominador <= 0.0:
        raise ValueError(
            f"[LN-QBE-036] μ_liga inválida para la derivación log-diferencial: {mu_liga}. Debe ser > 0."
        )
    numerador = PESO_XG * float(xg) + PESO_GF * float(gf)
    if numerador <= 0.0:
        raise ValueError(
            f"[LN-QBE-036] Evidencia ofensiva no positiva (xG={xg}, GF={gf}): el operador no "
            "fabrica factores; la suficiencia S(I) se gobierna en `[LN-QBE-035-B]`."
        )
    return math.log(numerador / denominador)


def contraer_factores_forma_bayesiana(
    xg_10p: float,
    gf_10p: float,
    xg_macro: float,
    gf_macro: float,
    mu_liga: float = MU_LIGA_DEFAULT,
    q_mod: float = 1.00,
    sigma_liga: float = SIGMA_LIGA_DEFAULT,
) -> BayesianFormResult:
    """[LN-QBE-036] Contracción convexa Normal-Normal entre la evidencia reciente (10P) y el ancla macro.

    * `rho_aplicado` = 0.30 si el shock contextual está verificado (`q_mod != 1.00`); 0.55 en estabilidad.
    * `A*_i = (1 - ρ)·A_reciente + ρ·A_macro`.
    * `A_amortiguado` = `aplicar_damping_hiperbolico(A*, sigma_liga)` — canon `[VAULT-CORE-001]`
      (κ_net = 0.2500 absoluto; `sigma_liga` vestigial en la firma), jamás el κ del decaimiento
      H2H de `[LN-QBE-020]`.

    El mismo operador se aplica al par defensivo (`xGA`/`GC`) por simetría; el signo del factor
    defensivo lo legisla `[LN-QBE-035-B]` en el llamador (cero reglas inventadas aquí).
    """
    a_reciente = _factor_log_diferencial(xg_10p, gf_10p, mu_liga)
    a_macro = _factor_log_diferencial(xg_macro, gf_macro, mu_liga)

    rho_aplicado = RHO_SHOCK if float(q_mod) != 1.00 else RHO_ESTABLE
    a_contraido = (1.0 - rho_aplicado) * a_reciente + rho_aplicado * a_macro
    a_amortiguado = aplicar_damping_hiperbolico(a_contraido, sigma_liga=float(sigma_liga))

    return BayesianFormResult(
        a_reciente=a_reciente,
        a_macro=a_macro,
        a_contraido=a_contraido,
        rho_aplicado=rho_aplicado,
        a_amortiguado=a_amortiguado,
    )
