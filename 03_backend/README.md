# Backend — HidroSopó

API en FastAPI: ingesta de telemetría, motor de IA, alertas y reporte PUEAA.

## Puesta en marcha local (5 minutos)

```bash
cd 03_backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Abre `http://localhost:8000/docs` — tienes la API documentada e interactiva.

## Cargar datos de prueba

```bash
# 1. Generar 90 días de datos sintéticos
cd ../06_datos && python generar_datos_prueba.py --dias 90

# 2. Entrenar el modelo ML
cd ../03_backend && python -m ia.modelo_ml --csv ../06_datos/datos_sinteticos.csv

# 3. Ver el dashboard
cd ../04_dashboard && python -m http.server 5500
# abre http://localhost:5500
```

## Registrar el predio y los nodos

```python
# python -i, dentro de 03_backend
from db import SessionLocal, init_db, Predio, Nodo
from datetime import datetime
init_db()
db = SessionLocal()

db.add(Predio(
    nombre="Finca La Esperanza",
    propietario="Nombre del productor",
    telefono="+573001234567",
    vereda="Hato Grande",
    latitud=4.9083, longitud=-73.9403, altitud_m=2587,
    area_predio_ha=4.5, area_regada_ha=2.0,
    perfil_cultivo="kikuyo_pastoreo",     # ver /api/v1/catalogos
    tipo_suelo="sabana_bogota",
    sistema_riego="aspersion",
    caudal_disponible_lps=2.5,
    fecha_ultimo_pastoreo=datetime(2026, 9, 15),
    tiene_concesion=False,     # ¿tiene permiso de captación?
    consentimiento_firmado=True,
    fecha_consentimiento=datetime(2026, 9, 5),
))
db.commit()

db.add(Nodo(codigo="NODO-SUELO-01", token="pon_un_token_largo_aqui",
            tipo="suelo", predio_id=1))
db.add(Nodo(codigo="NODO-CAUDAL-01", token="otro_token_distinto",
            tipo="caudal", predio_id=1))
db.commit()
```

Los tokens deben coincidir con los de `02_firmware/src/config.h`.

## Variables de entorno

| Variable | Por defecto | Para qué |
|---|---|---|
| `DATABASE_URL` | `sqlite:///hidrosopo.db` | PostgreSQL/Supabase en producción |
| `CANAL_ALERTAS` | `consola` | `telegram` / `whatsapp` / `twilio` |
| `TELEGRAM_TOKEN` | — | Token del bot de @BotFather |
| `CALLMEBOT_APIKEY` | — | Para WhatsApp gratuito |
| `LLM_PROVEEDOR` | `ninguno` | `ollama` / `groq` / `gemini` (opcional) |
| `RUTA_CALIBRACION` | `config_sensores.json` | Curvas de tus sensores |
| `CORS_ORIGINS` | `*` | Restringir en producción |

## Despliegue gratuito

### Opción A — Render (la más rápida)

1. Sube el repositorio a GitHub.
2. En Render: *New → Web Service*, conecta el repo.
3. Build: `pip install -r requirements.txt`
4. Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Agrega la variable `DATABASE_URL` apuntando a tu base de Supabase.

> **Advertencia del plan gratuito:** el servicio se duerme tras 15 minutos de
> inactividad y tarda ~30 s en despertar. El firmware ya maneja esto con
> reintentos y buffer local, pero anótalo en el informe como limitación conocida.

### Opción B — Oracle Cloud Always Free (la más robusta)

4 vCPU ARM + 24 GB de RAM, gratis de forma permanente, sin spin-down.
Requiere registro con tarjeta (no cobra). Es la que usarías si el proyecto
sigue después de los 4 meses.

### Opción C — Raspberry Pi en la finca + Cloudflare Tunnel

Control total, sin nube, sin costo. Depende de la internet del predio.

## Endpoints principales

