# -*- coding: utf-8 -*-
"""
🗄️ Q-BE · ADAPTADOR SOBERANO DE LECTURA (`src/core/sovereign_reads.py`)
[LN-QBE-117] · [ARCH-1.4.26] · [ARCH-PILLAR]

Los proveedores de `src/core/sovereign/` son aritmética pura: `[ARCH-1.4.26]` les prohíbe
importar `sqlalchemy`, `src.storage` y `src.ingestion`. Este adaptador concentra TODAS las
lecturas 3NF que esos proveedores necesitan y las publica como **diccionarios planos**, de modo
que la capa pura nunca vea el metamodelo ORM ni el dialecto de la bóveda.

Reglas de la casa:
  * SÓLO lectura: cero `add`/`commit`/`flush`, cero DDL, cero caché lateral, cero defaults.
  * La `sesion` la inyecta el orquestador (`src/core/sovereign_pipeline.py` y scripts de ingesta).
  * Puertas cubiertas: `matches`, `match_telemetry`, `standings_snapshots`.
  * Cada fila se proyecta al contrato mínimo documentado; cualquier columna ausente se publica
    como `None` para que el proveedor decida (jamás se imputa un valor aquí).

Contrato de proyección:
  * `leer_fixture` / `leer_partidos_corte` / `leer_calendario` → `matches`
    (`id`, `competition_id`, `season_id`, `matchday_num`, `kickoff_utc`, `home_team_slug`,
    `away_team_slug`, `status`, `score_home`, `score_away`).
  * `leer_telemetria` → `match_telemetry` (`match_id`, `team_slug`, `possession_pct`, `sot`, `sota`).
  * `leer_snapshots_posiciones` → `standings_snapshots`
    (`id`, `league_id`, `season`, `matchday`, `captured_at`, `positions_json`).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from src.storage.models import Match, MatchTelemetry, StandingSnapshot

__all__ = [
    "leer_calendario",
    "leer_fixture",
    "leer_partidos_corte",
    "leer_snapshots_posiciones",
    "leer_telemetria",
]


def _fila_partido(fila: Any) -> Dict[str, Any]:
    """Proyección plana de una fila de `matches` (contrato interno del adaptador)."""
    return {
        "id": str(fila.id),
        "competition_id": fila.competition_id,
        "season_id": fila.season_id,
        "matchday_num": fila.matchday_num,
        "kickoff_utc": fila.kickoff_utc,
        "home_team_slug": fila.home_team_slug,
        "away_team_slug": fila.away_team_slug,
        "status": fila.status,
        "score_home": fila.score_home,
        "score_away": fila.score_away,
    }


def leer_fixture(sesion: Any, match_id: str) -> Optional[Dict[str, Any]]:
    """Fixture evaluado de la cartelera 3NF, o `None` si el `match_id` no existe."""
    fila = sesion.query(Match).filter(Match.id == str(match_id)).first()
    return _fila_partido(fila) if fila is not None else None


def leer_partidos_corte(sesion: Any, corte: int) -> List[Dict[str, Any]]:
    """Partidos con `matchday_num < corte`, en orden cronológico ascendente (futuro-ceguera)."""
    limite = int(corte)
    filas = (
        sesion.query(Match)
        .filter(Match.matchday_num.isnot(None), Match.matchday_num < limite)
        .order_by(Match.matchday_num.asc(), Match.id.asc())
        .all()
    )
    return [_fila_partido(fila) for fila in filas]


def leer_calendario(sesion: Any) -> List[Dict[str, Any]]:
    """Cartelera completa (todas las jornadas) en el orden natural de la bóveda."""
    return [_fila_partido(fila) for fila in sesion.query(Match).all()]


def leer_telemetria(
    sesion: Any, ids: Sequence[str], slug: str
) -> List[Dict[str, Any]]:
    """Filas de `match_telemetry` del club (`team_slug`) restringidas a `ids`."""
    identificadores = [str(identificador) for identificador in ids]
    if not identificadores:
        return []
    filas = (
        sesion.query(MatchTelemetry)
        .filter(
            MatchTelemetry.match_id.in_(identificadores),
            MatchTelemetry.team_slug == str(slug),
        )
        .all()
    )
    return [
        {
            "match_id": str(fila.match_id),
            "team_slug": fila.team_slug,
            "possession_pct": fila.possession_pct,
            "sot": fila.sot,
            "sota": fila.sota,
        }
        for fila in filas
    ]


def leer_snapshots_posiciones(sesion: Any, corte: int) -> List[Dict[str, Any]]:
    """Snapshots de posiciones con `matchday ≤ corte`, del más reciente al más antiguo."""
    limite = int(corte)
    filas = (
        sesion.query(StandingSnapshot)
        .filter(StandingSnapshot.matchday <= limite)
        .order_by(
            StandingSnapshot.matchday.desc(),
            StandingSnapshot.captured_at.desc(),
            StandingSnapshot.id.desc(),
        )
        .all()
    )
    return [
        {
            "id": fila.id,
            "league_id": fila.league_id,
            "season": fila.season,
            "matchday": fila.matchday,
            "captured_at": fila.captured_at,
            "positions_json": fila.positions_json,
        }
        for fila in filas
    ]
