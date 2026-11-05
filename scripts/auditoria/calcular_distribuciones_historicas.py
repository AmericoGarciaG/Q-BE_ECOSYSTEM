# -*- coding: utf-8 -*-
"""`[LN-QBE-150]` Motor de Cálculo de Distribuciones Históricas (P').

Régimen ``[DIRGEN-STRICT]``.

Lee el vector causal de 32 variables (``historical_match_causal_vars``, `[LN-QBE-146]`),
reconstruye el registro fáctico PRE-KICKOFF de cada partido y delega el cálculo del símplex
soberano en la función sellada ``generar_distribucion_soberana`` de ``qbe_core``
(Dixon-Coles 2D + colapso al Símplex + Cláusula de André). Persiste el resultado en
``historical_sovereign_distributions``, llaveado por ``match_id``.

Reglas duras
------------
1. **Cero imputación.** Si un partido no satisface la suficiencia informativa ``S(I_i)``
   (`[LN-QBE-035-B]`: ≥ 3 partidos previos por club con marcador legible), NO se genera
   distribución: se salta y se declara en el reporte.
2. **Cero fuga temporal.** El registro de entrada se construye exclusivamente con evidencia
   anterior al kickoff; el resultado del partido evaluado jamás entra en su propia entrada.
3. **Cero reimplementación.** La matemática vive en ``qbe_core``; este script sólo transporta
   evidencia y persiste. ``qbe_core`` se importa, nunca se modifica.

Uso::

    python scripts/auditoria/calcular_distribuciones_historicas.py --temporada 2018_2019 --dry-run
    python scripts/auditoria/calcular_distribuciones_historicas.py --temporada 2018_2019
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

RAIZ_PROYECTO = Path(__file__).resolve().parents[2]
for _ruta in (RAIZ_PROYECTO, RAIZ_PROYECTO / "qbe_core"):
    if str(_ruta) not in sys.path:
        sys.path.insert(0, str(_ruta))

if hasattr(sys.stdout, "reconfigure"):
    try:  # consola Windows cp1252
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, OSError, ValueError):  # pragma: no cover
        pass

from src.core.sovereign_pipeline import generar_distribucion_soberana  # noqa: E402
from src.core.sovereign.calibrar_perturbacion import brier_multiclase  # noqa: E402
from src.core.sovereign.orthogonal_factor_engine import EPSILON_LOG_NORMALIZACION  # noqa: E402

DB_DEFECTO = RAIZ_PROYECTO / "qbe_observatory" / "data" / "qbe_historico.db"
TABLA_VECTOR = "historical_match_causal_vars"
TABLA_BOVEDA = "historical_matches"
TABLA_DESTINO = "historical_sovereign_distributions"

# ── [SPRINT-50][LN-QBE-039 §7.6] Ruta V2 (GSL-3D v2) ────────────────────────────────────────
MOTOR_V1 = "v1"
MOTOR_V2 = "v2"
MOTOR_V3 = "v3"
MOTORES = (MOTOR_V1, MOTOR_V2, MOTOR_V3)
#: La P' V2 se persiste en su propia tabla: la V1 queda como baseline histórico comparable.
TABLA_DESTINO_V2 = "historical_sovereign_distributions_v2"
MODEL_VERSION_V2 = "v14.0-GSL3D-V2"
#: [E-50.6] V3 = V2 + ρ continuo + pesos β (Lasso) aplicados PRE-Gram-Schmidt.
TABLA_DESTINO_V3 = "historical_sovereign_distributions_v3"
MODEL_VERSION_V3 = "v15.0-GSL3D-V3-BETA"
#: Ventana del vector causal por club (partidos previos, misma temporada) que alimenta la matriz.
MAX_FILAS_MATRIZ = 20
VARIABLES_CATALOGO: Tuple[str, ...] = tuple(f"V{indice:02d}" for indice in range(1, 33))

MODEL_VERSION = "v13.0-DIRGEN"
ORIGEN = "HISTORICO_SPRINT48"
#: `fuente_causal` NO es constante: se hereda del vector (`historical_match_causal_vars.fuente_datos`).
FUENTE_SIN_PROCEDENCIA = "SIN_PROCEDENCIA"
PARTIDOS_MINIMOS_SI = 3  # [LN-QBE-035-B] S(I_i): suficiencia informativa

#: Selección de tabla y versión por motor (V1 baseline · V2 GSL-3D · V3 + β Lasso).
TABLAS_POR_MOTOR = {
    MOTOR_V1: TABLA_DESTINO,
    MOTOR_V2: TABLA_DESTINO_V2,
    MOTOR_V3: TABLA_DESTINO_V3,
}
VERSIONES_POR_MOTOR = {
    MOTOR_V1: MODEL_VERSION,
    MOTOR_V2: MODEL_VERSION_V2,
    MOTOR_V3: MODEL_VERSION_V3,
}

#: Ganancia de contexto declarada al motor sellado (`[ARCH-1.5.1]` §CQRS — sólo transporte).
VARIABLES_CONTEXTO = ("V29", "V30")

def _ddl(tabla: str = TABLA_DESTINO) -> str:
    """[LN-QBE-150] DDL idempotente de la tabla destino (V1 o V2, mismo contrato de columnas)."""
    return f"""
