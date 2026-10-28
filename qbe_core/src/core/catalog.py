# Q-BE Casino Deportes — Strategy Catalog (src/core/catalog.py)
"""
Catálogo Canónico Inmutable de Estrategias Q-BE.
[LN-QBE-060] [ARCH-PILLAR] [BIZ-LOGIC] [ALGO-PROTECTED]
Única Fuente de Verdad para las 9 Estrategias Oficiales + Veto + Satélite.
"""

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class StrategyDefinition:
    codigo: str
    nombre_oficial: str
    descripcion_ejecutiva: str
    familia: str
    requiere_triple_candado_factico: bool
    formula_ev: str
    rol_boleto_1: str
    rol_boleto_2: str


STRATEGY_CATALOG: Dict[str, StrategyDefinition] = {
    "QBE-D1": StrategyDefinition(
        codigo="QBE-D1",
        nombre_oficial="Favorito Directo Puro",
        descripcion_ejecutiva="Victoria directa del Favorito sin cobertura de tablas (Alta convicción estadística)",
        familia="D",
        requiere_triple_candado_factico=False,
        formula_ev="EV = P_Fav * (O_Fav - 1.0) - (1.0 - P_Fav)",
        rol_boleto_1="N/A ($0.00)",
        rol_boleto_2="Gana Favorito"
    ),
    "QBE-D1+": StrategyDefinition(
        codigo="QBE-D1+",
        nombre_oficial="Favorito Directo Potenciado",
        descripcion_ejecutiva="Victoria del Favorito con liquidación temprana al sacar ventaja de +2 goles",
        familia="D",
        requiere_triple_candado_factico=False,
        formula_ev="EV = [P_Fav * (O_Fav - 1.0)] - [(1.0 - P_Fav) * 1.08]",
        rol_boleto_1="N/A ($0.00)",
        rol_boleto_2="Gana Favorito + Pago Anticipado"
    ),
    "QBE-H1": StrategyDefinition(
        codigo="QBE-H1",
        nombre_oficial="Favorito con Seguro en Empate",
        descripcion_ejecutiva="Búsqueda de ganancia en el Favorito, con recuperación del 100% de la inversión (Tablas) si el juego empata",
        familia="H",
        requiere_triple_candado_factico=False,
        formula_ev="EV = [P_Fav * ROI_Neto] - Psi_Ruina",
        rol_boleto_1="Seguro en Empate (Recuperación)",
        rol_boleto_2="Ganancia en Favorito"
    ),
    "QBE-H1+": StrategyDefinition(
        codigo="QBE-H1+",
        nombre_oficial="Favorito Potenciado con Seguro",
        descripcion_ejecutiva="Búsqueda de ganancia en el Favorito con Pago Anticipado (+2 goles) y recuperación total en empate",
        familia="H",
        requiere_triple_candado_factico=False,
        formula_ev="EV = [(P_Fav + Phi_Lead2 * P_Emp) * ROI_Neto] - Psi_Ruina",
        rol_boleto_1="Seguro en Empate (Recuperación)",
        rol_boleto_2="Ganancia en Favorito + Pago Anticipado"
    ),
    "QBE-H2": StrategyDefinition(
        codigo="QBE-H2",
        nombre_oficial="Favorito Visitante con Cobertura en Tablas (V=0)",
        descripcion_ejecutiva="Monetiza la superioridad del favorito foráneo protegiendo el 100% de la inversión ante la fricción territorial del empate en cancha ajena.",
        familia="H",
        requiere_triple_candado_factico=False,
        formula_ev="EV = [P_Visita * ROI_Neto] - Psi_Ruina",
        rol_boleto_1="Seguro en Empate (Recuperación V=0)",
        rol_boleto_2="Ganancia en Favorito Visitante (+PA)"
    ),
    "QBE-H2+": StrategyDefinition(
        codigo="QBE-H2+",
        nombre_oficial="Freeroll Doble Impacto (Joya)",
        descripcion_ejecutiva="Búsqueda de ganancia en el Favorito Visitante con Seguro en Empate (Doble cobro si el favorito foráneo saca 2 goles y el juego concluye empatado)",
        familia="H",
        requiere_triple_candado_factico=False,
        formula_ev="EV = [(Phi_Lead2 * P_Emp) * (ROI_Neto + 1.0)] + [(P_Emp * (1 - Phi_Lead2)) * ROI_Neto] - Psi_Ruina",
        rol_boleto_1="Seguro en Empate (Recuperación V=0) + Pago Anticipado",
        rol_boleto_2="Ganancia en Favorito Visitante + Pago Anticipado"
    ),
    "QBE-R1": StrategyDefinition(
        codigo="QBE-R1",
        nombre_oficial="Asalto al No-Favorito con Seguro en Empate",
        descripcion_ejecutiva="Búsqueda de ganancia en el No-Favorito ante cuotas infladas, con recuperación del 100% de la inversión (Tablas) en empate",
        familia="R",
        requiere_triple_candado_factico=True,
        formula_ev="EV = [P_Und * ROI_Und_Neto] - P_Fav",
        rol_boleto_1="Seguro en Empate (Recuperación)",
        rol_boleto_2="Ganancia en Underdog + Pago Anticipado"
    ),
    "QBE-R2": StrategyDefinition(
        codigo="QBE-R2",
        nombre_oficial="Doble Oportunidad Sintética X2",
        descripcion_ejecutiva="Distribución proporcional de capital (Dutching) entre el Empate y el No-Favorito",
        familia="R",
        requiere_triple_candado_factico=True,
        formula_ev="EV = [P(X2) * (O_Sintetico_X2 - 1.0)] - P_Fav",
        rol_boleto_1="Proporcional Empate (Dutching)",
        rol_boleto_2="Proporcional Underdog (Dutching)"
    ),
    "QBE-00": StrategyDefinition(
        codigo="QBE-00",
        nombre_oficial="Veto Preventivo de Capital",
        descripcion_ejecutiva="Descarte total de operación por inviabilidad matemática, riesgo elevado o cuotas sin valor",
        familia="VETO",
        requiere_triple_candado_factico=False,
        formula_ev="N/A ($0.00)",
        rol_boleto_1="N/A",
        rol_boleto_2="N/A"
    ),
    "QBE-MOONSHOT": StrategyDefinition(
        codigo="QBE-MOONSHOT",
        nombre_oficial="Tiro Satélite Asimétrico",
        descripcion_ejecutiva="Oportunidad especial de alto rendimiento en el No-Favorito, respaldada y cubierta con las ganancias proyectadas de la jornada",
        familia="SATELITE",
        requiere_triple_candado_factico=False,
        formula_ev="EV = P_Und * (O_Und - 1.0) - (1.0 - P_Und)",
        rol_boleto_1="N/A",
        rol_boleto_2="Tiro Directo Underdog + Pago Anticipado"
    )
}

