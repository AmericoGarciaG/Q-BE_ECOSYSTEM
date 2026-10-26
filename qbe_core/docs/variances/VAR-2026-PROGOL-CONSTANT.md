# VAR-2026-PROGOL-CONSTANT — Enmienda del sello `MANIFEST_FASE1`

| Campo | Valor |
|---|---|
| **ID** | `VAR-2026-PROGOL-CONSTANT` |
| **Fecha** | 2026-10-25 |
| **Régimen** | `[DIRGEN-STRICT]` |
| **Estado** | **EJECUTADA POR DIRECTIVA DE FASE 3 §3.2** |
| **Archivo afectado** | `qbe_core/src/core/constants.py` |
| **Hash anterior** | `168e233702aba8c60b7f94cd8ce5938e820f770a13d145b2ce81b20115c5ba64` |
| **Hash nuevo** | `a4c52fac5b483bcd9764758180dad31c83af7b4947a031a888df40f878027a68` |
| **Manifiesto vigente** | `MANIFEST_FASE1_REV2.sha256` (8/8) |
| **Manifiesto histórico** | `MANIFEST_FASE1.sha256` (7/8 respecto al estado actual; conservado) |

## Motivo

La directiva de Fase 3 §3.2 ordenó mover `PRIOR_IGNORANCIA_FIDUCIARIA` desde
`src.ingestion.progol_scraper` a `src.core.constants`, para que `progol_math`
pueda vivir en `qbe_core` sin importar la ingesta.

## Cambio exacto

Se añadió al final de `constants.py`:

```python
PRIOR_IGNORANCIA_FIDUCIARIA: tuple[float, float, float] = (0.3333, 0.3333, 0.3334)
```

No se modificó ninguna constante existente, fórmula, clamp ni firma.

## Verificación

- `MANIFEST_FASE1_REV2.sha256`: **8/8 OK**.
- Los otros 7 archivos del manifiesto original conservan su hash.
- `qbe_core` sigue importando sin SQLAlchemy/ingesta.
- El baseline `Q_BE_CD_WEB` no fue mutado (no se eliminó su `progol_math.py`).

## Nota de gobierno

El sello histórico `MANIFEST_FASE1.sha256` se conserva para auditoría. La
certificación vigente es `REV2`; cualquier otra modificación de los 8 módulos
exige una nueva enmienda.
