"""
Plegable «Sopó Cuida el Agua» — tríptico carta horizontal (2 caras) para ferias,
mercados campesinos, colegios y huertas caseras.

    python generar_plegable.py   →  plegable.html + Plegable_Sopo_Cuida_el_Agua.pdf

Imprimir a doble cara, «voltear por el borde corto», y doblar en tres.
Las cifras de riego salen del mismo cálculo FAO-56 de la página «Mi huerta».
"""
import io
from pathlib import Path

AQUI = Path(__file__).resolve().parent
import json as _json
# La URL del QR se cambia en poster/config.json → "url_plegable" (un solo lugar para todo)
URL = _json.loads((AQUI.parent / "poster" / "config.json").read_text(encoding="utf-8")).get(
    "url_plegable", "https://claude.ai/artifact/ADUrD7srCq1N17nQWrasq9#comunidad")

# Kc media temporada (FAO-56, tabla 12) · ET0 Sabana: 2,8 normal / 3,6 seco · eficiencia regadera 0,8
CULTIVOS = [("Lechuga", 1.0), ("Cilantro", 1.0), ("Cebolla larga", 1.0), ("Tomate", 1.15),
            ("Fresa", 0.85), ("Zanahoria", 1.05), ("Papa criolla", 1.15), ("Fríjol", 1.15), ("Aromáticas", 0.9)]


def qr_svg():
    import qrcode, qrcode.image.svg
    b = io.BytesIO()
    qrcode.make(URL, image_factory=qrcode.image.svg.SvgPathImage, border=1).save(b)
    s = b.getvalue().decode()
    return s[s.index("<svg"):].replace('width="', 'data-w="').replace('height="', 'data-h="', 1)


def n(v, d=0):
    return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def filas():
    out = []
    for nombre, kc in CULTIVOS:
        normal = kc * 2.8 * 7 / 0.8
        seco = kc * 3.6 * 7 / 0.8
        out.append(f"<tr><td>{nombre}</td><td>{n(normal)} L</td><td>{n(seco)} L</td><td>{n(seco / 10, 1)}</td></tr>")
    return "".join(out)


GOTA = '<svg viewBox="0 0 16 20" class="gota"><path d="M8 0C8 0 0 9 0 13.5A8 8 0 0 0 16 13.5C16 9 8 0 8 0Z"/></svg>'

CSS = """
@page{ size: 279.4mm 215.9mm; margin:0 }
*{ box-sizing:border-box; margin:0; padding:0 }
:root{ --tierra:#2A2117; --agua:#2A7BA3; --hondo:#1B5C7D; --tenue:#E1EEF4; --pasto:#5B8A2C; --pasto-t:#E8F1DC;
  --arcilla:#C2602C; --papel:#FFFDFA; --humo:#5E625B; --linea:#D5DCD6 }
body{ font-family:"Inter","Noto Sans","DejaVu Sans",Arial,sans-serif; color:var(--tierra); font-size:9.6pt; line-height:1.38 }
.cara{ width:279.4mm; height:215.9mm; display:grid; grid-template-columns:repeat(3,1fr); page-break-after:always; background:var(--papel) }
.panel{ padding:11mm 9mm 9mm; position:relative; display:flex; flex-direction:column; gap:3.2mm; overflow:hidden }
.panel + .panel{ border-left:.2mm dashed #E3E0D8 }
h1{ font-family:"Bricolage Grotesque","Inter",sans-serif; font-weight:800; font-size:30pt; line-height:.98; letter-spacing:-.02em }
h2{ font-family:"Bricolage Grotesque","Inter",sans-serif; font-weight:800; font-size:15pt; line-height:1.1; color:var(--hondo) }
h3{ font-weight:700; font-size:10.5pt }
.etq{ font-size:7.6pt; font-weight:700; letter-spacing:.12em; text-transform:uppercase; color:var(--agua) }
.gota{ width:5mm; height:6.2mm; fill:var(--agua) }
.portada{ background:linear-gradient(170deg,#1B5C7D 0%,#22506A 55%,#2A2117 100%); color:#F2F5F2; justify-content:space-between }
.portada h1 em{ font-style:normal; color:#9DE0A0 }
.portada .etq{ color:#BFE3F3 }
.portada p{ color:#D7E3E6; font-size:10.5pt }
.capas{ display:grid; gap:1.6mm } .capas div{ display:flex; gap:2.4mm; align-items:center; font-weight:600; font-size:10pt }
.capas i{ width:6mm; height:6mm; border-radius:50%; background:rgba(255,255,255,.14); display:grid; place-items:center; font-style:normal; font-size:8.5pt; flex:none }
.dato{ background:var(--tenue); border-radius:3.5mm; padding:3.5mm 4mm }
.dato b{ display:block; font-family:"Bricolage Grotesque","Inter",sans-serif; font-size:22pt; line-height:1; color:var(--hondo) }
.reglas{ display:grid; gap:2.6mm; list-style:none; counter-reset:r }
.reglas li{ display:grid; grid-template-columns:8mm 1fr; gap:2mm; counter-increment:r }
.reglas li::before{ content:counter(r); width:7mm; height:7mm; border-radius:50%; background:var(--pasto); color:#fff; display:grid; place-items:center; font-weight:800; font-size:10pt }
table{ width:100%; border-collapse:collapse; font-size:8.6pt }
th{ text-align:left; font-size:7pt; text-transform:uppercase; letter-spacing:.06em; color:var(--humo); padding:1.4mm 1mm; border-bottom:.5mm solid var(--tierra) }
td{ padding:1.5mm 1mm; border-bottom:.2mm solid var(--linea); font-variant-numeric:tabular-nums }
td+td{ text-align:right; white-space:nowrap } th+th{ text-align:right }
.nota{ font-size:7.4pt; color:var(--humo) }
.qr{ width:42mm; height:42mm; background:#fff; padding:2mm; border-radius:3mm; align-self:center }
.qr svg{ width:100%; height:100%; display:block }
.lista{ display:grid; gap:1.8mm; padding-left:4mm } .lista li{ padding-left:1mm }
.caja{ border:.3mm solid var(--linea); border-radius:3.5mm; padding:3.5mm 4mm; display:grid; gap:1.6mm }
.verde{ background:var(--pasto-t); border-color:transparent }
.pie{ margin-top:auto; font-size:7.2pt; color:var(--humo) }
.experimento{ display:grid; grid-template-columns:repeat(3,1fr); gap:2mm; font-size:8pt }
.experimento div{ background:var(--tenue); border-radius:2.5mm; padding:2.4mm }
.experimento b{ display:block; color:var(--hondo); font-size:7.4pt; text-transform:uppercase; letter-spacing:.06em }
"""


