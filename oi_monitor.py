#!/usr/bin/env python3
"""
OI Monitor — Coinalyze edition con FVG/POC/EMA/OBV e confluenza.
"""

import os
import json
import time
from datetime import datetime, timezone
try:
    from zoneinfo import ZoneInfo
    ITALY_TZ = ZoneInfo("Europe/Rome")
except Exception:
    ITALY_TZ = None

import requests


def now_italy_str():
    if ITALY_TZ is not None:
        return datetime.now(ITALY_TZ).strftime("%H:%M · %d/%m/%Y")
    return datetime.now(timezone.utc).strftime("%H:%M UTC · %d/%m/%Y")


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
    {"id": "KAS",     "coinalyze": "KASUSDT.6"},
    {"id": "TRX",     "coinalyze": "TRXUSDT_PERP.A"},
    {"id": "TON",     "coinalyze": "TONUSDT_PERP.A"},
    {"id": "ROSE",    "coinalyze": "ROSEUSDT_PERP.A"},
    {"id": "NEAR",    "coinalyze": "NEARUSDT_PERP.A"},
    {"id": "FET",     "coinalyze": "FETUSDT_PERP.A"},
    {"id": "HYPE",    "coinalyze": "HYPEUSDT_PERP.A"},
    {"id": "STRK",    "coinalyze": "STRKUSDT_PERP.A"},
]

T = {
    "oi_expanding": 5, "oi_strong_exp": 10, "oi_contracting": -5, "oi_strong_contr": -10,
    "price_up": 2, "price_down": -2, "price_strong_up": 5, "price_strong_down": -5,
    "funding_high": 0.05, "funding_very_high": 0.08,
    "funding_negative": -0.01, "funding_very_neg": -0.03,
}

EMA_FAST_4H = 9
EMA_SLOW_4H = 21
EMA_MACRO_1D = 200

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


def _kline_val(k, key):
    return float(k.get(key, 0) or 0)


def compute_ema(closes, period):
    if not closes or len(closes) < period:
        return None
    k = 2.0 / (period + 1)
    seed = sum(closes[:period]) / period
    ema = seed
    for v in closes[period:]:
        ema = (v - ema) * k + ema
    return ema


def compute_trend(klines4h, klines1d, current_price):
    if not klines4h or len(klines4h) < EMA_SLOW_4H + 5:
        return None
    closes4h = [_kline_val(k, "c") for k in klines4h]
    ema_fast = compute_ema(closes4h, EMA_FAST_4H)
    ema_slow = compute_ema(closes4h, EMA_SLOW_4H)
    if ema_fast is None or ema_slow is None:
        return None
    ema_macro, ema_macro_period = None, None
    if klines1d and len(klines1d) >= EMA_MACRO_1D:
        closes1d = [_kline_val(k, "c") for k in klines1d]
        ema_macro = compute_ema(closes1d, EMA_MACRO_1D)
        ema_macro_period = EMA_MACRO_1D
    elif klines1d and len(klines1d) >= 50:
        closes1d = [_kline_val(k, "c") for k in klines1d]
        ema_macro = compute_ema(closes1d, 50)
        ema_macro_period = 50
    fast_vs_slow = ema_fast > ema_slow
    above_macro = (current_price > ema_macro) if ema_macro else None
    if fast_vs_slow and above_macro is True:
        label = "TREND UP"
    elif (not fast_vs_slow) and above_macro is False:
        label = "TREND DOWN"
    elif above_macro is True and not fast_vs_slow:
        label = "PULLBACK UP"
    elif above_macro is False and fast_vs_slow:
        label = "PULLBACK DOWN"
    else:
        label = "CHOP"
    return {"label": label, "emaFast": ema_fast, "emaSlow": ema_slow,
            "emaMacro": ema_macro, "emaMacroPeriod": ema_macro_period,
            "fastVsSlow": fast_vs_slow, "aboveMacro": above_macro}


