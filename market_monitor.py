"""
Bullseye Market Monitor — an educational dashboard.

What it does: pulls price/volume data, computes common technical indicators,
and surfaces neutral *observations* for you to investigate and learn from.

What it deliberately does NOT do: tell you what to buy, when to buy, or how
much. Indicators describe what price has done; they do not prescribe action.
The interpretation is yours.

Run with:  streamlit run market_monitor.py
"""

import concurrent.futures as futures
import datetime as dt
import os
from io import StringIO

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf
from plotly.subplots import make_subplots


# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------
@st.cache_data(ttl=900)  # cache 15 min so you don't hammer the API while tweaking
def fetch(ticker: str, period: str) -> pd.DataFrame:
    df = yf.Ticker(ticker).history(period=period, auto_adjust=True)
    if df.empty:
        return df
    df = df.rename(columns=str.title)  # Open/High/Low/Close/Volume
    return df[["Open", "High", "Low", "Close", "Volume"]]


# Baked-in S&P 500 list (Yahoo-style symbols, dots -> dashes) so the app
# still works offline. Refreshed from Wikipedia at runtime when reachable.
_SP500_FALLBACK = [
    'A', 'AAPL', 'ABBV', 'ABNB', 'ABT', 'ACGL', 'ACN', 'ADBE', 'ADI', 'ADM',
    'ADP', 'ADSK', 'AEE', 'AEP', 'AES', 'AFL', 'AIG', 'AIZ', 'AJG', 'AKAM',
    'ALB', 'ALGN', 'ALL', 'ALLE', 'AMAT', 'AMCR', 'AMD', 'AME', 'AMGN', 'AMP',
    'AMT', 'AMZN', 'ANET', 'AON', 'AOS', 'APA', 'APD', 'APH', 'APO', 'APP',
    'APTV', 'ARE', 'ARES', 'ATO', 'AVB', 'AVGO', 'AVY', 'AWK', 'AXON', 'AXP',
    'AZO', 'BA', 'BAC', 'BALL', 'BAX', 'BBY', 'BDX', 'BEN', 'BF-B', 'BG',
    'BIIB', 'BKNG', 'BKR', 'BLDR', 'BLK', 'BMY', 'BNY', 'BR', 'BRK-B', 'BRO',
    'BSX', 'BX', 'BXP', 'C', 'CAG', 'CAH', 'CARR', 'CASY', 'CAT', 'CB',
    'CBOE', 'CBRE', 'CCI', 'CCL', 'CDNS', 'CDW', 'CEG', 'CF', 'CFG', 'CHD',
    'CHRW', 'CHTR', 'CI', 'CIEN', 'CINF', 'CL', 'CLX', 'CMCSA', 'CME', 'CMG',
    'CMI', 'CMS', 'CNC', 'CNP', 'COF', 'COHR', 'COIN', 'COO', 'COP', 'COR',
    'COST', 'CPAY', 'CPB', 'CPRT', 'CPT', 'CRH', 'CRL', 'CRM', 'CRWD', 'CSCO',
    'CSGP', 'CSX', 'CTAS', 'CTSH', 'CTVA', 'CVNA', 'CVS', 'CVX', 'D', 'DAL',
    'DASH', 'DD', 'DDOG', 'DE', 'DECK', 'DELL', 'DG', 'DGX', 'DHI', 'DHR',
    'DIS', 'DLR', 'DLTR', 'DOC', 'DOV', 'DOW', 'DPZ', 'DRI', 'DTE', 'DUK',
    'DVA', 'DVN', 'DXCM', 'EA', 'EBAY', 'ECL', 'ED', 'EFX', 'EG', 'EIX', 'EL',
    'ELV', 'EME', 'EMR', 'EOG', 'EPAM', 'EQIX', 'EQR', 'EQT', 'ERIE', 'ES',
    'ESS', 'ETN', 'ETR', 'EVRG', 'EW', 'EXC', 'EXE', 'EXPD', 'EXPE', 'EXR',
    'F', 'FANG', 'FAST', 'FCX', 'FDS', 'FDX', 'FE', 'FFIV', 'FICO', 'FIS',
    'FISV', 'FITB', 'FIX', 'FOX', 'FOXA', 'FRT', 'FSLR', 'FTNT', 'FTV', 'GD',
    'GDDY', 'GE', 'GEHC', 'GEN', 'GEV', 'GILD', 'GIS', 'GL', 'GLW', 'GM',
    'GNRC', 'GOOG', 'GOOGL', 'GPC', 'GPN', 'GRMN', 'GS', 'GWW', 'HAL', 'HAS',
    'HBAN', 'HCA', 'HD', 'HIG', 'HII', 'HLT', 'HON', 'HOOD', 'HPE', 'HPQ',
    'HRL', 'HSIC', 'HST', 'HSY', 'HUBB', 'HUM', 'HWM', 'IBKR', 'IBM', 'ICE',
    'IDXX', 'IEX', 'IFF', 'INCY', 'INTC', 'INTU', 'INVH', 'IP', 'IQV', 'IR',
    'IRM', 'ISRG', 'IT', 'ITW', 'IVZ', 'J', 'JBHT', 'JBL', 'JCI', 'JKHY',
    'JNJ', 'JPM', 'KDP', 'KEY', 'KEYS', 'KHC', 'KIM', 'KKR', 'KLAC', 'KMB',
    'KMI', 'KO', 'KR', 'KVUE', 'L', 'LDOS', 'LEN', 'LH', 'LHX', 'LII', 'LIN',
    'LITE', 'LLY', 'LMT', 'LNT', 'LOW', 'LRCX', 'LULU', 'LUV', 'LVS', 'LYB',
    'LYV', 'MA', 'MAA', 'MAR', 'MAS', 'MCD', 'MCHP', 'MCK', 'MCO', 'MDLZ',
    'MDT', 'MET', 'META', 'MGM', 'MKC', 'MLM', 'MMM', 'MNST', 'MO', 'MOS',
    'MPC', 'MPWR', 'MRK', 'MRNA', 'MRSH', 'MS', 'MSCI', 'MSFT', 'MSI', 'MTB',
    'MTD', 'MU', 'NCLH', 'NDAQ', 'NDSN', 'NEE', 'NEM', 'NFLX', 'NI', 'NKE',
    'NOC', 'NOW', 'NRG', 'NSC', 'NTAP', 'NTRS', 'NUE', 'NVDA', 'NVR', 'NWS',
    'NWSA', 'NXPI', 'O', 'ODFL', 'OKE', 'OMC', 'ON', 'ORCL', 'ORLY', 'OTIS',
    'OXY', 'PANW', 'PAYX', 'PCAR', 'PCG', 'PEG', 'PEP', 'PFE', 'PFG', 'PG',
    'PGR', 'PH', 'PHM', 'PKG', 'PLD', 'PLTR', 'PM', 'PNC', 'PNR', 'PNW',
    'PODD', 'POOL', 'PPG', 'PPL', 'PRU', 'PSA', 'PSKY', 'PSX', 'PTC', 'PWR',
    'PYPL', 'Q', 'QCOM', 'RCL', 'REG', 'REGN', 'RF', 'RJF', 'RL', 'RMD',
    'ROK', 'ROL', 'ROP', 'ROST', 'RSG', 'RTX', 'RVTY', 'SATS', 'SBAC', 'SBUX',
    'SCHW', 'SHW', 'SJM', 'SLB', 'SMCI', 'SNA', 'SNDK', 'SNPS', 'SO', 'SOLV',
    'SPG', 'SPGI', 'SRE', 'STE', 'STLD', 'STT', 'STX', 'STZ', 'SW', 'SWK',
    'SWKS', 'SYF', 'SYK', 'SYY', 'T', 'TAP', 'TDG', 'TDY', 'TECH', 'TEL',
    'TER', 'TFC', 'TGT', 'TJX', 'TKO', 'TMO', 'TMUS', 'TPL', 'TPR', 'TRGP',
    'TRMB', 'TROW', 'TRV', 'TSCO', 'TSLA', 'TSN', 'TT', 'TTD', 'TTWO', 'TXN',
    'TXT', 'TYL', 'UAL', 'UBER', 'UDR', 'UHS', 'ULTA', 'UNH', 'UNP', 'UPS',
    'URI', 'USB', 'V', 'VEEV', 'VICI', 'VLO', 'VLTO', 'VMC', 'VRSK', 'VRSN',
    'VRT', 'VRTX', 'VST', 'VTR', 'VTRS', 'VZ', 'WAB', 'WAT', 'WBD', 'WDAY',
    'WDC', 'WEC', 'WELL', 'WFC', 'WM', 'WMB', 'WMT', 'WRB', 'WSM', 'WST',
    'WTW', 'WY', 'WYNN', 'XEL', 'XOM', 'XYL', 'XYZ', 'YUM', 'ZBH', 'ZBRA',
    'ZTS',
]


