"""
HidroSopó - Simulador integral del sistema
-------------------------------------------
Genera 4 escenarios completos de prueba para el dashboard:

1. Predio Demo Acueducto
   - Agua de acueducto
   - Se paga tarifa por m3
   - Sin bombeo
   - El ahorro económico se concentra en agua

2. Predio Demo Lago
   - Fuente superficial propia
   - Bombeo eléctrico
   - El ahorro económico se concentra en energía

3. Predio Demo Diesel
   - Fuente superficial propia
   - Bombeo con motor diésel
   - El ahorro económico se concentra en combustible

4. Predio Demo Invernadero
   - Flor de exportación bajo cubierta, riego por goteo
   - Único con bajo_cubierta=True: no espera lluvia que no le llega
   - Distinto perfil de cultivo y tipo de suelo a los otros tres

Cada predio contiene:
- 4 sectores
- 3 nodos (2 suelo + 1 caudal)
- 60 días de historia
- lecturas de suelo cada 6 horas
- lecturas de caudal diarias
- línea base de 30 días con mayor consumo
- período actual de 30 días con menor consumo
- eventos de riego
- detalle de riego por sector
- nodos online/offline
- fechas relativas a datetime.utcnow()

Ejecutar desde 03_backend:

    python simular_sistema.py

ADVERTENCIA:
Este script SOLO borra los cuatro predios de simulación:
- Predio Demo Acueducto
- Predio Demo Lago
- Predio Demo Diesel
- Predio Demo Invernadero

No toca otros predios.
"""

from datetime import datetime, timedelta
import math
import random

from db import (
    init_db,
    SessionLocal,
    Predio,
    Nodo,
    Sector,
    LecturaSuelo,
    LecturaCaudal,
    EventoRiego,
    RiegoSector,
    Recomendacion,
    Mensaje,
    NotaProductor,
)


random.seed(42)


# ============================================================
# CONFIGURACIÓN GENERAL
# ============================================================

DIAS_HISTORIA = 60
NUM_SECTORES = 4

CAUDAL_SECTOR_LPS = 1.5

MINUTOS_BASE_POR_SECTOR = 45
MINUTOS_ACTUAL_POR_SECTOR = 30

NOMBRES_SECTORES = [
    "Sector 1 - Norte",
    "Sector 2 - Centro",
    "Sector 3 - Oriente",
    "Sector 4 - Sur",
]


# ============================================================
# ESCENARIOS
# ============================================================

ESCENARIOS = [
    {
        "nombre": "Predio Demo Acueducto",
        "propietario": "Productor Demo Acueducto",
        "fuente_hidrica": "Acueducto",
        "tipo_captacion": "acueducto",
        "tipo_energia": "gravedad",

        # El acueducto cobra por cada m3.
        "tarifa_agua_m3": 4200,

        # No se utiliza bombeo.
        "altura_bombeo_m": 0,
        "eficiencia_bomba": 1.0,

        # Valores diesel quedan disponibles pero no se utilizan.
        "consumo_diesel_lph": 0,
        "costo_diesel_litro": 13000,

        "descripcion":
            "Escenario de agua de acueducto con tarifa por metro cúbico. "
            "Permite demostrar ahorro directo en factura de agua.",
    },

    {
        "nombre": "Predio Demo Lago",
        "propietario": "Productor Demo Lago",
        "fuente_hidrica": "Lago / fuente superficial propia",
        "tipo_captacion": "bombeo",
        "tipo_energia": "electrica",

        # Agua propia: no hay tarifa de agua.
        "tarifa_agua_m3": 0,

        # Bombeo eléctrico.
        "altura_bombeo_m": 30,
        "eficiencia_bomba": 0.55,
        "costo_kwh": 850,

        "consumo_diesel_lph": 1.2,
        "costo_diesel_litro": 13000,

        "descripcion":
            "Escenario de fuente superficial propia con bomba eléctrica. "
            "Permite demostrar ahorro energético.",
    },

    {
        "nombre": "Predio Demo Diesel",
        "propietario": "Productor Demo Diesel",
        "fuente_hidrica": "Reservorio / fuente superficial propia",
        "tipo_captacion": "bombeo",
        "tipo_energia": "diesel",

        # Agua propia: no hay tarifa de agua.
        "tarifa_agua_m3": 0,

        # Bombeo con motor diésel.
        "altura_bombeo_m": 30,
        "eficiencia_bomba": 0.55,

        "costo_kwh": 850,

        # Consumo del motor.
        "consumo_diesel_lph": 1.2,
        "costo_diesel_litro": 13000,

        "descripcion":
            "Escenario de fuente superficial propia con bombeo diésel. "
            "Permite demostrar ahorro de combustible.",
    },

    {
        "nombre": "Predio Demo Invernadero",
        "propietario": "Productor Demo Invernadero",
        "fuente_hidrica": "Acueducto",
        "tipo_captacion": "acueducto",
        "tipo_energia": "electrica",

        # Flor de exportación bajo cubierta: perfil, suelo y riego
        # distintos a los otros tres escenarios (que son pastoreo).
        "perfil_cultivo": "flores_invernadero",
        "tipo_suelo": "franco",
        "sistema_riego": "goteo",
        "bajo_cubierta": True,

        "tarifa_agua_m3": 2100,

        # Bombeo eléctrico de presión para el goteo.
        "altura_bombeo_m": 18,
        "eficiencia_bomba": 0.65,
        "costo_kwh": 920,

        "consumo_diesel_lph": 0,
        "costo_diesel_litro": 13000,

        "descripcion":
            "Escenario de invernadero de flores con riego por goteo y tarifa de "
            "acueducto. Es el único de los cuatro que corre con bajo_cubierta=True: "
            "sirve para demostrar que el sistema no espera lluvia que la planta "
            "nunca recibe bajo plástico.",
    },
]


