#!/usr/bin/env python3
"""OI Monitor — Coinalyze + tier + EMA 12/50 + scoring pesato + delta + filtri contro-trend."""

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
    {"id": "BTC", "coinalyze": "BTCUSDT_PERP.A", "binance": "BTCUSDT"},
    {"id": "ETH", "coinalyze": "ETHUSDT_PERP.A", "binance": "ETHUSDT"},
    {"id": "SOL", "coinalyze": "SOLUSDT_PERP.A", "binance": "SOLUSDT"},
    {"id": "LINK", "coinalyze": "LINKUSDT_PERP.A", "binance": "LINKUSDT"},
    {"id": "ICP", "coinalyze": "ICPUSDT_PERP.A", "binance": "ICPUSDT"},
    {"id": "SUI", "coinalyze": "SUIUSDT_PERP.A", "binance": "SUIUSDT"},
    {"id": "HBAR", "coinalyze": "HBARUSDT_PERP.A", "binance": "HBARUSDT"},
    {"id": "AR", "coinalyze": "ARUSDT_PERP.A", "binance": "ARUSDT"},
    {"id": "TAO", "coinalyze": "TAOUSDT_PERP.A", "binance": "TAOUSDT"},
    {"id": "RENDER", "coinalyze": "RENDERUSDT_PERP.A", "binance": "RENDERUSDT"},
    {"id": "VIRTUAL", "coinalyze": "VIRTUALUSDT_PERP.A", "binance": "VIRTUALUSDT"},
    {"id": "INJ", "coinalyze": "INJUSDT_PERP.A", "binance": "INJUSDT"},
    {"id": "SEI", "coinalyze": "SEIUSDT_PERP.A", "binance": "SEIUSDT"},
    {"id": "ONDO", "coinalyze": "ONDOUSDT_PERP.A", "binance": "ONDOUSDT"},
    {"id": "ENA", "coinalyze": "ENAUSDT_PERP.A", "binance": "ENAUSDT"},
    {"id": "JUP", "coinalyze": "JUPUSDT_PERP.A", "binance": "JUPUSDT"},
    {"id": "BONK", "coinalyze": "1000BONKUSDT_PERP.A", "binance": "1000BONKUSDT"},
    {"id": "PENGU", "coinalyze": "PENGUUSDT_PERP.A", "binance": "PENGUUSDT"},
    {"id": "KAS", "coinalyze": "KASUSDT.6", "binance": None},
    {"id": "TRX", "coinalyze": "TRXUSDT_PERP.A", "binance": "TRXUSDT"},
    {"id": "TON", "coinalyze": "TONUSDT_PERP.A", "binance": "TONUSDT"},
    {"id": "ROSE", "coinalyze": "ROSEUSDT_PERP.A", "binance": "ROSEUSDT"},
    {"id": "NEAR", "coinalyze": "NEARUSDT_PERP.A", "binance": "NEARUSDT"},
    {"id": "FET", "coinalyze": "FETUSDT_PERP.A", "binance": "FETUSDT"},
    {"id": "HYPE", "coinalyze": "HYPEUSDT_PERP.A", "binance": "HYPEUSDT"},
    {"id": "STRK", "coinalyze": "STRKUSDT_PERP.A", "binance": "STRKUSDT"},
    # --- Nuovi asset (mag 2026) ---
    {"id": "XLM", "coinalyze": "XLMUSDT_PERP.A", "binance": "XLMUSDT"},
    {"id": "ZEC", "coinalyze": "ZECUSDT_PERP.A", "binance": "ZECUSDT"},
    {"id": "ALGO", "coinalyze": "ALGOUSDT_PERP.A", "binance": "ALGOUSDT"},
    {"id": "APT", "coinalyze": "APTUSDT_PERP.A", "binance": "APTUSDT"},
    {"id": "FARTCOIN", "coinalyze": "FARTCOINUSDT_PERP.A", "binance": "FARTCOINUSDT"},
    # BGB: futures solo su Bitget. Se log dice "dati assenti", correggere suffisso exchange.
    {"id": "BGB", "coinalyze": "BGBUSDT_PERP.A", "binance": None},
]

T = {
    "oi_expanding": 5,
    "oi_strong_exp": 10,
    "oi_contracting": -5,
    "oi_strong_contr": -10,
    "price_up": 2,
    "price_down": -2,
    "price_strong_up": 5,
    "price_strong_down": -5,
    "funding_high": 0.05,
    "funding_very_high": 0.08,
    "funding_negative": -0.01,
    "funding_very_neg": -0.03,
    "sig_px_flat": 0.5,
    "sig_px_move": 0.8,
    "sig_px24_move": 1.0,
    "sig_oi_move": 1.5,
    "sig_oi24_move": 2.0,
}

EMA_FAST_4H = 12
EMA_SLOW_4H = 50
EMA_MACRO_1D = 200

ASSET_TIERS = {
    "BTC": "MAJOR",   "ETH": "MAJOR",    "SOL": "MAJOR",
    "SEI": "SMALL",   "RENDER": "SMALL", "VIRTUAL": "SMALL",
    "ENA": "SMALL",   "KAS": "SMALL",    "STRK": "SMALL",  "ROSE": "SMALL",
    "BONK": "MEMECOIN", "PENGU": "MEMECOIN", "FARTCOIN": "MEMECOIN",
}

