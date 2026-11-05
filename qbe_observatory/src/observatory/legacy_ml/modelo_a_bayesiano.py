# -*- coding: utf-8 -*-
"""`[SPRINT-50]` Modelo A v2 — NLL de marcador exacto + penalización L1 sobre 23 multiplicadores.

Régimen ``[DIRGEN-STRICT]``. El erudito no inventa matemática: delega la distribución en
``qbe_core`` (matriz de Poisson/Dixon-Coles, `[VAULT-CORE-004]`) y sólo busca los pesos β.

Función objetivo ([E-50.6] §T4)
-------------------------------
    L(β) = −Σ ln P(G_H = x, G_A = y | β) + λ_L1 · Σ |β_j|

* La verosimilitud se evalúa sobre el **marcador exacto** de cada partido del Train con la matriz
  Dixon-Coles (τ incluido) y el ρ continuo de `[E-50.5]`.
* El puente legislado `[LN-QBE-147]` sigue gobernando β → (λ_H, λ_A): sólo V07/V13 tienen canal.
* La penalización L1 apaga las 21 dimensiones sin canal (su gradiente de datos es nulo y el del
  regularizador no), con umbralización dura posterior |β| < 1e-2 ⇒ 0.0.

Búsqueda determinista: rejilla gruesa sobre el canal (V07, V13) + L-BFGS-B numérico. Sin
aleatoriedad: mismo dataset ⇒ mismo vector.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np

DIR_SCRIPTS = Path(__file__).resolve().parent
if str(DIR_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(DIR_SCRIPTS))

import preparar_dataset_ml as base  # noqa: E402
from scipy.optimize import minimize  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, OSError, ValueError):  # pragma: no cover
        pass

MODELO = "A"
MOTOR = "scipy.optimize.minimize·L-BFGS-B·NLL+L1"
PESO_MIN, PESO_MAX = 0.0, 2.0          # [E-50.6] el Lasso exige 0 alcanzable
PASO_REJILLA = 0.25
LAMBDA_L1 = 0.5                        # λ_L1 en unidades de suma (E-50.6 §T4)
UMBRAL_APAGADO = 1e-2                  # |β| < umbral ⇒ 0.0 exacto (umbralización Lasso)
EPS_L1 = 1e-3                          # suavizado |β| ≈ √(β²+ε²) − ε (gradiente finito)

#: Constantes selladas del puente `[LN-QBE-147]` (paridad con `probabilidades_puente`).
#: [E-50.6] La NLL usa un retículo ampliado (0..10) y censura los marcadores extremos: el
#: retículo 0..6 del símplex publicado dejaría fuera del soporte los 9-0 observados.
K_MAX = 10
CENSURA_GOLES = K_MAX
RHO_TACTICA, RHO_BASE = -0.12, -0.05
CORTE_TACTICO, VENTANA_RHO = 2.65, 0.10
SIGMOIDE_K = 8.0


class ModeloAError(RuntimeError):
    """`[SPRINT-50]` El modelo A no converge a un vector válido."""


def _canales(artefactos: Dict[str, Any]) -> Tuple[int, int]:
    variables: List[str] = artefactos["variables"]
    return variables.index("V07"), variables.index("V13")


# ── Puente β → (λ_H, λ_A) — espejo exacto de `preparar_dataset_ml.probabilidades_puente` ─────
def lambdas(artefactos: Dict[str, Any], split: str, pesos: Sequence[float]) -> Tuple[np.ndarray, np.ndarray]:
    variables: List[str] = artefactos["variables"]
    indice = {nombre: posicion for posicion, nombre in enumerate(variables)}
    vector = np.asarray(pesos, dtype=np.float64)
    factor_v07 = float(vector[indice["V07"]])
    factor_v13 = float(vector[indice["V13"]])

    local = np.clip(artefactos[f"local_{split}"][:, indice["V07"]] * factor_v07, 0.0, base.LIMITE_V07)
    visita = np.clip(artefactos[f"visita_{split}"][:, indice["V07"]] * factor_v07, 0.0, base.LIMITE_V07)
    local_def = np.clip(artefactos[f"local_{split}"][:, indice["V13"]] * factor_v13, 0.0, base.LIMITE_V13)
    visita_def = np.clip(artefactos[f"visita_{split}"][:, indice["V13"]] * factor_v13, 0.0, base.LIMITE_V13)

    media_v07 = float(artefactos["media_v07"])
    media_v13 = float(artefactos["media_v13"])
    mu_liga = float(artefactos["mu_liga"])

    ataque_local = (local + 1.0) / (media_v07 + 1.0)
    ataque_visita = (visita + 1.0) / (media_v07 + 1.0)
    defensa_local = (local_def + 1.0) / (media_v13 + 1.0)
    defensa_visita = (visita_def + 1.0) / (media_v13 + 1.0)

    lambda_h = np.clip(mu_liga * ataque_local / defensa_visita, base.LAMBDA_MIN, base.LAMBDA_MAX)
    lambda_a = np.clip(mu_liga * ataque_visita / defensa_local, base.LAMBDA_MIN, base.LAMBDA_MAX)
    return lambda_h, lambda_a


# ── ρ continuo [E-50.5] vectorizado ─────────────────────────────────────────────────────────
def _rho_continuo(lambda_h: np.ndarray, lambda_a: np.ndarray) -> np.ndarray:
    suma = lambda_h + lambda_a
    inferior = CORTE_TACTICO - VENTANA_RHO
    superior = CORTE_TACTICO + VENTANA_RHO
    t = np.clip((suma - inferior) / (superior - inferior), 0.0, 1.0)
    bajo = 1.0 / (1.0 + math.exp(SIGMOIDE_K * 0.5))
    alto = 1.0 / (1.0 + math.exp(-SIGMOIDE_K * 0.5))
    sigmoide = (1.0 / (1.0 + np.exp(-SIGMOIDE_K * (t - 0.5))) - bajo) / (alto - bajo)
    rho = RHO_TACTICA + (RHO_BASE - RHO_TACTICA) * np.clip(sigmoide, 0.0, 1.0)
    # Cotas analíticas de admisibilidad (paridad con [VAULT-CORE-004] §5.16.1).
    cota_inf = -np.minimum(1.0 / np.maximum(0.01, lambda_h), 1.0 / np.maximum(0.01, lambda_a))
    cota_sup = np.minimum(1.0, 1.0 / np.maximum(0.01, lambda_h * lambda_a))
    return np.clip(rho, cota_inf, cota_sup)


def nll_marcador(artefactos: Dict[str, Any], split: str, pesos: Sequence[float]) -> float:
    """−Σ ln P(x, y | β) sobre el marcador exacto del split (matriz Dixon-Coles 7×7)."""
    goles_local = artefactos.get(f"goles_local_{split}")
    goles_visita = artefactos.get(f"goles_visita_{split}")
    if goles_local is None or goles_visita is None:
        raise ModeloAError(
            f"Dataset sin marcador exacto (`goles_*_{split}`): reconstruir con preparar_dataset_ml."
        )
    lambda_h, lambda_a = lambdas(artefactos, split, pesos)

    k = np.arange(K_MAX + 1, dtype=np.float64)
    factorial = np.array([math.factorial(int(valor)) for valor in k])
    # pmf Poisson (n, 7)
    pois_h = np.exp(-lambda_h)[:, None] * (lambda_h[:, None] ** k) / factorial
    pois_a = np.exp(-lambda_a)[:, None] * (lambda_a[:, None] ** k) / factorial

    rho = _rho_continuo(lambda_h, lambda_a)                       # (n,)
    tau = np.ones((lambda_h.shape[0], K_MAX + 1, K_MAX + 1), dtype=np.float64)
    tau[:, 0, 0] = 1.0 - lambda_h * lambda_a * rho
    tau[:, 0, 1] = 1.0 + lambda_h * rho
    tau[:, 1, 0] = 1.0 + lambda_a * rho
    tau[:, 1, 1] = 1.0 - rho
    tau = np.maximum(tau, 0.0)                                     # Invariante I13

    densidad = pois_h[:, :, None] * pois_a[:, None, :] * tau       # (n, 7, 7)
    normalizador = densidad.sum(axis=(1, 2))
    indice_local = np.clip(np.asarray(goles_local, dtype=np.int64), 0, CENSURA_GOLES)
    indice_visita = np.clip(np.asarray(goles_visita, dtype=np.int64), 0, CENSURA_GOLES)
    observado = densidad[np.arange(densidad.shape[0]), indice_local, indice_visita]
    verosimilitud = np.clip(observado / normalizador, 1e-12, None)
    return float(-np.sum(np.log(verosimilitud)))


def _l1(pesos: Sequence[float]) -> float:
    vector = np.asarray(pesos, dtype=np.float64)
    return float(np.sum(np.sqrt(vector * vector + EPS_L1 * EPS_L1) - EPS_L1))


def objetivo(pesos: Sequence[float], artefactos: Dict[str, Any]) -> float:
    """[E-50.6 §T4] L(β) = NLL(marcador exacto) + λ_L1·‖β‖₁."""
    return nll_marcador(artefactos, "train", pesos) + LAMBDA_L1 * _l1(pesos)


def _rejilla(artefactos: Dict[str, Any], activas: Sequence[int], paso: float = PASO_REJILLA) -> np.ndarray:
    """Arranque determinista sobre el canal productivo (V07, V13); resto en 1.0."""
    mejor = np.ones(len(artefactos["variables"]))
    mejor_objetivo = objetivo(mejor, artefactos)
    valores = np.arange(0.5, 2.0 + 1e-9, paso)
    for primero in valores:
        for segundo in valores:
            candidato = np.ones(len(artefactos["variables"]))
            candidato[activas[0]] = primero
            candidato[activas[1]] = segundo
            valor = objetivo(candidato, artefactos)
            if valor < mejor_objetivo:
                mejor, mejor_objetivo = candidato, valor
    return mejor


def _umbralizar(pesos: np.ndarray) -> np.ndarray:
    """Umbralización Lasso: |β| < umbral ⇒ 0.0 exacto (declarado, no silencioso)."""
    limpio = pesos.copy()
    limpio[np.abs(limpio) < UMBRAL_APAGADO] = 0.0
    return limpio


def entrenar(artefactos: Dict[str, Any]) -> Dict[str, Any]:
    activas = _canales(artefactos)
    arranque = _rejilla(artefactos, activas)
    limites = [(PESO_MIN, PESO_MAX)] * len(artefactos["variables"])

    resultado = minimize(
        objetivo,
        x0=arranque,
        args=(artefactos,),
        method="L-BFGS-B",
        bounds=limites,
        options={"maxiter": 120, "ftol": 1e-10, "gtol": 1e-7},
    )
    pesos = _umbralizar(np.clip(np.asarray(resultado.x, dtype=np.float64), PESO_MIN, PESO_MAX))
    if not np.all(np.isfinite(pesos)):
        raise ModeloAError("El optimizador devolvió NaN/Inf.")
    if objetivo(pesos, artefactos) > objetivo(arranque, artefactos) + 1e-6:
        raise ModeloAError("L-BFGS-B no mejoró el arranque de rejilla.")

    nll_train = nll_marcador(artefactos, "train", pesos)
    nll_test = nll_marcador(artefactos, "test", pesos)
    apagadas = [artefactos["variables"][i] for i in range(len(pesos)) if pesos[i] == 0.0]
    saturadas = [artefactos["variables"][i] for i in range(len(pesos)) if pesos[i] >= PESO_MAX - 1e-9]

    return {
        "modelo": MODELO,
        "motor": MOTOR,
        "variables": artefactos["variables"],
        "pesos": [float(valor) for valor in pesos],
        "brier_train": float(base.brier_de_vector(artefactos, "train", pesos)),
        "brier_test": float(base.brier_de_vector(artefactos, "test", pesos)),
        "nll_train": float(nll_train),
        "nll_test": float(nll_test),
        "lambda_l1": LAMBDA_L1,
        "n_apagadas": len(apagadas),
        "apagadas": apagadas,
        "saturadas": saturadas,
        "diagnostico": {
            "canal": ["V07", "V13"],
            "dimensiones": int(len(pesos)),
            "umbral_apagado": UMBRAL_APAGADO,
            "arranque_rejilla": {"paso": PASO_REJILLA, "objetivo": float(objetivo(arranque, artefactos))},
            "iteraciones": int(resultado.nit),
            "evaluaciones": int(resultado.nfev),
            "mensaje": str(resultado.message),
        },
    }


def _reporte(acta: Dict[str, Any]) -> None:
    print("=" * 96)
    print("`[SPRINT-50]` MODELO A v2 — NLL(MARCADOR EXACTO) + L1 · [DIRGEN-STRICT]")
    print("=" * 96)
    print(f"Objetivo Train : {acta['diagnostico']['arranque_rejilla']['objetivo']:.4f} → "
          f"NLL={acta['nll_train']:.4f} + L1·λ={acta['lambda_l1']}")
    print(f"NLL Test       : {acta['nll_test']:.6f}")
    print(f"Brier Test     : {acta['brier_test']:.6f}")
    print(f"Variables apagadas por L1: {acta['n_apagadas']}/{len(acta['pesos'])}")
    print("=" * 96)


def main() -> int:
    analizador = argparse.ArgumentParser(prog="modelo_a_bayesiano")
    analizador.add_argument("--json", default=None, help="ruta del acta JSON")
    analizador.add_argument("--dataset", default=None, help="ruta del .npz (omite: canónico)")
    argumentos = analizador.parse_args()

    artefactos = base.cargar_artefactos(Path(argumentos.dataset) if argumentos.dataset else None)
    acta = entrenar(artefactos)
    _reporte(acta)
    if argumentos.json:
        ruta = Path(argumentos.json)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(json.dumps(acta, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
