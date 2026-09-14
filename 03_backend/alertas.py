"""
HidroSopó — Envío de alertas al productor
==========================================
Opciones gratuitas, en orden de recomendación para el piloto:

1. Telegram Bot      — 100% gratis, ilimitado, 5 min de configuración
2. CallMeBot WhatsApp— gratis, requiere que el productor autorice el número
3. Twilio sandbox    — gratis con límites, sirve para demostrar
4. SMS               — de pago en Colombia, no recomendado para el piloto

Realidad de campo: en una finca de Sopó el productor probablemente usa
WhatsApp, no Telegram. Empieza con WhatsApp vía CallMeBot y ten Telegram
como respaldo. Si el productor no usa smartphone, imprime el reporte
semanal en papel — no es menos válido, y hay que decirlo en el informe.
"""

from __future__ import annotations
import os
import urllib.parse

try:
    import requests
except ImportError:
    requests = None

CANAL = os.getenv("CANAL_ALERTAS", "consola")   # consola|telegram|whatsapp|twilio


def enviar(destino: str, mensaje: str) -> bool:
    """Envía la alerta por el canal configurado. Devuelve True si salió."""
    if CANAL == "consola" or requests is None:
        print(f"\n{'='*56}\n[ALERTA -> {destino}]\n{mensaje}\n{'='*56}\n")
        return True

    try:
        if CANAL == "telegram":
            token = os.environ["TELEGRAM_TOKEN"]
            chat_id = destino or os.environ["TELEGRAM_CHAT_ID"]
            r = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": mensaje, "parse_mode": "HTML"},
                timeout=15)
            return r.ok

        if CANAL == "whatsapp":
            # CallMeBot: el productor debe enviar una vez
            # "I allow callmebot to send me messages" al +34 644 51 95 23
            apikey = os.environ["CALLMEBOT_APIKEY"]
            url = ("https://api.callmebot.com/whatsapp.php"
                   f"?phone={urllib.parse.quote(destino)}"
                   f"&text={urllib.parse.quote(mensaje)}"
                   f"&apikey={apikey}")
            r = requests.get(url, timeout=20)
            return r.ok

        if CANAL == "twilio":
            sid = os.environ["TWILIO_SID"]
            tok = os.environ["TWILIO_TOKEN"]
            desde = os.environ["TWILIO_FROM"]      # 'whatsapp:+14155238886'
            r = requests.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
                auth=(sid, tok),
                data={"From": desde, "To": f"whatsapp:{destino}", "Body": mensaje},
                timeout=20)
            return r.status_code < 300

    except Exception as e:                       # noqa: BLE001
        print(f"[alertas] falló el envío por {CANAL}: {e}")
        return False

    return False


def alerta_tecnica(mensaje: str) -> bool:
    """Alertas para el estudiante, no para el productor:
    batería baja, nodo caído, exceso de concesión."""
    destino = os.getenv("CONTACTO_TECNICO", "")
    return enviar(destino, f"⚙️ [HidroSopó — técnico]\n{mensaje}")
