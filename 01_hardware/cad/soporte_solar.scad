// ============================================================
//  HidroSopó — Soporte de panel solar
//  Inclinación 15° orientación sur (Sopó, lat 4.9° N)
//  El ángulo es para autolimpieza por lluvia, no para captación.
//  Imprimir en PETG/ASA. 4 unidades (uno por esquina del panel).
// ============================================================

angulo     = 15;
poste_d    = 33.4;   // tubo galvanizado 1" (verificar)
tol        = 0.4;
$fn = 48;

module abrazadera_poste() {
    difference() {
        union() {
            cylinder(h = 30, d = poste_d + 12);
            translate([-6, 0, 0]) cube([12, poste_d/2 + 20, 30]);
        }
        translate([0,0,-1]) cylinder(h = 32, d = poste_d + tol);
        // corte de apriete
        translate([-1.5, 0, -1]) cube([3, poste_d, 32]);
        // tornillos M5 de apriete
        for (z = [8, 22])
            translate([-20, poste_d/2 + 10, z]) rotate([0,90,0])
                cylinder(h = 40, d = 5.4);
    }
}

module brazo_inclinado() {
    rotate([angulo, 0, 0])
    difference() {
        union() {
            cube([12, 90, 8]);
            translate([0, 80, 0]) cube([12, 10, 22]);
        }
        // tornillos M6 al marco del panel
        for (y = [20, 55])
            translate([6, y, -1]) cylinder(h = 12, d = 6.4);
    }
}

module soporte() {
    abrazadera_poste();
    translate([-6, poste_d/2 + 10, 26]) brazo_inclinado();
}

soporte();
