#!/usr/bin/env python3
"""OI Monitor — Coinalyze + tier system + EMA 8/12 + Signal 4h per tier + pending alerts."""

import os
import json
import time
from datetime import datetime, timezone, timedelta
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
    # BGB: quotato a futures SOLO su Bitget (non su Binance/Bybit). Il simbolo Coinalyze
    # del mercato Bitget va verificato al primo run: se appare "BGB: dati assenti" nel log,
    # correggere il suffisso exchange qui sotto. binance=None così l'HTML non tenta il live.
    {"id": "BGB", "coinalyze": "BGBUSDT_PERP.A", "binance": None},
    # --- Nuovi asset (lug 2026, watchlist utente) ---
    # Simboli col pattern standard Coinalyze <SYM>USDT_PERP.A (aggregato multi-exchange).
    {"id": "AVAX", "coinalyze": "AVAXUSDT_PERP.A", "binance": "AVAXUSDT"},
    {"id": "DOT", "coinalyze": "DOTUSDT_PERP.A", "binance": "DOTUSDT"},
    {"id": "CRV", "coinalyze": "CRVUSDT_PERP.A", "binance": "CRVUSDT"},
    {"id": "LTC", "coinalyze": "LTCUSDT_PERP.A", "binance": "LTCUSDT"},
    {"id": "ADA", "coinalyze": "ADAUSDT_PERP.A", "binance": "ADAUSDT"},
    {"id": "DOGE", "coinalyze": "DOGEUSDT_PERP.A", "binance": "DOGEUSDT"},
    {"id": "XRP", "coinalyze": "XRPUSDT_PERP.A", "binance": "XRPUSDT"},
    {"id": "UNI", "coinalyze": "UNIUSDT_PERP.A", "binance": "UNIUSDT"},
    {"id": "AAVE", "coinalyze": "AAVEUSDT_PERP.A", "binance": "AAVEUSDT"},
    {"id": "TIA", "coinalyze": "TIAUSDT_PERP.A", "binance": "TIAUSDT"},
    {"id": "WLD", "coinalyze": "WLDUSDT_PERP.A", "binance": "WLDUSDT"},
    {"id": "POL", "coinalyze": "POLUSDT_PERP.A", "binance": "POLUSDT"},
    {"id": "EIGEN", "coinalyze": "EIGENUSDT_PERP.A", "binance": "EIGENUSDT"},
    {"id": "PEPE", "coinalyze": "1000PEPEUSDT_PERP.A", "binance": "1000PEPEUSDT"},
    {"id": "RAY", "coinalyze": "RAYUSDT_PERP.A", "binance": "RAYUSDT"},
    {"id": "XPL", "coinalyze": "XPLUSDT_PERP.A", "binance": None},
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
    # --- Soglie Signal 4h (default STANDARD) ---
    "sig_px_flat": 0.5,    # BUILD-UP: |px4| sotto questa = "piatto"; e soglia min px CONFERMA
    "sig_px_move": 0.8,    # px divergenza/movimento min su 4h
    "sig_px24_move": 1.0,  # px divergenza min su 24h
    "sig_oi_move": 1.5,    # oi build-up/divergenza/conferma min su 4h
    "sig_oi24_move": 2.0,  # oi divergenza min su 24h
}

EMA_FAST_4H = 12
EMA_SLOW_4H = 50
EMA_MACRO_1D = 200

