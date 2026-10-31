/* Focos de Alerta - interfaz web */
"use strict";

const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];

const estado = {
  config: null,
  reportes: [],
  tab: "ruta",
  modo: null,            // 'origen' | 'destino' | null
  origen: null, destino: null,
  reporte: { latlng: null, severidad: 2 },
  vista: "marcadores",
  filtroCats: new Set(),
};

// Identificador anonimo del dispositivo (solo para evitar votos repetidos).
function dispositivo() {
  try {
    let id = localStorage.getItem("focos-dispositivo");
    if (!id) { id = crypto.randomUUID(); localStorage.setItem("focos-dispositivo", id); }
    return id;
  } catch { return "sin-almacenamiento"; }
}

async function api(ruta, opciones = {}) {
  const r = await fetch(ruta, {
    ...opciones,
    headers: { "Content-Type": "application/json", "X-Dispositivo": dispositivo(), ...(opciones.headers || {}) },
  });
  const datos = await r.json().catch(() => ({}));
  return { ok: r.ok, status: r.status, datos };
}

function aviso(texto, error = false) {
  const a = $("#aviso");
  a.textContent = texto; a.className = error ? "error" : ""; a.hidden = false;
  clearTimeout(aviso.t); aviso.t = setTimeout(() => (a.hidden = true), 3800);
}

function escapar(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function edadTexto(dias) {
  if (dias === 0) return "hoy";
  if (dias === 1) return "ayer";
  if (dias < 30) return `hace ${dias} días`;
  const m = Math.round(dias / 30);
  return `hace ${m} ${m === 1 ? "mes" : "meses"}`;
}

const horaSeleccionada = () => ($("#hora").value === "" ? estado.config.hora_servidor : Number($("#hora").value));

// ---------------------------------------------------------------------------
// Mapa
// ---------------------------------------------------------------------------
const mapa = L.map("mapa", { zoomControl: true });
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19, attribution: "© colaboradores de OpenStreetMap",
}).addTo(mapa);

const capaFocos = L.layerGroup().addTo(mapa);
const capaTramos = L.layerGroup();
const capaRuta = L.layerGroup().addTo(mapa);
const capaPuntos = L.layerGroup().addTo(mapa);
let capaCalor = null;

const iconoPin = (clase, letra) => L.divIcon({ className: "", html: `<div class="pin ${clase}">${letra}</div>`, iconSize: [26, 26], iconAnchor: [13, 13] });
let marcaOrigen = null, marcaDestino = null, marcaReporte = null;

function iconoFoco(r) {
  const cat = estado.config.categorias[r.categoria];
  const tenue = r.intensidad < 0.25 ? " tenue" : "";
  return L.divIcon({
    className: "", iconSize: [28, 28], iconAnchor: [14, 28], popupAnchor: [0, -26],
    html: `<div class="marcador ${cat.grupo}${tenue}"><span>${cat.icono}</span></div>`,
  });
}

function popupFoco(r) {
  const cat = estado.config.categorias[r.categoria];
  const sev = ["", "Leve", "Moderada", "Grave"][r.severidad];
  return `<div class="popup">
    <h4>${cat.icono} ${escapar(cat.nombre)}</h4>
    <p>${escapar(r.descripcion) || "<i>Sin descripción</i>"}</p>
    <p><small>${cat.grupo === "fisico" ? "Factor físico" : "Incidente"} · ${sev} · ${edadTexto(r.edad_dias)}
      · ${r.confirmaciones} confirmación(es)<br>Peso actual en el cálculo: <b>${r.intensidad.toFixed(2)}</b></small></p>
    ${r.origen === "demo" ? '<p class="demo">Dato simulado para demostración</p>' : ""}
    <div class="acciones">
      <button onclick="votar(${r.id}, 'confirmar')">👍 Sigue ahí</button>
      <button onclick="votar(${r.id}, 'resuelto')">✔ Ya no existe</button>
    </div></div>`;
}

window.votar = async (id, tipo) => {
  const { ok, datos } = await api(`/api/reportes/${id}/votar`, { method: "POST", body: JSON.stringify({ tipo }) });
  aviso(datos.mensaje || "Error al votar", !ok);
  if (ok) { mapa.closePopup(); await cargarReportes(); }
};

function reportesFiltrados() {
  const dias = $("#filtro-dias").value;
  return estado.reportes.filter((r) =>
    estado.filtroCats.has(r.categoria) && (dias === "" || r.edad_dias <= Number(dias)));
}

