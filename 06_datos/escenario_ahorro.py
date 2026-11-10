"""
HidroSopó — Escenario de ahorro (gemelo digital)
=================================================
Compara, con el MISMO clima simulado, dos formas de regar un potrero de
kikuyo de 1 ha en Sopó durante 90 días:

  A) Riego tradicional: "por calendario", 12 mm cada 3 días salvo que
     hayan caído más de 3 mm en los tres días anteriores (lo que contaron los productores
     en el diagnóstico típico de la Sabana).
  B) Riego con HidroSopó: balance hídrico FAO-56; se riega solo cuando el
     agotamiento supera el agua fácilmente aprovechable (RAW) y el
     pronóstico de 24 h trae menos de 5 mm; se repone lo que falta.

IMPORTANTE: es una SIMULACIÓN. Sirve para dimensionar el ahorro esperado y
preparar el análisis. El ahorro que se reporta como resultado del proyecto
es el MEDIDO con el caudalímetro (ver 09_entregables/PROTOCOLO_PRUEBAS.md).

Uso:  python escenario_ahorro.py            → imprime tabla y guarda JSON
"""
import json, math, random
from datetime import date, timedelta

def correr(dias=90, semilla=7, area_ha=1.0, inicio=date(2026, 9, 1)):
    rnd = random.Random(semilla)
    cc, pmp, raiz_m, p, kc = 0.32, 0.16, 0.40, 0.55, 1.0     # kikuyo, andisol Sabana
    taw = (cc - pmp) * raiz_m * 1000                         # mm
    raw = p * taw
    efic = 0.75                                              # aspersión
    # clima: régimen bimodal (sep–nov es temporada de lluvias)
    lluvia, et0 = [], []
    for d in range(dias + 2):
        dj = (inicio + timedelta(days=d)).timetuple().tm_yday
        f = 1.0 + 0.6 * math.sin(4 * math.pi * (dj - 60) / 365)
        lluvia.append(rnd.expovariate(1 / 9.0) if rnd.random() < 0.33 * f else 0.0)
        et0.append(max(1.8, 3.2 + 0.8 * math.sin(2 * math.pi * (dj - 30) / 365) + rnd.gauss(0, 0.5)))
    pron = [max(0.0, lluvia[d + 1] * rnd.uniform(0.6, 1.4) + rnd.gauss(0, 0.8)) for d in range(dias)]

    def simular(politica):
        dr = 0.3 * taw          # agotamiento inicial
        out = []
        for d in range(dias):
            riego_bruto = 0.0
            if politica == "tradicional":
                # el productor ya "mira el cielo": no riega si llovió >5 mm en
                # los dos días anteriores, pero sí riega por calendario
                llovio = sum(lluvia[max(0, d - 3):d]) > 3
                if d % 3 == 0 and not llovio:
                    riego_bruto = 12.0 / efic
            else:
                if dr > raw and pron[d] < 5:
                    riego_bruto = 0.8 * dr / efic     # repone hasta ~80 % (deja espacio a la lluvia)
            neta = riego_bruto * efic
            pe = lluvia[d] * 0.85 if lluvia[d] > 2 else 0.0      # lluvia efectiva
            etc = kc * et0[d]
            ks = 1.0 if dr <= raw else max(0.0, (taw - dr) / (taw - raw))
            dr = dr - pe - neta + etc * ks
            perc = max(0.0, -dr); dr = max(0.0, min(taw, dr))
            out.append({"dia": d, "fecha": str(inicio + timedelta(days=d)),
                        "riego_mm": round(riego_bruto, 2),
                        "riego_m3": round(riego_bruto * 10 * area_ha, 2),
                        "percolacion_mm": round(perc, 2), "estres": ks < 1.0,
                        "agotamiento_mm": round(dr, 2), "lluvia_mm": round(lluvia[d], 2)})
        return out

    A, B = simular("tradicional"), simular("hidrosopo")
    sem = lambda S: [round(sum(x["riego_m3"] for x in S[i:i + 7]), 1) for i in range(0, dias, 7)]   # la última semana puede ser parcial
    tot = lambda S, k: round(sum(x[k] for x in S), 1)
    vA, vB = tot(A, "riego_m3"), tot(B, "riego_m3")
    kwh_m3, cop_kwh = 0.223, 850                     # bomba 30 m, η 0.55 (costos.py)
    r = {
        "nota": "SIMULACIÓN (gemelo digital). No reemplaza la medición de campo.",
        "dias": dias, "area_ha": area_ha, "taw_mm": round(taw, 1), "raw_mm": round(raw, 1),
        "tradicional": {"m3": vA, "eventos": sum(1 for x in A if x["riego_mm"] > 0),
                        "dias_estres": sum(x["estres"] for x in A), "percolacion_mm": tot(A, "percolacion_mm")},
        "hidrosopo": {"m3": vB, "eventos": sum(1 for x in B if x["riego_mm"] > 0),
                      "dias_estres": sum(x["estres"] for x in B), "percolacion_mm": tot(B, "percolacion_mm")},
        "ahorro_m3": round(vA - vB, 1),
        "ahorro_pct": round(100 * (vA - vB) / vA, 1) if vA else 0,
        "ahorro_cop_energia": round((vA - vB) * kwh_m3 * cop_kwh),
        "semanal_tradicional_m3": sem(A), "semanal_hidrosopo_m3": sem(B),
        "lluvia_total_mm": round(sum(lluvia[:dias]), 1),
    }
    return r

