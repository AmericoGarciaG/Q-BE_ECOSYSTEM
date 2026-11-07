# -*- coding: utf-8 -*-
"""[ARCH-1.4.78] Fachada de lectura de la Vista Unificada de Desempeño.

Ruta `/desempeno` (`[DES-QBE-078]`). Régimen `[DBBD-FUNGIBLE]` en la capa de
presentación: esta fachada NO reimplementa ninguna ley del núcleo. Su único
trabajo es:

* **enrutador dual de bóvedas (`[ARCH-1.4.78 · FIX]`)**: la temporada en curso se
  sirve del snapshot vivo (`cargar_vista_calibracion` → `reporte_calibracion_canonico`)
  y las temporadas históricas o `Todas` de la bóveda OLAP
  (`qbe_observatory/data/qbe_historico.db`) en solo lectura (`mode=ro` +
  `PRAGMA query_only=ON`), cruzando `historical_matches` con
  `historical_sovereign_distributions`;
* proyectar su DTO a `DesempenoKPIsOut` / `DesempenoJornadaOut` /
  `DesempenoPartidoOut` (`docs/ARCH.md` §18.2);
* emitir AMBAS clasificaciones del resultado consumado (`vertice_qbe` y
  `vertice_mercado`) para que el pintor Jinja no ordene ni compare nada;
* delegar el des-margen a las leyes selladas: `desmarcar_cuotas_proporcional`
  (`[VAULT-CORE-007-C]`) y `desmarginar_shin` (`[LN-QBE-151]`), y el Brier a
  `calcular_brier_multicategorico` (`[LN-QBE-100]`).

Fail-Loud de dominio (`docs/ARCH.md` §18.1): un `casino` fuera del catálogo o un
`devig` distinto de `shin` / `proporcional` levantan `ValueError`. No existe
degradación silenciosa a la fuente por defecto ni reparación de la petición.

Ausencias declaradas, jamás imputadas: sin cuota válida no hay `q_mkt`, sin `S=0`
no hay vértice que teñir y sin varias casas no hay spread inter-casinos.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from pydantic import BaseModel, Field

from app.adapters.db_readonly import BaseDatosSoloLectura
from app.services.calibration_view import cargar_vista_calibracion

logger = logging.getLogger(__name__)

#: Bóveda OLAP histórica (12 temporadas FootyStats), abierta en solo lectura.
RUTA_HISTORICO = Path(__file__).resolve().parents[2] / "data" / "qbe_historico.db"
#: Clave de temporada tal como la escribe la bóveda histórica (sin sufijo «· Actual»).
CLAVE_TEMPORADA_ACTUAL = "2026_2027"
#: `[ARCH-1.4.78 · FIX]` La bóveda no porta número de jornada: el corpus se agrupa
#: en bloques cronológicos de 9 partidos (calendario Liga MX) por temporada.
BLOQUE_HISTORICO = 9

#: `docs/ARCH.md` §18.1 — dominio cerrado de fuentes de mercado.
CASINOS_RECONOCIDOS: Tuple[str, ...] = ("caliente", "novibet", "betway", "footystats")
#: `docs/ARCH.md` §18.1 — métodos de des-marginado admitidos.
METODOS_DEVIG: Tuple[str, ...] = ("shin", "proporcional")
#: `docs/DESIGN.md` §7.4.3 — fuentes rectoras del conmutador.
MANDOS_RECTORES: Tuple[str, ...] = ("qbe", "mercado")

#: `[DES-QBE-078 · REV.3]` Catálogo canónico de temporadas (homólogo a `/consenso`).
#: El snapshot 3NF sirve el universo de la temporada en curso; una temporada
#: histórica se declara vacía —jamás se rellena con datos de otra bóveda—.
TEMPORADAS_CANONICAS: Tuple[str, ...] = (
    "Todas",
    "2026_2027 · Actual",
    "2025_2026",
    "2024_2025",
    "2023_2024",
    "2022_2023",
    "2021_2022",
    "2020_2021",
    "2019_2020",
    "2018_2019",
    "2017_2018",
    "2016_2017",
    "2015_2016",
)
TEMPORADA_TODAS = "Todas"
TEMPORADA_ACTUAL = "2026_2027 · Actual"

MAPA_VERTICE_QBE: Dict[str, str] = {"P_MAX": "max", "P_MID": "mid", "P_LOW": "low"}
RANGOS_VERTICE: Tuple[str, ...] = ("max", "mid", "low")
DESENLACES: Tuple[str, ...] = ("LOCAL", "EMPATE", "VISITANTE")

ETIQUETA_SIN_EVIDENCIA = "SIN EVIDENCIA"
MOTIVO_SPREAD = (
    "El snapshot sirve una sola fuente de cuotas por partido: no hay dispersión "
    "inter-casinos que medir (cero cifra fabricada)"
)


# ── Contratos DTO (`docs/ARCH.md` §18.2) ─────────────────────────────────────
class DesempenoPartidoOut(BaseModel):
    """Tarjeta de partido: coexistencia de P′, consenso des-marginado y cuotas."""

    id_partido: str
    local: str
    visitante: str
    marcador: Optional[str] = None
    resultado_real: Optional[str] = None
    brier_qbe: Optional[float] = None
    brier_mercado: Optional[float] = None
    es_cold_start: bool = False
    suficiencia_s_i: int = 0
    p_local: Optional[float] = None
    p_empate: Optional[float] = None
    p_visitante: Optional[float] = None
    q_local: Optional[float] = None
    q_empate: Optional[float] = None
    q_visitante: Optional[float] = None
    momios: Dict[str, float] = Field(default_factory=dict)
    r_max: Optional[str] = None
    r_mid: Optional[str] = None
    r_low: Optional[str] = None
    vertice_qbe: Optional[str] = None
    vertice_mercado: Optional[str] = None
    #: `[REV.4]` Alpha bidireccional del partido a favor de la base activa (§7.4.9).
    alpha_partido_pct: Optional[float] = None
    #: `[REV.4]` ¿El resultado cayó en el par de cobertura de la base activa?
    rescate_partido: bool = False
    #: `[REV.4]` Diagnóstico de vértice: PRIMARIO / RESCATE / RUPTURA / COLD_START.
    diagnostico_cobertura: Optional[str] = None
    shin_z: Optional[float] = None
    spread_cuotas: Optional[float] = None
    semaforos: Dict[str, str] = Field(default_factory=dict)
    atribucion_disponible: bool = False
    atribucion_driver: Optional[str] = None
    variables_44: Dict[str, Any] = Field(default_factory=dict)
    origen_captura: Optional[str] = None


class DesempenoJornadaOut(BaseModel):
    """Contenedor desplegable de la parrilla de desempeño.

    `[DES-QBE-078 · REV.4]` Publica la terna de cobertura por jornada con el
    Invariante C-50 (`cobertura = pmax + pmid`) y el Alpha bidireccional.
    """

    numero: int
    #: Rótulo de presentación (`2025_2026 · J12` en el modo «Todas»); `None` ⇒ `JORNADA n`.
    etiqueta: Optional[str] = None
    total_partidos: int
    pmax_success_rate: Optional[float] = None
    pmid_success_rate: Optional[float] = None
    cobertura_resultado_rate: Optional[float] = None
    alpha: Optional[float] = None
    brier_qbe: Optional[float] = None
    brier_mkt: Optional[float] = None
    partidos: List[DesempenoPartidoOut] = Field(default_factory=list)


class DesempenoKPIsOut(BaseModel):
    """Banda superior de siete macro KPIs unificados.

    `[DES-QBE-078 · REV.4]` La terna de cobertura cumple el Invariante C-50:
    `cobertura_resultado_rate` es la suma estricta de `pmax_success_rate` y
    `pmid_success_rate`.
    """

    pmax_success_rate: Optional[float] = None
    pmid_success_rate: Optional[float] = None
    cobertura_resultado_rate: Optional[float] = None
    brier_qbe: Optional[float] = None
    brier_mercado: Optional[float] = None
    alpha_desempeno: Optional[float] = None
    total_partidos: int = 0
    total_jornadas: int = 0
    metodo_devig: str = "shin"
    mando_rector: str = "qbe"
    temporadas_disponibles: List[str] = Field(default_factory=list)


# ── Aduana Fail-Loud (`docs/ARCH.md` §18.1) ─────────────────────────────────
def validar_dominio(*, casinos: Sequence[str], devig: str, mando: str) -> None:
    """Certifica el dominio de la petición. Fuera de él: `ValueError` inmediato.

    Raises:
        ValueError: si algún `casino` no pertenece a `CASINOS_RECONOCIDOS`, si
            `devig` no es `shin` / `proporcional` o si `mando` no es
            `qbe` / `mercado`. La petición muere ruidosamente; no se sustituye
            por el defecto ni se degrada a `shin`.
    """
    desconocidos = sorted({c for c in casinos if c not in CASINOS_RECONOCIDOS})
    if desconocidos:
        raise ValueError(
            "Casino no reconocido: "
            f"{desconocidos!r}. Dominio canónico de fuentes de mercado: "
            f"{CASINOS_RECONOCIDOS} [ARCH-1.4.78]."
        )
    if devig not in METODOS_DEVIG:
        raise ValueError(
            f"Método de de-vig no reconocido: {devig!r}. Dominio canónico: "
            f"{METODOS_DEVIG} [ARCH-1.4.78]."
        )
    if mando not in MANDOS_RECTORES:
        raise ValueError(
            f"Distribución Base no reconocida: {mando!r}. Dominio canónico: "
            f"{MANDOS_RECTORES} [DES-QBE-078]."
        )


def normalizar_seleccion(casinos: Optional[Sequence[str]]) -> Tuple[str, ...]:
    """Normaliza las casillas de fuentes; sin selección rige el defecto (las cuatro)."""
    seleccion: List[str] = []
    for bruto in casinos or ():
        nombre = str(bruto or "").strip().lower()
        if nombre and nombre not in seleccion:
            seleccion.append(nombre)
    return tuple(seleccion) if seleccion else CASINOS_RECONOCIDOS


# ── Des-margen delegado a las leyes selladas ────────────────────────────────
def _desmargen(src: Dict[str, Any], devig: str) -> Tuple[Tuple[Optional[float], ...], Optional[float]]:
    """Devuelve `(q_local, q_empate, q_visitante)` y el `z` de Shin si existe.

    * `proporcional` → transcribe el vector ya servido por el reporte canónico
      (que usó `desmarcar_cuotas_proporcional`).
    * `shin` → invoca `desmarginar_shin` sobre las MISMAS cuotas servidas.

    Sin terna íntegra (o ante cuota inadmisible) no hay consenso: se declara la
    ausencia en lugar de reparar la cuota o imputar `1/3`.
    """
    momios = src.get("momios")
    if not isinstance(momios, dict):
        return (None, None, None), None
    try:
        cuotas = (float(momios["L"]), float(momios["E"]), float(momios["V"]))
    except (KeyError, TypeError, ValueError):
        return (None, None, None), None

    if devig == "proporcional":
        vector = (src.get("q_local"), src.get("q_empate"), src.get("q_visitante"))
        if all(valor is not None for valor in vector):
            return vector, None
        # `[ARCH-1.4.78 · FIX]` La bóveda histórica no sirve `q_mkt` precalculado:
        # se des-margina con la MISMA ley canónica sobre las cuotas servidas.
        from src.core.contracts.portfolio_math import desmarcar_cuotas_proporcional

        return desmarcar_cuotas_proporcional(*cuotas), None

    try:
        from src.core.consensus import desmarginar_shin

        limpio = desmarginar_shin(cuotas)
    except (ValueError, TypeError) as exc:  # InvalidOddsException ⊂ ValueError
        logger.warning(
            "Consenso Shin no identificable en %s: %s. Se declara SIN EVIDENCIA.",
            src.get("id_partido"),
            exc,
        )
        return (None, None, None), None
    return (limpio.p_local, limpio.p_empate, limpio.p_visitante), limpio.z_insider


def _orden_mercado(q: Sequence[Optional[float]]) -> Optional[Tuple[str, str, str]]:
    """Roles 1X2 ordenados por el consenso des-marginado (mayor ⇒ menor).

    Ordenamiento de presentación (no de negocio): empatado el valor, el desempate
    es alfabético para que la vista sea determinista. `None` si falta el vector.
    """
    if any(valor is None for valor in q):
        return None
    pares = list(zip(DESENLACES, (float(valor) for valor in q)))  # type: ignore[arg-type]
    orden = sorted(pares, key=lambda par: (-par[1], par[0]))
    return tuple(rol for rol, _ in orden)  # type: ignore[return-value]


def _vertice_mercado(resultado: Optional[str], q: Sequence[Optional[float]]) -> Optional[str]:
    """Clasifica el resultado consumado dentro del orden del consenso des-marginado."""
    if resultado not in DESENLACES:
        return None
    orden = _orden_mercado(q)
    if orden is None:
        return None
    for indice, rol in enumerate(orden):
        if rol == resultado:
            return RANGOS_VERTICE[indice]
    return None


def _registros_comunes(partidos: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Muestra COINCIDENTE del universo: P′ ∩ q_mkt ∩ resultado en el mismo partido.

    `[DES-QBE-078 · REV.3]` Los Briers y el Alpha se agregan sobre esta muestra,
    no sobre denominadores distintos. Un partido sin vector de mercado no puede
    puntuar el Brier de mercado ni el Alpha (cero imputación).
    """
    comunes: List[Dict[str, Any]] = []
    for partido in partidos:
        resultado = partido.get("resultado_real")
        if resultado not in DESENLACES:
            continue
        campos = (
            "p_local",
            "p_empate",
            "p_visitante",
            "q_local",
            "q_empate",
            "q_visitante",
        )
        if any(partido.get(campo) is None for campo in campos):
            continue
        comunes.append(partido)
    return comunes