CREATE TABLE IF NOT EXISTS {tabla} (
    match_id TEXT PRIMARY KEY,
    temporada TEXT NOT NULL,
    model_version TEXT NOT NULL,
    p_local REAL NOT NULL,
    p_empate REAL NOT NULL,
    p_visitante REAL NOT NULL,
    lambda_home REAL NOT NULL,
    lambda_away REAL NOT NULL,
    phi_lead2_home REAL NOT NULL,
    phi_lead2_away REAL NOT NULL,
    epistemic_delta REAL NOT NULL DEFAULT 0.0,
    delta_epist REAL NOT NULL DEFAULT 0.0,
    origen_factores TEXT NOT NULL DEFAULT 'analitico_base',
    es_operable INTEGER NOT NULL DEFAULT 1,
    pj_home INTEGER NOT NULL DEFAULT 0,
    pj_away INTEGER NOT NULL DEFAULT 0,
    duelos_h2h INTEGER NOT NULL DEFAULT 0,
    variables_con_evidencia INTEGER NOT NULL DEFAULT 0,
    origen TEXT NOT NULL DEFAULT '{ORIGEN}',
    fuente_causal TEXT NOT NULL DEFAULT '{FUENTE_SIN_PROCEDENCIA}',
    audit_trace_json TEXT NOT NULL DEFAULT '{{}}',
    created_at TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (match_id) REFERENCES {TABLA_BOVEDA} (match_id)
)
"""


DDL = _ddl()


class CalculoError(RuntimeError):
    """`[LN-QBE-150]` Fallo de dominio del cálculo histórico."""


# ═════════════════════════════════════════════════════════════════════════════════════════════
# Lectura de la bóveda
# ═════════════════════════════════════════════════════════════════════════════════════════════
def _instante(texto: Any) -> Optional[datetime]:
    if not texto:
        return None
    try:
        valor = datetime.fromisoformat(str(texto).strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if valor.tzinfo is None:
        valor = valor.replace(tzinfo=timezone.utc)
    return valor.astimezone(timezone.utc)


def _filas(conexion: sqlite3.Connection, sql: str, parametros: Sequence[Any] = ()) -> List[Dict[str, Any]]:
    cursor = conexion.execute(sql, parametros)
    nombres = [columna[0] for columna in cursor.description]
    return [dict(zip(nombres, fila)) for fila in cursor.fetchall()]


def _vector_de(conexion: sqlite3.Connection, match_id: str) -> Optional[Dict[str, Optional[float]]]:
    filas = _filas(conexion, f"SELECT * FROM {TABLA_VECTOR} WHERE match_id = ?", (match_id,))
    return filas[0] if filas else None


def _evidencia(vector: Optional[Dict[str, Any]]) -> int:
    """Cuenta variables del catálogo con al menos un lado no nulo."""
    if not vector:
        return 0
    total = 0
    for indice in range(1, 33):
        variable = f"v{indice:02d}"
        if vector.get(f"{variable}_local") is not None or vector.get(f"{variable}_visita") is not None:
            total += 1
    return total


# ═════════════════════════════════════════════════════════════════════════════════════════════
# Construcción del registro fáctico PRE-KICKOFF
# ═════════════════════════════════════════════════════════════════════════════════════════════
class Corpus:
    """Corpus cronológico de la bóveda para reconstruir el estado pre-kickoff."""

    def __init__(self, filas: Sequence[Dict[str, Any]]) -> None:
        self.filas: List[Dict[str, Any]] = []
        for fila in filas:
            momento = _instante(fila.get("fecha_utc"))
            if momento is None:
                continue
            registro = dict(fila)
            registro["_instante"] = momento
            self.filas.append(registro)
        self.filas.sort(key=lambda fila: fila["_instante"])
        self.por_equipo: Dict[str, List[Dict[str, Any]]] = {}
        for fila in self.filas:
            self.por_equipo.setdefault(str(fila.get("home_team_slug")), []).append(fila)
            self.por_equipo.setdefault(str(fila.get("away_team_slug")), []).append(fila)

    def previos(self, slug: str, momento: datetime, temporada: str) -> List[Dict[str, Any]]:
        return [
            fila
            for fila in self.por_equipo.get(slug, [])
            if fila["_instante"] < momento and str(fila.get("temporada")) == temporada
        ]

    def h2h(self, local: str, visita: str, momento: datetime) -> List[Dict[str, Any]]:
        return [
            fila
            for fila in self.filas
            if fila["_instante"] < momento
            and local != visita
            and {str(fila.get("home_team_slug")), str(fila.get("away_team_slug"))} == {local, visita}
        ]


def _agregado(
    corpus: Corpus, slug: str, momento: datetime, temporada: str, xg_total: float, xga_total: float
) -> Tuple[Dict[str, float], int]:
    """Suma los marcadores previos legibles del club en la temporada."""
    gf = gc = 0.0
    partidos = 0
    for fila in corpus.previos(slug, momento, temporada):
        goles_local = fila.get("home_goals")
        goles_visita = fila.get("away_goals")
        if goles_local is None or goles_visita is None:
            continue
        if str(fila.get("home_team_slug")) == slug:
            gf += float(goles_local)
            gc += float(goles_visita)
        else:
            gf += float(goles_visita)
            gc += float(goles_local)
        partidos += 1
    return (
        {"pj": float(partidos), "gf": gf, "gc": gc, "xg": xg_total, "xga": xga_total},
        partidos,
    )


def _xg_previo(
    conexion: sqlite3.Connection, corpus: Corpus, slug: str, momento: datetime, temporada: str
) -> Tuple[float, float]:
    """Suma `V06` (xG) y `V12` (xGA) de los partidos previos, si el proveedor los publica."""
    total_xg = total_xga = 0.0
    for fila in corpus.previos(slug, momento, temporada):
        vector = _vector_de(conexion, str(fila["match_id"]))
        if not vector:
            continue
        es_local = str(fila.get("home_team_slug")) == slug
        xg = vector.get("v06_local" if es_local else "v06_visita")
        xga = vector.get("v12_local" if es_local else "v12_visita")
        if xg is not None:
            total_xg += float(xg)
        if xga is not None:
            total_xga += float(xga)
    return total_xg, total_xga


def _duelos_h2h(corpus: Corpus, local: str, visita: str, momento: datetime) -> List[Dict[str, Any]]:
    """Serie histórica en la perspectiva del fixture evaluado (`[LN-QBE-020-C]`)."""
    duelos: List[Dict[str, Any]] = []
    for fila in corpus.h2h(local, visita, momento):
        goles_local = fila.get("home_goals")
        goles_visita = fila.get("away_goals")
        if goles_local is None or goles_visita is None:
            continue
        anfitrion = str(fila.get("home_team_slug"))
        if anfitrion == local:
            pro_local, pro_visita = float(goles_local), float(goles_visita)
        else:
            pro_local, pro_visita = float(goles_visita), float(goles_local)
        duelos.append(
            {
                "dias_antiguedad": (momento - fila["_instante"]).total_seconds() / 86400.0,
                "goles_local": pro_local,
                "goles_visita": pro_visita,
            }
        )
    return duelos


# ═════════════════════════════════════════════════════════════════════════════════════════════
# [SPRINT-50][LN-QBE-039 §7.6] PUENTE DE DATOS — MATRIZ CAUSAL HISTÓRICA
# ═════════════════════════════════════════════════════════════════════════════════════════════
class AcumuladorCausal:
    """Estado pre-kickoff por club y referencia de liga por temporada (cero fuga temporal).

    Para cada partido objetivo entrega:

    * ``local`` / ``visita``: las últimas ``max_filas`` filas del club (una por partido previo),
      que son las COLUMNAS de la matriz causal $M \\in \\mathbb{R}^{n\\times 32}$;
    * ``vector_local`` / ``vector_visita``: media expansiva de esas filas (estado del club);
    * ``medias_liga``: media expansiva de la temporada (referencia de normalización §7.6.3).

    El acumulador se actualiza DESPUÉS de calcular el partido: el encuentro evaluado jamás
    alimenta su propia matriz (cero fuga temporal).
    """

    def __init__(self, max_filas: int = MAX_FILAS_MATRIZ) -> None:
        self.max_filas = int(max_filas)
        self._clubes: Dict[Tuple[str, str], List[Dict[str, float]]] = {}
        self._liga: Dict[str, Dict[str, List[float]]] = {}

    @staticmethod
    def _plano(fila_vector: Optional[Dict[str, Any]], lado: str) -> Dict[str, float]:
        plano: Dict[str, float] = {}
        if not isinstance(fila_vector, dict):
            return plano
        for variable in VARIABLES_CATALOGO:
            valor = fila_vector.get(f"{variable.lower()}_{lado}")
            if not isinstance(valor, (int, float)) or isinstance(valor, bool):
                continue
            # [§7.6.3] El log-diferencial exige dominio positivo: z = ln((v+ε)/(μ+ε)) con ε=0.5.
            # Una celda ≤ −ε no admite normalización ⇒ la variable sale de la matriz y el motor la
            # declara SIN_EVIDENCIA. Prohibido imputar, recortar o inventar un desplazamiento.
            if float(valor) + EPSILON_LOG_NORMALIZACION <= 0.0:
                continue
            plano[variable] = float(valor)
        return plano

    def registrar(
        self,
        temporada: str,
        local: str,
        visita: str,
        vector_local_fila: Optional[Dict[str, Any]],
        vector_visita_fila: Optional[Dict[str, Any]],
    ) -> None:
        """Incorpora las DOS filas del partido ya ocurrido al estado de cada club."""
        for slug, lado, fila in (
            (local, "local", vector_local_fila),
            (visita, "visita", vector_visita_fila),
        ):
            plano = self._plano(fila, lado)
            if not plano:
                continue
            serie = self._clubes.setdefault((temporada, slug), [])
            serie.append(plano)
            if len(serie) > self.max_filas:
                del serie[0]
            cubo = self._liga.setdefault(temporada, {})
            for variable, valor in plano.items():
                acumulado = cubo.setdefault(variable, [0.0, 0])
                acumulado[0] += valor
                acumulado[1] += 1

    @staticmethod
    def _media(serie: Sequence[Dict[str, float]]) -> Dict[str, float]:
        acumulado: Dict[str, List[float]] = {}
        for fila in serie:
            for variable, valor in fila.items():
                cubo = acumulado.setdefault(variable, [0.0, 0])
                cubo[0] += valor
                cubo[1] += 1
        return {
            variable: total / conteo
            for variable, (total, conteo) in acumulado.items()
            if conteo
        }

    def matriz_causal(self, temporada: str, local: str, visita: str) -> Dict[str, Any]:
        """Contrato IPO v2 (`[LN-QBE-039]` §7.6.1) listo para el motor V2."""
        serie_local = list(self._clubes.get((temporada, local), []))
        serie_visita = list(self._clubes.get((temporada, visita), []))
        liga = self._liga.get(temporada, {})
        return {
            "local": [dict(fila) for fila in serie_local],
            "visita": [dict(fila) for fila in serie_visita],
            "vector_local": self._media(serie_local),
            "vector_visita": self._media(serie_visita),
            "medias_liga": {
                variable: total / conteo
                for variable, (total, conteo) in liga.items()
                if conteo
            },
        }


def construir_entrada(
    conexion: sqlite3.Connection,
    corpus: Corpus,
    fila: Dict[str, Any],
    vector: Dict[str, Any],
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Devuelve `raw_match_data` pre-kickoff o el motivo del descarte (sin imputar nada)."""
    momento = _instante(fila.get("fecha_utc"))
    if momento is None:
        return None, "fecha_utc_ilegible"
    local = str(fila.get("home_team_slug") or "")
    visita = str(fila.get("away_team_slug") or "")
    temporada = str(fila.get("temporada") or "")

    xg_h, xga_h = _xg_previo(conexion, corpus, local, momento, temporada)
    xg_a, xga_a = _xg_previo(conexion, corpus, visita, momento, temporada)
    stats_local, pj_local = _agregado(corpus, local, momento, temporada, xg_h, xga_h)
    stats_visita, pj_visita = _agregado(corpus, visita, momento, temporada, xg_a, xga_a)

    if pj_local < PARTIDOS_MINIMOS_SI or pj_visita < PARTIDOS_MINIMOS_SI:
        return None, f"SI_insuficiente(pj_local={pj_local},pj_visita={pj_visita})"

    if local == visita:
        return None, "identidad_de_club_imposible"

    delta_alt = vector.get("v29_local")
    delta_descanso = vector.get("v30_local")

    # [E-50.1 §P-01] Operadores C-2: la ausencia viaja como `None` («no publicado» ⇒ operador no
    # aplicado y declarado en la traza). Prohibido convertirla en `0.0` fabricado.
    return (
        {
            "home_team_stats": stats_local,
            "away_team_stats": stats_visita,
            "home_team_slug": local,
            "away_team_slug": visita,
            "delta_alt_metros": float(delta_alt) if delta_alt is not None else None,
            "delta_descanso_dias": float(delta_descanso) if delta_descanso is not None else None,
            "h2h_matches": _duelos_h2h(corpus, local, visita, momento),
        },
        None,
    )


