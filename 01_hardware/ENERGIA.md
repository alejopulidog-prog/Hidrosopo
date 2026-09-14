# Presupuesto Energético del Nodo

## Consumo por ciclo de medición

| Estado | Corriente | Duración | Carga (mAh) |
|---|---|---|---|
| Deep sleep | 0.020 mA | 14 min 45 s | 0.0049 |
| Despertar + estabilizar sensores | 45 mA | 2 s | 0.0250 |
| Lectura de sensores | 65 mA | 3 s | 0.0542 |
| Transmisión LoRa (SF9, 20 dBm) | 120 mA | 0.4 s | 0.0133 |
| Espera de ACK | 12 mA | 0.6 s | 0.0020 |
| **Total por ciclo (15 min)** | | | **≈ 0.099 mAh** |

## Consumo diario

```
96 ciclos/día × 0.099 mAh = 9.5 mAh/día
+ autodescarga de las celdas (~2%/mes) ≈ 4 mAh/día
+ consumo del regulador y quiescente ≈ 12 mAh/día
────────────────────────────────────────────
TOTAL ≈ 25.5 mAh/día
```

## Autonomía sin sol

```
Capacidad útil: 2 × 3000 mAh × 0.80 (profundidad de descarga segura) = 4800 mAh
Autonomía = 4800 / 25.5 ≈ 188 días
```

Sobra muchísimo. Pero ojo: **a 2600 m de altitud las noches de Sopó son frías** y por debajo de 0 °C el Li-ion pierde capacidad y no se debe cargar. En la práctica cuenta con 60–90 días reales. Sigue siendo de sobra.

## Generación solar

```
Panel 10 W en Sopó:
  Irradiación media Sabana de Bogotá ≈ 4.2 kWh/m²/día
  Horas sol pico ≈ 4.2 h
  Generación bruta = 10 W × 4.2 h = 42 Wh/día
  Con pérdidas (MPPT 85%, suciedad 10%, nubes 40% en temporada lluviosa):
  42 × 0.85 × 0.90 × 0.60 ≈ 19 Wh/día = 5.100 mAh/día a 3.7 V
```

Generas **200 veces** lo que consumes. El sistema está sobredimensionado a propósito: en temporada de lluvias en la Sabana puede haber 10 días seguidos con muy poca radiación, y prefieres que sobre.

> Podrías bajar a un panel de 3 W y una sola celda 18650 para reducir costo. Con panel de 3 W y 3000 mAh la autonomía sin sol sigue siendo ~94 días. Es una optimización válida si el presupuesto aprieta.

## Ángulo del panel solar

Sopó está a **latitud ≈ 4.9° N**. Para máxima captación anual, el ángulo óptimo es cercano a la horizontal, pero:

**Recomendación: 15° con orientación sur.**

No por captación (a 5° de latitud da casi igual), sino porque **necesitas que la lluvia lave el panel**. Un panel horizontal en una finca ganadera se cubre de polvo, hojas y excremento de aves en dos semanas y pierde 40% de rendimiento. Con 15° se autolimpia. El soporte CAD ya viene con ese ángulo.

## Nodo de caudal (no duerme)

| Estado | Corriente | Notas |
|---|---|---|
| ESP32 en light sleep con ISR activa | 3.5 mA | Debe contar pulsos continuamente |
| Transmisión cada 15 min | 120 mA × 0.4 s | |

```
Consumo diario ≈ 3.5 mA × 24 h + 96 × 0.013 mAh ≈ 85 mAh/día
Autonomía con 1×3000 mAh (80% DoD): 2400 / 85 ≈ 28 días sin sol
Generación panel 6 W: ~3.000 mAh/día
```

Suficiente, pero con menos margen. Si la captación queda a la sombra (bocatomas suelen estar entre árboles), **usa panel de 10 W también aquí** o pásale corriente de red si hay.

## Protecciones obligatorias

- **Diodo Schottky** en serie con el panel (evita descarga inversa nocturna). El CN3791 ya lo trae.
- **Fusible reseteable PTC 1 A** en el positivo de la batería.
- **BMS/protección** en las celdas 18650 (compra celdas protegidas, no las crudas).
- **Nunca energizar el módulo LoRa sin antena.** Quema la etapa de potencia del SX1262.
