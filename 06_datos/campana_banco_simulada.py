"""
Campaña de pruebas en banco SIMULADA — gemelo digital de HidroSopó.

Reproduce, con modelos físicos de cada componente, los cinco protocolos de
09_entregables/PROTOCOLO_PRUEBAS.md antes de tener el hardware en campo.
Sirve para (1) fijar los criterios de aceptación, (2) dimensionar qué se espera
medir y (3) dejar listas las planillas y las gráficas que luego se repiten con
datos reales.

>>> TODO RESULTADO DE ESTE SCRIPT ES SIMULADO. NO ES UNA MEDICIÓN DE CAMPO. <<<
Cada figura lleva la marca "SIMULACIÓN · gemelo digital" y cada registro la
columna fuente="simulacion".

Uso:
    python campana_banco_simulada.py            # semilla fija (reproducible)
    python campana_banco_simulada.py --semilla 7
Salida: 06_datos/campana_banco/  (resumen.json, planillas CSV y figuras PNG)
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

AQUI = Path(__file__).resolve().parent
SALIDA = AQUI / "campana_banco"

# Paleta del proyecto (misma del póster y la app)
TIERRA = "#2B2118"
AGUA = "#2F7FA6"
PASTO = "#6A8E3A"
ARCILLA = "#C0632F"
GRIS = "#8A8378"
FONDO = "#FBFAF6"
MARCA = "SIMULACIÓN · gemelo digital — no es medición de campo"


def estilo():
    plt.rcParams.update({
        "figure.facecolor": FONDO, "axes.facecolor": FONDO,
        "axes.edgecolor": "#CFC8BC", "axes.labelcolor": TIERRA,
        "xtick.color": "#5B5348", "ytick.color": "#5B5348",
        "axes.spines.top": False, "axes.spines.right": False,
        "font.family": "DejaVu Sans", "font.size": 10.5,
        "axes.titleweight": "bold", "axes.titlesize": 12.5,
        "axes.grid": True, "grid.color": "#E7E2D8", "grid.linewidth": 0.8,
    })


def marca(fig):
    fig.text(0.99, 0.01, MARCA, ha="right", va="bottom", fontsize=8,
             color=ARCILLA, alpha=0.9, style="italic")


def guardar(fig, nombre):
    marca(fig)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(SALIDA / nombre, dpi=200)
    plt.close(fig)


def csv_out(nombre, filas, campos):
    with open(SALIDA / nombre, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos + ["fuente"])
        w.writeheader()
        for r in filas:
            w.writerow({**r, "fuente": "simulacion"})


# ---------------------------------------------------------------- 1. Calibración
def prueba_calibracion(rng):
    """Sensor capacitivo v1.2: ADC ≈ a − b·θ + c·θ² (respuesta levemente no lineal),
    con ruido de lectura, variación entre unidades y error de pesada."""
    pasos_theta = np.array([0, 5, 10, 15, 20, 25, 30, 35, 40], float)  # θv real (%)
    sensores = {"S1 · 15 cm": (3150, 46, 0.22), "S2 · 30 cm": (3090, 43, 0.20),
                "S3 · 45 cm": (3210, 48, 0.25)}
    res, filas = {}, []
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    for (nombre, (a, b, c)), color in zip(sensores.items(), [AGUA, PASTO, ARCILLA]):
        a_u = a + rng.normal(0, 40); b_u = b * rng.normal(1, 0.04)
        theta_med = pasos_theta + rng.normal(0, 1.3, len(pasos_theta))  # error gravimétrico
        adc = a_u - b_u * pasos_theta + c * pasos_theta ** 2 + rng.normal(0, 55, len(pasos_theta))
        adc = np.round(adc)
        # Ajuste cuadrático ADC → θv (el que usa ia/calibracion.py)
        coef = np.polyfit(adc, theta_med, 2)
        pred = np.polyval(coef, adc)
        ss_res = np.sum((theta_med - pred) ** 2); ss_tot = np.sum((theta_med - theta_med.mean()) ** 2)
        r2 = 1 - ss_res / ss_tot
        rmse = math.sqrt(ss_res / len(adc))
        res[nombre] = {"r2": round(r2, 3), "rmse_pct_vol": round(rmse, 2),
                       "adc_seco": int(adc[0]), "adc_saturado": int(adc[-1]),
                       "coeficientes": [round(x, 8) for x in coef]}
        for t, aa in zip(theta_med, adc):
            filas.append({"sensor": nombre, "theta_v_pct": round(t, 2), "adc": int(aa)})
        xs = np.linspace(adc.min(), adc.max(), 100)
        ax.scatter(adc, theta_med, color=color, s=28, zorder=3)
        ax.plot(xs, np.polyval(coef, xs), color=color, lw=2,
                label=f"{nombre}   R² = {r2:.3f}".replace(".", ","))
    ax.set_xlabel("Lectura del sensor (ADC, 12 bits)")
    ax.set_ylabel("Humedad volumétrica θv (%)")
    ax.set_title("Prueba 1 · Curva de calibración gravimétrica (banco virtual)")
    ax.invert_xaxis(); ax.legend(frameon=False, loc="upper left")
    ax.axhline(0, color="#CFC8BC", lw=0.8)
    guardar(fig, "p1_calibracion.png")
    csv_out("p1_calibracion.csv", filas, ["sensor", "theta_v_pct", "adc"])
    r2s = [v["r2"] for v in res.values()]
    return {"criterio": "R² ≥ 0,90 por sensor", "sensores": res,
            "r2_min": min(r2s), "cumple": min(r2s) >= 0.90}


# ---------------------------------------------------------------- 2. WiFi
def prueba_wifi(rng, distancia_m=38.0, horas=72, graficar=True):
    """Pérdida log-distancia (n=2,7) + sombreado lognormal + desvanecimiento por
    lluvia/ganado. Cada envío fallido queda en el buffer (120 lecturas) y se
    reintenta en el siguiente ciclo."""
    n_env = horas * 4
    p0, n_exp = -40.0, 2.7          # RSSI a 1 m (dBm), exponente de pérdidas
    rssi_medio = p0 - 10 * n_exp * math.log10(distancia_m)
    sens = -90.0                    # umbral práctico de asociación + HTTPS
    t = np.arange(n_env) / 4.0
    lluvia = (np.sin(2 * np.pi * (t - 15) / 24) > 0.75).astype(float)   # tardes húmedas
    rssi = rssi_medio + rng.normal(0, 4.5, n_env) - 4 * lluvia
    ok_directo = rssi > sens
    buffer, entregadas, reenviadas, max_buffer = 0, 0, 0, 0
    serie_buffer = []
    for ok in ok_directo:
        if ok:
            entregadas += 1 + buffer; reenviadas += buffer; buffer = 0
        else:
            buffer = min(buffer + 1, 120)
        max_buffer = max(max_buffer, buffer); serie_buffer.append(buffer)
    pct_directo = 100 * ok_directo.mean()
    pct_final = 100 * entregadas / n_env
    resultado = {"criterio": "≥ 95 % de envíos entregados en 72 h", "distancia_m": distancia_m,
            "rssi_medio_dbm": round(rssi_medio, 1), "esperados": n_env,
            "entrega_directa_pct": round(pct_directo, 1), "entrega_final_pct": round(pct_final, 1),
            "reenviadas_desde_buffer": reenviadas, "max_buffer": max_buffer,
            "cumple": pct_final >= 95}
    if not graficar:
        return resultado

    fig, (a1, a2) = plt.subplots(2, 1, figsize=(7.2, 5.0), sharex=True,
                                 gridspec_kw={"height_ratios": [3, 1.3]})
    a1.scatter(t[ok_directo], rssi[ok_directo], s=7, color=AGUA, label="envío directo OK")
    a1.scatter(t[~ok_directo], rssi[~ok_directo], s=12, color=ARCILLA, marker="x", label="fallido → buffer")
    a1.axhline(sens, ls="--", color=GRIS, lw=1); a1.text(1, sens + 1, "umbral −90 dBm", color=GRIS, fontsize=8.5)
    a1.set_ylabel("RSSI (dBm)")
    a1.set_title(f"Prueba 2 · Enlace WiFi a {distancia_m:.0f} m del router, 72 h")
    a1.legend(frameon=False, loc="lower right", fontsize=9)
    a2.fill_between(t, serie_buffer, step="post", color=PASTO, alpha=0.6)
    a2.set_ylabel("buffer"); a2.set_xlabel("horas")
    guardar(fig, "p2_wifi.png")
    return resultado


def barrido_wifi(rng):
    """Entrega directa vs distancia: define la regla de instalación (≲ 50 m)."""
    ds = np.arange(10, 121, 10)
    vals = []
    for d in ds:
        r = [prueba_wifi(np.random.default_rng(int(d) * 10 + k), d, graficar=False)["entrega_directa_pct"] for k in range(5)]
        vals.append(np.mean(r))
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    ax.plot(ds, vals, "-o", color=AGUA, lw=2)
    ax.axhline(95, ls="--", color=ARCILLA, lw=1); ax.text(12, 96, "criterio 95 %", color=ARCILLA, fontsize=9)
    ax.axvspan(50, 120, color=ARCILLA, alpha=0.06)
    ax.text(85, 40, "zona de repetidor\no LoRa", ha="center", color=ARCILLA, fontsize=9)
    ax.set_xlabel("distancia nodo–router (m)"); ax.set_ylabel("envíos directos OK (%)")
    ax.set_ylim(0, 103); ax.set_title("Prueba 2b · Alcance WiFi esperado (sin buffer)")
    guardar(fig, "p2b_alcance_wifi.png")
    return {"distancias_m": ds.tolist(), "entrega_directa_pct": [round(v, 1) for v in vals]}


# ---------------------------------------------------------------- 3. Energía
def prueba_energia(rng, horas=240):
    """2 × 18650 en paralelo (≈ 5200 mAh útiles), panel desconectado, ciclo de
    15 min con WiFi (lectura + asociación + HTTPS ≈ 4,5 s a 120 mA).
    Se comparan dos placas: la ESP32 DevKit que ya se tiene (regulador AMS1117 y
    chip USB-serial siempre encendidos: ≈ 8 mA en reposo) y una placa de bajo
    consumo (≈ 0,065 mA en reposo). Las noches frías de Sopó suben el consumo."""
    cap_mah = 2 * 3000 * 0.87
    dt = 0.25
    t = np.arange(0, horas + dt, dt)
    placas = {"ESP32 DevKit (la que se tiene)": 8.0, "Placa de bajo consumo": 0.065}
    curvas, out = {}, {}
    for nombre, reposo in placas.items():
        q = cap_mah; v = []
        for tt in t:
            temp = 12 + 7 * math.sin(2 * math.pi * (tt - 9) / 24)
            factor_frio = 1.0 + max(0, 8 - temp) * 0.012
            rafaga = 120 * 4.5 / 3600 * 4 * rng.normal(1, 0.08)
            q -= (reposo + rafaga) * dt * factor_frio
            s = max(q / cap_mah, 0)
            ocv = 3.3 + 0.9 * s - 0.25 * (1 - s) ** 8
            v.append(ocv - 0.015 * rng.random())
        v = np.array(v); curvas[nombre] = v
        consumo_dia = (reposo + 120 * 4.5 / 3600 * 4) * 24 * 1.04
        out[nombre] = {"v_a_72h": round(float(v[int(72 / dt)]), 2),
                       "v_a_240h": round(float(v[-1]), 2),
                       "consumo_mah_dia": round(consumo_dia, 1),
                       "autonomia_dias_estimada": round(cap_mah * 0.8 / consumo_dia, 1)}
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for (nombre, v), color in zip(curvas.items(), [ARCILLA, PASTO]):
        ax.plot(t, v, color=color, lw=2, label=nombre)
    ax.axhline(3.5, ls="--", color=GRIS, lw=1); ax.text(2, 3.51, "mínimo 3,5 V", color=GRIS, fontsize=9)
    ax.axvline(72, ls=":", color=GRIS); ax.text(73, 4.21, "72 h", color=TIERRA, fontsize=9)
    ax.set_ylim(3.35, 4.25); ax.set_xlabel("horas sin panel solar"); ax.set_ylabel("voltaje de batería (V)")
    ax.set_title("Prueba 3 · Autonomía energética sin sol (2 × 18650, WiFi)")
    ax.legend(frameon=False, fontsize=9, loc="center right")
    guardar(fig, "p3_energia.png")
    dk = out["ESP32 DevKit (la que se tiene)"]
    return {"criterio": "≥ 72 h sin red y V ≥ 3,5 V", "placas": out,
            "v_a_72h": dk["v_a_72h"], "autonomia_dias_estimada": dk["autonomia_dias_estimada"],
            "hallazgo": "Con la DevKit el regulador y el chip USB dominan el consumo; la autonomía "
                        "baja de cientos de días a ≈ 3 semanas. Cumple el objetivo de ≥ 8 días, "
                        "pero conviene retirar el LED de encendido o migrar a una placa de bajo consumo.",
            "cumple": dk["v_a_72h"] >= 3.5}


# ---------------------------------------------------------------- 4. Caudalímetro
def prueba_caudal(rng):
    """Sensor de efecto Hall tipo YF (K de fábrica 450 pulsos/L). El K real
    depende del caudal y de la unidad; se simula una unidad con K ≈ 7 % menor
    (típico) y se aplica el procedimiento: 5 llenados → corregir K → 5 llenados."""
    k_fabrica = 450.0
    k_real_base = k_fabrica * rng.normal(0.93, 0.01)
    filas = []

    def llenados(k_firmware, etiqueta):
        errs = []
        for i in range(5):
            caudal = rng.uniform(9, 16)                     # L/min de la manguera
            k_real = k_real_base * (1 + 0.004 * (caudal - 12)) # leve no linealidad
            litros_reales = 20.0 + rng.normal(0, 0.08)        # error de aforo del balde
            pulsos = round(litros_reales * k_real)
            litros_nodo = pulsos / k_firmware
            e = (litros_nodo - litros_reales) / litros_reales * 100
            errs.append(e)
            filas.append({"serie": etiqueta, "llenado": i + 1, "litros_reales": round(litros_reales, 2),
                          "litros_nodo": round(litros_nodo, 2), "error_pct": round(e, 2),
                          "caudal_lpm": round(caudal, 1)})
        return errs

    e_antes = llenados(k_fabrica, "K de fábrica (450)")
    k_corr = k_fabrica * (1 + np.mean(e_antes) / 100)
    e_desp = llenados(k_corr, f"K corregido ({k_corr:.0f})")
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    x = np.arange(1, 6)
    ax.bar(x - 0.18, e_antes, 0.36, color=GRIS, label="K de fábrica = 450 pulsos/L")
    ax.bar(x + 0.18, e_desp, 0.36, color=AGUA, label=f"K corregido = {k_corr:.0f} pulsos/L")
    ax.axhspan(-5, 5, color=PASTO, alpha=0.08); ax.text(5.45, 4.2, "±5 %", color=PASTO, fontsize=9)
    ax.axhline(0, color=TIERRA, lw=0.8)
    ax.set_xticks(x); ax.set_xlabel("llenado de balde aforado (20 L)"); ax.set_ylabel("error (%)")
    ax.set_title("Prueba 4 · Caudalímetro vs. balde aforado")
    ax.set_ylim(-11, 6)
    ax.legend(frameon=False, fontsize=9, loc="lower center", ncol=2)
    guardar(fig, "p4_caudal.png")
    csv_out("p4_caudal.csv", filas, ["serie", "llenado", "litros_reales", "litros_nodo", "error_pct", "caudal_lpm"])
    emax = float(np.max(np.abs(e_desp)))
    return {"criterio": "error ≤ 5 % vs. balde aforado",
            "error_medio_fabrica_pct": round(float(np.mean(e_antes)), 2),
            "k_corregido": round(float(k_corr), 1),
            "error_max_corregido_pct": round(emax, 2),
            "error_medio_corregido_pct": round(float(np.mean(e_desp)), 2), "cumple": emax <= 5}


# ---------------------------------------------------------------- 5. IA y ahorro
def prueba_ia_y_ahorro():
    m24 = json.loads((AQUI.parent / "03_backend/modelos/humedad_24h_metricas.json").read_text())
    m48 = json.loads((AQUI.parent / "03_backend/modelos/humedad_48h_metricas.json").read_text())
    esc = json.loads((AQUI / "escenario_ahorro.json").read_text())
    seca = esc.get("montecarlo_temporada_seca", {})
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    hs = ["24 h", "48 h"]
    mod = [m24["mae_cv"], m48["mae_cv"]]; per = [m24["mae_linea_base_persistencia"], m48["mae_linea_base_persistencia"]]
    x = np.arange(2)
    ax.bar(x - 0.18, per, 0.36, color=GRIS, label="«mañana igual que hoy»")
    ax.bar(x + 0.18, mod, 0.36, color=PASTO, label="modelo HidroSopó (Gradient Boosting)")
    for i in range(2):
        ax.text(i + 0.18, mod[i] + 0.02, f"−{(1 - mod[i] / per[i]) * 100:.0f} %", ha="center", color=PASTO, fontweight="bold")
    ax.set_xticks(x, hs); ax.set_ylabel("error medio (MAE, % vol)")
    ax.set_title("Prueba 5 · Pronóstico de humedad, validación temporal")
    ax.legend(frameon=False, fontsize=9)
    guardar(fig, "p5_modelo_ia.png")
    return {
        "ia": {"mae_24h": m24["mae_cv"], "persistencia_24h": m24["mae_linea_base_persistencia"],
               "mejora_24h_pct": m24["mejora_vs_linea_base_pct"],
               "mae_48h": m48["mae_cv"], "persistencia_48h": m48["mae_linea_base_persistencia"],
               "mejora_48h_pct": m48["mejora_vs_linea_base_pct"]},
        "ahorro_temporada_seca": {"mediana_pct": seca.get("ahorro_pct_mediana"),
                                  "p10_pct": seca.get("ahorro_pct_p10"), "p90_pct": seca.get("ahorro_pct_p90"),
                                  "climas": seca.get("n")},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--semilla", type=int, default=2026)
    a = ap.parse_args()
    SALIDA.mkdir(exist_ok=True)
    estilo()
    rng = np.random.default_rng(a.semilla)
    resumen = {
        "AVISO": "RESULTADOS SIMULADOS (gemelo digital / banco virtual). No son mediciones de campo. "
                 "Se repetirán con el hardware real según 09_entregables/PROTOCOLO_PRUEBAS.md.",
        "semilla": a.semilla,
        "p1_calibracion": prueba_calibracion(rng),
        "p2_wifi": prueba_wifi(rng),
        "p2b_alcance_wifi": barrido_wifi(rng),
        "p3_energia": prueba_energia(rng),
        "p4_caudal": prueba_caudal(rng),
    }
    resumen.update(prueba_ia_y_ahorro())
    (SALIDA / "resumen.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o)), encoding="utf-8")
    print((SALIDA / "resumen.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
