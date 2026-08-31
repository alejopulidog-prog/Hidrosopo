"""
HidroSopó — Motor de recomendación
===================================
Combina las tres capas:
  1. Modelo físico FAO-56 (balance hídrico)
  2. Modelo ML entrenado con datos del predio (predicción de humedad)
  3. Reglas agronómicas y de pastoreo

Salida: una recomendación en español que el productor entiende.

Costo de operación: $0.
"""

from __future__ import annotations
from datetime import date, datetime, timedelta
from typing import Optional
import statistics

from . import fao56
from .perfiles import obtener_perfil, obtener_suelo, SISTEMAS_RIEGO
from .clima import obtener_pronostico


# ============================================================
#  Decisión principal
# ============================================================

def generar_recomendacion(
    lecturas_humedad_pct: list[float],
    temp_aire_c: float,
    temp_max_c: float,
    temp_min_c: float,
    hr_pct: float,
    perfil_clave: str,
    suelo_clave: str,
    sistema_riego: str,
    area_m2: float,
    caudal_disponible_lps: float,
    lat: float = fao56.LATITUD_SOPO,
    lon: float = fao56.LONGITUD_SOPO,
    dias_desde_siembra: Optional[int] = None,
    dias_desde_ultimo_pastoreo: Optional[int] = None,
    prediccion_ml: Optional[dict] = None,
    fecha: Optional[date] = None,
) -> dict:
    """Genera la recomendación completa de riego/manejo."""

    fecha = fecha or date.today()
    perfil = obtener_perfil(perfil_clave)
    suelo = obtener_suelo(suelo_clave)
    eficiencia = SISTEMAS_RIEGO.get(sistema_riego, {"eficiencia": 0.75})["eficiencia"]

    # ---- 1. Humedad representativa de la zona radicular ----
    # Pondera por profundidad: el sensor superficial pesa más porque
    # ahí está la mayor densidad de raíces.
    pesos = [0.5, 0.3, 0.2][:len(lecturas_humedad_pct)]
    total_peso = sum(pesos)
    humedad_ponderada = sum(h * p for h, p in zip(lecturas_humedad_pct, pesos)) / total_peso

    # ---- 2. Estado del suelo (FAO-56) ----
    estado = fao56.calcular_estado_suelo(humedad_ponderada, perfil, suelo)

    # ---- 3. Clima: pronóstico y ET0 ----
    clima = obtener_pronostico(lat, lon, dias=7)

    dj = fao56.dia_juliano(fecha)
    if clima and clima.get("et0_diaria"):
        et0_hoy = clima["et0_diaria"][0]
        et0_futuro = clima["et0_diaria"]
        lluvia_futura = clima["lluvia_diaria"]
        fuente_clima = "Open-Meteo"
    else:
        # Respaldo: calcular con los sensores del nodo
        et0_hoy = fao56.et0_hargreaves(temp_aire_c, temp_max_c, temp_min_c, dj, lat)
        et0_futuro = [et0_hoy] * 7
        lluvia_futura = [0.0] * 7
        fuente_clima = "sensores locales (Hargreaves) - sin conexión a Open-Meteo"

    kc = fao56.kc_por_etapa(perfil, dias_desde_siembra)
    etc_hoy = fao56.etc(et0_hoy, kc, estado.coef_estres)
    etc_futuro = [fao56.etc(e, kc) for e in et0_futuro]

    # ---- 4. Proyección del balance hídrico ----
    proyeccion = fao56.proyectar_agotamiento(
        estado, statistics.mean(etc_futuro), lluvia_futura
    )

    # ---- 5. Ajuste con el modelo ML (si existe) ----
    ajuste_ml = None
    if prediccion_ml:
        h48 = prediccion_ml.get("humedad_48h_pct")
        if h48 is not None:
            estado_48 = fao56.calcular_estado_suelo(h48, perfil, suelo)
            ajuste_ml = {
                "humedad_predicha_48h_pct": round(h48, 1),
                "agotamiento_predicho_48h_mm": estado_48.agotamiento_mm,
                "cruzara_umbral_en_48h": estado_48.agotamiento_mm >= estado.agua_facilmente_disponible_mm,
                "confianza": prediccion_ml.get("confianza"),
                "mae_modelo_pct": prediccion_ml.get("mae"),
            }

    # ---- 6. Decisión ----
    decision = _decidir(estado, proyeccion, lluvia_futura, ajuste_ml, perfil)

    # ---- 7. Dosis y tiempo ----
    riego = fao56.lamina_riego_recomendada(estado, perfil, eficiencia)
    tiempo = fao56.tiempo_de_riego(riego["lamina_bruta_mm"], area_m2, caudal_disponible_lps)

    # No tiene sentido recomendar una lámina que el suelo no puede
    # infiltrar en una sola pasada: se escurre.
    lamina_max_por_pasada = suelo["infiltracion_mm_h"] * 2.0
    fraccionar = riego["lamina_bruta_mm"] > lamina_max_por_pasada

    resultado = {
        "fecha": fecha.isoformat(),
        "perfil": perfil["nombre"],
        "modo": perfil["modo"],
        "estado_suelo": {
            "humedad_ponderada_pct": round(humedad_ponderada, 1),
            "lecturas_por_profundidad": lecturas_humedad_pct,
            "agua_disponible_total_mm": estado.agua_disponible_total_mm,
            "agua_facilmente_disponible_mm": estado.agua_facilmente_disponible_mm,
            "agotamiento_actual_mm": estado.agotamiento_mm,
            "pct_agua_disponible": round(
                100 * (1 - estado.agotamiento_mm / estado.agua_disponible_total_mm), 1
            ) if estado.agua_disponible_total_mm > 0 else 0,
            "coef_estres_ks": estado.coef_estres,
            "en_estres": estado.coef_estres < 1.0,
        },
        "clima": {
            "fuente": fuente_clima,
            "et0_hoy_mm": round(et0_hoy, 2),
            "kc_actual": round(kc, 2),
            "etc_hoy_mm": round(etc_hoy, 2),
            "lluvia_proxima_7d_mm": round(sum(lluvia_futura), 1),
            "lluvia_por_dia_mm": [round(x, 1) for x in lluvia_futura],
        },
        "proyeccion": proyeccion,
        "prediccion_ml": ajuste_ml,
        "decision": decision,
        "riego": {
            **riego,
            **tiempo,
            "sistema": SISTEMAS_RIEGO.get(sistema_riego, {}).get("nombre", sistema_riego),
            "fraccionar_en_pasadas": fraccionar,
            "pasadas_sugeridas": max(1, int(riego["lamina_bruta_mm"] / lamina_max_por_pasada) + 1) if fraccionar else 1,
        } if decision["accion"] == "regar" else None,
    }

    # ---- 8. Módulo de pastoreo ----
    if perfil["modo"] == "pastoreo":
        resultado["pastoreo"] = _evaluar_pastoreo(
            perfil, dias_desde_ultimo_pastoreo, temp_aire_c, estado, clima
        )

    resultado["mensaje"] = redactar_mensaje(resultado)
    return resultado