def html():
    qr = qr_svg()
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Plegable Sopó Cuida el Agua</title>
<style>{CSS}</style></head><body>

<!-- ============ CARA EXTERIOR: solapa interior · contraportada · portada ============ -->
<div class="cara">
  <div class="panel">
    <span class="etq">Agua lluvia</span>
    <h2>Su techo es un tanque gratis</h2>
    <div class="dato"><b>1 mm × 1 m² = 1 L</b>Un milímetro de lluvia sobre un metro cuadrado de techo da un litro de agua.</div>
    <p>Un techo de <b>40 m²</b> con un aguacero de <b>10 mm</b> recoge cerca de <b>300 litros</b>, contando que se pierde algo y que se botan los primeros litros que lavan el techo.</p>
    <ul class="lista">
      <li>Bote el primer lavado de cada aguacero.</li>
      <li>Tape la caneca con angeo: así no se crían zancudos.</li>
      <li>Úsela para regar y lavar, no para tomar.</li>
      <li>Ponga la caneca en alto y riegue por gravedad.</li>
    </ul>
    <div class="caja verde"><h3>En la casa, sin gastar un peso</h3>
      <ul class="lista">
        <li>Ducha de 5 minutos: ahorra unos 50 L por persona al día con regadera convencional.</li>
        <li>Llave cerrada al cepillarse y al enjabonar los platos.</li>
        <li>Botella con arena en el tanque de un sanitario antiguo.</li>
        <li>El agua de la lavadora sirve para trapear.</li>
      </ul>
    </div>
  </div>

  <div class="panel">
    <span class="etq">Calcule lo suyo</span>
    <h2>Escanee y le decimos cuánto regar</h2>
    <p>Escoja su cultivo, el tamaño de la era o el número de materas, y la página le dice cuántas regaderas echar y cada cuánto. También calcula el agua lluvia de su techo y el gasto de su casa.</p>
    <div class="qr">{qr}</div>
    <p class="nota" style="text-align:center">Funciona en cualquier celular. Gratis y sin registro.</p>
    <div class="caja"><h3>¿Y en el potrero?</h3>
      <p>HidroSopó mide la humedad del suelo a 15, 30 y 45 cm, mira el pronóstico y le dice al productor si debe regar hoy y por cuántos minutos. La decisión siempre es suya.</p></div>
    <div class="pie">Proyecto HidroSopó · José Alejandro Pulido Gómez, Ingeniería Mecatrónica, Universitaria Agustiniana · Incentivo FOES 2026-II, Secretaría de Ciencia, Tecnología e Innovación de Sopó. Material educativo de libre distribución.</div>
  </div>

  <div class="panel portada">
    <div style="display:flex;gap:2.5mm;align-items:center"><svg viewBox="0 0 16 20" class="gota" style="fill:#7FC6E6"><path d="M8 0C8 0 0 9 0 13.5A8 8 0 0 0 16 13.5C16 9 8 0 8 0Z"/></svg><span class="etq">HidroSopó</span></div>
    <div style="display:grid;gap:5mm">
      <h1>Sopó cuida el agua: <em>riegue con lo justo</em></h1>
      <p>Guía rápida para huertas caseras, campesinos y familias. Cuánta agua necesita cada cultivo, cuándo regar y cómo aprovechar la lluvia.</p>
    </div>
    <div class="capas">
      <div><i>1</i>Huerta: litros por cultivo</div>
      <div><i>2</i>Cuatro reglas para regar mejor</div>
      <div><i>3</i>Agua lluvia y ahorro en la casa</div>
      <div><i>4</i>Experimento para el colegio</div>
    </div>
    <p style="font-size:8.6pt">Cada gota cuenta, y aquí se puede contar.</p>
  </div>
