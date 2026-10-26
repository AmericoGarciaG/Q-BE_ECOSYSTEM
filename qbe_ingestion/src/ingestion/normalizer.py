"""Compatibilidad del normalizador canónico.

La implementación pura vive en `qbe_core` (`src.core.normalization.normalizer`).
Este módulo conserva el import histórico `src.ingestion.normalizer` sin duplicar
la lógica.
"""

from src.core.normalization.normalizer import (  # noqa: F401
    NormalizationException,
    canonicalize_team_name,
)

__all__ = ["NormalizationException", "canonicalize_team_name"]