| Método | Ruta | Para qué |
|---|---|---|
| POST | `/api/v1/telemetria` | Ingesta desde el gateway |
| GET | `/api/v1/predios/{id}/recomendacion` | **El endpoint central** |
| GET | `/api/v1/predios/{id}/series?horas=168` | Datos para gráficas |
| GET | `/api/v1/predios/{id}/consumo?dias=30` | Consumo diario en m³ |
| GET | `/api/v1/predios/{id}/reporte-pueaa?desde=&hasta=` | Anexo técnico PUEAA |
| GET | `/api/v1/institucional/resumen` | Panel para Emsersopó |
| GET | `/api/v1/salud` | Estado de nodos y modelos |
| GET | `/api/v1/catalogos` | Perfiles, suelos, sistemas de riego |
| POST | `/api/v1/predios/{id}/conversar` | **El agente**: el productor escribe, el sistema responde y actúa |
| GET | `/api/v1/predios/{id}/conversacion` | Historial de la conversación |
| GET | `/api/v1/predios/{id}/ahorro` | Agua ahorrada contra la línea base |
| GET | `/api/v1/predios/{id}/riegos` | Riegos reportados por el productor |
| GET | `/api/v1/predios/{id}/notas` | Rutina, desacuerdos y problemas que él contó |
| GET | `/api/v1/predios/{id}/sectores` | Sectores de riego con su tasa de aplicación |
| GET | `/api/v1/predios/{id}/costo-agua` | **El ahorro en pesos**, no solo en m³ |

## Sectores de riego: por qué existen

Una finca real no tiene "un caudal". Tiene sectores con distinta área, distinto número
de aspersores y distinto caudal. Y el productor a veces prende dos bombas al tiempo.

Sin modelar esto, todos los cálculos salen mal. Con un solo caudal y el área total del
predio, el sistema calculaba que 40 minutos de riego eran 0.3 mm, y recomendaba jornadas
de 20 horas.

```python
db.add(Sector(predio_id=1, orden=1, nombre="Potrero de arriba",
              area_ha=0.35, caudal_lps=2.5, n_emisores=6, bomba="Bomba grande"))
db.add(Sector(predio_id=1, orden=3, nombre="Lote de la casa",
              area_ha=0.35, caudal_lps=1.4, n_emisores=4, bomba="Bomba chica"))
```

El agente entiende:

| El productor escribe | Qué hace |
|---|---|
| "Regué 45 minutos" (varios sectores) | **Pregunta cuál.** No adivina: registrar el riego en el sector equivocado daña el balance de dos sectores |
| "el 2" | Recupera los 45 minutos pendientes y los aplica al sector 2 |
| "Prendí las dos bombas una hora" | Elige un sector por cada bomba distinta y reparte el volumen |
| "media hora en el sector 1" | Funciona sin verbo de riego, como habla la gente |
| "regué toda la finca 30 min" | Todos los sectores activos |

También calcula la **tasa de aplicación** (mm/h) de cada sector y avisa si es demasiado
baja (sector subequipado: regar bien tomaría jornadas) o demasiado alta (el suelo no
alcanza a absorber y el agua se escurre).

## El ahorro en pesos, partida por partida (`costos.py`)

Los metros cúbicos son para el informe. **Los pesos son los que hacen que el productor
siga usando el sistema.**

Si el agua sale de su quebrada o su pozo, el agua es gratis: lo que cuesta es bombearla.

```
kWh por m³ = 0.002725 × altura_de_bombeo / eficiencia_de_la_bomba
```

Con 45 m de altura y 55% de eficiencia: 0.22 kWh/m³. A $850/kWh, mover un metro cúbico
cuesta unos $190.

### Las partidas van separadas, no sumadas

El agua y la energía son plata de bolsillos distintos, y en muchas fincas una de las dos
es cero. Sumarlas en un solo número oculta información:

| Caso de Sopó | Agua | Energía | Total por m³ | Retorno |
|---|---:|---:|---:|---:|
| Quebrada propia + bomba eléctrica | $0 | $190 | **$190** | 13.7 años |
| Acueducto veredal + bomba eléctrica | $1.800 | $105 | **$1.905** | 4.0 años |
| Pozo + motobomba diésel | $0 | $2.600 | **$2.600** | 2.6 años |

