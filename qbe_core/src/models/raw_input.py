# Q-BE Casino Deportes — Raw Input Models (src/models/raw_input.py)
"""
[LN-QBE-010] [LN-QBE-020] Esquemas Pydantic V2 de Ingesta Cruda y Tabla Maestra.
[ARCH-PILLAR] Validación tipada estricta para el perímetro de ingesta neuro-simbólica y FotMob Opta.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class TrazabilidadConsenso(BaseModel):
    model_config = ConfigDict(extra="ignore")
    # [LN-QBE-093 · Enmienda Nudo 1] Cero confianza fabricada: una ausencia de medición viaja
    # como `None`. Declarar 100.0 por defecto desactivaba la aduana de `[LN-QBE-010]`.
    confiabilidad_porcentaje: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    estado_extraccion: Optional[str] = Field(default=None)


class IdentidadPartido(BaseModel):
    model_config = ConfigDict(extra="ignore")
    favorito: Optional[str] = None
    underdog: Optional[str] = None
    local: Optional[str] = None
    visitante: Optional[str] = None
    id_partido: Optional[str] = "M_DEFAULT"
    fecha_partido_evaluado: Optional[str] = "Fin de Semana"
    liga_torneo: Optional[str] = None
    jornada_en_disputa: Optional[int] = None
    fase_torneo: Optional[str] = None


class ContextoEquipoTabla(BaseModel):
    model_config = ConfigDict(extra="ignore")
    posicion_tabla: Optional[int] = 1
    puntos: Optional[int] = 0
    pts_por_partido: Optional[float] = 1.35
    gf_torneo: Optional[int] = 0
    gc_torneo: Optional[int] = 0
    pj_torneo: Optional[int] = 0


class ContextoTablaPosiciones(BaseModel):
    model_config = ConfigDict(extra="ignore")
    favorito: Optional[ContextoEquipoTabla] = Field(default_factory=ContextoEquipoTabla)
    underdog: Optional[ContextoEquipoTabla] = Field(default_factory=ContextoEquipoTabla)
    local: Optional[ContextoEquipoTabla] = None
    visitante: Optional[ContextoEquipoTabla] = None
    jornada_actual_torneo: int = Field(default=5, ge=1)


class Promedios10P(BaseModel):
    model_config = ConfigDict(extra="ignore")
    promedio_poss: float = Field(default=50.0, ge=0.0, le=100.0)
    promedio_sot: float = Field(default=4.0, ge=0.0)
    promedio_sota: float = Field(default=4.0, ge=0.0)
    promedio_gf: float = Field(default=1.2, ge=0.0)
    promedio_gc: float = Field(default=1.0, ge=0.0)
    xg_promedio: Optional[float] = None
    xga_promedio: Optional[float] = None
    gf: Optional[int] = None
    gc: Optional[int] = None
    sot: Optional[float] = None
    sota: Optional[float] = None
    poss_pct: Optional[float] = None



class MetricasResumenDatos(BaseModel):
    model_config = ConfigDict(extra="ignore")
    fav_10p: Promedios10P = Field(default_factory=Promedios10P)
    und_10p: Promedios10P = Field(default_factory=Promedios10P)


class RadarEquipo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    q_mod_calculado: float = Field(default=1.0, ge=0.0, le=2.0)
    descripcion_impacto_bajas: Optional[str] = "Sin reporte crítico"


class RadarCualitativoEntorno(BaseModel):
    model_config = ConfigDict(extra="ignore")
    favorito: RadarEquipo = Field(default_factory=RadarEquipo)
    underdog: RadarEquipo = Field(default_factory=RadarEquipo)


class CuotasPagoAnticipado(BaseModel):
    model_config = ConfigDict(extra="ignore")
    # [GOVERNANCE-01 · Enmienda Nudo 1] Cero mercado sintético: la ausencia de precio viaja
    # como `None`. Queda prohibido que el DTO invente una terna 2.00/3.20/3.50.
    L: Optional[float] = Field(default=None, gt=1.0)
    E: Optional[float] = Field(default=None, gt=1.0)
    V: Optional[float] = Field(default=None, gt=1.0)
    disponible: Optional[bool] = Field(default=None)


class MomiosSnapshot(BaseModel):
    model_config = ConfigDict(extra="ignore")
    estandar: Optional[CuotasPagoAnticipado] = None
    # [GOVERNANCE-01 · Enmienda Nudo 1] Sin captura de Pago Anticipado no hay objeto de mercado.
    pago_anticipado: Optional[CuotasPagoAnticipado] = Field(default=None)



class H2HMatchRaw(BaseModel):
    model_config = ConfigDict(extra="ignore")
    num: Optional[int] = None
    fecha: str
    dias_transcurridos: float = Field(..., ge=0.0)
    local_real: str
    visitante_real: str
    marcador: str
    resultado_qbe: Optional[str] = None


class RawMatchInput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    trazabilidad_consenso: Optional[TrazabilidadConsenso] = Field(default_factory=TrazabilidadConsenso)
    identidad_partido: Optional[IdentidadPartido] = Field(default_factory=IdentidadPartido)
    contexto_tabla_posiciones: Optional[ContextoTablaPosiciones] = Field(default_factory=ContextoTablaPosiciones)
    metricas_resumen_datos: Optional[MetricasResumenDatos] = Field(default_factory=MetricasResumenDatos)
    radar_cualitativo_entorno: Optional[RadarCualitativoEntorno] = Field(default_factory=RadarCualitativoEntorno)
    momios: Optional[MomiosSnapshot] = Field(default_factory=MomiosSnapshot)
    h2h_matches: Optional[List[H2HMatchRaw]] = None
    h2h_ultimos_5_misma_liga: Optional[List[H2HMatchRaw]] = None
    raw_data: Optional[Dict[str, Any]] = None

    def model_post_init(self, __context: Any) -> None:
        if self.h2h_matches is None and self.h2h_ultimos_5_misma_liga is not None:
            object.__setattr__(self, "h2h_matches", self.h2h_ultimos_5_misma_liga)
        elif self.h2h_ultimos_5_misma_liga is None and self.h2h_matches is not None:
            object.__setattr__(self, "h2h_ultimos_5_misma_liga", self.h2h_matches)


class MasterTablePosition(BaseModel):
    model_config = ConfigDict(extra="ignore")
    pos: int = Field(ge=1, le=24)
    equipo: str
    puntos: int = Field(ge=0)
    pj: int = Field(ge=0)
    gf: int = Field(ge=0)
    gc: int = Field(ge=0)
    dif: int
    pts_por_partido: float = Field(ge=0.0)
    xg: Optional[float] = None
    xga: Optional[float] = None


class MasterTableSnapshot(BaseModel):
    model_config = ConfigDict(extra="ignore")
    jornada_concluida: Optional[int] = None
    torneo: Optional[str] = "Liga MX - Torneo Apertura 2026"
    posiciones: List[MasterTablePosition] = Field(default_factory=list)


# Aliases de compatibilidad [ARCH-PILLAR]
MatchIdentity = IdentidadPartido
ContextoFavorito = ContextoEquipoTabla
ContextoUnderdog = ContextoEquipoTabla
Odds1X2WithPA = CuotasPagoAnticipado
OddsContainer = MomiosSnapshot
Form10PRaw = Promedios10P
EvaluacionCualitativaClub = RadarEquipo