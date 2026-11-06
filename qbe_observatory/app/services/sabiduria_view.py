# -*- coding: utf-8 -*-
"""`[DES-QBE-076]` Adaptador de Consenso de Mercado — revisión `[SPRINT-47]`.

Lee las bóvedas en modo de solo lectura y construye:
  * KPIs del universo filtrado;
  * desglose por jornada (Brier/Alpha/Peso);
  * mercado en vivo de la próxima jornada (`fixtures_snapshots`) con cuotas
    reales de los operadores seleccionados y el Consenso Ponderado.

Contrato `[SPRINT-47]` (erradicación de las inconsistencias D1-D10):

  * **Un solo universo por vista.** El KPI `brier_consenso` es la media
    ponderada por número de partidos de los Brier de los bloques servidos en la
    tabla, calculada desde la MISMA consulta. Si el KPI dice 0.2119, la tabla
    promedia 0.2119.
  * **Cero suplantación de fuente.** La rama histórica rotula su fila de mercado
    como `FootyStats` (es el corpus FootyStats) y **no** emite una fila
    `Consenso` duplicada. Cada casino seleccionado que no tenga evidencia
    propia se declara `[Casino]` con estado `SIN EVIDENCIA`; nunca se rotula un
    casino como si fuera otra fuente.
  * **Cero fallo silencioso.** La ausencia o el bloqueo de la bóveda histórica
    lanza `HistoricoDBError` (propagada a la UI); jamás se degrada en silencio a
    otra base de datos.
  * **Filtros globales.** `temporada` viaja al panel de mercado en vivo, que se
    declara vacío con motivo explícito cuando la temporada es histórica.
  * **El peso del panel vivo es real:** `1 / len(casinos_seleccionados)` por
    operador participante (normalizado entre los que portan cuota en el partido).
  * **Cero jornada inventada.** `historical_matches` no declara jornada (ver
    `DIRGEN_VARIANCE_REQUEST.md`); el bloque histórico se publica con
    `jornada=None` y etiqueta de temporada, y `_agrupar_por_jornada` emite
    bloques J1…Jn automáticamente en cuanto la fuente la declare.
  * **Cierre de jornada.** Las jornadas cerradas por el daemon con captura
    propia (`historical_odds_qbe_live`, origen `Q_BE_CAPTURA_PROPIA`) rotulan su
    fila de mercado como `Q-BE Live Capture`; el KPI declara la composición
    exacta (partidos por fuente) y sigue siendo la media ponderada de la tabla.
  * `[LN-QBE-148]` Q-BE es Challenger independiente: su fila es de solo lectura
    y jamás participa del Consenso Ponderado.
"""

from __future__ import annotations

import json
import logging
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from app.adapters.db_readonly import BaseDatosSoloLectura
from app.services.calibration_view import (
    RUTA_HISTORICO,
    HistoricoDBError,
    temporadas_historicas,
    total_partidos_historicos,
)
from src.core.consensus import ConsensoInvalidoError, promediar_simplex
from src.observatory.sabiduria_masas import (
    alpha_pct,
    brier_promedio_partidos,
    construir_tabla_sabiduria,
)

logger = logging.getLogger(__name__)

FUENTES_CASINO = ("caliente", "novibet", "betway")
FUENTES_CONOCIDAS = frozenset(FUENTES_CASINO) | {"qbe", "q-be"}

# Rotulación de la fila de mercado: la rama histórica ES FootyStats; la rama de
# reporte es el consenso de cuotas de la captura congelada.
ETIQUETA_MERCADO_HISTORICO = "FootyStats"
ETIQUETA_MERCADO_REPORTE = "Consenso"
# `[SPRINT-47]` Cierre de jornada: la fila de mercado proviene de nuestra propia
# captura (`historical_odds_qbe_live`, origen `Q_BE_CAPTURA_PROPIA`).
ETIQUETA_MERCADO_CAPTURA = "Q-BE Live Capture"
ESTADO_CIERRE_CERRADA = "CERRADA"

ESTADO_DATO = "DATO"
ESTADO_SIN_EVIDENCIA = "SIN EVIDENCIA"

MOTIVO_TEMPORADA_HISTORICA = "Temporada histórica no tiene mercado en vivo"
MOTIVO_SIN_FUENTES = "Sin fuentes seleccionadas"
MOTIVO_SIN_CARTELERA = "Sin cartelera programada en el snapshot"
#: `[LN-QBE-148]` Filtro «Todas»: el histórico masivo no porta número de jornada.
AVISO_DESGLOSE_GLOBAL = (
    "El desglose por jornada no está disponible para el histórico global. "
    "Seleccione una temporada específica."
)
ETIQUETA_TEMPORADA_GLOBAL = "Todas"

# Valores de `temporada` que NO designan un archivo histórico: la vista usa el
# snapshot vivo. Cualquier otra temporada distinta de la vigente es histórica.
TEMPORADAS_NO_ARCHIVADAS = frozenset({"actual", "no declarada"})

Resultado = Tuple[float, float, float]


# ── Símplex y Brier (aritmética de presentación, sin leyes nuevas) ─────────────
def _simplex(odd_home: Any, odd_draw: Any, odd_away: Any) -> Optional[Resultado]:
    try:
        cuotas = [float(odd_home), float(odd_draw), float(odd_away)]
    except (TypeError, ValueError):
        return None
    if any(not math.isfinite(cuota) or cuota <= 1.0 for cuota in cuotas):
        return None
    inversas = [1.0 / cuota for cuota in cuotas]
    total = sum(inversas)
    return (inversas[0] / total, inversas[1] / total, inversas[2] / total)


