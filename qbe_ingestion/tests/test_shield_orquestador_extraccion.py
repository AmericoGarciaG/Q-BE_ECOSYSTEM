# -*- coding: utf-8 -*-
"""🏆 THE SHIELD — JUEZ INMUTABLE DEL ORQUESTADOR DE EXTRACCIÓN MASIVA.

Nodos: `[LN-QBE-143]` Orquestador de Extracción Masiva de Eventos y
`[LN-QBE-144]` Almacén de Eventos Históricos (`historical_match_events`).
Base de Gobierno: `docs/LOGIC.md` §17 y `docs/ARCH.md` §15 ([ARCH-1.5.1]).

Aislamiento: los imports son diferidos para no contaminar `sys.modules`
durante la colecta (el Juez de fronteras de `qbe_business` verifica que
`qbe_ingestion` no se importe a nivel de módulo).

Los dobles de prueba (Sonda, descargador, parser) son exclusivos del Juez:
en producción no existe ningún mock (`[GOVERNANCE-01]`).
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List

import pytest

RAIZ = Path(__file__).resolve().parents[2]
MHTML_MUESTRA = (
    RAIZ / "data" / "raw_ligamx_min_x_min" / "MinXMin_2015-2016_Clau_Ame_vs_MTY.mhtml"
)

MATCH_AME_MTY = "fs_2015_2016_z85264"

# Eventos con la forma exacta del contrato `[LN-QBE-141]`: cubren lado local y
# visita, minuto base, tiempo agregado y marcador de período.
EVENTOS = [
    {
        "evento_id": "111593",
        "lado": "local",
        "equipo": None,
        "minuto_texto": "MF",
        "minuto": None,
        "minuto_agregado": None,
        "marcador_periodo": "MF",
        "periodo": "MF",
        "tipo": "final_partido",
        "descripcion": "El árbitro silba el Final del Partido: América 3 - 3 Monterrey",
        "video_url": None,
        "paso": "emf",
        "orden_dom": 0,
    },
    {
        "evento_id": "111584",
        "lado": "local",
        "equipo": "América",
        "minuto_texto": "78'",
        "minuto": 78,
        "minuto_agregado": None,
        "marcador_periodo": None,
        "periodo": "2T",
        "tipo": "gol",
        "descripcion": "¡Goool de América! Anotación de Darío Ismael Benedetto",
        "video_url": None,
        "paso": None,
        "orden_dom": 1,
    },
    {
        "evento_id": "111591",
        "lado": "visita",
        "equipo": "Monterrey",
        "minuto_texto": "+1'",
        "minuto": None,
        "minuto_agregado": 1,
        "marcador_periodo": None,
        "periodo": "2T",
        "tipo": "corner",
        "descripcion": "Tiro de esquina de Monterrey",
        "video_url": None,
        "paso": None,
        "orden_dom": 2,
    },
    {
        "evento_id": "111570",
        "lado": "local",
        "equipo": None,
        "minuto_texto": "MT",
        "minuto": None,
        "minuto_agregado": None,
        "marcador_periodo": "MT",
        "periodo": "MT",
        "tipo": "final_primer_tiempo",
        "descripcion": "Final del primer tiempo: América 1 - 1 Monterrey",
        "video_url": None,
        "paso": None,
        "orden_dom": 3,
    },
]

_SQL_MATCHES = """
CREATE TABLE historical_matches (
    match_id       TEXT PRIMARY KEY,
    temporada      TEXT NOT NULL,
    home_team      TEXT NOT NULL,
    away_team      TEXT NOT NULL,
    home_team_slug TEXT,
    away_team_slug TEXT,
    home_goals     INTEGER,
    away_goals     INTEGER
)
"""

_FILAS_BOVEDA = [
    (MATCH_AME_MTY, "2015_2016", "América", "Monterrey", "america", "monterrey", 3, 3),
    ("fs_2015_2016_z85265", "2015_2016", "Guadalajara", "Atlas", "guadalajara", "atlas", 1, 0),
]

# Filas canónicas de los cinco partidos que el Join Determinista rechazaba por
# brecha de alias antes de [LN-QBE-145].
_FILAS_ALIAS = [
    ("fs_2015_2016_z85271", "2015_2016", "Chiapas", "Atlas", "chiapas", "atlas", 0, 3),
    ("fs_2015_2016_z85272", "2015_2016", "Morelia", "Santos Laguna", "morelia", "santos-laguna", 3, 2),
    ("fs_2015_2016_z85273", "2015_2016", "Tigres UANL", "Veracruz", "tigres-uanl", "veracruz", 0, 0),
    ("fs_2015_2016_z85274", "2015_2016", "Tijuana", "Puebla", "tijuana", "puebla", 0, 0),
    ("fs_2015_2016_z85275", "2015_2016", "Querétaro", "Pumas UNAM", "queretaro", "pumas-unam", 2, 1),
]


# ── Acceso diferido a los módulos bajo juicio ───────────────────────────────────────────────
def _almacen():
    from qbe_ingestion.src.ingestion.loaders import cargar_eventos_historicos

    return cargar_eventos_historicos


def _orquestador():
    from scripts.auditoria import extraer_historico_ligamx

    return extraer_historico_ligamx


def _parser():
    from qbe_ingestion.src.ingestion.parsers import parsear_minuto_a_minuto

    return parsear_minuto_a_minuto


def _alias():
    from qbe_core.src.core.normalization import ligamx_alias

    return ligamx_alias


# ── Utilidades ──────────────────────────────────────────────────────────────────────────────
def _boveda(ruta: Path, filas: List[tuple] = None) -> Path:
    """Crea una bóveda mínima con `historical_matches` poblada."""
    conexion = sqlite3.connect(ruta)
    conexion.execute(_SQL_MATCHES)
    conexion.executemany(
        "INSERT INTO historical_matches VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        _FILAS_BOVEDA if filas is None else filas,
    )
    conexion.commit()
    conexion.close()
    return ruta


def _filas_eventos(ruta: Path, match_id: str = MATCH_AME_MTY) -> List[tuple]:
    conexion = sqlite3.connect(ruta)
    try:
        return list(
            conexion.execute(
                "SELECT evento_id, minuto_texto, minuto_entero, minuto_agregado, "
                "periodo, tipo_evento, equipo, descripcion, orden_dom "
                "FROM historical_match_events WHERE match_id = ? ORDER BY orden_dom",
                (match_id,),
            )
        )
    finally:
        conexion.close()


class _DescargadorEspia:
    """Doble del navegador: entrega un HTML fijo y registra las URLs pedidas."""

    def __init__(self, html: str = "<html>mxm</html>", fallos: tuple = ()) -> None:
        self.html = html
        self.fallos = set(fallos)
        self.llamadas: List[str] = []

    def __enter__(self) -> "_DescargadorEspia":
        return self

    def __exit__(self, *_excepcion: Any) -> bool:
        return False

    def descargar(self, url: str) -> str:
        self.llamadas.append(url)
        if url in self.fallos:
            raise RuntimeError(f"descarga simulada fallida: {url}")
        return self.html


def _partido(match_id: str, local: str, visitante: str) -> Dict[str, str]:
    return {
        "id_partido": match_id,
        "local": local,
        "visitante": visitante,
        "goles_local": 3,
        "goles_visitante": 3,
        "url_minuto_a_minuto": f"https://ligamx.net/cancha/mxm/{match_id}/pestana",
    }


SOBRE_AME = {
    "equipo_local": "América",
    "equipo_visitante": "Monterrey",
    "marcador_local": 3,
    "marcador_visitante": 3,
    "eventos": EVENTOS,
}


# ── [LN-QBE-144] Almacén de Eventos ─────────────────────────────────────────────────────────
def test_almacen_crea_tabla_por_reflection_ddl(tmp_path: Path) -> None:
    """[INV 1] La tabla se crea con el DDL canónico si la bóveda no la tiene."""
    almacen = _almacen()
    boveda = _boveda(tmp_path / "boveda.db")

    resultado = almacen.cargar_eventos(boveda, MATCH_AME_MTY, EVENTOS)

    assert resultado == {
        "match_id": MATCH_AME_MTY,
        "recibidos": len(EVENTOS),
        "insertados": len(EVENTOS),
        "ignorados": 0,
        "total_en_tabla": len(EVENTOS),
    }
    conexion = sqlite3.connect(boveda)
    try:
        columnas = {fila[1] for fila in conexion.execute("PRAGMA table_info(historical_match_events)")}
        indices = {fila[1] for fila in conexion.execute("PRAGMA index_list(historical_match_events)")}
    finally:
        conexion.close()
    assert {
        "match_id", "evento_id", "minuto_texto", "minuto_entero", "minuto_agregado",
        "periodo", "tipo_evento", "equipo", "descripcion", "orden_dom",
        "fuente_datos", "cargado_utc",
    } <= columnas
    assert "idx_hist_events_match" in indices


def test_almacen_inserta_todos_los_eventos_y_mapea_el_lado(tmp_path: Path) -> None:
    """[INV 2] Los n eventos del parser quedan persistidos y `lado` → `equipo`."""
    almacen = _almacen()
    boveda = _boveda(tmp_path / "boveda.db")

    almacen.cargar_eventos(boveda, MATCH_AME_MTY, EVENTOS)
    filas = _filas_eventos(boveda)

    assert len(filas) == len(EVENTOS)
    assert [fila[0] for fila in filas] == [evento["evento_id"] for evento in EVENTOS]
    assert [fila[8] for fila in filas] == list(range(len(EVENTOS)))
    assert [fila[6] for fila in filas] == ["local", "local", "visita", "local"]
    assert [fila[5] for fila in filas] == [
        "final_partido", "gol", "corner", "final_primer_tiempo",
    ]


def test_almacen_es_idempotente_por_evento_id(tmp_path: Path) -> None:
    """[INV 3] Recargar el mismo partido no duplica ni altera eventos."""
    almacen = _almacen()
    boveda = _boveda(tmp_path / "boveda.db")

    almacen.cargar_eventos(boveda, MATCH_AME_MTY, EVENTOS)
    segunda = almacen.cargar_eventos(boveda, MATCH_AME_MTY, EVENTOS)

    assert segunda["insertados"] == 0
    assert segunda["ignorados"] == len(EVENTOS)
    assert segunda["total_en_tabla"] == len(EVENTOS)
    assert len(_filas_eventos(boveda)) == len(EVENTOS)


def test_almacen_preserva_minuto_texto_y_agregado(tmp_path: Path) -> None:
    """[INV 4] El rótulo literal se conserva; el agregado no se imputa al base."""
    almacen = _almacen()
    boveda = _boveda(tmp_path / "boveda.db")

    almacen.cargar_eventos(boveda, MATCH_AME_MTY, EVENTOS)
    por_id = {fila[0]: fila for fila in _filas_eventos(boveda)}

    assert por_id["111591"][1:4] == ("+1'", None, 1)
    assert por_id["111584"][1:4] == ("78'", 78, None)
    assert por_id["111593"][1:3] == ("MF", None)
    assert por_id["111593"][4] == "MF"


def test_almacen_rechaza_lista_vacia(tmp_path: Path) -> None:
    """[SAD 1] Lista vacía: excepción de dominio y cero escrituras."""
    almacen = _almacen()
    boveda = _boveda(tmp_path / "boveda.db")

    with pytest.raises(almacen.EventoInvalidoError):
        almacen.cargar_eventos(boveda, MATCH_AME_MTY, [])


def test_almacen_rechaza_match_id_inexistente(tmp_path: Path) -> None:
    """[SAD 2] FK inexistente: aborta la transacción sin residuos."""
    almacen = _almacen()
    boveda = _boveda(tmp_path / "boveda.db")

    with pytest.raises(almacen.MatchResolutionError):
        almacen.cargar_eventos(boveda, "fs_no_existe", EVENTOS)

    conexion = sqlite3.connect(boveda)
    try:
        existe = conexion.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='historical_match_events'"
        ).fetchone()[0]
        filas = (
            conexion.execute("SELECT COUNT(*) FROM historical_match_events").fetchone()[0]
            if existe
            else 0
        )
    finally:
        conexion.close()
    assert filas == 0


def test_almacen_rechaza_evento_sin_contrato(tmp_path: Path) -> None:
    """[SAD 3] Evento sin descripción: excepción antes de abrir transacción."""
    almacen = _almacen()
    boveda = _boveda(tmp_path / "boveda.db")
    invalido = [dict(EVENTOS[0], descripcion="")]

    with pytest.raises(almacen.EventoInvalidoError):
        almacen.cargar_eventos(boveda, MATCH_AME_MTY, invalido)


def test_almacen_no_toca_tablas_ajenas(tmp_path: Path) -> None:
    """[INV 5] La carga no altera `historical_matches` ni crea tablas del lado de comando."""
    almacen = _almacen()
    boveda = _boveda(tmp_path / "boveda.db")
    conexion = sqlite3.connect(boveda)
    antes = list(conexion.execute("SELECT * FROM historical_matches ORDER BY match_id"))
    conexion.close()

    almacen.cargar_eventos(boveda, MATCH_AME_MTY, EVENTOS)

    conexion = sqlite3.connect(boveda)
    try:
        despues = list(conexion.execute("SELECT * FROM historical_matches ORDER BY match_id"))
        tablas = {fila[0] for fila in conexion.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        conexion.close()
    assert antes == despues
    assert "matches" not in tablas and "match_telemetry" not in tablas


# ── [ARCH-1.5.1] §15.3 Join Determinista ───────────────────────────────────────────────────
def test_resolucion_match_id_exitosa_y_normalizada(tmp_path: Path) -> None:
    """[INV 6] Temporada y acentos canonizan antes del cruce; la llave es única."""
    almacen = _almacen()
    boveda = _boveda(tmp_path / "boveda.db")

    assert almacen.resolver_match_id(boveda, "2015-2016", "América", "Monterrey", 3, 3) == MATCH_AME_MTY
    assert almacen.resolver_match_id(boveda, "2015_2016", "AMÉRICA", "Monterrey", 3, 3) == MATCH_AME_MTY
    assert almacen.resolver_match_id(boveda, "2015-2016", "Guadalajara", "Atlas", 1, 0) == "fs_2015_2016_z85265"


def test_resolucion_sin_candidatos_falla(tmp_path: Path) -> None:
    """[SAD 4] Cero coincidencias: `MatchResolutionError`, sin aproximación."""
    almacen = _almacen()
    boveda = _boveda(tmp_path / "boveda.db")

    with pytest.raises(almacen.MatchResolutionError, match="0 candidatos"):
        almacen.resolver_match_id(boveda, "2015-2016", "América", "Monterrey", 2, 1)


def test_resolucion_ambigua_falla(tmp_path: Path) -> None:
    """[SAD 5] Más de una coincidencia: `MatchResolutionError` con el conteo."""
    almacen = _almacen()
    filas = list(_FILAS_BOVEDA) + [
        ("fs_2015_2016_z99999", "2015_2016", "América", "Monterrey", "america", "monterrey", 3, 3)
    ]
    boveda = _boveda(tmp_path / "boveda.db", filas)

    with pytest.raises(almacen.MatchResolutionError, match="2 candidatos"):
        almacen.resolver_match_id(boveda, "2015-2016", "América", "Monterrey", 3, 3)


# ── [LN-QBE-145] Diccionario Canónico de Alias ─────────────────────────────────────────────
@pytest.mark.parametrize(
    "pantalla, canonico",
    [
        ("Jaguares", "Chiapas"),
        ("M. Morelia", "Morelia"),
        ("Tigres", "Tigres UANL"),
        ("Tigres de la U.A.N.L.", "Tigres UANL"),
        ("Club Tijuana", "Tijuana"),
        ("Pumas", "Pumas UNAM"),
        ("Puebla F.C.", "Puebla"),
    ],
)
def test_alias_traduce_el_nombre_de_pantalla(pantalla: str, canonico: str) -> None:
    """[INV 12] Los nombres observados del sitio se traducen al nombre de la bóveda."""
    assert _alias().resolver_alias_ligamx(pantalla) == canonico


def test_alias_devuelve_el_original_sin_entrada() -> None:
    """[INV 13] Sin alias no se inventa: se devuelve el nombre original intacto."""
    modulo = _alias()
    assert modulo.resolver_alias_ligamx("América") == "América"
    assert modulo.resolver_alias_ligamx("Nombre Inexistente FC") == "Nombre Inexistente FC"
    assert modulo.resolver_alias_ligamx("") == ""


def test_alias_rechaza_entrada_no_textual() -> None:
    """[SAD 8] Entrada no textual: `TypeError`, sin coacción silenciosa."""
    modulo = _alias()
    for valor in (None, 3, b"Jaguares"):
        with pytest.raises(TypeError):
            modulo.resolver_alias_ligamx(valor)  # type: ignore[arg-type]


def test_alias_canonicos_existen_en_la_boveda() -> None:
    """[INV 14] Todo valor del diccionario es un nombre canónico real de la bóveda."""
    boveda = RAIZ / "qbe_observatory" / "data" / "qbe_historico.db"
    if not boveda.is_file():
        pytest.skip("bóveda no disponible en este entorno")
    modulo = _alias()
    conexion = sqlite3.connect(boveda)
    try:
        nombres = set()
        for local, visitante in conexion.execute(
            "SELECT home_team, away_team FROM historical_matches WHERE temporada = '2015_2016'"
        ):
            nombres.update((local, visitante))
    finally:
        conexion.close()
    assert set(modulo.ALIAS_LIGAMX.values()) <= nombres


# ── [LN-QBE-141] §17.3 Extensión pura desde HTML ───────────────────────────────────────────
def test_parser_desde_html_es_equivalente_al_mhtml() -> None:
    """[INV 7] Misma evidencia por ambas rutas: 49 eventos y sobre idéntico."""
    modulo = _parser()
    assert MHTML_MUESTRA.is_file(), f"Falta el MHTML de muestra: {MHTML_MUESTRA}"

    desde_mhtml = modulo.parsear_partido(MHTML_MUESTRA)
    desde_html = modulo.parsear_partido_desde_html(modulo.extraer_html_de_mhtml(MHTML_MUESTRA))

    assert desde_html == desde_mhtml
    assert len(desde_html["eventos"]) == 49
    assert (desde_html["equipo_local"], desde_html["marcador_local"]) == ("América", 3)
    assert (desde_html["equipo_visitante"], desde_html["marcador_visitante"]) == ("Monterrey", 3)

    with pytest.raises(modulo.MinutoAJugadaError):
        modulo.parsear_partido_desde_html("   ")


# ── [LN-QBE-143] Orquestador ───────────────────────────────────────────────────────────────
def _lote(tmp_path: Path, *, partidos_por_jornada: Dict[int, List[Dict[str, str]]], **kw):
    modulo = _orquestador()
    boveda = kw.pop("boveda", None) or _boveda(tmp_path / "boveda.db")
    descargador = kw.pop("descargador", _DescargadorEspia())
    llamadas: List[tuple] = []

    def descubridor(temporada: str, torneo: str, jornada: str) -> List[Dict[str, str]]:
        llamadas.append((temporada, torneo, jornada))
        return partidos_por_jornada.get(int(jornada), [])

    lote = modulo.ejecutar(
        "2015-2016",
        "Clausura",
        16,
        17,
        db_path=boveda,
        descubridor=descubridor,
        descargador=descargador,
        parser=kw.pop("parser", lambda _html: SOBRE_AME),
        reporte_json=kw.pop("reporte_json", None),
        pausa=kw.pop("pausa", 0.0),
        **kw,
    )
    return lote, boveda, descargador, llamadas


def test_orquestador_itera_todas_las_jornadas_del_rango(tmp_path: Path) -> None:
    """[INV 8] `jornada_inicio..jornada_fin` se recorre sin saltos."""
    partidos = {
        16: [_partido("67047", "América", "Monterrey")],
        17: [_partido("67060", "América", "Monterrey")],
    }
    lote, _, _, llamadas = _lote(tmp_path, partidos_por_jornada=partidos)

    assert [llamada[2] for llamada in llamadas] == ["16", "17"]
    assert [registro.jornada for registro in lote.registros] == [16, 17]
    assert lote.resumen()["jornadas"] == 2


def test_orquestador_invoca_la_sonda_con_argumentos_exactos(tmp_path: Path) -> None:
    """[INV 9] La Sonda recibe temporada, torneo y jornada textual."""
    lote, _, _, llamadas = _lote(tmp_path, partidos_por_jornada={16: [_partido("67047", "América", "Monterrey")]})

    assert llamadas == [
        ("2015-2016", "Clausura", "16"),
        ("2015-2016", "Clausura", "17"),
    ]
    assert all(isinstance(llamada[2], str) for llamada in llamadas)
    assert lote.fallos_jornada == []
    assert [registro.estado for registro in lote.registros] == ["OK"]


def test_orquestador_parser_y_persistidor_reciben_el_partido(tmp_path: Path) -> None:
    """[INV 10] HTML → Parser; sobre → `match_id`; eventos → bóveda; bitácora."""
    descargador = _DescargadorEspia(html="<html>jornada 16</html>")
    vistos: List[str] = []
    reporte = tmp_path / "reporte.json"

    def parser(html: str) -> Dict[str, Any]:
        vistos.append(html)
        return SOBRE_AME

    lote, boveda, _, _ = _lote(
        tmp_path,
        partidos_por_jornada={16: [_partido("67047", "América", "Monterrey")]},
        descargador=descargador,
        parser=parser,
        reporte_json=reporte,
    )
    registro = lote.registros[0]

    assert vistos == ["<html>jornada 16</html>"]
    assert descargador.llamadas == ["https://ligamx.net/cancha/mxm/67047/pestana"]
    assert (registro.estado, registro.match_id) == ("OK", MATCH_AME_MTY)
    assert (registro.eventos, registro.insertados) == (len(EVENTOS), len(EVENTOS))
    assert len(_filas_eventos(boveda)) == len(EVENTOS)

    documento = json.loads(reporte.read_text(encoding="utf-8"))
    assert documento["resumen"]["ok"] == 1
    assert documento["resumen"]["eventos_insertados"] == len(EVENTOS)
    assert documento["registros"][0]["match_id"] == MATCH_AME_MTY


def test_orquestador_fail_loud_continua_y_reporta_fallos(tmp_path: Path) -> None:
    """[SAD 6] Un partido falla, el siguiente se procesa y el fallo se declara."""
    partidos = {
        16: [
            _partido("67047", "América", "Monterrey"),
            _partido("67048", "Guadalajara", "Atlas"),
        ]
    }
    descargador = _DescargadorEspia(fallos=("https://ligamx.net/cancha/mxm/67047/pestana",))
    lote, boveda, _, _ = _lote(tmp_path, partidos_por_jornada=partidos, descargador=descargador)

    fallido, exitoso = lote.registros
    assert (fallido.estado, fallido.error_tipo) == ("FALLO", "RuntimeError")
    assert "descarga simulada fallida" in fallido.error
    assert (exitoso.estado, exitoso.match_id) == ("OK", MATCH_AME_MTY)
    resumen = lote.resumen()
    assert (resumen["partidos"], resumen["ok"], resumen["fallidos"]) == (2, 1, 1)
    assert resumen["eventos_insertados"] == len(EVENTOS)
    assert len(_filas_eventos(boveda)) == len(EVENTOS)


def test_orquestador_fallo_de_jornada_no_aborta_el_lote(tmp_path: Path) -> None:
    """[SAD 7] Una jornada irresoluble se registra y el lote continúa."""
    modulo = _orquestador()
    boveda = _boveda(tmp_path / "boveda.db")

    def descubridor(temporada: str, torneo: str, jornada: str) -> List[Dict[str, str]]:
        if jornada == "16":
            raise RuntimeError("cartelera no disponible")
        return [_partido("67060", "América", "Monterrey")]

    lote = modulo.ejecutar(
        "2015-2016", "Clausura", 16, 17,
        db_path=boveda,
        descubridor=descubridor,
        descargador=_DescargadorEspia(),
        parser=lambda _html: SOBRE_AME,
    )

    assert lote.fallos_jornada == [
        {"jornada": 16, "error_tipo": "RuntimeError", "error": "cartelera no disponible"}
    ]
    assert [registro.estado for registro in lote.registros] == ["OK"]
    assert lote.resumen()["fallidos"] == 1


def test_orquestador_cli_emite_codigos_de_salida(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """[INV 11] `main` devuelve 0 limpio, 1 con fallos y 2 si el lote estalla."""
    modulo = _orquestador()
    argumentos = [
        "--temporada", "2015-2016", "--torneo", "Clausura",
        "--jornada_inicio", "16", "--jornada_fin", "16",
    ]

    limpio = modulo.ResultadoLote("2015-2016", "Clausura", 16, 16)
    limpio.registros.append(
        modulo.RegistroPartido(
            16, "67047", "América", "Monterrey", "url",
            estado="OK", eventos=4, insertados=4,
        )
    )
    monkeypatch.setattr(modulo, "ejecutar", lambda *a, **k: limpio)
    assert modulo.main(argumentos) == 0

    con_fallo = modulo.ResultadoLote("2015-2016", "Clausura", 16, 16)
    con_fallo.registros.append(
        modulo.RegistroPartido(
            16, "67047", "América", "Monterrey", "url",
            estado="FALLO", error_tipo="RuntimeError", error="boom",
        )
    )
    monkeypatch.setattr(modulo, "ejecutar", lambda *a, **k: con_fallo)
    assert modulo.main(argumentos) == 1

    def estalla(*_a: Any, **_k: Any) -> Any:
        raise RuntimeError("sin navegador")

    monkeypatch.setattr(modulo, "ejecutar", estalla)
    assert modulo.main(argumentos) == 2
    assert "sin navegador" in capsys.readouterr().err

@pytest.mark.parametrize(
    "local_pantalla, visita_pantalla, goles, esperado",
    [
        ("Jaguares", "Atlas", (0, 3), "fs_2015_2016_z85271"),
        ("M. Morelia", "Santos Laguna", (3, 2), "fs_2015_2016_z85272"),
        ("Tigres", "Veracruz", (0, 0), "fs_2015_2016_z85273"),
        ("Club Tijuana", "Puebla F.C.", (0, 0), "fs_2015_2016_z85274"),
        ("Querétaro", "Pumas", (2, 1), "fs_2015_2016_z85275"),
    ],
)
def test_orquestador_resuelve_los_cinco_alias_contra_la_boveda(
    tmp_path: Path,
    local_pantalla: str,
    visita_pantalla: str,
    goles: tuple,
    esperado: str,
) -> None:
    """[INV 15] El orquestador canoniza el sobre y el Join resuelve los 5 partidos."""
    modulo = _orquestador()
    boveda = _boveda(tmp_path / "boveda.db", _FILAS_ALIAS)
    sobre = {
        "equipo_local": local_pantalla,
        "equipo_visitante": visita_pantalla,
        "marcador_local": goles[0],
        "marcador_visitante": goles[1],
        "eventos": EVENTOS,
    }
    lote = modulo.ejecutar(
        "2015-2016", "Clausura", 16, 16,
        db_path=boveda,
        descubridor=lambda *_a: [_partido("99999", local_pantalla, visita_pantalla)],
        descargador=_DescargadorEspia(),
        parser=lambda _html: sobre,
    )

    registro = lote.registros[0]
    assert (registro.estado, registro.match_id) == ("OK", esperado)
    assert registro.error is None
    assert len(_filas_eventos(boveda, esperado)) == len(EVENTOS)
    assert lote.resumen()["fallidos"] == 0

def test_orquestador_checkpoint_registra_avance_y_resume_omite(tmp_path: Path) -> None:
    """[INV 16] El checkpoint guarda el avance y `resume` omite lo ya persistido."""
    boveda = _boveda(tmp_path / "boveda.db")
    checkpoint = tmp_path / "checkpoint.json"
    partidos = {16: [_partido("67047", "América", "Monterrey")]}

    primero, _, _, _ = _lote(
        tmp_path,
        partidos_por_jornada=partidos,
        boveda=boveda,
        checkpoint=str(checkpoint),
        resume=False,
    )
    assert primero.resumen()["ok"] == 1

    estado = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert estado["temporada"] == "2015-2016"
    assert estado["torneo"] == "Clausura"
    assert estado["ultimo_partido"]["id_partido"] == "67047"
    assert estado["ultimo_partido"]["estado"] == "OK"
    assert "2015-2016|Clausura|67047" in estado["completados"]

    segundo, _, _, _ = _lote(
        tmp_path,
        partidos_por_jornada=partidos,
        boveda=boveda,
        checkpoint=str(checkpoint),
        resume=True,
    )
    assert segundo.omitidos == 1
    assert segundo.registros == []
    assert segundo.resumen()["ok"] == 0


def test_orquestador_resume_reintenta_los_fallidos(tmp_path: Path) -> None:
    """[INV 17] Un partido en FALLO no se marca completado: `resume` lo reintenta."""
    boveda = _boveda(tmp_path / "boveda.db")
    checkpoint = tmp_path / "checkpoint.json"
    partidos = {16: [_partido("67047", "América", "Monterrey")]}
    url = "https://ligamx.net/cancha/mxm/67047/pestana"

    caido, _, _, _ = _lote(
        tmp_path,
        partidos_por_jornada=partidos,
        boveda=boveda,
        descargador=_DescargadorEspia(fallos=(url,)),
        checkpoint=str(checkpoint),
    )
    assert caido.registros[0].estado == "FALLO"
    assert json.loads(checkpoint.read_text(encoding="utf-8"))["completados"] == []

    sano, _, _, _ = _lote(
        tmp_path,
        partidos_por_jornada=partidos,
        boveda=boveda,
        checkpoint=str(checkpoint),
        resume=True,
    )
    assert sano.omitidos == 0
    assert sano.registros[0].estado == "OK"
    assert json.loads(checkpoint.read_text(encoding="utf-8"))["completados"]
