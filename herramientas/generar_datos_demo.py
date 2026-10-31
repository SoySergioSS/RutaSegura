"""
Carga reportes SIMULADOS en la base de datos para demostrar el sistema.

Los reportes se marcan con origen='demo' y la interfaz los identifica como
datos de demostracion: NO representan hechos reales. Se agrupan en "focos"
alrededor de puntos al azar de la red, como ocurre con los datos reales.

Uso:
    python herramientas/generar_datos_demo.py          # agrega datos demo
    python herramientas/generar_datos_demo.py --borrar # elimina solo los demo
"""
import argparse
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import db  # noqa: E402
from enrutador import RedVial  # noqa: E402
from motor_riesgo import CATEGORIAS  # noqa: E402

DESCRIPCIONES = {
    "alumbrado": ["Postes apagados en toda la cuadra", "Solo funciona un poste de tres", "Luminaria rota hace semanas"],
    "lote_baldio": ["Terreno sin cerco con desmonte", "Lote vacío donde se esconden de noche"],
    "camara": ["Cámara municipal sin funcionar", "Cámara volteada, no enfoca la calle"],
    "botadero": ["Acumulación de basura en la esquina", "Botadero informal junto al muro"],
    "pasaje": ["Escalera sin luz y sin salida", "Pasaje estrecho entre muros"],
    "abandonado": ["Casa abandonada, entran de noche", "Construcción paralizada sin cerco"],
    "paradero": ["Paradero oscuro, sin caseta", "Paradero donde roban celulares al subir"],
    "vereda": ["Vereda rota, obliga a caminar por la pista", "No hay vereda en este tramo"],
    "robo": ["Arrebato de celular", "Le quitaron la mochila a una vecina", "Robo a la salida del mercado"],
    "asalto": ["Asalto con cuchillo", "Dos sujetos en moto con arma"],
    "acoso": ["Acoso a estudiantes a la salida", "Grupo que molesta a las personas que pasan"],
    "pandillaje": ["Grupo consumiendo drogas en el parque", "Pandilla reunida en la esquina de noche"],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--borrar", action="store_true")
    ap.add_argument("--semilla", type=int, default=2026)
    args = ap.parse_args()

    con = db.conectar()
    con.execute("DELETE FROM votos WHERE reporte_id IN (SELECT id FROM reportes WHERE origen='demo')")
    con.execute("DELETE FROM reportes WHERE origen='demo'")
    con.commit()
    if args.borrar:
        print("Datos demo eliminados.")
        return

    rnd = random.Random(args.semilla)
    red = RedVial(RAIZ / "data" / "red_vial.json")
    o, s_, e, n = red.bbox
    m = 0.0015  # margen para que los focos queden dentro de la zona piloto
    nodos = sorted(i for i in red.principal
                   if s_ + m <= red.nodos[i][0] <= n - m and o + m <= red.nodos[i][1] <= e - m)
    ahora = datetime.now().replace(second=0, microsecond=0)
    fisicos = [k for k, v in CATEGORIAS.items() if v["grupo"] == "fisico"]
    incidentes = [k for k, v in CATEGORIAS.items() if v["grupo"] == "incidente"]

    def punto_cerca(n, radio_m):
        lat, lon = red.nodos[n]
        dlat = rnd.uniform(-radio_m, radio_m) / 111320
        dlon = rnd.uniform(-radio_m, radio_m) / 111320 / 0.978
        return round(lat + dlat, 6), round(lon + dlon, 6)

    def reporte(cat, lat, lon):
        g = CATEGORIAS[cat]["grupo"]
        if g == "incidente":
            edad = rnd.expovariate(1 / 18)        # la mayoria son recientes
            hora = rnd.choice([6, 7, 13, 19, 20, 21, 22, 23])
        else:
            edad = rnd.uniform(1, 200)
            hora = rnd.randint(8, 18)
        fecha = (ahora - timedelta(days=min(edad, 300))).replace(hour=hora, minute=rnd.randint(0, 59))
        if fecha > ahora:
            fecha -= timedelta(days=1)
        return {
            "categoria": cat, "lat": lat, "lon": lon,
            "descripcion": rnd.choice(DESCRIPCIONES[cat]),
            "severidad": rnd.choices([1, 2, 3], [2, 5, 3])[0],
            "fecha_hecho": fecha.isoformat(timespec="minutes"),
            "hora_hecho": fecha.hour if g == "incidente" else None,
            "creado_en": (fecha + timedelta(hours=rnd.uniform(0.2, 30))).isoformat(timespec="seconds"),
            "origen": "demo",
        }

    total = 0
    # Focos concentrados: cada uno mezcla factores fisicos e incidentes
    for _ in range(11):
        centro = rnd.choice(nodos)
        for _ in range(rnd.randint(5, 11)):
            cat = rnd.choice(fisicos) if rnd.random() < 0.5 else rnd.choice(incidentes)
            rid = db.crear(con, reporte(cat, *punto_cerca(centro, 90)), "demo")
            conf = rnd.choices([0, 1, 2, 3, 4], [3, 3, 2, 1, 1])[0]
            con.execute("UPDATE reportes SET confirmaciones=? WHERE id=?", (conf, rid))
            total += 1
    # Reportes dispersos
    for _ in range(35):
        cat = rnd.choice(fisicos + incidentes)
        db.crear(con, reporte(cat, *punto_cerca(rnd.choice(nodos), 20)), "demo")
        total += 1
    con.commit()
    print(f"{total} reportes demo creados en {db.RUTA_DB}")


if __name__ == "__main__":
    main()
