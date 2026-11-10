"""Render del diseño CAD del nodo (caja IP65, estaca, soporte solar) para el póster.
    python render_cad.py  →  ../../09_entregables/poster/fotos/nodo.png
"""
import struct, sys
from pathlib import Path
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

AQUI = Path(__file__).resolve().parent

def leer_stl(p):
    b = p.read_bytes()
    if b[:5].lower() == b"solid" and b"facet" in b[:400]:
        v = [list(map(float, l.split()[1:4])) for l in b.decode(errors="ignore").splitlines() if l.strip().startswith("vertex")]
        return np.array(v).reshape(-1, 3, 3)
    n = struct.unpack("<I", b[80:84])[0]
    a = np.frombuffer(b[84:84 + n * 50], dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("x", "<u2")]))
    return a["v"].reshape(-1, 3, 3).astype(float)

def dibujar(ax, tri, desplaz, color):
    tri = tri - tri.reshape(-1, 3).min(0) + np.array(desplaz)
    nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    nrm /= (np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-9)
    luz = np.array([0.35, -0.55, 0.75]); luz /= np.linalg.norm(luz)
    k = 0.45 + 0.55 * np.clip(nrm @ luz, 0, 1)
    base = np.array(matplotlib.colors.to_rgb(color))
    pc = Poly3DCollection(tri, facecolors=np.clip(base * k[:, None] + 0.08, 0, 1), edgecolors="none")
    ax.add_collection3d(pc)
    return tri.reshape(-1, 3)

piezas = [("caja_base.stl", (0, 0, 0), "#E7E1D4"), ("caja_tapa.stl", (0, 0, 95), "#2E7EA6"),
          ("soporte_solar.stl", (190, 0, 0), "#6A8E3A"), ("estaca_guia.stl", (-120, 20, 0), "#C2602C"),
          ("estaca_collar.stl", (-120, 120, 0), "#C2602C"), ("estaca_punta.stl", (-60, 120, 0), "#8A7A62")]
fig = plt.figure(figsize=(14, 6.4), dpi=420); fig.patch.set_facecolor("#E9E6DD")
ax = fig.add_subplot(projection="3d"); ax.set_facecolor("#E9E6DD")
pts = []
for f, d, c in piezas:
    p = AQUI / "salida" / f
    if p.exists(): pts.append(dibujar(ax, leer_stl(p), d, c))
P = np.vstack(pts); mn, mx = P.min(0), P.max(0); r = (mx - mn).max() / 2; cen = (mx + mn) / 2
ax.set_xlim(cen[0] - r, cen[0] + r); ax.set_ylim(cen[1] - r, cen[1] + r); ax.set_zlim(cen[2] - r * 0.45, cen[2] + r * 0.45)
ax.set_box_aspect((1, 1, 0.45)); ax.view_init(elev=24, azim=-58); ax.set_axis_off()
plt.subplots_adjust(0, 0, 1, 1)
out = AQUI.parents[1] / "09_entregables/poster/fotos/nodo.png"
fig.savefig(out, facecolor=fig.get_facecolor()); print(out)

# Recortar al contenido, con margen y proporción ≈ 2,2 : 1 (hueco del póster)
from PIL import Image, ImageChops
im = Image.open(out).convert("RGB")
bg = Image.new("RGB", im.size, im.getpixel((0, 0)))
x0, y0, x1, y1 = ImageChops.difference(im, bg).getbbox()
cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
h = (y1 - y0) * 1.25; w = max((x1 - x0) * 1.15, h * 2.2); h = w / 2.2
im.crop((int(cx - w / 2), int(cy - h / 2), int(cx + w / 2), int(cy + h / 2))).save(out)
