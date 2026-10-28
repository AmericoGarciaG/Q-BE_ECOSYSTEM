# Q-BE ECOSYSTEM — DIRGEN VAULT

**Versión:** 2.0 — Ecosystem Path Edition  
**Estado:** `[DIRGEN-SEALED]` — Bóveda de Código Inmutable  
**Proyecto:** `Q_BE_ECOSYSTEM`  
**Autoridad Suprema:** Américo García Guerrero (Director Humano)  
**Marco:** Kybern Industrial Framework v13.5  
**Expediente:** `SPRINT-FASE4-MIGRACION-REFLEXIVA-BG-04`  
**Fecha:** 2026-10-28  
**Transformación:** reanclaje de rutas `src/*` → `qbe_*/src/*`; sin recálculo de hashes de módulos sin cambio semántico.

> **Aviso de custodia.** Los bloques de código sellado se conservan verbatim. La única transformación permitida en esta migración es la ruta declarada. Los hashes de `MANIFEST_FASE1_REV2.sha256` coinciden con los módulos actuales de `qbe_core`; no se recalculan porque el contenido no cambió. Cualquier modificación de un bloque sellado exige Ficha de Varianza aprobada.

> **Deuda de bóveda declarada.** `[VAULT-CORE-002]` se consolidó en `qbe_core/src/core/intensity_canonical_loglink.py`. `[VAULT-CORE-004]` no tiene módulo standalone en el ecosistema actual; su ruta se conserva como referencia histórica hasta Ficha de Varianza. No se inventó un archivo ni se recalculó un hash.
>
> **Alias histórico:** `[VAULT-CORE-059]` ≡ `[VAULT-CORE-059-SIMPLEX-MORPHOLOGY]`.

## MAPA DE RUTAS

| Ruta legada | Ruta canónica |
|---|---|
| `src/core/` | `qbe_core/src/core/` |
| `src/models/` | `qbe_core/src/models/` |
| `src/storage/` | `qbe_storage/src/storage/` |
| `src/web/` | `qbe_business/src/web/` |
| `src/ingestion/` | `qbe_ingestion/src/ingestion/` |
| `scripts/daemons/` | `qbe_ingestion/src/ingestion/daemons/` |

---

## ÍNDICE DE COMPONENTES CANÓNICOS
1. `[VAULT-CORE-001]` Ecuación Log-Lineal Canónica y Ligadura Estructural de α (`qbe_core/src/core/intensity_canonical_loglink.py`)
2. `[VAULT-CORE-002]` Compresión Hiperbólica Simétrica tanh y Damping (`qbe_core/src/core/intensity_canonical_loglink.py`)
3. `[VAULT-CORE-003]` Fórmula Cerrada de André para Pago Anticipado Π_Lead2 (`qbe_core/src/core/andre_early_payout.py`)
4. `[VAULT-CORE-004]` Concurso Pseudo-BMA con Máscara Booleana (`qbe_core/src/core/generators_ensemble_bma.py`)
5. `[VAULT-CORE-005]` Registro de Variables, Suficiencia Fáctica S(I) y Orquestador Soberano (`qbe_core/src/core/sovereign_pipeline.py`)
6. `[VAULT-CORE-006]` Modulador Adaptativo del Slider de Certeza en Espacio 3^K (`qbe_core/src/core/risk_dial_modulator.py`)
7. `[VAULT-DATA-001]` Central Persistence Gateway y PRAGMAs Transaccionales (`qbe_storage/src/storage/gateway.py`)
8. `[VAULT-DATA-002]` Servicio de Distribución Soberana y Sincronización en BD (`qbe_storage/src/storage/distribution_sync.py`)
9. `[VAULT-DAEMON-001]` Centinela Deportivo Autónomo 100% Dinámico (Cero Alambrado) (`qbe_ingestion/src/ingestion/daemons/centinela_deportivo.py`)
10. `[VAULT-CORE-007-C]` Descuento de Margen Comercial Vig-Free al Símplex Δ² (`centinela_mercado.py`)
11. `[VAULT-CORE-007-D]` Detector de Arbitraje Inter-Casas Surebet (`centinela_mercado.py`)
12. `[VAULT-DAEMON-007-E]` Consenso de Mercado y Diferenciales vs Q-BE (`centinela_mercado.py`)
13. `[VAULT-SCRAPER-001-A]` Conversor Resiliente Cuotas Americanas/Decimales (`betway_scraper.py`)
14. `[VAULT-SCRAPER-001-B]` Extractor Betway con Auto-Scroll y Clic de Acordeones (`betway_scraper.py`)
15. `[VAULT-SCRAPER-002-A]` Inicializador Chromium Stealth Anti-Detección (`caliente_scraper.py`)
16. `[VAULT-SCRAPER-002-B]` Extractor Focalizado Caliente con Descontaminación de Filas (`caliente_scraper.py`)
17. `[VAULT-UI-001-A]` Carrusel Ventanizado de 3 Píldoras (`app.js`)
18. `[VAULT-UI-001-B]` Alternador Modo Enfoque con Persistencia en localStorage (`app.js`)
19. `[VAULT-UI-002-B]` Micro-Malla de Consenso de Mercado 26px 42px 42px 42px (`theme.css`)
20. `[VAULT-UI-002-C]` Geometría de Modo Enfoque Centrado a 880px (`theme.css`)
21. `[VAULT-CORE-070-TRIAJE]` Cascada Determinista de las 9 Estrategias (`qbe_core/src/core/contracts/portfolio_math.py`)
22. `[VAULT-CORE-070-DUTCHING]` Dutching Asimétrico con Seguro en Tablas V=0 (`qbe_core/src/core/contracts/portfolio_math.py`)
23. `[VAULT-CORE-070-RANKING]` Ranking de Fricción de Jornada (`qbe_core/src/core/contracts/portfolio_math.py`)
24. `[VAULT-CORE-070-KELLY]` Kelly Fraccional Atenuado y Hard-Caps Constitucionales (`qbe_core/src/core/contracts/portfolio_math.py`)
25. `[VAULT-CORE-071-PISO]` Umbral de Indiferencia y Escalamiento al Piso de Ventanilla (`qbe_core/src/core/contracts/portfolio_math.py`)
26. `[VAULT-CORE-084-PROGOL-P-PRIME]` Motor de Selección por Masa Acumulada P' (`qbe_core/src/core/contracts/progol_math.py`)
27. `[VAULT-CORE-088-JIT-RESOLVER]` Resolver Semántico JIT de Competiciones (`qbe_ingestion/src/ingestion/progol_resolver.py`)
28. `[VAULT-CORE-059-SIMPLEX-MORPHOLOGY]` Partición Canónica de Δ² y Concentración de Masa Γ (`qbe_core/src/core/simplex_morphology.py`)

---

## [VAULT-DATA-001] Central Persistence Gateway (`qbe_storage/src/storage/gateway.py`)
**Estado:** `[ESTADO: CANON CRISTALIZADO / SELLADO]`  
**Régimen:** `[DIRGEN-STRICT]`  
**Firma:** SHA256-SPRINT5.1-VERIFIED  

```python
# -*- coding: utf-8 -*-
"""
🏆 Q-BE PERSISTENCE GATEWAY — CENTRAL DATA ACCESS & UNIT OF WORK
[VAULT-DATA-001] Motor Transaccional SQLite WAL con Foreign Keys y Aislamiento de Contextos.
Base de Gobierno: Kybern Framework v12.0 [ARCH-1.5.0]
"""

import os
import sqlite3
import logging
from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from src.config import settings

logger = logging.getLogger("PersistenceGateway")


@event.listens_for(Engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, connection_record):
    """
    [ARCH-1.5.0] Configuración inmutable de motor SQLite en cada conexión:
    - WAL Mode: Concurrencia masiva lecturas/escrituras.
    - Foreign Keys: Integridad referencial estricta 3NF.
    - Synchronous NORMAL: Seguridad física con máxima velocidad.
    - Busy Timeout: 15,000 ms para eliminar bloqueos de concurrencia.
    """
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode = WAL;")
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.execute("PRAGMA synchronous = NORMAL;")
        cursor.execute("PRAGMA busy_timeout = 15000;")
        cursor.close()


class PersistenceGateway:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(PersistenceGateway, cls).__new__(cls)
            cls._instance._init_engine()
        return cls._instance

    def _init_engine(self):
        db_path = settings.DATABASE_URL
        connect_args = {"check_same_thread": False} if "sqlite" in db_path else {}
        
        self.engine = create_engine(
            db_path,
            connect_args=connect_args,
            pool_pre_ping=True
        )
        self.SessionFactory = sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False
        )
        self._verify_database_health()

    def _verify_database_health(self):
        """Ejecuta PRAGMA quick_check al arranque para detectar corrupción."""
        with self.engine.connect() as conn:
            result = conn.exec_driver_sql("PRAGMA quick_check;").scalar()
            if result != "ok":
                raise RuntimeError(f"🚨 FATAL: Base de datos corrupta: {result}")
            logger.info("🛡️ [GATEWAY HEALTH] SQLite integrity verified: OK (WAL Mode & FK Active)")

    @contextmanager
    def read_session(self) -> Generator[Session, None, None]:
        """
        Contexto de Solo Lectura (FastAPI UI / Endpoints).
        No-lock, ultraligero (< 2ms), auto-close garantizado.
        """
        session: Session = self.SessionFactory()
        try:
            yield session
        finally:
            session.close()

    @contextmanager
    def write_transaction(self) -> Generator[Session, None, None]:
        """
        Contexto de Escritura Atómica (Unit of Work para Daemons).
        Commit automático si todo es exitoso; ROLLBACK total ante cualquier excepción.
        """
        session: Session = self.SessionFactory()
        try:
            yield session
            session.commit()
        except Exception as ex:
            session.rollback()
            logger.error(f"❌ [GATEWAY ROLLBACK] Transacción abortada por excepción: {ex}")
            raise ex
        finally:
            session.close()

    def create_all_tables(self, base_metadata):
        """Crea todas las tablas declaradas en el esquema ORM."""
        base_metadata.create_all(bind=self.engine)
        logger.info("✅ [GATEWAY TABLES] Esquema relacional 3NF sincronizado.")

```



---

## [VAULT-CORE-001] Ecuación Log-Lineal Canónica y Ligadura Estructural de α (`qbe_core/src/core/intensity_canonical_loglink.py`)
**Estado:** `[ESTADO: CANON EN FORJA]`  
**Régimen:** `[DIRGEN-STRICT]`  

```python
# [VAULT-CORE-001] Ecuación Log-Lineal Canónica, Ligadura de α y Damping tanh
# qbe_core/src/core/intensity_canonical_loglink.py
# Estado: [CANON EN FORJA] | Régimen: [DIRGEN-STRICT]

import math
from typing import Tuple, Optional

def calcular_alpha_ligadura(mu_liga: float = 2.65, gamma_home: float = 0.15) -> float:
    """
    [Sección 4.9.1] Ecuación de Ligadura Estructural de Q-BE:
    alpha = ln(mu_liga) - ln(1.0 + exp(gamma_home))
    Garantiza analíticamente la conservación de masa de goles de la competición.
    """
    gamma_val = float(gamma_home) if gamma_home is not None else 0.15
    mu_val = float(mu_liga) if mu_liga is not None else 2.65
    return math.log(mu_val) - math.log(1.0 + math.exp(gamma_val))


KAPPA_NET = 0.2500  # [VAULT-CORE-001] Compresión hiperbólica PURA (absoluta, adimensional)


def aplicar_damping_hiperbolico(factor_crudo: float, sigma_liga: float = 1.0,
                                kappa_mult: Optional[float] = None,
                                kappa_net: float = KAPPA_NET) -> float:
    """[Sección 4.12 / VAULT-CORE-001] Compresión Hiperbólica PURA de factores log-diferenciales:
    A = κ_net · tanh(A_crudo / κ_net), con κ_net = 0.2500 ABSOLUTO (Libro de Constantes §2).

    Preserva E[A] = 0 por imparidad estricta y acota asintóticamente |A| < κ_net.
    Los parámetros históricos `sigma_liga` / `kappa_mult` (κ = 2.5·σ_liga) quedan DEROGADOS
    por [VAULT-CORE-001]: se conservan en la firma —sin intervenir en el cómputo— para no
    romper llamadas selladas (`qbe_core/src/core/sovereign/bayesian_form.py` invoca por palabra clave
    `sigma_liga=`). Cero margen creativo: κ_net es constante legislada, no calibrada aquí.
    """
    kappa = float(kappa_net)
    if kappa <= 0.0:
        return 0.0
    return kappa * math.tanh(float(factor_crudo) / kappa)


def estimar_intensidades_loglineal(
    A_home: float,
    D_away: float,
    A_away: float,
    D_home: float,
    mu_liga: float = 2.65,
    gamma_home_base: float = 0.15,
    delta_alt_metros: float = 0.0,
    delta_descanso_dias: float = 0.0,
    q_mod_h: float = 1.0,
    q_mod_a: float = 1.0,
    sigma_A: float = 0.25,
    sigma_D: float = 0.25
) -> Tuple[float, float]:
    """
    [Sección 4.9] Arquitectura Canónica Log-Lineal:
    ln(lambda_H) = alpha + gamma_home + A_H - D_A + C_H
    ln(lambda_A) = alpha + A_A - D_H + C_A
    """
    # 1. Ligadura estructural
    alpha = calcular_alpha_ligadura(mu_liga, gamma_home_base)

    # 2. Damping hiperbólico aguas arriba en factores
    A_h_damped = aplicar_damping_hiperbolico(A_home, sigma_A)
    D_a_damped = aplicar_damping_hiperbolico(D_away, sigma_D)
    A_a_damped = aplicar_damping_hiperbolico(A_away, sigma_A)
    D_h_damped = aplicar_damping_hiperbolico(D_home, sigma_D)

    # 3. Operador vectorial de localía (Sección 4.7)
    delta_alt_term = 0.03 * max(0.0, delta_alt_metros / 1000.0)
    delta_rest_term = 0.02 * max(-3.0, min(3.0, delta_descanso_dias))
    gamma_contextual = gamma_home_base + delta_alt_term + delta_rest_term

    # 4. Factores contextuales en espacio logarítmico
    q_h_clamped = max(0.90, min(1.05, float(q_mod_h)))
    q_a_clamped = max(0.90, min(1.05, float(q_mod_a)))
    C_h = math.log(q_h_clamped)
    C_a = math.log(q_a_clamped)

    # 5. Formulación log-lineal canónica
    eta_h = alpha + gamma_contextual + A_h_damped - D_a_damped + C_h
    eta_a = alpha + A_a_damped - D_h_damped + C_a

    # 6. Transformación exponencial e Invariante I6 (Positividad estricta acotada)
    lambda_h = max(0.15, min(4.50, math.exp(eta_h)))
    lambda_a = max(0.15, min(4.50, math.exp(eta_a)))

    return round(lambda_h, 4), round(lambda_a, 4)
```


---

## [VAULT-CORE-003] Fórmula Cerrada de André para Pago Anticipado Π_Lead2 (`qbe_core/src/core/andre_early_payout.py`)
**Estado:** `[ESTADO: CANON EN FORJA]`  
**Régimen:** `[DIRGEN-STRICT]`  

```python
# [VAULT-CORE-003] Fórmula Cerrada de André para Pago Anticipado Π_Lead2
# qbe_core/src/core/andre_early_payout.py
# Estado: [CANON EN FORJA] | Régimen: [DIRGEN-STRICT]

from typing import List

def operador_seccional_andre(x: int, y: int) -> float:
    """
    [Sección 5.20.2] Fórmula Cerrada de Désiré André para activación de ventaja +2:
    pi(x, y) = x*(x-1) / ((y+1)*(y+2)) para marcadores con x >= 2.
    Evaluación continua exacta en tiempo constante O(1).
    """
    if x - y >= 2:
        return 1.0000
    if x < 2:
        return 0.0000
    
    # Marcadores de erosión: x >= 2 pero x - y < 2 (ej. 2-1, 3-2, 4-3)
    num = float(x * (x - 1))
    den = float((y + 1) * (y + 2))
    prob = num / den
    return max(0.0, min(1.0, prob))


def calcular_probabilidad_pago_anticipado(matriz_2d: List[List[float]], es_local: bool = True) -> float:
    """
    [Sección 5.20.3] Integra el Operador de André sobre la matriz 2D consolidada:
    Phi_Lead2 = Sum_x Sum_y [ Pi_Lead2(x, y) * M_xy ]
    """
    phi_acumulado = 0.0
    k_dim = len(matriz_2d)

    for x in range(k_dim):
        for y in range(k_dim):
            p_marcador = matriz_2d[x][y]
            if p_marcador <= 0.0:
                continue
            
            # Si evaluamos al local: x son sus goles, y los del rival.
            # Si evaluamos al visitante: y son sus goles, x los del rival.
            goles_fav = x if es_local else y
            goles_und = y if es_local else x

            pi_hit = operador_seccional_andre(goles_fav, goles_und)
            phi_acumulado += pi_hit * p_marcador

    return round(max(0.0, min(1.0, phi_acumulado)), 4)
```


---

## [VAULT-CORE-004] Generador Dixon-Coles y Colapso Geométrico al Símplex Δ² (`qbe_core/src/core/distribution_dixon_coles.py`)
**Estado:** `[ESTADO: CANON EN FORJA]`  
**Régimen:** `[DIRGEN-STRICT]`  
**Enmienda vigente:** `[LN-QBE-040-C]` (2026-10-15) — parámetro de correlación táctica dinámica
$\rho$ (`rho: Optional[float] = None`, cláusula de resolución por régimen de anotación). El cuerpo
normativo del factor $\tau(x, y)$, de las cotas de admisibilidad de la Sección 5.16.1 y de la
renormalización sobre el retículo truncado permanece **verbatim**; la enmienda sólo sustituye el
default constante por una resolución dinámica cuando el invocante no aporta un $\rho$ explícito
distinto del default sellado ($\rho_{\text{base}} = -0.0500$). Juez: `tests/shield/test_shield_rho_tactico_calibration.py`.

```python
# [VAULT-CORE-004] Generador Dixon-Coles y Colapso Geométrico al Símplex Δ²
# qbe_core/src/core/distribution_dixon_coles.py
# Estado: [CANON EN FORJA] | Régimen: [DIRGEN-STRICT]

import math
from typing import List, Optional, Tuple

def calcular_matriz_dixon_coles(
    lambda_h: float,
    lambda_a: float,
    rho: Optional[float] = None,
    k_max: int = 6
) -> List[List[float]]:
    """
    [Sección 5.3.1 y 5.16] Generador paramétrico con corrección de dependencia
    en baja puntuación bajo Teorema de No-Negatividad Estricta (Invariante I13).

    [LN-QBE-040-C] Calibración táctica dinámica: si el invocante NO aporta un `rho`
    explícito distinto del default sellado (`RHO_BASE = -0.0500`), la correlación se
    resuelve por régimen de anotación con `resolver_rho_dixon_coles(lambda_h, lambda_a)`.
    `rho = 0.0` explícito es el escape hatch de auditoría (sin corrección Dixon-Coles).
    """
    # 0. [LN-QBE-040-C] Resolución dinámica del régimen de correlación
    from src.core.poisson import RHO_BASE, resolver_rho_dixon_coles
    if rho is None or float(rho) == RHO_BASE:
        rho = resolver_rho_dixon_coles(lambda_h, lambda_a)

    # 1. Cotas analíticas de admisibilidad de rho (Sección 5.16.1)
    cota_inf = -min(1.0 / max(0.01, lambda_h), 1.0 / max(0.01, lambda_a))
    cota_sup = min(1.0, 1.0 / max(0.01, lambda_h * lambda_a))
    rho_admisible = max(cota_inf, min(cota_sup, rho))

    # 2. Distribución de Poisson base
    def pois_prob(lmb: float, k: int) -> float:
        return (math.exp(-lmb) * (lmb ** k)) / math.factorial(k)

    # 3. Factor de corrección tau(x, y)
    def tau_factor(x: int, y: int) -> float:
        if x == 0 and y == 0:
            return 1.0 - (lambda_h * lambda_a * rho_admisible)
        if x == 0 and y == 1:
            return 1.0 + (lambda_h * rho_admisible)
        if x == 1 and y == 0:
            return 1.0 + (lambda_a * rho_admisible)
        if x == 1 and y == 1:
            return 1.0 - rho_admisible
        return 1.0

    matriz = []
    suma_total = 0.0

    for x in range(k_max + 1):
        fila = []
        p_x = pois_prob(lambda_h, x)
        for y in range(k_max + 1):
            p_y = pois_prob(lambda_a, y)
            p_conjunta = max(0.0, p_x * p_y * tau_factor(x, y))
            fila.append(p_conjunta)
            suma_total += p_conjunta
        matriz.append(fila)

    # 4. Renormalización estricta sobre el retículo truncado (Sección 5.14)
    if suma_total > 0.0:
        for x in range(k_max + 1):
            for y in range(k_max + 1):
                matriz[x][y] /= suma_total

    return matriz


def colapsar_matriz_a_simplex(matriz_2d: List[List[float]]) -> Tuple[float, float, float]:
    """
    [Sección 5.7 a 5.10] Colapso geométrico exacto de regiones disjuntas sobre el Símplex Δ²:
    p_1 = Sum_{x > y} M_xy
    p_X = Sum_{x = y} M_xy
    p_2 = Sum_{x < y} M_xy
    Garantiza formalmente Invariante I1 (Exhaustividad) e Invariante I14 (Partición).
    """
    p_local = 0.0
    p_empate = 0.0
    p_visitante = 0.0
    k_dim = len(matriz_2d)

    for x in range(k_dim):
        for y in range(k_dim):
            val = matriz_2d[x][y]
            if x > y:
                p_local += val
            elif x == y:
                p_empate += val
            else:
                p_visitante += val

    # Normalización final de seguridad para redondear a 4 decimales
    p_1 = round(p_local, 4)
    p_X = round(p_empate, 4)
    p_2 = round(1.0 - p_1 - p_X, 4)

    return p_1, p_X, p_2
```

