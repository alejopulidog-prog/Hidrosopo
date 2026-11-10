"""
HidroSopó — Generador del póster científico (90 × 120 cm, PDF para imprenta)
============================================================================
    python generar_poster.py            → poster.html + HidroSopo_Poster_90x120.pdf

Qué lee:
  config.json      fuente de datos, resultados de las pruebas, URL del QR, contacto
  fotos/           predio.jpg, nodo.jpg, calibracion.jpg, caudal.jpg  (si existen, se insertan)
  logos/           sopo.png, uniagustiniana.png                        (ídem)
  06_datos/…       datos y escenario de ahorro (o los de campo, ver config.json)
  03_backend/modelos/*_metricas.json   métricas del modelo ML

Cambie "fuente_datos" a "campo" cuando tenga datos reales: la cinta de "gemelo
digital" desaparece y los textos pasan a "medido en campo".

PDF: usa Playwright (pip install playwright && playwright install chromium).
Sin Playwright: abra poster.html en Chrome → Imprimir → Guardar como PDF,
tamaño personalizado 900 × 1200 mm, márgenes "Ninguno", gráficos de fondo activado.
"""
from __future__ import annotations
import base64, json, html
from pathlib import Path

import figuras

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]


def _img(carpeta: str, nombre: str) -> str | None:
    for ext in ("png", "jpg", "jpeg", "webp", "svg"):
        p = AQUI / carpeta / f"{nombre}.{ext}"
        if p.exists():
            mime = "svg+xml" if ext == "svg" else ("jpeg" if ext in ("jpg", "jpeg") else ext)
            return f"data:image/{mime};base64,{base64.b64encode(p.read_bytes()).decode()}"
    return None


def _foto(nombre: str, pie: str, grafica: bool = False) -> str:
    src = _img("fotos", nombre)
    if src:
        clase = "foto grafica" if grafica else "foto"
        return f'<figure class="{clase}"><img src="{src}" alt="{html.escape(pie)}"><figcaption>{pie}</figcaption></figure>'
    return (f'<figure class="foto vacia"><div><b>FOTO</b><span>{pie}</span>'
            f'<small>poner en fotos/{nombre}.jpg</small></div></figure>')


def _logo(nombre: str, texto: str) -> str:
    src = _img("logos", nombre)
    return (f'<img class="logo" src="{src}" alt="{texto}">' if src
            else f'<div class="logo vacio">{texto}</div>')


def _qr(url: str) -> str:
    propio = _img("logos", "qr")          # un QR hecho en cualquier generador gratuito
    if propio:
        return f'<div class="qr"><img src="{propio}" alt="QR" style="width:100%;height:100%"></div>'
    if url:
        try:
            import qrcode, qrcode.image.svg, io
            buf = io.BytesIO()
            qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage, border=1).save(buf)
            return f'<div class="qr">{buf.getvalue().decode()}</div>'
        except ImportError:
            pass
    return '<div class="qr vacio">QR<br><small>logos/qr.png<br>o "url_qr"</small></div>'


def _svg(nombre: str) -> str:
    s = (AQUI / nombre).read_text(encoding="utf-8")
    return s[s.index("<svg"):]


