"""Ícono de HidroSopó: gota blanca con brote, sobre degradado agua→tierra y capas de suelo.
Contraste alto para que se vea en pantallas de inicio claras y oscuras."""
import math, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
S = 1024; K = 4  # supermuestreo

def lerp(a,b,t): return tuple(int(a[i]+(b[i]-a[i])*t) for i in range(3))

def fondo(n):
    im = Image.new("RGB",(n,n)); px = im.load()
    c1, c2, c3 = (31,155,204), (17,96,130), (24,52,44)
    for y in range(n):
        for x in range(n):
            t = (x*0.35 + y*0.9)/(n*1.25)
            px[x,y] = lerp(c1,c2,t/0.6) if t<0.6 else lerp(c2,c3,(t-0.6)/0.4)
    return im

def gota(d, cx, cy, R, color):
    dist = 2.05*R; a = math.acos(R/dist); up = -math.pi/2
    pts = [(cx, cy-dist)]
    n = 120
    for i in range(n+1):
        th = up + a + (2*math.pi - 2*a)*i/n
        pts.append((cx + R*math.cos(th), cy + R*math.sin(th)))
    d.polygon(pts, fill=color)

def arte(n, escala):
    big = n*K
    im = fondo(256).resize((big,big), Image.BICUBIC).convert("RGBA")
    d = ImageDraw.Draw(im)
    c = big/2
    # capas de suelo abajo, con borde ondulado de pasto
    base = big*0.79
    for i,(col,off) in enumerate([((110,86,55),0),((84,65,45),0.065),((59,46,32),0.13)]):
        y0 = base + big*off
        pts = [(0,big)]
        for x in range(0, big+1, big//60):
            pts.append((x, y0 + (big*0.012 if i==0 else 0)*math.sin(x/big*math.pi*6)))
        pts.append((big,big)); d.polygon(pts, fill=col)
    d.line([(x, base - big*0.004 + big*0.012*math.sin(x/big*math.pi*6)) for x in range(0,big+1,big//120)],
           fill=(132,190,72), width=int(big*0.022))
    # sombra suave de la gota
    sh = Image.new("RGBA",(big,big),(0,0,0,0)); ds = ImageDraw.Draw(sh)
    R = big*0.225*escala; cy = c + big*0.07*escala
    gota(ds, c+big*0.012, cy+big*0.02, R, (0,0,0,90))
    sh = sh.filter(ImageFilter.GaussianBlur(big*0.02)); im = Image.alpha_composite(im, sh)
    d = ImageDraw.Draw(im)
    gota(d, c, cy, R, (255,255,255,255))
    # brote dentro de la gota
    def hoja(x0,y0,x1,y1,ancho,col):
        L = math.hypot(x1-x0,y1-y0); ux,uy = (x1-x0)/L,(y1-y0)/L; nx,ny = -uy,ux
        pts = []
        for i in range(41):
            t = i/40; b = math.sin(math.pi*t)*ancho
            pts.append((x0+ux*L*t+nx*b, y0+uy*L*t+ny*b))
        for i in range(40,-1,-1):
            t = i/40; b = math.sin(math.pi*t)*ancho
            pts.append((x0+ux*L*t-nx*b, y0+uy*L*t-ny*b))
        d.polygon(pts, fill=col)
    g = (46,128,52); w = int(R*0.12)
    tallo = [(c + R*0.06*math.sin(t*2.2), cy + R*0.62 - R*0.95*t) for t in [i/30 for i in range(31)]]
    d.line(tallo, fill=g, width=w, joint="curve")
    hoja(c, cy-R*0.05, c-R*0.66, cy-R*0.42, R*0.2, g)
    hoja(c+R*0.04, cy-R*0.28, c+R*0.62, cy-R*0.78, R*0.22, (84,168,58))
    return im.resize((n,n), Image.LANCZOS).convert("RGB")

a = arte(1024, 1.0)
for nombre, tam in [("icono-512.png",512),("icono-192.png",192),("apple-touch-icon.png",180),("favicon-48.png",48)]:
    a.resize((tam,tam), Image.LANCZOS).save(OUT/nombre, optimize=True)
arte(1024, 0.78).resize((512,512), Image.LANCZOS).save(OUT/"icono-maskable-512.png", optimize=True)
print("ok")
