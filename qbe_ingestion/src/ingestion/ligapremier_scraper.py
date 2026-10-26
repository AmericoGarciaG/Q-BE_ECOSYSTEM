# -*- coding: utf-8 -*-
"""
🏆 Q-BE CD WEB — SENSOR OFICIAL DE LIGA PREMIER FMF (src/ingestion/ligapremier_scraper.py)
[ARCH-1.4.23] Ingesta de Estadísticas Oficiales, Tabla General y Marcadores desde ligapremier.mx.
Régimen: [DBBD-FUNGIBLE] (Ingesta / Parsing — CERO matemática protegida).
Degradación explícita [GOVERNANCE-01]: filas malformadas se ignoran y se registran en log; el sensor
JAMÁS inventa clubes ni identidades sintéticas.
"""

import re
import logging
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session

logger = logging.getLogger("LigaPremierScraper")

# [ARCH-1.4.23] Fuente oficial de la Segunda División / Liga Premier FMF.
URL_ESTADISTICAS_PREMIER = "https://ligapremier.mx/estadisticas"


class LigaPremierScraper:
    """Sensor de Ingesta para la Segunda División / Liga Premier FMF Oficial."""

    @classmethod
    def parsear_tabla_estadisticas_html(cls, html_str: str) -> List[Dict[str, Any]]:
        """
        [ARCH-1.4.23] Extrae la tabla de posiciones oficial: JJ, G, E, P, GF, GC, PTS.
        Tolerante a selectores HTML o parseo regex de celdas <tr><td>.
        """
        standings = []
        if not html_str:
            return standings

        # Patrón robusto para filas de tabla de estadísticas de ligapremier.mx
        # <tr><td>POS</td><td>CLUB</td><td>JJ</td><td>G</td><td>E</td><td>P</td><td>GF</td><td>GC</td><td>PTS</td></tr>
        filas = re.findall(r'<tr[^>]*>(.*?)</tr>', html_str, re.DOTALL | re.IGNORECASE)

        for fila in filas:
            celdas = re.findall(r'<td[^>]*>(.*?)</td>', fila, re.DOTALL | re.IGNORECASE)
            # Limpiar etiquetas HTML internas de cada celda (como <a> o <img>)
            celdas_limpias = [re.sub(r'<[^>]+>', '', c).strip() for c in celdas if re.sub(r'<[^>]+>', '', c).strip()]

            # Una fila válida de estadísticas tiene al menos 8 columnas numéricas y el nombre del club
            if len(celdas_limpias) >= 8:
                try:
                    # Detectar cuál celda es el nombre del club (cadena no numérica de longitud > 2)
                    nombre_club = None
                    pos_num = 0
                    idx_inicio = 0

                    if celdas_limpias[0].isdigit():
                        pos_num = int(celdas_limpias[0])
                        nombre_club = celdas_limpias[1]
                        idx_inicio = 2
                    else:
                        nombre_club = celdas_limpias[0]
                        idx_inicio = 1

                    nums = [int(c) for c in celdas_limpias[idx_inicio:] if c.isdigit() or (c.startswith('-') and c[1:].isdigit())]

                    if len(nums) >= 6 and nombre_club:
                        # Estructura: JJ, G, E, P, GF, GC, PTS
                        jj = nums[0]
                        g = nums[1]
                        e = nums[2]
                        p = nums[3]
                        gf = nums[4]
                        gc = nums[5]
                        pts = nums[6] if len(nums) > 6 else (g * 3 + e)

                        standings.append({
                            "pos": pos_num,
                            "nombre": nombre_club,
                            "jj": jj,
                            "g": g,
                            "e": e,
                            "p": p,
                            "gf": gf,
                            "gc": gc,
                            "pts": pts
                        })
                except Exception as ex:
                    logger.debug("Fila ignorada en tabla premier: %s (%s)", celdas_limpias, ex)

        return standings

    @classmethod
    def registrar_competicion_ligapremier(cls, session: Session) -> Any:
        """
        [ARCH-1.4.23] Responsabilidad 3: auto-registro de la competición `MEX_LIGAPREMIER` en SQLite 3NF
        con μ_premier = 2.45 y γ̄_home = 0.16.

        Delegación ÍNTEGRA en el helper canónico sellado `registrar_liga_descubierta_si_no_existe()`
        [ARCH-1.4.21 / LN-QBE-089]: cero lógica paralela de persistencia, cero SQL local.
        El efecto es IDEMPOTENTE (si la competición ya existe por `fotmob_id`, se devuelve la fila viva).
        """
        from src.ingestion.progol_resolver import registrar_liga_descubierta_si_no_existe

        return registrar_liga_descubierta_si_no_existe(session, {
            "fotmob_league_id": 9991,
            "league_name": "Liga Premier FMF",
            "country": "Mexico",
            "mu_liga": 2.45,
        })
