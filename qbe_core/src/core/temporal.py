# Q-BE Casino Deportes — Temporal Decay Engine (src/core/temporal.py)
"""
[LN-QBE-020] Operador de Decaimiento Temporal Acelerado en H2H (kappa-Decay).
[BIZ-LOGIC] [ALGO-PROTECTED] Ponderación exponencial continua con vida media tau = 180 días.
Calcula la serie temporal de enfrentamientos directos preservando el simplex estocástico.
"""

import math
from typing import List, Optional
from src.models.raw_input import H2HMatchRaw
from src.models.analytics import H2HDecayResult


class TemporalDecayEngine:
    TAU_HALF_LIFE_DAYS = 180.0
    KAPPA = math.log(2.0) / TAU_HALF_LIFE_DAYS  # ~0.0038509775

    @classmethod
    def compute_decay(
        cls,
        h2h_matches: List[H2HMatchRaw],
        local: str,
        vis: str,
        fav: str
    ) -> H2HDecayResult:
        """
        Calcula las probabilidades ponderadas por decaimiento exponencial para 5 partidos H2H.
        Invarianza: p_fav + p_emp + p_und == 1.0000.
        """
        if not h2h_matches:
            # [LN-QBE-020-B] LEY ZERO-H2H: Sin antecedentes reales, retornar resultado neutro.
            # La antigüedad de 9999 días activa la guarda w_h2h=0.0 en poisson.py.
            return H2HDecayResult(
                p_fav=0.3333, p_emp=0.3333, p_und=0.3334,
                gf_h2h_local=0.0, gf_h2h_visita=0.0,
                antiguedad_promedio_dias=9999.0
            )

        if len(h2h_matches) != 5:
            raise ValueError(f"H2H requiere exactamente 5 partidos (recibidos: {len(h2h_matches)})")

        fav_norm = fav.strip().lower()
        local_norm = local.strip().lower()
        vis_norm = vis.strip().lower()

        weights = []
        outcomes = []  # "FAV", "EMP", "UND"
        gf_local_list = []
        gf_vis_list = []

        total_dias = 0.0

        for m in h2h_matches:
            w_i = math.exp(-cls.KAPPA * m.dias_transcurridos)
            weights.append(w_i)
            total_dias += m.dias_transcurridos

            # Determinar goles si hay marcador disponible
            gl, gv = None, None
            if m.marcador and "-" in m.marcador:
                try:
                    parts = m.marcador.split("-")
                    gl, gv = int(parts[0].strip()), int(parts[1].strip())
                except (ValueError, IndexError):
                    gl, gv = None, None

            # Asignar goles históricos según localía del partido histórico
            if gl is not None and gv is not None and m.local_real and m.visitante_real:
                loc_real_norm = m.local_real.strip().lower()
                vis_real_norm = m.visitante_real.strip().lower()
                if loc_real_norm == local_norm:
                    gf_local_list.append(gl)
                elif vis_real_norm == local_norm:
                    gf_local_list.append(gv)

                if loc_real_norm == vis_norm:
                    gf_vis_list.append(gl)
                elif vis_real_norm == vis_norm:
                    gf_vis_list.append(gv)

            # Clasificar desenlace
            outcome = cls._classify_outcome(m, fav_norm, gl, gv)
            outcomes.append(outcome)

        w_total = sum(weights)
        if w_total <= 0.0:
            raise ValueError("Suma de pesos H2H inválida")

        w_fav = sum(w for w, o in zip(weights, outcomes) if o == "FAV")
        w_emp = sum(w for w, o in zip(weights, outcomes) if o == "EMP")
        w_und = sum(w for w, o in zip(weights, outcomes) if o == "UND")

        p_fav = w_fav / w_total
        p_emp = w_emp / w_total
        p_und = w_und / w_total

        # Preservar simplex numérico
        total_p = p_fav + p_emp + p_und
        if total_p > 0:
            p_fav /= total_p
            p_emp /= total_p
            p_und /= total_p

        antiguedad_promedio = total_dias / 5.0
        gf_h2h_local = sum(gf_local_list) / len(gf_local_list) if gf_local_list else 0.0
        gf_h2h_visita = sum(gf_vis_list) / len(gf_vis_list) if gf_vis_list else 0.0

        return H2HDecayResult(
            p_fav=p_fav,
            p_emp=p_emp,
            p_und=p_und,
            antiguedad_promedio_dias=antiguedad_promedio,
            gf_h2h_local=gf_h2h_local,
            gf_h2h_visita=gf_h2h_visita
        )

    @classmethod
    def _classify_outcome(cls, m: H2HMatchRaw, fav_norm: str, gl: Optional[int], gv: Optional[int]) -> str:
        # Prioridad 1: Marcador explícito
        if gl is not None and gv is not None:
            if gl == gv:
                return "EMP"
            winner_is_loc = gl > gv
            winner_team = m.local_real if winner_is_loc else m.visitante_real
            if winner_team and winner_team.strip().lower() == fav_norm:
                return "FAV"
            return "UND"

        # Prioridad 2: resultado_qbe ("1", "X", "2")
        if m.resultado_qbe:
            res_str = m.resultado_qbe.strip().upper()
            if res_str == "X":
                return "EMP"
            if res_str == "1":
                if m.local_real and m.local_real.strip().lower() == fav_norm:
                    return "FAV"
                return "UND"
            if res_str == "2":
                if m.visitante_real and m.visitante_real.strip().lower() == fav_norm:
                    return "FAV"
                return "UND"

        return "EMP"