@st.cache_data(ttl=86400)  # constituents change rarely; refresh daily
def sp500_tickers() -> list[str]:
    """Live S&P 500 list from Wikipedia, falling back to the baked-in copy."""
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    try:
        html = requests.get(url, headers={"User-Agent": "Mozilla/5.0"},
                            timeout=15).text
        df = pd.read_html(StringIO(html))[0]
        syms = (df["Symbol"].astype(str).str.upper()
                .str.replace(".", "-", regex=False).tolist())
        return sorted(s for s in syms if s)
    except Exception:
        return list(_SP500_FALLBACK)


# --------------------------------------------------------------------------
# Indicators — computed by hand so the math is visible, not hidden in a lib
# --------------------------------------------------------------------------
def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    c = df["Close"]

    # Simple moving averages
    df["SMA50"] = c.rolling(50).mean()
    df["SMA200"] = c.rolling(200).mean()

    # RSI (Wilder's smoothing), 14-period
    delta = c.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    rs = avg_gain / avg_loss
    df["RSI"] = 100 - 100 / (1 + rs)

    # MACD: 12/26 EMA difference, 9-period signal line
    ema12 = c.ewm(span=12, adjust=False).mean()
    ema26 = c.ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_hist"] = df["MACD"] - df["MACD_signal"]

    # Bollinger Bands: 20-period SMA +/- 2 standard deviations
    mid = c.rolling(20).mean()
    std = c.rolling(20).std()
    df["BB_mid"] = mid
    df["BB_up"] = mid + 2 * std
    df["BB_low"] = mid - 2 * std

    # Ripster EMA Clouds — pairs of EMAs whose shaded gap forms a "cloud".
    # A cloud is bullish (green) when its faster EMA is above its slower EMA.
    for span in (5, 12, 34, 50, 72, 89):
        df[f"EMA{span}"] = c.ewm(span=span, adjust=False).mean()

    return df


# Ripster EMA cloud pairs: (fast, slow, short-label). Short / intermediate /
# longer-term, mirroring the clouds Ripster47 popularised.
RIPSTER_CLOUDS = [(5, 12, "5/12"), (34, 50, "34/50"), (72, 89, "72/89")]


def crossed(series_a: pd.Series, series_b: pd.Series) -> str | None:
    """Return 'up' / 'down' if a crossed b within the last bar, else None."""
    a, b = series_a.dropna(), series_b.dropna()
    idx = a.index.intersection(b.index)
    if len(idx) < 2:
        return None
    a, b = a.loc[idx], b.loc[idx]
    if a.iloc[-2] <= b.iloc[-2] and a.iloc[-1] > b.iloc[-1]:
        return "up"
    if a.iloc[-2] >= b.iloc[-2] and a.iloc[-1] < b.iloc[-1]:
        return "down"
    return None


# --------------------------------------------------------------------------
# Observations — neutral flags, each paired with what to go learn about.
# Intentionally NO recommendations and NO position sizes.
# --------------------------------------------------------------------------
def observations(df: pd.DataFrame) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    last = df.iloc[-1]

    rsi = last["RSI"]
    if pd.notna(rsi):
        if rsi >= 70:
            out.append(("RSI is in the 'overbought' zone (>=70).",
                        "Read up on why stretched momentum often precedes "
                        "consolidation — and the many times it doesn't."))
        elif rsi <= 30:
            out.append(("RSI is in the 'oversold' zone (<=30).",
                        "A classic mean-reversion signal — and a classic "
                        "value trap. Investigate which this is."))

    if pd.notna(last["SMA200"]):
        rel = "above" if last["Close"] > last["SMA200"] else "below"
        out.append((f"Price is {rel} its 200-day average.",
                    "The 200-day is a common long-term trend reference. "
                    "Ask what changed if it just flipped."))

    ma_cross = crossed(df["SMA50"], df["SMA200"])
    if ma_cross == "up":
        out.append(("50-day just crossed above the 200-day ('golden cross').",
                    "Look at how often this signal has held vs. whipsawed "
                    "for this specific name."))
    elif ma_cross == "down":
        out.append(("50-day just crossed below the 200-day ('death cross').",
                    "Same caution — study the false-signal rate before "
                    "reading anything into it."))

    macd_cross = crossed(df["MACD"], df["MACD_signal"])
    if macd_cross == "up":
        out.append(("MACD crossed above its signal line.",
                    "Momentum indicator turning positive. Compare against "
                    "volume and the broader trend."))
    elif macd_cross == "down":
        out.append(("MACD crossed below its signal line.",
                    "Momentum turning negative. Context matters more than "
                    "the cross itself."))

    if pd.notna(last["BB_up"]):
        if last["Close"] >= last["BB_up"]:
            out.append(("Price is touching the upper Bollinger Band.",
                        "Bands measure volatility, not direction — a tag "
                        "isn't a signal on its own."))
        elif last["Close"] <= last["BB_low"]:
            out.append(("Price is touching the lower Bollinger Band.",
                        "Same idea — investigate why volatility expanded."))

    if "EMA5" in df.columns and pd.notna(last["EMA89"]):
        rip, detail = lens_ripster(df)
        if rip > 0:
            out.append(("Ripster EMA clouds are aligned bullish.",
                        f"{detail}. Ripster traders watch for price to hold "
                        "above the clouds as support — study where it last failed."))
        elif rip < 0:
            out.append(("Ripster EMA clouds are aligned bearish.",
                        f"{detail}. Clouds above price often act as resistance — "
                        "see whether prior bounces stalled there."))

    if not out:
        out.append(("Nothing notable on the indicators right now.",
                    "Quiet tape. A fine time to study the business itself "
                    "rather than the chart."))
    return out


# --------------------------------------------------------------------------
# Signal aggregation — a MECHANICAL summary, not a forecast.
# Each indicator casts a -1 / 0 / +1 vote; news adds a sentiment tilt.
# This is a heuristic that compresses the chart into one word. It does not
# know anything the indicators above don't. Treat it as a conversation
# starter, not an instruction.
# --------------------------------------------------------------------------
def technical_signals(df: pd.DataFrame) -> list[tuple[str, int, str]]:
    """Return [(name, vote, rationale)] where vote is -1 / 0 / +1."""
    last = df.iloc[-1]
    sig: list[tuple[str, int, str]] = []

    rsi = last["RSI"]
    if pd.notna(rsi):
        if rsi <= 30:
            sig.append(("RSI (14)", +1, f"oversold at {rsi:.0f} (mean-reversion bias up)"))
        elif rsi >= 70:
            sig.append(("RSI (14)", -1, f"overbought at {rsi:.0f} (mean-reversion bias down)"))
        else:
            sig.append(("RSI (14)", 0, f"neutral at {rsi:.0f}"))

    if pd.notna(last["SMA200"]):
        if last["Close"] > last["SMA200"]:
            sig.append(("Price vs 200-day", +1, "trading above long-term average"))
        else:
            sig.append(("Price vs 200-day", -1, "trading below long-term average"))

    if pd.notna(last["SMA50"]) and pd.notna(last["SMA200"]):
        if last["SMA50"] > last["SMA200"]:
            sig.append(("50 vs 200-day", +1, "50-day above 200-day (uptrend regime)"))
        else:
            sig.append(("50 vs 200-day", -1, "50-day below 200-day (downtrend regime)"))

    if pd.notna(last["MACD"]) and pd.notna(last["MACD_signal"]):
        if last["MACD"] > last["MACD_signal"]:
            sig.append(("MACD", +1, "above signal line (positive momentum)"))
        else:
            sig.append(("MACD", -1, "below signal line (negative momentum)"))

    if pd.notna(last["BB_up"]):
        if last["Close"] <= last["BB_low"]:
            sig.append(("Bollinger", +1, "at lower band (stretched down)"))
        elif last["Close"] >= last["BB_up"]:
            sig.append(("Bollinger", -1, "at upper band (stretched up)"))
        else:
            sig.append(("Bollinger", 0, "inside the bands"))

    return sig


