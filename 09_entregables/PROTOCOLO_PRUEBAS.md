# Protocolo de pruebas — HidroSopó

Cinco pruebas de banco y campo que caben en **una semana** y cuestan casi nada.
Cada una tiene un criterio de aceptación, una planilla y dónde va el resultado
(`09_entregables/poster/config.json → "pruebas"`). Al cambiar ese archivo y correr
`python generar_poster.py`, el póster se actualiza solo.

> Regla de oro: en el póster y en los informes, **lo simulado se rotula como simulado y
> lo medido como medido**. Un dato real pequeño vale más que uno inflado, y ante el
> COMUC+CTeI es lo que te protege.

| # | Prueba | Tiempo | Costo extra | Criterio de aceptación |
|---|---|---|---|---|
| 0 | Software (automática) | 2 min | $0 | 101/102 pruebas aprobadas |
| 1 | Calibración gravimétrica | 2 días (casi todo es esperar el horno/sol) | ~$0 (balanza de cocina) | R² ≥ 0,90 por sensor |
| 2 | Conexión WiFi en el sitio | 72 h (corre sola) | $0 | ≥ 95 % de envíos exitosos |
| 3 | Autonomía energética | 72 h (corre sola) | $0 | ≥ 72 h sin red, batería ≥ 3,5 V al final |
| 4 | Caudalímetro vs. balde aforado | 1 hora | $0 (balde de 20 L) | error ≤ 5 % |
| 5 | Recomendación en campo | 3–5 días | $0 | el productor sigue la recomendación y se registra |

---

## 0. Software

```bash
cd 03_backend && pytest          # 102 pruebas: FAO-56, motor, agente, costos, PUEAA, modelo ML
```
Toma pantallazo del resultado: va al avance 2 como evidencia.

## 1. Calibración gravimétrica (la credencial de rigor)

Detalle completo en `01_hardware/CALIBRACION.md`. Versión rápida:

1. Saca ~1 kg de suelo del predio a la profundidad de los sensores. Sécalo al sol 2 días
   (o horno de cocina a 105 °C, 24 h).
2. En un recipiente de volumen conocido (V, en cm³), compacta el suelo seco, pésalo (m_seco).
3. Agrega agua en 6–8 pasos (ej. 50 mL cada vez), mezcla, espera 20 min, y en cada paso
   anota **peso** y **lectura ADC** de cada sensor.
4. Humedad volumétrica de cada paso: θv = (m − m_seco) / V × 100 (agua: 1 g = 1 cm³).
5. Ajusta la curva ADC → θv (un comando por sensor, pares `adc,theta`):

```bash
cd 03_backend && python -m ia.calibracion --sensor S1 --profundidad 15 \
    --datos 3120,0 2980,4.1 2810,8.3 2650,12.4 2470,16.6 2300,20.8 2150,25.0
```
Imprime el R² y lo guarda en `config_sensores.json`, que el backend usa en vivo.

**Planilla:**

| Paso | Peso (g) | θv (%) | ADC S1 | ADC S2 | ADC S3 |
|---|---|---|---|---|---|
| 0 (seco) | | 0 | | | |
Resultado al póster: `"calibracion": {"resultado": "R² = 0,96 / 0,94 / 0,95", "estado": "ok"}`

## 2. Conexión WiFi en el sitio de instalación

1. Con el nodo en su **posición final** y el router de la finca encendido, déjalo operar 72 h en su ciclo normal (cada 15 min).
2. La plataforma guarda cada envío: `GET /api/v1/predios/{id}/series`. Cuenta los envíos recibidos frente a los esperados (≈ 288 en 72 h).
3. Si falla, en este orden: acercar el nodo al router, usar un repetidor o antena exterior, o activar LoRa (`config.h → TRANSPORTE_LORA`) y agregar la pasarela.

| Ventana | Esperados | Recibidos | % entrega | Lecturas guardadas en buffer y reenviadas |
|---|---|---|---|---|
| 72 h | 288 | | | |

## 3. Autonomía energética

Batería cargada al 100 %, panel **desconectado**, nodo en su ciclo normal (deep sleep,
15 min). La plataforma registra `v_bateria` en cada envío: a las 72 h exporta la curva.
Criterio: sigue transmitiendo y V ≥ 3,5 V. Si pasa, la autonomía calculada (≥ 8 días de diseño,
`01_hardware/ENERGIA.md`) queda respaldada por una medición.

## 4. Caudalímetro vs. balde aforado

1. Instala el caudalímetro en la manguera o tubería.
2. Llena un balde de 20 L **cinco veces**, cronometrando. Anota los litros que reporta el nodo.
3. Error = (L_nodo − 20) / 20 × 100. Si el error es constante, corrige el factor de pulsos
   (`02_firmware/src/nodo_caudal.cpp.txt → PULSOS_POR_LITRO`, de fábrica 450) y repite una vez.

| Llenado | Litros reales | Litros nodo | Error % | Tiempo (s) |
|---|---|---|---|---|
| 1 | 20 | | | |

## 5. Recomendación en campo (la prueba que cuenta la historia)

Durante 3–5 días el productor consulta la app cada mañana. Por cada día anota:
recomendación del sistema, qué hizo él, y si llovió. Al final, una encuesta de 5 preguntas
(¿la entendió?, ¿le sirvió?, ¿la seguiría?, ¿qué cambiaría?, ¿la recomendaría?).
Es corta, pero es **evidencia de uso real**, y el jurado la valora.

---

## Qué es simulación y qué es medición (para no confundir)

| Resultado | Origen hoy | Cómo se vuelve medido |
|---|---|---|
| Curvas de humedad | gemelo digital (`06_datos/datos_sinteticos.csv`) | exportar el CSV de la plataforma y ponerlo en `config.json → csv_sensores` |
| Ahorro de agua 35 % | escenario FAO-56, 50 climas (`06_datos/escenario_ahorro.py`) | caudalímetro: línea base vs. período con sistema |
| Métricas del modelo IA | entrenado con datos simulados | `python -m ia.modelo_ml --csv <tu_csv_real>` |
| 101/102 pruebas de software | **real** | — |
| Calibración, conexión WiFi, autonomía, caudal | pendiente | este protocolo |
