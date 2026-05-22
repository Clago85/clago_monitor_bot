#!/usr/bin/env python3
"""
OI Monitor — versione Python per GitHub Actions / scheduler cloud.

Replica la logica della dashboard HTML (Bias 24h x Signal 4h -> Azione)
e manda alert Telegram quando un asset transita verso un setup operativo.

Variabili d'ambiente richieste:
  TELEGRAM_TOKEN     - token del bot Telegram (da @BotFather)
  TELEGRAM_CHAT_ID   - il tuo chat ID (da @userinfobot)

File generati nella cartella corrente:
  state.json    - ultimo stato di ogni asset (committed dal workflow)
  history.json  - log delle transizioni (ultimi 1000 eventi)
"""

import os
import json
import time
from datetime import datetime, timezone

import requests

# =========================================================
# CONFIGURAZIONE - lista asset
# =========================================================
ASSETS = [
    {"id": "BTC",     "binance": "BTCUSDT",      "bybit": "BTCUSDT",      "primary": "binance"},
    {"id": "ETH",     "binance": "ETHUSDT",      "bybit": "ETHUSDT",      "primary": "binance"},
    {"id": "SOL",     "binance": "SOLUSDT",      "bybit": "SOLUSDT",      "primary": "binance"},
    {"id": "LINK",    "binance": "LINKUSDT",     "bybit": "LINKUSDT",     "primary": "binance"},
    {"id": "ICP",     "binance": "ICPUSDT",      "bybit": "ICPUSDT",      "primary": "binance"},
    {"id": "SUI",     "binance": "SUIUSDT",      "bybit": "SUIUSDT",      "primary": "binance"},
    {"id": "HBAR",    "binance": "HBARUSDT",     "bybit": "HBARUSDT",     "primary": "binance"},
    {"id": "AR",      "binance": "ARUSDT",       "bybit": "ARUSDT",       "primary": "binance"},
    {"id": "TAO",     "binance": "TAOUSDT",      "bybit": "TAOUSDT",      "primary": "binance"},
    {"id": "RENDER",  "binance": "RENDERUSDT",   "bybit": "RENDERUSDT",   "primary": "binance"},
    {"id": "VIRTUAL", "binance": "VIRTUALUSDT",  "bybit": "VIRTUALUSDT",  "primary": "binance"},
    {"id": "INJ",     "binance": "INJUSDT",      "bybit": "INJUSDT",      "primary": "binance"},
    {"id": "SEI",     "binance": "SEIUSDT",      "bybit": "SEIUSDT",      "primary": "binance"},
    {"id": "ONDO",    "binance": "ONDOUSDT",     "bybit": "ONDOUSDT",     "primary": "binance"},
    {"id": "ENA",     "binance": "ENAUSDT",      "bybit": "ENAUSDT",      "primary": "binance"},
    {"id": "JUP",     "binance": "JUPUSDT",      "bybit": "JUPUSDT",      "primary": "binance"},
    {"id": "BONK",    "binance": "1000BONKUSDT", "bybit": "1000BONKUSDT", "primary": "binance"},
    {"id": "PENGU",   "binance": "PENGUUSDT",    "bybit": "PENGUUSDT",    "primary": "binance"},
    {"id": "KAS",     "binance": None,           "bybit": "KASUSDT",      "primary": "bybit"},
    {"id": "TRX",     "binance": "TRXUSDT",      "bybit": "TRXUSDT",      "primary": "binance"},
    {"id": "TON",     "binance": "TONUSDT",      "bybit": "TONUSDT",      "primary": "binance"},
    {"id": "ROSE",    "binance": "ROSEUSDT",     "bybit": "ROSEUSDT",     "primary": "binance"},
    {"id": "NEAR",    "binance": "NEARUSDT",     "bybit": "NEARUSDT",     "primary": "binance"},
    {"id": "FET",     "binance": "FETUSDT",      "bybit": "FETUSDT",      "primary": "binance"},
    {"id": "HYPE",    "binance": "HYPEUSDT",     "bybit": "HYPEUSDT",     "primary": "binance"},
    {"id": "STRK",    "binance": "STRKUSDT",     "bybit": "STRKUSDT",     "primary": "binance"},
]