def _one_hot(score_home: int, score_away: int) -> Resultado:
    if score_home > score_away:
        return (1.0, 0.0, 0.0)
    if score_home == score_away:
        return (0.0, 1.0, 0.0)
    return (0.0, 0.0, 1.0)


def _brier(probabilidades: Sequence[float], resultado: Sequence[float]) -> float:
    return sum((float(p) - float(y)) ** 2 for p, y in zip(probabilidades, resultado))


def _positivo(valor: Any) -> Optional[float]:
    """Brier utilizable: finito y estrictamente positivo; `0.0` es placeholder."""
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return numero if math.isfinite(numero) and numero > 0.0 else None


def _es_casino(fuente: Any) -> bool:
    """`[LN-QBE-148]` Solo casinos participan del Consenso; Q-BE queda fuera."""
    return str(fuente or "").strip().lower() in FUENTES_CASINO


def _entero_jornada(jornada: Any) -> Optional[int]:
    """Jornada filtrable: entero no negativo; cualquier otro valor no filtra."""
    if jornada is None or isinstance(jornada, bool):
        return None
    texto = str(jornada).strip()
    if not texto:
        return None
    try:
        numero = int(texto)
    except (TypeError, ValueError):
        return None
    return numero if numero >= 0 else None


def _normalizar_seleccion(fuentes: Optional[Sequence[str]]) -> List[str]:
    if fuentes is None:
        return [*FUENTES_CASINO, "qbe"]
    seleccion: List[str] = []
    for fuente in fuentes:
        nombre = str(fuente or "").strip().lower()
        if nombre == "q-be":
            nombre = "qbe"
        if nombre in FUENTES_CONOCIDAS and nombre not in seleccion:
            seleccion.append(nombre)
    return seleccion


def _nombre_fuente(casino: str) -> str:
    return str(casino).replace("_", " ").strip().title()


def _normalizar_pesos(pesos: Mapping[str, float]) -> Dict[str, float]:
    """Normaliza pesos positivos a suma 1; sin masa positiva devuelve ceros."""
    total = sum(float(valor) for valor in pesos.values() if float(valor) > 0.0)
    if not math.isfinite(total) or total <= 0.0:
        return {clave: 0.0 for clave in pesos}
    return {clave: float(valor) / total for clave, valor in pesos.items()}


# ── Consenso `[LN-QBE-148]` ───────────────────────────────────────────────────
def _consenso_casinos(
    probabilidades: Mapping[str, Resultado],
    pesos: Mapping[str, float],
) -> Optional[Resultado]:
    """`[LN-QBE-148]` Consenso Ponderado estrictamente entre casinos.

    Q-BE —y cualquier fuente que no sea casino— se descarta **antes** de la
    suma: ni su probabilidad ni su peso entran en ``Δ²``. Sin casinos no hay
    consenso (``None``), jamás un consenso degenerado de una sola fuente.
    """
    participantes = {
        casino: fila for casino, fila in probabilidades.items() if _es_casino(casino)
    }
    if not participantes:
        return None
    pesos_uso = {
        casino: float(pesos.get(casino, 1.0)) for casino in participantes
    }
    try:
        return promediar_simplex(participantes, pesos_uso)
    except ConsensoInvalidoError:
        return None


# ── Tabla por jornada ─────────────────────────────────────────────────────────
def _promedio_ponderado(pares: Sequence[Tuple[Optional[float], int]]) -> Optional[float]:
    """Media ponderada por número de partidos; `None` si no hay masa de evidencia.

    Se publica con la precisión canónica del Brier del ecosistema (4 decimales,
    `calcular_brier_multicategorico`), de modo que el Alpha que imprime la UI
    satisface exactamente la fórmula que declara el pie de página.
    """
    acumulado = 0.0
    total = 0
    for valor, cantidad in pares:
        if valor is None or cantidad <= 0:
            continue
        acumulado += float(valor) * int(cantidad)
        total += int(cantidad)
    if total <= 0:
        return None
    return round(acumulado / total, 4)


def _media_brier(valores: Sequence[Any]) -> Optional[float]:
    """Media de Brier sobre valores positivos; `None` sin evidencia (cero imputado)."""
    validos = [valor for valor in (_positivo(item) for item in valores) if valor is not None]
    return brier_promedio_partidos(validos)


def _agrupar_por_jornada(
    partidos: Sequence[Mapping[str, Any]], incluir_qbe: bool = False
) -> List[Dict[str, Any]]:
    """Agrupa los partidos por la jornada REAL que declare la fuente.

    `jornada=None` designa un bloque sin desglose (la fuente no la declara). En
    cuanto `_partidos_historicos` propague una jornada entera, esta función
    emite J1…Jn sin cambios adicionales.

    `[LN-QBE-148]` Cada bloque publica DOS Brier sobre la MISMA muestra: el de
    mercado y el de Q-BE. La muestra de Q-BE son los partidos donde coexisten
    momios y distribución P'; un partido sin P' no entra en el promedio de Q-BE.
    """
    grupos: Dict[Optional[int], List[Mapping[str, Any]]] = {}
    for partido in partidos:
        jornada = partido.get("jornada")
        numero = _entero_jornada(jornada) if jornada is not None else None
        grupos.setdefault(numero, []).append(partido)
    bloques: List[Dict[str, Any]] = []
    for jornada, items in grupos.items():
        comparables = [
            partido
            for partido in items
            if partido.get("brier") is not None and partido.get("brier_qbe") is not None
        ]
        if incluir_qbe and comparables:
            muestra = comparables
            brier_qbe = _media_brier([p.get("brier_qbe") for p in muestra])
            n_qbe = len(muestra)
        else:
            muestra = [partido for partido in items if partido.get("brier") is not None]
            brier_qbe = None
            n_qbe = 0
        bloques.append(
            {
                "jornada": jornada,
                "brier": _media_brier([p.get("brier") for p in muestra]),
                "n_partidos": len(muestra),
                "brier_qbe": brier_qbe,
                "n_qbe": n_qbe,
            }
        )
    bloques.sort(key=lambda bloque: (bloque["jornada"] is None, bloque["jornada"] or 0))
    return bloques


