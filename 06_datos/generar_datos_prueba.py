"""
HidroSopó — Generador de datos sintéticos
==========================================
Simula 60 días de operación de un nodo en una finca de Sopó, para:
  - Probar el backend sin esperar a tener el hardware
  - Entrenar el modelo ML y ver que funciona
  - Preparar las gráficas del póster antes de la instalación

El modelo de suelo usa un balance hídrico simple con lluvia estocástica
calibrada al régimen bimodal de la Sabana de Bogotá.

Uso:  python generar_datos_prueba.py --dias 60 --salida datos_sinteticos.csv
"""
import argparse
import math
import random
from datetime import datetime, timedelta
import csv

random.seed(42)


def generar(dias=60, intervalo_min=15, inicio=None,
            cc=32.0, pmp=16.0, prob_lluvia_dia=0.35):
    inicio = inicio or (datetime(2026, 9, 1))
    n = int(dias * 24 * 60 / intervalo_min)
    paso_h = intervalo_min / 60.0

    # --- Lluvia de todo el período, decidida por adelantado ---
    # Así podemos construir un "pronóstico" imperfecto pero informativo,
    # que es exactamente lo que aporta Open-Meteo en la operación real.
    n_dias = dias + 3
    lluvia_por_dia = []
    for d in range(n_dias):
        dj_d = (inicio + timedelta(days=d)).timetuple().tm_yday
        factor = 1.0 + 0.6 * math.sin(4 * math.pi * (dj_d - 60) / 365)
        lluvia_por_dia.append(
            random.expovariate(1 / 9.0) if random.random() < prob_lluvia_dia * factor else 0.0)

    def pronostico(d, horizonte_dias):
        """Pronóstico con error realista: acierta la tendencia, falla el monto."""
        total = sum(lluvia_por_dia[d + 1: d + 1 + horizonte_dias])
        return max(0.0, total * random.uniform(0.55, 1.45) + random.gauss(0, 1.2))

    filas = []
    # Estado inicial: suelo cerca de capacidad de campo
    h = [30.0, 29.0, 28.0]      # 15, 30, 45 cm
    lluvia_hoy = 0.0
    dia_actual = -1
    idx_dia = 0
    pron_24 = pron_48 = 0.0

    for i in range(n):
        ts = inicio + timedelta(minutes=i * intervalo_min)
        hora = ts.hour + ts.minute / 60.0
        dj = ts.timetuple().tm_yday

        # --- Temperatura: ciclo diario típico de la Sabana (6-20 °C) ---
        t_base = 13.0 + 1.5 * math.sin(2 * math.pi * (dj - 80) / 365)
        amplitud = 7.0
        temp_aire = t_base + amplitud * math.sin(2 * math.pi * (hora - 9) / 24) \
                    + random.gauss(0, 0.8)
        # El suelo amortigua y desfasa la onda térmica
        temp_suelo = t_base + 2.5 * math.sin(2 * math.pi * (hora - 14) / 24) + random.gauss(0, 0.3)

        # --- Humedad relativa: inversa a la temperatura ---
        hr = max(35.0, min(98.0, 95.0 - 2.2 * (temp_aire - 8) + random.gauss(0, 4)))

        # --- Lluvia: se decide una vez al día, cae en la tarde ---
        if ts.day != dia_actual:
            dia_actual = ts.day
            idx_dia = (ts.date() - inicio.date()).days
            lluvia_hoy = lluvia_por_dia[min(idx_dia, n_dias - 1)]
            pron_24 = pronostico(idx_dia, 1)
            pron_48 = pronostico(idx_dia, 2)
        lluvia = 0.0
        if lluvia_hoy > 0 and 14 <= hora < 18:
            lluvia = lluvia_hoy / (4 / paso_h) * random.uniform(0.5, 1.5)

        # --- ET0 (solo de día) ---
        et0_dia = 3.2 + 0.8 * math.sin(2 * math.pi * (dj - 30) / 365)
        et0 = et0_dia * paso_h / 12 * max(0, math.sin(math.pi * (hora - 6) / 12)) if 6 <= hora <= 18 else 0.0

        # --- Riego: el productor riega cuando el sensor superficial baja de 21% ---
        riego = 0.0
        if h[0] < 21.0 and 6 <= hora < 8 and random.random() < 0.5:
            riego = random.uniform(8, 16)

        # --- Balance por capa ---
        entrada = lluvia * 0.85 + riego
        # capa 1 (0-20 cm): recibe todo, pierde por ET
        h[0] += entrada / 2.0 - et0 * 1.15 / 2.0
        exceso1 = max(0.0, h[0] - cc); h[0] -= exceso1
        # capa 2 (20-40 cm): recibe la percolación de la 1
        h[1] += exceso1 * 0.9 - et0 * 0.5 / 2.0
        exceso2 = max(0.0, h[1] - cc); h[1] -= exceso2
        # capa 3 (40-60 cm): recibe de la 2, pierde poco
        h[2] += exceso2 * 0.85 - et0 * 0.15 / 2.0
        h[2] = min(cc, h[2])

        h = [max(pmp - 2, min(cc + 1, x)) for x in h]

        for prof, hum in zip([15, 30, 45], h):
            filas.append({
                "timestamp": ts.isoformat(),
                "humedad_pct": round(hum + random.gauss(0, 0.25), 2),
                "temp_aire": round(temp_aire, 2),
                "temp_suelo": round(temp_suelo, 2),
                "hr_aire": round(hr, 1),
                "lluvia_mm": round(lluvia, 3),
                "et0_mm": round(et0, 4),
                "profundidad_cm": prof,
                "riego_mm": round(riego, 2),
                "lluvia_pron_24h": round(pron_24, 2),
                "lluvia_pron_48h": round(pron_48, 2),
            })

    return filas


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dias", type=int, default=60)
    ap.add_argument("--salida", default="datos_sinteticos.csv")
    a = ap.parse_args()

    filas = generar(dias=a.dias)
    with open(a.salida, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
        w.writeheader(); w.writerows(filas)

    print(f"Generados {len(filas)} registros ({a.dias} días x 3 profundidades)")
    print(f"Guardado en {a.salida}")
    print("\nSiguiente paso:")
    print(f"  cd ../03_backend && python -m ia.modelo_ml --csv ../06_datos/{a.salida}")
