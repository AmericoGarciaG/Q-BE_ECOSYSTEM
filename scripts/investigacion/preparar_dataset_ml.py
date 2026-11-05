# -*- coding: utf-8 -*-
"""`[SPRINT-49]` Tarea 1 (corregida) — Dataset pre-kickoff del laboratorio.

Régimen ``[DIRGEN-STRICT]``. Único punto de contacto con la bóveda: lectura estricta
(``mode=ro``), cero escrituras, cero imputación hacia el motor.

Corrección de fuga temporal (Dictamen del Eco, E1–E6)
-----------------------------------------------------
El vector causal del corpus describe **el propio partido** (conteo de eventos y
estadística del mismo encuentro). Por tanto NO se usa como entrada: cada partido
consume el **promedio expansivo de sus partidos previos**.

* **E1 — Ventana:** media expansiva **por temporada** de los partidos previos del club
  (``fecha_utc`` estrictamente menor). Es la misma ley con la que `[LN-QBE-150]` construyó
  la P' oficial (``Corpus.previos`` / ``_agregado``), lo que hace comparables ML y motor.
* **E2 — Reparto:** ``V01``–``V25`` (evento del partido) se agregan; ``V26``–``V28`` (H2H),
  ``V29`` (Δaltitud), ``V30`` (Δdescanso) y ``V31``–``V32`` (forma de 5) se conservan
  por partido, porque ya son evidencia pre-kickoff por diseño.
* **E3 — Cold start:** club sin previos en la temporada ⇒ ``NaN``, imputado con la mediana
  del ``Train`` (nunca ``0.0`` fabricado). Se cuenta y se declara.
* **E4 — Nulos:** mediana del ``Train`` por (lado, variable); columna íntegramente nula
  ⇒ ``0.0`` declarado.
* **E5 — Evaluación:** el puente `[LN-QBE-147]` consume ``V07``/``V13`` **acumulados**, de
  modo que λ se estima con la producción histórica de remates de cada club.
* **E6 — Congelamiento:** los vectores descartados viven en ``.lab-sprint49/congelado_v1/``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

RAIZ_PROYECTO = Path(__file__).resolve().parents[2]
_RAIZ_CORE = RAIZ_PROYECTO / "qbe_core"
for _ruta in (RAIZ_PROYECTO, _RAIZ_CORE):
    if str(_ruta) not in sys.path:
        sys.path.insert(0, str(_ruta))

from src.core.sovereign.calibrar_perturbacion import (  # noqa: E402
    LAMBDA_MAX,
    LAMBDA_MIN,
    brier_multiclase,
)
from src.core.distribution_dixon_coles import (  # noqa: E402
    calcular_matriz_dixon_coles,
    colapsar_matriz_a_simplex,
)

if hasattr(sys.stdout, "reconfigure"):
    try:  # consola Windows cp1252
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, OSError, ValueError):  # pragma: no cover
        pass

__all__ = [
    "DATASET_META",
    "DATASET_NPZ",
    "DIR_SALIDA",
    "DB_HISTORICO",
    "TEMPORADAS_TEST",
    "TEMPORADAS_TRAIN",
    "brier_canonico",
    "brier_de_vector",
    "cargar_artefactos",
    "evaluar_split",
    "preparar_dataset",
    "verificar_antifuga",
]

DB_HISTORICO = RAIZ_PROYECTO / "qbe_observatory" / "data" / "qbe_historico.db"
DIR_SCRIPTS = Path(__file__).resolve().parent
#: Directorio de artefactos del laboratorio (oculto, fuera de la bóveda y del código).
DIR_SALIDA = RAIZ_PROYECTO / ".lab-sprint49"
DATASET_NPZ = DIR_SALIDA / "dataset_ml.npz"
DATASET_META = DIR_SALIDA / "dataset_ml_meta.json"

TEMPORADAS_TRAIN: Tuple[str, ...] = (
    "2018_2019",
    "2019_2020",
    "2020_2021",
    "2021_2022",
    "2022_2023",
)
TEMPORADAS_TEST: Tuple[str, ...] = (
    "2023_2024",
    "2024_2025",
    "2025_2026",
    "2026_2027",
)
TEMPORADAS_EXCLUIDAS: Tuple[str, ...] = ("2015_2016",)

N_VARIABLES = 23
VERSION_DATASET = "sprint49-v2-prekickoff"

#: [LN-QBE-147] Límites físicos del canal legislado.
LIMITE_V07 = 25.0
LIMITE_V13 = 25.0

#: Variables que el corpus registra como EVENTO DEL PARTIDO (se agregan por media expansiva).
VARIABLES_AGREGADAS: Tuple[str, ...] = tuple(f"V{indice:02d}" for indice in range(1, 26))

#: Columnas de la bóveda que el puente consume (`[LN-QBE-147]` §1).
VARIABLES_CANAL: Tuple[str, ...] = ("V07", "V13")

_SQL_HISTORIAL = """
SELECT m.match_id, m.temporada, m.fecha_utc,
       m.home_team_slug, m.away_team_slug,
       v.*
  FROM historical_match_causal_vars v
  JOIN historical_matches m ON m.match_id = v.match_id
 ORDER BY m.fecha_utc, m.match_id