def _etiqueta_bloque(temporada: str, jornada: Optional[int]) -> Optional[str]:
    """Etiqueta del bloque: `None` delega en la plantilla (`J{n}`)."""
    if jornada is not None:
        return None
    return f"Temporada {temporada} · sin jornada declarada en la fuente"


def _filas_bloque(
    *,
    etiqueta_mercado: str,
    brier_mercado: Any,
    n_mercado: int,
    brier_qbe: Any,
    incluir_qbe: bool,
    casinos_sin_evidencia: Sequence[str] = (),
) -> List[Dict[str, Any]]:
    """Filas de un bloque: UNA fila de mercado (sin duplicar) + casinos + Q-BE.

    `casinos_sin_evidencia` declara, con el nombre propio del operador, la
    ausencia de evidencia por casino. Es la corrección de D5/D6: el casino jamás
    se rotula con la etiqueta de otra fuente.
    """
    filas: List[Dict[str, Any]] = [
        {
            "fuente": etiqueta_mercado,
            "brier": brier_mercado,
            "alpha_pct": alpha_pct(brier_mercado, brier_qbe),
            "peso": 1.0 if brier_mercado is not None else None,
            "estado": ESTADO_DATO if brier_mercado is not None else ESTADO_SIN_EVIDENCIA,
            "n_partidos": int(n_mercado),
        }
    ]
    for casino in casinos_sin_evidencia:
        filas.append(
            {
                "fuente": _nombre_fuente(casino),
                "brier": None,
                "alpha_pct": None,
                "peso": None,
                "estado": ESTADO_SIN_EVIDENCIA,
                "n_partidos": 0,
                "motivo": "El corpus histórico FootyStats no discrimina por operador",
            }
        )
    if incluir_qbe:
        filas.append(
            {
                "fuente": "Q-BE",
                "brier": brier_qbe,
                "alpha_pct": 0.0 if brier_qbe is not None else None,
                "peso": None,
                "estado": ESTADO_DATO if brier_qbe is not None else ESTADO_SIN_EVIDENCIA,
                "n_partidos": None,
            }
        )
    exigir_consenso = any(
        str(fila["fuente"]).strip().lower() == "consenso" for fila in filas
    )
    return construir_tabla_sabiduria(
        filas, exigir_consenso=exigir_consenso, fuente_maestra=etiqueta_mercado
    )


def _bloque(
    jornada: Optional[int],
    etiqueta: Optional[str],
    filas: Sequence[Mapping[str, Any]],
    *,
    brier_mercado: Any,
    n_mercado: int,
    brier_qbe: Any,
    n_qbe: int,
    fuente_mercado: str = "",
) -> Dict[str, Any]:
    return {
        "jornada": jornada,
        "etiqueta": etiqueta,
        "total_partidos": int(n_mercado),
        "n_partidos": int(n_mercado),
        "brier_mercado": brier_mercado,
        "n_mercado": int(n_mercado),
        "brier_qbe": brier_qbe,
        "n_qbe": int(n_qbe),
        "fuente_mercado": fuente_mercado,
        "fuentes": list(filas),
    }


def _kpis(bloques: Sequence[Mapping[str, Any]]) -> Tuple[Optional[float], Optional[float]]:
    """KPI = media ponderada por partidos de los bloques SERVIDOS en la tabla."""
    mercado = _promedio_ponderado(
        [(bloque.get("brier_mercado"), int(bloque.get("n_mercado") or 0)) for bloque in bloques]
    )
    qbe = _promedio_ponderado(
        [(bloque.get("brier_qbe"), int(bloque.get("n_qbe") or 0)) for bloque in bloques]
    )
    return mercado, qbe


def _fuentes_de(bloques: Sequence[Mapping[str, Any]]) -> Dict[str, int]:
    """Composición del KPI: partidos aportados por cada fuente de mercado servida."""
    fuentes: Dict[str, int] = {}
    for bloque in bloques:
        partidos = int(bloque.get("n_mercado") or 0)
        if partidos <= 0:
            continue
        nombre = str(bloque.get("fuente_mercado") or ETIQUETA_MERCADO_REPORTE)
        fuentes[nombre] = fuentes.get(nombre, 0) + partidos
    return fuentes