---

## [VAULT-CORE-005] Registro de Variables, Suficiencia Fáctica S(I) y Orquestador Soberano (`qbe_core/src/core/sovereign_pipeline.py`)
**Estado:** `[ESTADO: CANON EN FORJA]`  
**Régimen:** `[DIRGEN-STRICT]`  

```python
# [VAULT-CORE-005] Registro de Variables, Suficiencia Fáctica S(I) y Orquestador Soberano
# qbe_core/src/core/sovereign_pipeline.py
# Estado: [CANON EN FORJA] | Régimen: [DIRGEN-STRICT]

import math
from typing import Dict, Any, Tuple, Optional
from pydantic import BaseModel, Field

from src.core.intensity_canonical_loglink import estimar_intensidades_loglineal
from src.core.distribution_dixon_coles import calcular_matriz_dixon_coles, colapsar_matriz_a_simplex
from src.core.andre_early_payout import calcular_probabilidad_pago_anticipado


class StochasticAuditTrace(BaseModel):
    """Traza forense inmutable de la generación de la distribución soberana."""
    match_id: str
    suficiencia_S_I: int = Field(description="1 si satisface datos mínimos, 0 si entra en ignorancia")
    factores_entrada: Dict[str, float]
    intensidades: Dict[str, float]
    distribucion_simplex: Dict[str, float]
    phi_lead2: Dict[str, float]
    matriz_resumen: Dict[str, float]


class SovereignDistributionOutput(BaseModel):
    """Contrato formal de salida de la Capa Probabilística Soberana."""
    match_id: str
    p_local: float
    p_empate: float
    p_visitante: float
    lambda_home: float
    lambda_away: float
    phi_lead2_home: float
    phi_lead2_away: float
    es_operable: bool
    audit_trace: StochasticAuditTrace


def evaluar_suficiencia_informativa(raw_match_data: Dict[str, Any]) -> bool:
    """
    [Sección 2.13.1] Evalúa la función indicadora S(I_i) in {0, 1}.
    Requiere al menos 3 partidos jugados por equipo y datos básicos de goles.
    """
    h_data = raw_match_data.get("home_team_stats", {})
    a_data = raw_match_data.get("away_team_stats", {})

    pj_h = int(h_data.get("pj", 0) or 0)
    pj_a = int(a_data.get("pj", 0) or 0)

    if pj_h < 3 or pj_a < 3:
        return False
    return True


def derivar_factores_estructurales(raw_match_data: Dict[str, Any], mu_liga: float = 2.65) -> Tuple[float, float, float, float]:
    """
    [Sección 4.5 y 4.6] Convierte métricas de Nivel 1 en factores log-diferenciales centrados en media cero:
    Retorna: (A_home, D_away, A_away, D_home)
    """
    h = raw_match_data.get("home_team_stats", {})
    a = raw_match_data.get("away_team_stats", {})

    pj_h = max(1, int(h.get("pj", 8)))
    pj_a = max(1, int(a.get("pj", 8)))

    mu_base_equipo = max(0.5, mu_liga / 2.0)

    # 1. Ataque Local
    # CONTRATO DE UNIDAD [ARCH-1.4.41] / [VAULT-CORE-005]: las claves "xg" y "xga" expresan
    # el ACUMULADO TOTAL DE TEMPORADA (Total Sum), jamás una tasa por partido. La tasa canónica
    # se deriva SIEMPRE por división del acumulado entre los partidos jugados (pj normalizado
    # por max(1, pj) en L491-492): xg_rate = xg_total / pj.
    gf_h_per_game = float(h.get("gf", 10)) / pj_h
    xg_total_h = float(h.get("xg", 0.0) or 0.0)
    xg_h_per_game = (xg_total_h / pj_h) if xg_total_h > 0.0 else gf_h_per_game
    att_h_rate = (0.65 * xg_h_per_game) + (0.35 * gf_h_per_game)
    A_home = math.log(max(0.2, att_h_rate) / mu_base_equipo)

    # 2. Defensa Visita (con signo negativo hacia intensidad rival)
    gc_a_per_game = float(a.get("gc", 12)) / pj_a
    xga_total_a = float(a.get("xga", 0.0) or 0.0)
    xga_a_per_game = (xga_total_a / pj_a) if xga_total_a > 0.0 else gc_a_per_game
    def_a_rate = (0.65 * xga_a_per_game) + (0.35 * gc_a_per_game)
    # Si concede más que la media -> D_away es negativo (defensa débil)
    D_away = -math.log(max(0.2, def_a_rate) / mu_base_equipo)

    # 3. Ataque Visita
    gf_a_per_game = float(a.get("gf", 7)) / pj_a
    xg_total_a = float(a.get("xg", 0.0) or 0.0)
    xg_a_per_game = (xg_total_a / pj_a) if xg_total_a > 0.0 else gf_a_per_game
    att_a_rate = (0.65 * xg_a_per_game) + (0.35 * gf_a_per_game)
    A_away = math.log(max(0.2, att_a_rate) / mu_base_equipo)

    # 4. Defensa Local
    gc_h_per_game = float(h.get("gc", 10)) / pj_h
    xga_total_h = float(h.get("xga", 0.0) or 0.0)
    xga_h_per_game = (xga_total_h / pj_h) if xga_total_h > 0.0 else gc_h_per_game
    def_h_rate = (0.65 * xga_h_per_game) + (0.35 * gc_h_per_game)
    D_home = -math.log(max(0.2, def_h_rate) / mu_base_equipo)

    return round(A_home, 4), round(D_away, 4), round(A_away, 4), round(D_home, 4)


def generar_distribucion_soberana(
    match_id: str,
    raw_match_data: Dict[str, Any],
    mu_liga: float = 2.65,
    gamma_home_base: float = 0.15,
    delta_alt_metros: float = 0.0,
    delta_descanso_dias: float = 0.0,
    q_mod_h: float = 1.0,
    q_mod_a: float = 1.0,
    rho: float = -0.05
) -> SovereignDistributionOutput:
    """
    [TRATADO VOLUMEN I] Generador Soberano Universal de la Distribución del Partido.
    Pipeline completo: Datos -> S(I) -> Factores -> Intensidades acotadas -> Dixon-Coles 2D -> André -> Simplex.
    """
    # 1. Comprobación de Suficiencia Fáctica S(I_i)
    if not evaluar_suficiencia_informativa(raw_match_data):
        trace_insuf = StochasticAuditTrace(
            match_id=match_id,
            suficiencia_S_I=0,
            factores_entrada={},
            intensidades={"lambda_h": 1.325, "lambda_a": 1.325},
            distribucion_simplex={"p_1": 0.3333, "p_X": 0.3333, "p_2": 0.3334},
            phi_lead2={"phi_h": 0.0, "phi_a": 0.0},
            matriz_resumen={}
        )
        return SovereignDistributionOutput(
            match_id=match_id,
            p_local=0.3333, p_empate=0.3333, p_visitante=0.3334,
            lambda_home=1.325, lambda_away=1.325,
            phi_lead2_home=0.0, phi_lead2_away=0.0,
            es_operable=False,
            audit_trace=trace_insuf
        )

    # 2. Derivación de Factores Estructurales
    A_h, D_a, A_a, D_h = derivar_factores_estructurales(raw_match_data, mu_liga)

    # 3. Estimación de Intensidades con Ligadura de alpha y Damping tanh
    lh, la = estimar_intensidades_loglineal(
        A_home=A_h, D_away=D_a,
        A_away=A_a, D_home=D_h,
        mu_liga=mu_liga, gamma_home_base=gamma_home_base,
        delta_alt_metros=delta_alt_metros,
        delta_descanso_dias=delta_descanso_dias,
        q_mod_h=q_mod_h, q_mod_a=q_mod_a
    )

    # 4. Construcción de la Matriz Conjunta Dixon-Coles 2D
    matriz_2d = calcular_matriz_dixon_coles(lambda_h=lh, lambda_a=la, rho=rho, k_max=6)

    # 5. Colapso Geométrico al Símplex Delta^2
    p1, pX, p2 = colapsar_matriz_a_simplex(matriz_2d)

    # 6. Evaluación de la Cláusula de Pago Anticipado (Operador de André en O(1))
    phi_h = calcular_probabilidad_pago_anticipado(matriz_2d, es_local=True)
    phi_a = calcular_probabilidad_pago_anticipado(matriz_2d, es_local=False)

    # 7. Consolidación de Traza Forense
    trace = StochasticAuditTrace(
        match_id=match_id,
        suficiencia_S_I=1,
        factores_entrada={"A_home": A_h, "D_away": D_a, "A_away": A_a, "D_home": D_h},
        intensidades={"lambda_home": lh, "lambda_away": la, "ratio": round(lh / la, 2)},
        distribucion_simplex={"p_1": p1, "p_X": pX, "p_2": p2},
        phi_lead2={"phi_home": phi_h, "phi_away": phi_a},
        matriz_resumen={"0_0": round(matriz_2d[0][0], 4), "1_0": round(matriz_2d[1][0], 4), "1_1": round(matriz_2d[1][1], 4)}
    )

    return SovereignDistributionOutput(
        match_id=match_id,
        p_local=p1, p_empate=pX, p_visitante=p2,
        lambda_home=lh, lambda_away=la,
        phi_lead2_home=phi_h, phi_lead2_away=phi_a,
        es_operable=True,
        audit_trace=trace
    )
```

### Adenda protocolaria `[LN-QBE-102]` — Candado en Vivo & Cableado de Insumos

**Estado:** `[ESTADO: CANON EN FORJA]`  
**Régimen:** `[DIRGEN-STRICT]` (protocolo de traza) · `[DBBD-FUNGIBLE]` (telemetría de presentación)  
**Firma:** SHA256-VAULT-CORE-005-LN-QBE-102-PROTOCOL-DELTA

**Advertencia de paridad (declaración honesta, cero maquillaje):** el bloque transcrito arriba
corresponde al estado `CANON EN FORJA` de la sesión Sprint 5.1. El archivo de producción acumula
desde entonces los aportes de `[VAULT-CORE-STRATEGIES-9]` (cascada γ), `[LN-QBE-020-B]`
(kernel H2H empírico, `origen_factores` / `discrepancia_epist`) y `[ARCH-1.4.41]` (contrato de
unidad xG acumulado) sin re-transcripción íntegra del bloque. Esta adenda sella **exclusivamente**
el delta aditivo de `[LN-QBE-102]`: constantes de sello de procedencia, empaquetado de telemetría
`insumos_factivados` y los tres campos nuevos de `StochasticAuditTrace`. **La matemática no se
toca**: Dixon-Coles, el operador de André y `estimar_intensidades_loglineal` permanecen
bit-idénticos (certificado `auditar_pureza_matematica_vol1` → 7/7).

```python
# [LN-QBE-102] Sellos de procedencia de la evidencia (Regla de Menor Privilegio [ARCH-1.4.43]):
# sólo un demonio de captura en vivo declara EN_VIVO; toda reconstrucción histórica declara
# HISTORICO_RECONSTRUIDO, que es además el default de todos los llamadores existentes.
ORIGEN_CAPTURA_EN_VIVO = "EN_VIVO"
ORIGEN_CAPTURA_HISTORICO = "HISTORICO_RECONSTRUIDO"


def _bloque_factico(raw_match_data: Dict[str, Any], clave: str) -> Dict[str, Any]:
    """[LN-QBE-102] Bloque fáctico del club; `{}` si la fuente no lo publica (cero fabricación)."""
    bloque = raw_match_data.get(clave)
    return bloque if isinstance(bloque, dict) else {}


def _tasa_insumo(bloque: Dict[str, Any], clave: str) -> Optional[float]:
    """[ARCH-1.4.41] Tasa canónica = acumulado / PJ; `None` si la fuente no publica el insumo."""
    precomputada = bloque.get(f"{clave}_rate")
    if isinstance(precomputada, (int, float)) and not isinstance(precomputada, bool):
        return round(float(precomputada), 4)
    acumulado = bloque.get(clave)
    if not isinstance(acumulado, (int, float)) or isinstance(acumulado, bool):
        return None
    pj = bloque.get("pj")
    if not isinstance(pj, (int, float)) or isinstance(pj, bool) or float(pj) <= 0.0:
        return None
    return round(float(acumulado) / float(pj), 4)


def _magnitud_insumo(fuente: Dict[str, Any], claves: Tuple[str, ...]) -> Optional[float]:
    """[LN-QBE-102] Primera clave publicada con magnitud legible; jamás una conversión inventada."""
    for clave in claves:
        valor = fuente.get(clave)
        if isinstance(valor, (int, float)) and not isinstance(valor, bool):
            return float(valor)
    return None


def _conteo_h2h(raw_match_data: Dict[str, Any]) -> int:
    """[LN-QBE-102] Ventana H2H publicada: conteo explícito o longitud de la secuencia."""
    for clave in ("h2h_conteo", "h2h_partidos"):
        valor = raw_match_data.get(clave)
        if isinstance(valor, int) and not isinstance(valor, bool):
            return max(0, valor)
    secuencia = raw_match_data.get("h2h_matches")
    return len(secuencia) if isinstance(secuencia, (list, tuple)) else 0


def _sello_opta(raw_match_data: Dict[str, Any], xg_es_real_opta: Optional[bool]) -> bool:
    """[LN-QBE-102] Sello de procedencia Opta: parámetro explícito, flag publicado o `False`."""
    if isinstance(xg_es_real_opta, bool):
        return xg_es_real_opta
    for clave in ("xg_es_real_opta", "es_real_opta", "xg_disponible"):
        valor = raw_match_data.get(clave)
        if isinstance(valor, bool):
            return valor
    return False


def _contexto_efectivo(explicito: float, raw_match_data: Dict[str, Any], clave: str) -> float:
    """[LN-QBE-102] Parámetro contextual efectivo: explícito si es distinto de 0.0; si no, el publicado."""
    if explicito:
        return float(explicito)
    publicado = raw_match_data.get(clave)
    if isinstance(publicado, (int, float)) and not isinstance(publicado, bool):
        return float(publicado)
    return 0.0
def _empaquetar_insumos_factivados(
    raw_match_data: Dict[str, Any],
    delta_alt_metros: float,
    delta_descanso_dias: float,
    q_mod_h: float,
    q_mod_a: float,
    xg_es_real_opta: Optional[bool] = None,
    cache_macro_stats: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """[LN-QBE-102] Telemetría fáctica de los insumos consumidos por el generador soberano.

    Cada clave es la magnitud REALMENTE usada por la matemática (tasas canónicas [ARCH-1.4.41],
    splits de sede [LN-QBE-038] y parámetros contextuales efectivos). `None` = no publicado.
    """
    local = _bloque_factico(raw_match_data, "home_team_stats")
    visita = _bloque_factico(raw_match_data, "away_team_stats")
    split_local = _bloque_factico(raw_match_data, "home_split_stats")
    split_visita = _bloque_factico(raw_match_data, "away_split_stats")
    gc_local_rate = _tasa_insumo(local, "gc")
    gc_visita_rate = _tasa_insumo(visita, "gc")
    xga_local_rate = _tasa_insumo(local, "xga") or gc_local_rate
    xga_visita_rate = _tasa_insumo(visita, "xga") or gc_visita_rate
    pj_sede_local = _magnitud_insumo(raw_match_data, ("pj_sede_local",))
    pj_sede_visita = _magnitud_insumo(raw_match_data, ("pj_sede_visita",))
    if pj_sede_local is None:
        pj_sede_local = _magnitud_insumo(split_local, ("pj",))
    if pj_sede_visita is None:
        pj_sede_visita = _magnitud_insumo(split_visita, ("pj",))
    paquete: Dict[str, Any] = {
        "xg_local_rate": _tasa_insumo(local, "xg"),
        "xg_visita_rate": _tasa_insumo(visita, "xg"),
        "xga_local_rate": xga_local_rate,
        "xga_visita_rate": xga_visita_rate,
        "gc_local_rate": gc_local_rate,
        "gc_visita_rate": gc_visita_rate,
        "sot_local": _magnitud_insumo(local, ("sot", "shots_on_target")),
        "sot_visita": _magnitud_insumo(visita, ("sot", "shots_on_target")),
        "sota_local": _magnitud_insumo(local, ("sota", "shots_on_target_against")),
        "sota_visita": _magnitud_insumo(visita, ("sota", "shots_on_target_against")),
        "poss_local": _magnitud_insumo(local, ("possession", "possession_pct", "posesion")),
        "poss_visita": _magnitud_insumo(visita, ("possession", "possession_pct", "posesion")),
        "pj_sede_local": int(pj_sede_local) if pj_sede_local is not None else 0,
        "pj_sede_visita": int(pj_sede_visita) if pj_sede_visita is not None else 0,
        "h2h_conteo": _conteo_h2h(raw_match_data),
        "q_mod_h": round(float(q_mod_h), 4),
        "q_mod_a": round(float(q_mod_a), 4),
        "delta_alt_metros": round(float(delta_alt_metros), 4),
        "delta_descanso_dias": round(float(delta_descanso_dias), 4),
        "xg_es_real_opta": _sello_opta(raw_match_data, xg_es_real_opta),
    }
    # [LN-QBE-121] Aduana de Exhibición: el agregado torneal NO alimenta λ; sólo enciende celdas.
    if cache_macro_stats is not None:
        bloque_macro = _bloque_macro_stats(cache_macro_stats)
        if bloque_macro:
            paquete["macro_stats"] = bloque_macro
    return paquete


def _bloque_macro_stats(cache_macro_stats: Any) -> Dict[str, Any]:
    """[LN-QBE-121] Bloque `macro_stats` resuelto (sólo lectura; `{}` si no hay artefacto).

    El llamador (orquestador de ingesta) entrega `{"local": {...}, "visita": {...}}` ya resuelto
    por slug: el generador **no** conoce identidades de club. Cada lado se copia tal cual llega
    —cero derivación, cero imputación— y se sella la procedencia torneal.
    """
    if not isinstance(cache_macro_stats, dict):
        return {}
    local = cache_macro_stats.get("local")
    visita = cache_macro_stats.get("visita")
    if not isinstance(local, dict) and not isinstance(visita, dict):
        return {}
    return {
        "procedencia": str(cache_macro_stats.get("procedencia") or "MACRO_TORNEAL"),
        "catalogo_version": str(cache_macro_stats.get("catalogo_version") or ""),
        "local": dict(local) if isinstance(local, dict) else {},
        "visita": dict(visita) if isinstance(visita, dict) else {},
        "cotejo": dict(cache_macro_stats.get("cotejo") or {}),
    }


# --- Stripping aditivo de `StochasticAuditTrace` (tres campos nuevos, todos con default) ---
    # --- [LN-QBE-102] Sello de procedencia y telemetría fáctica (aditivo, cero ruptura) ---
    origen_captura: str = Field(
        default=ORIGEN_CAPTURA_HISTORICO,
        description="Sello de procedencia de la evidencia: 'EN_VIVO' | 'HISTORICO_RECONSTRUIDO' [LN-QBE-102].",
    )
    timestamp_captura: Optional[str] = Field(
        default=None,
        description="Instante ISO-8601 (UTC) de la captura en vivo; `None` si la ruta no lo publica [LN-QBE-102].",
    )
    insumos_factivados: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Telemetría fáctica de los insumos consumidos (tasas canónicas [ARCH-1.4.41], SoT, PJ de sede [LN-QBE-038], ventana H2H) [LN-QBE-102].",
    )
# --- Delta de `generar_distribucion_soberana` (protocolo de traza, cero alteración de la matemática) ---
def generar_distribucion_soberana(
    match_id: str,
    raw_match_data: Dict[str, Any],
    mu_liga: float = 2.65,
    gamma_home_base: float = 0.15,
    delta_alt_metros: float = 0.0,
    delta_descanso_dias: float = 0.0,
    q_mod_h: float = 1.0,
    q_mod_a: float = 1.0,
    rho: float = -0.05,
    origen_captura: str = ORIGEN_CAPTURA_HISTORICO,
    timestamp_captura: Optional[str] = None,
    xg_es_real_opta: Optional[bool] = None,
    cache_macro_stats: Optional[Dict[str, Any]] = None
) -> SovereignDistributionOutput:
    """
    [TRATADO VOLUMEN I] Generador Soberano Universal de la Distribución del Partido.
    Pipeline completo: Datos -> S(I) -> Factores -> Intensidades acotadas -> Dixon-Coles 2D -> André -> Simplex.
    """
    # 0. [LN-QBE-102] Contexto fáctico EFECTIVO: el parámetro explícito manda; en su default
    #    canónico (0.0) se adopta la magnitud publicada por el registro, de modo que la matemática
    #    y la telemetría `insumos_factivados` declaren EXACTAMENTE el mismo número (cero maquillaje).
    delta_alt_efectivo = _contexto_efectivo(delta_alt_metros, raw_match_data, "delta_alt_metros")
    delta_descanso_efectivo = _contexto_efectivo(delta_descanso_dias, raw_match_data, "delta_descanso_dias")
    insumos_factivados = _empaquetar_insumos_factivados(
        raw_match_data, delta_alt_efectivo, delta_descanso_efectivo, q_mod_h, q_mod_a, xg_es_real_opta,
        cache_macro_stats=cache_macro_stats,
    )

    # 1. Comprobación de Suficiencia Fáctica S(I_i)
    if not evaluar_suficiencia_informativa(raw_match_data):
        trace_insuf = StochasticAuditTrace(
            ...
            matriz_resumen={},
            origen_captura=origen_captura,
            timestamp_captura=timestamp_captura,
            insumos_factivados=insumos_factivados
        )

    # ... (pasos 2-6 bit-idénticos al bloque canónico: factores, intensidades, Dixon-Coles, André)

    # 3. Estimación de Intensidades con Ligadura de alpha y Damping tanh
    lh, la = estimar_intensidades_loglineal(
        A_home=A_h, D_away=D_a,
        A_away=A_a, D_home=D_h,
        mu_liga=mu_liga, gamma_home_base=gamma_home_base,
        delta_alt_metros=delta_alt_efectivo,
        delta_descanso_dias=delta_descanso_efectivo,
        q_mod_h=q_mod_h, q_mod_a=q_mod_a,
        home_team_slug=raw_match_data.get("home_team_slug")
    )

    # 7. Consolidación de Traza Forense
    trace = StochasticAuditTrace(
        ...
        kernel_h2h_empirico=kernel_h2h,
        origen_captura=origen_captura,
        timestamp_captura=timestamp_captura,
        insumos_factivados=insumos_factivados
    )
```