"""

_SQL_CORPUS = """
SELECT d.match_id,
       m.temporada,
       m.fecha_utc,
       m.home_team_slug,
       m.away_team_slug,
       m.home_goals,
       m.away_goals,
       m.odd_home,
       m.odd_draw,
       m.odd_away,
       d.p_local,
       d.p_empate,
       d.p_visitante
  FROM historical_sovereign_distributions d
  JOIN historical_matches m ON m.match_id = d.match_id
 ORDER BY m.fecha_utc, d.match_id
"""

#: [SPRINT-50] Fuente de la P' de referencia. `V2` es la P' del motor GSL-3D v2.
TABLA_P_DEFECTO = "historical_sovereign_distributions"
TABLA_P_V2 = "historical_sovereign_distributions_v2"
TABLAS_P_PERMITIDAS = (TABLA_P_DEFECTO, TABLA_P_V2)


def _sql_corpus(tabla_p: str) -> str:
    """SQL del corpus P' sobre la tabla autorizada (lista blanca: cero inyección)."""
    if tabla_p not in TABLAS_P_PERMITIDAS:
        raise DatasetError(f"Tabla P' no autorizada: {tabla_p!r}. Válidas: {TABLAS_P_PERMITIDAS}.")
    return _SQL_CORPUS.replace("historical_sovereign_distributions d", f"{tabla_p} d")


class DatasetError(RuntimeError):
    """`[SPRINT-49]` La bóveda no permite construir el dataset."""


# ── Lectura de la bóveda (solo lectura) ──────────────────────────────────────────────────────
def _conectar() -> sqlite3.Connection:
    if not DB_HISTORICO.is_file():
        raise DatasetError(f"Bóveda inexistente: {DB_HISTORICO}")
    conexion = sqlite3.connect(f"file:{DB_HISTORICO.as_posix()}?mode=ro", uri=True)
    conexion.row_factory = sqlite3.Row
    return conexion


def _filas(consulta: str) -> List[Dict[str, Any]]:
    conexion = _conectar()
    try:
        return [dict(fila) for fila in conexion.execute(consulta)]
    finally:
        conexion.close()


def cargar_historial() -> List[Dict[str, Any]]:
    """Los 3,000 partidos con vector causal: materia prima de la media expansiva."""
    filas = _filas(_SQL_HISTORIAL)
    if not filas:
        raise DatasetError("Historial vacío: no hay vectores causales.")
    return filas


def cargar_corpus(tabla_p: str = TABLA_P_DEFECTO) -> List[Dict[str, Any]]:
    """Los partidos con P' almacenada: conjunto de evaluación (V1 por defecto; V2 si se declara)."""
    filas = _filas(_sql_corpus(tabla_p))
    if not filas:
        raise DatasetError(f"Corpus vacío: no hay distribuciones P' en {tabla_p}.")
    return filas


def _epoch(iso: Any) -> int:
    from datetime import datetime, timezone

    if not iso:
        return 0
    try:
        valor = datetime.fromisoformat(str(iso).strip().replace("Z", "+00:00"))
    except ValueError:
        return 0
    if valor.tzinfo is None:
        valor = valor.replace(tzinfo=timezone.utc)
    return int(valor.timestamp())