# ============================================================
# TOKENS Y NODOS
# ============================================================

def nombres_nodos(indice):
    """
    Genera nombres únicos para cada predio.
    """

    sufijo = f"{indice:02d}"

    return {
        "soil_1": f"NODO_DEMO_{sufijo}_SUELO_01",
        "soil_2": f"NODO_DEMO_{sufijo}_SUELO_02",
        "flow": f"NODO_DEMO_{sufijo}_CAUDAL_01",
    }


def tokens_nodos(indice):

    sufijo = f"{indice:02d}"

    return {
        "soil_1": f"demo-{sufijo}-suelo-01",
        "soil_2": f"demo-{sufijo}-suelo-02",
        "flow": f"demo-{sufijo}-caudal-01",
    }


# ============================================================
# BORRAR SIMULACIÓN ANTERIOR
# ============================================================

def borrar_predio_simulacion(db, nombre):

    predio = (
        db.query(Predio)
        .filter(Predio.nombre == nombre)
        .first()
    )

    if not predio:
        return False

    # Sectores asociados.
    sector_ids = [
        s.id
        for s in db.query(Sector)
        .filter(Sector.predio_id == predio.id)
        .all()
    ]

    # Eventos asociados.
    evento_ids = [
        e.id
        for e in db.query(EventoRiego)
        .filter(EventoRiego.predio_id == predio.id)
        .all()
    ]

    # Primero detalles de riego.
    if evento_ids:
        db.query(RiegoSector).filter(
            RiegoSector.evento_riego_id.in_(evento_ids)
        ).delete(
            synchronize_session=False
        )

    if sector_ids:
        db.query(RiegoSector).filter(
            RiegoSector.sector_id.in_(sector_ids)
        ).delete(
            synchronize_session=False
        )

    # Eventos.
    db.query(EventoRiego).filter(
        EventoRiego.predio_id == predio.id
    ).delete(
        synchronize_session=False
    )

    # Lecturas.
    db.query(LecturaSuelo).filter(
        LecturaSuelo.predio_id == predio.id
    ).delete(
        synchronize_session=False
    )

    db.query(LecturaCaudal).filter(
        LecturaCaudal.predio_id == predio.id
    ).delete(
        synchronize_session=False
    )

    # Recomendaciones.
    db.query(Recomendacion).filter(
        Recomendacion.predio_id == predio.id
    ).delete(
        synchronize_session=False
    )

    # Mensajes.
    db.query(Mensaje).filter(
        Mensaje.predio_id == predio.id
    ).delete(
        synchronize_session=False
    )

    # Notas.
    db.query(NotaProductor).filter(
        NotaProductor.predio_id == predio.id
    ).delete(
        synchronize_session=False
    )

    # Nodos.
    db.query(Nodo).filter(
        Nodo.predio_id == predio.id
    ).delete(
        synchronize_session=False
    )

    # Sectores.
    db.query(Sector).filter(
        Sector.predio_id == predio.id
    ).delete(
        synchronize_session=False
    )

    # Finalmente el predio.
    db.delete(predio)

    db.commit()

    return True


