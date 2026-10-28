# -*- coding: utf-8 -*-
"""
[LN-QBE-106] / [ARCH-1.4.45] SANDBOX H2H — PIPELINE AUTÓNOMO CLI-FIRST.

Misión
------
Desacoplar la experimentación matemática y la observabilidad del peso de la interfaz web.
Ejecuta de punta a punta la cadena REAL del servidor —ingesta (SQLite + corpus congelado)
→ tratamiento → kernel H2H → fusión convexa → salud/semáforos → tablero ASCII— sin FastAPI,
sin DOM y sin Playwright.

Régimen: `[HÍBRIDO DUAL-TRACK]`
* `[DIRGEN-STRICT]`: el modelado relacional de la Dimensión 11 (V26/V27/V28), la ley de mezcla
  `[LN-QBE-104]`/`[VAULT-CORE-005]` y la métrica `Δ_epist` NO se reimplementan: se invocan
  `calcular_matriz_h2h_empirica`, `fusionar_simplex_con_h2h` y `derivar_discrepancia_epistemica`
  tal como están sellados.
* `[DBBD-FUNGIBLE]`: composición, CLI (`--partido` / `--jornada` / `--json`) y tablero.

Axiomas operativos
------------------
1. **Sólo lectura:** `PersistenceGateway.read_session()` y `json.load` del corpus. Prohibido
   escribir en `data/qbe_database.db`; prohibido abrir red.
2. **Cero doble fusión (H-2 ratificado):** `distribucion_poisson` se alimenta de
   `audit_trace_json.simplex_poisson` (Generador A puro). Sólo si la traza no lo publica se
   usa el símplex persistido, declarando `origen_poisson = "distribucion_persistida"` (🟡).
3. **Clave canónica `p_visitante` (H-3 ratificado):** el símplex emitido porta SIEMPRE
   `p_local` / `p_empate` / `p_visitante`; nunca `p_visita` (evita `NameError` en el juez).
4. **Ley Zero-H2H (H-4 ratificado):** sin duelos el kernel NO se invoca; `w_H2H = 0.0`,
   fusión = identidad y `Δ_epist` en el piso R-1 (`0.02`), con V26/V27/V28 en `SIN EVIDENCIA`.
   Jamás se fabrica un récord `0-0-0` ni un `ΔG = 0` (ausencia de evidencia no es empate).
5. **Futuro-ceguera declarada:** si la ventana incluye un duelo con `dias_antiguedad == 0`
   (el propio día del kickoff) se declara en el semáforo; el comportamiento del proveedor
   sellado `[ARCH-1.4.44]` NO se altera desde el sandbox.

Uso:
    python -m scripts.laboratorio.sandbox_h2h_pipeline --partido LIGAMX-J11-07
    python -m scripts.laboratorio.sandbox_h2h_pipeline --jornada 11
    python -m scripts.laboratorio.sandbox_h2h_pipeline --partido LIGAMX-J11-07 --json
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

from sqlalchemy import select

# ── Planos sellados (cero reimplementación de fórmulas) ─────────────────────────────────────
from src.core.sovereign.h2h_kernel import TAU_H2H_DEEP, calcular_matriz_h2h_empirica
from src.core.sovereign.h2h_provider import LIMITE_DUELOS_H2H, obtener_h2h_unificado
from src.core.sovereign_pipeline import (
    DELTA_EPISTEMICO_SIN_EVIDENCIA,
    derivar_discrepancia_epistemica,
    fusionar_simplex_con_h2h,
)
from src.storage.gateway import PersistenceGateway
from src.storage.models import FixtureSnapshot, Match, SovereignDistribution

logger = logging.getLogger("SandboxH2H")

# ── Constantes de presentación y de degradación honesta ────────────────────────────────────
ESTADO_EVALUADO = "EVALUADO"
ESTADO_SIN_EVIDENCIA = "SIN EVIDENCIA"
SIN_ANTECEDENTES_DIRECTOS = "Sin antecedentes directos"
SIN_ANTECEDENTES_SEDE = "Sin antecedentes locales"   # [LN-QBE-105] literal sellado
UMBRAL_CUARENTENA_EPIST = 0.12                       # [LN-QBE-070-B] frontera τ_disp
TOLERANCIA_SIMPLEX = 1e-6                            # invariante ciego §P-2 [LN-QBE-106]
NIVEL_VERDE = "VERDE"
NIVEL_AMARILLO = "AMARILLO"
NIVEL_ROJO = "ROJO"
NIVEL_NEUTRAL = "NEUTRAL"
GLIFO = {NIVEL_VERDE: "🟢", NIVEL_AMARILLO: "🟡", NIVEL_ROJO: "🔴", NIVEL_NEUTRAL: "⚪"}

ANCHO_TABLERO = 94


def _semaforo(nivel: str, motivo: str) -> Dict[str, str]:
    """Celda semafórica homogénea (nivel + glifo + motivo fáctico)."""
    return {"nivel": nivel, "glifo": GLIFO.get(nivel, "⚪"), "motivo": motivo}


# ═════════════════════════════════════════════════════════════════════════════════════════════
# DIMENSIÓN 11 — MODELADO RELACIONAL DE LA MEMORIA H2H (V26 / V27 / V28 / AUX_XG_HIST)
# ═════════════════════════════════════════════════════════════════════════════════════════════
def calcular_metricas_relacionales_h2h(
    duelos: Sequence[Dict[str, Any]],
    local_nombre: str = "LOCAL",
    visita_nombre: str = "VISITANTE",
) -> Dict[str, Dict[str, Any]]:
    """`[LN-QBE-106]` Agregado relacional antisimétrico de la ventana H2H.

    Transcripción aritmética del agregado sellado `[LN-QBE-105]` (`_agregar_h2h_stats`),
    enriquecida con la ATRIBUCIÓN del bando beneficiario:

    * **V26** — multiconjunto de resultados desde la perspectiva del local evaluado: `W-D-L`.
    * **V27** — magnitud diferencial `ΔG = Σ(GL − GV)` con bando beneficiario explícito
      (`LOCAL` / `VISITANTE` / `EQUILIBRADO`) y saldo descriptivo firmado.
    * **V28** — rendimiento del VISITANTE condicionado a la sede evaluada: sólo acreditan
      las filas con `es_local_sede is True` (cero fabricación de sede).
    * **AUX_XG_HIST** — Fase 6 (Deep Opta Cache): permanece `SIN EVIDENCIA`, jamás simulada.

    Sin evidencia verificable devuelve las cuatro variables en `SIN EVIDENCIA` (Ley Zero-H2H).
    """
    local_nombre = str(local_nombre or "LOCAL")
    visita_nombre = str(visita_nombre or "VISITANTE")

    victorias = empates = derrotas = 0
    goles_favor = goles_contra = 0
    visitante_victorias = visitante_empates = visitante_derrotas = 0
    con_sede = 0
    evaluados = 0

    for fila in (duelos or []):
        if not isinstance(fila, dict):
            continue
        try:
            goles_local = int(fila.get("goles_local"))
            goles_visita = int(fila.get("goles_visita"))
        except (TypeError, ValueError):
            continue
        evaluados += 1
        goles_favor += goles_local
        goles_contra += goles_visita
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

    aux_xg_hist = {
        "id": "AUX_XG_HIST",
        "estado": ESTADO_SIN_EVIDENCIA,
        "fase": 6,
        "nota": "xG histórico: Deep Opta Cache (Fase 6). No se simula.",
    }

    if evaluados == 0:
        return {
            "V26": {
                "id": "V26", "estado": ESTADO_SIN_EVIDENCIA, "record_general": None,
                "victorias": 0, "empates": 0, "derrotas": 0, "duelos_evaluados": 0,
                "nota": SIN_ANTECEDENTES_DIRECTOS,
            },
            "V27": {
                "id": "V27", "estado": ESTADO_SIN_EVIDENCIA,
                "delta_goles": None, "delta_goles_local": None, "delta_goles_visita": None,
                "magnitud_absoluta": None, "beneficiario": None,
                "saldo_descriptivo": SIN_ANTECEDENTES_DIRECTOS,
                "goles_favor": 0, "goles_contra": 0,
                "nota": "Ley Zero-H2H [LN-QBE-020-B]: ausencia de evidencia no es empate.",
            },
            "V28": {
                "id": "V28", "estado": ESTADO_SIN_EVIDENCIA,
                "record_sede": SIN_ANTECEDENTES_SEDE, "duelos_con_sede": 0,
                "visitante_victorias": 0, "visitante_empates": 0, "visitante_derrotas": 0,
                "nota": "Ningún duelo acredita la sede evaluada.",
            },
            "AUX_XG_HIST": aux_xg_hist,
        }

    delta = goles_favor - goles_contra
    if delta > 0:
        beneficiario = "LOCAL"
        saldo = f"{local_nombre} (+{delta})"
    elif delta < 0:
        beneficiario = "VISITANTE"
        saldo = f"{visita_nombre} (+{abs(delta)})"
    else:
        beneficiario = "EQUILIBRADO"
        saldo = "EQUILIBRADO (0)"

    return {
        "V26": {
            "id": "V26", "estado": ESTADO_EVALUADO,
            "record_general": f"{victorias}V - {empates}E - {derrotas}D",
            "victorias": victorias, "empates": empates, "derrotas": derrotas,
            "duelos_evaluados": evaluados,
            "nota": "Récord del local evaluado (perspectiva del fixture) [LN-QBE-105].",
        },
        "V27": {
            "id": "V27", "estado": ESTADO_EVALUADO,
            # `delta_goles` es el alias público del DTO de inspección; ambos valores son la
            # MISMA magnitud (cero doble fuente de verdad).
            "delta_goles": delta,
            "delta_goles_local": delta,
            "delta_goles_visita": -delta,          # antisimetría exacta [LN-QBE-106]
            "magnitud_absoluta": abs(delta),
            "beneficiario": beneficiario,
            "saldo_descriptivo": saldo,
            "goles_favor": goles_favor, "goles_contra": goles_contra,
            "nota": "ΔG = Σ(GL − GV); ventaja atribuida al bando beneficiario [LN-QBE-106].",
        },
        "V28": {
            "id": "V28", "estado": ESTADO_EVALUADO,
            "record_sede": (
                f"{visitante_victorias}V - {visitante_empates}E - {visitante_derrotas}D (Visita)"
                if con_sede else SIN_ANTECEDENTES_SEDE
            ),
            "duelos_con_sede": con_sede,
            "visitante_victorias": visitante_victorias,
            "visitante_empates": visitante_empates,
            "visitante_derrotas": visitante_derrotas,
            "nota": "Récord del visitante en la sede evaluada (es_local_sede is True) [LN-QBE-105].",
        },
        "AUX_XG_HIST": aux_xg_hist,
    }


# ═════════════════════════════════════════════════════════════════════════════════════════════
# ACCESO DE SÓLO LECTURA (SQLite 3NF + corpus congelado) — CERO ESCRITURA
# ═════════════════════════════════════════════════════════════════════════════════════════════
def _numero(valor: Any) -> Optional[float]:
    """Coerción estricta a float (excluye bool, que en Python es subclase de int)."""
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return None
    return float(valor)


def _simplex(origen: Any, clave_local: str, clave_empate: str, clave_visita: str) -> Optional[Dict[str, float]]:
    """Extrae un símplex con las claves canónicas del sandbox (`p_visitante`, nunca `p_visita`)."""
    if not isinstance(origen, dict):
        return None
    p_local = _numero(origen.get(clave_local))
    p_empate = _numero(origen.get(clave_empate))
    p_visitante = _numero(origen.get(clave_visita))
    if p_local is None or p_empate is None or p_visitante is None:
        return None
    return {"p_local": p_local, "p_empate": p_empate, "p_visitante": p_visitante}


def _json_dict(valor: Any) -> Dict[str, Any]:
    """Normaliza columnas JSON que puedan llegar como texto (SQLite crudo) o dict (ORM)."""
    if isinstance(valor, dict):
        return valor
    if isinstance(valor, str):
        try:
            cargado = json.loads(valor)
        except ValueError:
            return {}
        return cargado if isinstance(cargado, dict) else {}
    return {}


def _fixture_desde_entrada(
    entrada: Dict[str, Any], jornada: Any, snapshot_id: Any, actualizado: Any
) -> Dict[str, Any]:
    """Proyecta una entrada de `matches_json` al contrato interno del sandbox."""
    fecha_ref = entrada.get("fecha_dt") or entrada.get("kickoff_utc")
    actualizado_txt = actualizado.isoformat() if hasattr(actualizado, "isoformat") else str(actualizado or "")
    return {
        "match_id": str(entrada.get("id_partido") or ""),
        "jornada": jornada,
        "local": entrada.get("local") or "",
        "visitante": entrada.get("visitante") or "",
        "local_slug": entrada.get("home_team_slug") or "",
        "visitante_slug": entrada.get("away_team_slug") or "",
        "fecha_ref": fecha_ref,
        "estado": entrada.get("estado") or "",
        "marcador": entrada.get("marcador_actual"),
        "origen": f"fixtures_snapshots#{snapshot_id}",
        "snapshot_actualizado": actualizado_txt,
    }


def _leer_fixture(sesion: Any, match_id: str) -> Optional[Dict[str, Any]]:
    """Localiza el fixture por `id_partido` en el snapshot más reciente (fallback: tabla `matches`).

    El snapshot es la fuente de exhibición (nombres, `fecha_dt`, marcador). La tabla `matches`
    sólo aporta `kickoff_utc` y slugs canónicos cuando el fixture no está en cartelera.
    """
    consulta = select(FixtureSnapshot).order_by(FixtureSnapshot.updated_at.desc(), FixtureSnapshot.id.desc())
    for snapshot in sesion.execute(consulta).scalars().all():
        partidos = snapshot.matches_json or []
        if isinstance(partidos, str):
            try:
                partidos = json.loads(partidos)
            except ValueError:
                continue
        for entrada in partidos:
            if isinstance(entrada, dict) and str(entrada.get("id_partido")) == str(match_id):
                return _fixture_desde_entrada(
                    entrada, snapshot.matchday, snapshot.id, snapshot.updated_at
                )

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


def _leer_poisson(sesion: Any, match_id: str) -> Tuple[Optional[Dict[str, float]], str, Dict[str, Any]]:
    """Resuelve el símplex Poisson PURO del Generador A (H-2) y la evidencia de la captura previa.

    Orden de precedencia:
      1. `audit_trace_json.simplex_poisson` → `origen_poisson = "traza_simplex_poisson"` (🟢).
      2. Columnas persistidas `p_local/p_empate/p_visitante` → `"distribucion_persistida"` (🟡,
         posible símplex ya fusionado en capturas previas a `[LN-QBE-104]`).
    """
    fila = sesion.execute(
        select(SovereignDistribution).where(SovereignDistribution.match_id == str(match_id))
    ).scalars().first()
    if fila is None:
        return None, "sin_distribucion", {}

    traza = _json_dict(fila.audit_trace_json)
    puro = _simplex(traza.get("simplex_poisson"), "p_1", "p_X", "p_2")
    persistido = _simplex(
        {"p_local": fila.p_local, "p_empate": fila.p_empate, "p_visitante": fila.p_visitante},
        "p_local", "p_empate", "p_visitante",
    )

    captura = {
        "model_version": fila.model_version,
        "capturado_en": fila.created_at.isoformat() if getattr(fila, "created_at", None) else None,
        "epistemic_delta": _numero(fila.epistemic_delta),
        "origen_captura": traza.get("origen_captura"),
        "kernel_h2h_empirico": traza.get("kernel_h2h_empirico"),
        "simplex_persistido": persistido,
    }
    if puro is not None:
        return puro, "traza_simplex_poisson", captura
    if persistido is not None:
        return persistido, "distribucion_persistida", captura
    return None, "sin_distribucion", captura


# ═════════════════════════════════════════════════════════════════════════════════════════════
# TELEMETRÍA: VENTANA, SEMÁFOROS Y CONTRASTE DE CAPTURAS
# ═════════════════════════════════════════════════════════════════════════════════════════════
def _ventana_h2h(duelos: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Ventana efectiva publicada (conteo real, tope sellado, τ_deep y fuentes de procedencia)."""
    fuentes: List[str] = []
    for duelo in duelos:
        fuente = duelo.get("fuente") if isinstance(duelo, dict) else None
        if fuente and fuente not in fuentes:
            fuentes.append(str(fuente))
    return {
        "conteo": len(duelos),
        "limite": LIMITE_DUELOS_H2H,
        "tau_dias": float(TAU_H2H_DEEP),
        "fuentes": fuentes,
        "duelos": [dict(duelo) for duelo in duelos if isinstance(duelo, dict)],
    }


