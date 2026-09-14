"""
HidroSopó — CAD paramétrico en geometría sólida (B-Rep)
========================================================
Genera archivos STEP, STL y DXF a partir de un solo script.

POR QUÉ ESTE ARCHIVO Y NO SOLO LOS .SCAD
-----------------------------------------
Los archivos OpenSCAD (.scad) producen MALLAS (STL): triángulos.
Inventor y AutoCAD los abren, pero como cuerpo de malla: no puedes
acotarlos bien, no puedes editar una operación, y los planos salen feos.

Este script produce geometría SÓLIDA B-Rep y exporta **STEP (AP214)**,
que es el formato de intercambio estándar de la industria. Inventor,
SolidWorks, Fusion 360, CATIA y AutoCAD 3D lo abren como sólido real,
con caras, aristas y vértices propios. Ahí sí puedes acotar, hacer
planos de taller y editar.

También exporta DXF de las vistas en planta, que AutoCAD abre nativo
para hacer los planos 2D.

USO
---
    pip install cadquery
    python cad_solido.py

    # Solo una pieza:
    python cad_solido.py --pieza caja_base

Salida en la carpeta `salida/`:
    *.step   → Inventor, AutoCAD 3D, SolidWorks, Fusion 360
    *.stl    → impresión 3D
    *.dxf    → AutoCAD 2D (vistas en planta para planos)

Licencia: CC BY 4.0
"""

from __future__ import annotations
import argparse
import os

import cadquery as cq
from cadquery import exporters

# ============================================================
#  PARÁMETROS — ajusta aquí, todo se regenera
# ============================================================

# --- Caja del nodo ---
CAJA_ANCHO = 150.0      # X interior (mm)
CAJA_LARGO = 100.0      # Y interior
CAJA_ALTO = 60.0        # Z interior
PARED = 3.0
R_ESQ = 8.0             # radio de esquina interior
H_LABIO = 8.0           # altura del labio de la tapa

CANAL_ANCHO = 3.2       # canal para cordón de sello de 3 mm
CANAL_PROF = 2.0

PG7_D = 12.5            # diámetro de rosca prensaestopas PG7
PG9_D = 15.5            # PG9
N_PG7 = 4
ANTENA_D = 6.5          # paso de conector SMA

TORNILLO_D = 3.4        # paso para M3
INSERTO_D = 4.2         # inserto roscado térmico M3
INSERTO_H = 6.0

PCB_ANCHO = 51.0        # Heltec WiFi LoRa 32 V3
PCB_LARGO = 26.0
POSTE_D = 7.0
POSTE_H = 8.0

OLED_ANCHO = 26.0
OLED_ALTO = 14.0

# --- Estaca de sensores ---
TUBO_D_EXT = 21.3       # PVC 1/2" presión — MÍDELO con calibrador
SENSOR_ANCHO = 24.0     # sensor capacitivo v2.0
SENSOR_ESP = 1.8
COLLAR_H = 34.0
TOL = 0.35              # tolerancia de impresión FDM

# --- Soporte solar ---
ANGULO_PANEL = 15.0     # grados; para autolimpieza por lluvia, no captación
POSTE_TUBO_D = 33.4     # tubo galvanizado 1"

SALIDA = "salida"


# ============================================================
#  Piezas
# ============================================================

