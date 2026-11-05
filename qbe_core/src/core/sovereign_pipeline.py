# -*- coding: utf-8 -*-
"""
🏆 Q-BE SOVEREIGN ENGINE — REGISTRO DE VARIABLES, SUFICIENCIA S(I) Y ORQUESTADOR SOBERANO
[VAULT-CORE-005] Generador Soberano Universal de la Distribución del Partido y Traza Forense.
Base de Gobierno: Kybern Framework v12.0 [ARCH-1.3.4] / Tratado Volumen I (Sección 2.13.1, 4.5, 5.20)

Cableado de Capa 4 (Sprint 3 — erradicación de código muerto [H-16]):
* `[LN-QBE-036]` Operador de Contracción Bayesiana de Forma Reciente → `src/core/sovereign/bayesian_form.py`.
  Interviene en `derivar_factores_estructurales` SOLO cuando el registro fáctico publica `form_10p`.
* `[LN-QBE-020-C]` Kernel H2H Empírico en Eje Localía → `src/core/sovereign/h2h_kernel.py`.
  Interviene en `generar_distribucion_soberana` SOLO cuando el registro publica `h2h_matches` no vacío,
  para derivar Δ_epist contra el consenso Poisson paramétrico (Ley Zero-H2H `[LN-QBE-020-B]` si está vacío).
* `[LN-QBE-104]` Fusión Convexa del Símplex Soberano (Generador A ∪ Generador C) →
  `fusionar_simplex_con_h2h`. Interviene con la MISMA evidencia: P_hib(k) = w_Liga·P_Poisson(k) +
  w_H2H·P_H2H(k) con w_H2H = min(0.25, N·0.05) y Δ_epist(∞) = ‖P_Poisson − P_H2H‖_∞. Sin evidencia
  la fusión degrada a la identidad (w_H2H = 0.0) y Δ_epist(∞) = 0.02 (ignorancia declarada R-1).
* Regla de oro: si el registro NO publica estas fuentes, el motor permanece EXACTAMENTE igual
  (ruta analítica sellada `[LN-QBE-035-B]` y Δ_epist = 0.0). Cero invención, cero fabricación de datos.
"""

import math
from typing import Dict, Any, Tuple, Optional
from pydantic import BaseModel, Field

from src.core.intensity_canonical_loglink import (
    KAPPA_NET,
    InsufficientDataException,
    estimar_intensidades_loglineal,
)
from src.core.distribution_dixon_coles import calcular_matriz_dixon_coles, colapsar_matriz_a_simplex
from src.core.andre_early_payout import calcular_probabilidad_pago_anticipado

# Capa 4 — Sovereign Memory ([ARCH-1.4.26]): módulos puros, sin I/O ni dependencias de src.storage.
from src.core.sovereign.bayesian_form import contraer_factores_forma_bayesiana
from src.core.sovereign.h2h_kernel import calcular_matriz_h2h_empirica, TAU_H2H_DEEP

# [LN-QBE-039] & [ARCH-1.4.33] Contenedor de Factores Latentes Tridimensionales (GSL-3D):
# v1 = residuo log-diferencial de sede (ruta declarada); v2 = proyección ortogonal real
# sobre la matriz causal de 32 variables (docs/LOGIC.md §7.6).
from src.core.sovereign.orthogonal_factor_engine import (
    resolver_factores_latentes_gsl3d,
    resolver_factores_latentes_gsl3d_v2,
)

# [E-50.1 §P-01] `W_SEDE = 0.50` queda ERRADICADO: era una constante legislada sin una sola
# referencia (el peso real del residuo v1 es 1.00). Su reemplazo es la proyección §7.6, que no
# usa pesos libres de sede.

# [LN-QBE-104] Fusión Convexa del Símplex Soberano (Generador A ∪ Generador C).
# Sellado en el nodo legislativo `docs/LOGIC.md` → `docs/DIRGEN_VAULT.md` [VAULT-CORE-005]:
#   w_H2H = min(0.25, N · 0.05)   con N = enfrentamientos directos verificables
#   w_Liga = 1 − w_H2H            (mezcla convexa: P_hib = w_Liga·P_A + w_H2H·P_C)
#   Δ_epist(∞) = max_k |P_A(k) − P_C(k)| ∈ [0, 1]  (norma infinito sobre el símplex Δ²)
# Sin evidencia H2H la fusión degrada a la identidad y la discrepancia se declara en el piso
# fiduciario de ignorancia del Contrato R-1 (`[LN-QBE-070-C]`: delta_epist = 0.02).
PESO_H2H_POR_DUELO = 0.05
PESO_H2H_TOPE = 0.25
DELTA_EPISTEMICO_SIN_EVIDENCIA = 0.02


def _splits_de_sede_publicados(home_split: Any, away_split: Any) -> bool:
    """[LN-QBE-038] Suficiencia mínima de los splits de sede: ambos bloques con PJ >= 3.

    Cualquier carencia (bloque ausente, no diccionario o muestra insuficiente) degrada
    limpiamente a la ruta de Nivel 1 sellada `[LN-QBE-035-B]`, sin inventar registros de sede.
    """
    if not isinstance(home_split, dict) or not isinstance(away_split, dict):
        return False
    if "pj" not in home_split or "pj" not in away_split:
        return False
    try:
        return int(home_split["pj"]) >= 3 and int(away_split["pj"]) >= 3
    except (TypeError, ValueError):
        return False


def _tasa_por_sede(bloque: Dict[str, Any], clave: str, match_id: str, lado: str) -> float:
    """[LN-QBE-038] Tasa por partido de un bloque de sede (GF o GC).

    [E-50.1 §P-01] Sin respaldo silencioso: si el bloque declara sede (PJ ≥ 3) pero no publica
    la clave, se levanta `InsufficientDataException`. Nunca se reconstruye un total a partir
    del promedio general: eso es una imputación, no un dato.
    """
    if clave not in bloque:
        raise InsufficientDataException(match_id, clave, lado)
    pj_sede = max(1, int(bloque["pj"]))
    return float(bloque[clave]) / pj_sede


# [LN-QBE-102] Sellos de procedencia de la evidencia (Regla de Menor Privilegio [ARCH-1.4.43]):
# sólo un demonio de captura en vivo declara EN_VIVO; toda reconstrucción histórica declara
# HISTORICO_RECONSTRUIDO, que es además el default de todos los llamadores existentes.
ORIGEN_CAPTURA_EN_VIVO = "EN_VIVO"
ORIGEN_CAPTURA_HISTORICO = "HISTORICO_RECONSTRUIDO"


def _bloque_factico(raw_match_data: Dict[str, Any], clave: str) -> Dict[str, Any]:
    """[LN-QBE-102] Bloque fáctico del club; `{}` si la fuente no lo publica (cero fabricación)."""
    bloque = raw_match_data.get(clave)
    return bloque if isinstance(bloque, dict) else {}


# [VAULT-CORE-005] [LN-QBE-118] VÍA B — formalización de paridad canónica ([LN-QBE-139]/[LN-QBE-140]).
def _tasa_insumo(bloque: Dict[str, Any], clave: str) -> Optional[float]:
    """[ARCH-1.4.41] Tasa canónica = acumulado / PJ; `None` si la fuente no publica el insumo."""
    precomputada = bloque.get(f"{clave}_rate")
    if isinstance(precomputada, (int, float)) and not isinstance(precomputada, bool):
        return round(float(precomputada), 4)
    acumulado = bloque.get(clave)
    if not isinstance(acumulado, (int, float)) or isinstance(acumulado, bool):
        return None
    pj = bloque.get("pj")
    if not isinstance(pj, (int, float)) or isinstance(pj, bool) or float(pj) <= 0.0:
        return None
    return round(float(acumulado) / float(pj), 4)


def _magnitud_insumo(fuente: Dict[str, Any], claves: Tuple[str, ...]) -> Optional[float]:
    """[LN-QBE-102] Primera clave publicada con magnitud legible; jamás una conversión inventada."""
    for clave in claves:
        valor = fuente.get(clave)
        if isinstance(valor, (int, float)) and not isinstance(valor, bool):
            return float(valor)
    return None


def _conteo_h2h(raw_match_data: Dict[str, Any]) -> int:
    """[LN-QBE-102] Ventana H2H publicada: conteo explícito o longitud de la secuencia."""
    for clave in ("h2h_conteo", "h2h_partidos"):
        valor = raw_match_data.get(clave)
        if isinstance(valor, int) and not isinstance(valor, bool):
            return max(0, valor)
    secuencia = raw_match_data.get("h2h_matches")
    return len(secuencia) if isinstance(secuencia, (list, tuple)) else 0


