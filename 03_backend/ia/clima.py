"""
HidroSopó — Cliente de datos meteorológicos
============================================
Open-Meteo: gratis, sin API key, sin registro, uso no comercial.
Entrega directamente et0_fao_evapotranspiration, que es exactamente
lo que necesita el modelo FAO-56.

Documentación: https://open-meteo.com/en/docs
"""

from __future__ import annotations
import time
from typing import Optional

try:
    import requests
except ImportError:
    requests = None

_CACHE: dict = {}
_CACHE_TTL = 3600   # 1 hora: no tiene sentido pedir el pronóstico cada 15 min


def obtener_pronostico(lat: float, lon: float, dias: int = 7,
                       timeout: int = 12) -> Optional[dict]:
    """Trae pronóstico diario de Open-Meteo.

    Devuelve None si no hay conexión — el motor tiene respaldo
    con Hargreaves usando los sensores locales.
    """
    if requests is None:
        return None

    clave = f"{lat:.3f},{lon:.3f},{dias}"
    ahora = time.time()
    if clave in _CACHE and ahora - _CACHE[clave]["t"] < _CACHE_TTL:
        return _CACHE[clave]["data"]

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": ",".join([
            "temperature_2m_max",
            "temperature_2m_min",
            "temperature_2m_mean",
            "precipitation_sum",
            "precipitation_probability_max",
            "et0_fao_evapotranspiration",
            "shortwave_radiation_sum",
            "wind_speed_10m_max",
            "relative_humidity_2m_mean",
        ]),
        "timezone": "America/Bogota",
        "forecast_days": dias,
    }

    try:
        r = requests.get(url, params=params, timeout=timeout)
        r.raise_for_status()
        d = r.json()["daily"]
    except Exception as e:                      # noqa: BLE001
        print(f"[clima] Open-Meteo no disponible: {e}")
        return None

    resultado = {
        "fechas": d["time"],
        "temp_max": d["temperature_2m_max"],
        "temp_min": d["temperature_2m_min"],
        "temp_media": d["temperature_2m_mean"],
        "lluvia_diaria": [x or 0.0 for x in d["precipitation_sum"]],
        "prob_lluvia": d.get("precipitation_probability_max", [0] * dias),
        "et0_diaria": [x or 0.0 for x in d["et0_fao_evapotranspiration"]],
        "radiacion_mj": [(x or 0.0) for x in d.get("shortwave_radiation_sum", [0] * dias)],
        "viento_max_kmh": d.get("wind_speed_10m_max", [0] * dias),
        "hr_media": d.get("relative_humidity_2m_mean", [70] * dias),
    }

    _CACHE[clave] = {"t": ahora, "data": resultado}
    return resultado


def obtener_historico(lat: float, lon: float, fecha_inicio: str,
                      fecha_fin: str, timeout: int = 25) -> Optional[dict]:
    """Datos históricos (ERA5) para entrenar el modelo ML y para
    construir la línea base climática del informe.

    Formato de fecha: 'YYYY-MM-DD'. Hay ~5 días de latencia.
    """
    if requests is None:
        return None

    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat, "longitude": lon,
        "start_date": fecha_inicio, "end_date": fecha_fin,
        "daily": ("temperature_2m_max,temperature_2m_min,temperature_2m_mean,"
                  "precipitation_sum,et0_fao_evapotranspiration,"
                  "shortwave_radiation_sum,relative_humidity_2m_mean"),
        "timezone": "America/Bogota",
    }
    try:
        r = requests.get(url, params=params, timeout=timeout)
        r.raise_for_status()
        return r.json()["daily"]
    except Exception as e:                      # noqa: BLE001
        print(f"[clima] histórico no disponible: {e}")
        return None


if __name__ == "__main__":
    p = obtener_pronostico(4.9083, -73.9403)
    if p:
        print("Pronóstico Sopó, 7 días:")
        for i, f in enumerate(p["fechas"]):
            print(f"  {f}  ET0={p['et0_diaria'][i]:.2f} mm  "
                  f"lluvia={p['lluvia_diaria'][i]:.1f} mm  "
                  f"T={p['temp_min'][i]:.0f}-{p['temp_max'][i]:.0f}°C")
    else:
        print("Sin conexión (el motor usará Hargreaves con sensores locales)")
