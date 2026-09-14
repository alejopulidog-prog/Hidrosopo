"""
HidroSopó — Modelo de Machine Learning
=======================================
Predice la humedad del suelo a 24 y 48 horas usando los datos
del PROPIO predio piloto.

Esto es lo que justifica la palabra "Inteligencia Artificial" en el
proyecto ante el jurado: un modelo entrenado con datos, validado con
métricas, no una regla if-else.

Algoritmo: Gradient Boosting Regressor (scikit-learn).
Por qué: funciona bien con pocos datos (desde ~500 registros), captura
relaciones no lineales, no requiere escalado de features y da
importancia de variables — que es material excelente para el póster.

Costo: $0. scikit-learn es open source, corre en CPU.
"""

from __future__ import annotations
import os
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.metrics import mean_absolute_error, r2_score
import joblib

DIR_MODELOS = Path(os.getenv("DIR_MODELOS", "modelos"))
DIR_MODELOS.mkdir(exist_ok=True, parents=True)

FEATURES = [
    "humedad_actual",
    "humedad_lag_6h",
    "humedad_lag_24h",
    "delta_humedad_6h",
    "temp_aire",
    "temp_suelo",
    "hr_aire",
    "et0_acumulada_24h",
    "lluvia_acumulada_24h",
    "lluvia_pronosticada_24h",
    "lluvia_pronosticada_48h",
    "hora_sin",
    "hora_cos",
    "profundidad_cm",
]

# Nota: se quitaron dia_año_sin/cos a propósito. Con 4 meses de datos el
# modelo no puede aprender estacionalidad anual — solo memoriza la tendencia
# del período de entrenamiento y extrapola pésimo en validación temporal.
# Reincorpóralas solo si algún día tienes 2+ años de serie.


# ============================================================
#  Preparación de features
# ============================================================

def construir_features(df: pd.DataFrame) -> pd.DataFrame:
    """Genera las variables predictoras a partir de la serie cruda.

    Espera un DataFrame con columnas:
        timestamp, humedad_pct, temp_aire, temp_suelo, hr_aire,
        lluvia_mm, et0_mm, profundidad_cm

    Cada profundidad es una serie temporal independiente: se procesan
    por separado y se concatenan. Si se mezclan, los rezagos quedan mal
    (el lag de 6h del sensor de 15 cm tomaría el valor del de 45 cm).
    """
    if "profundidad_cm" in df.columns and df["profundidad_cm"].nunique() > 1:
        partes = [_features_una_serie(g) for _, g in df.groupby("profundidad_cm")]
        return pd.concat(partes).sort_index()
    return _features_una_serie(df)


def _features_una_serie(df: pd.DataFrame) -> pd.DataFrame:
    """Features de una sola profundidad (índice temporal sin duplicados)."""
    df = df.sort_values("timestamp").copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.drop_duplicates(subset="timestamp").set_index("timestamp")

    out = pd.DataFrame(index=df.index)
    out["humedad_actual"] = df["humedad_pct"]

    # Rezagos: el estado pasado predice el futuro
    tol = pd.Timedelta("20min")   # sin tolerancia, los bordes se rellenan con
                                  # el valor más cercano aunque esté a días de distancia
    out["humedad_lag_6h"]  = df["humedad_pct"].shift(freq="6h").reindex(
        df.index, method="nearest", tolerance=tol)
    out["humedad_lag_24h"] = df["humedad_pct"].shift(freq="24h").reindex(
        df.index, method="nearest", tolerance=tol)
    out["delta_humedad_6h"] = out["humedad_actual"] - out["humedad_lag_6h"]

    out["temp_aire"]  = df["temp_aire"]
    out["temp_suelo"] = df["temp_suelo"]
    out["hr_aire"]    = df["hr_aire"]

    # Acumulados móviles de 24 h
    out["et0_acumulada_24h"]    = df["et0_mm"].rolling("24h").sum()
    out["lluvia_acumulada_24h"] = df["lluvia_mm"].rolling("24h").sum()

    # Pronóstico (se rellena desde Open-Meteo al ingerir; 0 si no hay)
    out["lluvia_pronosticada_24h"] = df.get("lluvia_pron_24h", pd.Series(0.0, index=df.index))
    out["lluvia_pronosticada_48h"] = df.get("lluvia_pron_48h", pd.Series(0.0, index=df.index))

    # Codificación cíclica del tiempo: la hora 23 y la hora 0 son vecinas.
    # Sin esto el modelo cree que están a 23 unidades de distancia.
    hora = out.index.hour + out.index.minute / 60.0
    out["hora_sin"] = np.sin(2 * np.pi * hora / 24)
    out["hora_cos"] = np.cos(2 * np.pi * hora / 24)

    out["profundidad_cm"] = df["profundidad_cm"]

    return out