# ── Selección de las 23 variables (cobertura) ────────────────────────────────────────────────
def seleccionar_variables(filas: Sequence[Dict[str, Any]]) -> Tuple[List[str], Dict[str, int]]:
    """Top-23 variables por filas con al menos un lado no nulo."""
    cobertura: Dict[str, int] = {}
    for indice in range(1, 33):
        variable = f"V{indice:02d}"
        columna_local = f"{variable.lower()}_local"
        columna_visita = f"{variable.lower()}_visita"
        if columna_local not in filas[0]:
            continue
        cobertura[variable] = sum(
            1
            for fila in filas
            if fila.get(columna_local) is not None or fila.get(columna_visita) is not None
        )
    ordenadas = sorted(cobertura.items(), key=lambda par: (-par[1], par[0]))
    elegidas = sorted(nombre for nombre, _ in ordenadas[:N_VARIABLES])
    return elegidas, cobertura


# ── Media expansiva pre-kickoff ─────────────────────────────────────────────────────────────
def _agregar_prekickoff(
    historial: Sequence[Dict[str, Any]], variables: Sequence[str]
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, int]]:
    """Para cada partido, media expansiva de sus previos (misma temporada) por club.

    Devuelve ``({match_id: {...}}, auditoría)``. La fila del partido objetivo NUNCA entra
    en su propio vector: el acumulador se actualiza DESPUÉS de leerlo.
    """
    total = len(variables)
    indice_agregada = np.array(
        [variable in set(VARIABLES_AGREGADAS) for variable in variables], dtype=bool
    )
    columnas_local = [f"{variable.lower()}_local" for variable in variables]
    columnas_visita = [f"{variable.lower()}_visita" for variable in variables]

    acumulado: Dict[Tuple[str, str], Dict[str, Any]] = {}
    salida: Dict[str, Dict[str, Any]] = {}
    auditoria = {
        "filas": 0,
        "violaciones_fecha": 0,
        "violaciones_identidad": 0,
        "filas_cold_start": 0,
        "filas_verificadas": 0,
    }

    for fila in sorted(historial, key=lambda item: (_epoch(item.get("fecha_utc")), str(item.get("match_id")))):
        momento = _epoch(fila.get("fecha_utc"))
        temporada = str(fila.get("temporada") or "")
        match_id = str(fila.get("match_id"))
        equipos = {
            "local": str(fila.get("home_team_slug") or ""),
            "visita": str(fila.get("away_team_slug") or ""),
        }
        registro: Dict[str, Any] = {"match_id": match_id, "temporada": temporada, "fecha": momento}
        previos = {"local": 0, "visita": 0}
        evidencia_max = {"local": -1, "visita": -1}

        for lado, slug in equipos.items():
            estado = acumulado.get((temporada, slug))
            vector = np.full(total, np.nan, dtype=np.float64)
            columnas = columnas_local if lado == "local" else columnas_visita
            for indice, columna in enumerate(columnas):
                if indice_agregada[indice]:
                    if estado is not None and estado["conteo"][indice] > 0:
                        vector[indice] = estado["suma"][indice] / estado["conteo"][indice]
                else:
                    valor = fila.get(columna)
                    if valor is not None:
                        vector[indice] = float(valor)
            registro[lado] = vector
            if estado is not None and estado["ids"]:
                previos[lado] = len(estado["ids"])
                evidencia_max[lado] = int(estado["ultima"])
                auditoria["filas_verificadas"] += 1
                if estado["ultima"] >= momento:
                    auditoria["violaciones_fecha"] += 1
                if match_id in estado["ids"]:
                    auditoria["violaciones_identidad"] += 1

        if previos["local"] == 0 or previos["visita"] == 0:
            auditoria["filas_cold_start"] += 1
        registro["previos_local"] = previos["local"]
        registro["previos_visita"] = previos["visita"]
        registro["evidencia_max_local"] = evidencia_max["local"]
        registro["evidencia_max_visita"] = evidencia_max["visita"]
        salida[match_id] = registro
        auditoria["filas"] += 1

        # Update DESPUÉS: el partido evaluado jamás alimenta su propia fila.
        for lado, slug in equipos.items():
            clave = (temporada, slug)
            estado = acumulado.setdefault(
                clave,
                {
                    "suma": np.zeros(total, dtype=np.float64),
                    "conteo": np.zeros(total, dtype=np.int64),
                    "ultima": -1,
                    "ids": set(),
                },
            )
            columnas = columnas_local if lado == "local" else columnas_visita
            for indice, columna in enumerate(columnas):
                valor = fila.get(columna)
                if valor is not None:
                    estado["suma"][indice] += float(valor)
                    estado["conteo"][indice] += 1
            estado["ultima"] = max(int(estado["ultima"]), momento)
            estado["ids"].add(match_id)

    return salida, auditoria


