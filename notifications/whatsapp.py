"""
WhatsApp notifications via CallMeBot (free, no Twilio).

CallMeBot lets you receive WhatsApp messages to your own number after a one-time
setup: add their bot, get an API key, then call their HTTP API.

Setup: https://www.callmebot.com/blog/free-api-whatsapp-messages/
  - Add +34 644 66 32 62 to your contacts and send "I allow callmebot to send me messages"
  - You receive an API key; set CALLMEBOT_WHATSAPP_APIKEY and CALLMEBOT_WHATSAPP_PHONE (E.164, e.g. +15551234567)
"""

import os
import threading
import urllib.parse
import urllib.request

CALLMEBOT_URL = "https://api.callmebot.com/whatsapp.php"


def _send_whatsapp_sync(recording_path: str) -> None:
    """Do the actual HTTP request (run in background thread)."""
    api_key = os.environ.get("CALLMEBOT_WHATSAPP_APIKEY", "").strip()
    phone = os.environ.get("CALLMEBOT_WHATSAPP_PHONE", "").strip()

    if not api_key or not phone:
        print("[WhatsApp] Notification skipped: set CALLMEBOT_WHATSAPP_APIKEY and CALLMEBOT_WHATSAPP_PHONE in .env")
        return

    phone_clean = phone.lstrip("+").replace(" ", "")
    if not phone_clean.isdigit():
        print("[WhatsApp] CALLMEBOT_WHATSAPP_PHONE should be E.164 (e.g. +15551234567); skipping.")
        return

    filename = os.path.basename(recording_path)
    message = f"Rover: Pepe spotted! 🐶  — {filename}"

    params = {"phone": f"+{phone_clean}", "text": message, "apikey": api_key}
    url = f"{CALLMEBOT_URL}?{urllib.parse.urlencode(params)}"

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8", errors="replace").strip()
            if resp.status == 200 and "error" not in body.lower():
                print(f"[WhatsApp] Sent for {filename}")
            else:
                print(f"[WhatsApp] CallMeBot response ({resp.status}): {body or '(empty)'}")
    except OSError as e:
        print(f"[WhatsApp] Failed to send: {e}")


def notify_recording_saved(recording_path: str) -> None:
    """
    Send a WhatsApp message when a dog recording has been saved.

    Runs the HTTP request in a background thread so the main loop (camera, motors)
    is not blocked. Uses CallMeBot if CALLMEBOT_WHATSAPP_APIKEY and
    CALLMEBOT_WHATSAPP_PHONE are set.

    Args:
        recording_path: Path to the saved video file (e.g. recordings/dog_2025-03-02_14-30-45.avi).
    """
    thread = threading.Thread(target=_send_whatsapp_sync, args=(recording_path,), daemon=True)
    thread.start()