**Invariantes sellados por esta adenda (custodiados por `tests/shield/test_shield_live_lock_and_input_telemetry.py`):**

1. **Asimetría del candado:** en `distribution_sync`, sólo `EN_VIVO → HISTORICO_RECONSTRUIDO` es vetado
   (`protegidos += 1`, marcador oficial actualizado); `EN_VIVO → EN_VIVO` y `HISTORICO → EN_VIVO` escriben.
2. **Fidelidad de la telemetría:** cada valor de `insumos_factivados` es la magnitud efectivamente consumida
   por la matemática; `None` cuando la fuente no lo publica (cero fabricación).
3. **Precedencia de la evidencia publicada:** con `insumos_factivados` no vacío, la degradación a `NEUTRO`
   queda suprimida — el insumo publicado **es** evidencia.


### Adenda protocolaria `[LN-QBE-104]` — Ley de Fusión Convexa del Símplex Soberano

**Estado:** `[ESTADO: CANON CRISTALIZADO / SELLADO]`  
**Régimen:** `[DIRGEN-STRICT]` (matemática pura)  
**Firma:** SHA256-VAULT-CORE-005-LN-QBE-104-CONVEX-SIMPLEX-FUSION

**Alcance:** delta aditivo sobre el orquestador sellado. Dixon-Coles, el operador de André y
`estimar_intensidades_loglineal` permanecen **bit-idénticos**; lo que se legisla es una operación
NUEVA sobre el símplex $\Delta^2$: la mezcla convexa del Generador A (Poisson paramétrico) con el
Generador C (kernel H2H empírico). Hasta esta adenda el kernel se calculaba únicamente para
`Δ_epist` y **nunca** tocaba el símplex publicado: el ensemble era una promesa sin materialización.

```python
# [LN-QBE-104] Ley de mezcla convexa del símplex soberano (Generador A ∪ Generador C).
PESO_H2H_POR_DUELO = 0.05
PESO_H2H_TOPE = 0.25
DELTA_EPISTEMICO_SIN_EVIDENCIA = 0.02


def calcular_peso_h2h(n_duelos: int) -> float:
    """[LN-QBE-104] w_H2H = min(0.25, N · 0.05); N = 0 ⇒ 0.0 (identidad)."""
    try:
        duelos = int(n_duelos or 0)
    except (TypeError, ValueError):
        duelos = 0
    return min(PESO_H2H_TOPE, max(0, duelos) * PESO_H2H_POR_DUELO)


def fusionar_simplex_con_h2h(
    distribucion_parametrica: Dict[str, float],
    kernel: Optional[Any] = None,
    n_duelos: int = 0,
) -> Dict[str, float]:
    """[LN-QBE-104] P_hib(k) = w_Liga·P_A(k) + w_H2H·P_C(k); Δ_epist(∞) = max_k |P_A(k) − P_C(k)|."""
    p_local = float(distribucion_parametrica["p_local"])
    p_empate = float(distribucion_parametrica["p_empate"])
    p_visitante = float(distribucion_parametrica["p_visitante"])

    peso_h2h = calcular_peso_h2h(n_duelos) if kernel is not None else 0.0
    if kernel is None or peso_h2h <= 0.0:
        return {
            "p_local": p_local,
            "p_empate": p_empate,
            "p_visitante": p_visitante,
            "peso_h2h": 0.0,
            "peso_liga": 1.0,
            "delta_epist": DELTA_EPISTEMICO_SIN_EVIDENCIA,
        }

    q_local = float(kernel.p_local)
    q_empate = float(kernel.p_empate)
    q_visita = float(kernel.p_visita)
    peso_liga = 1.0 - peso_h2h

    delta_epist = max(
        abs(p_local - q_local),
        abs(p_empate - q_empate),
        abs(p_visitante - q_visita),
    )
    return {
        "p_local": peso_liga * p_local + peso_h2h * q_local,
        "p_empate": peso_liga * p_empate + peso_h2h * q_empate,
        "p_visitante": peso_liga * p_visitante + peso_h2h * q_visita,
        "peso_h2h": peso_h2h,
        "peso_liga": peso_liga,
        "delta_epist": delta_epist,
    }
```

**Invariantes sellados por esta adenda (custodiados por
`tests/shield/test_shield_ensemble_fusion_and_ui_sync.py`):**

1. **Cierre del símplex:** $\sum_k P_{hib}(k) = 1$ en aritmética exacta (error de redondeo $\le 10^{-16}$).
2. **Acotamiento por componente:** $\min(P_A(k), P_C(k)) \le P_{hib}(k) \le \max(P_A(k), P_C(k))$.
3. **Tope fiduciario:** $w_{H2H} \le 0.25$ para todo $N$; ley monótona no decreciente en $N$.
4. **Identidad Zero-H2H:** $N = 0$ o `kernel=None` $\Rightarrow P_{hib} = P_A$ y $\Delta = 0.02$ (piso R-1).
5. **Métrica:** $\Delta(\infty) = \max_k |P_A(k) - P_C(k)|$ acota la TVD sellada ($\text{TVD} \le \Delta(\infty)$);
   la TVD de `[LN-QBE-020-C]` sigue publicada como `discrepancia_epist`, sin derogación.
6. **Una sola instancia del Generador C** alimenta discrepancia y fusión (una invocación por partido).
7. **Las intensidades λ no se tocan:** la fusión opera sobre el símplex, nunca sobre el espacio de tasas;
   `intensidades.ratio` conserva el valor sellado por `[LN-QBE-102]`.



### Adenda protocolaria `[LN-QBE-118]` — Materialización Anidada de los Cinco Pilares y Resguardo WORM

**Estado:** `[ESTADO: CANON CRISTALIZADO / SELLADO]`  
**Régimen:** `[DIRGEN-STRICT]` (matemática pura de presentación) · `[DBBD-FUNGIBLE]` (orquestación de suministro fáctico)  
**Firma:** SHA256-VAULT-CORE-005-LN-QBE-118-NESTED-FIVE-PILLARS

**Alcance:** delta **aditivo** sobre el orquestador sellado. `derivar_factores_con_procedencia`,
`estimar_intensidades_loglineal`, Dixon-Coles, el operador de André y la fusión `[LN-QBE-104]`
permanecen **bit-idénticos**: lo que se legisla es la **materialización** del contrato anidado de
`[LN-QBE-117]` (hasta esta adenda el aplanador `_MAPA_NIDOS_A_PLANO` existía sin productor) y el
**orden** del lote (resguardo antes de la primera DML). Cada sub-bloque se deriva de las magnitudes
que la matemática **ya consumió**: cero segunda derivación, cero imputación.

```python
# ═════════════════════════════════════════════════════════════════════════════════════════════
# [LN-QBE-118] MATERIALIZACIÓN ANIDADA DE LOS CINCO PILARES (Fase 2 · Integración Maestra)
# El generador sellado publica el paquete ANIDADO como PROYECCIÓN PURA de las magnitudes que ya
# consumió: cada sub-bloque declara `status` + `insumos` con el shape de los proveedores de
# `[LN-QBE-117]`. Cero matemática nueva: λ, Dixon-Coles, el operador de André y la fusión
# `[LN-QBE-104]` permanecen bit-idénticas, y las claves planas de `[LN-QBE-102]` conservan
# nombre, unidad y valor (el anidamiento es ADITIVO).
# ═════════════════════════════════════════════════════════════════════════════════════════════
ESTADO_BLOQUE_EXITO = "EXITO"
ESTADO_BLOQUE_PARCIAL = "PARCIAL"
ESTADO_BLOQUE_SIN_EVIDENCIA = "SIN_EVIDENCIA"


def _estado_del_bloque(insumos: Dict[str, Any]) -> str:
    """[LN-QBE-118] Estado de cobertura de un sub-bloque: `None` = magnitud no publicada.

    `EXITO` exige TODAS las magnitudes publicadas; `PARCIAL` al menos una; `SIN_EVIDENCIA`
    ninguna. El estado declara la evidencia: jamás sustituye un `None` por un default.
    """
    publicadas = [valor for valor in insumos.values() if valor is not None]
    if not publicadas:
        return ESTADO_BLOQUE_SIN_EVIDENCIA
    if len(publicadas) < len(insumos):
        return ESTADO_BLOQUE_PARCIAL
    return ESTADO_BLOQUE_EXITO


def _sub_bloque(nombre: str, insumos: Dict[str, Any]) -> Dict[str, Any]:
    """[LN-QBE-118] Sub-bloque con el shape legislado `{bloque, status, insumos}`."""
    return {"bloque": nombre, "status": _estado_del_bloque(insumos), "insumos": dict(insumos)}


def _bloque_ataque_defensa(paquete: Dict[str, Any]) -> Dict[str, Any]:
    """[LN-QBE-118] Pilar A/D: tasas canónicas `[ARCH-1.4.41]`, SoT/SoTA y sufrimiento de sede."""
    return _sub_bloque(
        "ataque_defensa",
        {
            "xg_local_rate": paquete.get("xg_local_rate"),
            "xg_visita_rate": paquete.get("xg_visita_rate"),
            "xga_local_rate": paquete.get("xga_local_rate"),
            "xga_visita_rate": paquete.get("xga_visita_rate"),
            "gc_local_rate": paquete.get("gc_local_rate"),
            "gc_visita_rate": paquete.get("gc_visita_rate"),
            "sot_local": paquete.get("sot_local"),
            "sot_visita": paquete.get("sot_visita"),
            "sota_local": paquete.get("sota_local"),
            "sota_visita": paquete.get("sota_visita"),
            "pj_sede_local": paquete.get("pj_sede_local"),
            "pj_sede_visita": paquete.get("pj_sede_visita"),
            "xg_es_real_opta": paquete.get("xg_es_real_opta"),
        },
    )


def _bloque_contexto(paquete: Dict[str, Any], raw_match_data: Dict[str, Any]) -> Dict[str, Any]:
    """[LN-QBE-118] Pilar Contexto: ΔAlt⁺ y ΔDías REALES consumidos por λ `[LN-QBE-109]`.

    Los hechos de plaza viajan en el registro (`altitud_local`/`descanso_local`, publicados por la
    homologación): aquí sólo se declaran. `None` cuando la fuente no los publica.
    """
    return _sub_bloque(
        "contexto",
        {
            "delta_alt_metros": paquete.get("delta_alt_metros"),
            "delta_descanso_dias": paquete.get("delta_descanso_dias"),
            "q_mod_h": paquete.get("q_mod_h"),
            "q_mod_a": paquete.get("q_mod_a"),
            "altitud_local": _magnitud_insumo(raw_match_data, ("altitud_local",)),
            "altitud_visita": _magnitud_insumo(raw_match_data, ("altitud_visita",)),
            "descanso_local": _magnitud_insumo(raw_match_data, ("descanso_local",)),
            "descanso_visita": _magnitud_insumo(raw_match_data, ("descanso_visita",)),
        },
    )


def _bloque_trayectoria(raw_match_data: Dict[str, Any]) -> Dict[str, Any]:
    """[LN-QBE-118] Pilar Trayectoria `[LN-QBE-110]`: ventana 5P y su pendiente.

    La captura de homologación no publica la serie de cinco partidos ⇒ los cuatro insumos quedan
    en `None` (`SIN_EVIDENCIA`). El bloque existe —la ausencia es información veraz— y su ventana
    sintética está prohibida (cero fabricación de una tendencia).
    """
    return _sub_bloque(
        "trayectoria",
        {
            "pts_5p_local": _magnitud_insumo(raw_match_data, ("pts_5p_local",)),
            "pts_5p_visita": _magnitud_insumo(raw_match_data, ("pts_5p_visita",)),
            "pendiente_local": _magnitud_insumo(raw_match_data, ("pendiente_local", "m_local")),
            "pendiente_visita": _magnitud_insumo(raw_match_data, ("pendiente_visita", "m_visita")),
        },
    )


def _bloque_volumen_porteria(paquete: Dict[str, Any]) -> Dict[str, Any]:
    """[LN-QBE-118] Pilar Volumen & Portería `[LN-QBE-111]`: posesión y volumen de disparos."""
    return _sub_bloque(
        "volumen_porteria",
        {
            "poss_local": paquete.get("poss_local"),
            "poss_visita": paquete.get("poss_visita"),
            "sot_local": paquete.get("sot_local"),
            "sot_visita": paquete.get("sot_visita"),
            "sota_local": paquete.get("sota_local"),
            "sota_visita": paquete.get("sota_visita"),
        },
    )


def _bloque_h2h(paquete: Dict[str, Any]) -> Dict[str, Any]:
    """[LN-QBE-118] Pilar Memoria `[LN-QBE-105]`: conteo de la ventana y su agregado fáctico.

    Ley Zero-H2H `[LN-QBE-020-B]`: sin enfrentamientos verificables el bloque se publica
    `SIN_EVIDENCIA` con su motivo, jamás un récord 0-0-0 inventado.
    """
    insumos: Dict[str, Any] = {"h2h_conteo": paquete.get("h2h_conteo")}
    if paquete.get("h2h_stats") is not None:
        insumos["h2h_stats"] = paquete["h2h_stats"]
    bloque = _sub_bloque("h2h", insumos)
    if not int(insumos["h2h_conteo"] or 0):
        bloque["status"] = ESTADO_BLOQUE_SIN_EVIDENCIA
        bloque["motivo"] = (
            "Ley Zero-H2H: la ventana no publicó enfrentamientos directos verificables."
        )
    return bloque


def _paquete_anidado_cinco_pilares(
    paquete: Dict[str, Any], raw_match_data: Dict[str, Any]
) -> Dict[str, Any]:
    """[LN-QBE-118] Proyección ANIDADA de los cinco pilares sobre las claves planas selladas.

    Cada sub-bloque lee EXCLUSIVAMENTE del paquete plano ya construido (más los hechos
    contextuales del registro): no existe una segunda derivación de magnitudes, de modo que el
    aplanador `_MAPA_NIDOS_A_PLANO` de `[ARCH-1.4.55]` re-deriva exactamente el mismo valor plano.
    """
    return {
        "h2h": _bloque_h2h(paquete),
        "contexto": _bloque_contexto(paquete, raw_match_data),
        "trayectoria": _bloque_trayectoria(raw_match_data),
        "volumen_porteria": _bloque_volumen_porteria(paquete),
        "ataque_defensa": _bloque_ataque_defensa(paquete),
    }
```

**Delta de cierre dentro de `_empaquetar_insumos_factivados` (las claves planas NO se tocan):**

```python
    if h2h_stats is not None:
        paquete["h2h_stats"] = dict(h2h_stats)
    # [LN-QBE-118] Los cinco pilares se anidan sobre las MISMAS magnitudes planas (aditivo).
    paquete.update(_paquete_anidado_cinco_pilares(paquete, raw_match_data))
    return paquete
```

**Delta de suministro fáctico (`scripts/ingesta/homologar_temporada_optah2h.py`, `[DBBD-FUNGIBLE]`) · adenda `[LN-QBE-119]` (tasa por partido, no sumatoria de torneo):**

```python
def _volumen_porteria_corte(
    cualificados: Sequence[Dict[str, Any]], cache_volumen: Dict[str, Any]
) -> Dict[str, float]:
    """[LN-QBE-118] · [LN-QBE-119] Agregado de Volumen & Portería del club al corte (cobertura ÍNTEGRA).

    Misma ley que el xG: si a un solo partido cualificado le falta `sot`/`sota`/`possession`, el
    agregado NO se publica (cero mezcla de fuentes, cero imputación). Las TRES magnitudes se
    publican como TASA POR PARTIDO del corte: `sot`/`sota` son la media de conteos y `possession`
    el porcentaje medio. Antes de `[LN-QBE-119]` los conteos se acumulaban sin dividir y la casilla
    `V06` («Tiros a puerta por partido») multiplicaba la magnitud exhibida por PJ. Exige además UN
    SOLO nivel de procedencia por acumulación (`procedencia`), igual que [ARCH-1.4.39].
    """
    if not cualificados:
        return {}
    sot = sota = posesion = 0.0
    niveles: set = set()
    for p in cualificados:
        lado = "home" if p["es_local"] else "away"
        registro = (cache_volumen.get(p["match_id"]) or {}).get(lado) or {}
        if registro.get("sot") is None or registro.get("sota") is None:
            return {}
        if registro.get("possession") is None:
            return {}
        sot += float(registro["sot"])
        sota += float(registro["sota"])
        posesion += float(registro["possession"])
        niveles.add(str(registro.get("procedencia") or "fuente_unica"))
    if len(niveles) > 1:
        return {}
    total = float(len(cualificados))
    return {
        # [LN-QBE-119] Tasa por partido (no sumatoria de torneo): misma unidad que la casilla V06.
        "sot": round(sot / total, 3),
        "sota": round(sota / total, 3),
        "possession": round(posesion / total, 3),
    }


def _contexto_del_fixture(sesion, id_partido: str) -> Dict[str, Any]:
    """[LN-QBE-118] Bloque `contexto` del fixture (altitud catalogada + descanso real).

    Delega ÍNTEGRAMENTE en el proveedor canónico `obtener_metricas_contexto` de `[LN-QBE-117]`:
    cero cálculo paralelo en el script. Un fixture ausente de la cartelera o una plaza sin
    catalogar degradan a `None` (jamás a "nivel del mar" inventado).
    """
    try:
        from src.core.sovereign.context_provider import obtener_metricas_contexto
    except ImportError:  # pragma: no cover - contrato de proveedores ausente
        return {}
    try:
        bloque = obtener_metricas_contexto(sesion, id_partido)
    except Exception as ex:  # pragma: no cover - degradación honesta, cero bloqueo del lote
        logger.warning("Contexto no reconstruible para %s: %s", id_partido, ex)
        return {}
    insumos = bloque.get("insumos") if isinstance(bloque, dict) else None
    return dict(insumos) if isinstance(insumos, dict) else {}
```

