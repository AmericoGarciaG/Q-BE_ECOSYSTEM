# -*- coding: utf-8 -*-
"""
Q-BE CD WEB — MINERÍA DE INFORMACIÓN MUTUA DE SHANNON Y ÁRBOL ESPARSO DE VETO
[ARCH-1.4.70] / [LN-QBE-129] · Régimen: [DBBD-FUNGIBLE]

Misión
------
Ordenar las 64 celdas fácticas PRE-KICKOFF de la matriz canónica `[ARCH-1.4.67]` por su contenido
informativo REAL sobre la etiqueta consumada — información mutua de Shannon en BITS — e inducir,
con un árbol CART **esparso** (profundidad 3, hoja mínima gobernada), reglas de VETO legibles para
la ruptura residual de la tríada (`clasificacion_triada == "P_LOW"`).

Frontera anti-fuga (invariante del instrumento)
-----------------------------------------------
Las candidatas se derivan del ENCABEZADO del CSV con patrón `vNN_{local|visita}` (Zona B). Las
Zonas C (P′ servida, `p_low_ruptura_pct`) y D (marcador, Brier, clasificación) quedan PROHIBIDAS
como predictoras: `p_low_ruptura_pct` es función determinista de la etiqueta y usarla sería fuga
circular. La etiqueta es el ÚNICO contacto legítimo con el desenlace.

Cero dependencias nuevas
------------------------
Entropía, información mutua, discretización por rangos y árbol CART se implementan con biblioteca
estándar (`csv`, `math`, `json`). No se siembra `numpy`/`pandas`/`scikit-learn`: un sandbox de
investigación no justifica una dependencia de producción.

Uso
---
    python -m scripts.investigacion.mineria_factores_shannon
    python -m scripts.investigacion.mineria_factores_shannon --json
    python -m scripts.investigacion.mineria_factores_shannon --top 20 --min-hoja 6
    python -m scripts.investigacion.mineria_factores_shannon --ruta-dataset data/output/otra.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ─── Constantes legisladas ───────────────────────────────────────────────────────────────────
SONDA_MINERIA = "ARCH-1.4.70 · MINERIA-SHANNON-ARBOL-ESPARCISO"
RUTA_DATASET_DEFAULT = os.path.join("data", "output", "research_feature_matrix.csv")
RUTA_REPORTE_DEFAULT = os.path.join("data", "output", "mineria_shannon_reporte.json")
COLUMNA_ETIQUETA = "clasificacion_triada"
CLASE_RUPTURA = "P_LOW"
BINS_DISCRETIZACION = 4
PROFUNDIDAD_MAXIMA_DEFAULT = 3
MIN_HOJA_DEFAULT = 5
# Decreto D4 ratificado por el Director: pureza >= 60%, soporte >= 5, lift >= 2.0.
PUREZA_MINIMA_PCT = 60.0
PUREZA_PISO_JUEZ_PCT = 50.0
SOPORTE_MINIMO = 5
LIFT_MINIMO = 2.0
# Barrido gobernado: si la configuración canónica no alcanza el umbral de veto (Decreto D4), se
# explora la hoja mínima y —sólo entonces— la profundidad, publicando la configuración elegida.
BARRIDO_MIN_HOJA: Tuple[int, ...] = (5, 6, 7, 8, 4)
BARRIDO_PROFUNDIDAD: Tuple[int, ...] = (3, 4, 5)
# Columnas de identidad/contexto que jamás son predictoras (Zona A).
COLUMNAS_ZONA_A = ("match_id", "jornada", "competition_id", "kickoff_utc", "local", "visitante")
ETIQUETA_SIN_DATO = "SIN_DATO"
ROTULO_HIPOTESIS = "SUGERIDA · NO EJECUTA TRIAJE"


# ═════════════════════════════════════════════════════════════════════════════════════════════
# ZONA 1 — LECTURA DEL DATASET Y FRONTERA ANTI-FUGA
# ═════════════════════════════════════════════════════════════════════════════════════════════
def columnas_candidatas(columnas: Sequence[str]) -> List[str]:
    """Candidatas = Zona B (`vNN_local` / `vNN_visita`); Zonas A, C y D quedan fuera por ley."""
    candidatas = []
    for columna in columnas:
        if columna in COLUMNAS_ZONA_A or columna == COLUMNA_ETIQUETA:
            continue
        if columna.endswith("_local"):
            identificador = columna[: -len("_local")]
        elif columna.endswith("_visita"):
            identificador = columna[: -len("_visita")]
        else:
            continue
        if len(identificador) == 3 and identificador[0] == "v" and identificador[1:].isdigit():
            candidatas.append(columna)
    return candidatas


def leer_dataset(ruta: str) -> Tuple[List[str], List[Dict[str, str]]]:
    """Lee el CSV canónico tal cual (cero transformación de valores: la tolerancia es local)."""
    if not os.path.exists(ruta):
        raise SystemExit(f"[ALTO AL FUEGO] Dataset ausente: {ruta}")
    with open(ruta, encoding="utf-8", newline="") as archivo:
        lector = csv.DictReader(archivo)
        columnas = list(lector.fieldnames or [])
        filas = [dict(fila) for fila in lector]
    return columnas, filas


def a_flotante(valor: Any) -> Optional[float]:
    """`None` para vacío/`None`/no numérico: el cero NUNCA se fabrica a partir de una ausencia."""
    if valor is None:
        return None
    texto = str(valor).strip()
    if not texto:
        return None
    try:
        return float(texto)
    except ValueError:
        return None

# ═════════════════════════════════════════════════════════════════════════════════════════════
# ZONA 2 — DISCRETIZACIÓN POR RANGOS, ENTROPÍA E INFORMACIÓN MUTUA
# ═════════════════════════════════════════════════════════════════════════════════════════════
def cortes_por_rangos(valores: Sequence[float], bins: int = BINS_DISCRETIZACION) -> List[float]:
    """Cortes cuantílicos ÚNICOS (jamás fabrica un corte que no exista en los datos)."""
    ordenados = sorted(valores)
    if len(ordenados) < 2:
        return []
    cortes: List[float] = []
    for indice in range(1, bins):
        posicion = int(round(indice * len(ordenados) / bins)) - 1
        posicion = min(max(posicion, 0), len(ordenados) - 2)
        corte = (ordenados[posicion] + ordenados[posicion + 1]) / 2.0
        if corte not in cortes:
            cortes.append(corte)
    return cortes


def discretizar(valor: Optional[float], cortes: Sequence[float]) -> str:
    """Bina un valor observado; `SIN_DATO` es una categoría propia, jamás un cero."""
    if valor is None:
        return ETIQUETA_SIN_DATO
    indice = 0
    for corte in cortes:
        if valor > corte:
            indice += 1
    return f"B{indice}"


def entropia_bits(conteos: Dict[Any, int], total: int) -> float:
    """`H(X) = -Σ p·log2(p)` en bits (0.0 si la muestra es vacía o degenerada)."""
    if total <= 0:
        return 0.0
    acumulado = 0.0
    for conteo in conteos.values():
        if conteo <= 0:
            continue
        probabilidad = conteo / total
        acumulado -= probabilidad * math.log2(probabilidad)
    return acumulado


def informacion_mutua_bits(
    pares: Dict[Tuple[str, str], int], x_bins: Dict[str, int], y_bins: Dict[str, int], total: int
) -> float:
    """`I(X;Y) = Σ p(x,y)·log2( p(x,y) / (p(x)·p(y)) )` en BITS."""
    if total <= 0:
        return 0.0
    acumulado = 0.0
    for (x, y), conteo in pares.items():
        if conteo <= 0:
            continue
        p_xy = conteo / total
        p_x = x_bins[x] / total
        p_y = y_bins[y] / total
        if p_x <= 0 or p_y <= 0:
            continue
        acumulado += p_xy * math.log2(p_xy / (p_x * p_y))
    return max(0.0, acumulado)


def calcular_ranking_informacion_mutua(
    filas: Sequence[Dict[str, str]], candidatas: Sequence[str]
) -> List[Dict[str, Any]]:
    """Ranking descendente de información mutua (bits) sobre la etiqueta ternaria.

    Desempate alfabético: el ranking es determinista bit-a-bit para una misma matriz.
    """
    etiquetas = [str(fila.get(COLUMNA_ETIQUETA) or "").strip() for fila in filas]
    total = len(filas)
    y_bins: Dict[str, int] = {}
    for etiqueta in etiquetas:
        y_bins[etiqueta] = y_bins.get(etiqueta, 0) + 1
    entropia_y = entropia_bits(y_bins, total)

    ranking: List[Dict[str, Any]] = []
    for columna in candidatas:
        valores = [a_flotante(fila.get(columna)) for fila in filas]
        observados = [valor for valor in valores if valor is not None]
        if len(observados) < SOPORTE_MINIMO:
            continue
        cortes = cortes_por_rangos(observados)
        x_bins: Dict[str, int] = {}
        pares: Dict[Tuple[str, str], int] = {}
        for valor, etiqueta in zip(valores, etiquetas):
            bin_x = discretizar(valor, cortes)
            x_bins[bin_x] = x_bins.get(bin_x, 0) + 1
            clave = (bin_x, etiqueta)
            pares[clave] = pares.get(clave, 0) + 1
        mutua = informacion_mutua_bits(pares, x_bins, y_bins, total)
        ranking.append(
            {
                "variable": columna,
                "informacion_mutua_bits": round(mutua, 6),
                "entropia_variable_bits": round(entropia_bits(x_bins, total), 6),
                "entropia_etiqueta_bits": round(entropia_y, 6),
                "valores_observados": len(observados),
                "valores_ausentes": total - len(observados),
                "bins_utilizados": len(x_bins),
                "cortes": [round(corte, 6) for corte in cortes],
                "estado": "MEDIDA",
            }
        )
    ranking.sort(key=lambda item: (-item["informacion_mutua_bits"], item["variable"]))
    return ranking



# ═════════════════════════════════════════════════════════════════════════════════════════════
# ZONA 3 — ÁRBOL CART ESPARSO SOBRE LA RUPTURA RESIDUAL
# ═════════════════════════════════════════════════════════════════════════════════════════════
def impureza_gini(pos: int, n: int) -> float:
    """Gini binario `2·p·(1−p)` (idéntico al índice multiclase de dos clases)."""
    if n <= 0:
        return 0.0
    p = pos / n
    return 2.0 * p * (1.0 - p)


def _mejor_corte(
    registros: Sequence[Tuple[Dict[str, Optional[float]], int]], candidatas: Sequence[str], min_hoja: int
) -> Optional[Dict[str, Any]]:
    """Busca el corte binario que MINIMIZA la impureza ponderada (todos los umbrales observados).

    Cada variable se ordena UNA vez por nodo y se evalúan todos los umbrales intermedios con sumas
    acumuladas: `O(k·log k)` por variable y nodo, no `O(k²)`. Semántica declarada del dato ausente:
    `SIN_DATO` NO supera el umbral y cae en la rama `<=`. Desempate determinista: impureza, nombre
    de la variable, umbral.
    """
    total = len(registros)
    if total <= 0:
        return None
    mejor: Optional[Dict[str, Any]] = None
    mejor_clave: Optional[Tuple[float, str, float]] = None
    for columna in candidatas:
        observados = sorted(
            (valores[columna], y) for valores, y in registros if valores.get(columna) is not None
        )
        if len(observados) < 2:
            continue
        ausentes_n = total - len(observados)
        ausentes_pos = sum(y for valores, y in registros if valores.get(columna) is None)
        acumulado_n = ausentes_n
        acumulado_pos = ausentes_pos
        for indice in range(len(observados) - 1):
            acumulado_n += 1
            acumulado_pos += observados[indice][1]
            valor_actual, valor_siguiente = observados[indice][0], observados[indice + 1][0]
            if valor_siguiente == valor_actual:
                continue
            der_n = total - acumulado_n
            if acumulado_n < min_hoja or der_n < min_hoja:
                continue
            der_pos = sum(y for _, y in observados[indice + 1:])
            impureza = (
                acumulado_n * impureza_gini(acumulado_pos, acumulado_n)
                + der_n * impureza_gini(der_pos, der_n)
            ) / total
            umbral = (valor_actual + valor_siguiente) / 2.0
            clave = (round(impureza, 12), columna, float(umbral))
            if mejor_clave is None or clave < mejor_clave:
                mejor_clave = clave
                mejor = {"variable": columna, "umbral": float(umbral), "impureza": impureza}
    return mejor


def construir_arbol_esparso(
    registros: Sequence[Tuple[Dict[str, Optional[float]], int]],
    candidatas: Sequence[str],
    profundidad: int = PROFUNDIDAD_MAXIMA_DEFAULT,
    min_hoja: int = MIN_HOJA_DEFAULT,
    condiciones: Sequence[str] = (),
) -> Dict[str, Any]:
    """Construye el árbol de forma recursiva; las hojas quedan etiquetadas con su regla legible."""
    total = len(registros)
    positivos = sum(y for _, y in registros)
    nodo: Dict[str, Any] = {
        "soporte": total,
        "rupturas": positivos,
        "tasa_ruptura_pct": round(100.0 * positivos / total, 2) if total else 0.0,
        "condiciones": list(condiciones),
        "hoja": True,
    }
    if profundidad <= 0 or total < 2 * min_hoja or positivos in (0, total):
        return nodo
    corte = _mejor_corte(registros, candidatas, min_hoja)
    if corte is None:
        return nodo
    columna, umbral = corte["variable"], corte["umbral"]
    izq = [registro for registro in registros if registro[0].get(columna) is None or registro[0][columna] <= umbral]
    der = [registro for registro in registros if not (registro[0].get(columna) is None or registro[0][columna] <= umbral)]
    nodo.update(
        {
            "hoja": False,
            "variable": columna,
            "umbral": round(umbral, 6),
            "impureza": round(corte["impureza"], 6),
            "izq": construir_arbol_esparso(
                izq, candidatas, profundidad - 1, min_hoja,
                list(condiciones) + [f"{columna} <= {umbral:.4f} (o {ETIQUETA_SIN_DATO})"],
            ),
            "der": construir_arbol_esparso(
                der, candidatas, profundidad - 1, min_hoja,
                list(condiciones) + [f"{columna} > {umbral:.4f}"],
            ),
        }
    )
    return nodo


def hojas_del_arbol(nodo: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Recorre el árbol y devuelve las hojas (con su condición y su tasa observada)."""
    if nodo.get("hoja"):
        return [nodo]
    hojas: List[Dict[str, Any]] = []
    hojas.extend(hojas_del_arbol(nodo["izq"]))
    hojas.extend(hojas_del_arbol(nodo["der"]))
    return hojas


