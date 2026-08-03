#!/usr/bin/env python3
"""Invia gli alert salvati in pending_alerts.json a Telegram.

RETE DI SICUREZZA (03/08/2026): se Telegram rifiuta il messaggio per un errore
di formattazione HTML (codice 400, "can't parse entities"), il messaggio NON
viene perso: si ritenta in testo semplice, togliendo i tag. Prima bastava un
carattere "<" dentro il testo — per esempio la scritta "8<12<21" dello stack
EMA — per far rifiutare l'intero alert e restare senza avvisi senza accorgersene,
perche' il workflow risultava comunque "success".
"""

import os
import json
import re
import time
import requests

PENDING_PATH = "pending_alerts.json"
TG_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
TG_CHAT = os.environ.get("TELEGRAM_CHAT_ID", "").strip()


def _strip_html(text):
    """Toglie i tag e riporta le entita' di base: usato solo come fallback."""
    txt = re.sub(r"<a href=\"([^\"]*)\">([^<]*)</a>", r"\2 (\1)", text)
    txt = re.sub(r"<[^>]+>", "", txt)
    return (txt.replace("&lt;", "<").replace("&gt;", ">")
               .replace("&amp;", "&").replace("&quot;", '"'))


def _post(payload):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    return requests.post(url, json=payload, timeout=20)


def send_telegram(text):
    if not TG_TOKEN or not TG_CHAT:
        print("[WARN] Telegram non configurato", flush=True)
        return False
    base = {"chat_id": TG_CHAT, "disable_web_page_preview": True}
    try:
        r = _post({**base, "text": text, "parse_mode": "HTML"})
        if r.ok:
            return True
        # 400 = quasi sempre HTML malformato: ritento senza formattazione
        if r.status_code == 400:
            print(f"[WARN] HTML rifiutato ({r.text[:120]}), ritento in testo semplice", flush=True)
            r2 = _post({**base, "text": _strip_html(text)})
            if r2.ok:
                print("[INFO] inviato in testo semplice", flush=True)
                return True
            print(f"[ERR] anche il testo semplice fallisce: {r2.status_code} {r2.text[:150]}", flush=True)
            return False
        print(f"[ERR] Telegram {r.status_code}: {r.text[:200]}", flush=True)
        return False
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
    if sent < len(alerts):
        print(f"[WARN] {len(alerts) - sent} alert NON consegnati", flush=True)
    try:
        os.remove(PENDING_PATH)
        print("[INFO] pending_alerts.json eliminato")
    except Exception as e:
        print(f"[WARN] Impossibile eliminare pending_alerts.json: {e}")


if __name__ == "__main__":
    main()