# === SISTEMA A TIER: ogni asset appartiene a una categoria con soglie diverse ===
# MAJOR: market cap molto alto, OI stabile, volatilità bassa
# STANDARD: la maggior parte degli altcoin, comportamento "normale" (default T)
# SMALL: altcoin più piccoli, volatilità maggiore
# MEMECOIN: estremamente volatili, OI/funding possono spike enormi
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
        # Signal 4h più reattivo: BTC/ETH/SOL si muovono poco, soglie strette
        "sig_px_flat": 0.4, "sig_px_move": 0.6, "sig_px24_move": 0.8,
        "sig_oi_move": 1.0, "sig_oi24_move": 1.5,
    },
    "SMALL": {
        "oi_expanding": 6, "oi_strong_exp": 12, "oi_contracting": -6, "oi_strong_contr": -12,
        "price_up": 2.5, "price_strong_up": 6, "price_down": -2.5, "price_strong_down": -6,
        # Signal 4h leggermente più largo per filtrare rumore
        "sig_px_flat": 0.7, "sig_px_move": 1.2, "sig_px24_move": 1.5,
        "sig_oi_move": 2.0, "sig_oi24_move": 3.0,
    },
    "MEMECOIN": {
        "oi_expanding": 8, "oi_strong_exp": 16, "oi_contracting": -8, "oi_strong_contr": -16,
        "price_up": 4, "price_strong_up": 10, "price_down": -4, "price_strong_down": -10,
        "funding_high": 0.08, "funding_very_high": 0.15,
        "funding_negative": -0.015, "funding_very_neg": -0.05,
        # Signal 4h molto largo: BONK/PENGU oscillano del 2-3% in 4h come routine
        "sig_px_flat": 1.5, "sig_px_move": 2.5, "sig_px24_move": 3.0,
        "sig_oi_move": 3.5, "sig_oi24_move": 5.0,
    },
}


def get_thresholds_for(asset_id):
    """Restituisce le soglie per un asset in base al suo tier."""
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
# BATCH_SIZE 10 (da 7): con 48 asset il numero di chiamate history torna uguale a
# quello che 30 asset facevano con batch 7 -> stesso carico, niente 429 a raffica.
# Gli endpoint snapshot (funding/open-interest) accettano gia' tutti i simboli insieme.
BATCH_SIZE = 10
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


# === Bybit public data: Long/Short Ratio (fallback) ===
# Coinalyze fornisce un long/short ratio affidabile (campo `r`) e funziona da GitHub
# Actions. Binance Futures invece è bloccato (HTTP 451) dagli IP dei runner, quindi NON
# è utilizzabile qui. Bybit viene usato solo come "riempi-buchi" per gli asset che
# Coinalyze non copre.
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
    """Long/Short ratio (account ratio Bybit), usato solo come fallback.
    Restituisce {asset_id: float}. ratio = buyRatio / sellRatio."""
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


# === OKX public data: Long/Short Ratio (terzo fallback) ===
# Usato per gli asset che né Coinalyze né Bybit coprono. Endpoint pubblico, accessibile
# da GitHub Actions. ccy = ticker dell'asset (es. TAO, INJ).
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
    """Long/Short account ratio da OKX (rubik), usato come ulteriore fallback.
    Restituisce {asset_id: float}. ccy = ticker dell'asset; risposta = lista [ts, ratio]."""
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
                # data ordinata dal più recente; ogni voce è [timestamp, ratio]
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
    # Macro = EMA lenta sul 4h (50). Niente più EMA 200 su 1d: troppo lenta.
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
    """VWAP (Volume Weighted Average Price) sulle ultime `bars` candele.
    typical price = (H+L+C)/3, pesato per volume. Restituisce dict con valore e
    posizione del prezzo corrente rispetto al VWAP (distanza % e above bool)."""
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


def compute_weekly_bias(klines4h, current_price):
    """Bias settimanale per swing (peso leggero, conferma): weekly open (apertura
    lunedi' 00:00 UTC) + Monday high/low (range del lunedi'). Il lunedi' il range si
    sta ancora formando -> NON attivo; diventa utilizzabile da martedi' 00:00 UTC.
    Ritorna dict {active, weeklyOpen, mondayHigh/Low, bias LONG/SHORT/NEUTRAL} o None.
    bias LONG = prezzo sopra weekly open E sopra Monday high; SHORT = sotto entrambi;
    NEUTRAL = dentro il range (non informa la direzione)."""
    if not klines4h or current_price is None:
        return None
    now = datetime.now(timezone.utc)
    monday = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    monday_ts = int(monday.timestamp())
    tuesday_ts = monday_ts + 24 * 3600
    if now.timestamp() < tuesday_ts:        # e' ancora lunedi': range non chiuso
        return {"active": False}
    mon = [k for k in klines4h if monday_ts <= _kline_val(k, "t") < tuesday_ts]
    if not mon:
        return {"active": False}
    weekly_open = _kline_val(mon[0], "o")
    monday_high = max(_kline_val(k, "h") for k in mon)
    monday_low = min(_kline_val(k, "l") for k in mon)
    if weekly_open <= 0 or monday_high <= 0:
        return {"active": False}
    if current_price > weekly_open and current_price > monday_high:
        bias = "LONG"
    elif current_price < weekly_open and current_price < monday_low:
        bias = "SHORT"
    else:
        bias = "NEUTRAL"
    return {
        "active": True, "bias": bias,
        "weeklyOpen": weekly_open, "mondayHigh": monday_high, "mondayLow": monday_low,
        "aboveOpen": current_price > weekly_open,
    }


