import argparse
import json
from dataclasses import asdict
from pathlib import Path
import pandas as pd
from .core import validate, indicators, analyze, backtest, size

def data(path, drop_last):
    x=pd.read_csv(path)
    if drop_last: x=x.iloc[:-1]
    return validate(x)

def fetch(a):
    import ccxt
    if a.exchange not in ccxt.exchanges: raise ValueError("Unknown exchange")
    ex=getattr(ccxt,a.exchange)({"enableRateLimit":True,"timeout":15000})
    try:
        ex.load_markets()
        market=ex.market(a.symbol)
        if not market.get("spot") or market.get("active") is False: raise ValueError("Not an active spot market")
        rows=ex.fetch_ohlcv(a.symbol,a.timeframe,limit=a.limit)
        if not rows: raise ValueError("No candles")
        x=pd.DataFrame(rows,columns=["timestamp","open","high","low","close","volume"])
        x["timestamp"]=pd.to_datetime(x.timestamp,unit="ms",utc=True)
        x.to_csv(a.csv,index=False)
        return {"saved":a.csv,"rows":len(x),"warning":"Last candle may be incomplete: use --drop-last"}
    finally: ex.close()

def paper(a):
    x=indicators(data(a.csv,a.drop_last))
    b=x.iloc[-1]; p=Path(a.state)
    st=json.loads(p.read_text()) if p.exists() else {"cash":a.starting_cash,"units":0.0,"stop":0.0,"last":""}
    if b.timestamp.isoformat() <= st["last"]: return {"action":"unchanged","state":st}
    price=float(b.close); action="hold"
    if st["units"] and (price <= st["stop"] or bool(b.sell)):
        st["cash"]+=st["units"]*price*(1-a.fee); st["units"]=0; st["stop"]=0; action="paper_sell"
    elif not st["units"] and bool(b.buy):
        stop=price-2*float(b.atr)
        r=size(st["cash"],st["cash"],price,stop,fee=a.fee)
        if r.approved:
            st["units"]=r.units; st["cash"]-=r.units*price*(1+a.fee)
            st["stop"]=stop; action="paper_buy"
    st["last"]=b.timestamp.isoformat()
    temp=p.with_suffix(p.suffix+".tmp")
    temp.write_text(json.dumps(st,indent=2)); temp.replace(p)
    return {"action":action,"paper_equity":round(st["cash"]+st["units"]*price,2),
            "state":st,"warning":"Snapshot simulation; NOT a real order or protective stop"}

def main():
    p=argparse.ArgumentParser()
    s=p.add_subparsers(dest="cmd",required=True)
    f=s.add_parser("fetch")
    f.add_argument("--exchange",default="binance"); f.add_argument("--symbol",default="BTC/USDT")
    f.add_argument("--timeframe",default="1h"); f.add_argument("--limit",type=int,default=500)
    f.add_argument("--csv",default="candles.csv")
    for name in ("analyze","backtest","paper"):
        q=s.add_parser(name); q.add_argument("--csv",required=True)
        q.add_argument("--drop-last",action="store_true")
        if name == "backtest":
            q.add_argument("--starting-cash",type=float,default=10000)
        if name == "paper":
            q.add_argument("--state",default="paper.json")
            q.add_argument("--starting-cash",type=float,default=10000)
            q.add_argument("--fee",type=float,default=.001)
    r=s.add_parser("risk")
    for k in ("equity","cash","entry","stop"):
        r.add_argument("--"+k,type=float,required=True)
    a=p.parse_args()
    if a.cmd=="fetch": result=fetch(a)
    elif a.cmd=="risk": result=asdict(size(a.equity,a.cash,a.entry,a.stop))
    elif a.cmd=="analyze": result=analyze(data(a.csv,a.drop_last))
    elif a.cmd=="backtest": result=backtest(data(a.csv,a.drop_last),a.starting_cash)
    else: result=paper(a)
    print(json.dumps(result,indent=2))

if __name__=="__main__": main()
