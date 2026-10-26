# -*- coding: utf-8 -*-
"""
🏆 Q-BE PERSISTENCE BRIDGE — SINCRONIZACIÓN DE DISTRIBUCIONES SOBERANAS
[ARCH-1.6.11] Puente Transaccional E2E: Hechos Deportivos -> Sovereign Pipeline -> SQLite 3NF.
Base de Gobierno: Kybern Framework v12.0 / Tratado Volumen I
"""

import logging
import math
from typing import Dict, Any, List, Optional
from src.storage.gateway import PersistenceGateway
from src.storage.models import Competition, Match, SovereignDistribution
from src.core.sovereign_pipeline import (
    generar_distribucion_soberana,
    DELTA_EPISTEMICO_SIN_EVIDENCIA,
    ORIGEN_CAPTURA_EN_VIVO,
    ORIGEN_CAPTURA_HISTORICO,
)

logger = logging.getLogger("DistributionSync")


def _delta_epistemico_publicado(dist_out: Any, trace_dict: Dict[str, Any]) -> float:
    """
    [LN-QBE-104] Δ_epist(∞) persistido en `sovereign_distributions.epistemic_delta`.

    La columna deja de espejar el `ratio` λ_max/λ_min de `intensidades` (evidencia 3NF sellada
    [LN-QBE-102], que permanece intacta en la traza) y publica la discrepancia REAL entre el
    Generador A (Poisson paramétrico) y el Generador C (kernel H2H): max_k |P_A(k) − P_C(k)|.

    Orden de lectura: contrato de salida → traza forense → piso de ignorancia declarada R-1.
    El valor se acota a [0, 1] porque Δ(∞) vive en el símplex Δ²; un `None` heredado o un tipo
    no numérico JAMÁS se maquilla con 0.0 (se declara la ignorancia 0.02 del Contrato R-1).
    """
    for candidato in (
        getattr(dist_out, "epistemic_delta", None),
        trace_dict.get("epistemic_delta"),
    ):
        if isinstance(candidato, bool) or not isinstance(candidato, (int, float)):
            continue
        valor = float(candidato)
        if math.isfinite(valor):
            return min(1.0, max(0.0, valor))
    return DELTA_EPISTEMICO_SIN_EVIDENCIA


def _candado_blindado(origen_previo: str, origen_entrante: str) -> bool:
    """[LN-QBE-102] `LIVE_PROTECTION_LOCK`: veta únicamente la DEGRADACIÓN de procedencia.

    Relación estrictamente asimétrica: una reconstrucción histórica jamás sobreescribe evidencia
    capturada en ventanilla; en cambio `EN_VIVO -> EN_VIVO` (re-captura) y
    `HISTORICO_RECONSTRUIDO -> EN_VIVO` (ascenso de calidad de evidencia) sí escriben.
    """
    return (
        origen_previo == ORIGEN_CAPTURA_EN_VIVO
        and origen_entrante == ORIGEN_CAPTURA_HISTORICO
    )


def _actualizar_marcador_oficial(session, match_id: str, item: Dict[str, Any]) -> bool:
    """[LN-QBE-102] Excepción del Hecho Consumado bajo blindaje.

    La única mutación autorizada sobre una distribución blindada es la del resultado oficial en
    la tabla `matches` (`score_home`, `score_away`, `status = "FINISHED"`): el hecho consumado no
    altera la probabilidad calculada ni la evidencia capturada en ventanilla.
    """
    marcador_local = item.get("score_home")
    marcador_visita = item.get("score_away")
    if not isinstance(marcador_local, int) or isinstance(marcador_local, bool):
        return False
    if not isinstance(marcador_visita, int) or isinstance(marcador_visita, bool):
        return False
    partido = session.query(Match).filter(Match.id == match_id).first()
    if partido is None:
        return False
    partido.score_home = marcador_local
    partido.score_away = marcador_visita
    partido.status = "FINISHED"
    return True


