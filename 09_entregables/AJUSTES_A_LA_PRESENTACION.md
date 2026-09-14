# Ajustes a la presentación y respuestas para la sustentación

Revisión de `Presentacion_FOES_Sopo_Alejandro_Pulido_.pptx` (8 diapositivas, 5 minutos)
contra lo que quedó construido en el paquete.

La presentación está bien armada: buena estructura, notas del orador con tiempos, cierre
claro. Lo que sigue no es una crítica, son **desajustes que aparecieron porque el diseño
técnico avanzó después de hacerla**.

---

## 1. Cinco cosas que ya no coinciden

### 1.1 La diapositiva 4 dice "ESP32 + WiFi"

**El problema:** en una finca de pastoreo el potrero está a 300–1500 m de la casa. El
router no llega. El nodo funcionaría el día de la demo al lado del WiFi y se caería en
campo.

**Lo que se construyó:** ESP32 + **LoRa 915 MHz**, con un gateway en la casa que sube los
datos por WiFi. Alcance de 1–3 km por unos $35.000 extra por nodo.

**Qué hacer:** cambiar "ESP32 + WiFi" por "ESP32 + LoRa 915 MHz" en el diagrama, y agregar
la caja del gateway. Si ya presentaste con esta versión, no es problema: en la
sustentación final lo presentas como una decisión de diseño tomada durante la ejecución,
que es exactamente lo que fue. Eso se ve bien, no mal.

### 1.2 No aparece el caudalímetro

**Este es el desajuste más importante.** La presentación habla de "uso más eficiente del
agua" y "menores costos de riego", pero los sensores listados solo miden humedad y
temperatura.

Con humedad y temperatura **no se puede demostrar ahorro de agua**. Solo se puede decir
"el suelo estaba húmedo". El PUEAA no mide humedad: mide metros cúbicos.

**Qué hacer:** agregar el caudalímetro al diagrama de la diapositiva 4 y a la lista de
sensores de la 3. Es una línea, y es la que sostiene todo el argumento de impacto.

### 1.3 "Recomendaciones de riego basadas en IA" es vago

Es la frase que un jurado técnico va a atacar. Ahora tienes la versión defendible:

> Un modelo físico de balance hídrico según el estándar FAO-56, más un modelo de
> aprendizaje automático entrenado con los datos del propio predio, validado contra una
> línea base de persistencia.

Eso es específico, es verificable, y **nombra la línea base**, que es lo que separa un
proyecto de ingeniería de una demostración.

### 1.4 La diapositiva 7 dice "menores costos" sin cifra

Ahora el sistema calcula el ahorro en pesos, separado por partida:

| Caso | Agua | Energía | Total por m³ |
|---|---:|---:|---:|
| Quebrada propia + bomba eléctrica | $0 | $190 | $190 |
| Acueducto veredal + bomba eléctrica | $1.800 | $105 | $1.905 |
| Pozo + motobomba diésel | $0 | $2.600 | $2.600 |

En la sustentación final esa tabla, con los datos reales del predio piloto, vale más que
las tres viñetas de impacto juntas.

### 1.5 No aparece que el productor puede responderle al sistema

La presentación describe un flujo de una sola vía: sensor → nube → recomendación.

Lo que se construyó es bidireccional: el productor reporta cuánto regó, cuenta su rutina,
pregunta por el ahorro, y puede decir que **no está de acuerdo** — y ese desacuerdo se
registra y alerta al técnico, porque suele significar que el sensor está mal calibrado.

Es un diferenciador fuerte y no está en el deck.

---

## 2. Las preguntas del jurado, con las respuestas reales

### "¿Cuánta agua se ahorró?"

No respondas con porcentajes solos. Muestra la tabla:

| | Línea base (sem. 5–8) | Con el sistema (sem. 10–15) |
|---|---:|---:|
| Consumo medido | X m³ | Y m³ |
| Promedio diario | X/día | Y/día |
| Reducción | — | Z% |
| En pesos | — | $N |

Y si el ahorro fue menor al esperado, dilo con el contexto climático. Un dato real
pequeño vale más que uno inflado.

### "¿Dónde está la inteligencia artificial?"

> Es un `GradientBoostingRegressor` de scikit-learn, entrenado con N registros del predio.
> Predice el cambio de humedad del suelo a 48 horas. Lo comparo siempre contra una línea
> base de persistencia — "la humedad de pasado mañana será igual a la de hoy" — porque si
> el modelo no le gana a eso, el modelo no sirve.

Muestra la gráfica de predicho contra real y el recuadro de comparación.

