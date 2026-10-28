# -*- coding: utf-8 -*-
"""
🏆 THE SHIELD — OBSERVATORY WORKING TREE HYGIENE & CLEANLINESS SUITE
Juez Inmutable: [ARCH-ECOSYSTEM-WORKING-TREE-HYGIENE]
Base de Gobierno: Kybern Framework v13.5
"""

import os
import subprocess
from pathlib import Path
import pytest

def test_invarianza_cero_logs_temporales_en_observatorio():
    """[INVARIANZA 1 - HIGIENE]: No deben existir archivos de log (ej. PYTEST_*) residuales en qbe_observatory."""
    raiz_observatory = Path(__file__).resolve().parent.parent
    
    archivos_residuales = list(raiz_observatory.glob("*.log"))
    assert not archivos_residuales, f"Archivos de log temporales detectados: {[f.name for f in archivos_residuales]}"

def test_invarianza_parche_inerte_eliminado_en_lifecycle():
    """[INVARIANZA 2 - DEUDA TÉCNICA]: El parche manual de sqlite pragmas en test_shield_observatory_lifecycle.py debe ser extirpado."""
    ruta_lifecycle = Path(__file__).resolve().parent / "test_shield_observatory_lifecycle.py"
    
    if ruta_lifecycle.exists():
        with open(ruta_lifecycle, "r", encoding="utf-8") as f:
            contenido = f.read()
        
        # El parche antiguo intentaba desregistrar `_set_sqlite_pragmas` de la clase Engine
        assert "_set_sqlite_pragmas" not in contenido, (
            "El parche inerte de pragmas globales sigue existiendo en el archivo de ciclo de vida del Observatorio"
        )
        assert "event.remove(Engine, 'connect'" not in contenido, (
            "Se detectó un intento de manipular eventos globales del Engine desde un test de integración"
        )

def test_invarianza_factor_attribution_reside_en_observatorio():
    """[INVARIANZA 3 - CQRS]: factor_attribution debe residir en el Observatorio, no en el núcleo puro."""
    raiz_ecosystem = Path(__file__).resolve().parent.parent.parent
    
    ruta_core = raiz_ecosystem / "qbe_core" / "src" / "core" / "factor_attribution.py"
    ruta_obs = raiz_ecosystem / "qbe_observatory" / "src" / "observatory" / "core" / "factor_attribution.py"
    
    assert not ruta_core.exists(), "Violación CQRS: factor_attribution fue promovido erróneamente a qbe_core"
    assert ruta_obs.exists(), "Falta factor_attribution en su residencia canónica del Observatorio"
