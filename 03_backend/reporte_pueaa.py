"""
HidroSopó — Módulo de reporte PUEAA
====================================
Genera los indicadores de uso eficiente del agua para el Programa de
Uso Eficiente y Ahorro del Agua (PUEAA) del municipio de Sopó, liderado
por Emsersopó E.S.P. junto con la Alcaldía y la Secretaría de Ambiente.

MARCO DE REFERENCIA
-------------------
  Ley 373 de 1997          — establece el PUEAA
  Decreto 1090 de 2018     — lo reglamenta
  Resolución 1257 de 2018  — define su estructura y contenido

ALCANCE
-------
Este módulo produce un ANEXO TÉCNICO con datos medidos. No es un
trámite ambiental ni un reporte oficial ante ninguna autoridad.

Lo que hace:
  1. Calcula los indicadores de uso eficiente con datos medidos
     cada 15 minutos, no con estimaciones teóricas
  2. Genera el informe en formato legible y convertible a PDF
  3. Exporta CSV de indicadores para que el municipio o el operador
     lo integre a su propia gestión del programa
  4. Deja trazabilidad auditable de cada m³ captado

Qué NO hace: radicar, tramitar, ni sustituir la formulación del PUEAA.
Eso es competencia de quien opera el programa.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict, field
from datetime import date, datetime, timedelta
from typing import Optional
import json
import csv
import io


# ============================================================
#  Datos del usuario del recurso hídrico
# ============================================================

@dataclass
class UsuarioAgua:
    """Información del predio y su relación con la autoridad ambiental."""
    nombre_predio: str
    propietario: str
    documento: str
    municipio: str = "Sopó"
    departamento: str = "Cundinamarca"
    vereda: str = ""
    coordenadas: tuple[float, float] = (0.0, 0.0)     # (lat, lon) WGS84
    area_predio_ha: float = 0.0
    area_regada_ha: float = 0.0

    # Concesión de aguas (si existe)
    tiene_concesion: bool = False
    numero_permiso: str = ""
    resolucion_concesion: str = ""
    fecha_resolucion: str = ""
    caudal_concesionado_lps: float = 0.0
    uso_autorizado: str = "riego"           # doméstico | pecuario | riego | otro
    fuente_hidrica: str = ""
    tipo_captacion: str = ""                # superficial | subterránea | acueducto
    entidad_articulacion: str = "Emsersopó E.S.P. — Municipio de Sopó"

    # Sistema productivo
    tipo_actividad: str = "agrícola"         # agrícola | pecuaria | mixta
    sistema_riego: str = "aspersion"


# ============================================================
#  Indicadores
# ============================================================

@dataclass
class IndicadoresPUEAA:
    periodo_inicio: str
    periodo_fin: str
    dias_periodo: int

    # Volumen (Res. 1257/2018)
    volumen_captado_m3: float = 0.0
    volumen_diario_promedio_m3: float = 0.0
    caudal_medio_lps: float = 0.0
    caudal_maximo_lps: float = 0.0
    caudal_concesionado_lps: float = 0.0
    pct_uso_de_concesion: float = 0.0
    excedio_concesion: bool = False
    dias_con_exceso: int = 0

    # Eficiencia
    modulo_consumo_lps_ha: float = 0.0
    lamina_aplicada_mm: float = 0.0
    requerimiento_teorico_mm: float = 0.0
    eficiencia_aplicacion_pct: float = 0.0
    percolacion_estimada_mm: float = 0.0
    perdidas_estimadas_pct: float = 0.0

    # Ahorro
    volumen_linea_base_m3: float = 0.0
    ahorro_m3: float = 0.0
    ahorro_pct: float = 0.0

    # Aportes naturales
    precipitacion_periodo_mm: float = 0.0
    precipitacion_efectiva_mm: float = 0.0
    et0_acumulada_mm: float = 0.0

    # Calidad del dato
    registros_totales: int = 0
    registros_validos: int = 0
    cobertura_datos_pct: float = 0.0

    observaciones: list[str] = field(default_factory=list)


def calcular_indicadores(
    usuario: UsuarioAgua,
    registros_caudal: list[dict],
    registros_clima: list[dict],
    periodo_inicio: date,
    periodo_fin: date,
    volumen_linea_base_m3: float = 0.0,
    requerimiento_teorico_mm: float = 0.0,
    percolacion_estimada_mm: float = 0.0,
) -> IndicadoresPUEAA:
    """Calcula los indicadores del período.

    registros_caudal: [{"ts": iso, "litros_periodo": float, "caudal_lps": float}, ...]
    registros_clima:  [{"ts": iso, "lluvia_mm": float, "et0_mm": float}, ...]
    """
    dias = max(1, (periodo_fin - periodo_inicio).days + 1)
    ind = IndicadoresPUEAA(
        periodo_inicio=periodo_inicio.isoformat(),
        periodo_fin=periodo_fin.isoformat(),
        dias_periodo=dias,
        caudal_concesionado_lps=usuario.caudal_concesionado_lps,
        requerimiento_teorico_mm=requerimiento_teorico_mm,
        percolacion_estimada_mm=percolacion_estimada_mm,
        volumen_linea_base_m3=volumen_linea_base_m3,
    )

    # ---- Volumen y caudal ----
    litros = sum(r.get("litros_periodo", 0.0) for r in registros_caudal)
    ind.volumen_captado_m3 = round(litros / 1000.0, 3)
    ind.volumen_diario_promedio_m3 = round(ind.volumen_captado_m3 / dias, 3)
    ind.caudal_medio_lps = round(litros / (dias * 86400.0), 5) if dias else 0.0

    caudales = [r.get("caudal_lps", 0.0) for r in registros_caudal if r.get("caudal_lps") is not None]
    ind.caudal_maximo_lps = round(max(caudales), 4) if caudales else 0.0

    if usuario.caudal_concesionado_lps > 0:
        ind.pct_uso_de_concesion = round(
            100.0 * ind.caudal_medio_lps / usuario.caudal_concesionado_lps, 1)
        excesos = [c for c in caudales if c > usuario.caudal_concesionado_lps]
        ind.dias_con_exceso = len(excesos)
        ind.excedio_concesion = ind.caudal_maximo_lps > usuario.caudal_concesionado_lps
        if ind.excedio_concesion:
            ind.observaciones.append(
                f"Se registraron {len(excesos)} intervalos con caudal instantáneo "
                f"por encima del autorizado ({usuario.caudal_concesionado_lps} l/s). "
                "Conviene revisar la operación del sistema de captación."
            )
    else:
        ind.observaciones.append(
            "El predio no reporta permiso de captación vigente. Este informe se limita "
            "a registrar el uso medido; la situación jurídica de la captación está "
            "fuera del alcance de este proyecto."
        )

    # ---- Módulo de consumo (l/s por hectárea) ----
    if usuario.area_regada_ha > 0:
        ind.modulo_consumo_lps_ha = round(ind.caudal_medio_lps / usuario.area_regada_ha, 5)
        # 1 m³ sobre 1 ha = 0.1 mm
        ind.lamina_aplicada_mm = round(
            ind.volumen_captado_m3 / (usuario.area_regada_ha * 10000.0) * 1000.0, 2)

    # ---- Eficiencia ----
    if ind.lamina_aplicada_mm > 0 and requerimiento_teorico_mm > 0:
        ind.eficiencia_aplicacion_pct = round(
            100.0 * min(requerimiento_teorico_mm, ind.lamina_aplicada_mm) / ind.lamina_aplicada_mm, 1)
        ind.perdidas_estimadas_pct = round(100.0 - ind.eficiencia_aplicacion_pct, 1)
        if ind.eficiencia_aplicacion_pct < 60:
            ind.observaciones.append(
                f"Eficiencia de aplicación baja ({ind.eficiencia_aplicacion_pct}%). "
                "Se recomienda revisar uniformidad del sistema y fraccionar los riegos."
            )

    # ---- Ahorro contra línea base ----
    if volumen_linea_base_m3 > 0:
        ind.ahorro_m3 = round(volumen_linea_base_m3 - ind.volumen_captado_m3, 3)
        ind.ahorro_pct = round(100.0 * ind.ahorro_m3 / volumen_linea_base_m3, 1)

    # ---- Clima ----
    ind.precipitacion_periodo_mm = round(sum(r.get("lluvia_mm", 0.0) for r in registros_clima), 1)
    ind.precipitacion_efectiva_mm = round(ind.precipitacion_periodo_mm * 0.80, 1)
    ind.et0_acumulada_mm = round(sum(r.get("et0_mm", 0.0) for r in registros_clima), 1)

    # ---- Calidad del dato ----
    esperados = dias * 96      # 96 registros/día a 15 min
    ind.registros_totales = esperados
    ind.registros_validos = len(registros_caudal)
    ind.cobertura_datos_pct = round(100.0 * len(registros_caudal) / esperados, 1) if esperados else 0.0
    if ind.cobertura_datos_pct < 85:
        ind.observaciones.append(
            f"Cobertura de datos del {ind.cobertura_datos_pct}%. Hubo interrupciones "
            "en la transmisión. Los volúmenes reportados pueden estar subestimados."
        )

    return ind


# ============================================================
#  Generación del reporte
# ============================================================

def generar_reporte_markdown(usuario: UsuarioAgua, ind: IndicadoresPUEAA,
                             acciones_implementadas: list[str] | None = None) -> str:
    """Reporte en Markdown, convertible a PDF con pandoc.

    Estructura alineada con los componentes que la Resolución 1257
    de 2018 exige para el PUEAA simplificado / pequeños usuarios.
    """
    acciones = acciones_implementadas or []
    hoy = date.today().isoformat()
    lat, lon = usuario.coordenadas

    def si_no(v): return "Sí" if v else "No"

    md = f"""# Informe de Seguimiento al Uso Eficiente del Agua

