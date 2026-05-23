#!/usr/bin/env python3
"""
OI Monitor — Coinalyze edition (rate-limit safe, OI 24h corretto).
"""

import os
import json
import time
from datetime import datetime, timezone

import requests

ASSETS = [
    {"id": "BTC",     "coinalyze": "BTCUSDT_PERP.A"},
    {"id": "ETH",     "coinalyze": "ETHUSDT_PERP.A"},
    {"id": "SOL",     "coinalyze": "SOLUSDT_PERP.A"},
    {"id": "LINK",    "coinalyze": "LINKUSDT_PERP.A"},
    {"id": "ICP",     "coinalyze": "ICPUSDT_PERP.A"},
    {"id": "SUI",     "coinalyze": "SUIUSDT_PERP.A"},
    {"id": "HBAR",    "coinalyze": "HBARUSDT_PERP.A"},
    {"id": "AR",      "coinalyze": "ARUSDT_PERP.A"},
    {"id": "TAO",     "coinalyze": "TAOUSDT_PERP.A"},
    {"id": "RENDER",  "coinalyze": "RENDERUSDT_PERP.A"},
    {"id": "VIRTUAL", "coinalyze": "VIRTUALUSDT_PERP.A"},
    {"id": "INJ",     "coinalyze": "INJUSDT_PERP.A"},
    {"id": "SEI",     "coinalyze": "SEIUSDT_PERP.A"},
    {"id": "ONDO",    "coinalyze": "ONDOUSDT_PERP.A"},
    {"id": "ENA",     "coinalyze": "ENAUSDT_PERP.A"},
    {"id": "JUP",     "coinalyze": "JUPUSDT_PERP.A"},
    {"id": "BONK",    "coinalyze": "1000BONKUSDT_PERP.A"},
    {"id": "PENGU",   "coinalyze": "PENGUUSDT_PERP.A"},
    {"id": "KAS",     "coinalyze": "KASUSDT_PERP.6"},
    {"id": "TRX",     "coinalyze": "TRXUSDT_PERP.A"},
    {"id": "TON",     "coinalyze": "TONUSDT_PERP.A"},
    {"id": "ROSE",    "coinalyze": "ROSEUSDT_PERP.A"},
    {"id": "NEAR",    "coinalyze": "NEARUSDT_PERP.A"},
    {"id": "FET",     "coinalyze": "FETUSDT_PERP.A"},
    {"id": "HYPE",    "coinalyze": "HYPEUSDT_PERP.A"},
    {"id": "STRK",    "coinalyze": "STRKUSDT_PERP.A"},
]

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

COINALYZE_BASE = "https://api.coinalyze.net/v1"
COINALYZE_KEY = os.environ.get("COINALYZE_API_KEY", "").strip()

TG_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
TG_CHAT  = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

HTTP_TIMEOUT = 25

BATCH_SIZE = 7
SLEEP_BETWEEN = 6
SLEEP_BETWEEN_BATCHES = 8


def coinalyze_get(path, params, max_retries=5):
    url = f"{COINALYZE_BASE}{path}"
    headers = {"api_key": COINALYZE_KEY}
    for attempt in range(max_retries):
        r = requests.get(url, params=params, headers=headers, timeout=HTTP_TIMEOUT)
        if r.status_code == 429:
            try:
                wait = int(r.headers.get("Retry-After", "10"))
            except (TypeError, ValueError):
                wait = 10
            wait = max(2, min(wait + 1, 60))
            print(f"[WARN] 429 su {path}, attendo {wait}s (tent. {attempt+1}/{max_retries})", flush=True)
            time.sleep(wait)
            continue
        if r.status_code != 200:
            raise Exception(f"Coinalyze {path} HTTP {r.status_code}: {r.text[:300]}")
        return r.json()
    raise Exception(f"Coinalyze {path}: rate-limit persistente dopo {max_retries} tentativi")


def _extract_history(item):
    if isinstance(item, dict):
        if "history" in item and isinstance(item["history"], list):
            return item["history"]
        if "data" in item and isinstance(item["data"], list):
            return item["data"]
    return []


def _symbol_of(item):
    if isinstance(item, dict):
        return item.get("symbol") or item.get("s") or item.get("sym")
    return None


