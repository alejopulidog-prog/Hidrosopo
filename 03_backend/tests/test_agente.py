"""
HidroSopó — Pruebas del agente conversacional
==============================================
Cada prueba viene de un caso real que falló durante el desarrollo.
Si alguna se cae, es que se rompió algo que ya funcionaba.

    pytest tests/test_agente.py -v
"""
import sys, os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agente import (entender, extraer_minutos, normalizar, calcular_ahorro,
                    responder_medir_caudal, _resolver_sectores)
import costos


class SectorFalso:
    def __init__(self, id, orden, nombre, area_ha, caudal_lps, bomba):
        self.id, self.orden, self.nombre = id, orden, nombre
        self.area_ha, self.caudal_lps, self.bomba = area_ha, caudal_lps, bomba
        self.activo = True


class PredioFalso:
    area_regada_ha = 1.1
    area_por_turno_ha = None
    caudal_disponible_lps = 2.5
    altura_bombeo_m = 45
    eficiencia_bomba = 0.55
    tipo_energia = "electrica"
    costo_kwh = 850
    tarifa_agua_m3 = 0
    propietario = "Jaime Rodríguez"


SECTORES = [
    SectorFalso(1, 1, "Potrero de arriba", 0.35, 2.5, "Bomba grande"),
    SectorFalso(2, 2, "Potrero del medio", 0.40, 2.5, "Bomba grande"),
    SectorFalso(3, 3, "Lote de la casa",   0.35, 1.4, "Bomba chica"),
]


# ============================================================
#  Extracción de tiempo
# ============================================================

@pytest.mark.parametrize("frase,esperado", [
    ("regué 40 minutos", 40),
    ("regue 40 min", 40),
    ("Regué 40", 40),
    ("puse la bomba 2 horas", 120),
    ("prendí las dos bombas una hora", 60),   # daba 1 minuto antes de corregirlo
    ("regué hora y media", 90),
    ("media hora en el sector 1", 30),
    ("regué 1.5 horas", 90),
])
def test_extraer_minutos(frase, esperado):
    assert extraer_minutos(frase) == esperado


def test_normalizar_quita_tildes():
    """El productor escribe 'regue', no 'regué'. Y a veces en mayúscula."""
    assert normalizar("REGUÉ") == "regue"
    assert normalizar("  ¿Cuánta   agua?  ") == "¿cuanta agua?"


# ============================================================
#  Intenciones
# ============================================================

@pytest.mark.parametrize("frase,tipo", [
    ("regué 40 minutos", "registrar_riego"),
    ("media hora en el sector 1", "registrar_riego"),
    ("prendí la bomba 30 min", "registrar_riego"),
    ("no pude regar", "registrar_no_riego"),
    ("riego dos veces al día", "registrar_rutina"),
    ("cuánta agua he ahorrado?", "consultar_ahorro"),
    ("riego hoy?", "consultar_riego"),
    ("va a llover?", "consultar_lluvia"),
    ("cuándo meto las vacas?", "consultar_pastoreo"),
    ("se dañó el sensor", "reportar_problema"),
    ("cuánta agua da mi bomba?", "medir_caudal"),
    ("hola", "saludo"),
    ("ayuda", "ayuda"),
    ("xyzabc qwerty", "desconocido"),
])
def test_intenciones(frase, tipo):
    assert entender(frase).tipo == tipo


def test_detecta_el_sector():
    assert entender("regué el sector 2, 40 minutos").datos.get("sector_num") == 2
    assert entender("regué el potrero 3 media hora").datos.get("sector_num") == 3


def test_detecta_bombas_simultaneas():
    """'Prendí las dos bombas' es lo normal en una finca con dos motores."""
    assert entender("prendí las dos bombas una hora").datos.get("bombas_simultaneas") == 2
    assert entender("puse ambas bombas 30 min").datos.get("bombas_simultaneas") == 2


def test_discrepancia_se_detecta():
    """Si el productor no está de acuerdo, hay que registrarlo:
    suele significar que el sensor está mal."""
    assert entender("la tierra la veo seca pero usted dice que está bien").tipo == "discrepar"


# ============================================================
#  Resolución de sectores
# ============================================================

