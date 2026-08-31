"""
HidroSopó — Agente conversacional
==================================
Convierte el sistema de una sola vía (sensores → recomendación) en una
conversación de dos vías: el productor le cuenta cosas y el sistema
aprende de lo que realmente hace.

CÓMO ESTÁ CONSTRUIDO Y POR QUÉ
------------------------------
Es un agente HÍBRIDO, no un chatbot con LLM al frente.

    mensaje del productor
            ↓
    [1] Analizador de intención   ← reglas + expresiones regulares
            ↓                        $0, funciona sin internet, es determinista
    [2] Acción sobre datos reales ← consulta la base, registra el riego,
            ↓                        calcula el ahorro
    [3] Respuesta                 ← plantilla, o LLM opcional solo para redactar
                                     NUNCA para inventar el número

Por qué no un LLM puro: en una finca de Sopó la señal se cae, y un
agente que depende de una API externa deja de servir justo cuando más
se necesita. Además, un LLM suelto alucina cifras de riego, y aquí una
cifra inventada le cuesta agua y plata al productor.

Regla de oro del diseño: **el LLM puede cambiar cómo suena la respuesta,
nunca de dónde sale el número.** Los datos siempre vienen del motor.
"""

from __future__ import annotations
import re
import unicodedata
from datetime import datetime, timedelta, date
from dataclasses import dataclass
from typing import Optional


# ============================================================
#  Normalización
# ============================================================

def normalizar(texto: str) -> str:
    """Quita tildes y baja a minúsculas.

    El productor escribe 'regue', no 'regué'. Y a veces 'REGUE'.
    Si no normalizamos, el agente falla en el caso más común.
    """
    t = texto.lower().strip()
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", t)


NUMEROS_PALABRA = {
    "un": 1, "una": 1, "uno": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
    "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10,
    "quince": 15, "veinte": 20, "treinta": 30, "cuarenta": 40,
    "media": 0.5, "medio": 0.5, "cuarto": 0.25,
}


def extraer_numero(texto: str) -> Optional[float]:
    """Saca la primera cantidad del mensaje, en dígitos o en palabra."""
    m = re.search(r"(\d+(?:[.,]\d+)?)", texto)
    if m:
        return float(m.group(1).replace(",", "."))
    for palabra, valor in NUMEROS_PALABRA.items():
        if re.search(rf"\b{palabra}\b", texto):
            return float(valor)
    return None


def extraer_minutos(texto: str) -> Optional[float]:
    """Convierte '40 minutos', 'hora y media', '2 horas' a minutos."""
    t = normalizar(texto)

    if re.search(r"\bhora y media\b", t):
        return 90.0
    if re.search(r"\bmedia hora\b", t):
        return 30.0

    # Horas en dígitos: "2 horas", "1.5 h"
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(h|hr|hrs|hora|horas)\b", t)
    if m:
        return float(m.group(1).replace(",", ".")) * 60

    # Horas en palabra: "una hora", "dos horas", "tres horas".
    # Sin esto, "prendí las dos bombas una hora" se leía como 1 minuto.
    m = re.search(r"\b(un|una|dos|tres|cuatro|cinco|seis|siete|ocho)\s+horas?\b", t)
    if m:
        return float(NUMEROS_PALABRA[m.group(1)]) * 60

    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(m|min|mins|minuto|minutos)\b", t)
    if m:
        return float(m.group(1).replace(",", "."))

    m = re.search(r"\b(un|una|dos|tres|cuatro|cinco|diez|quince|veinte|treinta)\s+minutos?\b", t)
    if m:
        return float(NUMEROS_PALABRA.get(m.group(1), 0)) or None

    # "regué 40" sin unidad: casi siempre son minutos
    if re.search(r"\b(regue|regué|riegue|puse|prendi|prendí|eche|eché)\b", t):
        n = extraer_numero(t)
        if n and 1 <= n <= 600:
            return float(n)
    return None


# ============================================================
#  Intenciones
# ============================================================

@dataclass
class Intencion:
    tipo: str
    datos: dict
    confianza: float


