# -*- coding: utf-8 -*-
"""`[SPRINT-49]` Tarea 5 — Ensamble y consenso (La Sabiduría de los Modelos).

Régimen ``[DIRGEN-STRICT]``.

Carga los tres vectores de 23 multiplicadores (A: optimización bayesiana, B: regresión
logística, C: gradient boosting), calcula la **mediana por variable** —que anula los valores
atípicos— y valida el consenso en el ``Test`` con la misma vara para todos: el puente
legislado `[LN-QBE-147]` (``qbe_core``), Brier multiclase canónico y Alpha de calibración
`[LN-QBE-100]`.

Líneas base declaradas (D5)
---------------------------
* **Puente 1.0** — mismo motor, multiplicadores neutros: línea base interna del laboratorio.
* **P' almacenada** — ``historical_sovereign_distributions``: línea base oficial del ecosistema.

Fail-Loud
---------
Vector con NaN/Inf, fuera de ``[0.5, 2.0]`` o Brier normalizado > 0.25 ⇒ ``FALLA DE
CALIBRACIÓN`` y código de salida 2. Nada se maquilla.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

DIR_SCRIPTS = Path(__file__).resolve().parent
if str(DIR_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(DIR_SCRIPTS))

import preparar_dataset_ml as base  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, OSError, ValueError):  # pragma: no cover
        pass

PESO_MIN, PESO_MAX = 0.5, 2.0
UMBRAL_FALLA = 0.25  # sobre Brier normalizado (/3)
ETIQUETA_MERCADO = "[REFERENCIA-DEUDA]"


class ConsensoError(RuntimeError):
    """`[SPRINT-49]` El ensamble no puede emitirse."""


def cargar_pesos(directorio: Path) -> Dict[str, Dict[str, Any]]:
    actas: Dict[str, Dict[str, Any]] = {}
    for modelo, nombre in (("A", "pesos_modelo_a.json"), ("B", "pesos_modelo_b.json"), ("C", "pesos_modelo_c.json")):
        ruta = directorio / nombre
        if not ruta.is_file():
            raise ConsensoError(f"Falta el acta del modelo {modelo}: {ruta}")
        actas[modelo] = json.loads(ruta.read_text(encoding="utf-8"))
    return actas


def _validar(nombre: str, pesos: Sequence[float], variables: Sequence[str]) -> np.ndarray:
    vector = np.asarray(pesos, dtype=np.float64)
    if vector.shape != (len(variables),):
        raise ConsensoError(f"{nombre}: vector de forma {vector.shape}, se esperaba ({len(variables)},).")
    if not np.all(np.isfinite(vector)):
        raise ConsensoError(f"{nombre}: vector con NaN/Inf.")
    if vector.min() < PESO_MIN - 1e-9 or vector.max() > PESO_MAX + 1e-9:
        raise ConsensoError(f"{nombre}: vector fuera de [{PESO_MIN}, {PESO_MAX}].")
    return np.clip(vector, PESO_MIN, PESO_MAX)


def _brier_matriz(probabilidades: np.ndarray, y: np.ndarray) -> tuple[float, int]:
    mascara = y >= 0
    total = 0.0
    for p_local, p_empate, p_visitante, indice in zip(
        probabilidades[mascara, 0], probabilidades[mascara, 1], probabilidades[mascara, 2], np.flatnonzero(mascara)
    ):
        fila = int(y[indice])
        goles_local, goles_visita = (1, 0) if fila == 0 else ((0, 0) if fila == 1 else (0, 1))
        total += base.brier_canonico(p_local, p_empate, p_visitante, goles_local, goles_visita)
    return total / int(mascara.sum()), int(mascara.sum())


def _alpha_pct(brier: float, brier_mercado: Optional[float]) -> Optional[float]:
    """`[LN-QBE-100]` Alpha = (1 − BS_QBE / BS_MKT) × 100."""
    if not brier_mercado or brier_mercado <= 0.0:
        return None
    return round((1.0 - brier / brier_mercado) * 100.0, 2)


def _format(value: Any, ancho: int = 10, decimales: int = 4) -> str:
    if value is None:
        return "—".rjust(ancho)
    if isinstance(value, str):
        return value.rjust(ancho)
    return f"{value:{ancho}.{decimales}f}"


def ejecutar(artefactos: Dict[str, Any], actas: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    variables: List[str] = artefactos["variables"]
    vectores = {
        modelo: _validar(modelo, acta["pesos"], variables) for modelo, acta in actas.items()
    }
    for modelo, acta in actas.items():
        if list(acta["variables"]) != list(variables):
            raise ConsensoError(f"El acta del modelo {modelo} no comparte el orden de variables.")

    matriz = np.vstack([vectores["A"], vectores["B"], vectores["C"]])
    consenso = np.median(matriz, axis=0)
    consenso = _validar("Ensemble", consenso, variables)

    y_test = np.asarray(artefactos["y_test"])
    filas: List[Dict[str, Any]] = []

    for nombre, vector in (
        ("Modelo A", vectores["A"]),
        ("Modelo B", vectores["B"]),
        ("Modelo C", vectores["C"]),
        ("Ensemble", consenso),
        ("Puente 1.0", np.ones(len(variables))),
    ):
        brier, n = base.evaluar_split(artefactos, "test", vector)[:2]
        filas.append({"nombre": nombre, "brier": float(brier), "n": int(n)})

    brier_almacenada, n_almacenada = _brier_matriz(
        np.asarray(artefactos["p_base_test"], dtype=np.float64), y_test
    )
    filas.append({"nombre": "P' almacenada", "brier": float(brier_almacenada), "n": int(n_almacenada)})

    brier_mercado, n_mercado = base.brier_mercado(artefactos, "test")
    for fila in filas:
        fila["alpha"] = _alpha_pct(fila["brier"], brier_mercado)
        fila["brier_norm"] = float(fila["brier"] / 3.0)

    return {
        "variables": variables,
        "vectores": {modelo: [float(v) for v in vector] for modelo, vector in vectores.items()},
        "consenso": [float(v) for v in consenso],
        "filas": filas,
        "brier_mercado": brier_mercado,
        "n_mercado": n_mercado,
        "mediana_matriz": matriz.tolist(),
    }


def _tabla_pesos(resultado: Dict[str, Any]) -> None:
    variables = resultado["variables"]
    vectores = resultado["vectores"]
    consenso = resultado["consenso"]
    print("-" * 96)
    print(f"{'Variable':<10}{'Modelo A':>12}{'Modelo B':>12}{'Modelo C':>12}{'MEDIANA':>12}{'Rango':>12}")
    print("-" * 96)
    for indice, variable in enumerate(variables):
        valores = [vectores["A"][indice], vectores["B"][indice], vectores["C"][indice]]
        rango = max(valores) - min(valores)
        print(
            f"{variable:<10}{valores[0]:>12.4f}{valores[1]:>12.4f}{valores[2]:>12.4f}"
            f"{consenso[indice]:>12.4f}{rango:>12.4f}"
        )
    print("-" * 96)
    print("Vecino del consenso: V07 y V13 son las ÚNICAS variables con canal hacia λ [LN-QBE-147].")
    print("El resto del vector es inerte en esta fase (efecto 1.0 en la evaluación, D2).")


def _tabla_brier(resultado: Dict[str, Any]) -> None:
    referencia = next(fila for fila in resultado["filas"] if fila["nombre"] == "Puente 1.0")["brier"]
    print("-" * 96)
    print(f"{'Modelo':<16}{'Brier Test':>12}{'Normalizado':>13}{'Δ vs 1.0':>12}{'Alpha %':>10}{'N':>7}")
    print("-" * 96)
    for fila in resultado["filas"]:
        delta = fila["brier"] - referencia
        print(
            f"{fila['nombre']:<16}{fila['brier']:>12.6f}{fila['brier_norm']:>13.4f}"
            f"{delta:>+12.6f}{_format(fila['alpha'], 10, 2)}{fila['n']:>7d}"
        )
    print("-" * 96)
    mercado = resultado["brier_mercado"]
    if mercado is None:
        print(f"Alpha vs FootyStats {ETIQUETA_MERCADO}: SIN EVIDENCIA (sin cuotas utilizables).")
    else:
        print(
            f"Brier mercado FootyStats {ETIQUETA_MERCADO}: {mercado:.6f} "
            f"(n={resultado['n_mercado']}); Alpha = (1 − BS_QBE/BS_MKT)·100."
        )


def _alertas(resultado: Dict[str, Any]) -> List[str]:
    alertas: List[str] = []
    for fila in resultado["filas"]:
        if fila["brier_norm"] > UMBRAL_FALLA:
            alertas.append(
                f"FALLA DE CALIBRACIÓN: {fila['nombre']} con Brier normalizado {fila['brier_norm']:.4f} > {UMBRAL_FALLA}."
            )
    return alertas


def main() -> int:
    parser = argparse.ArgumentParser(description="Ensamble y consenso (SPRINT-49)")
    parser.add_argument("--directorio", default=str(base.DIR_SALIDA))
    argumentos = parser.parse_args()

    directorio = Path(argumentos.directorio)
    artefactos = base.cargar_artefactos()
    actas = cargar_pesos(directorio)
    resultado = ejecutar(artefactos, actas)

    print("=" * 96)
    print("`[SPRINT-49]` TAREA 5 — ENSAMBLE Y CONSENSO · REGIMEN [DIRGEN-STRICT]")
    print("=" * 96)
    print(f"Train: {artefactos['meta']['n_train']} partidos  ·  Test: {artefactos['meta']['n_test']}"
          f" (con marcador {artefactos['meta']['n_test_con_marcador']})")
    print(f"Variables: {len(resultado['variables'])}  ·  banda [{PESO_MIN}, {PESO_MAX}]"
          f"  ·  mediana por variable (anula atípicos)")
    _tabla_pesos(resultado)
    print()
    print("VALIDACIÓN EN TEST — misma vara (puente `[LN-QBE-147]`, Brier `qbe_core`)")
    _tabla_brier(resultado)

    alertas = _alertas(resultado)
    print()
    if alertas:
        for alerta in alertas:
            print(f"  ⚠ {alerta}")
    else:
        print(f"  ✔ Invariantes: Brier normalizado ≤ {UMBRAL_FALLA} en todos los vectores; sin NaN/Inf.")

    print()
    print("VENTANA PRE-KICKOFF (SPRINT-49 v2): las 23 características son medias expansivas de")
    print("partidos previos del club (misma temporada); el vector del partido objetivo no contiene")
    antifuga = artefactos["meta"]["antifuga"]
    print(f"ningún dato del propio partido (anti-fuga: {antifuga['violaciones_fecha']} violaciones de fecha,")
    print(f"{antifuga['violaciones_identidad']} de identidad sobre {antifuga['filas_verificadas']} lados).")
    print("El puente `[LN-QBE-147]` consume V07/V13 ACUMULADOS: el Brier de Test es fuera de muestra.")

    oficial = next(fila for fila in resultado["filas"] if fila["nombre"] == "P' almacenada")["brier"]
    ensemble = next(fila for fila in resultado["filas"] if fila["nombre"] == "Ensemble")["brier"]
    mejor_ml = min(
        (fila for fila in resultado["filas"] if fila["nombre"].startswith("Modelo")),
        key=lambda fila: fila["brier"],
    )
    print()
    print(f"VEREDICTO ML vs P' OFICIAL: ensamble {ensemble:.6f} · mejor ML ({mejor_ml['nombre']}) "
          f"{mejor_ml['brier']:.6f} · oficial {oficial:.6f}")
    print(f"  Δ(ensamble − oficial) = {ensemble - oficial:+.6f}  ⇒  "
          f"{'EL ML VENCE' if ensemble < oficial else 'EL ML NO VENCE'} a la P' oficial.")
    print("=" * 96)

    destino = directorio / "consenso_ensamble.json"
    destino.write_text(json.dumps({**resultado, "alertas": alertas}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Acta: {destino}")
    return 2 if alertas else 0


if __name__ == "__main__":
    raise SystemExit(main())
