"""Orquestador de lectura de la Auditoría de Calibración y Atribución.

[DBBD-FUNGIBLE] Capa de presentación: NO calcula Brier, Alpha, probabilidades ni
ninguna ley de `qbe_core`. Su única responsabilidad es abrir la bóveda 3NF en
modo de solo lectura, invocar el builder canónico del Observatorio y transcribir
su DTO a un modelo de vista Jinja2. La ausencia del motor causal se declara como
`PENDIENTE MOTOR`; la ausencia de una métrica, como `SIN EVIDENCIA`.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import sessionmaker

from app import config
from app.adapters.db_readonly import BaseDatosSoloLectura
from app.routes.backtesting import _motor_solo_lectura, reporte_calibracion_canonico
from app.services.snapshot_refresh import edad_snapshot, snapshot_fresco

logger = logging.getLogger(__name__)

ESTADO_PENDIENTE_MOTOR = "PENDIENTE MOTOR"
ESTADO_SIN_EVIDENCIA = "SIN EVIDENCIA"


def _signo_alpha(valor: Optional[float]) -> str:
    """Clasificación de presentación por signo; no altera el valor canónico."""
    if valor is None:
        return "sin_evidencia"
    if valor > 0.0:
        return "positivo"
    if valor < 0.0:
        return "negativo"
    return "neutro"


def _brier_vars() -> Dict[str, Any]:
    """Placeholder declarado del futuro motor causal. Cero cifras inventadas."""
    return {
        "valor": None,
        "estado": "PENDIENTE_MOTOR",
        "etiqueta": ESTADO_PENDIENTE_MOTOR,
        "fuente": None,
    }


def _componentes_futuros() -> Dict[str, Any]:
    """Slots estables para inyectar Heatmap/Radar sin refactorizar la plantilla."""
    return {
        "heatmap_sinergia": {
            "slot_id": "slot-heatmap-sinergia",
            "lienzo_id": "lienzo-heatmap-sinergia",
            "estado": "PENDIENTE_MOTOR",
            "etiqueta": ESTADO_PENDIENTE_MOTOR,
        },
        "radar_distribucion": {
            "slot_id": "slot-radar-distribucion",
            "lienzo_id": "lienzo-radar-distribucion",
            "estado": "PENDIENTE_MOTOR",
            "etiqueta": ESTADO_PENDIENTE_MOTOR,
        },
    }


def _fuente_base(ruta: Path) -> Dict[str, Any]:
    edad = edad_snapshot(ruta)
    return {
        "tipo": "snapshot_3nf",
        "ruta": str(ruta),
        "nombre": ruta.name,
        "edad_min": round(edad / 60.0, 1) if edad is not None else None,
        "fresco": snapshot_fresco(ruta, 60),
        "liga": ESTADO_SIN_EVIDENCIA,
        "temporada": "No declarada",
        "solo_lectura": True,
    }


def _metadatos_boveda(ruta: Path) -> Dict[str, Any]:
    """Liga y temporada de la MISMA bóveda; nunca se heredan del histórico."""
    metadatos = {"liga": ESTADO_SIN_EVIDENCIA, "temporada": "No declarada"}
    try:
        base = BaseDatosSoloLectura(ruta)
        competiciones = base.ejecutar_select(
            "SELECT id, name FROM competitions ORDER BY name ASC"
        )
        if len(competiciones) == 1:
            fila = competiciones[0]
            metadatos["liga"] = f"{fila['name']} ({fila['id']})"
        elif len(competiciones) > 1:
            metadatos["liga"] = "MULTI"

        temporadas = base.ejecutar_select(
            "SELECT DISTINCT season_id FROM matches "
            "WHERE season_id IS NOT NULL ORDER BY season_id ASC"
        )
        if len(temporadas) == 1:
            metadatos["temporada"] = str(temporadas[0]["season_id"])
        elif len(temporadas) > 1:
            metadatos["temporada"] = "MULTI"
    except (FileNotFoundError, sqlite3.Error) as exc:
        logger.warning("No se pudieron leer los metadatos de la bóveda: %s", exc)
    return metadatos


def _tiene_cuotas(partido: Dict[str, Any]) -> bool:
    """Presencia factual del trío 1X2; no se infiere ni se recalcula Brier."""
    momios = partido.get("momios") or {}
    if not isinstance(momios, dict):
        return False
    try:
        return all(float(momios.get(clave, 0.0) or 0.0) > 1.0 for clave in ("L", "E", "V"))
    except (TypeError, ValueError):
        return False


def _texto_probabilidades(partido: Dict[str, Any]) -> Optional[str]:
    valores = [partido.get("p_local"), partido.get("p_empate"), partido.get("p_visitante")]
    if any(valor is None for valor in valores):
        return None
    try:
        return " / ".join(f"{float(valor):.3f}" for valor in valores)
    except (TypeError, ValueError):
        return None


def _diccionario(valor: Any) -> Dict[str, Any]:
    """Blindaje de transcripción: un bloque ausente se declara vacío, jamás se imputa."""
    return valor if isinstance(valor, dict) else {}


def _partido_vista(partido: Dict[str, Any], mercado_disponible: bool) -> Dict[str, Any]:
    atribucion = partido.get("atribucion_factorial") or {}
    driver = atribucion.get("driver_principal") or {}
    etiqueta_driver = driver.get("etiqueta")
    # [DES-QBE-075] Transcripción ADITIVA de la Match Card Híbrida. Cero aritmética:
    # se copian las magnitudes que `reporte_calibracion_canonico` ya publica por
    # partido (P′ por desenlace, consenso desmarcado, momios, escudos, sellos y el
    # bloque de atribución). El pintor compara; no deriva ni recalcula ninguna ley.
    return {
        "id_partido": partido.get("id_partido"),
        "local": partido.get("local"),
        "visitante": partido.get("visitante"),
        "marcador": partido.get("marcador"),
        "resultado_real": partido.get("resultado_real"),
        "p_texto": _texto_probabilidades(partido),
        "brier_qbe": partido.get("brier_qbe"),
        "brier_mercado": partido.get("brier_mercado") if mercado_disponible else None,
        "brier_vars": None,
        "clasificacion_triada": partido.get("clasificacion_triada"),
        "suficiencia_s_i": partido.get("suficiencia_S_I"),
        "origen_p_prima": partido.get("origen_p_prima"),
        "atribucion_disponible": bool(atribucion.get("disponible")),
        "atribucion_driver": str(etiqueta_driver) if etiqueta_driver else None,
        "atribucion_dimension": driver.get("dimension"),
        # ── [DES-QBE-075] Parrilla 1X2: magnitudes servidas, sin transformar ──
        "p_local": partido.get("p_local"),
        "p_empate": partido.get("p_empate"),
        "p_visitante": partido.get("p_visitante"),
        "q_local": partido.get("q_local"),
        "q_empate": partido.get("q_empate"),
        "q_visitante": partido.get("q_visitante"),
        "momios": _diccionario(partido.get("momios")),
        "local_escudo_url": partido.get("local_escudo_url"),
        "visitante_escudo_url": partido.get("visitante_escudo_url"),
        "origen_captura": partido.get("origen_captura"),
        "es_cold_start": partido.get("suficiencia_S_I") == 0,
        # ── [DES-QBE-075 · REV.2] Identidad de los vértices del símplex Δ² ──
        # `resolver_orden_fiduciario_con_indiferencia` (banda ε = 1 % + rescate
        # territorial) ya emitió el orden: se transcribe tal cual. Un argmax en el
        # pintor perdería ambas leyes y crearía una segunda verdad.
        "r_max": partido.get("r_max"),
        "r_mid": partido.get("r_mid"),
        "r_low": partido.get("r_low"),
        # ── [DES-QBE-075] Micro-HUD y panel 32V (transcripción literal) ──
        "semaforos": _diccionario(atribucion.get("semaforos")),
        "variables_44": _diccionario(atribucion.get("variables_44")),
        "descomposicion_log": _diccionario(atribucion.get("descomposicion_log")),
        "origen_factores": atribucion.get("origen_factores"),
    }


def _jornada_vista(fila: Dict[str, Any]) -> Dict[str, Any]:
    partidos_crudos = fila.get("partidos") or []
    total = int(fila.get("total_partidos") or len(partidos_crudos))
    cobertura_mercado = sum(1 for partido in partidos_crudos if _tiene_cuotas(partido))
    mercado_disponible = cobertura_mercado > 0
    brier_qbe = fila.get("brier_score_qbe") if total > 0 else None
    brier_mercado = (
        fila.get("brier_score_mercado") if total > 0 and mercado_disponible else None
    )
    alpha = (
        fila.get("alpha_calibracion_pct")
        if total > 0 and mercado_disponible
        else None
    )
    return {
        "jornada": int(fila.get("jornada") or 0),
        "total_partidos": total,
        "brier_qbe": brier_qbe,
        "brier_mercado": brier_mercado,
        "alpha_calibracion_pct": alpha,
        "alpha_signo": _signo_alpha(alpha),
        "alpha_etiqueta": fila.get("alpha_etiqueta"),
        "es_cold_start": bool(fila.get("es_cold_start")),
        "cobertura_mercado": cobertura_mercado,
        "mercado_disponible": mercado_disponible,
        "brier_vars": None,
        "partidos": [
            _partido_vista(partido, mercado_disponible) for partido in partidos_crudos
        ],
    }


def _resumen_vacio() -> Dict[str, Any]:
    return {
        "total_partidos": 0,
        "n_jornadas": 0,
        "jornada_min": None,
        "jornada_max": None,
        "brier_qbe": None,
        "brier_mercado": None,
        "alpha_calibracion_pct": None,
        "alpha_signo": "sin_evidencia",
        "alpha_etiqueta": None,
        "cobertura_mercado": 0,
        "mercado_disponible": False,
        "muestra_vacia": True,
        "partidos_pendientes_captura": 0,
        "partidos_resueltos_al_vuelo": 0,
        "jornadas_auditadas": [],
        "brier_vars": None,
    }


def _resumen_vista(
    resumen_canonico: Dict[str, Any],
    jornadas: List[Dict[str, Any]],
    cobertura_mercado: int,
) -> Dict[str, Any]:
    total = int(resumen_canonico.get("total_partidos") or 0)
    mercado_disponible = cobertura_mercado > 0
    brier_qbe = resumen_canonico.get("brier_score_qbe") if total > 0 else None
    brier_mercado = (
        resumen_canonico.get("brier_score_mercado")
        if total > 0 and mercado_disponible
        else None
    )
    alpha = (
        resumen_canonico.get("alpha_calibracion_pct")
        if total > 0 and mercado_disponible
        else None
    )
    numeros_jornada = [fila["jornada"] for fila in jornadas if fila["jornada"] > 0]
    return {
        "total_partidos": total,
        "n_jornadas": len(jornadas),
        "jornada_min": min(numeros_jornada) if numeros_jornada else None,
        "jornada_max": max(numeros_jornada) if numeros_jornada else None,
        "brier_qbe": brier_qbe,
        "brier_mercado": brier_mercado,
        "alpha_calibracion_pct": alpha,
        "alpha_signo": _signo_alpha(alpha),
        "alpha_etiqueta": None,
        "cobertura_mercado": cobertura_mercado,
        "mercado_disponible": mercado_disponible,
        "muestra_vacia": total == 0,
        "partidos_pendientes_captura": int(
            resumen_canonico.get("partidos_pendientes_captura") or 0
        ),
        "partidos_resueltos_al_vuelo": int(
            resumen_canonico.get("partidos_resueltos_al_vuelo") or 0
        ),
        "jornadas_auditadas": list(resumen_canonico.get("jornadas_auditadas") or []),
        "brier_vars": None,
    }


def construir_vista_desde_reporte(
    reporte: Dict[str, Any], *, fuente: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Transcribe el DTO canónico al modelo de vista. Función pura, sin I/O."""
    jornadas_canonicas = reporte.get("jornadas") or []
    jornadas = [_jornada_vista(fila) for fila in jornadas_canonicas]
    partidos = [
        partido
        for fila in jornadas_canonicas
        for partido in (fila.get("partidos") or [])
    ]
    cobertura_mercado = sum(1 for partido in partidos if _tiene_cuotas(partido))
    return {
        "fuente": fuente or {},
        "resumen": _resumen_vista(
            reporte.get("resumen_temporada") or {}, jornadas, cobertura_mercado
        ),
        "jornadas": jornadas,
        "brier_vars": _brier_vars(),
        "componentes_futuros": _componentes_futuros(),
        "error": None,
    }