def compute_delta(klines, bars=6):
    """Delta REALE compratori-venditori dalle candele Coinalyze.
    Coinalyze OHLCV espone 'v' (volume totale) e 'bv' (buy volume).
    delta = bv - (v - bv) = 2*bv - v.  >0 = dominano i compratori.
    Calcola: delta ultima candela, somma delta su `bars`, e il rapporto
    cumulato (buy/sell) per leggere lo sbilanciamento recente.
    Ritorna None se 'bv' non è disponibile (alcuni mercati minori)."""
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
    # ratio normalizzato in [-1, +1]: +1 tutto buy, -1 tutto sell
    ratio = (cum_delta / denom) if denom > 0 else 0.0
    return {
        "lastDelta": last_delta,      # delta ultima candela 4h
        "cumDelta": cum_delta,        # delta cumulato su `bars`
        "ratio": ratio,               # sbilanciamento normalizzato [-1,+1]
        "bars": len(tail),
    }


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

    # OI corrente in tempo reale (snapshot) — più fresco delle candele orarie.
    # Le candele 1h restano per calcolare i confronti OI 4h/24h fa.
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
    print(f"[INFO] Coinalyze L/S top traders · {len(lsr_batches)} batch", flush=True)
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

    # NB: le candele giornaliere (1d) NON vengono più scaricate. La EMA macro ora è la
    # EMA 50 sul 4h (non più EMA 200 daily), quindi i dati 1d erano inutilizzati.
    # Rimuoverli risparmia ~31 chiamate API e ~1 min per run (minuti GitHub Actions).
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

            # OI corrente: preferisci lo snapshot real-time; fallback all'ultima candela 1h
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
            # L/S ratio: un solo valore affidabile da Coinalyze (campo r).
            # Gli asset senza dato Coinalyze verranno riempiti con Bybit più sotto.
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
            # VWAP: settimanale (~42 barre 4h = 7gg) e mensile (~180 barre = 30gg)
            vwap_w = compute_vwap(k4h, 42)
            vwap_m = compute_vwap(k4h, 180)
            # Delta reale buy/sell (da campo bv di Coinalyze), ultime 3 candele 4h (~12h).
            # 3 candele invece di 6: più reattivo, non si media a zero come prima.
            delta = compute_delta(k4h, bars=3)
            # Bias settimanale: weekly open + Monday range (conferma swing, da martedì)
            weekly_bias = compute_weekly_bias(k4h, current_price)
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
                "weeklyBias": weekly_bias,
            }
        except Exception as e:
            result[aid] = {"error": f"parse error: {e}"}

    # Riempi i buchi L/S (asset senza dato Coinalyze) con Bybit
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
    # Ancora senza L/S dopo Bybit -> ultimo tentativo con OKX
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


