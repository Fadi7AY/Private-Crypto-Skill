# Claude Code Crypto Spot Skills

Research-grade, **paper-only** spot trading toolkit. No exchange order placement, leverage, shorts, or API keys. No claim of profitability.

## Setup
Python >=3.10:
```bash
pip install -e ".[dev]"
pytest -q
crypto-skill fetch --symbol BTC/USDT --timeframe 1h --limit 500 --csv candles.csv
crypto-skill analyze --csv candles.csv --drop-last
crypto-skill backtest --csv candles.csv --drop-last
crypto-skill paper --csv candles.csv --drop-last --state paper.json
crypto-skill risk --equity 10000 --cash 10000 --entry 100 --stop 95
```

Use Claude Code commands /spot-market-scan, /spot-signal-review, /spot-risk-check, /spot-backtest, /spot-paper-trade, and /tradingview-alert-review in this repository.

## Baseline
Long-only research strategy: EMA20 crosses above EMA50, RSI(14) in [45,70], initial 2x ATR(14) stop; sell on cross below or stop. Backtests decide at completed candle t, execute no earlier than candle t+1. Stops are simulated using next candle open and intrabar low, including gap risk. Fees and slippage are modeled. Paper snapshots are **not continuously monitored** and don't protect funds. Market data may have gaps; validate quality before conclusions.

Defaults: 0.5% equity risk/trade, max 20% account allocation, 0.1% fee, 0.05% slippage. Daily-loss limits / correlation require external portfolio enforcement before *any* future live integration. Backtests do not establish expected profits; perform holdout and walk-forward tests.

Sources for design review: [Freqtrade](https://github.com/freqtrade/freqtrade), [CCXT](https://github.com/ccxt/ccxt), [Claude skills](https://code.claude.com/docs/en/skills), [TradingView alerts](https://www.tradingview.com/support/solutions/43000529348-how-to-configure-webhook-alerts/). Implementation is original, not copied from another strategy. Never commit secrets.