PATRONES = [
    # --- El productor reporta que regó ---
    ("registrar_riego", 0.95, [
        r"\b(regue|riegue|ya regue|acabo de regar|termine de regar)\b",
        r"\b(puse|prendi|encendi)\b.*\b(bomba|motor|manguera|aspersor)",
        r"\b(eche|echamos|le eche)\b.*\bagua\b",
        r"\bestuve regando\b",
        # Sin verbo: "media hora en el sector 1", "40 min en el potrero de arriba".
        # Es como habla la gente cuando ya está en la conversación.
        r"\b(media hora|\d+\s*(?:min|mins|minutos|h|horas?)|(?:un|una|dos|tres)\s+horas?)\b.*\b(sector|potrero|lote|turno|franja)\b",
        r"\b(sector|potrero|lote|turno|franja)\b.*\b(media hora|\d+\s*(?:min|mins|minutos|h|horas?))\b",
    ]),
    # --- Reporta que NO regó ---
    ("registrar_no_riego", 0.9, [
        r"\bno (pude|alcance a|logre|he podido)\b.*\breg(ar|ue|o)\b",
        r"\bno regue\b", r"\bno rego\b", r"\bno he regado\b",
        r"\bse me paso\b", r"\bno hubo riego\b", r"\bhoy no regu?e\b",
    ]),
    # --- Cuenta su rutina de riego ---
    ("registrar_rutina", 0.85, [
        r"\briego\b.*\b(cada|todos los|veces)\b",
        r"\b(siempre|normalmente|casi siempre)\b.*\briego\b",
        r"\b(dos|tres|una|1|2|3)\s*veces (al|por) (dia|semana)\b",
        r"\bcada (\d+|dos|tres|cuatro) dias\b",
    ]),
    # --- Pregunta por el ahorro ---
    ("consultar_ahorro", 0.95, [
        r"\bcuant[oa]s? (agua |)(me |)(he |)ahorr", r"\bahorro\b",
        r"\bcuanto llevo ahorrado\b", r"\bsirve\b.*\bahorrar\b",
        r"\bcuanta agua (he |)(gastado|usado|consumido)\b",
    ]),
    # --- Pregunta si debe regar ---
    ("consultar_riego", 0.9, [
        r"\b(riego|debo regar|toca regar|hay que regar|necesito regar)\b\s*(hoy|ahora|manana|\?|$)",
        r"\bpuedo (no |)regar\b", r"\bque hago (hoy|con el riego)\b",
        r"\bcomo (esta|va) (la tierra|el suelo|la humedad)\b",
        r"\bcuando (toca|debo|hay que) regar\b",
    ]),
    # --- Pregunta por el pastoreo ---
    ("consultar_pastoreo", 0.9, [
        r"\b(pastoreo|franja|potrero|meter|entrar)\b.*\b(animales|vacas|ganado|listo|cuando)\b",
        r"\bcuando (meto|entro|paso) (las |los |)(vacas|animales|ganado)\b",
        r"\bcomo (esta|va) (el |la |)(pasto|franja|potrero)\b",
    ]),
    # --- Pregunta por la lluvia ---
    ("consultar_lluvia", 0.85, [
        r"\b(va a |)llover\b", r"\blluvia\b", r"\bpronostico\b", r"\bel clima\b",
    ]),
    # --- Reporta un problema ---
    ("reportar_problema", 0.85, [
        r"\b(no funciona|esta danado|se dano|no sirve|no marca|no llega)\b",
        r"\b(se cayo|se movio|golpearon|tumbaron)\b.*\b(sensor|caja|equipo|panel)\b",
        r"\bhay un problema\b", r"\bfuga\b", r"\bse esta botando\b",
    ]),
    # --- No está de acuerdo con la recomendación ---
    ("discrepar", 0.8, [
        r"\bno (estoy de acuerdo|creo|me parece)\b",
        r"\b(la tierra|el suelo)\b.*\b(seca|seco|humeda|humedo)\b.*\b(pero|y)\b",
        r"\beso no (es|esta) (cierto|bien|correcto)\b",
        r"\byo veo\b.*\bdiferente\b",
    ]),
    # --- Medir el caudal de la bomba (casi nadie lo sabe) ---
    ("medir_caudal", 0.95, [
        r"\bmedir\b.*\b(caudal|bomba|cuanta agua)\b",
        r"\bcuanta agua (da|saca|bota|echa) (la |mi |)bomba\b",
        r"\bno se (cuanto|cuanta)\b.*\b(bomba|caudal)\b",
        r"\bcalibrar la bomba\b",
    ]),
    # --- Configurar sectores ---
    ("configurar_sectores", 0.9, [
        r"\b(tengo|son|hay)\b.*\b(\d+|dos|tres|cuatro|cinco|seis)\s*(sectores|potreros|turnos|llaves)\b",
        r"\b(configurar|registrar|agregar)\b.*\bsector\b",
        r"\bmis sectores\b",
    ]),
    # --- Saludo / ayuda ---
    ("saludo", 0.7, [
        r"^(hola|buenas|buenos dias|buenas tardes|que mas|hey|holi)\b",
    ]),
    ("ayuda", 0.9, [
        r"\b(ayuda|que puedo (preguntar|hacer)|como funciona|no entiendo|menu)\b",
    ]),
]


