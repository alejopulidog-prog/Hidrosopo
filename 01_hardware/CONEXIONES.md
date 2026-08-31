# Esquema de Conexiones — Nodo de Suelo (Heltec WiFi LoRa 32 V3)

## Pinout

```
                    ┌──────────────────────────┐
                    │   Heltec WiFi LoRa 32 V3 │
                    │        (ESP32-S3)        │
  Humedad #1  ──────┤ GPIO 1  (ADC1_CH0)       │
  Humedad #2  ──────┤ GPIO 2  (ADC1_CH1)       │
  Humedad #3  ──────┤ GPIO 3  (ADC1_CH2)       │
  DS18B20 DATA ─────┤ GPIO 4  (1-Wire)         │  + pull-up 4.7k a 3V3
  SHT31 SDA   ──────┤ GPIO 41 (I2C SDA)        │
  SHT31 SCL   ──────┤ GPIO 42 (I2C SCL)        │
  Pluviómetro ──────┤ GPIO 5  (RTC_GPIO, wake) │  + pull-up interno
  MOSFET gate ──────┤ GPIO 6  (power sensores) │
  Batería ADC ──────┤ GPIO 7  (divisor 2:1)    │
                    │                          │
                    │ SX1262 LoRa (interno)    │
                    │ SPI: 8,9,10,11,12,13,14  │  ← no usar estos pines
                    │ OLED: SDA 17, SCL 18     │  ← ni estos
                    └──────────────────────────┘
```

> **Ojo con el ADC2 del ESP32:** los pines del ADC2 no funcionan cuando el WiFi está activo. Por eso los tres sensores de humedad van en ADC1 (GPIO 1–10 en el S3). Es un error clásico que cuesta un día de depuración.

## Sensor de humedad capacitivo

```
   Sensor capacitivo v2.0
   ┌──────────┐
   │ VCC ─────┼──── Drain del MOSFET (alimentación conmutada)
   │ GND ─────┼──── GND común
   │ AOUT ────┼──── GPIO 1 / 2 / 3
   └──────────┘
```

**Sellado obligatorio:** la parte electrónica del sensor (arriba de la línea blanca) se cubre con **resina epóxica o termorretráctil con adhesivo**. Los sensores capacitivos baratos se dañan en semanas si entra humedad por ahí. Este paso es la diferencia entre un piloto de 4 meses y un piloto de 3 semanas.

## Alimentación conmutada de sensores (ahorro de batería)

```
        3V3 (regulado)
          │
          ├──────────────────► SHT31 (siempre, consume 0.2 µA en reposo)
          │
          │      ┌─────────┐
          └──────┤ S       │  IRLZ44N (N-channel, logic level)
                 │       D ├──────► VCC de los 3 sensores de humedad
   GPIO 6 ───────┤ G       │        y del DS18B20
                 └────┬────┘
                      │
                  10k a GND (pull-down, evita flotar en deep sleep)
```

Con esto los sensores solo consumen durante los ~2 segundos de la medición, no las 24 horas. Multiplica la autonomía por ~15.

## Medición de batería

```
   BAT+ ──┬── R1 100k ──┬── GPIO 7 (ADC)
          │             │
          │            R2 100k
          │             │
   GND ───┴─────────────┴── GND
```

Divisor 2:1 → V_bat = lectura_adc × 2 × (3.3 / 4095) × factor_calibracion

## Pluviómetro de cangilones

```
   Reed switch ──┬── GPIO 5 (con INPUT_PULLUP)
                 │
                GND
```

Cada bascula del cangilón cierra el reed → un pulso. Con el cangilón estándar de 0.28 mm, cada pulso = 0.28 mm de lluvia. **Debounce por software de 150 ms** (el reed rebota). GPIO 5 es RTC_GPIO, lo que permite despertar el ESP32 desde deep sleep para contar lluvia sin perder eventos.

## Nodo de caudal

```
   YF-S201
   ┌──────────┐
   │ Rojo ────┼──── 5V (o 3V3, funciona)
   │ Negro ───┼──── GND
   │ Amarillo ┼──── GPIO 5 (pulsos, INPUT_PULLUP)
   └──────────┘
```

Factor del YF-S201: **F = 7.5 × Q** (Hz, con Q en L/min). Es decir, `L/min = pulsos_por_segundo / 7.5`. Este factor **hay que calibrarlo** con una probeta de 5 L (el de fábrica tiene ±10% de error).

**El nodo de caudal NO duerme.** Usa un contador por interrupción y despierta el radio cada 15 min para reportar. El consumo es mayor, por eso lleva su propio panel.

## Instalación física de los sensores de humedad

```
   Superficie del suelo
   ══════════════════════════════
        │                        
     15 cm ──── Sensor #1  ← zona de raíces activas
        │       DS18B20 #1
        │
     30 cm ──── Sensor #2  ← zona radicular media
        │
     45 cm ──── Sensor #3  ← control de percolación profunda
                DS18B20 #2
```

**El sensor #3 es el que demuestra el ahorro.** Si detecta aumento de humedad después de un riego, significa que el agua se está yendo por debajo de la raíz — agua desperdiciada. Ese dato es oro para el informe y para el reporte PUEAA.

**Método de instalación:** abrir una calicata con barreno o pala, insertar los sensores lateralmente contra la pared **no perturbada** del hoyo, rellenar con el mismo suelo en el mismo orden de capas, compactando ligeramente. Si rellenas con suelo suelto, mides la humedad del relleno, no la del perfil real.

## Checklist antes de cerrar la caja

- [ ] Todas las soldaduras con termorretráctil
- [ ] Prensaestopas apretados y con silicona neutra en el cable
- [ ] Bolsa de sílica gel adentro
- [ ] Cabezal electrónico de cada sensor de humedad sellado con epóxica
- [ ] Antena LoRa conectada (**nunca energizar sin antena — quema el SX1262**)
- [ ] Prueba de aspersión con manguera durante 2 min antes de instalar en campo
- [ ] Etiqueta con nombre del proyecto, contacto y "equipo de investigación — no retirar"
