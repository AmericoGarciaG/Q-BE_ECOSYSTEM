# -*- coding: utf-8 -*-
"""Parsers offline de ingesta — volcados MIME HTML de FootyStats.

[LN-QBE-134] / [ARCH-1.4.71]
Régimen: `[DBBD-FUNGIBLE]` en el desempaquetado; `[DIRGEN-STRICT]` en la
aserción de integridad de temporada.

Cero red, cero navegador, cero dependencias fuera de la librería estándar y
`bs4` con `html.parser`.
"""
from __future__ import annotations

import argparse
import email
import json
import re
import sys
from datetime import datetime, timezone
from email import policy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from bs4 import BeautifulSoup

RAIZ_PROYECTO = Path(__file__).resolve().parents[4]
RAW_ROOT = RAIZ_PROYECTO / "data" / "raw_footystats"
OUT_ROOT = RAIZ_PROYECTO / "data" / "extracted_footystats"

FUENTE_XG = "FOOTYSTATS_PROPIETARIO"

_PATRON_TEMPORADA = re.compile(r"(\d{4})\s*[/\-_]\s*(\d{2,4})")
_PATRON_HASH = re.compile(r"^(\d{4})(\d{4})$")
_PATRON_EPOCH = re.compile(r"^\d{9,11}$")
_PATRON_MARCADOR = re.compile(r"^\s*(\d+)\s*-\s*(\d+)\s*$")
_PATRON_NUMERO = re.compile(r"^\s*([+-]?\d+(?:\.\d+)?)")


class SeasonIntegrityError(Exception):
    """[LN-QBE-134] El volcado no declara la temporada de su carpeta contenedora."""


# ── Utilidades de texto ────────────────────────────────────────────────────────────────────────
def _texto(nodo: Any) -> str:
    if nodo is None:
        return ""
    return re.sub(r"\s+", " ", nodo.get_text(" ", strip=True)).strip()


def _flotante(valor: str) -> Optional[float]:
    coincide = _PATRON_NUMERO.match(str(valor or ""))
    if not coincide:
        return None
    try:
        return float(coincide.group(1))
    except ValueError:
        return None


def _entero(valor: str) -> Optional[int]:
    numero = _flotante(valor)
    return int(numero) if numero is not None else None


def normalizar_temporada(valor: Optional[str]) -> Optional[str]:
    """Normaliza `2018/19`, `2018-2019` o `20182019` a `2018_2019`."""
    if not valor:
        return None
    texto = str(valor).strip()
    hash_ocho = _PATRON_HASH.match(texto)
    if hash_ocho:
        return f"{hash_ocho.group(1)}_{hash_ocho.group(2)}"
    coincide = _PATRON_TEMPORADA.search(texto)
    if not coincide:
        return None
    inicio = coincide.group(1)
    fin = coincide.group(2)
    if len(fin) == 2:
        fin = inicio[:2] + fin
    elif len(fin) == 3:
        fin = inicio[:1] + fin
    return f"{inicio}_{fin}"


# ── MIME ────────────────────────────────────────────────────────────────────────────────────────
def extraer_html_de_mhtml(ruta_archivo: Path) -> str:
    """Extrae la parte `text/html` de un `.mhtml` (RFC 822/2045)."""
    ruta = Path(ruta_archivo)
    with open(ruta, "rb") as manejador:
        mensaje = email.message_from_binary_file(manejador, policy=policy.default)
    for parte in mensaje.walk():
        if parte.get_content_type() == "text/html":
            carga = parte.get_payload(decode=True)
            if carga is None:
                continue
            codificacion = parte.get_content_charset() or "utf-8"
            return carga.decode(codificacion, errors="replace")
    raise ValueError(f"No se encontró payload text/html en {ruta}")


# ── Integridad de temporada ────────────────────────────────────────────────────────────────────
def detectar_temporada_html(html: str) -> Tuple[Optional[str], Optional[str]]:
    """Devuelve `(temporada, origen_marcador)`.

    Orden: H1 de Fixtures → `data-hash` activo → H1 genérico con temporada.
    El `<title>` queda prohibido: en este corpus declara `2026/27` en todas las
    capturas históricas.
    """
    sopa = BeautifulSoup(html, "html.parser")

    h1 = sopa.select_one("h1.detailed-stats-h1")
    if h1 is not None:
        span = h1.select_one("span.normal")
        temporada = normalizar_temporada(_texto(span) if span is not None else _texto(h1))
        if temporada:
            return temporada, "H1"

    activo = sopa.select_one("li.active a.changeLeagueDataButton[data-hash]")
    if activo is not None:
        temporada = normalizar_temporada(activo.get("data-hash"))
        if temporada:
            return temporada, "DATA_HASH"

    for cabecera in sopa.find_all("h1"):
        temporada = normalizar_temporada(_texto(cabecera))
        if temporada:
            return temporada, "H1_GENERICO"

    return None, None


