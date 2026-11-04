# GL_update — Bandeja de Revisión de Paridad Canónica

- **Nodo auditor:** `[LN-QBE-139]`
- **Juez:** `[LN-QBE-140]`
- **Sprint:** `SPRINT-49`
- **Fuente de vigencia:** `docs/ID_REGISTRY.md` (estado `SELLADO`; regla de sprint 001–138).
- **Estado:** `PENDIENTE DEL DIRECTOR`

> Esta bandeja es una salida determinista del Auditor de Paridad. No corrige, no interpreta y no decide. El Director marca cada fila con **VÍA A (Erradicación)** o **VÍA B (Formalización)**.

## Resumen

| Métrica | Valor |
|---|---:|
| Archivos auditados | 64 |
| Reglas huérfanas | 257 |
| Clase I — Fabricación Sintética | 0 |
| Clase II — Contradicción Numérica | 0 |
| Clase III — Colisión de Literales | 0 |
| Clase IV — Heurísticas Permisivas | 257 |

## Hallazgos

| # | Archivo | Línea | Función / Nodo | Clase | Etiqueta | Evidencia | VEREDICTO DIRECTOR |
|---:|---|---:|---|---|---|---|---|
| 1 | `qbe_observatory/app/adapters/db_readonly.py` | 24 | `conexion_solo_lectura` | IV | — | `Nodo sin etiqueta canónica` |  |
| 2 | `qbe_observatory/app/adapters/db_readonly.py` | 40 | `ejecutar_select` | IV | — | `Nodo sin etiqueta canónica` |  |
| 3 | `qbe_observatory/app/adapters/db_readonly.py` | 53 | `BaseDatosSoloLectura` | IV | — | `Clase sin etiqueta canónica` |  |
| 4 | `qbe_observatory/app/adapters/db_readonly.py` | 56 | `__init__` | IV | — | `Nodo sin etiqueta canónica` |  |
| 5 | `qbe_observatory/app/adapters/db_readonly.py` | 60 | `conexion` | IV | — | `Nodo sin etiqueta canónica` |  |
| 6 | `qbe_observatory/app/adapters/db_readonly.py` | 64 | `ejecutar_select` | IV | — | `Nodo sin etiqueta canónica` |  |
| 7 | `qbe_observatory/app/main.py` | 37 | `index` | IV | — | `Nodo sin etiqueta canónica` |  |
| 8 | `qbe_observatory/app/main.py` | 46 | `visor` | IV | — | `Nodo sin etiqueta canónica` |  |
| 9 | `qbe_observatory/app/main.py` | 68 | `visor_panel_vars44` | IV | — | `Nodo sin etiqueta canónica` |  |
| 10 | `qbe_observatory/app/main.py` | 82 | `health` | IV | — | `Nodo sin etiqueta canónica` |  |
| 11 | `qbe_observatory/app/routes/backtesting.py` | 26 | `_motor_solo_lectura` | IV | — | `Nodo sin etiqueta canónica` |  |
| 12 | `qbe_observatory/app/routes/backtesting.py` | 39 | `_detalle_snapshot_ausente` | IV | — | `Nodo sin etiqueta canónica` |  |
| 13 | `qbe_observatory/app/routes/backtesting.py` | 48 | `get_db_ro` | IV | — | `Nodo sin etiqueta canónica` |  |
| 14 | `qbe_observatory/app/routes/backtesting.py` | 63 | `_ReadOnlyGateway` | IV | — | `Clase sin etiqueta canónica` |  |
| 15 | `qbe_observatory/app/routes/backtesting.py` | 66 | `__init__` | IV | — | `Nodo sin etiqueta canónica` |  |
| 16 | `qbe_observatory/app/routes/backtesting.py` | 79 | `read_session` | IV | — | `Nodo sin etiqueta canónica` |  |
| 17 | `qbe_observatory/app/routes/backtesting.py` | 98 | `_estado_concluido` | IV | — | `Nodo sin etiqueta canónica` |  |
| 18 | `qbe_observatory/app/routes/backtesting.py` | 107 | `_captura_declara_resultado` | IV | — | `Nodo sin etiqueta canónica` |  |
| 19 | `qbe_observatory/app/routes/backtesting.py` | 114 | `_marcador_de_captura` | IV | — | `Nodo sin etiqueta canónica` |  |
| 20 | `qbe_observatory/app/routes/backtesting.py` | 132 | `_resultado_consumado` | IV | — | `Nodo sin etiqueta canónica` |  |
| 21 | `qbe_observatory/app/routes/backtesting.py` | 154 | `_fixtures_snapshot_indexados` | IV | — | `Nodo sin etiqueta canónica` |  |
| 22 | `qbe_observatory/app/routes/backtesting.py` | 177 | `_soberanas_por_id` | IV | — | `Nodo sin etiqueta canónica` |  |
| 23 | `qbe_observatory/app/routes/backtesting.py` | 190 | `_trazas_soberanas_por_id` | IV | — | `Nodo sin etiqueta canónica` |  |
| 24 | `qbe_observatory/app/routes/backtesting.py` | 226 | `_datos_partido_para_atribucion` | IV | — | `Nodo sin etiqueta canónica` |  |
| 25 | `qbe_observatory/app/routes/backtesting.py` | 264 | `_atribucion_factorial_del_partido` | IV | — | `Nodo sin etiqueta canónica` |  |
| 26 | `qbe_observatory/app/routes/backtesting.py` | 277 | `_p_prima_del_fixture` | IV | — | `Nodo sin etiqueta canónica` |  |
| 27 | `qbe_observatory/app/routes/backtesting.py` | 378 | `_trio_cuotas_valido` | IV | — | `Nodo sin etiqueta canónica` |  |
| 28 | `qbe_observatory/app/routes/backtesting.py` | 398 | `_cuotas_1x2_factuales` | IV | — | `Nodo sin etiqueta canónica` |  |
| 29 | `qbe_observatory/app/routes/backtesting.py` | 432 | `_cuotas_1x2_con_fuente` | IV | — | `Nodo sin etiqueta canónica` |  |
| 30 | `qbe_observatory/app/routes/backtesting.py` | 440 | `_fecha_dia` | IV | — | `Nodo sin etiqueta canónica` |  |
| 31 | `qbe_observatory/app/routes/backtesting.py` | 479 | `_construir_indice_cuotas_historicas` | IV | — | `Nodo sin etiqueta canónica` |  |
| 32 | `qbe_observatory/app/routes/backtesting.py` | 543 | `_resolver_cuota_historica` | IV | — | `Nodo sin etiqueta canónica` |  |
| 33 | `qbe_observatory/app/routes/backtesting.py` | 621 | `cuotas_desde_historico` | IV | — | `Nodo sin etiqueta canónica` |  |
| 34 | `qbe_observatory/app/routes/backtesting.py` | 666 | `_delta_altitud_del_partido` | IV | — | `return 0.0 sin etiqueta canónica` |  |
| 35 | `qbe_observatory/app/routes/backtesting.py` | 740 | `_pct` | IV | — | `Nodo sin etiqueta canónica` |  |
| 36 | `qbe_observatory/app/routes/backtesting.py` | 1188 | `reporte_calibracion_canonico` | IV | — | `Nodo sin etiqueta canónica` |  |
| 37 | `qbe_observatory/app/routes/backtesting.py` | 1201 | `get_backtesting_calibration_report` | IV | — | `Nodo sin etiqueta canónica` |  |
| 38 | `qbe_observatory/app/routes/backtesting_ui.py` | 23 | `_reporte` | IV | — | `Nodo sin etiqueta canónica` |  |
| 39 | `qbe_observatory/app/routes/backtesting_ui.py` | 35 | `_contexto` | IV | — | `Nodo sin etiqueta canónica` |  |
| 40 | `qbe_observatory/app/routes/backtesting_ui.py` | 47 | `backtesting_ui` | IV | — | `Nodo sin etiqueta canónica` |  |
| 41 | `qbe_observatory/app/routes/backtesting_ui.py` | 59 | `backtesting_simular` | IV | — | `Nodo sin etiqueta canónica` |  |
| 42 | `qbe_observatory/app/routes/calibration.py` | 23 | `ResumenTemporada` | IV | — | `Clase sin etiqueta canónica` |  |
| 43 | `qbe_observatory/app/routes/calibration.py` | 36 | `JornadaResumen` | IV | — | `Clase sin etiqueta canónica` |  |
| 44 | `qbe_observatory/app/routes/calibration.py` | 44 | `CalibrationReportResponse` | IV | — | `Clase sin etiqueta canónica` |  |
| 45 | `qbe_observatory/app/routes/calibration.py` | 52 | `_temporada_mas_reciente` | IV | — | `Nodo sin etiqueta canónica` |  |
| 46 | `qbe_observatory/app/routes/calibration.py` | 60 | `_desenlace` | IV | — | `Nodo sin etiqueta canónica` |  |
| 47 | `qbe_observatory/app/routes/calibration.py` | 69 | `_reporte_sin_historico` | IV | — | `Nodo sin etiqueta canónica` |  |
| 48 | `qbe_observatory/app/routes/calibration.py` | 103 | `construir_reporte` | IV | — | `Nodo sin etiqueta canónica` |  |
| 49 | `qbe_observatory/app/routes/calibration.py` | 242 | `reporte_calibracion` | IV | — | `Nodo sin etiqueta canónica` |  |
| 50 | `qbe_observatory/app/routes/consenso_ui.py` | 22 | `consenso_ui` | IV | — | `Nodo sin etiqueta canónica` |  |
| 51 | `qbe_observatory/app/routes/manus.py` | 20 | `PredictionRequest` | IV | — | `Clase sin etiqueta canónica` |  |
| 52 | `qbe_observatory/app/routes/manus.py` | 25 | `listar_modelos` | IV | — | `Nodo sin etiqueta canónica` |  |
| 53 | `qbe_observatory/app/routes/manus.py` | 30 | `predecir_modelo` | IV | — | `Nodo sin etiqueta canónica` |  |
| 54 | `qbe_observatory/app/routes/snapshot.py` | 14 | `estado_snapshot` | IV | — | `Nodo sin etiqueta canónica` |  |
| 55 | `qbe_observatory/app/services/calibration_view.py` | 31 | `HistoricoDBError` | IV | — | `Clase sin etiqueta canónica` |  |
| 56 | `qbe_observatory/app/services/calibration_view.py` | 40 | `temporadas_historicas` | IV | — | `Nodo sin etiqueta canónica` |  |
| 57 | `qbe_observatory/app/services/calibration_view.py` | 60 | `total_partidos_historicos` | IV | — | `Nodo sin etiqueta canónica` |  |
| 58 | `qbe_observatory/app/services/calibration_view.py` | 76 | `_signo_alpha` | IV | — | `Nodo sin etiqueta canónica` |  |
| 59 | `qbe_observatory/app/services/calibration_view.py` | 87 | `_brier_vars` | IV | — | `Nodo sin etiqueta canónica` |  |
| 60 | `qbe_observatory/app/services/calibration_view.py` | 97 | `_componentes_futuros` | IV | — | `Nodo sin etiqueta canónica` |  |
| 61 | `qbe_observatory/app/services/calibration_view.py` | 115 | `_fuente_base` | IV | — | `Nodo sin etiqueta canónica` |  |
| 62 | `qbe_observatory/app/services/calibration_view.py` | 129 | `_metadatos_boveda` | IV | — | `Nodo sin etiqueta canónica` |  |
| 63 | `qbe_observatory/app/services/calibration_view.py` | 156 | `_tiene_cuotas` | IV | — | `Nodo sin etiqueta canónica` |  |
| 64 | `qbe_observatory/app/services/calibration_view.py` | 167 | `_texto_probabilidades` | IV | — | `Nodo sin etiqueta canónica` |  |
| 65 | `qbe_observatory/app/services/calibration_view.py` | 177 | `_diccionario` | IV | — | `Nodo sin etiqueta canónica` |  |
| 66 | `qbe_observatory/app/services/calibration_view.py` | 182 | `_partido_vista` | IV | — | `Nodo sin etiqueta canónica` |  |
| 67 | `qbe_observatory/app/services/calibration_view.py` | 233 | `_jornada_vista` | IV | — | `Nodo sin etiqueta canónica` |  |
| 68 | `qbe_observatory/app/services/calibration_view.py` | 265 | `_resumen_vacio` | IV | — | `Nodo sin etiqueta canónica` |  |
| 69 | `qbe_observatory/app/services/calibration_view.py` | 286 | `_resumen_vista` | IV | — | `Nodo sin etiqueta canónica` |  |
| 70 | `qbe_observatory/app/services/calibration_view.py` | 329 | `construir_vista_desde_reporte` | IV | — | `Nodo sin etiqueta canónica` |  |
| 71 | `qbe_observatory/app/services/calibration_view.py` | 356 | `_vista_error` | IV | — | `Nodo sin etiqueta canónica` |  |
| 72 | `qbe_observatory/app/services/calibration_view.py` | 368 | `cargar_panel_vars44` | IV | — | `Nodo sin etiqueta canónica` |  |
| 73 | `qbe_observatory/app/services/calibration_view.py` | 385 | `cargar_vista_calibracion` | IV | — | `Nodo sin etiqueta canónica` |  |
| 74 | `qbe_observatory/app/services/consenso_view.py` | 37 | `_normalizar_seleccion` | IV | — | `Nodo sin etiqueta canónica` |  |
| 75 | `qbe_observatory/app/services/consenso_view.py` | 50 | `_sabiduria_vacia` | IV | — | `Nodo sin etiqueta canónica` |  |
| 76 | `qbe_observatory/app/services/consenso_view.py` | 84 | `_mercado_vacio` | IV | — | `Nodo sin etiqueta canónica` |  |
| 77 | `qbe_observatory/app/services/consenso_view.py` | 97 | `_procedencia` | IV | — | `Nodo sin etiqueta canónica` |  |
| 78 | `qbe_observatory/app/services/consenso_view.py` | 107 | `_contexto` | IV | — | `Nodo sin etiqueta canónica` |  |
| 79 | `qbe_observatory/app/services/consenso_view.py` | 132 | `cargar_vista_consenso` | IV | — | `Nodo sin etiqueta canónica` |  |
| 80 | `qbe_observatory/app/services/manus.py` | 19 | `ModeloNoDisponible` | IV | — | `Clase sin etiqueta canónica` |  |
| 81 | `qbe_observatory/app/services/manus.py` | 23 | `_ruta_modelo` | IV | — | `Nodo sin etiqueta canónica` |  |
| 82 | `qbe_observatory/app/services/manus.py` | 27 | `modelos_disponibles` | IV | — | `Nodo sin etiqueta canónica` |  |
| 83 | `qbe_observatory/app/services/manus.py` | 39 | `predecir` | IV | — | `Nodo sin etiqueta canónica` |  |
| 84 | `qbe_observatory/app/services/sabiduria_view.py` | 98 | `_simplex` | IV | — | `Nodo sin etiqueta canónica` |  |
| 85 | `qbe_observatory/app/services/sabiduria_view.py` | 110 | `_one_hot` | IV | — | `Nodo sin etiqueta canónica` |  |
| 86 | `qbe_observatory/app/services/sabiduria_view.py` | 118 | `_brier` | IV | — | `Nodo sin etiqueta canónica` |  |
| 87 | `qbe_observatory/app/services/sabiduria_view.py` | 122 | `_positivo` | IV | — | `Nodo sin etiqueta canónica` |  |
| 88 | `qbe_observatory/app/services/sabiduria_view.py` | 136 | `_entero_jornada` | IV | — | `Nodo sin etiqueta canónica` |  |
| 89 | `qbe_observatory/app/services/sabiduria_view.py` | 150 | `_normalizar_seleccion` | IV | — | `Nodo sin etiqueta canónica` |  |
| 90 | `qbe_observatory/app/services/sabiduria_view.py` | 163 | `_nombre_fuente` | IV | — | `Nodo sin etiqueta canónica` |  |
| 91 | `qbe_observatory/app/services/sabiduria_view.py` | 167 | `_normalizar_pesos` | IV | — | `Nodo sin etiqueta canónica` |  |
| 92 | `qbe_observatory/app/services/sabiduria_view.py` | 201 | `_promedio_ponderado` | IV | — | `Nodo sin etiqueta canónica` |  |
| 93 | `qbe_observatory/app/services/sabiduria_view.py` | 220 | `_media_brier` | IV | — | `Nodo sin etiqueta canónica` |  |
| 94 | `qbe_observatory/app/services/sabiduria_view.py` | 272 | `_etiqueta_bloque` | IV | — | `Nodo sin etiqueta canónica` |  |
| 95 | `qbe_observatory/app/services/sabiduria_view.py` | 279 | `_filas_bloque` | IV | — | `Nodo sin etiqueta canónica` |  |
| 96 | `qbe_observatory/app/services/sabiduria_view.py` | 335 | `_bloque` | IV | — | `Nodo sin etiqueta canónica` |  |
| 97 | `qbe_observatory/app/services/sabiduria_view.py` | 360 | `_kpis` | IV | — | `Nodo sin etiqueta canónica` |  |
| 98 | `qbe_observatory/app/services/sabiduria_view.py` | 371 | `_fuentes_de` | IV | — | `Nodo sin etiqueta canónica` |  |
| 99 | `qbe_observatory/app/services/sabiduria_view.py` | 383 | `_resumen` | IV | — | `Nodo sin etiqueta canónica` |  |
| 100 | `qbe_observatory/app/services/sabiduria_view.py` | 415 | `_composicion` | IV | — | `Nodo sin etiqueta canónica` |  |
| 101 | `qbe_observatory/app/services/sabiduria_view.py` | 425 | `_etiqueta_kpi` | IV | — | `Nodo sin etiqueta canónica` |  |
| 102 | `qbe_observatory/app/services/sabiduria_view.py` | 431 | `_tabla_vacia` | IV | — | `Nodo sin etiqueta canónica` |  |
| 103 | `qbe_observatory/app/services/sabiduria_view.py` | 529 | `_es_temporada_archivada` | IV | — | `Nodo sin etiqueta canónica` |  |
| 104 | `qbe_observatory/app/services/sabiduria_view.py` | 543 | `_cierres_propios` | IV | — | `Nodo sin etiqueta canónica` |  |
| 105 | `qbe_observatory/app/services/sabiduria_view.py` | 589 | `construir_sabiduria_masas` | IV | — | `Nodo sin etiqueta canónica` |  |
| 106 | `qbe_observatory/app/services/sabiduria_view.py` | 839 | `_mercado_vacio` | IV | — | `Nodo sin etiqueta canónica` |  |
| 107 | `qbe_observatory/app/services/sabiduria_view.py` | 852 | `_ultima_jornada_programada` | IV | — | `Nodo sin etiqueta canónica` |  |
| 108 | `qbe_observatory/app/services/sabiduria_view.py` | 876 | `_probabilidades_qbe` | IV | — | `Nodo sin etiqueta canónica` |  |
| 109 | `qbe_observatory/app/services/sabiduria_view.py` | 900 | `_soberanas` | IV | — | `Nodo sin etiqueta canónica` |  |
| 110 | `qbe_observatory/app/services/sabiduria_view.py` | 927 | `_momio_justo` | IV | — | `Nodo sin etiqueta canónica` |  |
| 111 | `qbe_observatory/app/services/sabiduria_view.py` | 941 | `_cuotas_justas` | IV | — | `Nodo sin etiqueta canónica` |  |
| 112 | `qbe_observatory/app/services/snapshot_refresh.py` | 28 | `edad_snapshot` | IV | — | `Nodo sin etiqueta canónica` |  |
| 113 | `qbe_observatory/app/services/snapshot_refresh.py` | 35 | `snapshot_fresco` | IV | — | `Nodo sin etiqueta canónica` |  |
| 114 | `qbe_observatory/app/services/snapshot_refresh.py` | 41 | `huella_sha256` | IV | — | `Nodo sin etiqueta canónica` |  |
| 115 | `qbe_observatory/app/services/snapshot_refresh.py` | 50 | `_uri_solo_lectura` | IV | — | `Nodo sin etiqueta canónica` |  |
| 116 | `qbe_observatory/app/services/snapshot_refresh.py` | 54 | `_limpiar_sidecars` | IV | — | `Nodo sin etiqueta canónica` |  |
| 117 | `qbe_observatory/app/services/snapshot_refresh.py` | 65 | `_verificar_copia` | IV | — | `return 0.0 sin etiqueta canónica` |  |
| 118 | `qbe_observatory/app/services/snapshot_refresh.py` | 108 | `refrescar_snapshot` | IV | — | `Nodo sin etiqueta canónica` |  |
| 119 | `qbe_observatory/scripts/refresh_snapshot.py` | 27 | `_parser` | IV | — | `Nodo sin etiqueta canónica` |  |
| 120 | `qbe_observatory/scripts/refresh_snapshot.py` | 61 | `main` | IV | — | `return 0.0 sin etiqueta canónica` |  |
| 121 | `qbe_observatory/src/observatory/core/context_provider.py` | 84 | `_r` | IV | — | `Nodo sin etiqueta canónica` |  |
| 122 | `qbe_observatory/src/observatory/core/context_provider.py` | 89 | `_clamp` | IV | — | `Nodo sin etiqueta canónica` |  |
| 123 | `qbe_observatory/src/observatory/core/context_provider.py` | 94 | `_num` | IV | — | `Nodo sin etiqueta canónica` |  |
| 124 | `qbe_observatory/src/observatory/core/context_provider.py` | 215 | `parse_fecha` | IV | — | `Nodo sin etiqueta canónica` |  |
| 125 | `qbe_observatory/src/observatory/core/context_provider.py` | 241 | `normalizar_identidad` | IV | — | `Nodo sin etiqueta canónica` |  |
| 126 | `qbe_observatory/src/observatory/core/context_provider.py` | 275 | `identidad_coincide` | IV | — | `Nodo sin etiqueta canónica` |  |
| 127 | `qbe_observatory/src/observatory/core/context_provider.py` | 304 | `leer_fixture_cartelera` | IV | — | `Nodo sin etiqueta canónica` |  |
| 128 | `qbe_observatory/src/observatory/core/context_provider.py` | 334 | `partidos_terminales_de_club` | IV | — | `Nodo sin etiqueta canónica` |  |
| 129 | `qbe_observatory/src/observatory/core/context_provider.py` | 385 | `_catalogo_calendario` | IV | — | `Nodo sin etiqueta canónica` |  |
| 130 | `qbe_observatory/src/observatory/core/context_provider.py` | 410 | `_partido_previo` | IV | — | `Nodo sin etiqueta canónica` |  |
| 131 | `qbe_observatory/src/observatory/core/context_provider.py` | 496 | `_texto_dias` | IV | — | `Nodo sin etiqueta canónica` |  |
| 132 | `qbe_observatory/src/observatory/core/context_provider.py` | 500 | `_texto_metros` | IV | — | `Nodo sin etiqueta canónica` |  |
| 133 | `qbe_observatory/src/observatory/core/context_provider.py` | 504 | `_bloque_vacio_contexto` | IV | — | `Nodo sin etiqueta canónica` |  |
| 134 | `qbe_observatory/src/observatory/core/factor_attribution.py` | 44 | `_num` | IV | — | `Nodo sin etiqueta canónica` |  |
| 135 | `qbe_observatory/src/observatory/core/factor_attribution.py` | 57 | `_es_certificado` | IV | — | `Nodo sin etiqueta canónica` |  |
| 136 | `qbe_observatory/src/observatory/core/factor_attribution.py` | 72 | `_amortiguar` | IV | — | `Nodo sin etiqueta canónica` |  |
| 137 | `qbe_observatory/src/observatory/core/factor_attribution.py` | 455 | `_celda_h2h_stats` | IV | — | `Nodo sin etiqueta canónica` |  |
| 138 | `qbe_observatory/src/observatory/core/factor_attribution.py` | 501 | `_celda_trayectoria` | IV | — | `Nodo sin etiqueta canónica` |  |
| 139 | `qbe_observatory/src/observatory/core/factor_attribution.py` | 597 | `_formatear_macro` | IV | — | `Nodo sin etiqueta canónica` |  |
| 140 | `qbe_observatory/src/observatory/core/factor_attribution.py` | 616 | `_celda_macro_stats` | IV | — | `Nodo sin etiqueta canónica` |  |
| 141 | `qbe_observatory/src/observatory/core/factor_attribution.py` | 813 | `_insumos_del_bloque` | IV | — | `Nodo sin etiqueta canónica` |  |
| 142 | `qbe_observatory/src/observatory/core/factor_attribution.py` | 821 | `_aplanar_insumos` | IV | — | `Nodo sin etiqueta canónica` |  |
| 143 | `qbe_observatory/src/observatory/core/factor_attribution.py` | 840 | `_fusionar_planas` | IV | — | `Nodo sin etiqueta canónica` |  |
| 144 | `qbe_observatory/src/observatory/core/factor_attribution.py` | 917 | `_formatear_insumo` | IV | — | `Nodo sin etiqueta canónica` |  |
| 145 | `qbe_observatory/src/observatory/core/factor_attribution.py` | 941 | `_bloque_equipo` | IV | — | `Nodo sin etiqueta canónica` |  |
| 146 | `qbe_observatory/src/observatory/core/factor_attribution.py` | 950 | `_leer_clave` | IV | — | `Nodo sin etiqueta canónica` |  |
| 147 | `qbe_observatory/src/observatory/core/factor_attribution.py` | 962 | `_valor_tasa` | IV | — | `Nodo sin etiqueta canónica` |  |
| 148 | `qbe_observatory/src/observatory/core/factor_attribution.py` | 977 | `_h2h_secuencia` | IV | — | `Nodo sin etiqueta canónica` |  |
| 149 | `qbe_observatory/src/observatory/core/factor_attribution.py` | 984 | `_campo_partido` | IV | — | `Nodo sin etiqueta canónica` |  |
| 150 | `qbe_observatory/src/observatory/core/factor_attribution.py` | 990 | `_resumen_h2h` | IV | — | `Nodo sin etiqueta canónica` |  |
| 151 | `qbe_observatory/src/observatory/core/factor_attribution.py` | 1032 | `_valor_variable` | IV | — | `Nodo sin etiqueta canónica` |  |
| 152 | `qbe_observatory/src/observatory/core/factor_attribution.py` | 1186 | `_gamma_efectivo` | IV | — | `return 0.0 sin etiqueta canónica` |  |
| 153 | `qbe_observatory/src/observatory/core/simulation_engine.py` | 142 | `_a_float` | IV | — | `Nodo sin etiqueta canónica` |  |
| 154 | `qbe_observatory/src/observatory/core/simulation_engine.py` | 152 | `_marcador_valido` | IV | — | `Nodo sin etiqueta canónica` |  |
| 155 | `qbe_observatory/src/observatory/core/simulation_engine.py` | 213 | `_familias_con_cobertura` | IV | — | `Nodo sin etiqueta canónica` |  |
| 156 | `qbe_observatory/src/observatory/core/simulation_engine.py` | 218 | `_cubre_empate` | IV | — | `Nodo sin etiqueta canónica` |  |
| 157 | `qbe_observatory/src/observatory/core/simulation_engine.py` | 388 | `_cargar_jornada` | IV | — | `Nodo sin etiqueta canónica` |  |
| 158 | `qbe_observatory/src/observatory/core/simulation_engine.py` | 613 | `_dimensionar_y_liquidar` | IV | — | `Nodo sin etiqueta canónica` |  |
| 159 | `qbe_observatory/src/observatory/core/simulation_engine.py` | 908 | `_consolidar_reporte` | IV | — | `Nodo sin etiqueta canónica` |  |
| 160 | `qbe_observatory/src/observatory/core/simulation_engine.py` | 1132 | `_dibujar_curva_bankroll` | IV | — | `Nodo sin etiqueta canónica` |  |
| 161 | `qbe_observatory/src/observatory/core/simulation_engine.py` | 1153 | `_formatear_pesos` | IV | — | `Nodo sin etiqueta canónica` |  |
| 162 | `qbe_observatory/src/observatory/core/simulation_engine.py` | 1170 | `imprimir_tablero_rentabilidad_consola` | IV | — | `Nodo sin etiqueta canónica` |  |
| 163 | `qbe_observatory/src/observatory/core/simulation_engine.py` | 1282 | `parsear_rango_jornadas` | IV | — | `Nodo sin etiqueta canónica` |  |
| 164 | `qbe_observatory/src/observatory/core/simulation_engine.py` | 1313 | `construir_parser` | IV | — | `Nodo sin etiqueta canónica` |  |
| 165 | `qbe_observatory/src/observatory/core/simulation_engine.py` | 1349 | `main` | IV | — | `return 0.0 sin etiqueta canónica` |  |
| 166 | `qbe_observatory/src/observatory/core/sovereign_reads.py` | 42 | `_fila_partido` | IV | — | `Nodo sin etiqueta canónica` |  |
| 167 | `qbe_observatory/src/observatory/core/sovereign_reads.py` | 58 | `leer_fixture` | IV | — | `Nodo sin etiqueta canónica` |  |
| 168 | `qbe_observatory/src/observatory/core/sovereign_reads.py` | 64 | `leer_partidos_corte` | IV | — | `Nodo sin etiqueta canónica` |  |
| 169 | `qbe_observatory/src/observatory/core/sovereign_reads.py` | 76 | `leer_calendario` | IV | — | `Nodo sin etiqueta canónica` |  |
| 170 | `qbe_observatory/src/observatory/core/sovereign_reads.py` | 81 | `leer_telemetria` | IV | — | `Nodo sin etiqueta canónica` |  |
| 171 | `qbe_observatory/src/observatory/core/sovereign_reads.py` | 108 | `leer_snapshots_posiciones` | IV | — | `Nodo sin etiqueta canónica` |  |
| 172 | `qbe_observatory/src/observatory/sabiduria_masas.py` | 37 | `_numero` | IV | — | `Nodo sin etiqueta canónica` |  |
| 173 | `qbe_observatory/src/observatory/sabiduria_masas.py` | 47 | `brier_promedio_partidos` | IV | — | `Nodo sin etiqueta canónica` |  |
| 174 | `qbe_observatory/src/observatory/sabiduria_masas.py` | 64 | `brier_jornada` | IV | — | `Nodo sin etiqueta canónica` |  |
| 175 | `qbe_observatory/src/observatory/sabiduria_masas.py` | 69 | `pesos_desde_brier` | IV | — | `Nodo sin etiqueta canónica` |  |
| 176 | `qbe_observatory/src/observatory/sabiduria_masas.py` | 101 | `alpha_pct` | IV | — | `Nodo sin etiqueta canónica` |  |
| 177 | `qbe_observatory/src/observatory/sabiduria_masas.py` | 114 | `construir_tabla_sabiduria` | IV | — | `Nodo sin etiqueta canónica` |  |
| 178 | `qbe_observatory/src/observatory/sabiduria_masas.py` | 160 | `construir_tabla_por_jornada` | IV | — | `Nodo sin etiqueta canónica` |  |
| 179 | `qbe_observatory/src/observatory/visor_backtesting.py` | 25 | `FuenteDesconocidaError` | IV | — | `Clase sin etiqueta canónica` |  |
| 180 | `qbe_observatory/src/observatory/visor_backtesting.py` | 29 | `_validar_simplex` | IV | — | `Nodo sin etiqueta canónica` |  |
| 181 | `qbe_observatory/src/observatory/visor_backtesting.py` | 40 | `construir_dto_simulacion` | IV | — | `Nodo sin etiqueta canónica` |  |
| 182 | `qbe_observatory/tests/test_parity_observatory_backtesting.py` | 22 | `_preparar` | IV | — | `Nodo sin etiqueta canónica` |  |
| 183 | `qbe_observatory/tests/test_parity_observatory_backtesting.py` | 57 | `test_paridad_calibracion_backtesting` | IV | — | `Nodo sin etiqueta canónica` |  |
| 184 | `qbe_observatory/tests/test_parity_observatory_backtesting.py` | 74 | `test_simulacion_backtesting_responde` | IV | — | `Nodo sin etiqueta canónica` |  |
| 185 | `qbe_observatory/tests/test_parity_observatory_backtesting.py` | 95 | `test_dependencias_analiticas_son_solo_del_observatorio` | IV | — | `Nodo sin etiqueta canónica` |  |
| 186 | `qbe_observatory/tests/test_parity_observatory_backtesting.py` | 99 | `deps` | IV | — | `Nodo sin etiqueta canónica` |  |
| 187 | `qbe_observatory/tests/test_refresh_snapshot_cli.py` | 20 | `test_parser_construye_sin_baseline_root` | IV | — | `Nodo sin etiqueta canónica` |  |
| 188 | `qbe_observatory/tests/test_refresh_snapshot_cli.py` | 37 | `test_live_db_por_omision_vive_dentro_del_monorepo` | IV | — | `Nodo sin etiqueta canónica` |  |
| 189 | `qbe_observatory/tests/test_shield_obs.py` | 36 | `_sha256` | IV | — | `Nodo sin etiqueta canónica` |  |
| 190 | `qbe_observatory/tests/test_shield_obs.py` | 45 | `test_a_aislamiento_de_escritura` | IV | — | `Nodo sin etiqueta canónica` |  |
| 191 | `qbe_observatory/tests/test_shield_obs.py` | 54 | `test_b_inmutabilidad_de_la_bd` | IV | — | `Nodo sin etiqueta canónica` |  |
| 192 | `qbe_observatory/tests/test_shield_obs.py` | 69 | `test_c_consumo_de_qbe_core` | IV | — | `Nodo sin etiqueta canónica` |  |
| 193 | `qbe_observatory/tests/test_shield_obs.py` | 99 | `test_d_contrato_del_endpoint` | IV | — | `Nodo sin etiqueta canónica` |  |
| 194 | `qbe_observatory/tests/test_shield_observatory_autonomy.py` | 43 | `test_invarianza_historico_db_apunta_dentro_del_ecosistema` | IV | — | `Nodo sin etiqueta canónica` |  |
| 195 | `qbe_observatory/tests/test_shield_observatory_autonomy.py` | 63 | `test_invarianza_cero_referencias_a_monolito_en_codigo_observatorio` | IV | — | `Nodo sin etiqueta canónica` |  |
| 196 | `qbe_observatory/tests/test_shield_observatory_autonomy.py` | 88 | `test_invarianza_archivo_historico_existe_en_data_observatorio` | IV | — | `Nodo sin etiqueta canónica` |  |
| 197 | `qbe_observatory/tests/test_shield_observatory_lifecycle.py` | 41 | `_aislar_configuracion_del_snapshot` | IV | — | `Nodo sin etiqueta canónica` |  |
| 198 | `qbe_observatory/tests/test_shield_observatory_lifecycle.py` | 64 | `_sha256` | IV | — | `Nodo sin etiqueta canónica` |  |
| 199 | `qbe_observatory/tests/test_shield_observatory_lifecycle.py` | 72 | `_conexion_ro` | IV | — | `Nodo sin etiqueta canónica` |  |
| 200 | `qbe_observatory/tests/test_shield_observatory_lifecycle.py` | 77 | `test_i1_snapshot_presente_verificado_e_inmutable` | IV | — | `Nodo sin etiqueta canónica` |  |
| 201 | `qbe_observatory/tests/test_shield_observatory_lifecycle.py` | 109 | `test_i2_arranque_asgi_salud_y_portada` | IV | — | `Nodo sin etiqueta canónica` |  |
| 202 | `qbe_observatory/tests/test_shield_observatory_lifecycle.py` | 128 | `test_i3_calibracion_resuelve_y_el_alias_converge` | IV | — | `Nodo sin etiqueta canónica` |  |
| 203 | `qbe_observatory/tests/test_shield_working_tree_clean.py` | 13 | `test_invarianza_cero_logs_temporales_en_observatorio` | IV | — | `Nodo sin etiqueta canónica` |  |
| 204 | `qbe_observatory/tests/test_shield_working_tree_clean.py` | 20 | `test_invarianza_parche_inerte_eliminado_en_lifecycle` | IV | — | `Nodo sin etiqueta canónica` |  |
| 205 | `qbe_observatory/tests/test_shield_working_tree_clean.py` | 36 | `test_invarianza_factor_attribution_reside_en_observatorio` | IV | — | `Nodo sin etiqueta canónica` |  |
| 206 | `qbe_observatory/tests/test_slice2b.py` | 19 | `_hash` | IV | — | `Nodo sin etiqueta canónica` |  |
| 207 | `qbe_observatory/tests/test_slice2b.py` | 23 | `_preparar_snapshot` | IV | — | `Nodo sin etiqueta canónica` |  |
| 208 | `qbe_observatory/tests/test_slice2b.py` | 39 | `test_ui_backtesting_200_sin_assets_de_la_mesa` | IV | — | `Nodo sin etiqueta canónica` |  |
| 209 | `qbe_observatory/tests/test_slice2b.py` | 53 | `test_ui_simulacion_renderiza_curva` | IV | — | `Nodo sin etiqueta canónica` |  |
| 210 | `qbe_observatory/tests/test_slice2b.py` | 76 | `test_snapshot_status_y_frescura` | IV | — | `Nodo sin etiqueta canónica` |  |
| 211 | `qbe_observatory/tests/test_slice2b.py` | 92 | `test_refresco_atomico_no_muta_origen` | IV | — | `Nodo sin etiqueta canónica` |  |
| 212 | `qbe_observatory/tests/test_slice2b.py` | 120 | `test_manus_lista_y_503_sin_artefacto` | IV | — | `Nodo sin etiqueta canónica` |  |
| 213 | `qbe_observatory/tests/test_slice2b.py` | 147 | `test_manus_predice_con_sklearn` | IV | — | `Nodo sin etiqueta canónica` |  |
| 214 | `qbe_observatory/tests/test_slice2b.py` | 173 | `test_puerto_propio_8001` | IV | — | `Nodo sin etiqueta canónica` |  |
| 215 | `qbe_observatory/tests/test_visor_auditoria_calibracion.py` | 29 | `cliente` | IV | — | `Nodo sin etiqueta canónica` |  |
| 216 | `qbe_observatory/tests/test_visor_auditoria_calibracion.py` | 37 | `_canonico` | IV | — | `Nodo sin etiqueta canónica` |  |
| 217 | `qbe_observatory/tests/test_visor_auditoria_calibracion.py` | 43 | `test_visor_200_y_titulo_auditoria` | IV | — | `Nodo sin etiqueta canónica` |  |
| 218 | `qbe_observatory/tests/test_visor_auditoria_calibracion.py` | 53 | `test_visor_paridad_con_endpoint_canonico` | IV | — | `Nodo sin etiqueta canónica` |  |
| 219 | `qbe_observatory/tests/test_visor_auditoria_calibracion.py` | 67 | `test_visor_no_fabrica_brier_cuando_la_muestra_esta_vacia` | IV | — | `Nodo sin etiqueta canónica` |  |
| 220 | `qbe_observatory/tests/test_visor_auditoria_calibracion.py` | 91 | `test_visor_alpha_semantico_por_signo` | IV | — | `Nodo sin etiqueta canónica` |  |
| 221 | `qbe_observatory/tests/test_visor_auditoria_calibracion.py` | 100 | `test_visor_estructura_drilldown_y_columnas` | IV | — | `Nodo sin etiqueta canónica` |  |
| 222 | `qbe_observatory/tests/test_visor_auditoria_calibracion.py` | 113 | `test_visor_slots_futuros_pendiente_motor` | IV | — | `Nodo sin etiqueta canónica` |  |
| 223 | `qbe_observatory/tests/test_visor_auditoria_calibracion.py` | 123 | `test_visor_filtro_rango_estructura` | IV | — | `Nodo sin etiqueta canónica` |  |
| 224 | `qbe_observatory/tests/test_visor_auditoria_calibracion.py` | 132 | `test_visor_snapshot_ausente_degrada_sin_fallback` | IV | — | `Nodo sin etiqueta canónica` |  |
| 225 | `qbe_observatory/tests/test_visor_auditoria_calibracion.py` | 146 | `test_main_no_consume_el_builder_legacy_del_historico` | IV | — | `Nodo sin etiqueta canónica` |  |
| 226 | `qbe_observatory/tests/test_visor_auditoria_calibracion.py` | 160 | `test_visor_presentacion_saneada` | IV | — | `Nodo sin etiqueta canónica` |  |
| 227 | `qbe_observatory/tests/test_visor_auditoria_calibracion.py` | 183 | `_vista_sintetica` | IV | — | `Nodo sin etiqueta canónica` |  |
| 228 | `qbe_observatory/tests/test_visor_auditoria_calibracion.py` | 254 | `_render_visor` | IV | — | `Nodo sin etiqueta canónica` |  |
| 229 | `qbe_observatory/tests/test_visor_auditoria_calibracion.py` | 268 | `test_visor_pildora_declara_bando_y_oculta_el_token_crudo` | IV | — | `Nodo sin etiqueta canónica` |  |
| 230 | `qbe_observatory/tests/test_visor_match_card.py` | 31 | `cliente` | IV | — | `Nodo sin etiqueta canónica` |  |
| 231 | `qbe_observatory/tests/test_visor_match_card.py` | 40 | `reporte` | IV | — | `Nodo sin etiqueta canónica` |  |
| 232 | `qbe_observatory/tests/test_visor_match_card.py` | 47 | `html` | IV | — | `Nodo sin etiqueta canónica` |  |
| 233 | `qbe_observatory/tests/test_visor_match_card.py` | 54 | `_tarjetas` | IV | — | `Nodo sin etiqueta canónica` |  |
| 234 | `qbe_observatory/tests/test_visor_match_card.py` | 58 | `_celda` | IV | — | `Nodo sin etiqueta canónica` |  |
| 235 | `qbe_observatory/tests/test_visor_match_card.py` | 66 | `_vista_sintetica` | IV | — | `Nodo sin etiqueta canónica` |  |
| 236 | `qbe_observatory/tests/test_visor_match_card.py` | 142 | `_render` | IV | — | `Nodo sin etiqueta canónica` |  |
| 237 | `qbe_observatory/tests/test_visor_match_card.py` | 155 | `test_match_card_una_por_partido` | IV | — | `Nodo sin etiqueta canónica` |  |
| 238 | `qbe_observatory/tests/test_visor_match_card.py` | 164 | `test_match_card_parrilla_1x2_tres_celdas` | IV | — | `Nodo sin etiqueta canónica` |  |
| 239 | `qbe_observatory/tests/test_visor_match_card.py` | 178 | `test_match_card_boton_32v_y_cascaron_unico` | IV | — | `Nodo sin etiqueta canónica` |  |
| 240 | `qbe_observatory/tests/test_visor_match_card.py` | 188 | `test_match_card_modal_contrato_apertura_cierre` | IV | — | `Nodo sin etiqueta canónica` |  |
| 241 | `qbe_observatory/tests/test_visor_match_card.py` | 198 | `test_match_card_marca_valor_sin_depender_del_color` | IV | — | `Nodo sin etiqueta canónica` |  |
| 242 | `qbe_observatory/tests/test_visor_match_card.py` | 213 | `test_match_card_marca_acierto_en_la_celda_correcta` | IV | — | `Nodo sin etiqueta canónica` |  |
| 243 | `qbe_observatory/tests/test_visor_match_card.py` | 223 | `test_match_card_cold_start_suprime_el_veredicto_de_valor` | IV | — | `Nodo sin etiqueta canónica` |  |
| 244 | `qbe_observatory/tests/test_visor_match_card.py` | 247 | `test_match_card_vertice_mapea_la_clasificacion_canonica` | IV | — | `Nodo sin etiqueta canónica` |  |
| 245 | `qbe_observatory/tests/test_visor_match_card.py` | 260 | `test_match_card_balon_sustituye_al_check` | IV | — | `Nodo sin etiqueta canónica` |  |
| 246 | `qbe_observatory/tests/test_visor_match_card.py` | 270 | `test_match_card_barras_pmax_y_mktmax` | IV | — | `Nodo sin etiqueta canónica` |  |
| 247 | `qbe_observatory/tests/test_visor_match_card.py` | 290 | `test_match_card_cold_start_no_tiñe_el_vertice` | IV | — | `Nodo sin etiqueta canónica` |  |
| 248 | `qbe_observatory/tests/test_visor_match_card.py` | 306 | `test_match_card_sin_riel_de_valor` | IV | — | `Nodo sin etiqueta canónica` |  |
| 249 | `qbe_observatory/tests/test_visor_match_card.py` | 314 | `test_match_card_tetralogia_sin_epist` | IV | — | `Nodo sin etiqueta canónica` |  |
| 250 | `qbe_observatory/tests/test_visor_match_card.py` | 326 | `test_match_card_brier_vars_declara_el_vacio` | IV | — | `Nodo sin etiqueta canónica` |  |
| 251 | `qbe_observatory/tests/test_visor_match_card.py` | 338 | `test_match_card_sin_hex_inline` | IV | — | `Nodo sin etiqueta canónica` |  |
| 252 | `qbe_observatory/tests/test_visor_match_card.py` | 344 | `test_match_card_paridad_brier_con_endpoint` | IV | — | `Nodo sin etiqueta canónica` |  |
| 253 | `qbe_observatory/tests/test_visor_match_card.py` | 354 | `test_match_card_degrada_sin_explotar` | IV | — | `Nodo sin etiqueta canónica` |  |
| 254 | `qbe_observatory/tests/test_visor_match_card.py` | 364 | `test_fragmento_vars44_bajo_demanda` | IV | — | `Nodo sin etiqueta canónica` |  |
| 255 | `qbe_observatory/tests/test_visor_match_card.py` | 373 | `test_fragmento_vars44_partido_inexistente` | IV | — | `Nodo sin etiqueta canónica` |  |
| 256 | `qbe_observatory/tests/test_visor_match_card.py` | 378 | `_render_panel` | IV | — | `Nodo sin etiqueta canónica` |  |
| 257 | `qbe_observatory/tests/test_visor_match_card.py` | 388 | `test_fragmento_vars44_transcribe_cifras_textuales` | IV | — | `Nodo sin etiqueta canónica` |  |

---

**VÍA A:** erradicación de la regla huérfana. **VÍA B:** formalización legislativa y etiquetado con Juez.