# ============================================================
# CREAR PREDIO
# ============================================================

def crear_predio(db, escenario):

    ahora = datetime.utcnow()

    predio = Predio(

        nombre=escenario["nombre"],

        propietario=escenario["propietario"],

        documento="",

        telefono="",

        vereda="Sopó",

        latitud=4.9083,

        longitud=-73.9403,

        altitud_m=2587,

        area_predio_ha=1.0,

        area_regada_ha=1.0,

        perfil_cultivo=escenario.get("perfil_cultivo", "kikuyo_pastoreo"),

        tipo_suelo=escenario.get("tipo_suelo", "sabana_bogota"),

        sistema_riego=escenario.get("sistema_riego", "aspersion"),

        caudal_disponible_lps=1.5,

        area_por_turno_ha=0.25,

        turnos_para_cubrir=4,

        fecha_siembra=ahora - timedelta(days=120),

        fecha_ultimo_pastoreo=ahora - timedelta(days=18),

        tiene_concesion=False,

        caudal_concesionado_lps=0,

        fuente_hidrica=escenario["fuente_hidrica"],

        tipo_captacion=escenario["tipo_captacion"],

        altura_bombeo_m=escenario["altura_bombeo_m"],

        eficiencia_bomba=escenario["eficiencia_bomba"],

        tipo_energia=escenario["tipo_energia"],

        costo_kwh=escenario.get("costo_kwh", 850),

        consumo_diesel_lph=escenario["consumo_diesel_lph"],

        costo_diesel_litro=escenario["costo_diesel_litro"],

        tarifa_agua_m3=escenario["tarifa_agua_m3"],

        tasa_uso_agua_m3=0,

        inversion_sistema_cop=1720000,

        capacidad_campo_pct=32,

        punto_marchitez_pct=16,

        consentimiento_firmado=True,

        fecha_consentimiento=ahora - timedelta(days=60),

        bajo_cubierta=escenario.get("bajo_cubierta", False),

    )

    db.add(predio)

    db.flush()

    return predio


# ============================================================
# CREAR SECTORES
# ============================================================

def crear_sectores(db, predio):

    sectores = []

    for orden, nombre in enumerate(
        NOMBRES_SECTORES,
        1
    ):

        sector = Sector(

            predio_id=predio.id,

            nombre=nombre,

            area_ha=0.25,

            caudal_lps=CAUDAL_SECTOR_LPS,

            sistema_riego=predio.sistema_riego or "aspersion",

            n_emisores=120,

            bomba="Bomba principal",

            uniformidad=0.82,

            activo=True,

            orden=orden,

            notas=(
                "Sector generado para simulación. "
                "Área 0.25 ha y caudal 1.50 L/s."
            ),
        )

        db.add(sector)

        sectores.append(sector)

    db.flush()

    return sectores


# ============================================================
# CREAR NODOS
# ============================================================

def crear_nodos(db, predio, indice):

    ahora = datetime.utcnow()

    nombres = nombres_nodos(indice)
    tokens = tokens_nodos(indice)

    nodos = [

        Nodo(
            codigo=nombres["soil_1"],
            token=tokens["soil_1"],
            tipo="suelo",
            predio_id=predio.id,
            descripcion="Nodo de suelo demo - sectores 1 y 2",
            activo=True,
            ultima_conexion=ahora - timedelta(minutes=4),
        ),

        Nodo(
            codigo=nombres["soil_2"],
            token=tokens["soil_2"],
            tipo="suelo",
            predio_id=predio.id,
            descripcion="Nodo de suelo demo - sectores 3 y 4",
            activo=True,
            ultima_conexion=ahora - timedelta(minutes=12),
        ),

        Nodo(
            codigo=nombres["flow"],
            token=tokens["flow"],
            tipo="caudal",
            predio_id=predio.id,
            descripcion="Caudalímetro demo",
            activo=True,

            # Se dejará OFFLINE después de crear todos los datos.
            ultima_conexion=ahora - timedelta(minutes=70),
        ),
    ]

    db.add_all(nodos)

    db.flush()

    return nodos


# ============================================================
# HUMEDAD
# ============================================================

