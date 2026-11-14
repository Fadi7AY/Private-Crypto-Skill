import numpy as np
import pandas as pd
import pytest
from crypto_skill.core import validate, indicators, size, backtest

def sample():
    n=180; p=100+np.linspace(0,20,n)+4*np.sin(np.arange(n)/8)
    return pd.DataFrame({"timestamp":pd.date_range("2025-01-01",periods=n,freq="h",tz="UTC"),
                         "open":p,"high":p+1,"low":p-1,"close":p,"volume":1000})
def test_indicators():
    x=indicators(sample())
    assert x.ema50.notna().sum()>100
    assert x.rsi.dropna().between(0,100).all()
def test_backtest():
    r=backtest(sample())
    assert r["final_equity"]>=0 and r["max_drawdown_pct"]<=0
def test_invalid():
    x=sample(); x.loc[2,"timestamp"]=x.loc[1,"timestamp"]
    with pytest.raises(ValueError): validate(x)
def test_risk():
    d=size(10000,10000,100,95)
    assert d.approved and d.notional<=2000.01 and d.estimated_stop_loss<=50.01
    assert not size(10000,10000,100,101).approved
