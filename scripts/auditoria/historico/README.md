# Auditoría forense histórica — solo lectura

Sondas de diagnóstico del expediente `SPRINT-47-AUDITORIA-DATOS-HISTORICOS`.
No escriben bases de datos, no modifican la UI y no alteran `src/`.

| Script | Fuente | Salida |
|---|---|---|
| `auditar_134_partidos.py` | Reporte de calibración de Auditoría (`observatory_snapshot.db`, solo lectura) | Primeros 5 partidos con P Q-BE, P FootyStats, resultado y Brier individual 3N |
| `auditar_3870_partidos.py` | `qbe_historico.db` → `historical_matches` (solo lectura) | Muestra aleatoria de 5 partidos con momios/resultado, probabilidades implícitas, Brier crudo y Brier/3 |

## Ejecución

```bash
python scripts/auditoria/historico/auditar_134_partidos.py
python scripts/auditoria/historico/auditar_3870_partidos.py
```

## Convención de Brier

- La UI y las vistas del ecosistema usan **Brier multiclase normalizado 3N**:
  `suma de las 3 casillas / (3 · N)`.
- Las sondas conservan el **crudo** (`suma de las 3 casillas / N`) únicamente como
  evidencia forense; el crudo no se publica en la UI.
- `historical_matches` no tiene Q-BE por partido: el Alpha histórico solo puede
  calcularse en la muestra de control donde Q-BE y mercado convergen.