async function dibujarFocos() {
  capaFocos.clearLayers();
  capaTramos.clearLayers();
  if (capaCalor) { mapa.removeLayer(capaCalor); capaCalor = null; }
  mapa.removeLayer(capaTramos);
  const lista = reportesFiltrados();

  if (estado.vista === "marcadores") {
    lista.forEach((r) => L.marker([r.lat, r.lon], { icon: iconoFoco(r) }).bindPopup(popupFoco(r)).addTo(capaFocos));
  } else if (estado.vista === "calor") {
    capaCalor = L.heatLayer(lista.map((r) => [r.lat, r.lon, Math.min(1, r.intensidad)]), {
      radius: 28, blur: 22, maxZoom: 17, minOpacity: 0.25,
      gradient: { 0.2: "#fde68a", 0.5: "#f59e0b", 0.8: "#dc2626", 1: "#7f1d1d" },
    }).addTo(mapa);
  } else {
    const { datos } = await api(`/api/tramos-riesgo?hora=${horaSeleccionada()}`);
    (datos || []).forEach((t) => {
      const color = t.r >= 1 ? "#7f1d1d" : t.r >= 0.5 ? "#dc2626" : "#f59e0b";
      L.polyline(t.c, { color, weight: 5, opacity: 0.8 }).bindTooltip(`Riesgo ${t.r}`).addTo(capaTramos);
    });
    capaTramos.addTo(mapa);
  }
  pintarLista(lista);
}

function pintarLista(lista) {
  const cont = $("#lista-focos");
  const orden = [...lista].sort((a, b) => b.intensidad - a.intensidad).slice(0, 40);
  cont.innerHTML = `<p class="nota">${lista.length} focos visibles · ordenados por peso actual</p>` +
    orden.map((r) => {
      const cat = estado.config.categorias[r.categoria];
      return `<div class="item" data-id="${r.id}">
        <div class="ico ${cat.grupo}">${cat.icono}</div>
        <div><p>${escapar(cat.nombre)}${r.origen === "demo" ? '<span class="etq">demo</span>' : ""}</p>
        <small>${edadTexto(r.edad_dias)} · peso ${r.intensidad.toFixed(2)} · ${r.confirmaciones} conf.</small></div></div>`;
    }).join("");
  cont.querySelectorAll(".item").forEach((el) => el.addEventListener("click", () => {
    const r = estado.reportes.find((x) => x.id === Number(el.dataset.id));
    mapa.setView([r.lat, r.lon], 18);
    L.popup().setLatLng([r.lat, r.lon]).setContent(popupFoco(r)).openOn(mapa);
  }));
}

async function cargarReportes() {
  const { datos } = await api(`/api/reportes?hora=${horaSeleccionada()}`);
  estado.reportes = Array.isArray(datos) ? datos : [];
  await dibujarFocos();
  if (estado.tab === "stats") cargarStats();
}

// ---------------------------------------------------------------------------
// Ruta segura
// ---------------------------------------------------------------------------
function fijarPunto(tipo, latlng, etiqueta) {
  estado[tipo] = latlng;
  const icono = iconoPin(tipo === "origen" ? "o" : "d", tipo === "origen" ? "A" : "B");
  if (tipo === "origen") { marcaOrigen?.remove(); marcaOrigen = L.marker(latlng, { icon: icono, draggable: true }).addTo(capaPuntos); marcaOrigen.on("dragend", (e) => fijarPunto("origen", e.target.getLatLng())); }
  else { marcaDestino?.remove(); marcaDestino = L.marker(latlng, { icon: icono, draggable: true }).addTo(capaPuntos); marcaDestino.on("dragend", (e) => fijarPunto("destino", e.target.getLatLng())); }
  $(`#${tipo}-txt`).value = etiqueta || `${latlng.lat.toFixed(5)}, ${latlng.lng.toFixed(5)}`;
  $("#calcular").disabled = !(estado.origen && estado.destino);
  if (estado.origen && estado.destino && estado.ultimaRuta) calcularRuta();
}

function cambiarModo(modo) {
  estado.modo = estado.modo === modo ? null : modo;
  $$("[data-elegir]").forEach((b) => b.classList.toggle("sel", b.dataset.elegir === estado.modo));
  const m = $("#modo-mapa");
  m.hidden = !estado.modo;
  m.textContent = estado.modo === "origen" ? "Toca el mapa para fijar el ORIGEN" : "Toca el mapa para fijar el DESTINO";
}

