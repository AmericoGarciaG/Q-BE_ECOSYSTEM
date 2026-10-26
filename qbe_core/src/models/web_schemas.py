# Q-BE Casino Deportes — Web Schemas (src/models/web_schemas.py)
"""
[ARCH-PILLAR] Contratos Pydantic V2 para la Capa Web y Endpoints REST de FastAPI.
Gobierna los esquemas de entrada y salida del cliente SPA reactivo.
"""

from typing import List, Optional, Dict, Any, Literal, Union
from pydantic import BaseModel, Field, ConfigDict


class LeagueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    id: int
    name: str
    country: str
    flag: str
    fotmob_id: int
    is_active: bool


class StandingRowOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    pos: int
    equipo: str
    escudo_url: Optional[str] = None
    pj: int
    pg: int
    pe: int
    pp: int
    gf: int
    gc: int
    dif: int
    puntos: int
    forma: List[str] = Field(default_factory=list)  # ["G", "E", "P", ...]
    xg: Optional[float] = None
    xga: Optional[float] = None
    xpts: Optional[float] = None
    proximo_rival: Optional[str] = None
    proximo_escudo_url: Optional[str] = None  # <-- [DES-QBE-016-B] Campo obligatorio agregado


class Odds1X2(BaseModel):
    model_config = ConfigDict(extra="ignore")
    L: float = Field(gt=1.0)
    E: float = Field(gt=1.0)
    V: float = Field(gt=1.0)
    pago_anticipado: bool = True


class MatchFixtureOut(BaseModel):
    """
    [ARCH-1.6.3] Contrato canónico de fixture con Máquina de Estados semántica.
    Campos obligatorios para el ciclo de vida completo del partido en el Live Board.
    """
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    id_partido: str
    local: str
    visitante: str
    local_escudo_url: Optional[str] = None
    visitante_escudo_url: Optional[str] = None
    horario: str
    fecha_dt: Optional[str] = None              # ISO 8601: "YYYY-MM-DDTHH:MM:SS"
    fecha_bloque: Optional[str] = None          # Etiqueta de agrupación (retrocompat.)
    momios: Optional[Union[Odds1X2, Dict[str, Any]]] = None
    es_viable_triaje: bool = True
    motivo_triaje: Optional[str] = None
    sub_badge: Optional[str] = None

    # [ARCH-1.6.3] Máquina de Estados del Fixture
    estado: Literal["PROGRAMADO", "EN_CURSO", "FINALIZADO", "REPROGRAMADO"] = "PROGRAMADO"
    marcador_actual: Optional[str] = None       # Ej. "0 - 2", "1 - 1" (solo FINALIZADO/EN_CURSO)
    minuto_juego: Optional[str] = None          # Ej. "75'", "Medio Tiempo", "Final"
    es_hoy: bool = False                        # True si fecha_dt.date() == datetime.now().date()
    disponible_para_seleccion: bool = True      # False si FINALIZADO o REPROGRAMADO [BIZ-LOGIC]
    es_operable: bool = True
    es_pospuesto: bool = False

    # ── [CAMPOS SOBERANOS TRATADO VOL. I - ENMIENDA SOBERANA ARCH-1.4.5-B] ──
    p_local: Optional[float] = Field(default=None, description="Probabilidad soberana victoria local")
    p_empate: Optional[float] = Field(default=None, description="Probabilidad soberana empate")
    p_visitante: Optional[float] = Field(default=None, description="Probabilidad soberana victoria visitante")
    lambda_home: Optional[float] = Field(default=None, description="Intensidad de gol esperada local")
    lambda_away: Optional[float] = Field(default=None, description="Intensidad de gol esperada visitante")
    phi_lead2_home: Optional[float] = Field(default=None, description="Probabilidad de ventaja >=2 goles local (André)")
    phi_lead2_away: Optional[float] = Field(default=None, description="Probabilidad de ventaja >=2 goles visitante (André)")

    # ── [BENCHMARK DE MERCADO - DES-QBE-039 & ARCH-1.4.8] ──
    consenso_mercado: Optional["MarketConsensusOut"] = None
    momios_operadores: Optional[Dict[str, Any]] = None


class MarketConsensusOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    p_L_mercado: float = 0.0
    p_E_mercado: float = 0.0
    p_V_mercado: float = 0.0
    delta_L: float = 0.0
    delta_E: float = 0.0
    delta_V: float = 0.0



class LiveBoardOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    league_id: int
    league_name: str
    jornada: str
    fechas: str
    standings: List[StandingRowOut]
    fixtures: List[MatchFixtureOut]
    # Nuevos campos legislados Fase 4: [ARCH-1.6.8]
    jornada_actual: int = Field(default=8, description="Jornada administrativa de la liga")
    jornada_mostrada: int = Field(default=8, description="Jornada desplegada actualmente en cartelera")
    jornadas_disponibles: List[int] = Field(default_factory=lambda: [8, 9], description="Jornadas seleccionables")



# Alias para retrocompatibilidad total
LiveBoardResponse = LiveBoardOut


class GeneratePortfolioRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    league_id: int = Field(default=262)
    selected_match_ids: List[str] = Field(default_factory=list)
    bankroll: float = Field(default=200.0, ge=10.0)
    mode: str = Field(default="BANKROLL", pattern="^(BANKROLL|VAQUITA)$")
    # [ARCH-1.4.30] Parámetro interactivo de concentración de masa Γ (Capa 0).
    gamma_slider: Optional[float] = Field(0.67, ge=0.67, le=0.75, description="Umbral de concentración de masa Capa 0")
    # [ARCH-1.4.37] Parámetro de Cobertura Dinámica δ (Dutching con Rendimiento, [LN-QBE-077-B]).
    # `DEF` = indemnidad pura V=0 (contrato sellado) | `BAL` = 50% de δ* | `AGR` = δ* |
    # `CUSTOM` = δ explícito resuelto por la ley pura `calcular_particion_dutching_dinamico()`.
    modo_cobertura: Optional[str] = Field(
        "DEF", description="DEF (V=0), BAL (50% delta*), AGR (delta*)"
    )


class IngestionExtractRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    url: Optional[str] = None
    imagen_path: Optional[str] = None


# ── [ARCH-1.4.42 / LN-QBE-101] DTO DE INSPECCIÓN DE ATRIBUCIÓN FACTORIAL ──────
class AtribucionSemaforosOut(BaseModel):
    """[LN-QBE-101].P.3 — Las cinco luces de salud fáctica de los insumos."""

    model_config = ConfigDict(extra="ignore")
    opta: str = "NEUTRO"
    sede: str = "NEUTRO"
    h2h: str = "NEUTRO"
    epist: str = "NEUTRO"
    ctx: str = "NEUTRO"


class AtribucionDriverOut(BaseModel):
    """[LN-QBE-101].P.2 — `Driver* = argmax |Δ_k|` con desempate canónico."""

    model_config = ConfigDict(extra="ignore")
    dimension: str = "NEUTRO"
    magnitud: float = 0.0
    favorece: str = "NEUTRO"
    etiqueta: str = ""
    valor_firmado: float = 0.0


class AtribucionDescomposicionOut(BaseModel):
    """[LN-QBE-101].P.1 — Descomposición aditiva exacta de `Δη = ln(λ_H/λ_A)`."""

    model_config = ConfigDict(extra="ignore")
    delta_ofensiva: Optional[float] = None
    delta_defensiva: Optional[float] = None
    delta_contexto: Optional[float] = None
    delta_neto_total: Optional[float] = None
    delta_ofensiva_cruda: Optional[float] = None
    delta_defensiva_cruda: Optional[float] = None
    delta_ln_lambda: Optional[float] = None
    residuo_no_atribuido: Optional[float] = None


class AtribucionVariableOut(BaseModel):
    """[LN-QBE-101].P.4 — Renglón forense del catálogo (evidencia ausente ⇒ `None`).

    [ARCH-1.4.42-B] La celda puede portar unidad (`'+0.0 d'`, `'2660m'`, `'0 partidos'`, `'54.2%'`)
    o magnitud pura. `str` precede a `float` en el `Union`: Pydantic V2 preserva el tipo exacto y
    ninguna cadena con unidad se fuerza a flotante (erradica el `ResponseValidationError` → HTTP 500).
    """

    model_config = ConfigDict(extra="ignore")
    id: str
    variable: str
    local: Optional[Union[str, float]] = Field(
        default=None, description="Valor formateado con unidad (ej. '53.5%', '+0.0 d') o float puro"
    )
    visita: Optional[Union[str, float]] = Field(
        default=None, description="Valor formateado con unidad o float puro"
    )
    z_score: Optional[Union[str, float]] = Field(
        default=None, description="Z-score formateado o float puro"
    )
    origen: str = "SIN EVIDENCIA"
    estado: str = "SIN EVIDENCIA"
    impacto: str = ""
    nota: str = ""