# A tiny lexicon. Crude on purpose — no API key, no black box. It counts
# loaded words in headlines; it does not understand sarcasm, context, or
# whether the news is already priced in.
_POS = {
    "beat", "beats", "surge", "surges", "jump", "jumps", "rally", "rallies",
    "soar", "soars", "gain", "gains", "upgrade", "upgrades", "record", "high",
    "growth", "profit", "profits", "strong", "outperform", "bullish", "rise",
    "rises", "boost", "wins", "win", "approval", "approved", "raises", "raise",
    "top", "tops", "expands", "expansion", "buyback", "dividend", "optimistic",
}
_NEG = {
    "miss", "misses", "plunge", "plunges", "fall", "falls", "drop", "drops",
    "slump", "slumps", "downgrade", "downgrades", "loss", "losses", "weak",
    "cut", "cuts", "lawsuit", "probe", "investigation", "recall", "warns",
    "warning", "bearish", "decline", "declines", "slip", "slips", "crash",
    "fraud", "layoff", "layoffs", "fears", "concern", "concerns", "slowdown",
    "tumble", "tumbles", "sinks", "sink", "halts", "halt", "delay", "delays",
}


@st.cache_data(ttl=1800)  # news moves slower than price; cache 30 min
def news_feed(ticker: str) -> list[dict]:
    """Fetch recent headlines via yfinance, flattened to simple dicts."""
    try:
        raw = yf.Ticker(ticker).news or []
    except Exception:
        return []
    items = []
    for r in raw:
        c = r.get("content", r)  # newer yfinance nests under 'content'
        title = (c.get("title") or "").strip()
        if not title:
            continue
        url = ((c.get("clickThroughUrl") or c.get("canonicalUrl") or {}) or {}).get("url", "")
        publisher = ((c.get("provider") or {}) or {}).get("displayName", "")
        items.append({
            "title": title,
            "summary": (c.get("summary") or "").strip(),
            "url": url,
            "publisher": publisher,
            "time": c.get("pubDate") or c.get("displayTime") or "",
        })
    return items


def score_headline(text: str) -> int:
    """Net sentiment of a single headline: positive words minus negative."""
    words = {w.strip(".,:;!?'\"()").lower() for w in text.split()}
    return len(words & _POS) - len(words & _NEG)


def news_sentiment(items: list[dict]) -> tuple[float, list[tuple[dict, int]]]:
    """Return (avg_sentiment, [(item, score)]). avg ~ [-1, 1]-ish range."""
    scored = [(it, score_headline(f"{it['title']} {it['summary']}")) for it in items]
    if not scored:
        return 0.0, scored
    nonzero = [s for _, s in scored if s != 0]
    avg = sum(nonzero) / len(nonzero) if nonzero else 0.0
    return avg, scored


# --------------------------------------------------------------------------
# Fundamentals, analysts, environment — the non-chart lenses.
# Every fetch is wrapped: missing data degrades the lens to "no opinion"
# rather than crashing the app.
# --------------------------------------------------------------------------
# SPDR sector ETFs, keyed by yfinance's sector names, for relative strength.
SECTOR_ETF = {
    "Technology": "XLK", "Financial Services": "XLF", "Healthcare": "XLV",
    "Consumer Cyclical": "XLY", "Consumer Defensive": "XLP", "Energy": "XLE",
    "Industrials": "XLI", "Basic Materials": "XLB", "Real Estate": "XLRE",
    "Utilities": "XLU", "Communication Services": "XLC",
}


@st.cache_data(ttl=3600)
def fundamentals(ticker: str) -> dict:
    """Valuation / quality / growth snapshot from yfinance .info."""
    try:
        info = yf.Ticker(ticker).info or {}
    except Exception:
        return {}
    fields = [
        "trailingPE", "forwardPE", "pegRatio", "priceToSalesTrailing12Months",
        "priceToBook", "enterpriseToEbitda", "profitMargins", "revenueGrowth",
        "earningsGrowth", "returnOnEquity", "debtToEquity", "dividendYield",
        "beta", "marketCap", "freeCashflow", "sector", "industry",
        "longName", "currentPrice",
    ]
    return {k: info.get(k) for k in fields}


@st.cache_data(ttl=3600)
def analyst_view(ticker: str) -> dict:
    """Analyst price target + consensus rating."""
    try:
        info = yf.Ticker(ticker).info or {}
    except Exception:
        return {}
    price = info.get("currentPrice")
    target = info.get("targetMeanPrice")
    upside = (target / price - 1) if (price and target) else None
    return {
        "price": price,
        "target_mean": target,
        "target_high": info.get("targetHighPrice"),
        "target_low": info.get("targetLowPrice"),
        "upside": upside,
        "rec_mean": info.get("recommendationMean"),   # 1 strong buy .. 5 strong sell
        "rec_key": info.get("recommendationKey"),
        "n_analysts": info.get("numberOfAnalystOpinions"),
    }


@st.cache_data(ttl=3600)
def earnings_proximity(ticker: str) -> dict:
    """Days until next earnings date (event risk)."""
    try:
        cal = yf.Ticker(ticker).calendar or {}
        dates = cal.get("Earnings Date") or []
        if isinstance(dates, (list, tuple)) and dates:
            nxt = min(dates)
        else:
            nxt = dates or None
        if nxt is None:
            return {"date": None, "days": None}
        days = (nxt - dt.date.today()).days
        return {"date": nxt, "days": days}
    except Exception:
        return {"date": None, "days": None}


@st.cache_data(ttl=1800)
def market_environment() -> dict:
    """Broad-market regime: SPY trend, VIX level, 10-yr yield."""
    env: dict = {}
    try:
        spy = fetch("SPY", "1y")
        if not spy.empty:
            sma200 = spy["Close"].rolling(200).mean().iloc[-1]
            last = spy["Close"].iloc[-1]
            env["spy_last"] = last
            env["spy_sma200"] = sma200
            env["spy_above_200"] = bool(pd.notna(sma200) and last > sma200)
            env["spy_ret_3m"] = _pct_return(spy["Close"], 63)
    except Exception:
        pass
    try:
        vix = fetch("^VIX", "6mo")
        env["vix"] = float(vix["Close"].iloc[-1]) if not vix.empty else None
    except Exception:
        env["vix"] = None
    try:
        tnx = fetch("^TNX", "6mo")
        # ^TNX is quoted in tenths of a percent on some feeds; here it's the yield.
        env["tnx"] = float(tnx["Close"].iloc[-1]) if not tnx.empty else None
    except Exception:
        env["tnx"] = None
    return env


def _pct_return(close: pd.Series, lookback: int) -> float | None:
    s = close.dropna()
    if len(s) <= lookback:
        return None
    return float(s.iloc[-1] / s.iloc[-1 - lookback] - 1)


@st.cache_data(ttl=1800)
def relative_strength(ticker: str, sector: str | None) -> dict:
    """3-month return of the stock vs SPY and its sector ETF."""
    out: dict = {"stock": None, "spy": None, "sector": None, "etf": None}
    try:
        out["stock"] = _pct_return(fetch(ticker, "1y")["Close"], 63)
        out["spy"] = _pct_return(fetch("SPY", "1y")["Close"], 63)
        etf = SECTOR_ETF.get(sector or "")
        if etf:
            out["etf"] = etf
            out["sector"] = _pct_return(fetch(etf, "1y")["Close"], 63)
    except Exception:
        pass
    return out


# --------------------------------------------------------------------------
# Conviction engine — independent lenses vote; conviction = how much they agree
# --------------------------------------------------------------------------
def _avg_vote(parts: list[int]) -> int:
    """Collapse sub-scores into a single -1/0/+1 vote."""
    parts = [p for p in parts if p is not None]
    if not parts:
        return 0
    m = sum(parts) / len(parts)
    return 1 if m >= 0.34 else -1 if m <= -0.34 else 0