async function calcularRuta() {
  const btn = $("#calcular");
  btn.disabled = true; btn.textContent = "Calculando…";
  const cuerpo = {
    origen: { lat: estado.origen.lat, lon: estado.origen.lng },
    destino: { lat: estado.destino.lat, lon: estado.destino.lng },
    prioridad: Number($("#prioridad").value), hora: horaSeleccionada(),
  };
  const { ok, datos } = await api("/api/ruta", { method: "POST", body: JSON.stringify(cuerpo) });
  btn.disabled = false; btn.textContent = "Calcular ruta segura";
  if (!ok) { aviso(datos.error || "No se pudo calcular la ruta", true); return; }
  estado.ultimaRuta = datos;
  dibujarRuta(datos);
}

function dibujarRuta(d) {
  capaRuta.clearLayers();
  const corta = L.polyline(d.corta.coordenadas, { color: "#6b7280", weight: 5, opacity: 0.8, dashArray: "8 8" }).addTo(capaRuta);
  L.polyline(d.segura.coordenadas, { color: "#ffffff", weight: 9, opacity: 0.9 }).addTo(capaRuta);
  L.polyline(d.segura.coordenadas, { color: "#0f7b6c", weight: 6 }).addTo(capaRuta);
  corta.bindTooltip("Ruta más corta");
  d.corta.alertas.forEach((a) => {
    L.circleMarker([a.lat, a.lon], { radius: 6, color: "#c8372d", fillColor: "#c8372d", fillOpacity: 0.85, weight: 2 })
      .bindPopup(popupFoco(a)).addTo(capaRuta);
  });
  mapa.fitBounds(L.latLngBounds([...d.segura.coordenadas, ...d.corta.coordenadas]).pad(0.15));

  const c = d.comparacion;
  const hora = `${String(d.hora).padStart(2, "0")}:00`;
  const tarjeta = (r, clase, titulo, color) => `
    <div class="tarjeta ${clase}">
      <h3><i style="background:${color}"></i>${titulo}</h3>
      <div class="metricas">
        <div><b>${(r.distancia_m / 1000).toFixed(2)} km</b><small>distancia</small></div>
        <div><b>${Math.round(r.tiempo_min)} min</b><small>a pie</small></div>
        <div><b>${r.indice_exposicion}</b><small>índice de exposición</small></div>
      </div>
      <p class="calles">${r.tramos_criticos} tramo(s) crítico(s) · ${r.alertas.length} foco(s) a menos de 60 m${r.calles.length ? "<br>Por: " + r.calles.slice(0, 5).map(escapar).join(" → ") : ""}</p>
    </div>`;

  let resumen;
  if (c.misma_ruta) {
    resumen = `A las ${hora} la ruta más corta ya es la más segura disponible.`;
  } else {
    resumen = `A las ${hora}, la ruta segura reduce la exposición al riesgo en <b>${c.reduccion_exposicion_pct}%</b>` +
      ` caminando <b>${c.distancia_extra_m} m</b> más (+${c.distancia_extra_pct}%).`;
  }
  const alertas = d.segura.alertas.length
    ? `<h4 style="margin:14px 0 4px;font-size:13px">Focos que aún quedan cerca de tu ruta</h4>` +
      d.segura.alertas.slice(0, 5).map((a) => {
        const cat = estado.config.categorias[a.categoria];
        return `<div class="item"><div class="ico ${cat.grupo}">${cat.icono}</div><div><p>${escapar(cat.nombre)}</p><small>${edadTexto(a.edad_dias)} · peso ${a.intensidad.toFixed(2)}</small></div></div>`;
      }).join("")
    : "";
  $("#resultado-ruta").innerHTML = `<div class="resumen">${resumen}</div>` +
    tarjeta(d.segura, "segura", "Ruta más segura", "#0f7b6c") +
    (c.misma_ruta ? "" : tarjeta(d.corta, "", "Ruta más corta", "#6b7280")) + alertas;
}

// Busqueda de direcciones (Nominatim, limitada a la zona piloto)
let campoBusqueda = null;
async function buscar(texto) {
  const [o, s, e, n] = estado.config.bbox;
  const url = `https://nominatim.openstreetmap.org/search?format=json&limit=5&bounded=1&viewbox=${o},${n},${e},${s}&q=${encodeURIComponent(texto)}`;
  try {
    const r = await fetch(url, { headers: { "Accept-Language": "es" } });
    return await r.json();
  } catch { return []; }
}
function prepararBusqueda(tipo) {
  const input = $(`#${tipo}-txt`);
  let t;
  input.addEventListener("input", () => {
    clearTimeout(t);
    const q = input.value.trim();
    if (q.length < 4) { $("#sugerencias").hidden = true; return; }
    t = setTimeout(async () => {
      campoBusqueda = tipo;
      const res = await buscar(q);
      const ul = $("#sugerencias");
      ul.innerHTML = res.length ? res.map((x, i) => `<li data-i="${i}">${escapar(x.display_name)}</li>`).join("") : "<li>Sin resultados dentro de la zona piloto</li>";
      ul.hidden = false;
      ul.querySelectorAll("li[data-i]").forEach((li) => li.addEventListener("click", () => {
        const x = res[Number(li.dataset.i)];
        const ll = L.latLng(Number(x.lat), Number(x.lon));
        fijarPunto(campoBusqueda, ll, x.display_name.split(",").slice(0, 2).join(","));
        mapa.setView(ll, 16);
        ul.hidden = true;
      }));
    }, 600);
  });
}

