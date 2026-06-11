import numpy as np
import pandas as pd

from stock_agent.indicators import momentum_score, pct_change_over, rsi, trend_flags


def _series(values):
    idx = pd.date_range("2024-01-01", periods=len(values), freq="B")
    return pd.Series(values, index=idx, dtype=float)


def test_pct_change_over():
    s = _series([100, 110, 121])
    assert round(pct_change_over(s, 1), 2) == 10.0
    assert round(pct_change_over(s, 2), 2) == 21.0
    # 기간이 시리즈보다 길면 0
    assert pct_change_over(s, 10) == 0.0


def test_rsi_bounds_and_uptrend():
    up = _series(list(np.linspace(100, 200, 60)))
    val = rsi(up, 14)
    assert 0.0 <= val <= 100.0
    # 지속 상승은 RSI가 높게 나와야 함
    assert val > 70


def test_trend_flags_uptrend():
    up = _series(list(np.linspace(100, 200, 120)))
    above20, above60 = trend_flags(up)
    assert above20 is True
    assert above60 is True


def test_momentum_score_monotonic():
    up = _series(list(np.linspace(100, 160, 80)))
    down = _series(list(np.linspace(160, 100, 80)))
    assert momentum_score(up) > momentum_score(down)
    assert 0.0 <= momentum_score(up) <= 100.0
