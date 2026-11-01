# -*- coding: utf-8 -*-
"""
[LN-QBE-139] Auditor de Paridad Estática AST y Generador de Bandeja GL_update.md

Juez Inmutable: [LN-QBE-140]
Base de Gobierno: docs/GOVERNANCE.md §1.1 / docs/LOGIC.md [LN-QBE-139]
Régimen: [DIRGEN-STRICT] — determinista, solo lectura sobre el código, Fail-Loud.

El Auditor no corrige, no interpreta y no decide: detecta Reglas Huérfanas en el
AST, las clasifica según la taxonomía de docs/GOVERNANCE.md §1.1.3 y propone una
bandeja de revisión al Director Humano.
"""

from __future__ import annotations

import argparse
import ast
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence

PATRON_ETIQUETA = re.compile(r"\[LN-QBE-\d{3}(?:-[A-Z0-9]+)*\]")
ESTADOS_VIGENTES = frozenset({"SELLADO"})
ESTADOS_NO_VIGENTES = frozenset({"EN FORJA", "LIBRE"})
BASE_ASUMIDA_SPRINT = 138


@dataclass(frozen=True)
class Hallazgo:
    """Una Regla Huérfana detectada en un nodo del AST."""

    clase: str
    funcion: str
    etiqueta: str | None
    archivo: str
    linea: int
    evidencia: str = ""


@dataclass(frozen=True)
class ResultadoParidad:
    """Resultado del peritaje de un archivo."""

    reglas_huerfanas: Sequence[Hallazgo]
    archivo: str = ""