def compute_obv(klines, lookback=50):
    if not klines or len(klines) < lookback + 1:
        return None
    obv = 0.0
    series = []
    for i in range(1, len(klines)):
        close = _kline_val(klines[i], "c")
        prev_close = _kline_val(klines[i-1], "c")
        vol = _kline_val(klines[i], "v")
        if close > prev_close: obv += vol
        elif close < prev_close: obv -= vol
        series.append({"obv": obv, "close": close})
    recent = series[-min(lookback, len(series)):]
    if len(recent) < 5:
        return None
    obv_start, obv_end = recent[0]["obv"], recent[-1]["obv"]
    price_start, price_end = recent[0]["close"], recent[-1]["close"]
    obv_change = ((obv_end - obv_start) / abs(obv_start)) * 100 if obv_start != 0 else 0
    price_change = ((price_end - price_start) / price_start) * 100 if price_start else 0
    obv_dir = 1 if obv_change > 0 else (-1 if obv_change < 0 else 0)
    price_dir = 1 if price_change > 0 else (-1 if price_change < 0 else 0)
    diverge = (obv_dir != price_dir and obv_dir != 0 and price_dir != 0
               and abs(obv_change) > 5 and abs(price_change) > 2)
    return {"obvChange": obv_change, "priceChange": price_change,
            "diverge": diverge, "direction": obv_dir}


def compute_rvol(klines, lookback=20):
    if not klines or len(klines) < lookback + 1:
        return None
    tail = klines[-lookback - 1:]
    vols = [_kline_val(k, "v") for k in tail]
    current = vols[-1]
    avg = sum(vols[:lookback]) / lookback
    if avg <= 0:
        return None
    return {"ratio": current / avg, "current": current, "avg": avg}


def detect_fvgs(klines, current_price):
    if not klines or len(klines) < 3:
        return {"above": None, "below": None, "count": 0}
    unfilled = []
    for i in range(2, len(klines)):
        h0 = _kline_val(klines[i-2], "h")
        l0 = _kline_val(klines[i-2], "l")
        h2 = _kline_val(klines[i], "h")
        l2 = _kline_val(klines[i], "l")
        if h0 < l2:
            filled = any(_kline_val(klines[j], "l") <= h0 for j in range(i+1, len(klines)))
            if not filled:
                unfilled.append({"type": "bull", "top": l2, "bottom": h0,
                                 "size": ((l2 - h0) / h0) * 100 if h0 > 0 else 0})
        if l0 > h2:
            filled = any(_kline_val(klines[j], "h") >= l0 for j in range(i+1, len(klines)))
            if not filled:
                unfilled.append({"type": "bear", "top": l0, "bottom": h2,
                                 "size": ((l0 - h2) / h2) * 100 if h2 > 0 else 0})
    above_candidates = [f for f in unfilled if f["bottom"] > current_price]
    below_candidates = [f for f in unfilled if f["top"] < current_price]
    above_candidates.sort(key=lambda x: x["bottom"])
    below_candidates.sort(key=lambda x: -x["top"])
    above = above_candidates[0] if above_candidates else None
    below = below_candidates[0] if below_candidates else None
    if above:
        above["distance"] = ((above["bottom"] - current_price) / current_price) * 100 if current_price else 0
    if below:
        below["distance"] = ((below["top"] - current_price) / current_price) * 100 if current_price else 0
    return {"above": above, "below": below, "count": len(unfilled)}


def compute_poc_swing(klines, current_price, lookback_bars=126):
    if not klines or len(klines) < 10:
        return None
    n = min(lookback_bars, len(klines))
    slice_ = klines[-n:]
    range_high, range_low = float("-inf"), float("inf")
    for k in slice_:
        h = _kline_val(k, "h"); l = _kline_val(k, "l")
        if h > range_high: range_high = h
        if l < range_low: range_low = l
    if range_high <= range_low:
        return None
    BUCKETS = 100
    bucket_size = (range_high - range_low) / BUCKETS
    volumes = [0.0] * BUCKETS
    for k in slice_:
        h = _kline_val(k, "h"); l = _kline_val(k, "l"); v = _kline_val(k, "v")
        if v <= 0: continue
        ch = min(h, range_high); cl = max(l, range_low)
        if ch <= cl: continue
        sb = max(0, int((cl - range_low) / bucket_size))
        eb = min(BUCKETS - 1, int((ch - range_low) / bucket_size))
        nb = eb - sb + 1
        vpb = v / nb
        for b in range(sb, eb + 1):
            volumes[b] += vpb
    max_vol = 0; poc_idx = 0
    for i, v in enumerate(volumes):
        if v > max_vol:
            max_vol = v; poc_idx = i
    poc = range_low + (poc_idx + 0.5) * bucket_size
    total_vol = sum(volumes)
    if total_vol <= 0: return None
    target = total_vol * 0.7
    covered = max_vol
    lo = poc_idx; hi = poc_idx
    while covered < target and (lo > 0 or hi < BUCKETS - 1):
        lv = volumes[lo - 1] if lo > 0 else -1
        uv = volumes[hi + 1] if hi < BUCKETS - 1 else -1
        if lv >= uv:
            lo -= 1; covered += volumes[lo]
        else:
            hi += 1; covered += volumes[hi]
    val = range_low + lo * bucket_size
    vah = range_low + (hi + 1) * bucket_size
    return {"poc": poc, "vah": vah, "val": val,
            "rangeHigh": range_high, "rangeLow": range_low,
            "distance": ((poc - current_price) / current_price) * 100 if current_price else 0,
            "inValueArea": current_price >= val and current_price <= vah}


