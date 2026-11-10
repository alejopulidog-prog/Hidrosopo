"""
Genera los informes de seguimiento FOES 2026-II de HidroSopó (python-docx).

    python generar_informes.py        → informes/*.docx

Criterio de redacción (el mismo de la bitácora): solo se reporta como hecho lo
que está hecho; lo simulado se rotula «gemelo digital / banco virtual»; lo que
el beneficiario debe completar con información real va resaltado en amarillo
entre corchetes [COMPLETAR: …] y debe llenarse o borrarse antes de enviar.
"""
from __future__ import annotations
import json
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = Path(__file__).resolve().parent / "informes"
BANCO = RAIZ / "06_datos" / "campana_banco"
R = json.loads((BANCO / "resumen.json").read_text(encoding="utf-8"))

TIERRA = RGBColor(0x2A, 0x21, 0x17)
AGUA = RGBColor(0x2E, 0x7E, 0xA6)
SIM = RGBColor(0x9A, 0x5A, 0x12)
GRIS = RGBColor(0x5B, 0x55, 0x4B)

BENEFICIARIO = "José Alejandro Pulido Gómez"
# La cédula no va en el código (el repositorio es público): se lee de un
# archivo local que está en .gitignore.
try:
    CC = json.loads((Path(__file__).resolve().parent / "datos_personales.json").read_text(encoding="utf-8"))["cc"]
except Exception:
    CC = "C.C. ______________"
PROYECTO = "Monitoreo Ambiental Inteligente y Uso Eficiente del Agua (HidroSopó)"
URL_PLATAFORMA = "https://claude.ai/artifact/ADUrD7srCq1N17nQWrasq9"   # usado solo en el avance 1 (enviado antes del despliegue)
URL_NETLIFY = "https://hidrosopo.netlify.app"


# ------------------------------------------------------------------ utilidades
def sombrear(celda, hex_color):
    tcPr = celda._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def documento(titulo_corto):
    d = Document()
    s = d.sections[0]
    s.page_width, s.page_height = Cm(21.59), Cm(27.94)
    s.left_margin = s.right_margin = Cm(2.2)
    s.top_margin, s.bottom_margin = Cm(2.0), Cm(1.8)
    st = d.styles["Normal"]; st.font.name = "Arial"; st.font.size = Pt(10.5)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), "Arial")
    st.paragraph_format.space_after = Pt(5); st.paragraph_format.line_spacing = 1.12
    for nivel, tam, color in [(1, 13.5, TIERRA), (2, 11.5, AGUA)]:
        h = d.styles[f"Heading {nivel}"]
        h.font.name = "Arial"; h.font.size = Pt(tam); h.font.bold = True; h.font.color.rgb = color
        h.element.rPr.rFonts.set(qn("w:asciiTheme"), "") if False else None
        rf = h.element.rPr.rFonts; rf.set(qn("w:ascii"), "Arial"); rf.set(qn("w:hAnsi"), "Arial")
        h.paragraph_format.space_before = Pt(12 if nivel == 1 else 8)
        h.paragraph_format.space_after = Pt(4); h.paragraph_format.keep_with_next = True
    enc = s.header.paragraphs[0]
    r = enc.add_run(f"HidroSopó · Incentivo FOES 2026-II · Secretaría de CTeI de Sopó · {titulo_corto}")
    r.font.size = Pt(8); r.font.color.rgb = GRIS
    pie = s.footer.paragraphs[0]; pie.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = pie.add_run(f"{BENEFICIARIO} · Ingeniería Mecatrónica, Universitaria Agustiniana")
    r.font.size = Pt(8); r.font.color.rgb = GRIS
    return d


def portada(d, titulo, subtitulo, filas):
    p = d.add_paragraph(); r = p.add_run(titulo); r.bold = True; r.font.size = Pt(18); r.font.color.rgb = TIERRA
    p.paragraph_format.space_after = Pt(2)
    p = d.add_paragraph(); r = p.add_run(subtitulo); r.font.size = Pt(11); r.font.color.rgb = AGUA
    tabla(d, ["Dato", "Detalle"], filas, [4.2, 12.9], encabezado=False)


def texto(d, *partes, estilo=None):
    """partes: str normal, ('b', str) negrita, ('i', str) cursiva, ('c', str) completar."""
    p = d.add_paragraph(style=estilo)
    for x in partes:
        if isinstance(x, str):
            p.add_run(x)
        else:
            k, t = x
            r = p.add_run(t)
            if k == "b": r.bold = True
            if k == "i": r.italic = True
            if k == "s": r.font.color.rgb = SIM; r.bold = True
            if k == "c": r.font.highlight_color = WD_COLOR_INDEX.YELLOW
    return p


def vineta(d, *partes):
    return texto(d, *partes, estilo="List Bullet")


def tabla(d, cab, filas, anchos_cm, encabezado=True, tam=9):
    t = d.add_table(rows=0, cols=len(anchos_cm))
    t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    todas = ([cab] if encabezado else []) + filas
    for i, fila in enumerate(todas):
        celdas = t.add_row().cells
        for j, v in enumerate(fila):
            c = celdas[j]; c.width = Cm(anchos_cm[j])
            p = c.paragraphs[0]; p.paragraph_format.space_after = Pt(1)
            completar = isinstance(v, tuple) and v[0] == "c"
            simulado = isinstance(v, tuple) and v[0] == "s"
            val = v[1] if isinstance(v, tuple) else str(v)
            r = p.add_run(val); r.font.size = Pt(tam)
            if completar: r.font.highlight_color = WD_COLOR_INDEX.YELLOW
            if simulado: r.font.color.rgb = SIM
            if encabezado and i == 0:
                r.bold = True; r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF); sombrear(c, "2A2117")
            elif not encabezado and j == 0:
                r.bold = True; sombrear(c, "EFF0EA")
    t.autofit = False
    for j, w in enumerate(anchos_cm):
        t.columns[j].width = Cm(w)
        for celda in t.columns[j].cells:
            celda.width = Cm(w)
    d.add_paragraph().paragraph_format.space_after = Pt(0)
    return t


def figura(d, archivo, pie, ancho_cm=14.5):
    d.add_picture(str(archivo), width=Cm(ancho_cm))
    d.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    p = d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(pie); r.italic = True; r.font.size = Pt(8.5); r.font.color.rgb = GRIS


def aviso_sim(d, txt):
    t = d.add_table(rows=1, cols=1); t.alignment = WD_TABLE_ALIGNMENT.CENTER
    c = t.rows[0].cells[0]; c.width = Cm(17.1); sombrear(c, "FBF0DD")
    r = c.paragraphs[0].add_run(txt); r.font.size = Pt(9); r.font.color.rgb = SIM; r.bold = True
    d.add_paragraph().paragraph_format.space_after = Pt(0)