// ---------------------------------------------------------------------------
// Reportar
// ---------------------------------------------------------------------------
function fijarUbicacionReporte(latlng) {
  const [o, s, e, n] = estado.config.bbox;
  if (latlng.lat < s || latlng.lat > n || latlng.lng < o || latlng.lng > e) { aviso("Ese punto está fuera de la zona piloto", true); return; }
  estado.reporte.latlng = latlng;
  marcaReporte?.remove();
  marcaReporte = L.marker(latlng, { icon: iconoPin("r", "!"), draggable: true }).addTo(capaPuntos);
  marcaReporte.on("dragend", (ev) => fijarUbicacionReporte(ev.target.getLatLng()));
  const u = $("#rep-ubicacion");
  u.textContent = `Ubicación: ${latlng.lat.toFixed(5)}, ${latlng.lng.toFixed(5)} (puedes arrastrar el pin)`;
  u.classList.add("ok");
  $("#enviar-reporte").disabled = false;
}

async function enviarReporte() {
  const btn = $("#enviar-reporte");
  btn.disabled = true;
  const cuerpo = {
    categoria: $("#rep-categoria").value,
    lat: estado.reporte.latlng.lat, lon: estado.reporte.latlng.lng,
    severidad: estado.reporte.severidad,
    fecha_hecho: $("#rep-fecha").value || null,
    descripcion: $("#rep-desc").value,
  };
  const { ok, datos } = await api("/api/reportes", { method: "POST", body: JSON.stringify(cuerpo) });
  if (!ok) { aviso((datos.errores || ["Error al enviar"]).join(" "), true); btn.disabled = false; return; }
  aviso("¡Gracias! Tu reporte ya forma parte del mapa y del cálculo de rutas.");
  $("#rep-desc").value = "";
  marcaReporte?.remove(); marcaReporte = null;
  estado.reporte.latlng = null;
  $("#rep-ubicacion").textContent = "Sin ubicación: toca el mapa.";
  $("#rep-ubicacion").classList.remove("ok");
  ponerFechaActual();
  await cargarReportes();
  if (estado.ultimaRuta) calcularRuta();
}

function ponerFechaActual() {
  const d = new Date(); d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  $("#rep-fecha").value = d.toISOString().slice(0, 16);
  $("#rep-fecha").max = d.toISOString().slice(0, 16);
}

// ---------------------------------------------------------------------------
// Estadisticas
// ---------------------------------------------------------------------------
async function cargarStats() {
  const { datos: s } = await api(`/api/estadisticas?hora=${horaSeleccionada()}`);
  const cats = estado.config.categorias;
  const max = Math.max(1, ...Object.values(s.por_categoria));
  const barras = Object.entries(s.por_categoria).sort((a, b) => b[1] - a[1]).map(([k, n]) => `
    <div class="barra"><span>${cats[k].icono} ${escapar(cats[k].nombre.split(" o ")[0])}</span>
      <div class="riel"><i style="width:${(100 * n) / max}%;background:var(--${cats[k].grupo})"></i></div><span class="n">${n}</span></div>`).join("");
  $("#stats").innerHTML = `
    <div class="kpis">
      <div class="kpi"><b>${s.total_activos}</b><small>focos activos</small></div>
      <div class="kpi"><b>${s.ultimos_30_dias}</b><small>en los últimos 30 días</small></div>
      <div class="kpi"><b>${s.fisicos}</b><small>factores físicos</small></div>
      <div class="kpi"><b>${s.incidentes}</b><small>incidentes</small></div>
      <div class="kpi"><b>${s.tramos_criticos}</b><small>tramos críticos ahora</small></div>
      <div class="kpi"><b>${s.resueltos}</b><small>marcados como resueltos</small></div>
    </div>
    ${s.demo ? `<p class="nota" style="margin-top:0">Incluye ${s.demo} reportes simulados de demostración.</p>` : ""}
    <div class="barras"><h4>Focos por categoría</h4>${barras}</div>
    <div class="ranking"><h4>Vías con mayor exposición al riesgo</h4><ol>${s.calles_criticas.map((c) => `<li>${escapar(c.calle)} <small class="etq">${c.exposicion}</small></li>`).join("")}</ol></div>`;
}

