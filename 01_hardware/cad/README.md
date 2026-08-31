# Archivos CAD — HidroSopó

Hay **dos rutas de CAD**, y sirven para cosas distintas. Usa la que necesites.

| | `cad_solido.py` (CadQuery) | `*.scad` (OpenSCAD) |
|---|---|---|
| Geometría | **Sólido B-Rep** | Malla |
| Exporta | **STEP, STL, DXF** | STL, DXF |
| Inventor / AutoCAD | ✅ Sólido real, editable, acotable | ⚠️ Solo como malla |
| Impresión 3D | ✅ | ✅ |
| Ver rápido y tocar medidas | Requiere correr el script | ✅ Vista previa en vivo |

**Para Inventor y AutoCAD usa los STEP.** Ya están generados en `salida/`.

---

## Los archivos ya generados

En `salida/` hay 6 piezas × 3 formatos:

| Pieza | Qué es | Cantidad a fabricar |
|---|---|---|
| `caja_base` | Cuerpo inferior del encapsulado IP65 | 3 (nodo suelo, nodo caudal, gateway) |
| `caja_tapa` | Tapa con labio de sellado, visera y ventana OLED | 3 |
| `estaca_collar` | Collar porta-sensor sobre tubo PVC | 3 (uno por profundidad) |
| `estaca_punta` | Punta cónica de penetración | 1 |
| `estaca_guia` | Guía superior de cables | 1 |
| `soporte_solar` | Abrazadera a poste con inclinación 15° | 4 |

Verificación de los STEP generados (todos son sólidos únicos y válidos):

| Pieza | Sólidos | Caras | Aristas | Volumen |
|---|---:|---:|---:|---:|
| caja_base | 1 | 78 | 195 | 134.9 cm³ |
| caja_tapa | 1 | 40 | 176 | 64.9 cm³ |
| estaca_collar | 1 | 17 | 42 | 18.2 cm³ |
| estaca_guia | 1 | 9 | 17 | 12.5 cm³ |
| estaca_punta | 1 | 8 | 14 | 9.6 cm³ |
| soporte_solar | 1 | 15 | 51 | 33.3 cm³ |

Esquema STEP: **AP214 (AUTOMOTIVE_DESIGN)**, el más compatible.

---

## Abrir en Autodesk Inventor

1. **Archivo → Abrir** → selecciona el `.step`
2. En *Opciones de importación* elige **"Convertir en modelo"** (no "Referencia")
   — así queda como sólido editable dentro de Inventor, no como cuerpo enlazado.
3. Guarda como `.ipt`.

Ya puedes acotar, medir, hacer cortes, agregar operaciones y generar planos con
**Archivo → Nuevo → Dibujo (.idw)**.

> **Nota honesta:** el STEP trae la *geometría* final, no el *árbol de operaciones*.
> Inventor lo ve como un sólido resuelto, no como "extrusión → corte → redondeo".
> Puedes agregarle operaciones nuevas encima sin problema, pero no puedes editar la
> altura original de la extrusión desde el navegador de modelo.
>
> Si necesitas el árbol paramétrico dentro de Inventor, hay dos caminos:
> (a) cambiar el parámetro en `cad_solido.py` y regenerar el STEP — es más rápido de
> lo que suena; o (b) remodelar la pieza en Inventor usando el STEP como plantilla
> de referencia. La opción (a) es la que yo usaría.

## Abrir en AutoCAD

**Para 3D:**
```
Comando: IMPORT     (o IMPORTAR)
```
Selecciona el `.step`. Queda como sólido 3D nativo de AutoCAD.

**Para planos 2D:**
Los `.dxf` de `salida/` son las vistas en planta de cada pieza. Ábrelos directamente
(`Archivo → Abrir`) y acota encima. Es la ruta más rápida para armar el plano de taller.

## Otros programas

| Programa | Qué usar |
|---|---|
| Fusion 360 | STEP → *Insert → Insert Mesh* no; usa *Upload* del STEP |
| SolidWorks | STEP → abre nativo |
| FreeCAD | STEP → abre nativo, y es gratis |
| Onshape | STEP → *Import* |
| Cura / PrusaSlicer / Bambu | STL |

---

## Regenerar el CAD si cambias una medida

Esta es la ventaja real del enfoque por script: cambias un número y se regenera todo,
en los tres formatos, en segundos.

```bash
pip install cadquery
cd 01_hardware/cad
python cad_solido.py

# Solo una pieza:
python cad_solido.py --pieza caja_base
```

### Medidas que DEBES verificar con calibrador antes de fabricar

Están todas al inicio de `cad_solido.py`:

| Parámetro | Qué medir | Por qué importa |
|---|---|---|
| `TUBO_D_EXT` | Diámetro exterior de tu PVC de 1/2" | Varía entre Pavco y Gerfor; si no ajusta, el collar no entra o queda flojo |
| `PG7_D` / `PG9_D` | Rosca de tus prensaestopas | Si queda grande, entra agua |
| `PCB_ANCHO` / `PCB_LARGO` | Tu placa Heltec | Los postes no van a coincidir |
| `POSTE_TUBO_D` | El poste donde va el panel | |
| `TOL` | Tolerancia de tu impresora | 0.35 mm funciona en la mayoría de FDM; si las piezas quedan apretadas, sube a 0.45 |

**Imprime primero un solo collar** para verificar el ajuste antes de tirar los tres.

---

## Impresión 3D

| Pieza | Material | Capa | Relleno | Soportes |
|---|---|---|---|---|
| caja_base | PETG / ASA | 0.20 mm | 30% | No |
| caja_tapa | PETG / ASA | 0.20 mm | 30% | **Sí** (por la visera) |
| estaca_collar | PETG | 0.20 mm | 40% | No |
| estaca_punta | PETG | 0.20 mm | **100%** | No |
| estaca_guia | PETG | 0.20 mm | 30% | No |
| soporte_solar | PETG / ASA | 0.24 mm | 50% | No |

**No uses PLA.** A 2.600 m la radiación UV es intensa y una caja oscura al sol llega a
55–60 °C. El PLA empieza a deformarse ahí mismo. PETG aguanta ~80 °C; ASA aguanta calor
y UV. Si solo tienes PLA, píntala de blanco y ponla a la sombra, pero cuenta con
reemplazarla.

## Si no tienes impresora 3D

- Laboratorios y maker spaces universitarios (la Uniagustiniana tiene).
- Servicios en Bogotá: 3DPrints Colombia, Bogotá 3D, Treatstock.
- **Plan B sin impresión:** caja estanca comercial IP65 de ferretería (Legrand, Schneider
  o genérica) + prensaestopas comerciales. Los collares se reemplazan con abrazaderas
  plásticas y cinta autofundente. Funciona, se ve menos elegante, cuesta lo mismo.

---

## Los archivos OpenSCAD

`caja_nodo.scad`, `estaca_sensor.scad` y `soporte_solar.scad` siguen ahí. Son útiles
para ver la geometría rápido y jugar con las medidas en vivo (OpenSCAD renderiza
mientras editas). Pero **para entregar planos o llevar a Inventor, usa los STEP**.