def _resumen(
    brier_consenso: Any,
    brier_qbe: Any,
    *,
    etiqueta_mercado: str,
    n_partidos: int,
    n_jornadas: int,
    composicion_mercado: str = "",
    fuentes_mercado: Optional[Mapping[str, int]] = None,
    seleccion_vacia: bool = False,
) -> Dict[str, Any]:
    alpha = (
        alpha_pct(brier_consenso, brier_qbe)
        if brier_consenso is not None and brier_qbe is not None
        else None
    )
    composicion = dict(fuentes_mercado or {})
    activas = [nombre for nombre, cantidad in composicion.items() if int(cantidad) > 0]
    casinos = [nombre for nombre in activas if nombre.lower() in FUENTES_CASINO]
    # La unidad del KPI es «Casinos» sólo si todas las fuentes activas son operadores;
    # una fuente histórica (FootyStats) se declara como «Fuentes», no se disfraza de casa.
    unidad = "Casinos" if activas and len(casinos) == len(activas) else "Fuentes"
    return {
        "brier_consenso": brier_consenso,
        "brier_qbe": brier_qbe,
        "alpha_pct": alpha,
        "etiqueta_mercado": etiqueta_mercado,
        "composicion_mercado": composicion_mercado,
        "fuentes_mercado": composicion,
        "n_partidos": int(n_partidos),
        "n_jornadas": int(n_jornadas),
        "n_fuentes": len(activas),
        "lista_fuentes": ", ".join(activas),
        "unidad_fuentes": unidad,
        "es_hibrida": len(activas) > 1,
        "actualizado": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "casinos_validos": 0,
        "casinos_totales": 0,
        "consenso_degenerado": False,
        "seleccion_vacia": seleccion_vacia,
    }


def _composicion(fuentes_mercado: Mapping[str, int]) -> str:
    """Texto de procedencia del KPI: cuántos partidos aporta cada fuente."""
    partes = [
        f"{nombre}: {int(partidos)} partidos"
        for nombre, partidos in sorted(fuentes_mercado.items())
        if int(partidos) > 0
    ]
    return " · ".join(partes)


def _etiqueta_kpi(fuentes_mercado: Mapping[str, int]) -> str:
    """Una sola fuente ⇒ su nombre; varias ⇒ `Mercado` (composición declarada)."""
    activas = [nombre for nombre, partidos in fuentes_mercado.items() if int(partidos) > 0]
    return activas[0] if len(activas) == 1 else "Mercado"


def _tabla_vacia(seleccion_vacia: bool = True) -> Dict[str, Any]:
    return {
        "resumen": _resumen(
            None,
            None,
            etiqueta_mercado=ETIQUETA_MERCADO_REPORTE,
            n_partidos=0,
            n_jornadas=0,
            seleccion_vacia=seleccion_vacia,
        ),
        "fuentes": [],
        "jornadas": [],
        "jornadas_disponibles": [],
        "temporadas": [],
        "temporada_actual": "",
        "total_partidos": 0,
        "total_universo": 0,
        "total_historico": 0,
        "casinos": 0,
        "seleccion": [],
        "seleccion_vacia": seleccion_vacia,
        "es_historica": False,
        "fuente_etiqueta": "Sin datos",
        "nota": "",
        "motivo_filtro": None,
    }


# ── Bóveda histórica: UNA sola consulta para KPI y tabla ──────────────────────
def _partidos_historicos(temporada: str = "") -> List[Dict[str, Any]]:
    """Partidos de mercado de la temporada histórica, con su distribución P' si existe.

    Única consulta SQL que alimenta KPIs y tabla (`[SPRINT-47]` Tarea 3): el KPI
    y los bloques no pueden divergir porque nacen de las mismas filas.

    `[LN-QBE-150]` Cruce histórico Q-BE × mercado: se adjunta el símplex P' por
    `match_id` (`LEFT JOIN historical_sovereign_distributions`). Un partido sin
    distribución P' queda con `brier_qbe = None` y **no** entra en la muestra de
    comparación, pero conserva su Brier de mercado. Una bóveda previa a la tabla
    P' se sirve igual: la consulta degrada a la rama sin JOIN.

    `temporada` vacía ⇒ universo histórico completo (filtro «Todas»).

    `jornada` queda en `None` porque `historical_matches` no la declara (ni la
    columna, ni el parser de ingesta); ver `DIRGEN_VARIANCE_REQUEST.md`.
    """
    filtro = "WHERE m.temporada = ?" if temporada else ""
    parametros = (temporada,) if temporada else ()
    sql_base = (
        "SELECT m.home_goals, m.away_goals, m.odd_home, m.odd_draw, m.odd_away, "
        "m.fecha_utc"
    )
    try:
        base = BaseDatosSoloLectura(RUTA_HISTORICO)
        try:
            filas = base.ejecutar_select(
                f"{sql_base}, d.p_local AS p_local, d.p_empate AS p_empate, "
                "d.p_visitante AS p_visitante "
                "FROM historical_matches m "
                "LEFT JOIN historical_sovereign_distributions d ON d.match_id = m.match_id "
                f"{filtro} ORDER BY m.fecha_utc ASC",
                parametros,
            )
        except sqlite3.OperationalError:
            # Bóveda previa a `[LN-QBE-150]`: sin tabla P' se sirve el mercado solo.
            filas = base.ejecutar_select(
                f"{sql_base}, NULL AS p_local, NULL AS p_empate, NULL AS p_visitante "
                f"FROM historical_matches m {filtro} ORDER BY m.fecha_utc ASC",
                parametros,
            )
    except (FileNotFoundError, sqlite3.Error) as error:
        raise HistoricoDBError(
            f"No se pudo leer `historical_matches` ({RUTA_HISTORICO}): {error}"
        ) from error

    partidos: List[Dict[str, Any]] = []
    for fila in filas:
        probabilidades = _simplex(fila["odd_home"], fila["odd_draw"], fila["odd_away"])
        brier: Optional[float] = None
        brier_qbe: Optional[float] = None
        if probabilidades is not None:
            try:
                goles_local = int(fila["home_goals"])
                goles_visitante = int(fila["away_goals"])
            except (TypeError, ValueError):
                brier = None
            else:
                # Normalización 3N idéntica a `calcular_brier_multicategorico`
                # ([LN-QBE-100]): BS = Σ_k (p_k − y_k)² / 3 por partido.
                resultado = _one_hot(goles_local, goles_visitante)
                brier = _brier(probabilidades, resultado) / 3.0
                p_qbe = (fila["p_local"], fila["p_empate"], fila["p_visitante"])
                if all(valor is not None for valor in p_qbe):
                    brier_qbe = _brier(p_qbe, resultado) / 3.0
        partidos.append({"jornada": None, "brier": brier, "brier_qbe": brier_qbe})
    return partidos


