// Fachada de feature flags de la SPA — Fase 3.
// Si el módulo está desactivado, el tab se bloquea antes de disparar endpoints
// que no pertenecen a Business (backtesting → Observatorio, admin → Ingesta).
(async () => {
  try {
    const response = await fetch("/api/business/features", { headers: { Accept: "application/json" } });
    if (!response.ok) return;
    const flags = await response.json();
    window.QBE_FEATURES = flags;

    const bloquear = (id, habilitado) => {
      const elemento = document.getElementById(id);
      if (!elemento || habilitado) return;
      elemento.setAttribute("aria-disabled", "true");
      elemento.classList.add("is-disabled");
      elemento.addEventListener(
        "click",
        (evento) => {
          evento.preventDefault();
          evento.stopImmediatePropagation();
        },
        true
      );
    };

    bloquear("tab-visor-backtesting", Boolean(flags.backtesting));
    bloquear("btn-tab-control", Boolean(flags.admin));
  } catch (_) {
    // La SPA sigue operando con los tabs visibles; el backend responde 503.
  }
})();