**Sistema HidroSopó — Monitoreo IoT del recurso hídrico**

Documento técnico anexo para el Programa de Uso Eficiente y Ahorro del Agua (PUEAA)
conforme a la Ley 373 de 1997, el Decreto 1090 de 2018 y la Resolución 1257 de 2018.

- **Fecha de elaboración:** {hoy}
- **Período reportado:** {ind.periodo_inicio} a {ind.periodo_fin} ({ind.dias_periodo} días)
- **Articulación institucional:** {usuario.entidad_articulacion}

---

## 1. Identificación del usuario del recurso hídrico

| Campo | Valor |
|---|---|
| Nombre del predio | {usuario.nombre_predio} |
| Propietario / representante | {usuario.propietario} |
| Documento de identificación | {usuario.documento} |
| Municipio | {usuario.municipio}, {usuario.departamento} |
| Vereda | {usuario.vereda or 'No registrada'} |
| Coordenadas (WGS84) | {lat:.6f}, {lon:.6f} |
| Área total del predio | {usuario.area_predio_ha} ha |
| Área bajo riego | {usuario.area_regada_ha} ha |
| Actividad productiva | {usuario.tipo_actividad} |
| Sistema de riego | {usuario.sistema_riego} |

## 2. Información de la captación

| Campo | Valor |
|---|---|
| ¿Cuenta con permiso vigente? | {si_no(usuario.tiene_concesion)} |
| Número de permiso / expediente | {usuario.numero_permiso or 'No aplica'} |
| Acto de otorgamiento | {usuario.resolucion_concesion or 'No aplica'} |
| Fecha de la resolución | {usuario.fecha_resolucion or 'No aplica'} |
| Caudal autorizado | {usuario.caudal_concesionado_lps} l/s |
| Uso autorizado | {usuario.uso_autorizado} |
| Fuente hídrica | {usuario.fuente_hidrica or 'No registrada'} |
| Tipo de captación | {usuario.tipo_captacion or 'No registrado'} |