# ============================================================
#  Lógica de decisión
# ============================================================

def _decidir(estado, proyeccion, lluvia_futura, ajuste_ml, perfil) -> dict:
    """Reglas de decisión, en orden de prioridad."""

    agot = estado.agotamiento_mm
    afd = estado.agua_facilmente_disponible_mm
    adt = estado.agua_disponible_total_mm
    lluvia_48h = sum(lluvia_futura[:2]) if len(lluvia_futura) >= 2 else 0.0

    # Regla 1 — estrés severo: regar sí o sí, aunque llueva
    if estado.coef_estres < 0.6:
        return {
            "accion": "regar",
            "urgencia": "critica",
            "razon": "El cultivo está en estrés hídrico severo. El agua disponible cayó "
                     f"a {round(100*(1-agot/adt))}% y ya hay pérdida de rendimiento.",
            "regla": "R1_estres_severo",
        }

    # Regla 2 — bajo el umbral pero viene lluvia significativa: esperar
    if agot >= afd and lluvia_48h >= (agot * 0.7):
        return {
            "accion": "esperar",
            "urgencia": "baja",
            "razon": f"El suelo llegó al umbral de riego, pero se pronostican "
                     f"{lluvia_48h:.0f} mm en 48 h, suficientes para reponer. "
                     "Regar ahora sería desperdiciar agua.",
            "regla": "R2_lluvia_suficiente",
            "ahorro_estimado_mm": round(agot, 1),
        }

    # Regla 3 — bajo el umbral, sin lluvia: regar
    if agot >= afd:
        return {
            "accion": "regar",
            "urgencia": "alta",
            "razon": f"El agotamiento ({agot:.0f} mm) superó el umbral de "
                     f"{afd:.0f} mm y no hay lluvia significativa pronosticada.",
            "regla": "R3_umbral_sin_lluvia",
        }

    # Regla 4 — el ML anticipa que se cruza el umbral y no hay lluvia
    if ajuste_ml and ajuste_ml["cruzara_umbral_en_48h"] and lluvia_48h < 3.0:
        return {
            "accion": "preparar",
            "urgencia": "media",
            "razon": "El modelo predice que el suelo cruzará el umbral de riego "
                     "en las próximas 48 horas sin lluvia de por medio. "
                     "Conviene programar el riego.",
            "regla": "R4_prediccion_ml",
        }

    # Regla 5 — proyección física indica riego próximo
    d = proyeccion.get("dias_a_umbral_riego")
    if d is not None and d <= 2:
        return {
            "accion": "preparar",
            "urgencia": "media",
            "razon": f"El balance hídrico proyecta llegar al umbral en {d + 1} día(s).",
            "regla": "R5_proyeccion_fao56",
            "dias_restantes": d + 1,
        }

    # Regla 6 — todo bien
    dias_txt = f"{d + 1} días" if d is not None else "más de 7 días"
    return {
        "accion": "no_regar",
        "urgencia": "ninguna",
        "razon": f"El suelo tiene humedad suficiente. Próximo riego estimado en {dias_txt}.",
        "regla": "R6_sin_necesidad",
        "dias_hasta_proximo_riego": (d + 1) if d is not None else None,
    }