def construir(cfg: dict) -> str:
    res = figuras.generar(cfg)
    esc, ho = res["escenario"], res["holdout"]
    m24 = json.loads((RAIZ / "03_backend/modelos/humedad_24h_metricas.json").read_text())
    m48 = json.loads((RAIZ / "03_backend/modelos/humedad_48h_metricas.json").read_text())
    seca, mc_s, mc_l = esc["seca"], esc["montecarlo_temporada_seca"], esc["montecarlo"]
    sim = cfg.get("fuente_datos", "simulacion") != "campo"
    n = lambda v, d=0: f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")

    cinta = ('<div class="cinta">GEMELO DIGITAL · resultados de simulación. '
             'El ahorro definitivo es el medido con el caudalímetro en el predio piloto.</div>'
             if sim else '<div class="cinta campo">Datos medidos en campo · predio piloto, Sopó</div>')

    filas_pruebas = "".join(
        f'<tr><td>{k}</td><td>{v["criterio"]}</td>'
        f'<td class="{v["estado"]}">{v["resultado"]}</td></tr>'
        for k, v in [("Software", cfg["pruebas"]["software"]),
                     ("Calibración gravimétrica", cfg["pruebas"]["calibracion"]),
                     ("Conexión WiFi", cfg["pruebas"]["wifi"]),
                     ("Autonomía energética", cfg["pruebas"]["autonomia"]),
                     ("Caudalímetro", cfg["pruebas"]["caudal"])])

    arquitectura = ARQ_SVG

    return f"""<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<title>HidroSopó — Póster científico</title>
<style>{CSS}</style></head><body><div class="poster">

<header>
  <svg class="estratos" viewBox="0 0 900 190" preserveAspectRatio="none" aria-hidden="true">
    <defs><linearGradient id="gt" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#2A2117"/><stop offset="1" stop-color="#3A2D1F"/></linearGradient></defs>
    <rect width="900" height="190" fill="url(#gt)"/>
    <path d="M0 150 C150 135 300 165 450 150 S750 135 900 150 V190 H0Z" fill="#54412D" opacity=".55"/>
    <path d="M0 168 C200 158 380 180 560 168 S800 160 900 170 V190 H0Z" fill="#6E5637" opacity=".7"/>
    <path d="M0 138 C160 126 320 150 470 138 S760 126 900 138" stroke="#5AA8C9" stroke-width="1.6" fill="none" opacity=".9"/>
  </svg>
  <div class="cab">
    <div class="marca"><span class="gota"></span>HidroSopó</div>
    <h1>¿Cuánta agua se ahorra cuando<br>el <em>suelo</em> puede hablar?</h1>
    <p class="sub">Monitoreo Ambiental Inteligente y Uso Eficiente del Agua · IoT + inteligencia artificial para el riego en predios rurales de Sopó, Cundinamarca</p>
  </div>
  <div class="logos">{_logo("sopo", "LOGO ALCALDÍA DE SOPÓ")}{_logo("uniagustiniana", "LOGO UNIAGUSTINIANA")}</div>
</header>

<div class="autor"><b>José Alejandro Pulido Gómez</b> · Ingeniería Mecatrónica, Universitaria Agustiniana
  <span>Estímulo para la formación en CTeI · FOES 2026-II · COMUC+CTeI · Municipio de Sopó</span></div>

<main>
<div class="col">
  <section><h2><i>01</i>El problema</h2>
    <p>En las fincas lecheras y los pequeños predios agrícolas de Sopó se riega <b>por costumbre</b>: por calendario o “a ojo”. Nadie sabe cuánta agua usa ni puede demostrarlo, y el <b>PUEAA</b> municipal necesita esos datos del sector rural.</p>
    {_foto("predio", "Software funcionando: app del productor, asistente y laboratorio de pruebas (capturas reales, datos de prueba)", True)}
  </section>
  <section class="objetivo"><h2><i>02</i>Objetivo</h2>
    <p>Diseñar, implementar y validar un sistema de <b>bajo costo</b> que mida el agua del suelo y la que entra al predio, y le diga al productor —en su celular y en español— <b>si debe regar hoy y cuánto</b>.</p>
  </section>
  <section><h2><i>03</i>Diagnóstico y diseño electrónico</h2>
    <p class="dato-predio">Predio piloto: <b>kikuyo para pastoreo lechero</b> · riego por aspersión · Sabana de Bogotá, 2.587 m s. n. m.</p>
    <ul class="sensores">
      <li><b>3 × humedad del suelo</b> capacitivos a 15, 30 y 45 cm</li>
      <li><b>Temperatura del suelo</b> DS18B20</li>
      <li><b>Temperatura y humedad del aire</b> SHT31</li>
      <li><b>Pluviómetro</b> de balancín</li>
      <li><b>Caudalímetro de pulsos</b> en la captación: mide los m³</li>
      <li><b>ESP32 con WiFi</b> · 2 × 18650 + panel 10 W · caja IP65 impresa en 3D</li>
    </ul>
    <div class="costos"><div><b>≈ $1,1 M</b><span>hardware por predio (WiFi)</span></div><div><b>$0</b><span>software, nube e IA</span></div><div><b>≥ 8 días</b><span>de autonomía sin sol</span></div></div>
  </section>
</div>

<div class="col">
  <section><h2><i>04</i>Sensores y plataforma en la nube</h2>
    <div class="arq">{arquitectura}</div>
    <p class="pie">Cada nodo envía por WiFi a la nube a través del router de la finca; si se cae la señal guarda hasta 30 h de lecturas. LoRa queda como opción para potreros sin WiFi.</p>
  </section>
  <section><h2><i>05</i>Módulo de IA e instalación piloto</h2>
    <div class="capas">
      <div><b>Capa 1 · Física</b>Balance hídrico <b>FAO-56</b>: ET₀ (Penman-Monteith) × Kc del cultivo, con el pronóstico de Open-Meteo.</div>
      <div><b>Capa 2 · Aprendizaje automático</b><b>Gradient Boosting</b> entrenado con los datos del predio: predice la humedad a 24 y 48 h.</div>
      <div><b>Capa 3 · Conversación</b>App instalable y asistente en español: “Regué 40 minutos”, “¿por qué no riego hoy?”.</div>
    </div>
    <div class="fotos3">{_foto("nodo", "Diseño CAD del nodo: caja IP65, tapa, estaca de sensores y soporte solar (STEP · STL · DXF)", True)}{_foto("calibracion", "Calibración en banco virtual (simulación)", True)}{_foto("caudal", "Caudalímetro: corrección del factor K (simulación)", True)}</div>
  </section>
</div>

<div class="col">
  <section class="resultados"><h2><i>06</i>Pruebas y resultados</h2>
    {cinta}
    <h3>Humedad por profundidad · 4 semanas</h3>
    <div class="fig">{_svg("fig_humedad.svg")}</div>
    <h3>Agua aplicada · temporada seca, 1 ha</h3>
    <div class="fig">{_svg("fig_consumo.svg")}</div>
    <div class="ml">
      <div class="fig">{_svg("fig_modelo.svg")}</div>
      <table><caption>¿La IA le gana a no hacer nada?</caption>
        <tr><th></th><th>24 h</th><th>48 h</th></tr>
        <tr><td>Modelo (MAE)</td><td>{n(m24["mae_cv"],2)}</td><td>{n(m48["mae_cv"],2)}</td></tr>
        <tr><td>Persistencia</td><td>{n(m24["mae_linea_base_persistencia"],2)}</td><td>{n(m48["mae_linea_base_persistencia"],2)}</td></tr>
        <tr class="mejor"><td>Mejora</td><td>{n(m24["mejora_vs_linea_base_pct"],0)} %</td><td>{n(m48["mejora_vs_linea_base_pct"],0)} %</td></tr>
        <tr><td colspan="3" class="nota">MAE en % vol, validación temporal (5 bloques). Persistencia = “mañana igual que hoy”.</td></tr>
      </table>
    </div>
  </section>
  <section class="pueaa"><h2><i>07</i>PUEAA y comunidad</h2>
    <p>El sistema calcula solo los indicadores y los entrega en un informe y en CSV para Emsersopó:</p>
    <div class="chips"><span>Volumen captado <b>m³</b></span><span>Caudal medio y máximo <b>l/s</b></span><span>Módulo de consumo <b>l/s/ha</b></span><span>Lámina aplicada <b>mm</b></span><span>Eficiencia de aplicación <b>%</b></span><span>Ahorro vs. línea base <b>m³ · $</b></span></div>
    <div class="comunidad"><b>Sopó Cuida el Agua</b> · apropiación social (Ley 373, art. 12: campañas educativas)
      <div><span><i>Huertas</i>litros por cultivo y agua lluvia</span><span><i>Ferias</i>plegable con QR y cálculo en vivo</span><span><i>Colegios</i>taller «El suelo habla» · PRAE</span><span><i>Hogares</i>reto de ahorro en casa</span></div>
    </div>
  </section>
</div>
</main>

<section class="ruta">
  <div><i>1</i><b>Diagnóstico y diseño electrónico</b><span>24 ago – 9 oct</span></div>
  <div><i>2</i><b>Sensores y plataforma en la nube</b><span>28 sep – 3 nov</span></div>
  <div><i>3</i><b>Módulo de IA e instalación piloto</b><span>12 oct – 13 nov</span></div>
  <div><i>4</i><b>Pruebas, análisis y recomendaciones</b><span>banco virtual: nov 2026 · campo: ene – feb 2027</span></div>
</section>

<section class="numero">
  <div class="grande">{n(mc_s["ahorro_pct_mediana"],0)}<small>%</small></div>
  <div class="texto"><b>menos agua para regar</b> en temporada seca, sin pérdidas por percolación
    <span>{n(seca["ahorro_m3"])} m³/ha en 90 días · {seca["tradicional"]["eventos"]} riegos por calendario → {seca["hidrosopo"]["eventos"]} con el sistema · ≈ ${n(seca["ahorro_cop_energia"])} de energía de bombeo</span>
    <em>{"Simulación con 50 climas: rango P10–P90 de " + n(mc_s["ahorro_pct_p10"],0) + " a " + n(mc_s["ahorro_pct_p90"],0) + " %. En lluvias el ahorro simulado sube a " + n(mc_l["ahorro_pct_mediana"],0) + " %." if sim else "Medido con caudalímetro contra la línea base del predio."}</em>
  </div>
</section>

<footer>
  <section><h2><i>08</i>Pruebas de validación</h2>
    <table class="pruebas"><tr><th>Prueba</th><th>Criterio</th><th>Resultado</th></tr>{filas_pruebas}</table>
  </section>
  <section class="conclusiones"><h2><i>09</i>Conclusiones y recomendaciones</h2>
    <ul>
      <li><b>Medir cambia la decisión:</b> el sistema evitó {seca["tradicional"]["eventos"] - seca["hidrosopo"]["eventos"]} de {seca["tradicional"]["eventos"]} riegos por calendario y riega solo cuando el suelo lo necesita.</li>
      <li><b>La IA aporta sobre la regla fija:</b> el modelo supera a la persistencia en {n(m48["mejora_vs_linea_base_pct"],0)}–{n(m24["mejora_vs_linea_base_pct"],0)} %; la lluvia pronosticada es su variable más importante.</li>
      <li><b>Limitación:</b> {"resultados de gemelo digital y un solo tipo de predio; " if sim else "un solo predio y una temporada; "}hubo {seca["hidrosopo"]["dias_estres"]} días de estrés leve, por lo que se recomienda bajar el umbral (p = 0,45) en pasto de producción.</li>
      <li><b>Siguiente paso:</b> instalación en el predio piloto y comparación pareada de 4 semanas con caudalímetro (ene – feb 2027); luego 10 predios con Emsersopó y la Secretaría de Ambiente; los indicadores salen listos para el PUEAA (Ley 373 de 1997).</li>
    </ul>
  </section>
  <section class="refs"><h2><i>10</i>Referencias</h2>
    <ol>
      <li>Allen, R. G., Pereira, L. S., Raes, D. y Smith, M. (1998). <i>Crop evapotranspiration</i> (FAO 56). FAO.</li>
      <li>Ojha, T., Misra, S. y Raghuwanshi, N. S. (2015). Wireless sensor networks for agriculture. <i>Computers and Electronics in Agriculture, 118</i>, 66–84.</li>
      <li>Boursianis, A. D., Goudos, S. K., et al. (2021). Smart irrigation system for precision agriculture: the AREThOU5A IoT platform. <i>IEEE Sensors Journal, 21</i>, 17539–17547.</li>
      <li>FAO. (2017). <i>El futuro de la alimentación y la agricultura: tendencias y desafíos</i>. FAO.</li>
      <li>Ley 373 de 1997 y Resolución 1257 de 2018 (PUEAA). Congreso de Colombia; MinAmbiente.</li>
      <li>Pedregosa, F. et al. (2011). Scikit-learn. <i>JMLR, 12</i>, 2825–2830.</li>
      <li>Zippenfenig, P. (2023). <i>Open-Meteo.com Weather API</i>. Zenodo.</li>
    </ol>
    <div class="cierre">{_qr(cfg.get("url_qr", ""))}<div><b>Código abierto</b><span>Código MIT · diseños CC BY 4.0</span><span>{html.escape(cfg.get("contacto", ""))}</span></div></div>
  </section>
</footer>
<div class="lema">💧 Cuidemos el agua, cuidemos el futuro</div>
</div></body></html>"""