TIER_OVERRIDES = {
    "MAJOR": {
        "oi_expanding": 2.5, "oi_strong_exp": 5, "oi_contracting": -2.5, "oi_strong_contr": -5,
        "price_up": 1.5, "price_strong_up": 4, "price_down": -1.5, "price_strong_down": -4,
        "sig_px_flat": 0.4, "sig_px_move": 0.6, "sig_px24_move": 0.8,
        "sig_oi_move": 1.0, "sig_oi24_move": 1.5,
    },
    "SMALL": {
        "oi_expanding": 6, "oi_strong_exp": 12, "oi_contracting": -6, "oi_strong_contr": -12,
        "price_up": 2.5, "price_strong_up": 6, "price_down": -2.5, "price_strong_down": -6,
        "sig_px_flat": 0.7, "sig_px_move": 1.2, "sig_px24_move": 1.5,
        "sig_oi_move": 2.0, "sig_oi24_move": 3.0,
    },
    "MEMECOIN": {
        "oi_expanding": 8, "oi_strong_exp": 16, "oi_contracting": -8, "oi_strong_contr": -16,
        "price_up": 4, "price_strong_up": 10, "price_down": -4, "price_strong_down": -10,
        "funding_high": 0.08, "funding_very_high": 0.15,
        "funding_negative": -0.015, "funding_very_neg": -0.05,
        "sig_px_flat": 1.5, "sig_px_move": 2.5, "sig_px24_move": 3.0,
        "sig_oi_move": 3.5, "sig_oi24_move": 5.0,
    },
}


def get_thresholds_for(asset_id):
    t = T.copy()
    tier = ASSET_TIERS.get(asset_id)
    if tier and tier in TIER_OVERRIDES:
        t.update(TIER_OVERRIDES[tier])
    return t


STATE_FILE = "state.json"
HISTORY_FILE = "history.json"
PENDING_ALERTS_FILE = "pending_alerts.json"

COINALYZE_BASE = "https://api.coinalyze.net/v1"
COINALYZE_KEY = os.environ.get("COINALYZE_API_KEY", "").strip()
TG_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
TG_CHAT = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

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
    raise Exception(f"Coinalyze {path}: rate-limit dopo {max_retries} tentativi")


BYBIT_BASE = "https://api.bybit.com"


def bybit_get(path, params, max_retries=3):
    url = f"{BYBIT_BASE}{path}"
    for attempt in range(max_retries):
        try:
            r = requests.get(url, params=params, timeout=HTTP_TIMEOUT)
        except Exception:
            if attempt == max_retries - 1:
                raise
            time.sleep(2)
            continue
        if r.status_code != 200:
            raise Exception(f"Bybit {path} HTTP {r.status_code}: {r.text[:160]}")
        return r.json()
    raise Exception(f"Bybit {path}: troppi tentativi")


def fetch_bybit_lsr(assets):
    out = {}
    syms = [(a["id"], a.get("binance")) for a in assets if a.get("binance")]
    if not syms:
        return out
    print(f"[INFO] Bybit L/S ratio (fallback) · {len(syms)} simboli", flush=True)
    for aid, bsym in syms:
        try:
            resp = bybit_get(
                "/v5/market/account-ratio",
                {"category": "linear", "symbol": bsym, "period": "4h", "limit": 1},
            )
            lst = ((resp or {}).get("result") or {}).get("list") or []
            if lst:
                buy = float(lst[0].get("buyRatio") or 0)
                sell = float(lst[0].get("sellRatio") or 0)
                if sell > 0:
                    out[aid] = buy / sell
        except Exception as e:
            print(f"  [WARN] Bybit L/S {aid} ({bsym}): {e}", flush=True)
        time.sleep(0.2)
    return out


OKX_BASE = "https://www.okx.com"


def okx_get(path, params, max_retries=3):
    url = f"{OKX_BASE}{path}"
    for attempt in range(max_retries):
        try:
            r = requests.get(url, params=params, timeout=HTTP_TIMEOUT)
        except Exception:
            if attempt == max_retries - 1:
                raise
            time.sleep(2)
            continue
        if r.status_code != 200:
            raise Exception(f"OKX {path} HTTP {r.status_code}: {r.text[:160]}")
        return r.json()
    raise Exception(f"OKX {path}: troppi tentativi")


def fetch_okx_lsr(assets):
    out = {}
    if not assets:
        return out
    print(f"[INFO] OKX L/S ratio (fallback) · {len(assets)} simboli", flush=True)
    for a in assets:
        aid = a["id"]
        try:
            resp = okx_get(
                "/api/v5/rubik/stat/contracts/long-short-account-ratio",
                {"ccy": aid, "period": "4H"},
            )
            data = (resp or {}).get("data") or []
            if data:
                ratio = float(data[0][1])
                if ratio > 0:
                    out[aid] = ratio
        except Exception as e:
            print(f"  [WARN] OKX L/S {aid}: {e}", flush=True)
        time.sleep(0.2)
    return out


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
    ema_macro = ema_slow
    ema_macro_period = EMA_SLOW_4H
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
    return {
        "label": label,
        "emaFast": ema_fast,
        "emaSlow": ema_slow,
        "emaMacro": ema_macro,
        "emaMacroPeriod": ema_macro_period,
        "fastVsSlow": fast_vs_slow,
        "aboveMacro": above_macro,
    }


