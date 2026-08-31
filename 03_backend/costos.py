"""
HidroSopó — Qué cuesta el agua y qué se ahorra en pesos
========================================================
El productor no siente el ahorro en metros cúbicos. Lo siente en la
factura de la luz, en los galones de ACPM, o en el recibo del acueducto.

Este módulo separa el ahorro en sus componentes reales:

    ┌─ AGUA      → solo si la compra a un acueducto (tarifa por m³)
    ├─ ENERGÍA   → lo que cuesta bombearla (kWh o litros de ACPM)
    └─ TASA      → tasa por uso del agua, si tiene concesión

La separación importa: la mayoría de las fincas de Sopó toman agua de
una quebrada o un pozo propio. Para ellos el agua es GRATIS y el 100%
del ahorro está en la energía. Decirles "ahorró en la factura del agua"
cuando no pagan agua es mentirles.

Todos los precios son configurables por predio y hay que VERIFICARLOS
con la factura real. Los valores por defecto son referenciales.
"""
from __future__ import annotations

# Energía hidráulica para elevar 1 m³ un metro:
#   E = rho * g * H * V / 3.6e6  [kWh]   con rho=1000 kg/m³, g=9.81 m/s²
KWH_POR_M3_POR_METRO = 1000 * 9.81 / 3.6e6      # ≈ 0.0027250

# Rendimiento de una motobomba diésel pequeña de finca.
# El valor teórico de un diésel es ~10 kWh/L de energía química, pero un
# motor pequeño y viejo entrega apenas 20-25% en el eje. 2.2 kWh útiles
# por litro es realista; 3.0 sería optimista y subestimaría el ahorro.
# Si el productor sabe cuántos litros/hora gasta su motor, se usa ESE dato
# en vez de la estimación: él lo mide llenando el tanque.
KWH_UTILES_POR_LITRO_ACPM = 2.2


def _attr(predio, nombre, defecto):
    v = getattr(predio, nombre, None)
    return defecto if v is None else v


# ============================================================
#  Energía de bombeo
# ============================================================

def energia_por_m3(altura_m: float, eficiencia: float = 0.55) -> float:
    """kWh necesarios para bombear un metro cúbico a esa altura."""
    if eficiencia <= 0:
        eficiencia = 0.55
    return KWH_POR_M3_POR_METRO * max(0.0, altura_m) / eficiencia


# ============================================================
#  Desglose del costo por metro cúbico
# ============================================================

