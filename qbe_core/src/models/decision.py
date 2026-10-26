# Q-BE Casino Deportes — Decision Models (src/models/decision.py)
"""
Contratos Pydantic V2 para Órdenes de Ejecución y Gestión de Cartera.
[LN-QBE-070] [ARCH-PILLAR]
"""

from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class StrategySelection(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")
    codigo: str
    nombre_oficial: str
    descripcion_ejecutiva: str
    linea_promocional: str


class KeyMetrics(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")
    score_calidad_S_i: float
    peso_portafolio_w_i: float
    phi_lead2_prob_ventaja_2_goles: float
    psi_downside_riesgo: float
    ev_neto_roi_porcentaje: float


class TicketOrder(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")
    seleccion: str
    momio: float = Field(ge=0.0)  # Permite 0.0 en boletos sin seguro (D1)
    monto_mxn: float = Field(ge=0.0)
    # [ARCH-1.5.10 / DES-QBE-053] Casa patrocinadora que publica el momio de ESTA pierna.
    # En modalidad MEJOR_COMBINACION cada boleto puede viajar en un operador distinto;
    # el campo es opcional para no romper el contrato de la modalidad mono-operador.
    operador: Optional[str] = None
    # [DES-QBE-060] Probabilidad fiduciaria contraída P' (%) asociada al desenlace que
    # transporta ESTA pierna. Variable DERIVADA downstream, hidratada por el motor de
    # cartera desde la distribución contraída ([ARCH-1.4.17]); el frontend se limita a
    # exhibirla ([GOVERNANCE-01] paridad fáctica backend↔pantalla). Opcional para no
    # romper payloads históricos.
    prob_qbe: Optional[float] = Field(
        default=None,
        description="Probabilidad fiduciaria contraída P' (%) asociada al desenlace"
    )


class MatchTickets(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")
    inversion_partido_A_i: float = Field(ge=0.0)
    boleto_1_seguro: TicketOrder
    boleto_2_ganancia: TicketOrder


class Projections(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")
    ganancia_neta_principal_mxn: float
    roi_principal_porcentaje: float
    freeroll_doble_ganancia_mxn: float = 0.0
    freeroll_roi_porcentaje: float = 0.0
    resultado_tablas_mxn: float
    perdida_maxima_posible_mxn: float


class CashoutTargets(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")
    monto_salida_emergencia_tablas_mxn: float
    monto_salida_optima_min85: str
    instruccion_emergencia_rompequinielas: str
    instruccion_desarrollo_normal: str


class MatchExecutionOrder(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")
    id_partido: str
    partido: str
    horario_evento: str
    estrategia_seleccionada: StrategySelection
    metricas_clave: KeyMetrics
    forma_reciente_auditada: Dict[str, Any]
    boletos: MatchTickets
    proyecciones: Projections
    cashout_targets: CashoutTargets
    # [DES-QBE-060] Bloque de Transparencia 360°: métricas del desenlace rival DESCARTADO
    # (el que la estrategia no juega). Hidratado por el motor con la terna contraída
    # canónica; el frontend exhibe nombre, momio y P' sin recalcular nada.
    opcion_no_jugada: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Métricas del desenlace rival descartado (nombre, momio, prob_qbe)"
    )
    # [LN-QBE-077-B] / [ARCH-1.4.37] Invariante VIII-54: trazabilidad contractual del parámetro δ
    # de Cobertura Dinámica y de los ROIs proyectados (favorito / empate). Bloque DERIVADO de sólo
    # lectura hidratado por el motor de cartera (`[ARCH-1.4.37]`); el frontend lo EXHIBE sin
    # recalcular nada ([GOVERNANCE-01] paridad fáctica backend↔pantalla). `None` en las familias
    # sin seguro de empate (D1/D2/C1/QBE-00) y en toda orden cuya modalidad sellada sea `DEF`.
    cobertura_dinamica: Optional[Dict[str, Any]] = Field(
        default=None,
        description="δ de cobertura dinámica y ROIs proyectados (favorito / empate)"
    )


class SatelliteModule(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")
    autorizado: bool = False
    partido_seleccionado: str = "N/A"
    seleccion: str = "N/A"
    momio: float = 0.0
    monto_satelite_mxn: float = 0.0
    promocion: str = "Pago Anticipado"
    ganancia_potencial_neta_mxn: float = 0.0
    roi_potencial_porcentaje: float = 0.0
    justificacion_financiamiento: str


class PortfolioControl(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")
    modalidad: Literal["BANKROLL", "VAQUITA"]
    total_partidos_core_aprobados: int
    # [ARCH-1.4.14] Denominador fáctico de cartelera: partidos que componen la fecha en
    # `FixtureSnapshot.matches_json` (ej. 9 en Liga MX). Garantiza que el frontend exhiba
    # con veracidad K / 9 y nunca K / K. Viaja junto al numerador core aprobado.
    total_partidos_jornada: int = Field(
        default=9,
        ge=0,
        description="Total de partidos que componen la fecha oficial"
    )
    total_partidos_escaneados: int = Field(
        default=9,
        ge=0,
        description="[ARCH-1.4.14] Partidos escaneados de la jornada (denominador fáctico KPI)"
    )
    capital_total_core_mxn: float
    probabilidad_ruina_total_porcentaje: float
    blindaje_global_preservacion_porcentaje: float
    desglose_vaquita: Dict[str, Any]
    desglose_bankroll: Dict[str, Any]


class PortfolioBalance(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")
    capital_total_comprometido_mxn: float
    ganancia_neta_esperada_jornada_mxn: float
    roi_global_esperado_porcentaje: float


class PortfolioExecutionPlan(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")
    control_portafolio: PortfolioControl
    ordenes_ejecucion_partidos: List[MatchExecutionOrder]
    modulo_satelite_asimetrico: SatelliteModule
    balance_global_portafolio: PortfolioBalance