# Protocolo de articulación con el PUEAA municipal

Ruta institucional del proyecto. **Toda la articulación es con el municipio de Sopó:
Emsersopó E.S.P., la Alcaldía y sus secretarías.** No se contempla gestión directa
ante autoridades ambientales regionales.

---

## 1. Por qué esta decisión de alcance

El PUEAA es el programa que Emsersopó E.S.P. lidera en Sopó junto con la Alcaldía y la
Secretaría de Ambiente. Es un instrumento **local, con dolientes locales**, y ahí es donde
este proyecto puede aportar de verdad en cuatro meses.

Ir directamente a la corporación regional agregaría tiempos administrativos que no caben
en el cronograma, y no aportaría nada que el municipio no pueda aprovechar primero. Si en
el futuro Emsersopó decide usar estos datos en su propia gestión ante la autoridad
ambiental, esa decisión es de ellos, no una carga de este proyecto.

**Traducción para la sustentación:** el proyecto se articula con el programa municipal de
uso eficiente del agua. No pretende ser un trámite ambiental ni sustituirlo.

Un dato de contexto que conviene manejar: el PUEAA de Emsersopó tiene un horizonte de cinco
años que ya venció, y el Plan de Acción 2024–2027 de la entidad contempla actualizarlo,
implementarlo y hacerle seguimiento. Ese pendiente es tu mejor puerta de entrada.

---

## 2. Lo que el sistema aporta al PUEAA

El PUEAA necesita saber **cuánta agua se usa y con qué eficiencia**. Hoy ese dato, en el
sector rural, se estima con módulos de consumo teóricos. Este proyecto lo mide.

| Indicador | Unidad | Para qué le sirve al programa |
|---|---|---|
| Volumen captado | m³ | Demanda real medida, no estimada |
| Caudal medio y máximo | l/s | Caracterización del patrón de uso |
| Módulo de consumo | l/s/ha | El indicador central del sector agrícola |
| Lámina aplicada | mm | Comparable con el requerimiento del cultivo |
| Eficiencia de aplicación | % | Cuantifica el desperdicio |
| Percolación bajo raíz | mm | Agua que se pierde por debajo de la raíz |
| Precipitación efectiva | mm | Aporte natural que reduce la necesidad de riego |
| **Ahorro vs. línea base** | **m³ y %** | **El número que justifica el proyecto** |
| Cobertura de datos | % | Honestidad metodológica |

Todos calculados con datos medidos cada 15 minutos y trazables hasta el registro individual.

---

## 3. Lo que este sistema NO es

Sé explícito en esto. Prometer de más es la forma más rápida de perder credibilidad.

| ❌ No es | ✅ Sí es |
|---|---|
| Un trámite ambiental | Una herramienta de medición |
| Un reporte oficial | Un anexo técnico con datos verificables |
| Un sistema de fiscalización | Un apoyo a la decisión del productor |
| Un sustituto del PUEAA | Un insumo para el PUEAA |
| Un riego automático | Un sistema de recomendación; la decisión es del productor |

Esto último está también en el consentimiento informado, y hay que respetarlo: el sistema
no acciona válvulas ni bombas.

---

## 4. Orden de las conversaciones

```
  1. Secretaría de Ciencia, Tecnología e Innovación de Sopó
     └─ Es tu contraparte del estímulo FOES. Empieza SIEMPRE aquí.
        Ellos te abren las demás puertas.
                    │
                    ▼
  2. Emsersopó E.S.P. — área de gestión ambiental
     └─ El argumento: su PUEAA está en ciclo de actualización
        y tú traes el dato que más les cuesta conseguir.
                    │
                    ▼
  3. Secretaría de Ambiente y Desarrollo Agropecuario
     └─ Replicabilidad, articulación con asistencia técnica rural.
```

**Cuándo tocar cada puerta:**

| Semana | Acción |
|---|---|
| 1–2 | Reunión inicial con la Secretaría de CTeI (presentación del plan) |
| 8 | **Solicitar cita** con Emsersopó. Los tiempos institucionales son de semanas |
| 11 | Reunión con Emsersopó, ya con 5–6 semanas de datos reales |
| 13 | Reunión con Secretaría de Ambiente |
| 15 | Entrega del informe con las manifestaciones de interés obtenidas |