def verificar_antifuga(agregado: Dict[str, Dict[str, Any]], auditoria: Dict[str, int]) -> List[str]:
    """Prueba anti-fuga estructural: cero excepciones o lista de violaciones."""
    fallos: List[str] = []
    for match_id, registro in agregado.items():
        momento = int(registro["fecha"])
        for lado in ("local", "visita"):
            evidencia = int(registro[f"evidencia_max_{lado}"])
            if evidencia >= momento:
                fallos.append(f"{match_id}: evidencia {lado} {evidencia} >= kickoff {momento}")
    if auditoria["violaciones_fecha"] or auditoria["violaciones_identidad"]:
        fallos.append(
            f"contadores: fecha={auditoria['violaciones_fecha']} identidad={auditoria['violaciones_identidad']}"
        )
    return fallos


# ── Utilidades ──────────────────────────────────────────────────────────────────────────────
def _resultado(filas: Sequence[Dict[str, Any]]) -> np.ndarray:
    salida = np.full(len(filas), -1, dtype=np.int64)
    for indice, fila in enumerate(filas):
        local, visita = fila.get("home_goals"), fila.get("away_goals")
        if local is None or visita is None:
            continue
        if int(local) > int(visita):
            salida[indice] = 0
        elif int(local) == int(visita):
            salida[indice] = 1
        else:
            salida[indice] = 2
    return salida


def _p_base(filas: Sequence[Dict[str, Any]]) -> np.ndarray:
    return np.array(
        [[fila["p_local"], fila["p_empate"], fila["p_visitante"]] for fila in filas],
        dtype=np.float64,
    )


def _mercado(filas: Sequence[Dict[str, Any]]) -> np.ndarray:
    """Símplex de-vig de FootyStats; `NaN` donde no hay cuotas utilizables."""
    salida = np.full((len(filas), 3), np.nan, dtype=np.float64)
    for indice, fila in enumerate(filas):
        cuotas = (fila.get("odd_home"), fila.get("odd_draw"), fila.get("odd_away"))
        if any(cuota is None for cuota in cuotas):
            continue
        cuotas = tuple(float(cuota) for cuota in cuotas)
        if min(cuotas) <= 1.0:
            continue
        inversas = [1.0 / cuota for cuota in cuotas]
        suma = sum(inversas)
        salida[indice] = [inversa / suma for inversa in inversas]
    return salida


def _imputar(
    entrenamiento: np.ndarray, aplicables: Sequence[np.ndarray], lado: str, variables: Sequence[str]
) -> Tuple[List[np.ndarray], Dict[str, Tuple[float, str]]]:
    """Mediana del Train por (lado, variable); columna íntegramente nula ⇒ 0.0 declarado."""
    medianas: Dict[str, Tuple[float, str]] = {}
    for indice_variable, variable in enumerate(variables):
        columna = entrenamiento[:, indice_variable]
        valida = columna[~np.isnan(columna)]
        if valida.size == 0:
            medianas[f"{variable}_{lado}"] = (0.0, "columna_nula_declarada")
        else:
            medianas[f"{variable}_{lado}"] = (float(np.median(valida)), "mediana_train")
    salidas: List[np.ndarray] = []
    for matriz in aplicables:
        copia = matriz.copy()
        for indice_variable, variable in enumerate(variables):
            valor = medianas[f"{variable}_{lado}"][0]
            copia[np.isnan(copia[:, indice_variable]), indice_variable] = valor
        salidas.append(copia)
    return salidas, medianas