def inducir_reglas_veto(
    arbol: Dict[str, Any],
    pureza_minima_pct: float = PUREZA_MINIMA_PCT,
    soporte_minimo: int = SOPORTE_MINIMO,
    lift_minimo: float = LIFT_MINIMO,
) -> List[Dict[str, Any]]:
    """Extrae las hojas que constituyen regla de VETO según el Decreto D4 ratificado."""
    tasa_base = (100.0 * arbol["rupturas"] / arbol["soporte"]) if arbol.get("soporte") else 0.0
    reglas: List[Dict[str, Any]] = []
    for hoja in hojas_del_arbol(arbol):
        if not hoja.get("condiciones") or hoja["soporte"] <= 0:
            continue
        pureza = hoja["tasa_ruptura_pct"]
        if pureza < pureza_minima_pct or hoja["soporte"] < soporte_minimo:
            continue
        lift = (pureza / tasa_base) if tasa_base > 0 else 0.0
        if lift < lift_minimo:
            continue
        reglas.append(
            {
                "condicion_booleana": " AND ".join(hoja["condiciones"]),
                "tasa_ruptura_pct": round(pureza, 2),
                "soporte": int(hoja["soporte"]),
                "rupturas_observadas": int(hoja["rupturas"]),
                "lift": round(lift, 3),
                "tasa_base_ruptura_pct": round(tasa_base, 2),
                "rotulo": ROTULO_HIPOTESIS,
            }
        )
    reglas.sort(key=lambda regla: (-regla["tasa_ruptura_pct"], -regla["soporte"], regla["condicion_booleana"]))
    return reglas


