"""
HidroSopó — Ajuste de curvas de calibración
============================================
Toma los pares (ADC, humedad volumétrica) del procedimiento gravimétrico
y ajusta el polinomio.

Uso:
    python -m ia.calibracion --sensor S1 --datos 3050,0 2740,11.5 2380,23.0 2010,34.5 1720,46.0
"""
import argparse
import json
from pathlib import Path
import numpy as np


def ajustar(adc: list[float], theta: list[float], grado: int = 2) -> dict:
    if len(adc) < grado + 1:
        raise ValueError(f"Se necesitan al menos {grado+1} puntos para grado {grado}")

    coefs = np.polyfit(adc, theta, grado)
    pred = np.polyval(coefs, adc)
    ss_res = float(np.sum((np.array(theta) - pred) ** 2))
    ss_tot = float(np.sum((np.array(theta) - np.mean(theta)) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    rmse = float(np.sqrt(np.mean((np.array(theta) - pred) ** 2)))

    if grado == 2:
        d = {"a": float(coefs[0]), "b": float(coefs[1]), "c": float(coefs[2])}
    else:
        d = {f"c{i}": float(c) for i, c in enumerate(coefs)}

    return {**d, "grado": grado, "r2": round(r2, 4), "rmse_pct": round(rmse, 3),
            "n_puntos": len(adc)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sensor", required=True, help="S1, S2 o S3")
    ap.add_argument("--datos", nargs="+", required=True,
                    help="Pares adc,theta_volumetrico  ej: 3050,0 2740,11.5")
    ap.add_argument("--grado", type=int, default=2)
    ap.add_argument("--profundidad", type=int, default=15)
    ap.add_argument("--salida", default="config_sensores.json")
    a = ap.parse_args()

    adc, theta = [], []
    for par in a.datos:
        x, y = par.split(",")
        adc.append(float(x)); theta.append(float(y))

    res = ajustar(adc, theta, a.grado)
    res["profundidad_cm"] = a.profundidad

    print(f"\nSensor {a.sensor} — polinomio de grado {a.grado}")
    print(f"  theta_v = {res.get('a'):.6e}*adc^2 + {res.get('b'):.6f}*adc + {res.get('c'):.4f}")
    print(f"  R²   = {res['r2']}")
    print(f"  RMSE = {res['rmse_pct']} % vol")
    if res["r2"] < 0.95:
        print("  ⚠️  R² bajo. Revisa las mediciones: probablemente la muestra no")
        print("      reposó lo suficiente o la compactación fue inconsistente.")

    p = Path(a.salida)
    cfg = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    cfg[a.sensor] = res
    p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n  Guardado en {p}")


if __name__ == "__main__":
    main()