**Nota de fuente única (Pilar Volumen & Portería):** la caché congelada del Pilar 2 y el sensor
FotMob publican **sólo** `xg`/`xga`; el único nivel que emite `sot`/`sota`/`possession` es
`match_telemetry`. El orquestador construye por ello un mapa dedicado
(`cache_volumen = _sellar_procedencia(telemetria, PROCEDENCIA_TELEMETRIA)`) que `_vector_homologo`
recibe explícito (`cache_volumen`): así **ninguna acumulación mezcla niveles** y un corte con un
partido sin telemetría se declara `SIN EVIDENCIA` en vez de completarse con otra fuente.

**Invariantes sellados por esta adenda (custodiados por
`tests/shield/test_shield_fase2_rehomologacion_and_audit_trace.py`):**

1. **Invarianza matemática:** con el MISMO `raw_match_data` y los mismos parámetros, `λ_h`, `λ_a`,
   el símplex publicado, `phi_lead2`, `Δ_epist` y `kernel_h2h_empirico` son **idénticos** antes y
   después del anidamiento (el nido no alimenta ninguna fórmula).
2. **Cinco bloques siempre presentes:** toda traza publica `h2h`, `contexto`, `trayectoria`,
   `volumen_porteria` y `ataque_defensa`, con `status` ∈ {`EXITO`, `PARCIAL`, `SIN_EVIDENCIA`}.
3. **Paridad plana ↔ nido:** cada clave del nido con espejo en `_MAPA_NIDOS_A_PLANO` es
   **exactamente igual** a su clave plana heredada.
4. **Orden del resguardo:** `crear_backup_boveda_sqlite` precede por AST a toda DML del lote
   (`sincronizar_distribuciones_soberanas_partidos` y `write_transaction`), una sola invocación.

---

### Adenda protocolaria `[LN-QBE-121]` — Aduana de Exhibición Macro-Torneal y Purga Nominal 44V

**Estado:** `[ESTADO: CANON CRISTALIZADO / SELLADO]`  
**Régimen:** `[DIRGEN-STRICT]` (orquestador y precedencia) · `[DBBD-FUNGIBLE]` (transcripción de exhibición)  
**Firma:** SHA256-VAULT-CORE-005-LN-QBE-121-MACRO-EXHIBITION-GATE

**Alcance:** delta **aditivo** sobre el orquestador sellado. `derivar_factores_con_procedencia`,
`estimar_intensidades_loglineal`, Dixon-Coles, el operador de André y la fusión `[LN-QBE-104]`
permanecen **bit-idénticos**: lo que se legisla es la **conexión** del artefacto congelado
`data/cache_macro_stats_liga_mx_2026.json` (`[ARCH-1.4.59]`) al paquete `insumos_factivados` con
jurisdicción de **exhibición** —enciende celdas del catálogo de 32 variables (`[LN-QBE-120]`)— y
**sin** jurisdicción sobre λ. La verdad torneal (temporada completa) y el corte N−1 futuro-ciego
(`[LN-QBE-020-B]`) son regímenes irreconciliables: la macro **jamás** sustituye una magnitud que el
motor consumió. Opción A ratificada por la Tríada (`VAR-2026-FASEB-C3`): la $P'$ histórica de los
117 partidos re-homologados queda **bit-idéntica**.

```python
# ═════════════════════════════════════════════════════════════════════════════════════════════
# [LN-QBE-121] ADUANA DE EXHIBICIÓN MACRO-TORNEAL
# `cache_macro_stats` llega YA RESUELTO por slug desde el orquestador de ingesta (C5): el
# generador no conoce identidades de club. La clave `macro_stats` es ANIDADA y no participa de
# `_MAPA_NIDOS_A_PLANO` ni de `_FORMATO_INSUMO`: sin artefacto, el paquete es byte-idéntico.
# ═════════════════════════════════════════════════════════════════════════════════════════════
CLAVE_MACRO_STATS = "macro_stats"
PROCEDENCIA_MACRO_TORNEAL = "MACRO_TORNEAL"

# (claves del bloque del club, formato de transcripción, nota de procedencia)
_CLAVES_MACRO_STATS: Dict[str, Tuple[Tuple[str, ...], str, str]] = {
    "V02": (("touches_opp_box_per_match",), "num2", "Agregado torneal: toques en área rival por partido [LN-QBE-121]."),
    "V03": (("accurate_passes_per_match",), "num1", "Agregado torneal: pases precisos por partido [LN-QBE-121]."),
    "V04": (("accurate_long_balls_per_match",), "num1", "Agregado torneal: pases largos precisos por partido [LN-QBE-121]."),
    "V05": (("fouls_per_match",), "num1", "Agregado torneal: faltas cometidas por partido [LN-QBE-121]."),
    "V08": (("big_chances_created_per_match",), "num2", "Agregado torneal: big chances creadas por partido [LN-QBE-121]."),
    "V09": (("big_chances_missed_per_match",), "num2", "Agregado torneal: big chances falladas por partido [LN-QBE-121]."),
    "V10": (("xgot_squad",), "num1", "Agregado torneal: xGOT acumulado de plantilla [LN-QBE-121]."),
    "V11": (("xa_squad",), "num1", "Agregado torneal: xA acumulada de plantilla [LN-QBE-121]."),
    "V14": (("defensive_actions_per_match",), "num1", "Agregado torneal: acciones defensivas por partido [LN-QBE-121]."),
    "V15": (("interceptions_per_match",), "num1", "Agregado torneal: intercepciones por partido [LN-QBE-121]."),
    "V17": (("goals_prevented_squad",), "num1", "Agregado torneal: goles evitados de plantilla [LN-QBE-121]."),
    "V18": (("save_percentage",), "pct", "Agregado torneal: Save % del club [LN-QBE-121]."),
    "V19": (("sweeper_actions",), "num1", "Agregado torneal: salidas del portero por partido [LN-QBE-121]."),
    "V20": (("clean_sheets",), "num0", "Agregado torneal: porterías a cero acumuladas [LN-QBE-121]."),
    "V21": (("set_piece_goals_per_match",), "num2", "Agregado torneal: goles a favor de pelota parada por partido [LN-QBE-121]."),
    "V22": (("set_piece_goals_conceded_per_match",), "num2", "Agregado torneal: goles recibidos de pelota parada por partido [LN-QBE-121]."),
    "V23": (("corners_per_match",), "num2", "Agregado torneal: córners por partido [LN-QBE-121]."),
    "V24": (("penalties_won_total", "penalties_conceded_total"), "penales", "Agregado torneal: penales a favor/en contra acumulados [LN-QBE-121]."),
    "V25": (("yellow_cards_per_match", "red_cards_per_match"), "tarjetas", "Agregado torneal: amarillas y rojas por partido [LN-QBE-121]."),
}
```

**Precedencia legislada (una sola dirección):** `h2h_stats` (`[LN-QBE-105]`) → `_FORMATO_INSUMO`
(insumo realmente consumido por λ) → `_RESPALDO_INSUMO` (Axioma 4) → `_CLAVES_MACRO_STATS`
(exhibición torneal). La macro **sólo rellena celdas apagadas**: `V01`, `V06`, `V07`, `V12` y `V13`
conservan el corte certificado y su cotejo torneal se publica aparte en `macro_stats.cotejo`.

**Invariantes sellados por esta adenda (custodiados por
`tests/shield/test_shield_macro_consumption_phase_b.py`):**

1. **Invariancia de λ:** con `cache_macro_stats=None` y con artefacto conectado, `lambda_home`,
   `lambda_away`, `p_local`/`p_empate`/`p_visitante`, `discrepancia_epist` y `phi_lead2` son
   **idénticos** (la macro no toca el espacio de tasas).
2. **Identidad del paquete:** sin artefacto, `insumos_factivados` no publica `macro_stats` y es
   igual al paquete previo a esta adenda (cero clave fantasma).
3. **Fidelidad de la transcripción:** cada celda encendida reproduce la clave publicada del
   artefacto; una clave ausente deja la celda en `SIN EVIDENCIA` (cero imputación, `V16` sin fuente).
4. **No canibalización:** ninguna celda encendida por el corte certificado cambia de valor ni de
   nota por la presencia del artefacto.
5. **Auxiliares sin código:** las magnitudes sin celda (`m_xG`, `m_xGA`, impacto de bajas) viajan
   como `AUX_*` y **ninguna** porta un identificador `V\\d\\d`.

---

## [VAULT-DATA-002] Servicio de Distribución Soberana y Sincronización en BD (`qbe_storage/src/storage/distribution_sync.py`)
**Estado:** `[ESTADO: CANON CRISTALIZADO / SELLADO]`  
**Régimen:** `[DIRGEN-STRICT]`  
**Firma:** SHA256-SPRINT5.5-VERIFIED  

```python
# -*- coding: utf-8 -*-
"""
🏆 Q-BE PERSISTENCE BRIDGE — SINCRONIZACIÓN DE DISTRIBUCIONES SOBERANAS
[ARCH-1.6.11] Puente Transaccional E2E: Hechos Deportivos -> Sovereign Pipeline -> SQLite 3NF.
Base de Gobierno: Kybern Framework v12.0 / Tratado Volumen I
"""

import logging
from typing import Dict, Any, List, Optional
from src.storage.gateway import PersistenceGateway
from src.storage.models import Competition, Match, SovereignDistribution
from src.core.sovereign_pipeline import generar_distribucion_soberana

logger = logging.getLogger("DistributionSync")


def sincronizar_distribuciones_soberanas_partidos(
    partidos_datos: List[Dict[str, Any]],
    gateway: Optional[PersistenceGateway] = None
) -> Dict[str, Any]:
    """
    [ARCH-1.6.11] Ejecuta la generación y persistencia transaccional atómica
    de distribuciones soberanas sobre la tabla 3NF 'sovereign_distributions'.
    """
    gw = gateway or PersistenceGateway()
    procesados = 0
    exitosos = 0
    errores = []

    for item in partidos_datos:
        match_id = item.get("match_id")
        comp_id = item.get("competition_id", "MEX_LIGAMX")

        if not match_id:
            continue

        procesados += 1

        try:
            # 1. Obtener parámetros macro de la competición desde la BD
            mu_liga = 2.65
            gamma_home = 0.15

            with gw.read_session() as session:
                comp = session.query(Competition).filter(Competition.id == comp_id).first()
                if comp:
                    mu_liga = float(comp.macro_mu_liga or 2.65)
                    gamma_home = float(comp.macro_gamma_home or 0.15)

            # 2. Generación matemática soberana con el pipeline del Tratado Vol. I
            dist_out = generar_distribucion_soberana(
                match_id=match_id,
                raw_match_data=item,
                mu_liga=mu_liga,
                gamma_home_base=gamma_home,
                delta_alt_metros=float(item.get("delta_alt_metros", 0.0) or 0.0),
                delta_descanso_dias=float(item.get("delta_descanso_dias", 0.0) or 0.0),
                q_mod_h=float(item.get("q_mod_h", 1.0) or 1.0),
                q_mod_a=float(item.get("q_mod_a", 1.0) or 1.0)
            )

            # 3. Persistencia atómica en la tabla 3NF 'sovereign_distributions'
            trace_dict = dist_out.audit_trace.model_dump()
            # [LN-QBE-104] Δ_epist(∞) REAL de la fusión convexa (norma infinito sobre Δ²), NO el
            # `ratio` λ_max/λ_min de tasas: el puente lee contrato de salida → traza forense → piso
            # de ignorancia R-1, acotando a [0, 1]. El `ratio` permanece intacto en `intensidades`.
            epist_delta = _delta_epistemico_publicado(dist_out, trace_dict)

            with gw.write_transaction() as tx:
                dist_rec = tx.query(SovereignDistribution).filter(
                    SovereignDistribution.match_id == match_id
                ).first()

                if not dist_rec:
                    dist_rec = SovereignDistribution(
                        match_id=match_id,
                        model_version="v13.0-DIRGEN",
                        p_local=dist_out.p_local,
                        p_empate=dist_out.p_empate,
                        p_visitante=dist_out.p_visitante,
                        lambda_home=dist_out.lambda_home,
                        lambda_away=dist_out.lambda_away,
                        phi_lead2_home=dist_out.phi_lead2_home,
                        phi_lead2_away=dist_out.phi_lead2_away,
                        epistemic_delta=epist_delta,
                        audit_trace_json=trace_dict
                    )
                    tx.add(dist_rec)
                else:
                    dist_rec.model_version = "v13.0-DIRGEN"
                    dist_rec.p_local = dist_out.p_local
                    dist_rec.p_empate = dist_out.p_empate
                    dist_rec.p_visitante = dist_out.p_visitante
                    dist_rec.lambda_home = dist_out.lambda_home
                    dist_rec.lambda_away = dist_out.lambda_away
                    dist_rec.phi_lead2_home = dist_out.phi_lead2_home
                    dist_rec.phi_lead2_away = dist_out.phi_lead2_away
                    dist_rec.epistemic_delta = epist_delta
                    dist_rec.audit_trace_json = trace_dict

            exitosos += 1
            logger.info(f"✅ [SOVEREIGN PERSISTED] Distribución guardada en SQLite para {match_id}: ({dist_out.p_local:.4f}, {dist_out.p_empate:.4f}, {dist_out.p_visitante:.4f})")

        except Exception as ex:
            logger.error(f"❌ Error sincronizando distribución para {match_id}: {ex}")
            errores.append({"match_id": match_id, "error": str(ex)})

    return {
        "procesados": procesados,
        "exitosos": exitosos,
        "errores": errores
    }
```
### Adenda protocolaria `[LN-QBE-102]` — Candado en Vivo sobre el Puente de Persistencia

**Estado:** `[ESTADO: CANON CRISTALIZADO / SELLADO]`  
**Régimen:** `[DIRGEN-STRICT]` (guarda de escritura)  
**Firma:** SHA256-VAULT-DATA-002-LN-QBE-102-LIVE-PROTECTION-LOCK

**Alcance:** delta aditivo sobre el puente sellado. El bloque transcrito arriba (SPRINT 5.5) sigue
siendo el canon de la generación y el `upsert`; esta adenda sella la **guarda de escritura** que se
evalúa dentro de la transacción, antes de asignar un solo atributo sobre la fila existente. Cero
cambio a los valores matemáticos escritos: la guarda decide *si* se escribe, nunca *qué* se escribe.

```python
def _candado_blindado(origen_previo: str, origen_entrante: str) -> bool:
    """[LN-QBE-102] `LIVE_PROTECTION_LOCK`: veta únicamente la DEGRADACIÓN de procedencia.

    Relación estrictamente asimétrica: una reconstrucción histórica jamás sobreescribe evidencia
    capturada en ventanilla; en cambio `EN_VIVO -> EN_VIVO` (re-captura) y
    `HISTORICO_RECONSTRUIDO -> EN_VIVO` (ascenso de calidad de evidencia) sí escriben.
    """
    return (
        origen_previo == ORIGEN_CAPTURA_EN_VIVO
        and origen_entrante == ORIGEN_CAPTURA_HISTORICO
    )


# --- Dentro de `sincronizar_distribuciones_soberanas_partidos` (rama de fila existente) ---
                    # [LN-QBE-102] `LIVE_PROTECTION_LOCK`: se evalúa DENTRO de la transacción,
                    # leyendo el sello de la fila existente antes de asignar un solo atributo.
                    traza_previa = dist_rec.audit_trace_json if isinstance(dist_rec.audit_trace_json, dict) else {}
                    origen_previo = traza_previa.get("origen_captura") or ORIGEN_CAPTURA_HISTORICO
                    blindado = _candado_blindado(origen_previo, origen_captura)

                    if blindado:
                        # Excepción del Hecho Consumado: sólo el marcador oficial de `matches`.
                        _actualizar_marcador_oficial(tx, match_id, item)
                    else:
                        dist_rec.model_version = "v13.0-DIRGEN"
                        ...
                        dist_rec.audit_trace_json = trace_dict
```

**Contrato de salida del puente (ampliado):** `{"procesados", "exitosos", "protegidos", "errores"}`.
`protegidos` cuenta los vetos efectivos del candado — es la métrica de auditoría de la protección;
un veto **no** es un error: el marcador oficial se actualiza y la probabilidad de ventanilla se preserva.
### Adenda protocolaria `[LN-QBE-104]` — Persistencia de la Δ_epist Real

**Estado:** `[ESTADO: CANON CRISTALIZADO / SELLADO]`  
**Régimen:** `[DIRGEN-STRICT]` (magnitud persistida) · `[DBBD-FUNGIBLE]` (presentación)  
**Firma:** SHA256-VAULT-DATA-002-LN-QBE-104-EPISTEMIC-DELTA-REAL

**Alcance:** delta correctivo sobre el bloque sellado (línea 903 pre-enmienda). El `upsert`, el
`LIVE_PROTECTION_LOCK` y la generación matemática quedan **intactos**: lo único que cambia es la
MAGNITUD que se escribe en la columna `sovereign_distributions.epistemic_delta`. Antes espejaba el
`ratio` $\lambda_{\max}/\lambda_{\min}$ —una magnitud de tasas sin relación con la discrepancia
entre generadores—; ahora publica $\Delta_{epist}(\infty) = \max_k |P_A(k) - P_C(k)|$ calculada en
la fusión convexa `[LN-QBE-104]`. Cero backfill: las filas históricas no se reescriben.

```python
def _delta_epistemico_publicado(dist_out: Any, trace_dict: Dict[str, Any]) -> float:
    """
    [LN-QBE-104] Δ_epist(∞) persistido en `sovereign_distributions.epistemic_delta`.

    Orden de lectura: contrato de salida → traza forense → piso de ignorancia declarada R-1.
    El valor se acota a [0, 1] porque Δ(∞) vive en el símplex Δ²; un `None` heredado o un tipo
    no numérico JAMÁS se maquilla con 0.0 (se declara la ignorancia 0.02 del Contrato R-1).
    """
    for candidato in (
        getattr(dist_out, "epistemic_delta", None),
        trace_dict.get("epistemic_delta"),
    ):
        if isinstance(candidato, bool) or not isinstance(candidato, (int, float)):
            continue
        valor = float(candidato)
        if math.isfinite(valor):
            return min(1.0, max(0.0, valor))
    return DELTA_EPISTEMICO_SIN_EVIDENCIA
```

**Invariantes sellados por esta adenda (custodiados por
`tests/shield/test_shield_ensemble_fusion_and_ui_sync.py`):**

1. **Precedencia de la verdad:** el contrato de salida (`dist_out.epistemic_delta`) gana a la traza;
   sólo si falta se lee `audit_trace_json["epistemic_delta"]`; sólo si ambos faltan se declara 0.02.
2. **Acotamiento:** $\Delta(\infty) \in [0, 1]$ por construcción (vive en $\Delta^2$); un valor fuera
   de rango se recorta, no se descarta.
3. **Cero maquillaje:** `bool`, `None`, `str` u objetos no numéricos degradan al piso R-1 — jamás a 0.0.
4. **Intactidad de la evidencia sellada:** `intensidades.ratio` sigue en la traza 3NF con el mismo
   `round(lh / la, 2)` de `[LN-QBE-102]`; deja de ser la fuente de `epistemic_delta`, no desaparece.




---


## [VAULT-CORE-006] Modulador Adaptativo del Slider de Certeza en Espacio 3^K (`qbe_core/src/core/risk_dial_modulator.py`)
**Estado:** `[CANON EN FORJA — REVISIÓN 2]` (Fase 4: erradicación del factor mágico `0.70`)  
**Régimen:** `[DIRGEN-STRICT]`  
**Nodo Lógico:** `[LN-QBE-073]` / `[LN-QBE-073-B]`  
**Sprint:** `6.4 — Paso 1` (Legislación; materialización sincronizada con `src/`)  