def compute_obv(klines, lookback=50):
    if not klines or len(klines) < lookback + 1:
        return None
    obv = 0.0
    series = []
    for i in range(1, len(klines)):
        close = _kline_val(klines[i], "c")
        prev_close = _kline_val(klines[i-1], "c")
        vol = _kline_val(klines[i], "v")
        if close > prev_close:
            obv += vol
        elif close < prev_close:
            obv -= vol
        series.append({"obv": obv, "close": close})
    recent = series[-min(lookback, len(series)):]
    if len(recent) < 5:
        return None
    obv_start = recent[0]["obv"]
    obv_end = recent[-1]["obv"]
    price_start = recent[0]["close"]
    price_end = recent[-1]["close"]
    obv_change = ((obv_end - obv_start) / abs(obv_start)) * 100 if obv_start != 0 else 0
    price_change = ((price_end - price_start) / price_start) * 100 if price_start else 0
    obv_dir = 1 if obv_change > 0 else (-1 if obv_change < 0 else 0)
    price_dir = 1 if price_change > 0 else (-1 if price_change < 0 else 0)
    diverge = (obv_dir != price_dir and obv_dir != 0 and price_dir != 0
               and abs(obv_change) > 5 and abs(price_change) > 2)
    return {
        "obvChange": obv_change,
        "priceChange": price_change,
        "diverge": diverge,
        "direction": obv_dir,
    }


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
            filled = False
            for j in range(i + 1, len(klines)):
                if _kline_val(klines[j], "l") <= h0:
                    filled = True
                    break
            if not filled:
                unfilled.append({"type": "bull", "top": l2, "bottom": h0,
                                 "size": ((l2 - h0) / h0) * 100 if h0 > 0 else 0})
        if l0 > h2:
            filled = False
            for j in range(i + 1, len(klines)):
                if _kline_val(klines[j], "h") >= l0:
                    filled = True
                    break
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
    range_high = float("-inf")
    range_low = float("inf")
    for k in slice_:
        h = _kline_val(k, "h")
        l = _kline_val(k, "l")
        if h > range_high:
            range_high = h
        if l < range_low:
            range_low = l
    if range_high <= range_low:
        return None
    BUCKETS = 100
    bucket_size = (range_high - range_low) / BUCKETS
    volumes = [0.0] * BUCKETS
    for k in slice_:
        h = _kline_val(k, "h")
        l = _kline_val(k, "l")
        v = _kline_val(k, "v")
        if v <= 0:
            continue
        ch = min(h, range_high)
        cl = max(l, range_low)
        if ch <= cl:
            continue
        sb = max(0, int((cl - range_low) / bucket_size))
        eb = min(BUCKETS - 1, int((ch - range_low) / bucket_size))
        nb = eb - sb + 1
        vpb = v / nb
        for b in range(sb, eb + 1):
            volumes[b] += vpb
    max_vol = 0
    poc_idx = 0
    for i, v in enumerate(volumes):
        if v > max_vol:
            max_vol = v
            poc_idx = i
    poc = range_low + (poc_idx + 0.5) * bucket_size
    total_vol = sum(volumes)
    if total_vol <= 0:
        return None
    target = total_vol * 0.7
    covered = max_vol
    lo = poc_idx
    hi = poc_idx
    while covered < target and (lo > 0 or hi < BUCKETS - 1):
        lv = volumes[lo - 1] if lo > 0 else -1
        uv = volumes[hi + 1] if hi < BUCKETS - 1 else -1
        if lv >= uv:
            lo -= 1
            covered += volumes[lo]
        else:
            hi += 1
            covered += volumes[hi]
    val = range_low + lo * bucket_size
    vah = range_low + (hi + 1) * bucket_size
    return {
        "poc": poc,
        "vah": vah,
        "val": val,
        "rangeHigh": range_high,
        "rangeLow": range_low,
        "distance": ((poc - current_price) / current_price) * 100 if current_price else 0,
        "inValueArea": current_price >= val and current_price <= vah,
    }


def compute_vwap(klines, bars):
    if not klines or len(klines) < 2:
        return None
    tail = klines[-bars:] if len(klines) >= bars else klines
    num = 0.0
    den = 0.0
    for k in tail:
        h = _kline_val(k, "h")
        l = _kline_val(k, "l")
        c = _kline_val(k, "c")
        v = _kline_val(k, "v")
        if v <= 0:
            continue
        tp = (h + l + c) / 3.0
        num += tp * v
        den += v
    if den <= 0:
        return None
    vwap = num / den
    last_close = _kline_val(tail[-1], "c")
    dist = ((last_close - vwap) / vwap) * 100 if vwap else 0
    return {"vwap": vwap, "distance": dist, "above": last_close > vwap, "bars": len(tail)}


def compute_delta(klines, bars=3):
    """Delta REALE buy/sell da Coinalyze (v e bv). 3 candele (~12h) = reattivo."""
    if not klines or len(klines) < 2:
        return None
    tail = klines[-bars:] if len(klines) >= bars else klines
    have_bv = any(("bv" in k and k.get("bv") is not None) for k in tail)
    if not have_bv:
        return None
    tot_buy = 0.0
    tot_sell = 0.0
    last_delta = 0.0
    for i, k in enumerate(tail):
        v = _kline_val(k, "v")
        bv = _kline_val(k, "bv")
        sv = max(0.0, v - bv)
        tot_buy += bv
        tot_sell += sv
        if i == len(tail) - 1:
            last_delta = bv - sv
    cum_delta = tot_buy - tot_sell
    denom = tot_buy + tot_sell
    ratio = (cum_delta / denom) if denom > 0 else 0.0
    return {"lastDelta": last_delta, "cumDelta": cum_delta, "ratio": ratio, "bars": len(tail)}


