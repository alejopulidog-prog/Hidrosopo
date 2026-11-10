# Paso a paso de las entregas FOES 2026-II — HidroSopó

Correo: **proyectosctei@sopo-cundinamarca.gov.co** con copia a **ctei@sopo-cundinamarca.gov.co**.
Asunto sugerido: `FOES 2026-II · [Entrega] · José Alejandro Pulido Gómez · HidroSopó`.

| Fecha | Entrega | Qué adjuntar |
|---|---|---|
| **26 oct** | Plan de trabajo **y bitácora de avances** (10 ago – 25 oct) | `Formato_Seguimiento_FOES_HidroSopo_JAPulido.docx` + `Bitacora_de_avances_HidroSopo.docx` completada + `HidroSopo_Documento_del_Proyecto_ampliado.docx` (celdas amarillas completadas) + `HidroSopo_Presentacion_Avances_26oct.pptx` si hay exposición, con las evidencias de lo ya avanzado (diagnóstico, diseño, BOM, CAD, código) |
| **5 nov** | Avance 1: sensores y plataforma en la nube (act. 5 y 6) | Informe de avance 1 + curvas de calibración (R²), registro de línea base del caudalímetro, URL de la plataforma, fotos |
| **19 nov** | Avance 2: módulo de IA e instalación piloto (act. 7 y 8) | Informe de avance 2 + métricas del modelo, pantallazo de `pytest` (102/102), recomendaciones generadas, acta y fotos de instalación |
| **26 nov** | Producto final: pruebas, análisis y póster (act. 9 y 10) | Póster impreso 90 × 120 cm + PDF + informe técnico + enlace al repositorio |

## Estructura de cada informe de avance (máx. 3 páginas)
1. Actividades del plan ejecutadas en el periodo (con el N.º del plan de trabajo).
2. Evidencias (fotos, archivos, enlaces) — una por actividad.
3. Resultados preliminares — **diferenciando lo medido de lo simulado**.
4. Dificultades y cómo se resolvieron (cruza con la matriz de riesgos).
5. Actividades del siguiente periodo.

## Cronograma (alineado al plan de trabajo)
| Periodo | Actividad del plan |
|---|---|
| 10 ago – 28 ago | 2. Revisión técnica y requerimientos |
| 24 ago – 18 sep | 3. Diagnóstico del predio piloto |
| 7 sep – 9 oct | 4. Diseño electrónico y mecánico |
| 28 sep – 30 oct | 5. Sensores: nodo, calibración, caudalímetro (línea base) |
| 5 oct – 3 nov | 6. Plataforma en la nube y app |
| 12 oct – 12 nov | 7. Módulo de IA |
| 2 nov – 13 nov | 8. Instalación piloto |
| 9 nov – 24 nov | 9. Pruebas y análisis (`09_entregables/PROTOCOLO_PRUEBAS.md`) |
| 16 nov – 26 nov | 10. Póster e informe final |

**Antes del 26 oct:** completar la bitácora con lo realmente hecho (cada semana, una evidencia), revisar el formato y enviar ambos a proyectosctei@ con copia a ctei@. La bitácora se escribe con fechas y hechos reales; si una semana tuvo poco avance, se deja así.

## Cómo gastar lo mínimo
| Decisión | Efecto aprox. |
|---|---|
| WiFi directo, sin LoRa ni pasarela (configuración del piloto) | hardware de ≈ $1,7 M a ≈ $1,1 M (−36 %), según `01_hardware/BOM.md` |
| ESP32 DevKit (≈ $28.000) en lugar de Heltec V3 ($175.000) | ya incluido en la cifra anterior; hay que ajustar los pines en `config.h` |
| DHT22 en lugar de SHT31 | ~$24.000 |
| Pluviómetro impreso en 3D | ~$85.000 |
| Reutilizar celdas 18650 | ~$36.000 |
| Póster en papel bond plano en vez de lona | ~$25.000 |
| Render + Supabase + Netlify + Open-Meteo + scikit-learn | $0 |

**Lo que nunca se recorta:** el caudalímetro. **Condición del WiFi:** el nodo debe quedar a ≲ 50 m del router o con repetidor; si no, se activa LoRa.

## Imprimir el póster
- Archivo: `09_entregables/poster/HidroSopo_Poster_90x120.pdf` (vectorial, 1 página, 90 × 120 cm).
- Pide "impresión gran formato a tamaño real, sin escalar". Bond plano: ~$25–35 mil; propalcote: ~$50–70 mil.
- Antes: imprime en hoja carta un pedazo al 100 % (texto del cuerpo legible a 1 m).
- QR: comparte la página de resultados, crea el QR en un generador gratuito, guárdalo como `poster/logos/qr.png` y regenera. **Prueba el QR con el celular.**
