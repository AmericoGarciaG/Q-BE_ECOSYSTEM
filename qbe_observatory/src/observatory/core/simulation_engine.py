# -*- coding: utf-8 -*-
"""
[LN-QBE-107] / [ARCH-1.4.46] SANDBOX DE RENTABILIDAD — SIMULADOR RETROSPECTIVO DEL FONDO.
[LN-QBE-113] / [ARCH-1.4.52] VETO FIDUCIARIO SELECTIVO POR FAMILIA ESTRATÉGICA.
[LN-QBE-115] / [ARCH-1.4.53] COTA UNDERDOG LEY 3, ESCUDO DE ALTITUD Y TRINIDAD DE CERTEZA.

Misión
------
Cerrar el circuito fiduciario: tomar las decisiones YA congeladas en la bóveda 3NF
(estrategia, partición y stake), cruzarlas con los marcadores oficiales consumados y emitir
el ESTADO DE RESULTADOS de la cartera —PnL, ROI, máximo drawdown, tasa de preservación V=0 y
proyección anualizada a 40 jornadas— sin FastAPI, sin DOM y sin Playwright.

Régimen: `[HÍBRIDO DUAL-TRACK]`
* `[DIRGEN-STRICT]`: el triaje, la contracción fiduciaria, la probabilidad efectiva, el
  ordenamiento lexicográfico, el sizing monótono y la partición dutching NO se reimplementan:
  se invocan VERBATIM desde `src.core.contracts.portfolio_math`.
* `[DBBD-FUNGIBLE]`: composición del pipeline, CLI (`--bankroll` / `--modo` / `--jornadas` /
  `--sin-familia-r` / `--excluir` / `--gamma` / `--certeza` / `--modo-cobertura` / `--json`) y
  tablero ASCII.

Axiomas operativos
------------------
1. **Sólo lectura:** `PersistenceGateway.read_session()`. Prohibido escribir en
   `data/qbe_database.db`; prohibido abrir red. El módulo es una función pura de la bóveda.
2. **Ventanilla retrospectiva declarada:** el triaje se alimenta con `es_operable = True`
   (idéntico al carril de Backtesting `[ARCH-1.4.35]`: la liquidación real EXIGE el resultado
   consumado) y con el `epistemic_delta` FÁCTICO de la bóveda bajo guarda de dominio
   (`[LN-QBE-115]`): `0.0 <= Δ <= 1.0` ⇒ valor real; fuera de dominio o ausente ⇒ fallback
   legislado `0.02` de `[LN-QBE-070-C]`. La fuente efectiva se declara en `nota_paridad`.
3. **Cero fabricación de resultados:** el único oráculo es `matches.score_home` / `score_away`.
   Sin marcador la posición se declara `NO_LIQUIDABLE` con capital devuelto (jamás un `0-0`).
4. **Instrumento de medición, no de optimización:** no recalibra parámetros, no reentrena
   modelos y no altera una sola fila de la bóveda. Γ, el Slider de Certeza y el modo δ se
   TRANSPORTAN y se aplican; jamás se optimizan dentro del instrumento.
5. **Paridad declarada:** las familias con cobertura (H1/H2/R1/R2) se particionan con
   `calcular_particion_dutching_dinamico` (`[LN-QBE-077-B/C/D]`); el modo `DEF` degenera
   exactamente en la ley V=0 de `[LN-QBE-070]`. La rama R2 del motor vivo usa ponderación
   inversa de probabilidad y esa divergencia se publica en el reporte.
6. **Veto fiduciario selectivo (`[LN-QBE-113]`):** la exclusión intercepta el resultado del
   triaje canónico DESPUÉS del triaje y ANTES del ordenamiento lexicográfico, del sizing monótono
   y del dutching. El código vetado colapsa atómicamente a `QBE-00` / "Veto Fiduciario Selectivo"
   con `alpha = 0.0`, no absorbe capital y se declara en `descartes` con `veto_fiduciario = True`.
   Cero mutación de `portfolio_math`: el veto es orquestación, no aritmética.
7. **Escudo de Altitud (`[LN-QBE-115]`):** ΔAlt⁺ se deriva del catálogo inmutable
   `CATALOGO_ALTITUDES_LIGAMX` de `[LN-QBE-109]` (`altitud_estadio(home_slug)`). `matches_json`
   no transporta altitud: sin catálogo ⇒ `0.0` (el escudo NO se evalúa; cero veto fabricado).
8. **Trinidad de Certeza §5.10 (`[LN-QBE-115]`):** el Slider de Certeza es un filtro ACTIVO de
   admisión. `>= 90%` Conservador (sólo Híbridas con cobertura) · `80-90%` Balanceado (veta
   Familia R y `QBE-D2`) · `< 80%` Crecimiento (cartera plena). `0.0` es la identidad neutra que
   reproduce la línea base. Sus abstenciones se cuentan aparte (`vetos_certeza_aplicados`).

Uso:
    python -m scripts.laboratorio.sandbox_rentabilidad_pipeline --bankroll 10000
    python -m scripts.laboratorio.sandbox_rentabilidad_pipeline --jornadas 1-11 --modo plano
    python -m scripts.laboratorio.sandbox_rentabilidad_pipeline --jornadas 1-11 --json
    python -m scripts.laboratorio.sandbox_rentabilidad_pipeline --jornadas 1-11 --sin-familia-r
    python -m scripts.laboratorio.sandbox_rentabilidad_pipeline --jornadas 1-11 --excluir QBE-C1,QBE-C2
    python -m scripts.laboratorio.sandbox_rentabilidad_pipeline --jornadas 1-11 --certeza 90 --modo-cobertura BAL
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
from src.core.contracts.portfolio_math import (
    CAP_UNDERDOG_LEY3_PCT,
    FAMILIAS_CON_COBERTURA,
    UMBRAL_DOMINANCIA_VISITANTE_PCT,
    UMBRAL_VETO_ALTITUD_METROS,
    asignar_capital_monotono_cartera,
    calcular_particion_dutching_dinamico,
    calcular_probabilidad_exito_estrategia,
    contraer_distribucion_fiduciaria,
    ordenar_cartera_por_certeza_lexicografica,
    triaje_determinista_9_estrategias,
)
from src.storage.gateway import PersistenceGateway
from src.storage.models import FixtureSnapshot, Match, SovereignDistribution

logger = logging.getLogger("SandboxRentabilidad")

# ── Parámetros legislados ──────────────────────────────────────────────────────────────────
GAMMA_BASE = 0.67                        # [LN-QBE-060-B] umbral de masa Capa 0
GAMMA_MIN, GAMMA_MAX = 0.67, 0.75        # [LN-QBE-059] dominio legislado del slider Γ
DELTA_EPIST_LEGISLADO = 0.02             # [LN-QBE-070-C] estrato R-1 (fallback de Δ_epist)
CAP_MAX_PARTIDO_PCT = 0.08               # [LN-QBE-082] tope individual
CAP_MAX_CARTERA_PCT = 0.25               # [LN-QBE-082] bolsa de jornada
PISO_VENTANILLA_MXN = 2.00               # [LN-QBE-071] piso por boleto
PISO_BIVARIADO_MXN = 4.00                # [LN-QBE-071-B] piso de cobertura (2 leguas)
JORNADAS_POR_TEMPORADA = 40              # horizonte de anualización declarado
TOLERANCIA_V0_MXN = 0.08                 # holgura de redondeo de la indemnidad V=0
PATRIMONIO_BASE_SHIELD = 10000.0         # base de certificación del Juez
ANCHO_TABLERO = 94

# ── Partición canónica de la liquidación factual (colectivamente exhaustiva) ───────────────
ESCENARIO_VICTORIA = "VICTORIA_FAVORITO"
ESCENARIO_COBERTURA_V0 = "COBERTURA_EMPATE_V0"
ESCENARIO_DOBLE_COBRO_PA = "DOBLE_COBRO_PA"
ESCENARIO_RUPTURA = "RUPTURA_P_LOW"
ESCENARIO_NO_LIQUIDABLE = "NO_LIQUIDABLE"
ESCENARIOS_CANONICOS: Tuple[str, ...] = (
    ESCENARIO_VICTORIA, ESCENARIO_COBERTURA_V0, ESCENARIO_DOBLE_COBRO_PA,
    ESCENARIO_RUPTURA, ESCENARIO_NO_LIQUIDABLE,
)
ESTADOS_CON_MARCADOR = ("FINALIZADO", "FINISHED", "CONCLUIDO")
MODOS_VALIDOS = ("compuesto", "plano")

# ── [LN-QBE-113] Veto Fiduciario Selectivo ────────────────────────────────────────────────
CODIGO_VETO_FIDUCIARIO = "QBE-00"
NOMBRE_VETO_FIDUCIARIO = "Veto Fiduciario Selectivo"
FAMILIA_R_CODIGOS: Tuple[str, ...] = ("QBE-R1", "QBE-R2")

# ── [LN-QBE-115] Cobertura dinámica δ y Trinidad de Certeza §5.10 ─────────────────────────
MODOS_COBERTURA_VALIDOS: Tuple[str, ...] = ("DEF", "BAL", "AGR")
MODO_COBERTURA_DEF = "DEF"
UMBRAL_CERTEZA_CONSERVADOR = 90.0        # >= 90.0 ⇒ sólo Híbridas con cobertura
UMBRAL_CERTEZA_BALANCEADO = 80.0         # >= 80.0 ⇒ veta Familia R y QBE-D2
MODO_CERTEZA_CRECIMIENTO = "CRECIMIENTO"
MODO_CERTEZA_BALANCEADO = "BALANCEADO"
MODO_CERTEZA_CONSERVADOR = "CONSERVADOR"
NOMBRE_VETO_CERTEZA = "Veto Trinidad de Certeza"
VETOS_CERTEZA_CONSERVADOR: Tuple[str, ...] = ("QBE-D1", "QBE-D2", "QBE-R1", "QBE-R2")
VETOS_CERTEZA_BALANCEADO: Tuple[str, ...] = ("QBE-R1", "QBE-R2", "QBE-D2")
CERTEZA_NEUTRA_PCT = 0.0                 # identidad: reproduce la línea base sin filtro


def _a_float(valor: Any, defecto: float = 0.0) -> float:
    """Coerción numérica defensiva: cero invención, sólo lectura tolerante."""
    try:
        if valor is None:
            return defecto
        return float(valor)
    except (TypeError, ValueError):
        return defecto


def _marcador_valido(goles_local: Any, goles_visitante: Any) -> bool:
    return goles_local is not None and goles_visitante is not None


def _normalizar_exclusiones(codigos: Optional[Sequence[str]]) -> Tuple[str, ...]:
    """`[LN-QBE-113]` Normaliza la lista de veto: mayúsculas, sin vacíos, dedup y orden estable.

    Cero inferencia: sólo se veta lo que el operador declara. La lista vacía es el estado neutro
    (simulación íntegra, paridad exacta con la línea base de `[LN-QBE-107]`). El orden determinista
    garantiza que el reporte y el tablero sean reproducibles bit a bit.
    """
    if not codigos:
        return ()
    normalizados = {
        str(codigo).strip().upper() for codigo in codigos if str(codigo or "").strip()
    }
    return tuple(sorted(normalizados))


def _resolver_trinidad_certeza(target_certeza_pct: float) -> Tuple[str, Tuple[str, ...]]:
    """`[LN-QBE-115]` Resuelve la banda de la Trinidad de Certeza §5.10 y su tupla de vetos."""
    certeza = _a_float(target_certeza_pct, CERTEZA_NEUTRA_PCT)
    if certeza >= UMBRAL_CERTEZA_CONSERVADOR:
        return (MODO_CERTEZA_CONSERVADOR, VETOS_CERTEZA_CONSERVADOR)
    if certeza >= UMBRAL_CERTEZA_BALANCEADO:
        return (MODO_CERTEZA_BALANCEADO, VETOS_CERTEZA_BALANCEADO)
    return (MODO_CERTEZA_CRECIMIENTO, ())


def _delta_epist_factico(distribucion: Any) -> Tuple[float, str]:
    """`[LN-QBE-115]` Δ_epist fáctico con guarda de dominio y fallback legislado `0.02`.

    Si `0.0 <= Δ <= 1.0` se usa el valor fáctico de `sovereign_distributions`; cualquier otro
    caso (legado no normalizado, `None`, `NaN`) degenera al estrato R-1 de `[LN-QBE-070-C]`.
    Cero inferencia: la unidad sólo se acepta dentro de su dominio probabilístico.
    """
    valor = getattr(distribucion, "epistemic_delta", None) if distribucion is not None else None
    try:
        delta = float(valor) if valor is not None else None
    except (TypeError, ValueError):
        delta = None
    if delta is None or not (0.0 <= delta <= 1.0):
        return (DELTA_EPIST_LEGISLADO, "fallback")
    return (delta, "factico")


def _delta_altitud_metros(home_slug: Any, away_slug: Any) -> float:
    """`[LN-QBE-115]` ΔAlt⁺ unidireccional desde el catálogo inmutable de `[LN-QBE-109]`.

    Club fuera de catálogo ⇒ `0.0` (SIN EVIDENCIA): el escudo NO se evalúa y jamás se fabrica
    un veto de altitud. Import diferido para no cargar el plano contextual en cada arranque.
    """
    from src.observatory.core.context_provider import altitud_estadio

    altitud_local = altitud_estadio(home_slug)
    altitud_visita = altitud_estadio(away_slug)
    if altitud_local is None or altitud_visita is None:
        return 0.0
    return round(max(0.0, float(altitud_local) - float(altitud_visita)), 4)


def _familias_con_cobertura() -> Tuple[str, ...]:
    """Lectura directa del manifiesto sellado: cero lista paralela hardcodeada."""
    return tuple(FAMILIAS_CON_COBERTURA)


def _cubre_empate(posicion: Dict[str, Any]) -> bool:
    """La cobertura de tablas la dicta la FAMILIA, jamás el tamaño del boleto."""
    if "cubre_empate" in posicion:
        return bool(posicion["cubre_empate"])
    return str(posicion.get("familia") or "").upper() in _familias_con_cobertura()


def _lado_de_ataque(codigo: str, p_local: float, p_visitante: float) -> Optional[str]:
    """Bando que monetiza el boleto de ataque según la partición sellada de cada familia.

    * H1/H2/D1/D2 → el FAVORITO soberano (`p_local >= p_visitante`).
    * R1 → el underdog LOCAL; R2 → el underdog VISITANTE ([LN-QBE-060-B] pasos 1-3).
    * C1/C2 → mercados derivados sin oráculo 1X2 certificado: no liquidables aquí.
    """
    codigo = str(codigo or "").upper().strip()
    if codigo == "QBE-R1":
        return "LOCAL"
    if codigo == "QBE-R2":
        return "VISITANTE"
    if codigo in ("QBE-D1", "QBE-H1"):
        return "LOCAL"
    if codigo in ("QBE-D2", "QBE-H2"):
        return "VISITANTE"
    if codigo in ("QBE-C1", "QBE-C2"):
        return None
    return "LOCAL" if float(p_local) >= float(p_visitante) else "VISITANTE"


# ═════════════════════════════════════════════════════════════════════════════════════════════
# LIQUIDACIÓN FACTUAL ([LN-QBE-107] paso 5) — partición colectivamente exhaustiva de desenlaces
# ═════════════════════════════════════════════════════════════════════════════════════════════
def liquidar_posicion_factual(
    posicion: Dict[str, Any],
    goles_local: Optional[int],
    goles_visitante: Optional[int],
    ventaja_maxima_favorito: Optional[int] = None,
) -> Dict[str, Any]:
    """`[LN-QBE-107]` Liquida una posición contra el marcador oficial consumado.

    Puro y determinista. No fabrica marcadores: sin evidencia declara `NO_LIQUIDABLE` y
    devuelve el capital. Las cinco salidas son mutuamente excluyentes y exhaustivas:
    `VICTORIA_FAVORITO` = B_prio·O_ataque · `COBERTURA_EMPATE_V0` = B_seg·O_empate ≈ B_i ·
    `DOBLE_COBRO_PA` = ambas piernas · `RUPTURA_P_LOW` = $0.00 · `NO_LIQUIDABLE` = capital
    devuelto con PnL $0.00.

    El Pago Anticipado exige testigo fáctico: margen final >= 2 goles del bando de ataque
    (necesariamente lideró por +2 en algún instante). En tablas el único testigo válido es la
    traza in-play opcional `ventaja_maxima_favorito`; sin ella la acreditación se declara
    negativa con motivo explícito y se liquida V=0 puro.
    """
    inversion = round(_a_float(posicion.get("inversion_total")), 2)
    b_prio = round(_a_float(posicion.get("b_prio")), 2)
    b_seg = round(_a_float(posicion.get("b_seg")), 2)
    o_ata = _a_float(posicion.get("cuota_ataque"))
    o_emp = _a_float(posicion.get("cuota_empate"))
    lado = str(posicion.get("lado_ataque") or "LOCAL").upper()
    pa_activo = bool(posicion.get("pago_anticipado"))
    cubre = _cubre_empate(posicion)

    base = {
        "id_partido": posicion.get("id_partido"),
        "familia": posicion.get("familia"),
        "inversion_total": inversion,
        "b_prio": b_prio,
        "b_seg": b_seg,
        "lado_ataque": lado,
        "pago_anticipado": pa_activo,
        "marcador_local": goles_local,
        "marcador_visitante": goles_visitante,
        "pago_anticipado_acreditado": False,
        "testigo_pago_anticipado": "sin_pago_anticipado" if not pa_activo else "",
        "capital_devuelto": False,
    }

    # ── Guarda de degradación honesta: sin marcador oficial no hay liquidación ──────────────
    if not _marcador_valido(goles_local, goles_visitante):
        return {
            **base,
            "escenario": ESCENARIO_NO_LIQUIDABLE,
            "cobro_mxn": 0.0,
            "pnl_mxn": 0.0,
            "roi_pct": 0.0,
            "capital_devuelto": True,
            "margen_goles": None,
            "motivo": "Sin marcador oficial consumado en la bóveda: capital devuelto (cero 0-0 fabricado).",
        }

    gl, gv = int(goles_local), int(goles_visitante)
    empate = gl == gv
    ganador = None if empate else ("LOCAL" if gl > gv else "VISITANTE")
    margen = abs(gl - gv)

    escenario = ESCENARIO_RUPTURA
    cobro = 0.0
    testigo = ""
    acreditado = False

    if empate and cubre:
        # ── Tablas en familia con cobertura: indemnidad V=0 (o Doble Cobro con PA acreditado) ─
        if pa_activo:
            if ventaja_maxima_favorito is not None and int(ventaja_maxima_favorito) >= 2:
                testigo = "traza_in_play_ventaja_2"
                acreditado = True
            else:
                testigo = "sin_traza_in_play"
        if acreditado:
            cobro = round((b_prio * o_ata) + (b_seg * o_emp), 2)
            escenario = ESCENARIO_DOBLE_COBRO_PA
        else:
            cobro = round(b_seg * o_emp, 2)
            escenario = ESCENARIO_COBERTURA_V0
    elif (not empate) and ganador == lado:
        # ── La pierna de ataque gana: única vía de ganancia estructural ────────────────────
        cobro = round(b_prio * o_ata, 2)
        escenario = ESCENARIO_VICTORIA
        if pa_activo:
            if margen >= 2:
                acreditado = True
                testigo = "margen_final_ge_2"
            else:
                testigo = "margen_final_lt_2"
    else:
        # ── Gana el bando no cubierto (o tablas sin cobertura): pérdida íntegra ────────────
        escenario = ESCENARIO_RUPTURA
        cobro = 0.0
        if pa_activo and not empate:
            testigo = "bando_de_ataque_no_ganador"

    pnl = round(cobro - inversion, 2)
    roi = round((pnl / inversion) * 100.0, 2) if inversion > 0 else 0.0
    motivo = ""
    if escenario == ESCENARIO_RUPTURA:
        motivo = "Tablas sin cobertura" if empate else "Ganó el bando no cubierto por la cartera"
    elif escenario == ESCENARIO_COBERTURA_V0 and pa_activo:
        motivo = "PA sin traza in-play: se liquida V=0 puro (cero testigo fabricado)"

    return {
        **base,
        "escenario": escenario,
        "cobro_mxn": cobro,
        "pnl_mxn": pnl,
        "roi_pct": roi,
        "pago_anticipado_acreditado": acreditado,
        "testigo_pago_anticipado": testigo or base["testigo_pago_anticipado"],
        "margen_goles": margen,
        "motivo": motivo,
    }


# ═════════════════════════════════════════════════════════════════════════════════════════════
# CARGA DE LA BÓVEDA ([LN-QBE-107] paso 1) — función pura de sólo lectura
# ═════════════════════════════════════════════════════════════════════════════════════════════
def _resolver_partido(
    fixture: Dict[str, Any],
    indice_por_id: Dict[str, Match],
    indice_por_slug: Dict[Tuple[str, str], Match],
) -> Optional[Match]:
    """Resuelve la fila oficial de `matches` por `id_partido` y, en su defecto, por slugs."""
    mid = str(fixture.get("id_partido") or "").strip()
    if mid and mid in indice_por_id:
        return indice_por_id[mid]
    slugs = (
        str(fixture.get("home_team_slug") or "").strip(),
        str(fixture.get("away_team_slug") or "").strip(),
    )
    if slugs[0] and slugs[1]:
        return indice_por_slug.get(slugs)
    return None


def _cargar_jornada(sesion: Any, jornada: int) -> Dict[str, Any]:
    """Carga la captura congelada de la jornada, sus marcadores oficiales y sus distribuciones.

    Estrictamente de sólo lectura. Un snapshot ausente no es un error fatal: la jornada se
    declara sin cartelera y el capital permanece intacto (cero invención de partidos).
    """
    snapshot = sesion.execute(
        select(FixtureSnapshot)
        .where(FixtureSnapshot.matchday == int(jornada))
        .order_by(FixtureSnapshot.updated_at.desc())
    ).scalars().first()

    fixtures: List[Dict[str, Any]] = []
    if snapshot is not None and snapshot.matches_json:
        fixtures = [f for f in snapshot.matches_json if isinstance(f, dict)]

    identificadores = [str(f.get("id_partido")) for f in fixtures if f.get("id_partido")]
    partidos: Sequence[Match] = []
    if identificadores:
        partidos = sesion.execute(select(Match).where(Match.id.in_(identificadores))).scalars().all()
    if not partidos:
        # Respaldo declarado: la jornada oficial por `matchday_num` (cero coincidencia inventada).
        partidos = sesion.execute(
            select(Match).where(Match.matchday_num == int(jornada))
        ).scalars().all()

    indice_por_id: Dict[str, Match] = {str(p.id): p for p in partidos}
    indice_por_slug: Dict[Tuple[str, str], Match] = {
        (str(p.home_team_slug), str(p.away_team_slug)): p for p in partidos
    }

    distribuciones: Dict[str, SovereignDistribution] = {}
    if identificadores:
        filas = sesion.execute(
            select(SovereignDistribution).where(SovereignDistribution.match_id.in_(identificadores))
        ).scalars().all()
        distribuciones = {str(d.match_id): d for d in filas}
    if not distribuciones and partidos:
        filas = sesion.execute(
            select(SovereignDistribution).where(
                SovereignDistribution.match_id.in_([str(p.id) for p in partidos])
            )
        ).scalars().all()
        distribuciones = {str(d.match_id): d for d in filas}

    return {
        "jornada": int(jornada),
        "fixtures": fixtures,
        "indice_por_id": indice_por_id,
        "indice_por_slug": indice_por_slug,
        "distribuciones": distribuciones,
        "snapshot_capturado": snapshot.updated_at.isoformat() if snapshot is not None and snapshot.updated_at else None,
    }


# ═════════════════════════════════════════════════════════════════════════════════════════════
# CONSTRUCCIÓN DE CARTERA ([LN-QBE-107] pasos 2-4) — triaje, sizing y partición de boletos
# ═════════════════════════════════════════════════════════════════════════════════════════════
def _construir_cartera_jornada(
    cargado: Dict[str, Any],
    base_capital: float,
    excluir_estrategias: Sequence[str] = (),
    gamma: float = GAMMA_BASE,
    modo_cobertura: str = MODO_COBERTURA_DEF,
    familias_veto_certeza: Sequence[str] = (),
    modo_certeza: str = MODO_CERTEZA_CRECIMIENTO,
) -> Dict[str, Any]:
    """Construye y liquida la cartera de una jornada sobre la base de capital declarada.

    El pipeline reproduce el carril de Backtesting de la ventanilla (`[ARCH-1.4.35]`): triaje
    canónico → **veto fiduciario selectivo (`[LN-QBE-113]`)** → contracción fiduciaria →
    ordenamiento lexicográfico → sizing monótono → dutching. Cero fórmulas propias: todas las
    magnitudes provienen de `portfolio_math`.
    """
    jornada = int(cargado["jornada"])
    # Normalización defensiva en la frontera del veto (`[LN-QBE-113]`): idempotente, garantiza que
    # un llamador directo con minúsculas o duplicados no anule silenciosamente la abstención.
    vetos = frozenset(_normalizar_exclusiones(excluir_estrategias))
    vetos_certeza = frozenset(_normalizar_exclusiones(familias_veto_certeza))
    candidatos: List[Dict[str, Any]] = []
    descartes: List[Dict[str, Any]] = []
    origen_delta_conteo: Dict[str, int] = {"factico": 0, "fallback": 0}

    for fixture in cargado["fixtures"]:
        mid = str(fixture.get("id_partido") or "").strip()
        if not mid:
            continue
        partido = _resolver_partido(fixture, cargado["indice_por_id"], cargado["indice_por_slug"])
        momios = fixture.get("momios") if isinstance(fixture.get("momios"), dict) else {}
        o_l = _a_float(momios.get("L"))
        o_e = _a_float(momios.get("E"))
        o_v = _a_float(momios.get("V"))

        distribucion = cargado["distribuciones"].get(mid)
        p_l = fixture.get("p_local") if fixture.get("p_local") is not None else (
            distribucion.p_local if distribucion is not None else None)
        p_e = fixture.get("p_empate") if fixture.get("p_empate") is not None else (
            distribucion.p_empate if distribucion is not None else None)
        p_v = fixture.get("p_visitante") if fixture.get("p_visitante") is not None else (
            distribucion.p_visitante if distribucion is not None else None)

        local = str(fixture.get("local") or "Local")
        visitante = str(fixture.get("visitante") or "Visita")

        if p_l is None or p_e is None or p_v is None:
            descartes.append({
                "id_partido": mid, "partido": f"{local} vs {visitante}",
                "motivo": "Sin distribución soberana fáctica en la bóveda",
            })
            continue
        if min(o_l, o_e, o_v) <= 1.0:
            descartes.append({
                "id_partido": mid, "partido": f"{local} vs {visitante}",
                "motivo": "Sin cuotas 1X2 fácticas: cuarentena fiduciaria (GOVERNANCE-01)",
            })
            continue

        pago_anticipado = bool(
            momios.get("pa") or momios.get("pago_anticipado") or fixture.get("pago_anticipado")
        )
        # ── [LN-QBE-115] Δ_epist fáctico (guarda de dominio) y ΔAlt⁺ del catálogo inmutable ──
        delta_epist, origen_delta = _delta_epist_factico(distribucion)
        origen_delta_conteo[origen_delta] = origen_delta_conteo.get(origen_delta, 0) + 1
        delta_alt_metros = _delta_altitud_metros(
            fixture.get("home_team_slug")
            or (partido.home_team_slug if partido is not None else None),
            fixture.get("away_team_slug")
            or (partido.away_team_slug if partido is not None else None),
        )
        payload = {
            "p_local": float(p_l),
            "p_empate": float(p_e),
            "p_visitante": float(p_v),
            # Ventanilla retrospectiva: la liquidación real exige el resultado consumado.
            "es_operable": True,
            "delta_epist": delta_epist,
            "delta_alt_metros": delta_alt_metros,
            "p_under_25": _a_float(fixture.get("p_under_25")),
            "lambda_home": _a_float(fixture.get("lambda_home")),
            "lambda_away": _a_float(fixture.get("lambda_away")),
        }
        cuotas = {
            "L": o_l, "E": o_e, "V": o_v, "pa": pago_anticipado,
            "DNB": _a_float(momios.get("DNB")),
            "Under_25": _a_float(momios.get("Under_25")),
        }

        triaje = triaje_determinista_9_estrategias(payload, cuotas, gamma=gamma)
        codigo_triaje = str(triaje.get("codigo") or CODIGO_VETO_FIDUCIARIO).upper()

        # ── [LN-QBE-113] Intercepción PRE-dimensionamiento: veto fiduciario selectivo ──────
        # El colapso a QBE-00 ocurre DESPUÉS del triaje canónico y ANTES del ordenamiento
        # lexicográfico ([LN-QBE-081]) y de la asignación monótona de capital ([LN-QBE-082]):
        # la posición vetada jamás absorbe capital y queda declarada en abstención fiduciaria.
        vetada = bool(vetos) and codigo_triaje != CODIGO_VETO_FIDUCIARIO and codigo_triaje in vetos
        # ── [LN-QBE-115] Trinidad de Certeza §5.10: filtro ACTIVO de admisión de cartera ───────
        # Intercepta en el MISMO punto pre-dimensionamiento que `[LN-QBE-113]`, pero se cuenta
        # aparte (`veto_trinidad_certeza`) para no contaminar la traza del veto selectivo.
        vetada_certeza = (
            bool(vetos_certeza)
            and codigo_triaje != CODIGO_VETO_FIDUCIARIO
            and codigo_triaje in vetos_certeza
        )
        if vetada or vetada_certeza:
            if vetada:
                nombre_veto = NOMBRE_VETO_FIDUCIARIO
                motivo_veto = f"{NOMBRE_VETO_FIDUCIARIO}: {codigo_triaje} excluida de la jornada"
            else:
                nombre_veto = NOMBRE_VETO_CERTEZA
                motivo_veto = (
                    f"{NOMBRE_VETO_CERTEZA} [{modo_certeza}] (§5.10): "
                    f"{codigo_triaje} no admitida por el nivel de certeza solicitado"
                )
            triaje = {
                **triaje,
                "codigo": CODIGO_VETO_FIDUCIARIO,
                "nombre": nombre_veto,
                "alpha": 0.0,
                "motivo": motivo_veto,
            }

        codigo = str(triaje.get("codigo") or CODIGO_VETO_FIDUCIARIO).upper()
        if codigo == CODIGO_VETO_FIDUCIARIO:
            descarte = {
                "id_partido": mid, "partido": f"{local} vs {visitante}",
                "motivo": triaje.get("motivo") or "Cuarentena / Sin Valor (QBE-00)",
                "familia": codigo,
            }
            if vetada:
                descarte["familia_vetada"] = codigo_triaje
                descarte["veto_fiduciario"] = True
            if vetada_certeza:
                descarte["familia_no_admitida"] = codigo_triaje
                descarte["veto_trinidad_certeza"] = True
            descartes.append(descarte)
            continue

        favorece_local = float(p_l) >= float(p_v)
        candidatos.append({
            "id_partido": mid,
            "partido": f"{local} vs {visitante}",
            "familia": codigo,
            "estrategia_codigo": codigo,
            "familia_nombre": str(triaje.get("nombre") or ""),
            "alpha": round(_a_float(triaje.get("alpha")), 4),
            "prob_fav": round((float(p_l) if favorece_local else float(p_v)) * 100.0, 1),
            "prob_emp": round(float(p_e) * 100.0, 1),
            "prob_und": round((float(p_v) if favorece_local else float(p_l)) * 100.0, 1),
            "odd_fav": o_l if favorece_local else o_v,
            "odd_emp": o_e,
            "odd_und": o_v if favorece_local else o_l,
            "fav_lado": "LOCAL" if favorece_local else "VISITANTE",
            "pago_anticipado": pago_anticipado,
            "delta_epist": delta_epist,
            "delta_alt_metros": delta_alt_metros,
            "marcador_local": partido.score_home if partido is not None else None,
            "marcador_visitante": partido.score_away if partido is not None else None,
            "estado_partido": str(partido.status) if partido is not None else "SIN_REGISTRO",
        })

    cartera = _dimensionar_y_liquidar(jornada, candidatos, descartes, base_capital, modo_cobertura)
    cartera["delta_epist_origen"] = dict(origen_delta_conteo)
    return cartera


def _dimensionar_y_liquidar(
    jornada: int,
    candidatos: List[Dict[str, Any]],
    descartes: List[Dict[str, Any]],
    base_capital: float,
    modo_cobertura: str = MODO_COBERTURA_DEF,
) -> Dict[str, Any]:
    """Contracción fiduciaria → orden lexicográfico → sizing monótono → dutching → liquidación."""
    if not candidatos or float(base_capital) <= 0.0:
        return {
            "jornada": jornada, "posiciones": [], "descartes": list(descartes),
            "no_liquidables": [], "inversion_total": 0.0, "capital_no_desplegado": 0.0,
            "candidatos_triaje": len(candidatos),
        }

    # ── [LN-QBE-079] Distribución fiduciaria contraída: variable derivada, jamás persistida ──
    for candidato in candidatos:
        p_fav_c, p_emp_c, p_und_c = contraer_distribucion_fiduciaria(
            candidato["prob_fav"] / 100.0,
            candidato["prob_emp"] / 100.0,
            candidato["prob_und"] / 100.0,
            candidato["delta_epist"],
        )
        candidato["prob_exito_efectiva"] = calcular_probabilidad_exito_estrategia(
            candidato["familia"], p_fav_c, p_emp_c, p_und_c
        )

    # ── [LN-QBE-081]/[LN-QBE-082] Orden por certeza y asignación monótona de capital ────────
    ordenados = ordenar_cartera_por_certeza_lexicografica(list(candidatos))
    ordenados = asignar_capital_monotono_cartera(
        ordenados,
        float(base_capital),
        cap_max_partido_pct=CAP_MAX_PARTIDO_PCT,
        cap_max_cartera_pct=CAP_MAX_CARTERA_PCT,
    )

    posiciones: List[Dict[str, Any]] = []
    no_liquidables: List[Dict[str, Any]] = []
    inversion_total = 0.0
    capital_no_desplegado = 0.0
    familias_con_cobertura = _familias_con_cobertura()

    for candidato in ordenados:
        inversion = round(_a_float(candidato.get("inversion_total")), 2)
        if inversion <= 0.0:
            continue

        familia = str(candidato["familia"]).upper()
        favorece_local = candidato["fav_lado"] == "LOCAL"
        p_local_ref = candidato["prob_fav"] if favorece_local else candidato["prob_und"]
        p_visita_ref = candidato["prob_und"] if favorece_local else candidato["prob_fav"]

        lado = _lado_de_ataque(familia, p_local_ref, p_visita_ref)
        if lado is None:
            # Mercado derivado (C1/C2) sin oráculo 1X2 certificado: capital devuelto, cero invención.
            no_liquidables.append({
                "id_partido": candidato["id_partido"], "partido": candidato["partido"],
                "familia": familia, "inversion_total": inversion,
                "motivo": "Mercado derivado sin oráculo certificado en el sandbox: capital devuelto",
            })
            capital_no_desplegado = round(capital_no_desplegado + inversion, 2)
            continue

        delta_cobertura = 0.0
        roi_favorito_pct = 0.0
        roi_empate_pct = 0.0
        if familia in familias_con_cobertura:
            # [LN-QBE-077-B/C/D] Partición dinámica sellada. El modo `DEF` degenera EXACTAMENTE en
            # la ley V=0 de [LN-QBE-070]: B_seg = B_i / O_empate y B_prio = B_i - B_seg.
            particion = calcular_particion_dutching_dinamico(
                inversion, candidato["odd_fav"], candidato["odd_emp"], modo=modo_cobertura
            )
            b_prio = particion["monto_ataque"]
            b_seg = particion["monto_seguro"]
            delta_cobertura = particion["delta_efectivo"]
            roi_favorito_pct = particion["roi_favorito_porcentaje"]
            roi_empate_pct = particion["roi_empate_porcentaje"]
            cubre_empate = True
        else:
            b_prio, b_seg, cubre_empate = inversion, 0.0, False

        # ── Pisos de ventanilla: el tope prevalece, jamás se infla la orden ────────────────
        if cubre_empate and 0.0 < b_seg < PISO_BIVARIADO_MXN:
            descartes.append({
                "id_partido": candidato["id_partido"], "partido": candidato["partido"],
                "familia": familia,
                "motivo": (f"Piso bivariado inalcanzable bajo el tope de cartera: "
                           f"B_seg ${b_seg:.2f} < ${PISO_BIVARIADO_MXN:.2f}"),
            })
            capital_no_desplegado = round(capital_no_desplegado + inversion, 2)
            continue
        if 0.0 < b_prio < PISO_VENTANILLA_MXN:
            descartes.append({
                "id_partido": candidato["id_partido"], "partido": candidato["partido"],
                "familia": familia,
                "motivo": (f"Piso de ventanilla inalcanzable: "
                           f"B_prio ${b_prio:.2f} < ${PISO_VENTANILLA_MXN:.2f}"),
            })
            capital_no_desplegado = round(capital_no_desplegado + inversion, 2)
            continue

        cuota_ataque = (
            candidato["odd_fav"] if candidato["fav_lado"] == lado else candidato["odd_und"]
        )
        posicion = {
            "id_partido": candidato["id_partido"],
            "partido": candidato["partido"],
            "familia": familia,
            "estrategia_codigo": familia,
            "familia_nombre": candidato["familia_nombre"],
            "lado_ataque": lado,
            "prob_exito_efectiva": candidato["prob_exito_efectiva"],
            "inversion_total": inversion,
            "b_prio": round(_a_float(b_prio), 2),
            "b_seg": round(_a_float(b_seg), 2),
            "cuota_ataque": round(_a_float(cuota_ataque), 2),
            "cuota_empate": round(_a_float(candidato["odd_emp"]), 2),
            "pago_anticipado": bool(candidato["pago_anticipado"]),
            "cubre_empate": cubre_empate,
            # [LN-QBE-077-B] & Invariante VIII-54: δ y ROIs proyectados viajan en la orden.
            "delta_cobertura": delta_cobertura,
            "roi_favorito_pct": roi_favorito_pct,
            "roi_empate_pct": roi_empate_pct,
        }
        liquidacion = liquidar_posicion_factual(
            posicion,
            candidato["marcador_local"],
            candidato["marcador_visitante"],
            ventaja_maxima_favorito=candidato.get("ventaja_maxima_favorito"),
        )
        posiciones.append({**posicion, **liquidacion})
        inversion_total = round(inversion_total + inversion, 2)

    return {
        "jornada": jornada,
        "posiciones": posiciones,
        "descartes": descartes,
        "no_liquidables": no_liquidables,
        "inversion_total": round(inversion_total, 2),
        "capital_no_desplegado": round(capital_no_desplegado, 2),
        "candidatos_triaje": len(candidatos),
    }


# ═════════════════════════════════════════════════════════════════════════════════════════════
# MOTOR DE SIMULACIÓN ([LN-QBE-107] pasos 3-7) — curva de bankroll, riesgo y proyección
# ═════════════════════════════════════════════════════════════════════════════════════════════
def ejecutar_simulacion_rentabilidad(
    bankroll_inicial: float = PATRIMONIO_BASE_SHIELD,
    jornadas: Optional[Sequence[int]] = None,
    modo: str = "compuesto",
    jornadas_por_temporada: int = JORNADAS_POR_TEMPORADA,
    gateway: Any = None,
    excluir_estrategias: Optional[Sequence[str]] = None,
    gamma: float = GAMMA_BASE,
    target_certeza_pct: float = CERTEZA_NEUTRA_PCT,
    modo_cobertura: str = MODO_COBERTURA_DEF,
) -> Dict[str, Any]:
    """`[LN-QBE-107]` Simula la trayectoria del fondo jornada a jornada y emite el tablero.

    `modo="compuesto"` dimensiona la jornada $j$ sobre el patrimonio real $B_{j-1}$;
    `modo="plano"` mantiene el stake nominal sobre $B_0$. Ambas modalidades respetan las cotas
    constitucionales (8% individual / 25% de jornada) porque el sizing se delega a
    `asignar_capital_monotono_cartera`. El capital que no puede desplegarse con integridad de
    piso permanece líquido y se declara en `capital_no_desplegado`.

    `[LN-QBE-113]`: `excluir_estrategias` es la lista de códigos sujetos a Veto Fiduciario
    Selectivo. El veto intercepta el triaje antes del dimensionamiento, de modo que el capital
    liberado se reasigna a las estrategias de alta convicción o queda líquido. La lista vacía
    reproduce exactamente la línea base `[LN-QBE-107]`.

    `[LN-QBE-115]`: `gamma` gobierna la Capa 0 (dominio legislado `[0.67, 0.75]`);
    `target_certeza_pct` activa la Trinidad de Certeza §5.10 como filtro de admisión
    (`0.0` = identidad neutra); `modo_cobertura` fija δ (`DEF` = V=0 exacto, `BAL` = 0.5·δ*,
    `AGR` = δ*). Cero optimización dentro del instrumento: los tres parámetros se aplican, no
    se calibran.
    """
    modo_norm = str(modo or "").strip().lower()
    if modo_norm not in MODOS_VALIDOS:
        raise ValueError(f"Modo no legislado: {modo!r}. Válidos: {MODOS_VALIDOS}")
    base_inicial = round(float(bankroll_inicial), 2)
    if base_inicial <= 0.0:
        raise ValueError("El bankroll inicial debe ser estrictamente positivo.")

    exclusiones = _normalizar_exclusiones(excluir_estrategias)

    # ── [LN-QBE-115] Validación de dominio de los parámetros gobernantes (cero clamping mudo) ──
    gamma_norm = round(_a_float(gamma, GAMMA_BASE), 4)
    if not (GAMMA_MIN <= gamma_norm <= GAMMA_MAX):
        raise ValueError(
            f"Γ fuera del dominio legislado [{GAMMA_MIN}, {GAMMA_MAX}]: {gamma!r}"
        )
    cobertura_norm = str(modo_cobertura or MODO_COBERTURA_DEF).strip().upper()
    if cobertura_norm not in MODOS_COBERTURA_VALIDOS:
        raise ValueError(
            f"Modo de cobertura no legislado: {modo_cobertura!r}. "
            f"Válidos: {MODOS_COBERTURA_VALIDOS}"
        )
    certeza_pct = round(_a_float(target_certeza_pct, CERTEZA_NEUTRA_PCT), 2)
    if not (0.0 <= certeza_pct <= 100.0):
        raise ValueError(
            f"target_certeza_pct fuera de [0.0, 100.0]: {target_certeza_pct!r}"
        )
    modo_certeza, familias_veto_certeza = _resolver_trinidad_certeza(certeza_pct)

    jornadas_lista = sorted({int(j) for j in (jornadas if jornadas is not None else range(1, 12))})
    if not jornadas_lista:
        raise ValueError("Debe solicitar al menos una jornada.")

    pasarela = gateway if gateway is not None else PersistenceGateway()
    detalle: List[Dict[str, Any]] = []
    resumen_coberturas: Dict[str, int] = {escenario: 0 for escenario in ESCENARIOS_CANONICOS}
    posiciones_operables = 0
    descartes_totales = 0
    capital_no_desplegado = 0.0
    bankroll = base_inicial
    origen_delta: Dict[str, int] = {"factico": 0, "fallback": 0}

    with pasarela.read_session() as sesion:
        for jornada in jornadas_lista:
            base_dimensionamiento = bankroll if modo_norm == "compuesto" else base_inicial
            cargado = _cargar_jornada(sesion, jornada)
            cartera = _construir_cartera_jornada(
                cargado,
                base_dimensionamiento,
                excluir_estrategias=exclusiones,
                gamma=gamma_norm,
                modo_cobertura=cobertura_norm,
                familias_veto_certeza=familias_veto_certeza,
                modo_certeza=modo_certeza,
            )
            for origen, conteo in (cartera.get("delta_epist_origen") or {}).items():
                origen_delta[origen] = origen_delta.get(origen, 0) + int(conteo)

            posiciones = cartera["posiciones"]
            inversion = round(_a_float(cartera["inversion_total"]), 2)
            cobro = round(sum(_a_float(p.get("cobro_mxn")) for p in posiciones), 2)
            pnl = round(sum(_a_float(p.get("pnl_mxn")) for p in posiciones), 2)
            bankroll_final = round(bankroll + pnl, 2)

            for posicion in posiciones:
                escenario = str(posicion.get("escenario") or ESCENARIO_RUPTURA)
                resumen_coberturas[escenario] = resumen_coberturas.get(escenario, 0) + 1

            posiciones_operables += len(posiciones)
            descartes_totales += len(cartera["descartes"]) + len(cartera["no_liquidables"])
            capital_no_desplegado = round(
                capital_no_desplegado + _a_float(cartera["capital_no_desplegado"]), 2
            )

            detalle.append({
                "jornada": jornada,
                "fecha_captura": cargado["snapshot_capturado"],
                "cartelera": len(cargado["fixtures"]),
                "candidatos_triaje": cartera["candidatos_triaje"],
                "bankroll_disponible": bankroll,
                "base_dimensionamiento": base_dimensionamiento,
                "inversion_total": inversion,
                "cobro_total": cobro,
                "pnl_jornada": pnl,
                "roi_jornada_pct": round((pnl / bankroll) * 100.0, 2) if bankroll > 0 else 0.0,
                "bankroll_final": bankroll_final,
                "posiciones_operables": len(posiciones),
                "capital_no_desplegado": round(_a_float(cartera["capital_no_desplegado"]), 2),
                "descartes_total": len(cartera["descartes"]) + len(cartera["no_liquidables"]),
                "descartes": cartera["descartes"],
                "no_liquidables": cartera["no_liquidables"],
                "posiciones": posiciones,
            })
            bankroll = bankroll_final

    return _consolidar_reporte(
        detalle=detalle,
        base_inicial=base_inicial,
        modo=modo_norm,
        jornadas_lista=jornadas_lista,
        resumen_coberturas=resumen_coberturas,
        posiciones_operables=posiciones_operables,
        descartes_totales=descartes_totales,
        capital_no_desplegado=capital_no_desplegado,
        jornadas_por_temporada=int(jornadas_por_temporada),
        parametros_simulacion={
            "gamma": gamma_norm,
            "target_certeza_pct": certeza_pct,
            "modo_certeza": modo_certeza,
            "familias_vetadas_certeza": list(familias_veto_certeza),
            "modo_cobertura": cobertura_norm,
            "escudo_altitud_metros": UMBRAL_VETO_ALTITUD_METROS,
            "cap_underdog_ley3_pct": CAP_UNDERDOG_LEY3_PCT,
            "delta_epist_origen": dict(origen_delta),
        },
        exclusiones_activas=exclusiones,
    )


def _consolidar_reporte(
    detalle: List[Dict[str, Any]],
    base_inicial: float,
    modo: str,
    jornadas_lista: List[int],
    resumen_coberturas: Dict[str, int],
    posiciones_operables: int,
    descartes_totales: int,
    capital_no_desplegado: float,
    jornadas_por_temporada: int,
    parametros_simulacion: Optional[Dict[str, Any]] = None,
    exclusiones_activas: Sequence[str] = (),
) -> Dict[str, Any]:
    """Consolida curva, drawdown, tasa de preservación V=0 y proyección anualizada."""
    curva = [round(base_inicial, 2)] + [round(_a_float(j["bankroll_final"]), 2) for j in detalle]

    # ── Drawdown máximo sobre la curva COMPLETA (incluye el patrimonio inicial) ────────────
    pico = curva[0]
    dd_max_pct = 0.0
    dd_max_mxn = 0.0
    jornada_dd: Optional[int] = None
    drawdown_por_jornada: List[float] = []
    for indice, valor in enumerate(curva):
        pico = max(pico, valor)
        caida = round(pico - valor, 2)
        dd_pct = round((caida / pico) * 100.0, 2) if pico > 0 else 0.0
        drawdown_por_jornada.append(dd_pct)
        if indice > 0 and dd_pct > dd_max_pct:
            dd_max_pct = dd_pct
            dd_max_mxn = caida
            jornada_dd = jornadas_lista[indice - 1]

    bankroll_final = curva[-1]
    pnl_acumulado = round(bankroll_final - base_inicial, 2)
    roi_acumulado = round((pnl_acumulado / base_inicial) * 100.0, 2) if base_inicial > 0 else 0.0

    # ── Tasa de preservación V=0 sobre el denominador honesto de desenlaces defensivos ────
    coberturas_v0 = int(resumen_coberturas.get(ESCENARIO_COBERTURA_V0, 0))
    rupturas = int(resumen_coberturas.get(ESCENARIO_RUPTURA, 0))
    denominador = coberturas_v0 + rupturas
    tasa_preservacion = round((coberturas_v0 / denominador) * 100.0, 2) if denominador else 0.0

    # ── Proyección anualizada a 40 jornadas ([LN-QBE-107] paso 7) ─────────────────────────
    operadas = [j for j in detalle if int(j["posiciones_operables"]) > 0]
    total_operadas = len(operadas)
    horizonte = max(1, int(jornadas_por_temporada))
    if total_operadas:
        pnl_promedio = sum(_a_float(j["pnl_jornada"]) for j in operadas) / total_operadas
        roi_promedio = sum(
            _a_float(j["pnl_jornada"]) / max(_a_float(j["bankroll_disponible"]), 0.01)
            for j in operadas
        ) / total_operadas
    else:
        pnl_promedio = 0.0
        roi_promedio = 0.0

    proyeccion_lineal = round(base_inicial + (pnl_promedio * horizonte), 2)
    proyeccion_compuesta = 0.0
    if 1.0 + roi_promedio > 0.0:
        try:
            proyeccion_compuesta = round(base_inicial * ((1.0 + roi_promedio) ** horizonte), 2)
        except OverflowError:
            proyeccion_compuesta = 0.0
        if proyeccion_compuesta != proyeccion_compuesta:  # guarda anti-NaN
            proyeccion_compuesta = 0.0
    roi_anual_compuesto = (
        round(((proyeccion_compuesta / base_inicial) - 1.0) * 100.0, 2)
        if proyeccion_compuesta > 0.0 and base_inicial > 0.0 else -100.0
    )
    if total_operadas and bankroll_final > 0.0 and base_inicial > 0.0:
        cagr = round((((bankroll_final / base_inicial) ** (horizonte / total_operadas)) - 1.0) * 100.0, 2)
    else:
        cagr = -100.0

    # ── [LN-QBE-113] Trazabilidad del Veto Fiduciario Selectivo ───────────────────────────
    exclusiones = tuple(exclusiones_activas or ())
    vetos_aplicados = sum(
        1 for jornada in detalle for descarte in jornada.get("descartes", [])
        if descarte.get("veto_fiduciario")
    )
    # ── [LN-QBE-115] Abstenciones de admisión por la Trinidad de Certeza §5.10 ─────────────
    vetos_certeza_aplicados = sum(
        1 for jornada in detalle for descarte in jornada.get("descartes", [])
        if descarte.get("veto_trinidad_certeza")
    )
    parametros = dict(parametros_simulacion or {})

    # ── [LN-QBE-115] Desglose por estrategia (meso-económico, cero recálculo en la capa web) ──
    resumen_estrategias: Dict[str, Dict[str, Any]] = {}
    for jornada in detalle:
        for posicion in jornada.get("posiciones", []):
            codigo = str(
                posicion.get("estrategia_codigo") or posicion.get("familia") or ""
            ).upper()
            if not codigo:
                continue
            bloque = resumen_estrategias.setdefault(codigo, {
                "posiciones": 0, "inversion_total": 0.0, "pnl_neto": 0.0,
                "aciertos": 0, "_delta_acumulado": 0.0,
            })
            bloque["posiciones"] += 1
            bloque["inversion_total"] = round(
                bloque["inversion_total"] + _a_float(posicion.get("inversion_total")), 2
            )
            bloque["pnl_neto"] = round(
                bloque["pnl_neto"] + _a_float(posicion.get("pnl_mxn")), 2
            )
            if _a_float(posicion.get("pnl_mxn")) > 0.0:
                bloque["aciertos"] += 1
            bloque["_delta_acumulado"] = round(
                bloque["_delta_acumulado"] + _a_float(posicion.get("delta_cobertura")), 6
            )

    for bloque in resumen_estrategias.values():
        operaciones = int(bloque["posiciones"])
        inversion_bloque = float(bloque["inversion_total"])
        bloque["roi_pct"] = (
            round((bloque["pnl_neto"] / inversion_bloque) * 100.0, 2)
            if inversion_bloque > 0.0 else 0.0
        )
        bloque["tasa_acierto_pct"] = (
            round((bloque["aciertos"] / operaciones) * 100.0, 2) if operaciones else 0.0
        )
        bloque["delta_medio"] = (
            round(bloque.pop("_delta_acumulado") / operaciones, 4) if operaciones else 0.0
        )
    resumen_estrategias = {
        codigo: resumen_estrategias[codigo] for codigo in sorted(resumen_estrategias)
    }

    nota_paridad = [
        "Ventanilla retrospectiva: es_operable=True (estrato legislado) y Δ_epist fáctico de 3NF.",
        "Familias con cobertura particionadas con la ley δ de [LN-QBE-077] (DEF ⇒ V=0 uniforme).",
        "R2: el motor vivo usa ponderación inversa; aquí rige [LN-QBE-070] para indemnidad total.",
        "Pago Anticipado sólo se acredita con testigo fáctico (margen >= 2 o traza in-play).",
        "Sin marcador oficial la posición es NO_LIQUIDABLE con capital devuelto: cero 0-0 fabricado.",
    ]
    if exclusiones:
        nota_paridad.append(
            f"Veto Fiduciario Selectivo [LN-QBE-113]: exclusión de "
            f"{', '.join(exclusiones)} ({vetos_aplicados} abstenciones fiduciarias)."
        )

    # ── [LN-QBE-115] Paridad declarada del Saneamiento Vol. II (cero silencios) ────────────
    origen = parametros.get("delta_epist_origen") or {}
    nota_paridad.append(
        "Δ_epist [LN-QBE-115]: lectura fáctica de sovereign_distributions.epistemic_delta con "
        f"guarda 0.0<=Δ<=1.0 ({int(_a_float(origen.get('factico')))} fixtures) y fallback "
        f"legislado 0.02 ({int(_a_float(origen.get('fallback')))} fixtures)."
    )
    nota_paridad.append(
        "Escudo de Altitud [LN-QBE-115]: ΔAlt⁺ >= "
        f"{UMBRAL_VETO_ALTITUD_METROS:.0f} m veta QBE-H2 sobre ASIMETRIA_VISITANTE "
        "(catálogo inmutable [LN-QBE-109]); sin evidencia de altitud no hay veto."
    )
    nota_paridad.append(
        "Cota de Dominancia P′ [LN-QBE-116]: QBE-H2 se veta cuando "
        f"P_visitante < {UMBRAL_DOMINANCIA_VISITANTE_PCT * 100.0:.2f}% (borde exacto: el piso "
        "no veta); opera después del escudo de altitud y sólo sobre la ruta H2."
    )
    nota_paridad.append(
        f"Cota Underdog Ley 3 [LN-QBE-115]: QBE-R1/QBE-R2 <= "
        f"{CAP_UNDERDOG_LEY3_PCT * 100.0:.2f}% del capital de la jornada."
    )
    nota_paridad.append(
        "Trinidad de Certeza §5.10 [LN-QBE-115]: modo "
        f"{parametros.get('modo_certeza', MODO_CERTEZA_CRECIMIENTO)} a "
        f"{_a_float(parametros.get('target_certeza_pct')):.2f}% "
        f"({vetos_certeza_aplicados} abstenciones de admisión)."
    )
    nota_paridad.append(
        "Cobertura dinámica δ [LN-QBE-077]: modo "
        f"{parametros.get('modo_cobertura', MODO_COBERTURA_DEF)} "
        f"con Γ = {_a_float(parametros.get('gamma'), GAMMA_BASE):.2f} en Capa 0."
    )

    return {
        "status": "EXITO",
        "modo": modo,
        "modo_descripcion": (
            "Compuesto: la jornada dimensiona sobre el patrimonio real de la jornada previa"
            if modo == "compuesto"
            else "Plano: stake nominal fijo dimensionado sobre el patrimonio inicial"
        ),
        "bankroll_inicial": base_inicial,
        "jornadas_solicitadas": list(jornadas_lista),
        "jornadas_con_cartera": total_operadas,
        "cartelera_total": sum(int(_a_float(j.get("cartelera"))) for j in detalle),
        "posiciones_operables": int(posiciones_operables),
        "descartes_totales": int(descartes_totales),
        "capital_no_desplegado": round(_a_float(capital_no_desplegado), 2),
        "bankroll_final": bankroll_final,
        "pnl_acumulado": pnl_acumulado,
        "roi_acumulado_pct": roi_acumulado,
        "drawdown_maximo_pct": dd_max_pct,
        "drawdown_maximo_mxn": round(dd_max_mxn, 2),
        "jornada_drawdown_maximo": jornada_dd,
        "drawdown_por_jornada_pct": drawdown_por_jornada[1:],
        "curva_bankroll": curva,
        "resumen_coberturas": dict(resumen_coberturas),
        "tasa_preservacion_v0_pct": tasa_preservacion,
        "exclusiones_activas": list(exclusiones),
        "vetos_aplicados": int(vetos_aplicados),
        # ── [LN-QBE-115] Trazabilidad del Saneamiento Vol. II ──────────────────────────────
        "vetos_certeza_aplicados": int(vetos_certeza_aplicados),
        "parametros_simulacion": parametros,
        "resumen_estrategias": resumen_estrategias,
        "proyeccion_anual": {
            "horizonte_jornadas": horizonte,
            "jornadas_operadas": total_operadas,
            "roi_promedio_jornada_pct": round(roi_promedio * 100.0, 4),
            "lineal_mxn": proyeccion_lineal,
            "compuesta_mxn": proyeccion_compuesta,
            "roi_anual_compuesto_pct": roi_anual_compuesto,
            "cagr_pct": cagr,
        },
        "jornadas_detalle": detalle,
        "nota_paridad": nota_paridad,
    }


# ═════════════════════════════════════════════════════════════════════════════════════════════
# PRESENTACIÓN ([DBBD-FUNGIBLE]) — tablero ASCII de alta densidad
# ═════════════════════════════════════════════════════════════════════════════════════════════
def _dibujar_curva_bankroll(curva: Sequence[float], ancho: int = 62, alto: int = 7) -> List[str]:
    """Curva de patrimonio en ASCII puro (determinista, sin dependencias gráficas)."""
    valores = [round(_a_float(v), 2) for v in curva]
    if not valores:
        return []
    maximo, minimo = max(valores), min(valores)
    rango = (maximo - minimo) or 1.0
    lienzo = [[" "] * ancho for _ in range(alto)]
    for indice, valor in enumerate(valores):
        columna = round(indice * (ancho - 1) / max(1, len(valores) - 1))
        fila = alto - 1 - round((valor - minimo) / rango * (alto - 1))
        lienzo[fila][columna] = "●"

    lineas: List[str] = []
    for fila in range(alto):
        nivel = minimo + ((alto - 1 - fila) / max(1, alto - 1)) * rango
        lineas.append(f"   ${nivel:>12,.2f} ┤" + "".join(lienzo[fila]))
    lineas.append("   " + " " * 14 + "└" + "─" * (ancho - 1))
    return lineas


def _formatear_pesos(valor: float) -> str:
    """Formato monetario local con signo explícito (cero ambigüedad fiduciaria)."""
    numero = _a_float(valor)
    if not numero:
        return "$0.00"
    return f"-${abs(numero):,.2f}" if numero < 0 else f"+${numero:,.2f}"


_DESCRIPCION_ESCENARIO = {
    ESCENARIO_VICTORIA: "Cobro íntegro de la pierna de ataque (B_prio · O_ataque)",
    ESCENARIO_COBERTURA_V0: "Indemnidad V=0: tablas cubiertas, capital preservado",
    ESCENARIO_DOBLE_COBRO_PA: "Doble cobro: Pago Anticipado + seguro de Empate",
    ESCENARIO_RUPTURA: "Ganó el bando no cubierto: pérdida íntegra del stake",
    ESCENARIO_NO_LIQUIDABLE: "Sin marcador oficial: capital devuelto (cero 0-0 fabricado)",
}


def imprimir_tablero_rentabilidad_consola(reporte: Dict[str, Any]) -> None:
    """Tablero ASCII de alta densidad: jornadas, curva, coberturas y proyección."""
    linea = "═" * ANCHO_TABLERO
    separador = "─" * ANCHO_TABLERO

    print(linea)
    print("  🏦 SANDBOX DE RENTABILIDAD RETROSPECTIVA — [LN-QBE-107] / [ARCH-1.4.46]")
    print(f"  Bóveda 3NF en SÓLO LECTURA · modo {str(reporte.get('modo')).upper()} · "
          f"bankroll inicial ${_a_float(reporte.get('bankroll_inicial')):,.2f}")
    print(f"  {reporte.get('modo_descripcion', '')}")
    parametros = reporte.get("parametros_simulacion") or {}
    print(f"  ⚙️  Γ = {_a_float(parametros.get('gamma'), GAMMA_BASE):.2f} · "
          f"Certeza {_a_float(parametros.get('target_certeza_pct')):.1f}% "
          f"({parametros.get('modo_certeza', MODO_CERTEZA_CRECIMIENTO)}) · "
          f"Cobertura δ {parametros.get('modo_cobertura', MODO_COBERTURA_DEF)} · "
          f"Escudo altitud "
          f"{_a_float(parametros.get('escudo_altitud_metros'), UMBRAL_VETO_ALTITUD_METROS):.0f} m · "
          f"Cota R {_a_float(parametros.get('cap_underdog_ley3_pct')) * 100.0:.2f}%")
    exclusiones = list(reporte.get("exclusiones_activas") or [])
    if exclusiones:
        print(f"  🚫 Veto Fiduciario [LN-QBE-113]: Exclusión de "
              f"[{', '.join(exclusiones)}] "
              f"({int(_a_float(reporte.get('vetos_aplicados')))} abstenciones)")
    else:
        print("  🚫 Filtros Activos: ninguno (cartera íntegra)")
    if int(_a_float(reporte.get("vetos_certeza_aplicados"))) > 0:
        print(f"  🎚️  Trinidad de Certeza [LN-QBE-115]: "
              f"{int(_a_float(reporte.get('vetos_certeza_aplicados')))} "
              f"abstenciones de admisión")
    print(linea)

    print(f" {'J':>2}  {'CART':>4}  {'POS':>3}  {'BASE':>11}  {'INVERTIDO':>11}  "
          f"{'COBRO':>11}  {'PnL':>11}  {'ROI%':>7}  {'BANKROLL':>11}")
    print(separador)
    for jornada in reporte.get("jornadas_detalle", []):
        print(
            f" {int(_a_float(jornada['jornada'])):>2}  {int(_a_float(jornada.get('cartelera'))):>4}  "
            f"{int(_a_float(jornada.get('posiciones_operables'))):>3}  "
            f"{_a_float(jornada.get('base_dimensionamiento')):>11,.2f}  "
            f"{_a_float(jornada.get('inversion_total')):>11,.2f}  "
            f"{_a_float(jornada.get('cobro_total')):>11,.2f}  "
            f"{_a_float(jornada.get('pnl_jornada')):>+11,.2f}  "
            f"{_a_float(jornada.get('roi_jornada_pct')):>+6.2f}%  "
            f"{_a_float(jornada.get('bankroll_final')):>11,.2f}"
        )
    print(separador)
    print(f" {'TOTAL':>2}  {'':>4}  {int(_a_float(reporte.get('posiciones_operables'))):>3}  "
          f"{'':>11}  {'':>11}  {'':>11}  "
          f"{_a_float(reporte.get('pnl_acumulado')):>+11,.2f}  "
          f"{_a_float(reporte.get('roi_acumulado_pct')):>+6.2f}%  "
          f"{_a_float(reporte.get('bankroll_final')):>11,.2f}")
    print(linea)

    print("  📈 CURVA DE BANKROLL (jornada 0 → N)")
    for renglon in _dibujar_curva_bankroll(reporte.get("curva_bankroll", [])):
        print(renglon)
    print(f"   J0{' ' * 12}"
          + "".join(
              f"J{int(_a_float(j['jornada']))}".rjust(
                  max(2, round(62 / max(1, len(reporte.get('jornadas_detalle', []))))))
              for j in reporte.get("jornadas_detalle", [])
          ))
    print(separador)

    print("  🛡️  COBERTURA DE LIQUIDACIÓN")
    for escenario, conteo in reporte.get("resumen_coberturas", {}).items():
        print(f"    ● {escenario:<22} {int(_a_float(conteo)):>3}   "
              f"{_DESCRIPCION_ESCENARIO.get(escenario, '')}")
    print(f"    → Tasa de preservación V=0: {_a_float(reporte.get('tasa_preservacion_v0_pct')):.2f}%  "
          f"| Capital no desplegado: ${_a_float(reporte.get('capital_no_desplegado')):,.2f}")
    print(separador)

    print("  🎯 DESGLOSE POR ESTRATEGIA [LN-QBE-115]")
    resumen_estrategias = reporte.get("resumen_estrategias") or {}
    if not resumen_estrategias:
        print("    ● sin posiciones operables")
    for codigo, bloque in resumen_estrategias.items():
        print(f"    ● {str(codigo):<8} {int(_a_float(bloque.get('posiciones'))):>3} pos · "
              f"inv ${_a_float(bloque.get('inversion_total')):>10,.2f} · "
              f"PnL {_formatear_pesos(bloque.get('pnl_neto')):>13} · "
              f"ROI {_a_float(bloque.get('roi_pct')):>+7.2f}% · "
              f"ac. {_a_float(bloque.get('tasa_acierto_pct')):>6.2f}%")
    print(separador)

    proyeccion = reporte.get("proyeccion_anual", {})
    print(f"  🔭 PROYECCIÓN ANUALIZADA ({int(_a_float(proyeccion.get('horizonte_jornadas')))} jornadas · "
          f"{int(_a_float(proyeccion.get('jornadas_operadas')))} operadas)")
    print(f"    Lineal       ${_a_float(proyeccion.get('lineal_mxn')):>14,.2f}   "
          f"(ROI medio/jornada {_a_float(proyeccion.get('roi_promedio_jornada_pct')):+.4f}%)")
    print(f"    Compuesta    ${_a_float(proyeccion.get('compuesta_mxn')):>14,.2f}   "
          f"(ROI anual {_a_float(proyeccion.get('roi_anual_compuesto_pct')):+.2f}%)")
    print(f"    CAGR         {_a_float(proyeccion.get('cagr_pct')):>+14.2f}%")
    print(separador)

    print(f"  💰 PnL acumulado: {_formatear_pesos(reporte.get('pnl_acumulado'))}  "
          f"| ROI acumulado: {_a_float(reporte.get('roi_acumulado_pct')):+.2f}%  "
          f"| Drawdown máx: {_a_float(reporte.get('drawdown_maximo_pct')):.2f}% "
          f"(${_a_float(reporte.get('drawdown_maximo_mxn')):,.2f}"
          + (f" en J{int(_a_float(reporte.get('jornada_drawdown_maximo')))}"
             if reporte.get("jornada_drawdown_maximo") is not None else "") + ")")
    veredicto = "✅ FONDO SOLVENTE (no-ruina)" if _a_float(reporte.get("bankroll_final")) > 0 else "🚨 FONDO EXTINGUIDO"
    print(f"  {veredicto} · Bankroll final ${_a_float(reporte.get('bankroll_final')):,.2f}")

    print("  📌 NOTA DE PARIDAD DECLARADA")
    for nota in reporte.get("nota_paridad", []):
        print(f"    · {nota}")
    print(linea)


# ═════════════════════════════════════════════════════════════════════════════════════════════
# CLI ([DBBD-FUNGIBLE]) — ventanilla de consola del simulador
# ═════════════════════════════════════════════════════════════════════════════════════════════
def parsear_rango_jornadas(texto: str) -> List[int]:
    """Acepta `1-11`, `1,3,5` o combinaciones (`1-3,7`). Cero jornadas implícitas."""
    jornadas: List[int] = []
    for trozo in str(texto or "").replace(" ", "").split(","):
        if not trozo:
            continue
        if "-" in trozo:
            desde, hasta = trozo.split("-", 1)
            jornadas.extend(range(int(desde), int(hasta) + 1))
        else:
            jornadas.append(int(trozo))
    return sorted({j for j in jornadas if j > 0})


def resolver_exclusiones_cli(
    sin_familia_r: bool = False, excluir: Optional[str] = None
) -> List[str]:
    """`[ARCH-1.4.52]` Compone la lista de veto desde la CLI (unión idempotente y determinista).

    `--sin-familia-r` inyecta el atajo fiduciario `QBE-R1, QBE-R2`; `--excluir` admite una lista
    separada por comas. La normalización (`[LN-QBE-113]`) deduplica y ordena, de modo que
    `--sin-familia-r --excluir qbe-r2` produce exactamente `["QBE-R1", "QBE-R2"]`.
    """
    codigos: List[str] = []
    if sin_familia_r:
        codigos.extend(FAMILIA_R_CODIGOS)
    if excluir:
        codigos.extend(str(excluir).split(","))
    return list(_normalizar_exclusiones(codigos))


def construir_parser() -> argparse.ArgumentParser:
    """Contrato de banderas del sandbox (`[ARCH-1.4.46]` / `[ARCH-1.4.52]`)."""
    parser = argparse.ArgumentParser(
        prog="sandbox_rentabilidad_pipeline",
        description=(
            "[LN-QBE-107] Simulación retrospectiva de rentabilidad del fondo: liquida las "
            "posiciones YA congeladas contra los marcadores oficiales y emite PnL, ROI, "
            "drawdown y proyección anualizada. Sólo lectura."
        ),
    )
    parser.add_argument("--bankroll", type=float, default=PATRIMONIO_BASE_SHIELD,
                        help=f"Bankroll inicial en MXN (default {PATRIMONIO_BASE_SHIELD:,.2f}).")
    parser.add_argument("--modo", choices=MODOS_VALIDOS, default="compuesto",
                        help="compuesto = base rodante por jornada · plano = stake nominal fijo.")
    parser.add_argument("--jornadas", default="1-11",
                        help="Rango de jornadas a simular (ej. 1-11, 3, 1-3,7).")
    parser.add_argument("--sin-familia-r", action="store_true", dest="sin_familia_r",
                        help="Atajo fiduciario: excluye la Familia R (QBE-R1, QBE-R2).")
    parser.add_argument("--excluir", type=str, default=None, metavar="LISTA",
                        help="Códigos separados por coma, ej. QBE-R1,QBE-R2")
    parser.add_argument("--horizonte", type=int, default=JORNADAS_POR_TEMPORADA,
                        help=f"Jornadas por temporada para la anualización (default {JORNADAS_POR_TEMPORADA}).")
    parser.add_argument("--gamma", type=float, default=GAMMA_BASE, metavar="GAMMA",
                        help=f"Γ de Capa 0, dominio [{GAMMA_MIN}, {GAMMA_MAX}] "
                             f"(default {GAMMA_BASE}).")
    parser.add_argument("--certeza", type=float, default=CERTEZA_NEUTRA_PCT, metavar="PCT",
                        help="Slider de Certeza §5.10 en %% (0.0 = sin exigencia; "
                             ">= 80 Balanceado; >= 90 Conservador).")
    parser.add_argument("--modo-cobertura", choices=MODOS_COBERTURA_VALIDOS,
                        default=MODO_COBERTURA_DEF, dest="modo_cobertura",
                        help="DEF (V=0 exacto), BAL (50%% de delta*), AGR (delta*).")
    parser.add_argument("--json", action="store_true", dest="salida_json",
                        help="Emite el contrato JSON y suprime el tablero ASCII.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Punto de entrada CLI. Retorna 0 en éxito y 1 en alto al fuego."""
    argumentos = construir_parser().parse_args(argv)
    logging.basicConfig(level=logging.WARNING)
    try:
        reporte = ejecutar_simulacion_rentabilidad(
            bankroll_inicial=argumentos.bankroll,
            jornadas=parsear_rango_jornadas(argumentos.jornadas),
            modo=argumentos.modo,
            jornadas_por_temporada=argumentos.horizonte,
            excluir_estrategias=resolver_exclusiones_cli(
                argumentos.sin_familia_r, argumentos.excluir
            ),
            gamma=argumentos.gamma,
            target_certeza_pct=argumentos.certeza,
            modo_cobertura=argumentos.modo_cobertura,
        )
    except (ValueError, RuntimeError) as error:
        print(f"🚨 ALTO AL FUEGO: {error}", file=sys.stderr)
        return 1

    if argumentos.salida_json:
        print(json.dumps(reporte, ensure_ascii=False, indent=2))
    else:
        imprimir_tablero_rentabilidad_consola(reporte)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())