def fetch_all_via_coinalyze():
    if not COINALYZE_KEY:
        raise Exception("COINALYZE_API_KEY non configurato nei secrets")
    now = int(time.time())
    from_ts = now - 25 * 3600
    oi_by_sym = {}
    px_by_sym = {}
    fr_by_sym = {}
    all_assets = list(ASSETS)
    all_symbols_csv = ",".join(a["coinalyze"] for a in all_assets)

    print(f"[INFO] Coinalyze funding-rate snapshot ({len(all_assets)} simboli)", flush=True)
    try:
        fr_resp = coinalyze_get("/funding-rate", {"symbols": all_symbols_csv})
        if isinstance(fr_resp, list):
            for item in fr_resp:
                sym = _symbol_of(item)
                if not sym:
                    continue
                val = item.get("value")
                if val is None:
                    val = item.get("funding_rate")
                if val is None:
                    val = item.get("rate")
                try:
                    fr_by_sym[sym] = float(val) if val is not None else 0.0
                except (TypeError, ValueError):
                    fr_by_sym[sym] = 0.0
    except Exception as e:
        print(f"[WARN] funding-rate fallito: {e}", flush=True)
    time.sleep(SLEEP_BETWEEN_BATCHES)

    oi_now_by_sym = {}
    print(f"[INFO] Coinalyze open-interest snapshot ({len(all_assets)} simboli)", flush=True)
    try:
        oi_now_resp = coinalyze_get("/open-interest", {"symbols": all_symbols_csv, "convert_to_usd": "false"})
        if isinstance(oi_now_resp, list):
            for item in oi_now_resp:
                sym = _symbol_of(item)
                if not sym:
                    continue
                val = item.get("value")
                try:
                    if val is not None:
                        oi_now_by_sym[sym] = float(val)
                except (TypeError, ValueError):
                    pass
    except Exception as e:
        print(f"[WARN] open-interest snapshot fallito: {e}", flush=True)
    time.sleep(SLEEP_BETWEEN_BATCHES)

    lsr_by_sym = {}
    lsr_batches = list(_chunks(all_assets, BATCH_SIZE))
    print(f"[INFO] Coinalyze L/S · {len(lsr_batches)} batch", flush=True)
    for batch_idx, batch in enumerate(lsr_batches, 1):
        sym_csv = ",".join(a["coinalyze"] for a in batch)
        try:
            lsr_resp = coinalyze_get(
                "/long-short-ratio-history",
                {"symbols": sym_csv, "interval": "4hour", "from": now - 8 * 3600, "to": now},
            )
            if isinstance(lsr_resp, list):
                for item in lsr_resp:
                    sym = _symbol_of(item)
                    if not sym:
                        continue
                    hist = _extract_history(item)
                    if hist:
                        last = max(hist, key=lambda x: x.get("t", 0))
                        ratio_global = last.get("r") or last.get("ratio")
                        lsr_by_sym[sym] = {
                            "global": float(ratio_global) if ratio_global is not None else None,
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
            oi_resp = coinalyze_get(
                "/open-interest-history",
                {"symbols": sym_csv, "interval": "1hour", "from": from_ts, "to": now, "convert_to_usd": "false"},
            )
            for item in (oi_resp or []):
                sym = _symbol_of(item)
                if sym:
                    oi_by_sym[sym] = _extract_history(item)
        except Exception as e:
            print(f"  [WARN] OI batch {batch_idx}: {e}", flush=True)
        time.sleep(SLEEP_BETWEEN)
        try:
            px_resp = coinalyze_get(
                "/ohlcv-history",
                {"symbols": sym_csv, "interval": "1hour", "from": from_ts, "to": now},
            )
            for item in (px_resp or []):
                sym = _symbol_of(item)
                if sym:
                    px_by_sym[sym] = _extract_history(item)
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
            resp = coinalyze_get(
                "/ohlcv-history",
                {"symbols": sym_csv, "interval": "4hour", "from": from_ts_4h, "to": now},
            )
            for item in (resp or []):
                sym = _symbol_of(item)
                if sym:
                    klines4h_by_sym[sym] = sorted(_extract_history(item), key=lambda x: x.get("t", 0))
        except Exception as e:
            print(f"  [WARN] klines 4h batch {batch_idx}: {e}", flush=True)
        if batch_idx < len(batches):
            time.sleep(SLEEP_BETWEEN)

    # candele 1d NON più scaricate (EMA macro = EMA 50 sul 4h). Risparmio API/minuti.
    klines1d_by_sym = {}

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

            snap_oi = oi_now_by_sym.get(sym)
            current_oi = snap_oi if snap_oi is not None else _close(oi_sorted[-1])
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
            c_lsr = lsr_by_sym.get(sym, {})
            lsr_value = c_lsr.get("global")
            lsr_source = "coinalyze" if lsr_value is not None else None
            k4h = klines4h_by_sym.get(sym, [])
            k1d = klines1d_by_sym.get(sym, [])
            trend = compute_trend(k4h, k1d, current_price)
            obv = compute_obv(k4h, lookback=50)
            rvol = compute_rvol(k4h, lookback=20)
            fvg = detect_fvgs(k4h, current_price)
            poc = compute_poc_swing(k4h, current_price, lookback_bars=126)
            vwap_w = compute_vwap(k4h, 42)
            vwap_m = compute_vwap(k4h, 180)
            delta = compute_delta(k4h, bars=3)
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
                "lsr": lsr_value,
                "lsrSource": lsr_source,
                "trend": trend,
                "obv": obv,
                "rvol": rvol,
                "fvg": fvg,
                "poc": poc,
                "vwapW": vwap_w,
                "vwapM": vwap_m,
                "delta": delta,
            }
        except Exception as e:
            result[aid] = {"error": f"parse error: {e}"}

    missing = [a for a in ASSETS
               if isinstance(result.get(a["id"]), dict)
               and not result[a["id"]].get("error")
               and result[a["id"]].get("lsr") is None
               and a.get("binance")]
    if missing:
        bybit_lsr = fetch_bybit_lsr(missing)
        for a in missing:
            v = bybit_lsr.get(a["id"])
            if v is not None:
                result[a["id"]]["lsr"] = v
                result[a["id"]]["lsrSource"] = "bybit"
    still_missing = [a for a in ASSETS
                     if isinstance(result.get(a["id"]), dict)
                     and not result[a["id"]].get("error")
                     and result[a["id"]].get("lsr") is None]
    if still_missing:
        okx_lsr = fetch_okx_lsr(still_missing)
        for a in still_missing:
            v = okx_lsr.get(a["id"])
            if v is not None:
                result[a["id"]]["lsr"] = v
                result[a["id"]]["lsrSource"] = "okx"
    return result


