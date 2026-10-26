"""The Shield — contrato del laboratorio de scraping (Slice 4B)."""

from __future__ import annotations


def test_lab_puede_instanciarse_y_devuelve_contrato() -> None:
    from src.ingestion.lab.site_analyzer import ExtractionPlan, FakeSiteAnalyzer

    analyzer = FakeSiteAnalyzer()
    plan = analyzer.analyze("https://example.com/odds")

    assert isinstance(plan, ExtractionPlan)
    assert plan.url == "https://example.com/odds"
    assert "title" in plan.selectors
    assert isinstance(plan.json_endpoints, list)
    assert 0.0 <= plan.confidence <= 1.0
