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
# EMA ultra-veloce: SOLO riferimento per l'uscita-esaurimento (non cambia la
# definizione di trend, che resta 12/50). Serve a capire prima quando un movimento
# esteso sta invertendo, senza aspettare che la 12 incroci la 50.
EMA_ULTRA_FAST_4H = 8

# ============================================================================
# FINESTRA OPERATIVA — misurata sui 500 trade storici:
#   aperti venerdi 22:00 -> domenica 12:00 : 90 trade, -28.9 punti, PF 0.63
#   aperti fuori da quella finestra        : 410 trade, -40.1 punti, PF 0.91
# Il 18% delle operazioni produce il 42% delle perdite: liquidita' sottile,
# book vuoti, sweep facili. Blocca SOLO le nuove aperture: le uscite restano
# sempre libere, in qualsiasi momento.
# ============================================================================
WEEKEND_BLOCK = True

# ============================================================================
# TIMING D'INGRESSO — il buco piu' grave del bot: l'escursione favorevole
# mediana dei suoi trade e' +0.36%, cioe' meta' delle operazioni non va MAI in
# guadagno, perche' entra quando vede il flusso e non quando il prezzo e' in
# una zona che ha senso. La zona di valore e' l'area tra EMA21 4h e VWAP
# settimanale (allargata di 0.25 ATR): li' il rapporto rischio/rendimento e'
# al massimo. Non blocca il segnale: lo qualifica.
# ============================================================================
# ============================================================================
# ZONE DI SWING (porting del Pine "Swing Levels Pro" dell'utente)
# Pivot 8/8 sul 4h -> raggruppati in ZONE entro lo 0.45% -> punteggio a stelle:
#   base = numero di tocchi
#   +1 volume forte (>= 66% del massimo)   +1 vicino all'apertura settimanale
#   +1 dentro la Golden Pocket             +1 una media (21/50/200) passa di li'
#   +1 vicino al POC
#   >=5 punti = 3 stelle, >=3 = 2 stelle, altrimenti 1
# L'idea che il bot non aveva: non conta DOVE sta il prezzo rispetto a un
# livello, conta QUANTI riferimenti si accatastano allo stesso prezzo.
# ============================================================================
SWING_ZONES = True
# WAVE: momentum multi-orizzonte (porting dell'indicatore dell'utente).
# Parametri come nel Pine: scala 50 per BTC / 100 per le altre, signal DEMA
# adattiva su ADX, CVD da geometria della candela, stack EMA 8/12/21.
WAVE_ON = True
PIVOT_LEN = 8
ZONE_TOL_PCT = 0.45
VOL_BOOST = 0.66
MAX_ZONES = 30
GP_LOOKBACK = 120
FIB_A = 0.618
FIB_B = 0.705

