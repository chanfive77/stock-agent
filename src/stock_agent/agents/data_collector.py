"""Agent 1 — 데이터 수집.

지수/종목 데이터를 수집하고 종목별 기술적 지표를 계산하여
이후 모든 에이전트가 사용할 ``market_data`` 를 구성한다.
"""

from __future__ import annotations

import logging

import pandas as pd

from ..config import Config
from ..data import DataProvider
from ..indicators import momentum_score, pct_change_over, rsi, trend_flags
from ..state import PipelineState

log = logging.getLogger(__name__)


def _index_summary(df: pd.DataFrame) -> dict:
    close = df["Close"].dropna()
    return {
        "pct_1d": pct_change_over(close, 1),
        "pct_5d": pct_change_over(close, 5),
        "pct_20d": pct_change_over(close, 20),
        "pct_60d": pct_change_over(close, 60),
        "last_close": float(close.iloc[-1]) if len(close) else 0.0,
        "close": close,
    }


def _stock_indicators(code: str, row: pd.Series, provider: DataProvider) -> dict | None:
    df = provider.stock_ohlcv(code)
    if df is None or "Close" not in df.columns or len(df) < 60:
        return None
    close = df["Close"].dropna()
    if len(close) < 60:
        return None
    above20, above60 = trend_flags(close)
    return {
        "Code": code,
        "Name": row["Name"],
        "Market": row["Market"],
        "Sector": row["Sector"],
        "Marcap": float(row["Marcap"]),
        "last_close": float(close.iloc[-1]),
        "pct_1d": pct_change_over(close, 1),
        "pct_5d": pct_change_over(close, 5),
        "pct_20d": pct_change_over(close, 20),
        "pct_60d": pct_change_over(close, 60),
        "rsi14": rsi(close, 14),
        "above_ma20": above20,
        "above_ma60": above60,
        "mom_score": momentum_score(close),
    }


def run(state: PipelineState, cfg: Config) -> PipelineState:
    provider = DataProvider(lookback_days=cfg.market.lookback_days)
    errors = list(state.get("errors", []))

    # 1) 지수
    indices: dict[str, dict] = {}
    for market in ("KOSPI", "KOSDAQ"):
        try:
            indices[market] = _index_summary(provider.index_ohlcv(market))
        except Exception as e:  # noqa: BLE001
            errors.append(f"index({market}) 수집 실패: {e}")

    # 2) 유니버스 + 종목별 지표
    rows: list[dict] = []
    try:
        uni = provider.universe(cfg.market.universe, cfg.market.top_n_by_marketcap)
        log.info("유니버스 %d종목 수집, 일봉 다운로드 시작", len(uni))
        for _, row in uni.iterrows():
            rec = _stock_indicators(row["Code"], row, provider)
            if rec is not None:
                rows.append(rec)
        log.info("일봉/지표 계산 완료: %d종목", len(rows))
    except Exception as e:  # noqa: BLE001
        errors.append(f"유니버스 수집 실패: {e}")

    stocks = pd.DataFrame(rows)

    # 3) 섹터 집계 (시총 가중 모멘텀)
    sectors = pd.DataFrame()
    if not stocks.empty:
        def _agg(g: pd.DataFrame) -> pd.Series:
            w = g["Marcap"].clip(lower=1)
            return pd.Series(
                {
                    "mom_score": float((g["mom_score"] * w).sum() / w.sum()),
                    "pct_20d": float((g["pct_20d"] * w).sum() / w.sum()),
                    "pct_5d": float((g["pct_5d"] * w).sum() / w.sum()),
                    "breadth_ma20": float(g["above_ma20"].mean()),
                    "n": int(len(g)),
                }
            )

        sectors = (
            stocks.groupby("Sector", group_keys=False)[
                ["Marcap", "mom_score", "pct_20d", "pct_5d", "above_ma20"]
            ]
            .apply(_agg)
            .reset_index()
        )
        # 너무 적은 표본의 섹터는 후순위(노이즈 제거)
        sectors = sectors[sectors["n"] >= 2]

    state["market_data"] = {
        "indices": indices,
        "stocks": stocks,
        "sectors": sectors,
    }
    state["errors"] = errors
    return state
