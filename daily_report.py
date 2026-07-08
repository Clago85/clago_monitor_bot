#!/usr/bin/env python3
"""
Report giornaliero su Telegram (gira sui server GitHub, NON dipende dal PC).
Legge performance.json e manda un riepilogo della giornata: trade aperti e loro
P&L, trade chiusi OGGI con esito, % vincenti, migliore/peggiore, sbilanciamento
long/short del mercato.

Lanciato da un workflow dedicato (report.yml) via workflow_dispatch, tipicamente
alle 23:00 italiane tramite un job su cron-job.org.

Coerente col dashboard: esclude i chiusi con durata < 3h (flip-flop, non swing).
"""

import os
import json
import datetime
import requests

try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("Europe/Rome")
except Exception:
    TZ = datetime.timezone(datetime.timedelta(hours=2))  # fallback estate

PERF_PATH = "performance.json"
MIN_DURATION_H = 3.0  # come il dashboard: sotto le 3h è rumore, non conta
TG_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
TG_CHAT = os.environ.get("TELEGRAM_CHAT_ID", "").strip()


def send_telegram(text):
    if not TG_TOKEN or not TG_CHAT:
        print("[WARN] Telegram non configurato (manca TELEGRAM_TOKEN o CHAT_ID)", flush=True)
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


def pct(x, plus=True):
    if x is None:
        return "-"
    s = "+" if (plus and x >= 0) else ""
    return f"{s}{x:.2f}%"


def main():
    if not os.path.exists(PERF_PATH):
        print("[INFO] performance.json assente, niente report")
        return
    try:
        with open(PERF_PATH, "r", encoding="utf-8") as f:
            perf = json.load(f)
    except Exception as e:
        print(f"[ERR] performance.json illeggibile: {e}")
        return

    open_t = perf.get("open", []) or []
    closed_all = perf.get("closed", []) or []

    now = datetime.datetime.now(TZ)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_ts = today_start.timestamp()

    # Chiusi OGGI, filtro durata >= 3h (coerente col dashboard)
    closed_today = [t for t in closed_all
                    if (t.get("close_ts") or 0) >= today_ts
                    and (t.get("duration_h") or 0) >= MIN_DURATION_H]

    # --- Sezione APERTI ---
    n_open = len(open_t)
    in_profit = sum(1 for t in open_t if (t.get("pnl_pct") or 0) > 0)
    n_long = sum(1 for t in open_t if t.get("direction") == "LONG")
    n_short = sum(1 for t in open_t if t.get("direction") == "SHORT")
    avg_open = (sum((t.get("pnl_pct") or 0) for t in open_t) / n_open) if n_open else None
    best_o = max(open_t, key=lambda t: t.get("pnl_pct") or -999, default=None)
    worst_o = min(open_t, key=lambda t: t.get("pnl_pct") or 999, default=None)

    # --- Sezione CHIUSI OGGI ---
    n_cl = len(closed_today)
    wins = sum(1 for t in closed_today if (t.get("result_pct") or 0) > 0)
    losses = n_cl - wins
    winrate = (wins / n_cl * 100) if n_cl else None
    avg_cl = (sum((t.get("result_pct") or 0) for t in closed_today) / n_cl) if n_cl else None
    best_c = max(closed_today, key=lambda t: t.get("result_pct") or -999, default=None)
    worst_c = min(closed_today, key=lambda t: t.get("result_pct") or 999, default=None)

    L = []
    L.append(f"📊 <b>REPORT GIORNALIERO</b> — {now.strftime('%d/%m/%Y')}")
    L.append("")
    L.append(f"🟢 <b>Aperti:</b> {n_open}  ({in_profit} in profitto)")
    if n_open:
        L.append(f"   Long {n_long} · Short {n_short} · P&amp;L medio {pct(avg_open)}")
        if best_o:
            L.append(f"   ▲ {best_o.get('asset')} {pct(best_o.get('pnl_pct'))}"
                     f"  ▼ {worst_o.get('asset')} {pct(worst_o.get('pnl_pct'))}")
    L.append("")
    if n_cl:
        L.append(f"✅ <b>Chiusi oggi:</b> {n_cl}  ({wins} vinti, {losses} persi · {winrate:.0f}%)")
        L.append(f"   Media {pct(avg_cl)}  ·  ▲ {best_c.get('asset')} {pct(best_c.get('result_pct'))}"
                 f"  ▼ {worst_c.get('asset')} {pct(worst_c.get('result_pct'))}")
        L.append("")
        for t in sorted(closed_today, key=lambda x: x.get("result_pct") or 0, reverse=True):
            ico = "✅" if (t.get("result_pct") or 0) > 0 else "❌"
            L.append(f"   {ico} {t.get('asset')} {t.get('direction')} "
                     f"{pct(t.get('result_pct'))} ({(t.get('duration_h') or 0):.0f}h)")
    else:
        L.append("✅ <b>Chiusi oggi:</b> nessuno (nessun trade ha chiuso oggi)")

    msg = "\n".join(L)
    ok = send_telegram(msg)
    print("[INFO] Report inviato" if ok else "[ERR] Invio report fallito", flush=True)


if __name__ == "__main__":
    main()
