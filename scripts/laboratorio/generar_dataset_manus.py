# -*- coding: utf-8 -*-
"""
📦 Q-BE — EXTRACCIÓN DEL PAQUETE DE DATOS CONSOLIDADO PARA EL AGENTE MANUS
[UTIL-MANUS-01] — Instrumento CLI-FIRST de LECTURA PURA (cero DML, cero red, cero navegador).

Misión
------
Publicar `data/output/Q-BE_Manus_Dataset.csv`: UNA fila por partido concluido del universo
canónico de investigación (Jornadas 1..11, 97 partidos) y 81 columnas organizadas en las
CUATRO zonas del contrato ratificado por el Director:

  · A — IDENTIDAD Y CONTEXTO (6): `match_id`, `jornada`, `fecha`, `local`, `visitante`,
        `competition_id`.
  · B — TARGET / VARIABLE OBJETIVO (3): `goles_local`, `goles_visita`, `resultado_real`
        ∈ {'L', 'E', 'V'}, derivado mecánicamente del marcador consumado en `matches`.
  · C — PREDICCIONES Q-BE (5): `p_local_qbe`, `p_empate_qbe`, `p_visita_qbe`,
        `lambda_home`, `lambda_away`, transcritas de la tabla soberana 3NF
        `sovereign_distributions`.
  · D — FÁCTICAS Y MERCADO (67):
        – Mercado (3): `p_local_mkt`, `p_empate_mkt`, `p_visita_mkt`, desmarcadas del trío
          1X2 de la captura por la ley sellada `[VAULT-CORE-007-C]`.
        – Fácticas (64): `v01_local` … `v32_local` y `v01_visita` … `v32_visita`, transcritas
          de `data/output/research_feature_matrix.csv` (zona B de `[ARCH-1.4.67]`).

Régimen y frontera de gobernanza
--------------------------------
[DIRGEN-STRICT] — el dataset es un TRANSPORTE: este instrumento NO reimplementa una sola
fórmula y NO altera el núcleo. La única matemática se IMPORTA de sus planos sellados:

    · `src.core.contracts.portfolio_math.desmarcar_cuotas_proporcional`  [VAULT-CORE-007-C]
    · `src.web.routes.markets._cuotas_1x2_factuales`                      [ARCH-1.4.38]

`src/core/` y `src/storage/` permanecen INTACTOS: la bóveda se abre en sesión de sólo lectura
(`PersistenceGateway.read_session()`) y jamás se escribe una fila.

Axiomas operativos
------------------
1. **LEFT JOIN con el universo del CSV.** El universo de filas es EXACTAMENTE el de
   `research_feature_matrix.csv` (97 partidos, J1..J11): ninguna captura soberana ausente
   expulsa un partido del dataset. La ausencia se publica como celda VACÍA, jamás como cifra
   fabricada [GOVERNANCE-01].
2. **Cero relleno sintético.** Sin trío de cuotas ⇒ las tres columnas de mercado quedan vacías
   (no se invoca el desmarque: el `1/3` uniforme de la guarda sería una cifra inventada). Sin
   fila soberana ⇒ P′ y λ vacías. Sin marcador ⇒ target vacío.
3. **Precedencia de captura homologada.** El fixture de un partido se resuelve con la MISMA
   precedencia del Visor sellado (`updated_at DESC` por jornada y `setdefault` por `id_partido`),
   de modo que el mercado del dataset no puede diferir del que audita la vitrina.
4. **Determinismo total.** Orden estable `(jornada, match_id)`; decimales fijos (probabilidades
   e intensidades a 4); UTF-8 SIN BOM y `newline=''`; encabezado derivado del contrato, sin
   transcripción manual. Dos ejecuciones consecutivas producen el MISMO SHA-256.
5. **Sin pandas.** Salida por `csv` de la biblioteca estándar: el artefacto no puede arrastrar
   un índice implícito y el repositorio no adquiere una dependencia nueva.

Modo histórico (`--historico`)
------------------------------
El modo canónico conserva el universo sellado de 97 partidos de `research_feature_matrix.csv`
y su layout de 81 columnas. El modo histórico amplía el universo a **todos** los `matches`
con marcador consumado de la 3NF (incluidos los `FOTMOB-*` de `[ARCH-1.4.73]`), publica las
mismas 81 columnas y añade las 97 filas vivas ya certificadas. Para los partidos con fila en
`match_telemetry`, C (P′/λ) y D (64 celdas fácticas) se toman de `sovereign_distributions` y
de la matriz histórica; para los partidos sin telemetría, C y D quedan **vacías**. Prohibido
imputar: la ausencia es una celda vacía. `local`/`visitante` se publican como slugs canónicos.

Nota fáctica de `fecha`
-----------------------
`matches.kickoff_utc` está NULL en las 153 filas de la bóveda viva y la zona A de la matriz
tampoco porta instante de saque. La fuente factorial disponible es el campo `fecha_dt` de la
captura (`fixtures_snapshots.matches_json[]`, ISO-8601 sin zona) y ése es el valor transcrito;
si la captura no lo portara se cae a `matches.kickoff_utc`, y si tampoco existe la celda queda
vacía (cero fechas inventadas).

Uso
---
    python scripts/laboratorio/generar_dataset_manus.py
    python scripts/laboratorio/generar_dataset_manus.py --salida data/output/otro.csv
    python scripts/laboratorio/generar_dataset_manus.py --historico
    python scripts/laboratorio/generar_dataset_manus.py --historico --db data/qbe_historico.db
    python scripts/laboratorio/generar_dataset_manus.py --historico --salida data/output/Q-BE_Manus_Dataset.csv
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import os
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError, ValueError):
        pass

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Planos sellados: cero reimplementación (ley de bóveda, no de utilidad).
from src.core.contracts.portfolio_math import desmarcar_cuotas_proporcional  # noqa: E402
from src.observatory.core.factor_attribution import estructurar_catalogo_44_variables  # noqa: E402
from src.storage.gateway import PersistenceGateway  # noqa: E402
from src.storage.models import FixtureSnapshot, Match, MatchTelemetry, SovereignDistribution  # noqa: E402
from app.routes.backtesting import _cuotas_1x2_factuales  # noqa: E402

# ── Rutas y parámetros canónicos ─────────────────────────────────────────────────────────────
RUTA_MATRIZ_DEFAULT = os.path.join("data", "output", "research_feature_matrix.csv")
RUTA_SALIDA_DEFAULT = os.path.join("data", "output", "Q-BE_Manus_Dataset.csv")
RUTA_SALIDA_HISTORICO = os.path.join("data", "output", "Q-BE_Manus_Dataset_Historico.csv")
RUTA_MATRIZ_HISTORICA = os.path.join("data", "output", "research_feature_matrix_historico.csv")
RUTA_VIVOS_97 = os.path.join("data", "output", "Q-BE_Manus_Dataset_97_canonico.csv")
LIGA_ID_CANONICA = 1
FILAS_ESPERADAS = 97
DECIMALES_PROBABILIDAD = 4
DECIMALES_INTENSIDAD = 4

# ── Contrato de columnas ratificado (A + B + C + D = 6 + 3 + 5 + 67 = 81) ──────────────────
COLUMNAS_ZONA_A: Tuple[str, ...] = (
    "match_id",
    "jornada",
    "fecha",
    "local",
    "visitante",
    "competition_id",
)

COLUMNAS_ZONA_B: Tuple[str, ...] = (
    "goles_local",
    "goles_visita",
    "resultado_real",
)

COLUMNAS_ZONA_C: Tuple[str, ...] = (
    "p_local_qbe",
    "p_empate_qbe",
    "p_visita_qbe",
    "lambda_home",
    "lambda_away",
)

COLUMNAS_MERCADO: Tuple[str, ...] = (
    "p_local_mkt",
    "p_empate_mkt",
    "p_visita_mkt",
)

LADOS_CATALOGO: Tuple[str, ...] = ("local", "visita")


def _identificadores_catalogo() -> Tuple[str, ...]:
    """Identificadores `v01..v32` del catálogo forense ÚNICO (`[LN-QBE-120]`).

    Se invoca el productor puro sin datos: devuelve las 32 celdas declaradas `SIN EVIDENCIA` y
    de ahí se toma la lista de identificadores. Cero transcripción a mano: si el catálogo cambia,
    el encabezado de la zona D cambia con él (paridad espejo con `[ARCH-1.4.67]`).
    """
    catalogo = estructurar_catalogo_44_variables()
    identificadores: List[str] = []
    for dimension in catalogo.get("dimensiones") or []:
        for variable in dimension.get("variables") or []:
            identificador = str(variable.get("id") or "").strip().lower()
            if identificador:
                identificadores.append(identificador)
    return tuple(identificadores)


# 32 variables × 2 lados = 64 celdas fácticas, por BLOQUES de lado (contrato del Director).
COLUMNAS_FACTICAS: Tuple[str, ...] = tuple(
    f"{identificador}_{lado}"
    for lado in LADOS_CATALOGO
    for identificador in _identificadores_catalogo()
)

COLUMNAS_ZONA_D: Tuple[str, ...] = COLUMNAS_MERCADO + COLUMNAS_FACTICAS

COLUMNAS_DATASET: Tuple[str, ...] = (
    COLUMNAS_ZONA_A + COLUMNAS_ZONA_B + COLUMNAS_ZONA_C + COLUMNAS_ZONA_D
)

MAPA_RESULTADO: Dict[str, str] = {"LOCAL": "L", "EMPATE": "E", "VISITANTE": "V"}


# ── LECTURA DEL UNIVERSO (matriz canónica de investigación) ───────────────────────────────────
def leer_universo(ruta: str) -> Tuple[List[Dict[str, str]], Tuple[str, ...]]:
    """Lee la matriz canónica y devuelve sus filas + su encabezado, sin rellenar ausencias.

    Raises:
        FileNotFoundError: si el artefacto de investigación no existe (no se fabrica un universo).
        ValueError: si el artefacto no porta las columnas fuente del contrato o duplica identidad.
    """
    if not os.path.isfile(ruta):
        raise FileNotFoundError(
            f"No existe la matriz canónica '{ruta}'. Genérela con "
            "`python scripts/investigacion/generar_matriz_investigacion.py` antes de extraer."
        )

    with open(ruta, "r", encoding="utf-8", newline="") as archivo:
        lector = csv.DictReader(archivo)
        encabezado = tuple(lector.fieldnames or ())
        filas = [dict(fila) for fila in lector]

    # Columnas fuente exigidas: identidad/contexto de la matriz + las 64 celdas fácticas.
    columnas_fuente: Tuple[str, ...] = (
        "match_id", "jornada", "competition_id", "kickoff_utc", "local", "visitante",
    ) + COLUMNAS_FACTICAS
    faltantes = [columna for columna in columnas_fuente if columna not in encabezado]
    if faltantes:
        raise ValueError(
            "La matriz canónica no porta las columnas fuente exigidas por el contrato: "
            + ", ".join(faltantes)
        )

    vistos: set = set()
    for fila in filas:
        identificador = str(fila.get("match_id") or "").strip()
        if not identificador:
            raise ValueError("La matriz canónica contiene una fila sin `match_id`.")
        if identificador in vistos:
            raise ValueError(f"Identidad duplicada en la matriz canónica: '{identificador}'.")
        vistos.add(identificador)

    return filas, encabezado


# ── CRUCE CON LA BÓVEDA 3NF (sólo lectura) ───────────────────────────────────────────────────
def indexar_capturas(sesion, league_id: int) -> Dict[str, Dict[str, Any]]:
    """Índice `{match_id: fixture}` con la precedencia EXACTA del Visor sellado.

    El snapshot más reciente de cada jornada gana (`updated_at DESC`) y la primera captura vista
    por `id_partido` se queda (`setdefault`): la identidad de la captura no se pisa entre reingestas.
    """
    snapshots = (
        sesion.query(FixtureSnapshot)
        .filter(FixtureSnapshot.league_id == league_id)
        .order_by(FixtureSnapshot.matchday.asc(), FixtureSnapshot.updated_at.desc())
        .all()
    )
    indice: Dict[str, Dict[str, Any]] = {}
    for snapshot in snapshots:
        for fixture in (snapshot.matches_json or []):
            if not isinstance(fixture, dict):
                continue
            identificador = str(fixture.get("id_partido") or "").strip()
            if identificador:
                indice.setdefault(identificador, fixture)
    return indice


def leer_boveda(
    gateway: PersistenceGateway,
    league_id: int,
) -> Tuple[Dict[str, Match], Dict[str, SovereignDistribution], Dict[str, Dict[str, Any]]]:
    """Abre la bóveda en sesión de SÓLO LECTURA y materializa los tres índices del cruce."""
    with gateway.read_session() as sesion:
        partidos = {str(fila.id): fila for fila in sesion.query(Match).all()}
        soberanas = {str(fila.match_id): fila for fila in sesion.query(SovereignDistribution).all()}
        capturas = indexar_capturas(sesion, league_id)
    return partidos, soberanas, capturas


# ── FORMATEO Y DERIVACIONES MECÁNICAS ───────────────────────────────────────────────────────
def _fmt(valor: Optional[float], decimales: int) -> str:
    """Formato decimal FIJO por columna (determinismo total); `None` ⇒ celda vacía."""
    if valor is None:
        return ""
    return f"{float(valor):.{decimales}f}"


def _fecha_factica(
    fixture: Dict[str, Any],
    partido: Optional[Match],
) -> str:
    """Instante de saque factual: captura (`fecha_dt`) → `matches.kickoff_utc` → celda vacía."""
    fecha_captura = str(fixture.get("fecha_dt") or "").strip()
    if fecha_captura:
        return fecha_captura
    if partido is not None and partido.kickoff_utc is not None:
        saque = partido.kickoff_utc
        return saque.isoformat() if hasattr(saque, "isoformat") else str(saque)
    return ""


def _resultado_real(goles_local: Optional[int], goles_visita: Optional[int]) -> str:
    """Target categórico `L`/`E`/`V` derivado mecánicamente del marcador; sin marcador, vacío."""
    if goles_local is None or goles_visita is None:
        return ""
    if goles_local > goles_visita:
        return "L"
    if goles_local < goles_visita:
        return "V"
    return "E"


def _triada_mercado(fixture: Dict[str, Any]) -> Tuple[Optional[float], ...]:
    """P′ de mercado (vig-free) delegando ENTERAMENTE en la ley sellada `[VAULT-CORE-007-C]`.

    Sin trío 1X2 completo NO se invoca el desmarque: la guarda fiduciaria de la ley degrada a la
    ignorancia uniforme `1/3`, y publicar ese `1/3` como probabilidad de mercado sería una cifra
    inventada [GOVERNANCE-01]. La ausencia se declara con celdas vacías.
    """
    cuotas = _cuotas_1x2_factuales(fixture)
    if not cuotas:
        return (None, None, None)
    return desmarcar_cuotas_proporcional(cuotas["L"], cuotas["E"], cuotas["V"])


def construir_fila(
    fila_matriz: Dict[str, str],
    partido: Optional[Match],
    soberana: Optional[SovereignDistribution],
    fixture: Optional[Dict[str, Any]],
) -> Dict[str, str]:
    """Compone una fila del dataset Manus: transcripción pura + derivaciones mecánicas.

    A (identidad) y D (fácticas) se transcriben de la matriz canónica; B (target) se deriva del
    marcador de `matches`; C (Q-BE) se transcribe de la 3NF; D (mercado) delega el desmarque.
    """
    captura = fixture or {}
    identificador = str(fila_matriz.get("match_id") or "").strip()

    # ── A — Identidad y contexto ────────────────────────────────────────────────────────────
    jornada = ""
    if partido is not None and partido.matchday_num is not None:
        jornada = str(int(partido.matchday_num))
    elif str(fila_matriz.get("jornada") or "").strip():
        jornada = str(fila_matriz.get("jornada")).strip()

    competition_id = ""
    if partido is not None and partido.competition_id:
        competition_id = str(partido.competition_id)
    else:
        competition_id = str(fila_matriz.get("competition_id") or "").strip()

    local = str(captura.get("local") or fila_matriz.get("local") or "").strip()
    visitante = str(captura.get("visitante") or fila_matriz.get("visitante") or "").strip()

    # ── B — Target: marcador consumado de la bóveda 3NF ─────────────────────────────────────
    goles_local: Optional[int] = None
    goles_visita: Optional[int] = None
    if partido is not None:
        if partido.score_home is not None:
            goles_local = int(partido.score_home)
        if partido.score_away is not None:
            goles_visita = int(partido.score_away)

    # ── C — Predicciones Q-BE (P′ y λ) transcritas de `sovereign_distributions` ──────────────
    p_local_qbe: Optional[float] = None
    p_empate_qbe: Optional[float] = None
    p_visita_qbe: Optional[float] = None
    lambda_home: Optional[float] = None
    lambda_away: Optional[float] = None
    if soberana is not None:
        p_local_qbe = float(soberana.p_local)
        p_empate_qbe = float(soberana.p_empate)
        p_visita_qbe = float(soberana.p_visitante)
        lambda_home = float(soberana.lambda_home)
        lambda_away = float(soberana.lambda_away)

    # ── D — Mercado: desmarque proporcional delegado a la ley sellada ───────────────────────
    p_local_mkt, p_empate_mkt, p_visita_mkt = _triada_mercado(captura)

    salida: Dict[str, str] = {
        "match_id": identificador,
        "jornada": jornada,
        "fecha": _fecha_factica(captura, partido),
        "local": local,
        "visitante": visitante,
        "competition_id": competition_id,
        "goles_local": "" if goles_local is None else str(goles_local),
        "goles_visita": "" if goles_visita is None else str(goles_visita),
        "resultado_real": _resultado_real(goles_local, goles_visita),
        "p_local_qbe": _fmt(p_local_qbe, DECIMALES_PROBABILIDAD),
        "p_empate_qbe": _fmt(p_empate_qbe, DECIMALES_PROBABILIDAD),
        "p_visita_qbe": _fmt(p_visita_qbe, DECIMALES_PROBABILIDAD),
        "lambda_home": _fmt(lambda_home, DECIMALES_INTENSIDAD),
        "lambda_away": _fmt(lambda_away, DECIMALES_INTENSIDAD),
        "p_local_mkt": _fmt(p_local_mkt, DECIMALES_PROBABILIDAD),
        "p_empate_mkt": _fmt(p_empate_mkt, DECIMALES_PROBABILIDAD),
        "p_visita_mkt": _fmt(p_visita_mkt, DECIMALES_PROBABILIDAD),
    }

    # Zona D — 64 celdas fácticas PRE-KICKOFF, transcritas VERBATIM (unidad incluida).
    for columna in COLUMNAS_FACTICAS:
        valor = fila_matriz.get(columna)
        salida[columna] = "" if valor is None else str(valor)

    return salida


def extraer_dataset(
    gateway: PersistenceGateway,
    league_id: int,
    ruta_matriz: str,
) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
    """Extrae el dataset completo (LEFT JOIN sobre el universo del CSV) y sus metadatos."""
    filas_matriz, _ = leer_universo(ruta_matriz)
    partidos, soberanas, capturas = leer_boveda(gateway, league_id)

    def _orden(fila: Dict[str, str]) -> Tuple[int, str]:
        partido = partidos.get(str(fila.get("match_id") or "").strip())
        if partido is not None and partido.matchday_num is not None:
            return (int(partido.matchday_num), str(fila.get("match_id") or ""))
        try:
            return (int(str(fila.get("jornada") or 0)), str(fila.get("match_id") or ""))
        except ValueError:
            return (0, str(fila.get("match_id") or ""))

    filas: List[Dict[str, str]] = []
    metadatos: Dict[str, Any] = {
        "sin_soberana": [],
        "sin_mercado": [],
        "sin_marcador": [],
        "celdas_facticas": 0,
        "jornadas": set(),
    }

    for fila_matriz in sorted(filas_matriz, key=_orden):
        identificador = str(fila_matriz.get("match_id") or "").strip()
        fila = construir_fila(
            fila_matriz,
            partidos.get(identificador),
            soberanas.get(identificador),
            capturas.get(identificador),
        )
        filas.append(fila)

        if identificador not in soberanas:
            metadatos["sin_soberana"].append(identificador)
        if not fila["p_local_mkt"]:
            metadatos["sin_mercado"].append(identificador)
        if not fila["resultado_real"]:
            metadatos["sin_marcador"].append(identificador)
        if fila["jornada"]:
            metadatos["jornadas"].add(int(fila["jornada"]))
        metadatos["celdas_facticas"] += sum(
            1 for columna in COLUMNAS_FACTICAS if fila.get(columna) not in (None, "")
        )

    return filas, metadatos


# ── PUBLICACIÓN DEL ARTEFACTO ───────────────────────────────────────────────────────────────
def exportar_csv(filas: Sequence[Dict[str, str]], ruta: str) -> str:
    """Escribe el dataset (UTF-8 SIN BOM, `newline=''`, sin índice, encabezado = contrato)."""
    directorio = os.path.dirname(os.path.abspath(ruta))
    if directorio and not os.path.isdir(directorio):
        os.makedirs(directorio, exist_ok=True)
    with open(ruta, "w", encoding="utf-8", newline="") as archivo:
        escritor = csv.DictWriter(
            archivo,
            fieldnames=list(COLUMNAS_DATASET),
            extrasaction="ignore",
            lineterminator="\n",
        )
        escritor.writeheader()
        for fila in filas:
            escritor.writerow(fila)
    return os.path.abspath(ruta)


def _sha256(ruta: str) -> str:
    """Huella del artefacto para certificar determinismo entre ejecuciones."""
    digest = hashlib.sha256()
    with open(ruta, "rb") as archivo:
        for bloque in iter(lambda: archivo.read(65536), b""):
            digest.update(bloque)
    return digest.hexdigest()


# ── MODO HISTÓRICO (todos los matches con marcador de la 3NF) ─────────────────────────────────
def _matriz_historica_por_id(ruta: str) -> Dict[str, Dict[str, str]]:
    """Índice `match_id -> fila` de la matriz histórica de 92 columnas; vacío si no existe."""
    if not os.path.isfile(ruta):
        return {}
    with open(ruta, "r", encoding="utf-8-sig", newline="") as archivo:
        lector = csv.DictReader(archivo)
        return {
            str(fila.get("match_id") or "").strip(): dict(fila)
            for fila in lector
            if str(fila.get("match_id") or "").strip()
        }


def _normalizar_no_evidencia(fila: Dict[str, str]) -> Dict[str, str]:
    """Normaliza no-evidencias al dominio V-E-D, sin fabricar un récord jugado."""
    for columna in ("v26_local", "v26_visita"):
        if str(fila.get(columna, "")).strip() == "0 partidos":
            fila[columna] = "0V - 0E - 0D"
    if str(fila.get("v28_local", "")).strip() == "Sin antecedentes locales":
        fila["v28_local"] = "0V - 0E - 0D (Visita)"
    return fila


def construir_fila_historica(
    partido: Match,
    matriz: Optional[Dict[str, str]] = None,
    con_telemetria: bool = False,
    soberana: Optional[SovereignDistribution] = None,
    publicar_p: bool = False,
) -> Dict[str, str]:
    """Compone una fila histórica con el MISMO layout de 81 columnas.

    A (identidad) y B (target) se transcriben de la 3NF. C (P′/λ) se publica si el partido
    tiene telemetría o si su traza 3NF porta `S(I)=1` (fix D); D (64 celdas fácticas) se
    publica SOLO con telemetría. No se imputa ninguna magnitud: la ausencia es celda vacía.
    `local`/`visitante` son slugs canónicos.
    """
    goles_local = int(partido.score_home) if partido.score_home is not None else None
    goles_visita = int(partido.score_away) if partido.score_away is not None else None
    salida: Dict[str, str] = {
        "match_id": str(partido.id),
        "jornada": "" if partido.matchday_num is None else str(int(partido.matchday_num)),
        "fecha": (
            partido.kickoff_utc.isoformat()
            if partido.kickoff_utc is not None and hasattr(partido.kickoff_utc, "isoformat")
            else ""
        ),
        "local": str(partido.home_team_slug or ""),
        "visitante": str(partido.away_team_slug or ""),
        "competition_id": str(partido.competition_id or ""),
        "goles_local": "" if goles_local is None else str(goles_local),
        "goles_visita": "" if goles_visita is None else str(goles_visita),
        "resultado_real": _resultado_real(goles_local, goles_visita),
        "p_local_qbe": "",
        "p_empate_qbe": "",
        "p_visita_qbe": "",
        "lambda_home": "",
        "lambda_away": "",
        "p_local_mkt": "",
        "p_empate_mkt": "",
        "p_visita_mkt": "",
    }
    for columna in COLUMNAS_FACTICAS:
        salida[columna] = ""
    if not (con_telemetria or publicar_p):
        return salida

    if soberana is not None:
        salida["p_local_qbe"] = _fmt(float(soberana.p_local), DECIMALES_PROBABILIDAD)
        salida["p_empate_qbe"] = _fmt(float(soberana.p_empate), DECIMALES_PROBABILIDAD)
        salida["p_visita_qbe"] = _fmt(float(soberana.p_visitante), DECIMALES_PROBABILIDAD)
        salida["lambda_home"] = _fmt(float(soberana.lambda_home), DECIMALES_INTENSIDAD)
        salida["lambda_away"] = _fmt(float(soberana.lambda_away), DECIMALES_INTENSIDAD)

    if con_telemetria and matriz:
        # La matriz publica `p_local`/`p_empate`/`p_visitante`; la 3NF manda para λ. Si la
        # distribución no estuviera disponible, se usa la P′ de la matriz como respaldo.
        if not salida["p_local_qbe"]:
            salida["p_local_qbe"] = _fmt(_a_flotante(matriz.get("p_local")), DECIMALES_PROBABILIDAD)
            salida["p_empate_qbe"] = _fmt(_a_flotante(matriz.get("p_empate")), DECIMALES_PROBABILIDAD)
            salida["p_visita_qbe"] = _fmt(_a_flotante(matriz.get("p_visitante")), DECIMALES_PROBABILIDAD)
        for columna in COLUMNAS_FACTICAS:
            valor = matriz.get(columna)
            salida[columna] = "" if valor in (None, "") else str(valor)
    return _normalizar_no_evidencia(salida)


def _a_flotante(valor: Any) -> Optional[float]:
    """Conversión tolerante para celdas CSV; `None` si no es numérica."""
    if valor in (None, ""):
        return None
    try:
        return float(str(valor).replace(",", "."))
    except (TypeError, ValueError):
        return None


def extraer_dataset_historico(
    gateway: PersistenceGateway,
    ruta_matriz: str = RUTA_MATRIZ_HISTORICA,
    ruta_vivos: str = RUTA_VIVOS_97,
) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
    """Extrae el histórico y añade los 97 vivos.

    C se publica para telemetría o para `S(I)=1` (fix D); D solo con telemetría. El fix E
    normaliza V26 `0 partidos` → `0V - 0E - 0D`. Criterio: 4.329 + 97 = 4.426 filas.
    """
    with gateway.read_session() as sesion:
        partidos = (
            sesion.query(Match)
            .filter(Match.score_home.isnot(None), Match.score_away.isnot(None))
            .all()
        )
        ids_telemetria = {
            str(fila[0])
            for fila in sesion.query(MatchTelemetry.match_id).distinct().all()
        }
        soberanas = {
            str(fila.match_id): fila for fila in sesion.query(SovereignDistribution).all()
        }
    partidos.sort(key=lambda partido: (str(partido.kickoff_utc or ""), str(partido.id)))
    matriz = _matriz_historica_por_id(ruta_matriz)

    filas: List[Dict[str, str]] = []
    for partido in partidos:
        identificador = str(partido.id)
        soberana = soberanas.get(identificador)
        trace = soberana.audit_trace_json if soberana is not None and isinstance(soberana.audit_trace_json, dict) else {}
        publicar_p = int(trace.get("suficiencia_S_I", 0) or 0) == 1
        filas.append(
            construir_fila_historica(
                partido,
                matriz.get(identificador),
                con_telemetria=identificador in ids_telemetria,
                soberana=soberana,
                publicar_p=publicar_p,
            )
        )

    # Los 97 partidos de la bóveda viva conservan su fila canónica ya certificada.
    if os.path.isfile(ruta_vivos):
        with open(ruta_vivos, "r", encoding="utf-8-sig", newline="") as archivo:
            for fila in csv.DictReader(archivo):
                filas.append(
                    _normalizar_no_evidencia(
                        {columna: str(fila.get(columna) or "") for columna in COLUMNAS_DATASET}
                    )
                )

    metadatos: Dict[str, Any] = {
        "historico": True,
        "sin_soberana": [fila["match_id"] for fila in filas if not fila["p_local_qbe"]],
        "sin_mercado": [fila["match_id"] for fila in filas if not fila["p_local_mkt"]],
        "sin_marcador": [fila["match_id"] for fila in filas if not fila["resultado_real"]],
        "celdas_facticas": sum(
            1 for fila in filas for columna in COLUMNAS_FACTICAS if fila.get(columna)
        ),
        "jornadas": {
            int(fila["jornada"]) for fila in filas if str(fila.get("jornada") or "").strip()
        },
        "con_telemetria": len(ids_telemetria),
        "vivos": sum(1 for fila in filas if not str(fila["match_id"]).startswith("FOTMOB-")),
    }
    return filas, metadatos


def _configurar_bd(ruta: str) -> None:
    """Reapunta el Gateway a una 3NF alterna (p. ej. `data/qbe_historico.db`)."""
    import src.config as cfg

    absoluta = os.path.abspath(ruta)
    cfg.settings.DATABASE_URL = f"sqlite:///{absoluta.replace(os.sep, '/')}"
    PersistenceGateway._instance = None


def _imprimir_resumen(
    filas: Sequence[Dict[str, str]],
    metadatos: Dict[str, Any],
    ruta_csv: str,
    modo: str = "canonico",
) -> int:
    """Epílogo de certificación: dimensiones, cobertura por zona y huella SHA-256."""
    total = len(filas)
    columnas = len(COLUMNAS_DATASET)
    print("=" * 90)
    print("📦 Q-BE — DATASET CONSOLIDADO PARA EL AGENTE MANUS [UTIL-MANUS-01]")
    print("   Régimen: [DIRGEN-STRICT] · Solo lectura · Matemática sellada delegada")
    if modo == "historico":
        print("   MODO: HISTÓRICO · universo = todos los matches con marcador de la 3NF")
    print("=" * 90)
    print(f"  ARCHIVO  : {ruta_csv}")
    print(f"  DIMENSIONES: {total} filas × {columnas} columnas")
    print(
        "  ZONAS    : "
        f"A={len(COLUMNAS_ZONA_A)} · B={len(COLUMNAS_ZONA_B)} · "
        f"C={len(COLUMNAS_ZONA_C)} · D={len(COLUMNAS_ZONA_D)} "
        f"(mercado={len(COLUMNAS_MERCADO)} + fácticas={len(COLUMNAS_FACTICAS)})"
    )
    print(f"  SHA-256  : {_sha256(ruta_csv)}")

    if total == 0:
        print("  ⚠️  Universo vacío: cero filas publicadas, cero cifras fabricadas.")
        print("=" * 90)
        return 1

    if modo == "historico":
        print(f"  PARIDAD DE FILAS: {total} (histórico; sin techo de {FILAS_ESPERADAS})")
    else:
        paridad = "OK" if total == FILAS_ESPERADAS else f"⚠️ DESVIACIÓN (esperadas {FILAS_ESPERADAS})"
        print(f"  PARIDAD DE FILAS: {paridad}")

    jornadas = sorted(metadatos["jornadas"])
    if jornadas:
        print(f"  JORNADAS : J{min(jornadas)}..J{max(jornadas)} ({len(jornadas)} jornadas)")
    print(
        f"  COBERTURA: Q-BE(P′+λ)={total - len(metadatos['sin_soberana'])}/{total} · "
        f"Mercado={total - len(metadatos['sin_mercado'])}/{total} · "
        f"Target={total - len(metadatos['sin_marcador'])}/{total}"
    )
    if metadatos["sin_soberana"]:
        print(f"  ⚠️  Sin fila soberana (P′/λ vacías): {len(metadatos['sin_soberana'])} "
              f"→ {', '.join(metadatos['sin_soberana'][:8])}")
    if metadatos["sin_mercado"]:
        print(f"  ⚠️  Sin trío 1X2 (mercado vacío): {len(metadatos['sin_mercado'])} "
              f"→ {', '.join(metadatos['sin_mercado'][:8])}")
    if metadatos["sin_marcador"]:
        print(f"  ⚠️  Sin marcador (target vacío): {len(metadatos['sin_marcador'])} "
              f"→ {', '.join(metadatos['sin_marcador'][:8])}")

    print(f"  EVIDENCIA (zona D fácticas): {metadatos['celdas_facticas']} celdas materializadas")
    print("=" * 90)
    return 0


def ejecutar(argv: Optional[Sequence[str]] = None) -> int:
    """Punto de entrada: lectura pura de la bóveda, cruce, publicación y certificación."""
    parser = argparse.ArgumentParser(
        description="Extrae el dataset consolidado Q-BE para el Agente Manus (81 columnas, J1..J11).",
    )
    parser.add_argument("--matriz", default=RUTA_MATRIZ_DEFAULT,
                        help=f"matriz canónica de origen (default: {RUTA_MATRIZ_DEFAULT})")
    parser.add_argument("--salida", default=None,
                        help=("ruta del CSV de salida (default canónico: "
                              f"{RUTA_SALIDA_DEFAULT}; default histórico: {RUTA_SALIDA_HISTORICO})"))
    parser.add_argument("--liga-id", type=int, default=LIGA_ID_CANONICA,
                        help=f"liga de la captura (default: {LIGA_ID_CANONICA} = Liga MX)")
    parser.add_argument("--historico", action="store_true",
                        help="Extrae el histórico con C/D solo donde hay telemetría y añade los 97 vivos.")
    parser.add_argument("--db", default=None,
                        help="SQLite alterna (p. ej. data/qbe_historico.db); omítala para la bóveda viva.")
    parser.add_argument("--matriz-historica", default=RUTA_MATRIZ_HISTORICA,
                        help=f"matriz histórica de 92 columnas (default: {RUTA_MATRIZ_HISTORICA})")
    parser.add_argument("--vivos", default=RUTA_VIVOS_97,
                        help=f"CSV canónico de los 97 partidos vivos (default: {RUTA_VIVOS_97})")
    args = parser.parse_args(argv)

    if args.db:
        _configurar_bd(str(args.db))
    salida = args.salida or (RUTA_SALIDA_HISTORICO if args.historico else RUTA_SALIDA_DEFAULT)
    gateway = PersistenceGateway()
    if args.historico:
        filas, metadatos = extraer_dataset_historico(
            gateway, str(args.matriz_historica), str(args.vivos)
        )
        ruta_csv = exportar_csv(filas, salida)
        return _imprimir_resumen(filas, metadatos, ruta_csv, modo="historico")

    filas, metadatos = extraer_dataset(gateway, int(args.liga_id), args.matriz)
    ruta_csv = exportar_csv(filas, salida)
    return _imprimir_resumen(filas, metadatos, ruta_csv)


def main() -> int:
    """Punto de entrada CLI (UTF-8 asegurado antes de imprimir pictogramas)."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (AttributeError, OSError, ValueError):
            pass
    return ejecutar()


if __name__ == "__main__":
    raise SystemExit(main())
