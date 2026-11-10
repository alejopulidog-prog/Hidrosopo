"""
HidroSopó — Figuras del póster (SVG vectoriales, listas para imprenta)
=====================================================================
Lee los datos del proyecto y genera las tres gráficas del póster:

  fig_humedad.svg   Humedad por profundidad, 4 semanas, con lluvia, riegos y umbral
  fig_consumo.svg   Agua aplicada por semana: riego tradicional vs. HidroSopó
  fig_modelo.svg    Modelo ML: humedad predicha vs. real (datos que el modelo NO vio)

Fuente de datos (config.json → "fuente_datos"):
  "simulacion" → 06_datos/datos_sinteticos.csv + 06_datos/escenario_ahorro.json
  "campo"      → CSV exportado de la plataforma (mismas columnas) + tabla de consumo medido

Los textos quedan como texto (no como curvas), así el PDF pesa poco y se ve nítido.
"""
from __future__ import annotations
import json, sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
sys.path.insert(0, str(RAIZ / "03_backend"))

C = dict(tinta="#1E1A14", tierra="#54412D", agua="#2E7EA6", agua_clara="#8CC4DC",
         kikuyo="#6F9438", arcilla="#C4622D", humo="#6A6961", linea="#D9D9CF",
         p15="#2E7EA6", p30="#6F9438", p45="#8A6A3F")

plt.rcParams.update({
    "svg.fonttype": "none", "font.family": "sans-serif",
    "font.sans-serif": ["Noto Sans CJK SC", "Inter", "DejaVu Sans"],
    "font.size": 15, "axes.titlesize": 17, "axes.labelsize": 15,
    "axes.edgecolor": C["linea"], "axes.labelcolor": C["tinta"],
    "xtick.color": C["humo"], "ytick.color": C["humo"],
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": "#ECECE4", "grid.linewidth": 0.8,
    "legend.frameon": False, "figure.dpi": 100,
})


def _guardar(fig, nombre):
    fig.savefig(AQUI / nombre, format="svg", bbox_inches="tight", transparent=True)
    plt.close(fig)


def fig_humedad(csv: Path, desde="2026-10-01", dias=28, umbral=23.2):
    df = pd.read_csv(csv, parse_dates=["timestamp"])
    df = df[(df.timestamp >= desde) & (df.timestamp < pd.Timestamp(desde) + pd.Timedelta(days=dias))]
    fig, ax = plt.subplots(figsize=(10, 4.6))
    ax2 = ax.twinx()
    lluvia_d = df[df.profundidad_cm == 15].set_index("timestamp").lluvia_mm.resample("D").sum()
    ax2.bar(lluvia_d.index + pd.Timedelta(hours=12), lluvia_d.values, width=0.7,
            color=C["agua_clara"], alpha=0.55, label="Lluvia (mm/día)", zorder=0)
    ax2.set_ylim(0, max(40, lluvia_d.max() * 2.6)); ax2.set_ylabel("Lluvia (mm/día)", color=C["humo"])
    ax2.grid(False); ax2.spines["right"].set_visible(True); ax2.spines["top"].set_visible(False)
    for prof, col in [(15, C["p15"]), (30, C["p30"]), (45, C["p45"])]:
        s = df[df.profundidad_cm == prof].set_index("timestamp").humedad_pct.rolling("2h").mean()
        ax.plot(s.index, s.values, color=col, lw=2.4, label=f"{prof} cm", zorder=3)
    ax.axhline(umbral, color=C["arcilla"], ls=(0, (6, 4)), lw=2, zorder=2)
    ax.text(df.timestamp.min(), umbral - 0.35, " umbral de riego (FAO-56)",
            color=C["arcilla"], fontsize=13, va="top", ha="left",
            bbox=dict(facecolor="white", edgecolor="none", alpha=.85, pad=1.5))
    riegos = df[(df.profundidad_cm == 15) & (df.riego_mm > 0)].timestamp
    for t in riegos:
        ax.axvline(t, color=C["kikuyo"], lw=1.2, alpha=.5, zorder=1)
    if len(riegos):
        ax.plot([], [], color=C["kikuyo"], lw=1.2, alpha=.6, label="riego")
    ax.set_ylabel("Humedad volumétrica (% vol)")
    ax.set_ylim(15, 34)
    ax.set_zorder(ax2.get_zorder() + 1); ax.patch.set_visible(False)
    ax.xaxis.set_major_locator(matplotlib.dates.DayLocator(interval=4))
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%d %b"))
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, ncol=5, loc="upper center", bbox_to_anchor=(.5, 1.13), fontsize=13)
    _guardar(fig, "fig_humedad.svg")