def _sello_opta(raw_match_data: Dict[str, Any], xg_es_real_opta: Optional[bool]) -> bool:
    """[LN-QBE-102] Sello de procedencia Opta: parámetro explícito, flag publicado o `False`."""
    if isinstance(xg_es_real_opta, bool):
        return xg_es_real_opta
    for clave in ("xg_es_real_opta", "es_real_opta", "xg_disponible"):
        valor = raw_match_data.get(clave)
        if isinstance(valor, bool):
            return valor
    return False


def _contexto_efectivo(
    explicito: Optional[float], raw_match_data: Dict[str, Any], clave: str
) -> Optional[float]:
    """[LN-QBE-102] · [E-50.1 §P-01] Parámetro contextual efectivo (clase C-2).

    Si el llamador aporta un valor distinto de `None`/0.0, manda el explícito; si no, el publicado.
    Si no se publica, devuelve `None`: el operador queda **no aplicado** y así viaja en la traza.
    Prohibido devolver `0.0` para significar «no se sabe»: 0.0 es un hecho publicado, no una ausencia.
    """
    if explicito:
        return float(explicito)
    publicado = raw_match_data.get(clave)
    if isinstance(publicado, (int, float)) and not isinstance(publicado, bool):
        return float(publicado)
    return None


# ── [LN-QBE-105] Agregación fáctica de la ventana H2H (V26/V27/V28 del catálogo forense) ──────
SIN_ANTECEDENTES_SEDE = "Sin antecedentes locales"


def _agregar_h2h_stats(h2h_matches: Any) -> Optional[Dict[str, str]]:
    """`[LN-QBE-105]` Agregado fáctico de la ventana H2H desde la perspectiva del local evaluado.

    Emite `record_general` (V26), `dif_goles` (V27) y `record_sede` (V28) sobre las filas
    verificables (`goles_local`/`goles_visita` enteros). Sin duelos ⇒ `None`: la Ley Zero-H2H no
    fabrica un récord 0-0-0 (ausencia de evidencia no es un empate). Sólo `es_local_sede is True`
    acredita la sede evaluada; una fila histórica sin bandera no se cuenta (cero fabricación).
    """
    victorias = empates = derrotas = 0
    diferencia = 0
    visitante_victorias = visitante_empates = visitante_derrotas = 0
    con_sede = 0
    for fila in (h2h_matches or []):
        if not isinstance(fila, dict):
            continue
        try:
            goles_local = int(fila.get("goles_local"))
            goles_visita = int(fila.get("goles_visita"))
        except (TypeError, ValueError):
            continue
        diferencia += goles_local - goles_visita
        if goles_local > goles_visita:
            victorias += 1
        elif goles_local == goles_visita:
            empates += 1
        else:
            derrotas += 1
        if fila.get("es_local_sede") is not True:
            continue
        con_sede += 1
        if goles_visita > goles_local:
            visitante_victorias += 1
        elif goles_visita == goles_local:
            visitante_empates += 1
        else:
            visitante_derrotas += 1

    if victorias + empates + derrotas == 0:
        return None
    return {
        "record_general": f"{victorias}V - {empates}E - {derrotas}D",
        "dif_goles": "0" if diferencia == 0 else f"{diferencia:+d}",
        "record_sede": (
            f"{visitante_victorias}V - {visitante_empates}E - {visitante_derrotas}D (Visita)"
            if con_sede
            else SIN_ANTECEDENTES_SEDE
        ),
    }


# ═════════════════════════════════════════════════════════════════════════════════════════════
# [LN-QBE-118] MATERIALIZACIÓN ANIDADA DE LOS CINCO PILARES (Fase 2 · Integración Maestra)
# El generador sellado publica el paquete ANIDADO como PROYECCIÓN PURA de las magnitudes que ya
# consumió: cada sub-bloque declara `status` + `insumos` con el shape de los proveedores de
# `[LN-QBE-117]`. Cero matemática nueva: λ, Dixon-Coles, el operador de André y la fusión
# `[LN-QBE-104]` permanecen bit-idénticas, y las claves planas de `[LN-QBE-102]` conservan
# nombre, unidad y valor (el anidamiento es ADITIVO).
# ═════════════════════════════════════════════════════════════════════════════════════════════
ESTADO_BLOQUE_EXITO = "EXITO"
ESTADO_BLOQUE_PARCIAL = "PARCIAL"
ESTADO_BLOQUE_SIN_EVIDENCIA = "SIN_EVIDENCIA"


def _estado_del_bloque(insumos: Dict[str, Any]) -> str:
    """[LN-QBE-118] Estado de cobertura de un sub-bloque: `None` = magnitud no publicada.

    `EXITO` exige TODAS las magnitudes publicadas; `PARCIAL` al menos una; `SIN_EVIDENCIA`
    ninguna. El estado declara la evidencia: jamás sustituye un `None` por un default.
    """
    publicadas = [valor for valor in insumos.values() if valor is not None]
    if not publicadas:
        return ESTADO_BLOQUE_SIN_EVIDENCIA
    if len(publicadas) < len(insumos):
        return ESTADO_BLOQUE_PARCIAL
    return ESTADO_BLOQUE_EXITO


def _sub_bloque(nombre: str, insumos: Dict[str, Any]) -> Dict[str, Any]:
    """[LN-QBE-118] Sub-bloque con el shape legislado `{bloque, status, insumos}`."""
    return {"bloque": nombre, "status": _estado_del_bloque(insumos), "insumos": dict(insumos)}


def _bloque_ataque_defensa(paquete: Dict[str, Any]) -> Dict[str, Any]:
    """[LN-QBE-118] Pilar A/D: tasas canónicas `[ARCH-1.4.41]`, SoT/SoTA y sufrimiento de sede."""
    return _sub_bloque(
        "ataque_defensa",
        {
            "xg_local_rate": paquete.get("xg_local_rate"),
            "xg_visita_rate": paquete.get("xg_visita_rate"),
            "xga_local_rate": paquete.get("xga_local_rate"),
            "xga_visita_rate": paquete.get("xga_visita_rate"),
            "gc_local_rate": paquete.get("gc_local_rate"),
            "gc_visita_rate": paquete.get("gc_visita_rate"),
            "sot_local": paquete.get("sot_local"),
            "sot_visita": paquete.get("sot_visita"),
            "sota_local": paquete.get("sota_local"),
            "sota_visita": paquete.get("sota_visita"),
            "pj_sede_local": paquete.get("pj_sede_local"),
            "pj_sede_visita": paquete.get("pj_sede_visita"),
            "xg_es_real_opta": paquete.get("xg_es_real_opta"),
        },
    )


def _bloque_contexto(paquete: Dict[str, Any], raw_match_data: Dict[str, Any]) -> Dict[str, Any]:
    """[LN-QBE-118] Pilar Contexto: ΔAlt⁺ y ΔDías REALES consumidos por λ `[LN-QBE-109]`.

    Los hechos de plaza viajan en el registro (`altitud_local`/`descanso_local`, publicados por la
    homologación): aquí sólo se declaran. `None` cuando la fuente no los publica.
    """
    return _sub_bloque(
        "contexto",
        {
            "delta_alt_metros": paquete.get("delta_alt_metros"),
            "delta_descanso_dias": paquete.get("delta_descanso_dias"),
            "q_mod_h": paquete.get("q_mod_h"),
            "q_mod_a": paquete.get("q_mod_a"),
            "altitud_local": _magnitud_insumo(raw_match_data, ("altitud_local",)),
            "altitud_visita": _magnitud_insumo(raw_match_data, ("altitud_visita",)),
            "descanso_local": _magnitud_insumo(raw_match_data, ("descanso_local",)),
            "descanso_visita": _magnitud_insumo(raw_match_data, ("descanso_visita",)),
        },
    )


def _bloque_trayectoria(raw_match_data: Dict[str, Any]) -> Dict[str, Any]:
    """[LN-QBE-118] Pilar Trayectoria `[LN-QBE-110]`: ventana 5P y su pendiente.

    La captura de homologación no publica la serie de cinco partidos ⇒ los cuatro insumos quedan
    en `None` (`SIN_EVIDENCIA`). El bloque existe —la ausencia es información veraz— y su ventana
    sintética está prohibida (cero fabricación de una tendencia).
    """
    return _sub_bloque(
        "trayectoria",
        {
            "pts_5p_local": _magnitud_insumo(raw_match_data, ("pts_5p_local",)),
            "pts_5p_visita": _magnitud_insumo(raw_match_data, ("pts_5p_visita",)),
            "pendiente_local": _magnitud_insumo(raw_match_data, ("pendiente_local", "m_local")),
            "pendiente_visita": _magnitud_insumo(raw_match_data, ("pendiente_visita", "m_visita")),
        },
    )


def _bloque_volumen_porteria(paquete: Dict[str, Any]) -> Dict[str, Any]:
    """[LN-QBE-118] Pilar Volumen & Portería `[LN-QBE-111]`: posesión y volumen de disparos."""
    return _sub_bloque(
        "volumen_porteria",
        {
            "poss_local": paquete.get("poss_local"),
            "poss_visita": paquete.get("poss_visita"),
            "sot_local": paquete.get("sot_local"),
            "sot_visita": paquete.get("sot_visita"),
            "sota_local": paquete.get("sota_local"),
            "sota_visita": paquete.get("sota_visita"),
        },
    )