# Pesi dei fattori di confluenza (più alto = più importante per validare l'azione).
# Logica: si entra CON il trend, confermato da OI e volume; funding e L/S agiscono
# da filtro contrarian agli estremi (folla troppo sbilanciata = rischio); la struttura
# (POC/FVG) misura la qualità dell'ingresso.
CONF_WEIGHTS = {
    "trend": 3,    # direzione EMA 12/50 sul 4h: non andare controtrend
    "oi": 3,       # OI in espansione = convinzione dietro il movimento
    "obv": 2,      # volume che conferma la spinta
    "poc": 2,      # posizione vs POC (volume profile)
    "vwap_w": 2,   # prezzo vs VWAP settimanale (fair value istituzionale, swing)
    "delta": 3,    # delta reale buy/sell — ANTICIPATORE (si muove per primo): peso alto per reattività
    "fvg": 1,      # gap di prezzo a favore
    "vwap_m": 1,   # prezzo vs VWAP mensile (filtro trend macro)
    "weekly_bias": 1,  # LEGGERO: weekly open + Monday range (conferma swing, da martedi')
    # --- I due sotto NON danno bonus: sono PENALITÀ contrarian agli estremi ---
    "funding": 2,  # PENALITÀ se funding bollente/gelido contro il trade
    "lsr": 1,      # PENALITÀ se L/S retail troppo carico nel verso del trade
}