</div>

<!-- ============ CARA INTERIOR ============ -->
<div class="cara">
  <div class="panel">
    <span class="etq">Huerta casera</span>
    <h2>¿Cuánta agua por metro cuadrado a la semana?</h2>
    <p>Para una era de 1 m² con la planta ya produciendo. Multiplique por los metros de su era.</p>
    <table><tr><th>Cultivo</th><th>Normal</th><th>Seco</th><th>Regaderas<br>(seco)</th></tr>{filas()}</table>
    <p class="nota">Regadera de 10 L. Recién sembrada necesita cerca de la mitad, pero en riegos cortos y frecuentes. Si llovió, espere y haga la prueba del dedo. Cálculo FAO-56 con la evaporación de referencia de la Sabana de Bogotá (2,8 mm/día normal y 3,6 mm/día en tiempo seco) y 80 % de aprovechamiento de la regadera.</p>
  </div>

  <div class="panel">
    <span class="etq">Cuatro reglas</span>
    <h2>Regar mejor gasta menos</h2>
    <ol class="reglas">
      <li><div><h3>A la hora fresca</h3>Antes de las 9 de la mañana o después de las 4 de la tarde. Al mediodía buena parte se evapora.</div></li>
      <li><div><h3>Prueba del dedo</h3>Meta el dedo hasta el segundo nudillo. Si sale húmedo, todavía no riegue.</div></li>
      <li><div><h3>Al pie de la mata</h3>Despacio y en la raíz, no sobre las hojas: se aprovecha más y se evitan hongos.</div></li>
      <li><div><h3>Suelo cubierto</h3>Pasto seco, hojas o compost encima de la tierra guardan la humedad y espacian los riegos.</div></li>
    </ol>
    <div class="dato" style="background:#F8E8DD"><b style="color:#C2602C">Regar de más</b>no hace crecer más la planta: el agua se va por debajo de la raíz y se lleva el abono.</div>
  </div>

  <div class="panel">
    <span class="etq">Para el colegio</span>
    <h2>¿Qué suelo guarda más agua?</h2>
    <div class="experimento">
      <div><b>Paso 1</b>3 botellas cortadas, boca abajo, con tela en el pico.</div>
      <div><b>Paso 2</b>Arena, tierra, y tierra con compost: la misma cantidad.</div>
      <div><b>Paso 3</b>200 mL de agua en cada una. A los 10 min, mida lo que bajó.</div>
    </div>
    <p><b>Agua guardada = 200 mL − lo que bajó.</b> La tierra con materia orgánica guarda más: por eso cubrir el suelo ahorra riego.</p>
    <div class="caja"><h3>Para el PUEAA de Sopó</h3>
      <p>La Ley 373 de 1997 pide a los municipios un programa de uso eficiente y ahorro del agua, y campañas educativas a la comunidad (artículo 12). Este material hace parte de esa tarea.</p></div>
    <div class="caja verde"><h3>Yo me comprometo</h3>
      <p>En mi casa voy a ahorrar ______ litros al día cambiando: ______________________________</p>
      <p class="nota">Firme, recorte y péguelo en la nevera.</p></div>
  </div>
</div>
</body></html>"""


def main():
    h = html()
    (AQUI / "plegable.html").write_text(h, encoding="utf-8")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page()
        pg.goto((AQUI / "plegable.html").as_uri()); pg.wait_for_timeout(400)
        pg.pdf(path=str(AQUI / "Plegable_Sopo_Cuida_el_Agua.pdf"), width="279.4mm", height="215.9mm", print_background=True)
        b.close()
    print("✓ Plegable_Sopo_Cuida_el_Agua.pdf")


if __name__ == "__main__":
    main()