def entender(mensaje: str) -> Intencion:
    """Clasifica el mensaje. Es determinista: la misma frase da siempre lo mismo."""
    t = normalizar(mensaje)

    mejor = Intencion("desconocido", {}, 0.0)
    for tipo, conf, patrones in PATRONES:
        for p in patrones:
            if re.search(p, t):
                if conf > mejor.confianza:
                    mejor = Intencion(tipo, {}, conf)
                break

    # Enriquecer con los datos que trae el mensaje
    if mejor.tipo == "registrar_riego":
        mejor.datos["minutos"] = extraer_minutos(mensaje)

        # ¿Qué sector? "sector 2", "el potrero de arriba", "la franja 3"
        m = re.search(r"\b(?:sector|potrero|turno|franja|lote)\s*(\d+)\b", t)
        if m:
            mejor.datos["sector_num"] = int(m.group(1))
        else:
            m = re.search(r"\b(?:en|el|la)\s+((?:potrero|sector|lote)\s+\w+(?:\s+\w+)?)", t)
            if m:
                mejor.datos["sector_texto"] = m.group(1)

        # ¿Varias bombas al tiempo? Es lo normal en fincas con dos motores.
        if re.search(r"\b(las dos|ambas|dos bombas|2 bombas|todas las bombas|los dos motores)\b", t):
            mejor.datos["bombas_simultaneas"] = 2
        else:
            m = re.search(r"\b(\d+)\s*bombas\b", t)
            if m:
                mejor.datos["bombas_simultaneas"] = int(m.group(1))
        if re.search(r"\b(todo|todos los sectores|toda la finca|completo)\b", t):
            mejor.datos["todos_los_sectores"] = True
        if re.search(r"\b(ayer)\b", t):
            mejor.datos["cuando"] = "ayer"
        elif re.search(r"\b(anteayer|antier)\b", t):
            mejor.datos["cuando"] = "antier"
        else:
            mejor.datos["cuando"] = "hoy"

    if mejor.tipo == "registrar_rutina":
        mejor.datos["texto"] = mensaje.strip()
        n = extraer_numero(t)
        if re.search(r"veces (al|por) dia", t):
            mejor.datos["frecuencia"] = f"{int(n or 1)} vez/veces al día"
        elif re.search(r"cada \S+ dias", t):
            mejor.datos["frecuencia"] = f"cada {int(n or 2)} días"
        elif re.search(r"veces (a la|por) semana", t):
            mejor.datos["frecuencia"] = f"{int(n or 1)} vez/veces por semana"

    return mejor


# ============================================================
#  Respuestas
# ============================================================

def _mm_desde_minutos(minutos: float, caudal_lps: float, area_m2: float) -> float:
    """Convierte minutos de bombeo en lámina aplicada (mm)."""
    if area_m2 <= 0 or caudal_lps <= 0:
        return 0.0
    litros = caudal_lps * minutos * 60.0
    return litros / area_m2          # 1 L/m² = 1 mm


def _resolver_sectores(datos: dict, sectores: list) -> tuple[list, str]:
    """Decide sobre qué sectores se aplicó el riego y devuelve una descripción.

    Casos que hay que cubrir porque son los reales de una finca:
      - "regué 40 min"                  → el sector del turno, o el único que hay
      - "regué el sector 2, 40 min"     → ese sector
      - "prendí las dos bombas 1 hora"  → todos los sectores que alimentan cada bomba
      - "regué toda la finca"           → todos los sectores activos
    """
    activos = [x for x in sectores if getattr(x, "activo", True)]
    if not activos:
        return [], ""

    if datos.get("todos_los_sectores"):
        return activos, "toda la finca"

    if datos.get("sector_num"):
        n = datos["sector_num"]
        elegido = [x for x in activos if x.orden == n] or \
                  [x for x in activos if re.search(rf"\b{n}\b", x.nombre or "")]
        if elegido:
            return elegido[:1], elegido[0].nombre or f"sector {n}"

    if datos.get("sector_texto"):
        clave = normalizar(datos["sector_texto"])
        for x in activos:
            if clave in normalizar(x.nombre or ""):
                return [x], x.nombre

    nb = datos.get("bombas_simultaneas")
    if nb and nb > 1:
        # Un sector por cada bomba distinta, en orden de turno
        bombas, elegidos = [], []
        for x in sorted(activos, key=lambda z: z.orden or 99):
            b = x.bomba or f"bomba-{x.id}"
            if b not in bombas:
                bombas.append(b); elegidos.append(x)
            if len(elegidos) >= nb:
                break
        if len(elegidos) > 1:
            return elegidos, " y ".join(x.nombre or "sector" for x in elegidos)

    if len(activos) == 1:
        return activos, activos[0].nombre or "su sector"

    return [], "AMBIGUO"


