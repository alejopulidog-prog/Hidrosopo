# Plan de Escalamiento — de 1 predio a N

Documento de futuro. **No lo ejecutes durante los 4 meses del FOES**: el compromiso es
un prototipo validado en un predio piloto, y meterle alcance a eso es la forma más común
de no entregar nada.

Pero sí conviene tenerlo escrito desde ya, por dos razones: (1) las decisiones técnicas
que tomas hoy determinan si mañana puedes escalar o si toca reescribir todo, y (2) en la
sustentación te van a preguntar "¿y esto se puede replicar?" — y tener este documento es
una respuesta mucho mejor que un "sí, claro".

---

## 1. Qué ya está listo para escalar (y qué no)

El sistema se diseñó multi-predio desde el principio. Esto no es casualidad, es la
decisión de arquitectura que más plata te ahorra después.

| Componente | ¿Escala hoy? | Qué falta |
|---|---|---|
| Base de datos | ✅ Sí — `predio_id` en todas las tablas | Nada |
| Motor FAO-56 | ✅ Sí — es una función pura | Nada |
| Perfiles agronómicos | ✅ Sí — agregar cultivo = agregar un diccionario | Más perfiles locales |
| Ingesta de telemetría | ✅ Sí — un token por nodo | Rate limiting |
| Reporte de indicadores | ✅ Sí — por predio y período | Reporte consolidado municipal |
| Panel institucional | ✅ Sí — ya agrega varios predios | Filtros por vereda y fecha |
| Modelo ML | ⚠️ Uno por predio | Modelo global + ajuste por predio |
| **Autenticación** | ❌ **No existe** | **Es el bloqueo #1** |
| Roles y permisos | ❌ No existe | Productor / técnico / institucional |
| Gestión de nodos | ❌ Manual, por consola | Pantalla de administración |
| Alertas técnicas | ⚠️ Parcial | Nodo caído, batería baja, sin datos |

**Traducción:** con 1–3 predios el sistema funciona tal cual. Del cuarto en adelante,
lo primero que necesitas es autenticación. Sin eso, cualquiera con la URL ve los datos
de todos los productores, y eso rompe el compromiso del consentimiento informado.

---

## 2. Las tres fases

### Fase 1 — Piloto (los 4 meses del FOES)

**Alcance:** 1 predio, 2 nodos, 1 productor.
**Objetivo:** demostrar que funciona y que ahorra agua.
**Entregable:** póster, informe, prototipo.

Esto es lo comprometido. No más.

### Fase 2 — Validación multi-predio (6–8 meses después)

**Alcance:** 5–10 predios de distintas veredas y sistemas productivos.
**Objetivo:** demostrar que el ahorro no fue suerte de un predio.

Qué hay que construir:

1. **Autenticación y roles** (2 semanas)
   - Productor: ve solo su predio
   - Técnico: ve los predios que administra
   - Institucional: ve indicadores agregados, sin nombres
   - Usar tokens JWT; FastAPI ya trae soporte

2. **Pantalla de administración** (2 semanas)
   - Alta de predios y nodos sin tocar la consola
   - Estado de nodos en tiempo real
   - Gestión de calibraciones por sensor

3. **Alertas técnicas automáticas** (1 semana)
   - Nodo sin reportar > 2 h
   - Batería por debajo de 3.5 V
   - Caudal anómalo (posible fuga)
   - Estas van al técnico, no al productor

4. **Modelo ML global** (2 semanas)
   - Un modelo entrenado con todos los predios, ajustado por predio
   - Con 10 predios × 6 meses tienes ~1M de registros: ahí el ML sí se vuelve fuerte
   - Este es el punto donde el modelo por fin le gana claramente a la persistencia

5. **Reporte consolidado municipal** (1 semana)
   - Demanda hídrica rural total, por vereda y por tipo de actividad
   - Este es el producto que le interesa a Emsersopó y a la Alcaldía

**Costo estimado:** ~$1.2M COP por predio en hardware (economías de escala en la compra),
$0 en software. Total 10 predios: ~$12M COP.

### Fase 3 — Operación sostenida (año 2+)

**Alcance:** 30–100 predios.
**Objetivo:** que el sistema siga vivo sin depender de una sola persona.

Aquí el problema deja de ser técnico y pasa a ser de sostenibilidad. Ver sección 4.

Qué se necesita técnicamente:

- Migrar a **LoRaWAN** con gateways compartidos en vez de enlaces punto a punto
- Fabricación de PCB propia en vez de módulos sueltos (baja el costo ~35% y sube la
  confiabilidad enormemente)
- Base de datos de series temporales (TimescaleDB) en vez de PostgreSQL plano
- Monitoreo de infraestructura (Grafana + alertas)

---

## 3. Cómo baja el costo al escalar

| | 1 predio | 10 predios | 50 predios |
|---|---:|---:|---:|
| Hardware por predio | $1.720.000 | ~$1.150.000 | ~$700.000 |
| Por qué baja | — | Compra al por mayor, sin herramienta repetida | PCB propia, importación directa, gateway compartido |
| Software / nube | $0 | $0 | ~$180.000/año (servidor propio) |
| Tiempo de instalación | 2 días | ~4 h por predio | ~2 h por predio |