**Si el modelo no le ganó a la persistencia, dilo.** Eso también es un resultado, y
reportarlo con honestidad te va a dejar mejor parado que forzar un número. La frase:
*"para este predio y este período, el balance hídrico FAO-56 fue suficiente y el modelo
de aprendizaje no aportó mejora significativa"* es una conclusión científica válida.

### "¿Esto se paga solo?"

La respuesta honesta, que ya calcula el sistema:

> Con el ahorro de energía de bombeo en un predio de una hectárea con luz barata, el
> equipo tarda unos 13 años en pagarse. Donde sí se paga rápido es en bombeo diésel
> (2.6 años), en predios que compran agua a un acueducto (4 años), o con mayor altura de
> bombeo y más área.

Y el complemento:

> El resto del valor no está en la factura: está en no perder producción por estrés
> hídrico, en poder demostrar el uso del agua ante el PUEAA municipal, y en que el costo
> por predio baja de $1.7 a unos $700.000 al replicar en 50 predios.

**Tener este número listo es la diferencia entre verse riguroso y verse improvisado.**
Alguien lo va a preguntar.

### "¿Esto se puede replicar?"

Costo por predio, repositorio abierto con licencia, sistema de perfiles que soporta
cultivo y pastoreo sin recodificar, y el plan de escalamiento con sus tres fases.

Nombra también el bloqueo real: del cuarto predio en adelante hace falta autenticación,
porque sin ella cualquiera con la URL vería los datos de todos los productores, y eso
rompe el consentimiento informado firmado.

### "¿Y si el sensor se equivoca?"

> El productor puede decírmelo. Si él ve la tierra seca y el sensor dice lo contrario, el
> sistema registra la discrepancia y alerta al técnico, porque casi siempre significa que
> el sensor está mal instalado o descalibrado. Su criterio es un dato de diagnóstico, no
> un ruido que haya que descartar.

Esa respuesta suele sorprender bien.

### "¿Por qué no una app nativa?"

> Una app nativa son 4 a 8 semanas de desarrollo, US$25 de Play Store, US$99 al año de
> App Store, y dos códigos distintos. Una PWA se instala igual en el celular, funciona sin
> señal, y se actualiza subiendo un archivo. Elegí la tecnología proporcional al problema.

---

## 3. Estructura sugerida para la presentación final (mes 4)

La de la propuesta tenía 8 diapositivas para prometer. La final necesita otra proporción:
**menos promesa, más evidencia**.

| # | Diapositiva | Cambio respecto a la propuesta |
|---|---|---|
| 1 | Portada | Igual |
| 2 | El problema | Igual, pero con una foto del predio piloto real |
| 3 | Qué se construyó | Reemplaza "la solución": fotos del nodo instalado |
| 4 | Arquitectura | Actualizada: LoRa + caudalímetro + gateway |
| 5 | **Los datos** | **Nueva y la más importante.** Gráfica de humedad por profundidad, 4 semanas, con riegos y lluvias marcados |
| 6 | **El ahorro** | **Nueva.** Línea base vs. con sistema, en m³ y en pesos |
| 7 | El modelo | Predicho vs. real + comparación con la línea base |
| 8 | Lo que no funcionó | **Nueva.** Limitaciones honestas: cobertura de datos, fallas, ajustes |
| 9 | Impacto y réplica | Costo por predio, articulación con Emsersopó, plan de escalamiento |
| 10 | Cierre | Igual |

La número 8 es la que más te va a servir. Todas las presentaciones tienen conclusiones
triunfales; la que reconoce sus límites se ve más seria, no menos.

---

## 4. Lo que todavía falta, y no es código

El paquete técnico está completo. Estas cinco cosas no se pueden programar:

1. **El predio piloto confirmado.** Sin esto no arranca nada. Ten un segundo candidato
   identificado desde la semana 1, por si el primero se retira.
2. **El consentimiento informado firmado.** Está listo en
   `05_institucional/01_consentimiento_informado.md`, pero necesita la firma antes de
   instalar cualquier equipo.
3. **La compra del hardware.** Si vas a importar sensores, esa orden va esta semana:
   3 a 5 semanas de tránsito.
4. **La cita con Emsersopó agendada.** Pídela en la semana 8 para reunirte en la 11. Los
   tiempos institucionales se miden en semanas.
5. **La bitácora empezada.** Desde el día uno. En el mes 4, cuando toque escribir el
   informe, esa bitácora es la diferencia entre reconstruir de memoria y tener el trabajo
   hecho.

Y la que ya sabes: **el caudalímetro en la semana 5, no en la 10.** Todo el argumento de
ahorro se sostiene en medir cómo regaba antes.