def fig_consumo(escenario: dict, temporada="seca"):
    """Agua acumulada en el período: la brecha entre las dos curvas es el ahorro."""
    s = escenario[temporada] if temporada in escenario else escenario
    A = np.cumsum([0] + s["semanal_tradicional_m3"]); B = np.cumsum([0] + s["semanal_hidrosopo_m3"])
    x = np.arange(len(A))
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.fill_between(x, B, A, color=C["agua_clara"], alpha=.35, lw=0)
    ax.plot(x, A, color="#9C8F7A", lw=3, marker="o", ms=6, label="Riego tradicional (por calendario)")
    ax.plot(x, B, color=C["agua"], lw=3, marker="o", ms=6, label="Con HidroSopó (FAO-56 + pronóstico)")
    ax.annotate(f"ahorro\n{A[-1]-B[-1]:,.0f} m³".replace(",", "."), xy=(x[-1], (A[-1] + B[-1]) / 2),
                xytext=(x[-1] - 2.3, (A[-1] + B[-1]) / 2), fontsize=15, color=C["agua"],
                fontweight="bold", va="center")
    ax.set_xlabel("Semana"); ax.set_ylabel("Agua aplicada acumulada (m³/ha)")
    ax.set_xticks(x); ax.set_xlim(0, x[-1] + .3)
    ax.legend(loc="upper left", fontsize=13)
    _guardar(fig, "fig_consumo.svg")


def fig_modelo(csv: Path, horizonte=24):
    """Entrena con el 80 % inicial de la serie y evalúa en el 20 % final
    (datos futuros que el modelo nunca vio). Profundidad 15 cm."""
    from ia import modelo_ml as M
    from sklearn.ensemble import GradientBoostingRegressor
    df = pd.read_csv(csv)
    X = M.construir_features(df); y = M.construir_objetivo(df, horizonte)
    d = X.reset_index().join(y.reset_index(drop=True).rename("obj")).dropna()
    d = d.sort_values("timestamp")
    corte = d.timestamp.iloc[int(len(d) * .8)]
    tr, te = d[d.timestamp < corte], d[d.timestamp >= corte]
    m = GradientBoostingRegressor(n_estimators=300, learning_rate=.05, max_depth=3,
                                  min_samples_leaf=50, subsample=.8, loss="huber", random_state=42)
    m.fit(tr[M.FEATURES].values, (tr.obj - tr.humedad_actual).values)
    te = te[te.profundidad_cm == 15].iloc[::4]
    pred = te.humedad_actual.values + m.predict(te[M.FEATURES].values)
    real = te.obj.values; pers = te.humedad_actual.values
    mae_m = float(np.mean(np.abs(pred - real))); mae_p = float(np.mean(np.abs(pers - real)))
    fig, ax = plt.subplots(figsize=(5.6, 5.2))
    lo, hi = min(real.min(), pred.min()) - .5, max(real.max(), pred.max()) + .5
    ax.plot([lo, hi], [lo, hi], color=C["humo"], ls="--", lw=1.4, label="predicción perfecta")
    ax.scatter(real, pred, s=16, color=C["agua"], alpha=.45, edgecolor="none", label="modelo")
    ax.set_xlim(lo, hi); ax.set_ylim(lo, hi)
    ax.set_xlabel(f"Humedad real a {horizonte} h (% vol)"); ax.set_ylabel("Humedad predicha (% vol)")
    ax.legend(loc="upper left", fontsize=12)
    _guardar(fig, "fig_modelo.svg")
    return {"mae_modelo": round(mae_m, 2), "mae_persistencia": round(mae_p, 2),
            "mejora_pct": round(100 * (1 - mae_m / mae_p), 1), "n_prueba": int(len(te)),
            "corte": str(corte)[:10]}


def generar(cfg: dict) -> dict:
    datos = RAIZ / cfg.get("csv_sensores", "06_datos/datos_sinteticos.csv")
    esc = json.loads((RAIZ / cfg.get("json_consumo", "06_datos/escenario_ahorro.json")).read_text())
    fig_humedad(datos, desde=cfg.get("ventana_humedad_desde", "2026-10-01"))
    fig_consumo(esc, cfg.get("temporada_consumo", "seca"))
    holdout = fig_modelo(datos)
    return {"holdout": holdout, "escenario": esc}


if __name__ == "__main__":
    cfg = json.loads((AQUI / "config.json").read_text())
    print(json.dumps(generar(cfg)["holdout"], indent=2))