def _bloque_h2h(paquete: Dict[str, Any]) -> Dict[str, Any]:
    """[LN-QBE-118] Pilar Memoria `[LN-QBE-105]`: conteo de la ventana y su agregado fáctico.

    Ley Zero-H2H `[LN-QBE-020-B]`: sin enfrentamientos verificables el bloque se publica
    `SIN_EVIDENCIA` con su motivo, jamás un récord 0-0-0 inventado.
    """
    insumos: Dict[str, Any] = {"h2h_conteo": paquete.get("h2h_conteo")}
    if paquete.get("h2h_stats") is not None:
        insumos["h2h_stats"] = paquete["h2h_stats"]
    bloque = _sub_bloque("h2h", insumos)
    if not int(insumos["h2h_conteo"] or 0):
        bloque["status"] = ESTADO_BLOQUE_SIN_EVIDENCIA
        bloque["motivo"] = (
            "Ley Zero-H2H: la ventana no publicó enfrentamientos directos verificables."
        )
    return bloque


def _paquete_anidado_cinco_pilares(
    paquete: Dict[str, Any], raw_match_data: Dict[str, Any]
) -> Dict[str, Any]:
    """[LN-QBE-118] Proyección ANIDADA de los cinco pilares sobre las claves planas selladas.

    Cada sub-bloque lee EXCLUSIVAMENTE del paquete plano ya construido (más los hechos
    contextuales del registro): no existe una segunda derivación de magnitudes, de modo que el
    aplanador `_MAPA_NIDOS_A_PLANO` de `[ARCH-1.4.55]` re-deriva exactamente el mismo valor plano.
    """
    return {
        "h2h": _bloque_h2h(paquete),
        "contexto": _bloque_contexto(paquete, raw_match_data),
        "trayectoria": _bloque_trayectoria(raw_match_data),
        "volumen_porteria": _bloque_volumen_porteria(paquete),
        "ataque_defensa": _bloque_ataque_defensa(paquete),
    }


def _empaquetar_insumos_factivados(
    raw_match_data: Dict[str, Any],
    delta_alt_metros: Optional[float],
    delta_descanso_dias: Optional[float],
    q_mod_h: Optional[float],
    q_mod_a: Optional[float],
    xg_es_real_opta: Optional[bool] = None,
    h2h_stats: Optional[Dict[str, str]] = None,
    cache_macro_stats: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """[LN-QBE-102] Telemetría fáctica de los insumos consumidos por el generador soberano.

    Cada clave es la magnitud REALMENTE usada por la matemática (tasas canónicas [ARCH-1.4.41],
    splits de sede [LN-QBE-038] y parámetros contextuales efectivos). `None` = no publicado.
    `[LN-QBE-105]` `h2h_stats` se anexa de forma aditiva SÓLO cuando la ventana publicó duelos
    verificables; en su ausencia la clave no existe y la ruta heredada de V26 queda intacta.

    `[LN-QBE-118]` Sobre esas MISMAS magnitudes se anidan los cinco pilares (`h2h`, `contexto`,
    `trayectoria`, `volumen_porteria`, `ataque_defensa`): el anidamiento es una PROYECCIÓN, no un
    cálculo, y ninguna de sus claves alimenta λ, Dixon-Coles, André ni la fusión `[LN-QBE-104]`.

    `[LN-QBE-121]` `cache_macro_stats` (agregado torneal YA resuelto por slug) se anida como
    bloque de EXHIBICIÓN: enciende celdas apagadas del catálogo de 32 variables y jamás sustituye
    una magnitud consumida. Sin artefacto el paquete es byte-idéntico al previo.
    """
    local = _bloque_factico(raw_match_data, "home_team_stats")
    visita = _bloque_factico(raw_match_data, "away_team_stats")
    split_local = _bloque_factico(raw_match_data, "home_split_stats")
    split_visita = _bloque_factico(raw_match_data, "away_split_stats")
    gc_local_rate = _tasa_insumo(local, "gc")
    gc_visita_rate = _tasa_insumo(visita, "gc")
    xga_local_rate = _tasa_insumo(local, "xga") or gc_local_rate
    xga_visita_rate = _tasa_insumo(visita, "xga") or gc_visita_rate
    pj_sede_local = _magnitud_insumo(raw_match_data, ("pj_sede_local",))
    pj_sede_visita = _magnitud_insumo(raw_match_data, ("pj_sede_visita",))
    if pj_sede_local is None:
        pj_sede_local = _magnitud_insumo(split_local, ("pj",))
    if pj_sede_visita is None:
        pj_sede_visita = _magnitud_insumo(split_visita, ("pj",))
    paquete: Dict[str, Any] = {
        "xg_local_rate": _tasa_insumo(local, "xg"),
        "xg_visita_rate": _tasa_insumo(visita, "xg"),
        "xga_local_rate": xga_local_rate,
        "xga_visita_rate": xga_visita_rate,
        "gc_local_rate": gc_local_rate,
        "gc_visita_rate": gc_visita_rate,
        "sot_local": _magnitud_insumo(local, ("sot", "shots_on_target")),
        "sot_visita": _magnitud_insumo(visita, ("sot", "shots_on_target")),
        "sota_local": _magnitud_insumo(local, ("sota", "shots_on_target_against")),
        "sota_visita": _magnitud_insumo(visita, ("sota", "shots_on_target_against")),
        "poss_local": _magnitud_insumo(local, ("possession", "possession_pct", "posesion")),
        "poss_visita": _magnitud_insumo(visita, ("possession", "possession_pct", "posesion")),
        "pj_sede_local": int(pj_sede_local) if pj_sede_local is not None else 0,
        "pj_sede_visita": int(pj_sede_visita) if pj_sede_visita is not None else 0,
        "h2h_conteo": _conteo_h2h(raw_match_data),
        # [E-50.1 §P-02] Operadores C-2: `None` = no publicado ⇒ se declara, no se sustituye por 0.0.
        "q_mod_h": None if q_mod_h is None else round(float(q_mod_h), 4),
        "q_mod_a": None if q_mod_a is None else round(float(q_mod_a), 4),
        "delta_alt_metros": None if delta_alt_metros is None else round(float(delta_alt_metros), 4),
        "delta_descanso_dias": (
            None if delta_descanso_dias is None else round(float(delta_descanso_dias), 4)
        ),
        "xg_es_real_opta": _sello_opta(raw_match_data, xg_es_real_opta),
    }
    if h2h_stats is not None:
        paquete["h2h_stats"] = dict(h2h_stats)
    # [LN-QBE-121] Aduana de Exhibición: el agregado torneal NO alimenta λ; sólo enciende celdas.
    if cache_macro_stats is not None:
        bloque_macro = _bloque_macro_stats(cache_macro_stats)
        if bloque_macro:
            paquete["macro_stats"] = bloque_macro
    # [LN-QBE-118] Los cinco pilares se anidan sobre las MISMAS magnitudes planas (aditivo).
    paquete.update(_paquete_anidado_cinco_pilares(paquete, raw_match_data))
    return paquete


def _bloque_macro_stats(cache_macro_stats: Any) -> Dict[str, Any]:
    """[LN-QBE-121] Bloque `macro_stats` resuelto (sólo lectura; `{}` si no hay artefacto).

    El llamador (orquestador de ingesta) entrega `{"local": {...}, "visita": {...}}` ya resuelto
    por slug: el generador **no** conoce identidades de club. Cada lado se copia tal cual llega
    —cero derivación, cero imputación— y se sella la procedencia torneal.
    """
    if not isinstance(cache_macro_stats, dict):
        return {}
    local = cache_macro_stats.get("local")
    visita = cache_macro_stats.get("visita")
    if not isinstance(local, dict) and not isinstance(visita, dict):
        return {}
    return {
        "procedencia": str(cache_macro_stats.get("procedencia") or "MACRO_TORNEAL"),
        "catalogo_version": str(cache_macro_stats.get("catalogo_version") or ""),
        "local": dict(local) if isinstance(local, dict) else {},
        "visita": dict(visita) if isinstance(visita, dict) else {},
        "cotejo": dict(cache_macro_stats.get("cotejo") or {}),
    }


# [VAULT-CORE-005] [LN-QBE-118] VÍA B — formalización de paridad canónica ([LN-QBE-139]/[LN-QBE-140]).
class StochasticAuditTrace(BaseModel):
    """Traza forense inmutable de la generación de la distribución soberana."""
    match_id: str
    suficiencia_S_I: int = Field(description="1 si satisface datos mínimos, 0 si entra en ignorancia")
    factores_entrada: Dict[str, float]
    intensidades: Dict[str, float]
    distribucion_simplex: Dict[str, float]
    phi_lead2: Dict[str, float]
    matriz_resumen: Dict[str, float]
    # --- Capa 4 (aditivo, cero ruptura de contrato para consumidores previos) ---
    origen_factores: str = Field(
        default="analitico_base",
        description="Procedencia legislada de (A, D): 'analitico_base' [LN-QBE-035-B] o 'bayesiano_10p' [LN-QBE-036].",
    )
    discrepancia_epist: float = Field(
        default=0.0,
        description="Δ_epist ∈ [0,1): distancia de variación total entre el consenso Poisson paramétrico y el Kernel H2H empírico [LN-QBE-020-C].",
    )
    kernel_h2h_empirico: Dict[str, float] = Field(
        default_factory=dict,
        description="Símplex empírico Δ² del Generador C; vacío bajo la Ley Zero-H2H [LN-QBE-020-B] (w_H2H = 0.0, w_Liga = 1.0).",
    )
    # --- [LN-QBE-104] Fusión Convexa del Símplex Soberano (aditivo, cero ruptura) ---
    simplex_poisson: Dict[str, float] = Field(
        default_factory=dict,
        description="Símplex paramétrico PURO del Generador A (pre-fusión) para auditoría de la mezcla [LN-QBE-104].",
    )
    epistemic_delta: float = Field(
        default=DELTA_EPISTEMICO_SIN_EVIDENCIA,
        description="Δ_epist(∞) = max_k |P_A(k) − P_C(k)|, norma infinito sobre el símplex Δ² [LN-QBE-104].",
    )
    # --- [LN-QBE-102] Sello de procedencia y telemetría fáctica (aditivo, cero ruptura) ---
    origen_captura: str = Field(
        default=ORIGEN_CAPTURA_HISTORICO,
        description="Sello de procedencia de la evidencia: 'EN_VIVO' | 'HISTORICO_RECONSTRUIDO' [LN-QBE-102].",
    )
    timestamp_captura: Optional[str] = Field(
        default=None,
        description="Instante ISO-8601 (UTC) de la captura en vivo; `None` si la ruta no lo publica [LN-QBE-102].",
    )
    insumos_factivados: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Telemetría fáctica de los insumos consumidos (tasas canónicas [ARCH-1.4.41], SoT, PJ de sede [LN-QBE-038], ventana H2H) [LN-QBE-102].",
    )
    # --- [E-50.1] / [LN-QBE-039 §7.6] Trazabilidad de la ruta y de la proyección ortogonal ---
    motivo_insuficiencia: Optional[str] = Field(
        default=None,
        description="Motivo declarado cuando S(I)=0 (Ley Fail-Loud [E-50.1 §P-01]).",
    )
    gsl3d: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Traza de GSL-3D v2 por lado: estados por variable, contribuciones, cobertura y suficiencia (§7.6).",
    )


