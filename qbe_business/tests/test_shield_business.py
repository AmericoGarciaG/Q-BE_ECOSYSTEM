# -*- coding: utf-8 -*-
"""
The Shield — Business (Fase 3, Paso 2)

Jueces inmutables de las decisiones arquitectónicas de Fase 3. Nacen RED:
`qbe_storage`, el namespace compartido, la fachada de la SPA y `progol_math`
en `qbe_core` aún no están materializados.

Régimen: [DIRGEN-STRICT] para fronteras; [DBBD-FUNGIBLE] para la fachada.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]      # qbe_business/
ECOSYSTEM_ROOT = PROJECT_ROOT.parent                    # Q_BE_ECOSYSTEM/
BUSINESS_SRC = PROJECT_ROOT / "src"

# Permite `import src.web.app` cuando el namespace compartido exista.
for _path in (str(PROJECT_ROOT), str(PROJECT_ROOT / "src")):
    if _path not in sys.path:
        sys.path.insert(0, _path)


# ── 1. Namespace compartido ─────────────────────────────────────────────────────────────────────

def test_namespace_pep420_core_y_storage_coexisten() -> None:
    """`src.core` (qbe_core) y `src.storage` (qbe_storage) deben convivir sin colisión."""
    import src.core.poisson as poisson
    import src.storage.gateway as gateway

    assert hasattr(poisson, "PoissonBivariateEngine")
    assert hasattr(gateway, "PersistenceGateway")

    ruta_poisson = Path(poisson.__file__).resolve().as_posix()
    ruta_gateway = Path(gateway.__file__).resolve().as_posix()

    assert "qbe_core" in ruta_poisson, f"src.core no viene de qbe_core: {ruta_poisson}"
    assert "qbe_storage" in ruta_gateway, f"src.storage no viene de qbe_storage: {ruta_gateway}"
    assert ruta_poisson != ruta_gateway


# ── 2. Frontera de qbe_business ────────────────────────────────────────────────────────────────

def test_frontera_business_no_importa_observatorio_ni_ingesta() -> None:
    """El AST de qbe_business/src no debe importar qbe_ingestion ni qbe_observatory."""
    assert BUSINESS_SRC.is_dir(), f"no existe todavía {BUSINESS_SRC}"
    archivos = sorted(BUSINESS_SRC.rglob("*.py"))
    assert archivos, f"qbe_business/src no contiene módulos: {BUSINESS_SRC}"

    prohibidos = ("qbe_ingestion", "qbe_observatory", "src.ingestion", "src.observatory")
    violaciones: list[str] = []

    for archivo in archivos:
        arbol = ast.parse(archivo.read_text(encoding="utf-8"), filename=str(archivo))
        for nodo in ast.walk(arbol):
            modulos: list[str] = []
            if isinstance(nodo, ast.Import):
                modulos = [alias.name for alias in nodo.names]
            elif isinstance(nodo, ast.ImportFrom) and nodo.module:
                modulos = [nodo.module]
            for modulo in modulos:
                if modulo.startswith(prohibidos):
                    violaciones.append(f"{archivo.relative_to(PROJECT_ROOT)}:{nodo.lineno}: {modulo}")

    assert not violaciones, "Frontera violada:\n" + "\n".join(violaciones)


# ── 3. Aislamiento de qbe_storage ──────────────────────────────────────────────────────────────

def test_qbe_storage_aislado_de_business_e_ingesta() -> None:
    """qbe_storage debe importarse sin arrastrar qbe_business ni qbe_ingestion."""
    import qbe_storage
    from importlib.metadata import distribution

    ruta = getattr(qbe_storage, "__file__", None)
    assert ruta is not None, "qbe_storage no expone __file__; no es un paquete importable"
    assert "qbe_storage" in Path(ruta).as_posix()

    dist = distribution("qbe_storage")
    requisitos = [r.lower() for r in (dist.requires or [])]
    acoplados = [r for r in requisitos if "qbe-business" in r or "qbe-ingestion" in r]
    assert not acoplados, f"qbe_storage depende de business/ingesta: {acoplados}"

    import src.storage.gateway as gateway

    ruta_gateway = Path(gateway.__file__).resolve().as_posix()
    assert "qbe_storage" in ruta_gateway, f"src.storage no viene de qbe_storage: {ruta_gateway}"
    assert "qbe_business" not in ruta_gateway
    assert "qbe_ingestion" not in ruta_gateway


# ── 4. Fachada de la SPA: feature flags ────────────────────────────────────────────────────────

def test_spa_desactiva_backtesting_y_admin() -> None:
    """La fachada debe declarar ambos flags en false y no servir endpoints no implementados."""
    from fastapi.testclient import TestClient
    from src.web.app import app

    with TestClient(app) as cliente:
        flags = cliente.get("/api/business/features")
        assert flags.status_code == 200, flags.text
        cuerpo = flags.json()
        assert cuerpo["backtesting"] is False
        assert cuerpo["admin"] is False

        backtesting = cliente.get("/api/markets/backtesting/calibration-report")
        assert backtesting.status_code in (404, 503), (
            "La SPA no debe exponer backtesting mientras el flag esté en false"
        )

        admin = cliente.get("/api/admin/status/drift")
        assert admin.status_code in (404, 503), (
            "La SPA no debe exponer admin mientras el flag esté en false"
        )


# ── 5. progol_math dentro de qbe_core ─────────────────────────────────────────────────────────

def test_progol_math_vive_en_qbe_core_sin_ingesta() -> None:
    """progol_math debe importarse de qbe_core y no requerir src.ingestion."""
    from src.core.contracts import progol_math

    ruta = Path(progol_math.__file__).resolve().as_posix()
    assert "qbe_core" in ruta, f"progol_math no viene de qbe_core: {ruta}"
    assert "src.ingestion" not in sys.modules
    assert "qbe_ingestion" not in sys.modules

    assert hasattr(progol_math, "calcular_sesgo_quiniela")
    assert hasattr(progol_math, "PROB_IGNORANCIA")