**Regla de oro:** no vayas a Emsersopó sin datos. Una reunión con evidencia es una
conversación técnica; sin evidencia es una molestia, y solo tienes una primera impresión.

---

## 5. Qué llevar a la reunión con Emsersopó

Máximo 40 minutos. Prepara esto:

**Impreso (2 páginas, no diez):**
- Resumen del proyecto en una página
- Tabla de indicadores del período medido

**En el celular, funcionando:**
- La app abierta mostrando datos reales del predio
- Que vean el mensaje que le llega al productor

**Digital, para dejarles:**
- El reporte generado por el sistema (`/api/v1/predios/1/reporte-pueaa`)
- El CSV de indicadores
- Enlace al panel institucional de solo lectura (`/api/v1/institucional/resumen`)

**Lo que pides:**
1. Retroalimentación sobre qué indicadores y en qué formato les sirven
2. Una manifestación de interés o carta de utilidad para tu informe FOES
3. Nada más. No pidas dinero ni compromisos en la primera reunión.

---

## 6. El panel institucional

El sistema expone una vista agregada y anonimizada pensada para la entidad:

```
GET /api/v1/institucional/resumen
```

Devuelve: número de predios monitoreados, área total bajo riego, volumen acumulado,
y detalle por vereda **sin nombres de productores ni de predios**.

Esto es deliberado. Si Emsersopó recibe datos identificables, el productor pierde la
confianza y se acaba el piloto. Ver sección 7.

---

## 7. Cuidado con el productor

Punto ético, no burocrático.

El consentimiento informado que firma el productor establece que sus datos **no se usarán
para fiscalizar**. Cúmplelo:

- En los reportes institucionales, **anonimiza**: "predio de la vereda X", no el nombre.
- Si descubres que el predio capta agua sin permiso, **eso no se reporta a ninguna entidad**.
  Tú no eres autoridad de control. Puedes comentárselo al productor y ofrecerle información
  sobre cómo formalizarse, si él lo pide.
- Antes de mostrar cualquier dato en una reunión, pregúntate: ¿el productor estaría cómodo
  viendo esta diapositiva?

Si esto se maneja mal, pierdes el predio piloto en el mes 3 y el proyecto se cae. Y con
razón.

---

## 8. Cómo generar el reporte

```bash
# Reporte en Markdown
curl "http://localhost:8000/api/v1/predios/1/reporte-pueaa?desde=2026-09-01&hasta=2026-11-30&linea_base_m3=420" \
  -o reporte_pueaa.md

# Convertir a PDF
pandoc reporte_pueaa.md -o reporte_pueaa.pdf --pdf-engine=xelatex -V geometry:margin=2.5cm

# CSV de indicadores para la entidad
curl "http://localhost:8000/api/v1/predios/1/reporte-pueaa?desde=2026-09-01&hasta=2026-11-30&formato=csv" \
  -o indicadores_pueaa.csv
```

---

## 9. Los cinco errores que hunden esta parte

1. **No medir la línea base.** Sin las semanas previas de "cómo regaba antes", no hay contra
   qué comparar y todo el módulo queda sin conclusión. Instala el caudalímetro en la semana 5.
2. **No calibrar el caudalímetro.** Todo el reporte se sostiene en ese número. El error de
   fábrica llega al 10%. Calíbralo con probeta y documéntalo con fotos.
3. **Dejar las reuniones para el mes 4.** Agenda en el mes 2. Los tiempos institucionales
   se miden en semanas.
4. **Prometer de más.** Revisa la tabla de la sección 3 antes de cada reunión.
5. **Exponer al productor.** Ver sección 7.

---

## 10. Contactos

- Emsersopó E.S.P.: `emsersopoesp.gov.co`
- Alcaldía de Sopó: `sopo-cundinamarca.gov.co`
- Secretaría de CTeI de Sopó: tu contraparte del estímulo FOES
