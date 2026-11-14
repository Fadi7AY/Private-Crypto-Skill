---
name: spot-market-scan
description: spot market scan for research and paper-only spot crypto trading
---

# spot-market-scan

Fetch spot OHLCV with crypto-skill fetch --symbol BTC/USDT --timeframe 1h --csv candles.csv; analyze --csv candles.csv --drop-last. Check UTC timestamp, gaps, missing bars, liquidity, freshness, RSI14, EMA20/EMA50, ATR14. No trade if data is stale.