def lens_trend(df: pd.DataFrame) -> tuple[int, str]:
    last = df.iloc[-1]
    parts, notes = [], []
    if pd.notna(last["SMA200"]):
        up = last["Close"] > last["SMA200"]
        parts.append(1 if up else -1)
        notes.append(f"price {'above' if up else 'below'} 200-day")
    if pd.notna(last["SMA50"]) and pd.notna(last["SMA200"]):
        up = last["SMA50"] > last["SMA200"]
        parts.append(1 if up else -1)
        notes.append(f"50d {'>' if up else '<'} 200d")
    return _avg_vote(parts), ", ".join(notes) or "insufficient history"


def lens_momentum(df: pd.DataFrame) -> tuple[int, str]:
    last = df.iloc[-1]
    parts, notes = [], []
    if pd.notna(last["MACD"]) and pd.notna(last["MACD_signal"]):
        up = last["MACD"] > last["MACD_signal"]
        parts.append(1 if up else -1)
        notes.append(f"MACD {'>' if up else '<'} signal")
    rsi = last["RSI"]
    if pd.notna(rsi):
        if rsi >= 70:
            parts.append(0); notes.append(f"RSI {rsi:.0f} overbought")
        elif rsi <= 30:
            parts.append(0); notes.append(f"RSI {rsi:.0f} oversold")
        elif rsi >= 50:
            parts.append(1); notes.append(f"RSI {rsi:.0f}")
        else:
            parts.append(-1); notes.append(f"RSI {rsi:.0f}")
    return _avg_vote(parts), ", ".join(notes) or "n/a"


def lens_ripster(df: pd.DataFrame) -> tuple[int, str]:
    """Ripster EMA Clouds. Bullish when price rides above green, stacked clouds.

    Five checks: each cloud's colour (fast EMA above slow = green), price vs the
    fast cloud, and whether the fast cloud is stacked above the intermediate
    cloud. Net of bullish minus bearish checks drives the vote.
    """
    last = df.iloc[-1]
    cols = ["EMA5", "EMA12", "EMA34", "EMA50", "EMA72", "EMA89"]
    if any(c not in df.columns or pd.isna(last[c]) for c in cols):
        return 0, "insufficient history"

    bull = bear = 0
    # Cloud colours (faster EMA above slower = bullish/green).
    colours = []
    for fast, slow, label in RIPSTER_CLOUDS:
        green = last[f"EMA{fast}"] > last[f"EMA{slow}"]
        bull += green
        bear += not green
        colours.append(f"{label}{'🟢' if green else '🔴'}")

    # Price relative to the fast (5/12) cloud.
    fast_hi = max(last["EMA5"], last["EMA12"])
    fast_lo = min(last["EMA5"], last["EMA12"])
    price = last["Close"]
    if price > fast_hi:
        bull += 1; price_note = "price above fast cloud"
    elif price < fast_lo:
        bear += 1; price_note = "price below fast cloud"
    else:
        price_note = "price inside fast cloud"

    # Cloud stacking: fast (5/12) fully above intermediate (34/50) = bullish.
    mid_hi = max(last["EMA34"], last["EMA50"])
    mid_lo = min(last["EMA34"], last["EMA50"])
    if fast_lo > mid_hi:
        bull += 1; stack_note = "stacked bullish"
    elif fast_hi < mid_lo:
        bear += 1; stack_note = "stacked bearish"
    else:
        stack_note = "clouds overlapping"

    vote = 1 if bull - bear >= 2 else -1 if bull - bear <= -2 else 0
    detail = f"{bull}/5 bullish · {' '.join(colours)} · {price_note} · {stack_note}"
    return vote, detail


def lens_valuation(f: dict) -> tuple[int, str]:
    parts, notes = [], []
    pe = f.get("forwardPE") or f.get("trailingPE")
    if pe and pe > 0:
        parts.append(1 if pe < 15 else -1 if pe > 30 else 0)
        notes.append(f"P/E {pe:.0f}")
    peg = f.get("pegRatio")
    if peg and peg > 0:
        parts.append(1 if peg < 1 else -1 if peg > 2 else 0)
        notes.append(f"PEG {peg:.1f}")
    ps = f.get("priceToSalesTrailing12Months")
    if ps and ps > 0:
        parts.append(1 if ps < 2 else -1 if ps > 10 else 0)
        notes.append(f"P/S {ps:.1f}")
    return _avg_vote(parts), ", ".join(notes) or "no valuation data"


def lens_quality(f: dict) -> tuple[int, str]:
    parts, notes = [], []
    rg = f.get("revenueGrowth")
    if rg is not None:
        parts.append(1 if rg > 0.10 else -1 if rg < 0 else 0)
        notes.append(f"rev g/ {rg*100:+.0f}%")
    eg = f.get("earningsGrowth")
    if eg is not None:
        parts.append(1 if eg > 0.10 else -1 if eg < 0 else 0)
        notes.append(f"eps g/ {eg*100:+.0f}%")
    pm = f.get("profitMargins")
    if pm is not None:
        parts.append(1 if pm > 0.15 else -1 if pm < 0.05 else 0)
        notes.append(f"margin {pm*100:.0f}%")
    roe = f.get("returnOnEquity")
    if roe is not None:
        parts.append(1 if roe > 0.15 else -1 if roe < 0 else 0)
        notes.append(f"ROE {roe*100:.0f}%")
    return _avg_vote(parts), ", ".join(notes) or "no fundamentals"


def lens_analysts(a: dict) -> tuple[int, str]:
    parts, notes = [], []
    up = a.get("upside")
    if up is not None:
        parts.append(1 if up > 0.15 else -1 if up < -0.05 else 0)
        notes.append(f"{up*100:+.0f}% to target")
    rec = a.get("rec_mean")
    if rec:
        parts.append(1 if rec < 2.5 else -1 if rec > 3.5 else 0)
        label = a.get("rec_key") or f"{rec:.1f}"
        notes.append(f"consensus {label}")
    n = a.get("n_analysts")
    if n:
        notes.append(f"{n} analysts")
    return _avg_vote(parts), ", ".join(str(x) for x in notes) or "no coverage"


def lens_environment(env: dict) -> tuple[int, str]:
    parts, notes = [], []
    if "spy_above_200" in env:
        up = env["spy_above_200"]
        parts.append(1 if up else -1)
        notes.append(f"SPY {'above' if up else 'below'} 200-day")
    vix = env.get("vix")
    if vix is not None:
        parts.append(1 if vix < 20 else -1 if vix > 30 else 0)
        notes.append(f"VIX {vix:.0f}")
    return _avg_vote(parts), ", ".join(notes) or "n/a"


def lens_relative(rel: dict) -> tuple[int, str]:
    parts, notes = [], []
    stock, spy, sec = rel.get("stock"), rel.get("spy"), rel.get("sector")
    if stock is not None and spy is not None:
        parts.append(1 if stock > spy else -1)
        notes.append(f"{(stock-spy)*100:+.0f}% vs SPY (3m)")
    if stock is not None and sec is not None:
        parts.append(1 if stock > sec else -1)
        notes.append(f"{(stock-sec)*100:+.0f}% vs {rel.get('etf')}")
    return _avg_vote(parts), ", ".join(notes) or "n/a"


def lens_sentiment(news_avg: float, n: int) -> tuple[int, str]:
    if n == 0:
        return 0, "no headlines"
    vote = 1 if news_avg > 0.3 else -1 if news_avg < -0.3 else 0
    return vote, f"avg {news_avg:+.1f} over {n} headlines"