# ═════════════════════════════════════════════════════════════════════════════════════════════
# Cálculo y persistencia
# ═════════════════════════════════════════════════════════════════════════════════════════════
def _respaldo_worm(db_path: Path) -> Path:
    destino = db_path.parent / "backups" / (
        f"{db_path.stem}_pre_distribuciones_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.db"
    )
    destino.parent.mkdir(parents=True, exist_ok=True)
    origen = sqlite3.connect(str(db_path))
    copia = sqlite3.connect(str(destino))
    try:
        origen.backup(copia)
    finally:
        copia.close()
        origen.close()
    return destino


def _insert(tabla: str = TABLA_DESTINO) -> str:
    columnas = [
        "match_id", "temporada", "model_version", "p_local", "p_empate", "p_visitante",
        "lambda_home", "lambda_away", "phi_lead2_home", "phi_lead2_away", "epistemic_delta",
        "delta_epist", "origen_factores", "es_operable", "pj_home", "pj_away", "duelos_h2h",
        "variables_con_evidencia", "origen", "fuente_causal", "audit_trace_json", "created_at",
    ]
    marcadores = ", ".join("?" for _ in columnas)
    return f"INSERT OR REPLACE INTO {tabla} ({', '.join(columnas)}) VALUES ({marcadores})"


