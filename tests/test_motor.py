"""Pruebas unitarias del motor de riesgo y del enrutador.  python -m pytest tests"""
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from enrutador import RedVial  # noqa: E402
from motor_riesgo import factor_credibilidad, factor_tiempo, intensidad, riesgo_por_tramo  # noqa: E402

AHORA = datetime(2026, 10, 30, 21, 0)


def reporte(**kw):
    base = {"categoria": "robo", "lat": 0.0, "lon": 0.0, "severidad": 2, "fecha_hecho": AHORA,
            "hora_hecho": 21, "confirmaciones": 0, "votos_resuelto": 0, "estado": "activo"}
    base.update(kw)
    return base


def test_decaimiento_vida_media():
    assert abs(factor_tiempo(AHORA - timedelta(days=21), AHORA, 21) - 0.5) < 1e-9
    assert factor_tiempo(AHORA, AHORA, 21) == 1.0


def test_incidente_viejo_no_cuenta():
    assert intensidad(reporte(fecha_hecho=AHORA - timedelta(days=200)), AHORA, 21) == 0.0


def test_resuelto_no_cuenta():
    assert intensidad(reporte(estado="resuelto"), AHORA, 21) == 0.0


def test_confirmaciones_refuerzan():
    assert factor_credibilidad(3, 0) > factor_credibilidad(0, 0) > factor_credibilidad(0, 2)


def test_alumbrado_pesa_mas_de_noche():
    r = reporte(categoria="alumbrado", hora_hecho=None)
    assert intensidad(r, AHORA, 21) > intensidad(r, AHORA, 11)


def test_incidente_pesa_mas_en_su_franja_horaria():
    r = reporte(hora_hecho=21)
    assert intensidad(r, AHORA, 22) > intensidad(r, AHORA, 9)


def red_cuadrada(tmp_path):
    """Dos caminos de igual largo entre A(0) y D(3): por B(1) o por C(2)."""
    d = 0.001  # ~111 m
    datos = {"bbox": [0, 0, d, d], "nodos": [[0, 0], [d, 0], [0, d], [d, d]],
             "aristas": [[0, 1, 111, "residential", 0], [1, 3, 111, "residential", 0],
                         [0, 2, 111, "residential", 0], [2, 3, 113, "residential", 0]],
             "nombres": [""]}
    p = tmp_path / "red.json"
    p.write_text(json.dumps(datos))
    return RedVial(p)


def test_ruta_segura_evita_el_foco(tmp_path):
    red = red_cuadrada(tmp_path)
    foco = reporte(lat=0.001, lon=0.0005)  # a mitad del tramo B-D (arista 1)
    riesgo = riesgo_por_tramo(red, [foco], AHORA, 21)
    corta = [idx for *_, idx in red.ruta(0, 3, riesgo, 0.0)]
    segura = [idx for *_, idx in red.ruta(0, 3, riesgo, 9.0)]
    assert corta == [0, 1]          # sin penalizar, va por B (222 m < 224 m)
    assert segura == [2, 3]         # penalizando el riesgo, rodea por C


def test_sin_reportes_ambas_rutas_coinciden(tmp_path):
    red = red_cuadrada(tmp_path)
    riesgo = riesgo_por_tramo(red, [], AHORA, 21)
    assert red.ruta(0, 3, riesgo, 0.0) == red.ruta(0, 3, riesgo, 9.0)