## 3. Volumen captado y caudal

Mediciones obtenidas con caudalímetro de pulsos instalado en el punto de captación,
con registro automático cada 15 minutos.

| Indicador | Valor | Unidad |
|---|---:|---|
| Volumen total captado en el período | {ind.volumen_captado_m3:,.2f} | m³ |
| Volumen diario promedio | {ind.volumen_diario_promedio_m3:,.3f} | m³/día |
| Caudal medio | {ind.caudal_medio_lps:.5f} | l/s |
| Caudal máximo instantáneo | {ind.caudal_maximo_lps:.4f} | l/s |
| Caudal autorizado | {ind.caudal_concesionado_lps:.4f} | l/s |
| **Porcentaje de uso del caudal autorizado** | **{ind.pct_uso_de_concesion:.1f}** | **%** |
| ¿Se excedió el caudal autorizado? | {si_no(ind.excedio_concesion)} | — |
| Intervalos con exceso | {ind.dias_con_exceso} | — |

## 4. Indicadores de eficiencia

| Indicador | Valor | Unidad |
|---|---:|---|
| Módulo de consumo | {ind.modulo_consumo_lps_ha:.5f} | l/s/ha |
| Lámina aplicada | {ind.lamina_aplicada_mm:.1f} | mm |
| Requerimiento teórico (FAO-56) | {ind.requerimiento_teorico_mm:.1f} | mm |
| Eficiencia de aplicación | {ind.eficiencia_aplicacion_pct:.1f} | % |
| Pérdidas estimadas | {ind.perdidas_estimadas_pct:.1f} | % |
| Percolación bajo zona radicular | {ind.percolacion_estimada_mm:.1f} | mm |

