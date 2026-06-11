"""데이터 제공자 (pykrx/FinanceDataReader 래퍼).

현재는 FinanceDataReader 를 1차 소스로 사용한다.
- 지수(KOSPI/KOSDAQ) 일봉
- 전체 종목 스냅샷(시가총액, 등락률) + 섹터 분류
- 개별 종목 일봉 (디스크 캐시)

추후 한국투자증권(KIS) API 로 교체할 수 있도록 인터페이스를 단순하게 유지한다.
"""

from __future__ import annotations

import datetime as dt
import pickle
from pathlib import Path

import pandas as pd
from tenacity import retry, stop_after_attempt, wait_fixed

INDEX_SYMBOLS = {"KOSPI": "KS11", "KOSDAQ": "KQ11"}


class DataProvider:
    def __init__(self, lookback_days: int = 200, cache_dir: str | Path = "output/.cache"):
        self.lookback_days = lookback_days
        self.today = dt.date.today()
        self.start = self.today - dt.timedelta(days=lookback_days)
        self.cache_dir = Path(cache_dir) / self.today.strftime("%Y%m%d")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ── 지수 ────────────────────────────────────────────────
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1.0))
    def index_ohlcv(self, market: str) -> pd.DataFrame:
        import FinanceDataReader as fdr

        symbol = INDEX_SYMBOLS[market]
        return fdr.DataReader(symbol, self.start, self.today)

    # ── 종목 유니버스 (스냅샷 + 섹터) ─────────────────────────
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1.0))
    def universe(self, market: str = "ALL", top_n: int = 300) -> pd.DataFrame:
        import FinanceDataReader as fdr

        krx = fdr.StockListing("KRX")
        desc = fdr.StockListing("KRX-DESC")[["Code", "Sector", "Industry"]]
        df = krx.merge(desc, on="Code", how="left")

        markets = ["KOSPI", "KOSDAQ"] if market == "ALL" else [market]
        df = df[df["Market"].isin(markets)].copy()
        df = df.dropna(subset=["Marcap"])
        # ETF/우선주 등 잡음 최소화: 종목명 기준 우선주(끝자리 5/7/9) 제외는 생략, 시총 상위로 컷
        df = df.sort_values("Marcap", ascending=False).head(top_n)
        df["Sector"] = df["Sector"].fillna("기타")
        rename = {"ChagesRatio": "pct_1d", "Close": "close"}
        df = df.rename(columns=rename)
        keep = ["Code", "Name", "Market", "Sector", "Industry", "Marcap", "close", "pct_1d"]
        return df[keep].reset_index(drop=True)

    # ── 개별 종목 일봉 (캐시) ────────────────────────────────
    def stock_ohlcv(self, code: str) -> pd.DataFrame | None:
        cache_file = self.cache_dir / f"{code}.pkl"
        if cache_file.exists():
            try:
                with open(cache_file, "rb") as f:
                    return pickle.load(f)
            except Exception:
                pass
        df = self._fetch_stock(code)
        if df is not None:
            try:
                with open(cache_file, "wb") as f:
                    pickle.dump(df, f)
            except Exception:
                pass
        return df

    @retry(stop=stop_after_attempt(2), wait=wait_fixed(0.5))
    def _fetch_stock(self, code: str) -> pd.DataFrame | None:
        import FinanceDataReader as fdr

        try:
            df = fdr.DataReader(code, self.start, self.today)
        except Exception:
            return None
        if df is None or df.empty or "Close" not in df.columns:
            return None
        return df
