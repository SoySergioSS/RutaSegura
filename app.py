"""
Focos de Alerta - servidor web (API REST + interfaz).

    python app.py            -> http://localhost:5000
"""
import csv
import io
import math
from datetime import datetime, timedelta
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_from_directory

import db
from enrutador import RedVial
from motor_riesgo import CATEGORIAS, a_metros, intensidad, riesgo_por_tramo

RAIZ = Path(__file__).resolve().parent
app = Flask(__name__, static_folder=str(RAIZ / "static"), static_url_path="")
red = RedVial(RAIZ / "data" / "red_vial.json")

MAX_REPORTES_POR_HORA = 10
LAMBDA_POR_NIVEL = 1.5      # prioridad 0..10 -> lambda 0..15
RADIO_ALERTA_RUTA = 60      # m: focos que se listan como "en el camino"

_version = {"n": 0}
_cache_riesgo = {}


def invalidar():
    _version["n"] += 1
    _cache_riesgo.clear()


def riesgo_actual(hora):
    clave = (_version["n"], hora, datetime.now().date())
    if clave not in _cache_riesgo:
        with db.conectar() as con:
            reportes = db.listar(con)
        _cache_riesgo.clear()
        _cache_riesgo[clave] = (riesgo_por_tramo(red, reportes, datetime.now(), hora), reportes)
    return _cache_riesgo[clave]


def autor():
    return db.hash_anonimo(request.headers.get("X-Dispositivo", request.remote_addr))


def serializar(r, ahora, hora):
    cat = CATEGORIAS[r["categoria"]]
    return {
        "id": r["id"], "categoria": r["categoria"], "grupo": cat["grupo"],
        "lat": r["lat"], "lon": r["lon"], "descripcion": r["descripcion"],
        "severidad": r["severidad"], "fecha_hecho": r["fecha_hecho"].isoformat(),
        "hora_hecho": r["hora_hecho"], "confirmaciones": r["confirmaciones"],
        "votos_resuelto": r["votos_resuelto"], "origen": r["origen"],
        "edad_dias": max(0, (ahora - r["fecha_hecho"]).days),
        "intensidad": round(intensidad(r, ahora, hora), 3),
    }


def hora_param(valor):
    try:
        h = int(valor)
        return h if 0 <= h <= 23 else datetime.now().hour
    except (TypeError, ValueError):
        return datetime.now().hour


# ---------------------------------------------------------------------------
@app.get("/")
def inicio():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/config")
def config():
    o, s, e, n = red.bbox
    return jsonify({
        "bbox": red.bbox, "centro": [(s + n) / 2, (o + e) / 2],
        "zona": "San Juan de Lurigancho - Zona piloto Canto Rey / Los Jardines / Bayóvar",
        "categorias": {k: {x: v[x] for x in ("nombre", "grupo", "icono", "vida_media")}
                       for k, v in CATEGORIAS.items()},
        "hora_servidor": datetime.now().hour,
    })


@app.get("/api/reportes")
def listar_reportes():
    hora = hora_param(request.args.get("hora"))
    dias = request.args.get("dias", type=int)
    ahora = datetime.now()
    with db.conectar() as con:
        reportes = db.listar(con)
    salida = [serializar(r, ahora, hora) for r in reportes
              if dias is None or (ahora - r["fecha_hecho"]).days <= dias]
    return jsonify(salida)