def fetch_all_via_coinalyze():
    if not COINALYZE_KEY:
        raise Exception("COINALYZE_API_KEY non configurato nei secrets")
    now = int(time.time())
    from_ts = now - 25 * 3600
    oi_by_sym = {}; px_by_sym = {}; fr_by_sym = {}
    all_assets = list(ASSETS)
    all_symbols_csv = ",".join(a["coinalyze"] for a in all_assets)

    print(f"[INFO] Coinalyze funding-rate snapshot ({len(all_assets)} simboli)", flush=True)
    try:
        fr_resp = coinalyze_get("/funding-rate", {"symbols": all_symbols_csv})
        if isinstance(fr_resp, list):
            for item in fr_resp:
                sym = _symbol_of(item)
                if not sym: continue
                val = item.get("value")
                if val is None: val = item.get("funding_rate")
                if val is None: val = item.get("rate")
                try:
                    fr_by_sym[sym] = float(val) if val is not None else 0.0
                except (TypeError, ValueError):
                    fr_by_sym[sym] = 0.0
    except Exception as e:
        print(f"[WARN] funding-rate globale fallito: {e}", flush=True)
    time.sleep(SLEEP_BETWEEN_BATCHES)

    lsr_by_sym = {}
    lsr_batches = list(_chunks(all_assets, BATCH_SIZE))
    print(f"[INFO] Coinalyze long/short ratio · {len(lsr_batches)} batch", flush=True)
    for batch_idx, batch in enumerate(lsr_batches, 1):
        sym_csv = ",".join(a["coinalyze"] for a in batch)
        try:
            lsr_resp = coinalyze_get("/long-short-ratio-history",
                {"symbols": sym_csv, "interval": "4hour",
                 "from": now - 8*3600, "to": now})
            if isinstance(lsr_resp, list):
                for item in lsr_resp:
                    sym = _symbol_of(item)
                    if not sym: continue
                    hist = _extract_history(item)
                    if hist:
                        last = max(hist, key=lambda x: x.get("t", 0))
                        ratio_global = last.get("r") or last.get("ratio")
                        ratio_top = last.get("tr") or last.get("top_trader_ratio")
                        lsr_by_sym[sym] = {
                            "global": float(ratio_global) if ratio_global is not None else None,
                            "top": float(ratio_top) if ratio_top is not None else None,
                        }
        except Exception as e:
            print(f"  [WARN] L/S batch {batch_idx}: {e}", flush=True)
        if batch_idx < len(lsr_batches):
            time.sleep(SLEEP_BETWEEN)
    time.sleep(SLEEP_BETWEEN_BATCHES)

    batches = list(_chunks(all_assets, BATCH_SIZE))
    print(f"[INFO] Coinalyze history (OI+OHLCV 1h) · {len(batches)} batch", flush=True)
    for batch_idx, batch in enumerate(batches, 1):
        sym_csv = ",".join(a["coinalyze"] for a in batch)
        try:
            oi_resp = coinalyze_get("/open-interest-history",
                {"symbols": sym_csv, "interval": "1hour",
                 "from": from_ts, "to": now, "convert_to_usd": "false"})
            for item in (oi_resp or []):
                sym = _symbol_of(item)
                if sym: oi_by_sym[sym] = _extract_history(item)
        except Exception as e:
            print(f"  [WARN] OI batch {batch_idx}: {e}", flush=True)
        time.sleep(SLEEP_BETWEEN)
        try:
            px_resp = coinalyze_get("/ohlcv-history",
                {"symbols": sym_csv, "interval": "1hour",
                 "from": from_ts, "to": now})
            for item in (px_resp or []):
                sym = _symbol_of(item)
                if sym: px_by_sym[sym] = _extract_history(item)
        except Exception as e:
            print(f"  [WARN] OHLCV batch {batch_idx}: {e}", flush=True)
        if batch_idx < len(batches):
            time.sleep(SLEEP_BETWEEN_BATCHES)

    time.sleep(SLEEP_BETWEEN_BATCHES)
    klines4h_by_sym = {}
    print(f"[INFO] Coinalyze klines 4h · {len(batches)} batch", flush=True)
    from_ts_4h = now - 130 * 4 * 3600
    for batch_idx, batch in enumerate(batches, 1):
        sym_csv = ",".join(a["coinalyze"] for a in batch)
        try:
            resp = coinalyze_get("/ohlcv-history",
                {"symbols": sym_csv, "interval": "4hour",
                 "from": from_ts_4h, "to": now})
            for item in (resp or []):
                sym = _symbol_of(item)
                if sym:
                    klines4h_by_sym[sym] = sorted(_extract_history(item), key=lambda x: x.get("t", 0))
        except Exception as e:
            print(f"  [WARN] klines 4h batch {batch_idx}: {e}", flush=True)
        if batch_idx < len(batches):
            time.sleep(SLEEP_BETWEEN)

    time.sleep(SLEEP_BETWEEN_BATCHES)
    klines1d_by_sym = {}
    print(f"[INFO] Coinalyze klines 1d · {len(batches)} batch", flush=True)
    from_ts_1d = now - 250 * 86400
    for batch_idx, batch in enumerate(batches, 1):
        sym_csv = ",".join(a["coinalyze"] for a in batch)
        try:
            resp = coinalyze_get("/ohlcv-history",
                {"symbols": sym_csv, "interval": "daily",
                 "from": from_ts_1d, "to": now})
            for item in (resp or []):
                sym = _symbol_of(item)
                if sym:
                    klines1d_by_sym[sym] = sorted(_extract_history(item), key=lambda x: x.get("t", 0))
        except Exception as e:
            print(f"  [WARN] klines 1d batch {batch_idx}: {e}", flush=True)
        if batch_idx < len(batches):
            time.sleep(SLEEP_BETWEEN)

    result = {}
    for asset in ASSETS:
        sym = asset["coinalyze"]; aid = asset["id"]
        oi_hist = oi_by_sym.get(sym, []); px_hist = px_by_sym.get(sym, [])
        if not oi_hist or not px_hist:
            result[aid] = {"error": f"dati assenti su Coinalyze (sym={sym})"}
            continue
        try:
            oi_sorted = sorted(oi_hist, key=lambda x: x.get("t", x.get("time", 0)))
            px_sorted = sorted(px_hist, key=lambda x: x.get("t", x.get("time", 0)))
            def _close(c): return float(c.get("c", c.get("close", 0)))
            current_oi = _close(oi_sorted[-1])
            oi_24h_ago = _close(oi_sorted[0])
            oi_4h_ago = _close(oi_sorted[max(0, len(oi_sorted) - 5)])
            current_price = _close(px_sorted[-1])
            price_24h_ago = _close(px_sorted[0])
            price_4h_ago = _close(px_sorted[max(0, len(px_sorted) - 5)])
            oi_change_24h = ((current_oi - oi_24h_ago) / oi_24h_ago) * 100 if oi_24h_ago else None
            oi_change_4h = ((current_oi - oi_4h_ago) / oi_4h_ago) * 100 if oi_4h_ago else None
            price_change_24h = ((current_price - price_24h_ago) / price_24h_ago) * 100 if price_24h_ago else None
            price_change_4h = ((current_price - price_4h_ago) / price_4h_ago) * 100 if price_4h_ago else None
            funding_rate = fr_by_sym.get(sym, 0.0) * 100
            lsr = lsr_by_sym.get(sym, {})
            lsr_global = lsr.get("global"); lsr_top = lsr.get("top")
            lsr_spread = (lsr_top - lsr_global) if (lsr_top is not None and lsr_global is not None) else None
            k4h = klines4h_by_sym.get(sym, []); k1d = klines1d_by_sym.get(sym, [])
            trend = compute_trend(k4h, k1d, current_price)
            obv = compute_obv(k4h, lookback=50)
            rvol = compute_rvol(k4h, lookback=20)
            fvg = detect_fvgs(k4h, current_price)
            poc = compute_poc_swing(k4h, current_price, lookback_bars=126)
            result[aid] = {
                "source": "Coinalyze", "source_symbol": sym,
                "price": current_price,
                "priceChange24h": price_change_24h, "priceChange4h": price_change_4h,
                "fundingRate": funding_rate,
                "currentOI": current_oi, "currentOI_USD": current_oi * current_price,
                "oiChange24h": oi_change_24h, "oiChange4h": oi_change_4h,
                "lsrGlobal": lsr_global, "lsrTop": lsr_top, "lsrSpread": lsr_spread,
                "trend": trend, "obv": obv, "rvol": rvol, "fvg": fvg, "poc": poc,
            }
        except Exception as e:
            result[aid] = {"error": f"parse error: {e}"}
    return result


