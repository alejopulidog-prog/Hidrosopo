# Póster Científico — estructura y contenido

El póster es el producto final que marcaste en la propuesta FOES. Este documento es el
guion: qué va en cada bloque, con qué datos, y qué errores evitar.

**Formato estándar:** 90 × 120 cm vertical. Impresión en Bogotá: ~$50.000–70.000 COP.

---

## Regla de oro del póster

Un póster no es un informe pegado en una pared. Es un **anzuelo visual**: alguien que
pasa a 3 metros debe entender de qué se trata en 5 segundos, y si le interesa, se acerca.

- **Texto total: menos de 800 palabras.** En serio.
- **60% del área debe ser visual**: gráficas, fotos, diagramas.
- Título legible desde 3 m (≥ 72 pt). Cuerpo legible desde 1 m (≥ 24 pt).
- Nada de párrafos largos. Viñetas y frases cortas.

---

## Diagramación (90 × 120 cm)

```
┌──────────────────────────────────────────────────────────┐
│  TÍTULO (2 líneas máximo, 90 pt)                         │
│  Autor · Programa · Universidad · Logos                  │  ← 12 cm
├──────────────────┬───────────────────┬───────────────────┤
│ 1. PROBLEMA      │ 3. ARQUITECTURA   │ 5. RESULTADOS     │
│    + foto        │    (el diagrama)  │    (las gráficas) │
│                  │                   │                   │
├──────────────────┤                   │                   │  ← 3 columnas
│ 2. OBJETIVO      │ 4. METODOLOGÍA    │ 6. AHORRO         │     de ~28 cm
│                  │    + fotos campo  │    (el número     │
│                  │                   │     grande)       │
├──────────────────┴───────────────────┴───────────────────┤
│  7. CONCLUSIONES        │  8. Referencias · QR al repo   │  ← 14 cm
└──────────────────────────────────────────────────────────┘
```

---

## Bloque por bloque

### Título
No uses el título administrativo largo. Usa uno que se entienda:

> **HidroSopó: ¿cuánta agua se ahorra cuando el suelo puede hablar?**
> Monitoreo IoT e inteligencia artificial para riego en fincas de Sopó

Debajo, en 32 pt: nombre, Ingeniería Mecatrónica, Uniagustiniana, y "Proyecto FOES —
Municipio de Sopó, 2026". Logos de la universidad y la Alcaldía.

### 1. Problema (~80 palabras + 1 foto)
La foto: el predio piloto, con el productor si autorizó. Una foto real vale más que
cualquier gráfico de barras aquí.

Texto: en Sopó las pequeñas fincas de pastoreo y los predios agrícolas menores riegan
por intuición. No por descuido: las tecnologías de monitoreo cuestan más de lo que
pueden pagar. Sin medir, no se puede mejorar.

### 2. Objetivo (~40 palabras)
Una sola frase, en grande. El objetivo general de la propuesta, resumido.

### 3. Arquitectura (el diagrama, sin texto largo)
Reusa el diagrama del plan maestro, redibujado limpio. Sensores → ESP32 → LoRa →
gateway → nube → IA → celular del productor.

**Etiqueta cada sensor con lo que mide y a qué profundidad.** Esa especificidad es lo
que distingue un póster de ingeniería de uno de feria escolar.

### 4. Metodología (~120 palabras + 3 fotos)
Fotos: montaje del nodo, calibración gravimétrica, instalación en campo.

Puntos clave a mencionar:
- Calibración gravimétrica de los sensores (con tu R², es tu credencial de rigor)
- Balance hídrico FAO-56 con Kc por cultivo
- Modelo `GradientBoostingRegressor` entrenado con datos del predio
- Línea base de N semanas antes de la intervención

### 5. Resultados (2–3 gráficas, poco texto)

**Gráfica 1 — Humedad por profundidad, 4 semanas.** Con líneas verticales marcando
riegos y lluvias, y una línea horizontal en el umbral de riego. Esta gráfica cuenta
toda la historia del proyecto.