def _es_temporada_archivada(temporada: str) -> bool:
    """Verdadero si la temporada pedida NO es la vigente (o no es una etiqueta viva).

    `[SPRINT-47]` D3: una temporada desconocida o no vigente jamás hereda el
    snapshot vivo; se declara histórica y, sin evidencia, queda vacía.
    """
    nombre = str(temporada or "").strip()
    if not nombre or nombre.lower() in TEMPORADAS_NO_ARCHIVADAS:
        return False
    temporadas = temporadas_historicas()
    vigente = temporadas[-1] if temporadas else ""
    return nombre != vigente


def _cierres_propios(temporada: str) -> Dict[int, Dict[str, Any]]:
    """Cierres de jornada con captura propia (`[SPRINT-47]` Tarea 6).

    Lee ``jornada_closure_log`` de la bóveda histórica: jornadas cerradas por
    `src.storage.jornada_closure` con `origen = Q_BE_CAPTURA_PROPIA`. Sólo las
    que declaran `CERRADA` y portan Brier entran al mapa; `SIN EVIDENCIA_PROPIA`
    se excluye aquí y la UI conserva la fuente nativa de la jornada.

    La ausencia de la tabla (vista previa al primer cierre) se declara como «sin
    cierres», nunca como fallo; un error real de la bóveda sigue siendo
    `HistoricoDBError` (D2).
    """
    base = BaseDatosSoloLectura(RUTA_HISTORICO)
    try:
        existe = base.ejecutar_select(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='jornada_closure_log'"
        )
        if not existe:
            return {}
        filas = base.ejecutar_select(
            "SELECT jornada, estado, ticks, partidos, brier_propio "
            "FROM jornada_closure_log WHERE temporada = ? ORDER BY jornada ASC",
            (temporada,),
        )
    except (FileNotFoundError, sqlite3.Error) as error:
        raise HistoricoDBError(
            f"No se pudo leer el cierre de jornada ({RUTA_HISTORICO}): {error}"
        ) from error

    cierres: Dict[int, Dict[str, Any]] = {}
    for fila in filas:
        if str(fila["estado"]) != ESTADO_CIERRE_CERRADA:
            continue
        brier = _positivo(fila["brier_propio"])
        if brier is None:
            continue
        cierres[int(fila["jornada"])] = {
            "estado": str(fila["estado"]),
            "ticks": int(fila["ticks"] or 0),
            "partidos": int(fila["partidos"] or 0),
            "brier": brier,
        }
    return cierres


