"""
HidroSopó — Base de conocimiento del asistente
==============================================
Preguntas generales de riego, suelo, clima, tecnología y normativa que el
asistente responde como experto, sin depender de internet. El mismo JSON lo
usan la app (04_dashboard/conocimiento.json) y «Sopó Cuida el Agua».

Regla: aquí hay conocimiento general. Las cifras del predio (humedad, minutos,
ahorro) salen siempre del motor, nunca de este archivo.
"""
from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

RUTA = Path(__file__).with_name("conocimiento.json")


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFD", (t or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"[¿?¡!.,;:()«»\"']", " ", t)
    return re.sub(r"\s+", " ", t).strip()


@lru_cache(maxsize=1)
def entradas() -> list[dict]:
    return json.loads(RUTA.read_text(encoding="utf-8"))["entradas"]


def buscar(mensaje: str) -> tuple[dict | None, int]:
    """Devuelve (entrada, puntaje). El puntaje suma la longitud de las claves
    encontradas (claves más específicas pesan más); el título exacto gana."""
    t = f" {_norm(mensaje)} "
    mejor, puntos_mejor = None, 0
    for e in entradas():
        puntos = 100 if _norm(e["titulo"]) in t else 0
        for c in e["claves"]:
            c = _norm(c)
            if len(c) >= 3 and f" {c} " in t:
                puntos += len(c)
        if puntos > puntos_mejor:
            mejor, puntos_mejor = e, puntos
    return mejor, puntos_mejor


PREGUNTA_GENERAL = re.compile(
    r"\b(que es|que son|que significa|para que sirve|como funciona|como se|como hago|"
    r"como detecto|como recojo|como regar|como sé|como se|por que|cual es|cuales son|"
    r"cuando necesita|es mejor|necesito|explique|expliqueme|explicame|que pasa si|"
    r"cuanto cuesta el sistema|cuanta lluvia)\b")


def es_pregunta_general(mensaje: str) -> bool:
    return bool(PREGUNTA_GENERAL.search(_norm(mensaje)))