def compute_bias(d):
    oi = d.get("oiChange24h") or 0; px = d.get("priceChange24h") or 0; fr = d.get("fundingRate") or 0
    f_v_high = fr > T["funding_very_high"]; f_neg = fr < T["funding_negative"]; f_v_neg = fr < T["funding_very_neg"]
    oi_exp = oi > T["oi_expanding"]; oi_str_exp = oi > T["oi_strong_exp"]
    oi_contr = oi < T["oi_contracting"]; oi_str_contr = oi < T["oi_strong_contr"]
    px_up = px > T["price_up"]; px_str_up = px > T["price_strong_up"]
    px_down = px < T["price_down"]; px_str_down = px < T["price_strong_down"]
    px_flat = abs(px) < 1.5
    if px_str_down and oi_str_contr and f_neg: return "CAPITULATION"
    if px_up and oi_exp and f_v_high: return "OVERHEATED LONG"
    if px_up and oi_exp: return "BULLISH SOLIDO"
    if px_up and oi_contr: return "SHORT SQUEEZE"
    if px_down and oi_exp: return "BEARISH AGGRESSIVO"
    if px_down and oi_contr: return "BEAR EXHAUSTION"
    if px_flat and oi_str_exp: return "PRESSURE BUILDUP"
    if f_v_neg and not px_str_down: return "SHORT CROWDED"
    if f_v_high and not px_str_up: return "LONG CROWDED"
    return "NEUTRAL"