def _brier(partidos: Sequence[Dict[str, Any]], fuente: str) -> Optional[float]:
    """Brier 3N delegado a `[LN-QBE-100]` sobre la muestra coincidente. Vacío ⇒ `None`."""
    campos = (
        ("p_local", "p_empate", "p_visitante")
        if fuente == "qbe"
        else ("q_local", "q_empate", "q_visitante")
    )
    registros: List[Dict[str, Any]] = []
    for partido in _registros_comunes(partidos):
        valores = [partido.get(campo) for campo in campos]
        if any(valor is None for valor in valores):
            continue
        registros.append(
            {
                "p_local": float(valores[0]),
                "p_empate": float(valores[1]),
                "p_visitante": float(valores[2]),
                "resultado": partido.get("resultado_real"),
            }
        )
    if not registros:
        return None
    from src.core.contracts.portfolio_math import calcular_brier_multicategorico

    return calcular_brier_multicategorico(registros)


def _par_cobertura(
    partido: Dict[str, Any], mando: str
) -> Optional[frozenset]:
    """Par de cobertura de la base activa, o `None` si el partido no es evaluable.

    `[DES-QBE-078 · REV.4]` Una sola definición para las tres superficies:

    * `qbe`      → `{r_max, r_mid}` (vértices fiduciarios del núcleo).
    * `mercado`  → `{max q_mkt, second_max q_mkt}` (orden del consenso).

    `None` cuando el resultado consumado no existe o la fuente no puede formar
    el par (cold start sin vértices, partido sin cuotas): no hay cobertura que
    medir, jamás una cobertura imputada.
    """
    resultado = partido.get("resultado_real")
    if resultado not in DESENLACES:
        return None
    if mando == "qbe":
        r_max = partido.get("r_max")
        r_mid = partido.get("r_mid")
        if r_max is None or r_mid is None:
            return None
        return frozenset({r_max, r_mid})
    orden = _orden_mercado(
        (
            partido.get("q_local"),
            partido.get("q_empate"),
            partido.get("q_visitante"),
        )
    )
    if orden is None:
        return None
    return frozenset({orden[0], orden[1]})