def desglose_por_m3(predio) -> dict:
    """Cuánto cuesta un metro cúbico, línea por línea.

    Devuelve cada componente por separado para que el productor vea
    exactamente de dónde sale su ahorro.
    """
    tipo = (_attr(predio, "tipo_energia", "electrica") or "electrica").lower()
    tarifa_agua = float(_attr(predio, "tarifa_agua_m3", 0) or 0)
    tasa_uso = float(_attr(predio, "tasa_uso_agua_m3", 0) or 0)

    lineas = []

    # ---- 1. El agua en sí ----
    if tarifa_agua > 0:
        lineas.append({
            "concepto": "Agua",
            "cop_por_m3": round(tarifa_agua, 2),
            "detalle": "Tarifa del acueducto por metro cúbico.",
        })
    else:
        lineas.append({
            "concepto": "Agua",
            "cop_por_m3": 0.0,
            "detalle": "El agua es de fuente propia: no la paga. "
                       "Todo su ahorro está en la energía de bombeo.",
        })

    # ---- 2. La energía para moverla ----
    energia = {"concepto": "Energía", "cop_por_m3": 0.0, "kwh_por_m3": 0.0}

    if tipo == "gravedad":
        energia["detalle"] = "El agua llega por gravedad: no gasta energía en bombear."
    else:
        kwh = energia_por_m3(float(_attr(predio, "altura_bombeo_m", 30)),
                             float(_attr(predio, "eficiencia_bomba", 0.55)))
        energia["kwh_por_m3"] = round(kwh, 4)

        if tipo == "diesel":
            precio = float(_attr(predio, "costo_diesel_litro", 13000))
            lph = float(_attr(predio, "consumo_diesel_lph", 0) or 0)
            caudal = float(_attr(predio, "caudal_disponible_lps", 0) or 0)

            if lph > 0 and caudal > 0:
                # Método preferido: el consumo real del motor.
                # Bombear 1 m³ toma 1000/(caudal_lps*3600) horas.
                horas_por_m3 = 1000.0 / (caudal * 3600.0)
                litros = horas_por_m3 * lph
                origen = f"medido: {lph:.1f} L/hora del motor"
            else:
                litros = kwh / KWH_UTILES_POR_LITRO_ACPM
                origen = "estimado a partir de la altura de bombeo"

            energia["cop_por_m3"] = round(litros * precio, 2)
            energia["litros_diesel_por_m3"] = round(litros, 5)
            energia["detalle"] = (f"ACPM para bombear a "
                                  f"{_attr(predio,'altura_bombeo_m',30):.0f} m "
                                  f"de altura ({origen}).")
        else:
            precio = float(_attr(predio, "costo_kwh", 850))
            energia["cop_por_m3"] = round(kwh * precio, 2)
            energia["detalle"] = (f"Energía eléctrica para bombear a "
                                  f"{_attr(predio,'altura_bombeo_m',30):.0f} m "
                                  f"de altura, a {pesos(precio)} el kWh.")
    lineas.append(energia)

    # ---- 3. Tasa por uso del agua (si tiene concesión) ----
    if tasa_uso > 0:
        lineas.append({
            "concepto": "Tasa por uso del agua",
            "cop_por_m3": round(tasa_uso, 2),
            "detalle": "Tasa que se paga por el volumen captado bajo concesión.",
        })

    total = sum(l["cop_por_m3"] for l in lineas)
    return {
        "lineas": lineas,
        "total_cop_por_m3": round(total, 2),
        "kwh_por_m3": energia.get("kwh_por_m3", 0.0),
        "tipo_energia": tipo,
        "paga_agua": tarifa_agua > 0,
    }


# Compatibilidad con el código anterior
def costo_por_m3(predio) -> dict:
    d = desglose_por_m3(predio)
    salida = {"cop_por_m3": d["total_cop_por_m3"], "kwh_por_m3": d["kwh_por_m3"],
              "tipo": d["tipo_energia"], "detalle": d["lineas"][-1]["detalle"]}
    for l in d["lineas"]:
        if "litros_diesel_por_m3" in l:
            salida["litros_diesel_por_m3"] = l["litros_diesel_por_m3"]
    return salida


# ============================================================
#  Valorizar un volumen
# ============================================================

def valorizar(m3: float, predio) -> dict:
    """Traduce metros cúbicos a pesos, con el desglose por concepto."""
    d = desglose_por_m3(predio)
    conceptos = []
    for l in d["lineas"]:
        cop = m3 * l["cop_por_m3"]
        item = {"concepto": l["concepto"], "cop": round(cop, 0),
                "detalle": l["detalle"]}
        if l.get("kwh_por_m3"):
            item["kwh"] = round(m3 * l["kwh_por_m3"], 2)
        if l.get("litros_diesel_por_m3"):
            item["litros_diesel"] = round(m3 * l["litros_diesel_por_m3"], 2)
            item["galones_diesel"] = round(item["litros_diesel"] / 3.785, 2)
        conceptos.append(item)

    total = sum(c["cop"] for c in conceptos)
    kwh = m3 * d["kwh_por_m3"]

    salida = {
        "m3": round(m3, 2),
        "cop": round(total, 0),
        "kwh": round(kwh, 2),
        "cop_por_m3": d["total_cop_por_m3"],
        "tipo_energia": d["tipo_energia"],
        "paga_agua": d["paga_agua"],
        "conceptos": conceptos,
        "cop_agua": round(next((c["cop"] for c in conceptos if c["concepto"] == "Agua"), 0), 0),
        "cop_energia": round(next((c["cop"] for c in conceptos if c["concepto"] == "Energía"), 0), 0),
    }
    lts = next((c.get("litros_diesel") for c in conceptos if c.get("litros_diesel")), None)
    if lts:
        salida["litros_diesel"] = lts
    return salida