ENTRY_ZONE = True
EMA_ZONE_4H = 21
ATR_PERIOD = 14

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
    ema_ultra = compute_ema(closes4h, EMA_ULTRA_FAST_4H)
    dist_ultra = ((current_price - ema_ultra) / ema_ultra) * 100 if ema_ultra else None
    return {
        "label": label,
        "emaFast": ema_fast,
        "emaSlow": ema_slow,
        "emaMacro": ema_macro,
        "emaMacroPeriod": ema_macro_period,
        "fastVsSlow": fast_vs_slow,
        "aboveMacro": above_macro,
        "ema8": ema_ultra,           # riferimento uscita-esaurimento
        "distUltra": dist_ultra,     # % prezzo vs EMA 8 (isteresi sull'uscita)
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
    # closedRatio = volume dell'ultima candela CHIUSA (completa) vs media. E' stabile
    # dentro la candela (non dipende da quanto siamo avanti), a differenza di `ratio`
    # che usa la candela in formazione (a inizio candela e' vuota per tutti).
    closed = vols[-2] if len(vols) >= 2 else current
    return {"ratio": current / avg, "closedRatio": closed / avg, "current": current, "avg": avg}


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


def _series_rma(vals, n):
    """RMA (media di Wilder) su tutta la serie."""
    if not vals or len(vals) < n:
        return []
    out = [None] * (n - 1)
    acc = sum(vals[:n]) / n
    out.append(acc)
    for v in vals[n:]:
        acc = (acc * (n - 1) + v) / n
        out.append(acc)
    return out


def _series_ema(vals, n):
    if not vals or len(vals) < n:
        return []
    k = 2.0 / (n + 1)
    out = [None] * (n - 1)
    e = sum(vals[:n]) / n
    out.append(e)
    for v in vals[n:]:
        e = v * k + e * (1 - k)
        out.append(e)
    return out


def _series_dema(vals, n):
    """DEMA = 2*EMA - EMA(EMA): la signal line della WAVE."""
    e1 = _series_ema(vals, n)
    clean = [x for x in e1 if x is not None]
    if len(clean) < n:
        return []
    e2 = _series_ema(clean, n)
    pad = len(e1) - len(clean)
    out = [None] * len(e1)
    for i, v in enumerate(e2):
        if v is None:
            continue
        out[pad + i] = 2 * clean[pad + i - pad] - v if (pad + i) < len(e1) else None
    # ricalcolo lineare piu' semplice e robusto
    out = [None] * len(vals)
    off = len(vals) - len(clean)
    for i in range(len(e2)):
        if e2[i] is None:
            continue
        idx = off + i
        if 0 <= idx < len(vals):
            out[idx] = 2 * clean[i] - e2[i]
    return out


def compute_adx(klines, period=14):
    """ADX di Wilder: misura la FORZA del trend, non la direzione.
    Serve alla WAVE per scegliere quanto reattiva deve essere la signal line."""
    if not klines or len(klines) < period * 2 + 2:
        return None
    trs, pdm, ndm = [], [], []
    for i in range(1, len(klines)):
        h, l = _kline_val(klines[i], "h"), _kline_val(klines[i], "l")
        ph, pl = _kline_val(klines[i - 1], "h"), _kline_val(klines[i - 1], "l")
        pc = _kline_val(klines[i - 1], "c")
        if None in (h, l, ph, pl, pc):
            continue
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
        up, dn = h - ph, pl - l
        pdm.append(up if (up > dn and up > 0) else 0.0)
        ndm.append(dn if (dn > up and dn > 0) else 0.0)
    if len(trs) < period * 2:
        return None
    atr_s = _series_rma(trs, period)
    pdi_s = _series_rma(pdm, period)
    ndi_s = _series_rma(ndm, period)
    dx = []
    for i in range(len(atr_s)):
        if atr_s[i] is None or not atr_s[i] or pdi_s[i] is None or ndi_s[i] is None:
            continue
        pdi = 100 * pdi_s[i] / atr_s[i]
        ndi = 100 * ndi_s[i] / atr_s[i]
        den = pdi + ndi
        dx.append(100 * abs(pdi - ndi) / den if den else 0.0)
    if len(dx) < period:
        return None
    adx_s = _series_rma(dx, period)
    vals = [v for v in adx_s if v is not None]
    return vals[-1] if vals else None


def compute_wave(klines, asset_type="OTHER", sign=7, vol_period=20):
    """WAVE (porting dell'indicatore dell'utente): momentum multi-orizzonte.
    Confronta una media brevissima (5) con quelle a 10/20/40/80 e pesa di piu'
    gli scarti sulle finestre corte: e' un momentum che vede insieme la spinta
    immediata e quella di fondo. La signal line e' una DEMA la cui reattivita'
    dipende dall'ADX (trend forte -> signal veloce, range -> signal lenta).
    Aggiunge CVD (delta proxy dalla geometria della candela) e stack EMA 8/12/21.
    Ritorna lo stato corrente, non la serie."""
    if not klines or len(klines) < 90:
        return None
    closes = [_kline_val(k, "c") for k in klines]
    highs = [_kline_val(k, "h") for k in klines]
    lows = [_kline_val(k, "l") for k in klines]
    vols = [_kline_val(k, "v") or 0.0 for k in klines]
    if any(x is None for x in closes[-90:]):
        return None
    mom_scale = 50.0 if asset_type == "BTC" else 100.0
    vol_mult = 2.0 if asset_type == "BTC" else 1.5

    a0 = _series_rma(closes, 5)
    a1 = _series_rma(closes, 10)
    a2 = _series_rma(closes, 20)
    a3 = _series_rma(closes, 40)
    a4 = _series_rma(closes, 80)
    n = len(closes)
    vol_sma = _series_rma(vols, vol_period)
    dsl = []
    for i in range(n):
        vs = [a0[i] if i < len(a0) else None, a1[i] if i < len(a1) else None,
              a2[i] if i < len(a2) else None, a3[i] if i < len(a3) else None,
              a4[i] if i < len(a4) else None]
        if any(v is None or not v for v in vs):
            continue
        avg, avg1, avg2, avg3, avg4 = vs
        m1 = mom_scale * (avg - avg1) / avg1
        m2 = mom_scale * (avg - avg2) / avg2
        m3 = mom_scale * (avg - avg3) / avg3
        m4 = mom_scale * (avg - avg4) / avg4
        v = (m4 + m3 * 2.0 + m2 * 4.0 + m1 * 8.0) / 4.0
        vsma = vol_sma[i] if i < len(vol_sma) and vol_sma[i] else None
        if vsma and vols[i] > vsma * vol_mult:
            v *= 1.5
        dsl.append(v)
    if len(dsl) < 30:
        return None

    adx = compute_adx(klines) or 0.0
    sig_len = 9 if adx > 25 else (12 if adx > 23 else 16)
    sig_s = _series_dema(dsl, sig_len)
    sig_vals = [x for x in sig_s if x is not None]
    if not sig_vals:
        return None
    wave_v, wave_sig = dsl[-1], sig_vals[-1]

    # CVD proxy: dove chiude la candela dentro il suo range = pressione
    cvd, cvd_hist = 0.0, []
    for i in range(len(klines)):
        h, l, c, v = highs[i], lows[i], closes[i], vols[i]
        if None in (h, l, c):
            cvd_hist.append(cvd)
            continue
        rng = h - l
        buy = v * (c - l) / rng if rng > 0 else v * 0.5
        sell = v * (h - c) / rng if rng > 0 else v * 0.5
        cvd += buy - sell
        cvd_hist.append(cvd)
    cvd_sig_s = _series_ema(cvd_hist, 21)
    cvd_sig_vals = [x for x in cvd_sig_s if x is not None]
    cvd_up = bool(cvd_sig_vals) and cvd_hist[-1] >= cvd_sig_vals[-1]

    e8 = compute_ema(closes, 8)
    e12 = compute_ema(closes, 12)
    e21 = compute_ema(closes, 21)
    bull_stack = bool(e8 and e12 and e21 and e8 > e12 > e21)
    bear_stack = bool(e8 and e12 and e21 and e8 < e12 < e21)

    # velocita' e curvatura -> picco / esaurimento della spinta
    vel = [dsl[i] - dsl[i - 1] for i in range(1, len(dsl))]
    vel_e = _series_ema(vel, 3)
    vel_now = next((x for x in reversed(vel_e) if x is not None), 0.0)
    vel_prev = None
    seen = 0
    for x in reversed(vel_e):
        if x is None:
            continue
        seen += 1
        if seen == 2:
            vel_prev = x
            break
    curv = (vel_now - vel_prev) if vel_prev is not None else 0.0
    min_amp = 0.40 if asset_type == "BTC" else 0.25
    decel = 0
    if len(dsl) > 5:
        for i in range(len(dsl) - 1, max(0, len(dsl) - 6), -1):
            v_i = dsl[i] - dsl[i - 1]
            v_p = dsl[i - 1] - dsl[i - 2] if i >= 2 else 0.0
            c_i = v_i - v_p
            if (dsl[i] > 0 and c_i < 0) or (dsl[i] < 0 and c_i > 0):
                decel += 1
            else:
                break
    trending = adx > 23
    near_peak = wave_v > 0 and vel_now > 0 and decel >= 3 and trending and abs(wave_v) > min_amp
    near_trough = wave_v < 0 and vel_now < 0 and decel >= 3 and trending and abs(wave_v) > min_amp

    bull = wave_v > wave_sig
    return {
        "value": round(wave_v, 3), "signal": round(wave_sig, 3),
        "bull": bull, "adx": round(adx, 1), "trending": trending,
        "velocity": round(vel_now, 3), "curvature": round(curv, 4),
        "cvdUp": cvd_up, "emaStack": "BULL" if bull_stack else ("BEAR" if bear_stack else "MISTA"),
        "nearPeak": near_peak, "nearTrough": near_trough,
        # CONFLUENZA come nel tuo indicatore: stack EMA + CVD + WAVE vs signal
        "confluence": "LONG" if (bull_stack and cvd_up and bull)
                      else ("SHORT" if (bear_stack and not cvd_up and not bull) else None),
    }


def compute_golden_pocket(klines, lookback=GP_LOOKBACK):
    """Golden Pocket sulla gamba dominante: cerca massimo e minimo delle ultime
    `lookback` barre; se il massimo e' piu' recente la gamba e' rialzista e i
    ritracciamenti si misurano dall'alto, altrimenti dal basso."""
    if not klines or len(klines) < 20:
        return None
    seg = klines[-lookback:]
    highs = [_kline_val(k, "h") for k in seg if _kline_val(k, "h") is not None]
    lows = [_kline_val(k, "l") for k in seg if _kline_val(k, "l") is not None]
    if not highs or not lows:
        return None
    hh, ll = max(highs), min(lows)
    rng = hh - ll
    if rng <= 0:
        return None
    i_hh = len(highs) - 1 - highs[::-1].index(hh)
    i_ll = len(lows) - 1 - lows[::-1].index(ll)
    up_leg = i_hh >= i_ll                      # il massimo e' piu' recente
    a = hh - rng * FIB_A if up_leg else ll + rng * FIB_A
    b = hh - rng * FIB_B if up_leg else ll + rng * FIB_B
    return {"lo": min(a, b), "hi": max(a, b), "upLeg": up_leg, "legHigh": hh, "legLow": ll}


def _pivots(klines, length=PIVOT_LEN):
    """Pivot high/low stile ta.pivothigh/pivotlow: estremo con `length` barre
    piu' basse (o piu' alte) a destra e a sinistra."""
    out = []
    n = len(klines)
    for i in range(length, n - length):
        h = _kline_val(klines[i], "h")
        l = _kline_val(klines[i], "l")
        v = _kline_val(klines[i], "v") or 0.0
        if h is None or l is None:
            continue
        win = klines[i - length:i + length + 1]
        hs = [_kline_val(k, "h") for k in win if _kline_val(k, "h") is not None]
        ls = [_kline_val(k, "l") for k in win if _kline_val(k, "l") is not None]
        if hs and h >= max(hs):
            out.append({"price": h, "isHigh": True, "vol": v, "i": i})
        if ls and l <= min(ls):
            out.append({"price": l, "isHigh": False, "vol": v, "i": i})
    return out


def compute_swing_zones(klines4h, current_price, weekly_open=None, poc=None,
                        emas=None, golden_pocket=None):
    """Zone di swing con punteggio a stelle (porting del Pine dell'utente).
    Ritorna la lista ordinata per distanza dal prezzo."""
    if not klines4h or len(klines4h) < PIVOT_LEN * 2 + 5 or not current_price:
        return []
    zones = []
    for p in _pivots(klines4h):
        price, tol = p["price"], p["price"] * ZONE_TOL_PCT / 100.0
        best, idx = tol, -1
        for j, z in enumerate(zones):
            d = abs(z["price"] - price)
            if d <= best:
                best, idx = d, j
        if idx >= 0:
            z = zones[idx]
            z["price"] = (z["price"] * z["count"] + price) / (z["count"] + 1)
            z["count"] += 1
            z["vol"] += p["vol"]
        else:
            zones.append({"price": price, "count": 1, "vol": p["vol"], "isHigh": p["isHigh"]})
        if len(zones) > MAX_ZONES:
            zones.pop(0)
    if not zones:
        return []
    max_vol = max(z["vol"] for z in zones) or 1.0
    poc_price = poc.get("poc") if isinstance(poc, dict) else None
    out = []
    for z in zones:
        tol_w = z["price"] * ZONE_TOL_PCT / 100.0 * 1.5
        score = z["count"]
        if z["vol"] >= max_vol * VOL_BOOST:
            score += 1
        if weekly_open and abs(z["price"] - weekly_open) <= tol_w:
            score += 1
        if golden_pocket and golden_pocket["lo"] <= z["price"] <= golden_pocket["hi"]:
            score += 1
        if emas and any(e and abs(z["price"] - e) <= tol_w for e in emas):
            score += 1
        if poc_price and abs(z["price"] - poc_price) <= tol_w:
            score += 1
        stars = 3 if score >= 5 else 2 if score >= 3 else 1
        out.append({"price": round(z["price"], 8), "count": z["count"], "stars": stars,
                    "isHigh": z["isHigh"],
                    "distPct": round((z["price"] - current_price) / current_price * 100, 2)})
    out.sort(key=lambda x: abs(x["distPct"]))
    return out


def nearest_zone(zones, direction, current_price, max_atr=None, atr=None, min_stars=2):
    """Zona forte piu' vicina utile al trade: supporto sotto per un LONG,
    resistenza sopra per uno SHORT."""
    if not zones or direction not in ("LONG", "SHORT"):
        return None
    cands = []
    for z in zones:
        if z["stars"] < min_stars:
            continue
        if direction == "LONG" and z["price"] > current_price:
            continue
        if direction == "SHORT" and z["price"] < current_price:
            continue
        if atr and max_atr and abs(z["price"] - current_price) > max_atr * atr:
            continue
        cands.append(z)
    if not cands:
        return None
    return sorted(cands, key=lambda x: abs(x["distPct"]))[0]


def compute_atr(klines, period=ATR_PERIOD):
    """ATR classico sulle candele 4h: misura di volatilita' per dimensionare
    zona d'ingresso, stop e target in modo proporzionale alla coin."""
    if not klines or len(klines) < period + 1:
        return None
    trs = []
    for i in range(1, len(klines)):
        h = _kline_val(klines[i], "h")
        l = _kline_val(klines[i], "l")
        pc = _kline_val(klines[i - 1], "c")
        if h is None or l is None or pc is None:
            continue
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    if len(trs) < period:
        return None
    return sum(trs[-period:]) / period


def compute_entry_zone(klines4h, current_price, vwap_w, direction_hint=None,
                       zones=None):
    """Zona di valore dove il rapporto rischio/rendimento e' migliore.
    Area tra EMA21(4h) e VWAP settimanale, allargata di 0.25 ATR. Se i due
    riferimenti distano oltre 1.5 ATR (coin molto estesa) vale solo la EMA21,
    altrimenti la zona diventa larghissima e inutile.
    Ritorna anche stop e target proporzionali all'ATR."""
    if not klines4h or not current_price:
        return None
    closes = [_kline_val(k, "c") for k in klines4h]
    closes = [c for c in closes if c is not None]
    ema21 = compute_ema(closes, EMA_ZONE_4H)
    atr = compute_atr(klines4h)
    if not ema21 or not atr:
        return None
    vw = None
    if isinstance(vwap_w, dict):
        vw = vwap_w.get("vwap")
    elif isinstance(vwap_w, (int, float)):
        vw = vwap_w
    if vw and abs(ema21 - vw) <= 1.5 * atr:
        lo = min(ema21, vw) - 0.25 * atr
        hi = max(ema21, vw) + 0.25 * atr
    else:
        lo = ema21 - 0.5 * atr
        hi = ema21 + 0.5 * atr
    src = "EMA21/VWAP"
    # Se esiste una ZONA FORTE (>=2 stelle) nella direzione del trade entro 2 ATR,
    # quella batte la zona statistica: e' un livello dove il prezzo ha gia'
    # reagito piu' volte, non una media calcolata.
    if zones and direction_hint:
        z = nearest_zone(zones, direction_hint, current_price, max_atr=2.0, atr=atr, min_stars=2)
        if z:
            lo = z["price"] - 0.35 * atr
            hi = z["price"] + 0.35 * atr
            src = "zona " + "*" * z["stars"] + f" ({z['count']}x)"
    dist = 0.0
    if current_price > hi:
        dist = (current_price - hi) / atr
    elif current_price < lo:
        dist = (current_price - lo) / atr
    return {"lo": lo, "hi": hi, "ema21": ema21, "atr": atr, "src": src,
            "inZone": lo <= current_price <= hi,
            "distATR": round(dist, 2)}


def entry_state(zone, direction, current_price):
    """Stato operativo del segnale rispetto alla zona di valore.
    NON invalida mai il segnale: dice solo se e' il momento giusto."""
    if not zone or not direction or direction not in ("LONG", "SHORT"):
        return None
    if zone["inZone"]:
        return "PRONTO"
    if direction == "LONG":
        return "INSEGUIMENTO" if current_price > zone["hi"] else "SOTTO ZONA"
    return "INSEGUIMENTO" if current_price < zone["lo"] else "SOPRA ZONA"


def entry_levels(zone, direction, current_price):
    """Stop e target proporzionali alla volatilita' (ATR 4h)."""
    if not zone or direction not in ("LONG", "SHORT") or not current_price:
        return None
    atr = zone["atr"]
    sl = current_price - 1.5 * atr if direction == "LONG" else current_price + 1.5 * atr
    risk = abs(current_price - sl)
    if not risk:
        return None
    tp1 = current_price + (1.5 * risk if direction == "LONG" else -1.5 * risk)
    tp2 = current_price + (2.5 * risk if direction == "LONG" else -2.5 * risk)
    dist_pct = risk / current_price * 100
    lev = max(1, min(20, int(70 / dist_pct))) if dist_pct else 1
    return {"sl": sl, "tp1": tp1, "tp2": tp2,
            "riskPct": round(dist_pct, 2), "maxLev": lev}


def in_weekend_block(ts=None):
    """True dentro la finestra morta: venerdi 22:00 -> domenica 12:00 (ora IT)."""
    if ITALY_TZ is not None:
        d = datetime.fromtimestamp(ts or time.time(), ITALY_TZ)
    else:
        d = datetime.fromtimestamp(ts or time.time())
    wd, hh = d.weekday(), d.hour   # lunedi=0 ... domenica=6
    if wd == 4 and hh >= 22:
        return True
    if wd == 5:
        return True
    if wd == 6 and hh < 12:
        return True
    return False


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
            # Zone di swing con punteggio a stelle (porting dell'indicatore utente)
            gp = compute_golden_pocket(k4h) if SWING_ZONES else None
            wave = compute_wave(k4h, "BTC" if aid == "BTC" else "OTHER") if WAVE_ON else None
            _c4 = [_kline_val(k, "c") for k in k4h if _kline_val(k, "c") is not None]
            _emas = [compute_ema(_c4, 21), compute_ema(_c4, 50), compute_ema(_c4, 200)] if _c4 else []
            zones = compute_swing_zones(k4h, current_price,
                                        weekly_open=(weekly_bias or {}).get("weeklyOpen"),
                                        poc=poc, emas=_emas, golden_pocket=gp) if SWING_ZONES else []
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
                "atr": compute_atr(k4h),
                "goldenPocket": gp,
                "wave": wave,
                "zones": zones[:8] if zones else [],
                "entryZone": compute_entry_zone(k4h, current_price, vwap_w, zones=zones),
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
    "zones": 2,    # il trade arriva su una ZONA FORTE (>=2 stelle): livello dove il
                   # prezzo ha gia' reagito piu' volte, non una media calcolata
    "wave": 3,     # MOMENTUM (indicatore WAVE dell'utente): DSL multi-orizzonte
                   # + stack EMA 8/12/21 + CVD. Peso alto: e' l'unico fattore
                   # che misura l'ACCELERAZIONE, non lo stato
    # --- I due sotto NON danno bonus: sono PENALITÀ contrarian agli estremi ---
    "funding": 2,  # PENALITÀ se funding bollente/gelido contro il trade
    "lsr": 1,      # PENALITÀ se L/S retail troppo carico nel verso del trade
}