if __name__ == "__main__":
    r = correr()
    json.dump(r, open("escenario_ahorro.json", "w"), indent=2, ensure_ascii=False)
    print(f"{'':22}{'Tradicional':>12}{'HidroSopó':>12}")
    for k, lab in [("m3", "Agua aplicada (m³)"), ("eventos", "Riegos"), ("dias_estres", "Días con estrés"),
                   ("percolacion_mm", "Pérdida por percolación")]:
        print(f"{lab:22}{r['tradicional'][k]:>12}{r['hidrosopo'][k]:>12}")
    print(f"\nAhorro: {r['ahorro_m3']} m³ ({r['ahorro_pct']} %) · ${r['ahorro_cop_energia']:,} COP de energía en {r['dias']} días")
    print(r["nota"])


def montecarlo(n=50, **kw):
    """Repite el escenario con n climas distintos: el ahorro depende mucho de
    cuánto llueva, así que se reporta la mediana y el rango P10–P90."""
    import statistics as st
    rs = [correr(semilla=s, **kw) for s in range(1, n + 1)]
    ah = sorted(r["ahorro_pct"] for r in rs)
    m3 = sorted(r["ahorro_m3"] for r in rs)
    q = lambda v, f: v[int(f * (len(v) - 1))]
    return {"n": n, "ahorro_pct_mediana": round(st.median(ah), 1),
            "ahorro_pct_p10": q(ah, .1), "ahorro_pct_p90": q(ah, .9),
            "ahorro_m3_mediana": round(st.median(m3), 1),
            "estres_hidrosopo_mediana": st.median(r["hidrosopo"]["dias_estres"] for r in rs),
            "estres_tradicional_mediana": st.median(r["tradicional"]["dias_estres"] for r in rs)}


if __name__ == "__main__":
    mc = montecarlo()
    print(f"\n50 climas distintos → ahorro mediano {mc['ahorro_pct_mediana']} % "
          f"(P10–P90: {mc['ahorro_pct_p10']}–{mc['ahorro_pct_p90']} %), "
          f"{mc['ahorro_m3_mediana']} m³/ha en 90 días")
    from datetime import date as _d
    seca = montecarlo(inicio=_d(2026, 12, 1))
    print(f"Temporada seca (dic–feb) → ahorro mediano {seca['ahorro_pct_mediana']} % "
          f"(P10–P90: {seca['ahorro_pct_p10']}–{seca['ahorro_pct_p90']} %)")
    r = json.load(open("escenario_ahorro.json")); r["montecarlo"] = mc
    r["montecarlo_temporada_seca"] = seca
    # Para la gráfica se usa el clima "típico": el de ahorro más cercano a la mediana
    cand = [correr(semilla=k, inicio=_d(2026, 12, 1)) for k in range(1, 51)]
    r["seca"] = min(cand, key=lambda c: abs(c["ahorro_pct"] - seca["ahorro_pct_mediana"]))
    json.dump(r, open("escenario_ahorro.json", "w"), indent=2, ensure_ascii=False)