def compute_signal_4h(d):
    oi4 = d.get("oiChange4h") or 0; px4 = d.get("priceChange4h") or 0
    oi24 = d.get("oiChange24h") or 0; px24 = d.get("priceChange24h") or 0
    def sgn(x): return 1 if x > 0 else -1 if x < 0 else 0
    px4_s, px24_s = sgn(px4), sgn(px24); oi4_s, oi24_s = sgn(oi4), sgn(oi24)
    if abs(px4) < 0.5 and oi4 > 1.5: return "BUILD-UP"
    px_div = abs(px4) > 0.8 and abs(px24) > 1 and px4_s != 0 and px24_s != 0 and px4_s != px24_s
    oi_div = abs(oi4) > 1.5 and abs(oi24) > 2 and oi4_s != 0 and oi24_s != 0 and oi4_s != oi24_s
    if px_div and oi_div: return "REVERSAL"
    if oi_div: return "OI GIRA"
    if px_div: return "PULLBACK"
    px_conf = px4_s == px24_s and px4_s != 0 and abs(px4) > 0.5
    oi_conf = oi4_s == oi24_s and oi4_s != 0 and abs(oi4) > 1.5
    if px_conf and oi_conf: return "CONFERMA"
    if px_conf or oi_conf: return "PARZIALE"
    return "PIATTO"


def compute_action(bias, signal_4h):
    B, S = bias, signal_4h
    if B == "BULLISH SOLIDO" and S == "CONFERMA": return ("LONG", "strong")
    if B == "BULLISH SOLIDO" and S in ("BUILD-UP", "PARZIALE", "PULLBACK"): return ("LONG", "moderate")
    if B == "PRESSURE BUILDUP" and S in ("CONFERMA", "BUILD-UP"): return ("LONG", "moderate")
    if B == "CAPITULATION" and S in ("REVERSAL", "OI GIRA"): return ("LONG", "strong")
    if B == "BEAR EXHAUSTION" and S in ("REVERSAL", "OI GIRA"): return ("LONG", "moderate")
    if B == "SHORT CROWDED" and S == "REVERSAL": return ("LONG", "strong")
    if B == "SHORT CROWDED" and S == "OI GIRA": return ("LONG", "moderate")
    if B == "BEARISH AGGRESSIVO" and S == "OI GIRA": return ("LONG", "moderate")
    if B == "BEARISH AGGRESSIVO" and S == "CONFERMA": return ("SHORT", "strong")
    if B == "BEARISH AGGRESSIVO" and S in ("PARZIALE", "PULLBACK"): return ("SHORT", "moderate")
    if B == "OVERHEATED LONG" and S == "REVERSAL": return ("SHORT", "strong")
    if B == "OVERHEATED LONG" and S == "OI GIRA": return ("SHORT", "moderate")
    if B == "LONG CROWDED" and S == "REVERSAL": return ("SHORT", "strong")
    if B == "LONG CROWDED" and S == "OI GIRA": return ("SHORT", "moderate")
    if B == "SHORT SQUEEZE" and S == "REVERSAL": return ("SHORT", "moderate")
    if B == "BULLISH SOLIDO" and S == "REVERSAL": return ("SHORT", "weak")
    if B == "PRESSURE BUILDUP" and S == "REVERSAL": return ("SHORT", "weak")
    return ("NEUTRAL", "weak")


