# -*- coding: utf-8 -*-
"""
🏆 THE SHIELD — ECOSYSTEM GOVERNANCE & HYGIENE SUITE
Juez Inmutable: [GOV-ECOSYSTEM-FOUNDATION]
Base de Gobierno: Kybern Framework v13.5
"""

import os
from pathlib import Path
import pytest


def test_invarianza_higiene_global_repositorio():
    """[INVARIANZA 1 - HIGIENE]: Deben existir .gitignore y .gitattributes globales en la raíz."""
    raiz = Path(__file__).resolve().parent.parent.parent

    gitignore = raiz / ".gitignore"
    gitattributes = raiz / ".gitattributes"

    assert gitignore.exists(), "Falta el .gitignore global en la raíz del monorepo"
    assert gitattributes.exists(), "Falta el .gitattributes global en la raíz del monorepo"

    with open(gitignore, "r", encoding="utf-8") as f:
        contenido = f.read()
        assert "*.log" in contenido, "El .gitignore no está filtrando archivos .log"
        assert "*.db" in contenido, "El .gitignore no está filtrando bases de datos SQLite"

    with open(gitattributes, "r", encoding="utf-8") as f:
        assert "text=auto eol=lf" in f.read(), "El .gitattributes no fuerza la normalización LF"


def test_invarianza_presencia_7_libros_canonicos():
    """[INVARIANZA 2 - CONSTITUCIÓN]: Los 7 libros canónicos deben existir en docs/."""
    raiz = Path(__file__).resolve().parent.parent.parent
    docs_dir = raiz / "docs"

    assert docs_dir.exists(), "Falta el directorio docs/ en la raíz del ecosistema"

    libros = [
        "GOVERNANCE.md", "LOGIC.md", "ARCH.md",
        "DESIGN.md", "DIRGEN_VAULT.md", "ID_REGISTRY.md", "CONSTANTS.md"
    ]

    for libro in libros:
        assert (docs_dir / libro).exists(), f"Falta el libro canónico {libro}"


def test_invarianza_arquitectura_refleja_4_pilares():
    """[INVARIANZA 3 - TOPOLOGÍA]: ARCH.md debe documentar los 4 pilares modulares del ecosistema."""
    arch_md = Path(__file__).resolve().parent.parent.parent / "docs" / "ARCH.md"
    if arch_md.exists():
        with open(arch_md, "r", encoding="utf-8") as f:
            contenido = f.read()

        assert "qbe_core" in contenido
        assert "qbe_business" in contenido
        assert "qbe_observatory" in contenido
        assert "qbe_ingestion" in contenido