def humedad_base(dia_idx, profundidad):

    offsets = {
        15: 0.0,
        30: 2.5,
        45: 4.0,
    }

    ciclo = (
        24
        + 3.5 * math.sin(dia_idx / 4.5)
    )

    ruido = random.uniform(
        -1.0,
        1.0
    )

    return (
        ciclo
        + offsets[profundidad]
        + ruido
    )


def generar_humedad(
    dia_idx,
    hora,
    profundidad,
    evento_riego,
    lluvia,
):

    h = humedad_base(
        dia_idx,
        profundidad
    )

    if evento_riego:

        factor = {
            15: 8.0,
            30: 5.0,
            45: 3.0,
        }[profundidad]

        h += factor

    if lluvia > 0:

        factor_lluvia = {
            15: 0.8,
            30: 0.5,
            45: 0.25,
        }[profundidad]

        h += lluvia * factor_lluvia

    # Variación horaria.
    h += (
        0.8
        * math.sin(
            (hora - 6)
            / 24
            * 2
            * math.pi
        )
    )

    return max(
        17.0,
        min(34.0, h)
    )


# ============================================================
# ADC
# ============================================================

def adc_desde_humedad(h):

    adc = (
        3000
        - (h / 45.0)
        * (3000 - 1300)
    )

    return int(
        max(
            1300,
            min(3000, adc)
        )
    )


# ============================================================
# EVENTOS DE RIEGO
# ============================================================

def crear_eventos_simulados():

    eventos = {}

    volumen_base_sector = (
        CAUDAL_SECTOR_LPS
        * MINUTOS_BASE_POR_SECTOR
        * 60
        / 1000
    )

    volumen_actual_sector = (
        CAUDAL_SECTOR_LPS
        * MINUTOS_ACTUAL_POR_SECTOR
        * 60
        / 1000
    )

    for dia_idx in range(DIAS_HISTORIA):

        # ----------------------------------------------------
        # PRIMEROS 30 DÍAS
        # Línea base
        # ----------------------------------------------------

        if dia_idx < 30:

            # Cada 3 días.
            if dia_idx % 3 == 1:

                eventos[dia_idx] = {

                    "minutos":
                        MINUTOS_BASE_POR_SECTOR
                        * NUM_SECTORES,

                    "m3":
                        round(
                            volumen_base_sector
                            * NUM_SECTORES,
                            2
                        ),

                    "minutos_por_sector":
                        MINUTOS_BASE_POR_SECTOR,

                    "por_sector":
                        round(
                            volumen_base_sector,
                            2
                        ),
                }

        # ----------------------------------------------------
        # ÚLTIMOS 30 DÍAS
        # Período actual
        # ----------------------------------------------------

        else:

            # Cada 5 días.
            if dia_idx % 5 == 2:

                eventos[dia_idx] = {

                    "minutos":
                        MINUTOS_ACTUAL_POR_SECTOR
                        * NUM_SECTORES,

                    "m3":
                        round(
                            volumen_actual_sector
                            * NUM_SECTORES,
                            2
                        ),

                    "minutos_por_sector":
                        MINUTOS_ACTUAL_POR_SECTOR,

                    "por_sector":
                        round(
                            volumen_actual_sector,
                            2
                        ),
                }

    return eventos


# ============================================================
# LLUVIAS
# ============================================================

def crear_lluvias():

    lluvias = {}

    for dia_idx in range(DIAS_HISTORIA):

        if dia_idx % 9 == 4:

            lluvias[dia_idx] = round(
                random.uniform(2.0, 7.0),
                1
            )

        elif dia_idx % 17 == 8:

            lluvias[dia_idx] = round(
                random.uniform(8.0, 14.0),
                1
            )

        else:

            lluvias[dia_idx] = 0.0

    return lluvias


# ============================================================
# LECTURAS DE SUELO
# ============================================================

