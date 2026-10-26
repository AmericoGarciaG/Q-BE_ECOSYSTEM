# Q-BE Casino Deportes — Base Data Provider (src/ingestion/providers/base_provider.py)
"""
[LN-QBE-002] [LN-QBE-003] [ARCH-PILLAR] Contrato abstracto canónico para proveedores de datos deportivos.
Define los métodos de extracción e interfaces obligatorias para FotMob, Caliente y sensores de IA.
"""

import abc
from typing import Dict, Any, List, Optional


class BaseSportsDataProvider(abc.ABC):
    """Contrato abstracto para proveedores de datos deportivos (FotMob, Sofascore, Gemini)."""

    @abc.abstractmethod
    def get_standings(self, league_id: int, season: Optional[str] = None) -> List[Dict[str, Any]]:
        """Extrae la tabla de posiciones oficial completa con puestos, puntos, PJ, GF, GC, forma y xG."""
        pass

    @abc.abstractmethod
    def get_h2h(self, team1_name: str, team2_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Extrae los últimos enfrentamientos directos de misma liga con fechas reales, marcadores y localía."""
        pass

    @abc.abstractmethod
    def get_team_last_10_matches(self, team_name: str, league_id: int) -> Dict[str, Any]:
        """Extrae los últimos 10 partidos de liga con GF, GC, Tiros al Arco (SoT), Tiros Recibidos (SoTA) y Posesión %."""
        pass

    @abc.abstractmethod
    def get_injuries(self, team_name: str) -> List[Dict[str, Any]]:
        """Extrae el reporte médico oficial de futbolistas lesionados o suspendidos."""
        pass

    @abc.abstractmethod
    def build_match_factual_payload(self, match_raw: Dict[str, Any]) -> Dict[str, Any]:
        """Ensambla el payload fáctico consolidado validado contra el esquema RawMatchInput."""
        pass


# Alias para retrocompatibilidad total
BaseProvider = BaseSportsDataProvider