def _evaluar_pastoreo(perfil, dias_descanso, temp_c, estado, clima) -> dict:
    """Módulo específico de pastoreo rotacional.

    Para una finca lechera de Sopó, saber cuándo entrar a una franja
    vale más que saber cuándo regar. Combina días de descanso,
    grados-día acumulados y estado hídrico.
    """
    if dias_descanso is None:
        return {"estado": "sin_datos",
                "mensaje": "Registra la fecha del último pastoreo para activar este módulo."}

    opt = perfil["dias_descanso_optimo"]
    mn = perfil["dias_descanso_min"]
    mx = perfil["dias_descanso_max"]

    # Grados-día acumulados: aproximación con la temperatura media
    gd_dia = max(0.0, temp_c - perfil["temp_base_gd"])
    gd_acum = gd_dia * dias_descanso
    gd_obj = perfil["gd_acumulados_objetivo"]

    # El estrés hídrico frena el rebrote: hay que esperar más
    penalizacion = 0
    if estado.coef_estres < 1.0:
        penalizacion = int((1.0 - estado.coef_estres) * 12)

    dias_recomendados = opt + penalizacion

    if dias_descanso < mn:
        estado_franja, msg = "no_listo", (
            f"Faltan {mn - dias_descanso} días para el descanso mínimo. "
            "Entrar antes reduce las reservas de la planta y compromete el siguiente rebrote."
        )
    elif dias_descanso >= dias_recomendados and gd_acum >= gd_obj * 0.85:
        estado_franja, msg = "listo", (
            f"La franja está lista para pastoreo ({dias_descanso} días de descanso, "
            f"{gd_acum:.0f} grados-día acumulados)."
        )
    elif dias_descanso > mx:
        estado_franja, msg = "sobremaduro", (
            f"La franja lleva {dias_descanso} días, por encima del máximo de {mx}. "
            "El pasto pierde calidad nutricional y se encaña. Pastorear pronto o cortar."
        )
    else:
        faltan = max(0, dias_recomendados - dias_descanso)
        extra = " El estrés hídrico está frenando el rebrote." if penalizacion else ""
        estado_franja, msg = "en_recuperacion", (
            f"Faltan aproximadamente {faltan} días.{extra}"
        )

    return {
        "estado": estado_franja,
        "mensaje": msg,
        "dias_descanso_actual": dias_descanso,
        "dias_descanso_recomendado": dias_recomendados,
        "grados_dia_acumulados": round(gd_acum, 0),
        "grados_dia_objetivo": gd_obj,
        "pct_recuperacion": min(100, round(100 * gd_acum / gd_obj)) if gd_obj else None,
        "penalizacion_por_estres_dias": penalizacion,
        "altura_objetivo_cm": perfil["altura_pastoreo_cm"],
        "altura_residual_cm": perfil["altura_residual_cm"],
    }