El salto grande está en el **gateway compartido**: un gateway LoRa en un punto alto puede
cubrir 8–15 predios en un radio de 3–5 km. Eso elimina un ESP32 y una instalación por
predio.

En Sopó, con la topografía de la Sabana, un gateway bien ubicado en una loma podría cubrir
buena parte de una vereda. Vale la pena hacer un estudio de cobertura antes de la Fase 3.

---

## 4. Sostenibilidad: el problema real

La pregunta que hunde el 90% de estos proyectos: **¿quién lo mantiene cuando el estudiante
se gradúa?**

Tenla contestada antes de que te la hagan.

### Opción A — Transferencia al municipio

El municipio adopta el sistema, lo opera desde la Secretaría de Ambiente o desde
Emsersopó, y contrata o asigna a alguien para el mantenimiento.

- ✅ Sostenible de verdad, llega a más gente
- ❌ Depende de voluntad política y de presupuesto; los cambios de administración matan proyectos
- **Qué necesitas:** documentación impecable, código abierto, y capacitación a alguien de planta

### Opción B — Asociación de productores

Una asociación local (de ganaderos, por ejemplo) adopta el sistema para sus asociados y
paga una cuota que cubre el mantenimiento.

- ✅ Los usuarios tienen incentivo directo, no depende de política
- ❌ Requiere que exista una asociación organizada y con capacidad de pago
- **Qué necesitas:** demostrar el ahorro en pesos, no en metros cúbicos

### Opción C — Emprendimiento

Convertirlo en producto y venderlo o alquilarlo.

- ✅ Sostenible por sí mismo, y puede escalar más allá de Sopó
- ❌ Es un trabajo de tiempo completo; competir con soluciones comerciales existentes
- **Qué necesitas:** validación de disposición a pagar, y decidir si quieres ser empresario

### Opción D — Investigación universitaria

Queda como plataforma de investigación de la Uniagustiniana; los siguientes semestres
lo continúan como proyectos de grado.

- ✅ Continuidad garantizada, cero costo, genera publicaciones
- ❌ Avanza lento, cambia de manos cada semestre
- **Qué necesitas:** un docente que lo adopte como línea de trabajo

### Lo que yo recomendaría

**D + A en paralelo.** Deja el proyecto como línea de investigación en la universidad
(asegura continuidad) mientras negocias la transferencia al municipio (asegura impacto).
Si en el camino aparece interés real de una asociación de productores, entonces evalúas B.

No arranques por C. El emprendimiento es una decisión de vida, no un paso siguiente
obvio de un proyecto académico.

---

## 5. Decisiones de hoy que afectan el mañana

Estas ya están tomadas en el código, y por buenas razones. No las cambies sin pensarlo.

| Decisión | Por qué escala |
|---|---|
| `predio_id` en todas las tablas desde el día uno | Agregar predios no requiere migración |
| Perfiles agronómicos como datos, no como código | Agregar un cultivo no requiere programar |
| Contador de caudal **acumulado histórico**, no por período | Sobrevive cortes de energía y reinicios; auditable |
| Buffer local en el nodo y en el gateway | La red de la finca se cae; los datos no se pierden |
| Reporte generado desde la base, no escrito a mano | Un predio o cincuenta, el mismo código |
| Todo el software es abierto y sin licencias | Nadie queda amarrado a un proveedor |
| PWA en vez de app nativa | Actualizar 50 celulares es subir un archivo |
| Datos institucionales anonimizados por diseño | El compromiso con el productor se mantiene al escalar |

---

## 6. Lo que NO debes hacer

1. **No escales durante los 4 meses.** Es la tentación más grande y el error más común.
   Un predio funcionando y medido vale más que cinco a medias.
2. **No agregues predios sin autenticación.** Rompe el consentimiento informado que
   firmaste. Es un problema ético, no técnico.
3. **No prometas escalamiento en la propuesta.** Preséntalo como "potencial de réplica",
   que es lo que es.
4. **No compres hardware para 10 predios de una.** Espera a validar el diseño en uno.
   Los componentes cambian, y vas a querer ajustar el diseño después del primero.
5. **No dependas de un solo predio piloto.** Ten un segundo candidato identificado desde
   la semana 1, por si el primero se retira.

---

## 7. Métricas de éxito para decidir si vale la pena escalar

Al final de la Fase 1, revisa esto honestamente:

| Métrica | Umbral para seguir |
|---|---|
| Ahorro de agua medido | > 15% frente a la línea base |
| Disponibilidad del sistema | > 85% de cobertura de datos |
| El productor siguió las recomendaciones | > 60% de las veces |
| El productor quiere seguir usándolo | Sí / No — **esta es la más importante** |
| Costo por predio | < $1.500.000 COP |
| Interés institucional real | Al menos una carta de intención |

Si el productor dice que no le sirvió, no escales. Arregla eso primero. Un sistema que
mide muy bien pero que nadie usa no ahorra un solo litro de agua.
