// ============================================================
//  HidroSopó — Estaca de instalación de sensores de suelo
//  Sostiene 3 sensores capacitivos a 15 / 30 / 45 cm
//  y 2 DS18B20. Se inserta en la pared de la calicata.
//  Imprimir en PETG. 100% relleno en la punta.
// ============================================================

pieza = "todo";   // "guia" | "punta" | "collar" | "todo"

tubo_d_ext = 21.3;   // PVC 1/2" presión (verificar con calibrador)
tubo_d_int = 16.0;
sensor_w   = 24;     // ancho del sensor capacitivo v2.0
sensor_t   = 1.8;    // espesor de la PCB del sensor
tol        = 0.35;   // tolerancia de impresión

$fn = 64;

// ---------- COLLAR PORTA-SENSOR ----------
// Se desliza sobre el tubo PVC y sujeta un sensor apuntando hacia afuera.

module collar() {
    difference() {
        union() {
            cylinder(h = 34, d = tubo_d_ext + 8);
            // aleta que sujeta el sensor
            translate([tubo_d_ext/2 + 2, -sensor_w/2 - 3, 0])
                cube([10, sensor_w + 6, 34]);
        }
        // paso del tubo
        translate([0,0,-1]) cylinder(h = 36, d = tubo_d_ext + tol);

        // ranura del sensor
        translate([tubo_d_ext/2 + 5, -sensor_w/2 - tol/2, 4])
            cube([sensor_t + tol, sensor_w + tol, 34]);

        // tornillo prisionero M3 para fijar al tubo
        translate([0, tubo_d_ext/2 + 6, 17]) rotate([90,0,0])
            cylinder(h = 12, d = 2.9);

        // canal de cable
        translate([-tubo_d_ext/2 - 5, 0, 17]) rotate([0,90,0])
            cylinder(h = 8, d = 5);
    }
}

// ---------- PUNTA DE PENETRACIÓN ----------

module punta() {
    difference() {
        union() {
            cylinder(h = 40, d1 = tubo_d_ext + 4, d2 = 3);
            translate([0,0,-14]) cylinder(h = 15, d = tubo_d_ext + 4);
        }
        translate([0,0,-15]) cylinder(h = 16, d = tubo_d_ext + tol);
        // prisionero
        translate([0, tubo_d_ext/2 + 4, -7]) rotate([90,0,0])
            cylinder(h = 10, d = 2.9);
    }
}

// ---------- GUÍA SUPERIOR ----------
// Tapa el tubo, organiza los cables y se conecta al prensaestopas de la caja.

module guia() {
    difference() {
        union() {
            cylinder(h = 20, d = tubo_d_ext + 8);
            translate([0,0,20]) cylinder(h = 14, d1 = tubo_d_ext + 8, d2 = 16);
        }
        translate([0,0,-1]) cylinder(h = 16, d = tubo_d_ext + tol);
        translate([0,0,10]) cylinder(h = 30, d = 9);   // salida de cables
        translate([0, tubo_d_ext/2 + 6, 10]) rotate([90,0,0])
            cylinder(h = 12, d = 2.9);
    }
}

// ---------- ENSAMBLE ----------

if (pieza == "collar") collar();
if (pieza == "punta")  punta();
if (pieza == "guia")   guia();
if (pieza == "todo") {
    // vista de ensamble (el tubo es una referencia, no se imprime)
    color("gray", 0.3) translate([0,0,-500]) cylinder(h = 560, d = tubo_d_ext);
    translate([0,0,-510]) punta();
    for (z = [-450, -300, -150]) translate([0,0,z]) collar();   // 45 / 30 / 15 cm
    translate([0,0,20]) guia();
}
