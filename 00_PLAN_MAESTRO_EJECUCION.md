# HidroSopó — Plan Maestro de Ejecución

**Sistema Inteligente de Monitoreo Ambiental y Optimización del Uso del Agua (IoT + IA) — Municipio de Sopó, Cundinamarca**

Documento operativo de ejecución. Complementa (no reemplaza) la propuesta presentada al FOES.

- **Ejecutor:** Jose Alejandro Pulido Gómez — Ing. Mecatrónica, 6° semestre, Uniagustiniana
- **Duración:** 4 meses
- **Ventana asumida:** Mes 1 = septiembre 2026 → Mes 4 = diciembre 2026 *(ajustar a la fecha real de acta de inicio)*
- **Producto final comprometido:** Póster científico + prototipo funcional + informe técnico

---

## 0. Dos advertencias antes de arrancar (léelas)

Te las digo de frente porque afectan el diseño del proyecto:

### 0.1 La articulación es municipal, no regional

El alcance institucional de este proyecto es **el municipio de Sopó**: Emsersopó E.S.P.,
la Alcaldía y la Secretaría de Ambiente. El PUEAA es un programa local, con dolientes
locales, y ahí es donde el proyecto puede aportar en cuatro meses.

Lo que se construye:

| Lo que la gente imagina | Lo que realmente se construye |
|---|---|
| Una integración automática con entidades | Un **anexo técnico** con indicadores medidos, generado automáticamente y listo para entregar |
| Un login contra sistemas de gobierno | Un **exportador CSV** de indicadores para que el municipio los integre a su gestión |
| Un trámite ambiental resuelto por software | Un **panel de solo lectura** para la entidad + una carta de intención |

**Traducción:** el proyecto no "se conecta" a ninguna entidad. Produce **evidencia medida
y trazable** y se articula institucionalmente con el municipio. Eso es defendible y se puede
demostrar. Si prometes una integración automática que no existe, te lo tumban en la
sustentación.

### 0.2 El caudalímetro no es opcional — es el corazón regulatorio

La propuesta original solo tiene humedad de suelo y temperatura. Con eso **no puedes demostrar ahorro de agua**, solo puedes decir "el suelo estaba húmedo". El PUEAA no mide humedad: mide **metros cúbicos captados**.

Agregar un **caudalímetro de pulsos en la captación** (~$45.000–90.000 COP) convierte el proyecto de "sensor bonito" a "instrumento que mide el recurso". Es el cambio más importante de todo este documento.

---

## 1. La tesis del proyecto (cómo lo vendes)

> En Sopó, las pequeñas fincas de pastoreo lechero y los predios agrícolas menores riegan por intuición. No tienen forma de saber cuánta agua usan ni de demostrarlo. HidroSopó mide el agua que realmente entra al predio, calcula cuánta necesita el cultivo o el pasto usando el método FAO-56, y le dice al productor —en español, por WhatsApp o en una app en su celular— si debe regar hoy, cuánto, o si le conviene esperar la lluvia. Y genera automáticamente los indicadores de uso eficiente que el PUEAA municipal necesita.

Tres beneficiarios en una sola caja:

1. **El productor** → ahorra agua y plata, y tiene datos para su concesión.
2. **Emsersopó / Alcaldía** → indicadores reales de demanda rural para actualizar el PUEAA.
3. **Alcaldía / Secretaría de Ambiente** → caracterización real del uso del agua en el sector rural del municipio.

### Timing institucional (usa esto, es tu mejor carta)

El PUEAA de **EMSERSOPÓ E.S.P. fue aprobado en 2017 y actualizado en enero de 2021, con un horizonte de 5 años**. Ese horizonte ya venció. Y el **Plan de Acción 2024–2027 de Emsersopó incluye explícitamente "Actualizar, implementar y realizar seguimiento al Programa de Uso Eficiente y Ahorro del Agua – PUEAA"**.

Es decir: **están obligados a actualizar el PUEAA justo ahora, y tú llegas con la herramienta que produce los datos.** Ese es tu argumento de entrada a la reunión. No llegas pidiendo, llegas resolviéndoles un pendiente del plan de acción.

---