# ── Construcción de la vista histórica / de reporte ───────────────────────────
def construir_sabiduria_masas(
    reporte: Mapping[str, Any],
    ruta: Path,
    temporada: str = "",
    fuentes: Optional[Sequence[str]] = None,
    jornada: Any = None,
) -> Dict[str, Any]:
    """Construye KPIs y desglose por jornada desde UNA sola fuente de verdad.

    ``jornada`` filtra los bloques y recomputa los KPIs sobre los bloques
    visibles (nunca se hereda el KPI global).

    Propagación de fallos (`[SPRINT-47]` D2): si la bóveda histórica no responde,
    `temporadas_historicas()` / `total_partidos_historicos()` /
    `_partidos_historicos()` lanzan `HistoricoDBError`; esta función **no la
    captura**. La UI declara el fallo en vez de servir otra base de datos.
    """
    seleccion = _normalizar_seleccion(fuentes)
    if not seleccion:
        return _tabla_vacia(seleccion_vacia=True)

    incluir_qbe = "qbe" in seleccion
    casinos_sel = [casino for casino in FUENTES_CASINO if casino in seleccion]
    jornada_sel = _entero_jornada(jornada)

    temporadas = temporadas_historicas()
    temporada_actual = temporadas[-1] if temporadas else ""
    total_historico = total_partidos_historicos()
    nombre_temporada = str(temporada or "").strip()
    es_historica = (
        bool(nombre_temporada)
        and nombre_temporada.lower() not in TEMPORADAS_NO_ARCHIVADAS
        and nombre_temporada != temporada_actual
    )

    es_global = nombre_temporada.strip().lower() in {"todas", "todo", "all", "*"}
    if es_historica or es_global:
        partidos = _partidos_historicos("" if es_global else nombre_temporada)
        agrupados = _agrupar_por_jornada(partidos, incluir_qbe=incluir_qbe)
        bloques: List[Dict[str, Any]] = []
        for grupo in agrupados:
            etiqueta_grupo = _etiqueta_bloque(nombre_temporada, grupo["jornada"])
            if es_global and grupo["jornada"] is None:
                etiqueta_grupo = "Universo histórico completo (todas las temporadas)"
            filas = _filas_bloque(
                etiqueta_mercado=ETIQUETA_MERCADO_HISTORICO,
                brier_mercado=grupo["brier"],
                n_mercado=grupo["n_partidos"],
                brier_qbe=grupo["brier_qbe"],
                incluir_qbe=incluir_qbe,
                casinos_sin_evidencia=casinos_sel,
            )
            bloques.append(
                _bloque(
                    grupo["jornada"],
                    etiqueta_grupo,
                    filas,
                    brier_mercado=grupo["brier"],
                    n_mercado=grupo["n_partidos"],
                    brier_qbe=grupo["brier_qbe"],
                    n_qbe=grupo["n_qbe"],
                    fuente_mercado=ETIQUETA_MERCADO_HISTORICO,
                )
            )

        jornadas_disponibles = sorted(
            int(bloque["jornada"]) for bloque in bloques if bloque["jornada"] is not None
        )
        motivo_filtro: Optional[str] = None
        if jornada_sel is not None:
            visibles = [bloque for bloque in bloques if bloque["jornada"] == jornada_sel]
            if not visibles and not jornadas_disponibles:
                motivo_filtro = (
                    f"La temporada {nombre_temporada} no declara jornada en la fuente "
                    f"FootyStats; el filtro J{jornada_sel} no puede aplicarse."
                )
            elif not visibles:
                motivo_filtro = f"La jornada J{jornada_sel} no tiene evidencia en la temporada {nombre_temporada}."
            bloques = visibles

        brier_consenso, brier_qbe = _kpis(bloques)
        n_comparables = sum(int(bloque.get("n_qbe") or 0) for bloque in bloques)
        n_usados = sum(int(bloque["n_mercado"]) for bloque in bloques)
        fuentes_mercado = _fuentes_de(bloques) or {ETIQUETA_MERCADO_HISTORICO: 0}
        # Tabla «global» coherente con el KPI: misma etiqueta, mismo universo.
        filas_globales = _filas_bloque(
            etiqueta_mercado=ETIQUETA_MERCADO_HISTORICO,
            brier_mercado=brier_consenso,
            n_mercado=n_usados,
            brier_qbe=brier_qbe,
            incluir_qbe=incluir_qbe,
            casinos_sin_evidencia=casinos_sel,
        )
        etiqueta_temporada = "todas las temporadas" if es_global else nombre_temporada
        return {
            "resumen": _resumen(
                brier_consenso,
                brier_qbe if incluir_qbe else None,
                etiqueta_mercado=_etiqueta_kpi(fuentes_mercado),
                n_partidos=n_usados,
                n_jornadas=len(bloques),
                composicion_mercado=_composicion(fuentes_mercado),
                fuentes_mercado=fuentes_mercado,
                seleccion_vacia=False,
            ),
            "fuentes": filas_globales,
            "jornadas": bloques,
            "jornadas_disponibles": jornadas_disponibles,
            "temporadas": temporadas,
            "temporada_actual": nombre_temporada,
            "total_partidos": n_usados,
            "total_universo": len(partidos),
            "total_historico": total_historico,
            "casinos": len(casinos_sel),
            "seleccion": seleccion,
            "seleccion_vacia": False,
            "es_historica": True,
            "es_global": es_global,
            "desglose_no_disponible": bool(es_global and jornada_sel is None),
            "aviso_desglose": AVISO_DESGLOSE_GLOBAL if es_global else None,
            "n_comparables": n_comparables,
            "fuente_etiqueta": f"Histórico FootyStats ({etiqueta_temporada})",
            "nota": (
                "Brier de mercado FootyStats normalizado 3N; Brier Q-BE calculado sobre "
                "`historical_sovereign_distributions` ([LN-QBE-150]). Muestra de Alpha: "
                "partidos con momios y distribución P' simultáneamente."
            ),
            "motivo_filtro": motivo_filtro,
        }

    # ── Rama de reporte: temporada vigente sobre el snapshot vivo ─────────────
    resumen_reporte = reporte.get("resumen_temporada") or {}
    total_universo = int(resumen_reporte.get("total_partidos") or 0)
    # `[SPRINT-47]` Cierre de jornada: si la jornada fue cerrada con nuestra
    # propia captura, su fila de mercado es `Q-BE Live Capture` (evidencia
    # propia) y sustituye al consenso de la captura congelada.
    cierres = _cierres_propios(temporada_actual)
    fuentes_mercado: Dict[str, int] = {}
    bloques = []
    jornadas_disponibles = []
    for fila_jornada in reporte.get("jornadas") or []:
        numero = _entero_jornada(fila_jornada.get("jornada"))
        if numero is None:
            continue
        jornadas_disponibles.append(numero)
        partidos_jornada = [
            partido for partido in (fila_jornada.get("partidos") or []) if isinstance(partido, dict)
        ]
        total_jornada = int(fila_jornada.get("total_partidos") or len(partidos_jornada))

        brier_qbe = _positivo(fila_jornada.get("brier_score_qbe")) if incluir_qbe else None
        n_qbe = 0
        if incluir_qbe and brier_qbe is not None:
            n_qbe = (
                sum(1 for partido in partidos_jornada if partido.get("brier_qbe") is not None)
                if partidos_jornada
                else total_jornada
            )

        cierre = cierres.get(numero)
        if cierre is not None and cierre["brier"] is not None:
            etiqueta_mercado = ETIQUETA_MERCADO_CAPTURA
            brier_mercado = cierre["brier"]
            n_mercado = int(cierre["partidos"])
        else:
            etiqueta_mercado = ETIQUETA_MERCADO_REPORTE
            brier_mercado = _positivo(fila_jornada.get("brier_score_mercado"))
            if partidos_jornada:
                n_mercado = sum(
                    1 for partido in partidos_jornada if partido.get("brier_mercado") is not None
                )
            else:
                n_mercado = total_jornada
            if brier_mercado is None:
                n_mercado = 0

        filas = _filas_bloque(
            etiqueta_mercado=etiqueta_mercado,
            brier_mercado=brier_mercado,
            n_mercado=n_mercado,
            brier_qbe=brier_qbe,
            incluir_qbe=incluir_qbe,
        )
        bloques.append(
            _bloque(
                numero,
                None,
                filas,
                brier_mercado=brier_mercado,
                n_mercado=n_mercado,
                brier_qbe=brier_qbe,
                n_qbe=n_qbe,
                fuente_mercado=etiqueta_mercado,
            )
        )

    jornadas_disponibles.sort()
    motivo_filtro = None
    if jornada_sel is not None:
        visibles = [bloque for bloque in bloques if int(bloque["jornada"]) == jornada_sel]
        if not visibles:
            motivo_filtro = f"La jornada J{jornada_sel} no tiene evidencia en el reporte."
        bloques = visibles

    brier_consenso, brier_qbe = _kpis(bloques)
    n_usados = sum(int(bloque["n_mercado"]) for bloque in bloques)
    fuentes_mercado = _fuentes_de(bloques) or {ETIQUETA_MERCADO_REPORTE: 0}
    etiqueta_kpi = _etiqueta_kpi(fuentes_mercado)
    # Tabla «global» coherente con el KPI: misma etiqueta, mismo universo.
    filas_globales = _filas_bloque(
        etiqueta_mercado=etiqueta_kpi,
        brier_mercado=brier_consenso,
        n_mercado=n_usados,
        brier_qbe=brier_qbe if incluir_qbe else None,
        incluir_qbe=incluir_qbe,
    )
    return {
        "resumen": _resumen(
            brier_consenso,
            brier_qbe,
            etiqueta_mercado=etiqueta_kpi,
            n_partidos=n_usados,
            n_jornadas=len(bloques),
            composicion_mercado=_composicion(fuentes_mercado),
            fuentes_mercado=fuentes_mercado,
            seleccion_vacia=False,
        ),
        "fuentes": filas_globales,
        "jornadas": bloques,
        "jornadas_disponibles": jornadas_disponibles,
        "temporadas": temporadas,
        "temporada_actual": temporada_actual,
        "total_partidos": n_usados,
        "total_universo": total_universo,
        "total_historico": total_historico,
        "casinos": len(casinos_sel),
        "seleccion": seleccion,
        "seleccion_vacia": False,
        "es_historica": False,
        "fuente_etiqueta": f"Snapshot Vivo ({temporada_actual or 'temporada no declarada'})",
        "nota": (
            "Brier de Mercado desde el reporte de Auditoría (universo de partidos "
            "finalizados), normalizado 3N; Q-BE del mismo reporte. Alpha: diferencia "
            "porcentual del Brier de Q-BE frente al mercado. Consenso Ponderado [LN-QBE-148]."
        ),
        "motivo_filtro": motivo_filtro,
    }


