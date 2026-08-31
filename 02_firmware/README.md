# Firmware — HidroSopó

## Instalación del entorno

```bash
pip install platformio
# o instala la extensión "PlatformIO IDE" en VS Code
```

## Compilar y cargar

```bash
cd 02_firmware
pio run                 # compila
pio run -t upload       # carga al ESP32
pio device monitor      # ver el serial
```

## Los tres firmwares

| Archivo | Dispositivo | Notas |
|---|---|---|
| `src/main.cpp` | Nodo de suelo | Deep sleep, batería + solar |
| `src/gateway.cpp.txt` | Gateway | Alimentación de red, siempre despierto |
| `src/nodo_caudal.cpp.txt` | Nodo de caudal | Light sleep, cuenta pulsos continuamente |

Los `.txt` están así para que PlatformIO no intente compilar los tres a la vez. Para usarlos, crea un proyecto aparte por dispositivo (recomendado) o usa `build_src_filter` en `platformio.ini`.

## Orden de puesta en marcha

1. **Prueba de mesa con WiFi.** Pon `TRANSPORTE_WIFI` en `config.h`, conecta un solo sensor de humedad, verifica que llegue el JSON al backend. Sin esto, no sigas.
2. **Agrega sensores uno por uno.** Si agregas los seis de una y algo falla, no sabes cuál es.
3. **Cambia a LoRa.** Prueba primero a 2 metros de distancia, luego a 50 m, luego en campo.
4. **Prueba de deep sleep.** Verifica con el monitor que despierte cada 15 min y que el consumo baje. Si no baja de 1 mA, algún periférico quedó energizado.
5. **Prueba de 72 h con batería sola** (sin panel) antes de instalar en campo.

## Errores que vas a cometer (para que no los cometas)

- **ADC2 con WiFi:** en ESP32 los pines del ADC2 devuelven basura cuando el WiFi está activo. Por eso los sensores de humedad van en GPIO 1, 2, 3 (ADC1).
- **Energizar el LoRa sin antena:** quema el SX1262. Conecta la antena antes de dar corriente. Siempre.
- **Olvidar el pull-up del DS18B20:** sin la resistencia de 4.7 kΩ entre DATA y 3V3, lees -127 °C.
- **No poner pull-down en el gate del MOSFET:** en deep sleep el pin queda flotando y el MOSFET conduce parcialmente, drenando la batería.
- **Confiar en `MM_POR_PULSO = 0.28`:** verifica tu cangilón vertiendo un volumen conocido.
- **Dejar `setInsecure()` en producción:** para el piloto está bien, pero documenta en el informe que en despliegue real hay que cargar el certificado raíz. El jurado lo puede preguntar.

## Consumo esperado

| Modo | Corriente |
|---|---|
| Deep sleep (nodo suelo) | < 30 µA |
| Midiendo | ~65 mA por 5 s |
| TX LoRa | ~120 mA por 0.4 s |

Si tu deep sleep está por encima de 200 µA, revisa: MOSFET flotando, LED de la placa encendido, o el regulador de la placa (algunos clones tienen reguladores con consumo quiescente alto).