# [VAULT-CORE-005] [LN-QBE-118] VÍA B — formalización de paridad canónica ([LN-QBE-139]/[LN-QBE-140]).
class SovereignDistributionOutput(BaseModel):
    """Contrato formal de salida de la Capa Probabilística Soberana."""
    match_id: str
    p_local: float
    p_empate: float
    p_visitante: float
    lambda_home: float
    lambda_away: float
    phi_lead2_home: float
    phi_lead2_away: float
    es_operable: bool
    audit_trace: StochasticAuditTrace
    # --- Capa 4 (aditivo, espejo de la traza forense para consumidores directos de la Capa 5) ---
    delta_epist: float = Field(
        default=0.0,
        description="Δ_epist ∈ [0,1) publicado al exterior: 0.0 cuando no hay evidencia H2H [LN-QBE-020-B].",
    )
    origen_factores: str = Field(
        default="analitico_base",
        description="'analitico_base' [LN-QBE-035-B] o 'bayesiano_10p' [LN-QBE-036].",
    )
    # [LN-QBE-104] Δ_epist(∞) — discrepancia MÁXIMA por componente entre los dos generadores.
    # Sustituye al ratio λ_max/λ_min como valor PERSISTIDO en `sovereign_distributions.epistemic_delta`:
    # el ratio permanece en `intensidades` (evidencia 3NF sellada [LN-QBE-102]) pero jamás se publica
    # como discrepancia epistémica. Sin evidencia H2H el piso es la ignorancia declarada R-1 (0.02).
    epistemic_delta: float = Field(
        default=DELTA_EPISTEMICO_SIN_EVIDENCIA,
        description="Δ_epist(∞) ∈ [0,1] publicado al exterior: max_k |P_Poisson(k) − P_H2H(k)| [LN-QBE-104].",
    )


# [E-50.1 §P-01] SALIDA POR IGNORANCIA DECLARADA — nunca un λ calculado con un sustituto.
def _salida_por_insuficiencia(
    match_id: str,
    insumos_factivados: Dict[str, Any],
    origen_captura: str,
    timestamp_captura: Optional[str],
    motivo: str,
    gsl3d: Optional[Dict[str, Any]] = None,
) -> SovereignDistributionOutput:
    """[E-50.1 §P-01] Prior fiduciario R-1 con motivo declarado y traza completa.

    No es un `except` que devuelve un número: es la rama legislada de ignorancia, idéntica en
    contrato a la de S(I)=0 y con el motivo publicado para que ningún consumidor confunda
    ignorancia declarada con divergencia de mercado.
    """
    trace_insuf = StochasticAuditTrace(
        match_id=match_id,
        suficiencia_S_I=0,
        factores_entrada={},
        intensidades={"lambda_h": 1.325, "lambda_a": 1.325},
        distribucion_simplex={"p_1": 0.3333, "p_X": 0.3333, "p_2": 0.3334},
        phi_lead2={"phi_h": 0.0, "phi_a": 0.0},
        matriz_resumen={},
        origen_captura=origen_captura,
        timestamp_captura=timestamp_captura,
        insumos_factivados=insumos_factivados,
        motivo_insuficiencia=motivo,
        gsl3d=gsl3d,
    )
    return SovereignDistributionOutput(
        match_id=match_id,
        p_local=0.3333, p_empate=0.3333, p_visitante=0.3334,
        lambda_home=1.325, lambda_away=1.325,
        phi_lead2_home=0.0, phi_lead2_away=0.0,
        es_operable=False,
        audit_trace=trace_insuf,
    )


# [VAULT-CORE-005] [LN-QBE-118] VÍA B — formalización de paridad canónica ([LN-QBE-139]/[LN-QBE-140]).
def evaluar_suficiencia_informativa(raw_match_data: Dict[str, Any]) -> bool:
    """
    [Sección 2.13.1] Evalúa la función indicadora S(I_i) in {0, 1}.
    Requiere al menos 3 partidos jugados por equipo y datos básicos de goles.

    [E-50.1 §P-01] Sin `dict.get(clave, 0)`: la ausencia de `pj` NO es «cero partidos», es
    «no publicado»; en ambos casos S(I)=0, pero el camino es explícito y no un default literal.
    """
    h_data = raw_match_data.get("home_team_stats")
    a_data = raw_match_data.get("away_team_stats")
    if not isinstance(h_data, dict) or not isinstance(a_data, dict):
        return False
    if "pj" not in h_data or "pj" not in a_data:
        return False
    try:
        pj_h = int(h_data["pj"])
        pj_a = int(a_data["pj"])
    except (TypeError, ValueError):
        return False

    if pj_h < 3 or pj_a < 3:
        return False
    return True


def _extraer_bloque_forma_10p(raw_match_data: Dict[str, Any]) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
    """
    Lectura tolerante del bloque fáctico `form_10p` exigido por [LN-QBE-036].

    Formatos admitidos (misma carga semántica; no se inventan campos):
      * Diccionario: {"home": {...}, "away": {...}}
      * Secuencia:   [{...local...}, {...visita...}]
    Campos por equipo: xg_10p, gf_10p, xga_10p, gc_10p, xg_macro, gf_macro, xga_macro, gc_macro
    y el modificador contextual opcional q_mod.

    Devuelve `None` cuando el registro no publica forma reciente: en ese caso la Capa 4 NO
    interviene y el motor continúa por la ruta analítica sellada [LN-QBE-035-B].
    """
    bloque = raw_match_data.get("form_10p")
    if not bloque:
        return None
    if isinstance(bloque, dict):
        home = bloque.get("home")
        away = bloque.get("away")
        if home is None or away is None:
            return None
        return dict(home), dict(away)
    if isinstance(bloque, (list, tuple)) and len(bloque) >= 2:
        return dict(bloque[0]), dict(bloque[1])
    return None