def _rescate_partido(partido: Dict[str, Any], mando: str) -> bool:
    """`rescate_partido` de la tarjeta: ¿el resultado cayó en el par de la base?

    `False` si cayó fuera del par o si el partido no es evaluable. Se deriva de
    `_par_cobertura`, la MISMA ley que agrega la Tasa de Rescate: la tarjeta y
    el KPI no pueden discrepar.
    """
    par = _par_cobertura(partido, mando)
    return bool(par is not None and partido.get("resultado_real") in par)


def _tasa_cobertura(
    partidos: Sequence[Dict[str, Any]], mando: str
) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """Terna de cobertura de la base activa: `(pmax, pmid, cobertura)`.

    `[DES-QBE-078 · REV.4]` Sobre los partidos evaluables (resultado consumado,
    fuera de Cold Start y con la fuente capaz de formar su par de vértices):

    * `pmax_success_rate` → porcentaje donde el resultado es el primer vértice.
    * `pmid_success_rate` → porcentaje donde el resultado es el segundo vértice.
    * `cobertura_resultado_rate` → suma estricta de las dos anteriores (C-50).

    El denominador es el número de partidos evaluables, no el universo total.
    Sin evaluables la terna es `(None, None, None)`, jamás ceros fabricados.
    """
    evaluados = 0
    aciertos_pmax = 0
    aciertos_pmid = 0
    for partido in partidos:
        if partido.get("es_cold_start"):
            continue
        resultado = partido.get("resultado_real")
        if resultado not in DESENLACES:
            continue
        if mando == "qbe":
            r_max = partido.get("r_max")
            r_mid = partido.get("r_mid")
            if r_max is None or r_mid is None:
                continue
            evaluados += 1
            if resultado == r_max:
                aciertos_pmax += 1
            elif resultado == r_mid:
                aciertos_pmid += 1
        else:
            orden = _orden_mercado(
                (
                    partido.get("q_local"),
                    partido.get("q_empate"),
                    partido.get("q_visitante"),
                )
            )
            if orden is None:
                continue
            evaluados += 1
            if resultado == orden[0]:
                aciertos_pmax += 1
            elif resultado == orden[1]:
                aciertos_pmid += 1

    if not evaluados:
        return (None, None, None)

    pmax = round((aciertos_pmax / evaluados) * 100.0, 2)
    pmid = round((aciertos_pmid / evaluados) * 100.0, 2)
    # Invariante C-50: la cobertura se SUMA, nunca se recalcula por separado.
    cobertura = round(pmax + pmid, 2)
    return (pmax, pmid, cobertura)


