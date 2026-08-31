# Calibración Gravimétrica de Sensores de Humedad

Este procedimiento es lo que convierte "valores ADC" en "% de humedad volumétrica". Sin esto, tu proyecto reporta números sin significado físico y el jurado lo va a notar.

Tiempo: una tarde. Costo: una balanza de $55.000.

## Materiales

- Balanza de precisión (0.01 g)
- Horno o estufa (105 °C)
- 5 recipientes plásticos idénticos de ~500 ml
- Suelo del predio piloto (no de otro lado — la textura cambia la curva)
- Agua destilada o de lluvia
- Los sensores a calibrar, ya conectados al ESP32

## Procedimiento

### Paso 1 — Puntos de referencia (los dos extremos)

1. **Seco al aire:** sensor al aire libre, sin tocar nada. Anota el valor ADC. Este es `ADC_seco` (típico 2800–3200).
2. **Sumergido en agua:** hasta la línea marcada, sin mojar la electrónica. Anota `ADC_agua` (típico 1200–1500).

Con esto ya tienes una calibración burda de 2 puntos. Suficiente para la demo, insuficiente para el informe.

### Paso 2 — Calibración real de 5 puntos

1. Seca 3 kg de suelo del predio en horno a **105 °C por 24 h**. Este es tu suelo de referencia con humedad 0%.
2. Prepara 5 muestras de 400 g de suelo seco cada una.
3. Agrega agua a cada una para lograr contenidos gravimétricos crecientes:

| Muestra | Agua a agregar | θ gravimétrico objetivo |
|---|---|---|
| A | 0 ml | 0% |
| B | 40 ml | 10% |
| C | 80 ml | 20% |
| D | 120 ml | 30% |
| E | 160 ml | 40% |

4. Mezcla bien, sella en bolsa y **deja reposar 24 h** para que la humedad se distribuya uniformemente. Si mides de una, mides gradientes.
5. Empaca cada muestra en el recipiente con una **densidad aparente similar a la del campo** (compacta con golpes suaves, siempre igual). Mide y anota la densidad aparente ρb = masa_suelo_seco / volumen_recipiente. Típico en suelos de la Sabana: 1.0–1.3 g/cm³.
6. Inserta el sensor en el centro de cada muestra, espera 60 s, anota el ADC promedio de 20 lecturas.

### Paso 3 — Convertir a humedad volumétrica

```
θ_volumétrico (%) = θ_gravimétrico (%) × ρb
```

Ejemplo: 20% gravimétrico con ρb = 1.15 g/cm³ → θv = 23%.

### Paso 4 — Ajustar la curva

Con los 5 pares (ADC, θv), ajusta un polinomio de grado 2 o 3. El script está en `03_backend/ia/calibracion.py`:

```bash
python calibracion.py --sensor S1 --datos 3050,0 2740,11.5 2380,23.0 2010,34.5 1720,46.0
```

Salida:
```
Sensor S1 — Polinomio grado 2
theta_v = a*adc^2 + b*adc + c
a = 1.842e-05  b = -1.4102e-01  c = 2.6394e+02
R² = 0.9971
```

Ese R² va en tu informe y en tu póster. Es la prueba de rigor metodológico.

### Paso 5 — Guardar en el sistema

Los coeficientes se cargan en `03_backend/config_sensores.json`:

```json
{
  "S1": {"a": 1.842e-05, "b": -0.14102, "c": 263.94, "r2": 0.9971, "profundidad_cm": 15},
  "S2": {"a": 1.901e-05, "b": -0.14550, "c": 271.20, "r2": 0.9958, "profundidad_cm": 30},
  "S3": {"a": 1.788e-05, "b": -0.13890, "c": 259.11, "r2": 0.9963, "profundidad_cm": 45}
}
```

**Calibra cada sensor por separado.** Dos sensores capacitivos del mismo lote pueden diferir 15% entre sí. Ese es el chiste de tener 3.

---

## Determinar Capacidad de Campo y Punto de Marchitez

El motor de riego necesita estos dos valores. Hay dos rutas:

### Ruta A — Medición en campo (mejor, gratis, 3 días)

1. Riega abundantemente un área de 2×2 m alrededor de los sensores hasta saturar.
2. Cubre con plástico (evita la evaporación, no la percolación).
3. Registra la humedad cada hora durante 48 h.
4. **Capacidad de campo (CC)** = el valor donde la curva se aplana, típicamente a las 24–48 h.

Esta gráfica es excelente material para el póster.

### Ruta B — Estimación por textura (rápida, aceptable)

| Textura | CC (θv %) | PMP (θv %) | Agua disponible |
|---|---|---|---|
| Arenosa | 12 | 5 | 7% |
| Franco-arenosa | 20 | 9 | 11% |
| **Franca** | **28** | **13** | **15%** |
| **Franco-arcillosa** | **34** | **19** | **15%** |
| Arcillosa | 40 | 25 | 15% |

Los suelos de la Sabana de Bogotá son predominantemente **francos a franco-arcillosos**, con contenidos altos de materia orgánica. Empieza con CC=30%, PMP=15% y ajusta con la Ruta A cuando tengas datos.

Para la textura exacta, puedes hacer la **prueba del hidrómetro de Bouyoucos** en el laboratorio de la Uniagustiniana, o una prueba de campo por sedimentación en frasco (menos precisa pero sirve).

---

## Calibración del caudalímetro

No confíes en el factor de fábrica (7.5 pulsos/L/min para el YF-S201).

1. Conecta el caudalímetro a la tubería.
2. Prepara un recipiente de volumen conocido (balde de 20 L, verificado con probeta).
3. Pon el ESP32 a contar pulsos.
4. Llena el recipiente completo. Anota el total de pulsos.
5. Repite 5 veces a distintos caudales (llave a 1/4, 1/2, 3/4, abierta).

```
factor_pulsos_por_litro = total_pulsos / litros_reales
```

6. Promedia. Si la desviación entre caudales es >5%, ajusta una recta en vez de una constante.

Este número es el que sustenta todos los m³ que reportes. Que quede documentado con fotos en la bitácora.