def _campo_obligatorio(
    bloque: Dict[str, Any], clave: str, match_id: str = "", lado: str = ""
) -> float:
    """[E-50.1 §P-01] Lectura de evidencia obligatoria: ausencia ⇒ `InsufficientDataException`.

    Sustituye a `dict.get(clave, <literal>)`. Un `None` explícito de la fuente es ausencia
    declarada, no un cero.
    """
    if clave not in bloque or bloque[clave] is None:
        raise InsufficientDataException(match_id, clave, lado)
    try:
        return float(bloque[clave])
    except (TypeError, ValueError):
        raise InsufficientDataException(match_id, clave, lado)


def _factores_forma_bayesiana(raw_match_data: Dict[str, Any], mu_liga: float) -> Optional[Tuple[float, float, float, float]]:
    """
    [LN-QBE-036] Deriva (A_home, D_away, A_away, D_home) desde la forma reciente (10P) + ancla macro.

    Se consume `a_contraido` (A*) — el factor log-diferencial CONTRAÍDO, pre-amortiguamiento. El
    damping hiperbólico canónico NO se aplica aquí: permanece delegado aguas abajo en
    `estimar_intensidades_loglineal` ([VAULT-CORE-001], κ_net = 0.2500 absoluto), exactamente como en la
    ruta base [LN-QBE-035-B]. Amortiguar dos veces comprimiría dos veces el mismo factor y rompería
    la comparabilidad entre ambas rutas (evidencia en `BayesianFormResult.a_amortiguado`, disponible
    para auditoría).

    Simetría defensiva: el MISMO operador se aplica al par (xGA, GC) y se invierte el signo, conforme
    a la legislación defensiva [LN-QBE-035-B] (D = −ln(tasa / μ_base)). Cero reglas nuevas.
    Devuelve `None` si el registro no publica `form_10p` (Capa 4 inactiva, ruta base intacta).
    """
    bloque = _extraer_bloque_forma_10p(raw_match_data)
    if bloque is None:
        return None
    home, away = bloque
    q_mod_home = 1.0 if "q_mod" not in home or home["q_mod"] is None else float(home["q_mod"])
    q_mod_away = 1.0 if "q_mod" not in away or away["q_mod"] is None else float(away["q_mod"])

    # 1. Ataque Local (A*_home) y Defensa Local (D*_home, signo legislado)
    a_home = contraer_factores_forma_bayesiana(
        _campo_obligatorio(home, "xg_10p"), _campo_obligatorio(home, "gf_10p"),
        _campo_obligatorio(home, "xg_macro"), _campo_obligatorio(home, "gf_macro"),
        mu_liga=mu_liga, q_mod=q_mod_home,
    ).a_contraido
    d_home = -contraer_factores_forma_bayesiana(
        _campo_obligatorio(home, "xga_10p"), _campo_obligatorio(home, "gc_10p"),
        _campo_obligatorio(home, "xga_macro"), _campo_obligatorio(home, "gc_macro"),
        mu_liga=mu_liga, q_mod=q_mod_home,
    ).a_contraido

    # 2. Ataque Visita (A*_away) y Defensa Visita (D*_away, signo legislado)
    a_away = contraer_factores_forma_bayesiana(
        _campo_obligatorio(away, "xg_10p"), _campo_obligatorio(away, "gf_10p"),
        _campo_obligatorio(away, "xg_macro"), _campo_obligatorio(away, "gf_macro"),
        mu_liga=mu_liga, q_mod=q_mod_away,
    ).a_contraido
    d_away = -contraer_factores_forma_bayesiana(
        _campo_obligatorio(away, "xga_10p"), _campo_obligatorio(away, "gc_10p"),
        _campo_obligatorio(away, "xga_macro"), _campo_obligatorio(away, "gc_macro"),
        mu_liga=mu_liga, q_mod=q_mod_away,
    ).a_contraido

    return round(a_home, 4), round(d_away, 4), round(a_away, 4), round(d_home, 4)


# [VAULT-CORE-005] [LN-QBE-118] VÍA B — formalización de paridad canónica ([LN-QBE-139]/[LN-QBE-140]).
def _mezcla_opta(bloque: Dict[str, Any], clave: str, tasa_goles: float, pj: int) -> float:
    """[LN-QBE-035-B] Mezcla 0.65·xG + 0.35·goles (CONSTANTS §2), con ausencia DECLARADA.

    [E-50.1 §P-01] Si la fuente no publica xG/xGA, no se sustituye por un literal ni se
    «reconstruye» un ancla inexistente: se usa la tasa de goles sola. Además el resultado es
    idéntico al de la ruta histórica `xg := gf`, porque 0.65·f + 0.35·f ≡ f: cero regresión
    numérica acompañando la erradicación del mock.
    """
    valor = bloque.get(clave)
    if isinstance(valor, (int, float)) and not isinstance(valor, bool) and float(valor) > 0.0:
        return (0.65 * (float(valor) / pj)) + (0.35 * tasa_goles)
    return tasa_goles


# [VAULT-CORE-005] [LN-QBE-118] VÍA B — formalización de paridad canónica ([LN-QBE-139]/[LN-QBE-140]).
def derivar_factores_estructurales(
    raw_match_data: Dict[str, Any], mu_liga: float = 2.65, match_id: str = ""
) -> Tuple[float, float, float, float]:
    """
    [Sección 4.5 y 4.6] Convierte métricas de Nivel 1 en factores log-diferenciales centrados en media cero:
    Retorna: (A_home, D_away, A_away, D_home)

    [E-50.1 §P-01] `pj`, `gf` y `gc` son evidencia C-1 OBLIGATORIA: su ausencia levanta
    `InsufficientDataException(match_id, clave, lado)`. Prohibido `h.get("gf", 10)`.
    """
    h = _bloque_factico(raw_match_data, "home_team_stats")
    a = _bloque_factico(raw_match_data, "away_team_stats")

    pj_h = max(1, int(_campo_obligatorio(h, "pj", match_id, "local")))
    pj_a = max(1, int(_campo_obligatorio(a, "pj", match_id, "visita")))

    gf_h = _campo_obligatorio(h, "gf", match_id, "local")
    gc_h = _campo_obligatorio(h, "gc", match_id, "local")
    gf_a = _campo_obligatorio(a, "gf", match_id, "visita")
    gc_a = _campo_obligatorio(a, "gc", match_id, "visita")

    mu_base_equipo = max(0.5, mu_liga / 2.0)

    # 1. Ataque Local · 2. Defensa Visita · 3. Ataque Visita · 4. Defensa Local
    gf_h_per_game = gf_h / pj_h
    gc_a_per_game = gc_a / pj_a
    gf_a_per_game = gf_a / pj_a
    gc_h_per_game = gc_h / pj_h

    att_h_rate = _mezcla_opta(h, "xg", gf_h_per_game, pj_h)
    def_a_rate = _mezcla_opta(a, "xga", gc_a_per_game, pj_a)
    att_a_rate = _mezcla_opta(a, "xg", gf_a_per_game, pj_a)
    def_h_rate = _mezcla_opta(h, "xga", gc_h_per_game, pj_h)

    A_home = math.log(max(0.2, att_h_rate) / mu_base_equipo)
    D_away = -math.log(max(0.2, def_a_rate) / mu_base_equipo)
    A_away = math.log(max(0.2, att_a_rate) / mu_base_equipo)
    D_home = -math.log(max(0.2, def_h_rate) / mu_base_equipo)

    # 5. [LN-QBE-039] Ruta declarada v1 — residuo ortogonal log-diferencial de sede.
    #    Se conserva como degradación EXPLÍCITA cuando el registro no publica la matriz causal
    #    que exige la proyección §7.6 (GSL-3D v2). No se presenta como ortogonalización.
    home_split = _bloque_factico(raw_match_data, "home_split_stats")
    away_split = _bloque_factico(raw_match_data, "away_split_stats")
    if _splits_de_sede_publicados(home_split, away_split):
        gf_h_gen = gf_h_per_game
        gc_h_gen = gc_h_per_game

        gf_h_sede = _tasa_por_sede(home_split, "gf", match_id, "local")
        gc_h_sede = _tasa_por_sede(home_split, "gc", match_id, "local")

        gsl_local = resolver_factores_latentes_gsl3d(
            A_gen=A_home, D_gen=D_home,
            gf_gen=gf_h_gen, gc_gen=gc_h_gen,
            gf_sede=gf_h_sede, gc_sede=gc_h_sede,
            gamma_base=0.15, es_local=True
        )

        # ALT-I: el residuo de sede se aplica EXCLUSIVAMENTE al anfitrión; el visitante conserva
        # su evaluación estructural basal [LN-QBE-035-B] intacta.
        A_home, D_home = gsl_local.A_star, gsl_local.D_star

    # [SPRINT 3 / H-16] Capa 4 ([LN-QBE-036]): si el registro publica `form_10p`, el operador
    # bayesiano sellado SUSTITUYE de forma gobernada la mezcla analítica base.
    factores_bayesianos = _factores_forma_bayesiana(raw_match_data, mu_liga)
    if factores_bayesianos is not None:
        return factores_bayesianos
    return round(A_home, 4), round(D_away, 4), round(A_away, 4), round(D_home, 4)