# ── Preparación ─────────────────────────────────────────────────────────────────────────────
def preparar_dataset(salida: Optional[Path] = None, tabla_p: str = TABLA_P_DEFECTO) -> Dict[str, Any]:
    """Construye, imputa y persiste el dataset pre-kickoff. Devuelve el resumen."""
    ruta_npz = Path(salida) if salida else DATASET_NPZ
    ruta_meta = ruta_npz.with_name(f"{ruta_npz.stem}_meta.json")
    ruta_npz.parent.mkdir(parents=True, exist_ok=True)

    corpus = cargar_corpus(tabla_p)
    historial = cargar_historial()
    # La cobertura se mide sobre las filas del corpus (las que tienen P' almacenada).
    identificadores = {str(fila.get("match_id")) for fila in corpus}
    variables, cobertura = seleccionar_variables(
        [fila for fila in historial if str(fila.get("match_id")) in identificadores]
    )
    agregado, auditoria = _agregar_prekickoff(historial, variables)
    fallos = verificar_antifuga(agregado, auditoria)
    if fallos:
        raise DatasetError(f"Fuga temporal detectada ({len(fallos)}): {fallos[:3]}")

    temporadas = [str(fila.get("temporada") or "") for fila in corpus]
    mascara_train = np.array([temporada in TEMPORADAS_TRAIN for temporada in temporadas])
    mascara_test = np.array([temporada in TEMPORADAS_TEST for temporada in temporadas])
    mascara_fuera = ~(mascara_train | mascara_test)
    if not mascara_train.any() or not mascara_test.any():
        raise DatasetError("Split vacío: revisar las temporadas legisladas.")

    n = len(corpus)
    local = np.full((n, len(variables)), np.nan, dtype=np.float64)
    visita = np.full((n, len(variables)), np.nan, dtype=np.float64)
    for indice, fila in enumerate(corpus):
        registro = agregado.get(str(fila.get("match_id")))
        if registro is None:
            raise DatasetError(f"Sin registro pre-kickoff para {fila.get('match_id')}")
        local[indice] = registro["local"]
        visita[indice] = registro["visita"]

    # La mediana se estima SOLO con el Train (cero fuga de información).
    locales, medianas = _imputar(
        local[mascara_train],
        [local[mascara_train], local[mascara_test], local[mascara_fuera]],
        "local",
        variables,
    )
    visitas, medianas_visita = _imputar(
        visita[mascara_train],
        [visita[mascara_train], visita[mascara_test], visita[mascara_fuera]],
        "visita",
        variables,
    )
    medianas.update(medianas_visita)

    x_train = locales[0] - visitas[0]
    x_test = locales[1] - visitas[1]
    x_fuera = locales[2] - visitas[2]

    y = _resultado(corpus)
    # [SPRINT-50][E-50.6 §T4] Marcador EXACTO para la NLL (la matriz Dixon-Coles necesita x,y).
    goles_local = np.array(
        [-1 if fila.get("home_goals") is None else int(fila["home_goals"]) for fila in corpus],
        dtype=np.int64,
    )
    goles_visita = np.array(
        [-1 if fila.get("away_goals") is None else int(fila["away_goals"]) for fila in corpus],
        dtype=np.int64,
    )
    p_base = _p_base(corpus)
    mercado = _mercado(corpus)
    fechas = np.array([_epoch(fila.get("fecha_utc")) for fila in corpus], dtype=np.int64)
    previos = np.array(
        [
            [agregado[str(fila["match_id"])]["previos_local"], agregado[str(fila["match_id"])]["previos_visita"]]
            for fila in corpus
        ],
        dtype=np.int64,
    )

    indices_canal = {
        variable: variables.index(variable) for variable in VARIABLES_CANAL if variable in variables
    }
    if len(indices_canal) != len(VARIABLES_CANAL):
        raise DatasetError(f"El vector debe contener el canal {VARIABLES_CANAL}; tiene {variables}.")
    media_v07 = float(
        (
            np.mean(locales[0][:, indices_canal["V07"]])
            + np.mean(visitas[0][:, indices_canal["V07"]])
        )
        / 2.0
    )
    media_v13 = float(
        (
            np.mean(locales[0][:, indices_canal["V13"]])
            + np.mean(visitas[0][:, indices_canal["V13"]])
        )
        / 2.0
    )
    goles_train = y[mascara_train]
    jugados_train = goles_train[goles_train >= 0]
    total_goles = sum(
        int(fila["home_goals"]) + int(fila["away_goals"])
        for fila, dentro in zip(corpus, mascara_train)
        if dentro and fila.get("home_goals") is not None and fila.get("away_goals") is not None
    )
    mu_liga = total_goles / (2.0 * len(jugados_train)) if len(jugados_train) else 1.325

    np.savez_compressed(
        ruta_npz,
        variables=np.array(variables),
        x_train=x_train,
        x_test=x_test,
        x_fuera=x_fuera,
        local_train=locales[0],
        visita_train=visitas[0],
        local_test=locales[1],
        visita_test=visitas[1],
        y_train=y[mascara_train],
        y_test=y[mascara_test],
        y_fuera=y[mascara_fuera],
        goles_local_train=goles_local[mascara_train],
        goles_local_test=goles_local[mascara_test],
        goles_visita_train=goles_visita[mascara_train],
        goles_visita_test=goles_visita[mascara_test],
        p_base_train=p_base[mascara_train],
        p_base_test=p_base[mascara_test],
        mercado_train=mercado[mascara_train],
        mercado_test=mercado[mascara_test],
        fecha_train=fechas[mascara_train],
        fecha_test=fechas[mascara_test],
        previos_train=previos[mascara_train],
        previos_test=previos[mascara_test],
        temporada_train=np.array([t for t, dentro in zip(temporadas, mascara_train) if dentro]),
        temporada_test=np.array([t for t, dentro in zip(temporadas, mascara_test) if dentro]),
    )

    meta = {
        "version": VERSION_DATASET,
        "tabla_p": tabla_p,
        "ventana": "media_expansiva_misma_temporada",
        "variables": variables,
        "variables_agregadas": list(VARIABLES_AGREGADAS),
        "cobertura": cobertura,
        "medianas": {clave: valor for clave, (valor, _) in medianas.items()},
        "origen_imputacion": {clave: origen for clave, (_, origen) in medianas.items()},
        "temporadas_train": list(TEMPORADAS_TRAIN),
        "temporadas_test": list(TEMPORADAS_TEST),
        "temporadas_excluidas": list(TEMPORADAS_EXCLUIDAS),
        "n_train": int(mascara_train.sum()),
        "n_test": int(mascara_test.sum()),
        "n_fuera": int(mascara_fuera.sum()),
        "n_test_con_marcador": int((y[mascara_test] >= 0).sum()),
        "n_test_con_mercado": int((~np.isnan(mercado[mascara_test][:, 0])).sum()),
        "antifuga": {
            "filas_historial": int(auditoria["filas"]),
            "filas_verificadas": int(auditoria["filas_verificadas"]),
            "violaciones_fecha": int(auditoria["violaciones_fecha"]),
            "violaciones_identidad": int(auditoria["violaciones_identidad"]),
            "filas_cold_start": int(auditoria["filas_cold_start"]),
        },
        "media_v07": media_v07,
        "media_v13": media_v13,
        "mu_liga": mu_liga,
        "sha256_x_train": hashlib.sha256(x_train.tobytes()).hexdigest(),
        "sha256_x_test": hashlib.sha256(x_test.tobytes()).hexdigest(),
        "sha256_y_train": hashlib.sha256(y[mascara_train].tobytes()).hexdigest(),
    }
    ruta_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