def firma(d, fecha):
    d.add_paragraph()
    texto(d, "Firma del beneficiario: ______________________________        Fecha: ", fecha)
    texto(d, ("b", BENEFICIARIO), f" · {CC}")


def guardar(d, nombre):
    SALIDA.mkdir(exist_ok=True)
    d.save(SALIDA / nombre)
    print("✓", nombre)


# ------------------------------------------------------------------ cifras
cal = R["p1_calibracion"]["sensores"]
r2 = " · ".join(f"{v['r2']:.3f}".replace(".", ",") for v in cal.values())
wifi = R["p2_wifi"]; ene = R["p3_energia"]; cau = R["p4_caudal"]; ia = R["ia"]; aho = R["ahorro_temporada_seca"]
dk = ene["placas"]["ESP32 DevKit (la que se tiene)"]; bc = ene["placas"]["Placa de bajo consumo"]
c = lambda x: f"{x:.1f}".replace(".", ",")

FILAS_BANCO = [
    ["1. Calibración gravimétrica", "R² ≥ 0,90 por sensor", ("s", f"R² = {r2}"), "Cumple (simulado)"],
    ["2. Conexión WiFi (38 m, 72 h)", "≥ 95 % de envíos", ("s", f"{c(wifi['entrega_directa_pct'])} % directo → {c(wifi['entrega_final_pct'])} % con buffer"), "Cumple (simulado)"],
    ["3. Autonomía sin sol", "≥ 72 h y V ≥ 3,5 V", ("s", f"{c(dk['v_a_72h'])} V a 72 h; ≈ {dk['autonomia_dias_estimada']:.0f} días (DevKit)"), "Cumple (simulado)"],
    ["4. Caudalímetro vs. balde 20 L", "Error ≤ 5 %", ("s", f"{c(cau['error_medio_fabrica_pct'])} % de fábrica → {c(cau['error_max_corregido_pct'])} % máx. con K = {cau['k_corregido']:.0f}"), "Cumple (simulado)"],
    ["5. Pronóstico de humedad (IA)", "Mejor que la persistencia", ("s", f"−{ia['mejora_24h_pct']:.0f} % error a 24 h · −{ia['mejora_48h_pct']:.0f} % a 48 h"), "Cumple (simulado)"],
    ["6. Ahorro temporada seca", "Reportar mediana y rango", ("s", f"{c(aho['mediana_pct'])} % (P10–P90: {c(aho['p10_pct'])}–{c(aho['p90_pct'])} %), 50 climas"), "Referencia"],
]

REPROGRAMACION = [
    ["Compra de sensores, caudalímetro, pluviómetro, baterías y panel", "1 – 18 dic 2026"],
    ["Pruebas reales en banco con la ESP32 (WiFi, consumo, firmware)", "desde 12 nov 2026"],
    ["Diagnóstico formal del predio: ficha, fotos y consentimiento firmado", "12 – 16 ene 2027"],
    ["Calibración gravimétrica con suelo del predio", "12 – 22 ene 2027"],
    ["Instalación piloto y caudalímetro (inicio de la línea base)", "18 – 29 ene 2027"],
    ["Comparación pareada: sector con riego habitual vs. sector con HidroSopó (4 semanas)", "1 – 26 feb 2027"],
    ["Reentrenamiento del modelo con datos reales e informe complementario de campo", "hasta el 5 mar 2027"],
]