## 2. Arquitectura del sistema

```
                          ┌─────────────────────────────┐
   CAMPO                  │  NODO SENSOR (ESP32+LoRa)   │
                          │  · Humedad suelo x3 prof.   │
                          │  · Temp. suelo (DS18B20)    │
                          │  · Temp/HR aire (SHT31)     │
                          │  · Pluviómetro (reed)       │
                          │  · Batería 18650 + solar    │
                          └──────────────┬──────────────┘
                                         │ LoRa 915 MHz (1–3 km)
                          ┌──────────────▼──────────────┐
   CAPTACIÓN              │  NODO CAUDAL (ESP32+LoRa)   │
   (bocatoma/pozo/tanque) │  · Caudalímetro de pulsos   │
                          │  · Contador acumulado m³    │
                          └──────────────┬──────────────┘
                                         │ LoRa
                          ┌──────────────▼──────────────┐
   CASA DE FINCA          │  GATEWAY (ESP32 + WiFi)     │
                          │  · Recibe LoRa              │
                          │  · Buffer en SPIFFS         │
                          │  · POST HTTPS al backend    │
                          └──────────────┬──────────────┘
                                         │ Internet
   ┌─────────────────────────────────────▼──────────────────────────────┐
   │  BACKEND (FastAPI + PostgreSQL)          — gratis en Oracle/Render │
   │                                                                     │
   │  ┌────────────┐  ┌──────────────────┐  ┌────────────────────────┐ │
   │  │ Ingesta    │  │ MOTOR IA         │  │ Módulo PUEAA           │ │
   │  │ /api/v1/   │→ │ · ET0 FAO-56     │→ │ · Indicadores Res.1257 │ │
   │  │ telemetria │  │ · Balance hídrico│  │ · Reporte PDF/XLSX     │ │
   │  │            │  │ · ML humedad 48h │  │ · Panel institucional  │ │
   │  │            │  │ · Reglas agro    │  │ · Export CSV           │ │
   │  └────────────┘  └──────────────────┘  └────────────────────────┘ │
   │         ▲                  ▲                                       │
   │         │                  │ Open-Meteo API (gratis, sin llave)    │
   └─────────┼──────────────────┴───────────────────────────────────────┘
             │
   ┌─────────┴───────────┬─────────────────────┬──────────────────────┐
   │ App móvil (PWA)     │ Alertas WhatsApp    │ Panel institucional  │
   │ productor           │ / Telegram          │ Emsersopó (lectura)  │
   └─────────────────────┴─────────────────────┴──────────────────────┘
```

### Por qué LoRa y no WiFi puro

La propuesta original dice "ESP32 + WiFi". En una finca de pastoreo eso **no funciona**: el potrero está a 300–1500 m de la casa y el router no llega. Vas a montar el nodo, va a funcionar el día de la demo al lado del router, y en campo se cae.

LoRa a 915 MHz (banda ISM Región 2, la correcta para Colombia — verifica el cuadro de atribución de la ANE) te da 1–3 km en línea de vista con ~$35.000 COP extra por nodo. Es la decisión técnica que salva el piloto.

El firmware incluye ambos modos (`#define TRANSPORTE_LORA` / `TRANSPORTE_WIFI`) para que puedas empezar con WiFi en la mesa de laboratorio y pasar a LoRa en campo sin reescribir nada.

---

## 3. El módulo de IA — cómo hacerlo gratis y que sea IA de verdad

Esta es la pregunta que más importa, así que la respondo en detalle.

### 3.1 ¿Qué significa "IA" aquí sin hacer trampa?

Hay tres capas, y las tres son gratis:

**Capa 1 — Modelo físico determinista (FAO-56).** No es machine learning, es el estándar mundial de agronomía. Calcula la evapotranspiración de referencia (ET0) por Penman-Monteith, la multiplica por el coeficiente de cultivo (Kc) y obtiene ETc = cuánta agua consume realmente ese cultivo hoy. Con eso haces un **balance hídrico del suelo**: entra lluvia + riego, sale ETc, y sabes exactamente cuándo el suelo va a llegar al umbral de estrés.

Costo: $0. Es matemática. El código está en `03_backend/ia/fao56.py`.