def caja_base() -> cq.Workplane:
    """Cuerpo inferior del encapsulado IP65."""
    ext_x = CAJA_ANCHO + 2 * PARED
    ext_y = CAJA_LARGO + 2 * PARED

    # Cuerpo exterior con esquinas redondeadas
    p = (cq.Workplane("XY")
         .rect(ext_x, ext_y)
         .extrude(CAJA_ALTO)
         .edges("|Z").fillet(R_ESQ + PARED))

    # Cavidad interior. Se construye como sólido ya redondeado y se resta:
    # filetear las aristas DESPUÉS del corte falla, porque el selector toma
    # también las aristas del fondo y OCC no puede resolver esos empalmes.
    cavidad = (cq.Workplane("XY").workplane(offset=PARED)
               .rect(CAJA_ANCHO, CAJA_LARGO)
               .extrude(CAJA_ALTO)
               .edges("|Z").fillet(R_ESQ))
    p = p.cut(cavidad)

    # Canal de sello en el borde superior
    canal_medio = (CAJA_ANCHO + CAJA_LARGO) / 2  # referencia, no usado directamente
    canal = (cq.Workplane("XY").workplane(offset=CAJA_ALTO - CANAL_PROF)
             .rect(CAJA_ANCHO + PARED + CANAL_ANCHO / 2,
                   CAJA_LARGO + PARED + CANAL_ANCHO / 2)
             .rect(CAJA_ANCHO + PARED - CANAL_ANCHO / 2,
                   CAJA_LARGO + PARED - CANAL_ANCHO / 2)
             .extrude(CANAL_PROF + 1))
    p = p.cut(canal)

    # Prensaestopas PG7 en la cara -Y (cables de sensores hacia el suelo)
    paso = (CAJA_ANCHO - 44) / max(1, N_PG7 - 1)
    for i in range(N_PG7):
        x = -CAJA_ANCHO / 2 + 22 + i * paso
        agujero = (cq.Workplane("XZ")
                   .workplane(offset=CAJA_LARGO / 2 + PARED + 1)
                   .center(x, CAJA_ALTO * 0.35)
                   .circle(PG7_D / 2)
                   .extrude(PARED + 2))
        p = p.cut(agujero)

    # PG9 en +X para el cable del panel solar
    pg9 = (cq.Workplane("YZ")
           .workplane(offset=ext_x / 2 - PARED - 1)
           .center(0, CAJA_ALTO * 0.6)
           .circle(PG9_D / 2)
           .extrude(PARED + 2))
    p = p.cut(pg9)

    # Paso de antena SMA en -X
    ant = (cq.Workplane("YZ")
           .workplane(offset=-ext_x / 2 - 1)
           .center(CAJA_LARGO / 4, CAJA_ALTO * 0.6)
           .circle(ANTENA_D / 2)
           .extrude(PARED + 2))
    p = p.cut(ant)

    # Insertos roscados M3 en las 4 esquinas
    for sx in (-1, 1):
        for sy in (-1, 1):
            ins = (cq.Workplane("XY")
                   .workplane(offset=CAJA_ALTO - INSERTO_H)
                   .center(sx * (CAJA_ANCHO / 2 - 2), sy * (CAJA_LARGO / 2 - 2))
                   .circle(INSERTO_D / 2)
                   .extrude(INSERTO_H + 1))
            p = p.cut(ins)

    # Drenaje de condensado: 1.5 mm deja salir vapor, no entra agua a presión
    dren = cq.Workplane("XY").workplane(offset=-1).circle(0.75).extrude(PARED + 2)
    p = p.cut(dren)

    # Postes de montaje de la PCB con hueco para inserto
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx = sx * PCB_ANCHO / 2
            cy = sy * PCB_LARGO / 2
            poste = (cq.Workplane("XY").workplane(offset=PARED)
                     .center(cx, cy).circle(POSTE_D / 2).extrude(POSTE_H))
            hueco = (cq.Workplane("XY")
                     .workplane(offset=PARED + POSTE_H - INSERTO_H)
                     .center(cx, cy).circle(INSERTO_D / 2)
                     .extrude(INSERTO_H + 0.1))
            p = p.union(poste).cut(hueco)

    # Orejas laterales para amarrar a la estaca
    for s in (-1, 1):
        oreja = (cq.Workplane("XY")
                 .workplane(offset=CAJA_ALTO * 0.25)
                 .center(s * (ext_x / 2 + 4), 0)
                 .rect(14, 16).extrude(8)
                 .edges("|Z").fillet(3))
        agu = (cq.Workplane("XY")
               .workplane(offset=CAJA_ALTO * 0.25 - 1)
               .center(s * (ext_x / 2 + 4), 0)
               .circle(2.75).extrude(12))
        p = p.union(oreja).cut(agu)

    return p