def derivar_factores_con_procedencia(
    raw_match_data: Dict[str, Any], mu_liga: float = 2.65, match_id: str = ""
) -> Tuple[Tuple[float, float, float, float], str]:
    """
    Envoltorio trazable de `derivar_factores_estructurales`: publica los factores y su PROCEDENCIA
    legislada ('bayesiano_10p' [LN-QBE-036] o 'analitico_base' [LN-QBE-035-B]) para la traza forense.
    """
    if _extraer_bloque_forma_10p(raw_match_data) is not None:
        return derivar_factores_estructurales(raw_match_data, mu_liga, match_id), "bayesiano_10p"
    return derivar_factores_estructurales(raw_match_data, mu_liga, match_id), "analitico_base"


# [E-50.7][FASE 5.1] EXPOSICIÓN LIMPIA DEL MOTOR GSL-3D v2 (sólo lectura, sin matemática nueva).
def derivar_factores_estructurales_v2(
    matriz_causal: Dict[str, Any]
) -> Optional[Tuple[float, float, float, float, Dict[str, Any]]]:
    """[E-50.7] Factor (A_home, D_away, A_away, D_home) desde el contrato IPO v2 (§7.6).

    Reúne en UNA sola llamada la proyección ortogonal de ambos clubes para consumidores de
    investigación: devuelve `(A_home, D_away, A_away, D_home, gsl3d_traza)` si ambos lados
    satisfacen la cobertura mínima, o `None` si la matriz no publica evidencia suficiente
    (equivale a `S(I)=0`). Cero fabricación: la insuficiencia se declara, no se rellena.
    """
    if not isinstance(matriz_causal, dict):
        raise InsufficientDataException("", "matriz_causal", "partido")
    medias_liga = matriz_causal.get("medias_liga")
    if not isinstance(medias_liga, dict) or not medias_liga:
        raise InsufficientDataException("", "medias_liga", "liga")
    pesos = matriz_causal.get("pesos")
    gsl_local = resolver_factores_latentes_gsl3d_v2(
        matriz_causal.get("local"), matriz_causal.get("vector_local"), medias_liga, pesos=pesos
    )
    gsl_visita = resolver_factores_latentes_gsl3d_v2(
        matriz_causal.get("visita"), matriz_causal.get("vector_visita"), medias_liga, pesos=pesos
    )
    traza = {"local": gsl_local.model_dump(), "visita": gsl_visita.model_dump()}
    if not (gsl_local.suficiente and gsl_visita.suficiente):
        return None
    return (
        gsl_local.A_star,
        gsl_visita.D_star,
        gsl_visita.A_star,
        gsl_local.D_star,
        traza,
    )


# ═══════════════════════════════════════════════════════════════════════════════════════
# [E-50.9][FASE 6] CAPA 1 — SÚPER-SEÑAL (V06 xG · V07 SoT · V12 xGA), SIN GSL-3D, α FIJA
#
# Contrato de entrada V6 (lo construye el laboratorio `scripts/investigacion/fase6_*`):
#   raw_match_data = {
#       "home_team_stats": {"pj", "xg": tasa_xG, "sot": tasa_SoT, "xga": tasa_xGA},
#       "away_team_stats": {…},
#       "medias_liga": {"xg": μ_xG, "sot": μ_SoT, "xga": μ_xGA},   # media de liga por temporada
#   }
# Los factores se pasan DIRECTOS a la ecuación log-lineal; la ligadura α queda FIJA en el punto
# canónico (μ=2.65, γ=0.15 ⇒ α=0.203603): prohibido inyectar plaza/altitud/descanso en α.
# ═══════════════════════════════════════════════════════════════════════════════════════
GAMMA_FIJO_V6 = 0.15


def derivar_factores_super_senal(
    raw_match_data: Dict[str, Any], match_id: str = ""
) -> Tuple[float, float, float, float]:
    """[E-50.9] Factor log-diferencial desde V06/V07 (ataque) y V12 (defensa), sin ortogonalización.

    Normalización log-ratio contra la media de liga sellada (misma filosofía §7.6.3):

        xg_n = (xG + 1)/(μ_xG + 1) · sot_n = (SoT + 1)/(μ_SoT + 1) · xga_n = (xGA + 1)/(μ_xGA + 1)
        A = ln(0.65·xg_n + 0.35·sot_n) · D = −ln(xga_n)
    """
    h = raw_match_data.get("home_team_stats")
    a = raw_match_data.get("away_team_stats")
    medias = raw_match_data.get("medias_liga")
    if not isinstance(h, dict) or not isinstance(a, dict):
        raise InsufficientDataException(match_id, "team_stats", "partido")
    if not isinstance(medias, dict) or not all(clave in medias for clave in ("xg", "sot", "xga")):
        raise InsufficientDataException(match_id, "medias_liga", "liga")

    def _factor(xg: float, sot: float, xga: float) -> Tuple[float, float]:
        xg_n = (float(xg) + 1.0) / (float(medias["xg"]) + 1.0)
        sot_n = (float(sot) + 1.0) / (float(medias["sot"]) + 1.0)
        xga_n = (float(xga) + 1.0) / (float(medias["xga"]) + 1.0)
        ataque = math.log(max(0.2, 0.65 * xg_n + 0.35 * sot_n))
        defensa = -math.log(max(0.2, xga_n))
        return ataque, defensa

    def _tasas(bloque: Dict[str, Any], lado: str) -> Tuple[float, float, float]:
        for clave in ("xg", "sot", "xga"):
            if clave not in bloque or bloque[clave] is None:
                raise InsufficientDataException(match_id, clave, lado)
        return float(bloque["xg"]), float(bloque["sot"]), float(bloque["xga"])

    xg_h, sot_h, xga_h = _tasas(h, "local")
    xg_a, sot_a, xga_a = _tasas(a, "visita")
    A_home, D_home = _factor(xg_h, sot_h, xga_h)
    A_away, D_away = _factor(xg_a, sot_a, xga_a)
    return A_home, D_away, A_away, D_home


def generar_distribucion_v6(
    match_id: str,
    raw_match_data: Dict[str, Any],
    mu_liga: float = 2.65,
    kappa_net: float = KAPPA_NET,
    rho: float = -0.05,
) -> SovereignDistributionOutput:
    """[E-50.9][FASE 6] Generador V6: súper-señal → α fija → λ → Dixon-Coles → André → símplex.

    Cero GSL-3D, cero plaza/altitud/descanso: `α = ln(2.65) − ln(1+e^0.15) = 0.203603` FIJO.
    """
    try:
        A_h, D_a, A_a, D_h = derivar_factores_super_senal(raw_match_data, match_id)
    except InsufficientDataException as error:
        return _salida_por_insuficiencia(
            match_id, {}, ORIGEN_CAPTURA_HISTORICO, None, f"V6:{error.clave}:{error.lado}"
        )

    lambda_h, lambda_a = estimar_intensidades_loglineal(
        A_h, D_a, A_a, D_h,
        mu_liga=mu_liga, gamma_home_base=GAMMA_FIJO_V6,
        home_team_slug=None, delta_alt_metros=None, delta_descanso_dias=None,
        kappa_net=kappa_net,
    )
    matriz_2d = calcular_matriz_dixon_coles(lambda_h, lambda_a, rho=rho)
    p1, px, p2 = colapsar_matriz_a_simplex(matriz_2d)
    phi_h = calcular_probabilidad_pago_anticipado(matriz_2d, es_local=True)
    phi_a = calcular_probabilidad_pago_anticipado(matriz_2d, es_local=False)

    traza = StochasticAuditTrace(
        match_id=match_id,
        suficiencia_S_I=1,
        factores_entrada={"A_home": A_h, "D_away": D_a, "A_away": A_a, "D_home": D_h},
        intensidades={"lambda_home": lambda_h, "lambda_away": lambda_a, "ratio": round(lambda_h / lambda_a, 2)},
        distribucion_simplex={"p_1": p1, "p_X": px, "p_2": p2},
        phi_lead2={"phi_home": phi_h, "phi_away": phi_a},
        matriz_resumen={"0_0": round(matriz_2d[0][0], 4), "1_0": round(matriz_2d[1][0], 4), "1_1": round(matriz_2d[1][1], 4)},
        origen_factores="super_senal",
        origen_captura=ORIGEN_CAPTURA_HISTORICO,
    )
    return SovereignDistributionOutput(
        match_id=match_id,
        p_local=p1, p_empate=px, p_visitante=p2,
        lambda_home=lambda_h, lambda_away=lambda_a,
        phi_lead2_home=phi_h, phi_lead2_away=phi_a,
        es_operable=True,
        audit_trace=traza,
        origen_factores="super_senal",
    )


