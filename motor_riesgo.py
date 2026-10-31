"""
Motor de riesgo de Focos de Alerta.

Convierte los reportes ciudadanos en un indice de riesgo para cada tramo de la
red vial. Cada reporte aporta una "intensidad" que depende de:

    I = w_categoria * f_severidad * f_tiempo * f_credibilidad * f_horario

y esa intensidad se reparte en el espacio con un nucleo gaussiano:

    riesgo_tramo = sum_i  I_i * exp(-d_i^2 / (2 * SIGMA^2))   (si d_i <= RADIO_CORTE)

donde d_i es la distancia del reporte al tramo. El costo que usa el enrutador es

    costo_tramo = longitud * (1 + lambda * riesgo_tramo)

lambda = 0 da la ruta mas corta; lambda > 0 penaliza los tramos peligrosos.
"""
import math
from datetime import datetime

# ---------------------------------------------------------------------------
# Catalogo de categorias
#   peso       : aporte base al riesgo
#   vida_media : dias en que el aporte cae a la mitad (los incidentes envejecen
#                rapido, los factores fisicos permanecen hasta que se atienden)
#   nocturno   : multiplicador de noche / de dia (alumbrado pesa mas de noche)
# ---------------------------------------------------------------------------
CATEGORIAS = {
    # Factores fisicos de riesgo
    "alumbrado":   {"nombre": "Alumbrado deficiente o apagado", "grupo": "fisico", "peso": 0.8, "vida_media": 120, "nocturno": (1.8, 0.4), "icono": "💡"},
    "lote_baldio": {"nombre": "Lote baldío o terreno abandonado", "grupo": "fisico", "peso": 0.6, "vida_media": 180, "nocturno": (1.4, 0.8), "icono": "🏚"},
    "camara":      {"nombre": "Cámara de vigilancia inoperativa", "grupo": "fisico", "peso": 0.4, "vida_media": 120, "nocturno": (1.2, 1.0), "icono": "📷"},
    "botadero":    {"nombre": "Botadero o acumulación de basura", "grupo": "fisico", "peso": 0.5, "vida_media": 90,  "nocturno": (1.3, 0.9), "icono": "🗑"},
    "pasaje":      {"nombre": "Pasaje estrecho, muro ciego o escalera sin salida", "grupo": "fisico", "peso": 0.6, "vida_media": 365, "nocturno": (1.6, 0.8), "icono": "🧱"},
    "abandonado":  {"nombre": "Inmueble abandonado o tomado", "grupo": "fisico", "peso": 0.7, "vida_media": 180, "nocturno": (1.5, 0.9), "icono": "🏗"},
    "paradero":    {"nombre": "Paradero inseguro o sin iluminación", "grupo": "fisico", "peso": 0.6, "vida_media": 120, "nocturno": (1.5, 0.9), "icono": "🚏"},
    "vereda":      {"nombre": "Vereda en mal estado o inexistente", "grupo": "fisico", "peso": 0.3, "vida_media": 365, "nocturno": (1.3, 1.0), "icono": "🚧"},
    # Incidentes recientes
    "robo":        {"nombre": "Robo al paso / arrebato", "grupo": "incidente", "peso": 1.0, "vida_media": 21, "nocturno": (1.0, 1.0), "icono": "👜"},
    "asalto":      {"nombre": "Asalto con arma", "grupo": "incidente", "peso": 1.4, "vida_media": 30, "nocturno": (1.0, 1.0), "icono": "⚠"},
    "acoso":       {"nombre": "Acoso o intimidación", "grupo": "incidente", "peso": 0.9, "vida_media": 21, "nocturno": (1.0, 1.0), "icono": "🚫"},
    "pandillaje":  {"nombre": "Pandillaje o consumo de drogas en vía pública", "grupo": "incidente", "peso": 0.8, "vida_media": 45, "nocturno": (1.3, 0.8), "icono": "👥"},
}