def verificar_integridad_temporada_html(
    html: str,
    carpeta_esperada: str,
    permitir_heredada: bool = False,
) -> str:
    """Aserción inviolable `Temporada_DOM == NombreCarpeta` (Fail-Loud)."""
    esperada = normalizar_temporada(carpeta_esperada)
    if not esperada:
        raise SeasonIntegrityError(
            f"Nombre de carpeta no normalizable: {carpeta_esperada!r}"
        )

    detectada, origen = detectar_temporada_html(html)
    if detectada is None:
        if permitir_heredada:
            return esperada
        raise SeasonIntegrityError(
            f"Sin marcador de temporada en el DOM; carpeta esperada {esperada}"
        )

    if detectada != esperada:
        raise SeasonIntegrityError(
            f"Discrepancia fáctica: archivo en {esperada} contiene datos de {detectada}"
        )
    return detectada


# ── Fixtures ───────────────────────────────────────────────────────────────────────────────────
def _nombre_equipo(celda: Any) -> Optional[str]:
    if celda is None:
        return None
    enlace = celda.find("a")
    if enlace is not None:
        for fragmento in enlace.find_all(string=True, recursive=False):
            texto = str(fragmento).strip()
            if texto:
                return texto
    texto = _texto(celda)
    if not texto:
        return None
    return re.split(r"\s+Liga MX\b", texto, maxsplit=1)[0].strip() or None


def _equipo(row: Any, lado: str) -> Tuple[Optional[str], Optional[int]]:
    nodo = row.select_one(f".team.{lado} span[data-team-id]")
    if nodo is None:
        nodo = row.select_one(f".team.{lado}")
    if nodo is None:
        return None, None
    nombre = _texto(nodo) or None
    identificador = nodo.get("data-team-id")
    try:
        return nombre, int(identificador) if identificador is not None else None
    except (TypeError, ValueError):
        return nombre, None


def _cuotas(row: Any) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    spans = row.select("li.match-stats .stat.odds > span")
    valores: List[float] = []
    for span in spans:
        valor = _flotante(_texto(span))
        if valor is not None:
            valores.append(valor)
        if len(valores) == 3:
            break
    if len(valores) != 3:
        return None, None, None
    return valores[0], valores[1], valores[2]


def _marcador(row: Any) -> Tuple[Optional[int], Optional[int]]:
    nodo = row.select_one(".ft-score")
    if nodo is None:
        return None, None
    coincide = _PATRON_MARCADOR.match(_texto(nodo))
    if not coincide:
        return None, None
    return int(coincide.group(1)), int(coincide.group(2))


def _epoch(row: Any) -> Optional[int]:
    nodo = row.select_one(".date [data-time]")
    if nodo is None:
        return None
    crudo = str(nodo.get("data-time") or "").strip()
    return int(crudo) if _PATRON_EPOCH.match(crudo) else None


def _referencia(row: Any) -> Optional[str]:
    for clase in row.get("class") or []:
        if re.fullmatch(r"z\d+", str(clase)):
            return str(clase)
    return None