def conviction_engine(df, f, a, env, rel, news_avg, n_news, days_to_earnings):
    """Run every lens, then derive direction + a conviction level from agreement."""
    lenses = [
        ("Trend", 1.0, *lens_trend(df)),
        ("Momentum", 1.0, *lens_momentum(df)),
        ("Ripster EMA clouds", 1.0, *lens_ripster(df)),
        ("Valuation", 1.0, *lens_valuation(f)),
        ("Quality / growth", 1.0, *lens_quality(f)),
        ("Analyst targets", 1.0, *lens_analysts(a)),
        ("Market regime", 1.0, *lens_environment(env)),
        ("Relative strength", 1.0, *lens_relative(rel)),
        ("News sentiment", 0.5, *lens_sentiment(news_avg, n_news)),
    ]
    # lenses: (name, weight, vote, detail)
    weighted_sum = sum(w * v for _, w, v, _ in lenses)
    weight_total = sum(w for _, w, _, _ in lenses) or 1
    direction = weighted_sum / weight_total  # -1 .. +1

    active = [(w, v) for _, w, v, _ in lenses if v != 0]
    net_sign = 1 if direction > 0 else -1 if direction < 0 else 0
    agree_w = sum(w for w, v in active if v == net_sign)
    disagree_w = sum(w for w, v in active if v == -net_sign)
    agreement = agree_w / (agree_w + disagree_w) if (agree_w + disagree_w) else 0.0
    participation = len(active)

    # Direction label
    if direction >= 0.30:
        label, color = "BUY", "#22c55e"
    elif direction <= -0.30:
        label, color = "SELL", "#ef4444"
    else:
        label, color = "NEUTRAL", "#eab308"

    # Conviction = agreement × participation, then capped by event risk
    if net_sign == 0 or participation < 3:
        conviction = "LOW"
    elif agreement >= 0.78 and participation >= 5:
        conviction = "HIGH"
    elif agreement >= 0.62:
        conviction = "MEDIUM"
    else:
        conviction = "LOW"

    event_warning = None
    if days_to_earnings is not None and 0 <= days_to_earnings <= 7:
        event_warning = (f"Earnings in {days_to_earnings} day(s) — a binary event "
                         "the chart can't predict. Conviction capped.")
        if conviction == "HIGH":
            conviction = "MEDIUM"
        elif conviction == "MEDIUM":
            conviction = "LOW"

    conv_color = {"HIGH": "#22c55e", "MEDIUM": "#eab308", "LOW": "#9ca3af"}[conviction]

    return {
        "label": label, "color": color,
        "direction": direction, "agreement": agreement,
        "participation": participation, "conviction": conviction,
        "conv_color": conv_color, "lenses": lenses,
        "event_warning": event_warning,
    }


# --------------------------------------------------------------------------
# Screener — scan the whole index, bucket by direction × conviction.
# Hybrid: a cheap technical pre-screen on all names (batch price download),
# then the full conviction engine on a bounded shortlist (threaded). News is
# omitted in bulk mode for speed, so screener scores use up to 7 lenses.
# --------------------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def batch_close(tickers: tuple, period: str) -> dict:
    """Batch-download Close series for many tickers, chunked to stay polite."""
    out: dict = {}
    step = 120
    for i in range(0, len(tickers), step):
        part = list(tickers[i:i + step])
        try:
            data = yf.download(part, period=period, auto_adjust=True,
                               progress=False, threads=True)
            if "Close" in data:
                close = data["Close"]
            else:
                close = data
            if isinstance(close, pd.Series):  # single-ticker shape
                s = close.dropna()
                if len(s):
                    out[part[0]] = s
            else:
                for col in close.columns:
                    s = close[col].dropna()
                    if len(s):
                        out[col] = s
        except Exception:
            continue
    return out


def _tech_score(close: pd.Series):
    """Stage-1 technical lean from price alone: (score in -2..2, 3-mo return)."""
    s = close.dropna()
    if len(s) < 200:
        return None
    df = add_indicators(pd.DataFrame({"Close": s}))
    tv, _ = lens_trend(df)
    mv, _ = lens_momentum(df)
    return tv + mv, (_pct_return(s, 63) or 0.0)


def _screen_one(ticker, close, spy_close, sector_closes, env):
    """Full conviction for one name (no per-name news fetch, for speed)."""
    try:
        df = add_indicators(pd.DataFrame({"Close": close.dropna()}))
        info = yf.Ticker(ticker).info or {}
        f = {k: info.get(k) for k in (
            "trailingPE", "forwardPE", "pegRatio",
            "priceToSalesTrailing12Months", "profitMargins", "revenueGrowth",
            "earningsGrowth", "returnOnEquity", "marketCap", "sector")}
        price, target = info.get("currentPrice"), info.get("targetMeanPrice")
        a = {
            "price": price, "target_mean": target,
            "upside": (target / price - 1) if (price and target) else None,
            "rec_mean": info.get("recommendationMean"),
            "rec_key": info.get("recommendationKey"),
            "n_analysts": info.get("numberOfAnalystOpinions"),
        }
        try:
            cal = yf.Ticker(ticker).calendar or {}
            ds = cal.get("Earnings Date") or []
            nxt = min(ds) if isinstance(ds, (list, tuple)) and ds else (ds or None)
            days = (nxt - dt.date.today()).days if nxt else None
        except Exception:
            days = None
        etf = SECTOR_ETF.get(f.get("sector") or "")
        rel = {
            "stock": _pct_return(close, 63),
            "spy": _pct_return(spy_close, 63) if spy_close is not None else None,
            "sector": _pct_return(sector_closes[etf], 63) if etf in sector_closes else None,
            "etf": etf,
        }
        v = conviction_engine(df, f, a, env, rel, 0.0, 0, days)
        return {
            "ticker": ticker, "label": v["label"], "conviction": v["conviction"],
            "direction": round(v["direction"], 2), "agreement": v["agreement"],
            "participation": v["participation"], "days_to_earnings": days,
            "upside": a["upside"], "pe": f.get("forwardPE") or f.get("trailingPE"),
        }
    except Exception:
        return None


def screen_all(universe, period, n_bull, n_bear, progress=None):
    """Two-stage scan. progress(frac, text) is an optional UI callback."""
    def report(frac, text):
        if progress:
            progress(min(frac, 1.0), text)

    report(0.05, "Loading market environment & benchmarks…")
    env = market_environment()
    spy = fetch("SPY", period)
    spy_close = spy["Close"] if not spy.empty else None
    sector_closes = {}
    for etf in set(SECTOR_ETF.values()):
        h = fetch(etf, period)
        if not h.empty:
            sector_closes[etf] = h["Close"]

    report(0.15, f"Downloading prices for {len(universe)} tickers…")
    closes = batch_close(tuple(universe), period)

    report(0.45, "Technical pre-screen on all names…")
    tech = {}
    for t, s in closes.items():
        r = _tech_score(s)
        if r is not None:
            tech[t] = r

    bulls = sorted((t for t in tech if tech[t][0] > 0),
                   key=lambda t: (tech[t][0], tech[t][1]), reverse=True)[:n_bull]
    bears = sorted((t for t in tech if tech[t][0] < 0),
                   key=lambda t: (tech[t][0], tech[t][1]))[:n_bear]
    shortlist = bulls + bears

    report(0.5, f"Full conviction scan on {len(shortlist)} candidates…")
    results, done = [], 0
    with futures.ThreadPoolExecutor(max_workers=10) as ex:
        futs = {ex.submit(_screen_one, t, closes[t], spy_close, sector_closes, env): t
                for t in shortlist}
        for fut in futures.as_completed(futs):
            r = fut.result()
            done += 1
            if r:
                results.append(r)
            report(0.5 + 0.5 * done / max(len(shortlist), 1),
                   f"Scored {done}/{len(shortlist)}…")

    buckets = {"Strong Buy": [], "Buy": [], "Watch / Mixed": [],
               "Sell": [], "Strong Sell": []}
    for r in results:
        L, C = r["label"], r["conviction"]
        if L == "BUY" and C == "HIGH":
            buckets["Strong Buy"].append(r)
        elif L == "BUY" and C == "MEDIUM":
            buckets["Buy"].append(r)
        elif L == "SELL" and C == "HIGH":
            buckets["Strong Sell"].append(r)
        elif L == "SELL" and C == "MEDIUM":
            buckets["Sell"].append(r)
        else:
            buckets["Watch / Mixed"].append(r)
    for name in ("Strong Buy", "Buy"):
        buckets[name].sort(key=lambda r: (r["agreement"], r["direction"]), reverse=True)
    for name in ("Sell", "Strong Sell"):
        buckets[name].sort(key=lambda r: (r["agreement"], -r["direction"]), reverse=True)

    report(1.0, "Done.")
    return {"buckets": buckets, "scored": len(results),
            "shortlist": len(shortlist), "scanned": len(closes)}