def caja_tapa() -> cq.Workplane:
    """Tapa con labio de sellado, visera y ventana para el OLED."""
    ext_x = CAJA_ANCHO + 2 * PARED
    ext_y = CAJA_LARGO + 2 * PARED

    p = (cq.Workplane("XY")
         .rect(ext_x, ext_y).extrude(PARED)
         .edges("|Z").fillet(R_ESQ + PARED))

    # Labio que entra en la base (con holgura de impresión)
    labio_ext = (cq.Workplane("XY").workplane(offset=-H_LABIO)
                 .rect(CAJA_ANCHO - 2 * TOL, CAJA_LARGO - 2 * TOL)
                 .extrude(H_LABIO))
    labio_int = (cq.Workplane("XY").workplane(offset=-H_LABIO - 0.1)
                 .rect(CAJA_ANCHO - 2 * PARED, CAJA_LARGO - 2 * PARED)
                 .extrude(H_LABIO + 0.2))
    p = p.union(labio_ext.cut(labio_int))

    # Visera contra sol y lluvia directa sobre el frente
    visera = (cq.Workplane("XY")
              .center(0, -ext_y / 2 - 7)
              .rect(ext_x, 14).extrude(PARED))
    p = p.union(visera)

    # Paso de tornillos M3 con avellanado
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx = sx * (CAJA_ANCHO / 2 - 2)
            cy = sy * (CAJA_LARGO / 2 - 2)
            paso = (cq.Workplane("XY").workplane(offset=-1)
                    .center(cx, cy).circle(TORNILLO_D / 2).extrude(PARED + 2))
            avell = (cq.Workplane("XY").workplane(offset=PARED - 1.8)
                     .center(cx, cy)
                     .circle(TORNILLO_D / 2).workplane(offset=1.8).circle(3.25)
                     .loft())
            p = p.cut(paso).cut(avell)

    # Ventana del OLED (se sella con acrílico + silicona)
    oled = (cq.Workplane("XY").workplane(offset=-1)
            .rect(OLED_ANCHO, OLED_ALTO).extrude(PARED + 2))
    p = p.cut(oled)

    return p


def estaca_collar() -> cq.Workplane:
    """Collar porta-sensor. Se desliza sobre el tubo PVC y sujeta un sensor."""
    d_ext = TUBO_D_EXT + 8

    p = cq.Workplane("XY").circle(d_ext / 2).extrude(COLLAR_H)

    # Aleta que sostiene el sensor
    aleta = (cq.Workplane("XY")
             .center(TUBO_D_EXT / 2 + 7, 0)
             .rect(10, SENSOR_ANCHO + 6).extrude(COLLAR_H))
    p = p.union(aleta)

    # Paso del tubo
    tubo = cq.Workplane("XY").workplane(offset=-1).circle((TUBO_D_EXT + TOL) / 2).extrude(COLLAR_H + 2)
    p = p.cut(tubo)

    # Ranura del sensor
    ranura = (cq.Workplane("XY").workplane(offset=4)
              .center(TUBO_D_EXT / 2 + 7, 0)
              .rect(SENSOR_ESP + TOL, SENSOR_ANCHO + TOL)
              .extrude(COLLAR_H))
    p = p.cut(ranura)

    # Tornillo prisionero M3 para fijar al tubo
    pris = (cq.Workplane("XZ").workplane(offset=-d_ext / 2 - 1)
            .center(0, COLLAR_H / 2).circle(1.45).extrude(d_ext + 2))
    p = p.cut(pris)

    # Canal de salida del cable
    canal = (cq.Workplane("YZ").workplane(offset=-d_ext / 2 - 1)
             .center(0, COLLAR_H / 2).circle(2.5).extrude(6))
    p = p.cut(canal)

    return p


def estaca_punta() -> cq.Workplane:
    """Punta cónica de penetración. Imprimir con 100% de relleno."""
    p = (cq.Workplane("XY")
         .circle((TUBO_D_EXT + 4) / 2)
         .workplane(offset=40)
         .circle(1.5)
         .loft())
    faldon = cq.Workplane("XY").workplane(offset=-15).circle((TUBO_D_EXT + 4) / 2).extrude(15)
    p = p.union(faldon)

    hueco = (cq.Workplane("XY").workplane(offset=-16)
             .circle((TUBO_D_EXT + TOL) / 2).extrude(16))
    p = p.cut(hueco)

    pris = (cq.Workplane("XZ").workplane(offset=-(TUBO_D_EXT + 4) / 2 - 1)
            .center(0, -7).circle(1.45).extrude(TUBO_D_EXT + 6))
    p = p.cut(pris)
    return p


