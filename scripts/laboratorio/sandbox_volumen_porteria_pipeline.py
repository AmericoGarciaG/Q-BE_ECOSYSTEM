# -*- coding: utf-8 -*-
"""
[LN-QBE-111] / [ARCH-1.4.50] SANDBOX VOLUMEN & PORTERÍA — PIPELINE AUTÓNOMO CLI-FIRST.

Misión
------
Aislar en consola las dos dimensiones que hoy NO entran a la proyección λ y que por eso nunca se
auditan: el **Volumen y Dominio Territorial** (Dimensión 1, 𝒯_Vol, V01/V02 + `AUX_*`) y el **Rendimiento de
Guardametas** (Dimensión 4, 𝒯_Por, V17/V18/V19). Ejecuta la cadena REAL —corte N−1 de la 3NF + caché
Opta congelada → celdas bipartitas → residuo de volumen ortogonal → tablero ASCII— sin FastAPI,
sin DOM y sin Playwright.

Régimen: `[HÍBRIDO DUAL-TRACK]`
* `[DIRGEN-STRICT]`: el Factor de Control de Cancha NO se reimplementa; se invoca VERBATIM
  `SyntheticMetricsEngine._compute_fcf` (`[LN-QBE-030]`, `src/core/metrics.py`) y el residuo
  ortogonal se define como `FCF − 1.0` dentro de las cotas garantizadas por los clamps inmutables
  `FCF_MIN = 0.65` / `FCF_MAX = 1.35` (`[LN-QBE-039]`).
* `[DBBD-FUNGIBLE]`: composición del corte, CLI (`--partido` / `--jornada` / `--temporada` /
  `--json`), tablero y semáforos.

Axiomas operativos
------------------
1. **Sólo lectura:** `PersistenceGateway.read_session()` y `json.load` del corpus congelado.
   Prohibido escribir en `data/qbe_database.db`; prohibido abrir red.
2. **Futuro-ceguera (N−1):** el corte de cada club son los partidos con `matchday_num < N` en
   estado terminal. El fixture evaluado jamás alimenta su propia acumulación.
3. **Cobertura íntegra:** si a UN partido del corte le falta posesión, SoT o SoTA, ese club-corte
   NO publica la variable. Jamás se mezclan fuentes ni se inventan cifras `[GOVERNANCE-01]`.
4. **Cero conversión inventada:** una fila de `match_telemetry` creada con los defaults del esquema
   (`sot = 0.0`, `sota = 0.0`, `possession_pct = 50.0`) NO es evidencia: se declara ausencia.
5. **Bipartita simétrica:** cada celda V0x publica `local` y `visita` independientes; una variable es
   `EVALUADO` sólo si AMBOS clubes publican magnitud real, y `SIN EVIDENCIA (FASE 6)` en caso
   contrario — jamás un cero ficticio.
6. **El residuo es diagnóstico:** `v_Vol⊥` NO se reinyecta a λ; el motor sellado ya consume la señal
   directora `xG` (`[VAULT-CORE-001/005]` no se tocan).
7. **Contrato tri-estado (varianza `VAR-2026-LAB5-EVIDENCIA`):** V01 y V18 certifican `EVALUADO` con
   evidencia fáctica o degradan a `SIN EVIDENCIA (FASE 6)` publicando la cobertura `cubiertos/total`
   de ambos cortes.

Uso:
    python -m scripts.laboratorio.sandbox_volumen_porteria_pipeline --partido LIGAMX-J11-07
    python -m scripts.laboratorio.sandbox_volumen_porteria_pipeline --jornada 11
    python -m scripts.laboratorio.sandbox_volumen_porteria_pipeline --partido LIGAMX-J11-07 --json
    python -m scripts.laboratorio.sandbox_volumen_porteria_pipeline --jornada 11 --temporada 2026
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy import or_, select

# ── Plano sellado (cero reimplementación del FCF) ──────────────────────────────────────────────
from src.core.metrics import SyntheticMetricsEngine
from src.observatory.core.factor_attribution import derivar_taxonomia
from src.storage.gateway import PersistenceGateway
from src.storage.models import FixtureSnapshot, Match, MatchTelemetry

logger = logging.getLogger("SandboxVolumenPorteria")

# ── Constantes legisladas y de presentación ────────────────────────────────────────────────────
RUTA_CACHE_OPTA_PLANTILLA = os.path.join("data", "cache_optaxg_liga_mx_{temporada}.json")
TEMPORADA_DEFAULT = "2026"

ESTADO_EVALUADO = "EVALUADO"
ESTADO_SIN_EVIDENCIA = "SIN EVIDENCIA"
ESTADOS_TERMINALES = ("FINALIZADO", "FINISHED")

NIVEL_VERDE = "VERDE"
NIVEL_AMARILLO = "AMARILLO"
NIVEL_NEUTRAL = "NEUTRAL"
GLIFO = {
    NIVEL_VERDE: "🟢", NIVEL_AMARILLO: "🟡", NIVEL_NEUTRAL: "⚪",
    ESTADO_EVALUADO: "🟢", ESTADO_SIN_EVIDENCIA: "⚪",
}
ANCHO_TABLERO = 94
NOTA_FASE_6 = "SIN EVIDENCIA (FASE 6)"

# Clamps inmutables del plano sellado [LN-QBE-030] — sólo se LEEN, jamás se redefinen.
FCF_MIN = SyntheticMetricsEngine.FCF_MIN
FCF_MAX = SyntheticMetricsEngine.FCF_MAX
COTA_RESIDUO = (round(FCF_MIN - 1.0, 4), round(FCF_MAX - 1.0, 4))

# Defaults del esquema ORM: una fila así NO es evidencia (cero conversión inventada).
_POSS_DEFAULT = 50.0
_SOT_DEFAULT = 0.0
_SOTA_DEFAULT = 0.0

# ── Taxonomía bipartita de las dimensiones ([LN-QBE-122] · 𝒯_Vol / 𝒯_Por) ─────────────────────
# [LN-QBE-122] NOMBRE y ORDEN vienen del catálogo único `[LN-QBE-120]`; aquí sólo viven la unidad
# canónica y la nota de procedencia. `AUX_*` = magnitud sin celda (jamás usurpa un `VXX`).
_LOCALES_DIM_1: Dict[str, Tuple[str, str, str]] = {
    "V01": ("Posesión Promedio (%)", "%",
            "Posesión media del corte N−1; fuente: match_telemetry.possession_pct con cobertura íntegra."),
    "V02": ("Toques en Área Rival", "toques/PJ",
            "SIN EVIDENCIA (FASE 6): el sensor congelado no publica toques en área."),
    "AUX_PASES_PROG": ("Pases progresivos completados", "pases/PJ",
                       "SIN EVIDENCIA (FASE 6): el sensor congelado no publica pases progresivos."),
    "AUX_ENTRADAS_UT": ("Entradas al último tercio", "entradas/PJ",
                        "SIN EVIDENCIA (FASE 6): el sensor congelado no publica entradas al último tercio."),
}
_LOCALES_DIM_4: Dict[str, Tuple[str, str, str]] = {
    "V17": ("Goles Evitados", "xGOT−GC/PJ",
            "SIN EVIDENCIA (FASE 6): el sensor congelado no publica xGOT (post-shot)."),
    "V18": ("Save % (Porcentaje de Atajadas)", "%",
            "Save% = 100·(SoTA − GC)/SoTA sobre el corte N−1, cobertura íntegra de SoTA."),
    "V19": ("Salidas/Líbero por Partido", "salidas/PJ",
            "SIN EVIDENCIA (FASE 6): el sensor congelado no publica high claims."),
}
_TAXONOMIA_DIM_1: Tuple[Tuple[str, str, str, str], ...] = derivar_taxonomia("𝒯_Vol", _LOCALES_DIM_1)
_TAXONOMIA_DIM_4: Tuple[Tuple[str, str, str, str], ...] = derivar_taxonomia("𝒯_Por", _LOCALES_DIM_4)

# ── Trazabilidad y contrato ───────────────────────────────────────────────────────────────────
REGLA_CORTE = "matchday_num < N ∧ estado ∈ {FINALIZADO, FINISHED} (futuro-ceguera N−1)"
NODOS_GOBIERNO = ("LN-QBE-111", "ARCH-1.4.50")
VARIANZA_RATIFICADA = "VAR-2026-LAB5-EVIDENCIA"


def _celda(
    identificador: str,
    nombre: str,
    unidad: str,
    local: Optional[float],
    visita: Optional[float],
    nota: str,
    formato: str = "num",
) -> Dict[str, Any]:
    """Celda bipartita homogénea: `EVALUADO` sólo si AMBOS clubes publican magnitud real.

    `formato="pct"` publica la magnitud de presentación con sufijo `%` (contrato del Juez) y replica
    el valor numérico en `local_num`/`visita_num` para el consumo máquina (`--json`).
    """
    evaluada = local is not None and visita is not None
    local_num = round(float(local), 4) if evaluada else None
    visita_num = round(float(visita), 4) if evaluada else None
    if formato == "pct":
        local_pub = f"{local_num:.1f}%" if evaluada else None
        visita_pub = f"{visita_num:.1f}%" if evaluada else None
    else:
        local_pub, visita_pub = local_num, visita_num
    return {
        "id": identificador,
        "variable": nombre,
        "unidad": unidad,
        "local": local_pub,
        "visita": visita_pub,
        "local_num": local_num,
        "visita_num": visita_num,
        "estado": ESTADO_EVALUADO if evaluada else ESTADO_SIN_EVIDENCIA,
        "nota": nota,
    }


def _r(valor: Optional[float], decimales: int = 4) -> Optional[float]:
    """Redondeo seguro de presentación (preserva `None` como ausencia declarada)."""
    return None if valor is None else round(float(valor), decimales)


def _tasa(total: Optional[float], pj: int) -> Optional[float]:
    """Tasa por partido (≈ por 90 min). `None` sin total o sin muestra: cero invención."""
    if total is None or pj <= 0:
        return None
    return float(total) / float(pj)


# ═════════════════════════════════════════════════════════════════════════════════════════════════
# PROTOCOLO DE INGESTA FÁCTICA (caché congelada + telemetría 3NF, todo en SÓLO LECTURA)
# ═════════════════════════════════════════════════════════════════════════════════════════════════
def ruta_cache_opta(temporada: str = TEMPORADA_DEFAULT) -> str:
    """Ruta absoluta del artefacto congelado `[ARCH-1.4.39]` para la temporada declarada."""
    return os.path.join(PROJECT_ROOT, RUTA_CACHE_OPTA_PLANTILLA.format(temporada=str(temporada)))


def cargar_cache_opta(temporada: str = TEMPORADA_DEFAULT) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Lee el corpus Opta congelado y publica su procedencia (`fuente`, `generado_at`, cobertura).

    Artefacto ausente o ilegible ⇒ mapa vacío + `disponible = False`: el reporte degrada de forma
    honesta a `SIN EVIDENCIA`. Jamás se fabrica una cifra para tapar la ausencia de feed.
    """
    ruta = ruta_cache_opta(temporada)
    meta: Dict[str, Any] = {
        "temporada": str(temporada),
        "ruta": os.path.relpath(ruta, PROJECT_ROOT).replace(os.sep, "/"),
        "disponible": False,
        "fuente": None,
        "generado_at": None,
        "partidos": 0,
        "error": None,
    }
    if not os.path.exists(ruta):
        meta["error"] = f"Artefacto congelado ausente: {meta['ruta']}"
        return {}, meta
    try:
        with open(ruta, "r", encoding="utf-8") as fh:
            artefacto = json.load(fh)
    except (OSError, ValueError) as exc:
        meta["error"] = f"{type(exc).__name__}: {exc}"
        return {}, meta
    partidos = artefacto.get("partidos") if isinstance(artefacto, dict) else None
    if not isinstance(partidos, dict):
        meta["error"] = "El artefacto no publica el mapa 'partidos'."
        return {}, meta
    meta.update({
        "disponible": True,
        "fuente": artefacto.get("fuente"),
        "generado_at": artefacto.get("generado_at"),
        "partidos": len(partidos),
    })
    return partidos, meta