def parsear_archivo_fixtures_html(html: str, temporada: str) -> List[Dict[str, Any]]:
    """Extrae los partidos de `Fixtures_*.mhtml` (sólo hechos declarados)."""
    sopa = BeautifulSoup(html, "html.parser")
    partidos: List[Dict[str, Any]] = []

    for row in sopa.select("ul.match"):
        home_team, home_id = _equipo(row, "home")
        away_team, away_id = _equipo(row, "away")
        if not home_team or not away_team:
            continue

        home_goals, away_goals = _marcador(row)
        odd_home, odd_draw, odd_away = _cuotas(row)
        epoch = _epoch(row)
        fecha_utc = None
        if epoch is not None:
            fecha_utc = (
                datetime.fromtimestamp(epoch, tz=timezone.utc)
                .isoformat()
                .replace("+00:00", "Z")
            )

        partidos.append(
            {
                "match_ref": _referencia(row),
                "temporada": temporada,
                "fecha_utc": fecha_utc,
                "fecha_epoch": epoch,
                "fecha_texto": _texto(row.select_one(".date")),
                "home_team": home_team,
                "away_team": away_team,
                "home_team_id": home_id,
                "away_team_id": away_id,
                "home_goals": home_goals,
                "away_goals": away_goals,
                "odd_home": odd_home,
                "odd_draw": odd_draw,
                "odd_away": odd_away,
                "xg_home": None,
                "xg_away": None,
                "fuente_xg": None,
            }
        )
    return partidos


# ── Forma Last 5 ──────────────────────────────────────────────────────────────────────────────
def parsear_archivo_forma_html(html: str, temporada: str) -> List[Dict[str, Any]]:
    """Extrae la tabla `form-5-table` (Last 5) por club."""
    sopa = BeautifulSoup(html, "html.parser")
    tabla = sopa.select_one("table.form-5-table")
    if tabla is None:
        cabecera = next(
            (h for h in sopa.find_all("h2") if "Last 5 Form Table" in _texto(h)),
            None,
        )
        tabla = cabecera.find_next("table") if cabecera is not None else None
    if tabla is None:
        return []

    cuerpo = tabla.find("tbody") or tabla
    filas: List[Dict[str, Any]] = []
    for row in cuerpo.find_all("tr", recursive=False):
        celdas = row.find_all("td", recursive=False)
        if len(celdas) < 13:
            continue
        equipo = _nombre_equipo(celdas[2])
        if not equipo:
            continue
        filas.append(
            {
                "temporada": temporada,
                "team": equipo,
                "mp_last5": _entero(_texto(celdas[3])),
                "w_last5": _entero(_texto(celdas[4])),
                "d_last5": _entero(_texto(celdas[5])),
                "l_last5": _entero(_texto(celdas[6])),
                "gf_last5": _entero(_texto(celdas[7])),
                "ga_last5": _entero(_texto(celdas[8])),
                "gd_last5": _entero(_texto(celdas[9])),
                "pts_last5": _entero(_texto(celdas[10])),
                "forma_last5": _texto(celdas[11]),
                "ppg_last5": _flotante(_texto(celdas[12])),
                "cs_pct": _flotante(_texto(celdas[13])) if len(celdas) > 13 else None,
                "fts_pct": _flotante(_texto(celdas[14])) if len(celdas) > 14 else None,
                "btts_pct": _flotante(_texto(celdas[15])) if len(celdas) > 15 else None,
            }
        )
    return filas


# ── xG macro por club-temporada ───────────────────────────────────────────────────────────────
def parsear_archivo_xg_macro_html(html: str, temporada: str) -> List[Dict[str, Any]]:
    """Extrae la tabla macro `Team | MP | xG | xGA | xGD | GF | GA`."""
    sopa = BeautifulSoup(html, "html.parser")
    tabla = sopa.select_one("table.xg-all")
    if tabla is None:
        for candidata in sopa.find_all("table"):
            encabezados = {_texto(th).lower() for th in candidata.find_all("th")}
            if "xg" in encabezados and "xga" in encabezados:
                tabla = candidata
                break
    if tabla is None:
        return []

    cuerpo = tabla.find("tbody") or tabla
    filas: List[Dict[str, Any]] = []
    for row in cuerpo.find_all("tr", recursive=False):
        celdas = row.find_all("td", recursive=False)
        if len(celdas) < 10:
            continue
        equipo = _nombre_equipo(celdas[2])
        if not equipo:
            continue
        filas.append(
            {
                "temporada": temporada,
                "team": equipo,
                "mp": _entero(_texto(celdas[3])),
                "xg": _flotante(_texto(celdas[4])),
                "xga": _flotante(_texto(celdas[5])),
                "xgd": _flotante(_texto(celdas[6])),
                "gf": _flotante(_texto(celdas[7])),
                "ga": _flotante(_texto(celdas[8])),
                "xg_vs_actual": _flotante(_texto(celdas[9])),
                "fuente_xg": FUENTE_XG,
            }
        )
    return filas


