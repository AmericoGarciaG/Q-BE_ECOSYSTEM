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

DB_DEFECTO = RAIZ_PROYECTO / "qbe_observatory" / "data" / "qbe_historico.db"
TABLA_VECTOR = "historical_match_causal_vars"
TABLA_BOVEDA = "historical_matches"
TABLA_DESTINO = "historical_sovereign_distributions"

MODEL_VERSION = "v13.0-DIRGEN"
ORIGEN = "HISTORICO_SPRINT48"
#: `fuente_causal` NO es constante: se hereda del vector (`historical_match_causal_vars.fuente_datos`).
FUENTE_SIN_PROCEDENCIA = "SIN_PROCEDENCIA"
PARTIDOS_MINIMOS_SI = 3  # [LN-QBE-035-B] S(I_i): suficiencia informativa

#: Ganancia de contexto declarada al motor sellado (`[ARCH-1.5.1]` §CQRS — sólo transporte).
VARIABLES_CONTEXTO = ("V29", "V30")

DDL = f"""
CREATE TABLE IF NOT EXISTS {TABLA_DESTINO} (
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

    return (
        {
            "home_team_stats": stats_local,
            "away_team_stats": stats_visita,
            "home_team_slug": local,
            "away_team_slug": visita,
            "delta_alt_metros": float(delta_alt) if delta_alt is not None else 0.0,
            "delta_descanso_dias": float(delta_descanso) if delta_descanso is not None else 0.0,
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


def _insert() -> str:
    columnas = [
        "match_id", "temporada", "model_version", "p_local", "p_empate", "p_visitante",
        "lambda_home", "lambda_away", "phi_lead2_home", "phi_lead2_away", "epistemic_delta",
        "delta_epist", "origen_factores", "es_operable", "pj_home", "pj_away", "duelos_h2h",
        "variables_con_evidencia", "origen", "fuente_causal", "audit_trace_json", "created_at",
    ]
    marcadores = ", ".join("?" for _ in columnas)
    return f"INSERT OR REPLACE INTO {TABLA_DESTINO} ({', '.join(columnas)}) VALUES ({marcadores})"


def calcular(
    db_path: Path,
    temporada: Optional[str] = None,
    *,
    dry_run: bool = False,
    salida: Any = None,
) -> Dict[str, Any]:
    salida = salida or sys.stdout
    if not db_path.is_file():
        raise CalculoError(f"Bóveda inexistente: {db_path}")

    conexion = sqlite3.connect(str(db_path), isolation_level=None)
    conexion.execute("PRAGMA foreign_keys = ON")
    try:
        conexion.execute(DDL)
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
             ORDER BY m.fecha_utc
            """,
            parametros,
        )
        if not candidatos:
            raise CalculoError(
                f"Sin partidos con vector causal para '{temporada or 'toda la bóveda'}'."
            )

        corpus = Corpus(_filas(conexion, f"SELECT * FROM {TABLA_BOVEDA}"))

        generadas: List[Tuple[str, float, float, float]] = []
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
                continue
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
                continue

            if not salida_core.es_operable:
                saltados.append(
                    {
                        "match_id": match_id,
                        "temporada": temporada_fila,
                        "motivo": "S(I)=0 declarado por el motor",
                    }
                )
                continue

            traza = salida_core.audit_trace.model_dump()
            filas_insert.append(
                (
                    match_id,
                    str(fila.get("temporada") or ""),
                    MODEL_VERSION,
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

        respaldo = None
        if filas_insert and not dry_run:
            respaldo = _respaldo_worm(db_path)
            conexion.execute("BEGIN IMMEDIATE")
            try:
                for valores in filas_insert:
                    conexion.execute(_insert(), valores)
                conexion.execute("COMMIT")
            except BaseException:
                conexion.execute("ROLLBACK")
                raise

        integridad = conexion.execute("PRAGMA quick_check").fetchone()[0]
        total = conexion.execute(f"SELECT COUNT(*) FROM {TABLA_DESTINO}").fetchone()[0]
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


def _tablero(reporte: Dict[str, Any]) -> None:
    print("=" * 78)
    print(f"P' HISTÓRICO — temporada {reporte['temporada'] or 'TODAS'}  [LN-QBE-150]")
    print("=" * 78)
    print(f"Partidos con vector causal : {reporte['candidatos']}")
    print(f"Distribuciones generadas   : {reporte['generadas']}")
    print(f"Partidos saltados          : {reporte['saltadas']}")
    print(f"Filas en la tabla          : {reporte['filas_tabla']}")
    print(f"PRAGMA quick_check         : {reporte['integridad']}")
    print(f"Respaldo WORM              : {reporte['respaldo_worm'] or '—'}")
    print(f"Modo dry-run               : {reporte['dry_run']}")
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
    analizador.add_argument("--reporte-json", default=None, help="bitácora del cálculo (JSON)")
    argumentos = analizador.parse_args(argv)

    try:
        reporte = calcular(
            Path(argumentos.db), argumentos.temporada, dry_run=argumentos.dry_run
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