# ═════════════════════════════════════════════════════════════════════════════════════════════
# ZONA 4 — ORQUESTADOR: RANKING + BARRIDO DEL ÁRBOL + REGLAS + REPORTE
# ═════════════════════════════════════════════════════════════════════════════════════════════
def _resumen_arbol(nodo: Dict[str, Any], nivel: int = 0) -> List[str]:
    """Aplana el árbol en líneas ASCII (profundidad declarada, sin recursión silenciosa)."""
    marca = "HOJA" if nodo.get("hoja") else f"{nodo.get('variable')} <= {nodo.get('umbral')}"
    lineas = [
        "  " * nivel
        + f"· {marca} | n={nodo.get('soporte')} rupturas={nodo.get('rupturas')} "
        + f"({nodo.get('tasa_ruptura_pct')}%)"
    ]
    if not nodo.get("hoja"):
        lineas.extend(_resumen_arbol(nodo["izq"], nivel + 1))
        lineas.extend(_resumen_arbol(nodo["der"], nivel + 1))
    return lineas


def _tablero_ascii(reporte: Dict[str, Any], top: Optional[int] = None) -> str:
    """Tablero de 5 bloques: partición, ranking, árbol, reglas y cobertura."""
    lineas: List[str] = []
    ancho = 100
    muestra = reporte.get("muestra") or {}
    lineas.append("=" * ancho)
    lineas.append("🧠 Q-BE — MINERÍA DE SHANNON Y ÁRBOL ESPARSO DE VETO [ARCH-1.4.70 / LN-QBE-129]")
    lineas.append("   Régimen: [DBBD-FUNGIBLE] · Solo lectura · Reglas SUGERIDAS (no ejecutan triaje)")
    lineas.append("=" * ancho)
    lineas.append(f"  DATASET   : {reporte.get('ruta_dataset')}")
    lineas.append(
        f"  MUESTRA   : {muestra.get('filas')} partidos · {muestra.get('candidatas_evaluadas')} candidatas "
        f"medidas de {muestra.get('candidatas_derivadas')} derivadas (Zona B)"
    )
    particion = reporte.get("particion") or {}
    lineas.append(
        "  PARTICIÓN : "
        + " · ".join(f"{clave}={valor}" for clave, valor in sorted(particion.items()))
        + f" · tasa base ruptura={reporte.get('tasa_base_ruptura_pct')}%"
    )
    lineas.append(f"  ENTROPÍA Y: {reporte.get('entropia_etiqueta_bits')} bits")
    lineas.append("-" * ancho)
    ranking = reporte.get("ranking_informacion_mutua") or []
    limite = top if top else len(ranking)
    lineas.append(
        f"  [1] RANKING DE INFORMACIÓN MUTUA (bits) — mostrando {min(limite, len(ranking))}/{len(ranking)}"
    )
    for posicion, item in enumerate(ranking[:limite], start=1):
        lineas.append(
            f"    {posicion:2d}. {item['variable']:16s} I(X;Y)={item['informacion_mutua_bits']:7.6f} bits "
            f"· H(X)={item['entropia_variable_bits']:6.4f} · obs={item['valores_observados']}"
        )
    lineas.append("-" * ancho)
    configuracion = reporte.get("configuracion_arbol") or {}
    lineas.append(
        f"  [2] ÁRBOL ESPARSO — profundidad<={configuracion.get('profundidad_maxima')} · "
        f"hoja mínima={configuracion.get('min_hoja')} (canónica {configuracion.get('min_hoja_canonica')}) · "
        f"criterio={configuracion.get('criterio')} · estado={configuracion.get('calidad')}"
    )
    lineas.extend(_resumen_arbol(reporte.get("arbol_esparso") or {}))
    lineas.append("-" * ancho)
    reglas = reporte.get("reglas_veto_inducidas") or []
    lineas.append(f"  [3] REGLAS DE VETO INDUCIDAS ({len(reglas)}) — {ROTULO_HIPOTESIS}")
    for posicion, regla in enumerate(reglas, start=1):
        lineas.append(f"    V{posicion}. SI {regla['condicion_booleana']}")
        lineas.append(
            f"        ⇒ ruptura={regla['tasa_ruptura_pct']}% · soporte={regla['soporte']} "
            f"· lift={regla['lift']}x · base={regla['tasa_base_ruptura_pct']}%"
        )
    lineas.append("-" * ancho)
    cobertura = reporte.get("cobertura") or {}
    lineas.append(
        f"  [4] COBERTURA: {cobertura.get('partidos_cubiertos')}/{muestra.get('filas')} partidos "
        f"({cobertura.get('cobertura_pct')}%) · rupturas cubiertas={cobertura.get('rupturas_cubiertas')}"
    )
    lineas.append(
        f"  [5] DEUDA DECLARADA: {reporte.get('degradacion_declarada') or 'sin degradación: umbrales D4 plenos'}"
    )
    lineas.append("=" * ancho)
    return "\n".join(lineas)