**El caso más común en Sopó es el primero: el agua es suya, no la paga.** Decirle que
"ahorró en la factura del agua" cuando no paga agua sería mentirle. El sistema lo dice
explícitamente: *"El agua es de fuente propia: no la paga. Todo su ahorro está en la
energía de bombeo."*

Configurable por predio: `altura_bombeo_m`, `eficiencia_bomba`, `tipo_energia`,
`costo_kwh`, `costo_diesel_litro`, `consumo_diesel_lph`, `tarifa_agua_m3`,
`tasa_uso_agua_m3`, `inversion_sistema_cop`.

**Verifique los precios con la factura real.** Los valores por defecto son referenciales.

### Diésel: se prefiere el dato medido

Si el productor sabe cuántos litros por hora gasta su motor (lo mide llenando el tanque),
ese dato manda sobre la estimación termodinámica. Él lo sabe; nosotros lo estimamos.
Y se reporta en **galones**, que es como compra el ACPM.

### El retorno de la inversión, sin maquillar

`retorno_inversion()` calcula en cuántos años se paga el equipo con el ahorro medido.

En el caso típico de Sopó (quebrada propia, luz barata, 1 ha) el resultado son
**13.7 años**, y el sistema lo dice sin adornos:

> Con el ahorro de bombeo solo, el equipo no se paga en un plazo corto. Esto es esperable
> en un predio pequeño con energía barata, y no invalida el proyecto: el valor está
> también en no perder producción por estrés hídrico, en poder demostrar el uso del agua,
> y en que el costo por predio baja mucho al replicar.

**Ese dato es incómodo pero hay que tenerlo listo para la sustentación.** Alguien del
jurado va a preguntar si esto se paga solo. Llegar con el número real y con el argumento
de dónde viene el resto del valor es mucho más sólido que improvisar.

Donde sí se paga rápido: bombeo diésel, mayor altura, más área, o predios que compran
agua a un acueducto.

Ejemplo de respuesta real del agente:

> En 30 días ha ahorrado 55.9 m³ de agua, un 58% menos que antes. Son unos 56 tanques
> de mil litros. En plata son $10.601 que no gastó en bombear (12 kWh menos). A ese
> ritmo serían unos $128.974 al año, aunque en época de lluvias se riega menos.

## Medir el caudal de la bomba

Casi ningún productor sabe cuántos litros por segundo da su bomba, y sin ese dato todos
los cálculos son adivinanzas. El agente lo mide con lo que hay en cualquier finca:

> **¿Cuánta agua da mi bomba?**
> Consiga un balde del que sepa los litros. Prenda la bomba, meta la manguera y tome el
> tiempo hasta llenarlo. Dígame cuántos segundos se demoró.
>
> **20 litros en 9 segundos**
> Su bomba da 2.22 litros por segundo, o sea 133 litros por minuto (8.0 m³ por hora).
> Ya lo dejo registrado.

Detecta valores absurdos: más de 25 l/s en una finca pequeña, o menos de 0.15 l/s
(filtro tapado o bomba fallando).

## El agente conversacional (`agente.py`)

Es un agente **híbrido**, no un chatbot con LLM al frente:

```
mensaje del productor
        ↓
[1] Analizador de intención    reglas + regex · $0 · sin internet · determinista
        ↓
[2] Acción sobre datos reales  registra el riego, calcula el ahorro, alerta al técnico
        ↓
[3] Respuesta                  plantilla en español, o LLM opcional solo para redactar
```

**Regla de oro: el LLM puede cambiar cómo suena la respuesta, nunca de dónde sale el
número.** Los datos siempre vienen del motor FAO-56 y de la base.

Por qué no un LLM puro: en una finca la señal se cae, y un agente que depende de una API
externa deja de servir justo cuando más se necesita. Además un LLM suelto alucina cifras
de riego, y una cifra inventada le cuesta agua y plata al productor.

### Lo que entiende

