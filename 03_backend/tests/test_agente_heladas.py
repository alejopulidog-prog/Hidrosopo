"""
Pruebas de las intenciones agregadas en la versión 10 del agente:
aviso de heladas y conversión de la lámina a minutos de bomba.
"""
import sys, os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agente import entender, conversar, responder_helada, responder_tiempo_riego


@pytest.mark.parametrize("frase", [
    "¿va a caer helada?", "hay riesgo de heladas esta semana", "va a hacer mucho frio",
    "amaneció con escarcha", "se va a quemar el pasto?",
])
def test_detecta_helada(frase):
    assert entender(frase).tipo == "consultar_helada"


@pytest.mark.parametrize("frase", [
    "cuanto tiempo prendo la bomba", "cuantos minutos riego hoy",
    "por cuanto tiempo debo regar", "cuanta agua le echo",
])
def test_detecta_tiempo_riego(frase):
    assert entender(frase).tipo == "consultar_tiempo_riego"


def test_helada_con_minima_bajo_cero_alerta():
    rec = {"clima": {"temp_min_c": [6, 1.0, -1.5, 5, 7, 8, 8]},
           "estado_suelo": {"porcentaje_agua_disponible": 35}}
    r = responder_helada(rec)
    assert r["accion"] == "alerta_helada"
    assert r["datos"]["temp_min_c"] == -1.5
    assert "riego ligero" in r["texto"]


def test_helada_suelo_humedo_no_pide_riego_extra():
    rec = {"clima": {"temp_min_c": [0.5, 6, 7]},
           "estado_suelo": {"porcentaje_agua_disponible": 85}}
    r = responder_helada(rec)
    assert "no hace falta regar extra" in r["texto"]


def test_sin_riesgo_de_helada():
    r = responder_helada({"clima": {"temp_min_c": [8, 9, 7.5, 8, 9, 10, 9]}})
    assert r["accion"] is None and "No veo riesgo" in r["texto"]


def test_helada_sin_pronostico_no_inventa():
    r = responder_helada({})
    assert "No tengo el pronóstico" in r["texto"]


def test_tiempo_riego_en_minutos():
    rec = {"riego": {"lamina_bruta_mm": 18.4, "minutos": 74, "fraccionar_en_pasadas": True,
                     "pasadas_sugeridas": 2}}
    t = responder_tiempo_riego(rec)["texto"]
    assert "74 minutos" in t and "2 pasadas" in t


def test_tiempo_riego_cuando_no_toca():
    t = responder_tiempo_riego({"riego": None, "mensaje": "Hoy no riegue."})["texto"]
    assert "no le toca regar" in t


def test_conversar_enruta_helada():
    out = conversar("¿va a caer helada?", {"recomendacion": {"clima": {"temp_min_c": [1, 5]}}})
    assert out["intencion"] == "consultar_helada"