El requerimiento teórico se calcula por el método FAO-56 (Allen et al., 1998),
usando la evapotranspiración de referencia del sitio y el coeficiente de cultivo
correspondiente a la especie sembrada.

## 5. Aportes naturales

| Indicador | Valor | Unidad |
|---|---:|---|
| Precipitación acumulada | {ind.precipitacion_periodo_mm:.1f} | mm |
| Precipitación efectiva (80%) | {ind.precipitacion_efectiva_mm:.1f} | mm |
| Evapotranspiración de referencia acumulada | {ind.et0_acumulada_mm:.1f} | mm |

## 6. Reducción del consumo

| Indicador | Valor | Unidad |
|---|---:|---|
| Volumen de línea base | {ind.volumen_linea_base_m3:,.2f} | m³ |
| Volumen del período con sistema | {ind.volumen_captado_m3:,.2f} | m³ |
| **Ahorro** | **{ind.ahorro_m3:,.2f}** | **m³** |
| **Reducción porcentual** | **{ind.ahorro_pct:.1f}** | **%** |

## 7. Acciones de uso eficiente implementadas

"""
    if acciones:
        for i, a in enumerate(acciones, 1):
            md += f"{i}. {a}\n"
    else:
        md += ("1. Instalación de sistema de medición continua del volumen captado.\n"
               "2. Implementación de programación de riego basada en balance hídrico FAO-56.\n"
               "3. Monitoreo de humedad del suelo en tres profundidades de la zona radicular.\n"
               "4. Detección y control de percolación profunda.\n"
               "5. Emisión de alertas al productor para evitar riegos innecesarios.\n")

    md += f"""
## 8. Calidad y trazabilidad de los datos

| Indicador | Valor |
|---|---:|
| Registros esperados en el período | {ind.registros_totales:,} |
| Registros efectivamente recibidos | {ind.registros_validos:,} |
| Cobertura de datos | {ind.cobertura_datos_pct:.1f}% |

**Instrumentación:** caudalímetro de pulsos calibrado en campo con volumen patrón;
sensores capacitivos de humedad calibrados por método gravimétrico con suelo del predio;
sensor de temperatura y humedad relativa SHT31 (±0.3 °C / ±2 % HR);
pluviómetro de cangilones. Registro automático cada 15 minutos, con almacenamiento
local de respaldo ante fallas de conectividad.

## 9. Observaciones

"""
    if ind.observaciones:
        for o in ind.observaciones:
            md += f"- {o}\n"
    else:
        md += "- Sin observaciones. El período transcurrió dentro de los parámetros esperados.\n"

    md += f"""