# =========================================================
# SOGLIE - identiche alla dashboard HTML
# =========================================================
T = {
    "oi_expanding":     5,
    "oi_strong_exp":    10,
    "oi_contracting":   -5,
    "oi_strong_contr":  -10,
    "price_up":         2,
    "price_down":       -2,
    "price_strong_up":  5,
    "price_strong_down": -5,
    "funding_high":     0.05,
    "funding_very_high": 0.08,
    "funding_negative": -0.01,
    "funding_very_neg": -0.03,
}

STATE_FILE = "state.json"
HISTORY_FILE = "history.json"

TG_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
TG_CHAT  = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

HTTP_TIMEOUT = 15

# =========================================================
# FETCHERS
# =========================================================

def http_get_json(url):
    r = requests.get(url, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    return r.json()


def fetch_binance(asset):
    sym = asset["binance"]
    oi_now  = http_get_json(f"https://fapi.binance.com/fapi/v1/openInterest?symbol={sym}")
    oi_hist = http_get_json(f"https://fapi.binance.com/futures/data/openInterestHist?symbol={sym}&period=1h&limit=25")
    ticker  = http_get_json(f"https://fapi.binance.com/fapi/v1/ticker/24hr?symbol={sym}")
    premium = http_get_json(f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={sym}")
    klines  = http_get_json(f"https://fapi.binance.com/fapi/v1/klines?symbol={sym}&interval=1h&limit=5")

    if isinstance(oi_now, dict) and oi_now.get("code"):
        raise Exception(f"Binance OI error: {oi_now.get('msg')}")

    current_oi = float(oi_now["openInterest"])
    last_price = float(premium["markPrice"])

    oi_24h_ago = oi_4h_ago = None
    if isinstance(oi_hist, list) and oi_hist:
        sorted_hist = sorted(oi_hist, key=lambda x: x["timestamp"])
        oi_24h_ago = float(sorted_hist[0]["sumOpenInterest"])
        four_idx = max(0, len(sorted_hist) - 5)
        oi_4h_ago = float(sorted_hist[four_idx]["sumOpenInterest"])

    oi_change_24h = ((current_oi - oi_24h_ago) / oi_24h_ago) * 100 if oi_24h_ago else None
    oi_change_4h  = ((current_oi - oi_4h_ago)  / oi_4h_ago) * 100 if oi_4h_ago else None

    price_change_4h = None
    if isinstance(klines, list) and len(klines) >= 1:
        try:
            p4 = float(klines[0][1])
            if p4 > 0:
                price_change_4h = ((last_price - p4) / p4) * 100
        except Exception:
            pass

    return {
        "source": "Binance",
        "source_symbol": sym,
        "price": last_price,
        "priceChange24h": float(ticker["priceChangePercent"]),
        "priceChange4h": price_change_4h,
        "fundingRate": float(premium["lastFundingRate"]) * 100,
        "currentOI": current_oi,
        "currentOI_USD": current_oi * last_price,
        "oiChange24h": oi_change_24h,
        "oiChange4h": oi_change_4h,
    }


def fetch_bybit(asset):
    sym = asset.get("bybit")
    if not sym:
        raise Exception("Nessun simbolo Bybit configurato")

    oi_hist = http_get_json(
        f"https://api.bybit.com/v5/market/open-interest?category=linear&symbol={sym}&intervalTime=1h&limit=25"
    )
    ticker  = http_get_json(f"https://api.bybit.com/v5/market/tickers?category=linear&symbol={sym}")
    klines  = http_get_json(f"https://api.bybit.com/v5/market/kline?category=linear&symbol={sym}&interval=60&limit=5")

    if not oi_hist.get("result") or not oi_hist["result"].get("list"):
        raise Exception("Bybit OI list vuota")
    lst = oi_hist["result"]["list"]
    sorted_lst = sorted(lst, key=lambda x: int(x["timestamp"]), reverse=True)
    current_oi  = float(sorted_lst[0]["openInterest"])
    oi_24h_ago  = float(sorted_lst[-1]["openInterest"])
    four_idx    = min(len(sorted_lst) - 1, 4)
    oi_4h_ago   = float(sorted_lst[four_idx]["openInterest"])

    oi_change_24h = ((current_oi - oi_24h_ago) / oi_24h_ago) * 100 if oi_24h_ago else None
    oi_change_4h  = ((current_oi - oi_4h_ago)  / oi_4h_ago) * 100 if oi_4h_ago else None

    t = ticker["result"]["list"][0]
    last_price = float(t["lastPrice"])

    price_change_4h = None
    if klines.get("result") and klines["result"].get("list"):
        k_sorted = sorted(klines["result"]["list"], key=lambda x: int(x[0]))
        try:
            p4 = float(k_sorted[0][1])
            if p4 > 0:
                price_change_4h = ((last_price - p4) / p4) * 100
        except Exception:
            pass

    return {
        "source": "Bybit",
        "source_symbol": sym,
        "price": last_price,
        "priceChange24h": float(t["price24hPcnt"]) * 100,
        "priceChange4h": price_change_4h,
        "fundingRate": float(t["fundingRate"]) * 100,
        "currentOI": current_oi,
        "currentOI_USD": current_oi * last_price,
        "oiChange24h": oi_change_24h,
        "oiChange4h": oi_change_4h,
    }


def fetch_asset(asset):
    primary = asset["primary"]
    try:
        if primary == "binance" and asset.get("binance"):
            return fetch_binance(asset)
        if asset.get("bybit"):
            return fetch_bybit(asset)
        raise Exception("Nessuna source configurata")
    except Exception as e:
        if primary == "binance" and asset.get("bybit"):
            try:
                return fetch_bybit(asset)
            except Exception as e2:
                return {"error": f"{e} / {e2}"}
        return {"error": str(e)}


# =========================================================
# BIAS / SIGNAL / ACTION - identici alla dashboard JS
# =========================================================

def compute_bias(d):
    oi = d.get("oiChange24h") or 0
    px = d.get("priceChange24h") or 0
    fr = d.get("fundingRate") or 0

    f_high   = fr > T["funding_high"]
    f_v_high = fr > T["funding_very_high"]
    f_neg    = fr < T["funding_negative"]
    f_v_neg  = fr < T["funding_very_neg"]

    oi_exp       = oi > T["oi_expanding"]
    oi_str_exp   = oi > T["oi_strong_exp"]
    oi_contr     = oi < T["oi_contracting"]
    oi_str_contr = oi < T["oi_strong_contr"]

    px_up       = px > T["price_up"]
    px_str_up   = px > T["price_strong_up"]
    px_down     = px < T["price_down"]
    px_str_down = px < T["price_strong_down"]
    px_flat     = abs(px) < 1.5

    if px_str_down and oi_str_contr and f_neg:    return "CAPITULATION"
    if px_up and oi_exp and f_v_high:             return "OVERHEATED LONG"
    if px_up and oi_exp:                          return "BULLISH SOLIDO"
    if px_up and oi_contr:                        return "SHORT SQUEEZE"
    if px_down and oi_exp:                        return "BEARISH AGGRESSIVO"
    if px_down and oi_contr:                      return "BEAR EXHAUSTION"
    if px_flat and oi_str_exp:                    return "PRESSURE BUILDUP"
    if f_v_neg and not px_str_down:               return "SHORT CROWDED"
    if f_v_high and not px_str_up:                return "LONG CROWDED"
    return "NEUTRAL"


def compute_signal_4h(d):
    oi4  = d.get("oiChange4h")   or 0
    px4  = d.get("priceChange4h") or 0
    oi24 = d.get("oiChange24h")   or 0
    px24 = d.get("priceChange24h") or 0

    def sgn(x):
        return 1 if x > 0 else -1 if x < 0 else 0
    px4_s, px24_s = sgn(px4), sgn(px24)
    oi4_s, oi24_s = sgn(oi4), sgn(oi24)

    if abs(px4) < 0.5 and oi4 > 1.5:
        return "BUILD-UP"

    px_div = abs(px4) > 0.8 and abs(px24) > 1 and px4_s != 0 and px24_s != 0 and px4_s != px24_s
    oi_div = abs(oi4) > 1.5 and abs(oi24) > 2 and oi4_s != 0 and oi24_s != 0 and oi4_s != oi24_s

    if px_div and oi_div: return "REVERSAL"
    if oi_div:            return "OI GIRA"
    if px_div:            return "PULLBACK"

    px_conf = px4_s == px24_s and px4_s != 0 and abs(px4) > 0.5
    oi_conf = oi4_s == oi24_s and oi4_s != 0 and abs(oi4) > 1.5
    if px_conf and oi_conf: return "CONFERMA"
    if px_conf or oi_conf:  return "PARZIALE"
    return "PIATTO"


def compute_action(bias, signal_4h):
    B, S = bias, signal_4h

    if B == "BULLISH SOLIDO" and S == "CONFERMA":                          return ("LONG", "strong")
    if B == "BULLISH SOLIDO" and S in ("BUILD-UP", "PARZIALE", "PULLBACK"): return ("LONG", "moderate")
    if B == "PRESSURE BUILDUP" and S in ("CONFERMA", "BUILD-UP"):          return ("LONG", "moderate")
    if B == "CAPITULATION" and S in ("REVERSAL", "OI GIRA"):               return ("LONG", "strong")
    if B == "BEAR EXHAUSTION" and S in ("REVERSAL", "OI GIRA"):            return ("LONG", "moderate")
    if B == "SHORT CROWDED" and S == "REVERSAL":                           return ("LONG", "strong")
    if B == "SHORT CROWDED" and S == "OI GIRA":                            return ("LONG", "moderate")
    if B == "BEARISH AGGRESSIVO" and S == "OI GIRA":                       return ("LONG", "moderate")

    if B == "BEARISH AGGRESSIVO" and S == "CONFERMA":                      return ("SHORT", "strong")
    if B == "BEARISH AGGRESSIVO" and S in ("PARZIALE", "PULLBACK"):        return ("SHORT", "moderate")
    if B == "OVERHEATED LONG" and S == "REVERSAL":                         return ("SHORT", "strong")
    if B == "OVERHEATED LONG" and S == "OI GIRA":                          return ("SHORT", "moderate")
    if B == "LONG CROWDED" and S == "REVERSAL":                            return ("SHORT", "strong")
    if B == "LONG CROWDED" and S == "OI GIRA":                             return ("SHORT", "moderate")
    if B == "SHORT SQUEEZE" and S == "REVERSAL":                           return ("SHORT", "moderate")
    if B == "BULLISH SOLIDO" and S == "REVERSAL":                          return ("SHORT", "weak")
    if B == "PRESSURE BUILDUP" and S == "REVERSAL":                        return ("SHORT", "weak")

    return ("NEUTRAL", "weak")


# =========================================================
# LOGICA TRANSIZIONI E TELEGRAM
# =========================================================

def should_notify(prev_label, curr_label):
    if prev_label == curr_label:
        return False
    prev_a, prev_s = prev_label.split("_") if "_" in prev_label else (prev_label, "weak")
    curr_a, curr_s = curr_label.split("_") if "_" in curr_label else (curr_label, "weak")

    if prev_a == "NEUTRAL" and curr_a in ("LONG", "SHORT"):
        return True
    if (prev_a == "LONG" and curr_a == "SHORT") or (prev_a == "SHORT" and curr_a == "LONG"):
        return True
    if prev_a == curr_a and prev_a in ("LONG", "SHORT"):
        strengths = {"weak": 0, "moderate": 1, "strong": 2}
        if strengths.get(curr_s, 0) > strengths.get(prev_s, 0):
            return True
    return False


def fmt_price(p):
    if p is None: return "-"
    if p >= 1000: return f"${p:,.0f}"
    if p >= 1:    return f"${p:.2f}"
    if p >= 0.01: return f"${p:.4f}"
    return f"${p:.6f}"


def fmt_pct(p, sig=2):
    if p is None: return "-"
    s = "+" if p > 0 else ""
    return f"{s}{p:.{sig}f}%"


def format_transition_message(t):
    asset = t["asset"]
    curr  = t["to"]
    prev  = t["from"]
    curr_a, curr_s = curr.split("_") if "_" in curr else (curr, "weak")

    emoji = {"LONG": "🟢", "SHORT": "🔴", "NEUTRAL": "⚪"}.get(curr_a, "⚪")
    strength_text = {"strong": "FORTE", "moderate": "moderato", "weak": "debole"}.get(curr_s, "")

    d = t["data"]
    sym = d.get("source_symbol", asset)
    src = d.get("source", "?")
    tv_exchange = "BINANCE" if src == "Binance" else "BYBIT"
    tv_link = f"https://www.tradingview.com/chart/?symbol={tv_exchange}:{sym}.P"

    return (
        f"{emoji} <b>{curr_a} {strength_text}</b> · <b>{asset}</b>\n\n"
        f"<b>Prezzo:</b> {fmt_price(d['price'])}\n"
        f"  Δ 4h:  {fmt_pct(d.get('priceChange4h'))}\n"
        f"  Δ 24h: {fmt_pct(d.get('priceChange24h'))}\n\n"
        f"<b>OI:</b>\n"
        f"  Δ 4h:  {fmt_pct(d.get('oiChange4h'))}\n"
        f"  Δ 24h: {fmt_pct(d.get('oiChange24h'))}\n\n"
        f"<b>Funding:</b> {fmt_pct(d.get('fundingRate'), 4)} (8h)\n\n"
        f"<b>Bias 24h:</b> {t['bias']}\n"
        f"<b>Signal 4h:</b> {t['signal']}\n"
        f"<b>Transizione:</b> {prev} → {curr}\n\n"
        f"🔍 <a href=\"{tv_link}\">TradingView</a>\n"
        f"⏰ {datetime.now(timezone.utc).strftime('%H:%M UTC · %d/%m/%Y')}"
    )


def send_telegram(text):
    if not TG_TOKEN or not TG_CHAT:
        print("[WARN] Telegram non configurato (mancano TELEGRAM_TOKEN o TELEGRAM_CHAT_ID)", flush=True)
        return False
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={
            "chat_id": TG_CHAT,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }, timeout=HTTP_TIMEOUT)
        if not r.ok:
            print(f"[ERR] Telegram {r.status_code}: {r.text[:200]}", flush=True)
            return False
        return True
    except Exception as e:
        print(f"[ERR] Telegram exception: {e}", flush=True)
        return False


# =========================================================
# STATE PERSISTENCE
# =========================================================

def load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False, default=str)