def sincronizar_distribuciones_soberanas_partidos(
    partidos_datos: List[Dict[str, Any]],
    gateway: Optional[PersistenceGateway] = None,
    origen_captura: str = ORIGEN_CAPTURA_HISTORICO
) -> Dict[str, Any]:
    """
    [ARCH-1.6.11] Ejecuta la generación y persistencia transaccional atómica
    de distribuciones soberanas sobre la tabla 3NF 'sovereign_distributions'.

    [LN-QBE-102] `origen_captura` es el sello de procedencia de la evidencia. La Regla de Menor
    Privilegio sella el default en 'HISTORICO_RECONSTRUIDO': sólo un demonio de captura viva
    declara 'EN_VIVO' de forma explícita. Bajo `LIVE_PROTECTION_LOCK`, una reconstrucción
    histórica jamás sobreescribe una distribución capturada en ventanilla (ver `protegidos`).
    """
    gw = gateway or PersistenceGateway()
    procesados = 0
    exitosos = 0
    protegidos = 0
    errores = []

    for item in partidos_datos:
        match_id = item.get("match_id")
        comp_id = item.get("competition_id", "MEX_LIGAMX")

        if not match_id:
            continue

        procesados += 1

        try:
            # 1. Obtener parámetros macro de la competición desde la BD
            mu_liga = 2.65
            gamma_home = 0.15

            with gw.read_session() as session:
                comp = session.query(Competition).filter(Competition.id == comp_id).first()
                if comp:
                    mu_liga = float(comp.macro_mu_liga or 2.65)
                    gamma_home = float(comp.macro_gamma_home or 0.15)

            # 2. Generación matemática soberana con el pipeline del Tratado Vol. I
            dist_out = generar_distribucion_soberana(
                match_id=match_id,
                raw_match_data=item,
                mu_liga=mu_liga,
                gamma_home_base=gamma_home,
                delta_alt_metros=float(item.get("delta_alt_metros", 0.0) or 0.0),
                delta_descanso_dias=float(item.get("delta_descanso_dias", 0.0) or 0.0),
                q_mod_h=float(item.get("q_mod_h", 1.0) or 1.0),
                q_mod_a=float(item.get("q_mod_a", 1.0) or 1.0),
                origen_captura=origen_captura,
                # [LN-QBE-121] Bloque torneal de EXHIBICIÓN ya resuelto por slug (C5).
                cache_macro_stats=item.get("macro_stats") or None,
            )

            # 3. Persistencia atómica en la tabla 3NF 'sovereign_distributions'
            trace_dict = dist_out.audit_trace.model_dump()
            # [LN-QBE-104] Δ_epist(∞) REAL (Generador A vs Generador C); el `ratio` λ_max/λ_min deja
            # de transcribirse como discrepancia epistémica (sigue siendo evidencia 3NF en la traza).
            epist_delta = _delta_epistemico_publicado(dist_out, trace_dict)
            blindado = False

            with gw.write_transaction() as tx:
                dist_rec = tx.query(SovereignDistribution).filter(
                    SovereignDistribution.match_id == match_id
                ).first()

                if not dist_rec:
                    dist_rec = SovereignDistribution(
                        match_id=match_id,
                        model_version="v13.0-DIRGEN",
                        p_local=dist_out.p_local,
                        p_empate=dist_out.p_empate,
                        p_visitante=dist_out.p_visitante,
                        lambda_home=dist_out.lambda_home,
                        lambda_away=dist_out.lambda_away,
                        phi_lead2_home=dist_out.phi_lead2_home,
                        phi_lead2_away=dist_out.phi_lead2_away,
                        epistemic_delta=epist_delta,
                        audit_trace_json=trace_dict
                    )
                    tx.add(dist_rec)
                else:
                    # [LN-QBE-102] `LIVE_PROTECTION_LOCK`: se evalúa DENTRO de la transacción,
                    # leyendo el sello de la fila existente antes de asignar un solo atributo.
                    traza_previa = dist_rec.audit_trace_json if isinstance(dist_rec.audit_trace_json, dict) else {}
                    origen_previo = traza_previa.get("origen_captura") or ORIGEN_CAPTURA_HISTORICO
                    blindado = _candado_blindado(origen_previo, origen_captura)

                    if blindado:
                        # Excepción del Hecho Consumado: sólo el marcador oficial de `matches`.
                        _actualizar_marcador_oficial(tx, match_id, item)
                    else:
                        dist_rec.model_version = "v13.0-DIRGEN"
                        dist_rec.p_local = dist_out.p_local
                        dist_rec.p_empate = dist_out.p_empate
                        dist_rec.p_visitante = dist_out.p_visitante
                        dist_rec.lambda_home = dist_out.lambda_home
                        dist_rec.lambda_away = dist_out.lambda_away
                        dist_rec.phi_lead2_home = dist_out.phi_lead2_home
                        dist_rec.phi_lead2_away = dist_out.phi_lead2_away
                        dist_rec.epistemic_delta = epist_delta
                        dist_rec.audit_trace_json = trace_dict

            if blindado:
                protegidos += 1
                logger.warning(
                    f"🔒 [LIVE_PROTECTION_LOCK] Evidencia EN_VIVO preservada para {match_id}: "
                    f"la reconstrucción histórica NO sobreescribió la distribución capturada."
                )
            else:
                exitosos += 1
                logger.info(f"✅ [SOVEREIGN PERSISTED] Distribución guardada en SQLite para {match_id}: ({dist_out.p_local:.4f}, {dist_out.p_empate:.4f}, {dist_out.p_visitante:.4f})")

        except Exception as ex:
            logger.error(f"❌ Error sincronizando distribución para {match_id}: {ex}")
            errores.append({"match_id": match_id, "error": str(ex)})

    return {
        "procesados": procesados,
        "exitosos": exitosos,
        "protegidos": protegidos,
        "errores": errores
    }