def compute_action_with_confluence(bias, signal_4h, trend, obv, fvg, poc,
                                   current_price, oi_change_4h=None,
                                   funding=None, lsr=None, thresholds=None,
                                   vwap_w=None, vwap_m=None, delta=None,
                                   px_change_24h=None, weekly_bias=None):
    """Confluenza PESATA: ogni fattore contribuisce con il suo peso se è d'accordo
    con la direzione. La forza dipende dalla frazione di peso a favore (score/total).
    I fattori mancanti vengono esclusi dal totale, così non penalizzano a vuoto."""
    # === GERARCHIA DELLA DIREZIONE (ottimizzata per swing 4h) ===
    # MOTORE PRIMARIO = TREND. Su uno swing la direzione la dà il trend 4h (EMA 12/50),
    # non l'OI: così si entra presto sui trend puliti senza aspettare che il bias 24h
    # diventi "estremo". L'OI-matrix resta come SECONDO motore per i casi in cui il
    # trend è piatto (range/CHOP) o per cogliere le inversioni (REVERSAL contro-trend).
    matrix_action, _ = compute_action(bias, signal_4h)
    tlabel = trend.get("label") if trend else None
    direction = "NEUTRAL"
    trend_generated = False

    if tlabel == "TREND UP":
        direction = "LONG"
        trend_generated = True
        # Eccezione: se la matrice grida un'inversione opposta forte, lasciala vincere
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
        # Trend piatto (CHOP/PULLBACK): si affida alla matrice OI (range, build-up, ecc.)
        direction = matrix_action

    if direction == "NEUTRAL":
        return ("NEUTRAL", "weak", 0, 0)
    t = thresholds or T
    W = CONF_WEIGHTS
    score = 0.0
    total = 0.0

    # 1) Trend EMA 12/50 (4h)
    if trend and trend.get("label"):
        total += W["trend"]
        if direction == "LONG" and trend["label"] in ("TREND UP", "PULLBACK UP"):
            score += W["trend"]
        elif direction == "SHORT" and trend["label"] in ("TREND DOWN", "PULLBACK DOWN"):
            score += W["trend"]

    # 2) Open Interest: espansione = convinzione dietro il movimento (vale entrambe le direzioni)
    if oi_change_4h is not None:
        total += W["oi"]
        if oi_change_4h > t.get("sig_oi_move", 1.5):
            score += W["oi"]

    # 3) OBV / volume
    if obv:
        total += W["obv"]
        if direction == "LONG" and obv.get("direction", 0) == 1:
            score += W["obv"]
        elif direction == "SHORT" and obv.get("direction", 0) == -1:
            score += W["obv"]

    # 4) POC / struttura
    if poc and poc.get("poc") and current_price:
        total += W["poc"]
        if direction == "LONG" and current_price > poc["poc"]:
            score += W["poc"]
        elif direction == "SHORT" and current_price < poc["poc"]:
            score += W["poc"]

    # 4b) VWAP settimanale: prezzo sopra = supporta LONG, sotto = supporta SHORT
    if vwap_w and vwap_w.get("vwap"):
        total += W["vwap_w"]
        if direction == "LONG" and vwap_w.get("above"):
            score += W["vwap_w"]
        elif direction == "SHORT" and not vwap_w.get("above"):
            score += W["vwap_w"]

    # 4c) VWAP mensile: filtro trend macro
    if vwap_m and vwap_m.get("vwap"):
        total += W["vwap_m"]
        if direction == "LONG" and vwap_m.get("above"):
            score += W["vwap_m"]
        elif direction == "SHORT" and not vwap_m.get("above"):
            score += W["vwap_m"]

    # 4d) DELTA reale (IBRIDO, peso 2): dà il punto se UNA delle due:
    #     (a) momentum: delta a favore della direzione (buy per LONG, sell per SHORT)
    #     (b) assorbimento a un livello chiave: delta CONTRO il prezzo ma il prezzo regge
    #         (es. forte vendita ma prezzo non scende vicino a VWAP/POC = assorbimento buy)
    if delta and delta.get("ratio") is not None:
        total += W["delta"]
        dr = delta["ratio"]               # [-1, +1]: >0 dominano i compratori
        # momentum a favore
        momentum_ok = (direction == "LONG" and dr > 0.10) or (direction == "SHORT" and dr < -0.10)
        # assorbimento a livello: vicino a VWAP settimanale o POC
        near_level = False
        if vwap_w and vwap_w.get("vwap") and current_price:
            near_level = abs(current_price - vwap_w["vwap"]) / vwap_w["vwap"] <= 0.01
        if poc and poc.get("poc") and current_price and not near_level:
            near_level = abs(current_price - poc["poc"]) / poc["poc"] <= 0.01
        # assorbimento: a un livello, delta forte CONTRO la direzione = chi difende il livello
        # (per un LONG: vendite forti assorbite => dr molto negativo ma siamo al supporto)
        absorption_ok = near_level and (
            (direction == "LONG" and dr < -0.25) or (direction == "SHORT" and dr > 0.25)
        )
        if momentum_ok or absorption_ok:
            score += W["delta"]

    # 6) FVG: gap a favore (sotto per LONG = supporto, sopra per SHORT = resistenza/target)
    if fvg and (fvg.get("above") or fvg.get("below")):
        total += W["fvg"]
        if direction == "LONG" and fvg.get("below"):
            score += W["fvg"]
        elif direction == "SHORT" and fvg.get("above"):
            score += W["fvg"]

    # 7) BIAS SETTIMANALE (weekly open + Monday range) — peso 1, LEGGERO.
    # Attivo solo da martedi' (lunedi' il range non e' chiuso). Conta solo quando e'
    # direzionale (LONG/SHORT, cioe' prezzo fuori dal range del lunedi'): +peso se
    # allineato alla direzione del trade, altrimenti 0 ma entra nel totale (freno
    # morbido per diluizione). Dentro il range (NEUTRAL) non lo contiamo: non informa.
    if weekly_bias and weekly_bias.get("active") and weekly_bias.get("bias") in ("LONG", "SHORT"):
        total += W["weekly_bias"]
        if weekly_bias["bias"] == direction:
            score += W["weekly_bias"]

    # === FILTRI CONTRARIAN (solo PENALITÀ agli estremi) ===
    # Funding e L/S NON danno bonus quando sono normali (non entrano in `total`):
    # restano neutri. Tolgono punti SOLO quando sono a un estremo CONTRO il trade,
    # perché segnalano folla troppo sbilanciata = rischio washout/squeeze.
    penalty = 0.0

    # Funding estremo contro il trade
    if funding is not None:
        if direction == "LONG" and funding > t.get("funding_very_high", 0.08):
            penalty += W["funding"]   # long su funding bollente = rischioso
        elif direction == "SHORT" and funding < t.get("funding_very_neg", -0.03):
            penalty += W["funding"]   # short su funding molto negativo = rischio squeeze

    # L/S retail estremo nel verso del trade (contrarian: folla troppo carica)
    if lsr is not None:
        if direction == "LONG" and lsr > 2.0:
            penalty += W["lsr"]       # troppi long retail = rischio per un nuovo long
        elif direction == "SHORT" and lsr < 0.5:
            penalty += W["lsr"]       # troppi short retail = rischio per un nuovo short

    score = max(0.0, score - penalty)

    if total == 0:
        _, base_strength = compute_action(bias, signal_4h)
        return (direction, base_strength, 0, 0)

    frac = score / total
    # Soglie reattive: abbassate per anticipare il passaggio a 'forte'.
    # (full 0.82, strong 0.66, moderate 0.52). Combinate col peso alto del delta
    # rendono il segnale forte più tempestivo senza allargarlo a mosse deboli.
    if trend_generated:
        # Segnale nato dal trend (senza conferma bias/OI): solo MODERATE o STRONG.
        # SOGLIA MINIMA 30%: un trend up/down da solo non basta. Serve almeno il 30%
        # di confluenza (OI/volume/struttura a favore), altrimenti è un trend che sta
        # morendo (es. APT: trend up ma OI in calo, delta piatto, 24%) -> NEUTRAL.
        if frac < 0.30:
            return ("NEUTRAL", "weak", round(score), round(total))
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

    # === BLOCCO CONTRO-TREND (24h) ===
    # Se il prezzo nelle 24h va CONTRO la direzione, il segnale non può essere "forte":
    # stai shortando un asset che sale (es. XLM +4%) o longando uno che scende.
    # Declassa a "moderate" — evita i forti sui rimbalzi controtrend visti nel check.
    CT = 1.0  # % minima di movimento 24h per considerarlo "contro"
    if px_change_24h is not None:
        against = (direction == "SHORT" and px_change_24h > CT) or \
                  (direction == "LONG" and px_change_24h < -CT)
        if against and strength in ("full", "strong"):
            strength = "moderate"

    # === DECLASSAMENTO PER DELTA CONTRARIO ===
    # Se il delta reale (flusso buy/sell) va CONTRO la direzione in modo netto,
    # manca la convinzione: un LONG con forte flusso di VENDITA (o viceversa) non è
    # un buon setup. Un segnale è "forte" SOLO se pure il flusso è d'accordo:
    #  - strong/full + delta contro  -> scende a "moderate" (direzione ok, timing no:
    #    es. KAS short strutturale ma con delta +11% = compratori che spingono, a
    #    metà range: si shorta un rimbalzo, non con convinzione)
    #  - moderate + delta contro     -> NEUTRAL (niente trade)
    # Soglia 3%: sotto il 2% è rumore, dal 3% in su è flusso reale contrario.
    # (Tarata sui dati veri: i long deboli avevano delta -3/-4% = distribuzione.)
    if delta and delta.get("ratio") is not None:
        dr = delta["ratio"]
        delta_against = (direction == "LONG" and dr < -0.03) or \
                        (direction == "SHORT" and dr > 0.03)
        if delta_against:
            if strength in ("full", "strong"):
                strength = "moderate"
            elif strength == "moderate":
                return ("NEUTRAL", "weak", round(score), round(total))

    # === VETO "NESSUNA CONFERMA" (VWAP sett. + delta ENTRAMBI contro) ===
    # Un segnale solo 'moderate' che ha CONTRO le due conferme che pesano di più:
    #  - prezzo dal lato sbagliato della VWAP settimanale (niente livello istituzionale)
    #  - E delta reale contro la direzione (il flusso spinge dall'altra parte)
    # non è un trade: è deriva vicino alla media. Nessuno dei due filtri singoli lo
    # blocca (delta-contrario scatta solo oltre 3%, la VWAP da sola pesa 2), ma INSIEME
    # dicono "nessuna convinzione". Es. ETH LONG 6/17 sotto VWAP sett. con delta -2.5%
    # mentre BTC identico era già NEUTRAL: così tornano coerenti (entrambi NEUTRAL).
    # Solo 'moderate': uno 'strong/full' ha già abbastanza struttura altrove.
    if strength == "moderate" and vwap_w and vwap_w.get("vwap") and \
       delta and delta.get("ratio") is not None:
        dr2 = delta["ratio"]
        vwap_against = (direction == "LONG" and not vwap_w.get("above")) or \
                       (direction == "SHORT" and vwap_w.get("above"))
        delta_against2 = (direction == "LONG" and dr2 < -0.01) or \
                         (direction == "SHORT" and dr2 > 0.01)
        if vwap_against and delta_against2:
            return ("NEUTRAL", "weak", round(score), round(total))

    # === FRENO MOVIMENTO GIÀ ESPLOSO (anti "comprare sul massimo") ===
    # Se il prezzo ha già corso MOLTO nella direzione del segnale nelle 24h e il flusso
    # (delta) NON conferma con forza, è un ingresso tardivo: stai comprando un massimo
    # o shortando un minimo già fatto. Es. JUP LONG +17% con delta 0%.
    #  - oltre ±12% a favore + delta debole (<10%) -> niente "strong/full" (max moderate)
    #  - oltre ±18% (estensione estrema) + delta debole -> NEUTRAL (non inseguire)
    if px_change_24h is not None and delta and delta.get("ratio") is not None:
        dr = delta["ratio"]
        move = px_change_24h if direction == "LONG" else -px_change_24h  # >0 = a favore
        delta_confirms = (direction == "LONG" and dr > 0.10) or \
                         (direction == "SHORT" and dr < -0.10)
        if move > 18 and not delta_confirms:
            return ("NEUTRAL", "weak", round(score), round(total))
        if move > 12 and not delta_confirms and strength in ("full", "strong"):
            strength = "moderate"

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
            tech_block += f" (EMA{trend['emaMacroPeriod']} 1D)"
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
        tech_block += f"<b>Delta 1g:</b> {('+' if r>=0 else '')}{r*100:.0f}% ({dlabel})\n"
    confluence = t.get("confluence")
    if confluence:
        score = confluence.get("score", 0)
        total = confluence.get("total", 0)
        if total > 0:
            tech_block += f"<b>📊 Confluenza:</b> {score}/{total} indicatori d'accordo\n"
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