def _registro_opta(cache: Dict[str, Any], match_id: str, lado: str) -> Dict[str, Any]:
    """Bloque `home` | `away` del partido en el corpus congelado; `{}` si no está publicado."""
    registro = cache.get(match_id)
    if not isinstance(registro, dict):
        return {}
    bloque = registro.get(lado)
    return bloque if isinstance(bloque, dict) else {}


def _magnitud(bloque: Dict[str, Any], clave: str) -> Optional[float]:
    """Magnitud numérica publicada; `None` si la clave no existe (cero conversión inventada)."""
    valor = bloque.get(clave)
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        return float(valor)
    return None


def _partidos_de_club(sesion: Any, slug: str, jornada_corte: int) -> List[Dict[str, Any]]:
    """Corte futuro-ciego N−1: partidos TERMINALES del club con `matchday_num < N`."""
    consulta = (
        select(Match)
        .where(
            Match.matchday_num.isnot(None),
            Match.matchday_num < int(jornada_corte),
            Match.status.in_(ESTADOS_TERMINALES),
            or_(Match.home_team_slug == slug, Match.away_team_slug == slug),
        )
        .order_by(Match.matchday_num, Match.id)
    )
    partidos: List[Dict[str, Any]] = []
    for registro in sesion.execute(consulta).scalars().all():
        es_local = registro.home_team_slug == slug
        goles_favor = registro.score_home if es_local else registro.score_away
        goles_contra = registro.score_away if es_local else registro.score_home
        if goles_favor is None or goles_contra is None:
            logger.warning("[LN-QBE-111] Partido sin marcador terminal: %s", registro.id)
            continue
        partidos.append({
            "match_id": str(registro.id),
            "jornada": int(registro.matchday_num or 0),
            "es_local": bool(es_local),
            "goles_favor": int(goles_favor),
            "goles_contra": int(goles_contra),
        })
    return partidos


def _bloque_sede(partidos: Sequence[Dict[str, Any]], es_local: bool) -> Dict[str, Any]:
    """Split de sede (`pj`, `gf`, `gc`, `pts`) exigido por `[LN-QBE-038]`; `{}` si está vacío."""
    tramo = [p for p in partidos if p["es_local"] is es_local]
    if not tramo:
        return {}
    return {
        "pj": len(tramo),
        "gf": sum(p["goles_favor"] for p in tramo),
        "gc": sum(p["goles_contra"] for p in tramo),
        "pts": sum(
            3 if p["goles_favor"] > p["goles_contra"] else (1 if p["goles_favor"] == p["goles_contra"] else 0)
            for p in tramo
        ),
    }


def _valor_telemetria(fila: Any, atributo: str) -> Optional[float]:
    """Magnitud numérica de una columna de `match_telemetry`; `None` si no está publicada."""
    valor = getattr(fila, atributo, None)
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        return float(valor)
    return None


def _telemetria_de_club(
    sesion: Any, partidos: Sequence[Dict[str, Any]], slug: str
) -> Dict[str, Any]:
    """Agrega posesión/SoT/SoTA desde `match_telemetry` (3NF) con cobertura ÍNTEGRA obligatoria.

    Las tres magnitudes se exigen juntas: la posesión sin el reparto de remates no permite construir
    el FCF (`[LN-QBE-030]`), y el SoTA sin posesión no permite diagnosticar el volumen. Una fila
    creada con los defaults del esquema (`0.0` / `0.0` / `50.0`) no es evidencia y se descarta.
    """
    ids = [p["match_id"] for p in partidos]
    resultado: Dict[str, Any] = {
        "fuente": "match_telemetry",
        "cubiertos": 0,
        "total": len(ids),
        "poss_sum": None,
        "sot_total": None,
        "sota_total": None,
        "faltantes": list(ids),
    }
    if not ids:
        return resultado
    filas = sesion.execute(
        select(MatchTelemetry).where(
            MatchTelemetry.match_id.in_(ids),
            MatchTelemetry.team_slug == slug,
        )
    ).scalars().all()
    indice = {str(fila.match_id): fila for fila in filas}
    validas: Dict[str, Tuple[float, float, float]] = {}
    for identificador in ids:
        fila = indice.get(identificador)
        if fila is None:
            continue
        poss = _valor_telemetria(fila, "possession_pct")
        sot = _valor_telemetria(fila, "sot")
        sota = _valor_telemetria(fila, "sota")
        if poss is None or sot is None or sota is None:
            continue
        if sot == _SOT_DEFAULT and sota == _SOTA_DEFAULT and poss == _POSS_DEFAULT:
            # Defaults del esquema: fila huérfana, NO evidencia fáctica.
            continue
        validas[identificador] = (poss, sot, sota)
    faltantes = [identificador for identificador in ids if identificador not in validas]
    resultado["cubiertos"] = len(validas)
    resultado["faltantes"] = faltantes
    if faltantes or not validas:
        # Cobertura incompleta ⇒ NO se publica la tasa: mezclar submuestras sesga el corte.
        return resultado
    resultado["poss_sum"] = round(sum(triple[0] for triple in validas.values()), 4)
    resultado["sot_total"] = round(sum(triple[1] for triple in validas.values()), 4)
    resultado["sota_total"] = round(sum(triple[2] for triple in validas.values()), 4)
    return resultado