# ── Mercado en vivo ───────────────────────────────────────────────────────────
def _mercado_vacio(motivo: str, *, historica: bool = False) -> Dict[str, Any]:
    return {
        "jornada": None,
        "jornada_viva": None,
        "actualizado": None,
        "partidos": [],
        "vacio": True,
        "motivo": motivo,
        "motivo_historico": historica,
        "fuente_etiqueta": "Sin datos de mercado",
    }


def _ultima_jornada_programada(
    base: BaseDatosSoloLectura,
) -> Tuple[Optional[int], Optional[str], List[Dict[str, Any]]]:
    try:
        filas = base.ejecutar_select(
            "SELECT matchday, updated_at, matches_json FROM fixtures_snapshots "
            "ORDER BY updated_at DESC, matchday DESC"
        )
    except (sqlite3.Error, FileNotFoundError) as error:
        logger.warning("fixtures_snapshots no disponible: %s", error)
        return None, None, []

    for fila in filas:
        try:
            partidos = json.loads(fila["matches_json"]) if fila["matches_json"] else []
        except (TypeError, ValueError):
            continue
        if not isinstance(partidos, list):
            continue
        if any(str(p.get("estado") or "").upper() == "PROGRAMADO" for p in partidos):
            return int(fila["matchday"]), str(fila["updated_at"] or ""), partidos
    return None, None, []


def _probabilidades_qbe(
    partido: Mapping[str, Any],
    soberana: Optional[Sequence[Any]] = None,
) -> Optional[Resultado]:
    valores: Sequence[Any]
    if soberana is not None:
        valores = soberana
    else:
        valores = [
            partido.get("p_local"),
            partido.get("p_empate"),
            partido.get("p_visitante"),
        ]
    try:
        triple = tuple(float(valor) for valor in valores)
    except (TypeError, ValueError):
        return None
    if any(not math.isfinite(valor) or valor < 0.0 for valor in triple):
        return None
    if abs(sum(triple) - 1.0) > 1e-6:
        return None
    return triple  # type: ignore[return-value]


def _soberanas(base: BaseDatosSoloLectura) -> Dict[str, Resultado]:
    """Distribución persistida por `qbe_core` (JOIN por `match_id`)."""
    try:
        filas = base.ejecutar_select(
            "SELECT match_id, p_local, p_empate, p_visitante FROM sovereign_distributions"
        )
    except (sqlite3.Error, FileNotFoundError) as error:
        logger.warning("sovereign_distributions no disponible: %s", error)
        return {}
    resultado: Dict[str, Resultado] = {}
    for fila in filas:
        try:
            triple = (
                float(fila["p_local"]),
                float(fila["p_empate"]),
                float(fila["p_visitante"]),
            )
        except (TypeError, ValueError):
            continue
        if any(not math.isfinite(valor) or valor < 0.0 for valor in triple):
            continue
        if abs(sum(triple) - 1.0) > 1e-6:
            continue
        resultado[str(fila["match_id"])] = triple
    return resultado


