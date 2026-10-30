# -*- coding: utf-8 -*-
"""
📊 Q-BE LABORATORIO — CONSOLIDACIÓN DEL RERUN DOBLE B + D

Lee los artefactos de `opcion_b/` y `opcion_d/` y escribe `REPORTE_FINAL.md` con tablas
numéricas y un veredicto gobernado por criterios explícitos. No reinterpreta: transcribe.

Uso:
    python -m scripts.laboratorio.consolidar_rerun --raiz data/output/rerun_20261030
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

RAIZ_PROYECTO = Path(__file__).resolve().parents[2]
TAU_COMPARABLES = (0.80, 0.90, 0.95, 0.99)


def _leer(ruta: Path) -> Dict[str, Any]:
    return json.loads(ruta.read_text(encoding="utf-8"))


def _por_tau(curva: Dict[str, Any], particion: str) -> Dict[float, Dict[str, Any]]:
    return {float(fila["tau"]): fila for fila in curva["curvas"][particion]}


def _fmt(valor: Any, decimales: int = 4) -> str:
    if valor is None:
        return "—"
    return f"{float(valor):.{decimales}f}"


def _ic(fila: Dict[str, Any]) -> str:
    ic = fila.get("ic95_mediana")
    if not ic:
        return "—"
    return f"[{ic[0]:.4f}, {ic[1]:.4f}]"


def _solapan(a: Optional[Sequence[float]], b: Optional[Sequence[float]]) -> Optional[bool]:
    if not a or not b:
        return None
    return not (a[1] < b[0] or b[1] < a[0])


def _tabla(cabeceras: Sequence[str], filas: Sequence[Sequence[Any]]) -> str:
    lineas = ["| " + " | ".join(cabeceras) + " |", "|" + "|".join(["---"] * len(cabeceras)) + "|"]
    for fila in filas:
        lineas.append("| " + " | ".join(str(celda) for celda in fila) + " |")
    return "\n".join(lineas)


def _cargar_corpus(raiz: Path, carpeta: str) -> Dict[str, Any]:
    base = raiz / carpeta
    datos: Dict[str, Any] = {"base": base}
    for nombre in (
        "curva_fragilidad",
        "deformacion_por_celda",
        "fixed_free",
        "modelo_nulo",
        "outliers",
        "brier_mercado",
        "kfold_alpha",
        "kfold_sigma",
    ):
        ruta = base / f"{nombre}.json"
        datos[nombre] = _leer(ruta) if ruta.is_file() else None
    return datos


def _veredicto(
    b: Dict[str, Any], d: Dict[str, Any]
) -> Dict[str, Any]:
    """Criterios NUMÉRICOS declarados antes de mirar el resultado."""
    curva_b = b["curva_fragilidad"]
    curva_d = d["curva_fragilidad"]
    opta_b = _por_tau(curva_b, "opta")
    total_b = _por_tau(curva_b, "total")
    non_b = _por_tau(curva_b, "non_opta")
    total_d = _por_tau(curva_d, "total")
    tau_principal = float(curva_b["tau_principal"])

    comparables = []
    for tau in TAU_COMPARABLES:
        if tau not in opta_b or tau not in total_d:
            continue
        sigma_b = float(opta_b[tau]["sigma_mediana"])
        sigma_d = float(total_d[tau]["sigma_mediana"])
        diferencia = abs(sigma_b - sigma_d) / max(sigma_b, sigma_d, 1e-12)
        comparables.append(
            {
                "tau": tau,
                "sigma_b_opta": sigma_b,
                "sigma_d": sigma_d,
                "diferencia_relativa": diferencia,
                "ic_solapan": _solapan(
                    opta_b[tau].get("ic95_mediana"), total_d[tau].get("ic95_mediana")
                ),
            }
        )
    estable = bool(comparables) and all(
        fila["diferencia_relativa"] <= 0.25 and fila["ic_solapan"] is not False
        for fila in comparables
    )

    share_b = (b["deformacion_por_celda"] or {}).get("celdas", {}).get("opta", {})
    share_d = (d["deformacion_por_celda"] or {}).get("celdas", {}).get("total", {})

    def _cara(celdas: Dict[str, Any], celda: str) -> bool:
        if not celdas:
            return False
        valores = sorted((v["share_norma2"] for v in celdas.values()), reverse=True)
        propio = celdas.get(celda, {}).get("share_norma2", 0.0)
        return propio >= 0.10 or (len(valores) >= 3 and propio >= valores[2])

    v12_cara = _cara(share_b, "V12") and _cara(share_d, "V12")
    v29_cara = _cara(share_b, "V29") and _cara(share_d, "V29")
    v19_v20 = (
        share_d.get("V19", {}).get("share_norma2", 0.0)
        + share_d.get("V20", {}).get("share_norma2", 0.0)
    )
    v19_v20_confirmadas = v19_v20 >= 0.10

    ratio_opta_non = None
    if tau_principal in opta_b and tau_principal in non_b:
        no = float(non_b[tau_principal]["sigma_mediana"])
        if no > 0:
            ratio_opta_non = float(opta_b[tau_principal]["sigma_mediana"]) / no
    opta_mucho_mayor = ratio_opta_non is not None and ratio_opta_non >= 1.5

    max_mediana_b = float(total_b[tau_principal]["sigma_max"]) / max(
        float(total_b[tau_principal]["sigma_mediana"]), 1e-12
    )
    max_mediana_d = float(total_d[tau_principal]["sigma_max"]) / max(
        float(total_d[tau_principal]["sigma_mediana"]), 1e-12
    )
    concentracion_b = (b.get("outliers") or {}).get("concentracion_top")
    concentracion_d = (d.get("outliers") or {}).get("concentracion_top")
    if concentracion_b is None or concentracion_d is None:
        # Guarda de compatibilidad: sin concentración explícita, se usa el proxy max/mediana.
        outliers_dominan = max_mediana_b >= 3.0 or max_mediana_d >= 3.0
    else:
        outliers_dominan = concentracion_b >= 0.5 or concentracion_d >= 0.5

    if opta_mucho_mayor or outliers_dominan:
        etiqueta = "FRAGILIDAD NO CONFIRMADA"
    elif estable and v12_cara and v29_cara:
        etiqueta = "FRAGILIDAD CONFIRMADA"
    else:
        etiqueta = "FRAGILIDAD PARCIAL"

    return {
        "comparables": comparables,
        "estable": estable,
        "v12_cara": bool(v12_cara),
        "v29_cara": bool(v29_cara),
        "v19_v20_share": v19_v20,
        "v19_v20_confirmadas": bool(v19_v20_confirmadas),
        "ratio_opta_non_opta": ratio_opta_non,
        "opta_mucho_mayor": bool(opta_mucho_mayor),
        "max_mediana_b": max_mediana_b,
        "max_mediana_d": max_mediana_d,
        "concentracion_top_b": concentracion_b,
        "concentracion_top_d": concentracion_d,
        "outliers_dominan": bool(outliers_dominan),
        "etiqueta": etiqueta,
    }


def construir(raiz: Path) -> str:
    b = _cargar_corpus(raiz, "opcion_b")
    d = _cargar_corpus(raiz, "opcion_d")
    for nombre in ("curva_fragilidad", "deformacion_por_celda", "fixed_free", "modelo_nulo", "outliers"):
        if not b.get(nombre) or not d.get(nombre):
            raise FileNotFoundError(f"Falta {nombre}.json en opcion_b/ u opcion_d/")

    curva_b = b["curva_fragilidad"]
    curva_d = d["curva_fragilidad"]
    opta_b = _por_tau(curva_b, "opta")
    total_b = _por_tau(curva_b, "total")
    non_b = _por_tau(curva_b, "non_opta")
    total_d = _por_tau(curva_d, "total")
    tau_principal = float(curva_b["tau_principal"])
    veredicto = _veredicto(b, d)

    def _share_grupo(celdas: Dict[str, Any], grupo: str) -> float:
        if grupo == "V26_V29_V30":
            return sum(
                float(celdas.get(celda, {}).get("share_norma2", 0.0))
                for celda in ("V26", "V29", "V30")
            )
        return float(celdas.get(grupo, {}).get("share_norma2", 0.0))

    lineas: List[str] = [
        "# REPORTE FINAL — RERUN DOBLE B + D",
        "",
        "**Expediente:** SPRINT-FASE5-E-MUESTREO-MULTIFUENTE · Fase Rerun Doble  ",
        "**Régimen:** [DIRGEN-STRICT] en datos/contratos · [DBBD-FUNGIBLE] en CLI/reportes  ",
        "**Naturaleza:** análisis completo. Los números se transcriben; la interpretación es del Director.",
        "",
        "## 0 · Ficha técnica",
        "",
        _tabla(
            ["Corpus", "Snapshot", "SHA-256", "n", "n_esperado", "τ principal"],
            [
                [
                    "B (histórico)",
                    curva_b["snapshot"]["ruta"],
                    f"`{curva_b['snapshot']['sha256']}`",
                    curva_b["n"],
                    curva_b["n_esperado"],
                    tau_principal,
                ],
                [
                    "D (J14)",
                    curva_d["snapshot"]["ruta"],
                    f"`{curva_d['snapshot']['sha256']}`",
                    curva_d["n"],
                    curva_d["n_esperado"],
                    tau_principal,
                ],
            ],
        ),
        "",
        f"- τ: `{curva_b['taus']}`",
        f"- Bootstrap: {curva_b.get('metodo_bootstrap')}",
        f"- Estratificación B: `{curva_b.get('estratificacion')}`; D: `{curva_d.get('estratificacion')}`",
        "",
        "## 1 · Comparativa B (Opta) vs D (J14)",
        "",
        "Criterio de coincidencia: diferencia relativa ≤ 25 % y IC 95 % solapados para τ ≥ 0.80.",
        "",
        _tabla(
            ["τ", "σ_B Opta", "IC95 B Opta", "σ_D", "IC95 D", "dif. rel.", "IC solapan"],
            [
                [
                    f"{fila['tau']:.2f}",
                    _fmt(fila["sigma_b_opta"]),
                    _ic(opta_b[fila["tau"]]),
                    _fmt(fila["sigma_d"]),
                    _ic(total_d[fila["tau"]]),
                    f"{fila['diferencia_relativa'] * 100:.2f}%",
                    "sí" if fila["ic_solapan"] else "no",
                ]
                for fila in veredicto["comparables"]
            ],
        ),
        "",
        f"**¿Coincide σ_Opta del histórico con σ de J14?** {'SÍ' if veredicto['estable'] else 'NO'} "
        f"(criterio: dif. rel. ≤ 25 % e IC solapados en τ ≥ 0.80).",
        "",
        "**Nota de censura de caja (numérica):** "
        f"B total τ=0.99 σ_p90/σ_máx = "
        f"{float(total_b[tau_principal]['sigma_p90']) / max(float(total_b[tau_principal]['sigma_max']), 1e-12):.6f}; "
        f"D total τ=0.99 σ_p90/σ_máx = "
        f"{float(total_d[tau_principal]['sigma_p90']) / max(float(total_d[tau_principal]['sigma_max']), 1e-12):.6f}. "
        "Un cociente ≈ 1 indica que al menos el 10 % de los partidos agotan la cota física de sus celdas "
        "y la cola de la curva está censurada por la caja; no es una cola libre.",
        "",
        "## 2 · Estratificación por procedencia xG (B)",
        "",
        _tabla(
            ["τ", "n Opta", "σ Opta", "IC95 Opta", "n non-Opta", "σ non-Opta", "n total", "σ total", "ratio Opta/non-Opta"],
            [
                [
                    f"{tau:.2f}",
                    opta_b[tau]["n"],
                    _fmt(opta_b[tau]["sigma_mediana"]),
                    _ic(opta_b[tau]),
                    non_b[tau]["n"],
                    _fmt(non_b[tau]["sigma_mediana"]),
                    total_b[tau]["n"],
                    _fmt(total_b[tau]["sigma_mediana"]),
                    _fmt(
                        float(opta_b[tau]["sigma_mediana"])
                        / float(non_b[tau]["sigma_mediana"])
                        if non_b[tau]["sigma_mediana"]
                        else None,
                        3,
                    ),
                ]
                for tau in sorted(opta_b)
            ],
        ),
        "",
        "## 3 · Fixed/Free — ablaciones y descomposición",
        "",
        "σ mediana por ablación en τ principal. `todos` es la geometría completa; las demás fijan el resto de α en 0.",
        "",
        _tabla(
            ["Ablación", "n_B", "sat_B", "σ_B", "n_D", "sat_D", "σ_D"],
            [
                [
                    nombre,
                    next(
                        (fila["n"] for fila in b["fixed_free"]["ablaciones"][nombre]
                         if abs(float(fila["tau"]) - tau_principal) < 1e-12),
                        "—",
                    ),
                    next(
                        (fila.get("n_saturados", 0) for fila in b["fixed_free"]["ablaciones"][nombre]
                         if abs(float(fila["tau"]) - tau_principal) < 1e-12),
                        "—",
                    ),
                    _fmt(
                        next(
                            (
                                fila["sigma_mediana"]
                                for fila in b["fixed_free"]["ablaciones"][nombre]
                                if abs(float(fila["tau"]) - tau_principal) < 1e-12
                            ),
                            None,
                        )
                    ),
                    next(
                        (fila["n"] for fila in d["fixed_free"]["ablaciones"][nombre]
                         if abs(float(fila["tau"]) - tau_principal) < 1e-12),
                        "—",
                    ),
                    next(
                        (fila.get("n_saturados", 0) for fila in d["fixed_free"]["ablaciones"][nombre]
                         if abs(float(fila["tau"]) - tau_principal) < 1e-12),
                        "—",
                    ),
                    _fmt(
                        next(
                            (
                                fila["sigma_mediana"]
                                for fila in d["fixed_free"]["ablaciones"][nombre]
                                if abs(float(fila["tau"]) - tau_principal) < 1e-12
                            ),
                            None,
                        )
                    ),
                ]
                for nombre in ("solo_V06", "solo_V12", "solo_V26_V29_V30", "todos")
            ],
        ),
        "",
        _tabla(
            ["Share de ‖Δ‖²", "B total", "B Opta", "B non-Opta", "D total"],
            [
                [
                    grupo,
                    f"{(b['deformacion_por_celda'].get('descomposicion_total', {}).get(grupo, 0) * 100):.2f}%",
                    f"{_share_grupo(b['deformacion_por_celda']['celdas']['opta'], grupo) * 100:.2f}%",
                    f"{_share_grupo(b['deformacion_por_celda']['celdas']['non_opta'], grupo) * 100:.2f}%",
                    f"{(d['deformacion_por_celda'].get('descomposicion_total', {}).get(grupo, 0) * 100):.2f}%",
                ]
                for grupo in ("V06", "V12", "V26_V29_V30", "resto")
            ],
        ),
        "",
        "## 4 · Modelo nulo — σ_QBE vs σ_null",
        "",
        _tabla(
            ["τ", "σ_QBE B", "σ_null B", "ratio B", "σ_QBE D", "σ_null D", "ratio D"],
            [
                [
                    f"{tau:.2f}",
                    _fmt(
                        next(
                            (f["sigma_qbe_mediana"] for f in b["modelo_nulo"]["por_tau"] if abs(f["tau"] - tau) < 1e-12),
                            None,
                        )
                    ),
                    _fmt(
                        next(
                            (f["sigma_null_mediana"] for f in b["modelo_nulo"]["por_tau"] if abs(f["tau"] - tau) < 1e-12),
                            None,
                        )
                    ),
                    _fmt(
                        next(
                            (f["ratio"] for f in b["modelo_nulo"]["por_tau"] if abs(f["tau"] - tau) < 1e-12),
                            None,
                        ),
                        3,
                    ),
                    _fmt(
                        next(
                            (f["sigma_qbe_mediana"] for f in d["modelo_nulo"]["por_tau"] if abs(f["tau"] - tau) < 1e-12),
                            None,
                        )
                    ),
                    _fmt(
                        next(
                            (f["sigma_null_mediana"] for f in d["modelo_nulo"]["por_tau"] if abs(f["tau"] - tau) < 1e-12),
                            None,
                        )
                    ),
                    _fmt(
                        next(
                            (f["ratio"] for f in d["modelo_nulo"]["por_tau"] if abs(f["tau"] - tau) < 1e-12),
                            None,
                        ),
                        3,
                    ),
                ]
                for tau in sorted({f["tau"] for f in b["modelo_nulo"]["por_tau"]})
            ],
        ),
        "",
        "Lectura aritmética: ratio < 1 ⇒ la P′ de Q-BE requiere menos deformación que el prior uniforme para alcanzar τ.",
        "",
        "## 5 · Outliers",
        "",
        f"### B — top 30 (τ = {b['outliers']['tau']:.2f})",
        "",
        _tabla(
            ["#", "Partido", "Temporada", "J", "Resultado", "‖Δ‖σ", "Celdas dominantes"],
            [
                [
                    i + 1,
                    fila["id_partido"],
                    fila["temporada"],
                    fila["jornada"],
                    fila["resultado"],
                    _fmt(fila["norma_sigma"], 2),
                    " · ".join(f"{c['celda']} {c['delta_sigma']:+.2f}" for c in fila["celdas_dominantes"]),
                ]
                for i, fila in enumerate(b["outliers"]["top"])
            ],
        ),
        "",
        f"### D — top 30 (τ = {d['outliers']['tau']:.2f})",
        "",
        _tabla(
            ["#", "Partido", "Temporada", "J", "Resultado", "‖Δ‖σ", "Celdas dominantes"],
            [
                [
                    i + 1,
                    fila["id_partido"],
                    fila["temporada"],
                    fila["jornada"],
                    fila["resultado"],
                    _fmt(fila["norma_sigma"], 2),
                    " · ".join(f"{c['celda']} {c['delta_sigma']:+.2f}" for c in fila["celdas_dominantes"]),
                ]
                for i, fila in enumerate(d["outliers"]["top"])
            ],
        ),
        "",
        "## 6 · α_Por y estabilidad k-fold (D)",
        "",
        _tabla(
            ["Fold", "Jornadas test", "n train", "n test", "α_Por", "α[Vol Rem Def Por Spc Ctx]"],
            [
                [
                    fila["fold"],
                    ",".join(f"J{j}" for j in fila["jornadas_test"]),
                    fila["n_train"],
                    fila["n_test"],
                    _fmt(fila["alfa_Por"], 4),
                    " ".join(f"{v:.3f}" for v in fila["alfa"]),
                ]
                for fila in d["kfold_alpha"]["por_fold"]
            ],
        ),
        "",
        _tabla(
            ["α", "mean", "std", "CV"],
            [
                [
                    dimension,
                    _fmt(d["kfold_alpha"]["resumen"][dimension]["mean"]),
                    _fmt(d["kfold_alpha"]["resumen"][dimension]["std"]),
                    _fmt(
                        d["kfold_alpha"]["resumen"][dimension]["std"]
                        / d["kfold_alpha"]["resumen"][dimension]["mean"]
                        if d["kfold_alpha"]["resumen"][dimension]["mean"]
                        else None,
                        4,
                    ),
                ]
                for dimension in list(d["kfold_alpha"]["dimensiones"]) + ["alfa_Por"]
            ],
        ),
        "",
        "σ held-out por celda (media ± std entre 5 folds):",
        "",
        _tabla(
            ["Celda", "mean", "std"],
            [
                [celda, _fmt(valores["mean"]), _fmt(valores["std"])]
                for celda, valores in d["kfold_sigma"]["resumen"].items()
            ],
        ),
        "",
        "**α_Por — estabilidad:** "
        f"mean ± std = {_fmt(d['kfold_alpha']['resumen']['alfa_Por']['mean'])} ± "
        f"{_fmt(d['kfold_alpha']['resumen']['alfa_Por']['std'])} · "
        f"CV = {_fmt(d['kfold_alpha']['resumen']['alfa_Por']['cv'], 4)}. "
        f"¿1.008 ∈ [mean−std, mean+std]? "
        f"{'sí' if abs(1.008 - d['kfold_alpha']['resumen']['alfa_Por']['mean']) <= d['kfold_alpha']['resumen']['alfa_Por']['std'] else 'no'}. "
        f"Criterio de estabilidad declarado: CV ≤ 0.10 y rango (max−min) ≤ 0.30. "
        f"Resultado: "
        f"{'ESTABLE' if (d['kfold_alpha']['resumen']['alfa_Por']['cv'] is not None and d['kfold_alpha']['resumen']['alfa_Por']['cv'] <= 0.10 and (max(f['alfa_Por'] for f in d['kfold_alpha']['por_fold']) - min(f['alfa_Por'] for f in d['kfold_alpha']['por_fold'])) <= 0.30) else 'NO ESTABLE'}.",
        "",
        "## 7 · Brier de mercado (B)",
        "",
        _tabla(
            ["Concepto", "Valor"],
            [
                ["n total", b["brier_mercado"]["n_total"]],
                ["Brier modelo (4,329)", _fmt(b["brier_mercado"]["brier_modelo_total"], 6)],
                ["n con cuota", b["brier_mercado"]["n_con_cuota"]],
                ["Brier mercado", _fmt(b["brier_mercado"]["brier_mercado"], 6)],
                ["n sin cuota", b["brier_mercado"]["n_sin_cuota"]],
            ],
        ),
        "",
        "## 8 · Veredicto del Constructor",
        "",
        "Criterios numéricos declarados antes de leer el resultado:",
        "",
        _tabla(
            ["Criterio", "Umbral", "Resultado", "Cumple"],
            [
                ["Estabilidad B-Opta vs D en τ ≥ 0.80", "dif. rel. ≤ 25 % e IC solapados", f"{'sí' if veredicto['estable'] else 'no'}", "sí" if veredicto["estable"] else "no"],
                ["V12 cara de mover en ambos corpus", "share ≥ 10 % o top-3", f"{veredicto['v12_cara']}", "sí" if veredicto["v12_cara"] else "no"],
                ["V29 cara de mover en ambos corpus", "share ≥ 10 % o top-3", f"{veredicto['v29_cara']}", "sí" if veredicto["v29_cara"] else "no"],
                ["V19+V20 (sólo D)", "share conjunto ≥ 10 %", f"{veredicto['v19_v20_share'] * 100:.2f}%", "sí" if veredicto["v19_v20_confirmadas"] else "no"],
                ["σ_Opta ≫ σ_non-Opta (τ principal)", "ratio ≥ 1.5", _fmt(veredicto["ratio_opta_non_opta"], 3), "sí" if veredicto["opta_mucho_mayor"] else "no"],
                ["Outliers dominan", "top-30 ≥ 50 % de ‖Δ‖²", f"B {_fmt(veredicto['concentracion_top_b'], 3)} · D {_fmt(veredicto['concentracion_top_d'], 3)}", "sí" if veredicto["outliers_dominan"] else "no"],
            ],
        ),
        "",
        f"### **{veredicto['etiqueta']}**",
        "",
        "---",
        "",
        "*Fin del reporte. Sin promedio entre B y D; la comparación es cualitativa por τ.*",
    ]
    return "\n".join(lineas)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Consolida el Rerun Doble B + D.")
    parser.add_argument(
        "--raiz",
        type=Path,
        default=RAIZ_PROYECTO / "data" / "output" / "rerun_20261030",
        help="Directorio con opcion_b/ y opcion_d/.",
    )
    argumentos = parser.parse_args(argv)
    raiz = Path(argumentos.raiz)
    texto = construir(raiz)
    destino = raiz / "REPORTE_FINAL.md"
    destino.write_text(texto + "\n", encoding="utf-8")
    print(f"📄 Reporte consolidado: {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
