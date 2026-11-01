# -*- coding: utf-8 -*-
"""
🏆 THE SHIELD — CANONICAL PARITY & ORPHAN RULE INTEGRITY SUITE
Juez Inmutable: [LN-QBE-140]
Base de Gobierno: docs/GOVERNANCE.md §1.1 / docs/LOGIC.md [LN-QBE-139] y [LN-QBE-140]
Autoridad: Américo García Guerrero (Director Humano)
Régimen: [DIRGEN-STRICT] — Inmutable, Cero Mocks en Producción.

CONTRATO DE INTERFAZ (materialización futura de [LN-QBE-139]):

    from scripts.auditoria.auditar_paridad_bg import AuditarParidadBG

    auditor = AuditarParidadBG()
    resultado = auditor.auditar_archivo(ruta: Path) -> ResultadoParidad

    ResultadoParidad.reglas_huerfanas: Sequence[Hallazgo]
    Hallazgo.clase:    str en {"I", "II", "III", "IV"}
    Hallazgo.funcion:  str (nombre simple de la función infractora)
    Hallazgo.etiqueta: str | None (None si la función no porta [LN-QBE-XXX])
    Hallazgo.archivo:  Path | str
    Hallazgo.linea:    int

Invariantes del contrato:
  1. `auditar_archivo` es de SOLO LECTURA: no escribe, no corrige, no formatea.
  2. Ante sintaxis corrupta DEBE propagar `SyntaxError` (fail-loud), nunca
     devolver un resultado vacío ni silenciar la excepción.
  3. Una función infractora produce EXACTAMENTE un hallazgo; no se duplica
     por patrón sintético y por etiqueta ausente.
  4. La clase I (Fabricación Sintética) cubre `except: return 0.0`.

Este Juez se entrega en RED: `scripts/auditoria/auditar_paridad_bg.py` aún no
existe. El rojo no se corrige relajando el Juez; se corrige materializando el
Auditor en el Paso 3.
"""

import hashlib
import sys
from pathlib import Path

import pytest

RAIZ_ECOSISTEMA = Path(__file__).resolve().parents[2]
if str(RAIZ_ECOSISTEMA) not in sys.path:
    sys.path.insert(0, str(RAIZ_ECOSISTEMA))

try:
    from scripts.auditoria.auditar_paridad_bg import AuditarParidadBG
except ImportError as exc:  # RED controlado: el Auditor todavía no existe.
    AuditarParidadBG = None  # type: ignore[assignment]
    _ERROR_IMPORTACION = exc
else:
    _ERROR_IMPORTACION = None


FUENTE_HUERFANA = '''\
"""Fixture de peritaje: función crítica sin etiqueta canónica."""


def calcular_probabilidad_sintetica(cuota: float) -> float:
    try:
        return 1.0 / cuota
    except:
        return 0.0
'''


def _crear_auditor():
    """Instancia el Auditor o falla ruidosamente si aún no fue materializado."""
    if AuditarParidadBG is None:
        pytest.fail(
            "RED [LN-QBE-140]: falta materializar "
            "`scripts/auditoria/auditar_paridad_bg.py` con la clase "
            "`AuditarParidadBG`. "
            f"Error de importación: {_ERROR_IMPORTACION}"
        )
    return AuditarParidadBG()


def test_replica_analitica_detecta_exactamente_una_regla_huerfana_clase_i(tmp_path):
    """
    [TRIPLE ASERCIÓN 1 — RÉPLICA ANALÍTICA]:
    Una función crítica con `except: return 0.0` y sin `[LN-QBE-XXX]` DEBE
    producir exactamente 1 Regla Huérfana de Clase I.
    """
    ruta = tmp_path / "modulo_huerfano.py"
    ruta.write_text(FUENTE_HUERFANA, encoding="utf-8")

    auditor = _crear_auditor()
    resultado = auditor.auditar_archivo(ruta)

    hallazgos = list(resultado.reglas_huerfanas)
    assert len(hallazgos) == 1, (
        "🚨 El Auditor debió emitir exactamente 1 Regla Huérfana; "
        f"emitió {len(hallazgos)}: "
        f"{[(getattr(h, 'clase', None), getattr(h, 'funcion', None)) for h in hallazgos]}"
    )

    hallazgo = hallazgos[0]
    assert hallazgo.clase == "I", (
        "🚨 La fabricación sintética `except: return 0.0` debe clasificarse "
        f"como Clase I; el Auditor emitió {hallazgo.clase!r}."
    )
    assert hallazgo.funcion == "calcular_probabilidad_sintetica", (
        "🚨 El hallazgo debe señalar la función infractora; "
        f"señaló {hallazgo.funcion!r}."
    )
    assert hallazgo.etiqueta is None, (
        "🚨 La función no porta etiqueta canónica; el Auditor debió reportar "
        f"`etiqueta=None`, no {hallazgo.etiqueta!r}."
    )
    assert Path(hallazgo.archivo).resolve() == ruta.resolve(), (
        "🚨 El hallazgo debe conservar la ruta del archivo peritado."
    )


def test_invarianza_estructural_auditor_no_muta_archivo(tmp_path):
    """
    [TRIPLE ASERCIÓN 2 — INVARIANZA ESTRUCTURAL]:
    El Auditor es de solo lectura. El contenido, el hash SHA-256 y el `mtime`
    del archivo original deben permanecer idénticos tras el peritaje.
    """
    ruta = tmp_path / "modulo_inmutable.py"
    ruta.write_text(FUENTE_HUERFANA, encoding="utf-8")

    bytes_antes = ruta.read_bytes()
    hash_antes = hashlib.sha256(bytes_antes).hexdigest()
    mtime_antes = ruta.stat().st_mtime_ns

    auditor = _crear_auditor()
    auditor.auditar_archivo(ruta)

    bytes_despues = ruta.read_bytes()
    assert bytes_despues == bytes_antes, "🚨 El Auditor modificó el contenido del archivo original."
    assert hashlib.sha256(bytes_despues).hexdigest() == hash_antes, (
        "🚨 El hash SHA-256 del archivo original cambió tras el peritaje."
    )
    assert ruta.stat().st_mtime_ns == mtime_antes, (
        "🚨 El `mtime` del archivo original cambió: el Auditor no es de solo lectura."
    )


def test_sad_path_sintaxis_corrupta_falla_ruidosamente(tmp_path):
    """
    [TRIPLE ASERCIÓN 3 — ANTI-PATRÓN / SAD PATH]:
    Ante un archivo con sintaxis corrupta, el Auditor DEBE propagar una
    excepción explícita `SyntaxError`; prohibido ignorar, devolver vacío o
    degradar silenciosamente.
    """
    ruta = tmp_path / "modulo_corrupto.py"
    ruta.write_text("def funcion_rota(:\n    return 0.0\n", encoding="utf-8")

    auditor = _crear_auditor()
    with pytest.raises(SyntaxError):
        auditor.auditar_archivo(ruta)