def responder_registro_riego(minutos: Optional[float], predio, recomendacion: dict,
                             sectores: list | None = None, datos: dict | None = None) -> dict:
    """El caso más valioso: el productor cuenta que regó.

    El sistema no solo dice 'anotado': compara lo que aplicó contra lo que
    el cultivo necesitaba, y le devuelve algo útil.
    """
    datos = datos or {}
    sectores = sectores or []

    if minutos is None:
        return {
            "texto": "Anoto que regó. ¿Cuántos minutos dejó prendida la bomba? "
                     "Con ese dato le puedo decir si fue la cantidad justa.",
            "esperando": "minutos_riego",
            "accion": None,
        }

    elegidos, descripcion = _resolver_sectores(datos, sectores)

    # Varios sectores y el productor no dijo cuál: preguntar, no adivinar.
    if descripcion == "AMBIGUO":
        nombres = ", ".join(f"{x.orden}) {x.nombre}" for x in sectores if x.activo)
        return {
            "texto": f"Anoto los {minutos:.0f} minutos. ¿En cuál sector regó? "
                     f"Tengo registrados: {nombres}. "
                     "Dígame el número, o \"las dos bombas\" si regó en varios a la vez.",
            "esperando": "sector_riego",
            "accion": None,
            "datos": {"minutos": minutos},
        }

    # ---- Cálculo por sector ----
    if elegidos:
        detalle, m3_total, mm_prom = [], 0.0, 0.0
        for sx in elegidos:
            area_s = (sx.area_ha or 0) * 10000
            m3_s = (sx.caudal_lps or 0) * minutos * 60 / 1000.0
            mm_s = _mm_desde_minutos(minutos, sx.caudal_lps or 0, area_s)
            m3_total += m3_s
            mm_prom += mm_s
            detalle.append({"sector_id": sx.id, "nombre": sx.nombre,
                            "minutos": minutos, "volumen_m3": round(m3_s, 3),
                            "lamina_mm": round(mm_s, 2)})
        mm = mm_prom / len(elegidos)
        m3 = m3_total
    else:
        # Respaldo: predio de un solo sector sin configurar
        area = (getattr(predio, "area_por_turno_ha", None) or predio.area_regada_ha or 0) * 10000
        mm = _mm_desde_minutos(minutos, predio.caudal_disponible_lps or 0, area)
        m3 = (predio.caudal_disponible_lps or 0) * minutos * 60 / 1000.0
        detalle = []

    donde = f" en {descripcion}" if descripcion and descripcion != "AMBIGUO" else ""
    partes = [f"Anotado: {minutos:.0f} minutos de riego{donde}."]

    if len(elegidos) > 1:
        partes.append(
            f"Con {len(elegidos)} sectores abiertos al tiempo son {m3:.1f} m³ en total, "
            f"unos {mm:.1f} mm en cada uno."
        )
    elif mm > 0:
        partes.append(f"Eso son unos {mm:.1f} mm, o sea {m3:.1f} m³ de agua.")

    # Lo que le costó bombear esa agua: el dato que de verdad le importa
    try:
        import costos
        v = costos.valorizar(m3, predio)
        if v["cop"] > 0:
            trozos = []
            if v["cop_agua"] > 0:
                trozos.append(f"{costos.pesos(v['cop_agua'])} de agua")
            if v["cop_energia"] > 0:
                unidad = (f"{v['litros_diesel']:.1f} L de ACPM" if "litros_diesel" in v
                          else f"{v['kwh']:.1f} kWh")
                trozos.append(f"{costos.pesos(v['cop_energia'])} de energía ({unidad})")
            partes.append("Ese riego le costó " + " y ".join(trozos) + ".")
    except Exception:
        pass

    # Lo que importa no es la lámina (0.7 mm en 30 min es normal), sino la
    # TASA de aplicación: cuántos mm por hora entrega el sistema. Si es muy
    # baja, el sector está subequipado y regar bien toma jornadas enteras.
    tasa = (mm / (minutos / 60.0)) if minutos > 0 else 0
    if 0 < tasa < 2.0:
        horas_40mm = 40.0 / max(0.01, tasa)
        partes.append(
            f"Ojo con algo: ese sector aplica {tasa:.1f} mm por hora, que es poco. "
            f"Para reponer un riego completo necesitaría unas {horas_40mm:.0f} horas. "
            "Con más aspersores o más presión rendiría mucho mejor."
        )
    elif tasa > 25:
        partes.append(
            f"Ese sector aplica {tasa:.0f} mm por hora, que es mucho: el suelo no "
            "alcanza a absorber y el agua se escurre. Riegue por tiempos más cortos."
        )

    # Comparar contra lo que el suelo pedía
    rec = (recomendacion or {}).get("riego")
    agot = (recomendacion or {}).get("estado_suelo", {}).get("agotamiento_mm")

    if rec and rec.get("lamina_bruta_mm"):
        pedia = rec["lamina_bruta_mm"]
        if mm > pedia * 1.35:
            exceso = mm - pedia
            partes.append(
                f"El suelo pedía {pedia:.1f} mm. Aplicó {exceso:.1f} mm de más, "
                f"y esa agua se va por debajo de la raíz. La próxima vez, "
                f"con {pedia / max(0.01, mm) * minutos:.0f} minutos alcanza."
            )
        elif mm < pedia * 0.65:
            partes.append(
                f"El suelo pedía {pedia:.1f} mm y usted aplicó {mm:.1f}. "
                "Quedó corto: la humedad no va a llegar a la raíz profunda. "
                "Revise mañana cómo quedó."
            )
        else:
            partes.append("Es prácticamente lo que el suelo pedía. Buen riego.")
    elif agot is not None and agot < 5:
        partes.append(
            "Ojo: el suelo ya venía con buena humedad. Este riego probablemente "
            "no hacía falta. Mañana le muestro cómo quedó."
        )

    partes.append("Mañana vuelvo a medir y le cuento cómo respondió la tierra.")

    return {
        "texto": " ".join(partes),
        "accion": "registrar_riego",
        "datos": {"minutos": minutos, "volumen_m3": round(m3, 3),
                  "lamina_mm": round(mm, 2), "sectores": detalle},
    }