def crear_lecturas_suelo(
    db,
    predio,
    inicio,
    eventos,
    lluvias,
    indice,
):

    nombres = nombres_nodos(indice)

    for dia_idx in range(
        DIAS_HISTORIA
    ):

        fecha = (
            inicio
            + timedelta(days=dia_idx)
        )

        for hora in (
            0,
            6,
            12,
            18,
        ):

            ts = (
                fecha
                + timedelta(hours=hora)
            )

            lluvia = (
                lluvias[dia_idx]
                if hora == 6
                else 0.0
            )

            riego = (
                dia_idx in eventos
                and hora == 6
            )

            for nodo_codigo, extra in [

                (
                    nombres["soil_1"],
                    0.0
                ),

                (
                    nombres["soil_2"],
                    0.7
                ),
            ]:

                h1 = (
                    generar_humedad(
                        dia_idx,
                        hora,
                        15,
                        riego,
                        lluvia,
                    )
                    + extra
                )

                h2 = (
                    generar_humedad(
                        dia_idx,
                        hora,
                        30,
                        riego,
                        lluvia,
                    )
                    + extra
                )

                h3 = (
                    generar_humedad(
                        dia_idx,
                        hora,
                        45,
                        riego,
                        lluvia,
                    )
                    + extra
                )

                temp_aire = (
                    13.5
                    + 5.0
                    * math.sin(
                        (hora - 7)
                        / 24
                        * 2
                        * math.pi
                    )
                )

                temp_aire += random.uniform(
                    -1.0,
                    1.0
                )

                temp_s1 = (
                    temp_aire
                    - 0.5
                    + random.uniform(
                        -0.4,
                        0.4
                    )
                )

                temp_s2 = (
                    temp_aire
                    - 0.2
                    + random.uniform(
                        -0.4,
                        0.4
                    )
                )

                hum_aire = (
                    78
                    - 22
                    * max(
                        0,
                        math.sin(
                            (hora - 6)
                            / 24
                            * math.pi
                        )
                    )
                )

                hum_aire += random.uniform(
                    -3,
                    3
                )

                db.add(
                    LecturaSuelo(

                        nodo_codigo=nodo_codigo,

                        predio_id=predio.id,

                        ts=ts,

                        ciclo=(
                            dia_idx * 4
                            + hora // 6
                        ),

                        hum_adc_1=
                            adc_desde_humedad(h1),

                        hum_adc_2=
                            adc_desde_humedad(h2),

                        hum_adc_3=
                            adc_desde_humedad(h3),

                        hum_pct_1=
                            round(h1, 2),

                        hum_pct_2=
                            round(h2, 2),

                        hum_pct_3=
                            round(h3, 2),

                        temp_suelo_1=
                            round(temp_s1, 2),

                        temp_suelo_2=
                            round(temp_s2, 2),

                        temp_aire=
                            round(temp_aire, 2),

                        hum_aire=
                            round(
                                max(
                                    45,
                                    min(
                                        98,
                                        hum_aire
                                    )
                                ),
                                2
                            ),

                        lluvia_mm=lluvia,

                        v_bateria=round(
                            3.95
                            - (
                                0.08
                                if dia_idx % 13 == 0
                                else 0
                            )
                            + random.uniform(
                                -0.03,
                                0.03
                            ),
                            2
                        ),

                        rssi=random.randint(
                            -58,
                            -45
                        ),

                        snr=round(
                            random.uniform(
                                7,
                                12
                            ),
                            1
                        ),
                    )
                )


# ============================================================
# LECTURAS DE CAUDAL
# ============================================================

def crear_lecturas_caudal(
    db,
    predio,
    inicio,
    eventos,
    indice,
):

    nombres = nombres_nodos(indice)

    acumulado = 0.0

    for dia_idx in range(
        DIAS_HISTORIA
    ):

        fecha = (
            inicio
            + timedelta(days=dia_idx)
        )

        evento = eventos.get(
            dia_idx
        )

        if evento:

            litros = (
                evento["m3"]
                * 1000
                * random.uniform(
                    0.97,
                    1.03
                )
            )

            q_lps = (
                litros
                / (
                    evento["minutos"]
                    * 60
                )
            )

        else:

            # Ruido mínimo del caudalímetro.
            litros = random.uniform(
                0.2,
                1.5
            )

            q_lps = random.uniform(
                0.01,
                0.03
            )

        acumulado += litros

        db.add(
            LecturaCaudal(

                nodo_codigo=
                    nombres["flow"],

                predio_id=predio.id,

                ts=(
                    fecha
                    + timedelta(hours=23)
                ),

                litros_periodo=
                    round(litros, 2),

                m3_acumulado=
                    round(
                        acumulado / 1000,
                        3
                    ),

                caudal_lps=
                    round(
                        q_lps,
                        4
                    ),

                v_bateria=
                    round(
                        3.92
                        + random.uniform(
                            -0.04,
                            0.04
                        ),
                        2
                    ),
            )
        )