// ---------------------------------------------------------------------------
// Inicio
// ---------------------------------------------------------------------------
function cambiarTab(tab) {
  estado.tab = tab;
  $$(".pestanas button").forEach((b) => b.classList.toggle("activa", b.dataset.tab === tab));
  $$(".tab").forEach((t) => t.classList.toggle("activa", t.id === `tab-${tab}`));
  if (estado.modo) cambiarModo(estado.modo);
  if (tab === "stats") cargarStats();
}

async function iniciar() {
  const { datos } = await api("/api/config");
  estado.config = datos;
  $("#zona").textContent = datos.zona;
  const [o, s, e, n] = datos.bbox;
  mapa.fitBounds([[s, o], [n, e]]);
  mapa.setMaxBounds(L.latLngBounds([[s, o], [n, e]]).pad(0.4));
  L.rectangle([[s, o], [n, e]], { color: "#0f7b6c", weight: 1.5, fill: false, dashArray: "6 6", interactive: false }).addTo(mapa);

  // Selectores
  const grupos = { fisico: "Factores físicos de riesgo", incidente: "Incidentes" };
  $("#rep-categoria").innerHTML = Object.entries(grupos).map(([g, nombre]) =>
    `<optgroup label="${nombre}">${Object.entries(datos.categorias).filter(([, c]) => c.grupo === g)
      .map(([k, c]) => `<option value="${k}">${c.icono} ${escapar(c.nombre)}</option>`).join("")}</optgroup>`).join("");
  Object.keys(datos.categorias).forEach((k) => estado.filtroCats.add(k));
  $("#filtro-cats").innerHTML = Object.entries(datos.categorias).map(([k, c]) =>
    `<label><input type="checkbox" value="${k}" checked>${c.icono} ${escapar(c.nombre.split(" o ")[0].split(",")[0])}</label>`).join("");
  $("#hora").innerHTML = `<option value="">Ahora (${String(datos.hora_servidor).padStart(2, "0")}:00)</option>` +
    Array.from({ length: 24 }, (_, h) => `<option value="${h}">${String(h).padStart(2, "0")}:00${h >= 18 || h < 6 ? " · noche" : ""}</option>`).join("");
  ponerFechaActual();

  // Eventos
  $$(".pestanas button").forEach((b) => b.addEventListener("click", () => cambiarTab(b.dataset.tab)));
  $$("[data-elegir]").forEach((b) => b.addEventListener("click", (ev) => { ev.preventDefault(); cambiarModo(b.dataset.elegir); }));
  $("#prioridad").addEventListener("input", (e) => ($("#prioridad-val").textContent = e.target.value));
  $("#prioridad").addEventListener("change", () => estado.ultimaRuta && calcularRuta());
  $("#hora").addEventListener("change", async () => { await cargarReportes(); if (estado.ultimaRuta) calcularRuta(); });
  $("#calcular").addEventListener("click", calcularRuta);
  $("#enviar-reporte").addEventListener("click", enviarReporte);
  $$("#rep-severidad button").forEach((b) => b.addEventListener("click", () => {
    estado.reporte.severidad = Number(b.dataset.v);
    $$("#rep-severidad button").forEach((x) => x.classList.toggle("sel", x === b));
  }));
  $$("#vista button").forEach((b) => b.addEventListener("click", () => {
    estado.vista = b.dataset.v;
    $$("#vista button").forEach((x) => x.classList.toggle("sel", x === b));
    dibujarFocos();
  }));
  $("#filtro-dias").addEventListener("change", dibujarFocos);
  $("#filtro-cats").addEventListener("change", (e) => {
    e.target.checked ? estado.filtroCats.add(e.target.value) : estado.filtroCats.delete(e.target.value);
    dibujarFocos();
  });
  prepararBusqueda("origen");
  prepararBusqueda("destino");

  mapa.on("click", (e) => {
    if (estado.tab === "reportar") return fijarUbicacionReporte(e.latlng);
    if (estado.modo) { fijarPunto(estado.modo, e.latlng); cambiarModo(estado.modo); return; }
    if (estado.tab === "ruta") {
      if (!estado.origen) fijarPunto("origen", e.latlng);
      else if (!estado.destino) fijarPunto("destino", e.latlng);
    }
  });

  await cargarReportes();
}

iniciar().catch((e) => { console.error(e); aviso("No se pudo conectar con el servidor. ¿Ejecutaste python app.py?", true); });