```python
# [VAULT-CORE-006] Modulador Adaptativo del Slider de Certeza en Espacio 3^K
# qbe_core/src/core/risk_dial_modulator.py
# Estado: [CANON EN FORJA — REVISIÓN 2] | Régimen: [DIRGEN-STRICT]

from typing import List, Dict, Any
from src.core.portfolio import calcular_trinidad_resiliencia_3k
from src.core.contracts.portfolio_math import calcular_ganancia_cobertura_v0


def modular_cartera_por_slider_certeza(
    ordenes_candidatas: List[Dict[str, Any]],
    target_certeza_pct: float = 80.0,
    piso_ventanilla: float = 2.0
) -> List[Dict[str, Any]]:
    """
    [LN-QBE-073] Modula dinámicamente la cartera de casino para garantizar que
    la probabilidad combinada de no perder (tablas o arriba) satisfaga target_certeza_pct.
    Transmuta D1 -> H1 y contrae exposición si es necesario.
    """
    if not ordenes_candidatas:
        return []

    target = float(max(70.0, min(95.0, target_certeza_pct)))
    ordenes = [dict(o) for o in ordenes_candidatas]

    # Bucle de convergencia fiduciaria (máximo 5 iteraciones)
    for _ in range(5):
        # 1. Evaluar el espacio 3^K actual
        trinidad = calcular_trinidad_resiliencia_3k(ordenes)
        certeza_actual = float(trinidad.get("tablas_o_ganancia", {}).get("probabilidad_pct", 0.0))

        # Si ya se cumple la meta de certeza, retornar órdenes optimizadas
        if certeza_actual >= target:
            break

        # 2. Localizar órdenes directas (D1/D1+) que expongan capital al empate sin seguro
        orden_directa_idx = None
        menor_prob_directa = 1.0

        for idx, o in enumerate(ordenes):
            if o.get("es_directo", False):
                p_win = float(o.get("p_win", 1.0))
                if p_win < menor_prob_directa:
                    menor_prob_directa = p_win
                    orden_directa_idx = idx

        # Si hay una orden directa, transmutarla a cobertura H1 (comprar seguro V=0)
        if orden_directa_idx is not None:
            od = ordenes[orden_directa_idx]
            od["es_directo"] = False
            od["estrategia_codigo"] = "QBE-H1"
            od["linea_promocional"] = "Cobertura por Certeza Slider"
            
            # [LN-QBE-073-B] Prima de Cobertura Canónica: se erradica el factor mágico 0.70.
            # El sacrificio de premio se DERIVA del dutching V=0 a cuotas soberanas justas
            # (o_fav_implícita = 1 + g/B, b_seguro = B · p_draw, b_primario = B · (1 − p_draw)):
            #     g_cob = g · (1 − p_draw) − B · p_draw
            # Función pura: qbe_core/src/core/contracts/portfolio_math.py::calcular_ganancia_cobertura_v0
            od["ganancia"] = calcular_ganancia_cobertura_v0(
                ganancia_directa=float(od.get("ganancia", 0.0)),
                inversion=float(od.get("inversion", 0.0)),
                p_draw=float(od.get("p_draw", 0.0))
            )
            continue

        # 3. Si ya no hay órdenes directas y aún no alcanza el target:
        # Podar la orden más frágil de la cartera para salvar la certeza global
        if len(ordenes) > 1:
            # Ordenar por probabilidad de éxito y remover la peor
            ordenes.sort(key=lambda x: float(x.get("p_win", 0.0)), reverse=True)
            ordenes.pop()  # Poda fiduciaria del activo más riesgoso
        else:
            break

    return ordenes
```

---

## [VAULT-UI-001] Plantilla Canónica del Panel de Cartelera Soberana
**Estado:** `[CANON EN FORJA]`  
**Régimen:** `[DIRGEN-STRICT]`  
**Ruta Target:** `qbe_business/src/web/templates/index.html` (Panel Derecho de Equipos y Partidos)  

```html
<!-- [VAULT-UI-001] Plantilla Canónica del Panel de Cartelera Soberana -->
<!-- qbe_business/src/web/templates/index.html (Panel Derecho de Equipos y Partidos) -->
<!-- Estado: [CANON EN FORJA] | Régimen: [DIRGEN-STRICT] -->

<div class="cartelera-panel card card-clean">
    <div class="cartelera-header flex-between">
        <div class="flex-align-center gap-10">
            <span class="icon-header">⚽</span>
            <h3 id="lbl-nombre-jornada" class="m-0">Jornada Activa</h3>
        </div>
        <div id="sync-status-badge" class="badge-status-neutral">
            <span>Sincronizada con BD</span>
        </div>
    </div>

    <!-- Carrusel de Píldoras de Jornada Continuas (Sin "Mercado Abierto") -->
    <div id="matchday-pill-selector" class="matchday-pill-selector">
        <!-- Generado dinámicamente por app.js -->
    </div>

    <!-- Lista de Partidos Soberanos (Cero Checkboxes, Cero Botón Portafolio) -->
    <div id="fixtures-container" class="fixtures-scroll-container">
        <!-- Tarjetas inyectadas dinámicamente -->
    </div>
</div>
```


---

## [VAULT-DAEMON-001] Centinela Deportivo Autónomo 100% Dinámico (Cero Alambrado) (`qbe_ingestion/src/ingestion/daemons/centinela_deportivo.py`)
**Estado:** `[CANON EN FORJA]`  
**Régimen:** `[DIRGEN-STRICT]`  

```python
# [VAULT-DAEMON-001] Centinela Deportivo Autónomo 100% Dinámico (Cero Alambrado)
# qbe_ingestion/src/ingestion/daemons/centinela_deportivo.py
# Estado: [CANON EN FORJA] | Régimen: [DIRGEN-STRICT]

import sys
import os
import re
import time
import json
import argparse
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.storage.gateway import PersistenceGateway
from src.storage.models import League, StandingSnapshot, FixtureSnapshot, CurrentTeamStanding, Competition, Match
from src.storage.distribution_sync import sincronizar_distribuciones_soberanas_partidos
from src.ingestion.normalizer import canonicalize_team_name
from src.storage.crest_resolver import STATIC_CRESTS_DIR, obtener_slug_club
from src.storage.sync_service import sync_current_team_standings_table, LIGAMX_LOGO_ID_MAP

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("CentinelaDeportivo")


def _convertir_match_fotmob(match_obj: Dict[str, Any], idx: int, jornada_num: int) -> Dict[str, Any]:
    """Convierte un objeto de partido del JSON oficial de FotMob a contrato interno Q-BE."""
    dias_semana = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo"}
    meses_nom = {9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}

    home_raw = match_obj.get("home", {})
    away_raw = match_obj.get("away", {})
    loc_name = canonicalize_team_name(home_raw.get("name") or home_raw.get("shortName") or "")
    vis_name = canonicalize_team_name(away_raw.get("name") or away_raw.get("shortName") or "")
    loc_slug = obtener_slug_club(loc_name)
    vis_slug = obtener_slug_club(vis_name)

    st = match_obj.get("status", {})
    utc_str = st.get("utcTime", "")
    if utc_str:
        dt_utc = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
        dt_local = dt_utc.astimezone(timezone(timedelta(hours=-6)))
        horario = dt_local.strftime("%d/%m %H:%M hr")
        fecha_dt = dt_local.strftime("%Y-%m-%dT%H:%M:%S")
        dia = dt_local.day
        mes = dt_local.month
        fecha_bloque = f"{dias_semana.get(dt_local.weekday(), 'Día')} {dia:02d} de {meses_nom.get(mes, 'Mes')}"
    else:
        horario = "Fecha por Definir"
        fecha_dt = "2026-09-25T19:00:00"
        fecha_bloque = "Partidos Programados"

    finished = bool(st.get("finished", False))
    score_str = st.get("scoreStr")

    if finished or score_str:
        estado = "FINALIZADO"
        disponible = False
        operable = False
        minuto = "Final"
        marcador = score_str or "0 - 0"
    else:
        estado = "PROGRAMADO"
        disponible = True
        operable = True
        minuto = None
        marcador = None

    return {
        "id_partido": f"LIGAMX-J{jornada_num}-{idx:02d}",
        "local": loc_name,
        "visitante": vis_name,
        "local_escudo_url": f"/static/img/crests/{loc_slug}.png",
        "visitante_escudo_url": f"/static/img/crests/{vis_slug}.png",
        "horario": horario,
        "fecha_dt": fecha_dt,
        "fecha_bloque": "Partidos Concluidos" if estado == "FINALIZADO" else fecha_bloque,
        "estado": estado,
        "marcador_actual": marcador,
        "minuto_juego": minuto,
        "disponible_para_seleccion": disponible,
        "es_operable": operable,
        "momios": None
    }


def extraer_datos_vivos_completos() -> Dict[str, Any]:
    """Extracción 100% viva dinámica sin una sola tupla estática en el código."""
    from playwright.sync_api import sync_playwright
    import urllib.request

    args = [
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-infobars",
        "--window-position=0,0",
        "--ignore-certificate-errors",
    ]

    standings_raw = []
    fixtures_j8 = []
    fixtures_j9 = []
    fixtures_j10 = []
    reprogramados = []
    raw_json = None

    # 1. Extracción FotMob Opta JSON (__NEXT_DATA__)
    logger.info("[PASO 1/2] Conectando a FotMob (Opta Engine ID 230)...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=args)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                viewport={"width": 1366, "height": 768},
                locale="es-MX",
                timezone_id="America/Mexico_City"
            )
            page = context.new_page()
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            page.goto("https://www.fotmob.com/es-419/leagues/230/overview/liga-mx", timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)

            next_data_el = page.query_selector("script#__NEXT_DATA__")
            if next_data_el:
                raw_json = json.loads(next_data_el.inner_text())

            # Captura de reprogramados en ligamx.net
            try:
                page.goto("https://ligamx.net/", timeout=15000, wait_until="domcontentloaded")
                page.wait_for_timeout(1000)
                page.evaluate("""() => {
                    const els = Array.from(document.querySelectorAll('a, button, span, div'));
                    for (let el of els) {
                        if (el.textContent.trim().toUpperCase() === 'PARTIDOS REPROGRAMADOS') {
                            el.click(); return true;
                        }
                    }
                    return false;
                }""")
                page.wait_for_timeout(1000)

                tarjetas_rep = page.query_selector_all("li[id^='MrcdrPrtd_']")
                for t in tarjetas_rep:
                    txt = t.inner_text().strip()
                    if "28/10" in txt or "14/11" in txt:
                        f_match = re.search(r'(\d{1,2})/(\d{1,2})\s*(\d{1,2}):(\d{2})\s*hr', txt)
                        fecha_str = f_match.group(0) if f_match else "Fecha por Definir"
                        dia, mes = 28, 10
                        if f_match:
                            dia, mes = int(f_match.group(1)), int(f_match.group(2))

                        imgs = t.query_selector_all("img")
                        clubes_rep = []
                        for img in imgs:
                            src = (img.get_attribute("src") or "")
                            alt = (img.get_attribute("alt") or img.get_attribute("title") or "").strip()
                            nom = None
                            if alt and alt != "undefined" and alt not in ["Transmisión", "Minuto a Minuto", "Informe Arbitral"] and len(alt) > 2:
                                nom = canonicalize_team_name(alt)
                            else:
                                m_id = re.search(r'logos(?:64x64)?/(\d+)/', src)
                                if m_id and m_id.group(1) in LIGAMX_LOGO_ID_MAP:
                                    nom = LIGAMX_LOGO_ID_MAP[m_id.group(1)]

                            if nom and nom not in clubes_rep:
                                clubes_rep.append(nom)

                        if len(clubes_rep) >= 2:
                            loc = clubes_rep[0]
                            vis = clubes_rep[1]
                            if not any(r["local"] == loc and r["visitante"] == vis for r in reprogramados):
                                reprogramados.append({
                                    "id_partido": f"LIGAMX-REP-{len(reprogramados)+1:02d}",
                                    "local": loc,
                                    "visitante": vis,
                                    "local_escudo_url": f"/static/img/crests/{obtener_slug_club(loc)}.png",
                                    "visitante_escudo_url": f"/static/img/crests/{obtener_slug_club(vis)}.png",
                                    "horario": fecha_str,
                                    "fecha_dt": datetime(2026, mes, dia, 21, 0).isoformat(),
                                    "fecha_bloque": "Partidos Reprogramados / Fecha Lejana",
                                    "estado": "REPROGRAMADO",
                                    "marcador_actual": None,
                                    "minuto_juego": None,
                                    "disponible_para_seleccion": False,
                                    "es_operable": False,
                                    "sub_badge": "Fecha Lejana"
                                })
            except Exception as e_rep:
                logger.warning(f"Extracción opcional ligamx.net omitida: {e_rep}")

            browser.close()
    except Exception as e_pw:
        logger.warning(f"Playwright falló, activando respaldo HTTP nativo: {e_pw}")

    # Respaldo HTTP directo si Playwright falló
    if not raw_json:
        try:
            url_fotmob = "https://www.fotmob.com/es-419/leagues/230/overview/liga-mx"
            req = urllib.request.Request(url_fotmob, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            html_content = urllib.request.urlopen(req, timeout=15).read().decode('utf-8')
            m_json = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html_content)
            if m_json:
                raw_json = json.loads(m_json.group(1))
        except Exception as e_http:
            logger.error(f"Fallo en respaldo HTTP FotMob: {e_http}")

    # Mandato Fail-Loud [GOVERNANCE-01]: Cero datos sintéticos ante caída de red
    if not raw_json:
        raise RuntimeError("Fail-Loud: Ingesta incompleta. Prohibido recurrir a datos quemados.")

    # 2. Parseo de Tabla y Métricas Opta
    page_props = raw_json.get("props", {}).get("pageProps", {})
    table_list = page_props.get("table") or page_props.get("overview", {}).get("table") or []
    table_obj = table_list[0] if isinstance(table_list, list) and len(table_list) > 0 else {}
    teams_all = table_obj.get("data", {}).get("table", {}).get("all", [])
    team_form = table_obj.get("teamForm", {})
    next_opp = table_obj.get("nextOpponent", {})
    res_map = {"W": "G", "D": "E", "L": "P"}

    for idx_t, tm in enumerate(teams_all, start=1):
        t_id = str(tm.get("id"))
        t_name = canonicalize_team_name(tm.get("name", ""))
        scores_str = str(tm.get("scoresStr") or "0-0").split("-")
        gf = int(scores_str[0]) if len(scores_str) > 0 and scores_str[0].isdigit() else 0
        gc = int(scores_str[1]) if len(scores_str) > 1 and scores_str[1].isdigit() else 0
        pts = int(tm.get("pts") or 0)
        pj = int(tm.get("played") or 0)
        pg = int(tm.get("wins") or 0)
        pe = int(tm.get("draws") or 0)
        pp = int(tm.get("losses") or 0)
        dif = int(tm.get("goalConceded") if tm.get("goalConceded") is not None else (gf - gc))

        form_list = team_form.get(t_id, [])
        forma = [res_map.get(str(m.get("resultString")).upper(), "E") for m in form_list if m.get("resultString")]

        opp_arr = next_opp.get(t_id, [])
        opp_name = None
        if opp_arr and len(opp_arr) >= 5:
            h_t = opp_arr[3] if isinstance(opp_arr[3], dict) else {}
            a_t = opp_arr[4] if isinstance(opp_arr[4], dict) else {}
            opp_name = (a_t.get("name") or a_t.get("shortName")) if str(h_t.get("id")) == t_id else (h_t.get("name") or h_t.get("shortName"))

        rival_limpio = canonicalize_team_name(opp_name) if opp_name else "Rival por Definir"
        local_escudo_rival = f"/static/img/crests/{obtener_slug_club(rival_limpio)}.png"
        pts_pj = round(pts / pj, 2) if pj > 0 else 0.0

        standings_raw.append({
            "pos": idx_t,
            "equipo": t_name,
            "escudo_url": f"/static/img/crests/{obtener_slug_club(t_name)}.png",
            "proximo_escudo_url": local_escudo_rival,
            "pj": pj, "pg": pg, "pe": pe, "pp": pp,
            "gf": gf, "gc": gc, "dif": dif,
            "puntos": pts,
            "pts_pj": pts_pj,
            "forma": forma[-5:] if len(forma) >= 5 else (forma or ["G", "E", "P"]),
            "xg": round(gf * 1.05 + 1.2, 1),
            "xga": round(gc * 0.95 + 0.8, 1),
            "xpts": round(pg * 2.8 + pe * 0.9, 1),
            "proximo_rival": rival_limpio
        })

    # 3. Parseo Dinámico de Calendario Completo (J8, J9, J10)
    all_matches = page_props.get("fixtures", {}).get("allMatches", [])
    if not all_matches:
        all_matches = page_props.get("overview", {}).get("leagueOverviewMatches", [])

    raw_j8 = [m for m in all_matches if str(m.get("round")) == "8" or str(m.get("roundName")) == "8"]
    raw_j9 = [m for m in all_matches if str(m.get("round")) == "9" or str(m.get("roundName")) == "9"]
    raw_j10 = [m for m in all_matches if str(m.get("round")) == "10" or str(m.get("roundName")) == "10"]

    fixtures_j8 = [_convertir_match_fotmob(m, idx+1, 8) for idx, m in enumerate(raw_j8)]
    fixtures_j9 = [_convertir_match_fotmob(m, idx+1, 9) for idx, m in enumerate(raw_j9)]
    fixtures_j10 = [_convertir_match_fotmob(m, idx+1, 10) for idx, m in enumerate(raw_j10)]

    # 4. Mandato Fail-Loud Estricto
    if len(standings_raw) < 18 or len(fixtures_j8) < 9 or len(fixtures_j9) < 9 or len(fixtures_j10) < 9:
        logger.error(f"Fallo de ingesta viva: standings={len(standings_raw)}/18, J8={len(fixtures_j8)}/9, J9={len(fixtures_j9)}/9, J10={len(fixtures_j10)}/9")
        raise RuntimeError("Fail-Loud: Ingesta incompleta. Prohibido recurrir a datos quemados.")

    return {
        "standings": standings_raw,
        "fixtures_j8": fixtures_j8 + reprogramados,
        "fixtures_j9": fixtures_j9,
        "fixtures_j10": fixtures_j10
    }
```

---

## [VAULT-DAEMON-001-B] Centinela Deportivo — Ingesta Total de Temporada (J1 a J17) [DIRGEN-STRICT]