SEVERIDAD = {1: 0.6, 2: 1.0, 3: 1.4}
SIGMA = 45.0          # metros: radio de influencia "tipico" de un foco
RADIO_CORTE = 130.0   # metros: mas alla de esto el foco no afecta al tramo
UMBRAL_TIEMPO = 0.05  # aportes menores a 5% se ignoran
VENTANA_HORARIA = 3   # horas alrededor de la hora del incidente

# ---------------------------------------------------------------------------


def es_noche(hora):
    return hora >= 18 or hora < 6


def factor_tiempo(fecha_hecho, ahora, vida_media):
    """Decaimiento exponencial: 1.0 el dia del hecho, 0.5 tras 'vida_media' dias."""
    edad_dias = max(0.0, (ahora - fecha_hecho).total_seconds() / 86400.0)
    return math.exp(-math.log(2) * edad_dias / vida_media)


def factor_credibilidad(confirmaciones, votos_resuelto):
    """Un reporte solo vale 0.6; cada confirmacion lo refuerza (tope 1.3).
    Los votos de 'ya no existe' lo debilitan."""
    c = 0.6 + 0.2 * confirmaciones - 0.25 * votos_resuelto
    return max(0.0, min(1.3, c))


def factor_horario(cat, hora_consulta, hora_hecho):
    noche, dia = cat["nocturno"]
    f = noche if es_noche(hora_consulta) else dia
    if cat["grupo"] == "incidente" and hora_hecho is not None:
        # Los delitos tienden a repetirse en la misma franja horaria
        dif = abs(hora_consulta - hora_hecho) % 24
        dif = min(dif, 24 - dif)
        f *= 1.3 if dif <= VENTANA_HORARIA else 0.8
    return f


def intensidad(reporte, ahora, hora_consulta):
    """Aporte de un reporte al riesgo, o 0 si ya no debe considerarse."""
    cat = CATEGORIAS.get(reporte["categoria"])
    if cat is None or reporte["estado"] != "activo":
        return 0.0
    ft = factor_tiempo(reporte["fecha_hecho"], ahora, cat["vida_media"])
    if ft < UMBRAL_TIEMPO:
        return 0.0
    return (cat["peso"]
            * SEVERIDAD.get(reporte["severidad"], 1.0)
            * ft
            * factor_credibilidad(reporte["confirmaciones"], reporte["votos_resuelto"])
            * factor_horario(cat, hora_consulta, reporte.get("hora_hecho")))


# ---------------------------------------------------------------------------
# Geometria local (proyeccion equirectangular: suficiente para pocos km)
# ---------------------------------------------------------------------------
M_POR_GRADO_LAT = 111320.0


def a_metros(lat, lon, lat0):
    return lon * M_POR_GRADO_LAT * math.cos(math.radians(lat0)), lat * M_POR_GRADO_LAT


def distancia_punto_segmento(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    cx, cy = ax + t * dx, ay + t * dy
    return math.hypot(px - cx, py - cy)


def riesgo_por_tramo(red, reportes, ahora=None, hora_consulta=None):
    """Devuelve una lista con el indice de riesgo de cada arista de la red.

    Usa una rejilla espacial para comparar cada reporte solo con los tramos
    cercanos, en vez de con toda la red.
    """
    ahora = ahora or datetime.now()
    hora_consulta = ahora.hour if hora_consulta is None else hora_consulta
    riesgo = [0.0] * len(red.aristas)

    activos = []
    for r in reportes:
        i = intensidad(r, ahora, hora_consulta)
        if i > 0:
            x, y = a_metros(r["lat"], r["lon"], red.lat0)
            activos.append((x, y, i))
    if not activos:
        return riesgo

    for x, y, inten in activos:
        for idx in red.aristas_cercanas(x, y, RADIO_CORTE):
            ax, ay, bx, by = red.segmentos_m[idx]
            d = distancia_punto_segmento(x, y, ax, ay, bx, by)
            if d <= RADIO_CORTE:
                riesgo[idx] += inten * math.exp(-(d * d) / (2 * SIGMA * SIGMA))
    return riesgo