def compute_action_with_confluence(bias, signal_4h, trend, obv, fvg, poc, current_price):
    base_action, _ = compute_action(bias, signal_4h)
    if base_action == "NEUTRAL":
        return ("NEUTRAL", "weak", 0, 0)
    direction = base_action
    score = 0; total = 0
    if trend and trend.get("label"):
        total += 1
        if direction == "LONG" and trend["label"] in ("TREND UP", "PULLBACK UP"): score += 1
        elif direction == "SHORT" and trend["label"] in ("TREND DOWN", "PULLBACK DOWN"): score += 1
    if trend and trend.get("aboveMacro") is not None:
        total += 1
        if direction == "LONG" and trend["aboveMacro"]: score += 1
        elif direction == "SHORT" and not trend["aboveMacro"]: score += 1
    if obv:
        total += 1
        if direction == "LONG" and obv.get("direction", 0) == 1: score += 1
        elif direction == "SHORT" and obv.get("direction", 0) == -1: score += 1
    if fvg and (fvg.get("above") or fvg.get("below")):
        total += 1
        if direction == "LONG" and fvg.get("below"): score += 1
        elif direction == "SHORT" and fvg.get("above"): score += 1
    if poc and poc.get("poc") and current_price:
        total += 1
        if direction == "LONG" and current_price > poc["poc"]: score += 1
        elif direction == "SHORT" and current_price < poc["poc"]: score += 1
    if total == 0:
        _, base_strength = compute_action(bias, signal_4h)
        return (direction, base_strength, 0, 0)
    if score >= 5 and total >= 5: strength = "full"
    elif score >= 4: strength = "strong"
    elif score >= 3: strength = "moderate"
    else: return ("NEUTRAL", "weak", score, total)
    return (direction, strength, score, total)


def should_notify(prev_label, curr_label):
    if prev_label == curr_label: return False
    prev_a, prev_s = prev_label.split("_") if "_" in prev_label else (prev_label, "weak")
    curr_a, curr_s = curr_label.split("_") if "_" in curr_label else (curr_label, "weak")
    if prev_a == "NEUTRAL" and curr_a in ("LONG", "SHORT"): return True
    if (prev_a == "LONG" and curr_a == "SHORT") or (prev_a == "SHORT" and curr_a == "LONG"): return True
    if prev_a == curr_a and prev_a in ("LONG", "SHORT"):
        strengths = {"weak": 0, "moderate": 1, "strong": 2, "full": 3}
        if strengths.get(curr_s, 0) > strengths.get(prev_s, 0): return True
    return False


def fmt_price(p):
    if p is None: return "-"
    if p >= 1000: return f"${p:,.0f}"
    if p >= 1: return f"${p:.2f}"
    if p >= 0.01: return f"${p:.4f}"
    return f"${p:.6f}"


def fmt_pct(p, sig=2):
    if p is None: return "-"
    s = "+" if p > 0 else ""
    return f"{s}{p:.{sig}f}%"


def _binance_symbol(coinalyze_sym):
    if not coinalyze_sym: return None
    return coinalyze_sym.split(".")[0].replace("_PERP", "")


def _build_other_active(state, exclude_asset):
    longs = []; shorts = []
    for aid, s in state.items():
        if aid == exclude_asset: continue
        label = s.get("label", "")
        if label.startswith("LONG"):
            strength = label.split("_")[1] if "_" in label else ""
            longs.append((aid, strength))
        elif label.startswith("SHORT"):
            strength = label.split("_")[1] if "_" in label else ""
            shorts.append((aid, strength))
    return longs, shorts


