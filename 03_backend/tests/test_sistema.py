"""
HidroSopó — Pruebas automatizadas
==================================
Corre con:   pytest -v

Por qué tener pruebas en un proyecto académico: cuando en el mes 3 cambies
un coeficiente y algo deje de funcionar, estas pruebas te dicen QUÉ se rompió
en 5 segundos, en vez de que lo descubras en la sustentación.

Además, un repositorio con pruebas se ve distinto a uno sin ellas.
"""
import sys, os
from datetime import date
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ia import fao56
from ia.perfiles import PERFILES, SUELOS, obtener_perfil, obtener_suelo
from ia.motor_recomendacion import _decidir, _evaluar_pastoreo, redactar_mensaje


# ============================================================
#  Modelo físico FAO-56
# ============================================================

def test_presion_atmosferica_por_altitud():
    """A 2587 m la presión debe ser ~74 kPa, no los 101 del nivel del mar.
    Si esto falla, la ET0 sale sobreestimada 8-12% en toda la Sabana."""
    assert 73 < fao56.presion_atmosferica(2587) < 76
    assert 100 < fao56.presion_atmosferica(0) < 102


def test_et0_en_rango_realista_sabana():
    """La ET0 en la Sabana de Bogotá está entre 2 y 5 mm/día.
    Fuera de ese rango, algo está mal en el cálculo."""
    for mes, dj in [("enero", 15), ("abril", 105), ("julio", 195), ("octubre", 288)]:
        et0 = fao56.et0_hargreaves(13.5, 20.0, 6.0, dj)
        assert 1.5 < et0 < 6.0, f"ET0 fuera de rango en {mes}: {et0}"


def test_et0_aumenta_con_temperatura():
    dj = 100
    frio = fao56.et0_hargreaves(10, 16, 4, dj)
    calor = fao56.et0_hargreaves(20, 28, 12, dj)
    assert calor > frio


def test_penman_monteith_coherente_con_hargreaves():
    """Los dos métodos deben dar valores del mismo orden.
    FAO acepta ±20% de diferencia entre ellos."""
    dj = 100
    h = fao56.et0_hargreaves(13.5, 20, 6, dj)
    pm = fao56.et0_penman_monteith(13.5, 20, 6, 72, 1.8, 18.5, dj)
    assert 0.5 < pm / h < 2.0, f"Divergencia excesiva: PM={pm}, H={h}"


def test_suelo_saturado_no_tiene_agotamiento():
    suelo = SUELOS["sabana_bogota"]
    e = fao56.calcular_estado_suelo(suelo["capacidad_campo_pct"],
                                    PERFILES["papa"], suelo)
    assert e.agotamiento_mm == 0
    assert e.coef_estres == 1.0


def test_suelo_en_marchitez_esta_en_estres_total():
    suelo = SUELOS["sabana_bogota"]
    e = fao56.calcular_estado_suelo(suelo["punto_marchitez_pct"],
                                    PERFILES["papa"], suelo)
    assert e.coef_estres == pytest.approx(0.0, abs=0.01)
    assert e.agotamiento_mm == pytest.approx(e.agua_disponible_total_mm, rel=0.02)


def test_agotamiento_es_monotono():
    """Menos humedad debe implicar siempre más agotamiento. Sin excepciones."""
    suelo, perfil = SUELOS["sabana_bogota"], PERFILES["kikuyo_pastoreo"]
    previos = -1
    for h in [30, 28, 26, 24, 22, 20, 18]:
        a = fao56.calcular_estado_suelo(h, perfil, suelo).agotamiento_mm
        assert a > previos, f"El agotamiento no creció al bajar la humedad a {h}%"
        previos = a


def test_lluvia_reduce_el_agotamiento():
    suelo, perfil = SUELOS["sabana_bogota"], PERFILES["kikuyo_pastoreo"]
    e = fao56.calcular_estado_suelo(22.0, perfil, suelo)
    seco = fao56.proyectar_agotamiento(e, 3.0, [0]*7)
    lluvia = fao56.proyectar_agotamiento(e, 3.0, [0, 25, 0, 0, 0, 0, 0])
    assert lluvia["trayectoria"][-1]["agotamiento_mm"] < seco["trayectoria"][-1]["agotamiento_mm"]


def test_percolacion_se_detecta_con_exceso_de_lluvia():
    """Si llueve más de lo que el suelo puede almacenar, debe reportarse
    percolación. Es el indicador de agua perdida."""
    suelo, perfil = SUELOS["sabana_bogota"], PERFILES["hortalizas_hoja"]
    e = fao56.calcular_estado_suelo(30.0, perfil, suelo)   # casi lleno
    proy = fao56.proyectar_agotamiento(e, 2.0, [80, 0, 0, 0, 0, 0, 0])
    assert proy["percolacion_total_mm"] > 0