@app.post("/api/reportes")
def crear_reporte():
    d = request.get_json(silent=True) or {}
    errores = []
    cat = d.get("categoria")
    if cat not in CATEGORIAS:
        errores.append("Categoría no válida.")
    try:
        lat, lon = float(d.get("lat")), float(d.get("lon"))
        if not red.dentro(lat, lon):
            errores.append("El punto está fuera de la zona piloto.")
    except (TypeError, ValueError):
        errores.append("Ubicación no válida.")
    severidad = d.get("severidad", 2)
    if severidad not in (1, 2, 3):
        errores.append("Severidad debe ser 1, 2 o 3.")
    descripcion = str(d.get("descripcion", "")).strip()[:280]
    try:
        fecha = datetime.fromisoformat(d.get("fecha_hecho") or datetime.now().isoformat())
        if fecha > datetime.now() + timedelta(minutes=10):
            errores.append("La fecha no puede ser futura.")
        if fecha < datetime.now() - timedelta(days=365):
            errores.append("Solo se aceptan hechos del último año.")
    except ValueError:
        errores.append("Fecha no válida.")
    if errores:
        return jsonify({"ok": False, "errores": errores}), 400

    quien = autor()
    with db.conectar() as con:
        hace_una_hora = (datetime.now() - timedelta(hours=1)).isoformat(timespec="seconds")
        if db.reportes_recientes_de(con, quien, hace_una_hora) >= MAX_REPORTES_POR_HORA:
            return jsonify({"ok": False, "errores": ["Límite de reportes por hora alcanzado."]}), 429
        nuevo = db.crear(con, {
            "categoria": cat, "lat": lat, "lon": lon, "descripcion": descripcion,
            "severidad": severidad, "fecha_hecho": fecha.isoformat(timespec="minutes"),
            "hora_hecho": fecha.hour if CATEGORIAS[cat]["grupo"] == "incidente" else None,
        }, quien)
    invalidar()
    return jsonify({"ok": True, "id": nuevo}), 201


@app.post("/api/reportes/<int:rid>/votar")
def votar(rid):
    tipo = (request.get_json(silent=True) or {}).get("tipo")
    if tipo not in ("confirmar", "resuelto"):
        return jsonify({"ok": False, "mensaje": "Tipo de voto no válido."}), 400
    with db.conectar() as con:
        ok, msg = db.votar(con, rid, autor(), tipo)
    if ok:
        invalidar()
    return jsonify({"ok": ok, "mensaje": msg}), (200 if ok else 409)


@app.post("/api/ruta")
def calcular_ruta():
    d = request.get_json(silent=True) or {}
    try:
        o, t = d["origen"], d["destino"]
        olat, olon, dlat, dlon = float(o["lat"]), float(o["lon"]), float(t["lat"]), float(t["lon"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"ok": False, "error": "Indica origen y destino."}), 400
    if not (red.dentro(olat, olon) and red.dentro(dlat, dlon)):
        return jsonify({"ok": False, "error": "Origen y destino deben estar dentro de la zona piloto."}), 400

    prioridad = max(0.0, min(10.0, float(d.get("prioridad", 6))))
    hora = hora_param(d.get("hora"))
    riesgo, reportes = riesgo_actual(hora)

    n_o, dist_o = red.nodo_cercano(olat, olon)
    n_d, dist_d = red.nodo_cercano(dlat, dlon)
    if n_o is None or n_d is None:
        return jsonify({"ok": False, "error": "No hay calles cerca del punto elegido."}), 400

    corta = red.ruta(n_o, n_d, riesgo, 0.0)
    segura = red.ruta(n_o, n_d, riesgo, prioridad * LAMBDA_POR_NIVEL)
    if corta is None or segura is None:
        return jsonify({"ok": False, "error": "No se encontró una ruta entre esos puntos."}), 404

    r_corta, r_segura = red.resumir(corta, riesgo), red.resumir(segura, riesgo)
    ahora = datetime.now()
    r_segura["alertas"] = alertas_en_ruta(r_segura["coordenadas"], reportes, ahora, hora)
    r_corta["alertas"] = alertas_en_ruta(r_corta["coordenadas"], reportes, ahora, hora)

    def pct(a, b):
        return round(100 * (a - b) / a, 1) if a else 0.0

    return jsonify({
        "ok": True, "hora": hora, "prioridad": prioridad,
        "segura": r_segura, "corta": r_corta,
        "comparacion": {
            "misma_ruta": r_corta["aristas"] == r_segura["aristas"],
            "reduccion_exposicion_pct": pct(r_corta["exposicion_total"], r_segura["exposicion_total"]),
            "distancia_extra_m": r_segura["distancia_m"] - r_corta["distancia_m"],
            "distancia_extra_pct": -pct(r_corta["distancia_m"], r_segura["distancia_m"]),
        },
        "ajuste_m": {"origen": round(dist_o), "destino": round(dist_d)},
    })


