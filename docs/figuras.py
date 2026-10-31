import csv, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = sys.argv[1]
EVAL = sys.argv[2]
plt.rcParams.update({"font.family": "Segoe UI", "font.size": 10})
INK, MUTED, BORDE = "#1d2330", "#5d6677", "#c9ced8"

# ---------------- Arquitectura ----------------
fig, ax = plt.subplots(figsize=(10, 6.6), dpi=200)
ax.set_xlim(0, 100); ax.set_ylim(0, 66); ax.axis("off")

def capa(x, y, w, h, titulo, color):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.5",
                                fc=color, ec="none", alpha=0.10))
    ax.text(x + 1, y + h - 1.6, titulo, fontsize=10.5, fontweight="bold", color=INK, va="top")

def caja(x, y, w, h, titulo, sub="", fc="#ffffff", ec=BORDE):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3,rounding_size=1",
                                fc=fc, ec=ec, lw=1.2))
    ax.text(x + w / 2, y + h / 2 + (1.3 if sub else 0), titulo, ha="center", va="center",
            fontsize=9.5, fontweight="bold", color=INK)
    if sub:
        ax.text(x + w / 2, y + h / 2 - 1.6, sub, ha="center", va="center", fontsize=7.8, color=MUTED)

def flecha(x1, y1, x2, y2, txt="", dx=0.8):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.1, shrinkA=0, shrinkB=0))
    if txt:
        ax.text((x1 + x2) / 2 + dx, (y1 + y2) / 2, txt, fontsize=7.5, color=MUTED, va="center")

# Capa 1: presentacion
capa(2, 49, 96, 15, "1. Capa de presentación (navegador: PC o celular)", "#2a78d6")
caja(4, 52.5, 20, 7.5, "Registro de focos", "formulario + pin en mapa")
caja(27, 52.5, 20, 7.5, "Mapa de riesgo", "marcadores · calor · tramos")
caja(50, 52.5, 20, 7.5, "Ruta segura", "origen/destino · prioridad · hora")
caja(73, 52.5, 22, 7.5, "Estadísticas", "indicadores · CSV / GeoJSON")
ax.text(50, 50.4, "HTML5 + CSS + JavaScript · Leaflet 1.9 · Leaflet.heat", ha="center", fontsize=7.8, color=MUTED)

flecha(50, 49, 50, 44.5, "HTTP/JSON (API REST)")

# Capa 2: logica
capa(2, 21, 96, 23, "2. Capa de aplicación (servidor Python + Flask)", "#0f7b6c")
caja(4, 31, 20, 8, "API REST", "app.py · validación · límites")
caja(27, 31, 20, 8, "Gestión de reportes", "alta · votos · resueltos")
caja(50, 31, 21, 8, "Motor de riesgo", "intensidad · núcleo gaussiano")
caja(74, 31, 21, 8, "Enrutador A*", "costo = L·(1+λ·riesgo)")
caja(27, 23, 20, 6, "Índice espacial", "rejilla 130 m (motor y A*)")
caja(50, 23, 21, 6, "Caché de riesgo", "por versión y hora")
caja(74, 23, 21, 6, "Comparador de rutas", "corta vs. segura")
flecha(24, 35, 27, 35); flecha(47, 35, 50, 35); flecha(71, 35, 74, 35)
flecha(60.5, 31, 60.5, 29); flecha(84.5, 31, 84.5, 29)

flecha(37, 21, 37, 16.5, "SQL"); flecha(52, 21, 52, 16.5, "lectura")

# Capa 3: datos
capa(2, 2, 96, 14.5, "3. Capa de datos", "#eb6834")
caja(4, 4, 28, 7.5, "SQLite: focos.db", "reportes · votos (hash anónimo)")
caja(36, 4, 28, 7.5, "Red vial: red_vial.json", "10 737 nodos · 12 833 tramos")
caja(68, 4, 28, 7.5, "OpenStreetMap", "teselas · descarga de red vial")
flecha(68, 7.75, 64, 7.75)

fig.savefig(f"{OUT}/arquitectura.png", bbox_inches="tight", facecolor="white")
plt.close(fig)

# ---------------- Flujo del algoritmo ----------------
fig, ax = plt.subplots(figsize=(10, 2.6), dpi=200)
ax.set_xlim(0, 100); ax.set_ylim(0, 20); ax.axis("off")
pasos = [("1. Reportes\nactivos", "SQLite"), ("2. Intensidad I_i", "categoría · severidad\ntiempo · votos · hora"),
         ("3. Riesgo por\ntramo r_e", "Σ I_i · e^(−d²/2σ²)"), ("4. Costo del\ntramo c_e", "L_e · (1 + λ·r_e)"),
         ("5. A* (λ=0 y λ>0)", "ruta corta y\nruta segura"), ("6. Comparación", "Δ exposición\nΔ distancia")]
w = 14.5
for i, (t, s) in enumerate(pasos):
    x = 1 + i * 16.6
    ax.add_patch(FancyBboxPatch((x, 4), w, 12, boxstyle="round,pad=0.3,rounding_size=1", fc="#ffffff", ec=BORDE, lw=1.2))
    ax.text(x + w / 2, 12.6, t, ha="center", va="center", fontsize=9, fontweight="bold", color=INK)
    ax.text(x + w / 2, 7.2, s, ha="center", va="center", fontsize=7.6, color=MUTED)
    if i < len(pasos) - 1:
        ax.annotate("", xy=(x + w + 2, 10), xytext=(x + w + 0.2, 10),
                    arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.1))
fig.savefig(f"{OUT}/flujo.png", bbox_inches="tight", facecolor="white")
plt.close(fig)

# ---------------- Evaluacion ----------------
filas = [r for r in csv.DictReader(open(EVAL, encoding="utf-8")) if r["expuesta"] == "True"]
fig, ax = plt.subplots(figsize=(8, 4.6), dpi=200)
ax.axvspan(-1, 20, ymin=0, ymax=1, color="#0f7b6c", alpha=0.0)
ax.fill_between([-1, 20], 30, 102, color="#0f7b6c", alpha=0.08, lw=0)
ax.text(0.5, 31.5, "Zona de la hipótesis:\n≥ 30 % menos exposición y ≤ 20 % más distancia",
        ha="left", va="bottom", fontsize=8.5, color="#0b5f54")
for franja, color, nombre in (("dia", "#2a78d6", "Día (11:00)"), ("noche", "#eb6834", "Noche (21:00)")):
    xs = [float(r["aumento_distancia_pct"]) for r in filas if r["franja"] == franja]
    ys = [float(r["reduccion_exposicion_pct"]) for r in filas if r["franja"] == franja]
    ax.scatter(xs, ys, s=16, color=color, alpha=0.65, edgecolors="white", linewidths=0.6, label=nombre)
ax.set_xlabel("Aumento de distancia de la ruta segura respecto a la más corta (%)", color=INK)
ax.set_ylabel("Reducción de la exposición al riesgo (%)", color=INK)
ax.set_xlim(-1, max(45, max(float(r["aumento_distancia_pct"]) for r in filas) + 2)); ax.set_ylim(-2, 102)
for s in ("top", "right"): ax.spines[s].set_visible(False)
for s in ("left", "bottom"): ax.spines[s].set_color(BORDE)
ax.tick_params(colors=MUTED)
ax.grid(color="#eceef2", lw=0.8); ax.set_axisbelow(True)
ax.legend(frameon=False, loc="lower right")
fig.savefig(f"{OUT}/evaluacion.png", bbox_inches="tight", facecolor="white")
print("ok")