def test_sector_por_numero():
    els, desc = _resolver_sectores({"sector_num": 2}, SECTORES)
    assert len(els) == 1 and els[0].nombre == "Potrero del medio"


def test_sector_por_nombre():
    els, desc = _resolver_sectores({"sector_texto": "lote de la casa"}, SECTORES)
    assert len(els) == 1 and els[0].id == 3


def test_dos_bombas_elige_sectores_de_bombas_distintas():
    """Con dos bombas se riegan dos sectores que NO comparten motor."""
    els, desc = _resolver_sectores({"bombas_simultaneas": 2}, SECTORES)
    assert len(els) == 2
    assert len({x.bomba for x in els}) == 2


def test_toda_la_finca():
    els, _ = _resolver_sectores({"todos_los_sectores": True}, SECTORES)
    assert len(els) == 3


def test_sin_pista_y_varios_sectores_queda_ambiguo():
    """No adivinar: preguntar. Registrar el riego en el sector equivocado
    daña el balance hídrico de dos sectores a la vez."""
    els, desc = _resolver_sectores({}, SECTORES)
    assert desc == "AMBIGUO"


def test_un_solo_sector_no_pregunta():
    els, desc = _resolver_sectores({}, SECTORES[:1])
    assert len(els) == 1 and desc != "AMBIGUO"


# ============================================================
#  Medición del caudal con balde
# ============================================================

def test_medicion_con_balde():
    r = responder_medir_caudal("segundos_balde", "20 litros en 9 segundos", PredioFalso())
    assert r["accion"] == "registrar_caudal"
    assert r["datos"]["caudal_lps"] == pytest.approx(2.222, abs=0.01)


def test_medicion_incompleta_vuelve_a_preguntar():
    r = responder_medir_caudal("segundos_balde", "como 20", PredioFalso())
    assert r["esperando"] == "segundos_balde"
    assert r.get("accion") is None


def test_caudal_absurdo_se_advierte():
    r = responder_medir_caudal("segundos_balde", "200 litros en 2 segundos", PredioFalso())
    assert "revise" in r["texto"].lower()


# ============================================================
#  Costo del agua bombeada
# ============================================================

def test_costo_por_m3_electrico():
    """A 45 m de altura y 55% de eficiencia, mover 1 m³ cuesta ~0.22 kWh."""
    c = costos.costo_por_m3(PredioFalso())
    assert c["kwh_por_m3"] == pytest.approx(0.223, abs=0.01)
    assert 150 < c["cop_por_m3"] < 230


def test_gravedad_no_cuesta_bombeo():
    class P(PredioFalso):
        tipo_energia = "gravedad"
    assert costos.costo_por_m3(P())["cop_por_m3"] == 0


def test_diesel_reporta_litros():
    class P(PredioFalso):
        tipo_energia = "diesel"
        costo_diesel_litro = 13000
    v = costos.valorizar(100, P())
    assert v["litros_diesel"] > 0 and v["cop"] > 0


def test_mas_altura_cuesta_mas():
    class Bajo(PredioFalso):
        altura_bombeo_m = 10
    class Alto(PredioFalso):
        altura_bombeo_m = 80
    assert costos.costo_por_m3(Alto())["cop_por_m3"] > costos.costo_por_m3(Bajo())["cop_por_m3"]


def test_formato_de_pesos_colombiano():
    assert costos.pesos(1234567) == "$1.234.567"


# ============================================================
#  Ahorro
# ============================================================

def test_ahorro_se_calcula_bien():
    base = [{"fecha": f"2026-09-{d:02d}", "m3": 4.0} for d in range(1, 11)]
    actual = [{"fecha": f"2026-10-{d:02d}", "m3": 3.0} for d in range(1, 11)]
    a = calcular_ahorro(actual, base, 10)
    assert a["ahorro_m3"] == pytest.approx(10.0)
    assert a["ahorro_pct"] == pytest.approx(25.0)


def test_sin_linea_base_no_inventa_un_numero():
    """Es preferible decir 'todavía no sé' que inventar un ahorro."""
    assert calcular_ahorro([{"fecha": "x", "m3": 1}], [], 10).get("sin_datos") is True


# ============================================================
#  Desglose separado: agua vs. energía
# ============================================================

