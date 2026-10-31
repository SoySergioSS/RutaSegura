"""
Red vial y calculo de rutas.

La red se carga desde data/red_vial.json (generado con
herramientas/descargar_red_vial.py a partir de OpenStreetMap). El calculo de
rutas usa A* con heuristica de distancia en linea recta, que es admisible
porque el costo de cada tramo nunca es menor que su longitud.
"""
import heapq
import json
import math
from collections import defaultdict

from motor_riesgo import a_metros, RADIO_CORTE

VELOCIDAD_PEATON = 1.25  # m/s (~4.5 km/h)


class RedVial:
    def __init__(self, ruta_json):
        datos = json.loads(open(ruta_json, encoding="utf-8").read())
        self.bbox = datos["bbox"]
        self.nodos = datos["nodos"]                 # [[lat, lon], ...]
        self.nombres = datos["nombres"]
        self.aristas = datos["aristas"]             # [u, v, longitud, tipo, nombre_idx]
        self.lat0 = (self.bbox[1] + self.bbox[3]) / 2

        self.xy = [a_metros(lat, lon, self.lat0) for lat, lon in self.nodos]
        self.adyacencia = defaultdict(list)         # nodo -> [(vecino, idx_arista)]
        self.segmentos_m = []
        for idx, (u, v, _l, _t, _n) in enumerate(self.aristas):
            self.adyacencia[u].append((v, idx))
            self.adyacencia[v].append((u, idx))
            self.segmentos_m.append((*self.xy[u], *self.xy[v]))

        self._indexar()
        self._componente_principal()

    # -- indices espaciales ---------------------------------------------------
    def _celda(self, x, y):
        return int(x // RADIO_CORTE), int(y // RADIO_CORTE)

    def _indexar(self):
        self.rejilla_aristas = defaultdict(list)
        for idx, (ax, ay, bx, by) in enumerate(self.segmentos_m):
            c1, c2 = self._celda(min(ax, bx), min(ay, by)), self._celda(max(ax, bx), max(ay, by))
            for cx in range(c1[0], c2[0] + 1):
                for cy in range(c1[1], c2[1] + 1):
                    self.rejilla_aristas[(cx, cy)].append(idx)

    def aristas_cercanas(self, x, y, radio):
        cx, cy = self._celda(x, y)
        r = int(math.ceil(radio / RADIO_CORTE))
        vistos = set()
        for i in range(cx - r, cx + r + 1):
            for j in range(cy - r, cy + r + 1):
                for idx in self.rejilla_aristas.get((i, j), ()):
                    if idx not in vistos:
                        vistos.add(idx)
                        yield idx

    def _componente_principal(self):
        """Marca los nodos del mayor componente conexo, para no 'pegar' el origen
        a un tramo aislado del que no se puede salir."""
        visto, mejor = set(), set()
        for inicio in self.adyacencia:
            if inicio in visto:
                continue
            comp, pila = set([inicio]), [inicio]
            while pila:
                n = pila.pop()
                for m, _ in self.adyacencia[n]:
                    if m not in comp:
                        comp.add(m)
                        pila.append(m)
            visto |= comp
            if len(comp) > len(mejor):
                mejor = comp
        self.principal = mejor
        self.rejilla_nodos = defaultdict(list)
        for n in mejor:
            self.rejilla_nodos[self._celda(*self.xy[n])].append(n)

    def dentro(self, lat, lon):
        o, s, e, n = self.bbox
        return s <= lat <= n and o <= lon <= e

    def nodo_cercano(self, lat, lon):
        x, y = a_metros(lat, lon, self.lat0)
        cx, cy = self._celda(x, y)
        for r in range(0, 8):
            mejor, dmin = None, float("inf")
            for i in range(cx - r, cx + r + 1):
                for j in range(cy - r, cy + r + 1):
                    for n in self.rejilla_nodos.get((i, j), ()):
                        d = math.hypot(self.xy[n][0] - x, self.xy[n][1] - y)
                        if d < dmin:
                            mejor, dmin = n, d
            if mejor is not None:
                return mejor, dmin
        return None, None

    # -- rutas ------------------------------------------------------------------
    def ruta(self, origen, destino, riesgo, lam):
        """A* sobre costo = longitud * (1 + lam * riesgo). Devuelve lista de aristas."""
        tx, ty = self.xy[destino]
        g = {origen: 0.0}
        previo = {}
        abiertos = [(0.0, origen)]
        cerrados = set()
        while abiertos:
            _, n = heapq.heappop(abiertos)
            if n == destino:
                break
            if n in cerrados:
                continue
            cerrados.add(n)
            for m, idx in self.adyacencia[n]:
                if m in cerrados:
                    continue
                costo = g[n] + self.aristas[idx][2] * (1.0 + lam * riesgo[idx])
                if costo < g.get(m, float("inf")):
                    g[m] = costo
                    previo[m] = (n, idx)
                    h = math.hypot(self.xy[m][0] - tx, self.xy[m][1] - ty)
                    heapq.heappush(abiertos, (costo + h, m))
        if destino not in previo and origen != destino:
            return None
        camino, n = [], destino
        while n != origen:
            n_prev, idx = previo[n]
            camino.append((n_prev, n, idx))
            n = n_prev
        camino.reverse()
        return camino

    def resumir(self, camino, riesgo):
        """Metricas de una ruta: distancia, tiempo, exposicion y calles."""
        coords = []
        distancia = exposicion = riesgo_max = 0.0
        calles = []
        tramos_criticos = 0
        for i, (u, v, idx) in enumerate(camino):
            if i == 0:
                coords.append(self.nodos[u])
            coords.append(self.nodos[v])
            L = self.aristas[idx][2]
            distancia += L
            exposicion += L * riesgo[idx]
            riesgo_max = max(riesgo_max, riesgo[idx])
            if riesgo[idx] >= 0.5:
                tramos_criticos += 1
            nombre = self.nombres[self.aristas[idx][4]]
            if nombre and (not calles or calles[-1] != nombre):
                calles.append(nombre)
        return {
            "coordenadas": coords,
            "distancia_m": round(distancia),
            "tiempo_min": round(distancia / VELOCIDAD_PEATON / 60, 1),
            # exposicion media por metro recorrido x 100 -> "indice de exposicion"
            "indice_exposicion": round(100 * exposicion / distancia, 1) if distancia else 0.0,
            "exposicion_total": round(exposicion, 1),
            "riesgo_maximo": round(riesgo_max, 2),
            "tramos_criticos": tramos_criticos,
            "calles": calles[:12],
            "aristas": [idx for _, _, idx in camino],
        }