# ============================================================
#  Redacción en lenguaje natural (Capa 3, versión gratuita)
# ============================================================

def redactar_mensaje(r: dict, nombre_productor: str = "") -> str:
    """Convierte el resultado técnico en un mensaje que el productor entiende.

    Esta es la versión de plantillas: $0, sin dependencias, no falla.
    Si quieres LLM, ver llm_opcional.py — pero para el piloto,
    esto es más confiable.
    """
    saludo = f"{nombre_productor}, " if nombre_productor else ""
    d = r["decision"]
    es = r["estado_suelo"]
    cl = r["clima"]

    partes = []

    if d["accion"] == "regar":
        rg = r["riego"]
        emoji = "🔴" if d["urgencia"] == "critica" else "🟠"
        partes.append(f"{emoji} {saludo}hay que regar hoy.")
        partes.append(
            f"El suelo está al {es['pct_agua_disponible']}% de su agua disponible."
        )
        partes.append(
            f"Aplique {rg['lamina_bruta_mm']} mm "
            f"({rg['m3_por_hectarea']} m³ por hectárea). "
            f"Con su sistema de {rg['sistema'].lower()} y el caudal actual, "
            f"son unos {rg['minutos']:.0f} minutos ({rg['volumen_m3']} m³ en total)."
        )
        if rg.get("excede_jornada"):
            partes.append(
                f"⚠️ Con el caudal que tiene, eso son más de 4 horas seguidas. "
                f"Reparta el riego en {rg['dias_necesarios']} días, "
                f"unos {rg['minutos_por_dia']:.0f} minutos cada día."
            )
        elif rg["fraccionar_en_pasadas"]:
            partes.append(
                f"⚠️ Divida el riego en {rg['pasadas_sugeridas']} pasadas con "
                "descanso entre ellas. De un solo golpe, el suelo no alcanza a "
                "absorber y el agua se escurre."
            )
        if not rg.get("repone_en_un_riego", True):
            partes.append(
                f"La tierra viene con {rg['deficit_pendiente_mm']:.0f} mm de atraso "
                "que no se reponen de una. Se van recuperando en los próximos riegos."
            )

    elif d["accion"] == "esperar":
        partes.append(f"🟢 {saludo}hoy no riegue.")
        partes.append(d["razon"])
        if "ahorro_estimado_mm" in d:
            m3_ha = d["ahorro_estimado_mm"] * 10
            partes.append(f"Se ahorra aproximadamente {m3_ha:.0f} m³ por hectárea.")

    elif d["accion"] == "preparar":
        partes.append(f"🟡 {saludo}hoy todavía no, pero prepare el riego.")
        partes.append(d["razon"])

    else:
        partes.append(f"🟢 {saludo}el cultivo está bien de agua.")
        partes.append(
            f"Humedad al {es['pct_agua_disponible']}% de la disponible. {d['razon']}"
        )

    if cl["lluvia_proxima_7d_mm"] > 5:
        partes.append(
            f"🌧️ Pronóstico: {cl['lluvia_proxima_7d_mm']} mm de lluvia en los próximos 7 días."
        )

    if r.get("pastoreo"):
        p = r["pastoreo"]
        iconos = {"listo": "✅", "no_listo": "⛔", "sobremaduro": "⚠️",
                  "en_recuperacion": "🌱", "sin_datos": "ℹ️"}
        partes.append(f"\n{iconos.get(p['estado'], '')} Pastoreo: {p['mensaje']}")

    if r["proyeccion"]["percolacion_total_mm"] > 10:
        partes.append(
            f"\n💧 Atención: se proyectan {r['proyeccion']['percolacion_total_mm']} mm "
            "de agua percolando por debajo de la raíz. Ese es el agua que se está perdiendo."
        )

    texto = " ".join(partes)
    # Si no hay nombre del productor, la frase arranca en minúscula
    # ("🟢 el cultivo está bien"). Se corrige tras el emoji.
    for i, ch in enumerate(texto):
        if ch.isalpha():
            texto = texto[:i] + ch.upper() + texto[i + 1:]
            break
    return texto