PERFORMANCE_FILE = "performance.json"


def _structure_broken(direction, data):
    """Chiusura BASATA SUI VALORI (non sul label NEUTRAL). Un trade resta aperto
    finché la struttura che l'ha creato regge; si chiude se SI ROMPE almeno una:
      - il trend 4h si gira (LONG chiude su TREND DOWN; SHORT su TREND UP)
      - il prezzo rompe il VWAP settimanale (LONG chiude se scende sotto; SHORT sopra)
      - il delta si gira forte contro (>5%)
    Così un LONG resta aperto anche se il label va NEUTRAL, purché trend+VWAP+flusso
    reggano — elimina i trade-spezzone da 1-2h e misura lo swing vero."""
    if not data:
        return False  # niente dati: non chiudere per prudenza
    tlabel = (data.get("trend") or {}).get("label")
    vw = data.get("vwapW") or {}
    above_vwap = vw.get("above")
    dr = (data.get("delta") or {}).get("ratio")
    if direction == "LONG":
        if tlabel == "TREND DOWN":
            return True
        if above_vwap is False:
            return True
        if dr is not None and dr < -0.05:
            return True
    elif direction == "SHORT":
        if tlabel == "TREND UP":
            return True
        if above_vwap is True:
            return True
        if dr is not None and dr > 0.05:
            return True
    return False