# ============================================================
# EVENTOS DE RIEGO + RIEGO POR SECTOR
# ============================================================

def crear_eventos_riego(
    db,
    predio,
    sectores,
    inicio,
    eventos,
):

    for dia_idx, datos in eventos.items():

        inicio_evento = (
            inicio
            + timedelta(
                days=dia_idx,
                hours=6
            )
        )

        fin_evento = (
            inicio_evento
            + timedelta(
                minutes=datos["minutos"]
            )
        )

        evento = EventoRiego(

            predio_id=predio.id,

            inicio=inicio_evento,

            fin=fin_evento,

            volumen_m3=datos["m3"],

            origen="simulacion",
        )

        db.add(evento)

        db.flush()

        for sector in sectores:

            db.add(
                RiegoSector(

                    evento_riego_id=evento.id,

                    sector_id=sector.id,

                    minutos=
                        datos[
                            "minutos_por_sector"
                        ],

                    volumen_m3=
                        datos["por_sector"],

                    lamina_mm=round(
                        datos["por_sector"]
                        / (
                            sector.area_ha
                            * 10
                        ),
                        2
                    ),
                )
            )


# ============================================================
# NOTA DEL PRODUCTOR
# ============================================================

def crear_nota(
    db,
    predio,
    escenario,
):

    db.add(
        NotaProductor(

            predio_id=predio.id,

            tipo="observacion",

            texto=(
                "Simulación: "
                + escenario["descripcion"]
                + " Durante los últimos "
                  "30 días se redujo la duración "
                  "y frecuencia del riego."
            ),
        )
    )


# ============================================================
# SIMULAR UN PREDIO
# ============================================================

def simular_predio(
    db,
    escenario,
    indice,
):

    print()
    print(
        "-" * 65
    )

    print(
        f"Creando: {escenario['nombre']}"
    )

    # --------------------------------------------------------
    # Crear estructura
    # --------------------------------------------------------

    predio = crear_predio(
        db,
        escenario
    )

    sectores = crear_sectores(
        db,
        predio
    )

    crear_nodos(
        db,
        predio,
        indice
    )

    # --------------------------------------------------------
    # Fechas
    # --------------------------------------------------------

    ahora = (
        datetime.utcnow()
        .replace(
            minute=0,
            second=0,
            microsecond=0
        )
    )

    inicio = (
        ahora
        - timedelta(
            days=DIAS_HISTORIA
        )
    )

    # --------------------------------------------------------
    # Eventos y lluvia
    # --------------------------------------------------------

    eventos = (
        crear_eventos_simulados()
    )

    lluvias = crear_lluvias()

    # --------------------------------------------------------
    # Lecturas
    # --------------------------------------------------------

    crear_lecturas_suelo(
        db,
        predio,
        inicio,
        eventos,
        lluvias,
        indice,
    )

    crear_lecturas_caudal(
        db,
        predio,
        inicio,
        eventos,
        indice,
    )

    # --------------------------------------------------------
    # Riegos
    # --------------------------------------------------------

    crear_eventos_riego(
        db,
        predio,
        sectores,
        inicio,
        eventos,
    )

    # --------------------------------------------------------
    # Nota
    # --------------------------------------------------------

    crear_nota(
        db,
        predio,
        escenario,
    )

    db.flush()

    # --------------------------------------------------------
    # El nodo de caudal queda OFFLINE.
    # Los dos de suelo quedan ONLINE.
    # --------------------------------------------------------

    ahora = datetime.utcnow()

    nodos = (
        db.query(Nodo)
        .filter(
            Nodo.predio_id == predio.id
        )
        .all()
    )

    for nodo in nodos:

        if nodo.tipo == "caudal":

            nodo.ultima_conexion = (
                ahora
                - timedelta(minutes=70)
            )

        elif "01" in nodo.codigo:

            nodo.ultima_conexion = (
                ahora
                - timedelta(minutes=4)
            )

        else:

            nodo.ultima_conexion = (
                ahora
                - timedelta(minutes=12)
            )

    db.commit()

    # --------------------------------------------------------
    # Estadísticas
    # --------------------------------------------------------

    total_suelo = (
        db.query(LecturaSuelo)
        .filter(
            LecturaSuelo.predio_id
            == predio.id
        )
        .count()
    )

    total_caudal = (
        db.query(LecturaCaudal)
        .filter(
            LecturaCaudal.predio_id
            == predio.id
        )
        .count()
    )

    total_riegos = (
        db.query(EventoRiego)
        .filter(
            EventoRiego.predio_id
            == predio.id
        )
        .count()
    )

    print(
        f"Predio ID:       {predio.id}"
    )

    print(
        f"Fuente:          {escenario['fuente_hidrica']}"
    )

    print(
        f"Energía:         {escenario['tipo_energia']}"
    )

    print(
        f"Sectores:        {len(sectores)}"
    )

    print(
        f"Lecturas suelo:  {total_suelo}"
    )

    print(
        f"Lecturas caudal: {total_caudal}"
    )

    print(
        f"Eventos riego:   {total_riegos}"
    )

    print()

    print(
        "Nodos:"
    )

    for nodo in nodos:

        if nodo.tipo == "caudal":

            estado = (
                "OFFLINE "
                "(intencional, >45 min)"
            )

        else:

            estado = "ONLINE"

        print(
            f"  {nodo.codigo} -> {estado}"
        )

    return predio