**Capa 2 — Machine learning real (scikit-learn, local).** Entrenas un `GradientBoostingRegressor` con los datos de **tu propio predio** para predecir la humedad del suelo a 24 y 48 horas, usando como features: humedad actual, ET0 pronosticada, lluvia pronosticada, temperatura, hora del día, profundidad. Con 30 días de datos ya tienes un modelo útil.

Esto es lo que justifica la palabra "Inteligencia Artificial" ante el jurado: **es un modelo entrenado con datos, no un `if`**. Y corre en tu propio servidor, sin costo de API.

Costo: $0. scikit-learn es open source. El código está en `03_backend/ia/entrenar_modelo.py`.

**Capa 3 — LLM para redactar la recomendación en lenguaje natural (opcional).** Convierte `{deficit: 12.4mm, prob_lluvia: 0.8}` en *"Don Jaime, hoy no riegue. El suelo tiene humedad para 2 días más y hay 80% de probabilidad de lluvia mañana en la tarde. Le ahorra unos 14 mil litros."*

Opciones gratis, en orden de recomendación:

| Opción | Costo | Nota |
|---|---|---|
| **Plantillas en español** (incluidas) | $0, sin dependencias | Recomendado para el piloto. No falla, no se cae, no gasta cuota |
| **Groq API** (free tier) | $0 con límite generoso | Muy rápido, Llama 3.x |
| **Google Gemini API** (free tier) | $0 con límite diario | Buena calidad en español |
| **Ollama local** (Llama 3.2 3B) | $0 total | Corre en el PC del estudiante, sin internet |

El código trae la plantilla funcionando y un adaptador LLM opcional que se activa con una variable de entorno. **Para la sustentación, la Capa 2 es la que importa.** La Capa 3 es cosmética.

### 3.2 Datos meteorológicos gratis

**Open-Meteo** (`api.open-meteo.com`): gratis, sin API key, sin registro, uso no comercial. Y lo mejor: **ya entrega `et0_fao_evapotranspiration` calculada**, además de pronóstico de lluvia por hora a 7–16 días para las coordenadas exactas del predio.

Complemento: **IDEAM** publica datos de estaciones en `dhime.ideam.gov.co` (descarga manual, sirve para validar y para el marco teórico del informe).

### 3.3 Hosting gratis del backend

| Opción | Ventaja | Riesgo |
|---|---|---|
| **Oracle Cloud Always Free** ⭐ | 4 vCPU ARM + 24 GB RAM, gratis para siempre, sin spin-down | Registro pide tarjeta (no cobra) |
| Render free tier | Deploy en 5 min desde GitHub | **Se duerme a los 15 min** de inactividad → el gateway debe reintentar |
| Fly.io free | Buen middle ground | Cuota limitada |
| Supabase free | PostgreSQL + Auth + API REST gratis | Pausa proyectos tras 1 semana inactiva |
| **Raspberry Pi en la finca + Cloudflare Tunnel** | Control total, sin nube | Depende de la internet de la finca |

**Recomendación:** Supabase (base de datos) + Render (API). Si Render duerme, el gateway tiene buffer en SPIFFS y reintenta — ya está resuelto en el firmware. Para producción, migrar a Oracle Always Free.

---

## 4. Adaptabilidad: cultivo vs. pastoreo

Este es el requisito de "que se adapte según la necesidad". Se resuelve con un **sistema de perfiles agronómicos** (`03_backend/ia/perfiles.py`), no con código distinto.

Cada perfil define:

| Parámetro | Qué es | Kikuyo (pastoreo) | Papa | Fresa |
|---|---|---|---|---|
| `kc_inicial / medio / final` | Coef. de cultivo FAO-56 | 0.85 / 1.00 / 0.90 | 0.50 / 1.15 / 0.75 | 0.40 / 0.85 / 0.75 |
| `profundidad_raiz_m` | Zona radicular efectiva | 0.30–0.60 | 0.40–0.60 | 0.20–0.30 |
| `mad` (p) | Agotamiento permisible antes de estrés | 0.55 | 0.35 | 0.20 |
| `modo` | Lógica de decisión | pastoreo rotacional | riego programado | riego frecuente |