def update_performance(new_state, last_state):
    """Traccia le performance dei segnali. performance.json ha due liste:
      - open:   trade attivi (LONG/SHORT in corso), aggiornati a ogni run col P&L live
      - closed: trade chiusi, con esito finale
    La chiusura NON avviene al primo NEUTRAL, ma quando la STRUTTURA si rompe
    (trend/VWAP/delta) — vedi _structure_broken. Così i trade durano quanto lo swing.
    """
    perf = load_json(PERFORMANCE_FILE, {"open": [], "closed": []})
    if not isinstance(perf, dict):
        perf = {"open": [], "closed": []}
    open_trades = perf.get("open", [])
    closed = perf.get("closed", [])
    now = int(time.time())

    def cur_dir(aid):
        lab = new_state.get(aid, {}).get("label", "")
        return lab.split("_")[0] if "_" in lab else "NEUTRAL"

    def cur_price(aid):
        return new_state.get(aid, {}).get("data", {}).get("price")

    def cur_data(aid):
        return new_state.get(aid, {}).get("data", {})

    still_open = []
    open_ids = set()
    for tr in open_trades:
        aid = tr["asset"]
        direction = tr["direction"]
        p0 = tr["entry_price"]
        pc = cur_price(aid)
        d_now = cur_dir(aid)
        if pc and p0:
            chg = (pc - p0) / p0 * 100
            favor = chg if direction == "LONG" else -chg  # >0 = a favore
            tr["last_price"] = pc
            tr["pnl_pct"] = round(favor, 2)  # P&L a favore corrente
            tr["last_ts"] = now
            tr["max_favor"] = round(max(tr.get("max_favor", favor), favor), 2)
            tr["min_favor"] = round(min(tr.get("min_favor", favor), favor), 2)
        # Chiusura per ROTTURA STRUTTURA (non per semplice NEUTRAL).
        # Eccezione: se il segnale si è GIRATO in direzione opposta, chiudi comunque.
        flipped = d_now in ("LONG", "SHORT") and d_now != direction
        broken = _structure_broken(direction, cur_data(aid))
        if not (flipped or broken):
            still_open.append(tr)
            open_ids.add(aid)
        else:
            tr["close_ts"] = now
            tr["close_price"] = pc
            tr["duration_h"] = round((now - tr["entry_ts"]) / 3600, 1)
            tr["result_pct"] = tr.get("pnl_pct", 0.0)
            tr["outcome"] = "win" if tr.get("pnl_pct", 0) > 0 else "loss"
            tr["closed_to"] = d_now
            tr["close_reason"] = "flip" if flipped else "struttura"
            closed.append(tr)

    # apri nuovi trade per asset appena entrati in LONG/SHORT (e non già tracciati)
    for aid, s in new_state.items():
        lab = s.get("label", "")
        direction = lab.split("_")[0] if "_" in lab else "NEUTRAL"
        if direction in ("LONG", "SHORT") and aid not in open_ids:
            p0 = s.get("data", {}).get("price")
            if p0:
                still_open.append({
                    "asset": aid,
                    "direction": direction,
                    "entry_ts": now,
                    "entry_price": p0,
                    "entry_strength": lab.split("_")[1] if "_" in lab else "",
                    "last_price": p0,
                    "pnl_pct": 0.0,
                    "max_favor": 0.0,
                    "min_favor": 0.0,
                    "last_ts": now,
                })
                open_ids.add(aid)

    closed = closed[-500:]  # cap
    save_json(PERFORMANCE_FILE, {"open": still_open, "closed": closed})


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
                weekly_bias=data.get("weeklyBias"),
            )
            curr_label = f"{action}_{strength}"
            prev_entry = last_state.get(asset_id, {})
            prev_label = prev_entry.get("label")
            transition_logged = False
            is_transition = prev_label and should_notify(prev_label, curr_label)
            is_new_active = (not prev_label) and (not is_first_run) and action in ("LONG", "SHORT")
            # Cambio di stato "generico": qualsiasi variazione di label (include
            # anche uscite a NEUTRAL e indebolimenti, che NON generano alert Telegram).
            label_changed = bool(prev_label) and (prev_label != curr_label)
            # since_ts = "da quando" l'asset è in QUESTO stato (orario dell'ultima
            # transizione di label). Resta FISSO finché il label non cambia, così
            # l'orario mostrato nel pannello/storico coincide con l'alert Telegram e
            # non si sposta ad ogni run del bot.
            prev_since = prev_entry.get("since_ts")
            since_ts = int(time.time()) if (label_changed or not prev_since) else prev_since

            # --- Alert Telegram: solo eventi rilevanti (ingressi, inversioni, rafforzamenti) ---
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

            # --- Storico history.json: OGNI cambio di stato (audit completo h24) ---
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

    # Traccia performance: apre/aggiorna/chiude i trade e calcola il P&L a favore.
    try:
        update_performance(new_state, last_state)
    except Exception as e:
        print(f"[WARN] update_performance fallito: {e}", flush=True)

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
# audit history: ogni cambio di stato viene registrato in history.json (h24)