def cargar_artefactos(ruta: Optional[Path] = None) -> Dict[str, Any]:
    """Carga el dataset persistido más su metadata de calibración."""
    ruta_npz = Path(ruta) if ruta else DATASET_NPZ
    ruta_meta = ruta_npz.with_name(f"{ruta_npz.stem}_meta.json")
    if not ruta_npz.is_file() or not ruta_meta.is_file():
        raise DatasetError(
            f"Artefactos ausentes en {ruta_npz.parent}. Ejecutar antes preparar_dataset_ml.py"
        )
    with np.load(ruta_npz, allow_pickle=False) as datos:
        artefactos: Dict[str, Any] = {clave: datos[clave] for clave in datos.files}
    artefactos["variables"] = [str(valor) for valor in artefactos["variables"]]
    artefactos["meta"] = json.loads(ruta_meta.read_text(encoding="utf-8"))
    for clave in ("media_v07", "media_v13", "mu_liga"):
        artefactos[clave] = float(artefactos["meta"][clave])
    return artefactos


# ── Evaluación sobre el puente legislado (`[LN-QBE-147]`) ───────────────────────────────────
def brier_canonico(
    p_local: float, p_empate: float, p_visitante: float, goles_local: int, goles_visita: int
) -> float:
    """Delegación literal en `qbe_core` — cero reimplementación del Juez."""
    return brier_multiclase(p_local, p_empate, p_visitante, int(goles_local), int(goles_visita))


