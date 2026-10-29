/*
 * [DES-QBE-075] Apertura y cierre del modal de 32 variables — Observatorio.
 * Régimen [DBBD-FUNGIBLE]: el cliente NO pinta el catálogo; pide el fragmento
 * HTML ya transcrito por Jinja (`/visor/partido/<id>/variables`, B2) y lo inyecta
 * en `#vars44-cuerpo`. Abrir/cerrar conserva el contrato sellado: `hidden` en el
 * cascarón único, cierre por botón, clic en el velo y tecla Escape.
 */
(() => {
  'use strict';

  const modal = document.getElementById('modal-44-variables');
  if (!modal) return;

  const cuerpo = document.getElementById('vars44-cuerpo');
  const titulo = document.getElementById('vars44-titulo');
  const botonCerrar = modal.querySelector('[data-cerrar-modal]');
  const TITULO_BASE = titulo ? titulo.textContent : '🔬 Catálogo de 32 variables';
  let focoPrevio = null;

  const abrir = () => {
    modal.hidden = false;
    document.documentElement.classList.add('vars44-abierto');
    if (botonCerrar) botonCerrar.focus();
  };

  const cerrar = () => {
    if (modal.hidden) return;
    modal.hidden = true;
    document.documentElement.classList.remove('vars44-abierto');
    if (focoPrevio && typeof focoPrevio.focus === 'function') focoPrevio.focus();
    focoPrevio = null;
  };

  const cargar = async (url) => {
    if (!cuerpo) return;
    cuerpo.innerHTML = '<div class="vars44-aviso">⏳ Cargando panel forense del partido…</div>';
    try {
      const respuesta = await fetch(url, { headers: { 'X-Requested-With': 'fetch' } });
      if (!respuesta.ok) throw new Error(String(respuesta.status));
      cuerpo.innerHTML = await respuesta.text();
    } catch (error) {
      cuerpo.innerHTML = '<div class="vars44-aviso">⚪ No se pudo cargar el panel forense del ' +
        'partido. Verifique que el snapshot de calibración siga disponible y recargue la página.</div>';
    }
  };

  document.addEventListener('click', (evento) => {
    const disparador = evento.target.closest('.btn-ver-44-vars');
    if (disparador) {
      evento.preventDefault();
      focoPrevio = disparador;
      const url = disparador.getAttribute('data-vars44-url');
      if (titulo) {
        titulo.textContent = disparador.getAttribute('data-vars44-titulo') || TITULO_BASE;
      }
      if (cuerpo) cuerpo.innerHTML = '';
      abrir();
      if (url) cargar(url);
      return;
    }
    if (evento.target.closest('[data-cerrar-modal]')) {
      cerrar();
      return;
    }
    if (evento.target === modal) cerrar();
  });

  document.addEventListener('keydown', (evento) => {
    if (evento.key === 'Escape') cerrar();
  });
})();