**Diferencia clave de la lógica:**

- **Modo cultivo:** el objetivo es no dejar que el suelo baje del umbral de estrés. Recomienda lámina de riego en mm y su equivalente en litros y en minutos de bombeo.
- **Modo pastoreo:** el objetivo es la **tasa de rebrote del pasto**. Aquí el sistema no solo dice "riegue", dice *"franja 4 lista para pastoreo en 3 días"* combinando humedad + grados-día acumulados + días de descanso. Para ganadería lechera de Sopó (kikuyo/raigrás) esto vale más que el riego mismo.

Perfiles incluidos: `kikuyo_pastoreo`, `raigras_pastoreo`, `pasto_corte`, `papa`, `hortalizas_hoja`, `fresa`, `mora`, `generico`.

Agregar un perfil nuevo = agregar un diccionario. Sin tocar el motor.

---

## 5. Cronograma real de ejecución (16 semanas)

El cronograma de la propuesta es correcto pero está en granularidad de mes. Esta es la versión de trabajo.

### MES 1 — Diagnóstico y diseño

| Sem | Actividad | Entregable verificable |
|---|---|---|
| 1 | Selección del predio piloto. Visita técnica. Levantamiento de la fuente de agua (¿quebrada, pozo, acueducto veredal? ¿diámetro de la tubería?). Georreferenciación con GPS del celular. | Ficha de caracterización del predio + coordenadas + fotos |
| 2 | Firma del **consentimiento informado**. Entrevista al productor: ¿cómo decide regar hoy? ¿cuántas horas bombea? ¿qué le duele? | Consentimiento firmado + acta de diagnóstico |
| 3 | Compra de componentes (lista en `01_hardware/BOM.md`). Diseño del esquema eléctrico. Cálculo del presupuesto energético. | Orden de compra + esquemático |
| 4 | Diseño CAD del encapsulado y la estaca. Impresión 3D o corte. | Archivos `.scad`/`.stl` + piezas físicas |

**Hito 1:** predio confirmado, consentimiento firmado, componentes comprados.

### MES 2 — Instrumentación y plataforma

| Sem | Actividad | Entregable |
|---|---|---|
| 5 | Montaje del nodo en protoboard. Firmware básico: leer los 6 sensores e imprimir por serial. | Video de lecturas en vivo |
| 6 | **Calibración gravimétrica** de los sensores de humedad (procedimiento en `01_hardware/CALIBRACION.md`). Este paso es el que separa un proyecto serio de uno de feria. | Curva de calibración + R² por sensor |
| 7 | Backend: base de datos, endpoint de ingesta, autenticación por token. Deploy en Render/Supabase. | URL pública funcionando |
| 8 | Dashboard v1: gráficas de humedad, temperatura, lluvia. Enlace LoRa gateway↔nodo probado a 500 m. | Dashboard con datos reales |

**Hito 2:** datos del nodo llegando a la nube y visibles en el dashboard.

### MES 3 — IA e instalación en campo

| Sem | Actividad | Entregable |
|---|---|---|
| 9 | Motor FAO-56 + balance hídrico + integración Open-Meteo. Perfiles agronómicos. | Recomendaciones generadas |
| 10 | **Instalación definitiva en campo.** Nodo de suelo + nodo de caudal + gateway. Prueba de autonomía energética 72 h. | Sistema instalado, fotos, acta |
| 11 | Alertas WhatsApp/Telegram al productor. Módulo de reporte PUEAA. | Productor recibiendo mensajes |
| 12 | Entrenamiento del modelo ML con los datos acumulados. Validación cruzada. | Métricas MAE/R² del modelo |

**Hito 3:** sistema operando en campo y enviando recomendaciones.

> **Semana 11 — reunión institucional.** Radicar la carta a Emsersopó + Secretaría de Ambiente + Secretaría de Desarrollo Económico (plantilla en `05_institucional/`). Esta reunión hay que agendarla en la semana 8, no en la 11.

### MES 4 — Validación y cierre