ARQ_SVG = """<svg viewBox="0 0 540 430" xmlns="http://www.w3.org/2000/svg" font-family="inherit">
<defs><marker id="fl" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0 10 5 0 10z" fill="#2E7EA6"/></marker></defs>
<g font-size="15" fill="#1E1A14">
 <rect x="10" y="10" width="160" height="150" rx="14" fill="#EDF2E1" stroke="#6F9438" stroke-width="2"/>
 <text x="90" y="36" text-anchor="middle" font-weight="700" font-size="16">Nodo de suelo</text>
 <text x="90" y="60" text-anchor="middle">humedad 15·30·45 cm</text>
 <text x="90" y="80" text-anchor="middle">T suelo · T/HR aire</text>
 <text x="90" y="100" text-anchor="middle">pluviómetro</text>
 <text x="90" y="128" text-anchor="middle" fill="#6A6961" font-size="13">ESP32 + WiFi</text>
 <text x="90" y="146" text-anchor="middle" fill="#6A6961" font-size="13">solar + batería</text>
 <rect x="10" y="180" width="160" height="96" rx="14" fill="#E4F0F6" stroke="#2E7EA6" stroke-width="2"/>
 <text x="90" y="208" text-anchor="middle" font-weight="700" font-size="16">Nodo de caudal</text>
 <text x="90" y="232" text-anchor="middle">caudalímetro</text>
 <text x="90" y="252" text-anchor="middle">m³ captados</text>
 <rect x="220" y="95" width="120" height="96" rx="14" fill="#FFFDFA" stroke="#54412D" stroke-width="2"/>
 <text x="280" y="125" text-anchor="middle" font-weight="700" font-size="16">Router WiFi</text>
 <text x="280" y="148" text-anchor="middle">de la finca</text>
 <text x="280" y="168" text-anchor="middle" fill="#6A6961" font-size="13">nodos reintentan</text>
 <path d="M170 85 Q200 100 218 125" stroke="#2E7EA6" stroke-width="2.4" fill="none" stroke-dasharray="6 5" marker-end="url(#fl)"/>
 <path d="M170 228 Q200 210 218 170" stroke="#2E7EA6" stroke-width="2.4" fill="none" stroke-dasharray="6 5" marker-end="url(#fl)"/>
 <text x="196" y="72" font-size="13" fill="#2E7EA6" font-weight="700">WiFi</text>
 <rect x="390" y="40" width="140" height="210" rx="14" fill="#2A2117"/>
 <text x="460" y="68" text-anchor="middle" font-weight="700" font-size="16" fill="#fff">Nube</text>
 <text x="460" y="96" text-anchor="middle" fill="#E8E3DA">API FastAPI</text>
 <text x="460" y="118" text-anchor="middle" fill="#E8E3DA">PostgreSQL</text>
 <rect x="404" y="134" width="112" height="56" rx="10" fill="#6F9438"/>
 <text x="460" y="157" text-anchor="middle" fill="#fff" font-weight="700">IA</text>
 <text x="460" y="177" text-anchor="middle" fill="#fff" font-size="13">FAO-56 + ML</text>
 <text x="460" y="214" text-anchor="middle" fill="#E8E3DA" font-size="13">clima Open-Meteo</text>
 <text x="460" y="234" text-anchor="middle" fill="#E8E3DA" font-size="13">indicadores PUEAA</text>
 <path d="M340 143 L386 143" stroke="#2E7EA6" stroke-width="2.6" marker-end="url(#fl)"/>
 <text x="362" y="134" text-anchor="middle" font-size="13" fill="#2E7EA6" font-weight="700">HTTPS</text>
 <rect x="230" y="310" width="140" height="110" rx="18" fill="#FFFDFA" stroke="#1E1A14" stroke-width="2"/>
 <text x="300" y="338" text-anchor="middle" font-weight="700" font-size="16">Productor</text>
 <text x="300" y="362" text-anchor="middle">app en el celular</text>
 <text x="300" y="382" text-anchor="middle">“¿riego hoy?”</text>
 <text x="300" y="404" text-anchor="middle" fill="#6A6961" font-size="13">funciona sin señal</text>
 <rect x="395" y="310" width="135" height="110" rx="18" fill="#FFFDFA" stroke="#1E1A14" stroke-width="2"/>
 <text x="462" y="338" text-anchor="middle" font-weight="700" font-size="16">Municipio</text>
 <text x="462" y="362" text-anchor="middle">Emsersopó</text>
 <text x="462" y="382" text-anchor="middle">informe PUEAA</text>
 <text x="462" y="404" text-anchor="middle" fill="#6A6961" font-size="13">CSV / solo lectura</text>
 <path d="M430 250 Q380 285 340 306" stroke="#2E7EA6" stroke-width="2.4" fill="none" marker-end="url(#fl)"/>
 <path d="M470 250 L466 304" stroke="#2E7EA6" stroke-width="2.4" fill="none" marker-end="url(#fl)"/>
</g></svg>"""


