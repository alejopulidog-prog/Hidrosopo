# Guía de Puesta en Marcha — paso a paso

De cero a "el productor recibe recomendaciones en su celular".

Tiempo total si tienes el hardware: **un fin de semana**.
Sin hardware, para probar todo con datos simulados: **40 minutos**.

---

## Índice

- [Parte 1 — Instalar el módulo de IA (40 min, sin hardware)](#parte-1)
- [Parte 2 — Publicar el backend en internet (30 min)](#parte-2)
- [Parte 3 — Poner la app en el celular (20 min)](#parte-3)
- [Parte 4 — Conectar los sensores reales (un fin de semana)](#parte-4)
- [Parte 5 — Alertas por WhatsApp (15 min)](#parte-5)
- [Parte 6 — Automatizar todo (10 min)](#parte-6)
- [Solución de problemas](#problemas)

---

<a name="parte-1"></a>
## Parte 1 — Instalar el módulo de IA

Esto se hace en tu computador. No necesitas ningún sensor todavía.

### 1.1 Instalar Python

Descarga Python 3.11 o superior de [python.org](https://python.org).

> **Windows:** en el instalador marca la casilla **"Add Python to PATH"**. Si no la marcas,
> nada de lo que sigue va a funcionar y vas a perder media hora averiguando por qué.

Verifica:
```bash
python --version
```

### 1.2 Preparar el entorno

```bash
cd hidrosopo/03_backend

# Crear un entorno aislado (evita romper otras cosas de tu PC)
python -m venv venv

# Activarlo
source venv/bin/activate       # Mac / Linux
venv\Scripts\activate          # Windows

# Instalar todo
pip install -r requirements.txt
```

Si `pip install` tarda mucho, es normal: `scikit-learn`, `pandas` y `numpy` son pesados.

### 1.3 Encender el backend

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Deberías ver:
```
[OK] HidroSopó API lista
INFO:     Uvicorn running on http://0.0.0.0:8000
```

Abre `http://localhost:8000/docs` en el navegador. Ahí tienes toda la API documentada
e interactiva. **Deja esta terminal abierta** y abre otra para los pasos siguientes.

### 1.4 Crear el predio y los nodos

En la segunda terminal:

```bash
cd hidrosopo/03_backend
source venv/bin/activate        # Windows: venv\Scripts\activate
python
```

Y dentro de Python, pega esto (ajustando los datos de tu predio):

```python
from db import init_db, SessionLocal, Predio, Nodo
from datetime import datetime

init_db()
db = SessionLocal()

db.add(Predio(
    nombre="Finca La Esperanza",
    propietario="Nombre del productor",
    telefono="+573001234567",
    vereda="Hato Grande",
    latitud=4.9083, longitud=-73.9403, altitud_m=2587,   # coordenadas reales del predio
    area_predio_ha=4.5,
    area_regada_ha=2.0,
    perfil_cultivo="kikuyo_pastoreo",    # ver lista abajo
    tipo_suelo="sabana_bogota",
    sistema_riego="aspersion",
    caudal_disponible_lps=2.5,           # caudal de su bomba o manguera
    fecha_ultimo_pastoreo=datetime(2026, 9, 15),
    consentimiento_firmado=True,
))
db.commit()

# Los tokens deben ser iguales a los de 02_firmware/src/config.h
db.add(Nodo(codigo="NODO-SUELO-01",  token="token_largo_y_secreto_1", tipo="suelo",  predio_id=1))
db.add(Nodo(codigo="NODO-CAUDAL-01", token="token_largo_y_secreto_2", tipo="caudal", predio_id=1))
db.commit()

print("Predio y nodos creados.")
exit()
```

**Perfiles disponibles:** `kikuyo_pastoreo`, `raigras_pastoreo`, `pasto_corte`, `papa`,
`hortalizas_hoja`, `fresa`, `mora`, `maiz`, `generico`.
Consulta la lista completa en `http://localhost:8000/api/v1/catalogos`.

**Coordenadas del predio:** ábrelas en Google Maps, mantén presionado el punto exacto,
y copia los números que aparecen. Importa porque de ahí sale el pronóstico del clima.

### 1.5 Generar datos de prueba y entrenar el modelo

```bash
cd ../06_datos
python generar_datos_prueba.py --dias 90

cd ../03_backend
python -m ia.modelo_ml --csv ../06_datos/datos_sinteticos.csv
```

Vas a ver algo así:

```
 Modelo: humedad a 48 h
 Registros usados  : 25062
 MAE (val. cruzada): 1.058 % vol
 MAE línea base    : 1.068 % vol (persistencia)
 Mejora vs. base   : 0.9%

 Variables más importantes:
   lluvia_pronosticada_48h    0.199 █████████
   et0_acumulada_24h          0.178 ████████
```

**Ese es tu módulo de IA instalado y entrenado.** Los archivos quedan en
`03_backend/modelos/`.

> **Importante:** cuando tengas datos reales del predio, **vuelve a entrenar** con ellos.
> El modelo aprende de tu suelo específico, no de un promedio genérico. Reentrena cada
> 2–3 semanas durante el piloto.

### 1.6 Ver que funcione

```bash
curl "http://localhost:8000/api/v1/predios/1/recomendacion"
```

O simplemente abre esa dirección en el navegador. Deberías recibir un JSON con la
recomendación completa.

**¿Qué pasó por dentro?**

```
Tus sensores          →  humedad, temperatura, lluvia
        +
Open-Meteo (gratis)   →  pronóstico y ET0 de tus coordenadas
        ↓
Modelo FAO-56         →  cuánta agua necesita el cultivo (balance hídrico)
        +
Modelo ML             →  cómo va a cambiar la humedad en 48 h
        +
Reglas agronómicas    →  regar / esperar / preparar / no regar
        ↓
Mensaje en español    →  "Don Jaime, hoy no riegue..."
```

---

<a name="parte-2"></a>
## Parte 2 — Publicar el backend en internet

Mientras el backend corra solo en tu PC, ni el ESP32 ni el celular del productor lo
alcanzan. Hay que publicarlo.

### Opción recomendada: Render + Supabase (gratis, 30 minutos)

**Paso A — Base de datos en Supabase**

1. Crea cuenta en [supabase.com](https://supabase.com) (gratis, sin tarjeta).
2. *New project*. Elige región **South America (São Paulo)** — es la más cercana.
3. Guarda la contraseña que te pide crear.
4. Ve a *Project Settings → Database → Connection string → URI*.
5. Copia esa cadena. Se ve así:
   `postgresql://postgres:[TU-CLAVE]@db.xxxx.supabase.co:5432/postgres`

**Paso B — Subir el código a GitHub**

```bash
cd hidrosopo
git init
echo "venv/
__pycache__/
*.db
.env" > .gitignore
git add .
git commit -m "HidroSopo v1.0"
```

Crea un repositorio en [github.com](https://github.com) y sigue las instrucciones que te da
para hacer `git remote add origin ...` y `git push`.

**Paso C — Desplegar en Render**

1. Crea cuenta en [render.com](https://render.com) (gratis).
2. *New → Web Service* → conecta tu repositorio de GitHub.
3. Configura:
   - **Root Directory:** `03_backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type:** Free
4. En *Environment*, agrega:
   | Key | Value |
   |---|---|
   | `DATABASE_URL` | la cadena de Supabase del paso A |
   | `CANAL_ALERTAS` | `consola` (por ahora) |
5. *Create Web Service*. Espera 3–5 minutos.

Te queda una URL tipo `https://hidrosopo.onrender.com`. **Guárdala, la vas a usar en
todas partes.**

6. Repite el paso 1.4 (crear predio y nodos) pero apuntando a la base de Supabase.
   La forma más fácil: `export DATABASE_URL="tu-cadena"` antes de correr `python`.

> ⚠️ **El plan gratuito de Render se duerme** tras 15 minutos sin uso, y tarda ~30 s
> en despertar. El firmware ya reintenta y guarda en buffer, así que no pierdes datos.
> Anótalo como limitación conocida en tu informe.

### Alternativa más robusta: Oracle Cloud Always Free

4 CPU ARM + 24 GB de RAM, gratis permanentemente, sin dormirse. Pide tarjeta para
verificar identidad pero no cobra. Es lo que usarías si el proyecto continúa después
de los 4 meses.

### Alternativa sin nube: Raspberry Pi en la finca

Si el predio tiene internet estable, un Raspberry Pi corriendo el backend + un túnel de
Cloudflare te da control total sin depender de nadie.

---

<a name="parte-3"></a>
## Parte 3 — Poner la app en el celular

**No necesitas Android Studio, ni Flutter, ni React Native, ni publicar en Play Store.**

La app es una **PWA** (Aplicación Web Progresiva): una página web que el celular instala
como app nativa. Se ve igual, tiene su ícono, abre a pantalla completa y funciona sin señal.

### Por qué PWA y no una app nativa

| | PWA | App nativa |
|---|---|---|
| Costo de publicación | $0 | US$25 Play Store + US$99/año App Store |
| Tiempo de desarrollo | Ya está hecha | 4–8 semanas |
| Actualizar | Subes el archivo, listo | Nueva versión, revisión, esperar aprobación |
| Funciona en Android e iOS | Sí, el mismo código | Dos códigos distintos |
| Cabe en un proyecto de 4 meses | Sí | No |

Para tu sustentación, la PWA es además un punto a favor: demuestra criterio de ingeniería
al elegir la tecnología proporcional al problema.

### 3.1 Configurar la dirección del backend

Abre `04_dashboard/index.html`, busca esta línea (está al inicio del `<script>`):

```javascript
const API = localStorage.getItem('hidrosopo_api') || 'http://localhost:8000';
```

Cámbiala por tu URL de Render:

```javascript
const API = localStorage.getItem('hidrosopo_api') || 'https://hidrosopo.onrender.com';
```

### 3.2 Publicar la app (5 minutos, gratis)

**La forma más simple: Netlify Drop**

1. Ve a [app.netlify.com/drop](https://app.netlify.com/drop)
2. **Arrastra la carpeta `04_dashboard` completa** a la ventana del navegador.
3. Listo. Te da una URL tipo `https://hidrosopo-app.netlify.app`

Sin cuenta, sin configuración, sin comandos. Puedes cambiar el nombre del sitio después
si creas cuenta gratuita.

**Alternativas igual de gratis:** GitHub Pages, Vercel, Cloudflare Pages.

> **La PWA necesita HTTPS** para instalarse. Netlify, Vercel y GitHub Pages te lo dan
> automáticamente. Por eso no sirve abrir el archivo con doble clic.

### 3.3 Instalar en el celular

**Android (Chrome):**
1. Abrir la URL en Chrome.
2. Aparece el botón **"Instalar"** en la app, o el menú **⋮ → Instalar aplicación**.
3. Toca instalar. Queda el ícono en la pantalla de inicio.

**iPhone (Safari — tiene que ser Safari, no Chrome):**
1. Abrir la URL en Safari.
2. Botón **Compartir** (el cuadrito con la flecha).
3. **Agregar a pantalla de inicio**.

La app ya está programada para mostrarle esas instrucciones al usuario de iPhone
automáticamente.

### 3.4 Qué obtiene el productor

- Ícono propio en la pantalla de inicio
- Abre a pantalla completa, sin barra de navegador
- **Funciona sin señal**: muestra la última información recibida, con la fecha
- Aviso claro de "sin conexión" en vez de una pantalla en blanco
- Gráficas de humedad, temperatura, lluvia y consumo
- La recomendación del día con los minutos exactos de riego

> Ese detalle de funcionar sin señal no es adorno. En una finca de Sopó la señal se cae
> a diario. Sin caché, la app sería inútil justo cuando más se necesita.

---

<a name="parte-4"></a>
## Parte 4 — Conectar los sensores reales

### 4.1 Preparar el entorno de firmware

Instala [VS Code](https://code.visualstudio.com) y dentro de él la extensión
**PlatformIO IDE**. La primera vez tarda unos minutos en descargar el toolchain.

### 4.2 Configurar el nodo

Abre `02_firmware/src/config.h` y ajusta:

```c
#define NODO_ID       "NODO-SUELO-01"              // igual al que creaste en la base
#define NODO_TOKEN    "token_largo_y_secreto_1"    // igual al de la base

#define TRANSPORTE    TRANSPORTE_WIFI              // empieza con WiFi para probar

#define WIFI_SSID     "RedDeLaFinca"
#define WIFI_PASS     "clave"
#define BACKEND_URL   "https://hidrosopo.onrender.com/api/v1/telemetria"
```

### 4.3 Cargar y probar

```bash
cd 02_firmware
pio run                  # compila
pio run -t upload        # carga al ESP32
pio device monitor       # ver qué está haciendo
```

**Orden de pruebas. No te saltes pasos:**

1. **Un solo sensor de humedad, en la mesa.** Verifica que el JSON llegue al backend.
2. **Agrega los demás sensores uno por uno.** Si pones seis de una y falla algo, no vas
   a saber cuál es.
3. **Calibra** los sensores (`01_hardware/CALIBRACION.md`). Sin esto, tus datos no tienen
   significado físico.
4. **Cambia a LoRa** (`TRANSPORTE_LORA`). Prueba a 2 m, luego a 50 m, luego en campo.
5. **Prueba de deep sleep.** Verifica que despierte cada 15 min y que el consumo baje.
6. **72 horas solo con batería**, sin panel, antes de instalar en el predio.

### 4.4 Verificar que los datos llegan

```
https://hidrosopo.onrender.com/api/v1/salud
```

Te dice qué nodos están reportando y hace cuántos minutos.

---

<a name="parte-5"></a>
## Parte 5 — Alertas por WhatsApp

El productor probablemente no va a abrir la app todos los días. El mensaje sí lo lee.

### Opción A — WhatsApp con CallMeBot (gratis)

1. Guarda el número **+34 644 51 95 23** en los contactos del celular del productor.
2. Desde ese celular, envíale por WhatsApp el mensaje exacto:
   `I allow callmebot to send me messages`
3. Te responden con una API key.
4. En Render, agrega las variables de entorno:
   | Key | Value |
   |---|---|
   | `CANAL_ALERTAS` | `whatsapp` |
   | `CALLMEBOT_APIKEY` | la clave que te dieron |

Prueba:
```bash
curl "https://hidrosopo.onrender.com/api/v1/predios/1/recomendacion?guardar=true&enviar=true"
```

### Opción B — Telegram (gratis e ilimitado, más confiable)

1. En Telegram, escríbele a **@BotFather** → `/newbot` → sigue las instrucciones.
2. Te da un token.
3. El productor le escribe algo a tu bot.
4. Abre `https://api.telegram.org/bot<TU_TOKEN>/getUpdates` y copia el `chat_id`.
5. Variables en Render: `CANAL_ALERTAS=telegram`, `TELEGRAM_TOKEN=...`
6. Guarda el `chat_id` en el campo `telefono` del predio.

### Si el productor no usa smartphone

Imprime el reporte semanal y llévaselo. No es menos válido, y **decirlo en el informe
demuestra que entendiste el contexto real** en vez de asumir que todo el mundo tiene
un iPhone.

---

<a name="parte-6"></a>
## Parte 6 — Automatizar

Para que la recomendación llegue sola cada mañana a las 6:

**Con cron (Linux/Mac/Raspberry Pi):**
```bash
crontab -e
# agrega:
0 6 * * * curl -s "https://hidrosopo.onrender.com/api/v1/predios/1/recomendacion?guardar=true&enviar=true" > /dev/null
```

**Sin servidor propio — cron-job.org (gratis):**
1. Cuenta en [cron-job.org](https://cron-job.org)
2. *Create cronjob*
3. URL: `https://hidrosopo.onrender.com/api/v1/predios/1/recomendacion?guardar=true&enviar=true`
4. Horario: diario, 6:00 AM, zona horaria America/Bogota

**Bonus:** este cron también mantiene despierto el servicio de Render.

---

<a name="problemas"></a>
## Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| `ModuleNotFoundError` | El entorno virtual no está activado | `source venv/bin/activate` |
| `python: command not found` (Windows) | No marcaste "Add to PATH" | Reinstala Python marcando la casilla |
| La app muestra "modo demostración" | El backend no responde | Revisa la URL en `index.html`; si es Render free, espera 30 s y recarga |
| No aparece el botón "Instalar" | Falta HTTPS, o ya está instalada | Publica en Netlify/Vercel. En iPhone usa Safari, no Chrome |
| El ESP32 no conecta al WiFi | Red de 5 GHz | El ESP32 solo funciona en **2.4 GHz** |
| El sensor lee `-127 °C` | Falta el pull-up del DS18B20 | Resistencia de 4.7 kΩ entre DATA y 3V3 |
| Lecturas de humedad erráticas con WiFi | Usaste pines del ADC2 | Muévelos a GPIO 1, 2, 3 (ADC1) |
| El nodo consume mucho en deep sleep | MOSFET flotando | Pull-down de 10 kΩ en el gate |
| El módulo LoRa no responde / se quema | Lo energizaste sin antena | Conecta la antena **antes** de dar corriente. Siempre |
| `Error 401` al enviar telemetría | Token distinto | Debe ser idéntico en `config.h` y en la base de datos |
| El modelo ML no predice | No lo has entrenado | Corre `python -m ia.modelo_ml --csv ...` |
| El modelo no le gana a la persistencia | Pocos datos, o el suelo es muy estable | Espera más días y reentrena. Si sigue igual, repórtalo con honestidad: también es un resultado |

---

## Orden recomendado si tienes poco tiempo

Si mañana tienes reunión y quieres mostrar algo funcionando:

1. **Parte 1** (40 min) → backend corriendo local con datos simulados
2. **Parte 3.2** con `localhost` → abre el dashboard en el navegador

Con eso ya muestras el sistema completo funcionando. Las partes 2, 4, 5 y 6 son para el
despliegue real.

---

## Checklist de "está todo listo"

- [ ] Backend responde en `/api/v1/salud`
- [ ] Predio creado con coordenadas reales del piloto
- [ ] Los dos nodos registrados con sus tokens
- [ ] Modelo ML entrenado (hay archivos en `03_backend/modelos/`)
- [ ] Backend publicado en internet con HTTPS
- [ ] App publicada y instalada en el celular del productor
- [ ] El ESP32 envía datos y se ven en el dashboard
- [ ] Sensores calibrados por gravimetría, con su R² documentado
- [ ] Caudalímetro calibrado con probeta, con fotos en la bitácora
- [ ] El productor recibe el mensaje diario
- [ ] Consentimiento informado firmado y archivado
- [ ] Bitácora al día desde el primer día
