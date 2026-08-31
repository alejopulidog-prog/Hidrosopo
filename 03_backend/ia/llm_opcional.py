"""
HidroSopó — Capa 3 opcional: redacción con LLM
===============================================
La versión de plantillas (motor_recomendacion.redactar_mensaje) es
la que se usa por defecto: $0, sin dependencias, no se cae.

Esta capa es cosmética. Actívala solo si quieres mensajes con más
variedad de redacción. NO es lo que sustenta la parte de "IA" del
proyecto — eso es el modelo ML de modelo_ml.py.

Proveedores gratuitos, en orden de recomendación:
  1. Ollama local (llama3.2:3b)  — $0 total, sin internet, sin cuotas
  2. Groq free tier              — muy rápido
  3. Google Gemini free tier     — buena calidad en español
"""

from __future__ import annotations
import os
import json

try:
    import requests
except ImportError:
    requests = None

PROVEEDOR = os.getenv("LLM_PROVEEDOR", "ninguno")   # ninguno|ollama|groq|gemini

SYSTEM = (
    "Eres un asistente técnico agrícola que habla con pequeños productores "
    "de Sopó, Cundinamarca. Escribe en español colombiano, claro y respetuoso, "
    "sin tecnicismos innecesarios. Máximo 4 frases. Nunca inventes datos: "
    "usa solo los números que te dan. Si recomiendas regar, di los minutos "
    "y los metros cúbicos. Trata al productor de usted."
)


def redactar_con_llm(datos: dict, nombre: str = "") -> str | None:
    """Devuelve el texto redactado, o None si falla (el caller usa la plantilla)."""
    if PROVEEDOR == "ninguno" or requests is None:
        return None

    resumen = json.dumps({
        "accion": datos["decision"]["accion"],
        "razon": datos["decision"]["razon"],
        "pct_agua_disponible": datos["estado_suelo"]["pct_agua_disponible"],
        "riego": datos.get("riego"),
        "lluvia_7d_mm": datos["clima"]["lluvia_proxima_7d_mm"],
        "pastoreo": datos.get("pastoreo"),
    }, ensure_ascii=False)

    prompt = (f"Productor: {nombre or 'el productor'}\n"
              f"Datos del sistema:\n{resumen}\n\n"
              "Redacta la recomendación:")

    try:
        if PROVEEDOR == "ollama":
            r = requests.post(
                os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat"),
                json={"model": os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
                      "messages": [{"role": "system", "content": SYSTEM},
                                   {"role": "user", "content": prompt}],
                      "stream": False},
                timeout=45)
            return r.json()["message"]["content"].strip()

        if PROVEEDOR == "groq":
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}"},
                json={"model": "llama-3.3-70b-versatile",
                      "messages": [{"role": "system", "content": SYSTEM},
                                   {"role": "user", "content": prompt}],
                      "max_tokens": 300, "temperature": 0.4},
                timeout=30)
            return r.json()["choices"][0]["message"]["content"].strip()

        if PROVEEDOR == "gemini":
            key = os.environ["GEMINI_API_KEY"]
            r = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"gemini-2.0-flash:generateContent?key={key}",
                json={"system_instruction": {"parts": [{"text": SYSTEM}]},
                      "contents": [{"parts": [{"text": prompt}]}],
                      "generationConfig": {"maxOutputTokens": 300, "temperature": 0.4}},
                timeout=30)
            return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

    except Exception as e:                      # noqa: BLE001
        print(f"[llm] falló ({PROVEEDOR}): {e} — se usa la plantilla")
        return None

    return None
