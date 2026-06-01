"""
Market Monitor — an educational dashboard.

What it does: pulls price/volume data, computes common technical indicators,
and surfaces neutral *observations* for you to investigate and learn from.

What it deliberately does NOT do: tell you what to buy, when to buy, or how
much. Indicators describe what price has done; they do not prescribe action.
The interpretation is yours.

Run with:  streamlit run market_monitor.py
"""

import datetime as dt
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

    return df


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


def combined_suggestion(df: pd.DataFrame, news_avg: float) -> dict:
    """Blend technical votes with news tilt into one Buy/Neutral/Sell label."""
    signals = technical_signals(df)
    tech_votes = [v for _, v, _ in signals]
    tech_sum = sum(tech_votes)
    tech_max = len(tech_votes) or 1
    tech_norm = tech_sum / tech_max  # -1 .. +1

    news_norm = max(-1.0, min(1.0, news_avg / 2.0))  # squash to -1 .. +1

    # Technicals carry the weight here; news is a tilt, not a driver.
    blended = 0.75 * tech_norm + 0.25 * news_norm

    if blended >= 0.34:
        label, color = "BUY", "#22c55e"
    elif blended <= -0.34:
        label, color = "SELL", "#ef4444"
    else:
        label, color = "NEUTRAL", "#eab308"

    return {
        "label": label,
        "color": color,
        "blended": blended,
        "tech_sum": tech_sum,
        "tech_max": tech_max,
        "signals": signals,
        "news_norm": news_norm,
    }


# --------------------------------------------------------------------------
# Charts
# --------------------------------------------------------------------------
def price_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03,
        row_heights=[0.6, 0.2, 0.2],
        subplot_titles=(f"{ticker} — price, moving averages & Bollinger Bands",
                        "RSI (14)", "MACD (12/26/9)"),
    )

    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"], name="Price"), row=1, col=1)
    for col, color in [("SMA50", "#5B8FF9"), ("SMA200", "#F6BD16"),
                       ("BB_up", "#bbb"), ("BB_low", "#bbb")]:
        fig.add_trace(go.Scatter(x=df.index, y=df[col], name=col,
                                 line=dict(width=1, color=color)), row=1, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], name="RSI",
                             line=dict(color="#9270CA")), row=2, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="#e8684a", row=2, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="#5ad8a6", row=2, col=1)

    fig.add_trace(go.Bar(x=df.index, y=df["MACD_hist"], name="Hist",
                         marker_color="#ccc"), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], name="MACD",
                             line=dict(color="#5B8FF9")), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["MACD_signal"], name="Signal",
                             line=dict(color="#F6BD16")), row=3, col=1)

    fig.update_layout(height=720, xaxis_rangeslider_visible=False,
                      showlegend=True, margin=dict(t=40, b=20))
    return fig


# --------------------------------------------------------------------------
# UI
# --------------------------------------------------------------------------
st.set_page_config(page_title="Market Monitor", layout="wide")
st.title("Market Monitor")
st.caption(
    "Educational tool. It describes what price has done and flags things "
    "worth investigating. It does not recommend trades or position sizes — "
    "that's on you. Not financial advice."
)

with st.sidebar:
    st.header("Settings")

    universe = sp500_tickers()
    default_idx = universe.index("AAPL") if "AAPL" in universe else 0
    ticker = st.selectbox(
        f"S&P 500 ({len(universe)} symbols)", universe, index=default_idx,
        help="Type to search. List refreshes from Wikipedia daily.",
    )

    custom = st.text_input(
        "…or enter any other symbol", value="",
        placeholder="e.g. SPY, BTC-USD",
    ).strip().upper()
    if custom:
        ticker = custom

    period = st.selectbox(
        "Period", ["6mo", "1y", "2y", "5y", "max"], index=1
    )
    st.markdown("---")
    st.caption(f"Loaded {dt.datetime.now():%Y-%m-%d %H:%M}")

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

st.plotly_chart(price_chart(data, ticker), use_container_width=True)

st.subheader("Observations to investigate")
for flag, note in observations(data):
    with st.container(border=True):
        st.markdown(f"**{flag}**")
        st.caption(note)

with st.expander("See the raw data"):
    st.dataframe(data.tail(60), use_container_width=True)

# --------------------------------------------------------------------------
# Suggestion — at the very bottom, on purpose. Read everything above first.
# --------------------------------------------------------------------------
st.markdown("---")
st.subheader("Mechanical suggestion")

news_items = news_feed(ticker)
news_avg, scored_news = news_sentiment(news_items)
verdict = combined_suggestion(data, news_avg)

v1, v2 = st.columns([1, 2])
with v1:
    st.markdown(
        f"<div style='text-align:center;padding:1.2rem;border-radius:12px;"
        f"background:{verdict['color']}22;border:2px solid {verdict['color']};'>"
        f"<div style='font-size:2.4rem;font-weight:800;color:{verdict['color']};"
        f"line-height:1;'>{verdict['label']}</div>"
        f"<div style='font-size:0.8rem;opacity:0.7;margin-top:0.4rem;'>"
        f"score {verdict['blended']:+.2f} &nbsp;(−1 sell … +1 buy)</div></div>",
        unsafe_allow_html=True,
    )
with v2:
    st.caption(
        f"Technical vote: **{verdict['tech_sum']:+d}** out of "
        f"±{verdict['tech_max']} signals &nbsp;·&nbsp; "
        f"News tilt: **{verdict['news_norm']:+.2f}** "
        f"from {len(news_items)} headlines."
    )
    for name, vote, why in verdict["signals"]:
        mark = "🟢" if vote > 0 else "🔴" if vote < 0 else "⚪️"
        st.markdown(f"{mark} **{name}** — {why}")

st.warning(
    "This label is a weighted tally of the indicators above (75%) plus a "
    "keyword read of recent headlines (25%). It is **not a forecast and not "
    "financial advice** — it can't see fundamentals, valuation, your time "
    "horizon, or anything the chart doesn't already show. The decision is yours."
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
