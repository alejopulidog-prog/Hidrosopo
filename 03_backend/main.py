"""
HidroSopó — API principal
==========================
FastAPI. Corre en Render / Oracle Always Free / Raspberry Pi local.

Arrancar:
    pip install -r requirements.txt
    uvicorn main:app --reload --host 0.0.0.0 --port 8000

Documentación automática: http://localhost:8000/docs
"""

from __future__ import annotations
import os
import json
from datetime import datetime, date, timedelta
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Header, Request
from fastapi.responses import PlainTextResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from db import (init_db, get_db, Nodo, Predio, LecturaSuelo,
                LecturaCaudal, Recomendacion, EventoRiego,
                Mensaje, NotaProductor, Sector, RiegoSector)
from ia import fao56
from ia.motor_recomendacion import generar_recomendacion
from ia.perfiles import listar_perfiles, SUELOS, SISTEMAS_RIEGO, obtener_perfil, obtener_suelo
from ia import modelo_ml
import reporte_pueaa as rp
import alertas
import agente
import costos

app = FastAPI(
    title="HidroSopó API",
    description="Monitoreo IoT y optimización del uso del agua — Sopó, Cundinamarca",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Calibración de los sensores, obtenida del procedimiento gravimétrico
RUTA_CAL = os.getenv("RUTA_CALIBRACION", "config_sensores.json")
try:
    CALIBRACION = json.loads(open(RUTA_CAL, encoding="utf-8").read())
except Exception:
    CALIBRACION = {}
    print(f"[WARN] {RUTA_CAL} no encontrado — se usará calibración lineal por defecto")


@app.on_event("startup")
def arranque():
    init_db()
    print("[OK] HidroSopó API lista")


# ============================================================
#  Esquemas
# ============================================================

class PayloadSuelo(BaseModel):
    id: str
    tok: str
    c: int = 0
    h: list[int] = Field(default_factory=list)      # ADC crudo x3
    ts: list[float] = Field(default_factory=list)   # temp suelo x2
    ta: float = -999
    ha: float = -999
    ll: float = 0.0
    vb: float = 0.0
    rssi: Optional[int] = None
    snr: Optional[float] = None


class PayloadCaudal(BaseModel):
    id: str
    tok: str
    lp: float = 0.0     # litros del período
    m3: float = 0.0     # m³ acumulado histórico
    qls: float = 0.0    # caudal medio l/s
    vb: float = 0.0


# ============================================================
#  Utilidades
# ============================================================

def _calibrar(adc: int, sensor: str) -> float:
    """Convierte ADC a humedad volumétrica usando la curva del sensor."""
    cal = CALIBRACION.get(sensor)
    if cal:
        return fao56.adc_a_humedad_volumetrica(adc, cal)
    # Respaldo lineal de dos puntos. Aproximado — calibra los sensores.
    adc_seco, adc_agua = 3000.0, 1300.0
    pct = (adc_seco - adc) / (adc_seco - adc_agua) * 45.0
    return max(0.0, min(60.0, pct))


def _validar_nodo(db: Session, codigo: str, token: str) -> Nodo:
    nodo = db.query(Nodo).filter(Nodo.codigo == codigo).first()
    if not nodo:
        raise HTTPException(404, f"Nodo '{codigo}' no registrado")
    if nodo.token != token:
        raise HTTPException(401, "Token inválido")
    if not nodo.activo:
        raise HTTPException(403, "Nodo desactivado")
    nodo.ultima_conexion = datetime.utcnow()
    return nodo


def _suelo_del_predio(predio: Predio) -> dict:
    """Usa la calibración medida en campo si existe; si no, la tabla por textura."""
    base = dict(obtener_suelo(predio.tipo_suelo))
    if predio.capacidad_campo_pct:
        base["capacidad_campo_pct"] = predio.capacidad_campo_pct
    if predio.punto_marchitez_pct:
        base["punto_marchitez_pct"] = predio.punto_marchitez_pct
    return base


# ============================================================
#  Ingesta de telemetría
# ============================================================

@app.post("/api/v1/telemetria")
def ingesta(payload: dict, request: Request, db: Session = Depends(get_db)):
    """Endpoint único de ingesta. Detecta el tipo por los campos presentes."""

    # --- Nodo de caudal ---
    if "m3" in payload or "qls" in payload:
        p = PayloadCaudal(**payload)
        nodo = _validar_nodo(db, p.id, p.tok)
        db.add(LecturaCaudal(
            nodo_codigo=p.id, predio_id=nodo.predio_id,
            litros_periodo=p.lp, m3_acumulado=p.m3,
            caudal_lps=p.qls, v_bateria=p.vb,
        ))
        db.commit()
        return {"ok": True, "tipo": "caudal", "m3_acumulado": p.m3}

    # --- Nodo de suelo ---
    p = PayloadSuelo(**payload)
    nodo = _validar_nodo(db, p.id, p.tok)

    adc = (p.h + [0, 0, 0])[:3]
    lect = LecturaSuelo(
        nodo_codigo=p.id, predio_id=nodo.predio_id, ciclo=p.c,
        hum_adc_1=adc[0], hum_adc_2=adc[1], hum_adc_3=adc[2],
        hum_pct_1=_calibrar(adc[0], "S1"),
        hum_pct_2=_calibrar(adc[1], "S2"),
        hum_pct_3=_calibrar(adc[2], "S3"),
        temp_suelo_1=None if not p.ts or p.ts[0] == -999 else p.ts[0],
        temp_suelo_2=None if len(p.ts) < 2 or p.ts[1] == -999 else p.ts[1],
        temp_aire=None if p.ta == -999 else p.ta,
        hum_aire=None if p.ha == -999 else p.ha,
        lluvia_mm=p.ll, v_bateria=p.vb,
        rssi=p.rssi or payload.get("rssi"),
        snr=p.snr or payload.get("snr"),
    )
    db.add(lect)
    db.commit()

    alerta_bat = p.vb < 3.5 and p.vb > 1.0
    return {"ok": True, "tipo": "suelo",
            "humedad_pct": [lect.hum_pct_1, lect.hum_pct_2, lect.hum_pct_3],
            "alerta_bateria": alerta_bat}


# ============================================================
#  Recomendaciones
# ============================================================

@app.get("/api/v1/predios/{predio_id}/recomendacion")
def recomendacion(predio_id: int, guardar: bool = False, enviar: bool = False,
                  db: Session = Depends(get_db)):
    """El endpoint principal: genera la recomendación de riego/manejo."""

    predio = db.query(Predio).get(predio_id)
    if not predio:
        raise HTTPException(404, "Predio no encontrado")

    ultima = (db.query(LecturaSuelo)
              .filter(LecturaSuelo.predio_id == predio_id)
              .order_by(desc(LecturaSuelo.ts)).first())
    if not ultima:
        raise HTTPException(404, "Aún no hay lecturas para este predio")

    # Extremos de temperatura de las últimas 24 h (los necesita Hargreaves)
    desde = datetime.utcnow() - timedelta(hours=24)
    agg = (db.query(func.max(LecturaSuelo.temp_aire), func.min(LecturaSuelo.temp_aire))
           .filter(LecturaSuelo.predio_id == predio_id, LecturaSuelo.ts >= desde).first())
    t_max = agg[0] if agg and agg[0] is not None else (ultima.temp_aire or 20.0) + 5
    t_min = agg[1] if agg and agg[1] is not None else (ultima.temp_aire or 20.0) - 5

    humedades = [h for h in (ultima.hum_pct_1, ultima.hum_pct_2, ultima.hum_pct_3)
                 if h is not None]
    if not humedades:
        raise HTTPException(422, "La última lectura no tiene datos de humedad válidos")

    # Predicción del modelo ML (si ya fue entrenado)
    pred = modelo_ml.predecir(
        humedad_actual=humedades[0],
        contexto={
            "humedad_lag_6h": humedades[0],
            "humedad_lag_24h": humedades[0],
            "delta_humedad_6h": 0.0,
            "temp_aire": ultima.temp_aire or 15.0,
            "temp_suelo": ultima.temp_suelo_1 or 15.0,
            "hr_aire": ultima.hum_aire or 70.0,
            "et0_acumulada_24h": 3.0,
            "lluvia_acumulada_24h": ultima.lluvia_mm or 0.0,
            "lluvia_pronosticada_24h": 0.0,
            "lluvia_pronosticada_48h": 0.0,
            "hora_sin": 0.0, "hora_cos": 1.0,
            "dia_año_sin": 0.0, "dia_año_cos": 1.0,
            "profundidad_cm": 15,
        },
        horizonte_horas=48,
    )
    if pred:
        pred = {"humedad_48h_pct": pred["humedad_48h_pct"],
                "confianza": pred["confianza"], "mae": pred["mae"]}

    dias_siembra = None
    if predio.fecha_siembra:
        dias_siembra = (datetime.utcnow() - predio.fecha_siembra).days
    dias_pastoreo = None
    if predio.fecha_ultimo_pastoreo:
        dias_pastoreo = (datetime.utcnow() - predio.fecha_ultimo_pastoreo).days

    r = generar_recomendacion(
        lecturas_humedad_pct=humedades,
        temp_aire_c=ultima.temp_aire or 15.0,
        temp_max_c=t_max, temp_min_c=t_min,
        hr_pct=ultima.hum_aire or 70.0,
        perfil_clave=predio.perfil_cultivo,
        suelo_clave=predio.tipo_suelo,
        sistema_riego=predio.sistema_riego,
        area_m2=(predio.area_por_turno_ha or predio.area_regada_ha or 0) * 10000,
        caudal_disponible_lps=predio.caudal_disponible_lps,
        lat=predio.latitud, lon=predio.longitud,
        dias_desde_siembra=dias_siembra,
        dias_desde_ultimo_pastoreo=dias_pastoreo,
        prediccion_ml=pred,
    )
    r["predio"] = {"id": predio.id, "nombre": predio.nombre,
                   "propietario": predio.propietario}
    r["ultima_lectura"] = ultima.ts.isoformat()

    if guardar:
        rec = Recomendacion(
            predio_id=predio_id, accion=r["decision"]["accion"],
            urgencia=r["decision"]["urgencia"], regla=r["decision"]["regla"],
            mensaje=r["mensaje"], payload_json=json.dumps(r, ensure_ascii=False, default=str),
        )
        db.add(rec); db.commit(); db.refresh(rec)
        r["recomendacion_id"] = rec.id

        if enviar and predio.telefono:
            ok = alertas.enviar(predio.telefono, r["mensaje"])
            rec.enviada = ok
            db.commit()
            r["alerta_enviada"] = ok

    return r


# ============================================================
#  Agente conversacional
# ============================================================

class MensajeEntrada(BaseModel):
    texto: str
    canal: str = "app"


def _consumo_por_dia(db: Session, predio_id: int, desde: datetime, hasta: datetime):
    filas = (db.query(func.date(LecturaCaudal.ts).label("dia"),
                      func.sum(LecturaCaudal.litros_periodo).label("litros"))
             .filter(LecturaCaudal.predio_id == predio_id,
                     LecturaCaudal.ts >= desde, LecturaCaudal.ts < hasta)
             .group_by("dia").order_by("dia").all())
    return [{"fecha": str(f.dia), "m3": round((f.litros or 0) / 1000, 3)} for f in filas]


def _ahorro(db: Session, predio_id: int, dias: int = 30) -> dict:
    """Compara el consumo reciente contra el mismo número de días previos.

    Es la línea base 'antes vs. después'. Si no hay suficientes días
    previos, devuelve sin_datos en vez de inventar una cifra.
    """
    ahora = datetime.utcnow()
    corte = ahora - timedelta(days=dias)
    inicio = corte - timedelta(days=dias)
    actual = _consumo_por_dia(db, predio_id, corte, ahora)
    base = _consumo_por_dia(db, predio_id, inicio, corte)
    if len(base) < 5 or len(actual) < 5:
        return {"sin_datos": True,
                "motivo": "Faltan días de medición para comparar contra una línea base."}
    return agente.calcular_ahorro(actual, base, dias)


@app.post("/api/v1/predios/{predio_id}/conversar")
def conversar(predio_id: int, entrada: MensajeEntrada, db: Session = Depends(get_db)):
    """El productor le escribe al sistema. Aquí vive el agente."""
    predio = db.query(Predio).get(predio_id)
    if not predio:
        raise HTTPException(404, "Predio no encontrado")

    # ¿Se le había pedido un dato concreto en el turno anterior?
    ultimo = (db.query(Mensaje)
              .filter(Mensaje.predio_id == predio_id, Mensaje.de == "sistema")
              .order_by(desc(Mensaje.ts)).first())
    esperando = ultimo.esperando if ultimo else None

    db.add(Mensaje(predio_id=predio_id, de="productor",
                   texto=entrada.texto, canal=entrada.canal))

    # Contexto: la recomendación viva y el ahorro real
    try:
        rec = recomendacion(predio_id, guardar=False, enviar=False, db=db)
    except HTTPException:
        rec = None

    sectores = (db.query(Sector).filter(Sector.predio_id == predio_id,
                                        Sector.activo == True).all())   # noqa: E712

    # Si el turno anterior dejó datos a medias (minutos sin sector), se recuperan
    pendiente = {}
    if esperando == "sector_riego":
        # El mensaje nuevo aún no está en la base (la sesión no hace autoflush),
        # así que los últimos mensajes del productor son los anteriores a este.
        for prev in (db.query(Mensaje)
                     .filter(Mensaje.predio_id == predio_id, Mensaje.de == "productor")
                     .order_by(desc(Mensaje.ts)).limit(3).all()):
            mins = agente.extraer_minutos(prev.texto)
            if mins:
                pendiente["minutos"] = mins
                break

    salida = agente.conversar(entrada.texto, {
        "predio": predio, "recomendacion": rec, "sectores": sectores,
        "ahorro": _ahorro(db, predio_id), "esperando": esperando,
        "pendiente": pendiente,
    })

    # ---- Ejecutar la acción que el agente decidió ----
    accion = salida.get("accion")
    d = salida.get("datos", {})

    if accion == "registrar_riego" and d.get("minutos"):
        ahora = datetime.utcnow()
        ev = EventoRiego(predio_id=predio_id, inicio=ahora,
                         fin=ahora + timedelta(minutes=d["minutos"]),
                         volumen_m3=d.get("volumen_m3"), origen="reportado")
        db.add(ev); db.flush()
        for sd in d.get("sectores") or []:
            db.add(RiegoSector(evento_riego_id=ev.id, sector_id=sd["sector_id"],
                               minutos=sd["minutos"], volumen_m3=sd["volumen_m3"],
                               lamina_mm=sd["lamina_mm"]))
    elif accion == "registrar_caudal" and d.get("caudal_lps"):
        # El productor midió su bomba con el balde. Se guarda donde corresponda.
        if len(sectores) == 1:
            sectores[0].caudal_lps = d["caudal_lps"]
        predio.caudal_disponible_lps = d["caudal_lps"]
        db.add(NotaProductor(predio_id=predio_id, tipo="observacion",
                             texto=f"Caudal medido con balde: {d['caudal_lps']} l/s"))
    elif accion == "registrar_rutina":
        db.add(NotaProductor(predio_id=predio_id, tipo="rutina", texto=entrada.texto))
    elif accion == "registrar_discrepancia":
        db.add(NotaProductor(predio_id=predio_id, tipo="discrepancia", texto=entrada.texto))
        alertas.alerta_tecnica(
            f"El productor de '{predio.nombre}' no coincide con la lectura: "
            f"\"{entrada.texto}\". Revisar calibración e instalación del sensor.")
    elif accion == "alertar_tecnico":
        db.add(NotaProductor(predio_id=predio_id, tipo="problema", texto=entrada.texto))
        alertas.alerta_tecnica(f"Problema reportado en '{predio.nombre}': {entrada.texto}")
    elif accion == "registrar_no_riego":
        db.add(NotaProductor(predio_id=predio_id, tipo="observacion",
                             texto=f"No hubo riego: {entrada.texto}"))

    db.add(Mensaje(predio_id=predio_id, de="sistema", texto=salida["texto"],
                   intencion=salida.get("intencion"), canal=entrada.canal,
                   esperando=salida.get("esperando")))
    db.commit()

    return {"respuesta": salida["texto"],
            "intencion": salida.get("intencion"),
            "confianza": salida.get("confianza"),
            "accion_ejecutada": accion,
            "esperando": salida.get("esperando")}


@app.get("/api/v1/predios/{predio_id}/conversacion")
def historial(predio_id: int, n: int = 40, db: Session = Depends(get_db)):
    ms = (db.query(Mensaje).filter(Mensaje.predio_id == predio_id)
          .order_by(desc(Mensaje.ts)).limit(n).all())
    return [{"ts": m.ts.isoformat(), "de": m.de, "texto": m.texto,
             "intencion": m.intencion} for m in reversed(ms)]


@app.get("/api/v1/predios/{predio_id}/ahorro")
def ahorro(predio_id: int, dias: int = 30, db: Session = Depends(get_db)):
    """Cuánta agua se ha ahorrado. El número que justifica todo el proyecto."""
    return _ahorro(db, predio_id, dias)


@app.get("/api/v1/predios/{predio_id}/riegos")
def riegos(predio_id: int, dias: int = 30, db: Session = Depends(get_db)):
    """Eventos de riego reportados por el productor o detectados por el caudalímetro."""
    desde = datetime.utcnow() - timedelta(days=dias)
    evs = (db.query(EventoRiego)
           .filter(EventoRiego.predio_id == predio_id, EventoRiego.inicio >= desde)
           .order_by(desc(EventoRiego.inicio)).all())
    return [{"inicio": e.inicio.isoformat(),
             "minutos": round((e.fin - e.inicio).total_seconds() / 60) if e.fin else None,
             "volumen_m3": e.volumen_m3, "origen": e.origen} for e in evs]


@app.get("/api/v1/predios/{predio_id}/sectores")
def listar_sectores(predio_id: int, db: Session = Depends(get_db)):
    ss = (db.query(Sector).filter(Sector.predio_id == predio_id)
          .order_by(Sector.orden).all())
    return [{"id": x.id, "orden": x.orden, "nombre": x.nombre, "area_ha": x.area_ha,
             "caudal_lps": x.caudal_lps, "sistema_riego": x.sistema_riego,
             "n_emisores": x.n_emisores, "bomba": x.bomba,
             "uniformidad": x.uniformidad, "activo": x.activo,
             "tasa_aplicacion_mm_h": round((x.caudal_lps or 0) * 3.6 / (x.area_ha or 1) / 10, 2)
             } for x in ss]


@app.get("/api/v1/predios/{predio_id}/costo-agua")
def costo_agua(predio_id: int, dias: int = 30, db: Session = Depends(get_db)):
    """Qué significa el ahorro en pesos. El número que sostiene el proyecto
    frente al productor: los m³ son para el informe, los pesos son para él."""
    predio = db.query(Predio).get(predio_id)
    if not predio:
        raise HTTPException(404, "Predio no encontrado")

    a = _ahorro(db, predio_id, dias)
    salida = {
        "predio": predio.nombre,
        "desglose_por_m3": costos.desglose_por_m3(predio),
    }

    if a.get("sin_datos"):
        salida["ahorro"] = None
        salida["motivo"] = a.get("motivo")
        return salida

    ahorro = costos.valorizar(a["ahorro_m3"], predio)
    salida["ahorro"] = ahorro
    salida["gasto_actual"] = costos.valorizar(a["volumen_actual_m3"], predio)
    salida["gasto_antes"] = costos.valorizar(a["linea_base_m3"], predio)
    salida["proyeccion_anual"] = costos.proyectar_anual(a["ahorro_m3"], a["dias"], predio)
    salida["retorno_inversion"] = costos.retorno_inversion(
        a["ahorro_m3"], a["dias"], predio,
        float(predio.inversion_sistema_cop or 1720000))
    salida["equivalencias"] = costos.equivalencias(a["ahorro_m3"], ahorro["kwh"])
    salida["detalle_volumen"] = a
    return salida


@app.get("/api/v1/predios/{predio_id}/notas")
def notas(predio_id: int, db: Session = Depends(get_db)):
    """Lo que el productor ha contado. Para el técnico y para el informe final."""
    ns = (db.query(NotaProductor).filter(NotaProductor.predio_id == predio_id)
          .order_by(desc(NotaProductor.ts)).all())
    return [{"ts": n.ts.isoformat(), "tipo": n.tipo, "texto": n.texto,
             "revisada": n.revisada} for n in ns]


# ============================================================
#  Consulta de datos
# ============================================================

@app.get("/api/v1/predios")
def predios(db: Session = Depends(get_db)):
    return [{"id": p.id, "nombre": p.nombre, "propietario": p.propietario,
             "vereda": p.vereda, "perfil": p.perfil_cultivo,
             "area_regada_ha": p.area_regada_ha,
             "tiene_concesion": p.tiene_concesion}
            for p in db.query(Predio).all()]


@app.get("/api/v1/predios/{predio_id}/series")
def series(predio_id: int, horas: int = 168, db: Session = Depends(get_db)):
    """Serie temporal para las gráficas del dashboard. 168 h = 7 días."""
    desde = datetime.utcnow() - timedelta(hours=horas)
    ls = (db.query(LecturaSuelo)
          .filter(LecturaSuelo.predio_id == predio_id, LecturaSuelo.ts >= desde)
          .order_by(LecturaSuelo.ts).all())
    lc = (db.query(LecturaCaudal)
          .filter(LecturaCaudal.predio_id == predio_id, LecturaCaudal.ts >= desde)
          .order_by(LecturaCaudal.ts).all())
    return {
        "suelo": [{"ts": x.ts.isoformat(), "h1": x.hum_pct_1, "h2": x.hum_pct_2,
                   "h3": x.hum_pct_3, "ta": x.temp_aire, "ts1": x.temp_suelo_1,
                   "ha": x.hum_aire, "lluvia": x.lluvia_mm, "vbat": x.v_bateria,
                   "rssi": x.rssi} for x in ls],
        "caudal": [{"ts": x.ts.isoformat(), "litros": x.litros_periodo,
                    "m3_acum": x.m3_acumulado, "qlps": x.caudal_lps} for x in lc],
    }


@app.get("/api/v1/predios/{predio_id}/consumo")
def consumo(predio_id: int, dias: int = 30, db: Session = Depends(get_db)):
    """Consumo agregado por día. La base del reporte de indicadores del PUEAA."""
    desde = datetime.utcnow() - timedelta(days=dias)
    filas = (db.query(func.date(LecturaCaudal.ts).label("dia"),
                      func.sum(LecturaCaudal.litros_periodo).label("litros"),
                      func.max(LecturaCaudal.caudal_lps).label("q_max"))
             .filter(LecturaCaudal.predio_id == predio_id, LecturaCaudal.ts >= desde)
             .group_by("dia").order_by("dia").all())
    return [{"fecha": str(f.dia), "litros": round(f.litros or 0, 1),
             "m3": round((f.litros or 0) / 1000, 3),
             "caudal_max_lps": round(f.q_max or 0, 4)} for f in filas]


@app.get("/api/v1/catalogos")
def catalogos():
    return {"perfiles": listar_perfiles(),
            "suelos": list(SUELOS.keys()),
            "sistemas_riego": [{"clave": k, **v} for k, v in SISTEMAS_RIEGO.items()]}


# ============================================================
#  Reporte PUEAA
# ============================================================

@app.get("/api/v1/predios/{predio_id}/reporte-pueaa", response_class=PlainTextResponse)
def reporte(predio_id: int, desde: str, hasta: str, formato: str = "markdown",
            linea_base_m3: float = 0.0, db: Session = Depends(get_db)):
    """Genera el anexo técnico de indicadores para el PUEAA municipal.

    formato: markdown | csv | json
    Fechas en formato YYYY-MM-DD.
    """
    predio = db.query(Predio).get(predio_id)
    if not predio:
        raise HTTPException(404, "Predio no encontrado")

    d0 = date.fromisoformat(desde)
    d1 = date.fromisoformat(hasta)

    usuario = rp.UsuarioAgua(
        nombre_predio=predio.nombre, propietario=predio.propietario or "",
        documento=predio.documento or "", vereda=predio.vereda or "",
        coordenadas=(predio.latitud, predio.longitud),
        area_predio_ha=predio.area_predio_ha, area_regada_ha=predio.area_regada_ha,
        tiene_concesion=predio.tiene_concesion,
        numero_permiso=predio.permiso_captacion or "",
        resolucion_concesion=predio.resolucion_concesion or "",
        caudal_concesionado_lps=predio.caudal_concesionado_lps,
        fuente_hidrica=predio.fuente_hidrica or "",
        tipo_captacion=predio.tipo_captacion or "",
        sistema_riego=predio.sistema_riego,
    )

    lc = (db.query(LecturaCaudal)
          .filter(LecturaCaudal.predio_id == predio_id,
                  func.date(LecturaCaudal.ts) >= d0,
                  func.date(LecturaCaudal.ts) <= d1).all())
    ls = (db.query(LecturaSuelo)
          .filter(LecturaSuelo.predio_id == predio_id,
                  func.date(LecturaSuelo.ts) >= d0,
                  func.date(LecturaSuelo.ts) <= d1).all())

    registros_caudal = [{"ts": x.ts.isoformat(), "litros_periodo": x.litros_periodo,
                         "caudal_lps": x.caudal_lps} for x in lc]
    registros_clima = [{"ts": x.ts.isoformat(), "lluvia_mm": x.lluvia_mm or 0,
                        "et0_mm": 0} for x in ls]

    ind = rp.calcular_indicadores(
        usuario, registros_caudal, registros_clima, d0, d1,
        volumen_linea_base_m3=linea_base_m3,
    )

    if formato == "csv":
        return PlainTextResponse(rp.exportar_csv_indicadores(usuario, ind),
                                 media_type="text/csv")
    if formato == "json":
        return PlainTextResponse(rp.exportar_json(usuario, ind),
                                 media_type="application/json")
    return rp.generar_reporte_markdown(usuario, ind)


# ============================================================
#  Panel institucional (Emsersopó / Secretaría de Ambiente)
# ============================================================

@app.get("/api/v1/institucional/resumen")
def resumen_institucional(db: Session = Depends(get_db)):
    """Vista agregada del municipio. Solo lectura, sin datos personales.

    Esto es lo que se le ofrece a Emsersopó y a la Secretaría de Ambiente:
    demanda hídrica rural real, sin exponer información del productor.
    """
    predios = db.query(Predio).all()
    total = 0.0
    detalle = []
    for p in predios:
        m3 = (db.query(func.sum(LecturaCaudal.litros_periodo))
              .filter(LecturaCaudal.predio_id == p.id).scalar() or 0) / 1000.0
        total += m3
        detalle.append({
            "predio_id": p.id,
            "vereda": p.vereda,
            "actividad": p.perfil_cultivo,
            "area_regada_ha": p.area_regada_ha,
            "volumen_acumulado_m3": round(m3, 2),
            "tiene_concesion": p.tiene_concesion,
            "modulo_consumo_lps_ha": None,
        })
    return {
        "municipio": "Sopó, Cundinamarca",
        "predios_monitoreados": len(predios),
        "volumen_total_m3": round(total, 2),
        "area_total_monitoreada_ha": round(sum(p.area_regada_ha for p in predios), 2),
        "predios_sin_concesion": sum(1 for p in predios if not p.tiene_concesion),
        "detalle": detalle,
        "nota": "Datos agregados de monitoreo con fines de planificación del recurso "
                "hídrico. No incluye información personal de los productores.",
    }


# ============================================================
#  Salud y raíz
# ============================================================

@app.get("/api/v1/salud")
def salud(db: Session = Depends(get_db)):
    nodos = db.query(Nodo).all()
    ahora = datetime.utcnow()
    return {
        "estado": "ok",
        "hora_servidor": ahora.isoformat(),
        "nodos": [{
            "codigo": n.codigo, "tipo": n.tipo, "activo": n.activo,
            "ultima_conexion": n.ultima_conexion.isoformat() if n.ultima_conexion else None,
            "minutos_sin_reportar": round((ahora - n.ultima_conexion).total_seconds() / 60)
                                    if n.ultima_conexion else None,
            "en_linea": bool(n.ultima_conexion and (ahora - n.ultima_conexion) < timedelta(minutes=45)),
        } for n in nodos],
        "modelos_ml": modelo_ml.resumen_modelos(),
    }


@app.get("/", response_class=HTMLResponse)
def raiz():
    return """<h1>HidroSopó API</h1>
    <p>Sistema de monitoreo IoT y optimización del uso del agua — Sopó, Cundinamarca</p>
    <ul>
      <li><a href="/docs">Documentación interactiva (Swagger)</a></li>
      <li><a href="/api/v1/salud">Estado del sistema</a></li>
      <li><a href="/api/v1/predios">Predios</a></li>
    </ul>"""