# --------------------------------------------------------------------------
# Neon Postgres — persist screener scan history.
# The connection string is read from the NEON_DATABASE_URL env var, or from
# .streamlit/secrets.toml ([neon] dsn = "..."). Never hard-coded / committed.
# --------------------------------------------------------------------------
_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS scan_runs (
    id BIGSERIAL PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    period TEXT, n_bull INT, n_bear INT,
    scanned INT, scored INT
);
CREATE TABLE IF NOT EXISTS scan_results (
    run_id BIGINT REFERENCES scan_runs(id) ON DELETE CASCADE,
    bucket TEXT, ticker TEXT, label TEXT, conviction TEXT,
    direction REAL, agreement REAL, participation INT,
    upside REAL, pe REAL, days_to_earnings INT
);
"""


def neon_dsn() -> str | None:
    """Connection string from env var first, then Streamlit secrets."""
    dsn = os.environ.get("NEON_DATABASE_URL")
    if not dsn:
        try:
            dsn = st.secrets["neon"]["dsn"]
        except Exception:
            dsn = None
    return dsn


def _neon_connect():
    import psycopg2
    return psycopg2.connect(neon_dsn())


@st.cache_resource(show_spinner=False)
def neon_status() -> tuple[bool, str]:
    """Connect once and ensure the schema exists. Returns (ok, message)."""
    if not neon_dsn():
        return False, "No connection string configured."
    try:
        conn = _neon_connect()
        with conn, conn.cursor() as cur:
            cur.execute(_SCHEMA_SQL)
        conn.close()
        return True, "Connected."
    except Exception as e:  # noqa: BLE001 — surface any driver/network error
        return False, f"{type(e).__name__}: {e}"


def save_scan_to_neon(res: dict, period, n_bull, n_bear) -> int:
    """Persist one scan (run row + per-ticker result rows). Returns run id."""
    conn = _neon_connect()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(_SCHEMA_SQL)
            cur.execute(
                "INSERT INTO scan_runs (period, n_bull, n_bear, scanned, scored) "
                "VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (period, n_bull, n_bear, res["scanned"], res["scored"]),
            )
            run_id = cur.fetchone()[0]
            rows = [
                (run_id, bucket, r["ticker"], r["label"], r["conviction"],
                 r["direction"], r["agreement"], r["participation"],
                 r.get("upside"), r.get("pe"), r.get("days_to_earnings"))
                for bucket, items in res["buckets"].items() for r in items
            ]
            if rows:
                cur.executemany(
                    "INSERT INTO scan_results (run_id, bucket, ticker, label, "
                    "conviction, direction, agreement, participation, upside, pe, "
                    "days_to_earnings) VALUES "
                    "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", rows)
        return run_id
    finally:
        conn.close()


def load_scan_runs(limit: int = 25) -> pd.DataFrame:
    conn = _neon_connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, ts, period, scanned, scored, n_bull, n_bear "
                "FROM scan_runs ORDER BY ts DESC LIMIT %s", (limit,))
            cols = [d[0] for d in cur.description]
            return pd.DataFrame(cur.fetchall(), columns=cols)
    finally:
        conn.close()


def load_run_results(run_id: int) -> pd.DataFrame:
    conn = _neon_connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT bucket, ticker, label, conviction, direction, agreement, "
                "participation, upside, pe, days_to_earnings "
                "FROM scan_results WHERE run_id = %s "
                "ORDER BY direction DESC", (run_id,))
            cols = [d[0] for d in cur.description]
            return pd.DataFrame(cur.fetchall(), columns=cols)
    finally:
        conn.close()


# --------------------------------------------------------------------------
# Charts
# --------------------------------------------------------------------------
def price_chart(df: pd.DataFrame, ticker: str, dark: bool = False,
                show_clouds: bool = True) -> go.Figure:
    template = "plotly_dark" if dark else "plotly_white"
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03,
        row_heights=[0.6, 0.2, 0.2],
        subplot_titles=(f"{ticker} — price, MAs, Bollinger & Ripster EMA clouds",
                        "RSI (14)", "MACD (12/26/9)"),
    )

    # Ripster EMA clouds first, so they sit behind the candles. Each cloud is
    # tinted by its CURRENT colour (faster EMA above slower = green).
    if show_clouds:
        for fast, slow, label in RIPSTER_CLOUDS:
            green = df[f"EMA{fast}"].iloc[-1] > df[f"EMA{slow}"].iloc[-1]
            fill = "rgba(38,166,154,0.13)" if green else "rgba(239,83,80,0.13)"
            edge = "rgba(38,166,154,0.55)" if green else "rgba(239,83,80,0.55)"
            fig.add_trace(go.Scatter(
                x=df.index, y=df[f"EMA{slow}"], line=dict(width=0),
                showlegend=False, hoverinfo="skip"), row=1, col=1)
            fig.add_trace(go.Scatter(
                x=df.index, y=df[f"EMA{fast}"], fill="tonexty", fillcolor=fill,
                line=dict(width=1, color=edge),
                name=f"Ripster {label}"), row=1, col=1)

    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"], name="Price"), row=1, col=1)
    # Trend MAs in distinct solid hues; Bollinger bands as subtle dotted gray
    # so they read as context rather than competing with the moving averages.
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA50"], name="SMA 50",
                             line=dict(width=1.7, color="#3B82F6")), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA200"], name="SMA 200",
                             line=dict(width=1.7, color="#F97316")), row=1, col=1)
    for col, nm in [("BB_up", "Boll upper"), ("BB_low", "Boll lower")]:
        fig.add_trace(go.Scatter(x=df.index, y=df[col], name=nm,
                                 line=dict(width=1, color="#94A3B8", dash="dot")),
                      row=1, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], name="RSI",
                             line=dict(width=1.6, color="#A855F7")), row=2, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="#e8684a", row=2, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="#5ad8a6", row=2, col=1)

    # MACD histogram coloured by sign; MACD line cyan, Signal line amber.
    hist_colors = ["rgba(34,197,94,0.55)" if v >= 0 else "rgba(239,83,80,0.55)"
                   for v in df["MACD_hist"].fillna(0)]
    fig.add_trace(go.Bar(x=df.index, y=df["MACD_hist"], name="Histogram",
                         marker_color=hist_colors), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], name="MACD",
                             line=dict(width=1.8, color="#06B6D4")), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["MACD_signal"], name="Signal",
                             line=dict(width=1.8, color="#F59E0B")), row=3, col=1)

    fig.update_layout(height=720, xaxis_rangeslider_visible=False,
                      showlegend=True, margin=dict(t=40, b=20),
                      template=template)
    if dark:
        fig.update_layout(paper_bgcolor="#0e1117", plot_bgcolor="#0e1117")
        # Dim the default plotly_dark gridlines so they don't overpower the data.
        fig.update_xaxes(gridcolor="#1b212c", zerolinecolor="#2a2f3a")
        fig.update_yaxes(gridcolor="#1b212c", zerolinecolor="#2a2f3a")
    return fig


# --------------------------------------------------------------------------
# Screener view
# --------------------------------------------------------------------------
_BUCKET_STYLE = {
    "Strong Buy": ("🟢🟢", "#16a34a"), "Buy": ("🟢", "#22c55e"),
    "Watch / Mixed": ("🟡", "#eab308"), "Sell": ("🔴", "#ef4444"),
    "Strong Sell": ("🔴🔴", "#b91c1c"),
}


def render_screener(universe, period, n_bull, n_bear, run):
    st.header("📋 S&P 500 conviction screener")
    st.caption(
        "Runs the same engine across the index and buckets names by direction × "
        "conviction. A fast technical pre-screen ranks all names, then the full "
        "engine scores the strongest bullish and bearish candidates. **News is "
        "skipped in bulk mode for speed**, so scores use up to 7 lenses."
    )
    st.warning(
        "In a bull market the Buy buckets crowd up and Sell stays sparse — that's "
        "the structural lean, not a signal. The **Watch / Mixed** bucket (genuine "
        "disagreement) is often the most informative. Not financial advice.",
        icon="⚠️",
    )

    if run:
        bar = st.progress(0.0, "Starting…")
        try:
            res = screen_all(universe, period, n_bull, n_bear,
                             progress=lambda f, t: bar.progress(f, t))
            res["_meta"] = {"period": period, "n_bull": n_bull, "n_bear": n_bear}
            st.session_state["scan"] = res
            st.session_state.pop("saved_run", None)  # new scan = unsaved
        finally:
            bar.empty()

    res = st.session_state.get("scan")
    if not res:
        st.info("Pick candidate counts in the sidebar, then click **Run scan**.")
        return

    m1, m2, m3 = st.columns(3)
    m1.metric("Names scanned", res["scanned"])
    m2.metric("Fully scored", res["scored"])
    counts = {k: len(v) for k, v in res["buckets"].items()}
    m3.metric("Strong Buy / Strong Sell",
              f"{counts['Strong Buy']} / {counts['Strong Sell']}")

    all_scored = []
    for rows in res["buckets"].values():
        all_scored.extend(r["ticker"] for r in rows)

    for name, rows in res["buckets"].items():
        emoji, color = _BUCKET_STYLE[name]
        with st.expander(f"{emoji}  {name}  ·  {len(rows)}",
                         expanded=name in ("Strong Buy", "Strong Sell") and bool(rows)):
            if not rows:
                st.caption("Nothing in this bucket.")
                continue
            table = pd.DataFrame([{
                "Ticker": r["ticker"],
                "Dir": r["direction"],
                "Conviction": r["conviction"],
                "Agree %": round(r["agreement"] * 100),
                "Lenses": r["participation"],
                "Upside %": (round(r["upside"] * 100) if r["upside"] is not None else None),
                "P/E": (round(r["pe"], 1) if r["pe"] else None),
                "Earnings in": r["days_to_earnings"],
            } for r in rows])
            st.dataframe(table, use_container_width=True, hide_index=True)

    st.markdown("---")

    def _jump_to_detail():
        # Runs as a callback, before widgets are instantiated on the rerun,
        # so modifying the "view" radio's state here is allowed.
        pick = st.session_state.get("jump_pick")
        if pick and pick != "—":
            st.session_state["force_ticker"] = pick
            st.session_state["view"] = "📈 Single ticker"

    st.selectbox("Open a scanned ticker in the detail view",
                 ["—"] + sorted(all_scored), key="jump_pick",
                 on_change=_jump_to_detail)

    # --- Neon Postgres: save this scan & browse history --------------------
    st.markdown("##### 🗄️ Scan history (Neon Postgres)")
    ok, msg = neon_status()
    if not ok:
        st.info(
            "Not connected to Neon. Set `NEON_DATABASE_URL` (or add `[neon]` "
            f"`dsn` to `.streamlit/secrets.toml`) to save scan history. — {msg}"
        )
        return

    meta = res.get("_meta", {})
    saved_id = st.session_state.get("saved_run")
    cols = st.columns([1, 2])
    if cols[0].button("💾 Save this scan", disabled=saved_id is not None,
                      use_container_width=True):
        try:
            rid = save_scan_to_neon(res, meta.get("period"), meta.get("n_bull"),
                                    meta.get("n_bear"))
            st.session_state["saved_run"] = rid
            st.rerun()
        except Exception as e:  # noqa: BLE001
            st.error(f"Save failed: {e}")
    if saved_id is not None:
        cols[1].success(f"Saved as run #{saved_id}.")

    try:
        runs = load_scan_runs()
    except Exception as e:  # noqa: BLE001
        st.error(f"Could not load history: {e}")
        return
    if runs.empty:
        st.caption("No saved scans yet.")
        return

    st.caption("Past scans:")
    st.dataframe(runs, use_container_width=True, hide_index=True)
    labels = {f"#{r.id} · {r.ts:%Y-%m-%d %H:%M} · {r.period}": int(r.id)
              for r in runs.itertuples()}
    chosen = st.selectbox("Inspect a saved run", ["—"] + list(labels))
    if chosen != "—":
        st.dataframe(load_run_results(labels[chosen]),
                     use_container_width=True, hide_index=True)


# --------------------------------------------------------------------------
# Theme — a CSS-injected dark mode, toggled from the sidebar.
# --------------------------------------------------------------------------
_DARK_CSS = """
<style>
.stApp { background-color: #0e1117; }
.stApp, .stApp p, .stApp span, .stApp li, .stApp label,
[data-testid="stMarkdownContainer"], [data-testid="stWidgetLabel"] p {
    color: #e6edf3 !important;
}
h1, h2, h3, h4, h5, h6 { color: #ffffff !important; }
section[data-testid="stSidebar"] { background-color: #11151c !important; }
[data-testid="stHeader"] { background: rgba(0,0,0,0) !important; }
[data-testid="stMetricValue"] { color: #ffffff !important; }
[data-testid="stMetricLabel"] p { color: #9aa4b2 !important; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color: #9aa4b2 !important; }
[data-testid="stExpander"] details {
    background-color: #11151c !important; border: 1px solid #2a2f3a !important;
}
[data-testid="stExpander"] summary { color: #e6edf3 !important; }
div[data-testid="stVerticalBlockBorderWrapper"] { border-color: #2a2f3a !important; }
.stTextInput input, .stNumberInput input {
    background-color: #1c212b !important; color: #e6edf3 !important;
}
div[data-baseweb="select"] > div {
    background-color: #1c212b !important; color: #e6edf3 !important;
    border-color: #2a2f3a !important;
}
[data-baseweb="popover"] li, [role="option"] {
    background-color: #1c212b !important; color: #e6edf3 !important;
}
</style>
"""


def apply_theme(dark: bool) -> None:
    if dark:
        st.markdown(_DARK_CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------
# UI
# --------------------------------------------------------------------------
st.set_page_config(page_title="Bullseye Market Monitor", page_icon="🎯",
                   layout="wide")
st.session_state.setdefault("dark", False)
apply_theme(st.session_state["dark"])
st.title("🎯 Bullseye Market Monitor")
st.caption(
    "Educational tool. It describes what price has done and flags things "
    "worth investigating. It does not recommend trades or position sizes — "
    "that's on you. Not financial advice."
)

universe = sp500_tickers()
ticker = None
period = "1y"
scan_period = scan_bull = scan_bear = scan_run = None

with st.sidebar:
    head_l, head_r = st.columns([2, 1])
    head_l.header("Settings")
    head_r.toggle("🌙", key="dark", help="Toggle dark mode")
    view = st.radio("View", ["📈 Single ticker", "📋 Screener"], key="view",
                    label_visibility="collapsed")
    st.markdown("---")

    if view == "📈 Single ticker":
        # Honor a jump request from the screener.
        forced = st.session_state.pop("force_ticker", None)
        if forced and forced in universe:
            st.session_state["detail_ticker"] = forced
        st.session_state.setdefault("detail_ticker",
                                    "AAPL" if "AAPL" in universe else universe[0])
        ticker = st.selectbox(
            f"S&P 500 ({len(universe)} symbols)", universe, key="detail_ticker",
            help="Type to search. List refreshes from Wikipedia daily.",
        )
        custom = st.text_input(
            "…or enter any other symbol", value="",
            placeholder="e.g. SPY, BTC-USD",
        ).strip().upper()
        if custom:
            ticker = custom
        period = st.selectbox("Period", ["6mo", "1y", "2y", "5y", "max"], index=1)
    else:
        st.subheader("Screener")
        scan_period = st.selectbox("History", ["1y", "2y"], index=0)
        scan_bull = st.slider("Bullish candidates", 20, 120, 60, 10)
        scan_bear = st.slider("Bearish candidates", 0, 80, 30, 10)
        scan_run = st.button("🔍 Run scan", type="primary",
                             use_container_width=True)

    st.markdown("---")
    st.caption(f"Loaded {dt.datetime.now():%Y-%m-%d %H:%M}")

if view == "📋 Screener":
    render_screener(universe, scan_period, scan_bull, scan_bear, scan_run)
    st.stop()

if not ticker:
    st.info("Add at least one ticker in the sidebar.")
    st.stop()

with st.spinner(f"Fetching {ticker}…"):
    data = fetch(ticker, period)

if data.empty:
    st.error(f"No data for '{ticker}'. Check the symbol.")
    st.stop()

data = add_indicators(data)
last = data.iloc[-1]

c1, c2, c3, c4 = st.columns(4)
prev_close = data["Close"].iloc[-2] if len(data) > 1 else last["Close"]
pct = (last["Close"] / prev_close - 1) * 100
c1.metric("Last close", f"${last['Close']:,.2f}", f"{pct:+.2f}%")
c2.metric("RSI (14)", f"{last['RSI']:.1f}" if pd.notna(last["RSI"]) else "—")
c3.metric("50-day SMA",
          f"${last['SMA50']:,.2f}" if pd.notna(last["SMA50"]) else "—")
c4.metric("200-day SMA",
          f"${last['SMA200']:,.2f}" if pd.notna(last["SMA200"]) else "—")

st.plotly_chart(price_chart(data, ticker, dark=st.session_state["dark"]),
                use_container_width=True)

st.subheader("Observations to investigate")
for flag, note in observations(data):
    with st.container(border=True):
        st.markdown(f"**{flag}**")
        st.caption(note)

with st.expander("See the raw data"):
    st.dataframe(data.tail(60), use_container_width=True)

# --------------------------------------------------------------------------
# Conviction dashboard — at the very bottom, on purpose. Read the chart first.
# --------------------------------------------------------------------------
st.markdown("---")
st.header("Conviction dashboard")

with st.spinner("Gathering fundamentals, analyst targets & market environment…"):
    fund = fundamentals(ticker)
    analyst = analyst_view(ticker)
    env = market_environment()
    rel = relative_strength(ticker, fund.get("sector"))
    earn = earnings_proximity(ticker)
    news_items = news_feed(ticker)
news_avg, scored_news = news_sentiment(news_items)

verdict = conviction_engine(
    data, fund, analyst, env, rel, news_avg, len(news_items), earn["days"]
)


def _fmt(v, kind=""):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    if kind == "pct":
        return f"{v*100:+.1f}%"
    if kind == "x":
        return f"{v:.1f}×"
    if kind == "money":
        for unit, div in (("T", 1e12), ("B", 1e9), ("M", 1e6)):
            if abs(v) >= div:
                return f"${v/div:.1f}{unit}"
        return f"${v:,.0f}"
    if isinstance(v, float):
        return f"{v:.2f}"
    return str(v)


# --- Verdict + conviction meter ------------------------------------------
v1, v2 = st.columns([1, 1])
with v1:
    st.markdown(
        f"<div style='text-align:center;padding:1.2rem;border-radius:12px;"
        f"background:{verdict['color']}22;border:2px solid {verdict['color']};'>"
        f"<div style='font-size:0.8rem;opacity:0.7;'>DIRECTION</div>"
        f"<div style='font-size:2.4rem;font-weight:800;color:{verdict['color']};"
        f"line-height:1.1;'>{verdict['label']}</div>"
        f"<div style='font-size:0.8rem;opacity:0.7;margin-top:0.3rem;'>"
        f"score {verdict['direction']:+.2f} (−1 sell … +1 buy)</div></div>",
        unsafe_allow_html=True,
    )
with v2:
    st.markdown(
        f"<div style='text-align:center;padding:1.2rem;border-radius:12px;"
        f"background:{verdict['conv_color']}22;border:2px solid {verdict['conv_color']};'>"
        f"<div style='font-size:0.8rem;opacity:0.7;'>CONVICTION</div>"
        f"<div style='font-size:2.4rem;font-weight:800;color:{verdict['conv_color']};"
        f"line-height:1.1;'>{verdict['conviction']}</div>"
        f"<div style='font-size:0.8rem;opacity:0.7;margin-top:0.3rem;'>"
        f"{verdict['agreement']*100:.0f}% of {verdict['participation']} active "
        f"lenses agree</div></div>",
        unsafe_allow_html=True,
    )

if verdict["event_warning"]:
    st.warning("📅 " + verdict["event_warning"])

# --- The lenses ----------------------------------------------------------
st.markdown("##### How each lens votes")
st.caption(
    "Conviction is high only when independent lenses agree. Disagreement "
    "below is the signal — it tells you the call is contested."
)
for name, weight, vote, detail in verdict["lenses"]:
    mark = "🟢" if vote > 0 else "🔴" if vote < 0 else "⚪️"
    wlabel = "" if weight == 1.0 else f"  ·  weight {weight:g}"
    st.markdown(f"{mark} **{name}** — {detail}{wlabel}")

# --- Supporting detail panels --------------------------------------------
st.markdown("##### The data behind it")
p1, p2, p3 = st.columns(3)

with p1:
    st.markdown("**Valuation & quality**")
    rows = [
        ("Fwd P/E", _fmt(fund.get("forwardPE"))),
        ("Trailing P/E", _fmt(fund.get("trailingPE"))),
        ("PEG", _fmt(fund.get("pegRatio"))),
        ("P/S", _fmt(fund.get("priceToSalesTrailing12Months"))),
        ("Rev growth", _fmt(fund.get("revenueGrowth"), "pct")),
        ("EPS growth", _fmt(fund.get("earningsGrowth"), "pct")),
        ("Profit margin", _fmt(fund.get("profitMargins"), "pct")),
        ("ROE", _fmt(fund.get("returnOnEquity"), "pct")),
        ("Market cap", _fmt(fund.get("marketCap"), "money")),
    ]
    for k, val in rows:
        st.caption(f"{k}: **{val}**")

with p2:
    st.markdown("**Analyst view**")
    if analyst.get("target_mean"):
        st.caption(f"Mean target: **${analyst['target_mean']:,.2f}**")
        st.caption(f"Implied upside: **{_fmt(analyst.get('upside'), 'pct')}**")
        st.caption(f"Range: {_fmt(analyst.get('target_low'))} – "
                   f"{_fmt(analyst.get('target_high'))}")
        st.caption(f"Consensus: **{analyst.get('rec_key') or '—'}** "
                   f"(mean {_fmt(analyst.get('rec_mean'))}, 1=buy 5=sell)")
        st.caption(f"Analysts: {analyst.get('n_analysts') or '—'}")
    else:
        st.caption("No analyst coverage returned.")
    st.markdown("**Event risk**")
    if earn.get("days") is not None:
        st.caption(f"Next earnings: **{earn['date']}** "
                   f"({earn['days']} days out)")
    else:
        st.caption("No scheduled earnings date found.")

with p3:
    st.markdown("**Market environment**")
    if "spy_above_200" in env:
        st.caption(f"SPY vs 200-day: **{'above ✅' if env['spy_above_200'] else 'below ⚠️'}**")
    if env.get("spy_ret_3m") is not None:
        st.caption(f"SPY 3-mo return: **{_fmt(env['spy_ret_3m'], 'pct')}**")
    if env.get("vix") is not None:
        mood = "calm" if env["vix"] < 20 else "elevated" if env["vix"] < 30 else "fearful"
        st.caption(f"VIX: **{env['vix']:.1f}** ({mood})")
    if env.get("tnx") is not None:
        st.caption(f"10-yr yield: **{env['tnx']:.2f}%**")
    st.markdown("**Relative strength (3-mo total return)**")
    if rel.get("stock") is not None:
        st.caption(f"{ticker}: **{_fmt(rel['stock'], 'pct')}**")
    if rel.get("spy") is not None:
        delta = (rel["stock"] - rel["spy"]) if rel.get("stock") is not None else None
        st.caption(f"SPY: {_fmt(rel['spy'], 'pct')}  →  {ticker} "
                   f"**{_fmt(delta, 'pct')}** vs SPY")
    if rel.get("sector") is not None:
        delta = (rel["stock"] - rel["sector"]) if rel.get("stock") is not None else None
        st.caption(f"{rel.get('etf')} (sector): {_fmt(rel['sector'], 'pct')}  →  "
                   f"{ticker} **{_fmt(delta, 'pct')}** vs sector")

st.warning(
    "This combines technicals, fundamentals, analyst targets, the market "
    "regime, relative strength and headline sentiment into one view. It is "
    "**not a forecast and not financial advice.** More inputs reduce false "
    "signals but can also manufacture false confidence — treat LOW conviction "
    "as a genuine 'I don't know,' and always do your own work. The decision is yours."
)

with st.expander(f"Headlines factored in ({len(news_items)})"):
    if not news_items:
        st.caption("No recent headlines returned for this symbol.")
    for it, s in scored_news:
        tag = "🟢" if s > 0 else "🔴" if s < 0 else "⚪️"
        title = f"[{it['title']}]({it['url']})" if it["url"] else it["title"]
        meta = " · ".join(x for x in (it["publisher"], str(it["time"])[:10]) if x)
        st.markdown(f"{tag} {title}")
        if meta:
            st.caption(meta)