class AtribucionDimensionOut(BaseModel):
    """[LN-QBE-101].P.4 — Dimensión canónica del catálogo (𝒯_Vol … 𝒯_Cls)."""

    model_config = ConfigDict(extra="ignore")
    dimension: str
    titulo: str = ""
    conteo: int = 0
    # [ARCH-1.4.58] Telemetría dimensional del acordeón bicolor. El productor puro
    # (`estructurar_catalogo_44_variables`, [DES-QBE-066]) YA publicaba estos tres contadores, pero
    # `extra="ignore"` los descartaba en silencio y el Visor degradaba a `SIN EVALUAR` / `○ 0 de 0`.
    # Campos ADITIVOS con default: el contrato [LN-QBE-101] no sufre ruptura alguna.
    total_variables: int = 0
    variables_evaluadas: int = 0
    tiene_datos: bool = False
    variables: List[AtribucionVariableOut] = Field(default_factory=list)


class Catalogo44Out(BaseModel):
    """[LN-QBE-120].P.4 — Partición vigente: 6 dimensiones × 32 variables PRE-KICKOFF.

    Deroga la cardinalidad 12×44 de `[LN-QBE-101]` (VAR-3) sin alterar el nombre del DTO ni la
    forma de sus campos: los consumidores siguen recibiendo `dimensiones` planas.
    """

    model_config = ConfigDict(extra="ignore")
    total_variables: int = 32
    dimensiones: List[AtribucionDimensionOut] = Field(default_factory=list)


class AtribucionFactorialOut(BaseModel):
    """[ARCH-1.4.42] Bloque completo de auditoría factorial de un partido."""

    model_config = ConfigDict(extra="ignore")
    disponible: bool = False
    origen_factores: str = "sin_traza"
    # [LN-QBE-102] Sello de procedencia de la evidencia: "EN_VIVO" | "HISTORICO_RECONSTRUIDO".
    # `None` ⇒ traza legada sin sello (la ausencia no se interpreta como captura histórica).
    origen_captura: Optional[str] = None
    descomposicion_log: AtribucionDescomposicionOut = Field(default_factory=AtribucionDescomposicionOut)
    driver_principal: AtribucionDriverOut = Field(default_factory=AtribucionDriverOut)
    semaforos: AtribucionSemaforosOut = Field(default_factory=AtribucionSemaforosOut)
    variables_44: Catalogo44Out = Field(default_factory=Catalogo44Out)