def _diagnostico_cobertura(
    partido: Dict[str, Any], mando: str
) -> Optional[str]:
    """Vértice de cobertura del resultado consumado bajo la base activa.

    `PRIMARIO` / `RESCATE` / `RUPTURA` / `COLD_START`, o `None` si el partido
    no es evaluable. Es una clasificación por igualdad de roles, no aritmética.
    """
    if partido.get("es_cold_start"):
        return "COLD_START"
    resultado = partido.get("resultado_real")
    if resultado not in DESENLACES:
        return None
    if mando == "qbe":
        if resultado == partido.get("r_max"):
            return "PRIMARIO"
        if resultado == partido.get("r_mid"):
            return "RESCATE"
        if resultado == partido.get("r_low"):
            return "RUPTURA"
        return None
    vertice = _vertice_mercado(
        resultado,
        (
            partido.get("q_local"),
            partido.get("q_empate"),
            partido.get("q_visitante"),
        ),
    )
    return {"max": "PRIMARIO", "mid": "RESCATE", "low": "RUPTURA"}.get(vertice)


def _coeficiente_alpha(
    brier_qbe: Optional[float],
    brier_mercado: Optional[float],
    mando: str = "qbe",
) -> Optional[float]:
    """Alpha bidireccional a favor de la base activa (`docs/DESIGN.md` §7.4.9).

    * base `qbe`      → `(1 − BS_QBE / BS_MKT) × 100` (positivo ⇒ Q-BE mejor).
    * base `mercado`  → `(1 − BS_MKT / BS_QBE) × 100` (positivo ⇒ mercado mejor).

    Sin par de Briers o con denominador `≤ 0` no hay medición: `None`, jamás un
    cero fabricado.
    """
    if brier_qbe is None or brier_mercado is None:
        return None
    if mando == "mercado":
        base, oponente = brier_mercado, brier_qbe
    else:
        base, oponente = brier_qbe, brier_mercado
    if oponente <= 0.0:
        return None
    return round((1.0 - (base / oponente)) * 100.0, 2)