def responder_medir_caudal(paso: str | None, mensaje: str, predio) -> dict:
    """Casi ningún productor sabe cuántos litros por segundo da su bomba.

    Sin ese dato, todos los cálculos de lámina y de tiempo son adivinanzas.
    Este asistente lo mide con un balde y un cronómetro, que es lo que hay
    en cualquier finca.
    """
    if paso != "segundos_balde":
        return {"texto":
            "Vamos a medirlo, es fácil y toma dos minutos.\n\n"
            "1. Consiga un balde o caneca de la que sepa los litros "
            "(un balde de pintura suele ser de 20 litros).\n"
            "2. Prenda la bomba y deje que salga parejo.\n"
            "3. Meta la manguera al balde y tome el tiempo hasta llenarlo.\n\n"
            "Dígame cuántos segundos se demoró y de cuántos litros es el balde. "
            "Por ejemplo: \"20 litros en 8 segundos\".",
            "esperando": "segundos_balde", "accion": None}

    t = normalizar(mensaje)
    nums = [float(x.replace(",", ".")) for x in re.findall(r"(\d+(?:[.,]\d+)?)", t)]
    litros, segundos = None, None

    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(l|lt|lts|litro|litros)\b", t)
    if m:
        litros = float(m.group(1).replace(",", "."))
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(s|seg|segundo|segundos)\b", t)
    if m:
        segundos = float(m.group(1).replace(",", "."))

    if litros is None or segundos is None:
        if len(nums) >= 2:
            litros, segundos = nums[0], nums[1]
        elif len(nums) == 1:
            return {"texto": "Me falta un dato. ¿Cuántos litros es el balde y en "
                             "cuántos segundos se llenó? Por ejemplo: \"20 litros en 8 segundos\".",
                    "esperando": "segundos_balde", "accion": None}
        else:
            return {"texto": "No pillé los números. Escríbame algo como "
                             "\"20 litros en 8 segundos\".",
                    "esperando": "segundos_balde", "accion": None}

    if segundos <= 0 or litros <= 0:
        return {"texto": "Esos números no me cuadran. Intente otra vez: "
                         "\"20 litros en 8 segundos\".",
                "esperando": "segundos_balde", "accion": None}

    lps = litros / segundos
    lpm = lps * 60
    m3h = lps * 3.6

    juicio = ""
    if lps > 25:
        juicio = " Ese caudal es muy alto para una bomba de finca pequeña; revise la medida."
    elif lps < 0.15:
        juicio = " Ese caudal es muy bajo; puede que la bomba esté fallando o el filtro tapado."

    return {"texto":
        f"Su bomba da {lps:.2f} litros por segundo, o sea {lpm:.0f} litros por minuto "
        f"({m3h:.1f} m³ por hora).{juicio}\n\n"
        "Ya lo dejo registrado. Con este dato los tiempos de riego que le doy "
        "van a ser exactos y no aproximados.",
        "accion": "registrar_caudal", "datos": {"caudal_lps": round(lps, 3)}}