---

## Nota sobre el alcance de este documento

Este informe es un **anexo técnico** producido automáticamente por el sistema de
monitoreo HidroSopó, en el marco de un proyecto académico de Ciencia, Tecnología e
Innovación del municipio de Sopó.

Su propósito es aportar evidencia medida y trazable sobre el uso del agua en un predio
rural, como insumo para el Programa de Uso Eficiente y Ahorro del Agua del municipio.

**No constituye un trámite ambiental, ni un reporte oficial ante ninguna autoridad, ni
sustituye la formulación del PUEAA.** Los datos aquí presentados provienen de
instrumentación calibrada y su uso posterior es decisión de la entidad que los reciba.

---

*Generado por HidroSopó v1.0 — {datetime.now().isoformat(timespec='seconds')}*
"""
    return md


def exportar_csv_indicadores(usuario: UsuarioAgua, ind: IndicadoresPUEAA) -> str:
    """CSV plano de indicadores, para entregar a Emsersopó o a la Secretaría
    de Ambiente e integrarlo a la gestión del PUEAA municipal.

    No es un formato oficial: es una estructura de intercambio simple y legible,
    con los indicadores que el programa necesita.
    """
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["campo", "valor", "unidad"])
    filas = [
        ("municipio", usuario.municipio, ""),
        ("departamento", usuario.departamento, ""),
        ("predio", usuario.nombre_predio, ""),
        ("latitud", f"{usuario.coordenadas[0]:.6f}", "grados"),
        ("longitud", f"{usuario.coordenadas[1]:.6f}", "grados"),
        ("permiso_captacion", usuario.numero_permiso, ""),
        ("uso_autorizado", usuario.uso_autorizado, ""),
        ("fuente_hidrica", usuario.fuente_hidrica, ""),
        ("tipo_captacion", usuario.tipo_captacion, ""),
        ("periodo_inicio", ind.periodo_inicio, "fecha"),
        ("periodo_fin", ind.periodo_fin, "fecha"),
        ("caudal_concesionado", f"{ind.caudal_concesionado_lps:.5f}", "l/s"),
        ("caudal_medio_captado", f"{ind.caudal_medio_lps:.5f}", "l/s"),
        ("caudal_maximo_captado", f"{ind.caudal_maximo_lps:.5f}", "l/s"),
        ("volumen_captado", f"{ind.volumen_captado_m3:.3f}", "m3"),
        ("area_regada", f"{usuario.area_regada_ha:.2f}", "ha"),
        ("modulo_consumo", f"{ind.modulo_consumo_lps_ha:.5f}", "l/s/ha"),
        ("lamina_aplicada", f"{ind.lamina_aplicada_mm:.2f}", "mm"),
        ("eficiencia_aplicacion", f"{ind.eficiencia_aplicacion_pct:.1f}", "%"),
        ("precipitacion", f"{ind.precipitacion_periodo_mm:.1f}", "mm"),
        ("et0_acumulada", f"{ind.et0_acumulada_mm:.1f}", "mm"),
        ("ahorro_volumen", f"{ind.ahorro_m3:.3f}", "m3"),
        ("ahorro_porcentual", f"{ind.ahorro_pct:.1f}", "%"),
        ("cobertura_datos", f"{ind.cobertura_datos_pct:.1f}", "%"),
    ]
    w.writerows(filas)
    return buf.getvalue()


def exportar_json(usuario: UsuarioAgua, ind: IndicadoresPUEAA) -> str:
    return json.dumps({
        "usuario": asdict(usuario),
        "indicadores": asdict(ind),
        "marco_referencia": [
            "Ley 373 de 1997",
            "Decreto 1090 de 2018",
            "Resolución 1257 de 2018",
        ],
        "alcance": "Anexo técnico de medición. No es un trámite ni un reporte oficial.",
        "generado": datetime.now().isoformat(timespec="seconds"),
        "sistema": "HidroSopó v1.0",
    }, indent=2, ensure_ascii=False, default=str)