def derivar_discrepancia_epistemica(
    distribucion_parametrica: Dict[str, float],
    h2h_matches: Optional[Any] = None,
    tau_dias: float = TAU_H2H_DEEP,
    kernel: Optional[Any] = None,
) -> Tuple[float, Dict[str, float]]:
    """
    [LN-QBE-020-C] Δ_epist — discrepancia entre el consenso Poisson paramétrico y el Kernel H2H empírico.

    Métrica legislada: distancia de variación total (media L1) sobre el símplex Δ²
        Δ_epist = ½ · (|p_local − q_local| + |p_empate − q_empate| + |p_visitante − q_visita|) ∈ [0, 1).
    Es invariante ante la permutación de etiquetas, no amplifica ruido y se anula exactamente en la
    coincidencia perfecta (Δ_epist = 0 ⟺ ambos generadores publican el mismo símplex); la frontera de
    cuarentena fiduciaria τ_disp = 0.12 ([LN-QBE-070-B]) se evalúa aguas abajo, no aquí.

    Ley Zero-H2H ([LN-QBE-020-B]): sin enfrentamientos directos ⇒ w_H2H = 0.0, w_Liga = 1.0 y
    Δ_epist = 0.0. El kernel NO se invoca con evidencia vacía (jamás se fabrican partidos sintéticos).

    [ARCH-1.6.13-C] La ventana de memoria es la multianual sellada τ_deep = 540 días: la secuencia
    completa se pondera sin corte artificial por antigüedad (los partidos de 500 a 750 días
    conservan peso efectivo material, impidiendo el colapso falso a Δ_epist = 0.0).

    [LN-QBE-104] `kernel` (aditivo, por defecto `None`) permite INYECTAR la instancia del Generador C
    ya materializada por el orquestador: la fusión convexa y esta discrepancia consumen entonces
    EXACTAMENTE la misma matriz (una sola invocación por partido, cero doble fuente de verdad).
    Con `kernel=None` la resolución es idéntica a la ruta sellada [LN-QBE-020-C].

    Devuelve (Δ_epist, evidencia_del_Generador_C) para la traza forense.
    """
    partidos = list(h2h_matches or [])
    if not partidos:
        return 0.0, {"peso_h2h": 0.0, "peso_liga": 1.0}

    if kernel is None:
        kernel = calcular_matriz_h2h_empirica(partidos, tau_dias=tau_dias)
    delta_epist = 0.5 * (
        abs(float(distribucion_parametrica["p_local"]) - kernel.p_local)
        + abs(float(distribucion_parametrica["p_empate"]) - kernel.p_empate)
        + abs(float(distribucion_parametrica["p_visitante"]) - kernel.p_visita)
    )
    return round(delta_epist, 6), {
        "p_local": round(kernel.p_local, 6),
        "p_empate": round(kernel.p_empate, 6),
        "p_visita": round(kernel.p_visita, 6),
        "peso_total_efectivo": round(kernel.peso_total_efectivo, 6),
    }


def calcular_peso_h2h(n_duelos: int) -> float:
    """
    [LN-QBE-104] Peso convexo del Generador C: w_H2H = min(0.25, N · 0.05).

    N es el número de enfrentamientos directos VERIFICABLES de la ventana sellada. La ley es monótona
    (cada duelo adicional aporta 0.05) y satura en el tope fiduciario 0.25: a partir del quinto duelo
    el kernel empírico NUNCA desplaza más de una cuarta parte del símplex paramétrico `[LN-QBE-035-B]`.
    `N = 0` ⇒ w_H2H = 0.0 (identidad: la mezcla no toca el símplex Poisson).
    """
    try:
        duelos = int(n_duelos or 0)
    except (TypeError, ValueError):
        duelos = 0
    return min(PESO_H2H_TOPE, max(0, duelos) * PESO_H2H_POR_DUELO)


def fusionar_simplex_con_h2h(
    distribucion_parametrica: Dict[str, float],
    kernel: Optional[Any] = None,
    n_duelos: int = 0,
) -> Dict[str, float]:
    """
    [LN-QBE-104] Fusión Convexa del Símplex Soberano (Generador A ∪ Generador C).

    Ley de mezcla sellada en `[VAULT-CORE-005]`:
        P_hib(k) = w_Liga · P_Poisson(k) + w_H2H · P_H2H(k),  w_Liga = 1 − w_H2H,
        w_H2H = min(0.25, N · 0.05).
    Al ser una combinación convexa de dos distribuciones de probabilidad, P_hib habita el mismo símplex
    Δ² (Σ = 1 en aritmética exacta; error de redondeo ≤ 1e-16) y cada componente queda acotada entre
    los dos generadores:  min(P_A, P_C) ≤ P_hib ≤ max(P_A, P_C).

    Δ_epist se publica con la norma infinito sobre Δ² (`[VAULT-CORE-005]`):
        Δ_epist(∞) = max_k |P_A(k) − P_C(k)| ∈ [0, 1].
    Es la discrepancia MÁXIMA por componente — la cota de Kolmogorov —, que acota la variación total
    por arriba (TVD ≤ Δ(∞)) y por tanto conserva el orden de la frontera τ_disp = 0.12 ya legislada.

    Ley Zero-H2H ([LN-QBE-020-B]): sin kernel o con N = 0 la fusión es la IDENTIDAD (w_H2H = 0.0,
    w_Liga = 1.0) y Δ_epist(∞) se declara en el piso de ignorancia del Contrato R-1
    (DELTA_EPISTEMICO_SIN_EVIDENCIA = 0.02), jamás 0.0: ausencia de evidencia no es coincidencia.

    Devuelve el símplex híbrido más su telemetría de mezcla (peso_h2h, peso_liga, delta_epist).
    """
    p_local = float(distribucion_parametrica["p_local"])
    p_empate = float(distribucion_parametrica["p_empate"])
    p_visitante = float(distribucion_parametrica["p_visitante"])

    peso_h2h = calcular_peso_h2h(n_duelos) if kernel is not None else 0.0
    if kernel is None or peso_h2h <= 0.0:
        return {
            "p_local": p_local,
            "p_empate": p_empate,
            "p_visitante": p_visitante,
            "peso_h2h": 0.0,
            "peso_liga": 1.0,
            "delta_epist": DELTA_EPISTEMICO_SIN_EVIDENCIA,
        }

    q_local = float(kernel.p_local)
    q_empate = float(kernel.p_empate)
    q_visita = float(kernel.p_visita)
    peso_liga = 1.0 - peso_h2h

    delta_epist = max(
        abs(p_local - q_local),
        abs(p_empate - q_empate),
        abs(p_visitante - q_visita),
    )
    return {
        "p_local": peso_liga * p_local + peso_h2h * q_local,
        "p_empate": peso_liga * p_empate + peso_h2h * q_empate,
        "p_visitante": peso_liga * p_visitante + peso_h2h * q_visita,
        "peso_h2h": peso_h2h,
        "peso_liga": peso_liga,
        "delta_epist": delta_epist,
    }


