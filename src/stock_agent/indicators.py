"""기술적 지표 계산 유틸리티 (pandas 기반)."""

from __future__ import annotations

import numpy as np
import pandas as pd


def pct_change_over(close: pd.Series, periods: int) -> float:
    """periods 영업일 전 대비 등락률(%)."""
    if len(close) <= periods:
        return 0.0
    prev = close.iloc[-(periods + 1)]
    last = close.iloc[-1]
    if prev == 0 or pd.isna(prev) or pd.isna(last):
        return 0.0
    return float((last / prev - 1.0) * 100.0)


def sma(close: pd.Series, window: int) -> float:
    if len(close) < window:
        return float("nan")
    return float(close.tail(window).mean())


def rsi(close: pd.Series, period: int = 14) -> float:
    """Wilder RSI."""
    if len(close) <= period:
        return 50.0
    delta = close.diff().dropna()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean().iloc[-1]
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean().iloc[-1]
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100.0 - 100.0 / (1.0 + rs))


def momentum_score(close: pd.Series) -> float:
    """단기+중기 모멘텀을 결합한 0~100 점수.

    구성: 5일/20일/60일 등락률 가중합을 시그모이드로 정규화.
    """
    p5 = pct_change_over(close, 5)
    p20 = pct_change_over(close, 20)
    p60 = pct_change_over(close, 60)
    raw = 0.5 * p20 + 0.3 * p5 + 0.2 * p60
    # 시그모이드 정규화 (raw 0% -> 50점)
    return float(100.0 / (1.0 + np.exp(-raw / 5.0)))


def trend_flags(close: pd.Series) -> tuple[bool, bool]:
    """(20일선 위, 60일선 위) 여부."""
    last = float(close.iloc[-1])
    ma20 = sma(close, 20)
    ma60 = sma(close, 60)
    above20 = bool(not np.isnan(ma20) and last > ma20)
    above60 = bool(not np.isnan(ma60) and last > ma60)
    return above20, above60
