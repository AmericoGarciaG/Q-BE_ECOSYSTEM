# GL_update — Bandeja de Revisión de Paridad Canónica

- **Nodo auditor:** `[LN-QBE-139]`
- **Juez:** `[LN-QBE-140]`
- **Sprint:** `SPRINT-51 — PENDIENTE DE RATIFICACIÓN`
- **Fuente de vigencia:** `docs/ID_REGISTRY.md` (estado `SELLADO`; regla de sprint 001–138).
- **Estado:** `PENDIENTE DEL DIRECTOR`

> Esta bandeja es una salida determinista del Auditor de Paridad. No corrige, no interpreta y no decide. El Director marca cada fila con **VÍA A (Erradicación)** o **VÍA B (Formalización)**.

## Resumen

| Métrica | Valor |
|---|---:|
| Archivos auditados | 42 |
| Reglas huérfanas | 112 |
| Clase I — Fabricación Sintética | 0 |
| Clase II — Contradicción Numérica | 0 |
| Clase III — Colisión de Literales | 0 |
| Clase IV — Heurísticas Permisivas | 112 |

## Hallazgos

| # | Archivo | Línea | Función / Nodo | Clase | Etiqueta | Evidencia | VEREDICTO DIRECTOR |
|---:|---|---:|---|---|---|---|---|
| 1 | `qbe_observatory/src/observatory/core/context_provider.py` | 84 | `_r` | IV | — | `Nodo sin etiqueta canónica` |  |
| 2 | `qbe_observatory/src/observatory/core/context_provider.py` | 89 | `_clamp` | IV | — | `Nodo sin etiqueta canónica` |  |
| 3 | `qbe_observatory/src/observatory/core/context_provider.py` | 94 | `_num` | IV | — | `Nodo sin etiqueta canónica` |  |
| 4 | `qbe_observatory/src/observatory/core/context_provider.py` | 215 | `parse_fecha` | IV | — | `Nodo sin etiqueta canónica` |  |
| 5 | `qbe_observatory/src/observatory/core/context_provider.py` | 241 | `normalizar_identidad` | IV | — | `Nodo sin etiqueta canónica` |  |
| 6 | `qbe_observatory/src/observatory/core/context_provider.py` | 275 | `identidad_coincide` | IV | — | `Nodo sin etiqueta canónica` |  |
| 7 | `qbe_observatory/src/observatory/core/context_provider.py` | 304 | `leer_fixture_cartelera` | IV | — | `Nodo sin etiqueta canónica` |  |
| 8 | `qbe_observatory/src/observatory/core/context_provider.py` | 334 | `partidos_terminales_de_club` | IV | — | `Nodo sin etiqueta canónica` |  |
| 9 | `qbe_observatory/src/observatory/core/context_provider.py` | 385 | `_catalogo_calendario` | IV | — | `Nodo sin etiqueta canónica` |  |
| 10 | `qbe_observatory/src/observatory/core/context_provider.py` | 410 | `_partido_previo` | IV | — | `Nodo sin etiqueta canónica` |  |
| 11 | `qbe_observatory/src/observatory/core/context_provider.py` | 496 | `_texto_dias` | IV | — | `Nodo sin etiqueta canónica` |  |
| 12 | `qbe_observatory/src/observatory/core/context_provider.py` | 500 | `_texto_metros` | IV | — | `Nodo sin etiqueta canónica` |  |
| 13 | `qbe_observatory/src/observatory/core/context_provider.py` | 504 | `_bloque_vacio_contexto` | IV | — | `Nodo sin etiqueta canónica` |  |
| 14 | `qbe_observatory/src/observatory/core/factor_attribution.py` | 44 | `_num` | IV | — | `Nodo sin etiqueta canónica` |  |
| 15 | `qbe_observatory/src/observatory/core/factor_attribution.py` | 57 | `_es_certificado` | IV | — | `Nodo sin etiqueta canónica` |  |
| 16 | `qbe_observatory/src/observatory/core/factor_attribution.py` | 72 | `_amortiguar` | IV | — | `Nodo sin etiqueta canónica` |  |
| 17 | `qbe_observatory/src/observatory/core/factor_attribution.py` | 455 | `_celda_h2h_stats` | IV | — | `Nodo sin etiqueta canónica` |  |
| 18 | `qbe_observatory/src/observatory/core/factor_attribution.py` | 501 | `_celda_trayectoria` | IV | — | `Nodo sin etiqueta canónica` |  |
| 19 | `qbe_observatory/src/observatory/core/factor_attribution.py` | 597 | `_formatear_macro` | IV | — | `Nodo sin etiqueta canónica` |  |
| 20 | `qbe_observatory/src/observatory/core/factor_attribution.py` | 616 | `_celda_macro_stats` | IV | — | `Nodo sin etiqueta canónica` |  |
| 21 | `qbe_observatory/src/observatory/core/factor_attribution.py` | 813 | `_insumos_del_bloque` | IV | — | `Nodo sin etiqueta canónica` |  |
| 22 | `qbe_observatory/src/observatory/core/factor_attribution.py` | 821 | `_aplanar_insumos` | IV | — | `Nodo sin etiqueta canónica` |  |
| 23 | `qbe_observatory/src/observatory/core/factor_attribution.py` | 840 | `_fusionar_planas` | IV | — | `Nodo sin etiqueta canónica` |  |
| 24 | `qbe_observatory/src/observatory/core/factor_attribution.py` | 917 | `_formatear_insumo` | IV | — | `Nodo sin etiqueta canónica` |  |
| 25 | `qbe_observatory/src/observatory/core/factor_attribution.py` | 941 | `_bloque_equipo` | IV | — | `Nodo sin etiqueta canónica` |  |
| 26 | `qbe_observatory/src/observatory/core/factor_attribution.py` | 950 | `_leer_clave` | IV | — | `Nodo sin etiqueta canónica` |  |
| 27 | `qbe_observatory/src/observatory/core/factor_attribution.py` | 962 | `_valor_tasa` | IV | — | `Nodo sin etiqueta canónica` |  |
| 28 | `qbe_observatory/src/observatory/core/factor_attribution.py` | 977 | `_h2h_secuencia` | IV | — | `Nodo sin etiqueta canónica` |  |
| 29 | `qbe_observatory/src/observatory/core/factor_attribution.py` | 984 | `_campo_partido` | IV | — | `Nodo sin etiqueta canónica` |  |
| 30 | `qbe_observatory/src/observatory/core/factor_attribution.py` | 990 | `_resumen_h2h` | IV | — | `Nodo sin etiqueta canónica` |  |
| 31 | `qbe_observatory/src/observatory/core/factor_attribution.py` | 1032 | `_valor_variable` | IV | — | `Nodo sin etiqueta canónica` |  |
| 32 | `qbe_observatory/src/observatory/core/factor_attribution.py` | 1186 | `_gamma_efectivo` | IV | — | `return 0.0 sin etiqueta canónica` |  |
| 33 | `qbe_observatory/src/observatory/core/simulation_engine.py` | 142 | `_a_float` | IV | — | `Nodo sin etiqueta canónica` |  |
| 34 | `qbe_observatory/src/observatory/core/simulation_engine.py` | 152 | `_marcador_valido` | IV | — | `Nodo sin etiqueta canónica` |  |
| 35 | `qbe_observatory/src/observatory/core/simulation_engine.py` | 213 | `_familias_con_cobertura` | IV | — | `Nodo sin etiqueta canónica` |  |
| 36 | `qbe_observatory/src/observatory/core/simulation_engine.py` | 218 | `_cubre_empate` | IV | — | `Nodo sin etiqueta canónica` |  |
| 37 | `qbe_observatory/src/observatory/core/simulation_engine.py` | 388 | `_cargar_jornada` | IV | — | `Nodo sin etiqueta canónica` |  |
| 38 | `qbe_observatory/src/observatory/core/simulation_engine.py` | 613 | `_dimensionar_y_liquidar` | IV | — | `Nodo sin etiqueta canónica` |  |
| 39 | `qbe_observatory/src/observatory/core/simulation_engine.py` | 908 | `_consolidar_reporte` | IV | — | `Nodo sin etiqueta canónica` |  |
| 40 | `qbe_observatory/src/observatory/core/simulation_engine.py` | 1132 | `_dibujar_curva_bankroll` | IV | — | `Nodo sin etiqueta canónica` |  |
| 41 | `qbe_observatory/src/observatory/core/simulation_engine.py` | 1153 | `_formatear_pesos` | IV | — | `Nodo sin etiqueta canónica` |  |
| 42 | `qbe_observatory/src/observatory/core/simulation_engine.py` | 1170 | `imprimir_tablero_rentabilidad_consola` | IV | — | `Nodo sin etiqueta canónica` |  |
| 43 | `qbe_observatory/src/observatory/core/simulation_engine.py` | 1282 | `parsear_rango_jornadas` | IV | — | `Nodo sin etiqueta canónica` |  |
| 44 | `qbe_observatory/src/observatory/core/simulation_engine.py` | 1313 | `construir_parser` | IV | — | `Nodo sin etiqueta canónica` |  |
| 45 | `qbe_observatory/src/observatory/core/simulation_engine.py` | 1349 | `main` | IV | — | `return 0.0 sin etiqueta canónica` |  |
| 46 | `qbe_observatory/src/observatory/core/sovereign_reads.py` | 42 | `_fila_partido` | IV | — | `Nodo sin etiqueta canónica` |  |
| 47 | `qbe_observatory/src/observatory/core/sovereign_reads.py` | 58 | `leer_fixture` | IV | — | `Nodo sin etiqueta canónica` |  |
| 48 | `qbe_observatory/src/observatory/core/sovereign_reads.py` | 64 | `leer_partidos_corte` | IV | — | `Nodo sin etiqueta canónica` |  |
| 49 | `qbe_observatory/src/observatory/core/sovereign_reads.py` | 76 | `leer_calendario` | IV | — | `Nodo sin etiqueta canónica` |  |
| 50 | `qbe_observatory/src/observatory/core/sovereign_reads.py` | 81 | `leer_telemetria` | IV | — | `Nodo sin etiqueta canónica` |  |
| 51 | `qbe_observatory/src/observatory/core/sovereign_reads.py` | 108 | `leer_snapshots_posiciones` | IV | — | `Nodo sin etiqueta canónica` |  |
| 52 | `qbe_observatory/src/observatory/legacy_ml/consenso_ensamble.py` | 51 | `ConsensoError` | IV | — | `Clase sin etiqueta canónica` |  |
| 53 | `qbe_observatory/src/observatory/legacy_ml/consenso_ensamble.py` | 55 | `cargar_pesos` | IV | — | `Nodo sin etiqueta canónica` |  |
| 54 | `qbe_observatory/src/observatory/legacy_ml/consenso_ensamble.py` | 65 | `_validar` | IV | — | `Nodo sin etiqueta canónica` |  |
| 55 | `qbe_observatory/src/observatory/legacy_ml/consenso_ensamble.py` | 76 | `_brier_matriz` | IV | — | `Nodo sin etiqueta canónica` |  |
| 56 | `qbe_observatory/src/observatory/legacy_ml/consenso_ensamble.py` | 95 | `_format` | IV | — | `Nodo sin etiqueta canónica` |  |
| 57 | `qbe_observatory/src/observatory/legacy_ml/consenso_ensamble.py` | 103 | `ejecutar` | IV | — | `Nodo sin etiqueta canónica` |  |
| 58 | `qbe_observatory/src/observatory/legacy_ml/consenso_ensamble.py` | 150 | `_tabla_pesos` | IV | — | `Nodo sin etiqueta canónica` |  |
| 59 | `qbe_observatory/src/observatory/legacy_ml/consenso_ensamble.py` | 169 | `_tabla_brier` | IV | — | `Nodo sin etiqueta canónica` |  |
| 60 | `qbe_observatory/src/observatory/legacy_ml/consenso_ensamble.py` | 191 | `_alertas` | IV | — | `Nodo sin etiqueta canónica` |  |
| 61 | `qbe_observatory/src/observatory/legacy_ml/consenso_ensamble.py` | 201 | `main` | IV | — | `Nodo sin etiqueta canónica` |  |
| 62 | `qbe_observatory/src/observatory/legacy_ml/fase7_meta_labeling.py` | 34 | `_cargar` | IV | — | `Nodo sin etiqueta canónica` |  |
| 63 | `qbe_observatory/src/observatory/legacy_ml/fase7_meta_labeling.py` | 44 | `main` | IV | — | `return 0.0 sin etiqueta canónica` |  |
| 64 | `qbe_observatory/src/observatory/legacy_ml/fase7_meta_labeling.py` | 126 | `_roi_calc` | IV | — | `Nodo sin etiqueta canónica` |  |
| 65 | `qbe_observatory/src/observatory/legacy_ml/meta_labeler.py` | 34 | `MetaLabeler` | IV | — | `Clase sin etiqueta canónica` |  |
| 66 | `qbe_observatory/src/observatory/legacy_ml/meta_labeler.py` | 37 | `__init__` | IV | — | `Nodo sin etiqueta canónica` |  |
| 67 | `qbe_observatory/src/observatory/legacy_ml/meta_labeler.py` | 43 | `_instanciar` | IV | — | `Nodo sin etiqueta canónica` |  |
| 68 | `qbe_observatory/src/observatory/legacy_ml/meta_labeler.py` | 61 | `fit` | IV | — | `Nodo sin etiqueta canónica` |  |
| 69 | `qbe_observatory/src/observatory/legacy_ml/meta_labeler.py` | 67 | `predict_proba` | IV | — | `Nodo sin etiqueta canónica` |  |
| 70 | `qbe_observatory/src/observatory/legacy_ml/meta_labeler.py` | 77 | `pr_auc` | IV | — | `Nodo sin etiqueta canónica` |  |
| 71 | `qbe_observatory/src/observatory/legacy_ml/meta_labeler.py` | 82 | `umbral_veto_max_precision` | IV | — | `Nodo sin etiqueta canónica` |  |
| 72 | `qbe_observatory/src/observatory/legacy_ml/meta_labeler.py` | 104 | `es_veto` | IV | — | `Nodo sin etiqueta canónica` |  |
| 73 | `qbe_observatory/src/observatory/legacy_ml/meta_labeler.py` | 109 | `integrar_veto_meta` | IV | — | `Nodo sin etiqueta canónica` |  |
| 74 | `qbe_observatory/src/observatory/legacy_ml/modelo_a_bayesiano.py` | 64 | `ModeloAError` | IV | — | `Clase sin etiqueta canónica` |  |
| 75 | `qbe_observatory/src/observatory/legacy_ml/modelo_a_bayesiano.py` | 68 | `_canales` | IV | — | `Nodo sin etiqueta canónica` |  |
| 76 | `qbe_observatory/src/observatory/legacy_ml/modelo_a_bayesiano.py` | 74 | `lambdas` | IV | — | `Nodo sin etiqueta canónica` |  |
| 77 | `qbe_observatory/src/observatory/legacy_ml/modelo_a_bayesiano.py` | 101 | `_rho_continuo` | IV | — | `Nodo sin etiqueta canónica` |  |
| 78 | `qbe_observatory/src/observatory/legacy_ml/modelo_a_bayesiano.py` | 116 | `nll_marcador` | IV | — | `Nodo sin etiqueta canónica` |  |
| 79 | `qbe_observatory/src/observatory/legacy_ml/modelo_a_bayesiano.py` | 149 | `_l1` | IV | — | `Nodo sin etiqueta canónica` |  |
| 80 | `qbe_observatory/src/observatory/legacy_ml/modelo_a_bayesiano.py` | 154 | `objetivo` | IV | — | `Nodo sin etiqueta canónica` |  |
| 81 | `qbe_observatory/src/observatory/legacy_ml/modelo_a_bayesiano.py` | 159 | `_rejilla` | IV | — | `Nodo sin etiqueta canónica` |  |
| 82 | `qbe_observatory/src/observatory/legacy_ml/modelo_a_bayesiano.py` | 175 | `_umbralizar` | IV | — | `Nodo sin etiqueta canónica` |  |
| 83 | `qbe_observatory/src/observatory/legacy_ml/modelo_a_bayesiano.py` | 182 | `entrenar` | IV | — | `Nodo sin etiqueta canónica` |  |
| 84 | `qbe_observatory/src/observatory/legacy_ml/modelo_a_bayesiano.py` | 231 | `_reporte` | IV | — | `Nodo sin etiqueta canónica` |  |
| 85 | `qbe_observatory/src/observatory/legacy_ml/modelo_a_bayesiano.py` | 243 | `main` | IV | — | `return 0.0 sin etiqueta canónica` |  |
| 86 | `qbe_observatory/src/observatory/legacy_ml/modelo_b_regresion.py` | 53 | `ModeloBError` | IV | — | `Clase sin etiqueta canónica` |  |
| 87 | `qbe_observatory/src/observatory/legacy_ml/modelo_b_regresion.py` | 57 | `proyectar` | IV | — | `Nodo sin etiqueta canónica` |  |
| 88 | `qbe_observatory/src/observatory/legacy_ml/modelo_b_regresion.py` | 68 | `entrenar` | IV | — | `Nodo sin etiqueta canónica` |  |
| 89 | `qbe_observatory/src/observatory/legacy_ml/modelo_b_regresion.py` | 114 | `_reporte` | IV | — | `Nodo sin etiqueta canónica` |  |
| 90 | `qbe_observatory/src/observatory/legacy_ml/modelo_b_regresion.py` | 128 | `main` | IV | — | `return 0.0 sin etiqueta canónica` |  |
| 91 | `qbe_observatory/src/observatory/legacy_ml/modelo_c_xgboost.py` | 67 | `ModeloCError` | IV | — | `Clase sin etiqueta canónica` |  |
| 92 | `qbe_observatory/src/observatory/legacy_ml/modelo_c_xgboost.py` | 71 | `proyectar` | IV | — | `Nodo sin etiqueta canónica` |  |
| 93 | `qbe_observatory/src/observatory/legacy_ml/modelo_c_xgboost.py` | 81 | `_particion_cronologica` | IV | — | `Nodo sin etiqueta canónica` |  |
| 94 | `qbe_observatory/src/observatory/legacy_ml/modelo_c_xgboost.py` | 87 | `_importancias` | IV | — | `Nodo sin etiqueta canónica` |  |
| 95 | `qbe_observatory/src/observatory/legacy_ml/modelo_c_xgboost.py` | 146 | `entrenar` | IV | — | `Nodo sin etiqueta canónica` |  |
| 96 | `qbe_observatory/src/observatory/legacy_ml/modelo_c_xgboost.py` | 177 | `_reporte` | IV | — | `Nodo sin etiqueta canónica` |  |
| 97 | `qbe_observatory/src/observatory/legacy_ml/modelo_c_xgboost.py` | 190 | `main` | IV | — | `return 0.0 sin etiqueta canónica` |  |
| 98 | `qbe_observatory/src/observatory/legacy_ml/preparar_meta_dataset.py` | 59 | `_mercado_de_vig` | IV | — | `Nodo sin etiqueta canónica` |  |
| 99 | `qbe_observatory/src/observatory/legacy_ml/preparar_meta_dataset.py` | 70 | `construir` | IV | — | `Nodo sin etiqueta canónica` |  |
| 100 | `qbe_observatory/src/observatory/legacy_ml/preparar_meta_dataset.py` | 148 | `_vector_x` | IV | — | `Nodo sin etiqueta canónica` |  |
| 101 | `qbe_observatory/src/observatory/legacy_ml/preparar_meta_dataset.py` | 158 | `_imputar_mediana` | IV | — | `Nodo sin etiqueta canónica` |  |
| 102 | `qbe_observatory/src/observatory/legacy_ml/preparar_meta_dataset.py` | 174 | `preparar` | IV | — | `Nodo sin etiqueta canónica` |  |
| 103 | `qbe_observatory/src/observatory/sabiduria_masas.py` | 37 | `_numero` | IV | — | `Nodo sin etiqueta canónica` |  |
| 104 | `qbe_observatory/src/observatory/sabiduria_masas.py` | 47 | `brier_promedio_partidos` | IV | — | `Nodo sin etiqueta canónica` |  |
| 105 | `qbe_observatory/src/observatory/sabiduria_masas.py` | 64 | `brier_jornada` | IV | — | `Nodo sin etiqueta canónica` |  |
| 106 | `qbe_observatory/src/observatory/sabiduria_masas.py` | 69 | `pesos_desde_brier` | IV | — | `Nodo sin etiqueta canónica` |  |
| 107 | `qbe_observatory/src/observatory/sabiduria_masas.py` | 101 | `alpha_pct` | IV | — | `Nodo sin etiqueta canónica` |  |
| 108 | `qbe_observatory/src/observatory/sabiduria_masas.py` | 114 | `construir_tabla_sabiduria` | IV | — | `Nodo sin etiqueta canónica` |  |
| 109 | `qbe_observatory/src/observatory/sabiduria_masas.py` | 160 | `construir_tabla_por_jornada` | IV | — | `Nodo sin etiqueta canónica` |  |
| 110 | `qbe_observatory/src/observatory/visor_backtesting.py` | 25 | `FuenteDesconocidaError` | IV | — | `Clase sin etiqueta canónica` |  |
| 111 | `qbe_observatory/src/observatory/visor_backtesting.py` | 29 | `_validar_simplex` | IV | — | `Nodo sin etiqueta canónica` |  |
| 112 | `qbe_observatory/src/observatory/visor_backtesting.py` | 40 | `construir_dto_simulacion` | IV | — | `Nodo sin etiqueta canónica` |  |

---

**VÍA A:** erradicación de la regla huérfana. **VÍA B:** formalización legislativa y etiquetado con Juez.