# ================================================================== AVANCE 1
def avance1():
    d = documento("Informe de avance 1")
    portada(d, "Informe de avance 1", "Actividades 5 y 6 del plan de trabajo: sensores y plataforma en la nube", [
        ["Beneficiario", f"{BENEFICIARIO} · {CC}"],
        ["Proyecto", PROYECTO],
        ["Periodo reportado", "28 de septiembre al 10 de noviembre de 2026"],
        ["Fecha programada / de envío", "5 de noviembre de 2026 / 10 de noviembre de 2026 (entrega tardía, ver sección 4)"],
        ["Plataforma", URL_PLATAFORMA],
    ])

    d.add_heading("1. Actividades del plan ejecutadas en el periodo", 1)
    tabla(d, ["N.º", "Actividad del plan", "Qué se hizo", "Estado"], [
        ["5", "Implementación de sensores: nodo de suelo y nodo de caudal, calibración, caudalímetro (línea base)",
         "Firmware del nodo de suelo y del nodo de caudal escrito (ESP32, envío WiFi/HTTPS, bajo consumo, buffer de 120 lecturas). "
         "Placa ESP32 adquirida. Los cinco protocolos de prueba se ejecutaron en banco virtual (gemelo digital) para fijar criterios y planillas.",
         "Parcial. Sensores, caudalímetro y energía por comprar; calibración y línea base reales reprogramadas"],
        ["6", "Plataforma en la nube y app del productor",
         "API de recepción, base de datos, indicadores PUEAA y reporte CSV. App instalable con «¿riego hoy?», corte del suelo, "
         "«¿qué pasa si no riego?» y asistente en español; funciona sin conexión. Nuevo laboratorio web con simulador de riego, "
         "pruebas en banco y estado del proyecto, publicado en enlace.",
         "Desarrollada y publicada. Opera con datos de prueba hasta instalar los sensores"],
        ["3", "Diagnóstico del predio piloto (pendiente del periodo anterior)",
         "Conversación inicial con el productor sobre el sistema de riego y la fuente de agua.",
         "Parcial. Falta ficha, registro fotográfico y consentimiento firmado"],
    ], [1.0, 4.2, 8.4, 3.5], tam=8.5)

    d.add_heading("2. Evidencias", 1)
    tabla(d, ["Actividad", "Evidencia", "Dónde"], [
        ["5 · Firmware", "Código del nodo de suelo y del nodo de caudal; configuración WiFi/LoRa", "Repositorio: 02_firmware/"],
        ["5 · Hardware", "Placa ESP32 adquirida", ("c", "[COMPLETAR: foto de la placa / factura, o borrar fila]")],
        ["5 · Pruebas", "Campaña en banco virtual: 6 gráficas, planillas CSV y resumen", "06_datos/campana_banco/ · Anexo A"],
        ["6 · Plataforma", "Laboratorio, app del productor y página de resultados", URL_PLATAFORMA],
        ["6 · Software", "102 pruebas automáticas aprobadas (85 anteriores + 17 nuevas: asistente y servidor)", "03_backend/tests/ · pytest"],
    ], [3.3, 8.0, 5.8], tam=8.5)

    d.add_heading("3. Resultados preliminares", 1)
    texto(d, ("b", "Medido en campo: "), "ninguno todavía. Por eso no se reportan curvas de calibración, línea base de consumo ni "
          "ahorro medido. Esos resultados dependen de la instalación, reprogramada como se explica en la sección 5.")
    texto(d, ("s", "Simulado (gemelo digital / banco virtual): "), "cada prueba del protocolo se reprodujo con un modelo físico del componente. "
          "Sirve para fijar qué se espera medir y para dejar listas las planillas; no reemplaza la medición.")
    tabla(d, ["Prueba", "Criterio", "Resultado simulado", "Estado"], FILAS_BANCO, [4.3, 3.4, 6.4, 3.0], tam=8.5)
    texto(d, ("b", "Hallazgo de diseño. "), f"La ESP32 DevKit que ya se tiene consume ≈ 8 mA en reposo por su regulador y su chip USB. "
          f"La autonomía sin sol baja a ≈ {dk['autonomia_dias_estimada']:.0f} días (frente a ≈ {bc['autonomia_dias_estimada']:.0f} con una placa de bajo consumo). "
          "Cumple el objetivo de diseño (≥ 8 días), y se verificará con una medición real de corriente en banco.")

    d.add_heading("4. Dificultades y cómo se están resolviendo", 1)
    tabla(d, ["Dificultad", "Efecto", "Mitigación"], [
        ["Situación familiar: accidente de mi pareja, que requirió mi acompañamiento", "Retraso en la compra de componentes, en el trabajo de campo y en este informe",
         "Se priorizó el trabajo que no depende del predio (software, IA, gemelo digital, póster) y se propone reprogramar la fase de campo (riesgo 1 de la matriz)"],
        ["Dificultades para conseguir y comprar los componentes", "Sin sensores ni caudalímetro no hay calibración ni línea base",
         "Compra consolidada en diciembre con alternos ya definidos en el BOM (riesgo 3: DHT22 por SHT31, otra placa ESP32)"],
        ["Poco tiempo de datos de campo antes del 26/11", "El ahorro no se puede medir en este semestre",
         "Comparación pareada de 4 semanas en febrero de 2027; resultados simulados y medidos se reportan por separado (riesgos 1, 2 y 8)"],
    ], [5.0, 4.6, 7.5], tam=8.5)

    d.add_heading("5. Actividades del siguiente periodo y reprogramación propuesta", 1)
    texto(d, "Hasta el 19 de noviembre (avance 2): módulo de IA y asistente (actividad 7) y pruebas reales en banco con la ESP32: "
          "intensidad de señal WiFi a distintas distancias y corriente en reposo. La instalación piloto (actividad 8) y las pruebas "
          "de campo (actividad 9) se proponen para el inicio de 2027, sujetas a aprobación de la Secretaría:")
    tabla(d, ["Actividad de campo", "Fecha propuesta"], REPROGRAMACION, [12.6, 4.5], tam=8.5)
    texto(d, "El 26 de noviembre se entregará el producto final previsto (póster 90 × 120 cm, informe técnico, plataforma y gemelo "
          "digital), con los resultados de campo en un informe complementario.")
    firma(d, "10 / 11 / 2026")

    d.add_page_break()
    d.add_heading("Anexo A. Campaña de pruebas en banco virtual (gemelo digital)", 1)
    aviso_sim(d, "SIMULACIÓN. Las siguientes gráficas salen de 06_datos/campana_banco_simulada.py (semilla 2026, reproducible). "
                 "No son mediciones de campo; cada una se repetirá con el hardware real.")
    for f, pie in [("p1_calibracion.png", "Figura A1. Calibración gravimétrica en banco virtual: ajuste cuadrático ADC → humedad volumétrica."),
                   ("p2_wifi.png", "Figura A2. Enlace WiFi a 38 m del router durante 72 h y reenvíos desde el buffer del nodo."),
                   ("p3_energia.png", "Figura A3. Descarga de la batería sin panel: ESP32 DevKit frente a placa de bajo consumo."),
                   ("p4_caudal.png", "Figura A4. Error del caudalímetro antes y después de corregir el factor de pulsos.")]:
        figura(d, BANCO / f, pie, 12.0)
    guardar(d, "Informe_Avance1_HidroSopo_JAPulido.docx")


