// src/web/static/js/app.js
// Q-BE Casino Deportes — Live Board Reactivo SPA (DES-QBE-016 / ARCH-1.6.0 / ARCH-1.6.2)

let currentLiveBoard = null;
let selectedMatchIds = [];

document.addEventListener("DOMContentLoaded", function () {
    initNavigation();
    cargarLigasDesdeBD();
    initVisorBacktesting();
});

function initNavigation() {
    const tabs = document.querySelectorAll('.tab-btn');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const target = tab.getAttribute('data-tab');
            switchView(target);
        });
    });
}

function switchView(viewId) {
    document.querySelectorAll('.view-section').forEach(v => v.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(t => t.classList.remove('active'));

    const targetView = document.getElementById(viewId);
    if (targetView) targetView.classList.add('active');
    const targetTab = document.querySelector(`.tab-btn[data-tab="${viewId}"]`);
    if (targetTab) targetTab.classList.add('active');
}

function switchTableTab(tabName) {
    document.querySelectorAll('.subtab-btn').forEach(btn => btn.classList.remove('active'));
    const clickedBtn = document.getElementById(`btn-tab-${tabName}`);
    if (clickedBtn) clickedBtn.classList.add('active');

    const colGen = document.querySelectorAll('.col-gen');
    const colForma = document.querySelectorAll('.col-forma');
    const colXg = document.querySelectorAll('.col-xg');

    colGen.forEach(el => el.style.display = (tabName === 'general') ? '' : 'none');
    colForma.forEach(el => el.style.display = (tabName === 'forma') ? '' : 'none');
    colXg.forEach(el => el.style.display = (tabName === 'xg') ? '' : 'none');
}

// 1. Cargar Ligas en Vista 1
async function cargarLigasDesdeBD() {
    try {
        const resp = await fetch("/api/leagues");
        if (!resp.ok) throw new Error("Error al consultar /api/leagues");
        const ligas = await resp.json();

        const grid = document.querySelector(".leagues-grid");
        if (!grid) return;
        grid.innerHTML = "";

        ligas.forEach(l => {
            const card = document.createElement("div");
            card.className = "league-card active";
            card.style.cssText = "background: #1C2541; border: 1px solid #00E676; border-radius: 8px; padding: 14px; cursor: pointer; transition: transform 0.15s ease;";
            const logoHtml = l.flag ? `<img src="${l.flag}" alt="" onerror="this.src='/static/img/favicon.svg'" style="width: 32px; height: 32px; object-fit: contain; margin-bottom: 8px;">` : `<div style="font-size: 14pt; font-weight: 800; color: #38BDF8; margin-bottom: 6px;">MX</div>`;
            card.innerHTML = `
                <div style="margin-bottom: 4px;">${logoHtml}</div>
                <div class="league-info">
                    <h3 style="margin: 0; color: #ffffff; font-size: 1.05rem;">${l.name}</h3>
                    <span style="font-size: 7.5pt; color: #94A3B8;">${l.country}</span>
                    <div style="font-size: 7.2pt; color: #00E676; font-weight: 700; margin-top: 6px;">• 18 Clubes</div>
                </div>
            `;
            card.onmouseenter = () => card.style.transform = "translateY(-3px)";
            card.onmouseleave = () => card.style.transform = "translateY(0)";
            card.onclick = () => seleccionarLiga(l.fotmob_id);
            grid.appendChild(card);
        });
    } catch (e) {
        console.error("Fallo cargando ligas:", e);
    }
}

// 2. Seleccionar Liga y Cargar Live Board en Vista 2
async function seleccionarLiga(fotmobId, forceRefresh = false, targetJornada = null) {
    switchView("view-matchday-selection");
    const tbody = document.querySelector(".table-panel-left table tbody");
    if (tbody && !currentLiveBoard) tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; padding:20px; color:#38BDF8;">⏳ Sincronizando datos oficiales en tiempo real...</td></tr>';

    try {
        let url = `/api/leagues/${fotmobId}/live-board`;
        const params = [];
        if (targetJornada !== null && targetJornada !== undefined) params.push(`jornada=${targetJornada}`);
        if (forceRefresh) params.push("force_refresh=true");
        if (params.length > 0) url += "?" + params.join("&");

        const resp = await fetch(url);
        if (!resp.ok) throw new Error("Error al obtener Live Board");
        currentLiveBoard = await resp.json();

        const lblTabla = document.getElementById("lbl-nombre-tabla");
        if (lblTabla) lblTabla.textContent = currentLiveBoard.league_name || "Liga MX";
        const lblJornada = document.getElementById("lbl-nombre-jornada");
        if (lblJornada) {
            // [DES-QBE-056 / ARCH-1.6.15-C] Etiqueta derivada del payload: cero celdas quemadas.
            const vigenteLbl = (currentLiveBoard.jornada_actual !== null && currentLiveBoard.jornada_actual !== undefined)
                ? currentLiveBoard.jornada_actual : currentLiveBoard.jornada_mostrada;
            const jornadaBase = currentLiveBoard.jornada ||
                (Number.isInteger(vigenteLbl) ? `Jornada ${vigenteLbl}` : "Jornada —");
            // [UI-REFINEMENT-5-POINTS §4] La fecha de la jornada NO se quema: se deriva del
            // rango fáctico de los fixtures vigentes del Live Board.
            const rangoFechasJornada = _rangoFechasJornada(currentLiveBoard.fixtures);
            lblJornada.textContent = rangoFechasJornada ? `${jornadaBase} · ${rangoFechasJornada}` : jornadaBase;
        }
        const lblTime = document.getElementById("lbl-timestamp-tabla");
        if (lblTime) {
            lblTime.textContent = `🕒 Tabla Oficial: Sincronizada en vivo (${_formatearFechaHoraActual()})`;
        }

        renderizarPildorasJornada(currentLiveBoard);

        // [DES-QBE-051] Guarda de bóveda vacía: banner didáctico, jamás excepción roja
        if (!currentLiveBoard.standings || currentLiveBoard.standings.length === 0) {
            if (tbody) tbody.innerHTML = `<tr><td colspan="9" style="text-align:center; padding:30px; color:#94A3B8;">
                ℹ️ Base de datos en reposo / vacía.<br>
                <span style="font-size:8pt; color:#38BDF8;">Vaya a <strong>[ ⚙️ Centro de Control ]</strong> y presione <em>"⚡ Ejecutar Cadena de Ingesta Total"</em> para sincronizar la liga en vivo.</span>
            </td></tr>`;
        } else {
            renderizarTabla18Clubes(currentLiveBoard.standings);
        }

        renderizarCartelera(currentLiveBoard.fixtures);
    } catch (e) {
        console.error("Error cargando live board:", e);
        if (tbody) tbody.innerHTML = `<tr><td colspan="9" style="text-align:center; color:#f87171;">❌ Error al conectar: ${e.message}</td></tr>`;
    }
}

// [DES-QBE-056] Apertura determinista en la jornada VIGENTE: la píldora activa emana del estado
// fáctico de la bóveda (`jornada_actual` → primer partido PROGRAMADO), jamás de una celda fija.
// Cero invención: si la bóveda no dicta jornada, no se fabrica ninguna.
function resolverJornadaVigenteLiveBoard(liveBoard) {
    if (!liveBoard) return null;
    if (Number.isInteger(liveBoard.jornada_actual)) return liveBoard.jornada_actual;
    const fixtures = Array.isArray(liveBoard.fixtures) ? liveBoard.fixtures : [];
    const jornadaDe = (f) => {
        if (!f) return null;
        if (Number.isInteger(f.jornada)) return f.jornada;
        if (Number.isInteger(f.matchday)) return f.matchday;
        return null;
    };
    const pendientes = fixtures
        .filter(f => f && String(f.estado || "").toUpperCase() === "PROGRAMADO")
        .map(jornadaDe).filter(j => j !== null);
    if (pendientes.length > 0) return Math.min.apply(null, pendientes);
    const ledgeradas = fixtures.map(jornadaDe).filter(j => j !== null);
    if (ledgeradas.length > 0) return Math.max.apply(null, ledgeradas);
    return null;
}

// [DES-QBE-037] Carrusel Ventanizado Determinista (Máximo 3 píldoras en pantalla)
function renderizarPildorasJornada(liveBoard) {
    const container = document.getElementById("matchday-pill-selector");
    if (!container) return;
    container.innerHTML = "";

    const disponibles = liveBoard.jornadas_disponibles || [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17];
    const actual = resolverJornadaVigenteLiveBoard(liveBoard);
    if (!Number.isInteger(actual)) {
        container.innerHTML = '<span style="font-size:7.5pt; color:#94A3B8;">ℹ️ Sin jornadas ledgeradas en la bóveda: ejecute la ingesta en el Centro de Control.</span>';
        return;
    }
    const mostrada = Number.isInteger(liveBoard.jornada_mostrada) ? liveBoard.jornada_mostrada : actual;

    // 1. Calcular la ventana de 3 jornadas visibles [mostrada - 1, mostrada, mostrada + 1]
    let ventana = [mostrada - 1, mostrada, mostrada + 1];
    if (mostrada === 1) ventana = [1, 2, 3];
    if (mostrada === 17) ventana = [15, 16, 17];

    // Filtrar para que solo existan jornadas dentro del rango 1 a 17
    ventana = ventana.filter(j => j >= 1 && j <= 17);

    // 2. Controlar estado de flechas ◄ y ►
    const btnPrev = document.getElementById("btn-carousel-prev");
    const btnNext = document.getElementById("btn-carousel-next");
    if (btnPrev) btnPrev.disabled = (mostrada <= 1);
    if (btnNext) btnNext.disabled = (mostrada >= 17);

    // 3. Renderizar ÚNICAMENTE las 3 píldoras visibles
    ventana.forEach(jNum => {
        const btn = document.createElement("button");
        btn.type = "button";
        const isActive = (jNum === mostrada);
        btn.className = "pill-tab" + (isActive ? " active" : "");
        
        btn.style.cssText = `
            background: ${isActive ? '#0284C7' : '#1C2541'};
            border: 1px solid ${isActive ? '#38BDF8' : '#334155'};
            color: ${isActive ? '#FFFFFF' : '#94A3B8'};
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.78rem;
            font-weight: 700;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            white-space: nowrap;
            box-shadow: ${isActive ? '0 0 8px rgba(56, 189, 248, 0.35)' : 'none'};
        `;

        let badgeLabel = "";
        if (jNum < actual) {
            badgeLabel = "🏁";
        } else if (jNum === actual) {
            badgeLabel = "⚡ Activa";
        } else {
            badgeLabel = "📅";
        }

        btn.innerHTML = `<span>Jornada ${jNum}</span><span style="font-size:0.68rem; opacity:0.8;">${badgeLabel}</span>`;
        
        btn.onclick = (e) => {
            e.preventDefault();
            if (jNum === mostrada) return;
            const leagueId = liveBoard.league_id || 262;
            seleccionarLiga(leagueId, false, jNum);
        };
        container.appendChild(btn);
    });
}

function navegarCarruselTemporal(delta) {
    if (!currentLiveBoard) return;
    // [DES-QBE-056] La navegación parte de la jornada vigente derivada, nunca de una celda fija.
    const vigenteCarrusel = resolverJornadaVigenteLiveBoard(currentLiveBoard);
    const mostrada = Number.isInteger(currentLiveBoard.jornada_mostrada)
        ? currentLiveBoard.jornada_mostrada
        : vigenteCarrusel;
    if (!Number.isInteger(mostrada)) return;
    const targetJornada = mostrada + delta;
    if (targetJornada >= 1 && targetJornada <= 17) {
        const leagueId = currentLiveBoard.league_id || 262;
        seleccionarLiga(leagueId, false, targetJornada);
    }
}
window.navegarCarruselTemporal = navegarCarruselTemporal;
window.renderizarCarruselTemporadaCompleta = renderizarPildorasJornada;



function _formatearFechaHoraActual() {
    const ahora = new Date();
    const meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];
    const dia = ahora.getDate();
    const mes = meses[ahora.getMonth()];
    const hora = ahora.toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit" });
    return `${dia}-${mes} ${hora}`;
}

// [DES-QBE-056 / UI-REFINEMENT-5-POINTS §4] Rango fáctico de fechas de la jornada derivado
// EXCLUSIVAMENTE de los fixtures entregados por el Live Board (cero fechas quemadas en la UI).
// Degradación honesta: sin `fecha_dt`/`fecha_bloque` legibles retorna "" y el rótulo conserva
// únicamente el número de jornada ([GOVERNANCE-01]).
function _rangoFechasJornada(fixtures) {
    const MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
                   "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"];
    const fechas = (Array.isArray(fixtures) ? fixtures : [])
        .map(f => (f ? (f.fecha_dt || f.fecha_bloque) : null))
        .map(v => (v ? new Date(v) : null))
        .filter(d => d instanceof Date && !isNaN(d.getTime()))
        .sort((a, b) => a - b);
    if (fechas.length === 0) return "";
    const ini = fechas[0];
    const fin = fechas[fechas.length - 1];
    const mes = (d) => MESES[d.getMonth()];
    if (ini.getFullYear() === fin.getFullYear() && ini.getMonth() === fin.getMonth()) {
        return (ini.getDate() === fin.getDate())
            ? `${ini.getDate()} de ${mes(ini)} de ${ini.getFullYear()}`
            : `${ini.getDate()} al ${fin.getDate()} de ${mes(fin)} de ${fin.getFullYear()}`;
    }
    if (ini.getFullYear() === fin.getFullYear()) {
        return `${ini.getDate()} de ${mes(ini)} al ${fin.getDate()} de ${mes(fin)} de ${fin.getFullYear()}`;
    }
    return `${ini.getDate()} de ${mes(ini)} de ${ini.getFullYear()} al ${fin.getDate()} de ${mes(fin)} de ${fin.getFullYear()}`;
}

// ── 1. Refrescar ÚNICAMENTE la Tabla de Posiciones (Panel Izquierdo) ─────────
async function refrescarTablaEnVivo() {
    const targetId = currentLiveBoard ? currentLiveBoard.league_id : 262;
    const btn = document.getElementById("btn-force-refresh");
    const tbody = document.querySelector(".table-panel-left table tbody");

    if (btn) btn.innerHTML = "⏳ Refrescando...";
    if (tbody) tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; padding:20px; color:#38BDF8;">⏳ Sincronizando tabla oficial...</td></tr>';

    try {
        const resp = await fetch(`/api/leagues/${targetId}/refresh-tabla`, { method: "POST" });
        if (!resp.ok) throw new Error("Error en respuesta del servidor");
        const data = await resp.json();

        // Actualizar ÚNICAMENTE el panel izquierdo
        renderizarTabla18Clubes(data.standings);

        const lblTime = document.getElementById("lbl-timestamp-tabla");
        if (lblTime) {
            lblTime.textContent = `🕒 Tabla Oficial: Sincronizada en vivo (${_formatearFechaHoraActual()})`;
        }
    } catch (e) {
        console.error("Error refrescando tabla:", e);
    } finally {
        if (btn) btn.innerHTML = "🔄 Refrescar Tabla";
    }
}
window.refrescarTablaEnVivo = refrescarTablaEnVivo;

async function refrescarCarteleraEnVivo() {
    const targetId = currentLiveBoard ? currentLiveBoard.league_id : 262;
    const btn = document.getElementById("btn-refresh-cartelera");
    const container = document.querySelector(".fixtures-list");

    if (btn) btn.innerHTML = "⏳ Refrescando...";
    if (container) container.innerHTML = '<div style="text-align:center; padding:25px; color:#38BDF8; font-size:8.5pt;">⏳ Sincronizando momios Caliente en vivo...</div>';

    try {
        const resp = await fetch(`/api/leagues/${targetId}/refresh-momios`, { method: "POST" });
        if (!resp.ok) throw new Error("Error en respuesta del servidor");
        const data = await resp.json();

        // Actualizar ÚNICAMENTE el panel derecho
        renderizarCartelera(data.fixtures);

        const lblTime = document.getElementById("lbl-timestamp-cartelera");
        if (lblTime) {
            lblTime.textContent = `🕒 Momios Caliente: Sincronizados en vivo (${_formatearFechaHoraActual()})`;
        }
    } catch (e) {
        console.error("Error refrescando cartelera:", e);
    } finally {
        if (btn) btn.innerHTML = "🔄 Refrescar Momios";
    }
}
window.refrescarCarteleraEnVivo = refrescarCarteleraEnVivo;

// 3. Renderizar Tabla de 18 Clubes Completa (Panel Izquierdo)
function renderizarTabla18Clubes(standings) {
    const tbody = document.querySelector(".table-panel-left table tbody");
    if (!tbody || !standings) return;
    tbody.innerHTML = "";

    standings.forEach(t => {
        const tr = document.createElement("tr");

        // Renderizado del escudo oficial del club
        const escudoHtml = t.escudo_url ? `<img src="${t.escudo_url}" alt="" style="width: 16px; height: 16px; object-fit: contain; vertical-align: middle; margin-right: 6px;">` : '';

        // Forma con círculos de colores en contenedor horizontal anti-descuadre [DES-QBE-036]
        const formaHtml = `<div class="form-badges-wrapper" style="display: inline-flex; align-items: center; justify-content: center; gap: 3px; white-space: nowrap;">` +
            (t.forma || ["G", "E", "P"]).map(f => {
                const cls = (f === "G" || f === "W") ? "badge-g" : (f === "E" || f === "D") ? "badge-e" : "badge-p";
                const letra = (f === "G" || f === "W") ? "G" : (f === "E" || f === "D") ? "E" : "P";
                return `<span class="form-badge ${cls}" style="display: inline-flex; align-items: center; justify-content: center; width: 14px; height: 14px; border-radius: 50%; font-size: 6pt; font-weight: 800; color: #fff;">${letra}</span>`;
            }).join("") + `</div>`;

        // Renderizado del próximo rival con escudo miniatura [DES-QBE-016]
        const proxEscudoHtml = t.proximo_escudo_url ? `<img src="${t.proximo_escudo_url}" alt="" style="width: 14px; height: 14px; object-fit: contain; vertical-align: middle; margin-right: 4px;">` : '';
        const proximoHtml = `<div style="display: inline-flex; align-items: center; white-space: nowrap; color: #38BDF8; font-weight: 600; font-size: 7.2pt;">${proxEscudoHtml}${t.proximo_rival || "—"}</div>`;

        const difColor = t.dif >= 0 ? "#00E676" : "#f87171";
        const difSign = t.dif > 0 ? "+" : "";

        // Cálculo limpio de diferencia xG sin doble signo (+ -)
        const xgVal = parseFloat(t.xg || 0);
        const xgaVal = parseFloat(t.xga || 0);
        const difXg = xgVal - xgaVal;
        const difXgSign = difXg > 0 ? "+" : "";
        const difXgColor = difXg >= 0 ? "#00E676" : "#f87171";
        const difXgFormatted = `${difXgSign}${difXg.toFixed(1)}`;

        tr.innerHTML = `
            <td style="text-align: center; font-weight: 700;">${t.pos}</td>
            <td style="font-weight: 600; color: #ffffff; white-space: nowrap;">${escudoHtml}${t.equipo}</td>
            <td style="text-align: center; font-weight: 700; color: #00E676;">${t.puntos}</td>
            <!-- General -->
            <td class="col-gen" style="text-align: center;">${t.pj}</td>
            <td class="col-gen" style="text-align: center;">${t.pg}</td>
            <td class="col-gen" style="text-align: center;">${t.pe}</td>
            <td class="col-gen" style="text-align: center;">${t.pp}</td>
            <td class="col-gen" style="text-align: center;">${t.gf}:${t.gc}</td>
            <td class="col-gen" style="text-align: center; font-weight: 700; color: ${difColor};">${difSign}${t.dif}</td>
            <!-- Forma -->
            <td class="col-forma" style="text-align: center; white-space: nowrap !important; display: none;">${formaHtml}</td>
            <td class="col-forma" style="text-align: center; white-space: nowrap !important; display: none;">${proximoHtml}</td>
            <!-- xG Opta -->
            <td class="col-xg" style="text-align: center; color: #38BDF8; font-weight: 600; display: none;">${t.xg || "—"}</td>
            <td class="col-xg" style="text-align: center; color: #f87171; display: none;">${t.xga || "—"}</td>
            <td class="col-xg" style="text-align: center; color: #00E676; font-weight: 700; display: none;">${t.xpts || "—"}</td>
            <td class="col-xg" style="text-align: center; font-weight: 700; color: ${difXgColor}; display: none;">${difXgFormatted}</td>
        `;
        tbody.appendChild(tr);
    });
}

// 4. Renderizar Cartelera en 4 Niveles Visuales [DES-QBE-016-C] [ARCH-1.6.3]
function renderizarCartelera(fixtures) {
    const container = document.getElementById("fixtures-container") || document.querySelector(".fixtures-scroll-container");
    if (!container || !fixtures) return;
    container.innerHTML = "";
    selectedMatchIds = [];

    // Separar por estado semántico (Ordenamiento Topológico ya aplicado por el backend)
    const enCurso = fixtures.filter(f => f.estado === "EN_CURSO");
    const programados = fixtures.filter(f => f.estado === "PROGRAMADO");
    const reprogramados = fixtures.filter(f => f.estado === "REPROGRAMADO");
    const finalizados = fixtures.filter(f => f.estado === "FINALIZADO");

    // ── Nivel 1: EN CURSO ─────────────────────────────────────────────────
    if (enCurso.length > 0) {
        _renderSeccionHeader(container, "🔴 En Juego Ahora", "header-live");
        enCurso.forEach(f => _renderFixtureCard(container, f, false));
    }

    // ── Nivel 2: PROGRAMADOS — agrupados por fecha (con prefijo HOY dinámico) ──
    if (programados.length > 0) {
        const grupos = {};
        programados.forEach(f => {
            const hoy = f.fecha_dt ? _esHoyDinamico(f.fecha_dt) : false;
            const label = hoy ? `HOY — ${f.fecha_bloque}` : f.fecha_bloque;
            if (!grupos[label]) grupos[label] = [];
            grupos[label].push(f);
        });
        Object.keys(grupos).forEach(label => {
            _renderSeccionHeader(container, `📅 ${label}`, "");
            grupos[label].forEach(f => _renderFixtureCard(container, f, false));
        });
    }

    // ── Nivel 3: REPROGRAMADOS ────────────────────────────────────────────
    if (reprogramados.length > 0) {
        _renderSeccionHeader(container, "⏳ Partidos Reprogramados / Fecha Lejana", "header-postponed");
        reprogramados.forEach(f => _renderFixtureCard(container, f, false));
    }

    // ── Nivel 4: FINALIZADOS al fondo ─────────────────────────────────────
    if (finalizados.length > 0) {
        _renderSeccionHeader(container, "🏁 Partidos Concluidos de la Jornada", "header-finished");
        finalizados.forEach(f => _renderFixtureCard(container, f, true));
    }

    actualizarContadorSeleccionados();

    // Habilitar clicabilidad total de tarjeta [DES-QBE-016-C]
    habilitarClicTarjetaCompleta();
}

/** Evalúa dinámicamente si una fecha ISO 8601 corresponde al día de hoy [ARCH-1.6.3] */
function _esHoyDinamico(fechaDtStr) {
    if (!fechaDtStr) return false;
    try {
        const dt = new Date(fechaDtStr);
        const hoy = new Date();
        return dt.getFullYear() === hoy.getFullYear() &&
            dt.getMonth() === hoy.getMonth() &&
            dt.getDate() === hoy.getDate();
    } catch (e) {
        return false;
    }
}

/** Renderiza un encabezado de sección con clase de color opcional */
function _renderSeccionHeader(container, texto, claseAdicional) {
    const div = document.createElement("div");
    div.className = `fixture-section-header ${claseAdicional}`.trim();
    div.textContent = texto;
    container.appendChild(div);
}

/** Renderiza una tarjeta de fixture según su estado semántico [DES-QBE-016-C] */
function _renderFixtureCard(container, f, deshabilitada) {
    const estado = f.estado || "PROGRAMADO";
    const card = document.createElement("div");
    card.className = "card match-card-clean";
    card.id = `fixture-card-${f.id_partido}`;
    card.setAttribute("onclick", `abrirRadiografiaForense('${f.id_partido}')`);

    const localEscudo = f.local_escudo_url ? `<img src="${f.local_escudo_url}" class="match-crest-mini">` : "";
    const visEscudo = f.visitante_escudo_url ? `<img src="${f.visitante_escudo_url}" class="match-crest-mini">` : "";

    // Contenido del centro: reemplaza el 'vs' flotante por el resultado o estado discreto
    let centroHtml = "";
    if (estado === "FINALIZADO") {
        const marcador = f.marcador_actual || "Final";
        centroHtml = `
            <span class="match-time-muted">${f.horario}</span>
            <span class="score-center-badge">${marcador}</span>
        `;
    } else if (estado === "REPROGRAMADO") {
        centroHtml = `
            <span class="match-time-muted">${f.horario}</span>
            <span class="status-center-subtle">⏳ Reprogramado</span>
        `;
    } else {
        // PROGRAMADO (JORNADA ACTIVA J10)
        // [LN-QBE-098] Paridad de precisión con la Radiografía Forense y la tarjeta de boleto:
        // la distribución soberana se exhibe con UN decimal, idéntica en las tres pantallas.
        const pL = f.p_local ? (f.p_local * 100).toFixed(1) + "%" : "—";
        const pE = f.p_empate ? (f.p_empate * 100).toFixed(1) + "%" : "—";
        const pV = f.p_visitante ? (f.p_visitante * 100).toFixed(1) + "%" : "—";

        const wL = f.p_local ? (f.p_local * 100).toFixed(1) : 33.3;
        const wE = f.p_empate ? (f.p_empate * 100).toFixed(1) : 33.3;
        const wV = f.p_visitante ? (f.p_visitante * 100).toFixed(1) : 33.4;

        // [DES-QBE-039-B] Micro-Malla de Consenso y Diferencial Alineada
        let consensoHtml = '';
        if (f.consenso_mercado && f.consenso_mercado.p_L_mercado > 0) {
            const qL = (f.consenso_mercado.p_L_mercado * 100).toFixed(0);
            const qE = (f.consenso_mercado.p_E_mercado * 100).toFixed(0);
            const qV = (f.consenso_mercado.p_V_mercado * 100).toFixed(0);

            const dL = (f.consenso_mercado.delta_L * 100);
            const dE = (f.consenso_mercado.delta_E * 100);
            const dV = (f.consenso_mercado.delta_V * 100);

            const fmtDiff = (v) => (v >= 0 ? `+${v.toFixed(1)}%` : `${v.toFixed(1)}%`);

            consensoHtml = `
                <div class="market-benchmark-grid" title="Comparativo: Consenso de Mercado vs Modelo Q-BE">
                    <!-- Fila 1: Promedio de Mercado sin comisión -->
                    <span class="mkt-cell-lbl">Mkt</span>
                    <span class="mkt-cell-val">${qL}%</span>
                    <span class="mkt-cell-val">${qE}%</span>
                    <span class="mkt-cell-val">${qV}%</span>

                    <!-- Fila 2: Diferencial aritmético con signo -->
                    <span class="mkt-cell-lbl">Δ</span>
                    <span class="mkt-cell-diff">${fmtDiff(dL)}</span>
                    <span class="mkt-cell-diff">${fmtDiff(dE)}</span>
                    <span class="mkt-cell-diff">${fmtDiff(dV)}</span>
                </div>
            `;
        }


        centroHtml = `
            <span class="match-time-muted">${f.horario}</span>
            <div class="distribution-center-badge" title="Probabilidad Soberana Q-BE: Local · Empate · Visita">
                <span style="color:#00E676; font-weight:800;">${pL}</span>
                <span style="color:#64748B; margin: 0 3px;">·</span>
                <span style="color:#94A3B8; font-weight:700;">${pE}</span>
                <span style="color:#64748B; margin: 0 3px;">·</span>
                <span style="color:#EF4444; font-weight:800;">${pV}</span>
            </div>
            <div class="prob-strip-mini prob-strip" style="display:flex; width:75px; height:4px; border-radius:2px; overflow:hidden; margin-top:3px;">
                <div style="background:#00E676; width:${wL}%;"></div>
                <div style="background:#64748B; width:${wE}%;"></div>
                <div style="background:#EF4444; width:${wV}%;"></div>
            </div>
            ${consensoHtml}
        `;

    }

    card.innerHTML = `
        <div class="match-grid-3col">
            <div class="team-home-cell">
                <span>${f.local}</span>
                ${localEscudo}
            </div>
            <div class="match-center-cell">
                ${centroHtml}
            </div>
            <div class="team-away-cell">
                ${visEscudo}
                <span>${f.visitante}</span>
            </div>
        </div>
    `;

    container.appendChild(card);
}


// [DES-QBE-016-C] Clicabilidad Total de Tarjeta (Card-Level Clickability)
function habilitarClicTarjetaCompleta() {
    document.querySelectorAll('.fixture-card').forEach(card => {
        // Evitar doble registro de listeners
        if (card.dataset.listenerBound) return;
        card.dataset.listenerBound = "true";

        card.addEventListener("click", (e) => {
            const estado = card.dataset.estado;

            // Bloquear interacción ÚNICAMENTE si está finalizado o no tiene cuotas disponibles
            if (card.classList.contains("fixture-disabled") || estado === "FINALIZADO") {
                return;
            }

            const checkbox = card.querySelector("input[type='checkbox']");
            if (!checkbox || checkbox.disabled) return;

            // Clic en área de tarjeta (no directamente en el checkbox): alternar manualmente
            if (e.target !== checkbox) {
                checkbox.checked = !checkbox.checked;
            }

            // Actualizar estilo visual de selección
            const matchId = card.dataset.matchId;
            if (checkbox.checked) {
                card.classList.add("selected");
                card.style.borderColor = "#38BDF8";
                if (matchId && !selectedMatchIds.includes(matchId)) {
                    selectedMatchIds.push(matchId);
                }
            } else {
                card.classList.remove("selected");
                card.style.borderColor = "#334155";
                if (matchId) {
                    selectedMatchIds = selectedMatchIds.filter(id => id !== matchId);
                }
            }

            // Actualizar contador (sin disparar change para evitar doble-toggle)
            actualizarContadorSeleccionados();
        });
    });
}

// [DES-QBE-016] Selector único: feedback visual por borde cian (manejador de evento nativo)
function toggleFixtureCheckbox(checkbox, matchId) {
    const card = document.getElementById(`fixture-card-${matchId}`);
    if (checkbox.checked) {
        if (!selectedMatchIds.includes(matchId)) selectedMatchIds.push(matchId);
        if (card) {
            card.classList.add("selected");
            card.style.borderColor = "#38BDF8";
            card.style.backgroundColor = "rgba(56, 189, 248, 0.05)";
        }
    } else {
        selectedMatchIds = selectedMatchIds.filter(id => id !== matchId);
        if (card) {
            card.classList.remove("selected");
            card.style.borderColor = "#334155";
            card.style.backgroundColor = "rgba(0,230,118,0.04)";
        }
    }
    actualizarContadorSeleccionados();
}

function actualizarContadorSeleccionados() {
    const lbl = document.getElementById("lbl-partidos-seleccionados");
    // Contar exclusivamente checkboxes marcados que NO estén deshabilitados
    const checkboxesActivos = document.querySelectorAll(".fixture-card:not(.fixture-disabled) input[type='checkbox']:checked");
    selectedMatchIds = Array.from(checkboxesActivos).map(cb => cb.value);

    if (lbl) {
        lbl.textContent = `${selectedMatchIds.length} partido${selectedMatchIds.length !== 1 ? 's' : ''} seleccionado${selectedMatchIds.length !== 1 ? 's' : ''}`;
    }
}

let abortControllerDespacho = null;

function mostrarHUDProcesamiento() {
    const modal = document.getElementById("modal-hud-procesamiento");
    if (modal) modal.style.display = "flex";
    actualizarProgresoHUD(1, 15);
}

function ocultarHUDProcesamiento() {
    const modal = document.getElementById("modal-hud-procesamiento");
    if (modal) modal.style.display = "none";
}

function cancelarDespachoPortafolio() {
    if (abortControllerDespacho) {
        abortControllerDespacho.abort();
    }
    ocultarHUDProcesamiento();
}
window.cancelarDespachoPortafolio = cancelarDespachoPortafolio;

function actualizarProgresoHUD(paso, porcentaje) {
    const fill = document.getElementById("hud-barra-fill");
    if (fill) fill.style.width = `${porcentaje}%`;

    for (let i = 1; i <= 6; i++) {
        const el = document.getElementById(`hud-p${i}`);
        if (!el) continue;
        if (i < paso) {
            el.style.color = "#00E676";
            el.innerHTML = el.innerHTML.replace("⏳", "✅");
        } else if (i === paso) {
            el.style.color = "#38BDF8";
            el.innerHTML = el.innerHTML.replace("✅", "⏳");
        } else {
            el.style.color = "#64748B";
        }
    }
}

// [DICTAMEN DIRECTOR 2026-10-11 / UI-REFINEMENT-5-POINTS] Defaults soberanos de cartera del
// frontend: el DTO de backend (src/models/web_schemas.py) permanece INTACTO — cero mutación de
// contrato. La UI SIEMPRE envía los valores explícitos en el payload JSON:
// Bankroll = $100.00 MXN · Γ (Concentración de Masa) = 70% (0.70).
const DEFAULTS_CARTERA = Object.freeze({ bankroll: 100.0, gamma: 0.70 });

// [ARCH-1.4.53 / LN-QBE-115] Defaults y dominio de la ventanilla para los parámetros gobernantes
// del laboratorio de rentabilidad. `CERTEZA_PCT_DEFAULT` replica el `value="80"` del slider
// `#slider-risk-certainty` (PORCENTAJE, no fracción) y `MODOS_COBERTURA_VALIDOS` es el dominio
// legislado del tríptico δ ([ARCH-1.4.37]). Cero lógica financiera: sólo guardas de transporte.
const CERTEZA_PCT_DEFAULT = 80.0;
const MODOS_COBERTURA_VALIDOS = Object.freeze(["DEF", "BAL", "AGR"]);