def append_history(entry):
    history = load_json(HISTORY_FILE, [])
    history.append(entry)
    history = history[-1000:]
    save_json(HISTORY_FILE, history)


# =========================================================
# MAIN
# =========================================================

def main():
    started_at = datetime.now(timezone.utc)
    print(f"\n=== OI Monitor — {started_at.isoformat()} ===", flush=True)

    last_state = load_json(STATE_FILE, {})
    is_first_run = not last_state
    new_state = {}
    transitions = []
    errors = []

    for asset in ASSETS:
        asset_id = asset["id"]
        try:
            data = fetch_asset(asset)
            if data.get("error"):
                errors.append(f"{asset_id}: {data['error']}")
                print(f"  [X] {asset_id}: {data['error']}", flush=True)
                continue

            bias    = compute_bias(data)
            signal  = compute_signal_4h(data)
            action, strength = compute_action(bias, signal)
            curr_label = f"{action}_{strength}"

            prev_entry = last_state.get(asset_id, {})
            prev_label = prev_entry.get("label")

            transition_logged = False
            # Caso 1: asset con storia, transizione significativa
            is_transition = prev_label and should_notify(prev_label, curr_label)
            # Caso 2: asset nuovo (appena aggiunto agli ASSETS) che entra direttamente in LONG/SHORT
            # — non vale al primo run del bot (lì si manda il riepilogo di startup)
            is_new_active = (not prev_label) and (not is_first_run) and action in ("LONG", "SHORT")

            if is_transition or is_new_active:
                from_label = prev_label if is_transition else "NEW"
                transition = {
                    "ts": int(time.time()),
                    "asset": asset_id,
                    "from": from_label,
                    "to": curr_label,
                    "bias": bias,
                    "signal": signal,
                    "data": data,
                }
                transitions.append(transition)
                append_history({
                    "ts": int(time.time()),
                    "asset": asset_id,
                    "from": from_label,
                    "to": curr_label,
                    "bias": bias,
                    "signal": signal,
                    "price": data["price"],
                    "px4h": data.get("priceChange4h"),
                    "px24h": data.get("priceChange24h"),
                    "oi4h": data.get("oiChange4h"),
                    "oi24h": data.get("oiChange24h"),
                    "funding": data.get("fundingRate"),
                })
                transition_logged = True

            new_state[asset_id] = {
                "label": curr_label,
                "bias": bias,
                "signal": signal,
                "ts": int(time.time()),
                "data": {
                    "price": data["price"],
                    "px24h": data.get("priceChange24h"),
                    "px4h":  data.get("priceChange4h"),
                    "oi24h": data.get("oiChange24h"),
                    "oi4h":  data.get("oiChange4h"),
                    "funding": data.get("fundingRate"),
                },
            }
            flag = " *" if transition_logged else ""
            print(f"  [OK] {asset_id:7s} {curr_label:18s} (era {prev_label or 'nuovo'}){flag}", flush=True)
        except Exception as e:
            errors.append(f"{asset_id}: {e}")
            print(f"  [X] {asset_id}: exception {e}", flush=True)

        time.sleep(0.25)

    save_json(STATE_FILE, new_state)

    if is_first_run:
        print(f"\n[INFO] First run: invio messaggio di startup con setup attivi", flush=True)
        # Lista i setup già attivi al lancio
        active_long = []
        active_short = []
        for aid, s in new_state.items():
            label = s.get("label", "")
            if label.startswith("LONG"):
                strength = label.split("_")[1] if "_" in label else ""
                active_long.append(f"  🟢 <b>{aid}</b> ({strength})")
            elif label.startswith("SHORT"):
                strength = label.split("_")[1] if "_" in label else ""
                active_short.append(f"  🔴 <b>{aid}</b> ({strength})")

        active_block = ""
        if active_long:
            active_block += "\n\n<b>📈 Setup LONG attivi:</b>\n" + "\n".join(active_long)
        if active_short:
            active_block += "\n\n<b>📉 Setup SHORT attivi:</b>\n" + "\n".join(active_short)
        if not active_long and not active_short:
            active_block = "\n\nNessun setup operativo attivo al momento."

        startup_msg = (
            f"🤖 <b>OI Monitor avviato</b>\n\n"
            f"Sto monitorando {len(ASSETS)} asset.\n"
            f"Stato iniziale salvato. Riceverai alert quando un asset:\n"
            f"• transita da NEUTRAL a LONG/SHORT\n"
            f"• flippa direzione (LONG↔SHORT)\n"
            f"• upgrade a forte (moderato→forte)"
            f"{active_block}\n\n"
            f"⏰ {datetime.now(timezone.utc).strftime('%H:%M UTC · %d/%m/%Y')}"
        )
        send_telegram(startup_msg)
    else:
        for t in transitions:
            send_telegram(format_transition_message(t))
            time.sleep(0.5)

    print(f"\n=== Riepilogo ===", flush=True)
    print(f"  Asset processati: {len(new_state)}/{len(ASSETS)}", flush=True)
    print(f"  Transizioni:      {len(transitions)}", flush=True)
    print(f"  Errori:           {len(errors)}", flush=True)
    if errors:
        for e in errors:
            print(f"    ! {e}", flush=True)
    if transitions:
        print(f"  Alert inviati:", flush=True)
        for t in transitions:
            print(f"    -> {t['asset']}: {t['from']} -> {t['to']}", flush=True)
    elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()
    print(f"  Durata: {elapsed:.1f}s\n", flush=True)


if __name__ == "__main__":
    main()
