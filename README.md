# HidroSopó

**Sistema Inteligente de Monitoreo Ambiental y Optimización del Uso del Agua mediante IoT e Inteligencia Artificial — Municipio de Sopó, Cundinamarca**

Proyecto de Ciencia, Tecnología e Innovación — Fondo Especial para el Fomento de la Educación Superior (FOES), Municipio de Sopó.

---

## Empieza aquí

1. 👉 **[`00_PLAN_MAESTRO_EJECUCION.md`](00_PLAN_MAESTRO_EJECUCION.md)** — el plan completo:
   cronograma, presupuesto, riesgos y dos advertencias que cambian el diseño del proyecto.
   Léelo antes de comprar nada.
2. 🔧 **[`07_GUIA_PUESTA_EN_MARCHA.md`](07_GUIA_PUESTA_EN_MARCHA.md)** — el paso a paso:
   instalar el módulo de IA, publicar el backend, y poner la app en el celular del productor.

## Contenido

| Carpeta | Qué hay |
|---|---|
| `00_PLAN_MAESTRO_EJECUCION.md` | Plan de ejecución completo, 16 semanas |
| `07_GUIA_PUESTA_EN_MARCHA.md` | Instalación paso a paso, de cero a la app en el celular |
| `08_PLAN_ESCALAMIENTO.md` | Cómo pasar de 1 predio a N, y quién lo mantiene después |
| `09_entregables/` | Guion del póster, manual del productor, y ajustes a la presentación |
| `01_hardware/` | BOM con precios CO, conexiones, calibración, energía, y CAD en **STEP / STL / DXF** |
| `02_firmware/` | Código ESP32: nodo de suelo, nodo de caudal, gateway |
| `03_backend/` | API FastAPI, motor FAO-56, modelo ML, **agente conversacional**, sectores de riego, costo en pesos, 83 pruebas |
| `04_dashboard/` | App del productor: PWA instalable, corte de suelo interactivo y chat con el agente |
| `05_institucional/` | Consentimiento informado, cartas, protocolo PUEAA, bitácora |
| `06_datos/` | Generador de datos sintéticos para probar sin hardware |

## Arranque rápido sin hardware (10 minutos)

### Con Docker (un comando)

```bash
docker compose up
# Backend: http://localhost:8000 · App: http://localhost:5500
```

### Sin Docker

```bash
# 1. Backend
cd 03_backend
pip install -r requirements.txt
uvicorn main:app --reload

# 2. Datos y modelo (en otra terminal)
cd 06_datos && python generar_datos_prueba.py --dias 90
cd ../03_backend && python -m ia.modelo_ml --csv ../06_datos/datos_sinteticos.csv

# 3. Dashboard (en otra terminal)
cd 04_dashboard && python -m http.server 5500
```

El dashboard funciona en modo demostración aunque el backend no esté corriendo.

```bash
# Verificar que todo esté sano
cd 03_backend && pytest        # 83 pruebas
```

## Las tres cosas que no debes olvidar

1. **Instala el caudalímetro en la semana 5, no en la 10.** Sin línea base de consumo no
   puedes demostrar ahorro, y sin ahorro demostrado el proyecto no cumple su objetivo.

2. **No prometas integraciones automáticas con entidades.** Lo que el sistema hace —generar
   automáticamente los indicadores de uso eficiente, medidos y trazables, como insumo para el
   PUEAA municipal— es igual de sólido y sí es demostrable.
   Ver `05_institucional/04_protocolo_pueaa_municipal.md`.

3. **Calibra los sensores por gravimetría.** Sin eso reportas valores ADC sin significado
   físico. Ver `01_hardware/CALIBRACION.md`.

## Stack

- **Hardware:** ESP32-S3 (Heltec WiFi LoRa 32 V3), LoRa 915 MHz, sensores capacitivos, DS18B20, SHT31, caudalímetro de pulsos
- **Firmware:** C++ / Arduino / PlatformIO
- **Backend:** Python, FastAPI, SQLAlchemy, scikit-learn
- **Modelo agronómico:** FAO-56 (Allen et al., 1998)
- **Clima:** Open-Meteo (gratis, sin API key)
- **App móvil:** PWA (HTML + Chart.js), instalable en Android e iOS, funciona sin señal
- **CAD:** CadQuery → STEP (Inventor, AutoCAD, SolidWorks) + STL + DXF; OpenSCAD para vista rápida

**Costo de software y servicios: $0.**

## Licencia

Código: MIT. Documentación y diseños CAD: CC BY 4.0.

Reconocimiento a las librerías de código abierto utilizadas: RadioLib, ArduinoJson,
OneWire, DallasTemperature, Adafruit SHT31, FastAPI, SQLAlchemy, scikit-learn,
pandas, Chart.js y OpenSCAD.

## Autor

Jose Alejandro Pulido Gómez — Ingeniería Mecatrónica, Universitaria Agustiniana
Beneficiario FOES, Municipio de Sopó — 2026