| Sem | Actividad | Entregable |
|---|---|---|
| 13 | Comparación cuantitativa: consumo del período piloto vs. línea base declarada por el productor. | Tabla de ahorro con m³ medidos |
| 14 | Ajustes finales. Encuesta de usabilidad al productor. | Sistema estable + encuesta |
| 15 | Informe técnico final. Reporte PUEAA de demostración. | Documento entregable |
| 16 | **Póster científico** + sustentación. Repositorio GitHub público con licencia. | Póster impreso + repo |

**Hito 4:** póster + informe + evidencia de ahorro.

### El riesgo #1 del cronograma

La línea base. Si no mides el consumo **antes** de intervenir, no puedes demostrar ahorro. Instala el caudalímetro en la **semana 5–6**, no en la semana 10. Necesitas mínimo 3–4 semanas de "cómo regaba antes" para comparar contra 4–5 semanas de "cómo riega con el sistema".

Si arrancas a medir en la semana 10, tu conclusión va a ser "no se pudo cuantificar el ahorro" — y ese es exactamente el resultado que el FOES no quiere leer.

**Acción concreta:** mueve el caudalímetro al Mes 2, semana 5. Es un cambio de una línea en el cronograma que salva el resultado del proyecto.

---

## 6. Presupuesto

Ver `01_hardware/BOM.md` para el detalle con proveedores.

| Rubro | COP (aprox.) |
|---|---|
| Nodo de suelo completo (ESP32+LoRa, 3 sensores humedad, DS18B20, SHT31, solar, batería) | $420.000 |
| Nodo de caudal (ESP32+LoRa, caudalímetro, solar) | $230.000 |
| Gateway (ESP32+LoRa, fuente) | $95.000 |
| Encapsulados, estacas, cableado, prensaestopas, silicona | $150.000 |
| Impresión 3D / mecanizado | $80.000 |
| Herramienta y consumibles | $120.000 |
| Contingencia 15% | $165.000 |
| **Total hardware** | **≈ $1.260.000** |
| Software, nube, IA | **$0** |
| Impresión póster 90×120 cm | $60.000 |

Los precios son referenciales de mercado colombiano y cambian; verifica en Sigma Electrónica, Vistrónica, Didácticas Electrónicas y MercadoLibre CO antes de comprar. Puedes recortar a ~$800.000 usando un solo nodo de suelo con un sensor de humedad y DHT22 en vez de SHT31, pero pierdes el perfil de humedad por profundidad, que es un diferenciador fuerte del proyecto.

---

## 7. Ruta institucional — PUEAA municipal

Detalle completo en `05_institucional/04_protocolo_pueaa_municipal.md`.

### Fase A — Indicadores (dentro de los 4 meses)

El sistema calcula automáticamente los indicadores de uso eficiente que el programa
necesita: volumen captado (m³), caudal medio y máximo (l/s), módulo de consumo (l/s/ha),
lámina aplicada (mm), eficiencia de aplicación (%), percolación bajo raíz, precipitación
efectiva y **ahorro medido contra la línea base**.

Referencia conceptual: Ley 373 de 1997, Decreto 1090 de 2018 y Resolución 1257 de 2018,
que definen qué contiene un PUEAA. El sistema produce un **anexo técnico**, no un trámite.

### Fase B — Articulación (empieza en el mes 2)

**Orden de las reuniones:**

1. **Secretaría de Ciencia, Tecnología e Innovación de Sopó** — tu contraparte del estímulo.
   Empieza aquí siempre. Ellos te abren las demás puertas.
2. **Emsersopó E.S.P.** — el argumento es el pendiente del PUEAA en su Plan de Acción
   2024–2027. Ofrece un panel de solo lectura con la demanda hídrica rural real.
3. **Secretaría de Ambiente y Desarrollo Agropecuario** — replicabilidad y articulación
   con la asistencia técnica rural.

**Solicita la cita con Emsersopó en la semana 8**, para reunirte en la 11 con datos en mano.
Los tiempos institucionales se miden en semanas.

### Lo que NO debes prometer

- ❌ "Integración automática con entidades del Estado"
- ❌ "El sistema resuelve el trámite ambiental"
- ✅ "Genera automáticamente los indicadores de uso eficiente del agua, medidos y trazables,
  como insumo para el PUEAA municipal" → esto sí, y suena igual de fuerte.