def _exhaustion_reversal(direction, trend, vwap_w, delta):
    """USCITA PER ESAURIMENTO (porta solo a NEUTRAL, mai flip). Un movimento ESTESO
    (prezzo oltre ±4% dalla VWAP settimanale = sceso/salito tanto) che INVERTE, con
    DOPPIA conferma: prezzo che riprende la EMA 8 con margine (isteresi ±0.5%) +
    delta reale che smette di spingere contro. Solo per USCIRE prima senza aspettare
    che la EMA 12/50 giri. Simmetrico long/short. Per RIENTRARE serve tornare oltre la
    EMA 8 dall'altro lato (il ribasso/rialzo deve riprendere): niente ping-pong.
    Soglie 'al centro' (tarabili): estensione 4%, isteresi 0.5%, delta -0.02/+0.02."""
    if not trend or not vwap_w or not delta:
        return False
    vd = vwap_w.get("distance")      # % prezzo vs VWAP settimanale
    du = trend.get("distUltra")      # % prezzo vs EMA 8
    dr = delta.get("ratio")          # delta reale [-1, +1]
    if vd is None or du is None or dr is None:
        return False
    if direction == "SHORT":
        # sceso tanto (>4% sotto VWAP) + ripreso sopra EMA8 (+0.5%) + vendita esaurita
        return vd < -4.0 and du > 0.5 and dr > -0.02
    if direction == "LONG":
        # salito tanto (>4% sopra VWAP) + perso la EMA8 (-0.5%) + acquisti esauriti
        return vd > 4.0 and du < -0.5 and dr < 0.02
    return False


