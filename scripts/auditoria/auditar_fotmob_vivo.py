# -*- coding: utf-8 -*-
"""Sonda E2 — Auditoría FotMob en vivo de las 32 variables pre-kickoff.

Consulta el próximo partido `PROGRAMADO` de la bóveda canónica y ejecuta el
Centinela Macro contra FotMob (`tab=stats`). Imprime, variable por variable
(V01–V32), el dato local/visita disponible antes del kickoff y declara las
variables que FotMob no publica (`FUERA DE FUENTE`).

Solo lectura: no escribe el artefacto ni la bóveda.
"""

from __future__ import annotations

import json
import sqlite3
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

RAIZ = Path(__file__).resolve().parents[2]
BOVEDA = RAIZ / "data" / "qbe_database.db"
CACHE = RAIZ / "data" / "cache_macro_stats_liga_mx_2026.json"
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.ingestion.daemons.centinela_macro import (  # noqa: E402
    COBERTURA_FUERA_DE_FUENTE,
    DERIVACIONES,
    LIGA_FOTMOB_ID_DEFAULT,
    MAPA_LEADERBOARDS,
    construir_artefacto,
)

VARIABLES = [f"V{indice:02d}" for indice in range(1, 33)]


def _partido_proximo() -> Tuple[Dict[str, Any], int]:
    conexion = sqlite3.connect(f"file:{BOVEDA.as_posix()}?mode=ro", uri=True, timeout=5.0)
    try:
        filas = conexion.execute(
            "SELECT matchday, matches_json FROM fixtures_snapshots ORDER BY matchday"
        ).fetchall()
    finally:
        conexion.close()

    candidatos: List[Tuple[str, int, Dict[str, Any]]] = []
    for jornada, crudo in filas:
        try:
            partidos = json.loads(crudo) if crudo else []
        except (TypeError, ValueError):
            continue
        for partido in partidos:
            if str(partido.get("estado") or "").upper() != "PROGRAMADO":
                continue
            fecha = str(partido.get("fecha_dt") or "")
            candidatos.append((fecha, int(jornada), partido))
    if not candidatos:
        raise RuntimeError("La bóveda canónica no registra partidos PROGRAMADO.")
    ahora_iso = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    futuros = [item for item in candidatos if item[0] and item[0] >= ahora_iso]
    seleccion = futuros or candidatos
    seleccion.sort(key=lambda item: (item[0], item[1]))
    _fecha, jornada, partido = seleccion[0]
    return partido, jornada


def _cargar_artefacto() -> Tuple[Dict[str, Any], bool]:
    try:
        artefacto = construir_artefacto(
            liga_id=LIGA_FOTMOB_ID_DEFAULT,
            espera=0.05,
            verbose=False,
        )
        return artefacto, True
    except Exception:
        print("[FALLBACK] La extracción viva falló; se usa el artefacto congelado:")
        print(traceback.format_exc())
        return json.loads(CACHE.read_text(encoding="utf-8")), False


def _fuentes_por_variable() -> Dict[str, List[Tuple[str, str, str]]]:
    fuentes: Dict[str, List[Tuple[str, str, str]]] = {}
    for entrada in MAPA_LEADERBOARDS:
        variable = str(entrada["variable"])
        if not variable.startswith("V"):
            continue
        fuentes.setdefault(variable, []).append(
            (str(entrada["clave"]), str(entrada["board"]), str(entrada["normalizacion"]))
        )
    for derivacion in DERIVACIONES:
        fuentes.setdefault(str(derivacion["variable"]), []).append(
            (str(derivacion["clave"]), "derivación declarada", "derivada")
        )
    return fuentes


def _formatear(valor: Any) -> str:
    if valor is None:
        return "—"
    if isinstance(valor, float):
        return f"{valor:.3f}"
    return str(valor)


def main() -> int:
    partido, jornada = _partido_proximo()
    local = str(partido.get("local") or "?")
    visita = str(partido.get("visitante") or "?")
    slug_local = str(partido.get("home_team_slug") or "")
    slug_visita = str(partido.get("away_team_slug") or "")

    artefacto, vivo = _cargar_artefacto()
    artefacto.setdefault(
        "generado_at",
        datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    )
    if not artefacto.get("hash_sha256"):
        import hashlib

        cuerpo = json.dumps(
            {
                clave: valor
                for clave, valor in artefacto.items()
                if clave not in ("generado_at", "hash_sha256")
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        artefacto["hash_sha256"] = hashlib.sha256(cuerpo.encode("utf-8")).hexdigest()
    equipo_local = (artefacto.get("equipos") or {}).get(slug_local) or {}
    equipo_visita = (artefacto.get("equipos") or {}).get(slug_visita) or {}
    fuentes = _fuentes_por_variable()

    print("=" * 96)
    print("AUDITORÍA FOTMOB VIVO — 32 VARIABLES PRE-KICKOFF")
    print("=" * 96)
    print(f"Partido   : {local} vs {visita}  (Jornada {jornada})")
    print(f"Fecha     : {partido.get('fecha_dt') or '—'}")
    print(f"Slugs     : {slug_local or '—'} / {slug_visita or '—'}")
    print(f"Liga      : {(artefacto.get('liga') or {}).get('nombre')} · {(artefacto.get('liga') or {}).get('temporada_seleccionada')}")
    print(f"Fuente    : {'FotMob EN VIVO' if vivo else 'artefacto congelado (fallback)'}")
    print(f"Equipos   : {len(artefacto.get('equipos') or {})} · huecos: {len(artefacto.get('huecos') or [])} · errores: {len(artefacto.get('errores') or [])}")
    print("-" * 96)
    print(f"{'VAR':<5} {'FUENTE':<34} {'LOCAL':<20} {'VISITA':<20} {'ESTADO':<14}")
    print("-" * 96)

    con_dato = 0
    sin_evidencia = 0
    fuera = 0
    for variable in VARIABLES:
        if variable in COBERTURA_FUERA_DE_FUENTE:
            fuera += 1
            motivo = COBERTURA_FUERA_DE_FUENTE[variable]
            print(f"{variable:<5} {'FUERA DE FUENTE':<34} {'—':<20} {'—':<20} {'FUERA':<14}")
            print(f"      motivo: {motivo}")
            continue

        entradas = fuentes.get(variable, [])
        valores_local = []
        valores_visita = []
        for clave, _tablero, _norm in entradas:
            if equipo_local.get(clave) is not None:
                valores_local.append(f"{clave}={_formatear(equipo_local.get(clave))}")
            if equipo_visita.get(clave) is not None:
                valores_visita.append(f"{clave}={_formatear(equipo_visita.get(clave))}")
        fuente = ", ".join(sorted({tablero for _clave, tablero, _norm in entradas}))
        estado = "DATO" if (valores_local or valores_visita) else "SIN EVIDENCIA"
        if estado == "DATO":
            con_dato += 1
        else:
            sin_evidencia += 1
        print(
            f"{variable:<5} {fuente[:33]:<34} "
            f"{(', '.join(valores_local) or '—')[:19]:<20} "
            f"{(', '.join(valores_visita) or '—')[:19]:<20} {estado:<14}"
        )

    print("-" * 96)
    print(
        f"RESUMEN: con_dato={con_dato} | sin_evidencia={sin_evidencia} | "
        f"fuera_de_fuente={fuera} | total={len(VARIABLES)}"
    )
    print(f"ARTEFACTO: generado_at={artefacto.get('generado_at', '—')} · hash={str(artefacto.get('hash_sha256') or '—')[:16]}")
    print("=" * 96)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