## 8. Riesgos y mitigación

| Riesgo | Prob. | Mitigación |
|---|---|---|
| El productor se retira del piloto | Media | Tener 2 predios candidatos desde la semana 1. Consentimiento con cláusula de retiro clara |
| Robo o daño del equipo en campo | Media | Encapsulado discreto, sin logos, anclado. Nodo a >$400k solo si el predio es seguro |
| El sensor capacitivo se degrada / lecturas erráticas | Alta | Calibración gravimétrica + sellado con resina epóxica del cabezal electrónico + validación cruzada entre 3 sensores |
| No hay internet estable en la finca | Alta | Buffer en SPIFFS del gateway (hasta 2000 registros) + reintento exponencial. Ya implementado |
| Batería no aguanta días nublados | Media | Deep sleep + 2×18650 (5000 mAh) + panel 10 W = 8 días de autonomía sin sol. Cálculo en `01_hardware/ENERGIA.md` |
| No se logra demostrar ahorro | **Alta si no mueves el caudalímetro** | Instalar caudalímetro en semana 5 para tener línea base |
| Emsersopó no responde | Media | El proyecto es válido sin ellos. La articulación es un plus, no una dependencia crítica |

---

## 9. Cómo se ve el "éxito" en la sustentación

El jurado del FOES va a preguntar tres cosas. Ten la respuesta lista:

**"¿Cuánta agua ahorró?"**
→ Tabla: consumo semanal medido con caudalímetro, línea base (sem 5–8) vs. período con sistema (sem 10–15), % de reducción, m³ absolutos, equivalente en pesos según tarifa.

**"¿Dónde está la inteligencia artificial?"**
→ Modelo `GradientBoostingRegressor` entrenado con N registros del predio, features X, predice humedad a 48 h con MAE de Y%. Muestra la gráfica de predicho vs. real. Eso es ML verificable, no un `if`.

**"¿Esto se puede replicar?"**
→ Costo por predio, repositorio abierto, sistema de perfiles que soporta cultivo y pastoreo sin recodificar, e indicadores alineados con lo que el PUEAA necesita.

---

## 10. Estructura del paquete que estás recibiendo

```
hidrosopo/
├── 00_PLAN_MAESTRO_EJECUCION.md   ← este archivo
├── 01_hardware/
│   ├── BOM.md                     lista de materiales con proveedores CO
│   ├── CONEXIONES.md              pinout y esquema de cableado
│   ├── CALIBRACION.md             procedimiento gravimétrico
│   ├── ENERGIA.md                 cálculo del presupuesto energético
│   └── cad/
│       ├── caja_nodo.scad         encapsulado IP65 paramétrico
│       ├── estaca_sensor.scad     estaca de instalación en suelo
│       └── soporte_solar.scad     soporte de panel con ángulo Sopó
├── 02_firmware/                   código ESP32 (PlatformIO)
├── 03_backend/                    API + motor de IA + módulo PUEAA
├── 04_dashboard/                  interfaz web del productor
├── 05_institucional/              cartas, consentimiento, protocolo
└── 06_datos/                      generador de datos sintéticos para pruebas
```

Cada carpeta tiene su propio README con instrucciones de puesta en marcha.

---

## 11. Qué hacer en las próximas 72 horas

1. Confirmar la fecha real del acta de inicio y ajustar el cronograma.
2. Definir el predio piloto y hacer la primera visita. Sin predio no hay proyecto.
3. Averiguar cómo capta el agua ese predio (quebrada, pozo, acueducto veredal) y si tiene algún permiso. Es un dato del reporte, no un requisito para arrancar.
4. Cotizar el BOM y hacer la compra. Los tiempos de importación de sensores desde China son de 3–5 semanas — si vas a importar algo, pídelo esta semana.
5. Agendar la reunión con la Secretaría de CTeI de Sopó.
6. Actualizar la propuesta FOES: agregar el caudalímetro a la tabla de recursos, y redactar la articulación institucional como "generación de indicadores de uso eficiente del agua para el PUEAA municipal, liderado por Emsersopó E.S.P.".
