"""
HidroSopó — Capa de datos
==========================
SQLite por defecto (cero configuración, perfecto para el piloto).
Cambia DATABASE_URL a PostgreSQL/Supabase para producción.
"""
from __future__ import annotations
import os
from datetime import datetime
from sqlalchemy import (create_engine, Column, Integer, String, Float,
                        DateTime, Boolean, Text, Index)
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///hidrosopo.db")

# Supabase/Heroku entregan 'postgres://', SQLAlchemy 2 quiere 'postgresql://'
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class Nodo(Base):
    __tablename__ = "nodos"
    id = Column(Integer, primary_key=True)
    codigo = Column(String(50), unique=True, nullable=False, index=True)
    token = Column(String(120), nullable=False)
    tipo = Column(String(20), default="suelo")        # suelo | caudal | gateway
    predio_id = Column(Integer, index=True)
    descripcion = Column(String(200))
    activo = Column(Boolean, default=True)
    ultima_conexion = Column(DateTime)
    creado = Column(DateTime, default=datetime.utcnow)


class Predio(Base):
    __tablename__ = "predios"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(120), nullable=False)
    propietario = Column(String(120))
    documento = Column(String(40))
    telefono = Column(String(30))
    vereda = Column(String(80))
    latitud = Column(Float, default=4.9083)
    longitud = Column(Float, default=-73.9403)
    altitud_m = Column(Float, default=2587)
    area_predio_ha = Column(Float, default=0)
    area_regada_ha = Column(Float, default=0)

    perfil_cultivo = Column(String(50), default="kikuyo_pastoreo")
    tipo_suelo = Column(String(50), default="sabana_bogota")
    sistema_riego = Column(String(50), default="aspersion")
    caudal_disponible_lps = Column(Float, default=1.0)
    # Respaldo para predios de un solo sector. Si hay Sectores registrados,
    # esos mandan y estos campos se ignoran.
    area_por_turno_ha = Column(Float)
    turnos_para_cubrir = Column(Integer, default=1)

    fecha_siembra = Column(DateTime)
    fecha_ultimo_pastoreo = Column(DateTime)

    # Permiso de captación (si existe)
    tiene_concesion = Column(Boolean, default=False)
    permiso_captacion = Column(String(60))
    resolucion_concesion = Column(String(80))
    caudal_concesionado_lps = Column(Float, default=0)
    fuente_hidrica = Column(String(120))
    tipo_captacion = Column(String(40))

    # ---- Costo de mover el agua ----
    # Para un predio con quebrada o pozo propio, el agua es gratis: lo que
    # cuesta es BOMBEARLA. Este es el ahorro que el productor siente en el
    # bolsillo, y sin estos datos el proyecto solo puede hablar de metros
    # cúbicos, que a nadie le pagan la factura.
    altura_bombeo_m = Column(Float, default=30)        # altura dinámica total
    eficiencia_bomba = Column(Float, default=0.55)     # conjunto motor-bomba
    tipo_energia = Column(String(20), default="electrica")   # electrica | diesel | gravedad
    costo_kwh = Column(Float, default=850)             # COP/kWh — VERIFICAR con la factura
    consumo_diesel_lph = Column(Float, default=1.2)    # litros/hora del motor
    costo_diesel_litro = Column(Float, default=13000)  # COP/litro — VERIFICAR
    tarifa_agua_m3 = Column(Float, default=0)          # si compra agua a un acueducto
    tasa_uso_agua_m3 = Column(Float, default=0)        # tasa por volumen captado, si hay concesión
    inversion_sistema_cop = Column(Float, default=1720000)   # para calcular el retorno



    # Calibración de suelo medida en campo (sobreescribe la tabla por textura)
    capacidad_campo_pct = Column(Float)
    punto_marchitez_pct = Column(Float)

    consentimiento_firmado = Column(Boolean, default=False)
    fecha_consentimiento = Column(DateTime)
    creado = Column(DateTime, default=datetime.utcnow)


class Sector(Base):
    """Un sector de riego: el área que se moja cuando se abre esa llave.

    Una finca real no tiene "un caudal": tiene sectores con distinto
    número de aspersores, distinta área y distinto caudal. Y a veces el
    productor prende dos bombas al tiempo. Sin esto, todos los cálculos
    de lámina y de tiempo salen mal.
    """
    __tablename__ = "sectores"
    id = Column(Integer, primary_key=True)
    predio_id = Column(Integer, index=True)
    nombre = Column(String(60))                # "Potrero de arriba", "Sector 1"
    area_ha = Column(Float, default=0.25)
    caudal_lps = Column(Float, default=1.5)    # caudal cuando ESTE sector está abierto
    sistema_riego = Column(String(40), default="aspersion")
    n_emisores = Column(Integer)               # aspersores o goteros
    bomba = Column(String(40))                 # cuál bomba lo alimenta
    uniformidad = Column(Float, default=0.80)  # coeficiente de uniformidad (CU)
    activo = Column(Boolean, default=True)
    orden = Column(Integer, default=1)         # orden del turno de riego
    notas = Column(Text)