# ── [ARCH-1.4.38 / LN-QBE-100] VISOR DE BACKTESTING (CALIBRACIÓN FACTUAL) ─────
class CalibrationMatchOut(BaseModel):
    """
    [LN-QBE-100] Casilla micro estilo BetExplorer: P' fiduciaria vs consenso de mercado (q_mkt),
    resultado real consumado y error de Brier de ambas predicciones.
    """
    model_config = ConfigDict(extra="ignore")
    id_partido: str
    jornada: int
    local: str
    visitante: str
    local_escudo_url: Optional[str] = None
    visitante_escudo_url: Optional[str] = None
    marcador: str
    goles_local: int
    goles_visitante: int
    resultado_real: Literal["LOCAL", "EMPATE", "VISITANTE"]
    favorito_designado: Literal["LOCAL", "VISITANTE"]
    tipo_resultado: Literal["FAVORITO", "EMPATE", "UNDERDOG"]
    p_local: float
    p_empate: float
    p_visitante: float
    q_local: float
    q_empate: float
    q_visitante: float
    momios: Dict[str, float] = Field(default_factory=dict)
    brier_qbe: float
    brier_mercado: float
    acierto: bool
    # [LN-QBE-125 · derogación de la sustitución de [LN-QBE-100]] Sello de suficiencia fáctica
    # S(I) del partido: 0 = ignorancia declarada ⇒ P′ se evalúa TAL CUAL fue publicada (Cold Start
    # sincero) y la ceguera se declara en la vitrina (`❄️ Cold Start (S=0)`); jamás se sustituye
    # por q_mkt.
    suficiencia_S_I: Optional[int] = None
    # [LN-QBE-102] Sello de procedencia de la evidencia que sostiene P′: "EN_VIVO" (captura en
    # ventanilla, blindada por el candado) | "HISTORICO_RECONSTRUIDO" (reconstrucción posterior).
    origen_captura: Optional[str] = None
    # [LN-QBE-127] Sello de procedencia del VECTOR P′ servido: "CAPTURA" (snapshot congelado) |
    # "SOBERANA" (tabla 3NF) | "AL_VUELO" (resuelto dinámicamente por el motor soberano porque el
    # partido concluido no portaba distribución sellada). `None` en payloads legados.
    origen_p_prima: Optional[str] = None
    # [ARCH-1.4.38 · REFACTOR-TRIADA-PMAX-PMID-PLOW] Vértices del símplex Δ² ordenados por
    # probabilidad fiduciaria descendente (P_max ≥ P_mid ≥ P_low) y vértice consumado en cancha.
    r_max: Optional[Literal["LOCAL", "EMPATE", "VISITANTE"]] = None
    r_mid: Optional[Literal["LOCAL", "EMPATE", "VISITANTE"]] = None
    r_low: Optional[Literal["LOCAL", "EMPATE", "VISITANTE"]] = None
    clasificacion_triada: Optional[Literal["P_MAX", "P_MID", "P_LOW"]] = None
    masa_cobertura_pct: Optional[float] = None
    p_low_ruptura_pct: Optional[float] = None
    # [LN-QBE-124 / ARCH-1.4.64] Desnivel REALMENTE consumido por λ (traza V29 → catálogo → 0.0)
    # y bandera del rescate territorial que promovió al LOCAL a P_mid.
    delta_alt_metros: Optional[float] = None
    rescate_indiferencia: bool = False
    # [ARCH-1.4.42] Micro-HUD de atribución factorial + DTO de inspección de 44 variables.
    atribucion_factorial: Optional[AtribucionFactorialOut] = None


class CalibrationJornadaOut(BaseModel):
    """[LN-QBE-100] Fila meso: calibración agregada de una jornada concluida."""
    model_config = ConfigDict(extra="ignore")
    jornada: int
    total_partidos: int
    aciertos_cobertura: int
    tasa_cobertura_pct: float
    desglose: Dict[str, int] = Field(default_factory=dict)
    # [ARCH-1.4.38 · REFACTOR-TRIADA-PMAX-PMID-PLOW] Desglose cuantitativo puro de la jornada:
    # masa de cobertura (% P_max + % P_mid), porcentaje por vértice y conteos enteros, incluida la
    # procedencia del rescate secundario (empate vs rival).
    masa_cobertura_pct: float = 0.0
    pct_p_max: float = 0.0
    pct_p_mid: float = 0.0
    pct_p_low: float = 0.0
    n_p_max: int = 0
    n_p_mid: int = 0
    n_p_low: int = 0
    n_p_mid_empate: int = 0
    n_p_mid_rival: int = 0
    brier_score_qbe: float
    brier_score_mercado: float
    alpha_calibracion_pct: float
    # [LN-QBE-125 / ARCH-1.4.65] Ceguera declarada de la jornada (todos sus partidos con S(I)=0) y
    # etiqueta del Alpha servido: "COLD_START" (no es una medición) vs "MEDIDO".
    es_cold_start: bool = False
    alpha_etiqueta: Optional[str] = None
    partidos: List[CalibrationMatchOut] = Field(default_factory=list)


