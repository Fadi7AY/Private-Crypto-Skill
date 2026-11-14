from dataclasses import dataclass, asdict
import math
import numpy as np
import pandas as pd

COLS = ("timestamp", "open", "high", "low", "close", "volume")

def validate(df):
    if not set(COLS).issubset(df.columns):
        raise ValueError("Missing OHLCV columns")
    x = df.copy()
    x["timestamp"] = pd.to_datetime(x["timestamp"], utc=True, errors="raise")
    if x["timestamp"].isna().any() or x["timestamp"].duplicated().any() or not x["timestamp"].is_monotonic_increasing:
        raise ValueError("Invalid chronological timestamps")
    for c in COLS[1:]:
        x[c] = pd.to_numeric(x[c], errors="raise")
    if len(x) < 60 or x[list(COLS[1:])].isna().any().any():
        raise ValueError("Need 60+ non-null candles")
    if (x[["open", "high", "low", "close"]] <= 0).any().any() or (x["volume"] < 0).any():
        raise ValueError("Bad prices / volume")
    if ((x.high < x[["open", "low", "close"]].max(axis=1)) |
        (x.low > x[["open", "high", "close"]].min(axis=1))).any():
        raise ValueError("Invalid OHLC bounds")
    return x.reset_index(drop=True)

def indicators(df):
    x = validate(df)
    c = x.close
    x["ema20"] = c.ewm(span=20, adjust=False, min_periods=20).mean()
    x["ema50"] = c.ewm(span=50, adjust=False, min_periods=50).mean()
    d = c.diff()
    g = d.clip(lower=0).ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    l = (-d.clip(upper=0)).ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    x["rsi"] = 100 - 100/(1 + g/l.replace(0, np.nan))
    x.loc[(l == 0) & (g > 0), "rsi"] = 100
    x.loc[(l == 0) & (g == 0), "rsi"] = 50
    tr = pd.concat([x.high-x.low, (x.high-c.shift()).abs(), (x.low-c.shift()).abs()], axis=1).max(axis=1)
    x["atr"] = tr.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    x["buy"] = (x.ema20 > x.ema50) & (x.ema20.shift() <= x.ema50.shift()) & x.rsi.between(45,70) & x.atr.gt(0)
    x["sell"] = (x.ema20 < x.ema50) & (x.ema20.shift() >= x.ema50.shift())
    return x

@dataclass
class Risk:
    approved: bool
    units: float
    notional: float
    estimated_stop_loss: float
    reason: str

def size(equity, cash, entry, stop, risk_fraction=0.005, allocation=0.20, fee=0.001):
    if not all(math.isfinite(v) for v in (equity,cash,entry,stop,risk_fraction,allocation,fee)):
        return Risk(False,0,0,0,"Non-finite input")
    if min(equity,cash,entry,stop) <= 0 or stop >= entry or not (0 < risk_fraction <= .02 and 0 < allocation <= 1 and 0 <= fee < .05):
        return Risk(False,0,0,0,"Invalid risk constraints")
    loss = entry-stop+fee*(entry+stop)
    qty = min(equity*risk_fraction/loss, equity*allocation/entry, cash/(entry*(1+fee)))
    return Risk(qty>0, qty, qty*entry, qty*loss, "Simulation only; exchange precision and limits unverified")

def analyze(df):
    z = indicators(df).iloc[-1]
    return {"time_utc":z.timestamp.isoformat(),"close":float(z.close),"ema20":float(z.ema20),
            "ema50":float(z.ema50),"rsi14":float(z.rsi),"atr14":float(z.atr),
            "buy":bool(z.buy),"sell":bool(z.sell)}

def backtest(df, starting_cash=10000, fee=.001, slip=.0005):
    if starting_cash <= 0 or not (0 <= fee < .05 and 0 <= slip < .05):
        raise ValueError("Bad costs/equity")
    x = indicators(df); cash = float(starting_cash); qty = 0.; stop = 0.; cost = 0.
    equity = [cash]; trades=[]
    for i in range(1,len(x)):
        prev, b = x.iloc[i-1], x.iloc[i]
        op = float(b.open)
        if qty:
            fill = None
            if op <= stop: fill = op*(1-slip)
            elif float(b.low) <= stop: fill = stop*(1-slip)
            elif bool(prev.sell): fill = op*(1-slip)
            if fill is not None:
                proceeds = qty*fill*(1-fee)
                cash += proceeds; trades.append(proceeds-cost)
                qty=0.; stop=0.; cost=0.
        if not qty and bool(prev.buy):
            fill=op*(1+slip); proposed=fill-2*float(prev.atr)
            decision=size(cash,cash,fill,proposed,fee=fee)
            if decision.approved:
                qty=decision.units; stop=proposed
                cost=qty*fill*(1+fee); cash-=cost
        equity.append(cash+qty*float(b.close))
    curve=pd.Series(equity)
    final=float(equity[-1])
    return {"starting_cash":starting_cash, "final_equity":round(final,2),
            "return_pct":round(100*(final/starting_cash-1),2),
            "buy_hold_pct":round(100*(x.close.iloc[-1]/x.close.iloc[0]-1),2),
            "max_drawdown_pct":round(100*(curve/curve.cummax()-1).min(),2),
            "closed_trades":len(trades),"winning_trades":sum(v>0 for v in trades),
            "open_units":qty,"fees":fee,"slippage":slip,
            "note":"Historical next-open fills / approximate intrabar stop; no live execution"}