class RiegoSector(Base):
    """Qué sectores estuvieron abiertos en un evento de riego.

    Permite registrar 'prendí las dos bombas': dos filas, un evento.
    """
    __tablename__ = "riegos_sector"
    id = Column(Integer, primary_key=True)
    evento_riego_id = Column(Integer, index=True)
    sector_id = Column(Integer, index=True)
    minutos = Column(Float)
    volumen_m3 = Column(Float)
    lamina_mm = Column(Float)


class LecturaSuelo(Base):
    __tablename__ = "lecturas_suelo"
    id = Column(Integer, primary_key=True)
    nodo_codigo = Column(String(50), index=True)
    predio_id = Column(Integer, index=True)
    ts = Column(DateTime, default=datetime.utcnow, index=True)
    ciclo = Column(Integer)

    hum_adc_1 = Column(Integer)
    hum_adc_2 = Column(Integer)
    hum_adc_3 = Column(Integer)
    hum_pct_1 = Column(Float)      # ya calibrada
    hum_pct_2 = Column(Float)
    hum_pct_3 = Column(Float)

    temp_suelo_1 = Column(Float)
    temp_suelo_2 = Column(Float)
    temp_aire = Column(Float)
    hum_aire = Column(Float)
    lluvia_mm = Column(Float, default=0)
    v_bateria = Column(Float)
    rssi = Column(Integer)
    snr = Column(Float)


class LecturaCaudal(Base):
    """Los datos que sustentan el reporte de indicadores. Inmutables."""
    __tablename__ = "lecturas_caudal"
    id = Column(Integer, primary_key=True)
    nodo_codigo = Column(String(50), index=True)
    predio_id = Column(Integer, index=True)
    ts = Column(DateTime, default=datetime.utcnow, index=True)
    litros_periodo = Column(Float, default=0)
    m3_acumulado = Column(Float, default=0)     # contador histórico, nunca se reinicia
    caudal_lps = Column(Float, default=0)
    v_bateria = Column(Float)


class Recomendacion(Base):
    __tablename__ = "recomendaciones"
    id = Column(Integer, primary_key=True)
    predio_id = Column(Integer, index=True)
    ts = Column(DateTime, default=datetime.utcnow, index=True)
    accion = Column(String(20))
    urgencia = Column(String(20))
    regla = Column(String(40))
    mensaje = Column(Text)
    payload_json = Column(Text)
    enviada = Column(Boolean, default=False)
    # Retroalimentación del productor: ¿siguió la recomendación?
    seguida = Column(Boolean)
    comentario_productor = Column(Text)


class EventoRiego(Base):
    __tablename__ = "eventos_riego"
    id = Column(Integer, primary_key=True)
    predio_id = Column(Integer, index=True)
    inicio = Column(DateTime, index=True)
    fin = Column(DateTime)
    volumen_m3 = Column(Float)
    origen = Column(String(20), default="detectado")   # detectado | manual
    recomendacion_id = Column(Integer)


class Mensaje(Base):
    """Historial de la conversación con el productor.

    Sirve para dos cosas: darle contexto al agente (qué se le preguntó
    antes) y como evidencia cualitativa para el informe final.
    """
    __tablename__ = "mensajes"
    id = Column(Integer, primary_key=True)
    predio_id = Column(Integer, index=True)
    ts = Column(DateTime, default=datetime.utcnow, index=True)
    de = Column(String(12))                  # productor | sistema
    texto = Column(Text)
    intencion = Column(String(30))
    canal = Column(String(20), default="app")  # app | whatsapp | telegram
    esperando = Column(String(30))            # qué dato se le pidió


class NotaProductor(Base):
    """Lo que el productor cuenta y no es un evento de riego:
    su rutina, sus desacuerdos, sus observaciones del terreno.

    Los desacuerdos son especialmente valiosos: si él dice que la tierra
    está seca y el sensor dice lo contrario, hay un problema de sensor.
    """
    __tablename__ = "notas_productor"
    id = Column(Integer, primary_key=True)
    predio_id = Column(Integer, index=True)
    ts = Column(DateTime, default=datetime.utcnow, index=True)
    tipo = Column(String(30))    # rutina | discrepancia | problema | observacion
    texto = Column(Text)
    revisada = Column(Boolean, default=False)


Index("ix_lecturas_suelo_predio_ts", LecturaSuelo.predio_id, LecturaSuelo.ts)
Index("ix_lecturas_caudal_predio_ts", LecturaCaudal.predio_id, LecturaCaudal.ts)


def init_db():
    Base.metadata.create_all(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