def _metricas_brier(evaluables: Sequence[Tuple[Any, ...]]) -> Dict[str, Any]:
    """[LN-QBE-100] Brier multiclase 3N de la P' generada y Alpha de calibración vs mercado.

    * `brier_qbe`: sobre todo partido con marcador legible.
    * `brier_mercado` y `alpha`: sobre la MISMA intersección (marcador + cuotas de-vig),
      para que la comparación sea homogénea. `alpha = (1 − BS_qbe/BS_mercado)·100`.
    """
    total_qbe = 0.0
    total_mercado = 0.0
    total_qbe_mercado = 0.0
    n_qbe = 0
    n_mercado = 0
    for p_local, p_empate, p_visitante, goles_local, goles_visita, odd_h, odd_x, odd_a in evaluables:
        if goles_local is None or goles_visita is None:
            continue
        local, visita = int(goles_local), int(goles_visita)
        brier = brier_multiclase(float(p_local), float(p_empate), float(p_visitante), local, visita)
        total_qbe += brier
        n_qbe += 1
        if odd_h is None or odd_x is None or odd_a is None:
            continue
        cuotas = (float(odd_h), float(odd_x), float(odd_a))
        if min(cuotas) <= 1.0:
            continue
        inversas = [1.0 / cuota for cuota in cuotas]
        suma = sum(inversas)
        mercado = [inversa / suma for inversa in inversas]
        total_mercado += brier_multiclase(mercado[0], mercado[1], mercado[2], local, visita)
        total_qbe_mercado += brier
        n_mercado += 1

    brier_qbe = total_qbe / n_qbe if n_qbe else None
    brier_mercado = total_mercado / n_mercado if n_mercado else None
    alpha = None
    if n_mercado and brier_mercado:
        alpha = (1.0 - (total_qbe_mercado / n_mercado) / brier_mercado) * 100.0
    return {
        "n_qbe": n_qbe,
        "n_mercado": n_mercado,
        "brier_qbe": brier_qbe,
        "brier_mercado": brier_mercado,
        "brier_qbe_misma_muestra": (total_qbe_mercado / n_mercado) if n_mercado else None,
        "alpha_pct": alpha,
    }