def _acumular_club(
    partidos: Sequence[Dict[str, Any]],
    cache: Dict[str, Any],
    telemetria: Dict[str, Any],
) -> Dict[str, Any]:
    """Corte N−1 de un club: goles reales + cobertura ÍNTEGRA de xG/xGA y de posesión/SoT/SoTA.

    Regla dura: `xg_total`/`xga_total` y `poss_pct`/`sot_total`/`sota_total` sólo se publican si
    TODOS los partidos del corte traen la métrica. Una sola ausencia ⇒ `None` (cero imputación).
    """
    pj = len(partidos)
    acumulado: Dict[str, Any] = {
        "pj": pj,
        "gf": sum(p["goles_favor"] for p in partidos),
        "gc": sum(p["goles_contra"] for p in partidos),
        "pts": sum(
            3 if p["goles_favor"] > p["goles_contra"] else (1 if p["goles_favor"] == p["goles_contra"] else 0)
            for p in partidos
        ),
        "xg_total": None,
        "xga_total": None,
        "cobertura_xg": {"cubiertos": 0, "total": pj, "faltantes": []},
        "poss_pct": None,
        "sot_total": telemetria.get("sot_total"),
        "sota_total": telemetria.get("sota_total"),
        "cobertura_telemetria": {
            "cubiertos": int(telemetria.get("cubiertos") or 0),
            "total": int(telemetria.get("total") or pj),
            "faltantes": list(telemetria.get("faltantes") or []),
        },
        "partidos": [dict(p) for p in partidos],
    }
    cubiertos = 0
    faltantes: List[str] = []
    xg_suma = 0.0
    xga_suma = 0.0
    for partido in partidos:
        lado = "home" if partido["es_local"] else "away"
        bloque = _registro_opta(cache, partido["match_id"], lado)
        xg = _magnitud(bloque, "xg")
        xga = _magnitud(bloque, "xga")
        if xg is None or xga is None:
            faltantes.append(partido["match_id"])
            continue
        cubiertos += 1
        xg_suma += xg
        xga_suma += xga
    if pj > 0 and cubiertos == pj:
        acumulado["xg_total"] = round(xg_suma, 4)
        acumulado["xga_total"] = round(xga_suma, 4)
    acumulado["cobertura_xg"] = {"cubiertos": cubiertos, "total": pj, "faltantes": faltantes}
    poss_sum = telemetria.get("poss_sum")
    if poss_sum is not None and pj > 0:
        # Posesión media del corte: suma de porcentajes por partido / PJ.
        acumulado["poss_pct"] = round(float(poss_sum) / float(pj), 4)
    return acumulado


# ═════════════════════════════════════════════════════════════════════════════════════════════════
# ARITMÉTICA DE LA DIMENSIÓN 1 & 4 (pura, sin I/O — auditable por The Shield en aislamiento)
# ═════════════════════════════════════════════════════════════════════════════════════════════════
def calcular_delta_posesion(poss_local: float, poss_visita: float) -> float:
    """ΔPosición = `Poss_local − Poss_visita`, acotado por construcción a [−100, +100].

    Identidad bipartita exacta: con 56.4 % vs 43.6 % el diferencial es `+12.8` puntos porcentuales.
    Valores fuera de `[0, 100]` son un error de contrato (la posesión es un porcentaje) y se rechazan
    en voz alta: nunca se silencia un dato corrupto.
    """
    for nombre, valor in (("poss_local", poss_local), ("poss_visita", poss_visita)):
        if valor is None:
            raise ValueError(f"ΔPosición requiere {nombre}: la ausencia se declara, no se imputa.")
        numero = float(valor)
        if numero < 0.0 or numero > 100.0:
            raise ValueError(f"ΔPosición fuera de contrato: {nombre}={numero} ∉ [0, 100].")
    return round(float(poss_local) - float(poss_visita), 4)


def calcular_save_percentage(sota: float, gc: float) -> float:
    """Save % = 100·(SoTA − GC)/SoTA, saturado en [0, 100].

    * `SoTA = 0` ⇒ `100.0` (sin remates a puerta no hay nada que atajar; no es un fallo).
    * `GC > SoTA` (autogoles o datos sucios) ⇒ `0.0` por saturación inferior: un porcentaje de
      atajadas negativo no tiene lectura futbolística.
    * Entradas negativas ⇒ `ValueError`: son un error de contrato, no un caso de negocio.
    """
    sota_num = float(sota)
    gc_num = float(gc)
    if sota_num < 0.0 or gc_num < 0.0:
        raise ValueError(f"Save% requiere magnitudes no negativas: SoTA={sota_num}, GC={gc_num}.")
    if sota_num == 0.0:
        return 100.0
    bruto = 100.0 * (sota_num - gc_num) / sota_num
    return round(max(0.0, min(100.0, bruto)), 4)


def calcular_residuo_volumen_ortogonal(poss_pct: float, sot: float, sota: float) -> float:
    """`v_Vol⊥ = FCF − 1.0` delegando VERBATIM en `SyntheticMetricsEngine._compute_fcf` ([LN-QBE-030]).

    El FCF sellado ya aplica los clamps `[0.65, 1.35]`, por lo que el residuo está garantizado en
    `[−0.35, +0.35]` sin re-clampear localmente: cero margen para divergir del servidor central.
    * `v_Vol⊥ > 0` ⇒ dominio territorial CONVERTIDO en peligro (volumen eficiente).
    * `v_Vol⊥ < 0` ⇒ presión ESTÉRIL: se domina el balón sin traducirlo en remates a puerta.
    """
    poss_num = float(poss_pct)
    if poss_num < 0.0 or poss_num > 100.0:
        raise ValueError(f"FCF fuera de contrato: poss_pct={poss_num} ∉ [0, 100].")
    if float(sot) < 0.0 or float(sota) < 0.0:
        raise ValueError(f"FCF requiere SoT/SoTA no negativos: SoT={sot}, SoTA={sota}.")
    fcf = SyntheticMetricsEngine._compute_fcf(poss_num, float(sot), float(sota))
    return round(float(fcf) - 1.0, 6)


def _lectura_residuo(valor: Optional[float]) -> str:
    """Traducción forense del residuo ortogonal a lenguaje de cuerpo técnico."""
    if valor is None:
        return NOTA_FASE_6
    if valor >= 0.05:
        return "DOMINIO CONVERTIDO"
    if valor <= -0.05:
        return "PRESIÓN ESTÉRIL"
    return "NEUTRAL TERRITORIAL"


# ═════════════════════════════════════════════════════════════════════════════════════════════════
# CONSTRUCCIÓN DE LAS DIMENSIONES 𝒯_Vol (DIM 1) y 𝒯_Gk (DIM 4)
# ═════════════════════════════════════════════════════════════════════════════════════════════════
def _nota_cobertura(
    acum_local: Dict[str, Any], acum_visita: Dict[str, Any], sujeto: str
) -> str:
    """Nota de degradación con la cobertura explícita `cubiertos/total` de AMBOS cortes."""
    cob_local = acum_local.get("cobertura_telemetria") or {}
    cob_visita = acum_visita.get("cobertura_telemetria") or {}
    return (
        f"{NOTA_FASE_6}: `{sujeto}` cubre "
        f"{int(cob_local.get('cubiertos') or 0)}/{int(cob_local.get('total') or acum_local.get('pj') or 0)} "
        f"partidos del corte local y "
        f"{int(cob_visita.get('cubiertos') or 0)}/{int(cob_visita.get('total') or acum_visita.get('pj') or 0)} "
        f"del corte visita. Cero imputación [GOVERNANCE-01]."
    )


def _dimension_volumen(
    acum_local: Dict[str, Any], acum_visita: Dict[str, Any]
) -> Dict[str, Dict[str, Any]]:
    """𝒯_Vol · DIM 1 (taxonomía `[LN-QBE-122]`): sólo `V01` tiene feed en esta fase del corpus."""
    nota_v01 = _LOCALES_DIM_1["V01"][2]
    if acum_local["poss_pct"] is None or acum_visita["poss_pct"] is None:
        nota_v01 = _nota_cobertura(acum_local, acum_visita, "match_telemetry.possession_pct")
    celdas: Dict[str, Dict[str, Any]] = {}
    for identificador, nombre, unidad, nota in _TAXONOMIA_DIM_1:
        if identificador == "V01":
            celdas["V01"] = _celda(
                "V01", nombre, unidad,
                acum_local["poss_pct"], acum_visita["poss_pct"], nota_v01, formato="pct",
            )
        else:
            celdas[identificador] = _celda(identificador, nombre, unidad, None, None, nota)
    return celdas


def _save_de_corte(acumulado: Dict[str, Any]) -> Optional[float]:
    """Save % del corte N−1; `None` si el club-corte no publica SoTA (ausencia declarada)."""
    sota = acumulado.get("sota_total")
    if sota is None or int(acumulado.get("pj") or 0) <= 0:
        return None
    return calcular_save_percentage(float(sota), float(acumulado.get("gc") or 0.0))


