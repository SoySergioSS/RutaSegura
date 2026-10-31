"""
Evaluacion experimental del enrutador (prueba de la hipotesis).

Genera N pares origen-destino al azar dentro de la zona piloto y compara, para
cada uno, la ruta mas corta con la ruta segura. Reporta la reduccion de la
exposicion al riesgo y el aumento de distancia, de dia y de noche, y guarda el
detalle en data/evaluacion.csv.

Uso:
    python herramientas/evaluar_rutas.py --pares 300 --prioridad 6
"""
import argparse
import csv
import math
import random
import statistics as st
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import db  # noqa: E402
from app import LAMBDA_POR_NIVEL  # noqa: E402
from enrutador import RedVial  # noqa: E402
from motor_riesgo import riesgo_por_tramo  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pares", type=int, default=300)
    ap.add_argument("--prioridad", type=float, default=6)
    ap.add_argument("--min-dist", type=float, default=800, help="distancia minima O-D en metros")
    ap.add_argument("--semilla", type=int, default=7)
    args = ap.parse_args()

    red = RedVial(RAIZ / "data" / "red_vial.json")
    with db.conectar() as con:
        reportes = db.listar(con)
    rnd = random.Random(args.semilla)
    o, s, e, n = red.bbox
    nodos = [i for i in red.principal if s <= red.nodos[i][0] <= n and o <= red.nodos[i][1] <= e]
    lam = args.prioridad * LAMBDA_POR_NIVEL
    ahora = datetime.now()

    pares = []
    while len(pares) < args.pares:
        a, b = rnd.sample(nodos, 2)
        if math.dist(red.xy[a], red.xy[b]) >= args.min_dist:
            pares.append((a, b))

    filas = []
    for franja, hora in (("dia", 11), ("noche", 21)):
        riesgo = riesgo_por_tramo(red, reportes, ahora, hora)
        for k, (a, b) in enumerate(pares):
            c = red.resumir(red.ruta(a, b, riesgo, 0.0), riesgo)
            sg = red.resumir(red.ruta(a, b, riesgo, lam), riesgo)
            red_exp = 100 * (c["exposicion_total"] - sg["exposicion_total"]) / c["exposicion_total"] if c["exposicion_total"] else 0.0
            filas.append({
                "par": k, "franja": franja, "dist_corta_m": c["distancia_m"], "dist_segura_m": sg["distancia_m"],
                "exp_corta": c["exposicion_total"], "exp_segura": sg["exposicion_total"],
                "criticos_corta": c["tramos_criticos"], "criticos_segura": sg["tramos_criticos"],
                "reduccion_exposicion_pct": round(red_exp, 2),
                "aumento_distancia_pct": round(100 * (sg["distancia_m"] - c["distancia_m"]) / c["distancia_m"], 2),
                "expuesta": c["exposicion_total"] > 0,
            })

    salida = RAIZ / "data" / "evaluacion.csv"
    with open(salida, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)

    print(f"Pares O-D: {args.pares} | prioridad {args.prioridad} (lambda={lam}) | reportes activos: {len(reportes)}")
    for franja in ("dia", "noche"):
        fs = [f for f in filas if f["franja"] == franja and f["expuesta"]]
        red_e = [f["reduccion_exposicion_pct"] for f in fs]
        aum = [f["aumento_distancia_pct"] for f in fs]
        crit_c = sum(f["criticos_corta"] for f in fs)
        crit_s = sum(f["criticos_segura"] for f in fs)
        cumple = sum(1 for f in fs if f["reduccion_exposicion_pct"] >= 30 and f["aumento_distancia_pct"] <= 20)
        print(f"[{franja}] pares con exposicion>0: {len(fs)}")
        print(f"   reduccion exposicion: media {st.mean(red_e):.1f}%  mediana {st.median(red_e):.1f}%")
        print(f"   aumento distancia:    media {st.mean(aum):.1f}%  mediana {st.median(aum):.1f}%  p90 {sorted(aum)[int(.9*len(aum))]:.1f}%")
        print(f"   tramos criticos atravesados: {crit_c} -> {crit_s}")
        print(f"   pares que cumplen (>=30% menos exposicion y <=20% mas distancia): {cumple}/{len(fs)} = {100*cumple/len(fs):.1f}%")
    print("Detalle:", salida)


if __name__ == "__main__":
    main()