def _semaforos(
    poisson: Optional[Dict[str, float]],
    origen_poisson: str,
    duelos: Sequence[Dict[str, Any]],
    hibrida: Optional[Dict[str, float]],
    delta_epist: Optional[float],
    captura: Dict[str, Any],
) -> Dict[str, Dict[str, str]]:
    """Salud fiduciaria del experimento: seis celdas, todas derivadas de evidencia fáctica."""
    salud: Dict[str, Dict[str, str]] = {}

    if duelos:
        salud["cobertura_h2h"] = _semaforo(
            NIVEL_VERDE, f"{len(duelos)} duelos verificados (límite sellado {LIMITE_DUELOS_H2H})."
        )
    else:
        salud["cobertura_h2h"] = _semaforo(
            NIVEL_NEUTRAL, "0 duelos verificables: Ley Zero-H2H, kernel no invocado."
        )

    if poisson is None:
        salud["procedencia_poisson"] = _semaforo(
            NIVEL_NEUTRAL, "Sin distribución persistida para el fixture: fusión imposible."
        )
    elif origen_poisson == "traza_simplex_poisson":
        salud["procedencia_poisson"] = _semaforo(
            NIVEL_VERDE, "Símplex Poisson puro leído de audit_trace_json.simplex_poisson (cero doble fusión)."
        )
    else:
        salud["procedencia_poisson"] = _semaforo(
            NIVEL_AMARILLO,
            "Traza sin simplex_poisson: se usa el símplex persistido (posible fusión previa).",
        )

    if hibrida is None:
        salud["simplex"] = _semaforo(NIVEL_NEUTRAL, "Fusión no ejecutada: falta el Generador A.")
    else:
        suma = hibrida["p_local"] + hibrida["p_empate"] + hibrida["p_visitante"]
        if abs(suma - 1.0) <= TOLERANCIA_SIMPLEX:
            salud["simplex"] = _semaforo(
                NIVEL_VERDE, f"Σ = {suma:.12f} (|Σ − 1| = {abs(suma - 1.0):.2e} ≤ 1e-6)."
            )
        else:
            salud["simplex"] = _semaforo(
                NIVEL_ROJO, f"Σ = {suma:.12f}: violación de la variedad Δ² (|Σ − 1| > 1e-6)."
            )

    if delta_epist is None:
        salud["cuarentena_epist"] = _semaforo(NIVEL_NEUTRAL, "Δ_epist no calculable sin fusión.")
    elif delta_epist <= UMBRAL_CUARENTENA_EPIST:
        salud["cuarentena_epist"] = _semaforo(
            NIVEL_VERDE,
            f"Δ_epist(∞) = {delta_epist:.6f} ≤ {UMBRAL_CUARENTENA_EPIST} (τ_disp, [LN-QBE-070-B]).",
        )
    else:
        salud["cuarentena_epist"] = _semaforo(
            NIVEL_ROJO,
            f"Δ_epist(∞) = {delta_epist:.6f} > {UMBRAL_CUARENTENA_EPIST} (τ_disp, [LN-QBE-070-B]).",
        )

    mismo_dia = [
        duelo for duelo in duelos
        if isinstance(duelo, dict) and int(duelo.get("dias_antiguedad") or 0) == 0
    ]
    if mismo_dia:
        salud["futuro_ceguera"] = _semaforo(
            NIVEL_AMARILLO,
            f"{len(mismo_dia)} duelo(s) con dias_antiguedad = 0: la bóveda publica el día del "
            "kickoff (comparación por fecha, [ARCH-1.4.44]). Comportamiento sellado, no se altera.",
        )
    elif duelos:
        salud["futuro_ceguera"] = _semaforo(
            NIVEL_VERDE, "Todos los duelos son estrictamente anteriores al día del kickoff."
        )
    else:
        salud["futuro_ceguera"] = _semaforo(NIVEL_NEUTRAL, "Sin duelos: no hay exposición temporal.")

    previo = captura.get("simplex_persistido") if captura else None
    evidencia_previa = captura.get("kernel_h2h_empirico") if captura else None
    peso_previo = evidencia_previa.get("peso_h2h") if isinstance(evidencia_previa, dict) else None
    if hibrida is None or not previo:
        salud["deriva_persistida"] = _semaforo(NIVEL_NEUTRAL, "Sin captura previa comparable.")
    else:
        deriva = max(
            abs(hibrida[clave] - previo[clave])
            for clave in ("p_local", "p_empate", "p_visitante")
        )
        if deriva <= TOLERANCIA_SIMPLEX:
            salud["deriva_persistida"] = _semaforo(
                NIVEL_VERDE, f"Recálculo idéntico a la captura previa (|Δ| = {deriva:.2e})."
            )
        else:
            salud["deriva_persistida"] = _semaforo(
                NIVEL_AMARILLO,
                f"Deriva vs. captura previa |Δ| = {deriva:.6f}; w_H2H previo = {peso_previo}.",
            )
    return salud


