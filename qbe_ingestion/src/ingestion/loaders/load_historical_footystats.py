# -*- coding: utf-8 -*-
"""Carga masiva idempotente del corpus histórico FootyStats a la bóveda OLAP.

[LN-QBE-135] / [ARCH-1.4.72]

Régimen: `[DBBD-FUNGIBLE]` en la orquestación; `[DIRGEN-STRICT]` en el
contrato de persistencia (idempotencia, transacción atómica, NULL honesto).

Destino: `qbe_observatory/data/qbe_historico.db`.
Tablas: `historical_matches`, `historical_team_season_stats`, `historical_load_log`.
No toca `matches`, `sovereign_distributions` ni `match_telemetry`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine

RAIZ_PROYECTO = Path(__file__).resolve().parents[4]
JSON_ROOT = RAIZ_PROYECTO / "data" / "extracted_footystats"
DB_DEFECTO = RAIZ_PROYECTO / "qbe_observatory" / "data" / "qbe_historico.db"

FUENTE_DATOS = "FOOTYSTATS_MHTML"

_PATRON_TEMPORADA = re.compile(r"(\d{4})\s*[/\-_]\s*(\d{2,4})")

DDL = (
    """
    CREATE TABLE IF NOT EXISTS historical_matches (
        match_id       TEXT PRIMARY KEY,
        temporada      TEXT NOT NULL,
        match_ref      TEXT,
        fecha_utc      TEXT,
        fecha_epoch    INTEGER,
        home_team      TEXT NOT NULL,
        away_team      TEXT NOT NULL,
        home_team_slug TEXT,
        away_team_slug TEXT,
        home_team_id   INTEGER,
        away_team_id   INTEGER,
        home_goals     INTEGER,
        away_goals     INTEGER,
        odd_home       REAL,
        odd_draw       REAL,
        odd_away       REAL,
        xg_home        REAL,
        xg_away        REAL,
        fuente_datos   TEXT NOT NULL DEFAULT 'FOOTYSTATS_MHTML',
        cargado_utc    TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS historical_team_season_stats (
        temporada    TEXT NOT NULL,
        team         TEXT NOT NULL,
        team_slug    TEXT NOT NULL,
        xg           REAL,
        xga          REAL,
        xgd          REAL,
        gf           REAL,
        ga           REAL,
        xg_vs_actual REAL,
        fuente_xg    TEXT,
        mp_last5     INTEGER,
        w_last5      INTEGER,
        d_last5      INTEGER,
        l_last5      INTEGER,
        gf_last5     INTEGER,
        ga_last5     INTEGER,
        gd_last5     INTEGER,
        pts_last5    INTEGER,
        forma_last5  TEXT,
        ppg_last5    REAL,
        cs_pct       REAL,
        fts_pct      REAL,
        btts_pct     REAL,
        cargado_utc  TEXT NOT NULL,
        PRIMARY KEY (temporada, team_slug)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS historical_load_log (
        temporada   TEXT PRIMARY KEY,
        partidos    INTEGER NOT NULL,
        equipos     INTEGER NOT NULL,
        sha256_json TEXT NOT NULL,
        cargado_utc TEXT NOT NULL,
        estado      TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_hist_matches_temporada ON historical_matches(temporada)",
    "CREATE INDEX IF NOT EXISTS idx_hist_matches_equipos ON historical_matches(home_team_slug, away_team_slug)",
)

_COLUMNAS_MATCHES: Dict[str, str] = {
    "match_ref": "TEXT",
    "fecha_utc": "TEXT",
    "fecha_epoch": "INTEGER",
    "home_team_slug": "TEXT",
    "away_team_slug": "TEXT",
    "home_team_id": "INTEGER",
    "away_team_id": "INTEGER",
    "xg_home": "REAL",
    "xg_away": "REAL",
    "fuente_datos": "TEXT",
    "cargado_utc": "TEXT",
}

_INSERT_MATCHES = """
INSERT INTO historical_matches (
    match_id, temporada, match_ref, fecha_utc, fecha_epoch,
    home_team, away_team, home_team_slug, away_team_slug,
    home_team_id, away_team_id, home_goals, away_goals,
    odd_home, odd_draw, odd_away, xg_home, xg_away,
    fuente_datos, cargado_utc
) VALUES (
    :match_id, :temporada, :match_ref, :fecha_utc, :fecha_epoch,
    :home_team, :away_team, :home_team_slug, :away_team_slug,
    :home_team_id, :away_team_id, :home_goals, :away_goals,
    :odd_home, :odd_draw, :odd_away, :xg_home, :xg_away,
    :fuente_datos, :cargado_utc
)
"""

_INSERT_STATS = """
INSERT INTO historical_team_season_stats (
    temporada, team, team_slug, xg, xga, xgd, gf, ga, xg_vs_actual, fuente_xg,
    mp_last5, w_last5, d_last5, l_last5, gf_last5, ga_last5, gd_last5,
    pts_last5, forma_last5, ppg_last5, cs_pct, fts_pct, btts_pct, cargado_utc
) VALUES (
    :temporada, :team, :team_slug, :xg, :xga, :xgd, :gf, :ga, :xg_vs_actual, :fuente_xg,
    :mp_last5, :w_last5, :d_last5, :l_last5, :gf_last5, :ga_last5, :gd_last5,
    :pts_last5, :forma_last5, :ppg_last5, :cs_pct, :fts_pct, :btts_pct, :cargado_utc
)
"""

_INSERT_LOG = """
INSERT OR REPLACE INTO historical_load_log
    (temporada, partidos, equipos, sha256_json, cargado_utc, estado)
VALUES (:temporada, :partidos, :equipos, :sha256_json, :cargado_utc, :estado)
"""


# ── Utilidades ────────────────────────────────────────────────────────────────────────────────
def normalizar_temporada(valor: Optional[str]) -> Optional[str]:
    if not valor:
        return None
    coincide = _PATRON_TEMPORADA.search(str(valor))
    if not coincide:
        return None
    inicio, fin = coincide.group(1), coincide.group(2)
    if len(fin) == 2:
        fin = inicio[:2] + fin
    return f"{inicio}_{fin}"


def slugify(valor: Any) -> Optional[str]:
    """Canoniza `Tigres UANL`, `tigres-uanl`, `León` → slug estable."""
    if valor is None:
        return None
    texto = unicodedata.normalize("NFKD", str(valor))
    texto = texto.encode("ascii", "ignore").decode("ascii").lower()
    texto = re.sub(r"[^a-z0-9]+", "-", texto).strip("-")
    return texto or None


def _ahora_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _fecha(valor: Any) -> Tuple[Optional[str], Optional[int]]:
    """Acepta epoch (int/str numérico) o ISO-8601. Devuelve (ISO, epoch)."""
    if valor is None or valor == "":
        return None, None
    if isinstance(valor, (int, float)):
        epoch = int(valor)
    else:
        texto = str(valor).strip()
        if texto.lstrip("-").isdigit():
            epoch = int(texto)
        else:
            try:
                momento = datetime.fromisoformat(texto.replace("Z", "+00:00"))
            except ValueError:
                return None, None
            if momento.tzinfo is None:
                momento = momento.replace(tzinfo=timezone.utc)
            epoch = int(momento.timestamp())
    iso = datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat().replace("+00:00", "Z")
    return iso, epoch


def _numero(valor: Any, entero: bool = False) -> Optional[float]:
    if valor is None or valor == "":
        return None
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return int(numero) if entero else numero


def _texto(valor: Any) -> Optional[str]:
    if valor is None:
        return None
    texto = str(valor).strip()
    return texto or None


def _lista_partidos(datos: Dict[str, Any]) -> List[Dict[str, Any]]:
    crudo = datos.get("fixtures")
    if crudo is None:
        crudo = datos.get("partidos")
    return list(crudo or [])


def _match_id(partido: Dict[str, Any], temporada: str) -> str:
    explicito = _texto(partido.get("match_id"))
    if explicito:
        return explicito
    referencia = _texto(partido.get("match_ref"))
    if referencia:
        return f"fs_{temporada}_{referencia}"
    local = slugify(partido.get("home_team")) or "local"
    visita = slugify(partido.get("away_team")) or "visita"
    _, epoch = _fecha(partido.get("fecha_utc"))
    sufijo = str(epoch) if epoch is not None else "sinfecha"
    return f"fs_{temporada}_{local}_{visita}_{sufijo}"


def _filas_partidos(datos: Dict[str, Any], temporada: str, cargado: str) -> List[Dict[str, Any]]:
    filas: List[Dict[str, Any]] = []
    for partido in _lista_partidos(datos):
        home_team = _texto(partido.get("home_team"))
        away_team = _texto(partido.get("away_team"))
        if not home_team or not away_team:
            continue
        fecha_utc, fecha_epoch = _fecha(partido.get("fecha_utc"))
        filas.append(
            {
                "match_id": _match_id(partido, temporada),
                "temporada": temporada,
                "match_ref": _texto(partido.get("match_ref")),
                "fecha_utc": fecha_utc,
                "fecha_epoch": fecha_epoch,
                "home_team": home_team,
                "away_team": away_team,
                "home_team_slug": slugify(home_team),
                "away_team_slug": slugify(away_team),
                "home_team_id": _numero(partido.get("home_team_id"), entero=True),
                "away_team_id": _numero(partido.get("away_team_id"), entero=True),
                "home_goals": _numero(partido.get("home_goals"), entero=True),
                "away_goals": _numero(partido.get("away_goals"), entero=True),
                "odd_home": _numero(partido.get("odd_home")),
                "odd_draw": _numero(partido.get("odd_draw")),
                "odd_away": _numero(partido.get("odd_away")),
                "xg_home": _numero(partido.get("xg_home")),
                "xg_away": _numero(partido.get("xg_away")),
                "fuente_datos": FUENTE_DATOS,
                "cargado_utc": cargado,
            }
        )
    return filas


def _filas_stats(datos: Dict[str, Any], temporada: str, cargado: str) -> List[Dict[str, Any]]:
    fusion: Dict[str, Dict[str, Any]] = {}
    for entrada in datos.get("xg_macro") or []:
        equipo = _texto(entrada.get("team"))
        slug = slugify(equipo)
        if not slug:
            continue
        fila = fusion.setdefault(slug, {"temporada": temporada, "team": equipo, "team_slug": slug})
        fila.update(
            {
                "xg": _numero(entrada.get("xg")),
                "xga": _numero(entrada.get("xga")),
                "xgd": _numero(entrada.get("xgd")),
                "gf": _numero(entrada.get("gf")),
                "ga": _numero(entrada.get("ga")),
                "xg_vs_actual": _numero(entrada.get("xg_vs_actual")),
                "fuente_xg": _texto(entrada.get("fuente_xg")),
            }
        )
    for entrada in datos.get("forma") or []:
        equipo = _texto(entrada.get("team"))
        slug = slugify(equipo)
        if not slug:
            continue
        fila = fusion.setdefault(slug, {"temporada": temporada, "team": equipo, "team_slug": slug})
        fila.update(
            {
                "mp_last5": _numero(entrada.get("mp_last5"), entero=True),
                "w_last5": _numero(entrada.get("w_last5"), entero=True),
                "d_last5": _numero(entrada.get("d_last5"), entero=True),
                "l_last5": _numero(entrada.get("l_last5"), entero=True),
                "gf_last5": _numero(entrada.get("gf_last5"), entero=True),
                "ga_last5": _numero(entrada.get("ga_last5"), entero=True),
                "gd_last5": _numero(entrada.get("gd_last5"), entero=True),
                "pts_last5": _numero(entrada.get("pts_last5"), entero=True),
                "forma_last5": _texto(entrada.get("forma_last5")),
                "ppg_last5": _numero(entrada.get("ppg_last5")),
                "cs_pct": _numero(entrada.get("cs_pct")),
                "fts_pct": _numero(entrada.get("fts_pct")),
                "btts_pct": _numero(entrada.get("btts_pct")),
            }
        )
    columnas = (
        "xg", "xga", "xgd", "gf", "ga", "xg_vs_actual", "fuente_xg",
        "mp_last5", "w_last5", "d_last5", "l_last5", "gf_last5", "ga_last5",
        "gd_last5", "pts_last5", "forma_last5", "ppg_last5", "cs_pct",
        "fts_pct", "btts_pct",
    )
    filas: List[Dict[str, Any]] = []
    for fila in fusion.values():
        completa = {columna: fila.get(columna) for columna in columnas}
        completa.update({"temporada": temporada, "team": fila["team"], "team_slug": fila["team_slug"], "cargado_utc": cargado})
        filas.append(completa)
    return filas


# ── Esquema ────────────────────────────────────────────────────────────────────────────────────
def _columnas(conn: Connection, tabla: str) -> set:
    return {fila[1] for fila in conn.exec_driver_sql(f'PRAGMA table_info("{tabla}")').fetchall()}


def _asegurar_esquema(engine: Engine) -> None:
    with engine.connect() as conn:
        for sentencia in DDL[:3]:
            conn.exec_driver_sql(sentencia)
        for columna, tipo in _COLUMNAS_MATCHES.items():
            if columna not in _columnas(conn, "historical_matches"):
                conn.exec_driver_sql(
                    f'ALTER TABLE historical_matches ADD COLUMN "{columna}" {tipo}'
                )
        for sentencia in DDL[3:]:
            conn.exec_driver_sql(sentencia)


# ── Carga ──────────────────────────────────────────────────────────────────────────────────────
def inyectar_temporada_en_db(
    db_path: str | Path,
    temporada: str,
    datos: Dict[str, Any],
    sha256_json: Optional[str] = None,
) -> Dict[str, Any]:
    """Purga la temporada y vuelve a insertarla en una única transacción."""
    temporada_norm = normalizar_temporada(temporada)
    if not temporada_norm:
        raise ValueError(f"Temporada no normalizable: {temporada!r}")

    ruta_db = Path(db_path)
    ruta_db.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{ruta_db.as_posix()}", isolation_level="AUTOCOMMIT")
    try:
        _asegurar_esquema(engine)
        cargado = _ahora_utc()
        partidos = _filas_partidos(datos, temporada_norm, cargado)
        equipos = _filas_stats(datos, temporada_norm, cargado)
        registro = {
            "temporada": temporada_norm,
            "partidos": len(partidos),
            "equipos": len(equipos),
            "sha256_json": sha256_json or "",
            "cargado_utc": cargado,
            "estado": "OK",
        }

        with engine.connect() as conn:
            conn.exec_driver_sql("BEGIN IMMEDIATE")
            try:
                conn.execute(text("DELETE FROM historical_matches WHERE temporada = :t"), {"t": temporada_norm})
                conn.execute(text("DELETE FROM historical_team_season_stats WHERE temporada = :t"), {"t": temporada_norm})
                if partidos:
                    conn.execute(text(_INSERT_MATCHES), partidos)
                if equipos:
                    conn.execute(text(_INSERT_STATS), equipos)
                conn.execute(text(_INSERT_LOG), registro)
                conn.exec_driver_sql("COMMIT")
            except Exception:
                conn.exec_driver_sql("ROLLBACK")
                raise
        return registro
    finally:
        engine.dispose()


def _sha256_archivo(ruta: Path) -> str:
    digest = hashlib.sha256()
    with open(ruta, "rb") as manejador:
        for bloque in iter(lambda: manejador.read(1 << 20), b""):
            digest.update(bloque)
    return digest.hexdigest()


def cargar_temporada(json_path: Path, db_path: Path) -> Dict[str, Any]:
    datos = json.loads(Path(json_path).read_text(encoding="utf-8"))
    temporada = datos.get("temporada") or Path(json_path).stem.replace("temporada_", "")
    return inyectar_temporada_en_db(
        db_path, temporada, datos, sha256_json=_sha256_archivo(Path(json_path))
    )


def _tablero(filas: Sequence[Dict[str, Any]]) -> None:
    cabecera = ("TEMPORADA", "PARTIDOS", "CUOTAS 1X2", "XG", "FORMA", "ESTADO")
    cuerpo = [
        (
            f["temporada"],
            str(f["partidos"]),
            str(f.get("cuotas", "-")),
            str(f.get("xg", "-")),
            str(f.get("equipos", "-")),
            f["estado"],
        )
        for f in filas
    ]
    anchos = [max(len(f[i]) for f in [cabecera, *cuerpo]) for i in range(len(cabecera))]
    print(" | ".join(h.ljust(anchos[i]) for i, h in enumerate(cabecera)))
    print("-+-".join("-" * a for a in anchos))
    for fila in cuerpo:
        print(" | ".join(v.ljust(anchos[i]) for i, v in enumerate(fila)))
    print("-+-".join("-" * a for a in anchos))
    print(
        f"TOTAL | {sum(f['partidos'] for f in filas)} | "
        f"{sum(int(f.get('cuotas', 0)) for f in filas)} | "
        f"{sum(int(f.get('xg', 0)) for f in filas)} | "
        f"{sum(int(f['equipos']) for f in filas)} |"
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="load_historical_footystats",
        description="[LN-QBE-135] Carga masiva idempotente del corpus histórico FootyStats.",
    )
    parser.add_argument("--run", action="store_true", help="carga las 12 temporadas")
    parser.add_argument("--temporada", default=None, help="carga una temporada (YYYY_YYYY)")
    parser.add_argument("--db", default=str(DB_DEFECTO), help="ruta de qbe_historico.db")
    parser.add_argument("--json-root", default=str(JSON_ROOT), help="raíz de datasets JSON")
    argumentos = parser.parse_args(argv)

    if not argumentos.run and not argumentos.temporada:
        parser.error("Indique --run o --temporada")

    raiz = Path(argumentos.json_root)
    db = Path(argumentos.db)
    archivos = sorted(raiz.glob("temporada_*.json"))
    if argumentos.temporada:
        objetivo = normalizar_temporada(argumentos.temporada)
        archivos = [a for a in archivos if normalizar_temporada(a.stem.replace("temporada_", "")) == objetivo]
        if not archivos:
            print(f"🔴 Temporada no encontrada: {argumentos.temporada}", file=sys.stderr)
            return 2

    filas: List[Dict[str, Any]] = []
    errores = 0
    for archivo in archivos:
        try:
            registro = cargar_temporada(archivo, db)
        except Exception as error:  # noqa: BLE001 - reporte de lote
            errores += 1
            print(f"🔴 {archivo.name}: {error}", file=sys.stderr)
            continue
        datos = json.loads(archivo.read_text(encoding="utf-8"))
        registro["cuotas"] = datos.get("resumen", {}).get("con_cuotas_1x2", 0)
        registro["xg"] = datos.get("resumen", {}).get("con_xg_macro", 0)
        filas.append(registro)
        print(f"✅ {registro['temporada']} → {registro['partidos']} partidos, {registro['equipos']} equipos")

    print()
    _tablero(filas)
    return 0 if errores == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