def ejecutar_mineria_shannon(
    ruta_dataset: str = RUTA_DATASET_DEFAULT,
    ruta_reporte: Optional[str] = None,
    top: Optional[int] = None,
    profundidad: int = PROFUNDIDAD_MAXIMA_DEFAULT,
    min_hoja: int = MIN_HOJA_DEFAULT,
) -> Dict[str, Any]:
    """Ejecuta la minería completa y devuelve el reporte (escribe JSON sólo si se pide la ruta).

    Cero escritura por defecto: la hermeticidad bajo The Shield exige que el veredicto no mute el
    disco. La CLI es la única que exporta el artefacto de investigación.
    """
    columnas, filas = leer_dataset(ruta_dataset)
    candidatas = columnas_candidatas(columnas)
    total = len(filas)
    particion: Dict[str, int] = {}
    for fila in filas:
        etiqueta = str(fila.get(COLUMNA_ETIQUETA) or "").strip() or "SIN_ETIQUETA"
        particion[etiqueta] = particion.get(etiqueta, 0) + 1
    if total <= 0 or len(candidatas) < 15:
        return {
            "sonda": SONDA_MINERIA,
            "status": "SIN_DATOS",
            "ruta_dataset": os.path.abspath(ruta_dataset),
            "particion": particion,
            "ranking_informacion_mutua": [],
            "reglas_veto_inducidas": [],
            "mensaje": "Dataset vacío o con menos de 15 candidatas de Zona B: cero cifras fabricadas.",
        }

    rupturas = int(particion.get(CLASE_RUPTURA, 0))
    tasa_base = (100.0 * rupturas / total) if total else 0.0
    ranking = calcular_ranking_informacion_mutua(filas, candidatas)
    registros = [
        (
            {columna: a_flotante(fila.get(columna)) for columna in candidatas},
            1 if str(fila.get(COLUMNA_ETIQUETA) or "").strip() == CLASE_RUPTURA else 0,
        )
        for fila in filas
    ]

    configuraciones: List[Tuple[int, int]] = [(int(profundidad), int(min_hoja))]
    configuraciones.extend(
        (int(profundidad), hoja) for hoja in BARRIDO_MIN_HOJA if hoja != int(min_hoja)
    )
    for profundidad_barrida in BARRIDO_PROFUNDIDAD:
        if profundidad_barrida == int(profundidad):
            continue
        configuraciones.append((profundidad_barrida, int(min_hoja)))
        configuraciones.extend(
            (profundidad_barrida, hoja) for hoja in BARRIDO_MIN_HOJA if hoja != int(min_hoja)
        )

    evaluadas: List[Tuple[Tuple[Any, ...], int, int, Dict[str, Any], List[Dict[str, Any]]]] = []
    for profundidad_efectiva, hoja_minima in configuraciones:
        arbol_candidato = construir_arbol_esparso(registros, candidatas, profundidad_efectiva, hoja_minima)
        reglas_candidatas = inducir_reglas_veto(arbol_candidato)
        pureza_maxima = max((regla["tasa_ruptura_pct"] for regla in reglas_candidatas), default=0.0)
        # Principio de MINIMALIDAD GOBERNADA: se adopta la PRIMERA configuración del orden declarado
        # (canónica primero; hoja mínima antes que profundidad) que induce al menos 2 reglas D4.
        clave = (-len(reglas_candidatas), -pureza_maxima, profundidad_efectiva, hoja_minima)
        evaluadas.append((clave, profundidad_efectiva, hoja_minima, arbol_candidato, reglas_candidatas))
        if len(reglas_candidatas) >= 2:
            break
    if len(evaluadas) > 1 and len(evaluadas[-1][4]) >= 2:
        _, profundidad_efectiva, hoja_efectiva, arbol, reglas = evaluadas[-1]
    else:
        evaluadas.sort(key=lambda elemento: elemento[0])
        _, profundidad_efectiva, hoja_efectiva, arbol, reglas = evaluadas[0]
    calidad = (
        "CANONICA"
        if (profundidad_efectiva, hoja_efectiva) == (int(profundidad), int(min_hoja))
        else "BARRIDO_GOBERNADO"
    )

    degradacion: Optional[str] = None
    if len(reglas) < 2:
        reglas = inducir_reglas_veto(arbol, pureza_minima_pct=PUREZA_PISO_JUEZ_PCT)
        degradacion = (
            "PUREZA_RELAJADA_A_50: la configuración con umbral D4 (60%) no indujo 2 reglas; se publica "
            "el piso del Juez (50%) y la degradación queda declarada."
        )

    condiciones_regla = {regla["condicion_booleana"] for regla in reglas}
    hojas = [hoja for hoja in hojas_del_arbol(arbol) if hoja.get("condiciones")]
    cubiertas = sum(
        hoja["soporte"] for hoja in hojas if " AND ".join(hoja["condiciones"]) in condiciones_regla
    )
    rupturas_cubiertas = sum(
        hoja["rupturas"] for hoja in hojas if " AND ".join(hoja["condiciones"]) in condiciones_regla
    )



    reporte: Dict[str, Any] = {
        "sonda": SONDA_MINERIA,
        "status": "EXITO",
        "ruta_dataset": os.path.abspath(ruta_dataset),
        "muestra": {
            "filas": total,
            "candidatas_derivadas": len(candidatas),
            "candidatas_evaluadas": len(ranking),
        },
        "particion": particion,
        "entropia_etiqueta_bits": round(entropia_bits(particion, total), 6),
        "tasa_base_ruptura_pct": round(tasa_base, 2),
        "ranking_informacion_mutua": ranking,
        "arbol_esparso": arbol,
        "configuracion_arbol": {
            "profundidad_maxima": int(profundidad_efectiva),
            "profundidad_canonica": int(profundidad),
            "min_hoja": int(hoja_efectiva),
            "min_hoja_canonica": int(min_hoja),
            "criterio": "gini",
            "calidad": calidad,
        },
        "reglas_veto_inducidas": reglas,
        "cobertura": {
            "partidos_cubiertos": int(cubiertas),
            "cobertura_pct": round(100.0 * cubiertas / total, 2),
            "rupturas_cubiertas": int(rupturas_cubiertas),
            "rupturas_totales": rupturas,
        },
        "degradacion_declarada": degradacion,
        "leyes": {
            "etiqueta": COLUMNA_ETIQUETA,
            "clase_veto": CLASE_RUPTURA,
            "bins": BINS_DISCRETIZACION,
            "pureza_minima_pct": PUREZA_MINIMA_PCT,
            "soporte_minimo": SOPORTE_MINIMO,
            "lift_minimo": LIFT_MINIMO,
            "rotulo": ROTULO_HIPOTESIS,
            "anti_fuga": "Zonas A/C/D prohibidas como predictoras: sólo celdas vNN_{local,visita}",
        },
    }
    reporte["tablero_ascii"] = _tablero_ascii(reporte, top=top)
    if ruta_reporte:
        directorio = os.path.dirname(os.path.abspath(ruta_reporte))
        os.makedirs(directorio, exist_ok=True)
        with open(ruta_reporte, "w", encoding="utf-8") as archivo:
            json.dump(reporte, archivo, ensure_ascii=False, indent=2)
            archivo.write("\n")
        reporte["ruta_reporte"] = os.path.abspath(ruta_reporte)
    return reporte