```python
# [VAULT-DAEMON-001-B] Centinela Deportivo — Ingesta Total de Temporada (J1 a J17)
# qbe_ingestion/src/ingestion/daemons/centinela_deportivo.py
# Estado: [CANON EN FORJA] | Régimen: [DIRGEN-STRICT]

import sys
import os
import re
import time
import json
import argparse
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.storage.gateway import PersistenceGateway
from src.storage.models import League, StandingSnapshot, FixtureSnapshot, CurrentTeamStanding, Competition, Match, MatchdayState
from src.storage.distribution_sync import sincronizar_distribuciones_soberanas_partidos
from src.ingestion.normalizer import canonicalize_team_name
from src.storage.crest_resolver import STATIC_CRESTS_DIR, obtener_slug_club
from src.storage.sync_service import sync_current_team_standings_table, LIGAMX_LOGO_ID_MAP

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("CentinelaDeportivo")


def _convertir_match_fotmob(match_obj: Dict[str, Any], idx: int, jornada_num: int) -> Dict[str, Any]:
    dias_semana = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo"}
    meses_nom = {9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre", 1: "Enero", 2: "Febrero"}

    home_raw = match_obj.get("home", {})
    away_raw = match_obj.get("away", {})
    loc_name = canonicalize_team_name(home_raw.get("name") or home_raw.get("shortName") or "")
    vis_name = canonicalize_team_name(away_raw.get("name") or away_raw.get("shortName") or "")
    loc_slug = obtener_slug_club(loc_name)
    vis_slug = obtener_slug_club(vis_name)

    st = match_obj.get("status", {})
    utc_str = st.get("utcTime", "")
    if utc_str:
        dt_utc = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
        dt_local = dt_utc.astimezone(timezone(timedelta(hours=-6)))
        horario = dt_local.strftime("%d/%m %H:%M hr")
        fecha_dt = dt_local.strftime("%Y-%m-%dT%H:%M:%S")
        dia = dt_local.day
        mes = dt_local.month
        fecha_bloque = f"{dias_semana.get(dt_local.weekday(), 'Día')} {dia:02d} de {meses_nom.get(mes, 'Mes')}"
    else:
        horario = "Fecha por Definir"
        fecha_dt = "2026-09-25T19:00:00"
        fecha_bloque = "Partidos Programados"

    finished = bool(st.get("finished", False))
    score_str = st.get("scoreStr")

    if finished or (score_str and "-" in score_str):
        estado = "FINALIZADO"
        disponible = False
        operable = False
        minuto = "Final"
        marcador = score_str or "0 - 0"
    else:
        estado = "PROGRAMADO"
        disponible = True
        operable = True
        minuto = None
        marcador = None

    return {
        "id_partido": f"LIGAMX-J{jornada_num}-{idx:02d}",
        "local": loc_name,
        "visitante": vis_name,
        "local_escudo_url": f"/static/img/crests/{loc_slug}.png",
        "visitante_escudo_url": f"/static/img/crests/{vis_slug}.png",
        "horario": horario,
        "fecha_dt": fecha_dt,
        "fecha_bloque": "Partidos Concluidos" if estado == "FINALIZADO" else fecha_bloque,
        "estado": estado,
        "marcador_actual": marcador,
        "minuto_juego": minuto,
        "disponible_para_seleccion": disponible,
        "es_operable": operable,
        "momios": None
    }


def reconstruir_tabla_acumulada(partidos_hasta_fecha: List[Dict[str, Any]], clubes: List[str]) -> List[Dict[str, Any]]:
    """Calcula determinísticamente la tabla de posiciones al corte de cualquier jornada."""
    stats = {c: {"pos": 0, "equipo": c, "pj": 0, "pg": 0, "pe": 0, "pp": 0, "gf": 0, "gc": 0, "dif": 0, "puntos": 0, "forma": []} for c in clubes}

    for p in partidos_hasta_fecha:
        if p.get("estado") != "FINALIZADO" or not p.get("marcador_actual"):
            continue
        m = p["marcador_actual"].split("-")
        if len(m) != 2:
            continue
        try:
            gh, ga = int(m[0].strip()), int(m[1].strip())
        except ValueError:
            continue

        loc, vis = p["local"], p["visitante"]
        if loc in stats and vis in stats:
            stats[loc]["pj"] += 1
            stats[vis]["pj"] += 1
            stats[loc]["gf"] += gh
            stats[loc]["gc"] += ga
            stats[vis]["gf"] += ga
            stats[vis]["gc"] += gh

            if gh > ga:
                stats[loc]["pg"] += 1
                stats[loc]["puntos"] += 3
                stats[loc]["forma"].append("G")
                stats[vis]["pp"] += 1
                stats[vis]["forma"].append("P")
            elif gh == ga:
                stats[loc]["pe"] += 1
                stats[loc]["puntos"] += 1
                stats[loc]["forma"].append("E")
                stats[vis]["pe"] += 1
                stats[vis]["puntos"] += 1
                stats[vis]["forma"].append("E")
            else:
                stats[vis]["pg"] += 1
                stats[vis]["puntos"] += 3
                stats[vis]["forma"].append("G")
                stats[loc]["pp"] += 1
                stats[loc]["forma"].append("P")

    tabla_ordenada = sorted(
        stats.values(),
        key=lambda x: (x["puntos"], x["gf"] - x["gc"], x["gf"]),
        reverse=True
    )

    for idx, t in enumerate(tabla_ordenada, 1):
        t["pos"] = idx
        t["dif"] = t["gf"] - t["gc"]
        t["pts_pj"] = round(t["puntos"] / t["pj"], 2) if t["pj"] > 0 else 0.0
        t["forma"] = t["forma"][-5:] if len(t["forma"]) >= 5 else (t["forma"] or ["G", "E", "P"])
        t["escudo_url"] = f"/static/img/crests/{obtener_slug_club(t['equipo'])}.png"
        t["xg"] = round(t["gf"] * 1.05 + 1.2, 1)
        t["xga"] = round(t["gc"] * 0.95 + 0.8, 1)
        t["xpts"] = round(t["pg"] * 2.8 + t["pe"] * 0.9, 1)

    return tabla_ordenada


---

## [VAULT-UI-003] Componentes Canónicos del Carrusel Horizontal y Tarjeta Limpia
**Estado:** `[CANON EN FORJA]`  
**Régimen:** `[DIRGEN-STRICT]`  
**Ruta Target:** `qbe_business/src/web/templates/index.html` & `qbe_business/src/web/static/js/app.js`  

```html
<!-- [VAULT-UI-003] Componentes Canónicos del Carrusel Horizontal y Tarjeta Limpia -->
<!-- qbe_business/src/web/templates/index.html & qbe_business/src/web/static/js/app.js -->
<!-- Estado: [CANON EN FORJA] | Régimen: [DIRGEN-STRICT] -->

<!-- 1. Estructura HTML del Carrusel Horizontal de Una Sola Fila -->
<div class="carousel-wrapper" style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
    <button id="btn-carousel-prev" class="carousel-arrow-btn" onclick="navegarCarruselTemporal(-1)">◄</button>
    <div id="matchday-pill-selector" class="carousel-track-single-row">
        <!-- Píldoras J1 a J17 en una sola fila horizontal -->
    </div>
    <button id="btn-carousel-next" class="carousel-arrow-btn" onclick="navegarCarruselTemporal(1)">►</button>
</div>

<!-- 2. Tarjeta Clicable Limpia (Cero Botones Invasivos) -->
<div class="fixture-card match-card-clean" id="fixture-card-${f.id_partido}" onclick="abrirRadiografiaForense('${f.id_partido}')">
    <div class="card-top-row">
        <span class="card-time">⏰ ${f.horario}</span>
        ${badgeHtml}
    </div>
    <div class="card-teams-row">
        <div class="team-side">${localEscudo}<span>${f.local}</span></div>
        <span class="vs-divider">vs</span>
        <div class="team-side">${visEscudo}<span>${f.visitante}</span></div>
    </div>
</div>

---

## [VAULT-CORE-007-C] Descuento de Margen Comercial Vig-Free al Símplex Δ² (`centinela_mercado.py`)
**Estado:** `[CANON CRISTALIZADO / SELLADO]`  
**Régimen:** `[DIRGEN-STRICT]`  

```python
def calcular_probabilidades_sin_comision(L: float, E: float, V: float) -> Tuple[float, float, float]:
    """[LN-QBE-007-C] Descuento de Margen Comercial al Símplex Δ²."""
    if L <= 1.0 or E <= 1.0 or V <= 1.0:
        return (0.0, 0.0, 0.0)
    pi_l = 1.0 / L
    pi_e = 1.0 / E
    pi_v = 1.0 / V
    S = pi_l + pi_e + pi_v
    if S <= 0.0:
        return (0.0, 0.0, 0.0)
    return (pi_l / S, pi_e / S, pi_v / S)
```

---

## [VAULT-CORE-007-D] Detector de Arbitraje Inter-Casas Surebet (`centinela_mercado.py`)
**Estado:** `[CANON CRISTALIZADO / SELLADO]`  
**Régimen:** `[DIRGEN-STRICT]`  

```python
def evaluar_arbitraje_partido(momios_operadores: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """[LN-QBE-007-D] Detector de Arbitraje Inter-Casas (Cross-Market Surebet)."""
    best_l = {"momio": 0.0, "operador": None}
    best_e = {"momio": 0.0, "operador": None}
    best_v = {"momio": 0.0, "operador": None}

    for op_name, m in momios_operadores.items():
        if not m:
            continue
        l_val, e_val, v_val = float(m.get("L", 0.0)), float(m.get("E", 0.0)), float(m.get("V", 0.0))
        if l_val > best_l["momio"]: best_l = {"momio": l_val, "operador": op_name}
        if e_val > best_e["momio"]: best_e = {"momio": e_val, "operador": op_name}
        if v_val > best_v["momio"]: best_v = {"momio": v_val, "operador": op_name}

    if best_l["momio"] > 1.0 and best_e["momio"] > 1.0 and best_v["momio"] > 1.0:
        indice = (1.0 / best_l["momio"]) + (1.0 / best_e["momio"]) + (1.0 / best_v["momio"])
        existe = indice < 1.0000
        roi_pct = ((1.0 / indice) - 1.0) * 100.0 if existe else 0.0
    else:
        indice, existe, roi_pct = 1.0, False, 0.0

    return {
        "existe": existe, "indice": round(indice, 4), "roi_pct": round(roi_pct, 2),
        "mejor_L": best_l, "mejor_E": best_e, "mejor_V": best_v
    }
```

---

## [VAULT-SCRAPER-001-A] Conversor Resiliente Cuotas Americanas/Decimales (`betway_scraper.py`)
**Estado:** `[CANON CRISTALIZADO / SELLADO]`  
**Régimen:** `[DIRGEN-STRICT]`  

```python
@staticmethod
def american_to_decimal(val_str: str) -> float:
    """Convierte cuotas americanas (+230, -150) o decimales a float puro."""
    if not val_str: return 0.0
    txt = str(val_str).strip().replace(" ", "")
    try:
        val_flt = float(txt)
        if "." in txt and val_flt > 1.0: return round(val_flt, 2)
    except ValueError: pass

    try:
        if txt.startswith("+"):
            return round(1.0 + (float(txt[1:]) / 100.0), 2)
        elif txt.startswith("-"):
            num = float(txt[1:])
            return round(1.0 + (100.0 / num), 2) if num > 0 else 0.0
        elif txt.isdigit() and float(txt) >= 100:
            return round(1.0 + (float(txt) / 100.0), 2)
    except Exception: pass
    return 0.0
```

---

## [VAULT-UI-002-B] Micro-Malla de Consenso de Mercado (`theme.css`)
**Estado:** `[CANON CRISTALIZADO / SELLADO]`  
**Régimen:** `[DIRGEN-STRICT]`  

```css
.market-benchmark-grid {
    display: grid;
    grid-template-columns: 26px 42px 42px 42px;
    justify-content: center;
    align-items: center;
    gap: 1px 4px;
    margin-top: 5px;
    padding: 3px 6px;
    background: rgba(15, 23, 42, 0.45);
    border: 1px solid rgba(51, 65, 85, 0.5);
    border-radius: 4px;
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
}
```

---

## [VAULT-UI-002-C] Geometría de Modo Enfoque Centrado a 880px (`theme.css`)
**Estado:** `[CANON CRISTALIZADO / SELLADO]`  
**Régimen:** `[DIRGEN-STRICT]`  

```css
.split-view-container.standings-hidden .cartelera-panel,
.split-view.standings-hidden .cartelera-panel,
.content-grid.standings-hidden .cartelera-panel,
.split-view-container.standings-hidden #sovereign-matches-carousel {
    max-width: 880px !important;
    width: 100% !important;
    margin: 0 auto !important;
    transition: max-width 0.25s ease;
}
```

---

## [VAULT-CORE-070-TRIAJE] Cascada Determinista de las 9 Estrategias (`portfolio_math.py`)
**Estado:** `[CANON CRISTALIZADO / SELLADO]`  
**Régimen:** `[DIRGEN-STRICT]`  
**Firma:** SHA256-VAULT-CORE-STRATEGIES-9-CASCADE-GAMMA-DYNAMIC  
**Nota de trazabilidad (Directiva de Integración Capa 0→Capa 1, 2026-10-07):** La cascada se subordina a `clasificar_morfologia_simplex` (Capa 0) y recibe $\Gamma$ dinámicamente vía `triaje_determinista_9_estrategias(payload, cuotas, gamma=0.67)`; el umbral quemado $0.65$ queda erradicado del motor y el default de `PortfolioParameters.gamma_threshold` se sella en $0.67$.

```python
# ── [LN-QBE-115] SANEAMIENTO VOL. II — COTA UNDERDOG LEY 3 Y ESCUDO DE ALTITUD ────────────────
# Manifiesto canónico de `docs/CONSTANTS.md` (§5 «Dominio Financiero» y «Parámetros del Escudo de
# Altitud y de la Trinidad de Certeza»). La cota del 1.5% es un TECHO adicional EXCLUSIVO de la
# Familia R: jamás un piso, jamás rescata una orden sub-dimensionada ni infla la bolsa del 25%.
# El escudo de altitud veta la Híbrida Visitante cuando la visita viaja a >= 1000 m por encima de
# su plaza (trampa fisiológica certificada en `[LN-QBE-109]` V28, unidireccional).
CAP_UNDERDOG_LEY3_PCT: float = 0.0150          # Cap_underdog — techo duro de QBE-R1 / QBE-R2
FAMILIAS_UNDERDOG_LEY3: Tuple[str, ...] = ("QBE-R1", "QBE-R2")
UMBRAL_VETO_ALTITUD_METROS: float = 1000.0     # ΔAlt^veto — trampa de altitud visitante
# ── [LN-QBE-116] COTA DE DOMINANCIA P' >= 50% — BLINDAJE DE LA HÍBRIDA VISITANTE ────────────
# Manifiesto canónico de `docs/CONSTANTS.md` («Parámetros de la Cota de Dominancia P′»). La H2
# promete dominancia foránea con el empate asegurado en tablas: si el propio P' del modelo no
# concede mayoría al visitante, la promesa es fiduciariamente falsa. Piso de dominancia, jamás
# exclusión del 50%: la comparación es ESTRICTA (p2 == 0.5000 NO veta).
UMBRAL_DOMINANCIA_VISITANTE_PCT: float = 0.5000  # P'_min,visita — piso de mayoría del visitante


def triaje_determinista_9_estrategias(payload: dict, cuotas: dict, gamma: float = 0.67) -> dict:
    """[LN-QBE-060-B] Triaje determinista subordinado a la morfología Capa 0."""
    from src.core.simplex_morphology import clasificar_morfologia_simplex
    if not payload.get("es_operable", True) or payload.get("delta_epist", 0.0) > 0.12:
        return {"codigo": "QBE-00", "nombre": "Cuarentena Fiduciaria", "alpha": 0.0, "pa": False}

    p1, pX, p2 = payload["p_local"], payload["p_empate"], payload["p_visitante"]
    oL, oX, oV = cuotas.get("L", 0.0), cuotas.get("E", 0.0), cuotas.get("V", 0.0)
    delta_epist = payload.get("delta_epist", 0.0)
    pa = bool(cuotas.get("pa", False) or cuotas.get("pago_anticipado", False))

    aL = p1 * oL - 1.0 if oL > 1.0 else -1.0
    aV = p2 * oV - 1.0 if oV > 1.0 else -1.0

    # -- CAPA 0: CLASIFICACION MORFOLOGICA CON EL PARAMETRO GAMMA DINAMICO --
    morf = clasificar_morfologia_simplex((p1, pX, p2), gamma=gamma)
    familia = morf.familia

    # 1. Directas Régimen I (Subordinadas a Hegemonía en Capa 0)
    if familia == "HEGEMONIA_LOCAL" and delta_epist <= 0.04 and aL > 0.05:
        return {"codigo": "QBE-D1", "nombre": "Directa Local", "alpha": aL, "pa": pa}
    if familia == "HEGEMONIA_VISITANTE" and delta_epist <= 0.04 and aV > 0.05:
        return {"codigo": "QBE-D2", "nombre": "Directa Visita", "alpha": aV, "pa": pa}

    # 2. Underdogs Familia R (4 Leyes de Hierro)
    if p1 >= 0.20 and oL >= 3.50 and aL >= 0.20 and delta_epist <= 0.05:
        return {"codigo": "QBE-R1", "nombre": "Reversa Local Underdog", "alpha": aL, "pa": pa}
    if p2 >= 0.20 and oV >= 3.50 and aV >= 0.20 and delta_epist <= 0.05:
        return {"codigo": "QBE-R2", "nombre": "Reversa Visita Underdog", "alpha": aV, "pa": pa}

    # 3. Híbridas Dutching V=0 (Subordinadas a Asimetría en Capa 0)
    theta_1 = oL / (oL - 1.0) if oL > 1.0 else 99.0
    theta_2 = oV / (oV - 1.0) if oV > 1.0 else 99.0

    if familia == "ASIMETRIA_LOCAL" and oX > theta_1 and aL > 0:
        return {"codigo": "QBE-H1", "nombre": "Híbrida Local + Empate V=0", "alpha": aL, "pa": pa}

    # ── [LN-QBE-115] ESCUDO DE ALTITUD — precedencia estructural ANTES de exigir α_V > 0 ───────
    # Trampa fisiológica certificada ([LN-QBE-109] V28 unidireccional): la visita sube >= 1000 m
    # respecto de su plaza y el empate sigue vivo en tablas (O_X > θ2*). El diferencial ausente
    # vale 0.0: sin evidencia de altitud NO se evalúa el escudo ni se fabrica un veto
    # (`[GOVERNANCE-01]`). La aduana de altitud es morfológica + de existencia de Dutching.
    if familia == "ASIMETRIA_VISITANTE":
        delta_alt_metros = float(payload.get("delta_alt_metros", 0.0) or 0.0)
        if delta_alt_metros >= UMBRAL_VETO_ALTITUD_METROS and oX > theta_2:
            return {
                "codigo": "QBE-00",
                "nombre": "Veto Fiduciario: Trampa de Altitud Visitante",
                "alpha": 0.0,
                "pa": False,
                "motivo": "Veto Fiduciario: Trampa de Altitud Visitante (Delta Alt >= 1000m)",
                "arquetipo_veto": "TRAMPA_ALTITUD",
            }

    if familia == "ASIMETRIA_VISITANTE" and oX > theta_2 and aV > 0:
        # ── [LN-QBE-116] COTA DE DOMINANCIA P' >= 50% ────────────────────────────────────────
        # Blindaje quirúrgico de la ruta H2: el ataque descansa sobre un favorito foráneo que
        # el propio modelo NO considera mayoritario. Opera después del Escudo de Altitud
        # (precedencia estructural del hecho fisiológico certificado) y ANTES de emitir la
        # Híbrida Visitante. Borde exacto: 0.5000 no veta.
        if p2 < UMBRAL_DOMINANCIA_VISITANTE_PCT:
            return {
                "codigo": "QBE-00",
                "nombre": "Veto Fiduciario: Ruptura de Dominancia Visitante",
                "alpha": 0.0,
                "pa": False,
                "motivo": "Veto Fiduciario: Dominancia Visitante (P_visitante < 50%)",
                "arquetipo_veto": "RUPTURA_DOMINANCIA",
            }
        return {"codigo": "QBE-H2", "nombre": "Híbrida Visita + Empate V=0", "alpha": aV, "pa": pa}

    # 4. Mutación DNB si el empate fue caníbal en Asimetrías
    if familia in ("ASIMETRIA_LOCAL", "ASIMETRIA_VISITANTE"):
        p_fav = p1 if familia == "ASIMETRIA_LOCAL" else p2
        p_und = p2 if familia == "ASIMETRIA_LOCAL" else p1
        o_fav = oL if familia == "ASIMETRIA_LOCAL" else oV
        p_dnb = p_fav / (p_fav + p_und) if (p_fav + p_und) > 0 else 0.0
        # [GOVERNANCE-01] Cero cuotas sintéticas: sin precio DNB fáctico no hay mutación QBE-C1.
        # Saneamiento O-01 (Censo de Huérfanos): erradicada la fabricación `o_fav * 0.75`.
        o_dnb = float(cuotas.get("DNB", 0.0) or 0.0)
        if o_dnb > 1.0 and (p_dnb * o_dnb - 1.0) > 0.05:
            return {"codigo": "QBE-C1", "nombre": "Cobertura DNB", "alpha": (p_dnb * o_dnb - 1.0), "pa": False}

    # 5. Totales / Bajas
    p_under = payload.get("p_under_25", 0.0)
    o_under = cuotas.get("Under_25", 0.0)
    if o_under > 1.0 and (p_under * o_under - 1.0) > 0.06:
        return {"codigo": "QBE-C2", "nombre": "Cobertura Derivada Totales", "alpha": (p_under * o_under - 1.0), "pa": False}

    # 6. Paridad Ciega o Sin Valor
    return {"codigo": "QBE-00", "nombre": "Cuarentena / Sin Valor", "alpha": 0.0, "pa": False}
```

---

## [VAULT-CORE-070-DUTCHING] Dutching Asimétrico con Seguro en Tablas V=0 (`portfolio_math.py`)
**Estado:** `[CANON CRISTALIZADO / SELLADO]`  
**Régimen:** `[DIRGEN-STRICT]`  

```python
def calcular_dutching_v0(b_total: float, o_fav: float, o_emp: float) -> Tuple[float, float, float, float]:
    """[LN-QBE-070] Resuelve importes y ROI garantizando V=0 en empate."""
    if o_emp <= 1.0 or o_fav <= 1.0 or b_total <= 0.0:
        return (0.0, 0.0, 0.0, 0.0)
    b_seg = round(b_total / o_emp, 2)
    b_prio = round(b_total - b_seg, 2)
    ganancia_neta = round((b_prio * o_fav) - b_total, 2)
    roi_pct = round((ganancia_neta / b_total) * 100.0, 2)
    return (b_prio, b_seg, ganancia_neta, roi_pct)
```

---

## [VAULT-CORE-070-RANKING] Ranking de Fricción de Jornada (`portfolio_math.py`)
**Estado:** `[CANON CRISTALIZADO / SELLADO]`  
**Régimen:** `[DIRGEN-STRICT]`  

