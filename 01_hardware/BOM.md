# Lista de Materiales (BOM) — HidroSopó

Precios referenciales del mercado colombiano (verificar antes de comprar: Sigma Electrónica, Vistrónica, Didácticas Electrónicas, i+D Electrónica, MercadoLibre CO).

## NODO DE SUELO (el principal)

| # | Componente | Especificación | Cant | COP unit | Subtotal | Notas |
|---|---|---|---|---|---|---|
| 1 | Heltec WiFi LoRa 32 V3 | ESP32-S3 + SX1262 915 MHz + OLED | 1 | 175.000 | 175.000 | Alternativa: ESP32 DevKit + módulo RA-01H |
| 2 | Sensor humedad suelo capacitivo v2.0 | Salida analógica 0–3V | 3 | 12.000 | 36.000 | Comprar 5, vienen con dispersión |
| 3 | DS18B20 waterproof | Temp. suelo, 1-Wire, cable 1 m | 2 | 14.000 | 28.000 | Uno a 15 cm, otro a 40 cm |
| 4 | SHT31-D | Temp/HR aire I2C ±0.3°C | 1 | 38.000 | 38.000 | Mejor que DHT22, no deriva |
| 5 | Pluviómetro de cangilones | Reed switch, 0.28 mm/pulso | 1 | 85.000 | 85.000 | Se puede imprimir en 3D si no hay presupuesto |
| 6 | Panel solar 10 W 12 V | Policristalino | 1 | 45.000 | 45.000 | |
| 7 | CN3791 MPPT 12V→Li-ion | Cargador solar con MPPT | 1 | 22.000 | 22.000 | Mejor que TP4056 con panel |
| 8 | Celdas 18650 3000 mAh | Li-ion protegidas | 2 | 18.000 | 36.000 | En paralelo = 6000 mAh |
| 9 | Portapilas 18650 x2 | Paralelo con cables | 1 | 6.000 | 6.000 | |
| 10 | Antena 915 MHz SMA | Ganancia 3 dBi | 1 | 18.000 | 18.000 | |
| 11 | Resistencia 4.7 kΩ | Pull-up 1-Wire | 2 | 200 | 400 | |
| 12 | MOSFET IRLZ44N + resist. | Corte de alimentación a sensores | 1 | 3.500 | 3.500 | Clave para ahorro de batería |
| | | | | **Subtotal** | **~493.000** | |

## NODO DE CAUDAL (el regulatorio — no lo omitas)

| # | Componente | Especificación | Cant | COP unit | Subtotal |
|---|---|---|---|---|---|
| 1 | Heltec WiFi LoRa 32 V3 | ESP32-S3 + LoRa | 1 | 175.000 | 175.000 |
| 2 | Caudalímetro YF-S201 | 1/2", 1–30 L/min, pulsos | 1 | 32.000 | 32.000 |
| | *o* Caudalímetro YF-B10 | 1", bronce, 1–100 L/min | 1 | 88.000 | 88.000 |
| 3 | Panel solar 6 W + CN3791 | | 1 | 55.000 | 55.000 |
| 4 | 18650 3000 mAh + porta | | 1 | 24.000 | 24.000 |
| 5 | Adaptadores/uniones PVC | Según diámetro de la tubería | 1 | 25.000 | 25.000 |
| | | | | **Subtotal** | **~311.000** |

> **Elegir el caudalímetro:** mide el diámetro real de la tubería de la captación antes de comprar. Si es de 1", el YF-S201 de 1/2" te estrangula el flujo y el productor te lo va a reclamar. Ante la duda, el YF-B10.

## GATEWAY (en la casa de la finca)

| # | Componente | Cant | COP unit | Subtotal |
|---|---|---|---|---|
| 1 | Heltec WiFi LoRa 32 V3 | 1 | 175.000 | 175.000 |
| 2 | Fuente 5 V 2 A | 1 | 15.000 | 15.000 |
| 3 | Caja plástica pequeña | 1 | 12.000 | 12.000 |
| | | | **Subtotal** | **~202.000** |

## ENCAPSULADO Y MONTAJE

| # | Componente | Cant | COP unit | Subtotal |
|---|---|---|---|---|
| 1 | Caja estanca IP65 158×90×60 mm | 3 | 28.000 | 84.000 |
| 2 | Prensaestopas PG7/PG9 | 12 | 1.500 | 18.000 |
| 3 | Silicona neutra + resina epóxica | 1 | 35.000 | 35.000 |
| 4 | Tubo PVC 1/2" (estacas) 3 m | 2 | 9.000 | 18.000 |
| 5 | Cable multipar apantallado 4×22AWG | 15 m | 2.500 | 37.500 |
| 6 | Bolsas de sílica gel | 10 | 500 | 5.000 |
| 7 | Abrazaderas, tornillería, amarres UV | 1 | 25.000 | 25.000 |
| 8 | Filamento PETG 1 kg (impresión 3D) | 1 | 95.000 | 95.000 |
| | | | **Subtotal** | **~317.500** |

## HERRAMIENTA Y CONSUMIBLES (si no se tiene)

| Componente | COP |
|---|---|
| Multímetro | 45.000 |
| Cautín + estaño + flux | 60.000 |
| Termorretráctil surtido | 15.000 |
| Balanza de precisión 0.01 g (calibración gravimétrica) | 55.000 |
| **Subtotal** | **~175.000** |

---

## RESUMEN

| Bloque | COP |
|---|---|
| Nodo de suelo | 493.000 |
| Nodo de caudal | 311.000 |
| Gateway | 202.000 |
| Encapsulado y montaje | 317.500 |
| Herramienta | 175.000 |
| **Subtotal** | **1.498.500** |
| Contingencia 15% | 225.000 |
| **TOTAL** | **≈ 1.723.500 COP** |

## VERSIÓN ECONÓMICA (~$850.000)

Si el presupuesto no da:

- ESP32 DevKit V1 ($28.000) + módulo LoRa RA-01H ($35.000) en vez de Heltec → ahorra ~$110.000 por nodo
- 1 sensor de humedad en vez de 3 → ahorra $24.000 (pero pierdes el perfil por profundidad)
- DHT22 ($14.000) en vez de SHT31 → ahorra $24.000 (pero deriva con el tiempo)
- Pluviómetro impreso en 3D → ahorra $85.000
- Reutilizar 18650 de baterías de portátil viejas → ahorra $36.000

**Lo que NUNCA recortes:** el caudalímetro. Sin él no hay evidencia de ahorro y el proyecto no cumple su objetivo declarado.

## SOFTWARE Y SERVICIOS

| Servicio | Costo |
|---|---|
| PlatformIO / Arduino IDE | $0 |
| Python + FastAPI + scikit-learn | $0 |
| PostgreSQL (Supabase free) | $0 |
| Hosting API (Render free / Oracle Always Free) | $0 |
| Open-Meteo API | $0, sin llave |
| Telegram Bot API | $0 |
| WhatsApp (vía CallMeBot o Twilio sandbox) | $0 con límites |
| GitHub | $0 |
| OpenSCAD / FreeCAD / KiCad | $0 |
| **Total software** | **$0** |
