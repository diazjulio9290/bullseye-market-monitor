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
- **Mechanical suggestion** — a single Buy/Neutral/Sell verdict with a full,
  transparent breakdown of every contributing signal and the headlines factored in.

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

## How the suggestion is scored

Each technical signal casts a −1 / 0 / +1 vote (RSI zone, price vs 200-day,
50/200 trend regime, MACD vs signal, Bollinger position). Recent headlines are
scored with a small positive/negative keyword lexicon. The two are blended:

```
score = 0.75 × (technical votes, normalized) + 0.25 × (news tilt, normalized)
```

`score ≥ +0.34 → BUY`, `score ≤ −0.34 → SELL`, otherwise `NEUTRAL`.

The weights and thresholds are simple defaults — tune them to taste.

## Data source

Price and news data come from Yahoo Finance via
[`yfinance`](https://github.com/ranaroussi/yfinance). It is unofficial and
rate-limited; occasional fetch failures are usually a rate limit or a bad symbol.
