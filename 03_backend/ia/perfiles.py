"""
HidroSopó — Perfiles agronómicos
=================================
Aquí vive la adaptabilidad del sistema. Agregar un cultivo nuevo
es agregar un diccionario, no tocar el motor.

Coeficientes de cultivo (Kc) tomados de FAO-56 Tabla 12, ajustados
para condiciones de altiplano cundiboyacense.
"""

PERFILES = {

    # ========== PASTOREO (ganadería lechera de Sopó) ==========
    "kikuyo_pastoreo": {
        "nombre": "Kikuyo (Cenchrus clandestinus) — pastoreo rotacional",
        "modo": "pastoreo",
        "kc_inicial": 0.85, "kc_medio": 1.00, "kc_final": 0.90,
        "etapas_dias": None,
        "profundidad_raiz_m": 0.45,
        "mad": 0.55,
        "dias_descanso_optimo": 35,
        "dias_descanso_min": 28,
        "dias_descanso_max": 45,
        "altura_pastoreo_cm": 25,
        "altura_residual_cm": 8,
        "temp_base_gd": 10.0,       # temperatura base para grados-día
        "gd_acumulados_objetivo": 420,
        "notas": "Pasto dominante en la Sabana. Tolera pisoteo y baja fertilidad. "
                 "Responde fuerte al riego en verano.",
    },

    "raigras_pastoreo": {
        "nombre": "Raigrás perenne (Lolium perenne) — pastoreo",
        "modo": "pastoreo",
        "kc_inicial": 0.90, "kc_medio": 1.05, "kc_final": 0.95,
        "etapas_dias": None,
        "profundidad_raiz_m": 0.35,
        "mad": 0.50,
        "dias_descanso_optimo": 28,
        "dias_descanso_min": 21,
        "dias_descanso_max": 35,
        "altura_pastoreo_cm": 22,
        "altura_residual_cm": 6,
        "temp_base_gd": 5.0,
        "gd_acumulados_objetivo": 350,
        "notas": "Mayor calidad nutricional que kikuyo pero menos tolerante a sequía. "
                 "Raíz superficial: requiere riegos más frecuentes y ligeros.",
    },

    "pasto_corte": {
        "nombre": "Pasto de corte (avena forrajera / maralfalfa)",
        "modo": "pastoreo",
        "kc_inicial": 0.40, "kc_medio": 1.15, "kc_final": 0.85,
        "etapas_dias": [20, 30, 45, 25],
        "profundidad_raiz_m": 0.60,
        "mad": 0.55,
        "dias_descanso_optimo": 60,
        "dias_descanso_min": 45,
        "dias_descanso_max": 80,
        "altura_pastoreo_cm": 120,
        "altura_residual_cm": 15,
        "temp_base_gd": 8.0,
        "gd_acumulados_objetivo": 900,
        "notas": "Se corta y se lleva al comedero. Alta demanda hídrica en la fase de mayor crecimiento.",
    },

    # ========== CULTIVOS ==========
    "papa": {
        "nombre": "Papa (Solanum tuberosum)",
        "modo": "cultivo",
        "kc_inicial": 0.50, "kc_medio": 1.15, "kc_final": 0.75,
        "etapas_dias": [30, 35, 50, 30],   # ~145 días, variedad pastusa
        "profundidad_raiz_m": 0.50,
        "mad": 0.35,
        "sensible_estres": ["tuberizacion", "llenado"],
        "notas": "Muy sensible al déficit hídrico durante tuberización (días 45-95). "
                 "El exceso de agua favorece gota (Phytophthora). No sobre-regar.",
    },

    "hortalizas_hoja": {
        "nombre": "Hortalizas de hoja (lechuga, espinaca, acelga)",
        "modo": "cultivo",
        "kc_inicial": 0.70, "kc_medio": 1.00, "kc_final": 0.95,
        "etapas_dias": [20, 25, 25, 10],
        "profundidad_raiz_m": 0.25,
        "mad": 0.30,
        "notas": "Raíz muy superficial. Riegos frecuentes y ligeros. "
                 "El estrés hídrico provoca sabor amargo y espigado prematuro.",
    },

    "fresa": {
        "nombre": "Fresa (Fragaria x ananassa)",
        "modo": "cultivo",
        "kc_inicial": 0.40, "kc_medio": 0.85, "kc_final": 0.75,
        "etapas_dias": [30, 40, 90, 40],
        "profundidad_raiz_m": 0.25,
        "mad": 0.20,
        "notas": "MAD muy bajo: no tolera agotamiento. Ideal para goteo. "
                 "Cultivo de alto valor en Sopó y municipios vecinos.",
    },

    "mora": {
        "nombre": "Mora de Castilla (Rubus glaucus)",
        "modo": "cultivo",
        "kc_inicial": 0.50, "kc_medio": 0.95, "kc_final": 0.85,
        "etapas_dias": [60, 90, 120, 60],
        "profundidad_raiz_m": 0.60,
        "mad": 0.40,
        "notas": "Perenne. Exceso de humedad en el cuello favorece pudriciones.",
    },

    "maiz": {
        "nombre": "Maíz",
        "modo": "cultivo",
        "kc_inicial": 0.35, "kc_medio": 1.20, "kc_final": 0.60,
        "etapas_dias": [25, 40, 45, 30],
        "profundidad_raiz_m": 0.80,
        "mad": 0.50,
        "notas": "Crítico en floración. Un estrés de 3 días en floración cuesta 30% del rendimiento.",
    },

    "generico": {
        "nombre": "Cultivo genérico (usar solo si no hay perfil específico)",
        "modo": "cultivo",
        "kc_inicial": 0.50, "kc_medio": 1.00, "kc_final": 0.80,
        "etapas_dias": [25, 35, 45, 30],
        "profundidad_raiz_m": 0.40,
        "mad": 0.45,
        "notas": "Valores promedio. Reemplazar por un perfil real apenas se pueda.",
    },
}