def calcular(
    db_path: Path,
    temporada: Optional[str] = None,
    *,
    dry_run: bool = False,
    motor: str = MOTOR_V2,
    pesos: Optional[Dict[str, float]] = None,
    salida: Any = None,
) -> Dict[str, Any]:
    """Calcula la P' histórica. `motor` = `v2` (GSL-3D v2, estándar), `v3` (v2 + β) o `v1`.

    La ruta V2 construye la matriz causal de cada club con sus partidos previos de la temporada
    y la inyecta al motor; la V3 añade el vector β (Lasso) al contrato de la matriz, que el
    motor aplica PRE-Gram-Schmidt ([E-50.4 §T2]); la V1 conserva el comportamiento histórico.
    """
    if motor not in MOTORES:
        raise CalculoError(f"Motor desconocido: {motor!r}. Válidos: {MOTORES}.")
    tabla_destino = TABLAS_POR_MOTOR[motor]
    version_modelo = VERSIONES_POR_MOTOR[motor]
    if motor == MOTOR_V3 and not pesos:
        raise CalculoError("El motor v3 exige el vector β (`pesos`); sin él es idéntico a v2.")

    salida = salida or sys.stdout
    if not db_path.is_file():
        raise CalculoError(f"Bóveda inexistente: {db_path}")

    conexion = sqlite3.connect(str(db_path), isolation_level=None)
    conexion.execute("PRAGMA foreign_keys = ON")
    try:
        conexion.execute(_ddl(tabla_destino))
        parametros: Tuple[Any, ...] = ()
        filtro = ""
        if temporada:
            filtro = "AND m.temporada = ?"
            parametros = (temporada,)
        candidatos = _filas(
            conexion,
            f"""
            SELECT m.*, v.match_id AS vector_match_id
              FROM {TABLA_BOVEDA} m
              JOIN {TABLA_VECTOR} v ON v.match_id = m.match_id
             WHERE 1 = 1 {filtro}
             ORDER BY m.fecha_utc, m.match_id
            """,
            parametros,
        )
        if not candidatos:
            raise CalculoError(
                f"Sin partidos con vector causal para '{temporada or 'toda la bóveda'}'."
            )

        corpus = Corpus(_filas(conexion, f"SELECT * FROM {TABLA_BOVEDA}"))
        acumulador = AcumuladorCausal()

        generadas: List[Tuple[str, float, float, float]] = []
        evaluables: List[Tuple[Any, ...]] = []
        saltados: List[Dict[str, str]] = []
        filas_insert: List[Tuple[Any, ...]] = []

        for fila in candidatos:
            match_id = str(fila["match_id"])
            temporada_fila = str(fila.get("temporada") or "")
            vector = _vector_de(conexion, match_id)
            if vector is None:
                saltados.append(
                    {"match_id": match_id, "temporada": temporada_fila, "motivo": "sin_vector_causal"}
                )
                continue
            # [LN-QBE-150] Trazabilidad: la procedencia del símplex es la del vector que lo alimentó.
            procedencia = str(vector.get("fuente_datos") or "").strip()
            if not procedencia:
                saltados.append(
                    {
                        "match_id": match_id,
                        "temporada": temporada_fila,
                        "motivo": "vector_sin_procedencia",
                    }
                )
                continue
            entrada, motivo = construir_entrada(conexion, corpus, fila, vector)
            if entrada is None:
                saltados.append(
                    {"match_id": match_id, "temporada": temporada_fila, "motivo": str(motivo)}
                )
                acumulador.registrar(
                    temporada_fila,
                    str(fila.get("home_team_slug") or ""),
                    str(fila.get("away_team_slug") or ""),
                    vector,
                    vector,
                )
                continue

            # [SPRINT-50][§7.6] Puente de datos: matriz causal de ambos clubes (rutas V2/V3).
            if motor in (MOTOR_V2, MOTOR_V3):
                matriz = acumulador.matriz_causal(
                    temporada_fila,
                    str(fila.get("home_team_slug") or ""),
                    str(fila.get("away_team_slug") or ""),
                )
                if motor == MOTOR_V3:
                    matriz["pesos"] = {clave: float(valor) for clave, valor in (pesos or {}).items()}
                entrada["matriz_causal"] = matriz

            try:
                salida_core = generar_distribucion_soberana(
                    match_id,
                    entrada,
                    delta_alt_metros=entrada["delta_alt_metros"],
                    delta_descanso_dias=entrada["delta_descanso_dias"],
                )
            except (ValueError, ZeroDivisionError, AssertionError) as error:
                saltados.append(
                    {
                        "match_id": match_id,
                        "temporada": temporada_fila,
                        "motivo": f"{type(error).__name__}: {error}",
                    }
                )
                acumulador.registrar(
                    temporada_fila,
                    str(fila.get("home_team_slug") or ""),
                    str(fila.get("away_team_slug") or ""),
                    vector,
                    vector,
                )
                continue

            # El partido ya ocurrió: entra al estado de ambos clubes DESPUÉS de calcularlo.
            acumulador.registrar(
                temporada_fila,
                str(fila.get("home_team_slug") or ""),
                str(fila.get("away_team_slug") or ""),
                vector,
                vector,
            )

            if not salida_core.es_operable:
                motivo_motor = getattr(salida_core.audit_trace, "motivo_insuficiencia", None) or ""
                clave_motivo = (
                    "matriz_causal_insuficiente"
                    if "MATRIZ_CAUSAL_INSUFICIENTE" in motivo_motor
                    else "S(I)=0 declarado por el motor"
                )
                saltados.append(
                    {
                        "match_id": match_id,
                        "temporada": temporada_fila,
                        "motivo": f"{clave_motivo} [{motivo_motor}]" if motivo_motor else clave_motivo,
                    }
                )
                continue

            traza = salida_core.audit_trace.model_dump()
            filas_insert.append(
                (
                    match_id,
                    str(fila.get("temporada") or ""),
                    version_modelo,
                    float(salida_core.p_local),
                    float(salida_core.p_empate),
                    float(salida_core.p_visitante),
                    float(salida_core.lambda_home),
                    float(salida_core.lambda_away),
                    float(salida_core.phi_lead2_home),
                    float(salida_core.phi_lead2_away),
                    float(salida_core.epistemic_delta),
                    float(salida_core.delta_epist),
                    str(salida_core.origen_factores),
                    1,
                    int(entrada["home_team_stats"]["pj"]),
                    int(entrada["away_team_stats"]["pj"]),
                    len(entrada["h2h_matches"]),
                    _evidencia(vector),
                    ORIGEN,
                    procedencia,
                    json.dumps(traza, ensure_ascii=False, default=str),
                    datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                )
            )
            generadas.append(
                (
                    match_id,
                    float(salida_core.p_local),
                    float(salida_core.p_empate),
                    float(salida_core.p_visitante),
                )
            )
            evaluables.append(
                (
                    float(salida_core.p_local),
                    float(salida_core.p_empate),
                    float(salida_core.p_visitante),
                    fila.get("home_goals"),
                    fila.get("away_goals"),
                    fila.get("odd_home"),
                    fila.get("odd_draw"),
                    fila.get("odd_away"),
                )
            )

        respaldo = None
        if filas_insert and not dry_run:
            respaldo = _respaldo_worm(db_path)
            conexion.execute("BEGIN IMMEDIATE")
            try:
                for valores in filas_insert:
                    conexion.execute(_insert(tabla_destino), valores)
                conexion.execute("COMMIT")
            except BaseException:
                conexion.execute("ROLLBACK")
                raise

        integridad = conexion.execute("PRAGMA quick_check").fetchone()[0]
        total = conexion.execute(f"SELECT COUNT(*) FROM {tabla_destino}").fetchone()[0]
    finally:
        conexion.close()

    motivos: Dict[str, int] = {}
    for registro in saltados:
        motivos[registro["motivo"].split("(")[0]] = motivos.get(registro["motivo"].split("(")[0], 0) + 1

    # [Tarea 2] Agrupación por temporada: ¿el cold start `SI_insuficiente` es global o local?
    motivos_por_temporada: Dict[str, Dict[str, int]] = {}
    for registro in saltados:
        temporada_registro = registro.get("temporada") or "(sin temporada)"
        clave = registro["motivo"].split("(")[0]
        cubo = motivos_por_temporada.setdefault(temporada_registro, {})
        cubo[clave] = cubo.get(clave, 0) + 1

    return {
        "temporada": temporada,
        "candidatos": len(candidatos),
        "generadas": len(generadas),
        "saltadas": len(saltados),
        "detalle_saltadas": saltados,
        "motivos": motivos,
        "motivos_por_temporada": motivos_por_temporada,
        "filas_tabla": total,
        "integridad": integridad,
        "respaldo_worm": str(respaldo) if respaldo else None,
        "dry_run": dry_run,
        "motor": motor,
        "tabla": tabla_destino,
        "model_version": version_modelo,
        "brier": _metricas_brier(evaluables),
        "muestra": [
            {"match_id": m, "p_local": round(p1, 4), "p_empate": round(px, 4), "p_visitante": round(p2, 4)}
            for m, p1, px, p2 in generadas[:5]
        ],
        "promedio_simplex": (
            [round(sum(fila[i] for fila in generadas) / len(generadas), 4) for i in (1, 2, 3)]
            if generadas
            else []
        ),
    }


