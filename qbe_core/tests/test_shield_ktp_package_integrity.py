# -*- coding: utf-8 -*-
"""
🏆 THE SHIELD — KTP PACKAGE INTEGRITY & GOVERNANCE SUITE
Juez Inmutable: [LN-QBE-138] / [ARCH-1.4.74]
Base de Gobierno: Kybern Framework v13.5 [GOV-TEST-01]
"""

import os
from pathlib import Path
import pytest

def test_invarianza_existencia_paquete_ktp_completo():
    """[INVARIANZA 1 - ESTRUCTURA KTP]: docs/KTP debe contener los 5 archivos canónicos y el directorio history/."""
    raiz = Path(__file__).resolve().parent.parent.parent
    ktp_dir = raiz / "docs" / "KTP"
    
    assert ktp_dir.exists() and ktp_dir.is_dir(), "Falta el directorio docs/KTP en el monorepo"
    
    archivos_requeridos = [
        "KTP_Guide.md",
        "KDB.md",
        "AKT_Pmpt.md",
        "AKT.md",
        "KDB_Act_Pmpt.md"
    ]
    
    for arc in archivos_requeridos:
        ruta_arc = ktp_dir / arc
        assert ruta_arc.exists(), f"Falta el archivo canónico {arc} en docs/KTP/"
        assert ruta_arc.stat().st_size > 100, f"El archivo {arc} no puede estar vacío"

    history_dir = ktp_dir / "history"
    assert history_dir.exists() and history_dir.is_dir(), "Falta el directorio docs/KTP/history/"

def test_invarianza_kdb_declara_invariantes_y_autoridad_suprema():
    """[INVARIANZA 2 - KDB AUTORIDAD E INVARIANTES]: KDB.md debe consagrar la autoridad de Américo García Guerrero y los 11 invariantes."""
    kdb_path = Path(__file__).resolve().parent.parent.parent / "docs" / "KTP" / "KDB.md"
    
    with open(kdb_path, "r", encoding="utf-8") as f:
        contenido = f.read()
        
    assert "Américo García Guerrero" in contenido, "KDB.md no declara la Autoridad Suprema"
    assert "Director Humano" in contenido
    assert "Soberanía Estocástica" in contenido or "Axioma de Dos Mundos" in contenido
    assert "Simplex" in contenido or "Delta^2" in contenido or "Δ²" in contenido
    assert "0.08" in contenido or "V=0" in contenido, "Falta invariante de indemnidad en tablas"
    assert "0.0150" in contenido or "1.5%" in contenido, "Falta invariante de Ley 3 del Underdog"
    assert "1000" in contenido or "Altitud" in contenido, "Falta invariante de Escudo de Altitud"
    assert "0.0100" in contenido or "1.0%" in contenido, "Falta invariante de Banda de Indiferencia"

def test_invarianza_topologia_4_pilares_en_kdb():
    """[INVARIANZA 3 - KDB TOPOLOGÍA]: KDB.md debe documentar los 4 pilares y puertos del ecosistema."""
    kdb_path = Path(__file__).resolve().parent.parent.parent / "docs" / "KTP" / "KDB.md"
    
    with open(kdb_path, "r", encoding="utf-8") as f:
        contenido = f.read()
        
    assert "qbe_core" in contenido
    assert "qbe_ingestion" in contenido and "8002" in contenido
    assert "qbe_business" in contenido and "8000" in contenido
    assert "qbe_observatory" in contenido and "8001" in contenido

def test_invarianza_akt_estado_real_sprint38():
    """[INVARIANZA 4 - AKT ESTADO VIGENTE]: AKT.md debe reflejar el cierre real de la carga de 12 temporadas."""
    akt_path = Path(__file__).resolve().parent.parent.parent / "docs" / "KTP" / "AKT.md"
    
    with open(akt_path, "r", encoding="utf-8") as f:
        contenido = f.read()
        
    assert "3,870" in contenido or "3870" in contenido, "AKT.md debe registrar los 3,870 partidos históricos"
    assert "12 temporadas" in contenido or "12 Temporadas" in contenido
    assert "qbe_historico.db" in contenido