def format_transition_message(t, other_active_state=None):
    asset = t["asset"]; curr = t["to"]; prev = t["from"]
    curr_a, curr_s = curr.split("_") if "_" in curr else (curr, "weak")
    strength_text_map = {"full": "PIENA", "strong": "FORTE", "moderate": "moderata", "weak": "debole"}
    emoji = {"LONG": "🟢", "SHORT": "🔴", "NEUTRAL": "⚪"}.get(curr_a, "⚪")
    strength_text = strength_text_map.get(curr_s, "")
    d = t["data"]; sym = d.get("source_symbol", asset)
    tv_exchange = "BYBIT" if sym.endswith(".6") else "BINANCE"
    base_sym = _binance_symbol(sym) or asset
    tv_link = f"https://www.tradingview.com/chart/?symbol={tv_exchange}:{base_sym}.P"

    lsr_block = ""
    lsr_global = d.get("lsrGlobal"); lsr_top = d.get("lsrTop"); lsr_spread = d.get("lsrSpread")
    if lsr_top is not None and lsr_global is not None:
        spread_sign = "+" if lsr_spread >= 0 else ""
        conferma = ""
        if curr_a == "LONG" and lsr_spread > 0.3: conferma = " ✅"
        elif curr_a == "SHORT" and lsr_spread < -0.3: conferma = " ✅"
        elif curr_a == "LONG" and lsr_spread < -0.3: conferma = " ⚠️"
        elif curr_a == "SHORT" and lsr_spread > 0.3: conferma = " ⚠️"
        lsr_block = f"<b>L/S Top:</b> {lsr_top:.2f} · Global {lsr_global:.2f} · Δ {spread_sign}{lsr_spread:.2f}{conferma}\n"

    tech_block = ""
    trend = d.get("trend"); obv = d.get("obv"); rvol = d.get("rvol"); fvg = d.get("fvg"); poc = d.get("poc")
    if trend and trend.get("label"):
        tech_block += f"<b>Trend:</b> {trend['label']}"
        if trend.get("emaMacroPeriod"): tech_block += f" (EMA{trend['emaMacroPeriod']} 1D)"
        tech_block += "\n"
    if obv:
        obv_dir = "↑" if obv.get("direction", 0) == 1 else "↓" if obv.get("direction", 0) == -1 else "→"
        div_flag = " ⚠️ div" if obv.get("diverge") else ""
        tech_block += f"<b>OBV:</b> {obv_dir} {fmt_pct(obv.get('obvChange'), 1)}{div_flag}\n"
    if rvol and rvol.get("ratio"):
        tech_block += f"<b>RVOL:</b> {rvol['ratio']:.2f}x\n"
    if fvg:
        fvg_parts = []
        if fvg.get("below"): fvg_parts.append(f"sotto a {fmt_pct(fvg['below']['distance'], 1)}")
        if fvg.get("above"): fvg_parts.append(f"sopra a {fmt_pct(fvg['above']['distance'], 1)}")
        if fvg_parts:
            tech_block += f"<b>FVG 4h:</b> {' · '.join(fvg_parts)}\n"
    if poc and poc.get("poc"):
        in_va = " (in value area)" if poc.get("inValueArea") else ""
        tech_block += f"<b>POC:</b> {fmt_price(poc['poc'])} · Δ {fmt_pct(poc.get('distance'), 1)}{in_va}\n"
    confluence = t.get("confluence")
    if confluence:
        score = confluence.get("score", 0); total = confluence.get("total", 0)
        if total > 0:
            tech_block += f"<b>📊 Confluenza:</b> {score}/{total} indicatori d'accordo\n"

    msg = (
        f"{emoji} <b>{curr_a} {strength_text}</b> · <b>{asset}</b>\n"
        f"🕐 <b>Rilevato:</b> {now_italy_str()}\n\n"
        f"<b>Prezzo:</b> {fmt_price(d['price'])}\n"
        f"  Δ 4h:  {fmt_pct(d.get('priceChange4h'))}\n"
        f"  Δ 24h: {fmt_pct(d.get('priceChange24h'))}\n\n"
        f"<b>OI:</b>\n"
        f"  Δ 4h:  {fmt_pct(d.get('oiChange4h'))}\n"
        f"  Δ 24h: {fmt_pct(d.get('oiChange24h'))}\n\n"
        f"<b>Funding:</b> {fmt_pct(d.get('fundingRate'), 4)} (8h)\n"
        f"{lsr_block}"
        f"<b>Bias 24h:</b> {t['bias']}\n"
        f"<b>Signal 4h:</b> {t['signal']}\n\n"
        f"<b>━ Indicatori tecnici ━</b>\n"
        f"{tech_block}"
        f"\n<b>Transizione:</b> {prev} → {curr}\n"
        f"🔍 <a href=\"{tv_link}\">TradingView</a>"
    )

    if other_active_state is not None:
        longs, shorts = _build_other_active(other_active_state, asset)
        if longs or shorts:
            strength_short = {"full": "FULL", "strong": "F", "moderate": "M", "weak": "D"}
            msg += "\n\n<b>📊 Altre posizioni attive:</b>"
            if longs:
                items = [f"{aid} ({strength_short.get(s, s)})" for aid, s in longs]
                msg += "\n  🟢 LONG: " + ", ".join(items)
            if shorts:
                items = [f"{aid} ({strength_short.get(s, s)})" for aid, s in shorts]
                msg += "\n  🔴 SHORT: " + ", ".join(items)
        else:
            msg += "\n\n<i>📊 Nessun'altra posizione attiva.</i>"
    return msg