# ================================================================== AVANCE 2
def avance2():
    d = documento("Informe de avance 2")
    portada(d, "Informe de avance 2", "Actividades 7 y 8 del plan de trabajo: módulo de IA e instalación piloto", [
        ["Beneficiario", f"{BENEFICIARIO} · {CC}"],
        ["Proyecto", PROYECTO],
        ["Periodo reportado", "11 al 19 de noviembre de 2026"],
        ["Fecha de entrega", "19 de noviembre de 2026"],
        ["Plataforma", URL_NETLIFY + "/laboratorio"],
    ])
    d.add_heading("1. Actividades del plan ejecutadas en el periodo", 1)
    tabla(d, ["N.º", "Actividad del plan", "Qué se hizo", "Estado"], [
        ["7", "Módulo de IA: balance hídrico FAO-56, aprendizaje automático (24 y 48 h) y asistente conversacional",
         "Motor FAO-56 (ETc = Kc × ET₀, agua fácilmente aprovechable, coeficiente de estrés) con pronóstico de Open-Meteo. "
         "Dos modelos Gradient Boosting que predicen la humedad a 24 y 48 h. Asistente en español ampliado: avisos de helada "
         "con la mínima pronosticada y conversión de la lámina a minutos de bomba. 102 pruebas automáticas aprobadas.",
         "Desarrollado con datos simulados; reentrenamiento con datos reales en la fase de campo"],
        ["8", "Instalación piloto en el predio y puesta en operación",
         "No ejecutada en el periodo. Se prepararon el protocolo, las planillas y el manual del productor.",
         "Reprogramada a enero de 2027 (ver avance 1)"],
        ["5", "Pruebas reales en banco con la ESP32", ("c", "[COMPLETAR con lo que se haga del 12 al 18/11: envío a la plataforma, RSSI a 5/10/20/30 m, corriente en reposo con multímetro. Si no se alcanza, borrar esta fila]"),
         ("c", "[COMPLETAR]")],
    ], [1.0, 4.2, 8.4, 3.5], tam=8.5)

    d.add_heading("2. Evidencias", 1)
    tabla(d, ["Actividad", "Evidencia", "Dónde"], [
        ["7 · Pruebas", "Pantallazo de pytest: 102 pruebas aprobadas", ("c", "[COMPLETAR: pegar pantallazo, ver Anexo]")],
        ["7 · Modelo", "Métricas de validación temporal de los modelos 24 h y 48 h", "03_backend/modelos/*_metricas.json · Figura 1"],
        ["7 · Recomendaciones", "Recomendación diaria y respuestas del asistente en la app (modo demostración)", URL_NETLIFY + " (app del productor)"],
        ["7 · Simulador", "Gemelo digital interactivo: calendario frente a HidroSopó con el mismo clima", URL_NETLIFY + "/laboratorio"],
        ["5 · Banco real", ("c", "[COMPLETAR: fotos del montaje y tabla de mediciones, o borrar fila]"), ("c", "[COMPLETAR]")],
    ], [3.3, 8.0, 5.8], tam=8.5)

    d.add_heading("3. Resultados preliminares", 1)
    aviso_sim(d, "Todas las métricas de esta sección son de SIMULACIÓN (gemelo digital, 90 días, 25.350 registros). "
                 "Las métricas con datos reales se reportarán tras la comparación pareada de febrero de 2027.")
    tabla(d, ["Indicador (simulado)", "HidroSopó", "Referencia", "Mejora"], [
        ["Error medio de humedad a 24 h (MAE, % vol)", c(ia["mae_24h"]).replace(",0", ",") if False else f"{ia['mae_24h']:.2f}".replace(".", ","),
         f"{ia['persistencia_24h']:.2f}".replace(".", ",") + " («mañana igual que hoy»)", f"{ia['mejora_24h_pct']:.0f} %"],
        ["Error medio de humedad a 48 h (MAE, % vol)", f"{ia['mae_48h']:.2f}".replace(".", ","),
         f"{ia['persistencia_48h']:.2f}".replace(".", ","), f"{ia['mejora_48h_pct']:.0f} %"],
        ["Agua aplicada, temporada seca, 1 ha, 90 días (caso representativo)", "2.386 m³ · 6 riegos", "3.680 m³ · 23 riegos por calendario", "35 %"],
        ["Ahorro en 50 climas distintos (temporada seca)", f"mediana {c(aho['mediana_pct'])} %", f"P10–P90: {c(aho['p10_pct'])}–{c(aho['p90_pct'])} %", "—"],
    ], [6.6, 3.4, 4.8, 2.3], tam=8.5)
    figura(d, BANCO / "p5_modelo_ia.png", "Figura 1. Error del pronóstico de humedad frente a la persistencia (validación temporal por bloques, datos simulados).", 11.5)
    texto(d, ("b", "Ejemplo de recomendación generada (modo demostración): "), ("i",
          "«Hoy no riegue. La tierra llegó al punto de regar, pero se esperan 18 mm de lluvia en dos días. Regar hoy sería botar el agua.»"))
    texto(d, ("b", "Cómo decide: "), "el motor FAO-56 calcula cuánta agua le queda al suelo; si bajó del umbral y el pronóstico de 24 h "
          "trae menos de 5 mm, recomienda regar y traduce la lámina a minutos de bomba. El modelo de aprendizaje automático ajusta la "
          "proyección. El sistema solo recomienda: la decisión es del productor.")

    d.add_heading("4. Dificultades y cómo se resolvieron", 1)
    tabla(d, ["Dificultad", "Mitigación"], [
        ["El modelo no se puede validar con datos reales este semestre", "Validación temporal por bloques con el gemelo digital; reentrenamiento automático (ia/modelo_ml.py) cuando haya 4 semanas de datos del predio"],
        ["Instalación piloto no realizada (situación familiar y compras)", "Reprogramación a enero de 2027 con comparación pareada de 4 semanas (riesgos 1, 2 y 3)"],
    ], [6.5, 10.6], tam=8.5)

    d.add_heading("5. Actividades del siguiente periodo", 1)
    vineta(d, "Hasta el 26/11: póster 90 × 120 cm impreso, informe técnico final y entrega en la Secretaría (actividad 10).")
    vineta(d, "Diciembre 2026 – marzo 2027: compras, instalación, calibración, línea base y comparación pareada (actividades 5, 8 y 9), según el cronograma propuesto en el avance 1.")
    firma(d, "19 / 11 / 2026")
    d.add_page_break()
    d.add_heading("Anexo. Pantallazo de las pruebas automáticas", 1)
    texto(d, ("c", "[COMPLETAR: en la carpeta 03_backend ejecutar «pytest» y pegar aquí el pantallazo con «102 passed»]"))
    guardar(d, "Informe_Avance2_HidroSopo_JAPulido.docx")