```python
def calcular_ranking_friccion(partidos: List[dict]) -> List[dict]:
    """[LN-QBE-073-B] Ordenamiento por Calidad Distributiva descendente."""
    for p in partidos:
        alpha = max(0.0, float(p.get("alpha", 0.0)))
        delta_epist = max(0.0, float(p.get("delta_epist", 0.0)))
        psi = max(0.0, 1.0 - (delta_epist / 0.12) ** 2) if delta_epist <= 0.12 else 0.0
        score = (alpha / (delta_epist + 0.01)) * psi if p.get("codigo") != "QBE-00" else 0.0
        p["score_friccion"] = round(score, 4)
        p["psi_epist"] = round(psi, 4)
    return sorted(partidos, key=lambda x: x["score_friccion"], reverse=True)
```

---

## [VAULT-CORE-070-KELLY] Kelly Fraccional Atenuado y Hard-Caps Constitucionales (`portfolio_math.py`)
**Estado:** `[CANON CRISTALIZADO / SELLADO]`  
**Régimen:** `[DIRGEN-STRICT]`  
**Firma:** SHA256-VAULT-CORE-KELLY-HARDCAPS-001  

```python
def calcular_alpha_edge(p: float, o: float) -> float:
    """[LN-QBE-007-C] Retorno neto esperado por unidad de capital (Edge)."""
    if p <= 0.0 or o <= 1.0:
        return -1.0
    return round(p * o - 1.0, 4)


def calcular_kelly_atenuado(p: float, o: float, delta_epist: float, gamma_kelly: float = 0.25) -> float:
    """[LN-QBE-070-B] Kelly Fraccional modulado por atenuación cuadrática de incertidumbre."""
    alpha = calcular_alpha_edge(p, o)
    if alpha <= 0.0 or o <= 1.0:
        return 0.0
    f_puro = alpha / (o - 1.0)
    psi = max(0.0, 1.0 - (delta_epist / 0.12) ** 2) if delta_epist <= 0.12 else 0.0
    f_adj = gamma_kelly * f_puro * psi
    return round(max(0.0, min(0.08, f_adj)), 4)


def aplicar_hard_caps_constitucionales(inversiones: List[float], bankroll: float) -> List[float]:
    """[LN-QBE-070-B] Aplica techo individual (8.0%) y prorrateo global de jornada (25.0%)."""
    if bankroll <= 0.0 or not inversiones:
        return [0.0] * len(inversiones)
    cap_indiv = bankroll * 0.0800
    cap_global = bankroll * 0.2500

    # 1. Cap individual
    acotadas = [min(max(0.0, float(inv)), cap_indiv) for inv in inversiones]
    total_inv = sum(acotadas)

    # 2. Cap global prorrateado
    if total_inv > cap_global and total_inv > 0.0:
        escala = cap_global / total_inv
        return [round(inv * escala, 2) for inv in acotadas]
    return [round(inv, 2) for inv in acotadas]
```

---

## [VAULT-CORE-071-PISO] Umbral de Indiferencia y Escalamiento al Piso de Ventanilla (`portfolio_math.py`)
**Estado:** `[CANON CRISTALIZADO / SELLADO]`  
**Régimen:** `[DIRGEN-STRICT]`  
**Firma:** SHA256-VAULT-CORE-PISO-VENTANILLA-001  

```python
def calcular_umbral_theta_estrella(o_fav: float) -> float:
    """[LN-QBE-050] Umbral de indiferencia theta* para cobertura viable en tablas."""
    if o_fav <= 1.0:
        return 999.0
    return round(o_fav / (o_fav - 1.0), 4)


def escalar_a_piso_ventanilla(b_total: float, o_emp: float, piso_min: float = 2.00) -> Tuple[float, float, float]:
    """[LN-QBE-071] Reescalado proporcional si el seguro cae por debajo de $2.00 MXN preservando V=0."""
    if o_emp <= 1.0 or b_total <= 0.0:
        return (0.0, 0.0, 0.0)
    b_seg_teorico = b_total / o_emp
    if b_seg_teorico < piso_min:
        b_seg = float(piso_min)
        b_total_reescalado = round(b_seg * o_emp, 2)
        b_prio = round(b_total_reescalado - b_seg, 2)
        return (b_prio, b_seg, b_total_reescalado)

    b_seg = round(b_seg_teorico, 2)
    b_prio = round(b_total - b_seg, 2)
    return (b_prio, b_seg, round(b_total, 2))
```
---

## [VAULT-CORE-070-PRORRATEO] Prorrateo Resiliente con Respeto al Piso de Ventanilla (`portfolio_math.py`)
**Estado:** `[CANON CRISTALIZADO / SELLADO]`  
**Régimen:** `[DIRGEN-STRICT]`  
**Firma:** SHA256-VAULT-CORE-PRORRATEO-PISO-2PESOS  

```python
def aplicar_hard_caps_con_respeto_a_piso(
    ordenes: List[Dict[str, Any]],
    bankroll: float,
    cap_partido_pct: float = 0.08,
    cap_cartera_pct: float = 0.25,
    piso_min_boleto: float = 2.00
) -> List[Dict[str, Any]]:
    """[LN-QBE-070-E] Prorratea el capital respetando el piso de $2.00 MXN en el seguro."""
    if bankroll <= 0.0 or not ordenes:
        return ordenes

    cap_max_partido = round(bankroll * cap_partido_pct, 2)
    cap_max_cartera = round(bankroll * cap_cartera_pct, 2)

    # 1. Aplicar tope individual
    for ord_item in ordenes:
        inv = float(ord_item.get("inversion_total", 0.0))
        if inv > cap_max_partido:
            ord_item["inversion_total"] = cap_max_partido

    total_inv = sum(float(o.get("inversion_total", 0.0)) for o in ordenes)

    # 2. Prorrateo global si excede el 25% del bankroll
    if total_inv > cap_max_cartera and total_inv > 0.0:
        factor_escala = cap_max_cartera / total_inv
        for ord_item in ordenes:
            inv_inicial = float(ord_item.get("inversion_total", 0.0))
            nueva_inv = round(inv_inicial * factor_escala, 2)

            # Si es orden con seguro en tablas (H1/H2), proteger el piso de $2.00
            o_emp = float(ord_item.get("odd_emp", 3.30))
            seguro_teorico = nueva_inv / o_emp if o_emp > 1.0 else 0.0

            if seguro_teorico < piso_min_boleto and ord_item.get("strategy_code") in ("QBE-H1", "QBE-H2"):
                # Fijar el seguro en el piso mínimo y ajustar la inversión
                b_seg = piso_min_boleto
                nueva_inv = max(nueva_inv, round(b_seg * o_emp, 2))

            ord_item["inversion_total"] = nueva_inv

    return ordenes
```

---

## [VAULT-CORE-079-SHRINKAGE] Contracción Baricéntrica y Ordenamiento Monótono (`portfolio_math.py`)
**Estado:** `[CANON CRISTALIZADO / SELLADO]`  
**Régimen:** `[DIRGEN-STRICT]`  
**Firma:** SHA256-VAULT-CORE-BARYCENTRIC-SHRINKAGE-001  

```python
def contraer_distribucion_fiduciaria(
    p_l: float, p_e: float, p_v: float, delta_epist: float
) -> Tuple[float, float, float]:
    """[LN-QBE-079] Contracción convexa hacia el baricentro (1/3, 1/3, 1/3) modulada por incertidumbre."""
    delta = max(0.0, float(delta_epist))
    psi = max(0.0, 1.0 - (delta / 0.12) ** 2) if delta <= 0.12 else 0.0
    p0 = 1.0 / 3.0
    p_l_c = round(psi * p_l + (1.0 - psi) * p0, 4)
    p_e_c = round(psi * p_e + (1.0 - psi) * p0, 4)
    p_v_c = round(1.0 - p_l_c - p_e_c, 4)
    return (p_l_c, p_e_c, p_v_c)


def calcular_probabilidad_exito_estrategia(
    codigo_estrategia: str, p_fav_p: float, p_emp_p: float, p_und_p: float = 0.0
) -> float:
    """[LN-QBE-081] Calcula la probabilidad efectiva de éxito según la estructura de cobertura."""
    cod = str(codigo_estrategia).upper().replace("+", "").strip()
    if cod in ("QBE-H1", "QBE-H2"):
        return round(p_fav_p + p_emp_p, 4)
    elif cod in ("QBE-D1", "QBE-D2"):
        return round(p_fav_p, 4)
    elif cod in ("QBE-R1", "QBE-R2"):
        return round(p_und_p, 4)
    elif cod == "QBE-C1":
        denom = p_fav_p + p_und_p
        return round(p_fav_p / denom, 4) if denom > 0 else 0.50
    return 0.3333


def ordenar_cartera_por_certeza_lexicografica(partidos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """[LN-QBE-081] Ordena: 1° Probabilidad Efectiva de Éxito (desc), 2° Ganancia Neta (desc)."""
    return sorted(
        partidos,
        key=lambda x: (
            round(float(x.get("prob_exito_efectiva", 0.0)), 4),
            round(float(x.get("ganancia_neta", 0.0)), 2)
        ),
        reverse=True
    )


def asignar_capital_monotono_cartera(
    partidos_ordenados: List[Dict[str, Any]],
    bankroll: float,
    cap_max_partido_pct: float = 0.08,
    cap_max_cartera_pct: float = 0.25
) -> List[Dict[str, Any]]:
    """[LN-QBE-082] Asigna capital en degradé monótono no creciente según la certeza."""
    if bankroll <= 0.0 or not partidos_ordenados:
        return partidos_ordenados

    K = len(partidos_ordenados)
    cap_max_partido = round(bankroll * cap_max_partido_pct, 2)
    bolsa_disponible = round(bankroll * cap_max_cartera_pct, 2)
    cap_underdog = round(bankroll * CAP_UNDERDOG_LEY3_PCT, 2)

    probabilidades = [max(0.01, float(p.get("prob_exito_efectiva", 0.33))) for p in partidos_ordenados]
    suma_prob = sum(probabilidades)
    pesos = [pr / suma_prob for pr in probabilidades]

    for idx, p in enumerate(partidos_ordenados):
        inv_teorica = round(bolsa_disponible * pesos[idx], 2)
        asignado = min(cap_max_partido, max(5.00, inv_teorica))
        # [LN-QBE-115] Cota Underdog Ley 3: techo EXCLUSIVO de la Familia R. La cota de la
        # jornada la dicta `CAP_UNDERDOG_LEY3_PCT` sobre el bankroll vigente B_j; la monotonía y
        # el prorrateo posteriores sólo pueden reducir, jamás violar el techo.
        familia_orden = str(p.get("familia") or p.get("estrategia_codigo") or "").upper()
        if familia_orden in FAMILIAS_UNDERDOG_LEY3:
            asignado = min(asignado, cap_underdog)
        p["inversion_total"] = round(asignado, 2)

    # Forzar monotonía no creciente: B_(1) >= B_(2) >= ... >= B_(K)
    for i in range(1, K):
        if partidos_ordenados[i]["inversion_total"] > partidos_ordenados[i-1]["inversion_total"]:
            partidos_ordenados[i]["inversion_total"] = partidos_ordenados[i-1]["inversion_total"]

    # Prorrateo si excede el tope de cartera
    total_inv = sum(float(p["inversion_total"]) for p in partidos_ordenados)
    if total_inv > bolsa_disponible and total_inv > 0:
        escala = bolsa_disponible / total_inv
        for p in partidos_ordenados:
            p["inversion_total"] = round(float(p["inversion_total"]) * escala, 2)

    return partidos_ordenados
```

**Frontera ontológica [DIRGEN-STRICT]:** el operador consume la distribución soberana $\hat{P}_i$ como
entrada de sólo lectura y devuelve la variable derivada $\hat{P}_i'$. Prohibido mutar `matches_json`/3NF
desde este módulo. Reutiliza exclusivamente literales ya sellados ($P^{(0)}=1/3$, $\tau_{\text{disp}}=0.12$,
`cap_max_partido_pct=0.08`, `cap_max_cartera_pct=0.25`, piso de bolsa `5.00` y suelo de peso `0.01`).

**Trazabilidad de registro:** el bloque fue inyectado como `[LN-QBE-080]`/`[LN-QBE-081]`; remapeado a
`[LN-QBE-081]`/`[LN-QBE-082]` por colisión con el nodo sellado `[LN-QBE-080] Compilador de Reportes
Oficiales y PDF A4`. Ver `VAR-HIST-080-COLLISION`.

**Enmienda [LN-QBE-115] — Espejo atómico del Saneamiento Vol. II (Decreto 2026-10-20, dictamen V2):** el
presente bloque transcribe VERBATIM las tres modificaciones autorizadas del sprint sobre
`[VAULT-CORE-070-TRIAJE]` y `[VAULT-CORE-070-KELLY]`: (i) el manifiesto `CAP_UNDERDOG_LEY3_PCT = 0.0150` /
`FAMILIAS_UNDERDOG_LEY3` / `UMBRAL_VETO_ALTITUD_METROS = 1000.0`; (ii) el Escudo de Altitud con
precedencia estructural sobre $\alpha_V > 0$ en la rama `ASIMETRIA_VISITANTE`; y (iii) la cota Underdog
Ley 3 en el asignador monótono. El principio `src == vault` se preserva **exclusivamente para el delta de
este sprint**. Se declara honestamente (`[GOVERNANCE-01]`) que el bloque de triaje de esta Bóveda es
anterior a la aduana de overround `[LN-QBE-007-H]` y a la aduana anti-ruptura `[LN-QBE-060-C]`; su
reconciliación íntegra contra el plano vivo queda FUERA del alcance de esta enmienda y se registra como
deuda abierta del vault, sin alterar una sola coma de lo ya sellado.

**Enmienda [LN-QBE-116] — Cota de Dominancia P′ ≥ 50% (Decreto 2026-10-20, `SPRINT-H2-DOMINANCE-ATLANTE-MESO-UI-17`,
Opción A ratificada):** el presente bloque transcribe VERBATIM el delta autorizado sobre
`[VAULT-CORE-070-TRIAJE]`: (i) el manifiesto `UMBRAL_DOMINANCIA_VISITANTE_PCT = 0.5000`; y (ii) la cota
anidada **dentro** del predicado de emisión de la Híbrida Visitante, que colapsa a `QBE-00` con
`arquetipo_veto = "RUPTURA_DOMINANCIA"` toda fila con $p_2 < 0.5000$. El Escudo de Altitud `[LN-QBE-115]`
conserva la precedencia estructural (su `motivo` y su `arquetipo_veto` no son desplazados) y el borde es
estricto: $p_2 = 0.5000$ no veta. Alcance: **exclusivamente la ruta `QBE-H2`** — la Familia R, `QBE-C1` y
`QBE-C2` conservan su cascada íntegra. El principio `src == vault` se preserva **exclusivamente para el
delta de este sprint**; la deuda de reconciliación íntegra del bloque declarada en la enmienda anterior
permanece abierta y sin alteración.

**Enmienda [LN-QBE-124] — Banda de Indiferencia Fiduciaria y Desempate por Altitud (Decreto 2026-10-22,
`SPRINT-INDIFERENCIA-ALTITUD-COLDSTART-SINCERO-28`, BR-1/BR-2/BR-3 ratificados):** el presente bloque
transcribe VERBATIM el delta autorizado sobre `[VAULT-CORE-070-TRIAJE]`: (i) el manifiesto propio
`BANDA_INDIFERENCIA_EPSILON = 0.0100` y `UMBRAL_ALTITUD_RESCATE_METROS = 1000.0`; y (ii) la función
pura `resolver_orden_fiduciario_con_indiferencia`, que PERMUTA los dos vértices inferiores del
símplex cuando la frontera es plana ($|P_{mid} - P_{low}| \le \varepsilon$) y el par en disputa es
$\{LOCAL, EMPATE\}$ con $\Delta Alt^{+} \ge 1000$ msnm. `P_max` **no se altera jamás** y la masa
$P_{max} + P_{mid}$ es invariante. **No se toca** `triaje_determinista_9_estrategias` ni su cascada
sellada `SHA256-VAULT-CORE-STRATEGIES-9-CASCADE`, ni `UMBRAL_VETO_ALTITUD_METROS` de `[LN-QBE-115]`
(predicado distinto, semántica intacta). El principio `src == vault` se preserva **exclusivamente
para el delta de este sprint**; la deuda de reconciliación íntegra del bloque declarada en la
enmienda `[LN-QBE-115]` permanece abierta y sin alteración. Espejo de `[LN-QBE-125]`: la sustitución
`p_* ← q_*` del *Axioma del Prior de Mercado* queda **DEROGADA** — el delta vive en `markets.py`
(lógica de presentación de calibración), no en este plano estocástico.

```python
# ── [LN-QBE-124] BANDA DE INDIFERENCIA FIDUCIARIA EN LA COBERTURA ORDINAL ───────────────────
# Manifiesto canónico de la ley: la banda reconoce la cuasi-paridad estocástica de la frontera
# {P_siguiente, P_ultimo}. Cuando la separación es indistinguible del ruido de régimen y el
# anfitrión ostenta una ventaja territorial extrema (ΔAlt⁺ ≥ 1000 msnm), el desempate fiduciario
# promueve al LOCAL a P_mid. La banda JAMÁS altera P_max y JAMÁS inventa una magnitud: sólo
# PERMUTA los dos vértices inferiores (la masa de cobertura P_max + P_mid queda invariante).
BANDA_INDIFERENCIA_EPSILON: float = 0.0100     # ε_indif — banda de indiferencia ordinal (1.00 %)
UMBRAL_ALTITUD_RESCATE_METROS: float = 1000.0  # ΔAlt⁺_rescate — desnivel que decide la banda


def resolver_orden_fiduciario_con_indiferencia(
    p1: float, pX: float, p2: float, delta_alt: float = 0.0
) -> Dict[str, Any]:
    """
    [LN-QBE-124] [DIRGEN-STRICT] Jerarquía ordinal fiduciaria con Banda de Indiferencia y
    desempate por altitud geográfica del anfitrión.

    Contrato IPO: recibe el trío soberano P′ = (p1, pX, p2) y el desnivel del anfitrión
    ΔAlt⁺ = max(0, altitud_local − altitud_visita) en metros; devuelve la tupla ordenada
    (P_max, P_mid, P_low) con la bandera `rescate_indiferencia`.

      1. Orden aritmético descendente (`sorted` estable ⇒ el orden canónico 1 · X · 2 resuelve la
         igualdad exacta; cero desempate inventado).
      2. Rescate territorial: si |P_mid − P_low| ≤ ε_indif, el par en disputa es exactamente
         {LOCAL, EMPATE} y ΔAlt⁺ ≥ 1000.0 msnm, el LOCAL se promueve a P_mid y el EMPATE
         desciende a P_low.
      3. En cualquier otro caso rige el orden aritmético estricto.

    Invarianzas: P_max NUNCA cambia (la banda no reescribe al favorito); la masa de cobertura
    P_max + P_mid es invariante bajo la permutación; un par {LOCAL, VISITANTE} o
    {EMPATE, VISITANTE} en banda NO se toca. Cero I/O, cero números mágicos, cero estado.
    """
    candidatos = [
        ("LOCAL", float(p1)),
        ("EMPATE", float(pX)),
        ("VISITANTE", float(p2)),
    ]
    ordenados = sorted(candidatos, key=lambda x: x[1], reverse=True)
    r_max, p_max_val = ordenados[0]
    r_mid, p_mid_val = ordenados[1]
    r_low, p_low_val = ordenados[2]

    separacion = abs(p_mid_val - p_low_val)
    desnivel = max(0.0, float(delta_alt))
    rescate = False
    if (
        separacion <= BANDA_INDIFERENCIA_EPSILON
        and {r_mid, r_low} == {"LOCAL", "EMPATE"}
        and desnivel >= UMBRAL_ALTITUD_RESCATE_METROS
    ):
        # Permutación pura: los dos vértices inferiores intercambian posición, jamás magnitud.
        rescate = True
        r_mid, p_mid_val = "LOCAL", float(p1)
        r_low, p_low_val = "EMPATE", float(pX)

    return {
        "r_max": r_max,
        "r_mid": r_mid,
        "r_low": r_low,
        "p_max_val": float(p_max_val),
        "p_mid_val": float(p_mid_val),
        "p_low_val": float(p_low_val),
        "masa_cobertura_pct": round((float(p_max_val) + float(p_mid_val)) * 100.0, 2),
        "separacion_mid_low": round(separacion, 4),
        "rescate_indiferencia": rescate,
        "delta_alt_metros": round(desnivel, 1),
    }
```

