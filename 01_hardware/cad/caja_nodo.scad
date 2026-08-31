// ============================================================
//  HidroSopó — Encapsulado del nodo sensor (IP65)
//  OpenSCAD paramétrico. Licencia: CC BY 4.0
//  Imprimir en PETG o ASA (NO PLA: se deforma al sol de la Sabana)
// ============================================================
//  Uso:
//    Abrir en OpenSCAD (gratis, openscad.org)
//    Cambiar 'pieza' abajo para exportar cada parte por separado
//    F6 para renderizar, luego Exportar como STL
// ============================================================

pieza = "todo";   // "base" | "tapa" | "todo" | "corte"

// ---------- PARÁMETROS ----------
ancho      = 150;   // X interior
largo      = 100;   // Y interior
alto       = 60;    // Z interior
pared      = 3;     // espesor de pared
r_esq      = 8;     // radio de esquina
h_tapa     = 8;     // altura del labio de la tapa

// Junta tórica / sello
canal_ancho = 3.2;  // para cordón de silicona de 3 mm
canal_prof  = 2.0;

// Prensaestopas
pg7_d   = 12.5;     // diámetro de rosca PG7
pg9_d   = 15.5;     // PG9
n_pg7   = 4;        // cantidad en la cara inferior

// Tornillos M3 de cierre
tornillo_d   = 3.4;
inserto_d    = 4.2;  // para inserto roscado térmico M3
inserto_h    = 6;

// Postes de montaje de la PCB
pcb_ancho = 51;      // Heltec V3 ≈ 51 x 26 mm
pcb_largo = 26;
poste_h   = 8;

$fn = 48;

// ---------- MÓDULOS AUXILIARES ----------

module caja_redondeada(x, y, z, r) {
    hull() for (i = [-1, 1], j = [-1, 1])
        translate([i*(x/2 - r), j*(y/2 - r), 0])
            cylinder(h = z, r = r);
}

module postes_pcb() {
    for (i = [-1, 1], j = [-1, 1])
        translate([i*pcb_ancho/2, j*pcb_largo/2, pared])
            difference() {
                cylinder(h = poste_h, d = 7);
                translate([0,0,poste_h - inserto_h])
                    cylinder(h = inserto_h + 0.1, d = inserto_d);
            }
}

module orejas_montaje() {
    // 2 orejas laterales para amarrar a la estaca con abrazaderas
    for (s = [-1, 1])
        translate([s*(ancho/2 + pared), 0, 0])
            difference() {
                hull() {
                    translate([0,0,alto*0.25]) cylinder(h=8, d=16);
                    translate([-s*4,0,alto*0.25]) cube([8,16,8], center=true);
                }
                translate([0,0,alto*0.25 - 1]) cylinder(h = 12, d = 5.5);
            }
}

// ---------- BASE ----------

module base() {
    difference() {
        union() {
            // cuerpo exterior
            caja_redondeada(ancho + 2*pared, largo + 2*pared, alto, r_esq + pared);
            orejas_montaje();
        }

        // cavidad interior
        translate([0, 0, pared])
            caja_redondeada(ancho, largo, alto, r_esq);

        // canal de sello en el borde superior
        translate([0, 0, alto - canal_prof])
            difference() {
                caja_redondeada(ancho + pared + canal_ancho/2, largo + pared + canal_ancho/2,
                                canal_prof + 1, r_esq + pared);
                translate([0,0,-0.5])
                    caja_redondeada(ancho + pared - canal_ancho/2, largo + pared - canal_ancho/2,
                                    canal_prof + 2, r_esq + pared);
            }

        // agujeros para prensaestopas en la cara inferior (cables de sensores)
        for (i = [0 : n_pg7 - 1])
            translate([-ancho/2 + 22 + i*(ancho - 44)/(n_pg7 - 1), -largo/2 - pared - 1, alto*0.35])
                rotate([-90, 0, 0])
                    cylinder(h = pared + 2, d = pg7_d);

        // prensaestopa PG9 para cable del panel solar (cara superior lateral)
        translate([ancho/2 + pared + 1, 0, alto*0.6])
            rotate([0, -90, 0])
                cylinder(h = pared + 2, d = pg9_d);

        // paso de antena SMA
        translate([-ancho/2 - pared - 1, largo/4, alto*0.6])
            rotate([0, 90, 0])
                cylinder(h = pared + 2, d = 6.5);

        // insertos M3 en las 4 esquinas
        for (i = [-1, 1], j = [-1, 1])
            translate([i*(ancho/2 - 2), j*(largo/2 - 2), alto - inserto_h])
                cylinder(h = inserto_h + 1, d = inserto_d);

        // drenaje: micro-orificio inferior (deja salir condensado, no entra agua a presión)
        translate([0, 0, -1]) cylinder(h = pared + 2, d = 1.5);
    }

    postes_pcb();

    // riel para la bolsa de sílica gel
    translate([0, largo/2 - 10, pared])
        difference() {
            cube([60, 6, 12], center = false);
            translate([2, -1, 2]) cube([56, 8, 12]);
        }
}

// ---------- TAPA ----------

module tapa() {
    difference() {
        union() {
            caja_redondeada(ancho + 2*pared, largo + 2*pared, pared, r_esq + pared);
            // labio que entra en la base
            translate([0, 0, -h_tapa + pared])
                caja_redondeada(ancho - 0.4, largo - 0.4, h_tapa, r_esq);
            // visera contra lluvia y sol directo
            translate([0, -largo/2 - pared, 0])
                hull() {
                    cube([ancho + 2*pared, 1, pared], center = false);
                    translate([0, -14, 6]) cube([ancho + 2*pared, 1, pared]);
                }
        }
        // cavidad del labio
        translate([0, 0, -h_tapa + pared - 0.1])
            caja_redondeada(ancho - 2*pared, largo - 2*pared, h_tapa, r_esq);

        // paso de tornillos M3
        for (i = [-1, 1], j = [-1, 1])
            translate([i*(ancho/2 - 2), j*(largo/2 - 2), -1])
                cylinder(h = pared + 2, d = tornillo_d);
        // avellanado
        for (i = [-1, 1], j = [-1, 1])
            translate([i*(ancho/2 - 2), j*(largo/2 - 2), pared - 1.8])
                cylinder(h = 2, d1 = tornillo_d, d2 = 6.5);

        // ventana para el OLED del Heltec (sellar con acrílico + silicona)
        translate([0, 0, -1]) cube([26, 14, pared + 2], center = true);

        // texto grabado
        translate([0, largo/2 - 12, pared - 0.6])
            linear_extrude(1) text("HidroSopo", size = 9, halign = "center", font = "Liberation Sans:style=Bold");
    }
}

// ---------- RENDER ----------

if (pieza == "base")  base();
if (pieza == "tapa")  translate([0,0,0]) rotate([180,0,0]) tapa();
if (pieza == "todo") {
    base();
    translate([0, 0, alto + 25]) tapa();
}
if (pieza == "corte") {
    difference() {
        union() { base(); translate([0,0,alto + 2]) tapa(); }
        translate([-500, 0, -50]) cube([1000, 500, 500]);
    }
}