# ================================================================== INFORME FINAL
def informe_final():
    d = documento("Informe técnico final")
    portada(d, "Informe técnico final", "Sistema inteligente de monitoreo ambiental y optimización del uso del agua mediante IoT e IA para el municipio de Sopó", [
        ["Beneficiario", f"{BENEFICIARIO} · {CC}"],
        ["Programa", "Ingeniería Mecatrónica, sexto semestre · Universitaria Agustiniana"],
        ["Convocatoria", "Incentivo FOES 2026-II · Secretaría de Ciencia, Tecnología e Innovación de Sopó (COMUC+CTeI)"],
        ["Fecha", "26 de noviembre de 2026"],
        ["Plataforma y repositorio", URL_NETLIFY + "/laboratorio" + " · " ],
    ])
    t = d.tables[-1]; cel = t.rows[4].cells[1].paragraphs[0]
    r = cel.add_run("[COMPLETAR: enlace al repositorio en GitHub]"); r.font.size = Pt(9); r.font.highlight_color = WD_COLOR_INDEX.YELLOW

    d.add_heading("Resumen", 1)
    texto(d, "En la Sabana de Bogotá la mayoría de predios pequeños riega por calendario, sin saber cuánta agua tiene el suelo. "
          "HidroSopó es un prototipo de bajo costo que mide la humedad del suelo a 15, 30 y 45 cm, consulta el pronóstico del tiempo "
          "y, con el balance hídrico FAO-56 y un modelo de aprendizaje automático, le dice al productor si debe regar hoy y por "
          "cuántos minutos. En este semestre se diseñó el hardware (≈ $1,1 M por predio con WiFi), se desarrollaron el firmware, la "
          "plataforma en la nube, la aplicación del productor, el módulo de IA y un gemelo digital del predio. ")
    texto(d, ("s", "En simulación "), f"el modelo reduce el error del pronóstico de humedad en {ia['mejora_24h_pct']:.0f} % (24 h) frente a la "
          f"persistencia, y el riego guiado ahorra una mediana de {c(aho['mediana_pct'])} % de agua en temporada seca (P10–P90: "
          f"{c(aho['p10_pct'])}–{c(aho['p90_pct'])} %, 50 climas). La instalación en el predio piloto y la medición del ahorro real con "
          "caudalímetro se reprogramaron para enero y febrero de 2027.")

    d.add_heading("1. Problema y objetivo", 1)
    texto(d, "La Ley 373 de 1997 obliga a los municipios a tener un Programa de Uso Eficiente y Ahorro del Agua (PUEAA), pero en "
          "los predios rurales no hay datos de cuánta agua se usa ni de si se usa bien. El objetivo general fue diseñar y construir "
          "un prototipo funcional basado en IoT e IA para el monitoreo ambiental y la optimización del uso del agua en un predio "
          "agrícola piloto de Sopó.")
    tabla(d, ["Objetivo específico", "Estado al 26/11/2026"], [
        ["1. Diagnosticar las necesidades de monitoreo y riego del predio piloto", "Parcial: conversación inicial; ficha y consentimiento en enero de 2027"],
        ["2. Diseñar e implementar el nodo de sensores ESP32", "Diseño completo (esquema, BOM, energía, CAD) y firmware; montaje con sensores en enero de 2027"],
        ["3. Desarrollar la plataforma digital de visualización", "Cumplido: API, base de datos, PUEAA, app instalable y laboratorio publicados"],
        ["4. Incorporar un módulo de IA que recomiende el riego", "Cumplido con datos simulados: FAO-56 + modelos 24/48 h + asistente"],
        ["5. Instalar y probar el prototipo en campo", "Reprogramado: comparación pareada de 4 semanas en febrero de 2027"],
    ], [8.5, 8.6], tam=8.5)

    d.add_heading("2. Arquitectura y diseño", 1)
    tabla(d, ["Capa", "Componentes", "Función"], [
        ["Captura", "ESP32 + 3 sensores capacitivos (15/30/45 cm), DS18B20, SHT31 o DHT22, pluviómetro de balancín, caudalímetro de pulsos; 2 × 18650 y panel de 10 W; caja IP65 impresa en 3D", "Medir el agua disponible y el agua captada (línea base)"],
        ["Comunicación", "WiFi directo por HTTPS; buffer de 120 lecturas; LoRa 915 MHz como opción", "Hardware ≈ 36 % más barato que con pasarela"],
        ["Nube", "FastAPI, PostgreSQL, Open-Meteo; servicios gratuitos", "Guardar lecturas, calcular indicadores PUEAA"],
        ["IA", "FAO-56 (ETc = Kc × ET₀) + Gradient Boosting 24/48 h + asistente híbrido (reglas, sin LLM obligatorio)", "Recomendar si regar y cuánto; nunca inventa cifras"],
        ["Usuario", "App web instalable, sin conexión; reporte CSV para el municipio", "El productor decide desde el celular"],
    ], [2.6, 8.8, 5.7], tam=8.5)

    d.add_heading("3. Metodología de validación", 1)
    texto(d, "La validación se planteó en dos etapas. (a) ", ("b", "Banco virtual y gemelo digital"), ": cada componente se modeló con su "
          "física (respuesta del sensor capacitivo, pérdida de trayecto WiFi, descarga Li-ion, factor de pulsos del caudalímetro) y el "
          "predio con un balance hídrico diario de 90 días; el ahorro se estimó comparando, con el mismo clima, riego por calendario "
          "(12 mm cada 3 días salvo lluvia) frente a riego guiado. (b) ", ("b", "Campo"), ": los mismos cinco protocolos con el hardware real "
          "(09_entregables/PROTOCOLO_PRUEBAS.md) y una comparación pareada entre dos sectores del predio durante 4 semanas.")

    d.add_heading("4. Resultados", 1)
    aviso_sim(d, "Los resultados de esta sección son de SIMULACIÓN (gemelo digital / banco virtual). El ahorro oficial del proyecto será "
                 "el medido con el caudalímetro en el predio piloto (informe complementario, marzo de 2027).")
    tabla(d, ["Prueba", "Criterio", "Resultado simulado", "Estado"], FILAS_BANCO, [4.3, 3.4, 6.4, 3.0], tam=8.5)
    figura(d, BANCO / "p1_calibracion.png", "Figura 1. Calibración gravimétrica en banco virtual.", 11.0)
    figura(d, BANCO / "p2b_alcance_wifi.png", "Figura 2. Envíos WiFi exitosos según la distancia al router: define la regla de instalación (≲ 50 m con buffer).", 11.0)
    figura(d, BANCO / "p3_energia.png", "Figura 3. Autonomía sin sol: la placa DevKit domina el consumo en reposo.", 11.0)
    figura(d, BANCO / "p4_caudal.png", "Figura 4. Corrección del factor de pulsos del caudalímetro.", 11.0)
    figura(d, BANCO / "p5_modelo_ia.png", "Figura 5. Pronóstico de humedad: modelo frente a persistencia.", 11.0)

    d.add_heading("5. Discusión y limitaciones", 1)
    vineta(d, ("b", "Lo simulado no es lo medido. "), "Los modelos de los componentes usan valores típicos de fabricante y literatura; el suelo, "
           "el router y el caudalímetro reales pueden comportarse distinto. Por eso los criterios de aceptación se mantienen y se repiten en campo.")
    vineta(d, ("b", "El ahorro depende de la temporada. "), "En lluvias el ahorro simulado es mayor porque el riego por calendario sigue regando "
           "sobre suelo húmedo; en temporada seca es más moderado y es el dato más representativo.")
    vineta(d, ("b", "Días bajo el umbral. "), "El riego guiado aplica menos agua y tolera algunos días cerca del umbral de estrés; en campo se "
           "vigilará con el productor que eso no afecte el pasto.")
    vineta(d, ("b", "Hallazgo de hardware. "), f"La ESP32 DevKit gasta ≈ {dk['consumo_mah_dia']:.0f} mAh/día; una placa de bajo consumo, "
           f"≈ {bc['consumo_mah_dia']:.0f} mAh/día. Para escalar a más predios conviene la segunda.")

    d.add_heading("6. Recomendaciones", 1)
    vineta(d, "Instalar el caudalímetro antes que cualquier otro sensor: sin línea base no hay ahorro demostrable.")
    vineta(d, "Ubicar el nodo a menos de 50 m del router o con repetidor; si no, activar LoRa (ya soportado en el firmware).")
    vineta(d, "Calibrar cada sensor con suelo del propio predio y repetir la calibración al año.")
    vineta(d, "Para el municipio: usar el reporte CSV como insumo del PUEAA (consumo, lámina aplicada, eficiencia).")

    d.add_heading("7. Apropiación social: Sopó Cuida el Agua", 1)
    texto(d, "Para que el conocimiento del proyecto no se quede en un predio, se desarrolló el componente «Sopó Cuida el Agua», "
          "dirigido a huertas caseras, campesinos y ferias, hogares y colegios, y articulado con el PUEAA (Ley 373 de 1997, "
          "artículo 12: campañas educativas y de concientización). Materiales listos:")
    for t_ in ["Página web con calculadora de riego por cultivo (FAO-56), calculadora de agua lluvia, reto del hogar, quiz escolar y vista de indicadores para Emsersopó.",
               "Plegable tríptico con QR para ferias, mercados campesinos y colegios.",
               "Taller escolar «El suelo habla» de 2 sesiones, articulado al PRAE (Decreto 1743 de 1994), con encuesta antes y después.",
               "Carta de intención a Emsersopó para una mesa técnica sobre indicadores rurales y campañas."]:
        vineta(d, t_)
    texto(d, ("b", "Resultados de apropiación al 26/11/2026: "), ("c", "[COMPLETAR con lo realizado: actividad, lugar, fecha, número de personas, resultados de la encuesta. Si no se alcanzó, escribir: «Programado para diciembre de 2026 y febrero de 2027, ver Estrategia Sopó Cuida el Agua»]"))
    texto(d, ("b", "Mejora futura: "), "convertir la línea escolar en la app «Guardianes del Agua» (retos por curso, registro del contador de la casa y huerta escolar monitoreada) y en una red escolar de datos para el PUEAA.")

    d.add_heading("8. Plan de la fase de campo (2027)", 1)
    tabla(d, ["Actividad", "Fecha propuesta"], REPROGRAMACION, [12.6, 4.5], tam=8.5)

    d.add_heading("9. Conclusiones", 1)
    texto(d, "El sistema completo —firmware, plataforma, app, IA y gemelo digital— está desarrollado, probado con 102 pruebas "
          "automáticas y publicado. En simulación cumple los cinco criterios de aceptación y muestra un ahorro de agua relevante. "
          "La contribución que falta, y la más importante, es medir ese ahorro en el predio piloto; para eso quedan listos el "
          "protocolo, las planillas, el cronograma y el compromiso del beneficiario de completarlo al inicio de 2027. El componente "
          "«Sopó Cuida el Agua» extiende el proyecto a huertas, ferias, hogares y colegios, y le da al PUEAA herramientas para sus campañas.")

    d.add_heading("Referencias", 1)
    for ref in [
        "Allen, R. G., Pereira, L. S., Raes, D. y Smith, M. (1998). Crop evapotranspiration: Guidelines for computing crop water requirements. FAO Irrigation and Drainage Paper 56. FAO.",
        "Congreso de Colombia (1997). Ley 373 de 1997, por la cual se establece el programa para el uso eficiente y ahorro del agua.",
        "Open-Meteo (2026). Weather Forecast API. https://open-meteo.com",
        "Pedregosa, F. et al. (2011). Scikit-learn: Machine Learning in Python. Journal of Machine Learning Research, 12, 2825–2830.",
    ]:
        p = texto(d, ref); p.paragraph_format.left_indent = Cm(0.8); p.paragraph_format.first_line_indent = Cm(-0.8)
        for r_ in p.runs: r_.font.size = Pt(9)
    firma(d, "26 / 11 / 2026")
    guardar(d, "Informe_Tecnico_Final_HidroSopo_JAPulido.docx")