def compute_action_with_confluence(bias, signal_4h, trend, obv, fvg, poc,
                                   current_price, oi_change_4h=None,
                                   funding=None, lsr=None, thresholds=None,
                                   vwap_w=None, vwap_m=None, delta=None,
                                   px_change_24h=None, weekly_bias=None, rvol=None,
                                   zones_list=None, wave=None):
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

    # USCITA PER ESAURIMENTO: un movimento esteso che inverte va a NEUTRAL subito,
    # senza aspettare che la EMA 12/50 giri. Solo per uscire (mai flip). Vedi helper.
    if direction in ("LONG", "SHORT") and _exhaustion_reversal(direction, trend, vwap_w, delta):
        return ("NEUTRAL", "weak", 0, 0)

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

    # 7c) WAVE — momentum. Punto pieno se la WAVE e' dalla parte del trade;
    #     mezzo punto se la confluenza completa (EMA+CVD+WAVE) e' allineata.
    if wave:
        total += W["wave"]
        w_ok = (direction == "LONG" and wave.get("bull")) or (direction == "SHORT" and not wave.get("bull"))
        if w_ok:
            score += W["wave"] * (1.0 if wave.get("confluence") == direction else 0.66)

    # 8) ZONE DI SWING: il prezzo sta arrivando su un livello a 2-3 stelle?
    #    Supporto sotto per un LONG, resistenza sopra per uno SHORT: e' il posto
    #    dove il movimento ha piu' probabilita' di reagire.
    if zones_list:
        total += W["zones"]
        _atr_z = None
        for _z in zones_list:
            if _z.get("stars", 0) >= 2:
                _atr_z = True
                break
        near = nearest_zone(zones_list, direction, current_price, min_stars=2)
        if near and abs(near["distPct"]) <= 1.5:
            score += W["zones"]

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

    # === GUARD LIQUIDITÀ (volume fantasma) ===
    # Se l'ultima candela 4h CHIUSA ha volume molto sotto la media (< 30%), il mercato
    # è fermo/illiquido e il segnale è poco affidabile (OBV/POC su volume sottile valgono
    # poco — es. EIGEN). Usa la candela CHIUSA, non quella in formazione (che a inizio
    # candela è vuota per tutti). strong/full -> moderate; moderate -> NEUTRAL.
    if rvol and rvol.get("closedRatio") is not None and rvol["closedRatio"] < 0.30:
        if strength in ("full", "strong"):
            strength = "moderate"
        elif strength == "moderate":
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