def test_tiempo_de_riego_es_coherente():
    """1 mm sobre 1 m² = 1 litro. Verificación de la conversión de unidades."""
    r = fao56.tiempo_de_riego(lamina_bruta_mm=10, area_m2=1000, caudal_lps=2.0)
    assert r["volumen_litros"] == pytest.approx(10000)
    assert r["minutos"] == pytest.approx(10000 / 2.0 / 60, rel=0.01)


# ============================================================
#  Perfiles agronómicos
# ============================================================

def test_todos_los_perfiles_estan_completos():
    obligatorios = ["nombre", "modo", "kc_inicial", "kc_medio", "kc_final",
                    "profundidad_raiz_m", "mad"]
    for clave, p in PERFILES.items():
        for campo in obligatorios:
            assert campo in p, f"Al perfil '{clave}' le falta '{campo}'"
        assert p["modo"] in ("cultivo", "pastoreo")
        assert 0 < p["mad"] < 1, f"MAD fuera de rango en '{clave}'"
        assert 0.1 < p["profundidad_raiz_m"] < 2.0
        assert 0.2 < p["kc_medio"] < 1.5, f"Kc medio irreal en '{clave}'"


def test_todos_los_suelos_son_coherentes():
    for clave, s in SUELOS.items():
        assert s["capacidad_campo_pct"] > s["punto_marchitez_pct"], \
            f"En '{clave}' la capacidad de campo no supera el punto de marchitez"
        assert 0 < s["infiltracion_mm_h"] < 200


def test_kc_pastoreo_ignora_dias_desde_siembra():
    """El pasto permanente no tiene etapas fenológicas."""
    p = PERFILES["kikuyo_pastoreo"]
    assert fao56.kc_por_etapa(p, None) == fao56.kc_por_etapa(p, 500) == p["kc_medio"]


def test_kc_cultivo_sigue_las_etapas():
    p = PERFILES["papa"]
    assert fao56.kc_por_etapa(p, 10) == p["kc_inicial"]      # emergencia
    assert fao56.kc_por_etapa(p, 90) == p["kc_medio"]        # tuberización
    assert fao56.kc_por_etapa(p, 200) == p["kc_final"]       # senescencia


def test_perfil_inexistente_falla_claro():
    with pytest.raises(ValueError):
        obtener_perfil("cultivo_que_no_existe")


# ============================================================
#  Motor de decisión
# ============================================================

def _estado(agot, afd, adt, ks=1.0):
    return fao56.EstadoSuelo(adt, afd, agot, 25.0, ks, None)

_PROY_VACIA = {"dias_a_umbral_riego": None, "dias_a_estres_severo": None,
               "trayectoria": [], "percolacion_total_mm": 0}


def test_estres_severo_manda_regar_aunque_llueva():
    d = _decidir(_estado(65, 40, 72, ks=0.4), _PROY_VACIA, [50]*7, None,
                 PERFILES["papa"])
    assert d["accion"] == "regar"
    assert d["urgencia"] == "critica"


def test_no_riega_si_viene_lluvia_suficiente():
    """La regla que genera el ahorro: llegó al umbral pero llueve mañana."""
    d = _decidir(_estado(42, 40, 72), _PROY_VACIA, [0, 40, 0, 0, 0, 0, 0], None,
                 PERFILES["kikuyo_pastoreo"])
    assert d["accion"] == "esperar"
    assert d["ahorro_estimado_mm"] > 0


def test_riega_en_umbral_sin_lluvia():
    d = _decidir(_estado(42, 40, 72), _PROY_VACIA, [0]*7, None,
                 PERFILES["kikuyo_pastoreo"])
    assert d["accion"] == "regar"


def test_no_riega_con_suelo_humedo():
    d = _decidir(_estado(5, 40, 72), _PROY_VACIA, [0]*7, None,
                 PERFILES["kikuyo_pastoreo"])
    assert d["accion"] == "no_regar"


def test_ml_anticipa_el_riego():
    ml = {"cruzara_umbral_en_48h": True, "humedad_predicha_48h_pct": 18.0,
          "agotamiento_predicho_48h_mm": 45, "confianza": "alta", "mae_modelo_pct": 1.0}
    d = _decidir(_estado(20, 40, 72), _PROY_VACIA, [0]*7, ml,
                 PERFILES["kikuyo_pastoreo"])
    assert d["accion"] == "preparar"
    assert d["regla"] == "R4_prediccion_ml"


