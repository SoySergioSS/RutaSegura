"""
Descarga la red vial peatonal de la zona piloto desde la API de OpenStreetMap
y la guarda como un grafo compacto en data/red_vial.json.

Uso:
    python herramientas/descargar_red_vial.py
    python herramientas/descargar_red_vial.py --bbox -77.015 -11.990 -76.985 -11.960

La API principal de OSM limita cada peticion a un area pequena, por eso la
zona se descarga en celdas de 0.01 grados y luego se unen.
Datos (c) colaboradores de OpenStreetMap, licencia ODbL.
"""
import argparse
import json
import math
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "data" / "red_vial.json"
API = "https://api.openstreetmap.org/api/0.6/map"

# Vias por las que una persona puede caminar
VIAS_PEATONALES = {
    "primary", "primary_link", "secondary", "secondary_link", "tertiary",
    "tertiary_link", "residential", "living_street", "unclassified",
    "pedestrian", "footway", "path", "steps", "service", "track",
}


def descargar_celda(oeste, sur, este, norte):
    for intento in range(4):
        r = requests.get(API, params={"bbox": f"{oeste},{sur},{este},{norte}"},
                         headers={"User-Agent": "FocosDeAlerta-UNMSM/1.0"}, timeout=120)
        if r.status_code == 200:
            return ET.fromstring(r.content)
        print(f"  HTTP {r.status_code}, reintentando...")
        time.sleep(5 * (intento + 1))
    raise RuntimeError("No se pudo descargar la celda")


def distancia_m(lat1, lon1, lat2, lon2):
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bbox", nargs=4, type=float,
                    default=[-77.015, -11.990, -76.985, -11.960],
                    metavar=("OESTE", "SUR", "ESTE", "NORTE"))
    ap.add_argument("--paso", type=float, default=0.01)
    args = ap.parse_args()
    oeste, sur, este, norte = args.bbox

    nodos = {}   # id -> (lat, lon)
    vias = {}    # id -> (lista de nodos, tipo, nombre)
    lon = oeste
    while lon < este - 1e-9:
        lat = sur
        while lat < norte - 1e-9:
            celda = (lon, lat, min(lon + args.paso, este), min(lat + args.paso, norte))
            print("Descargando celda", ["%.3f" % c for c in celda])
            raiz = descargar_celda(*celda)
            for n in raiz.iter("node"):
                nodos[n.get("id")] = (float(n.get("lat")), float(n.get("lon")))
            for w in raiz.iter("way"):
                tags = {t.get("k"): t.get("v") for t in w.iter("tag")}
                tipo = tags.get("highway")
                if tipo not in VIAS_PEATONALES or tags.get("foot") == "no" or tags.get("access") == "private":
                    continue
                vias[w.get("id")] = ([nd.get("ref") for nd in w.iter("nd")], tipo, tags.get("name", ""))
            time.sleep(1.5)  # cortesia con el servidor de OSM
            lat += args.paso
        lon += args.paso

    # Construir grafo: solo nodos usados por vias, con indices compactos
    indice, coords, aristas = {}, [], []
    nombres = [""]
    nombre_idx = {"": 0}
    for ids, tipo, nombre in vias.values():
        if nombre not in nombre_idx:
            nombre_idx[nombre] = len(nombres)
            nombres.append(nombre)
        previo = None
        for nid in ids:
            if nid not in nodos:
                previo = None
                continue
            if nid not in indice:
                indice[nid] = len(coords)
                coords.append([round(nodos[nid][0], 6), round(nodos[nid][1], 6)])
            actual = indice[nid]
            if previo is not None and previo != actual:
                a, b = coords[previo], coords[actual]
                aristas.append([previo, actual, round(distancia_m(a[0], a[1], b[0], b[1]), 1),
                                tipo, nombre_idx[nombre]])
            previo = actual

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps({
        "fuente": "OpenStreetMap (ODbL) - api.openstreetmap.org",
        "bbox": [oeste, sur, este, norte],
        "nodos": coords,
        "aristas": aristas,
        "nombres": nombres,
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Listo: {len(coords)} nodos, {len(aristas)} aristas -> {SALIDA}")


if __name__ == "__main__":
    main()