def alertas_en_ruta(coords, reportes, ahora, hora):
    pts = [a_metros(lat, lon, red.lat0) for lat, lon in coords]
    salida = []
    for r in reportes:
        inten = intensidad(r, ahora, hora)
        if inten <= 0:
            continue
        x, y = a_metros(r["lat"], r["lon"], red.lat0)
        if min(math.hypot(px - x, py - y) for px, py in pts) <= RADIO_ALERTA_RUTA:
            salida.append(serializar(r, ahora, hora))
    salida.sort(key=lambda a: -a["intensidad"])
    return salida[:10]


@app.get("/api/tramos-riesgo")
def tramos_riesgo():
    hora = hora_param(request.args.get("hora"))
    riesgo, _ = riesgo_actual(hora)
    salida = []
    for idx, valor in enumerate(riesgo):
        if valor >= 0.25:
            u, v = red.aristas[idx][0], red.aristas[idx][1]
            salida.append({"c": [red.nodos[u], red.nodos[v]], "r": round(valor, 2)})
    return jsonify(salida)


@app.get("/api/estadisticas")
def estadisticas():
    hora = hora_param(request.args.get("hora"))
    riesgo, reportes = riesgo_actual(hora)
    ahora = datetime.now()
    por_categoria = {k: 0 for k in CATEGORIAS}
    ultimos_30 = 0
    for r in reportes:
        por_categoria[r["categoria"]] += 1
        if (ahora - r["fecha_hecho"]).days <= 30:
            ultimos_30 += 1
    # Calles con mayor exposicion acumulada (riesgo x longitud)
    por_calle = {}
    for idx, valor in enumerate(riesgo):
        nombre = red.nombres[red.aristas[idx][4]]
        if nombre and valor > 0:
            por_calle[nombre] = por_calle.get(nombre, 0) + valor * red.aristas[idx][2]
    top = sorted(por_calle.items(), key=lambda kv: -kv[1])[:8]
    with db.conectar() as con:
        resueltos = con.execute("SELECT COUNT(*) FROM reportes WHERE estado='resuelto'").fetchone()[0]
    return jsonify({
        "total_activos": len(reportes), "ultimos_30_dias": ultimos_30, "resueltos": resueltos,
        "fisicos": sum(1 for r in reportes if CATEGORIAS[r["categoria"]]["grupo"] == "fisico"),
        "incidentes": sum(1 for r in reportes if CATEGORIAS[r["categoria"]]["grupo"] == "incidente"),
        "por_categoria": por_categoria,
        "calles_criticas": [{"calle": c, "exposicion": round(v)} for c, v in top],
        "tramos_criticos": sum(1 for v in riesgo if v >= 0.5),
        "demo": sum(1 for r in reportes if r["origen"] == "demo"),
    })


@app.get("/api/exportar.geojson")
def exportar_geojson():
    ahora, hora = datetime.now(), datetime.now().hour
    with db.conectar() as con:
        reportes = db.listar(con)
    features = [{
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [r["lon"], r["lat"]]},
        "properties": {k: v for k, v in serializar(r, ahora, hora).items() if k not in ("lat", "lon")}
                      | {"categoria_nombre": CATEGORIAS[r["categoria"]]["nombre"]},
    } for r in reportes]
    return Response(
        __import__("json").dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False),
        mimetype="application/geo+json",
        headers={"Content-Disposition": "attachment; filename=focos_de_alerta.geojson"})


@app.get("/api/exportar.csv")
def exportar_csv():
    ahora, hora = datetime.now(), datetime.now().hour
    with db.conectar() as con:
        reportes = db.listar(con)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "categoria", "tipo", "lat", "lon", "fecha_hecho", "severidad",
                "confirmaciones", "intensidad_actual", "descripcion", "origen"])
    for r in reportes:
        s = serializar(r, ahora, hora)
        w.writerow([s["id"], CATEGORIAS[s["categoria"]]["nombre"], s["grupo"], s["lat"], s["lon"],
                    s["fecha_hecho"], s["severidad"], s["confirmaciones"], s["intensidad"],
                    s["descripcion"], s["origen"]])
    return Response("﻿" + buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=focos_de_alerta.csv"})


if __name__ == "__main__":
    print("Focos de Alerta en http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