def _chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def fetch_all_via_coinalyze():
    if not COINALYZE_KEY:
        raise Exception("COINALYZE_API_KEY non configurato nei secrets")

    now = int(time.time())
    # Window 25h: candle[0] close ≈ "24h fa"
    from_ts = now - 25 * 3600

    oi_by_sym = {}
    px_by_sym = {}
    fr_by_sym = {}

    all_assets = list(ASSETS)
    all_symbols_csv = ",".join(a["coinalyze"] for a in all_assets)

    # === FUNDING RATE (1 sola chiamata snapshot per tutti i 26 simboli) ===
    print(f"[INFO] Coinalyze funding-rate snapshot ({len(all_assets)} simboli)", flush=True)
    try:
        fr_resp = coinalyze_get("/funding-rate", {"symbols": all_symbols_csv})
        if isinstance(fr_resp, list):
            for item in fr_resp:
                sym = _symbol_of(item)
                if not sym:
                    continue
                val = item.get("value")
                if val is None: val = item.get("funding_rate")
                if val is None: val = item.get("rate")
                try:
                    fr_by_sym[sym] = float(val) if val is not None else 0.0
                except (TypeError, ValueError):
                    fr_by_sym[sym] = 0.0
    except Exception as e:
        print(f"[WARN] funding-rate globale fallito: {e} — funding=0 per tutti", flush=True)

    time.sleep(SLEEP_BETWEEN_BATCHES)

    # === HISTORY (OI + OHLCV) in batch da BATCH_SIZE simboli ===
    batches = list(_chunks(all_assets, BATCH_SIZE))
    print(f"[INFO] Coinalyze history fetch · {len(all_assets)} simboli in {len(batches)} batch da {BATCH_SIZE}", flush=True)

    for batch_idx, batch in enumerate(batches, 1):
        sym_csv = ",".join(a["coinalyze"] for a in batch)
        print(f"  [batch {batch_idx}/{len(batches)}] {sym_csv}", flush=True)

        oi_resp = coinalyze_get(
            "/open-interest-history",
            {"symbols": sym_csv, "interval": "1hour",
             "from": from_ts, "to": now, "convert_to_usd": "false"},
        )
        if isinstance(oi_resp, list):
            for item in oi_resp:
                sym = _symbol_of(item)
                if sym:
                    oi_by_sym[sym] = _extract_history(item)
        time.sleep(SLEEP_BETWEEN)

        px_resp = coinalyze_get(
            "/ohlcv-history",
            {"symbols": sym_csv, "interval": "1hour",
             "from": from_ts, "to": now},
        )
        if isinstance(px_resp, list):
            for item in px_resp:
                sym = _symbol_of(item)
                if sym:
                    px_by_sym[sym] = _extract_history(item)

        if batch_idx < len(batches):
            time.sleep(SLEEP_BETWEEN_BATCHES)

    # === Costruzione risultato per asset ===
    result = {}
    for asset in ASSETS:
        sym = asset["coinalyze"]
        aid = asset["id"]
        oi_hist = oi_by_sym.get(sym, [])
        px_hist = px_by_sym.get(sym, [])

        if not oi_hist or not px_hist:
            result[aid] = {"error": f"dati assenti su Coinalyze (sym={sym})"}
            continue

        try:
            oi_sorted = sorted(oi_hist, key=lambda x: x.get("t", x.get("time", 0)))
            px_sorted = sorted(px_hist, key=lambda x: x.get("t", x.get("time", 0)))

            def _close(c):
                return float(c.get("c", c.get("close", 0)))

            # Con window 25h: candle[0] close ≈ 24h fa, candle[-1] close ≈ ora
            current_oi  = _close(oi_sorted[-1])
            oi_24h_ago  = _close(oi_sorted[0])
            oi_4h_idx   = max(0, len(oi_sorted) - 5)
            oi_4h_ago   = _close(oi_sorted[oi_4h_idx])

            current_price = _close(px_sorted[-1])
            price_24h_ago = _close(px_sorted[0])
            px_4h_idx     = max(0, len(px_sorted) - 5)
            price_4h_ago  = _close(px_sorted[px_4h_idx])

            oi_change_24h    = ((current_oi - oi_24h_ago) / oi_24h_ago) * 100 if oi_24h_ago else None
            oi_change_4h     = ((current_oi - oi_4h_ago)  / oi_4h_ago)  * 100 if oi_4h_ago  else None
            price_change_24h = ((current_price - price_24h_ago) / price_24h_ago) * 100 if price_24h_ago else None
            price_change_4h  = ((current_price - price_4h_ago)  / price_4h_ago)  * 100 if price_4h_ago  else None

            funding_rate = fr_by_sym.get(sym, 0.0) * 100

            result[aid] = {
                "source": "Coinalyze",
                "source_symbol": sym,
                "price": current_price,
                "priceChange24h": price_change_24h,
                "priceChange4h": price_change_4h,
                "fundingRate": funding_rate,
                "currentOI": current_oi,
                "currentOI_USD": current_oi * current_price,
                "oiChange24h": oi_change_24h,
                "oiChange4h": oi_change_4h,
            }
        except Exception as e:
            result[aid] = {"error": f"parse error: {e}"}

    return result


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
    oi4  = d.get("oiChange4h")    or 0
    px4  = d.get("priceChange4h") or 0
    oi24 = d.get("oiChange24h")   or 0
    px24 = d.get("priceChange24h") or 0
    def sgn(x): return 1 if x > 0 else -1 if x < 0 else 0
    px4_s, px24_s = sgn(px4), sgn(px24)
    oi4_s, oi24_s = sgn(oi4), sgn(oi24)
    if abs(px4) < 0.5 and oi4 > 1.5: return "BUILD-UP"
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