# ============================================================
#  Módulo de pastoreo
# ============================================================

def test_franja_no_lista_antes_del_descanso_minimo():
    r = _evaluar_pastoreo(PERFILES["kikuyo_pastoreo"], 10, 14.0, _estado(10, 40, 72), None)
    assert r["estado"] == "no_listo"


def test_franja_sobremadura_se_detecta():
    r = _evaluar_pastoreo(PERFILES["kikuyo_pastoreo"], 60, 14.0, _estado(10, 40, 72), None)
    assert r["estado"] == "sobremaduro"


def test_estres_hidrico_alarga_el_descanso():
    """Si el pasto está en estrés, rebrota más lento: hay que esperar más."""
    sin = _evaluar_pastoreo(PERFILES["kikuyo_pastoreo"], 30, 14.0, _estado(10, 40, 72, 1.0), None)
    con = _evaluar_pastoreo(PERFILES["kikuyo_pastoreo"], 30, 14.0, _estado(60, 40, 72, 0.5), None)
    assert con["dias_descanso_recomendado"] > sin["dias_descanso_recomendado"]


def test_pastoreo_sin_fecha_no_revienta():
    r = _evaluar_pastoreo(PERFILES["kikuyo_pastoreo"], None, 14.0, _estado(10, 40, 72), None)
    assert r["estado"] == "sin_datos"


# ============================================================
#  Redacción del mensaje
# ============================================================

def _resultado_base(accion="no_regar"):
    return {
        "decision": {"accion": accion, "urgencia": "ninguna", "razon": "Prueba."},
        "estado_suelo": {"pct_agua_disponible": 55.0},
        "clima": {"lluvia_proxima_7d_mm": 2.0},
        "proyeccion": {"percolacion_total_mm": 0.0},
    }


def test_mensaje_empieza_en_mayuscula():
    m = redactar_mensaje(_resultado_base())
    letras = [c for c in m if c.isalpha()]
    assert letras[0].isupper()


def test_mensaje_incluye_el_nombre_del_productor():
    assert "Don Jaime" in redactar_mensaje(_resultado_base(), "Don Jaime")


def test_mensaje_de_riego_dice_los_minutos():
    """El productor necesita minutos, no milímetros."""
    r = _resultado_base("regar")
    r["riego"] = {"lamina_bruta_mm": 12.0, "m3_por_hectarea": 120.0, "sistema": "Aspersión",
                  "minutos": 45, "volumen_m3": 6.5, "fraccionar_en_pasadas": False,
                  "pasadas_sugeridas": 1}
    m = redactar_mensaje(r)
    assert "45" in m and "minutos" in m.lower()


def test_avisa_cuando_hay_que_fraccionar_el_riego():
    r = _resultado_base("regar")
    r["riego"] = {"lamina_bruta_mm": 40.0, "m3_por_hectarea": 400.0, "sistema": "Aspersión",
                  "minutos": 150, "volumen_m3": 20.0, "fraccionar_en_pasadas": True,
                  "pasadas_sugeridas": 3}
    assert "pasadas" in redactar_mensaje(r).lower()


# ============================================================
#  Reporte de indicadores
# ============================================================

def test_indicadores_calculan_volumen_correcto():
    import reporte_pueaa as rp
    u = rp.UsuarioAgua(nombre_predio="Test", propietario="X", documento="1",
                       area_regada_ha=2.0, caudal_concesionado_lps=1.0,
                       tiene_concesion=True)
    caudal = [{"ts": "2026-09-01T00:00:00", "litros_periodo": 1000.0, "caudal_lps": 0.5}] * 10
    ind = rp.calcular_indicadores(u, caudal, [], date(2026, 9, 1), date(2026, 9, 30),
                                  volumen_linea_base_m3=15.0)
    assert ind.volumen_captado_m3 == pytest.approx(10.0)
    assert ind.ahorro_m3 == pytest.approx(5.0)
    assert ind.ahorro_pct == pytest.approx(33.3, abs=0.5)


def test_reporte_no_menciona_autoridades_regionales():
    """El alcance del proyecto es municipal. Si alguien reintroduce
    lenguaje de trámite regional, esta prueba lo detecta."""
    import reporte_pueaa as rp
    u = rp.UsuarioAgua(nombre_predio="Test", propietario="X", documento="1")
    ind = rp.calcular_indicadores(u, [], [], date(2026, 9, 1), date(2026, 9, 30))
    texto = rp.generar_reporte_markdown(u, ind)
    for prohibido in ["CAR ", "SIRH", "Corporación Autónoma", "VITAL"]:
        assert prohibido not in texto, f"El reporte menciona '{prohibido}'"