def _brier_vector(
    vector: Sequence[Optional[float]], resultado: Optional[str]
) -> Optional[float]:
    """Brier del partido sobre el vector servido (misma ley `[LN-QBE-100]`).

    Se evalúa por tarjeta para que la banda y las casillas compartan la misma
    aritmética en ambas bóvedas: sin vector o sin desenlace no hay cifra.
    """
    if resultado not in DESENLACES or any(valor is None for valor in vector):
        return None
    from src.core.contracts.portfolio_math import calcular_brier_multicategorico

    registro = {
        "p_local": float(vector[0]),
        "p_empate": float(vector[1]),
        "p_visitante": float(vector[2]),
        "resultado": resultado,
    }
    return calcular_brier_multicategorico([registro])


def _momios_normalizados(momios: Any) -> Dict[str, float]:
    """Transcribe las cuotas decimales servidas; lo ilegible no se inventa."""
    if not isinstance(momios, dict):
        return {}
    limpio: Dict[str, float] = {}
    for clave in ("L", "E", "V"):
        valor = momios.get(clave)
        if isinstance(valor, bool) or valor is None:
            continue
        try:
            limpio[clave] = float(valor)
        except (TypeError, ValueError):
            continue
    return limpio


def _partido_out(src: Dict[str, Any], devig: str, mando: str = "qbe") -> DesempenoPartidoOut:
    """Proyecta un partido (snapshot o bóveda histórica) al contrato de la tarjeta.

    `[DES-QBE-078 · REV.4]` Además de las dos clasificaciones del resultado,
    emite la lectura individual de la base activa: `alpha_partido_pct` (misma ley
    bidireccional del KPI, §7.4.9) y `rescate_partido` (¿cayó en el par de
    cobertura?, §7.1 · §18.2).
    """
    q, shin_z = _desmargen(src, devig)
    resultado = src.get("resultado_real")
    es_cold_start = bool(src.get("es_cold_start"))
    vertice_qbe = (
        "cold_start" if es_cold_start else MAPA_VERTICE_QBE.get(src.get("clasificacion_triada"))
    )
    # Ambas bóvedas se puntúan con la MISMA ley: el Brier de la tarjeta se deriva
    # del vector servido (P′ y q_mkt del método activo), sin heredar una cifra
    # calculada con otro denominador.
    p_vector = (src.get("p_local"), src.get("p_empate"), src.get("p_visitante"))
    brier_qbe = _brier_vector(p_vector, resultado)
    brier_mercado = _brier_vector(q, resultado)

    semaforos = src.get("semaforos")
    return DesempenoPartidoOut(
        id_partido=str(src.get("id_partido") or ""),
        local=str(src.get("local") or ETIQUETA_SIN_EVIDENCIA),
        visitante=str(src.get("visitante") or ETIQUETA_SIN_EVIDENCIA),
        marcador=src.get("marcador"),
        resultado_real=resultado,
        brier_qbe=brier_qbe,
        brier_mercado=brier_mercado,
        es_cold_start=es_cold_start,
        suficiencia_s_i=int(src.get("suficiencia_s_i") or 0),
        p_local=src.get("p_local"),
        p_empate=src.get("p_empate"),
        p_visitante=src.get("p_visitante"),
        q_local=q[0],
        q_empate=q[1],
        q_visitante=q[2],
        momios=_momios_normalizados(src.get("momios")),
        r_max=src.get("r_max"),
        r_mid=src.get("r_mid"),
        r_low=src.get("r_low"),
        vertice_qbe=vertice_qbe,
        vertice_mercado=_vertice_mercado(resultado, q),
        alpha_partido_pct=_coeficiente_alpha(brier_qbe, brier_mercado, mando),
        rescate_partido=_rescate_partido(
            {
                "resultado_real": resultado,
                "r_max": src.get("r_max"),
                "r_mid": src.get("r_mid"),
                "q_local": q[0],
                "q_empate": q[1],
                "q_visitante": q[2],
            },
            mando,
        ),
        diagnostico_cobertura=_diagnostico_cobertura(
            {
                "es_cold_start": es_cold_start,
                "resultado_real": resultado,
                "r_max": src.get("r_max"),
                "r_mid": src.get("r_mid"),
                "r_low": src.get("r_low"),
                "q_local": q[0],
                "q_empate": q[1],
                "q_visitante": q[2],
            },
            mando,
        ),
        shin_z=shin_z,
        spread_cuotas=None,
        semaforos=(
            {str(clave): str(valor) for clave, valor in semaforos.items()}
            if isinstance(semaforos, dict)
            else {}
        ),
        atribucion_disponible=bool(src.get("atribucion_disponible")),
        atribucion_driver=src.get("atribucion_driver"),
        variables_44=(
            src.get("variables_44") if isinstance(src.get("variables_44"), dict) else {}
        ),
        origen_captura=src.get("origen_captura"),
    )