def responder_ahorro(ahorro: dict, predio=None) -> dict:
    """El productor pregunta cuánta agua ha ahorrado.

    Se responde en metros cúbicos Y en pesos. El m³ es para el informe;
    los pesos son los que hacen que el productor siga usando el sistema.
    """
    if not ahorro or ahorro.get("sin_datos"):
        return {"texto":
            "Todavía no le puedo dar ese número. Para saber cuánto se ahorró "
            "necesito comparar contra cómo regaba antes, y llevo poco tiempo "
            "midiendo. En unas semanas se lo tengo.", "accion": None}

    m3 = ahorro["ahorro_m3"]
    pct = ahorro["ahorro_pct"]
    dias = ahorro["dias"]

    if m3 <= 0:
        return {"texto":
            f"En estos {dias} días ha usado {ahorro['volumen_actual_m3']:.1f} m³, "
            f"un poco más que antes. No siempre se ahorra: si el clima estuvo más "
            f"seco, el cultivo pide más agua. Lo importante es que ahora sabe "
            f"exactamente cuánto usa.", "accion": None}

    tanques = m3 / 1.0     # 1 m³ = 1000 L = un tanque grande de finca
    partes = [
        f"En {dias} días ha ahorrado {m3:.1f} m³ de agua, un {pct:.0f}% menos que antes.",
        f"Son unos {tanques:.0f} tanques de mil litros.",
    ]

    if predio is not None:
        try:
            import costos
            v = costos.valorizar(m3, predio)

            # Se separan las dos cosas porque son plata de bolsillos distintos:
            # la del acueducto y la de la energía.
            if v["cop_agua"] > 0:
                partes.append(
                    f"En la factura del agua se ahorró {costos.pesos(v['cop_agua'])}.")

            if v["cop_energia"] > 0:
                if "litros_diesel" in v:
                    gal = v["litros_diesel"] / 3.785
                    medida = (f"{gal:.1f} galones" if gal >= 1
                              else f"{v['litros_diesel']:.1f} litros")
                    partes.append(
                        f"Y en ACPM se ahorró {costos.pesos(v['cop_energia'])}, "
                        f"unos {medida} que no quemó bombeando.")
                else:
                    partes.append(
                        f"Y en la factura de la luz se ahorró "
                        f"{costos.pesos(v['cop_energia'])}: son {v['kwh']:.0f} kWh "
                        "que no gastó bombeando.")

            if v["cop"] > 0:
                if v["cop_agua"] > 0 and v["cop_energia"] > 0:
                    partes.append(f"Entre las dos cosas, {costos.pesos(v['cop'])}.")
                anual = costos.proyectar_anual(m3, dias, predio)
                if anual.get("cop", 0) > 0:
                    partes.append(
                        f"A ese ritmo serían unos {costos.pesos(anual['cop'])} al año, "
                        "aunque en época de lluvias se riega menos y se ahorra menos.")
            elif not v["paga_agua"]:
                partes.append(
                    "En este predio el agua es suya y el riego es por gravedad, "
                    "así que el ahorro no se ve en ninguna factura. Pero es agua "
                    "que queda en la quebrada.")
        except Exception:
            pass

    partes.append(f"Usó {ahorro['volumen_actual_m3']:.1f} m³ contra los "
                  f"{ahorro['linea_base_m3']:.1f} m³ que gastaba antes.")
    return {"texto": " ".join(partes), "accion": None}


def responder_recomendacion(r: dict) -> dict:
    """El productor pregunta si debe regar. Se le devuelve el mensaje del motor."""
    return {"texto": r.get("mensaje", "No tengo lectura reciente de los sensores."),
            "accion": None}


def responder_pastoreo(r: dict) -> dict:
    p = (r or {}).get("pastoreo")
    if not p or p.get("estado") == "sin_datos":
        return {"texto":
            "Para eso necesito saber cuándo sacó los animales de esa franja. "
            "Dígame la fecha del último pastoreo y le llevo la cuenta.",
            "esperando": "fecha_pastoreo", "accion": None}

    partes = [p["mensaje"]]
    dias = p.get("dias_descanso_actual")
    rec_dias = p.get("dias_descanso_recomendado")
    if dias is not None and rec_dias is not None:
        partes.append(f"Lleva {dias} días de descanso y le convienen {rec_dias}.")
    if p.get("pct_recuperacion") is not None:
        partes.append(f"El pasto va en un {p['pct_recuperacion']}% de su recuperación.")

    if p["estado"] == "listo":
        partes.append(f"Cuando entre, deje {p['altura_residual_cm']} cm de residual: "
                      "si lo pela más, el rebrote se demora el doble.")
    elif p["estado"] == "sobremaduro":
        partes.append("Si se demora más, el pasto se encaña y pierde calidad nutricional.")
    elif p["estado"] == "no_listo":
        partes.append("Entrar antes de tiempo le gasta las reservas a la planta "
                      "y el siguiente rebrote sale más pobre.")
    if p.get("penalizacion_por_estres_dias"):
        partes.append("La falta de agua está frenando el rebrote; por eso se corrió la fecha.")
    return {"texto": " ".join(partes), "accion": None}