def compute_bias(d, thresholds=None):
    t = thresholds or T
    oi = d.get("oiChange24h") or 0
    px = d.get("priceChange24h") or 0
    fr = d.get("fundingRate") or 0
    f_v_high = fr > t["funding_very_high"]
    f_neg = fr < t["funding_negative"]
    f_v_neg = fr < t["funding_very_neg"]
    oi_exp = oi > t["oi_expanding"]
    oi_str_exp = oi > t["oi_strong_exp"]
    oi_contr = oi < t["oi_contracting"]
    oi_str_contr = oi < t["oi_strong_contr"]
    px_up = px > t["price_up"]
    px_str_up = px > t["price_strong_up"]
    px_down = px < t["price_down"]
    px_str_down = px < t["price_strong_down"]
    px_flat = abs(px) < 1.5
    if px_str_down and oi_str_contr and f_neg:
        return "CAPITULATION"
    if px_up and oi_exp and f_v_high:
        return "OVERHEATED LONG"
    if px_up and oi_exp:
        return "BULLISH SOLIDO"
    if px_up and oi_contr:
        return "SHORT SQUEEZE"
    if px_down and oi_exp:
        return "BEARISH AGGRESSIVO"
    if px_down and oi_contr:
        return "BEAR EXHAUSTION"
    if px_flat and oi_str_exp:
        return "PRESSURE BUILDUP"
    if f_v_neg and not px_str_down:
        return "SHORT CROWDED"
    if f_v_high and not px_str_up:
        return "LONG CROWDED"
    return "NEUTRAL"


def compute_signal_4h(d, thresholds=None):
    t = thresholds or T
    oi4 = d.get("oiChange4h") or 0
    px4 = d.get("priceChange4h") or 0
    oi24 = d.get("oiChange24h") or 0
    px24 = d.get("priceChange24h") or 0

    px_flat   = t["sig_px_flat"]
    px_move   = t["sig_px_move"]
    px24_move = t["sig_px24_move"]
    oi_move   = t["sig_oi_move"]
    oi24_move = t["sig_oi24_move"]

    def sgn(x):
        return 1 if x > 0 else -1 if x < 0 else 0

    px4_s, px24_s = sgn(px4), sgn(px24)
    oi4_s, oi24_s = sgn(oi4), sgn(oi24)
    if abs(px4) < px_flat and oi4 > oi_move:
        return "BUILD-UP"
    px_div = abs(px4) > px_move and abs(px24) > px24_move and px4_s != 0 and px24_s != 0 and px4_s != px24_s
    oi_div = abs(oi4) > oi_move and abs(oi24) > oi24_move and oi4_s != 0 and oi24_s != 0 and oi4_s != oi24_s
    if px_div and oi_div:
        return "REVERSAL"
    if oi_div:
        return "OI GIRA"
    if px_div:
        return "PULLBACK"
    px_conf = px4_s == px24_s and px4_s != 0 and abs(px4) > px_flat
    oi_conf = oi4_s == oi24_s and oi4_s != 0 and abs(oi4) > oi_move
    if px_conf and oi_conf:
        return "CONFERMA"
    if px_conf or oi_conf:
        return "PARZIALE"
    return "PIATTO"


def compute_action(bias, signal_4h):
    B, S = bias, signal_4h
    if B == "BULLISH SOLIDO" and S == "CONFERMA":
        return ("LONG", "strong")
    if B == "BULLISH SOLIDO" and S in ("BUILD-UP", "PARZIALE", "PULLBACK"):
        return ("LONG", "moderate")
    if B == "PRESSURE BUILDUP" and S in ("CONFERMA", "BUILD-UP"):
        return ("LONG", "moderate")
    if B == "CAPITULATION" and S in ("REVERSAL", "OI GIRA"):
        return ("LONG", "strong")
    if B == "BEAR EXHAUSTION" and S in ("REVERSAL", "OI GIRA"):
        return ("LONG", "moderate")
    if B == "SHORT CROWDED" and S == "REVERSAL":
        return ("LONG", "strong")
    if B == "SHORT CROWDED" and S == "OI GIRA":
        return ("LONG", "moderate")
    if B == "BEARISH AGGRESSIVO" and S == "OI GIRA":
        return ("LONG", "moderate")
    if B == "BEARISH AGGRESSIVO" and S == "CONFERMA":
        return ("SHORT", "strong")
    if B == "BEARISH AGGRESSIVO" and S in ("PARZIALE", "PULLBACK"):
        return ("SHORT", "moderate")
    if B == "OVERHEATED LONG" and S == "REVERSAL":
        return ("SHORT", "strong")
    if B == "OVERHEATED LONG" and S == "OI GIRA":
        return ("SHORT", "moderate")
    if B == "LONG CROWDED" and S == "REVERSAL":
        return ("SHORT", "strong")
    if B == "LONG CROWDED" and S == "OI GIRA":
        return ("SHORT", "moderate")
    if B == "SHORT SQUEEZE" and S == "REVERSAL":
        return ("SHORT", "moderate")
    if B == "BULLISH SOLIDO" and S == "REVERSAL":
        return ("SHORT", "weak")
    if B == "PRESSURE BUILDUP" and S == "REVERSAL":
        return ("SHORT", "weak")
    if B == "BEAR EXHAUSTION" and S == "CONFERMA":
        return ("SHORT", "moderate")
    if B == "BEAR EXHAUSTION" and S in ("PARZIALE", "PULLBACK"):
        return ("SHORT", "weak")
    if B == "SHORT SQUEEZE" and S == "CONFERMA":
        return ("LONG", "moderate")
    if B == "SHORT SQUEEZE" and S in ("PARZIALE", "PULLBACK"):
        return ("LONG", "weak")
    return ("NEUTRAL", "weak")