def _rango(
    desde: Optional[int], hasta: Optional[int], numeros: Sequence[int]
) -> Tuple[Optional[int], Optional[int]]:
    """Rango declarado del universo; los extremos se normalizan sin alterar el dato."""
    if not numeros:
        return (None, None)
    inferior = int(desde) if desde is not None else min(numeros)
    superior = int(hasta) if hasta is not None else max(numeros)
    if inferior > superior:
        inferior, superior = superior, inferior
    return (inferior, superior)


# ── Enrutador dual de bóvedas (`[ARCH-1.4.78 · FIX]`) ───────────────────────
def _partido_historico(fila: Any) -> Dict[str, Any]:
    """Proyecta una fila del corpus histórico al contrato de la tarjeta.

    El orden fiduciario NO se decide aquí: se delega en
    `resolver_orden_fiduciario_con_indiferencia` (`[LN-QBE-124]`), la MISMA ley
    que gobierna el snapshot vivo. El desnivel de altitud no viaja en la bóveda
    ⇒ `ΔAlt⁺ = 0.0` declarado (sin rescate territorial inventado).
    """
    from src.core.contracts.portfolio_math import resolver_orden_fiduciario_con_indiferencia

    p_local = float(fila["p_local"])
    p_empate = float(fila["p_empate"])
    p_visitante = float(fila["p_visitante"])
    goles_local = int(fila["home_goals"])
    goles_visita = int(fila["away_goals"])
    if goles_local > goles_visita:
        resultado = "LOCAL"
    elif goles_local < goles_visita:
        resultado = "VISITANTE"
    else:
        resultado = "EMPATE"

    orden = resolver_orden_fiduciario_con_indiferencia(
        p_local, p_empate, p_visitante, delta_alt=0.0
    )
    r_max, r_mid, r_low = orden["r_max"], orden["r_mid"], orden["r_low"]
    if resultado == r_max:
        clasificacion = "P_MAX"
    elif resultado == r_mid:
        clasificacion = "P_MID"
    else:
        clasificacion = "P_LOW"

    return {
        "id_partido": str(fila["match_id"]),
        "local": str(fila["home_team"]),
        "visitante": str(fila["away_team"]),
        "marcador": f"{goles_local} - {goles_visita}",
        "resultado_real": resultado,
        # §15.5: la bóveda sólo persiste distribuciones con S(I)=1 ⇒ no es cold start.
        "es_cold_start": False,
        "suficiencia_s_i": 1,
        "p_local": p_local,
        "p_empate": p_empate,
        "p_visitante": p_visitante,
        # `q_mkt` lo resuelve `_desmargen` desde las cuotas servidas (Shin o Prop.).
        "q_local": None,
        "q_empate": None,
        "q_visitante": None,
        "momios": {
            "L": float(fila["odd_home"]),
            "E": float(fila["odd_draw"]),
            "V": float(fila["odd_away"]),
        },
        "r_max": r_max,
        "r_mid": r_mid,
        "r_low": r_low,
        "clasificacion_triada": clasificacion,
        "semaforos": {},
        "atribucion_disponible": False,
        "atribucion_driver": None,
        "variables_44": {},
        "origen_captura": "HISTORICO",
    }


