"""
HidroSopó — Motor agronómico FAO-56
====================================
Implementa el estándar FAO Irrigation and Drainage Paper No. 56
(Allen et al., 1998) para calcular evapotranspiración y balance hídrico.

Esto NO es machine learning: es el modelo físico que sustenta la decisión.
El ML (ver modelo_ml.py) se monta encima para predecir el futuro.

Costo: $0. Es matemática pura.
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from datetime import date

# Constantes del sitio — Sopó, Cundinamarca
LATITUD_SOPO = 4.9083          # grados norte
LONGITUD_SOPO = -73.9403
ALTITUD_SOPO = 2587            # msnm (ajustar al predio exacto con GPS)


# ============================================================
#  Evapotranspiración de referencia (ET0)
# ============================================================

def presion_atmosferica(altitud_m: float) -> float:
    """Presión atmosférica en kPa. FAO-56 Ec. 7.

    A 2587 m la presión es ~74 kPa contra 101 kPa a nivel del mar.
    Esto importa: usar la constante de nivel del mar sobreestima
    la ET0 en la Sabana de Bogotá en un 8-12%.
    """
    return 101.3 * ((293.0 - 0.0065 * altitud_m) / 293.0) ** 5.26


def constante_psicrometrica(altitud_m: float) -> float:
    """gamma en kPa/°C. FAO-56 Ec. 8."""
    return 0.000665 * presion_atmosferica(altitud_m)


def presion_vapor_saturacion(temp_c: float) -> float:
    """e°(T) en kPa. FAO-56 Ec. 11."""
    return 0.6108 * math.exp((17.27 * temp_c) / (temp_c + 237.3))


def pendiente_curva_vapor(temp_c: float) -> float:
    """Delta en kPa/°C. FAO-56 Ec. 13."""
    es = presion_vapor_saturacion(temp_c)
    return (4098.0 * es) / ((temp_c + 237.3) ** 2)


def radiacion_extraterrestre(latitud_deg: float, dia_juliano: int) -> float:
    """Ra en MJ/m²/día. FAO-56 Ec. 21-25."""
    phi = math.radians(latitud_deg)
    dr = 1.0 + 0.033 * math.cos(2.0 * math.pi * dia_juliano / 365.0)
    delta = 0.409 * math.sin(2.0 * math.pi * dia_juliano / 365.0 - 1.39)

    arg = -math.tan(phi) * math.tan(delta)
    arg = max(-1.0, min(1.0, arg))       # cerca del ecuador nunca satura, pero por seguridad
    ws = math.acos(arg)

    return (24.0 * 60.0 / math.pi) * 0.0820 * dr * (
        ws * math.sin(phi) * math.sin(delta) +
        math.cos(phi) * math.cos(delta) * math.sin(ws)
    )


def et0_hargreaves(t_media: float, t_max: float, t_min: float,
                   dia_juliano: int, latitud: float = LATITUD_SOPO) -> float:
    """ET0 en mm/día por Hargreaves-Samani. FAO-56 Ec. 52.

    Método de respaldo cuando faltan datos de radiación y viento.
    Es el que usamos con los sensores del nodo, que no miden radiación
    ni velocidad de viento.

    Precisión: ±15-20% contra Penman-Monteith. Aceptable para decisiones
    de riego, y es el método que la propia FAO recomienda cuando hay
    datos limitados.
    """
    if t_max < t_min:
        t_max, t_min = t_min, t_max
    ra = radiacion_extraterrestre(latitud, dia_juliano)
    delta_t = max(0.0, t_max - t_min)
    et0 = 0.0023 * (t_media + 17.8) * math.sqrt(delta_t) * ra * 0.408
    return max(0.0, et0)


def et0_penman_monteith(t_media: float, t_max: float, t_min: float,
                        hr_media: float, viento_2m: float,
                        radiacion_solar: float,
                        dia_juliano: int,
                        latitud: float = LATITUD_SOPO,
                        altitud: float = ALTITUD_SOPO) -> float:
    """ET0 en mm/día por Penman-Monteith FAO-56. Ec. 6.

    Es el método de referencia. Requiere radiación solar y viento,
    que en nuestro caso vienen de Open-Meteo, no del nodo.

    Args:
        radiacion_solar: Rs en MJ/m²/día
        viento_2m: velocidad del viento a 2 m en m/s
    """
    gamma = constante_psicrometrica(altitud)
    delta = pendiente_curva_vapor(t_media)

    es = (presion_vapor_saturacion(t_max) + presion_vapor_saturacion(t_min)) / 2.0
    ea = es * (hr_media / 100.0)
    deficit = max(0.0, es - ea)

    ra = radiacion_extraterrestre(latitud, dia_juliano)
    rso = (0.75 + 2e-5 * altitud) * ra            # radiación de cielo despejado
    rns = (1.0 - 0.23) * radiacion_solar          # neta de onda corta, albedo 0.23

    # Neta de onda larga. FAO-56 Ec. 39
    sigma = 4.903e-9
    rel = min(1.0, radiacion_solar / rso) if rso > 0 else 0.0
    rnl = (sigma * (((t_max + 273.16) ** 4 + (t_min + 273.16) ** 4) / 2.0)
           * (0.34 - 0.14 * math.sqrt(max(0.0, ea)))
           * (1.35 * rel - 0.35))
    rn = rns - rnl

    g = 0.0    # flujo de calor del suelo, despreciable a escala diaria

    u2 = max(0.5, viento_2m)   # FAO-56 recomienda mínimo 0.5 m/s

    numerador = 0.408 * delta * (rn - g) + gamma * (900.0 / (t_media + 273.0)) * u2 * deficit
    denominador = delta + gamma * (1.0 + 0.34 * u2)
    return max(0.0, numerador / denominador)


# ============================================================
#  Coeficiente de cultivo y ETc
# ============================================================

def kc_por_etapa(perfil: dict, dias_desde_siembra: int | None) -> float:
    """Interpola el Kc según la etapa fenológica.

    En pastoreo permanente (kikuyo, raigrás establecido) no hay
    'días desde siembra': el pasto está siempre en etapa media.
    """
    if perfil.get("modo") == "pastoreo" or dias_desde_siembra is None:
        return perfil["kc_medio"]

    d = dias_desde_siembra
    e = perfil["etapas_dias"]      # [inicial, desarrollo, media, final]
    acum_ini = e[0]
    acum_des = e[0] + e[1]
    acum_med = e[0] + e[1] + e[2]
    acum_fin = sum(e)

    if d <= acum_ini:
        return perfil["kc_inicial"]
    if d <= acum_des:
        # interpolación lineal inicial -> medio
        f = (d - acum_ini) / max(1, e[1])
        return perfil["kc_inicial"] + f * (perfil["kc_medio"] - perfil["kc_inicial"])
    if d <= acum_med:
        return perfil["kc_medio"]
    if d <= acum_fin:
        f = (d - acum_med) / max(1, e[3])
        return perfil["kc_medio"] + f * (perfil["kc_final"] - perfil["kc_medio"])
    return perfil["kc_final"]


def etc(et0: float, kc: float, coef_estres: float = 1.0) -> float:
    """Evapotranspiración del cultivo. ETc = ET0 x Kc x Ks."""
    return et0 * kc * coef_estres


# ============================================================
#  Balance hídrico del suelo
# ============================================================

@dataclass
class EstadoSuelo:
    """Estado del reservorio de agua en la zona radicular."""
    agua_disponible_total_mm: float      # ADT (TAW en FAO-56)
    agua_facilmente_disponible_mm: float # AFD (RAW)
    agotamiento_mm: float                # Dr: cuánta agua le falta al suelo
    humedad_volumetrica_pct: float
    coef_estres: float                   # Ks: 1.0 = sin estrés, <1 = con estrés
    dias_a_umbral: float | None          # cuándo tocará regar


def calcular_estado_suelo(humedad_vol_pct: float, perfil: dict,
                          suelo: dict) -> EstadoSuelo:
    """Convierte una lectura de humedad volumétrica en estado agronómico.

    Referencias FAO-56 Ec. 82, 83, 84.
    """
    cc = suelo["capacidad_campo_pct"]     # theta_FC
    pmp = suelo["punto_marchitez_pct"]    # theta_WP
    zr = perfil["profundidad_raiz_m"]
    p = perfil["mad"]                     # fracción de agotamiento permisible

    # ADT = 1000 * (theta_FC - theta_WP) * Zr    [mm]
    adt = 1000.0 * ((cc - pmp) / 100.0) * zr
    afd = adt * p

    theta = max(pmp, min(cc, humedad_vol_pct))
    # Dr = 1000 * (theta_FC - theta) * Zr
    agotamiento = 1000.0 * ((cc - theta) / 100.0) * zr
    agotamiento = max(0.0, min(adt, agotamiento))

    # Coeficiente de estrés hídrico. FAO-56 Ec. 84
    if agotamiento <= afd:
        ks = 1.0
    else:
        ks = max(0.0, (adt - agotamiento) / (adt - afd)) if adt > afd else 0.0

    return EstadoSuelo(
        agua_disponible_total_mm=round(adt, 1),
        agua_facilmente_disponible_mm=round(afd, 1),
        agotamiento_mm=round(agotamiento, 1),
        humedad_volumetrica_pct=round(theta, 1),
        coef_estres=round(ks, 3),
        dias_a_umbral=None,
    )


def proyectar_agotamiento(estado: EstadoSuelo, etc_diaria_mm: float,
                          lluvia_pronosticada_mm: list[float],
                          eficiencia_lluvia: float = 0.80) -> dict:
    """Simula el balance hídrico día a día hacia adelante.

    Esta función es la que responde: "¿tengo que regar hoy o puedo esperar?"

    Entrada:
        lluvia_pronosticada_mm: lista con la lluvia esperada por día
                                (viene de Open-Meteo)
        eficiencia_lluvia: no toda la lluvia entra al suelo; parte escurre.
                           0.80 es conservador para suelos francos.
    """
    dr = estado.agotamiento_mm
    afd = estado.agua_facilmente_disponible_mm
    adt = estado.agua_disponible_total_mm

    trayectoria = []
    dia_umbral = None
    dia_estres = None

    for i, lluvia in enumerate(lluvia_pronosticada_mm):
        efectiva = lluvia * eficiencia_lluvia
        # el suelo no puede almacenar más allá de capacidad de campo:
        # lo que sobra percola (y es agua perdida)
        percolacion = max(0.0, efectiva - dr)
        dr = dr - efectiva + percolacion
        dr = dr + etc_diaria_mm
        dr = max(0.0, min(adt, dr))

        if dia_umbral is None and dr >= afd:
            dia_umbral = i
        if dia_estres is None and dr >= adt * 0.95:
            dia_estres = i

        trayectoria.append({
            "dia": i,
            "agotamiento_mm": round(dr, 1),
            "lluvia_efectiva_mm": round(efectiva, 1),
            "percolacion_mm": round(percolacion, 1),
            "pct_agua_disponible": round(100.0 * (1.0 - dr / adt), 1) if adt > 0 else 0.0,
        })

    return {
        "trayectoria": trayectoria,
        "dias_a_umbral_riego": dia_umbral,
        "dias_a_estres_severo": dia_estres,
        "percolacion_total_mm": round(sum(t["percolacion_mm"] for t in trayectoria), 1),
    }


def lamina_riego_recomendada(estado: EstadoSuelo, perfil: dict,
                             eficiencia_aplicacion: float = 0.75) -> dict:
    """Calcula cuánta agua aplicar en UN riego.

    eficiencia_aplicacion típica:
        aspersión           0.75
        goteo               0.90
        gravedad/inundación 0.50
        manguera manual     0.60

    Regla agronómica importante: NO se repone todo el agotamiento de un
    solo golpe cuando el suelo se dejó secar de más. La lámina se limita
    al agua fácilmente disponible (AFD/RAW). Reponer 70 mm en una pasada
    sobre un suelo muy seco no hidrata: sella la superficie, escurre y
    percola. Si hay déficit acumulado, se repone en varios riegos.
    """
    agotamiento = estado.agotamiento_mm
    afd = estado.agua_facilmente_disponible_mm

    lamina_neta = min(agotamiento, afd) if afd > 0 else agotamiento
    deficit_pendiente = max(0.0, agotamiento - lamina_neta)

    lamina_bruta = lamina_neta / eficiencia_aplicacion if eficiencia_aplicacion > 0 else 0.0

    return {
        "lamina_neta_mm": round(lamina_neta, 1),
        "lamina_bruta_mm": round(lamina_bruta, 1),
        "agotamiento_total_mm": round(agotamiento, 1),
        "deficit_pendiente_mm": round(deficit_pendiente, 1),
        "repone_en_un_riego": deficit_pendiente < 1.0,
        "litros_por_m2": round(lamina_bruta, 1),          # 1 mm = 1 L/m²
        "litros_por_hectarea": round(lamina_bruta * 10000, 0),
        "m3_por_hectarea": round(lamina_bruta * 10.0, 2),
        "eficiencia_usada": eficiencia_aplicacion,
    }


def tiempo_de_riego(lamina_bruta_mm: float, area_m2: float,
                    caudal_lps: float) -> dict:
    """Traduce la lámina a minutos de bombeo.

    Este es el número que el productor realmente usa. Decirle
    '12.4 mm' no le sirve; decirle '38 minutos' sí.
    """
    volumen_litros = lamina_bruta_mm * area_m2      # mm * m² = litros
    if caudal_lps <= 0:
        return {"error": "caudal no valido"}
    segundos = volumen_litros / caudal_lps
    minutos = segundos / 60.0

    # Un turno de riego de más de 4 horas no es realista en una finca
    # pequeña. Si sale eso, el caudal no alcanza y hay que repartir en días.
    MAX_MIN_POR_JORNADA = 240
    excede_jornada = minutos > MAX_MIN_POR_JORNADA
    dias_necesarios = max(1, int(minutos / MAX_MIN_POR_JORNADA) + (1 if minutos % MAX_MIN_POR_JORNADA else 0))

    return {
        "volumen_litros": round(volumen_litros, 0),
        "volumen_m3": round(volumen_litros / 1000.0, 2),
        "minutos": round(minutos, 0),
        "horas": round(segundos / 3600.0, 2),
        "excede_jornada": excede_jornada,
        "dias_necesarios": dias_necesarios if excede_jornada else 1,
        "minutos_por_dia": round(minutos / dias_necesarios, 0) if excede_jornada else round(minutos, 0),
        "tasa_aplicacion_mm_h": round(lamina_bruta_mm / max(0.01, segundos/3600), 2),
    }


# ============================================================
#  Utilidades
# ============================================================

def dia_juliano(fecha: date) -> int:
    return fecha.timetuple().tm_yday


def adc_a_humedad_volumetrica(adc: int, cal: dict) -> float:
    """Aplica la curva de calibración del sensor.

    cal = {"a": ..., "b": ..., "c": ...} del polinomio de grado 2
    obtenido en el procedimiento gravimétrico.
    """
    theta = cal["a"] * adc ** 2 + cal["b"] * adc + cal["c"]
    return max(0.0, min(60.0, theta))


if __name__ == "__main__":
    # Prueba rápida con datos típicos de Sopó en época seca
    hoy = date(2026, 1, 15)
    dj = dia_juliano(hoy)

    et0_h = et0_hargreaves(t_media=13.5, t_max=20.0, t_min=6.0, dia_juliano=dj)
    print(f"ET0 Hargreaves (Sopó, 15-ene): {et0_h:.2f} mm/día")

    et0_pm = et0_penman_monteith(
        t_media=13.5, t_max=20.0, t_min=6.0, hr_media=72.0,
        viento_2m=1.8, radiacion_solar=18.5, dia_juliano=dj)
    print(f"ET0 Penman-Monteith:           {et0_pm:.2f} mm/día")
    print(f"Presión atmosférica a {ALTITUD_SOPO} m: {presion_atmosferica(ALTITUD_SOPO):.1f} kPa")