def probabilidades_puente(
    artefactos: Dict[str, Any], split: str, pesos: Sequence[float]
) -> np.ndarray:
    """Recalcula P' con `qbe_core` aplicando los multiplicadores SOLO al canal V07/V13.

    Con `[SPRINT-49 v2]` las columnas ``local_*``/``visita_*`` son medias expansivas
    pre-kickoff: el vector del partido objetivo no contiene ningún dato del partido.
    """
    variables: List[str] = artefactos["variables"]
    indice = {nombre: posicion for posicion, nombre in enumerate(variables)}
    peso = np.asarray(pesos, dtype=np.float64)
    if peso.shape != (len(variables),):
        raise DatasetError(f"Vector de pesos con forma {peso.shape}, se esperaba ({len(variables)},)")
    if not np.all(np.isfinite(peso)):
        raise DatasetError("Vector de pesos con NaN/Inf: calibración inválida.")

    factor_v07 = float(peso[indice["V07"]])
    factor_v13 = float(peso[indice["V13"]])

    local = artefactos[f"local_{split}"][:, indice["V07"]] * factor_v07
    visita = artefactos[f"visita_{split}"][:, indice["V07"]] * factor_v07
    local_def = artefactos[f"local_{split}"][:, indice["V13"]] * factor_v13
    visita_def = artefactos[f"visita_{split}"][:, indice["V13"]] * factor_v13

    local = np.clip(local, 0.0, LIMITE_V07)
    visita = np.clip(visita, 0.0, LIMITE_V07)
    local_def = np.clip(local_def, 0.0, LIMITE_V13)
    visita_def = np.clip(visita_def, 0.0, LIMITE_V13)

    media_v07 = float(artefactos["media_v07"])
    media_v13 = float(artefactos["media_v13"])
    mu_liga = float(artefactos["mu_liga"])

    ataque_local = (local + 1.0) / (media_v07 + 1.0)
    ataque_visita = (visita + 1.0) / (media_v07 + 1.0)
    defensa_local = (local_def + 1.0) / (media_v13 + 1.0)
    defensa_visita = (visita_def + 1.0) / (media_v13 + 1.0)

    lam_local = np.clip(mu_liga * ataque_local / defensa_visita, LAMBDA_MIN, LAMBDA_MAX)
    lam_visita = np.clip(mu_liga * ataque_visita / defensa_local, LAMBDA_MIN, LAMBDA_MAX)

    salida = np.empty((lam_local.shape[0], 3), dtype=np.float64)
    for indice_partido, (lh, la) in enumerate(zip(lam_local, lam_visita)):
        matriz = calcular_matriz_dixon_coles(float(lh), float(la))
        salida[indice_partido] = colapsar_matriz_a_simplex(matriz)
    return salida


def evaluar_split(
    artefactos: Dict[str, Any], split: str, pesos: Sequence[float]
) -> Tuple[float, int, np.ndarray]:
    """Brier canónico medio del split sobre los partidos con marcador real."""
    probabilidades = probabilidades_puente(artefactos, split, pesos)
    y = artefactos[f"y_{split}"]
    mascara = y >= 0
    if not mascara.any():
        raise DatasetError(f"Split '{split}' sin partidos con marcador.")
    total = 0.0
    for p_local, p_empate, p_visitante, indice in zip(
        probabilidades[mascara, 0],
        probabilidades[mascara, 1],
        probabilidades[mascara, 2],
        np.flatnonzero(mascara),
    ):
        fila_y = int(y[indice])
        goles_local, goles_visita = (
            (1, 0) if fila_y == 0 else ((0, 0) if fila_y == 1 else (0, 1))
        )
        total += brier_canonico(p_local, p_empate, p_visitante, goles_local, goles_visita)
    return total / int(mascara.sum()), int(mascara.sum()), probabilidades


def brier_de_vector(artefactos: Dict[str, Any], split: str, pesos: Sequence[float]) -> float:
    return evaluar_split(artefactos, split, pesos)[0]