def construir_objetivo(df: pd.DataFrame, horizonte_horas: int) -> pd.Series:
    """La variable a predecir: la humedad H horas en el futuro.

    Igual que las features, se calcula por profundidad para no mezclar series.
    """
    def _una(g):
        g = g.sort_values("timestamp").copy()
        g["timestamp"] = pd.to_datetime(g["timestamp"])
        s = g.drop_duplicates(subset="timestamp").set_index("timestamp")["humedad_pct"]
        # tolerance evita que el final de la serie (que no tiene futuro real)
        # se rellene con el último valor disponible: queda NaN y se descarta.
        return s.shift(freq=f"-{horizonte_horas}h").reindex(
            s.index, method="nearest", tolerance=pd.Timedelta("20min"))

    if "profundidad_cm" in df.columns and df["profundidad_cm"].nunique() > 1:
        return pd.concat([_una(g) for _, g in df.groupby("profundidad_cm")]).sort_index()
    return _una(df)


# ============================================================
#  Entrenamiento
# ============================================================

def entrenar(df_crudo: pd.DataFrame, horizonte_horas: int = 24,
             nombre: str = "humedad", verbose: bool = True) -> dict:
    """Entrena el modelo y guarda el artefacto en disco.

    Con menos de 500 registros el modelo no es confiable. A 15 min
    de intervalo, 500 registros son ~5 días. Con 30 días (2880
    registros) ya tienes un modelo sólido.
    """
    X = construir_features(df_crudo)
    y = construir_objetivo(df_crudo, horizonte_horas)

    # Índice con duplicados (una fila por profundidad y timestamp):
    # se une posicionalmente, ya que X e y salen del mismo orden de groupby.
    datos = X.reset_index(drop=True).join(
        y.reset_index(drop=True).rename("objetivo")).dropna()
    if len(datos) < 200:
        raise ValueError(
            f"Solo hay {len(datos)} registros utilizables. Se necesitan al menos 200 "
            "(≈2 días a 15 min). Deja el nodo corriendo más tiempo."
        )

    Xm = datos[FEATURES].values
    # Se modela el CAMBIO de humedad, no el nivel absoluto.
    # Predecir el nivel hace que el modelo tenga que "reaprender" en cada
    # predicción dónde está el suelo; predecir el cambio lo deja concentrarse
    # en lo único que no es trivial: cuánto se va a mover.
    humedad_ahora = datos["humedad_actual"].values
    ym = datos["objetivo"].values - humedad_ahora

    # Hiperparámetros deliberadamente conservadores. Con series cortas
    # (4 meses) y objetivo en deltas, los árboles profundos memorizan ruido:
    # en pruebas, max_depth=4 quedó 9.6% POR DEBAJO de la persistencia,
    # mientras que max_depth=2 con hojas grandes la supera.
    # loss="huber" reduce el peso de los saltos por lluvias fuertes.
    modelo = GradientBoostingRegressor(
        n_estimators=250,
        learning_rate=0.03,
        max_depth=2,
        min_samples_leaf=80,
        subsample=0.70,
        loss="huber",
        random_state=42,
    )

    # Validación cruzada respetando el orden temporal.
    # Un KFold normal aquí haría trampa: entrenaría con el futuro
    # para predecir el pasado. TimeSeriesSplit no.
    cv = TimeSeriesSplit(n_splits=min(5, max(2, len(datos) // 100)))
    scores_mae = -cross_val_score(modelo, Xm, ym, cv=cv,
                                  scoring="neg_mean_absolute_error")
    scores_r2 = cross_val_score(modelo, Xm, ym, cv=cv, scoring="r2")

    # --- Línea base de persistencia ---
    # "la humedad dentro de 24 h será igual a la de ahora".
    # Si el modelo no le gana a esto, el modelo no sirve. Reportarlo
    # es lo que separa un análisis serio de uno decorativo.
    # Con el objetivo en deltas, la persistencia es simplemente predecir 0.
    mae_persistencia = float(mean_absolute_error(ym, np.zeros_like(ym)))

    # Entrenamiento final con todo el histórico
    modelo.fit(Xm, ym)

    y_pred = modelo.predict(Xm)
    # Métricas también en el espacio del nivel absoluto, que es lo que
    # el productor y el jurado entienden.
    nivel_real = humedad_ahora + ym
    nivel_pred = humedad_ahora + y_pred
    metricas = {
        "n_registros": int(len(datos)),
        "horizonte_horas": horizonte_horas,
        "mae_cv": round(float(scores_mae.mean()), 3),
        "mae_cv_std": round(float(scores_mae.std()), 3),
        "r2_cv": round(float(scores_r2.mean()), 3),
        "objetivo": "delta_humedad",
        "mae_entrenamiento": round(float(mean_absolute_error(ym, y_pred)), 3),
        "mae_nivel_absoluto": round(float(mean_absolute_error(nivel_real, nivel_pred)), 3),
        "r2_nivel_absoluto": round(float(r2_score(nivel_real, nivel_pred)), 3),
        "mae_linea_base_persistencia": round(mae_persistencia, 3),
        "mejora_vs_linea_base_pct": round(
            100 * (mae_persistencia - float(scores_mae.mean())) / mae_persistencia, 1
        ) if mae_persistencia > 0 else 0.0,
        "r2_entrenamiento": round(float(r2_score(ym, y_pred)), 3),
        "importancia_variables": {
            f: round(float(imp), 4)
            for f, imp in sorted(zip(FEATURES, modelo.feature_importances_),
                                 key=lambda x: -x[1])
        },
        "entrenado_en": datetime.now().isoformat(timespec="seconds"),
        "rango_datos": [str(X.index.min()), str(X.index.max())],
    }

    ruta = DIR_MODELOS / f"{nombre}_{horizonte_horas}h.joblib"
    joblib.dump({"modelo": modelo, "features": FEATURES, "metricas": metricas}, ruta)
    (DIR_MODELOS / f"{nombre}_{horizonte_horas}h_metricas.json").write_text(
        json.dumps(metricas, indent=2, ensure_ascii=False))

    if verbose:
        print(f"\n{'='*56}")
        print(f" Modelo: humedad a {horizonte_horas} h")
        print(f"{'='*56}")
        print(f" Registros usados : {metricas['n_registros']}")
        print(f" MAE (val. cruzada): {metricas['mae_cv']} ± {metricas['mae_cv_std']} % vol")
        print(f" R²  (val. cruzada): {metricas['r2_cv']}")
        print(f" MAE línea base    : {metricas['mae_linea_base_persistencia']} % vol "
              f"(persistencia)")
        print(f" Mejora vs. base   : {metricas['mejora_vs_linea_base_pct']}%")
        print(f"\n Variables más importantes:")
        for f, i in list(metricas["importancia_variables"].items())[:6]:
            barra = "█" * int(i * 50)
            print(f"   {f:<26} {i:.3f} {barra}")
        print(f"\n Guardado en: {ruta}")

        if metricas["mejora_vs_linea_base_pct"] < 5:
            print("\n ⚠️  El modelo apenas le gana a la persistencia. Con más días")
            print("     de datos debería mejorar. No lo presentes como resultado final.")
        if metricas["r2_cv"] < 0.5:
            print("\n ℹ️  R² bajo. En series muy estables el R² castiga mucho aunque")
            print("     el MAE sea bueno: reporta ambos, y sobre todo la mejora")
            print("     contra la línea base, que es la comparación que importa.")

    return metricas


def predecir(humedad_actual: float, contexto: dict,
             nombre: str = "humedad", horizonte_horas: int = 24) -> dict | None:
    """Predice la humedad futura. Devuelve None si el modelo no existe todavía."""
    ruta = DIR_MODELOS / f"{nombre}_{horizonte_horas}h.joblib"
    if not ruta.exists():
        return None

    art = joblib.load(ruta)
    modelo, features, metricas = art["modelo"], art["features"], art["metricas"]

    fila = np.array([[contexto.get(f, 0.0) for f in features]])
    fila[0, features.index("humedad_actual")] = humedad_actual

    delta = float(modelo.predict(fila)[0])
    pred = humedad_actual + delta      # el modelo devuelve el cambio
    mae = metricas["mae_cv"]

    return {
        f"humedad_{horizonte_horas}h_pct": round(pred, 2),
        "cambio_previsto_pct": round(delta, 2),
        "intervalo_aprox": [round(pred - 1.96 * mae, 2), round(pred + 1.96 * mae, 2)],
        "mae": mae,
        "r2": metricas["r2_cv"],
        "confianza": "alta" if metricas["r2_cv"] > 0.75
                     else "media" if metricas["r2_cv"] > 0.5 else "baja",
        "n_registros_entrenamiento": metricas["n_registros"],
    }


def resumen_modelos() -> list[dict]:
    """Para mostrar en el dashboard y en el póster."""
    out = []
    for p in DIR_MODELOS.glob("*_metricas.json"):
        out.append({"archivo": p.stem, **json.loads(p.read_text())})
    return out


# ============================================================
#  CLI
# ============================================================

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Entrena el modelo de humedad de HidroSopó")
    ap.add_argument("--csv", required=True,
                    help="CSV con columnas: timestamp, humedad_pct, temp_aire, "
                         "temp_suelo, hr_aire, lluvia_mm, et0_mm, profundidad_cm")
    ap.add_argument("--horizontes", default="24,48",
                    help="Horizontes en horas, separados por coma")
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    print(f"Cargados {len(df)} registros de {args.csv}")

    for h in [int(x) for x in args.horizontes.split(",")]:
        entrenar(df, horizonte_horas=h)