class PredioAcueducto(PredioFalso):
    tarifa_agua_m3 = 1800
    altura_bombeo_m = 25


class PredioDiesel(PredioFalso):
    tipo_energia = "diesel"
    altura_bombeo_m = 70
    eficiencia_bomba = 0.50
    costo_diesel_litro = 13000
    consumo_diesel_lph = 1.8
    caudal_disponible_lps = 2.5


class PredioGravedad(PredioFalso):
    tipo_energia = "gravedad"


def test_fuente_propia_no_cobra_agua():
    """La mayoría de fincas de Sopó toman de una quebrada: el agua es gratis
    y el 100% del ahorro está en la energía. Decirle que ahorró en la
    factura del agua sería mentirle."""
    d = costos.desglose_por_m3(PredioFalso())
    agua = next(l for l in d["lineas"] if l["concepto"] == "Agua")
    assert agua["cop_por_m3"] == 0
    assert d["paga_agua"] is False


def test_acueducto_separa_agua_y_energia():
    d = costos.desglose_por_m3(PredioAcueducto())
    agua = next(l for l in d["lineas"] if l["concepto"] == "Agua")
    energia = next(l for l in d["lineas"] if l["concepto"] == "Energía")
    assert agua["cop_por_m3"] == 1800
    assert energia["cop_por_m3"] > 0
    assert d["total_cop_por_m3"] == pytest.approx(agua["cop_por_m3"] + energia["cop_por_m3"])


def test_valorizar_devuelve_las_dos_partidas_por_aparte():
    v = costos.valorizar(100, PredioAcueducto())
    assert v["cop_agua"] > 0 and v["cop_energia"] > 0
    assert v["cop"] == pytest.approx(v["cop_agua"] + v["cop_energia"], abs=2)


def test_gravedad_con_agua_propia_no_tiene_ahorro_en_plata():
    v = costos.valorizar(100, PredioGravedad())
    assert v["cop"] == 0 and v["kwh"] == 0


def test_diesel_usa_el_consumo_medido_si_existe():
    """Si el productor midió los litros/hora de su motor, ese dato manda
    sobre la estimación termodinámica: él lo sabe, nosotros lo estimamos."""
    d = costos.desglose_por_m3(PredioDiesel())
    energia = next(l for l in d["lineas"] if l["concepto"] == "Energía")
    assert "medido" in energia["detalle"]
    # 1000/(2.5*3600) h/m³ × 1.8 L/h = 0.2 L/m³
    assert energia["litros_diesel_por_m3"] == pytest.approx(0.2, abs=0.01)


def test_diesel_sin_consumo_medido_estima():
    class P(PredioDiesel):
        consumo_diesel_lph = 0
    energia = next(l for l in costos.desglose_por_m3(P())["lineas"]
                   if l["concepto"] == "Energía")
    assert "estimado" in energia["detalle"]
    assert energia["litros_diesel_por_m3"] > 0


def test_reporta_galones_para_el_diesel():
    """El campesino compra ACPM por galones, no por litros."""
    v = costos.valorizar(100, PredioDiesel())
    energia = next(c for c in v["conceptos"] if c["concepto"] == "Energía")
    assert energia["galones_diesel"] == pytest.approx(energia["litros_diesel"]/3.785, abs=0.05)


# ============================================================
#  Retorno de la inversión
# ============================================================

def test_retorno_se_calcula():
    r = costos.retorno_inversion(55.0, 30, PredioAcueducto(), 1_720_000)
    assert r["calculable"] and r["anios_retorno"] > 0
    assert r["ahorro_anual_cop"] > 0


def test_retorno_largo_se_reconoce_como_tal():
    """Con agua propia y luz barata el equipo no se paga rápido.
    El sistema debe decirlo, no maquillarlo."""
    r = costos.retorno_inversion(55.0, 30, PredioFalso(), 1_720_000)
    assert r["anios_retorno"] > 7
    assert "no se paga en un plazo corto" in r["veredicto"]


def test_sin_ahorro_no_inventa_retorno():
    assert costos.retorno_inversion(0, 30, PredioFalso())["calculable"] is False


def test_gravedad_no_tiene_retorno_monetario():
    r = costos.retorno_inversion(55.0, 30, PredioGravedad())
    assert r["calculable"] is False