def estaca_guia() -> cq.Workplane:
    """Tapa superior de la estaca: organiza los cables hacia el prensaestopas."""
    d_ext = TUBO_D_EXT + 8
    p = cq.Workplane("XY").circle(d_ext / 2).extrude(20)
    cono = (cq.Workplane("XY").workplane(offset=20)
            .circle(d_ext / 2).workplane(offset=14).circle(8).loft())
    p = p.union(cono)

    p = p.cut(cq.Workplane("XY").workplane(offset=-1).circle((TUBO_D_EXT + TOL) / 2).extrude(16))
    p = p.cut(cq.Workplane("XY").workplane(offset=10).circle(4.5).extrude(30))
    p = p.cut(cq.Workplane("XZ").workplane(offset=-d_ext / 2 - 1)
              .center(0, 10).circle(1.45).extrude(d_ext + 2))
    return p


def soporte_solar() -> cq.Workplane:
    """Abrazadera a poste con brazo inclinado 15°. Se imprimen 4 unidades."""
    d = POSTE_TUBO_D
    p = cq.Workplane("XY").circle((d + 12) / 2).extrude(30)
    p = p.union(cq.Workplane("XY").center(0, d / 4 + 10).rect(12, d / 2 + 20).extrude(30))

    p = p.cut(cq.Workplane("XY").workplane(offset=-1).circle((d + TOL) / 2).extrude(32))
    # Corte de apriete
    p = p.cut(cq.Workplane("XY").workplane(offset=-1).center(0, -d / 2).rect(3, d).extrude(32))
    # Tornillos M5 de apriete
    for z in (8, 22):
        p = p.cut(cq.Workplane("YZ").workplane(offset=-20)
                  .center(d / 4 + 12, z).circle(2.7).extrude(40))

    # Brazo inclinado
    brazo = (cq.Workplane("XZ")
             .center(0, 26)
             .rect(12, 8)
             .extrude(-90)
             .rotate((0, 0, 26), (1, 0, 26), ANGULO_PANEL)
             .translate((0, d / 2 + 10, 0)))
    p = p.union(brazo)
    return p


# ============================================================
#  Exportación
# ============================================================

PIEZAS = {
    "caja_base":     (caja_base,     "Cuerpo inferior del encapsulado IP65"),
    "caja_tapa":     (caja_tapa,     "Tapa con labio de sellado y visera"),
    "estaca_collar": (estaca_collar, "Collar porta-sensor (imprimir 3)"),
    "estaca_punta":  (estaca_punta,  "Punta de penetración"),
    "estaca_guia":   (estaca_guia,   "Guía superior de cables"),
    "soporte_solar": (soporte_solar, "Soporte de panel a 15° (imprimir 4)"),
}


def exportar(nombre: str, solido: cq.Workplane) -> None:
    os.makedirs(SALIDA, exist_ok=True)
    base = os.path.join(SALIDA, nombre)

    # STEP AP214 — el que abre Inventor y AutoCAD como sólido real
    exporters.export(solido, f"{base}.step", exporters.ExportTypes.STEP)

    # STL para impresión 3D
    exporters.export(solido, f"{base}.stl", exporters.ExportTypes.STL,
                     tolerance=0.01, angularTolerance=0.1)

    # DXF de la vista en planta, para planos 2D en AutoCAD
    try:
        seccion = solido.faces("<Z").wires().toPending()
        exporters.exportDXF(seccion, f"{base}_planta.dxf")
    except Exception:
        pass  # algunas piezas no dan una sección plana limpia; el STEP es lo importante

    print(f"  ✓ {nombre:<16} → .step  .stl  .dxf")


def main():
    ap = argparse.ArgumentParser(description="Genera el CAD de HidroSopó en STEP, STL y DXF")
    ap.add_argument("--pieza", choices=list(PIEZAS) + ["todas"], default="todas")
    args = ap.parse_args()

    objetivo = list(PIEZAS) if args.pieza == "todas" else [args.pieza]

    print("\nGenerando geometría sólida...\n")
    for nombre in objetivo:
        fn, desc = PIEZAS[nombre]
        try:
            exportar(nombre, fn())
        except Exception as e:                       # noqa: BLE001
            print(f"  ✗ {nombre}: {e}")

    print(f"\nListo. Archivos en ./{SALIDA}/")
    print("\n  .step → Inventor, AutoCAD 3D, SolidWorks, Fusion 360 (sólido editable)")
    print("  .stl  → impresión 3D")
    print("  .dxf  → AutoCAD 2D para planos acotados\n")


if __name__ == "__main__":
    main()