# ============================================================
# SIMULACIÓN COMPLETA
# ============================================================

def simular():

    init_db()

    db = SessionLocal()

    try:

        print()
        print(
            "=" * 65
        )

        print(
            "HIDROSOPÓ - SIMULACIÓN INTEGRAL"
        )

        print(
            "=" * 65
        )

        print()
        print(
            "Borrando únicamente simulaciones anteriores..."
        )

        # ----------------------------------------------------
        # Borrar solamente nuestros 3 predios.
        # ----------------------------------------------------

        for escenario in ESCENARIOS:

            borrar_predio_simulacion(
                db,
                escenario["nombre"]
            )

        # ----------------------------------------------------
        # Crear los 3 escenarios.
        # ----------------------------------------------------

        predios = []

        for indice, escenario in enumerate(
            ESCENARIOS,
            1
        ):

            predio = simular_predio(
                db,
                escenario,
                indice,
            )

            predios.append(
                predio
            )

        # ----------------------------------------------------
        # Resumen final.
        # ----------------------------------------------------

        print()
        print(
            "=" * 65
        )

        print(
            "SIMULACIÓN COMPLETA CREADA CORRECTAMENTE"
        )

        print(
            "=" * 65
        )

        print()

        for predio, escenario in zip(
            predios,
            ESCENARIOS
        ):

            print(
                f"Predio ID {predio.id}: "
                f"{predio.nombre}"
            )

            print(
                f"  Fuente:   "
                f"{predio.fuente_hidrica}"
            )

            print(
                f"  Energía:  "
                f"{predio.tipo_energia}"
            )

            print(
                f"  Tarifa:   "
                f"${predio.tarifa_agua_m3:,.0f}/m3"
            )

            print()

        print(
            "ESCENARIOS DISPONIBLES:"
        )

        print(
            "  1. Acueducto -> ahorro en agua"
        )

        print(
            "  2. Lago      -> ahorro en energía"
        )

        print(
            "  3. Diesel    -> ahorro en combustible"
        )

        print()

        print(
            "Todos los predios tienen:"
        )

        print(
            "  - 4 sectores"
        )

        print(
            "  - 2 nodos de suelo ONLINE"
        )

        print(
            "  - 1 nodo de caudal OFFLINE"
        )

        print(
            "  - 60 días de historia"
        )

        print(
            "  - línea base de 30 días"
        )

        print(
            "  - período actual de 30 días"
        )

        print(
            "  - riego por sectores"
        )

        print(
            "  - lecturas de humedad"
        )

        print(
            "  - lecturas de caudal"
        )

        print()

        print(
            "La simulación está lista para probar:"
        )

        print(
            "  /ahorro"
        )

        print(
            "  /costo-agua"
        )

        print(
            "  /sectores"
        )

        print(
            "  /riegos"
        )

        print(
            "  /consumo"
        )

        print(
            "  /series"
        )

        print(
            "  /salud"
        )

        print(
            "  /recomendacion"
        )

        print(
            "  /conversar"
        )

        print(
            "=" * 65
        )

        print()

    except Exception:

        db.rollback()

        raise

    finally:

        db.close()


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    simular()