# ============================================================
#  Formato y equivalencias
# ============================================================

def pesos(v: float) -> str:
    """Formato colombiano: $1.234.567"""
    return "$" + f"{round(v):,}".replace(",", ".")


def equivalencias(m3: float, kwh: float) -> list[str]:
    """Traduce las cifras a cosas que se pueden imaginar.

    '56 m³' no le dice nada a nadie. 'Un carrotanque' sí.
    """
    e = []
    if m3 >= 1:
        e.append(f"{m3/1:.0f} tanques de mil litros")
    if m3 >= 10:
        e.append(f"{m3/10:.1f} carrotanques de 10 m³")
    if kwh >= 1:
        # Una nevera de finca consume del orden de 1 kWh al día
        e.append(f"lo que gasta una nevera en {kwh/1.0:.0f} días")
    return e


# ============================================================
#  Proyección y retorno de la inversión
# ============================================================

def proyectar_anual(ahorro_m3: float, dias: int, predio) -> dict:
    """Extrapola el ahorro medido a un año, con su advertencia."""
    if dias <= 0:
        return {}
    anual_m3 = ahorro_m3 / dias * 365
    v = valorizar(anual_m3, predio)
    v["dias_medidos"] = dias
    v["nota"] = (f"Proyección a partir de {dias} días medidos. El ahorro real "
                 "cambia con la temporada: en época de lluvias se riega menos "
                 "y por tanto se ahorra menos.")
    return v


def retorno_inversion(ahorro_m3: float, dias: int, predio,
                      inversion_cop: float = 1_720_000) -> dict:
    """En cuánto tiempo se paga el sistema con el ahorro medido.

    Este número es el que decide si el proyecto se puede replicar, y hay
    que calcularlo con honestidad: en una finca pequeña con energía
    eléctrica barata, el ahorro de bombeo solo NO alcanza a pagar el
    equipo en poco tiempo. Eso no invalida el proyecto, pero sí obliga
    a nombrar de dónde viene el resto del valor.
    """
    if dias <= 0 or ahorro_m3 <= 0:
        return {"calculable": False,
                "motivo": "Todavía no hay ahorro medido para calcularlo."}

    anual = proyectar_anual(ahorro_m3, dias, predio)
    ahorro_anual = anual.get("cop", 0)
    if ahorro_anual <= 0:
        return {"calculable": False,
                "motivo": "El ahorro no tiene valor monetario en este predio "
                          "(agua propia y riego por gravedad)."}

    anios = inversion_cop / ahorro_anual

    if anios <= 3:
        veredicto = ("El sistema se paga solo con el ahorro de bombeo. "
                     "Es replicable tal cual.")
    elif anios <= 7:
        veredicto = ("Se paga en un plazo razonable para un equipo que dura "
                     "varios años, pero conviene abaratar el hardware para replicarlo.")
    else:
        veredicto = (
            "Con el ahorro de bombeo solo, el equipo no se paga en un plazo corto. "
            "Esto es esperable en un predio pequeño con energía barata, y no "
            "invalida el proyecto: el valor está también en no perder producción "
            "por estrés hídrico, en poder demostrar el uso del agua, y en que el "
            "costo por predio baja mucho al replicar. Para que el retorno sea "
            "atractivo hay que bajar el costo del equipo o aplicarlo donde el "
            "bombeo sea más caro (diésel, mayor altura, más área)."
        )

    return {
        "calculable": True,
        "inversion_cop": round(inversion_cop, 0),
        "ahorro_anual_cop": round(ahorro_anual, 0),
        "ahorro_anual_m3": anual.get("m3"),
        "anios_retorno": round(anios, 1),
        "meses_retorno": round(anios * 12),
        "veredicto": veredicto,
    }