def _leer_historico(
    temporada: Optional[str],
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Filas del corpus histórico con P′, cuotas y marcador (solo lectura estricta).

    `temporada=None` ⇒ todas las temporadas históricas. La temporada en curso se
    excluye SIEMPRE: su fuente es el snapshot vivo y duplicarla falsearía el
    universo de «Todas».
    """
    if not RUTA_HISTORICO.is_file():
        return [], (
            f"Bóveda histórica no disponible en {RUTA_HISTORICO}. "
            "El Observatorio no sustituye una bóveda por otra."
        )
    filtro = "" if temporada is None else "AND m.temporada = :temporada"
    consulta = f"""
        SELECT m.match_id, m.temporada, m.fecha_utc, m.home_team, m.away_team,
               m.home_goals, m.away_goals, m.odd_home, m.odd_draw, m.odd_away,
               d.p_local, d.p_empate, d.p_visitante
        FROM historical_matches m
        INNER JOIN historical_sovereign_distributions d ON m.match_id = d.match_id
        WHERE m.temporada <> :actual
          AND m.odd_home > 1 AND m.odd_draw > 1 AND m.odd_away > 1
          AND m.home_goals IS NOT NULL AND m.away_goals IS NOT NULL
          AND d.p_local IS NOT NULL AND d.p_empate IS NOT NULL AND d.p_visitante IS NOT NULL
          {filtro}
        ORDER BY m.temporada ASC, m.fecha_utc ASC, m.match_id ASC
    """
    parametros: Dict[str, Any] = {"actual": CLAVE_TEMPORADA_ACTUAL}
    if temporada is not None:
        parametros["temporada"] = temporada
    try:
        filas = BaseDatosSoloLectura(RUTA_HISTORICO).ejecutar_select(consulta, parametros)
    except Exception as exc:  # noqa: BLE001 — la vitrina degrada, nunca tumba la app
        logger.exception("No se pudo leer la bóveda histórica")
        return [], f"No se pudo leer la bóveda histórica: {exc}"
    return [dict(fila) for fila in filas], None


def _bloques_historicos(filas: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Agrupa el corpus por temporada en bloques cronológicos de 9 partidos.

    `historical_matches` no porta número de jornada: el bloque es el ordinal
    declarado del calendario (`[ARCH-1.4.78 · FIX]`), nunca una ronda inventada.
    """
    por_temporada: Dict[str, List[Dict[str, Any]]] = {}
    for fila in filas:
        por_temporada.setdefault(str(fila.get("temporada") or ""), []).append(fila)

    bloques: List[Dict[str, Any]] = []
    for temporada in sorted(por_temporada):
        grupo = por_temporada[temporada]
        for indice in range(0, len(grupo), BLOQUE_HISTORICO):
            tramo = grupo[indice : indice + BLOQUE_HISTORICO]
            bloques.append(
                {
                    "temporada": temporada,
                    "jornada": indice // BLOQUE_HISTORICO + 1,
                    "partidos": [_partido_historico(fila) for fila in tramo],
                }
            )
    return bloques


def _universo_live() -> Dict[str, Any]:
    """Universo de la temporada en curso: snapshot 3NF vía builder canónico."""
    calibracion = cargar_vista_calibracion()
    return {
        "jornadas": [
            {
                "jornada": int(fila.get("jornada") or 0),
                "etiqueta": None,
                "partidos": list(fila.get("partidos") or []),
            }
            for fila in (calibracion.get("jornadas") or [])
        ],
        "fuente": calibracion.get("fuente") or {},
        "error": calibracion.get("error"),
        "motivo_vacio": None,
    }


def _universo_historico(temporada: str) -> Dict[str, Any]:
    """Universo de una temporada histórica: bóveda OLAP en solo lectura."""
    fuente = {
        "tipo": "historico_olap",
        "ruta": str(RUTA_HISTORICO),
        "nombre": RUTA_HISTORICO.name,
        "temporada": temporada,
        "solo_lectura": True,
    }
    filas, error = _leer_historico(temporada)
    if error:
        return {"jornadas": [], "fuente": fuente, "error": error, "motivo_vacio": None}
    if not filas:
        return {
            "jornadas": [],
            "fuente": fuente,
            "error": None,
            "motivo_vacio": (
                f"La temporada {temporada!r} no cuenta con distribuciones P′ en la "
                "bóveda histórica (0 filas): sin vector causal FotMob. Universo vacío "
                "declarado, sin relleno de otra temporada."
            ),
        }
    return {
        "jornadas": [
            {"jornada": bloque["jornada"], "etiqueta": None, "partidos": bloque["partidos"]}
            for bloque in _bloques_historicos(filas)
        ],
        "fuente": fuente,
        "error": None,
        "motivo_vacio": None,
    }


def _universo_todas() -> Dict[str, Any]:
    """Universo masivo: corpus histórico completo + temporada en curso del snapshot."""
    filas, error = _leer_historico(None)
    bloques = _bloques_historicos(filas) if filas else []
    live = _universo_live()

    jornadas: List[Dict[str, Any]] = []
    ordinal = 0
    for bloque in bloques:
        ordinal += 1
        jornadas.append(
            {
                "jornada": ordinal,
                "etiqueta": f"{bloque['temporada']} · J{bloque['jornada']}",
                "partidos": bloque["partidos"],
            }
        )
    for fila in live["jornadas"]:
        ordinal += 1
        jornadas.append(
            {
                "jornada": ordinal,
                "etiqueta": f"{CLAVE_TEMPORADA_ACTUAL} · J{fila['jornada']}",
                "partidos": fila["partidos"],
            }
        )

    return {
        "jornadas": jornadas,
        "fuente": {
            "tipo": "dual_vault",
            "ruta": str(RUTA_HISTORICO),
            "nombre": "qbe_historico.db + snapshot 3NF",
            "temporada": TEMPORADA_TODAS,
            "solo_lectura": True,
        },
        "error": error,
        "motivo_vacio": None,
    }


def _kpis(
    jornadas: Sequence[DesempenoJornadaOut], mando: str, devig: str = "shin"
) -> DesempenoKPIsOut:
    """Ensambla la banda de siete macro KPIs del universo filtrado.

    `[DES-QBE-078 · REV.4]` La muestra de Briers/Alpha es la COINCIDENTE
    (P′ ∩ q_mkt ∩ resultado). La terna de cobertura se deriva de
    `_tasa_cobertura`, la MISMA ley que alimenta cada jornada: la cobertura es
    la suma estricta de sus dos componentes (Invariante C-50).
    """
    partidos = [partido.model_dump() for jornada in jornadas for partido in jornada.partidos]
    brier_qbe = _brier(partidos, "qbe")
    brier_mercado = _brier(partidos, "mercado")
    pmax, pmid, cobertura = _tasa_cobertura(partidos, mando)
    return DesempenoKPIsOut(
        pmax_success_rate=pmax,
        pmid_success_rate=pmid,
        cobertura_resultado_rate=cobertura,
        brier_qbe=brier_qbe,
        brier_mercado=brier_mercado,
        alpha_desempeno=_coeficiente_alpha(brier_qbe, brier_mercado, mando),
        total_partidos=len(partidos),
        total_jornadas=len(jornadas),
        metodo_devig=devig,
        mando_rector=mando,
        temporadas_disponibles=list(TEMPORADAS_CANONICAS),
    )


def cargar_vista_desempeno(
    *,
    mando: str = "qbe",
    temporada: str = "",
    jornada_desde: Optional[int] = None,
    jornada_hasta: Optional[int] = None,
    casinos: Optional[Sequence[str]] = None,
    devig: str = "shin",
) -> Dict[str, Any]:
    """Contexto Jinja completo de `/desempeno` (`{"mando", "filtros", "kpis", …}`).

    Enrutamiento dual: `2026_2027 · Actual` → snapshot vivo; `Todas` → corpus
    histórico + temporada en curso; cualquier otra temporada canónica → bóveda
    histórica OLAP. Una temporada sin distribuciones P′ se declara vacía con su
    motivo; jamás se rellena con otra bóveda.

    Raises:
        ValueError: dominio de `casino` / `devig` / `mando` fuera de contrato
            (Fail-Loud de `docs/ARCH.md` §18.1). Se valida ANTES de abrir
            cualquier bóveda: una petición inválida no cuesta lectura.
    """
    mando_norm = str(mando or "qbe").strip().lower()
    devig_norm = str(devig or "shin").strip().lower()
    seleccion = normalizar_seleccion(casinos)
    validar_dominio(casinos=seleccion, devig=devig_norm, mando=mando_norm)

    # Sin parámetro la vista aterriza en la temporada EN CURSO (snapshot vivo);
    # «Todas» es una petición explícita del Director y agrega el corpus histórico.
    temporada_sel = str(temporada or "").strip() or TEMPORADA_ACTUAL
    if temporada_sel == TEMPORADA_ACTUAL:
        universo = _universo_live()
    elif temporada_sel == TEMPORADA_TODAS:
        universo = _universo_todas()
    else:
        universo = _universo_historico(temporada_sel)

    fuente = universo.get("fuente") or {}
    jornadas_cal = list(universo.get("jornadas") or [])
    motivo = universo.get("error")
    motivo_vacio = universo.get("motivo_vacio")

    # El modo «Todas» usa un ordinal global de bloques: el rango Jn no aplica.
    numeros = [] if temporada_sel == TEMPORADA_TODAS else [
        int(fila.get("jornada") or 0) for fila in jornadas_cal
    ]
    desde, hasta = _rango(jornada_desde, jornada_hasta, numeros)

    jornadas: List[DesempenoJornadaOut] = []
    for fila in jornadas_cal:
        numero = int(fila.get("jornada") or 0)
        if desde is not None and numero < desde:
            continue
        if hasta is not None and numero > hasta:
            continue
        crudos = list(fila.get("partidos") or [])
        partidos = [_partido_out(partido, devig_norm, mando_norm) for partido in crudos]
        planos = [partido.model_dump() for partido in partidos]
        brier_qbe_jornada = _brier(planos, "qbe")
        brier_mercado_jornada = _brier(planos, "mercado")
        pmax_j, pmid_j, cobertura_j = _tasa_cobertura(planos, mando_norm)
        alpha_j = _coeficiente_alpha(
            brier_qbe_jornada, brier_mercado_jornada, mando_norm
        )
        jornadas.append(
            DesempenoJornadaOut(
                numero=numero,
                etiqueta=fila.get("etiqueta"),
                total_partidos=len(partidos),
                pmax_success_rate=pmax_j,
                pmid_success_rate=pmid_j,
                cobertura_resultado_rate=cobertura_j,
                alpha=alpha_j,
                brier_qbe=brier_qbe_jornada,
                brier_mkt=brier_mercado_jornada,
                partidos=partidos,
            )
        )

    kpis = _kpis(jornadas, mando_norm, devig_norm)

    return {
        "mando": mando_norm,
        "temporadas_disponibles": list(TEMPORADAS_CANONICAS),
        "filtros": {
            "temporada": temporada_sel,
            "jornada_min": desde,
            "jornada_max": hasta,
            "jornadas": numeros,
            "fuentes": list(seleccion),
            "fuentes_disponibles": list(CASINOS_RECONOCIDOS),
            "devig": devig_norm,
        },
        "kpis": kpis.model_dump(),
        "jornadas": [jornada.model_dump() for jornada in jornadas],
        "fuente": fuente,
        "motivo_spread": MOTIVO_SPREAD,
        "motivo_vacio": motivo_vacio,
        "error": motivo,
    }