async function ejecutarDespachoPortafolio() {
    const bankrollInput = document.getElementById('input-bankroll') || document.getElementById('bankroll-input');
    const bankrollParsed = bankrollInput ? parseFloat(bankrollInput.value) : NaN;
    const bankroll = Number.isFinite(bankrollParsed) ? bankrollParsed : DEFAULTS_CARTERA.bankroll;

    const operatorSelect = document.getElementById('casino-operator-select');
    const operador = operatorSelect ? operatorSelect.value : "caliente";
    currentCasinoOperador = operador;

    const certaintySlider = document.getElementById('slider-risk-certainty');
    const certeza = certaintySlider ? parseFloat(certaintySlider.value) / 100.0 : 0.80;

    // [ARCH-1.4.30] Concentración de Masa Γ de Capa 0 seleccionada en la barra de configuración
    // (67% | 70% | 75%). Default soberano sellado: 70% (0.70) cuando ningún radio queda marcado.
    const gammaSeleccionada = parseFloat(document.querySelector('input[name="opcion_gamma"]:checked')?.value || String(DEFAULTS_CARTERA.gamma));

    const leagueId = (currentLiveBoard && currentLiveBoard.league_id) ? currentLiveBoard.league_id : 262;

    mostrarHUDProcesamiento();
    abortControllerDespacho = new AbortController();

    try {
        // Simulación visual reactiva de progresión mientras responde el worker
        setTimeout(() => actualizarProgresoHUD(2, 35), 300);
        setTimeout(() => actualizarProgresoHUD(3, 55), 600);
        setTimeout(() => actualizarProgresoHUD(4, 75), 900);
        setTimeout(() => actualizarProgresoHUD(5, 90), 1200);

        const resp = await fetch('/api/markets/sportsbook/portfolio/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            signal: abortControllerDespacho.signal,
            body: JSON.stringify({
                league_id: leagueId,
                selected_match_ids: [],
                bankroll: bankroll,
                target_certeza: certeza,
                operador: operador,
                gamma_slider: gammaSeleccionada,
                // [ARCH-1.4.37 / LN-QBE-077-B / ARCH-1.4.12-C] Tríptico de Cobertura: la ventanilla
                // declara el modo de partición δ del capital. `DEF` (V=0) sigue siendo el default del
                // contrato de petición sellado; el tríptico ARRANCA en `BAL` (default legislado de la
                // Mesa de Apuestas, [ARCH-1.4.12-C]); `BAL` (r_bal = 50% de δ*) y `AGR` (δ*) activan la
                // ley general del Dutching Dinámico.
                modo_cobertura: state.modo_cobertura,
                // [ARCH-1.4.35 / CONMUTADOR DE SLATES] El anclaje de jornada viaja SÓLO con el
                // candado abierto (🔓). Con el candado cerrado (🔒) se emite `null` y el backend
                // resuelve la jornada activa dinámicamente ([ARCH-1.6.15]). Doble seguro: la UI
                // jamás congela la mesa por accidente.
                jornada: esModoBacktestingJornada() ? _jornadaSeleccionadaConmutador() : null
            })
        });

        actualizarProgresoHUD(6, 100);
        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.detail || "Error en cálculo de portafolio");
        }

        const data = await resp.json();

        setTimeout(() => {
            ocultarHUDProcesamiento();
            switchView("tab-portfolio");
            renderizarResultadosPortafolio(data);

            // Enlazar botón PDF export en la vista de cartera
            const pdfBtn = document.getElementById("export-pdf-btn");
            if (pdfBtn && data.portfolio_id) {
                pdfBtn.onclick = () => window.open(`/api/portfolio/${data.portfolio_id}/pdf`, '_blank');
            }
        }, 400);

    } catch (e) {
        ocultarHUDProcesamiento();
        if (e.name !== 'AbortError') {
            alert(`❌ Error calculando portafolio: ${e.message}`);
        }
    }
}
window.ejecutarDespachoPortafolio = ejecutarDespachoPortafolio;
window.ejecutarDespachoMesaApuestas = ejecutarDespachoPortafolio;

let currentPortfolioData = null;
let currentCasinoOperador = "caliente";
// [ARCH-1.4.37 / LN-QBE-077-B / ARCH-1.4.12-C] Estado soberano del Tríptico de Cobertura (δ):
// `DEF` es el contrato sellado V=0 (paridad bit a bit con el Dutching clásico); `BAL`/`AGR` activan
// la ley general de partición. DEFAULT LEGISLADO = `BAL` (Balanceado +15%), modo de cobertura por
// omisión de la Mesa de Apuestas ([ARCH-1.4.12-C]). Sólo la VENTANILLA declara el modo; el motor
// jamás lo infiere.
let state = { modo_cobertura: "BAL" };

// ─── [DES-QBE-055 / ARCH-1.5.10-B] Rótulo de Casa Patrocinadora por Boleto ─────
// El emblema viaja desde la bóveda LOCAL de activos (`/static/img/bookmakers/{slug}.png`,
// anclada por `scripts/utilidades/sincronizar_boveda_activos.py`). Cero hotlinking a
// servidores de terceros ([ARCH-1.5.10-B]). Si el plan no expone operador (modalidad
// mono-casa heredada), se conserva el rótulo genérico de ventanilla: degradación
// declarada, jamás una casa inventada ([GOVERNANCE-01]).
// [DES-QBE-055] Pie de boleto split sobrio: rótulo + emblema de la bóveda local, SIN el nombre
// textual del casino (deroga el sufijo `{NOMBRE_CASINO}` de [DES-QBE-053]). El operador se
// identifica por el logo y por su tooltip fiduciario; jamás se duplica el texto en el boleto.
function _rotuloCasaApostar(slugOperador) {
    const etiqueta = `<span class="ticket-action-label" style="font-size:7pt; color:#94A3B8; font-weight:700;">APOSTAR EN:</span>`;
    if (!slugOperador) return `${etiqueta} <span style="font-size:7pt; color:#94A3B8;">VENTANILLA</span>`;
    const slug = String(slugOperador).toLowerCase();
    // Bóveda local ([ARCH-1.5.10-B]): PNG oficial si está anclado; si no, respaldo SVG local;
    // en última instancia el emblema se oculta (degradación declarada, cero hotlink).
    const onerror = "if(!this.dataset.fb){this.dataset.fb='1';this.src='/static/img/bookmakers/" +
        slug + ".svg';}else{this.style.display='none';}";
    return `${etiqueta} <img src="/static/img/bookmakers/${slug}.png" class="bookmaker-logo-inline" alt="${slug}" title="Operador: ${slug.toUpperCase()}" style="height:18px; vertical-align:middle; margin-left:4px;" onerror="${onerror}">`;
}

// ─── [ARCH-1.4.15] Disponibilidad Dinámica de Operadores en Ventanilla ───────
// El backend declara la captura fáctica por casa. Una casa con `disponible: false` no
// puede simular cuotas ajenas: se inhabilita y se rotula explícitamente.
function _aplicarDisponibilidadOperadores(mapaOperadores) {
    const sel = document.getElementById("casino-operator-select");
    if (!sel || !mapaOperadores || Object.keys(mapaOperadores).length === 0) return;

    const etiquetaBase = {};
    Array.from(sel.options).forEach(op => {
        etiquetaBase[op.value] = (op.textContent || "").replace(/\s*\(Sin cuotas disponibles\)\s*$/, "").trim();
    });

    Array.from(sel.options).forEach(op => {
        const info = mapaOperadores[op.value];
        if (!info || info.disponible === undefined) return;
        const disponible = info.disponible !== false;
        op.disabled = !disponible;
        op.textContent = disponible ? etiquetaBase[op.value] : `${etiquetaBase[op.value]} (Sin cuotas disponibles)`;
    });

    const actual = sel.options[sel.selectedIndex];
    if (actual && actual.disabled) {
        const primera = Array.from(sel.options).find(op => !op.disabled);
        if (primera) sel.value = primera.value;
    }
}

// ─── [ARCH-1.4.35 / CONMUTADOR DE SLATES] Doble Seguro del Backtesting Fiduciario ────────
// CANDADO 🔒 = ventanilla VIVA: el backend resuelve la jornada dinámicamente ([ARCH-1.6.15]) y
//   el payload de despacho NO ancla jornada alguna (cero congelamiento accidental de la mesa).
// CANDADO 🔓 = BACKTESTING: el payload ancla la jornada elegida y el backend liquida cada orden
//   contra el marcador REAL de la bóveda 3NF (Real vs. Predicho, [LN-QBE-025-B]).
// [GOVERNANCE-01] El cliente sólo EXHIBE hechos de la bóveda: cero fechas, marcadores, cuotas o
// PnL inventados; toda cifra llega hidratada por el backend.
let modoBacktestingJornada = false;

// [DES-QBE-069 / LN-QBE-114] Centinela del selector: con el candado abierto se ofrece el rango
// COMPLETO de la temporada (derivado de las jornadas REALES de la bóveda, jamás quemado en HTML).
const VALOR_TEMPORADA = 'temporada';

function esModoBacktestingJornada() {
    return modoBacktestingJornada === true;
}

function _jornadaSeleccionadaConmutador() {
    const sel = document.getElementById('select-jornada');
    if (!sel) return null;
    const valor = parseInt(sel.value, 10);
    return Number.isFinite(valor) ? valor : null;
}

// [DOBLE SEGURO] Al re-bloquear se restituye la jornada ACTIVA declarada por la bóveda. La
// jornada activa es un HECHO ([ARCH-1.6.15]): se lee del contrato del Live Board (`jornada_activa`)
// o del cache hidratado por el conmutador. Sin declaración de bóveda se conserva la primera opción
// legislada: el cliente JAMÁS inventa una jornada ([GOVERNANCE-01]).
let _jornadaActivaBoveda = null;

function _jornadaActivaDelConmutador() {
    const sel = document.getElementById('select-jornada');
    if (!sel) return null;
    const valores = Array.from(sel.options)
        .map(op => parseInt(op.value, 10))
        .filter(Number.isFinite);
    if (!valores.length) return null;
    const declarada = (currentLiveBoard && currentLiveBoard.jornada_activa !== undefined)
        ? Number(currentLiveBoard.jornada_activa)
        : Number(_jornadaActivaBoveda);
    if (Number.isFinite(declarada) && valores.includes(declarada)) return String(declarada);
    return String(valores[0]);
}

function _pintarEstadoConmutadorJornada() {
    const btn = document.getElementById('btn-lock-jornada');
    const sel = document.getElementById('select-jornada');
    const tarjeta = document.getElementById('configuracion-cartera');
    const banner = document.getElementById('banner-backtesting-jornada');
    const strip = document.getElementById('slate-cartelera-jornada');
    if (!btn || !sel) return;

    if (esModoBacktestingJornada()) {
        btn.textContent = '🔓';
        btn.classList.remove('locked');
        btn.classList.add('unlocked');
        btn.style.color = '#38BDF8';
        btn.title = 'Click para bloquear y volver a la jornada activa';
        sel.disabled = false;
        sel.style.borderColor = '#F59E0B';
        sel.style.color = '#F8FAFC';
        if (tarjeta) tarjeta.style.border = '1px solid rgba(245, 158, 11, 0.45)';
        if (banner) banner.style.display = 'block';
        // [DES-QBE-069] Modo Laboratorio: centinela de temporada + filtros fiduciarios + botón mutado.
        _sincronizarOpcionTemporada();
        const filtrosLab = document.getElementById('filtros-backtest-container');
        if (filtrosLab) filtrosLab.style.display = 'flex';
        const btnCalc = document.getElementById('btn-calcular-cartera');
        if (btnCalc) {
            btnCalc.textContent = ' 📈 Simular Rentabilidad ';
            btnCalc.title = 'Simulación retrospectiva sobre el motor sellado [LN-QBE-107] / [LN-QBE-114]';
        }
        _actualizarAlcanceSimulacion();
    } else {
        btn.textContent = '🔒';
        btn.classList.remove('unlocked');
        btn.classList.add('locked');
        btn.style.color = '#F59E0B';
        btn.title = 'Click para desbloquear modo simulación histórica';
        sel.disabled = true;
        sel.style.borderColor = '#475569';
        sel.style.color = '#94A3B8';
        if (tarjeta) tarjeta.style.border = '';
        if (banner) banner.style.display = 'none';
        if (strip) { strip.style.display = 'none'; strip.innerHTML = ''; }
        // [DES-QBE-069] Candado cerrado: se retira el centinela y se restituye la ventanilla viva.
        _sincronizarOpcionTemporada();
        const filtrosLab = document.getElementById('filtros-backtest-container');
        if (filtrosLab) filtrosLab.style.display = 'none';
        const btnCalc = document.getElementById('btn-calcular-cartera');
        if (btnCalc) {
            btnCalc.textContent = ' ⚡ Calcular Cartera ';
            btnCalc.title = '';
        }
    }
}

async function conmutarCandadoJornada() {
    // [DOBLE SEGURO / GOVERNANCE-01] Sin jornadas declaradas por la bóveda el candado NO se abre:
    // el modo Backtesting exige anclar una jornada REAL y el cliente JAMÁS inventa un número. La
    // degradación es declarada (tooltip) y la ventanilla viva permanece operativa.
    if (!esModoBacktestingJornada() && _jornadaSeleccionadaConmutador() === null) {
        const btnSinSlate = document.getElementById('btn-lock-jornada');
        if (btnSinSlate) btnSinSlate.title = 'La bóveda 3NF no declara jornadas: backtesting no disponible';
        console.warn('Conmutador de jornadas: la bóveda no declaró slate alguno; el candado permanece cerrado.');
        return;
    }
    modoBacktestingJornada = !esModoBacktestingJornada();
    const sel = document.getElementById('select-jornada');
    if (!esModoBacktestingJornada() && sel) {
        // [DOBLE SEGURO] Candado cerrado ⇒ SIEMPRE la jornada activa (jamás una histórica).
        const activa = _jornadaActivaDelConmutador();
        if (activa !== null) sel.value = activa;
    }
    _pintarEstadoConmutadorJornada();
    if (esModoBacktestingJornada()) {
        await cargarCarteleraJornada(_jornadaSeleccionadaConmutador());
    } else {
        // [DOBLE SEGURO] Al re-bloquear NO se dispara sincronización ni navegación alguna: el
        // candado sólo restituye la jornada activa en el selector y retira el detalle histórico
        // (la cartelera viva del Live Board permanece intacta e independiente).
        _restituirDetalleBacktesting();
    }
}