CONF_WEIGHTS = {
    "trend": 3,
    "oi": 3,
    "obv": 2,
    "poc": 2,
    "vwap_w": 2,
    "delta": 3,
    "fvg": 1,
    "vwap_m": 1,
    "funding": 2,
    "lsr": 1,
}


def compute_action_with_confluence(bias, signal_4h, trend, obv, fvg, poc,
                                   current_price, oi_change_4h=None,
                                   funding=None, lsr=None, thresholds=None,
                                   vwap_w=None, vwap_m=None, delta=None,
                                   px_change_24h=None):
    matrix_action, _ = compute_action(bias, signal_4h)
    tlabel = trend.get("label") if trend else None
    direction = "NEUTRAL"
    trend_generated = False

    if tlabel == "TREND UP":
        direction = "LONG"
        trend_generated = True
        if matrix_action == "SHORT" and signal_4h in ("REVERSAL", "OI GIRA"):
            direction = "SHORT"
            trend_generated = False
    elif tlabel == "TREND DOWN":
        direction = "SHORT"
        trend_generated = True
        if matrix_action == "LONG" and signal_4h in ("REVERSAL", "OI GIRA"):
            direction = "LONG"
            trend_generated = False
    else:
        direction = matrix_action

    if direction == "NEUTRAL":
        return ("NEUTRAL", "weak", 0, 0)
    t = thresholds or T
    W = CONF_WEIGHTS
    score = 0.0
    total = 0.0

    if trend and trend.get("label"):
        total += W["trend"]
        if direction == "LONG" and trend["label"] in ("TREND UP", "PULLBACK UP"):
            score += W["trend"]
        elif direction == "SHORT" and trend["label"] in ("TREND DOWN", "PULLBACK DOWN"):
            score += W["trend"]

    if oi_change_4h is not None:
        total += W["oi"]
        if oi_change_4h > t.get("sig_oi_move", 1.5):
            score += W["oi"]

    if obv:
        total += W["obv"]
        if direction == "LONG" and obv.get("direction", 0) == 1:
            score += W["obv"]
        elif direction == "SHORT" and obv.get("direction", 0) == -1:
            score += W["obv"]

    if poc and poc.get("poc") and current_price:
        total += W["poc"]
        if direction == "LONG" and current_price > poc["poc"]:
            score += W["poc"]
        elif direction == "SHORT" and current_price < poc["poc"]:
            score += W["poc"]

    if vwap_w and vwap_w.get("vwap"):
        total += W["vwap_w"]
        if direction == "LONG" and vwap_w.get("above"):
            score += W["vwap_w"]
        elif direction == "SHORT" and not vwap_w.get("above"):
            score += W["vwap_w"]

    if vwap_m and vwap_m.get("vwap"):
        total += W["vwap_m"]
        if direction == "LONG" and vwap_m.get("above"):
            score += W["vwap_m"]
        elif direction == "SHORT" and not vwap_m.get("above"):
            score += W["vwap_m"]

    if delta and delta.get("ratio") is not None:
        total += W["delta"]
        dr = delta["ratio"]
        momentum_ok = (direction == "LONG" and dr > 0.10) or (direction == "SHORT" and dr < -0.10)
        near_level = False
        if vwap_w and vwap_w.get("vwap") and current_price:
            near_level = abs(current_price - vwap_w["vwap"]) / vwap_w["vwap"] <= 0.01
        if poc and poc.get("poc") and current_price and not near_level:
            near_level = abs(current_price - poc["poc"]) / poc["poc"] <= 0.01
        absorption_ok = near_level and (
            (direction == "LONG" and dr < -0.25) or (direction == "SHORT" and dr > 0.25)
        )
        if momentum_ok or absorption_ok:
            score += W["delta"]

    if fvg and (fvg.get("above") or fvg.get("below")):
        total += W["fvg"]
        if direction == "LONG" and fvg.get("below"):
            score += W["fvg"]
        elif direction == "SHORT" and fvg.get("above"):
            score += W["fvg"]

    penalty = 0.0
    if funding is not None:
        if direction == "LONG" and funding > t.get("funding_very_high", 0.08):
            penalty += W["funding"]
        elif direction == "SHORT" and funding < t.get("funding_very_neg", -0.03):
            penalty += W["funding"]
    if lsr is not None:
        if direction == "LONG" and lsr > 2.0:
            penalty += W["lsr"]
        elif direction == "SHORT" and lsr < 0.5:
            penalty += W["lsr"]

    score = max(0.0, score - penalty)

    if total == 0:
        _, base_strength = compute_action(bias, signal_4h)
        return (direction, base_strength, 0, 0)

    frac = score / total
    if trend_generated:
        strength = "strong" if frac >= 0.66 else "moderate"
    else:
        if frac >= 0.82:
            strength = "full"
        elif frac >= 0.66:
            strength = "strong"
        elif frac >= 0.52:
            strength = "moderate"
        else:
            return ("NEUTRAL", "weak", round(score), round(total))

    # === BLOCCO CONTRO-TREND (24h): niente forti contro il movimento ===
    CT = 1.0
    if px_change_24h is not None:
        against = (direction == "SHORT" and px_change_24h > CT) or \
                  (direction == "LONG" and px_change_24h < -CT)
        if against and strength in ("full", "strong"):
            strength = "moderate"

    # === DECLASSAMENTO PER DELTA CONTRARIO: moderate senza flusso -> NEUTRAL ===
    # Soglia 3%: sotto il 2% è rumore, dal 3% in su è flusso reale contrario.
    if delta and delta.get("ratio") is not None:
        dr = delta["ratio"]
        delta_against = (direction == "LONG" and dr < -0.03) or \
                        (direction == "SHORT" and dr > 0.03)
        if delta_against and strength == "moderate":
            return ("NEUTRAL", "weak", round(score), round(total))

    return (direction, strength, round(score), round(total))


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
        strengths = {"weak": 0, "moderate": 1, "strong": 2, "full": 3}
        if strengths.get(curr_s, 0) > strengths.get(prev_s, 0):
            return True
    return False


