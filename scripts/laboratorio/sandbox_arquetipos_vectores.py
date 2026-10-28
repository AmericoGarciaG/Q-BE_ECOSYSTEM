# -*- coding: utf-8 -*-
"""
🧬 Q-BE LABORATORIO — SANDBOX DE ARQUETIPOS Y VECTORES
[LN-QBE-126] / [ARCH-1.4.66] · Base de Gobierno: Kybern Framework v12.0 · [HÍBRIDO DUAL-TRACK]

Instrumento CLI-FIRST (cero HTTP, cero plantillas, cero estado) que INDUCE la firma
estadística de los tres desenlaces soberanos a partir de la bóveda real:

    1. Partición ternaria delegada — la clase de cada partido concluido la decide la función
       pura canónica `resolver_orden_fiduciario_con_indiferencia` ([LN-QBE-124]) sobre el trío
       soberano y el ΔAlt⁺ realmente aplicado. El sandbox NO ordena por segunda vía: transcribe
       `r_max` → P_MAX, `r_mid` → P_MID, `r_low` → P_LOW.
    2. Matriz Z-Score global — cada columna se estandariza (μ, σ) sobre los 97 partidos; σ = 0
       se declara como z = 0.0 (guarda de varianza nula, jamás división por cero).
    3. Centroides V_P_max / V_P_mid / V_P_low y Vector de Contraste ΔV_Ruptura = V_P_low − V_P_max.
    4. Ranking univariado de Fisher F = SS_entre / SS_dentro, descendente, con etiqueta
       fiduciaria de poder separador.

Régimen declarado:
* `[DIRGEN-STRICT]` — Z-Score, centroides, contraste y Fisher (álgebra pura, sin I/O).
* `[DBBD-FUNGIBLE]` — ingesta, composición de la matriz y tablero ASCII.

Read-only absoluto: abre `PersistenceGateway.read_session()` y jamás escribe en la bóveda
(cero `INSERT`/`UPDATE`/`DELETE`/`commit`). La única escritura es el reporte JSON de laboratorio.

Uso:
    python -m scripts.laboratorio.sandbox_arquetipos_vectores
    python -m scripts.laboratorio.sandbox_arquetipos_vectores --top 10
    python -m scripts.laboratorio.sandbox_arquetipos_vectores --json
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

RAIZ_PROYECTO = Path(__file__).resolve().parents[2]
if str(RAIZ_PROYECTO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROYECTO))

from src.core.contracts.portfolio_math import resolver_orden_fiduciario_con_indiferencia
from src.observatory.core.factor_attribution import (
    CLAVE_MACRO_STATS,
    _CATALOGO_32,
    _CLAVES_H2H_STATS,
    _CLAVES_MACRO_STATS,
    _FORMATO_INSUMO,
    _RESPALDO_INSUMO,
)
from src.storage.gateway import PersistenceGateway
from src.storage.models import FixtureSnapshot, Match, SovereignDistribution

logger = logging.getLogger("SandboxArquetipos")

# ── Clases fiduciarias (vocabulario sellado [LN-QBE-126]) ─────────────────────────────────────
CLASE_PMAX = "P_MAX"
CLASE_PMID = "P_MID"
CLASE_PLOW = "P_LOW"
CLASES: Tuple[str, ...] = (CLASE_PMAX, CLASE_PMID, CLASE_PLOW)

# ── Bloques de dimensión ─────────────────────────────────────────────────────────────────────
BLOQUE_ESTRUCTURAL = "ESTRUCTURAL"
BLOQUE_METAESTOCASTICO = "METAESTOCASTICO"

# ── Exclusión declarada del catálogo de 32 (cero imputación) ──────────────────────────────────
EXCLUSIONES: Dict[str, str] = {
    "V16": "Cuarentena [LN-QBE-123]: FotMob no publica el leaderboard de big chances concedidas.",
    "V28": "Récord de sede sin magnitud firmada: la celda es nominal, no métrica ([LN-QBE-105]).",
    "V31": "Forma 5P sin evidencia en la traza soberana (0/97 insumos encendidos).",
    "V32": "Varianza ΔxPTS sin evidencia en la traza soberana (0/97 insumos encendidos).",
}

# ── Metadatos estocásticos del registro soberano (7 dimensiones; no son del catálogo) ────────
METADATOS: Tuple[Tuple[str, str], ...] = (
    ("P1_PRIMA", "P' Soberana del LOCAL"),
    ("PX_PRIMA", "P' Soberana del EMPATE"),
    ("P2_PRIMA", "P' Soberana del VISITANTE"),
    ("P_MAX_PRIMA", "P' del vértice P_max (máximo del trío)"),
    ("P_MID_PRIMA", "P' del vértice P_mid (mediana del trío)"),
    ("DELTA_ETA", "Δη = ln(λ_local / λ_visita)"),
    ("DELTA_EPIST", "Δ_epist publicado por el motor soberano"),
)

# ── Umbrales de poder separador (F-ratio univariado) ─────────────────────────────────────────
UMBRAL_FISHER_DECISIVA = 1.0    # η² ≥ 0.5 aproximado: la clase explica más que el ruido
UMBRAL_FISHER_MODERADA = 0.25   # señal presente pero subordinada
UMBRAL_FISHER_SATURACION = 1e6  # SS_dentro = 0 con SS_entre > 0 ⇒ señal perfecta (razón indefinida)
UMBRAL_CONTRASTE_VETO = 0.25    # |ΔV_Ruptura| en unidades σ para sugerir veto de celdas
TOLERANCIA_SIGMA = 1e-12        # guarda de varianza nula

ETIQUETA_DECISIVA = "DECISIVA"
ETIQUETA_MODERADA = "MODERADA"
ETIQUETA_RUIDO = "RUIDO"
ETIQUETA_NULO = "NULO"

ANCHO_TABLERO = 94
RUTA_SALIDA_JSON = RAIZ_PROYECTO / "data" / "output" / "arquetipos_vectores_reporte.json"


# ═════════════════════════════════════════════════════════════════════════════════════════════
# NÚCLEO MATEMÁTICO PURO — [DIRGEN-STRICT] (cero I/O, cero estado, cero números mágicos)
# ═════════════════════════════════════════════════════════════════════════════════════════════
def _numero(valor: Any) -> Optional[float]:
    """Lectura numérica honesta: ausencia, texto no convertible, NaN e ∞ ⇒ `None`."""
    if valor is None or isinstance(valor, bool):
        return None
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    if math.isnan(numero) or math.isinf(numero):
        return None
    return numero


def _redondear(valor: Optional[float], decimales: int = 6) -> Optional[float]:
    """Redondeo de exhibición (idempotente); `None` se propaga sin imputar."""
    return None if valor is None else round(float(valor), decimales)


def calcular_centroide_zscore(
    matriz_clase: Sequence[Dict[str, Optional[float]]],
) -> Dict[str, float]:
    """Centroide de una clase: media aritmética de las celdas PRESENTES por dimensión.

    Invarianzas [LN-QBE-126]:
    * Una celda ausente (`None`) NO se imputa: la dimensión promedia sólo sus valores reales.
    * Una dimensión sin ninguna celda presente no aparece en el centroide (jamás media de vacío).
    * Dimensión constante ⇒ su media es exactamente ese valor (no hay división por σ aquí).
    """
    sumas: Dict[str, float] = {}
    conteos: Dict[str, int] = {}
    for fila in matriz_clase or ():
        for clave, valor in fila.items():
            numero = _numero(valor)
            if numero is None:
                continue
            sumas[clave] = sumas.get(clave, 0.0) + numero
            conteos[clave] = conteos.get(clave, 0) + 1
    return {clave: _redondear(sumas[clave] / conteos[clave]) for clave in sumas if conteos[clave]}


def _estadisticos_columna(valores: Sequence[float]) -> Tuple[float, float]:
    """(μ, σ) poblacional de la columna; columna constante ⇒ (μ, 0.0) sin excepción."""
    if not valores:
        return 0.0, 0.0
    media = sum(valores) / len(valores)
    varianza = sum((valor - media) ** 2 for valor in valores) / len(valores)
    return media, math.sqrt(max(varianza, 0.0))


def estandarizar_matriz(
    matriz: Sequence[Dict[str, Optional[float]]], columnas: Sequence[str]
) -> List[Dict[str, Optional[float]]]:
    """Z-Score GLOBAL por columna (μ, σ sobre toda la muestra). Guarda: σ ≤ 1e-12 ⇒ z = 0.0."""
    parametros: Dict[str, Tuple[float, float]] = {}
    for columna in columnas:
        presentes = [
            numero for numero in (_numero(fila.get(columna)) for fila in matriz) if numero is not None
        ]
        parametros[columna] = _estadisticos_columna(presentes)

    estandarizada: List[Dict[str, Optional[float]]] = []
    for fila in matriz:
        nueva: Dict[str, Optional[float]] = {}
        for columna in columnas:
            numero = _numero(fila.get(columna))
            media, sigma = parametros[columna]
            if numero is None:
                nueva[columna] = None
            elif sigma <= TOLERANCIA_SIGMA:
                nueva[columna] = 0.0
            else:
                nueva[columna] = _redondear((numero - media) / sigma)
        estandarizada.append(nueva)
    return estandarizada


def _etiqueta_poder(f_ratio: float, ss_dentro: float, ss_entre: float) -> str:
    """Etiqueta fiduciaria del poder separador de una dimensión (vocabulario sellado)."""
    if ss_entre <= TOLERANCIA_SIGMA and ss_dentro <= TOLERANCIA_SIGMA:
        return ETIQUETA_NULO
    if ss_dentro <= TOLERANCIA_SIGMA:
        return ETIQUETA_DECISIVA if ss_entre > 0.0 else ETIQUETA_NULO
    if f_ratio >= UMBRAL_FISHER_DECISIVA:
        return ETIQUETA_DECISIVA
    if f_ratio >= UMBRAL_FISHER_MODERADA:
        return ETIQUETA_MODERADA
    return ETIQUETA_RUIDO


def calcular_fisher_ratio(
    clases: Dict[str, Sequence[Dict[str, Optional[float]]]],
) -> List[Dict[str, Any]]:
    """F-ratio univariado de Fisher por dimensión, ordenado descendente (empate: nombre).

        F = SS_entre / SS_dentro   con   SS_entre = Σ_c n_c · (μ_c − μ)²
                                        SS_dentro = Σ_c Σ_i (x_ci − μ_c)²

    Guardas [LN-QBE-126]:
    * `SS_dentro = 0` con `SS_entre > 0` ⇒ separación PERFECTA: la razón es indefinida y se
      satura en `UMBRAL_FISHER_SATURACION`, declarando `separacion_perfecta = True`.
    * `SS_dentro = 0` y `SS_entre = 0` ⇒ clases indistinguibles: F = 0.0 (`NULO`).
    * Dimensión sin ninguna celda presente en la muestra ⇒ no se emite fila (cero invención).
    """
    columnas: List[str] = []
    for filas in clases.values():
        for fila in filas:
            for clave in fila:
                if clave not in columnas:
                    columnas.append(clave)

    ranking: List[Dict[str, Any]] = []
    for columna in columnas:
        medias: Dict[str, float] = {}
        conteos: Dict[str, int] = {}
        ss_dentro = 0.0
        total = 0
        suma_total = 0.0
        for clase, filas in clases.items():
            valores = [
                numero for numero in (_numero(fila.get(columna)) for fila in filas) if numero is not None
            ]
            if not valores:
                continue
            media = sum(valores) / len(valores)
            medias[clase] = media
            conteos[clase] = len(valores)
            ss_dentro += sum((valor - media) ** 2 for valor in valores)
            total += len(valores)
            suma_total += sum(valores)
        if total == 0:
            continue

        media_global = suma_total / total
        ss_entre = sum(conteos[clase] * (medias[clase] - media_global) ** 2 for clase in medias)
        separacion_perfecta = ss_dentro <= TOLERANCIA_SIGMA and ss_entre > TOLERANCIA_SIGMA
        if ss_dentro <= TOLERANCIA_SIGMA:
            f_ratio = UMBRAL_FISHER_SATURACION if ss_entre > TOLERANCIA_SIGMA else 0.0
        else:
            f_ratio = ss_entre / ss_dentro

        ranking.append(
            {
                "id_variable": columna,
                "f_ratio": _redondear(f_ratio),
                "poder_separador": _etiqueta_poder(f_ratio, ss_dentro, ss_entre),
                "separacion_perfecta": bool(separacion_perfecta),
                "cobertura": total,
                "media_global": _redondear(media_global),
                "medias_por_clase": {clase: _redondear(valor) for clase, valor in medias.items()},
                "ss_entre": _redondear(ss_entre),
                "ss_dentro": _redondear(ss_dentro),
                "eta_cuadrado": _redondear(
                    ss_entre / (ss_entre + ss_dentro) if (ss_entre + ss_dentro) > TOLERANCIA_SIGMA else 0.0
                ),
            }
        )

    ranking.sort(key=lambda fila: (-float(fila["f_ratio"]), str(fila["id_variable"])))
    return ranking


# ═════════════════════════════════════════════════════════════════════════════════════════════
# INGESTA READ-ONLY — transcripción de la bóveda ([DBBD-FUNGIBLE] sobre contratos sellados)
# ═════════════════════════════════════════════════════════════════════════════════════════════
VARIABLES_ESTRUCTURALES: Tuple[Tuple[str, str], ...] = tuple(
    (fila[0], fila[1]) for fila in _CATALOGO_32 if fila[0] not in EXCLUSIONES
)
DIMENSIONES_ESTRUCTURALES: Tuple[str, ...] = tuple(identificador for identificador, _ in VARIABLES_ESTRUCTURALES)
DIMENSIONES_META: Tuple[str, ...] = tuple(clave for clave, _ in METADATOS)
DIMENSIONES: Tuple[str, ...] = DIMENSIONES_ESTRUCTURALES + DIMENSIONES_META
NOMBRES_DIMENSION: Dict[str, str] = {
    **{identificador: f"{identificador} · {nombre}" for identificador, nombre in VARIABLES_ESTRUCTURALES},
    **{clave: f"{clave} · {descripcion}" for clave, descripcion in METADATOS},
}


def _entero_firmado(valor: Any) -> Optional[int]:
    """Transcribe una cadena firmada de marcador (`"+3"`, `"-2"`, `3`) sin recalcular nada."""
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)):
        numero = _numero(valor)
        return None if numero is None else int(round(numero))
    if isinstance(valor, str):
        limpio = valor.strip().replace("−", "-")
        if not limpio:
            return None
        try:
            return int(round(float(limpio)))
        except ValueError:
            return None
    return None


def _magnitud_insumo(insumos: Dict[str, Any], identificador: str) -> Tuple[Optional[float], Optional[float]]:
    """(local, visita) del bloque `insumos` [LN-QBE-102], con respaldo declarado [ARCH-1.4.44]."""
    receta = _FORMATO_INSUMO.get(identificador)
    if receta is None:
        return None, None
    clave_local, clave_visita, _formato = receta
    local = _numero(insumos.get(clave_local))
    visita = _numero(insumos.get(clave_visita)) if clave_visita else None
    if local is None:
        respaldo = _RESPALDO_INSUMO.get(identificador)
        if respaldo is not None:
            claves, _formato_respaldo, _nota = respaldo
            local = _numero(insumos.get(claves[0]))
            if local is not None and len(claves) > 1:
                visita = _numero(insumos.get(claves[1]))
    return local, visita


def _magnitud_macro(insumos: Dict[str, Any], identificador: str) -> Tuple[Optional[float], Optional[float]]:
    """(local, visita) del agregado torneal `macro_stats` [LN-QBE-121]; cero imputación parcial."""
    receta = _CLAVES_MACRO_STATS.get(identificador)
    if receta is None:
        return None, None
    claves, formato, _nota = receta
    macro = insumos.get(CLAVE_MACRO_STATS)
    if not isinstance(macro, dict):
        return None, None

    def _de_bando(bando: str) -> Optional[float]:
        bloque = macro.get(bando)
        if not isinstance(bloque, dict):
            return None
        # V24 compone la magnitud firmada a favor/en contra; V25 declara sólo la primaria
        # (amarillas) porque ponderar rojas exigiría un peso que ninguna ley fija (cero invención).
        if formato == "penales" and len(claves) >= 2:
            primario = _numero(bloque.get(claves[0]))
            secundario = _numero(bloque.get(claves[1]))
            if primario is None or secundario is None:
                return None
            return float(primario) - float(secundario)
        primario = _numero(bloque.get(claves[0]))
        return None if primario is None else float(primario)

    return _de_bando("local"), _de_bando("visita")


def _par_magnitudes(
    insumos: Dict[str, Any], h2h_stats: Dict[str, Any], identificador: str
) -> Tuple[Optional[float], Optional[float], bool]:
    """(local, visita, bilateral) de una dimensión; `(None, None, ...)` si no hay evidencia.

    `bilateral = False` ⇒ magnitud de CONTEXTO (ΔAlt⁺, ΔDescanso, ventana H2H): pertenece al
    partido, no a un club, y por tanto se transcribe sin orientarse al favorito.
    """
    if identificador in _FORMATO_INSUMO:
        local, visita = _magnitud_insumo(insumos, identificador)
        clave_visita = _FORMATO_INSUMO[identificador][1]
        return local, visita, clave_visita is not None
    if identificador in _CLAVES_MACRO_STATS:
        local, visita = _magnitud_macro(insumos, identificador)
        return local, visita, True
    if identificador in _CLAVES_H2H_STATS:
        # V27: el agregado es un diferencial FIRMADO del local evaluado; el visitante lo ve opuesto.
        clave, _nota = _CLAVES_H2H_STATS[identificador]
        diferencia = _entero_firmado((h2h_stats or {}).get(clave))
        if diferencia is None:
            return None, None, True
        return float(diferencia), float(-diferencia), True
    return None, None, True


def _distribuciones_vigentes(sesion: Any) -> Dict[str, SovereignDistribution]:
    """Una fila vigente por partido: la ÚLTIMA leída gana (regla idéntica a `_soberanas_por_id`)."""
    vigentes: Dict[str, SovereignDistribution] = {}
    for fila in sesion.query(SovereignDistribution).all():
        vigentes[str(fila.match_id)] = fila
    return vigentes


def _indice_h2h_stats(sesion: Any) -> Dict[str, Dict[str, Any]]:
    """`h2h_stats` del snapshot MÁS RECIENTE por partido (fuente de V27, [LN-QBE-105]).

    Se toma el primer snapshot que declare las estadísticas del partido: la consulta está
    ordenada por `updated_at` descendente, de modo que un snapshot viejo jamás pisa al nuevo.
    """
    indice: Dict[str, Dict[str, Any]] = {}
    consulta = sesion.query(FixtureSnapshot).order_by(
        FixtureSnapshot.updated_at.desc(), FixtureSnapshot.id.desc()
    )
    for snapshot in consulta.all():
        partidos = snapshot.matches_json or []
        if isinstance(partidos, str):
            try:
                partidos = json.loads(partidos)
            except ValueError:
                continue
        if not isinstance(partidos, list):
            continue
        for entrada in partidos:
            if not isinstance(entrada, dict):
                continue
            clave = str(entrada.get("id_partido") or "")
            if not clave or clave in indice:
                continue
            estadisticas = entrada.get("h2h_stats")
            if isinstance(estadisticas, dict) and estadisticas.get("dif_goles") is not None:
                indice[clave] = estadisticas
    return indice


def _desenlace_real(registro: Optional[Match]) -> Optional[str]:
    """Desenlace fáctico `LOCAL`/`EMPATE`/`VISITANTE` desde el marcador; sin marcador ⇒ `None`."""
    if registro is None:
        return None
    local = _numero(getattr(registro, "score_home", None))
    visita = _numero(getattr(registro, "score_away", None))
    if local is None or visita is None:
        return None
    if local > visita:
        return "LOCAL"
    if visita > local:
        return "VISITANTE"
    return "EMPATE"


def _jornada_de(registro: Optional[Match], match_id: str) -> int:
    """Jornada canónica: `matchday_num` y, en su ausencia, el segmento `-J<n>-` del identificador."""
    if registro is not None:
        numero = _numero(getattr(registro, "matchday_num", None))
        if numero is not None:
            return int(numero)
    for segmento in str(match_id).split("-"):
        if segmento.upper().startswith("J") and segmento[1:].isdigit():
            return int(segmento[1:])
    return 0


def _clasificar(desenlace: Optional[str], orden: Dict[str, Any]) -> Optional[str]:
    """Clase fiduciaria: `r_max` → P_MAX, `r_mid` → P_MID, `r_low` → P_LOW ([LN-QBE-124])."""
    if desenlace is None:
        return None
    if desenlace == orden["r_max"]:
        return CLASE_PMAX
    if desenlace == orden["r_mid"]:
        return CLASE_PMID
    return CLASE_PLOW


def _fila_arquetipo(
    match_id: str,
    registro: Optional[Match],
    distribucion: SovereignDistribution,
    h2h_stats: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Fila completa del arquetipo: clase, orden fiduciario y vector de magnitudes orientado."""
    traza = distribucion.audit_trace_json if isinstance(distribucion.audit_trace_json, dict) else {}
    insumos = traza.get("insumos_factivados")
    if not isinstance(insumos, dict):
        insumos = {}

    p_local = _numero(getattr(distribucion, "p_local", None))
    p_empate = _numero(getattr(distribucion, "p_empate", None))
    p_visita = _numero(getattr(distribucion, "p_visitante", None))
    if p_local is None or p_empate is None or p_visita is None:
        logger.debug("Partido %s sin trío soberano completo: excluido del arquetipo.", match_id)
        return None

    desenlace = _desenlace_real(registro)
    if desenlace is None:
        logger.debug("Partido %s sin marcador fáctico: excluido del arquetipo.", match_id)
        return None

    delta_alt = _numero(insumos.get("delta_alt_metros")) or 0.0
    orden = resolver_orden_fiduciario_con_indiferencia(p_local, p_empate, p_visita, delta_alt=delta_alt)
    clase = _clasificar(desenlace, orden)
    if clase is None:
        return None

    favorito = "LOCAL" if orden["r_max"] == "LOCAL" else "VISITANTE"
    vector: Dict[str, Optional[float]] = {}
    for identificador in DIMENSIONES_ESTRUCTURALES:
        local, visita, bilateral = _par_magnitudes(insumos, h2h_stats, identificador)
        # Orientación: la magnitud bilateral se lee del FAVORITO; la contextual (no bilateral)
        # describe al partido y se transcribe tal cual, sin perderla cuando el favorito es visita.
        if not bilateral or favorito == "LOCAL":
            vector[identificador] = local
        else:
            vector[identificador] = visita

    lambda_local = _numero(getattr(distribucion, "lambda_home", None))
    lambda_visita = _numero(getattr(distribucion, "lambda_away", None))
    delta_eta = (
        math.log(lambda_local / lambda_visita)
        if lambda_local is not None and lambda_visita is not None and lambda_local > 0.0 and lambda_visita > 0.0
        else None
    )

    vector["P1_PRIMA"] = p_local
    vector["PX_PRIMA"] = p_empate
    vector["P2_PRIMA"] = p_visita
    vector["P_MAX_PRIMA"] = orden["p_max_val"]
    vector["P_MID_PRIMA"] = orden["p_mid_val"]
    vector["DELTA_ETA"] = delta_eta
    vector["DELTA_EPIST"] = _numero(getattr(distribucion, "epistemic_delta", None))

    return {
        "match_id": match_id,
        "jornada": _jornada_de(registro, match_id),
        "desenlace": desenlace,
        "favorito": favorito,
        "clase": clase,
        "rescate_indiferencia": bool(orden["rescate_indiferencia"]),
        "separacion_mid_low": orden["separacion_mid_low"],
        "vector": vector,
    }