def _dimension_porteria(
    acum_local: Dict[str, Any], acum_visita: Dict[str, Any]
) -> Dict[str, Dict[str, Any]]:
    """𝒯_Por · DIM 4 (taxonomía `[LN-QBE-122]`): sólo `V18` tiene feed (Save % sobre SoTA)."""
    save_local = _save_de_corte(acum_local)
    save_visita = _save_de_corte(acum_visita)
    nota_v18 = _LOCALES_DIM_4["V18"][2]
    if save_local is None or save_visita is None:
        nota_v18 = _nota_cobertura(acum_local, acum_visita, "match_telemetry.sota")
    celdas: Dict[str, Dict[str, Any]] = {}
    for identificador, nombre, unidad, nota in _TAXONOMIA_DIM_4:
        if identificador == "V18":
            celdas[identificador] = _celda(
                identificador, nombre, unidad, save_local, save_visita, nota_v18, formato="pct"
            )
        else:
            celdas[identificador] = _celda(identificador, nombre, unidad, None, None, nota)
    return celdas


def _lado_residuo(acumulado: Dict[str, Any], etiqueta: str) -> Dict[str, Any]:
    """Un club-corte del bloque ortogonal: insumos → FCF sellado → `v_Vol⊥` → lectura forense."""
    poss = acumulado.get("poss_pct")
    sot = acumulado.get("sot_total")
    sota = acumulado.get("sota_total")
    bloque: Dict[str, Any] = {
        "etiqueta": etiqueta,
        "poss_pct": _r(poss),
        "sot": _r(sot),
        "sota": _r(sota),
        "fcf": None,
        "residuo": None,
        "lectura": NOTA_FASE_6,
        "nota": None,
    }
    if poss is None or sot is None or sota is None:
        bloque["nota"] = (
            f"{NOTA_FASE_6}: el corte no publica posesión/SoT/SoTA íntegros; "
            "el FCF no se inventa."
        )
        return bloque
    residuo = calcular_residuo_volumen_ortogonal(poss, sot, sota)
    bloque.update({
        "fcf": round(residuo + 1.0, 6),
        "residuo": residuo,
        "lectura": _lectura_residuo(residuo),
    })
    return bloque


def _bloque_residuo(
    acum_local: Dict[str, Any], acum_visita: Dict[str, Any]
) -> Dict[str, Any]:
    """Residuo de Volumen Ortogonal: separa el DOMINIO del PELIGRO REAL ([LN-QBE-111])."""
    lado_local = _lado_residuo(acum_local, "LOCAL")
    lado_visita = _lado_residuo(acum_visita, "VISITA")
    if lado_local["residuo"] is None or lado_visita["residuo"] is None:
        delta = None
    else:
        delta = round(lado_local["residuo"] - lado_visita["residuo"], 6)
    return {
        "local": lado_local,
        "visita": lado_visita,
        "delta": delta,
        "lectura_delta": _lectura_residuo(delta),
        "formula": "v_Vol⊥ = FCF − 1.0; FCF = clamp[(Poss/50)·(2·(SoT+1)/(SoT+SoTA+2)), 0.65, 1.35]",
        "delegacion": "SyntheticMetricsEngine._compute_fcf ([LN-QBE-030])",
        "cotas": [COTA_RESIDUO[0], COTA_RESIDUO[1]],
    }