**Gráfica 2 — Consumo diario: línea base vs. período con sistema.** Barras de dos
colores. Es la gráfica que justifica el proyecto.

**Gráfica 3 — Desempeño del modelo ML.** Predicho vs. real, con la línea diagonal
ideal. Y en un recuadro, la comparación honesta:

| | MAE |
|---|---|
| Modelo | X % vol |
| Línea base (persistencia) | Y % vol |
| Mejora | Z % |

> **Este recuadro te va a diferenciar de todos los demás pósters.** Comparar contra
> una línea base es lo que hace un investigador; decir "usamos IA" sin comparar es lo
> que hace todo el mundo. Si tu modelo no le gana a la persistencia, ponlo igual y
> explica por qué: eso es honestidad metodológica y el jurado técnico lo reconoce.

### 6. El número grande

Un solo dato, enorme, imposible de ignorar:

```
        ██  ██   %
        de reducción en el consumo de agua
        ██ ██ m³ ahorrados en N semanas
```

Si el ahorro fue menor al esperado, ponlo igual con el contexto. Un dato real pequeño
vale más que uno inflado.

### 7. Conclusiones (4 viñetas, máximo)
Una debe ser una limitación honesta. Todos los pósters tienen conclusiones triunfales;
el que reconoce sus límites se ve más serio, no menos.

Ejemplos de limitación válida: cobertura de datos del X%, el modelo requiere más tiempo
de entrenamiento, la validación fue en un solo predio y una sola temporada.

### 8. Pie
Referencias (máximo 5, formato APA), QR al repositorio de GitHub, y tus datos de contacto.

El QR es importante: quien se interese puede llevarse todo el proyecto.

---

## Herramientas para hacerlo

| Herramienta | Costo | Nota |
|---|---|---|
| **Canva** | Gratis | Plantillas de póster científico. Lo más rápido |
| **Inkscape** | Gratis | Control total, vectorial |
| PowerPoint | — | Configura la diapositiva a 90×120 cm. Funciona bien |
| LaTeX (beamerposter) | Gratis | Si quieres verte muy académico |

**Exportar siempre a PDF con imágenes a 300 dpi.** Un póster con fotos pixeladas se ve
mal a un metro de distancia.

---

## Paleta sugerida

Los mismos colores del dashboard, para que todo el proyecto se vea coherente:

| Uso | Color |
|---|---|
| Tinta / texto | `#12211c` |
| Agua / datos principales | `#1c6e8c` |
| Acento tierra | `#8a6a3f` |
| Alerta | `#c9702a` |
| Fondo | `#f6f7f4` |

Tipografías: una sans-serif limpia para todo. No mezcles más de dos familias.

---

## Errores que hunden un póster

1. **Demasiado texto.** El error número uno, por mucho.
2. **Gráficas sin unidades ni ejes rotulados.**
3. **Fotos de baja resolución.**
4. **No mostrar el resultado numérico.** Si hay que buscar el ahorro en el póster, perdiste.
5. **Colores de fondo oscuros.** Se imprimen mal y gastan tinta.
6. **No probar la impresión.** Imprime una hoja carta con un pedazo al 100% para verificar
   que el texto se lea. Cuesta $500 y te salva de un póster ilegible.

---

## Checklist antes de mandar a imprimir

- [ ] Menos de 800 palabras en total
- [ ] Título legible desde 3 metros
- [ ] Las tres gráficas con ejes rotulados y unidades
- [ ] El número de ahorro, grande y visible
- [ ] Al menos 4 fotos reales del proyecto (no imágenes de banco)
- [ ] Comparación del modelo ML contra la línea base
- [ ] Una limitación reconocida en conclusiones
- [ ] QR al repositorio, probado con el celular
- [ ] Logos de Uniagustiniana y Alcaldía de Sopó
- [ ] Exportado a PDF, 300 dpi
- [ ] Prueba de impresión en hoja carta revisada
- [ ] **Que el productor lo haya visto antes**, si su predio o su nombre aparecen