def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI: tablero ASCII a consola (y `--json` para el reporte íntegro)."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (AttributeError, OSError, ValueError):
            pass
    analizador = argparse.ArgumentParser(
        description="[ARCH-1.4.70] Minería de información mutua y árbol esparso de veto (solo lectura)."
    )
    analizador.add_argument("--ruta-dataset", default=RUTA_DATASET_DEFAULT, help="matriz canónica de entrada")
    analizador.add_argument("--ruta-reporte", default=RUTA_REPORTE_DEFAULT, help="JSON de salida del reporte")
    analizador.add_argument("--top", type=int, default=None, help="cuántas variables mostrar en el ranking")
    analizador.add_argument(
        "--profundidad", type=int, default=PROFUNDIDAD_MAXIMA_DEFAULT, help="profundidad máxima del árbol"
    )
    analizador.add_argument("--min-hoja", type=int, default=MIN_HOJA_DEFAULT, help="soporte mínimo por hoja")
    analizador.add_argument("--json", action="store_true", dest="como_json", help="emitir el reporte completo")
    analizador.add_argument(
        "--sin-reporte", action="store_true", help="no escribir el JSON de investigación (solo consola)"
    )
    argumentos = analizador.parse_args(argv)

    reporte = ejecutar_mineria_shannon(
        ruta_dataset=argumentos.ruta_dataset,
        ruta_reporte=None if argumentos.sin_reporte else argumentos.ruta_reporte,
        top=argumentos.top,
        profundidad=int(argumentos.profundidad),
        min_hoja=int(argumentos.min_hoja),
    )
    if argumentos.como_json:
        print(json.dumps(reporte, ensure_ascii=False, indent=2))
        return 0 if reporte.get("status") == "EXITO" else 1
    print(reporte.get("tablero_ascii") or reporte.get("mensaje") or "")
    if reporte.get("ruta_reporte"):
        print(f"  REPORTE JSON: {reporte['ruta_reporte']}")
    return 0 if reporte.get("status") == "EXITO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