def _momio_justo(probabilidad: Any) -> Optional[float]:
    """Inverso de una probabilidad válida; ``None`` si no es representable."""
    try:
        p = float(probabilidad)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(p) or p <= 0.0 or p > 1.0:
        return None
    momio = 1.0 / p
    if not math.isfinite(momio):
        return None
    return round(momio, 2)


def _cuotas_justas(probabilidades: Sequence[Any]) -> Dict[str, Optional[float]]:
    return {
        "L": _momio_justo(probabilidades[0]),
        "E": _momio_justo(probabilidades[1]),
        "V": _momio_justo(probabilidades[2]),
    }


def construir_mercado_vivo(
    ruta: Path,
    fuentes: Optional[Sequence[str]] = None,
    jornada: Any = None,
    temporada: str = "",
) -> Dict[str, Any]:
    """Cuotas reales de la próxima jornada para las fuentes seleccionadas.

    `[SPRINT-47]` Filtros globales:
      * ``temporada`` histórica (distinta de la vigente) ⇒ panel vacío con
        motivo explícito `MOTIVO_TEMPORADA_HISTORICA`; jamás se sirve la
        cartelera viva bajo una temporada archivada.
      * ``jornada`` distinta de la viva ⇒ panel vacío con motivo explícito.

    Los pesos del Consenso son REALES: cada casino seleccionado pesa
    ``1 / len(casinos_seleccionados)`` y ese mismo valor se publica en la
    columna «Peso». La normalización entre los operadores que sí portan cuota
    en el partido la aplica `promediar_simplex` ([LN-QBE-148]).
    """
    seleccion = _normalizar_seleccion(fuentes)
    incluir_qbe = "qbe" in seleccion
    casinos_sel = [casino for casino in FUENTES_CASINO if casino in seleccion]
    if not seleccion:
        return _mercado_vacio(MOTIVO_SIN_FUENTES)
    if not casinos_sel and not incluir_qbe:
        return _mercado_vacio(MOTIVO_SIN_FUENTES)
    if _es_temporada_archivada(temporada):
        return _mercado_vacio(MOTIVO_TEMPORADA_HISTORICA, historica=True)

    jornada_pedida = _entero_jornada(jornada)
    base = BaseDatosSoloLectura(ruta)
    jornada_viva, actualizado, partidos_crudos = _ultima_jornada_programada(base)
    if jornada_viva is None:
        return _mercado_vacio(MOTIVO_SIN_CARTELERA)
    if jornada_pedida is not None and jornada_pedida != jornada_viva:
        return _mercado_vacio(
            f"La cartelera viva es J{jornada_viva}; la J{jornada_pedida} no tiene "
            "cuotas capturadas."
        )
    soberanas = _soberanas(base)

    peso_nominal = 1.0 / len(casinos_sel) if casinos_sel else 0.0
    partidos: List[Dict[str, Any]] = []
    for partido in partidos_crudos:
        if not isinstance(partido, dict):
            continue
        if str(partido.get("estado") or "").upper() != "PROGRAMADO":
            continue
        operadores = partido.get("momios_operadores") or {}
        probabilidades: Dict[str, Resultado] = {}
        cuotas: Dict[str, Any] = {}
        for casino in casinos_sel:
            payload = operadores.get(casino)
            if not isinstance(payload, dict):
                continue
            simplex = _simplex(payload.get("L"), payload.get("E"), payload.get("V"))
            if simplex is None:
                continue
            probabilidades[casino] = simplex
            cuotas[casino] = {
                "L": payload.get("L"),
                "E": payload.get("E"),
                "V": payload.get("V"),
            }

        qbe = (
            _probabilidades_qbe(
                partido,
                soberanas.get(str(partido.get("id_partido") or "")),
            )
            if incluir_qbe
            else None
        )

        # Peso uniforme declarado y normalizado entre los operadores presentes.
        pesos_live = _normalizar_pesos(
            {casino: peso_nominal for casino in probabilidades}
        )
        consenso = _consenso_casinos(probabilidades, pesos_live) if probabilidades else None

        fuentes_partido: List[Dict[str, Any]] = []
        if consenso is not None:
            fuentes_partido.append(
                {
                    "fuente": "Consenso",
                    "cuota": _cuotas_justas(consenso),
                    "p": consenso,
                    "peso": 1.0,
                    "es_consenso": True,
                }
            )
        if qbe is not None:
            fuentes_partido.append(
                {
                    "fuente": "Q-BE",
                    "cuota": _cuotas_justas(qbe),
                    "p": qbe,
                    "peso": None,
                    "es_consenso": False,
                }
            )
        for casino, probabilidad in probabilidades.items():
            fuentes_partido.append(
                {
                    "fuente": _nombre_fuente(casino),
                    "cuota": cuotas[casino],
                    "p": probabilidad,
                    "peso": pesos_live.get(casino, peso_nominal),
                    "es_consenso": False,
                }
            )

        if fuentes_partido:
            partidos.append(
                {
                    "local": partido.get("local"),
                    "visitante": partido.get("visitante"),
                    "fecha_dt": partido.get("fecha_dt"),
                    "fuentes": fuentes_partido,
                }
            )

    motivo = None if partidos else "Sin cuotas para la selección actual."
    return {
        "jornada": jornada_viva,
        "jornada_viva": jornada_viva,
        "actualizado": actualizado,
        "partidos": partidos,
        "vacio": not partidos,
        "motivo": motivo,
        "motivo_historico": False,
        "fuente_etiqueta": f"Snapshot Vivo (J{jornada_viva})",
        "peso_nominal": round(peso_nominal, 6),
    }
