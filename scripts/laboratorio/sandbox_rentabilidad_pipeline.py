# -*- coding: utf-8 -*-
"""Wrapper de compatibilidad CLI del motor de simulación retrospectiva.

[ARCH-1.6.4 · Enmienda Nudo 3] La lógica reside en
`qbe_observatory/src/observatory/core/simulation_engine.py`.
Este archivo sólo preserva la ruta histórica de invocación
(`python -m scripts.laboratorio.sandbox_rentabilidad_pipeline`) y reexporta el
contrato público para los consumidores de consola. `src/` ya no depende de este
script: la dependencia se invirtió.
"""
from src.observatory.core.simulation_engine import *  # noqa: F401,F403
from src.observatory.core.simulation_engine import main  # noqa: F401

if __name__ == "__main__":
    raise SystemExit(main())