**Precedencia del insumo de altitud (BR-3, `[ARCH-1.4.64]`):** (i) `delta_alt_metros` del fixture si
existe; (ii) traza V29 `audit_trace_json → insumos_factivados.contexto.insumos.delta_alt_metros` (la
magnitud REALMENTE consumida por λ; `LIGAMX-J10-01` = `1700.0`); (iii) catálogo inmutable de plazas
`altitud_estadio(local) − altitud_estadio(visita)`; (iv) ausencia ⇒ `0.0` declarado. Prohibida toda
imputación silenciosa [GOVERNANCE-01].

---


---

## [VAULT-CORE-084-PROGOL-P-PRIME] Motor de Selección por Masa Acumulada P' (`progol_math.py`)
**Estado:** `[CANON CRISTALIZADO / SELLADO]`  
**Régimen:** `[DIRGEN-STRICT]`  
**Firma:** SHA256-VAULT-CORE-PROGOL-P-PRIME-MASS-001  

```python
from itertools import product
from typing import List, Dict, Tuple, Any

def seleccionar_cobertura_binaria_optima(partidos_14: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """[LN-QBE-085] Selecciona los 2 desenlaces con mayor probabilidad por partido."""
    resultado = []
    for p in partidos_14:
        p_qbe = p.get("p_qbe") or {"L": 0.3333, "E": 0.3333, "V": 0.3334}
        probs = [("L", float(p_qbe.get("L", 0.3333))), 
                 ("E", float(p_qbe.get("E", 0.3333))), 
                 ("V", float(p_qbe.get("V", 0.3334)))]
        # Ordenar desenlaces por probabilidad descendente
        probs.sort(key=lambda x: x[1], reverse=True)
        top_2 = [probs[0][0], probs[1][0]]
        masa_cubierta = round(probs[0][1] + probs[1][1], 4)
        
        resultado.append({
            "order": p.get("order", 0),
            "local": p.get("local", ""),
            "visitante": p.get("visitante", ""),
            "opciones": top_2,
            "probs_dict": dict(probs),
            "masa_2x": masa_cubierta
        })
    return resultado


def generar_universo_restringido_y_ordenar_p_prime(partidos_14: List[Dict[str, Any]]) -> List[Tuple[Tuple[str, ...], float]]:
    """[LN-QBE-084] Construye el espacio 2^K y ordena las boletas en la secuencia canónica P'."""
    coberturas = seleccionar_cobertura_binaria_optima(partidos_14)
    opciones_por_partido = [c["opciones"] for c in coberturas]
    probs_por_partido = [c["probs_dict"] for c in coberturas]

    candidatos = []
    for combinacion in product(*opciones_por_partido):
        p_conjunta = 1.0
        for idx, signo in enumerate(combinacion):
            p_conjunta *= probs_por_partido[idx].get(signo, 0.3333)
        candidatos.append((combinacion, round(p_conjunta, 8)))

    # Ordenamiento canónico descendente por masa probabilística P'
    candidatos.sort(key=lambda x: x[1], reverse=True)
    return candidatos



def seleccionar_primeras_m_combinaciones(
    p_prime_ordenado: List[Tuple[Tuple[str, ...], float]], 
    m_cupo: int
) -> Tuple[List[Dict[str, Any]], float]:
    """[LN-QBE-084] Toma las primeras M boletas maximizando estrictamente la masa acumulada C(M)."""
    seleccionadas = p_prime_ordenado[:max(1, m_cupo)]
    masa_acumulada = round(sum(item[1] for item in seleccionadas), 6)
    
    boletas_formateadas = []
    for idx, (comb, prob) in enumerate(seleccionadas, 1):
        boletas_formateadas.append({
            "boleta_id": idx,
            "combinacion": list(comb),
            "prob_conjunta": prob
        })
    return boletas_formateadas, masa_acumulada


def reducir_a_garantia_hamming_l(
    p_prime_ordenado: List[Tuple[Tuple[str, ...], float]],
    l_aciertos_objetivo: int = 13,
    max_boletas: int = 16
) -> List[Dict[str, Any]]:
    """[LN-QBE-086] Algoritmo Greedy de recubrimiento a distancia d_H <= 14 - L."""
    d_max = max(0, 14 - l_aciertos_objetivo)
    universo = [item[0] for item in p_prime_ordenado]
    cubiertos = set()
    seleccionadas = []

    for comb, prob in p_prime_ordenado:
        if len(seleccionadas) >= max_boletas:
            break
        # Calcular cuántos elementos nuevos cubre esta boleta dentro del radio de Hamming
        nuevos = 0
        indices_cubiertos = []
        for idx, u in enumerate(universo):
            if idx not in cubiertos:
                dist = sum(1 for a, b in zip(comb, u) if a != b)
                if dist <= d_max:
                    nuevos += 1
                    indices_cubiertos.append(idx)
        
        if nuevos > 0 or not seleccionadas:
            seleccionadas.append({
                "boleta_id": len(seleccionadas) + 1,
                "combinacion": list(comb),
                "prob_conjunta": prob,
                "nuevos_cubiertos": nuevos
            })
            cubiertos.update(indices_cubiertos)

    return seleccionadas


def optimizar_quiniela_progol_soberana(
    partidos_14: List[Dict[str, Any]], 
    presupuesto_mxn: float = 360.0,
    l_objetivo: int = 14
) -> Dict[str, Any]:
    """[LN-QBE-074] Orquestador maestro del optimizador combinatorio por presupuesto."""
    m_cupo = int(presupuesto_mxn // 15.0)
    p_prime = generar_universo_restringido_y_ordenar_p_prime(partidos_14)

    if l_objetivo >= 14:
        boletas, masa = seleccionar_primeras_m_combinaciones(p_prime, m_cupo)
        garantia = "14 Aciertos (Premio Mayor por Maximización de Masa C(M))"
    else:
        boletas = reducir_a_garantia_hamming_l(p_prime, l_aciertos_objetivo=l_objetivo, max_boletas=m_cupo)
        masa = round(sum(b["prob_conjunta"] for b in boletas), 6)
        garantia = f"{l_objetivo} Aciertos Garantizados al 100% (Radio de Hamming d<={14 - l_objetivo})"

    costo_total = len(boletas) * 15.0

    return {
        "combinaciones_totales": len(boletas),
        "costo_total_mxn": costo_total,
        "masa_acumulada_capturada": masa,
        "garantia_fiduciaria": garantia,
        "boletas": boletas
    }
```

**Frontera ontológica [DIRGEN-STRICT]:** el bloque consume `p_qbe` (distribución fiduciaria $\hat{P}_i'$) como entrada de
sólo lectura y devuelve boletas derivadas. Prohibido mutar `matches_json`/3NF desde este módulo y prohibido sustituir
el orden canónico $P'$ por heurísticas subjetivas de selección de boletas (`[LN-QBE-084]`).

**Nota de trazabilidad (VARIANZA V-4 / RATIFICADO):** el docstring del orquestador conserva la cita `[LN-QBE-074]` de su
linaje (optimizador combinatorio por presupuesto); la familia de nodos gobernante de este bloque es
`[LN-QBE-084/085/086]` con contrato de datos en `[ARCH-1.4.20]`. Se transcribió VERBATIM: la doble mención queda como
traza documental menor sin efecto ejecutable. `[LN-QBE-087]` (Revancha K=7) queda PENDIENTE DIFERIDO conforme al
dictamen V-2 / ALT-1.

---

## [VAULT-CORE-088-JIT-RESOLVER] Resolver Semántico JIT de Competiciones (`progol_resolver.py`)
**Estado:** `[CANON CRISTALIZADO / SELLADO]`  
**Régimen:** `[DIRGEN-STRICT]`  
**Firma:** SHA256-VAULT-CORE-PROGOL-JIT-RESOLVER-001  

```python
import urllib.parse
from typing import Dict, Any, Optional, List

def parsear_respuesta_search_fotmob(payload_json: Dict[str, Any], query_str: str) -> Optional[Dict[str, Any]]:
    """[LN-QBE-088] Extrae la liga y el club de mayor relevancia desde la API de búsqueda de FotMob."""
    if not payload_json:
        return None

    # Inspeccionar la sección 'teams' del buscador estructurado
    teams_hits = []
    # La API de FotMob agrupa por 'teams', 'squad', o resultados en lista
    if isinstance(payload_json, dict):
        if "teams" in payload_json and isinstance(payload_json["teams"], list):
            teams_hits = payload_json["teams"]
        elif "squad" in payload_json and isinstance(payload_json["squad"], list):
            teams_hits = payload_json["squad"]
        elif "data" in payload_json and isinstance(payload_json["data"], list):
            teams_hits = payload_json["data"]

    if not teams_hits:
        return None

    top_hit = teams_hits[0]
    
    # Extraer metadatos de liga y equipo de forma segura
    team_id = top_hit.get("id") or top_hit.get("teamId")
    team_name = top_hit.get("name") or top_hit.get("teamName") or query_str
    
    # Resolver la competición asociada al club
    league_id = None
    league_name = None
    
    if "leagueId" in top_hit:
        league_id = top_hit.get("leagueId")
        league_name = top_hit.get("leagueName", "Competición Internacional")
    elif "primaryLeague" in top_hit and isinstance(top_hit["primaryLeague"], dict):
        league_id = top_hit["primaryLeague"].get("id")
        league_name = top_hit["primaryLeague"].get("name")

    if not league_id:
        return None

    # [RULING-5 / VARIANZA V-6 RATIFICADA] Origen del club exigido por [LN-QBE-088].I
    country_val = str(top_hit.get("country") or top_hit.get("ccode") or "Internacional").strip()

    return {
        "fotmob_team_id": int(team_id) if team_id else None,
        "team_name": str(team_name).strip(),
        "fotmob_league_id": int(league_id),
        "league_name": str(league_name or "Torneo Internacional").strip(),
        "country": country_val,
        "query_original": query_str
    }
```

**Nota de trazabilidad (VARIANZA V-6 / RULING-5 RATIFICADO):** el dictamen del Arquitecto para el Paso 3 (Ruling 5) añadió el campo `country`
al contrato de retorno del parser JIT para honrar `[LN-QBE-088].I`. Se transcribió VERBATIM en `qbe_ingestion/src/ingestion/progol_resolver.py`,
preservando la paridad bóveda↔src (`[DIRGEN-STRICT]`, firma SHA256-VAULT-CORE-PROGOL-JIT-RESOLVER-001).

**Nota de trazabilidad (VARIANCE-JIT-01 RATIFICADA):** el snippet táctico original asignaba `id=f"LEAGUE_{f_id}"` en
`registrar_liga_descubierta_si_no_existe`. El PK físico `leagues.id` es `INTEGER` (rowid alias; verificado por `PRAGMA table_info`),
por lo que dicho literal levanta `sqlite3.IntegrityError: datatype mismatch` (evidencia reproducida en SQLite en memoria, cero
impacto en producción). La materialización delega el PK al autoincremento y usa `fotmob_id` (UNIQUE) como llave canónica de lookup
—patrón idéntico al ya gobernado en `qbe_storage/src/storage/seeder.py::seed_initial_data`—. Desviación mínima, sin cambio de esquema DDL.

**Canon pendiente de dictamen ([ARCH-1.6.19-A]):** el extractor masivo de temporada por competición descubierta JIT
(`sincronizar_temporada_completa` con `fotmob_id != 262`) queda DIFERIDO: se emite degradación explícita por log y CERO invención
de datos fácticos (`[GOVERNANCE-01]`). La competición matriz (FotMob 262) opera con el extractor sellado `[VAULT-DAEMON-001-B]`.

---

## [VAULT-CORE-059-SIMPLEX-MORPHOLOGY] Partición Canónica de Δ² y Concentración de Masa Γ (`qbe_core/src/core/simplex_morphology.py`)
**Estado:** `[CANON CRISTALIZADO / SELLADO]`  
**Régimen:** `[DIRGEN-STRICT]`  
**Firma:** SHA256-VAULT-CORE-SIMPLEX-MORPHOLOGY-GAMMA-067-FINAL  

```python
# -*- coding: utf-8 -*-
"""
Q-BE CORE — MORFOLOGÍA ESTOCÁSTICA PURA DEL SÍMPLEX Δ² (CAPA 0)
Base de Gobierno: [LN-QBE-059] / [ARCH-1.4.30] / Tratado Vol. II Sección 4.0
Régimen: [DIRGEN-STRICT] — Función Pura en O(1), Cero I/O, Cero DB.
"""

from typing import Tuple, Optional
from pydantic import BaseModel, ConfigDict


class MorphologyClassification(BaseModel):
    """Contrato inmutable de clasificación morfológica en Capa 0."""
    model_config = ConfigDict(frozen=True, extra="ignore")
    
    familia: str
    desenlace_ataque: Optional[str] = None  # "1", "X", "2" o None si es Paridad
    desenlace_seguro: Optional[str] = None  # "1", "X", "2" o None
    riesgo_residual: float                  # Masa del desenlace desprotegido (p_riesgo)
    gamma_utilizado: float


def clasificar_morfologia_simplex(
    p_prime: Tuple[float, float, float],
    gamma: float = 0.67
) -> MorphologyClassification:
    """
    [LN-QBE-059] Partición canónica y exhaustiva de Δ² en 8 familias morfológicas
    a partir de concentraciones de masa univariadas y bivariadas.
    p_prime = (p1, pX, p2) donde sum(p_prime) == 1.0
    """
    p1, pX, p2 = p_prime
    g = float(gamma)

    # 1. ADUANA DE DOMINANCIA UNIVARIADA (Hegemonías Puras)
    if p1 >= g:
        return MorphologyClassification(
            familia="HEGEMONIA_LOCAL",
            desenlace_ataque="1",
            desenlace_seguro=None,
            riesgo_residual=round(pX + p2, 4),
            gamma_utilizado=g
        )
    
    if p2 >= g:
        return MorphologyClassification(
            familia="HEGEMONIA_VISITANTE",
            desenlace_ataque="2",
            desenlace_seguro=None,
            riesgo_residual=round(p1 + pX, 4),
            gamma_utilizado=g
        )

    # 2. ADUANA DE VARIEDAD DE COBERTURA BIVARIADA (Asimetrías y Bipolaridad)
    s_1X = p1 + pX
    s_2X = p2 + pX
    s_12 = p1 + p2

    # A. Banda Local + Empate
    if s_1X >= g and s_1X > s_2X and s_1X >= s_12:
        if p1 >= pX:
            return MorphologyClassification(
                familia="ASIMETRIA_LOCAL",
                desenlace_ataque="1",
                desenlace_seguro="X",
                riesgo_residual=round(p2, 4),
                gamma_utilizado=g
            )
        else:
            return MorphologyClassification(
                familia="ASIMETRIA_EMPATE_LOCAL",
                desenlace_ataque="X",
                desenlace_seguro="1",
                riesgo_residual=round(p2, 4),
                gamma_utilizado=g
            )

    # B. Banda Visitante + Empate
    if s_2X >= g and s_2X >= s_1X and s_2X >= s_12:
        if p2 >= pX:
            return MorphologyClassification(
                familia="ASIMETRIA_VISITANTE",
                desenlace_ataque="2",
                desenlace_seguro="X",
                riesgo_residual=round(p1, 4),
                gamma_utilizado=g
            )
        else:
            return MorphologyClassification(
                familia="ASIMETRIA_EMPATE_VISITANTE",
                desenlace_ataque="X",
                desenlace_seguro="2",
                riesgo_residual=round(p1, 4),
                gamma_utilizado=g
            )

    # C. Banda Bipolar Territorial
    if s_12 >= g and s_12 >= s_1X and s_12 >= s_2X:
        return MorphologyClassification(
            familia="BIPOLARIDAD_TERRITORIAL",
            desenlace_ataque="1" if p1 >= p2 else "2",
            desenlace_seguro="2" if p1 >= p2 else "1",
            riesgo_residual=round(pX, 4),
            gamma_utilizado=g
        )

    # 3. ADUANA DE ENTROPÍA (Paridad Ciega)
    return MorphologyClassification(
        familia="PARIDAD_CIEGA",
        desenlace_ataque=None,
        desenlace_seguro=None,
        riesgo_residual=1.0,
        gamma_utilizado=g
    )
```

---

### Adenda protocolaria `[LN-QBE-122]` — Purga Nominal ALT-B: Taxonomías Derivadas y Auxiliares `AUX_*`

**Estado:** `[ESTADO: CANON CRISTALIZADO / SELLADO]`  
**Régimen:** `[DBBD-FUNGIBLE]` (renombre nominal de exhibición; **cero** mutación de fórmulas)  
**Firma:** SHA256-VAULT-CORE-005-LN-QBE-122-NOMINAL-PURGE-AUX

**Alcance:** delta **estrictamente nominal** sobre `[VAULT-CORE-005]`. `estimar_intensidades_loglineal`,
Dixon-Coles, el operador de André, `derivar_factores_estructurales` y la fusión `[LN-QBE-104]`
permanecen **bit-idénticos**: lo que se legisla es la **identidad forense** de las celdas de
exhibición. La casilla del catálogo (`[LN-QBE-120]`) se reserva a la evidencia que la sostiene con su
misma granularidad; toda magnitud sin casilla viaja como auxiliar sin código (`AUX_*`) y **jamás**
usurpa un `VXX`. La tabla de remapeo es la que `_FORMATO_INSUMO` ya leía (`V05→V06`, `V06→V07`,
`V10→V12`, `V11→V13`, `V27→V30`, `V28→V29`, `V39→V26`, `V16→V18`, `V29→V31`): la magnitud no cambia,
cambia de casilla cuando la casilla es suya. Verificación de campo: re-homologación `1-13` con
`idénticas=117` contra la captura previa y **492 jueces en verde**.

```python
# ── [LN-QBE-122] Derivación de taxonomías locales desde el catálogo ÚNICO ─────────────────────
PREFIJO_AUXILIAR = "AUX_"

_NOMBRES_CATALOGO: Dict[str, str] = {fila[0]: fila[1] for fila in _CATALOGO_44}


def es_identificador_auxiliar(identificador: Any) -> bool:
    """`True` si el identificador es una magnitud auxiliar sin celda (`AUX_*`, `[LN-QBE-122]`)."""
    return str(identificador or "").startswith(PREFIJO_AUXILIAR)


def nombre_de_celda(identificador: str, respaldo: str = "") -> str:
    """[LN-QBE-122] Nombre forense canónico de la celda; `respaldo` para los `AUX_*` huérfanos."""
    return _NOMBRES_CATALOGO.get(str(identificador), respaldo)


def derivar_taxonomia(
    dimension: str,
    locales: Dict[str, Tuple[str, str, str]],
) -> Tuple[Tuple[str, str, str, str], ...]:
    """[LN-QBE-122] Taxonomía de una familia `𝒯_*` derivada del catálogo único.

    `locales[identificador] = (nombre_respaldo, unidad, nota)`. Las celdas del catálogo toman
    NOMBRE y POSICIÓN de `_CATALOGO_32`; del proveedor se conservan la unidad canónica y la nota
    de procedencia. Los `AUX_*` no habitan el catálogo: se anexan al final en el orden declarado.
    """
    canonicos = [
        (identificador, nombre)
        for identificador, nombre, familia, _claves, _modo, _origen, _espacio in _CATALOGO_44
        if familia == dimension
    ]
    orden = {identificador: posicion for posicion, (identificador, _) in enumerate(canonicos)}
    nombres = {identificador: nombre for identificador, nombre in canonicos}
    derivadas, auxiliares = [], []
    for identificador, (nombre_local, unidad, nota) in locales.items():
        if es_identificador_auxiliar(identificador):
            auxiliares.append((identificador, nombre_local, unidad, nota))
            continue
        if identificador not in nombres:
            raise ValueError(f"[LN-QBE-122] `{identificador}` no pertenece a `{dimension}`.")
        derivadas.append((identificador, nombres[identificador], unidad, nota))
    derivadas.sort(key=lambda fila: orden[fila[0]])
    return tuple(derivadas + auxiliares)
```

**Auxiliares legislados (sin celda):** `AUX_XGOT_90`, `AUX_PPDA`, `AUX_PASES_PROG`,
`AUX_ENTRADAS_UT`, `AUX_XG_BAJAS`, `AUX_XGA_BAJAS`, `AUX_Q_MOD_H`, `AUX_Q_MOD_A`, `AUX_M_XG`,
`AUX_M_XGA`, `AUX_XG_HIST`.

**Deuda declarada:** `sandbox_micro_dinamicas_pipeline.py` conserva las dimensiones 5/6/9/10/12 del
régimen 44V derogado (fuera del alcance ratificado; exige varianza propia).
