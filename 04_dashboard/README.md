# App del productor — HidroSopó

Una PWA: página web que el celular instala como aplicación nativa. Sin Play Store,
sin costo, un solo código para Android e iOS, y funciona sin señal.

## Archivos

| Archivo | Qué es |
|---|---|
| `index.html` | Toda la app: estructura, estilos y lógica en un archivo |
| `manifest.json` | Lo que convierte la web en app instalable |
| `sw.js` | Service worker: guarda los datos para abrir sin señal |
| `iconos/` | Ícono de la app en los tamaños que piden Android e iOS |

## Antes de publicar: una línea

En `index.html`, busca al inicio del `<script>`:

```javascript
const API = localStorage.getItem('hidrosopo_api') || 'http://localhost:8000';
```

Cambia `http://localhost:8000` por la URL de tu backend publicado.

## Publicar (5 minutos, gratis)

Entra a **[app.netlify.com/drop](https://app.netlify.com/drop)** y **arrastra esta carpeta
completa** al navegador. Te da una URL con HTTPS lista para instalar.

Alternativas iguales de gratis: GitHub Pages, Vercel, Cloudflare Pages.

> La PWA necesita HTTPS para instalarse. Abrir el archivo con doble clic no sirve
> para instalarla, aunque sí para verla.

## Probarla local

```bash
python -m http.server 5500
# abre http://localhost:5500
```

Funciona en modo de ejemplo aunque el backend esté apagado, así que puedes mostrarla
en una reunión sin montar nada.

---

## Decisiones de diseño

Vale la pena que las conozcas, porque en la sustentación te pueden preguntar por qué
la app se ve así y no como un dashboard corporativo.

### El héroe es un corte de suelo, no un tablero de indicadores

La pantalla abre con un corte vertical de la tierra: el pasto arriba, los tres
horizontes del suelo, las raíces buscando agua, y los sensores a 15, 30 y 45 cm.

Es lo más característico del mundo del productor. Él camina sobre esa tierra todos
los días pero nunca la ha visto por dentro. Un número grande en una tarjeta no le
dice nada; un corte de suelo donde la capa de arriba se ve seca y clara mientras la
de abajo sigue oscura, sí.

**Todo en el dibujo significa algo:**

| Lo que ve | Lo que significa |
|---|---|
| Color de cada capa | Su humedad real. Seca = clara y polvorienta; húmeda = oscura y saturada |
| El pasto amarilleando y encogiéndose | El coeficiente de estrés hídrico (Ks) del modelo FAO-56 |
| La columna azul de la izquierda | La reserva de agua aprovechable |
| La línea punteada amarilla | El umbral de riego calculado con el MAD del cultivo |
| Los tres círculos | Los sensores. Tóquelos para ver su lectura |

### El deslizador responde la pregunta real

"¿Qué pasa si no riego?" es la pregunta que hay detrás de cada decisión de riego,
y ninguna app agrícola la responde de frente.

Al deslizar, el suelo se seca **en vivo**: las capas se aclaran, la reserva baja, el
pasto amarillea. Es la proyección del balance hídrico FAO-56 volviéndose visible.

No es adorno: es la función más útil de toda la app.

### Colores tomados de los materiales, no de una paleta

El café oscuro es el andisol de la Sabana. El verde es kikuyo real, apagado, no verde
de logo. El amarillo del pasto seco es el color que toma el kikuyo en estrés. El azul
es agua.

### Movimiento con criterio

Una sola secuencia al abrir: la reserva de agua llenándose. Después de eso, nada se
mueve solo. Todo el demás movimiento responde a algo que la persona hizo — deslizar,
tocar un sensor, cambiar de gráfica.

Se respeta `prefers-reduced-motion`.

### Escrito para el productor, no para el ingeniero

- "Hoy no riegue", no "Estado: sin requerimiento hídrico"
- "38 minutos", no "12.4 mm de lámina bruta"
- "de aquí para abajo, hay que regar", no "umbral MAD"
- "Sin señal. Esta es la última información que llegó el 12 de nov a las 6:15",
  no "Error de conexión"

Los términos técnicos existen en la app, pero después del lenguaje claro, no antes.

### Funciona sin señal, por diseño

En una finca de Sopó la señal se cae a diario. El service worker guarda la última
información recibida y la app la muestra con su fecha, en vez de una pantalla en
blanco. Es la diferencia entre una app útil y una decorativa.

---

## Personalizar

Los colores están todos en las variables CSS al inicio del archivo:

```css
--tierra-honda:#3A2E23;   /* andisol de la Sabana */
--pasto:#7A9B3E;          /* kikuyo sano */
--pasto-seco:#B8A052;     /* kikuyo en estrés */
--agua:#2E7EA6;
```

El corte de suelo se dibuja en la función `dibujarSuelo()`. Las profundidades de los
sensores están en el arreglo de esa función; si instalas a otras profundidades,
cámbialas ahí y en `SUELO.y()`.


---

## Versión 2 — la app por tipo de predio (ago 2026)

### La escena cambia con el predio

El héroe ya no es solo el corte de suelo: arriba está lo que se ve desde el camino
y abajo lo que solo ven los sensores, en el mismo dibujo. Todo es SVG generado con
los datos, no fotos: pesa nada, funciona sin señal y se puede animar.

| Tipo | Qué se dibuja | Cómo se le habla | Raíz |
|---|---|---|---|
| `pastoreo` | Kikuyo, vacas, cerca eléctrica de la franja | "la franja" | 40 cm |
| `papa` | Caballones aporcados, mata con flor | "el lote" | 45 cm |
| `hortalizas` | Camas levantadas con acolchado y lechugas | "la cama" | 25 cm |
| `flores` | La nave con su cubierta, camas de rosa | "la nave" | 30 cm |

El cielo responde a la hora (amanecer, día, atardecer, noche), a las nubes del
pronóstico y a la lluvia del día que se esté viendo. Al mover el deslizador de
días, la planta se marchita y amarillea en vivo.

Para agregar un tipo nuevo: se añade una entrada en `TIPOS` (colores, vocabulario,
profundidad de raíz, nota de la gráfica) y una rama en `plantas()`. Nada más.

### El backend manda, el teléfono responde si no hay señal

`agente.py` y `costos.py` están portados a JavaScript dentro de la app. Cuando hay
conexión, la conversación va al servidor como siempre. Cuando no la hay, responde
el agente local con la última lectura descargada, y lo dice explícitamente en vez
de fingir que está en línea. Las mismas intenciones: registrar riego (con sector y
varias bombas), ahorro, lluvia, pastoreo o cosecha, costo del riego, medición de
caudal con balde y cronómetro, reporte de daño y discrepancia.

### Qué campos espera del backend

Además de lo de siempre, la app usa si vienen:

- `predio.tipo` — uno de `pastoreo`, `papa`, `hortalizas`, `flores` (si falta, asume pastoreo)
- `predio.sectores[]` — `{orden, nombre, area_ha, caudal_lps}`
- `predio.energia`, `paga_agua`, `tarifa_agua_m3`, `altura_bombeo_m`, `costo_kwh`,
  `costo_diesel_litro`, `consumo_diesel_lph` — para calcular el costo en el teléfono
- `ciclo` — `{titulo, texto, pct, izq, der, estado}` para la franja o la etapa del cultivo
- `cuarta` — `{etiqueta, datos[], ejes[], objetivo}` para la cuarta gráfica

Si el backend no los manda, la app cae a los datos de prueba de los cuatro predios
y lo avisa arriba.

### Hora del predio, no del teléfono

La app se rige por `America/Bogota`, no por el reloj del aparato: el sol, el riego
y el corte del día pasan en Sopó. Arriba del `<script>` hay tres interruptores:

```javascript
const TZ = 'America/Bogota';
const RELOJ_DEL_PREDIO = true;   // false = usa el reloj del teléfono
const TS_SIN_ZONA_ES_UTC = true; // cómo leer marcas de tiempo sin zona
```

`TS_SIN_ZONA_ES_UTC` importa: si el backend serializa con `datetime.utcnow()` sin
zona, déjelo en `true`. Si guarda hora local de Colombia sin zona, póngalo en
`false`. **Lo correcto es que el backend mande la zona** (`2026-08-31T07:29:00-05:00`)
y entonces este interruptor deja de importar: la app respeta el offset que venga.

### Otros cambios

- Dictado por voz en es-CO donde el navegador lo soporte
- Atajo desde el ícono de la app directo a la conversación (`?charla=1`)
- El service worker pasó a `hidrosopo-v2` y sirve la app con red primero: una
  versión nueva entra sin que el productor tenga que desinstalar nada
- Las cifras se despliegan y explican qué significan al tocarlas
- El rango de fechas del informe se calcula con el día de Sopó. Antes salía de
  `toISOString()`, que da el día en UTC: después de las 7 p.m. en Colombia el
  informe se pedía con un día corrido