# ============================================================================
# FILTRI OPERATIVI (taratura sui 500 trade storici)
#   - moderate: 45% di direzione corretta = rumore -> niente alert Telegram,
#     restano in state.json solo per l'ampiezza di flusso
#   - strong: 61% direzione corretta, PF 1.23 senza flip -> gli unici operativi
#   - flip diretto LONG<->SHORT: 27 trade, 0 vinti, media -3.07% -> vietato
# ============================================================================
NOTIFY_STRONG_ONLY = True   # alert Telegram solo sui segnali strong/full
# ...MA con una via alternativa: un segnale "moderate" con una confluenza alta
# passa comunque. Nato dal caso ADA (03/08): LONG moderate al 50% ha fatto +3.1%
# e non ha avvisato nessuno, mentre ALGO strong al 77.3% ha fatto +7.1%.
# L'etichetta e' una soglia grossolana: il numero continuo e' piu' onesto.
NOTIFY_MIN_CONF = 60.0      # % di confluenza che rende notificabile anche un moderate
NOTIFY_EXITS = True         # avvisa anche quando una posizione strong si chiude
ANTI_FLIP = True            # mai inversione diretta: passa da NEUTRAL almeno un run

# FILTRO AMPIEZZA DI MERCATO: niente ingressi controcorrente quando il mercato si
# muove in blocco. Misurato su 42 trade nati dopo il riavvio del 26/07: i LONG
# aperti durante una discesa generale hanno chiuso con PF 0.06 (19 trade), gli
# SHORT nella stessa fase PF 1.20 (23 trade). Blocca solo le APERTURE nuove:
# le posizioni gia' aperte restano gestite dalla struttura come sempre.
BREADTH_FILTER = True
BREADTH_LONG_MIN = 25.0   # se meno del 25% delle coin e' in rialzo 24h -> niente nuovi LONG
BREADTH_SHORT_MAX = 75.0  # se piu' del 75% e' in rialzo -> niente nuovi SHORT

# TRAILING VIRTUALE — SOLO MISURA, NON CHIUDE NULLA.
# A ogni run controlla se una posizione ha restituito oltre TRAIL_PCT del suo
# picco: in quel caso registra il livello di uscita che il trailing avrebbe
# ottenuto. Il trade resta aperto e gestito come sempre dalla struttura: alla
# chiusura avremo affiancati "risultato reale" e "risultato col trailing",
# cosi' la decisione se attivarlo davvero si prende sui numeri e non a intuito.
# Misurato sulle 16 posizioni reali del 26-30/07/2026, simulando il trailing
# come lavora DAVVERO (picco aggiornato candela per candela, senza sapere in
# anticipo dove arrivera'). Non fare nulla: +73.5 punti.
#     30% del picco da +2%  ->  27.6   (disastroso: esce al primo respiro)
#     30% del picco da +5%  ->  55.3
#     30% del picco da +8%  ->  71.1
#     30% del picco da +10% ->  78.7   <-- il migliore, ma solo +5 punti
#     50% del picco da +5%  ->  77.7
# Conclusione: il trailing aiuta solo se si attiva TARDI. Attivarlo presto
# uccide i trade prima che il movimento inizi. Per questo la soglia e' a +10%.
TRAIL_TRACK = True
TRAIL_PCT = 0.30        # restituzione massima tollerata del picco
TRAIL_MIN_PEAK = 10.0   # si arma solo da +10% di guadagno (vedi tabella sopra)


def compute_market_breadth(all_data):
    """Percentuale di coin dell'universo in rialzo sulle 24h.
    E' la fotografia del flusso: 10% = discesa generalizzata, 90% = melt-up.
    Restituisce None se i dati validi sono troppo pochi per essere significativi."""
    vals = [d.get("priceChange24h") for d in all_data.values()
            if isinstance(d, dict) and not d.get("error")]
    vals = [v for v in vals if isinstance(v, (int, float))]
    if len(vals) < 10:
        return None
    return sum(1 for v in vals if v > 0) / len(vals) * 100.0