# ── Orquestación ──────────────────────────────────────────────────────────────────────────────
def _archivo(carpeta: Path, patron: str) -> Optional[Path]:
    return next(carpeta.glob(patron), None)


def procesar_temporada(carpeta: Path) -> Dict[str, Any]:
    """Valida integridad, extrae y devuelve el dataset de una carpeta."""
    temporada = normalizar_temporada(carpeta.name)
    if not temporada:
        raise SeasonIntegrityError(f"Carpeta no normalizable: {carpeta.name}")

    archivos = {
        "fixtures": _archivo(carpeta, "Fixtures*.mhtml"),
        "forma": _archivo(carpeta, "Form Table*.mhtml"),
        "xg": _archivo(carpeta, "xG*.mhtml"),
    }

    integridad: Dict[str, str] = {}
    fixtures: List[Dict[str, Any]] = []
    forma: List[Dict[str, Any]] = []
    xg_macro: List[Dict[str, Any]] = []

    if archivos["fixtures"] is not None:
        html = extraer_html_de_mhtml(archivos["fixtures"])
        verificar_integridad_temporada_html(html, carpeta.name)
        integridad["fixtures"] = "OK"
        fixtures = parsear_archivo_fixtures_html(html, temporada)
    else:
        integridad["fixtures"] = "AUSENTE"

    if archivos["forma"] is not None:
        html = extraer_html_de_mhtml(archivos["forma"])
        detectada, origen = detectar_temporada_html(html)
        if detectada is None:
            verificar_integridad_temporada_html(
                html, carpeta.name, permitir_heredada=True
            )
            integridad["forma"] = "OK_HEREDADA"
        else:
            verificar_integridad_temporada_html(html, carpeta.name)
            integridad["forma"] = f"OK_{origen}"
        forma = parsear_archivo_forma_html(html, temporada)
    else:
        integridad["forma"] = "AUSENTE"

    if archivos["xg"] is not None:
        html = extraer_html_de_mhtml(archivos["xg"])
        detectada, origen = detectar_temporada_html(html)
        if detectada is None:
            verificar_integridad_temporada_html(
                html, carpeta.name, permitir_heredada=True
            )
            integridad["xg"] = "OK_HEREDADA"
        else:
            verificar_integridad_temporada_html(html, carpeta.name)
            integridad["xg"] = f"OK_{origen}"
        xg_macro = parsear_archivo_xg_macro_html(html, temporada)
    else:
        integridad["xg"] = "AUSENTE"

    con_cuotas = sum(
        1
        for p in fixtures
        if None not in (p.get("odd_home"), p.get("odd_draw"), p.get("odd_away"))
    )
    return {
        "temporada": temporada,
        "archivos": {k: (v.name if v is not None else None) for k, v in archivos.items()},
        "integridad": integridad,
        "resumen": {
            "archivos": sum(1 for v in archivos.values() if v is not None),
            "partidos": len(fixtures),
            "con_cuotas_1x2": con_cuotas,
            "con_xg_macro": len(xg_macro),
            "equipos_forma": len(forma),
        },
        "fixtures": fixtures,
        "forma": forma,
        "xg_macro": xg_macro,
    }


def _carpetas(raw_root: Path) -> List[Path]:
    return sorted(p for p in raw_root.glob("20*_*") if p.is_dir())


def _fila_tablero(dataset: Dict[str, Any]) -> Tuple[str, ...]:
    resumen = dataset["resumen"]
    integridad = "OK" if all(
        str(v).startswith("OK") for v in dataset["integridad"].values() if v != "AUSENTE"
    ) else "FALLA"
    con_xg = str(resumen["con_xg_macro"]) if resumen["con_xg_macro"] else "N/A"
    return (
        dataset["temporada"],
        str(resumen["archivos"]),
        integridad,
        str(resumen["partidos"]),
        con_xg,
        str(resumen["con_cuotas_1x2"]),
        "OK" if resumen["partidos"] and integridad == "OK" else "PARCIAL",
    )


def _imprimir_tablero(filas: Sequence[Tuple[str, ...]]) -> None:
    cabecera = ("TEMPORADA", "ARCHIVOS", "INTEGRIDAD", "PARTIDOS", "CON XG", "CUOTAS 1X2", "ESTADO")
    anchos = [max(len(str(f[i])) for f in [cabecera, *filas]) for i in range(len(cabecera))]
    linea = " | ".join(h.ljust(anchos[i]) for i, h in enumerate(cabecera))
    print(linea)
    print("-+-".join("-" * a for a in anchos))
    for fila in filas:
        print(" | ".join(str(v).ljust(anchos[i]) for i, v in enumerate(fila)))


