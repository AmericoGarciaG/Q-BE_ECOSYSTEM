# -*- coding: utf-8 -*-
"""
[ARCH-1.4.26] Paquete Soberano de Memoria Histórica (Capa 4 — Sovereign Memory).
Régimen: [DIRGEN-STRICT].

Submódulos puros (`[ARCH-PILLAR]`), sin I/O, sin red, sin SQLAlchemy y sin acoplamiento a
`src.storage` / `src.ingestion` (invariante de pureza auditada por AST en
`tests/shield/test_shield_bayesian_form_and_h2h.py`):

* `bayesian_form.py` → `[LN-QBE-036]` Contracción Bayesiana de Forma Reciente (10 partidos).
* `h2h_kernel.py`   → `[LN-QBE-020-C]` Kernel H2H Empírico en Eje Localía.

Composición sellada: el amortiguamiento hiperbólico se delega en `[VAULT-CORE-001]`
(`src/core/intensity_canonical_loglink.py`) y la constante de decaimiento κ = ln(2)/180 en
`[LN-QBE-020]` (`src/core/temporal.py`). Ninguna constante del canon se transcribe aquí.
"""