# [VAULT-CORE-005] [LN-QBE-118] VÍA B — formalización de paridad canónica ([LN-QBE-139]/[LN-QBE-140]).
def generar_distribucion_soberana(
    match_id: str,
    raw_match_data: Dict[str, Any],
    mu_liga: float = 2.65,
    gamma_home_base: float = 0.15,
    delta_alt_metros: Optional[float] = None,
    delta_descanso_dias: Optional[float] = None,
    q_mod_h: Optional[float] = None,
    q_mod_a: Optional[float] = None,
    rho: float = -0.05,
    origen_captura: str = ORIGEN_CAPTURA_HISTORICO,
    timestamp_captura: Optional[str] = None,
    xg_es_real_opta: Optional[bool] = None,
    cache_macro_stats: Optional[Dict[str, Any]] = None
) -> SovereignDistributionOutput:
    """
    [TRATADO VOLUMEN I] Generador Soberano Universal de la Distribución del Partido.
    Pipeline completo: Datos -> S(I) -> Factores -> Intensidades acotadas -> Dixon-Coles 2D -> André -> Simplex.

    [E-50.1] Los operadores contextuales (`Δalt`, `Δrest`, `q_mod`) son clase C-2: su default es
    `None` («no publicado» ⇒ operador no aplicado y declarado), nunca `0.0`.
    [LN-QBE-039 §7.6] Si el registro publica `matriz_causal`, GSL-3D v2 gobierna (A,D); en su
    ausencia rige la ruta declarada v1/basal, que NO se presenta como ortogonalización.
    """
    # 0. [LN-QBE-102] Contexto fáctico EFECTIVO: el parámetro explícito manda; si no, la magnitud
    #    publicada por el registro; si tampoco, `None` (operador no aplicado).
    delta_alt_efectivo = _contexto_efectivo(delta_alt_metros, raw_match_data, "delta_alt_metros")
    delta_descanso_efectivo = _contexto_efectivo(delta_descanso_dias, raw_match_data, "delta_descanso_dias")
    insumos_factivados = _empaquetar_insumos_factivados(
        raw_match_data, delta_alt_efectivo, delta_descanso_efectivo, q_mod_h, q_mod_a, xg_es_real_opta,
        h2h_stats=_agregar_h2h_stats(raw_match_data.get("h2h_matches")),
        cache_macro_stats=cache_macro_stats,
    )

    # 1. Comprobación de Suficiencia Fáctica S(I_i)
    if not evaluar_suficiencia_informativa(raw_match_data):
        return _salida_por_insuficiencia(
            match_id, insumos_factivados, origen_captura, timestamp_captura,
            "S(I)=0: muestra insuficiente o `pj` no publicado (evidencia C-1).",
        )

    # 2. Derivación de Factores Estructurales
    # 2-a. [LN-QBE-039 §7.6] IPO v2 — proyección ortogonal real sobre la matriz causal.
    matriz_causal = raw_match_data.get("matriz_causal")
    gsl3d_traza: Optional[Dict[str, Any]] = None
    if matriz_causal is not None:
        if not isinstance(matriz_causal, dict):
            raise InsufficientDataException(match_id, "matriz_causal", "partido")
        medias_liga = matriz_causal.get("medias_liga")
        if not isinstance(medias_liga, dict) or not medias_liga:
            raise InsufficientDataException(match_id, "medias_liga", "liga")
        # [E-50.4 §T2] El vector β viaja en el contrato de la matriz y se aplica PRE-GS.
        pesos_gsl = matriz_causal.get("pesos")
        gsl_local = resolver_factores_latentes_gsl3d_v2(
            matriz_causal.get("local"), matriz_causal.get("vector_local"), medias_liga, pesos=pesos_gsl)
        gsl_visita = resolver_factores_latentes_gsl3d_v2(
            matriz_causal.get("visita"), matriz_causal.get("vector_visita"), medias_liga, pesos=pesos_gsl)
        gsl3d_traza = {
            "local": gsl_local.model_dump(),
            "visita": gsl_visita.model_dump(),
        }
        if not (gsl_local.suficiente and gsl_visita.suficiente):
            motivo = "; ".join(m for m in (gsl_local.motivo, gsl_visita.motivo) if m)
            return _salida_por_insuficiencia(
                match_id, insumos_factivados, origen_captura, timestamp_captura,
                f"MATRIZ_CAUSAL_INSUFICIENTE: {motivo}", gsl3d=gsl3d_traza,
            )
        A_h, D_a = gsl_local.A_star, gsl_visita.D_star
        A_a, D_h = gsl_visita.A_star, gsl_local.D_star
        origen_factores = "gsl3d_v2"
    else:
        # 2-b. Ruta declarada (v1 de sede / basal). Sin pretensión de ortogonalización.
        (A_h, D_a, A_a, D_h), origen_factores = derivar_factores_con_procedencia(
            raw_match_data, mu_liga, match_id)

    # 3. Estimación de Intensidades con Ligadura de alpha y Damping tanh
    #    [LN-QBE-038] `home_team_slug` habilita el bono sellado de intimidación de plaza:
    #    la ligadura α se recalibra en caliente sobre la localía efectiva (conservación de masa).
    lh, la = estimar_intensidades_loglineal(
        A_home=A_h, D_away=D_a,
        A_away=A_a, D_home=D_h,
        mu_liga=mu_liga, gamma_home_base=gamma_home_base,
        delta_alt_metros=delta_alt_efectivo,
        delta_descanso_dias=delta_descanso_efectivo,
        q_mod_h=q_mod_h, q_mod_a=q_mod_a,
        home_team_slug=raw_match_data.get("home_team_slug")
    )

    # 4. Construcción de la Matriz Conjunta Dixon-Coles 2D
    matriz_2d = calcular_matriz_dixon_coles(lambda_h=lh, lambda_a=la, rho=rho, k_max=6)

    # 5. Colapso Geométrico al Símplex Delta^2
    p1, pX, p2 = colapsar_matriz_a_simplex(matriz_2d)

    # 6. Evaluación de la Cláusula de Pago Anticipado (Operador de André en O(1))
    phi_h = calcular_probabilidad_pago_anticipado(matriz_2d, es_local=True)
    phi_a = calcular_probabilidad_pago_anticipado(matriz_2d, es_local=False)

    # 7. [LN-QBE-020-C] Δ_epist: consenso Poisson paramétrico vs Kernel H2H empírico.
    #    Ley Zero-H2H ([LN-QBE-020-B]): sin enfrentamientos directos ⇒ w_H2H = 0.0, w_Liga = 1.0
    #    y Δ_epist = 0.0 (el kernel jamás se invoca con evidencia vacía).
    #    [LN-QBE-104] Una SOLA instancia del Generador C alimenta la discrepancia y la fusión convexa:
    #    ambos consumidores leen la MISMA matriz (cero doble invocación, cero doble fuente de verdad).
    partidos_h2h = list(raw_match_data.get("h2h_matches") or [])
    kernel_generador_c = (
        calcular_matriz_h2h_empirica(partidos_h2h, tau_dias=TAU_H2H_DEEP) if partidos_h2h else None
    )
    delta_epist, kernel_h2h = derivar_discrepancia_epistemica(
        {"p_local": p1, "p_empate": pX, "p_visitante": p2},
        partidos_h2h,
        tau_dias=TAU_H2H_DEEP,
        kernel=kernel_generador_c,
    )
    s_poisson = {"p_1": p1, "p_X": pX, "p_2": p2}

    # 7-bis. [LN-QBE-104] Fusión Convexa del Símplex Soberano (Generador A ∪ Generador C).
    #    El símplex PUBLICADO —el que sostiene la Cláusula de André, el despacho de mesas y la
    #    calibración— pasa a ser P_hib = w_Liga·P_A + w_H2H·P_C con w_H2H = min(0.25, N·0.05).
    #    Las intensidades λ NO se tocan: `intensidades` conserva la evidencia 3NF sellada [LN-QBE-102]
    #    (la fusión es una operación sobre el símplex Δ², no sobre el espacio de tasas).
    fusion_h2h = fusionar_simplex_con_h2h(
        {"p_local": p1, "p_empate": pX, "p_visitante": p2},
        kernel=kernel_generador_c,
        n_duelos=len(partidos_h2h),
    )
    p1, pX, p2 = fusion_h2h["p_local"], fusion_h2h["p_empate"], fusion_h2h["p_visitante"]
    # Δ_epist(∞): norma infinito sobre Δ² — la discrepancia MÁXIMA por componente [VAULT-CORE-005].
    delta_epist_infinito = fusion_h2h["delta_epist"]
    if partidos_h2h:
        # Telemetría de mezcla en la MISMA evidencia del Generador C (una sola fuente del peso).
        kernel_h2h = dict(kernel_h2h)
        kernel_h2h["peso_h2h"] = round(fusion_h2h["peso_h2h"], 6)
        kernel_h2h["peso_liga"] = round(fusion_h2h["peso_liga"], 6)

    # 8. Consolidación de Traza Forense
    trace = StochasticAuditTrace(
        match_id=match_id,
        suficiencia_S_I=1,
        factores_entrada={"A_home": A_h, "D_away": D_a, "A_away": A_a, "D_home": D_h},
        intensidades={"lambda_home": lh, "lambda_away": la, "ratio": round(lh / la, 2)},
        distribucion_simplex={"p_1": p1, "p_X": pX, "p_2": p2},
        phi_lead2={"phi_home": phi_h, "phi_away": phi_a},
        matriz_resumen={"0_0": round(matriz_2d[0][0], 4), "1_0": round(matriz_2d[1][0], 4), "1_1": round(matriz_2d[1][1], 4)},
        origen_factores=origen_factores,
        discrepancia_epist=delta_epist,
        kernel_h2h_empirico=kernel_h2h,
        origen_captura=origen_captura,
        timestamp_captura=timestamp_captura,
        insumos_factivados=insumos_factivados,
        # [LN-QBE-104] Símplex paramétrico puro (Generador A) y Δ_epist(∞) de la fusión.
        simplex_poisson=s_poisson,
        epistemic_delta=delta_epist_infinito,
        # [LN-QBE-039 §7.6] Traza de la proyección ortogonal (None si rige la ruta declarada v1).
        gsl3d=gsl3d_traza,
    )

    return SovereignDistributionOutput(
        match_id=match_id,
        p_local=p1, p_empate=pX, p_visitante=p2,
        lambda_home=lh, lambda_away=la,
        phi_lead2_home=phi_h, phi_lead2_away=phi_a,
        es_operable=True,
        audit_trace=trace,
        delta_epist=delta_epist,
        epistemic_delta=delta_epist_infinito,
        origen_factores=origen_factores
    )