_STRENGTHS = {"weak": 0, "moderate": 1, "strong": 2, "full": 3}


def _is_operative(strength, conf_pct=None):
    """Un segnale genera alert se e' strong/full OPPURE se la sua confluenza
    supera NOTIFY_MIN_CONF: cosi' un moderate molto convincente non resta muto."""
    if not NOTIFY_STRONG_ONLY:
        return True
    if strength in ("strong", "full"):
        return True
    return conf_pct is not None and conf_pct >= NOTIFY_MIN_CONF


def should_notify(prev_label, curr_label, conf_pct=None, prev_conf_pct=None):
    """conf_pct = confluenza attuale in %, prev_conf_pct = quella precedente.
    Servono a far passare i moderate convincenti (>= NOTIFY_MIN_CONF)."""
    if prev_label == curr_label:
        return False
    prev_a, prev_s = prev_label.split("_") if "_" in prev_label else (prev_label, "weak")
    curr_a, curr_s = curr_label.split("_") if "_" in curr_label else (curr_label, "weak")
    # USCITA: una posizione che era operativa e va a NEUTRAL va comunicata
    if NOTIFY_EXITS and prev_a in ("LONG", "SHORT") and curr_a == "NEUTRAL" \
            and _is_operative(prev_s, prev_conf_pct):
        return True
    if prev_a == "NEUTRAL" and curr_a in ("LONG", "SHORT"):
        return _is_operative(curr_s, conf_pct)
    if (prev_a == "LONG" and curr_a == "SHORT") or (prev_a == "SHORT" and curr_a == "LONG"):
        return _is_operative(curr_s, conf_pct)
    if prev_a == curr_a and prev_a in ("LONG", "SHORT"):
        if _STRENGTHS.get(curr_s, 0) > _STRENGTHS.get(prev_s, 0):
            return _is_operative(curr_s, conf_pct)
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
    # --- blocco TIMING: zona di valore, stop e target ---
    entry_block = ""
    z = d.get("entryZone")
    dir_now = curr_a if curr_a in ("LONG", "SHORT") else None
    if z and dir_now:
        st = entry_state(z, dir_now, d.get("price"))
        lv = entry_levels(z, dir_now, d.get("price"))
        icona = {"PRONTO": "🎯", "INSEGUIMENTO": "⚠️", "SOTTO ZONA": "⏳", "SOPRA ZONA": "⏳"}.get(st, "")
        nota = {"PRONTO": "prezzo in zona di valore: qui il rischio/rendimento e' al massimo",
                "INSEGUIMENTO": f"prezzo oltre la zona di {abs(z.get('distATR') or 0)} ATR: stai inseguendo",
                "SOTTO ZONA": "prezzo non ancora in zona: attendi il rientro",
                "SOPRA ZONA": "prezzo non ancora in zona: attendi il rientro"}.get(st, "")
        srcz = z.get("src") or "EMA21/VWAP"
        entry_block = (f"\n<b>— Timing —</b>\n"
                       f"{icona} <b>{st}</b> · {nota}\n"
                       f"<b>Zona:</b> {fmt_price(z['lo'])} – {fmt_price(z['hi'])} <i>({srcz})</i>\n")
        if lv:
            entry_block += (f"<b>SL:</b> {fmt_price(lv['sl'])} ({lv['riskPct']}%) · "
                            f"<b>TP1</b> {fmt_price(lv['tp1'])} · <b>TP2</b> {fmt_price(lv['tp2'])}\n"
                            f"<b>Leva max:</b> {lv['maxLev']}x\n")
    # livelli forti piu' vicini (zone a 2-3 stelle)
    zl = d.get("zones") or []
    strong_lv = [z for z in zl if z.get("stars", 0) >= 2][:3]
    if strong_lv:
        parts = [f"{'★' * z['stars']} {fmt_price(z['price'])} ({z['count']}x, {z['distPct']:+.1f}%)"
                 for z in strong_lv]
        entry_block += "<b>Livelli forti:</b> " + " · ".join(parts) + "\n"
    wv = d.get("wave")
    if wv:
        frecc = "▲" if wv.get("bull") else "▼"
        # ATTENZIONE: mai < o > nel testo, Telegram li interpreta come tag HTML
        # e rifiuta l'intero messaggio (errore "Unsupported start tag").
        stack = {"BULL": "8 › 12 › 21 ▲", "BEAR": "8 ‹ 12 ‹ 21 ▼"}.get(wv.get("emaStack"), "intrecciate ↔")
        cvdtxt = "compratori ▲" if wv.get("cvdUp") else "venditori ▼"
        entry_block += (f"<b>WAVE:</b> {wv['value']:+.2f} {frecc} signal {wv['signal']:+.2f} · "
                        f"ADX {wv['adx']:.0f} {'trend' if wv.get('trending') else 'range'}\n"
                        f"<b>EMA 8/12/21:</b> {stack} · <b>CVD:</b> {cvdtxt}\n")
        if wv.get("confluence"):
            entry_block += f"✅ <b>Confluenza WAVE {wv['confluence']}</b> (EMA + CVD + momentum allineati)\n"
        if wv.get("nearPeak"):
            entry_block += "⚠️ <b>pre-picco</b>: il momentum sta decelerando, spinta in esaurimento\n"
        if wv.get("nearTrough"):
            entry_block += "⚠️ <b>pre-minimo</b>: il ribasso sta decelerando\n"

    gpx = d.get("goldenPocket")
    if gpx and d.get("price") and gpx["lo"] <= d["price"] <= gpx["hi"]:
        entry_block += "🟡 <b>prezzo dentro la Golden Pocket</b>\n"

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
    testa = "🎯 <b>PRONTO — prezzo in zona</b>\n" if prev == "READY" else ""
    msg = (
        testa +
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
        f"<b>Signal 4h:</b> {t['signal']}\n"
        f"{entry_block}\n"
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
    # Uscita per esaurimento: movimento esteso che inverte (EMA8 + delta) -> chiudi
    # prima, senza aspettare che l'EMA 12/50 giri. Stessa condizione del segnale.
    if _exhaustion_reversal(direction, data.get("trend"), data.get("vwapW"), data.get("delta")):
        return True
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


def _conf_raw_of(aid, state):
    """Punteggio grezzo della confluenza al momento dell'ingresso, es. '17/23'."""
    c = (state.get(aid) or {}).get("confluence") or {}
    sc, tot = c.get("score"), c.get("total")
    if sc is None or not tot:
        return None
    return f"{sc}/{tot}"


def _conf_pct_of(aid, state):
    """Frazione di confluenza in percentuale: e' il numero continuo su cui
    tarare soglie e size, al posto delle etichette strong/moderate."""
    c = (state.get(aid) or {}).get("confluence") or {}
    sc, tot = c.get("score"), c.get("total")
    if sc is None or not tot:
        return None
    return round(sc / tot * 100, 1)


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
    # ANTI-CHURN: memoria delle chiusure per rottura di struttura avvenute
    # mentre l'etichetta era ANCORA nella stessa direzione. Senza questo, il
    # tracker chiudeva e riapriva la stessa posizione nello stesso run, all
    # infinito: POL risultava aperta/chiusa 8 volte in 3 giorni pur essendo
    # sempre lo stesso short. Finche' l'etichetta non passa da NEUTRAL (o non
    # si gira), quella coin non puo' riaprire nella direzione bloccata.
    cooldown = perf.get("cooldown", {})
    if not isinstance(cooldown, dict):
        cooldown = {}
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
            # PICCO: oltre al valore massimo registro QUANDO e a che prezzo è avvenuto.
            # Serve per misurare con precisione quanto viene restituito dai massimi e
            # per poter simulare un eventuale trailing sui dati reali (non a stima).
            prev_peak = tr.get("max_favor", favor)
            tr["max_favor"] = round(max(prev_peak, favor), 2)
            if favor > prev_peak or "peak_ts" not in tr:
                tr["peak_ts"] = now
                tr["peak_price"] = pc
            prev_trough = tr.get("min_favor", favor)
            tr["min_favor"] = round(min(prev_trough, favor), 2)
            if favor < prev_trough or "trough_ts" not in tr:
                tr["trough_ts"] = now
            # TRAILING VIRTUALE: registra (una sola volta) dove sarebbe uscito
            if TRAIL_TRACK and "trail_exit_pct" not in tr:
                _pk = tr.get("max_favor", 0.0) or 0.0
                if _pk >= TRAIL_MIN_PEAK:
                    _lvl = _pk * (1.0 - TRAIL_PCT)
                    if favor <= _lvl:
                        tr["trail_exit_pct"] = round(_lvl, 2)
                        tr["trail_exit_ts"] = now
                        tr["trail_peak_at_exit"] = round(_pk, 2)
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
            # RESTITUZIONE: quanto del massimo è stato lasciato sul tavolo, in punti
            # e in quota del picco. giveback_share = 1.0 significa aver restituito tutto.
            _peak = tr.get("max_favor", 0.0) or 0.0
            _res = tr.get("result_pct", 0.0) or 0.0
            tr["giveback_pct"] = round(_peak - _res, 2)
            tr["giveback_share"] = round((_peak - _res) / _peak, 2) if _peak > 0 else 0.0
            tr["hours_after_peak"] = round((now - tr.get("peak_ts", tr["entry_ts"])) / 3600, 1)
            # confronto finale: cosa avrebbe reso il trailing su questo trade
            if TRAIL_TRACK:
                _tr = tr.get("trail_exit_pct")
                tr["trail_result_pct"] = _tr if _tr is not None else tr.get("result_pct", 0.0)
                tr["trail_delta"] = round(tr["trail_result_pct"] - tr.get("result_pct", 0.0), 2)
            tr["outcome"] = "win" if tr.get("pnl_pct", 0) > 0 else "loss"
            tr["closed_to"] = d_now
            tr["close_reason"] = "flip" if flipped else "struttura"
            # se chiudo per struttura ma il segnale e' ancora nella stessa
            # direzione, blocco la riapertura finche' l'etichetta non cambia
            if not flipped and d_now == direction:
                cooldown[aid] = {"dir": direction, "ts": now}
            closed.append(tr)

    # apri nuovi trade per asset appena entrati in LONG/SHORT (e non già tracciati)
    for aid, s in new_state.items():
        lab = s.get("label", "")
        direction = lab.split("_")[0] if "_" in lab else "NEUTRAL"
        # il blocco anti-churn cade appena l'etichetta cambia direzione o va a NEUTRAL
        cd = cooldown.get(aid)
        if cd and cd.get("dir") != direction:
            cooldown.pop(aid, None)
            cd = None
        if cd:
            continue
        if direction in ("LONG", "SHORT") and aid not in open_ids:
            p0 = s.get("data", {}).get("price")
            if p0:
                still_open.append({
                    "asset": aid,
                    "direction": direction,
                    "entry_ts": now,
                    "entry_price": p0,
                    "entry_strength": lab.split("_")[1] if "_" in lab else "",
                    # FRAZIONE DI CONFLUENZA ESATTA (0-100). Le etichette
                    # strong/moderate sono soglie arbitrarie: questo numero
                    # permette di trovare la soglia giusta sui dati veri, o di
                    # dimensionare la size in modo continuo invece che binario.
                    "entry_conf_pct": _conf_pct_of(aid, new_state),
                    "entry_conf": _conf_raw_of(aid, new_state),
                    # contesto d'ingresso: serve a capire QUALI condizioni pagano
                    "entry_state": ((new_state.get(aid) or {}).get("entry") or {}).get("state"),
                    "entry_wave": (((new_state.get(aid) or {}).get("data") or {}).get("wave") or {}).get("confluence"),
                    "entry_zone_src": ((new_state.get(aid) or {}).get("entry") or {}).get("zoneSrc"),
                    "last_price": p0,
                    "pnl_pct": 0.0,
                    "max_favor": 0.0,
                    "min_favor": 0.0,
                    "last_ts": now,
                })
                open_ids.add(aid)

    closed = closed[-500:]  # cap
    # pulizia cooldown: via le coin che non sono piu' nello state
    for k in list(cooldown.keys()):
        if k not in new_state:
            cooldown.pop(k, None)
    save_json(PERFORMANCE_FILE, {"open": still_open, "closed": closed, "cooldown": cooldown})


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
    market_breadth = compute_market_breadth(all_data)
    if market_breadth is not None:
        print(f"[BREADTH] {market_breadth:.0f}% delle coin in rialzo 24h", flush=True)
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
                rvol=data.get("rvol"),
                zones_list=data.get("zones"),
                wave=data.get("wave"),
            )
            curr_label = f"{action}_{strength}"
            prev_entry = last_state.get(asset_id, {})
            prev_label = prev_entry.get("label")
            # ANTI-FLIP: mai passare direttamente da LONG a SHORT (o viceversa).
            # L'inversione diretta cade nel punto di massima confusione del mercato:
            # storicamente 27 trade chiusi cosi', 0 vinti, media -3.07%.
            # Si passa da NEUTRAL per almeno un run: il vecchio trade si chiude come
            # "struttura" e il nuovo si apre solo se il segnale regge al run dopo.
            if ANTI_FLIP and prev_label:
                prev_dir = prev_label.split("_")[0] if "_" in prev_label else prev_label
                if prev_dir in ("LONG", "SHORT") and action in ("LONG", "SHORT") and action != prev_dir:
                    action, strength = "NEUTRAL", "weak"
                    curr_label = "NEUTRAL_weak"
                    print(f"  [ANTI-FLIP] {asset_id}: inversione diretta bloccata, passo da NEUTRAL", flush=True)
            # FINESTRA OPERATIVA: nel weekend morto niente NUOVE aperture
            # (le uscite e la gestione restano sempre attive).
            if WEEKEND_BLOCK and in_weekend_block():
                prev_dir_w = prev_label.split("_")[0] if (prev_label and "_" in prev_label) else "NEUTRAL"
                if action in ("LONG", "SHORT") and action != prev_dir_w:
                    action, strength, curr_label = "NEUTRAL", "weak", "NEUTRAL_weak"
                    print(f"  [WEEKEND] {asset_id}: apertura bloccata (ven 22 -> dom 12)", flush=True)

            # FILTRO AMPIEZZA: non aprire contro un mercato che si muove in blocco.
            # Agisce solo se non c'e' gia' una posizione aperta nella stessa direzione
            # (cioe' blocca le nuove entrate, non la gestione di quelle in corso).
            if BREADTH_FILTER and market_breadth is not None:
                prev_dir_b = prev_label.split("_")[0] if (prev_label and "_" in prev_label) else "NEUTRAL"
                if action != prev_dir_b:
                    if action == "LONG" and market_breadth < BREADTH_LONG_MIN:
                        action, strength, curr_label = "NEUTRAL", "weak", "NEUTRAL_weak"
                        print(f"  [BREADTH] {asset_id}: LONG bloccato ({market_breadth:.0f}% in rialzo)", flush=True)
                    elif action == "SHORT" and market_breadth > BREADTH_SHORT_MAX:
                        action, strength, curr_label = "NEUTRAL", "weak", "NEUTRAL_weak"
                        print(f"  [BREADTH] {asset_id}: SHORT bloccato ({market_breadth:.0f}% in rialzo)", flush=True)
            transition_logged = False
            conf_pct_now = round(conf_score / conf_total * 100, 1) if conf_total else None
            _pc = (prev_entry.get("confluence") or {})
            prev_conf_pct = (round(_pc["score"] / _pc["total"] * 100, 1)
                             if _pc.get("total") else None)
            is_transition = prev_label and should_notify(prev_label, curr_label,
                                                         conf_pct_now, prev_conf_pct)
            is_new_active = ((not prev_label) and (not is_first_run)
                             and action in ("LONG", "SHORT")
                             and _is_operative(strength, conf_pct_now))
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
            # TIMING D'INGRESSO: dove si trova il prezzo rispetto alla zona di valore
            zone = data.get("entryZone")
            # se esiste una zona forte nella direzione del trade, quella diventa
            # l'area d'ingresso: batte la zona statistica EMA21/VWAP
            if ENTRY_ZONE and zone and zone.get("atr") and action in ("LONG", "SHORT"):
                _z = nearest_zone(data.get("zones"), action, data.get("price"),
                                  max_atr=2.0, atr=zone["atr"], min_stars=2)
                if _z:
                    _a = zone["atr"]
                    zone = dict(zone, lo=_z["price"] - 0.35 * _a, hi=_z["price"] + 0.35 * _a,
                                src=f"zona {'★' * _z['stars']} ({_z['count']}x)")
                    _p = data.get("price")
                    zone["inZone"] = zone["lo"] <= _p <= zone["hi"]
                    zone["distATR"] = round((_p - zone["hi"]) / _a if _p > zone["hi"]
                                            else ((_p - zone["lo"]) / _a if _p < zone["lo"] else 0.0), 2)
            est = entry_state(zone, action, data.get("price")) if ENTRY_ZONE else None
            lev = entry_levels(zone, action, data.get("price")) if (ENTRY_ZONE and est) else None
            prev_entry_state = (prev_entry.get("entry") or {}).get("state")
            became_ready = (est == "PRONTO" and prev_entry_state != "PRONTO"
                            and action in ("LONG", "SHORT")
                            and _is_operative(strength, conf_pct_now))
            if became_ready:
                print(f"  [PRONTO] {asset_id} {action}: prezzo in zona di valore", flush=True)

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
                    "atr": data.get("atr"),
                    "entryZone": zone,
                    # pubblicati anche nello state: servono al pannello per
                    # mostrare le stesse cose che il motore ha gia' valutato
                    "wave": data.get("wave"),
                    "zones": data.get("zones"),
                    "goldenPocket": data.get("goldenPocket"),
                },
                "entry": ({"state": est,
                           "zoneSrc": (zone or {}).get("src"),
                           "zoneLo": zone.get("lo") if zone else None,
                           "zoneHi": zone.get("hi") if zone else None,
                           "distATR": zone.get("distATR") if zone else None,
                           "sl": lev.get("sl") if lev else None,
                           "tp1": lev.get("tp1") if lev else None,
                           "tp2": lev.get("tp2") if lev else None,
                           "riskPct": lev.get("riskPct") if lev else None,
                           "maxLev": lev.get("maxLev") if lev else None} if est else None),
            }
            # ALERT "PRONTO": il segnale operativo entra in zona di valore.
            # E' l'avviso che prima non esisteva: non "c'e' un segnale", ma
            # "adesso il prezzo e' dove conviene entrare".
            if became_ready and not is_transition:
                transitions.append({
                    "ts": int(time.time()), "asset": asset_id,
                    "from": "READY", "to": curr_label,
                    "bias": bias, "signal": signal, "data": data,
                    "confluence": {"score": conf_score, "total": conf_total},
                })
                transition_logged = True
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
