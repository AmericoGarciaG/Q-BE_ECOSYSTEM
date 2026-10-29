# -*- coding: utf-8 -*-
"""
🛡️ THE SHIELD — TWIN-TEST: CONTRACCIÓN BARICÉNTRICA Y ASIGNACIÓN MONÓTONA DE CAPITAL
[LN-QBE-079, LN-QBE-081, LN-QBE-082] & [ARCH-1.4.17, ARCH-1.4.18]
Régimen: [DIRGEN-STRICT]
Axioma: Conservación estricta del símplex bajo contracción y jerarquía no creciente de capital.
Nota de trazabilidad: el bloque fue inyectado como [LN-QBE-080]/[LN-QBE-081] y remapeado a
[LN-QBE-081]/[LN-QBE-082] por colisión con el nodo sellado [LN-QBE-080] (Compilador PDF A4).
Ver VAR-HIST-080-COLLISION
"""

import pytest
from abc import ABC, abstractmethod


class AbstractTestFiduciaryShrinkageAndMonotonicOrdering(ABC):
    """Juez Abstracto que audita el operador de contracción baricéntrica y el ordenamiento monótono."""

    def test_invarianza_simplex_contraccion_baricentrica(self):
        """Verifica que la contracción preserve estrictamente la suma 1.0 en todo el dominio."""
        from src.core.contracts.portfolio_math import contraer_distribucion_fiduciaria

        # Caso 1: Certeza perfecta (Delta = 0.0) -> No se altera la distribución
        pl, pe, pv = contraer_distribucion_fiduciaria(0.60, 0.25, 0.15, delta_epist=0.00)
        assert abs((pl + pe + pv) - 1.0) <= 1e-4
        assert pl == 0.60

        # Caso 2: Incertidumbre crítica (Delta >= 0.12) -> Colapso total al baricentro (1/3, 1/3, 1/3)
        pl_c, pe_c, pv_c = contraer_distribucion_fiduciaria(0.75, 0.15, 0.10, delta_epist=0.13)
        assert abs((pl_c + pe_c + pv_c) - 1.0) <= 1e-4
        assert abs(pl_c - 0.3333) <= 1e-3

        # Caso 3: Fricción intermedia (Delta = 0.08 -> Psi = 0.5556) -> Contracción suave
        pl_m, pe_m, pv_m = contraer_distribucion_fiduciaria(0.60, 0.25, 0.15, delta_epist=0.08)
        assert abs((pl_m + pe_m + pv_m) - 1.0) <= 1e-4
        assert pl_m < 0.60
        assert pl_m > 0.45

    def test_probabilidad_exito_por_estrategia(self):
        """Verifica que H1/H2 sumen victoria + empate, y D1/D2 tomen solo la victoria."""
        from src.core.contracts.portfolio_math import calcular_probabilidad_exito_estrategia

        # H1 con p_fav=0.50 y p_emp=0.25 -> Exito = 0.75 (75%)
        assert calcular_probabilidad_exito_estrategia("QBE-H1", 0.50, 0.25) == 0.7500
        # D1 con p_fav=0.68 -> Exito = 0.68 (68%)
        assert calcular_probabilidad_exito_estrategia("QBE-D1", 0.68, 0.18) == 0.6800

    def test_ordenamiento_lexicografico_exito_antes_que_ganancia(self):
        """Verifica que la certeza lidere el ordenamiento por encima de una ganancia mayor pero volada."""
        from src.core.contracts.portfolio_math import ordenar_cartera_por_certeza_lexicografica

        partidos = [
            {"id": "PUMAS_VOLADO", "prob_exito_efectiva": 0.45, "ganancia_neta": 15.00},
            {"id": "PACHUCA_SEGURO", "prob_exito_efectiva": 0.68, "ganancia_neta": 2.50},
            {"id": "AMERICA_MEDIO", "prob_exito_efectiva": 0.58, "ganancia_neta": 8.00},
        ]

        ordenados = ordenar_cartera_por_certeza_lexicografica(partidos)
        assert ordenados[0]["id"] == "PACHUCA_SEGURO"  # Máxima certeza arriba
        assert ordenados[1]["id"] == "AMERICA_MEDIO"
        assert ordenados[2]["id"] == "PUMAS_VOLADO"   # Volado con gran ganancia abajo

    def test_asignacion_capital_monotona_no_creciente(self):
        """Verifica que el capital asignado disminuya o sea igual conforme baja la probabilidad de éxito."""
        from src.core.contracts.portfolio_math import asignar_capital_monotono_cartera

        bankroll = 200.0  # 8% cap = 16.00, 25% global = 50.00
        partidos = [
            {"id": "P1", "prob_exito_efectiva": 0.75},
            {"id": "P2", "prob_exito_efectiva": 0.68},
            {"id": "P3", "prob_exito_efectiva": 0.55},
            {"id": "P4", "prob_exito_efectiva": 0.48}
        ]

        asignados = asignar_capital_monotono_cartera(partidos, bankroll)

        # 1. Monotonía estricta: B_1 >= B_2 >= B_3 >= B_4
        for i in range(len(asignados) - 1):
            assert asignados[i]["inversion_total"] >= asignados[i+1]["inversion_total"], \
                f"Violación LN-QBE-082: Inversión en {asignados[i]['id']} ({asignados[i]['inversion_total']}) < que {asignados[i+1]['id']} ({asignados[i+1]['inversion_total']})"

        # 2. Hard-Caps respetados
        assert all(p["inversion_total"] <= 16.01 for p in asignados)
        assert sum(p["inversion_total"] for p in asignados) <= 50.08


class TestFiduciaryShrinkageAndMonotonicOrdering(AbstractTestFiduciaryShrinkageAndMonotonicOrdering):
    """Implementación concreta en The Shield."""
    pass