CSS = """
@page { size: 900mm 1200mm; margin: 0 }
/* Comillas, rayas y puntos suspensivos en una fuente latina: las fuentes CJK
   los dibujan de ancho completo y dejan huecos raros alrededor */
@font-face{ font-family:"Puntuacion"; src:local("Carlito"),local("Calibri"),local("Liberation Sans"),local("Arial");
  unicode-range:U+2010-2027,U+00AB,U+00BB,U+00B7 }
:root{ --tinta:#1E1A14; --tierra:#2A2117; --tierra2:#54412D; --agua:#2E7EA6; --agua2:#5AA8C9;
  --kikuyo:#6F9438; --kikuyo-t:#EDF2E1; --arcilla:#C4622D; --humo:#6A6961; --linea:#DEDDD3; --papel:#FBFAF6 }
*{ box-sizing:border-box; margin:0; padding:0 }
html,body{ width:900mm; height:1200mm; background:var(--papel);
  -webkit-print-color-adjust:exact; print-color-adjust:exact }
body{ font-family:"Inter","Puntuacion","Noto Sans CJK SC","Noto Sans","DejaVu Sans",Arial,sans-serif; color:var(--tinta); font-size:9mm; line-height:1.34 }
.poster{ width:900mm; height:1200mm; position:relative; overflow:hidden; display:flex; flex-direction:column; padding-bottom:34mm }
.poster > main{ flex:1 } .poster > footer{ padding-top:12mm }
header{ position:relative; height:190mm; color:#fff; padding:20mm 34mm 0 }
.estratos{ position:absolute; inset:0; width:100%; height:100% }
.cab{ position:relative; max-width:690mm }
.marca{ display:flex; align-items:center; gap:5mm; font-size:12mm; font-weight:800; letter-spacing:.02em; color:#BFE0EE }
.gota{ width:9mm; height:12mm; background:var(--agua2); border-radius:50% 50% 50% 50% / 62% 62% 38% 38%; transform:rotate(180deg) }
h1{ font-size:31mm; line-height:1.04; font-weight:900; margin-top:7mm; letter-spacing:-.01em }
h1 em{ font-style:normal; color:#C9A46B }
.sub{ margin-top:7mm; font-size:10mm; color:#E8E3DA; max-width:660mm; line-height:1.25 }
.logos{ position:absolute; right:34mm; top:24mm; display:flex; flex-direction:column; gap:7mm; align-items:flex-end }
.logo{ max-height:42mm; max-width:120mm; background:#fff; padding:3mm; border-radius:4mm }
.logo.vacio{ background:transparent; padding:0; width:120mm; height:42mm; border:.7mm dashed rgba(255,255,255,.55); border-radius:4mm; display:grid; place-items:center; font-size:5.5mm; color:#E8E3DA; text-align:center; letter-spacing:.06em }
.autor{ padding:7mm 34mm; font-size:9.6mm; border-bottom:.6mm solid var(--linea); display:flex; justify-content:space-between; align-items:baseline; gap:10mm }
.autor span{ font-size:7.4mm; color:var(--humo) }
main{ display:grid; grid-template-columns:268mm 268mm 268mm; gap:13mm; padding:11mm 34mm 0 }
.col{ display:flex; flex-direction:column; gap:10mm }
section h2{ display:flex; align-items:center; gap:4mm; font-size:12.5mm; line-height:1.1; font-weight:800; margin-bottom:4.5mm; color:var(--tierra) }
section h2 i{ font-style:normal; font-size:7mm; font-weight:800; color:#fff; background:var(--agua); border-radius:50%; width:13mm; height:13mm; display:grid; place-items:center; flex:none }
h3{ font-size:8mm; color:var(--humo); font-weight:700; margin:4mm 0 1.5mm; text-transform:uppercase; letter-spacing:.04em }
p{ margin-bottom:3mm }
b{ font-weight:700 }
.objetivo{ background:var(--tierra); color:#fff; border-radius:7mm; padding:9mm 10mm }
.objetivo h2{ color:#fff } .objetivo h2 i{ background:var(--kikuyo) }
.objetivo p{ font-size:10mm; line-height:1.28; margin:0 } .objetivo b{ color:#C9DE9E }
.foto{ border-radius:5mm; overflow:hidden; background:#E9E6DD; position:relative }
.foto img{ width:100%; height:100%; object-fit:cover; display:block }
.foto.grafica{ background:#FBFAF6; border:.35mm solid var(--linea) } .foto.grafica img{ object-fit:contain; padding:2mm 2mm 15mm } .foto.grafica figcaption{ color:var(--tierra); background:none; font-weight:600 }
.foto figcaption{ position:absolute; left:0; right:0; bottom:0; padding:2mm 4mm; font-size:5.6mm; color:#fff; background:linear-gradient(transparent,rgba(0,0,0,.6)) }
.foto.vacia{ border:.6mm dashed #B9AE9C; display:grid; place-items:center; text-align:center; color:var(--humo) }
.foto.vacia b{ display:block; font-size:8mm; letter-spacing:.2em; color:#9C8F7A } .foto.vacia span{ display:block; font-size:6.4mm } .foto.vacia small{ font-size:5mm; color:#9C8F7A }
.col:first-child .foto{ height:165mm; margin-top:3mm }
.dato-predio{ background:var(--kikuyo-t); border-left:2mm solid var(--kikuyo); padding:3mm 5mm; border-radius:0 3mm 3mm 0; font-size:7.8mm }
.sensores{ list-style:none; margin:4mm 0 } .sensores li{ padding:2.6mm 0 2.6mm 9mm; position:relative; font-size:8.2mm; border-bottom:.35mm solid var(--linea) }
.sensores li::before{ content:""; position:absolute; left:0; top:4.6mm; width:4.5mm; height:4.5mm; border-radius:50%; background:var(--agua) }
.costos{ display:grid; grid-template-columns:repeat(3,1fr); gap:4mm; margin-top:5mm }
.costos div{ background:#fff; border:.5mm solid var(--linea); border-radius:4mm; padding:4mm; text-align:center }
.costos b{ display:block; font-size:11mm; color:var(--agua); line-height:1.05 } .costos span{ font-size:6mm; color:var(--humo) }
.arq{ background:#fff; border:.5mm solid var(--linea); border-radius:6mm; padding:5mm }
.arq svg{ width:100%; height:auto; display:block; font-family:inherit }
.pie{ font-size:7mm; color:var(--humo); margin-top:3mm }
.capas{ display:flex; flex-direction:column; gap:3.5mm }
.capas div{ background:#fff; border:.5mm solid var(--linea); border-left:2.4mm solid var(--agua); border-radius:3mm; padding:4mm 5mm; font-size:8mm; line-height:1.28 }
.capas div:nth-child(2){ border-left-color:var(--kikuyo) } .capas div:nth-child(3){ border-left-color:var(--arcilla) }
.capas div > b:first-child{ display:block; font-size:6.4mm; text-transform:uppercase; letter-spacing:.05em; color:var(--humo); margin-bottom:1mm }
.fotos3{ display:grid; grid-template-columns:1fr 1fr; gap:4mm; margin-top:5mm }
.fotos3 .foto{ height:100mm } .fotos3 .foto:first-child{ grid-column:1 / 3; height:125mm }
.cinta{ background:#FFF3E6; color:#8A3E14; border:.5mm solid #F0C9A6; border-radius:3mm; padding:2.5mm 4mm; font-size:6.2mm; font-weight:600; line-height:1.3 }
.cinta.campo{ background:var(--kikuyo-t); color:#42601F; border-color:#CFE0B0 }
.fig svg{ width:100%; height:auto; display:block }
.ml{ display:grid; grid-template-columns:1fr 1fr; gap:4mm; align-items:center; margin-top:3mm }
.ml table{ border-collapse:collapse; font-size:6.8mm; width:100% }
.ml caption{ text-align:left; font-weight:800; font-size:7.6mm; margin-bottom:2mm; color:var(--tierra) }
.ml th,.ml td{ padding:1.8mm 2mm; border-bottom:.35mm solid var(--linea); text-align:right } .ml td:first-child{ text-align:left }
.ml tr.mejor td{ color:var(--kikuyo); font-weight:800; font-size:8.4mm }
.ml td.nota{ font-size:5mm; color:var(--humo); text-align:left; border:0; line-height:1.25 }
.numero{ margin:9mm 34mm 0; background:linear-gradient(100deg,#1F5F80,#2E7EA6 55%,#3D93B8); color:#fff; border-radius:9mm; display:flex; align-items:center; gap:14mm; padding:7mm 18mm; position:relative; overflow:hidden }
.numero::after{ content:""; position:absolute; right:-40mm; top:-50mm; width:200mm; height:200mm; border-radius:50%; background:rgba(255,255,255,.06) }
.grande{ font-size:62mm; font-weight:900; line-height:.9; letter-spacing:-.03em } .grande small{ font-size:30mm; margin-left:1mm }
.numero .texto{ font-size:12mm; line-height:1.15; position:relative; z-index:1 }
.numero .texto span{ display:block; font-size:7.6mm; color:#DDEEF6; margin-top:3mm; line-height:1.3 }
.numero .texto em{ display:block; font-style:normal; font-size:6.2mm; color:#BFE0EE; margin-top:2mm }
footer{ display:grid; grid-template-columns:250mm 320mm 236mm; gap:13mm; padding:10mm 34mm 0 }
.pruebas{ border-collapse:collapse; width:100%; font-size:7.6mm }
.pruebas th{ text-align:left; color:var(--humo); font-size:5.6mm; text-transform:uppercase; letter-spacing:.04em; padding:1.6mm 1.5mm; border-bottom:.6mm solid var(--tierra) }
.pruebas td{ padding:2.1mm 1.5mm; border-bottom:.35mm solid var(--linea); vertical-align:top }
.pruebas td.ok{ color:var(--kikuyo); font-weight:800 } .pruebas td.sim{ color:#9A5A12; font-weight:700 } .pruebas td.sim small{ display:block; font-weight:500; font-size:5.4mm; color:var(--humo) } .pruebas td.pendiente{ color:var(--arcilla); font-style:italic } .pruebas td.fallo{ color:#A83E30; font-weight:800 }
.conclusiones ul{ list-style:none } .conclusiones li{ font-size:8.1mm; line-height:1.3; padding:1.8mm 0 1.8mm 8mm; position:relative }
.conclusiones li::before{ content:""; position:absolute; left:0; top:4.2mm; width:3.6mm; height:3.6mm; background:var(--kikuyo); transform:rotate(45deg) }
.refs ol{ font-size:6.4mm; line-height:1.3; padding-left:6mm; color:#3B362F } .refs li{ margin-bottom:1.2mm }
.cierre{ display:flex; gap:5mm; align-items:center; margin-top:4mm }
.cierre b{ display:block; font-size:7mm } .cierre span{ display:block; font-size:5.4mm; color:var(--humo) }
.qr{ width:50mm; height:50mm; flex:none; background:#fff } .qr svg{ width:100%; height:100% }
.qr.vacio{ border:.6mm dashed #B9AE9C; display:grid; place-items:center; text-align:center; font-weight:800; color:#9C8F7A; font-size:7mm; line-height:1.1 } .qr.vacio small{ font-size:3.6mm; font-weight:400 }
.pueaa p{ font-size:8mm }
.chips{ display:flex; flex-wrap:wrap; gap:3mm }
.comunidad{ margin-top:5mm; background:var(--tierra); color:#F2EEE6; border-radius:5mm; padding:5mm 6mm; font-size:7.2mm; line-height:1.3 }
.comunidad > b{ color:#9DE0A0; font-size:8.4mm }
.comunidad div{ display:grid; grid-template-columns:1fr 1fr; gap:2.5mm; margin-top:3mm }
.comunidad span{ background:rgba(255,255,255,.08); border-radius:3mm; padding:2.4mm 3mm; font-size:6.4mm }
.comunidad i{ display:block; font-style:normal; font-weight:800; color:#7FC6E6; font-size:6.8mm }
.chips span{ background:#fff; border:.5mm solid var(--linea); border-radius:20mm; padding:2.4mm 5mm; font-size:7.2mm }
.chips b{ color:var(--agua); margin-left:1.5mm }
.ruta{ margin:9mm 34mm 0; display:grid; grid-template-columns:repeat(4,1fr); gap:0; position:relative }
.ruta div{ position:relative; padding:6mm 6mm 6mm 22mm; background:#fff; border:.5mm solid var(--linea); margin-right:-.5mm }
.ruta div:first-child{ border-radius:5mm 0 0 5mm } .ruta div:last-child{ border-radius:0 5mm 5mm 0 }
.ruta i{ position:absolute; left:5mm; top:50%; transform:translateY(-50%); width:13mm; height:13mm; border-radius:50%; background:var(--kikuyo); color:#fff; font-style:normal; font-weight:800; display:grid; place-items:center; font-size:7mm }
.ruta b{ display:block; font-size:8mm; line-height:1.15 } .ruta span{ font-size:6mm; color:var(--humo) }
.lema{ position:absolute; left:0; right:0; bottom:0; height:22mm; background:var(--tierra); color:#E8E3DA; display:grid; place-items:center; font-size:8mm; letter-spacing:.03em }
"""


def main():
    cfg = json.loads((AQUI / "config.json").read_text(encoding="utf-8"))
    pagina = construir(cfg)
    (AQUI / "poster.html").write_text(pagina, encoding="utf-8")
    print("✓ poster.html")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright no está instalado: abra poster.html en Chrome e imprima a PDF 900×1200 mm.")
        return
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.goto((AQUI / "poster.html").as_uri()); pg.wait_for_timeout(800)
        pg.pdf(path=str(AQUI / "HidroSopo_Poster_90x120.pdf"), width="900mm", height="1200mm",
               print_background=True, prefer_css_page_size=True)
        b.close()
    print("✓ HidroSopo_Poster_90x120.pdf")


if __name__ == "__main__":
    main()