# ═════════════════════════════════════════════════════════════════════════════════════════════
# ORQUESTADOR — CADENA REAL DEL SERVIDOR EN AISLAMIENTO (CERCA DE LA VERDAD, LEJOS DEL DOM)
# ═════════════════════════════════════════════════════════════════════════════════════════════
def _reporte_sin_fusion(status: str, motivo: str, fixture: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Reporte de degradación honesta: ninguna variable se fabrica y el símplex no se inventa."""
    local = (fixture or {}).get("local") or "LOCAL"
    visitante = (fixture or {}).get("visitante") or "VISITANTE"
    return {
        "status": status,
        "motivo": motivo,
        "match": fixture,
        "ventana_h2h": _ventana_h2h([]),
        "variables_h2h": calcular_metricas_relacionales_h2h([], local, visitante),
        "distribucion_poisson": None,
        "distribucion_h2h": {
            "p_local": None, "p_empate": None, "p_visitante": None,
            "peso_total_efectivo": 0.0, "estado": ESTADO_SIN_EVIDENCIA,
        },
        "distribucion_hibrida": None,
        "impacto_delta": {},
        "semaforos": {},
        "origen_poisson": None,
        "captura_persistida": {},
    }


def ejecutar_sandbox_partido(match_id: str) -> Dict[str, Any]:
    """`[LN-QBE-106]` Ejecuta la cadena completa sobre UN fixture y devuelve el reporte forense.

    Cadena: fixture → ventana H2H (bóveda 3NF ∪ corpus congelado) → kernel empírico →
    símplex Poisson PURO (traza) → fusión convexa sellada → semáforos. Sólo lectura.
    """
    gateway = PersistenceGateway()
    with gateway.read_session() as sesion:
        fixture = _leer_fixture(sesion, match_id)
        if fixture is None:
            return _reporte_sin_fusion(
                "NO_ENCONTRADO",
                f"El fixture '{match_id}' no existe en fixtures_snapshots ni en matches.",
                None,
            )
        if not fixture.get("fecha_ref"):
            return _reporte_sin_fusion(
                "SIN_FECHA_REFERENCIA",
                "El fixture no publica kickoff: evaluar H2H sin fecha de referencia habilitaría "
                "fuga de información. Se aborta la ventana.",
                fixture,
            )
        duelos = obtener_h2h_unificado(
            sesion,
            fixture["local_slug"] or fixture["local"],
            fixture["visitante_slug"] or fixture["visitante"],
            fixture["fecha_ref"],
        )
        poisson, origen_poisson, captura = _leer_poisson(sesion, match_id)

    kernel = calcular_matriz_h2h_empirica(duelos, tau_dias=TAU_H2H_DEEP) if duelos else None
    distribucion_h2h = {
        "p_local": float(kernel.p_local) if kernel is not None else None,
        "p_empate": float(kernel.p_empate) if kernel is not None else None,
        "p_visitante": float(kernel.p_visita) if kernel is not None else None,
        "peso_total_efectivo": float(kernel.peso_total_efectivo) if kernel is not None else 0.0,
        "estado": ESTADO_EVALUADO if kernel is not None else ESTADO_SIN_EVIDENCIA,
    }
    variables = calcular_metricas_relacionales_h2h(
        duelos, fixture["local"], fixture["visitante"]
    )

    hibrida: Optional[Dict[str, float]] = None
    impacto: Dict[str, Any] = {}
    delta_epist: Optional[float] = None
    if poisson is not None:
        fusion = fusionar_simplex_con_h2h(poisson, kernel=kernel, n_duelos=len(duelos))
        hibrida = {
            "p_local": float(fusion["p_local"]),
            "p_empate": float(fusion["p_empate"]),
            "p_visitante": float(fusion["p_visitante"]),
            "peso_h2h": float(fusion["peso_h2h"]),
            "peso_liga": float(fusion["peso_liga"]),
        }
        delta_epist = float(fusion["delta_epist"])
        if duelos:
            delta_tvd = float(
                derivar_discrepancia_epistemica(
                    poisson, duelos, tau_dias=TAU_H2H_DEEP, kernel=kernel
                )[0]
            )
        else:
            delta_tvd = 0.0
        cambios = {
            clave: round(hibrida[clave] - poisson[clave], 6)
            for clave in ("p_local", "p_empate", "p_visitante")
        }
        impacto = {
            "delta_p_local": cambios["p_local"],
            "delta_p_empate": cambios["p_empate"],
            "delta_p_visitante": cambios["p_visitante"],
            "max_abs": round(max(abs(valor) for valor in cambios.values()), 6),
            "peso_h2h": hibrida["peso_h2h"],
            "peso_liga": hibrida["peso_liga"],
            "delta_epist_infinito": round(delta_epist, 6),
            "delta_epist_tvd": round(delta_tvd, 6),
            "piso_r1_aplicado": not duelos,
        }

    if poisson is None:
        status = "SIN_DISTRIBUCION"
        motivo = (
            "Fixture y ventana resueltos, pero no existe fila en sovereign_distributions: "
            "sin Generador A no hay fusión posible."
        )
    elif not duelos:
        status = "SIN_EVIDENCIA"
        motivo = (
            "0 duelos verificables: kernel NO invocado, w_H2H = 0.0, fusión = identidad y "
            f"Δ_epist en el piso R-1 ({DELTA_EPISTEMICO_SIN_EVIDENCIA})."
        )
    else:
        status = "EXITO"
        motivo = (
            f"Ventana H2H de {len(duelos)} duelo(s) fusionada con el Generador A "
            f"(w_H2H = {hibrida['peso_h2h']:.2f})."
        )

    return {
        "status": status,
        "motivo": motivo,
        "match": fixture,
        "ventana_h2h": _ventana_h2h(duelos),
        "variables_h2h": variables,
        "distribucion_poisson": poisson,
        "distribucion_h2h": distribucion_h2h,
        "distribucion_hibrida": hibrida,
        "impacto_delta": impacto,
        "semaforos": _semaforos(poisson, origen_poisson, duelos, hibrida, delta_epist, captura),
        "origen_poisson": origen_poisson,
        "captura_persistida": captura,
    }


def _ids_de_jornada(sesion: Any, jornada: int) -> List[str]:
    """Identificadores de la jornada en el snapshot MÁS RECIENTE que la publica (orden de cartelera)."""
    consulta = select(FixtureSnapshot).order_by(FixtureSnapshot.updated_at.desc(), FixtureSnapshot.id.desc())
    for snapshot in sesion.execute(consulta).scalars().all():
        try:
            coincide = int(snapshot.matchday or 0) == int(jornada)
        except (TypeError, ValueError):
            coincide = False
        if not coincide:
            continue
        partidos = snapshot.matches_json or []
        if isinstance(partidos, str):
            try:
                partidos = json.loads(partidos)
            except ValueError:
                continue
        identificadores: List[str] = []
        for entrada in partidos:
            if not isinstance(entrada, dict):
                continue
            identificador = str(entrada.get("id_partido") or "")
            if identificador and identificador not in identificadores:
                identificadores.append(identificador)
        if identificadores:
            return identificadores
    return []


def ejecutar_sandbox_jornada(jornada: int) -> List[Dict[str, Any]]:
    """Ejecuta el sandbox sobre TODA la cartelera de una jornada (orden de snapshot preservado)."""
    gateway = PersistenceGateway()
    with gateway.read_session() as sesion:
        identificadores = _ids_de_jornada(sesion, jornada)
    return [ejecutar_sandbox_partido(identificador) for identificador in identificadores]


# ═════════════════════════════════════════════════════════════════════════════════════════════
# TABLERO ASCII DE ALTA DENSIDAD + CLI (capa [DBBD-FUNGIBLE], cero matemática propia)
# ═════════════════════════════════════════════════════════════════════════════════════════════
def _regla(caracter: str = "─") -> str:
    return caracter * ANCHO_TABLERO


def _seccion(titulo: str) -> str:
    encabezado = f"├─ {titulo} "
    return encabezado + "─" * max(0, ANCHO_TABLERO - len(encabezado))


def _porcentaje(valor: Optional[float]) -> str:
    return "   —   " if valor is None else f"{valor * 100:6.2f}%"


def _puntos(valor: Optional[float]) -> str:
    return "     —     " if valor is None else f"{valor * 100:+6.2f} pp"


def _cabecera_tablero(lineas: Sequence[str]) -> None:
    ancho_interno = ANCHO_TABLERO - 2
    print("╔" + "═" * ancho_interno + "╗")
    for linea in lineas:
        print("║" + f"  {linea}".ljust(ancho_interno)[:ancho_interno] + "║")
    print("╚" + "═" * ancho_interno + "╝")


def imprimir_tablero_consola(reporte: Dict[str, Any]) -> None:
    """Imprime el tablero forense de UN fixture (símplex de tres vías + Dimensión 11 + salud)."""
    fixture = reporte.get("match") or {}
    _cabecera_tablero([
        "Q-BE · SANDBOX H2H · PIPELINE AUTÓNOMO CLI-FIRST",
        "[LN-QBE-106] / [ARCH-1.4.45] · Read-Only · τ_deep = 540 d · Sólo lectura de la 3NF",
    ])

    if fixture:
        print(f" FIXTURE    {fixture.get('match_id')}   ·   Jornada {fixture.get('jornada')}   ·   "
              f"{fixture.get('estado') or '—'}")
        print(f" ENCUENTRO  {fixture.get('local')} vs {fixture.get('visitante')}")
        print(f" KICKOFF    {fixture.get('fecha_ref')}   ·   MARCADOR {fixture.get('marcador') or '—'}")
        print(f" FUENTE     {fixture.get('origen')}  (snapshot {fixture.get('snapshot_actualizado') or '—'})")
    print(f" ESTADO     {reporte.get('status')} — {reporte.get('motivo')}")

    if reporte.get("status") not in ("EXITO", "SIN_EVIDENCIA"):
        print(_regla("═"))
        return

    ventana = reporte.get("ventana_h2h") or {}
    print()
    print(_seccion(
        f"VENTANA H2H  N = {ventana.get('conteo', 0)}/{ventana.get('limite')}   "
        f"τ_deep = {float(ventana.get('tau_dias') or 0.0):.0f} d   "
        f"fuentes = {', '.join(ventana.get('fuentes') or ['—'])}"
    ))
    if ventana.get("duelos"):
        print("   #   FECHA         MARCADOR   ΔG    d     SEDE   FUENTE")
        for indice, duelo in enumerate(ventana["duelos"], 1):
            goles_local = duelo.get("goles_local")
            goles_visita = duelo.get("goles_visita")
            try:
                delta = f"{int(goles_local) - int(goles_visita):+d}"
            except (TypeError, ValueError):
                delta = "—"
            marcador = f"{goles_local}-{goles_visita}"
            print(
                f"   {indice:<3} {str(duelo.get('fecha') or '—'):<13} {marcador:<10} {delta:<5} "
                f"{int(duelo.get('dias_antiguedad') or 0):<5} "
                f"{'SÍ' if duelo.get('es_local_sede') is True else 'NO':<6} {duelo.get('fuente') or '—'}"
            )
    else:
        print("   ⚪ Sin enfrentamientos directos verificables (Ley Zero-H2H).")

    variables = reporte.get("variables_h2h") or {}
    v26 = variables.get("V26") or {}
    v27 = variables.get("V27") or {}
    v28 = variables.get("V28") or {}
    aux_xg_hist = variables.get("AUX_XG_HIST") or {}
    print()
    print(_seccion("DIMENSIÓN 11 · MODELADO RELACIONAL (V26 / V27 / V28)"))
    print(f"   V26  Récord del local evaluado        {v26.get('record_general') or ESTADO_SIN_EVIDENCIA}")
    print(f"   V27  ΔG = {str(v27.get('delta_goles_local') if v27.get('delta_goles_local') is not None else '—'):<4}"
          f" · Beneficiario {str(v27.get('beneficiario') or '—'):<12} {v27.get('saldo_descriptivo')}")
    print(f"   V28  Resistencia en sede (visita)     {v28.get('record_sede') or ESTADO_SIN_EVIDENCIA}")
    print(f"   AUX_XG_HIST  xG histórico                     {aux_xg_hist.get('estado') or ESTADO_SIN_EVIDENCIA} (Fase 6)")

    poisson = reporte.get("distribucion_poisson")
    h2h = reporte.get("distribucion_h2h") or {}
    hibrida = reporte.get("distribucion_hibrida")
    impacto = reporte.get("impacto_delta") or {}
    print()
    print(_seccion("SÍMPLEX Δ² · CONTRASTE DE TRES VÍAS (Poisson puro ∪ Kernel H2H ∪ Híbrida)"))
    print("   DESENLACE    POISSON PURO     KERNEL H2H       HÍBRIDA          ΔP (híbrida − poisson)")
    for clave, etiqueta in (("p_local", "LOCAL"), ("p_empate", "EMPATE"), ("p_visitante", "VISITANTE")):
        p_poisson = (poisson or {}).get(clave)
        p_h2h = h2h.get(clave)
        p_hibrida = (hibrida or {}).get(clave)
        delta_p = None if (p_poisson is None or p_hibrida is None) else p_hibrida - p_poisson
        print(
            f"   {etiqueta:<12} {_porcentaje(p_poisson)}         {_porcentaje(p_h2h)}        "
            f"{_porcentaje(p_hibrida)}        {_puntos(delta_p)}"
        )
    if hibrida is not None:
        suma = hibrida["p_local"] + hibrida["p_empate"] + hibrida["p_visitante"]
        print()
        print(
            f"   w_H2H = {hibrida['peso_h2h']:.4f}   w_Liga = {hibrida['peso_liga']:.4f}   "
            f"Δ_epist(∞) = {float(impacto.get('delta_epist_infinito') or 0.0):.6f}   "
            f"TVD = {float(impacto.get('delta_epist_tvd') or 0.0):.6f}   Σ = {suma:.12f}"
        )
        print(
            f"   Origen Poisson: {reporte.get('origen_poisson')}   "
            f"|ΔP|máx = {float(impacto.get('max_abs') or 0.0):.6f}   "
            f"Piso R-1 aplicado: {'SÍ' if impacto.get('piso_r1_aplicado') else 'NO'}"
        )
    else:
        print("\n   ⚪ Fusión no ejecutada: no existe símplex Poisson puro para el fixture.")

    semaforos = reporte.get("semaforos") or {}
    print()
    print(_seccion("SALUD FIDUCIARIA · SEMÁFOROS DEL EXPERIMENTO"))
    for nombre, celda in semaforos.items():
        print(
            f"   {celda.get('glifo', '⚪')} {nombre.upper():<20} {celda.get('nivel', '—'):<9} "
            f"{celda.get('motivo', '')}"
        )

    print()
    print(_regla("═"))
    rojos = [nombre for nombre, celda in semaforos.items() if celda.get("nivel") == NIVEL_ROJO]
    if reporte.get("status") == "SIN_EVIDENCIA":
        veredicto = (
            "SIN EVIDENCIA H2H · identidad + piso R-1 "
            "(no es cuarentena: no hay evidencia que juzgar)"
        )
    elif rojos:
        veredicto = f"CUARENTENA FIDUCIARIA · celdas rojas: {', '.join(rojos)}"
    else:
        veredicto = "EVIDENCIA H2H VIGENTE · símplex en la variedad y Δ_epist ≤ τ_disp"
    print(f" VEREDICTO  {veredicto}")
    print(_regla("═"))


def imprimir_tablero_jornada(jornada: int, reportes: Sequence[Dict[str, Any]]) -> None:
    """Cartelera compacta de la jornada: una fila por fixture con V26/V27 y Δ_epist."""
    _cabecera_tablero([
        f"CARTELERA DE MEMORIA H2H · JORNADA {jornada}",
        "[LN-QBE-106] · contraste Poisson ∪ Kernel H2H por fixture (sólo lectura)",
    ])
    if not reportes:
        print(f" ⚪ Sin fixtures para la jornada {jornada} en fixtures_snapshots.")
        return

    print()
    print("   PARTIDO          ENCUENTRO                              N   V26          "
          "V27                          Δ_epist   SEM · ESTADO")
    print("   " + "─" * (ANCHO_TABLERO - 4))
    for reporte in reportes:
        fixture = reporte.get("match") or {}
        variables = reporte.get("variables_h2h") or {}
        v26 = (variables.get("V26") or {}).get("record_general") or ESTADO_SIN_EVIDENCIA
        v27 = (variables.get("V27") or {}).get("saldo_descriptivo") or SIN_ANTECEDENTES_DIRECTOS
        conteo = (reporte.get("ventana_h2h") or {}).get("conteo", 0)
        delta = (reporte.get("impacto_delta") or {}).get("delta_epist_infinito")
        celda = (reporte.get("semaforos") or {}).get("cuarentena_epist") or {}
        encuentro = f"{fixture.get('local') or '—'} vs {fixture.get('visitante') or '—'}"
        print(
            f"   {str(fixture.get('match_id') or '—'):<16} {encuentro[:38]:<38} {conteo:<3} "
            f"{v26:<12} {v27[:28]:<28} {('—' if delta is None else f'{delta:.6f}'):<9} "
            f"{celda.get('glifo', '⚪')} {reporte.get('status')}"
        )

    exitos = sum(1 for reporte in reportes if reporte.get("status") == "EXITO")
    sin_evidencia = sum(1 for reporte in reportes if reporte.get("status") == "SIN_EVIDENCIA")
    incidencias = len(reportes) - exitos - sin_evidencia
    en_cuarentena = sum(
        1 for reporte in reportes
        if any(celda.get("nivel") == NIVEL_ROJO for celda in (reporte.get("semaforos") or {}).values())
    )
    print()
    print(_regla("═"))
    print(
        f" RESUMEN    {len(reportes)} fixture(s) · {exitos} con evidencia · "
        f"{sin_evidencia} sin evidencia (Zero-H2H) · {incidencias} incidencia(s) · "
        f"{en_cuarentena} en cuarentena (🔴)"
    )
    print(_regla("═"))


# ═════════════════════════════════════════════════════════════════════════════════════════════
# INTERFAZ DE LÍNEA DE COMANDOS
# ═════════════════════════════════════════════════════════════════════════════════════════════
def _construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.laboratorio.sandbox_h2h_pipeline",
        description=(
            "[LN-QBE-106] Sandbox H2H CLI-First: Poisson puro ∪ kernel H2H sobre la 3NF "
            "(sólo lectura, cero FastAPI, cero DOM)."
        ),
    )
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument(
        "--partido", metavar="MATCH_ID",
        help="Identificador canónico del fixture (p. ej. LIGAMX-J11-07).",
    )
    grupo.add_argument(
        "--jornada", type=int, metavar="N",
        help="Número de jornada de la cartelera activa (p. ej. 11).",
    )
    parser.add_argument(
        "--json", action="store_true", dest="como_json",
        help="Emite el reporte estructurado en JSON (sin tablero ASCII).",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    argumentos = _construir_parser().parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    try:
        if argumentos.partido:
            reporte = ejecutar_sandbox_partido(argumentos.partido)
            if argumentos.como_json:
                print(json.dumps(reporte, ensure_ascii=False, indent=2, default=str))
            else:
                imprimir_tablero_consola(reporte)
            return 0 if reporte.get("status") in ("EXITO", "SIN_EVIDENCIA") else 1

        reportes = ejecutar_sandbox_jornada(argumentos.jornada)
        if argumentos.como_json:
            print(json.dumps(
                {"jornada": argumentos.jornada, "resultados": reportes},
                ensure_ascii=False, indent=2, default=str,
            ))
        else:
            imprimir_tablero_jornada(argumentos.jornada, reportes)
        if not reportes:
            return 1
        return 0 if all(r.get("status") in ("EXITO", "SIN_EVIDENCIA") for r in reportes) else 1
    except Exception as exc:  # frontera del CLI: se informa el fallo, jamás se silencia
        logger.error("Fallo en el sandbox H2H: %s", exc)
        print(f"🔴 ERROR  {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