# =============================================================================
# [DIRGEN-STRICT] CATÁLOGO INMUTABLE DE ALTITUDES Y SEDES — LIGA MX
# Promovido desde qbe_observatory a qbe_core en SPRINT-FASE3-ECOSYSTEM-BUSINESS-AND-CATALOG-34
# Fuente única de verdad para todo el ecosistema. Cero I/O. Cero DB.
# =============================================================================
from typing import Dict, Optional

CATALOGO_ALTITUDES_LIGAMX: Dict[str, float] = {
    "deportivo-toluca": 2660.0,
    "pachuca": 2400.0,
    "club-puebla": 2135.0,
    "pumas-unam": 2240.0,
    "club-america": 2240.0,
    "cruz-azul": 2240.0,
    "atlante": 2240.0,
    "club-atlante": 2240.0,  # Estadio Ciudad de los Deportes
    "club-necaxa": 1880.0,
    "atletico-san-luis": 1860.0,
    "queretaro-fc": 1820.0,
    "club-leon": 1815.0,
    "chivas-guadalajara": 1560.0,
    "atlas-fc": 1560.0,
    "fc-juarez": 1120.0,
    "santos-laguna": 1120.0,
    "tigres-uanl": 540.0,
    "rayados-de-monterrey": 540.0,
    "club-tijuana": 30.0,
    "mazatlan-fc": 10.0,
}

# Aliases de nomenclatura viva (3NF / FotMob) -> clave canónica del catálogo.
# Solo resuelve nombres: NUNCA altera un valor numérico del catálogo.
ALIAS_ALTITUDES: Dict[str, str] = {
    "club-pachuca": "pachuca",
    "necaxa": "club-necaxa",
    "pumas": "pumas-unam",
    "america": "club-america",
    "chivas": "chivas-guadalajara",
    "atlas": "atlas-fc",
    "leon": "club-leon",
    "queretaro": "queretaro-fc",
    "san-luis": "atletico-san-luis",
    "juarez": "fc-juarez",
    "santos": "santos-laguna",
    "tigres": "tigres-uanl",
    "monterrey": "rayados-de-monterrey",
    "tijuana": "club-tijuana",
    "mazatlan": "mazatlan-fc",
    "puebla": "club-puebla",
    "toluca": "deportivo-toluca",
    "club-atlante": "atlante",
}


def slug_canonico_altitud(slug: Optional[str]) -> Optional[str]:
    """Resuelve el slug vivo al slug canónico del catálogo de altitudes (alias declarado)."""
    if not slug:
        return None
    clave = str(slug).lower().strip()
    if clave in CATALOGO_ALTITUDES_LIGAMX:
        return clave
    return ALIAS_ALTITUDES.get(clave)


def altitud_estadio(slug: str) -> float:
    """Retorna la altitud en msnm del estadio del club. Fallback 0.0 si es desconocido.
    
    Contrato [DIRGEN-STRICT]: función pura, determinista, sin I/O ni DB.
    Compatible con la firma de context_provider para migración sin fricción.
    """
    if not slug:
        return 0.0
    clave = str(slug).lower().strip()
    # Resolución directa
    if clave in CATALOGO_ALTITUDES_LIGAMX:
        return float(CATALOGO_ALTITUDES_LIGAMX[clave])
    # Resolución por alias
    canonico = ALIAS_ALTITUDES.get(clave)
    if canonico and canonico in CATALOGO_ALTITUDES_LIGAMX:
        return float(CATALOGO_ALTITUDES_LIGAMX[canonico])
    return 0.0