| El productor escribe | Qué hace el sistema |
|---|---|
| "Regué 40 minutos" | Registra el evento, calcula la lámina aplicada y **la compara con lo que el suelo pedía** |
| "regué" (sin número) | Pregunta cuántos minutos y recuerda que está esperando ese dato |
| "riego dos veces al día" | Guarda su rutina para contrastarla con la necesidad real |
| "¿cuánta agua he ahorrado?" | Calcula contra la línea base y responde en m³ y en tanques |
| "¿riego hoy?" | Devuelve la recomendación del motor |
| "¿va a llover?" | Pronóstico de Open-Meteo por día |
| "¿cuándo meto las vacas?" | Estado de la franja, días de descanso, altura de entrada y residual |
| "se dañó el sensor" | Registra el problema y **alerta al técnico** |
| "la tierra la veo seca pero usted dice que está bien" | Registra la discrepancia y **avisa al técnico para revisar calibración** |

### El caso de la discrepancia

Cuando el productor no está de acuerdo, el sistema **no lo descarta**. Él conoce su tierra
mejor que el sensor: si dice que está seca y el sensor dice lo contrario, lo más probable
es que el sensor esté mal instalado o descalibrado.

Su desacuerdo se guarda como dato de diagnóstico y dispara una alerta al técnico. Esa
tabla de notas es además material cualitativo excelente para el informe final.

### Probarlo

```bash
curl -X POST http://localhost:8000/api/v1/predios/1/conversar \
  -H "Content-Type: application/json" \
  -d '{"texto": "Regué 40 minutos"}'
```

## Tarea programada de recomendaciones

Para que el productor reciba el mensaje cada mañana:

```bash
# crontab -e
0 6 * * * curl -s "http://localhost:8000/api/v1/predios/1/recomendacion?guardar=true&enviar=true" > /dev/null
```

## Sobre el modelo de machine learning

Lee esto antes de reportar resultados.

**Qué predice:** el *cambio* de humedad del suelo a 24 y 48 horas, no el valor absoluto.
Predecir el cambio hace que la línea base trivial (persistencia) sea "cambio = 0", y obliga
al modelo a demostrar que aporta algo.

**Línea base obligatoria.** El script reporta siempre el MAE de la persistencia —
"la humedad de pasado mañana será igual a la de hoy". Si el modelo no le gana a eso,
el modelo no sirve, por bonito que se vea el R².

**Resultados sobre datos sintéticos** (los que trae este paquete):

| Horizonte | MAE modelo | MAE persistencia | Mejora |
|---|---|---|---|
| 24 h | 0.81 % vol | 0.73 % vol | **−11 %** |
| 48 h | 1.06 % vol | 1.07 % vol | **+1 %** |

A 24 horas la persistencia es prácticamente imbatible: en ese plazo el suelo casi no se
mueve y lo poco que se mueve depende de la lluvia, que es estocástica. A 48 horas el modelo
empieza a aportar, y las variables más importantes son precisamente las de pronóstico de
lluvia — lo cual confirma que el modelo está aprendiendo lo correcto.

**Qué hacer con esto:**

1. **No inventes.** Reporta el número real, con su línea base. Un proyecto que dice
   "el modelo mejoró 1% sobre la persistencia a 48 h" es infinitamente más serio que uno
   que dice "usamos inteligencia artificial" sin comparar contra nada.
2. **Re-evalúa con datos reales.** Los datos sintéticos tienen lluvia puramente aleatoria.
   El suelo real tiene curvas de secado con estructura que el modelo puede aprender mejor.
3. **Prioriza el horizonte de 48 h** en el dashboard y en el informe.
4. Si con datos reales el modelo tampoco gana, **eso también es un resultado publicable**:
   significa que para este predio el balance hídrico FAO-56 es suficiente y el ML no aporta.
   Decirlo con honestidad vale más que forzar un número.

**Cuántos datos necesitas:** mínimo 200 registros para que corra; con 30 días (≈2.900
registros por profundidad) el modelo es razonable.

## Pruebas rápidas

```bash
# Motor FAO-56
python -m ia.fao56

# Cliente de clima
python -m ia.clima

# Calibrar un sensor
python -m ia.calibracion --sensor S1 --datos 3050,0 2740,11.5 2380,23.0 2010,34.5 1720,46.0
```