def responder_lluvia(r: dict) -> dict:
    c = (r or {}).get("clima", {})
    total = c.get("lluvia_proxima_7d_mm", 0)
    dias = c.get("lluvia_por_dia_mm", [])
    if total < 2:
        return {"texto": "No se espera lluvia importante en los próximos siete días. "
                         "Cuente con regar.", "accion": None}
    nombres = ["hoy", "mañana", "pasado mañana", "en 3 días", "en 4 días",
               "en 5 días", "en 6 días"]
    fuertes = [f"{nombres[i]} unos {v:.0f} mm" for i, v in enumerate(dias[:7]) if v >= 2]
    detalle = ", ".join(fuertes) if fuertes else "repartidos en varios días"
    return {"texto": f"Se esperan {total:.0f} mm en los próximos siete días: {detalle}. "
                     "Téngalo en cuenta antes de prender la bomba.", "accion": None}


def responder_rutina(datos: dict) -> dict:
    frec = datos.get("frecuencia")
    if frec:
        return {"texto":
            f"Listo, anoto que usted riega {frec}. Eso me sirve para comparar "
            "con lo que la tierra realmente necesita. Puede que en algunos días "
            "le sobre y en otros le falte: ahí es donde está el ahorro.",
            "accion": "registrar_rutina", "datos": datos}
    return {"texto":
        "Anotado. ¿Cada cuánto riega normalmente, y por cuántos minutos? "
        "Con eso puedo comparar su rutina contra lo que la tierra pide.",
        "esperando": "rutina", "accion": "registrar_rutina", "datos": datos}


def responder_discrepancia() -> dict:
    """El productor no está de acuerdo. Esto NO se descarta: se registra.

    Él conoce su finca. Si dice que la tierra está seca y el sensor dice
    lo contrario, lo más probable es que el sensor esté mal instalado o
    descalibrado. Su desacuerdo es un dato de diagnóstico.
    """
    return {"texto":
        "Gracias por decírmelo, eso es importante. Usted conoce su tierra mejor "
        "que el sensor. Voy a registrar su observación para revisarla. "
        "¿Qué está viendo usted en el terreno?",
        "accion": "registrar_discrepancia"}


def responder_problema(mensaje: str) -> dict:
    return {"texto":
        "Anotado el problema, ya queda reportado al técnico. No intente arreglarlo "
        "usted. Si algún equipo quedó suelto o expuesto, tápelo como pueda y "
        "avísenos por teléfono.",
        "accion": "alertar_tecnico", "datos": {"reporte": mensaje}}


def responder_sectores(sectores: list, mensaje: str) -> dict:
    activos = [x for x in sectores if getattr(x, "activo", True)]
    if activos:
        lista = "\n".join(
            f"· {x.orden}) {x.nombre}: {x.area_ha} ha, {x.caudal_lps} l/s"
            + (f", bomba {x.bomba}" if x.bomba else "")
            for x in sorted(activos, key=lambda z: z.orden or 99))
        return {"texto":
            f"Estos son los sectores que tengo registrados:\n\n{lista}\n\n"
            "Si alguno no está bien, o falta uno, dígamelo y lo corrijo con el técnico.",
            "accion": None}
    n = extraer_numero(normalizar(mensaje))
    return {"texto":
        (f"Anoto que tiene {int(n)} sectores. " if n else "")
        + "Todavía no los tengo registrados uno por uno. Para que los tiempos "
        "de riego le salgan exactos necesito de cada sector: cuántas hectáreas "
        "moja, cuánta agua le llega y con cuál bomba. El técnico se los registra "
        "en una visita. Mientras tanto le doy números aproximados.",
        "accion": "registrar_rutina"}


def responder_ayuda() -> dict:
    return {"texto":
        "Puede escribirme cosas como:\n\n"
        "· \"Regué 40 minutos\" — se lo anoto y le digo si fue lo justo\n"
        "· \"¿Riego hoy?\" — le doy la recomendación del día\n"
        "· \"¿Cuánta agua he ahorrado?\" — le muestro el acumulado\n"
        "· \"¿Va a llover?\" — le doy el pronóstico\n"
        "· \"¿Cuándo meto los animales?\" — le digo cómo va la franja\n"
        "· \"Regué el sector 2, 40 minutos\" — si tiene varios sectores\n"
        "· \"Prendí las dos bombas una hora\" — riego simultáneo\n"
        "· \"¿Cuánta agua da mi bomba?\" — la medimos con un balde\n"
        "· \"Se dañó un sensor\" — le aviso al técnico\n\n"
        "Y si no está de acuerdo con lo que le digo, dígamelo. Su criterio "
        "también cuenta.", "accion": None}


