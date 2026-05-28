#!/usr/bin/env python3
"""Invia gli alert salvati in pending_alerts.json a Telegram."""

import os
import json
import time
import requests

PENDING_PATH = "pending_alerts.json"
TG_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
TG_CHAT = os.environ.get("TELEGRAM_CHAT_ID", "").strip()


def send_telegram(text):
    if not TG_TOKEN or not TG_CHAT:
        print("[WARN] Telegram non configurato", flush=True)
        return False
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={
            "chat_id": TG_CHAT,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }, timeout=20)
        if not r.ok:
            print(f"[ERR] Telegram {r.status_code}: {r.text[:200]}", flush=True)
            return False
        return True
    except Exception as e:
        print(f"[ERR] Telegram exception: {e}", flush=True)
        return False


def main():
    if not os.path.exists(PENDING_PATH):
        print("[INFO] Nessun pending_alerts.json da inviare")
        return
    try:
        with open(PENDING_PATH, "r", encoding="utf-8") as f:
            alerts = json.load(f)
    except Exception as e:
        print(f"[ERR] Impossibile leggere {PENDING_PATH}: {e}")
        return
    if not isinstance(alerts, list) or not alerts:
        print("[INFO] pending_alerts.json vuoto")
        try:
            os.remove(PENDING_PATH)
        except Exception:
            pass
        return
    print(f"[INFO] Invio {len(alerts)} alert Telegram...")
    sent = 0
    for msg in alerts:
        if send_telegram(msg):
            sent += 1
        time.sleep(0.6)
    print(f"[INFO] Inviati {sent}/{len(alerts)} alert")
    try:
        os.remove(PENDING_PATH)
        print("[INFO] pending_alerts.json eliminato")
    except Exception as e:
        print(f"[WARN] Impossibile eliminare pending_alerts.json: {e}")


if __name__ == "__main__":
    main()