# ========== TIPOS DE SUELO ==========
# Valores de referencia. SIEMPRE preferir la medición en campo
# (ver 01_hardware/CALIBRACION.md, Ruta A).

SUELOS = {
    "arenoso":          {"capacidad_campo_pct": 12, "punto_marchitez_pct": 5,  "densidad_aparente": 1.55, "infiltracion_mm_h": 50},
    "franco_arenoso":   {"capacidad_campo_pct": 20, "punto_marchitez_pct": 9,  "densidad_aparente": 1.45, "infiltracion_mm_h": 25},
    "franco":           {"capacidad_campo_pct": 28, "punto_marchitez_pct": 13, "densidad_aparente": 1.30, "infiltracion_mm_h": 13},
    "franco_arcilloso": {"capacidad_campo_pct": 34, "punto_marchitez_pct": 19, "densidad_aparente": 1.25, "infiltracion_mm_h": 8},
    "arcilloso":        {"capacidad_campo_pct": 40, "punto_marchitez_pct": 25, "densidad_aparente": 1.20, "infiltracion_mm_h": 4},
    # Los suelos de la Sabana de Bogotá suelen ser francos a franco-arcillosos
    # con alto contenido de materia orgánica y buena retención de humedad.
    "sabana_bogota":    {"capacidad_campo_pct": 32, "punto_marchitez_pct": 16, "densidad_aparente": 1.15, "infiltracion_mm_h": 10},
}


# ========== SISTEMAS DE RIEGO ==========

SISTEMAS_RIEGO = {
    "goteo":            {"eficiencia": 0.90, "nombre": "Goteo"},
    "microaspersion":   {"eficiencia": 0.85, "nombre": "Microaspersión"},
    "aspersion":        {"eficiencia": 0.75, "nombre": "Aspersión"},
    "manguera":         {"eficiencia": 0.60, "nombre": "Manguera manual"},
    "gravedad":         {"eficiencia": 0.50, "nombre": "Gravedad / surcos"},
    "inundacion":       {"eficiencia": 0.40, "nombre": "Inundación"},
}


def obtener_perfil(clave: str) -> dict:
    if clave not in PERFILES:
        raise ValueError(
            f"Perfil '{clave}' no existe. Disponibles: {', '.join(PERFILES)}"
        )
    return PERFILES[clave]


def obtener_suelo(clave: str) -> dict:
    if clave not in SUELOS:
        raise ValueError(f"Suelo '{clave}' no existe. Disponibles: {', '.join(SUELOS)}")
    return SUELOS[clave]


def listar_perfiles() -> list[dict]:
    return [
        {"clave": k, "nombre": v["nombre"], "modo": v["modo"]}
        for k, v in PERFILES.items()
    ]
