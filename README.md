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
  MACD (12/26/9), Bollinger Bands (20, 2σ), and **Ripster EMA Clouds**
  (5/12, 34/50, 72/89) shaded green/red on the chart.
- **Interactive Plotly charts** — candlesticks with overlays, plus RSI and MACD
  subplots. **Dark mode** toggle in the sidebar.
- **Observations** — neutral flags (golden/death cross, overbought/oversold,
  band tags, Ripster cloud alignment) each paired with what to go learn about.
- **Conviction dashboard** — a Buy/Neutral/Sell **direction** *and* a
  High/Medium/Low **conviction** read derived from how much nine independent
  lenses agree, plus the supporting fundamentals, analyst targets, market
  environment, relative strength, and event-risk data behind it.
- **S&P 500 screener** — scans the whole index and buckets names into Strong Buy /
  Buy / Watch-Mixed / Sell / Strong Sell. Hybrid: a fast technical pre-screen on
  all 503, then the full engine on the strongest candidates (threaded). Click any
  result to open it in the detail view.

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

Nine independent lenses each cast a −1 / 0 / +1 vote:

| Lens | What it reads |
| --- | --- |
| Trend | price vs 200-day, 50/200 regime |
| Momentum | MACD vs signal, RSI zone |
| Ripster EMA clouds | cloud colours, price vs fast cloud, cloud stacking |
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

### Ripster EMA Clouds

Popularised by Ripster47, each "cloud" is the shaded gap between a fast and a
slow EMA — here 5/12 (short), 34/50 (intermediate) and 72/89 (longer). A cloud is
**green** when its faster EMA leads, **red** when it lags. The lens runs five
checks — the three cloud colours, price relative to the fast cloud, and whether
the fast cloud is stacked above the intermediate cloud — and nets them:

- **Bullish**: price riding above green, upward-stacked clouds.
- **Bearish**: price below red, downward-stacked clouds.

## Scan history (Neon Postgres)

The screener can persist each scan to a [Neon](https://neon.tech) Postgres
database so you build a historical record of how conviction shifts over time.
It's optional — without a connection the app runs normally and just hides the
save controls.

Provide the connection string one of two ways:

```bash
export NEON_DATABASE_URL="postgresql://USER:PASSWORD@ENDPOINT.neon.tech/DB?sslmode=require"
```

or copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` (gitignored)
and fill in the `[neon] dsn` value. The app creates the `scan_runs` and
`scan_results` tables automatically on first connect. In the Screener view, run a
scan then click **💾 Save this scan**; past runs are listed below and any run can
be re-inspected.

## Data source

Price and news data come from Yahoo Finance via
[`yfinance`](https://github.com/ranaroussi/yfinance). It is unofficial and
rate-limited; occasional fetch failures are usually a rate limit or a bad symbol.
