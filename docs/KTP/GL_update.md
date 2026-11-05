# GL_update — Bandeja de Revisión de Paridad Canónica

- **Nodo auditor:** `[LN-QBE-139]`
- **Juez:** `[LN-QBE-140]`
- **Sprint:** `SPRINT-50-REINGENIERIA-INDUSTRIAL-QBE-CORE`
- **Fuente de vigencia:** `docs/ID_REGISTRY.md` (estado `SELLADO`; regla de sprint 001–138).
- **Estado:** `PENDIENTE DEL DIRECTOR`

> Esta bandeja es una salida determinista del Auditor de Paridad. No corrige, no interpreta y no decide. El Director marca cada fila con **VÍA A (Erradicación)** o **VÍA B (Formalización)**.

## Resumen

| Métrica | Valor |
|---|---:|
| Archivos auditados | 27 |
| Reglas huérfanas | 23 |
| Clase I — Fabricación Sintética | 0 |
| Clase II — Contradicción Numérica | 0 |
| Clase III — Colisión de Literales | 0 |
| Clase IV — Heurísticas Permisivas | 23 |

## Hallazgos

| # | Archivo | Línea | Función / Nodo | Clase | Etiqueta | Evidencia | VEREDICTO DIRECTOR |
|---:|---|---:|---|---|---|---|---|
| 1 | `qbe_core/src/core/distribution_dixon_coles.py` | 34 | `_sigmoide_normalizada` | IV | — | `Nodo sin etiqueta canónica` |  |
| 2 | `qbe_core/src/core/intensity_canonical_loglink.py` | 17 | `InsufficientDataException` | IV | — | `Clase sin etiqueta canónica` |  |
| 3 | `qbe_core/src/core/intensity_canonical_loglink.py` | 25 | `__init__` | IV | — | `Nodo sin etiqueta canónica` |  |
| 4 | `qbe_core/src/core/intensity_canonical_loglink.py` | 76 | `calcular_alpha_ligadura` | IV | — | `Nodo sin etiqueta canónica` |  |
| 5 | `qbe_core/src/core/intensity_canonical_loglink.py` | 127 | `estimar_intensidades_loglineal` | IV | — | `Nodo sin etiqueta canónica` |  |
| 6 | `qbe_core/src/core/sovereign/orthogonal_factor_engine.py` | 198 | `orden_gs` | IV | — | `Nodo sin etiqueta canónica` |  |
| 7 | `qbe_core/src/core/sovereign/orthogonal_factor_engine.py` | 203 | `ResultadoGSL3Dv2` | IV | — | `Clase sin etiqueta canónica` |  |
| 8 | `qbe_core/src/core/sovereign/orthogonal_factor_engine.py` | 220 | `_normalizar_log` | IV | — | `Nodo sin etiqueta canónica` |  |
| 9 | `qbe_core/src/core/sovereign/orthogonal_factor_engine.py` | 230 | `_columnas_utilizables` | IV | — | `Nodo sin etiqueta canónica` |  |
| 10 | `qbe_core/src/core/sovereign/orthogonal_factor_engine.py` | 262 | `_gram_schmidt_modificado` | IV | — | `Nodo sin etiqueta canónica` |  |
| 11 | `qbe_core/src/core/sovereign/orthogonal_factor_engine.py` | 316 | `_sintetizar_espacio` | IV | — | `Nodo sin etiqueta canónica` |  |
| 12 | `qbe_core/src/core/sovereign/orthogonal_factor_engine.py` | 356 | `resolver_factores_latentes_gsl3d_v2` | IV | — | `Nodo sin etiqueta canónica` |  |
| 13 | `qbe_core/src/core/sovereign_pipeline.py` | 550 | `_salida_por_insuficiencia` | IV | — | `Nodo sin etiqueta canónica` |  |
| 14 | `qbe_core/src/core/sovereign_pipeline.py` | 641 | `_campo_obligatorio` | IV | — | `Nodo sin etiqueta canónica` |  |
| 15 | `qbe_core/src/core/sovereign_pipeline.py` | 805 | `derivar_factores_estructurales_v2` | IV | — | `Nodo sin etiqueta canónica` |  |
| 16 | `qbe_core/src/core/sovereign_pipeline.py` | 854 | `derivar_factores_super_senal` | IV | — | `Nodo sin etiqueta canónica` |  |
| 17 | `qbe_core/src/core/sovereign_pipeline.py` | 872 | `_factor` | IV | — | `Nodo sin etiqueta canónica` |  |
| 18 | `qbe_core/src/core/sovereign_pipeline.py` | 880 | `_tasas` | IV | — | `Nodo sin etiqueta canónica` |  |
| 19 | `qbe_core/src/core/sovereign_pipeline.py` | 893 | `generar_distribucion_v6` | IV | — | `Nodo sin etiqueta canónica` |  |
| 20 | `qbe_core/src/core/triage.py` | 132 | `veto_inmunidad_fiduciaria` | IV | — | `Nodo sin etiqueta canónica` |  |
| 21 | `qbe_core/src/core/triage.py` | 145 | `_alto` | IV | — | `Nodo sin etiqueta canónica` |  |
| 22 | `qbe_core/src/core/triage.py` | 148 | `_muy_alto` | IV | — | `Nodo sin etiqueta canónica` |  |
| 23 | `qbe_core/src/core/triage.py` | 151 | `_bajo` | IV | — | `Nodo sin etiqueta canónica` |  |

---

**VÍA A:** erradicación de la regla huérfana. **VÍA B:** formalización legislativa y etiquetado con Juez.