def _verificar_solo(raw_root: Path) -> int:
    filas: List[Tuple[str, ...]] = []
    fallos = 0
    for carpeta in _carpetas(raw_root):
        temporada = normalizar_temporada(carpeta.name) or carpeta.name
        estados: List[str] = []
        for archivo in sorted(carpeta.glob("*.mhtml")):
            html = extraer_html_de_mhtml(archivo)
            try:
                detectada, origen = detectar_temporada_html(html)
                if detectada is None and "Fixtures" not in archivo.name:
                    detectada = normalizar_temporada(carpeta.name)
                    origen = "HEREDADA"
                if detectada is None:
                    raise SeasonIntegrityError(
                        f"Sin marcador de temporada en {archivo.name}"
                    )
                if detectada != normalizar_temporada(carpeta.name):
                    raise SeasonIntegrityError(
                        f"{archivo.name} declara {detectada}, carpeta {carpeta.name}"
                    )
                estados.append(f"OK({origen})")
            except SeasonIntegrityError as error:
                estados.append("FALLA")
                fallos += 1
                print(f"  🔴 {carpeta.name}/{archivo.name}: {error}")
        filas.append(
            (
                temporada,
                str(len(list(carpeta.glob("*.mhtml")))),
                "OK" if all(e.startswith("OK") for e in estados) else "FALLA",
                "-",
                "-",
                "-",
                "OK" if all(e.startswith("OK") for e in estados) else "FALLA",
            )
        )
    _imprimir_tablero(filas)
    return 0 if fallos == 0 else 1


def _exportar(dataset: Dict[str, Any], out_root: Path) -> Path:
    out_root.mkdir(parents=True, exist_ok=True)
    destino = out_root / f"temporada_{dataset['temporada']}.json"
    destino.write_text(
        json.dumps(dataset, ensure_ascii=False, indent=2, sort_keys=False),
        encoding="utf-8",
    )
    return destino


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="parsear_footystats_mhtml",
        description="[LN-QBE-134] Parser offline de volcados MHTML de FootyStats.",
    )
    parser.add_argument("--verificar-solo", action="store_true", help="valida integridad sin escribir")
    parser.add_argument("--temporada", default=None, help="procesa una sola temporada (YYYY_YYYY)")
    parser.add_argument("--todas", action="store_true", help="procesa todas las temporadas")
    parser.add_argument("--raw-root", default=str(RAW_ROOT), help="raíz de volcados .mhtml")
    parser.add_argument("--out-root", default=str(OUT_ROOT), help="directorio de salida JSON")
    argumentos = parser.parse_args(argv)

    raw_root = Path(argumentos.raw_root)
    out_root = Path(argumentos.out_root)

    if not raw_root.is_dir():
        print(f"🔴 No existe la raíz de volcados: {raw_root}", file=sys.stderr)
        return 2

    if argumentos.verificar_solo:
        return _verificar_solo(raw_root)

    carpetas = _carpetas(raw_root)
    if argumentos.temporada:
        esperada = normalizar_temporada(argumentos.temporada)
        carpetas = [c for c in carpetas if normalizar_temporada(c.name) == esperada]
        if not carpetas:
            print(f"🔴 Temporada no encontrada: {argumentos.temporada}", file=sys.stderr)
            return 2

    if not argumentos.todas and not argumentos.temporada:
        parser.error("Indique --todas, --temporada o --verificar-solo")

    filas: List[Tuple[str, ...]] = []
    errores = 0
    for carpeta in carpetas:
        try:
            dataset = procesar_temporada(carpeta)
        except SeasonIntegrityError as error:
            errores += 1
            print(f"🔴 {carpeta.name}: {error}", file=sys.stderr)
            filas.append((carpeta.name, "-", "FALLA", "-", "-", "-", "ERROR"))
            continue
        destino = _exportar(dataset, out_root)
        filas.append(_fila_tablero(dataset))
        print(f"✅ {dataset['temporada']} → {destino.name}")

    print()
    _imprimir_tablero(filas)
    return 0 if errores == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