def _num(valor: Any, decimales: int = 6) -> str:
    """Formato estable para métricas que pueden no existir (None ⇒ `—`)."""
    if valor is None:
        return "—"
    return f"{float(valor):.{decimales}f}"


def _tablero(reporte: Dict[str, Any]) -> None:
    print("=" * 78)
    print(f"P' HISTÓRICO — temporada {reporte['temporada'] or 'TODAS'}  [LN-QBE-150]")
    print("=" * 78)
    print(f"Motor                      : {reporte.get('motor', MOTOR_V1)} · {reporte.get('model_version', MODEL_VERSION)}")
    print(f"Tabla destino              : {reporte.get('tabla', TABLA_DESTINO)}")
    print(f"Partidos con vector causal : {reporte['candidatos']}")
    print(f"Distribuciones generadas   : {reporte['generadas']}")
    print(f"Partidos saltados          : {reporte['saltadas']}")
    print(f"Filas en la tabla          : {reporte['filas_tabla']}")
    print(f"PRAGMA quick_check         : {reporte['integridad']}")
    print(f"Respaldo WORM              : {reporte['respaldo_worm'] or '—'}")
    print(f"Modo dry-run               : {reporte['dry_run']}")
    metricas = reporte.get("brier") or {}
    if metricas:
        print("-" * 78)
        print("Brier multiclase 3N [LN-QBE-100] · Alpha de calibración")
        print(f"  QBE      : {_num(metricas.get('brier_qbe'))}   (N={metricas.get('n_qbe')})")
        print(f"  Mercado  : {_num(metricas.get('brier_mercado'))}   (N={metricas.get('n_mercado')})")
        print(f"  QBE∩Merc.: {_num(metricas.get('brier_qbe_misma_muestra'))}")
        print(f"  Alpha    : {_num(metricas.get('alpha_pct'), 2)} %")
    if reporte["promedio_simplex"]:
        p1, px, p2 = reporte["promedio_simplex"]
        print(f"Símplex promedio           : 1={p1}  X={px}  2={p2}  (suma {round(p1+px+p2, 6)})")
    print("-" * 78)
    print("Motivos de descarte:")
    for motivo, cantidad in sorted(reporte["motivos"].items(), key=lambda par: -par[1]):
        print(f"  {cantidad:>4}  {motivo}")
    print("-" * 78)
    print("Motivos por temporada:")
    for temporada, cubo in sorted(reporte["motivos_por_temporada"].items()):
        detalle = ", ".join(f"{clave}={valor}" for clave, valor in sorted(cubo.items()))
        print(f"  {temporada}: {detalle}")
    print("-" * 78)
    print("Muestra:")
    for fila in reporte["muestra"]:
        print(
            f"  {fila['match_id']}: 1={fila['p_local']} X={fila['p_empate']} 2={fila['p_visitante']}"
        )