class AuditarParidadBG:
    """Auditor determinista de paridad canónica código ↔ Base de Gobierno."""

    def __init__(self, raiz: Path | None = None, registro_path: Path | None = None) -> None:
        self.raiz = Path(raiz) if raiz is not None else Path(__file__).resolve().parents[2]
        self.registro_path = (
            Path(registro_path)
            if registro_path is not None
            else self.raiz / "docs" / "ID_REGISTRY.md"
        )
        self.ids_vigentes = self._cargar_ids_vigentes()

    def _cargar_ids_vigentes(self) -> frozenset[str]:
        """Extrae los IDs LN-QBE vigentes del registro maestro.

        Regla de sprint: las filas 001–138 con estado ausente o malformado se
        asumen vigentes; `EN FORJA` y `LIBRE` nunca se consideran vigentes.
        """
        if not self.registro_path.exists():
            raise FileNotFoundError(
                f"Registro de IDs no encontrado: {self.registro_path}"
            )

        ids: set[str] = set()
        for linea in self.registro_path.read_text(encoding="utf-8-sig").splitlines():
            if not linea.lstrip().startswith("|"):
                continue

            coincidencia = PATRON_ETIQUETA.search(linea)
            if not coincidencia:
                continue
            id_canonico = coincidencia.group(0)

            estado: str | None = None
            for candidato in ("SELLADO", "EN FORJA", "LIBRE"):
                if re.search(rf"\|\s*{re.escape(candidato)}\s*\|", linea):
                    estado = candidato
                    break

            if estado in ESTADOS_VIGENTES:
                ids.add(id_canonico)
                continue
            if estado in ESTADOS_NO_VIGENTES:
                continue

            # Fila sin estado legible: la directiva del sprint autoriza asumir
            # vigentes los IDs históricos 001–138. No se inventan IDs nuevos.
            base = int(id_canonico[8:11])
            if base <= BASE_ASUMIDA_SPRINT:
                ids.add(id_canonico)

        if not ids:
            raise ValueError(
                f"El registro {self.registro_path} no contiene IDs LN-QBE vigentes."
            )
        return frozenset(ids)

    def _ruta_reporte(self, ruta: Path) -> str:
        """Devuelve una ruta estable para la bandeja (relativa a la raíz si es posible)."""
        try:
            return ruta.resolve().relative_to(self.raiz.resolve()).as_posix()
        except ValueError:
            return str(ruta)

    def _etiqueta_en_comentarios_previos(
        self, lineas: Sequence[str], linea_uno_based: int, limite_inferior: int
    ) -> str | None:
        """Busca una etiqueta en el bloque de comentarios inmediatamente anterior."""
        indice = linea_uno_based - 2
        while indice >= limite_inferior:
            texto = lineas[indice].strip()
            if not texto:
                break
            if not texto.startswith("#"):
                break
            coincidencia = PATRON_ETIQUETA.search(texto)
            if coincidencia:
                return coincidencia.group(0)
            indice -= 1
        return None

    def _extraer_etiqueta(
        self,
        nodo: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef,
        lineas: Sequence[str],
    ) -> str | None:
        """Extrae la etiqueta del docstring o de los comentarios adyacentes."""
        docstring = ast.get_docstring(nodo, clean=False)
        if docstring:
            coincidencia = PATRON_ETIQUETA.search(docstring)
            if coincidencia:
                return coincidencia.group(0)

        linea_definicion = lineas[nodo.lineno - 1]
        if "#" in linea_definicion:
            coincidencia = PATRON_ETIQUETA.search(linea_definicion.split("#", 1)[1])
            if coincidencia:
                return coincidencia.group(0)

        inicio = nodo.lineno
        decoradores = getattr(nodo, "decorator_list", ())
        if decoradores:
            inicio = min([inicio] + [decorador.lineno for decorador in decoradores])

        coincidencia = self._etiqueta_en_comentarios_previos(lineas, inicio, 0)
        if coincidencia:
            return coincidencia

        # Comentarios entre la firma y la primera sentencia del cuerpo. Solo se
        # aplican a funciones: en una clase podrían pertenecer al primer método.
        if not isinstance(nodo, ast.ClassDef) and nodo.body:
            coincidencia = self._etiqueta_en_comentarios_previos(
                lineas, nodo.body[0].lineno, nodo.lineno
            )
            if coincidencia:
                return coincidencia

        return None

    @staticmethod
    def _constante_sintetica(nodo: ast.AST) -> float | None:
        """Detecta `except: return 0.0` o `except: return 0.50`."""
        for subnodo in ast.walk(nodo):
            if not isinstance(subnodo, ast.ExceptHandler):
                continue
            for retorno in ast.walk(subnodo):
                if not isinstance(retorno, ast.Return):
                    continue
                valor = retorno.value
                if not isinstance(valor, ast.Constant):
                    continue
                if isinstance(valor.value, bool) or not isinstance(valor.value, (int, float)):
                    continue
                numero = float(valor.value)
                if numero in (0.0, 0.5):
                    return numero
        return None

    @staticmethod
    def _retorno_numerico(nodo: ast.AST) -> float | None:
        """Detecta retornos constantes 0.0 o 1.0 usados como fallback heurístico."""
        for subnodo in ast.walk(nodo):
            if not isinstance(subnodo, ast.Return):
                continue
            valor = subnodo.value
            if not isinstance(valor, ast.Constant):
                continue
            if isinstance(valor.value, bool) or not isinstance(valor.value, (int, float)):
                continue
            numero = float(valor.value)
            if numero in (0.0, 1.0):
                return numero
        return None

    def _clasificar(
        self,
        nodo: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef,
        etiqueta: str | None,
    ) -> tuple[str, str] | None:
        """Devuelve (clase, evidencia) o None si el nodo está en paridad."""
        if etiqueta is not None:
            if etiqueta in self.ids_vigentes:
                return None
            return "III", "Etiqueta no registrada como SELLADO"

        if isinstance(nodo, ast.ClassDef):
            return "IV", "Clase sin etiqueta canónica"

        sintetica = self._constante_sintetica(nodo)
        if sintetica is not None:
            return "I", f"except: return {sintetica:.1f}"

        numerico = self._retorno_numerico(nodo)
        if numerico is not None:
            return "IV", f"return {numerico:.1f} sin etiqueta canónica"

        return "IV", "Nodo sin etiqueta canónica"

    def auditar_archivo(self, ruta: Path) -> ResultadoParidad:
        """Perita un archivo y devuelve sus Reglas Huérfanas.

        Es de solo lectura. Un `SyntaxError` se propaga sin capturarse.
        """
        ruta = Path(ruta)
        fuente = ruta.read_text(encoding="utf-8-sig")
        arbol = ast.parse(fuente, filename=str(ruta))
        lineas = fuente.splitlines()

        hallazgos: list[Hallazgo] = []
        for nodo in ast.walk(arbol):
            if not isinstance(
                nodo, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            ):
                continue

            etiqueta = self._extraer_etiqueta(nodo, lineas)
            clasificacion = self._clasificar(nodo, etiqueta)
            if clasificacion is None:
                continue

            clase, evidencia = clasificacion
            hallazgos.append(
                Hallazgo(
                    clase=clase,
                    funcion=nodo.name,
                    etiqueta=etiqueta,
                    archivo=self._ruta_reporte(ruta),
                    linea=nodo.lineno,
                    evidencia=evidencia,
                )
            )

        hallazgos.sort(key=lambda hallazgo: (hallazgo.linea, hallazgo.funcion, hallazgo.clase))
        return ResultadoParidad(
            reglas_huerfanas=tuple(hallazgos),
            archivo=self._ruta_reporte(ruta),
        )

    @staticmethod
    def _escapar_celda(valor: object) -> str:
        return str(valor).replace("|", "\\|").replace("\n", " ").strip()

    def generar_bandeja(
        self, resultados: List[ResultadoParidad], ruta_salida: Path
    ) -> None:
        """Escribe la bandeja Markdown de revisión para el Director Humano."""
        ruta_salida = Path(ruta_salida)
        todos = sorted(
            (hallazgo for resultado in resultados for hallazgo in resultado.reglas_huerfanas),
            key=lambda hallazgo: (
                hallazgo.archivo,
                hallazgo.linea,
                hallazgo.funcion,
                hallazgo.clase,
            ),
        )
        conteo = Counter(hallazgo.clase for hallazgo in todos)

        lineas: list[str] = [
            "# GL_update — Bandeja de Revisión de Paridad Canónica",
            "",
            "- **Nodo auditor:** `[LN-QBE-139]`",
            "- **Juez:** `[LN-QBE-140]`",
            "- **Sprint:** `SPRINT-41-TRANSICION-Y-CONSISTENCIA-BG`",
            "- **Fuente de vigencia:** `docs/ID_REGISTRY.md` (estado `SELLADO`; regla de sprint 001–138).",
            "- **Estado:** `PENDIENTE DEL DIRECTOR`",
            "",
            "> Esta bandeja es una salida determinista del Auditor de Paridad. No corrige, no interpreta y no decide. El Director marca cada fila con **VÍA A (Erradicación)** o **VÍA B (Formalización)**.",
            "",
            "## Resumen",
            "",
            "| Métrica | Valor |",
            "|---|---:|",
            f"| Archivos auditados | {len(resultados)} |",
            f"| Reglas huérfanas | {len(todos)} |",
            f"| Clase I — Fabricación Sintética | {conteo.get('I', 0)} |",
            f"| Clase II — Contradicción Numérica | {conteo.get('II', 0)} |",
            f"| Clase III — Colisión de Literales | {conteo.get('III', 0)} |",
            f"| Clase IV — Heurísticas Permisivas | {conteo.get('IV', 0)} |",
            "",
            "## Hallazgos",
            "",
            "| # | Archivo | Línea | Función / Nodo | Clase | Etiqueta | Evidencia | VEREDICTO DIRECTOR |",
            "|---:|---|---:|---|---|---|---|---|",
        ]

        if not todos:
            lineas.append("| — | — | — | — | — | — | Sin hallazgos |  |")
        else:
            for indice, hallazgo in enumerate(todos, start=1):
                etiqueta = "—" if hallazgo.etiqueta is None else f"`{hallazgo.etiqueta}`"
                lineas.append(
                    f"| {indice} | `{self._escapar_celda(hallazgo.archivo)}` | "
                    f"{hallazgo.linea} | `{self._escapar_celda(hallazgo.funcion)}` | "
                    f"{hallazgo.clase} | {etiqueta} | "
                    f"`{self._escapar_celda(hallazgo.evidencia)}` |  |"
                )

        lineas.extend(
            [
                "",
                "---",
                "",
                "**VÍA A:** erradicación de la regla huérfana. "
                "**VÍA B:** formalización legislativa y etiquetado con Juez.",
                "",
            ]
        )

        ruta_salida.parent.mkdir(parents=True, exist_ok=True)
        ruta_salida.write_text("\n".join(lineas), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """Entrypoint CLI del Auditor de Paridad."""
    parser = argparse.ArgumentParser(
        description="[LN-QBE-139] Auditor de Paridad Estática AST y Generador de GL_update.md"
    )
    parser.add_argument(
        "rutas",
        nargs="*",
        help="Archivos o directorios a peritar. Por defecto: qbe_core/src/core/.",
    )
    parser.add_argument(
        "--salida",
        default=None,
        help="Ruta de la bandeja. Por defecto: docs/KTP/GL_update.md.",
    )
    parser.add_argument(
        "--registro",
        default=None,
        help="Ruta del registro de IDs. Por defecto: docs/ID_REGISTRY.md.",
    )
    args = parser.parse_args(argv)

    raiz = Path(__file__).resolve().parents[2]
    registro = Path(args.registro) if args.registro else raiz / "docs" / "ID_REGISTRY.md"
    if not registro.is_absolute():
        registro = raiz / registro

    auditor = AuditarParidadBG(raiz=raiz, registro_path=registro)

    objetivos = [Path(ruta) for ruta in args.rutas] if args.rutas else [raiz / "qbe_core" / "src" / "core"]
    resultados: list[ResultadoParidad] = []

    for objetivo in objetivos:
        if not objetivo.is_absolute():
            objetivo = raiz / objetivo
        if not objetivo.exists():
            raise FileNotFoundError(f"Ruta de auditoría no encontrada: {objetivo}")

        archivos = [objetivo] if objetivo.is_file() else sorted(objetivo.rglob("*.py"))
        for archivo in archivos:
            resultados.append(auditor.auditar_archivo(archivo))

    salida = Path(args.salida) if args.salida else raiz / "docs" / "KTP" / "GL_update.md"
    if not salida.is_absolute():
        salida = raiz / salida

    auditor.generar_bandeja(resultados, salida)

    total = sum(len(resultado.reglas_huerfanas) for resultado in resultados)
    conteo = Counter(
        hallazgo.clase
        for resultado in resultados
        for hallazgo in resultado.reglas_huerfanas
    )
    print(f"[LN-QBE-139] Archivos auditados: {len(resultados)}")
    print(
        f"[LN-QBE-139] Reglas huérfanas: {total} "
        f"(Clase I: {conteo.get('I', 0)}, "
        f"Clase III: {conteo.get('III', 0)}, "
        f"Clase IV: {conteo.get('IV', 0)})"
    )
    print(f"[LN-QBE-139] Bandeja: {salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