def _bloque_delta(
    acum_local: Dict[str, Any], acum_visita: Dict[str, Any], dim_volumen: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """ΔPosición bipartita con la MISMA fuente que publica V01 (coherencia interna garantizada)."""
    v01 = dim_volumen["V01"]
    poss_local = acum_local.get("poss_pct")
    poss_visita = acum_visita.get("poss_pct")
    bloque: Dict[str, Any] = {
        "valor": None,
        "local": _r(poss_local),
        "visita": _r(poss_visita),
        "lectura": NOTA_FASE_6,
        "nota": None,
        "estado": v01["estado"],
    }
    if poss_local is None or poss_visita is None:
        bloque["nota"] = f"{NOTA_FASE_6}: ΔPosición no computable sin posesión íntegra de ambos cortes."
        return bloque
    valor = calcular_delta_posesion(poss_local, poss_visita)
    if valor >= 5.0:
        lectura = "DOMINIO LOCAL"
    elif valor <= -5.0:
        lectura = "DOMINIO VISITA"
    else:
        lectura = "PARIDAD TERRITORIAL"
    bloque.update({"valor": valor, "lectura": lectura})
    return bloque


# ═════════════════════════════════════════════════════════════════════════════════════════════════
# LOCALIZACIÓN DEL FIXTURE (cartelera 3NF, sólo lectura)
# ═════════════════════════════════════════════════════════════════════════════════════════════════
def _entradas_snapshot(snapshot: Any) -> List[Dict[str, Any]]:
    """Normaliza `matches_json` (lista ORM o texto crudo SQLite) a lista de diccionarios."""
    partidos = snapshot.matches_json or []
    if isinstance(partidos, str):
        try:
            partidos = json.loads(partidos)
        except ValueError:
            return []
    if not isinstance(partidos, list):
        return []
    return [entrada for entrada in partidos if isinstance(entrada, dict)]


def _leer_fixture(sesion: Any, match_id: str) -> Optional[Dict[str, Any]]:
    """Localiza el fixture por `id_partido` en el snapshot más reciente (fallback: `matches`).

    El snapshot es la fuente de exhibición (nombres, `fecha_dt`, marcador y JORNADA canónica).
    La tabla `matches` sólo aporta slugs y `kickoff_utc` cuando el fixture no está en cartelera.
    """
    consulta = select(FixtureSnapshot).order_by(
        FixtureSnapshot.updated_at.desc(), FixtureSnapshot.id.desc()
    )
    for snapshot in sesion.execute(consulta).scalars().all():
        for entrada in _entradas_snapshot(snapshot):
            if str(entrada.get("id_partido")) != str(match_id):
                continue
            actualizado = snapshot.updated_at
            return {
                "match_id": str(entrada.get("id_partido")),
                "jornada": int(snapshot.matchday) if snapshot.matchday is not None else None,
                "local": entrada.get("local") or "",
                "visitante": entrada.get("visitante") or "",
                "local_slug": entrada.get("home_team_slug") or "",
                "visitante_slug": entrada.get("away_team_slug") or "",
                "fecha_ref": entrada.get("fecha_dt") or entrada.get("kickoff_utc"),
                "estado": entrada.get("estado") or "",
                "marcador": entrada.get("marcador_actual"),
                "origen": f"fixtures_snapshots#{snapshot.id}",
                "snapshot_actualizado": (
                    actualizado.isoformat() if hasattr(actualizado, "isoformat") else str(actualizado or "")
                ),
            }

    registro = sesion.execute(select(Match).where(Match.id == str(match_id))).scalars().first()
    if registro is None:
        return None
    marcador = None
    if registro.score_home is not None and registro.score_away is not None:
        marcador = f"{registro.score_home}-{registro.score_away}"
    return {
        "match_id": str(registro.id),
        "jornada": registro.matchday_num,
        "local": registro.home_team_slug or "",
        "visitante": registro.away_team_slug or "",
        "local_slug": registro.home_team_slug or "",
        "visitante_slug": registro.away_team_slug or "",
        "fecha_ref": registro.kickoff_utc.isoformat() if registro.kickoff_utc else None,
        "estado": registro.status or "",
        "marcador": marcador,
        "origen": "matches",
        "snapshot_actualizado": "",
    }


def _resumen_corte(acumulado: Dict[str, Any]) -> Dict[str, Any]:
    """Corte N−1 auditable: muestra, goles reales, tasas, split de sede y cobertura por métrica."""
    pj = int(acumulado["pj"])
    partidos = acumulado["partidos"]
    jornadas = [p["jornada"] for p in partidos if p.get("jornada")]
    return {
        "pj": pj,
        "rango_jornadas": [min(jornadas), max(jornadas)] if jornadas else None,
        "gf": int(acumulado["gf"]),
        "gc": int(acumulado["gc"]),
        "pts": int(acumulado["pts"]),
        "gf_90": _r(_tasa(acumulado["gf"], pj)),
        "gc_90": _r(_tasa(acumulado["gc"], pj)),
        "xg_total": _r(acumulado.get("xg_total")),
        "xga_total": _r(acumulado.get("xga_total")),
        "npxg_90": _r(_tasa(acumulado.get("xg_total"), pj)),
        "xga_90": _r(_tasa(acumulado.get("xga_total"), pj)),
        "poss_pct": _r(acumulado.get("poss_pct")),
        "sot_total": _r(acumulado.get("sot_total")),
        "sota_total": _r(acumulado.get("sota_total")),
        "sot_90": _r(_tasa(acumulado.get("sot_total"), pj)),
        "sota_90": _r(_tasa(acumulado.get("sota_total"), pj)),
        "save_pct": _save_de_corte(acumulado),
        "cobertura_xg": dict(acumulado["cobertura_xg"]),
        "cobertura_telemetria": dict(acumulado["cobertura_telemetria"]),
        "split_sede": {
            "como_local": _bloque_sede(partidos, True),
            "como_visita": _bloque_sede(partidos, False),
        },
    }


# ═════════════════════════════════════════════════════════════════════════════════════════════════
# SEMÁFOROS DE SALUD (derivados de evidencia fáctica, cero opinión)
# ═════════════════════════════════════════════════════════════════════════════════════════════════
def _semaforo(nivel: str, detalle: str) -> Dict[str, str]:
    """Celda de salud homogénea: `{nivel, glifo, detalle}`."""
    return {"nivel": nivel, "glifo": GLIFO.get(nivel, "·"), "detalle": detalle}


def _semaforos(
    dim_volumen: Dict[str, Dict[str, Any]],
    dim_porteria: Dict[str, Dict[str, Any]],
    residuo: Dict[str, Any],
    acum_local: Dict[str, Any],
    acum_visita: Dict[str, Any],
    cache_meta: Dict[str, Any],
) -> Dict[str, Dict[str, str]]:
    """Celdas de salud del laboratorio: cobertura, muestra, delegación, corpus y degradación."""
    salud: Dict[str, Dict[str, str]] = {}

    cob_local = acum_local["cobertura_telemetria"]
    cob_visita = acum_visita["cobertura_telemetria"]
    total = int(cob_local["total"]) + int(cob_visita["total"])
    cubiertos = int(cob_local["cubiertos"]) + int(cob_visita["cubiertos"])
    if total > 0 and cubiertos == total:
        salud["cobertura_posesion"] = _semaforo(
            NIVEL_VERDE, f"{cubiertos}/{total} partidos del corte con posesión/SoT/SoTA publicados."
        )
    elif cubiertos > 0:
        salud["cobertura_posesion"] = _semaforo(
            NIVEL_AMARILLO,
            f"{cubiertos}/{total} partidos cubiertos: V01/V18 degradan a SIN EVIDENCIA (FASE 6).",
        )
    else:
        salud["cobertura_posesion"] = _semaforo(
            NIVEL_NEUTRAL,
            f"0/{total} partidos con `match_telemetry`: no se publica posesión ni Save% (cero invención).",
        )

    muestra = min(int(acum_local["pj"]), int(acum_visita["pj"]))
    if muestra >= 5:
        salud["muestra_corte"] = _semaforo(NIVEL_VERDE, f"Muestra mínima N−1 = {muestra} partidos por club.")
    elif muestra >= 1:
        salud["muestra_corte"] = _semaforo(NIVEL_AMARILLO, f"Muestra mínima N−1 = {muestra} partidos: corte corto.")
    else:
        salud["muestra_corte"] = _semaforo(NIVEL_NEUTRAL, "Muestra N−1 vacía: dimensiones no computables.")

    if residuo["local"]["residuo"] is not None and residuo["visita"]["residuo"] is not None:
        salud["residuo_ortogonal"] = _semaforo(
            NIVEL_VERDE,
            f"v_Vol⊥ = {residuo['local']['residuo']:+.4f} (L) / {residuo['visita']['residuo']:+.4f} (V) "
            f"dentro de [{residuo['cotas'][0]:+.2f}, {residuo['cotas'][1]:+.2f}].",
        )
    else:
        salud["residuo_ortogonal"] = _semaforo(
            NIVEL_NEUTRAL, "No computable: exige posesión + SoT + SoTA íntegros en ambos cortes."
        )

    if cache_meta.get("disponible"):
        salud["corpus_congelado"] = _semaforo(
            NIVEL_VERDE, f"{int(cache_meta.get('partidos') or 0)} partidos en `{cache_meta.get('ruta')}`."
        )
    else:
        salud["corpus_congelado"] = _semaforo(
            NIVEL_NEUTRAL, str(cache_meta.get("error") or "Artefacto congelado no disponible.")
        )

    celdas = list(dim_volumen.values()) + list(dim_porteria.values())
    degradadas = [celda["id"] for celda in celdas if celda["estado"] != ESTADO_EVALUADO]
    if not degradadas:
        salud["degradacion_fase_6"] = _semaforo(
            NIVEL_VERDE, f"0/{len(celdas)} celdas degradadas: evidencia íntegra en ambas dimensiones."
        )
    else:
        salud["degradacion_fase_6"] = _semaforo(
            NIVEL_AMARILLO,
            f"{len(degradadas)}/{len(celdas)} celdas en SIN EVIDENCIA (FASE 6): "
            f"{', '.join(degradadas)} — contrato tri-estado {VARIANZA_RATIFICADA}.",
        )
    return salud


# ═════════════════════════════════════════════════════════════════════════════════════════════════
# ORQUESTADOR DEL PARTIDO (corte N−1 real → celdas → residuo → veredicto)
# ═════════════════════════════════════════════════════════════════════════════════════════════════
def _marco_reporte(
    match_id: str, fixture: Optional[Dict[str, Any]], temporada: str
) -> Dict[str, Any]:
    """Esqueleto común del reporte (contrato estable para la consola y `--json`)."""
    return {
        "nodos_gobernanza": list(NODOS_GOBIERNO),
        "sandbox": "VOLUMEN_PORTERIA_DIM1_DIM4",
        "modo": "SOLO_LECTURA",
        "varianza": VARIANZA_RATIFICADA,
        "temporada": str(temporada),
        "match": fixture if fixture is not None else {"match_id": str(match_id)},
        "escritura_bd": False,
        "llamadas_red": False,
    }


def _corte_nulo(motivo: str) -> Dict[str, Any]:
    """Bloque de corte cuando el fixture no permite fijar la jornada objetivo."""
    return {
        "jornada_objetivo": None,
        "corte_hasta_jornada": None,
        "regla": REGLA_CORTE,
        "local": None,
        "visita": None,
        "nota": motivo,
    }


def _reporte_no_encontrado(match_id: str, temporada: str, cache_meta: Dict[str, Any]) -> Dict[str, Any]:
    """Reporte honesto cuando el fixture no existe: cero dimensiones inventadas, todo degradado."""
    vacio = _acumular_club([], {}, {})
    dim_1 = _dimension_volumen(vacio, vacio)
    dim_4 = _dimension_porteria(vacio, vacio)
    residuo = _bloque_residuo(vacio, vacio)
    reporte = _marco_reporte(match_id, None, temporada)
    reporte.update({
        "status": "NO_ENCONTRADO",
        "motivo": (
            f"El fixture `{match_id}` no está publicado ni en `fixtures_snapshots` ni en la tabla "
            "`matches`: sin identidad no hay corte N−1 que auditar."
        ),
        "cache_opta": cache_meta,
        "corte_n_1": _corte_nulo("Fixture inexistente: jornada objetivo desconocida."),
        "dimension_1_volumen": dim_1,
        "dimension_4_porteria": dim_4,
        "delta_posesion": _bloque_delta(vacio, vacio, dim_1),
        "residuo_volumen": residuo,
        "semaforos": _semaforos(dim_1, dim_4, residuo, vacio, vacio, cache_meta),
    })
    return reporte


def _veredicto(
    dim_volumen: Dict[str, Dict[str, Any]],
    dim_porteria: Dict[str, Dict[str, Any]],
    acum_local: Dict[str, Any],
    acum_visita: Dict[str, Any],
    jornada_objetivo: Optional[int],
) -> Tuple[str, str]:
    """Veredicto tri-estado derivado del número de celdas EVALUADAS (jamás de una opinión)."""
    celdas = list(dim_volumen.values()) + list(dim_porteria.values())
    evaluadas = [celda["id"] for celda in celdas if celda["estado"] == ESTADO_EVALUADO]
    total = len(celdas)
    if not jornada_objetivo:
        return (
            "SIN_EVIDENCIA",
            "Jornada objetivo no publicada: imposible fijar el corte futuro-ciego N−1.",
        )
    pj_local = int(acum_local.get("pj") or 0)
    pj_visita = int(acum_visita.get("pj") or 0)
    if pj_local <= 0 or pj_visita <= 0:
        return (
            "SIN_EVIDENCIA",
            f"Corte N−1 vacío (local PJ={pj_local} · visita PJ={pj_visita}): "
            "no existe muestra terminal que auditar antes de la jornada objetivo.",
        )
    if len(evaluadas) == total:
        return (
            "EXITO",
            f"{total}/{total} celdas EVALUADO: V01/V02 y V17/V18/V19 + `AUX_*` con evidencia fáctica íntegra.",
        )
    if evaluadas:
        return (
            "PARCIAL",
            f"{len(evaluadas)}/{total} celdas EVALUADO ({', '.join(evaluadas)}); "
            f"el resto degrada a {NOTA_FASE_6} con cobertura declarada.",
        )
    return (
        "SIN_EVIDENCIA",
        f"0/{total} celdas con evidencia: el corte N−1 (PJ local={pj_local} · visita={pj_visita}) "
        "no publica posesión/SoT/SoTA ni xGOT. Cero imputación [GOVERNANCE-01].",
    )


def ejecutar_sandbox_volumen_porteria_partido(
    match_id: str,
    temporada: str = TEMPORADA_DEFAULT,
    jornada: Optional[int] = None,
) -> Dict[str, Any]:
    """Audita DIM 1 (𝒯_Vol · V01/V02) y DIM 4 (𝒯_Por · V17/V18/V19) de un fixture, sólo lectura.

    Cadena: `PersistenceGateway.read_session()` → fixture (snapshot o `matches`) → corte futuro-ciego
    N−1 por club → telemetría 3NF con cobertura íntegra → caché Opta congelada → celdas bipartitas →
    residuo de volumen ortogonal (FCF delegado) → ΔPosición → veredicto tri-estado.

    `jornada` permite sobreescribir la jornada objetivo; por omisión se usa la del snapshot/`matches`.
    """
    cache, cache_meta = cargar_cache_opta(temporada)
    gateway = PersistenceGateway()
    with gateway.read_session() as sesion:
        fixture = _leer_fixture(sesion, match_id)
        if fixture is None:
            logger.warning("[LN-QBE-111] Fixture inexistente: %s", match_id)
            return _reporte_no_encontrado(match_id, temporada, cache_meta)
        objetivo = int(jornada) if jornada is not None else fixture.get("jornada")
        acumulados: Dict[str, Dict[str, Any]] = {}
        for lado, clave_slug in (("local", "local_slug"), ("visita", "visitante_slug")):
            slug = str(fixture.get(clave_slug) or "")
            if not slug or not objetivo:
                partidos: List[Dict[str, Any]] = []
            else:
                partidos = _partidos_de_club(sesion, slug, int(objetivo))
            telemetria = _telemetria_de_club(sesion, partidos, slug)
            acumulados[lado] = _acumular_club(partidos, cache, telemetria)

    acum_local = acumulados["local"]
    acum_visita = acumulados["visita"]
    dim_1 = _dimension_volumen(acum_local, acum_visita)
    dim_4 = _dimension_porteria(acum_local, acum_visita)
    residuo = _bloque_residuo(acum_local, acum_visita)
    delta = _bloque_delta(acum_local, acum_visita, dim_1)
    status, motivo = _veredicto(dim_1, dim_4, acum_local, acum_visita, objetivo)

    reporte = _marco_reporte(match_id, fixture, temporada)
    reporte.update({
        "status": status,
        "motivo": motivo,
        "cache_opta": cache_meta,
        "corte_n_1": {
            "jornada_objetivo": objetivo,
            "corte_hasta_jornada": (int(objetivo) - 1) if objetivo else None,
            "regla": REGLA_CORTE,
            "local": _resumen_corte(acum_local),
            "visita": _resumen_corte(acum_visita),
        },
        "cobertura": {
            "telemetria": {
                "local": dict(acum_local["cobertura_telemetria"]),
                "visita": dict(acum_visita["cobertura_telemetria"]),
            },
            "opta_xg": {
                "local": dict(acum_local["cobertura_xg"]),
                "visita": dict(acum_visita["cobertura_xg"]),
            },
        },
        "dimension_1_volumen": dim_1,
        "dimension_4_porteria": dim_4,
        "delta_posesion": delta,
        "residuo_volumen": residuo,
        "semaforos": _semaforos(dim_1, dim_4, residuo, acum_local, acum_visita, cache_meta),
    })
    return reporte


# ═════════════════════════════════════════════════════════════════════════════════════════════════
# [ARCH-1.4.50] TABLERO ASCII DE CONSOLA (presentación pura, cero cálculo)
# ═════════════════════════════════════════════════════════════════════════════════════════════════
def _ancho_visible(texto: str) -> int:
    """Ancho de desplazamiento en terminal (glifos anchos y emoji cuentan 2 columnas)."""
    ancho = 0
    for caracter in texto:
        codigo = ord(caracter)
        if codigo in (0xFE0F, 0x200D) or 0x0300 <= codigo <= 0x036F:
            continue
        if (
            0x1F000 <= codigo <= 0x1FAFF
            or 0x2600 <= codigo <= 0x27BF
            or 0x2B00 <= codigo <= 0x2BFF
            or 0x2E80 <= codigo <= 0xA4CF
        ):
            ancho += 2
        else:
            ancho += 1
    return ancho


def _pad(texto: str, ancho: int) -> str:
    """Relleno derecho por ancho VISIBLE (no por longitud de cadena)."""
    relleno = max(0, ancho - _ancho_visible(texto))
    return texto + (" " * relleno)


def _recortar(texto: str, ancho: int) -> str:
    """Recorta a ancho visible (red de seguridad para no romper el borde de la caja)."""
    if _ancho_visible(texto) <= ancho:
        return texto
    salida = ""
    for caracter in texto:
        if _ancho_visible(salida + caracter) > ancho - 1:
            break
        salida += caracter
    return salida + "…"


def _caja(titulo: str, filas: Sequence[str]) -> None:
    """Caja ASCII/Unicode de ancho fijo (94 columnas) con título embebido."""
    interior = ANCHO_TABLERO - 2
    encabezado = f"─ {titulo} "
    print("┌" + encabezado + ("─" * max(0, interior - _ancho_visible(encabezado))) + "┐")
    for fila in filas:
        print("│ " + _pad(_recortar(fila, interior - 2), interior - 2) + " │")
    print("└" + ("─" * interior) + "┘")


def _linea(etiqueta: str, texto: str) -> str:
    """Fila etiqueta/valor del bloque de contexto (etiqueta alineada en 10 columnas)."""
    return f"{_pad(etiqueta, 10)}{texto}"


def _num(valor: Optional[float], decimales: int = 4, ancho: int = 8) -> str:
    """Formato numérico con signo y ancho fijo; `—` cuando la evidencia no existe."""
    if valor is None:
        return "—".rjust(ancho)
    return f"{float(valor):+.{decimales}f}".rjust(ancho)


def _texto_magnitud(valor: Any, ancho: int) -> str:
    """Celda de tabla: `%` publicado tal cual, numérico a 4 decimales, `None` como `—`."""
    if valor is None:
        return "—".rjust(ancho)
    if isinstance(valor, str):
        return valor.rjust(ancho)
    return f"{float(valor):.4f}".rjust(ancho)


def _glifo_celda(celda: Dict[str, Any]) -> str:
    """Glifo de estado de una celda V0x (🟢 evaluada / ⚪ sin evidencia)."""
    return GLIFO.get(str(celda.get("estado")), "·")


def _fila_dimension(celda: Dict[str, Any]) -> str:
    """Fila de tabla: ID · variable · unidad · LOCAL · VISITA · estado."""
    return (
        f"{_pad(str(celda['id']), 5)}"
        f"{_pad(str(celda['variable'])[:39], 40)}"
        f"{_pad(str(celda['unidad']), 10)}"
        f"{_texto_magnitud(celda.get('local'), 9)}"
        f"{_texto_magnitud(celda.get('visita'), 9)}"
        f"  {_glifo_celda(celda)} {celda['estado']}"
    )


def _encabezado_dimension(etiqueta: str) -> str:
    """Cabecera de tabla de dimensión, alineada con `_fila_dimension`."""
    return (
        f"{_pad(etiqueta, 5)}{_pad('VARIABLE', 40)}{_pad('UNIDAD', 10)}"
        f"{'LOCAL'.rjust(9)}{'VISITA'.rjust(9)}  ESTADO"
    )


def _envolver(texto: str, ancho: int = ANCHO_TABLERO - 14) -> List[str]:
    """Envuelve texto largo respetando palabras (sin dependencias externas)."""
    palabras = str(texto).split()
    lineas: List[str] = []
    actual = ""
    for palabra in palabras:
        candidata = f"{actual} {palabra}".strip()
        if _ancho_visible(candidata) <= ancho:
            actual = candidata
            continue
        if actual:
            lineas.append(actual)
        actual = palabra
    if actual:
        lineas.append(actual)
    return lineas or [""]


def _bloque_dimension(reporte: Dict[str, Any], clave: str, titulo: str) -> None:
    """Caja de una dimensión completa (V0x) con pie de cobertura declarada."""
    dimension = reporte.get(clave) or {}
    separador = "─" * (ANCHO_TABLERO - 4)
    filas: List[str] = [_encabezado_dimension("ID"), separador]
    evaluadas = 0
    for identificador in sorted(dimension.keys()):
        celda = dimension[identificador]
        filas.append(_fila_dimension(celda))
        if celda.get("estado") == ESTADO_EVALUADO:
            evaluadas += 1
    filas.append(separador)
    filas.append(
        f"Evaluadas {evaluadas}/{len(dimension)} · ⚪ SIN EVIDENCIA = sensor ausente; "
        "jamás se imputa una cifra [GOVERNANCE-01]."
    )
    degradadas = [c for c in sorted(dimension) if dimension[c].get("estado") != ESTADO_EVALUADO]
    if degradadas:
        filas.append(
            f"Nota de degradación ({', '.join(degradadas)}): {dimension[degradadas[0]].get('nota')}"
        )
    _caja(titulo, filas)


def _bloque_contexto_volumen(reporte: Dict[str, Any]) -> None:
    """Caja 1: identidad del experimento, corte N−1 declarado y procedencia de la evidencia."""
    fixture = reporte.get("match") or {}
    corte = reporte.get("corte_n_1") or {}
    cache = reporte.get("cache_opta") or {}
    cobertura = reporte.get("cobertura") or {}
    telemetria = cobertura.get("telemetria") or {}
    dim_1 = reporte.get("dimension_1_volumen") or {}
    local = corte.get("local") or {}
    visita = corte.get("visita") or {}
    jornada = corte.get("jornada_objetivo") or fixture.get("jornada")
    marcador = fixture.get("marcador")
    rango = local.get("rango_jornadas")
    tramo = f"J{rango[0]}..J{rango[1]}" if rango else "—"

    filas: List[str] = [
        _linea(
            "FIXTURE",
            f"{fixture.get('match_id')} · Jornada {jornada if jornada else '—'} · "
            f"{fixture.get('estado') or '—'}{(' · ' + str(marcador)) if marcador else ''}",
        ),
        _linea(
            "DUELO",
            f"{fixture.get('local') or '—'} (L)  vs  {fixture.get('visitante') or '—'} (V)",
        ),
        _linea("REGLA", REGLA_CORTE),
        _linea(
            "CORTE",
            f"{tramo} · {local.get('pj', 0)} PJ local · {visita.get('pj', 0)} PJ visita · "
            f"N−1 ≤ J{(int(jornada) - 1) if jornada else '—'}",
        ),
        _linea(
            "CORPUS",
            f"{cache.get('ruta') or '—'} · {cache.get('partidos', 0)} partidos · "
            f"{'disponible' if cache.get('disponible') else 'AUSENTE'}",
        ),
        _linea(
            "SENSOR",
            f"match_telemetry · cobertura {int((telemetria.get('local') or {}).get('cubiertos') or 0)}/"
            f"{int((telemetria.get('local') or {}).get('total') or 0)} (L) · "
            f"{int((telemetria.get('visita') or {}).get('cubiertos') or 0)}/"
            f"{int((telemetria.get('visita') or {}).get('total') or 0)} (V) · "
            "posesión/SoT/SoTA",
        ),
        _linea(
            "CONTRATO",
            f"tri-estado {VARIANZA_RATIFICADA} · V01/V18 EVALUADO ⇔ evidencia fáctica íntegra",
        ),
        _linea(
            "MODELO",
            "DIM 1 (𝒯_Vol · V01/V02) × DIM 4 (𝒯_Por · V17/V18/V19) · "
            f"v_Vol⊥ = FCF − 1 ∈ [{COTA_RESIDUO[0]:+.2f}, {COTA_RESIDUO[1]:+.2f}]",
        ),
        _linea(
            "V01",
            f"estado {dim_1.get('V01', {}).get('estado', '—')} · posesión media del corte "
            "(cero imputación).",
        ),
        "",
    ]
    texto_estado = f"{reporte.get('status')} — {reporte.get('motivo')}"
    trozos = _envolver(texto_estado)
    filas.append(_linea("ESTADO", trozos[0]))
    for trozo in trozos[1:]:
        filas.append(_linea("", trozo))
    _caja("CONTEXTO DEL EXPERIMENTO · VOLUMEN & PORTERÍA", filas)


def _bloque_residuo_consola(reporte: Dict[str, Any]) -> None:
    """Caja 4: residuo de Volumen Ortogonal (FCF sellado) separando DOMINIO de PELIGRO REAL."""
    residuo = reporte.get("residuo_volumen") or {}
    local = residuo.get("local") or {}
    visita = residuo.get("visita") or {}
    separador = "─" * (ANCHO_TABLERO - 4)
    filas: List[str] = [
        f"{_pad('CLUB', 9)}{'POSS%'.rjust(9)}{'SoT'.rjust(8)}{'SoTA'.rjust(8)}"
        f"{'FCF'.rjust(9)}{'v_Vol⊥'.rjust(10)}  LECTURA",
        separador,
    ]
    for etiqueta, lado in (("LOCAL", local), ("VISITA", visita)):
        filas.append(
            f"{_pad(etiqueta, 9)}"
            f"{_num(lado.get('poss_pct'), 2, 9)}"
            f"{_num(lado.get('sot'), 2, 8)}"
            f"{_num(lado.get('sota'), 2, 8)}"
            f"{_num(lado.get('fcf'), 4, 9)}"
            f"{_num(lado.get('residuo'), 4, 10)}"
            f"  {lado.get('lectura')}"
        )
    filas.append(separador)
    filas.append(
        f"Δ v_Vol⊥ (L − V) = {_num(residuo.get('delta'), 4, 10)}   ⇒ {residuo.get('lectura_delta')}"
    )
    filas.append(separador)
    filas.extend(_envolver(f"Fórmula: {residuo.get('formula')}"))
    filas.extend(_envolver(f"Delegación DIRGEN: {residuo.get('delegacion')} — cero reimplementación."))
    filas.append(
        f"v_Vol⊥ > 0 ⇒ dominio CONVERTIDO · v_Vol⊥ < 0 ⇒ PRESIÓN ESTÉRIL · diagnóstico, NO insumo de λ."
    )
    nota_local = local.get("nota")
    if nota_local:
        filas.extend(_envolver(f"Nota LOCAL: {nota_local}"))
    nota_visita = visita.get("nota")
    if nota_visita:
        filas.extend(_envolver(f"Nota VISITA: {nota_visita}"))
    _caja("RESIDUO DE VOLUMEN ORTOGONAL · v_Vol⊥ = FCF − 1  [LN-QBE-111]", filas)


def _bloque_delta_consola(reporte: Dict[str, Any]) -> None:
    """Caja 5: ΔPosición territorial bipartita con la MISMA fuente que publica V01."""
    delta = reporte.get("delta_posesion") or {}
    filas: List[str] = [
        f"POSESIÓN LOCAL  {_num(delta.get('local'), 2, 9)} %   ·   "
        f"POSESIÓN VISITA {_num(delta.get('visita'), 2, 9)} %",
        f"{_pad('ΔPOSICIÓN', 15)}{_num(delta.get('valor'), 2, 9)} pp   ⇒ {delta.get('lectura')}",
        f"{_pad('ESTADO V01', 15)}{delta.get('estado') or '—'}",
    ]
    nota = delta.get("nota")
    if nota:
        filas.append("")
        filas.extend(_envolver(nota))
    filas.append("")
    filas.extend(_envolver(
        "Identidad: ΔPosición = poss_local − poss_visita con ambas magnitudes ∈ [0, 100]; "
        "un valor fuera de contrato dispara ValueError (cero saneamiento silencioso)."
    ))
    _caja("ΔPOSICIÓN TERRITORIAL · poss_local − poss_visita", filas)


def _bloque_semaforos(reporte: Dict[str, Any]) -> None:
    """Caja 6: semáforos de salud derivados de la evidencia (cero opinión)."""
    semaforos = reporte.get("semaforos") or {}
    filas: List[str] = []
    for nombre in sorted(semaforos.keys()):
        celda = semaforos[nombre]
        detalle = _envolver(str(celda.get("detalle") or ""), ANCHO_TABLERO - 32)
        filas.append(
            f"{celda.get('glifo', '·')} {_pad(nombre, 22)}{detalle[0] if detalle else ''}"
        )
        for extra in detalle[1:]:
            filas.append(f"   {_pad('', 22)}{extra}")
    if not filas:
        filas.append("Sin semáforos publicados.")
    _caja("SEMÁFOROS DE SALUD", filas)


def imprimir_tablero_volumen_porteria_consola(reporte: Dict[str, Any]) -> None:
    """Renderiza el tablero completo de un partido ([ARCH-1.4.50]). Presentación pura."""
    print()
    _caja("Q-BE · LABORATORIO VOLUMEN & PORTERÍA · DIM 1 (𝒯_Vol) × DIM 4 (𝒯_Gk)", [
        f"[{NODOS_GOBIERNO[0]}] / [{NODOS_GOBIERNO[1]}] · SÓLO LECTURA · corte N−1 (futuro-ciego)",
        f"FCF ∈ [{FCF_MIN:.2f}, {FCF_MAX:.2f}] · v_Vol⊥ = FCF − 1 ∈ "
        f"[{COTA_RESIDUO[0]:+.2f}, {COTA_RESIDUO[1]:+.2f}] · plano [LN-QBE-030]",
        f"Contrato tri-estado {VARIANZA_RATIFICADA} · hermana: sandbox_ataque_defensa_pipeline [ARCH-1.4.47]",
    ])
    _bloque_contexto_volumen(reporte)
    _bloque_dimension(
        reporte, "dimension_1_volumen", "DIM 1 · VOLUMEN Y DOMINIO TERRITORIAL (𝒯_Vol · V01/V02 + AUX)"
    )
    _bloque_dimension(
        reporte, "dimension_4_porteria", "DIM 4 · RENDIMIENTO DE GUARDAMETAS (𝒯_Gk · V15-V17)"
    )
    _bloque_residuo_consola(reporte)
    _bloque_delta_consola(reporte)
    _bloque_semaforos(reporte)
    print("─" * ANCHO_TABLERO)
    print(
        " Sólo lectura · 0 escrituras en la bóveda · 0 llamadas de red · "
        f"nodos {' + '.join(NODOS_GOBIERNO)}"
    )
    print()


# ═════════════════════════════════════════════════════════════════════════════════════════════════
# MODO JORNADA (barrido de la cartelera completa, mismo protocolo sellado)
# ═════════════════════════════════════════════════════════════════════════════════════════════════
def _ids_de_jornada(sesion: Any, jornada: int) -> List[str]:
    """IDs de la jornada desde el snapshot más reciente; fallback a la tabla `matches`."""
    consulta = (
        select(FixtureSnapshot)
        .where(FixtureSnapshot.matchday == int(jornada))
        .order_by(FixtureSnapshot.updated_at.desc(), FixtureSnapshot.id.desc())
    )
    for snapshot in sesion.execute(consulta).scalars().all():
        identificadores: List[str] = []
        for entrada in _entradas_snapshot(snapshot):
            ident = str(entrada.get("id_partido") or "")
            if ident and ident not in identificadores:
                identificadores.append(ident)
        if identificadores:
            return identificadores
    filas = sesion.execute(
        select(Match).where(Match.matchday_num == int(jornada)).order_by(Match.id)
    ).scalars().all()
    return [str(fila.id) for fila in filas]


def ejecutar_sandbox_volumen_porteria_jornada(
    jornada: int,
    temporada: str = TEMPORADA_DEFAULT,
) -> Dict[str, Any]:
    """Barrido soberano de la jornada: un reporte por fixture + conteo de veredictos."""
    gateway = PersistenceGateway()
    with gateway.read_session() as sesion:
        identificadores = _ids_de_jornada(sesion, jornada)

    reportes = [
        ejecutar_sandbox_volumen_porteria_partido(ident, temporada, int(jornada))
        for ident in identificadores
    ]
    conteo = {"EXITO": 0, "PARCIAL": 0, "SIN_EVIDENCIA": 0, "NO_ENCONTRADO": 0}
    for reporte in reportes:
        estado = str(reporte.get("status") or "NO_ENCONTRADO")
        conteo[estado] = conteo.get(estado, 0) + 1
    return {
        "nodos_gobernanza": list(NODOS_GOBIERNO),
        "sandbox": "VOLUMEN_PORTERIA_DIM1_DIM4_JORNADA",
        "modo": "SOLO_LECTURA",
        "varianza": VARIANZA_RATIFICADA,
        "temporada": str(temporada),
        "jornada": int(jornada),
        "total_partidos": len(reportes),
        "conteo_estados": conteo,
        "escritura_bd": False,
        "llamadas_red": False,
        "reportes": reportes,
    }


def imprimir_tablero_jornada_volumen_porteria_consola(resumen: Dict[str, Any]) -> None:
    """Tablero compacto de la jornada: V01 · V18 · Δ v_Vol⊥ por fixture ([ARCH-1.4.50])."""
    jornada = resumen.get("jornada")
    separador = "─" * (ANCHO_TABLERO - 4)
    filas: List[str] = [
        f"{_pad('FIXTURE', 16)}{_pad('LOCAL vs VISITA', 28)}"
        f"{'V01 L'.rjust(8)}{'V01 V'.rjust(8)}{'V18 L'.rjust(8)}{'V18 V'.rjust(8)}"
        f"{'Δv_Vol⊥'.rjust(9)}  ST",
        separador,
    ]
    for reporte in resumen.get("reportes") or []:
        fixture = reporte.get("match") or {}
        v01 = (reporte.get("dimension_1_volumen") or {}).get("V01") or {}
        v16 = (reporte.get("dimension_4_porteria") or {}).get("V18") or {}
        residuo = reporte.get("residuo_volumen") or {}
        duelo = (
            f"{str(fixture.get('local') or '—')[:13]} v "
            f"{str(fixture.get('visitante') or '—')[:12]}"
        )
        filas.append(
            f"{_pad(str(fixture.get('match_id') or '—')[:15], 16)}"
            f"{_pad(duelo, 28)}"
            f"{_texto_magnitud(v01.get('local'), 8)}"
            f"{_texto_magnitud(v01.get('visita'), 8)}"
            f"{_texto_magnitud(v16.get('local'), 8)}"
            f"{_texto_magnitud(v16.get('visita'), 8)}"
            f"{_num(residuo.get('delta'), 3, 9)}"
            f"  {str(reporte.get('status') or '?')[:1]}"
        )
    if not filas[2:]:
        filas.append("Sin fixtures publicados para la jornada solicitada.")
    filas.append("")
    filas.append("ST: E=EXITO · P=PARCIAL · S=SIN EVIDENCIA · N=NO ENCONTRADO")
    conteo = resumen.get("conteo_estados") or {}
    filas.append(
        "CONTEO: " + " · ".join(f"{clave}={valor}" for clave, valor in sorted(conteo.items()))
    )
    _caja(f"BARRIDO DE LA JORNADA {jornada} · VOLUMEN & PORTERÍA", filas)
    print("─" * ANCHO_TABLERO)
    print(
        f" Sólo lectura · nodos {' + '.join(NODOS_GOBIERNO)} · "
        "detalle por fixture: --partido <ID>"
    )
    print()


# ═════════════════════════════════════════════════════════════════════════════════════════════════
# CLI (argparse puro, sin dependencias externas)
# ═════════════════════════════════════════════════════════════════════════════════════════════════
def _construir_parser() -> argparse.ArgumentParser:
    """Contrato de línea de comandos del sandbox [ARCH-1.4.50]."""
    parser = argparse.ArgumentParser(
        prog="sandbox_volumen_porteria_pipeline",
        description=(
            "Sandbox CLI-first de Volumen Territorial (DIM 1 · V01/V02) y Portería (DIM 4 · V17/V18/V19): "
            "corte N−1 real → telemetría íntegra → residuo de volumen ortogonal (FCF delegado) → "
            "ΔPosición → tablero tri-estado. Sólo lectura."
        ),
    )
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument(
        "--partido", metavar="MATCH_ID", help="Fixture a evaluar, ej. LIGAMX-J11-07"
    )
    grupo.add_argument("--jornada", type=int, metavar="N", help="Barrido de toda la jornada, ej. 11")
    parser.add_argument(
        "--temporada", default=TEMPORADA_DEFAULT, metavar="AAAA",
        help=f"Temporada del corpus congelado (default {TEMPORADA_DEFAULT}).",
    )
    parser.add_argument("--json", action="store_true", help="Emite el reporte estructurado en JSON.")
    parser.add_argument("--verbose", action="store_true", help="Registro de diagnóstico detallado.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Punto de entrada CLI. Devuelve 0 salvo fixture inexistente o jornada vacía."""
    argumentos = _construir_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if argumentos.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    if argumentos.partido:
        reporte = ejecutar_sandbox_volumen_porteria_partido(
            argumentos.partido, argumentos.temporada
        )
        if argumentos.json:
            print(json.dumps(reporte, ensure_ascii=False, indent=2))
        else:
            imprimir_tablero_volumen_porteria_consola(reporte)
        return 0 if reporte.get("status") in ("EXITO", "PARCIAL", "SIN_EVIDENCIA") else 1

    resumen = ejecutar_sandbox_volumen_porteria_jornada(argumentos.jornada, argumentos.temporada)
    if argumentos.json:
        print(json.dumps(resumen, ensure_ascii=False, indent=2))
    else:
        imprimir_tablero_jornada_volumen_porteria_consola(resumen)
    return 0 if resumen.get("total_partidos") else 1


if __name__ == "__main__":
    sys.exit(main())

















