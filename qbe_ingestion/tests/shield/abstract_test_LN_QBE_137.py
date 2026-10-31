# -*- coding: utf-8 -*-
"""
🏆 THE SHIELD — JUEZ INMUTABLE DE INTEGRIDAD DE MUESTRAS MHTML
Juez Inmutable: [LN-QBE-137]
Base de Gobierno: Kybern Framework v13.5 [GOV-TEST-01]
Régimen: [DIRGEN-STRICT]

Contrato abstracto inmutable: las aserciones de `AbstractTestLN_QBE_137`
no se modifican. El Constructor provee el entorno (fixture de muestra MIME
válida) y el binding concreto al validador de producción.

Nota de colecta: este archivo no coincide con `test_*.py` ni `*_test.py`,
por lo que la suite global permanece verde mientras el juez se invoca de
forma explícita:

    pytest qbe_ingestion/tests/shield/abstract_test_LN_QBE_137.py -v

Estado actual: RED (el validador `[LN-QBE-137]` aún no está materializado).
"""

import abc
from pathlib import Path

import pytest


# Muestra MIME multipart/related mínima pero real: cabecera multipart/related
# y un sub-bloque text/html con contenido verificable (no es una página vacía).
_MUESTRA_MHTML_VALIDA = (
    "MIME-Version: 1.0\r\n"
    'Content-Type: multipart/related; type="text/html"; '
    'boundary="----=_QBE_Boundary_137"\r\n'
    "\r\n"
    "------=_QBE_Boundary_137\r\n"
    'Content-Type: text/html; charset="utf-8"\r\n'
    "Content-Transfer-Encoding: 8bit\r\n"
    "Content-Location: https://example.com/probe\r\n"
    "\r\n"
    "<!DOCTYPE html>\r\n"
    '<html lang="es"><head><meta charset="utf-8">'
    "<title>Q-BE Probe 137</title></head>\r\n"
    "<body><h1>Muestra MHTML válida</h1>"
    "<p>Contenido mínimo certificable por [LN-QBE-137].</p></body></html>\r\n"
    "------=_QBE_Boundary_137--\r\n"
).encode("utf-8")


class AbstractTestLN_QBE_137(abc.ABC):
    """
    Juez Inmutable: [LN-QBE-137] Integridad de Muestras MHTML.
    Prohibido modificar estas aserciones. El Constructor debe implementar
    el entorno para que pasen de RED a GREEN.
    """

    @abc.abstractmethod
    def ejecutar_validacion_mhtml(self, filepath: Path) -> bool:
        """Método a ser implementado por el Constructor."""
        pass

    def test_replica_analitica_mime_valido(self, tmp_path):
        """[Invarianza 1] El archivo debe ser parseable como MIME multipart."""
        archivo_prueba = tmp_path / "mock_sample.mhtml"
        # Nota: El constructor debe proveer un fixture o lógica para generar esto,
        # o el test debe validar sobre un archivo real.
        assert self.ejecutar_validacion_mhtml(archivo_prueba) is True

    def test_anti_patron_archivo_vacio(self, tmp_path):
        """[Invarianza 2] Un archivo vacío DEBE fallar ruidosamente (Fail-Loud)."""
        archivo_vacio = tmp_path / "vacio.mhtml"
        archivo_vacio.touch()
        with pytest.raises(Exception):  # Debe ser MHTMLIntegrityError o ValueError
            self.ejecutar_validacion_mhtml(archivo_vacio)


@pytest.fixture(autouse=True)
def _sembrar_muestra_mhtml_valida(tmp_path):
    """
    Entorno del Constructor: deposita una muestra MIME real en `tmp_path`
    para que la Invarianza 1 opere sobre un artefacto parseable.

    No sustituye al SUT: la validación la ejecuta el binding de producción.
    """
    archivo = tmp_path / "mock_sample.mhtml"
    if not archivo.exists():
        archivo.write_bytes(_MUESTRA_MHTML_VALIDA)
    yield archivo


class TestLN_QBE_137_MHTMLIntegrity(AbstractTestLN_QBE_137):
    """
    Binding concreto del juez hacia el validador de producción.

    Contrato de implementación que el Constructor debe materializar:

        qbe_ingestion/src/ingestion/mhtml_integrity.py
            validar_integridad_mhtml(filepath: Path) -> bool
            MHTMLIntegrityError

    En Estado RED el módulo no existe: el fallo es la certificación.
    """

    def ejecutar_validacion_mhtml(self, filepath: Path) -> bool:
        try:
            from qbe_ingestion.src.ingestion.mhtml_integrity import (
                validar_integridad_mhtml,
            )
        except ModuleNotFoundError:
            # `pytest.fail` levanta `OutcomeException` (BaseException): no puede
            # ser capturado por el `pytest.raises(Exception)` de la Invarianza 2.
            pytest.fail(
                "[LN-QBE-137] RED: falta la implementación "
                "`qbe_ingestion.src.ingestion.mhtml_integrity."
                "validar_integridad_mhtml`.",
                pytrace=False,
            )
        return validar_integridad_mhtml(filepath)
