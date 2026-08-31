import csv
from datetime import datetime
from db import init_db, SessionLocal, Predio, LecturaSuelo


CSV_PATH = "../06_datos/datos_sinteticos.csv"


def cargar_datos():
    # Crear las tablas si todavía no existen
    init_db()

    db = SessionLocal()

    try:
        # ---------------------------------------------------------
        # 1. Crear el predio de prueba
        # ---------------------------------------------------------
        predio = db.query(Predio).filter(Predio.id == 1).first()

        if not predio:
            predio = Predio(
                id=1,
                nombre="Predio de prueba HidroSopó",
                propietario="Productor de prueba",
                vereda="Sopó",
                latitud=4.9083,
                longitud=-73.9403,
                altitud_m=2587,
                area_predio_ha=1.0,
                area_regada_ha=1.0,
                area_por_turno_ha=1.0,
                perfil_cultivo="kikuyo_pastoreo",
                tipo_suelo="sabana_bogota",
                sistema_riego="aspersion",
                caudal_disponible_lps=1.5,
                capacidad_campo_pct=32.0,
                punto_marchitez_pct=16.0,
            )

            db.add(predio)
            db.commit()
            db.refresh(predio)

            print(f"Predio creado correctamente con ID: {predio.id}")

        else:
            print(f"El predio ID 1 ya existe: {predio.nombre}")

        # ---------------------------------------------------------
        # 2. Leer datos sintéticos
        # ---------------------------------------------------------
        with open(CSV_PATH, newline="", encoding="utf-8") as f:
            filas = list(csv.DictReader(f))

        print(f"Leídas {len(filas)} filas desde {CSV_PATH}")

        # ---------------------------------------------------------
        # 3. Agrupar las tres profundidades por timestamp
        # ---------------------------------------------------------
        grupos = {}

        for fila in filas:
            timestamp = fila["timestamp"]
            profundidad = int(fila["profundidad_cm"])

            if timestamp not in grupos:
                grupos[timestamp] = {}

            grupos[timestamp][profundidad] = fila

        # ---------------------------------------------------------
        # 4. Crear lecturas de suelo
        # ---------------------------------------------------------
        lecturas = []

        for timestamp, datos in sorted(grupos.items()):

            # Necesitamos las tres profundidades
            if not all(p in datos for p in (15, 30, 45)):
                continue

            f15 = datos[15]
            f30 = datos[30]
            f45 = datos[45]

            ts = datetime.fromisoformat(timestamp)

            lectura = LecturaSuelo(
                nodo_codigo="NODO_PRUEBA",
                predio_id=1,
                ts=ts,
                ciclo=0,

                hum_pct_1=float(f15["humedad_pct"]),
                hum_pct_2=float(f30["humedad_pct"]),
                hum_pct_3=float(f45["humedad_pct"]),

                temp_suelo_1=float(f15["temp_suelo"]),
                temp_suelo_2=float(f30["temp_suelo"]),

                temp_aire=float(f15["temp_aire"]),
                hum_aire=float(f15["hr_aire"]),

                lluvia_mm=float(f15["lluvia_mm"]),

                v_bateria=4.0,
                rssi=-50,
                snr=10.0,
            )

            lecturas.append(lectura)

        # ---------------------------------------------------------
        # 5. Evitar duplicados si ejecutamos el script nuevamente
        # ---------------------------------------------------------
        existentes = db.query(LecturaSuelo).filter(
            LecturaSuelo.predio_id == 1
        ).count()

        if existentes > 0:
            print(
                f"El predio ya tiene {existentes} lecturas. "
                "No se agregarán duplicados."
            )
        else:
            db.add_all(lecturas)
            db.commit()

            print(f"Lecturas de suelo creadas: {len(lecturas)}")

        print()
        print("==============================================")
        print("DATOS DE PRUEBA CARGADOS CORRECTAMENTE")
        print("==============================================")
        print(f"Predio ID: 1")
        print(f"Filas CSV: {len(filas)}")
        print(f"Lecturas agrupadas: {len(lecturas)}")
        print()
        print("Ahora prueba:")
        print("curl http://localhost:8000/api/v1/predios")
        print()
        print(
            "curl "
            "http://localhost:8000/api/v1/predios/1/recomendacion"
        )

    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        raise

    finally:
        db.close()


if __name__ == "__main__":
    cargar_datos()
