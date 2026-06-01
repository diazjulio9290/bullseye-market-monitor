# Market Monitor

An educational technical-analysis dashboard built with [Streamlit](https://streamlit.io/).

It pulls price/volume data for any S&P 500 name (or a custom symbol), computes
common technical indicators by hand, surfaces neutral observations worth
investigating, and renders a **mechanical** Buy / Neutral / Sell summary.

> **Not financial advice.** The suggestion is a weighted tally of chart
> indicators (75%) plus a keyword read of recent headlines (25%). It is not a
> forecast and cannot see fundamentals, valuation, or your time horizon. The
> decision is yours.

## Features

- **Full S&P 500 universe** — searchable dropdown of all constituents, refreshed
  daily from Wikipedia (with a baked-in offline fallback). Plus a custom-symbol
  box for anything else (ETFs, crypto like `BTC-USD`, etc.).
- **Indicators** computed transparently: SMA 50/200, RSI (14, Wilder),
  MACD (12/26/9), Bollinger Bands (20, 2σ).
- **Interactive Plotly charts** — candlesticks with overlays, plus RSI and MACD
  subplots.
- **Observations** — neutral flags (golden/death cross, overbought/oversold,
  band tags) each paired with what to go learn about.
- **Conviction dashboard** — a Buy/Neutral/Sell **direction** *and* a
  High/Medium/Low **conviction** read derived from how much eight independent
  lenses agree, plus the supporting fundamentals, analyst targets, market
  environment, relative strength, and event-risk data behind it.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
streamlit run market_monitor.py
```

Then open <http://localhost:8501>.

## How conviction is scored

Eight independent lenses each cast a −1 / 0 / +1 vote:

| Lens | What it reads |
| --- | --- |
| Trend | price vs 200-day, 50/200 regime |
| Momentum | MACD vs signal, RSI zone |
| Valuation | P/E, PEG, P/S |
| Quality / growth | revenue & EPS growth, margins, ROE |
| Analyst targets | implied upside, consensus rating |
| Market regime | SPY vs 200-day, VIX |
| Relative strength | 3-mo return vs SPY and sector ETF |
| News sentiment | keyword lexicon over recent headlines (½ weight) |

- **Direction** is the weighted net vote: `≥ +0.30 → BUY`, `≤ −0.30 → SELL`,
  otherwise `NEUTRAL`.
- **Conviction** is *agreement*, not strength: HIGH only when ≥78% of the active
  lenses point the same way (and ≥5 are active); MEDIUM at ≥62%; otherwise LOW.
  Earnings within 7 days caps conviction down a notch.

The point is to surface **disagreement** — a contested call should read LOW even
if it leans one way. Weights and thresholds are simple defaults; tune to taste.

> Note: analyst consensus and the trend/regime lenses skew structurally bullish
> (Wall Street rarely says "sell"; most names sit above their 200-day in a bull
> market). Expect a bullish lean for quality large-caps — the tool is most
> useful when it flags *conflict*, not agreement.

## Data source

Price and news data come from Yahoo Finance via
[`yfinance`](https://github.com/ranaroussi/yfinance). It is unofficial and
rate-limited; occasional fetch failures are usually a rate limit or a bad symbol.