def _particion(filas: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Partición ternaria + distribución por jornada (la suma debe reconstruir el total)."""
    conteo = {clase: 0 for clase in CLASES}
    por_jornada: Dict[str, Dict[int, int]] = {clase: {} for clase in CLASES}
    rescates = 0
    for fila in filas:
        clase = fila["clase"]
        conteo[clase] = conteo.get(clase, 0) + 1
        jornada = int(fila["jornada"])
        por_jornada[clase][jornada] = por_jornada[clase].get(jornada, 0) + 1
        if fila["rescate_indiferencia"]:
            rescates += 1
    return {
        "n_aciertos_pmax": conteo[CLASE_PMAX],
        "n_rescates_pmid": conteo[CLASE_PMID],
        "n_rupturas_plow": conteo[CLASE_PLOW],
        "n_total": len(filas),
        "n_rescates_banda": rescates,
        "por_jornada": por_jornada,
    }


def _cobertura(
    filas: Sequence[Dict[str, Any]], dimensiones: Sequence[str]
) -> Dict[str, Dict[str, Any]]:
    """Celdas presentes por dimensión (cero imputación: `None` no cuenta como evidencia)."""
    total = len(filas)
    cobertura: Dict[str, Dict[str, Any]] = {}
    for dimension in dimensiones:
        presentes = sum(1 for fila in filas if _numero(fila["vector"].get(dimension)) is not None)
        cobertura[dimension] = {
            "nombre": NOMBRES_DIMENSION.get(dimension, dimension),
            "bloque": BLOQUE_ESTRUCTURAL if dimension in DIMENSIONES_ESTRUCTURALES else BLOQUE_METAESTOCASTICO,
            "n": presentes,
            "pct": round(100.0 * presentes / total, 2) if total else 0.0,
        }
    return cobertura


def _reglas_veto_sugeridas(
    ranking: Sequence[Dict[str, Any]], contraste: Dict[str, Optional[float]]
) -> List[Dict[str, Any]]:
    """Celdas cuyo contraste separa arquetipos con fuerza suficiente para vetar decisiones."""
    sugeridas: List[Dict[str, Any]] = []
    for fila in ranking:
        delta = _numero(contraste.get(fila["id_variable"]))
        if delta is None or abs(delta) < UMBRAL_CONTRASTE_VETO:
            continue
        sugeridas.append(
            {
                "id_variable": fila["id_variable"],
                "nombre_variable": fila["nombre_variable"],
                "delta_ruptura": _redondear(delta),
                "sentido": "P_LOW_SOBRE_P_MAX" if delta > 0.0 else "P_MAX_SOBRE_P_LOW",
                "poder_separador": fila["poder_separador"],
                "f_ratio": fila["f_ratio"],
            }
        )
    sugeridas.sort(key=lambda fila: (-abs(float(fila["delta_ruptura"])), str(fila["id_variable"])))
    return sugeridas


# ═════════════════════════════════════════════════════════════════════════════════════════════
# ORQUESTACIÓN — composición del reporte de arquetipos
# ═════════════════════════════════════════════════════════════════════════════════════════════
def _exportar_json(reporte: Dict[str, Any]) -> Path:
    """Materializa el reporte de laboratorio (única escritura del sandbox, fuera de la bóveda)."""
    RUTA_SALIDA_JSON.parent.mkdir(parents=True, exist_ok=True)
    RUTA_SALIDA_JSON.write_text(
        json.dumps(reporte, ensure_ascii=False, indent=2, sort_keys=False), encoding="utf-8"
    )
    return RUTA_SALIDA_JSON


def ejecutar_extraccion_arquetipos(exportar_json: bool = False) -> Dict[str, Any]:
    """Induce partición, centroides, contraste y Fisher desde la bóveda (read-only, idempotente)."""
    gateway = PersistenceGateway()
    with gateway.read_session() as sesion:
        registros = {str(registro.id): registro for registro in sesion.query(Match).all()}
        distribuciones = _distribuciones_vigentes(sesion)
        indice_h2h = _indice_h2h_stats(sesion)

    filas: List[Dict[str, Any]] = []
    excluidos = 0
    for match_id in sorted(distribuciones):
        fila = _fila_arquetipo(
            match_id, registros.get(match_id), distribuciones[match_id], indice_h2h.get(match_id, {})
        )
        if fila is not None:
            filas.append(fila)
        else:
            excluidos += 1

    reporte: Dict[str, Any] = {
        "ley": "[LN-QBE-126]",
        "arquitectura": "[ARCH-1.4.66]",
        "instrumento": "sandbox_arquetipos_vectores",
        "ruta_json_exportado": None,
    }
    if not filas:
        reporte.update(
            {
                "status": "SIN_MUESTRA",
                "motivo": "La bóveda no publica partidos concluidos con trío soberano y marcador.",
                "total_partidos": 0,
            }
        )
        return reporte

    observadas = [
        dimension
        for dimension in DIMENSIONES
        if any(_numero(fila["vector"].get(dimension)) is not None for fila in filas)
    ]
    matriz = [fila["vector"] for fila in filas]
    matriz_z = estandarizar_matriz(matriz, observadas)
    por_clase = {
        clase: [matriz_z[indice] for indice, fila in enumerate(filas) if fila["clase"] == clase]
        for clase in CLASES
    }
    centroides = {clase: calcular_centroide_zscore(por_clase[clase]) for clase in CLASES}

    # Sólo se publican dimensiones con centroide en LAS TRES clases: comparar arquetipos exige que
    # el vector exista entero (una celda ausente se declara fuera, jamás se imputa con 0).
    completas = [
        dimension for dimension in observadas if all(dimension in centroides[clase] for clase in CLASES)
    ]

    # Dimensión del catálogo sin una sola celda en la muestra: se declara FUERA DE MATRIZ con su
    # causa fáctica (cero imputación). V27 se reintegra sola cuando el snapshot publique `h2h_stats`.
    sin_evidencia: Dict[str, str] = {}
    for dimension in DIMENSIONES_ESTRUCTURALES:
        if dimension in observadas:
            continue
        sin_evidencia[dimension] = (
            "Sin `h2h_stats` en el snapshot vigente (0 celdas): la celda se reintegra en cuanto la "
            "fuente publique el agregado [LN-QBE-105]."
            if dimension == "V27"
            else f"Sin evidencia fáctica en la muestra de {len(filas)} partidos concluidos."
        )

    vector_pmax = {dimension: centroides[CLASE_PMAX][dimension] for dimension in completas}
    vector_pmid = {dimension: centroides[CLASE_PMID][dimension] for dimension in completas}
    vector_plow = {dimension: centroides[CLASE_PLOW][dimension] for dimension in completas}
    contraste = {
        dimension: _redondear(vector_plow[dimension] - vector_pmax[dimension], 9)
        for dimension in completas
    }

    ranking: List[Dict[str, Any]] = []
    for fila_fisher in calcular_fisher_ratio(por_clase):
        identificador = fila_fisher["id_variable"]
        ranking.append(
            {
                "id_variable": identificador,
                "nombre_variable": NOMBRES_DIMENSION.get(identificador, identificador),
                "bloque": (
                    BLOQUE_ESTRUCTURAL
                    if identificador in DIMENSIONES_ESTRUCTURALES
                    else BLOQUE_METAESTOCASTICO
                ),
                **{clave: valor for clave, valor in fila_fisher.items() if clave != "id_variable"},
                "delta_ruptura": contraste.get(identificador),
            }
        )

    reporte.update(
        {
            "status": "EXITO",
            "motivo": "Partición fiduciaria, centroides y Fisher inducidos desde la bóveda real.",
            "total_partidos": len(filas),
            "excluidos_sin_marcador": excluidos,
            "n_dimensiones": len(completas),
            "jornadas": sorted({int(fila["jornada"]) for fila in filas}),
            "particion": _particion(filas),
            "dimensiones": completas,
            "dimensiones_descartadas": [dimension for dimension in DIMENSIONES if dimension not in completas],
            "cobertura": _cobertura(filas, completas),
            "vector_pmax": vector_pmax,
            "vector_pmid": vector_pmid,
            "vector_plow": vector_plow,
            "vector_contraste_ruptura": contraste,
            "ranking_fisher": ranking,
            "reglas_veto_sugeridas": _reglas_veto_sugeridas(ranking, contraste),
            "derivaciones": {
                "regla_particion": (
                    "resolver_orden_fiduciario_con_indiferencia [LN-QBE-124]: r_max → P_MAX, "
                    "r_mid → P_MID, r_low → P_LOW (sin segundo ordenamiento)."
                ),
                "regla_orientacion": (
                    "Toda magnitud se orienta al FAVORITO del trío soberano; el bando rival nunca se "
                    "mezcla con el arquetipo que se desea inducir."
                ),
                "fuente_estructural": (
                    "Celdas que el motor consume (V01 · V06 · V07 · V12 · V13) desde "
                    "`insumos_factivados` [LN-QBE-102] con respaldo [ARCH-1.4.44]; el resto del "
                    "catálogo desde `macro_stats` [LN-QBE-121]; V27 desde `h2h_stats` del snapshot "
                    "vigente [LN-QBE-105]."
                ),
                "fuera_de_matriz": {**EXCLUSIONES, **sin_evidencia},
                "composiciones": {
                    "V24": "penales a favor − penales en contra (magnitud firmada, sin pesos).",
                    "V25": "sólo amarillas por partido: ponderar rojas exigiría un peso no legislado.",
                    "V27": "ΔG del local evaluado; el visitante recibe el diferencial opuesto.",
                },
            },
            "matriz_zscore": [
                {
                    "match_id": fila["match_id"],
                    "jornada": int(fila["jornada"]),
                    "clase": fila["clase"],
                    "desenlace": fila["desenlace"],
                    "favorito": fila["favorito"],
                    "z": matriz_z[indice],
                }
                for indice, fila in enumerate(filas)
            ],
        }
    )

    if exportar_json:
        reporte["ruta_json_exportado"] = str(_exportar_json(reporte))
    return reporte


# ═════════════════════════════════════════════════════════════════════════════════════════════
# TABLERO ASCII — [DBBD-FUNGIBLE] (presentación pura; cero cálculo)
# ═════════════════════════════════════════════════════════════════════════════════════════════
def _linea(caracter: str = "═", ancho: int = ANCHO_TABLERO) -> str:
    return caracter * ancho


def _barra(proporcion: float, ancho: int = 26) -> str:
    """Barra proporcional honesta: satura en [0, 1] y nunca dibuja fuera del marco."""
    llenos = int(round(max(0.0, min(1.0, float(proporcion))) * ancho))
    return "█" * llenos + "·" * (ancho - llenos)


def _formatear_numero(valor: Any, decimales: int = 3, ancho: int = 10) -> str:
    numero = _numero(valor)
    if numero is None:
        return f"{'—':>{ancho}}"
    return f"{numero:>{ancho}.{decimales}f}"


def _bloque_particion(reporte: Dict[str, Any], lineas: List[str]) -> None:
    particion = reporte["particion"]
    total = max(1, int(particion["n_total"]))
    etiquetas = {
        CLASE_PMAX: ("P_max · aciertos", particion["n_aciertos_pmax"]),
        CLASE_PMID: ("P_mid · rescates", particion["n_rescates_pmid"]),
        CLASE_PLOW: ("P_low · rupturas", particion["n_rupturas_plow"]),
    }
    lineas.append("1 · PARTICIÓN FIDUCIARIA [LN-QBE-124]")
    jornadas = reporte["jornadas"]
    rango = f"J{jornadas[0]}–J{jornadas[-1]}" if jornadas else "—"
    lineas.append(f"   {particion['n_total']} partidos concluidos ({rango}) · suma ternaria exacta")
    for clase in CLASES:
        texto, cuantos = etiquetas[clase]
        proporcion = cuantos / total
        lineas.append(
            f"   {texto:<18}{cuantos:>4}  {_barra(proporcion)} {proporcion * 100:>5.1f}%"
        )
    lineas.append(
        f"   Rescates por banda de indiferencia (ΔAlt⁺ ≥ 1000 m): {particion['n_rescates_banda']}"
    )
    lineas.append("")


def _bloque_matriz(reporte: Dict[str, Any], lineas: List[str]) -> None:
    cobertura = reporte["cobertura"]
    estructurales = [d for d, meta in cobertura.items() if meta["bloque"] == BLOQUE_ESTRUCTURAL]
    metaestocasticas = [d for d, meta in cobertura.items() if meta["bloque"] == BLOQUE_METAESTOCASTICO]
    media = sum(meta["pct"] for meta in cobertura.values()) / len(cobertura) if cobertura else 0.0
    lineas.append("2 · MATRIZ Z-SCORE GLOBAL")
    lineas.append(
        f"   D = {reporte['n_dimensiones']} dimensiones · {len(estructurales)} estructurales + "
        f"{len(metaestocasticas)} metaestocásticas"
    )
    lineas.append(
        f"   Cobertura media {media:.1f}% · celdas ausentes se declaran, jamás se imputan"
    )
    descartadas = reporte["dimensiones_descartadas"]
    lineas.append(
        f"   Dimensiones sin cómputo: {', '.join(descartadas) if descartadas else 'ninguna'} "
        f"· partidos sin marcador: {reporte['excluidos_sin_marcador']}"
    )
    lineas.append("")


def _bloque_centroides(reporte: Dict[str, Any], lineas: List[str], top: int) -> None:
    contraste = reporte["vector_contraste_ruptura"]
    ordenadas = sorted(contraste, key=lambda clave: (-abs(float(contraste[clave])), clave))[:top]
    lineas.append("3 · CENTROIDES Y VECTOR DE CONTRASTE ΔV_Ruptura = V_P_low − V_P_max")
    lineas.append(
        f"   {'dimensión':<46}{'V_P_max':>9}{'V_P_mid':>9}{'V_P_low':>9}{'ΔV_Ruptura':>12}"
    )
    lineas.append("   " + _linea("─", ANCHO_TABLERO - 3))
    for clave in ordenadas:
        nombre = NOMBRES_DIMENSION.get(clave, clave)[:46]
        lineas.append(
            f"   {nombre:<46}"
            f"{_formatear_numero(reporte['vector_pmax'][clave], 3, 9)}"
            f"{_formatear_numero(reporte['vector_pmid'][clave], 3, 9)}"
            f"{_formatear_numero(reporte['vector_plow'][clave], 3, 9)}"
            f"{_formatear_numero(contraste[clave], 3, 12)}"
        )
    lineas.append("")


def _bloque_fisher(reporte: Dict[str, Any], lineas: List[str], top: int) -> None:
    ranking = reporte["ranking_fisher"][:top]
    lineas.append("4 · RANKING DE FISHER (F = SS_entre / SS_dentro, descendente)")
    lineas.append(
        f"   {'#':>2}  {'dimensión':<44}{'F':>9}{'η²':>7}  {'poder':<10}{'ΔV_Ruptura':>11}"
    )
    lineas.append("   " + _linea("─", ANCHO_TABLERO - 3))
    for posicion, fila in enumerate(ranking, start=1):
        nombre = fila["nombre_variable"][:44]
        lineas.append(
            f"   {posicion:>2}  {nombre:<44}"
            f"{_formatear_numero(fila['f_ratio'], 4, 9)}"
            f"{_formatear_numero(fila['eta_cuadrado'], 3, 7)}  "
            f"{fila['poder_separador']:<10}"
            f"{_formatear_numero(fila['delta_ruptura'], 3, 11)}"
        )
    decisivas = sum(1 for fila in reporte["ranking_fisher"] if fila["poder_separador"] == ETIQUETA_DECISIVA)
    moderadas = sum(1 for fila in reporte["ranking_fisher"] if fila["poder_separador"] == ETIQUETA_MODERADA)
    lineas.append(
        f"   Cartera de poder: {decisivas} decisivas · {moderadas} moderadas · "
        f"{len(reporte['ranking_fisher']) - decisivas - moderadas} en ruido"
    )
    lineas.append("")


def _bloque_vetos(reporte: Dict[str, Any], lineas: List[str]) -> None:
    sugeridas = reporte["reglas_veto_sugeridas"]
    lineas.append("5 · REGLAS DE VETO SUGERIDAS (|ΔV_Ruptura| ≥ 0.25σ)")
    if not sugeridas:
        lineas.append("   Sin candidatas: ningún contraste separa arquetipos con fuerza suficiente.")
    for fila in sugeridas[:8]:
        lineas.append(
            f"   · {fila['nombre_variable'][:48]:<48}  {fila['sentido']:<19}"
            f"{_formatear_numero(fila['delta_ruptura'], 3, 9)}"
        )
    lineas.append("")


def _bloque_pureza(reporte: Dict[str, Any], lineas: List[str]) -> None:
    excluidas = reporte["derivaciones"]["fuera_de_matriz"]
    lineas.append("6 · DECLARACIÓN DE PUREZA Y PROCEDENCIA")
    lineas.append("   Read-only: `PersistenceGateway.read_session()` · cero INSERT/UPDATE/DELETE/COMMIT")
    lineas.append(f"   Partición: {reporte['derivaciones']['regla_particion']}")
    lineas.append(f"   Orientación: {reporte['derivaciones']['regla_orientacion']}")
    lineas.append(f"   Fuente: {reporte['derivaciones']['fuente_estructural']}")
    lineas.append(f"   Fuera de matriz ({len(excluidas)}):")
    for clave in sorted(excluidas):
        lineas.append(f"     - {clave}: {excluidas[clave]}")
    if reporte.get("ruta_json_exportado"):
        lineas.append(f"   Reporte exportado: {reporte['ruta_json_exportado']}")
    lineas.append("")


def imprimir_tablero_arquetipos_consola(reporte: Dict[str, Any], top: int = 15) -> None:
    """Tablero ASCII del sandbox (seis bloques). Función de presentación: no calcula nada."""
    lineas: List[str] = [
        _linea(),
        "🧬 SANDBOX DE ARQUETIPOS Y VECTORES · [LN-QBE-126] / [ARCH-1.4.66]",
        "   Inducción de firmas P_max · P_mid · P_low sobre la bóveda real (CLI-FIRST, read-only)",
        _linea(),
        "",
    ]
    if reporte.get("status") != "EXITO":
        lineas.append(f"⛔ STATUS {reporte.get('status')}: {reporte.get('motivo', 'sin motivo declarado')}")
        print("\n".join(lineas))
        return

    _bloque_particion(reporte, lineas)
    _bloque_matriz(reporte, lineas)
    _bloque_centroides(reporte, lineas, max(1, int(top)))
    _bloque_fisher(reporte, lineas, max(1, int(top)))
    _bloque_vetos(reporte, lineas)
    _bloque_pureza(reporte, lineas)
    lineas.append(_linea())
    print("\n".join(lineas))


# ═════════════════════════════════════════════════════════════════════════════════════════════
# CLI — [DBBD-FUNGIBLE]
# ═════════════════════════════════════════════════════════════════════════════════════════════
def _parsear_argumentos(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="sandbox_arquetipos_vectores",
        description=(
            "Sandbox de arquetipos y vectores [LN-QBE-126]: induce la firma estadística de "
            "P_max / P_mid / P_low desde la bóveda real (read-only)."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emite el reporte estructurado (JSON) en vez del tablero ASCII.",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=15,
        help="Dimensiones exhibidas en los rankings de centroides y Fisher (default 15).",
    )
    parser.add_argument(
        "--exportar",
        action="store_true",
        help=f"Materializa el reporte en {RUTA_SALIDA_JSON.relative_to(RAIZ_PROYECTO)}.",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Optional[Sequence[str]] = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (ValueError, OSError):  # consola que no admite reconfiguración: se respeta
            pass
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    argumentos = _parsear_argumentos(argv)
    reporte = ejecutar_extraccion_arquetipos(exportar_json=bool(argumentos.exportar))

    if argumentos.json:
        print(json.dumps(reporte, ensure_ascii=False, indent=2))
    else:
        imprimir_tablero_arquetipos_consola(reporte, top=argumentos.top)

    return 0 if reporte.get("status") == "EXITO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