def brier_mercado(artefactos: Dict[str, Any], split: str = "test") -> Tuple[Optional[float], int]:
    """Brier de referencia FootyStats de-vig. `[REFERENCIA-DEUDA]`."""
    mercado = artefactos[f"mercado_{split}"]
    y = artefactos[f"y_{split}"]
    valido = (~np.isnan(mercado[:, 0])) & (y >= 0)
    if not valido.any():
        return None, 0
    total = 0.0
    for p_local, p_empate, p_visitante, fila_y in zip(
        mercado[valido, 0], mercado[valido, 1], mercado[valido, 2], y[valido]
    ):
        goles_local, goles_visita = (
            (1, 0) if int(fila_y) == 0 else ((0, 0) if int(fila_y) == 1 else (0, 1))
        )
        total += brier_canonico(p_local, p_empate, p_visitante, goles_local, goles_visita)
    return total / int(valido.sum()), int(valido.sum())


# ── CLI ─────────────────────────────────────────────────────────────────────────────────────
def _reporte(meta: Dict[str, Any]) -> None:
    print("=" * 96)
    print("`[SPRINT-49 v2]` TAREA 1 — DATASET PRE-KICKOFF · REGIMEN [DIRGEN-STRICT]")
    print("=" * 96)
    print(f"Bóveda (solo lectura): {DB_HISTORICO}")
    print(f"Historial causal: {meta['antifuga']['filas_historial']} partidos · "
          f"Corpus P': {meta['n_train'] + meta['n_test'] + meta['n_fuera']}")
    print(f"  Train {TEMPORADAS_TRAIN[0]}..{TEMPORADAS_TRAIN[-1]}: {meta['n_train']}")
    print(f"  Test  {TEMPORADAS_TEST[0]}..{TEMPORADAS_TEST[-1]}: {meta['n_test']}"
          f"  (con marcador: {meta['n_test_con_marcador']}, con mercado: {meta['n_test_con_mercado']})")
    print(f"  Fuera de split (declarado): {meta['n_fuera']} -> {list(TEMPORADAS_EXCLUIDAS)}")
    print(f"Ventana: {meta['ventana']} sobre {len(meta['variables_agregadas'])} variables de evento")
    print(f"Variables ({len(meta['variables'])}): {', '.join(meta['variables'])}")
    print("-" * 96)
    print(f"ANTI-FUGA: {meta['antifuga']['filas_verificadas']} lados verificados · "
          f"violaciones de fecha={meta['antifuga']['violaciones_fecha']} · "
          f"identidad={meta['antifuga']['violaciones_identidad']}  ⇒ 0 EXCEPCIONES")
    print(f"Cold start (sin previos): {meta['antifuga']['filas_cold_start']} filas → mediana Train")
    nulas = [c for c, o in meta["origen_imputacion"].items() if o != "mediana_train"]
    print(f"Columnas 100% nulas (0.0 declarado): {', '.join(nulas) if nulas else 'ninguna'}")
    print(f"Calibración Train -> mu_liga={meta['mu_liga']:.6f}  media V07={meta['media_v07']:.6f}"
          f"  media V13={meta['media_v13']:.6f}")
    print(f"sha256 X_train={meta['sha256_x_train'][:16]}…  X_test={meta['sha256_x_test'][:16]}…")
    print("Resolución D1/D2: las 23 por cobertura mantienen V07/V13 —canal único hacia λ— dentro")
    print("del vector. El puente consume ahora los valores ACUMULADOS, no los del partido.")
    print(f"Artefactos: {DATASET_NPZ.name} + {DATASET_META.name}")
    print("=" * 96)


if __name__ == "__main__":
    analizador = argparse.ArgumentParser(
        prog="preparar_dataset_ml",
        description="[SPRINT-49/50] Dataset pre-kickoff del laboratorio (P' V1 o V2).",
    )
    analizador.add_argument(
        "--tabla-p",
        default=TABLA_P_DEFECTO,
        choices=list(TABLAS_P_PERMITIDAS),
        help="fuente de la P' de referencia (V1 = baseline, V2 = GSL-3D v2)",
    )
    analizador.add_argument("--salida", default=None, help="ruta del .npz (omite: artefacto canónico)")
    _argumentos = analizador.parse_args()
    _meta = preparar_dataset(
        Path(_argumentos.salida) if _argumentos.salida else None,
        _argumentos.tabla_p,
    )
    _reporte(_meta)