# ================================================================== APROPIACIÓN SOCIAL
URL_COMUNIDAD = URL_NETLIFY + "/agua"


def apropiacion():
    d = documento("Apropiación social del conocimiento")
    portada(d, "Sopó Cuida el Agua", "Componente de apropiación social del conocimiento del proyecto HidroSopó: educación, campañas y articulación con el PUEAA y Emsersopó", [
        ["Beneficiario", f"{BENEFICIARIO} · {CC}"],
        ["Proyecto", PROYECTO],
        ["Públicos", "Colegios (PRAE), huertas caseras y familias, campesinos y ferias, Emsersopó y Alcaldía"],
        ["Fecha", "10 de noviembre de 2026 · versión 1"],
        ["Herramientas en línea", URL_COMUNIDAD],
    ])

    d.add_heading("1. Por qué este componente", 1)
    texto(d, "HidroSopó nació para medir y recomendar el riego en un predio. Pero el uso eficiente del agua en Sopó no depende solo "
          "de los potreros: también de las huertas caseras, de los campesinos que venden en ferias y mercados, de los hogares y de "
          "los colegios, donde se forman los hábitos. Este componente lleva el mismo conocimiento del proyecto —cuánta agua necesita "
          "de verdad una planta, cuándo regar, cómo medir— a esos públicos, con herramientas que no necesitan sensores.")
    texto(d, ("b", "Encaje normativo. "), "La Ley 373 de 1997 crea el Programa de Uso Eficiente y Ahorro del Agua (PUEAA) y, en su "
          "artículo 12, establece que las entidades usuarias deben incluir en su presupuesto los costos de las campañas educativas y "
          "de concientización a la comunidad para el uso racionalizado y eficiente del recurso hídrico. El Decreto 1743 de 1994 "
          "institucionaliza los Proyectos Ambientales Escolares (PRAE) en los colegios. Este componente ofrece a Emsersopó y a los "
          "colegios material listo para cumplir esas dos tareas.")

    d.add_heading("2. Objetivos", 1)
    texto(d, ("b", "General: "), "promover el uso eficiente del agua en Sopó mediante herramientas digitales, materiales y talleres "
          "basados en el método FAO-56 y en los resultados del proyecto HidroSopó, articulados con el PUEAA municipal.")
    for o in ["Dar a familias y campesinos una forma sencilla de saber cuánta agua necesita su huerta y cuánta lluvia pueden recoger.",
              "Llevar a los colegios un taller práctico de ciencia, tecnología y agua, articulado al PRAE.",
              "Medir el cambio en conocimientos y prácticas con una encuesta antes y después.",
              "Proponer a Emsersopó un formato de indicadores rurales y de campañas como insumo para el PUEAA."]:
        vineta(d, o)

    d.add_heading("3. Líneas de acción", 1)
    tabla(d, ["Línea", "Público", "Qué se hace", "Material", "Indicador"], [
        ["1. Escuela del agua", "Estudiantes de 6.º a 11.º y docentes", "Taller «El suelo habla» de 2 sesiones: experimento de retención de agua y demostración con la placa ESP32 y un sensor de humedad", "Guía docente (Anexo A), quiz en línea, kit didáctico", "Talleres, estudiantes, mejora en la encuesta"],
        ["2. Mi huerta", "Huertas caseras y familias", "Calculadora de riego por cultivo, calculadora de agua lluvia y reto del hogar", "Página «Sopó Cuida el Agua», plegable", "Plegables entregados, compromisos firmados"],
        ["3. Feria y mercado", "Campesinos y visitantes", "Stand con demostración de la app y del sensor, cálculo en vivo para cada huerta e inscripción voluntaria de predios para la red piloto", "Plegable con QR, encuesta corta, planilla de asistencia", "Personas atendidas, predios inscritos"],
        ["4. PUEAA", "Emsersopó y Alcaldía", "Mesa técnica para revisar el formato de indicadores rurales y el apoyo a las campañas del artículo 12", "Carta de intención (Anexo C), reporte de ejemplo", "Reunión realizada, acuerdo de trabajo"],
        ["5. Comunicación", "Comunidad en general", "Piezas cortas para redes y canales de la Alcaldía con los datos del plegable", "Textos y gráficas del plegable", "Publicaciones, alcance"],
    ], [2.6, 2.8, 5.4, 3.4, 2.9], tam=8)

    d.add_heading("4. Materiales listos", 1)
    tabla(d, ["Material", "Estado", "Dónde"], [
        ["Página «Sopó Cuida el Agua»: Mi huerta, Agua lluvia, Reto del hogar, Escuela del agua (quiz de 8 preguntas y experimento), PUEAA", "Publicada", URL_COMUNIDAD],
        ["Plegable tríptico carta para ferias, colegios y huertas, con QR", "Listo para imprimir", "09_entregables/plegable/"],
        ["Guía docente del taller «El suelo habla»", "Lista", "Anexo A"],
        ["Encuesta antes y después", "Lista", "Anexo B"],
        ["Carta de intención a Emsersopó", "Lista para firmar", "Anexo C"],
        ["Planilla de asistencia", "Lista", "Anexo D"],
    ], [9.2, 3.0, 4.9], tam=8.5)

    d.add_heading("5. Cronograma propuesto", 1)
    tabla(d, ["Actividad", "Fecha"], [
        ["Primera actividad piloto: un stand en feria o mercado campesino, o un taller en un colegio", ("c", "[COMPLETAR: fecha y lugar si se alcanza antes del 26/11/2026; si no, borrar fila]")],
        ["Radicación de la carta de intención y solicitud de reunión con Emsersopó", "16 – 27 nov 2026"],
        ["Impresión de plegables y stand en ferias y mercados de diciembre", "dic 2026"],
        ["Talleres «El suelo habla» en colegios (inicio del calendario escolar)", "feb 2027"],
        ["Encuestas, consolidación de indicadores e informe de apropiación (con el informe complementario de campo)", "hasta el 5 mar 2027"],
    ], [12.1, 5.0], tam=8.5)

    d.add_heading("6. Cómo se mide", 1)
    texto(d, "Estos indicadores son medibles y se reportarán con evidencia (planillas, fotos, encuestas):")
    tabla(d, ["Indicador", "Cómo se mide", "Meta propuesta"], [
        ["Personas alcanzadas", "Planillas de asistencia (Anexo D)", "≥ 150"],
        ["Talleres en colegios", "Registro fotográfico y planilla", "≥ 2 colegios"],
        ["Mejora de conocimientos", "Encuesta antes y después (Anexo B): % de respuestas correctas", "+ 25 puntos porcentuales"],
        ["Compromisos de ahorro", "Desprendibles «Yo me comprometo» firmados", "≥ 50"],
        ["Predios interesados en la red", "Inscripción voluntaria en el stand", "≥ 5"],
        ["Articulación con el PUEAA", "Acta de reunión con Emsersopó", "1 reunión"],
    ], [5.0, 8.0, 4.1], tam=8.5)
    texto(d, ("i", "Las metas son propuestas. Se reportará lo que efectivamente se logre."))

    d.add_heading("7. Recursos", 1)
    tabla(d, ["Recurso", "Costo aproximado"], [
        ["Herramientas en línea (página, calculadoras, quiz)", "$0"],
        ["Kit didáctico: placa ESP32 (ya adquirida), sensor capacitivo de humedad, cables y botellas recicladas", "≈ $40.000"],
        ["Impresión de 200 plegables a color, doble cara", ("c", "[COMPLETAR: cotización local]")],
        ["Fotocopias de encuestas y planillas", "≈ $20.000"],
    ], [12.1, 5.0], tam=8.5)

    d.add_heading("8. Mejoras futuras: app educativa para colegios", 1)
    texto(d, "La página «Sopó Cuida el Agua» es la primera versión. La propuesta de crecimiento, sujeta a aliados y financiación, "
          "es convertir la línea escolar en una app propia:")
    tabla(d, ["Fase", "Qué se construye", "Aliados posibles"], [
        ["Fase 1 · 2027-I", "Kit «El suelo habla»: un nodo didáctico por colegio (ESP32 + sensor) conectado a la plataforma, con guía docente y talleres en el PRAE", "Colegios de Sopó, Secretaría de CTeI"],
        ["Fase 2 · 2027-II", "App «Guardianes del Agua»: retos semanales por curso, registro del contador de la casa, huerta escolar monitoreada, puntos y reconocimientos, modo sin conexión", "Emsersopó, Universitaria Agustiniana (semillero de investigación)"],
        ["Fase 3 · 2028", "Red escolar de datos: los colegios publican humedad, lluvia y consumo en un mapa municipal abierto, como insumo para el PUEAA y para clases de ciencias", "Alcaldía, Emsersopó, colegios"],
    ], [2.8, 9.3, 5.0], tam=8.5)
    firma(d, "10 / 11 / 2026")

    # ---------------- Anexo A: guía docente
    d.add_page_break()
    d.add_heading("Anexo A. Guía docente · Taller «El suelo habla»", 1)
    tabla(d, ["Dato", "Detalle"], [
        ["Grados", "6.º a 11.º (se ajusta el nivel de las preguntas)"],
        ["Duración", "2 sesiones de 90 minutos"],
        ["Áreas", "Ciencias naturales, tecnología e informática, PRAE"],
        ["Materiales", "3 botellas plásticas por grupo, arena, tierra, compost, tela, vaso medidor, agua; placa ESP32 con sensor de humedad; celular o computador con internet"],
    ], [3.5, 13.6], encabezado=False, tam=8.5)
    d.add_heading("Sesión 1 · ¿Cuánta agua guarda el suelo?", 2)
    for t_ in ["Encuesta inicial (10 min, Anexo B).",
               "Pregunta detonante (10 min): ¿por qué unas plantas se secan y otras se pudren si se riegan igual?",
               "Experimento de las 3 botellas en grupos (40 min): arena, tierra y tierra con compost; 200 mL en cada una; se mide el agua que baja y se calcula la que guardó el suelo.",
               "Puesta en común (20 min): tabla en el tablero con los resultados de todos los grupos. Concepto clave: la materia orgánica funciona como una esponja.",
               "Tarea (10 min): medir en casa con el «Reto del hogar» cuánta agua gasta la familia."]:
        vineta(d, t_)
    d.add_heading("Sesión 2 · Un sensor que escucha al suelo", 2)
    for t_ in ["Demostración (25 min): el sensor de humedad conectado a la ESP32 en las tres botellas; los estudiantes ven el cambio en la pantalla al echar agua.",
               "Explicación (20 min): evapotranspiración, por qué no hay que regar de más, cómo HidroSopó decide si regar (FAO-56 + pronóstico) y por qué la decisión siempre es de la persona.",
               "Reto en grupos (25 min): con la calculadora «Mi huerta», planear el riego de una huerta escolar de 6 m².",
               "Quiz en línea (10 min) y encuesta final (10 min, Anexo B)."]:
        vineta(d, t_)
    texto(d, ("b", "Evaluación: "), "diferencia entre la encuesta inicial y la final, informe del experimento por grupo y plan de riego de la huerta escolar.")

    # ---------------- Anexo B: encuesta
    d.add_heading("Anexo B. Encuesta antes y después", 1)
    texto(d, "Nombre o código: ____________________   Curso o lugar: ____________________   ☐ Antes   ☐ Después")
    preguntas = [
        "1. ¿Cuál es la mejor hora para regar?  ☐ Al mediodía  ☐ Temprano o al final de la tarde  ☐ Da lo mismo",
        "2. Si se riega de más, el agua…  ☐ hace crecer más la planta  ☐ se va por debajo de las raíces y se lleva nutrientes  ☐ no pasa nada",
        "3. 1 mm de lluvia sobre 1 m² equivale a…  ☐ 1 litro  ☐ 10 litros  ☐ 1 vaso",
        "4. ¿Qué ayuda a que el suelo guarde la humedad?  ☐ Dejarlo desnudo  ☐ Cubrirlo con hojas, pasto seco o compost  ☐ Echarle arena",
        "5. ¿Conoce el Programa de Uso Eficiente y Ahorro del Agua (PUEAA)?  ☐ Sí  ☐ He oído  ☐ No",
        "6. ¿Sabe cuántos litros gasta su casa al día?  ☐ Sí  ☐ Más o menos  ☐ No",
        "7. ¿Recoge agua lluvia en su casa o finca?  ☐ Sí  ☐ No, pero me gustaría  ☐ No",
        "8. De 1 a 5, ¿qué tan importante es para usted ahorrar agua?  ☐ 1  ☐ 2  ☐ 3  ☐ 4  ☐ 5",
    ]
    for q in preguntas:
        p_ = texto(d, q); p_.runs[0].font.size = Pt(9.5)
    texto(d, ("i", "Las preguntas 1 a 4 miden conocimiento (se califican); las 5 a 8, prácticas y percepción."))

    # ---------------- Anexo C: carta
    d.add_page_break()
    d.add_heading("Anexo C. Carta de intención a Emsersopó", 1)
    for linea in ["Sopó, Cundinamarca, ____ de noviembre de 2026", "",
                  "Señores", "EMPRESA DE SERVICIOS PÚBLICOS DE SOPÓ — EMSERSOPÓ", ]:
        texto(d, linea)
    texto(d, "Atn.: ", ("c", "[COMPLETAR: nombre y cargo del gerente o del responsable del PUEAA]"))
    texto(d, "Sopó")
    texto(d, ("b", "Asunto: "), "Propuesta de colaboración en educación para el uso eficiente del agua y en indicadores del sector rural para el PUEAA")
    texto(d, "Respetados señores:")
    texto(d, f"Soy {BENEFICIARIO}, estudiante de Ingeniería Mecatrónica de la Universitaria Agustiniana y beneficiario del incentivo "
          "FOES 2026-II del Municipio de Sopó. Con el acompañamiento de la Secretaría de Ciencia, Tecnología e Innovación desarrollo "
          "el proyecto HidroSopó: un sistema de bajo costo, con sensores e inteligencia artificial, que recomienda cuándo y cuánto "
          "regar en predios rurales. El software, la plataforma y el gemelo digital del predio están desarrollados; la instalación "
          "en el predio piloto y la medición con caudalímetro se realizarán a inicios de 2027.")
    texto(d, "Como parte del proyecto preparé el componente educativo «Sopó Cuida el Agua», que pongo a disposición de la empresa "
          "sin costo, como apoyo a las campañas educativas y de concientización que establece el artículo 12 de la Ley 373 de 1997:")
    for t_ in ["Herramientas en línea para la comunidad: calculadora de riego para huertas, calculadora de agua lluvia, reto del hogar y quiz escolar.",
               "Un plegable para ferias, colegios y puntos de atención, y un taller escolar articulado al PRAE.",
               "Una propuesta de formato de indicadores del uso del agua en el sector rural (volumen captado, módulo de consumo, lámina aplicada, eficiencia y ahorro), que el sistema genera automáticamente cuando hay predios instalados."]:
        vineta(d, t_)
    texto(d, "Les solicito una reunión de 30 minutos para presentar el material, conocer las prioridades de la empresa en el PUEAA "
          "y acordar cómo estos recursos pueden apoyar sus campañas. Puedo ajustarlos al formato y la imagen que la empresa indique.")
    texto(d, "Agradezco su atención.")
    texto(d, "Cordialmente,")
    d.add_paragraph()
    texto(d, ("b", BENEFICIARIO)); texto(d, CC)
    texto(d, "Correo: ", ("c", "[COMPLETAR]"), " · Celular: ", ("c", "[COMPLETAR]"))
    texto(d, "Copia: Secretaría de Ciencia, Tecnología e Innovación de Sopó")

    # ---------------- Anexo D: asistencia
    d.add_page_break()
    d.add_heading("Anexo D. Planilla de asistencia", 1)
    texto(d, "Actividad: ________________________   Lugar: ____________________   Fecha: ____ / ____ / ______")
    tabla(d, ["N.º", "Nombre", "Vereda o barrio", "Tipo (estudiante, productor, hogar…)", "¿Autoriza fotos? (sí/no)", "Firma"],
          [[str(i), "", "", "", "", ""] for i in range(1, 19)], [1.0, 4.6, 3.0, 3.6, 2.2, 2.7], tam=9)
    texto(d, ("i", "Los datos se usan solo para el informe del proyecto (Ley 1581 de 2012)."))
    guardar(d, "Estrategia_Sopo_Cuida_el_Agua_HidroSopo.docx")


if __name__ == "__main__":
    avance1(); avance2(); informe_final(); apropiacion()