class CalibrationSummaryOut(BaseModel):
    """[LN-QBE-100] Bloque macro de temporada (H_fid, Brier de Q-BE vs mercado y Alpha)."""
    model_config = ConfigDict(extra="ignore")
    total_partidos: int
    partidos_favorito: int
    partidos_empate: int
    partidos_underdog: int
    tasa_coincidencia_fiduciaria_pct: float
    # [ARCH-1.4.38 · REFACTOR-TRIADA-PMAX-PMID-PLOW] Taxonomía macro de vértices del símplex Δ²:
    # masa de cobertura (P_max + P_mid ≡ 100% − P_low), tasas puras por vértice y conteos enteros
    # con el desglose de la procedencia del rescate secundario (empate vs rival).
    masa_cobertura_pct: float = 0.0
    p_max_aciertos_pct: float = 0.0
    p_mid_rescate_pct: float = 0.0
    p_mid_empate_pct: float = 0.0
    p_mid_rival_pct: float = 0.0
    p_low_ruptura_pct: float = 0.0
    total_p_max: int = 0
    total_p_mid: int = 0
    total_p_low: int = 0
    total_p_mid_empate: int = 0
    total_p_mid_rival: int = 0
    brier_score_qbe: float
    brier_score_mercado: float
    alpha_calibracion_pct: float
    partidos_pendientes_captura: int = 0
    # [LN-QBE-127] Partidos concluidos cuyo P′ se resolvió AL VUELO (sin distribución sellada).
    # Declarado y contado: la ceguera de captura se mide, jamás se esconde. En `resumen_calibrado`
    # vale 0 por construcción (una resolución al vuelo nunca declara suficiencia).
    partidos_resueltos_al_vuelo: int = 0
    jornadas_auditadas: List[int] = Field(default_factory=list)


class CalibrationReportResponse(BaseModel):
    """
    [ARCH-1.4.38] Contrato REST del Visor de Backtesting (solo lectura):
    resumen macro de temporada + tabla meso por jornada con parrilla micro embebida.

    [LN-QBE-125 · ARCH-1.4.65] Doble agregado declarado: `resumen_calibrado` (universo informado,
    S(I)=1) y `resumen_global` (temporada completa). `resumen_temporada` subsiste como alias
    byte-idéntico del global porque tres consumidores sellados lo leen.
    """
    model_config = ConfigDict(extra="ignore")
    resumen_temporada: CalibrationSummaryOut
    jornadas: List[CalibrationJornadaOut] = Field(default_factory=list)
    resumen_calibrado: Optional[CalibrationSummaryOut] = None
    resumen_global: Optional[CalibrationSummaryOut] = None


class SimulatePortfolioRequest(BaseModel):
    """
    [LN-QBE-114 / DES-QBE-068] Payload de la pasarela REST de simulación retrospectiva.

    Transporta EXCLUSIVAMENTE los parámetros del motor `[LN-QBE-107]`; la capa web no
    interpreta ni recalcula PnL, ROI ni drawdown. `excluir_estrategias` alimenta el veto
    fiduciario selectivo de `[LN-QBE-113]` (la normalización canónica vive en el sandbox).
    """
    model_config = ConfigDict(extra="ignore")
    bankroll_inicial: float = Field(default=10000.0, gt=0.0)
    rango_jornadas: Optional[str] = "1-11"
    modo_interes: Literal["compuesto", "plano"] = "compuesto"
    excluir_estrategias: Optional[List[str]] = None
    # ── [ARCH-1.4.53 / LN-QBE-115] Parámetros gobernantes del Saneamiento Vol. II ─────────────
    # Γ de Capa 0 (dominio legislado [0.67, 0.75]), Slider de Certeza §5.10 en PORCENTAJE
    # (0.0 = identidad neutra / Modo Crecimiento) y modo de cobertura δ (DEF = V=0, BAL = 50% de
    # δ*, AGR = δ*). La capa web sólo los transporta: el dominio se valida en el motor.
    gamma_slider: float = Field(default=0.67, ge=0.67, le=0.75)
    target_certeza_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    modo_cobertura: Literal["DEF", "BAL", "AGR"] = "DEF"


class TicketRegistrationRequest(BaseModel):
    """[ARCH-1.4.32 / P3-9] Boleto a sellar en el ledger 3NF."""
    match_id: str = Field(..., min_length=1, max_length=100)
    desenlace: str = Field(..., min_length=1, max_length=120)
    cuota_congelada: float = Field(..., gt=1.0)
    monto: float = Field(..., gt=0.0)


class TicketRegistrationResponse(BaseModel):
    """[ARCH-1.4.32 / P3-9] Confirmación del sellado y agregado para el badge."""
    status: str
    ticket_id: int
    boletos_comprados: int
    monto_comprometido_mxn: float


class TicketLedgerStatusResponse(BaseModel):
    """[ARCH-1.4.32 / P3-9] Estado agregado del ledger para hidratar la SPA."""
    boletos_comprados: int
    monto_comprometido_mxn: float
    match_ids: List[str] = Field(default_factory=list)

