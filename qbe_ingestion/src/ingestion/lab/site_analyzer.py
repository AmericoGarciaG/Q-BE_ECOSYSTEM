"""Contrato IPO del laboratorio de scraping.

`SiteAnalyzer` recibe una URL y devuelve un `ExtractionPlan`: selectores CSS,
endpoints JSON candidatos y nivel de confianza. La implementación real usará el
gateway LLM de Ingesta; el `FakeSiteAnalyzer` permite certificar el contrato sin
red ni Gemini.
"""

from __future__ import annotations

from typing import Dict, List, Protocol

from pydantic import BaseModel, Field


class ExtractionPlan(BaseModel):
    url: str
    selectors: Dict[str, str] = Field(default_factory=dict)
    json_endpoints: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    notes: str = ""


class SiteAnalyzer(Protocol):
    def analyze(self, url: str) -> ExtractionPlan: ...


class FakeSiteAnalyzer:
    """Analizador determinista para tests; no toca la red."""

    def analyze(self, url: str) -> ExtractionPlan:
        return ExtractionPlan(
            url=url,
            selectors={"title": "h1", "rows": "table tbody tr"},
            json_endpoints=[],
            confidence=0.5,
            notes="fake: contrato certificado sin LLM",
        )
