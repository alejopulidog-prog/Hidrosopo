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