def responder_desconocido() -> dict:
    return {"texto":
        "No le entendí bien. Puede preguntarme si debe regar hoy, cuánta agua "
        "ha ahorrado, o contarme cuántos minutos regó. Escriba \"ayuda\" para "
        "ver todo lo que puedo hacer.", "accion": None}


# ============================================================
#  Cálculo del ahorro
# ============================================================

def calcular_ahorro(consumo_actual: list[dict], consumo_base: list[dict],
                    dias: int) -> dict:
    """Compara el consumo del período con la línea base.

    consumo_actual / consumo_base: [{"fecha": ..., "m3": ...}, ...]
    """
    if not consumo_base or not consumo_actual:
        return {"sin_datos": True}

    dias_base = max(1, len(consumo_base))
    dias_act = max(1, len(consumo_actual))

    prom_base = sum(d["m3"] for d in consumo_base) / dias_base
    total_actual = sum(d["m3"] for d in consumo_actual)
    esperado = prom_base * dias_act

    ahorro = esperado - total_actual
    pct = (100.0 * ahorro / esperado) if esperado > 0 else 0.0

    return {
        "dias": dias_act,
        "volumen_actual_m3": round(total_actual, 2),
        "linea_base_m3": round(esperado, 2),
        "promedio_diario_base_m3": round(prom_base, 3),
        "promedio_diario_actual_m3": round(total_actual / dias_act, 3),
        "ahorro_m3": round(ahorro, 2),
        "ahorro_pct": round(pct, 1),
        "ahorro_litros": round(ahorro * 1000, 0),
    }


# ============================================================
#  Punto de entrada del agente
# ============================================================

def conversar(mensaje: str, contexto: dict) -> dict:
    """Procesa un mensaje del productor y devuelve la respuesta.

    contexto espera:
        predio         — el objeto Predio
        recomendacion  — dict del motor (puede ser None)
        ahorro         — dict de calcular_ahorro (puede ser None)
        esperando      — qué se le preguntó antes (para respuestas cortas)
    """
    predio = contexto.get("predio")
    rec = contexto.get("recomendacion")
    esperando = contexto.get("esperando")
    sectores = contexto.get("sectores") or []
    pendiente = contexto.get("pendiente") or {}

    # ---- Continuaciones: si le pedimos un dato, ese dato manda ----
    # Sin esto, un "40" o un "sector 2" sueltos no significan nada.
    if esperando == "minutos_riego":
        mins = extraer_minutos(mensaje) or extraer_numero(normalizar(mensaje))
        if mins:
            r = responder_registro_riego(float(mins), predio, rec, sectores,
                                         entender(mensaje).datos)
            r["intencion"] = "registrar_riego"
            return r

    if esperando == "sector_riego":
        d = entender("regue " + mensaje).datos
        n = extraer_numero(normalizar(mensaje))
        if n and not d.get("sector_num"):
            d["sector_num"] = int(n)
        mins = pendiente.get("minutos") or extraer_minutos(mensaje)
        if mins:
            r = responder_registro_riego(float(mins), predio, rec, sectores, d)
            r["intencion"] = "registrar_riego"
            return r

    if esperando == "segundos_balde":
        r = responder_medir_caudal("segundos_balde", mensaje, predio)
        r["intencion"] = "medir_caudal"
        return r

    intencion = entender(mensaje)

    despacho = {
        "registrar_riego":   lambda: responder_registro_riego(
            intencion.datos.get("minutos"), predio, rec, sectores, intencion.datos),
        "registrar_no_riego": lambda: {"texto":
            "Anotado, no hubo riego. Si el suelo lo necesitaba, mañana se lo "
            "vuelvo a recordar.", "accion": "registrar_no_riego"},
        "registrar_rutina":  lambda: responder_rutina(intencion.datos),
        "consultar_ahorro":  lambda: responder_ahorro(contexto.get("ahorro"), predio),
        "medir_caudal":      lambda: responder_medir_caudal(None, mensaje, predio),
        "configurar_sectores": lambda: responder_sectores(sectores, mensaje),
        "consultar_riego":   lambda: responder_recomendacion(rec or {}),
        "consultar_pastoreo": lambda: responder_pastoreo(rec or {}),
        "consultar_lluvia":  lambda: responder_lluvia(rec or {}),
        "reportar_problema": lambda: responder_problema(mensaje),
        "discrepar":         lambda: responder_discrepancia(),
        "saludo":            lambda: {"texto":
            f"Buenas{', ' + predio.propietario.split()[0] if predio and predio.propietario else ''}. "
            + ((rec or {}).get("mensaje") or "Aún no tengo lectura de los sensores."),
            "accion": None},
        "ayuda":             lambda: responder_ayuda(),
    }

    salida = despacho.get(intencion.tipo, responder_desconocido)()
    salida["intencion"] = intencion.tipo
    salida["confianza"] = intencion.confianza
    return salida