def send_telegram(text):
    if not TG_TOKEN or not TG_CHAT:
        print("[WARN] Telegram non configurato", flush=True)
        return False
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={
            "chat_id": TG_CHAT, "text": text,
            "parse_mode": "HTML", "disable_web_page_preview": True,
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
    new_state = {}; transitions = []; errors = []
    try:
        all_data = fetch_all_via_coinalyze()
    except Exception as e:
        print(f"[FATAL] Coinalyze fetch fallito: {e}", flush=True)
        send_telegram(f"⚠️ <b>OI Monitor errore</b>\n\nCoinalyze fetch fallito:\n<code>{str(e)[:300]}</code>")
        return

    for asset in ASSETS:
        asset_id = asset["id"]
        data = all_data.get(asset_id, {"error": "no data"})
        if data.get("error"):
            errors.append(f"{asset_id}: {data['error']}")
            print(f"  [X] {asset_id}: {data['error']}", flush=True)
            continue
        try:
            bias = compute_bias(data); signal = compute_signal_4h(data)
            action, strength, conf_score, conf_total = compute_action_with_confluence(
                bias, signal,
                data.get("trend"), data.get("obv"),
                data.get("fvg"), data.get("poc"),
                data.get("price"))
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
                    "confluence": {"score": conf_score, "total": conf_total},
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
                    "confluence_score": conf_score,
                    "confluence_total": conf_total,
                })
                transition_logged = True
            new_state[asset_id] = {
                "label": curr_label, "bias": bias, "signal": signal,
                "ts": int(time.time()),
                "confluence": {"score": conf_score, "total": conf_total},
                "data": {
                    "price": data["price"],
                    "px24h": data.get("priceChange24h"),
                    "px4h": data.get("priceChange4h"),
                    "oi24h": data.get("oiChange24h"),
                    "oi4h": data.get("oiChange4h"),
                    "funding": data.get("fundingRate"),
                    "lsrTop": data.get("lsrTop"),
                    "lsrGlobal": data.get("lsrGlobal"),
                    "lsrSpread": data.get("lsrSpread"),
                    "trend": data.get("trend"),
                    "obv": data.get("obv"),
                    "rvol": data.get("rvol"),
                    "fvg": data.get("fvg"),
                    "poc": data.get("poc"),
                },
            }
            flag = " *" if transition_logged else ""
            print(f"  [OK] {asset_id:7s} {curr_label:18s} (era {prev_label or 'nuovo'}){flag}", flush=True)
        except Exception as e:
            errors.append(f"{asset_id}: {e}")
            print(f"  [X] {asset_id}: exception {e}", flush=True)

    save_json(STATE_FILE, new_state)

    if is_first_run:
        active_long = []; active_short = []
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
            f"🤖 <b>OI Monitor avviato</b>\n"
            f"🕐 {now_italy_str()}\n\n"
            f"Sto monitorando {len(ASSETS)} asset via <b>Coinalyze</b>.\n"
            f"Riceverai alert quando un asset:\n"
            f"• transita da NEUTRAL a LONG/SHORT\n"
            f"• flippa direzione (LONG↔SHORT)\n"
            f"• upgrade a forte (moderato→forte)"
            f"{active_block}"
        )
        send_telegram(startup_msg)
    else:
        for t in transitions:
            send_telegram(format_transition_message(t, other_active_state=new_state))
            time.sleep(0.5)

    print(f"\n=== Riepilogo ===", flush=True)
    print(f"  Asset processati: {len(new_state)}/{len(ASSETS)}", flush=True)
    print(f"  Transizioni:      {len(transitions)}", flush=True)
    print(f"  Errori:           {len(errors)}", flush=True)
    if errors:
        for e in errors: print(f"    ! {e}", flush=True)
    elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()
    print(f"  Durata: {elapsed:.1f}s\n", flush=True)


if __name__ == "__main__":
    main()