def fmt_price(p):
    if p is None:
        return "-"
    if p >= 1000:
        return f"${p:,.0f}"
    if p >= 1:
        return f"${p:.2f}"
    if p >= 0.01:
        return f"${p:.4f}"
    return f"${p:.6f}"


def fmt_pct(p, sig=2):
    if p is None:
        return "-"
    s = "+" if p > 0 else ""
    return f"{s}{p:.{sig}f}%"


def _binance_symbol(coinalyze_sym):
    if not coinalyze_sym:
        return None
    return coinalyze_sym.split(".")[0].replace("_PERP", "")


def _build_other_active(state, exclude_asset):
    longs = []
    shorts = []
    for aid, s in state.items():
        if aid == exclude_asset:
            continue
        label = s.get("label", "")
        if label.startswith("LONG"):
            strength = label.split("_")[1] if "_" in label else ""
            longs.append((aid, strength))
        elif label.startswith("SHORT"):
            strength = label.split("_")[1] if "_" in label else ""
            shorts.append((aid, strength))
    return longs, shorts


def format_transition_message(t, other_active_state=None):
    asset = t["asset"]
    curr = t["to"]
    prev = t["from"]
    curr_a, curr_s = curr.split("_") if "_" in curr else (curr, "weak")
    strength_text_map = {"full": "PIENA", "strong": "FORTE", "moderate": "moderata", "weak": "debole"}
    emoji = {"LONG": "🟢", "SHORT": "🔴", "NEUTRAL": "⚪"}.get(curr_a, "⚪")
    strength_text = strength_text_map.get(curr_s, "")
    exhaustion_tag = ""
    if t.get("bias") in ("BEAR EXHAUSTION", "SHORT SQUEEZE"):
        exhaustion_tag = " ⚠️ <i>esaurimento</i>"
    d = t["data"]
    sym = d.get("source_symbol", asset)
    tv_exchange = "BYBIT" if sym.endswith(".6") else "BINANCE"
    base_sym = _binance_symbol(sym) or asset
    tv_link = f"https://www.tradingview.com/chart/?symbol={tv_exchange}:{base_sym}.P"
    lsr_block = ""
    lsr_value = d.get("lsr")
    if lsr_value is not None:
        src = d.get("lsrSource") or ""
        src_tag = f" ({src})" if src else ""
        bias_tag = " · più long" if lsr_value >= 1.0 else " · più short"
        lsr_block = f"<b>L/S ratio:</b> {lsr_value:.2f}{bias_tag}{src_tag}\n"
    tech_block = ""
    trend = d.get("trend")
    obv = d.get("obv")
    rvol = d.get("rvol")
    fvg = d.get("fvg")
    poc = d.get("poc")
    if trend and trend.get("label"):
        tech_block += f"<b>Trend:</b> {trend['label']}"
        if trend.get("emaMacroPeriod"):
            tech_block += f" (EMA{trend['emaMacroPeriod']} 4h)"
        tech_block += "\n"
    if obv:
        obv_dir = "↑" if obv.get("direction", 0) == 1 else "↓" if obv.get("direction", 0) == -1 else "→"
        div_flag = " ⚠️ div" if obv.get("diverge") else ""
        tech_block += f"<b>OBV:</b> {obv_dir} {fmt_pct(obv.get('obvChange'), 1)}{div_flag}\n"
    if rvol and rvol.get("ratio"):
        tech_block += f"<b>RVOL:</b> {rvol['ratio']:.2f}x\n"
    if fvg:
        fvg_parts = []
        if fvg.get("below"):
            fvg_parts.append(f"sotto a {fmt_pct(fvg['below']['distance'], 1)}")
        if fvg.get("above"):
            fvg_parts.append(f"sopra a {fmt_pct(fvg['above']['distance'], 1)}")
        if fvg_parts:
            tech_block += f"<b>FVG 4h:</b> {' · '.join(fvg_parts)}\n"
    if poc and poc.get("poc"):
        in_va = " (in value area)" if poc.get("inValueArea") else ""
        tech_block += f"<b>POC:</b> {fmt_price(poc['poc'])} · Δ {fmt_pct(poc.get('distance'), 1)}{in_va}\n"
    vwap_w = d.get("vwapW")
    vwap_m = d.get("vwapM")
    if vwap_w and vwap_w.get("vwap"):
        pos_w = "sopra" if vwap_w.get("above") else "sotto"
        vwm_txt = ""
        if vwap_m and vwap_m.get("vwap"):
            pos_m = "sopra" if vwap_m.get("above") else "sotto"
            vwm_txt = f" · mens. {pos_m}"
        tech_block += f"<b>VWAP sett.:</b> {fmt_price(vwap_w['vwap'])} · prezzo {pos_w} ({fmt_pct(vwap_w.get('distance'), 1)}){vwm_txt}\n"
    delta = d.get("delta")
    if delta and delta.get("ratio") is not None:
        r = delta["ratio"]
        dlabel = "compratori" if r > 0 else "venditori"
        tech_block += f"<b>Delta 12h:</b> {('+' if r>=0 else '')}{r*100:.0f}% ({dlabel})\n"
    confluence = t.get("confluence")
    if confluence:
        score = confluence.get("score", 0)
        total = confluence.get("total", 0)
        if total > 0:
            tech_block += f"<b>📊 Confluenza:</b> {score}/{total} (peso a favore)\n"
    msg = (
        f"{emoji} <b>{curr_a} {strength_text}</b> · <b>{asset}</b>{exhaustion_tag}\n"
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
        save_json(PENDING_ALERTS_FILE, [f"⚠️ <b>OI Monitor errore</b>\n\nCoinalyze fetch fallito:\n<code>{str(e)[:300]}</code>"])
        return
    for asset in ASSETS:
        asset_id = asset["id"]
        data = all_data.get(asset_id, {"error": "no data"})
        if data.get("error"):
            errors.append(f"{asset_id}: {data['error']}")
            print(f"  [X] {asset_id}: {data['error']}", flush=True)
            continue
        try:
            thr = get_thresholds_for(asset_id)
            bias = compute_bias(data, thr)
            signal = compute_signal_4h(data, thr)
            action, strength, conf_score, conf_total = compute_action_with_confluence(
                bias, signal,
                data.get("trend"), data.get("obv"),
                data.get("fvg"), data.get("poc"),
                data.get("price"),
                oi_change_4h=data.get("oiChange4h"),
                funding=data.get("fundingRate"),
                lsr=data.get("lsr"),
                thresholds=thr,
                vwap_w=data.get("vwapW"),
                vwap_m=data.get("vwapM"),
                delta=data.get("delta"),
                px_change_24h=data.get("priceChange24h"),
            )
            curr_label = f"{action}_{strength}"
            prev_entry = last_state.get(asset_id, {})
            prev_label = prev_entry.get("label")
            transition_logged = False
            is_transition = prev_label and should_notify(prev_label, curr_label)
            is_new_active = (not prev_label) and (not is_first_run) and action in ("LONG", "SHORT")
            label_changed = bool(prev_label) and (prev_label != curr_label)
            prev_since = prev_entry.get("since_ts")
            since_ts = int(time.time()) if (label_changed or not prev_since) else prev_since

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
                    "confluence": {"score": conf_score, "total": conf_total},
                }
                transitions.append(transition)
                transition_logged = True

            if label_changed or is_new_active:
                hist_from = prev_label if label_changed else "NEW"
                append_history({
                    "ts": int(time.time()),
                    "asset": asset_id,
                    "from": hist_from,
                    "to": curr_label,
                    "bias": bias,
                    "signal": signal,
                    "price": data["price"],
                    "px4h": data.get("priceChange4h"),
                    "px24h": data.get("priceChange24h"),
                    "oi4h": data.get("oiChange4h"),
                    "oi24h": data.get("oiChange24h"),
                    "funding": data.get("fundingRate"),
                    "confluence_score": conf_score,
                    "confluence_total": conf_total,
                })
            new_state[asset_id] = {
                "label": curr_label,
                "bias": bias,
                "signal": signal,
                "ts": int(time.time()),
                "since_ts": since_ts,
                "confluence": {"score": conf_score, "total": conf_total},
                "data": {
                    "price": data["price"],
                    "px24h": data.get("priceChange24h"),
                    "px4h": data.get("priceChange4h"),
                    "oi24h": data.get("oiChange24h"),
                    "oi4h": data.get("oiChange4h"),
                    "funding": data.get("fundingRate"),
                    "lsr": data.get("lsr"),
                    "lsrSource": data.get("lsrSource"),
                    "trend": data.get("trend"),
                    "obv": data.get("obv"),
                    "rvol": data.get("rvol"),
                    "fvg": data.get("fvg"),
                    "poc": data.get("poc"),
                    "vwapW": data.get("vwapW"),
                    "vwapM": data.get("vwapM"),
                    "delta": data.get("delta"),
                },
            }
            flag = " *" if transition_logged else ""
            print(f"  [OK] {asset_id:7s} {curr_label:18s} (era {prev_label or 'nuovo'}){flag}", flush=True)
        except Exception as e:
            errors.append(f"{asset_id}: {e}")
            print(f"  [X] {asset_id}: exception {e}", flush=True)

    save_json(STATE_FILE, new_state)

    pending_alerts = []
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
            f"🤖 <b>OI Monitor avviato</b>\n"
            f"🕐 {now_italy_str()}\n\n"
            f"Sto monitorando {len(ASSETS)} asset via <b>Coinalyze</b>.\n"
            f"Riceverai alert quando un asset:\n"
            f"• transita da NEUTRAL a LONG/SHORT\n"
            f"• flippa direzione (LONG↔SHORT)\n"
            f"• upgrade a forte (moderato→forte)"
            f"{active_block}"
        )
        pending_alerts.append(startup_msg)
    else:
        for t in transitions:
            msg = format_transition_message(t, other_active_state=new_state)
            pending_alerts.append(msg)

    if pending_alerts:
        save_json(PENDING_ALERTS_FILE, pending_alerts)
        print(f"\n[INFO] {len(pending_alerts)} alert salvati in pending_alerts.json", flush=True)

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
