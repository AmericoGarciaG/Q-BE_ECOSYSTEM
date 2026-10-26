# Q-BE Casino Deportes — DTOs de la Capa 1: Ingesta Pura (src/ingestion/schemas.py)
"""
[ARCH-1.4.24] [LN-QBE-093] Contratos canónicos de transporte (Data Transfer Objects, Pydantic V2)
para los sensores de ingesta pura del Data Nexus.

Declaraciones puras: cero lógica de negocio, cero acceso a persistencia, cero estado.
Ningún módulo de `src/ingestion/providers/` importa este archivo para consultar SQLite:
los DTOs son el ÚNICO vehículo de salida de un sensor de red.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ScheduledMatchDTO(BaseModel):
    """[ARCH-1.4.24] Partido programado emitido por un sensor de calendario."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    match_id: str
    home_team: str
    away_team: str
    kickoff_utc: datetime
    tournament_id: Optional[int] = None


class SeasonTeamAccumulatedDTO(BaseModel):
    """[ARCH-1.4.24] Acumulados fácticos por club dentro de la vista de temporada."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    team_name: str
    pj: int
    pts: int
    gf: int
    gc: int
    xg: float
    xga: float


class SeasonOverviewDTO(BaseModel):
    """
    [ARCH-1.4.24] Vista de temporada: lista de equipos con sus acumulados.
    Accesor canónico de la colección: `teams`.
    """

    model_config = ConfigDict(extra="ignore", frozen=True)

    teams: List[SeasonTeamAccumulatedDTO] = Field(default_factory=list)


class ProgolContestDTO(BaseModel):
    """[ARCH-1.4.24] Concurso de Progol emitido por el sensor de quinielas."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    contest_id: str
    bolsa_estimada: float
    cierre_utc: Optional[datetime] = None
    items: List[Dict[str, Any]] = Field(default_factory=list)


class Odds1X2DTO(BaseModel):
    """[ARCH-1.4.24] Captura fáctica de cuotas 1X2 de un operador de mercado."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    L: float
    E: float
    V: float
    pago_anticipado: bool
    bookmaker: str


class DisambiguatedMatchDTO(BaseModel):
    """
    [LN-QBE-094] Salida canónica de la desambiguación temporal en Ventana Crítica:
    resolución unívoca de partido y competición cuando un mismo par de clubes se enfrenta
    en múltiples torneos en fechas cercanas (`docs/LOGIC.md`, nodo [LN-QBE-094].O).
    """

    model_config = ConfigDict(extra="ignore", frozen=True)

    match_id: str
    competition_id: Optional[int] = None
    kickoff_utc: Optional[datetime] = None
    is_ambiguous: bool = False


class CategorizedEntityDTO(BaseModel):
    """
    [LN-QBE-095] Identidad canónica categorizada de una entidad deportiva (club, filial,
    rama femenil o formativa). El `canonical_slug` conserva SIEMPRE el sufijo de categoría
    (`club-america-femenil`, `real-sociedad-b`, `chivas-sub20`) para impedir colisiones con
    el primer equipo varonil (`docs/LOGIC.md`, nodo [LN-QBE-095].O).
    """

    model_config = ConfigDict(extra="ignore", frozen=True)

    canonical_name: str
    canonical_slug: str
    category: str