def main(argv: Optional[Sequence[str]] = None) -> int:
    analizador = argparse.ArgumentParser(
        prog="calcular_distribuciones_historicas",
        description="[LN-QBE-150] Calcula la distribución soberana P' histórica por partido.",
    )
    analizador.add_argument("--temporada", default=None, help="p. ej. 2018_2019 (omite: todas)")
    analizador.add_argument("--db", default=str(DB_DEFECTO), help="ruta de qbe_historico.db")
    analizador.add_argument("--dry-run", action="store_true", help="calcula sin persistir")
    analizador.add_argument(
        "--motor",
        default=MOTOR_V2,
        choices=list(MOTORES),
        help="v2 = GSL-3D v2 con matriz causal (estándar); v1 = baseline sellado (sólo agregados)",
    )
    analizador.add_argument("--reporte-json", default=None, help="bitácora del cálculo (JSON)")
    analizador.add_argument(
        "--pesos",
        default=None,
        help="[E-50.6] ruta del JSON {V##: β} para el motor v3 (Lasso). Obligatorio con --motor v3.",
    )
    argumentos = analizador.parse_args(argv)

    pesos = None
    if argumentos.pesos:
        ruta_pesos = Path(argumentos.pesos)
        if not ruta_pesos.is_file():
            print(f"🔴 Pesos inexistentes: {ruta_pesos}", file=sys.stderr)
            return 1
        pesos = json.loads(ruta_pesos.read_text(encoding="utf-8"))
        if not isinstance(pesos, dict) or not pesos:
            print("🔴 El archivo de pesos debe ser un objeto {V##: β} no vacío.", file=sys.stderr)
            return 1

    try:
        reporte = calcular(
            Path(argumentos.db),
            argumentos.temporada,
            dry_run=argumentos.dry_run,
            motor=argumentos.motor,
            pesos=pesos,
        )
    except (CalculoError, sqlite3.Error) as error:
        print(f"🔴 {error}", file=sys.stderr)
        return 1

    if argumentos.reporte_json:
        ruta = Path(argumentos.reporte_json)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(json.dumps(reporte, ensure_ascii=False, indent=2), encoding="utf-8")

    _tablero(reporte)
    return 0 if reporte["integridad"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
