"""Base de conocimiento del asistente: el experto responde sin internet y
nunca le quita el turno a un registro (riego, pastoreo, caudal)."""
import sys, os, json, pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agente import conversar, entender
from ia import conocimiento

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.mark.parametrize("pregunta,tema", [
    ("¿Qué es la evapotranspiración?", "et0"),
    ("¿Cuál es la mejor hora para regar?", "hora"),
    ("¿Es mejor goteo o aspersión?", "goteo"),
    ("¿Qué es el PUEAA?", "pueaa"),
    ("¿necesito concesión para sacar agua del río?", "concesion"),
    ("¿cómo recojo agua lluvia?", "agua_lluvia"),
    ("¿por qué hay que calibrar los sensores?", "calibracion"),
    ("¿cómo funciona la inteligencia artificial?", "ia"),
    ("qué pasa si riego de más", "exceso"),
    ("¿cuándo necesita más agua la papa?", "papa"),
])
def test_responde_como_experto(pregunta, tema):
    out = conversar(pregunta, {})
    assert out["intencion"] == "consulta_experta"
    assert out["tema"] == tema
    assert out["sugerencias"] and out["fuente"]


def test_no_reemplaza_un_registro_de_riego():
    from agente import REEMPLAZABLES
    assert entender("regué 40 minutos con aspersor").tipo == "registrar_riego"
    assert "registrar_riego" not in REEMPLAZABLES


def test_por_que_solo_sigue_siendo_sobre_la_recomendacion():
    assert entender("¿por qué?").tipo == "consultar_por_que"
    assert conversar("¿por qué?", {"recomendacion": {}})["intencion"] == "consultar_por_que"


def test_sin_coincidencia_y_sin_llm_responde_ayuda():
    out = conversar("xyzzy blablá", {})
    assert out["intencion"] == "desconocido"


def test_entradas_bien_formadas_y_ids_unicos():
    es = conocimiento.entradas()
    assert len(es) >= 25
    assert len({e["id"] for e in es}) == len(es)
    for e in es:
        assert e["titulo"] and e["respuesta"] and e["claves"] and e["fuente"]


def test_la_app_usa_la_misma_base():
    a = json.load(open(os.path.join(RAIZ, "03_backend/ia/conocimiento.json"), encoding="utf-8"))
    b = json.load(open(os.path.join(RAIZ, "04_dashboard/conocimiento.json"), encoding="utf-8"))
    assert a == b, "Copie 03_backend/ia/conocimiento.json a 04_dashboard/conocimiento.json"