// [ARCH-1.4.35] Cartelera del slate CONGELADO: consume el endpoint del conmutador
// (`GET /api/markets/sportsbook/live-board?jornada=N`) y exhibe únicamente lo que la bóveda
// declara (cuotas capturadas y marcadores reales de la 3NF). Cero cifras calculadas en cliente.
async function cargarCarteleraJornada(jornada) {
    const numJornada = parseInt(jornada, 10);
    const detalle = document.getElementById('txt-detalle-backtesting');
    const strip = document.getElementById('slate-cartelera-jornada');
    if (!Number.isFinite(numJornada)) {
        if (detalle) detalle.textContent = 'Selecciona una jornada válida para simular.';
        return;
    }
    const leagueId = (currentLiveBoard && currentLiveBoard.league_id) ? currentLiveBoard.league_id : 262;
    const selOp = document.getElementById('casino-operator-select');
    const operador = selOp ? selOp.value : 'caliente';
    if (detalle) detalle.textContent = `Consultando la cartelera congelada de la Jornada ${numJornada}…`;

    try {
        const resp = await fetch(`/api/markets/sportsbook/live-board?jornada=${numJornada}&league_id=${leagueId}&bookmaker=${encodeURIComponent(operador)}`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        renderizarSlateCartelera(await resp.json());
    } catch (e) {
        if (detalle) detalle.textContent = `No fue posible cargar la cartelera de la Jornada ${numJornada}: ${e.message}`;
        if (strip) { strip.innerHTML = ''; strip.style.display = 'none'; }
    }
}

function renderizarSlateCartelera(data) {
    const strip = document.getElementById('slate-cartelera-jornada');
    const detalle = document.getElementById('txt-detalle-backtesting');
    const partidos = (data && data.partidos) || [];
    const conCuotas = partidos.filter(p => p.con_cuotas).length;
    const conMarcador = partidos.filter(p => p.marcador_real).length;

    // [ARCH-1.4.35] El conmutador se hidrata con las jornadas REALES de la bóveda ([GOVERNANCE-01]).
    _hidratarOpcionesJornada(data.jornadas, data.jornada_activa);

    if (detalle) {
        detalle.innerHTML = `Jornada ${data.jornada} congelada · <strong>${conCuotas}/${partidos.length}</strong> partidos con cuotas reales capturadas · ` +
            `<strong>${conMarcador}/${partidos.length}</strong> con marcador real en la bóveda 3NF · Casa: <strong>${String(data.bookmaker || '').toUpperCase()}</strong>` +
            (data.jornada_activa ? ` · Jornada activa dinámica: ${data.jornada_activa}` : '');
    }
    if (!strip) return;

    if (!partidos.length) {
        strip.innerHTML = `<div style="font-size:7.8pt; color:#F59E0B;">La bóveda no contiene captura para la Jornada ${data.jornada}: ${data.motivo || 'sin cartelera registrada'}.</div>`;
        strip.style.display = 'block';
        return;
    }

    const filas = partidos.map(p => {
        const cuotasHtml = p.con_cuotas
            ? `<span style="font-family:monospace; color:#F8FAFC;">${Number(p.momio_l).toFixed(2)} | ${Number(p.momio_e).toFixed(2)} | ${Number(p.momio_v).toFixed(2)}</span>`
            : `<span style="color:#64748B;">Sin cuotas capturadas</span>`;
        const marcadorHtml = p.marcador_real
            ? `<span style="color:#F59E0B; font-weight:800;">${p.marcador_real}</span>`
            : `<span style="color:#64748B;">—</span>`;
        const evHtml = p.es_viable_ev
            ? `<span style="color:#00E676; font-weight:800;">+EV</span>`
            : `<span style="color:#64748B;">—</span>`;
        return `<tr>
            <td style="white-space:nowrap; color:#e2e8f0;">${p.local} vs ${p.visitante}</td>
            <td style="text-align:center;">${cuotasHtml}</td>
            <td style="text-align:center;">${marcadorHtml}</td>
            <td style="text-align:center; color:#94A3B8;">${p.estado || '—'}</td>
            <td style="text-align:center;">${evHtml}</td>
        </tr>`;
    }).join('');

    strip.innerHTML = `
        <table class="fintech-table" style="margin:0; font-size:7.8pt;">
            <thead>
                <tr>
                    <th>PARTIDO (SLATE CONGELADO)</th>
                    <th style="text-align:center;">CUOTAS L | E | V</th>
                    <th style="text-align:center;">MARCADOR REAL (3NF)</th>
                    <th style="text-align:center;">ESTADO</th>
                    <th style="text-align:center;">+EV</th>
                </tr>
            </thead>
            <tbody>${filas}</tbody>
        </table>
    `;
    strip.style.display = 'block';
}

// [DOBLE SEGURO] Reposo del banner: sin jornada anclada no se exhibe cifra alguna de simulación.
function _restituirDetalleBacktesting() {
    const detalle = document.getElementById('txt-detalle-backtesting');
    if (detalle) detalle.textContent = 'Selecciona una jornada histórica y pulsa ⚡ Calcular Cartera.';
}

// ─── [ARCH-1.4.35 / CONMUTADOR DE SLATES] Hidratación fáctica de la lista de jornadas ────
// `data.jornadas` es el resumen que emite la bóveda 3NF en UNA sola lectura (`GET /api/markets/
// sportsbook/live-board`): jornada, partidos capturados, partidos con cuotas reales capturadas,
// conclusión y marcadores reales disponibles. Cero jornadas quemadas en el HTML ([GOVERNANCE-01]).
function _hidratarOpcionesJornada(jornadas, jornadaActiva) {
    const sel = document.getElementById('select-jornada');
    if (!sel || !Array.isArray(jornadas) || !jornadas.length) return;

    const previa = sel.value;
    const activa = Number(jornadaActiva);
    if (Number.isFinite(activa)) _jornadaActivaBoveda = activa;

    const opciones = jornadas.map(function (j) {
        const n = parseInt(j.jornada, 10);
        if (!Number.isFinite(n)) return '';
        const esActiva = Number.isFinite(activa) && n === activa;
        const etiqueta = esActiva ? `Jornada ${n} (Activa)` : `Jornada ${n} (Histórica)`;
        const hechos = [`${j.con_marcador_real || 0}/${j.total_partidos || 0} res. reales`];
        hechos.push(j.con_cuotas ? `${j.con_cuotas} con cuotas` : 'sin cuotas');
        if (!esActiva && (j.con_marcador_real || 0) > 0) hechos.push('⚡ backtesting viable');
        return `<option value="${n}">${etiqueta} · ${hechos.join(' · ')}</option>`;
    }).filter(Boolean);
    if (!opciones.length) return;

    sel.innerHTML = opciones.join('');
    // [DOBLE SEGURO] Se conserva la jornada elegida si la bóveda todavía la declara; si no, la activa.
    const disponibles = Array.from(sel.options).map(function (op) { return op.value; });
    if (disponibles.includes(previa)) sel.value = previa;
    else if (Number.isFinite(activa) && disponibles.includes(String(activa))) sel.value = String(activa);
    // [DES-QBE-069] La hidratación REESCRIBE las opciones: se re-inyecta el centinela de temporada
    // si el laboratorio sigue abierto y se respeta la selección previa del rango completo.
    _sincronizarOpcionTemporada();
    if (previa === VALOR_TEMPORADA && esModoBacktestingJornada()) sel.value = VALOR_TEMPORADA;
    _actualizarAlcanceSimulacion();
}

// [ARCH-1.4.35] Lectura inicial (una sola vez, al arrancar la SPA): la lista de jornadas del
// conmutador es un HECHO de la bóveda. Si la bóveda no responde se conserva la lista legislada y
// el candado sigue operativo: degradación declarada, cero jornadas inventadas ([GOVERNANCE-01]).
async function hidratarConmutadorJornadas() {
    const leagueId = (currentLiveBoard && currentLiveBoard.league_id) ? currentLiveBoard.league_id : 262;
    try {
        const resp = await fetch(`/api/markets/sportsbook/live-board?league_id=${leagueId}&bookmaker=caliente`);
        if (!resp.ok) return;
        const data = await resp.json();
        _hidratarOpcionesJornada(data.jornadas, data.jornada_activa);
    } catch (e) {
        console.warn('Conmutador de jornadas: la bóveda no respondió al arranque.', e);
    }
}

// ─── [LN-QBE-025-B / ARCH-1.4.35] Banner de Preservación de Capital (Cartera Vacía) ─────
// Publica en la vista de Cartera el estado fiduciario `PRESERVACION_EFECTIVO` (cero activos
// +EV). IDEMPOTENTE: reutiliza el nodo `#banner-preservacion-capital`, por lo que despachos
// sucesivos jamás duplican el aviso. CERO `alert()` para este caso: la cartera vacía es un
// estado LEGÍTIMO del contrato, no una excepción de usuario ([GOVERNANCE-01]). El texto se
// toma del contrato emitido (`control.mensaje_fiduciario`); si no viaja, se declara el motivo
// canónico del triaje. Cero cifras inventadas: el riesgo se publica como $0.00 MXN.
function _renderizarBannerPreservacionCapital(esCarteraVacia, control) {
    const contenedor = document.getElementById('tab-portfolio');
    if (!contenedor) return;

    let banner = document.getElementById('banner-preservacion-capital');
    if (!esCarteraVacia) {
        if (banner) banner.remove();
        return;
    }

    const mensaje = (control && control.mensaje_fiduciario)
        || "Ningún partido superó el triaje fiduciario (+EV). Capital 100% preservado en efectivo.";

    if (!banner) {
        banner = document.createElement('div');
        banner.id = 'banner-preservacion-capital';
        contenedor.insertBefore(banner, contenedor.firstChild);
    }

    banner.style.cssText = "border:1px solid var(--accent-amber, #F59E0B);"
        + " background:rgba(245,158,11,0.10); color:#FBBF24; border-radius:10px;"
        + " padding:10px 14px; margin:0 0 14px 0; font-size:8.4pt; font-weight:800;"
        + " display:flex; align-items:center; gap:10px;";

    banner.innerHTML = `
        <span style="font-size:12pt;">🛡️</span>
        <span style="flex:1;">
            <span style="display:block; letter-spacing:0.06em;">CAPITAL 100% PROTEGIDO · PRESERVACIÓN EN EFECTIVO</span>
            <span style="display:block; font-weight:400; color:var(--text-muted, #94A3B8); margin-top:2px;">${mensaje}</span>
        </span>
        <span style="font-family:monospace; font-weight:900; color:#FBBF24; white-space:nowrap;">$0.00 MXN EN RIESGO</span>
    `;
}

// ─── [ARCH-1.4.35 / LN-QBE-025-B] Liquidación REAL del Backtesting (Real vs. Predicho) ────
// Agregado del contrato `data.backtesting` que emite el controlador (`POST
// /api/markets/sportsbook/portfolio/generate` con la jornada anclada). IDEMPOTENTE: reutiliza el
// nodo `#banner-liquidacion-backtesting`. CERO aritmética de capital en el cliente: el PnL neto
// real, los denominadores y los marcadores finales llegan CERTIFICADOS por el backend, que a su
// vez delega la ley a `liquidar_orden_post_evento` ([DIRGEN-STRICT], cero reinvención).
function _renderizarLiquidacionBacktesting(data) {
    const contenedor = document.getElementById('tab-portfolio');
    if (!contenedor) return;

    const bt = data && data.backtesting;
    let banner = document.getElementById('banner-liquidacion-backtesting');
    if (!bt || bt.activo !== true) {
        // Ventanilla VIVA: sin jornada anclada no existe liquidación que exhibir.
        if (banner) banner.remove();
        return;
    }

    const pnl = Number(bt.pnl_neto_total_mxn || 0.0);
    const colorPnl = pnl > 0 ? '#00E676' : (pnl < 0 ? '#f87171' : '#FBBF24');
    const signo = pnl < 0 ? '−' : '+';

    if (!banner) {
        banner = document.createElement('div');
        banner.id = 'banner-liquidacion-backtesting';
        contenedor.insertBefore(banner, contenedor.firstChild);
    }

    banner.style.cssText = "border:1px solid rgba(56,189,248,0.45);"
        + " background:rgba(56,189,248,0.08); color:#38BDF8; border-radius:10px;"
        + " padding:10px 14px; margin:0 0 14px 0; font-size:8.2pt; font-weight:800;";

    banner.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center; gap:10px; flex-wrap:wrap;">
            <span>🧪 LIQUIDACIÓN REAL · REAL vs. PREDICHO (Jornada ${bt.jornada} congelada)</span>
            <span style="font-family:monospace; font-weight:900; color:${colorPnl}; white-space:nowrap;">
                ${signo}$${Math.abs(pnl).toFixed(2)} MXN PnL NETO REAL
            </span>
        </div>
        <div style="display:flex; gap:14px; flex-wrap:wrap; margin-top:6px; font-weight:400; color:var(--text-muted,#94A3B8); font-size:7.6pt;">
            <span>Órdenes liquidadas: <strong style="color:#e2e8f0;">${bt.ordenes_liquidadas}/${bt.total_ordenes}</strong></span>
            <span>Sin marcador real en la bóveda: <strong style="color:#e2e8f0;">${bt.ordenes_sin_marcador_real}</strong></span>
            <span>Cobrados (ataque): <strong style="color:#00E676;">${bt.cobrados}</strong></span>
            <span>Tablas (V=0): <strong style="color:#38BDF8;">${bt.tablas_v0}</strong></span>
            <span>Cosechas δ (seguro): <strong style="color:#34D399;">${bt.cosechas_seguro_delta || 0}</strong></span>
            <span>Fallos: <strong style="color:#f87171;">${bt.fallos}</strong></span>
            <span>Capital liquidado: <strong style="color:#e2e8f0;">$${Number(bt.inversion_liquidada_mxn || 0).toFixed(2)} MXN</strong></span>
        </div>
    `;
}

// [ARCH-1.4.35] Celda de la columna LIQUIDACIÓN REAL (7ª) de `#tabla-resumen-asignacion`. En la
// ventanilla VIVA degrada a "—": sólo el oráculo 3NF dicta veredictos ([GOVERNANCE-01]).
function _celdaLiquidacionReal(ord) {
    const liq = ord && ord.liquidacion_real;
    if (!liq) return `<td style="text-align:center; color:#64748B;">—</td>`;

    const pnl = Number(liq.pnl_neto_mxn || 0.0);
    const color = pnl > 0 ? '#00E676' : (pnl < 0 ? '#f87171' : '#FBBF24');
    const etiqueta = String(liq.estado || '').replace(/_/g, ' ');
    return `<td style="text-align:center; font-size:7.6pt; line-height:1.3;">
        <span style="display:block; font-family:monospace; font-weight:900; color:#F59E0B;">${liq.marcador_final || '—'}</span>
        <span style="display:block; color:${color}; font-weight:800;">${pnl < 0 ? '−' : '+'}$${Math.abs(pnl).toFixed(2)} MXN</span>
        <span style="display:block; color:#94A3B8;">${etiqueta}</span>
    </td>`;
}

// [ARCH-1.4.35] Celda de cierre del `tfoot`: PnL real agregado de la jornada anclada.
function _celdaLiquidacionRealAgregada(data) {
    const bt = data && data.backtesting;
    if (!bt || bt.activo !== true) return `<td style="text-align:center; color:#64748B;">—</td>`;

    const pnl = Number(bt.pnl_neto_total_mxn || 0.0);
    const color = pnl > 0 ? '#00E676' : (pnl < 0 ? '#f87171' : '#FBBF24');
    return `<td style="text-align:center; font-family:monospace; color:${color};">
        ${pnl < 0 ? '−' : '+'}$${Math.abs(pnl).toFixed(2)} MXN
        <span style="display:block; font-size:6.8pt; font-weight:400; color:#94A3B8;">${bt.ordenes_liquidadas}/${bt.total_ordenes} liquidadas</span>
    </td>`;
}

// [ARCH-1.4.35 / Dictamen V-4] Sello FÁCTICO de liquidación DENTRO de la tarjeta de boleto: pinta el
// veredicto ya sellado por el backend (`ord.liquidacion_real`) sin aritmética nueva en el cliente.
// Sin liquidación (ventanilla VIVA) NO se emite sello alguno ([GOVERNANCE-01]).
function _badgeLiquidacionReal(ord) {
    const liq = ord && ord.liquidacion_real;
    if (!liq) return '';
    const base = 'padding:4px 8px; border-radius:6px; font-weight:800; font-size:7.4pt; white-space:nowrap;';
    const pnl = Number(liq.pnl_neto_mxn || 0.0);
    const estado = String(liq.estado || '');
    if (estado === 'COBRADO_ATAQUE') {
        return `<span class="badge-liquidacion-cobrado" style="background:#065F46; color:#34D399; border:1px solid #34D399; ${base}">🟢 COBRADO (+$${pnl.toFixed(2)} MXN)</span>`;
    }
    if (estado === 'COBRADO_SEGURO_DELTA') {
        // [ARCH-1.4.37 / LN-QBE-077-B] Cosecha Activa consumada en la cancha: el ROI exhibido es
        // el CERTIFICADO por el bloque `cobertura_dinamica` del motor (δ > 0). Cero aritmética
        // fiduciaria en el cliente ([GOVERNANCE-01] paridad estricta backend↔pantalla).
        const roiDelta = Number((ord && ord.cobertura_dinamica && ord.cobertura_dinamica.roi_empate_porcentaje) || 0);
        return `<span class="badge-liquidacion-seguro-delta" style="background:#065F46; color:#34D399; font-weight:bold; padding:4px 8px; border-radius:6px;">🟢 COBRADO_SEGURO_DELTA (+${roiDelta.toFixed(1)}%)</span>`;
    }
    if (estado === 'TABLAS_V0') {
        return `<span class="badge-liquidacion-tablas" style="background:#1E293B; color:#F59E0B; border:1px solid #F59E0B; ${base}">🛡️ TABLAS V=0 ($${pnl.toFixed(2)} MXN)</span>`;
    }
    if (estado === 'FALLO') {
        return `<span class="badge-liquidacion-fallo" style="background:#7F1D1D; color:#F87171; border:1px solid #F87171; ${base}">🔴 FALLO (−$${Math.abs(pnl).toFixed(2)} MXN)</span>`;
    }
    // Un veredicto no legislado se rotula VERBATIM sobre su marcador final: cero invención de estados.
    return `<span class="badge-liquidacion-otro" style="background:#1E293B; color:#94A3B8; border:1px solid #334155; ${base}">${estado || 'SIN VEREDICTO'}${liq.marcador_final ? ` · ${liq.marcador_final}` : ''}</span>`;
}

function renderizarResultadosPortafolio(data) {
    currentPortfolioData = data;
    // [DES-QBE-045] Consumo de las claves canónicas 3NF emitidas por markets.py (con fallback declarado).
    const orders = data.ordenes_ejecucion_partidos || data.ordenes || [];
    const control = data.control_portafolio || data.control || {};
    const balance = data.balance_global_portafolio || data.balance || {};
    const meta = data.metadata || {};

    // [ARCH-1.4.15] Contrato de disponibilidad: una casa sin cuotas capturadas en la jornada
    // activa se rotula `(Sin cuotas disponibles)` y queda inhabilitada en el selector.
    _aplicarDisponibilidadOperadores(data.operadores_disponibles || {});

    // [LN-QBE-025-B / ARCH-1.4.35] Axioma de la Cartera Vacía: cuando el contrato fiduciario
    // entrega $0.00 MXN en riesgo (cero activos +EV) la UI NO reporta error alguno —publica el
    // banner ámbar de PRESERVACIÓN y la vista degrada naturalmente (tabla sin filas). La
    // detección es fáctica y exclusiva de este contrato: sólo la cartera vacía emite
    // `capital_en_riesgo_mxn` (NaN en la cartera con posiciones ⇒ jamás un falso positivo).
    const capitalEnRiesgo = Number(
        balance.capital_en_riesgo_mxn ?? control.capital_en_riesgo_mxn ?? NaN
    );
    _renderizarBannerPreservacionCapital(capitalEnRiesgo === 0.0 && orders.length === 0, control);

    // [ARCH-1.4.35 / LN-QBE-025-B] Liquidación REAL del Backtesting (Real vs. Predicho): el
    // agregado del contrato sólo se exhibe cuando la jornada fue anclada (`data.backtesting`).
    _renderizarLiquidacionBacktesting(data);

    // 1. Encabezado Macro
    const elTorneo = document.getElementById("hdr-torneo-portfolio");
    if (elTorneo) elTorneo.textContent = meta.torneo || "Liga MX — Apertura 2026";
    const elFechas = document.getElementById("hdr-fechas-portfolio");
    if (elFechas) {
        // [UI-REFINEMENT-5-POINTS §4] Cero fecha quemada en la UI: si el contrato no entrega
        // `meta.fechas`, el rango se deriva de los fixtures del Live Board vigente; sin hecho
        // fechable se emite "—" ([GOVERNANCE-01]).
        const fechasPortfolio = meta.fechas
            || _rangoFechasJornada(currentLiveBoard ? currentLiveBoard.fixtures : null)
            || "—";
        elFechas.textContent = `${meta.jornada || "Jornada Activa"} · ${fechasPortfolio}`;
    }

    // 2. Macro KPIs Duales
    const invTotal = balance.capital_total_comprometido_mxn || 0.0;
    const gananciaEv = balance.ganancia_neta_esperada_jornada_mxn || 0.0;
    const roiGlobal = balance.roi_global_esperado_porcentaje || 0.0;
    const blindajePct = control.blindaje_global_preservacion_porcentaje || 99.9;
    const ruinaPct = control.probabilidad_ruina_total_porcentaje || 0.1;
    const kAprobados = control.total_partidos_core_aprobados || orders.length;
    // [ARCH-1.4.14 / DES-QBE-054] Denominador fáctico de cartelera: el KPI se lee K / 9 (jornada
    // oficial), nunca K / K. `total_partidos_jornada` es el campo legislado; se conserva el
    // fallback declarado a `total_partidos_escaneados` y al tamaño de la cartera entregada.
    const totalJornada = control.total_partidos_jornada || control.total_partidos_escaneados || orders.length;

    // Calcular suma de premios máximos netos (Ganancia Neta Potencial)
    let sumaPremios = 0;
    orders.forEach(o => {
        sumaPremios += (o.proyecciones?.ganancia_neta_principal_mxn || 0);
    });
    const roiPotencial = invTotal > 0 ? (sumaPremios / invTotal) * 100.0 : 0.0;

    const elInv = document.getElementById("kpi-inversion-total");
    if (elInv) elInv.textContent = `$${invTotal.toFixed(2)} MXN`;
    const elPctCaja = document.getElementById("kpi-pct-caja");
    if (elPctCaja) elPctCaja.textContent = `${((invTotal / (control.desglose_bankroll?.bankroll_total || 200)) * 100).toFixed(1)}% de la caja`;

    // Ganancia Potencial
    const elPot = document.getElementById("kpi-ganancia-potencial");
    if (elPot) elPot.textContent = `+$${sumaPremios.toFixed(2)} MXN`;
    const elRoiPot = document.getElementById("kpi-roi-potencial");
    if (elRoiPot) elRoiPot.textContent = `+${roiPotencial.toFixed(1)}% Ganando todas las apuestas principales (sin dobles premios)`;

    // Ganancia Esperada (EV)
    const elEv = document.getElementById("kpi-ganancia-esperada");
    if (elEv) elEv.textContent = `+$${gananciaEv.toFixed(2)} MXN`;
    const elRoi = document.getElementById("kpi-roi-global");
    if (elRoi) elRoi.textContent = `+${roiGlobal.toFixed(1)}% ROI Esperado (+EV estrategia a largo plazo)`;

    const elBlind = document.getElementById("kpi-blindaje-global");
    if (elBlind) elBlind.textContent = `${blindajePct.toFixed(2)}%`;
    const elRuina = document.getElementById("kpi-prob-ruina");
    if (elRuina) elRuina.textContent = `Probabilidad Ruina: ${ruinaPct.toFixed(4)}%  (de perder todas las apuestas)`;

    const elCore = document.getElementById("kpi-posiciones-core");
    if (elCore) elCore.textContent = `${kAprobados} / ${totalJornada}`;

    // 3. Banner de Certeza Tripartito (La Trinidad de Resiliencia) [DES-QBE-027]
    const trinidad = control.desglose_bankroll?.trinidad_resiliencia;
    const txtResumen = document.getElementById("txt-cascada-resumen");
    const pildorasCont = document.getElementById("pildoras-cascada");

    if (trinidad && pildorasCont) {
        const pleno = trinidad.pleno_exito;
        const tablas = trinidad.tablas_o_ganancia;
        const ruina = trinidad.ruina_total;

        if (txtResumen) {
            txtResumen.innerHTML = `<strong style="color:#38BDF8;">Certeza de Cartera:</strong> Tienes un <strong style="color:#00E676;">${tablas.probabilidad_pct}%</strong> de probabilidad de recuperar el 100% de tu dinero o salir con ganancia neta.`;
        }

        pildorasCont.innerHTML = `
            <span style="background: rgba(0, 230, 118, 0.15); color: #00E676; border: 1px solid #00E676; padding: 4px 12px; border-radius: 20px; font-size: 7.8pt; font-weight: 800;">
                🎯 Pleno Éxito: +$${pleno.pnl_mxn.toFixed(2)} (${pleno.probabilidad_pct}%)
            </span>
            <span style="background: rgba(56, 189, 248, 0.20); color: #38BDF8; border: 1px solid #38BDF8; padding: 4px 14px; border-radius: 20px; font-size: 8pt; font-weight: 900; box-shadow: 0 0 10px rgba(56, 189, 248, 0.3);">
                🛡️ Tablas o Ganancia: ≥ $0.00 (${tablas.probabilidad_pct}%) ⭐
            </span>
            <span style="background: rgba(239, 68, 68, 0.12); color: #ef4444; border: 1px solid #ef4444; padding: 4px 12px; border-radius: 20px; font-size: 7.8pt; font-weight: 700;">
                💀 Ruina Total: -$${Math.abs(ruina.pnl_mxn).toFixed(2)} (${ruina.probabilidad_pct}%)
            </span>
        `;
    }

    // 4. Tabla Resumen de Asignación
    const tbodyResumen = document.getElementById("cuerpo-resumen-asignacion");
    const tfootResumen = document.getElementById("pie-resumen-asignacion");
    if (tbodyResumen) {
        tbodyResumen.innerHTML = "";
        let sumaPremios = 0;
        let sumaInv = 0;

        orders.forEach(ord => {
            const inv = ord.boletos?.inversion_partido_A_i || 0;
            const gan = ord.proyecciones?.ganancia_neta_principal_mxn || 0;
            const tablas = ord.proyecciones?.resultado_tablas_mxn || 0;
            const roi = ord.proyecciones?.roi_principal_porcentaje || 0;
            const cod = ord.estrategia_seleccionada?.codigo || "";
            // [DES-QBE-045] Paleta canónica de las 9 familias estratégicas Q-BE.
            const pal = _paletaEstrategia(cod);
            sumaInv += inv;
            sumaPremios += gan;

            // [UX-MANDATE] Semántica precisa de cobertura por familia de estrategia (GOVERNANCE §8)
            let coberturaHtml = `<span style="color:#94A3B8;">Recuperas $${tablas.toFixed(2)} MXN ($0.00 pérdida)</span>`;
            // [V-4 / DES-QBE-062] El rótulo de Doble Cobro de la Familia R2 se gobierna por la
            // BANDERA BOOLEANA `pa_activo` (jamás por proxies de proyección heredados). Sin Pago
            // Anticipado la Doble Oportunidad Sintética cubre desenlaces MUTUAMENTE EXCLUYENTES:
            // exhibir "Ambos boletos ganan" sería fiduciariamente falso ([GOVERNANCE-01]).
            const paActivoFila = (ord.pa_activo === true) || Boolean(ord.estrategia_seleccionada?.linea_promocional);
            // [LN-QBE-083-B] [ARCH-1.4.16-B] Tramo 4: las familias DIRECTAS (QBE-D1 y QBE-D2) carecen de
            // pierna de cobertura en tablas ⇒ comparten el rótulo único de riesgo directo. El literal
            // genérico "Recuperas $X MXN ($0.00 pérdida)" queda erradicado para ellas: es fiduciariamente
            // falso al no existir recuperación alguna ([GOVERNANCE-01]).
            if (cod.startsWith("QBE-D1") || cod.startsWith("QBE-D2")) {
                coberturaHtml = `<span style="color:#f87171; font-weight:600;">Sin cobertura (Riesgo Directo: -$${inv.toFixed(2)})</span>`;
            } else if (cod === "QBE-R2") {
                coberturaHtml = paActivoFila
                    ? `<span style="color:#00E676; font-weight:600;">Ambos boletos ganan (+${roi.toFixed(1)}% ROI)</span>`
                    : `<span style="color:#38BDF8;">Recuperas $${tablas.toFixed(2)} MXN ($0.00 pérdida)</span>`;
            } else if (cod.startsWith("QBE-H1") || cod.startsWith("QBE-H2")) {
                // [ARCH-1.4.37 / LN-QBE-077-B] Con δ > 0 el seguro de tablas ya no recupera:
                // COSECHA. El veredicto lo certifica el bloque `cobertura_dinamica` del motor;
                // con δ = 0.0000 subsiste el rótulo sellado de recuperación V=0 (paridad).
                const cobFila = ord.cobertura_dinamica || null;
                coberturaHtml = (cobFila && Number(cobFila.delta_efectivo || 0) > 0)
                    ? `<span style="color:#00E676; font-weight:600;">Ganas +$${Number(cobFila.pnl_neto_empate_mxn || 0).toFixed(2)} MXN si empatan (+${Number(cobFila.roi_empate_porcentaje || 0).toFixed(1)}% ROI)</span>`
                    : `<span style="color:#38BDF8;">Recuperas $${tablas.toFixed(2)} MXN ($0.00 pérdida)</span>`;
            } else if (cod.startsWith("QBE-R1")) {
                coberturaHtml = `<span style="color:#38BDF8;">Recuperas $${tablas.toFixed(2)} MXN ($0.00 pérdida)</span>`;
            }

            // [ARCH-1.4.16-B] Tramo 3: el horario fáctico del encuentro se publica como línea secundaria
            // dentro de la columna PARTIDO (`horario_evento` es contrato sellado por [ARCH-1.4.16] y lo
            // emite src/web/routes/markets.py). Sin horario declarado no se inventa placeholder:
            // la fila se emite sin línea secundaria ([GOVERNANCE-01]).
            const horarioHtml = ord.horario_evento
                ? `<small style="display:block; font-weight:400; color:var(--text-muted); font-size:7.6pt;">⏰ ${ord.horario_evento}</small>`
                : "";

            // [UI-REFINEMENT-5-POINTS §3] Columna ROI %: cifra fáctica del contrato
            // (`roi_principal_porcentaje`). Cero estimaciones locales.
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td style="font-weight:700; color:#fff;">${ord.partido}${horarioHtml}</td>
                <td style="text-align:center;"><span class="badge-status-live" style="background:${pal.bg}; color:${pal.fg}; border-color:${pal.borde};">${cod}</span></td>
                <td style="text-align:right; font-weight:700;">$${inv.toFixed(2)}</td>
                <td style="text-align:right; font-weight:700; color:#00E676;">+$${gan.toFixed(2)} MXN</td>
                <td style="text-align:right; font-family:monospace; font-weight:700; color:#00E676;">${roi > 0 ? "+" : ""}${roi.toFixed(1)}%</td>
                <td>${coberturaHtml}</td>
                ${_celdaLiquidacionReal(ord)}
            `;
            tbodyResumen.appendChild(tr);
        });

        if (tfootResumen) {
            // [UI-REFINEMENT-5-POINTS §3] ROI % ponderado de cartera (`roi_global_esperado_porcentaje`,
            // KPI macro ya calculado por el motor). Sin hecho declarado se emite "—".
            tfootResumen.innerHTML = `
                <tr>
                    <td>TOTAL EN CARTERA</td>
                    <td style="text-align:center;">${orders.length} Posiciones</td>
                    <td style="text-align:right;">$${invTotal.toFixed(2)} MXN</td>
                    <td style="text-align:right; color:#00E676;">+$${sumaPremios.toFixed(2)} MXN</td>
                    <td style="text-align:right; font-family:monospace; color:#00E676;">${roiGlobal ? `${roiGlobal > 0 ? "+" : ""}${roiGlobal.toFixed(1)}%` : "—"}</td>
                    <td></td>
                    ${_celdaLiquidacionRealAgregada(data)}
                </tr>
            `;
        }
    }

    // 5. Tarjetas Ricas de Boletos Split (Ganancia a la Izquierda, Seguro a la Derecha, Escenarios Sobrios)
    const contSplit = document.getElementById("contenedor-tarjetas-split");
    if (contSplit) {
        contSplit.innerHTML = "";
        orders.forEach(ord => {
            const b1 = ord.boletos?.boleto_1_seguro || {};
            const b2 = ord.boletos?.boleto_2_ganancia || {};
            const opSlugB1 = (b1.operador || currentCasinoOperador || "caliente");
            const opSlugB2 = (b2.operador || currentCasinoOperador || "caliente");
            const est = ord.estrategia_seleccionada || {};
            // [DES-QBE-045] Paleta canónica de familia + distintivo de Pago Anticipado gobernado por bandera.
            const pal = _paletaEstrategia(est.codigo || "");
            const paBadgeHtml = _badgePagoAnticipado(ord, est);
            // [Dictamen V-4] Sello de liquidación real consumado en la cancha: sólo viaja cuando el
            // contrato del backend porta `liquidacion_real` (jornada anclada en backtesting).
            const selloLiquidacionHtml = _badgeLiquidacionReal(ord);
            const proy = ord.proyecciones || {};
            const inv = ord.boletos?.inversion_partido_A_i || 0;

            // Momios 1X2 completos
            const oddsObj = ord.momios_1x2 || {};
            const oddL = oddsObj.L ? `L @${Number(oddsObj.L).toFixed(2)}` : '';
            const oddE = oddsObj.E ? `E @${Number(oddsObj.E).toFixed(2)}` : '';
            const oddV = oddsObj.V ? `V @${Number(oddsObj.V).toFixed(2)}` : '';
            const momiosCompletos = [oddL, oddE, oddV].filter(Boolean).join(" | ");

            const b1Monto = b1.monto_mxn || 0;
            const b2Monto = b2.monto_mxn || 0;
            const cobroPrincipal = (b2Monto * (b2.momio || 1)).toFixed(2);
            const retornoTablas = (b1Monto * (b1.momio || 1)).toFixed(2);

            // [DES-QBE-061] Formato Dual de la cuota: probabilidad implícita del casino + decimal.
            // prob_implicita = 100.0 / O_casino (1 decimal, [DES-QBE-061]). Cero conversión en el
            // cliente: los momios ya viajan canónicos desde el motor ([GOVERNANCE-01] paridad).
            const _momioDual = (momio) => {
                const m = Number(momio);
                return (m > 1.0) ? `${(100.0 / m).toFixed(1)}% (@${m.toFixed(2)})` : '—';
            };
            const momioDualB1 = _momioDual(b2.momio);   // BOLETO 1 exhibido: GANANCIA (ataque)
            const momioDualB2 = _momioDual(b1.momio);   // BOLETO 2 exhibido: SEGURO (recuperación)
            // [DES-QBE-062] El renglón de Doble Cobro se gobierna por la bandera PA
            // ([DES-QBE-045]: por bandera booleana, jamás por proxies de proyección heredados).
            const paActivo = (ord.pa_activo === true) || Boolean(est.linea_promocional);
            // [ARCH-1.4.37 / LN-QBE-077-B] COSECHA ACTIVA: el bloque `cobertura_dinamica` es el
            // artefacto DERIVADO sellado por el motor (δ efectivo + ROIs proyectados). δ > 0 ⇒
            // el seguro de tablas deja de ser mera recuperación. Sin bloque ⇒ δ = 0.0000 (DEF).
            const cobDin = ord.cobertura_dinamica || null;
            const cosechaActiva = !!cobDin && Number(cobDin.delta_efectivo || 0) > 0;

            // [DES-QBE-062] Tetralogía de Escenarios en orden estricto y estilo sobrio (CERO balazos)
            let escenariosHtml = `
                <div style="font-size: 7.8pt; line-height: 1.6; color: #94A3B8; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 8px;">
                    <div>• <strong style="color: #e2e8f0;">Ganancia Principal:</strong> Cobro de $${cobroPrincipal} MXN (+$${proy.ganancia_neta_principal_mxn?.toFixed(2)} MXN netos, +${proy.roi_principal_porcentaje?.toFixed(1)}% ROI).</div>
            `;

            if (b1Monto > 0) {
                // [INVARIANTE VIII-11] Tras la Resolución Definitiva de VARIANZA-H2, la pierna de
                // recuperación (`boleto_1_seguro`) es SIEMPRE el Empate en toda la Familia H
                // (H1/H2). El renglón exhibe el capital recuperado CERTIFICADO POR EL MOTOR
                // (`inv`, con V=0 garantizado por `calcular_dutching_v0`), sin re-derivaciones
                // del cliente ([GOVERNANCE-01] paridad estricta backend↔pantalla).
                if (cosechaActiva) {
                    // [ARCH-1.4.37 / LN-QBE-077-B] COSECHA EN EMPATE: cifras CERTIFICADAS por el
                    // motor (`cobertura_dinamica`). El cliente sólo exhibe ([GOVERNANCE-01]).
                    escenariosHtml += `
                        <div>• <strong style="color: #00E676;">Cosecha en Empate (δ=${Number(cobDin.delta_efectivo).toFixed(4)}):</strong> Cobro de $${Number(cobDin.cobro_bruto_empate_mxn || 0).toFixed(2)} MXN (+$${Number(cobDin.pnl_neto_empate_mxn || 0).toFixed(2)} MXN netos, +${Number(cobDin.roi_empate_porcentaje || 0).toFixed(1)}% ROI).</div>
                    `;
                } else {
                    escenariosHtml += `
                        <div>• <strong style="color: #e2e8f0;">Cobertura en Empate:</strong> Recuperación de $${inv.toFixed(2)} MXN ($0.00 pérdida de capital).</div>
                    `;
                }
            }

            // Renglón 3: Pago Anticipado con Empate (Doble Cobro) si pa_activo es True y existe seguro
            if (paActivo && b1Monto > 0) {
                const dobleCobroTot = (Number(cobroPrincipal) + Number(retornoTablas)).toFixed(2);
                const dobleCobroNeto = Number(cobroPrincipal).toFixed(2);
                const dobleRoi = ((Number(dobleCobroNeto) / Math.max(0.01, inv)) * 100).toFixed(1);
                escenariosHtml += `
                    <div>• <strong style="color: #00E676;">Pago Anticipado con Empate:</strong> Cobro de AMBOS boletos por $${dobleCobroTot} MXN (+$${dobleCobroNeto} netos, +${dobleRoi}% ROI) si el favorito toma ventaja de 2 goles y el juego concluye empatado.</div>
                `;
            }

            // Renglón 4: Salida de Emergencia (Rompe-Quinielas)
            if (b1Monto > 0) {
                escenariosHtml += `
                    <div>• <strong style="color: #F59E0B;">Salida de Emergencia:</strong> Si el rival anota primero, ejecutar CashOut al empatar en el 2T en cuanto ofrezca Tablas ($${inv.toFixed(2)} MXN) para recuperar el 100% del capital.</div>
                `;
            }
            escenariosHtml += `</div>`;

            // [DES-QBE-060] Anatomía enriquecida del boleto: P' fiduciario por pierna y bloque de
            // transparencia 360°. El cliente NO calcula probabilidades: consume el contrato
            // hidratado por `PortfolioEngine.build_plan()` ([GOVERNANCE-01] paridad fáctica).
            const probB1Txt = (b2.prob_qbe === null || b2.prob_qbe === undefined) ? '—' : `${Number(b2.prob_qbe).toFixed(1)}%`;
            const probB2Txt = (b1.prob_qbe === null || b1.prob_qbe === undefined) ? '—' : `${Number(b1.prob_qbe).toFixed(1)}%`;
            const unbet = ord.opcion_no_jugada || {};
            const unbetNombre = unbet.nombre || 'Rival Descartado';
            const momioDualUnbet = _momioDual(unbet.momio);
            const unbetProb = (unbet.prob_qbe === null || unbet.prob_qbe === undefined) ? '—' : `${Number(unbet.prob_qbe).toFixed(1)}%`;
            // Cero jerga técnica y cero títulos ruidosos en este bloque ([DES-QBE-060]).
            const opcionNoJugadaHtml = `
                <div style="margin-top:8px; padding-top:6px; border-top:1px solid rgba(51,65,85,0.4); font-size:7.5pt; color:#94A3B8; font-family:monospace;">
                    • Opción No Jugada: <span style="color:#cbd5e1; font-weight:700;">${unbetNombre}</span> ──► Momio Casino: <strong style="color:#fff;">${momioDualUnbet}</strong> | Predicción Q-BE con P': <strong style="color:#38BDF8;">${unbetProb}</strong>
                </div>
            `;

            // [DES-QBE-069] Acciones de tarjeta: compra congelada en el Ledger + copia de ticket.
            const yaComprado = _verificarBoletoComprado(ord.id_partido);
            const btnComprarHtml = yaComprado
                ? `<button class="btn btn-sm" style="background:#1e293b; color:#00E676; border:1px solid #00E676; padding:6px 14px; border-radius:4px; font-size:7.8pt; font-weight:800; cursor:default;" disabled>✔ Boleto Registrado</button>`
                : `<button id="btn-comprar-${ord.id_partido}" onclick="comprarBoleto('${ord.id_partido}')" style="background:linear-gradient(135deg, #00E676 0%, #059669 100%); border:none; color:#0b1120; padding:6px 16px; border-radius:4px; font-size:8pt; font-weight:800; cursor:pointer; box-shadow:0 0 10px rgba(0,230,118,0.3);">🎟️ Comprar Boleto</button>`;

            // [ARCH-1.4.37 / LN-QBE-077-B] Rótulos del bloque de seguro según el veredicto del
            // motor: con δ > 0 el boleto se titula SEGURO ACTIVO y exhibe su proyección neta
            // certificada; con δ = 0.0000 subsiste el rótulo sellado de recuperación V=0.
            const tituloBoleto2 = cosechaActiva
                ? `🛡️ BOLETO 2: SEGURO ACTIVO (+${Number(cobDin.roi_empate_porcentaje || 0).toFixed(1)}% ROI)`
                : '🛡️ BOLETO 2: SEGURO (RECUPERACIÓN)';
            const subtituloCosechaHtml = cosechaActiva
                ? `<div style="font-size:7.5pt; color:#00E676; margin-top:2px;">Ganancia en Empate: Cobro de $${Number(cobDin.cobro_bruto_empate_mxn || 0).toFixed(2)} MXN (+$${Number(cobDin.pnl_neto_empate_mxn || 0).toFixed(2)} MXN netos, +${Number(cobDin.roi_empate_porcentaje || 0).toFixed(1)}% ROI)</div>`
                : '';

            const card = document.createElement("div");
            card.className = "card";
            card.style.cssText = "background:#1C2541; border:1px solid rgba(56,189,248,0.25); border-radius:8px; padding:16px;";
            card.innerHTML = `
                <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px;">
                    <div>
                        <div style="display:flex; gap:6px; align-items:center; margin-bottom:6px; flex-wrap:wrap;">
                            <span class="badge-status-live" style="background:${pal.bg}; color:${pal.fg}; border-color:${pal.borde}; font-weight:800;">${est.codigo}</span>
                            <span style="font-size:7.5pt; color:#cbd5e1;">${est.descripcion_ejecutiva}</span>
                            ${paBadgeHtml}
                            ${selloLiquidacionHtml}
                        </div>
                        <h3 style="margin:0; font-size:1.15rem; color:#fff;">${ord.partido}</h3>
                        <div style="font-size:7.5pt; color:#94A3B8; margin-top:3px;">⏰ ${ord.horario_evento} ${momiosCompletos ? `<span style="color:#64748B; margin:0 4px;">•</span> <span style="color:#38BDF8; font-weight:700;">${momiosCompletos}</span>` : ''}</div>
                    </div>
                    <div style="text-align:right;">
                        <span style="font-size:7pt; color:#94A3B8; text-transform:uppercase;">Inversión Total</span>
                        <div style="font-size:1.35rem; font-weight:900; color:#00E676;">$${inv.toFixed(2)} MXN</div>
                    </div>
                </div>

                <!-- Doble Boleto: Ganancia PRIMERO (Izquierda), Seguro SEGUNDO (Derecha) -->
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:12px;">
                    <!-- BOLETO GANANCIA / ATAQUE (IZQUIERDA - VERDE) -->
                    <div style="background:#0f172a; border:1px solid rgba(0,230,118,0.4); border-radius:6px; padding:12px;">
                        <span style="font-size:7.2pt; color:#00E676; font-weight:800;">🎯 BOLETO 1: GANANCIA (ATAQUE)</span>
                        <div style="font-size:1rem; font-weight:700; color:#fff; margin-top:3px;">${b2.seleccion || 'Victoria Principal'}</div>
                        <div style="font-size:7.5pt; color:#94A3B8; margin-top:2px;">Momio Casino: <strong style="color:#fff;">${momioDualB1}</strong></div>
                        <div style="font-size:7.5pt; color:#94A3B8;">Predicción Q-BE con P': <strong style="color:#38BDF8;">${probB1Txt}</strong></div>
                        <div style="margin-top:6px; padding-top:6px; border-top:1px solid rgba(255,255,255,0.05); display:flex; justify-content:space-between; align-items:flex-end;">
                            <span>${_rotuloCasaApostar(opSlugB2)}</span>
                            <span style="font-size:1.35rem; font-weight:900; color:#00E676;">$${(b2.monto_mxn || 0).toFixed(2)} MXN</span>
                        </div>
                    </div>

                    <!-- BOLETO SEGURO / RECUPERACIÓN (DERECHA - AZUL) -->
                    <div style="background:#0f172a; border:1px solid ${cosechaActiva ? 'rgba(0,230,118,0.45)' : 'rgba(56,189,248,0.3)'}; border-radius:6px; padding:12px;">
                        <span style="font-size:7.2pt; color:${cosechaActiva ? '#00E676' : '#38BDF8'}; font-weight:800;">${tituloBoleto2}</span>
                        <div style="font-size:1rem; font-weight:700; color:#fff; margin-top:3px;">${b1.seleccion || 'N/A ($0.00)'}</div>
                        ${subtituloCosechaHtml}
                        <div style="font-size:7.5pt; color:#94A3B8; margin-top:2px;">Momio Casino: <strong style="color:#fff;">${momioDualB2}</strong></div>
                        <div style="font-size:7.5pt; color:#94A3B8;">Predicción Q-BE con P': <strong style="color:#38BDF8;">${probB2Txt}</strong></div>
                        <div style="margin-top:6px; padding-top:6px; border-top:1px solid rgba(255,255,255,0.05); display:flex; justify-content:space-between; align-items:flex-end;">
                            <span>${_rotuloCasaApostar(opSlugB1)}</span>
                            <span style="font-size:1.35rem; font-weight:900; color:#38BDF8;">$${(b1.monto_mxn || 0).toFixed(2)} MXN</span>
                        </div>
                    </div>
                </div>

                <!-- Escenarios Desglosados Sobrios -->
                <div style="background:rgba(0,0,0,0.25); border-radius:6px; padding:10px 14px; margin-bottom:12px;">
                    ${escenariosHtml}
                </div>

                <!-- [DES-QBE-060] Bloque de Transparencia 360° al Pie de Tarjeta -->
                <div style="background:rgba(0,0,0,0.25); border-radius:6px; padding:8px 14px; margin-bottom:12px;">
                    ${opcionNoJugadaHtml}
                </div>

                <!-- [DES-QBE-069] Barra de dos extremos: Análisis (izq.) · Copiar + Comprar (der.) -->
                <div style="display:flex; justify-content:space-between; align-items:center; margin-top:12px; padding-top:10px; border-top:1px solid rgba(255,255,255,0.06);">
                    <button onclick="abrirRadiografiaForense('${ord.id_partido}')" style="background:transparent; border:1px solid #38BDF8; color:#38BDF8; padding:6px 14px; border-radius:4px; font-size:7.8pt; font-weight:700; cursor:pointer; display:inline-flex; align-items:center; gap:6px;">
                        🔬 Ver Análisis Cuantitativo
                    </button>
                    <div style="display:flex; align-items:center; gap:8px;">
                        <button onclick="copiarTicketPortapapeles('${ord.id_partido}')" style="background:rgba(255,255,255,0.04); border:1px solid #334155; color:#94A3B8; padding:6px 12px; border-radius:4px; font-size:7.8pt; cursor:pointer;" title="Copiar resumen para WhatsApp o terminal">
                            📋 Copiar Ticket
                        </button>
                        ${btnComprarHtml}
                    </div>
                </div>
            `;
            contSplit.appendChild(card);
        });
        // [UI-REFINEMENT-5-POINTS §1] La píldora del Ledger se pinta desde el estado
        // server-side hidratado; cero lectura de localStorage.
        _pintarBadgeLedger();
    }

    // 6. Radar de Descartes (QBE-00)
    const contDescartes = document.getElementById("contenedor-descartes");
    if (contDescartes) {
        contDescartes.innerHTML = "";
        const descartes = data.descartes || [];
        if (descartes.length === 0) {
            contDescartes.innerHTML = '<div style="color:#94A3B8; font-size:8pt; padding:8px;">Cero partidos vetados en esta selección.</div>';
        } else {
            descartes.forEach(d => {
                const m = d.metricas || {};
                const cifrasHtml = m.alpha_max !== undefined ?
                    `<div style="font-family: monospace; font-size: 7.2pt; color: #94A3B8; margin-top: 4px;">
                        Fav: ${(m.p_fav * 100).toFixed(0)}% (@${m.cuota_fav}) · Emp: @${m.cuota_empate} · α_max: <span style="color:#ef4444;">${(m.alpha_max * 100).toFixed(1)}% (-EV)</span> · θ*: ${m.theta_estrella}
                    </div>` : '';
                const item = document.createElement("div");
                item.style.cssText = "background:rgba(239,68,68,0.06); border:1px solid rgba(239,68,68,0.3); border-radius:6px; padding:10px 14px;";
                item.innerHTML = `
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                        <strong style="color:#fff; font-size:9pt;">❌ ${d.partido}</strong>
                        <span style="background:rgba(239,68,68,0.2); color:#ef4444; border:1px solid #ef4444; padding:2px 6px; border-radius:4px; font-size:7pt; font-weight:800;">VETO: ${d.motivo_codigo || 'QBE-00'}</span>
                    </div>
                    <div style="color:#cbd5e1; font-size:7.8pt;">${d.explicacion_didactica || d.motivo}</div>
                    ${cifrasHtml}
                `;
                contDescartes.appendChild(item);
            });
        }
    }
}

// ─── Modal de Radiografía Forense REBORN [LN-QBE-098 / ARCH-1.4.31 / DES-QBE-063] ──
// Cero red y cero LLM: toda la hidratación es determinista en O(1) sobre el payload
// soberano ya presente en memoria ([GOVERNANCE-01] paridad backend↔pantalla).

/** Densidad Poisson P(X=k) = λ^k · e^(-λ) / k!. Cálculo local determinista. */
function _calcularPoissonP(lambda, k) {
    let fact = 1;
    for (let i = 2; i <= k; i++) fact *= i;
    return (Math.pow(lambda, k) * Math.exp(-lambda)) / fact;
}

/** [DES-QBE-063-ext] Divide la etiqueta soberana en contendientes canónicos.
 *  El payload del portafolio rotula con " vs. " (engine.py) y el Live Board con " vs ";
 *  se admiten ambos separadores para no degradar la leyenda del comparador. */
function _dividirContendientes(p) {
    const bruto = String(p.partido || p.partido_nombre || "Local vs Visita").replace(/\s+/g, " ").trim();
    const partes = bruto.split(/\s+vs\.?\s+/i);
    const localNom = String(partes[0] || p.local || "Local").trim();
    const visitaNom = String(partes[1] || p.visitante || "Visita").trim();
    return [localNom, visitaNom];
}

/** [DES-QBE-063-ext] Lectura honesta de un hecho de la tabla 10P: devuelve null si el
 *  payload soberano no porta el dato (cero cifras fabricadas en pantalla). */
function _hecho10P(fila, clave) {
    const v = fila ? fila[clave] : null;
    if (v === null || v === undefined || v === "") return null;
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
}

/** [DES-QBE-063-ext] Extrae los goles concedidos (2º término) de "GF/GC" o "GF:GC",
 *  como los emite el motor (`engine.py`: "9/9"). Sin evidencia devuelve null. */
function _golesConcedidos(gfGc) {
    const m = String(gfGc === null || gfGc === undefined ? "" : gfGc).match(/(\d+)\s*[:/]\s*(\d+)/);
    return m ? Number(m[2]) : null;
}

/** [DES-QBE-063-ext-min] GF por partido de procedencia soberana: 1er término del hecho
 *  "goles_pro" del motor ("1.29 / 1.00" → 1.29) y, en su defecto, el cociente estricto
 *  gf/pj de la fila homóloga de posiciones. Sin evidencia devuelve null [GOVERNANCE-01]. */
function _gfPorPartido(fila10P, nombre) {
    const crudo = fila10P ? fila10P.goles_pro : null;
    const m = String(crudo === null || crudo === undefined ? "" : crudo).match(/^(\d+(?:\.\d+)?)\s*[:/]\s*(\d+(?:\.\d+)?)/);
    if (m) return Number(m[1]);
    const st = _filaStandings(nombre);
    const gf = _hecho10P(st, "gf");
    const pj = _hecho10P(st, "pj");
    return (gf !== null && pj) ? gf / pj : null;
}

/** [DES-QBE-063-ext-min] Partidos jugados: hecho 10P si viaja con el partido; si no, la fila
 *  homóloga de posiciones por normalización estricta de nombre. Sin match devuelve null. */
function _juegosJugados(fila10P, nombre) {
    const pj = _hecho10P(fila10P, "pj");
    return pj !== null ? pj : _hecho10P(_filaStandings(nombre), "pj");
}

/** [DES-QBE-063-ext-min] Homologación de nombres de club: minúsculas, sin acentos y sin los
 *  prefijos societarios que el proveedor intercala ("Club", "Deportivo", "FC"). */
function _normalizarClub(nombre) {
    return String(nombre || "")
        .toLowerCase()
        .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
        .replace(/\b(club|deportivo|fc)\b/g, "")
        .replace(/[^a-z0-9 ]+/g, " ")
        .replace(/\s+/g, " ").trim();
}

/** [DES-QBE-063-ext-min] Fila de posiciones del equipo: 1ª pasada por igualdad estricta
 *  normalizada y 2ª pasada por homología elástica de contención bidireccional
 *  ("Tigres" ⇄ "Tigres UANL"). Con cero candidatos o con más de uno devuelve null:
 *  JAMÁS se adivina la fila por posición ni se resuelve una ambigüedad con el primero
 *  de la tabla ([GOVERNANCE-01]). */
function _filaStandings(nombre) {
    const tabla = (typeof currentLiveBoard !== "undefined" && currentLiveBoard && Array.isArray(currentLiveBoard.standings))
        ? currentLiveBoard.standings : null;
    if (!tabla) return null;
    const objetivo = _normalizarClub(nombre);
    if (!objetivo) return null;
    const exactas = tabla.filter(t => _normalizarClub(t.equipo) === objetivo);
    if (exactas.length === 1) return exactas[0];
    if (exactas.length > 1) return null;
    const elasticas = tabla.filter(t => {
        const cand = _normalizarClub(t.equipo);
        return cand !== "" && (cand.includes(objetivo) || objetivo.includes(cand));
    });
    return elasticas.length === 1 ? elasticas[0] : null;
}

/** [DES-QBE-063-ext-min] Hecho numérico explícito de una fila soberana: si la clave no
 *  viaja o no es finita, devuelve null (cero cifras fabricadas) [GOVERNANCE-01]. */
function _hechoNumerico(fila, clave) {
    if (!fila) return null;
    const v = fila[clave];
    if (v === null || v === undefined || v === "") return null;
    return Number.isFinite(Number(v)) ? Number(v) : null;
}

/** [DES-QBE-063-ext-min] Cociente soberano estricto: sin numerador definido y denominador
 *  finito y positivo devuelve null; nunca un 0 ni un valor de relleno [GOVERNANCE-01]. */
function _porPartido(numerador, partidos) {
    if (numerador === null || numerador === undefined) return null;
    const n = Number(numerador);
    const d = Number(partidos);
    if (!Number.isFinite(n) || !Number.isFinite(d) || d <= 0) return null;
    return n / d;
}

/** [DES-QBE-063-ext-min] Pliega el diferencial relativo en la etiqueta del contendiente
 *  favorecido cuando el mayor es el mejor: "1.95 xG (+0.85)". */
function _plegarVentaja(idValLocal, idValVisita, vLocal, vVisita) {
    if (vLocal === null || vVisita === null || vLocal === vVisita) return;
    const el = document.getElementById(vLocal > vVisita ? idValLocal : idValVisita);
    if (el) el.textContent += ` (+${Math.abs(vLocal - vVisita).toFixed(2)})`;
}

/** [DES-QBE-063-ext-min] Pliega el diferencial relativo cuando el menor es el mejor
 *  (goles concedidos): el contendiente más sólido porta "(-0.20)". */
function _plegarDeficit(idValLocal, idValVisita, vLocal, vVisita) {
    if (vLocal === null || vVisita === null || vLocal === vVisita) return;
    const el = document.getElementById(vLocal < vVisita ? idValLocal : idValVisita);
    if (el) el.textContent += ` (-${Math.abs(vLocal - vVisita).toFixed(2)})`;
}

/** [DES-QBE-063-ext-min] Pinta una barra del comparador dual. Si el hecho soberano no
 *  existe, deja la barra neutra (50%) y el rótulo "--" con la causa honesta en el tooltip
 *  [GOVERNANCE-01]. `invertido` escala al revés (menos es mejor: goles concedidos). */
function _pintarBarraComparador(idBarra, idValor, valor, tope, sufijo, decimales, invertido) {
    const barEl = document.getElementById(idBarra);
    const valEl = document.getElementById(idValor);
    if (valor === null || valor === undefined || !Number.isFinite(Number(valor))) {
        if (barEl) barEl.style.width = "50%";
        if (valEl) {
            valEl.textContent = "--";
            valEl.title = "Sin evidencia 10P";
        }
        return null;
    }
    const v = Number(valor);
    const pct = invertido ? Math.max(15, 100 - (v / tope) * 70) : Math.min(100, Math.max(0, (v / tope) * 100));
    if (barEl) barEl.style.width = pct + "%";
    if (valEl) {
        valEl.textContent = v.toFixed(decimales) + sufijo;
        valEl.title = "";
    }
    return v;
}

/** [DES-QBE-063-ext-min] Comparador Gráfico de Barras Duales (Head-to-Head) minimalista:
 *  4 métricas de procedencia estrictamente soberana, leyenda apilada de contendientes y
 *  diferencial relativo plegado en la etiqueta del líder ("1.95 xG (+0.85)"). Cero prosa
 *  generativa y cero cifras fabricadas: sin evidencia el rótulo degrada a "--" [GOVERNANCE-01]. */
function _hidratarRadarYMarcadores(p) {
    const lamH = Number(p.lambda_local ?? p.lambda_home ?? p.xg_local ?? 1.5);
    const lamA = Number(p.mu_visita ?? p.lambda_away ?? p.xg_visita ?? 1.1);
    const [localNom, visitaNom] = _dividirContendientes(p);

    // Leyenda apilada: identidad única de contendientes (cero nombres repetidos en los renglones).
    const legLoc = document.getElementById("rad-legend-local");
    const legVis = document.getElementById("rad-legend-visita");
    if (legLoc) legLoc.textContent = localNom;
    if (legVis) legVis.textContent = visitaNom;

    // Fuente única de verdad: la tabla 10P viaja con el partido dentro del payload soberano.
    const t10 = Array.isArray(p.tabla_10p) ? p.tabla_10p : [];
    const norm = (s) => String(s || "").toLowerCase().replace(/\s+/g, " ").trim();
    const locSt = t10.find(t => norm(t.equipo) === norm(localNom)) || t10[0] || {};
    const visSt = t10.find(t => norm(t.equipo) === norm(visitaNom)) || t10[1] || {};

    // 1. Peligro Ofensivo: λ_H vs λ_A soberanos del motor (escala de barra 2.5 goles).
    const maxXg = Math.max(2.5, lamH, lamA);
    const xgH = _pintarBarraComparador("rad-bar-xg-loc", "rad-val-xg-loc", lamH, maxXg, " xG", 2);
    const xgA = _pintarBarraComparador("rad-bar-xg-vis", "rad-val-xg-vis", lamA, maxXg, " xG", 2);
    _plegarVentaja("rad-val-xg-loc", "rad-val-xg-vis", xgH, xgA);

    // 2. Producción en Temporada: GF por partido soberano ("goles_pro" del motor o gf/pj estricto).
    const proH = _gfPorPartido(locSt, localNom);
    const proA = _gfPorPartido(visSt, visitaNom);
    const maxPro = Math.max(3.0, proH ?? 0, proA ?? 0);
    const proVH = _pintarBarraComparador("rad-bar-sot-loc", "rad-val-sot-loc", proH, maxPro, " GF/PJ", 2);
    const proVA = _pintarBarraComparador("rad-bar-sot-vis", "rad-val-sot-vis", proA, maxPro, " GF/PJ", 2);
    _plegarVentaja("rad-val-sot-loc", "rad-val-sot-vis", proVH, proVA);

    // 3. Solidez Defensiva: goles concedidos por partido. Hecho soberano 10P ("gf_gc") y, si
    // el partido no lo porta (ruta del Live Board), remate en la fila homóloga de posiciones
    // ("gc" / "pj"). Menos concedidos = barra más larga (inversa). Sin fila homóloga: "--"
    // con barra neutra, jamás un relleno ([GOVERNANCE-01]).
    const stLoc = _filaStandings(localNom);
    const stVis = _filaStandings(visitaNom);
    const gcH = _golesConcedidos(locSt ? locSt.gf_gc : null);
    const gcA = _golesConcedidos(visSt ? visSt.gf_gc : null);
    const pjH = _juegosJugados(locSt, localNom);
    const pjA = _juegosJugados(visSt, visitaNom);
    const defH = _porPartido(gcH !== null ? gcH : _hechoNumerico(stLoc, "gc"), pjH);
    const defA = _porPartido(gcA !== null ? gcA : _hechoNumerico(stVis, "gc"), pjA);
    const maxDef = Math.max(2.5, defH ?? 0, defA ?? 0);
    const defVH = _pintarBarraComparador("rad-bar-def-loc", "rad-val-def-loc", defH, maxDef, " GC/PJ", 2, true);
    const defVA = _pintarBarraComparador("rad-bar-def-vis", "rad-val-def-vis", defA, maxDef, " GC/PJ", 2, true);
    _plegarDeficit("rad-val-def-loc", "rad-val-def-vis", defVH, defVA);

    // 4. Ritmo Competitivo: puntos por partido. Hecho soberano 10P ("pts_pj") y, si el partido
    // no lo porta, la aritmética soberana puntos/pj de su fila homóloga de posiciones.
    // Escala de barra 3.0 pts = techo teórico del torneo.
    const ritmoH = _hecho10P(locSt, "pts_pj");
    const ritmoA = _hecho10P(visSt, "pts_pj");
    const ptsPjH = ritmoH !== null ? ritmoH : _porPartido(_hechoNumerico(stLoc, "puntos"), pjH);
    const ptsPjA = ritmoA !== null ? ritmoA : _porPartido(_hechoNumerico(stVis, "puntos"), pjA);
    const posVH = _pintarBarraComparador("rad-bar-pos-loc", "rad-val-pos-loc", ptsPjH, 3.0, " pts/PJ", 2);
    const posVA = _pintarBarraComparador("rad-bar-pos-vis", "rad-val-pos-vis", ptsPjA, 3.0, " pts/PJ", 2);
    _plegarVentaja("rad-val-pos-loc", "rad-val-pos-vis", posVH, posVA);

    // 5. Top-4 marcadores más probables a partir de la rejilla Poisson 0..3.
    const scores = [];
    for (let x = 0; x <= 3; x++) {
        for (let y = 0; y <= 3; y++) {
            scores.push({ marcador: `${x} - ${y}`, prob: _calcularPoissonP(lamH, x) * _calcularPoissonP(lamA, y) });
        }
    }
    scores.sort((a, b) => b.prob - a.prob);
    const topContainer = document.getElementById("rad-top-marcadores");
    if (topContainer) {
        topContainer.innerHTML = scores.slice(0, 4).map(s => `
            <div style="background: #1e293b; padding: 6px 10px; border-radius: 6px; display: flex; justify-content: space-between; align-items: center;">
                <strong style="color: #f8fafc; font-size: 0.85rem;">${s.marcador}</strong>
                <span style="color: #38bdf8; font-size: 0.78rem; font-weight: 600;">${(s.prob * 100).toFixed(1)}%</span>
            </div>
        `).join("");
    }
}

/** [LN-QBE-098] Comparador de 6 columnas de probabilidad (cero momios).
 *  Colorimetría de boletos: Verde #00E676 = Ataque (Boleto 1), Azul #38BDF8 = Cobertura (Boleto 2). */
function _hidratarTablasRadiografia(p) {
    const COLOR_ATAQUE = "#00E676";
    const COLOR_COBERTURA = "#38BDF8";
    // [UI-REFINEMENT-5-POINTS §5 / DES-QBE-005] Gris Pizarra #64748B: token canónico legislado
    // para la serie NEUTRA (Empate / Rival no cubierto) del comparador de barras del modal.
    const COLOR_NEUTRO = "#64748B";
    const ord = p.orden || (Array.isArray(p.ordenes) ? p.ordenes[0] : null);

    // P' certificado (prob_qbe) por pierna + operador asignado, desde la orden soberana.
    const boletos = (ord && ord.boletos) || {};
    const legAtaque = boletos.boleto_2_ganancia || {};
    const legCobertura = boletos.boleto_1_seguro || {};
    const opNoJugada = (ord && ord.opcion_no_jugada) || {};

    const filas = Array.isArray(p.probabilidades_3vias) ? p.probabilidades_3vias : [];

    // ═══ [V-1 / VAR-2026-LIVE-AUDIT-J11] VINCULACIÓN POR IDENTIDAD DE PIERNA ═══
    // Defecto auditado: el P' certificado se asignaba por ROL POSICIONAL (la fila del favorito
    // reclamaba `boleto_2_ganancia` y la fila del Empate `boleto_1_seguro`). Tras la inversión
    // histórica de piernas en QBE-H2 (`VAR-H2-SIMETRIA-CANONICA`, commit génesis 0f4b340:
    // ataque en el Empate y seguro en el Favorito) el rol posicional ROTULABA EL P' DE LA
    // PIERNA EQUIVOCADA. La resolución es ahora por IDENTIDAD de la etiqueta `seleccion` de
    // cada pierna: espejo exacto del resolutor soberano del motor (`src/core/portfolio.py`),
    // fuente única de verdad. La posición en la tabla sólo sobrevive como degradación.
    const _normSeleccion = (s) => String(s || "")
        .toUpperCase()
        .replace(/\s*\+\s*PA\s*/gi, "")
        .replace(/\s+/g, " ")
        .trim();
    const _resolverPiernaDeFila = (resultado) => {
        const fila = String(resultado || "").trim().toUpperCase();
        const esFilaEmpate = /EMPATE/.test(fila);
        for (const leg of [legCobertura, legAtaque, opNoJugada]) {
            const sel = _normSeleccion(leg && leg.seleccion);
            if (!sel) continue;
            if (esFilaEmpate && /EMPATE/.test(sel)) return leg;
            if (!esFilaEmpate && sel === `GANA ${fila}`) return leg;
        }
        return null;  // Sin etiqueta certificada: degrada al rol posicional (cero invención).
    };

    // Favorito: por bandera, por nombre o por máxima probabilidad deportiva.
    let idxFav = null;
    if (p.is_fav_local === true) idxFav = 0;
    else if (p.is_fav_local === false) idxFav = filas.length - 1;
    else {
        let best = -1;
        filas.forEach((pv, i) => {
            if (/empate/i.test(String(pv.resultado || ""))) return;
            const pr = Number(pv.prob_real) || 0;
            if (pr > best) { best = pr; idxFav = i; }
        });
    }

    const consenso = p.consenso_mercado || null;
    const consensoSeq = consenso ? [consenso.p_L_mercado, consenso.p_E_mercado, consenso.p_V_mercado] : [];
    const fmtPct = (v) => (v === null || v === undefined || isNaN(Number(v))) ? "—" : `${Number(v).toFixed(1)}%`;

    // Suma de la MISMA probabilidad comercial exhibida en la tabla (fuente única de
    // probabilidades): alimenta el margen implícito del pie sin mezclar casas.
    let sumaProbCasinoReal = 0;

    const tbodyPron = document.getElementById("rad-cuerpo-pronostico");
    if (tbodyPron && filas.length) {
        tbodyPron.innerHTML = filas.map((pv, i) => {
            const esEmpate = /empate/i.test(String(pv.resultado || ""));
            const esAtaque = (!esEmpate && idxFav === i);

            // [V-1] La pierna se resuelve POR IDENTIDAD de su etiqueta; el rol posicional sólo
            // sobrevive como degradación cuando la orden no porta etiquetas certificadas.
            const legFila = _resolverPiernaDeFila(pv.resultado);
            const rol = (legFila === legAtaque) ? "ataque"
                : (legFila === legCobertura) ? "cobertura"
                : (legFila === opNoJugada) ? "none"
                : (esEmpate ? "cobertura" : (esAtaque ? "ataque" : "none"));
            const colorRes = (rol === "ataque") ? COLOR_ATAQUE
                : (rol === "cobertura") ? COLOR_COBERTURA
                : COLOR_NEUTRO;

            // P' fiduciaria CERTIFICADA por el motor, tomada de la pierna que ESTE desenlace
            // transporta realmente (identidad de etiqueta, jamás posición en la tabla).
            let pPrima = legFila ? legFila.prob_qbe : null;
            if (pPrima === null || pPrima === undefined) {
                if (rol === "ataque") pPrima = legAtaque.prob_qbe;
                else if (rol === "cobertura") pPrima = legCobertura.prob_qbe;
                else pPrima = opNoJugada.prob_qbe;
            }
            if (pPrima === null || pPrima === undefined) pPrima = pv.prob_real;

            // [DES-QBE-063] Columna CASINO SELECCIONADO: se resuelve MÁS ABAJO, sobre la cuota
            // REAL de la casa que paga ESTE desenlace (fuente única de probabilidades).

            // P̂ deportiva soberana (física de goles) certificada por el motor.
            const pDeportiva = pv.prob_real;

            // Consenso de mercado des-marginado (vig-free) si el fixture lo expone.
            const cRaw = consensoSeq[i];
            const pConsenso = (cRaw === null || cRaw === undefined) ? null : Number(cRaw) * 100.0;

            // [DES-QBE-063] CUOTA REAL que la casa asignada ofrece a ESTE desenlace: se erradica
            // el momio residual del snapshot cuando la orden viajó con otro operador. PROB.
            // CASINO, CASINO SELECCIONADO y VENTAJA (+EV) nacen de la MISMA cuota, de modo que
            // la tabla coincide al 100.0% con la tarjeta del boleto. Si la pierna no porta cuota
            // (V = $0.00) se degrada al momio fáctico del fixture y, sin operador asignado, al
            // operador vigente del selector (cero cifras inventadas).
            let momioReal = null;
            let operadorReal = null;

            // [V-1] Paridad estricta con la tarjeta del boleto: la cuota y el operador emanan de
            // la MISMA pierna identificada por etiqueta que gobierna el P' (fuente única).
            const legCuota = legFila
                || ((rol === "ataque") ? legAtaque : (rol === "cobertura") ? legCobertura : opNoJugada);
            if (legCuota && legCuota.momio) {
                momioReal = Number(legCuota.momio);
                operadorReal = legCuota.operador;
            } else {
                momioReal = Number(pv.momio);
            }

            // [ARCH-1.4.16] Herencia unívoca de operador: la pierna que no rotula casa
            // (opcion_no_jugada) hereda la del despacho vigente, jamás una casa ajena a la
            // cuota exhibida. Cero '—' mientras exista un operador gobernante declarado.
            if (!operadorReal) operadorReal = p.operador || currentCasinoOperador;

            // Probabilidad implícita COMERCIAL de ESA casa (comparación pura, sin cuota decimal).
            const probCasinoReal = (momioReal && momioReal > 1.0) ? (100.0 / momioReal) : null;
            if (probCasinoReal !== null) sumaProbCasinoReal += probCasinoReal;

            // [DES-QBE-063] Columna CASINO SELECCIONADO: operador ESPECÍFICO de CADA pierna.
            // Se descarta el rótulo residual de la modalidad cross-market ('mejor_combinacion'):
            // sólo se exhibe una casa real que publica cuota de ESTE desenlace, jamás el
            // selector global. Sin operador asignado ⇒ '—' (cero cifras inventadas). En la
            // práctica toda pierna sin rótulo hereda `currentCasinoOperador`, así que el '—'
            // sólo sobrevive en un desenlace huérfano de cuota y de operador gobernante.
            const slugOp = (operadorReal && String(operadorReal).toLowerCase() !== "mejor_combinacion")
                ? String(operadorReal).toLowerCase()
                : null;
            const nombreCap = slugOp ? slugOp.charAt(0).toUpperCase() + slugOp.slice(1) : null;
            // [DES-QBE-063-ext-min] Cero estrellas en la columna CASINO SELECCIONADO: el
            // operador se rotula en el color de su boleto (verde ataque / azul cobertura).
            const casinoTxt = slugOp
                ? `<span style="color: ${colorRes}; font-weight: 700;">${nombreCap}</span>`
                : "—";

            // Ventaja matemática neta sobre ESA casa: α = p̂·O − 1.0 ([LN-QBE-098]).
            // Se exhibe con UN decimal, idéntica a la métrica `ev_neto_roi_porcentaje`
            // de la tarjeta del boleto (paridad literal de cifras en pantalla).
            const alphaReal = (pDeportiva > 0 && momioReal > 1.0)
                ? ((pDeportiva / 100.0) * momioReal) - 1.0
                : null;
            const alphaColor = (alphaReal !== null && alphaReal > 0) ? COLOR_ATAQUE : "#EF4444";
            const alphaTxt = (alphaReal === null) ? "—" : `${alphaReal >= 0 ? "+" : ""}${(alphaReal * 100).toFixed(1)}%`;

            return `
                <tr style="border-top: 1px solid #1e293b;">
                    <td style="padding: 9px 14px; font-weight: 700; color: ${colorRes};">${pv.resultado}</td>
                    <td style="padding: 9px 10px; text-align: center; font-family: monospace; color: ${colorRes};">${fmtPct(pPrima)}</td>
                    <td style="padding: 9px 10px; text-align: center; font-family: monospace; color: #cbd5e1;">${fmtPct(pDeportiva)}</td>
                    <td style="padding: 9px 10px; text-align: center; font-family: monospace; color: #cbd5e1;">${fmtPct(pConsenso)}</td>
                    <td style="padding: 9px 10px; text-align: center; font-family: monospace; color: #94a3b8;">${fmtPct(probCasinoReal)}</td>
                    <td style="padding: 9px 10px; text-align: center; color: #e2e8f0; font-weight: 600;">${casinoTxt}</td>
                    <td style="padding: 9px 14px; text-align: right; font-weight: 800; color: ${alphaColor};">${alphaTxt}</td>
                </tr>
            `;
        }).join("");
    }

    // Margen comercial implícito del operador (Σ probabilidades implícitas − 100%).
    const footerCom = document.getElementById("rad-footer-comisiones");
    if (footerCom && filas.length) {
        const suma = sumaProbCasinoReal;
        footerCom.textContent = (suma > 0)
            ? `Margen comercial implícito del operador: ${(suma - 100).toFixed(1)}% · Comparación pura de probabilidades (sin cuota decimal).`
            : "";
    }

    // KPI Tiles: intensidades de gol y pago anticipado.
    const kLambda = document.getElementById("rad-kpi-lambda");
    const kMu = document.getElementById("rad-kpi-mu");
    const kTot = document.getElementById("rad-kpi-totales");
    const kPa = document.getElementById("rad-kpi-pa");
    if (kLambda) kLambda.textContent = (p.lambda_local !== undefined && p.lambda_local !== null) ? Number(p.lambda_local).toFixed(2) : "--";
    if (kMu) kMu.textContent = (p.mu_visita !== undefined && p.mu_visita !== null) ? Number(p.mu_visita).toFixed(2) : "--";
    if (kTot) kTot.textContent = (p.xg_total !== undefined && p.xg_total !== null) ? Number(p.xg_total).toFixed(2) : "--";
    if (kPa) kPa.textContent = (p.phi_lead2_pct !== undefined && p.phi_lead2_pct !== null) ? `${Number(p.phi_lead2_pct).toFixed(1)}%` : "--";

    // [DES-QBE-063-ext-min] Radiografía Estructural y Forma Reciente: dos filas (Local azul /
    // Visitante verde) leídas de la fila homóloga de posiciones del Live Board. Toda celda sin
    // hecho soberano degrada a "--" (cero ceros, récords ni xG inventados) [GOVERNANCE-01].
    const tbodyEq = document.getElementById("rad-cuerpo-equipos");
    if (tbodyEq) {
        const SIN_HECHO = "--";
        const [localTab, visitaTab] = _dividirContendientes(p);
        const t10Tabla = Array.isArray(p.tabla_10p) ? p.tabla_10p : [];
        const qmodDe = (nombre) => {
            const f10 = t10Tabla.find(t => _normalizarClub(t.equipo) === _normalizarClub(nombre));
            return f10 ? _hechoNumerico(f10, "qmod") : null;
        };
        const celda = (texto, color, negrita) => (texto === null || texto === undefined)
            ? `<td style="padding: 8px 8px; text-align: center; color: #64748b;">${SIN_HECHO}</td>`
            : `<td style="padding: 8px 8px; text-align: center; color: ${color || "#cbd5e1"}; font-weight: ${negrita ? 700 : 500};">${texto}</td>`;
        const formaDots = (forma) => {
            const arr = Array.isArray(forma) ? forma : [];
            if (arr.length === 0) return SIN_HECHO;
            return arr.map(f => {
                const c = (f === "G" || f === "W") ? "#00E676" : (f === "E" || f === "D") ? "#64748B" : "#ef4444";
                return `<span title="${f}" style="display:inline-block; width:9px; height:9px; border-radius:50%; background:${c}; margin:0 2px;"></span>`;
            }).join("");
        };
        const filaEstructural = (nombre, fila, color, marca) => {
            const pos = _hechoNumerico(fila, "pos");
            const pts = _hechoNumerico(fila, "puntos");
            const pg = _hechoNumerico(fila, "pg");
            const pe = _hechoNumerico(fila, "pe");
            const pp = _hechoNumerico(fila, "pp");
            const dif = _hechoNumerico(fila, "dif");
            const gf = _hechoNumerico(fila, "gf");
            const gc = _hechoNumerico(fila, "gc");
            const xg = _hechoNumerico(fila, "xg");
            const xga = _hechoNumerico(fila, "xga");
            const xpts = _hechoNumerico(fila, "xpts");
            const qmod = qmodDe(nombre);
            const record = (pg !== null && pe !== null && pp !== null) ? `${pg}G · ${pe}E · ${pp}P` : null;
            const difGoles = (dif === null) ? null : `${dif > 0 ? "+" : ""}${dif} (${gf ?? SIN_HECHO}:${gc ?? SIN_HECHO})`;
            const difXg = (xg === null || xga === null) ? null : `${(xg - xga) > 0 ? "+" : ""}${(xg - xga).toFixed(1)} xG`;
            return `
                <tr style="border-top: 1px solid #1e293b;">
                    <td style="padding: 8px 12px; font-weight: 700; color: ${color};">${marca} ${nombre}</td>
                    ${celda(pos === null ? null : `#${pos}`, color, true)}
                    ${celda(pts, color, true)}
                    ${celda(record)}
                    ${celda(difGoles)}
                    <td style="padding: 8px 12px; text-align: center; white-space: nowrap;">${formaDots(fila ? fila.forma : null)}</td>
                    ${celda(xpts === null ? null : `${xpts.toFixed(1)} pts`)}
                    ${celda(difXg)}
                    ${celda(qmod === null ? null : qmod.toFixed(2), "#38bdf8", true)}
                </tr>
            `;
        };
        tbodyEq.innerHTML = filaEstructural(localTab, _filaStandings(localTab), "#38bdf8", "🔵")
            + filaEstructural(visitaTab, _filaStandings(visitaTab), "#00e676", "🟢");
    }
}

async function abrirRadiografiaForense(matchId) {
    // [DES-QBE-045 cláusula 4] Autarquía de la Radiografía Forense: no exige cálculo de cartera previo.
    // Fuente 1: análisis soberano de la cartera. Fuente 2: datos soberanos del Live Board (fixtures).
    let p = (currentPortfolioData?.partidos_analisis || []).find(x => x.id_partido === matchId);
    if (!p) {
        const fixture = (currentLiveBoard?.fixtures || []).find(x => x.id_partido === matchId);
        if (!fixture) return;
        p = _adaptarFixtureARadiografia(fixture);
    }
    // Orden soberana asociada (P' fiduciaria por pierna y operador) — clave canónica 3NF
    // `ordenes_ejecucion_partidos` con fallback declarado a `ordenes` ([DES-QBE-045]).
    const allOrders = currentPortfolioData?.ordenes_ejecucion_partidos
        || currentPortfolioData?.ordenes
        || [];
    p.orden = allOrders.find(x => x.id_partido === matchId) || p.orden || null;

    document.getElementById("modal-radiografia-forense").style.display = "block";

    // [DES-QBE-063] Cabecera: píldora de estrategia REAL (familia canónica QBE-H/D/R/C)
    // resuelta desde la orden soberana; jamás el residuo genérico 'QBE-00' por omisión.
    const badgeEl = document.getElementById("rad-estrategia-badge");
    if (badgeEl) {
        const ordBadge = p.orden || {};
        const stratCode = (ordBadge.estrategia_seleccionada && ordBadge.estrategia_seleccionada.codigo)
            || ordBadge.estrategia_codigo
            || p.estrategia_codigo
            || p.strategy_code
            || "QBE-00";
        const pal = _paletaEstrategia(stratCode);
        badgeEl.textContent = stratCode;
        badgeEl.style.color = pal.fg;
        badgeEl.style.borderColor = pal.borde;
        badgeEl.style.background = pal.bg;
    }
    const tituloEl = document.getElementById("rad-titulo-partido");
    if (tituloEl) tituloEl.textContent = p.partido || p.partido_nombre || "Partido";
    const horarioEl = document.getElementById("rad-horario");
    if (horarioEl) horarioEl.textContent = String(p.horario || "").replace(/\n/g, " ");

    // [LN-QBE-098] Hidratación 100% local y determinista: Gemini permanece en reposo total (cero red).
    _hidratarRadarYMarcadores(p);
    _hidratarTablasRadiografia(p);
}

function cerrarRadiografiaForense() {
    document.getElementById("modal-radiografia-forense").style.display = "none";
}
window.abrirRadiografiaForense = abrirRadiografiaForense;
window.cerrarRadiografiaForense = cerrarRadiografiaForense;

// ─── [ARCH-1.4.32 / P3-9] LEDGER FIDUCIARIO 3NF (SIN localStorage) ──────────
// El boleto se sella vía POST /api/portfolio/register-ticket. El servidor es la única
// fuente de verdad del agregado y del estado "ya comprado" (tabla paper_trading_ledger).

let _ledgerBoletos = new Set();
let _ledgerCount = 0;
let _ledgerMonto = 0.0;

function _pintarBadgeLedger() {
    const badge = document.getElementById("badge-boletos-comprados");
    if (badge) {
        badge.textContent = `🎟️ Comprados: ${_ledgerCount} ($${Number(_ledgerMonto).toFixed(2)} MXN)`;
    }
}

/** ¿El boleto de este partido ya fue sellado en el ledger 3NF? */
function _verificarBoletoComprado(matchId) {
    return _ledgerBoletos.has(matchId);
}

/** Hidrata el badge y el estado "ya comprado" desde el servidor (cero localStorage). */
async function _hidratarLedgerDesdeServidor() {
    try {
        const resp = await fetch("/api/portfolio/ledger-status");
        if (!resp.ok) return;
        const data = await resp.json();
        _ledgerBoletos = new Set(data.match_ids || []);
        _ledgerCount = Number(data.boletos_comprados || 0);
        _ledgerMonto = Number(data.monto_comprometido_mxn || 0);
        _pintarBadgeLedger();
    } catch (e) {
        // Sin red: el badge conserva el último estado conocido; cero escritura local.
    }
}

/** [CONGELAMIENTO] Sella el boleto en el ledger 3NF a través del endpoint gobernado. */
async function comprarBoleto(matchId) {
    const allOrders = currentPortfolioData?.ordenes_ejecucion_partidos
        || currentPortfolioData?.ordenes
        || [];
    const ord = allOrders.find(x => x.id_partido === matchId);
    if (!ord) return;

    const b2 = ord.boletos?.boleto_2_ganancia || {};
    const payload = {
        match_id: ord.id_partido,
        desenlace: b2.seleccion || ord.estrategia_seleccionada?.codigo || "QBE-00",
        cuota_congelada: Number(b2.momio),
        monto: Number(ord.boletos?.inversion_partido_A_i),
    };

    if (!(payload.cuota_congelada > 1.0) || !(payload.monto > 0.0)) {
        alert("No se puede registrar el boleto: cuota congelada o monto inválidos.");
        return;
    }

    const btn = document.getElementById(`btn-comprar-${matchId}`);
    if (btn) {
        btn.disabled = true;
        btn.textContent = "Registrando...";
    }

    try {
        const resp = await fetch("/api/portfolio/register-ticket", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        const data = await resp.json();
        if (!resp.ok) {
            throw new Error(data.detail || "No se pudo registrar el boleto.");
        }

        _ledgerBoletos.add(matchId);
        _ledgerCount = Number(data.boletos_comprados || _ledgerCount);
        _ledgerMonto = Number(data.monto_comprometido_mxn || _ledgerMonto);
        _pintarBadgeLedger();

        if (btn) {
            btn.style.background = "#1e293b";
            btn.style.color = "#00E676";
            btn.style.border = "1px solid #00E676";
            btn.style.boxShadow = "none";
            btn.style.cursor = "default";
            btn.innerHTML = "✔ Boleto Registrado";
            btn.disabled = true;
        }
        alert(`🎟️ Boleto registrado en el ledger 3NF para ${ord.partido}.`);
    } catch (e) {
        if (btn) {
            btn.disabled = false;
            btn.textContent = "🎟️ Comprar Boleto";
        }
        alert(`No se pudo registrar el boleto: ${e.message}`);
    }
}

/** [MEJORA 2] Copia al portapapeles el ticket en formato limpio para ventanilla / WhatsApp. */
function copiarTicketPortapapeles(matchId) {
    const allOrders = currentPortfolioData?.ordenes_ejecucion_partidos
        || currentPortfolioData?.ordenes
        || [];
    const ord = allOrders.find(x => x.id_partido === matchId);
    if (!ord) return;

    const b1 = ord.boletos?.boleto_1_seguro || {};
    const b2 = ord.boletos?.boleto_2_ganancia || {};
    const inv = ord.boletos?.inversion_partido_A_i || 0;

    let texto = `🏛️ TICKET Q-BE · ${ord.partido}\n`;
    texto += `⏰ ${ord.horario_evento} | Inversión: $${Number(inv).toFixed(2)} MXN\n`;
    texto += `• Boleto 1 (Ataque): ${b2.seleccion} @${b2.momio} (${String(b2.operador || "").toUpperCase()}) ➔ $${Number(b2.monto_mxn || 0).toFixed(2)} MXN\n`;
    if (Number(b1.monto_mxn || 0) > 0) {
        texto += `• Boleto 2 (Seguro): ${b1.seleccion} @${b1.momio} (${String(b1.operador || "").toUpperCase()}) ➔ $${Number(b1.monto_mxn || 0).toFixed(2)} MXN (Tablas V=0)\n`;
    }
    texto += `🎯 Ganancia Neta: +$${Number(ord.proyecciones?.ganancia_neta_principal_mxn || 0).toFixed(2)} MXN`;

    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(texto)
            .then(() => alert("📋 Ticket copiado al portapapeles."))
            .catch(() => prompt("Copie manualmente el ticket:", texto));
    } else {
        prompt("Copie manualmente el ticket:", texto);
    }
}

window.comprarBoleto = comprarBoleto;
window.copiarTicketPortapapeles = copiarTicketPortapapeles;

// El ledger 3NF se hidrata desde el servidor al cargar la SPA.
document.addEventListener("DOMContentLoaded", _hidratarLedgerDesdeServidor);

// ─── Funciones del Panel de Curación Agéntica HITL [ARCH-1.5.2] ─────────────
async function abrirModalCurador(leagueId = 262) {
    document.getElementById("modal-curador-hitl").style.display = "block";
    const grid = document.getElementById("grid-curacion-clubes");
    grid.innerHTML = '<div style="color:#38BDF8; padding:20px;">🔍 Cargando candidatos prospectados...</div>';

    try {
        const resp = await fetch(`/api/admin/catalogs/staging?league_id=${leagueId}`);
        const teams = await resp.json();
        grid.innerHTML = "";

        teams.forEach(t => {
            const card = document.createElement("div");
            card.style.cssText = "background: #0f172a; border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; padding: 12px;";

            // Priorizar ruta local soberana con fallback a candidate_url
            const imgSrc = t.crest_url || t.crest_candidate_url;

            card.innerHTML = `
                <div style="display: flex; gap: 10px; align-items: center; margin-bottom: 8px;">
                    <img src="${imgSrc}" onerror="this.src='${t.crest_candidate_url}'" referrerpolicy="no-referrer" alt="" style="width: 36px; height: 36px; object-fit: contain;">
                    <div>
                        <strong style="color: #fff; font-size: 9pt;">${t.name}</strong>
                        <div style="color: #94A3B8; font-size: 7.2pt;">Estadio: ${t.stadium} (${t.city})</div>
                    </div>
                </div>
                <div style="font-size: 6.8pt; color: #38BDF8; margin-bottom: 8px;">Aliases: ${(t.aliases || []).join(", ")}</div>
                <div style="display: flex; justify-content: flex-end;">
                    <span style="color: #00E676; font-size: 7.2pt; font-weight: 700;">✅ Validado</span>
                </div>
            `;
            grid.appendChild(card);
        });
    } catch (e) {
        grid.innerHTML = `<div style="color:#f87171;">Error: ${e.message}</div>`;
    }
}

function cerrarModalCurador() {
    document.getElementById("modal-curador-hitl").style.display = "none";
}

async function sellarCatalogoCompleto(leagueId = 262) {
    try {
        const stagedResp = await fetch(`/api/admin/catalogs/staging?league_id=${leagueId}`);
        const teams = await stagedResp.json();

        const commitResp = await fetch("/api/admin/catalogs/commit", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ league_id: leagueId, approved_teams: teams })
        });
        const res = await commitResp.json();
        alert(`✅ Catálogo sellado con éxito: ${res.teams_committed} clubes guardados en SQLite.`);
        cerrarModalCurador();
        location.reload();
    } catch (e) {
        alert(`❌ Error al sellar: ${e.message}`);
    }
}

// [FAST-TRACK FIX]: Exponer funciones del Modal Curador al ámbito global
window.abrirModalCurador = typeof abrirModalCurador !== 'undefined' ? abrirModalCurador : function () {
    const modal = document.getElementById('modalCurador') || document.getElementById('modal-curador');
    if (modal) modal.style.display = 'flex';
};

window.cerrarModalCurador = typeof cerrarModalCurador !== 'undefined' ? cerrarModalCurador : function () {
    const modal = document.getElementById('modalCurador') || document.getElementById('modal-curador');
    if (modal) modal.style.display = 'none';
};

window.sellarCatalogoCompleto = typeof sellarCatalogoCompleto !== 'undefined' ? sellarCatalogoCompleto : function () {
    console.log("Sellando catálogo...");
};

// Funciones globales para control masivo de selección en cartelera
function seleccionarTodosPartidos() {
    selectedMatchIds = [];
    document.querySelectorAll('.fixture-card:not(.fixture-disabled)').forEach(card => {
        const checkbox = card.querySelector("input[type='checkbox']");
        const matchId = card.dataset.matchId;
        if (checkbox && !checkbox.disabled) {
            checkbox.checked = true;
            card.classList.add("selected");
            card.style.borderColor = "#38BDF8";
            if (matchId) selectedMatchIds.push(matchId);
        }
    });
    actualizarContadorSeleccionados();
}

function deseleccionarTodosPartidos() {
    selectedMatchIds = [];
    document.querySelectorAll('.fixture-card').forEach(card => {
        const checkbox = card.querySelector("input[type='checkbox']");
        if (checkbox) {
            checkbox.checked = false;
        }
        card.classList.remove("selected");
        card.style.borderColor = "#334155";
    });
    actualizarContadorSeleccionados();
}

// Exponer al ámbito global
window.seleccionarTodosPartidos = seleccionarTodosPartidos;
window.deseleccionarTodosPartidos = deseleccionarTodosPartidos;

// [DES-QBE-040] Alternador de Modo Enfoque (Ocultar/Mostrar Tabla de Posiciones)
function toggleTablaPosiciones() {
    // Localizar el contenedor split-view padre de Pantalla 1
    const splitContainer = document.querySelector('.split-view-container') || 
                           document.querySelector('.split-view') ||
                           document.getElementById('sovereign-split-container') ||
                           document.querySelector('#view-sovereign-hub .content-grid');

    const btnTxt = document.getElementById('btn-toggle-txt');
    const btnIcon = document.getElementById('btn-toggle-icon');
    const btn = document.getElementById('btn-toggle-standings');

    if (!splitContainer) {
        console.warn("No se encontró el contenedor split-view para alternar.");
        return;
    }

    const estaOculta = splitContainer.classList.toggle('standings-hidden');

    if (btnTxt && btnIcon) {
        if (estaOculta) {
            btnIcon.textContent = '◧';
            btnTxt.textContent = 'Ver Tabla';
            if (btn) btn.classList.add('active-focus');
            localStorage.setItem('qbe_standings_hidden', 'true');
        } else {
            btnIcon.textContent = '◨';
            btnTxt.textContent = 'Ocultar Tabla';
            if (btn) btn.classList.remove('active-focus');
            localStorage.setItem('qbe_standings_hidden', 'false');
        }
    }
}
window.toggleTablaPosiciones = toggleTablaPosiciones;

// Al inicializar la app, verificar si el usuario tenía la tabla oculta previamente
document.addEventListener('DOMContentLoaded', () => {
    if (localStorage.getItem('qbe_standings_hidden') === 'true') {
        const splitContainer = document.querySelector('.split-view-container') || 
                               document.querySelector('.split-view') ||
                               document.getElementById('sovereign-split-container') ||
                               document.querySelector('#view-sovereign-hub .content-grid');
        if (splitContainer) {
            splitContainer.classList.add('standings-hidden');
            const btnTxt = document.getElementById('btn-toggle-txt');
            const btnIcon = document.getElementById('btn-toggle-icon');
            const btn = document.getElementById('btn-toggle-standings');
        }
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// [DES-QBE-045] PALETA CANÓNICA DE LAS 9 ESTRATEGIAS Q-BE Y PAGO ANTICIPADO
// Familias: D1/D2 (cian) · H1/H2 (verde) · R1/R2 (ámbar) · C1/C2 (violeta) · 00 (coral)
// ═══════════════════════════════════════════════════════════════════════════════

/** Paleta soberana por familia estratégica (LOGIC.md [LN-QBE-060-B], DESIGN.md [DES-QBE-045]). */
const PALETA_ESTRATEGIAS_QBE = {
    "QBE-D": { bg: "rgba(56,189,248,0.18)", fg: "#38BDF8", borde: "#38BDF8" },
    "QBE-H": { bg: "rgba(0,230,118,0.18)", fg: "#00E676", borde: "#00E676" },
    "QBE-R": { bg: "rgba(245,158,11,0.18)", fg: "#F59E0B", borde: "#F59E0B" },
    "QBE-C": { bg: "rgba(168,85,247,0.18)", fg: "#A855F7", borde: "#A855F7" },
    "QBE-00": { bg: "rgba(239,68,68,0.18)", fg: "#EF4444", borde: "#EF4444" }
};

/** Resuelve la familia canónica de un código; degrada a gris neutro si el código no está declarado. */
function _paletaEstrategia(codigo) {
    const cod = String(codigo || "").toUpperCase();
    const familia = Object.keys(PALETA_ESTRATEGIAS_QBE).find(k => cod.startsWith(k));
    return familia
        ? PALETA_ESTRATEGIAS_QBE[familia]
        : { bg: "rgba(148,163,184,0.15)", fg: "#94A3B8", borde: "#64748B" };
}

/** [DES-QBE-045] El distintivo (+PA) se gobierna por bandera booleana, nunca por el sufijo '+' heredado. */
function _badgePagoAnticipado(ord, est) {
    const activo = (ord && ord.pa_activo === true) || Boolean(est && est.linea_promocional);
    if (!activo) return "";
    const etiqueta = String((est && est.linea_promocional) || "Pago Anticipado").replace(/\+PA/gi, "").trim();
    return `<span class="badge-status-live" style="background:rgba(0,230,118,0.12); color:#00E676; border-color:#00E676; font-size:7.5pt; font-weight:700;">🏷️ ${etiqueta} (+PA)</span>`;
}

// ═══════════════════════════════════════════════════════════════════════════════
// [DES-QBE-046] SUB-VISTA QUINIELAS PROGOL — CONTRATO FÁCTICO CONSUMIDO
//   GET  /api/markets/progol/slates/active  -> markets.py:497-509
//   POST /api/markets/progol/optimize       -> progol_math.py:156-162
// Cero mapeo a claves hipotéticas: la UI sirve al contrato real (desviación D-3 autorizada).
// ═══════════════════════════════════════════════════════════════════════════════

let currentProgolSlate = null;

/** Conmuta la Mesa de Apuestas entre la sub-vista Sportsbook y la sub-vista Progol. */
function conmutarSubvistaMercados(vista) {
    const esProgol = vista === "progol";
    const contSportsbook = document.getElementById("contenedor-sportsbook");
    const contProgol = document.getElementById("contenedor-progol");
    const btnSportsbook = document.getElementById("btn-subtab-sportsbook");
    const btnProgol = document.getElementById("btn-subtab-progol");

    if (contSportsbook) contSportsbook.style.display = esProgol ? "none" : "";
    if (contProgol) contProgol.style.display = esProgol ? "" : "none";
    if (btnSportsbook) btnSportsbook.classList.toggle("active", !esProgol);
    if (btnProgol) btnProgol.classList.toggle("active", esProgol);

    if (esProgol && !currentProgolSlate) cargarSlateProgolActivo();
}

/** Hidrata el encabezado y el retículo del concurso vigente desde la bóveda 3NF. */
async function cargarSlateProgolActivo() {
    const cont = document.getElementById("progol-reticulo-container");
    if (!cont) return;
    cont.innerHTML = '<div style="font-size: 8.5pt; color: #94A3B8;">Consultando bóveda 3NF…</div>';
    try {
        const resp = await fetch("/api/markets/progol/slates/active");
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const slate = await resp.json();
        currentProgolSlate = slate;
        _renderEncabezadoProgol(slate);
        _renderReticuloProgol(slate);
    } catch (e) {
        console.error("Fallo hidratando el concurso Progol:", e);
        currentProgolSlate = null;
        cont.innerHTML = `<div style="font-size: 8.5pt; color: #F87171;">⚠️ No fue posible leer la bóveda 3NF del concurso Progol (${e.message}). Cero cifras se muestran sin respaldo.</div>`;
    }
}

/** [GOVERNANCE-01] Encabezado honesto: si la bóveda no declara un dato, se rotula con '—'. */
function _renderEncabezadoProgol(slate) {
    const elNombre = document.getElementById("progol-slate-nombre");
    const elCasillas = document.getElementById("progol-slate-casillas");
    const elBolsa = document.getElementById("progol-slate-bolsa");
    const elCierre = document.getElementById("progol-slate-cierre");
    const elFuente = document.getElementById("progol-sesgo-fuente");

    const sinConcurso = !slate || !slate.slate_id;
    if (elNombre) {
        elNombre.textContent = sinConcurso
            ? "Sin concurso Progol OPEN en la bóveda 3NF"
            : (slate.name || "Concurso Progol");
    }
    if (elCasillas) {
        elCasillas.textContent = sinConcurso
            ? "—"
            : `${slate.items_total} casillas · ${slate.soberanos} soberanas (3NF) · ${slate.priors} con Prior Base (1/3)`;
    }
    if (elBolsa) {
        const bolsa = slate ? slate.bolsa_garantizada_mxn : null;
        elBolsa.textContent = (bolsa === null || bolsa === undefined)
            ? "—"
            : `$${Number(bolsa).toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} MXN`;
    }
    if (elCierre) {
        elCierre.textContent = `Tiempo límite: ${(slate && slate.fecha_cierre) ? slate.fecha_cierre : "—"}`;
    }
    if (elFuente) {
        const fuente = slate ? slate.sesgo_fuente : null;
        elFuente.textContent = (fuente === "MOMIOS_DE_CASINO")
            ? "📡 Contraste con venta pública: momios de casino de la jornada"
            : `📡 Contraste con venta pública: no disponible (${fuente || "SIN_BOVEDA"})`;
    }
}

/** Retículo de casillas del concurso (14 PROGOL REGULAR + 7 REVANCHA) leído de la bóveda 3NF. */
function _renderReticuloProgol(slate) {
    const cont = document.getElementById("progol-reticulo-container");
    if (!cont) return;
    const items = (slate && slate.items) || [];
    if (items.length === 0) {
        cont.textContent = "";
        const aviso = document.createElement("div");
        aviso.style.cssText = "font-size: 8.5pt; color: #94A3B8;";
        aviso.textContent = `⚠️ La bóveda 3NF no declara casillas para el concurso activo (fuente: ${(slate && slate.sesgo_fuente) || "SIN_BOVEDA"}). No se fabrican casillas ni probabilidades.`;
        cont.appendChild(aviso);
        return;
    }

    const fmtP = (v) => (v === null || v === undefined) ? "—" : `${(Number(v) * 100).toFixed(1)}%`;

    const filas = items.map(it => {
        const p = it.p_qbe || {};
        const badge = it.es_prior_ignorancia
            ? '<span class="badge-status-live" style="background:rgba(148,163,184,0.15); color:#cbd5e1; border-color:#64748B;">Prior Base (1/3)</span>'
            : '<span class="badge-status-live" style="background:rgba(0,230,118,0.15); color:#00E676; border-color:#00E676;">Soberano 3NF</span>';
        return `
            <tr>
                <td style="text-align:center; font-weight:800; color:#38BDF8;">${it.order}</td>
                <td style="text-align:center; font-size:7.5pt; color:#94A3B8;">${it.tipo_concurso || "—"}</td>
                <td style="font-weight:700; color:#fff;">${it.local || "—"}</td>
                <td style="font-weight:700; color:#fff;">${it.visitante || "—"}</td>
                <td style="text-align:center;">${fmtP(p.L)}</td>
                <td style="text-align:center;">${fmtP(p.E)}</td>
                <td style="text-align:center;">${fmtP(p.V)}</td>
                <td style="text-align:center;">${badge}</td>
                <td style="text-align:center;">${_badgeSesgoProgol(it)}</td>
            </tr>`;
    }).join("");

    cont.innerHTML = `
        <table class="fintech-table" style="width: 100%; font-size: 8.5pt;">
            <thead>
                <tr>
                    <th>#</th><th>Bloque</th><th>Local</th><th>Visitante</th>
                    <th>P(1)</th><th>P(X)</th><th>P(2)</th><th>Origen</th><th>Sesgo público</th>
                </tr>
            </thead>
            <tbody>${filas}</tbody>
        </table>`;
}

/** [GOVERNANCE-01] El sesgo sólo se declara con captura fáctica de momios públicos de la jornada. */
function _badgeSesgoProgol(it) {
    const motivo = it.sesgo_motivo || "";
    if (!it.sesgo_disponible) {
        return `<span style="font-size:7.2pt; color:#64748B;" title="${motivo}">Venta pública no ingesta</span>`;
    }
    const s = it.analisis_sesgo || {};
    const pct = (v) => `${(Number(v || 0) * 100).toFixed(1)}%`;
    const detalle = `Sesgo L ${pct(s.sesgo_local)} · X ${pct(s.sesgo_empate)} · V ${pct(s.sesgo_visitante)}`;
    if (s.alerta_sesgo) {
        return `<span class="badge-status-live" style="background:rgba(245,158,11,0.15); color:#F59E0B; border-color:#F59E0B;" title="${detalle}">⚠️ ${s.recomendacion_cobertura || "Sesgo popular"}</span>`;
    }
    return `<span style="font-size:7.2pt; color:#00E676;" title="${detalle}">${s.recomendacion_cobertura || "Sin sesgo explotable"}</span>`;
}

/** Ejecuta el optimizador combinatorio del backend (Costo = 15.00 × 2^D × 3^T ≤ presupuesto). */
async function ejecutarOptimizadorProgol() {
    const cont = document.getElementById("progol-resultado-optimizador");
    const input = document.getElementById("input-progol-presupuesto");
    if (!cont) return;

    const presupuesto = parseFloat(input ? input.value : "");
    if (!Number.isFinite(presupuesto) || presupuesto < 15.0) {
        cont.style.display = "block";
        cont.textContent = "";
        const aviso = document.createElement("div");
        aviso.style.cssText = "font-size: 8.5pt; color: #F87171;";
        aviso.textContent = "⚠️ El presupuesto mínimo aceptado es $15.00 MXN (invariante del request schema ProgolOptimizeRequest).";
        cont.appendChild(aviso);
        return;
    }

    cont.style.display = "block";
    cont.textContent = "";
    const carga = document.createElement("div");
    carga.style.cssText = "font-size: 8.5pt; color: #38BDF8;";
    carga.textContent = "⚡ Optimizando cobertura 2^D × 3^T sobre la bóveda 3NF…";
    cont.appendChild(carga);

    try {
        const resp = await fetch("/api/markets/progol/optimize", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                slate_id: currentProgolSlate ? currentProgolSlate.slate_id : null,
                presupuesto_mxn: presupuesto
            })
        });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        _renderResultadoOptimizadorProgol(await resp.json());
    } catch (e) {
        console.error("Fallo optimizando Progol:", e);
        cont.textContent = "";
        const error = document.createElement("div");
        error.style.cssText = "font-size: 8.5pt; color: #F87171;";
        error.textContent = `⚠️ Sin concurso optimizable en la bóveda 3NF (${e.message}). Cero matrices se muestran sin respaldo.`;
        cont.appendChild(error);
    }
}

/** [D-3] Renderiza la matriz con las claves FÁCTICAS del plano (progol_math.py:156-162). */
function _renderResultadoOptimizadorProgol(data) {
    const cont = document.getElementById("progol-resultado-optimizador");
    if (!cont || !data) return;

    const matriz = data.matriz_quiniela || [];
    const casilla = (jugada, etiqueta) => jugada
        ? `<span style="color:#38BDF8; font-weight:900;" title="Se juega ${etiqueta}">●</span>`
        : '<span style="color:#334155;">·</span>';

    if (matriz.length === 0) {
        cont.textContent = "";
        const aviso = document.createElement("div");
        aviso.style.cssText = "font-size: 8.5pt; color: #94A3B8;";
        aviso.textContent = "⚠️ El optimizador no devolvió matriz de casillas: la bóveda 3NF no expone el bloque REGULAR del concurso.";
        cont.appendChild(aviso);
        return;
    }

    const filas = matriz.map(row => `
        <tr>
            <td style="text-align:center; font-weight:800; color:#38BDF8;">${row.order}</td>
            <td style="font-weight:700; color:#fff;">${row.local || "—"} vs ${row.visitante || "—"}</td>
            <td style="text-align:center;">${casilla(row.juega_L, "1")}</td>
            <td style="text-align:center;">${casilla(row.juega_E, "X")}</td>
            <td style="text-align:center;">${casilla(row.juega_V, "2")}</td>
            <td style="font-size:7.5pt; color:#cbd5e1;">${row.recomendacion || "—"}</td>
            <td style="text-align:center;">${row.alerta_sesgo ? "⚠️" : "—"}</td>
        </tr>`).join("");

    // [ARCH-1.4.20 / VAULT-CORE-084-PROGOL-P-PRIME] Bloque aditivo del motor soberano de masa
    // acumulada P': despliega las boletas priorizadas por maximización de C(M) y su garantía
    // fiduciaria declarada por el backend. Sólo formatea claves ya calculadas por el motor.
    const boletasP = data.boletas || [];
    const bloqueMotorSoberano = boletasP.length === 0 ? "" : `
        <div style="margin-top: 12px; border-top: 1px solid #1E293B; padding-top: 10px;">
            <span style="font-size: 7.2pt; color: #00E676; text-transform: uppercase; font-weight: 800;">Motor de Masa Acumulada P' · ${data.motor || "PROGOL_P_PRIME_MASS"}</span>
            <div style="font-size: 8pt; color: #CBD5E1; margin: 4px 0 6px 0;">
                Garantía fiduciaria: <b style="color:#fff;">${data.garantia_fiduciaria || "—"}</b> ·
                Masa acumulada capturada: <b style="color:#fff;">${Number(data.masa_acumulada_capturada || 0).toExponential(3)}</b>
            </div>
            <div style="display: flex; flex-wrap: wrap; gap: 6px;">
                ${boletasP.map(b => `<span style="font-family: monospace; font-size: 7.5pt; color: #38BDF8; background: rgba(56,189,248,0.08); border: 1px solid #1E293B; border-radius: 4px; padding: 2px 6px;" title="Boleta #${b.boleta_id} · P' = ${Number(b.prob_conjunta || 0).toExponential(3)}">#${b.boleta_id} ${(b.combinacion || []).join("")}</span>`).join("")}
            </div>
        </div>`;

    cont.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 10px; margin-bottom: 10px;">
            <div>
                <span style="font-size: 7.2pt; color: #38BDF8; text-transform: uppercase; font-weight: 800;">Matriz de Quiniela Optimizada</span>
                <h3 style="margin: 2px 0 0 0; font-size: 1.05rem; color: #fff;">${data.combinaciones_totales} combinaciones · ${data.dobles_asignados} dobles · ${data.triples_asignados} triples</h3>
            </div>
            <div style="text-align: right;">
                <span style="font-size: 7pt; color: #94A3B8; text-transform: uppercase;">Costo real del boleto</span>
                <div style="font-size: 1.15rem; font-weight: 900; color: #00E676;">$${Number(data.costo_total_mxn || 0).toFixed(2)} MXN</div>
            </div>
        </div>
        <table class="fintech-table" style="width: 100%; font-size: 8.5pt;">
            <thead>
                <tr><th>#</th><th>Partido</th><th>1</th><th>X</th><th>2</th><th>Recomendación</th><th>Sesgo</th></tr>
            </thead>
            <tbody>${filas}</tbody>
        </table>${bloqueMotorSoberano}`;
}

// ═══════════════════════════════════════════════════════════════════════════════
// [DES-QBE-045 cláusula 4] ADAPTADOR AUTÁRQUICO DEL LIVE BOARD HACIA LA RADIOGRAFÍA
// Sólo se escriben claves sobre hechos presentes en el fixture (SovereignDistribution +
// momios 1X2). Si un dato no existe, la clave no se crea: cero cifras inventadas.
// ═══════════════════════════════════════════════════════════════════════════════

function _adaptarFixtureARadiografia(f) {
    const num = (v) => (v === null || v === undefined || v === "") ? null : Number(v);
    const etiqueta = `${f.local || "—"} vs ${f.visitante || "—"}`;
    const momios = f.momios || {};

    const p = {
        id_partido: f.id_partido,
        partido: etiqueta,
        partido_nombre: etiqueta,
        origen_datos: "LIVE_BOARD_SOBERANO"
    };

    // Tabla Pronóstico vs Mercado: soberana persistida contra el momio 1X2 del fixture.
    const claves = [
        { clave: "L", resultado: f.local || "Local", soberana: num(f.p_local) },
        { clave: "E", resultado: "Empate", soberana: num(f.p_empate) },
        { clave: "V", resultado: f.visitante || "Visitante", soberana: num(f.p_visitante) }
    ];
    const filas = [];
    claves.forEach(({ clave, resultado, soberana }) => {
        if (soberana === null) return;
        const momio = num(momios[clave]);
        const probCasino = (momio !== null && momio > 0) ? (1.0 / momio) * 100.0 : null;
        const probReal = soberana * 100.0;
        filas.push({
            resultado: resultado,
            prob_real: probReal,
            momio: momio,
            prob_casino: probCasino,
            edge: (probCasino === null) ? 0.0 : probReal - probCasino
        });
    });
    if (filas.length > 0) p.probabilidades_3vias = filas;

    // Poisson Boxes: lambdas persistidos; el total es la suma aritmética y sólo si ambos existen.
    const lambdaLocal = num(f.lambda_home);
    const lambdaVisita = num(f.lambda_away);
    if (lambdaLocal !== null) p.lambda_local = lambdaLocal;
    if (lambdaVisita !== null) p.mu_visita = lambdaVisita;
    if (lambdaLocal !== null && lambdaVisita !== null) p.xg_total = lambdaLocal + lambdaVisita;
    const phiLead2 = num(f.phi_lead2_home);
    if (phiLead2 !== null) p.phi_lead2_pct = phiLead2 * 100.0;

    // [LN-QBE-098] Passthrough soberano para el comparador de 6 columnas del modal:
    // favorito, consenso des-marginado y localía, ya presentes en el Live Board.
    p.fav_name = f.fav_name || null;
    p.horario = f.horario || null;
    if (typeof f.is_fav_local === "boolean") p.is_fav_local = f.is_fav_local;
    if (f.consenso_mercado) p.consenso_mercado = f.consenso_mercado;
    if (f.estrategia_codigo) p.estrategia_codigo = f.estrategia_codigo;
    if (f.strategy_code) p.strategy_code = f.strategy_code;

    return p;
}

// ══════════════════════════════════════════════════════════════════════════════
// [DES-QBE-048 / ARCH-1.4.12] CENTRO DE CONTROL — DESPACHO GOBERNADO DE TAREAS
// El cliente SÓLO transmite el identificador certificado: el servidor resuelve la
// whitelist estricta y materializa el comando (cero texto libre, cero inyección).
// ══════════════════════════════════════════════════════════════════════════════

function bloquearBotonesAdmin(congelado) {
    document.querySelectorAll('.cc-task-btn, .cc-btn-master').forEach(btn => {
        btn.disabled = !!congelado;
    });
}

async function ejecutarTareaAdmin(taskId) {
    const identificador = String(taskId || '').trim();
    if (!identificador) return;

    const consola = document.getElementById('terminal-stream-output');
    const meta = document.getElementById('cc-terminal-meta');
    const badge = document.getElementById('cc-estado');

    bloquearBotonesAdmin(true);
    if (badge) {
        badge.className = 'cc-badge cc-badge-running';
        badge.textContent = `● En ejecución: ${identificador}`;
    }
    if (meta) meta.textContent = `tarea: ${identificador} · exit: en curso · duración: —`;
    if (consola) consola.textContent = `[SISTEMA] Despachando tarea '${identificador}'...\n`;

    try {
        const resp = await fetch('/api/admin/tasks/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_id: identificador })
        });

        if (!resp.ok) {
            throw new Error(`HTTP ${resp.status} — ${await resp.text()}`);
        }

        const data = await resp.json();
        const salidaTexto = (data.output && data.output.length) ? data.output : '[SISTEMA] La tarea no emitió salida estándar.';

        // [GOVERNANCE-01] La salida se pinta como TEXTO PLANO: la consola nunca interpreta HTML.
        if (consola) {
            consola.textContent = salidaTexto;
            consola.scrollTop = consola.scrollHeight;
        }

        const exito = Number(data.exit_code) === 0;
        if (badge) {
            badge.className = `cc-badge ${exito ? 'cc-badge-ok' : 'cc-badge-fail'}`;
            badge.textContent = `${exito ? '✔ Completada' : '✖ Fallida'}: ${identificador}`;
        }
        if (meta) meta.textContent = `tarea: ${identificador} · exit: ${data.exit_code} · duración: ${data.duration_s}s`;
    } catch (e) {
        console.error('Fallo despachando tarea administrativa:', e);
        if (badge) {
            badge.className = 'cc-badge cc-badge-fail';
            badge.textContent = `✖ Error de despacho: ${identificador}`;
        }
        if (meta) meta.textContent = `tarea: ${identificador} · exit: — · duración: —`;
        if (consola) consola.textContent = `[ERROR] Despacho fallido: ${e.message}`;
    } finally {
        bloquearBotonesAdmin(false);
        // [ARCH-1.4.12-B] Toda mutación de fuentes re-sondea el semáforo: la pantalla jamás
        // exhibe un veredicto caduco tras un despacho.
        cargarEstadoDriftCentroControl();
    }
}

// ══════════════════════════════════════════════════════════════════════════════
// [ARCH-1.4.12-B] SEMÁFORO DE DERIVA Y FRESCURA DE FUENTES (SONDA READ-ONLY)
// El cliente NO calcula deriva: consume `GET /api/admin/status/drift` (cuatro luces
// certificadas por el motor: [ARCH-1.4.34] + [ARCH-1.6.2-B] + umbral de 45 min) y sólo
// PINTA el veredicto. [GOVERNANCE-01] Cero umbral ni cifra inventada en la pantalla.
// ══════════════════════════════════════════════════════════════════════════════

const DIMENSIONES_DRIFT = ['mercado', 'deportivo', 'progol', 'integridad'];
const CLASE_NIVEL_DRIFT = {
    CONFORME: 'cc-drift-ok',
    ADVERTENCIA: 'cc-drift-warn',
    DISCREPANCIA: 'cc-drift-fail',
    SIN_VEREDICTO: 'cc-drift-unknown'
};

function _pintarDimensionDrift(dimension, estado) {
    const contenedor = document.getElementById(`drift-luz-${dimension}`);
    const glifo = document.getElementById(`drift-glifo-${dimension}`);
    const detalle = document.getElementById(`drift-detalle-${dimension}`);
    const nivel = (estado && estado.nivel) ? String(estado.nivel) : 'SIN_VEREDICTO';
    if (glifo) glifo.textContent = (estado && estado.glifo) ? estado.glifo : '⚪';
    if (detalle) detalle.textContent = (estado && estado.detalle) ? estado.detalle : 'Sin lectura del motor.';
    if (contenedor) {
        Object.values(CLASE_NIVEL_DRIFT).forEach((clase) => contenedor.classList.remove(clase));
        contenedor.classList.add(CLASE_NIVEL_DRIFT[nivel] || CLASE_NIVEL_DRIFT.SIN_VEREDICTO);
        contenedor.setAttribute('title', `${nivel} — ${(estado && estado.detalle) ? estado.detalle : ''}`);
    }
}

function pintarSemaforoDrift(data) {
    if (!data) return;

    const etiquetaJornada = document.getElementById('drift-jornada');
    if (etiquetaJornada) {
        const jornada = data.jornada_activa;
        etiquetaJornada.textContent = (jornada === null || jornada === undefined) ? '—' : jornada;
    }
    const regimen = document.getElementById('drift-regimen');
    if (regimen) regimen.textContent = `${String(data.regimen || 'SOLO_LECTURA').toLowerCase()} · cuatro luces`;

    DIMENSIONES_DRIFT.forEach((dimension) => {
        _pintarDimensionDrift(dimension, data[`status_${dimension}`]);
    });

    const texto = document.getElementById('drift-accion-texto');
    const boton = document.getElementById('btn-drift-accion');
    const accion = data.accion_recomendada || {};
    const tarea = accion.task_id ? String(accion.task_id) : '';

    if (texto) texto.textContent = `[SISTEMA] ${accion.motivo ? accion.motivo : 'Semáforo sin veredicto.'}`;
    if (boton) {
        if (tarea) {
            boton.style.display = '';
            boton.textContent = `▶ Ejecutar Acción Recomendada: ${tarea}`;
            boton.setAttribute('data-task-id', tarea);
            boton.title = `Ejecuta la tarea certificada '${tarea}' recomendada por la sonda de deriva (siempre perteneciente a la whitelist [ARCH-1.4.12]).`;
        } else {
            boton.style.display = 'none';
            boton.removeAttribute('data-task-id');
        }
    }
}

// [ARCH-1.4.12-B] Narración del sondeo en la Terminal de Streaming (Decreto
// `VAR-2026-DRIFT-STREAM-MAP`): los cuatro pasos del diagnóstico se narran con sello de reloj.
// La consola monospaciada de la vista es `#terminal-stream-output` (contrato `[DES-QBE-048]`):
// cero salida silenciosa y cero interpretación de HTML (`[GOVERNANCE-01]`: texto plano).
function logDriftTerminal(msg) {
    const term = document.getElementById('terminal-stream-output');
    if (!term) return;
    const hora = new Date().toLocaleTimeString('es-MX', { hour12: false });
    term.textContent += `\n[${hora}] ${msg}`;
    term.scrollTop = term.scrollHeight;
}

// Guion literal del sondeo: los 4 pasos del diagnóstico de [ARCH-1.4.12-B].
const PASOS_SONDEO_DRIFT = [
    '📡 [DERIVA] Iniciando escaneo de frescura de fuentes en SQLite 3NF...',
    '⏳ [1/4] Sondeando timestamps de cuotas (Caliente / Novibet / Betway)...',
    '⏳ [2/4] Verificando horarios y marcadores en bóveda...',
    '⏳ [3/4] Verificando concurso oficial Progol...',
    '⏳ [4/4] Auditando integridad de cartelera...'
];

// Lee el nivel REAL del contrato REST (`.nivel`) y degrada honestamente a `SIN_VEREDICTO` si el
// payload llegara incompleto (cero veredicto inventado en el cliente: `[GOVERNANCE-01]`).
function _nivelDrift(dimension) {
    return (dimension && dimension.nivel) ? String(dimension.nivel) : 'SIN_VEREDICTO';
}

async function cargarEstadoDriftCentroControl() {
    const texto = document.getElementById('drift-accion-texto');
    PASOS_SONDEO_DRIFT.forEach((paso) => logDriftTerminal(paso));
    if (texto) texto.textContent = '[SISTEMA] Analizando integridad y vigencia...';
    try {
        const resp = await fetch('/api/admin/status/drift', { headers: { 'Accept': 'application/json' } });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        pintarSemaforoDrift(data);

        // Cierre de la narración: veredicto agregado (campos reales `.nivel` / `.motivo`).
        logDriftTerminal('🏁 [DERIVA] Diagnóstico concluido en tiempo récord.');
        logDriftTerminal(`🚦 Veredicto: Mercado (${_nivelDrift(data.status_mercado)}) · Deportivo (${_nivelDrift(data.status_deportivo)}) · Progol (${_nivelDrift(data.status_progol)}) · Integridad (${_nivelDrift(data.status_integridad)})`);
        if (data.accion_recomendada && data.accion_recomendada.motivo) {
            logDriftTerminal(`⚡ Acción sugerida: ${data.accion_recomendada.motivo}`);
        }
    } catch (e) {
        console.error('Fallo sondeando el semáforo de deriva:', e);
        logDriftTerminal(`❌ [DERIVA] Sonda inaccesible: ${e.message}`);
        if (texto) texto.textContent = `[ERROR] Sonda de deriva inaccesible: ${e.message}`;
    }
}

document.addEventListener('DOMContentLoaded', function () {
    const botonAccion = document.getElementById('btn-drift-accion');
    if (botonAccion) {
        botonAccion.addEventListener('click', function () {
            const tarea = botonAccion.getAttribute('data-task-id');
            if (tarea) ejecutarTareaAdmin(tarea);
        });
    }
    const botonRefresco = document.getElementById('btn-drift-refresco');
    if (botonRefresco) {
        botonRefresco.addEventListener('click', function () { cargarEstadoDriftCentroControl(); });
    }

    // Hidratación inicial de la sonda: jamás bloquea el render del Live Board.
    cargarEstadoDriftCentroControl();
});

window.cargarEstadoDriftCentroControl = cargarEstadoDriftCentroControl;
window.pintarSemaforoDrift = pintarSemaforoDrift;

window.ejecutarTareaAdmin = ejecutarTareaAdmin;
window.bloquearBotonesAdmin = bloquearBotonesAdmin;

window.conmutarSubvistaMercados = conmutarSubvistaMercados;
window.cargarSlateProgolActivo = cargarSlateProgolActivo;
window.ejecutarOptimizadorProgol = ejecutarOptimizadorProgol;

// Arranque de la SPA: se hidrata el concurso Progol vigente sin bloquear el render del Live Board.
document.addEventListener("DOMContentLoaded", function () {
    cargarSlateProgolActivo();
});

// ─── [ARCH-1.4.35] Cableado del Conmutador de Slates (Doble Seguro del Director) ─────────────
// 🔒/🔓 `#btn-lock-jornada` conmuta la ventanilla (viva ⇄ backtesting) y `#select-jornada` sólo
// re-expone la cartelera congelada si el candado está ABIERTO; con el candado cerrado el selector
// está inhabilitado (doble seguro contra el congelamiento accidental de la mesa).
document.addEventListener("DOMContentLoaded", function () {
    const btnLock = document.getElementById('btn-lock-jornada');
    if (btnLock) btnLock.addEventListener('click', function () { conmutarCandadoJornada(); });

    const selJornada = document.getElementById('select-jornada');
    if (selJornada) {
        selJornada.addEventListener('change', function () {
            if (esModoBacktestingJornada()) cargarCarteleraJornada(_jornadaSeleccionadaConmutador());
        });
    }

    // Estado inicial legislado: candado CERRADO (ventanilla viva, jornada dinámica [ARCH-1.6.15]).
    _pintarEstadoConmutadorJornada();
    hidratarConmutadorJornadas();
});

window.conmutarCandadoJornada = conmutarCandadoJornada;
window.cargarCarteleraJornada = cargarCarteleraJornada;
window.hidratarConmutadorJornadas = hidratarConmutadorJornadas;

// ─── [ARCH-1.4.37 / LN-QBE-077-B / ARCH-1.4.12-C] Cableado del Tríptico de Cobertura (δ) ──────
// `state.modo_cobertura` es la ÚNICA fuente de verdad del modo declarado; la clase `active` y los
// estilos de resalte se RE-DERIVAN de ese estado (cero estado duplicado ni divergente en el DOM).
// Default legislado vigente: `BAL` (Balanceado +15%), modo de cobertura por omisión de la Mesa de
// Apuestas ([ARCH-1.4.12-C]); `DEF` (paridad bit a bit con el contrato V=0 de [LN-QBE-070])
// subsiste como contrato sellado seleccionable.
document.addEventListener("DOMContentLoaded", function () {
    const botonesCobertura = document.querySelectorAll("#toggle-modo-cobertura .btn-cobertura");
    if (!botonesCobertura.length) return;
    const COBERTURA_ACTIVA = { background: "#1E293B", border: "1px solid #38BDF8", color: "#38BDF8" };
    const COBERTURA_INACTIVA = { background: "#0F172A", border: "1px solid #334155", color: "#94A3B8" };
    const _pintarCobertura = () => {
        botonesCobertura.forEach((boton) => {
            const esActivo = boton.getAttribute("data-modo") === state.modo_cobertura;
            boton.classList.toggle("active", esActivo);
            const estilo = esActivo ? COBERTURA_ACTIVA : COBERTURA_INACTIVA;
            boton.style.background = estilo.background;
            boton.style.border = estilo.border;
            boton.style.color = estilo.color;
        });
    };
    botonesCobertura.forEach((boton) => {
        boton.addEventListener("click", () => {
            // [ARCH-1.4.12-C] Fallback defensivo = default legislado de la Mesa (`BAL`): un botón
            // sin `data-modo` jamás degrada la ventanilla al contrato sellado por accidente.
            state.modo_cobertura = boton.getAttribute("data-modo") || "BAL";
            _pintarCobertura();
        });
    });
    _pintarCobertura();
});



// ── [LN-QBE-100 / ARCH-1.4.38] VISOR DE BACKTESTING (CALIBRACIÓN FACTUAL DE TEMPORADA) ──
let backtestingReportCache = null;
// [LN-QBE-104 · DES-QBE-067] Último universo EFECTIVO pintado (payload servido tras el filtro
// anti-cuarentena). La caché `backtestingReportCache` permanece intacta: el filtro es de
// presentación y jamás muta la evidencia recibida de la bóveda.
let backtestingUniversoActual = null;

// ── [DES-QBE-068 / DES-QBE-069 / LN-QBE-114] VISOR FINANCIERO DEL MODO LABORATORIO ──────────
// El candado abierto declara el alcance (jornada o temporada completa) y el veto fiduciario; el
// botón primario delega en `POST /api/markets/backtesting/simulate`. CERO aritmética financiera
// en el cliente: KPIs, curva y tabla meso se TRANSCRIBEN del reporte sellado ([LN-QBE-107]).
let _ultimaSimulacionRentabilidad = null;
let _equityChart = null;
let _panelBacktestingActivo = "panel-visor-factico";

function esSimulacionTemporada() {
    const sel = document.getElementById("select-jornada");
    return !!sel && sel.value === VALOR_TEMPORADA;
}

function _valoresJornadaDeclarados() {
    const sel = document.getElementById("select-jornada");
    if (!sel) return [];
    return Array.from(sel.options)
        .map(op => parseInt(op.value, 10))
        .filter(Number.isFinite);
}

/** Rótulo del centinela derivado de las jornadas REALES de la bóveda (cero rango quemado). */
function _rangoTemporadaEtiqueta() {
    const valores = _valoresJornadaDeclarados();
    if (!valores.length) return "Toda la Temporada";
    return `Toda la Temporada (J${Math.min(...valores)}-J${Math.max(...valores)})`;
}

/** Inyecta/retira el centinela `temporada` según el estado del candado (idempotente). */
function _sincronizarOpcionTemporada() {
    const sel = document.getElementById("select-jornada");
    if (!sel) return;
    const existente = Array.from(sel.options).find(op => op.value === VALOR_TEMPORADA);

    if (!esModoBacktestingJornada()) {
        if (existente) existente.remove();
        if (sel.value === VALOR_TEMPORADA) {
            const activa = _jornadaActivaDelConmutador();
            if (activa !== null) sel.value = activa;
        }
        return;
    }
    if (existente) {
        existente.textContent = `📊 ${_rangoTemporadaEtiqueta()}`;
        return;
    }
    const opcion = document.createElement("option");
    opcion.value = VALOR_TEMPORADA;
    opcion.textContent = `📊 ${_rangoTemporadaEtiqueta()}`;
    sel.insertBefore(opcion, sel.firstChild);
}

/** Rango declarado para el motor: `min-max` en temporada completa, `N` en jornada única. */
function _rangoSimulacionSeleccionado() {
    if (esSimulacionTemporada()) {
        const valores = _valoresJornadaDeclarados();
        if (!valores.length) {
            throw new Error("La bóveda 3NF no declara jornadas: prohibido inventar un rango");
        }
        const desde = Math.min(...valores);
        const hasta = Math.max(...valores);
        return desde === hasta ? String(desde) : `${desde}-${hasta}`;
    }
    const jornada = _jornadaSeleccionadaConmutador();
    if (!Number.isFinite(jornada)) {
        throw new Error("Selecciona una jornada válida o «Toda la Temporada»");
    }
    return String(jornada);
}

function _actualizarAlcanceSimulacion() {
    const span = document.getElementById("txt-alcance-simulacion");
    if (!span) return;
    if (esSimulacionTemporada()) {
        span.textContent = `Alcance: ${_rangoTemporadaEtiqueta()} · modo compuesto`;
        return;
    }
    const jornada = _jornadaSeleccionadaConmutador();
    span.textContent = Number.isFinite(jornada)
        ? `Alcance: Jornada ${jornada} · modo compuesto`
        : "Alcance: jornada seleccionada";
}

function _fmtMxn(valor) {
    const n = Number(valor);
    if (!Number.isFinite(n)) return "--";
    return new Intl.NumberFormat("es-MX", {
        style: "currency",
        currency: "MXN",
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    }).format(n);
}


/** Router del botón primario: candado cerrado ⇒ ventanilla viva; abierto ⇒ laboratorio. */
async function iniciarSimulacionRentabilidad() {
    if (!esModoBacktestingJornada()) {
        return ejecutarDespachoPortafolio();
    }

    const bankrollInput = document.getElementById("input-bankroll") || document.getElementById("bankroll-input");
    const bankrollParsed = bankrollInput ? parseFloat(bankrollInput.value) : NaN;
    const bankroll = Number.isFinite(bankrollParsed) && bankrollParsed > 0
        ? bankrollParsed
        : DEFAULTS_CARTERA.bankroll;

    let rango;
    try {
        rango = _rangoSimulacionSeleccionado();
    } catch (e) {
        alert(`❌ ${e.message}`);
        return;
    }

    const excluir = [];
    const casillaFamiliaR = document.getElementById("chk-excluir-familia-r");
    if (casillaFamiliaR && casillaFamiliaR.checked) excluir.push("QBE-R1", "QBE-R2");

    // ── [ARCH-1.4.53 / LN-QBE-115] Parámetros gobernantes del laboratorio ────────────────────
    // Γ (Concentración de Masa de Capa 0), Slider de Certeza §5.10 y modo de cobertura δ viajan
    // VERBATIM desde la ventanilla hacia `POST /api/markets/backtesting/simulate`. Cero
    // aritmética en el cliente: la banda de la Trinidad de Certeza y el δ efectivo los resuelve
    // el motor como pass-through puro ([LN-QBE-114]). Los nombres de llave son los LEGISLADOS en
    // `SimulatePortfolioRequest` (`gamma_slider`, `target_certeza_pct`, `modo_cobertura`): el DTO
    // declara `extra="ignore"`, de modo que una llave mal nombrada se descartaría en silencio.
    //
    // Unidades: `target_certeza_pct` es PORCENTAJE (0.0-100.0) — a diferencia del
    // `target_certeza` fraccionario (0.80) de la ventanilla viva. Prohibido reutilizar el factor
    // de normalización de esa ruta.
    //
    // Γ: tri-estado `input[name="opcion_gamma"]` (67% | 70% | 75%). Fallback = default legislado
    // de la UI `DEFAULTS_CARTERA.gamma` (0.70, [DICTAMEN DIRECTOR 2026-10-11]): pantalla y motor
    // jamás divergen si el grupo de radios quedara sin marcar.
    const gammaSeleccionado = parseFloat(
        document.querySelector('input[name="opcion_gamma"]:checked')?.value ||
        String(DEFAULTS_CARTERA.gamma)
    );
    // Certeza: `#slider-risk-certainty` publica el porcentaje ya escalado (70-90) + display
    // `#certainty-val`. Se transporta el valor tal cual, sin normalizar a fracción.
    const certezaSlider = document.getElementById("slider-risk-certainty");
    const certezaParsed = certezaSlider ? parseFloat(certezaSlider.value) : NaN;
    const certezaSeleccionada = Number.isFinite(certezaParsed)
        ? certezaParsed
        : CERTEZA_PCT_DEFAULT;
    // Cobertura: `state.modo_cobertura` es la ÚNICA fuente de verdad del tríptico (clase `active`
    // y estilos re-derivados de él, [ARCH-1.4.12-C]). Guarda contra valores fuera del dominio
    // legislado `DEF|BAL|AGR`: degradación al default de la Mesa (`BAL`).
    const MODO_COBERTURA_DEFAULT = "BAL";
    const modoCoberturaSeleccionado = MODOS_COBERTURA_VALIDOS.includes(state.modo_cobertura)
        ? state.modo_cobertura
        : MODO_COBERTURA_DEFAULT;

    const estado = document.getElementById("bt-financiero-estado");
    const boton = document.getElementById("btn-calcular-cartera");
    if (boton) boton.disabled = true;
    if (estado) {
        estado.textContent = `Simulando J${rango} sobre la bóveda 3NF · Γ ${gammaSeleccionado.toFixed(2)} · ` +
            `Certeza ${certezaSeleccionada.toFixed(1)}% · Cobertura ${modoCoberturaSeleccionado}… ` +
            (excluir.length ? `veto activo: ${excluir.join(", ")}.` : "sin exclusiones fiduciarias.");
    }

    try {
        const resp = await fetch("/api/markets/backtesting/simulate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                bankroll_inicial: bankroll,
                rango_jornadas: rango,
                modo_interes: "compuesto",
                // [LN-QBE-113] El veto lo ejecuta el motor: la UI sólo declara la intención.
                excluir_estrategias: excluir,
                // [ARCH-1.4.53 / LN-QBE-115] Pass-through VERBATIM de los parámetros gobernantes.
                // Nombres LEGISLADOS del DTO: `extra="ignore"` descartaría en silencio cualquier
                // alias (`gamma`, `target_certeza`) y el motor volvería a sus defaults.
                gamma_slider: gammaSeleccionado,
                target_certeza_pct: certezaSeleccionada,
                modo_cobertura: modoCoberturaSeleccionado,
            }),
        });
        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${resp.status}`);
        }
        const data = await resp.json();
        _ultimaSimulacionRentabilidad = data;
        pintarPanelFinanciero(data);
        switchView("panel-visor-backtesting");
        activarSubPanelBacktesting("panel-visor-financiero");
        // La auditoría fáctica queda disponible sin tráfico extra si ya fue certificada.
        if (!backtestingReportCache) cargarVisorBacktesting();
    } catch (e) {
        if (estado) {
            estado.textContent = `⚠️ Simulación no disponible: ${e.message}. ` +
                "Cero cifras se exhiben sin respaldo del motor.";
        }
        alert(`❌ Error en la simulación de rentabilidad: ${e.message}`);
    } finally {
        if (boton) boton.disabled = false;
    }
}


/** Transcribe el estado de resultados certificado. Prohibido recalcular una sola cifra. */
function pintarPanelFinanciero(data) {
    if (!data) return;
    const set = (id, texto) => {
        const el = document.getElementById(id);
        if (el) el.textContent = texto;
    };
    const pnl = Number(data.pnl_acumulado);
    const roi = Number(data.roi_acumulado_pct);
    const drawdownPct = Number(data.drawdown_maximo_pct);
    const drawdownMxn = Number(data.drawdown_maximo_mxn);
    const jornadasSolicitadas = Array.isArray(data.jornadas_solicitadas) ? data.jornadas_solicitadas : [];
    const exclusiones = Array.isArray(data.exclusiones_activas) ? data.exclusiones_activas : [];

    const pintarSigno = (id, valor) => {
        const el = document.getElementById(id);
        if (!el) return;
        el.classList.remove("bt-valor-positivo", "bt-valor-negativo");
        if (Number.isFinite(valor)) el.classList.add(valor >= 0 ? "bt-valor-positivo" : "bt-valor-negativo");
    };

    set("kpi-fin-bankroll", _fmtMxn(data.bankroll_final));
    set("kpi-fin-bankroll-detalle",
        `Inicial ${_fmtMxn(data.bankroll_inicial)} · ` +
        `${data.jornadas_con_cartera || 0} de ${jornadasSolicitadas.length} jornadas con cartera`);
    set("kpi-fin-pnl", `${Number.isFinite(pnl) && pnl > 0 ? "+" : ""}${_fmtMxn(pnl)}`);
    pintarSigno("kpi-fin-pnl", pnl);
    set("kpi-fin-pnl-detalle",
        `${data.posiciones_operables || 0} posiciones operables · ` +
        `${data.vetos_aplicados || 0} vetos fiduciarios`);
    set("kpi-fin-roi", `${Number.isFinite(roi) ? roi.toFixed(2) : "--"}%`);
    pintarSigno("kpi-fin-roi", roi);
    set("kpi-fin-roi-detalle", `Modo ${data.modo || "--"} · ${data.modo_descripcion || "sin descripción"}`);
    set("kpi-fin-drawdown", `${Number.isFinite(drawdownPct) ? drawdownPct.toFixed(2) : "--"}%`);
    set("kpi-fin-drawdown-detalle",
        `Máximo ${_fmtMxn(drawdownMxn > 0 ? -Math.abs(drawdownMxn) : 0)}` +
        (data.jornada_drawdown_maximo ? ` · J${data.jornada_drawdown_maximo}` : " · sin pico declarado"));

    const estado = document.getElementById("bt-financiero-estado");
    if (estado) {
        const veto = exclusiones.length
            ? `Veto fiduciario activo: ${exclusiones.join(", ")} (${data.vetos_aplicados || 0} intercepciones).`
            : "Sin exclusiones fiduciarias declaradas.";
        const primera = jornadasSolicitadas.length ? jornadasSolicitadas[0] : "--";
        const ultima = jornadasSolicitadas.length ? jornadasSolicitadas[jornadasSolicitadas.length - 1] : "--";
        // [ARCH-1.4.53 / LN-QBE-115] TRANSCRIPCIÓN del bloque `parametros_simulacion` que sella el
        // motor: certifica en pantalla que Γ, la banda de la Trinidad de Certeza y el δ efectivo
        // fueron los despachados (paridad estricta backend↔pantalla, [GOVERNANCE-01]). Cero
        // recálculo: si la llave falta, se degrada a `--` sin inventar un valor.
        const parametros = data.parametros_simulacion || {};
        const numeroParam = (valor, decimales) =>
            Number.isFinite(Number(valor)) ? Number(valor).toFixed(decimales) : "--";
        const gobernantes = `Γ ${numeroParam(parametros.gamma, 2)} · ` +
            `Certeza ${numeroParam(parametros.target_certeza_pct, 1)}% (${parametros.modo_certeza || "--"}) · ` +
            `Cobertura ${parametros.modo_cobertura || "--"}`;
        estado.textContent = `Simulación certificada [LN-QBE-107] · rango J${primera}-J${ultima} · ` +
            `${gobernantes} · ${veto}`;
    }

    _pintarMesoFinanciera(Array.isArray(data.jornadas_detalle) ? data.jornadas_detalle : []);
    _dibujarCurvaCapital(data);
}

/**
 * [ARCH-1.4.54] Clasificador cromático por TOKEN: la tabla meso jamás emite hex quemados.
 * El croma sólo lee el campo certificado del contrato; cero aritmética de negocio en cliente.
 */
const _clasePnlMeso = (valor) => {
    const numero = Number(valor);
    if (!Number.isFinite(numero) || numero === 0) return "meso-pnl-neutro";
    return numero > 0 ? "meso-pnl-positivo" : "meso-pnl-negativo";
};

function _pintarMesoFinanciera(detalle) {
    const cuerpo = document.getElementById("cuerpo-meso-financiero");
    if (!cuerpo) return;
    if (!detalle.length) {
        cuerpo.innerHTML = `<tr class="meso-inactiva"><td colspan="7" style="text-align:center; padding:18px;">` +
            "La simulación no devolvió jornadas liquidables sobre el rango solicitado.</td></tr>";
        return;
    }
    cuerpo.innerHTML = detalle.map(jornada => {
        const pnl = Number(jornada.pnl_jornada);
        const roi = Number(jornada.roi_jornada_pct || 0);
        const operables = Number(jornada.posiciones_operables || 0);
        const vetos = Array.isArray(jornada.descartes)
            ? jornada.descartes.filter(d => d && d.veto_fiduciario).length
            : 0;
        const clases = ["bt-jornada-auditada"];
        // [ARCH-1.4.54] Jornada sin despliegue operativo: se atenúa, jamás se disimula.
        if (operables === 0) clases.push("meso-inactiva");
        return `
            <tr class="${clases.join(" ")}">
                <td><strong>J${jornada.jornada}</strong></td>
                <td class="numeric">${operables}</td>
                <td class="numeric">${_fmtMxn(jornada.inversion_total)}</td>
                <td class="numeric ${_clasePnlMeso(pnl)}">${pnl > 0 ? "+" : ""}${_fmtMxn(pnl)}</td>
                <td class="numeric ${_clasePnlMeso(roi)}">${roi.toFixed(2)}%</td>
                <td class="numeric">${_fmtMxn(jornada.bankroll_final)}</td>
                <td class="numeric">${vetos}</td>
            </tr>`;
    }).join("");
}


/** Curva de capital: J0 (patrimonio inicial) + bankroll_final certificado de cada jornada. */
function _dibujarCurvaCapital(data) {
    const canvas = document.getElementById("equity-chart");
    const fallback = document.getElementById("equity-chart-fallback");
    if (!canvas) return;

    const detalle = Array.isArray(data.jornadas_detalle) ? data.jornadas_detalle : [];
    if (typeof Chart === "undefined" || !detalle.length) {
        canvas.style.display = "none";
        if (fallback) {
            fallback.textContent = typeof Chart === "undefined"
                ? "Chart.js no está disponible en este navegador: la trayectoria del capital permanece íntegra en la tabla meso financiera."
                : "Sin jornadas liquidables: no hay serie que graficar (cero curvas sintéticas).";
            fallback.style.display = "flex";
        }
        return;
    }
    canvas.style.display = "block";
    if (fallback) fallback.style.display = "none";

    const labels = ["J0"].concat(detalle.map(j => `J${j.jornada}`));
    const serie = [Number(data.bankroll_inicial)].concat(detalle.map(j => Number(j.bankroll_final)));

    if (_equityChart) {
        _equityChart.destroy();
        _equityChart = null;
    }
    _equityChart = new Chart(canvas.getContext("2d"), {
        type: "line",
        data: {
            labels: labels,
            datasets: [{
                label: "Bankroll",
                data: serie,
                borderColor: "#38BDF8",
                backgroundColor: "rgba(56, 189, 248, 0.12)",
                borderWidth: 2,
                fill: true,
                tension: 0.25,
                pointRadius: 3,
                pointBackgroundColor: "#38BDF8",
                pointBorderColor: "#0B132B",
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: ctx => `Bankroll: ${_fmtMxn(ctx.parsed.y)}`,
                    },
                },
            },
            scales: {
                x: {
                    grid: { color: "rgba(30, 41, 59, 0.6)" },
                    ticks: { color: "#94A3B8", font: { size: 10 } },
                },
                y: {
                    grid: { color: "rgba(30, 41, 59, 0.6)" },
                    ticks: {
                        color: "#94A3B8",
                        font: { size: 10 },
                        callback: valor => _fmtMxn(valor),
                    },
                },
            },
        },
    });
}

/** Conmutador de paneles del visor dual: ninguna vista destruye a la otra (sólo `d-none`). */
function activarSubPanelBacktesting(panelId) {
    const paneles = ["panel-visor-factico", "panel-visor-financiero"];
    const destino = paneles.includes(panelId) ? panelId : "panel-visor-factico";
    paneles.forEach(panel => {
        const el = document.getElementById(panel);
        if (el) el.classList.toggle("d-none", panel !== destino);
    });
    document.querySelectorAll(".bt-subtab-btn").forEach(btn => {
        const activo = btn.getAttribute("data-bt-panel") === destino;
        btn.classList.toggle("active", activo);
        btn.setAttribute("aria-selected", activo ? "true" : "false");
    });
    _panelBacktestingActivo = destino;
    if (destino === "panel-visor-financiero") {
        if (_equityChart) _equityChart.resize();
        else if (_ultimaSimulacionRentabilidad) _dibujarCurvaCapital(_ultimaSimulacionRentabilidad);
    }
}

window.activarSubPanelBacktesting = activarSubPanelBacktesting;
window.iniciarSimulacionRentabilidad = iniciarSimulacionRentabilidad;
window.pintarPanelFinanciero = pintarPanelFinanciero;


function initVisorBacktesting() {
    const tab = document.getElementById("tab-visor-backtesting");
    if (tab) {
        tab.addEventListener("click", cargarVisorBacktesting);
    }
    // [DES-QBE-068] Píldoras del visor dual (auditoría fáctica ↔ rentabilidad financiera).
    document.querySelectorAll(".bt-subtab-btn").forEach(btn => {
        btn.addEventListener("click", () => activarSubPanelBacktesting(btn.getAttribute("data-bt-panel")));
    });
    // [DES-QBE-069] El alcance declarado se re-deriva de la selección REAL del conmutador.
    const selectorJornada = document.getElementById("select-jornada");
    if (selectorJornada) selectorJornada.addEventListener("change", _actualizarAlcanceSimulacion);
    const casillaFamiliaR = document.getElementById("chk-excluir-familia-r");
    if (casillaFamiliaR) casillaFamiliaR.addEventListener("change", _actualizarAlcanceSimulacion);
    // [LN-QBE-104] `#chk-excluir-vetados`: conmutador del filtro anti-cuarentena. Cero refetch:
    // se re-pinta desde la caché ya certificada (idempotente y sin tráfico adicional).
    const casillaVetados = document.getElementById("chk-excluir-vetados");
    if (casillaVetados) {
        casillaVetados.addEventListener("change", _pintarVisorBacktesting);
    }
    // [DES-QBE-072 · Capa 1] El conmutador de alcance se cablea en el MARCADO
    // (`onclick="conmutarAlcanceMuestra(...)"`, publicado en `window`): aquí sólo se sincroniza el
    // estado accesible inicial, de modo que no existan dos manejadores para el mismo gesto.
    document.querySelectorAll(".visor-muestra-btn").forEach(btn => {
        const activo = btn.getAttribute("data-muestra") === _muestraVisorActiva;
        btn.classList.toggle("active", activo);
        btn.setAttribute("aria-selected", activo ? "true" : "false");
    });
}

function _pctBacktesting(valor) {
    const n = Number(valor);
    return Number.isFinite(n) ? `${(n * 100).toFixed(1)}%` : "--";
}

function _claseCoberturaBacktesting(pct) {
    const n = Number(pct);
    if (!Number.isFinite(n)) return "";
    if (n >= 70) return "bt-cobertura-alta";
    if (n >= 40) return "bt-cobertura-media";
    return "bt-cobertura-baja";
}

async function cargarVisorBacktesting() {
    const estado = document.getElementById("bt-estado");
    const cuerpo = document.getElementById("cuerpo-meso-jornadas");
    if (!cuerpo) return;
    if (estado) estado.textContent = "Leyendo la bóveda 3NF (solo lectura)…";
    try {
        const resp = await fetch("/api/markets/backtesting/calibration-report?league_id=1");
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        backtestingReportCache = data;
        // [DES-QBE-072 · ARCH-1.4.68 · Capa 0] LÍNEA BASE INMUTABLE: el payload certificado se
        // conserva intacto y todo filtrado posterior es PROYECCIÓN en cliente (cero refetch, cero
        // mutación de la bóveda). `backtestingReportCache` sigue siendo la fuente de verdad del
        // visor sellado ([DES-QBE-067]).
        window._calibracionPayloadOriginal = data;
        _pintarVisorBacktesting();
        // Capa 3: la selección declarada (alcance + filtros fiduciarios) se proyecta de una pasada.
        aplicarFiltrosVisorCalibracion();
    } catch (e) {
        if (estado) {
            estado.textContent = `⚠️ Bóveda no legible: ${e.message}. Cero cifras se muestran sin respaldo.`;
        }
        cuerpo.innerHTML = `<tr><td colspan="8" style="text-align:center; padding:18px; color:#F87171;">` +
            "Sin lectura factual disponible.</td></tr>";
    }
}

// ── [LN-QBE-104 · DES-QBE-067] FILTRO ANTI-CUARENTENA DE LA CARTELERA ─────────────────────────
// El semáforo EPIST lo publica el endpoint de atribución factorial [ARCH-1.4.42]:
// 🟢 Δ ≤ 0.03 · 🟡 0.03 < Δ ≤ 0.12 · 🔴 Δ > 0.12 (Cuarentena Fiduciaria [LN-QBE-070-B]).
// Un partido vetado NO recibe capital de la cartera; exhibirlo como acierto/fallo de Q-BE
// sobreestima la calibración con evidencia que el motor ya declaró inservible. El filtro es de
// PRESENTACIÓN (`[GOVERNANCE-01]`: cero cifras maquilladas, cero mutación de la bóveda).
const SEMAFORO_EPIST_VETO = "ROJO";
const VERTICES_TRIADA_BACKTESTING = ["P_MAX", "P_MID", "P_LOW"];
// [LN-QBE-125 · ARCH-1.4.65] MUESTRA DECLARADA del Visor: "CALIBRADA" (universo informado
// S(I)=1 — el criterio es el DATO, no el número de jornada) o "GLOBAL" (torneo completo).
// La conmutación NO refetchea: re-pinta la caché certificada y `#bt-estado` declara el universo.
let _muestraVisorActiva = "CALIBRADA";

/** [LN-QBE-125] Etiqueta legible de la muestra activa (declaración textual de la vitrina). */
function _etiquetaMuestraVisor() {
    return _muestraVisorActiva === "GLOBAL"
        ? "🌐 Torneo Completo (J1–J13)"
        : "🎯 Muestra Calibrada (J4–J13)";
}

function _partidoVetadoBacktesting(partido) {
    const atribucion = partido && partido.atribucion_factorial;
    const semaforos = atribucion && atribucion.semaforos;
    // [DES-QBE-071] Acceso INDEXADO a propósito: el semáforo epistémico ya no se exhibe en el HUD
    // ni en el panel del modal, pero sigue gobernando la cuarentena de calibración. Retirarlo de la
    // vitrina no lo retira del gobierno ([DES-QBE-067] intacto).
    return Boolean(semaforos && semaforos["epist"] === SEMAFORO_EPIST_VETO);
}

/**
 * [LN-QBE-100 · VAR-2026-LOBOTOMIA-RESCATE-A] Vértice del símplex Δ² consumado por el resultado.
 * Fuente de verdad única: el vértice SERVIDO por la bóveda (`clasificacion_triada`). Un payload
 * legado sin el campo degrada al rango del desenlace en el ranking P′ (0 ≡ P_MAX · 1 ≡ P_MID ·
 * 2 ≡ P_LOW): cero segunda verdad paralela y cero etiqueta inventada.
 */
function _verticeConsumadoBacktesting(partido) {
    if (partido && VERTICES_TRIADA_BACKTESTING.includes(partido.clasificacion_triada)) {
        return partido.clasificacion_triada;
    }
    const clavesPorPRima = ["LOCAL", "EMPATE", "VISITANTE"]
        .map((clave, orden) => ({
            clave,
            p: Number(partido ? partido[`p_${clave.toLowerCase()}`] : 0) || 0,
            orden,
        }))
        .sort((a, b) => (b.p - a.p) || (a.orden - b.orden))
        .map(x => x.clave);
    const rangoReal = clavesPorPRima.indexOf(partido ? partido.resultado_real : null);
    return rangoReal === 0 ? "P_MAX" : rangoReal === 1 ? "P_MID" : "P_LOW";
}

/** Conteos enteros por vértice y procedencia del rescate secundario [LN-QBE-100]. */
function _conteosTriadaBacktesting(partidos) {
    const conteos = {
        n_p_max: 0, n_p_mid: 0, n_p_low: 0, n_p_mid_empate: 0, n_p_mid_rival: 0,
    };
    (partidos || []).forEach(partido => {
        const vertice = _verticeConsumadoBacktesting(partido);
        if (vertice === "P_MAX") {
            conteos.n_p_max += 1;
            return;
        }
        if (vertice === "P_LOW") {
            conteos.n_p_low += 1;
            return;
        }
        conteos.n_p_mid += 1;
        // Rescate por empate ⟺ el vértice medio era el empate (`r_mid === "EMPATE"`) y el empate
        // se consumó; en cualquier otro caso el rescate lo aportó el rival del vértice medio.
        if (partido.resultado_real === "EMPATE" && partido.r_mid === "EMPATE") {
            conteos.n_p_mid_empate += 1;
        } else {
            conteos.n_p_mid_rival += 1;
        }
    });
    return conteos;
}

/**
 * Réplica exacta de `calcular_brier_multicategorico` [LN-QBE-100] sobre el subconjunto exhibido:
 * BS = (1/3N) · Σ_i Σ_k (p_ik − y_ik)² con normalización 3N y redondeo a 4 decimales. `prefijo`
 * selecciona el generador: "p_" = P′ de Q-BE · "q_" = consenso del mercado.
 */
function _brierBacktesting(partidos, prefijo) {
    let sumaError = 0;
    let evaluados = 0;
    (partidos || []).forEach(partido => {
        const probabilidades = ["local", "empate", "visitante"]
            .map(clave => Number(partido[`${prefijo}${clave}`]));
        if (!probabilidades.every(Number.isFinite)) return;
        const indiceReal = ["LOCAL", "EMPATE", "VISITANTE"]
            .indexOf(String(partido.resultado_real || "").toUpperCase());
        if (indiceReal < 0) return;
        probabilidades.forEach((p, indice) => {
            sumaError += (p - (indice === indiceReal ? 1 : 0)) ** 2;
        });
        evaluados += 1;
    });
    if (!evaluados) return 0;
    return Math.round((sumaError / (3 * evaluados)) * 10000) / 10000;
}

/** Alpha de Calibración = (1 − BS_QBE / BS_MKT) × 100 con guarda de cero [LN-QBE-100]. */
function _alphaBacktesting(brierQbe, brierMercado) {
    if (!(brierMercado > 0)) return 0;
    return Math.round((1 - (brierQbe / brierMercado)) * 100 * 100) / 100;
}

/**
 * [LN-QBE-104] Agregado de la triada desde los CONTEOS ENTEROS del universo efectivo. Sirve tanto
 * a la temporada como a una jornada suelta: las claves `n_*` (meso) y `total_*` (macro) se pueblan
 * con el mismo hecho, de modo que la cartelera nunca reconcilia dos verdades distintas.
 */
function _agregadoTriadaBacktesting(partidos) {
    const universo = partidos || [];
    const total = universo.length;
    const conteos = _conteosTriadaBacktesting(universo);
    const pct = n => (total ? Math.round((n / total) * 100 * 100) / 100 : 0);
    const pctMax = pct(conteos.n_p_max);
    const pctMid = pct(conteos.n_p_mid);
    const pctLow = pct(conteos.n_p_low);
    const aciertos = universo
        .filter(p => p.tipo_resultado === "FAVORITO" || p.tipo_resultado === "EMPATE").length;
    const brierQbe = _brierBacktesting(universo, "p_");
    const brierMercado = _brierBacktesting(universo, "q_");
    return {
        total_partidos: total,
        masa_cobertura_pct: Math.round((pctMax + pctMid) * 100) / 100,
        p_max_aciertos_pct: pctMax,
        p_mid_rescate_pct: pctMid,
        p_low_ruptura_pct: pctLow,
        pct_p_max: pctMax,
        pct_p_mid: pctMid,
        pct_p_low: pctLow,
        n_p_max: conteos.n_p_max,
        n_p_mid: conteos.n_p_mid,
        n_p_low: conteos.n_p_low,
        n_p_mid_empate: conteos.n_p_mid_empate,
        n_p_mid_rival: conteos.n_p_mid_rival,
        total_p_max: conteos.n_p_max,
        total_p_mid: conteos.n_p_mid,
        total_p_low: conteos.n_p_low,
        total_p_mid_empate: conteos.n_p_mid_empate,
        total_p_mid_rival: conteos.n_p_mid_rival,
        aciertos_cobertura: aciertos,
        tasa_cobertura_pct: pct(aciertos),
        brier_score_qbe: brierQbe,
        brier_score_mercado: brierMercado,
        alpha_calibracion_pct: _alphaBacktesting(brierQbe, brierMercado),
    };
}


/**
 * [LN-QBE-104] Universo efectivo de la cartelera: payload íntegro (filtro inerte) o el subconjunto
 * sin partidos en Cuarentena Fiduciaria, con TODOS sus agregados re-derivados de los conteos
 * enteros del subconjunto. Jornadas sin ningún vetado se sirven tal cual (cero recálculo: la
 * aritmética del servidor es la fuente de verdad y se respeta bit a bit).
 */
/**
 * [LN-QBE-125 · ARCH-1.4.65] Resumen SERVIDO del universo activo. El backend publica los dos
 * agregados con la MISMA aritmética (`resumen_calibrado` · `resumen_global`), de modo que el
 * pintor no recalcula nada: sólo elige. Un payload legado sin el bloque calibrado degrada al
 * alias sellado `resumen_temporada` y `#bt-estado` lo declara.
 */
function _resumenMuestraVisor(payload) {
    const raiz = payload || {};
    const global = raiz.resumen_global || raiz.resumen_temporada || {};
    if (_muestraVisorActiva === "GLOBAL") return global;
    return raiz.resumen_calibrado || global;
}

function _universoCalibracion() {
    const payload = backtestingReportCache || {};
    const resumenServido = _resumenMuestraVisor(payload);
    const casilla = document.getElementById("chk-excluir-vetados");
    const excluir = Boolean(casilla && casilla.checked);
    let excluidos = 0;

    const jornadas = (payload.jornadas || []).map(jornada => {
        const partidosServidos = jornada.partidos || [];
        if (!excluir) return jornada;
        const partidos = partidosServidos.filter(partido => !_partidoVetadoBacktesting(partido));
        const retirados = partidosServidos.length - partidos.length;
        if (!retirados) return jornada;
        excluidos += retirados;
        return Object.assign({}, jornada, _agregadoTriadaBacktesting(partidos), {
            jornada: jornada.jornada,
            partidos,
        });
    });

    const partidosEfectivos = [];
    jornadas.forEach(jornada => {
        (jornada.partidos || []).forEach(partido => partidosEfectivos.push(partido));
    });

    const filtroInerte = excluidos === 0;
    return {
        excluir,
        excluidos,
        filtroInerte,
        jornadas,
        totalServido: Number(resumenServido.total_partidos || 0),
        // Con el filtro inerte manda el agregado servido (idempotencia estricta); con vetados
        // retirados se publica el agregado del subconjunto, declarándolo en `#bt-estado`.
        resumen: (excluir && !filtroInerte)
            ? Object.assign({}, _agregadoTriadaBacktesting(partidosEfectivos), {
                jornadas_auditadas: resumenServido.jornadas_auditadas || [],
                partidos_pendientes_captura:
                    Number(resumenServido.partidos_pendientes_captura || 0),
                partidos_consolidados_servido: Number(resumenServido.total_partidos || 0),
            })
            : resumenServido,
        resumenServido,
    };
}

/** Declaración textual del universo leído: muestra activa + régimen del filtro anti-cuarentena. */
function _estadoLecturaBacktesting(universo) {
    const resumen = universo.resumen || {};
    const etiquetaMuestra = _etiquetaMuestraVisor();
    const jornadasAuditadas = (resumen.jornadas_auditadas || []).map(j => `J${j}`).join(" · ");
    const auditoria = "auditados contra la bóveda 3NF" +
        (jornadasAuditadas ? ` (${jornadasAuditadas})` : "");
    const calibracion = `Brier Q-BE ${Number(resumen.brier_score_qbe || 0).toFixed(4)} vs Mkt ` +
        `${Number(resumen.brier_score_mercado || 0).toFixed(4)} · Alpha ` +
        `${Number(resumen.alpha_calibracion_pct || 0) >= 0 ? "+" : ""}` +
        `${Number(resumen.alpha_calibracion_pct || 0).toFixed(2)}%`;
    if (!universo.excluir) {
        return `${etiquetaMuestra} · Lectura certificada · ${resumen.total_partidos || 0} ` +
            `partidos concluidos ${auditoria} · ${calibracion} ` +
            "(solo lectura: cero escritura, cero mocks).";
    }
    if (universo.filtroInerte) {
        return `${etiquetaMuestra} · Filtro anti-cuarentena activo sin efecto · 0 partidos ` +
            `vetados sobre ${resumen.total_partidos || 0} partidos concluidos ${auditoria} · ` +
            `${calibracion}.`;
    }
    // [DES-QBE-072] El conteo que se declara es el de VETOS FIDUCIARIOS (Cuarentena EPIST), no el
    // total de exclusiones del visor: las ausencias por alcance declarado no son cuarentena.
    const excluidosVeto = (universo.excluidosFiduciarios === undefined)
        ? universo.excluidos
        : universo.excluidosFiduciarios;
    return `${etiquetaMuestra} · Filtro anti-cuarentena activo · ${excluidosVeto} de ` +
        `${universo.totalServido} partidos concluidos excluidos por Cuarentena Fiduciaria ` +
        "(EPIST 🔴 · Δ_epist > 0.12) · " +
        `universo efectivo: ${resumen.total_partidos || 0} partidos ${auditoria} · ` +
        `${calibracion} [LN-QBE-104].`;
}

/**
 * [LN-QBE-125 · ARCH-1.4.65] Conmutador de MUESTRA DECLARADA del Visor de calibración.
 * No refetchea: reasigna el universo activo y re-pinta desde la caché certificada
 * (`_pintarVisorBacktesting`), que es idempotente. El KPI macro y `#bt-estado` cambian de
 * universo; la tabla meso y la parrilla micro siguen exhibiendo el torneo completo con sus
 * sellos de ceguera declarados.
 */
function conmutarMuestraVisor(tipo) {
    // [DES-QBE-072] Alias de compatibilidad: la única verdad del alcance vive en
    // `conmutarAlcanceMuestra` (Capa 1), que re-ejecuta la pasada atómica completa.
    conmutarAlcanceMuestra(tipo);
}

window.conmutarMuestraVisor = conmutarMuestraVisor;

// ══════════════════════════════════════════════════════════════════════════════════════════════
// [DES-QBE-072 · ARCH-1.4.68] VISOR DE CALIBRACIÓN EN CUATRO CAPAS
// Capa 0: `window._calibracionPayloadOriginal` — línea base certificada, INMUTABLE.
// Capa 1: ALCANCE declarado (`_muestraVisorActiva`: CALIBRADA ↔ GLOBAL), una sola verdad.
// Capa 2: tres filtros fiduciarios combinables (discrepancia · altitud · fragilidad).
// Capa 3: una sola pasada propaga la selección a macro, meso y micro y declara el DENOMINADOR.
// Régimen [DBBD-FUNGIBLE]: cero refetch, cero mutación de la bóveda, cero cifra fabricada.
// ══════════════════════════════════════════════════════════════════════════════════════════════
const MOTIVOS_EXCLUSION_VISOR = {
    ALCANCE: "Fuera de la muestra calibrada (Suficiencia de Datos = 0)",
    DISCREPANCIA: "Alta Discrepancia (Δ_epist > 0.12)",
    ALTITUD: "Asedio Territorial Neto (ΔAlt ≥ 1,000 m)",
    ALTITUD_FUERA: "Sin Asedio Territorial Neto (ΔAlt < 1,000 m)",
    FRAGIL: "Favorito Frágil (P′ máx < 0.50)",
};

// [DES-QBE-072 §Glosario] ANCLA DE DEROGACIÓN. Los rótulos derogados que la legislación conserva
// como memoria documental y que el Juez 7 del Shield vigila literales son "🎯 ACIERTO P_MAX",
// "🛡️ RESCATE P_MID" y "💀 RUPTURA P_LOW": JAMÁS se renderizan, la vitrina publica el glosario.
const GLOSARIO_VERTICES_VISOR = {
    P_MAX: "Acierto Primario",
    P_MID: "Rescate de Cobertura",
    P_LOW: "Ruptura Residual",
};

/** Índice de la jornada desplegada en la parrilla micro (para re-pintarla en la misma pasada). */
let _jornadaMicroVisorIdx = null;

/** Capa 2 — estado REAL de los tres toggles fiduciarios (una sola lectura del DOM). */
function _filtrosVisorActivos() {
    const activo = id => {
        const casilla = document.getElementById(id);
        return Boolean(casilla && casilla.checked);
    };
    return {
        epist: activo("chk-filtro-epist"),
        altitud: activo("chk-filtro-altitud"),
        fragil: activo("chk-filtro-fragil"),
    };
}

/**
 * Capa 2 — veto fiduciario. Delega ÍNTEGRO en el semáforo EPIST servido por la bóveda
 * (`_partidoVetadoBacktesting` ⇒ `SEMAFORO_EPIST_VETO`): el pintor no dictamina nada por su cuenta.
 */
function _motivoFiltroFiduciarioVisor(partido, filtros) {
    if (!partido) return null;
    const activos = filtros || _filtrosVisorActivos();
    if (activos.epist && _partidoVetadoBacktesting(partido)) {
        return MOTIVOS_EXCLUSION_VISOR.DISCREPANCIA;
    }
    // [DES-QBE-072 · Enmienda de Saneamiento] El Asedio Territorial Neto (ΔAlt ≥ 1,000 m) es una
    // VENTAJA física del LOCAL, no un defecto: el toggle obra como filtro de INCLUSIÓN (aisla y
    // muestra únicamente a quien goza de ella). Queda derogada la semántica de penalización que
    // excluía precisamente a los mejores partidos del anfitrión y restaba masa probabilística.
    if (activos.altitud && !(partido.delta_alt_metros >= 1000)) {
        return MOTIVOS_EXCLUSION_VISOR.ALTITUD_FUERA;
    }
    const pMaximo = Math.max(
        Number(partido.p_local || 0),
        Number(partido.p_empate || 0),
        Number(partido.p_visitante || 0),
    );
    if (activos.fragil && pMaximo < 0.50) return MOTIVOS_EXCLUSION_VISOR.FRAGIL;
    return null;
}

/**
 * Capa 1 — ¿el partido pertenece al alcance declarado? Criterio de DATO, jamás de jornada ordinal:
 * (i) la jornada sellada como Cold Start (`es_cold_start` / `alpha_etiqueta === "COLD_START"`) queda
 * fuera del alcance calibrado por definición, y (ii) el partido debe portar Suficiencia de Datos ≠ 0.
 */
function _partidoDentroAlcanceVisor(partido, jornada) {
    if (_muestraVisorActiva === "GLOBAL") return true;
    if (jornada && (jornada.es_cold_start === true ||
        String(jornada.alpha_etiqueta || "").toUpperCase() === "COLD_START")) {
        return false;
    }
    return Number(partido && partido.suficiencia_S_I) !== 0;
}

/** Motivo ÚNICO de exclusión de un partido (declaración textual de la parrilla micro). */
function _motivoExclusionPartidoCalibracion(partido, jornada) {
    if (!_partidoDentroAlcanceVisor(partido, jornada)) return MOTIVOS_EXCLUSION_VISOR.ALCANCE;
    return _motivoFiltroFiduciarioVisor(partido);
}

/** [DES-QBE-072 · R2] Espejo `#chk-excluir-vetados` ⇄ `#chk-filtro-epist`: una sola verdad. */
function _sincronizarEspejoVetadosVisor() {
    const toggle = document.getElementById("chk-filtro-epist");
    const espejo = document.getElementById("chk-excluir-vetados");
    if (toggle && espejo) espejo.checked = Boolean(toggle.checked);
}

/** Alias legislado del pintor macro: un solo dueño del agregado de la temporada. */
function actualizarMacroCards(resumen) {
    pintarResumenBacktesting(resumen);
}

/**
 * Capa 3 — PROYECCIÓN del alcance declarado. El universo se filtra EN CLIENTE sobre la línea base
 * inmutable y sus agregados se re-derivan de los CONTEOS ENTEROS (`_agregadoTriadaBacktesting`),
 * jamás se heredan de un promedio ajeno. Las jornadas SERVIDAS se conservan SIEMPRE: una jornada
 * sin partidos activos se declara inactiva en la tabla meso, nunca se oculta ([ARCH-1.4.68 §P.4]).
 */
function _proyectarUniversoVisorCalibracion() {
    const base = _universoCalibracion();
    // Las jornadas se leen de la LÍNEA BASE INMUTABLE (Capa 0): así la parrilla micro puede
    // declarar el motivo de CADA exclusión aunque el espejo sellado ya hubiera filtrado la
    // caché efectiva (`_universoCalibracion` sólo aporta el agregado certificado del alcance).
    const lineaBase = window._calibracionPayloadOriginal || backtestingReportCache || {};
    const jornadasServidas = lineaBase.jornadas || base.jornadas || [];
    const filtros = _filtrosVisorActivos();
    let fueraAlcance = 0;
    let excluidosFiduciarios = 0;

    const jornadas = jornadasServidas.map(jornada => {
        const partidosServidos = jornada.partidos || [];
        const partidos = partidosServidos.filter(partido => {
            if (!_partidoDentroAlcanceVisor(partido, jornada)) {
                fueraAlcance += 1;
                return false;
            }
            if (_motivoFiltroFiduciarioVisor(partido, filtros)) {
                excluidosFiduciarios += 1;
                return false;
            }
            return true;
        });
        const retirados = partidosServidos.length - partidos.length;
        const fila = Object.assign({}, jornada, { partidos, partidosServidos });
        return retirados
            ? Object.assign(fila, _agregadoTriadaBacktesting(partidos), {
                jornada: jornada.jornada,
                es_cold_start: jornada.es_cold_start,
                alpha_etiqueta: jornada.alpha_etiqueta,
            })
            : fila;
    });

    const partidosEfectivos = [];
    jornadas.forEach(jornada => {
        (jornada.partidos || []).forEach(partido => partidosEfectivos.push(partido));
    });

    const resumenServido = base.resumen || {};
    const activos = partidosEfectivos.length;
    const totalServido = jornadasServidas.reduce(
        (acc, jornada) => acc + (jornada.partidos || []).length, 0);
    // IDEMPOTENCIA ESTRICTA: si la proyección conserva exactamente los partidos que el agregado
    // servido declara, manda el agregado CERTIFICADO (cero recálculo); si retiró alguno, se
    // re-deriva del subconjunto efectivo con la MISMA aritmética de conteos enteros de [LN-QBE-100].
    const recalculado = activos !== Number(resumenServido.total_partidos || 0);
    const resumen = recalculado
        ? Object.assign({}, _agregadoTriadaBacktesting(partidosEfectivos), {
            jornadas_auditadas: resumenServido.jornadas_auditadas || [],
            partidos_pendientes_captura: Number(resumenServido.partidos_pendientes_captura || 0),
            partidos_consolidados_servido: Number(
                resumenServido.partidos_consolidados_servido ||
                resumenServido.total_partidos || 0),
        })
        : resumenServido;

    return {
        jornadas,
        resumen,
        filtros,
        excluir: Boolean(filtros.epist || filtros.altitud || filtros.fragil || base.excluir),
        excluidos: Math.max(0, totalServido - activos),
        excluidosFiduciarios,
        fueraAlcance,
        activos,
        alcance: totalServido,
        filtroInerte: excluidosFiduciarios === 0,
        totalServido,
    };
}

/**
 * Capa 3 — PASADA ATÓMICA. Una sola invocación repinta macro, meso, micro y el denominador desde
 * la MISMA proyección: la cartelera jamás reconcilia dos verdades distintas en el mismo instante.
 */
function aplicarFiltrosVisorCalibracion() {
    if (!backtestingReportCache) return;
    _sincronizarEspejoVetadosVisor();
    const proyeccion = _proyectarUniversoVisorCalibracion();
    backtestingUniversoActual = proyeccion;
    actualizarMacroCards(proyeccion.resumen);
    pintarMesoBacktesting(proyeccion.jornadas, proyeccion.resumen);
    if (_jornadaMicroVisorIdx !== null) mostrarMicroJornadaBacktesting(_jornadaMicroVisorIdx);
    _actualizarDenominadorVisor(proyeccion);
    const estado = document.getElementById("bt-estado");
    if (estado) estado.textContent = _estadoLecturaBacktesting(proyeccion);
}

/** Capa 1 — conmutador de ALCANCE (una sola verdad: `_muestraVisorActiva`). Cero refetch. */
function conmutarAlcanceMuestra(tipo) {
    _muestraVisorActiva = tipo === "GLOBAL" ? "GLOBAL" : "CALIBRADA";
    document.querySelectorAll(".visor-muestra-btn").forEach(btn => {
        const activo = btn.getAttribute("data-muestra") === _muestraVisorActiva;
        btn.classList.toggle("active", activo);
        btn.setAttribute("aria-selected", activo ? "true" : "false");
    });
    aplicarFiltrosVisorCalibracion();
}

/** Capa 2 — conmutador de los tres filtros fiduciarios (re-ejecuta la pasada atómica). */
function conmutarFiltrosVisorCalibracion() {
    aplicarFiltrosVisorCalibracion();
}

/**
 * [DES-QBE-072 §Denominador] Transparencia del denominador: X activos sobre N del alcance
 * declarado, con el número de exclusiones y su causa. Cero porcentaje huérfano de su base.
 */
function _actualizarDenominadorVisor(universo) {
    const proyeccion = universo || backtestingUniversoActual || {};
    const activos = Number(proyeccion.activos || 0);
    const excluidos = Number(proyeccion.excluidos || 0);
    const fueraAlcance = Number(proyeccion.fueraAlcance || 0);
    const alcance = Number(proyeccion.alcance || (activos + excluidos));

    const texto = document.getElementById("visor-denominador-texto");
    if (texto) {
        // La base estadística publicada es N = activos; el universo declarado es `alcance`.
        const filtrosActivos = Boolean(proyeccion.filtros &&
            (proyeccion.filtros.epist || proyeccion.filtros.altitud || proyeccion.filtros.fragil));
        const motivo = filtrosActivos
            ? "excluidos por filtros activos"
            : "fuera del alcance declarado";
        const sufijoAlcance = (fueraAlcance && filtrosActivos)
            ? ` · ${fueraAlcance} fuera del alcance declarado`
            : "";
        texto.textContent = `Mostrando ${activos} de ${alcance} partidos concluidos ` +
            `(${excluidos} ${motivo}) · N = ${activos}` + sufijoAlcance;
    }

    const badge = document.getElementById("visor-filtro-activo-badge");
    if (!badge) return;
    const filtros = proyeccion.filtros || _filtrosVisorActivos();
    const etiquetas = [];
    if (filtros.epist) etiquetas.push(MOTIVOS_EXCLUSION_VISOR.DISCREPANCIA);
    // [DES-QBE-072 · Enmienda] El toggle de altitud es de INCLUSIÓN: se rotula como tal para no
    // confundirlo con los filtros de exclusión y no sugerir que resta masa a los partidos con
    // ventaja física del local.
    if (filtros.altitud) etiquetas.push(`Inclusión · ${MOTIVOS_EXCLUSION_VISOR.ALTITUD}`);
    if (filtros.fragil) etiquetas.push(MOTIVOS_EXCLUSION_VISOR.FRAGIL);
    badge.textContent = etiquetas.length
        ? `Filtros activos: ${etiquetas.join(" · ")}`
        : `Línea Base Certificada · ${_etiquetaMuestraVisor()}`;
}

// Los manejadores `onclick` del marcado resuelven contra `window`: se publican explícitamente.
window.conmutarAlcanceMuestra = conmutarAlcanceMuestra;
window.conmutarFiltrosVisorCalibracion = conmutarFiltrosVisorCalibracion;
window.aplicarFiltrosVisorCalibracion = aplicarFiltrosVisorCalibracion;

/** Re-pintado íntegro del visor desde la caché certificada (idempotente, cero refetch). */
function _pintarVisorBacktesting() {
    if (!backtestingReportCache) return;
    const universo = _universoCalibracion();
    backtestingUniversoActual = universo;
    pintarResumenBacktesting(universo.resumen);
    pintarMesoBacktesting(universo.jornadas, universo.resumen);
    const estado = document.getElementById("bt-estado");
    if (estado) estado.textContent = _estadoLecturaBacktesting(universo);
}


function pintarResumenBacktesting(resumen) {
    const set = (id, texto) => {
        const el = document.getElementById(id);
        if (el) el.textContent = texto;
    };
    // [LN-QBE-100 · REFACTOR-TRIADA-PMAX-PMID-PLOW] Cuatro métricas PURAS de la taxonomía de
    // vértices del símplex Δ². La sigla derogada H_fid (FAS/FES/FUS) queda fuera de la cartelera
    // macro: aquí solo se exhibe masa de cobertura, convicción (P_max), rescate (P_mid) y ruptura.
    set("kpi-bt-masa-cobertura", `${Number(resumen.masa_cobertura_pct || 0).toFixed(2)}%`);
    const partidosCubiertos =
        Number(resumen.total_p_max || 0) + Number(resumen.total_p_mid || 0);
    set("kpi-bt-masa-detalle",
        `Acierto Primario + Rescate de Cobertura · ${partidosCubiertos} de ${resumen.total_partidos || 0} partidos`);
    set("kpi-bt-pmax", `${Number(resumen.p_max_aciertos_pct || 0).toFixed(2)}%`);
    set("kpi-bt-pmax-detalle",
        `${resumen.total_p_max || 0} partidos · Acierto Primario consumado`);
    set("kpi-bt-pmid", `${Number(resumen.p_mid_rescate_pct || 0).toFixed(2)}%`);
    set("kpi-bt-pmid-detalle",
        `[${resumen.total_p_mid_empate || 0} Emp · ${resumen.total_p_mid_rival || 0} Riv] ` +
        "Rescate de Cobertura activo");
    set("kpi-bt-plow", `${Number(resumen.p_low_ruptura_pct || 0).toFixed(2)}%`);
    set("kpi-bt-plow-detalle",
        `${resumen.total_p_low || 0} partidos · Ruptura Residual (vértice no cubierto)`);
}

function pintarMesoBacktesting(jornadas, resumen) {
    const cuerpo = document.getElementById("cuerpo-meso-jornadas");
    if (!cuerpo) return;
    // [DES-QBE-072 · R4] Se itera sobre las jornadas SERVIDAS por la bóveda: una jornada sin
    // partidos activos se declara inactiva con guiones, JAMÁS se oculta de la cartelera.
    const jornadasServidas = jornadas || [];
    if (!jornadasServidas.length) {
        cuerpo.innerHTML = `<tr><td colspan="8" style="text-align:center; padding:18px; color:var(--text-muted);">` +
            "La bóveda no registra jornadas con P′ y cuotas de cierre selladas.</td></tr>";
        return;
    }

    const maxJornada = jornadasServidas.reduce((acc, j) => Math.max(acc, Number(j.jornada)), 0);
    const filas = [];
    for (let j = 1; j <= maxJornada; j += 1) {
        const idx = jornadasServidas.findIndex(x => Number(x.jornada) === j);
        if (idx === -1) {
            filas.push(
                `<tr><td><strong>J${j}</strong></td><td>--</td>` +
                `<td colspan="6" class="bt-pendiente">Pendiente de captura ` +
                "(sin P′/cuotas de cierre selladas en la bóveda)</td></tr>"
            );
            continue;
        }
        const fila = jornadasServidas[idx];
        // [DES-QBE-072 · R4] Jornada INACTIVA: existe en la bóveda pero ninguno de sus partidos
        // pertenece al alcance con los filtros vigentes. Se declara con guiones y conserva su
        // botón de parrilla micro (donde cada exclusión publica su motivo).
        if (!(fila.partidos || []).length) {
            const selloInactiva = (fila.es_cold_start || fila.alpha_etiqueta === "COLD_START")
                ? ' <span class="bt-badge-cold-start" style="background:#1E293B; color:#93C5FD; border:1px solid #3B82F6; padding:1px 6px; border-radius:4px; font-size:9px; font-family:monospace;" title="Suficiencia de Datos = 0 en todos sus partidos: el Alpha no es una medición de ventaja">❄️ Cold Start · Suficiencia de Datos = 0</span>'
                : "";
            const servidosFuera = (fila.partidosServidos || []).length;
            filas.push(`
            <tr class="meso-inactiva">
                <td><strong>J${fila.jornada}</strong></td>
                <td class="numeric">0</td>
                <td>--</td>
                <td>Sin partidos en el alcance declarado · ${servidosFuera} servidos fuera</td>
                <td class="numeric">--</td>
                <td class="numeric">--</td>
                <td class="numeric">--${selloInactiva}</td>
                <td><button type="button" class="bt-btn-micro" data-jornada-idx="${idx}">Ver partidos</button></td>
            </tr>`);
            continue;
        }
        // [LN-QBE-100 · REFACTOR-TRIADA-PMAX-PMID-PLOW] Desglose por vértices del símplex Δ²:
        // masa de cobertura = % P_max + % P_mid (≡ 100% − % P_low) y conteos enteros que
        // reconcilian con la masa (n_p_max + n_p_mid + n_p_low = total_partidos).
        const masaJornada = Number(fila.masa_cobertura_pct || 0);
        const desgloseTriada =
            `${Number(fila.pct_p_max || 0).toFixed(2)}% · ` +
            `${Number(fila.pct_p_mid || 0).toFixed(2)}% · ` +
            `${Number(fila.pct_p_low || 0).toFixed(2)}%`;
        // [DES-QBE-072] Rótulo autodescriptivo del rescate secundario (empate vs rival).
        const conteosTriada =
            `(${fila.n_p_max || 0} · ${fila.n_p_mid || 0} · ${fila.n_p_low || 0}) · ` +
            `[Rescate: ${fila.n_p_mid_empate || 0} Emp · ${fila.n_p_mid_rival || 0} Riv]`;
        // [LN-QBE-125 / ARCH-1.4.65 · DES-QBE-072] Ceguera DECLARADA de la jornada: sin evidencia
        // fáctica el Alpha no mide ventaja, mide un prior puro. El sello lo dice en su columna con
        // el glosario autodescriptivo (Suficiencia de Datos = 0).
        const selloCeguera = (fila.es_cold_start || fila.alpha_etiqueta === "COLD_START")
            ? ' <span class="bt-badge-cold-start" style="background:#1E293B; color:#93C5FD; border:1px solid #3B82F6; padding:1px 6px; border-radius:4px; font-size:9px; font-family:monospace;" title="Suficiencia de Datos = 0 en todos sus partidos: el Alpha no es una medición de ventaja">❄️ Cold Start · Suficiencia de Datos = 0</span>'
            : "";
        filas.push(`
            <tr class="bt-jornada-auditada">
                <td><strong>J${fila.jornada}</strong></td>
                <td class="numeric">${fila.total_partidos}</td>
                <td class="${_claseCoberturaBacktesting(masaJornada)}">${masaJornada.toFixed(2)}%</td>
                <td>
                    <div style="font-weight:700; font-variant-numeric: tabular-nums;">${desgloseTriada}</div>
                    <div style="color:#94A3B8; font-size:10px; margin-top:2px; font-variant-numeric: tabular-nums;">${conteosTriada}</div>
                </td>
                <td class="numeric">${Number(fila.brier_score_qbe || 0).toFixed(4)}</td>
                <td class="numeric">${Number(fila.brier_score_mercado || 0).toFixed(4)}</td>
                <td class="numeric">${Number(fila.alpha_calibracion_pct || 0).toFixed(2)}%${selloCeguera}</td>
                <td><button type="button" class="bt-btn-micro" data-jornada-idx="${idx}">Ver partidos</button></td>
            </tr>`);
    }

    const pendientes = Number(resumen.partidos_pendientes_captura || 0);
    if (pendientes > 0) {
        filas.push(
            `<tr><td colspan="8" class="bt-pendiente">` +
            `Partidos concluidos sin P′ sellada (excluidos del cómputo): ${pendientes}</td></tr>`
        );
    }

    cuerpo.innerHTML = filas.join("");
    cuerpo.querySelectorAll(".bt-btn-micro").forEach(btn => {
        btn.addEventListener("click", () => {
            mostrarMicroJornadaBacktesting(Number(btn.getAttribute("data-jornada-idx")));
        });
    });
}

function mostrarMicroJornadaBacktesting(idx) {
    const contenedor = document.getElementById("contenedor-micro-partidos");
    // [LN-QBE-104] La parrilla micro consume el universo EFECTIVO (con el filtro anti-cuarentena
    // ya aplicado): jamás se exhibe un partido que la tabla meso dejó de contar.
    const jornadas = (backtestingUniversoActual && backtestingUniversoActual.jornadas) ||
        (backtestingReportCache && backtestingReportCache.jornadas) || [];
    const jornada = jornadas[idx];
    if (!contenedor || !jornada) return;
    // [DES-QBE-072] Se recuerda la jornada inspeccionada: la pasada atómica la re-pinta con la
    // MISMA proyección que alimentó macro y meso (cero ventana con datos de otra verdad).
    _jornadaMicroVisorIdx = idx;

    const escudo = url => (url ? `<img src="${url}" alt="" class="match-crest-mini">` : "");
    const momio = valor => {
        const n = Number(valor);
        return n > 1 ? n.toFixed(2) : "--";
    };

    // [DES-QBE-072 · R4] La parrilla exhibe TODOS los partidos servidos de la jornada: el excluido
    // por alcance o por filtro se ATENÚA, declara su motivo y se retira de los agregados, JAMÁS se
    // oculta (el Director debe poder auditar qué quedó fuera y por qué).
    const partidos = jornada.partidosServidos || jornada.partidos || [];
    const bloques = partidos.map(p => {
        // [DES-QBE-072 · Capa 2] Motivo ÚNICO de exclusión: alcance declarado o filtro fiduciario.
        const motivoExclusion = _motivoExclusionPartidoCalibracion(p, jornada);
        const claseExclusion = motivoExclusion ? " partido-excluido-filtro" : "";
        const badgeExclusion = motivoExclusion
            ? '<span class="badge-excluido-motivo" style="background:#1C1917; border:1px solid #78716C; color:#D6D3D1; padding:2px 6px; border-radius:4px; font-size:10px;" title="No cuenta en masa, Brier ni Alpha: retirado por el alcance declarado o por un filtro fiduciario activo">' +
                `🚫 EXCLUIDO · ${motivoExclusion}</span>`
            : "";
        const momios = p.momios || {};
        // [LN-QBE-125 · ARCH-1.4.65] Ceguera DECLARADA ([GOVERNANCE-01]): con S(I)=0 el partido se
        // puntúa con su P′ SOBERANA — la sustitución por el consenso del mercado quedó DEROGADA —,
        // así que el rótulo ya no puede afirmar que la parrilla espeja q_mkt: declara la ignorancia
        // fáctica del insumo y deja que el Brier mida la degradación real del prior.
        const pildoraColdStart = p.suficiencia_S_I === 0
            ? '<span class="bt-badge-cold-start" style="background:#1E293B; color:#93C5FD; border:1px solid #3B82F6; padding:2px 6px; border-radius:4px; font-size:10px;" title="Suficiencia de Datos = 0: sin evidencia fáctica; se evalúa el prior puro del modelo (Cold Start sincero)">❄️ Cold Start · Suficiencia de Datos = 0</span>'
            : "";
        // [DES-QBE-064-B] BANDA FIDUCIARIA DE ANCHO COMPLETO: los tres sellos (Cold Start,
        // procedencia de captura y exclusión) ABANDONAN la columna `auto` del marcador y se
        // apilan en una fila propia por encima de los equipos. Es la pieza que devuelve la
        // centralidad al resultado y extingue el desborde por zoom (una columna de ancho
        // intrínseco crecía con cada badge y comprimía las dos columnas `1fr` de los equipos).
        const bandaBadges = [
            pildoraColdStart,
            _badgeProcedenciaHtml(p.origen_captura),
            badgeExclusion,
        ].filter(Boolean).join("");
        // [ARCH-1.4.38-R3 · Rediseño Tridimensional 1X2] Ranking fiduciario del partido: los tres
        // desenlaces ordenados por P′ descendente resuelven QUIÉN es 1er, 2º y 3er favorito de
        // Q-BE. La colorimetría del desenlace real consumado se ancla a esa POSICIÓN (jamás al rol
        // nominal del resultado): 1er favorito → verde, 2º favorito (cobertura activa) → azul cian,
        // Underdog / ruptura → rojo carmín. Ante empate técnico desempata el orden canónico 1 · X · 2.
        const ordenClaves = ["LOCAL", "EMPATE", "VISITANTE"];
        const pPrimaPorClave = {
            LOCAL: Number(p.p_local || 0),
            EMPATE: Number(p.p_empate || 0),
            VISITANTE: Number(p.p_visitante || 0),
        };
        const clavesPorPRima = ordenClaves
            .map((clave, orden) => ({ clave, p: pPrimaPorClave[clave], orden }))
            .sort((a, b) => (b.p - a.p) || (a.orden - b.orden))
            .map(x => x.clave);
        const favQbeClave = clavesPorPRima[0];
        const rankReal = clavesPorPRima.indexOf(p.resultado_real);
        // [LN-QBE-100 · Decreto VAR-2026-LOBOTOMIA-RESCATE-A] FUENTE DE VERDAD ÚNICA: el vértice
        // consumado lo dicta la jerarquía estocástica SERVIDA por la bóveda (`clasificacion_triada`
        // = P_MAX / P_MID / P_LOW), no una derivación local del pintor. Un payload legado sin el
        // campo `clasificacion_triada` degrada al rango del ranking P′ (equivalencia estricta ya
        // legislada: 0 ≡ P_MAX, 1 ≡ P_MID, 2 ≡ P_LOW) ⇒ cero segunda verdad paralela y cero
        // etiqueta inventada ([GOVERNANCE-01]).
        // [LN-QBE-100 · Decreto VAR-2026-LOBOTOMIA-RESCATE-A §T2] Mapa explícito vértice → clase de
        // colorimetría de la casilla. Un vértice desconocido NO degrada en silencio a un color
        // inventado: se re-resuelve por el rango real del desenlace en el ranking P′.
        const MAPA_CLASE_TRIADA = {
            P_MAX: "box-resultado-fav",
            P_MID: "box-resultado-emp",
            P_LOW: "box-resultado-dog",
        };
        const triadaFiduciaria = (p.clasificacion_triada && MAPA_CLASE_TRIADA[p.clasificacion_triada])
            ? p.clasificacion_triada
            : (rankReal === 0 ? "P_MAX" : rankReal === 1 ? "P_MID" : "P_LOW");
        const claseResultado = MAPA_CLASE_TRIADA[triadaFiduciaria];
        // [ARCH-1.4.38 · Decreto VAR-2026-EGO-CONTRARIAN-AUDIT] Marcador factual del FAVORITO DEL
        // MERCADO: base gris inferior en la(s) casilla(s) que cotizan el máximo del consenso
        // desmarcado q_mkt (contrato plano del DTO, VAR-UI-01 aprobada). Empate técnico de mercado
        // ⇒ se marcan TODAS las casillas que alcanzan el máximo (igualdad estricta, cero desempate
        // inventado, VAR-UI-02 aprobada). La barra gris izquierda quedó RETIRADA por el rediseño
        // tridimensional: migró a la base inferior vía `.fav-base-mkt`.
        const maxQmkt = Math.max(p.q_local, p.q_empate, p.q_visitante);
        const esFavMercado = clave => (
            (clave === "LOCAL" && p.q_local === maxQmkt)
            || (clave === "EMPATE" && p.q_empate === maxQmkt)
            || (clave === "VISITANTE" && p.q_visitante === maxQmkt)
        );
        const qMktPorClave = {
            LOCAL: Number(p.q_local || 0),
            EMPATE: Number(p.q_empate || 0),
            VISITANTE: Number(p.q_visitante || 0),
        };
        const favMktClave = ordenClaves.find(clave => qMktPorClave[clave] === maxQmkt) || favQbeClave;
        // Postura fiduciaria del partido: consenso con las casas de apuestas o desmarque contrarian.
        const badgePostura = favQbeClave === favMktClave
            ? '<span class="badge-postura badge-consenso" style="background:#1E293B; border:1px solid #334155; color:#94A3B8; padding:3px 8px; border-radius:4px; font-weight:bold; font-size:10px; font-family:monospace;">🤝 Consenso</span>'
            : '<span class="badge-postura badge-contrarian" style="background:#1E1B4B; border:1px solid #6366F1; color:#A5B4FC; padding:3px 8px; border-radius:4px; font-weight:bold; font-size:10px; font-family:monospace;">⚡ Contrarian</span>';
        // [LN-QBE-100 · Decreto VAR-2026-LOBOTOMIA-RESCATE-A] Píldora del vértice consumado: rótulo y
        // colorimetría EXACTOS del vértice que la jerarquía estocástica declaró consumado por el
        // resultado de la cancha (verde P_MAX / azul P_MID / rojo P_LOW). Clase propia `badge-triada`
        // para no re-introducir la pastilla fiduciaria derogada (veto del Juez 4 del Shield).
        // [DES-QBE-072 §Glosario] ANCLA DE DEROGACIÓN (memoria documental, JAMÁS renderizada aquí):
        // "🎯 ACIERTO P_MAX" · "🛡️ RESCATE P_MID" · "💀 RUPTURA P_LOW". La vitrina publica el
        // concepto autodescriptivo del vértice consumado con la colorimetría sellada intacta.
        const MAPA_BADGE_TRIADA = {
            P_MAX: '<span class="badge-triada badge-fav" style="background:#065F46; border:1px solid #10B981; color:#34D399; padding:3px 8px; border-radius:4px; font-weight:bold; font-size:10px; font-family:monospace;">🎯 Acierto Primario</span>',
            P_MID: '<span class="badge-triada badge-emp" style="background:#0C4A6E; border:1px solid #0EA5E9; color:#38BDF8; padding:3px 8px; border-radius:4px; font-weight:bold; font-size:10px; font-family:monospace;">🛡️ Rescate de Cobertura</span>',
            P_LOW: '<span class="badge-triada badge-dog" style="background:#7F1D1D; border:1px solid #DC2626; color:#F87171; padding:3px 8px; border-radius:4px; font-weight:bold; font-size:10px; font-family:monospace;">💀 Ruptura Residual</span>',
        };
        const badgeTriadaHtml = MAPA_BADGE_TRIADA[triadaFiduciaria];
        // [LN-QBE-124 / ARCH-1.4.65] RESCATE TERRITORIAL: la Banda de Indiferencia promovió al LOCAL
        // a P_mid porque la frontera P_mid/P_low era plana (≤ ε = 1.00%) y el anfitrión jugaba con
        // un desnivel ΔAlt⁺ ≥ 1000 msnm. Se exhibe la magnitud REALMENTE consumida por λ (traza
        // V29); el pintor no deriva ni recalcula nada ([GOVERNANCE-01]).
        const badgeRescateAltitudHtml = p.rescate_indiferencia
            ? '<span class="bt-badge-rescate-alt" style="background:#082F49; border:1px solid #22D3EE; color:#67E8F9; padding:3px 8px; border-radius:4px; font-weight:bold; font-size:10px; font-family:monospace; display:inline-block; max-width:100%; margin-top:2px;" title="Banda de indiferencia ε = 1.00%: el LOCAL se promueve al Rescate de Cobertura por el Asedio Territorial Neto del anfitrión">' +
                `🛡️ Rescate de Cobertura · ΔAlt ${Math.round(Number(p.delta_alt_metros || 0))} m</span>`
            : "";
        // Columna central: Brier Score individual + Alpha del partido
        // Alpha_i = (1 − BS_QBE / BS_MKT) · 100 (guarda anti-división por cero: BS_MKT = 0 ⇒ 0%).
        const bsQbeRaw = Number(p.brier_qbe || 0);
        const bsMktRaw = Number(p.brier_mercado || 0);
        const bsQbe = bsQbeRaw.toFixed(4);
        const bsMkt = bsMktRaw.toFixed(4);
        const alphaPartido = bsMktRaw > 0 ? (1 - bsQbeRaw / bsMktRaw) * 100 : 0;
        const alphaPct = Math.abs(alphaPartido).toFixed(1);
        const signoAlpha = alphaPartido >= 0 ? "+" : "-";
        const alphaColor = alphaPartido >= 0 ? "#00E676" : "#EF4444";
        // Columna derecha: masa fiduciaria protegida por los dos primeros favoritos de Q-BE.
        const masaDto = p.masa_cobertura_pct;
        const masaPct = (masaDto === null || masaDto === undefined)
            ? ((pPrimaPorClave[favQbeClave] + pPrimaPorClave[clavesPorPRima[1]]) * 100).toFixed(1)
            : Number(masaDto).toFixed(1);
        const triadaProv = [p.r_max, p.r_mid, p.r_low].filter(Boolean).join(" ≥ ");
        // [LN-QBE-101 / ARCH-1.4.42 / DES-QBE-064 / DES-QBE-070-B / DES-QBE-071] Micro-HUD
        // soberano de la tarjeta: tetralogía fáctica de salud de insumos (OPTA · SEDE · H2H · CTX),
        // badge del driver principal y acceso al catálogo forense de 32 variables. El pintor NO
        // deriva nada: consume el bloque `atribucion_factorial` servido por el endpoint. Payload
        // legado o `disponible=false` degrada a gris NEUTRO (cero semáforo inventado).
        const atribucion = p.atribucion_factorial || null;
        const semaforosHud = (atribucion && atribucion.semaforos) || {};
        // [DES-QBE-071] EPIST sale de la vista, no del payload: el veto anti-cuarentena lo consume.
        // [DES-QBE-064-B] Limpieza semántica: el glifo BASTA. El estado viaja en `data-estado`
        // (lo consume el filtro anti-cuarentena y lo audita el Shield) y en el `title`
        // accesible; JAMÁS se imprime como texto redundante sobre el color.
        const tiraSemaforos = ["opta", "sede", "h2h", "ctx"].map(clave =>
            _glifoSemaforo(clave, semaforosHud[clave] || "NEUTRO", "hud-semaforo")
        ).join("");
        const driverPrincipal = atribucion && atribucion.driver_principal
            ? atribucion.driver_principal
            : null;
        const textoDriver = driverPrincipal && driverPrincipal.etiqueta
            ? driverPrincipal.etiqueta
            : "⚪ Sin driver (atribución no disponible)";
        const microHud = `
            <div class="bt-micro-hud">
                <div class="hud-tira-semaforos">${tiraSemaforos}</div>
                <span class="badge-driver-principal" title="Driver principal: argmax |Δ_k| de la descomposición logarítmica">${textoDriver}</span>
                <button class="btn-ver-44-vars" data-partido-id="${p.id_partido || ""}" title="Inspección forense del catálogo de 32 variables">🔬 Catálogo Fáctico (32V)</button>
            </div>`;
        const casillas = [
            { titulo: "1 LOCAL", clave: "LOCAL", p: p.p_local, q: p.q_local, o: momios.L },
            { titulo: "X EMPATE", clave: "EMPATE", p: p.p_empate, q: p.q_empate, o: momios.E },
            { titulo: "2 VISITANTE", clave: "VISITANTE", p: p.p_visitante, q: p.q_visitante, o: momios.V },
        ].map(c => {
            // [ARCH-1.4.38-R3] Geometría de dos ejes: techo blanco (favorito Q-BE, argmax P′) y
            // base gris (favorito del mercado, argmax q_mkt) conviven con la colorimetría del
            // desenlace real consumado. `box-sizing: border-box` es global: las barras no degradan
            // el layout (VAR-UI-03 preservada).
            const marcasGeometria = [
                c.clave === favQbeClave ? "fav-techo-qbe" : "",
                esFavMercado(c.clave) ? "fav-base-mkt" : "",
            ].filter(Boolean).join(" ");
            const tituloGeometria = [
                c.clave === favQbeClave ? "Favorito Q-BE (techo blanco P′)" : "",
                esFavMercado(c.clave) ? "Favorito del mercado (base gris q_mkt)" : "",
            ].filter(Boolean).join(" · ");
            return `
            <div class="bt-casilla ${p.resultado_real === c.clave ? claseResultado : "micro-box-inactivo"}${marcasGeometria ? " " + marcasGeometria : ""}"${tituloGeometria ? ` title="${tituloGeometria}"` : ""}>
                <span class="bt-casilla-titulo">${c.titulo}</span>
                <span class="bt-casilla-valor">P′ ${_pctBacktesting(c.p)}</span>
                <span class="bt-casilla-valor">q_mkt ${_pctBacktesting(c.q)}</span>
                <span class="bt-casilla-valor">momio ${momio(c.o)}</span>
            </div>`;
        }).join("");

        return `
        <div class="bt-micro-row${claseExclusion}">
            ${bandaBadges ? `<div class="bt-micro-badges">${bandaBadges}</div>` : ""}
            <div class="bt-micro-equipo">${escudo(p.local_escudo_url)}<span>${p.local}</span></div>
            <div class="bt-micro-marcador">${p.marcador}</div>
            <div class="bt-micro-equipo bt-visita"><span>${p.visitante}</span>${escudo(p.visitante_escudo_url)}</div>
            <div class="bt-micro-casillas">${casillas}</div>
            ${microHud}
            <div class="micro-partido-footer-v2">
                <div class="footer-col-postura">${badgePostura}<span style="display:inline-block; width:6px;"></span>${badgeTriadaHtml}</div>
                <div class="footer-kpi-grid">
                    <div class="footer-kpi">
                        <div class="footer-kpi-kicker">Brier (QBE / Mkt)</div>
                        <div class="footer-kpi-valor">${bsQbe} / ${bsMkt}</div>
                    </div>
                    <div class="footer-kpi">
                        <div class="footer-kpi-kicker">Masa Cubierta</div>
                        <div class="footer-kpi-valor">${masaPct}%</div>
                        ${triadaProv
                            ? `<div class="footer-kpi-nota">${triadaProv}${p.clasificacion_triada
                                ? ` (${GLOSARIO_VERTICES_VISOR[p.clasificacion_triada] || p.clasificacion_triada})`
                                : ""}</div>`
                            : ""}
                        ${badgeRescateAltitudHtml}
                    </div>
                    <div class="footer-kpi">
                        <div class="footer-kpi-kicker">Alpha</div>
                        <div class="footer-kpi-valor" style="color:${alphaColor};">${signoAlpha}${alphaPct}%</div>
                    </div>
                </div>
            </div>
        </div>`;
    }).join("");

    // [DES-QBE-072] Cabecera de jornada en clave de GLOSARIO autodescriptivo: la masa es
    // probabilística ex-ante y el desglose nombra los tres destinos del símplex Δ².
    contenedor.innerHTML = `
        <div class="bt-micro-head">
            Jornada ${jornada.jornada} · ${jornada.total_partidos} partidos concluidos ·
            Masa Probabilística Ex-Ante <strong>${Number(jornada.masa_cobertura_pct || 0).toFixed(2)}%</strong>
            (Acierto Primario ${Number(jornada.pct_p_max || 0).toFixed(2)}% ·
            Rescate de Cobertura ${Number(jornada.pct_p_mid || 0).toFixed(2)}% ·
            Ruptura Residual ${Number(jornada.pct_p_low || 0).toFixed(2)}%)
            · <span style="color:#94A3B8; font-size:10px;">[Rescate: ${Number(jornada.n_p_mid_empate || 0)} Emp ·
            ${Number(jornada.n_p_mid_rival || 0)} Riv]</span>
            · Alpha ${Number(jornada.alpha_calibracion_pct || 0).toFixed(2)}%
        </div>
        ${bloques}`;

    // [DES-QBE-064] Acceso al desglose forense: cada tarjeta abre el modal del partido.
    contenedor.querySelectorAll(".btn-ver-44-vars").forEach(btn => {
        btn.addEventListener("click", () => abrirModal44Variables(btn.getAttribute("data-partido-id")));
    });
}

/* ==========================================================================
   [LN-QBE-101 / ARCH-1.4.42 / DES-QBE-064 / DES-QBE-070-B] MODAL FORENSE DEL CATÁLOGO DE 32V
   Régimen [DBBD-FUNGIBLE]: el pintor sólo transcribe el bloque servido por el
   endpoint (`atribucion_factorial`). Cero derivación local, cero cifra inventada:
   la evidencia ausente se declara `SIN EVIDENCIA` tal como la bóveda la publica.
   ========================================================================== */
const COLORES_SEMAFORO_SALUD = {
    VERDE: "#10B981",
    AMARILLO: "#F59E0B",
    ROJO: "#EF4444",
    NEUTRO: "#94A3B8",
};

/* ==========================================================================
   [LN-QBE-102 / ARCH-1.4.43 / DES-QBE-065] SELLO DE PROCEDENCIA DE LA EVIDENCIA
   Régimen [DBBD-FUNGIBLE]. Única fuente de verdad de los dos rótulos legislados:
   `EN_VIVO` ⇒ captura en ventanilla (blindada por `LIVE_PROTECTION_LOCK`);
   cualquier otro valor (incluido `null`) ⇒ reconstrucción histórica. Regla de
   honestidad visual: el badge nunca se pinta en verde ni simula ventanilla.
   ========================================================================== */
const PROCEDENCIA_CAPTURA_EN_VIVO = "EN_VIVO";
const ETIQUETAS_PROCEDENCIA = {
    vivo: "🔴 EN VIVO",
    historico: "🏛️ HISTÓRICO",
};

function _claseProcedencia(origen) {
    return origen === PROCEDENCIA_CAPTURA_EN_VIVO ? "badge-procedencia-vivo" : "badge-procedencia-hist";
}

function _textoProcedencia(origen) {
    return origen === PROCEDENCIA_CAPTURA_EN_VIVO
        ? ETIQUETAS_PROCEDENCIA.vivo
        : ETIQUETAS_PROCEDENCIA.historico;
}

/** Devuelve el badge como nodo: el texto se inyecta con `textContent` (cero `innerHTML`). */
function _badgeProcedencia(origen) {
    const badge = document.createElement("span");
    badge.className = `badge-procedencia ${_claseProcedencia(origen)}`;
    badge.textContent = _textoProcedencia(origen);
    badge.title = origen === PROCEDENCIA_CAPTURA_EN_VIVO
        ? "Evidencia capturada en ventanilla · blindada contra sobreescritura histórica [LN-QBE-102]"
        : "Evidencia reconstruida con posterioridad · no blindada [LN-QBE-102]";
    return badge;
}

/** Variante en cadena para las plantillas de la parrilla: sólo constantes literales. */
function _badgeProcedenciaHtml(origen) {
    return `<span class="badge-procedencia ${_claseProcedencia(origen)}">${_textoProcedencia(origen)}</span>`;
}

// [DES-QBE-071] Tetralogía fáctica del panel de salud de datos del modal. `epist` se retira de la
// vitrina: el backend lo sigue publicando y el filtro anti-cuarentena ([DES-QBE-067]) lo lee por
// acceso indexado, de modo que el veredicto epistémico gobierna sin exhibirse.
const ETIQUETAS_SEMAFORO_32 = {
    opta: "OPTA",
    sede: "SEDE",
    h2h: "H2H",
    ctx: "CTX",
};

const COLORES_ESTADO_32 = {
    // [LN-QBE-102 / DES-QBE-065] `EVALUADO` = insumo fáctico publicado y consumido por el motor
    // (iluminación verde). Los tres estados preexistentes conservan su colorimetría sellada.
    EVALUADO: "#10B981",
    VALIDADO: "#10B981",
    DERIVADO: "#38BDF8",
    "SIN EVIDENCIA": "#94A3B8",
};

function _partidoBacktestingCache(idPartido) {
    const jornadas = (backtestingReportCache && backtestingReportCache.jornadas) || [];
    for (const jornada of jornadas) {
        for (const partido of (jornada.partidos || [])) {
            if (String(partido.id_partido) === String(idPartido)) return { partido, jornada };
        }
    }
    return null;
}

function _valor32(valor) {
    if (valor === null || valor === undefined) return '<span style="color:#475569;">—</span>';
    const numero = Number(valor);
    return Number.isFinite(numero) ? numero.toFixed(2) : String(valor);
}

function _delta32(valor) {
    if (valor === null || valor === undefined) return '<span style="color:#475569;">—</span>';
    const numero = Number(valor);
    if (!Number.isFinite(numero)) return String(valor);
    const color = numero >= 0 ? "#10B981" : "#EF4444";
    return `<span style="color:${color}; font-family:monospace;">${numero >= 0 ? "+" : ""}${numero.toFixed(4)}</span>`;
}

/**
 * [DES-QBE-064-B] Glifo soberano de un semáforo: `● DIMENSIÓN` teñido por la colorimetría
 * sellada de `COLORES_SEMAFORO_SALUD`. Única fuente de verdad del DOM de semáforos: la
 * parrilla micro (`.hud-semaforo`) y el panel del modal de 32V (`.vars44-semaforo`) la
 * consumen por igual. Prohibido imprimir el estado (`VERDE` / `AMARILLO` / `ROJO` / `NEUTRO`)
 * como texto visible: el dato viaja en `data-estado` (gobierno) y en `title` (accesibilidad),
 * nunca en el layout.
 */
function _glifoSemaforo(clave, estado, clase) {
    const nombre = ETIQUETAS_SEMAFORO_32[clave] || String(clave).toUpperCase();
    const color = COLORES_SEMAFORO_SALUD[estado] || COLORES_SEMAFORO_SALUD.NEUTRO;
    return `<span class="${clase || "vars44-semaforo"}" data-semaforo="${nombre}" ` +
        `data-estado="${estado}" title="${nombre}: ${estado}" ` +
        `style="color:${color};">● ${nombre}</span>`;
}

function _bloqueSemaforos32(semaforos) {
    return Object.keys(ETIQUETAS_SEMAFORO_32).map(clave =>
        _glifoSemaforo(clave, (semaforos && semaforos[clave]) || "NEUTRO")
    ).join("");
}

function _badgeDimension32(dimension) {
    // [DES-QBE-066 / LN-QBE-104] Badge bicolor del acordeón forense. Construcción DOM pura: los
    // contadores llegan servidos y se validan antes de pintarse; cero hidratación por marcado crudo.
    // «EVALUADA» exige evidencia REALMENTE evaluada: `tiene_datos` por sí solo no basta. Una
    // dimensión declarada sin una sola variable evaluada (o con denominador nulo) NO es un «0/0
    // evaluadas» —que finge una medición— sino `SIN EVALUAR` ([GOVERNANCE-01]: cero maquillaje).
    const evaluadas = Number(dimension && dimension.variables_evaluadas);
    const total = Number(dimension && dimension.total_variables);
    const coherente = Number.isFinite(evaluadas) && Number.isFinite(total) &&
        total > 0 && evaluadas > 0 && evaluadas <= total;
    const conDatos = Boolean(dimension && dimension.tiene_datos === true && coherente);
    const badge = document.createElement("span");
    badge.className = conDatos ? "badge-dim badge-dim-evaluada" : "badge-dim badge-dim-fase6";
    badge.textContent = conDatos ? `${evaluadas}/${total} evaluadas` : "SIN EVALUAR";
    return badge;
}

/**
 * [ARCH-1.4.63] Acordeón dimensional: el Card es el ÚNICO vehículo de lectura por dimensión.
 * La tabla de 7 columnas sellada por [DES-QBE-064] se DEROGÓ de este nodo (duplicaba, dimensión a
 * dimensión, la misma transcripción que el Card ya sirve) y sobrevive UNA sola vez, consolidada,
 * en el soporte forense del modal (`_soporteForense32`). El badge bicolor se hidrata igual sobre
 * `vars44-badge-slot`: la geometría del acordeón no cambia.
 */
function _tablaDimension32(dimension) {
    const indice = String(dimension && dimension.dimension ? dimension.dimension : "");
    return `
        <details class="vars44-dimension" data-dimension="${indice}">
            <summary>
                <span class="vars44-dim-titulo">${dimension.titulo || dimension.dimension}</span>
                <span class="vars44-dim-meta">
                    <span class="vars44-badge-slot" data-indice-badge="${indice}"></span>
                    <span class="vars44-dim-conteo">${dimension.conteo} variables · ${dimension.dimension}</span>
                </span>
            </summary>
            ${_cardDimension32(dimension)}
        </details>`;
}

/**
 * [ARCH-1.4.63] Soporte forense CONSOLIDADO: una sola tabla con las siete columnas selladas por
 * [DES-QBE-064] (ID, Variable, Local, Visita, Z-Score, Origen, Estado, Impacto) para las SEIS
 * dimensiones. Transcribe las celdas servidas VERBATIM: cero derivación, cero normalización, cero
 * imputación — es soporte de auditoría, no de lectura ([GOVERNANCE-01]).
 */
function _soporteForense32(dimensiones) {
    const bloques = (dimensiones || []).map(dimension => {
        const filas = (dimension.variables || []).map(variable => {
            const colorEstado = COLORES_ESTADO_32[variable.estado] || "#94A3B8";
            return `
                <tr>
                    <td class="vars44-col-id">${variable.id}</td>
                    <td class="vars44-col-variable">${variable.variable}</td>
                    <td class="vars44-col-num">${_valor32(variable.local)}</td>
                    <td class="vars44-col-num">${_valor32(variable.visita)}</td>
                    <td class="vars44-col-num">${_valor32(variable.z_score)}</td>
                    <td class="vars44-col-origen">${variable.origen || "—"}</td>
                    <td class="vars44-col-estado" style="color:${colorEstado};">${variable.estado || "—"}</td>
                    <td class="vars44-col-impacto">${variable.impacto || "—"}</td>
                </tr>`;
        }).join("");
        return `
            <tbody>
                <tr><td colspan="8" class="vars44-soporte-familia">${dimension.titulo || dimension.dimension}</td></tr>
                ${filas}
            </tbody>`;
    }).join("");
    if (!bloques) return "";
    return `
        <details class="vars44-soporte">
            <summary>Soporte forense consolidado · 7 columnas [DES-QBE-064] / [ARCH-1.4.63]</summary>
            <table class="vars44-tabla vars44-tabla-soporte">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Variable</th>
                        <th>Local</th>
                        <th>Visita</th>
                        <th>Z-Score</th>
                        <th>Origen</th>
                        <th>Estado</th>
                        <th>Impacto</th>
                    </tr>
                </thead>
                ${bloques}
            </table>
        </details>`;
}

function _hidratarBadgesDimension32(contenedor, dimensiones) {
    // [DES-QBE-066] Clase bicolor + badge construidos en DOM sobre la geometría sellada de
    // [DES-QBE-064]: la transcripción del bloque servido nunca se hidrata por `innerHTML`.
    if (!contenedor) return;
    const porIndice = {};
    (dimensiones || []).forEach(dimension => {
        if (dimension && dimension.dimension) porIndice[String(dimension.dimension)] = dimension;
    });
    contenedor.querySelectorAll(".vars44-badge-slot").forEach(ranura => {
        const dimension = porIndice[ranura.dataset.indiceBadge];
        if (!dimension) return;
        ranura.replaceWith(_badgeDimension32(dimension));
    });
    contenedor.querySelectorAll("details.vars44-dimension").forEach(acordeon => {
        const dimension = porIndice[acordeon.dataset.dimension];
        // [LN-QBE-105] Un solo criterio de verdad: el semáforo del acordeón se ilumina leyendo el
        // badge YA hidratado (misma coherencia `evaluadas/total`), sin recalcular ni duplicar la
        // regla. Un `tiene_datos` servido sin evidencia evaluada no enciende la dimensión.
        const badge = acordeon.querySelector(".badge-dim");
        const conDatos = Boolean(badge && badge.classList.contains("badge-dim-evaluada"));
        acordeon.classList.add(conDatos ? "dim-con-datos" : "dim-fase6");
        acordeon.dataset.tieneDatos = String(conDatos);
    });
}

/* ==========================================================================
   [DES-QBE-070-B] CARDS SEMÁNTICOS POLIMÓRFICOS DEL CATÁLOGO DE 32V (FASE C)
   --------------------------------------------------------------------------
   Hero Card que antecede al soporte forense de 7 columnas sellado por [DES-QBE-064]:
   el soporte SOBREVIVE (enmienda, no deroga) como UNA sola tabla consolidada del modal
   —`_soporteForense32`—, nunca replicada dimensión a dimensión ([ARCH-1.4.63]). El Card
   sólo TRANSCRIBE las celdas servidas de `atribucion_factorial.variables_44`; tiene
   prohibido derivar λ, Δlog, xG, récords o altitudes absolutas ([GOVERNANCE-01] /
   [ARCH-1.4.57]). Cero hidratación de datos de red por marcado crudo: todo el
   marcado sale de literales de plantilla y de `_valor32`, que preserva las celdas
   en cadena servidas (`'54.0%'`, `'+0.0 d'`, `'105m'`, `'3V - 1E - 0D'`).
   SEIS familias canónicas: 𝒯_Vol, 𝒯_Rem, 𝒯_Def, 𝒯_Por, 𝒯_Spc (FASE 6 atenuada)
   y 𝒯_Ctx (consolida las extintas 𝒯_Shk y 𝒯_H2H).
   ========================================================================== */

/** Sufijo latino de la familia canónica: `𝒯_Vol` ⇒ `Vol` ([LN-QBE-101].P.4). */
function _familiaCard32(dimension) {
    const codigo = String((dimension && dimension.dimension) || "");
    return codigo.slice(-3);
}

/** Variable del catálogo servido por id canónico (`V01`…`V32`); `null` si no se publicó. */
function _variable32(dimension, id) {
    const variables = (dimension && dimension.variables) || [];
    return variables.find(variable => String(variable.id) === id) || null;
}

/** Celda `local` transcrita por `_valor32` (preserva los `str` servidos, degrada `null` a `—`). */
function _celda32(dimension, id) {
    const variable = _variable32(dimension, id);
    return variable ? _valor32(variable.local) : '<span style="color:#475569;">—</span>';
}

/** Porcentaje YA servido (`'54.0%'`): lectura del carril, cero normalización. `null` si no lo publica. */
function _porcentaje32(variable) {
    if (!variable) return null;
    const numero = parseFloat(String(variable.local));
    return Number.isFinite(numero) ? numero : null;
}

/**
 * 𝒯_Vol — barra dual de posesión efectiva (`V01`). [ARCH-1.4.63] Los dos porcentajes servidos se
 * NORMALIZAN por complemento bipartito: la posesión de un partido SIEMPRE suma 100, de modo que un
 * par servido que no cierra (`54.0%` / `45.0%` por redondeo de origen) sigue siendo una posesión
 * medible, no una contradicción. El ancho es `local / (local + visita) * 100`: una sola magnitud
 * independiente (`visita` queda determinada por el complemento). Con Σ ≤ 0 no hay porcentaje que
 * exhibir: se declara `Posesión sin evidencia` en lugar de fingir un 50/50 ([GOVERNANCE-01]).
 */
function _cardPosesion32(dimension) {
    const variable = _variable32(dimension, "V01");
    const local = _porcentaje32(variable);
    const visita = variable ? parseFloat(String(variable.visita)) : null;
    const total = local !== null && Number.isFinite(visita) ? local + visita : 0;
    const proporcionLocal = total > 0 ? (local / total) * 100 : null;
    const anchoLocal = proporcionLocal === null ? 50 : proporcionLocal;
    const anchoVisita = proporcionLocal === null ? 50 : 100 - proporcionLocal;
    const rotulo = proporcionLocal === null
        ? "Posesión sin evidencia"
        : `Posesión ${proporcionLocal.toFixed(1)}% · ${(100 - proporcionLocal).toFixed(1)}%`;
    return `
        <div class="barra-posesion-dual" title="V01 · posesión efectiva normalizada [LN-QBE-102] / [ARCH-1.4.63]">
            <div class="barra-posesion-carril barra-posesion-local" style="width:${anchoLocal.toFixed(1)}%;"></div>
            <div class="barra-posesion-carril barra-posesion-visita" style="width:${anchoVisita.toFixed(1)}%;"></div>
            <span class="barra-posesion-rotulo">${rotulo}</span>
        </div>`;
}

/**
 * 𝒯_Rem / 𝒯_Def / 𝒯_Por — balanza bilateral de una variable servida (`V06` xG, `V12` xGA, `V18`
 * atajadas). El signo se LEE comparando las dos celdas servidas: el cliente no calcula
 * diferenciales ni normaliza unidades. Sin dos celdas numéricas la balanza declara `s/d`.
 */
function _balanzaGoles32(dimension, id, etiqueta) {
    const variable = _variable32(dimension, id);
    const celdaLocal = variable ? variable.local : null;
    const celdaVisita = variable ? variable.visita : null;
    const numeroLocal = parseFloat(String(celdaLocal));
    const numeroVisita = parseFloat(String(celdaVisita));
    const comparable = Number.isFinite(numeroLocal) && Number.isFinite(numeroVisita);
    const signo = comparable
        ? (numeroLocal === numeroVisita ? "=" : (numeroLocal > numeroVisita ? ">" : "<"))
        : "s/d";
    const clase = signo === ">"
        ? "balanza-favorece-local"
        : (signo === "<" ? "balanza-favorece-visita" : "balanza-neutra");
    const lectura = signo === "s/d"
        ? "s/d"
        : (signo === ">" ? "favorece local" : (signo === "<" ? "favorece visita" : "paridad"));
    return `
        <div class="balanza-goles-badge ${clase}" title="Balanza de ${etiqueta} · celdas servidas ${id}">
            <span class="balanza-celda balanza-local">${_valor32(celdaLocal)}</span>
            <span class="balanza-signo">${etiqueta} · ${lectura}</span>
            <span class="balanza-celda balanza-visita">${_valor32(celdaVisita)}</span>
        </div>`;
}

/**
 * `𝒯_Ctx` — memoria longitudinal consolidada: `V26` (`3V - 1E - 0D`), `V27` (Δgoles H2H) y `V28`
 * (récord del visitante en la sede) transcritos VERBATIM. El cliente no suma ni resta un solo gol
 * ([LN-QBE-105] / [ARCH-1.4.61]).
 */
function _recordH2HCard32(dimension) {
    const record = _celda32(dimension, "V26");
    const goles = _celda32(dimension, "V27");
    const sede = _celda32(dimension, "V28");
    return `
        <div class="balanza-goles-badge balanza-neutra" title="Memoria H2H servida (V26 · V27 · V28) [LN-QBE-105]">
            <span class="balanza-celda balanza-local">${record}</span>
            <span class="balanza-signo">H2H · Δgoles ${goles}</span>
            <span class="balanza-celda balanza-visita">${sede}</span>
        </div>`;
}

/**
 * `𝒯_Ctx` — shocks REALMENTE aplicados por el motor (`V29` = ΔAlt⁺, `V30` = ΔDías) y la varianza
 * de puntos esperados (`V32` = ΔxPTS). La altitud ABSOLUTA de la sede no cruza el DTO
 * ([ARCH-1.4.57], deuda declarada): no se finge. Absorbe la extinta familia `𝒯_Shk`.
 */
function _fichasContextoCard32(dimension) {
    const altitud = _celda32(dimension, "V29");
    const descanso = _celda32(dimension, "V30");
    const xpts = _celda32(dimension, "V32");
    return `
        <div class="card-fichas-contexto">
            <div class="card-ficha card-ficha-altitud" title="V29 · ΔAltitud⁺ realmente aplicado al modelo">
                <span class="card-ficha-rotulo">Altitud</span>
                <span class="card-ficha-valor">${altitud}</span>
            </div>
            <div class="card-ficha card-ficha-descanso" title="V30 · ΔDías realmente aplicado al modelo">
                <span class="card-ficha-rotulo">Descanso</span>
                <span class="card-ficha-valor">${descanso}</span>
            </div>
            <div class="card-ficha" title="V32 · varianza ΔxPTS servida por el motor">
                <span class="card-ficha-rotulo">ΔxPTS</span>
                <span class="card-ficha-valor">${xpts}</span>
            </div>
        </div>`;
}

/** Rejilla de transcripción de los ids indicados: los no publicados se omiten en silencio. */
function _rejillaCard32(dimension, ids) {
    const filas = (ids || []).map(id => {
        const variable = _variable32(dimension, id);
        if (!variable) return "";
        const color = COLORES_ESTADO_32[variable.estado] || "#94A3B8";
        return `
            <div class="card-dato" title="${variable.variable || ""}">
                <span class="card-dato-id">${variable.id}</span>
                <span class="card-dato-nombre">${variable.variable || "—"}</span>
                <span class="card-dato-valor" style="color:${color};">${_valor32(variable.local)}</span>
                <span class="card-dato-valor">${_valor32(variable.visita)}</span>
            </div>`;
    }).join("");
    return filas ? `<div class="card-rejilla-datos">${filas}</div>` : "";
}

/** Rejilla genérica de la dimensión: hasta seis insumos servidos, sin fabricar renglones. */
function _rejillaCardTodos32(dimension) {
    const ids = ((dimension && dimension.variables) || []).slice(0, 6).map(variable => variable.id);
    return _rejillaCard32(dimension, ids);
}

/**
 * [DES-QBE-070-B] Despachador polimórfico del Hero Card: la anatomía depende de la familia `𝒯_*` de
 * la dimensión. El soporte forense de [DES-QBE-064] se pinta UNA sola vez, consolidado, en
 * `_soporteForense32` ([ARCH-1.4.63]): el acordeón ya no replica una tabla por dimensión. Sin una
 * sola variable `EVALUADO` el Card se atenúa
 * (`card-fase6-muted`) y declara `○ 0 de N (Fase 6)`: jamás un cero fabricado ni un porcentaje
 * aparente sobre denominador vacío ([GOVERNANCE-01] / [DES-QBE-066]).
 */
function _cardDimension32(dimension) {
    if (!dimension) return "";
    const familia = _familiaCard32(dimension);
    const evaluadas = Number(dimension.variables_evaluadas);
    const total = Number(dimension.total_variables);
    const conEvidencia = Number.isFinite(evaluadas) && Number.isFinite(total) &&
        evaluadas > 0 && total > 0;
    const clases = ["card-semantico-dimension", `card-familia-${familia.toLowerCase()}`];
    if (!conEvidencia) clases.push("card-fase6-muted");
    let anatomia = _rejillaCardTodos32(dimension);
    if (familia === "Vol") {
        anatomia = _cardPosesion32(dimension) + _rejillaCard32(dimension, ["V02", "V03", "V04", "V05"]);
    } else if (familia === "Rem") {
        anatomia = _balanzaGoles32(dimension, "V06", "xG") +
            _rejillaCard32(dimension, ["V07", "V08", "V09", "V10", "V11"]);
    } else if (familia === "Def") {
        anatomia = _balanzaGoles32(dimension, "V12", "xGA") +
            _rejillaCard32(dimension, ["V13", "V14", "V15", "V16"]);
    } else if (familia === "Por") {
        anatomia = _balanzaGoles32(dimension, "V18", "Atajadas") +
            _rejillaCard32(dimension, ["V17", "V19", "V20"]);
    } else if (familia === "Spc") {
        // [DES-QBE-070-B] `𝒯_Spc` (V21-V25) está en FASE 6: el Card se atenúa SIEMPRE —régimen de
        // evidencia, no conteo servido— y exhibe la rejilla de transcripción de las cinco celdas
        // sin fabricar un solo cero. Es el espejo del sandbox `[ARCH-1.4.62]`.
        anatomia = _rejillaCard32(dimension, ["V21", "V22", "V23", "V24", "V25"]);
        if (!clases.includes("card-fase6-muted")) clases.push("card-fase6-muted");
    } else if (familia === "Ctx") {
        // `𝒯_Ctx` consolida las familias extintas `𝒯_Shk` y `𝒯_H2H`: memoria longitudinal
        // (V26-V28), shocks aplicados (V29 altitud, V30 descanso), varianza ΔxPTS (V32) y la
        // forma 5P (V31) como rejilla. Todas las celdas son del catálogo de 32.
        anatomia = _recordH2HCard32(dimension) +
            _fichasContextoCard32(dimension) +
            _rejillaCard32(dimension, ["V31"]);
    }
    const denominador = Number.isFinite(total) && total > 0 ? total : 0;
    const conteo = conEvidencia
        ? `${evaluadas} de ${total} evaluadas`
        : `○ 0 de ${denominador} (Fase 6)`;
    return `
        <div class="${clases.join(" ")}" data-familia="${familia}">
            <div class="card-semantico-cabecera">
                <span class="card-semantico-titulo">${dimension.titulo || dimension.dimension || ""}</span>
                <span class="card-semantico-conteo">${conteo}</span>
            </div>
            ${anatomia}
        </div>`;
}

function abrirModal44Variables(idPartido) {
    const modal = document.getElementById("modal-44-variables");
    const cuerpo = document.getElementById("vars44-cuerpo");
    const titulo = document.getElementById("vars44-titulo");
    if (!modal || !cuerpo) return;

    const hallado = _partidoBacktestingCache(idPartido);
    if (!hallado) {
        if (titulo) titulo.textContent = "⚪ Partido no localizado en el reporte de calibración";
        const origenHuerfano = document.getElementById("vars44-origen");
        if (origenHuerfano) origenHuerfano.textContent = "";
        cuerpo.innerHTML = `
            <div class="vars44-aviso">
                Sin evidencia en caché para el partido <strong>${idPartido || "—"}</strong>.
                Recargue el reporte de backtesting antes de abrir la inspección forense.
            </div>`;
        modal.style.display = "block";
        return;
    }

    const partido = hallado.partido;
    const jornada = hallado.jornada;
    if (titulo) {
        titulo.textContent = `🔬 ${partido.local} vs ${partido.visitante} · Jornada ${jornada.jornada} · ${partido.marcador || "—"}`;
    }

    const atribucion = partido.atribucion_factorial || null;
    const variables44 = (atribucion && atribucion.variables_44) || null;
    const dimensiones = (variables44 && variables44.dimensiones) || [];
    const descomposicion = (atribucion && atribucion.descomposicion_log) || {};
    const driver = (atribucion && atribucion.driver_principal) || null;
    const disponible = Boolean(atribucion && atribucion.disponible);

    // [LN-QBE-102 / DES-QBE-065] Sub-rayado de procedencia: el sello lo publica el endpoint
    // (casilla micro o bloque de atribución). Ausente ⇒ se declara "no publicado"; jamás se
    // asume ventanilla. El nodo se inyecta con `textContent`, cero `innerHTML` con datos de red.
    const origenCaptura = partido.origen_captura || (atribucion && atribucion.origen_captura) || null;
    const subrayadoOrigen = document.getElementById("vars44-origen");
    if (subrayadoOrigen) {
        subrayadoOrigen.textContent = "";
        subrayadoOrigen.appendChild(_badgeProcedencia(origenCaptura));
        const sello = document.createElement("span");
        sello.className = "vars44-origen-sello";
        sello.textContent = origenCaptura
            ? `sello: ${origenCaptura}`
            : "sello no publicado (traza legada)";
        subrayadoOrigen.appendChild(sello);
    }

    // Honestidad de degradación ([GOVERNANCE-01]): sin factores persistidos la atribución se
    // declara NEUTRA; el catálogo se pinta igual, sin fabricar una sola cifra.
    const aviso = disponible
        ? `<div class="vars44-aviso vars44-aviso-ok">
                ✅ Atribución disponible · origen de factores:
                <strong>${atribucion.origen_factores || "—"}</strong> · driver principal:
                <strong>${driver && driver.etiqueta ? driver.etiqueta : "—"}</strong>
           </div>`
        : `<div class="vars44-aviso">
                ⚪ Atribución NEUTRA: la bóveda no publicó el vector de factores de entrada de este
                partido (<code>disponible = false</code>). El catálogo se exhibe sin fabricar cifras.
           </div>`;

    const filasDescomposicion = [
        ["Δ Ofensiva", descomposicion.delta_ofensiva],
        ["Δ Defensiva", descomposicion.delta_defensiva],
        ["Δ Contexto", descomposicion.delta_contexto],
        ["Δ Neto ≡ ln(λ_H/λ_A)", descomposicion.delta_neto_total],
        ["Residuo no atribuido", descomposicion.residuo_no_atribuido],
    ].map(([etiqueta, valor]) => `
        <tr>
            <td class="vars44-col-variable">${etiqueta}</td>
            <td class="vars44-col-num">${_delta32(valor)}</td>
        </tr>`).join("");

    const total = (variables44 && variables44.total_variables) || 0;
    cuerpo.innerHTML = `
        ${aviso}
        <div class="vars44-grid">
            <div class="vars44-panel">
                <div class="vars44-panel-titulo">Descomposición logarítmica</div>
                <table class="vars44-tabla vars44-tabla-descomposicion">
                    <thead><tr><th>Componente</th><th>Δ (log)</th></tr></thead>
                    <tbody>${filasDescomposicion}</tbody>
                </table>
            </div>
            <div class="vars44-panel">
                <div class="vars44-panel-titulo">Semáforos de salud de datos</div>
                <div class="vars44-semaforos">${_bloqueSemaforos32(atribucion && atribucion.semaforos)}</div>
                <div class="vars44-panel-titulo" style="margin-top:14px;">Catálogo forense</div>
                <div class="vars44-resumen">
                    <strong>${total}</strong> variables en <strong>${dimensiones.length}</strong>
                    dimensiones canónicas.
                </div>
            </div>
        </div>
        <div class="vars44-acordeon">
            ${dimensiones.length
                ? dimensiones.map(_tablaDimension32).join("")
                : `<div class="vars44-aviso">⚪ El endpoint no publicó el catálogo de 32 variables de este partido.</div>`}
        </div>
        ${_soporteForense32(dimensiones)}`;

    // [DES-QBE-066] Hidratación del badge bicolor: se pinta en DOM tras transcribir el bloque.
    _hidratarBadgesDimension32(cuerpo, dimensiones);

    modal.style.display = "block";
}

function cerrarModal44Variables() {
    const modal = document.getElementById("modal-44-variables");
    if (modal) modal.style.display = "none";
}

window.abrirModal44Variables = abrirModal44Variables;
window.cerrarModal44Variables = cerrarModal44Variables;

// [DES-QBE-064] Cierre por tecla `Escape`, mismo contrato que el botón `Cerrar`.
document.addEventListener("keydown", evento => {
    if (evento.key !== "Escape") return;
    const modal = document.getElementById("modal-44-variables");
    if (modal && modal.style.display === "block") cerrarModal44Variables();
});