def _vista_error(fuente: Dict[str, Any], mensaje: str) -> Dict[str, Any]:
    return {
        "fuente": fuente,
        "resumen": _resumen_vacio(),
        "jornadas": [],
        "brier_vars": _brier_vars(),
        "componentes_futuros": _componentes_futuros(),
        "error": mensaje,
    }


def cargar_panel_vars44(id_partido: str) -> Optional[Dict[str, Any]]:
    """[DES-QBE-075] Localiza UN partido auditado para el fragmento B2 del modal 32V.

    Solo lectura y sin aritmética: reutiliza el builder canónico y devuelve la
    transcripción que el Visor ya sirve. La ausencia se declara con `None` (el
    llamador responde 404), jamás con un panel fabricado.
    """
    if not id_partido:
        return None
    vista = cargar_vista_calibracion()
    for jornada in vista.get("jornadas") or []:
        for partido in jornada.get("partidos") or []:
            if str(partido.get("id_partido")) == str(id_partido):
                return {"jornada": jornada.get("jornada"), "partido": partido}
    return None


def cargar_vista_calibracion(league_id: Optional[int] = None) -> Dict[str, Any]:
    """Abre el snapshot en `mode=ro`, ejecuta el builder canónico y degrada con honestidad."""
    ruta = Path(config.BACKTESTING_SNAPSHOT)
    fuente = _fuente_base(ruta)

    if not ruta.is_file():
        return _vista_error(
            fuente,
            (
                f"Snapshot no disponible: {ruta}. Materialícelo con "
                "`python -m scripts.refresh_snapshot --max-age-minutes 60` "
                "desde qbe_observatory/."
            ),
        )

    try:
        motor = _motor_solo_lectura()
        try:
            sesion = sessionmaker(bind=motor)()
            try:
                reporte = reporte_calibracion_canonico(sesion, league_id)
            finally:
                sesion.close()
        finally:
            motor.dispose()
    except RuntimeError as exc:
        return _vista_error(fuente, str(exc))
    except Exception as exc:  # noqa: BLE001 — la vitrina degrada, nunca tumba la app
        logger.exception("No se pudo construir la vista de calibración")
        return _vista_error(
            fuente, f"No se pudo leer el snapshot de calibración: {exc}"
        )

    fuente.update(_metadatos_boveda(ruta))
    return construir_vista_desde_reporte(reporte, fuente=fuente)