def should_notify(prev_label, curr_label):
    if prev_label == curr_label: return False
    prev_a, prev_s = prev_label.split("_") if "_" in prev_label else (prev_label, "weak")
    curr_a, curr_s = curr_label.split("_") if "_" in curr_label else (curr_label, "weak")
    if prev_a == "NEUTRAL" and curr_a in ("LONG", "SHORT"): return True
    if (prev_a == "LONG" and curr_a == "SHORT") or (prev_a == "SHORT" and curr_a == "LONG"): return True
    if prev_a == curr_a and prev_a in ("LONG", "SHORT"):
        strengths = {"weak": 0, "moderate": 1, "strong": 2}
        if strengths.get(curr_s, 0) > strengths.get(prev_s, 0): return True
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


def _binance_symbol(coinalyze_sym):
    if not coinalyze_sym: return None
    return coinalyze_sym.split(".")[0].replace("_PERP", "")


def format_transition_message(t):
    asset = t["asset"]
    curr  = t["to"]
    prev  = t["from"]
    curr_a, curr_s = curr.split("_") if "_" in curr else (curr, "weak")
    emoji = {"LONG": "🟢", "SHORT": "🔴", "NEUTRAL": "⚪"}.get(curr_a, "⚪")
    strength_text = {"strong": "FORTE", "moderate": "moderato", "weak": "debole"}.get(curr_s, "")
    d = t["data"]
    sym = d.get("source_symbol", asset)
    tv_exchange = "BYBIT" if sym.endswith(".6") else "BINANCE"
    base_sym = _binance_symbol(sym) or asset
    tv_link = f"https://www.tradingview.com/chart/?symbol={tv_exchange}:{base_sym}.P"
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
        print("[WARN] Telegram non configurato", flush=True)
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


def load_json(path, default):
    if not os.path.exists(path): return default
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


def main():
    started_at = datetime.now(timezone.utc)
    print(f"\n=== OI Monitor — {started_at.isoformat()} ===", flush=True)

    last_state = load_json(STATE_FILE, {})
    is_first_run = not last_state
    new_state = {}
    transitions = []
    errors = []

    try:
        all_data = fetch_all_via_coinalyze()
    except Exception as e:
        print(f"[FATAL] Coinalyze fetch fallito: {e}", flush=True)
        send_telegram(
            f"⚠️ <b>OI Monitor errore</b>\n\n"
            f"Coinalyze fetch fallito:\n<code>{str(e)[:300]}</code>"
        )
        return

    for asset in ASSETS:
        asset_id = asset["id"]
        data = all_data.get(asset_id, {"error": "no data"})
        if data.get("error"):
            errors.append(f"{asset_id}: {data['error']}")
            print(f"  [X] {asset_id}: {data['error']}", flush=True)
            continue

        try:
            bias    = compute_bias(data)
            signal  = compute_signal_4h(data)
            action, strength = compute_action(bias, signal)
            curr_label = f"{action}_{strength}"

            prev_entry = last_state.get(asset_id, {})
            prev_label = prev_entry.get("label")

            transition_logged = False
            is_transition = prev_label and should_notify(prev_label, curr_label)
            is_new_active = (not prev_label) and (not is_first_run) and action in ("LONG", "SHORT")

            if is_transition or is_new_active:
                from_label = prev_label if is_transition else "NEW"
                transition = {
                    "ts": int(time.time()),
                    "asset": asset_id, "from": from_label, "to": curr_label,
                    "bias": bias, "signal": signal, "data": data,
                }
                transitions.append(transition)
                append_history({
                    "ts": int(time.time()),
                    "asset": asset_id, "from": from_label, "to": curr_label,
                    "bias": bias, "signal": signal,
                    "price": data["price"],
                    "px4h": data.get("priceChange4h"),
                    "px24h": data.get("priceChange24h"),
                    "oi4h": data.get("oiChange4h"),
                    "oi24h": data.get("oiChange24h"),
                    "funding": data.get("fundingRate"),
                })
                transition_logged = True

            new_state[asset_id] = {
                "label": curr_label, "bias": bias, "signal": signal,
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

    save_json(STATE_FILE, new_state)

    if is_first_run:
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
            f"Sto monitorando {len(ASSETS)} asset via <b>Coinalyze</b>.\n"
            f"Riceverai alert quando un asset:\n"
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
    elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()
    print(f"  Durata: {elapsed:.1f}s\n", flush=True)


if __name__ == "__main__":
    main()
